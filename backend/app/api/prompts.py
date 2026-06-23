"""Prompt template and system-prompt endpoints, plus live render."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_project
from app.core.database import get_db
from app.models.project import Project
from app.models.user import User
from app.prompts.engine import prompt_engine
from app.schemas.common import ok
from app.schemas.project import (
    PromptRenderRequest,
    PromptTemplateCreate,
    PromptTemplateOut,
    PromptTemplateUpdate,
    SystemPromptCreate,
    SystemPromptOut,
    SystemPromptUpdate,
)
from app.services.project_service import PromptService

router = APIRouter(tags=["prompts"])


@router.get("/projects/{project_id}/system-prompts")
def list_system_prompts(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    items = PromptService(db).list_system(project.id)
    return ok([SystemPromptOut.model_validate(p).model_dump() for p in items])


@router.post("/projects/{project_id}/system-prompts")
def create_system_prompt(
    payload: SystemPromptCreate,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    prompt = PromptService(db).create_system(project.id, payload)
    return ok(SystemPromptOut.model_validate(prompt).model_dump(), "System prompt created")


@router.put("/system-prompts/{prompt_id}")
def update_system_prompt(
    prompt_id: str,
    payload: SystemPromptUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prompt = PromptService(db).update_system(prompt_id, payload)
    return ok(SystemPromptOut.model_validate(prompt).model_dump(), "System prompt updated")


@router.delete("/system-prompts/{prompt_id}")
def delete_system_prompt(
    prompt_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    PromptService(db).delete_system(prompt_id)
    return ok(message="System prompt deleted")


@router.get("/projects/{project_id}/prompts")
def list_templates(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    items = PromptService(db).list_templates(project.id)
    return ok([PromptTemplateOut.model_validate(p).model_dump() for p in items])


@router.post("/projects/{project_id}/prompts")
def create_template(
    payload: PromptTemplateCreate,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    tmpl = PromptService(db).create_template(project.id, payload)
    return ok(PromptTemplateOut.model_validate(tmpl).model_dump(), "Template created")


@router.put("/prompts/{template_id}")
def update_template(
    template_id: str,
    payload: PromptTemplateUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tmpl = PromptService(db).update_template(template_id, payload)
    return ok(PromptTemplateOut.model_validate(tmpl).model_dump(), "Template updated")


@router.delete("/prompts/{template_id}")
def delete_template(
    template_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    PromptService(db).delete_template(template_id)
    return ok(message="Template deleted")


@router.post("/prompts/render")
def render_prompt(payload: PromptRenderRequest, user: User = Depends(get_current_user)):
    rendered = prompt_engine.render(payload.template, payload.variables)
    return ok({"rendered": rendered})
