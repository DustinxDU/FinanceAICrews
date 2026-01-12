import os
import uuid
from AICrews.observability.logging import get_logger
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta

from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session

from AICrews.database.models import (
    User, KnowledgeSource, UserKnowledgeSubscription,
    UserKnowledgeSource, CrewKnowledgeBinding, AgentKnowledgeBinding,
    TradingLesson, KnowledgeSourceVersion, KnowledgeUsageLog
)
from AICrews.schemas.knowledge import (
    KnowledgeSourceResponse,
    CreateUserKnowledgeRequest,
    CrewKnowledgeBindingRequest,
    AgentKnowledgeBindingRequest,
    AgentKnowledgeBindingResponse,
    CrewKnowledgeBindingResponse,
    DEFAULT_INCLUDE_TRADING_LESSONS,
    DEFAULT_MAX_LESSONS
)

logger = get_logger(__name__)

class KnowledgeService:
    def __init__(self, db: Session):
        self.db = db

    def list_marketplace(
        self,
        category: Optional[str] = None,
        knowledge_scope: Optional[str] = None,
        tier: Optional[str] = None,
        search: Optional[str] = None,
        current_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """列出知识市场中的所有知识源"""
        try:
            # 1. 基础查询：显示所有官方知识(system)
            query = self.db.query(KnowledgeSource).filter(
                KnowledgeSource.is_active == True,
                KnowledgeSource.scope == "system",
            )
            
            # 2. 如果用户已登录，也显示其私有知识
            if current_user:
                # 使用 union_all 或 or_ 来避免 union() 带来的复杂子查询兼容性问题
                query = self.db.query(KnowledgeSource).filter(
                    KnowledgeSource.is_active == True,
                    or_(
                        KnowledgeSource.scope == "system",
                        and_(
                            KnowledgeSource.scope == "user",
                            KnowledgeSource.owner_id == current_user.id
                        )
                    )
                )
            
            # 3. 应用过滤
            if category:
                query = query.filter(KnowledgeSource.category == category)
            
            if knowledge_scope:
                if knowledge_scope in ["crew", "agent"]:
                    query = query.filter(KnowledgeSource.knowledge_scope.in_([knowledge_scope, "both"]))
                elif knowledge_scope == "both":
                    query = query.filter(KnowledgeSource.knowledge_scope == "both")
            
            if tier:
                query = query.filter(KnowledgeSource.tier == tier)
            
            if search:
                search_filter = f"%{search}%"
                query = query.filter(
                    or_(
                        KnowledgeSource.display_name.ilike(search_filter),
                        KnowledgeSource.description.ilike(search_filter),
                        KnowledgeSource.source_key.ilike(search_filter)
                    )
                )
            
            sources = query.order_by(KnowledgeSource.subscriber_count.desc()).all()
            
            # 4. 获取用户订阅状态
            subscribed_ids = set()
            if current_user:
                subscriptions = self.db.query(UserKnowledgeSubscription).filter(
                    UserKnowledgeSubscription.user_id == current_user.id,
                    UserKnowledgeSubscription.is_active == True,
                ).all()
                subscribed_ids = {s.source_id for s in subscriptions}
            
            # 5. 获取分类列表
            categories_query = self.db.query(KnowledgeSource.category).filter(
                KnowledgeSource.is_active == True,
            ).distinct().all()
            categories = [c[0] for c in categories_query if c[0]]
            
            def get_access_status(source) -> str:
                if source.tier == "free": return "free"
                if source.scope == "user" and current_user and source.owner_id == current_user.id: return "owned"
                if source.tier == "premium" and source.id in subscribed_ids: return "subscribed"
                return "locked"
            
            return {
                "sources": [
                    {
                        "id": s.id,
                        "source_key": s.source_key,
                        "display_name": s.display_name,
                        "description": s.description,
                        "source_type": s.source_type,
                        "category": s.category,
                        "knowledge_scope": getattr(s, "knowledge_scope", "both"),
                        "scope": getattr(s, "scope", "system"),
                        "tier": getattr(s, "tier", "free"),
                        "price": getattr(s, "price", 0),
                        "tags": s.tags,
                        "icon": s.icon,
                        "cover_image": s.cover_image,
                        "author": s.author,
                        "version": s.version,
                        "is_free": s.tier == "free",
                        "subscriber_count": s.subscriber_count,
                        "usage_count": s.usage_count,
                        "is_subscribed": s.id in subscribed_ids,
                        "is_owned": s.scope == "user" and current_user and s.owner_id == current_user.id,
                        "access_status": get_access_status(s),
                    }
                    for s in sources
                ],
                "categories": categories,
                "total": len(sources),
            }
        except Exception as e:
            logger.error(f"Marketplace error: {str(e)}", exc_info=True)
            # 极简兜底
            return {"sources": [], "categories": [], "total": 0, "error": str(e)}

    def get_knowledge_source(self, source_key: str, current_user: Optional[User] = None) -> Dict[str, Any]:
        """获取知识源详细信息"""
        source = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.source_key == source_key,
            KnowledgeSource.is_active == True,
        ).first()
        
        if not source:
            return None
        
        is_subscribed = False
        if current_user:
            subscription = self.db.query(UserKnowledgeSubscription).filter(
                UserKnowledgeSubscription.user_id == current_user.id,
                UserKnowledgeSubscription.source_id == source.id,
                UserKnowledgeSubscription.is_active == True,
            ).first()
            is_subscribed = subscription is not None
        
        return {
            "id": source.id,
            "source_key": source.source_key,
            "display_name": source.display_name,
            "description": source.description,
            "source_type": source.source_type,
            "category": source.category,
            "scope": getattr(source, "scope", "both"),
            "tags": source.tags,
            "icon": source.icon,
            "cover_image": source.cover_image,
            "author": source.author,
            "version": source.version,
            "is_free": source.is_free,
            "subscriber_count": source.subscriber_count,
            "usage_count": source.usage_count,
            "chunk_size": source.chunk_size,
            "chunk_overlap": source.chunk_overlap,
            "is_subscribed": is_subscribed,
            "created_at": source.created_at.isoformat(),
        }

    def subscribe_knowledge(self, source_key: str, current_user: User) -> Dict[str, Any]:
        """订阅一个知识源到用户的知识库"""
        source = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.source_key == source_key,
            KnowledgeSource.is_active == True,
        ).first()
        
        if not source:
            raise ValueError("Knowledge source not found")
        
        # 检查是否已订阅
        existing = self.db.query(UserKnowledgeSubscription).filter(
            UserKnowledgeSubscription.user_id == current_user.id,
            UserKnowledgeSubscription.source_id == source.id,
        ).first()
        
        if existing:
            if existing.is_active:
                raise ValueError("Already subscribed")
            existing.is_active = True
            existing.subscribed_at = datetime.now()
        else:
            subscription = UserKnowledgeSubscription(
                user_id=current_user.id,
                source_id=source.id,
            )
            self.db.add(subscription)
            source.subscriber_count += 1
        
        self.db.commit()
        
        return {
            "message": f"Successfully subscribed to {source.display_name}",
            "source_key": source_key,
            "source_id": source.id,
        }

    def unsubscribe_knowledge(self, source_key: str, current_user: User) -> Dict[str, str]:
        """取消订阅知识源"""
        source = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.source_key == source_key,
        ).first()
        
        if not source:
            raise ValueError("Knowledge source not found")
        
        subscription = self.db.query(UserKnowledgeSubscription).filter(
            UserKnowledgeSubscription.user_id == current_user.id,
            UserKnowledgeSubscription.source_id == source.id,
            UserKnowledgeSubscription.is_active == True,
        ).first()
        
        if not subscription:
            raise ValueError("Not subscribed")
        
        subscription.is_active = False
        source.subscriber_count = max(0, source.subscriber_count - 1)
        self.db.commit()
        
        return {"message": "Unsubscribed successfully"}

    def list_my_sources(self, current_user: User) -> Dict[str, Any]:
        """列出用户订阅的知识源和自定义知识源"""
        # 订阅的系统知识源
        subscriptions = self.db.query(UserKnowledgeSubscription).filter(
            UserKnowledgeSubscription.user_id == current_user.id,
            UserKnowledgeSubscription.is_active == True,
        ).all()
        
        subscribed_sources = []
        for s in subscriptions:
            source = s.source
            if source and source.is_active:
                subscribed_sources.append({
                    "id": source.id,
                    "source_key": source.source_key,
                    "display_name": source.display_name,
                    "description": source.description,
                    "category": source.category,
                    "source_type": source.source_type,
                    "icon": source.icon,
                    "is_system": True,
                    "subscribed_at": s.subscribed_at.isoformat(),
                })
        
        # 用户自定义知识源
        custom_sources = self.db.query(UserKnowledgeSource).filter(
            UserKnowledgeSource.user_id == current_user.id,
            UserKnowledgeSource.is_active == True,
        ).all()
        
        custom_list = [
            {
                "id": s.id,
                "source_key": s.source_key,
                "display_name": s.display_name,
                "description": s.description,
                "category": s.category,
                "source_type": s.source_type,
                "is_system": False,
                "created_at": s.created_at.isoformat(),
            }
            for s in custom_sources
        ]
        
        # Legacy TradingLesson 统计
        lesson_count = self.db.query(TradingLesson).count()
        
        return {
            "subscribed_sources": subscribed_sources,
            "custom_sources": custom_list,
            "legacy_lessons": {
                "count": lesson_count,
                "description": "历史交易教训 (自动从 Postgres 加载)",
            },
            "total": len(subscribed_sources) + len(custom_list),
        }

    def create_user_knowledge(self, request: CreateUserKnowledgeRequest, current_user: User) -> Dict[str, Any]:
        """创建用户自定义知识源（文本内容）"""
        source_key = f"user_{current_user.id}_{uuid.uuid4().hex[:8]}"
        
        source = UserKnowledgeSource(
            user_id=current_user.id,
            source_key=source_key,
            display_name=request.display_name,
            description=request.description,
            source_type=request.source_type,
            content=request.content,
            url=request.url,
            category=request.category,
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        
        return {
            "id": source.id,
            "source_key": source_key,
            "display_name": request.display_name,
            "message": "Knowledge source created successfully",
        }

    def upload_knowledge_file(
        self,
        file_content: bytes,
        filename: str,
        display_name: str,
        description: Optional[str],
        category: str,
        current_user: User
    ) -> Dict[str, Any]:
        """
        上传知识文件 (PDF, TXT, MD, CSV)
        文件将存储在 config/knowledge/user_{user_id}/ 目录下
        """
        # 保存文件
        # 注意：这里假设 config 目录相对于当前文件位置，或者是一个固定路径
        # 原代码: Path(__file__).parent.parent.parent / "config" / "knowledge"
        # 这里我们需要一个可靠的路径获取方式
        # 假设我们使用 AICrews/services/knowledge_service.py，那么 parent.parent.parent 是 AICrews/.. 即 FinanceAICrews/
        # 但我们应该使用绝对路径或项目根目录配置
        # 这里暂时沿用相对路径逻辑，但根据实际部署可能需要调整
        
        base_dir = Path(os.getcwd()) / "config" / "knowledge"
        user_dir = base_dir / f"user_{current_user.id}"
        user_dir.mkdir(parents=True, exist_ok=True)
        
        safe_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
        file_path = user_dir / safe_filename
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # 创建数据库记录
        source_key = f"user_{current_user.id}_{uuid.uuid4().hex[:8]}"
        
        source = UserKnowledgeSource(
            user_id=current_user.id,
            source_key=source_key,
            display_name=display_name,
            description=description,
            source_type="file",
            file_path=str(file_path),
            category=category,
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        
        return {
            "id": source.id,
            "source_key": source_key,
            "display_name": display_name,
            "file_path": str(file_path),
            "message": "Knowledge file uploaded successfully",
        }

    def delete_user_knowledge(self, source_id: int, current_user: User) -> Dict[str, str]:
        """删除用户自定义知识源"""
        source = self.db.query(UserKnowledgeSource).filter(
            UserKnowledgeSource.id == source_id,
            UserKnowledgeSource.user_id == current_user.id,
        ).first()
        
        if not source:
            raise ValueError("Knowledge source not found")
        
        # 删除关联文件
        if source.file_path and os.path.exists(source.file_path):
            try:
                os.remove(source.file_path)
            except Exception as e:
                logger.warning(f"Failed to delete file {source.file_path}: {e}")
        
        self.db.delete(source)
        self.db.commit()
        
        return {"message": "Knowledge source deleted successfully"}

    def get_crew_knowledge_binding(self, crew_name: str, current_user: User) -> CrewKnowledgeBindingResponse:
        """获取 Crew 的知识绑定配置"""
        binding = self.db.query(CrewKnowledgeBinding).filter(
            CrewKnowledgeBinding.user_id == current_user.id,
            CrewKnowledgeBinding.crew_name == crew_name,
        ).first()
        
        if not binding:
            return CrewKnowledgeBindingResponse(
                crew_name=crew_name,
                binding_mode="explicit",
                source_ids=[],
                user_source_ids=[],
                categories=[],
                excluded_source_ids=[],
                include_trading_lessons=DEFAULT_INCLUDE_TRADING_LESSONS,
                max_lessons=DEFAULT_MAX_LESSONS,
                is_default=True,
            )
        
        return CrewKnowledgeBindingResponse(
            id=binding.id,
            crew_name=binding.crew_name,
            binding_mode=binding.binding_mode,
            source_ids=binding.source_ids or [],
            user_source_ids=binding.user_source_ids or [],
            categories=binding.categories or [],
            excluded_source_ids=binding.excluded_source_ids or [],
            include_trading_lessons=binding.include_trading_lessons,
            max_lessons=binding.max_lessons,
            is_default=False,
        )

    def set_crew_knowledge_binding(self, crew_name: str, request: CrewKnowledgeBindingRequest, current_user: User) -> Dict[str, Any]:
        """设置 Crew 的知识绑定配置"""
        binding = self.db.query(CrewKnowledgeBinding).filter(
            CrewKnowledgeBinding.user_id == current_user.id,
            CrewKnowledgeBinding.crew_name == crew_name,
        ).first()
        
        if not binding:
            binding = CrewKnowledgeBinding(
                user_id=current_user.id,
                crew_name=crew_name,
            )
            self.db.add(binding)
        
        binding.binding_mode = request.binding_mode
        binding.source_ids = request.source_ids
        binding.user_source_ids = request.user_source_ids
        binding.categories = request.categories
        binding.excluded_source_ids = request.excluded_source_ids
        binding.include_trading_lessons = request.include_trading_lessons
        binding.max_lessons = request.max_lessons
        binding.updated_at = datetime.now()
        
        self.db.commit()
        
        return {
            "message": "Knowledge binding saved successfully",
            "crew_name": crew_name,
        }

    def delete_crew_knowledge_binding(self, crew_name: str, current_user: User) -> Dict[str, str]:
        """删除 Crew 的知识绑定配置（恢复默认）"""
        binding = self.db.query(CrewKnowledgeBinding).filter(
            CrewKnowledgeBinding.user_id == current_user.id,
            CrewKnowledgeBinding.crew_name == crew_name,
        ).first()
        
        if not binding:
            raise ValueError("Binding not found")
        
        self.db.delete(binding)
        self.db.commit()
        
        return {"message": "Knowledge binding deleted, reverted to default"}

    def list_categories(self) -> Dict[str, Any]:
        """获取所有知识分类及其统计"""
        categories = self.db.query(
            KnowledgeSource.category,
        ).filter(
            KnowledgeSource.is_active == True,
            KnowledgeSource.is_system == True,
        ).distinct().all()
        
        result = []
        for (category,) in categories:
            count = self.db.query(KnowledgeSource).filter(
                KnowledgeSource.category == category,
                KnowledgeSource.is_active == True,
            ).count()
            result.append({
                "name": category,
                "count": count,
            })
        
        return {
            "categories": result,
            "total": len(result),
        }

    def bind_agent_knowledge(self, request: AgentKnowledgeBindingRequest, crew_name: str, current_user: User) -> AgentKnowledgeBindingResponse:
        """为指定 Agent 绑定知识源（显式绑定）"""
        
        # 查找或创建绑定
        binding = self.db.query(AgentKnowledgeBinding).filter(
            AgentKnowledgeBinding.user_id == current_user.id,
            AgentKnowledgeBinding.crew_name == crew_name,
            AgentKnowledgeBinding.agent_name == request.agent_name,
        ).first()
        
        if binding:
            # 更新现有绑定
            binding.source_ids = request.source_ids or []
            binding.user_source_ids = request.user_source_ids or []
            binding.include_trading_lessons = request.include_trading_lessons
            binding.max_lessons = request.max_lessons
            binding.updated_at = datetime.now()
        else:
            # 创建新绑定
            binding = AgentKnowledgeBinding(
                user_id=current_user.id,
                crew_name=crew_name,
                agent_name=request.agent_name,
                source_ids=request.source_ids or [],
                user_source_ids=request.user_source_ids or [],
                include_trading_lessons=request.include_trading_lessons,
                max_lessons=request.max_lessons,
            )
            self.db.add(binding)
        
        self.db.commit()
        self.db.refresh(binding)
        
        logger.info(f"Bound knowledge for agent '{request.agent_name}' in crew '{crew_name}'")
        
        return AgentKnowledgeBindingResponse(
            agent_name=binding.agent_name,
            source_ids=binding.source_ids or [],
            user_source_ids=binding.user_source_ids or [],
            include_trading_lessons=binding.include_trading_lessons,
            max_lessons=binding.max_lessons,
            created_at=binding.created_at,
        )

    def get_agent_knowledge_binding(self, crew_name: str, agent_name: str, current_user: User) -> AgentKnowledgeBindingResponse:
        """获取指定 Agent 的知识绑定配置"""
        
        binding = self.db.query(AgentKnowledgeBinding).filter(
            AgentKnowledgeBinding.user_id == current_user.id,
            AgentKnowledgeBinding.crew_name == crew_name,
            AgentKnowledgeBinding.agent_name == agent_name,
        ).first()
        
        if not binding:
            # 返回默认配置（统一使用全局默认值）
            return AgentKnowledgeBindingResponse(
                agent_name=agent_name,
                source_ids=[],
                user_source_ids=[],
                include_trading_lessons=DEFAULT_INCLUDE_TRADING_LESSONS,
                max_lessons=DEFAULT_MAX_LESSONS,
                created_at=datetime.now(),
            )
        
        return AgentKnowledgeBindingResponse(
            agent_name=binding.agent_name,
            source_ids=binding.source_ids or [],
            user_source_ids=binding.user_source_ids or [],
            include_trading_lessons=binding.include_trading_lessons,
            max_lessons=binding.max_lessons,
            created_at=binding.created_at,
        )

    def delete_agent_knowledge_binding(self, crew_name: str, agent_name: str, current_user: User) -> Dict[str, str]:
        """删除指定 Agent 的知识绑定配置"""
        
        binding = self.db.query(AgentKnowledgeBinding).filter(
            AgentKnowledgeBinding.user_id == current_user.id,
            AgentKnowledgeBinding.crew_name == crew_name,
            AgentKnowledgeBinding.agent_name == agent_name,
        ).first()
        
        if not binding:
            raise ValueError("Agent knowledge binding not found")
        
        self.db.delete(binding)
        self.db.commit()
        
        logger.info(f"Deleted knowledge binding for agent '{agent_name}' in crew '{crew_name}'")
        
        return {"message": "Agent knowledge binding deleted"}

    def list_knowledge_versions(self, source_key: str) -> Dict[str, Any]:
        """获取知识源的所有版本"""
        source = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.source_key == source_key,
        ).first()
        
        if not source:
            raise ValueError("Knowledge source not found")
        
        versions = self.db.query(KnowledgeSourceVersion).filter(
            KnowledgeSourceVersion.source_id == source.id,
        ).order_by(KnowledgeSourceVersion.created_at.desc()).all()
        
        return {
            "source_key": source_key,
            "current_version": source.version,
            "versions": [
                {
                    "id": v.id,
                    "version": v.version,
                    "changelog": v.changelog,
                    "is_current": v.is_current,
                    "created_at": v.created_at.isoformat(),
                }
                for v in versions
            ],
            "total": len(versions),
        }

    def get_usage_stats(self, days: int, current_user: User) -> Dict[str, Any]:
        """获取用户的知识源使用统计"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 按知识源统计使用次数
        source_stats = self.db.query(
            KnowledgeUsageLog.source_id,
            func.count(KnowledgeUsageLog.id).label('count')
        ).filter(
            KnowledgeUsageLog.user_id == current_user.id,
            KnowledgeUsageLog.source_id.isnot(None),
            KnowledgeUsageLog.created_at >= cutoff_date,
        ).group_by(KnowledgeUsageLog.source_id).all()
        
        # 获取知识源详情
        source_ids = [s[0] for s in source_stats]
        sources = {}
        if source_ids:
            for source in self.db.query(KnowledgeSource).filter(KnowledgeSource.id.in_(source_ids)).all():
                sources[source.id] = {
                    "source_key": source.source_key,
                    "display_name": source.display_name,
                    "category": source.category,
                }
        
        # 按 Crew 统计
        crew_stats = self.db.query(
            KnowledgeUsageLog.crew_name,
            func.count(KnowledgeUsageLog.id).label('count')
        ).filter(
            KnowledgeUsageLog.user_id == current_user.id,
            KnowledgeUsageLog.crew_name.isnot(None),
            KnowledgeUsageLog.created_at >= cutoff_date,
        ).group_by(KnowledgeUsageLog.crew_name).all()
        
        # 总使用次数
        total_usage = self.db.query(func.count(KnowledgeUsageLog.id)).filter(
            KnowledgeUsageLog.user_id == current_user.id,
            KnowledgeUsageLog.created_at >= cutoff_date,
        ).scalar() or 0
        
        return {
            "period_days": days,
            "total_usage": total_usage,
            "by_source": [
                {
                    "source_id": s[0],
                    "count": s[1],
                    **sources.get(s[0], {}),
                }
                for s in source_stats
            ],
            "by_crew": [
                {"crew_name": c[0], "count": c[1]}
                for c in crew_stats
            ],
        }

    def get_popular_sources(self, limit: int) -> Dict[str, Any]:
        """获取全局热门知识源（按使用次数排序）"""
        sources = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.is_active == True,
            KnowledgeSource.is_system == True,
        ).order_by(KnowledgeSource.usage_count.desc()).limit(limit).all()
        
        return {
            "sources": [
                {
                    "id": s.id,
                    "source_key": s.source_key,
                    "display_name": s.display_name,
                    "category": s.category,
                    "usage_count": s.usage_count,
                    "subscriber_count": s.subscriber_count,
                }
                for s in sources
            ],
            "total": len(sources),
        }
