"""
Preferences Schemas - 用户偏好设置
"""

from __future__ import annotations

from typing import Optional, Literal

from pydantic import Field, ConfigDict

from AICrews.schemas.common import BaseSchema

ThemeOption = Literal["light", "dark", "system"]


class UserPreferencesResponse(BaseSchema):
    """用户偏好设置响应"""

    theme: ThemeOption = Field("system", description="主题: light/dark/system")
    locale: str = Field("en", description="语言")
    timezone: str = Field("UTC", description="时区")

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )


class UserPreferencesUpdate(BaseSchema):
    """用户偏好设置更新请求"""

    theme: Optional[ThemeOption] = Field(None, description="主题: light/dark/system")
    locale: Optional[str] = Field(None, description="语言")
    timezone: Optional[str] = Field(None, description="时区")

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )


__all__ = ["UserPreferencesResponse", "UserPreferencesUpdate"]
