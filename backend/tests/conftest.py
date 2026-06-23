"""Pytest fixtures: isolated in-memory DB and an authenticated TestClient."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def db_session():
    """A fresh in-memory SQLite session with all tables created."""
    from app.core.database import Base
    from app import models  # noqa: F401

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    """TestClient wired to the in-memory session, scheduler disabled."""
    from app.core.database import get_db
    from app.main import app

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    """Register a user and return Authorization headers."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "tester@example.com", "password": "password123", "name": "Tester"},
    )
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    """Disable the scheduler and effectively disable rate limiting during tests."""
    from app.core.config import settings
    from app.scheduler.manager import scheduler_manager

    monkeypatch.setattr(scheduler_manager, "start", lambda: None)
    monkeypatch.setattr(scheduler_manager, "shutdown", lambda: None)
    monkeypatch.setattr(scheduler_manager, "add_or_update", lambda job: None)
    monkeypatch.setattr(scheduler_manager, "remove", lambda job_id: None)
    monkeypatch.setattr(settings, "rate_limit_anonymous", 1_000_000)
    monkeypatch.setattr(settings, "rate_limit_authenticated", 1_000_000)
