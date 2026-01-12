from AICrews.observability.logging import get_logger
import copy
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from AICrews.database.models import (
    AgentDefinition,
    TaskDefinition,
    CrewDefinition,
    TemplateCatalog,
    TemplateImportLog,
    TemplateUpdateNotification,
)
from AICrews.schemas.template import (
    TemplateImportRequest,
    TemplateImportResponse,
    ApplyUpdateRequest,
    ApplyUpdateResponse,
    TemplateUpdateNotificationItem,
    MyImportItem,
    CategoryCount
)

logger = get_logger(__name__)

class TemplateService:
    def __init__(self, db: Session):
        self.db = db

    def list_templates(
        self,
        template_type: Optional[str] = None,
        category: Optional[str] = None,
        featured_only: bool = False,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TemplateCatalog]:
        """获取官方模板目录列表"""
        query = self.db.query(TemplateCatalog).filter(TemplateCatalog.is_active == True)
        
        if template_type:
            query = query.filter(TemplateCatalog.template_type == template_type)
        if category:
            query = query.filter(TemplateCatalog.category == category)
        if featured_only:
            query = query.filter(TemplateCatalog.is_featured == True)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (TemplateCatalog.display_name.ilike(search_pattern)) |
                (TemplateCatalog.description.ilike(search_pattern)) |
                (TemplateCatalog.template_key.ilike(search_pattern))
            )
        
        query = query.order_by(
            TemplateCatalog.is_featured.desc(),
            TemplateCatalog.sort_order,
            TemplateCatalog.template_type,
            TemplateCatalog.template_key
        )
        
        return query.offset(offset).limit(limit).all()

    def list_categories(self) -> List[CategoryCount]:
        """获取所有模板分类"""
        categories = self.db.query(
            TemplateCatalog.category,
            func.count(TemplateCatalog.id).label("count")
        ).filter(
            TemplateCatalog.is_active == True
        ).group_by(
            TemplateCatalog.category
        ).all()
        
        return [CategoryCount(category=c[0], count=c[1]) for c in categories]

    def get_template(self, template_id: int) -> Optional[TemplateCatalog]:
        """获取模板详情"""
        return self.db.query(TemplateCatalog).filter_by(id=template_id).first()

    def import_template(self, template_id: int, user_id: int, request: TemplateImportRequest) -> TemplateImportResponse:
        """导入模板到用户空间"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError("Template not found")
        
        payload = template.payload
        custom_name = request.custom_name or payload.get("key", template.template_key)
        
        # 根据模板类型创建对应的资源
        if template.template_type == "agent":
            resource = self._import_agent_template(user_id, payload, custom_name)
            resource_type = "agent"
            resource_id = resource.id
            resource_name = resource.name
            
        elif template.template_type == "task":
            resource = self._import_task_template(user_id, payload, custom_name)
            resource_type = "task"
            resource_id = resource.id
            resource_name = resource.name
            
        elif template.template_type == "crew":
            resource = self._import_crew_template(user_id, payload, custom_name)
            resource_type = "crew"
            resource_id = resource.id
            resource_name = resource.name
            
        else:
            raise ValueError(f"Unknown template type: {template.template_type}")
        
        # 记录导入日志
        import_log = TemplateImportLog(
            user_id=user_id,
            template_id=template_id,
            imported_resource_type=resource_type,
            imported_resource_id=resource_id,
            imported_version=template.version,
        )
        self.db.add(import_log)
        
        # 更新模板导入计数
        template.import_count += 1
        
        self.db.commit()
        
        logger.info(f"User {user_id} imported {resource_type} template '{template.template_key}' as '{resource_name}'")
        
        return TemplateImportResponse(
            success=True,
            message=f"Successfully imported {resource_type} template",
            imported_resource_type=resource_type,
            imported_resource_id=resource_id,
            imported_resource_name=resource_name,
        )

    def _import_agent_template(self, user_id: int, payload: Dict[str, Any], name: str) -> AgentDefinition:
        """导入 Agent 模板"""
        # 检查是否已存在同名资源
        existing = self.db.query(AgentDefinition).filter_by(user_id=user_id, name=name).first()
        if existing:
            # 添加后缀避免冲突
            name = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        agent = AgentDefinition(
            user_id=user_id,
            name=name,
            role=payload.get("role", name),
            goal=payload.get("goal", ""),
            backstory=payload.get("backstory", ""),
            description=payload.get("description"),
            verbose=payload.get("verbose", True),
            allow_delegation=payload.get("allow_delegation", False),
            tool_ids=None,  # 用户需要自行绑定工具
            is_template=False,
            is_active=True,
        )
        self.db.add(agent)
        self.db.flush()  # 获取 ID
        return agent

    def _import_task_template(self, user_id: int, payload: Dict[str, Any], name: str) -> TaskDefinition:
        """导入 Task 模板"""
        existing = self.db.query(TaskDefinition).filter_by(user_id=user_id, name=name).first()
        if existing:
            name = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        task = TaskDefinition(
            user_id=user_id,
            name=name,
            description=payload.get("description", ""),
            expected_output=payload.get("expected_output", ""),
            async_execution=payload.get("async_execution", False),
            context_task_ids=None,  # 用户需要自行设置上下文
        )
        self.db.add(task)
        self.db.flush()
        return task

    def _import_crew_template(self, user_id: int, payload: Dict[str, Any], name: str) -> CrewDefinition:
        """导入 Crew 模板"""
        existing = self.db.query(CrewDefinition).filter_by(user_id=user_id, name=name).first()
        if existing:
            name = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        crew = CrewDefinition(
            user_id=user_id,
            name=name,
            description=payload.get("description"),
            process=payload.get("execution", {}).get("process", "sequential"),
            structure=[],  # 用户需要自行构建结构
            memory_enabled=payload.get("execution", {}).get("memory", True),
            cache_enabled=True,
            verbose=payload.get("execution", {}).get("verbose", True),
            default_variables=payload.get("default_variables"),
            is_template=False,
            is_active=True,
        )
        self.db.add(crew)
        self.db.flush()
        return crew

    def get_update_notifications(self, user_id: int, unread_only: bool = True) -> List[TemplateUpdateNotificationItem]:
        """获取用户的模板更新通知"""
        query = self.db.query(TemplateUpdateNotification).filter_by(
            user_id=user_id,
            is_applied=False
        )
        
        if unread_only:
            query = query.filter(TemplateUpdateNotification.is_read == False)
        
        notifications = query.order_by(TemplateUpdateNotification.created_at.desc()).all()
        
        # 补充模板信息
        result = []
        for n in notifications:
            template = self.db.query(TemplateCatalog).filter_by(id=n.template_id).first()
            if template:
                result.append(TemplateUpdateNotificationItem(
                    id=n.id,
                    template_key=template.template_key,
                    template_type=template.template_type,
                    display_name=template.display_name,
                    old_version=n.old_version,
                    new_version=n.new_version,
                    changelog=n.changelog,
                    is_read=n.is_read,
                    created_at=n.created_at,
                ))
        return result

    def mark_notification_read(self, notification_id: int, user_id: int) -> bool:
        """标记通知为已读"""
        notification = self.db.query(TemplateUpdateNotification).filter_by(
            id=notification_id,
            user_id=user_id
        ).first()
        
        if not notification:
            return False
        
        notification.is_read = True
        self.db.commit()
        return True

    def apply_template_update(
        self, 
        notification_id: int, 
        user_id: int, 
        request: ApplyUpdateRequest
    ) -> ApplyUpdateResponse:
        """应用模板更新"""
        notification = self.db.query(TemplateUpdateNotification).filter_by(
            id=notification_id,
            user_id=user_id
        ).first()
        
        if not notification:
            raise ValueError("Notification not found")
        
        if notification.is_applied:
            raise ValueError("Update already applied")
        
        # 获取新版本模板
        template = self.db.query(TemplateCatalog).filter_by(
            id=notification.template_id
        ).first()
        
        if not template:
            raise ValueError("Template not found")
        
        # 获取导入日志和用户资源
        import_log = self.db.query(TemplateImportLog).filter_by(
            id=notification.import_log_id
        ).first()
        
        if not import_log:
            raise ValueError("Import log not found")
        
        # 根据合并策略更新用户资源
        if request.merge_strategy == "skip":
            # 跳过更新
            notification.is_applied = True
            notification.applied_at = datetime.now()
            self.db.commit()
            return ApplyUpdateResponse(
                success=True,
                message="Update skipped",
                updated_resource_id=import_log.imported_resource_id
            )
        
        # 执行更新
        payload = template.payload
        
        if template.template_type == "agent":
            resource = self.db.query(AgentDefinition).filter_by(
                id=import_log.imported_resource_id
            ).first()
            if resource:
                if request.merge_strategy == "replace":
                    resource.role = payload.get("role", resource.role)
                    resource.goal = payload.get("goal", resource.goal)
                    resource.backstory = payload.get("backstory", resource.backstory)
                resource.updated_at = datetime.now()
                
        elif template.template_type == "task":
            resource = self.db.query(TaskDefinition).filter_by(
                id=import_log.imported_resource_id
            ).first()
            if resource:
                if request.merge_strategy == "replace":
                    resource.description = payload.get("description", resource.description)
                    resource.expected_output = payload.get("expected_output", resource.expected_output)
                resource.updated_at = datetime.now()
                
        elif template.template_type == "crew":
            resource = self.db.query(CrewDefinition).filter_by(
                id=import_log.imported_resource_id
            ).first()
            if resource:
                if request.merge_strategy == "replace":
                    resource.description = payload.get("description", resource.description)
                resource.updated_at = datetime.now()
        
        # 更新通知状态
        notification.is_applied = True
        notification.applied_at = datetime.now()
        
        # 更新导入日志版本
        import_log.imported_version = notification.new_version
        
        self.db.commit()
        
        return ApplyUpdateResponse(
            success=True,
            message=f"Update applied with {request.merge_strategy} strategy",
            updated_resource_id=import_log.imported_resource_id
        )

    def list_my_imports(self, user_id: int, template_type: Optional[str] = None) -> List[MyImportItem]:
        """获取用户已导入的模板列表"""
        query = self.db.query(TemplateImportLog).filter_by(user_id=user_id)
        
        if template_type:
            query = query.filter(TemplateImportLog.imported_resource_type == template_type)
        
        imports = query.order_by(TemplateImportLog.imported_at.desc()).all()
        
        result = []
        for imp in imports:
            template = self.db.query(TemplateCatalog).filter_by(id=imp.template_id).first()
            if template:
                # 检查是否有更新
                has_update = self.db.query(TemplateUpdateNotification).filter_by(
                    import_log_id=imp.id,
                    is_applied=False
                ).first() is not None
                
                result.append(MyImportItem(
                    import_id=imp.id,
                    template_key=template.template_key,
                    template_type=template.template_type,
                    display_name=template.display_name,
                    imported_version=imp.imported_version,
                    latest_version=template.version,
                    has_update=has_update,
                    is_customized=imp.is_customized,
                    imported_resource_id=imp.imported_resource_id,
                    imported_at=imp.imported_at,
                ))
        return result
