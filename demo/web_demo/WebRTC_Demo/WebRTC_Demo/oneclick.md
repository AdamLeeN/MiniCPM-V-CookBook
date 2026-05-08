# oneclick.sh — MiniCPM-o WebRTC Demo One-Click Deployment

One script to download, build, and run the entire MiniCPM-o WebRTC demo stack **without Docker**.

## Prerequisites

| Requirement | Note |
|------------|------|
| **Python >= 3.9** |  |
| git | sudo \[apt\|yum\|dnf\|brew\] install git |
| cmake | sudo \[apt\|yum\|dnf\|brew\] install cmake ninja |

> **Tip:** If all tools are already installed, no sudo is needed and the script runs fully unprivileged.

## Quick Start

```bash
# Start all services (auto-downloads everything on first run)
bash oneclick.sh start
# Or specify Python path if needed
PYTHON_CMD=/path/to/python bash oneclick.sh start

# Check service status
bash oneclick.sh status

# View logs (all services, or pick one)
bash oneclick.sh logs
bash oneclick.sh logs cpp        # C++ inference only
bash oneclick.sh logs backend    # backend only

# Stop everything
bash oneclick.sh stop

# Restart (stop + start)
bash oneclick.sh restart
# Or specify Python path if needed
PYTHON_CMD=/path/to/python bash oneclick.sh restart

# Pull latest code + auto-rebuild
bash oneclick.sh update

# Download dependencies only (no start)
bash oneclick.sh download
```

## Commands

| Command    | Description |
|------------|-------------|
| `start`    | Start all 4 services (auto-downloads missing dependencies) |
| `stop`     | Stop all services |
| `restart`  | Stop then start all services |
| `status`   | Show running status of each service |
| `logs`     | Tail logs: `logs all` / `logs livekit` / `logs backend` / `logs cpp` / `logs frontend` |
| `download` | Download source code + models only (no start) |
| `update`   | Pull latest code from git, auto-rebuild if needed |

## Architecture & Startup Order

```
┌──────────────────────────────────────────────────────────────────┐
│                        oneclick.sh start                         │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                    preflight_check()
                    ┌──────┴────-──┐
                    │ Auto-download│  (if missing)
                    │ & auto-build │
                    └──────┬──-────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
  WebRTC_Demo        llama.cpp-omni     GGUF Models
  (sparse clone)     (git clone +       (huggingface-cli
                      cmake build)       download)
                           │
         ┌─────────────────┼──────────────────────-───┐
         │                 │                          │
         ▼                 ▼                          ▼
  [1/4] LiveKit     [2/4] Backend              [3/4] C++ Inference
  Server             (FastAPI)                  (llama-server)
  :7880              :8021                       :9060
         │                 │                          │
         │                 │                          │
         └────────┬────────┘                          │
                  │    token auth                     │
                  │◄──────────────────────────────────┘
                  │    register as inference service
                  │
                  ▼
           [4/4] Frontend
           (Vue + Vite)
           :8088 (HTTPS)
```

### Service Details

| # | Service | Port | Description |
|---|---------|------|-------------|
| 1 | **LiveKit Server** | 7880 | WebRTC SFU (Selective Forwarding Unit) for real-time audio/video |
| 2 | **Backend (FastAPI)** | 8021 | API server, room management, LiveKit token generation |
| 3 | **C++ Inference** | 9060 | llama-server + MiniCPM-o model (LLM + TTS + Vision + Audio) |
| 4 | **Frontend (Vue)** | 8088 | HTTPS web UI, proxies API/WebSocket to backend & LiveKit |

### Startup Flow

1. **Preflight Check** — verifies all dependencies, auto-downloads/installs missing ones:
   - Source code: `WebRTC_Demo`, `llama.cpp-omni`
   - Models: GGUF files from HuggingFace
   - Tools: `livekit-server`, `node`, `pnpm`, `python`, `cmake`
   - Binary: `llama-server` (auto-compiles if missing)

2. **LiveKit Server** — starts with auto-synced config:
   - Updates `livekit.yaml` API secret to match the script
   - Updates `node_ip` / `domain` to local IP

3. **Backend** — installs Python deps on first run, then starts FastAPI:
   - Connects to LiveKit via WebSocket
   - Provides REST API for the frontend

4. **C++ Inference** — the heaviest service:
   - Python wrapper (`minicpmo_cpp_http_server.py`) launches `llama-server`
   - Loads LLM, TTS, Vision, Audio, and Token2Wav models
   - Registers itself with the Backend as an available inference service
   - Health check waits up to 5 minutes for model loading

5. **Frontend** — dev mode (Vite hot reload) or prod mode (static build):
   - Generates HTTPS self-signed certificate (WebRTC requires secure context)
   - Proxies `/api/*` to Backend and `/rtc/*` to LiveKit

## Environment Variables

All variables have sensible defaults. Override as needed:

### Essential

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHON_CMD` | `python` | Python interpreter path (>= 3.9, recommend 3.11) |

### C++ Inference

| Variable | Default | Description |
|----------|---------|-------------|
| `LLAMACPP_ROOT` | `$SCRIPT_DIR/llama.cpp-omni` | llama.cpp-omni source directory |
| `MODEL_DIR` | `$SCRIPT_DIR/models/openbmb/MiniCPM-o-4_5-gguf` | GGUF model directory |
| `LLM_QUANT` | `Q4_K_M` | LLM quantization to download: `Q4_0`, `Q4_1`, `Q4_K_M`, `Q4_K_S`, `Q5_0`, `Q5_1`, `Q5_K_M`, `Q5_K_S`, `Q6_K`, `Q8_0`, or `F16` |
| `CPP_MODE` | `duplex` | Inference mode: `duplex` (full-duplex) or `simplex` |
| `VISION_BACKEND` | `coreml` (macOS) / `""` (Linux) | Vision encoder: `metal`, `coreml`, or `""` (default) |
| `N_GPU_LAYERS` | `99` | Number of LLM layers to offload to GPU |
| `TOKEN2WAV_DEVICE` | `gpu:1` | Token2Wav device: `gpu:1`, `gpu:0`, or `cpu` |

### Ports

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_PORT` | `1` | **Enabled by default.** Auto-allocate available ports if defaults are in use (`1`=enable, `0`=disable). Uses dual-layer detection to reliably detect port conflicts even from `sudo` processes. |
| `LIVEKIT_PORT` | `7880` | LiveKit server port |
| `BACKEND_PORT` | `8021` | Backend API port |
| `FRONTEND_PORT` | `8088` | Frontend HTTPS port |
| `CPP_SERVER_PORT` | `9060` | C++ inference HTTP port (+1 for health, +10000 for llama-server) |

> **Note:** With `AUTO_PORT=1` (default), the script automatically finds available ports if defaults are in use. All custom ports are fully respected — configuration files (`livekit.yaml`, `local.yaml`) are dynamically patched to ensure services use your specified ports.

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `FRONTEND_MODE` | `prod` | `prod` (production build) or `dev` (Vite hot reload) |
| `FORCE_BUILD` | `0` | Set to `1` to force frontend rebuild in prod mode |

### Download Mirrors (for China)

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_PROXY` | `https://ghfast.top` | GitHub download proxy (empty = direct) |
| `HF_ENDPOINT` | `https://hf-mirror.com` | HuggingFace mirror (empty = official) |
| `NODE_MIRROR` | `https://npmmirror.com/mirrors/node` | Node.js binary mirror |
| `NPM_REGISTRY` | `https://registry.npmmirror.com` | npm registry mirror |

### Repository URLs

| Variable | Default | Description |
|----------|---------|-------------|
| `COOKBOOK_REPO` | `https://github.com/OpenSQZ/MiniCPM-V-CookBook.git` | WebRTC_Demo source repo |
| `COOKBOOK_BRANCH` | `webrtc-demo` | Branch to checkout |
| `LLAMACPP_REPO` | `https://github.com/tc-mb/llama.cpp-omni.git` | llama.cpp-omni repo |
| `HF_MODEL_REPO` | `openbmb/MiniCPM-o-4_5-gguf` | HuggingFace model repo |

## Common Scenarios

### First Run on a New Server

```bash
# Use default Python (searches for 'python' in PATH)
bash oneclick.sh start

# Or specify custom Python path (e.g., conda environment)
PYTHON_CMD=/path/to/conda/envs/py311/bin/python bash oneclick.sh start
```

> **Note:** If `python` command is not in your PATH, you must specify `PYTHON_CMD`.

### Duplex / Simplex Mode

```bash
# Duplex (default) — speak and listen simultaneously, natural conversation
bash oneclick.sh start
# Or with custom Python
PYTHON_CMD=/path/to/python CPP_MODE=duplex bash oneclick.sh start

# Simplex — turn-based, one speaks at a time
CPP_MODE=simplex bash oneclick.sh start
# Or with custom Python
PYTHON_CMD=/path/to/python CPP_MODE=simplex bash oneclick.sh start
```

### 16GB macOS (Apple Silicon)

GPU memory is tight. Use Metal backend and offload Token2Wav to CPU:

```bash
# With default Python
VISION_BACKEND=metal TOKEN2WAV_DEVICE=cpu bash oneclick.sh start

# Or with custom Python
PYTHON_CMD=/path/to/python \
  VISION_BACKEND=metal \
  TOKEN2WAV_DEVICE=cpu \
  bash oneclick.sh start
```

### Choose LLM Quantization

By default, `Q4_K_M` is downloaded (~5 GB). For better quality or smaller size:

```bash
# Higher quality (larger size)
LLM_QUANT=Q5_K_M bash oneclick.sh start     # ~5.8 GB
LLM_QUANT=Q8_0 bash oneclick.sh start       # ~8.7 GB
LLM_QUANT=F16 bash oneclick.sh start        # ~16 GB

# Smaller size (lower quality)
LLM_QUANT=Q4_K_S bash oneclick.sh start     # ~4.8 GB
LLM_QUANT=Q4_0 bash oneclick.sh start       # ~4.7 GB
```

> **Note:** Only the specified quantization is downloaded. Submodels (vision, audio, tts, token2wav) are always F16.
> Total download: ~3.9 GB (submodels) + LLM quantization size = ~8.9 GB for Q4_K_M (vs. 79 GB full repo).

### Production Mode (Stable Frontend)

```bash
FRONTEND_MODE=prod bash oneclick.sh start
# Or with custom Python
PYTHON_CMD=/path/to/python FRONTEND_MODE=prod bash oneclick.sh start
```

### Direct Connection (No China Mirrors)

```bash
# With default Python
GITHUB_PROXY="" \
  HF_ENDPOINT="" \
  NODE_MIRROR="" \
  NPM_REGISTRY="" \
  bash oneclick.sh start

# Or with custom Python
PYTHON_CMD=/path/to/python \
  GITHUB_PROXY="" \
  HF_ENDPOINT="" \
  NODE_MIRROR="" \
  NPM_REGISTRY="" \
  bash oneclick.sh start
```

### Update to Latest Code

```bash
bash oneclick.sh update    # pulls code + auto-rebuilds if needed
bash oneclick.sh restart   # apply changes
```

### View Logs

```bash
bash oneclick.sh logs              # all services
bash oneclick.sh logs cpp          # C++ inference only
bash oneclick.sh logs backend      # backend only
```

## Directory Layout

```
$SCRIPT_DIR/
├── oneclick.sh                    # This script
├── WebRTC_Demo/                   # Project source (auto-downloaded)
│   ├── omini_backend_code/
│   │   ├── config/livekit.yaml    # LiveKit server config (auto-synced)
│   │   └── code/                  # Backend Python code
│   │       └── config/local.yaml  # Backend config
│   ├── o45-frontend/              # Vue frontend
│   └── cpp_server/                # C++ inference Python wrapper
├── llama.cpp-omni/                # C++ inference engine (auto-downloaded)
│   └── build/bin/llama-server     # Compiled binary (auto-built)
├── models/openbmb/MiniCPM-o-4_5-gguf/  # GGUF models (auto-downloaded)
│   ├── MiniCPM-o-4_5-Q4_K_M.gguf       # LLM (selected quantization, default Q4_K_M)
│   ├── tts/                             # TTS model + projector (F16)
│   ├── audio/                           # Audio processing model (F16)
│   ├── vision/                          # Vision encoder (F16 GGUF + CoreML)
│   └── token2wav-gguf/                  # Token2Wav vocoder (5 files)
├── .pids/                         # PID files for service management
├── .logs/                         # Log files
│   ├── livekit.log
│   ├── backend.log
│   ├── cpp_server.log             # Includes [CPP] prefixed llama-server output
│   └── frontend.log
└── .certs/                        # Auto-generated HTTPS certificates
```

## Troubleshooting

### Port Already in Use

**Default behavior (AUTO_PORT=1):**

The script **automatically finds available ports** if defaults are in use:

```bash
# Simply start (auto-allocation enabled by default)
bash oneclick.sh start
```

Port detection works reliably even for processes running with `sudo`/elevated privileges.

**To disable auto-allocation** (use fixed ports only):

```bash
AUTO_PORT=0 bash oneclick.sh start
```

**Manual port specification:**

```bash
BACKEND_PORT=8086 bash oneclick.sh start
```

Custom ports are fully supported and dynamically applied to all configuration files.

**Manual kill (if needed):**

```bash
# Find what's using the port
lsof -i :8021        # macOS
ss -tlnp | grep :8021  # Linux
netstat -an | grep 8021  # Cross-platform

# Kill it manually
kill <PID>
```

### Backend Not Starting on Custom Port

If you set `BACKEND_PORT` but the backend still uses 8021:

1. **Check the log for actual listening port:**
   ```bash
   grep "监听地址" .logs/backend.log
   # Should show: 监听地址: 0.0.0.0:8086
   ```

2. **Verify config patching:**
   ```bash
   grep "port:" WebRTC_Demo/omini_backend_code/code/config/local.yaml
   # Should show: port: 8086
   ```

3. **The script auto-patches configs** — no manual editing needed! If it still fails, check for file permission issues.

### Low GPU Utilization (High CPU, Low GPU)

If `llama-server` shows high CPU usage but low GPU:

1. **Verify CUDA/Metal acceleration:**
   ```bash
   # Check build log (shown during build)
   grep -i "CUDA\\|Metal" .logs/cpp_server.log
   ```

2. **Increase performance parameters:**
   ```bash
   BATCH_SIZE=4096 \
   UBATCH_SIZE=1024 \
   PARALLEL=8 \
   FLASH_ATTN=1 \
   bash oneclick.sh restart
   ```

3. **On Linux with NVIDIA GPU:**
   - Ensure `N_GPU_LAYERS=99` (default, offloads all layers)
   - Check CUDA drivers: `nvidia-smi`
   - Verify `llama-server` is linked with CUDA: 
     ```bash
     ldd llama.cpp-omni/build/bin/llama-server | grep cuda
     ```

4. **On macOS with Apple Silicon:**
   - Use `VISION_BACKEND=metal` for GPU acceleration
   - Metal is automatically enabled for LLM inference

### 401 Unauthorized (LiveKit)

The script auto-syncs `livekit.yaml` API secret on every start. If you still see 401:
- Check that `livekit.yaml` `keys.devkey` matches `LIVEKIT_API_SECRET` in the script
- Restart LiveKit: `bash oneclick.sh restart`

### GPU Out of Memory (macOS)

Reduce GPU usage:

```bash
TOKEN2WAV_DEVICE=cpu VISION_BACKEND=metal bash oneclick.sh restart
```

### C++ Inference Service Keeps Restarting

If you see repeated restarts in the logs:

1. **Check if GPU memory check is enabled:**
   ```bash
   grep "GPU_CHECK_ENABLED" .logs/cpp_server.log
   ```

2. **Disable for local deployment (recommended):**
   ```bash
   GPU_MEMORY_CHECK=0 bash oneclick.sh restart
   ```

> **Note:** GPU memory check is **disabled by default** (`GPU_MEMORY_CHECK=0`). Only enable for production/cloud deployments.

### Model Download Stuck or Incomplete

If model download appears stuck or only downloads partial files:

1. **The script now uses selective download** — only necessary files are downloaded (~8.9 GB vs. 79 GB full repo)

2. **Check download progress:**
   - Selective download uses `huggingface_hub` Python API (shows progress bars)
   - If it falls back to `hf` CLI, you'll see a warning

3. **Verify downloaded files:**
   ```bash
   ls -lh models/openbmb/MiniCPM-o-4_5-gguf/
   # Should show:
   # - MiniCPM-o-4_5-Q4_K_M.gguf (or your selected quantization)
   # - vision/, audio/, tts/, token2wav-gguf/ directories
   ```

4. **Force re-download:**
   ```bash
   rm -rf models/openbmb/MiniCPM-o-4_5-gguf
   bash oneclick.sh download
   ```

### C++ Server Not Registering with Backend

If C++ inference service starts but doesn't appear as "available":

1. **Check reconnect mechanism:**
   ```bash
   grep "reconnect\\|register" .logs/cpp_server.log
   ```

2. **Verify backend connectivity:**
   ```bash
   curl http://localhost:8021/health
   # Should return: {"status":"healthy","service":"minicpmo-backend"}
   ```

3. **Auto-reconnect is enabled by default** — if registration fails, it will retry every 60s.
