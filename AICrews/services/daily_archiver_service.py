"""
Daily Archiver Service - 日结归档服务

解决关键缺失环节：数据如何从 realtime_quotes 流入 market_prices？

问题：
- Sync Worker 只是不停地覆盖 realtime_quotes 快照
- AI Agent 需要 market_prices 历史数据
- 缺失的环节：快照如何变成历史？

解决方案：
- 每日定时任务（美东时间下午5:00，A股下午3:30）
- 读取 realtime_quotes 中当天的最终数据
- INSERT/UPSERT 进 market_prices 表，resolution='1d'
- 这样AI Agent明天就能看到今天的历史K线了

调度逻辑：
- 美股：美东时间 17:00 (收盘后1小时)
- A股：北京时间 15:30 (收盘时间)
- 港股：香港时间 16:00 (收盘时间)
- 加密货币：每日 00:00 UTC (24小时交易)
"""

import asyncio
from AICrews.observability.logging import get_logger
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, time
from dataclasses import dataclass
import pytz

from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import select, text, func
from sqlalchemy.exc import SQLAlchemyError

from AICrews.database.models import RealtimeQuote, Asset, ActiveMonitoring
from AICrews.database.db_manager import get_db_session

logger = get_logger(__name__)

@dataclass
class ArchivalTask:
    """归档任务配置"""
    market: str
    timezone: str
    schedule_time: time  # 本地时间
    asset_types: List[str]

class DailyArchiverService:
    """日结归档服务"""
    
    def __init__(self):
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        
        # 配置各市场的归档时间
        self.archival_tasks = [
            ArchivalTask(
                market="US",
                timezone="America/New_York",
                schedule_time=time(17, 0),  # 5:00 PM ET (收盘后1小时)
                asset_types=["US"]
            ),
            ArchivalTask(
                market="HK",
                timezone="Asia/Hong_Kong", 
                schedule_time=time(16, 0),  # 4:00 PM HKT (收盘时间)
                asset_types=["HK"]
            ),
            ArchivalTask(
                market="CN",
                timezone="Asia/Shanghai",
                schedule_time=time(15, 30),  # 3:30 PM CST (收盘时间)
                asset_types=["CN"]
            ),
            ArchivalTask(
                market="CRYPTO",
                timezone="UTC",
                schedule_time=time(0, 0),    # 12:00 AM UTC (每日重置)
                asset_types=["CRYPTO"]
            ),
            ArchivalTask(
                market="MACRO",
                timezone="UTC", 
                schedule_time=time(18, 0),   # 6:00 PM UTC (全球指标汇总)
                asset_types=["MACRO"]
            )
        ]
    
    async def start(self):
        """启动日结归档服务"""
        if self.is_running:
            logger.warning("Daily archiver service is already running")
            return
        
        self.is_running = True
        self._shutdown_event.clear()
        
        logger.info("Starting daily archiver service...")
        
        # 启动主循环
        asyncio.create_task(self._main_loop())
        
        logger.info("Daily archiver service started successfully")
    
    async def stop(self):
        """停止日结归档服务"""
        if not self.is_running:
            return
        
        logger.info("Stopping daily archiver service...")
        
        self.is_running = False
        self._shutdown_event.set()
        
        logger.info("Daily archiver service stopped")
    
    async def _main_loop(self):
        """主循环：每分钟检查是否需要执行归档任务"""
        while self.is_running:
            try:
                current_utc = datetime.now()
                
                # 检查每个市场是否到了归档时间
                for task in self.archival_tasks:
                    if await self._should_run_archival(task, current_utc):
                        logger.info(f"Executing daily archival for {task.market}")
                        await self._execute_archival(task)
                
                # 等待1分钟或收到停止信号
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=60.0)
                    break  # 收到停止信号
                except asyncio.TimeoutError:
                    continue  # 继续循环
                    
            except Exception as e:
                logger.error(f"Error in daily archiver main loop: {e}")
                await asyncio.sleep(60)
    
    async def _should_run_archival(self, task: ArchivalTask, current_utc: datetime) -> bool:
        """判断是否应该执行归档任务"""
        try:
            # 转换到市场本地时间
            tz = pytz.timezone(task.timezone)
            local_time = current_utc.replace(tzinfo=pytz.UTC).astimezone(tz)
            
            # 检查是否是归档时间（允许1分钟误差）
            target_time = task.schedule_time
            current_time = local_time.time()
            
            # 计算时间差（秒）
            target_seconds = target_time.hour * 3600 + target_time.minute * 60
            current_seconds = current_time.hour * 3600 + current_time.minute * 60
            
            time_diff = abs(target_seconds - current_seconds)
            
            # 如果在目标时间的1分钟内，且今天还未执行过
            if time_diff <= 60:
                return await self._check_not_executed_today(task, local_time.date())
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking archival schedule for {task.market}: {e}")
            return False
    
    async def _check_not_executed_today(self, task: ArchivalTask, local_date) -> bool:
        """检查今天是否已经执行过归档"""
        try:
            # 这里可以用Redis或数据库记录执行状态
            # 简化实现：检查market_prices表中是否已有今日数据
            async with get_db_session() as session:
                # asyncpg 需要 date 对象，不是字符串
                from datetime import date as date_type
                if isinstance(local_date, str):
                    local_date = datetime.strptime(local_date, '%Y-%m-%d').date()
                elif not isinstance(local_date, date_type):
                    local_date = local_date  # 已经是 date 对象

                result = await session.execute(
                    text("""
                    SELECT COUNT(*) as count
                    FROM market_prices mp
                    JOIN assets a ON mp.ticker = a.ticker
                    WHERE DATE(mp.date) = :today
                    AND a.asset_type = ANY(:asset_types)
                    AND mp.resolution = '1d'
                    """),
                    {
                        "today": local_date,
                        "asset_types": list(task.asset_types or [])
                    }
                )
                
                count = result.scalar()
                return count == 0  # 如果没有今日数据，说明未执行过
                
        except Exception as e:
            logger.error(f"Error checking execution status for {task.market}: {e}")
            return False
    
    async def _execute_archival(self, task: ArchivalTask):
        """执行归档任务：realtime_quotes → market_prices"""
        try:
            async with get_db_session() as session:
                # 1. 获取需要归档的realtime_quotes数据
                quotes_to_archive = await self._get_quotes_for_archival(session, task)
                
                if not quotes_to_archive:
                    logger.info(f"No quotes to archive for {task.market}")
                    return
                
                # 2. 转换并插入到market_prices表
                archived_count = 0
                for quote, asset in quotes_to_archive:
                    if await self._archive_quote_to_market_prices(session, quote, asset):
                        archived_count += 1
                
                await session.commit()
                
                logger.info(f"Successfully archived {archived_count} quotes for {task.market}")
                
        except Exception as e:
            logger.error(f"Error executing archival for {task.market}: {e}")
    
    async def _get_quotes_for_archival(self, session, task: ArchivalTask) -> List[tuple]:
        """获取需要归档的实时报价数据"""
        try:
            # 获取指定asset_types的所有活跃报价
            result = await session.execute(
                select(RealtimeQuote, Asset).join(Asset).where(
                    Asset.asset_type.in_(task.asset_types),
                    RealtimeQuote.price.is_not(None),  # 确保有价格数据
                    Asset.is_active == True
                )
            )
            
            return result.fetchall()
            
        except Exception as e:
            logger.error(f"Error getting quotes for archival: {e}")
            return []
    
    async def _archive_quote_to_market_prices(self, session, quote: RealtimeQuote, asset: Asset) -> bool:
        """将单个报价归档到market_prices表"""
        try:
            # 使用当前日期作为归档日期
            archive_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 插入到market_prices表（UPSERT逻辑）
            insert_query = text("""
                INSERT INTO market_prices (ticker, date, open, high, low, close, volume, resolution, source)
                VALUES (:ticker, :date, :open, :high, :low, :close, :volume, :resolution, :source)
                ON CONFLICT (ticker, date, resolution)
                DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume
            """)

            await session.execute(insert_query, {
                'ticker': quote.ticker,
                'date': archive_date,
                'open': quote.open_price or quote.price,  # 如果没有开盘价，用当前价
                'high': quote.high_price or quote.price,
                'low': quote.low_price or quote.price,
                'close': quote.price,  # 收盘价就是最新价
                'volume': quote.volume or 0,  # volume 是 NOT NULL，默认为 0
                'resolution': '1d',
                'source': quote.data_source or 'archive'  # 从实时报价继承数据来源
            })
            
            logger.debug(f"Archived {quote.ticker} to market_prices: close=${quote.price}")
            return True
            
        except Exception as e:
            logger.error(f"Error archiving quote for {quote.ticker}: {e}")
            return False
    
    async def force_archive_market(self, market: str) -> Dict[str, Any]:
        """手动触发特定市场的归档（用于测试和紧急情况）"""
        task = next((t for t in self.archival_tasks if t.market == market), None)
        
        if not task:
            return {"success": False, "error": f"Unknown market: {market}"}
        
        try:
            await self._execute_archival(task)
            return {"success": True, "message": f"Manual archival completed for {market}"}
        except Exception as e:
            logger.error(f"Error in manual archival for {market}: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_archival_status(self) -> Dict[str, Any]:
        """获取归档服务状态"""
        try:
            status = {
                "is_running": self.is_running,
                "markets": []
            }
            
            current_utc = datetime.now()
            
            for task in self.archival_tasks:
                try:
                    # 转换到本地时间
                    tz = pytz.timezone(task.timezone)
                    local_time = current_utc.replace(tzinfo=pytz.UTC).astimezone(tz)
                    
                    # 计算下次执行时间
                    next_run = self._calculate_next_run_time(task, local_time)
                    
                    market_status = {
                        "market": task.market,
                        "timezone": task.timezone,
                        "schedule_time": task.schedule_time.strftime("%H:%M"),
                        "local_time": local_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "next_run": next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None,
                        "asset_types": task.asset_types
                    }
                    
                    status["markets"].append(market_status)
                    
                except Exception as e:
                    logger.error(f"Error getting status for {task.market}: {e}")
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting archival status: {e}")
            return {"is_running": self.is_running, "error": str(e)}
    
    def _calculate_next_run_time(self, task: ArchivalTask, local_time: datetime) -> Optional[datetime]:
        """计算下次执行时间"""
        try:
            target_time = task.schedule_time
            today = local_time.date()
            
            # 今天的目标时间
            today_target = datetime.combine(today, target_time)
            today_target = pytz.timezone(task.timezone).localize(today_target)
            
            if local_time < today_target:
                # 今天还未到时间
                return today_target
            else:
                # 今天已过，明天执行
                tomorrow = today + timedelta(days=1)
                tomorrow_target = datetime.combine(tomorrow, target_time)
                return pytz.timezone(task.timezone).localize(tomorrow_target)
                
        except Exception as e:
            logger.error(f"Error calculating next run time: {e}")
            return None


# 全局服务实例
_daily_archiver_service: Optional[DailyArchiverService] = None

def get_daily_archiver_service() -> DailyArchiverService:
    """获取日结归档服务实例"""
    global _daily_archiver_service
    if _daily_archiver_service is None:
        _daily_archiver_service = DailyArchiverService()
    return _daily_archiver_service

async def start_daily_archiver_service():
    """启动日结归档服务"""
    service = get_daily_archiver_service()
    await service.start()

async def stop_daily_archiver_service():
    """停止日结归档服务"""
    service = get_daily_archiver_service()
    await service.stop()
