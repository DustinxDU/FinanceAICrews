#!/bin/bash
# ============================================
# FinanceAICrews - Docker 一键部署脚本
# ============================================
#
# 用途: 使用 Docker Compose 快速部署完整服务
# 使用: ./scripts/docker.sh [command]
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
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Docker Compose 命令 (兼容 v1 和 v2)
DOCKER_COMPOSE="docker compose"
if ! docker compose version &> /dev/null; then
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        log_error "Docker Compose 未安装"
        exit 1
    fi
fi

# 打印 Banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║     🐳 FinanceAICrews Docker Deployment                   ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查 .env 文件
check_env() {
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            log_warn ".env 文件不存在，从 .env.example 创建..."
            cp .env.example .env
            log_warn "请编辑 .env 文件配置你的 LLM API Key"
            echo ""
            read -p "是否现在编辑 .env 文件? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                ${EDITOR:-vim} .env
            fi
        else
            log_error ".env.example 文件不存在"
            exit 1
        fi
    fi
}

# 快速启动 (仅核心服务)
quick_start() {
    print_banner
    check_env

    log_step "启动核心服务 / Starting core services..."
    log_info "包含: PostgreSQL, Redis, Backend, Frontend"
    echo ""

    $DOCKER_COMPOSE up -d db redis
    log_info "等待数据库启动..."
    sleep 5

    # 运行数据库迁移
    log_info "运行数据库迁移..."
    $DOCKER_COMPOSE up -d backend
    sleep 3
    $DOCKER_COMPOSE exec -T backend alembic upgrade head 2>/dev/null || log_warn "迁移可能已完成或需要检查"

    # 导入初始数据
    log_info "导入初始数据..."
    $DOCKER_COMPOSE exec -T backend python scripts/seeding/seed_all.py 2>/dev/null || log_warn "Seed 可能已完成或需要检查"

    # 启动前端
    $DOCKER_COMPOSE up -d web
    log_info "等待服务启动..."
    sleep 5

    echo ""
    log_info "✅ 服务已启动!"
    echo ""
    echo -e "${BLUE}访问地址 / Access URLs:${NC}"
    echo "  Frontend: http://localhost:3000"
    echo "  Backend:  http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo ""
    echo -e "${YELLOW}查看日志: ./scripts/docker.sh logs${NC}"
    echo -e "${YELLOW}停止服务: ./scripts/docker.sh down${NC}"
}

# 完整启动 (包含 MCP 服务)
full_start() {
    print_banner
    check_env

    log_step "启动完整服务栈 / Starting full service stack..."
    log_info "包含: PostgreSQL, Redis, Backend, Frontend, MCP Servers, Gateway"
    echo ""

    # 构建镜像
    log_info "构建 Docker 镜像..."
    $DOCKER_COMPOSE build

    # 启动数据库和 Redis
    log_info "启动数据库服务..."
    $DOCKER_COMPOSE up -d db redis
    sleep 5

    # 启动后端并运行迁移
    log_info "启动后端服务..."
    $DOCKER_COMPOSE up -d backend
    sleep 3

    log_info "运行数据库迁移..."
    $DOCKER_COMPOSE exec -T backend alembic upgrade head 2>/dev/null || log_warn "迁移可能已完成"

    log_info "导入初始数据..."
    $DOCKER_COMPOSE exec -T backend python scripts/seeding/seed_all.py 2>/dev/null || log_warn "Seed 可能已完成"

    # 启动其他服务
    log_info "启动所有服务..."
    $DOCKER_COMPOSE up -d

    log_info "等待服务启动..."
    sleep 10

    echo ""
    log_info "✅ 完整服务栈已启动!"
    echo ""
    show_status
}

# 停止服务
stop_services() {
    log_info "停止所有服务 / Stopping all services..."
    $DOCKER_COMPOSE down
    log_info "✅ 服务已停止"
}

# 重启服务
restart_services() {
    log_info "重启服务 / Restarting services..."
    $DOCKER_COMPOSE restart
    log_info "✅ 服务已重启"
}

# 查看日志
show_logs() {
    SERVICE="${1:-}"
    if [ -z "$SERVICE" ]; then
        $DOCKER_COMPOSE logs -f --tail=100
    else
        $DOCKER_COMPOSE logs -f --tail=100 "$SERVICE"
    fi
}

# 显示状态
show_status() {
    echo -e "${BLUE}服务状态 / Service Status:${NC}"
    echo ""
    $DOCKER_COMPOSE ps
    echo ""

    echo -e "${BLUE}健康检查 / Health Check:${NC}"
    echo -n "  Database:  "
    $DOCKER_COMPOSE exec -T db pg_isready -U postgres &>/dev/null && echo -e "${GREEN}✓ Healthy${NC}" || echo -e "${RED}✗ Unhealthy${NC}"

    echo -n "  Redis:     "
    $DOCKER_COMPOSE exec -T redis redis-cli ping &>/dev/null && echo -e "${GREEN}✓ Healthy${NC}" || echo -e "${RED}✗ Unhealthy${NC}"

    echo -n "  Backend:   "
    curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null | grep -q "200" && echo -e "${GREEN}✓ Healthy${NC}" || echo -e "${YELLOW}○ Starting${NC}"

    echo -n "  Frontend:  "
    curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null | grep -q "200" && echo -e "${GREEN}✓ Healthy${NC}" || echo -e "${YELLOW}○ Starting${NC}"
    echo ""
}

# 运行数据库迁移
run_migrate() {
    log_info "运行数据库迁移 / Running database migrations..."
    $DOCKER_COMPOSE exec backend alembic upgrade head
    log_info "✅ 迁移完成"
}

# 运行 seed 脚本
run_seed() {
    log_info "导入初始数据 / Seeding database..."
    $DOCKER_COMPOSE exec backend python scripts/seeding/seed_all.py
    log_info "✅ 数据导入完成"
}

# 进入容器 shell
enter_shell() {
    SERVICE="${1:-backend}"
    log_info "进入 $SERVICE 容器..."
    $DOCKER_COMPOSE exec "$SERVICE" /bin/sh
}

# 清理所有数据
clean_all() {
    log_warn "⚠️  这将删除所有容器、镜像和数据卷!"
    read -p "确认删除? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "停止并删除容器..."
        $DOCKER_COMPOSE down -v --rmi local
        log_info "✅ 清理完成"
    else
        log_info "已取消"
    fi
}

# 重建服务
rebuild() {
    log_info "重建并重启服务 / Rebuilding services..."
    $DOCKER_COMPOSE down
    $DOCKER_COMPOSE build --no-cache
    $DOCKER_COMPOSE up -d
    log_info "✅ 重建完成"
}

# 打印帮助
print_help() {
    echo -e "${CYAN}FinanceAICrews Docker 部署工具${NC}"
    echo ""
    echo "使用方法: $0 <command>"
    echo ""
    echo -e "${BLUE}基础命令:${NC}"
    echo "  up          快速启动核心服务 (推荐)"
    echo "  up-full     启动完整服务栈 (含 MCP)"
    echo "  down        停止所有服务"
    echo "  restart     重启服务"
    echo "  status      查看服务状态"
    echo "  logs        查看日志 (可选: logs <service>)"
    echo ""
    echo -e "${BLUE}数据库命令:${NC}"
    echo "  migrate     运行数据库迁移"
    echo "  seed        导入初始数据"
    echo ""
    echo -e "${BLUE}维护命令:${NC}"
    echo "  build       构建 Docker 镜像"
    echo "  rebuild     重建并重启服务"
    echo "  shell       进入容器 shell (默认: backend)"
    echo "  clean       清理所有容器和数据"
    echo ""
    echo -e "${BLUE}示例:${NC}"
    echo "  $0 up              # 快速启动"
    echo "  $0 logs backend    # 查看后端日志"
    echo "  $0 shell db        # 进入数据库容器"
    echo ""
}

# 主函数
main() {
    case "${1:-help}" in
        up|start)
            quick_start
            ;;
        up-full|full)
            full_start
            ;;
        down|stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status|ps)
            show_status
            ;;
        logs)
            show_logs "$2"
            ;;
        build)
            log_info "构建 Docker 镜像..."
            $DOCKER_COMPOSE build
            log_info "✅ 构建完成"
            ;;
        rebuild)
            rebuild
            ;;
        migrate)
            run_migrate
        ;;
        seed)
            run_seed
            ;;
        shell|exec)
            enter_shell "$2"
            ;;
        clean)
            clean_all
            ;;
        help|--help|-h)
            print_help
            ;;
        *)
            log_error "未知命令: $1"
            echo ""
            print_help
            exit 1
            ;;
    esac
}

main "$@"
