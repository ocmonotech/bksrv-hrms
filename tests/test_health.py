from __future__ import annotations

from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "app" in response.json()


def test_health_check(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "healthy"


def test_readiness_check(client: TestClient) -> None:
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ready"


def test_login_invalid_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "unknown@ocmono.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_list_roles_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/roles")
    assert response.status_code == 401


def test_list_permissions_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/permissions")
    assert response.status_code == 401


def test_permissions_catalog(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "super@ocmono.com", "password": "change-me"},
    )
    assert login.status_code == 200

    token = login.json()["data"]["tokens"]["access_token"]
    response = client.get(
        "/api/v1/permissions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 112  # 16 modules × 7 actions


def test_super_admin_login(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "super@ocmono.com", "password": "change-me"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["user"]["is_super_admin"] is True
    assert body["user"]["role"] == "super_admin"
    assert "access_token" in body["tokens"]
