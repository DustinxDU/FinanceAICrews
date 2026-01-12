"""
SmartRSSTool - High-speed, zero-cost RSS-based news fetching with Smart Funnel pre-processing.

Replaces expensive yfinance/akshare API calls with RSS feeds:
- Yahoo Finance RSS for US/HK/SG individual stocks
- Sina Finance RSS for China A-Shares/Macro
- CoinTelegraph RSS for Crypto
- OilPrice/CNBC RSS for Commodities

Features:
- Time-based filtering (24-48 hour window)
- Keyword-based pre-filtering (before LLM processing)
- HTML stripping for clean summaries
- Async parallel fetching
- Graceful error handling with fallbacks
- LRU cache with bounded size (prevents unbounded growth)
"""

import asyncio
import hashlib
import re
import os
import threading
import yaml
from collections import OrderedDict

from AICrews.observability.logging import get_logger
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set

import feedparser
import httpx
from bs4 import BeautifulSoup

logger = get_logger(__name__)


class NewsCategory(str, Enum):
    STOCK = "stock"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    MACRO = "macro"


class Sentiment(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class RSSNewsItem:
    """Clean, processed news item ready for LLM consumption."""
    id: str
    title: str
    summary: str
    source: str
    url: str
    published_at: datetime
    tickers: List[str] = field(default_factory=list)
    sentiment: Sentiment = Sentiment.NEUTRAL
    category: NewsCategory = NewsCategory.STOCK
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "url": self.url,
            "published_at": self.published_at.isoformat(),
            "tickers": self.tickers,
            "sentiment": self.sentiment.value,
            "category": self.category.value,
            "keywords": self.keywords,
        }


@dataclass
class RSSFeedConfig:
    """Configuration for an RSS feed source."""
    url: str
    source_name: str
    category: NewsCategory
    max_items: int = 20
    timeout: float = 15.0


class SmartRSSTool:
    """
    High-performance RSS-based news fetcher with Smart Funnel pre-processing.
    
    Smart Funnel Pipeline:
    1. Fetcher: Async parallel RSS fetching with feedparser
    2. Filter A (Time): Discard items older than max_age_hours
    3. Filter B (Keywords): Python string matching before LLM processing
    4. Cleaner: BeautifulSoup HTML stripping
    5. Deduplication: Title-based similarity detection
    
    Usage:
        tool = SmartRSSTool()
        news = await tool.fetch_news(
            tickers=["AAPL", "MSFT"],
            keywords=["AI", "earnings"],
            categories=["stock", "macro"],
            max_age_hours=24,
            limit=20
        )
    """

    # RSS Feed Registry
    RSS_FEEDS: Dict[str, RSSFeedConfig] = {}
    
    # Sentiment analysis keywords
    BULLISH_KEYWORDS: Set[str] = set()
    BEARISH_KEYWORDS: Set[str] = set()

    def __init__(
        self,
        default_max_age_hours: int = 48,
        request_timeout: float = 15.0,
        max_concurrent_requests: int = 10,
    ):
        self.default_max_age_hours = default_max_age_hours
        self.request_timeout = request_timeout
        self.max_concurrent_requests = max_concurrent_requests
        
        # 初始化配置
        self._load_config()

    def _load_config(self):
        """从外部配置文件加载 RSS 和关键词配置"""
        # 加载配置文件
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        config_path = os.path.join(project_root, "config/tools/rss_config.yaml")
        
        tools_config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    tools_config = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Error loading RSS config: {e}")
        else:
            logger.warning(f"RSS config file not found: {config_path}")

        # 加载 RSS feeds
        feeds_data = tools_config.get("rss_feeds", {})
        for key, cfg in feeds_data.items():
            self.RSS_FEEDS[key] = RSSFeedConfig(
                url=cfg["url"],
                source_name=cfg["source_name"],
                category=NewsCategory(cfg["category"]),
                max_items=cfg.get("max_items", 20)
            )
            
        # 加载情感关键词
        sentiment_data = tools_config.get("sentiment_keywords", {})
        self.BULLISH_KEYWORDS.update(sentiment_data.get("bullish", []))
        self.BEARISH_KEYWORDS.update(sentiment_data.get("bearish", []))

        # Per-loop semaphore management (avoids "bound to different event loop" errors)
        # When tools use ThreadPoolExecutor + asyncio.run, each call creates a new loop
        # A single Semaphore bound to one loop will fail in other loops
        self._semaphores: Dict[int, asyncio.Semaphore] = {}
        self._semaphore_lock = threading.Lock()

        # Cache configuration with bounded size (LRU eviction)
        self._max_cache_entries = int(os.getenv("FAIC_RSS_CACHE_MAX_ENTRIES", "1000"))
        self._cache: OrderedDict[str, tuple] = OrderedDict()  # (data, timestamp)
        self._cache_ttl = timedelta(minutes=5)
        logger.debug(
            "SmartRSSTool cache initialized: max_entries=%d ttl=%s",
            self._max_cache_entries,
            self._cache_ttl,
        )

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create a semaphore for the current event loop.

        This avoids "bound to different event loop" errors when tools
        use ThreadPoolExecutor + asyncio.run to create new loops.
        """
        loop_id = id(asyncio.get_running_loop())

        with self._semaphore_lock:
            if loop_id not in self._semaphores:
                self._semaphores[loop_id] = asyncio.Semaphore(self.max_concurrent_requests)
            return self._semaphores[loop_id]

    async def fetch_news(
        self,
        tickers: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        max_age_hours: Optional[int] = None,
        limit: int = 50,
        force_refresh: bool = False,
    ) -> List[RSSNewsItem]:
        """
        Fetch and filter news from RSS feeds.

        Args:
            tickers: Stock symbols to fetch (e.g., ["AAPL", "0700.HK"])
            keywords: Keywords to filter by (e.g., ["AI", "earnings"])
            categories: News categories (stock, crypto, commodity, macro)
            max_age_hours: Maximum age of news items in hours
            limit: Maximum number of items to return
            force_refresh: Bypass cache

        Returns:
            List of cleaned, filtered RSSNewsItem objects
        """
        max_age = max_age_hours or self.default_max_age_hours
        target_categories = self._parse_categories(categories)
        
        # Build fetch tasks based on requested categories and tickers
        tasks = self._build_fetch_tasks(tickers, target_categories, force_refresh)
        
        # Parallel fetch all feeds
        all_items: List[RSSNewsItem] = []
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"RSS fetch error: {result}")
            elif result:
                all_items.extend(result)

        # Apply Smart Funnel
        filtered_items = self._apply_smart_funnel(
            items=all_items,
            tickers=tickers,
            keywords=keywords,
            target_categories=target_categories,
            max_age_hours=max_age,
        )

        # Deduplicate and sort
        unique_items = self._deduplicate(filtered_items)
        sorted_items = sorted(unique_items, key=lambda x: x.published_at, reverse=True)

        return sorted_items[:limit]

    def _parse_categories(self, categories: Optional[List[str]]) -> List[NewsCategory]:
        """Parse category strings to NewsCategory enum."""
        if not categories:
            return list(NewsCategory)
        result = []
        for cat in categories:
            try:
                result.append(NewsCategory(cat.lower()))
            except ValueError:
                logger.warning(f"Unknown category: {cat}")
        return result or list(NewsCategory)

    def _build_fetch_tasks(
        self,
        tickers: Optional[List[str]],
        categories: List[NewsCategory],
        force_refresh: bool,
    ) -> List[asyncio.Task]:
        """Build async fetch tasks based on requested data."""
        tasks = []

        # Yahoo Finance for individual stock tickers
        if tickers and NewsCategory.STOCK in categories:
            for ticker in tickers[:10]:  # Limit to 10 tickers
                tasks.append(self._fetch_yahoo_stock(ticker, force_refresh))

        # Category-based feeds
        category_feeds = {
            NewsCategory.STOCK: ["sina_finance", "eastmoney_stock", "marketwatch_stocks"],
            NewsCategory.MACRO: ["caixin_macro", "reuters_business", "investing_news", "marketwatch_top", "google_news_business"],
            NewsCategory.CRYPTO: ["cointelegraph", "coindesk"],
            NewsCategory.COMMODITY: ["cnbc_commodities", "cnbc_energy"],
        }

        for category in categories:
            feeds = category_feeds.get(category, [])
            for feed_key in feeds:
                if feed_key in self.RSS_FEEDS:
                    config = self.RSS_FEEDS[feed_key]
                    tasks.append(self._fetch_rss_feed(config, force_refresh))

        return tasks

    async def _fetch_yahoo_stock(
        self, ticker: str, force_refresh: bool = False
    ) -> List[RSSNewsItem]:
        """Fetch news for a specific stock ticker from Yahoo Finance RSS."""
        cache_key = f"yahoo_{ticker}"
        
        if not force_refresh:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
        items = await self._fetch_and_parse_rss(
            url=url,
            source_name="Yahoo Finance",
            category=NewsCategory.STOCK,
            default_ticker=ticker,
        )
        
        self._set_cache(cache_key, items)
        return items

    async def _fetch_rss_feed(
        self, config: RSSFeedConfig, force_refresh: bool = False
    ) -> List[RSSNewsItem]:
        """Fetch and parse a generic RSS feed."""
        cache_key = f"rss_{config.source_name}_{config.category.value}"
        
        if not force_refresh:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        items = await self._fetch_and_parse_rss(
            url=config.url,
            source_name=config.source_name,
            category=config.category,
            max_items=config.max_items,
            timeout=config.timeout,
        )
        
        self._set_cache(cache_key, items)
        return items

    async def _fetch_and_parse_rss(
        self,
        url: str,
        source_name: str,
        category: NewsCategory,
        default_ticker: Optional[str] = None,
        max_items: int = 20,
        timeout: float = 15.0,
    ) -> List[RSSNewsItem]:
        """Core RSS fetching and parsing with error handling."""
        async with self._get_semaphore():
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "application/rss+xml, application/xml, text/xml, */*",
                    }
                    response = await client.get(url, headers=headers, follow_redirects=True)
                    response.raise_for_status()
                    content = response.text

                # Parse RSS feed
                feed = feedparser.parse(content)
                if feed.bozo and not feed.entries:
                    logger.warning(f"RSS parse error for {url}: {feed.bozo_exception}")
                    return []

                items = []
                for entry in feed.entries[:max_items]:
                    item = self._parse_entry(entry, source_name, category, default_ticker)
                    if item:
                        items.append(item)

                logger.debug(f"Fetched {len(items)} items from {source_name}")
                return items

            except httpx.TimeoutException:
                logger.warning(f"Timeout fetching RSS: {url}")
                return []
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error {e.response.status_code} for {url}")
                return []
            except Exception as e:
                logger.warning(f"Error fetching RSS {url}: {e}")
                return []

    def _parse_entry(
        self,
        entry: Any,
        source_name: str,
        category: NewsCategory,
        default_ticker: Optional[str] = None,
    ) -> Optional[RSSNewsItem]:
        """Parse a single RSS entry into RSSNewsItem."""
        try:
            # Extract title
            title = entry.get("title", "").strip()
            if not title:
                return None

            # Extract and clean summary (Filter D: HTML Cleaner)
            raw_summary = entry.get("summary", entry.get("description", ""))
            summary = self._clean_html(raw_summary)[:500]

            # Parse publication date
            published_at = self._parse_date(entry)

            # Extract URL
            url = entry.get("link", entry.get("href", ""))

            # Generate unique ID
            item_id = self._generate_id(title, source_name, published_at)

            # Extract tickers from content
            tickers = self._extract_tickers(title + " " + summary)
            if default_ticker and default_ticker not in tickers:
                tickers.insert(0, default_ticker)

            # Analyze sentiment
            sentiment = self._analyze_sentiment(title + " " + summary)

            # Extract keywords for filtering
            keywords = self._extract_keywords(title + " " + summary)

            return RSSNewsItem(
                id=item_id,
                title=title,
                summary=summary,
                source=source_name,
                url=url,
                published_at=published_at,
                tickers=tickers,
                sentiment=sentiment,
                category=category,
                keywords=keywords,
            )

        except Exception as e:
            logger.debug(f"Error parsing RSS entry: {e}")
            return None

    def _clean_html(self, raw_text: str) -> str:
        """Strip HTML tags and clean text using BeautifulSoup."""
        if not raw_text:
            return ""
        try:
            soup = BeautifulSoup(raw_text, "html.parser")
            # Remove script and style elements
            for element in soup(["script", "style", "iframe"]):
                element.decompose()
            # Get text and clean whitespace
            text = soup.get_text(separator=" ")
            text = re.sub(r"\s+", " ", text).strip()
            return text
        except Exception as e:
            logger.debug(f"BeautifulSoup HTML parsing failed, using regex fallback: {e}")
            # Fallback: simple regex-based HTML stripping
            text = re.sub(r"<[^>]+>", " ", raw_text)
            return re.sub(r"\s+", " ", text).strip()

    def _parse_date(self, entry: Any) -> datetime:
        """Parse publication date from RSS entry."""
        now = datetime.now(timezone.utc)
        
        # Try published_parsed first
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass

        # Try updated_parsed
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass

        # Try parsing string dates
        for date_field in ["published", "updated", "pubDate"]:
            date_str = entry.get(date_field, "")
            if date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    return parsedate_to_datetime(date_str)
                except Exception as e:
                    logger.debug(f"Failed to parse date field '{date_field}': {e}")

        return now

    def _generate_id(self, title: str, source: str, published: datetime) -> str:
        """Generate unique ID for news item."""
        content = f"{title}_{source}_{published.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _extract_tickers(self, text: str) -> List[str]:
        """Extract stock ticker symbols from text."""
        tickers = []
        
        patterns = [
            # US stocks
            r"\b([A-Z]{1,5})\b(?=\s+(?:stock|shares|Inc|Corp|Ltd))",
            r"\$([A-Z]{1,5})\b",
            # HK stocks
            r"\b(\d{4,5})\.HK\b",
            r"\b(\d{4,5})\.?(?:HK|hk)\b",
            # China A-shares
            r"\b(\d{6})\.(?:SH|SZ|SS)\b",
            # Crypto
            r"\b(BTC|ETH|SOL|XRP|ADA|DOGE|DOT|AVAX|MATIC|LINK)-?USD\b",
            # Commodities
            r"\b(GC|SI|CL|NG|HG)=F\b",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            tickers.extend([m.upper() for m in matches if isinstance(m, str)])

        # Known company name mappings
        name_to_ticker = {
            "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
            "amazon": "AMZN", "nvidia": "NVDA", "meta": "META", "tesla": "TSLA",
            "alibaba": "BABA", "tencent": "0700.HK", "bitcoin": "BTC",
            "ethereum": "ETH", "gold": "GC=F", "oil": "CL=F", "crude": "CL=F",
        }
        
        text_lower = text.lower()
        for name, ticker in name_to_ticker.items():
            if name in text_lower and ticker not in tickers:
                tickers.append(ticker)

        return list(dict.fromkeys(tickers))[:5]  # Dedupe, limit to 5

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords for filtering."""
        keywords = []
        text_lower = text.lower()

        keyword_patterns = [
            "earnings", "revenue", "profit", "guidance", "forecast",
            "merger", "acquisition", "ipo", "dividend", "buyback",
            "fed", "rate", "inflation", "gdp", "employment", "cpi", "pmi",
            "ai", "artificial intelligence", "machine learning",
            "regulation", "sec", "lawsuit", "investigation",
            "upgrade", "downgrade", "target price", "analyst",
        ]

        for kw in keyword_patterns:
            if kw in text_lower:
                keywords.append(kw)

        return keywords[:10]

    def _analyze_sentiment(self, text: str) -> Sentiment:
        """Rule-based sentiment analysis."""
        text_lower = text.lower()
        
        bullish_score = sum(1 for kw in self.BULLISH_KEYWORDS if kw in text_lower)
        bearish_score = sum(1 for kw in self.BEARISH_KEYWORDS if kw in text_lower)

        if bullish_score > bearish_score + 1:
            return Sentiment.BULLISH
        elif bearish_score > bullish_score + 1:
            return Sentiment.BEARISH
        return Sentiment.NEUTRAL

    def _apply_smart_funnel(
        self,
        items: List[RSSNewsItem],
        tickers: Optional[List[str]],
        keywords: Optional[List[str]],
        target_categories: List[NewsCategory],
        max_age_hours: int,
    ) -> List[RSSNewsItem]:
        """
        Apply Smart Funnel filters to reduce token usage.
        
        Pipeline:
        1. Filter A (Time): Remove items older than max_age_hours
        2. Filter B (Keywords): Match requested keywords
        3. Filter C (Tickers): Match requested tickers
        4. Filter D (Categories): Match requested categories
        """
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=max_age_hours)
        
        filtered = []
        for item in items:
            # Make published_at timezone-aware for comparison
            pub_time = item.published_at
            if pub_time.tzinfo is None:
                pub_time = pub_time.replace(tzinfo=timezone.utc)

            # Filter A: Time filter
            if pub_time < cutoff_time:
                continue

            # Filter B: Category filter
            if item.category not in target_categories:
                continue

            # Filter C: Keyword filter (if specified)
            if keywords:
                text_lower = (item.title + " " + item.summary).lower()
                if not any(kw.lower() in text_lower for kw in keywords):
                    continue

            # Filter D: Ticker filter (if specified)
            if tickers:
                # Check if any requested ticker matches item's tickers
                item_tickers_upper = [it.upper() for it in item.tickers]
                ticker_match = any(t.upper() in item_tickers_upper for t in tickers)
                
                # Also check if ticker appears in title/summary for broader matching
                text_lower = (item.title + " " + item.summary).lower()
                text_match = any(t.lower() in text_lower for t in tickers)
                
                # Strict filtering: only include news that mentions the ticker
                if not ticker_match and not text_match:
                    continue

            filtered.append(item)

        logger.debug(f"Smart Funnel: {len(items)} -> {len(filtered)} items")
        return filtered

    def _deduplicate(self, items: List[RSSNewsItem]) -> List[RSSNewsItem]:
        """Remove duplicate news items based on title similarity."""
        seen_titles: Set[str] = set()
        unique = []
        
        for item in items:
            # Normalize title for comparison
            normalized = re.sub(r"[^\w\s]", "", item.title.lower())[:80]
            if normalized and normalized not in seen_titles:
                seen_titles.add(normalized)
                unique.append(item)

        return unique

    def _get_cached(self, key: str) -> Optional[List[RSSNewsItem]]:
        """Get cached data if not expired."""
        if key not in self._cache:
            return None
        data, timestamp = self._cache[key]
        if datetime.now(timezone.utc) - timestamp > self._cache_ttl:
            del self._cache[key]
            return None
        return data

    def _set_cache(self, key: str, data: List[RSSNewsItem]) -> None:
        """Set cache entry with LRU eviction.

        Implements bounded cache:
        - If cache is full, evict the oldest entry (FIFO/LRU)
        - Move accessed key to end (mark as recently used)
        """
        # If key exists, move it to end (mark as recently used)
        if key in self._cache:
            self._cache.move_to_end(key)

        # If cache is full, evict oldest entry
        if len(self._cache) >= self._max_cache_entries:
            evicted_key, _ = self._cache.popitem(last=False)  # Remove oldest (FIFO)
            logger.debug(
                "SmartRSSTool cache full (%d entries), evicted: %s",
                self._max_cache_entries,
                evicted_key[:50],  # Log first 50 chars
            )

        # Add new entry
        self._cache[key] = (data, datetime.now(timezone.utc))

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()


# Singleton instance
_smart_rss_tool: Optional[SmartRSSTool] = None


def get_smart_rss_tool() -> SmartRSSTool:
    """Get singleton SmartRSSTool instance."""
    global _smart_rss_tool
    if _smart_rss_tool is None:
        _smart_rss_tool = SmartRSSTool()
    return _smart_rss_tool


# CrewAI Tool wrapper for Agent integration
class SmartRSSCrewTool:
    """
    CrewAI-compatible tool wrapper for SmartRSSTool.
    
    Usage with CrewAI Agent:
        from crewai import Agent, Tool
        
        rss_tool = SmartRSSCrewTool()
        
        agent = Agent(
            role="News Analyst",
            goal="Gather and analyze market news",
            tools=[rss_tool.as_tool()],
        )
    """

    def __init__(self, tool: Optional[SmartRSSTool] = None):
        self.tool = tool or get_smart_rss_tool()

    def as_tool(self):
        """Return CrewAI Tool object."""
        from crewai_tools import tool as crewai_tool

        @crewai_tool("Fetch Market News")
        def fetch_market_news(
            tickers: str = "",
            keywords: str = "",
            categories: str = "stock,macro",
            max_age_hours: int = 24,
            limit: int = 20,
        ) -> str:
            """
            Fetch latest market news from RSS feeds with smart filtering.
            
            Args:
                tickers: Comma-separated stock symbols (e.g., "AAPL,MSFT,0700.HK")
                keywords: Comma-separated keywords to filter (e.g., "AI,earnings")
                categories: Comma-separated categories: stock,crypto,commodity,macro
                max_age_hours: Maximum age of news in hours (default: 24)
                limit: Maximum number of news items (default: 20)
            
            Returns:
                Formatted news summary ready for analysis
            """
            import asyncio
            
            ticker_list = [t.strip() for t in tickers.split(",") if t.strip()] or None
            keyword_list = [k.strip() for k in keywords.split(",") if k.strip()] or None
            category_list = [c.strip() for c in categories.split(",") if c.strip()]
            
            # Run async fetch
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.tool.fetch_news(
                            tickers=ticker_list,
                            keywords=keyword_list,
                            categories=category_list,
                            max_age_hours=max_age_hours,
                            limit=limit,
                        )
                    )
                    news_items = future.result()
            else:
                news_items = loop.run_until_complete(
                    self.tool.fetch_news(
                        tickers=ticker_list,
                        keywords=keyword_list,
                        categories=category_list,
                        max_age_hours=max_age_hours,
                        limit=limit,
                    )
                )
            
            # Format output for LLM consumption
            return self._format_news_for_llm(news_items)

        return fetch_market_news

    def _format_news_for_llm(self, items: List[RSSNewsItem]) -> str:
        """Format news items into concise text for LLM processing."""
        if not items:
            return "No recent news found matching the criteria."

        lines = [f"📰 **{len(items)} News Items Found**\n"]
        
        for i, item in enumerate(items, 1):
            sentiment_emoji = {
                Sentiment.BULLISH: "🟢",
                Sentiment.BEARISH: "🔴",
                Sentiment.NEUTRAL: "⚪",
            }.get(item.sentiment, "⚪")
            
            tickers_str = ", ".join(item.tickers[:3]) if item.tickers else "General"
            time_ago = self._time_ago(item.published_at)
            
            lines.append(
                f"{i}. {sentiment_emoji} **{item.title}**\n"
                f"   📍 {tickers_str} | ⏰ {time_ago} | 📰 {item.source}\n"
                f"   {item.summary[:200]}{'...' if len(item.summary) > 200 else ''}\n"
            )

        return "\n".join(lines)

    def _time_ago(self, dt: datetime) -> str:
        """Convert datetime to human-readable time ago string."""
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        diff = now - dt
        hours = diff.total_seconds() / 3600
        
        if hours < 1:
            return f"{int(diff.total_seconds() / 60)}m ago"
        elif hours < 24:
            return f"{int(hours)}h ago"
        else:
            return f"{int(hours / 24)}d ago"
