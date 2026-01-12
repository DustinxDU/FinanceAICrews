"""
Crew Version Manager - 负责 Crew 版本控制
"""
from AICrews.observability.logging import get_logger
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from AICrews.database.models import CrewDefinition, CrewVersion

logger = get_logger(__name__)

class CrewVersionManager:
    """Crew 版本管理器"""
    
    def save_version(
        self,
        session,
        crew_id: int,
        description: Optional[str] = None,
    ) -> CrewVersion:
        """保存 Crew 配置版本"""
        crew_def = session.get(CrewDefinition, crew_id)
        if not crew_def:
            raise ValueError(f"Crew not found: {crew_id}")
        
        # 获取当前最大版本号
        max_version = session.query(func.max(CrewVersion.version_number)).filter(
            CrewVersion.crew_id == crew_id,
        ).scalar() or 0
        
        # 创建快照
        snapshot = {
            "name": crew_def.name,
            "description": crew_def.description,
            "process": crew_def.process,
            "structure": crew_def.structure,
            "ui_state": crew_def.ui_state,
            "input_schema": crew_def.input_schema,
            "router_config": crew_def.router_config,
            "memory_enabled": crew_def.memory_enabled,
            "cache_enabled": crew_def.cache_enabled,
            "verbose": crew_def.verbose,
            "default_variables": crew_def.default_variables,
        }
        
        version = CrewVersion(
            crew_id=crew_id,
            version_number=max_version + 1,
            structure_snapshot=snapshot,
            description=description,
        )
        
        session.add(version)
        session.commit()
        session.refresh(version)
        
        logger.info(f"Saved version {version.version_number} for crew {crew_id}")
        
        return version

    def restore_version(
        self,
        session,
        crew_id: int,
        version_number: int,
    ) -> CrewDefinition:
        """恢复到指定版本"""
        version = session.query(CrewVersion).filter(
            CrewVersion.crew_id == crew_id,
            CrewVersion.version_number == version_number,
        ).first()
        
        if not version:
            raise ValueError(f"Version {version_number} not found for crew {crew_id}")
        
        crew_def = session.get(CrewDefinition, crew_id)
        if not crew_def:
            raise ValueError(f"Crew not found: {crew_id}")
        
        # 恢复快照
        snapshot = version.structure_snapshot or {}
        crew_def.name = snapshot.get("name", crew_def.name)
        crew_def.description = snapshot.get("description")
        crew_def.process = snapshot.get("process", "sequential")
        crew_def.structure = snapshot.get("structure", [])
        crew_def.ui_state = snapshot.get("ui_state")
        crew_def.input_schema = snapshot.get("input_schema")
        crew_def.router_config = snapshot.get("router_config")
        crew_def.memory_enabled = snapshot.get("memory_enabled", True)
        crew_def.cache_enabled = snapshot.get("cache_enabled", True)
        crew_def.verbose = snapshot.get("verbose", True)
        crew_def.default_variables = snapshot.get("default_variables")
        crew_def.updated_at = datetime.now()
        
        session.commit()
        session.refresh(crew_def)
        
        logger.info(f"Restored crew {crew_id} to version {version_number}")
        
        return crew_def

    def list_versions(self, session, crew_id: int) -> List[Dict[str, Any]]:
        """列出所有版本"""
        versions = session.query(CrewVersion).filter(
            CrewVersion.crew_id == crew_id,
        ).order_by(CrewVersion.version_number.desc()).all()
        
        return [
            {
                "version_number": v.version_number,
                "description": v.description,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]

    def clone_crew(
        self,
        session,
        crew_id: int,
        user_id: int,
        new_name: Optional[str] = None,
    ) -> CrewDefinition:
        """克隆 Crew 配置"""
        source = session.get(CrewDefinition, crew_id)
        if not source:
            raise ValueError(f"Crew not found: {crew_id}")
        
        # 创建新的 Crew 定义
        new_crew = CrewDefinition(
            user_id=user_id,
            name=new_name or f"{source.name} (Clone)",
            description=source.description,
            process=source.process,
            manager_llm_config=source.manager_llm_config,
            structure=source.structure.copy() if source.structure else [],
            ui_state=source.ui_state.copy() if source.ui_state else None,
            input_schema=source.input_schema.copy() if source.input_schema else None,
            router_config=source.router_config.copy() if source.router_config else None,
            memory_enabled=source.memory_enabled,
            cache_enabled=source.cache_enabled,
            verbose=source.verbose,
            is_template=False,
            is_active=True,
            default_variables=source.default_variables,
        )
        
        session.add(new_crew)
        session.commit()
        session.refresh(new_crew)
        
        logger.info(f"Cloned crew {crew_id} to new crew {new_crew.id}")
        
        return new_crew
