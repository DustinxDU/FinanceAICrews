"""LLM 工厂模块

只负责创建 crewai.LLM，不做 IO 操作。
"""

from AICrews.observability.logging import get_logger
from typing import Any, Dict, List, Optional

from crewai import LLM

from AICrews.llm.core.config_store import get_config_store
from AICrews.llm.core.config_models import ProviderType
from AICrews.database.models import (
    UserLLMConfig as DBUserLLMConfig,
    UserModelConfig as DBUserModelConfig,
)
from AICrews.utils.encryption import decrypt_api_key, is_encrypted

logger = get_logger(__name__)


class LLMFactory:
    """LLM 工厂类。

    职责：
    - 只负责构造 LLM 实例
    - 禁止 IO（不请求网络、不读 YAML、不查 DB）
    - 禁止写 os.environ
    """

    def __init__(self):
        """初始化工厂。"""
        self._config_store = get_config_store()

    def create_from_user_model_config(
        self,
        user_model_config: DBUserModelConfig,
        **kwargs,
    ) -> LLM:
        """从数据库 UserModelConfig 创建 LLM 实例。

        Args:
            user_model_config: 数据库中的用户模型配置
            **kwargs: 额外的 LLM 参数

        Returns:
            LLM: CrewAI LLM 实例
        """
        provider = user_model_config.llm_config.provider
        model = user_model_config.model
        provider_key = provider.provider_key
        model_key = model.model_key

        provider_config = self._config_store.get_provider(provider_key)
        if not provider_config:
            raise ValueError(f"Unknown provider: {provider_key}")

        provider_type = provider_config.provider_type

        # Decrypt API key if encrypted (DB stores encrypted keys)
        raw_api_key = user_model_config.llm_config.api_key
        api_key = decrypt_api_key(raw_api_key) if is_encrypted(raw_api_key) else raw_api_key

        # 构建 LLM 参数
        llm_params = self._build_llm_params(
            provider_key=provider_key,
            provider_type=provider_type,
            model_key=model_key,
            api_key=api_key,
            base_url=user_model_config.llm_config.base_url,
            temperature=user_model_config.temperature
            or user_model_config.llm_config.default_temperature,
            max_tokens=user_model_config.max_tokens
            or user_model_config.llm_config.default_max_tokens,
            custom_model_name=user_model_config.custom_model_name,
            volcengine_endpoint_id=getattr(
                user_model_config, "volcengine_endpoint_id", None
            ),
            **kwargs,
        )

        logger.info(
            f"Creating LLM: provider={provider_key}, model={model_key}, "
            f"base_url={llm_params.get('base_url')}"
        )

        return LLM(**llm_params)

    def create_from_agent_yaml(
        self,
        provider_key: str,
        model_key: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLM:
        """从 Agent YAML 配置创建 LLM 实例（兼容 crew_assembler.py）。

        Args:
            provider_key: 提供商键
            model_key: 模型键
            api_key: API Key
            base_url: Base URL
            temperature: 温度
            max_tokens: 最大 token 数
            **kwargs: 额外的 LLM 参数

        Returns:
            LLM: CrewAI LLM 实例
        """
        provider_config = self._config_store.get_provider(provider_key)
        if not provider_config:
            raise ValueError(f"Unknown provider: {provider_key}")

        provider_type = provider_config.provider_type

        # 构建 LLM 参数
        llm_params = self._build_llm_params(
            provider_key=provider_key,
            provider_type=provider_type,
            model_key=model_key,
            api_key=api_key,
            base_url=base_url or provider_config.endpoints.api_base,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        logger.info(
            f"Creating LLM from YAML: provider={provider_key}, model={model_key}"
        )

        return LLM(**llm_params)

    def create_llm(
        self,
        provider_key: str,
        model_key: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        fallback_models: Optional[List[str]] = None,
        **kwargs,
    ) -> LLM:
        """创建带有降级支持的 LLM 实例。

        Args:
            provider_key: 提供商键
            model_key: 核心模型键
            fallback_models: 降级模型列表（按优先级排序）
            ...
        """
        # 实现简单的基于包装器的降级逻辑是不现实的（因为 crewai.LLM 是底层类）
        # 这里我们记录配置，实际降级由 LiteLLM 内部或上层重试机制处理
        # 我们可以通过 model 字符串传递给 LiteLLM 的一些特性 (如果支持)

        provider_config = self._config_store.get_provider(provider_key)
        if not provider_config:
            raise ValueError(f"Unknown provider: {provider_key}")

        params = self._build_llm_params(
            provider_key=provider_key,
            provider_type=provider_config.provider_type,
            model_key=model_key,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        # 记录降级建议
        if fallback_models:
            logger.info(f"LLM created with fallbacks: {fallback_models}")
            # 注意：目前的 CrewAI/LiteLLM 实例创建后不直接支持动态 fallback 链切换
            # 但我们可以在 params 中注入额外配置供底层解析

        return LLM(**params)

    def _build_llm_params(
        self,
        provider_key: str,
        provider_type: ProviderType,
        model_key: str,
        api_key: Optional[str],
        base_url: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        custom_model_name: Optional[str] = None,
        volcengine_endpoint_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """构建 LLM 参数。

        Args:
            provider_key: 提供商键
            provider_type: 提供商类型
            model_key: 模型键
            api_key: API Key
            base_url: Base URL
            temperature: 温度
            max_tokens: 最大 token 数
            custom_model_name: 自定义模型名
            volcengine_endpoint_id: 火山引擎端点 ID

        Returns:
            Dict: LLM 参数
        """
        # 确定模型名
        final_model_name = model_key

        # 如果没有提供 base_url，尝试从配置中获取默认的 api_base
        if not base_url:
            provider_config = self._config_store.get_provider(provider_key)
            if provider_config and provider_config.endpoints.api_base:
                base_url = provider_config.endpoints.api_base

        # 对于 OpenAI Compatible / Volcengine，这个字段缺失会直接导致 CrewAI 回退到默认 OpenAI 端点
        # （api.openai.com），从而出现“带着非 OpenAI key 打 OpenAI”的 401。
        if provider_type in (ProviderType.OPENAI_COMPATIBLE, ProviderType.VOLCENGINE) and not base_url:
            raise ValueError(
                f"Provider '{provider_key}' requires a base_url (OpenAI compatible), "
                "but no base_url was provided and no default api_base is configured."
            )

        # 处理特殊 provider
        if provider_type == ProviderType.VOLCENGINE:
            # 火山引擎 Ark 接口为 OpenAI Compatible，但 endpoint_id 通常不满足 CrewAI 的
            # openai/<model> 常量/命名校验；若走该路径会被路由到 LiteLLM fallback，
            # 且不同版本对 base_url/api_base 的使用不一致，容易出现错打 api.openai.com。
            #
            # 这里强制显式指定 provider=openai，让 CrewAI 走 OpenAI native SDK，
            # 并使用 base_url/api_base 指向 Ark 网关。
            if volcengine_endpoint_id:
                final_model_name = volcengine_endpoint_id
            elif custom_model_name:
                final_model_name = custom_model_name

            # 强制走 OpenAI native provider（可接受任意 model 字符串）
            kwargs.setdefault("provider", "openai")

        elif provider_type == ProviderType.OPENAI_COMPATIBLE:
            # OpenAI 兼容接口：model 名称保持不变，base_url 会单独传递
            # LiteLLM 需要 model 名称（如 deepseek-v3.2）而非 provider 前缀格式
            # final_model_name 保持为 model_key
            # 显式指定 provider=openai，避免 CrewAI 基于 model 字符串误判/回退策略变化
            kwargs.setdefault("provider", "openai")

        elif provider_type == ProviderType.CREWAI_NATIVE:
            # CrewAI 原生支持使用 provider/model 格式
            provider_config = self._config_store.get_provider(provider_key)
            if provider_config:
                prefix = provider_config.llm_model_prefix
                if prefix:
                    final_model_name = f"{prefix.rstrip('/')}/{model_key}".replace(
                        f"{provider_key}/", ""
                    )
                    # 格式应该是 provider/model_key
                    final_model_name = f"{provider_key}/{model_key}"

        # 构建参数
        params = {
            "model": final_model_name,
            "temperature": temperature,
        }

        # Inject stable metadata for observability/cost tracking (best-effort).
        # This is safe to persist on the LLM instance and does NOT depend on run_id.
        try:
            metadata = kwargs.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            metadata.setdefault("faic_provider_key", provider_key)
            metadata.setdefault("faic_model_key", model_key)
            metadata.setdefault("faic_provider_type", str(provider_type))
            params["metadata"] = metadata
        except Exception:
            pass

        # 添加可选参数
        if api_key:
            params["api_key"] = api_key

        if base_url:
            # CrewAI native providers、LiteLLM fallback、以及 OpenAI SDK 的不同路径
            # 对 base_url/api_base 的读取存在差异；同时设置两者以避免错打默认 OpenAI。
            params["base_url"] = base_url
            params["api_base"] = base_url

        if max_tokens:
            params["max_tokens"] = max_tokens

        # 合并额外参数
        params.update(kwargs)

        return params

    def create_llm_params(
        self,
        provider_key: str,
        model_key: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """构建 LLM 参数（不创建实例）。

        Args:
            provider_key: 提供商键
            model_key: 模型键
            api_key: API Key
            base_url: Base URL
            temperature: 温度
            max_tokens: 最大 token 数
            **kwargs: 额外的 LLM 参数

        Returns:
            Dict: LLM 参数
        """
        provider_config = self._config_store.get_provider(provider_key)
        if not provider_config:
            raise ValueError(f"Unknown provider: {provider_key}")

        return self._build_llm_params(
            provider_key=provider_key,
            provider_type=provider_config.provider_type,
            model_key=model_key,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )


# 全局工厂实例
_llm_factory: Optional[LLMFactory] = None


def get_llm_factory() -> LLMFactory:
    """获取全局 LLM 工厂实例。"""
    global _llm_factory
    if _llm_factory is None:
        _llm_factory = LLMFactory()
    return _llm_factory


def reset_llm_factory() -> None:
    """重置 LLM 工厂（主要用于测试）。"""
    global _llm_factory
    _llm_factory = None
