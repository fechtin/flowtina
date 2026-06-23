"""Layered prompt engine.

Merges Global → Project → Content-Type prompts, injects runtime variables and
renders the final prompt with Jinja2. Missing variables resolve to sensible
defaults so rendering never crashes (per PROMPT_ENGINE.md absolute rules).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from jinja2 import Environment, StrictUndefined, Undefined

# Default values for every supported runtime variable.
DEFAULT_VARIABLES: dict[str, str] = {
    "date": "",
    "time": "",
    "language": "English",
    "topic": "",
    "source_content": "",
    "hashtags": "",
    "style": "professional",
    "persona": "",
    "tone": "professional",
    "cta": "",
    "brand_name": "",
    "audience": "general",
    "max_words": "300",
    "emoji_level": "low",
}

# Curly-brace ``{{var}}`` syntax with optional spaces -> normalized for Jinja2.
_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


class _SafeUndefined(Undefined):
    """Render unknown variables as empty strings instead of raising."""

    def __str__(self) -> str:  # noqa: D401
        return ""


class PromptEngine:
    """Render prompts from layered templates and variables."""

    def __init__(self, strict: bool = False) -> None:
        self.env = Environment(
            undefined=StrictUndefined if strict else _SafeUndefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @staticmethod
    def _runtime_defaults() -> dict[str, str]:
        now = datetime.now(timezone.utc)
        values = dict(DEFAULT_VARIABLES)
        values["date"] = now.strftime("%Y-%m-%d")
        values["time"] = now.strftime("%H:%M")
        return values

    def render(self, template: str, variables: dict[str, str] | None = None) -> str:
        """Render a single template string with merged defaults + overrides."""
        merged = self._runtime_defaults()
        if variables:
            merged.update({k: ("" if v is None else str(v)) for k, v in variables.items()})
        normalized = _VAR_RE.sub(r"{{ \1 }}", template or "")
        return self.env.from_string(normalized).render(**merged).strip()

    def build_final_prompt(
        self,
        *,
        global_prompt: str | None,
        project_prompt: str | None,
        content_prompt: str,
        variables: dict[str, str] | None = None,
    ) -> str:
        """Merge layers (lower layers last) then render the result."""
        layers = [global_prompt, project_prompt, content_prompt]
        merged_template = "\n\n".join(layer.strip() for layer in layers if layer and layer.strip())
        return self.render(merged_template, variables)

    @staticmethod
    def extract_variables(template: str) -> list[str]:
        """Return the list of ``{{variable}}`` names used by a template."""
        return sorted(set(_VAR_RE.findall(template or "")))


prompt_engine = PromptEngine()
