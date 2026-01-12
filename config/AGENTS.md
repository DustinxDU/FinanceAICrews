# Config YAML 配置设计规范

## 📖 模块概述

config 目录包含项目的 YAML 配置文件，负责：
- Agent 人设和 Prompt 模板定义
- 任务定义和依赖关系
- Crew 组合编排
- MCP 服务端点配置
- 知识库配置

---

## 🏗️ 配置文件结构

```
config/
├── agents/                  # Agents/Tasks/Crews 模板（种子配置）
│   ├── agents.yaml          # Agent 人设与 Prompt 模板
│   ├── tasks.yaml           # Task 定义与依赖
│   └── crews.yaml           # Crew 组合编排
├── llm/                     # LLM Providers/定价等
│   ├── providers.yaml
│   └── pricing.yaml
├── prompts/                 # 系统 Prompt 模板（按场景拆分）
│   ├── copilot.yaml
│   ├── internal.yaml
│   └── quick_scan.yaml
├── tools/                   # 工具相关配置
│   ├── rss_config.yaml
│   └── policies.yaml        # （可选）工具访问策略（存在则生效）
├── knowledge/               # 内置知识内容（种子配置）
│   └── initial.yaml
└── mcp_servers.yaml          # （可选）MCP 服务端点（也可走环境变量发现）
```

---

## 🔧 Agent 配置规范

### 1. Agent 配置模板

```yaml
# config/agents/agents.yaml

agent_name:
  role: "角色名称"                    # 必填：Agent 的角色
  goal: "目标描述，支持 {ticker} 变量"  # 必填：Agent 的目标
  backstory: |
    多行背景故事
    描述方法论、专业知识、分析框架
  tools:                              # 可选：工具列表
    - "get_fundamentals"
    - "get_stock_prices"
  verbose: true                         # 可选：是否显示详细日志
  allow_delegation: false                 # 可选：是否允许任务委派
```

### 2. 命名约定

```yaml
# ✅ 好的命名
fundamental_analyst:      # 类型_专业分析师
technical_analyst:         # 类型_专业分析师
sentiment_analyst:       # 类型_专业分析师
bull_researcher:          # 多头研究员
bear_researcher:          # 空头研究员
buffett_value_investor:   # 风格_投资理念

# ❌ 不好的命名
analyst1:                # 太通用
tech:                    # 太简短
FundAnalyst:              # 不一致的大小写
```

### 3. 变量使用

```yaml
# ✅ 使用 {ticker} 变量
fundamental_analyst:
  goal: "Conduct a deep-dive valuation analysis of {ticker}"
  backstory: |
    You are analyzing {ticker}, a publicly traded company.
    Focus on revenue growth, profit margins, and valuation metrics.

# ✅ 使用多个变量
market_sentiment_analyst:
  goal: "Analyze market sentiment for {ticker} in {market}"
  backstory: |
    Evaluate {ticker}'s sentiment in the {market} market.
```

### 4. 完整示例

```yaml
fundamental_analyst:
  role: "Senior Fundamental Analyst"
  goal: "Conduct a deep-dive valuation and financial health analysis of {ticker}."
  backstory: |
    You are a veteran analyst from a top-tier investment bank.
    Your methodology:
    1. **Growth**: Analyze revenue and earnings growth trends (YoY, QoQ).
    2. **Profitability**: Check margins (Gross, Operating, Net) and ROE/ROIC.
    3. **Health**: Scrutinize the Balance Sheet. Look for debt risks.
    4. **Valuation**: Compare PE, PS, PB against historical averages and peers.
    
    CRITICAL: Always cite the fiscal period. State "Data Unavailable" if missing.
  tools:
    - "get_fundamentals"
    - "get_financial_statements"
  verbose: true
  allow_delegation: false
```

---

## 📋 Task 配置规范

### 1. Task 配置模板

```yaml
# config/agents/tasks.yaml

task_name:
  description: "任务描述，支持变量"      # 必填：任务描述
  expected_output: "期望输出格式"        # 必填：期望输出
  agent: "agent_name"                    # 必填：执行任务的 Agent
  context:                              # 可选：依赖的任务
    - "task_1"
    - "task_2"
  async_execution: false                   # 可选：是否异步执行
```

### 2. 任务依赖关系

```yaml
# ✅ 正确的任务依赖链
gather_market_data:
  description: "Collect market data for {ticker}"
  agent: "data_collector"

analyze_fundamentals:
  description: "Analyze fundamental data"
  agent: "fundamental_analyst"
  context:
    - "gather_market_data"  # 依赖 gather_market_data

generate_report:
  description: "Generate final analysis report"
  agent: "report_writer"
  context:
    - "analyze_fundamentals"
```

### 3. 完整示例

```yaml
fundamental_analysis:
  description: |
    Perform comprehensive fundamental analysis on {ticker}.
    Focus on:
    1. Revenue growth trends
    2. Profitability metrics
    3. Balance sheet health
    4. Valuation compared to peers
  expected_output: |
    A detailed fundamental analysis report including:
    - Revenue and earnings growth rates
    - Key profitability ratios (margins, ROE, ROIC)
    - Debt levels and financial health indicators
    - Current valuation metrics (PE, PB, PS) with comparisons
    - Investment recommendation (Buy/Hold/Sell) with rationale
  agent: "fundamental_analyst"
  context:
    - "gather_market_data"
  async_execution: false
```

---

## 🤝 Crew 配置规范

### 1. Crew 配置模板

```yaml
# config/agents/crews.yaml

crew_name:
  agents:                               # 必填：Agent 列表
    - "agent_1"
    - "agent_2"
  tasks:                                # 必填：任务列表
    - "task_1"
    - "task_2"
  process: "sequential"                   # 可选：执行顺序 (sequential/hierarchical)
  verbose: true                          # 可选：详细日志
  memory: true                           # 可选：启用记忆
  max_rpm: 10                           # 可选：最大每分钟请求数
```

### 2. 执行顺序

```yaml
# ✅ 顺序执行（推荐用于简单流程）
simple_analysis:
  agents:
    - "fundamental_analyst"
    - "technical_analyst"
  tasks:
    - "fundamental_analysis"
    - "technical_analysis"
  process: "sequential"

# ✅ 层级执行（推荐用于复杂流程）
comprehensive_analysis:
  agents:
    - "fundamental_analyst"
    - "technical_analyst"
    - "sentiment_analyst"
    - "risk_manager"
  tasks:
    - "fundamental_analysis"
    - "technical_analysis"
    - "sentiment_analysis"
    - "risk_assessment"
  process: "hierarchical"
```

### 3. 完整示例

```yaml
comprehensive_analysis:
  description: "Complete fundamental, technical, and sentiment analysis"
  agents:
    - "fundamental_analyst"
    - "technical_analyst"
    - "sentiment_analyst"
    - "risk_manager"
  tasks:
    - "gather_market_data"
    - "fundamental_analysis"
    - "technical_analysis"
    - "sentiment_analysis"
    - "generate_final_report"
  process: "sequential"
  verbose: true
  memory: true
  max_rpm: 20
```

---

## 🔌 MCP 服务器配置规范

### 1. MCP 服务器模板

```yaml
# config/mcp_servers.yaml

server_name:
  command: "python"                      # 必填：启动命令
  args:                                  # 必填：命令参数
    - "-m"
    - "mcp_server"
  env:                                    # 可选：环境变量
    API_KEY: "${MCP_API_KEY}"
  description: "服务器描述"               # 可选：描述
  enabled: true                           # 可选：是否启用
```

> 说明：运行时 MCP 配置通常优先通过环境变量发现（如 `MCP_SERVER_<NAME>_URL` / `MCP_SERVER_<NAME>_CMD`）。
> `config/mcp_servers.yaml` 为可选项：存在则会被加载（且优先级高于环境变量）。

### 2. 完整示例

```yaml
akshare_server:
  command: "python"
  args:
    - "/path/to/akshare/server.py"
  env:
    AKSHARE_DATA_DIR: "/data/akshare"
    LOG_LEVEL: "info"
  description: "A-share market data provider"
  enabled: true

yfinance_server:
  command: "python"
  args:
    - "/path/to/yfinance/server.py"
  env:
    YFINANCE_CACHE_DIR: "/cache/yfinance"
  description: "US stock market data provider"
  enabled: true

openbb_server:
  command: "python"
  args:
    - "/path/to/openbb/server.py"
  env:
    OPENBB_API_KEY: "${OPENBB_API_KEY}"
  description: "Comprehensive financial data provider"
  enabled: false  # 需要配置 API 密钥
```

---

## 🧠 知识源配置规范

### 1. 知识源模板

```yaml
# config/knowledge/initial.yaml

knowledge_key:
  display_name: "显示名称"                 # 必填：展示名称
  description: "知识描述"                  # 必填：简介
  category: "market_history"              # 必填：分类（如 market_history/strategy/macro）
  scope: "crew"                           # 必填：作用域（如 crew/agent）
  source_type: "text"                     # 必填：当前内置知识常用 text
  tags: ["标签1", "标签2"]                 # 可选：标签
  recommended_roles: ["risk_manager"]     # 可选：推荐角色
  content: |                              # 必填：内容（Markdown/纯文本均可）
    # 标题
    内容...
```

### 2. 完整示例

```yaml
crisis_2008:
  display_name: "2008 金融危机复盘"
  description: "详细分析 2008 年金融危机的成因、演变和教训"
  category: "market_history"
  scope: "crew"
  source_type: "text"
  tags: ["金融危机", "系统性风险"]
  recommended_roles: ["risk_manager", "macro_analyst"]
  content: |
    # 2008 金融危机复盘
    ...
```

---

## 📝 配置文件最佳实践

### ✅ 推荐做法

1. **变量使用**: 使用 `{ticker}`, `{market}` 等变量提高复用性
2. **注释说明**: 在 `description` 和 `backstory` 中详细说明
3. **命名一致**: Agent、Task、Crew 名称使用 snake_case
4. **依赖清晰**: Task 的 `context` 明确列出依赖关系
5. **工具明确**: Agent 的 `tools` 列表清晰列出可用工具
6. **版本控制**: 重要配置变更添加注释说明
7. **环境变量**: 敏感信息使用 `${ENV_VAR}` 引用

### ❌ 避免做法

1. **硬编码**: 不要在配置中硬编码具体股票代码
2. **过长行**: 保持每行在合理长度内（< 120 字符）
3. **缺少描述**: Agent 和 Task 必须有清晰的描述
4. **循环依赖**: Task 之间避免循环依赖
5. **未使用的配置**: 定期清理不再使用的 Agent/Task
6. **混乱的缩进**: YAML 对缩进敏感，保持一致的 2 空格缩进

---

## 🔍 配置验证

### 1. YAML 语法检查

```bash
# 使用 yamllint 检查语法
yamllint config/agents/agents.yaml
yamllint config/agents/tasks.yaml
yamllint config/agents/crews.yaml
```

### 2. 配置完整性检查

```python
# scripts/validate_config.py
import yaml
from pathlib import Path

def validate_config():
    config_path = Path("config")
    
    # 检查必需的文件
    required_files = [
        "agents/agents.yaml",
        "agents/tasks.yaml",
        "agents/crews.yaml"
    ]
    
    for file in required_files:
        file_path = config_path / file
        if not file_path.exists():
            raise FileNotFoundError(f"Missing config file: {file}")
        
        # 解析 YAML
        with open(file_path) as f:
            try:
                yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML in {file}: {e}")

if __name__ == "__main__":
    validate_config()
    print("✅ All configurations are valid!")
```

---

## 📚 相关文档

- [根目录 AGENTS.md](../AGENTS.md) - 项目总体规范
- [AICrews/AGENTS.md](../AICrews/AGENTS.md) - 智能体引擎规范
- [docs/FINAL_ARCHITECTURE_DESIGN.md](../docs/FINAL_ARCHITECTURE_DESIGN.md) - 完整架构

---

**最后更新**: 2025-12-25
**维护者**: Config Team
