# FinanceAICrews

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## 🤖 Multi-Agent Financial Analysis Platform

> An experimental multi-agent financial analysis platform built on CrewAI

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)

### ⚠️ Disclaimer

This is a **personal experimental project** - my first attempt at building a multi-agent financial analysis system.

- ✅ Fully open source, Apache 2.0 License
- ✅ Inspired by many great open source projects
- ❌ Code may be incomplete in places
- ❌ Documentation may not be up to date
- ⏳ Will improve over time

**Not financial advice. Use at your own risk.**

### ✨ Features

- **Multi-Agent Collaboration** - Fundamental, technical, and sentiment analysis agents working together
- **Multi-LLM Support** - OpenAI, Anthropic, DeepSeek, Zhipu AI, and more
- **MCP Protocol** - Integrated market data via yfinance, akshare
- **Self-Hosted** - One-click Docker deployment
- **Subscription-Free** - Community edition with full features

### 🚀 Quick Start

#### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/FinanceAICrews.git
cd FinanceAICrews

# Configure environment
cp .env.example .env
# Edit .env and add your LLM API key

# Start with Docker
./scripts/docker.sh up

# Access
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

#### Option 2: Local Development

```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/FinanceAICrews.git
cd FinanceAICrews

# Run setup script
./scripts/setup.sh

# Configure your LLM API key
vim .env

# Start development server
./scripts/dev.sh

# Access
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
```

### 📦 Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, CrewAI, SQLAlchemy, Alembic |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Database | PostgreSQL, Redis |
| Data | MCP Protocol (yfinance, akshare) |
| Deployment | Docker, Docker Compose |

### ⚙️ Configuration

Edit `.env` file to configure:

```bash
# Required
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
JWT_SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-encryption-key

# LLM Configuration (choose one)
# Option A: Single provider for all
FAIC_LLM_DEFAULT_PROVIDER=openai
FAIC_LLM_DEFAULT_MODEL=gpt-4o-mini
FAIC_LLM_DEFAULT_API_KEY=sk-...

# Option B: Different providers per scope
FAIC_LLM_COPILOT_PROVIDER=openai
FAIC_LLM_SCAN_PROVIDER=deepseek
FAIC_LLM_AGENTS_PROVIDER=anthropic

# Community Edition (enables all features)
FAIC_SELF_HOSTED=true
```

See `.env.example` for full configuration options.

### 📁 Project Structure

```
FinanceAICrews/
├── AICrews/          # Agent engine & business logic
├── backend/          # FastAPI API layer
├── frontend/         # Next.js frontend
├── config/           # YAML configurations
├── docker/           # Docker & MCP servers
├── scripts/          # Deployment scripts
└── alembic/          # Database migrations
```

### 🛠️ Scripts

| Script | Description |
|--------|-------------|
| `./scripts/setup.sh` | One-click development setup |
| `./scripts/dev.sh` | Start development server |
| `./scripts/docker.sh up` | Docker quick start |
| `./scripts/docker.sh up-full` | Docker full stack (with MCP) |
| `./scripts/docker.sh down` | Stop all services |

### 🙏 Acknowledgments

- [CrewAI](https://www.crewai.com/) - Multi-agent framework
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol
- [yfinance](https://github.com/ranaroussi/yfinance) - Financial data
- And all the amazing open source community 🙏

### 📄 License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

---

<a name="中文"></a>
## 🤖 多智能体金融分析平台

> 基于 CrewAI 的实验性多智能体金融分析平台

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)

### ⚠️ 免责声明

这是一个**个人实验性项目** - 我第一次尝试构建多智能体金融分析系统。

- ✅ 完全开源，Apache 2.0 许可证
- ✅ 参考了很多优秀的开源项目
- ❌ 代码可能有不完善的地方
- ❌ 文档可能不够及时
- ⏳ 会慢慢优化改进

**本项目不构成投资建议，使用风险自负。**

### ✨ 主要特性

- **多智能体协作** - 基本面、技术面、情绪面分析智能体协同工作
- **多 LLM 支持** - OpenAI、Anthropic、DeepSeek、智谱 AI 等
- **MCP 协议** - 通过 yfinance、akshare 集成市场数据
- **自托管部署** - Docker 一键部署
- **无需订阅** - 社区版拥有完整功能

### 🚀 快速开始

#### 方式一：Docker 部署（推荐）

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/FinanceAICrews.git
cd FinanceAICrews

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 LLM API Key

# Docker 启动
./scripts/docker.sh up

# 访问
# 前端: http://localhost:3000
# API 文档: http://localhost:8000/docs
```

#### 方式二：本地开发

```bash
# 克隆并安装
git clone https://github.com/YOUR_USERNAME/FinanceAICrews.git
cd FinanceAICrews

# 运行安装脚本
./scripts/setup.sh

# 配置 LLM API Key
vim .env

# 启动开发服务器
./scripts/dev.sh

# 访问
# 前端: http://localhost:3000
# 后端: http://localhost:8000
```

### 📦 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI, CrewAI, SQLAlchemy, Alembic |
| 前端 | Next.js 14, TypeScript, Tailwind CSS |
| 数据库 | PostgreSQL, Redis |
| 数据源 | MCP 协议 (yfinance, akshare) |
| 部署 | Docker, Docker Compose |

### ⚙️ 配置说明

编辑 `.env` 文件进行配置：

```bash
# 必填项
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
JWT_SECRET_KEY=你的密钥
ENCRYPTION_KEY=你的加密密钥

# LLM 配置（选择一种方式）
# 方式 A：所有场景使用同一个提供商
FAIC_LLM_DEFAULT_PROVIDER=openai
FAIC_LLM_DEFAULT_MODEL=gpt-4o-mini
FAIC_LLM_DEFAULT_API_KEY=sk-...

# 方式 B：不同场景使用不同提供商
FAIC_LLM_COPILOT_PROVIDER=openai
FAIC_LLM_SCAN_PROVIDER=deepseek
FAIC_LLM_AGENTS_PROVIDER=anthropic

# 社区版模式（启用全部功能）
FAIC_SELF_HOSTED=true
```

完整配置选项请参考 `.env.example`。

### 📁 项目结构

```
FinanceAICrews/
├── AICrews/          # 智能体引擎和业务逻辑
├── backend/          # FastAPI API 层
├── frontend/         # Next.js 前端
├── config/           # YAML 配置文件
├── docker/           # Docker 和 MCP 服务
├── scripts/          # 部署脚本
└── alembic/          # 数据库迁移
```

### 🛠️ 常用脚本

| 脚本 | 说明 |
|------|------|
| `./scripts/setup.sh` | 一键安装开发环境 |
| `./scripts/dev.sh` | 启动开发服务器 |
| `./scripts/docker.sh up` | Docker 快速启动 |
| `./scripts/docker.sh up-full` | Docker 完整启动（含 MCP） |
| `./scripts/docker.sh down` | 停止所有服务 |

### 🙏 致谢

- [CrewAI](https://www.crewai.com/) - 多智能体框架
- [MCP](https://modelcontextprotocol.io/) - 模型上下文协议
- [yfinance](https://github.com/ranaroussi/yfinance) - 金融数据
- 以及所有开源社区的大神们 🙏

### 📄 许可证

Apache License 2.0 - 详见 [LICENSE](LICENSE)

---

## 💬 交流反馈

- Issues: [GitHub Issues](https://github.com/YOUR_USERNAME/FinanceAICrews/issues)
- 欢迎提交 PR 和建议！

---

*Made with ❤️ and lots of ☕*
