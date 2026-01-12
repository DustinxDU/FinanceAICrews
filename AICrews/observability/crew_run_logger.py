"""
Crew Run Logger - 独立的 Crew 运行日志系统

为每次 Crew 运行创建独立的详细日志文件，记录：
- Agent 思考过程
- 工具调用详情（输入/输出/耗时）
- LLM 调用详情（模型/tokens/耗时）
- Task 执行状态

日志文件结构：
logs/crew_runs/YYYY-MM-DD/run_{run_id}_{ticker}_{timestamp}.log
"""

import json
import logging
from AICrews.observability.logging import get_logger
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class CrewRunLoggerConfig:
    """CrewRunLogger 配置"""

    log_dir: str = "logs/crew_runs"
    retention_days: int = 7
    max_file_size_mb: int = 50
    backup_count: int = 3
    include_timestamps: bool = True
    include_agent_thoughts: bool = True
    include_tool_io: bool = True
    include_llm_prompts: bool = True
    include_llm_responses: bool = True  # 默认记录响应（用于调试）
    truncate_output_chars: int = 2000  # 截断长输出


class CrewRunLogger:
    """
    独立的 Crew 运行日志记录器

    为每次 Crew 运行创建独立的日志文件，支持：
    - 实时写入（tail -f 友好）
    - 结构化格式（易读易解析）
    - 完整的执行追踪

    Usage:
        logger = CrewRunLogger(
            run_id="abc123",
            ticker="AAPL",
            crew_name="Standard Analysis"
        )
        logger.log_run_start(variables={"ticker": "AAPL"})
        logger.log_tool_call(...)
        logger.log_llm_call(...)
        logger.log_run_end(status="completed")
        logger.close()
    """

    # 类级别的活跃 logger 注册表
    _active_loggers: Dict[str, "CrewRunLogger"] = {}
    _lock = threading.Lock()

    def __init__(
        self,
        run_id: str,
        ticker: str,
        crew_name: str,
        config: Optional[CrewRunLoggerConfig] = None,
    ):
        self.run_id = run_id
        self.ticker = ticker
        self.crew_name = crew_name
        self.config = config or CrewRunLoggerConfig()
        self.start_time = datetime.now()

        # 创建日志文件路径
        self.log_file_path = self._create_log_file_path()

        # 初始化 Python logger
        self._logger = self._setup_logger()

        # 注册到活跃 loggers
        with self._lock:
            self._active_loggers[run_id] = self

    def _create_log_file_path(self) -> Path:
        """创建日志文件路径，按日期分目录"""
        base_dir = Path(self.config.log_dir)
        date_dir = base_dir / self.start_time.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        # 文件名格式：run_{run_id}_{ticker}_{timestamp}.log
        timestamp = self.start_time.strftime("%H%M%S")
        safe_run_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", self.run_id)
        filename = f"run_{safe_run_id}_{self.ticker}_{timestamp}.log"

        return date_dir / filename

    def _setup_logger(self) -> logging.Logger:
        """设置独立的 Python logger"""
        # 使用唯一的 logger 名称
        logger_name = f"crew_run.{self.run_id}"
        logger = get_logger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # 不传播到父 logger

        # 清除已有的 handlers
        logger.handlers.clear()

        # 创建文件 handler
        handler = RotatingFileHandler(
            filename=str(self.log_file_path),
            maxBytes=self.config.max_file_size_mb * 1024 * 1024,
            backupCount=self.config.backup_count,
            encoding="utf-8",
        )
        handler.setLevel(logging.DEBUG)

        # 简洁的格式（时间戳在消息中处理）
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    def _format_timestamp(self) -> str:
        """格式化时间戳"""
        if self.config.include_timestamps:
            return datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f")[:-3] + "]"
        return ""

    def _truncate(self, text: str, max_chars: Optional[int] = None) -> str:
        """截断过长的文本"""
        max_chars = max_chars or self.config.truncate_output_chars
        if len(text) > max_chars:
            return text[:max_chars] + f"... [truncated, total {len(text)} chars]"
        return text

    def _format_dict(self, data: Any, indent: int = 2) -> str:
        """格式化字典/对象为可读字符串"""
        if data is None:
            return "null"
        try:
            if isinstance(data, (dict, list)):
                formatted = json.dumps(
                    data, indent=indent, ensure_ascii=False, default=str
                )
                return self._truncate(formatted)
            return self._truncate(str(data))
        except Exception:
            return self._truncate(str(data))

    def _write_separator(self, char: str = "─", width: int = 80) -> None:
        """写入分隔线"""
        self._logger.info(char * width)

    def _write_section_header(self, title: str) -> None:
        """写入段落标题"""
        ts = self._format_timestamp()
        self._logger.info(
            f"\n{ts} ══════════════════════════════════════════════════════════════"
        )
        self._logger.info(f"  {title}")
        self._logger.info(
            "══════════════════════════════════════════════════════════════════════"
        )

    # ==================== Public API ====================

    def log_run_start(self, variables: Optional[Dict[str, Any]] = None) -> None:
        """记录运行开始"""
        self._write_section_header("🚀 RUN START")
        self._logger.info(f"  Run ID:    {self.run_id}")
        self._logger.info(f"  Ticker:    {self.ticker}")
        self._logger.info(f"  Crew:      {self.crew_name}")
        self._logger.info(f"  Started:   {self.start_time.isoformat()}")
        if variables:
            self._logger.info(f"  Variables: {self._format_dict(variables)}")
        self._write_separator()

    def log_run_end(
        self,
        status: str,
        error: Optional[str] = None,
        summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        """记录运行结束"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        emoji = "✅" if status == "completed" else "❌"
        self._write_section_header(f"{emoji} RUN {status.upper()}")
        self._logger.info(f"  Status:    {status}")
        self._logger.info(f"  Duration:  {duration:.2f}s")
        if error:
            self._logger.info(f"  Error:     {error}")
        if summary:
            self._logger.info("  Summary:")
            for key, value in summary.items():
                self._logger.info(f"    - {key}: {value}")
        self._write_separator("═")

    def log_agent_thought(self, agent_name: str, thought: str) -> None:
        """记录 Agent 思考过程"""
        if not self.config.include_agent_thoughts:
            return

        ts = self._format_timestamp()
        self._logger.info(f"\n{ts} 💭 THOUGHT [{agent_name}]")
        self._logger.info(f"  {self._truncate(thought, 1000)}")

    def log_agent_action(
        self, agent_name: str, action: str, action_input: Any = None
    ) -> None:
        """记录 Agent 决策的动作"""
        ts = self._format_timestamp()
        self._logger.info(f"\n{ts} ⚡ ACTION [{agent_name}]")
        self._logger.info(f"  Action: {action}")
        if action_input and self.config.include_tool_io:
            self._logger.info(f"  Input:  {self._format_dict(action_input)}")

    def log_tool_call(
        self,
        agent_name: str,
        tool_name: str,
        input_data: Any = None,
        output_data: Any = None,
        duration_ms: Optional[int] = None,
        status: str = "success",
        error: Optional[str] = None,
    ) -> None:
        """记录工具调用"""
        ts = self._format_timestamp()
        status_emoji = "✓" if status == "success" else "✗"
        duration_str = f"{duration_ms}ms" if duration_ms else "N/A"

        self._logger.info(f"\n{ts} 🔧 TOOL CALL [{agent_name}] {status_emoji}")
        self._logger.info(f"  Tool:     {tool_name}")
        self._logger.info(f"  Status:   {status}")
        self._logger.info(f"  Duration: {duration_str}")

        if self.config.include_tool_io:
            if input_data:
                self._logger.info("  Input:")
                for line in self._format_dict(input_data).split("\n"):
                    self._logger.info(f"    {line}")
            if output_data and status == "success":
                self._logger.info("  Output:")
                for line in self._format_dict(output_data).split("\n"):
                    self._logger.info(f"    {line}")

        if error:
            self._logger.info(f"  Error:    {error}")

    def log_llm_call(
        self,
        agent_name: str,
        model_name: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = "success",
        error: Optional[str] = None,
        prompt_preview: Optional[str] = None,
        response_preview: Optional[str] = None,
    ) -> None:
        """记录 LLM 调用"""
        ts = self._format_timestamp()
        status_emoji = "✓" if status == "success" else "✗"
        duration_str = f"{duration_ms}ms" if duration_ms else "N/A"
        tokens_str = f"{total_tokens} tokens" if total_tokens else "N/A"

        self._logger.info(f"\n{ts} 🤖 LLM CALL [{agent_name}] {status_emoji}")
        self._logger.info(f"  Model:    {model_name}")
        self._logger.info(f"  Status:   {status}")
        self._logger.info(
            f"  Tokens:   {tokens_str} (prompt: {prompt_tokens or 'N/A'}, completion: {completion_tokens or 'N/A'})"
        )
        self._logger.info(f"  Duration: {duration_str}")

        if self.config.include_llm_prompts and prompt_preview:
            self._logger.info("  Prompt Preview:")
            self._logger.info(f"    {self._truncate(prompt_preview, 500)}")

        if self.config.include_llm_responses and response_preview:
            self._logger.info("  Response Preview:")
            self._logger.info(f"    {self._truncate(response_preview, 500)}")

        if error:
            self._logger.info(f"  Error:    {error}")

    def log_task_start(
        self, task_id: str, task_description: str, agent_name: str
    ) -> None:
        """记录 Task 开始"""
        ts = self._format_timestamp()
        self._logger.info(f"\n{ts} 📋 TASK START")
        self._logger.info(f"  Task ID:     {task_id}")
        self._logger.info(f"  Agent:       {agent_name}")
        self._logger.info(f"  Description: {self._truncate(task_description, 200)}")

    def log_task_end(
        self,
        task_id: str,
        agent_name: str,
        status: str = "completed",
        output_preview: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """记录 Task 完成"""
        ts = self._format_timestamp()
        status_emoji = "✅" if status == "completed" else "❌"
        duration_str = f"{duration_ms}ms" if duration_ms else "N/A"

        self._logger.info(f"\n{ts} 📋 TASK {status.upper()} {status_emoji}")
        self._logger.info(f"  Task ID:  {task_id}")
        self._logger.info(f"  Agent:    {agent_name}")
        self._logger.info(f"  Duration: {duration_str}")

        if output_preview:
            self._logger.info("  Output Preview:")
            self._logger.info(f"    {self._truncate(output_preview, 500)}")

    def log_activity(self, agent_name: str, activity_type: str, message: str) -> None:
        """记录通用活动"""
        ts = self._format_timestamp()
        self._logger.info(f"\n{ts} 📝 ACTIVITY [{agent_name}] ({activity_type})")
        self._logger.info(f"  {message}")

    def log_error(self, error: str, context: Optional[Dict[str, Any]] = None) -> None:
        """记录错误"""
        ts = self._format_timestamp()
        self._logger.error(f"\n{ts} ❌ ERROR")
        self._logger.error(f"  {error}")
        if context:
            self._logger.error(f"  Context: {self._format_dict(context)}")

    def log_warning(self, warning: str) -> None:
        """记录警告"""
        ts = self._format_timestamp()
        self._logger.warning(f"\n{ts} ⚠️ WARNING")
        self._logger.warning(f"  {warning}")

    def log_info(self, message: str) -> None:
        """记录信息"""
        ts = self._format_timestamp()
        self._logger.info(f"\n{ts} ℹ️ INFO")
        self._logger.info(f"  {message}")

    def close(self) -> None:
        """关闭 logger，释放资源"""
        # 从活跃 loggers 中移除
        with self._lock:
            self._active_loggers.pop(self.run_id, None)

        # 关闭所有 handlers
        for handler in self._logger.handlers[:]:
            handler.close()
            self._logger.removeHandler(handler)

    @classmethod
    def get_active_logger(cls, run_id: str) -> Optional["CrewRunLogger"]:
        """获取活跃的 run logger"""
        with cls._lock:
            return cls._active_loggers.get(run_id)

    def __enter__(self) -> "CrewRunLogger":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


# 便捷函数
def get_crew_run_logger(run_id: str) -> Optional[CrewRunLogger]:
    """获取指定 run_id 的活跃 logger"""
    return CrewRunLogger.get_active_logger(run_id)
