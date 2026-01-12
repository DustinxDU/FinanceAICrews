"""
External Tools - 独立工具函数模块

提供独立的工具函数，用于网络搜索和网页抓取：
- web_search: 网络搜索（优先使用 Serper API，回退到 DuckDuckGo）
- duckduckgo_search: DuckDuckGo 搜索（免费，无需 API key）
- scrape_website: 网页内容抓取
- search_financial_news: 金融新闻搜索
- search_company_info: 公司信息搜索

使用方式:
    from AICrews.tools.external_tools import web_search, duckduckgo_search
    
    # 直接调用工具函数
    result = web_search("AAPL stock news")
    
    # 或通过 LoadoutResolver + ToolsFactory 加载
    from AICrews.services.loadout_resolver import LoadoutResolver
    resolver = LoadoutResolver(session, user_id)
    result = resolver.resolve(["cap:web_search"])
    tools = result.tools
"""

import os
from AICrews.observability.logging import get_logger
import warnings
from typing import List, Optional, Dict, Any

from crewai.tools import tool

logger = get_logger(__name__)

# Import DDGS at module level for cleaner mocking
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None




# =========================================================================
# 内置工具函数（作为 crewai_tools 的 fallback）
# =========================================================================

@tool("web_search")
def web_search(query: str, num_results: int = 5) -> str:
    """搜索互联网获取最新信息
    
    使用网络搜索引擎查找与查询相关的信息。
    对于获取最新新闻、市场动态、公司公告等特别有用。
    
    Args:
        query: 搜索查询词
        num_results: 返回结果数量，默认5条
        
    Returns:
        搜索结果摘要
    """
    import urllib.parse
    
    # 首先尝试使用 Serper API
    serper_key = os.getenv("SERPER_API_KEY")
    if serper_key:
        try:
            import httpx
            
            response = httpx.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                json={"q": query, "num": num_results},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                # 处理自然搜索结果
                for item in data.get("organic", [])[:num_results]:
                    results.append(f"**{item.get('title', 'No title')}**\n{item.get('snippet', '')}\nURL: {item.get('link', '')}")
                
                if results:
                    return f"Search results for '{query}':\n\n" + "\n\n".join(results)
        except Exception as e:
            logger.warning(f"Serper API error: {e}")
    
    # Fallback: 使用 DuckDuckGo
    try:
        # Try new package name first (ddgs), fallback to old (duckduckgo_search)
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
            
            if results:
                output = f"Search results for '{query}':\n\n"
                for i, r in enumerate(results, 1):
                    output += f"{i}. **{r.get('title', 'No title')}**\n"
                    output += f"   {r.get('body', '')}\n"
                    output += f"   URL: {r.get('href', '')}\n\n"
                return output.strip()
    except ImportError:
        logger.warning("duckduckgo_search not installed")
    except Exception as e:
        logger.warning(f"DuckDuckGo search error: {e}")
    
    # 最终 fallback: 返回搜索建议
    encoded_query = urllib.parse.quote(query)
    return f"""Unable to perform web search. Please try:
1. Google: https://www.google.com/search?q={encoded_query}
2. DuckDuckGo: https://duckduckgo.com/?q={encoded_query}
3. Bing: https://www.bing.com/search?q={encoded_query}

Tip: Configure SERPER_API_KEY environment variable for automated searches."""


@tool("duckduckgo_search")
def duckduckgo_search(query: str, num_results: int = 5) -> str:
    """Search the internet using DuckDuckGo (free, no API key required).

    Uses DuckDuckGo search engine to find information.
    Ideal for getting latest news, market updates, and company announcements.

    Args:
        query: Search query terms
        num_results: Number of results to return, default 5

    Returns:
        Search results summary
    """
    import urllib.parse

    if DDGS is None:
        encoded_query = urllib.parse.quote(query)
        return f"""DuckDuckGo search library not installed. Please try:
1. Install: pip install duckduckgo-search
2. Or search manually: https://duckduckgo.com/?q={encoded_query}"""

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))

            if results:
                output = f"Search results for '{query}':\n\n"
                for i, r in enumerate(results, 1):
                    output += f"{i}. **{r.get('title', 'No title')}**\n"
                    output += f"   {r.get('body', '')}\n"
                    output += f"   URL: {r.get('href', '')}\n\n"
                return output.strip()
            else:
                return f"No results found for '{query}'. Try different search terms."

    except Exception as e:
        logger.warning(f"DuckDuckGo search error: {e}")
        encoded_query = urllib.parse.quote(query)
        return f"""Search failed: {e}

Try searching manually:
- DuckDuckGo: https://duckduckgo.com/?q={encoded_query}
- Google: https://www.google.com/search?q={encoded_query}"""


@tool("scrape_website")
def scrape_website(url: str) -> str:
    """抓取网页内容
    
    获取指定URL的网页内容，提取主要文本信息。
    适用于阅读文章、新闻、公司公告等。
    
    Args:
        url: 要抓取的网页URL
        
    Returns:
        网页的主要文本内容
    """
    try:
        import httpx
        from bs4 import BeautifulSoup
        
        # 设置请求头模拟浏览器
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        response = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 移除脚本和样式
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()
        
        # 尝试找到主要内容区域
        main_content = None
        for selector in ["article", "main", ".content", "#content", ".post", ".article"]:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if main_content:
            text = main_content.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)
        
        # 清理文本
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        cleaned_text = "\n".join(lines)
        
        # 限制长度
        max_length = 5000
        if len(cleaned_text) > max_length:
            cleaned_text = cleaned_text[:max_length] + "\n\n[Content truncated...]"
        
        return f"Content from {url}:\n\n{cleaned_text}"
        
    except ImportError:
        return "Error: beautifulsoup4 and httpx packages required. Install with: pip install beautifulsoup4 httpx"
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return f"Error scraping {url}: {str(e)}"


@tool("search_financial_news")
def search_financial_news(topic: str, days: int = 7) -> str:
    """搜索金融相关新闻
    
    专门搜索金融市场、股票、经济相关的新闻和分析。
    
    Args:
        topic: 搜索主题（如股票代码、公司名、市场事件）
        days: 搜索最近多少天的新闻，默认7天
        
    Returns:
        相关金融新闻列表
    """
    # 构建金融新闻搜索查询
    query = f"{topic} stock market news"
    
    result = web_search(query, num_results=8)
    
    if "Unable to perform" not in result:
        return f"Financial News for '{topic}':\n\n{result}"
    
    return result


@tool("search_company_info")
def search_company_info(company: str) -> str:
    """搜索公司信息
    
    搜索公司的基本信息、最新动态、财报等。
    
    Args:
        company: 公司名称或股票代码
        
    Returns:
        公司相关信息摘要
    """
    query = f"{company} company profile investor relations"
    
    result = web_search(query, num_results=5)
    
    if "Unable to perform" not in result:
        return f"Company Information for '{company}':\n\n{result}"

    return result


# =========================================================================
# Fixed SerperDevTool with complete schema
# =========================================================================

def create_fixed_serper_dev_tool():
    """
    Create a fixed version of SerperDevTool with complete schema.

    The original SerperDevTool from crewai_tools has an incomplete schema:
    - Only defines search_query in args_schema
    - But description mentions search_type support
    - This causes LLM to hallucinate incorrect parameter formats

    This fix adds search_type to the schema so LLM knows exactly what parameters
    are available and how to use them.
    """
    try:
        from crewai_tools import SerperDevTool
        from pydantic import BaseModel, Field
        from typing import Literal

        class FixedSerperDevToolSchema(BaseModel):
            """Complete input schema for SerperDevTool."""

            search_query: str = Field(
                ...,
                description="The search query string to search the internet"
            )
            search_type: Literal["search", "news"] = Field(
                default="search",
                description="Type of search: 'search' for general web results (default), 'news' for news articles only"
            )

        class FixedSerperDevTool(SerperDevTool):
            """
            Fixed SerperDevTool with complete schema.

            Improvements over original:
            - Adds search_type to args_schema (was only in description before)
            - Clearer tool name to avoid confusion
            - More explicit description of parameters
            """

            name: str = "serper_web_search"
            description: str = (
                "Search the internet using Serper API. "
                "Parameters: search_query (required string), "
                "search_type (optional: 'search' for web results, 'news' for news articles, default='search'). "
                "Returns formatted search results."
            )
            args_schema: type[BaseModel] = FixedSerperDevToolSchema

        return FixedSerperDevTool()

    except ImportError:
        logger.warning("crewai_tools not installed, SerperDevTool not available")
        return None
    except Exception as e:
        logger.error(f"Failed to create FixedSerperDevTool: {e}")
        return None
