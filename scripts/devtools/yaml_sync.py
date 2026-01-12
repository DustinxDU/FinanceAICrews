#!/usr/bin/env python3
"""
YAML 模板同步工具 - yaml_sync CLI

将 YAML 配置发布到数据库模板目录，供用户浏览和导入。

Usage:
    # 发布所有模板到数据库
    python scripts/yaml_sync.py publish --config-dir config
    
    # 预览（不实际写入）
    python scripts/yaml_sync.py publish --config-dir config --dry-run
    
    # 查看模板差异
    python scripts/yaml_sync.py diff --template-key fundamental_analyst --template-type agent
    
    # 列出已发布模板
    python scripts/yaml_sync.py list

Exit Codes:
    0: Success
    1: Error
"""

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# 确保项目根目录在 Python 路径中
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from AICrews.database.db_manager import DBManager
from AICrews.database.models import TemplateCatalog, TemplateImportLog, TemplateUpdateNotification

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def compute_checksum(payload: dict) -> str:
    """计算 payload 的 SHA256 校验和"""
    content = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def load_yaml_file(path: Path) -> Dict[str, Any]:
    """加载 YAML 文件"""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def get_display_name(key: str, config: dict) -> str:
    """从配置中获取展示名称"""
    return config.get("role") or config.get("name") or key.replace("_", " ").title()


def get_description(config: dict) -> Optional[str]:
    """从配置中获取描述"""
    return config.get("description") or config.get("backstory", "")[:200] if config.get("backstory") else None


def get_category(key: str, config: dict) -> str:
    """推断模板分类"""
    key_lower = key.lower()
    if any(x in key_lower for x in ["analyst", "analysis"]):
        return "analysis"
    elif any(x in key_lower for x in ["research", "bull", "bear", "debate"]):
        return "research"
    elif any(x in key_lower for x in ["trader", "trading", "risk"]):
        return "execution"
    elif any(x in key_lower for x in ["china", "hk", "hong_kong"]):
        return "regional"
    elif any(x in key_lower for x in ["buffett", "dalio", "soros", "quant"]):
        return "style"
    return "general"


def publish_agents(
    session: Session,
    config_dir: Path,
    dry_run: bool = False,
    version: str = "1.0.0",
    published_by: Optional[str] = None,
) -> Tuple[int, int, int]:
    """发布 agents.yaml 中的 Agent 模板"""
    agents_file = config_dir / "agents.yaml"
    if not agents_file.exists():
        logger.warning(f"agents.yaml not found: {agents_file}")
        return 0, 0, 0
    
    agents_config = load_yaml_file(agents_file)
    created, updated, skipped = 0, 0, 0
    
    for agent_key, agent_config in agents_config.items():
        payload = {"key": agent_key, **agent_config}
        checksum = compute_checksum(payload)
        
        # 查找现有模板
        existing = session.query(TemplateCatalog).filter_by(
            template_key=agent_key,
            template_type="agent",
            version=version
        ).first()
        
        if existing:
            if existing.checksum == checksum:
                skipped += 1
                logger.debug(f"Agent '{agent_key}' unchanged, skipping")
                continue
            
            # 更新现有模板
            if not dry_run:
                existing.payload = payload
                existing.checksum = checksum
                existing.display_name = get_display_name(agent_key, agent_config)
                existing.description = get_description(agent_config)
                existing.category = get_category(agent_key, agent_config)
                existing.source_file = "agents.yaml"
                existing.updated_at = datetime.now()
                
                # 创建更新通知
                _notify_template_update(session, existing, version)
            
            updated += 1
            logger.info(f"Updated agent template: {agent_key}")
        else:
            # 创建新模板
            if not dry_run:
                template = TemplateCatalog(
                    template_key=agent_key,
                    template_type="agent",
                    version=version,
                    display_name=get_display_name(agent_key, agent_config),
                    description=get_description(agent_config),
                    category=get_category(agent_key, agent_config),
                    payload=payload,
                    checksum=checksum,
                    source_file="agents.yaml",
                    published_by=published_by,
                )
                session.add(template)
            
            created += 1
            logger.info(f"Created agent template: {agent_key}")
    
    return created, updated, skipped


def publish_tasks(
    session: Session,
    config_dir: Path,
    dry_run: bool = False,
    version: str = "1.0.0",
    published_by: Optional[str] = None,
) -> Tuple[int, int, int]:
    """发布 tasks.yaml 中的 Task 模板"""
    tasks_file = config_dir / "tasks.yaml"
    if not tasks_file.exists():
        logger.warning(f"tasks.yaml not found: {tasks_file}")
        return 0, 0, 0
    
    tasks_config = load_yaml_file(tasks_file)
    created, updated, skipped = 0, 0, 0
    
    for task_key, task_config in tasks_config.items():
        payload = {"key": task_key, **task_config}
        checksum = compute_checksum(payload)
        
        existing = session.query(TemplateCatalog).filter_by(
            template_key=task_key,
            template_type="task",
            version=version
        ).first()
        
        if existing:
            if existing.checksum == checksum:
                skipped += 1
                continue
            
            if not dry_run:
                existing.payload = payload
                existing.checksum = checksum
                existing.display_name = task_key.replace("_", " ").title()
                existing.description = task_config.get("description", "")[:200]
                existing.category = get_category(task_key, task_config)
                existing.source_file = "tasks.yaml"
                existing.updated_at = datetime.now()
                _notify_template_update(session, existing, version)
            
            updated += 1
            logger.info(f"Updated task template: {task_key}")
        else:
            if not dry_run:
                template = TemplateCatalog(
                    template_key=task_key,
                    template_type="task",
                    version=version,
                    display_name=task_key.replace("_", " ").title(),
                    description=task_config.get("description", "")[:200],
                    category=get_category(task_key, task_config),
                    payload=payload,
                    checksum=checksum,
                    source_file="tasks.yaml",
                    published_by=published_by,
                )
                session.add(template)
            
            created += 1
            logger.info(f"Created task template: {task_key}")
    
    return created, updated, skipped


def publish_crews(
    session: Session,
    config_dir: Path,
    dry_run: bool = False,
    version: str = "1.0.0",
    published_by: Optional[str] = None,
) -> Tuple[int, int, int]:
    """发布 crews/*.yaml 中的 Crew 模板"""
    crews_dir = config_dir / "crews"
    if not crews_dir.exists():
        logger.warning(f"crews directory not found: {crews_dir}")
        return 0, 0, 0
    
    created, updated, skipped = 0, 0, 0
    
    for crew_file in crews_dir.glob("*.yaml"):
        crew_key = crew_file.stem
        crew_config = load_yaml_file(crew_file)
        
        if not crew_config:
            continue
        
        payload = {"key": crew_key, **crew_config}
        checksum = compute_checksum(payload)
        
        existing = session.query(TemplateCatalog).filter_by(
            template_key=crew_key,
            template_type="crew",
            version=version
        ).first()
        
        if existing:
            if existing.checksum == checksum:
                skipped += 1
                continue
            
            if not dry_run:
                existing.payload = payload
                existing.checksum = checksum
                existing.display_name = crew_config.get("name", crew_key.replace("_", " ").title())
                existing.description = crew_config.get("description")
                existing.source_file = f"crews/{crew_file.name}"
                existing.updated_at = datetime.now()
                _notify_template_update(session, existing, version)
            
            updated += 1
            logger.info(f"Updated crew template: {crew_key}")
        else:
            if not dry_run:
                template = TemplateCatalog(
                    template_key=crew_key,
                    template_type="crew",
                    version=version,
                    display_name=crew_config.get("name", crew_key.replace("_", " ").title()),
                    description=crew_config.get("description"),
                    category="crew",
                    payload=payload,
                    checksum=checksum,
                    source_file=f"crews/{crew_file.name}",
                    published_by=published_by,
                )
                session.add(template)
            
            created += 1
            logger.info(f"Created crew template: {crew_key}")
    
    return created, updated, skipped


def _notify_template_update(session: Session, template: TemplateCatalog, new_version: str) -> None:
    """为已导入该模板的用户创建更新通知"""
    import_logs = session.query(TemplateImportLog).filter_by(
        template_id=template.id
    ).all()
    
    for log in import_logs:
        if log.imported_version == new_version:
            continue
        
        existing_notification = session.query(TemplateUpdateNotification).filter_by(
            user_id=log.user_id,
            template_id=template.id,
            new_version=new_version,
            is_applied=False
        ).first()
        
        if not existing_notification:
            notification = TemplateUpdateNotification(
                user_id=log.user_id,
                template_id=template.id,
                import_log_id=log.id,
                old_version=log.imported_version,
                new_version=new_version,
            )
            session.add(notification)
            logger.debug(f"Created update notification for user {log.user_id}")


def cmd_publish(args) -> bool:
    """执行发布命令"""
    config_dir = Path(args.config_dir)
    if not config_dir.exists():
        logger.error(f"Config directory not found: {config_dir}")
        return False
    
    try:
        db = DBManager()
        session = db.get_session()
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return False
    
    try:
        logger.info("=" * 60)
        logger.info(f"Publishing templates from {config_dir}")
        logger.info(f"Version: {args.version}, Dry run: {args.dry_run}")
        logger.info("=" * 60)
        
        total_created, total_updated, total_skipped = 0, 0, 0
        
        # Publish agents
        c, u, s = publish_agents(session, config_dir, args.dry_run, args.version, args.published_by)
        total_created += c
        total_updated += u
        total_skipped += s
        
        # Publish tasks
        c, u, s = publish_tasks(session, config_dir, args.dry_run, args.version, args.published_by)
        total_created += c
        total_updated += u
        total_skipped += s
        
        # Publish crews
        c, u, s = publish_crews(session, config_dir, args.dry_run, args.version, args.published_by)
        total_created += c
        total_updated += u
        total_skipped += s
        
        if not args.dry_run:
            session.commit()
        
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Summary: Created={total_created}, Updated={total_updated}, Skipped={total_skipped}")
        if args.dry_run:
            logger.info("(Dry run - no changes made)")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Publish failed: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def cmd_list(args) -> bool:
    """列出已发布的模板"""
    try:
        db = DBManager()
        session = db.get_session()
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return False
    
    try:
        templates = session.query(TemplateCatalog).filter_by(is_active=True).order_by(
            TemplateCatalog.template_type,
            TemplateCatalog.template_key
        ).all()
        
        if not templates:
            logger.info("No templates found in catalog")
            return True
        
        logger.info(f"Found {len(templates)} templates:")
        logger.info("")
        
        current_type = None
        for t in templates:
            if t.template_type != current_type:
                current_type = t.template_type
                logger.info(f"--- {current_type.upper()}S ---")
            
            logger.info(f"  {t.template_key} (v{t.version}) - {t.display_name}")
            logger.info(f"    Category: {t.category}, Imports: {t.import_count}")
        
        return True
        
    finally:
        session.close()


def cmd_diff(args) -> bool:
    """显示模板差异"""
    try:
        db = DBManager()
        session = db.get_session()
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return False
    
    try:
        templates = session.query(TemplateCatalog).filter_by(
            template_key=args.template_key,
            template_type=args.template_type
        ).order_by(TemplateCatalog.version).all()
        
        if not templates:
            logger.info(f"No templates found for {args.template_type}/{args.template_key}")
            return True
        
        logger.info(f"Versions of {args.template_type}/{args.template_key}:")
        for t in templates:
            logger.info(f"  v{t.version} - checksum: {t.checksum[:16]}... (published: {t.published_at})")
        
        return True
        
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description="YAML Template Sync Tool"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # publish command
    publish_parser = subparsers.add_parser("publish", help="Publish YAML templates to database")
    publish_parser.add_argument(
        "--config-dir",
        default=str(project_root / "config"),
        help="Configuration directory path"
    )
    publish_parser.add_argument(
        "--version",
        default="1.0.0",
        help="Template version to publish"
    )
    publish_parser.add_argument(
        "--published-by",
        default="system",
        help="Publisher identifier"
    )
    publish_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to database"
    )
    
    # list command
    list_parser = subparsers.add_parser("list", help="List published templates")
    
    # diff command
    diff_parser = subparsers.add_parser("diff", help="Show template version differences")
    diff_parser.add_argument("--template-key", required=True, help="Template key")
    diff_parser.add_argument("--template-type", required=True, choices=["agent", "task", "crew"])
    
    args = parser.parse_args()
    
    if args.command == "publish":
        success = cmd_publish(args)
    elif args.command == "list":
        success = cmd_list(args)
    elif args.command == "diff":
        success = cmd_diff(args)
    else:
        parser.print_help()
        success = True
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
