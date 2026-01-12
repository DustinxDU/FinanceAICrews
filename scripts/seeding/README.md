# Seeding Scripts

数据库初始化和种子数据导入脚本。

## Scripts

| Script | Description |
|--------|-------------|
| `seed_all.py` | **主入口** - 初始化所有核心数据 |
| `seed_core_pack.py` | 核心数据初始化 (Agents, Tasks, Crews) |
| `seed_builtin_providers.py` | 内置 LLM Provider 配置 |
| `seed_builtin_tool_mappings.py` | 内置工具映射配置 |
| `seed_skills_system.py` | Skills 系统初始化 |
| `provision_litellm_keys.py` | LiteLLM 虚拟密钥配置 |
| `update_provider_mappings.py` | Provider 映射更新 |
| `validate_system_fixes.py` | 系统修复验证 |

## Usage

```bash
# 初始化所有数据 (推荐)
PYTHONPATH=/home/dustin/stock/FinanceAICrews:$PYTHONPATH python scripts/seeding/seed_all.py

# 单独初始化各个模块
PYTHONPATH=. python scripts/seeding/seed_core_pack.py
PYTHONPATH=. python scripts/seeding/seed_builtin_providers.py --execute
PYTHONPATH=. python scripts/seeding/seed_skills_system.py

# LiteLLM 密钥配置
python scripts/seeding/provision_litellm_keys.py reconcile --limit 50
```

## Order

初始化顺序（如果单独运行）:

1. `seed_core_pack.py` - 基础配置
2. `seed_builtin_providers.py` - Provider 配置
3. `seed_builtin_tool_mappings.py` - 工具映射
4. `seed_skills_system.py` - Skills
5. `provision_litellm_keys.py` - 密钥配置

## Environment Variables

```bash
DATABASE_URL      # PostgreSQL 连接字符串
LITELLM_MASTER_KEY  # LiteLLM 管理密钥
```
