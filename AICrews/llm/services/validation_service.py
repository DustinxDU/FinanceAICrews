"""Validation 服务模块

真实验证提供商配置的服务。
"""

import asyncio
from AICrews.observability.logging import get_logger
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from AICrews.llm.core.config_store import get_config_store
from AICrews.llm.core.config_models import (
    ProviderConfig,
    ProviderType,
    AuthType,
    DiscoveryStrategy,
)
from AICrews.llm.core.http_client import get_http_client, HTTPClient
from AICrews.llm.core.env_redactor import (
    redact_api_key,
    redact_url,
    redact_headers,
)

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """验证结果。"""
    valid: bool
    message: str
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class ValidationService:
    """验证服务。
    
    负责验证提供商配置（执行真实 API 调用）。
    """
    
    def __init__(self, http_client: Optional[HTTPClient] = None):
        """初始化验证服务。
        
        Args:
            http_client: HTTP 客户端实例
        """
        self._config_store = get_config_store()
        self._http_client = http_client
    
    async def validate_provider_config(
        self,
        provider_key: str,
        api_key: str,
        base_url: Optional[str] = None,
        custom_model: Optional[str] = None,
        volcengine_endpoints: Optional[List[str]] = None,
    ) -> ValidationResult:
        """验证提供商配置。

        Args:
            provider_key: 提供商键
            api_key: API Key
            base_url: 自定义 Base URL（可选）
            custom_model: 自定义模型名（可选）
            volcengine_endpoints: 火山引擎端点列表（可选）

        Returns:
            ValidationResult: 验证结果
        """
        provider_config = self._config_store.get_provider(provider_key)
        if not provider_config:
            return ValidationResult(
                valid=False,
                message=f"Unknown provider: {provider_key}",
                error_code="PROVIDER_NOT_FOUND",
            )
        
        provider_type = provider_config.provider_type
        
        try:
            if provider_type == ProviderType.CREWAI_NATIVE:
                return await self._validate_crewai_native(
                    provider_key, provider_config, api_key, base_url
                )
            elif provider_type == ProviderType.OPENAI_COMPATIBLE:
                return await self._validate_openai_compatible(
                    provider_key, provider_config, api_key, base_url, custom_model
                )
            elif provider_type == ProviderType.VOLCENGINE:
                return await self._validate_volcengine(
                    provider_key, provider_config, api_key, base_url, custom_model, volcengine_endpoints
                )
            else:
                return await self._validate_generic(
                    provider_key, provider_config, api_key, base_url
                )
        except Exception as e:
            logger.exception(f"Validation error for {provider_key}: {e}")
            return ValidationResult(
                valid=False,
                message=f"Validation error: {str(e)}",
                error_code="VALIDATION_ERROR",
                error_details={"exception": type(e).__name__},
            )
    
    async def _validate_crewai_native(
        self,
        provider_key: str,
        provider_config: ProviderConfig,
        api_key: str,
        base_url: Optional[str],
    ) -> ValidationResult:
        """验证 CrewAI 原生提供商。"""
        client = self._get_http_client()
        
        # 构建请求
        endpoint = base_url or provider_config.endpoints.api_base
        if not endpoint:
            return ValidationResult(
                valid=False,
                message="No endpoint configured for this provider",
                error_code="NO_ENDPOINT",
            )
        
        # 使用通用 chat completions 验证
        url = f"{endpoint.rstrip('/')}/chat/completions"
        
        # 构建请求头
        headers = self._build_auth_headers(provider_config, api_key)
        
        # 特殊 provider 使用不同的 payload 格式
        payload, headers = self._build_validation_payload(
            provider_key, headers
        )
        
        try:
            response = await client.post(url, headers=headers, json_data=payload)
            
            if response.status_code == 200:
                return ValidationResult(
                    valid=True,
                    message=f"{provider_config.display_name} validation successful",
                )
            else:
                return self._parse_error_response(provider_key, response)
                
        except Exception as e:
            logger.error(f"Validation request failed: {e}")
            return ValidationResult(
                valid=False,
                message=f"Request failed: {str(e)}",
                error_code="REQUEST_FAILED",
            )
    
    async def _validate_openai_compatible(
        self,
        provider_key: str,
        provider_config: ProviderConfig,
        api_key: str,
        base_url: Optional[str],
        custom_model: Optional[str],
    ) -> ValidationResult:
        """验证 OpenAI 兼容提供商。"""
        client = self._get_http_client()
        
        endpoint = base_url or provider_config.endpoints.api_base
        if not endpoint:
            return ValidationResult(
                valid=False,
                message="No endpoint configured",
                error_code="NO_ENDPOINT",
            )
        
        url = f"{endpoint.rstrip('/')}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        # 添加 provider 特定的 header
        if provider_config.auth.headers:
            headers.update(provider_config.auth.headers)
        
        # Provider-specific validation models (2025 latest lightweight models)
        validation_models = {
            # 中国API提供商 (Chinese Providers)
            "zhipu_ai": "glm-4-flash",           # FREE, ~72 tokens/sec, 128K context (2025)
            "kimi_moonshot": "moonshot-v1-8k",   # Most lightweight V1 model
            "qianwen_dashscope": "qwen-flash",   # Most cost-effective, extremely fast (2025)
            "deepseek": "deepseek-chat",         # V3 general purpose, 128K context

            # 国际提供商 (International Providers)
            "openrouter": "meta-llama/llama-3-8b-instruct:free",  # Free tier
            "groq": "llama-3.3-8b-it",           # Fast small model on Groq
            "together": "meta-llama/Llama-3-8b-chat-hf",  # Cost-effective
        }

        # 确定使用的模型
        if custom_model:
            model = custom_model
        elif provider_key in validation_models:
            model = validation_models[provider_key]
        else:
            model = "gpt-3.5-turbo"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
        }
        
        try:
            response = await client.post(url, headers=headers, json_data=payload)
            
            if response.status_code == 200:
                return ValidationResult(
                    valid=True,
                    message=f"{provider_config.display_name} validation successful",
                )
            else:
                return self._parse_error_response(provider_key, response)
                
        except Exception as e:
            return ValidationResult(
                valid=False,
                message=f"Request failed: {str(e)}",
                error_code="REQUEST_FAILED",
            )
    
    async def _validate_volcengine(
        self,
        provider_key: str,
        provider_config: ProviderConfig,
        api_key: str,
        base_url: Optional[str],
        custom_model: Optional[str],
        volcengine_endpoints: Optional[List[str]] = None,
    ) -> ValidationResult:
        """验证火山引擎配置。"""
        client = self._get_http_client()
        
        endpoint = base_url or provider_config.endpoints.api_base
        if not endpoint:
            return ValidationResult(
                valid=False,
                message="No endpoint configured for Volcengine",
                error_code="NO_ENDPOINT",
            )
        
        url = f"{endpoint.rstrip('/')}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        # 火山引擎使用自定义模型名
        model = custom_model or "doubao-1.5-pro"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
        }
        
        try:
            response = await client.post(url, headers=headers, json_data=payload)
            
            if response.status_code == 200:
                return ValidationResult(
                    valid=True,
                    message="Volcengine validation successful",
                )
            else:
                return self._parse_error_response(provider_key, response)
                
        except Exception as e:
            return ValidationResult(
                valid=False,
                message=f"Request failed: {str(e)}",
                error_code="REQUEST_FAILED",
            )
    
    async def _validate_generic(
        self,
        provider_key: str,
        provider_config: ProviderConfig,
        api_key: str,
        base_url: Optional[str],
    ) -> ValidationResult:
        """通用验证方法。"""
        return await self._validate_openai_compatible(
            provider_key, provider_config, api_key, base_url, None
        )
    
    def _build_auth_headers(
        self, 
        provider_config: ProviderConfig, 
        api_key: str
    ) -> Dict[str, str]:
        """构建认证请求头。"""
        auth_type = provider_config.auth.type
        
        if auth_type == AuthType.BEARER:
            return {"Authorization": f"Bearer {api_key}"}
        elif auth_type == AuthType.QUERY_PARAM:
            param_key = provider_config.auth.query_param_key or "key"
            return {}
        elif auth_type == AuthType.API_KEY_HEADER:
            return {"X-API-Key": api_key}
        else:
            return {"Authorization": f"Bearer {api_key}"}
    
    def _build_validation_payload(
        self, 
        provider_key: str,
        headers: Dict[str, str],
    ) -> tuple[Dict[str, Any], Dict[str, str]]:
        """构建验证请求 payload。"""
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
        }
        
        if provider_key == "anthropic":
            # Anthropic 使用不同的 API 格式
            headers.update({
                "x-api-key": headers.get("Authorization", "").replace("Bearer ", ""),
                "anthropic-version": "2023-06-01",
            })
            del headers["Authorization"]
            payload = {
                "model": "claude-3-haiku-2024-11-20",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 5,
            }
        elif provider_key == "google_gemini":
            # Google Gemini 使用不同的 API 格式
            pass  # 使用默认格式
        
        return payload, headers
    
    def _parse_error_response(
        self, 
        provider_key: str, 
        response
    ) -> ValidationResult:
        """解析错误响应。"""
        status_code = response.status_code
        error_data = response.data
        
        # 提取错误信息
        error_msg = "Unknown error"
        if isinstance(error_data, dict):
            if "error" in error_data:
                error_obj = error_data["error"]
                if isinstance(error_obj, dict):
                    error_msg = error_obj.get("message", str(error_obj))
                else:
                    error_msg = str(error_obj)
            elif "message" in error_data:
                error_msg = error_data["message"]
            elif "detail" in error_data:
                error_msg = error_data["detail"]
        elif isinstance(error_data, str):
            error_msg = error_data
        
        # 特定 provider 的错误处理
        if provider_key == "google_gemini" and "API_KEY_INVALID" in error_msg:
            error_msg = "API Key 无效。请检查是否从 Google AI Studio 正确获取 API Key"
        elif provider_key == "google_gemini" and status_code == 429:
            error_msg = "API 配额超限或请求过于频繁"
        elif provider_key == "openrouter" and status_code == 401:
            error_msg = "API Key 无效或已过期"
        elif provider_key == "openrouter" and status_code == 429:
            error_msg = "API 请求频率超限"
        
        return ValidationResult(
            valid=False,
            message=f"Validation failed (HTTP {status_code}): {error_msg}",
            error_code=f"HTTP_{status_code}",
            error_details={
                "status_code": status_code,
                "raw_response": error_data,
                "provider": provider_key,
            }
        )
    
    def _get_http_client(self) -> HTTPClient:
        """获取 HTTP 客户端。"""
        if self._http_client is None:
            self._http_client = get_http_client()
        return self._http_client
    
    async def batch_validate(
        self,
        configs: List[Dict[str, Any]],
    ) -> Dict[str, ValidationResult]:
        """批量验证多个提供商配置。
        
        Args:
            configs: 配置列表，每个包含 provider_key, api_key, base_url
            
        Returns:
            Dict: provider_key -> ValidationResult
        """
        results = {}
        
        for config in configs:
            provider_key = config["provider_key"]
            api_key = config["api_key"]
            base_url = config.get("base_url")
            
            result = await self.validate_provider_config(
                provider_key, api_key, base_url
            )
            results[provider_key] = result
        
        return results


# 全局服务实例
_validation_service: Optional[ValidationService] = None


def get_validation_service() -> ValidationService:
    """获取全局验证服务实例。"""
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService()
    return _validation_service


def reset_validation_service() -> None:
    """重置验证服务（主要用于测试）。"""
    global _validation_service
    _validation_service = None
