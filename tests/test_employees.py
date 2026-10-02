from __future__ import annotations

import io
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
        tenant = Tenant(name="HR Corp", slug=f"hr-{uuid.uuid4().hex[:8]}", is_active=True)
        db.add(tenant)
        db.flush()

        company = Company(tenant_id=tenant.id, name="HR Corp", code="HRCO", is_active=True)
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
            email=f"hr-{uuid.uuid4().hex[:8]}@test.com",
            password_hash=hash_password("password"),
            first_name="HR",
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
        json={"identifier": setup["email"], "password": setup["password"], "company_code": "HRCO"},
    )
    assert login.status_code == 200
    token = login.json()["data"]["tokens"]["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": setup["tenant_id"],
        "X-Company-Id": setup["company_id"],
    }


def test_create_employee_auto_code(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    resp = client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "first_name": "John",
            "last_name": "Doe",
            "email": f"john-{uuid.uuid4().hex[:6]}@test.com",
            "mobile": "9876543210",
            "branch_id": hr_setup["branch_id"],
            "department_id": hr_setup["department_id"],
            "designation_id": hr_setup["designation_id"],
            "employment_type": "full_time",
            "personal_detail": {
                "pan_number": "ABCDE1234F",
                "aadhaar_number": "234567890123",
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["employee_code"].startswith("EMP")
    assert data["personal_detail"]["pan_number"] == "ABCDE1234F"


def test_employee_list_filters(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    resp = client.get(
        f"/api/v1/employees?department_id={hr_setup['department_id']}&status=active",
        headers=headers,
    )
    assert resp.status_code == 200
    assert "total" in resp.json()


def test_employee_status_update(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    create = client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "first_name": "Jane",
            "last_name": "Sharma",
            "email": f"jane-{uuid.uuid4().hex[:6]}@test.com",
        },
    )
    emp_id = create.json()["data"]["id"]

    status = client.put(
        f"/api/v1/employees/{emp_id}/status",
        headers=headers,
        json={"status": "on_notice", "reason": "Resignation submitted"},
    )
    assert status.status_code == 200
    assert status.json()["data"]["status"] == "on_notice"


def test_employee_document_and_timeline(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    create = client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "first_name": "Doc",
            "last_name": "User",
            "email": f"doc-{uuid.uuid4().hex[:6]}@test.com",
        },
    )
    emp_id = create.json()["data"]["id"]

    file_content = io.BytesIO(b"fake pdf content")
    doc = client.post(
        f"/api/v1/employees/{emp_id}/documents",
        headers=headers,
        data={"document_type": "resume", "title": "Resume"},
        files={"file": ("resume.pdf", file_content, "application/pdf")},
    )
    assert doc.status_code == 201
    assert "uploads/" in doc.json()["data"]["file_path"]

    timeline = client.get(f"/api/v1/employees/{emp_id}/timeline", headers=headers)
    assert timeline.status_code == 200
    assert timeline.json()["total"] >= 2


def test_invalid_pan_rejected(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    resp = client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "first_name": "Bad",
            "last_name": "PAN",
            "email": f"bad-{uuid.uuid4().hex[:6]}@test.com",
            "personal_detail": {"pan_number": "INVALID"},
        },
    )
    assert resp.status_code == 422
