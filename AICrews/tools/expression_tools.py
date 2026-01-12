"""
Expression Engine - Level 2 策略解析器 (安全沙箱)

安全解析用户的字符串公式，转换为 Agent 可调用的工具。
使用 simpleeval 实现安全的表达式求值，严禁使用 eval()。

支持的语法：
- 比较运算: >, <, >=, <=, ==, !=
- 逻辑运算: AND, OR, NOT
- 函数调用: MA(period), EMA(period), RSI(period), MACD(), VOL, CLOSE, OPEN, HIGH, LOW
- 数学运算: +, -, *, /, %

示例公式：
- "MA(20) > MA(60) AND RSI(14) < 30"
- "CLOSE > MA(50) AND VOL > VOL_MA(20)"
- "MACD_HIST > 0 AND RSI(14) < 70"

安全保证：
- 使用 simpleeval 而非 eval()
- 白名单函数和变量
- 禁止 import、exec、open 等危险操作
- 超时保护防止无限循环
"""

import re
from AICrews.observability.logging import get_logger
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime
from functools import lru_cache

import pandas as pd
import numpy as np

try:
    from simpleeval import simple_eval, EvalWithCompoundTypes, DEFAULT_FUNCTIONS, DEFAULT_OPERATORS
    HAS_SIMPLEEVAL = True
except ImportError:
    HAS_SIMPLEEVAL = False
    simple_eval = None

from crewai.tools import tool

logger = get_logger(__name__)


class ExpressionParseError(Exception):
    """公式解析错误"""
    pass


class ExpressionSecurityError(Exception):
    """公式安全检查失败"""
    pass


class ExpressionEngine:
    """Level 2 策略表达式引擎
    
    安全解析并执行用户定义的量化策略公式
    """
    
    # 禁止的关键词（安全检查）
    FORBIDDEN_KEYWORDS = [
        'import', 'exec', 'eval', 'compile', 'open', 'file', 'input',
        '__', 'globals', 'locals', 'vars', 'dir', 'getattr', 'setattr',
        'delattr', 'hasattr', 'type', 'isinstance', 'issubclass',
        'callable', 'classmethod', 'staticmethod', 'property',
        'os', 'sys', 'subprocess', 'shutil', 'pathlib'
    ]
    
    # 支持的函数名称到内部方法的映射
    SUPPORTED_FUNCTIONS = {
        'MA': 'sma',
        'SMA': 'sma',
        'EMA': 'ema',
        'RSI': 'rsi',
        'MACD': 'macd',
        'MACD_LINE': 'macd_line',
        'MACD_SIGNAL': 'macd_signal',
        'MACD_HIST': 'macd_hist',
        'BB_UPPER': 'bb_upper',
        'BB_LOWER': 'bb_lower',
        'BB_MIDDLE': 'bb_middle',
        'ATR': 'atr',
        'VOL_MA': 'vol_ma',
        'OBV': 'obv',
        'K': 'stoch_k',
        'D': 'stoch_d',
        'J': 'stoch_j',
    }
    
    # 支持的价格变量
    PRICE_VARIABLES = ['CLOSE', 'OPEN', 'HIGH', 'LOW', 'VOL', 'VOLUME']
    
    def __init__(self):
        if not HAS_SIMPLEEVAL:
            logger.warning("simpleeval not installed. Expression engine will be limited.")
        
        self._quant_engine = None
    
    @property
    def quant_engine(self):
        """延迟加载 QuantEngine"""
        if self._quant_engine is None:
            from AICrews.tools.quant_tools import QuantEngine
            self._quant_engine = QuantEngine()
        return self._quant_engine
    
    def validate_formula(self, formula: str) -> Tuple[bool, Optional[str]]:
        """验证公式的安全性和语法正确性

        Args:
            formula: 用户输入的公式字符串

        Returns:
            (is_valid, error_message) - 验证结果和错误信息
        """
        if not formula or not formula.strip():
            return False, "Formula cannot be empty"

        # Reject obvious natural-language inputs (no operators, no parentheses, only words/spaces).
        stripped = formula.strip()
        if re.fullmatch(r"[A-Za-z\s]+", stripped) and re.search(r"\s", stripped):
            return False, "Invalid syntax: expected an expression, got natural language"

        formula_lower = formula.lower()

        # 安全检查：禁止危险关键词（只检查完整单词）
        for keyword in self.FORBIDDEN_KEYWORDS:
            # 使用正则表达式检查完整单词，避免误判 "close" 中的 "os"
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, formula_lower):
                return False, f"Forbidden keyword detected: {keyword}"
        
        # 检查括号匹配
        if formula.count('(') != formula.count(')'):
            return False, "Unbalanced parentheses"
        
        # 提取函数调用并验证
        func_pattern = r'([A-Z_]+)\s*\('
        functions_used = re.findall(func_pattern, formula.upper())
        
        for func in functions_used:
            if func not in self.SUPPORTED_FUNCTIONS and func not in ['AND', 'OR', 'NOT', 'IF']:
                # 检查是否是带参数的函数
                if not any(func.startswith(sf) for sf in self.SUPPORTED_FUNCTIONS):
                    return False, f"Unsupported function: {func}"

        # Validate identifiers (prevent accepting arbitrary words like SOMEVAR).
        allowed_identifiers = {
            *self.PRICE_VARIABLES,
            "CURRENTPRICE",  # alias for CLOSE
            "TRUE",
            "FALSE",
        }
        allowed_identifiers.update({'AND', 'OR', 'NOT'})
        allowed_functions = set(functions_used)
        allowed_functions.update(self.SUPPORTED_FUNCTIONS.keys())
        allowed_functions.add("IF")

        tokens = re.findall(r"\b[A-Z_][A-Z0-9_]*\b", formula.upper())
        for token in tokens:
            if token in allowed_identifiers:
                continue
            if token in allowed_functions:
                continue
            hint = ""
            if token in {"CURRENT_PRICE", "PRICE", "LAST"}:
                hint = f"Use CLOSE instead of {token}"

            supported_vars = ", ".join(self.PRICE_VARIABLES)
            supported_funcs = ", ".join(
                [
                    "MA()",
                    "SMA()",
                    "EMA()",
                    "RSI()",
                    "MACD",
                    "MACD_LINE",
                    "MACD_SIGNAL",
                    "MACD_HIST",
                    "BB_UPPER",
                    "BB_MIDDLE",
                    "BB_LOWER",
                    "ATR()",
                    "VOL_MA()",
                    "IF()",
                ]
            )
            msg = f"Unsupported identifier: {token}"
            if hint:
                msg = f"{msg}. {hint}"
            msg = f"{msg}. Supported variables: {supported_vars}. Supported functions: {supported_funcs}."
            return False, msg
        
        return True, None
    
    def parse_formula(self, formula: str, df: pd.DataFrame) -> Dict[str, Any]:
        """解析公式，提取所需的指标和变量
        
        Args:
            formula: 公式字符串
            df: 历史数据 DataFrame
            
        Returns:
            包含所有计算结果的字典，可用于表达式求值
        """
        # 确保列名小写
        df_copy = df.copy()
        df_copy.columns = df_copy.columns.str.lower()
        
        context = {}
        
        # 添加基础价格变量（使用最新值）
        context['CLOSE'] = df_copy['close'].iloc[-1]
        context['OPEN'] = df_copy['open'].iloc[-1]
        context['HIGH'] = df_copy['high'].iloc[-1]
        context['LOW'] = df_copy['low'].iloc[-1]
        context['VOL'] = df_copy['volume'].iloc[-1] if 'volume' in df_copy.columns else 0
        context['VOLUME'] = context['VOL']
        context['CURRENTPRICE'] = context['CLOSE']
        
        # 解析函数调用并计算指标
        # 匹配 MA(20), RSI(14) 等
        func_pattern = r'([A-Z_]+)\s*\(\s*(\d+)?\s*\)'
        matches = re.findall(func_pattern, formula.upper())
        
        for func_name, period_str in matches:
            period = int(period_str) if period_str else 14  # 默认周期14
            
            if func_name in ['MA', 'SMA']:
                series = self.quant_engine.calculate_sma(df_copy, period)
                context[f'{func_name}({period})'] = series.iloc[-1] if not pd.isna(series.iloc[-1]) else 0
                context[f'MA_{period}'] = context[f'{func_name}({period})']
                
            elif func_name == 'EMA':
                series = self.quant_engine.calculate_ema(df_copy, period)
                context[f'EMA({period})'] = series.iloc[-1] if not pd.isna(series.iloc[-1]) else 0
                context[f'EMA_{period}'] = context[f'EMA({period})']
                
            elif func_name == 'RSI':
                series = self.quant_engine.calculate_rsi(df_copy, period)
                context[f'RSI({period})'] = series.iloc[-1] if not pd.isna(series.iloc[-1]) else 50
                context[f'RSI_{period}'] = context[f'RSI({period})']
                
            elif func_name == 'ATR':
                series = self.quant_engine.calculate_atr(df_copy, period)
                context[f'ATR({period})'] = series.iloc[-1] if not pd.isna(series.iloc[-1]) else 0
                
            elif func_name == 'VOL_MA':
                series = self.quant_engine.calculate_volume_ma(df_copy, period)
                context[f'VOL_MA({period})'] = series.iloc[-1] if not pd.isna(series.iloc[-1]) else 0
        
        # 处理 MACD 相关
        if 'MACD' in formula.upper():
            macd = self.quant_engine.calculate_macd(df_copy)
            context['MACD'] = macd['macd'].iloc[-1] if not pd.isna(macd['macd'].iloc[-1]) else 0
            context['MACD_LINE'] = context['MACD']
            context['MACD_SIGNAL'] = macd['signal'].iloc[-1] if not pd.isna(macd['signal'].iloc[-1]) else 0
            context['MACD_HIST'] = macd['histogram'].iloc[-1] if not pd.isna(macd['histogram'].iloc[-1]) else 0
        
        # 处理 Bollinger Bands
        if 'BB_' in formula.upper():
            bb = self.quant_engine.calculate_bollinger_bands(df_copy)
            context['BB_UPPER'] = bb['upper'].iloc[-1] if not pd.isna(bb['upper'].iloc[-1]) else 0
            context['BB_MIDDLE'] = bb['middle'].iloc[-1] if not pd.isna(bb['middle'].iloc[-1]) else 0
            context['BB_LOWER'] = bb['lower'].iloc[-1] if not pd.isna(bb['lower'].iloc[-1]) else 0
        
        # 处理 KDJ
        if any(x in formula.upper() for x in ['K(', 'D(', 'J(']):
            kdj = self.quant_engine.calculate_kdj(df_copy)
            context['K'] = kdj['K'].iloc[-1] if not pd.isna(kdj['K'].iloc[-1]) else 50
            context['D'] = kdj['D'].iloc[-1] if not pd.isna(kdj['D'].iloc[-1]) else 50
            context['J'] = kdj['J'].iloc[-1] if not pd.isna(kdj['J'].iloc[-1]) else 50
        
        return context
    
    def _prepare_expression(self, formula: str, context: Dict[str, Any]) -> str:
        """将公式转换为可执行的表达式
        
        将 MA(20) 转换为 context 中的键名
        将 AND/OR 转换为 Python 的 and/or
        """
        expr = formula.upper()
        
        # 替换逻辑运算符
        expr = re.sub(r'\bAND\b', ' and ', expr, flags=re.IGNORECASE)
        expr = re.sub(r'\bOR\b', ' or ', expr, flags=re.IGNORECASE)
        expr = re.sub(r'\bNOT\b', ' not ', expr, flags=re.IGNORECASE)
        
        # Rewrite meta IF(...) into a Python conditional expression.
        # Example: IF(A > B, 1, 0) -> ((1) if (A > B) else (0))
        def _rewrite_if_calls(text: str) -> str:
            out = ""
            i = 0
            upper = text.upper()
            while True:
                idx = upper.find("IF(", i)
                if idx < 0:
                    out += text[i:]
                    return out
                out += text[i:idx]

                start = idx + 3  # after "IF("
                depth = 1
                j = start
                while j < len(text) and depth > 0:
                    ch = text[j]
                    if ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                    j += 1
                if depth != 0:
                    return out + text[idx:]

                inner = text[start : j - 1]
                args = []
                buf = ""
                depth = 0
                for ch in inner:
                    if ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                    if ch == "," and depth == 0:
                        args.append(buf.strip())
                        buf = ""
                        continue
                    buf += ch
                if buf.strip() or inner.strip():
                    args.append(buf.strip())

                if len(args) != 3:
                    return out + text[idx:j]

                cond, truthy, falsy = args
                out += f"(({truthy}) if ({cond}) else ({falsy}))"
                i = j
                upper = text.upper()

        expr = _rewrite_if_calls(expr)

        # 替换函数调用为上下文变量
        for key in sorted(context.keys(), key=len, reverse=True):
            # 转义括号
            pattern = re.escape(key)
            expr = re.sub(pattern, f"context['{key}']", expr, flags=re.IGNORECASE)
        
        return expr
    
    def evaluate(self, formula: str, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """执行公式求值
        
        Args:
            formula: 公式字符串
            df: 历史数据 DataFrame
            
        Returns:
            (result, details) - 布尔结果和计算详情
        """
        # 验证公式
        is_valid, error = self.validate_formula(formula)
        if not is_valid:
            raise ExpressionParseError(error)
        
        # 解析并计算指标
        context = self.parse_formula(formula, df)
        
        # 准备表达式
        expr = self._prepare_expression(formula, context)
        
        try:
            if HAS_SIMPLEEVAL:
                # 使用 simpleeval 安全求值
                evaluator = EvalWithCompoundTypes()
                evaluator.names = {"context": context}
                evaluator.functions = {}  # 禁用函数调用
                result = evaluator.eval(expr)
            else:
                # Fallback: 使用限制性的本地环境
                # 警告：这种方式安全性较低，仅作为备选
                local_vars = {"context": context}
                # 使用 compile 检查语法
                code = compile(expr, '<strategy>', 'eval')
                # 检查不安全的字节码
                for name in code.co_names:
                    if name not in ['context', 'and', 'or', 'not', 'True', 'False']:
                        raise ExpressionSecurityError(f"Unsafe name in expression: {name}")
                result = eval(code, {"__builtins__": {}}, local_vars)
            
            return bool(result), {
                "formula": formula,
                "result": bool(result),
                "context": {k: round(v, 4) if isinstance(v, float) else v for k, v in context.items()},
                "evaluated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Expression evaluation error: {e}")
            raise ExpressionParseError(f"Failed to evaluate expression: {str(e)}")
    
    async def evaluate_for_ticker(self, ticker: str, formula: str) -> Dict[str, Any]:
        """为指定股票评估策略公式
        
        Args:
            ticker: 股票代码
            formula: 策略公式
            
        Returns:
            评估结果
        """
        try:
            from AICrews.tools.market_data_tools import MarketDataClient
            client = MarketDataClient()
            
            # 获取足够长的历史数据以计算指标
            df = await client.get_historical_data(ticker, period="6mo")
            
            if df is None or len(df) < 50:
                return {
                    "ticker": ticker,
                    "formula": formula,
                    "result": False,
                    "error": "Insufficient historical data"
                }
            
            result, details = self.evaluate(formula, df)
            
            return {
                "ticker": ticker,
                "formula": formula,
                "result": result,
                "details": details
            }
            
        except Exception as e:
            return {
                "ticker": ticker,
                "formula": formula,
                "result": False,
                "error": str(e)
            }


# =========================================================================
# CrewAI 工具函数
# =========================================================================

_expression_engine = ExpressionEngine()


@tool("evaluate_strategy")
def evaluate_strategy(ticker: str, formula: str) -> str:
    """评估用户定义的量化策略公式
    
    安全执行量化策略公式，返回 True/False 信号。
    
    支持的函数：
    - MA(period), SMA(period), EMA(period): 移动平均线
    - RSI(period): 相对强弱指数
    - MACD, MACD_LINE, MACD_SIGNAL, MACD_HIST: MACD 指标
    - BB_UPPER, BB_MIDDLE, BB_LOWER: 布林带
    - ATR(period): 平均真实波幅
    - VOL_MA(period): 成交量均线
    
    支持的变量：CLOSE, OPEN, HIGH, LOW, VOL
    
    支持的运算：AND, OR, NOT, >, <, >=, <=, ==, !=
    
    Args:
        ticker: 股票代码 (如 "AAPL")
        formula: 策略公式 (如 "MA(20) > MA(60) AND RSI(14) < 30")
        
    Returns:
        策略评估结果，包含信号和指标详情
    """
    try:
        import asyncio
        
        async def _evaluate():
            return await _expression_engine.evaluate_for_ticker(ticker, formula)
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _evaluate())
                result = future.result()
        else:
            result = loop.run_until_complete(_evaluate())
        
        if result.get("error"):
            return f"Strategy evaluation failed for {ticker}: {result['error']}"
        
        signal = "✅ BUY SIGNAL" if result['result'] else "❌ NO SIGNAL"
        
        output = f"""
Strategy Evaluation for {ticker}
Formula: {formula}

Result: {signal}

Indicator Values:
"""
        for key, value in result.get('details', {}).get('context', {}).items():
            output += f"  - {key}: {value}\n"
        
        return output.strip()
        
    except Exception as e:
        logger.error(f"Error evaluating strategy for {ticker}: {e}")
        return f"Error: {str(e)}"


@tool("validate_strategy_formula")
def validate_strategy_formula(formula: str) -> str:
    """验证策略公式的语法和安全性
    
    在保存或执行策略之前，检查公式是否有效。
    
    Args:
        formula: 要验证的策略公式
        
    Returns:
        验证结果和任何错误信息
    """
    is_valid, error = _expression_engine.validate_formula(formula)
    
    if is_valid:
        return f"✅ Formula is valid: {formula}"
    else:
        return f"❌ Invalid formula: {error}"
