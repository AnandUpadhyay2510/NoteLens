"""
ORM models package.

Exports all SQLAlchemy models so they are registered with the Base metadata
when the application starts. This ensures Alembic and create_tables() can
discover all tables.
"""

from app.models.user import User
from app.models.document import Document
from app.models.filter_result import FilterResult

__all__ = ["User", "Document", "FilterResult"]
