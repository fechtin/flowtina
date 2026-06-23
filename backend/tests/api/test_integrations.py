"""Tests for sources, jobs, dashboard, settings and Facebook/Telegram (mocked HTTP)."""

from __future__ import annotations

import pytest


@pytest.fixture
def project(client, auth_headers):
    return client.post("/api/v1/projects", json={"name": "P"}, headers=auth_headers).json()["data"]["id"]


def test_topics_rss_keywords_crud(client, auth_headers, project):
    t = client.post(f"/api/v1/projects/{project}/topics", json={"topic": "AI"}, headers=auth_headers)
    assert t.status_code == 200
    topics = client.get(f"/api/v1/projects/{project}/topics", headers=auth_headers).json()["data"]
    assert len(topics) == 1
    assert client.delete(f"/api/v1/topics/{topics[0]['id']}", headers=auth_headers).status_code == 200

    r = client.post(
        f"/api/v1/projects/{project}/rss",
        json={"url": "https://news.google.com/rss"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    k = client.post(
        f"/api/v1/projects/{project}/keywords", json={"keyword": "crypto"}, headers=auth_headers
    )
    assert k.status_code == 200


def test_source_dedup(db_session):
    from app.repositories.repositories import ProjectRepository, UserRepository
    from app.services.source_service import SourceService
    from app.utils.text import content_hash

    user = UserRepository(db_session).create(email="s@x.com", password_hash="x", name="S")
    project = ProjectRepository(db_session).create(user_id=user.id, name="P")
    db_session.commit()

    svc = SourceService(db_session)
    h = content_hash("title\ncontent")
    assert not svc.cache.exists(project.id, h)
    svc.cache.create(project_id=project.id, hash=h, title="t", content="c", source_type="rss")
    db_session.commit()
    assert svc.cache.exists(project.id, h)


def test_jobs_crud(client, auth_headers, project):
    r = client.post(
        f"/api/v1/projects/{project}/jobs",
        json={"name": "Daily", "job_type": "generate_content", "cron_expression": "0 */3 * * *"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    job_id = r.json()["data"]["id"]
    jobs = client.get(f"/api/v1/projects/{project}/jobs", headers=auth_headers).json()["data"]
    assert len(jobs) == 1
    upd = client.put(f"/api/v1/jobs/{job_id}", json={"enabled": False}, headers=auth_headers)
    assert upd.json()["data"]["enabled"] is False
    assert client.delete(f"/api/v1/jobs/{job_id}", headers=auth_headers).status_code == 200


def test_dashboard_and_settings(client, auth_headers, project):
    stats = client.get(f"/api/v1/projects/{project}/dashboard/stats", headers=auth_headers)
    assert stats.status_code == 200
    assert "success_rate" in stats.json()["data"]

    charts = client.get(f"/api/v1/projects/{project}/dashboard/charts", headers=auth_headers)
    assert len(charts.json()["data"]["labels"]) == 7

    s = client.put("/api/v1/settings", json={"theme": "light", "daily_budget": 5.0}, headers=auth_headers)
    assert s.json()["data"]["theme"] == "light"


def test_telegram_config_and_send(client, auth_headers, project, monkeypatch):
    async def fake_post(url, payload):
        return {"ok": True}

    monkeypatch.setattr("app.services.telegram_service.TelegramService._post", staticmethod(fake_post))

    cfg = client.post(
        f"/api/v1/projects/{project}/telegram/config",
        json={"bot_token": "123:abc", "chat_id": "999"},
        headers=auth_headers,
    )
    assert cfg.status_code == 200
    assert cfg.json()["data"]["chat_id"] == "999"

    test = client.post(
        f"/api/v1/projects/{project}/telegram/test",
        json={"message": "hello"},
        headers=auth_headers,
    )
    assert test.json()["data"]["sent"] is True


def test_facebook_connect_and_publish(client, auth_headers, project, monkeypatch):
    async def fake_graph(url, data):
        return {"id": "fb_post_123"}

    monkeypatch.setattr("app.services.facebook_service.FacebookService._call_graph", staticmethod(fake_graph))

    page = client.post(
        f"/api/v1/projects/{project}/facebook/pages",
        json={"page_name": "My Page", "page_id": "111", "access_token": "tok"},
        headers=auth_headers,
    ).json()["data"]

    post = client.post(
        f"/api/v1/projects/{project}/posts",
        json={"content": "Hello Facebook from Flowtina test suite content."},
        headers=auth_headers,
    ).json()["data"]

    pub = client.post(
        f"/api/v1/posts/{post['id']}/publish?page_id={page['id']}", headers=auth_headers
    )
    assert pub.status_code == 200
    assert pub.json()["data"]["facebook_post_id"] == "fb_post_123"
