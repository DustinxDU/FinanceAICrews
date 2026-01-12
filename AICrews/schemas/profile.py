"""
Profile Schemas - User profile management

All schemas use Pydantic v2 with explicit validation.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict

from AICrews.schemas.common import BaseSchema


# ============================================
# Request Schemas
# ============================================

class ProfileUpdateRequest(BaseSchema):
    """
    Update user profile request

    Sensitive change rules:
    - full_name, avatar_url: NO password required
    - email, password, phone_number: REQUIRES current_password
    """
    # Non-sensitive fields (can update without password)
    full_name: Optional[str] = Field(None, max_length=200, description="Full name")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Avatar URL")

    # Sensitive fields (require current_password)
    email: Optional[EmailStr] = Field(None, description="New email address")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")

    # Password change
    current_password: Optional[str] = Field(None, min_length=8, max_length=100, description="Current password (required for sensitive changes)")
    new_password: Optional[str] = Field(None, min_length=8, max_length=100, description="New password (optional)")

    @field_validator('avatar_url')
    @classmethod
    def validate_avatar_url(cls, v: Optional[str]) -> Optional[str]:
        if v:
            # Prevent malicious URLs
            v_lower = v.lower()
            if not (v_lower.startswith('http://') or v_lower.startswith('https://')):
                raise ValueError("Avatar URL must start with http:// or https://")
            if any(v_lower.startswith(prefix) for prefix in ['javascript:', 'data:', 'file:']):
                raise ValueError("Avatar URL contains invalid protocol")
        return v

    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v:
            # Check format with regex
            import re
            if not re.match(r'^\+?[\d\s\-]{7,20}$', v):
                raise ValueError("Phone number must be 7-20 characters with digits, spaces, hyphens, and optional leading +")
            # Ensure at least 7 actual digits
            digits_only = re.sub(r'[^\d]', '', v)
            if len(digits_only) < 7:
                raise ValueError("Phone number must contain at least 7 digits")
        return v

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: Optional[str]) -> Optional[str]:
        if v:
            if len(v) < 8:
                raise ValueError("Password must be at least 8 characters")

            # Check password strength criteria
            has_upper = any(c.isupper() for c in v)
            has_lower = any(c.islower() for c in v)
            has_digit = any(c.isdigit() for c in v)
            has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

            criteria_met = sum([has_upper, has_lower, has_digit, has_special])
            if criteria_met < 3:
                raise ValueError("Password must contain at least 3 of: uppercase, lowercase, digit, special character")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "John Doe",
                "current_password": "oldpassword123"
            }
        }
    )


class EmailVerificationRequest(BaseSchema):
    """Verify email change with token"""
    token: str = Field(..., min_length=32, max_length=100, description="Verification token")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
            }
        }
    )


# ============================================
# Response Schemas
# ============================================

class ProfileResponse(BaseSchema):
    """
    User profile response

    Extended from base UserResponse with additional profile fields
    """
    id: int = Field(..., description="User ID")
    email: EmailStr = Field(..., description="Email address")
    username: str = Field(..., description="Username")
    full_name: Optional[str] = Field(None, description="Full name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    phone_number: Optional[str] = Field(None, description="Phone number")

    # Email verification state
    email_verified: bool = Field(False, description="Email verification status")
    pending_email: Optional[EmailStr] = Field(None, description="Pending email (awaiting verification)")

    # Account metadata
    subscription_level: str = Field("free", description="Subscription level")
    is_active: bool = Field(..., description="Account active status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Security indicators
    last_password_change: Optional[datetime] = Field(None, description="Last password change timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 123,
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "avatar_url": "https://example.com/avatar.jpg",
                "phone_number": "+1-555-123-4567",
                "email_verified": True,
                "pending_email": None,
                "subscription_level": "pro",
                "is_active": True,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2026-01-02T10:30:00Z",
                "last_password_change": "2025-12-01T00:00:00Z"
            }
        }
    )


class EmailVerificationResponse(BaseSchema):
    """Email verification result"""
    success: bool = Field(..., description="Verification success")
    email: EmailStr = Field(..., description="New email address")
    message: str = Field(..., description="Status message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "email": "newemail@example.com",
                "message": "Email successfully verified and updated"
            }
        }
    )


# ============================================
# API Endpoint Contracts
# ============================================

"""
Profile API Endpoints:

1. GET /api/v1/profile
   - Auth: Required
   - Response: ProfileResponse
   - Description: Get current user's profile

2. PUT /api/v1/profile
   - Auth: Required
   - Request: ProfileUpdateRequest
   - Response: ProfileResponse
   - Description: Update user profile
   - Validation:
     - If updating email/password/phone: current_password required
     - Email change triggers verification flow (sets pending_email)
     - Password change updates last_password_change timestamp

3. POST /api/v1/profile/verify-email
   - Auth: Required
   - Request: EmailVerificationRequest
   - Response: EmailVerificationResponse
   - Description: Verify pending email change with token
"""
