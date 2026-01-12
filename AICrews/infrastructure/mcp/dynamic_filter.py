from typing import List, Dict, Any, Callable, Optional


def create_context_aware_filter(
    allowed_tools: Optional[List[str]] = None,
    blocked_tools: Optional[List[str]] = None,
    agent_roles_allowed: Optional[List[str]] = None,
) -> Callable[[str, Dict[str, Any]], bool]:
    allowed = set(allowed_tools or [])
    blocked = set(blocked_tools or [])
    roles = set(agent_roles_allowed or [])

    def filter_func(agent_role: str, tool: Dict[str, Any]) -> bool:
        tool_name = tool.get("name", "")

        if roles and agent_role not in roles:
            return True

        if blocked and tool_name in blocked:
            return False

        if allowed and tool_name not in allowed:
            return False

        return True

    return filter_func


class ToolFilterContext:
    def __init__(
        self,
        agent_role: str,
        agent_goal: str = "",
        task_description: str = "",
    ):
        self.agent_role = agent_role
        self.agent_goal = agent_goal
        self.task_description = task_description

    @property
    def agent(self) -> "AgentInfo":
        return AgentInfo(role=self.agent_role, goal=self.agent_goal)


class AgentInfo:
    def __init__(self, role: str, goal: str = ""):
        self.role = role
        self.goal = goal
