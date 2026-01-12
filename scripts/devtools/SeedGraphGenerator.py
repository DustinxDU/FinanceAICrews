import uuid

class SeedGraphGenerator:
    """
    将逻辑配置 (YAML/Dict) 转换为带有坐标的 UI State (React Flow JSON)
    用于系统初始化时的种子数据可视化
    """
    
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.x_offset = 100
        self.y_baseline = 300
        self.node_spacing = 350
    
    def generate(self, crew_config: dict, agents_config: dict, tasks_config: dict) -> dict:
        """
        核心生成方法
        :param crew_config: crews.yaml 的内容
        :param agents_config: agents.yaml 的内容
        :param tasks_config: tasks.yaml 的内容
        """
        
        # 1. 创建 Start 节点
        start_id = "node_start"
        self._add_node(
            id=start_id,
            type="start",
            label="Start",
            x=self.x_offset,
            y=self.y_baseline,
            data={"input_schema": crew_config.get("input_schema", {})}
        )
        previous_node_id = start_id
        
        # 2. 遍历 Structure 创建 Agent 节点
        structure = crew_config.get("structure", [])
        
        for index, step in enumerate(structure):
            # 获取 Agent 和 Task 的 key
            agent_key = step.get("agent")
            task_key = step.get("tasks", [])[0] if step.get("tasks") else None
            
            # 从 Config 字典中获取详细信息
            agent_data = agents_config.get(agent_key, {})
            task_data = tasks_config.get(task_key, {})
            
            # 生成 Agent 节点
            node_id = f"node_agent_{index}_{agent_key}"
            
            # 构建节点 Data (符合前端格式)
            node_data = {
                "role": agent_data.get("role", "Agent"),
                "goal": agent_data.get("goal", ""),
                "backstory": agent_data.get("backstory", ""),
                "model": "gpt-4o", # 默认值，或从 manager_llm_config 取
                "tools": agent_data.get("tools", []), # 这里需要转换为 Tool IDs
                # 将 Task 信息直接嵌入 Agent 节点 (简化版设计)
                "taskName": task_data.get("name", ""),
                "taskDescription": task_data.get("description", ""),
                "expectedOutput": task_data.get("expected_output", "")
            }
            
            self.x_offset += self.node_spacing
            self._add_node(
                id=node_id,
                type="agent",
                label=agent_data.get("role", "Agent"),
                x=self.x_offset,
                y=self.y_baseline,
                data=node_data
            )
            
            # 3. 创建连线 (上一个 -> 当前)
            self._add_edge(previous_node_id, node_id)
            previous_node_id = node_id
            
        # 4. 创建 End 节点
        end_id = "node_end"
        self.x_offset += self.node_spacing
        self._add_node(
            id=end_id,
            type="end",
            label="End",
            x=self.x_offset,
            y=self.y_baseline,
            data={"output_format": "markdown"}
        )
        self._add_edge(previous_node_id, end_id)
        
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "viewport": {"x": 0, "y": 0, "zoom": 1}
        }

    def _add_node(self, id, type, label, x, y, data):
        self.nodes.append({
            "id": id,
            "type": type,
            "position": {"x": x, "y": y},
            "data": {**data, "label": label} # Label 用于显示
        })

    def _add_edge(self, source, target):
        self.edges.append({
            "id": f"edge_{source}_{target}",
            "source": source,
            "target": target,
            "type": "smoothstep", # 优美的贝塞尔曲线
            "animated": True if source == "node_start" else False # Start 出来的线可以是动画的
        })