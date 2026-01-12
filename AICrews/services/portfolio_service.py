from typing import List, Dict, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, select

from .base import BaseService
from AICrews.database.models import (
    UserPortfolio,
    Asset,
    RealtimeQuote,
    ActiveMonitoring,
)
from AICrews.database.session import SessionLocal
from AICrews.schemas.portfolio import (
    AddAssetRequest,
    UpdateAssetRequest,
    UserAssetResponse,
    PortfolioSummary,
    AssetSearchRequest,
    AssetSearchResult,
)
from AICrews.services.market_service import MarketService
from AICrews.observability.logging import get_logger

# Infrastructure services
from AICrews.services.unified_sync_service import get_unified_sync_service

logger = get_logger(__name__)


class PortfolioService(BaseService[UserPortfolio]):
    """Portfolio Service - 投资组合服务"""

    def __init__(self, db: Session):
        super().__init__(db, UserPortfolio)
        self.market_service = MarketService(db)

    async def search_assets(
        self, request: AssetSearchRequest
    ) -> List[AssetSearchResult]:
        """搜索资产 (使用统一的 market_service)"""
        return await self.market_service.unified_search_assets(request)

    async def add_user_asset(
        self, user_id: int, request: AddAssetRequest
    ) -> UserAssetResponse:
        """添加用户资产"""
        ticker = request.ticker.upper()

        # 1. 检查是否已关注
        existing = (
            self.db.query(UserPortfolio)
            .filter(
                and_(UserPortfolio.user_id == user_id, UserPortfolio.ticker == ticker)
            )
            .first()
        )
        if existing:
            raise ValueError(f"Asset {ticker} already in portfolio")

        # 2. 检查/创建Asset记录
        asset = self.db.query(Asset).filter(Asset.ticker == ticker).first()
        if not asset:
            asset_info = await self._fetch_asset_info(ticker, request.asset_type)
            if not asset_info:
                raise ValueError(f"Invalid asset: {ticker}")

            asset = Asset(**asset_info)
            self.db.add(asset)
            self.db.flush()

        # 3. 创建用户关注关系
        portfolio_entry = UserPortfolio(
            user_id=user_id,
            ticker=ticker,
            notes=request.notes,
            target_price=request.target_price,
            added_at=datetime.now(),
        )
        self.db.add(portfolio_entry)

        # 4. 显式处理 active_monitoring
        was_first_subscriber = self._handle_add_subscription_sync(ticker)

        self.db.commit()
        self.db.refresh(portfolio_entry)

        # 5. 确保同步任务存在并立即拉取数据
        sync_service = get_unified_sync_service()
        
        # 检查同步任务是否已存在
        if ticker not in sync_service.sync_tasks:
            logger.info(
                f"Starting sync task for {ticker} (first_subscriber={was_first_subscriber})"
            )
            await sync_service._start_sync_task(ticker, asset.asset_type)
        
        # 无论是否第一个订阅者，都拉取最新数据
        if was_first_subscriber:
            await self._immediate_data_fetch(ticker, asset.asset_type)

        # 6. 构建响应
        return self._build_asset_response_sync(asset, portfolio_entry)

    async def get_user_assets(self, user_id: int) -> List[UserAssetResponse]:
        """获取用户资产列表"""
        # NOTE: 读路径只读 DB，不允许触发任何外部拉取（限额与性能风险）
        stmt = (
            select(UserPortfolio, Asset, RealtimeQuote)
            .join(Asset, Asset.ticker == UserPortfolio.ticker)
            .outerjoin(RealtimeQuote, RealtimeQuote.ticker == UserPortfolio.ticker)
            .where(UserPortfolio.user_id == user_id)
        )

        rows = self.db.execute(stmt).all()
        return [
            self._build_asset_response(asset, portfolio, quote)
            for portfolio, asset, quote in rows
        ]

    async def remove_user_asset(self, user_id: int, ticker: str) -> bool:
        """移除用户资产"""
        ticker = ticker.upper()

        portfolio_entry = (
            self.db.query(UserPortfolio)
            .filter(
                and_(UserPortfolio.user_id == user_id, UserPortfolio.ticker == ticker)
            )
            .first()
        )

        if not portfolio_entry:
            return False

        self.db.delete(portfolio_entry)

        was_last_subscriber = self._handle_remove_subscription_sync(ticker)

        self.db.commit()

        if was_last_subscriber:
            try:
                sync_service = get_unified_sync_service()
                await sync_service.unregister_subscription(user_id, ticker)
            except Exception as e:
                logger.warning(f"Failed to unregister sync for {ticker}: {e}")

        return True

    async def update_user_asset(
        self, user_id: int, ticker: str, request: UpdateAssetRequest
    ) -> UserAssetResponse:
        """更新用户资产信息"""
        ticker = ticker.upper()

        portfolio_entry = (
            self.db.query(UserPortfolio)
            .filter(
                and_(UserPortfolio.user_id == user_id, UserPortfolio.ticker == ticker)
            )
            .first()
        )

        if not portfolio_entry:
            raise ValueError(f"Asset {ticker} not found in portfolio")

        if request.notes is not None:
            portfolio_entry.notes = request.notes
        if request.target_price is not None:
            portfolio_entry.target_price = request.target_price

        self.db.commit()

        asset = self.db.query(Asset).filter(Asset.ticker == ticker).first()
        return self._build_asset_response_sync(asset, portfolio_entry)

    async def get_portfolio_summary(self, user_id: int) -> PortfolioSummary:
        """获取投资组合摘要"""
        portfolios = (
            self.db.query(UserPortfolio).filter(UserPortfolio.user_id == user_id).all()
        )

        asset_types = {}
        total_assets = 0

        for portfolio in portfolios:
            asset = (
                self.db.query(Asset).filter(Asset.ticker == portfolio.ticker).first()
            )
            if asset:
                total_assets += 1
                asset_types[asset.asset_type] = asset_types.get(asset.asset_type, 0) + 1

        return PortfolioSummary(
            total_assets=total_assets,
            asset_types=asset_types,
            last_updated=datetime.now(),
        )

    # --- Helper Methods ---

    def _handle_add_subscription_sync(self, ticker: str) -> bool:
        """处理添加订阅的 active_monitoring"""
        monitoring = (
            self.db.query(ActiveMonitoring)
            .filter(ActiveMonitoring.ticker == ticker)
            .first()
        )

        if monitoring:
            monitoring.subscriber_count += 1
            return False
        else:
            monitoring = ActiveMonitoring(
                ticker=ticker,
                subscriber_count=1,
                sync_interval_minutes=5,
                is_active=True,
                created_at=datetime.now(),
            )
            self.db.add(monitoring)
            return True

    def _handle_remove_subscription_sync(self, ticker: str) -> bool:
        """处理移除订阅的 active_monitoring"""
        monitoring = (
            self.db.query(ActiveMonitoring)
            .filter(ActiveMonitoring.ticker == ticker)
            .first()
        )

        if not monitoring:
            return False

        monitoring.subscriber_count -= 1

        if monitoring.subscriber_count <= 0:
            self.db.delete(monitoring)
            # Cleanup realtime quote
            quote = (
                self.db.query(RealtimeQuote)
                .filter(RealtimeQuote.ticker == ticker)
                .first()
            )
            if quote:
                self.db.delete(quote)
            return True
        else:
            return False

    async def _fetch_asset_info(
        self, ticker: str, asset_type: str
    ) -> Optional[Dict[str, Any]]:
        """获取资产基础信息"""
        try:
            # Simple logic for now
            if asset_type == "CRYPTO" or "-USD" in ticker:
                actual_type = "CRYPTO"
                exchange = "Crypto"
                currency = "USD"
            elif asset_type == "HK" or ".HK" in ticker:
                actual_type = "HK"
                exchange = "HKEX"
                currency = "HKD"
            elif ticker in ["US10Y", "DXY", "VIX", "GOLD"]:
                actual_type = "MACRO"
                exchange = "INDEX"
                currency = "USD"
            else:
                actual_type = "US"
                exchange = "NASDAQ/NYSE"
                currency = "USD"

            return {
                "ticker": ticker,
                "name": ticker,
                "asset_type": actual_type,
                "exchange": exchange,
                "currency": currency,
                "is_active": True,
            }
        except Exception as e:
            logger.error(f"Error fetching asset info for {ticker}: {e}")
            return None

    def _build_asset_response_sync(
        self, asset: Asset, portfolio: UserPortfolio, quote: RealtimeQuote = None
    ) -> UserAssetResponse:
        """构建响应"""
        if quote is None:
            quote = (
                self.db.query(RealtimeQuote)
                .filter(RealtimeQuote.ticker == asset.ticker)
                .first()
            )

        return self._build_asset_response(asset, portfolio, quote)

    def _build_asset_response(
        self, asset: Asset, portfolio: UserPortfolio, quote: RealtimeQuote = None
    ) -> UserAssetResponse:
        return UserAssetResponse(
            ticker=asset.ticker,
            asset_type=asset.asset_type,
            asset_name=asset.name,
            exchange=asset.exchange,
            currency=asset.currency,
            notes=portfolio.notes,
            target_price=portfolio.target_price,
            added_at=portfolio.added_at,
            current_price=quote.price if quote else None,
            price_local=getattr(quote, "price_local", None) if quote else None,
            currency_local=getattr(quote, "currency_local", None) if quote else None,
            price_change=quote.change_value if quote else None,
            price_change_percent=quote.change_percent if quote else None,
            volume=quote.volume if quote else None,
            market_cap=quote.market_cap if quote else None,
            is_market_open=quote.is_market_open if quote else None,
            trade_time=quote.trade_time if quote else None,
            last_updated=quote.last_updated if quote else None,
        )

    async def _refresh_stale_quotes(self, stale_tickers: List[tuple]):
        """后台刷新过期报价 (New Session)"""
        # Create a new session for background task
        session = SessionLocal()
        try:
            for ticker, asset_type in stale_tickers:
                try:
                    quote_data = await self._fetch_realtime_quote(ticker, asset_type)
                    if quote_data:
                        existing = (
                            session.query(RealtimeQuote)
                            .filter(RealtimeQuote.ticker == ticker)
                            .first()
                        )
                        if existing:
                            for key, value in quote_data.items():
                                if value is not None:
                                    setattr(existing, key, value)
                            existing.last_updated = datetime.now()
                        else:
                            new_quote = RealtimeQuote(
                                ticker=ticker,
                                last_updated=datetime.now(),
                                data_source="mcp",
                                **{
                                    k: v for k, v in quote_data.items() if v is not None
                                },
                            )
                            session.add(new_quote)
                        session.commit()
                except Exception as e:
                    logger.warning(f"Failed to refresh quote for {ticker}: {e}")
        finally:
            session.close()

    async def _immediate_data_fetch(self, ticker: str, asset_type: str):
        """立即拉取数据 (New Session)"""
        # Create a new session
        session = SessionLocal()
        try:
            quote_data = await self._fetch_realtime_quote(ticker, asset_type)
            if quote_data:
                existing = (
                    session.query(RealtimeQuote)
                    .filter(RealtimeQuote.ticker == ticker)
                    .first()
                )
                if existing:
                    for key, value in quote_data.items():
                        if value is not None:
                            setattr(existing, key, value)
                    existing.last_updated = datetime.now()
                else:
                    new_quote = RealtimeQuote(
                        ticker=ticker,
                        last_updated=datetime.now(),
                        data_source="mcp",
                        **{k: v for k, v in quote_data.items() if v is not None},
                    )
                    session.add(new_quote)
                session.commit()
        except Exception as e:
            logger.error(f"Error in immediate data fetch for {ticker}: {e}")
        finally:
            session.close()

    async def _fetch_realtime_quote(
        self, ticker: str, asset_type: str
    ) -> Optional[Dict[str, Any]]:
        if asset_type == "US":
            return await self._fetch_us_stock_quote(ticker)
        elif asset_type == "CRYPTO":
            return await self._fetch_crypto_quote(ticker)
        elif asset_type == "HK":
            return await self._fetch_hk_stock_quote(ticker)
        elif asset_type == "MACRO":
            return await self._fetch_macro_indicator(ticker)
        return None

    async def _fetch_us_stock_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        try:
            yf_client = get_yfinance_client()
            data = await yf_client.call_tool("stock_quote", {"symbol": ticker})
            if data:
                return {
                    "price": float(
                        data.get("price", data.get("regularMarketPrice", 0))
                    ),
                    "change_value": float(
                        data.get("change", data.get("regularMarketChange", 0))
                    ),
                    "change_percent": float(
                        data.get(
                            "change_percent", data.get("regularMarketChangePercent", 0)
                        )
                    ),
                    "volume": data.get("volume", data.get("regularMarketVolume")),
                    "market_cap": data.get("market_cap", data.get("marketCap")),
                    "is_market_open": True,
                }
            return None
        except Exception as e:
            logger.debug(f"Failed to fetch US stock quote for {ticker}: {e}")
            return None

    async def _fetch_crypto_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        try:
            yf_client = get_yfinance_client()
            data = await yf_client.call_tool("stock_quote", {"symbol": ticker})
            if data:
                return {
                    "price": float(
                        data.get("regularMarketPrice", data.get("price", 0))
                    ),
                    "change_value": float(data.get("regularMarketChange", 0)),
                    "change_percent": float(data.get("regularMarketChangePercent", 0)),
                    "is_market_open": True,
                }
            return None
        except Exception as e:
            logger.debug(f"Failed to fetch crypto quote for {ticker}: {e}")
            return None

    async def _fetch_hk_stock_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        try:
            yf_client = get_yfinance_client()
            if not ticker.endswith(".HK"):
                ticker = ticker.lstrip("0").zfill(4) + ".HK"
            data = await yf_client.call_tool("stock_quote", {"symbol": ticker})
            if data:
                hkd_price = float(data.get("price", data.get("regularMarketPrice", 0)))
                usd_price = hkd_price / 7.8
                return {
                    "price": usd_price,
                    "price_local": hkd_price,
                    "currency_local": "HKD",
                    "change_value": float(data.get("change", 0)),
                    "change_percent": float(data.get("change_percent", 0)),
                    "is_market_open": True,
                }
            return None
        except Exception as e:
            logger.debug(f"Failed to fetch HK stock quote for {ticker}: {e}")
            return None

    async def _fetch_macro_indicator(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取宏观指标 (使用 yfinance)"""
        try:
            import yfinance as yf

            # Macro ticker mapping
            ticker_map = {
                "US10Y": "^TNX",  # 10年美债收益率
                "DXY": "UUP",     # 美元指数
                "VIX": "^VIX",    # 波动率指数
            }

            yf_ticker = ticker_map.get(ticker, ticker)
            data = yf.Ticker(yf_ticker).info

            if data:
                return {
                    "price": float(data.get("regularMarketPrice", data.get("previousClose", 0))),
                    "change_value": float(data.get("regularMarketChange", 0)),
                    "change_percent": float(data.get("regularMarketChangePercent", 0) or 0) * 100,
                    "is_market_open": True,
                }
            return None
        except Exception as e:
            logger.debug(f"Failed to fetch macro indicator for {ticker}: {e}")
            return None
