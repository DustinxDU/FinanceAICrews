#!/bin/bash
# ============================================
# FinanceAICrews Docker 部署脚本
# ============================================
# 
# 使用方法:
#   ./scripts/docker_deploy.sh [build|up|down|logs|status]
#
# 架构:
#   Browser → Nginx Gateway(:80) → Frontend(:3000) / Backend(:8000) → PostgreSQL
# ============================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

case "${1:-help}" in
    build)
        log_info "构建所有 Docker 镜像..."
        log_info "Step 1/3: 构建后端..."
        docker compose build backend
        log_info "Step 2/3: 构建前端 (standalone 模式)..."
        docker compose build web
        log_info "Step 3/3: 拉取 Nginx..."
        docker compose pull gateway
        log_info "✅ 构建完成!"
        ;;
    
    up)
        log_info "启动所有服务..."
        docker compose up -d gateway web backend db
        log_info "等待服务启动..."
        sleep 5
        log_info "服务状态:"
        docker compose ps
        echo ""
        log_info "✅ 服务已启动!"
        log_info "访问地址: http://localhost"
        log_info "API 文档: http://localhost/docs"
        ;;
    
    down)
        log_info "停止所有服务..."
        docker compose down
        log_info "✅ 服务已停止"
        ;;
    
    logs)
        SERVICE="${2:-}"
        if [ -z "$SERVICE" ]; then
            docker compose logs -f --tail=100
        else
            docker compose logs -f --tail=100 "$SERVICE"
        fi
        ;;
    
    status)
        log_info "服务状态:"
        docker compose ps
        echo ""
        log_info "健康检查:"
        echo -n "  Gateway:  "; curl -s -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null || echo "N/A"
        echo -n "  Backend:  "; curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null || echo "N/A"
        echo -n "  API:      "; curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/knowledge/marketplace 2>/dev/null || echo "N/A"
        echo ""
        ;;
    
    rebuild)
        log_info "重建并重启服务..."
        docker compose down
        docker compose build --no-cache
        docker compose up -d gateway web backend db
        log_info "✅ 重建完成!"
        ;;
    
    migrate)
        log_info "运行数据库迁移..."
        docker compose exec backend alembic upgrade head
        log_info "✅ 迁移完成!"
        ;;
    
    seed)
        log_info "导入知识源数据..."
        docker compose exec backend python scripts/seed_knowledge_sources.py
        log_info "✅ 导入完成!"
        ;;
    
    shell)
        SERVICE="${2:-backend}"
        log_info "进入 $SERVICE 容器..."
        docker compose exec "$SERVICE" /bin/sh
        ;;
    
    help|*)
        echo "FinanceAICrews Docker 部署工具"
        echo ""
        echo "使用方法: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  build     构建所有 Docker 镜像"
        echo "  up        启动所有服务"
        echo "  down      停止所有服务"
        echo "  logs      查看日志 (可选: logs <service>)"
        echo "  status    查看服务状态和健康检查"
        echo "  rebuild   重建并重启所有服务"
        echo "  migrate   运行数据库迁移"
        echo "  seed      导入知识源数据"
        echo "  shell     进入容器 (默认: backend)"
        echo ""
        echo "示例:"
        echo "  $0 build          # 构建镜像"
        echo "  $0 up             # 启动服务"
        echo "  $0 logs gateway   # 查看 Nginx 日志"
        echo "  $0 status         # 检查状态"
        ;;
esac
