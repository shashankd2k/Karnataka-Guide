"""
Data transfer objects and schemas for administrator authentication and authorization.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.infrastructure.db.models.admin import AdminRole


class LoginRequest(BaseModel):
    """Admin login request schema."""
    username: str = Field(..., min_length=3, max_length=50, description="Admin username or email")
    password: str = Field(..., min_length=6, max_length=128, description="Plaintext password")


class TokenResponse(BaseModel):
    """JWT token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token lifetime in seconds")


class RefreshRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str = Field(..., min_length=10, description="Valid signed refresh token")


class LogoutRequest(BaseModel):
    """Logout request schema."""
    refresh_token: Optional[str] = Field(default=None, description="Optional refresh token to revoke")


class AdminResponse(BaseModel):
    """Safe administrator response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    role: AdminRole
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
