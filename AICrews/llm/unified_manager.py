"""统一LLM管理器 (Facade)

职责：
- 对外提供统一 API
- 委托给各服务模块处理具体逻辑
- 保持对现有业务（crew_assembler、后端配置管理、DB 同步）的兼容

注意：核心逻辑已迁移到以下模块：
- `AICrews/llm/core/` - 配置加载、HTTP 客户端、异常处理
- `AICrews/llm/services/` - Provider/Model/Validation/DBSync 服务
- `AICrews/llm/factories/` - LLM 工厂
"""

from AICrews.observability.logging import get_logger
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from AICrews.database.models import (
    UserLLMConfig,
    UserModelConfig,
)
from AICrews.llm.core.config_store import get_config_store

# 服务模块
from AICrews.llm.services.provider_service import (
    ProviderService,
    get_provider_service,
)
from AICrews.llm.services.model_service import ModelService, get_model_service
from AICrews.llm.services.validation_service import (
    ValidationService,
    get_validation_service,
)
from AICrews.llm.services.db_sync_service import DBSyncService, get_db_sync_service

# 工厂模块
from AICrews.llm.factories.llm_factory import LLMFactory, get_llm_factory

logger = get_logger(__name__)


class UnifiedLLMManager:
    """统一LLM管理器 (Facade)
    
    对外 API 入口，委托给各服务模块处理具体逻辑。
    """
    
    def __init__(self):
        """初始化管理器。"""
        # 服务实例
        self._config_store = get_config_store()
        self._provider_service = get_provider_service()
        self._model_service = get_model_service()
        self._validation_service = get_validation_service()
        self._db_sync_service = get_db_sync_service()
        self._llm_factory = get_llm_factory()
        
        logger.info("UnifiedLLMManager initialized (Facade pattern)")
    
    # =====================================================================
    # Provider APIs (委托给 ProviderService)
    # =====================================================================
    
    def get_all_providers(self) -> List[Dict[str, Any]]:
        """获取所有提供商信息（给前端用）。"""
        providers = self._provider_service.list_providers()
        return [p.__dict__ for p in providers]
    
    def get_provider(self, provider_key: str) -> Optional[Dict[str, Any]]:
        """获取指定提供商信息。"""
        provider = self._provider_service.get_provider(provider_key)
        if provider:
            return provider.__dict__
        return None
    
    def get_provider_type(self, provider_key: str) -> str:
        """获取提供商类型。"""
        provider = self._config_store.get_provider(provider_key)
        if provider:
            return provider.provider_type.value
        return "unknown"
    
    def get_model_prefix(self, provider_key: str) -> str:
        """获取提供商的模型前缀。"""
        return self._provider_service.get_model_prefix(provider_key)
    
    def list_china_providers(self) -> List[Dict[str, Any]]:
        """获取中国提供商列表。"""
        providers = self._provider_service.list_china_providers()
        return [p.__dict__ for p in providers]
    
    def list_international_providers(self) -> List[Dict[str, Any]]:
        """获取国际提供商列表。"""
        providers = self._provider_service.list_international_providers()
        return [p.__dict__ for p in providers]
    
    # =====================================================================
    # Model APIs (委托给 ModelService)
    # =====================================================================
    
    async def get_provider_models_async(
        self, 
        provider_key: str, 
        api_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取提供商的模型列表（异步版本，推荐在 async 路由中使用）。"""
        models = await self._model_service.list_models(
            provider_key, api_key=api_key, use_cache=True
        )
        return [m.to_dict() for m in models]
    
    def get_provider_models(
        self, 
        provider_key: str, 
        api_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取提供商的模型列表（同步版本）。"""
        # 由于 ModelService 是异步的，这里使用 run_in_executor
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        models = loop.run_until_complete(
            self._model_service.list_models(
                provider_key, api_key=api_key, use_cache=True
            )
        )
        return [m.to_dict() for m in models]
    
    def clear_model_cache(self, provider_key: Optional[str] = None) -> int:
        """清除模型缓存。"""
        return self._model_service.clear_cache(provider_key)
    
    def get_model_cache_stats(self) -> Dict[str, Any]:
        """获取模型缓存统计。"""
        return self._model_service.get_cache_stats()
    
    # =====================================================================
    # Validation APIs (委托给 ValidationService)
    # =====================================================================
    
    async def validate_provider_config(
        self,
        provider_key: str,
        api_key: str,
        base_url: Optional[str] = None,
        custom_model: Optional[str] = None,
        volcengine_endpoints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """验证提供商配置。"""
        result = await self._validation_service.validate_provider_config(
            provider_key, api_key, base_url, custom_model, volcengine_endpoints
        )
        return {
            "valid": result.valid,
            "message": result.message,
            "error_code": result.error_code,
            "error_details": result.error_details,
        }
    
    # =====================================================================
    # LLM Factory APIs (委托给 LLMFactory)
    # =====================================================================

    def create_default_llm(
        self,
        provider_key: Optional[str] = None,
        model_key: Optional[str] = None,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Any:
        """创建默认 LLM 实例（用于无用户配置的服务级兜底）。

        Notes:
        - 优先使用显式传入的 provider/model（推荐：由业务配置驱动）。
        - 未提供时，回退到 Settings + 环境变量（用于兼容旧调用方）。
        - 不做网络请求，仅构造 crewai.LLM 实例。
        """
        resolved_provider = provider_key
        resolved_model = model_key

        if not resolved_provider or not resolved_model:
            try:
                from AICrews.config.settings import get_settings

                settings = get_settings()
            except Exception:
                settings = None

            if not resolved_provider:
                resolved_provider = (
                    os.getenv("FAIC_LLM_PROVIDER")
                    or os.getenv("LLM_PROVIDER")
                    or getattr(getattr(settings, "llm", None), "provider", None)
                )

            if not resolved_model:
                resolved_model = (
                    os.getenv("FAIC_LLM_DEFAULT_MODEL")
                    or os.getenv("DEFAULT_LLM")
                    or getattr(getattr(settings, "llm", None), "default_model", None)
                )
                if resolved_provider == "volcengine":
                    resolved_model = resolved_model or os.getenv(
                        "VOLCENGINE_ENDPOINT_ID"
                    ) or os.getenv("VOLCENGINE_MODEL")

        if not resolved_provider or not resolved_model:
            raise ValueError(
                "Default LLM provider/model is not configured. "
                "Provide provider_key/model_key explicitly or configure env/Settings."
            )

        provider_config = self._config_store.get_provider(resolved_provider)
        if not provider_config:
            raise ValueError(f"Unknown provider: {resolved_provider}")

        if api_key is None and provider_config.auth.api_key_env:
            api_key = os.getenv(provider_config.auth.api_key_env)
            if not api_key:
                logger.warning(
                    "Default LLM API key env var is not set: %s (provider=%s)",
                    provider_config.auth.api_key_env,
                    resolved_provider,
                )

        if base_url is None:
            base_url = provider_config.endpoints.api_base or None

        return self._llm_factory.create_from_agent_yaml(
            provider_key=resolved_provider,
            model_key=resolved_model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
    
    def create_from_user_model_config(
        self,
        user_model_config: UserModelConfig,
        **kwargs,
    ) -> Any:
        """从数据库 UserModelConfig 创建 LLM 实例。"""
        return self._llm_factory.create_from_user_model_config(
            user_model_config, **kwargs
        )
    
    def create_llm(
        self,
        provider: str,
        model_name: str,
        **kwargs,
    ) -> Any:
        """创建 CrewAI LLM 实例（CLI兼容，兼容 crew_assembler.py）。"""
        return self._llm_factory.create_from_agent_yaml(
            provider_key=provider,
            model_key=model_name,
            **kwargs,
        )
    
    def create_crewai_llm(
        self,
        user_model_config: UserModelConfig,
        **kwargs,
    ) -> Any:
        """为CrewAI创建LLM实例（别名，兼容旧代码）。"""
        return self.create_from_user_model_config(user_model_config, **kwargs)
    
    def get_llm_params(
        self,
        provider_key: str,
        model_key: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """构建 LLM 参数（不创建实例）。"""
        return self._llm_factory.create_llm_params(
            provider_key=provider_key,
            model_key=model_key,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
    
    # =====================================================================
    # DB Sync APIs (委托给 DBSyncService)
    # =====================================================================
    
    async def sync_all_models(self, db: Session) -> Dict[str, Any]:
        """同步所有提供商的模型到数据库。"""
        results = await self._db_sync_service.sync_all_providers(db)
        return {
            r.provider_key: {
                "status": r.status,
                "count": r.models_count,
                "message": r.message,
                "error": r.error,
            }
            for r in results
        }
    
    async def sync_provider_models(
        self,
        db: Session,
        provider_key: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """同步指定提供商的模型。"""
        if api_key:
            result = await self._db_sync_service.sync_models_with_api_key(
                db, provider_key, api_key, base_url
            )
        else:
            result = await self._db_sync_service.sync_provider(db, provider_key)
        
        return {
            "provider_key": result.provider_key,
            "status": result.status,
            "count": result.models_count,
            "message": result.message,
            "error": result.error,
        }
    
    def sync_pricing_from_config(self, db: Session) -> Dict[str, int]:
        """从配置文件同步定价信息。"""
        return self._db_sync_service.sync_pricing_from_config(db)
    
    # =====================================================================
    # Config APIs (委托给 ConfigStore)
    # =====================================================================
    
    def get_config_status(self) -> Dict[str, Any]:
        """获取配置状态。"""
        status = self._config_store.status()
        return {
            "providers_path": status.providers_path,
            "providers_loaded": status.providers_loaded,
            "providers_count": status.providers_count,
            "pricing_path": status.pricing_path,
            "pricing_loaded": status.pricing_loaded,
            "model_tags_path": status.model_tags_path,
            "model_tags_loaded": status.model_tags_loaded,
            "last_reload_time": (
                status.last_reload_time.isoformat() 
                if status.last_reload_time else None
            ),
            "reload_count": status.reload_count,
        }
    
    def reload_config(self) -> Dict[str, Any]:
        """重新加载配置。"""
        status = self._config_store.reload()
        # 同时清除缓存
        self._model_service.clear_cache()
        return {
            "status": "reloaded",
            "providers_count": status.providers_count,
            "reload_time": (
                status.last_reload_time.isoformat() 
                if status.last_reload_time else None
            ),
        }
    
    def check_config_updates(self) -> bool:
        """检查配置是否有更新。"""
        return self._config_store.check_for_updates()
    
    # =====================================================================
    # Legacy/Compatibility APIs (保留但标记 deprecated)
    # =====================================================================
    
    def get_providers(self) -> List[Dict[str, str]]:
        """获取用于CLI展示的提供商列表（已废弃，仅用于兼容性）。"""
        all_providers = self.get_all_providers()
        return [
            {"name": p["display_name"], "value": p["provider_key"]}
            for p in all_providers
            if p.get("has_env_config")
        ]
    
    def get_models_for_provider(
        self, 
        provider_key: str, 
        api_key: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """获取指定提供商的模型列表（CLI格式，已废弃）。"""
        models = self.get_provider_models(provider_key, api_key)
        return [{"name": m["display_name"], "value": m["model_key"]} for m in models]
    
    def list_configs(self, db: Session, user_id: int) -> List[UserLLMConfig]:
        """获取用户的LLM配置列表。"""
        return db.query(UserLLMConfig).filter(
            UserLLMConfig.user_id == user_id
        ).all()
    
    def get_config(self, db: Session, config_id: int) -> Optional[UserLLMConfig]:
        """获取指定ID的LLM配置。"""
        return db.query(UserLLMConfig).filter(
            UserLLMConfig.id == config_id
        ).first()
    
    def get_model_config(
        self, 
        db: Session, 
        model_config_id: int
    ) -> Optional[UserModelConfig]:
        """获取指定ID的用户模型配置。"""
        return db.query(UserModelConfig).filter(
            UserModelConfig.id == model_config_id
        ).first()
    
    def create_llm_instance(
        self, 
        config: UserLLMConfig
    ) -> Optional[Any]:
        """为指定的UserLLMConfig创建一个默认的LLM实例。"""
        # 查找该配置下第一个激活的模型
        active_model_config = next(
            (mc for mc in config.model_configs if mc.is_active), 
            None
        )
        
        # 如果没有激活的模型，尝试使用第一个可用的模型
        if not active_model_config:
            active_model_config = next(
                (mc for mc in config.model_configs if mc.is_available), 
                None
            )
        
        if not active_model_config:
            logger.error(f"No active or available models found for config {config.id}")
            return None
        
        return self.create_crewai_llm(active_model_config)


# 全局管理器实例
_unified_manager: Optional[UnifiedLLMManager] = None


def get_unified_llm_manager() -> UnifiedLLMManager:
    """获取全局统一LLM管理器实例。"""
    global _unified_manager
    if _unified_manager is None:
        _unified_manager = UnifiedLLMManager()
    return _unified_manager


def sync_models_to_db(
    db: Session,
    db_provider: Any,
    models: List[Dict[str, Any]]
) -> int:
    """同步模型到数据库（兼容性函数）。

    Args:
        db: 数据库 Session
        db_provider: 数据库提供商记录
        models: 模型信息列表（字典格式）

    Returns:
        int: 同步的模型数量
    """
    from AICrews.llm.services.model_service import ModelInfo
    
    # 将字典转换为 ModelInfo 对象
    model_infos = []
    for model_dict in models:
        model_info = ModelInfo(
            model_key=model_dict.get("model_key", ""),
            display_name=model_dict.get("display_name", ""),
            context_length=model_dict.get("context_length"),
            supports_tools=model_dict.get("supports_tools", False),
            performance_level=model_dict.get("performance_level"),
            is_thinking=model_dict.get("is_thinking", False),
            pricing=model_dict.get("pricing"),
        )
        model_infos.append(model_info)
    
    manager = get_unified_llm_manager()
    return manager._db_sync_service._upsert_models(db, db_provider, model_infos)


def reset_unified_llm_manager() -> None:
    """重置管理器实例（主要用于测试）。"""
    global _unified_manager
    _unified_manager = None
