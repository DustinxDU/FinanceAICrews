import os
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session
from jinja2 import Template
import litellm

from AICrews.observability.logging import get_logger
from AICrews.schemas.quick_analysis import QuickScanResponse, ChartAnalysisResponse
from AICrews.services.insight_ingestor import get_insight_ingestor
from AICrews.database.models import User, UserAssetInsight
from AICrews.infrastructure.cache.redis_manager import get_redis_manager
from AICrews.database.session import SessionLocal
from AICrews.config.prompt_config import get_prompt_config_loader

logger = get_logger(__name__)

# 获取配置加载器
prompt_loader = get_prompt_config_loader()
quick_scan_config = prompt_loader.get_config("quick_scan")
tech_scan_config = prompt_loader.get_config("technical_scan")

# =============================================================================
# 从配置加载
# =============================================================================

# Quick Scan
QUICK_SCAN_PARAMS = quick_scan_config.get("llm_params", {})
QUICK_SCAN_TEMPERATURE = QUICK_SCAN_PARAMS.get("temperature", 0.3)
QUICK_SCAN_MAX_TOKENS = QUICK_SCAN_PARAMS.get("max_tokens", 500)
QUICK_SCAN_SYSTEM_PROMPT = quick_scan_config.get(
    "system_prompt", "You are a financial analyst."
)

# Technical Scan (Chart Analysis)
TECH_SCAN_PARAMS = tech_scan_config.get("llm_params", {})
CHART_ANALYSIS_TEMPERATURE = TECH_SCAN_PARAMS.get("temperature", 0.3)
CHART_ANALYSIS_MAX_TOKENS = TECH_SCAN_PARAMS.get("max_tokens", 800)
CHART_ANALYSIS_SYSTEM_PROMPT = tech_scan_config.get(
    "system_prompt", "You are a technical analyst."
)


class QuickAnalysisService:
    """Quick Analysis Service - 快速分析服务

    直接使用 litellm 进行 LLM 调用，无需依赖 CrewAI。
    Quick Scan 和 Chart Analysis 是简单的一次性 LLM 调用场景。
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    async def _get_llm_config(self, scope: str) -> Dict[str, Any]:
        """获取 LLM 配置参数（用于直接调用 litellm）

        Args:
            scope: LLM scope, e.g., "quick_scan", "chart_scan"

        Returns:
            Dict with model, api_key, api_base for litellm
        """
        from AICrews.llm.policy_router import LLMPolicyRouter
        from AICrews.llm.core.config_store import get_config_store
        from AICrews.schemas.llm_policy import LLMScope

        # 映射 scope 字符串到 LLMScope 枚举
        scope_map = {
            "quick_scan": LLMScope.QUICK_SCAN,
            "chart_scan": LLMScope.CHART_SCAN,
        }
        llm_scope = scope_map.get(scope, LLMScope.QUICK_SCAN)

        # 检查是否有环境变量配置
        if LLMPolicyRouter.is_env_configured(llm_scope):
            from AICrews.llm.system_config import get_system_llm_config_store

            store = get_system_llm_config_store()
            config = store.get_config(llm_scope)

            provider = config.provider
            model = config.model

            # 从 providers.yaml 获取 provider 配置
            config_store = get_config_store()
            provider_config = config_store.get_provider(provider)

            if provider_config:
                # 使用配置中的 llm_model_prefix
                prefix = provider_config.llm_model_prefix or ""
                litellm_model = f"{prefix}{model}"
                api_base = config.base_url or provider_config.endpoints.api_base
            else:
                # 回退：直接使用模型名
                litellm_model = model
                api_base = config.base_url

            logger.info(f"Using env-based LLM config for {scope}: provider={provider}, model={model}, litellm_model={litellm_model}")

            return {
                "model": litellm_model,
                "api_key": config.api_key,
                "api_base": api_base,
            }

        # 回退：抛出错误，要求配置环境变量
        raise ValueError(f"LLM configuration required. Set FAIC_LLM_{scope.upper()}_* env vars.")

    async def run_quick_scan(
        self, ticker: str, thesis: Optional[str] = None, user: Optional[User] = None
    ) -> QuickScanResponse:
        """运行 Quick Scan"""
        start_time = datetime.now()
        ticker = ticker.upper()

        # 获取 LLM 配置 ID - 优先使用 default_model_config_id
        llm_config_id = None
        if user:
            if user.default_model_config_id:
                llm_config_id = str(user.default_model_config_id)
            elif user.default_llm_config_id:
                llm_config_id = user.default_llm_config_id

        # 1. 并行获取数据
        price_task = self._get_price_data(ticker)
        news_task = self._get_news_data(ticker)

        price_data, news_data = await asyncio.gather(
            price_task, news_task, return_exceptions=True
        )

        # 处理异常
        if isinstance(price_data, Exception):
            logger.warning(f"Price data fetch failed for {ticker}: {price_data}")
            price_data = {"price": "N/A", "change": "N/A", "change_percent": 0}

        if isinstance(news_data, Exception):
            logger.warning(f"News data fetch failed for {ticker}: {news_data}")
            news_data = []

        # 2. 生成快速总结
        summary, sentiment = await self._generate_summary_with_llm(
            ticker, price_data, news_data, thesis, llm_config_id
        )

        # 3. 提取新闻要点
        news_highlights = self._extract_news_highlights(news_data)

        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

        response = QuickScanResponse(
            ticker=ticker,
            summary=summary,
            sentiment=sentiment,
            news_highlights=news_highlights,
            price_info=price_data,
            execution_time_ms=execution_time,
        )

        # 4. 异步写入 Library
        if user:
            asyncio.create_task(self._ingest_quick_scan_to_library(response, user.id))

        return response

    async def run_chart_analysis(
        self, ticker: str, thesis: Optional[str] = None, user: Optional[User] = None
    ) -> ChartAnalysisResponse:
        """运行 Chart Analysis"""
        start_time = datetime.now()
        ticker = ticker.upper()

        # 获取 LLM 配置 ID - 优先使用 default_model_config_id
        llm_config_id = None
        if user:
            if user.default_model_config_id:
                llm_config_id = str(user.default_model_config_id)
            elif user.default_llm_config_id:
                llm_config_id = user.default_llm_config_id

        # 1. 获取历史数据
        hist_data = await self._get_historical_data(ticker)

        # 2. 计算技术指标
        indicators = self._calculate_indicators(hist_data)

        # 3. 计算支撑阻力位
        support_resistance = self._calculate_support_resistance(hist_data)

        # 4. 生成技术面总结
        summary, trend = await self._generate_technical_summary_with_llm(
            ticker, indicators, support_resistance, thesis, llm_config_id
        )

        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

        response = ChartAnalysisResponse(
            ticker=ticker,
            technical_summary=summary,
            indicators=indicators,
            support_resistance=support_resistance,
            trend_assessment=trend,
            execution_time_ms=execution_time,
        )

        # 5. 异步写入 Library
        if user:
            asyncio.create_task(
                self._ingest_technical_diagnostic_to_library(response, user.id)
            )

        return response

    # =============================================================================
    # Helper Methods
    # =============================================================================

    async def _get_price_data(self, ticker: str) -> Dict[str, Any]:
        """获取实时价格 - 支持多市场"""
        try:
            # 判断市场类型
            is_hk_stock = ticker.endswith(".HK")
            is_a_stock = ticker.endswith(".SS") or ticker.endswith(".SZ")

            # A股和港股优先使用 akshare
            if is_hk_stock or is_a_stock:
                price_data = await self._get_price_from_akshare(ticker)
                if price_data and price_data.get("price") != "N/A":
                    return price_data
                # akshare 失败，尝试 yfinance
                price_data = await self._get_price_from_yfinance(ticker)
                if price_data and price_data.get("price") != "N/A":
                    return price_data
            else:
                # 美股和加密货币优先使用 yfinance
                price_data = await self._get_price_from_yfinance(ticker)
                if price_data and price_data.get("price") != "N/A":
                    return price_data

            return {
                "price": "N/A",
                "change": "N/A",
                "change_percent": 0,
                "volume": "N/A",
                "high": "N/A",
                "low": "N/A",
                "note": "Real-time data unavailable",
            }

        except Exception as e:
            logger.error(f"Error fetching price for {ticker}: {e}")
            return {"price": "N/A", "change": "N/A", "change_percent": 0}

    async def _get_price_from_akshare(self, ticker: str) -> Dict[str, Any]:
        """使用 akshare 获取 A股/港股价格数据"""
        try:
            import akshare as ak

            if ticker.endswith(".HK"):
                code = ticker.replace(".HK", "").zfill(5)

                def fetch_hk_data():
                    try:
                        df = ak.stock_hk_spot()
                        if df is not None and not df.empty:
                            for _, row in df.iterrows():
                                row_code = str(
                                    row.get("symbol", "") or row.get("代码", "")
                                )
                                if code in row_code or row_code.endswith(code):
                                    return row.to_dict()
                    except Exception as e:
                        logger.warning(f"akshare stock_hk_spot failed: {e}")
                    return None

                row_data = await asyncio.to_thread(fetch_hk_data)
                if row_data:
                    price = row_data.get("lasttrade") or row_data.get("最新价")
                    prev_close = row_data.get("prevclose") or row_data.get("昨收")
                    if price and prev_close:
                        try:
                            price = float(price)
                            prev_close = float(prev_close)
                            change = price - prev_close
                            change_pct = (
                                (change / prev_close * 100) if prev_close else 0
                            )
                            return {
                                "price": f"{price:.2f}",
                                "change": f"{change:+.2f}",
                                "change_percent": round(change_pct, 2),
                                "volume": row_data.get("volume")
                                or row_data.get("成交量", "N/A"),
                                "high": row_data.get("high")
                                or row_data.get("最高", "N/A"),
                                "low": row_data.get("low")
                                or row_data.get("最低", "N/A"),
                                "name": row_data.get("name")
                                or row_data.get("名称", ticker),
                                "currency": "HKD",
                                "source": "akshare",
                            }
                        except (ValueError, TypeError):
                            pass

            elif ticker.endswith(".SS") or ticker.endswith(".SZ"):
                code = ticker.replace(".SS", "").replace(".SZ", "")

                def fetch_a_stock_data():
                    try:
                        df = ak.stock_zh_a_spot_em()
                        if df is not None and not df.empty:
                            for _, row in df.iterrows():
                                if str(row.get("代码", "")) == code:
                                    return row.to_dict()
                    except Exception as e:
                        logger.warning(f"akshare stock_zh_a_spot_em failed: {e}")
                    return None

                row_data = await asyncio.to_thread(fetch_a_stock_data)
                if row_data:

                    def safe_float(value, default=0):
                        try:
                            val = float(value) if value is not None else default
                            return default if (val != val) else val
                        except (ValueError, TypeError):
                            return default

                    price = safe_float(row_data.get("最新价"))
                    change = safe_float(row_data.get("涨跌额"))
                    change_pct = safe_float(row_data.get("涨跌幅"))

                    if price > 0:
                        return {
                            "price": f"{price:.2f}",
                            "change": f"{change:+.2f}" if change != 0 else "0.00",
                            "change_percent": round(change_pct, 2),
                            "volume": row_data.get("成交量", "N/A"),
                            "high": row_data.get("最高", "N/A"),
                            "low": row_data.get("最低", "N/A"),
                            "name": row_data.get("名称", ticker),
                            "currency": "CNY",
                            "source": "akshare",
                        }

            return {"price": "N/A"}
        except Exception as e:
            logger.warning(f"akshare fetch failed for {ticker}: {e}")
            return {"price": "N/A"}

    async def _get_price_from_yfinance(self, ticker: str) -> Dict[str, Any]:
        """使用 yfinance 获取价格数据"""
        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            info = await asyncio.to_thread(lambda: stock.info)

            if info:
                current_price = (
                    info.get("currentPrice")
                    or info.get("regularMarketPrice")
                    or info.get("previousClose")
                )
                prev_close = info.get("previousClose") or info.get(
                    "regularMarketPreviousClose"
                )

                if current_price:
                    change = current_price - prev_close if prev_close else 0
                    change_percent = (change / prev_close * 100) if prev_close else 0
                    return {
                        "price": f"{current_price:.2f}",
                        "change": f"{change:+.2f}",
                        "change_percent": round(change_percent, 2),
                        "volume": info.get("volume")
                        or info.get("regularMarketVolume", "N/A"),
                        "high": info.get("dayHigh")
                        or info.get("regularMarketDayHigh", "N/A"),
                        "low": info.get("dayLow")
                        or info.get("regularMarketDayLow", "N/A"),
                        "name": info.get("shortName") or info.get("longName", ticker),
                        "currency": info.get("currency", "USD"),
                    }
            return {"price": "N/A"}
        except Exception as e:
            logger.warning(f"yfinance fetch failed for {ticker}: {e}")
            return {"price": "N/A"}

    async def _get_news_data(self, ticker: str) -> List[Dict[str, Any]]:
        """获取相关新闻"""
        news_list = []
        # 1. yfinance
        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            news = await asyncio.to_thread(lambda: stock.news)
            if news:
                for item in news[:5]:
                    content = item.get("content", item)
                    title = (
                        content.get("title", "")
                        if isinstance(content, dict)
                        else item.get("title", "")
                    )
                    publisher = ""
                    link = ""
                    if isinstance(content, dict):
                        provider = content.get("provider", {})
                        publisher = (
                            provider.get("displayName", "")
                            if isinstance(provider, dict)
                            else ""
                        )
                        canonical = content.get("canonicalUrl", {})
                        link = (
                            canonical.get("url", "")
                            if isinstance(canonical, dict)
                            else ""
                        )

                    if title:
                        news_list.append(
                            {
                                "title": title,
                                "publisher": publisher,
                                "link": link,
                                "summary": content.get("summary", "")[:200]
                                if isinstance(content, dict)
                                else "",
                            }
                        )
                if news_list:
                    return news_list
        except Exception as e:
            logger.warning(f"yfinance news fetch failed for {ticker}: {e}")

        return news_list

    async def _generate_summary_with_llm(
        self,
        ticker: str,
        price_data: Dict[str, Any],
        news_data: List[Dict[str, Any]],
        thesis: Optional[str],
        llm_config_id: Optional[str],
    ) -> tuple[str, str]:
        """生成快速总结

        直接使用 litellm 进行 LLM 调用，无需依赖 CrewAI。
        """
        # 基础情绪
        change_percent = price_data.get("change_percent", 0)
        if change_percent > 2:
            base_sentiment = "bullish"
        elif change_percent > 0:
            base_sentiment = "bullish"
        elif change_percent < -2:
            base_sentiment = "bearish"
        elif change_percent < 0:
            base_sentiment = "bearish"
        else:
            base_sentiment = "neutral"

        # 尝试使用 litellm 直接调用
        try:
            llm_config = await self._get_llm_config("quick_scan")

            news_text = (
                "\n".join(
                    [f"- {n.get('title', 'News')}" for n in news_data[:5]]
                )
                if news_data
                else "No recent news."
            )

            # 使用模板渲染用户提示词
            user_template_str = quick_scan_config.get(
                "user_prompt_template", ""
            )
            if user_template_str:
                template = Template(user_template_str)
                user_prompt = template.render(
                    ticker=ticker,
                    price=price_data.get("price", "N/A"),
                    change_percent=f"{change_percent:+.2f}",
                    volume=price_data.get("volume", "N/A"),
                    news_text=news_text,
                    thesis_section=f"**User's Investment Thesis:** {thesis}"
                    if thesis
                    else "",
                )
            else:
                # 回退到硬编码（如果不应该发生）
                user_prompt = f"Analyze {ticker}..."

            full_prompt = f"{QUICK_SCAN_SYSTEM_PROMPT}\n\n{user_prompt}"

            # 使用 litellm 直接调用
            logger.info(f"[QuickScan] Calling litellm: model={llm_config['model']}")

            # 思考模型（如 GLM-4.6）需要更多 tokens 来完成推理并输出最终答案
            # 配置的 max_tokens 是给最终输出的，思考过程不计入
            # 但为了安全起见，我们确保至少有 1500 tokens
            effective_max_tokens = max(QUICK_SCAN_MAX_TOKENS, 1500)

            response = await litellm.acompletion(
                model=llm_config["model"],
                messages=[{"role": "user", "content": full_prompt}],
                api_key=llm_config.get("api_key"),
                api_base=llm_config.get("api_base"),
                temperature=QUICK_SCAN_TEMPERATURE,
                max_tokens=effective_max_tokens,
            )

            # 提取响应内容
            # 注意：思考模型的 reasoning_content 是推理过程，不是最终答案
            # 最终答案应该在 content 中
            choice = response.choices[0]
            message = choice.message
            response_text = message.content if message.content else None

            # 如果 content 为空，记录警告并使用 fallback
            if not response_text:
                # 检查是否有 reasoning_content（说明是思考模型但 tokens 不够）
                reasoning = getattr(message, "reasoning_content", None)
                if not reasoning and hasattr(message, "provider_specific_fields"):
                    reasoning = message.provider_specific_fields.get("reasoning_content")

                if reasoning:
                    logger.warning(
                        f"[QuickScan] Thinking model returned reasoning but no final answer. "
                        f"reasoning_length={len(reasoning)}. Consider increasing max_tokens."
                    )
                else:
                    logger.warning("[QuickScan] Empty response from LLM")

                return self._generate_fallback_summary(
                    ticker, price_data, news_data, thesis, base_sentiment
                )

            logger.info(f"[QuickScan] LLM response length: {len(response_text)}")

            # 解析情绪
            sentiment = base_sentiment
            if "SENTIMENT:" in response_text.upper():
                sentiment_line = (
                    response_text.upper().split("SENTIMENT:")[-1].strip()
                )
                if "BULLISH" in sentiment_line:
                    sentiment = "bullish"
                elif "BEARISH" in sentiment_line:
                    sentiment = "bearish"
                else:
                    sentiment = "neutral"
                response_text = response_text.rsplit("SENTIMENT:", 1)[
                    0
                ].strip()

            return response_text, sentiment

        except Exception as e:
            logger.warning(f"LLM call failed for Quick Scan: {e}", exc_info=True)

        return self._generate_fallback_summary(
            ticker, price_data, news_data, thesis, base_sentiment
        )

    def _generate_fallback_summary(
        self,
        ticker: str,
        price_data: Dict[str, Any],
        news_data: List[Dict[str, Any]],
        thesis: Optional[str],
        sentiment: str,
    ) -> tuple[str, str]:
        change_percent = price_data.get("change_percent", 0)
        if change_percent > 2:
            price_action = "showing strong upward momentum"
        elif change_percent > 0:
            price_action = "trading slightly higher"
        elif change_percent < -2:
            price_action = "under significant selling pressure"
        elif change_percent < 0:
            price_action = "trading slightly lower"
        else:
            price_action = "trading flat"

        news_count = len(news_data)
        news_summary = (
            f"{news_count} recent news items found"
            if news_count > 0
            else "No significant news"
        )

        summary = f"""**{ticker} Quick Scan**
1. **Price Action**: Currently {price_action} with {change_percent:+.2f}% change.
2. **News Flow**: {news_summary}.
3. **Sentiment**: Overall market sentiment appears {sentiment}."""

        if thesis:
            summary += f"\n\n*Your thesis*: {thesis[:100]}..."
        return summary, sentiment

    def _extract_news_highlights(self, news_data: List[Dict[str, Any]]) -> List[str]:
        highlights = []
        for news in news_data[:3]:
            if isinstance(news, dict):
                title = (
                    news.get("title")
                    or news.get("标题")
                    or news.get("content", "")[:50]
                )
                if title:
                    highlights.append(title)
        return highlights

    async def _get_historical_data(self, ticker: str) -> List[Dict[str, Any]]:
        """获取历史数据 - 支持多数据源回退"""
        redis_manager = get_redis_manager()
        cache_key = f"hist:{ticker}:1m"
        cached_data = await redis_manager.get_json(cache_key)
        if cached_data:
            return cached_data

        # 判断市场类型
        is_hk_stock = ticker.endswith(".HK")
        is_a_stock = ticker.endswith(".SS") or ticker.endswith(".SZ")

        # A股/港股优先 akshare，美股优先 yfinance
        if is_a_stock or is_hk_stock:
            data = await self._get_historical_from_akshare(ticker)
            if data:
                await redis_manager.set(cache_key, data, ttl=3600)
                return data

        # yfinance 作为主要/回退数据源
        data = await self._get_historical_from_yfinance(ticker)
        if data:
            await redis_manager.set(cache_key, data, ttl=3600)
            return data

        return []

    async def _get_historical_from_yfinance(self, ticker: str) -> List[Dict[str, Any]]:
        """使用 yfinance 获取历史数据"""
        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            # 获取1个月历史数据
            hist = await asyncio.to_thread(lambda: stock.history(period="1mo"))

            if hist is not None and not hist.empty:
                data = []
                for date, row in hist.iterrows():
                    data.append(
                        {
                            "date": date.strftime("%Y-%m-%d"),
                            "open": float(row.get("Open", 0)),
                            "high": float(row.get("High", 0)),
                            "low": float(row.get("Low", 0)),
                            "close": float(row.get("Close", 0)),
                            "volume": int(row.get("Volume", 0)),
                        }
                    )
                logger.info(
                    f"yfinance historical data for {ticker}: {len(data)} records"
                )
                return data
            return []
        except Exception as e:
            logger.warning(f"yfinance historical fetch failed for {ticker}: {e}")
            return []

    async def _get_historical_from_akshare(self, ticker: str) -> List[Dict[str, Any]]:
        """使用 akshare 获取 A股/港股历史数据"""
        try:
            import akshare as ak
            from datetime import datetime, timedelta

            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")

            if ticker.endswith(".SS") or ticker.endswith(".SZ"):
                code = ticker.replace(".SS", "").replace(".SZ", "")

                def fetch_a_hist():
                    try:
                        df = ak.stock_zh_a_hist(
                            symbol=code,
                            period="daily",
                            start_date=start_str,
                            end_date=end_str,
                            adjust="qfq",
                        )
                        return df
                    except Exception as e:
                        logger.warning(f"akshare A-share hist failed: {e}")
                        return None

                df = await asyncio.to_thread(fetch_a_hist)
                if df is not None and not df.empty:
                    data = []
                    for _, row in df.iterrows():
                        data.append(
                            {
                                "date": str(row.get("日期", "")),
                                "open": float(row.get("开盘", 0)),
                                "high": float(row.get("最高", 0)),
                                "low": float(row.get("最低", 0)),
                                "close": float(row.get("收盘", 0)),
                                "volume": int(row.get("成交量", 0)),
                            }
                        )
                    logger.info(
                        f"akshare A-share historical data for {ticker}: {len(data)} records"
                    )
                    return data

            elif ticker.endswith(".HK"):
                code = ticker.replace(".HK", "").zfill(5)

                def fetch_hk_hist():
                    try:
                        df = ak.stock_hk_hist(
                            symbol=code,
                            period="daily",
                            start_date=start_str,
                            end_date=end_str,
                            adjust="qfq",
                        )
                        return df
                    except Exception as e:
                        logger.warning(f"akshare HK hist failed: {e}")
                        return None

                df = await asyncio.to_thread(fetch_hk_hist)
                if df is not None and not df.empty:
                    data = []
                    for _, row in df.iterrows():
                        data.append(
                            {
                                "date": str(row.get("日期", "")),
                                "open": float(row.get("开盘", 0)),
                                "high": float(row.get("最高", 0)),
                                "low": float(row.get("最低", 0)),
                                "close": float(row.get("收盘", 0)),
                                "volume": int(row.get("成交量", 0)),
                            }
                        )
                    logger.info(
                        f"akshare HK historical data for {ticker}: {len(data)} records"
                    )
                    return data

            return []
        except Exception as e:
            logger.warning(f"akshare historical fetch failed for {ticker}: {e}")
            return []

    def _calculate_indicators(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not data or len(data) < 14:
            return {"error": "Insufficient data"}
        closes = [
            float(d.get("close") or d.get("收盘", 0))
            for d in data
            if d.get("close") or d.get("收盘")
        ]
        if len(closes) < 14:
            return {"error": "Insufficient close prices"}

        ma20 = (
            sum(closes[-20:]) / min(20, len(closes))
            if len(closes) >= 20
            else sum(closes) / len(closes)
        )
        ma50 = (
            sum(closes[-50:]) / min(50, len(closes))
            if len(closes) >= 50
            else sum(closes) / len(closes)
        )
        rsi = self._calculate_rsi(closes, 14)
        current_price = closes[-1] if closes else 0

        return {
            "current_price": round(current_price, 2),
            "ma20": round(ma20, 2),
            "ma50": round(ma50, 2),
            "rsi": round(rsi, 2),
            "price_vs_ma20": "above" if current_price > ma20 else "below",
            "price_vs_ma50": "above" if current_price > ma50 else "below",
            "rsi_signal": "overbought"
            if rsi > 70
            else ("oversold" if rsi < 30 else "neutral"),
        }

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _calculate_support_resistance(
        self, data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not data:
            return {"support": "N/A", "resistance": "N/A"}
        highs = [
            float(d.get("high") or d.get("最高", 0))
            for d in data
            if d.get("high") or d.get("最高")
        ]
        lows = [
            float(d.get("low") or d.get("最低", 0))
            for d in data
            if d.get("low") or d.get("最低")
        ]
        if not highs or not lows:
            return {"support": "N/A", "resistance": "N/A"}

        support = min(lows[-20:]) if len(lows) >= 20 else min(lows)
        resistance = max(highs[-20:]) if len(highs) >= 20 else max(highs)

        return {
            "support": round(support, 2),
            "resistance": round(resistance, 2),
            "range": round(resistance - support, 2),
            "range_percent": round((resistance - support) / support * 100, 2)
            if support > 0
            else 0,
        }

    async def _generate_technical_summary_with_llm(
        self,
        ticker: str,
        indicators: Dict[str, Any],
        support_resistance: Dict[str, Any],
        thesis: Optional[str],
        llm_config_id: Optional[str],
    ) -> tuple[str, str]:
        """生成技术分析总结

        直接使用 litellm 进行 LLM 调用，无需依赖 CrewAI。
        """
        if "error" in indicators:
            return f"Insufficient data to analyze {ticker}", "unknown"

        rsi = indicators.get("rsi", 50)
        price_vs_ma20 = indicators.get("price_vs_ma20", "unknown")

        if price_vs_ma20 == "above" and rsi < 70:
            base_trend = "bullish"
        elif price_vs_ma20 == "below" and rsi > 30:
            base_trend = "bearish"
        else:
            base_trend = "neutral"

        # 尝试使用 litellm 直接调用
        try:
            llm_config = await self._get_llm_config("chart_scan")

            # 准备技术指标文本
            indicators_text = (
                f"- Current Price: {indicators.get('current_price', 'N/A')}\n"
                f"- 20-day MA: {indicators.get('ma20', 'N/A')}\n"
                f"- Price vs MA20: {price_vs_ma20}\n"
                f"- RSI (14): {rsi:.1f} ({indicators.get('rsi_signal')})"
            )

            # 准备支撑阻力文本
            levels_text = (
                f"- Support Level: ${support_resistance.get('support', 'N/A')}\n"
                f"- Resistance Level: ${support_resistance.get('resistance', 'N/A')}\n"
                f"- Trading Range: {support_resistance.get('range_percent', 0):.1f}%"
            )

            # 使用模板渲染用户提示词
            user_template_str = tech_scan_config.get(
                "user_prompt_template", ""
            )
            if user_template_str:
                template = Template(user_template_str)
                user_prompt = template.render(
                    ticker=ticker,
                    indicators_text=indicators_text,
                    levels_text=levels_text,
                    thesis_section=f"**User's Investment Thesis:** {thesis}"
                    if thesis
                    else "",
                )
            else:
                user_prompt = (
                    f"Analyze technical indicators for {ticker}..."
                )

            full_prompt = f"{CHART_ANALYSIS_SYSTEM_PROMPT}\n\n{user_prompt}"

            # 使用 litellm 直接调用
            logger.info(f"[ChartScan] Calling litellm: model={llm_config['model']}")

            # 思考模型（如 GLM-4.6）需要更多 tokens 来完成推理并输出最终答案
            effective_max_tokens = max(CHART_ANALYSIS_MAX_TOKENS, 1500)

            response = await litellm.acompletion(
                model=llm_config["model"],
                messages=[{"role": "user", "content": full_prompt}],
                api_key=llm_config.get("api_key"),
                api_base=llm_config.get("api_base"),
                temperature=CHART_ANALYSIS_TEMPERATURE,
                max_tokens=effective_max_tokens,
            )

            # 提取响应内容
            # 注意：思考模型的 reasoning_content 是推理过程，不是最终答案
            choice = response.choices[0]
            message = choice.message
            response_text = message.content if message.content else None

            # 如果 content 为空，记录警告并使用 fallback
            if not response_text:
                reasoning = getattr(message, "reasoning_content", None)
                if not reasoning and hasattr(message, "provider_specific_fields"):
                    reasoning = message.provider_specific_fields.get("reasoning_content")

                if reasoning:
                    logger.warning(
                        f"[ChartScan] Thinking model returned reasoning but no final answer. "
                        f"reasoning_length={len(reasoning)}. Consider increasing max_tokens."
                    )
                else:
                    logger.warning("[ChartScan] Empty response from LLM")

                return self._generate_fallback_technical_summary(
                    ticker, indicators, support_resistance, base_trend
                )

            logger.info(f"[ChartScan] LLM response length: {len(response_text)}")

            # 解析趋势
            trend = base_trend
            if "TREND:" in response_text.upper():
                trend_line = (
                    response_text.upper().split("TREND:")[-1].strip()
                )
                if "BULLISH" in trend_line:
                    trend = "bullish"
                elif "BEARISH" in trend_line:
                    trend = "bearish"
                else:
                    trend = "neutral"
                response_text = response_text.rsplit("TREND:", 1)[0].strip()

            return response_text, trend

        except Exception as e:
            logger.warning(f"LLM call failed for Chart Analysis: {e}", exc_info=True)

        return self._generate_fallback_technical_summary(
            ticker, indicators, support_resistance, base_trend
        )

    def _generate_fallback_technical_summary(
        self,
        ticker: str,
        indicators: Dict[str, Any],
        support_resistance: Dict[str, Any],
        trend: str,
    ) -> tuple[str, str]:
        trend_desc = (
            "uptrend"
            if trend == "bullish"
            else "downtrend"
            if trend == "bearish"
            else "consolidation"
        )
        summary = f"""**{ticker} Technical Analysis**
**Trend**: Currently in a {trend_desc} pattern.
- Price is trading {indicators.get("price_vs_ma20")} the 20-day MA
- RSI at {indicators.get("rsi"):.1f} indicates {indicators.get("rsi_signal")} conditions
**Key Levels**:
- Support: ${support_resistance.get("support", "N/A")}
- Resistance: ${support_resistance.get("resistance", "N/A")}
**Signal**: {trend.upper()} bias."""
        return summary, trend

    async def _ingest_quick_scan_to_library(
        self, data: QuickScanResponse, user_id: int
    ) -> bool:
        try:
            db = SessionLocal()
            try:
                # 防重复检查：检查最近30秒内是否已有相同ticker的quick_scan记录
                from datetime import timedelta
                recent_cutoff = datetime.now() - timedelta(seconds=30)
                existing = db.query(UserAssetInsight).filter(
                    UserAssetInsight.user_id == user_id,
                    UserAssetInsight.ticker == data.ticker,
                    UserAssetInsight.source_type == "quick_scan",
                    UserAssetInsight.created_at >= recent_cutoff
                ).first()
                if existing:
                    logger.info(f"Skipping duplicate quick scan for {data.ticker}, existing record: {existing.id}")
                    return True

                ingestor = get_insight_ingestor(db)

                # 构建完整的 content 字段，包含新闻要点
                content_parts = []
                if data.news_highlights:
                    content_parts.append("## 新闻要点\n")
                    for i, highlight in enumerate(data.news_highlights, 1):
                        content_parts.append(f"- {highlight}\n")
                content = "".join(content_parts) if content_parts else None

                # 构建完整的 key_metrics，包含所有价格信息
                key_metrics = {}
                if data.price_info:
                    key_metrics.update(data.price_info)

                await ingestor.save_quick_scan(
                    user_id=user_id,
                    ticker=data.ticker,
                    title=f"Quick Scan: {data.ticker}",
                    summary=data.summary,
                    sentiment=data.sentiment,
                    sentiment_score=1.0
                    if data.sentiment == "bullish"
                    else (-1.0 if data.sentiment == "bearish" else 0.0),
                    key_metrics=key_metrics,
                    content=content,
                    raw_data={
                        "price_info": data.price_info,
                        "news_highlights": data.news_highlights,
                        "execution_time_ms": data.execution_time_ms,
                    },
                    tags=["quick_scan", "cockpit"],
                )
                return True
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Library ingest failed: {e}")
            return False

    async def _ingest_technical_diagnostic_to_library(
        self, data: ChartAnalysisResponse, user_id: int
    ) -> bool:
        try:
            db = SessionLocal()
            try:
                # 防重复检查：检查最近30秒内是否已有相同ticker的technical_diagnostic记录
                from datetime import timedelta
                recent_cutoff = datetime.now() - timedelta(seconds=30)
                existing = db.query(UserAssetInsight).filter(
                    UserAssetInsight.user_id == user_id,
                    UserAssetInsight.ticker == data.ticker,
                    UserAssetInsight.source_type == "technical_diagnostic",
                    UserAssetInsight.created_at >= recent_cutoff
                ).first()
                if existing:
                    logger.info(f"Skipping duplicate technical diagnostic for {data.ticker}, existing record: {existing.id}")
                    return True

                ingestor = get_insight_ingestor(db)
                await ingestor.save_technical_diagnostic(
                    user_id=user_id,
                    ticker=data.ticker,
                    title=f"Chart Analysis: {data.ticker}",
                    summary=data.technical_summary,
                    sentiment=data.trend_assessment,
                    sentiment_score=1.0
                    if data.trend_assessment == "bullish"
                    else (-1.0 if data.trend_assessment == "bearish" else 0.0),
                    key_metrics=data.indicators,
                    raw_data={
                        "indicators": data.indicators,
                        "support_resistance": data.support_resistance,
                    },
                    tags=["technical_diagnostic", "chart"],
                )
                return True
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Library ingest failed: {e}")
            return False
