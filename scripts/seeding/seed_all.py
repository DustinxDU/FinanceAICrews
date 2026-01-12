#!/usr/bin/env python3
"""
统一种子数据初始化脚本

用法:
    python scripts/seed_all.py [--llm] [--mcp] [--knowledge] [--crews] [--all]

说明:
    此脚本合并了所有种子数据初始化功能，替代原来分散的脚本：
    - init_llm_database.py → --llm
    - init_mcp_database.py → --mcp  
    - seed_knowledge_sources.py → --knowledge
    - init_crews.py → --crews
    
前置条件:
    1. 数据库已通过 alembic upgrade head 建表
    2. .env 配置正确
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import Session
from AICrews.database.db_manager import DBManager


def seed_llm_providers(session: Session) -> int:
    """初始化 LLM 提供商和模型"""
    from AICrews.database.models import LLMProvider, LLMModel
    from AICrews.llm.unified_manager import get_unified_llm_manager
    
    print("🚀 初始化 LLM 提供商和模型...")
    
    manager = get_unified_llm_manager()
    providers_data = manager.get_all_providers()
    
    provider_count = 0
    model_count = 0
    
    for provider_info in providers_data:
        existing = session.query(LLMProvider).filter(
            LLMProvider.provider_key == provider_info["provider_key"]
        ).first()
        
        if existing:
            existing.display_name = provider_info["display_name"]
            existing.provider_type = provider_info["provider_type"]
            existing.requires_api_key = provider_info["requires_api_key"]
            existing.requires_base_url = provider_info["requires_base_url"]
            existing.requires_custom_model_name = provider_info["requires_custom_model_name"]
            existing.default_base_url = provider_info.get("default_base_url")
            existing.updated_at = datetime.now()
            provider = existing
        else:
            provider = LLMProvider(
                provider_key=provider_info["provider_key"],
                display_name=provider_info["display_name"],
                provider_type=provider_info["provider_type"],
                requires_api_key=provider_info["requires_api_key"],
                requires_base_url=provider_info["requires_base_url"],
                requires_custom_model_name=provider_info["requires_custom_model_name"],
                default_base_url=provider_info.get("default_base_url"),
                sort_order=provider_count
            )
            session.add(provider)
            provider_count += 1
        
        session.flush()
        
        # 初始化该提供商的模型
        models_data = manager.get_provider_models(provider_info["provider_key"])
        for model_info in models_data:
            existing_model = session.query(LLMModel).filter(
                LLMModel.provider_id == provider.id,
                LLMModel.model_key == model_info["model_key"]
            ).first()
            
            if not existing_model:
                new_model = LLMModel(
                    provider_id=provider.id,
                    model_key=model_info["model_key"],
                    display_name=model_info["display_name"],
                    context_length=model_info.get("context_length"),
                    supports_tools=model_info.get("supports_tools", False),
                    supports_vision=model_info.get("supports_vision", False),
                    supports_streaming=True,
                    recommended_for=model_info.get("recommended_for"),
                    model_category="general",
                    is_active=True,
                    sort_order=model_count,
                    last_updated_from_api=datetime.now()
                )
                if provider_info["provider_key"] == "volcengine":
                    new_model.volcengine_endpoint_template = "ep-{endpoint_id}"
                session.add(new_model)
                model_count += 1
    
    session.commit()
    print(f"  ✅ LLM: {provider_count} 个提供商, {model_count} 个模型")
    return provider_count + model_count


def seed_mcp_servers(session: Session) -> int:
    """初始化 MCP 服务器和工具"""
    import os
    from AICrews.database.models import MCPServer, MCPTool
    
    print("🔧 初始化 MCP 服务器...")
    
    # 检查是否已初始化
    existing = session.query(MCPServer).count()
    if existing > 0:
        print(f"  ⚠️ 已存在 {existing} 个 MCP 服务器，跳过")
        return 0
    
    servers = [
        MCPServer(
            server_key="openbb",
            display_name="OpenBB Platform",
            description="OpenBB Platform MCP 服务器，提供 170+ 金融数据工具。覆盖股票、期权、外汇、加密货币、宏观经济等数据。",
            transport_type="http_sse",
            url=os.getenv("OPENBB_MCP_URL", "http://localhost:8008/mcp"),
            requires_auth=True,
            auth_type="api_key",
            default_api_key_env="OPENBB_TOKEN",
            provider="openbb",
            is_system=True,
            is_active=True,
            icon="📈",
            documentation_url="https://docs.openbb.co/platform",
            sort_order=1,
        ),
        MCPServer(
            server_key="akshare",
            display_name="Akshare 中国市场数据",
            description="基于 Akshare 的中国市场数据服务。提供 A股、港股历史行情、实时行情、财务报表、宏观经济数据等。免费且无需 API Key。",
            transport_type="http_sse",
            url=os.getenv("AKSHARE_MCP_URL", "http://localhost:8009/sse"),
            requires_auth=False,
            provider="akshare",
            is_system=True,
            is_active=True,
            icon="🇨🇳",
            documentation_url="https://akshare.akfamily.xyz/",
            sort_order=2,
        ),
    ]
    
    for server in servers:
        session.add(server)
    
    session.commit()
    print(f"  ✅ MCP: {len(servers)} 个服务器")
    return len(servers)


def seed_knowledge_sources(session: Session) -> int:
    """初始化知识源"""
    import yaml
    from AICrews.database.models import KnowledgeSource
    
    print("📚 初始化知识源...")
    
    config_path = project_root / "config" / "knowledge_sources.yaml"
    if not config_path.exists():
        print(f"  ⚠️ 配置文件不存在: {config_path}")
        return 0
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    
    created = 0
    for source_key, source_data in config.items():
        if not isinstance(source_data, dict):
            continue
        
        existing = session.query(KnowledgeSource).filter(
            KnowledgeSource.source_key == source_key
        ).first()
        
        if existing:
            continue
        
        new_source = KnowledgeSource(
            source_key=source_key,
            display_name=source_data.get("display_name", source_key),
            description=source_data.get("description"),
            source_type=source_data.get("source_type", "file"),
            file_path=source_data.get("file_path"),
            category=source_data.get("category", "general"),
            knowledge_scope=source_data.get("scope", "both"),
            scope="system",
            tags=source_data.get("tags"),
            icon=source_data.get("icon"),
            author=source_data.get("author"),
            version=source_data.get("version", "1.0.0"),
            is_system=True,
            is_free=source_data.get("is_free", True),
            is_active=True,
        )
        session.add(new_source)
        created += 1
    
    session.commit()
    print(f"  ✅ 知识源: {created} 个")
    return created


class SeedGraphGenerator:
    """将逻辑配置 (YAML) 转换为带有坐标的 UI State (React Flow JSON)"""
    
    LEGACY_TASK_KEY_MAP = {
        "fundamental_analysis": "fundamental_analysis_task",
        "technical_analysis": "technical_analysis_task",
        "sentiment_analysis": "sentiment_analysis_task",
        "bull_research": "bull_research_task",
        "bear_research": "bear_research_task",
        "debate_synthesis": "debate_synthesis_task",
        "trading_plan": "trading_plan_task",
        "risk_assessment": "risk_assessment_task",
    }
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.nodes = []
        self.edges = []
        self.x_offset = 100
        self.y_baseline = 300
        self.node_spacing = 400
        self.node_cnt = 0

    def generate(self, crew_key: str, crew_config: dict, agents_lookup: dict, tasks_lookup: dict) -> dict:
        self.reset()
        
        # 1. 创建 Start 节点
        start_id = "node_start"
        input_schema = crew_config.get("input_schema", {})
        variables = []
        
        if isinstance(input_schema, dict) and "properties" in input_schema:
            for key, prop in input_schema.get("properties", {}).items():
                variables.append({"name": key, "label": prop.get("title", key), "type": prop.get("type", "text")})
        elif isinstance(input_schema, list):
            for item in input_schema:
                if isinstance(item, dict):
                    variables.append({"name": item.get("name", ""), "label": item.get("label", ""), "type": item.get("type", "text")})
        
        var_names = [v["name"] for v in variables]
        if "ticker" not in var_names:
            variables.insert(0, {"name": "ticker", "label": "Stock Ticker", "type": "text"})
        if "date" not in var_names:
            variables.append({"name": "date", "label": "Analysis Date", "type": "text"})
        
        self._add_node(start_id, "start", "Start", self.x_offset, self.y_baseline, {"inputMode": "custom", "variables": variables, "input_schema": input_schema})
        previous_node_id = start_id
        
        # 2. 遍历 Structure 创建 Agent 节点
        for step in crew_config.get("structure", []):
            agent_key = step.get("agent")
            task_keys = step.get("tasks", [])
            agent_data = agents_lookup.get(agent_key, {})
            first_task_key = task_keys[0] if task_keys else None
            resolved_task_key = first_task_key if first_task_key in tasks_lookup else self.LEGACY_TASK_KEY_MAP.get(first_task_key, first_task_key)
            task_data = tasks_lookup.get(resolved_task_key, {})
            
            self.node_cnt += 1
            node_id = f"node_agent_{self.node_cnt}_{agent_key}"
            self.x_offset += self.node_spacing
            
            self._add_node(node_id, "agent", agent_data.get("role", agent_key), self.x_offset, self.y_baseline, {
                "role": agent_data.get("role", "Agent"),
                "goal": agent_data.get("goal", ""),
                "backstory": agent_data.get("backstory", ""),
                "model": crew_config.get("manager_llm_config", {}).get("model", "gpt-4o"),
                "tools": agent_data.get("tools", []),
                "taskName": task_data.get("name", ""),
                "taskDescription": task_data.get("description", ""),
                "expectedOutput": task_data.get("expected_output", "")
            })
            self._add_edge(previous_node_id, node_id)
            previous_node_id = node_id
        
        # 3. 创建 End 节点
        end_id = "node_end"
        self.x_offset += self.node_spacing
        self._add_node(end_id, "end", "End", self.x_offset, self.y_baseline, {"output_format": "markdown"})
        self._add_edge(previous_node_id, end_id)
        
        return {"nodes": self.nodes, "edges": self.edges, "viewport": {"x": 0, "y": 0, "zoom": 0.8}}

    def _add_node(self, id, type, label, x, y, data):
        sizes = {"start": (288, 140), "agent": (288, 220), "router": (288, 160), "knowledge": (288, 120), "end": (192, 100)}
        w, h = sizes.get(type, (288, 160))
        self.nodes.append({"id": id, "type": type, "x": x, "y": y, "w": w, "h": h, "data": {**data, "label": label}})

    def _add_edge(self, source, target):
        self.edges.append({"from": source, "to": target, "type": "control"})


def seed_skills(session: Session) -> int:
    """初始化 Skills 系统 (providers + capabilities)"""
    from scripts.seed_skills_system import seed_builtin_providers, seed_capability_skills

    print("🎯 初始化 Skills 系统...")

    # Seed builtin providers (indicator_calc, strategy_eval)
    seed_builtin_providers(session)

    # Seed capability skills (cap:* entries)
    seed_capability_skills(session)

    # Count created skills
    from AICrews.database.models.skill import SkillCatalog
    skill_count = session.query(SkillCatalog).count()

    print(f"  ✅ Skills 系统初始化完成 ({skill_count} 个技能)")
    return skill_count


def seed_crews(session: Session) -> int:
    """初始化 Crew 定义 (完整版，包含 UI State 生成)"""
    import yaml
    from AICrews.database.models import User, AgentDefinition, TaskDefinition, CrewDefinition

    print("🤖 初始化 Crews...")

    config_dir = project_root / "config" / "agents"
    agents_path = config_dir / "agents.yaml"
    tasks_path = config_dir / "tasks.yaml"
    crews_path = config_dir / "crews.yaml"
    
    if not all(p.exists() for p in [agents_path, tasks_path, crews_path]):
        print("  ⚠️ 配置文件不完整，跳过")
        return 0
    
    with open(agents_path, "r", encoding="utf-8") as f:
        agents_config = yaml.safe_load(f) or {}
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks_config = yaml.safe_load(f) or {}
    with open(crews_path, "r", encoding="utf-8") as f:
        crews_config = yaml.safe_load(f) or {}
    
    # 确保 admin 用户存在
    admin_user = session.get(User, 1)
    if not admin_user:
        admin_user = User(
            id=1,
            email="admin@financeai.com",
            username="admin",
            password_hash="hashed_secret",
            subscription_level="enterprise",
            is_active=True,
            is_superuser=True,
        )
        session.add(admin_user)
        session.flush()
    
    graph_gen = SeedGraphGenerator()
    created = 0
    
    # Legacy task key mapping
    LEGACY_TASK_KEY_MAP = {
        "fundamental_analysis": "fundamental_analysis_task",
        "technical_analysis": "technical_analysis_task",
        "sentiment_analysis": "sentiment_analysis_task",
        "bull_research": "bull_research_task",
        "bear_research": "bear_research_task",
        "debate_synthesis": "debate_synthesis_task",
        "trading_plan": "trading_plan_task",
        "risk_assessment": "risk_assessment_task",
    }
    
    for crew_key, crew_data in crews_config.items():
        if not isinstance(crew_data, dict):
            continue
        
        crew_name = crew_data.get("name", crew_key)
        
        # 检查是否已存在
        existing_crew = session.query(CrewDefinition).filter_by(name=crew_name).first()
        if existing_crew:
            continue
        
        # 生成 UI State
        ui_state = graph_gen.generate(crew_key, crew_data, agents_config, tasks_config)
        
        # 创建 Agent 和 Task 定义，构建 structure
        db_structure = []
        created_agents_cache = {}
        
        for step in crew_data.get("structure", []):
            agent_key = step.get("agent")
            task_keys = step.get("tasks", [])
            
            if agent_key not in agents_config:
                continue
            
            agent_yaml = agents_config[agent_key]
            unique_agent_name = f"{crew_key}_{agent_key}"
            
            # 获取或创建 Agent
            if unique_agent_name in created_agents_cache:
                agent_def = created_agents_cache[unique_agent_name]
            else:
                existing_agent = session.query(AgentDefinition).filter_by(name=unique_agent_name).first()
                if existing_agent:
                    agent_def = existing_agent
                else:
                    # Build llm_config from agent's llm_tier (if present)
                    agent_llm_config = None
                    if agent_yaml.get("llm_tier"):
                        agent_llm_config = {"llm_tier": agent_yaml.get("llm_tier")}

                    agent_def = AgentDefinition(
                        user_id=admin_user.id,
                        name=unique_agent_name,
                        role=agent_yaml.get("role", agent_key),
                        goal=agent_yaml.get("goal", ""),
                        backstory=agent_yaml.get("backstory", ""),
                        llm_config=agent_llm_config,
                        tool_ids=[],
                        loadout_data=agent_yaml.get("loadout_data"),
                        is_template=True,
                        is_active=True
                    )
                    session.add(agent_def)
                    session.flush()
                    created += 1
                created_agents_cache[unique_agent_name] = agent_def
            
            # 创建 Task 定义
            db_task_ids = []
            for t_key in task_keys:
                resolved_key = t_key if t_key in tasks_config else LEGACY_TASK_KEY_MAP.get(t_key, t_key)
                if resolved_key not in tasks_config:
                    continue
                task_yaml = tasks_config[resolved_key]
                task_def = TaskDefinition(
                    user_id=admin_user.id,
                    name=task_yaml.get("name", resolved_key),
                    description=task_yaml.get("description", ""),
                    expected_output=task_yaml.get("expected_output", ""),
                    agent_definition_id=agent_def.id,
                    async_execution=task_yaml.get("async_execution", False)
                )
                session.add(task_def)
                session.flush()
                db_task_ids.append(task_def.id)
                created += 1
            
            db_structure.append({"agent_id": agent_def.id, "tasks": db_task_ids, "type": "agent"})
        
        # 创建 Crew 定义
        new_crew = CrewDefinition(
            user_id=admin_user.id,
            name=crew_name,
            description=crew_data.get("description", ""),
            process=crew_data.get("process", "sequential"),
            structure=db_structure,
            ui_state=ui_state,
            input_schema=crew_data.get("input_schema"),
            manager_llm_config=crew_data.get("manager_llm_config"),
            memory_enabled=crew_data.get("memory_enabled", True),
            verbose=crew_data.get("verbose", True),
            is_template=True,
            is_active=True
        )
        session.add(new_crew)
        created += 1
    
    session.commit()
    print(f"  ✅ Crews: {created} 个定义 (含 Agents/Tasks)")
    return created


def main():
    parser = argparse.ArgumentParser(
        description="统一种子数据初始化脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/seed_all.py --all          # 初始化所有种子数据
  python scripts/seed_all.py --llm --mcp    # 只初始化 LLM 和 MCP
        """
    )
    parser.add_argument("--llm", action="store_true", help="初始化 LLM 提供商和模型")
    parser.add_argument("--mcp", action="store_true", help="初始化 MCP 服务器")
    parser.add_argument("--knowledge", action="store_true", help="初始化知识源")
    parser.add_argument("--skills", action="store_true", help="初始化 Skills 系统 (providers + capabilities)")
    parser.add_argument("--crews", action="store_true", help="初始化 Crew 定义")
    parser.add_argument("--all", action="store_true", help="初始化所有种子数据")
    
    args = parser.parse_args()
    
    # 如果没有指定任何选项，默认 --all
    if not any([args.llm, args.mcp, args.knowledge, args.skills, args.crews, args.all]):
        args.all = True

    print("=" * 50)
    print("🌱 种子数据初始化")
    print("=" * 50)

    db_manager = DBManager()
    session = db_manager.get_session()

    try:
        total = 0

        if args.all or args.llm:
            total += seed_llm_providers(session)

        if args.all or args.mcp:
            total += seed_mcp_servers(session)

        if args.all or args.knowledge:
            total += seed_knowledge_sources(session)

        if args.all or args.skills:
            total += seed_skills(session)

        if args.all or args.crews:
            total += seed_crews(session)
        
        print("=" * 50)
        print(f"✅ 完成! 共创建/更新 {total} 条记录")
        print("=" * 50)
        
    except Exception as e:
        session.rollback()
        print(f"❌ 错误: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
