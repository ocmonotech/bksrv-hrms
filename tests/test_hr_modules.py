from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models.company_setup import Branch, Department, Designation
from app.models.employee import Employee
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

        employee = Employee(
            tenant_id=tenant.id,
            company_id=company.id,
            employee_code="EMP001",
            first_name="Alex",
            last_name="Dev",
            email=f"alex-{uuid.uuid4().hex[:6]}@test.com",
            branch_id=branch.id,
            department_id=dept.id,
            designation_id=desig.id,
            employment_type="full_time",
            status="active",
            is_active=True,
            created_by=str(user.id),
            updated_by=str(user.id),
        )
        db.add(employee)
        db.commit()
        return {
            "tenant_id": str(tenant.id),
            "company_id": str(company.id),
            "employee_id": str(employee.id),
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


def test_recruitment_flow(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)

    job = client.post(
        "/api/v1/recruitment/jobs",
        headers=headers,
        json={"title": "Backend Engineer", "code": "BE001", "openings_count": 2},
    )
    assert job.status_code == 201
    job_id = job.json()["data"]["id"]

    candidate = client.post(
        "/api/v1/recruitment/candidates",
        headers=headers,
        json={
            "job_opening_id": job_id,
            "first_name": "Sam",
            "last_name": "Candidate",
            "email": f"sam-{uuid.uuid4().hex[:6]}@test.com",
        },
    )
    assert candidate.status_code == 201
    candidate_id = candidate.json()["data"]["id"]

    interview = client.post(
        "/api/v1/recruitment/interviews",
        headers=headers,
        json={
            "candidate_id": candidate_id,
            "job_opening_id": job_id,
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert interview.status_code == 201

    offer = client.post(
        "/api/v1/recruitment/offers",
        headers=headers,
        json={
            "candidate_id": candidate_id,
            "job_opening_id": job_id,
            "offered_ctc": "800000",
            "joining_date": "2026-08-01",
        },
    )
    assert offer.status_code == 201
    offer_id = offer.json()["data"]["id"]

    approve = client.put(f"/api/v1/recruitment/offers/{offer_id}/approve", headers=headers, json={})
    assert approve.status_code == 200
    assert approve.json()["data"]["status"] == "approved"


def test_onboarding_flow(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)

    checklist = client.post(
        "/api/v1/onboarding/checklists",
        headers=headers,
        json={"name": "Standard Onboarding", "code": "STD-ONB"},
    )
    assert checklist.status_code == 201
    checklist_id = checklist.json()["data"]["id"]

    task = client.post(
        "/api/v1/onboarding/tasks",
        headers=headers,
        json={
            "checklist_id": checklist_id,
            "employee_id": hr_setup["employee_id"],
            "task_name": "Complete KYC",
        },
    )
    assert task.status_code == 201

    doc = client.post(
        "/api/v1/onboarding/documents",
        headers=headers,
        data={"employee_id": hr_setup["employee_id"], "document_type": "aadhaar"},
        files={"file": ("aadhaar.pdf", io.BytesIO(b"pdf-content"), "application/pdf")},
    )
    assert doc.status_code == 201

    probation = client.post(
        "/api/v1/onboarding/probation",
        headers=headers,
        json={
            "employee_id": hr_setup["employee_id"],
            "review_date": date.today().isoformat(),
            "rating": 4,
            "outcome": "confirm",
        },
    )
    assert probation.status_code == 201


def test_performance_flow(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)

    goal = client.post(
        "/api/v1/performance/goals",
        headers=headers,
        json={
            "employee_id": hr_setup["employee_id"],
            "title": "Deliver MVP",
            "start_date": "2026-01-01",
            "end_date": "2026-06-30",
        },
    )
    assert goal.status_code == 201

    okr = client.post(
        "/api/v1/performance/okrs",
        headers=headers,
        json={
            "employee_id": hr_setup["employee_id"],
            "objective": "Improve platform reliability",
            "quarter": 2,
            "year": 2026,
            "key_results": [{"title": "Reduce incidents", "target": "50%"}],
        },
    )
    assert okr.status_code == 201

    cycle = client.post(
        "/api/v1/performance/review-cycles",
        headers=headers,
        json={
            "name": "FY2026 Annual",
            "code": "FY26",
            "start_date": "2026-04-01",
            "end_date": "2026-03-31",
        },
    )
    assert cycle.status_code == 201
    cycle_id = cycle.json()["data"]["id"]

    review = client.post(
        "/api/v1/performance/reviews",
        headers=headers,
        json={
            "review_type": "self",
            "review_cycle_id": cycle_id,
            "employee_id": hr_setup["employee_id"],
            "rating": "4.0",
            "responses": {"strengths": "Delivery"},
        },
    )
    assert review.status_code == 201

    appraisal = client.post(
        "/api/v1/performance/appraisals",
        headers=headers,
        json={
            "review_cycle_id": cycle_id,
            "employee_id": hr_setup["employee_id"],
            "final_rating": "4.2",
            "increment_percent": "10",
        },
    )
    assert appraisal.status_code == 201
    appraisal_id = appraisal.json()["data"]["id"]

    approved = client.put(f"/api/v1/performance/appraisals/{appraisal_id}/approve", headers=headers, json={})
    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "approved"
