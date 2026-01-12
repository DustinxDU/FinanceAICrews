from __future__ import annotations

from AICrews.observability.logging import get_logger
from typing import Any, Dict, Optional

from AICrews.schemas.execution_graph import ExecutionGraph

logger = get_logger(__name__)


class RuntimeExecutor:
    """
    Runtime executor scaffold (v2 plan).

    Task 10 implementation: provides an async execute() entrypoint and delegates
    execution to _execute_graph(), which can be wired to CrewAI kickoff/Flow later.
    """

    async def execute(
        self,
        graph: ExecutionGraph,
        *,
        variables: Dict[str, Any],
        user_id: Optional[int] = None,
        crew_id: Optional[int] = None,
        job_id: Optional[str] = None,
        compiled_data: Optional[Dict[str, Any]] = None,
        instantiate_fn: Optional[Any] = None,
        state_store: Optional[Any] = None,
        executor_selector: Optional[Any] = None,
        error_config: Optional[Any] = None,
    ) -> Any:
        return await self._execute_graph(
            graph,
            variables=variables,
            user_id=user_id,
            crew_id=crew_id,
            job_id=job_id,
            compiled_data=compiled_data,
            instantiate_fn=instantiate_fn,
            state_store=state_store,
            executor_selector=executor_selector,
            error_config=error_config,
        )

    async def _execute_graph(
        self,
        graph: ExecutionGraph,
        *,
        variables: Dict[str, Any],
        user_id: Optional[int],
        crew_id: Optional[int],
        job_id: Optional[str],
        compiled_data: Optional[Dict[str, Any]],
        instantiate_fn: Optional[Any],
        state_store: Optional[Any],
        executor_selector: Optional[Any],
        error_config: Optional[Any],
    ) -> Any:
        if compiled_data is None or instantiate_fn is None:
            raise NotImplementedError(
                "RuntimeExecutor requires compiled_data + instantiate_fn until Flow executor is integrated"
            )

        from AICrews.execution.error_handler import ErrorHandler
        from AICrews.schemas.error_handling import ErrorConfig, ErrorStrategy
        from AICrews.execution.executor_selector import ExecutorSelector

        selector = executor_selector or ExecutorSelector(mode="kickoff")
        cfg = error_config or ErrorConfig(strategy=ErrorStrategy.STOP)

        run_id = job_id or "run"
        if state_store is not None:
            try:
                await state_store.set_execution_state(
                    run_id=run_id,
                    data={
                        "status": "running",
                        "crew_id": crew_id,
                        "user_id": user_id,
                        "variables": variables,
                    },
                )
            except Exception:
                logger.warning("Failed to persist execution_state start", exc_info=True)

        try:
            crew = instantiate_fn(compiled_data, job_id=job_id, user_id=user_id)

            async def _run_selected() -> Any:
                if selector.mode == "kickoff":
                    return crew.kickoff()
                raise NotImplementedError(f"Unsupported executor mode: {selector.mode}")

            handler = ErrorHandler()
            result = await handler.arun_with_policy(_run_selected, cfg)
            if state_store is not None:
                try:
                    await state_store.set_execution_state(
                        run_id=run_id,
                        data={
                            "status": "completed",
                            "crew_id": crew_id,
                            "user_id": user_id,
                        },
                    )
                except Exception:
                    logger.warning(
                        "Failed to persist execution_state completed", exc_info=True
                    )
            return result
        except Exception as e:
            if state_store is not None:
                try:
                    await state_store.set_execution_state(
                        run_id=run_id,
                        data={
                            "status": "failed",
                            "crew_id": crew_id,
                            "user_id": user_id,
                            "error": str(e),
                        },
                    )
                except Exception:
                    logger.warning("Failed to persist execution_state failed", exc_info=True)
            raise
