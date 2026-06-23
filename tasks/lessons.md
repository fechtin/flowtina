# Lessons / Patterns

## Environment
- System Python is 3.9 but the project targets 3.12 (PEP 604 `X | None`, `list[T]`).
  The venv lives at `backend/venv` (created with `python3.12`). The IDE's
  diagnostics use system 3.9 and will falsely flag modules/union syntax — ignore;
  always run via `backend/venv/bin/python`.

## Tooling gotcha
- A stray `</content>` line was appended to every file written via the Write tool
  in this session. Fixed by a one-off script stripping a trailing `</content>`
  line across `backend/ frontend/ config/ scripts/ deploy/ tasks/`. If files are
  written again and behave oddly, re-check for this trailing tag.

## Architecture decisions
- OpenAI-compatible providers (OpenAI/DeepSeek/OpenRouter/Ollama/LM Studio/vLLM/
  custom) share one base class; only Gemini and Claude need bespoke clients.
- The scheduler runs as a **separate process** (`app.scheduler.runner`) in
  production so web workers stay stateless; gunicorn sets `SCHEDULER_ENABLED=false`.
- Rate-limit middleware keeps in-memory state on the app singleton, which bleeds
  across tests — the test suite raises the limits via an autouse fixture.

## Verified
- `alembic upgrade head` → 27 app tables. App boots, scheduler boots,
  job scheduling persists to `apscheduler_jobs`. `pytest` 28 tests / 80% coverage.
  `ruff check app` clean.
