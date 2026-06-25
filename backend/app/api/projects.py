"""Project and AI-provider endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_project
from app.core.database import get_db
from app.core.security import decrypt_secret
from app.models.project import Project
from app.models.user import User
from app.repositories.repositories import UserSettingsRepository
from app.schemas.common import ok
from app.schemas.project import (
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    ProviderCreate,
    ProviderModelsRequest,
    ProviderTestRequest,
    ProviderUpdate,
)
from app.services.ai_service import AIService
from app.services.project_service import ProjectService, ProviderService

router = APIRouter(tags=["projects"])


@router.get("/projects")
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = ProjectService(db).list(user.id)
    return ok([ProjectOut.model_validate(p).model_dump() for p in items])


@router.post("/projects")
def create_project(
    payload: ProjectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    project = ProjectService(db).create(user.id, payload)
    return ok(ProjectOut.model_validate(project).model_dump(), "Project created")


@router.get("/projects/{project_id}")
def get_project(project: Project = Depends(get_owned_project)):
    return ok(ProjectOut.model_validate(project).model_dump())


@router.put("/projects/{project_id}")
def update_project(
    payload: ProjectUpdate,
    project: Project = Depends(get_owned_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = ProjectService(db).update(user.id, project.id, payload)
    return ok(ProjectOut.model_validate(updated).model_dump(), "Project updated")


@router.delete("/projects/{project_id}")
def delete_project(
    project: Project = Depends(get_owned_project),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ProjectService(db).delete(user.id, project.id)
    return ok(message="Project deleted")


# --- Providers (scoped to a project) ---


@router.get("/projects/{project_id}/providers")
def list_providers(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    svc = ProviderService(db)
    return ok([svc.to_out(p) for p in svc.list(project.id)])


@router.post("/projects/{project_id}/providers")
def create_provider(
    payload: ProviderCreate,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    svc = ProviderService(db)
    provider = svc.create(project.id, payload)
    return ok(svc.to_out(provider), "Provider created")


@router.put("/providers/{provider_id}")
def update_provider(
    provider_id: str,
    payload: ProviderUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = ProviderService(db)
    provider = svc.update(provider_id, payload)
    return ok(svc.to_out(provider), "Provider updated")


@router.delete("/providers/{provider_id}")
def delete_provider(
    provider_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    ProviderService(db).delete(provider_id)
    return ok(message="Provider deleted")


def _saved_default_key(db: Session, user_id: str, provider: str) -> str | None:
    """Decrypt the user's saved global default API key when it matches ``provider``.

    The stored key is never returned to the form, so a "Test"/"Fetch models" call
    with a blank field would otherwise have no credential. Fall back to the saved
    key for the matching provider so these actions work without retyping it.
    """
    prefs = UserSettingsRepository(db).get_by(user_id=user_id)
    if prefs and prefs.default_provider == provider and prefs.default_api_key_encrypted:
        return decrypt_secret(prefs.default_api_key_encrypted) or None
    return None


@router.post("/providers/test")
async def test_provider(
    payload: ProviderTestRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.api_key:
        payload.api_key = _saved_default_key(db, user.id, payload.provider)
    result = await AIService.test_connection(payload)
    return ok(result.model_dump())


@router.post("/providers/models")
async def list_provider_models(
    payload: ProviderModelsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.api_key:
        payload.api_key = _saved_default_key(db, user.id, payload.provider)
    models = await AIService.list_models(payload)
    return ok(models)
