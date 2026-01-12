from AICrews.observability.logging import get_logger
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import func, extract, and_, or_, desc
from sqlalchemy.orm import Session

from AICrews.database.models import ExecutionLog, AnalysisReport, UserLLMConfig, LLMModel, LLMProvider, User
from AICrews.schemas.usage import UsageStatsResponse, UsageActivityResponse, UsageActivityItem

logger = get_logger(__name__)

class UsageService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_token_cost(self, tokens: int, provider_key: str, model_name: str) -> float:
        """计算 token 成本"""
        try:
            # 获取模型信息
            model = self.db.query(LLMModel).join(LLMProvider).filter(
                LLMProvider.provider_key == provider_key,
                LLMModel.model_key == model_name
            ).first()

            if not model or not model.cost_per_million_output_tokens:
                # 默认估算成本 (OpenAI GPT-4 价格)
                return (tokens / 1000000) * 30.0

            # 按百万 token 计算成本
            return (tokens / 1000000) * model.cost_per_million_output_tokens
        except Exception as e:
            logger.warning(f"Failed to calculate token cost: {e}")
            return (tokens / 1000000) * 30.0

    def get_model_display_name(self, provider_key: str, model_name: str) -> str:
        """获取模型显示名称"""
        try:
            model = self.db.query(LLMModel).join(LLMProvider).filter(
                LLMProvider.provider_key == provider_key,
                LLMModel.model_key == model_name
            ).first()

            if model and model.display_name:
                return model.display_name
            return f"{provider_key}/{model_name}"
        except Exception as e:
            logger.warning(f"Failed to get model display name: {e}")
            return f"{provider_key}/{model_name}"

    async def get_usage_stats(self, user_id: int) -> UsageStatsResponse:
        """获取用户使用统计"""
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        
        previous_month_date = now.replace(day=1) - timedelta(days=1)
        previous_month = previous_month_date.month
        previous_year = previous_month_date.year
        
        # 本月 Token 总数
        total_tokens_current = self.db.query(func.sum(ExecutionLog.total_tokens)).filter(
            ExecutionLog.user_id == user_id,
            extract('month', ExecutionLog.created_at) == current_month,
            extract('year', ExecutionLog.created_at) == current_year
        ).scalar() or 0
        
        # 上月 Token 总数
        total_tokens_previous = self.db.query(func.sum(ExecutionLog.total_tokens)).filter(
            ExecutionLog.user_id == user_id,
            extract('month', ExecutionLog.created_at) == previous_month,
            extract('year', ExecutionLog.created_at) == previous_year
        ).scalar() or 0
        
        # 增长率
        growth_percentage = 0.0
        if total_tokens_previous > 0:
            growth_percentage = ((total_tokens_current - total_tokens_previous) / total_tokens_previous) * 100
        elif total_tokens_current > 0:
            growth_percentage = 100.0
            
        # 本月报告数
        reports_count = self.db.query(func.count(AnalysisReport.id)).filter(
            AnalysisReport.user_id == user_id,
            extract('month', AnalysisReport.date) == current_month,
            extract('year', AnalysisReport.date) == current_year
        ).scalar() or 0
        
        # 估算成本 (简化计算，遍历本月日志)
        logs = self.db.query(ExecutionLog).filter(
            ExecutionLog.user_id == user_id,
            extract('month', ExecutionLog.created_at) == current_month,
            extract('year', ExecutionLog.created_at) == current_year
        ).all()
        
        estimated_cost = 0.0
        for log in logs:
            if log.llm_provider and log.model_name and log.total_tokens:
                estimated_cost += self.calculate_token_cost(log.total_tokens, log.llm_provider, log.model_name)
                
        return UsageStatsResponse(
            total_tokens_current_month=int(total_tokens_current),
            total_tokens_previous_month=int(total_tokens_previous),
            token_growth_percentage=round(growth_percentage, 1),
            reports_generated_current_month=reports_count,
            estimated_cost_current_month=round(estimated_cost, 4)
        )

    async def get_activity_log(self, user_id: int, page: int = 1, limit: int = 20) -> UsageActivityResponse:
        """获取活动日志"""
        offset = (page - 1) * limit
        
        query = self.db.query(ExecutionLog).filter(ExecutionLog.user_id == user_id)
        total_count = query.count()
        
        logs = query.order_by(desc(ExecutionLog.created_at)).offset(offset).limit(limit).all()
        
        items = []
        for log in logs:
            model_display = self.get_model_display_name(log.llm_provider, log.model_name) if log.llm_provider else "Unknown"
            
            items.append(UsageActivityItem(
                id=log.id,
                date=log.created_at.strftime("%Y-%m-%d"),
                time=log.created_at.strftime("%H:%M"),
                activity=f"Generated {log.crew_name or 'Report'}",
                model=model_display,
                reports=1, # 假设每个 log 对应一个报告，实际可能需要关联
                tokens=log.total_tokens or 0
            ))
            
        return UsageActivityResponse(
            items=items,
            total_count=total_count,
            current_page=page,
            total_pages=(total_count + limit - 1) // limit
        )
