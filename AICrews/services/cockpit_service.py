from AICrews.observability.logging import get_logger
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from AICrews.infrastructure.cache.redis_manager import get_redis_manager
from AICrews.services.unified_sync_service import get_unified_sync_service
from AICrews.services.market_service import MarketService
from AICrews.infrastructure.limits.provider_limiter import get_provider_limiter
from AICrews.schemas.cockpit import (
    CockpitDashboardResponse, CockpitMarketIndex, CockpitAssetPrice
)
from AICrews.database.models import UserPortfolio

logger = get_logger(__name__)

class CockpitService:
    def __init__(self, db: Session):
        self.db = db
        self.redis_manager = get_redis_manager()
        self.sync_service = get_unified_sync_service()
        self.market_service = MarketService(db)

    async def get_cockpit_dashboard(self, user_id: Optional[int], force_refresh: bool = False) -> CockpitDashboardResponse:
        """
        获取 Cockpit 仪表盘数据（聚合接口）
        """
        # 1. 获取市场指数/宏观数据（优先使用个性化指标）
        if user_id:
            macro_response = await self.market_service.get_personalized_cockpit_data(
                user_id=user_id,
                force_refresh=force_refresh,
            )
        else:
            macro_response = await self.market_service.get_cockpit_macro_data(force_refresh=force_refresh)
        
        markets = []
        for indicator in macro_response.indicators:
            markets.append(CockpitMarketIndex(
                id=indicator.id,
                name=indicator.name,
                value=indicator.value,
                change=indicator.change,
                change_percent=indicator.change_percent,
                trend=indicator.trend,
                critical=indicator.critical,
                type=indicator.type
            ))
            
        # 2. 获取用户关注资产价格
        assets = []
        if user_id:
            portfolios = self.db.query(UserPortfolio).filter(
                UserPortfolio.user_id == user_id
            ).all()
            
            tickers = [p.ticker for p in portfolios]
            
            if tickers:
                prices = await self.sync_service.get_user_prices(user_id, tickers)
                
                for portfolio in portfolios:
                    ticker = portfolio.ticker
                    price_data = prices.get(ticker, {})
                    asset = portfolio.asset
                    
                    assets.append(CockpitAssetPrice(
                        ticker=ticker,
                        name=asset.name if asset else None,
                        asset_type=asset.asset_type if asset else None,
                        exchange=asset.exchange if asset else None,
                        currency=asset.currency if asset else None,
                        notes=portfolio.notes,
                        target_price=portfolio.target_price,
                        price=price_data.get("price"),
                        price_local=price_data.get("price_local"),
                        currency_local=price_data.get("currency_local"),
                        change_percent=price_data.get("change_percent"),
                        change_value=price_data.get("change_value"),
                        volume=price_data.get("volume"),
                        market_cap=price_data.get("market_cap"),
                        is_market_open=price_data.get("is_market_open"),
                        source=price_data.get("source", "pending"),
                        last_updated=price_data.get("timestamp") or price_data.get("last_updated")
                    ))
                    
        # 3. Cache status (from MarketService's cache or logic)
        # MarketService doesn't expose cache expiration status directly in response, 
        # but we can infer or ignore. The API used _cockpit_macro_cache.is_expired().
        # We can assume false or calculate based on last_updated.
        
        # Actually, let's just use current time for response if not provided.
        # But wait, the original code returned `cache_expired`.
        # MarketService.get_cockpit_macro_data returns last_updated.
        
        last_updated_dt = datetime.fromisoformat(macro_response.last_updated) if isinstance(macro_response.last_updated, str) else macro_response.last_updated
        cache_expired = (datetime.now() - last_updated_dt).total_seconds() > 300  # 5 mins default
        
        return CockpitDashboardResponse(
            markets=markets,
            assets=assets,
            last_updated=macro_response.last_updated if isinstance(macro_response.last_updated, str) else datetime.now().isoformat(),
            cache_expired=cache_expired
        )

    async def get_user_assets(self, user_id: int) -> List[CockpitAssetPrice]:
        """获取用户关注的资产价格"""
        portfolios = self.db.query(UserPortfolio).filter(
            UserPortfolio.user_id == user_id
        ).all()
        
        if not portfolios:
            return []
            
        tickers = [p.ticker for p in portfolios]
        prices = await self.sync_service.get_user_prices(user_id, tickers)
        
        result = []
        for portfolio in portfolios:
            ticker = portfolio.ticker
            price_data = prices.get(ticker, {})
            
            result.append(CockpitAssetPrice(
                ticker=ticker,
                name=portfolio.asset.name if portfolio.asset else None,
                price=price_data.get("price"),
                change_percent=price_data.get("change_percent"),
                change_value=price_data.get("change_value"),
                volume=price_data.get("volume"),
                source=price_data.get("source", "pending"),
                last_updated=price_data.get("timestamp") or price_data.get("last_updated")
            ))
            
        return result

    async def get_asset_price(self, ticker: str, force_refresh: bool = False) -> Dict[str, Any]:
        """获取单个资产价格"""
        price_data = await self.sync_service.get_price(ticker, force_refresh=force_refresh)
        
        if price_data:
            return {
                "ticker": ticker,
                "price": price_data.get("price"),
                "change_percent": price_data.get("change_percent"),
                "change_value": price_data.get("change_value"),
                "volume": price_data.get("volume"),
                "last_updated": price_data.get("last_updated"),
                "source": price_data.get("source", "cache")
            }
            
        return {
            "ticker": ticker,
            "price": None,
            "change_percent": None,
            "error": "Price not available"
        }

    async def subscribe_asset(self, user_id: int, ticker: str) -> Dict[str, Any]:
        """订阅资产"""
        success = await self.sync_service.register_subscription(
            user_id=user_id,
            ticker=ticker
        )
        
        if success:
            return {
                "success": True,
                "message": f"Successfully subscribed to {ticker}",
                "ticker": ticker
            }
        else:
            return {
                "success": False,
                "message": f"Failed to subscribe to {ticker}",
                "ticker": ticker
            }

    async def unsubscribe_asset(self, user_id: int, ticker: str) -> Dict[str, Any]:
        """取消订阅资产"""
        success = await self.sync_service.unregister_subscription(
            user_id=user_id,
            ticker=ticker
        )
        
        if success:
            return {
                "success": True,
                "message": f"Successfully unsubscribed from {ticker}",
                "ticker": ticker
            }
        else:
            return {
                "success": False,
                "message": f"Failed to unsubscribe from {ticker}",
                "ticker": ticker
            }

    async def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        # UnifiedSyncService might not have get_status in the version I saw, 
        # but let's check the previous Read output.
        # It has `get_status`? No, I don't see `get_status` method in `UnifiedSyncService` class in the output.
        # But `cockpit.py` called `sync_service.get_status()`. 
        # Maybe I missed it or it was inherited?
        # Let's check `UnifiedSyncService` again or just implement what we know.
        # `cockpit.py` line 300: "sync_service": sync_service.get_status(),
        
        # If it's missing, I'll omit it or mock it.
        # Let's try to call it, if it fails I'll fix it.
        # But safer to check.
        
        # Checking `UnifiedSyncService` code again...
        # It has `start`, `stop`, `register_subscription`, `unregister_subscription`, `get_price`, `get_user_prices`, `_main_loop`...
        # I don't see `get_status`.
        # Maybe it was added in a part of file I didn't see (truncated)?
        # The file was truncated at 20KB.
        
        # I will assume it exists or implement a safe check.
        status = {}
        if hasattr(self.sync_service, 'get_status'):
            status = self.sync_service.get_status()
        else:
            status = {"running": self.sync_service.is_running, "tasks": len(self.sync_service.sync_tasks)}
            
        return {
            "sync_service": status,
            "redis_stats": await self.redis_manager.get_stats(),
            "provider_limits": get_provider_limiter().get_stats(),
            "timestamp": datetime.now().isoformat()
        }

    async def refresh_data(self):
        """刷新数据"""
        # Force refresh macro data
        await self.market_service.get_cockpit_macro_data(force_refresh=True)
