"""Growth Engine API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.growth.learning.engine import PerformanceMetrics
from app.growth.schemas import (
    ContentDraftOut,
    ContentDraftUpdate,
    GenerateDraftRequest,
    GrowthPromptTemplateCreate,
    GrowthPromptTemplateOut,
    GrowthPromptTemplateUpdate,
    LearningRecordOut,
    PageGrowthConfigOut,
    PageGrowthConfigUpdate,
    QuotaStatusOut,
    RecordPerformanceRequest,
    RunDiscoveryRequest,
    TrendTopicOut,
)
from app.growth.service import GrowthService
from app.models.user import User
from app.repositories.repositories import ProjectRepository

router = APIRouter(prefix="/growth", tags=["growth"])


def _get_service(db: Session = Depends(get_db)) -> GrowthService:
    return GrowthService(db)


def _resolve_project_id(page_id: str, user: User, db: Session) -> str:
    from app.models.integration import FacebookPage
    page = db.query(FacebookPage).filter_by(id=page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    project = ProjectRepository(db).get(page.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return project.id


# ---- Config ----

@router.get("/pages/{page_id}/config", response_model=PageGrowthConfigOut)
def get_config(
    page_id: str,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    cfg = svc.get_config(page_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found — create it first")
    return cfg


@router.put("/pages/{page_id}/config", response_model=PageGrowthConfigOut)
def upsert_config(
    page_id: str,
    body: PageGrowthConfigUpdate,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    return svc.upsert_config(page_id, body.model_dump(exclude_none=True))


# ---- Trend Discovery ----

@router.post("/pages/{page_id}/discover", response_model=list[TrendTopicOut])
async def run_discovery(
    page_id: str,
    body: RunDiscoveryRequest,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    return await svc.run_discovery(page_id, body.sources, body.max_per_source)


@router.get("/pages/{page_id}/topics", response_model=list[TrendTopicOut])
def list_topics(
    page_id: str,
    status: str | None = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    return svc.list_topics(page_id, status=status, limit=limit)


@router.delete("/pages/{page_id}/topics")
def clear_topics(
    page_id: str,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    return {"deleted": svc.delete_all_topics(page_id)}


@router.delete("/pages/{page_id}/topics/{topic_id}")
def delete_topic(
    page_id: str,
    topic_id: str,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    try:
        svc.delete_topic(topic_id, page_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": 1}


# ---- Content Drafts ----

@router.post("/pages/{page_id}/drafts/generate", response_model=ContentDraftOut, status_code=status.HTTP_201_CREATED)
async def generate_draft(
    page_id: str,
    body: GenerateDraftRequest,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    project_id = _resolve_project_id(page_id, user, db)
    return await svc.generate_draft(page_id, project_id, body.topic_id, body.content_type)


@router.get("/pages/{page_id}/drafts", response_model=list[ContentDraftOut])
def list_drafts(
    page_id: str,
    status: str | None = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    return svc.list_drafts(page_id, status=status, limit=limit)


@router.delete("/pages/{page_id}/drafts")
def clear_drafts(
    page_id: str,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    return {"deleted": svc.delete_all_drafts(page_id)}


@router.delete("/pages/{page_id}/drafts/{draft_id}")
def delete_draft(
    page_id: str,
    draft_id: str,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    try:
        svc.delete_draft(draft_id, page_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": 1}


@router.get("/pages/{page_id}/drafts/{draft_id}", response_model=ContentDraftOut)
def get_draft(
    page_id: str,
    draft_id: str,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    draft = svc.get_draft(draft_id, page_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.patch("/pages/{page_id}/drafts/{draft_id}", response_model=ContentDraftOut)
def update_draft(
    page_id: str,
    draft_id: str,
    body: ContentDraftUpdate,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    return svc.update_draft(draft_id, page_id, body.model_dump(exclude_none=True))


@router.post("/pages/{page_id}/drafts/{draft_id}/approve", response_model=ContentDraftOut)
def approve_draft(
    page_id: str,
    draft_id: str,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    return svc.approve_draft(draft_id, page_id)


@router.post("/pages/{page_id}/drafts/{draft_id}/reject", response_model=ContentDraftOut)
def reject_draft(
    page_id: str,
    draft_id: str,
    notes: str = "",
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    return svc.reject_draft(draft_id, page_id, notes)


# ---- Learning ----

@router.post("/pages/{page_id}/performance")
def record_performance(
    page_id: str,
    body: RecordPerformanceRequest,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    metrics = PerformanceMetrics(
        reach=body.reach,
        impressions=body.impressions,
        engagement=body.engagement,
        shares=body.shares,
        followers_gained=body.followers_gained,
        watch_time_seconds=body.watch_time_seconds,
        completion_rate=body.completion_rate,
    )
    record = svc.record_performance(page_id, body.draft_id, metrics)
    return {"id": record.id, "performance_score": record.performance_score}


@router.get("/pages/{page_id}/insights")
def get_insights(
    page_id: str,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    return svc.get_insights(page_id)


# ---- Prompt Templates ----

@router.get("/pages/{page_id}/prompts", response_model=list[GrowthPromptTemplateOut])
def list_prompts(
    page_id: str,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    return svc.list_prompts(page_id)


@router.post("/pages/{page_id}/prompts", response_model=GrowthPromptTemplateOut, status_code=status.HTTP_201_CREATED)
def create_prompt(
    page_id: str,
    body: GrowthPromptTemplateCreate,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    return svc.create_prompt(page_id, body.model_dump())


@router.patch("/pages/{page_id}/prompts/{prompt_id}", response_model=GrowthPromptTemplateOut)
def update_prompt(
    page_id: str,
    prompt_id: str,
    body: GrowthPromptTemplateUpdate,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _resolve_project_id(page_id, user, db)
    return svc.update_prompt(prompt_id, page_id, body.model_dump(exclude_none=True))


# ---- Quota ----

@router.get("/quota/{provider}/{model}", response_model=QuotaStatusOut)
def get_quota(
    provider: str,
    model: str,
    user: User = Depends(get_current_user),
    svc: GrowthService = Depends(_get_service),
):
    return svc.get_quota_status(provider, model)
