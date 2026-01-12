# Backend（FastAPI）开发规范

> **Scope**：本文件适用于 `backend/` 目录（FastAPI API 层）。目标：让任何 Agent 快速做出一致、可维护、可扩展的后端改动。

## TL;DR（必须遵守）

1. **Backend 只做 API 编排层**：参数校验 / 鉴权 / 依赖注入 / 调用服务 / 组装响应；业务逻辑下沉到 `AICrews/services/*`。
2. **Schema 统一放 `AICrews/schemas/*`（Pydantic v2）**：backend 不重复定义 schema，避免一处改动多处同步。
3. **新增 REST 端点的唯一入口**：`backend/app/api/v1/endpoints/<domain>.py` + 在 `backend/app/api/v1/router.py` 注册（保持 `backend/app/main.py` 轻薄）。
4. **数据库访问优先 SQLAlchemy 2.0 风格**：新代码使用 `select/insert/update/delete` + `session.execute`，避免新增 `session.query`。
5. **DB Session 依赖优先用** `backend.app.security.get_db`：确保配置异常能以 503 显式暴露；不要在 endpoints 里手动 new DBManager。
6. **错误返回要“稳定、可预期”**：对外不透出内部异常细节；内部错误写日志（`exc_info=True`），对外返回统一 `ErrorResponse`/合理状态码。
7. **外部 I/O 必须有超时/重试**（HTTP/MCP/LLM/Redis）：放在 Service 层封装，endpoint 不直接打外部依赖。
8. **后台任务/常驻服务只在** `backend/app/core/lifespan.py` **启停**：禁止 import 时启动线程/任务，保证可测与可控关闭。
9. **遵守 3 层数据架构与订阅模型**：`assets` → `realtime_quotes` → `market_prices`；图表数据“透传 + Redis 5min TTL”，不落库。
10. **破坏性变更必须做兼容**：改 API 路径/字段/语义时，提供兼容别名或版本升级，并同步更新相关文档。

## 关键入口（先看这些文件）

- `backend/app/main.py`：FastAPI 应用入口（注册 REST/WS router、CORS）
- `backend/app/core/lifespan.py`：启动/关闭编排（Redis、同步服务、归档服务、后台循环）
- `backend/app/security.py`：JWT、鉴权依赖、`get_db()`
- `backend/app/api/v1/router.py`：v1 路由聚合（新增 endpoints 必须在这里 include）
- `backend/app/api/v1/endpoints/`：按领域拆分的 REST endpoints
- `backend/app/ws/router.py`：WebSocket 路由（分析日志、实时价格）
- `backend/app/ws/run_log_manager.py`：运行日志 WS 连接管理
- `backend/app/storage.py`：存储层兼容封装（实现位于 `AICrews.infrastructure.storage`）

## 代码放置规则（最重要）

- **Endpoint（backend）**：只做输入/权限/编排，尽量保持“短小可读”（建议 ≤ ~50 行有效逻辑）。
- **Service（AICrews）**：承载业务逻辑、外部 I/O、缓存策略、复杂计算、与 MCP/LLM 的交互。
- **Schema（AICrews）**：所有请求/响应/分页结构集中管理，避免散落在 endpoints。
- **DB Model（AICrews）**：数据库表结构统一在 `AICrews/database/models/*`。
- **基础设施（AICrews）**：Redis/MCP/Jobs/Storage 的封装统一复用，不在 backend 里重新造轮子。

## API 设计约定

- **统一前缀**：`/api/v1`（见 `backend/app/api/v1/router.py`）
- **命名**：新接口优先 RESTful（名词/复数），旧接口保持兼容；不要随意重命名已有路径。
- **输入校验**：用 Pydantic v2 模型 + `Query/Path/Body` 限制边界（长度、范围、枚举）。
- **响应**：`response_model` 必填；列表接口优先使用 `PaginationParams` + `ListResponse[T]`（如需兼容现有返回结构，可逐步迁移）。

## 依赖注入与数据库

- **鉴权**：写操作/用户数据默认需要 `Depends(get_current_user)`；仅展示类接口可使用 `get_current_user_optional`。
- **DB Session**：在 endpoints 中使用 `db: Session = Depends(get_db)`；写操作必须 `commit()`，异常要 `rollback()`。
- **SQLAlchemy 2.0 建议写法**（新代码）：
  - `result = db.execute(select(Model).where(...))`
  - `items = result.scalars().all()`

## 异步与并发

- **何时用 `async def`**：需要 `await` 的 I/O（MCP/HTTP/Redis/LLM/WebSocket/Jobs 状态轮询）。
- **避免阻塞事件循环**：同步 DB/CPU 重任务不要在 `async def` 中长时间执行；优先下沉到后台任务或用线程池（仅必要时）。
- **长耗时工作**：使用 JobManager/后台任务，API 返回 job_id + 状态查询，而不是卡住请求。

## 错误处理（对外稳定、对内可观测）

- **常用状态码**：401/403/404/409/422/429/503/500。
- **不要把 `str(e)` 直接返回给前端**（避免泄露内部实现/凭据/堆栈信息）。
- **日志**：`logger.error("...", exc_info=True)`，并携带关键上下文（user_id、ticker、job_id、endpoint）。

## WebSocket 规范

- **职责**：只做实时推送（价格、运行日志），不承载复杂业务流程。
- **连接管理**：复用 `AICrews.services.realtime_ws_manager` 与 `backend.app.ws.run_log_manager`。
- **心跳**：客户端 `ping`，服务端 `pong`；断开要清理连接，避免内存泄漏。

## 缓存与数据层（与架构对齐）

- **三层数据**：`assets`（基础信息）→ `realtime_quotes`（快照）→ `market_prices`（历史）。
- **订阅式同步**：只同步有人关注的资产；订阅数归零自动停止（同步逻辑在 `AICrews.services.unified_sync_service`）。
- **图表数据**：透传 MCP + Redis 短缓存（建议 5 分钟），不落库（见 `AICrews.services.chart_service`）。

## 提交前 Checklist

- [ ] 先 `rg` 搜索现有 schema/service，能复用就复用，避免重复实现
- [ ] 新增 endpoints 已在 `backend/app/api/v1/router.py` 注册
- [ ] 权限/所有权校验完成，敏感信息不出现在响应/日志中
- [ ] 错误路径返回稳定状态码与结构，内部错误有 `exc_info=True` 日志
- [ ] 影响 API 结构/订阅同步/数据层时，同步更新 `docs/FINAL_ARCHITECTURE_DESIGN.md`

## 相关文档

- `AGENTS.md`（根目录总纲）
- `AICrews/AGENTS.md`（服务/引擎规范）
- `docs/FINAL_ARCHITECTURE_DESIGN.md`（完整架构）
- `docs/database_schema.md`（数据库结构）

---

**最后更新**: 2025-12-28
**维护者**: Backend Team
