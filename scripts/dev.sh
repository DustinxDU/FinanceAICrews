#!/bin/bash
# ============================================
# FinanceAICrews - 开发服务器启动脚本
# ============================================
#
# 用途: 启动本地开发服务器 (后端 + 前端)
# 使用: ./scripts/dev.sh [backend|frontend|all]
#
# ============================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 存储后台进程 PID
BACKEND_PID=""

# 清理函数
cleanup() {
    echo ""
    log_info "正在停止服务 / Stopping services..."

    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill -TERM "$BACKEND_PID" 2>/dev/null || true
        sleep 2
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            kill -9 "$BACKEND_PID" 2>/dev/null || true
        fi
    fi

    # 清理可能的残留进程
    pkill -TERM -f "uvicorn.*backend\.app\.main:app" 2>/dev/null || true

    log_info "服务已停止 ✓"
}

trap cleanup EXIT INT TERM

# 检查环境
check_env() {
    if [ ! -f ".env" ]; then
        log_error ".env 文件不存在，请先运行 ./scripts/setup.sh"
        exit 1
    fi

    if [ ! -d "venv" ]; then
        log_error "虚拟环境不存在，请先运行 ./scripts/setup.sh"
        exit 1
    fi
}

# 启动后端
start_backend() {
    log_info "启动后端服务 / Starting backend (port 8000)..."

    source venv/bin/activate

    PYTHONUNBUFFERED=1 python -m uvicorn backend.app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        &
    BACKEND_PID=$!

    sleep 3
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        log_info "后端服务已启动 ✓ (PID: $BACKEND_PID)"
    else
        log_error "后端启动失败"
        exit 1
    fi
}

# 启动前端
start_frontend() {
    log_info "启动前端服务 / Starting frontend (port 3000)..."

    cd "$PROJECT_ROOT/frontend"

    if [ ! -d "node_modules" ]; then
        log_warn "安装前端依赖..."
        npm install
    fi

    npm run dev
}

# 只启动后端
backend_only() {
    check_env
    source venv/bin/activate

    log_info "启动后端服务 (热重载模式)..."
    PYTHONUNBUFFERED=1 python -m uvicorn backend.app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload
}

# 只启动前端
frontend_only() {
    log_info "启动前端服务..."
    cd "$PROJECT_ROOT/frontend"
    npm run dev
}

# 打印帮助
print_help() {
    echo -e "${CYAN}FinanceAICrews 开发服务器${NC}"
    echo ""
    echo "使用方法: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  all       启动后端和前端 (默认)"
    echo "  backend   只启动后端"
    echo "  frontend  只启动前端"
    echo "  help      显示帮助"
    echo ""
    echo "示例:"
    echo "  $0              # 启动所有服务"
    echo "  $0 backend      # 只启动后端"
    echo "  $0 frontend     # 只启动前端"
    echo ""
    echo -e "${YELLOW}提示: 按 Ctrl+C 停止服务${NC}"
}

# 主函数
main() {
    case "${1:-all}" in
        all)
            check_env
            echo -e "${CYAN}"
            echo "╔═══════════════════════════════════════════════════════════╗"
            echo "║     🚀 FinanceAICrews Development Server                  ║"
            echo "╚═══════════════════════════════════════════════════════════╝"
            echo -e "${NC}"
    t_backend
            echo ""
            echo -e "${BLUE}访问地址:${NC}"
            echo "  Frontend: http://localhost:3000"
            echo "  Backend:  http://localhost:8000"
            echo "  API Docs: http://localhost:8000/docs"
            echo ""
            echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"
            echo ""
            start_frontend
            ;;
        backend)
            backend_only
            ;;
        frontend)
        frontend_only
            ;;
        help|--help|-h)
            print_help
            ;;
        *)
            log_error "未知命令: $1"
            print_help
            exit 1
            ;;
    esac
}

main "$@"
