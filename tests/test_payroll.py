from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models.company_setup import Branch, Department, Designation
from app.models.employee import Employee, EmployeeBankDetail
from app.models.role import UserTenantAccess
from app.models.tenant import Company, Tenant
from app.models.user import User
from app.repositories.role_repository import RoleRepository


@pytest.fixture
def payroll_setup(db_session_factory) -> dict:
    db = db_session_factory()
    try:
        tenant = Tenant(name="Pay Corp", slug=f"pay-{uuid.uuid4().hex[:8]}", is_active=True)
        db.add(tenant)
        db.flush()

        company = Company(tenant_id=tenant.id, name="Pay Corp", code="PAYCO", is_active=True)
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

        role = RoleRepository(db).get_system_role_by_slug("payroll_admin")
        user = User(
            email=f"payroll-{uuid.uuid4().hex[:8]}@test.com",
            password_hash=hash_password("password"),
            first_name="Payroll",
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
            first_name="Ravi",
            last_name="Kumar",
            email=f"ravi-{uuid.uuid4().hex[:6]}@test.com",
            branch_id=branch.id,
            department_id=dept.id,
            designation_id=desig.id,
            employment_type="full_time",
            status="active",
            is_active=True,
            joining_date=date(2024, 1, 1),
            created_by=str(user.id),
            updated_by=str(user.id),
        )
        db.add(employee)
        db.flush()
        db.add(
            EmployeeBankDetail(
                tenant_id=tenant.id,
                employee_id=employee.id,
                account_holder_name="Ravi Kumar",
                bank_name="HDFC",
                account_number="1234567890",
                ifsc_code="HDFC0001234",
                created_by=str(user.id),
                updated_by=str(user.id),
            )
        )
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
        json={"identifier": setup["email"], "password": setup["password"], "company_code": "PAYCO"},
    )
    assert login.status_code == 200
    token = login.json()["data"]["tokens"]["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": setup["tenant_id"],
        "X-Company-Id": setup["company_id"],
    }


def test_payroll_flow(client: TestClient, payroll_setup: dict) -> None:
    headers = _headers(payroll_setup, client)

    basic = client.post(
        "/api/v1/payroll/components",
        headers=headers,
        json={
            "name": "Basic Salary",
            "code": "BASIC",
            "component_type": "earning",
            "pf_applicable": True,
        },
    )
    assert basic.status_code == 201
    basic_id = basic.json()["data"]["id"]

    hra = client.post(
        "/api/v1/payroll/components",
        headers=headers,
        json={"name": "HRA", "code": "HRA", "component_type": "earning"},
    )
    assert hra.status_code == 201
    hra_id = hra.json()["data"]["id"]

    structure = client.post(
        "/api/v1/payroll/salary-structures",
        headers=headers,
        json={
            "name": "Standard CTC",
            "code": "STD",
            "annual_ctc": "600000",
            "components": [
                {"component_id": basic_id, "monthly_amount": "30000"},
                {"component_id": hra_id, "monthly_amount": "15000"},
            ],
        },
    )
    assert structure.status_code == 201
    structure_id = structure.json()["data"]["id"]

    assign = client.post(
        "/api/v1/payroll/assign-structure",
        headers=headers,
        json={
            "employee_id": payroll_setup["employee_id"],
            "structure_id": structure_id,
            "effective_from": "2024-01-01",
            "annual_ctc": "600000",
        },
    )
    assert assign.status_code == 201

    today = date.today()
    run = client.post(
        "/api/v1/payroll/run",
        headers=headers,
        json={
            "month": today.month,
            "year": today.year,
            "working_days": 26,
            "employee_ids": [payroll_setup["employee_id"]],
        },
    )
    assert run.status_code == 201
    run_data = run.json()["data"]
    assert run_data["employee_count"] == 1
    assert float(run_data["total_net"]) > 0
    run_id = run_data["id"]

    preview = client.get(f"/api/v1/payroll/run/{run_id}/preview", headers=headers)
    assert preview.status_code == 200
    preview_data = preview.json()["data"]
    assert len(preview_data["employees"]) == 1
    assert len(preview_data["bank_transfer"]) == 1
    assert preview_data["bank_transfer"][0]["account_number"] == "1234567890"

    approve = client.put(f"/api/v1/payroll/run/{run_id}/approve", headers=headers)
    assert approve.status_code == 200
    assert approve.json()["data"]["status"] == "approved"

    payslips = client.get(
        f"/api/v1/payroll/payslips/{payroll_setup['employee_id']}?year={today.year}",
        headers=headers,
    )
    assert payslips.status_code == 200
    assert len(payslips.json()["data"]) >= 1

    lock = client.put(f"/api/v1/payroll/run/{run_id}/lock", headers=headers)
    assert lock.status_code == 200
    assert lock.json()["data"]["status"] == "locked"


def test_fnf_settlement(client: TestClient, payroll_setup: dict) -> None:
    headers = _headers(payroll_setup, client)
    resp = client.post(
        "/api/v1/payroll/fnf",
        headers=headers,
        json={
            "employee_id": payroll_setup["employee_id"],
            "last_working_date": "2026-06-30",
            "pending_salary": "25000",
            "leave_encashment": "5000",
            "loan_recovery": "2000",
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert float(data["net_payable"]) == 28000.0


def test_list_components(client: TestClient, payroll_setup: dict) -> None:
    headers = _headers(payroll_setup, client)
    client.post(
        "/api/v1/payroll/components",
        headers=headers,
        json={"name": "Special Allowance", "code": "SA", "component_type": "earning"},
    )
    resp = client.get("/api/v1/payroll/components", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
