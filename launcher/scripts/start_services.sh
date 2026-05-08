#!/bin/bash
# ============================================================================
# MiniCPM-o 服务启动脚本
# 在 WSL2 中启动 Backend + C++ Inference + Frontend
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
BACKEND_PORT="${2:-8021}"
FRONTEND_PORT="${3:-8088}"
CPP_SERVER_PORT="${4:-9060}"
LIVEKIT_PORT="${5:-7880}"
CPP_MODE="${6:-simplex}"
FRONTEND_MODE="${7:-prod}"

VENV_DIR="$PROJECT_DIR/.venv"
WEBRTC_DIR="$PROJECT_DIR/WebRTC_Demo"
LLAMACPP_DIR="$PROJECT_DIR/llama.cpp-omni"
MODEL_DIR="${MODEL_DIR:-$HOME/models/openbmb/MiniCPM-o-4_5-gguf}"

# 激活虚拟环境
source "$VENV_DIR/bin/activate"
PYTHON_CMD="$VENV_DIR/bin/python"

# 确保日志目录存在
LOG_DIR="$PROJECT_DIR/.logs"
mkdir -p "$LOG_DIR"
PID_DIR="$PROJECT_DIR/.pids"
mkdir -p "$PID_DIR"

# LiveKit API 配置
LIVEKIT_API_KEY="devkey"
LIVEKIT_API_SECRET="secretsecretsecretsecretsecretsecret"

info "=============================================="
info "MiniCPM-o 服务启动"
info "=============================================="
info "项目目录: $PROJECT_DIR"
info "Backend Port: $BACKEND_PORT"
info "Frontend Port: $FRONTEND_PORT"
info "CPP Server Port: $CPP_SERVER_PORT"
info "LiveKit Port: $LIVEKIT_PORT"
info "CPP Mode: $CPP_MODE"
info "Frontend Mode: $FRONTEND_MODE"
info "Model Dir: $MODEL_DIR"

# ======================== 工具函数 ========================

check_port() {
    local port=$1
    if (echo >/dev/tcp/127.0.0.1/"$port") 2>/dev/null; then
        return 0
    fi
    return 1
}

wait_for_port() {
    local port=$1
    local name=$2
    local max_wait=${3:-30}
    local i=0
    while ! check_port "$port"; do
        sleep 1
        i=$((i + 1))
        if [[ $i -ge $max_wait ]]; then
            err "$name 启动超时 (${max_wait}s)"
            return 1
        fi
    done
    ok "$name 已启动 (port $port, ${i}s)"
}

kill_by_pidfile() {
    local pidfile=$1
    if [[ -f "$pidfile" ]]; then
        local pid=$(cat "$pidfile" 2>/dev/null)
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$pidfile"
    fi
}

# ======================== 清理旧进程 ========================
info "清理旧进程..."
kill_by_pidfile "$PID_DIR/backend.pid"
kill_by_pidfile "$PID_DIR/cpp_server.pid"
kill_by_pidfile "$PID_DIR/frontend.pid"
pkill -f "minicpmo_cpp_http_server" 2>/dev/null || true
pkill -f "llama-server" 2>/dev/null || true
sleep 1
ok "旧进程已清理"

# ======================== [1/3] 启动 Backend ========================
info "========== [1/3] 启动 Backend (FastAPI) =========="

BACKEND_DIR="$WEBRTC_DIR/omini_backend_code/code"
BACKEND_CONFIG="$BACKEND_DIR/config/local.yaml"

# 更新后端配置端口
if [[ -f "$BACKEND_CONFIG" ]]; then
    sed -i "s/^  port:.*/  port: $BACKEND_PORT/" "$BACKEND_CONFIG" 2>/dev/null || true
fi

cd "$BACKEND_DIR"

APP_ENV=local \
SERVER_PORT="$BACKEND_PORT" \
LIVEKIT_URL="ws://localhost:$LIVEKIT_PORT" \
LIVEKIT_API_KEY="$LIVEKIT_API_KEY" \
LIVEKIT_API_SECRET="$LIVEKIT_API_SECRET" \
WORKERS=1 \
NUMBA_CACHE_DIR=/tmp/numba_cache \
$PYTHON_CMD main.py > "$LOG_DIR/backend.log" 2>&1 &

echo $! > "$PID_DIR/backend.pid"

wait_for_port "$BACKEND_PORT" "Backend" 60

# ======================== [2/3] 启动 C++ Inference ========================
info "========== [2/3] 启动 C++ Inference =========="

CPP_HEALTH_PORT=$((CPP_SERVER_PORT + 1))
CPP_LLAMA_PORT=$((CPP_SERVER_PORT + 10000))

SERVER_SCRIPT="$WEBRTC_DIR/cpp_server/minicpmo_cpp_http_server.py"
REF_AUDIO="$WEBRTC_DIR/cpp_server/assets/default_ref_audio.wav"

MODE_FLAG="--simplex"
[[ "$CPP_MODE" == "duplex" ]] && MODE_FLAG="--duplex"

cd "$LLAMACPP_DIR"

CUDA_VISIBLE_DEVICES="0" \
REGISTER_URL="http://127.0.0.1:$BACKEND_PORT" \
REF_AUDIO="$REF_AUDIO" \
$PYTHON_CMD "$SERVER_SCRIPT" \
    --llamacpp-root "$LLAMACPP_DIR" \
    --model-dir "$MODEL_DIR" \
    --port "$CPP_SERVER_PORT" \
    --gpu-devices "0" \
    $MODE_FLAG \
    > "$LOG_DIR/cpp_server.log" 2>&1 &

echo $! > "$PID_DIR/cpp_server.pid"

info "等待 C++ Inference 启动（模型加载可能需要2-3分钟）..."
wait_for_port "$CPP_SERVER_PORT" "C++ Inference" 300

# 注册推理服务到 backend
LOCAL_IP="127.0.0.1"
curl -s -X POST "http://localhost:$BACKEND_PORT/api/inference/register" \
    -H 'Content-Type: application/json' \
    -d "{\"ip\": \"$LOCAL_IP\", \"port\": $CPP_SERVER_PORT, \"model_port\": $CPP_SERVER_PORT, \"model_type\": \"$CPP_MODE\", \"session_type\": \"release\", \"service_name\": \"o45-cpp\"}" \
    > /dev/null 2>&1 || warn "推理服务注册可能失败"

# ======================== [3/3] 启动 Frontend ========================
info "========== [3/3] 启动 Frontend =========="

FRONTEND_DIR="$WEBRTC_DIR/o45-frontend"

cd "$FRONTEND_DIR"

if [[ "$FRONTEND_MODE" == "prod" ]]; then
    info "Frontend 模式: 生产环境"
    VITE_CPP_MODE="$CPP_MODE" node serve-prod.mjs \
        --port "$FRONTEND_PORT" \
        --backend "$BACKEND_PORT" \
        --livekit "$LIVEKIT_PORT" \
        > "$LOG_DIR/frontend.log" 2>&1 &
else
    info "Frontend 模式: 开发环境"
    VITE_CPP_MODE="$CPP_MODE" pnpm run dev:external \
        > "$LOG_DIR/frontend.log" 2>&1 &
fi

echo $! > "$PID_DIR/frontend.pid"

wait_for_port "$FRONTEND_PORT" "Frontend" 30

# ======================== 完成 ========================
echo ""
echo "=============================================="
ok "所有服务启动成功！"
echo "=============================================="
echo ""
echo "访问地址:"
echo "  Frontend:  https://127.0.0.1:$FRONTEND_PORT"
echo "  Backend:   http://127.0.0.1:$BACKEND_PORT"
echo "  LiveKit:   ws://127.0.0.1:$LIVEKIT_PORT"
echo "  Inference: http://127.0.0.1:$CPP_SERVER_PORT"
echo ""
echo "日志文件:"
echo "  Backend:   $LOG_DIR/backend.log"
echo "  CPP:       $LOG_DIR/cpp_server.log"
echo "  Frontend:  $LOG_DIR/frontend.log"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 保持运行
trap 'echo ""; info "停止所有服务..."; kill_by_pidfile "$PID_DIR/frontend.pid"; kill_by_pidfile "$PID_DIR/cpp_server.pid"; pkill -f "minicpmo_cpp_http_server" || true; pkill -f "llama-server" || true; kill_by_pidfile "$PID_DIR/backend.pid"; ok "所有服务已停止"; exit 0' INT TERM

while true; do
    sleep 1
    # 检查服务是否还在运行
    any_running=false
    for pidfile in "$PID_DIR/backend.pid" "$PID_DIR/cpp_server.pid" "$PID_DIR/frontend.pid"; do
        if [[ -f "$pidfile" ]]; then
            pid=$(cat "$pidfile" 2>/dev/null)
            if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
                any_running=true
                break
            fi
        fi
    done
    if [[ "$any_running" != "true" ]]; then
        warn "所有后台服务已退出"
        break
    fi
done
