from AICrews.observability.logging import get_logger
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import desc

from AICrews.database.models import User, UserStrategy
from AICrews.schemas.strategy import (
    StrategyCreate, StrategyUpdate, StrategyResponse,
    EvaluationResult, BatchEvaluationResponse
)
from AICrews.tools.expression_tools import ExpressionEngine

logger = get_logger(__name__)

class StrategyService:
    """策略管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.engine = ExpressionEngine()

    async def list_strategies(
        self, user_id: int, category: Optional[str] = None, include_public: bool = False
    ) -> List[StrategyResponse]:
        """获取用户的策略列表"""
        query = self.db.query(UserStrategy).filter(UserStrategy.user_id == user_id)
        
        if category:
            query = query.filter(UserStrategy.category == category)
        
        strategies = query.order_by(desc(UserStrategy.updated_at)).all()
        
        # 如果需要包含公开策略
        if include_public:
            public_strategies = self.db.query(UserStrategy).filter(
                UserStrategy.is_public == True,
                UserStrategy.user_id != user_id
            ).all()
            strategies.extend(public_strategies)
        
        return [self._strategy_to_response(s) for s in strategies]

    async def create_strategy(self, user_id: int, strategy: StrategyCreate) -> StrategyResponse:
        """创建新策略"""
        # 验证公式
        validation = await self.validate_formula(strategy.formula)
        if not validation["is_valid"]:
            raise ValueError(f"Invalid formula: {validation['error']}")
        
        # 检查名称是否重复
        existing = self.db.query(UserStrategy).filter(
            UserStrategy.user_id == user_id,
            UserStrategy.name == strategy.name
        ).first()
        
        if existing:
            raise ValueError("Strategy with this name already exists")
        
        # 创建策略
        new_strategy = UserStrategy(
            user_id=user_id,
            name=strategy.name,
            description=strategy.description,
            formula=strategy.formula,
            category=strategy.category,
            variables=strategy.variables,
            is_public=strategy.is_public,
            is_active=True
        )
        
        self.db.add(new_strategy)
        self.db.commit()
        self.db.refresh(new_strategy)
        
        logger.info(f"Strategy created: {new_strategy.id} by user {user_id}")
        return self._strategy_to_response(new_strategy)

    async def get_strategy(self, user_id: int, strategy_id: int) -> StrategyResponse:
        """获取策略详情"""
        strategy = self.db.query(UserStrategy).filter(UserStrategy.id == strategy_id).first()
        if not strategy:
            raise ValueError("Strategy not found")
        
        # 检查权限
        if strategy.user_id != user_id and not strategy.is_public:
            raise PermissionError("Access denied")
        
        return self._strategy_to_response(strategy)

    async def update_strategy(self, user_id: int, strategy_id: int, update: StrategyUpdate) -> StrategyResponse:
        """更新策略"""
        strategy = self.db.query(UserStrategy).filter(
            UserStrategy.id == strategy_id,
            UserStrategy.user_id == user_id
        ).first()
        
        if not strategy:
            raise ValueError("Strategy not found")
        
        # 如果更新公式，需要验证
        if update.formula:
            validation = await self.validate_formula(update.formula)
            if not validation["is_valid"]:
                raise ValueError(f"Invalid formula: {validation['error']}")
            strategy.formula = update.formula
        
        # 更新其他字段
        if update.name is not None: strategy.name = update.name
        if update.description is not None: strategy.description = update.description
        if update.category is not None: strategy.category = update.category
        if update.variables is not None: strategy.variables = update.variables
        if update.is_active is not None: strategy.is_active = update.is_active
        if update.is_public is not None: strategy.is_public = update.is_public
        
        self.db.commit()
        self.db.refresh(strategy)
        return self._strategy_to_response(strategy)

    async def delete_strategy(self, user_id: int, strategy_id: int) -> bool:
        """删除策略"""
        strategy = self.db.query(UserStrategy).filter(
            UserStrategy.id == strategy_id,
            UserStrategy.user_id == user_id
        ).first()
        
        if not strategy:
            raise ValueError("Strategy not found")
        
        self.db.delete(strategy)
        self.db.commit()
        return True

    async def validate_formula(self, formula: str) -> Dict[str, Any]:
        """验证策略公式语法和安全性"""
        is_valid, error = self.engine.validate_formula(formula)
        return {
            "is_valid": is_valid,
            "formula": formula,
            "error": error,
            "supported_functions": list(self.engine.SUPPORTED_FUNCTIONS.keys()),
            "supported_variables": self.engine.PRICE_VARIABLES
        }

    async def evaluate_strategy(
        self, user_id: int, ticker: str, strategy_id: Optional[int] = None, formula: Optional[str] = None
    ) -> EvaluationResult:
        """评估策略"""
        strategy = None
        
        # 如果提供了 strategy_id，从数据库获取公式
        if strategy_id:
            strategy = self.db.query(UserStrategy).filter(UserStrategy.id == strategy_id).first()
            if not strategy:
                raise ValueError("Strategy not found")
            if strategy.user_id != user_id and not strategy.is_public:
                raise PermissionError("Access denied")
            formula = strategy.formula
            
            # 更新使用统计
            strategy.usage_count += 1
            strategy.last_used_at = datetime.now()
        
        if not formula:
            raise ValueError("Formula or strategy_id required")
        
        try:
            result = await self.engine.evaluate_for_ticker(ticker, formula)
            
            # 缓存结果
            if strategy_id and strategy:
                strategy.last_result = result
                self.db.commit()
            
            return EvaluationResult(
                ticker=ticker,
                formula=formula,
                result=result.get("result"),
                signal="BUY" if result.get("result") else "NO SIGNAL",
                context=result.get("context", {}),
                evaluated_at=result.get("evaluated_at", datetime.now().isoformat()),
                error=result.get("error")
            )
        except Exception as e:
            logger.error(f"Strategy evaluation error: {e}")
            return EvaluationResult(
                ticker=ticker,
                formula=formula,
                result=None,
                signal="ERROR",
                context={},
                evaluated_at=datetime.now().isoformat(),
                error=str(e)
            )

    async def batch_evaluate_strategy(
        self, user_id: int, strategy_id: int, tickers: List[str]
    ) -> BatchEvaluationResponse:
        """批量评估策略"""
        strategy = self.db.query(UserStrategy).filter(UserStrategy.id == strategy_id).first()
        if not strategy:
            raise ValueError("Strategy not found")
        
        if strategy.user_id != user_id and not strategy.is_public:
            raise PermissionError("Access denied")
        
        results = []
        for ticker in tickers[:20]:  # 限制最多20个
            try:
                result = await self.engine.evaluate_for_ticker(ticker, strategy.formula)
                results.append({
                    "ticker": ticker,
                    "result": result.get("result"),
                    "signal": "BUY" if result.get("result") else "NO SIGNAL",
                    "error": result.get("error")
                })
            except Exception as e:
                results.append({
                    "ticker": ticker,
                    "result": None,
                    "signal": "ERROR",
                    "error": str(e)
                })
        
        # 更新使用统计
        strategy.usage_count += len(tickers)
        strategy.last_used_at = datetime.now()
        self.db.commit()
        
        return BatchEvaluationResponse(
            strategy_id=strategy_id,
            strategy_name=strategy.name,
            formula=strategy.formula,
            results=results,
            summary={
                "total": len(results),
                "signals": len([r for r in results if r["result"]]),
                "errors": len([r for r in results if r.get("error")])
            }
        )

    async def get_popular_strategies(self, category: Optional[str] = None, limit: int = 10) -> List[StrategyResponse]:
        """获取热门公开策略"""
        query = self.db.query(UserStrategy).filter(
            UserStrategy.is_public == True,
            UserStrategy.is_active == True
        )
        
        if category:
            query = query.filter(UserStrategy.category == category)
        
        strategies = query.order_by(desc(UserStrategy.usage_count)).limit(limit).all()
        return [self._strategy_to_response(s) for s in strategies]

    async def clone_strategy(self, user_id: int, strategy_id: int, new_name: Optional[str] = None) -> StrategyResponse:
        """克隆公开策略"""
        original = self.db.query(UserStrategy).filter(
            UserStrategy.id == strategy_id,
            UserStrategy.is_public == True
        ).first()
        
        if not original:
            raise ValueError("Public strategy not found")
        
        cloned = UserStrategy(
            user_id=user_id,
            name=new_name or f"{original.name} (Copy)",
            description=f"Cloned from: {original.name}",
            formula=original.formula,
            category=original.category,
            variables=original.variables,
            is_public=False,
            is_active=True
        )
        
        self.db.add(cloned)
        self.db.commit()
        self.db.refresh(cloned)
        
        return self._strategy_to_response(cloned)

    def _strategy_to_response(self, strategy: UserStrategy) -> StrategyResponse:
        """将 ORM 对象转换为响应模型"""
        return StrategyResponse(
            id=strategy.id,
            name=strategy.name,
            description=strategy.description,
            formula=strategy.formula,
            category=strategy.category,
            variables=strategy.variables,
            is_active=strategy.is_active,
            is_public=strategy.is_public,
            usage_count=strategy.usage_count,
            last_used_at=strategy.last_used_at.isoformat() if strategy.last_used_at else None,
            last_result=strategy.last_result,
            created_at=strategy.created_at.isoformat(),
            updated_at=strategy.updated_at.isoformat()
        )
