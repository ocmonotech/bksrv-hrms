from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone

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
            first_name="Jane",
            last_name="Sharma",
            email=f"jane-{uuid.uuid4().hex[:6]}@test.com",
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


def test_punch_and_daily_summary(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    today = date.today()
    punch_in = datetime.combine(today, time(9, 0), tzinfo=timezone.utc)
    punch_out = datetime.combine(today, time(18, 0), tzinfo=timezone.utc)

    resp = client.post(
        "/api/v1/attendance/punch",
        headers=headers,
        json={
            "employee_id": hr_setup["employee_id"],
            "punch_type": "in",
            "punch_time": punch_in.isoformat(),
            "source": "web",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["punch_type"] == "in"

    resp = client.post(
        "/api/v1/attendance/punch",
        headers=headers,
        json={
            "employee_id": hr_setup["employee_id"],
            "punch_type": "out",
            "punch_time": punch_out.isoformat(),
            "source": "web",
        },
    )
    assert resp.status_code == 201
    summary = resp.json()["data"]["daily_summary"]
    assert summary["total_work_minutes"] > 0
    assert summary["payable_days"] in ("1", "1.00", 1)

    daily = client.get(
        f"/api/v1/attendance/daily?employee_id={hr_setup['employee_id']}&attendance_date={today.isoformat()}",
        headers=headers,
    )
    assert daily.status_code == 200
    assert len(daily.json()["data"]) >= 1


def test_shift_crud(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)
    resp = client.post(
        "/api/v1/shifts",
        headers=headers,
        json={
            "name": "General Shift",
            "code": "GEN",
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "break_minutes": 60,
        },
    )
    assert resp.status_code == 201
    shift_id = resp.json()["data"]["id"]

    resp = client.get("/api/v1/shifts", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    resp = client.put(
        f"/api/v1/shifts/{shift_id}",
        headers=headers,
        json={"grace_minutes": 15},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["grace_minutes"] == 15


def test_leave_apply_and_approve(client: TestClient, hr_setup: dict) -> None:
    headers = _headers(hr_setup, client)

    lt = client.post(
        "/api/v1/leaves/types",
        headers=headers,
        json={
            "name": "Casual Leave",
            "code": "CL",
            "is_paid": True,
            "max_days_per_year": "12",
        },
    )
    assert lt.status_code == 201
    leave_type_id = lt.json()["data"]["id"]

    client.post(
        "/api/v1/leaves/policies",
        headers=headers,
        json={
            "leave_type_id": leave_type_id,
            "name": "CL Policy",
            "accrual_days": "1",
            "allow_lop": True,
        },
    )

    gen = client.post(
        "/api/v1/leaves/balance/generate",
        headers=headers,
        json={"year": date.today().year, "employee_ids": [hr_setup["employee_id"]]},
    )
    assert gen.status_code == 200
    assert gen.json()["data"]["created"] >= 1

    start = date.today() + timedelta(days=10)
    end = start + timedelta(days=1)
    apply_resp = client.post(
        "/api/v1/leaves/apply",
        headers=headers,
        json={
            "employee_id": hr_setup["employee_id"],
            "leave_type_id": leave_type_id,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "reason": "Personal work",
        },
    )
    assert apply_resp.status_code == 201
    request_id = apply_resp.json()["data"]["id"]
    assert apply_resp.json()["data"]["status"] == "pending"

    approve = client.put(f"/api/v1/leaves/{request_id}/approve", headers=headers, json={})
    assert approve.status_code == 200
    assert approve.json()["data"]["status"] == "approved"

    balance = client.get(
        f"/api/v1/leaves/balance/{hr_setup['employee_id']}?year={date.today().year}",
        headers=headers,
    )
    assert balance.status_code == 200
    assert len(balance.json()["data"]) >= 1
