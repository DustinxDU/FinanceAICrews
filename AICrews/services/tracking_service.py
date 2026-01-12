from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import asyncio
import os

from AICrews.schemas.stats import (
    TaskExecutionStats,
    ToolUsageEvent,
    LLMCallEvent,
    AgentActivityEvent,
    RunEvent,
    RunEventType
)
from AICrews.schemas.tracking import (
    LiveStatusResponse,
    CompletionReportResponse,
    TrackingHistoryItem
)
from AICrews.utils.redaction import redact_sensitive, truncate_text
from AICrews.observability.crew_run_logger import (
    CrewRunLogger,
    CrewRunLoggerConfig,
    get_crew_run_logger,
)
from AICrews.observability.logging import get_logger

logger = get_logger(__name__)

# Prometheus metrics (lazy import to avoid circular dependencies)
_metrics = None
def _get_metrics():
    global _metrics
    if _metrics is None:
        try:
            from AICrews.infrastructure.metrics import get_metrics
            _metrics = get_metrics()
        except Exception as e:
            logger.warning(f"Failed to initialize Prometheus metrics: {e}")
            _metrics = False  # 标记为失败，避免重复尝试
    return _metrics if _metrics else None


# ============================================================
# litellm CustomLogger for LLM token tracking
# ============================================================

# Import litellm CustomLogger with fallback
try:
    from litellm.integrations.custom_logger import CustomLogger as LitellmCustomLogger
except ImportError:
    # Fallback if litellm not available
    class LitellmCustomLogger:
        """Fallback CustomLogger when litellm is not available."""
        pass


class NativeTrackingHandler(LitellmCustomLogger):
    """litellm callback handler for LLM token and cost tracking.

    Inherits from litellm's CustomLogger to receive LLM call events.
    Uses LogContext (contextvars) to get job_id for the current execution.

    Design decisions:
    - LLM token tracking: Handled here via litellm callbacks
    - Tool tracking: Moved to CrewAI EventBus listeners (crewai_event_listener.py)
    - Context: Uses get_context("job_id") from AICrews.observability.logging

    Tracking levels (configured via FAIC_EVENT_TRACKING_LEVEL):
    - "full": log_pre_call + log_success_event + log_failure_event
    - "minimal": log_success_event + log_failure_event only
    """

    def __init__(self, *, level: str = "minimal"):
        """Initialize the tracking handler.

        Args:
            level: Tracking level ("full" or "minimal")
        """
        super().__init__()
        self._level = level
        self._llm_preview_max_chars = int(
            os.getenv("FAIC_LLM_TRACE_PREVIEW_MAX_CHARS", "2000")
        )

    def _get_job_id(self) -> Optional[str]:
        """Get current job_id from LogContext (contextvars)."""
        try:
            from AICrews.observability.logging import get_context
            return get_context("job_id")
        except Exception as e:
            logger.debug(f"Failed to get job_id from LogContext: {e}")
            return None

    def _get_job_id_from_kwargs(self, kwargs: Dict[str, Any]) -> Optional[str]:
        """Best-effort fallback: derive job_id from litellm kwargs metadata.

        litellm callbacks may execute in ThreadPoolExecutor which can break
        contextvars propagation, so we allow metadata.run_id as a fallback.
        """
        try:
            metadata = kwargs.get("metadata")
            if isinstance(metadata, dict):
                run_id = metadata.get("run_id") or metadata.get("trace_id")
                if run_id:
                    return str(run_id)
        except Exception as e:
            logger.debug(f"Failed to get job_id from litellm kwargs: {e}")
            return None
        return None

    def _resolve_provider_and_model(self, *, model: str, kwargs: Dict[str, Any]) -> tuple[str, str]:
        """Resolve (provider_key, model_key) for tracking + pricing.

        Prefers stable metadata injected by our LLMFactory (`faic_provider_key`,
        `faic_model_key`), which supports OpenAI-compatible providers where the
        model string may not be namespaced.
        """
        metadata = kwargs.get("metadata")
        if isinstance(metadata, dict):
            provider_key = metadata.get("faic_provider_key")
            model_key = metadata.get("faic_model_key")
            if (
                isinstance(provider_key, str)
                and provider_key
                and isinstance(model_key, str)
                and model_key
            ):
                return provider_key, model_key

        if "/" in str(model):
            provider_key, model_key = str(model).split("/", 1)
            return provider_key, model_key

        return "unknown", str(model)

    def _estimate_llm_cost_usd(
        self,
        *,
        provider_key: str,
        model_key: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> tuple[Optional[float], Optional[str], Optional[str]]:
        """Estimate USD cost for one call based on pricing.yaml (best-effort)."""
        try:
            from AICrews.llm.core.config_store import get_config_store

            store = get_config_store()
            price = store.get_price(provider_key, model_key)
            if not price:
                return None, getattr(store.pricing, "version", None), getattr(
                    store.pricing, "updated", None
                )

            input_price = float(price.get("input") or 0.0)  # USD / 1M tokens
            output_price = float(price.get("output") or 0.0)  # USD / 1M tokens
            cost = (prompt_tokens / 1_000_000) * input_price + (
                completion_tokens / 1_000_000
            ) * output_price

            return cost, getattr(store.pricing, "version", None), getattr(
                store.pricing, "updated", None
            )
        except Exception:
            logger.debug("Failed to estimate LLM cost", exc_info=True)
            return None, None, None

    def log_pre_call(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        kwargs: Dict[str, Any],
    ) -> None:
        """Called before LLM call (full tracking mode only).

        Args:
            model: Model name/identifier
            messages: Messages being sent to the LLM
            kwargs: Additional call kwargs
        """
        if self._level != "full":
            return

        job_id = self._get_job_id() or self._get_job_id_from_kwargs(kwargs)
        if not job_id:
            return  # Not in a crew run context, skip

        # Record start event for detailed tracking
        try:
            # Extract prompt preview
            prompt_preview = None
            if messages:
                # Combine message contents for preview
                parts = []
                for msg in messages[:3]:  # Limit to first 3 messages
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        parts.append(content[:500])
                prompt_preview = "\n---\n".join(parts)
                if prompt_preview:
                    prompt_preview = truncate_text(
                        redact_sensitive(prompt_preview),
                        limit=self._llm_preview_max_chars
                    )

            TrackingService().add_activity(
                job_id,
                AgentActivityEvent(
                    agent_name="LLM",
                    activity_type="llm_start",
                    message=f"Starting LLM call to {model}",
                    details={"model": model, "prompt_preview": prompt_preview},
                    timestamp=datetime.now(),
                ),
            )
        except Exception:
            logger.debug("Failed to record LLM pre-call event", exc_info=True)

    def log_success_event(
        self,
        kwargs: Dict[str, Any],
        response_obj: Any,
        start_time: float,
        end_time: float,
    ) -> None:
        """Called when LLM call succeeds.

        Args:
            kwargs: Original call kwargs (contains model, messages, etc.)
            response_obj: Response from the LLM (dict with usage info)
            start_time: Call start timestamp
            end_time: Call end timestamp
        """
        job_id = self._get_job_id() or self._get_job_id_from_kwargs(kwargs)
        if not job_id:
            return  # Not in a crew run context, skip

        try:
            # Calculate duration
            duration_ms = int((end_time - start_time) * 1000)

            # Extract model info
            model = str(kwargs.get("model", "unknown"))
            provider_key, model_key = self._resolve_provider_and_model(model=model, kwargs=kwargs)

            # Extract token usage from response
            prompt_tokens = None
            completion_tokens = None
            total_tokens = None

            if isinstance(response_obj, dict) and "usage" in response_obj:
                usage = response_obj["usage"]
                if usage:
                    prompt_tokens = getattr(usage, "prompt_tokens", None)
                    completion_tokens = getattr(usage, "completion_tokens", None)
                    total_tokens = getattr(usage, "total_tokens", None)

            # Extract response preview
            response_preview = None
            try:
                if isinstance(response_obj, dict):
                    choices = response_obj.get("choices", [])
                    if choices and len(choices) > 0:
                        message = choices[0].get("message", {})
                        content = message.get("content", "")
                        if content:
                            response_preview = truncate_text(
                                redact_sensitive(str(content)),
                                limit=self._llm_preview_max_chars
                            )
            except Exception as e:
                logger.debug(f"Failed to extract response preview: {e}")

            # Estimate cost
            estimated_cost_usd, pricing_version, pricing_updated = self._estimate_llm_cost_usd(
                provider_key=provider_key,
                model_key=model_key,
                prompt_tokens=int(prompt_tokens or 0),
                completion_tokens=int(completion_tokens or 0),
            )

            # Record LLM event
            TrackingService().add_llm_event(
                job_id,
                LLMCallEvent(
                    agent_name="Agent",  # Will be enriched by context if available
                    llm_provider=provider_key,
                    model_name=model_key,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    duration_ms=duration_ms,
                    status="success",
                    timestamp=datetime.now(),
                    response_preview=response_preview,
                    estimated_cost_usd=estimated_cost_usd,
                    pricing_version=pricing_version,
                    pricing_updated=pricing_updated,
                ),
            )
        except Exception:
            logger.debug("Failed to record LLM success event", exc_info=True)

    def log_failure_event(
        self,
        kwargs: Dict[str, Any],
        response_obj: Any,
        start_time: float,
        end_time: float,
    ) -> None:
        """Called when LLM call fails.

        Args:
            kwargs: Original call kwargs
            response_obj: Error response or exception
            start_time: Call start timestamp
            end_time: Call end timestamp
        """
        job_id = self._get_job_id() or self._get_job_id_from_kwargs(kwargs)
        if not job_id:
            return  # Not in a crew run context, skip

        try:
            duration_ms = int((end_time - start_time) * 1000)
            model = str(kwargs.get("model", "unknown"))
            provider_key, model_key = self._resolve_provider_and_model(model=model, kwargs=kwargs)

            # Extract error message
            error_message = str(response_obj) if response_obj else "Unknown error"

            TrackingService().add_llm_event(
                job_id,
                LLMCallEvent(
                    agent_name="Agent",
                    llm_provider=provider_key,
                    model_name=model_key,
                    duration_ms=duration_ms,
                    status="failed",
                    error_message=truncate_text(error_message, limit=500),
                    timestamp=datetime.now(),
                ),
            )
        except Exception:
            logger.debug("Failed to record LLM failure event", exc_info=True)


class TrackingService:
    """任务跟踪服务

    Memory Management:
    - LRU eviction (max runs in memory, configurable via FAIC_TRACKING_MAX_RUNS)
    - Time-based retention (configurable via FAIC_TRACKING_RETENTION_HOURS)
    - Per-run event limits (configurable via FAIC_TRACKING_MAX_EVENTS_PER_RUN)
    - Per-run tool/LLM/activity event caps to prevent unbounded list growth
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Memory management configuration
        self._max_runs_in_memory = int(os.getenv("FAIC_TRACKING_MAX_RUNS", "1000"))
        self._retention_hours = int(os.getenv("FAIC_TRACKING_RETENTION_HOURS", "24"))
        self._max_events_per_run = int(os.getenv("FAIC_TRACKING_MAX_EVENTS_PER_RUN", "5000"))

        # Per-run list caps (tool_calls, llm_calls, agent_activities within TaskExecutionStats)
        self._max_tool_events_per_run = int(os.getenv("FAIC_TRACKING_MAX_TOOL_EVENTS_PER_RUN", "2000"))
        self._max_llm_events_per_run = int(os.getenv("FAIC_TRACKING_MAX_LLM_EVENTS_PER_RUN", "2000"))
        self._max_activity_events_per_run = int(os.getenv("FAIC_TRACKING_MAX_ACTIVITY_EVENTS_PER_RUN", "1000"))

        # CrewRunLogger configuration
        self._crew_run_logging_enabled = os.getenv("FAIC_CREW_RUN_LOGGING", "true").lower() == "true"
        self._crew_run_log_dir = os.getenv("FAIC_CREW_RUN_LOG_DIR", "logs/crew_runs")
        self._run_loggers: Dict[str, CrewRunLogger] = {}

        # OrderedDict for LRU tracking (insertion order = access order via move_to_end)
        self._stats: OrderedDict[str, TaskExecutionStats] = OrderedDict()
        # run_id -> list of RunEvent objects
        self._events: OrderedDict[str, List[RunEvent]] = OrderedDict()
        self.storage = None
        self.ws_manager = None
        self._initialized = True

        logger.info(
            f"TrackingService initialized: max_runs={self._max_runs_in_memory}, "
            f"retention_hours={self._retention_hours}, "
            f"max_events_per_run={self._max_events_per_run}, "
            f"crew_run_logging={self._crew_run_logging_enabled}"
        )

    def set_dependencies(self, storage: Any, ws_manager: Any) -> None:
        """设置持久化与 WebSocket 依赖。

        storage: backend.app.storage.get_storage() 的返回值（实现位于 AICrews.infrastructure.storage）
        ws_manager: backend.app.ws.run_log_manager.manager
        """
        self.storage = storage
        self.ws_manager = ws_manager

    def _is_run_expired(self, stats: TaskExecutionStats) -> bool:
        """Check if run is expired based on retention policy."""
        if not stats.completed_at:
            return False
        cutoff = datetime.now() - timedelta(hours=self._retention_hours)
        return stats.completed_at < cutoff

    def _evict_oldest_run(self) -> bool:
        """
        Evict the oldest run from memory (LRU policy).

        Only evicts completed/failed runs. Running runs are protected.
        Evicted runs remain in storage and can be restored via get_stats().

        Returns:
            True if a run was evicted, False if no evictable runs found.
        """
        # Find oldest evictable run (completed/failed)
        for run_id in list(self._stats.keys()):  # Iterate over copy to allow modification
            stats = self._stats[run_id]
            if stats.status in ["completed", "failed"]:
                # Evict this run
                del self._stats[run_id]
                self._events.pop(run_id, None)
                logger.debug(
                    f"[TrackingService] LRU eviction: run_id={run_id}, status={stats.status}, "
                    f"new_size={len(self._stats)}"
                )
                return True

        # If no evictable runs found (all running), log warning
        logger.warning(
            f"[TrackingService] Cache full ({len(self._stats)} runs) but all are running - cannot evict"
        )
        return False

    def _enforce_memory_limit(self) -> None:
        """
        Enforce max runs in memory limit via LRU eviction.

        Called before adding new runs to ensure we stay under the limit.
        Stops if no evictable runs are found (prevents infinite loop).
        """
        while len(self._stats) >= self._max_runs_in_memory:
            if not self._evict_oldest_run():
                # No evictable runs - break to prevent infinite loop
                break

    def init_job(self, job_id: str, ticker: str, crew_name: str) -> None:
        """初始化任务统计容器。

        Enforces memory limit via LRU eviction before adding new run.
        Also creates a CrewRunLogger for detailed run logging if enabled.
        """
        if job_id in self._stats:
            return

        # Enforce memory limit before adding new run
        self._enforce_memory_limit()

        stats = TaskExecutionStats(
            job_id=job_id,
            ticker=ticker,
            crew_name=crew_name,
            started_at=datetime.now(),
            status="running",
        )
        self._stats[job_id] = stats

        # Create CrewRunLogger for detailed run logging
        if self._crew_run_logging_enabled:
            try:
                config = CrewRunLoggerConfig(log_dir=self._crew_run_log_dir)
                run_logger = CrewRunLogger(
                    run_id=job_id,
                    ticker=ticker,
                    crew_name=crew_name,
                    config=config,
                )
                self._run_loggers[job_id] = run_logger
                run_logger.log_run_start(variables={"ticker": ticker, "crew_name": crew_name})
                logger.debug(f"CrewRunLogger created for job {job_id}: {run_logger.log_file_path}")
            except Exception as e:
                logger.warning(f"Failed to create CrewRunLogger for job {job_id}: {e}")

        if self.storage:
            try:
                self.storage.create_task_stats(stats)
            except Exception as e:
                logger.error(f"Failed to create task stats in storage: {e}")

    def get_stats(self, job_id: str) -> Optional[TaskExecutionStats]:
        """获取任务统计 (内存优先，必要时回退持久化)。

        Applies retention policy: expired runs are not restored from storage.
        """
        # Mark run as recently accessed (LRU)
        if job_id in self._stats:
            self._stats.move_to_end(job_id)

        stats = self._stats.get(job_id)
        if stats:
            return stats

        if self.storage:
            try:
                stats = self.storage.get_task_stats(job_id)

                # Check retention policy before restoring to memory
                if stats and self._is_run_expired(stats):
                    logger.debug(f"[TrackingService] Run {job_id} expired, not restoring to memory")
                    return None  # Don't restore expired runs

                # Restore to memory (respecting memory limit)
                if stats:
                    self._enforce_memory_limit()
                    self._stats[job_id] = stats

                return stats
            except Exception as e:
                logger.warning(f"Failed to get task stats from storage: {e}")
        return None

    async def _broadcast(self, run_id: str, payload: Dict[str, Any]) -> None:
        """广播事件到 WebSocket (run_log_manager ring-buffer)。"""
        if not self.ws_manager:
            return
        try:
            await self.ws_manager.broadcast_to_run(run_id, payload)
        except Exception as e:
            logger.error(f"Failed to broadcast run event: {e}")

    def _schedule_broadcast(self, run_id: str, payload: Dict[str, Any]) -> None:
        """在同步/线程上下文中安全调度广播协程。"""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast(run_id, payload))
        except RuntimeError:
            # 线程中通常没有 running loop
            try:
                asyncio.run(self._broadcast(run_id, payload))
            except Exception as e:
                logger.error(f"Failed to run broadcast coroutine: {e}")

    def _get_run_logger(self, job_id: str) -> Optional[CrewRunLogger]:
        """获取指定 job 的 CrewRunLogger（如果存在）"""
        return self._run_loggers.get(job_id)

    def _add_run_event(self, event: RunEvent) -> None:
        """内部辅助：存储并广播运行事件

        Enforces per-run event limit (configurable via FAIC_TRACKING_MAX_EVENTS_PER_RUN).
        """
        run_id = event.run_id
        if run_id not in self._events:
            self._events[run_id] = []
        self._events[run_id].append(event)

        # Limit memory: FIFO eviction when exceeding max events per run
        if len(self._events[run_id]) > self._max_events_per_run:
            evicted = self._events[run_id].pop(0)
            logger.debug(
                f"[TrackingService] Run {run_id} event buffer full ({self._max_events_per_run}), evicted oldest event"
            )

        # 广播（兼容线程池执行）
        self._schedule_broadcast(run_id, event.model_dump(mode="json"))

    def get_run_events(self, run_id: str) -> List[RunEvent]:
        """获取任务的所有运行事件"""
        return self._events.get(run_id, [])
        
    def add_tool_event(self, job_id: str, event: ToolUsageEvent) -> None:
        """添加工具使用事件

        Enforces per-run tool event limit to prevent unbounded list growth.
        Also writes to CrewRunLogger if enabled.
        """
        stats = self._stats.get(job_id)
        if stats:
            # Enforce per-run tool event limit (FIFO eviction)
            if len(stats.tool_calls) >= self._max_tool_events_per_run:
                evicted = stats.tool_calls.pop(0)
                logger.debug(
                    f"[TrackingService] Run {job_id} tool_calls full ({self._max_tool_events_per_run}), evicted oldest"
                )

            stats.tool_calls.append(event)
            if event.status in ("success", "failed"):
                stats.tool_call_count += 1
                if event.status == "success":
                    stats.tool_success_count += 1
                else:
                    stats.tool_failure_count += 1

            # Write to CrewRunLogger
            run_logger = self._get_run_logger(job_id)
            if run_logger:
                run_logger.log_tool_call(
                    agent_name=event.agent_name or "Unknown",
                    tool_name=event.tool_name,
                    input_data=event.input_data,
                    output_data=event.output_data,
                    duration_ms=event.duration_ms,
                    status=event.status,
                    error=event.error_message,
                )

            # 创建统一运行事件
            payload = event.model_dump()
            payload.setdefault("message", f"Tool: {event.tool_name} ({event.status})")
            run_event = RunEvent(
                run_id=job_id,
                event_type=RunEventType.TOOL_RESULT if event.status in ["success", "failed"] else RunEventType.TOOL_CALL,
                agent_name=event.agent_name,
                severity="error" if event.status == "failed" else "info",
                payload=payload,
            )
            self._add_run_event(run_event)

    def add_llm_event(self, job_id: str, event: LLMCallEvent) -> None:
        """添加 LLM 调用事件

        Enforces per-run LLM event limit to prevent unbounded list growth.
        Also writes to CrewRunLogger if enabled.
        """
        stats = self._stats.get(job_id)
        if stats:
            # Enforce per-run LLM event limit (FIFO eviction)
            if len(stats.llm_calls) >= self._max_llm_events_per_run:
                evicted = stats.llm_calls.pop(0)
                logger.debug(
                    f"[TrackingService] Run {job_id} llm_calls full ({self._max_llm_events_per_run}), evicted oldest"
                )

            stats.llm_calls.append(event)
            if event.status in ("success", "failed"):
                stats.llm_call_count += 1
                if event.prompt_tokens:
                    stats.total_prompt_tokens += event.prompt_tokens
                if event.completion_tokens:
                    stats.total_completion_tokens += event.completion_tokens
                if event.total_tokens:
                    stats.total_tokens += event.total_tokens

            # Write to CrewRunLogger
            run_logger = self._get_run_logger(job_id)
            if run_logger:
                run_logger.log_llm_call(
                    agent_name=event.agent_name or "Unknown",
                    model_name=event.model_name or "unknown",
                    prompt_tokens=event.prompt_tokens,
                    completion_tokens=event.completion_tokens,
                    total_tokens=event.total_tokens,
                    duration_ms=event.duration_ms,
                    status=event.status,
                    error=event.error_message,
                    # Enhanced debug fields
                    prompt_preview=event.prompt_preview,
                    response_preview=event.response_preview,
                )

            # 创建统一运行事件
            payload = event.model_dump()
            payload.setdefault("message", f"LLM: {event.model_name} ({event.status})")
            run_event = RunEvent(
                run_id=job_id,
                event_type=RunEventType.LLM_CALL,
                agent_name=event.agent_name,
                severity="error" if event.status == "failed" else "info",
                payload=payload,
            )
            self._add_run_event(run_event)
            
    def add_activity(self, job_id: str, event: AgentActivityEvent) -> None:
        """添加 Agent 活动事件

        Enforces per-run activity event limit to prevent unbounded list growth.
        Also writes to CrewRunLogger if enabled.
        """
        stats = self._stats.get(job_id)
        if stats:
            # Enforce per-run activity event limit (FIFO eviction)
            if len(stats.agent_activities) >= self._max_activity_events_per_run:
                evicted = stats.agent_activities.pop(0)
                logger.debug(
                    f"[TrackingService] Run {job_id} agent_activities full ({self._max_activity_events_per_run}), evicted oldest"
                )

            stats.agent_activities.append(event)

            # Write to CrewRunLogger
            run_logger = self._get_run_logger(job_id)
            if run_logger:
                # Map activity type to appropriate log method
                activity_type = event.activity_type or "activity"
                if activity_type == "thought":
                    run_logger.log_agent_thought(
                        agent_name=event.agent_name or "Unknown",
                        thought=event.message or "",
                    )
                elif activity_type == "error":
                    run_logger.log_error(
                        error=event.message or "Unknown error",
                        context=event.details,
                    )
                elif activity_type == "warning":
                    run_logger.log_warning(
                        warning=event.message or "Warning",
                    )
                elif activity_type == "phase":
                    run_logger.log_info(
                        message=event.message or "Phase update",
                    )
                else:
                    run_logger.log_activity(
                        agent_name=event.agent_name or "Unknown",
                        activity_type=activity_type,
                        message=event.message or "",
                    )

            # 创建统一运行事件
            run_event = RunEvent(
                run_id=job_id,
                event_type=RunEventType.ACTIVITY,
                agent_name=event.agent_name,
                payload=event.model_dump()
            )
            self._add_run_event(run_event)

    def add_task_output_event(
        self,
        job_id: str,
        agent_name: str,
        task_id: str,
        payload: Dict[str, Any],
        severity: str = "info",
    ) -> None:
        """Record a TASK_OUTPUT event with structured output diagnostics.

        This event captures task completion with the 3-layer payload structure:
        - summary: preview of output, validation status
        - artifact_ref: path to stored artifact
        - diagnostics: output_mode, guardrail_retries, etc.

        Args:
            job_id: The job/run ID
            agent_name: Name of the agent that produced the output
            task_id: The task ID
            payload: 3-layer payload (summary, artifact_ref, diagnostics)
            severity: Event severity (default "info")
        """
        # Redact sensitive data from payload (especially summary.raw_preview)
        safe_payload = redact_sensitive(payload)

        # Truncate raw_preview if present (increased limit for comprehensive reports)
        if "summary" in safe_payload and "raw_preview" in safe_payload["summary"]:
            safe_payload["summary"]["raw_preview"] = truncate_text(
                safe_payload["summary"]["raw_preview"], limit=10000
            )

        run_event = RunEvent(
            run_id=job_id,
            event_type=RunEventType.TASK_OUTPUT,
            agent_name=agent_name,
            task_id=task_id,
            severity=severity,
            payload=safe_payload,
        )
        self._add_run_event(run_event)

        # Record Prometheus metrics (LOW CARDINALITY - no job_id/task_id)
        metrics = _get_metrics()
        if metrics:
            try:
                metrics.record_task_output_event(
                    payload=safe_payload
                )
            except Exception as e:
                logger.warning(f"Failed to record task output metrics: {e}")

    def complete_job(self, job_id: str, status: str = "completed", error: Optional[str] = None) -> None:
        """完成任务跟踪

        Also closes the CrewRunLogger and writes a summary if enabled.
        """
        stats = self._stats.get(job_id)
        if stats:
            stats.completed_at = datetime.now()
            stats.status = status
            if error:
                stats.error_message = error
            if stats.started_at:
                delta = stats.completed_at - stats.started_at
                stats.total_duration_ms = int(delta.total_seconds() * 1000)

            # Close CrewRunLogger and write summary
            run_logger = self._run_loggers.pop(job_id, None)
            if run_logger:
                try:
                    summary = {
                        "tool_calls": stats.tool_call_count,
                        "tool_success": stats.tool_success_count,
                        "tool_failures": stats.tool_failure_count,
                        "llm_calls": stats.llm_call_count,
                        "total_tokens": stats.total_tokens,
                        "duration_ms": stats.total_duration_ms,
                    }
                    run_logger.log_run_end(status=status, error=error, summary=summary)
                    run_logger.close()
                    logger.debug(f"CrewRunLogger closed for job {job_id}")
                except Exception as e:
                    logger.warning(f"Failed to close CrewRunLogger for job {job_id}: {e}")

            # 同步到持久化存储
            if self.storage:
                try:
                    self.storage.update_task_stats(job_id, stats.model_dump())
                except Exception as e:
                    logger.error(f"Failed to update task stats in storage: {e}")

            # 创建统一运行事件
            run_event = RunEvent(
                run_id=job_id,
                event_type=RunEventType.TASK_STATE,
                severity="error" if status == "failed" else "info",
                payload={
                    "status": status,
                    "error": error,
                    "total_duration_ms": stats.total_duration_ms,
                    "timestamp": stats.completed_at.isoformat()
                }
            )
            self._add_run_event(run_event)
            
    def list_active_jobs(self) -> List[str]:
        """列出活跃任务"""
        return [
            job_id for job_id, stats in self._stats.items()
            if stats.status == "running"
        ]

    def get_live_status_data(self, job_id: str) -> Optional[LiveStatusResponse]:
        """获取任务的实时执行状态"""
        stats = self.get_stats(job_id)
        
        if not stats:
            # 尝试从 JobManager 获取基本信息
            from AICrews.infrastructure.jobs import get_job_manager
            job_manager = get_job_manager()
            job = job_manager.get_status(job_id)
            if not job:
                return None
            
            return LiveStatusResponse(
                job_id=job_id,
                status=job.status.value,
                ticker=job.ticker or "",
                crew_name=job.crew_name or "",
            )
        
        # 计算经过时间
        elapsed_ms = None
        if stats.started_at:
            delta = datetime.now() - stats.started_at
            elapsed_ms = int(delta.total_seconds() * 1000)
        
        # 获取最近活动
        recent_activities = []
        for activity in stats.agent_activities[-10:]:
            recent_activities.append({
                "timestamp": activity.timestamp.isoformat(),
                "agent": activity.agent_name,
                "type": activity.activity_type,
                "message": activity.message,
            })
        
        # 获取当前活动
        current_agent = None
        current_activity = None
        if stats.agent_activities:
            last_activity = stats.agent_activities[-1]
            current_agent = last_activity.agent_name
            current_activity = last_activity.message
        
        return LiveStatusResponse(
            job_id=job_id,
            status=stats.status,
            ticker=stats.ticker,
            crew_name=stats.crew_name,
            started_at=stats.started_at.isoformat() if stats.started_at else None,
            elapsed_ms=elapsed_ms,
            current_agent=current_agent,
            current_activity=current_activity,
            tool_call_count=stats.tool_call_count,
            llm_call_count=stats.llm_call_count,
            total_tokens=stats.total_tokens,
            recent_activities=recent_activities,
        )

    def get_completion_report_data(self, job_id: str) -> Optional[CompletionReportResponse]:
        """获取任务完成报告"""
        stats = self.get_stats(job_id)
        
        if not stats:
            # 尝试从持久化存储获取
            if self.storage:
                stats = self.storage.get_task_stats(job_id)
        
        if not stats:
            return None
        
        # 计算持续时间
        duration_seconds = None
        if stats.total_duration_ms:
            duration_seconds = stats.total_duration_ms / 1000
            
        summary = stats.to_summary()
        
        return CompletionReportResponse(
            job_id=job_id,
            ticker=stats.ticker,
            crew_name=stats.crew_name,
            status=stats.status,
            started_at=stats.started_at.isoformat() if stats.started_at else None,
            completed_at=stats.completed_at.isoformat() if stats.completed_at else None,
            duration_seconds=duration_seconds,
            tools_summary=summary["tools"],
            llm_summary=summary["llm"],
            tool_calls=[
                {
                    "timestamp": call.timestamp.isoformat() if call.timestamp else None,
                    "tool_name": call.tool_name,
                    "agent_name": call.agent_name,
                    "status": call.status,
                    "duration_ms": call.duration_ms,
                    "error": call.error_message,
                }
                for call in stats.tool_calls
            ],
            llm_calls=[
                {
                    "timestamp": call.timestamp.isoformat() if call.timestamp else None,
                    "agent_name": call.agent_name,
                    "provider": call.llm_provider,
                    "model": call.model_name,
                    "status": call.status,
                    "tokens": call.total_tokens,
                    "duration_ms": call.duration_ms,
                }
                for call in stats.llm_calls
            ],
        )

    def list_tracking_history(self, limit: int = 20) -> List[TrackingHistoryItem]:
        """获取历史任务统计列表"""
        if not self.storage:
            return []
            
        stats_list = self.storage.list_task_stats(limit=limit)
        
        return [
            TrackingHistoryItem(
                job_id=stats.job_id,
                ticker=stats.ticker,
                crew_name=stats.crew_name,
                status=stats.status,
                started_at=stats.started_at.isoformat() if stats.started_at else None,
                duration_seconds=stats.total_duration_ms / 1000 if stats.total_duration_ms else None,
                tool_calls=stats.tool_call_count,
                llm_calls=stats.llm_call_count,
                total_tokens=stats.total_tokens,
            )
            for stats in stats_list
        ]
