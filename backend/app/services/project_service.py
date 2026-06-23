"""Project, AI-provider and prompt management services."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, PermissionException
from app.core.security import decrypt_secret, encrypt_secret, mask_secret
from app.models.project import AIProvider, Project, PromptTemplate, SystemPrompt
from app.prompts.defaults import DEFAULT_GLOBAL_PROMPT, DEFAULT_TEMPLATES
from app.repositories.repositories import (
    AIProviderRepository,
    ProjectRepository,
    PromptTemplateRepository,
    SystemPromptRepository,
)
from app.schemas.project import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    ProviderCreate,
    ProviderUpdate,
    ProjectCreate,
    ProjectUpdate,
    SystemPromptCreate,
    SystemPromptUpdate,
)


class ProjectService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)

    def list(self, user_id: str) -> list[Project]:
        return self.projects.list(user_id=user_id)

    def get_owned(self, user_id: str, project_id: str) -> Project:
        project = self.projects.get(project_id)
        if not project:
            raise NotFoundException("Project not found")
        if project.user_id != user_id:
            raise PermissionException("You do not own this project")
        return project

    def create(self, user_id: str, payload: ProjectCreate) -> Project:
        project = self.projects.create(
            user_id=user_id, name=payload.name, description=payload.description
        )
        # Seed a default global system prompt and built-in templates.
        prompts = PromptService(self.db)
        prompts.seed_defaults(project.id)
        self.db.commit()
        self.db.refresh(project)
        return project

    def update(self, user_id: str, project_id: str, payload: ProjectUpdate) -> Project:
        project = self.get_owned(user_id, project_id)
        self.projects.update(project, **payload.model_dump(exclude_none=True))
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete(self, user_id: str, project_id: str) -> None:
        project = self.get_owned(user_id, project_id)
        self.projects.soft_delete(project)
        self.db.commit()


class ProviderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AIProviderRepository(db)

    def list(self, project_id: str) -> list[AIProvider]:
        return self.repo.list(project_id=project_id)

    def get(self, provider_id: str) -> AIProvider:
        provider = self.repo.get(provider_id)
        if not provider:
            raise NotFoundException("Provider not found")
        return provider

    def create(self, project_id: str, payload: ProviderCreate) -> AIProvider:
        data = payload.model_dump(exclude={"api_key"})
        provider = self.repo.create(
            project_id=project_id,
            api_key_encrypted=encrypt_secret(payload.api_key or ""),
            **data,
        )
        self.db.commit()
        self.db.refresh(provider)
        return provider

    def update(self, provider_id: str, payload: ProviderUpdate) -> AIProvider:
        provider = self.get(provider_id)
        data = payload.model_dump(exclude_none=True, exclude={"api_key"})
        if payload.api_key is not None:
            provider.api_key_encrypted = encrypt_secret(payload.api_key)
        self.repo.update(provider, **data)
        self.db.commit()
        self.db.refresh(provider)
        return provider

    def delete(self, provider_id: str) -> None:
        provider = self.get(provider_id)
        self.repo.soft_delete(provider)
        self.db.commit()

    @staticmethod
    def to_out(provider: AIProvider) -> dict:
        return {
            "id": provider.id,
            "project_id": provider.project_id,
            "provider": provider.provider,
            "base_url": provider.base_url,
            "api_key_masked": mask_secret(decrypt_secret(provider.api_key_encrypted or "")),
            "model": provider.model,
            "temperature": provider.temperature,
            "top_p": provider.top_p,
            "max_tokens": provider.max_tokens,
            "timeout_seconds": provider.timeout_seconds,
            "system_prompt": provider.system_prompt,
            "priority": provider.priority,
            "enabled": provider.enabled,
            "grounding_enabled": provider.grounding_enabled,
            "created_at": provider.created_at,
            "updated_at": provider.updated_at,
        }


class PromptService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.system = SystemPromptRepository(db)
        self.templates = PromptTemplateRepository(db)

    def seed_defaults(self, project_id: str) -> None:
        if not self.system.get_active(project_id):
            self.system.create(
                project_id=project_id,
                name="Global Prompt",
                content=DEFAULT_GLOBAL_PROMPT,
                active=True,
            )
        existing = {t.type for t in self.templates.list(project_id=project_id, limit=None)}
        for type_, template in DEFAULT_TEMPLATES.items():
            if type_ not in existing:
                self.templates.create(
                    project_id=project_id,
                    name=type_.replace("_", " ").title(),
                    type=type_,
                    template=template,
                )

    def list_system(self, project_id: str) -> list[SystemPrompt]:
        return self.system.list(project_id=project_id)

    def create_system(self, project_id: str, payload: SystemPromptCreate) -> SystemPrompt:
        if payload.active:
            for sp in self.system.list(project_id=project_id, active=True):
                sp.active = False
        prompt = self.system.create(
            project_id=project_id, name=payload.name, content=payload.content, active=payload.active
        )
        self.db.commit()
        self.db.refresh(prompt)
        return prompt

    def update_system(self, prompt_id: str, payload: SystemPromptUpdate) -> SystemPrompt:
        prompt = self.system.get(prompt_id)
        if not prompt:
            raise NotFoundException("System prompt not found")
        data = payload.model_dump(exclude_none=True)
        if data.get("active") and not prompt.active:
            for sp in self.system.list(project_id=prompt.project_id, active=True):
                if sp.id != prompt.id:
                    sp.active = False
        if "content" in data:
            prompt.version += 1
        self.system.update(prompt, **data)
        self.db.commit()
        self.db.refresh(prompt)
        return prompt

    def delete_system(self, prompt_id: str) -> None:
        prompt = self.system.get(prompt_id)
        if not prompt:
            raise NotFoundException("System prompt not found")
        self.system.soft_delete(prompt)
        self.db.commit()

    def list_templates(self, project_id: str) -> list[PromptTemplate]:
        return self.templates.list(project_id=project_id)

    def create_template(self, project_id: str, payload: PromptTemplateCreate) -> PromptTemplate:
        tmpl = self.templates.create(project_id=project_id, **payload.model_dump())
        self.db.commit()
        self.db.refresh(tmpl)
        return tmpl

    def update_template(self, template_id: str, payload: PromptTemplateUpdate) -> PromptTemplate:
        tmpl = self.templates.get(template_id)
        if not tmpl:
            raise NotFoundException("Template not found")
        data = payload.model_dump(exclude_none=True)
        if "template" in data:
            tmpl.version += 1
        self.templates.update(tmpl, **data)
        self.db.commit()
        self.db.refresh(tmpl)
        return tmpl

    def delete_template(self, template_id: str) -> None:
        tmpl = self.templates.get(template_id)
        if not tmpl:
            raise NotFoundException("Template not found")
        self.templates.soft_delete(tmpl)
        self.db.commit()
