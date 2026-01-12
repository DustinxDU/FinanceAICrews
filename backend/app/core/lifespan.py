"""FastAPI lifespan orchestration for backend startup/shutdown."""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Awaitable, Callable, List

from fastapi import FastAPI

from AICrews.database.db_manager import get_db_session
from AICrews.infrastructure.cache.redis_manager import close_redis, init_redis
from AICrews.infrastructure.jobs.job_manager import get_job_manager
from AICrews.llm.unified_manager import get_unified_llm_manager
from AICrews.services.daily_archiver_service import (
    start_daily_archiver_service,
    stop_daily_archiver_service,
)
from AICrews.services.cockpit_macro_sync_service import (
    start_cockpit_macro_sync_service,
    stop_cockpit_macro_sync_service,
)
from AICrews.services.unified_sync_service import (
    start_unified_sync_service,
    stop_unified_sync_service,
)
from AICrews.services.tracking_service import TrackingService
from backend.app.ws.run_log_manager import manager as ws_manager

logger = logging.getLogger(__name__)

# ============================================================================
# Lifecycle Management: Tasks and Cleanup Registry
# ============================================================================

# Store background tasks for proper cancellation on shutdown
_startup_tasks: List[asyncio.Task] = []

# Cleanup registry for singleton services (MCP clients, caches, etc.)
_cleanup_registry: List[Callable[[], Awaitable[None]]] = []

# Shutdown flag for graceful loop termination
_shutdown_event: asyncio.Event | None = None


def register_cleanup(cleanup_fn: Callable[[], Awaitable[None]]) -> None:
    """Register an async cleanup function to be called on shutdown.

    Usage:
        from backend.app.core.lifespan import register_cleanup

        async def my_service_cleanup():
            await my_service.close()

        register_cleanup(my_service_cleanup)
    """
    _cleanup_registry.append(cleanup_fn)


def get_shutdown_event() -> asyncio.Event:
    """Get the shutdown event for graceful loop termination."""
    global _shutdown_event
    if _shutdown_event is None:
        _shutdown_event = asyncio.Event()
    return _shutdown_event


async def _daily_model_sync_loop() -> None:
    """每日定时同步模型列表（后台任务）

    This loop checks the shutdown event to allow graceful termination.
    """
    shutdown_event = get_shutdown_event()

    while not shutdown_event.is_set():
        try:
            logger.info("Starting daily LLM model synchronization...")
            async with get_db_session() as db:
                manager = get_unified_llm_manager()
                results = await manager.sync_all_models(db)
                logger.info("Daily sync completed: %s", results)
        except asyncio.CancelledError:
            logger.info("Daily model sync loop cancelled")
            break
        except Exception as exc:
            logger.error("Error during daily model sync: %s", exc)

        # Wait with shutdown check (check every 60s instead of blocking 24h)
        try:
            await asyncio.wait_for(
                shutdown_event.wait(),
                timeout=24 * 3600,  # 24 hours
            )
            # If we get here, shutdown was signaled
            break
        except asyncio.TimeoutError:
            # Normal timeout, continue loop
            pass
        except asyncio.CancelledError:
            logger.info("Daily model sync loop cancelled during sleep")
            break

    logger.info("Daily model sync loop exiting")


async def _memory_metrics_update_loop() -> None:
    """Periodically update memory management Prometheus gauges.

    Updates:
    - JobManager jobs in memory count
    - TrackingService runs in memory count
    - Cache sizes (smart_rss, news_service, model_service)
    - WebSocket active runs/connections

    Update interval: 30 seconds (configurable via FAIC_METRICS_UPDATE_INTERVAL_SECONDS)
    """
    from AICrews.infrastructure.metrics.prometheus_metrics import get_memory_metrics

    shutdown_event = get_shutdown_event()
    update_interval = int(os.getenv("FAIC_METRICS_UPDATE_INTERVAL_SECONDS", "30"))

    logger.info("Starting memory metrics update loop (interval=%ds)", update_interval)

    while not shutdown_event.is_set():
        try:
            metrics = get_memory_metrics()

            # Update JobManager stats
            try:
                from AICrews.infrastructure.jobs.job_manager import JobStatus
                job_manager = get_job_manager()
                total_jobs = len(job_manager._jobs)
                running_jobs = sum(
                    1 for job in job_manager._jobs.values()
                    if job.status == JobStatus.RUNNING
                )
                metrics.update_job_manager_stats(total_jobs, running_jobs)
            except Exception as e:
                logger.debug("Failed to update JobManager metrics: %s", e)

            # Update TrackingService stats
            try:
                from AICrews.services.tracking_service import TrackingService
                tracker = TrackingService()
                total_runs = len(tracker._stats)
                running_runs = sum(
                    1 for stats in tracker._stats.values()
                    if stats.status == "running"
                )
                metrics.update_tracking_service_stats(total_runs, running_runs)
            except Exception as e:
                logger.debug("Failed to update TrackingService metrics: %s", e)

            # Update cache sizes
            try:
                from AICrews.tools.smart_rss_tool import SmartRSSTool
                rss_tool = SmartRSSTool()
                metrics.update_cache_size("smart_rss", len(rss_tool._cache))
            except Exception as e:
                logger.debug("Failed to update SmartRSSTool cache metrics: %s", e)

            try:
                from AICrews.services.news_service import get_news_service
                news_service = get_news_service()
                metrics.update_cache_size("news_service", len(news_service._cache))
            except Exception as e:
                logger.debug("Failed to update NewsService cache metrics: %s", e)

            try:
                from AICrews.llm.services.model_service import get_model_service
                model_service = get_model_service()
                metrics.update_cache_size("model_service", len(model_service._cache))
            except Exception as e:
                logger.debug("Failed to update ModelService cache metrics: %s", e)

            # Update WebSocket stats (ConnectionManager singleton)
            try:
                from backend.app.ws.run_log_manager import manager as ws_manager
                active_runs = len(ws_manager.history)
                active_connections = sum(
                    len(conns) for conns in ws_manager.active_connections.values()
                )
                metrics.update_websocket_stats(active_runs, active_connections)
            except Exception as e:
                logger.debug("Failed to update WebSocket metrics: %s", e)

        except asyncio.CancelledError:
            logger.info("Memory metrics update loop cancelled")
            break
        except Exception as exc:
            logger.warning("Error during memory metrics update: %s", exc)

        # Wait with shutdown check
        try:
            await asyncio.wait_for(
                shutdown_event.wait(),
                timeout=update_interval,
            )
            # If we get here, shutdown was signaled
            break
        except asyncio.TimeoutError:
            # Normal timeout, continue loop
            pass
        except asyncio.CancelledError:
            logger.info("Memory metrics update loop cancelled during sleep")
            break

    logger.info("Memory metrics update loop exiting")


async def _virtual_key_reconcile_loop() -> None:
    """Periodically reconcile pending LLM virtual key provisioning.

    This background loop ensures that any virtual keys stuck in PROVISIONING
    or FAILED state are eventually completed. It serves as a backup mechanism
    for the synchronous provisioning that happens during user registration.

    Update interval: 60 seconds (configurable via FAIC_PROVISIONER_INTERVAL_SECONDS)
    """
    shutdown_event = get_shutdown_event()
    interval_seconds = int(os.getenv("FAIC_PROVISIONER_INTERVAL_SECONDS", "60"))

    # Check if LiteLLM Proxy is configured
    master_key = os.getenv("LITELLM_PROXY_MASTER_KEY")
    if not master_key:
        logger.info(
            "LITELLM_PROXY_MASTER_KEY not set, virtual key reconcile loop disabled"
        )
        return

    logger.info(
        "Starting virtual key reconcile loop (interval=%ds)", interval_seconds
    )

    while not shutdown_event.is_set():
        try:
            from AICrews.services.provisioner_service import ProvisionerService
            from AICrews.services.litellm_admin_client import LiteLLMAdminClient

            async with get_db_session() as db:
                admin_client = LiteLLMAdminClient()
                provisioner = ProvisionerService(admin_client=admin_client)

                try:
                    stats = await provisioner.reconcile(db=db, limit=50)

                    if stats["processed"] > 0:
                        logger.info(
                            "Virtual key reconcile completed: processed=%d, "
                            "success=%d, failed=%d, skipped=%d",
                            stats["processed"],
                            stats["success"],
                            stats["failed"],
                            stats["skipped"],
                        )
                finally:
                    await admin_client.close()

        except asyncio.CancelledError:
            logger.info("Virtual key reconcile loop cancelled")
            break
        except Exception as exc:
            logger.warning("Error during virtual key reconcile: %s", exc)

        # Wait with shutdown check
        try:
            await asyncio.wait_for(
                shutdown_event.wait(),
                timeout=interval_seconds,
            )
            # If we get here, shutdown was signaled
            break
        except asyncio.TimeoutError:
            # Normal timeout, continue loop
            pass
        except asyncio.CancelledError:
            logger.info("Virtual key reconcile loop cancelled during sleep")
            break

    logger.info("Virtual key reconcile loop exiting")


async def _cancel_startup_tasks() -> None:
    """Cancel all tracked startup tasks gracefully."""
    global _startup_tasks

    if not _startup_tasks:
        return

    logger.info("Cancelling %d startup tasks...", len(_startup_tasks))

    # Signal shutdown to loops that check the event
    shutdown_event = get_shutdown_event()
    shutdown_event.set()

    # Cancel all tasks
    for task in _startup_tasks:
        if not task.done():
            task.cancel()

    # Wait for all tasks to complete (with timeout)
    try:
        await asyncio.wait_for(
            asyncio.gather(*_startup_tasks, return_exceptions=True),
            timeout=10.0,
        )
    except asyncio.TimeoutError:
        logger.warning("Some tasks did not complete within timeout")

    _startup_tasks.clear()
    logger.info("All startup tasks cancelled")


async def _run_cleanup_registry() -> None:
    """Run all registered cleanup functions."""
    global _cleanup_registry

    if not _cleanup_registry:
        return

    logger.info("Running %d cleanup functions...", len(_cleanup_registry))

    for cleanup_fn in _cleanup_registry:
        try:
            await cleanup_fn()
        except Exception as exc:
            logger.warning("Cleanup function failed: %s", exc, exc_info=True)

    _cleanup_registry.clear()
    logger.info("Cleanup registry completed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理

    Key improvements:
    - Background tasks are tracked and cancelled on shutdown
    - Cleanup registry allows singletons to register their cleanup
    - Shutdown event allows loops to exit gracefully
    """
    global _startup_tasks, _shutdown_event

    logger.info("Starting FinanceAI Platform...")

    # In unit tests we avoid starting external dependencies (Redis/MCP) and
    # long-running background loops to keep TestClient usage fast and reliable.
    # `PYTEST_CURRENT_TEST` is only set while executing an individual test.
    # During collection/import time (e.g. module-level `TestClient(app)`),
    # it may be unset, so also detect pytest via `sys.modules`.
    if (
        os.getenv("PYTEST_CURRENT_TEST")
        or os.getenv("FAIC_TESTING", "").lower() == "true"
        or "pytest" in sys.modules
    ):
        logger.info("Test environment detected; skipping backend lifespan startup")
        yield
        return

    # Reset shutdown event for fresh start
    _shutdown_event = asyncio.Event()

    # ===== Patch MCP client for schema normalization =====
    # This monkey patches CrewAI's MCPClient.list_tools() to normalize
    # tool schemas before they reach LLMs, fixing anyOf enum issues
    from AICrews.infrastructure.mcp.schema_normalizer import patch_mcp_client
    try:
        patch_mcp_client()
        logger.info("MCP schema normalizer successfully patched")
    except Exception as exc:
        logger.error("Failed to patch MCP schema normalizer: %s", exc, exc_info=True)
    # =========================================================

    job_manager = get_job_manager(max_workers=3)

    # Create and TRACK the daily model sync task
    task = asyncio.create_task(_daily_model_sync_loop(), name="daily_model_sync")
    _startup_tasks.append(task)
    logger.info("Daily model sync task scheduled")

    # Create and TRACK the memory metrics update task
    metrics_task = asyncio.create_task(_memory_metrics_update_loop(), name="memory_metrics_update")
    _startup_tasks.append(metrics_task)
    logger.info("Memory metrics update task scheduled")

    # Create and TRACK the virtual key reconcile task
    reconcile_task = asyncio.create_task(
        _virtual_key_reconcile_loop(), name="virtual_key_reconcile"
    )
    _startup_tasks.append(reconcile_task)
    logger.info("Virtual key reconcile task scheduled")

    try:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "0"))
        await init_redis(host=redis_host, port=redis_port, db=redis_db)
        logger.info("Redis cache initialized: %s:%s", redis_host, redis_port)

        # Initialize TrackingService with WebSocket manager for real-time event broadcast
        tracker = TrackingService()
        tracker.set_dependencies(storage=None, ws_manager=ws_manager)
        logger.info("TrackingService initialized with WebSocket manager")

        # Register CrewAI EventBus listeners and litellm callbacks for event tracking
        try:
            from AICrews.config.settings import get_settings
            from AICrews.observability.crewai_event_listener import (
                register_crewai_event_listeners,
                register_litellm_callback,
            )

            settings = get_settings()
            event_level = settings.tracking.event_tracking_level

            register_crewai_event_listeners(level=event_level)
            register_litellm_callback(level=event_level)
            logger.info(f"Event tracking listeners registered (level={event_level})")
        except Exception as exc:
            logger.warning(f"Failed to register event tracking listeners: {exc}")

        # Milestone C2: Recover persisted jobs on startup
        try:
            job_manager = get_job_manager()
            # Create and TRACK the job recovery task
            recovery_task = asyncio.create_task(
                job_manager.recover_jobs(), name="job_recovery"
            )
            _startup_tasks.append(recovery_task)
            logger.info("Job system recovery process started")
        except Exception as job_err:
            logger.error("Failed to initialize job recovery: %s", job_err)

    except Exception as exc:
        logger.warning("Redis init failed, falling back to in-memory cache: %s", exc)

    try:
        await start_unified_sync_service()
        logger.info("Unified sync service started")
    except Exception as exc:
        logger.error("Unified sync service failed to start: %s", exc, exc_info=True)

    try:
        await start_cockpit_macro_sync_service()
        logger.info("Cockpit macro sync service started")
    except Exception as exc:
        logger.error("Cockpit macro sync service failed to start: %s", exc, exc_info=True)

    try:
        await start_daily_archiver_service()
        logger.info("Daily archiver service started")
    except Exception as exc:
        logger.error("Daily archiver service failed to start: %s", exc, exc_info=True)

    logger.info("Backend startup complete")

    yield

    # ========================================================================
    # SHUTDOWN SEQUENCE
    # ========================================================================
    logger.info("Shutting down FinanceAI Platform...")

    # 1. Signal shutdown to all loops and cancel tracked tasks
    await _cancel_startup_tasks()

    # 2. Stop managed services
    try:
        await stop_unified_sync_service()
    except Exception as exc:
        logger.warning("Failed to stop unified sync service: %s", exc, exc_info=True)

    try:
        await stop_cockpit_macro_sync_service()
    except Exception as exc:
        logger.warning("Failed to stop cockpit macro sync service: %s", exc, exc_info=True)

    try:
        await stop_daily_archiver_service()
    except Exception as exc:
        logger.warning("Failed to stop daily archiver service: %s", exc, exc_info=True)

    # 3. Run cleanup registry (MCP clients, caches, etc.)
    await _run_cleanup_registry()

    # 4. Close Redis
    try:
        await close_redis()
    except Exception as exc:
        logger.warning("Failed to close redis: %s", exc, exc_info=True)

    # 5. Shutdown job manager
    job_manager.shutdown(wait=True)

    logger.info("Backend shutdown complete")
