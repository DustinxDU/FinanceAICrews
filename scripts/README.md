# Scripts Directory

FinanceAICrews 运维脚本集合，按功能分类组织。

## Directory Structure

```
scripts/
├── deployment/        # 服务启动和部署
│   ├── README.md
│   ├── start_all.sh
│   ├── start_backend.sh
│   ├── start_mcp.sh
│   └── docker_deploy.sh
│
├── seeding/          # 数据库初始化
│   ├── README.md
│   ├── seed_all.py           # 主入口
│   ├── seed_core_pack.py
│   ├── seed_builtin_providers.py
│   ├── seed_builtin_tool_mappings.py
│   ├── seed_skills_system.py
│   ├── provision_litellm_keys.py
│   ├── update_provider_mappings.py
│   └── validate_system_fixes.py
│
├── verification/     # 系统验证
│   ├── README.md
│   ├── verify_deployment.sh
│   ├── verify_memory_leak_fixes.sh
│   ├── verify_monitoring.sh    # 合并了 mvp + stack
│   └── verify_router_integration.py
│
├── init_mcp_providers.py    # MCP 初始化 (推荐)
├── sync_provider_mappings.py # 同步 capability mappings
├── cleanup_mcp_tools.py      # 清理多余工具
│
└── devtools/         # 开发工具 (参考)
    ├── init_llm_database.py
    ├── init_mcp_database.py
    └── ...
```

## MCP Provider Management

### 初始化 MCP Providers

```bash
# 首次初始化或重新同步
PYTHONPATH=. python scripts/init_mcp_providers.py

# 预览变更
PYTHONPATH=. python scripts/init_mcp_providers.py --dry-run
```

### 同步 Capability Mappings

```bash
# 同步所有 provider 的 mappings
PYTHONPATH=. python scripts/sync_provider_mappings.py

# 只同步特定 provider
PYTHONPATH=. python scripts/sync_provider_mappings.py --provider mcp:yfinance
```

### 清理多余工具

```bash
# 清理数据库中不存在于 server.py 的工具
PYTHONPATH=. python scripts/cleanup_mcp_tools.py

# 预览变更
PYTHONPATH=. python scripts/cleanup_mcp_tools.py --dry-run
```

## Quick Start

### 1. 首次部署

```bash
# 1. 启动基础设施
docker compose up -d db redis

# 2. 初始化数据
PYTHONPATH=. python scripts/seeding/seed_all.py

# 3. 初始化 MCP providers
PYTHONPATH=. python scripts/init_mcp_providers.py

# 4. 启动服务
./scripts/deployment/start_all.sh
```

### 2. 运行测试

```bash
# 测试脚本在 tests/ 目录下
./tests/run_coverage.sh
```

### 3. 验证部署

```bash
./scripts/verification/verify_deployment.sh
./scripts/verification/verify_monitoring.sh
```

## Environment Variables

```bash
# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/trading_agents

# Redis
FAIC_INFRA_REDIS_HOST=localhost
FAIC_INFRA_REDIS_PORT=6379

# LiteLLM
LITELLM_MASTER_KEY=sk-master-xxx

# 测试
FAIC_RUN_INTEGRATION_TESTS=true
```

## Guidelines

- **新增脚本**: 按功能放入对应子目录
- **一次性脚本**: 不要添加，用完即删
- **文档**: 每个脚本要有注释说明用途和参数
- **可执行**: `.sh` 脚本需要 `chmod +x`

## See Also

- [Tests Directory](../tests/README.md)
- [Documentation](../docs/)
- [CLAUDE.md](../CLAUDE.md)
