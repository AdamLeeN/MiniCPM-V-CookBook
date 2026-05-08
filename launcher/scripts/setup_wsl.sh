#!/bin/bash
# ============================================================================
# MiniCPM-o WSL2 初始化脚本
# 在 WSL2 Ubuntu 中安装所有依赖
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }

# ======================== 参数 ========================
PROJECT_DIR="${1:-$HOME/.minicpmo}"
PYTHON_VERSION="3.11"
NODE_VERSION="v22.14.0"

info "初始化目录: $PROJECT_DIR"
mkdir -p "$PROJECT_DIR"

# ======================== 更新系统包 ========================
info "更新系统包..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    build-essential \
    cmake \
    ninja-build \
    git \
    curl \
    wget \
    unzip \
    libcurl4-openssl-dev \
    libssl-dev \
    pkg-config \
    ffmpeg \
    openssl \
    > /dev/null 2>&1
ok "系统包更新完成"

# ======================== 安装 Python ========================
info "检查 Python $PYTHON_VERSION..."
if ! command -v python3.11 &>/dev/null; then
    info "安装 Python $PYTHON_VERSION..."
    sudo apt-get install -y -qq software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3.11 python3.11-venv python3.11-dev python3-pip
fi
ok "Python: $(python3.11 --version)"

# ======================== 创建虚拟环境 ========================
VENV_DIR="$PROJECT_DIR/.venv"
if [[ ! -f "$VENV_DIR/bin/python" ]]; then
    info "创建 Python 虚拟环境..."
    python3.11 -m venv "$VENV_DIR" --upgrade-deps
    ok "虚拟环境创建完成: $VENV_DIR"
else
    ok "虚拟环境已存在: $VENV_DIR"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"
PYTHON_CMD="$VENV_DIR/bin/python"
PIP_CMD="$PYTHON_CMD -m pip"

# ======================== 安装 Node.js ========================
info "检查 Node.js..."
if ! command -v node &>/dev/null || [[ $(node --version | cut -d'v' -f2 | cut -d'.' -f1) -lt 18 ]]; then
    info "安装 Node.js $NODE_VERSION..."
    NODE_DIR="$HOME/.local"
    mkdir -p "$NODE_DIR"
    
    NODE_TAR="node-${NODE_VERSION}-linux-x64.tar.xz"
    NODE_URL="https://npmmirror.com/mirrors/node/${NODE_VERSION}/${NODE_TAR}"
    
    curl -fsSL "$NODE_URL" | tar -xJ -C "$NODE_DIR" --strip-components=1
    export PATH="$NODE_DIR/bin:$PATH"
    
    # 添加到 .bashrc
    if ! grep -q "$NODE_DIR/bin" "$HOME/.bashrc"; then
        echo "export PATH=\"$NODE_DIR/bin:\$PATH\"" >> "$HOME/.bashrc"
    fi
    ok "Node.js 安装完成: $(node --version)"
else
    ok "Node.js: $(node --version)"
fi

# ======================== 安装 pnpm ========================
info "检查 pnpm..."
if ! command -v pnpm &>/dev/null; then
    info "安装 pnpm..."
    npm install -g pnpm --registry=https://registry.npmmirror.com
    ok "pnpm 安装完成: $(pnpm --version)"
else
    ok "pnpm: $(pnpm --version)"
fi

# ======================== 安装 Python 依赖 ========================
info "安装 Python 依赖..."

# 后端依赖
BACKEND_DIR="$PROJECT_DIR/WebRTC_Demo/omini_backend_code/code"
if [[ -f "$BACKEND_DIR/pyproject.toml" ]]; then
    info "安装后端依赖..."
    cd "$BACKEND_DIR"
    $PIP_CMD install -e . --quiet
    ok "后端依赖安装完成"
fi

# C++ server 依赖
CPP_SERVER_DIR="$PROJECT_DIR/WebRTC_Demo/cpp_server"
if [[ -f "$CPP_SERVER_DIR/requirements.txt" ]]; then
    info "安装 C++ server 依赖..."
    $PIP_CMD install -r "$CPP_SERVER_DIR/requirements.txt" --quiet
    ok "C++ server 依赖安装完成"
fi

# modelscope (用于模型下载)
if ! $PYTHON_CMD -c "import modelscope" 2>/dev/null; then
    info "安装 modelscope..."
    $PIP_CMD install modelscope --quiet
    ok "modelscope 安装完成"
fi

# huggingface_hub (备用)
if ! $PYTHON_CMD -c "import huggingface_hub" 2>/dev/null; then
    info "安装 huggingface_hub..."
    $PIP_CMD install huggingface_hub --quiet
    ok "huggingface_hub 安装完成"
fi

ok "所有 Python 依赖安装完成"

# ======================== 编译 llama-server ========================
LLAMACPP_DIR="$PROJECT_DIR/llama.cpp-omni"
if [[ -d "$LLAMACPP_DIR" ]]; then
    info "编译 llama-server..."
    cd "$LLAMACPP_DIR"
    
    # 检测 CUDA
    CMAKE_ARGS="-DCMAKE_BUILD_TYPE=Release"
    if command -v nvcc &>/dev/null || [[ -d "/usr/local/cuda" ]]; then
        info "检测到 CUDA，启用 GPU 加速"
        CMAKE_ARGS="$CMAKE_ARGS -DGGML_CUDA=ON"
        if [[ -d "/usr/local/cuda" ]]; then
            export PATH="/usr/local/cuda/bin:$PATH"
        fi
    else
        info "未检测到 CUDA，使用 CPU 模式"
    fi
    
    cmake -B build $CMAKE_ARGS
    cmake --build build --target llama-server -j$(nproc)
    
    if [[ -x "$LLAMACPP_DIR/build/bin/llama-server" ]]; then
        ok "llama-server 编译完成"
    else
        err "llama-server 编译失败"
        exit 1
    fi
else
    warn "llama.cpp-omni 目录不存在，跳过编译"
fi

# ======================== 安装前端依赖 ========================
FRONTEND_DIR="$PROJECT_DIR/WebRTC_Demo/o45-frontend"
if [[ -d "$FRONTEND_DIR" ]]; then
    info "安装前端依赖..."
    cd "$FRONTEND_DIR"
    pnpm install --registry=https://registry.npmmirror.com
    ok "前端依赖安装完成"
    
    # 构建前端
    info "构建前端..."
    VITE_CPP_MODE="simplex" pnpm run build:external
    ok "前端构建完成"
else
    warn "前端目录不存在，跳过"
fi

# ======================== 生成 HTTPS 证书 ========================
CERT_DIR="$PROJECT_DIR/WebRTC_Demo/.certs"
if [[ ! -f "$CERT_DIR/server.crt" ]]; then
    info "生成 HTTPS 自签名证书..."
    mkdir -p "$CERT_DIR"
    openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout "$CERT_DIR/server.key" \
        -out "$CERT_DIR/server.crt" \
        -days 365 \
        -subj "/CN=127.0.0.1" \
        -addext "subjectAltName=IP:127.0.0.1,DNS:localhost"
    ok "证书生成完成"
fi

# ======================== 完成 ========================
echo ""
echo "=============================================="
ok "WSL2 初始化完成！"
echo "=============================================="
echo ""
echo "项目目录: $PROJECT_DIR"
echo "Python: $PYTHON_CMD"
echo "虚拟环境: $VENV_DIR"
echo ""
echo "下一步:"
echo "  1. 下载模型: modelscope download --model openbmb/MiniCPM-o-4_5-gguf"
echo "  2. 启动服务: bash start_services.sh"
echo ""
