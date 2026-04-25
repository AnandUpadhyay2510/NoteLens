"""
CodeLens Backend — FastAPI Application Entry Point.

Creates and configures the FastAPI application with all routes, middleware,
exception handlers, CORS, and startup/shutdown lifecycle events.
"""

import logging
import sys
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import get_settings
from app.database import create_tables
from app.middleware.logging_middleware import LoggingMiddleware
from app.utils.exceptions import CodeLensBaseError

settings = get_settings()


# ---------------------------------------------------------------------------
# Structured logging configuration
# ---------------------------------------------------------------------------

def configure_logging():
    """Configure structlog for structured JSON logging."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.

    On startup: configure logging, create database tables, ensure upload dir.
    On shutdown: cleanup resources.
    """
    configure_logging()
    logger = structlog.get_logger("codelens.startup")

    logger.info("application_starting", app_name=settings.APP_NAME, version=settings.APP_VERSION)

    # Create database tables (in production, use Alembic migrations instead)
    await create_tables()
    logger.info("database_tables_created")

    # Ensure upload directory exists
    settings.upload_path
    logger.info("upload_directory_ready", path=settings.UPLOAD_DIR)

    logger.info("application_started", debug=settings.DEBUG)

    yield

    logger.info("application_shutting_down")


# ---------------------------------------------------------------------------
# FastAPI application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CodeLens",
    description=(
        "**CodeLens** — A GPT Wrapper with Syllabus Filter. "
        "An intelligent academic study assistant that cross-references "
        "student notes against a course syllabus using LLM-powered analysis "
        "via the OpenRouter API.\n\n"
        "## Features\n"
        "- 📄 Multi-modal input processing (Text, PDF, Audio)\n"
        "- 🎯 Two-stage Syllabus Filter pipeline\n"
        "- 🔐 JWT-based authentication with role-based access\n"
        "- 📊 Document management and processing history\n"
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# CORS — allow all origins in development, restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structured request/response logging
app.add_middleware(LoggingMiddleware)


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(CodeLensBaseError)
async def codelens_error_handler(request: Request, exc: CodeLensBaseError):
    """Convert CodeLensBaseError subclasses into structured JSON responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": type(exc).__name__,
            "message": exc.message,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle unexpected ValueErrors as 400 Bad Request."""
    return JSONResponse(
        status_code=400,
        content={
            "error": "ValueError",
            "message": str(exc),
            "status_code": 400,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for any unhandled exceptions to ensure JSON response."""
    structlog.get_logger("codelens.error").error("unhandled_exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred on the server.",
            "status_code": 500,
        },
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

# Mount the versioned API router
app.include_router(api_router)


@app.get(
    "/health",
    tags=["Health"],
    summary="Service health check",
    description="Returns the current health status of the application.",
)
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# ---------------------------------------------------------------------------
# Development server entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
