#!/bin/bash
# FinanceAI Platform - 一键启动脚本

cd "$(dirname "$0")/.."

echo "🚀 正在启动 FinanceAI Platform..."

# 存储后台进程 PID
BACKEND_PID=""

# 清理函数 - 在脚本退出时调用
cleanup() {
    echo ""
    echo "🛑 正在清理后台进程..."
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "停止后端进程 (PID: $BACKEND_PID)..."
        kill -TERM "$BACKEND_PID" 2>/dev/null || true
        sleep 2
        # 如果还活着，强制杀死
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            kill -9 "$BACKEND_PID" 2>/dev/null || true
        fi
    fi
    # 按模式杀死可能的残留 uvicorn 进程
    pkill -TERM -f "uvicorn.*backend\.app\.main:app" 2>/dev/null || true
    echo "✅ 清理完成"
}

# 关键：trap 必须在启动任何后台进程之前设置
trap cleanup EXIT INT TERM

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "⚠️  未检测到虚拟环境，尝试创建..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📦 安装后端依赖..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 启动后端 (注意：nohup 模式下不使用 --reload，避免 reloader 孤儿进程)
echo "🧠 启动后端服务 (端口 8000)..."
echo "⚠️  注意: nohup 模式下禁用 --reload，如需热重载请使用 start_backend.sh"
nohup PYTHONUNBUFFERED=1 \
  FINANCEAI_STORAGE_DIR="${FINANCEAI_STORAGE_DIR:-/tmp/financeaicrews-data}" \
  python -m uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  > backend.log 2>&1 &
BACKEND_PID=$!
echo "后端 PID: $BACKEND_PID"

# 等待后端启动
echo "等待后端服务启动..."
sleep 3
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "❌ 后端启动失败，请检查 backend.log"
    exit 1
fi
echo "✅ 后端服务已启动"

# 启动前端
echo "💻 启动前端服务 (端口 3000)..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "⚠️  未检测到 node_modules，安装前端依赖..."
    npm install
fi

# 前台运行前端，Ctrl+C 会触发 trap cleanup
echo "前端正在启动，请稍候..."
echo "💡 提示: 按 Ctrl+C 可同时停止前端和后端服务"
npm run dev
