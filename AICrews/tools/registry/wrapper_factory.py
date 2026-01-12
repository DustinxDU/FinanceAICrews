"""Factory for generating CrewAI tool wrappers from skill definitions.

This module provides WrapperFactory which creates callable tools from SkillCatalog
entries. Different skill kinds are handled differently:

- capability: Returns primitive tool directly (no wrapping)
- preset: Creates wrapper with partial parameter binding (e.g., RSI(14))
- strategy: Creates wrapper calling evaluate_strategy with bound formula
- skillset: Creates wrapper calling WorkflowEngine (legacy "workflow" renamed to "skillset")

All wrappers expose a simplified interface (usually just `ticker: str`) to reduce
LLM parameter guessing.
"""
from typing import Dict, Any, Callable, Optional
from functools import wraps
from crewai.tools import tool
from AICrews.database.models.skill import SkillCatalog, SkillKind
from AICrews.skills.workflow_engine import WorkflowEngine


class WrapperFactory:
    """Generate callable tools from skill catalog entries."""

    def __init__(self):
        """Initialize wrapper factory with workflow engine."""
        self.workflow_engine = WorkflowEngine()

    def generate_tool(
        self,
        skill: SkillCatalog,
        primitives: Optional[Dict[str, Callable]] = None,
        workflow_engine: Optional[WorkflowEngine] = None
    ) -> Callable:
        """
        Generate a callable tool from skill definition.

        Args:
            skill: SkillCatalog entry defining the skill
            primitives: Dict mapping capability_id -> primitive callable
            workflow_engine: Optional custom workflow engine (for testing)

        Returns:
            Callable tool ready to mount to Agent

        Raises:
            ValueError: If skill kind is unknown or required primitive missing
        """
        if primitives is None:
            primitives = {}

        if skill.kind == SkillKind.capability:
            return self._generate_capability_tool(skill, primitives)
        elif skill.kind == SkillKind.preset:
            return self._generate_preset_tool(skill, primitives)
        elif skill.kind == SkillKind.strategy:
            return self._generate_strategy_tool(skill, primitives)
        elif skill.kind == SkillKind.skillset:
            engine = workflow_engine if workflow_engine is not None else self.workflow_engine
            return self._generate_workflow_tool(skill, engine)
        else:
            raise ValueError(f"Unknown skill kind: {skill.kind}")

    def _generate_capability_tool(
        self,
        skill: SkillCatalog,
        primitives: Dict[str, Callable]
    ) -> Callable:
        """
        Return primitive tool directly (no wrapping needed for capabilities).

        Args:
            skill: Capability skill definition
            primitives: Available primitive tools

        Returns:
            The primitive callable

        Raises:
            ValueError: If primitive not found
        """
        capability_id = skill.invocation.get("capability_id")
        if not capability_id:
            raise ValueError(f"Missing capability_id in invocation for {skill.skill_key}")

        if capability_id not in primitives:
            raise ValueError(
                f"Primitive not found for capability: {capability_id}. "
                f"Available: {list(primitives.keys())}"
            )

        return primitives[capability_id]

    def _generate_preset_tool(
        self,
        skill: SkillCatalog,
        primitives: Dict[str, Callable]
    ) -> Callable:
        """
        Generate wrapper with partial parameter binding.

        Creates a tool that calls the underlying primitive with preset defaults
        (e.g., RSI(14) only needs ticker, period=14 is fixed).

        Args:
            skill: Preset skill definition
            primitives: Available primitive tools

        Returns:
            Wrapped tool with bound defaults

        Raises:
            ValueError: If primitive not found
        """
        capability_id = skill.invocation.get("capability_id")
        defaults = skill.invocation.get("defaults", {})

        if not capability_id:
            raise ValueError(f"Missing capability_id in invocation for {skill.skill_key}")

        primitive = primitives.get(capability_id)
        if not primitive:
            raise ValueError(
                f"Primitive not found for capability: {capability_id}. "
                f"Available: {list(primitives.keys())}"
            )

        # Extract preset name from skill_key (preset:pack:name -> name)
        preset_name = skill.skill_key.split(":")[-1]
        description = skill.description or f"Preset: {preset_name}"

        # Create wrapper with crewai @tool decorator
        # Need to create function dynamically to set docstring
        def create_preset_wrapper():
            def preset_wrapper(ticker: str) -> str:
                return primitive(ticker=ticker, **defaults)

            preset_wrapper.__doc__ = f"Preset tool wrapper with bound default parameters.\n\n{description}"
            return tool(preset_name)(preset_wrapper)

        return create_preset_wrapper()

    def _generate_strategy_tool(
        self,
        skill: SkillCatalog,
        primitives: Dict[str, Callable]
    ) -> Callable:
        """
        Generate wrapper calling evaluate_strategy with bound formula.

        Creates a tool that evaluates a user-defined strategy (formula)
        against a ticker.

        Args:
            skill: Strategy skill definition
            primitives: Available primitive tools (must include strategy_eval)

        Returns:
            Strategy wrapper tool

        Raises:
            ValueError: If strategy_eval primitive not found
        """
        strategy_id = skill.invocation.get("strategy_id")
        formula = skill.invocation.get("formula")

        evaluate_strategy = primitives.get("strategy_eval")
        if not evaluate_strategy:
            raise ValueError(
                "strategy_eval primitive not found. "
                f"Available: {list(primitives.keys())}"
            )

        strategy_name = f"strategy_{strategy_id}"
        description = skill.description or f"User strategy {strategy_id}: {formula}"

        # Create wrapper dynamically to set docstring
        def create_strategy_wrapper():
            def strategy_wrapper(ticker: str) -> str:
                return evaluate_strategy(
                    ticker=ticker,
                    strategy_id=strategy_id,
                    formula=formula
                )

            strategy_wrapper.__doc__ = f"User strategy wrapper.\n\n{description}"
            return tool(strategy_name)(strategy_wrapper)

        return create_strategy_wrapper()

    def _generate_workflow_tool(
        self,
        skill: SkillCatalog,
        engine: WorkflowEngine
    ) -> Callable:
        """
        Generate wrapper calling WorkflowEngine.

        Creates a tool that executes a multi-step workflow defined
        in the skill's invocation.

        Args:
            skill: Workflow skill definition
            engine: WorkflowEngine instance

        Returns:
            Workflow wrapper tool
        """
        # Extract workflow name from skill_key (skillset:pack:name -> name)
        workflow_name = skill.skill_key.split(":")[-1]
        workflow_def = skill.invocation
        description = skill.description or f"Workflow: {workflow_name}"

        # Create wrapper dynamically to set docstring
        def create_workflow_wrapper():
            def workflow_wrapper(ticker: str) -> str:
                result = engine.execute(
                    workflow_def=workflow_def,
                    inputs={"ticker": ticker},
                    tool_runner=None  # TODO: Pass actual tool_runner in runtime integration
                )

                # Return summary if available, otherwise full result
                if isinstance(result, dict):
                    return result.get("summary", str(result))
                return str(result)

            workflow_wrapper.__doc__ = f"Multi-step workflow wrapper.\n\n{description}"
            return tool(f"{workflow_name}_workflow")(workflow_wrapper)

        return create_workflow_wrapper()


def create_primitive_registry() -> Dict[str, Callable]:
    """
    Create registry of primitive tools (capabilities).

    This is a placeholder that should be replaced with actual primitive
    tool implementations from the existing codebase.

    Returns:
        Dict mapping capability_id -> primitive callable
    """
    # TODO: Import actual primitives from AICrews.tools.*
    # For now, return empty dict - real implementation will populate this
    return {}
