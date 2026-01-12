# Deployment Scripts

服务启动和部署相关脚本。

## Scripts

| Script | Description |
|--------|-------------|
| `start_all.sh` | 启动所有服务 (Backend + MCP Servers) |
| `start_backend.sh` | 启动 FastAPI 后端服务 |
| `start_mcp.sh` | 启动 MCP 数据服务器 |
| `docker_deploy.sh` | Docker 容器化部署脚本 |

## Usage

```bash
# 启动所有服务
./scripts/deployment/start_all.sh

# 仅启动后端
./scripts/deployment/start_backend.sh

# 仅启动 MCP 服务器
./scripts/deployment/start_mcp.sh

# Docker 部署
./scripts/deployment/docker_deploy.sh
```

## Requirements

- Python 3.12+ 环境
- Docker & Docker Compose (docker_deploy.sh)
- 依赖服务: PostgreSQL, Redis
