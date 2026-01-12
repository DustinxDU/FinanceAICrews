"""Task output schema registry endpoints.

Exposes the `AICrews.application.crew.task_output_registry` metadata so the
frontend can discover available output schemas and render selection UIs.
"""

from typing import Any, Dict, List

from fastapi import APIRouter

from AICrews.application.crew.task_output_registry import list_output_schemas

router = APIRouter(prefix="/task-output-schemas", tags=["Task Output Schemas"])


@router.get("", summary="List task output schemas")
async def list_task_output_schemas() -> List[Dict[str, Any]]:
    return list_output_schemas()
