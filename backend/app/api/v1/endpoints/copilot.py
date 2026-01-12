"""
Copilot API - 全局AI助手
功能：
1. 上下文记忆对话
2. MCP联网搜索
3. 金融专家人设
4. 使用用户默认LLM配置

API Layer - 仅负责路由和参数校验
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.security import get_current_user, get_db
from AICrews.database.models import User
from AICrews.schemas.copilot import (
    CopilotChatRequest, CopilotChatResponse, CopilotHistoryResponse, CopilotMessage,
    UserPreferencesResponse, UserPreferencesUpdate, AvailableLLMConfig
)
from AICrews.database.models import UserLLMConfig, LLMProvider, UserModelConfig
from AICrews.services.copilot_service import CopilotService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/copilot", tags=["Copilot"])

def get_copilot_service(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CopilotService:
    # 优先使用 default_model_config_id (新字段)，回退到 default_llm_config_id (旧字段)
    llm_config_id = None
    if current_user.default_model_config_id:
        llm_config_id = str(current_user.default_model_config_id)
    elif current_user.default_llm_config_id:
        llm_config_id = current_user.default_llm_config_id
    return CopilotService(db, current_user.id, llm_config_id)


def _build_available_llm_configs(
    current_user: User,
    db: Session
) -> List[AvailableLLMConfig]:
    """Build list of available LLM configurations for user.

    Queries UserModelConfig joined with UserLLMConfig to get all
    active and available model configurations for the current user.
    """
    model_configs = db.query(UserModelConfig).join(
        UserLLMConfig, UserModelConfig.llm_config_id == UserLLMConfig.id
    ).filter(
        UserLLMConfig.user_id == current_user.id,
        UserLLMConfig.is_active == True,
        UserModelConfig.is_active == True,
        UserModelConfig.is_available == True
    ).all()

    available_configs = []
    for model_config in model_configs:
        llm_config = model_config.llm_config
        provider = db.query(LLMProvider).filter(
            LLMProvider.id == llm_config.provider_id
        ).first()
        provider_name = provider.display_name if provider else "Unknown"
        provider_key = provider.provider_key if provider else ""

        # 构建模型名称显示
        if provider_key == "volcengine" and model_config.volcengine_endpoint_id:
            model_name = f"Endpoint: {model_config.volcengine_endpoint_id}"
        elif model_config.model:
            model_name = model_config.model.display_name
        else:
            model_name = ""

        available_configs.append(AvailableLLMConfig(
            id=str(model_config.id),
            name=f"{provider_name} - {model_name}",
            provider_name=provider_name,
            model_name=model_name
        ))

    return available_configs

@router.post("/chat", response_model=CopilotChatResponse)
async def chat(
    request: CopilotChatRequest,
    service: CopilotService = Depends(get_copilot_service)
):
    """
    发送消息给 Copilot
    """
    start_time = datetime.now()
    
    try:
        reply, sources, search_performed = await service.generate_response(
            message=request.message,
            context=request.context,
            enable_web_search=request.enable_web_search
        )
        
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return CopilotChatResponse(
            reply=reply,
            sources=sources,
            search_performed=search_performed,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Copilot chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/stream")
async def chat_stream(
    message: str = Query(..., description="用户消息"),
    context: Optional[str] = Query(None, description="上下文"),
    enable_web_search: bool = Query(True, description="是否启用搜索"),
    service: CopilotService = Depends(get_copilot_service)
):
    """
    流式发送消息给 Copilot (SSE)
    """
    return StreamingResponse(
        service.generate_streaming_response(
            message=message,
            context=context,
            enable_web_search=enable_web_search
        ),
        media_type="text/event-stream"
    )

@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户 Copilot 偏好设置"""
    available_configs = _build_available_llm_configs(current_user, db)

    return UserPreferencesResponse(
        default_llm_config_id=str(current_user.default_llm_config_id) if current_user.default_llm_config_id else None,
        default_model_config_id=current_user.default_model_config_id,
        available_llm_configs=available_configs
    )

@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    request: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户 Copilot 偏好设置"""
    # 优先使用新的 model-level 选择
    if request.default_model_config_id is not None:
        current_user.default_model_config_id = request.default_model_config_id
        # 设置新字段时清除旧字段，避免混淆
        current_user.default_llm_config_id = None

    # 向后兼容：如果只提供了 llm_config_id（旧客户端），则更新它
    elif request.default_llm_config_id is not None:
        current_user.default_llm_config_id = request.default_llm_config_id if request.default_llm_config_id else None

    db.commit()
    db.refresh(current_user)

    available_configs = _build_available_llm_configs(current_user, db)

    return UserPreferencesResponse(
        default_llm_config_id=str(current_user.default_llm_config_id) if current_user.default_llm_config_id else None,
        default_model_config_id=current_user.default_model_config_id,
        available_llm_configs=available_configs
    )

@router.get("/history", response_model=CopilotHistoryResponse)
async def get_history(
    service: CopilotService = Depends(get_copilot_service)
):
    """
    获取对话历史
    """
    history_data = await service.get_conversation_history()
    
    messages = [
        CopilotMessage(
            role=msg["role"],
            content=msg["content"],
            timestamp=msg.get("timestamp")
        )
        for msg in history_data
    ]
    
    return CopilotHistoryResponse(
        messages=messages,
        total_count=len(messages)
    )

@router.delete("/history")
async def clear_history(
    service: CopilotService = Depends(get_copilot_service)
):
    """
    清除对话历史
    """
    await service.clear_history()
    return {"status": "success", "message": "History cleared"}
