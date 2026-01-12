"""
System Context Injection - 系统级运行时上下文注入

在 Agent 运行时自动注入关键上下文信息，解决 LLM 幻觉问题：
1. 当前日期 - 防止 LLM 使用过时的日期
2. 时间范围 - 告知 Agent 分析的时间跨度
3. 其他运行时上下文

Philosophy: 系统级上下文应该自动注入，不需要在每个 agent YAML 中手动配置
"""

from datetime import datetime
from typing import Any, Dict

# 默认的系统上下文模板 - 只包含系统级信息（日期）
# 业务变量（如 timeframe, ticker）应该在 YAML 中通过占位符使用
DEFAULT_SYSTEM_CONTEXT_TEMPLATE = """
**RUNTIME CONTEXT (Auto-injected)**:
- Today's Date: {date}

**CRITICAL DATE INSTRUCTIONS**:
1. When fetching historical data, calculate dates relative to TODAY ({date}).
2. If the asset has limited history (e.g., recently IPO'd), work with available data - this is expected, not an error.
3. NEVER hallucinate or assume company identity - verify from actual data returned by tools.
4. NEVER use hardcoded dates from your training data (e.g., 2023, 2024) - always use dates relative to {date}.
"""

# 简洁版本（用于 goal 等短文本）
COMPACT_CONTEXT_TEMPLATE = """[Today: {date} | Timeframe: {timeframe}]"""


def get_system_context_template() -> str:
    """获取系统上下文模板

    未来可以从配置文件或数据库读取自定义模板
    """
    return DEFAULT_SYSTEM_CONTEXT_TEMPLATE


def build_system_context(variables: Dict[str, Any]) -> str:
    """构建系统上下文字符串

    Args:
        variables: 运行时变量字典，应包含 date, timeframe, ticker 等

    Returns:
        格式化后的系统上下文字符串
    """
    template = get_system_context_template()

    # 确保关键变量存在
    context_vars = {
        "date": variables.get("date", datetime.now().strftime("%Y-%m-%d")),
        "timeframe": variables.get("timeframe", "not specified"),
        "ticker": variables.get("ticker", "unknown"),
    }

    try:
        return template.format(**context_vars)
    except KeyError:
        # 如果模板中有未知变量，返回基础版本
        return (
            f"\n**RUNTIME CONTEXT**: Today is {context_vars['date']}. "
            f"Analyzing {context_vars['ticker']} for {context_vars['timeframe']}.\n"
        )


def inject_system_context_to_backstory(
    backstory: str,
    variables: Dict[str, Any],
    position: str = "prepend"
) -> str:
    """将系统上下文注入到 agent backstory

    Args:
        backstory: 原始 backstory
        variables: 运行时变量
        position: 注入位置 - "prepend" (开头) 或 "append" (结尾)

    Returns:
        注入系统上下文后的 backstory
    """
    system_context = build_system_context(variables)

    if position == "prepend":
        return system_context + "\n" + backstory
    else:
        return backstory + "\n" + system_context


def ensure_system_variables(variables: Dict[str, Any]) -> Dict[str, Any]:
    """确保系统级变量存在

    自动注入必要的系统变量（如 date），如果调用者未提供

    Args:
        variables: 用户提供的变量

    Returns:
        包含系统变量的完整变量字典
    """
    result = dict(variables)

    # 自动注入当前日期
    if "date" not in result:
        result["date"] = datetime.now().strftime("%Y-%m-%d")

    # 自动注入当前时间戳（可选，用于更精确的场景）
    if "timestamp" not in result:
        result["timestamp"] = datetime.now().isoformat()

    # 自动注入年份（方便模板使用）
    if "year" not in result:
        result["year"] = datetime.now().year

    return result
