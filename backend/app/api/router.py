"""Aggregate all API routers under the versioned prefix."""

from __future__ import annotations

from fastapi import APIRouter

from app.api import (
    auth,
    dashboard,
    growth,
    integrations,
    jobs,
    posts,
    projects,
    prompts,
    public,
    sources,
    video,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(prompts.router)
api_router.include_router(sources.router)
api_router.include_router(posts.router)
api_router.include_router(jobs.router)
api_router.include_router(integrations.router)
api_router.include_router(dashboard.router)
api_router.include_router(public.router)
api_router.include_router(growth.router)
api_router.include_router(video.router)
