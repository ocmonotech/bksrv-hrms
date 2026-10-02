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
        tenant = Tenant(name="Modules Corp", slug=f"mod-{uuid.uuid4().hex[:8]}", is_active=True)
        db.add(tenant)
        db.flush()

        company = Company(tenant_id=tenant.id, name="Modules Corp", code="MODC", is_active=True)
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
            email=f"mod-{uuid.uuid4().hex[:8]}@test.com",
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
            "user_id": str(user.id),
            "email": user.email,
            "password": "password",
        }
    finally:
        db.close()


def _headers(setup: dict, client: TestClient) -> dict:
    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": setup["email"], "password": setup["password"], "company_code": "MODC"},
    )
    assert login.status_code == 200
    token = login.json()["data"]["tokens"]["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": setup["tenant_id"],
        "X-Company-Id": setup["company_id"],
    }


def _create_employee(client: TestClient, headers: dict, setup: dict) -> str:
    response = client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "first_name": "Doc",
            "last_name": "Employee",
            "email": f"doc-{uuid.uuid4().hex[:8]}@test.com",
            "branch_id": setup["branch_id"],
            "department_id": setup["department_id"],
            "designation_id": setup["designation_id"],
            "employment_type": "full_time",
            "status": "active",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def test_document_category_and_letter_template(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)

    cat = client.post(
        "/api/v1/documents/categories",
        headers=headers,
        json={"name": "HR Policies", "code": "HR-POL", "description": "Policy documents"},
    )
    assert cat.status_code == 201
    assert cat.json()["data"]["code"] == "HR-POL"

    template = client.post(
        "/api/v1/documents/letter-templates",
        headers=headers,
        json={
            "name": "Offer Letter",
            "code": "OFFER",
            "letter_type": "offer",
            "subject": "Offer for {{name}}",
            "body_template": "Dear {{name}}, welcome to the company.",
        },
    )
    assert template.status_code == 201

    letter = client.post(
        "/api/v1/documents/generated-letters",
        headers=headers,
        json={
            "title": "Offer Letter",
            "subject": "Offer",
            "content": "Dear Employee, welcome.",
            "status": "draft",
        },
    )
    assert letter.status_code == 201
    assert letter.json()["data"]["status"] == "draft"


def test_employee_document_upload(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    employee_id = _create_employee(client, headers, hr_setup)

    response = client.post(
        "/api/v1/documents/employee",
        headers=headers,
        data={
            "employee_id": employee_id,
            "title": "ID Proof",
            "status": "active",
            "is_confidential": "false",
        },
        files={"file": ("id.pdf", io.BytesIO(b"pdf-content"), "application/pdf")},
    )
    assert response.status_code == 201
    assert response.json()["data"]["employee_id"] == employee_id

    listing = client.get(f"/api/v1/documents/employee?employee_id={employee_id}", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1


def test_helpdesk_ticket_flow(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)

    category = client.post(
        "/api/v1/helpdesk/categories",
        headers=headers,
        json={"name": "IT Support", "code": "IT", "default_sla_hours": 24},
    )
    assert category.status_code == 201
    category_id = category.json()["data"]["id"]

    ticket = client.post(
        "/api/v1/helpdesk/tickets",
        headers=headers,
        json={
            "category_id": category_id,
            "subject": "Laptop not working",
            "description": "My laptop does not power on since morning.",
            "priority": "high",
        },
    )
    assert ticket.status_code == 201
    ticket_id = ticket.json()["data"]["id"]
    assert ticket.json()["data"]["ticket_number"].startswith("TKT-")

    reply = client.post(
        f"/api/v1/helpdesk/tickets/{ticket_id}/reply",
        headers=headers,
        json={"message": "Please bring the laptop to IT desk."},
    )
    assert reply.status_code == 201

    assigned = client.post(
        f"/api/v1/helpdesk/tickets/{ticket_id}/assign",
        headers=headers,
        json={"assigned_to": hr_setup["user_id"], "notes": "IT admin"},
    )
    assert assigned.status_code == 200
    assert assigned.json()["data"]["assigned_to"] == hr_setup["user_id"]

    closed = client.post(
        f"/api/v1/helpdesk/tickets/{ticket_id}/close",
        headers=headers,
        json={"resolution_note": "Laptop replaced."},
    )
    assert closed.status_code == 200
    assert closed.json()["data"]["status"] == "closed"


def test_headcount_report(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    _create_employee(client, headers, hr_setup)

    response = client.get("/api/v1/reports/headcount", headers=headers)
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["report_type"] == "headcount"
    assert "columns" in body
    assert "rows" in body
    assert "summary" in body
    assert body["summary"]["total_employees"] >= 1
