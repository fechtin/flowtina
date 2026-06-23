"""Project, AI provider and prompt schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel, TimestampedSchema

# --- Projects ---


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    description: str | None = None
    active: bool | None = None


class ProjectOut(TimestampedSchema):
    user_id: str
    name: str
    description: str | None = None
    active: bool


# --- AI providers ---

PROVIDER_VALUES = {
    "openai", "gemini", "claude", "openrouter", "deepseek",
    "ollama", "lmstudio", "vllm", "custom",
}


class ProviderCreate(BaseModel):
    provider: str = Field(default="openai")
    base_url: str | None = None
    api_key: str | None = None
    model: str = Field(min_length=1, max_length=120)
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 1024
    timeout_seconds: int = 60
    system_prompt: str | None = None
    priority: int = 0
    enabled: bool = True


class ProviderUpdate(BaseModel):
    provider: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    timeout_seconds: int | None = None
    system_prompt: str | None = None
    priority: int | None = None
    enabled: bool | None = None


class ProviderOut(TimestampedSchema):
    project_id: str
    provider: str
    base_url: str | None = None
    api_key_masked: str = ""
    model: str
    temperature: float
    top_p: float
    max_tokens: int
    timeout_seconds: int
    system_prompt: str | None = None
    priority: int
    enabled: bool


class ProviderTestRequest(BaseModel):
    provider: str = "openai"
    base_url: str | None = None
    api_key: str | None = None
    model: str = "gpt-4o-mini"
    prompt: str = "Reply with the single word: OK"


class ProviderTestResult(BaseModel):
    success: bool
    latency_ms: int = 0
    output: str | None = None
    error: str | None = None


# --- Prompts ---


class SystemPromptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    content: str
    active: bool = True


class SystemPromptOut(TimestampedSchema):
    project_id: str
    name: str
    content: str
    version: int
    active: bool


class PromptTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    type: str = "short_post"
    template: str
    language: str = "en"
    active: bool = True


class PromptTemplateUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    template: str | None = None
    language: str | None = None
    active: bool | None = None


class PromptTemplateOut(TimestampedSchema):
    project_id: str
    name: str
    type: str
    template: str
    language: str
    version: int
    active: bool


class PromptRenderRequest(BaseModel):
    template: str
    variables: dict[str, str] = {}


class PromptRenderResult(ORMModel):
    rendered: str
