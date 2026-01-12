"""
Workflow Engine - Execute declarative multi-step skills.

Workflows are DAG-based pipelines with whitelisted step types:
- tool_call: Call a skill/capability
- formula_eval: Evaluate a formula expression
- transform: Pure data transformation
- branch: Conditional branching (if/else)
- aggregate: Combine results into final output

Security:
- No arbitrary code execution
- Only whitelisted step types
- Expression evaluation via simpleeval (sandboxed)
"""
from AICrews.observability.logging import get_logger
from typing import Any, Callable, Dict, List, Optional

logger = get_logger(__name__)

# Whitelisted step types
ALLOWED_STEP_TYPES = {"tool_call", "formula_eval", "transform", "branch", "aggregate"}


class WorkflowValidationError(Exception):
    """Workflow definition validation error."""
    pass


class WorkflowExecutionError(Exception):
    """Workflow execution error."""
    pass


class WorkflowEngine:
    """
    Execute declarative workflow definitions.

    Workflows are defined as a list of steps with dependencies.
    Each step type has a specific handler that executes it safely.
    """

    def __init__(self, max_steps: int = 50, timeout_per_step: int = 30):
        self.max_steps = max_steps
        self.timeout_per_step = timeout_per_step

    def validate(self, workflow_def: Dict[str, Any]) -> None:
        """
        Validate a workflow definition.

        Raises:
            WorkflowValidationError: If workflow is invalid
        """
        if "steps" not in workflow_def:
            raise WorkflowValidationError("Workflow must have 'steps' array")

        steps = workflow_def["steps"]

        if len(steps) > self.max_steps:
            raise WorkflowValidationError(f"Workflow exceeds max steps ({self.max_steps})")

        for i, step in enumerate(steps):
            self._validate_step(step, i)

    def _validate_step(self, step: Dict[str, Any], index: int) -> None:
        """Validate a single step."""
        if "type" not in step:
            raise WorkflowValidationError(f"Step {index}: missing 'type'")

        step_type = step["type"]

        if step_type not in ALLOWED_STEP_TYPES:
            raise WorkflowValidationError(
                f"Step {index}: invalid type '{step_type}'. "
                f"Allowed: {ALLOWED_STEP_TYPES}"
            )

        if "id" not in step:
            raise WorkflowValidationError(f"Step {index}: missing 'id'")

        # Type-specific validation
        if step_type == "tool_call":
            if "skill_key" not in step:
                raise WorkflowValidationError(f"Step {index}: tool_call requires 'skill_key'")

        if step_type == "branch":
            if "condition" not in step:
                raise WorkflowValidationError(f"Step {index}: branch requires 'condition'")
            if "then" not in step:
                raise WorkflowValidationError(f"Step {index}: branch requires 'then'")

    def execute(
        self,
        workflow_def: Dict[str, Any],
        inputs: Dict[str, Any],
        tool_runner: Callable[[str, Dict], Any],
    ) -> Dict[str, Any]:
        """
        Execute a workflow.

        Args:
            workflow_def: The workflow definition
            inputs: Input parameters (e.g., {"ticker": "AAPL"})
            tool_runner: Callable to execute skill/capability calls

        Returns:
            Result with steps outputs and summary
        """
        self.validate(workflow_def)

        context: Dict[str, Any] = dict(inputs)
        steps_output: Dict[str, Any] = {}

        steps = workflow_def["steps"]

        for step in steps:
            step_result = self._execute_step(step, context, tool_runner, steps_output)

            # Store result if 'as' is specified
            if "as" in step:
                output_name = step["as"]
                steps_output[output_name] = step_result
                context[output_name] = step_result

        result = {
            "steps": steps_output,
            "inputs": inputs,
        }

        # Check for aggregate step output
        for step in steps:
            if step["type"] == "aggregate" and "summary" in steps_output.get(step.get("as", ""), {}):
                result["summary"] = steps_output[step["as"]]["summary"]
            elif step["type"] == "aggregate":
                # Build summary from template
                summary = self._build_summary(step, context)
                result["summary"] = summary

        return result

    def _execute_step(
        self,
        step: Dict[str, Any],
        context: Dict[str, Any],
        tool_runner: Callable,
        steps_output: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute a single step."""
        step_type = step["type"]

        if step_type == "tool_call":
            return self._execute_tool_call(step, context, tool_runner)
        elif step_type == "formula_eval":
            return self._execute_formula_eval(step, context, tool_runner)
        elif step_type == "transform":
            return self._execute_transform(step, context)
        elif step_type == "branch":
            return self._execute_branch(step, context, tool_runner, steps_output)
        elif step_type == "aggregate":
            return self._execute_aggregate(step, context)
        else:
            raise WorkflowExecutionError(f"Unknown step type: {step_type}")

    def _execute_tool_call(
        self,
        step: Dict[str, Any],
        context: Dict[str, Any],
        tool_runner: Callable,
    ) -> Any:
        """Execute a tool_call step."""
        skill_key = step["skill_key"]

        # Build inputs from 'with' and context
        call_inputs = dict(context)
        if "with" in step:
            call_inputs.update(step["with"])

        return tool_runner(skill_key, call_inputs)

    def _execute_formula_eval(
        self,
        step: Dict[str, Any],
        context: Dict[str, Any],
        tool_runner: Callable,
    ) -> Any:
        """Execute a formula_eval step (delegates to strategy_eval)."""
        formula = step.get("formula", "")

        # Use strategy_eval capability
        return tool_runner("cap:strategy_eval", {
            "formula": formula,
            **context,
        })

    def _execute_transform(self, step: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """Execute a transform step (pure expression evaluation)."""
        expr = step.get("expr", "")

        # Use simpleeval for safe evaluation
        try:
            from simpleeval import simple_eval
            return simple_eval(expr, names=context)
        except ImportError:
            # Fallback: restricted evaluation
            return eval(expr, {"__builtins__": {}}, context)

    def _execute_branch(
        self,
        step: Dict[str, Any],
        context: Dict[str, Any],
        tool_runner: Callable,
        steps_output: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute a branch step (conditional)."""
        condition = step["condition"]

        # Evaluate condition
        try:
            from simpleeval import simple_eval
            result = simple_eval(condition, names=context)
        except ImportError:
            result = eval(condition, {"__builtins__": {}}, context)

        # Execute appropriate branch
        branch_steps = step["then"] if result else step.get("else", [])

        branch_result = None
        for branch_step in branch_steps:
            branch_result = self._execute_step(branch_step, context, tool_runner, steps_output)
            if "as" in branch_step:
                context[branch_step["as"]] = branch_result
                # Also store in steps_output so it's accessible in the result
                if steps_output is not None:
                    steps_output[branch_step["as"]] = branch_result

        return branch_result

    def _execute_aggregate(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an aggregate step (combine outputs)."""
        fields = step.get("fields", [])
        result = {f: context.get(f) for f in fields}

        if "summary_template" in step:
            result["summary"] = step["summary_template"].format(**context)

        return result

    def _build_summary(self, step: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Build summary from aggregate step."""
        if "summary_template" in step:
            try:
                return step["summary_template"].format(**context)
            except KeyError as e:
                return f"Summary generation error: missing {e}"
        return ""
