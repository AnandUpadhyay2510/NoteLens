"""
Authentication API routes.

Provides endpoints for user registration, login (JWT issuance),
and retrieving the current user's profile.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    MessageResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.config import get_settings
from app.utils.exceptions import InvalidCredentialsError

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email, username, password, and role.",
)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Register a new user account.

    Validates that the email and username are not already taken,
    hashes the password, creates the user record, and returns
    the user profile.
    """
    # Check for existing email
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{request.email}' is already registered.",
        )

    # Check for existing username
    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{request.username}' is already taken.",
        )

    # Create user - explicitly set role to STUDENT for all public registrations
    # to prevent privilege escalation vulnerabilities.
    from app.models.user import UserRole
    user = User(
        email=request.email,
        username=request.username,
        hashed_password=hash_password(request.password),
        role=UserRole.STUDENT,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    logger.info("user_registered", user_id=user.id, email=user.email, role=user.role.value)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT token",
    description="Authenticate with email and password to receive a JWT access token.",
)
async def login(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate a user and return a JWT access token.

    Looks up the user by email, verifies the password, checks that
    the account is active, and issues a signed JWT.
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        logger.warning("login_failed", email=request.email)
        raise InvalidCredentialsError()

    if not user.is_active:
        from app.utils.exceptions import InactiveUserError
        raise InactiveUserError()

    # Create JWT token
    access_token = create_access_token(data={"sub": user.id})

    logger.info("user_logged_in", user_id=user.id, email=user.email)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Retrieve the profile of the currently authenticated user.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the current authenticated user's profile."""
    return UserResponse.model_validate(current_user)
