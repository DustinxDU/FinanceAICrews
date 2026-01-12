import os
import pandas as pd
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, AsyncGenerator
from sqlalchemy import create_engine, select, text, and_, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .models import (
    Base, 
    StockPrice, 
    FundamentalData,
    FinancialStatement,
    TechnicalIndicator,
    MarketNews,
    InsiderActivity,
    AnalysisReport, 
    TradingLesson
)

from AICrews.utils import monitor
from AICrews.observability.logging import get_module_logger, LogModule

logger = get_module_logger(LogModule.DATABASE)
from AICrews.utils.exceptions import DatabaseException, ConfigException

# 尝试从环境变量获取数据库配置
DB_URL = os.getenv("DATABASE_URL")

# 如果没有设置 DATABASE_URL，在开发环境下尝试构造一个默认地址
# 生产环境下必须通过环境变量提供
if not DB_URL:
    logger.warning("DATABASE_URL not set in environment. Database features will be unavailable.")



class DBManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBManager, cls).__new__(cls)
            cls._instance.engine = None
            cls._instance.SessionLocal = None
        return cls._instance

    def _ensure_engine(self):
        """懒加载创建数据库 Engine 和 Session，避免导入即连接"""
        if self.engine is not None and self.SessionLocal is not None:
            return

        if not DB_URL:
            raise ConfigException("DATABASE_URL 未配置，无法初始化数据库连接")

        try:
            # 确保使用正确的同步数据库 URL
            sync_db_url = DB_URL
            if "postgresql+asyncpg://" in DB_URL:
                sync_db_url = DB_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
            elif "postgresql://" not in DB_URL and "postgres://" not in DB_URL:
                raise DatabaseException(f"不支持的数据库 URL 格式: {DB_URL}")
            
            self.engine = create_engine(sync_db_url)
            self.SessionLocal = sessionmaker(bind=self.engine)
        except Exception as e:
            raise DatabaseException(f"数据库连接失败，请检查 DATABASE_URL：{e}") from e

    def get_session(self):
        self._ensure_engine()
        return self.SessionLocal()

    def _init_db(self):
        """
        初始化数据库：创建所有表结构
        如果表已存在则跳过，不会删除现有数据
        """
        self._ensure_engine()

        # 启用 pgvector 扩展
        with self.engine.connect() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
            except Exception as e:
                raise DatabaseException(
                    f"初始化 pgvector 扩展失败，请确认数据库已安装 pgvector: {e}"
                ) from e
        
        # 创建所有表
        Base.metadata.create_all(self.engine)
        logger.info("Database tables initialized successfully")

    # --- 📈 1. 股价缓存逻辑 ---

    @monitor
    def get_cached_prices(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        尝试从数据库获取股价数据，返回 Pandas DataFrame (与 yfinance 格式兼容)
        """
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        with self.get_session() as session:
            stmt = select(StockPrice).where(
                StockPrice.ticker == ticker,
                StockPrice.date >= start,
                StockPrice.date <= end
            ).order_by(StockPrice.date)
            results = session.scalars(stmt).all()

            if not results:
                return pd.DataFrame()

            # 转换为 DataFrame
            data = [{
                "Date": r.date,
                "Open": r.open,
                "High": r.high,
                "Low": r.low,
                "Close": r.close,
                "Volume": r.volume
            } for r in results]
            
            df = pd.DataFrame(data)
            df.set_index("Date", inplace=True)
            return df

    @monitor
    def save_stock_data(self, ticker: str, df: pd.DataFrame, source: str = "yfinance"):
        """
        将 DataFrame 格式的 K 线数据存入数据库 (Upsert)
        """
        if df.empty: return

        records = []
        for date, row in df.iterrows():
            # 兼容 DataFrame index 为 date 的情况
            ts = date if isinstance(date, datetime) else pd.to_datetime(date)
            records.append({
                "ticker": ticker,
                "date": ts,
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
                "source": source,
                "resolution": "1d"
            })

        if not records: return

        with self.get_session() as session:
            # 使用 Postgres 的 ON CONFLICT DO NOTHING (避免重复报错)
            stmt = pg_insert(StockPrice).values(records)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=['ticker', 'date', 'resolution']
            )
            session.execute(stmt)
            session.commit()
            logger.info(f"[DB] Cached {len(records)} price records for {ticker}")

    # --- 📝 2. 报告归档逻辑 ---

    def save_analysis_report(self, run_id: str, ticker: str, role: str, content: str, report_type: str = "analysis", embedding: List[float] = None):
        """保存分析师报告或最终决策
        
        Args:
            run_id: 本次运行的唯一标识
            ticker: 股票代码
            role: Agent 角色名称
            content: 报告内容
            report_type: 报告类型，可选值: 'analysis'(分析), 'plan'(计划), 'critique'(评论)
            embedding: 向量嵌入
        """
        with self.get_session() as session:
            report = AnalysisReport(
                run_id=run_id,
                ticker=ticker,
                agent_role=role,
                report_type=report_type,
                content=content,
                embedding=embedding,
                date=datetime.now()
            )
            session.add(report)
            session.commit()
            logger.debug(f"Archived report for {role} (type: {report_type})")

    # --- 🧠 3. 记忆逻辑 (已实现) ---

    def save_lesson(self, situation: str, advice: str, embedding: List[float]):
        """保存一条经验教训"""
        with self.get_session() as session:
            lesson = TradingLesson(
                situation=situation,
                outcome_advice=advice,
                embedding=embedding
            )
            session.add(lesson)
            session.commit()

    def search_similar_lessons(self, query_embedding: List[float], limit: int = 3) -> List[TradingLesson]:
        """
        向量搜索：查找最相似的历史经验
        使用余弦相似度 (Cosine Similarity)
        """
        self._ensure_engine()
        with self.get_session() as session:
            # 使用 cosine_distance 排序 (pgvector 中的 <=> 操作符)
            # 1 - cosine_distance = cosine_similarity
            stmt = select(TradingLesson).order_by(
                TradingLesson.embedding.cosine_distance(query_embedding)
            ).limit(limit)
            
            return session.scalars(stmt).all()

    def get_latest_insider_sentiment(self, ticker: str, max_age_days: int = 90) -> Optional[Dict[str, Any]]:
        with self.get_session() as session:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            stmt = (
                select(InsiderActivity)
                .where(
                    InsiderActivity.ticker == ticker,
                    InsiderActivity.activity_type == "sentiment",
                    InsiderActivity.created_at >= cutoff_date,
                )
                .order_by(InsiderActivity.created_at.desc())
                .limit(1)
            )
            result = session.scalars(stmt).first()

            if not result:
                return None

            return {
                "ticker": result.ticker,
                "activity_type": result.activity_type,
                "sentiment_score": result.sentiment_score,
                "raw_data": result.raw_data,
                "source": result.source,
                "created_at": result.created_at.isoformat() if result.created_at else None,
            }

    def save_insider_sentiment(self, ticker: str, sentiment_score: Optional[float], raw_data: Dict[str, Any], source: str = "finnhub") -> None:
        with self.get_session() as session:
            record = InsiderActivity(
                ticker=ticker,
                activity_type="sentiment",
                sentiment_score=sentiment_score,
                raw_data=raw_data,
                source=source,
                created_at=datetime.now(),
            )
            session.add(record)
            session.commit()

    # --- 📁 4. 基本面数据逻辑 ---
    
    @monitor
    def get_cached_fundamentals(self, ticker: str, max_age_days: int = 1) -> Optional[Dict[str, Any]]:
        """
        从数据库获取缓存的基本面数据
        
        Args:
            ticker: 股票代码
            max_age_days: 最大年龄(天)，超过此年龄的数据不返回
            
        Returns:
            基本面数据字典或 None
        """
        with self.get_session() as session:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            
            stmt = select(FundamentalData).where(
                FundamentalData.ticker == ticker,
                FundamentalData.created_at >= cutoff_date
            ).order_by(FundamentalData.created_at.desc()).limit(1)
            
            result = session.scalars(stmt).first()
            
            if not result:
                return None
            
            # 转换为字典
            return {
                "company_name": result.company_name,
                "sector": result.sector,
                "industry": result.industry,
                "country": result.country,
                "exchange": result.exchange,
                "market_cap": result.market_cap,
                "pe_ratio": result.pe_ratio,
                "forward_pe": result.forward_pe,
                "pb_ratio": result.pb_ratio,
                "dividend_yield": result.dividend_yield,
                "beta": result.beta,
                "week_52_high": result.week_52_high,
                "week_52_low": result.week_52_low,
                "current_ratio": result.current_ratio,
                "debt_to_equity": result.debt_to_equity,
                "return_on_equity": result.return_on_equity,
                "profit_margins": result.profit_margins,
                "raw_data": result.raw_data,
                "source": result.source,
                "data_date": result.data_date,
            }
    
    @monitor
    def save_fundamentals(self, ticker: str, data: Dict[str, Any], source: str = "yfinance", data_date: Optional[datetime] = None):
        """
        保存基本面数据到数据库
        
        Args:
            ticker: 股票代码
            data: 基本面数据字典
            source: 数据来源
            data_date: 数据日期(默认今天)
        """
        if not data:
            return
        
        if data_date is None:
            data_date = datetime.now()
        
        with self.get_session() as session:
            record = {
                "ticker": ticker,
                "data_date": data_date,
                "company_name": data.get("company_name") or data.get("longName"),
                "sector": data.get("sector"),
                "industry": data.get("industry"),
                "country": data.get("country"),
                "exchange": data.get("exchange"),
                "market_cap": data.get("market_cap") or data.get("marketCap"),
                "pe_ratio": data.get("pe_ratio") or data.get("trailingPE"),
                "forward_pe": data.get("forward_pe") or data.get("forwardPE"),
                "pb_ratio": data.get("pb_ratio") or data.get("priceToBook"),
                "dividend_yield": data.get("dividend_yield") or data.get("dividendYield"),
                "beta": data.get("beta"),
                "week_52_high": data.get("week_52_high") or data.get("fiftyTwoWeekHigh"),
                "week_52_low": data.get("week_52_low") or data.get("fiftyTwoWeekLow"),
                "current_ratio": data.get("current_ratio") or data.get("currentRatio"),
                "debt_to_equity": data.get("debt_to_equity") or data.get("debtToEquity"),
                "return_on_equity": data.get("return_on_equity") or data.get("returnOnEquity"),
                "profit_margins": data.get("profit_margins") or data.get("profitMargins"),
                "raw_data": data,  # 保存完整原始数据
                "source": source,
            }
            
            stmt = pg_insert(FundamentalData).values(record)
            stmt = stmt.on_conflict_do_update(
                index_elements=['ticker', 'data_date', 'source'],
                set_={
                    "company_name": stmt.excluded.company_name,
                    "sector": stmt.excluded.sector,
                    "industry": stmt.excluded.industry,
                    "market_cap": stmt.excluded.market_cap,
                    "pe_ratio": stmt.excluded.pe_ratio,
                    "raw_data": stmt.excluded.raw_data,
                    "updated_at": datetime.now(),
                }
            )
            session.execute(stmt)
            session.commit()
            logger.info(f"[DB] Saved fundamentals for {ticker} from {source}")


# =============================================================================
# FastAPI Dependency Injection Helper (Sync)
# =============================================================================

def get_sync_db_session():
    """
    FastAPI dependency for database session (sync version).
    
    Usage:
        @router.get("/items")
        def get_items(db: Session = Depends(get_sync_db_session)):
            ...
    """
    db_manager = DBManager()
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


# =============================================================================
# Async Database Session Support
# =============================================================================

_async_engine = None
_async_session_factory = None


def _get_async_db_url() -> str:
    """Convert sync DB URL to async URL for asyncpg."""
    if not DB_URL:
        raise ValueError("DATABASE_URL not set")
    
    # Convert postgresql:// to postgresql+asyncpg://
    if DB_URL.startswith("postgresql://"):
        return DB_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif DB_URL.startswith("postgres://"):
        return DB_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif "asyncpg" in DB_URL:
        return DB_URL
    else:
        raise ValueError(f"Unsupported database URL format: {DB_URL}")


def _ensure_async_engine():
    """Lazily create async engine and session factory."""
    global _async_engine, _async_session_factory
    
    if _async_engine is None:
        async_url = _get_async_db_url()
        _async_engine = create_async_engine(
            async_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=20,      # 增加连接池大小
            max_overflow=40,    # 增加溢出连接数
            pool_recycle=3600,   # 1小时后回收连接（防止连接过期）
            pool_timeout=30,     # 获取连接超时30秒
            connect_args={}  # Keep empty for asyncpg compatibility
        )
        _async_session_factory = async_sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database session.
    
    Usage:
        async with get_db_session() as session:
            result = await session.execute(select(Model))
            ...
    """
    _ensure_async_engine()
    
    async with _async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
