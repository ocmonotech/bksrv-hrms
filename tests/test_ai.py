from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models.company_setup import Branch, Department, Designation
from app.models.role import UserTenantAccess
from app.models.tenant import Company, Tenant
from app.models.user import User
from app.repositories.role_repository import RoleRepository


@pytest.fixture
def hr_setup(db_session_factory) -> dict:
    db = db_session_factory()
    try:
        tenant = Tenant(name="AI Corp", slug=f"ai-{uuid.uuid4().hex[:8]}", is_active=True)
        db.add(tenant)
        db.flush()

        company = Company(tenant_id=tenant.id, name="AI Corp", code="AICO", is_active=True)
        db.add(company)
        db.flush()

        branch = Branch(tenant_id=tenant.id, name="HQ", code="HQ", created_by="seed", updated_by="seed")
        dept = Department(
            tenant_id=tenant.id, name="Engineering", code="ENG", created_by="seed", updated_by="seed"
        )
        desig = Designation(
            tenant_id=tenant.id, name="Developer", code="DEV", created_by="seed", updated_by="seed"
        )
        db.add_all([branch, dept, desig])
        db.flush()

        role = RoleRepository(db).get_system_role_by_slug("hr_admin")
        user = User(
            email=f"ai-{uuid.uuid4().hex[:8]}@test.com",
            password_hash=hash_password("password"),
            first_name="AI",
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
            "branch_id": str(branch.id),
            "department_id": str(dept.id),
            "designation_id": str(desig.id),
            "email": user.email,
            "password": "password",
        }
    finally:
        db.close()


def _headers(setup: dict, client: TestClient) -> dict:
    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": setup["email"], "password": setup["password"], "company_code": "AICO"},
    )
    assert login.status_code == 200
    token = login.json()["data"]["tokens"]["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": setup["tenant_id"],
        "X-Company-Id": setup["company_id"],
    }


def test_ai_usage(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    response = client.get("/api/v1/ai/usage", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["used_this_month"] == 0
    assert data["monthly_limit"] >= 1
    assert data["provider"] in ("mock", "auto")


def test_ai_chat(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    response = client.post(
        "/api/v1/ai/chat",
        headers=headers,
        json={"message": "What is our leave policy?"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["prompt_type"] == "hr_chatbot"
    assert body["provider"] == "mock"
    assert body["content"]
    assert body["token_usage"]["total_tokens"] > 0
    assert body["log_id"]

    usage = client.get("/api/v1/ai/usage", headers=headers)
    assert usage.json()["data"]["used_this_month"] == 1


def test_generate_policy(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    response = client.post(
        "/api/v1/ai/generate-policy",
        headers=headers,
        json={
            "policy_type": "Remote Work",
            "requirements": "Employees may work remotely up to 3 days per week with manager approval.",
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["prompt_type"] == "policy_generator"


def test_ai_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/ai/chat", json={"message": "hello"})
    assert response.status_code in (401, 403, 422)
