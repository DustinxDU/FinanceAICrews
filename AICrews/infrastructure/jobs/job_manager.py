"""
Async Job Manager - 异步任务管理器

处理 CrewAI 长耗时任务的异步执行
MVP阶段使用 ThreadPoolExecutor，Production可升级为 Celery + Redis

Memory Management:
- LRU eviction (max jobs in memory, configurable via FAIC_JOB_MAX_IN_MEMORY)
- Time-based retention (configurable via FAIC_JOB_RETENTION_HOURS)
- Result dropping: large results nulled from memory after Redis persistence
- Per-job chat message limits to prevent unbounded chat history growth
"""

import os
import uuid
import asyncio
import traceback
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

from typing import TYPE_CHECKING

from AICrews.observability.logging import get_logger

if TYPE_CHECKING:
    # 仅用于类型检查，避免运行时循环依赖
    from AICrews.schemas.stats import ToolUsageEvent, AgentActivityEvent

logger = get_logger(__name__)


class JobStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobResult:
    """任务结果"""
    job_id: str
    status: JobStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = 0
    progress_message: str = ""
    
    # 任务元数据
    ticker: Optional[str] = None
    crew_name: Optional[str] = None
    
    # 用户隔离
    user_id: Optional[int] = None
    
    # 聊天历史（用于后续 Copilot 功能）
    chat_history: List[Dict[str, str]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "ticker": self.ticker,
            "crew_name": self.crew_name,
            "user_id": self.user_id,
            "chat_history": self.chat_history,
        }


class JobStore:
    """任务存储抽象类"""
    def save(self, job: JobResult): raise NotImplementedError()
    def get(self, job_id: str) -> Optional[JobResult]: raise NotImplementedError()
    def list(self, user_id: Optional[int] = None, limit: int = 50) -> List[JobResult]: raise NotImplementedError()
    def delete(self, job_id: str): raise NotImplementedError()

class RedisJobStore(JobStore):
    """基于 Redis 的任务存储"""
    def __init__(self):
        from AICrews.infrastructure.cache.redis_manager import get_redis_manager
        self.redis = get_redis_manager()
        self.prefix = "job:"

    def _get_key(self, job_id: str) -> str:
        return f"{self.prefix}{job_id}"

    async def save(self, job: JobResult):
        await self.redis.set(self._get_key(job.job_id), job.to_dict(), ttl=86400) # 24h

    def save_sync(self, job: JobResult):
        """同步保存，用于非 asyncio 线程"""
        self.redis.set_sync(self._get_key(job.job_id), job.to_dict(), ttl=86400)

    def get_sync(self, job_id: str) -> Optional[JobResult]:
        """同步获取，用于非 asyncio 线程 - 避免 'Future attached to a different loop' 错误"""
        data = self.redis.get_json_sync(self._get_key(job_id))
        if data:
            # 从 dict 恢复，注意 datetime 转换
            if data.get('created_at'): data['created_at'] = datetime.fromisoformat(data['created_at'])
            if data.get('started_at'): data['started_at'] = datetime.fromisoformat(data['started_at'])
            if data.get('completed_at'): data['completed_at'] = datetime.fromisoformat(data['completed_at'])
            data['status'] = JobStatus(data['status'])
            return JobResult(**data)
        return None

    async def get(self, job_id: str) -> Optional[JobResult]:
        data = await self.redis.get_json(self._get_key(job_id))
        if data:
            # 简单的从 dict 恢复，注意 datetime 转换
            if data.get('created_at'): data['created_at'] = datetime.fromisoformat(data['created_at'])
            if data.get('started_at'): data['started_at'] = datetime.fromisoformat(data['started_at'])
            if data.get('completed_at'): data['completed_at'] = datetime.fromisoformat(data['completed_at'])
            data['status'] = JobStatus(data['status'])
            return JobResult(**data)
        return None

    async def list(self, user_id: Optional[int] = None, limit: int = 50) -> List[JobResult]:
        """列出持久化的任务"""
        # 注意：这里在 Redis 中扫描所有任务键
        # 实际生产中应维护一个 sorted set 保存 job_id 索引
        keys = await self.redis._client.keys(f"{self.prefix}*")
        jobs = []
        for key in keys:
            job_id = key.split(":")[-1]
            job = await self.get(job_id)
            if job:
                if user_id is None or job.user_id == user_id:
                    jobs.append(job)

        # 按时间排序
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        return jobs[:limit]

    def list_sync(self, user_id: Optional[int] = None, limit: int = 50) -> List[JobResult]:
        """同步版本的 list，用于非 asyncio 线程 - 避免 'Future attached to a different loop' 错误"""
        keys = self.redis.keys_sync(f"{self.prefix}*")
        jobs = []
        for key in keys:
            job_id = key.split(":")[-1]
            job = self.get_sync(job_id)
            if job:
                if user_id is None or job.user_id == user_id:
                    jobs.append(job)

        # 按时间排序
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        return jobs[:limit]

    async def delete(self, job_id: str):
        await self.redis.delete(self._get_key(job_id))

class JobManager:
    """
    任务管理器 - 单例模式
    
    使用 ThreadPoolExecutor 异步执行 CrewAI 任务
    支持 JobStore 持久化
    """
    
    _instance: Optional['JobManager'] = None
    _lock = Lock()
    
    def __new__(cls, max_workers: int = 3) -> 'JobManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, max_workers: int = 3):
        if self._initialized:
            return

        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        # Memory management configuration
        self._max_jobs_in_memory = int(os.getenv("FAIC_JOB_MAX_IN_MEMORY", "200"))
        self._retention_hours = int(os.getenv("FAIC_JOB_RETENTION_HOURS", "24"))
        self._drop_result_from_memory = os.getenv("FAIC_JOB_DROP_RESULT_FROM_MEMORY", "true").lower() == "true"
        self._max_chat_messages_per_job = int(os.getenv("FAIC_JOB_MAX_CHAT_MESSAGES", "1000"))

        # OrderedDict for LRU tracking (insertion order = access order via move_to_end)
        self._jobs: OrderedDict[str, JobResult] = OrderedDict()
        self._futures: Dict[str, Future] = {}
        self._initialized = True
        self.store = RedisJobStore()

        logger.info(
            f"JobManager initialized: workers={max_workers}, "
            f"max_in_memory={self._max_jobs_in_memory}, "
            f"retention_hours={self._retention_hours}, "
            f"drop_results={self._drop_result_from_memory}"
        )

    def _persist_job(self, job: JobResult) -> None:
        """
        Best-effort persistence for both async (FastAPI) and sync callers.

        If drop_result_from_memory is enabled, nulls out the result field
        after successful persistence to Redis (keeps metadata in memory).
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.store.save(job))

            # Drop large result from memory after persistence (async path)
            if self._drop_result_from_memory and job.result is not None:
                job.result = None
                logger.debug(f"[Job {job.job_id}] Dropped result from memory after async persistence")

        except RuntimeError:
            try:
                self.store.save_sync(job)

                # Drop large result from memory after persistence (sync path)
                if self._drop_result_from_memory and job.result is not None:
                    job.result = None
                    logger.debug(f"[Job {job.job_id}] Dropped result from memory after sync persistence")

            except Exception:
                logger.warning(
                    f"[Job {job.job_id}] Failed to persist job state (sync path)",
                    exc_info=True,
                )

    def _evict_oldest_job(self) -> bool:
        """
        Evict the oldest job from memory (LRU policy).

        Only evicts completed/failed/cancelled jobs. Running/pending jobs are protected.
        Evicted jobs remain in Redis and can be restored via get_status().

        Returns:
            True if a job was evicted, False if no evictable jobs found.
        """
        # Find oldest evictable job (completed/failed/cancelled)
        evictable_states = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}

        for job_id in list(self._jobs.keys()):  # Iterate over copy to allow modification
            job = self._jobs[job_id]
            if job.status in evictable_states:
                # Evict this job
                del self._jobs[job_id]
                self._futures.pop(job_id, None)
                logger.debug(
                    f"[JobManager] LRU eviction: job_id={job_id}, status={job.status.value}, "
                    f"new_size={len(self._jobs)}"
                )
                return True

        # If no evictable jobs found (all running/pending), log warning
        logger.warning(
            f"[JobManager] Cache full ({len(self._jobs)} jobs) but all are running/pending - cannot evict"
        )
        return False

    def _enforce_memory_limit(self) -> None:
        """
        Enforce max jobs in memory limit via LRU eviction.

        Called before adding new jobs to ensure we stay under the limit.
        Stops if no evictable jobs are found (prevents infinite loop).
        """
        while len(self._jobs) >= self._max_jobs_in_memory:
            if not self._evict_oldest_job():
                # No evictable jobs - break to prevent infinite loop
                break

    def _is_job_expired(self, job: JobResult) -> bool:
        """Check if job is expired based on retention policy."""
        if not job.completed_at:
            return False
        cutoff = datetime.now() - timedelta(hours=self._retention_hours)
        return job.completed_at < cutoff

    def _emit_job_notification(self, job: JobResult) -> None:
        """
        Emit webhook event for job completion/failure (best-effort).

        Only emits for COMPLETED or FAILED status.
        Requires job.user_id to be set.
        """
        if job.user_id is None:
            return

        if job.status == JobStatus.COMPLETED:
            event_type = "jobs.analysis_completed"
            data = {
                "job_id": job.job_id,
                "ticker": job.ticker,
                "crew_name": job.crew_name,
            }
        elif job.status == JobStatus.FAILED:
            event_type = "jobs.analysis_failed"
            data = {
                "job_id": job.job_id,
                "ticker": job.ticker,
                "crew_name": job.crew_name,
                "error": job.error,
            }
        else:
            # RUNNING, PENDING, CANCELLED - don't emit
            return

        # Best-effort notification delivery
        try:
            from AICrews.database.db_manager import DBManager
            from AICrews.services.notification_service import NotificationService

            db_manager = DBManager()
            with db_manager.get_session() as session:
                NotificationService(session).emit_event(
                    job.user_id,
                    event_type,
                    data
                )
        except Exception:
            # Silent failure (best-effort delivery)
            logger.debug(
                f"[Job {job.job_id}] Failed to emit {event_type} notification",
                exc_info=True
            )

    def submit(
        self,
        func: Callable[..., Any],
        *args,
        ticker: Optional[str] = None,
        crew_name: Optional[str] = None,
        user_id: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        提交任务到线程池

        Enforces memory limit via LRU eviction before adding new job.
        """
        # Enforce memory limit before adding new job
        self._enforce_memory_limit()

        job_id = str(uuid.uuid4())

        # 创建任务记录
        job_result = JobResult(
            job_id=job_id,
            status=JobStatus.PENDING,
            ticker=ticker,
            crew_name=crew_name,
            user_id=user_id,
        )
        self._jobs[job_id] = job_result

        # 初始持久化
        self._persist_job(job_result)
        
        # 包装函数
        def wrapped_func(jid: str):
            job: Optional[JobResult] = None
            tracker = None
            try:
                job = self._jobs[jid]
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now()
                job.progress_message = "AI 智能体正在分析中..."
                self.store.save_sync(job)

                logger.info(
                    f"[Job {jid}] 🚀 开始执行 - ticker={job.ticker}, crew={job.crew_name}"
                )

                from AICrews.services.tracking_service import TrackingService
                tracker = TrackingService()
                try:
                    tracker.init_job(jid, ticker or "Unknown", crew_name or "Unknown")
                except Exception:
                    logger.warning(
                        f"[Job {jid}] Tracking init failed; continuing without tracking",
                        exc_info=True,
                    )

                import inspect
                sig = inspect.signature(func)
                if 'job_id' in sig.parameters:
                    kwargs['job_id'] = jid

                # Establish LogContext for this worker thread so CrewAI EventBus
                # listeners and other observability helpers can reliably resolve
                # job_id/run_id/user_id/ticker during execution.
                from AICrews.observability.logging import LogContext

                with LogContext(
                    job_id=jid,
                    run_id=jid,
                    user_id=job.user_id,
                    ticker=job.ticker,
                ):
                    result = func(*args, **kwargs)
                job.status = JobStatus.COMPLETED
                job.result = result
                job.progress = 100
                job.progress_message = "分析完成"
                job.completed_at = datetime.now()
                
                # 持久化完成状态
                self.store.save_sync(job)

                # Drop large result from memory after persistence (Tier 3 memory management)
                if self._drop_result_from_memory and job.result is not None:
                    job.result = None
                    logger.debug(f"[Job {jid}] Dropped result from memory after completion (can be recovered from Redis)")

                # Emit webhook event (best-effort, after persistence)
                self._emit_job_notification(job)

                try:
                    tracker.complete_job(jid, status="completed")
                except Exception:
                    logger.warning(
                        f"[Job {jid}] Tracking complete failed",
                        exc_info=True,
                    )

                return result
            except Exception as e:
                logger.error(f"[Job {jid}] Worker crashed during execution:\n{traceback.format_exc()}")
                logger.error(
                    f"[Job {jid}] Worker crashed during execution: {e}",
                    exc_info=True,
                )

                if job is not None:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    job.progress_message = f"分析失败: {str(e)}"
                    job.completed_at = datetime.now()
                
                # 持久化失败状态
                if job is not None:
                    try:
                        self.store.save_sync(job)
                    except Exception:
                        logger.error(f"[Job {jid}] Failed to persist job state:\n{traceback.format_exc()}")

                    # Emit webhook event (best-effort, after persistence)
                    self._emit_job_notification(job)

                if tracker is not None:
                    try:
                        tracker.complete_job(jid, status="failed", error=str(e))
                    except Exception:
                        logger.warning(
                            f"[Job {jid}] Tracking complete (failed) failed",
                            exc_info=True,
                        )
                raise
        
        future = self._executor.submit(wrapped_func, job_id)
        self._futures[job_id] = future

        def _log_unhandled_future_error(done: Future) -> None:
            try:
                done.result()
            except Exception:
                logger.error(
                    f"[Job {job_id}] Unhandled exception in worker future",
                    exc_info=True,
                )

        future.add_done_callback(_log_unhandled_future_error)
        return job_id

    def get_status(self, job_id: str, user_id: Optional[int] = None) -> Optional[JobResult]:
        """
        获取任务状态 (先查内存，再查持久化)

        Applies retention policy: expired jobs are not restored from Redis.
        """
        # Mark job as recently accessed (LRU)
        if job_id in self._jobs:
            self._jobs.move_to_end(job_id)

        job = self._jobs.get(job_id)
        if not job:
            # 尝试从 store 恢复 - 使用同步方法避免事件循环冲突
            try:
                job = self.store.get_sync(job_id)

                # Check retention policy before restoring to memory
                if job:
                    if self._is_job_expired(job):
                        logger.debug(f"[Job {job_id}] Expired, not restoring to memory")
                        return None  # Don't restore expired jobs

                    # Restore to memory (respecting memory limit)
                    self._enforce_memory_limit()
                    self._jobs[job_id] = job
            except Exception as e:
                logger.warning(f"Failed to fetch job {job_id} from store: {e}")

        if job and user_id is not None and job.user_id != user_id:
            return None
        return job

    
    def get_result(self, job_id: str) -> Optional[Any]:
        """获取任务结果

        If result was dropped from memory (FAIC_JOB_DROP_RESULT_FROM_MEMORY=true),
        attempts to recover from Redis.
        """
        job = self._jobs.get(job_id)
        if job and job.status == JobStatus.COMPLETED:
            # If result is in memory, return it
            if job.result is not None:
                return job.result

            # Result was dropped from memory - try to recover from Redis
            if self._drop_result_from_memory:
                try:
                    persisted_job = self.store.get_sync(job_id)

                    if persisted_job and persisted_job.result is not None:
                        logger.debug(f"[Job {job_id}] Recovered result from Redis")
                        return persisted_job.result
                except Exception as e:
                    logger.warning(f"[Job {job_id}] Failed to recover result from Redis: {e}")

            return None
        return None
    
    def cancel(self, job_id: str) -> bool:
        """取消任务"""
        future = self._futures.get(job_id)
        if future and not future.done():
            cancelled = future.cancel()
            if cancelled:
                job = self._jobs.get(job_id)
                if job:
                    job.status = JobStatus.CANCELLED
                    job.completed_at = datetime.now()
                logger.info(f"Job {job_id} cancelled")
            return cancelled
        return False
    
    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 50,
        user_id: Optional[int] = None,
    ) -> List[JobResult]:
        """
        列出任务 (合并内存与持久化存储)
        """
        # 1. 先获取内存中的任务
        memory_jobs = list(self._jobs.values())
        if user_id is not None:
            memory_jobs = [j for j in memory_jobs if j.user_id == user_id]
        if status:
            memory_jobs = [j for j in memory_jobs if j.status == status]
            
        # 2. 如果内存任务不够，从 store 获取 - 使用同步方法避免事件循环冲突
        if len(memory_jobs) < limit:
            try:
                persisted_jobs = self.store.list_sync(user_id=user_id, limit=limit)

                # 合并并去重
                seen_ids = {j.job_id for j in memory_jobs}
                for pj in persisted_jobs:
                    if pj.job_id not in seen_ids:
                        if not status or pj.status == status:
                            memory_jobs.append(pj)
            except Exception as e:
                logger.warning(f"Failed to list jobs from store: {e}")
        
        # 3. 按创建时间倒序排序
        memory_jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        return memory_jobs[:limit]
    
    def add_chat_message(
        self,
        job_id: str,
        role: str,
        content: str,
    ) -> bool:
        """
        添加聊天消息到任务

        用于 AI Copilot 功能
        Enforces per-job chat message limit to prevent unbounded growth.
        """
        job = self._jobs.get(job_id)
        if job:
            # Enforce per-job chat message limit
            if len(job.chat_history) >= self._max_chat_messages_per_job:
                # Evict oldest message (FIFO)
                evicted = job.chat_history.pop(0)
                logger.debug(
                    f"[Job {job_id}] Chat history full ({self._max_chat_messages_per_job} messages), "
                    f"evicted oldest message"
                )

            job.chat_history.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            })
            return True
        return False
    
    def update_progress(
        self,
        job_id: str,
        progress: int,
        message: str = "",
    ) -> bool:
        """更新任务进度"""
        job = self._jobs.get(job_id)
        if job:
            job.progress = min(max(progress, 0), 100)
            if message:
                job.progress_message = message
            return True
        return False
    
    def cleanup_old_jobs(self, hours: Optional[int] = None) -> int:
        """
        清理旧任务

        Args:
            hours: Override retention hours (defaults to FAIC_JOB_RETENTION_HOURS)

        Returns:
            Number of jobs cleaned up
        """
        retention = hours if hours is not None else self._retention_hours
        cutoff = datetime.now() - timedelta(hours=retention)

        to_remove = [
            job_id for job_id, job in self._jobs.items()
            if job.completed_at and job.completed_at < cutoff
        ]

        for job_id in to_remove:
            del self._jobs[job_id]
            self._futures.pop(job_id, None)

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old jobs (retention={retention}h)")
        return len(to_remove)
    
    async def recover_jobs(self):
        """恢复持久化存储中的异常任务 (如重启导致的僵死任务)"""
        logger.info("Starting job recovery process...")
        # 扫描所有任务
        if hasattr(self.store, 'redis') and hasattr(self.store, 'prefix'):
            keys = await self.store.redis._client.keys(f"{self.store.prefix}*")
            recovered_count = 0
            for key in keys:
                job_id = key.split(":")[-1]
                job = await self.store.get(job_id)
                if job and job.status in [JobStatus.RUNNING, JobStatus.PENDING]:
                    # 如果任务处于运行中或等待中但没有对应的线程在跑，说明是重启导致的僵死任务
                    if job_id not in self._futures:
                        logger.info(f"Marking zombie job {job_id} as FAILED due to system restart")
                        job.status = JobStatus.FAILED
                        job.error = "Job interrupted by system restart"
                        job.completed_at = datetime.now()
                        await self.store.save(job)
                        recovered_count += 1
            
            if recovered_count > 0:
                logger.info(f"Successfully recovered {recovered_count} zombie jobs")
            else:
                logger.info("No zombie jobs found to recover")
        else:
            logger.warning("Job recovery skipped: store does not support key scanning")

    def shutdown(self, wait: bool = True) -> None:
        """关闭线程池"""
        self._executor.shutdown(wait=wait)
        logger.info("JobManager shutdown")


# 全局单例
_manager: Optional[JobManager] = None


def get_job_manager(max_workers: int = 3) -> JobManager:
    """获取或创建全局 JobManager 实例"""
    global _manager
    if _manager is None:
        _manager = JobManager(max_workers=max_workers)
    return _manager
