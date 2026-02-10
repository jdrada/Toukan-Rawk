"""FastAPI application factory with middleware, exception handlers, and lifespan."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.exceptions import RawkException
from app.repositories.database import dispose_engine, init_db
from app.routers import memories, processing, upload

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize resources on startup, clean up on shutdown."""
    settings = get_settings()
    if settings.environment == "development":
        await init_db(settings)
        logger.info("Database tables created (development mode)")
    yield
    await dispose_engine()
    logger.info("Database engine disposed")


app = FastAPI(
    title="RAWK Backend",
    description="Memory processing system with AI",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RawkException)
async def rawk_exception_handler(request: Request, exc: RawkException) -> JSONResponse:
    """Map all RawkException subclasses to their status_code."""
    logger.error(
        "RawkException: %s - %s",
        type(exc).__name__,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_type": type(exc).__name__},
    )


# Routers
app.include_router(upload.router)
app.include_router(memories.router)
app.include_router(processing.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "rawk-backend"}


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "service": "RAWK Backend",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "upload": "/upload",
            "memories": "/memories",
        },
    }
