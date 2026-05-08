# MiniCPM-o 完整部署指南

本文档包含 Docker 服务（前端、后端、LiveKit）和 C++ 推理服务的完整部署流程。

> 快速上手请参考 [README_zh.md](./README_zh.md)，本文档提供更详细的手动部署步骤和故障排查。

---

## ⚠️ 必须修改的配置

在开始部署之前，请确认以下路径配置：

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `CPP_DIR` | llama.cpp-omni 编译后的根目录 | `/path/to/llama.cpp-omni` |
| `MODEL_DIR` | GGUF 模型文件目录 | `/path/to/gguf` |

> **注意**: `PYTHON_BIN` 和 `LiveKit node_ip` 会自动检测，通常不需要手动修改。

---

## 目录结构

### 本部署包（已包含，无需修改）
```
./                                                # 部署包根目录
├── deploy_all.sh                                 # ✅ 一键部署脚本 (macOS/Linux)
├── deploy_all_win.ps1                            # ✅ 一键部署脚本 (Windows)
├── DEPLOY.md                                     # ✅ 本文档
├── README.md / README_zh.md                      # ✅ 快速入门文档
├── docker-compose.yml                            # ✅ Docker 编排文件
├── nginx.conf                                    # ✅ 前端 Nginx 配置
├── o45-frontend.tar                              # ✅ 前端 Docker 镜像
├── o45-frontend/                                 # ✅ 前端源码（可选，用于自定义构建）
├── cpp_server/                                   # ✅ Python HTTP 服务
│   ├── minicpmo_cpp_http_server.py              # Python 封装脚本
│   ├── requirements.txt                          # Python 依赖
│   └── assets/
│       └── default_ref_audio.wav                # 默认参考音频
└── omini_backend_code/
    ├── config/
    │   └── livekit.yaml                         # LiveKit 配置（自动更新 IP）
    └── omni_backend.tar                         # 后端 Docker 镜像
```

### 用户需要准备
```
<CPP_DIR>/                                        # ⚠️ llama.cpp-omni 编译后的目录
└── build/bin/llama-server                        # 编译后的 C++ 服务端

<MODEL_DIR>/                                      # ⚠️ GGUF 模型目录
├── MiniCPM-o-4_5-Q4_K_M.gguf                    # LLM 主模型 (~5GB)
├── audio/                                        # 音频编码器
│   └── MiniCPM-o-4_5-audio-F16.gguf
├── vision/                                       # 视觉编码器
│   └── MiniCPM-o-4_5-vision-F16.gguf
├── tts/                                          # TTS 模型
│   ├── MiniCPM-o-4_5-tts-F16.gguf
│   └── MiniCPM-o-4_5-projector-F16.gguf
└── token2wav-gguf/                              # Token2Wav 模型
    ├── encoder.gguf
    ├── flow_matching.gguf
    ├── flow_extra.gguf
    ├── hifigan2.gguf
    └── prompt_cache.gguf
```

---

## 一、前置条件

### 1. 安装 Docker

**macOS**:
```bash
brew install --cask docker
# 或从官网下载：https://www.docker.com/products/docker-desktop
open -a Docker
docker --version
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl start docker && sudo systemctl enable docker
sudo usermod -aG docker $USER  # 免 sudo（需重新登录）
```

**Windows**:
下载安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)，启用 WSL 2 后端。

### 2. 编译 C++ 推理服务

**macOS (Metal)**:
```bash
cd /path/to/llama.cpp-omni
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target llama-server -j
```

**Linux / Windows (CUDA)**:
```bash
cd /path/to/llama.cpp-omni
cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON
cmake --build build --target llama-server -j
```

### 3. 安装 Python 依赖
```bash
pip install -r cpp_server/requirements.txt
```

---

## 二、一键部署（推荐）

### macOS / Linux

```bash
# 查看帮助
./deploy_all.sh --help

# 单工模式（默认）
./deploy_all.sh \
    --cpp-dir /path/to/llama.cpp-omni \
    --model-dir /path/to/gguf

# 双工模式
./deploy_all.sh \
    --cpp-dir /path/to/llama.cpp-omni \
    --model-dir /path/to/gguf \
    --duplex

# 指定 Python 路径（自动检测失败时）
./deploy_all.sh \
    --cpp-dir /path/to/llama.cpp-omni \
    --model-dir /path/to/gguf \
    --python /path/to/python3

# macOS 使用 CoreML/ANE 加速视觉编码器
./deploy_all.sh \
    --cpp-dir /path/to/llama.cpp-omni \
    --model-dir /path/to/gguf \
    --vision-backend coreml
```

### Windows (PowerShell)

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

.\deploy_all_win.ps1 `
    -CppDir "C:\path\to\llama.cpp-omni" `
    -ModelDir "C:\path\to\gguf"

# 双工模式
.\deploy_all_win.ps1 `
    -CppDir "C:\path\to\llama.cpp-omni" `
    -ModelDir "C:\path\to\gguf" `
    -Mode duplex
```

### 脚本参数说明

| 参数 | 说明 | 必须 |
|------|------|------|
| `--cpp-dir PATH` | llama.cpp-omni 编译后的根目录 | ✅ 是 |
| `--model-dir PATH` | GGUF 模型目录 | ✅ 是 |
| `--python PATH` | Python 解释器路径 | 否（自动检测） |
| `--simplex` | 单工模式 | 否（默认） |
| `--duplex` | 双工模式 | 否 |
| `--port PORT` | 推理服务端口 | 否（默认 **9060**） |
| `--vision-backend metal/coreml` | 视觉编码器后端（macOS 专用） | 否（默认 metal） |

### 脚本自动完成的任务

1. ✅ 检查 Docker 环境
2. ✅ 自动更新 LiveKit 配置中的 IP 地址
3. ✅ 加载 Docker 镜像（如 .tar 文件存在）
4. ✅ 启动 Docker 服务（前端、后端、LiveKit）
5. ✅ 安装 Python 依赖
6. ✅ 启动 C++ 推理服务
7. ✅ 注册推理服务到后端

---

## 三、手动部署（分步操作）

如果一键脚本不适用，可按以下步骤手动部署。

### 1. 加载 Docker 镜像并启动服务
```bash
# 加载镜像
docker load -i o45-frontend.tar
docker load -i omini_backend_code/omni_backend.tar

# 更新 LiveKit 配置中的 IP
# 编辑 omini_backend_code/config/livekit.yaml，修改 node_ip 和 domain 为本机 IP

# 启动 Docker 服务
docker compose up -d
docker compose ps
```

### 2. 启动 C++ 推理服务
```bash
export LLAMACPP_ROOT="/path/to/llama.cpp-omni"
export MODEL_DIR="/path/to/gguf"

cd "$LLAMACPP_ROOT"

# 单工模式
python cpp_server/minicpmo_cpp_http_server.py \
    --llamacpp-root "$LLAMACPP_ROOT" \
    --model-dir "$MODEL_DIR" \
    --port 9060 \
    --simplex

# 双工模式
python cpp_server/minicpmo_cpp_http_server.py \
    --llamacpp-root "$LLAMACPP_ROOT" \
    --model-dir "$MODEL_DIR" \
    --port 9060 \
    --duplex
```

> **提示**: `cpp_server/minicpmo_cpp_http_server.py` 位于本部署包目录下，不是 llama.cpp-omni 目录下。

### 3. 后台运行
```bash
nohup python cpp_server/minicpmo_cpp_http_server.py \
    --llamacpp-root "$LLAMACPP_ROOT" \
    --model-dir "$MODEL_DIR" \
    --port 9060 \
    --duplex > /tmp/cpp_server.log 2>&1 &

# 查看日志（服务启动需要 1-2 分钟）
tail -f /tmp/cpp_server.log
```

### 4. 注册推理服务到后端
```bash
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')

# model_type 与启动模式对应: simplex 或 duplex
curl -X POST "http://localhost:8025/api/inference/register" \
  -H "Content-Type: application/json" \
  -d "{\"ip\": \"$LOCAL_IP\", \"port\": 9060, \"model_port\": 9060, \"model_type\": \"simplex\", \"session_type\": \"release\", \"service_name\": \"o45-cpp\"}"
```

### 5. 验证服务
```bash
# 推理服务健康检查
curl http://localhost:9060/health

# 后端健康检查
curl http://localhost:8025/health

# 访问前端
open http://localhost:3000
```

---

## 四、常用命令

### Docker 管理
```bash
docker compose up -d          # 启动
docker compose down           # 停止
docker compose restart        # 重启
docker compose ps             # 状态
docker compose logs -f        # 日志
```

### C++ 推理服务管理
```bash
ps aux | grep minicpmo                    # 查看进程
pkill -f "minicpmo_cpp_http_server"       # 停止服务
tail -f /tmp/cpp_server.log               # 查看日志
```

---

## 五、故障排查

### macOS 端口冲突

macOS 系统服务可能占用 8021 端口。`docker-compose.yml` 已将后端宿主机端口映射为 **8025**：

```yaml
backend:
  ports:
    - "8025:8021"   # 宿主机 8025 -> 容器 8021
```

检查端口占用：
```bash
lsof -i :8025   # 后端
lsof -i :9060   # 推理服务
lsof -i :3000   # 前端
lsof -i :7880   # LiveKit
```

### "体验人数已满"

通常是推理服务未注册或注册参数不匹配：
- 确认推理服务已启动：`curl http://localhost:9060/health`
- 确认 `model_type` 与前端请求匹配（`simplex` 或 `duplex`）
- 重新注册服务（见第三节第 4 步）

### Windows 脚本执行策略
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
# 或
powershell -ExecutionPolicy Bypass -File .\deploy_all_win.ps1
```

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| "体验人数已满" | 推理服务未注册或 `model_type` 不匹配 | 重新注册，确认 simplex/duplex 一致 |
| 模型加载超时 | 模型较大需要时间 | 等待 1-2 分钟，查看 `/tmp/cpp_server.log` |
| 无法连接 LiveKit | `node_ip` 配置错误 | 检查 `omini_backend_code/config/livekit.yaml` 中的 IP |
| Docker 权限不足 (Linux) | 用户未在 docker 组 | `sudo usermod -aG docker $USER` |
| Token2Wav 初始化失败 | GGUF 模型版本不匹配 | 重新下载最新版 `prompt_cache.gguf` |

---

## 六、配置文件说明

### docker-compose.yml 服务端口

| 服务 | 宿主机端口 | 容器端口 | 说明 |
|------|-----------|---------|------|
| frontend | 3000 | 80 | Web UI |
| backend | 8025 | 8021 | 后端 API |
| backend | 8032 | 8022 | 后端 WebSocket |
| livekit | 7880 | 7880 | 实时通信 (TCP) |
| livekit | 7891 | 7881 | LiveKit 管理 |
| livekit | 7882 | 7882 | LiveKit UDP |

### 推理服务端口

| 端口 | 说明 |
|------|------|
| 9060 | Python HTTP API（默认） |
| 9061 | 独立健康检查（推理期间也可用） |
| 19060 | C++ llama-server 内部端口 |
