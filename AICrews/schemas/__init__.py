"""
AICrews Schemas - 统一领域模型

这是项目的 Shared Kernel，包含所有 Pydantic 数据模型定义。
所有 API 层都应从这里导入 Schema，不要使用 backend.app.models。

导入示例:
    from AICrews.schemas.user import UserCreate, UserResponse
    from AICrews.schemas.llm import LLMProviderConfig
    from AICrews.schemas.market import AssetResponse
"""

from __future__ import annotations

# Common - 基础响应结构
from AICrews.schemas.common import (
    BaseResponse,
    ListResponse,
    ErrorResponse,
    PaginationParams,
)

# User - 用户相关
from AICrews.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdate,
    UserCredentialCreate,
    UserPortfolioCreate,
    UserPortfolioResponse,
)

# Market - 市场数据
from AICrews.schemas.market import (
    AssetCreate,
    AssetResponse,
    AssetUpdate,
    RealtimeQuoteResponse,
    StockPriceResponse,
    MarketNewsResponse,
    FundamentalDataResponse,
)

# LLM - LLM 配置
from AICrews.schemas.llm import (
    LLMProviderConfig,
    LLMProviderInfo,
    LLMModelInfo,
    LLMModelConfig,
    UserLLMConfigCreate,
    UserLLMConfigResponse,
)

# Agent - Agent 配置
from AICrews.schemas.agent import (
    AgentConfig,
    AgentCreate,
    AgentResponse,
    AgentUpdate,
)

# Crew - Crew 配置
from AICrews.schemas.crew import (
    CrewConfig,
    CrewCreate,
    CrewResponse,
    TaskConfig,
    TaskCreate,
    TaskResponse,
)

# Tool - 工具配置
from AICrews.schemas.tool import (
    ToolConfig,
    ToolCreate,
    ToolResponse,
    MCPToolConfig,
    MCPToolResponse,
)

# Billing - 计费订阅
from AICrews.schemas.billing import (
    SubscriptionResponse,
    InvoiceResponse,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    PortalSessionRequest,
    PortalSessionResponse,
    WebhookEventRequest,
    SubscriptionCancelRequest,
    SubscriptionCancelResponse,
    InvoiceListResponse,
)

# Security - 安全设置
from AICrews.schemas.security import (
    Setup2FARequest,
    Verify2FASetupRequest,
    Disable2FARequest,
    RevokeSessionRequest,
    TwoFactorSetupResponse,
    TwoFactorStatusResponse,
    LoginSessionResponse,
    SessionsResponse,
    LoginHistoryItem,
    LoginHistoryResponse,
)

__all__ = [
    # Common
    "BaseResponse",
    "ListResponse",
    "ErrorResponse",
    "PaginationParams",
    # User
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    "UserCredentialCreate",
    "UserPortfolioCreate",
    "UserPortfolioResponse",
    # Market
    "AssetCreate",
    "AssetResponse",
    "AssetUpdate",
    "RealtimeQuoteResponse",
    "StockPriceResponse",
    "MarketNewsResponse",
    "FundamentalDataResponse",
    # LLM
    "LLMProviderConfig",
    "LLMProviderInfo",
    "LLMModelInfo",
    "LLMModelConfig",
    "UserLLMConfigCreate",
    "UserLLMConfigResponse",
    # Agent
    "AgentConfig",
    "AgentCreate",
    "AgentResponse",
    "AgentUpdate",
    # Crew
    "CrewConfig",
    "CrewCreate",
    "CrewResponse",
    "TaskConfig",
    "TaskCreate",
    "TaskResponse",
    "PhaseConfig",
    # Tool
    "ToolConfig",
    "ToolCreate",
    "ToolResponse",
    "MCPToolConfig",
    "MCPToolResponse",
    # Billing
    "SubscriptionResponse",
    "InvoiceResponse",
    "CheckoutSessionRequest",
    "CheckoutSessionResponse",
    "PortalSessionRequest",
    "PortalSessionResponse",
    "WebhookEventRequest",
    "SubscriptionCancelRequest",
    "SubscriptionCancelResponse",
    "InvoiceListResponse",
    # Security
    "Setup2FARequest",
    "Verify2FASetupRequest",
    "Disable2FARequest",
    "RevokeSessionRequest",
    "TwoFactorSetupResponse",
    "TwoFactorStatusResponse",
    "LoginSessionResponse",
    "SessionsResponse",
    "LoginHistoryItem",
    "LoginHistoryResponse",
]
