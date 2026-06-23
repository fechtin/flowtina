"""API tests for auth, projects, providers and prompts."""

from __future__ import annotations


def test_register_login_profile(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "u1@example.com", "password": "password123", "name": "User One"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["access_token"]

    # Duplicate registration conflicts.
    r2 = client.post(
        "/api/v1/auth/register",
        json={"email": "u1@example.com", "password": "password123", "name": "Dup"},
    )
    assert r2.status_code == 409

    r3 = client.post("/api/v1/auth/login", json={"email": "u1@example.com", "password": "password123"})
    assert r3.status_code == 200
    token = r3.json()["data"]["access_token"]

    r4 = client.get("/api/v1/auth/profile", headers={"Authorization": f"Bearer {token}"})
    assert r4.json()["data"]["email"] == "u1@example.com"
    assert r4.json()["data"]["is_admin"] is True  # first user is admin


def test_login_invalid_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "u2@example.com", "password": "password123", "name": "U2"},
    )
    r = client.post("/api/v1/auth/login", json={"email": "u2@example.com", "password": "bad"})
    assert r.status_code == 401


def test_profile_requires_auth(client):
    assert client.get("/api/v1/auth/profile").status_code == 401


def test_project_crud_and_seeded_prompts(client, auth_headers):
    r = client.post("/api/v1/projects", json={"name": "P1", "description": "d"}, headers=auth_headers)
    assert r.status_code == 200
    pid = r.json()["data"]["id"]

    # Default templates were seeded on creation.
    tmpls = client.get(f"/api/v1/projects/{pid}/prompts", headers=auth_headers).json()["data"]
    assert len(tmpls) >= 8

    r2 = client.put(f"/api/v1/projects/{pid}", json={"name": "P1-renamed"}, headers=auth_headers)
    assert r2.json()["data"]["name"] == "P1-renamed"

    assert client.delete(f"/api/v1/projects/{pid}", headers=auth_headers).status_code == 200
    # Soft-deleted -> no longer listed.
    listed = client.get("/api/v1/projects", headers=auth_headers).json()["data"]
    assert all(p["id"] != pid for p in listed)


def test_provider_api_key_is_masked(client, auth_headers):
    pid = client.post("/api/v1/projects", json={"name": "P"}, headers=auth_headers).json()["data"]["id"]
    r = client.post(
        f"/api/v1/projects/{pid}/providers",
        json={"provider": "openai", "api_key": "sk-supersecret", "model": "gpt-4o-mini"},
        headers=auth_headers,
    )
    data = r.json()["data"]
    assert "supersecret" not in data["api_key_masked"]
    assert data["api_key_masked"].startswith("sk-s")


def test_prompt_render_endpoint(client, auth_headers):
    r = client.post(
        "/api/v1/prompts/render",
        json={"template": "Hi {{topic}}", "variables": {"topic": "AI"}},
        headers=auth_headers,
    )
    assert r.json()["data"]["rendered"] == "Hi AI"


def test_cross_user_project_access_forbidden(client):
    a = client.post(
        "/api/v1/auth/register",
        json={"email": "a@x.com", "password": "password123", "name": "A"},
    ).json()["data"]["access_token"]
    b = client.post(
        "/api/v1/auth/register",
        json={"email": "b@x.com", "password": "password123", "name": "B"},
    ).json()["data"]["access_token"]
    pid = client.post(
        "/api/v1/projects", json={"name": "owned"}, headers={"Authorization": f"Bearer {a}"}
    ).json()["data"]["id"]
    # B is not admin and does not own the project.
    r = client.get(f"/api/v1/projects/{pid}", headers={"Authorization": f"Bearer {b}"})
    assert r.status_code == 403
