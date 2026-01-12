# AICrews（智能体引擎）开发规范

> **Scope**：本文件适用于 `AICrews/` 目录（智能体引擎 + 业务服务 + 工具封装）。目标：让任何 Agent/开发者快速做出一致、可维护、可扩展的引擎改动。
>
> **Philosophy**：Code is Engine, Config is Soul（配置优先；提示词/编排/开关应由配置驱动，而不是写死在代码里）。

## TL;DR（必须遵守）

1. **配置优先**：新增/调整 Agent 人设、Task 流程、Crew 拓扑，优先改 `config/agents/*.yaml`（模板/种子）或数据库配置（见下文“配置源”），避免改代码。
2. **分层清晰**：`backend/` 只做 API 编排；`AICrews/` 负责引擎与服务实现；`AICrews` 不应 import `backend`。
3. **运行时装配走 DB**：Crew 装配由 `AICrews/application/crew/assembler.py` 从 `CrewDefinition/AgentDefinition/TaskDefinition` 等表读取并组装为 CrewAI 对象。
4. **YAML 是“种子/模板”**：`config/agents/agents.yaml`、`config/agents/tasks.yaml`、`config/agents/crews.yaml` 主要用于系统模板/初始化/同步；不保证直接被运行时读取。
5. **Schema 统一在 `AICrews/schemas/*`（Pydantic v2）**：不要在 services/tools/backend 重复定义同名 schema。
6. **工具要“可控、可观测、可降级”**：工具实现放 `AICrews/tools/*`，统一经 `AICrews/tools/registry/tool_registry.py` 暴露；必须有超时/错误处理/可序列化输出，禁止泄露密钥与内部堆栈到返回值。
7. **LLM 只走统一入口**：通过 `AICrews/llm/unified_manager.py` 获取/同步模型与配置；禁止散落的 provider SDK 直连调用。
8. **数据库访问要一致**：
   - 同步：`AICrews/database/db_manager.DBManager().get_session()`
   - 异步：`AICrews/database/db_manager.get_db_session()`
   - 禁止在 import 时创建 engine/连接；写操作确保 `commit()`，异常确保 `rollback()`。
9. **常驻任务可启停**：长循环/订阅同步/归档等必须提供 `start/stop`，由 `backend/app/core/lifespan.py` 统一编排启停。
10. **遵守数据架构**：`assets → realtime_quotes → market_prices`；图表数据“透传 + Redis 5min TTL”，不要私自落库（除非明确新增 layer 并同步更新架构文档）。

## 关键入口（先看这些文件）

- `AICrews/runner.py`：配置驱动的执行入口（组装 Crew、执行、归档）
- `AICrews/application/crew/assembler.py`：从 DB 配置组装 CrewAI（Agent/Task/Tools/Knowledge）
- `AICrews/application/crew/preflight.py`：运行前预检（结构/依赖/配置校验）
- `AICrews/llm/unified_manager.py`：统一 LLM 管理（模型同步/配置读取）
- `AICrews/tools/registry/tool_registry.py`：工具统一注册与装载（系统工具 / MCP / 用户工具）
- `AICrews/infrastructure/mcp/http_client.py`：MCP 访问封装
- `AICrews/infrastructure/cache/redis_manager.py`：Redis 缓存封装（短 TTL 缓存/发布订阅）
- `AICrews/services/unified_sync_service.py`：订阅式行情同步（多用户共享）
- `AICrews/services/daily_archiver_service.py`：日结归档（realtime_quotes → market_prices）

## 目录结构（概览）

```
AICrews/
├── application/crew/        # Crew 装配/预检/编译/版本
├── services/                # 业务服务（分析、市场、同步、归档、知识、组合…）
├── tools/                   # 工具实现 + registry（供 Agent 调用）
├── llm/                     # LLM 统一管理与配置存储
├── infrastructure/          # MCP / Redis / Jobs / Storage / Knowledge / VectorStore
├── database/                # DBManager、Session、Models、向量工具
├── schemas/                 # API/服务层通用 Schema（Pydantic v2）
└── utils/                   # 日志、异常、通用工具
```

## 配置源（要先搞清楚“改哪儿”）

- **系统种子（YAML）**：
  - Agents/Tasks/Crews：`config/agents/agents.yaml`、`config/agents/tasks.yaml`、`config/agents/crews.yaml`
  - Tools/Prompts/LLM/Knowledge：`config/tools/*`、`config/prompts/*`、`config/llm/*`、`config/knowledge/*`
  - MCP（可选）：优先通过环境变量发现（如 `MCP_SERVER_<NAME>_URL`），也可提供 `config/mcp_servers.yaml`
- **运行时配置（DB）**：`AgentDefinition/TaskDefinition/CrewDefinition` 等表（装配器读取）。
- **最佳实践**：把“可变”的东西（prompt、结构、开关、阈值、可选分析师/辩论轮数）放配置；把“不可变”的执行逻辑放代码。

## 常见改动怎么做（优先按这个走）

### 1) 新增/修改策略（Crew）

- **优先**：改 `config/agents/crews.yaml`（作为模板/种子）→ 通过系统的模板导入/同步流程落到 DB → 由 `CrewAssembler` 装配运行。
- **不要**：在 `services/analysis_service.py` 或 `runner.py` 硬编码新增策略分支。

### 2) 新增/修改 Agent 人设（Prompt）

- **优先**：改 `config/agents/agents.yaml`（模板）或更新 DB 中 `AgentDefinition`（UI/接口更新）。
- **注意**：Agent 的 tools/knowledge 绑定要通过 `AgentToolBinding/AgentKnowledgeBinding` 或对应配置/服务统一设置，不要在装配器里写死。

### 3) 新增工具（Tool/MCP/策略表达式）

- 实现放 `AICrews/tools/*.py`，并确保：
  - 输入校验（ticker、时间范围、limit 等）
  - 超时/重试（外部 I/O）
  - 返回值可 JSON 序列化（不要直接返回 DataFrame/Session/复杂对象）
  - 错误不要把内部堆栈/密钥透出给 LLM 或前端
- 通过 `AICrews/tools/registry/tool_registry.py` 暴露给 Agent（必要时补充 DB 中的工具元数据/绑定关系）。

### 4) 新增知识源（RAG/文件/向量库）

- 配置在 `config/knowledge/*.yaml`（如 `config/knowledge/initial.yaml`，或 DB 的 `KnowledgeSource/UserKnowledgeSource`）
- 加载逻辑集中在 `AICrews/infrastructure/knowledge/knowledge_sources.py`
- 向量存储适配在 `AICrews/infrastructure/vectorstores/*`

### 5) 新增 LLM Provider/模型策略

- 只在 `AICrews/llm/*` 扩展，统一暴露到 `unified_manager.py`
- 所有密钥/端点来自环境变量或 DB 配置，禁止硬编码
- 变更影响模型 Provider/定价时，同步更新 `config/llm/providers.yaml` 与 `config/llm/pricing.yaml`

## 代码质量与安全（硬要求）

- **不要在 import 时做 I/O**（连 DB/Redis/HTTP/启动线程），需要时延迟初始化。
- **日志**：用 `AICrews.utils.logger.get_logger(__name__)`；关键路径带 `run_id/job_id/user_id/ticker`。
- **异常**：统一用 `AICrews/utils/exceptions.py` 定义业务异常；对外返回稳定错误，不透出内部实现细节。
- **敏感信息**：Token/Key/用户隐私不写入日志，不回传给 LLM（必要时做脱敏）。

## 提交前 Checklist

- [ ] 改动能用配置完成就不用改代码（先查 `config/agents/*.yaml`、`config/tools/*`、`config/prompts/*` 与 DB 模型字段）
- [ ] 新工具具备超时/错误处理，返回值可序列化且不泄密
- [ ] 新增/调整 Crew/Agent/Task 同步了装配器预检（`preflight.py`）所需字段
- [ ] 涉及数据层/订阅同步/归档链路变更，同步更新 `docs/FINAL_ARCHITECTURE_DESIGN.md`

## 相关文档

- `AGENTS.md`（根目录总纲）
- `backend/AGENTS.md`（API 层规范）
- `config/AGENTS.md`（YAML 配置规范）
- `docs/FINAL_ARCHITECTURE_DESIGN.md`（完整架构）

---

**最后更新**: 2025-12-28
**维护者**: AICrews Team
