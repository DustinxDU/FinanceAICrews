#!/bin/bash
# 启动 Prometheus + Grafana 监控栈
# 用法: ./start.sh [up|down|logs|status]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_FILE="docker-compose.yml"

action="${1:-up}"

case "$action" in
    up)
        echo "🚀 启动监控栈..."
        docker-compose -f "$COMPOSE_FILE" up -d
        
        echo ""
        echo "✅ 服务已启动:"
        echo "   - Prometheus: http://localhost:9090"
        echo "   - Grafana:    http://localhost:3000 (admin/admin)"
        echo ""
        echo "📊 验证命令:"
        echo "   curl http://localhost:9090/api/v1/status/config | head -20"
        echo "   curl http://localhost:3000/api/health"
        ;;
        
    down)
        echo "🛑 停止监控栈..."
        docker-compose -f "$COMPOSE_FILE" down
        ;;
        
    logs)
        echo "📋 查看日志..."
        docker-compose -f "$COMPOSE_FILE" logs -f
        ;;
        
    status)
        echo "📊 服务状态:"
        docker-compose -f "$COMPOSE_FILE" ps
        ;;
        
    *)
        echo "用法: $0 [up|down|logs|status]"
        exit 1
        ;;
esac
