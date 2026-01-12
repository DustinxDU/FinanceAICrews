"""
User Schemas - 用户相关模型

定义 User、Portfolio、Credential 等用户相关的 Pydantic 模型。
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from datetime import datetime

from AICrews.schemas.common import BaseSchema


class UserCreate(BaseSchema):
    """用户创建请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=8, max_length=100, description="密码")
    full_name: Optional[str] = Field(None, max_length=200, description="全名")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "username": "testuser",
                "password": "password123",
                "full_name": "Test User"
            }
        }
    )


class UserResponse(BaseSchema):
    """用户响应"""
    id: int = Field(..., description="用户 ID")
    email: EmailStr = Field(..., description="邮箱地址")
    username: str = Field(..., description="用户名")
    full_name: Optional[str] = Field(None, description="全名")
    phone_number: Optional[str] = Field(None, description="电话号码")
    avatar_url: Optional[str] = Field(None, description="头像 URL")
    email_verified: bool = Field(False, description="邮箱验证状态")
    pending_email: Optional[EmailStr] = Field(None, description="待验证的新邮箱")
    subscription_level: str = Field("free", description="订阅级别")
    last_password_change: Optional[datetime] = Field(None, description="最后密码修改时间")
    is_active: bool = Field(..., description="是否激活")
    is_superuser: bool = Field(False, description="是否超级用户")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "email": "user@example.com",
                "username": "testuser",
                "full_name": "Test User",
                "phone_number": "+1234567890",
                "avatar_url": "https://example.com/avatar.jpg",
                "email_verified": True,
                "pending_email": None,
                "subscription_level": "free",
                "last_password_change": "2025-12-26T00:00:00Z",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2025-12-26T00:00:00Z",
                "updated_at": "2025-12-26T00:00:00Z"
            }
        }
    )


class UserUpdate(BaseSchema):
    """用户更新请求 (Admin/System use only - no password required)"""
    full_name: Optional[str] = Field(None, max_length=200, description="全名")
    is_active: Optional[bool] = Field(None, description="是否激活")


class UserProfileUpdate(BaseSchema):
    """用户个人资料更新请求 (Self-service - requires current password)"""
    email: Optional[EmailStr] = Field(None, description="新邮箱地址")
    current_password: str = Field(..., min_length=8, max_length=100, description="当前密码 (必填)")
    new_password: Optional[str] = Field(None, min_length=8, max_length=100, description="新密码 (可选)")
    full_name: Optional[str] = Field(None, max_length=200, description="全名 (可选)")


class UserLogin(BaseSchema):
    """用户登录请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")


class Token(BaseSchema):
    """Token 响应"""
    access_token: str = Field(..., description="Access Token")
    token_type: str = Field(..., description="Token 类型")
    user: UserResponse = Field(..., description="用户信息")


class UserCredentialCreate(BaseSchema):
    """用户凭证创建请求"""
    user_id: int = Field(..., description="用户 ID")
    provider_id: str = Field(..., description="提供商 ID")
    credential_type: str = Field(..., description="凭证类型: api_key, endpoint_url")
    encrypted_value: str = Field(..., description="加密后的凭证值")
    display_mask: str = Field(..., description="显示掩码（如 sk-***）")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 1,
                "provider_id": "openai",
                "credential_type": "api_key",
                "encrypted_value": "encrypted_string...",
                "display_mask": "sk-***"
            }
        }
    )


class UserCredentialResponse(BaseSchema):
    """用户凭证响应"""
    id: int = Field(..., description="凭证 ID")
    user_id: int = Field(..., description="用户 ID")
    provider_id: str = Field(..., description="提供商 ID")
    credential_type: str = Field(..., description="凭证类型")
    display_mask: str = Field(..., description="显示掩码")
    is_verified: bool = Field(..., description="是否已验证")
    updated_at: datetime = Field(..., description="更新时间")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": 1,
                "provider_id": "openai",
                "credential_type": "api_key",
                "display_mask": "sk-***",
                "is_verified": True,
                "updated_at": "2025-12-26T00:00:00Z"
            }
        }
    )


class UserPortfolioCreate(BaseSchema):
    """用户投资组合创建请求"""
    user_id: int = Field(..., description="用户 ID")
    ticker: str = Field(..., min_length=1, max_length=20, description="资产代码")
    notes: Optional[str] = Field(None, description="备注")
    target_price: Optional[float] = Field(None, description="目标价")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 1,
                "ticker": "AAPL",
                "notes": "关注股票",
                "target_price": 200.0
            }
        }
    )


class UserPortfolioUpdate(BaseSchema):
    """用户投资组合更新请求"""
    notes: Optional[str] = Field(None, description="备注")
    target_price: Optional[float] = Field(None, description="目标价")


class UserPortfolioResponse(BaseSchema):
    """用户投资组合响应"""
    user_id: int = Field(..., description="用户 ID")
    ticker: str = Field(..., description="资产代码")
    notes: Optional[str] = Field(None, description="备注")
    target_price: Optional[float] = Field(None, description="目标价")
    added_at: datetime = Field(..., description="添加时间")
    
    # 关联的资产信息
    asset_name: Optional[str] = Field(None, description="资产名称")
    asset_type: Optional[str] = Field(None, description="资产类型")
    current_price: Optional[float] = Field(None, description="当前价格")
    price_local: Optional[float] = Field(None, description="本地货币价格")
    currency_local: Optional[str] = Field(None, description="本地货币代码")
    price_change: Optional[float] = Field(None, description="价格变化")
    price_change_percent: Optional[float] = Field(None, description="价格变化百分比")
    market_cap: Optional[int] = Field(None, description="市值")
    volume: Optional[int] = Field(None, description="成交量")
    exchange: Optional[str] = Field(None, description="交易所")
    currency: Optional[str] = Field(None, description="货币")
    last_updated: Optional[datetime] = Field(None, description="最后更新时间")
    is_market_open: Optional[bool] = Field(None, description="市场是否开放")
    trade_time: Optional[datetime] = Field(None, description="交易时间")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "user_id": 1,
                "ticker": "AAPL",
                "notes": "关注股票",
                "target_price": 200.0,
                "added_at": "2025-12-26T00:00:00Z",
                "asset_name": "Apple Inc.",
                "asset_type": "US",
                "current_price": 185.0,
                "price_change_percent": 1.37
            }
        }
    )

class PortfolioSummary(BaseSchema):
    """投资组合摘要"""
    total_assets: int = Field(..., description="总资产数")
    asset_types: Dict[str, int] = Field(..., description="各类型资产数")
    last_updated: Optional[datetime] = Field(None, description="最后更新时间")


class UserUploadResponse(BaseSchema):
    """用户上传文件响应"""
    id: str = Field(..., description="上传 ID (UUID)")
    user_id: int = Field(..., description="用户 ID")
    original_name: str = Field(..., description="原始文件名")
    storage_path: str = Field(..., description="存储路径")
    mime_type: str = Field(..., description="MIME 类型")
    parsing_status: str = Field(..., description="解析状态: pending, processing, completed, failed")
    token_count: Optional[int] = Field(None, description="Token 数量")
    created_at: datetime = Field(..., description="创建时间")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": 1,
                "original_name": "document.pdf",
                "storage_path": "/uploads/user_1/document.pdf",
                "mime_type": "application/pdf",
                "parsing_status": "completed",
                "token_count": 1500,
                "created_at": "2025-12-26T00:00:00Z"
            }
        }
    )


class UserCockpitIndicatorResponse(BaseSchema):
    """用户 Cockpit 指标响应"""
    id: int = Field(..., description="指标 ID")
    user_id: int = Field(..., description="用户 ID")
    indicator_id: str = Field(..., description="指标 ID")
    display_order: int = Field(..., description="显示顺序")
    is_active: bool = Field(..., description="是否启用")
    added_at: datetime = Field(..., description="添加时间")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": 1,
                "indicator_id": "vix_index",
                "display_order": 1,
                "is_active": True,
                "added_at": "2025-12-26T00:00:00Z"
            }
        }
    )


class UserAssetCacheResponse(BaseSchema):
    """用户资产缓存响应"""
    id: int = Field(..., description="缓存 ID")
    user_id: int = Field(..., description="用户 ID")
    ticker: str = Field(..., description="资产代码")
    asset_type: str = Field(..., description="资产类型")
    asset_name: Optional[str] = Field(None, description="资产名称")
    current_price: Optional[float] = Field(None, description="当前价格")
    price_change: Optional[float] = Field(None, description="价格变化")
    price_change_percent: Optional[float] = Field(None, description="价格变化百分比")
    market_cap: Optional[int] = Field(None, description="市值")
    volume: Optional[int] = Field(None, description="成交量")
    exchange: Optional[str] = Field(None, description="交易所")
    currency: Optional[str] = Field(None, description="货币")
    data_source: str = Field(..., description="数据来源")
    last_updated: datetime = Field(..., description="最后更新时间")
    fetch_error: Optional[str] = Field(None, description="获取错误")
    is_valid: bool = Field(..., description="是否有效")
    created_at: datetime = Field(..., description="创建时间")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": 1,
                "ticker": "AAPL",
                "asset_type": "US",
                "asset_name": "Apple Inc.",
                "current_price": 185.0,
                "price_change": 2.5,
                "price_change_percent": 1.37,
                "data_source": "mcp",
                "last_updated": "2025-12-26T00:00:00Z",
                "is_valid": True,
                "created_at": "2025-12-26T00:00:00Z"
            }
        }
    )


__all__ = [
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    "UserProfileUpdate",
    "UserLogin",
    "Token",
    "UserCredentialCreate",
    "UserCredentialResponse",
    "UserPortfolioCreate",
    "UserPortfolioUpdate",
    "UserPortfolioResponse",
    "PortfolioSummary",
    "UserUploadResponse",
    "UserCockpitIndicatorResponse",
    "UserAssetCacheResponse",
]
