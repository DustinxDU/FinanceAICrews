"""
Security Schemas - 2FA, sessions, and security settings
"""

from typing import Optional, List
from datetime import datetime
from pydantic import Field, ConfigDict, field_validator

from AICrews.schemas.common import BaseSchema


# ============================================
# Request Schemas
# ============================================

class Setup2FARequest(BaseSchema):
    """Start 2FA setup (TOTP)"""
    method: str = Field("totp", description="2FA method (totp or sms)")

    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        if v not in ['totp', 'sms']:
            raise ValueError("Method must be 'totp' or 'sms'")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "method": "totp"
            }
        }
    )


class Verify2FASetupRequest(BaseSchema):
    """Verify 2FA setup with code"""
    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Code must be 6 digits")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "123456"
            }
        }
    )


class Disable2FARequest(BaseSchema):
    """Disable 2FA (requires password + 2FA code)"""
    password: str = Field(..., min_length=8, description="Current password")
    code: str = Field(..., min_length=6, max_length=6, description="Current 2FA code")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "password": "mypassword123",
                "code": "123456"
            }
        }
    )


class RevokeSessionRequest(BaseSchema):
    """Revoke a specific session"""
    session_id: int = Field(..., description="Session ID to revoke")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": 42
            }
        }
    )


# ============================================
# Response Schemas
# ============================================

class TwoFactorSetupResponse(BaseSchema):
    """2FA setup response (QR code + secret)"""
    secret: str = Field(..., description="TOTP secret key")
    qr_code_url: str = Field(..., description="Data URL for QR code image")
    backup_codes: List[str] = Field(..., description="Recovery codes (save these!)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "secret": "JBSWY3DPEHPK3PXP",
                "qr_code_url": "data:image/png;base64,iVBORw0KGgoAAAANS...",
                "backup_codes": [
                    "1234-5678",
                    "9012-3456",
                    "7890-1234"
                ]
            }
        }
    )


class TwoFactorStatusResponse(BaseSchema):
    """2FA status"""
    enabled: bool = Field(..., description="2FA enabled status")
    method: Optional[str] = Field(None, description="2FA method (totp/sms)")
    phone_last_4: Optional[str] = Field(None, description="Last 4 digits of phone (for SMS)")
    backup_codes_remaining: int = Field(0, description="Unused backup codes count")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "enabled": True,
                "method": "totp",
                "phone_last_4": None,
                "backup_codes_remaining": 8
            }
        }
    )


class LoginSessionResponse(BaseSchema):
    """Active login session"""
    id: int = Field(..., description="Session ID")
    device_info: str = Field(..., description="Device description (browser, OS)")
    ip_address: str = Field(..., description="IP address")
    location: Optional[str] = Field(None, description="Geographic location (city, country)")
    is_current: bool = Field(..., description="Is this the current session")
    created_at: datetime = Field(..., description="Session creation timestamp")
    last_active: datetime = Field(..., description="Last activity timestamp")
    expires_at: Optional[datetime] = Field(None, description="Session expiration")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 42,
                "device_info": "Chrome 120 on macOS",
                "ip_address": "192.168.1.100",
                "location": "San Francisco, CA, US",
                "is_current": True,
                "created_at": "2026-01-02T10:00:00Z",
                "last_active": "2026-01-02T10:30:00Z",
                "expires_at": "2026-01-09T10:00:00Z"
            }
        }
    )


class SessionsResponse(BaseSchema):
    """List of active sessions"""
    sessions: List[LoginSessionResponse] = Field(..., description="Active sessions")
    total: int = Field(..., description="Total session count")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sessions": [],  # LoginSessionResponse examples
                "total": 3
            }
        }
    )


class LoginHistoryItem(BaseSchema):
    """Single login history record"""
    id: int = Field(..., description="History record ID")
    timestamp: datetime = Field(..., description="Login timestamp")
    device_info: str = Field(..., description="Device description")
    ip_address: str = Field(..., description="IP address")
    location: Optional[str] = Field(None, description="Geographic location")
    status: str = Field(..., description="Login status (success, failed, suspicious)")
    failure_reason: Optional[str] = Field(None, description="Failure reason (if failed)")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1001,
                "timestamp": "2026-01-02T10:00:00Z",
                "device_info": "Chrome 120 on macOS",
                "ip_address": "192.168.1.100",
                "location": "San Francisco, CA, US",
                "status": "success",
                "failure_reason": None
            }
        }
    )


class LoginHistoryResponse(BaseSchema):
    """Login history"""
    history: List[LoginHistoryItem] = Field(..., description="Login history items")
    total: int = Field(..., description="Total history count")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "history": [],  # LoginHistoryItem examples
                "total": 47
            }
        }
    )


__all__ = [
    # Request schemas
    "Setup2FARequest",
    "Verify2FASetupRequest",
    "Disable2FARequest",
    "RevokeSessionRequest",
    # Response schemas
    "TwoFactorSetupResponse",
    "TwoFactorStatusResponse",
    "LoginSessionResponse",
    "SessionsResponse",
    "LoginHistoryItem",
    "LoginHistoryResponse",
]
