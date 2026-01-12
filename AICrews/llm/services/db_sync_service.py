"""DB Sync 服务模块

同步 providers/models 到数据库的服务。
"""

from AICrews.observability.logging import get_logger
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from AICrews.llm.core.config_store import get_config_store
from AICrews.llm.core.config_models import ProviderConfig
from AICrews.database.models import (
    LLMProvider as DBProvider,
    LLMModel as DBModel,
    UserLLMConfig,
    UserModelConfig,
)
from AICrews.llm.services.model_service import ModelInfo, get_model_service

logger = get_logger(__name__)


@dataclass
class SyncResult:
    """同步结果。"""
    provider_key: str
    status: str  # "success", "skipped", "error"
    models_count: int = 0
    message: str = ""
    error: Optional[str] = None


class DBSyncService:
    """数据库同步服务。
    
    负责同步 providers/models 到数据库。
    """
    
    def __init__(self):
        """初始化同步服务。"""
        self._config_store = get_config_store()
        self._model_service = get_model_service()
    
    async def sync_all_providers(
        self, 
        db: AsyncSession,
        sync_models: bool = True,
    ) -> List[SyncResult]:
        """同步所有提供商到数据库。
        
        Args:
            db: 数据库 Session
            sync_models: 是否同步模型
            
        Returns:
            List[SyncResult]: 同步结果列表
        """
        results = []
        
        for provider_key in self._config_store.list_provider_keys():
            try:
                result = await self.sync_provider(db, provider_key, sync_models)
                results.append(result)
            except Exception as e:
                logger.error(f"Error syncing provider {provider_key}: {e}")
                results.append(SyncResult(
                    provider_key=provider_key,
                    status="error",
                    message=str(e),
                    error=str(e),
                ))
        
        return results
    
    async def sync_provider(
        self,
        db: AsyncSession,
        provider_key: str,
        sync_models: bool = True,
    ) -> SyncResult:
        """同步单个提供商到数据库。
        
        Args:
            db: 数据库 Session
            provider_key: 提供商键
            sync_models: 是否同步模型
            
        Returns:
            SyncResult: 同步结果
        """
        provider_config = self._config_store.get_provider(provider_key)
        if not provider_config:
            return SyncResult(
                provider_key=provider_key,
                status="error",
                message=f"Provider {provider_key} not found in config",
                error="Provider not found",
            )
        
        try:
            # Upsert provider
            db_provider = await self._upsert_provider(db, provider_key, provider_config)
            
            # 同步模型
            if sync_models:
                models = await self._model_service.list_models(
                    provider_key, api_key=None, use_cache=False
                )
                
                if models:
                    models_synced = await self._upsert_models(db, db_provider, models)
                    await db.commit()
                    
                    return SyncResult(
                        provider_key=provider_key,
                        status="success",
                        models_count=len(models),
                        message=f"Synced {models_synced} models",
                    )
                else:
                    return SyncResult(
                        provider_key=provider_key,
                        status="skipped",
                        message="No models to sync (discovery disabled or failed)",
                    )
            else:
                return SyncResult(
                    provider_key=provider_key,
                    status="success",
                    models_count=0,
                    message="Provider synced (model sync skipped)",
                )
                
        except Exception as e:
            await db.rollback()
            logger.error(f"Error syncing provider {provider_key}: {e}")
            return SyncResult(
                provider_key=provider_key,
                status="error",
                message=str(e),
                error=str(e),
            )
    
    async def _upsert_provider(
        self,
        db: AsyncSession,
        provider_key: str,
        provider_config: ProviderConfig,
    ) -> DBProvider:
        """Upsert 提供商记录。"""
        result = await db.execute(select(DBProvider).filter(
            DBProvider.provider_key == provider_key
        ))
        db_provider = result.scalar_one_or_none()
        
        if not db_provider:
            db_provider = DBProvider(
                provider_key=provider_key,
                display_name=provider_config.display_name,
                provider_type=provider_config.provider_type.value,
                requires_api_key=True,
                requires_base_url=provider_config.endpoints.requires_base_url,
                requires_custom_model_name=provider_config.requires_custom_model_name,
                default_base_url=provider_config.endpoints.api_base or None,
            )
            db.add(db_provider)
            await db.flush()
            logger.info(f"Created provider: {provider_key}")
        else:
            # 更新字段
            db_provider.display_name = provider_config.display_name
            db_provider.provider_type = provider_config.provider_type.value
            db_provider.requires_base_url = provider_config.endpoints.requires_base_url
            db_provider.requires_custom_model_name = provider_config.requires_custom_model_name
            db_provider.default_base_url = provider_config.endpoints.api_base or None
            logger.info(f"Updated provider: {provider_key}")
        
        return db_provider
    
    async def _upsert_models(
        self,
        db: AsyncSession,
        db_provider: DBProvider,
        models: List[ModelInfo],
    ) -> int:
        """Upsert 模型记录。
        
        Args:
            db: 数据库 Session
            db_provider: 提供商记录
            models: 模型信息列表
            
        Returns:
            int: 同步的模型数量
        """
        existing_models = {
            m.model_key: m for m in db_provider.models
        }
        
        models_synced = 0
        now = datetime.now()
        
        for model in models:
            model_key = model.model_key
            
            if model_key in existing_models:
                # 更新现有模型
                db_model = existing_models[model_key]
                db_model.display_name = model.display_name
                db_model.context_length = model.context_length
                db_model.supports_tools = model.supports_tools
                db_model.performance_level = model.performance_level
                db_model.is_thinking = model.is_thinking
                db_model.last_updated_from_api = now
                
                # 更新定价
                if model.pricing:
                    db_model.cost_per_million_input_tokens = model.pricing.get("input")
                    db_model.cost_per_million_output_tokens = model.pricing.get("output")
                
                models_synced += 1
            else:
                # 创建新模型
                db_model = DBModel(
                    provider_id=db_provider.id,
                    model_key=model_key,
                    display_name=model.display_name,
                    context_length=model.context_length,
                    supports_tools=model.supports_tools,
                    performance_level=model.performance_level,
                    is_thinking=model.is_thinking,
                    cost_per_million_input_tokens=model.pricing.get("input") if model.pricing else None,
                    cost_per_million_output_tokens=model.pricing.get("output") if model.pricing else None,
                    last_updated_from_api=now,
                )
                db.add(db_model)
                models_synced += 1
        
        return models_synced
    
    async def sync_models_with_api_key(
        self,
        db: AsyncSession,
        provider_key: str,
        api_key: str,
        base_url: Optional[str] = None,
    ) -> SyncResult:
        """使用 API Key 动态同步模型。
        
        Args:
            db: 数据库 Session
            provider_key: 提供商键
            api_key: API Key
            base_url: 自定义 Base URL
            
        Returns:
            SyncResult: 同步结果
        """
        try:
            # 获取提供商配置
            provider_config = self._config_store.get_provider(provider_key)
            if not provider_config:
                return SyncResult(
                    provider_key=provider_key,
                    status="error",
                    message=f"Provider {provider_key} not found",
                    error="Provider not found",
                )
            
            # 确保提供商记录存在
            db_provider = await self._upsert_provider(db, provider_key, provider_config)
            
            # 动态发现模型
            models = await self._model_service.list_models(
                provider_key, api_key=api_key, base_url=base_url, use_cache=False
            )
            
            if not models:
                return SyncResult(
                    provider_key=provider_key,
                    status="skipped",
                    message="No models discovered",
                )
            
            # 同步模型
            models_synced = await self._upsert_models(db, db_provider, models)
            await db.commit()
            
            return SyncResult(
                provider_key=provider_key,
                status="success",
                models_count=models_synced,
                message=f"Synced {models_synced} models via API",
            )
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error syncing models for {provider_key}: {e}")
            return SyncResult(
                provider_key=provider_key,
                status="error",
                message=str(e),
                error=str(e),
            )
    
    async def sync_pricing_from_config(
        self,
        db: AsyncSession,
        provider_key: Optional[str] = None,
    ) -> Dict[str, int]:
        """从配置文件同步定价信息。
        
        Args:
            db: 数据库 Session
            provider_key: 指定提供商键（可选，同步所有）
            
        Returns:
            Dict: provider_key -> 更新的模型数量
        """
        results = {}
        pricing_config = self._config_store.pricing
        
        # 获取要同步的提供商
        if provider_key:
            providers_to_sync = [provider_key] if provider_key in pricing_config.pricing else []
        else:
            providers_to_sync = list(pricing_config.pricing.keys())
        
        for p_key in providers_to_sync:
            provider_pricing = pricing_config.pricing[p_key]
            result = await db.execute(select(DBProvider).filter(
                DBProvider.provider_key == p_key
            ))
            db_provider = result.scalar_one_or_none()
            
            if not db_provider:
                continue
            
            updated_count = 0
            for model_key, model_pricing in provider_pricing.models.items():
                result = await db.execute(select(DBModel).filter(
                    DBModel.provider_id == db_provider.id,
                    DBModel.model_key == model_key,
                ))
                db_model = result.scalar_one_or_none()
                
                if db_model:
                    db_model.cost_per_million_input_tokens = model_pricing.input
                    db_model.cost_per_million_output_tokens = model_pricing.output
                    updated_count += 1
            
            await db.commit()
            results[p_key] = updated_count
        
        return results


# 全局服务实例
_db_sync_service: Optional[DBSyncService] = None


def get_db_sync_service() -> DBSyncService:
    """获取全局数据库同步服务实例。"""
    global _db_sync_service
    if _db_sync_service is None:
        _db_sync_service = DBSyncService()
    return _db_sync_service


def reset_db_sync_service() -> None:
    """重置数据库同步服务（主要用于测试）。"""
    global _db_sync_service
    _db_sync_service = None
