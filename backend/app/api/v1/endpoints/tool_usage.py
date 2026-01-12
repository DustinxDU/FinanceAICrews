"""
Tool Usage Statistics API

Tracks tool usage frequency and provides recommendations for commonly used tools.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.security import get_db, get_current_user
from AICrews.database.models import User, UserToolPreference
from AICrews.schemas.tool import (
    ToolUsageStats,
    ToolRecommendation,
    UsageStatsResponse,
)

router = APIRouter(prefix="/tool-usage", tags=["Tool Usage Statistics"])

@router.get("/stats", response_model=UsageStatsResponse, summary="获取工具使用统计")
async def get_tool_usage_stats(
    days: int = Query(30, description="统计天数", ge=1, le=365),
    limit: int = Query(10, description="返回最常用工具数量", ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取用户工具使用统计信息
    
    - **days**: 统计的天数范围
    - **limit**: 返回最常用工具的数量
    """
    # 计算时间范围
    start_date = datetime.now() - timedelta(days=days)
    
    # 查询用户工具偏好（暂时用作使用统计的基础）
    user_tools = db.query(UserToolPreference).filter(
        UserToolPreference.user_id == current_user.id,
        UserToolPreference.updated_at >= start_date
    ).all()
    
    # 模拟使用统计数据（实际应该从使用日志表获取）
    mock_usage_data = []
    for tool in user_tools:
        # 模拟使用次数和最后使用时间
        usage_count = hash(tool.tool_key) % 50 + 1  # 1-50次使用
        last_used = tool.updated_at
        avg_daily_usage = usage_count / days
        
        mock_usage_data.append(ToolUsageStats(
            tool_key=tool.tool_key,
            tool_name=tool.tool_key.split(':')[-1].replace('_', ' ').title(),
            source=tool.tool_source,
            category=tool.tool_key.split(':')[1] if ':' in tool.tool_key else 'unknown',
            usage_count=usage_count,
            last_used=last_used,
            avg_daily_usage=avg_daily_usage
        ))
    
    # 按使用次数排序
    most_used_tools = sorted(mock_usage_data, key=lambda x: x.usage_count, reverse=True)[:limit]
    
    # 生成推荐
    recommendations = []
    if len(most_used_tools) > 0:
        # 推荐同类别的其他工具
        popular_categories = {}
        for tool in most_used_tools:
            popular_categories[tool.category] = popular_categories.get(tool.category, 0) + 1
        
        # 找到最热门的类别
        top_category = max(popular_categories.keys(), key=lambda k: popular_categories[k])
        
        recommendations.append(ToolRecommendation(
            tool_key=f"recommended:{top_category}:advanced_tool",
            tool_name=f"Advanced {top_category.title()} Tool",
            source="system",
            category=top_category,
            reason=f"基于您对 {top_category} 类工具的频繁使用",
            score=0.85
        ))
    
    # 统计各类别使用情况
    usage_by_category = {}
    usage_by_source = {}
    total_usage = 0
    
    for tool in mock_usage_data:
        usage_by_category[tool.category] = usage_by_category.get(tool.category, 0) + tool.usage_count
        usage_by_source[tool.source] = usage_by_source.get(tool.source, 0) + tool.usage_count
        total_usage += tool.usage_count
    
    return UsageStatsResponse(
        total_usage=total_usage,
        most_used_tools=most_used_tools,
        recommendations=recommendations,
        usage_by_category=usage_by_category,
        usage_by_source=usage_by_source
    )

@router.post("/record", summary="记录工具使用")
async def record_tool_usage(
    tool_key: str = Query(..., description="工具标识"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    记录工具使用情况
    
    在实际应用中，这个端点会在工具被使用时自动调用
    """
    # 更新工具偏好的最后使用时间
    tool_pref = db.query(UserToolPreference).filter(
        UserToolPreference.user_id == current_user.id,
        UserToolPreference.tool_key == tool_key
    ).first()
    
    if tool_pref:
        tool_pref.updated_at = datetime.now()
        db.commit()
        return {"message": f"已记录工具 {tool_key} 的使用"}
    else:
        raise HTTPException(status_code=404, detail="工具偏好不存在")

@router.get("/trending", summary="获取热门工具")
async def get_trending_tools(
    days: int = Query(7, description="统计天数", ge=1, le=30),
    limit: int = Query(5, description="返回数量", ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    获取全平台热门工具（所有用户）
    """
    # 模拟热门工具数据
    trending_tools = [
        {
            "tool_key": "mcp:akshare:stock_zh_a_hist",
            "tool_name": "A股历史数据",
            "source": "mcp",
            "category": "data",
            "usage_count": 1250,
            "user_count": 89,
            "growth_rate": 0.23
        },
        {
            "tool_key": "quant:indicator:rsi",
            "tool_name": "RSI 指标",
            "source": "quant",
            "category": "indicator",
            "usage_count": 980,
            "user_count": 67,
            "growth_rate": 0.18
        },
        {
            "tool_key": "crewai:search:serper",
            "tool_name": "Serper 搜索",
            "source": "crewai",
            "category": "search",
            "usage_count": 756,
            "user_count": 45,
            "growth_rate": 0.31
        }
    ]
    
    return {
        "trending_tools": trending_tools[:limit],
        "period_days": days,
        "last_updated": datetime.now()
    }
