"""
Unified Tool Registry API v2

统一工具注册中心 - 合并 MCP、Quant、CrewAI 和用户自定义工具的管理接口。

设计原则：
1. 统一的工具标识格式: "source:category:name"
2. 分离系统级状态 (is_active) 和用户级偏好 (is_enabled)
3. 所有工具来源通过同一套 API 管理

工具来源：
- mcp: 系统 MCP 服务器的工具
- quant: 内置量化分析工具  
- crewai: CrewAI 官方工具
- user: 用户自定义工具
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from backend.app.security import get_db, get_current_user, get_current_user_optional
from AICrews.database.models import (
    User, MCPServer, MCPTool, UserMCPSubscription, UserStrategy, BuiltinTool,
    UserToolPreference
)
from AICrews.schemas.tool import (
    UnifiedTool,
    ToolTierGroup,
    UnifiedToolsResponse,
    ToggleToolRequest,
    ToggleToolResponse,
    MCPServerStatus,
    VerifyAPIKeyRequest,
    VerifyAPIKeyResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tool-registry", tags=["Unified Tool Registry"])


# ============================================
# Helper Functions
# ============================================

def _get_user_tool_preferences(user_id: int, db: Session) -> Dict[str, bool]:
    """获取用户的工具偏好设置"""
    prefs = db.query(UserToolPreference).filter(
        UserToolPreference.user_id == user_id
    ).all()
    return {p.tool_key: p.is_enabled for p in prefs}


def _get_mcp_tools(db: Session, user_id: Optional[int] = None) -> List[UnifiedTool]:
    """获取所有 MCP 工具"""
    tools = []

    # 获取用户偏好
    user_prefs = {}
    if user_id:
        user_prefs = _get_user_tool_preferences(user_id, db)

    # 获取系统 MCP 服务器的工具
    mcp_tools = db.query(MCPTool).join(MCPServer).filter(
        MCPServer.is_active == True
    ).all()

    for tool in mcp_tools:
        # Use namespaced_name as key (new format: mcp_server_tool)
        # Fallback to legacy format if namespaced_name not available
        if tool.namespaced_name:
            tool_key = tool.namespaced_name
        else:
            tool_key = f"mcp:{tool.server.server_key}:{tool.tool_name}"

        # 确定 tier
        tier = "data"
        category_lower = (tool.category or "").lower()
        if any(x in category_lower for x in ["technical", "indicator", "quant"]):
            tier = "quant"
        elif any(x in category_lower for x in ["search", "web", "external"]):
            tier = "external"

        tools.append(UnifiedTool(
            key=tool_key,
            name=tool.display_name or tool.tool_name,
            description=tool.description or "",
            source="mcp",
            category=tool.category or "general",
            tier=tier,
            icon=None,
            is_active=tool.server.is_active,  # Inherit from parent server
            user_enabled=user_prefs.get(tool_key, False),
            requires_api_key=tool.requires_api_key,
            api_key_provider=tool.api_key_provider,
            is_configured=True,  # TODO: 检查实际配置状态
            server_key=tool.server.server_key,
            server_name=tool.server.display_name,
            sort_order=0,
        ))

    return tools


def _get_builtin_tools(db: Session, user_id: Optional[int] = None) -> List[UnifiedTool]:
    """获取内置工具（Quant 和 CrewAI）"""
    tools = []
    
    # 获取用户偏好
    user_prefs = {}
    if user_id:
        user_prefs = _get_user_tool_preferences(user_id, db)
    
    # 从数据库获取内置工具
    builtin_tools = db.query(BuiltinTool).filter(
        BuiltinTool.is_active == True
    ).order_by(BuiltinTool.sort_order).all()
    
    for tool in builtin_tools:
        tools.append(UnifiedTool(
            key=tool.tool_key,
            name=tool.display_name,
            description=tool.description or "",
            source=tool.source,
            category=tool.category,
            tier=tool.tier,
            icon=tool.icon,
            is_active=tool.is_active,
            user_enabled=user_prefs.get(tool.tool_key, False),  # 默认禁用，用户需手动启用
            requires_api_key=tool.requires_api_key,
            api_key_provider=tool.api_key_provider,
            is_configured=True,  # TODO: 检查实际配置状态
            server_key=None,
            server_name=None,
            sort_order=tool.sort_order,
        ))
    
    return tools


def _get_user_strategy_tools(db: Session, user_id: int) -> List[UnifiedTool]:
    """获取用户自定义策略工具"""
    tools = []
    
    strategies = db.query(UserStrategy).filter(
        UserStrategy.user_id == user_id,
        UserStrategy.is_active == True
    ).all()
    
    for s in strategies:
        tool_key = f"user:strategy:{s.id}"
        tools.append(UnifiedTool(
            key=tool_key,
            name=s.name,
            description=s.description or f"Custom strategy: {s.formula[:50]}...",
            source="user",
            category="strategy",
            tier="strategy",
            icon="🧮",
            is_active=True,
            user_enabled=s.is_active,
            requires_api_key=False,
            api_key_provider=None,
            is_configured=True,
            server_key=None,
            server_name=None,
            sort_order=100,
        ))
    
    return tools


# ============================================
# API Endpoints
# ============================================

@router.get("/tools", response_model=UnifiedToolsResponse, summary="获取所有工具")
async def list_all_tools(
    source: Optional[str] = Query(None, description="按来源过滤: mcp, quant, crewai, user"),
    tier: Optional[str] = Query(None, description="按层级过滤: data, quant, external, strategy"),
    enabled_only: bool = Query(False, description="只显示用户启用的工具"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    获取统一的工具列表
    
    合并所有来源的工具，按 tier 分组返回
    """
    user_id = current_user.id if current_user else None
    
    # 收集所有工具
    all_tools: List[UnifiedTool] = []
    
    # MCP 工具
    if source is None or source == "mcp":
        all_tools.extend(_get_mcp_tools(db, user_id))
    
    # 内置工具（Quant 和 CrewAI）
    if source is None or source in ["quant", "crewai"]:
        builtin = _get_builtin_tools(db, user_id)
        if source:
            builtin = [t for t in builtin if t.source == source]
        all_tools.extend(builtin)
    
    # 用户策略工具
    if user_id and (source is None or source == "user"):
        all_tools.extend(_get_user_strategy_tools(db, user_id))
    
    # 按 tier 过滤
    if tier:
        all_tools = [t for t in all_tools if t.tier == tier]
    
    # 按 enabled 过滤
    if enabled_only:
        all_tools = [t for t in all_tools if t.user_enabled and t.is_active]
    
    # 按 tier 分组
    tier_groups = {
        "data": {"title": "📂 Data Feeds", "icon": "📂", "tools": []},
        "quant": {"title": "🧠 Quant Skills", "icon": "🧠", "tools": []},
        "external": {"title": "🌍 External Access", "icon": "🌍", "tools": []},
        "strategy": {"title": "💎 User Strategies", "icon": "💎", "tools": []},
    }
    
    for tool in all_tools:
        if tool.tier in tier_groups:
            tier_groups[tool.tier]["tools"].append(tool)
    
    # 构建响应
    tiers = []
    for tier_key, tier_data in tier_groups.items():
        tools = tier_data["tools"]
        tiers.append(ToolTierGroup(
            tier=tier_key,
            title=tier_data["title"],
            icon=tier_data["icon"],
            tools=tools,
            total=len(tools),
            enabled_count=len([t for t in tools if t.user_enabled and t.is_active]),
        ))
    
    return UnifiedToolsResponse(
        tiers=tiers,
        summary={
            "total": len(all_tools),
            "enabled": len([t for t in all_tools if t.user_enabled and t.is_active]),
            "mcp": len([t for t in all_tools if t.source == "mcp"]),
            "quant": len([t for t in all_tools if t.source == "quant"]),
            "crewai": len([t for t in all_tools if t.source == "crewai"]),
            "user": len([t for t in all_tools if t.source == "user"]),
        }
    )


@router.post("/tools/{tool_key:path}/toggle", response_model=ToggleToolResponse, summary="切换工具启用状态")
async def toggle_tool(
    tool_key: str,
    request: ToggleToolRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    统一的工具启用/禁用接口
    
    tool_key 格式: source:category:name (例如 mcp:akshare:stock_zh_a_hist)
    """
    # 解析 tool_key
    parts = tool_key.split(":", 2)
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid tool_key format")
    
    source = parts[0]
    
    # 验证工具存在
    tool_exists = False
    
    if source == "mcp":
        # MCP 工具
        if len(parts) == 3:
            server_key, tool_name = parts[1], parts[2]
            mcp_tool = db.query(MCPTool).join(MCPServer).filter(
                MCPServer.server_key == server_key,
                MCPTool.tool_name == tool_name
            ).first()
            tool_exists = mcp_tool is not None
    elif source in ["quant", "crewai"]:
        # 内置工具
        builtin = db.query(BuiltinTool).filter(
            BuiltinTool.tool_key == tool_key
        ).first()
        tool_exists = builtin is not None
    elif source == "user":
        # 用户策略
        if len(parts) == 3 and parts[1] == "strategy":
            strategy_id = int(parts[2])
            strategy = db.query(UserStrategy).filter(
                UserStrategy.id == strategy_id,
                UserStrategy.user_id == current_user.id
            ).first()
            if strategy:
                tool_exists = True
                # 直接更新策略的 is_active
                strategy.is_active = request.enabled
                db.commit()
                return ToggleToolResponse(
                    tool_key=tool_key,
                    user_enabled=request.enabled,
                    message=f"Strategy {'enabled' if request.enabled else 'disabled'}"
                )
    
    if not tool_exists:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_key}")
    
    # 更新或创建用户偏好
    pref = db.query(UserToolPreference).filter(
        UserToolPreference.user_id == current_user.id,
        UserToolPreference.tool_key == tool_key
    ).first()
    
    if pref:
        pref.is_enabled = request.enabled
        pref.updated_at = datetime.now()
    else:
        now = datetime.now()
        pref = UserToolPreference(
            user_id=current_user.id,
            tool_key=tool_key,
            tool_source=source,
            is_enabled=request.enabled,
            created_at=now,
            updated_at=now,
        )
        db.add(pref)
    
    db.commit()
    
    return ToggleToolResponse(
        tool_key=tool_key,
        user_enabled=request.enabled,
        message=f"Tool {'enabled' if request.enabled else 'disabled'} successfully"
    )


@router.get("/servers", response_model=List[MCPServerStatus], summary="获取 MCP 服务器列表")
async def list_mcp_servers(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """获取所有 MCP 服务器及其状态"""
    servers = db.query(MCPServer).filter(MCPServer.is_active == True).all()
    
    # 获取用户订阅状态
    subscriptions = {}
    if current_user:
        subs = db.query(UserMCPSubscription).filter(
            UserMCPSubscription.user_id == current_user.id
        ).all()
        subscriptions = {s.server_id: s.is_active for s in subs}
    
    result = []
    for server in servers:
        # 统计工具数量
        tools = db.query(MCPTool).filter(MCPTool.server_id == server.id).all()
        
        # 统计用户启用的工具数量
        enabled_count = 0
        if current_user:
            user_prefs = _get_user_tool_preferences(current_user.id, db)
            for tool in tools:
                tool_key = f"mcp:{server.server_key}:{tool.tool_name}"
                if user_prefs.get(tool_key, False):
                    enabled_count += 1
        else:
            enabled_count = len(tools)
        
        result.append(MCPServerStatus(
            server_key=server.server_key,
            display_name=server.display_name,
            description=server.description,
            is_active=server.is_active,
            is_subscribed=subscriptions.get(server.id, True),
            tools_count=len(tools),
            enabled_tools_count=enabled_count,
        ))
    
    return result


@router.post("/servers/{server_key}/subscribe", summary="订阅/取消订阅 MCP 服务器")
async def subscribe_mcp_server(
    server_key: str,
    enabled: bool = Query(..., description="是否订阅"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    订阅或取消订阅 MCP 服务器
    
    取消订阅后，该服务器的所有工具将不可用
    """
    server = db.query(MCPServer).filter(MCPServer.server_key == server_key).first()
    if not server:
        raise HTTPException(status_code=404, detail=f"Server not found: {server_key}")
    
    # 查找或创建订阅记录
    sub = db.query(UserMCPSubscription).filter(
        UserMCPSubscription.user_id == current_user.id,
        UserMCPSubscription.server_id == server.id
    ).first()
    
    if sub:
        sub.is_active = enabled
        sub.updated_at = datetime.now()
    else:
        sub = UserMCPSubscription(
            user_id=current_user.id,
            server_id=server.id,
            is_active=enabled,
        )
        db.add(sub)
    
    db.commit()
    
    return {
        "server_key": server_key,
        "is_subscribed": enabled,
        "message": f"Server {'subscribed' if enabled else 'unsubscribed'} successfully"
    }


@router.post("/reset", summary="重置工具配置为默认")
async def reset_tool_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    重置用户的所有工具偏好为默认值（全部启用）
    """
    # 删除所有用户偏好
    db.query(UserToolPreference).filter(
        UserToolPreference.user_id == current_user.id
    ).delete()
    
    # 重置旧的 tools_config 字段
    current_user.tools_config = {}
    
    db.commit()
    
    return {"message": "All tool preferences reset to defaults (all enabled)"}


@router.get("/sources", summary="获取工具来源列表")
async def list_tool_sources():
    """获取所有支持的工具来源"""
    return [
        {
            "key": "mcp",
            "name": "MCP Data Sources",
            "description": "系统级 MCP 数据服务（akshare、openbb 等）",
            "icon": "🔌"
        },
        {
            "key": "quant",
            "name": "Native Quant",
            "description": "内置量化分析工具（RSI、MACD、MA 等）",
            "icon": "🧮"
        },
        {
            "key": "crewai",
            "name": "CrewAI Builtin",
            "description": "CrewAI 官方工具（搜索、网页抓取等）",
            "icon": "🌐"
        },
        {
            "key": "user",
            "name": "User Extensions",
            "description": "用户自定义策略和工具",
            "icon": "👤"
        },
    ]


@router.get("/tiers", summary="获取工具层级列表")
async def list_tool_tiers():
    """获取所有工具层级"""
    return [
        {
            "key": "data",
            "name": "Data Feeds",
            "description": "数据获取工具（行情、财务、新闻等）",
            "icon": "📂"
        },
        {
            "key": "quant",
            "name": "Quant Skills",
            "description": "量化分析工具（技术指标、策略评估等）",
            "icon": "🧠"
        },
        {
            "key": "external",
            "name": "External Access",
            "description": "外部访问工具（搜索、网页抓取等）",
            "icon": "🌍"
        },
        {
            "key": "strategy",
            "name": "User Strategies",
            "description": "用户自定义交易策略",
            "icon": "💎"
        },
    ]


@router.post("/servers/{server_key}/verify", response_model=VerifyAPIKeyResponse, summary="验证 MCP 服务器 API Key")
async def verify_server_api_key(
    server_key: str,
    request: VerifyAPIKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    验证 MCP 服务器的 API Key
    
    支持的验证类型:
    - openbb: 验证 OpenBB API Key
    - serper: 验证 Serper API Key  
    - 其他: 基本格式验证
    """
    import httpx
    
    server = db.query(MCPServer).filter(MCPServer.server_key == server_key).first()
    if not server:
        raise HTTPException(status_code=404, detail=f"Server not found: {server_key}")
    
    # 基本格式验证
    if not request.api_key or len(request.api_key) < 5:
        return VerifyAPIKeyResponse(
            valid=False,
            message="Invalid API Key format. Key must be at least 5 characters."
        )
    
    # 根据服务器类型进行实际验证
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if server_key == "openbb":
                # OpenBB API 验证
                response = await client.get(
                    "https://api.openbb.co/api/v1/user",
                    headers={"Authorization": f"Bearer {request.api_key}"}
                )
                if response.status_code == 200:
                    return VerifyAPIKeyResponse(valid=True, message="OpenBB API Key verified successfully.")
                else:
                    return VerifyAPIKeyResponse(valid=False, message=f"OpenBB API Key invalid: {response.status_code}")
            
            elif server_key == "serper":
                # Serper API 验证
                response = await client.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": request.api_key,
                        "Content-Type": "application/json"
                    },
                    json={"q": "test"}
                )
                if response.status_code == 200:
                    return VerifyAPIKeyResponse(valid=True, message="Serper API Key verified successfully.")
                else:
                    return VerifyAPIKeyResponse(valid=False, message=f"Serper API Key invalid: {response.status_code}")
            
            else:
                # 默认只做格式检查
                return VerifyAPIKeyResponse(valid=True, message="API Key format valid (no external verification).")
                
    except Exception as e:
        logger.error(f"API Key verification failed: {e}")
        return VerifyAPIKeyResponse(valid=False, message=f"Verification error: {str(e)}")
