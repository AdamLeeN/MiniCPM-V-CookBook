#!/bin/bash
# ============================================================================
# MiniCPM-o 服务停止脚本
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }

PROJECT_DIR="${1:-$HOME/.minicpmo}"
PID_DIR="$PROJECT_DIR/.pids"

info "停止所有服务..."

kill_by_pidfile() {
    local pidfile=$1
    local name=$2
    if [[ -f "$pidfile" ]]; then
        local pid=$(cat "$pidfile" 2>/dev/null)
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            info "停止 $name (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -9 "$pid" 2>/dev/null || true
            ok "$name 已停止"
        fi
        rm -f "$pidfile"
    fi
}

# 停止 Frontend
kill_by_pidfile "$PID_DIR/frontend.pid" "Frontend"
pkill -f "serve-prod.mjs" 2>/dev/null || true

# 停止 C++ Inference
kill_by_pidfile "$PID_DIR/cpp_server.pid" "C++ Inference"
pkill -f "minicpmo_cpp_http_server" 2>/dev/null || true
pkill -f "llama-server" 2>/dev/null || true

# 停止 Backend
kill_by_pidfile "$PID_DIR/backend.pid" "Backend"

ok "所有服务已停止"
