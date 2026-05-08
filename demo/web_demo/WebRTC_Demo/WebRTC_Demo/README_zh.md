# WebRTC 实时视频交互演示

基于 WebRTC 实现的全双工实时视频交互方案，支持流式输入输出，具有高响应、低延迟的特性。

📖 [English Version](./README.md)

## 概述

本演示采用 WebRTC 技术实现了**全双工实时视频交互**方案。该方案填补了目前开源社区中**流式双工对话方案**的技术空白，为实时多模态交互提供了完整的解决方案。

> [!IMPORTANT]
> **GGUF 模型更新提醒**：GGUF 模型文件近期有更新（包括 `prompt_cache.gguf` 等组件）。如果您之前已下载过模型，请重新下载最新版本以确保兼容性。使用旧版模型文件可能导致初始化失败或音频质量下降。

## 硬件配置要求

全量模型（LLM Q4_K_M + Vision/Audio/TTS F16 + Token2Wav）总计约 **8.3 GB**，运行时 GPU 显存占用约 **10 GB**（含 KV cache 和计算缓冲区）。

<details>
<summary><b>macOS (Apple Silicon)</b></summary>

| 模式 | 最低配置 | 推荐配置 | 说明 |
|------|---------|---------|------|
| **单工** | M1/M2/M3/M4, 16GB 内存 | M4 系列, 32GB+ 内存 | 所有 Apple Silicon 芯片均可运行；芯片越新推理越快 |
| **双工** | M4 Pro, 36GB+ 内存 | **M4 Max, 64GB+ 内存** | 实时流式交互对内存带宽要求高；M4 Max 实测 RTF < 1.0 |

> **说明**：macOS 使用统一内存架构——模型权重、KV cache、计算缓冲区共享系统内存。双工模式的主要瓶颈是计算吞吐量而非内存容量。M1/M2/M3 芯片的带宽和算力不足以支撑实时双工流式交互。
>
> **提示**：如果你的 Mac 只有 16GB 内存，运行前请关闭其他占用内存较大的应用（浏览器、IDE 等），确保有足够内存用于模型加载。

</details>

<details>
<summary><b>Linux / Windows (NVIDIA GPU)</b></summary>

| 模式 | 最低显存 | 推荐显存 | 示例显卡 |
|------|---------|---------|---------|
| **单工** | 10 GB | 12 GB+ | RTX 3060 12GB, RTX 4070 12GB |
| **双工** | 12 GB | 16 GB+ | RTX 4080 16GB, RTX 4090 24GB, RTX 3090 24GB |

**显卡适配参考**：

| 显卡 | 显存 | 单工 | 双工 | 说明 |
|------|------|------|------|------|
| RTX 4060 | 8 GB | ❌ | ❌ | 显存不足 |
| RTX 3060 | 12 GB | ✅ | ⚠️ 勉强 | 部分模块可能需要 CPU offload |
| RTX 4070 | 12 GB | ✅ | ✅ | 双工入门级 |
| RTX 4080 | 16 GB | ✅ | ✅ | 推荐双工配置 |
| RTX 3090 | 24 GB | ✅ | ✅ | 充裕 |
| RTX 4090 | 24 GB | ✅ | ✅ | 最佳性能 |

> **说明**：NVIDIA CUDA GPU 在此类负载下通常比 Apple Silicon Metal 更快。RTX 4070 即可流畅运行双工实时交互。

</details>

## 快速开始

提供三种部署方式，任选其一：

| 方式 | 说明 | 推荐场景 |
|------|------|---------|
| **⚡ 方案 A：oneclick.sh 全自动部署** | 一个脚本全搞定，自动下载源码/模型/工具、编译、启动 | **最省心**，适合新服务器，无需 Docker，无需手动前置准备 |
| **🐳 方案 B：Docker 部署** | 使用 Docker 运行前端/后端，本地运行 C++ 推理 | 灵活可控，支持预构建镜像 |

---

### ⚡ 方案 A：oneclick.sh 全自动部署（推荐）

**零前置条件** — 只需提供 Python 路径，脚本自动完成所有事情：下载源码、下载模型、编译 C++、安装依赖、启动全部服务。**不需要 Docker**。

```bash
# 首次运行 — 全自动下载、编译、启动（双工模式）
PYTHON_CMD=/path/to/python bash oneclick.sh start

# 单工模式
PYTHON_CMD=/path/to/python CPP_MODE=simplex bash oneclick.sh start

# macOS 使用 Metal GPU（部分芯片上比 ANE 更快）
PYTHON_CMD=/path/to/python VISION_BACKEND=metal bash oneclick.sh start

# 查看状态 / 查看日志 / 停止
bash oneclick.sh status
bash oneclick.sh logs
bash oneclick.sh stop
```

脚本自动完成：
1. ✅ 下载 WebRTC_Demo 源码、llama.cpp-omni 源码
2. ✅ 下载 GGUF 模型（从 HuggingFace，国内自动走镜像）
3. ✅ 安装 livekit-server、node、pnpm 等工具
4. ✅ 编译 llama-server
5. ✅ 启动 LiveKit → Backend → C++ 推理 → Frontend（共 4 个服务）
6. ✅ 自动注册推理服务

启动完成后，浏览器打开：**https://localhost:8088**

> 详细环境变量和进阶用法请参考 [oneclick.md](./oneclick.md)。

---

### 🐳 方案 B：Docker 部署

使用 Docker 运行前端/后端/LiveKit，本地运行 C++ 推理服务。

> 以下步骤**仅方案 B 需要**，方案 A 会自动处理。

#### 1. 安装 Docker

<details>
<summary><b>macOS</b></summary>

```bash
# 使用 Homebrew 安装
brew install --cask docker

# 或从官网下载：https://www.docker.com/products/docker-desktop

# 启动 Docker Desktop
open -a Docker

# 验证安装
docker --version
```

</details>

<details>
<summary><b>Linux</b></summary>

```bash
# 安装 Docker Engine (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# （可选）将当前用户添加到 docker 组（免 sudo）
sudo usermod -aG docker $USER
newgrp docker

# 验证安装
docker --version
```

**NVIDIA GPU 支持**（GPU 加速必须）：

```bash
# 安装 NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 验证 GPU 访问
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

</details>

<details>
<summary><b>Windows</b></summary>

1. 下载并安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
2. 确保启用 **WSL 2** 后端（Docker Desktop 设置 → General → Use the WSL 2 based engine）
3. 安装完成后重启电脑

```powershell
# 验证安装（PowerShell）
docker --version
```

</details>

#### 2. 编译 llamacpp-omni 推理服务

<details>
<summary><b>macOS (Apple Silicon)</b></summary>

```bash
# 克隆并进入项目目录
git clone https://github.com/tc-mb/llama.cpp-omni.git
cd llama.cpp-omni

# 编译（macOS 默认启用 Metal 加速）
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target llama-server -j

# 验证编译结果
ls -la build/bin/llama-server
```

**可选：Apple Neural Engine (ANE/NPU) 加速视觉编码器**

macOS 支持通过 CoreML 将视觉编码器运行在 Apple Neural Engine（ANE/NPU）上，从而将 ViT 计算从 GPU 卸载，为 LLM 和 TTS 模型留出更多 GPU 带宽。启用方法：

1. 下载 CoreML 视觉模型（`coreml_minicpmo45_vit_all_f16.mlmodelc`），放置在 `<MODEL_DIR>/vision/` 目录下
2. 部署时添加 `--vision-backend coreml` 参数（见下方部署步骤）

> **说明**：在部分芯片上，Metal GPU 的视觉编码速度可能快于 ANE。建议在你的硬件上分别测试两种后端，选择更快的。默认使用 Metal (GPU)。

</details>

<details>
<summary><b>Linux (NVIDIA GPU)</b></summary>

```bash
# 克隆并进入项目目录
git clone https://github.com/tc-mb/llama.cpp-omni.git
cd llama.cpp-omni

# 编译（启用 CUDA 加速）
cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON
cmake --build build --target llama-server -j

# 验证编译结果
ls -la build/bin/llama-server
```

> **注意**：需要预先安装 NVIDIA 驱动和 CUDA Toolkit，可通过 `nvidia-smi` 验证。

</details>

<details>
<summary><b>Windows (NVIDIA GPU)</b></summary>

**前提**：已安装 Visual Studio 2019+（含 C++ 工作负载）、CMake、CUDA Toolkit。

```powershell
# 克隆并进入项目目录
git clone https://github.com/tc-mb/llama.cpp-omni.git
cd llama.cpp-omni

# 编译（启用 CUDA 加速）
cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON
cmake --build build --config Release --target llama-server -j

# 验证编译结果
dir build\bin\Release\llama-server.exe
```

> **注意**：如果没有 NVIDIA GPU，去掉 `-DGGML_CUDA=ON` 以使用纯 CPU 模式。

</details>

#### 3. 准备 GGUF 模型文件

我们提供了**一键下载脚本** `download_models.sh`，自动下载所有所需的模型文件（共约 8.3GB），支持断点续传。

<details>
<summary><b>下载命令和模型文件说明</b></summary>

```bash
# 下载所有必需的 GGUF 模型（自动选择最快源）
./download_models.sh --model-dir /path/to/gguf

# 使用 ModelScope（国内更快）
./download_models.sh --model-dir /path/to/gguf --source ms

# 使用 HuggingFace 镜像
./download_models.sh --model-dir /path/to/gguf --hf-mirror https://hf-mirror.com

# 选择不同的 LLM 量化版本（默认 Q4_K_M）
./download_models.sh --model-dir /path/to/gguf --quant Q8_0
```

脚本下载以下文件：

```
<MODEL_DIR>/
├── MiniCPM-o-4_5-Q4_K_M.gguf        # LLM 主模型 (~5GB)
├── audio/                            # 音频编码器
│   └── MiniCPM-o-4_5-audio-F16.gguf
├── vision/                           # 视觉编码器
│   └── MiniCPM-o-4_5-vision-F16.gguf
├── tts/                              # TTS 模型
│   ├── MiniCPM-o-4_5-tts-F16.gguf
│   └── MiniCPM-o-4_5-projector-F16.gguf
└── token2wav-gguf/                   # Token2Wav 模型
    ├── encoder.gguf
    ├── flow_matching.gguf
    ├── flow_extra.gguf
    ├── hifigan2.gguf
    └── prompt_cache.gguf
```

可选 LLM 量化版本：`Q4_0`、`Q4_1`、`Q4_K_M`（推荐）、`Q4_K_S`、`Q5_0`、`Q5_1`、`Q5_K_M`、`Q5_K_S`、`Q6_K`、`Q8_0`、`F16`

</details>

#### 4. 可选：加载预构建 Docker 镜像

如果不想自行构建前端/后端镜像，可下载预构建镜像：

📦 [下载 Docker 镜像](https://drive.google.com/file/d/191h2OJYir9aAL4KIE-mFF_XJ1jT6gnxj/view?usp=sharing)

```bash
# 解压并加载镜像（已有镜像可跳过此步）
docker load -i o45-frontend.tar
docker load -i omini_backend_code/omni_backend.tar
```

#### 5. 一键启动

<details>
<summary><b>macOS / Linux (deploy_all.sh)</b></summary>

```bash
cd WebRTC_Demo

# 单工模式（默认）
./deploy_all.sh \
    --cpp-dir /path/to/llama.cpp-omni \
    --model-dir /path/to/gguf

# 双工模式
./deploy_all.sh \
    --cpp-dir /path/to/llama.cpp-omni \
    --model-dir /path/to/gguf \
    --duplex
```

**macOS 专属选项**：

```bash
# 使用 Apple Neural Engine (ANE/NPU) 加速视觉编码器
./deploy_all.sh \
    --cpp-dir /path/to/llama.cpp-omni \
    --model-dir /path/to/gguf \
    --duplex \
    --vision-backend coreml

# 手动指定 Python 路径
./deploy_all.sh \
    --cpp-dir /path/to/llama.cpp-omni \
    --model-dir /path/to/gguf \
    --python /path/to/python3
```

> **提示**：`--vision-backend coreml` 将视觉编码器运行在 NPU 上，释放 GPU 给 LLM/TTS 使用。默认值为 `metal`（GPU）。建议在你的硬件上分别测试两种方案，选择延迟更低的。

</details>

<details>
<summary><b>Windows (deploy_all_win.ps1)</b></summary>

```powershell
cd WebRTC_Demo
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# 单工模式（默认）
.\deploy_all_win.ps1 `
    -CppDir "C:\path\to\llama.cpp-omni" `
    -ModelDir "C:\path\to\gguf"

# 双工模式
.\deploy_all_win.ps1 `
    -CppDir "C:\path\to\llama.cpp-omni" `
    -ModelDir "C:\path\to\gguf" `
    -Mode duplex
```

</details>

脚本自动完成：启动 Docker 服务（前端、后端、LiveKit）→ 安装 Python 依赖 → 启动 C++ 推理 → 注册服务

启动完成后，浏览器打开：**http://localhost:3000**

> 手动逐步部署请参考 [DEPLOY.md](./DEPLOY.md)。

### 服务端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 3000 | Web UI |
| 后端 | 8025 | 后端 API |
| LiveKit | 7880 | 实时通信 |
| 推理服务 | 9060 | C++ HTTP API |

### 常见问题

<details>
<summary><b>macOS：端口 8021 被系统服务占用</b></summary>

macOS 系统服务可能会占用 8021 端口。部署脚本默认使用 8025 端口以避免冲突。

```bash
# 检查端口是否被占用
lsof -i :8021
```

</details>

<details>
<summary><b>Linux：Docker 权限不足</b></summary>

```bash
# 将用户添加到 docker 组
sudo usermod -aG docker $USER
newgrp docker

# 或使用 sudo 运行
sudo ./deploy_all.sh ...
```

</details>

<details>
<summary><b>Windows：脚本执行策略错误</b></summary>

```powershell
# 允许当前会话执行脚本
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# 或直接运行
powershell -ExecutionPolicy Bypass -File .\deploy_all_win.ps1
```

</details>

## 核心特性

### 🔄 全双工通信
- 支持音视频双向同时传输
- 自然流畅的对话体验，无需等待轮次切换

### ⚡ 高响应低延迟
- 流式输入输出，实现实时交互
- 端到端延迟优化
- 对话过程中即时反馈

### 🚀 原生支持 llamacpp-omni
- 无缝集成 [llamacpp-omni](https://github.com/tc-mb/llama.cpp-omni) 作为推理后端
- 快速部署，简单配置
- 高效的资源利用

### 🎯 快速体验 MiniCPM-o 4.5
- 快速体验 MiniCPM-o 4.5 的完整能力
- 实时多模态理解与生成
- 语音与视频交互一体化

## 技术亮点

- **WebRTC 协议**：业界标准的实时通信协议
- **流式架构**：连续数据流，交互流畅
- **双工设计**：填补开源社区流式双工对话方案的空白
- **跨平台支持**：支持 macOS (Metal)、Linux (CUDA)、Windows (CUDA)

## 相关资源

- [MiniCPM-o 4.5 模型](https://huggingface.co/openbmb/MiniCPM-o-4_5)
- [llamacpp-omni 推理后端](https://github.com/tc-mb/llama.cpp-omni)
