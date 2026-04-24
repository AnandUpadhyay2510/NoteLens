"""
Authentication service.

Handles password hashing, JWT token creation and verification, and provides
FastAPI dependencies for extracting the current authenticated user from
incoming requests.
"""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User, UserRole
from app.utils.exceptions import (
    InactiveUserError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
)

import structlog

logger = structlog.get_logger(__name__)

# Direct bcrypt hashing for Python 3.14 compatibility

# HTTP Bearer token security scheme for Swagger UI
security = HTTPBearer()

settings = get_settings()


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    Args:
        plain_password: The user's plain-text password.

    Returns:
        The bcrypt-hashed password string.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.

    Args:
        plain_password: The plain-text password to check.
        hashed_password: The stored bcrypt hash.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT utilities
# ---------------------------------------------------------------------------

def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        data: Payload data to encode (must include 'sub' with user ID).
        expires_delta: Optional custom expiry duration. Falls back to
                       ACCESS_TOKEN_EXPIRE_MINUTES from settings.

    Returns:
        The encoded JWT string.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    logger.debug("jwt_token_created", user_id=data.get("sub"), expires=expire.isoformat())
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.

    Args:
        token: The JWT string to decode.

    Returns:
        The decoded payload dictionary.

    Raises:
        InvalidCredentialsError: If the token is invalid, expired, or malformed.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.warning("jwt_decode_failed", error=str(e))
        raise InvalidCredentialsError()


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency: Extract and validate the current user from the JWT.

    This dependency reads the Authorization header, decodes the JWT,
    looks up the user in the database, and verifies that the account is active.

    Args:
        credentials: The HTTP Bearer credentials from the Authorization header.
        db: The database session (injected).

    Returns:
        The authenticated User ORM instance.

    Raises:
        InvalidCredentialsError: If the token is invalid or the user doesn't exist.
        InactiveUserError: If the user's account is deactivated.
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    user_id: str | None = payload.get("sub")
    if user_id is None:
        logger.warning("jwt_missing_subject")
        raise InvalidCredentialsError()

    # Look up the user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("jwt_user_not_found", user_id=user_id)
        raise InvalidCredentialsError()

    if not user.is_active:
        logger.warning("jwt_inactive_user", user_id=user_id)
        raise InactiveUserError()

    return user


def require_role(*roles: UserRole):
    """
    Factory for a FastAPI dependency that enforces role-based access control.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role(UserRole.ADMIN))])

    Args:
        *roles: One or more UserRole values that are permitted.

    Returns:
        A FastAPI dependency function.
    """

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            logger.warning(
                "insufficient_permissions",
                user_id=current_user.id,
                user_role=current_user.role.value,
                required_roles=[r.value for r in roles],
            )
            raise InsufficientPermissionsError(
                required_role=", ".join(r.value for r in roles)
            )
        return current_user

    return role_checker
