from __future__ import annotations

from AICrews.observability.logging import get_logger
from typing import Any, Dict, Optional

from AICrews.schemas.execution_state import (
    ExecutionCheckpoint,
    ExecutionState,
    TaskStatus,
)

logger = get_logger(__name__)


class ExecutionStateStore:
    """
    Redis-backed execution state persistence.

    Keys:
    - execution_state:{run_id}
    - checkpoint:{run_id}:{checkpoint_id}
    - task_status:{run_id}:{task_id}
    """

    def __init__(self, redis_manager: Any, *, ttl_seconds: int = 3600):
        self._redis = redis_manager
        self._ttl_seconds = int(ttl_seconds)

    def _key_execution_state(self, run_id: str) -> str:
        return f"execution_state:{run_id}"

    def _key_checkpoint(self, run_id: str, checkpoint_id: str) -> str:
        return f"checkpoint:{run_id}:{checkpoint_id}"

    def _key_task_status(self, run_id: str, task_id: str) -> str:
        return f"task_status:{run_id}:{task_id}"

    async def get_execution_state(self, *, run_id: str) -> Optional[ExecutionState]:
        try:
            raw = await self._redis.get_json(self._key_execution_state(run_id))
            if not raw:
                return None
            return ExecutionState.model_validate(raw)
        except Exception as e:
            logger.error("Failed to get execution state: run_id=%s err=%s", run_id, e)
            return None

    async def set_execution_state(
        self, *, run_id: str, data: Dict[str, Any], ttl_seconds: Optional[int] = None
    ) -> bool:
        ttl = self._ttl_seconds if ttl_seconds is None else int(ttl_seconds)
        state = ExecutionState(run_id=run_id, data=data)
        try:
            return bool(
                await self._redis.set(
                    self._key_execution_state(run_id),
                    state.model_dump(),
                    ttl=ttl,
                    json_encode=True,
                )
            )
        except Exception as e:
            logger.error("Failed to set execution state: run_id=%s err=%s", run_id, e)
            return False

    async def append_checkpoint(
        self,
        *,
        run_id: str,
        checkpoint_id: str,
        data: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        ttl = self._ttl_seconds if ttl_seconds is None else int(ttl_seconds)
        cp = ExecutionCheckpoint(run_id=run_id, checkpoint_id=checkpoint_id, data=data)
        try:
            return bool(
                await self._redis.set(
                    self._key_checkpoint(run_id, checkpoint_id),
                    cp.model_dump(),
                    ttl=ttl,
                    json_encode=True,
                )
            )
        except Exception as e:
            logger.error(
                "Failed to append checkpoint: run_id=%s checkpoint_id=%s err=%s",
                run_id,
                checkpoint_id,
                e,
            )
            return False

    async def set_task_status(
        self,
        *,
        run_id: str,
        task_id: str,
        status: str,
        detail: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        ttl = self._ttl_seconds if ttl_seconds is None else int(ttl_seconds)
        ts = TaskStatus(run_id=run_id, task_id=task_id, status=status, detail=detail)
        try:
            return bool(
                await self._redis.set(
                    self._key_task_status(run_id, task_id),
                    ts.model_dump(),
                    ttl=ttl,
                    json_encode=True,
                )
            )
        except Exception as e:
            logger.error(
                "Failed to set task status: run_id=%s task_id=%s err=%s",
                run_id,
                task_id,
                e,
            )
            return False

