#!/usr/bin/env python3
"""Migrate seeded global prompts to the current default.

Older installs seeded a Flowtina-specific global prompt that also predates the
"plain text only / no Markdown" guidance. This refreshes any global prompt whose
content is *verbatim* one of the known old defaults, leaving user-customised
prompts untouched. Idempotent and safe to re-run.

Usage (on the server):
    cd /opt/flowtina/backend
    /opt/flowtina/venv/bin/python /opt/flowtina/scripts/update_global_prompts.py          # dry run
    /opt/flowtina/venv/bin/python /opt/flowtina/scripts/update_global_prompts.py --apply   # write
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the backend package importable regardless of the current directory.
# Layout (repo and /opt/flowtina alike): <root>/scripts/ next to <root>/backend/.
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if _BACKEND.is_dir() and str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.core.database import SessionLocal
from app.models.project import SystemPrompt
from app.prompts.defaults import DEFAULT_GLOBAL_PROMPT

# Exact historical defaults that should be refreshed. Add prior versions here if
# the default ever changes again so the migration stays complete.
OLD_DEFAULTS: tuple[str, ...] = (
    "You are an expert social media content writer for the Flowtina platform. "
    "Always write clear, engaging, original content. Follow safety and brand "
    "guidelines. Never invent facts. Respect the requested language and length.",
)


def main() -> int:
    apply = "--apply" in sys.argv[1:]
    db = SessionLocal()
    try:
        rows = (
            db.query(SystemPrompt)
            .filter(
                SystemPrompt.deleted_at.is_(None),
                SystemPrompt.content.in_(OLD_DEFAULTS),
            )
            .all()
        )
        if not rows:
            print("No old-default global prompts found; nothing to update.")
            return 0

        print(f"Found {len(rows)} global prompt(s) matching an old default:")
        for row in rows:
            print(f"  - project={row.project_id} name={row.name!r} active={row.active}")
            if apply:
                row.content = DEFAULT_GLOBAL_PROMPT
                row.version += 1

        if apply:
            db.commit()
            print(f"Updated {len(rows)} prompt(s) to the current default.")
        else:
            print("Dry run — re-run with --apply to write these changes.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
