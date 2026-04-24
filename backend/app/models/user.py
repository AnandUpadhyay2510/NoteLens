"""
User ORM model.

Defines the users table with fields for authentication, role-based access
control, and account management.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    """Enumeration of available user roles for access control."""
    STUDENT = "student"
    EDUCATOR = "educator"
    ADMIN = "admin"


class User(Base):
    """
    Represents a registered user of the CodeLens application.

    Attributes:
        id: Unique identifier (UUID).
        email: User's email address (unique, indexed).
        username: Display name (unique).
        hashed_password: Bcrypt-hashed password.
        role: Access level — student, educator, or admin.
        is_active: Whether the account is active.
        created_at: Timestamp of account creation.
        updated_at: Timestamp of last account update.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.STUDENT, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    filter_results = relationship("FilterResult", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role.value})>"
