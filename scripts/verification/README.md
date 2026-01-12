# Verification Scripts

系统验证和健康检查脚本。

## Scripts

| Script | Description |
|--------|-------------|
| `verify_deployment.sh` | 部署完整性验证 |
| `verify_memory_leak_fixes.sh` | 内存泄漏修复验证 |
| `verify_monitoring.sh` | 监控堆栈验证 (MVP/Full) |
| `verify_router_integration.py` | LLM 路由集成验证 |

## Usage

```bash
# 部署验证
./scripts/verification/verify_deployment.sh

# 内存泄漏测试
./scripts/verification/verify_memory_leak_fixes.sh

# 监控验证
./scripts/verification/verify_monitoring.sh           # 完整验证
./scripts/verification/verify_monitoring.sh mvp       # MVP 检查
./scripts/verification/verify_monitoring.sh config    # 仅配置文件

# 路由集成测试
PYTHONPATH=. python scripts/verification/verify_router_integration.py
```

## Common Issues

- **PostgreSQL not running**: 启动 `docker compose up -d db`
- **Redis not running**: 启动 `docker compose up -d redis`
- **LiteLLM not configured**: 运行 `python scripts/seeding/provision_litellm_keys.py`
