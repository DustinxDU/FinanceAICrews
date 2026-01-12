"""
数据预取优化器 - 自动计算策略所需的最小历史数据长度

解决问题：
- 避免因数据不足导致的指标计算失败
- 根据策略公式自动推断需要的数据长度
- 优化数据获取效率
"""

import re
from AICrews.observability.logging import get_logger
from typing import Dict, List, Optional, Tuple

logger = get_logger(__name__)


class DataPrefetchOptimizer:
    """数据预取优化器
    
    分析策略表达式，计算所需的最小历史数据天数
    """
    
    # 指标名称到参数位置的映射
    INDICATOR_PARAMS = {
        'MA': [0],          # MA(period)
        'SMA': [0],         # SMA(period)
        'EMA': [0],         # EMA(period)
        'RSI': [0],         # RSI(period)
        'MACD': [0, 1, 2],  # MACD(fast, slow, signal)
        'BOLL': [0],        # BOLL(period)
        'ATR': [0],         # ATR(period)
        'ADX': [0],         # ADX(period)
        'CCI': [0],         # CCI(period)
        'MFI': [0],         # MFI(period)
        'OBV': [],          # OBV() - no period param
        'STOCH': [0, 1],    # STOCH(k_period, d_period)
    }
    
    # 指标计算所需的额外预热天数（warmup period）
    INDICATOR_WARMUP = {
        'MA': 0,
        'SMA': 0,
        'EMA': 20,      # EMA需要额外预热
        'RSI': 14,      # RSI需要至少14天来计算初始值
        'MACD': 35,     # MACD需要额外预热期
        'BOLL': 0,
        'ATR': 14,
        'ADX': 14,
        'CCI': 0,
        'MFI': 0,
        'OBV': 0,
        'STOCH': 0,
    }
    
    # 默认最小数据天数（如果无法解析）
    DEFAULT_MIN_DAYS = 252  # 1年
    
    # 安全边际（额外获取的天数百分比）
    SAFETY_MARGIN = 0.2  # 20%
    
    @classmethod
    def analyze_expression(cls, expression: str) -> Dict[str, any]:
        """分析策略表达式
        
        Args:
            expression: 策略表达式，例如 "MA(20) > MA(60)"
            
        Returns:
            分析结果字典
        """
        result = {
            'indicators': [],
            'min_days_required': cls.DEFAULT_MIN_DAYS,
            'recommended_period': '1y',
            'warnings': [],
        }
        
        if not expression or not expression.strip():
            result['warnings'].append('Empty expression')
            return result
        
        # 提取所有指标调用
        indicators = cls._extract_indicators(expression)
        result['indicators'] = indicators
        
        if not indicators:
            result['warnings'].append('No indicators found in expression')
            return result
        
        # 计算最小天数
        min_days = cls._calculate_min_days(indicators)
        
        # 添加安全边际
        recommended_days = int(min_days * (1 + cls.SAFETY_MARGIN))
        
        result['min_days_required'] = min_days
        result['recommended_days'] = recommended_days
        result['recommended_period'] = cls._days_to_period(recommended_days)
        
        logger.info(
            f"Expression analysis: indicators={len(indicators)}, "
            f"min_days={min_days}, recommended={recommended_days}"
        )
        
        return result
    
    @classmethod
    def _extract_indicators(cls, expression: str) -> List[Dict[str, any]]:
        """提取表达式中的所有指标调用
        
        Args:
            expression: 策略表达式
            
        Returns:
            指标列表，每个指标包含 name 和 params
        """
        indicators = []
        
        # 匹配模式：INDICATOR(param1, param2, ...)
        pattern = r'([A-Z_]+)\s*\(([^)]*)\)'
        
        matches = re.finditer(pattern, expression)
        
        for match in matches:
            indicator_name = match.group(1)
            params_str = match.group(2)
            
            # 跳过非指标函数（如 Crossover）
            if indicator_name not in cls.INDICATOR_PARAMS:
                continue
            
            # 解析参数
            params = []
            if params_str.strip():
                param_parts = [p.strip() for p in params_str.split(',')]
                for p in param_parts:
                    try:
                        # 尝试转换为整数
                        params.append(int(p))
                    except ValueError:
                        # 如果不是数字，可能是嵌套调用或变量
                        params.append(p)
            
            indicators.append({
                'name': indicator_name,
                'params': params,
                'raw': match.group(0),
            })
        
        return indicators
    
    @classmethod
    def _calculate_min_days(cls, indicators: List[Dict[str, any]]) -> int:
        """计算指标列表需要的最小天数
        
        Args:
            indicators: 指标列表
            
        Returns:
            最小天数
        """
        max_days = 0
        
        for indicator in indicators:
            name = indicator['name']
            params = indicator['params']
            
            # 获取该指标关心的参数位置
            param_positions = cls.INDICATOR_PARAMS.get(name, [])
            
            # 提取相关参数值
            period_values = []
            for pos in param_positions:
                if pos < len(params) and isinstance(params[pos], int):
                    period_values.append(params[pos])
            
            # 计算该指标需要的天数
            if period_values:
                # 取最大参数值（如 MACD(12,26,9) 取 26）
                indicator_period = max(period_values)
            else:
                # 无参数或参数无效，使用默认值
                indicator_period = 20
            
            # 添加预热天数
            warmup = cls.INDICATOR_WARMUP.get(name, 0)
            total_days = indicator_period + warmup
            
            logger.debug(
                f"Indicator {name}{params}: period={indicator_period}, "
                f"warmup={warmup}, total={total_days}"
            )
            
            max_days = max(max_days, total_days)
        
        # 至少需要60天（约3个月）
        return max(max_days, 60)
    
    @classmethod
    def _days_to_period(cls, days: int) -> str:
        """将天数转换为period参数
        
        Args:
            days: 天数
            
        Returns:
            period字符串，如 '3mo', '1y', '2y'
        """
        if days <= 90:
            return '3mo'
        elif days <= 180:
            return '6mo'
        elif days <= 365:
            return '1y'
        elif days <= 730:
            return '2y'
        else:
            years = (days // 365) + 1
            return f'{years}y'
    
    @classmethod
    def get_recommended_period(cls, expression: str) -> str:
        """获取推荐的数据获取周期
        
        Args:
            expression: 策略表达式
            
        Returns:
            推荐的period参数
        """
        result = cls.analyze_expression(expression)
        return result['recommended_period']
    
    @classmethod
    def validate_data_length(
        cls,
        expression: str,
        available_days: int
    ) -> Tuple[bool, Optional[str]]:
        """验证可用数据长度是否足够
        
        Args:
            expression: 策略表达式
            available_days: 可用的数据天数
            
        Returns:
            (is_sufficient, error_message)
        """
        result = cls.analyze_expression(expression)
        min_days = result['min_days_required']
        
        if available_days < min_days:
            return False, (
                f"Insufficient data: expression requires at least {min_days} days, "
                f"but only {available_days} days available. "
                f"Recommended period: {result['recommended_period']}"
            )
        
        return True, None


# 便捷函数
def get_required_period(expression: str) -> str:
    """获取策略表达式所需的数据周期
    
    Example:
        >>> get_required_period("MA(200) > MA(50)")
        '1y'
        >>> get_required_period("RSI(14) < 30")
        '3mo'
    """
    return DataPrefetchOptimizer.get_recommended_period(expression)


def analyze_strategy_data_needs(expression: str) -> Dict[str, any]:
    """分析策略的数据需求
    
    Example:
        >>> result = analyze_strategy_data_needs("MA(20) > MA(60) AND RSI(14) < 30")
        >>> print(result['min_days_required'])
        72
        >>> print(result['recommended_period'])
        '6mo'
    """
    return DataPrefetchOptimizer.analyze_expression(expression)


__all__ = [
    'DataPrefetchOptimizer',
    'get_required_period',
    'analyze_strategy_data_needs',
]
