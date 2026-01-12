"""
Quant Engine - 原生量化计算引擎

基于 pandas-ta 提供核心技术指标计算能力。
将复杂的 DataFrame 操作封装成简单的输入输出，供 Agent 调用。

支持的指标：
- 趋势类: MA, EMA, SMA, MACD
- 动量类: RSI, KDJ, Stochastic
- 波动类: Bollinger Bands, ATR
- 成交量: OBV, VWAP, Volume MA

使用方式:
    engine = QuantEngine()
    
    # 获取技术摘要
    summary = await engine.get_technical_summary("AAPL")
    
    # 计算单个指标
    rsi = engine.calculate_rsi(df, period=14)
"""

from AICrews.observability.logging import get_logger
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from functools import lru_cache
import asyncio
import concurrent.futures

import pandas as pd
import numpy as np

try:
    import pandas_ta as ta
    HAS_PANDAS_TA = True
except ImportError:
    HAS_PANDAS_TA = False
    ta = None

from crewai.tools import tool
from AICrews.tools.market_data_tools import MarketDataClient

logger = get_logger(__name__)


class QuantEngine:
    """原生量化计算引擎
    
    封装 pandas-ta 的技术指标计算，提供简单易用的接口
    """
    
    def __init__(self):
        if not HAS_PANDAS_TA:
            logger.warning("pandas-ta not installed. Some features will be limited.")
    
    # =========================================================================
    # 核心指标计算方法
    # =========================================================================
    
    def calculate_sma(self, df: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
        """计算简单移动平均线"""
        if HAS_PANDAS_TA:
            return ta.sma(df[column], length=period)
        return df[column].rolling(window=period).mean()
    
    def calculate_ema(self, df: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
        """计算指数移动平均线"""
        if HAS_PANDAS_TA:
            return ta.ema(df[column], length=period)
        return df[column].ewm(span=period, adjust=False).mean()
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14, column: str = "close") -> pd.Series:
        """计算相对强弱指数"""
        if HAS_PANDAS_TA:
            return ta.rsi(df[column], length=period)
        
        # 手动计算 RSI
        delta = df[column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9, 
                       column: str = "close") -> Dict[str, pd.Series]:
        """计算 MACD 指标"""
        if HAS_PANDAS_TA:
            macd_df = ta.macd(df[column], fast=fast, slow=slow, signal=signal)
            if macd_df is not None:
                return {
                    "macd": macd_df.iloc[:, 0],
                    "signal": macd_df.iloc[:, 1],
                    "histogram": macd_df.iloc[:, 2]
                }
        
        # 手动计算
        ema_fast = df[column].ewm(span=fast, adjust=False).mean()
        ema_slow = df[column].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram
        }
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2.0,
                                   column: str = "close") -> Dict[str, pd.Series]:
        """计算布林带"""
        if HAS_PANDAS_TA:
            bb = ta.bbands(df[column], length=period, std=std_dev)
            if bb is not None:
                return {
                    "upper": bb.iloc[:, 0],
                    "middle": bb.iloc[:, 1],
                    "lower": bb.iloc[:, 2]
                }
        
        # 手动计算
        middle = df[column].rolling(window=period).mean()
        std = df[column].rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return {"upper": upper, "middle": middle, "lower": lower}
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算平均真实波幅"""
        if HAS_PANDAS_TA:
            return ta.atr(df["high"], df["low"], df["close"], length=period)
        
        # 手动计算
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
    
    def calculate_kdj(self, df: pd.DataFrame, k_period: int = 9, d_period: int = 3) -> Dict[str, pd.Series]:
        """计算 KDJ 指标"""
        if HAS_PANDAS_TA:
            stoch = ta.stoch(df["high"], df["low"], df["close"], k=k_period, d=d_period)
            if stoch is not None:
                k = stoch.iloc[:, 0]
                d = stoch.iloc[:, 1]
                j = 3 * k - 2 * d
                return {"K": k, "D": d, "J": j}
        
        # 手动计算
        low_min = df["low"].rolling(window=k_period).min()
        high_max = df["high"].rolling(window=k_period).max()
        rsv = (df["close"] - low_min) / (high_max - low_min) * 100
        k = rsv.ewm(span=d_period, adjust=False).mean()
        d = k.ewm(span=d_period, adjust=False).mean()
        j = 3 * k - 2 * d
        
        return {"K": k, "D": d, "J": j}
    
    def calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """计算能量潮指标"""
        if HAS_PANDAS_TA:
            return ta.obv(df["close"], df["volume"])
        
        # 手动计算
        obv = (np.sign(df["close"].diff()) * df["volume"]).fillna(0).cumsum()
        return obv
    
    def calculate_volume_ma(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """计算成交量移动平均"""
        return df["volume"].rolling(window=period).mean()
    
    # =========================================================================
    # 高级分析方法
    # =========================================================================
    
    def get_indicator_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """获取所有指标的信号状态"""
        if len(df) < 30:
            return {"error": "Insufficient data (need at least 30 bars)"}
        
        # 确保列名小写
        df.columns = df.columns.str.lower()
        
        current_close = df["close"].iloc[-1]
        
        # 计算各指标
        sma_20 = self.calculate_sma(df, 20)
        sma_50 = self.calculate_sma(df, 50) if len(df) >= 50 else None
        ema_12 = self.calculate_ema(df, 12)
        rsi_14 = self.calculate_rsi(df, 14)
        macd = self.calculate_macd(df)
        bb = self.calculate_bollinger_bands(df)
        
        signals = {
            "current_price": current_close,
            "sma_20": {
                "value": round(sma_20.iloc[-1], 2) if not pd.isna(sma_20.iloc[-1]) else None,
                "signal": "bullish" if current_close > sma_20.iloc[-1] else "bearish"
            },
            "rsi_14": {
                "value": round(rsi_14.iloc[-1], 2) if not pd.isna(rsi_14.iloc[-1]) else None,
                "signal": "overbought" if rsi_14.iloc[-1] > 70 else "oversold" if rsi_14.iloc[-1] < 30 else "neutral"
            },
            "macd": {
                "value": round(macd["macd"].iloc[-1], 4) if not pd.isna(macd["macd"].iloc[-1]) else None,
                "histogram": round(macd["histogram"].iloc[-1], 4) if not pd.isna(macd["histogram"].iloc[-1]) else None,
                "signal": "bullish" if macd["histogram"].iloc[-1] > 0 else "bearish"
            },
            "bollinger": {
                "upper": round(bb["upper"].iloc[-1], 2) if not pd.isna(bb["upper"].iloc[-1]) else None,
                "lower": round(bb["lower"].iloc[-1], 2) if not pd.isna(bb["lower"].iloc[-1]) else None,
                "signal": "overbought" if current_close > bb["upper"].iloc[-1] else "oversold" if current_close < bb["lower"].iloc[-1] else "neutral"
            }
        }
        
        if sma_50 is not None and len(sma_50) >= 50:
            signals["sma_50"] = {
                "value": round(sma_50.iloc[-1], 2) if not pd.isna(sma_50.iloc[-1]) else None,
                "signal": "bullish" if current_close > sma_50.iloc[-1] else "bearish"
            }
            # 金叉/死叉判断
            if sma_20.iloc[-1] > sma_50.iloc[-1] and sma_20.iloc[-2] <= sma_50.iloc[-2]:
                signals["cross"] = "golden_cross"
            elif sma_20.iloc[-1] < sma_50.iloc[-1] and sma_20.iloc[-2] >= sma_50.iloc[-2]:
                signals["cross"] = "death_cross"
        
        return signals
    
    def get_trend_assessment(self, df: pd.DataFrame) -> Dict[str, Any]:
        """评估当前趋势"""
        if len(df) < 50:
            return {"trend": "unknown", "strength": 0, "reason": "Insufficient data"}
        
        df.columns = df.columns.str.lower()
        
        current_close = df["close"].iloc[-1]
        sma_20 = self.calculate_sma(df, 20).iloc[-1]
        sma_50 = self.calculate_sma(df, 50).iloc[-1]
        rsi = self.calculate_rsi(df, 14).iloc[-1]
        macd = self.calculate_macd(df)
        macd_hist = macd["histogram"].iloc[-1]
        
        # 评分系统
        bullish_score = 0
        bearish_score = 0
        
        # MA 趋势
        if current_close > sma_20:
            bullish_score += 1
        else:
            bearish_score += 1
            
        if current_close > sma_50:
            bullish_score += 1
        else:
            bearish_score += 1
            
        if sma_20 > sma_50:
            bullish_score += 1
        else:
            bearish_score += 1
        
        # RSI 趋势
        if rsi > 50:
            bullish_score += 1
        else:
            bearish_score += 1
        
        # MACD 趋势
        if macd_hist > 0:
            bullish_score += 1
        else:
            bearish_score += 1
        
        total = bullish_score + bearish_score
        
        if bullish_score > bearish_score:
            trend = "bullish"
            strength = bullish_score / total
        elif bearish_score > bullish_score:
            trend = "bearish"
            strength = bearish_score / total
        else:
            trend = "neutral"
            strength = 0.5
        
        return {
            "trend": trend,
            "strength": round(strength, 2),
            "bullish_signals": bullish_score,
            "bearish_signals": bearish_score,
            "indicators": {
                "price_vs_sma20": "above" if current_close > sma_20 else "below",
                "price_vs_sma50": "above" if current_close > sma_50 else "below",
                "sma20_vs_sma50": "above" if sma_20 > sma_50 else "below",
                "rsi": round(rsi, 2),
                "macd_histogram": round(macd_hist, 4)
            }
        }
    
    def calculate_support_resistance(
        self, 
        df: pd.DataFrame, 
        method: str = "pivot",
        num_levels: int = 5
    ) -> Dict[str, Any]:
        """计算支撑位和阻力位
        
        Args:
            df: 价格数据
            method: 计算方法 (pivot, fibonacci, atr)
            num_levels: 返回的支撑/阻力位数量
            
        Returns:
            包含支撑位和阻力位的字典
        """
        if len(df) < 20:
            return {"error": "Insufficient data (need at least 20 bars)"}
        
        df.columns = df.columns.str.lower()
        
        high = df["high"]
        low = df["low"]
        close = df["close"]
        
        if method == "pivot":
            # 传统枢轴点计算
            pivot = (high + low + close) / 3
            
            r1 = 2 * pivot - low
            r2 = pivot + (high - low)
            r3 = high + 2 * (pivot - low)
            s1 = 2 * pivot - high
            s2 = pivot - (high - low)
            s3 = low - 2 * (high - pivot)
            
            resistance = [round(r1.iloc[-1], 2), round(r2.iloc[-1], 2), round(r3.iloc[-1], 2)]
            support = [round(s1.iloc[-1], 2), round(s2.iloc[-1], 2), round(s3.iloc[-1], 2)]
            
        elif method == "fibonacci":
            # 斐波那契回撤位
            swing_high = high.max()
            swing_low = low.min()
            diff = swing_high - swing_low
            
            levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]
            fib_levels = [(swing_high - level * diff) for level in levels]
            
            current_price = close.iloc[-1]
            
            # 找到当前价格附近的斐波那契位
            resistance = [round(l, 2) for l in fib_levels if l > current_price][:num_levels]
            support = list(reversed([round(l, 2) for l in fib_levels if l < current_price]))[-num_levels:]
            
        elif method == "atr":
            # 基于 ATR 的支撑阻力
            atr = self.calculate_atr(df, period=14)
            current_price = close.iloc[-1]
            atr_value = atr.iloc[-1]
            
            resistance = [
                round(current_price + i * atr_value, 2)
                for i in range(1, num_levels + 1)
            ]
            support = [
                round(current_price - i * atr_value, 2)
                for i in range(1, num_levels + 1)
            ]
        else:
            return {"error": f"Unknown method: {method}. Supported: pivot, fibonacci, atr"}
        
        return {
            "method": method,
            "current_price": round(close.iloc[-1], 2),
            "resistance": resistance[:num_levels],
            "support": support[:num_levels],
            "distance_to_resistance": round((resistance[0] - close.iloc[-1]) / close.iloc[-1] * 100, 2) if resistance else None,
            "distance_to_support": round((close.iloc[-1] - support[-1]) / close.iloc[-1] * 100, 2) if support else None,
        }


# =========================================================================
# CrewAI 工具函数
# =========================================================================

_quant_engine = QuantEngine()


@tool("get_technical_summary")
def get_technical_summary(ticker: str) -> str:
    """获取股票的技术分析摘要
    
    分析内容包括：RSI、MACD、移动平均线、布林带等技术指标的当前状态和信号。
    
    Args:
        ticker: 股票代码 (如 "AAPL", "MSFT")
        
    Returns:
        技术分析摘要文本，包含各指标状态和交易信号
    """
    try:
        # 这里需要从数据源获取历史数据
        # 目前返回模板响应，实际使用时需要集成数据源
        
        async def _get_summary():
            client = MarketDataClient()
            df = await client.get_historical_data(ticker, period="3mo")
            
            if df is None or len(df) < 30:
                return f"Unable to get sufficient historical data for {ticker}"
            
            signals = _quant_engine.get_indicator_signals(df)
            trend = _quant_engine.get_trend_assessment(df)
            
            summary = f'''
## {ticker} Technical Analysis Summary

### Trend Assessment
- **Overall Trend**: {trend['trend'].upper()}
- **Strength**: {trend['strength']*100:.0f}%
- **Bullish Signals**: {trend['bullish_signals']}
- **Bearish Signals**: {trend['bearish_signals']}

### Key Indicators
- **Current Price**: ${signals['current_price']:.2f}
- **SMA(20)**: ${signals['sma_20']['value']} ({signals['sma_20']['signal']})
- **RSI(14)**: {signals['rsi_14']['value']} ({signals['rsi_14']['signal']})
- **MACD**: {signals['macd']['signal']} (histogram: {signals['macd']['histogram']})
- **Bollinger Bands**: {signals['bollinger']['signal']}

### Trading Signal
Based on technical indicators, the stock shows a **{trend['trend']}** bias.
'''.strip()
            return summary
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_summary())
                return future.result()
        else:
            return loop.run_until_complete(_get_summary())
            
    except Exception as e:
        logger.error(f"Error getting technical summary for {ticker}: {e}")
        return f"Error analyzing {ticker}: {str(e)}"


@tool("calculate_indicator")
def calculate_indicator(ticker: str, indicator: str, period: int = 14) -> str:
    """计算指定的技术指标
    
    Args:
        ticker: 股票代码
        indicator: 指标名称 (rsi, macd, sma, ema, bollinger, atr, kdj)
        period: 计算周期，默认14
        
    Returns:
        指标计算结果
    """
    try:
        
        async def _calculate():
            client = MarketDataClient()
            df = await client.get_historical_data(ticker, period="3mo")
            
            if df is None or len(df) < period:
                return f"Insufficient data for {ticker}"
            
            df.columns = df.columns.str.lower()
            indicator_lower = indicator.lower()
            
            if indicator_lower == "rsi":
                result = _quant_engine.calculate_rsi(df, period)
                value = result.iloc[-1]
                return f"RSI({period}) for {ticker}: {value:.2f}"
                
            elif indicator_lower == "macd":
                result = _quant_engine.calculate_macd(df)
                return f"MACD for {ticker}: Line={result['macd'].iloc[-1]:.4f}, Signal={result['signal'].iloc[-1]:.4f}, Histogram={result['histogram'].iloc[-1]:.4f}"
                
            elif indicator_lower in ["sma", "ma"]:
                result = _quant_engine.calculate_sma(df, period)
                return f"SMA({period}) for {ticker}: ${result.iloc[-1]:.2f}"
                
            elif indicator_lower == "ema":
                result = _quant_engine.calculate_ema(df, period)
                return f"EMA({period}) for {ticker}: ${result.iloc[-1]:.2f}"
                
            elif indicator_lower == "bollinger":
                result = _quant_engine.calculate_bollinger_bands(df, period)
                return f"Bollinger Bands({period}) for {ticker}: Upper=${result['upper'].iloc[-1]:.2f}, Middle=${result['middle'].iloc[-1]:.2f}, Lower=${result['lower'].iloc[-1]:.2f}"
                
            elif indicator_lower == "atr":
                result = _quant_engine.calculate_atr(df, period)
                return f"ATR({period}) for {ticker}: {result.iloc[-1]:.2f}"
                
            elif indicator_lower == "kdj":
                result = _quant_engine.calculate_kdj(df, period)
                return f"KDJ({period}) for {ticker}: K={result['K'].iloc[-1]:.2f}, D={result['D'].iloc[-1]:.2f}, J={result['J'].iloc[-1]:.2f}"
            else:
                return f"Unknown indicator: {indicator}. Supported: rsi, macd, sma, ema, bollinger, atr, kdj"
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _calculate())
                return future.result()
        else:
            return loop.run_until_complete(_calculate())
            
    except Exception as e:
        logger.error(f"Error calculating {indicator} for {ticker}: {e}")
        return f"Error: {str(e)}"


@tool("check_trend")
def check_trend(ticker: str) -> str:
    """检查股票的当前趋势方向和强度
    
    Args:
        ticker: 股票代码
        
    Returns:
        趋势分析结果，包含趋势方向、强度和关键指标状态
    """
    try:
        
        async def _check():
            client = MarketDataClient()
            df = await client.get_historical_data(ticker, period="3mo")
            
            if df is None or len(df) < 50:
                return f"Insufficient data for trend analysis of {ticker}"
            
            trend = _quant_engine.get_trend_assessment(df)
            
            return f'''
Trend Analysis for {ticker}:
- Trend: {trend['trend'].upper()}
- Strength: {trend['strength']*100:.0f}%
- Price vs SMA20: {trend['indicators']['price_vs_sma20']}
- Price vs SMA50: {trend['indicators']['price_vs_sma50']}
- RSI: {trend['indicators']['rsi']}
- MACD Histogram: {trend['indicators']['macd_histogram']}
'''.strip()
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _check())
                return future.result()
        else:
            return loop.run_until_complete(_check())
            
    except Exception as e:
        logger.error(f"Error checking trend for {ticker}: {e}")
        return f"Error: {str(e)}"


@tool("support_resistance")
def support_resistance(ticker: str, method: str = "pivot", num_levels: int = 3) -> str:
    """计算股票的支撑位和阻力位
    
    Args:
        ticker: 股票代码
        method: 计算方法 (pivot, fibonacci, atr)
        num_levels: 返回的支撑/阻力位数量，默认3个
        
    Returns:
        支撑位和阻力位分析结果
    """
    try:
        
        async def _calculate():
            client = MarketDataClient()
            df = await client.get_historical_data(ticker, period="3mo")
            
            if df is None or len(df) < 20:
                return f"Insufficient data for support/resistance analysis of {ticker}"
            
            result = _quant_engine.calculate_support_resistance(df, method, num_levels)
            
            if "error" in result:
                return f"Error: {result['error']}"
            
            output = f'''
## Support & Resistance Analysis for {ticker}

### Current Price
**${result['current_price']}**

### Resistance Levels (Top-Down)
'''
            for i, level in enumerate(result['resistance'], 1):
                distance = result.get('distance_to_resistance')
                dist_str = f" (+{distance}%)" if distance else ""
                output += f"  {i}. ${level}{dist_str}\n"
            
            output += "\n### Support Levels (Bottom-Up)\n"
            for i, level in enumerate(result['support'], 1):
                distance = result.get('distance_to_support')
                dist_str = f" (-{distance}%)" if distance else ""
                output += f"  {i}. ${level}{dist_str}\n"
            
            return output.strip()
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _calculate())
                return future.result()
        else:
            return loop.run_until_complete(_calculate())
            
    except Exception as e:
        logger.error(f"Error calculating support/resistance for {ticker}: {e}")
        return f"Error: {str(e)}"
