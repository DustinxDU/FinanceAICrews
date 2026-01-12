#!/usr/bin/env python3
"""
Seed Knowledge Sources - 从 config/knowledge_sources.yaml 导入知识源到数据库

Usage:
    python scripts/seed_knowledge_sources.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from sqlalchemy.orm import Session
from AICrews.database.db_manager import DBManager
from AICrews.database.models import KnowledgeSource


def validate_file_path(file_path: str) -> tuple[bool, str]:
    """验证知识源文件是否存在"""
    if not file_path:
        return True, ""  # 非文件类型，跳过验证
    
    full_path = project_root / file_path
    if full_path.exists():
        return True, str(full_path)
    return False, str(full_path)


def load_yaml_config() -> dict:
    """加载 YAML 配置文件"""
    config_path = project_root / "config" / "knowledge_sources.yaml"
    if not config_path.exists():
        print(f"配置文件不存在: {config_path}")
        return {}
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def seed_knowledge_sources():
    """导入知识源到数据库"""
    config = load_yaml_config()
    if not config:
        print("没有找到知识源配置")
        return
    
    db_manager = DBManager()
    session: Session = db_manager.get_session()
    
    try:
        created = 0
        updated = 0
        
        missing_files = []
        
        for source_key, source_data in config.items():
            # 跳过非字典项（如注释）
            if not isinstance(source_data, dict):
                continue
            
            # 验证文件路径
            file_path = source_data.get("file_path")
            if source_data.get("source_type") == "file" and file_path:
                exists, full_path = validate_file_path(file_path)
                if not exists:
                    missing_files.append((source_key, full_path))
                    print(f"⚠️  警告: {source_key} 的文件不存在: {full_path}")
            
            # 查找现有记录
            existing = session.query(KnowledgeSource).filter(
                KnowledgeSource.source_key == source_key
            ).first()
            
            if existing:
                # 更新现有记录
                existing.display_name = source_data.get("display_name", source_key)
                existing.description = source_data.get("description")
                existing.source_type = source_data.get("source_type", "file")
                existing.file_path = source_data.get("file_path")
                existing.category = source_data.get("category", "general")
                existing.knowledge_scope = source_data.get("scope", "both")  # YAML 中的 scope 对应数据库的 knowledge_scope
                existing.scope = "system"  # 种子数据默认是系统级
                existing.tags = source_data.get("tags")
                existing.icon = source_data.get("icon")
                existing.author = source_data.get("author")
                existing.version = source_data.get("version", "1.0.0")
                existing.is_free = source_data.get("is_free", True)
                updated += 1
                print(f"更新: {source_key}")
            else:
                # 创建新记录
                new_source = KnowledgeSource(
                    source_key=source_key,
                    display_name=source_data.get("display_name", source_key),
                    description=source_data.get("description"),
                    source_type=source_data.get("source_type", "file"),
                    file_path=source_data.get("file_path"),
                    category=source_data.get("category", "general"),
                    knowledge_scope=source_data.get("scope", "both"),  # YAML 中的 scope 对应数据库的 knowledge_scope
                    scope="system",  # 种子数据默认是系统级
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
                print(f"创建: {source_key}")
        
        session.commit()
        print(f"\n完成! 创建: {created}, 更新: {updated}")
        
        if missing_files:
            print(f"\n⚠️  {len(missing_files)} 个知识源文件缺失:")
            for key, path in missing_files:
                print(f"   - {key}: {path}")
        
    except Exception as e:
        session.rollback()
        print(f"错误: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_knowledge_sources()
