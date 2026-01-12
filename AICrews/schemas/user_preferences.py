"""
User Preferences Schemas - 用户偏好设置 Pydantic 模型
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class PushSubscriptionKeys(BaseModel):
    """Web Push subscription keys"""
    p256dh: str = Field(..., description="P256DH public key")
    auth: str = Field(..., description="Auth secret")


class PushSubscriptionData(BaseModel):
    """Web Push subscription data"""
    endpoint: str = Field(..., description="Push service endpoint URL")
    keys: PushSubscriptionKeys


class UserNotificationPreferencesRequest(BaseModel):
    """Request to update user notification preferences"""
    enabled: bool = Field(..., description="Master notification toggle")
    analysis_completion: bool = Field(default=True, description="Notify on analysis completion")
    system_updates: bool = Field(default=True, description="Notify on system updates")
    push_subscription: Optional[PushSubscriptionData] = Field(default=None, description="Web Push subscription")


class UserNotificationPreferencesResponse(BaseModel):
    """Response with user notification preferences"""
    id: int
    user_id: int
    enabled: bool
    analysis_completion: bool
    system_updates: bool
    has_push_subscription: bool = Field(..., description="Whether user has active push subscription")
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

    @staticmethod
    def from_orm(obj) -> "UserNotificationPreferencesResponse":
        """Convert SQLAlchemy model to response"""
        return UserNotificationPreferencesResponse(
            id=obj.id,
            user_id=obj.user_id,
            enabled=obj.enabled,
            analysis_completion=obj.analysis_completion,
            system_updates=obj.system_updates,
            has_push_subscription=bool(obj.push_subscription_endpoint),
            created_at=obj.created_at.isoformat() if obj.created_at else "",
            updated_at=obj.updated_at.isoformat() if obj.updated_at else "",
        )


__all__ = [
    "PushSubscriptionKeys",
    "PushSubscriptionData",
    "UserNotificationPreferencesRequest",
    "UserNotificationPreferencesResponse",
]
