"""
Intelligent Briefing News Service (RSS-Based Architecture)

High-speed, zero-cost news aggregation using RSS feeds:
- Yahoo Finance RSS: US/HK/SG individual stocks
- Sina Finance RSS: China A-Shares/Macro
- CoinTelegraph RSS: Crypto
- CNBC/OilPrice RSS: Commodities
- Reuters/Investing.com RSS: Global Macro

Features:
- Smart Funnel pre-processing to minimize LLM token usage
- Time-based filtering (24-48 hour window)
- Keyword-based filtering before LLM
- HTML stripping for clean summaries
- LRU cache with bounded size (prevents unbounded growth)
"""

import asyncio
from AICrews.observability.logging import get_logger
import os
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

try:
    from newspaper import Article as NewspaperArticle
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False
    NewspaperArticle = None

from AICrews.tools.smart_rss_tool import (
    NewsCategory,
    RSSNewsItem,
    Sentiment as RSSSentiment,
    SmartRSSTool,
    get_smart_rss_tool,
)
from AICrews.schemas.news import NewsSource, Sentiment

logger = get_logger(__name__)


@dataclass
class NewsItem:
    id: str
    title: str
    summary: str
    source: str
    url: str
    published_at: datetime
    tickers: List[str] = field(default_factory=list)
    sentiment: Sentiment = Sentiment.NEUTRAL
    news_type: str = "headline"
    language: str = "en"


class NewsService:
    """RSS-based news service with Smart Funnel pre-processing.
    
    This is a drop-in replacement for the previous yfinance/akshare implementation.
    Uses SmartRSSTool for high-speed, zero-cost news fetching.
    """
    
    def __init__(self, rss_tool: Optional[SmartRSSTool] = None):
        self._rss_tool = rss_tool or get_smart_rss_tool()

        # Cache configuration with bounded size (LRU eviction)
        self._max_cache_entries = int(os.getenv("FAIC_NEWS_CACHE_MAX_ENTRIES", "2000"))
        self._cache: OrderedDict[str, List[NewsItem]] = OrderedDict()
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)  # Reduced from 10 to 5 min
        self._update_lock = asyncio.Lock()
        self._updating = False
        logger.debug(
            "NewsService cache initialized: max_entries=%d ttl=%s",
            self._max_cache_entries,
            self._cache_ttl,
        )
    
    def is_cache_expired(self) -> bool:
        """Check if cache has expired."""
        if self._cache_timestamp is None:
            return True
        return datetime.now(timezone.utc) - self._cache_timestamp > self._cache_ttl
    
    async def get_headlines(
        self,
        tickers: Optional[List[str]] = None,
        news_types: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        max_age_hours: int = 24,
        force_refresh: bool = False,
        limit: int = 50,
    ) -> List[NewsItem]:
        """Fetch news headlines using RSS-based Smart Funnel.
        
        Args:
            tickers: Filter by stock symbols (e.g., ["AAPL", "0700.HK"])
            news_types: Filter by type: ['stock', 'crypto', 'commodity', 'macro']
            keywords: Filter by keywords (e.g., ["AI", "earnings"])
            max_age_hours: Maximum age of news in hours (default: 24)
            force_refresh: Bypass cache
            limit: Maximum number of results
        
        Returns:
            List of NewsItem objects, sorted by recency
        """
        cache_key = self._build_cache_key(tickers, news_types, keywords, limit)
        
        async with self._update_lock:
            if self._updating:
                while self._updating:
                    await asyncio.sleep(0.1)
                cached = self._cache.get(cache_key)
                if cached:
                    return cached[:limit]
            
            # Check cache first
            if not force_refresh and not self.is_cache_expired():
                cached = self._cache.get(cache_key)
                if cached:
                    return cached[:limit]
            
            self._updating = True
            try:
                news_items = await self._fetch_via_smart_rss(
                    tickers=tickers,
                    news_types=news_types,
                    keywords=keywords,
                    max_age_hours=max_age_hours,
                    limit=limit,
                    force_refresh=force_refresh,
                )
                self._set_cache(cache_key, news_items)
                self._cache_timestamp = datetime.now(timezone.utc)
                logger.info(f"RSS news cache updated: {len(news_items)} headlines")
                return news_items
            finally:
                self._updating = False
    
    def _build_cache_key(
        self,
        tickers: Optional[List[str]],
        news_types: Optional[List[str]],
        keywords: Optional[List[str]],
        limit: int,
    ) -> str:
        """Build cache key from query parameters."""
        parts = [
            "rss",
            ",".join(sorted(tickers or [])),
            ",".join(sorted(news_types or [])),
            ",".join(sorted(keywords or [])),
            str(limit),
        ]
        return ":".join(parts)

    def _set_cache(self, key: str, data: List[NewsItem]) -> None:
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
                "NewsService cache full (%d entries), evicted: %s",
                self._max_cache_entries,
                evicted_key[:50],  # Log first 50 chars
            )

        # Add new entry
        self._cache[key] = data

    async def _fetch_via_smart_rss(
        self,
        tickers: Optional[List[str]],
        news_types: Optional[List[str]],
        keywords: Optional[List[str]],
        max_age_hours: int,
        limit: int,
        force_refresh: bool,
    ) -> List[NewsItem]:
        """Fetch news using SmartRSSTool and convert to NewsItem format."""
        rss_items = await self._rss_tool.fetch_news(
            tickers=tickers,
            keywords=keywords,
            categories=news_types,
            max_age_hours=max_age_hours,
            limit=limit,
            force_refresh=force_refresh,
        )
        
        return [self._convert_rss_to_news_item(item) for item in rss_items]
    
    def _convert_rss_to_news_item(self, rss_item: RSSNewsItem) -> NewsItem:
        """Convert RSSNewsItem to NewsItem for backward compatibility."""
        # Map sentiment
        sentiment_map = {
            RSSSentiment.BULLISH: Sentiment.BULLISH,
            RSSSentiment.BEARISH: Sentiment.BEARISH,
            RSSSentiment.NEUTRAL: Sentiment.NEUTRAL,
        }
        
        return NewsItem(
            id=rss_item.id,
            title=rss_item.title,
            summary=rss_item.summary,
            source=rss_item.source,
            url=rss_item.url,
            published_at=rss_item.published_at,
            tickers=rss_item.tickers,
            sentiment=sentiment_map.get(rss_item.sentiment, Sentiment.NEUTRAL),
            news_type=rss_item.category.value,
            language="en" if not self._is_chinese(rss_item.title) else "zh",
        )
    
    def _is_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters."""
        import re
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    # Legacy methods removed - all fetching now delegated to SmartRSSTool
    # The Smart Funnel handles: time filtering, keyword filtering, HTML cleaning
    
    async def get_headlines_for_agent(
        self,
        tickers: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        max_age_hours: int = 24,
        limit: int = 20,
    ) -> str:
        """Convenience method for CrewAI agents - returns formatted string."""
        items = await self.get_headlines(
            tickers=tickers,
            news_types=categories,
            keywords=keywords,
            max_age_hours=max_age_hours,
            limit=limit,
        )
        return self._format_for_agent(items)
    
    def _format_for_agent(self, items: List[NewsItem]) -> str:
        """Format news items for LLM consumption."""
        if not items:
            return "No recent news found."
        
        lines = [f"📰 **{len(items)} News Items**\n"]
        for i, item in enumerate(items, 1):
            emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(
                item.sentiment.value, "⚪"
            )
            tickers = ", ".join(item.tickers[:3]) if item.tickers else "General"
            
            lines.append(
                f"{i}. {emoji} **{item.title}**\n"
                f"   📍 {tickers} | 📰 {item.source}\n"
                f"   {item.summary[:180]}...\n"
            )
        return "\n".join(lines)
    
    async def extract_article(self, url: str) -> Dict[str, Any]:
        """
        Extract article content using multi-layer strategy:
        1. newspaper3k (local, specialized for news)
        2. Jina AI Reader (free API, handles JS)
        3. Firecrawl (if API key available)
        4. BeautifulSoup fallback (basic HTML parsing)

        Args:
            url: Article URL to extract

        Returns:
            Dict with extracted content or error info
        """
        # Try extraction strategies in order
        extraction_strategies = [
            ("newspaper3k", self._extract_with_newspaper),
            ("jina_ai", self._extract_with_jina),
            ("firecrawl", self._extract_with_firecrawl),
            ("beautifulsoup", self._extract_with_bs4),
        ]
        
        for strategy_name, strategy_func in extraction_strategies:
            try:
                result = await strategy_func(url)
                if result and result.get("success"):
                    result["strategy"] = strategy_name  # Track which strategy succeeded
                    logger.info(f"Article extraction succeeded with {strategy_name}: {url}")
                    return result
                else:
                    error_msg = result.get("error", "Unknown error") if result else "No result"
                    logger.debug(f"Strategy {strategy_name} failed for {url}: {error_msg}")
            except Exception as e:
                logger.debug(f"Strategy {strategy_name} error for {url}: {e}")
                continue
        
        # All strategies failed
        return {
            "success": False,
            "url": url,
            "error": "无法提取文章内容，请跳转原文阅读",
        }

    async def _extract_with_newspaper(self, url: str) -> Dict[str, Any]:
        """Extract article using newspaper3k."""
        if not NEWSPAPER_AVAILABLE:
            return {"success": False, "error": "newspaper3k not available"}
        
        try:
            # Configure newspaper3k with custom headers
            config = {
                'browser_user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'request_timeout': 30,
                'memoize_articles': False,
                'fetch_images': False,  # Skip images for faster extraction
            }
            
            article = NewspaperArticle(url, config=config)
            article.download()
            article.parse()
            
            # Check if we got meaningful content
            if not article.text or len(article.text.strip()) < 200:
                return {
                    "success": False,
                    "error": "Content too short or empty",
                }
            
            return {
                "success": True,
                "title": article.title or "",
                "text": article.text,
                "top_image": article.top_image or "",
                "authors": article.authors or [],
                "url": url,
                "error": None,
                "is_blacklisted": False,
            }
        except Exception as e:
            logger.debug(f"newspaper3k extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _extract_with_jina(self, url: str) -> Dict[str, Any]:
        """Extract article using Jina AI Reader (free, no API key needed).

        Uses official Jina Reader API with:
        - ReaderLM-v2: Advanced model for clean HTML-to-Markdown conversion
        - X-Remove-All-Images: Strip all image tags
        - X-Exclude-Selector: Remove common ad/footer elements
        - Accept: application/json: Get structured JSON response

        Post-processes content to remove residual noise.
        """
        try:
            # Jina Reader URL format
            jina_url = f"https://r.jina.ai/http://{url.replace('https://', '').replace('http://', '')}"

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    jina_url,
                    headers={
                        # Use ReaderLM-v2 for better extraction quality
                        "X-Use-ReaderLM-v2": "true",
                        # Remove all images to save tokens
                        "X-Remove-All-Images": "true",
                        # Exclude common non-content elements
                        "X-Exclude-Selector": "nav, footer, header, aside, .ad, .ads, .advertisement, .social-share, .related-posts, .comments, .sidebar",
                        # Request JSON format for structured response
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()

                # Parse JSON response from Jina
                import json
                data = response.json()

                title = data.get("title", "") or ""
                content = data.get("content", data.get("markdown", "")) or ""

                # Fallback to text if content is empty
                if not content:
                    content = data.get("text", "") or response.text

                # Post-process to clean residual noise
                cleaned_content = self._clean_article_content(content)

                # Normalize paragraphs - merge broken lines, clear separation
                normalized_content = self._normalize_paragraphs(cleaned_content)

                # Check if we got meaningful content
                if len(normalized_content) < 200:
                    return {
                        "success": False,
                        "error": "Content too short",
                    }

                return {
                    "success": True,
                    "title": title,
                    "text": normalized_content,
                    "top_image": "",
                    "authors": data.get("authors", []) or [],
                    "url": url,
                    "error": None,
                }
        except json.JSONDecodeError:
            # Fallback to plain text parsing if JSON fails
            try:
                content = response.text.strip()
                lines = content.split('\n')
                title = lines[0].strip() if lines else ""
                text = '\n'.join(lines[1:]).strip() if len(lines) > 1 else content

                # Clean and normalize the text content
                cleaned_text = self._clean_article_content(text)
                normalized_text = self._normalize_paragraphs(cleaned_text)

                if len(normalized_text) < 200:
                    return {"success": False, "error": "Content too short"}

                return {
                    "success": True,
                    "title": title,
                    "text": normalized_text,
                    "top_image": "",
                    "authors": [],
                    "url": url,
                    "error": None,
                }
            except Exception as e:
                logger.debug(f"Jina AI text fallback failed: {e}")
                return {"success": False, "error": str(e)}
        except Exception as e:
            logger.debug(f"Jina AI extraction failed: {e}")
            return {"success": False, "error": str(e)}

    def _clean_article_content(self, raw_content: str) -> str:
        """Clean article content by removing residual noise from extraction.

        Removes common noise patterns:
        - Title separators (===== TITLE =====)
        - Navigation links ([Skip to...], [Menu], etc.)
        - Menu sections (Sections, Latest, Companies, etc.)
        - Social sharing links
        - Subscription forms
        - Privacy settings
        - Cookie consent dialogs
        - Footer content
        - Image placeholders
        """
        import re

        cleaned = raw_content

        # 1. Remove title separator lines (e.g., "===== TITLE =====")
        cleaned = re.sub(r'^=+\s*.+?\s*=+$', '', cleaned, flags=re.MULTILINE)

        # 2. Remove navigation/skip links
        nav_patterns = [
            r'\[Skip to [^\]]+\]',
            r'\[Menu\]',
            r'\[Search\]',
            r'\[Sections?\]',
            r'\[Latest\]',
            r'\[Companies?\]',
            r'\[Sectors?\]',
            r'\[Themes?\]',
            r'\[Insights?\]',
            r'\[GlobalData\]',
            r'\[WC\]',
            r'\[Left\]',
            r'\[Right\]',
        ]
        for pattern in nav_patterns:
            cleaned = re.sub(pattern, '', cleaned)

        # 3. Remove social sharing links
        share_patterns = [
            r'\[Share\s*\]',
            r'\[Copy Link\]',
            r'\[Share on X\]',
            r'\[Share on Linkedin\]',
            r'\[Share on Facebook\]',
            r'\[Share on Twitter\]',
        ]
        for pattern in share_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # 4. Remove subscription forms
        sub_patterns = [
            r'\[Sign up for our daily news round-up\]',
            r'\[Sign up\]',
            r'\[Give your business an edge.*?\]',
            r'\[Subscribe\]',
            r'\[Thank you for subscribing\]',
            r'\[View all newsletters\]',
            r'#### Sign up for our daily news round-up.*?(?=\n\n|\n#)',
        ]
        for pattern in sub_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)

        # 5. Remove privacy settings and cookie dialogs
        privacy_patterns = [
            r'\[Privacy Preference Center\]',
            r'\[We Value Your Privacy\]',
            r'\[More information\]',
            r'\[Allow All\]',
            r'\[Manage Consent Preferences\]',
            r'#### Strictly Necessary Cookies.*?(?=\n\n|$)',
            r'#### Functional Cookies.*?(?=\n\n|$)',
            r'#### Targeting Cookies.*?(?=\n\n|$)',
            r'#### Performance Cookies.*?(=\n\n|$)',
            r'\[View Cookies\]',
            r'\[Confirm My Choices\]',
            r'\[Accept All Cookies\]',
            r'\[Cookies Settings\]',
        ]
        for pattern in privacy_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)

        # 6. Remove image placeholders like "![Image N]" or "![Image N: description]"
        cleaned = re.sub(r'!\[Image \d+(?::[^\]]*)?\]', '', cleaned)

        # 7. Remove footer/utility links
        footer_patterns = [
            r'\[About us\]',
            r'\[Advertise with us\]',
            r'\[Contact us\]',
            r'\[Privacy policy\]',
            r'\[Terms and conditions\]',
            r'\[Sitemap\]',
            r'\[Powered by [^\]]+\]',
            r'© \d{4} [A-Za-z]+',
            r'\[Lost Password\]',
            r'\[Login\]',
            r'\[Register\]',
            r'\[Get new password\]',
            r'\[Registration is disabled\]',
        ]
        for pattern in footer_patterns:
            cleaned = re.sub(pattern, '', cleaned)

        # 8. Remove advertisement/promotional blocks
        promo_patterns = [
            r'#### Access deeper industry intelligence.*?(?=\n\n|#|\Z)',
            r'#### Sign up to the newsletter.*?(?=\n\n|#|\Z)',
            r'\[Find out more\]',
            r'\[Learn more about [^\]]+\]',
            r'\[Experience unmatched clarity.*?\]',
        ]
        for pattern in promo_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)

        # 9. Remove standalone URL lines (affiliate/tracking remnants)
        cleaned = re.sub(r'^https?://[^\s]*\s*$', '', cleaned, flags=re.MULTILINE)

        # 10. Remove empty markdown links [text](url) where text equals url or is generic
        cleaned = re.sub(r'\[([^\]]+)\]\(https?://[^\)]+\)', r'\1', cleaned)

        # 11. Clean up excessive whitespace and newlines
        cleaned = re.sub(r'\n{4,}', '\n\n\n', cleaned)  # Max 3 consecutive newlines
        cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)     # Multiple spaces to single
        cleaned = re.sub(r'^\s+|\s+$', '', cleaned, flags=re.MULTILINE)  # Trim lines

        # 12. Remove remaining menu-like sections (lines with just section names and dashes)
        lines = cleaned.split('\n')
        filtered_lines = []
        skip_pattern = re.compile(r'^[*\-—]\s*(Home|News|Analysis|Features|Projects|Data Insights|Energy|Construction Equipment|Civil Engineering|Artificial Intelligence|Cloud|Corporate Governance|Cybersecurity|Environmental Sustainability|Internet of Things|Robotics|Social Responsibility|Covid-19|Jobs|Filings|Patents|Social Media|Company A-Z|Company Categories|Products & Services|Company Releases|White Papers|Videos|Buyer\'s Guides|Partner Content|Webinar & Events|All Webinars & Events|Events|Webinars|On-Demand Webinars|Buy Reports|Excellence Awards|Innovation Rankings|Newsletters)$')

        for line in lines:
            stripped = line.strip()
            # Skip empty lines
            if not stripped:
                continue
            # Skip menu-like entries
            if skip_pattern.match(stripped):
                continue
            # Skip standalone section headers
            if re.match(r'^(Sections?|Latest|Companies?|Sectors?|Themes?|Insights?|GlobalData|Webinar & Events).*?[-—]+\s*$', stripped):
                continue
            filtered_lines.append(line)

        cleaned = '\n'.join(filtered_lines)

        # Final cleanup
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = cleaned.strip()

        return cleaned

    def _normalize_paragraphs(self, text: str) -> str:
        """Normalize paragraphs - merge broken lines, clear separation.

        处理逻辑：
        - 标题行（以 # 开头或全大写/短行）保持独立
        - 普通段落：合并被换行符分割的短行
        - 移除多余空行，保留清晰的段落分隔
        """
        import re

        lines = text.split('\n')
        normalized_lines = []
        current_paragraph = []

        def is_title_line(line: str) -> bool:
            """判断是否是标题行"""
            stripped = line.strip()
            # Markdown 标题
            if stripped.startswith('#'):
                return True
            # 全大写标题（通常是 section header）
            if stripped.isupper() and len(stripped) > 3 and len(stripped) < 100:
                return True
            # 短行且包含特定关键词（通常是导航/菜单）
            menu_keywords = ['sections', 'latest', 'companies', 'sectors', 'themes',
                           'insights', 'globaldata', 'menu', 'search']
            if len(stripped) < 30 and any(kw in stripped.lower() for kw in menu_keywords):
                return True
            return False

        def is_short_line(line: str) -> bool:
            """判断是否是短行（需要合并的段落行）"""
            stripped = line.strip()
            # 跳过空行和纯标点行
            if not stripped or len(stripped) < 10:
                return False
            # 跳过已经是标题格式的行
            if is_title_line(stripped):
                return False
            # 跳过列表项
            if stripped.startswith('- ') or stripped.startswith('* ') or stripped.startswith('• '):
                return False
            # 跳过带编号的列表
            if re.match(r'^\d+[\.\)]\s', stripped):
                return False
            # 段落行通常比较长，或者中等长度
            if len(stripped) > 60:
                return False  # 长行已经是完整句子
            return True  # 短行需要合并

        def flush_paragraph():
            """合并当前段落并添加到结果"""
            nonlocal current_paragraph
            if current_paragraph:
                # 合并段落行，用空格连接
                merged = ' '.join(current_paragraph)
                normalized_lines.append(merged)
                normalized_lines.append('')  # 空行分隔段落
            current_paragraph = []

        for line in lines:
            stripped = line.strip()

            # 空行处理
            if not stripped:
                flush_paragraph()
                continue

            # 标题行直接添加（不合并到段落）
            if is_title_line(stripped):
                flush_paragraph()
                normalized_lines.append(stripped)
                normalized_lines.append('')
                continue

            # 处理普通段落行
            if is_short_line(stripped):
                # 尝试修复行末的标点问题
                if current_paragraph:
                    last_line = current_paragraph[-1].rstrip()
                    if last_line and last_line[-1] not in '.!?,:;)]}':
                        # 不是完整句子，用空格连接
                        current_paragraph.append(stripped)
                    else:
                        # 是完整句子，可能需要合并（检查下一行是否相关）
                        current_paragraph.append(stripped)
                else:
                    current_paragraph.append(stripped)
            else:
                # 长行（可能是完整句子或标题）
                if len(stripped) < 30 and not is_title_line(stripped):
                    # 短的长行，可能是被错误分割的
                    current_paragraph.append(stripped)
                else:
                    flush_paragraph()
                    normalized_lines.append(stripped)
                    normalized_lines.append('')

        # 处理最后一个段落
        flush_paragraph()

        # 移除末尾空行，保留最多一个空行
        result = '\n'.join(normalized_lines)
        result = re.sub(r'\n{3,}', '\n\n', result)
        result = result.strip()

        return result

    async def _extract_with_firecrawl(self, url: str) -> Dict[str, Any]:
        """Extract article using Firecrawl (requires API key)."""
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            return {"success": False, "error": "Firecrawl API key not configured"}
        
        # Get Firecrawl configuration from environment
        api_url = os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev")
        timeout = int(os.getenv("FIRECRAWL_TIMEOUT", "30"))
        
        try:
            from crewai_tools import FirecrawlScrapeWebsiteTool
            
            # Initialize with API key from environment
            tool = FirecrawlScrapeWebsiteTool(api_key=api_key)
            
            # Configure additional parameters if needed
            result = tool.run(url)
            
            if isinstance(result, str):
                # Firecrawl returned text content
                return {
                    "success": True,
                    "title": "",
                    "text": result,
                    "top_image": "",
                    "authors": [],
                    "url": url,
                    "error": None,
                    "is_blacklisted": False,
                }
            elif isinstance(result, dict):
                # Firecrawl returned structured data
                return {
                    "success": True,
                    "title": result.get("title", ""),
                    "text": result.get("content", ""),
                    "top_image": result.get("image", ""),
                    "authors": result.get("authors", []),
                    "url": url,
                    "error": None,
                    "is_blacklisted": False,
                }
            else:
                return {"success": False, "error": "Unexpected Firecrawl response format"}
                
        except ImportError:
            return {"success": False, "error": "crewai-tools not available"}
        except Exception as e:
            logger.debug(f"Firecrawl extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _extract_with_bs4(self, url: str) -> Dict[str, Any]:
        """Fallback extraction using BeautifulSoup."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                from bs4 import BeautifulSoup
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Remove unwanted elements
                for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
                    element.decompose()
                
                # Try to find main content
                main_content = None
                for selector in ["article", "main", ".content", "#content", ".post", ".article", ".main"]:
                    main_content = soup.select_one(selector)
                    if main_content:
                        break
                
                if main_content:
                    text = main_content.get_text(separator="\n", strip=True)
                else:
                    text = soup.get_text(separator="\n", strip=True)
                
                # Clean up text
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                cleaned_text = "\n".join(lines)
                
                # Extract title
                title = ""
                if soup.title:
                    title = soup.title.string or ""
                
                # Check if we got meaningful content
                if len(cleaned_text) < 200:
                    return {
                        "success": False,
                        "error": "Content too short",
                    }
                
                return {
                    "success": True,
                    "title": title,
                    "text": cleaned_text,
                    "top_image": "",
                    "authors": [],
                    "url": url,
                    "error": None,
                    "is_blacklisted": False,
                }
        except Exception as e:
            logger.debug(f"BeautifulSoup extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._cache_timestamp = None
        self._rss_tool.clear_cache()


# 全局新闻服务实例
_news_service: Optional[NewsService] = None


def get_news_service() -> NewsService:
    """获取新闻服务单例"""
    global _news_service
    if _news_service is None:
        _news_service = NewsService()
    return _news_service
