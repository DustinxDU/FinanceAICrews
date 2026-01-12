"""HTTP 客户端模块

统一的 aiohttp 客户端（超时/重试/UA）。
"""

import asyncio
from AICrews.observability.logging import get_logger
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

import aiohttp
from aiohttp import ClientTimeout, ClientError

from .env_redactor import redact_headers, redact_url

logger = get_logger(__name__)


@dataclass
class HTTPClientConfig:
    """HTTP 客户端配置。"""
    timeout_seconds: float = 15.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    user_agent: str = "FinanceAICrews-LLM/1.0"
    enable_logging: bool = True


@dataclass
class HTTPResponse:
    """HTTP 响应封装。"""
    status_code: int
    data: Any
    headers: Dict[str, str] = field(default_factory=dict)
    url: str = ""
    elapsed_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class HTTPClient:
    """统一的 HTTP 客户端。
    
    提供统一的请求方法，自动处理超时、重试、日志脱敏。
    """
    
    DEFAULT_CONFIG = HTTPClientConfig()
    
    def __init__(self, config: Optional[HTTPClientConfig] = None):
        """初始化 HTTP 客户端。
        
        Args:
            config: 客户端配置
        """
        self._config = config or self.DEFAULT_CONFIG
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """获取或创建 aiohttp Session。"""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=self._config.timeout_seconds)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": self._config.user_agent},
            )
        return self._session
    
    async def close(self) -> None:
        """关闭 HTTP Session。"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def __aenter__(self):
        """异步上下文管理器入口。"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出。"""
        await self.close()
    
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_on: Optional[set[int]] = None,
    ) -> HTTPResponse:
        """发送 GET 请求。
        
        Args:
            url: 请求 URL
            headers: 请求头
            params: 查询参数
            retry_on: 需要重试的 HTTP 状态码
            
        Returns:
            HTTPResponse: 响应对象
        """
        return await self._request(
            method="GET",
            url=url,
            headers=headers,
            params=params,
            retry_on=retry_on,
        )
    
    async def post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_on: Optional[set[int]] = None,
    ) -> HTTPResponse:
        """发送 POST 请求。
        
        Args:
            url: 请求 URL
            headers: 请求头
            json_data: JSON 数据
            retry_on: 需要重试的 HTTP 状态码
            
        Returns:
            HTTPResponse: 响应对象
        """
        return await self._request(
            method="POST",
            url=url,
            headers=headers,
            json_data=json_data,
            retry_on=retry_on,
        )
    
    async def _request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_on: Optional[set[int]] = None,
    ) -> HTTPResponse:
        """发送 HTTP 请求（带重试逻辑）。
        
        Args:
            method: HTTP 方法
            url: 请求 URL
            headers: 请求头
            params: 查询参数
            json_data: JSON 数据
            retry_on: 需要重试的 HTTP 状态码
            
        Returns:
            HTTPResponse: 响应对象
            
        Raises:
            ClientError: 请求失败
        """
        if retry_on is None:
            retry_on = {429, 500, 502, 503, 504}
        
        session = await self.get_session()
        
        last_error = None
        for attempt in range(self._config.max_retries):
            try:
                start_time = datetime.now()
                
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                ) as response:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    
                    # 解析响应
                    if response.content_type == 'application/json':
                        data = await response.json()
                    else:
                        data = await response.text()
                    
                    # 日志记录
                    if self._config.enable_logging:
                        logger.debug(
                            f"HTTP {method} {redact_url(url)} - "
                            f"Status: {response.status}, "
                            f"Elapsed: {elapsed:.2f}s"
                        )
                    
                    # 检查是否需要重试
                    if response.status in retry_on and attempt < self._config.max_retries - 1:
                        delay = self._config.retry_delay_seconds * (2 ** attempt)  # 指数退避
                        logger.warning(
                            f"HTTP {method} {redact_url(url)} returned {response.status}, "
                            f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self._config.max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    
                    return HTTPResponse(
                        status_code=response.status,
                        data=data,
                        headers=dict(response.headers),
                        url=url,
                        elapsed_seconds=elapsed,
                    )
                    
            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(
                    f"HTTP {method} {redact_url(url)} timeout, "
                    f"attempt {attempt + 1}/{self._config.max_retries}"
                )
            except ClientError as e:
                last_error = e
                logger.warning(
                    f"HTTP {method} {redact_url(url)} error: {type(e).__name__}, "
                    f"attempt {attempt + 1}/{self._config.max_retries}"
                )
            
            # 重试前等待
            if attempt < self._config.max_retries - 1:
                delay = self._config.retry_delay_seconds * (2 ** attempt)
                await asyncio.sleep(delay)
        
        # 所有重试都失败了
        if last_error:
            raise last_error
        raise ClientError(f"HTTP request failed after {self._config.max_retries} attempts")


# 全局默认客户端
_default_client: Optional[HTTPClient] = None


def get_http_client(config: Optional[HTTPClientConfig] = None) -> HTTPClient:
    """获取全局 HTTP 客户端实例。"""
    global _default_client
    if _default_client is None:
        _default_client = HTTPClient(config)
    return _default_client


async def close_http_client() -> None:
    """关闭全局 HTTP 客户端。"""
    global _default_client
    if _default_client:
        await _default_client.close()
        _default_client = None
