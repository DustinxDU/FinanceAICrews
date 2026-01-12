#!/bin/bash
# ============================================
# FinanceAICrews - 开发环境一键安装脚本
# ============================================
#
# 用途: 快速搭建本地开发环境
# 使用: ./scripts/setup.sh
#
# 支持系统: Linux, macOS
# 依赖: Python 3.10+, Node.js 18+, PostgreSQL, Redis
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 日志函数
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# 打印 Banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║     FinanceAICrews - Development Environment Setup        ║"
    echo "║                                                           ║"
    echo "║     🤖 Multi-Agent Financial Analysis Platform            ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

# 检查系统依赖
check_dependencies() {
    log_step "检查系统依赖 / Checking dependencies..."

    local missing=()

    # Python
    if check_command python3; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        log_info "Python: $PYTHON_VERSION ✓"
    else
        missing+=("python3")
    fi

    # Node.js
    if check_command node; then
        NODE_VERSION=$(node -v)
        log_info "Node.js: $NODE_VERSION ✓"
    else
        missing+=("node")
    fi

    # npm
    if check_command npm; then
        NPM_VERSION=$(npm -v)
        log_info "npm: $NPM_VERSION ✓"
    else
        missing+=("npm")
    fi

    # PostgreSQL (可选，可以用 Docker)
    if check_command psql; then
        log_info "PostgreSQL: $(psql --version | head -1) ✓"
    else
        log_warn "PostgreSQL 未安装 (可使用 Docker)"
    fi

    # Redis (可选，可以用 Docker)
    if check_command redis-cli; then
        log_info "Redis: $(redis-cli --version) ✓"
    else
        log_warn "Redis 未安装 (可使用 Docker)"
    fi

    # Docker (可选)
    if check_command docker; then
        log_info "Docker: $(docker --version | cut -d' ' -f3 | tr -d ',') ✓"
    else
        log_warn "Docker 未安装 (推荐安装)"
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "缺少必要依赖: ${missing[*]}"
        echo ""
        echo "请先安装以下依赖:"
        echo "  - Python 3.10+: https://www.python.org/downloads/"
        echo "  - Node.js 18+: https://nodejs.org/"
        exit 1
    fi
}

# 创建 Python 虚拟环境
setup_python_env() {
    log_step "设置 Python 虚拟环境 / Setting up Python virtual environment..."

    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_info "虚拟环境已创建"
    else
        log_info "虚拟环境已存在"
    fi

    source venv/bin/activate

    log_info "安装 Python 依赖..."
    pip install --upgrade pip -q
    pip install -r requirements.txt -q

    log_info "Python 依赖安装完成 ✓"
}

# 安装前端依赖
setup_frontend() {
    log_step "设置前端环境 / Setting up frontend..."

    cd "$PROJECT_ROOT/frontend"

    if [ ! -d "node_modules" ]; then
        log_info "安装前端依赖..."
        npm install
    else
        log_info "前端依赖已存在"
    fi

    cd "$PROJECT_ROOT"
    log_info "前端依赖安装完成 ✓"
}

# 配置环境变量
setup_env_file() {
    log_step "配置环境变量 / Setting up environment variables..."

    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_info "已从 .env.example 创建 .env 文件"
            log_warn "请编辑 .env 文件，填入你的 LLM API Key"
        else
            log_error ".env.example 文件不存在"
            exit 1
        fi
    else
        log_info ".env 文件已存在"
    fi
}

# 启动基础服务 (PostgreSQL + Redis)
start_infra_services() {
    log_step "启动基础服务 / Starting infrastructure services..."

    if check_command docker; then
        log_info "使用 Docker 启动 PostgreSQL 和 Redis..."
        docker compose up -d db redis 2>/dev/null || docker-compose up -d db redis 2>/dev/null || {
            log_warn "Docker Compose 启动失败，请手动启动数据库服务"
            return 1
        }

        log_info "等待服务启动..."
        sleep 5
        log_info "基础服务已启动 ✓"
    else
        log_warn "Docker 未安装，请确保 PostgreSQL 和 Redis 已手动启动"
        echo "  PostgreSQL: localhost:5432"
        echo "  Redis: localhost:6379"
    fi
}

# 初始化数据库
init_database() {
    log_step "初始化数据库 / Initializing database..."

    source venv/bin/activate

    # 运行 Alembic 迁移
    log_info "运行数据库迁移..."
    if alembic upgrade head 2>/dev/null; then
        log_info "数据库迁移完成 ✓"
    else
        log_warn "Alembic 迁移失败，可能需要检查数据库连接"
    fi

    # 运行 seed 脚本
    if [ -f "scripts/seeding/seed_all.py" ]; then
        log_info "导入初始数据..."
        if python scripts/seeding/seed_all.py 2>/dev/null; then
            log_info "初始数据导入完成 ✓"
        else
            log_warn "Seed 脚本执行失败，可能需要手动运行"
        fi
    fi

    log_info "数据库初始化完成 ✓"
}

# 打印完成信息
print_success() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}║     ✅ 安装完成! / Setup Complete!                        ║${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}下一步 / Next Steps:${NC}"
    echo ""
    echo "  1. 编辑 .env 文件，配置你的 LLM API Key:"
    echo "     ${CYAN}vim .env${NC}"
    echo ""
    echo "  2. 启动开发服务器:"
    echo "     ${CYAN}./scripts/dev.sh${NC}"
    echo ""
    echo "  3. 或者使用 Docker 一键部署:"
    echo "     ${CYAN}./scripts/docker.sh up${NC}"
    echo ""
    echo -e "${BLUE}访问地址 / Access URLs:${NC}"
    echo "  Frontend: http://localhost:3000"
    echo "  Backend:  http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo ""
}

# 主函数
main() {
    print_banner

    check_dependencies
    echo ""

    setup_python_env
    echo ""

    setup_frontend
    echo ""

    setup_env_file
    echo ""

    # 询问是否启动基础服务
    if check_command docker; then
        read -p "是否使用 Docker 启动 PostgreSQL 和 Redis? (Y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            start_infra_services
            echo ""
            init_database
            echo ""
        fi
    fi

    print_success
}

# 运行
main "$@"
