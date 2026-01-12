"""
CrewAI EventBus Listener for Event Tracking

This module registers listeners for CrewAI's EventBus system to track:
- Tool usage events (ToolUsageStarted/Finished/Error)
- LLM call events (LLMCallStarted/Completed/Failed)
- Task events (TaskStarted/Completed/Failed)
- Agent delegation events (AgentDelegation)

Design decisions:
- All events: CrewAI EventBus (preferred over litellm callbacks)
- Context: Uses get_context("job_id") from LogContext system
- Why not litellm callbacks: litellm executes callbacks in ThreadPoolExecutor,
  which breaks contextvars propagation. CrewAI EventBus runs in the same thread.

Usage:
    from AICrews.observability.crewai_event_listener import (
        register_crewai_event_listeners,
        register_litellm_callback,
    )

    # In lifespan.py startup
    register_crewai_event_listeners(level="minimal")
    register_litellm_callback(level="minimal")  # Kept for backward compatibility
"""

import json
from datetime import datetime
from typing import Any

from AICrews.observability.logging import get_logger

logger = get_logger(__name__)

# Global flags to prevent double registration
_crewai_registered = False
_litellm_registered = False


def _extract_response_metadata(response: Any) -> dict[str, Any] | None:
    """Best-effort extraction of metadata dict from a litellm/crewai response object."""
    if response is None:
        return None

    # Common pattern: response.metadata (dict)
    try:
        metadata = getattr(response, "metadata", None)
        if isinstance(metadata, dict):
            return metadata
    except Exception:
        pass

    # Common litellm pattern: response._hidden_params["metadata"]
    try:
        hidden = getattr(response, "_hidden_params", None) or getattr(
            response, "hidden_params", None
        )
        if isinstance(hidden, dict):
            metadata = hidden.get("metadata")
            if isinstance(metadata, dict):
                return metadata
    except Exception:
        pass

    return None


def _extract_response_api_base(response: Any) -> str | None:
    """Best-effort extraction of api_base/base_url from response hidden params."""
    if response is None:
        return None
    try:
        hidden = getattr(response, "_hidden_params", None) or getattr(
            response, "hidden_params", None
        )
        if isinstance(hidden, dict):
            api_base = hidden.get("api_base") or hidden.get("base_url") or hidden.get("api_base_url")
            if isinstance(api_base, str) and api_base:
                return api_base
    except Exception:
        pass
    return None


def _infer_provider_from_api_base(api_base: str) -> str | None:
    """Infer provider_key by matching config/llm/providers.yaml endpoints.api_base."""
    if not api_base:
        return None
    try:
        from AICrews.llm.core.config_store import get_config_store

        store = get_config_store()
        normalized = api_base.rstrip("/")
        for provider_key, provider_cfg in store.providers.providers.items():
            try:
                cfg_base = str(getattr(provider_cfg.endpoints, "api_base", "") or "").rstrip("/")
                if cfg_base and cfg_base == normalized:
                    return provider_key
            except Exception:
                continue
    except Exception:
        return None
    return None


def _resolve_llm_identity(*, model_name: str, response: Any) -> tuple[str, str]:
    """Resolve (provider_key, model_key) for pricing + display.

    Priority:
    1) Metadata injected by our LLM factory (`faic_provider_key`, `faic_model_key`)
    2) Parse `model_name` as `provider/model_key` (strip provider prefix)
    3) Fallback to ("unknown", model_name)
    """
    md = _extract_response_metadata(response) or {}
    faic_provider = md.get("faic_provider_key")
    faic_model = md.get("faic_model_key")
    if (
        isinstance(faic_provider, str)
        and faic_provider
        and isinstance(faic_model, str)
        and faic_model
    ):
        return faic_provider, faic_model

    if model_name and "/" in model_name:
        provider = model_name.split("/", 1)[0]
        model_key = model_name.split("/", 1)[1]
        return provider, model_key

    # 3) Last resort: infer provider from response api_base (useful for OpenAI-compatible)
    api_base = _extract_response_api_base(response)
    inferred = _infer_provider_from_api_base(api_base) if api_base else None
    if inferred:
        return inferred, model_name or "unknown"

    return "unknown", model_name or "unknown"


def register_crewai_event_listeners(level: str = "minimal") -> bool:
    """Register CrewAI EventBus listeners for event tracking.

    This function registers event handlers for CrewAI events:
    - Tool usage events (Started/Finished/Error)
    - LLM call events (Started/Completed/Failed)
    - Task events (Started/Completed) - if available

    Should be called once during application startup (in lifespan.py).

    Args:
        level: Tracking level ("full" or "minimal")
            - "full": Track all events including Started events
            - "minimal": Track Finished/Completed/Error events only

    Returns:
        True if registration successful, False otherwise
    """
    global _crewai_registered

    if _crewai_registered:
        logger.debug("CrewAI event listeners already registered, skipping")
        return True

    try:
        from crewai.events.event_bus import crewai_event_bus
        from crewai.events.types.tool_usage_events import (
            ToolUsageStartedEvent,
            ToolUsageFinishedEvent,
            ToolUsageErrorEvent,
        )
        from crewai.events.types.llm_events import (
            LLMCallStartedEvent,
            LLMCallCompletedEvent,
            LLMCallFailedEvent,
        )
    except ImportError as e:
        logger.warning(f"Failed to import CrewAI event types: {e}")
        return False

    try:
        from AICrews.observability.logging import get_context
        from AICrews.services.tracking_service import TrackingService
        from AICrews.schemas.stats import ToolUsageEvent, LLMCallEvent
    except ImportError as e:
        logger.error(f"Failed to import tracking dependencies: {e}")
        return False

    # ========================================
    # Tool Event Handlers
    # ========================================

    # Register ToolUsageStartedEvent handler (full mode only)
    if level == "full":
        @crewai_event_bus.on(ToolUsageStartedEvent)
        def on_tool_started(source: Any, event: ToolUsageStartedEvent) -> None:
            """Handle tool usage started event."""
            job_id = get_context("job_id")
            if not job_id:
                return  # Not in a crew run context, skip

            try:
                TrackingService().add_tool_event(
                    job_id,
                    ToolUsageEvent(
                        tool_name=event.tool_name,
                        agent_name=event.agent_role,
                        status="running",
                        input_data=_safe_truncate(str(event.tool_args), 500)
                        if event.tool_args
                        else None,
                        timestamp=datetime.now(),
                    ),
                )
            except Exception:
                logger.debug("Failed to record tool started event", exc_info=True)

    # Register ToolUsageFinishedEvent handler (always)
    @crewai_event_bus.on(ToolUsageFinishedEvent)
    def on_tool_finished(source: Any, event: ToolUsageFinishedEvent) -> None:
        """Handle tool usage finished event."""
        job_id = get_context("job_id")
        if not job_id:
            return  # Not in a crew run context, skip

        try:
            # Calculate duration if timestamps available
            duration_ms = None
            if hasattr(event, "started_at") and hasattr(event, "finished_at"):
                if event.started_at and event.finished_at:
                    delta = event.finished_at - event.started_at
                    duration_ms = int(delta.total_seconds() * 1000)

            # Best-effort include input args even in minimal mode (improves debuggability)
            input_data = None
            if hasattr(event, "tool_args") and event.tool_args:
                if isinstance(event.tool_args, dict):
                    input_data = event.tool_args
                else:
                    input_data = {"args": _safe_truncate(str(event.tool_args), 500)}

            TrackingService().add_tool_event(
                job_id,
                ToolUsageEvent(
                    tool_name=event.tool_name,
                    agent_name=event.agent_role,
                    status="success",
                    duration_ms=duration_ms,
                    input_data=input_data,
                    output_data=_safe_json_serialize(event.output, 10000)
                    if hasattr(event, "output") and event.output
                    else None,
                    timestamp=datetime.now(),
                ),
            )
        except Exception:
            logger.debug("Failed to record tool finished event", exc_info=True)

    # Register ToolUsageErrorEvent handler (always)
    @crewai_event_bus.on(ToolUsageErrorEvent)
    def on_tool_error(source: Any, event: ToolUsageErrorEvent) -> None:
        """Handle tool usage error event."""
        job_id = get_context("job_id")
        if not job_id:
            return  # Not in a crew run context, skip

        try:
            input_data = None
            if hasattr(event, "tool_args") and event.tool_args:
                if isinstance(event.tool_args, dict):
                    input_data = event.tool_args
                else:
                    input_data = {"args": _safe_truncate(str(event.tool_args), 500)}

            TrackingService().add_tool_event(
                job_id,
                ToolUsageEvent(
                    tool_name=event.tool_name,
                    agent_name=event.agent_role,
                    status="failed",
                    input_data=input_data,
                    error_message=str(event.error) if hasattr(event, "error") else None,
                    timestamp=datetime.now(),
                ),
            )
        except Exception:
            logger.debug("Failed to record tool error event", exc_info=True)

    # ========================================
    # LLM Event Handlers
    # ========================================

    # Register LLMCallStartedEvent handler (full mode only)
    if level == "full":
        @crewai_event_bus.on(LLMCallStartedEvent)
        def on_llm_started(source: Any, event: LLMCallStartedEvent) -> None:
            """Handle LLM call started event."""
            job_id = get_context("job_id")
            if not job_id:
                return

            try:
                # Extract prompt preview from messages
                prompt_preview = None
                if event.messages:
                    if isinstance(event.messages, str):
                        prompt_preview = _safe_truncate(event.messages, 500)
                    elif isinstance(event.messages, list) and len(event.messages) > 0:
                        # Get last user message
                        for msg in reversed(event.messages):
                            if isinstance(msg, dict) and msg.get("role") == "user":
                                content = msg.get("content", "")
                                if isinstance(content, str):
                                    prompt_preview = _safe_truncate(content, 500)
                                    break

                TrackingService().add_llm_event(
                    job_id,
                    LLMCallEvent(
                        agent_name=event.agent_role or "Unknown",
                        model_name=event.model or "unknown",
                        status="running",
                        prompt_preview=prompt_preview,
                        timestamp=datetime.now(),
                    ),
                )
            except Exception:
                logger.debug("Failed to record LLM started event", exc_info=True)

    # Register LLMCallCompletedEvent handler (always)
    @crewai_event_bus.on(LLMCallCompletedEvent)
    def on_llm_completed(source: Any, event: LLMCallCompletedEvent) -> None:
        """Handle LLM call completed event."""
        job_id = get_context("job_id")
        if not job_id:
            return

        try:
            # Extract token usage from response
            prompt_tokens = None
            completion_tokens = None
            total_tokens = None
            response_preview = None
            raw_model_name = event.model or "unknown"
            llm_provider, model_key = _resolve_llm_identity(
                model_name=raw_model_name, response=event.response
            )

            # Extract usage from response object
            response = event.response
            if response:
                # Handle litellm ModelResponse
                if hasattr(response, "usage") and response.usage:
                    usage = response.usage
                    prompt_tokens = getattr(usage, "prompt_tokens", None)
                    completion_tokens = getattr(usage, "completion_tokens", None)
                    total_tokens = getattr(usage, "total_tokens", None)

                # Extract response content preview
                if hasattr(response, "choices") and response.choices:
                    try:
                        first_choice = response.choices[0]
                        if hasattr(first_choice, "message"):
                            content = getattr(first_choice.message, "content", None)
                            if content:
                                response_preview = _safe_truncate(str(content), 500)
                    except (IndexError, AttributeError):
                        pass

            # Estimate cost
            estimated_cost_usd = None
            pricing_version = None
            pricing_updated = None
            try:
                from AICrews.llm.core.config_store import get_config_store
                store = get_config_store()
                price = store.get_price(llm_provider, model_key)
                if price:
                    input_price = float(price.get("input") or 0.0)
                    output_price = float(price.get("output") or 0.0)
                    estimated_cost_usd = (
                        (prompt_tokens or 0) / 1_000_000 * input_price +
                        (completion_tokens or 0) / 1_000_000 * output_price
                    )
                    pricing_version = getattr(store.pricing, "version", None)
                    pricing_updated = getattr(store.pricing, "updated", None)
            except Exception as e:
                logger.debug(f"Failed to estimate LLM cost: {e}")

            TrackingService().add_llm_event(
                job_id,
                LLMCallEvent(
                    agent_name=event.agent_role or "Unknown",
                    llm_provider=llm_provider,
                    model_name=model_key,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    status="success",
                    response_preview=response_preview,
                    estimated_cost_usd=estimated_cost_usd,
                    pricing_version=pricing_version,
                    pricing_updated=pricing_updated,
                    timestamp=datetime.now(),
                ),
            )
        except Exception:
            logger.debug("Failed to record LLM completed event", exc_info=True)

    # Register LLMCallFailedEvent handler (always)
    @crewai_event_bus.on(LLMCallFailedEvent)
    def on_llm_failed(source: Any, event: LLMCallFailedEvent) -> None:
        """Handle LLM call failed event."""
        job_id = get_context("job_id")
        if not job_id:
            return

        try:
            TrackingService().add_llm_event(
                job_id,
                LLMCallEvent(
                    agent_name=event.agent_role or "Unknown",
                    model_name="unknown",
                    status="failed",
                    error_message=_safe_truncate(str(event.error), 500) if event.error else None,
                    timestamp=datetime.now(),
                ),
            )
        except Exception:
            logger.debug("Failed to record LLM failed event", exc_info=True)

    # ========================================
    # Task Event Handlers
    # ========================================

    try:
        from crewai.events.types.task_events import (
            TaskStartedEvent,
            TaskCompletedEvent,
            TaskFailedEvent,
        )
        from AICrews.schemas.stats import AgentActivityEvent

        # Register TaskStartedEvent handler (full mode only)
        if level == "full":
            @crewai_event_bus.on(TaskStartedEvent)
            def on_task_started(source: Any, event: TaskStartedEvent) -> None:
                """Handle task started event."""
                job_id = get_context("job_id")
                if not job_id:
                    return

                try:
                    task_name = event.task_name or "Unknown Task"
                    agent_role = event.agent_role or "Reporter"

                    TrackingService().add_activity(
                        job_id,
                        AgentActivityEvent(
                            agent_name=agent_role,
                            activity_type="task_started",
                            message=f"Started task: {_safe_truncate(task_name, 100)}",
                            details={
                                "task_id": event.task_id,
                                "task_name": task_name,
                            },
                            timestamp=datetime.now(),
                        ),
                    )
                except Exception:
                    logger.debug("Failed to record task started event", exc_info=True)

        # Register TaskCompletedEvent handler (always)
        @crewai_event_bus.on(TaskCompletedEvent)
        def on_task_completed(source: Any, event: TaskCompletedEvent) -> None:
            """Handle task completed event."""
            job_id = get_context("job_id")
            if not job_id:
                return

            try:
                task_name = event.task_name or "Unknown Task"
                agent_role = event.agent_role or "Reporter"

                # Extract output preview
                output_preview = None
                if event.output:
                    try:
                        raw_output = getattr(event.output, "raw", None)
                        if raw_output:
                            output_preview = _safe_truncate(str(raw_output), 200)
                    except Exception as e:
                        logger.debug(f"Failed to extract task output preview: {e}")

                TrackingService().add_activity(
                    job_id,
                    AgentActivityEvent(
                        agent_name=agent_role,
                        activity_type="task_completed",
                        message=f"Completed task: {_safe_truncate(task_name, 100)}",
                        details={
                            "task_id": event.task_id,
                            "task_name": task_name,
                            "output_preview": output_preview,
                        },
                        timestamp=datetime.now(),
                    ),
                )
            except Exception:
                logger.debug("Failed to record task completed event", exc_info=True)

        # Register TaskFailedEvent handler (always)
        @crewai_event_bus.on(TaskFailedEvent)
        def on_task_failed(source: Any, event: TaskFailedEvent) -> None:
            """Handle task failed event."""
            job_id = get_context("job_id")
            if not job_id:
                return

            try:
                task_name = event.task_name or "Unknown Task"
                agent_role = event.agent_role or "Reporter"

                TrackingService().add_activity(
                    job_id,
                    AgentActivityEvent(
                        agent_name=agent_role,
                        activity_type="task_failed",
                        message=f"Failed task: {_safe_truncate(task_name, 100)}",
                        details={
                            "task_id": event.task_id,
                            "task_name": task_name,
                            "error": _safe_truncate(str(event.error), 500) if event.error else None,
                        },
                        timestamp=datetime.now(),
                    ),
                )
            except Exception:
                logger.debug("Failed to record task failed event", exc_info=True)

    except ImportError:
        logger.debug("Task events not available in this CrewAI version")

    # ========================================
    # Agent Delegation (A2A) Event Handlers
    # ========================================

    try:
        from crewai.events.types.a2a_events import (
            A2ADelegationStartedEvent,
            A2ADelegationCompletedEvent,
        )
        from AICrews.schemas.stats import AgentActivityEvent

        # Register A2ADelegationStartedEvent handler (full mode only)
        if level == "full":
            @crewai_event_bus.on(A2ADelegationStartedEvent)
            def on_delegation_started(source: Any, event: A2ADelegationStartedEvent) -> None:
                """Handle agent delegation started event."""
                job_id = get_context("job_id")
                if not job_id:
                    return

                try:
                    from_agent = event.agent_role or "Unknown Agent"
                    task_desc = event.task_description or "Unknown Task"

                    TrackingService().add_activity(
                        job_id,
                        AgentActivityEvent(
                            agent_name=from_agent,
                            activity_type="delegation_started",
                            message=f"Delegating to: {event.endpoint}",
                            details={
                                "endpoint": event.endpoint,
                                "task_description": _safe_truncate(task_desc, 200),
                                "is_multiturn": event.is_multiturn,
                                "turn_number": event.turn_number,
                            },
                            timestamp=datetime.now(),
                        ),
                    )
                except Exception:
                    logger.debug("Failed to record delegation started event", exc_info=True)

        # Register A2ADelegationCompletedEvent handler (always)
        @crewai_event_bus.on(A2ADelegationCompletedEvent)
        def on_delegation_completed(source: Any, event: A2ADelegationCompletedEvent) -> None:
            """Handle agent delegation completed event."""
            job_id = get_context("job_id")
            if not job_id:
                return

            try:
                from_agent = event.agent_role or "Unknown Agent"
                status = event.status or "unknown"

                details = {
                    "status": status,
                    "is_multiturn": event.is_multiturn,
                }
                if event.result:
                    details["result_preview"] = _safe_truncate(str(event.result), 200)
                if event.error:
                    details["error"] = _safe_truncate(str(event.error), 500)

                TrackingService().add_activity(
                    job_id,
                    AgentActivityEvent(
                        agent_name=from_agent,
                        activity_type="delegation_completed",
                        message=f"Delegation {status}",
                        details=details,
                        timestamp=datetime.now(),
                    ),
                )
            except Exception:
                logger.debug("Failed to record delegation completed event", exc_info=True)

    except ImportError:
        logger.debug("A2A delegation events not available in this CrewAI version")

    _crewai_registered = True
    logger.info(f"CrewAI event listeners registered (level={level})")
    return True


def register_litellm_callback(level: str = "minimal") -> bool:
    """Register litellm callback handler for LLM token tracking.

    This function adds NativeTrackingHandler to litellm's callbacks list.
    Should be called once during application startup (in lifespan.py).

    Args:
        level: Tracking level ("full" or "minimal")
            - "full": log_pre_call + log_success_event + log_failure_event
            - "minimal": log_success_event + log_failure_event only

    Returns:
        True if registration successful, False otherwise
    """
    global _litellm_registered

    if _litellm_registered:
        logger.debug("litellm callback already registered, skipping")
        return True

    try:
        import litellm
        from AICrews.services.tracking_service import NativeTrackingHandler

        handler = NativeTrackingHandler(level=level)
        litellm.callbacks.append(handler)

        _litellm_registered = True
        logger.info(f"litellm callback registered (level={level})")
        return True

    except ImportError as e:
        logger.warning(f"Failed to register litellm callback: {e}")
        return False
    except Exception as e:
        logger.error(f"Error registering litellm callback: {e}")
        return False


def _safe_truncate(text: str, max_chars: int) -> str:
    """Safely truncate text to max_chars."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def _safe_json_serialize(obj: Any, max_chars: int = 10000) -> str | None:
    """Safely serialize object to JSON string with truncation.
    
    Unlike str(), this produces valid JSON that can be parsed by frontend.
    Falls back to str() representation if JSON serialization fails.
    """
    if obj is None:
        return None
    
    try:
        # First try direct JSON serialization
        json_str = json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        # Fallback: try to convert to dict if possible
        try:
            if hasattr(obj, 'model_dump'):  # Pydantic model
                json_str = json.dumps(obj.model_dump(), ensure_ascii=False, default=str)
            elif hasattr(obj, '__dict__'):
                json_str = json.dumps(obj.__dict__, ensure_ascii=False, default=str)
            else:
                # Last resort: use str() but wrap in JSON string
                json_str = json.dumps(str(obj))
        except Exception as e:
            logger.debug(f"JSON serialization fallback failed: {e}")
            # Final fallback
            json_str = json.dumps(str(obj))
    
    return _safe_truncate(json_str, max_chars)


def is_crewai_registered() -> bool:
    """Check if CrewAI event listeners are registered."""
    return _crewai_registered


def is_litellm_registered() -> bool:
    """Check if litellm callback is registered."""
    return _litellm_registered
