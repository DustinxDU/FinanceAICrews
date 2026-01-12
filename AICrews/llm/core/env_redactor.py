"""环境变量脱敏模块

日志脱敏 API Key、Base URL、Headers 等敏感信息。
"""

import os
import re
from typing import Any, Dict, List, Optional, Union


class EnvRedactor:
    """环境变量脱敏器。
    
    用于在日志中脱敏敏感信息。
    """
    
    # 常见的 API Key 模式（部分掩码）
    KEY_PATTERNS = [
        r'(sk-[a-zA-Z0-9]{20,})',  # OpenAI API Key
        r'(sk-ant-api03-[a-zA-Z0-9\-]{50,})',  # Anthropic API Key
        r'(AIza[0-9A-Za-z\-]{35})',  # Google API Key
        r'(VOLCENGINE_API_KEY[a-zA-Z0-9]{50,})',  # 火山引擎 API Key
        r'(Bearer\s+[a-zA-Z0-9\-_.]{20,})',  # Bearer Token
    ]
    
    def __init__(self):
        self._compiled_patterns = [
            re.compile(pattern) for pattern in self.KEY_PATTERNS
        ]
    
    def redact_key(self, api_key: Optional[str]) -> Optional[str]:
        """脱敏 API Key。
        
        Args:
            api_key: 原始 API Key
            
        Returns:
            脱敏后的 API Key
        """
        if not api_key:
            return None
        
        redacted = api_key
        for pattern in self._compiled_patterns:
            redacted = pattern.sub(r'\1****', redacted)
        
        # 保留首尾字符，中间用 * 替代
        if len(redacted) > 8:
            redacted = redacted[:4] + '****' + redacted[-4:]
        
        return redacted
    
    def redact_url(self, url: Optional[str]) -> Optional[str]:
        """脱敏 URL（移除敏感查询参数）。
        
        Args:
            url: 原始 URL
            
        Returns:
            脱敏后的 URL
        """
        if not url:
            return None
        
        # 移除常见的敏感查询参数
        sensitive_params = ['key', 'api_key', 'token', 'secret', 'password']
        
        try:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            
            parsed = urlparse(url)
            params = parse_qs(parsed.query, keep_blank_values=True)
            
            # 脱敏敏感参数
            for param in sensitive_params:
                if param in params:
                    params[param] = ['****']
            
            # 重建 URL
            query = urlencode(params, doseq=True)
            redacted = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                query,
                parsed.fragment
            ))
            
            return redacted
        except Exception:
            # 如果解析失败，简单掩码处理
            return '****'
    
    def redact_headers(self, headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        """脱敏 HTTP Headers。
        
        Args:
            headers: 原始 Headers
            
        Returns:
            脱敏后的 Headers
        """
        if not headers:
            return {}
        
        sensitive_keys = {
            'authorization', 'x-api-key', 'api-key', 'x-goog-api-key',
            'x-anthropic-api-key', 'cookie', 'set-cookie',
        }
        
        redacted = {}
        for key, value in headers.items():
            if key.lower() in sensitive_keys:
                if 'bearer' in value.lower():
                    # Bearer token
                    redacted[key] = 'Bearer ****'
                elif len(value) > 8:
                    redacted[key] = value[:4] + '****' + value[-4:]
                else:
                    redacted[key] = '****'
            else:
                redacted[key] = value
        
        return redacted
    
    def redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """递归脱敏字典中的敏感信息。
        
        Args:
            data: 原始数据字典
            
        Returns:
            脱敏后的数据字典
        """
        if not data:
            return {}
        
        sensitive_keys = {
            'api_key', 'apiKey', 'api-key', 'apikey',
            'base_url', 'baseUrl', 'base-url',
            'secret', 'token', 'password',
        }
        
        redacted = {}
        for key, value in data.items():
            if key.lower() in sensitive_keys:
                if isinstance(value, str):
                    if 'http' in value.lower():
                        redacted[key] = self.redact_url(value)
                    else:
                        redacted[key] = self.redact_key(value)
                else:
                    redacted[key] = '****'
            elif isinstance(value, dict):
                redacted[key] = self.redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self.redact_dict(item) if isinstance(item, dict) 
                    else item 
                    for item in value
                ]
            else:
                redacted[key] = value
        
        return redacted
    
    def redact_text(self, text: str) -> str:
        """脱敏文本中的 API Key。
        
        Args:
            text: 原始文本
            
        Returns:
            脱敏后的文本
        """
        redacted = text
        for pattern in self._compiled_patterns:
            redacted = pattern.sub(r'[REDACTED]', redacted)
        return redacted


# 全局脱敏器实例
_redactor = EnvRedactor()


def redact_api_key(api_key: Optional[str]) -> Optional[str]:
    """脱敏 API Key。"""
    return _redactor.redact_key(api_key)


def redact_url(url: Optional[str]) -> Optional[str]:
    """脱敏 URL。"""
    return _redactor.redact_url(url)


def redact_headers(headers: Optional[Dict[str, str]]) -> Dict[str, str]:
    """脱敏 HTTP Headers。"""
    return _redactor.redact_headers(headers)


def redact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """递归脱敏字典中的敏感信息。"""
    return _redactor.redact_dict(data)


def redact_text(text: str) -> str:
    """脱敏文本中的 API Key。"""
    return _redactor.redact_text(text)


def safe_log_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """安全记录字典（自动脱敏敏感信息）。"""
    return redact_dict(data)
