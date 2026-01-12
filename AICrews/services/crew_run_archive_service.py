from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime

from AICrews.observability.logging import get_logger
from pathlib import Path
from typing import Any, Dict, List, Optional

from AICrews.application.crew.versioning import CrewVersionManager
from AICrews.database.db_manager import DBManager
from AICrews.schemas.stats import RunEventType
from AICrews.services.insight_ingestor import get_insight_ingestor
from AICrews.services.tracking_service import TrackingService
from AICrews.utils.citations import CitationParser
from AICrews.utils.redaction import redact_sensitive
from AICrews.utils.redaction import truncate_text

logger = get_logger(__name__)

# Artifact storage base directory (configurable via env)
ARTIFACT_STORAGE_BASE = os.getenv(
    "FAIC_ARTIFACT_STORAGE_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "artifacts"),
)


def _build_run_metrics(
    *,
    job_id: str,
    ticker: str,
    crew_name: str,
    events: List[Any],
) -> Dict[str, Any]:
    """Build a preview-safe per-run metrics summary for offline/continuous analysis."""
    llm_total_calls = 0
    llm_total_tokens = 0
    llm_total_duration_ms = 0
    llm_estimated_cost_usd_total = 0.0
    llm_by_model: Dict[str, Dict[str, Any]] = {}

    tool_total_calls = 0
    tool_failures = 0
    tool_total_duration_ms = 0
    tool_by_name: Dict[str, Dict[str, Any]] = {}
    slowest_tool_calls: List[Dict[str, Any]] = []

    for event in events:
        if event.event_type == RunEventType.LLM_CALL:
            status = str(event.payload.get("status") or "").lower()
            # Avoid double counting started/pending events in "full" tracking mode.
            if status in ("running", "pending"):
                continue

            llm_total_calls += 1

            provider = str(event.payload.get("llm_provider") or "unknown")
            model = str(event.payload.get("model_name") or "unknown")
            key = f"{provider}/{model}"

            tokens = int(event.payload.get("total_tokens") or 0)
            duration_ms = int(event.payload.get("duration_ms") or 0)
            try:
                cost = float(event.payload.get("estimated_cost_usd") or 0.0)
            except (ValueError, TypeError) as e:
                logger.debug(f"Failed to parse estimated_cost_usd: {e}")
                cost = 0.0

            llm_total_tokens += tokens
            llm_total_duration_ms += duration_ms
            llm_estimated_cost_usd_total += cost

            bucket = llm_by_model.setdefault(
                key,
                {
                    "calls": 0,
                    "total_tokens": 0,
                    "total_duration_ms": 0,
                    "estimated_cost_usd_total": 0.0,
                },
            )
            bucket["calls"] += 1
            bucket["total_tokens"] += tokens
            bucket["total_duration_ms"] += duration_ms
            bucket["estimated_cost_usd_total"] += cost

        if event.event_type == RunEventType.TOOL_RESULT:
            tool_name = str(event.payload.get("tool_name") or "tool")
            status = str(event.payload.get("status") or "unknown")
            duration_ms = int(event.payload.get("duration_ms") or 0)

            tool_total_calls += 1
            if status == "failed":
                tool_failures += 1
            tool_total_duration_ms += duration_ms

            bucket = tool_by_name.setdefault(
                tool_name,
                {"calls": 0, "failures": 0, "total_duration_ms": 0},
            )
            bucket["calls"] += 1
            bucket["total_duration_ms"] += duration_ms
            if status == "failed":
                bucket["failures"] += 1

            # Only meaningful for terminal tool results
            slowest_tool_calls.append(
                {
                    "tool_name": tool_name,
                    "agent_name": event.agent_name,
                    "status": status,
                    "duration_ms": duration_ms,
                }
            )

    slowest_tool_calls.sort(key=lambda x: x.get("duration_ms") or 0, reverse=True)

    return {
        "run_id": job_id,
        "ticker": ticker,
        "crew_name": crew_name,
        "llm": {
            "total_calls": llm_total_calls,
            "total_tokens": llm_total_tokens,
            "total_duration_ms": llm_total_duration_ms,
            "estimated_cost_usd_total": llm_estimated_cost_usd_total,
            "by_model": llm_by_model,
        },
        "tools": {
            "total_calls": tool_total_calls,
            "failures": tool_failures,
            "total_duration_ms": tool_total_duration_ms,
            "by_tool": tool_by_name,
            "slowest_calls_top10": slowest_tool_calls[:10],
        },
    }


def _persist_artifact_to_disk(
    job_id: str,
    file_name: str,
    content: str,
    content_type: str,
) -> Dict[str, Any]:
    """Persist artifact content to disk and return storage-based artifact dict.

    Args:
        job_id: Job ID for directory organization
        file_name: Name of the file to create
        content: Content to write
        content_type: MIME type of the content

    Returns:
        Storage-based artifact dict with file_name, file_type, storage_path, etc.
    """
    # Ensure base directory exists
    base_path = Path(ARTIFACT_STORAGE_BASE).resolve()
    job_dir = base_path / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Write content to file
    file_path = job_dir / file_name
    file_path.write_text(content, encoding="utf-8")

    # Determine file_type from content_type or extension
    if "json" in content_type:
        file_type = "json"
    elif "text" in content_type:
        file_type = "txt"
    else:
        # Fallback to extension
        ext = file_name.rsplit(".", 1)[-1] if "." in file_name else "txt"
        file_type = ext

    return {
        "file_name": file_name,
        "file_type": file_type,
        "storage_path": str(file_path),
        "file_size": len(content.encode("utf-8")),
        "mime_type": content_type,
    }


def _serialize_tasks_output(
    tasks_output: List[Any],
    job_id: str,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Serialize tasks_output to artifact-friendly format.

    Args:
        tasks_output: List of CrewAI TaskOutput objects
        job_id: Job ID for artifact paths

    Returns:
        Tuple of (tasks_output_data, tasks_with_citations_data)
    """
    citation_parser = CitationParser()
    tasks_data = []
    tasks_with_citations_data = []

    for i, task_output in enumerate(tasks_output):
        raw = getattr(task_output, "raw", "") or ""
        json_dict = getattr(task_output, "json_dict", None)
        pydantic_obj = getattr(task_output, "pydantic", None)

        # Basic task data
        task_entry = {
            "task_index": i,
            "raw_preview": truncate_text(raw, limit=2000),
            "json_dict": json_dict,
            "pydantic_dump": None,
        }

        if pydantic_obj is not None:
            try:
                task_entry["pydantic_dump"] = pydantic_obj.model_dump()
            except Exception as e:
                logger.debug(f"Failed to dump pydantic object for task {i}: {e}")

        tasks_data.append(task_entry)

        # Task with citations
        citations = citation_parser.extract(raw)
        citation_data = [
            {"source_name": c.source_name, "is_valid": c.is_valid}
            for c in citations
        ]

        task_with_citations = {
            **task_entry,
            "citations": citation_data,
            "citation_count": len(citations),
        }
        tasks_with_citations_data.append(task_with_citations)

    return tasks_data, tasks_with_citations_data


def archive_crew_run_result(
    *,
    job_id: str,
    crew_id: int,
    crew_name: str,
    user_id: int,
    variables: Dict[str, Any],
    result: Any,
    result_str: str,
) -> None:
    """Archive a completed crew run to Library with version snapshot and traces.

    This function is designed to be called from thread execution context.
    It handles its own DB session lifecycle and runs async ingestor methods safely.
    """

    tracker = TrackingService()
    stats = tracker.get_stats(job_id)

    # Extract token usage from CrewOutput if available
    token_usage: Dict[str, Any] = {}
    if hasattr(result, "token_usage"):
        usage = result.token_usage
        token_usage = {
            "total_tokens": getattr(usage, "total_tokens", 0),
            "prompt_tokens": getattr(usage, "prompt_tokens", 0),
            "completion_tokens": getattr(usage, "completion_tokens", 0),
            "successful_requests": getattr(usage, "successful_requests", 0),
        }

    db_manager = DBManager()
    with db_manager.get_session() as session:
        # Auto-save a version snapshot for this run
        version_mgr = CrewVersionManager()
        version_id: Optional[int]
        try:
            version = version_mgr.save_version(
                session,
                crew_id,
                description=f"Auto-snapshot for job {job_id}",
            )
            version_id = version.id
            logger.info(
                f"[Job {job_id}] Auto-saved crew version {version.version_number}"
            )
        except Exception as ver_err:
            logger.warning(f"[Job {job_id}] Failed to save auto-version: {ver_err}")
            version_id = None

        ingestor = get_insight_ingestor(session)

        # Use RunEvents from tracker directly for high-fidelity traces
        events = tracker.get_run_events(job_id)
        traces = []
        for event in events:
            if event.event_type == RunEventType.LLM_CALL:
                llm_input = {
                    "prompt_preview": event.payload.get("prompt_preview"),
                    "serialized_info": event.payload.get("serialized_info"),
                }
                llm_output = {
                    "response_preview": event.payload.get("response_preview"),
                    "estimated_cost_usd": event.payload.get("estimated_cost_usd"),
                    "pricing_version": event.payload.get("pricing_version"),
                    "pricing_updated": event.payload.get("pricing_updated"),
                    "duration_ms": event.payload.get("duration_ms"),
                }
                traces.append(
                    {
                        "agent_name": event.agent_name,
                        "action_type": event.event_type,
                        "content": event.payload.get("message") or "",
                        "input_data": redact_sensitive(llm_input),
                        "output_data": redact_sensitive(llm_output),
                        "tokens_used": event.payload.get("total_tokens"),
                        "duration_ms": event.payload.get("duration_ms"),
                        "model_name": event.payload.get("model_name"),
                        "payload": event.payload,
                    }
                )
                continue

            traces.append(
                {
                    "agent_name": event.agent_name,
                    "action_type": event.event_type,
                    "content": event.payload.get("message")
                    or event.payload.get("thought")
                    or "",
                    "input_data": event.payload.get("input_data")
                    or event.payload.get("args"),
                    "output_data": event.payload.get("output_data")
                    or event.payload.get("result"),
                    "tokens_used": event.payload.get("total_tokens"),
                    "duration_ms": event.payload.get("duration_ms"),
                    "model_name": event.payload.get("model_name"),
                    "payload": event.payload,
                }
            )

        estimated_cost_usd_total = 0.0
        for event in events:
            if event.event_type == RunEventType.LLM_CALL:
                try:
                    estimated_cost_usd_total += float(
                        event.payload.get("estimated_cost_usd") or 0.0
                    )
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to parse estimated_cost_usd in event: {e}")

        run_summary = {
            **token_usage,
            "total_duration_ms": stats.total_duration_ms if stats else None,
            "tool_calls_count": stats.tool_call_count if stats else 0,
            "estimated_cost_usd_total": estimated_cost_usd_total,
            "version_id": version_id,
            "crew_id": crew_id,
            "compiled_at": datetime.now().isoformat(),
        }

        # Build artifacts from tasks_output if available
        # Artifacts are persisted to disk and stored in storage-based format
        artifacts = []
        try:
            run_metrics = _build_run_metrics(
                job_id=job_id,
                ticker=variables.get("ticker", "Unknown"),
                crew_name=crew_name,
                events=events,
            )
            artifacts.append(
                _persist_artifact_to_disk(
                    job_id=job_id,
                    file_name="run_metrics.json",
                    content=json.dumps(run_metrics, ensure_ascii=False, indent=2, default=str),
                    content_type="application/json",
                )
            )
        except Exception as exc:
            logger.warning("[Job %s] Failed to build run_metrics artifact: %s", job_id, exc)

        if hasattr(result, "tasks_output") and result.tasks_output:
            try:
                tasks_data, tasks_with_citations = _serialize_tasks_output(
                    result.tasks_output, job_id
                )

                # Persist tasks_output.json to disk
                tasks_content = json.dumps(tasks_data, ensure_ascii=False, indent=2)
                artifacts.append(
                    _persist_artifact_to_disk(
                        job_id=job_id,
                        file_name="tasks_output.json",
                        content=tasks_content,
                        content_type="application/json",
                    )
                )

                # Persist tasks_output_with_citations.json to disk
                citations_content = json.dumps(tasks_with_citations, ensure_ascii=False, indent=2)
                artifacts.append(
                    _persist_artifact_to_disk(
                        job_id=job_id,
                        file_name="tasks_output_with_citations.json",
                        content=citations_content,
                        content_type="application/json",
                    )
                )

                logger.info(
                    f"[Job {job_id}] Persisted {len(result.tasks_output)} task outputs to artifacts"
                )
            except Exception as e:
                logger.warning(f"[Job {job_id}] Failed to serialize tasks_output: {e}")

        title = f"Analysis: {variables.get('ticker', 'Unknown')}"
        summary = result_str[:500] + "..." if len(result_str) > 500 else result_str

        asyncio.run(
            ingestor.save_crew_result_with_artifacts(
                user_id=user_id,
                ticker=variables.get("ticker", "Unknown"),
                crew_name=crew_name,
                run_id=job_id,
                title=title,
                summary=summary,
                content=result_str,
                artifacts=artifacts,
                traces=traces,
                key_metrics=run_summary,
                analysis_date=datetime.now(),
            )
        )

        logger.info(
            f"[Job {job_id}] Full result archived to library with version tracking"
        )
