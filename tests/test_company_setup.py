from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models.role import UserTenantAccess
from app.models.tenant import Company, Tenant
from app.models.user import User
from app.repositories.role_repository import RoleRepository


@pytest.fixture
def tenant_setup(db_session_factory) -> dict:
    db = db_session_factory()
    try:
        tenant = Tenant(name="Test Corp", slug=f"test-{uuid.uuid4().hex[:8]}", is_active=True)
        db.add(tenant)
        db.flush()

        company = Company(
            tenant_id=tenant.id,
            name="Test Corp",
            code="TESTCO",
            is_active=True,
        )
        db.add(company)
        db.flush()

        role = RoleRepository(db).get_system_role_by_slug("company_admin")
        user = User(
            email=f"admin-{uuid.uuid4().hex[:8]}@test.com",
            password_hash=hash_password("password"),
            first_name="Test",
            last_name="Admin",
            is_super_admin=False,
            is_active=True,
            email_verified=True,
        )
        db.add(user)
        db.flush()

        db.add(
            UserTenantAccess(
                tenant_id=tenant.id,
                user_id=user.id,
                company_id=company.id,
                role_id=role.id,
                is_active=True,
                is_default=True,
            )
        )
        db.commit()
        return {
            "tenant_id": str(tenant.id),
            "company_id": str(company.id),
            "email": user.email,
            "password": "password",
        }
    finally:
        db.close()


def _auth_headers(setup: dict, client: TestClient) -> dict:
    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": setup["email"], "password": setup["password"], "company_code": "TESTCO"},
    )
    assert login.status_code == 200
    token = login.json()["data"]["tokens"]["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": setup["tenant_id"],
        "X-Company-Id": setup["company_id"],
    }


def test_company_profile_upsert(client: TestClient, tenant_setup: dict) -> None:
    headers = _auth_headers(tenant_setup, client)

    get_resp = client.get("/api/v1/company/profile", headers=headers)
    assert get_resp.status_code == 404

    put_resp = client.put(
        "/api/v1/company/profile",
        headers=headers,
        json={"display_name": "Test Corp Pvt Ltd", "country": "India", "currency": "INR"},
    )
    assert put_resp.status_code == 200
    body = put_resp.json()["data"]
    assert body["display_name"] == "Test Corp Pvt Ltd"
    assert body["tenant_id"] == tenant_setup["tenant_id"]

    get_resp = client.get("/api/v1/company/profile", headers=headers)
    assert get_resp.status_code == 200


def test_branch_crud(client: TestClient, tenant_setup: dict) -> None:
    headers = _auth_headers(tenant_setup, client)

    create = client.post(
        "/api/v1/branches",
        headers=headers,
        json={"name": "HQ", "code": "hq", "city": "Mumbai", "is_head_office": True},
    )
    assert create.status_code == 201
    branch_id = create.json()["data"]["id"]
    assert create.json()["data"]["code"] == "HQ"

    listing = client.get("/api/v1/branches?search=hq", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    update = client.put(
        f"/api/v1/branches/{branch_id}",
        headers=headers,
        json={"name": "Head Office", "is_active": True},
    )
    assert update.status_code == 200
    assert update.json()["data"]["name"] == "Head Office"

    delete = client.delete(f"/api/v1/branches/{branch_id}", headers=headers)
    assert delete.status_code == 200

    get_deleted = client.get(f"/api/v1/branches/{branch_id}", headers=headers)
    assert get_deleted.status_code == 404


def test_department_crud(client: TestClient, tenant_setup: dict) -> None:
    headers = _auth_headers(tenant_setup, client)

    create = client.post(
        "/api/v1/departments",
        headers=headers,
        json={"name": "Engineering", "code": "eng", "description": "Tech team"},
    )
    assert create.status_code == 201
    assert create.json()["data"]["is_active"] is True


def test_company_setup_requires_tenant_header(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "super@ocmono.com", "password": "change-me"},
    )
    token = login.json()["data"]["tokens"]["access_token"]
    resp = client.get("/api/v1/branches", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
