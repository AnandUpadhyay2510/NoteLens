"""
Central API router.

Aggregates all sub-routers (auth, documents, syllabus filter) under
the /api/v1 prefix. This single router is mounted by the FastAPI app.
"""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.syllabus_filter import router as filter_router

# Central v1 API router
api_router = APIRouter(prefix="/api/v1")

# Mount sub-routers
api_router.include_router(auth_router)
api_router.include_router(documents_router)
api_router.include_router(filter_router)
