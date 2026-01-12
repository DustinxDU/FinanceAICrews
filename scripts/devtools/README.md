# DevTools Directory

开发阶段的一次性工具和参考脚本。**这些脚本通常只使用一次**，用于：

- 数据初始化
- MCP 工具同步
- 配置验证
- 生产环境调试

## Scripts

| Script | Purpose |
|--------|---------|
| `init_llm_database.py` | 初始化 LLM 数据库 |
| `init_mcp_database.py` | 初始化 MCP 数据库 |
| `init_production_data.py` | 生产数据初始化 |
| `sync_knowledge_sources.py` | 知识源同步 |
| `seed_knowledge_sources.py` | 知识源种子数据 |
| `start_mcp_servers.py` | 启动 MCP 服务器 |
| `akshare_server.py` | Akshare MCP 服务器 |
| `discover_openbb_tools.py` | 发现 OpenBB 工具 |
| `validate_config.py` | 配置验证 |
| `verify_production_data.py` | 生产数据验证 |
| `yaml_sync.py` | YAML 配置同步 |
| `SeedGraphGenerator.py` | 种子图生成器 |
| `mcp_examples.py` | MCP 示例 |
| `gen_token.py` | 生成测试 Token |

## Usage

```bash
# 初始化 MCP providers (推荐使用根目录脚本)
PYTHONPATH=. python scripts/init_mcp_providers.py

# 验证配置
python scripts/devtools/validate_config.py
```

## Warning

这些脚本可能包含硬编码的配置或路径，只适用于特定场景。使用前请检查脚本内容。
