"""Model 服务模块

模型发现 + 缓存 + 标签合并服务。
LRU cache with bounded size to prevent unbounded growth.
"""

import asyncio
import hashlib
from AICrews.observability.logging import get_logger
import os
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from AICrews.llm.core.config_store import get_config_store
from AICrews.llm.core.config_models import DiscoveryStrategy, ProviderConfig
from AICrews.llm.core.http_client import get_http_client, HTTPClient
from AICrews.llm.core.env_redactor import redact_api_key

logger = get_logger(__name__)


@dataclass
class ModelInfo:
    """模型信息。"""
    model_key: str
    display_name: str
    context_length: Optional[int] = None
    supports_tools: bool = False
    performance_level: Optional[str] = None
    is_thinking: bool = False
    provider_key: str = ""
    pricing: Optional[Dict[str, float]] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "model_key": self.model_key,
            "display_name": self.display_name,
            "context_length": self.context_length,
            "supports_tools": self.supports_tools,
            "performance_level": self.performance_level,
            "is_thinking": self.is_thinking,
            "pricing": self.pricing,
        }


@dataclass
class ModelCacheKey:
    """模型缓存键。"""
    provider_key: str
    identity: str  # api_key hash + base_url
    
    def __str__(self) -> str:
        return f"{self.provider_key}:{self.identity}"


class ModelService:
    """模型服务。
    
    负责模型发现、缓存、标签合并。
    """
    
    def __init__(self, http_client: Optional[HTTPClient] = None):
        """初始化模型服务。

        Args:
            http_client: HTTP 客户端实例
        """
        self._config_store = get_config_store()
        self._http_client = http_client

        # Cache configuration with bounded size (LRU eviction)
        self._max_cache_entries = int(os.getenv("FAIC_MODEL_CACHE_MAX_ENTRIES", "200"))
        self._cache: OrderedDict[str, Tuple[List[ModelInfo], datetime]] = OrderedDict()
        self._cache_ttl = timedelta(hours=1)  # 默认缓存 1 小时
        logger.debug(
            "ModelService cache initialized: max_entries=%d ttl=%s",
            self._max_cache_entries,
            self._cache_ttl,
        )
    
    async def list_models(
        self,
        provider_key: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        use_cache: bool = True,
    ) -> List[ModelInfo]:
        """获取提供商的模型列表。
        
        Args:
            provider_key: 提供商键
            api_key: API Key（用于动态发现）
            base_url: 自定义 Base URL
            use_cache: 是否使用缓存
            
        Returns:
            List[ModelInfo]: 模型信息列表
        """
        provider_config = self._config_store.get_provider(provider_key)
        if not provider_config:
            logger.warning(f"Provider {provider_key} not found")
            return []
        
        # 生成缓存键
        cache_key = self._get_cache_key(provider_key, api_key, base_url)
        
        # 尝试从缓存获取
        if use_cache and cache_key in self._cache:
            models, expiry = self._cache[cache_key]
            if datetime.now() < expiry:
                logger.debug(f"Cache hit for {cache_key}")
                return models
            else:
                del self._cache[cache_key]
        
        # 动态发现模型
        if provider_config.discovery.enabled and api_key:
            logger.info(
                f"Discovery enabled for {provider_key}, strategy={provider_config.discovery.strategy}, "
                f"calling _discover_models..."
            )
            models = await self._discover_models(
                provider_key, provider_config, api_key, base_url
            )
            logger.info(f"_discover_models returned {len(models)} models for {provider_key}")
        else:
            # 返回空列表（由调用方决定是否使用默认模型）
            logger.debug(
                f"Discovery disabled for {provider_key}, "
                f"enabled={provider_config.discovery.enabled}, "
                f"has_api_key={api_key is not None}"
            )
            models = []
        
        # 合并标签
        models = self._merge_tags(models, provider_key)
        
        # 添加定价信息
        models = self._add_pricing(models, provider_key)

        # 缓存结果 with LRU eviction
        if use_cache and models:
            self._set_cache(cache_key, models)

        return models

    def _set_cache(self, key: str, models: List[ModelInfo]) -> None:
        """Set cache entry with LRU eviction.

        Implements bounded cache:
        - If cache is full, evict the oldest entry (FIFO/LRU)
        - Move accessed key to end (mark as recently used)
        """
        # If key exists, move it to end (mark as recently used)
        if key in self._cache:
            self._cache.move_to_end(key)

        # If cache is full, evict oldest entry
        if len(self._cache) >= self._max_cache_entries:
            evicted_key, _ = self._cache.popitem(last=False)  # Remove oldest (FIFO)
            logger.debug(
                "ModelService cache full (%d entries), evicted: %s",
                self._max_cache_entries,
                evicted_key,
            )

        # Add new entry
        self._cache[key] = (models, datetime.now() + self._cache_ttl)

    async def _discover_models(
        self,
        provider_key: str,
        provider_config: ProviderConfig,
        api_key: str,
        base_url: Optional[str] = None,
    ) -> List[ModelInfo]:
        """动态发现模型。
        
        Args:
            provider_key: 提供商键
            provider_config: 提供商配置
            api_key: API Key
            base_url: 自定义 Base URL
            
        Returns:
            List[ModelInfo]: 模型信息列表
        """
        strategy = provider_config.discovery.strategy
        
        if strategy == DiscoveryStrategy.OPENAI_MODELS:
            return await self._discover_openai_models(
                provider_key, provider_config, api_key, base_url
            )
        elif strategy == DiscoveryStrategy.GEMINI_MODELS:
            return await self._discover_gemini_models(
                provider_key, provider_config, api_key
            )
        elif strategy == DiscoveryStrategy.ANTHROPIC_MODELS:
            return await self._discover_anthropic_models(
                provider_key, provider_config, api_key
            )
        elif strategy == DiscoveryStrategy.OLLAMA_MODELS:
            return await self._discover_ollama_models(
                provider_key, provider_config, base_url
            )
        elif strategy == DiscoveryStrategy.HUGGINGFACE_MODELS:
            return await self._discover_huggingface_models(
                provider_key, provider_config, api_key
            )
        else:
            logger.warning(f"Unknown discovery strategy: {strategy}")
            return []
    
    async def _discover_openai_models(
        self,
        provider_key: str,
        provider_config: ProviderConfig,
        api_key: str,
        base_url: Optional[str] = None,
    ) -> List[ModelInfo]:
        """发现 OpenAI 兼容 API 的模型。"""
        client = self._get_http_client()

        endpoint = base_url or provider_config.endpoints.api_base
        models_path = provider_config.endpoints.models_path
        url = f"{endpoint.rstrip('/')}{models_path}"

        headers = {"Authorization": f"Bearer {api_key}"}

        logger.info(f"Fetching models from {url} for {provider_key}")

        try:
            response = await client.get(url, headers=headers)
            logger.info(f"Response from {provider_key}: status={response.status_code}")
            if response.status_code == 200:
                models = self._parse_openai_models_response(
                    response.data, provider_key
                )
                logger.info(f"Parsed {len(models)} models from {provider_key} response")
                return models
            else:
                logger.warning(
                    f"Failed to fetch models from {provider_key}: "
                    f"HTTP {response.status_code}, body={str(response.data)[:200]}"
                )
        except Exception as e:
            logger.error(f"Error discovering models from {provider_key}: {e}")

        return []
    
    async def _discover_gemini_models(
        self,
        provider_key: str,
        provider_config: ProviderConfig,
        api_key: str,
    ) -> List[ModelInfo]:
        """发现 Google Gemini 模型。"""
        client = self._get_http_client()
        
        endpoint = provider_config.endpoints.api_base
        url = f"{endpoint.rstrip('/')}/models?key={api_key}"
        
        try:
            response = await client.get(url)
            if response.status_code == 200:
                return self._parse_gemini_models_response(
                    response.data, provider_key
                )
        except Exception as e:
            logger.error(f"Error discovering Gemini models: {e}")
        
        return []
    
    async def _discover_anthropic_models(
        self,
        provider_key: str,
        provider_config: ProviderConfig,
        api_key: str,
    ) -> List[ModelInfo]:
        """发现 Anthropic 模型。"""
        client = self._get_http_client()
        
        endpoint = provider_config.endpoints.api_base
        url = f"{endpoint.rstrip('/')}/models"
        
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
        
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return self._parse_anthropic_models_response(
                    response.data, provider_key
                )
        except Exception as e:
            logger.error(f"Error discovering Anthropic models: {e}")
        
        return []
    
    async def _discover_ollama_models(
        self,
        provider_key: str,
        provider_config: ProviderConfig,
        base_url: Optional[str] = None,
    ) -> List[ModelInfo]:
        """发现 Ollama 本地模型。"""
        client = self._get_http_client()
        
        endpoint = base_url or provider_config.endpoints.api_base
        url = f"{endpoint.rstrip('/')}/api/tags"
        
        try:
            response = await client.get(url)
            if response.status_code == 200:
                return self._parse_ollama_models_response(
                    response.data, provider_key
                )
        except Exception as e:
            logger.error(f"Error discovering Ollama models: {e}")
        
        return []
    
    async def _discover_huggingface_models(
        self,
        provider_key: str,
        provider_config: ProviderConfig,
        api_key: str,
    ) -> List[ModelInfo]:
        """发现 Hugging Face 模型。"""
        client = self._get_http_client()
        
        endpoint = provider_config.endpoints.api_base
        url = f"{endpoint.rstrip('/')}/models"
        
        headers = {"Authorization": f"Bearer {api_key}"}
        
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return self._parse_huggingface_models_response(
                    response.data, provider_key
                )
        except Exception as e:
            logger.error(f"Error discovering HuggingFace models: {e}")
        
        return []
    
    def _parse_openai_models_response(
        self, 
        data: Dict[str, Any], 
        provider_key: str
    ) -> List[ModelInfo]:
        """解析 OpenAI 风格的模型列表响应。"""
        models = []
        for model in data.get("data", []):
            model_id = model.get("id", "")
            if model_id:
                models.append(ModelInfo(
                    model_key=model_id,
                    display_name=model.get("name", model_id),
                    context_length=model.get("context_length"),
                    supports_tools=model.get("supports_tools", False),
                    provider_key=provider_key,
                    raw_data=model,
                ))
        return models
    
    def _parse_gemini_models_response(
        self, 
        data: Dict[str, Any], 
        provider_key: str
    ) -> List[ModelInfo]:
        """解析 Google Gemini 模型列表响应。"""
        models = []
        for model in data.get("models", []):
            model_name = model.get("name", "")
            if model_name and model_name.startswith("models/"):
                model_id = model_name.replace("models/", "")
                models.append(ModelInfo(
                    model_key=model_id,
                    display_name=model.get("displayName", model_id),
                    context_length=model.get("inputTokenLimit", 32768),
                    supports_tools="generateContent" in model.get(
                        "supportedGenerationMethods", []
                    ),
                    provider_key=provider_key,
                    raw_data=model,
                ))
        return models
    
    def _parse_anthropic_models_response(
        self, 
        data: Dict[str, Any], 
        provider_key: str
    ) -> List[ModelInfo]:
        """解析 Anthropic 模型列表响应。"""
        models = []
        for model in data.get("data", []):
            model_id = model.get("id", "")
            if model_id:
                models.append(ModelInfo(
                    model_key=model_id,
                    display_name=model.get("name", model_id),
                    context_length=model.get("context_length"),
                    provider_key=provider_key,
                    raw_data=model,
                ))
        return models
    
    def _parse_ollama_models_response(
        self, 
        data: Dict[str, Any], 
        provider_key: str
    ) -> List[ModelInfo]:
        """解析 Ollama 模型列表响应。"""
        models = []
        for model in data.get("models", []):
            model_name = model.get("name", "")
            if model_name:
                # 解析模型名和标签
                name_parts = model_name.split(":")
                base_name = name_parts[0] if name_parts else model_name
                tag = name_parts[1] if len(name_parts) > 1 else "latest"
                
                models.append(ModelInfo(
                    model_key=model_name,
                    display_name=f"{base_name}:{tag}",
                    context_length=None,
                    supports_tools=False,
                    provider_key=provider_key,
                    raw_data=model,
                ))
        return models
    
    def _parse_huggingface_models_response(
        self, 
        data: List[Dict[str, Any]], 
        provider_key: str
    ) -> List[ModelInfo]:
        """解析 HuggingFace 模型列表响应。"""
        models = []
        for model in data:
            model_id = model.get("id", "")
            if model_id:
                models.append(ModelInfo(
                    model_key=model_id,
                    display_name=model.get("model_id", model_id),
                    context_length=None,
                    supports_tools=False,
                    provider_key=provider_key,
                    raw_data=model,
                ))
        return models
    
    def _merge_tags(
        self,
        models: List[ModelInfo],
        provider_key: str
    ) -> List[ModelInfo]:
        """合并 model_tags.yaml 中的标签。"""
        # Check if config_store has get_model_tag method
        if not hasattr(self._config_store, 'get_model_tag'):
            logger.debug("ConfigStore does not have get_model_tag method, skipping tag merge")
            return models

        for model in models:
            tag = self._config_store.get_model_tag(model.model_key)
            if tag:
                model.performance_level = tag.performance_level.value if tag.performance_level else None
                model.is_thinking = tag.is_thinking
        return models
    
    def _add_pricing(
        self,
        models: List[ModelInfo],
        provider_key: str
    ) -> List[ModelInfo]:
        """添加定价信息。"""
        # Check if config_store has get_price method
        if not hasattr(self._config_store, 'get_price'):
            logger.debug("ConfigStore does not have get_price method, skipping pricing")
            return models

        for model in models:
            pricing = self._config_store.get_price(provider_key, model.model_key)
            if pricing:
                model.pricing = pricing
        return models
    
    def _get_cache_key(
        self,
        provider_key: str,
        api_key: Optional[str],
        base_url: Optional[str],
    ) -> str:
        """生成缓存键。"""
        # 使用 api_key 的 hash 作为身份标识
        identity_parts = []
        if api_key:
            key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
            identity_parts.append(f"key:{key_hash}")
        if base_url:
            identity_parts.append(f"url:{base_url}")
        
        identity = ":".join(identity_parts) if identity_parts else "default"
        return f"{provider_key}:{identity}"
    
    def _get_http_client(self) -> HTTPClient:
        """获取 HTTP 客户端。"""
        if self._http_client is None:
            self._http_client = get_http_client()
        return self._http_client
    
    def clear_cache(self, provider_key: Optional[str] = None) -> int:
        """清除缓存。
        
        Args:
            provider_key: 指定提供商键（可选，清除所有）
            
        Returns:
            int: 清除的缓存数量
        """
        if provider_key:
            keys_to_remove = [
                k for k in self._cache.keys() 
                if k.startswith(provider_key + ":")
            ]
            for k in keys_to_remove:
                del self._cache[k]
            return len(keys_to_remove)
        else:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息。"""
        return {
            "cached_entries": len(self._cache),
            "ttl_hours": self._cache_ttl.total_seconds() / 3600,
        }


# 全局服务实例
_model_service: Optional[ModelService] = None


def get_model_service() -> ModelService:
    """获取全局模型服务实例。"""
    global _model_service
    if _model_service is None:
        _model_service = ModelService()
    return _model_service


def reset_model_service() -> None:
    """重置模型服务（主要用于测试）。"""
    global _model_service
    _model_service = None
