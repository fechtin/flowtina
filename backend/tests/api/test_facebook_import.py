"""Tests for one-token Facebook page import (Graph /me/accounts mocked)."""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationException
from app.repositories.repositories import (
    FacebookPageRepository,
    ProjectRepository,
    UserRepository,
)
from app.services.facebook_service import FacebookService

ACCOUNTS = {
    "data": [
        {"id": "100", "name": "Page A", "access_token": "tokA"},
        {"id": "200", "name": "Page B", "access_token": "tokB"},
    ]
}


@pytest.fixture
def project(db_session):
    user = UserRepository(db_session).create(email="fb@x.com", password_hash="x", name="FB")
    project = ProjectRepository(db_session).create(user_id=user.id, name="P")
    db_session.commit()
    return project


async def test_import_discovers_pages(db_session, project, monkeypatch):
    async def fake_get(url, params):
        return ACCOUNTS if "me/accounts" in url else {}

    monkeypatch.setattr("app.services.facebook_service.FacebookService._get", staticmethod(fake_get))
    pages = await FacebookService(db_session).import_pages(project.id, token="user-token")
    assert {p.page_id for p in pages} == {"100", "200"}
    assert {p.page_name for p in pages} == {"Page A", "Page B"}
    assert FacebookPageRepository(db_session).count(project_id=project.id) == 2


async def test_import_is_idempotent(db_session, project, monkeypatch):
    async def fake_get(url, params):
        return ACCOUNTS

    monkeypatch.setattr("app.services.facebook_service.FacebookService._get", staticmethod(fake_get))
    svc = FacebookService(db_session)
    await svc.import_pages(project.id, token="t")
    await svc.import_pages(project.id, token="t")  # second run updates, no duplicates
    assert FacebookPageRepository(db_session).count(project_id=project.id) == 2


async def test_import_prunes_pages_no_longer_returned(db_session, project, monkeypatch):
    accounts = {"data": list(ACCOUNTS["data"])}

    async def fake_get(url, params):
        return accounts

    monkeypatch.setattr("app.services.facebook_service.FacebookService._get", staticmethod(fake_get))
    svc = FacebookService(db_session)
    await svc.import_pages(project.id, token="t")
    assert FacebookPageRepository(db_session).count(project_id=project.id) == 2

    # Page B no longer assigned to the token → should be pruned on the next sync.
    accounts["data"] = [{"id": "100", "name": "Page A", "access_token": "tokA"}]
    pages = await svc.import_pages(project.id, token="t")
    assert {p.page_id for p in pages} == {"100"}
    assert FacebookPageRepository(db_session).count(project_id=project.id) == 1


async def test_sync_reuses_stored_token(db_session, project, monkeypatch):
    async def fake_get(url, params):
        return ACCOUNTS

    monkeypatch.setattr("app.services.facebook_service.FacebookService._get", staticmethod(fake_get))
    monkeypatch.setattr("app.core.config.settings.facebook_system_token", "", raising=False)
    svc = FacebookService(db_session)
    # First import supplies the token; it should be persisted on the project.
    await svc.import_pages(project.id, token="system-user-token")
    db_session.refresh(project)
    assert project.facebook_system_token_encrypted

    # Second sync with no token must reuse the stored one (no error raised).
    pages = await svc.import_pages(project.id, token=None)
    assert {p.page_id for p in pages} == {"100", "200"}


async def test_import_without_token_raises(db_session, project, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.facebook_system_token", "", raising=False)
    with pytest.raises(ValidationException):
        await FacebookService(db_session).import_pages(project.id, token=None)


def test_import_endpoint(client, auth_headers, monkeypatch):
    async def fake_get(url, params):
        return ACCOUNTS

    monkeypatch.setattr("app.services.facebook_service.FacebookService._get", staticmethod(fake_get))
    pid = client.post("/api/v1/projects", json={"name": "P"}, headers=auth_headers).json()["data"]["id"]
    r = client.post(
        f"/api/v1/projects/{pid}/facebook/import", json={"token": "user-token"}, headers=auth_headers
    )
    assert r.status_code == 200
    assert len(r.json()["data"]) == 2
