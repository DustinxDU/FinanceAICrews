# FinanceAICrews 开发规范总纲

> generate the plan first

> **Scope**：本文件适用于整个仓库（根目录及所有子目录）。进入某个子目录开发时，必须同时遵守对应目录下的 `AGENTS.md`；若子目录规范与本文件冲突，以**更具体/更靠近代码的规范**为准。
>
> **Philosophy**：**Code is Engine, Config is Soul**（配置优先；代码负责执行）。可变的“人设/流程/开关/阈值”优先由配置或 DB 驱动，而不是写死在代码里。

## 📋 目录导航（先读对应模块）

- `AICrews/AGENTS.md`：智能体引擎与服务实现规范（Python）
- `backend/AGENTS.md`：FastAPI API 编排层规范
- `frontend/AGENTS.md`：Next.js App Router 前端规范
- `config/AGENTS.md`：YAML 配置设计与命名规范

## TL;DR（必须遵守）

1. **改动先选“正确的层”**：API 编排在 `backend/`；业务/工具/同步/归档在 `AICrews/`；UI/交互在 `frontend/`；人设/任务/Crew/MCP/知识源在 `config/`（或 DB 运行时配置）。
2. **运行时装配走 DB**：Crew/Agent/Task 的运行时装配由 `AICrews/application/crew/assembler.py` 从表配置读取并组装；YAML 更多是“模板/种子/初始化”，不保证被运行时直接读取。
3. **Schema 统一**：请求/响应/分页等 schema 统一放 `AICrews/schemas/*`（Pydantic v2）；避免在 `backend/`/`services/`/`tools/` 重复定义同名 schema。
4. **外部 I/O 必须可控**：HTTP/MCP/LLM/Redis 调用必须有超时/错误处理/可观测日志；对外（前端/LLM）返回稳定结构，不泄露密钥与内部堆栈。
5. **禁止 import 时副作用**：不要在 import 时连接 DB/Redis、发 HTTP、启动线程/后台循环；长任务必须可 `start/stop`，由 `backend/app/core/lifespan.py` 统一启停。
6. **遵守数据架构与订阅模型**：`assets → realtime_quotes → market_prices`；图表数据“透传 + Redis 5min TTL”，不要私自落库（除非明确新增 layer 并同步更新架构文档）。

## 🧭 “改哪里”快速决策（给 Agent/开发者）

- **只改 Prompt/人设/工具绑定/任务流程/Crew 编排**：优先改 `config/agents/*.yaml`（模板/种子）或走 DB 配置更新；不要在代码里硬编码分支。
- **新增/改业务能力（同步、归档、分析、工具封装）**：改 `AICrews/services/*`、`AICrews/tools/*`、`AICrews/infrastructure/*`；工具需经 `AICrews/tools/registry/tool_registry.py` 暴露。
- **新增/改 API 端点**：只在 `backend/app/api/v1/endpoints/*` 增加，并在 `backend/app/api/v1/router.py` 注册；endpoint 保持轻薄，复杂逻辑下沉到 `AICrews/services/*`。
- **新增/改前端页面与交互**：按 `frontend/app/*`（App Router）组织；API 调用优先走 `frontend/lib/api.ts`；鉴权 token 在 `localStorage`，需要用户态数据的页面必须是 Client 组件（见 `frontend/AGENTS.md`）。

## 🎯 项目概述

FinanceAICrews 是一个基于 CrewAI 的金融智能体分析平台，重点能力：

- 多智能体协作：基本面/技术面/情绪/风险等
- 多数据源整合：通过 MCP 统一接入（服务可由 YAML 或环境变量发现）
- 多 LLM 支持：统一入口管理模型与配置（见 `AICrews/llm/unified_manager.py`）
- 实时市场监控：订阅式同步 + 三层数据架构

## 🏗️ 核心架构不变量（全仓库通用）

### 1) 3 层数据架构
```
Layer 1: assets           # 基础信息：ticker/name/sector/exchange
  ↓
Layer 2: realtime_quotes  # 实时快照：price/change%/volume（约 5 分钟更新）
  ↓
Layer 3: market_prices    # 历史K线：OHLCV（每日/定时归档）
```

### 2) 订阅式同步模型

- 只同步“有人关注/订阅”的资产
- 多用户共享同一份价格数据
- 订阅数归零时自动停止同步

### 3) 透传模式（图表数据）

- 图表数据不落库
- Redis 缓存建议 5 分钟 TTL
- 由 MCP API 直接透传（必要时在 Service 层做短缓存与容错）

## 🧩 关键入口（从这里定位代码）

- 引擎/装配：`AICrews/runner.py`、`AICrews/application/crew/assembler.py`、`AICrews/application/crew/preflight.py`
- 统一 LLM：`AICrews/llm/unified_manager.py`
- 工具注册：`AICrews/tools/registry/tool_registry.py`
- 后端入口与启停：`backend/app/main.py`、`backend/app/core/lifespan.py`
- 前端入口：`frontend/app/layout.tsx`、`frontend/lib/api.ts`
- 配置：
  - Agents/Tasks/Crews：`config/agents/agents.yaml`、`config/agents/tasks.yaml`、`config/agents/crews.yaml`
  - MCP：优先用环境变量发现（如 `MCP_SERVER_<NAME>_URL`），可选 `config/mcp_servers.yaml`
  - LLM：`config/llm/providers.yaml`、`config/llm/pricing.yaml`
  - Tools/Prompts/Knowledge：`config/tools/*`、`config/prompts/*`、`config/knowledge/*`

## 🧰 开发环境与常用命令

### 快速启动（本地开发）
```bash
# 终端 1：后端与 MCP
cd /home/dustin/stock/FinanceAICrews
source venv/bin/activate
python -m backend.app.main &
./scripts/start_mcp.sh &

# 终端 2：前端
cd frontend
npm run dev
```

### Python 依赖
```bash
source venv/bin/activate
uv add package-name
uv export > requirements.txt
```

### 前端依赖
```bash
cd frontend
npm install
npm run dev
npm run build
```

### 数据库迁移（如涉及表结构）
```bash
alembic revision --autogenerate -m "描述"
alembic upgrade head
alembic downgrade -1
```

## 🧪 测试（提交前至少跑一轮相关的）

```bash
pytest tests/
```

```bash
cd frontend
npm test
npm run build
```

## 🔒 安全与质量底线（全仓库通用）

- **永不硬编码密钥**：只从环境变量或 DB 配置读取；日志/返回值都要脱敏。
- **错误对外稳定**：不要把内部 `Exception`/堆栈/第三方响应原样返回给前端或 LLM。
- **日志可观测**：关键路径带 `run_id/job_id/user_id/ticker` 等上下文；内部错误 `exc_info=True`。
- **SQL 注入防护**：新代码使用参数化查询；SQLAlchemy 2.0 风格优先（见 `backend/AGENTS.md`）。

## 🔄 变更管理（需要同步更新文档/规范的场景）

- **新增数据 Layer/改变三层链路**：更新 `docs/FINAL_ARCHITECTURE_DESIGN.md`，并同步更新相关 `AGENTS.md`（尤其 `backend/AGENTS.md`、`AICrews/AGENTS.md`）。
- **修改订阅同步/实时推送模型**：同步更新 `backend/AGENTS.md`（lifespan/WS）与 `frontend/AGENTS.md`（WS/清理/退避）。
- **新增 LLM Provider/模型策略**：同步更新 `AICrews/AGENTS.md`（LLM 统一入口）与 `config/AGENTS.md`（配置约定）。
- **修改 API 结构/字段语义**：保持兼容或版本化，并同步更新相关文档与前端调用。

## 🔀 Git 工作流（建议）

```bash
feature/{功能名}
fix/{bug描述}
docs/{文档更新}
refactor/{重构内容}
```

```bash
git commit -m "feat: 添加实时数据同步功能"
git commit -m "fix: 修复 WebSocket 连接断开问题"
git commit -m "docs: 更新 API 文档"
```

## 📚 相关文档

- `docs/FINAL_ARCHITECTURE_DESIGN.md`：完整架构说明
- `docs/database_schema.md`：数据库结构
- `docs/mcp/README.md`：MCP 配置指南
- `docs/frontend-architecture.md`：前端架构

---

**最后更新**: 2025-12-29
**维护者**: FinanceAICrews Team
