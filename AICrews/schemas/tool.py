"""
Tool Schemas - 工具配置相关模型

定义 MCP Tool、Builtin Tool 相关的 Pydantic 模型。
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from AICrews.schemas.common import BaseSchema


class ToolConfig(BaseModel):
    """工具配置
    
    用于定义工具的基本信息。
    """
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    category: str = Field(..., description="工具类别")
    is_enabled: bool = Field(True, description="是否启用")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "get_fundamentals",
                "description": "获取基本面数据",
                "category": "data",
                "is_enabled": True
            }
        }
    )


class ToolCreate(BaseSchema):
    """工具创建请求
    
    用于创建新工具配置。
    """
    tool_key: str = Field(..., min_length=1, max_length=200, description="工具键")
    source: str = Field(..., description="工具来源: mcp, quant, crewai, user")
    display_name: str = Field(..., min_length=1, max_length=200, description="显示名称")
    description: Optional[str] = Field(None, description="工具描述")
    category: str = Field(..., description="工具类别")
    tier: str = Field("data", description="工具层级: data, quant, external")
    is_active: bool = Field(True, description="是否启用")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tool_key": "data:price:get_stock_price",
                "source": "mcp",
                "display_name": "Get Stock Price",
                "description": "获取实时股价数据",
                "category": "price",
                "tier": "data",
                "is_active": True
            }
        }
    )


class ToolResponse(BaseSchema):
    """工具响应
    
    用于返回工具信息。
    """
    id: int = Field(..., description="工具 ID")
    tool_key: str = Field(..., description="工具键")
    source: str = Field(..., description="工具来源")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="工具描述")
    category: str = Field(..., description="工具类别")
    tier: str = Field(..., description="工具层级")
    is_active: bool = Field(..., description="是否启用")
    created_at: datetime = Field(..., description="创建时间")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "tool_key": "data:price:get_stock_price",
                "source": "mcp",
                "display_name": "Get Stock Price",
                "category": "price",
                "tier": "data",
                "is_active": True,
                "created_at": "2025-12-26T00:00:00Z"
            }
        }
    )


class MCPToolConfig(BaseModel):
    """MCP 工具配置
    
    用于定义 MCP 工具的配置。
    """
    tool_name: str = Field(..., description="工具名称")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="工具描述")
    category: str = Field("custom", description="工具类别")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="输入参数 Schema")
    is_enabled: bool = Field(True, description="是否启用")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tool_name": "get_stock_price",
                "display_name": "Get Stock Price",
                "description": "获取实时股价数据",
                "category": "price",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string"}
                    }
                },
                "is_enabled": True
            }
        }
    )


class MCPToolResponse(BaseSchema):
    """MCP 工具响应
    
    用于返回 MCP 工具信息。
    """
    id: int = Field(..., description="工具 ID")
    server_id: int = Field(..., description="MCP 服务器 ID")
    
    tool_name: str = Field(..., description="工具名称")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="工具描述")
    category: str = Field(..., description="工具类别")
    
    input_schema: Optional[Dict[str, Any]] = Field(None, description="输入参数 Schema")
    required_params: Optional[List[str]] = Field(None, description="必需参数列表")
    
    is_active: bool = Field(..., description="是否启用")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    rate_limit: Optional[int] = Field(None, description="速率限制")
    cache_ttl: Optional[int] = Field(None, description="缓存时间")
    
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "server_id": 1,
                "tool_name": "get_stock_price",
                "display_name": "Get Stock Price",
                "description": "获取实时股价数据",
                "category": "price",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string"}
                    }
                },
                "is_active": True,
                "created_at": "2025-12-26T00:00:00Z",
                "updated_at": "2025-12-26T00:00:00Z"
            }
        }
    )


__all__ = [
    "ToolConfig",
    "ToolCreate",
    "ToolResponse",
    "MCPToolConfig",
    "MCPToolResponse",
    # Tool Registry API Schemas
    "UnifiedTool",
    "ToolTierGroup",
    "UnifiedToolsResponse",
    "ToggleToolRequest",
    "ToggleToolResponse",
    "MCPServerStatus",
    "VerifyAPIKeyRequest",
    "VerifyAPIKeyResponse",
    # Tool Usage Statistics Schemas
    "ToolUsageStats",
    "ToolRecommendation",
    "UsageStatsResponse",
]


# ============================================
# Tool Registry API Schemas (from endpoints)
# ============================================


class UnifiedTool(BaseModel):
    """
    Unified tool response model (Tool Registry API).

    Represents a tool from any source (MCP, quant, crewai, user) with
    consistent fields for display and management.
    """
    key: str = Field(..., description="Tool unique identifier (source:category:name)")
    name: str = Field(..., description="Display name")
    description: str = Field("", description="Tool description")
    source: str = Field(..., description="Source: mcp, quant, crewai, user")
    category: str = Field(..., description="Category")
    tier: str = Field("data", description="Tier: data, quant, external")
    icon: Optional[str] = Field(None, description="Icon")

    is_active: bool = Field(True, description="System-level status (admin controlled)")
    user_enabled: bool = Field(True, description="User enabled status")

    requires_api_key: bool = Field(False, description="Whether API Key is required")
    api_key_provider: Optional[str] = Field(None, description="API Key provider")
    is_configured: bool = Field(True, description="Whether API Key is configured")

    server_key: Optional[str] = Field(None, description="MCP server key (MCP tools only)")
    server_name: Optional[str] = Field(None, description="MCP server name")

    sort_order: int = Field(0, description="Sort order")


class ToolTierGroup(BaseModel):
    """Tool tier grouping for organized display (Tool Registry API)."""
    tier: str
    title: str
    icon: str
    tools: List[UnifiedTool]
    total: int
    enabled_count: int


class UnifiedToolsResponse(BaseModel):
    """Unified tool list response with tier grouping (Tool Registry API)."""
    tiers: List[ToolTierGroup]
    summary: Dict[str, int]


class ToggleToolRequest(BaseModel):
    """Request to toggle tool enabled status (Tool Registry API)."""
    enabled: bool = Field(..., description="Whether to enable")


class ToggleToolResponse(BaseModel):
    """Response after toggling tool status (Tool Registry API)."""
    tool_key: str
    user_enabled: bool
    message: str


class MCPServerStatus(BaseModel):
    """MCP server status information (Tool Registry API)."""
    server_key: str
    display_name: str
    description: Optional[str]
    is_active: bool
    is_subscribed: bool
    tools_count: int
    enabled_tools_count: int


class VerifyAPIKeyRequest(BaseModel):
    """Request to verify an API Key (Tool Registry API)."""
    api_key: str = Field(..., description="API Key or Token")


class VerifyAPIKeyResponse(BaseModel):
    """Response after API Key verification (Tool Registry API)."""
    valid: bool = Field(..., description="Whether valid")
    message: str = Field(..., description="Verification message")


# ============================================
# Tool Usage Statistics Schemas
# ============================================


class ToolUsageStats(BaseModel):
    """Tool usage statistics for a single tool."""
    tool_key: str
    tool_name: str
    source: str
    category: str
    usage_count: int
    last_used: Optional[datetime]
    avg_daily_usage: float


class ToolRecommendation(BaseModel):
    """Tool recommendation based on usage patterns."""
    tool_key: str
    tool_name: str
    source: str
    category: str
    reason: str
    score: float


class UsageStatsResponse(BaseModel):
    """Response containing tool usage statistics and recommendations."""
    total_usage: int
    most_used_tools: List[ToolUsageStats]
    recommendations: List[ToolRecommendation]
    usage_by_category: Dict[str, int]
    usage_by_source: Dict[str, int]
