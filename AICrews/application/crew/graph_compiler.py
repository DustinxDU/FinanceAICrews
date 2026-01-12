"""
Graph Compiler - 将前端 UI 图编译为可执行结构

核心职责:
1. 拓扑排序: 解析 ui_state.edges 确定执行顺序
2. 依赖注入: 自动生成 Task 的 context 依赖
3. 任务生成: 从 Agent 节点提取 Task 并写入数据库
4. 知识绑定: 从 Knowledge 连线同步到 Agent 的 knowledge_source_ids
5. Router 编译: 将路由节点转换为可执行的 Task 链
6. Start/End 处理: 生成输入校验和输出汇总 Task

Philosophy: Compile at Save-time, Execute at Run-time
"""

from AICrews.observability.logging import get_logger
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from AICrews.database.models import (
    AgentDefinition,
    TaskDefinition,
    CrewDefinition,
    KnowledgeSource,
)

from AICrews.config.prompt_config import get_prompt_config_loader

logger = get_logger(__name__)

_graph_config: Optional[Dict[str, Any]] = None
_reporter_agent_config: Optional[Dict[str, Any]] = None


def _get_graph_config() -> Dict[str, Any]:
    """Load graph compiler config lazily (avoid import-time I/O)."""
    global _graph_config
    if _graph_config is None:
        try:
            prompt_loader = get_prompt_config_loader()
            internal_config = prompt_loader.get_config("internal") or {}
            if not isinstance(internal_config, dict):
                internal_config = {}
            _graph_config = internal_config.get("graph_compiler", {}) or {}
        except Exception:
            logger.debug("Failed to load graph compiler config", exc_info=True)
            _graph_config = {}
    return _graph_config


def _get_reporter_agent_config() -> Dict[str, Any]:
    """Load reporter agent config lazily from config/prompts/internal.yaml."""
    global _reporter_agent_config
    if _reporter_agent_config is None:
        try:
            prompt_loader = get_prompt_config_loader()
            internal_config = prompt_loader.get_config("internal") or {}
            if not isinstance(internal_config, dict):
                internal_config = {}
            _reporter_agent_config = internal_config.get("reporter_agent", {}) or {}
        except Exception:
            logger.debug("Failed to load reporter agent config", exc_info=True)
            _reporter_agent_config = {}

    # Fallback defaults if config is missing
    if not _reporter_agent_config:
        _reporter_agent_config = {
            "role": "Reporter",  # 统一显示名称
            "goal": "Synthesize complex financial analyses into clear, actionable reports.",
            "backstory": "You are an expert financial report writer with years of experience at top investment banks.",
            "default_skill_keys": [
                "cap:chart_generator",
                "cap:table_formatter",
                "cap:markdown_exporter",
                "cap:pdf_exporter",
                "cap:ppt_generator",
            ],
        }

    return _reporter_agent_config


def _find_existing_router_task_id(structure: Optional[List[Dict[str, Any]]], router_id: str) -> Optional[int]:
    for entry in structure or []:
        if entry.get("type") != "router":
            continue
        if entry.get("router_id") != router_id:
            continue
        decision_task_id = entry.get("decision_task_id")
        if isinstance(decision_task_id, int):
            return decision_task_id
    return None


def _find_existing_summary_task_id(structure: Optional[List[Dict[str, Any]]]) -> Optional[int]:
    for entry in structure or []:
        if entry.get("type") != "summary":
            continue
        task_id = entry.get("task_id")
        if isinstance(task_id, int):
            return task_id
    return None


def _find_existing_summary_task_id_from_router_config(router_config: Any) -> Optional[int]:
    if not isinstance(router_config, dict):
        return None
    output_config = router_config.get("output_config")
    if not isinstance(output_config, dict):
        return None
    task_id = output_config.get("summary_task_id")
    if isinstance(task_id, int):
        return task_id
    return None


@dataclass
class CompiledNode:
    """编译后的节点"""
    id: str
    type: str  # start, agent, router, knowledge, end
    data: Dict[str, Any]
    order: int = 0  # 拓扑排序后的执行顺序
    upstream_nodes: List[str] = field(default_factory=list)
    downstream_nodes: List[str] = field(default_factory=list)
    knowledge_sources: List[int] = field(default_factory=list)  # 绑定的知识源 ID


@dataclass
class CompiledEdge:
    """编译后的边"""
    source: str
    target: str
    edge_type: str  # control (实线) or resource (虚线)
    source_handle: Optional[str] = None  # Router 分支标识


@dataclass
class CompilationResult:
    """编译结果"""
    success: bool
    structure: List[Dict[str, Any]]  # 可执行的 agent-task 结构
    input_schema: Dict[str, Any]  # Start 节点的输入 schema
    output_config: Dict[str, Any]  # End 节点的输出配置
    router_tasks: List[Dict[str, Any]]  # Router 生成的决策 Task
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    created_task_ids: List[int] = field(default_factory=list)  # 新创建的 Task ID
    created_agent_ids: List[int] = field(default_factory=list)  # 新创建的 Agent ID (如 Reporter Agent)
    updated_agent_ids: List[int] = field(default_factory=list)  # 更新了知识绑定的 Agent ID


class GraphCompiler:
    """
    图编译器
    
    将前端 UI 图 (ui_state) 编译为后端可执行的结构
    """
    
    def __init__(self, session: Session, user_id: int, crew_def: CrewDefinition):
        self.session = session
        self.user_id = user_id
        self.crew_def = crew_def
        
        # 解析后的节点和边
        self.nodes: Dict[str, CompiledNode] = {}
        self.edges: List[CompiledEdge] = []
        
        # 按类型分组的节点
        self.start_node: Optional[CompiledNode] = None
        self.end_node: Optional[CompiledNode] = None
        self.agent_nodes: List[CompiledNode] = []
        self.router_nodes: List[CompiledNode] = []
        self.knowledge_nodes: List[CompiledNode] = []
    
    def compile(self) -> CompilationResult:
        """
        执行编译
        
        Returns:
            CompilationResult: 编译结果
        """
        result = CompilationResult(
            success=True,
            structure=[],
            input_schema={},
            output_config={},
            router_tasks=[],
        )
        
        ui_state = self.crew_def.ui_state
        if not ui_state:
            result.warnings.append("No ui_state found, using existing structure")
            result.structure = self.crew_def.structure or []
            return result
        
        try:
            # Step 1: 解析节点和边
            self._parse_nodes(ui_state.get("nodes", []))
            self._parse_edges(ui_state.get("edges", []))
            
            # Step 2: 验证图结构
            validation_errors = self._validate_graph()
            if validation_errors:
                result.errors.extend(validation_errors)
                result.success = False
                return result
            
            # Step 3: 拓扑排序
            sorted_nodes = self._topological_sort()
            if sorted_nodes is None:
                result.errors.append("Cycle detected in graph - cannot determine execution order")
                result.success = False
                return result
            
            # Step 4: 处理知识源绑定 (从 Knowledge 节点连线)
            self._compile_knowledge_bindings(result)

            # Step 4.5: 处理 MCP 工具绑定 (从 Agent 节点配置)
            self._compile_tool_bindings(result)

            # Step 4.6: 处理技能绑定 (从 Agent 节点 selectedSkillKeys 到 skill_keys)
            self._compile_skill_bindings(result)

            # Step 5: 处理 Start 节点 (输入 schema)
            result.input_schema = self._compile_start_node()
            
            # Step 6: 处理 Agent 节点 (生成 Task)
            self._compile_agent_nodes(result, sorted_nodes)
            
            # Step 7: 处理 Router 节点 (生成决策 Task)
            self._compile_router_nodes(result, sorted_nodes)
            
            # Step 8: 处理 End 节点 (生成汇总 Task)
            result.output_config = self._compile_end_node(result)
            
            # Step 9: 生成最终的 structure
            result.structure = self._generate_structure(sorted_nodes)
            
            logger.info(f"Compiled graph for crew '{self.crew_def.name}': "
                       f"{len(result.structure)} agents, "
                       f"{len(result.created_task_ids)} tasks created")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Compilation failed: {str(e)}")
            logger.exception("Graph compilation error")
        
        return result
    
    def _parse_nodes(self, nodes_data: List[Dict]) -> None:
        """解析节点数据"""
        for node in nodes_data:
            node_id = node.get("id", "")
            node_type = node.get("type", "")
            node_data = node.get("data", {})
            
            compiled = CompiledNode(
                id=node_id,
                type=node_type,
                data=node_data,
            )
            self.nodes[node_id] = compiled
            
            # 按类型分组
            if node_type == "start":
                self.start_node = compiled
            elif node_type == "end":
                self.end_node = compiled
            elif node_type == "agent":
                self.agent_nodes.append(compiled)
            elif node_type == "router":
                self.router_nodes.append(compiled)
            elif node_type == "knowledge":
                self.knowledge_nodes.append(compiled)
    
    def _parse_edges(self, edges_data: List[Dict]) -> None:
        """解析边数据"""
        for edge in edges_data:
            source = edge.get("from", edge.get("source", ""))
            target = edge.get("to", edge.get("target", ""))
            edge_type = edge.get("type", "control")
            source_handle = edge.get("sourceHandle")
            
            compiled = CompiledEdge(
                source=source,
                target=target,
                edge_type=edge_type,
                source_handle=source_handle,
            )
            self.edges.append(compiled)
            
            # 更新节点的上下游关系
            if source in self.nodes:
                self.nodes[source].downstream_nodes.append(target)
            if target in self.nodes:
                self.nodes[target].upstream_nodes.append(source)
    
    def _validate_graph(self) -> List[str]:
        """验证图结构"""
        errors = []
        
        # 必须有且仅有一个 Start 节点
        if not self.start_node:
            errors.append("Missing Start node")
        
        # 必须有且仅有一个 End 节点
        if not self.end_node:
            errors.append("Missing End node")
        
        # 至少有一个 Agent 节点
        if not self.agent_nodes:
            errors.append("At least one Agent node is required")
        
        # Start 节点不能有入边
        if self.start_node and self.start_node.upstream_nodes:
            errors.append("Start node cannot have incoming edges")
        
        # End 节点不能有出边
        if self.end_node and self.end_node.downstream_nodes:
            errors.append("End node cannot have outgoing edges")
        
        # 所有 Agent 节点必须可达 (从 Start 到 End)
        reachable = self._find_reachable_nodes()
        for agent in self.agent_nodes:
            if agent.id not in reachable:
                errors.append(f"Agent '{agent.data.get('role', agent.id)}' is not reachable from Start")
        
        return errors
    
    def _find_reachable_nodes(self) -> Set[str]:
        """从 Start 节点出发，找到所有可达节点"""
        if not self.start_node:
            return set()
        
        reachable = set()
        queue = deque([self.start_node.id])
        
        while queue:
            node_id = queue.popleft()
            if node_id in reachable:
                continue
            reachable.add(node_id)
            
            node = self.nodes.get(node_id)
            if node:
                for downstream in node.downstream_nodes:
                    if downstream not in reachable:
                        queue.append(downstream)
        
        return reachable
    
    def _topological_sort(self) -> Optional[List[CompiledNode]]:
        """
        拓扑排序 (Kahn's algorithm)
        
        Returns:
            排序后的节点列表，如果有环则返回 None
        """
        # 计算入度 (只考虑控制流边)
        in_degree = defaultdict(int)
        for node_id in self.nodes:
            in_degree[node_id] = 0
        
        for edge in self.edges:
            if edge.edge_type == "control":
                in_degree[edge.target] += 1
        
        # 从入度为 0 的节点开始
        queue = deque([
            node_id for node_id, degree in in_degree.items()
            if degree == 0
        ])
        
        sorted_nodes = []
        order = 0
        
        while queue:
            node_id = queue.popleft()
            node = self.nodes.get(node_id)
            if node:
                node.order = order
                order += 1
                sorted_nodes.append(node)
                
                # 减少下游节点的入度
                for edge in self.edges:
                    if edge.source == node_id and edge.edge_type == "control":
                        in_degree[edge.target] -= 1
                        if in_degree[edge.target] == 0:
                            queue.append(edge.target)
        
        # 检查是否所有节点都被处理 (有环则不会)
        if len(sorted_nodes) != len(self.nodes):
            return None
        
        return sorted_nodes
    
    def _compile_knowledge_bindings(self, result: CompilationResult) -> None:
        """
        编译知识源绑定
        
        从 Knowledge 节点到 Agent 节点的虚线连接，同步到 Agent 的 knowledge_source_ids
        """
        # 收集每个 Agent 绑定的知识源
        agent_knowledge_map: Dict[str, List[int]] = defaultdict(list)
        
        for edge in self.edges:
            if edge.edge_type == "resource":
                source_node = self.nodes.get(edge.source)
                target_node = self.nodes.get(edge.target)
                
                if (source_node and source_node.type == "knowledge" and
                    target_node and target_node.type == "agent"):
                    # 获取 Knowledge 节点配置的 source_id
                    knowledge_id = source_node.data.get("knowledge_id") or source_node.data.get("sourceId")
                    if knowledge_id:
                        agent_knowledge_map[edge.target].append(int(knowledge_id))
                        target_node.knowledge_sources.append(int(knowledge_id))
        
        # 更新 Agent 节点对应的 AgentDefinition
        for agent_node in self.agent_nodes:
            agent_id = agent_node.data.get("agent_id")
            if not agent_id:
                continue
            
            agent_def = self.session.get(AgentDefinition, agent_id)
            if not agent_def:
                continue
            
            # 更新知识源绑定
            new_knowledge_ids = agent_knowledge_map.get(agent_node.id, [])
            if agent_def.knowledge_source_ids != new_knowledge_ids:
                agent_def.knowledge_source_ids = new_knowledge_ids
                agent_def.updated_at = datetime.now()
                result.updated_agent_ids.append(agent_id)
                logger.info(f"Updated knowledge bindings for agent {agent_id}: {new_knowledge_ids}")

    def _compile_tool_bindings(self, result: CompilationResult) -> None:
        """
        编译 MCP 工具绑定

        从 Agent 节点的工具配置同步到 AgentDefinition 的 tool_ids 和 mcp_server_ids
        """
        for agent_node in self.agent_nodes:
            agent_id = agent_node.data.get("agent_id") or agent_node.data.get("agentId")
            if not agent_id:
                continue

            agent_def = self.session.get(AgentDefinition, agent_id)
            if not agent_def:
                continue

            # 从前端 Agent 节点数据提取工具配置
            tools_config = agent_node.data.get("tools", [])
            mcp_tools = agent_node.data.get("mcpTools", [])

            # 更新传统工具 IDs
            new_tool_ids = []
            for tool in tools_config:
                if isinstance(tool, dict) and "id" in tool:
                    new_tool_ids.append(tool["id"])
                elif isinstance(tool, (int, str)):
                    new_tool_ids.append(int(tool))

            # 更新 MCP 服务器 IDs
            new_mcp_server_ids = []
            for mcp_tool in mcp_tools:
                if isinstance(mcp_tool, dict):
                    server_id = mcp_tool.get("server_id") or mcp_tool.get("serverId")
                    if server_id:
                        new_mcp_server_ids.append(int(server_id))

            # 检查是否需要更新
            updated = False
            if agent_def.tool_ids != new_tool_ids:
                agent_def.tool_ids = new_tool_ids
                updated = True
                logger.info(f"Updated tool bindings for agent {agent_id}: {new_tool_ids}")

            if agent_def.mcp_server_ids != new_mcp_server_ids:
                agent_def.mcp_server_ids = new_mcp_server_ids
                updated = True
                logger.info(
                    f"Updated MCP server bindings for agent {agent_id}: {new_mcp_server_ids}"
                )

            if updated:
                agent_def.updated_at = datetime.now()
                result.updated_agent_ids.append(agent_id)

    def _compile_skill_bindings(self, result: CompilationResult) -> None:
        """
        编译技能绑定

        从前端 Agent 节点的 selectedSkillKeys 同步到 AgentDefinition.loadout_data.skill_keys
        """
        for agent_node in self.agent_nodes:
            agent_id = agent_node.data.get("agent_id") or agent_node.data.get("agentId")
            if not agent_id:
                continue

            agent_def = self.session.get(AgentDefinition, agent_id)
            if not agent_def:
                continue

            selected_skill_keys = agent_node.data.get("selectedSkillKeys") or []
            if isinstance(selected_skill_keys, (str, int)):
                selected_skill_keys = [str(selected_skill_keys)]
            if not isinstance(selected_skill_keys, list):
                selected_skill_keys = []

            normalized_skill_keys: List[str] = []
            for key in selected_skill_keys:
                if key is None:
                    continue
                normalized_skill_keys.append(str(key))

            loadout_data = agent_def.loadout_data or {}
            if not isinstance(loadout_data, dict):
                loadout_data = {}

            current_skill_keys = loadout_data.get("skill_keys") or []
            if current_skill_keys != normalized_skill_keys:
                updated_loadout = dict(loadout_data)
                updated_loadout["skill_keys"] = normalized_skill_keys
                agent_def.loadout_data = updated_loadout
                try:
                    flag_modified(agent_def, "loadout_data")
                except Exception:
                    # When AgentDefinition is mocked in tests, it's not SQLAlchemy-instrumented.
                    pass
                agent_def.updated_at = datetime.now()
                result.updated_agent_ids.append(agent_id)
                logger.info(
                    f"Updated skill bindings for agent {agent_id}: {normalized_skill_keys}"
                )

    def _compile_start_node(self) -> Dict[str, Any]:
        """
        编译 Start 节点
        
        Returns:
            输入 schema (JSON Schema 格式)
        """
        if not self.start_node:
            return {}
        
        data = self.start_node.data
        variables = data.get("variables", [])
        
        # 构建 JSON Schema
        properties = {}
        required = []
        
        for var in variables:
            var_name = var.get("name", "")
            var_label = var.get("label", var_name)
            var_type = var.get("type", "text")
            var_options = var.get("options", [])
            
            if not var_name:
                continue
            
            prop = {
                "title": var_label,
                "description": var.get("description") or f"Input variable: {var_label}",
            }
            
            if var_type == "select" and var_options:
                prop["type"] = "string"
                prop["enum"] = var_options
            elif var_type == "number":
                prop["type"] = "number"
            else:
                prop["type"] = "string"
            
            properties[var_name] = prop
            required.append(var_name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }
    
    def _compile_agent_nodes(self, result: CompilationResult, sorted_nodes: List[CompiledNode]) -> None:
        """
        编译 Agent 节点

        为每个 Agent 节点生成或更新对应的 TaskDefinition
        """
        for node in sorted_nodes:
            if node.type != "agent":
                continue

            data = node.data
            agent_id = data.get("agent_id")

            # 如果没有 agent_id，说明是新 agent（从模板创建），尝试查找或创建 AgentDefinition
            if not agent_id:
                role = data.get("role", "")
                if role:
                    # 查找是否已存在同名 agent
                    existing_agent = self.session.query(AgentDefinition).filter(
                        AgentDefinition.user_id == self.user_id,
                        AgentDefinition.name == role
                    ).first()

                    if existing_agent:
                        agent_id = existing_agent.id
                        node.data["agent_id"] = agent_id
                        result.updated_agent_ids.append(agent_id)
                    else:
                        # 创建新的 AgentDefinition
                        new_agent = AgentDefinition(
                            user_id=self.user_id,
                            name=role,
                            role=role,
                            goal=data.get("goal", ""),
                            backstory=data.get("backstory", ""),
                            description=data.get("description") or f"Agent: {role}",
                            llm_config={"model": data.get("model", "gpt-4o")} if data.get("model") else None,
                            loadout_data=data.get("loadout_data"),
                            is_template=False,
                            is_active=True,
                        )
                        self.session.add(new_agent)
                        self.session.flush()
                        agent_id = new_agent.id
                        node.data["agent_id"] = agent_id
                        result.created_task_ids.append(-agent_id)  # Mark as created agent
                        logger.info(f"Created new agent {agent_id} for role '{role}'")
                else:
                    result.warnings.append(f"Agent node '{node.id}' has no role and no agent_id")
                    continue

            # 从节点数据提取任务信息
            task_description = data.get("taskDescription") or data.get("goal", "")
            expected_output = data.get("expectedOutput", "Provide a comprehensive analysis")
            
            if not task_description:
                result.warnings.append(f"Agent node '{node.id}' has no task description")
                continue
            
            # 计算上下文依赖 (上游 Agent 的 Task)
            context_task_ids = []
            for upstream_id in node.upstream_nodes:
                upstream_node = self.nodes.get(upstream_id)
                if upstream_node and upstream_node.type == "agent":
                    # 查找该上游 Agent 的 Task ID
                    upstream_task_id = upstream_node.data.get("task_id")
                    if upstream_task_id:
                        context_task_ids.append(upstream_task_id)
            
            # 检查是否已有关联的 Task
            existing_task_id = data.get("task_id")
            
            if existing_task_id:
                # 更新现有 Task
                task_def = self.session.get(TaskDefinition, existing_task_id)
                if task_def:
                    task_def.description = task_description
                    task_def.expected_output = expected_output
                    task_def.context_task_ids = context_task_ids if context_task_ids else None
                    task_def.updated_at = datetime.now()
                    logger.info(f"Updated task {existing_task_id} for agent node {node.id}")
            else:
                # 创建新 Task
                task_def = TaskDefinition(
                    user_id=self.user_id,
                    name=f"Task for {data.get('role', node.id)}",
                    description=task_description,
                    expected_output=expected_output,
                    agent_definition_id=agent_id,
                    context_task_ids=context_task_ids if context_task_ids else None,
                    async_execution=data.get("asyncExecution", False),
                )
                self.session.add(task_def)
                self.session.flush()  # 获取 ID
                
                # 更新节点数据中的 task_id
                node.data["task_id"] = task_def.id
                result.created_task_ids.append(task_def.id)
                logger.info(f"Created task {task_def.id} for agent node {node.id}")
    
    def _compile_router_nodes(self, result: CompilationResult, sorted_nodes: List[CompiledNode]) -> None:
        """
        编译 Router 节点
        
        将 Router 转换为决策 Task，使用 Prompt 注入方式实现分支控制
        """
        for node in sorted_nodes:
            if node.type != "router":
                continue
            
            data = node.data
            router_name = data.get("name", f"Router_{node.id}")
            instruction = data.get("instruction", "")
            routes = data.get("routes", [])
            default_route = data.get("defaultRouteId")
            router_model = data.get("routerModel", "gpt-4o")
            
            if not routes:
                result.warnings.append(f"Router '{router_name}' has no routes defined")
                continue
            
            # 构建决策 Task 的描述
            route_descriptions = []
            for route in routes:
                route_id = route.get("id", "")
                route_label = route.get("label", route_id)
                route_condition = route.get("condition", "")
                route_descriptions.append(f"- {route_label}: {route_condition}")
            
            graph_config = _get_graph_config()
            decision_prompt_tpl = graph_config.get(
                "decision_prompt_template",
                "Based on the previous analysis, determine which path to take.\n\nRouter Instruction: {instruction}\n\nAvailable Routes:\n{routes}\n\nDefault Route: {default_route}\n\nAnalyze the context and output ONLY the route label that should be taken.",
            )
            decision_prompt = decision_prompt_tpl.format(
                instruction=instruction,
                routes=chr(10).join(route_descriptions),
                default_route=default_route or 'None'
            )
            
            existing_task_id = data.get("decision_task_id") or _find_existing_router_task_id(
                self.crew_def.structure, node.id
            )
            decision_task = (
                self.session.get(TaskDefinition, existing_task_id)
                if existing_task_id
                else None
            )

            if decision_task:
                decision_task.name = f"Decision: {router_name}"
                decision_task.description = decision_prompt
                decision_task.expected_output = "The selected route label"
                decision_task.updated_at = datetime.now()
            else:
                decision_task = TaskDefinition(
                    user_id=self.user_id,
                    name=f"Decision: {router_name}",
                    description=decision_prompt,
                    expected_output="The selected route label",
                    async_execution=False,
                )
                self.session.add(decision_task)
                self.session.flush()
                result.created_task_ids.append(decision_task.id)

            node.data["decision_task_id"] = decision_task.id
            
            # 记录路由任务信息
            result.router_tasks.append({
                "router_id": node.id,
                "decision_task_id": decision_task.id,
                "routes": routes,
                "default_route": default_route,
                "model": router_model,
            })
            
            # 为下游分支 Agent 注入条件前缀
            for edge in self.edges:
                if edge.source == node.id and edge.edge_type == "control":
                    target_node = self.nodes.get(edge.target)
                    if target_node and target_node.type == "agent":
                        # 找到对应的路由分支
                        route_label = edge.source_handle or "default"
                        
                        # Store router condition in node data (for structure generation)
                        # The actual description wrapping happens at runtime in Assembler
                        # to avoid polluting ui_state with injection text
                        target_node.data["routerCondition"] = route_label
            
            logger.info(f"Compiled router '{router_name}' with {len(routes)} routes")
    
    def _create_or_update_reporter_agent(
        self,
        summary_model: str,
        result: CompilationResult,
    ) -> int:
        """
        创建或更新隐式的 Reporter Agent

        Reporter Agent 是 End 节点专用的 Agent，负责将所有分析结果汇总成报告。
        它拥有专业的报告撰写人设和报告生成工具集。

        Args:
            summary_model: 汇总使用的模型 tier (如 "agents_fast")
            result: 编译结果，用于记录新创建的 Agent ID

        Returns:
            Reporter Agent 的 ID
        """
        reporter_config = _get_reporter_agent_config()

        # 尝试获取已存在的 Reporter Agent
        existing_agent_id = self.end_node.data.get("reporter_agent_id")

        if existing_agent_id:
            agent = self.session.get(AgentDefinition, existing_agent_id)
            if agent:
                # 更新现有 Agent
                agent.role = reporter_config.get("role", "Financial Report Specialist")
                agent.goal = reporter_config.get("goal", "Synthesize financial analyses into clear reports.")
                agent.backstory = reporter_config.get("backstory", "Expert financial report writer.")
                agent.llm_config = {"llm_tier": summary_model}
                agent.loadout_data = {"skill_keys": reporter_config.get("default_skill_keys", [])}
                agent.updated_at = datetime.now()

                logger.info(f"Updated existing Reporter Agent {agent.id}")
                return agent.id

        # 创建新的 Reporter Agent
        agent = AgentDefinition(
            user_id=self.user_id,
            name=f"Reporter_{self.crew_def.id}",
            role=reporter_config.get("role", "Financial Report Specialist"),
            goal=reporter_config.get("goal", "Synthesize financial analyses into clear reports."),
            backstory=reporter_config.get("backstory", "Expert financial report writer."),
            llm_config={"llm_tier": summary_model},
            loadout_data={"skill_keys": reporter_config.get("default_skill_keys", [])},
            verbose=True,
            allow_delegation=False,
            is_template=False,
            is_active=True,
        )
        self.session.add(agent)
        self.session.flush()

        # 记录到 End 节点 data 和编译结果
        self.end_node.data["reporter_agent_id"] = agent.id
        result.created_agent_ids.append(agent.id)

        logger.info(f"Created Reporter Agent {agent.id} for End node")
        return agent.id

    def _compile_end_node(self, result: CompilationResult) -> Dict[str, Any]:
        """
        编译 End 节点

        如果配置了汇总模型，生成最终汇总 Task 和专属的 Reporter Agent

        Returns:
            输出配置
        """
        if not self.end_node:
            return {}

        data = self.end_node.data
        output_format = data.get("outputFormat", "Markdown")
        aggregation_method = data.get("aggregationMethod", "concatenate")
        summary_model = data.get("summaryModel")

        output_config = {
            "format": output_format,
            "aggregation": aggregation_method,
            "summary_model": summary_model,
        }

        # 如果需要 LLM 汇总，创建汇总 Task 和 Reporter Agent
        if aggregation_method == "llm_summary" and summary_model:
            # 1. 创建/更新 Reporter Agent
            reporter_agent_id = self._create_or_update_reporter_agent(summary_model, result)
            output_config["reporter_agent_id"] = reporter_agent_id

            # 2. 创建/更新 Summary Task
            graph_config = _get_graph_config()
            summary_prompt_tpl = graph_config.get(
                "summary_prompt_template",
                "Synthesize all the previous analysis results into a comprehensive final report.\n\nOutput Format: {output_format}\n\nRequirements:\n1. Integrate insights from all previous tasks\n2. Highlight key findings and recommendations\n3. Ensure the output is well-structured and professional\n4. Format the output as {output_format}",
            )
            summary_prompt = summary_prompt_tpl.format(output_format=output_format)

            existing_summary_task_id = (
                data.get("summary_task_id")
                or _find_existing_summary_task_id_from_router_config(self.crew_def.router_config)
                or _find_existing_summary_task_id(self.crew_def.structure)
            )
            summary_task = (
                self.session.get(TaskDefinition, existing_summary_task_id)
                if existing_summary_task_id
                else None
            )

            if summary_task:
                summary_task.name = "Final Summary Report"
                summary_task.description = summary_prompt
                summary_task.expected_output = (
                    f"A comprehensive {output_format} report synthesizing all analysis"
                )
                summary_task.updated_at = datetime.now()

                self.end_node.data["summary_task_id"] = summary_task.id
                output_config["summary_task_id"] = summary_task.id
            else:
                summary_task = TaskDefinition(
                    user_id=self.user_id,
                    name="Final Summary Report",
                    description=summary_prompt,
                    expected_output=f"A comprehensive {output_format} report synthesizing all analysis",
                    async_execution=False,
                )
                self.session.add(summary_task)
                self.session.flush()

                self.end_node.data["summary_task_id"] = summary_task.id
                output_config["summary_task_id"] = summary_task.id
                result.created_task_ids.append(summary_task.id)

                logger.info(f"Created summary task {summary_task.id} for End node")

        return output_config
    
    def _generate_structure(self, sorted_nodes: List[CompiledNode]) -> List[Dict[str, Any]]:
        """
        生成最终的可执行 structure
        
        Returns:
            [{agent_id, tasks: [task_ids], knowledge_source_ids, ...}, ...]
        """
        structure = []
        
        for node in sorted_nodes:
            if node.type == "agent":
                agent_id = node.data.get("agent_id")
                task_id = node.data.get("task_id")
                
                if not agent_id:
                    continue
                
                entry = {
                    "agent_id": agent_id,
                    "tasks": [task_id] if task_id else [],
                    "knowledge_source_ids": node.knowledge_sources,
                    "order": node.order,
                }
                
                # 添加路由条件 (如果有)
                if "routerCondition" in node.data:
                    entry["router_condition"] = node.data["routerCondition"]
                
                structure.append(entry)
            
            elif node.type == "router":
                # Router 作为特殊的决策节点
                decision_task_id = node.data.get("decision_task_id")
                if decision_task_id:
                    structure.append({
                        "type": "router",
                        "router_id": node.id,
                        "decision_task_id": decision_task_id,
                        "routes": node.data.get("routes", []),
                        "default_route": node.data.get("defaultRouteId"),
                        "order": node.order,
                    })
        
        # 添加汇总 Task (如果有)
        if self.end_node:
            summary_task_id = self.end_node.data.get("summary_task_id")
            reporter_agent_id = self.end_node.data.get("reporter_agent_id")
            if summary_task_id:
                summary_entry = {
                    "type": "summary",
                    "task_id": summary_task_id,
                    "order": len(sorted_nodes),
                }
                # 添加 Reporter Agent ID (如果存在)
                if reporter_agent_id:
                    summary_entry["reporter_agent_id"] = reporter_agent_id
                structure.append(summary_entry)
        
        # 按 order 排序
        structure.sort(key=lambda x: x.get("order", 0))
        
        return structure


def compile_crew_graph(
    session: Session,
    user_id: int,
    crew_def: CrewDefinition,
) -> CompilationResult:
    """
    编译 Crew 图的便捷函数
    
    Args:
        session: 数据库会话
        user_id: 用户 ID
        crew_def: Crew 定义
    
    Returns:
        CompilationResult: 编译结果
    """
    compiler = GraphCompiler(session, user_id, crew_def)
    return compiler.compile()
