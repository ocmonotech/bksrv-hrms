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
        tenant = Tenant(name="Features Corp", slug=f"feat-{uuid.uuid4().hex[:8]}", is_active=True)
        db.add(tenant)
        db.flush()

        company = Company(tenant_id=tenant.id, name="Features Corp", code="FEAT", is_active=True)
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
            email=f"feat-{uuid.uuid4().hex[:8]}@test.com",
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
        json={"identifier": setup["email"], "password": setup["password"], "company_code": "FEAT"},
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
            "first_name": "Test",
            "last_name": "Employee",
            "email": f"emp-{uuid.uuid4().hex[:8]}@test.com",
            "branch_id": setup["branch_id"],
            "department_id": setup["department_id"],
            "designation_id": setup["designation_id"],
            "employment_type": "full_time",
            "status": "active",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def test_timesheet_project_and_entry_flow(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    employee_id = _create_employee(client, headers, hr_setup)

    project = client.post(
        "/api/v1/timesheets/projects",
        headers=headers,
        json={"name": "Internal HRMS", "code": "HRMS", "client_name": "Internal", "is_billable": False},
    )
    assert project.status_code == 201
    project_id = project.json()["data"]["id"]

    entry = client.post(
        "/api/v1/timesheets/entries",
        headers=headers,
        json={
            "employee_id": employee_id,
            "project_id": project_id,
            "entry_date": "2026-06-16",
            "hours": 8,
            "description": "Feature development",
        },
    )
    assert entry.status_code == 201
    entry_id = entry.json()["data"]["id"]
    assert entry.json()["data"]["status"] == "draft"

    submitted = client.post(f"/api/v1/timesheets/entries/{entry_id}/submit", headers=headers)
    assert submitted.status_code == 200
    assert submitted.json()["data"]["status"] == "submitted"

    approved = client.post(f"/api/v1/timesheets/entries/{entry_id}/approve", headers=headers)
    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "approved"

    dashboard = client.get("/api/v1/timesheets/dashboard", headers=headers)
    assert dashboard.status_code == 200
    assert "total_hours_this_week" in dashboard.json()["data"]


def test_training_course_and_enrollment(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    employee_id = _create_employee(client, headers, hr_setup)

    course = client.post(
        "/api/v1/training/courses",
        headers=headers,
        json={
            "title": "Security Awareness",
            "code": "SEC-101",
            "category": "compliance",
            "duration_hours": 2,
            "delivery_mode": "online",
            "is_mandatory": True,
        },
    )
    assert course.status_code == 201
    course_id = course.json()["data"]["id"]

    enrollment = client.post(
        "/api/v1/training/enrollments",
        headers=headers,
        json={"course_id": course_id, "employee_id": employee_id, "due_date": "2026-07-31"},
    )
    assert enrollment.status_code == 201
    enrollment_id = enrollment.json()["data"]["id"]

    updated = client.patch(
        f"/api/v1/training/enrollments/{enrollment_id}",
        headers=headers,
        json={"status": "completed", "progress_pct": 100},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["status"] == "completed"


def test_survey_create_questions_and_respond(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    employee_id = _create_employee(client, headers, hr_setup)

    survey = client.post(
        "/api/v1/surveys",
        headers=headers,
        json={
            "title": "Engagement Pulse",
            "description": "Quarterly check-in",
            "survey_type": "engagement",
            "is_anonymous": True,
        },
    )
    assert survey.status_code == 201
    survey_id = survey.json()["data"]["id"]

    question = client.post(
        f"/api/v1/surveys/{survey_id}/questions",
        headers=headers,
        json={"question_text": "I feel valued at work", "question_type": "rating", "order_index": 1},
    )
    assert question.status_code == 201
    question_id = question.json()["data"]["id"]

    activated = client.patch(
        f"/api/v1/surveys/{survey_id}",
        headers=headers,
        json={"status": "active"},
    )
    assert activated.status_code == 200
    assert activated.json()["data"]["status"] == "active"

    response = client.post(
        f"/api/v1/surveys/{survey_id}/responses?employee_id={employee_id}",
        headers=headers,
        json={"answers": [{"question_id": question_id, "response_value": "5"}]},
    )
    assert response.status_code == 200
    assert response.json()["data"]["submitted"] == 1


def test_live_analytics(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    response = client.get("/api/v1/reports/analytics/live", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert "headcount" in data
    assert "trends" in data
    assert isinstance(data["trends"], list)
