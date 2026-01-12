from __future__ import annotations

from typing import Any, Dict, List

from AICrews.schemas.execution_graph import ExecutionGraph


class LightweightCompiler:
    """
    Lightweight compiler (v2 plan):
    - validates minimal structure
    - does NOT interpolate variables
    - produces an ExecutionGraph for runtime execution
    """

    def compile_from_compilation_result(
        self,
        *,
        structure: List[Dict[str, Any]],
        input_schema: Dict[str, Any],
        output_config: Dict[str, Any],
        warnings: List[str] | None = None,
    ) -> ExecutionGraph:
        return ExecutionGraph(
            structure=list(structure or []),
            input_schema=dict(input_schema or {}),
            output_config=dict(output_config or {}),
            warnings=list(warnings or []),
        )

