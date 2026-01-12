"""
Custom Vector Stores for CrewAI

解决双重 Embedding 问题：
- 问题：Postgres (已向量化) -> 取回 Text -> CrewAI -> OpenAI Embedding -> ChromaDB
- 方案：自定义 VectorStore，让 CrewAI 直接查询 Postgres pgvector

通过实现 CrewAI 的 VectorStore 接口，避免：
1. 成本浪费（重复调用 Embedding API）
2. 启动延迟（无需重新向量化）
3. 数据冗余（无需 ChromaDB 副本）
"""

from AICrews.observability.logging import get_logger
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from AICrews.database.db_manager import DBManager
from AICrews.database.vector_utils import VectorUtil
from AICrews.database.models import TradingLesson, MarketNews

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """向量搜索结果"""
    content: str
    metadata: Dict[str, Any]
    score: float
    source: str


class PostgresVectorStore:
    """
    Postgres pgvector 自定义 VectorStore
    
    直接查询 Postgres 中已向量化的数据，避免双重 Embedding。
    实现 CrewAI VectorStore 接口的核心方法。
    
    Supported Tables:
        - trading_lessons: 历史交易教训
        - market_news: 市场新闻
        - analysis_reports: 分析报告
    
    Usage:
        store = PostgresVectorStore(table="trading_lessons")
        results = store.search("high inflation market conditions", top_k=5)
    """
    
    def __init__(
        self,
        table: str = "trading_lessons",
        db: Optional[DBManager] = None,
    ):
        self.table = table
        self._db = db
        self._initialized = False
    
    @property
    def db(self) -> DBManager:
        """延迟初始化数据库连接"""
        if self._db is None:
            self._db = DBManager()
        return self._db
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        向量相似度搜索
        
        Args:
            query: 搜索查询文本
            top_k: 返回结果数量
            filter_metadata: 元数据过滤条件
            
        Returns:
            SearchResult 列表，按相似度排序
        """
        try:
            # 生成查询向量
            query_embedding = VectorUtil.get_embedding(query)
            if query_embedding is None:
                logger.warning("Failed to generate embedding for query")
                return []
            
            # 根据表类型执行搜索
            if self.table == "trading_lessons":
                return self._search_trading_lessons(query_embedding, top_k)
            elif self.table == "market_news":
                return self._search_market_news(query_embedding, top_k, filter_metadata)
            else:
                logger.warning(f"Unsupported table: {self.table}")
                return []
                
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def _search_trading_lessons(
        self,
        query_embedding: List[float],
        top_k: int,
    ) -> List[SearchResult]:
        """搜索 trading_lessons 表"""
        lessons = self.db.search_similar_lessons(
            query_embedding=query_embedding,
            limit=top_k,
        )
        
        return [
            SearchResult(
                content=f"Situation: {lesson.situation}\nLesson: {lesson.outcome_advice}",
                metadata={
                    "id": lesson.id,
                    "created_at": str(lesson.created_at) if lesson.created_at else None,
                },
                score=0.0,  # pgvector 返回距离，需要转换
                source="trading_lessons",
            )
            for lesson in lessons
        ]
    
    def _search_market_news(
        self,
        query_embedding: List[float],
        top_k: int,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """搜索 market_news 表"""
        with self.db.get_session() as session:
            from sqlalchemy import select
            
            # 使用 cosine_distance 排序
            stmt = select(MarketNews).order_by(
                MarketNews.embedding.cosine_distance(query_embedding)
            ).limit(top_k)
            
            # 应用过滤条件
            if filter_metadata:
                if "ticker" in filter_metadata:
                    stmt = stmt.filter(MarketNews.ticker == filter_metadata["ticker"])
            
            news_items = session.scalars(stmt).all()
            
            return [
                SearchResult(
                    content=f"Title: {news.title}\nContent: {news.content or news.summary or ''}",
                    metadata={
                        "id": news.id,
                        "ticker": news.ticker,
                        "published_at": str(news.published_at) if news.published_at else None,
                        "source": news.source,
                        "url": news.url,
                    },
                    score=0.0,
                    source="market_news",
                )
                for news in news_items
            ]
    
    def add(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """
        添加文本到向量存储
        
        对于 trading_lessons，使用 memorize_situation 工具添加
        """
        if self.table != "trading_lessons":
            raise NotImplementedError(f"Add not supported for table: {self.table}")
        
        ids = []
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas else {}
            
            # 生成向量
            embedding = VectorUtil.get_embedding(text)
            if embedding is None:
                continue
            
            # 保存到数据库
            self.db.save_lesson(
                situation=text,
                advice=metadata.get("advice", ""),
                embedding=embedding,
            )
            ids.append(str(i))
        
        return ids
    
    def delete(self, ids: List[str]) -> None:
        """删除向量（暂不支持）"""
        raise NotImplementedError("Delete not supported for PostgresVectorStore")


class LegacyLessonVectorStore(PostgresVectorStore):
    """
    专门用于 TradingLesson 的 VectorStore
    
    作为 CrewAI Knowledge Source 的后端存储，
    直接查询 Postgres 而不是让 CrewAI 重新向量化。
    
    Usage:
        from crewai import Agent
        from AICrews.infrastructure.vectorstores import LegacyLessonVectorStore
        
        # 创建自定义知识源
        store = LegacyLessonVectorStore(ticker="AAPL")
        
        # 在 Agent 中使用
        agent = Agent(
            role="Analyst",
            # 通过自定义 RAG 函数使用
        )
    """
    
    def __init__(
        self,
        ticker: Optional[str] = None,
        max_results: int = 5,
        db: Optional[DBManager] = None,
    ):
        super().__init__(table="trading_lessons", db=db)
        self.ticker = ticker
        self.max_results = max_results
    
    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        搜索相关的历史交易教训
        
        如果指定了 ticker，会在查询中包含 ticker 信息以提高相关性
        """
        # 增强查询
        enhanced_query = query
        if self.ticker:
            enhanced_query = f"{query} for stock {self.ticker}"
        
        return super().search(
            query=enhanced_query,
            top_k=top_k or self.max_results,
            filter_metadata=filter_metadata,
        )
    
    def get_relevant_context(self, query: str) -> str:
        """
        获取相关上下文（用于 RAG）
        
        返回格式化的知识文本，可直接注入到 Agent 上下文
        """
        results = self.search(query)
        
        if not results:
            return ""
        
        context_parts = ["## Relevant Historical Lessons\n"]
        for i, result in enumerate(results, 1):
            context_parts.append(f"### Lesson {i}")
            context_parts.append(result.content)
            context_parts.append("")
        
        return "\n".join(context_parts)


class UnifiedVectorStore:
    """
    统一向量存储接口
    
    聚合多个数据源的向量搜索，提供统一的查询接口。
    
    Usage:
        store = UnifiedVectorStore()
        store.add_source("lessons", LegacyLessonVectorStore(ticker="AAPL"))
        store.add_source("news", PostgresVectorStore(table="market_news"))
        
        results = store.search("market crash indicators")
    """
    
    def __init__(self):
        self._sources: Dict[str, PostgresVectorStore] = {}
    
    def add_source(self, name: str, store: PostgresVectorStore) -> None:
        """添加数据源"""
        self._sources[name] = store
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        sources: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """
        跨数据源搜索
        
        Args:
            query: 搜索查询
            top_k: 每个数据源返回的结果数
            sources: 指定搜索的数据源，None 表示搜索全部
        """
        all_results: List[SearchResult] = []
        
        target_sources = sources or list(self._sources.keys())
        
        for source_name in target_sources:
            if source_name not in self._sources:
                continue
            
            store = self._sources[source_name]
            results = store.search(query, top_k=top_k)
            all_results.extend(results)
        
        # 按相似度排序（如果有分数的话）
        all_results.sort(key=lambda x: x.score)
        
        return all_results[:top_k]
