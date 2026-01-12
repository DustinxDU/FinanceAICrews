"""
Custom Knowledge Sources for CrewAI

将现有的 TradingLesson 数据和用户知识源包装为 CrewAI 原生 Knowledge Source，
避免通过 backstory 拼接污染 Context Window。

优化特性：
1. 自定义 VectorStore：直接查询 Postgres pgvector，避免双重 Embedding
2. 角色绑定：基于 Agent 角色的知识路由，减少噪音
3. 强制引用：知识源自动添加 [Source: xxx] 标记，支持可观测性

Usage:
    from AICrews.core.knowledge_sources import LegacyLessonKnowledgeSource
    
    source = LegacyLessonKnowledgeSource(ticker="AAPL", max_lessons=5)
    agent = Agent(
        role="Analyst",
        knowledge_sources=[source],
        ...
    )
"""

import yaml
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Set, Tuple

from pydantic import Field

from AICrews.database.db_manager import DBManager
from AICrews.database.vector_utils import VectorUtil
from AICrews.observability.logging import get_logger

logger = get_logger(__name__)

# 知识源配置文件路径
KNOWLEDGE_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "knowledge_sources.yaml"


def load_knowledge_config() -> Dict[str, Any]:
    """加载知识源配置"""
    if not KNOWLEDGE_CONFIG_PATH.exists():
        return {}
    with open(KNOWLEDGE_CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


class LegacyLessonKnowledgeSource:
    """
    将 Postgres 中的 TradingLesson 包装为 CrewAI Knowledge Source
    
    优化：使用自定义 VectorStore 直接查询 Postgres，避免双重 Embedding。
    
    Attributes:
        ticker: 股票代码，用于过滤相关教训
        max_lessons: 最大返回教训数量
        context: 额外上下文，用于语义搜索
        source_name: 知识源名称，用于 Citations
    
    Example:
        source = LegacyLessonKnowledgeSource(
            ticker="AAPL",
            max_lessons=5,
        )
        # CrewAI 会自动调用 load_content() 获取知识内容
    """
    
    # 知识源标识，用于 Citations
    SOURCE_NAME = "trading_lessons.db"
    
    def __init__(
        self,
        ticker: Optional[str] = None,
        max_lessons: int = 5,
        context: Optional[str] = None,
        use_custom_vector_store: bool = True,
    ):
        self.ticker = ticker
        self.max_lessons = max_lessons
        self.context = context
        self.use_custom_vector_store = use_custom_vector_store
        self._db: Optional[DBManager] = None
        self._lessons_cache: Optional[List[Dict[str, Any]]] = None
        self._vector_store = None
    
    @property
    def db(self) -> DBManager:
        """延迟初始化数据库连接"""
        if self._db is None:
            self._db = DBManager()
        return self._db
    
    @property
    def vector_store(self):
        """获取自定义 VectorStore（避免双重 Embedding）"""
        if self._vector_store is None and self.use_custom_vector_store:
            from AICrews.infrastructure.vectorstores import LegacyLessonVectorStore
            self._vector_store = LegacyLessonVectorStore(
                ticker=self.ticker,
                max_results=self.max_lessons,
                db=self._db,
            )
        return self._vector_store
    
    def load_content(self) -> str:
        """
        加载知识内容 - CrewAI 会调用此方法
        
        Returns:
            格式化的历史教训文本，包含 [Source: ...] 引用标记
        """
        lessons = self._fetch_lessons()
        
        if not lessons:
            return "No historical trading lessons available."
        
        content_parts = ["## Historical Trading Lessons\n"]
        content_parts.append("The following are past market situations and lessons learned:\n")
        content_parts.append(f"[Source: {self.SOURCE_NAME}]\n")
        
        for i, lesson in enumerate(lessons, 1):
            content_parts.append(f"\n### Lesson {i} [Source: {self.SOURCE_NAME}]")
            content_parts.append(f"**Situation**: {lesson['situation']}")
            content_parts.append(f"**Lesson Learned**: {lesson['outcome_advice']}")
            content_parts.append("")
        
        return "\n".join(content_parts)
    
    def _fetch_lessons(self) -> List[Dict[str, Any]]:
        """从数据库获取相关教训"""
        if self._lessons_cache is not None:
            return self._lessons_cache
        
        try:
            # 使用自定义 VectorStore（如果启用）
            if self.use_custom_vector_store and self.vector_store:
                query = "Trading lessons and market situations"
                if self.context:
                    query = f"{query} in context of {self.context}"
                
                results = self.vector_store.search(query)
                self._lessons_cache = [
                    {
                        "situation": r.content.split("\nLesson:")[0].replace("Situation: ", ""),
                        "outcome_advice": r.content.split("\nLesson:")[-1].strip() if "\nLesson:" in r.content else "",
                    }
                    for r in results
                ]
            else:
                # 回退到原始实现
                query = "Trading lessons and market situations"
                if self.ticker:
                    query = f"{query} for {self.ticker}"
                if self.context:
                    query = f"{query} in context of {self.context}"
                
                query_embedding = VectorUtil.get_embedding(query)
                if query_embedding is None:
                    logger.warning("Failed to get embedding for lesson query")
                    return []
                
                lessons = self.db.search_similar_lessons(
                    query_embedding=query_embedding,
                    limit=self.max_lessons,
                )
                
                self._lessons_cache = [
                    {
                        "situation": lesson.situation,
                        "outcome_advice": lesson.outcome_advice,
                    }
                    for lesson in lessons
                ]
            
            logger.info(f"Loaded {len(self._lessons_cache)} trading lessons as knowledge source")
            return self._lessons_cache
            
        except Exception as e:
            logger.error(f"Failed to fetch trading lessons: {e}")
            return []
    
    def add(self, content: str) -> None:
        """只读知识源，不支持添加"""
        raise NotImplementedError("LegacyLessonKnowledgeSource is read-only")
    
    def __repr__(self) -> str:
        return f"LegacyLessonKnowledgeSource(ticker={self.ticker}, max_lessons={self.max_lessons})"


class FileKnowledgeSourceFactory:
    """
    根据数据库配置创建 CrewAI 文件知识源
    
    支持的文件类型:
    - PDF: 使用 PDFKnowledgeSource
    - CSV: 使用 CSVKnowledgeSource  
    - TXT/MD/JSON: 使用 TextFileKnowledgeSource
    - String: 使用 StringKnowledgeSource
    """
    
    @staticmethod
    def create_from_config(source: Union["KnowledgeSource", "UserKnowledgeSource"]) -> Any:
        """
        根据数据库中的 KnowledgeSource 记录创建对应的 CrewAI Knowledge Source
        
        Args:
            source: KnowledgeSource 或 UserKnowledgeSource 数据库记录
            
        Returns:
            CrewAI BaseKnowledgeSource 实例
        """
        try:
            from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
            from crewai.knowledge.source.pdf_knowledge_source import PDFKnowledgeSource
            from crewai.knowledge.source.csv_knowledge_source import CSVKnowledgeSource
            from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
        except ImportError:
            logger.warning("CrewAI knowledge sources not available, using fallback")
            return StringKnowledgeSourceFallback(
                content=getattr(source, 'content', '') or f"Knowledge from {source.display_name}"
            )
        
        chunk_size = getattr(source, 'chunk_size', 4000)
        chunk_overlap = getattr(source, 'chunk_overlap', 200)
        
        if source.source_type == "string":
            return StringKnowledgeSource(
                content=source.content or "",
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        
        if source.source_type == "file" and source.file_path:
            file_path = Path(source.file_path)
            
            if not file_path.exists():
                logger.warning(f"Knowledge file not found: {file_path}")
                return StringKnowledgeSource(
                    content=f"[File not found: {source.display_name}]",
                )
            
            ext = file_path.suffix.lower()
            
            if ext == ".pdf":
                return PDFKnowledgeSource(
                    file_paths=[str(file_path)],
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
            elif ext == ".csv":
                return CSVKnowledgeSource(
                    file_paths=[str(file_path)],
                )
            else:
                # txt, md, json 等文本文件
                return TextFileKnowledgeSource(
                    file_paths=[str(file_path)],
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
        
        # URL 类型暂时转换为 String
        if source.source_type == "url" and source.url:
            # TODO: 实现 URL 内容抓取
            return StringKnowledgeSource(
                content=f"Knowledge from URL: {source.url}",
            )
        
        raise ValueError(f"Unsupported source type: {source.source_type}")


class StringKnowledgeSourceFallback:
    """简单的字符串知识源回退实现"""
    
    def __init__(self, content: str):
        self.content = content
    
    def load_content(self) -> str:
        return self.content
    
    def add(self, content: str) -> None:
        raise NotImplementedError("Read-only knowledge source")


# 全局知识源缓存 - 避免重复创建相同的 FileKnowledgeSource
_knowledge_source_cache: Dict[str, Any] = {}


def _get_cache_key(source_type: str, source_id: int, file_path: Optional[str] = None) -> str:
    """生成知识源缓存键"""
    return f"{source_type}:{source_id}:{file_path or ''}"


def clear_knowledge_cache():
    """清除知识源缓存（用于测试或重新加载）"""
    global _knowledge_source_cache
    _knowledge_source_cache.clear()
    logger.info("Knowledge source cache cleared")


class KnowledgeLoader:
    """
    知识加载器 - 根据配置加载 CrewAI Knowledge Sources
    
    负责从数据库读取用户的知识配置，并创建相应的 CrewAI Knowledge Source 实例。
    
    特性：
    - **Memoization**: 同一 source_id 只创建一次 FileKnowledgeSource
    - **去重合并**: Crew + Agent 级别知识源自动去重（集合运算）
    - **优先级**: Agent 级配置覆盖 Crew 级配置
    - **使用统计**: 自动记录知识源调用次数
    
    Usage:
        loader = KnowledgeLoader(db_session, user_id)
        sources = loader.load_for_crew("stock_analyst", ticker="AAPL")
        
        crew = Crew(
            agents=agents,
            tasks=tasks,
            knowledge_sources=sources,
        )
    """
    
    def __init__(self, db_session, user_id: int, track_usage: bool = True, job_id: Optional[str] = None):
        self.db_session = db_session
        self.user_id = user_id
        self.track_usage = track_usage
        self.job_id = job_id
        self._loaded_source_ids: Set[int] = set()  # 跟踪已加载的系统知识源
        self._loaded_user_source_ids: Set[int] = set()  # 跟踪已加载的用户知识源
        self._current_crew_name: Optional[str] = None
        self._current_agent_name: Optional[str] = None
        self._current_ticker: Optional[str] = None
    
    def _check_knowledge_permission(self, source: Any) -> Tuple[bool, Optional[str]]:
        """
        检查用户是否有权限访问该知识源
        
        三类知识资产的权限规则：
        1. 官方免费 (scope=system, tier=free): 所有人可用
        2. 官方付费 (scope=system, tier=premium): 需要订阅记录
        3. 用户私有 (scope=user, tier=private): 必须是所有者
        
        Args:
            source: KnowledgeSource 数据库记录
            
        Returns:
            (is_allowed, error_message) 元组
        """
        from AICrews.database.models import UserKnowledgeSubscription
        from datetime import datetime
        
        scope = getattr(source, 'scope', 'system')
        tier = getattr(source, 'tier', 'free')
        owner_id = getattr(source, 'owner_id', None)
        
        # 规则 1: 免费知识直接放行
        if tier == 'free':
            return True, None
        
        # 规则 2: 私有知识，必须是所有者
        if tier == 'private' or scope == 'user':
            if owner_id != self.user_id:
                return False, f"无权访问私有知识源: {source.display_name}"
            return True, None
        
        # 规则 3: 付费知识，必须查订阅表
        if tier == 'premium':
            subscription = self.db_session.query(UserKnowledgeSubscription).filter(
                UserKnowledgeSubscription.user_id == self.user_id,
                UserKnowledgeSubscription.source_id == source.id,
                UserKnowledgeSubscription.is_active == True,
            ).first()
            
            if not subscription:
                return False, f"未购买付费知识源: {source.display_name}"
            
            # 检查订阅是否过期
            if subscription.valid_until and subscription.valid_until < datetime.now():
                return False, f"知识源订阅已过期: {source.display_name}"
            
            return True, None
        
        # 默认放行
        return True, None
    
    def _get_or_create_source(self, source: Any, source_type: str = "system") -> Optional[Any]:
        """
        获取或创建知识源实例（带缓存和权限检查）
        
        Args:
            source: KnowledgeSource 或 UserKnowledgeSource 数据库记录
            source_type: "system" 或 "user"
            
        Returns:
            CrewAI Knowledge Source 实例，如果已加载则返回 None
        """
        global _knowledge_source_cache
        
        # ✅ 权限检查 - 这是核心安全控制点
        is_allowed, error_msg = self._check_knowledge_permission(source)
        if not is_allowed:
            logger.warning(f"Permission denied: {error_msg}")
            raise PermissionError(error_msg)
        
        cache_key = _get_cache_key(
            source_type, 
            source.id, 
            getattr(source, 'file_path', None)
        )
        
        # 检查是否已在本次加载中处理过（去重）
        if source_type == "system":
            if source.id in self._loaded_source_ids:
                logger.debug(f"Skipping duplicate system source: {source.source_key}")
                return None
            self._loaded_source_ids.add(source.id)
        else:
            if source.id in self._loaded_user_source_ids:
                logger.debug(f"Skipping duplicate user source: {source.source_key}")
                return None
            self._loaded_user_source_ids.add(source.id)
        
        # 检查全局缓存
        if cache_key in _knowledge_source_cache:
            logger.debug(f"Using cached knowledge source: {source.source_key}")
            return _knowledge_source_cache[cache_key]
        
        # 创建新实例
        try:
            ks = FileKnowledgeSourceFactory.create_from_config(source)
            _knowledge_source_cache[cache_key] = ks
            logger.info(f"Created knowledge source: {source.display_name}")
            return ks
        except Exception as e:
            logger.warning(f"Failed to create knowledge source {source.source_key}: {e}")
            return None
    
    def reset_loaded_tracking(self):
        """重置已加载跟踪（用于新的加载周期）"""
        self._loaded_source_ids.clear()
        self._loaded_user_source_ids.clear()
    
    def _log_usage(self, source_id: Optional[int] = None, user_source_id: Optional[int] = None, usage_type: str = "crew_run", display_name: str = "Unknown"):
        """记录知识源使用统计并发出实时事件"""
        if self.job_id:
            from AICrews.services.tracking_service import TrackingService
            from AICrews.schemas.stats import AgentActivityEvent
            tracker = TrackingService()
            tracker.add_activity(self.job_id, AgentActivityEvent(
                agent_name=self._current_agent_name or "System",
                activity_type="knowledge_retrieval",
                message=f"Retrieved knowledge from: {display_name}",
                timestamp=datetime.now()
            ))

        if not self.track_usage:
            return
        
        try:
            from AICrews.database.models import KnowledgeUsageLog, KnowledgeSource
            
            log = KnowledgeUsageLog(
                source_id=source_id,
                user_source_id=user_source_id,
                user_id=self.user_id,
                crew_name=self._current_crew_name,
                agent_name=self._current_agent_name,
                ticker=self._current_ticker,
                usage_type=usage_type,
            )
            self.db_session.add(log)
            
            # 同时更新 KnowledgeSource 的 usage_count
            if source_id:
                source = self.db_session.query(KnowledgeSource).filter(
                    KnowledgeSource.id == source_id
                ).first()
                if source:
                    source.usage_count = (source.usage_count or 0) + 1
            
            self.db_session.commit()
        except Exception as e:
            logger.warning(f"Failed to log usage: {e}")
            try:
                self.db_session.rollback()
            except Exception as rollback_error:
                logger.warning(f"Rollback failed: {rollback_error}")
    
    @staticmethod
    def _is_scope_allowed(scope: Optional[str], target: str) -> bool:
        """判断知识源作用域是否允许注入到目标层级"""
        normalized = (scope or "both").lower()
        return normalized == "both" or normalized == target

    def load_for_crew(
        self,
        crew_name: str,
        ticker: Optional[str] = None,
    ) -> List[Any]:
        """
        为 Crew 加载知识源
        
        Args:
            crew_name: Crew 名称
            ticker: 股票代码（用于 TradingLesson 查询）
            
        Returns:
            CrewAI Knowledge Source 列表
        """
        from AICrews.database.models import (
            CrewKnowledgeBinding, KnowledgeSource, 
            UserKnowledgeSource, UserKnowledgeSubscription
        )
        
        # 设置当前上下文用于使用统计
        self._current_crew_name = crew_name
        self._current_agent_name = None
        self._current_ticker = ticker
        
        sources: List[Any] = []
        
        # 1. 获取 Crew 知识绑定配置
        binding = self.db_session.query(CrewKnowledgeBinding).filter(
            CrewKnowledgeBinding.user_id == self.user_id,
            CrewKnowledgeBinding.crew_name == crew_name,
        ).first()
        
        # 2. 加载 Legacy TradingLesson
        include_lessons = binding.include_trading_lessons if binding else True
        max_lessons = binding.max_lessons if binding else 5
        
        if include_lessons:
            sources.append(LegacyLessonKnowledgeSource(
                ticker=ticker,
                max_lessons=max_lessons,
            ))
            logger.info(f"Loaded LegacyLessonKnowledgeSource for crew '{crew_name}'")
        
        # 3. 加载订阅的系统知识源
        source_ids = binding.source_ids if binding and binding.source_ids else []
        
        if not source_ids and (not binding or binding.binding_mode == "all"):
            # 如果没有显式绑定且模式为 all，加载所有订阅的知识源
            subscriptions = self.db_session.query(UserKnowledgeSubscription).filter(
                UserKnowledgeSubscription.user_id == self.user_id,
                UserKnowledgeSubscription.is_active == True,
            ).all()
            source_ids = [s.source_id for s in subscriptions]
        
        if source_ids:
            system_sources = self.db_session.query(KnowledgeSource).filter(
                KnowledgeSource.id.in_(source_ids),
                KnowledgeSource.is_active == True,
            ).all()
            
            for source in system_sources:
                if not self._is_scope_allowed(getattr(source, "scope", None), "crew"):
                    continue
                ks = self._get_or_create_source(source, "system")
                if ks:
                    sources.append(ks)
                    self._log_usage(source_id=source.id, usage_type="crew_run", display_name=source.display_name)
        
        # 4. 加载用户自定义知识源
        user_source_ids = binding.user_source_ids if binding and binding.user_source_ids else []
        
        if user_source_ids:
            user_sources = self.db_session.query(UserKnowledgeSource).filter(
                UserKnowledgeSource.id.in_(user_source_ids),
                UserKnowledgeSource.user_id == self.user_id,
                UserKnowledgeSource.is_active == True,
            ).all()
            
            for source in user_sources:
                if not self._is_scope_allowed(getattr(source, "scope", None), "crew"):
                    continue
                ks = self._get_or_create_source(source, "user")
                if ks:
                    sources.append(ks)
                    self._log_usage(user_source_id=source.id, usage_type="crew_run", display_name=source.display_name)
        
        # 5. 按分类加载（如果配置了分类绑定）
        categories = binding.categories if binding and binding.categories else []
        excluded_ids = binding.excluded_source_ids if binding and binding.excluded_source_ids else []
        
        if categories:
            category_sources = self.db_session.query(KnowledgeSource).filter(
                KnowledgeSource.category.in_(categories),
                KnowledgeSource.is_active == True,
                ~KnowledgeSource.id.in_(excluded_ids) if excluded_ids else True,
            ).all()
            
            # 使用 _get_or_create_source 自动去重
            for source in category_sources:
                if not self._is_scope_allowed(getattr(source, "scope", None), "crew"):
                    continue
                ks = self._get_or_create_source(source, "system")
                if ks:
                    sources.append(ks)
                    logger.info(f"Loaded category knowledge source: {source.display_name}")
        
        logger.info(f"Total {len(sources)} knowledge sources loaded for crew '{crew_name}'")
        return sources
    
    def load_for_agent(
        self,
        agent_name: str,
        crew_name: str,
        ticker: Optional[str] = None,
    ) -> List[Any]:
        """
        为特定 Agent 加载知识源（显式绑定）
        
        直接返回为该 Agent 显式绑定的知识源，不做任何自动过滤。
        用户在 Crew Builder 中选择该 Agent 可用的知识源，就像选择工具一样。
        
        Args:
            agent_name: Agent 名称
            crew_name: Crew 名称
            ticker: 股票代码
            
        Returns:
            该 Agent 显式绑定的知识源列表
        """
        from AICrews.database.models import (
            AgentKnowledgeBinding, KnowledgeSource, UserKnowledgeSource
        )
        
        sources: List[Any] = []
        
        # 查询 Agent 级别的显式知识绑定
        try:
            agent_binding = self.db_session.query(AgentKnowledgeBinding).filter(
                AgentKnowledgeBinding.user_id == self.user_id,
                AgentKnowledgeBinding.crew_name == crew_name,
                AgentKnowledgeBinding.agent_name == agent_name,
            ).first()
        except Exception as e:
            logger.warning(f"Failed to query AgentKnowledgeBinding: {e}")
            return []
        
        if not agent_binding:
            # 没有显式绑定，返回空列表
            logger.debug(f"No knowledge binding found for agent '{agent_name}' in crew '{crew_name}'")
            return []
        
        # 加载系统知识源（使用缓存和去重）
        if agent_binding.source_ids:
            system_sources = self.db_session.query(KnowledgeSource).filter(
                KnowledgeSource.id.in_(agent_binding.source_ids),
                KnowledgeSource.is_active == True,
            ).all()
            
            for source in system_sources:
                if not self._is_scope_allowed(getattr(source, "scope", None), "agent"):
                    continue
                ks = self._get_or_create_source(source, "system")
                if ks:
                    sources.append(ks)
                    logger.info(f"Loaded knowledge source for agent '{agent_name}': {source.display_name}")
        
        # 加载用户自定义知识源（使用缓存和去重）
        if agent_binding.user_source_ids:
            user_sources = self.db_session.query(UserKnowledgeSource).filter(
                UserKnowledgeSource.id.in_(agent_binding.user_source_ids),
                UserKnowledgeSource.user_id == self.user_id,
                UserKnowledgeSource.is_active == True,
            ).all()
            
            for source in user_sources:
                if not self._is_scope_allowed(getattr(source, "scope", None), "agent"):
                    continue
                ks = self._get_or_create_source(source, "user")
                if ks:
                    sources.append(ks)
                    logger.info(f"Loaded user knowledge source for agent '{agent_name}': {source.display_name}")
        
        # 加载 Legacy TradingLesson（如果配置了）
        if agent_binding.include_trading_lessons:
            sources.append(LegacyLessonKnowledgeSource(
                ticker=ticker,
                max_lessons=agent_binding.max_lessons,
            ))
            logger.info(f"Loaded LegacyLessonKnowledgeSource for agent '{agent_name}'")
        
        logger.info(f"Loaded {len(sources)} knowledge sources for agent '{agent_name}'")
        return sources
    
    def _load_from_binding(self, binding, ticker: Optional[str]) -> List[Any]:
        """从绑定配置加载知识源"""
        from AICrews.database.models import KnowledgeSource, UserKnowledgeSource
        
        sources: List[Any] = []
        
        # 加载系统知识源
        if binding.source_ids:
            system_sources = self.db_session.query(KnowledgeSource).filter(
                KnowledgeSource.id.in_(binding.source_ids),
                KnowledgeSource.is_active == True,
            ).all()
            
            for source in system_sources:
                try:
                    ks = FileKnowledgeSourceFactory.create_from_config(source)
                    sources.append(ks)
                except Exception as e:
                    logger.warning(f"Failed to load knowledge source: {e}")
        
        # 加载用户知识源
        if binding.user_source_ids:
            user_sources = self.db_session.query(UserKnowledgeSource).filter(
                UserKnowledgeSource.id.in_(binding.user_source_ids),
                UserKnowledgeSource.user_id == self.user_id,
                UserKnowledgeSource.is_active == True,
            ).all()
            
            for source in user_sources:
                try:
                    ks = FileKnowledgeSourceFactory.create_from_config(source)
                    sources.append(ks)
                except Exception as e:
                    logger.warning(f"Failed to load user knowledge source: {e}")
        
        return sources
    
    def load_by_ids(
        self,
        source_ids: List[int],
        ticker: Optional[str] = None,
    ) -> List[Any]:
        """
        直接按 ID 列表加载知识源（由图编译器生成的绑定使用）
        
        这是最直接的加载方式，跳过绑定表查询，直接从 ID 加载。
        用于支持图编译器将 Knowledge 节点连线转换为 Agent 的知识源绑定。
        
        Args:
            source_ids: 知识源 ID 列表
            ticker: 股票代码（用于 TradingLesson 等动态知识源）
            
        Returns:
            CrewAI Knowledge Source 实例列表
        """
        from AICrews.database.models import KnowledgeSource, UserKnowledgeSource
        
        if not source_ids:
            return []
        
        sources: List[Any] = []
        self._current_ticker = ticker
        
        # 尝试从系统知识源加载
        system_sources = self.db_session.query(KnowledgeSource).filter(
            KnowledgeSource.id.in_(source_ids),
            KnowledgeSource.is_active == True,
        ).all()
        
        for source in system_sources:
            ks = self._get_or_create_source(source, "system")
            if ks:
                sources.append(ks)
                self._log_usage(source_id=source.id, usage_type="graph_compiled", display_name=source.display_name)
        
        # 如果系统知识源没有找到所有 ID，尝试从用户知识源加载
        found_ids = {s.id for s in system_sources}
        missing_ids = [sid for sid in source_ids if sid not in found_ids]
        
        if missing_ids:
            user_sources = self.db_session.query(UserKnowledgeSource).filter(
                UserKnowledgeSource.id.in_(missing_ids),
                UserKnowledgeSource.user_id == self.user_id,
                UserKnowledgeSource.is_active == True,
            ).all()
            
            for source in user_sources:
                ks = self._get_or_create_source(source, "user")
                if ks:
                    sources.append(ks)
                    self._log_usage(user_source_id=source.id, usage_type="graph_compiled", display_name=source.display_name)
        
        logger.info(f"Loaded {len(sources)} knowledge sources by IDs: {source_ids}")
        return sources
