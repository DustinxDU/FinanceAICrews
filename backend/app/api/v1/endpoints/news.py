"""
Intelligent Briefing API - 智能简报新闻接口

通过 MCP 服务器聚合全球金融新闻源:
- YFinance MCP: 美股/全球新闻
- Akshare MCP: A股/港股新闻
- OpenBB MCP: 市场概览新闻

Features:
- 多源新闻聚合
- 股票代码/新闻类型过滤
- 情感分析标签
- 自动缓存 (5分钟)
- 降级兜底数据
- 业务逻辑已下沉至 AICrews.services.news_service
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends

from AICrews.services.news_service import NewsService, get_news_service
from AICrews.schemas.news import (
    NewsItemResponse,
    NewsListResponse,
    NewsSourcesResponse,
    ArticleExtractResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/news",
    tags=["Intelligent Briefing - 智能简报"]
)

def _get_service() -> NewsService:
    """获取新闻服务单例"""
    return get_news_service()

@router.get("/headlines", response_model=NewsListResponse)
async def get_headlines(
    tickers: Optional[str] = Query(
        None,
        description="股票代码列表，逗号分隔 (如 AAPL,MSFT)"
    ),
    news_types: Optional[str] = Query(
        None,
        description="新闻类型: stock, crypto, commodity, macro"
    ),
    sources: Optional[str] = Query(
        None,
        description="新闻源: yfinance, akshare, openbb"
    ),
    limit: int = Query(50, ge=1, le=200),
    force_refresh: bool = Query(False, description="强制刷新缓存"),
    service: NewsService = Depends(_get_service),
):
    """获取新闻标题流
    
    聚合多个新闻源的最新头条，支持按股票代码和类型过滤。
    """
    try:
        tickers_list = [t.strip() for t in tickers.split(",") if t.strip()] if tickers else None
        news_types_list = [t.strip() for t in news_types.split(",") if t.strip()] if news_types else None

        # Note: `sources` is kept for backward compatibility
        _ = sources

        news_items = await service.get_headlines(
            tickers=tickers_list,
            news_types=news_types_list,
            force_refresh=force_refresh,
            limit=limit,
        )

        return NewsListResponse(
            news=[
                NewsItemResponse(
                    id=item.id,
                    title=item.title,
                    summary=item.summary,
                    source=item.source,
                    url=item.url,
                    published_at=item.published_at,
                    tickers=item.tickers,
                    sentiment=item.sentiment.value,
                    news_type=item.news_type,
                )
                for item in news_items
            ],
            total_count=len(news_items),
            cached=not force_refresh,
            last_updated=datetime.now().isoformat(),
            next_update_in_seconds=300,
        )
    except Exception as e:
        logger.error(f"获取新闻失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取新闻失败: {str(e)}")


@router.get("/stock/{ticker}", response_model=NewsListResponse)
async def get_stock_news(
    ticker: str,
    news_types: Optional[str] = Query(None, description="新闻类型过滤"),
    limit: int = Query(20, ge=1, le=100),
    force_refresh: bool = Query(False),
    service: NewsService = Depends(_get_service),
):
    """获取特定股票的新闻"""
    try:
        news_types_list = [t.strip() for t in news_types.split(",") if t.strip()] if news_types else None

        news_items = await service.get_headlines(
            tickers=[ticker.upper()],
            news_types=news_types_list,
            limit=limit,
            force_refresh=force_refresh,
        )

        return NewsListResponse(
            news=[
                NewsItemResponse(
                    id=item.id,
                    title=item.title,
                    summary=item.summary,
                    source=item.source,
                    url=item.url,
                    published_at=item.published_at,
                    tickers=item.tickers,
                    sentiment=item.sentiment.value,
                    news_type=item.news_type,
                )
                for item in news_items
            ],
            total_count=len(news_items),
            cached=not force_refresh,
            last_updated=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"获取股票 {ticker} 新闻失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取新闻失败: {str(e)}")


@router.get("/market", response_model=NewsListResponse)
async def get_market_news(
    limit: int = Query(30, ge=1, le=100),
    news_type: Optional[str] = Query(None, description="新闻类型: stock, crypto, commodity, macro"),
    force_refresh: bool = Query(False),
    service: NewsService = Depends(_get_service),
):
    """获取市场概览新闻"""
    try:
        news_types = [news_type] if news_type else None

        news_items = await service.get_headlines(
            tickers=None,
            news_types=news_types,
            limit=limit,
            force_refresh=force_refresh,
        )

        return NewsListResponse(
            news=[
                NewsItemResponse(
                    id=item.id,
                    title=item.title,
                    summary=item.summary,
                    source=item.source,
                    url=item.url,
                    published_at=item.published_at,
                    tickers=item.tickers,
                    sentiment=item.sentiment.value,
                    news_type=item.news_type,
                )
                for item in news_items
            ],
            total_count=len(news_items),
            cached=not force_refresh,
            last_updated=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"获取市场新闻失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取新闻失败: {str(e)}")


@router.get("/china", response_model=NewsListResponse)
async def get_china_news(
    limit: int = Query(30, ge=1, le=100),
    force_refresh: bool = Query(False),
    service: NewsService = Depends(_get_service),
):
    """获取中国/亚洲市场新闻"""
    try:
        # Sina RSS provides China stock + macro coverage
        news_items = await service.get_headlines(
            tickers=None,
            news_types=["stock", "macro"],
            limit=limit,
            force_refresh=force_refresh,
        )

        return NewsListResponse(
            news=[
                NewsItemResponse(
                    id=item.id,
                    title=item.title,
                    summary=item.summary,
                    source=item.source,
                    url=item.url,
                    published_at=item.published_at,
                    tickers=item.tickers,
                    sentiment=item.sentiment.value,
                    news_type=item.news_type,
                )
                for item in news_items
            ],
            total_count=len(news_items),
            cached=not force_refresh,
            last_updated=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"获取中国新闻失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取新闻失败: {str(e)}")


@router.get("/us", response_model=NewsListResponse)
async def get_us_news(
    tickers: Optional[str] = Query(None, description="美股代码列表"),
    limit: int = Query(30, ge=1, le=100),
    force_refresh: bool = Query(False),
    service: NewsService = Depends(_get_service),
):
    """获取美国市场新闻"""
    try:
        tickers_list = [t.strip() for t in tickers.split(",") if t.strip()] if tickers else None

        news_items = await service.get_headlines(
            tickers=tickers_list,
            news_types=["stock"],
            limit=limit,
            force_refresh=force_refresh,
        )

        return NewsListResponse(
            news=[
                NewsItemResponse(
                    id=item.id,
                    title=item.title,
                    summary=item.summary,
                    source=item.source,
                    url=item.url,
                    published_at=item.published_at,
                    tickers=item.tickers,
                    sentiment=item.sentiment.value,
                    news_type=item.news_type,
                )
                for item in news_items
            ],
            total_count=len(news_items),
            cached=not force_refresh,
            last_updated=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"获取美股新闻失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取新闻失败: {str(e)}")


@router.get("/sentiment/{ticker}", response_model=Dict[str, Any])
async def get_stock_sentiment(
    ticker: str,
    limit: int = Query(20, ge=1, le=100),
    service: NewsService = Depends(_get_service),
):
    """获取股票情感分析摘要"""
    try:
        news_items = await service.get_headlines(
            tickers=[ticker.upper()],
            limit=limit,
        )
        
        if not news_items:
            return {
                "ticker": ticker.upper(),
                "total_news": 0,
                "sentiment_distribution": {"bullish": 0, "bearish": 0, "neutral": 0},
                "overall_sentiment": "neutral",
                "top_news": [],
            }
        
        sentiment_counts = {"bullish": 0, "bearish": 0, "neutral": 0}
        for item in news_items:
            sentiment_counts[item.sentiment.value] += 1
        
        total = len(news_items)
        bullish_ratio = sentiment_counts["bullish"] / total
        bearish_ratio = sentiment_counts["bearish"] / total
        
        if bullish_ratio > 0.6:
            overall = "bullish"
        elif bearish_ratio > 0.6:
            overall = "bearish"
        else:
            overall = "neutral"
        
        return {
            "ticker": ticker.upper(),
            "total_news": total,
            "sentiment_distribution": sentiment_counts,
            "overall_sentiment": overall,
            "bullish_ratio": f"{bullish_ratio:.1%}",
            "bearish_ratio": f"{bearish_ratio:.1%}",
            "top_news": [
                {
                    "title": item.title,
                    "sentiment": item.sentiment.value,
                    "source": item.source,
                    "published_at": item.published_at.isoformat(),
                }
                for item in news_items[:5]
            ],
        }
    except Exception as e:
        logger.error(f"获取情感分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取情感分析失败: {str(e)}")


@router.get("/sources/status", response_model=NewsSourcesResponse)
async def get_sources_status(
    service: NewsService = Depends(_get_service),
):
    """获取新闻源状态"""
    status: Dict[str, Dict[str, Any]] = {}

    async def _check(name: str, news_types: Optional[List[str]] = None) -> None:
        try:
            items = await service.get_headlines(news_types=news_types, limit=1, force_refresh=False)
            status[name] = {
                "available": len(items) > 0,
                "last_check": datetime.now().isoformat(),
                "type": ",".join(news_types) if news_types else "all",
            }
        except Exception as e:
            status[name] = {
                "available": False,
                "error": str(e),
                "last_check": datetime.now().isoformat(),
                "type": ",".join(news_types) if news_types else "all",
            }

    import asyncio
    await asyncio.gather(
        _check("yahoo_rss", ["stock"]),
        _check("sina_rss", ["stock", "macro"]),
        _check("cointelegraph_rss", ["crypto"]),
        _check("cnbc_rss", ["commodity"]),
    )

    return NewsSourcesResponse(sources=status)


@router.post("/refresh")
async def refresh_news(
    tickers: Optional[str] = Query(None),
    news_types: Optional[str] = Query(None),
    service: NewsService = Depends(_get_service),
):
    """强制刷新新闻缓存"""
    try:
        tickers_list = [t.strip() for t in tickers.split(",") if t.strip()] if tickers else None
        news_types_list = [t.strip() for t in news_types.split(",") if t.strip()] if news_types else None

        news_items = await service.get_headlines(
            tickers=tickers_list,
            news_types=news_types_list,
            force_refresh=True,
            limit=50,
        )

        return {
            "success": True,
            "refreshed_count": len(news_items),
            "refreshed_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"刷新新闻失败: {e}")
        raise HTTPException(status_code=500, detail=f"刷新新闻失败: {str(e)}")


@router.get("/extract", response_model=ArticleExtractResponse)
async def extract_article(
    url: str = Query(..., description="要提取正文的文章 URL"),
    service: NewsService = Depends(_get_service),
):
    """提取文章正文内容"""
    return await service.extract_article(url)
