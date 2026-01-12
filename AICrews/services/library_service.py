from AICrews.observability.logging import get_logger
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session

from AICrews.database.models import User, UserAssetInsight, InsightAttachment, InsightTrace
from AICrews.schemas.library import (
    InsightResponse, AssetGroupResponse, TimelineEntryResponse, InsightDetailResponse, LibraryInsight
)

logger = get_logger(__name__)

class LibraryService:
    def __init__(self, db: Session):
        self.db = db

    async def list_assets(self, user_id: int) -> List[AssetGroupResponse]:
        """获取用户关注的资产列表（按 ticker 聚合）"""
        # 按 ticker 分组查询
        subquery = (
            self.db.query(
                UserAssetInsight.ticker,
                func.max(UserAssetInsight.created_at).label('max_created')
            )
            .filter(UserAssetInsight.user_id == user_id)
            .group_by(UserAssetInsight.ticker)
            .subquery()
        )
        
        # 获取每个 ticker 的最新分析
        latest_insights = (
            self.db.query(UserAssetInsight)
            .join(
                subquery,
                (UserAssetInsight.ticker == subquery.c.ticker) &
                (UserAssetInsight.created_at == subquery.c.max_created)
            )
            .filter(UserAssetInsight.user_id == user_id)
            .order_by(desc(UserAssetInsight.created_at))
            .all()
        )
        
        # 按 ticker 分组
        asset_map: Dict[str, AssetGroupResponse] = {}
        for insight in latest_insights:
            # 过滤掉 SQLAlchemy 内部属性
            insight_dict = {k: v for k, v in insight.__dict__.items() if not k.startswith('_sa_')}
            
            # 获取该资产的附件数量
            attachments_count = self.db.query(InsightAttachment).filter(
                InsightAttachment.insight_id == insight.id
            ).count()
            
            # 获取该资产的所有分析记录
            all_insights = (
                self.db.query(UserAssetInsight)
                .filter(UserAssetInsight.user_id == user_id)
                .filter(UserAssetInsight.ticker == insight.ticker)
                .order_by(desc(UserAssetInsight.analysis_date))
                .limit(10)
                .all()
            )
            
            asset_map[insight.ticker] = AssetGroupResponse(
                ticker=insight.ticker,
                asset_name=insight.asset_name,
                asset_type=insight.asset_type,
                insights_count=self.db.query(UserAssetInsight).filter(
                    UserAssetInsight.user_id == user_id,
                    UserAssetInsight.ticker == insight.ticker
                ).count(),
                last_analysis_at=insight.analysis_date,
                latest_sentiment=insight.sentiment,
                latest_signal=insight.signal,
                insights=[
                    InsightResponse(
                        **{
                            **{k: v for k, v in i.__dict__.items() if not k.startswith('_sa_')},
                            'attachments_count': self.db.query(InsightAttachment).filter(
                                InsightAttachment.insight_id == i.id
                            ).count()
                        }
                    )
                    for i in all_insights
                ]
            )
        
        return list(asset_map.values())

    async def get_timeline(self, user_id: int, days: int = 30, ticker: Optional[str] = None) -> List[TimelineEntryResponse]:
        """获取分析时间轴"""
        start_date = datetime.now() - timedelta(days=days)
        
        query = (
            self.db.query(
                func.date(UserAssetInsight.analysis_date).label('date'),
                func.count(UserAssetInsight.id).label('count'),
            )
            .filter(UserAssetInsight.user_id == user_id)
            .filter(UserAssetInsight.analysis_date >= start_date)
        )
        
        if ticker:
            query = query.filter(UserAssetInsight.ticker == ticker)
        
        results = (
            query.group_by('date')
            .order_by(asc('date'))
            .all()
        )
        
        timeline = []
        for row in results:
            # 获取该日期的来源类型和 ticker
            date_insights = (
                self.db.query(UserAssetInsight)
                .filter(UserAssetInsight.user_id == user_id)
                .filter(func.date(UserAssetInsight.analysis_date) == row.date)
                .all()
            )
            
            sources = list(set(i.source_type for i in date_insights))
            tickers = list(set(i.ticker for i in date_insights))
            
            timeline.append(TimelineEntryResponse(
                date=row.date.strftime('%Y-%m-%d'),
                insights_count=row.count,
                sources=sources,
                tickers=tickers
            ))
        
        return timeline

    async def list_insights(
        self,
        user_id: int,
        ticker: Optional[str] = None,
        source_type: Optional[str] = None,
        sentiment: Optional[str] = None,
        signal: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[LibraryInsight]:
        """获取分析洞察列表"""
        query = self.db.query(UserAssetInsight).filter(
            UserAssetInsight.user_id == user_id
        )
        
        if ticker:
            query = query.filter(UserAssetInsight.ticker == ticker)
        if source_type:
            query = query.filter(UserAssetInsight.source_type == source_type)
        if sentiment:
            query = query.filter(UserAssetInsight.sentiment == sentiment)
        if signal:
            query = query.filter(UserAssetInsight.signal == signal)
        
        # 获取总数
        total = query.count()
        
        # 分页查询
        insights = (
            query
            .order_by(desc(UserAssetInsight.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        results = []
        for insight in insights:
            attachments_count = self.db.query(InsightAttachment).filter(
                InsightAttachment.insight_id == insight.id
            ).count()
            
            results.append(LibraryInsight(
                id=insight.id,
                ticker=insight.ticker,
                asset_name=insight.asset_name,
                asset_type=insight.asset_type,
                source_type=insight.source_type,
                source_id=insight.source_id,
                crew_name=insight.crew_name,
                title=insight.title,
                summary=insight.summary,
                sentiment=insight.sentiment,
                sentiment_score=insight.sentiment_score,
                signal=insight.signal,
                key_metrics=insight.key_metrics,
                tags=insight.tags,
                is_favorite=insight.is_favorite,
                is_read=insight.is_read,
                analysis_date=insight.analysis_date,
                created_at=insight.created_at,
                attachments_count=attachments_count
            ))
        
        return results

    async def get_insight_detail(self, user_id: int, insight_id: int) -> Optional[InsightDetailResponse]:
        """获取分析详情"""
        # 获取分析记录
        insight = self.db.query(UserAssetInsight).filter(
            UserAssetInsight.id == insight_id,
            UserAssetInsight.user_id == user_id
        ).first()
        
        if not insight:
            return None
        
        # 获取附件
        attachments = (
            self.db.query(InsightAttachment)
            .filter(InsightAttachment.insight_id == insight_id)
            .all()
        )
        
        # 获取追溯日志
        traces = (
            self.db.query(InsightTrace)
            .filter(InsightTrace.insight_id == insight_id)
            .order_by(InsightTrace.step_order)
            .all()
        )
        
        # 获取附件数量
        attachments_count = len(attachments)
        
        return InsightDetailResponse(
            insight=InsightResponse(
                **{
                    **{k: v for k, v in insight.__dict__.items() if not k.startswith('_sa_')},
                    'attachments_count': attachments_count
                }
            ),
            attachments=[
                {
                    'id': a.id,
                    'file_name': a.file_name,
                    'file_type': a.file_type,
                    'file_size': a.file_size,
                    'description': a.description,
                }
                for a in attachments
            ],
            traces=[
                {
                    'id': t.id,
                    'agent_name': t.agent_name,
                    'action_type': t.action_type,
                    'content': t.content,
                    'step_order': t.step_order,
                    'tokens_used': t.tokens_used,
                    'duration_ms': t.duration_ms,
                    'created_at': t.created_at.isoformat() if t.created_at else None,
                    'input_data': t.input_data,
                    'output_data': t.output_data,
                }
                for t in traces
            ]
        )

    async def mark_as_read(self, user_id: int, insight_id: int) -> bool:
        """标记洞察为已读"""
        insight = self.db.query(UserAssetInsight).filter(
            UserAssetInsight.id == insight_id,
            UserAssetInsight.user_id == user_id
        ).first()

        if not insight:
            return False

        insight.is_read = True
        self.db.commit()
        return True

    async def toggle_favorite(self, user_id: int, insight_id: int, is_favorite: bool) -> bool:
        """切换收藏状态"""
        insight = self.db.query(UserAssetInsight).filter(
            UserAssetInsight.id == insight_id,
            UserAssetInsight.user_id == user_id
        ).first()

        if not insight:
            return False

        insight.is_favorite = is_favorite
        self.db.commit()
        return True
