#!/bin/bash
# AI Berkshire 个人投资理财工作台 - 启动脚本
# 用法: ./start.sh [start|stop|status]

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_PORT=8000
FRONTEND_PORT=3000
NODE_BIN="${NODE_BIN:-$(command -v node || true)}"
PYTHON_BIN="${PYTHON_BIN:-}"

if [ -z "$NODE_BIN" ] && [ -x "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node" ]; then
    NODE_BIN="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
fi

ensure_backend_python() {
    if [ -d "$BACKEND_DIR/venv" ] && [ ! -x "$BACKEND_DIR/venv/bin/python" ]; then
        rm -rf "$BACKEND_DIR/venv"
    fi

    if [ -z "$PYTHON_BIN" ]; then
        for candidate in python3.12 python3.11 python3.10 /usr/bin/python3 python3; do
            if command -v "$candidate" >/dev/null 2>&1 || [ -x "$candidate" ]; then
                version="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
                case "$version" in
                    3.9|3.10|3.11|3.12)
                        PYTHON_BIN="$(command -v "$candidate" 2>/dev/null || echo "$candidate")"
                        break
                        ;;
                esac
            fi
        done
    fi

    if [ -x "$BACKEND_DIR/venv/bin/python" ]; then
        venv_version="$("$BACKEND_DIR/venv/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
        if [ "$venv_version" != "3.13" ]; then
            PYTHON_BIN="$BACKEND_DIR/venv/bin/python"
        else
            rm -rf "$BACKEND_DIR/venv"
        fi
    fi

    if [ -z "$PYTHON_BIN" ]; then
        echo -e "${RED}❌ 未找到兼容的 Python 3.9-3.12，请先安装 Python 3.10+ 或设置 PYTHON_BIN=/path/to/python3${NC}"
        exit 1
    fi

    if "$PYTHON_BIN" -c "import uvicorn, fastapi, sqlalchemy, bcrypt" >/dev/null 2>&1; then
        return
    fi

    echo -e "${YELLOW}后端依赖未安装，正在创建/更新本地 venv...${NC}"
    cd "$BACKEND_DIR"
    if [ -x "venv/bin/python" ]; then
        venv_version="$(venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
        if [ "$venv_version" = "3.13" ]; then
            mv venv "venv.py313.$(date +%Y%m%d%H%M%S)"
        fi
    fi
    if [ ! -x "venv/bin/python" ]; then
        "$PYTHON_BIN" -m venv venv
    fi
    PYTHON_BIN="$BACKEND_DIR/venv/bin/python"
    "$PYTHON_BIN" -m pip install --upgrade pip
    "$PYTHON_BIN" -m pip install -r requirements.txt
}

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

status() {
    echo "=== 服务状态 ==="
    backend_pid=$(lsof -i :$BACKEND_PORT 2>/dev/null | grep LISTEN | awk '{print $2}' | head -1)
    frontend_pid=$(lsof -i :$FRONTEND_PORT 2>/dev/null | grep LISTEN | awk '{print $2}' | head -1)
    
    if [ -n "$backend_pid" ]; then
        echo -e "${GREEN}后端 (FastAPI)${NC}: PID $backend_pid | http://localhost:$BACKEND_PORT"
    else
        echo -e "${RED}后端 (FastAPI)${NC}: 未运行"
    fi
    
    if [ -n "$frontend_pid" ]; then
        echo -e "${GREEN}前端 (Next.js)${NC}: PID $frontend_pid | http://localhost:$FRONTEND_PORT"
    else
        echo -e "${RED}前端 (Next.js)${NC}: 未运行"
    fi
}

start_backend() {
    echo -e "${YELLOW}启动后端...${NC}"
    ensure_backend_python
    cd "$BACKEND_DIR"
    nohup "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT > "$PROJECT_ROOT/backend.log" 2>&1 &
    backend_job=$!
    disown "$backend_job" 2>/dev/null || true
    sleep 5
    backend_pid=$(lsof -i :$BACKEND_PORT 2>/dev/null | grep LISTEN | awk '{print $2}' | head -1)
    if [ -n "$backend_pid" ]; then
        echo -e "${GREEN}✅ 后端已启动${NC} (PID: $backend_pid)"
    else
        echo -e "${RED}❌ 后端启动失败${NC}"
        cat "$PROJECT_ROOT/backend.log" | tail -10
        exit 1
    fi
}

start_frontend() {
    echo -e "${YELLOW}启动前端...${NC}"
    cd "$FRONTEND_DIR"
    if [ -z "$NODE_BIN" ]; then
        echo -e "${RED}❌ 未找到 Node.js，请先安装 Node.js 或设置 NODE_BIN=/path/to/node${NC}"
        exit 1
    fi
    if [ ! -d ".next" ]; then
        echo -e "${YELLOW}未找到生产构建，正在执行 Next.js build...${NC}"
        "$NODE_BIN" ./node_modules/next/dist/bin/next build
    fi
    nohup "$NODE_BIN" ./node_modules/next/dist/bin/next start -p $FRONTEND_PORT > "$PROJECT_ROOT/frontend.log" 2>&1 &
    frontend_job=$!
    disown "$frontend_job" 2>/dev/null || true
    sleep 5
    frontend_pid=$(lsof -i :$FRONTEND_PORT 2>/dev/null | grep LISTEN | awk '{print $2}' | head -1)
    if [ -n "$frontend_pid" ]; then
        echo -e "${GREEN}✅ 前端已启动${NC} (PID: $frontend_pid)"
    else
        echo -e "${RED}❌ 前端启动失败${NC}"
        cat "$PROJECT_ROOT/frontend.log" | tail -10
        exit 1
    fi
}

stop() {
    echo -e "${YELLOW}停止服务...${NC}"
    for pid in $(lsof -i :$BACKEND_PORT 2>/dev/null | grep LISTEN | awk '{print $2}'); do
        kill -9 $pid 2>/dev/null || true
    done
    for pid in $(lsof -i :$FRONTEND_PORT 2>/dev/null | grep LISTEN | awk '{print $2}'); do
        kill -9 $pid 2>/dev/null || true
    done
    sleep 2
    echo -e "${GREEN}✅ 服务已停止${NC}"
}

start() {
    stop 2>/dev/null || true
    sleep 1
    start_backend
    start_frontend
    
    echo ""
    echo "=========================================="
    echo -e "${GREEN}🚀 AI Berkshire 个人工作台已启动！${NC}"
    echo "=========================================="
    echo ""
    echo "  前端: http://localhost:$FRONTEND_PORT"
    echo "  后端: http://localhost:$BACKEND_PORT"
    echo ""
    echo "  本地账号:"
    echo "    用户名: demo"
    echo "    密码:   demo123456"
    echo ""
    echo "  使用 Ctrl+C 停止此脚本，服务会在后台继续运行"
    echo "  用 ./start.sh stop 彻底停止服务"
    echo "=========================================="
    
    # 保持脚本运行，直到用户按 Ctrl+C
    trap 'echo ""; echo "脚本已退出，服务仍在后台运行"; exit 0' INT
    while true; do sleep 1; done
}

case "${1:-start}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    *)
        echo "用法: ./start.sh [start|stop|status]"
        exit 1
        ;;
esac
