"""
Knowledge Marketplace API - 知识市场管理

仿照 MCP 市场架构，提供知识源的浏览、订阅、管理功能。
用户可以从市场订阅知识卡带，并在 Crew 搭建时选择注入。

Runtime Flow:
    1. 用户在知识市场浏览并订阅知识卡带
    2. 用户在 Crew Builder 中选择要注入的知识源
    3. CrewFactory 根据配置加载 CrewAI Knowledge Source
    4. Agent 自动通过 RAG 检索相关知识
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session

from backend.app.security import get_current_user, get_current_user_optional, get_db
from AICrews.database.models import User

# Import schemas
from AICrews.schemas.knowledge import (
    CreateUserKnowledgeRequest,
    CrewKnowledgeBindingRequest,
    AgentKnowledgeBindingRequest,
    AgentKnowledgeBindingResponse,
    CrewKnowledgeBindingResponse
)

# Import service
from AICrews.services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["Knowledge Marketplace"])

# ============================================
# 依赖注入
# ============================================

def get_knowledge_service(db: Session = Depends(get_db)) -> KnowledgeService:
    return KnowledgeService(db)

# ============================================
# 知识市场 API
# ============================================

@router.get("/marketplace", summary="浏览知识市场")
async def list_marketplace(
    category: Optional[str] = Query(None, description="按类别过滤"),
    knowledge_scope: Optional[str] = Query(None, description="按注入作用域过滤: crew, agent, both"),
    tier: Optional[str] = Query(None, description="按等级过滤: free, premium"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Dict[str, Any]:
    """
    列出知识市场中的所有知识源
    """
    return service.list_marketplace(category, knowledge_scope, tier, search, current_user)

@router.get("/marketplace/{source_key}", summary="获取知识源详情")
async def get_knowledge_source(
    source_key: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Dict[str, Any]:
    """获取知识源详细信息"""
    result = service.get_knowledge_source(source_key, current_user)
    if not result:
        raise HTTPException(status_code=404, detail="Knowledge source not found")
    return result

@router.post("/marketplace/{source_key}/subscribe", summary="订阅知识源")
async def subscribe_knowledge(
    source_key: str,
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Dict[str, Any]:
    """订阅一个知识源到用户的知识库"""
    try:
        return service.subscribe_knowledge(source_key, current_user)
    except ValueError as e:
        if str(e) == "Knowledge source not found":
            raise HTTPException(status_code=404, detail=str(e))
        elif str(e) == "Already subscribed":
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/marketplace/{source_key}/unsubscribe", summary="取消订阅")
async def unsubscribe_knowledge(
    source_key: str,
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Dict[str, str]:
    """取消订阅知识源"""
    try:
        return service.unsubscribe_knowledge(source_key, current_user)
    except ValueError as e:
        if str(e) == "Knowledge source not found":
            raise HTTPException(status_code=404, detail=str(e))
        elif str(e) == "Not subscribed":
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# 用户知识库 API
# ============================================

@router.get("/my-sources", summary="我的知识库")
async def list_my_sources(
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Dict[str, Any]:
    """列出用户订阅的知识源和自定义知识源"""
    return service.list_my_sources(current_user)

@router.post("/my-sources", summary="创建自定义知识源")
async def create_user_knowledge(
    request: CreateUserKnowledgeRequest,
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Dict[str, Any]:
    """创建用户自定义知识源（文本内容）"""
    return service.create_user_knowledge(request, current_user)

@router.post("/upload", summary="上传知识文件")
async def upload_knowledge(
    file: UploadFile = File(...),
    display_name: str = Query(...),
    description: Optional[str] = Query(None),
    category: str = Query("custom"),
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Dict[str, Any]:
    """
    上传知识文件 (PDF, TXT, MD, CSV)
    
    文件将存储在 config/knowledge/user_{user_id}/ 目录下
    """
    allowed_extensions = {".pdf", ".txt", ".md", ".csv", ".json"}
    # Use filename attribute if available, otherwise empty string
    filename = file.filename or ""
    file_ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {allowed_extensions}"
        )
    
    content = await file.read()
    
    try:
        return service.upload_knowledge_file(
            file_content=content,
            filename=filename,
            display_name=display_name,
            description=description,
            category=category,
            current_user=current_user
        )
    except Exception as e:
        logger.error(f"Error uploading knowledge file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@router.delete("/my-sources/{source_id}", summary="删除自定义知识源")
async def delete_user_knowledge(
    source_id: int,
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Dict[str, str]:
    """删除用户自定义知识源"""
    try:
        return service.delete_user_knowledge(source_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# ============================================
# Crew 知识绑定 API
# ============================================

@router.get("/bindings/{crew_name}", summary="获取 Crew 知识绑定")
async def get_crew_knowledge_binding(
    crew_name: str,
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> CrewKnowledgeBindingResponse:
    """获取 Crew 的知识绑定配置"""
    return service.get_crew_knowledge_binding(crew_name, current_user)

@router.post("/bindings/{crew_name}", summary="设置 Crew 知识绑定")
async def set_crew_knowledge_binding(
    crew_name: str,
    request: CrewKnowledgeBindingRequest,
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Dict[str, Any]:
    """设置 Crew 的知识绑定配置"""
    return service.set_crew_knowledge_binding(crew_name, request, current_user)

@router.delete("/bindings/{crew_name}", summary="删除 Crew 知识绑定")
async def delete_crew_knowledge_binding(
    crew_name: str,
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Dict[str, str]:
    """删除 Crew 的知识绑定配置（恢复默认）"""
    try:
        return service.delete_crew_knowledge_binding(crew_name, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# ============================================
# 知识源分类 API
# ============================================

@router.get("/categories", summary="获取知识分类")
async def list_categories(
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Dict[str, Any]:
    """获取所有知识分类及其统计"""
    return service.list_categories()

# ============================================
# Agent 级别知识绑定 API
# ============================================

@router.post("/agents/bind", summary="绑定 Agent 知识源")
async def bind_agent_knowledge(
    request: AgentKnowledgeBindingRequest,
    crew_name: str = Query(..., description="Crew 名称"),
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> AgentKnowledgeBindingResponse:
    """为指定 Agent 绑定知识源（显式绑定）"""
    return service.bind_agent_knowledge(request, crew_name, current_user)

@router.get("/agents/{crew_name}/{agent_name}/binding", summary="获取 Agent 知识绑定")
async def get_agent_knowledge_binding(
    crew_name: str,
    agent_name: str,
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> AgentKnowledgeBindingResponse:
    """获取指定 Agent 的知识绑定配置"""
    return service.get_agent_knowledge_binding(crew_name, agent_name, current_user)

@router.delete("/agents/{crew_name}/{agent_name}/binding", summary="删除 Agent 知识绑定")
async def delete_agent_knowledge_binding(
    crew_name: str,
    agent_name: str,
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Dict[str, str]:
    """删除指定 Agent 的知识绑定配置"""
    try:
        return service.delete_agent_knowledge_binding(crew_name, agent_name, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# ============================================
# 知识源版本管理 API
# ============================================

@router.get("/sources/{source_key}/versions", summary="获取知识源版本列表")
async def list_knowledge_versions(
    source_key: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Dict[str, Any]:
    """获取知识源的所有版本"""
    try:
        return service.list_knowledge_versions(source_key)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# ============================================
# 知识源使用统计 API
# ============================================

@router.get("/stats/usage", summary="获取知识源使用统计")
async def get_usage_stats(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Dict[str, Any]:
    """获取用户的知识源使用统计"""
    return service.get_usage_stats(days, current_user)

@router.get("/stats/popular", summary="获取热门知识源")
async def get_popular_sources(
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Dict[str, Any]:
    """获取全局热门知识源（按使用次数排序）"""
    return service.get_popular_sources(limit)
