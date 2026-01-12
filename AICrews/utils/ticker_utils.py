"""
Ticker symbol normalization and validation utilities.

Handles conversion of stock tickers to standard formats required by different data providers.
"""

import re
from typing import Optional


def normalize_ticker(ticker: str, market_hint: Optional[str] = None) -> str:
    """
    Normalize ticker symbol to standard format for data providers.
    
    Args:
        ticker: Raw ticker symbol (e.g., "0700", "AAPL", "BTC-USD")
        market_hint: Optional market hint ("HK", "CN", "US", etc.)
    
    Returns:
        Normalized ticker symbol
    
    Examples:
        >>> normalize_ticker("0700", "HK")
        "0700.HK"
        >>> normalize_ticker("600000", "CN")
        "600000.SS"
        >>> normalize_ticker("AAPL")
        "AAPL"
        >>> normalize_ticker("0700.HK")
        "0700.HK"
    """
    if not ticker:
        return ticker
    
    ticker = ticker.strip().upper()
    
    # Already normalized (has suffix)
    if '.' in ticker or '-' in ticker:
        return ticker
    
    # Hong Kong stocks: 4-digit codes (0001-9999)
    if re.match(r'^\d{4}$', ticker):
        if market_hint == "HK" or not market_hint:
            return f"{ticker}.HK"
    
    # China A-share stocks: 6-digit codes starting with 6/0/3
    if re.match(r'^[630]\d{5}$', ticker):
        # Shanghai Stock Exchange: starts with 6
        if ticker.startswith('6'):
            return f"{ticker}.SS"
        # Shenzhen Stock Exchange: starts with 0 or 3
        else:
            return f"{ticker}.SZ"
    
    # Cryptocurrency pairs without suffix
    if market_hint == "CRYPTO":
        if not ticker.endswith('-USD') and not ticker.endswith('USDT'):
            return f"{ticker}-USD"
    
    # Default: return as-is for US stocks and others
    return ticker


def detect_market_from_ticker(ticker: str) -> str:
    """
    Detect market type from ticker format.
    
    Args:
        ticker: Ticker symbol
    
    Returns:
        Market type: "HK", "CN", "US", "CRYPTO", "UNKNOWN"
    """
    if not ticker:
        return "UNKNOWN"
    
    ticker = ticker.strip().upper()
    
    # Hong Kong
    if ticker.endswith('.HK') or ticker.endswith('.HKEX'):
        return "HK"
    
    # China A-share
    if ticker.endswith('.SS') or ticker.endswith('.SZ'):
        return "CN"
    
    # Crypto
    if '-USD' in ticker or 'USDT' in ticker or ticker.endswith('-USDT'):
        return "CRYPTO"
    
    # 4-digit code likely HK
    if re.match(r'^\d{4}$', ticker):
        return "HK"
    
    # 6-digit code likely CN
    if re.match(r'^[630]\d{5}$', ticker):
        return "CN"
    
    # Default to US
    return "US"


def validate_ticker(ticker: str) -> tuple[bool, Optional[str]]:
    """
    Validate ticker format.
    
    Args:
        ticker: Ticker symbol to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not ticker:
        return False, "Ticker cannot be empty"
    
    ticker = ticker.strip()
    
    if len(ticker) < 1:
        return False, "Ticker too short"
    
    if len(ticker) > 20:
        return False, "Ticker too long (max 20 characters)"
    
    # Allow alphanumeric, dots, hyphens, underscores
    if not re.match(r'^[A-Za-z0-9._-]+$', ticker):
        return False, "Ticker contains invalid characters (only A-Z, 0-9, ., -, _ allowed)"
    
    return True, None
