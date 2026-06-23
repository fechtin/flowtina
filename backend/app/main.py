"""Flowtina FastAPI application factory and entrypoint.

Run for development:  ``uvicorn app.main:app --reload``
Run for production:   ``gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 1 --threads 4``
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.core.logger import get_logger, setup_logging
from app.middlewares.middleware import RateLimitMiddleware, RequestLoggingMiddleware

setup_logging()
log = get_logger("system")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Startup/shutdown hooks: init DB and start the scheduler."""
    log.info(f"Starting {settings.app_name} ({settings.app_env})")
    if settings.is_sqlite:
        init_db()  # dev/bootstrap; production uses Alembic but this is idempotent
    from app.scheduler.manager import scheduler_manager

    scheduler_manager.start()
    try:
        yield
    finally:
        scheduler_manager.shutdown()
        log.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.app_name} API",
        version="1.0.0",
        description="AI Content Automation Platform",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(app)

    from app.api.router import api_router

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/", tags=["root"])
    def root() -> dict:
        return {"success": True, "data": {"app": settings.app_name, "version": "1.0.0"}}

    return app


app = create_app()
