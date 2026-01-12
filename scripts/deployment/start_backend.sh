#!/bin/bash
# FinanceAI Platform - Backend 启动脚本

cd "$(dirname "$0")/.."

echo "🚀 启动 FinanceAI Platform 后端服务..."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 错误: 虚拟环境不存在，请先运行 python -m venv venv"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查端口占用
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  警告: 端口 8000 已被占用"
    read -p "是否停止现有服务并重启？(y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🛑 停止现有服务..."
        pkill -f "uvicorn backend.app.main:app"
        sleep 2
    else
        echo "❌ 取消启动"
        exit 1
    fi
fi

# 启动后端服务
echo "▶️  启动后端服务 (http://0.0.0.0:8000)..."
PYTHONUNBUFFERED=1 \
FINANCEAI_STORAGE_DIR="${FINANCEAI_STORAGE_DIR:-/tmp/financeaicrews-data}" \
python -m uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --reload-exclude "*.log" \
  --reload-exclude "*.db" \
  --reload-exclude "*.db-wal" \
  --reload-exclude "*.db-shm" \
  --reload-exclude "*.json" \
  --reload-exclude ".data/*" \
  --reload-exclude ".data/**" \
  --reload-exclude ".crewai/*" \
  --reload-exclude "logs/*" \
  --reload-exclude "outputs/*" \
  --reload-exclude "__pycache__" \
  --reload-exclude ".pytest_cache"

# 如果服务异常退出
echo "⚠️  后端服务已停止"
