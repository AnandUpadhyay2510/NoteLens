"""
Authentication request/response schemas.

Defines the Pydantic models for user registration, login, JWT tokens,
and user profile responses.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class UserRegisterRequest(BaseModel):
    """Schema for new user registration."""

    email: EmailStr = Field(
        ...,
        description="User's email address. Must be unique.",
        examples=["student@university.edu"],
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Display name. Must be unique, 3-100 characters.",
        examples=["john_doe"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password. Minimum 8 characters.",
        examples=["SecurePass123!"],
    )


class UserLoginRequest(BaseModel):
    """Schema for user login."""

    email: EmailStr = Field(
        ...,
        description="Registered email address.",
        examples=["student@university.edu"],
    )
    password: str = Field(
        ...,
        description="Account password.",
        examples=["SecurePass123!"],
    )


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    """Schema for JWT token response after successful authentication."""

    access_token: str = Field(
        ...,
        description="JWT access token for authenticating API requests.",
    )
    token_type: str = Field(
        default="bearer",
        description="Token type — always 'bearer'.",
    )
    expires_in: int = Field(
        ...,
        description="Token expiry duration in seconds.",
    )


class UserResponse(BaseModel):
    """Schema for user profile information."""

    id: str = Field(..., description="Unique user identifier (UUID).")
    email: str = Field(..., description="User's email address.")
    username: str = Field(..., description="User's display name.")
    role: UserRole = Field(..., description="User's access role.")
    is_active: bool = Field(..., description="Whether the account is active.")
    created_at: datetime = Field(..., description="Account creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Generic message response for simple operations."""

    message: str = Field(..., description="Human-readable result message.")
    success: bool = Field(default=True, description="Whether the operation succeeded.")
