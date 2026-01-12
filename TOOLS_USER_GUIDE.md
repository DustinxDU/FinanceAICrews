# FinanceAICrews Tools 使用说明（小白一步步版）

> 这是一份面向“第一次使用就要跑通”的用户手册：从启动环境 → 接入 MCP 数据 → 启用/配置工具与技能 → 在 Crew Builder 里挂到 Agent → 跑出结果。  
> 如果你的界面还没升级到 **Providers/Skills/Knowledge** 三个 Tab，也可以直接跳到文末的「旧版 Tools 页面怎么对应」。

---

## 0. 你要先知道的 3 件事（避免踩坑）

1) **不要把 100+ 原始 MCP 工具直接暴露给 Agent**：会导致 prompt/token 爆炸、LLM 误用工具。正确做法是只启用少量“能力（Capability）”或少量“技能（Skill）”。
2) **新增默认关闭**：无论是官方内置的能力/技能，还是用户新增的 MCP Provider、导入的 Pack、发现的新工具，默认都应该是 `disabled`，必须手动启用。
3) **Blocked 必须不可选**：当数据源没配置/没启用/不健康时，依赖它的技能应显示 `blocked`，并且在 Crew Builder 里必须灰掉不可勾选。

---

## 1. 名词翻译（看一次就够）

- **Provider**：能力提供方（MCP/内置）。负责连接、鉴权、健康检查、工具发现、能力映射。
- **Capability（cap:\*）**：原子能力（你希望 Agent 拥有的能力），例如行情/历史K线/新闻/搜索/指标计算。
- **Skill（preset/strategy/workflow:\*）**：面向人类的封装（可理解的“技能卡片”），最终仍调用 capability。
- **Loadout**：某个 Agent 实际挂载了哪些 capabilities/skills（在 Crew Builder 配置）。

---

## 2. 快速启动（第一次跑通推荐）

你有两种启动方式：**全 Docker（最省事）** 或 **本地开发（更适合调试）**。

### 2.1 全 Docker（推荐新手）

1) 准备 `.env`
```bash
cp .env.example .env
```

2) 启动全栈（包含 db/redis/backend/web + MCP）
```bash
docker compose up -d
```

3) 检查 MCP 健康
```bash
curl http://localhost:8009/health   # akshare
curl http://localhost:8010/health   # yfinance
curl http://localhost:8008/mcp/     # openbb (streamable http)
```

4) 打开前端（通常走网关）
- `http://localhost:8081`（gateway）

### 2.2 本地开发（你需要看日志/改代码）

1) 启动依赖（db/redis + MCP）
```bash
docker compose up -d db redis akshare_mcp yfinance_mcp openbb_mcp
```

2) 启动后端
```bash
./start_backend.sh
```

3) 启动前端
```bash
./start_frontend.sh
```

4) 打开前端
- `http://localhost:3000`

> 如果后端提示 MCP 未启用：在 `.env` 里加上 `FAIC_MCP_ENABLED=true`（或 `MCP_ENABLED=true`），然后重启后端。

---

## 3. Tools 页面怎么用（新版：Providers / Skills / Knowledge）

> 你要记住一句话：**先接入并启用 Providers 的能力 → 再在 Skills 里启用/创建技能 → 最后到 Crew Builder 给 Agent 挂载。**

### 3.1 Tab：Providers（接入 MCP / 管理能力）

#### 3.1.1 新手最常见目标：让“行情 + 历史K线”可用

1) 打开 `Tools → Providers`
2) 找到内置 Provider（例如 Akshare / YFinance / OpenBB）
3) 对每个 Provider 做三件事：
   - **配置**（URL/凭证，若需要）
   - **启用**（enabled）
   - **健康检查**（healthy）
4) 在 “Capability 覆盖矩阵”里至少确保这些是 `available`：
   - `equity_quote`（行情/快照）
   - `equity_history`（历史K线）

> 只要 `equity_history` 不可用，很多量化技能都会变 `blocked`（例如 RSI/MACD/策略公式）。

#### 3.1.2 MCP 接入示例：连接一个远程 SSE MCP Server

**场景**：你拿到了第三方 MCP SSE 地址：`https://mcp.example.com/sse`

1) Tools → Providers → Add Provider
2) 选择 Transport：`SSE`
3) 填 URL：`https://mcp.example.com/sse`
4) 点击 Discover（发现工具）
5) 系统会给出 capability 推荐；你必须手动确认映射（可多选）
6) 默认是 disabled：只启用你需要的 Core capabilities（例如 `equity_history`、`equity_news`）

#### 3.1.3 MCP 接入示例：运维/本地无 UI 时用环境变量接入（高级备用）

如果你的版本暂未提供 “Add Provider” UI，你仍可以通过环境变量让系统发现 MCP：

```bash
# SSE MCP 示例
export MCP_SERVER_MYDATA_URL="https://mcp.example.com/sse"

# 本地测试：重启后端后生效
./start_backend.sh
```

> 说明：仓库里对 MCP URL 也兼容 `AKSHARE_MCP_URL / YFINANCE_MCP_URL / OPENBB_MCP_URL`（Docker Compose 默认会注入）。

#### 3.1.4 OpenBB 工具太多怎么办？（强烈建议限制类别）

OpenBB 默认可能暴露很多工具。新手建议先只开 `equity,news`，否则工具列表会非常长、Discover 也更慢。

**Docker Compose（推荐）**：`docker-compose.yml` 已支持：
- `OPENBB_MCP_DEFAULT_TOOL_CATEGORIES=equity,news`

如果你想改成别的类别（例如加上 `economy`），请直接修改 `docker-compose.yml` 的 `openbb_mcp` 环境变量行，然后重启容器：
```bash
docker compose restart openbb_mcp
```

---

### 3.2 Tab：Skills（技能库：启用/创建/导入）

Skills 默认是一个列表（Recommended / Enabled），你日常只在这里做 4 件事：

1) **启用官方 Quant Skill Pack 里的少量推荐技能**
2) **Create Skill → New Strategy（写公式）**
3) **Create Skill → New Workflow（多步）**
4) **Import Pack（导入第三方 Skill Pack）**

#### 3.2.1 Quant Skill Pack（官方默认技能包）怎么用？

**它是什么**：官方提供的一组 **presets/workflows**（不是 raw tools 列表）。  
**你怎么用**：

1) Tools → Skills
2) 在 Recommended 里启用少量条目（建议从 2~5 个开始）
   - `preset:quant:rsi_14`（示例）
   - `preset:quant:macd_default`（示例）
   - `workflow:quant:trend_scan_v1`（示例：一次调用跑完一个完整技术面流程）
3) 去 Crew Builder 把它们挂给 Agent（见第 4 章）

> 建议：Quant Skill Pack 的“默认开启”只开极少数（1~3 个）。其余必须用户手动开，避免 token 膨胀。

#### 3.2.2 我想写一个公式，是不是必须创建 My Strategies？

**推荐做法：是（创建 Strategy）。**  
原因：Strategy 会变成一个“稳定 wrapper 工具”，Agent 只需要传 `ticker`，不会每次都猜公式/参数。

**步骤（创建策略）**
1) Tools → Skills → Create Skill → New Strategy
2) 输入策略公式（例）：
   - `MA(20) > MA(60) AND RSI(14) < 30`
3) 点击 Validate（语法/白名单校验）
4) 点击 Evaluate（选择一个 ticker 试跑，例如 `AAPL`）
5) Save（会生成 `strategy:{id}`）
6) 创建完成默认 `enabled`（但如果依赖能力缺失仍会显示 blocked）

**注意：不支持的写法**
- 不支持 `Crossover(A, B)` / `Crossunder(A, B)`  
  你可以改成：`MA(20) > MA(60)`（金叉后状态）或结合更多条件。

#### 3.2.3 Workflow（多步）是不是必须依赖多个策略？

不是。Workflow 有 3 种常见用法：

1) **只用能力（cap:\*）+ transform**：例如行情 + RSI + 生成信号
2) **引用 0~N 个已有 Strategy**：把策略当“可复用判断步骤”
3) **在 workflow 内联公式**（formula_eval step）：高级用户用，省掉先保存 Strategy 的步骤

**步骤（创建 workflow）**
1) Tools → Skills → Create Skill → New Workflow
2) 选择模板（推荐）：`Price + Indicators + Signal`
3) 配置 steps（示例）：
   - step1：`cap:equity_quote`（输出 quote）
   - step2：`cap:indicator_calc`（计算 RSI(14)）
   - step3：`transform`（把 RSI<30 标成 oversold）
   - step4：`aggregate`（输出最终结构化结果 + 一段摘要文本）
4) Save：生成 `workflow:*`，默认 `enabled`

#### 3.2.4 Import Pack（导入第三方技能包）

1) Tools → Skills → Import Pack
2) 选择/粘贴 Pack 源（例如 URL 或 JSON/YAML）
3) 安装后默认 `disabled`
4) 你只启用其中 1~3 个条目（建议从 workflow 开始）
5) 去 Crew Builder 挂载

**Pack 更新规则（重要）**
- 必须显式点 Update
- 不允许静默改变一个已存在 skill 的行为（invocation 变化要生成新 `skill_key` 并提示迁移）

---

### 3.3 Tab：Knowledge（保留原样）

Tools 的 Knowledge Tab 当前按原系统保留（未来再优化）。  
对新手来说：先不用折腾 Knowledge，也能跑通工具/技能/crew。

---

## 4. Crew Builder：把工具/技能挂到 Agent（真正决定“能不能用”）

> Crew Builder 负责“给某个 Agent 配 Loadout”，不负责 provider 接入与配置。

### 4.1 两栏选择（推荐）

- 左：Capabilities（`cap:*`）
- 右：Skills（`preset/strategy/workflow:*`）

### 4.2 被灰掉（blocked）怎么办？

如果某个条目是灰色不可勾选：

1) 看提示：缺少哪个 capability（通常是 `equity_history`）
2) 回到 Tools → Providers
3) 启用并修复 provider 健康（healthy）
4) 回到 Crew Builder：条目会变为可选

### 4.3 新手最推荐的挂载方式（少而稳）

给一个“技术分析 Agent”建议只挂：
- 一个完整 workflow（例如 `workflow:quant:trend_scan_v1`），或
- 2~3 个 presets（RSI/MACD/趋势），不要一口气挂 30 个

这样：
- token 成本低
- LLM 误用概率低
- 输出更稳定

---

## 5. 详细案例（照着做一定能跑通）

### Case 1：跑通一次 AAPL 技术面（最短闭环）

**目标**：让 Agent 给出 RSI/MACD/趋势摘要  
**你需要启用的能力**：`equity_history`、`indicator_calc`

1) Tools → Providers：确保 `equity_history` available（provider healthy）
2) Tools → Skills：启用
   - `preset:quant:rsi_14`
   - `preset:quant:macd_default`
3) Crew Builder：创建/选择一个 Agent（如 “Quant Analyst”），挂载上述 skills
4) Run：输入 ticker `AAPL`

### Case 2：港股/ A 股 ticker 怎么填？

系统常见规范（示例）：
- 美股：`AAPL`
- 港股：`0700.HK`
- A 股：`600000.SH` 或 `000001.SZ`

如果你不确定：先用行情能力 `cap:equity_quote` 验证 ticker 能否返回数据。

### Case 3：写一个“超卖买入”策略并复用（My Strategy）

**目标**：保存策略 `strategy:{id}`，以后勾选一次就能用

1) Tools → Skills → Create Skill → New Strategy
2) 公式：`MA(20) > MA(60) AND RSI(14) < 30`
3) Validate → Evaluate（选 `AAPL`）→ Save
4) Crew Builder：给任意 Agent 勾选 `strategy:{id}`

### Case 4：做一个“一键日报”Workflow（一次调用输出结构化结果）

**目标**：workflow 输出包含：价格快照、RSI、信号、摘要

1) Tools → Skills → Create Skill → New Workflow
2) Steps 参考：
   - quote：`cap:equity_quote`
   - rsi：`cap:indicator_calc`（indicator=rsi, period=14）
   - transform：生成 `signal`（例如 oversold/neutral/overbought）
   - aggregate：输出 result + text
3) Save
4) Crew Builder：挂载该 workflow 到 Agent
5) Run：输入 ticker

### Case 5：接入第三方 MCP（只启用 1 个能力，避免爆炸）

**目标**：接入一个远程新闻 MCP，但只给系统 `equity_news` 能力

1) Tools → Providers → Add Provider（SSE）
2) Discover → 映射到 `equity_news`
3) 只启用 `equity_news`（其他全部保持 disabled）
4) Tools → Skills：启用一个新闻摘要 workflow（或你自己建一个 workflow）
5) Crew Builder：挂载给“Research Agent”

### Case 6：排查“为什么工具看得见但 Agent 用不了？”

检查顺序（从上到下）：
1) Tools → Providers：对应 capability 是否 `available`
2) Tools → Skills：skill 是否 `enabled`，且是否 `ready`
3) Crew Builder：skill 是否成功挂到 Agent（loadout）
4) Run 前 preflight：是否提示缺失依赖/禁用项

---

## 6. 我想“自己做工具”（给非程序员 / 给开发者）

### 6.1 非程序员（推荐）：用 Strategy / Workflow 当“自定义工具”

- Strategy：把一个公式变成 `strategy:{id}`（一个工具）
- Workflow：把多步流程变成 `workflow:*`（一个工具）

这两种方式都不会让你写 Python，也不会让你暴露 raw MCP tools 给 Agent。

### 6.2 开发者（高级）：新增一个内置 Tool/Capability（概念指引）

如果你要新增一个真正的 Python 工具（primitive），建议路径是：

1) 在 `AICrews/tools/` 实现一个 `@tool(...)` 的函数（签名稳定、带超时/错误处理）
2) 在 Tool Registry/Skill Catalog 把它归类成一个 capability（`capability_id`）
3) 在 Skills 里提供一个或多个 preset/workflow 作为“人类可用入口”
4) 默认 disabled，用户手动启用后才能在 Crew Builder 里挂载

> 这样可以保证：用户看到的是少量稳定能力/技能，而不是一堆内部实现细节。

### 6.3 开发者（高级）：自己做一个 MCP Server 并接入（可当作“第三方工具”）

如果你需要把一个数据源/券商 API/内部服务接入 FinanceAICrews，最推荐的方式是“把它做成一个 MCP Server”，再通过 Tools→Providers 接入。

#### 6.3.1 用模板创建一个 MCP Server（最短路径）

1) 复制模板
```bash
cp -r docker/mcp/_template docker/mcp/mydata
```

2) 实现你的工具
- 编辑 `docker/mcp/mydata/server.py`：实现你的 SDK 调用与 tool definitions
- 编辑 `docker/mcp/mydata/requirements.txt`：加依赖

3) 加到 `docker-compose.yml`
- 参考 `docker/mcp/_template/README.md`
- 选择一个未占用端口，例如 `8020`

4) 启动并验证健康
```bash
docker compose up -d mydata_mcp
curl http://localhost:8020/health
```

5) 接入到系统
- 新版 UI：Tools → Providers → Add Provider（SSE），URL 填 `http://localhost:8020/sse` → Discover → 映射 capability → 手动启用需要的能力
- 旧版/无 UI：先用环境变量让后端发现（示例）：
```bash
export MCP_SERVER_MYDATA_URL="http://localhost:8020/sse"
./start_backend.sh
```

> 建议：你的 MCP Server 也要支持超时、限流、缓存与清晰的错误结构（否则 LLM 很容易误判）。

---

## 7. 旧版 Tools 页面怎么对应（如果你没看到 Providers/Skills/Knowledge）

如果你当前 Tools 页面还是 `All/Data/Quant/External` 这种分类，可以按下面理解：

- 旧版 `data tools` ≈ 新版 Providers 里启用的 Market Data capabilities（如行情/历史/新闻）
- 旧版 `quant tools` ≈ 新版 `cap:indicator_calc` / `cap:strategy_eval` + 少量 presets
- 旧版 `external tools` ≈ 新版 External IO capabilities（search/scrape/browse）
- 旧版 `My Strategies` ≈ 新版 Tools → Skills → Create Skill → New Strategy

> 核心原则不变：少开、按需开、blocked 不选、优先用封装的 skills/workflows。
