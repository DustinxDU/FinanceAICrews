from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class StrategyCreate(BaseModel):
    """创建策略请求"""
    name: str = Field(..., min_length=1, max_length=100, description="策略名称")
    description: Optional[str] = Field(None, max_length=500, description="策略描述")
    formula: str = Field(..., min_length=1, description="策略公式")
    category: str = Field("custom", description="策略类别: trend, momentum, volatility, custom")
    variables: Optional[Dict[str, Any]] = Field(None, description="公式变量定义")
    is_public: bool = Field(False, description="是否公开分享")

class StrategyUpdate(BaseModel):
    """更新策略请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    formula: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None

class StrategyResponse(BaseModel):
    """策略响应"""
    id: int
    name: str
    description: Optional[str]
    formula: str
    category: str
    variables: Optional[Dict[str, Any]]
    is_active: bool
    is_public: bool
    usage_count: int
    last_used_at: Optional[str]
    last_result: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True

class StrategyValidation(BaseModel):
    """策略验证请求"""
    formula: str = Field(..., description="要验证的策略公式")

class StrategyEvaluation(BaseModel):
    """策略评估请求"""
    ticker: str = Field(..., description="股票代码")
    strategy_id: Optional[int] = Field(None, description="策略 ID")
    formula: Optional[str] = Field(None, description="直接使用公式（不保存）")

class EvaluationResult(BaseModel):
    """评估结果"""
    ticker: str
    formula: str
    result: Optional[bool]
    signal: str
    context: Dict[str, Any]
    evaluated_at: str
    error: Optional[str] = None

class BatchEvaluationResponse(BaseModel):
    strategy_id: int
    strategy_name: str
    formula: str
    results: List[Dict[str, Any]]
    summary: Dict[str, int]
