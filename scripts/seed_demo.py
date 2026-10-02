from __future__ import annotations

"""Seed demo tenant, company, org setup, and demo users for local development."""

from datetime import date

from app.constants.india import INDIA_DEFAULTS
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.company_setup import Branch, CompanyProfile, Department, Designation, Grade, Holiday
from app.models.role import UserTenantAccess
from app.models.tenant import Company, Tenant
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.services.auth_service import create_super_admin
from app.services.rbac_seed_service import RBACSeedService

settings = get_settings()

DEMO_USERS = [
    {
        "email": "hr@theglobalelephant.com",
        "password": "Lotus@2026",
        "first_name": "TGE",
        "last_name": "HR",
        "role_slug": "company_admin",
    }
    # {
    #     "email": "hr@ocmono.com",
    #     "password": "password",
    #     "first_name": "Suresh",
    #     "last_name": "Menon",
    #     "role_slug": "hr_admin",
    # },
    # {
    #     "email": "employee@ocmono.com",
    #     "password": "password",
    #     "first_name": "Asha",
    #     "last_name": "Patel",
    #     "role_slug": "employee",
    # },
    # {
    #     "email": "2fa@ocmono.com",
    #     "password": "password",
    #     "first_name": "Pooja",
    #     "last_name": "Desai",
    #     "role_slug": "company_admin",
    #     "two_factor_enabled": True,
    # },
]


def _seed_company_profile(db, tenant: Tenant, company: Company, actor_id: str) -> None:
    profile = (
        db.query(CompanyProfile)
        .filter(CompanyProfile.tenant_id == tenant.id, CompanyProfile.deleted_at.is_(None))
        .first()
    )
    if profile:
        return
    db.add(
        CompanyProfile(
            tenant_id=str(tenant.id),
            company_id=str(company.id),
            display_name="The Global Elephant",
            legal_name="The Global Elephant Pvt. Ltd.",
            registration_number="U72900MH2020PTC123456",
            tax_id="27AABCO1234A1Z5",
            email="tge@theglobalelephant.com",
            phone="+912245678900",
            website="https://theglobalelephant.com",
            address_line1="501, Business Park, Andheri East",
            city="Mumbai",
            state="Maharashtra",
            country=INDIA_DEFAULTS["country"],
            postal_code="400069",
            timezone=INDIA_DEFAULTS["timezone"],
            currency=INDIA_DEFAULTS["currency"],
            fiscal_year_start_month=INDIA_DEFAULTS["fiscal_year_start_month"],
            is_active=True,
            created_by=actor_id,
            updated_by=actor_id,
        )
    )
    db.flush()


def _seed_branches(db, tenant: Tenant, actor_id: str) -> None:
    branches = [
        {
            "name": "Mumbai HQ",
            "code": "MUM-HQ",
            "city": "Mumbai",
            "state": "Maharashtra",
            "postal_code": "400069",
            "is_head_office": True,
        },
        {
            "name": "Bangalore Office",
            "code": "BLR-01",
            "city": "Bangalore",
            "state": "Karnataka",
            "postal_code": "560066",
            "is_head_office": False,
        },
        {
            "name": "Delhi Office",
            "code": "DEL-01",
            "city": "Delhi",
            "state": "Delhi",
            "postal_code": "110001",
            "is_head_office": False,
        },
    ]
    for item in branches:
        exists = (
            db.query(Branch)
            .filter(Branch.tenant_id == tenant.id, Branch.code == item["code"])
            .first()
        )
        if exists:
            continue
        db.add(
            Branch(
                tenant_id=str(tenant.id),
                name=item["name"],
                code=item["code"],
                address_line1=f"{item['name']} Address",
                city=item["city"],
                state=item["state"],
                country=INDIA_DEFAULTS["country"],
                postal_code=item["postal_code"],
                phone="+919876543210",
                is_head_office=item["is_head_office"],
                is_active=True,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )
    db.flush()


def _seed_org_structure(db, tenant: Tenant, actor_id: str) -> None:
    if db.query(Department).filter(Department.tenant_id == tenant.id, Department.code == "ENG").first():
        return

    grades = [
        ("L2 - Associate", "L2", 2),
        ("L3 - Professional", "L3", 3),
        ("L4 - Senior", "L4", 4),
        ("L5 - Manager", "L5", 5),
    ]
    grade_ids = {}
    for name, code, level in grades:
        grade = Grade(
            tenant_id=str(tenant.id),
            name=name,
            code=code,
            level=level,
            description=f"Grade {code}",
            is_active=True,
            created_by=actor_id,
            updated_by=actor_id,
        )
        db.add(grade)
        db.flush()
        grade_ids[code] = grade.id

    departments = [
        ("Engineering", "ENG"),
        ("Human Resources", "HR"),
        ("Finance", "FIN"),
        ("Sales", "SAL"),
    ]
    dept_ids = {}
    for name, code in departments:
        dept = Department(
            tenant_id=str(tenant.id),
            name=name,
            code=code,
            is_active=True,
            created_by=actor_id,
            updated_by=actor_id,
        )
        db.add(dept)
        db.flush()
        dept_ids[code] = dept.id

    designations = [
        ("Software Engineer", "SE", "ENG", "L3"),
        ("Senior Software Engineer", "SSE", "ENG", "L4"),
        ("HR Executive", "HRE", "HR", "L3"),
        ("Finance Analyst", "FA", "FIN", "L3"),
        ("Sales Manager", "SM", "SAL", "L5"),
    ]
    for name, code, dept_code, grade_code in designations:
        db.add(
            Designation(
                tenant_id=str(tenant.id),
                name=name,
                code=code,
                department_id=str(dept_ids[dept_code]),
                grade_id=str(grade_ids[grade_code]),
                is_active=True,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )
    db.flush()


def _seed_holidays(db, tenant: Tenant, actor_id: str) -> None:
    holidays = [
        ("Republic Day", date(2026, 1, 26)),
        ("Independence Day", date(2026, 8, 15)),
        ("Gandhi Jayanti", date(2026, 10, 2)),
        ("Diwali", date(2026, 11, 8)),
    ]
    for name, holiday_date in holidays:
        exists = (
            db.query(Holiday)
            .filter(Holiday.tenant_id == tenant.id, Holiday.name == name, Holiday.holiday_date == holiday_date)
            .first()
        )
        if exists:
            continue
        db.add(
            Holiday(
                tenant_id=str(tenant.id),
                name=name,
                holiday_date=holiday_date,
                holiday_type="public",
                is_active=True,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )
    db.flush()


def seed_demo() -> None:
    db = SessionLocal()
    try:
        RBACSeedService(db).seed_all()
        create_super_admin(db)

        tenant = db.query(Tenant).filter(Tenant.slug == "ocmono").first()
        if not tenant:
            tenant = Tenant(name="OCMono Technologies", slug="ocmono", is_active=True)
            db.add(tenant)
            db.flush()

        company = (
            db.query(Company)
            .filter(Company.tenant_id == tenant.id, Company.code == "OCMONO")
            .first()
        )
        if not company:
            company = Company(
                tenant_id=tenant.id,
                name="OCMono Technologies",
                code="OCMONO",
                email="contact@ocmono.com",
                is_active=True,
            )
            db.add(company)
            db.flush()

        admin_user = db.query(User).filter(User.email == "admin@ocmono.com").first()
        actor_id = str(admin_user.id) if admin_user else str(company.id)

        role_repo = RoleRepository(db)
        for demo in DEMO_USERS:
            role = role_repo.get_system_role_by_slug(demo["role_slug"])
            if not role:
                raise RuntimeError(f"Role '{demo['role_slug']}' not found — run RBAC seed first")

            user = db.query(User).filter(User.email == demo["email"]).first()
            if not user:
                user = User(
                    email=demo["email"],
                    password_hash=hash_password(demo["password"]),
                    first_name=demo["first_name"],
                    last_name=demo["last_name"],
                    is_super_admin=False,
                    is_active=True,
                    email_verified=True,
                    two_factor_enabled=demo.get("two_factor_enabled", False),
                )
                db.add(user)
                db.flush()
            elif demo.get("two_factor_enabled"):
                user.two_factor_enabled = True

            if demo["email"] == "admin@ocmono.com":
                actor_id = str(user.id)

            access_exists = (
                db.query(UserTenantAccess)
                .filter(
                    UserTenantAccess.tenant_id == tenant.id,
                    UserTenantAccess.user_id == user.id,
                    UserTenantAccess.company_id == company.id,
                )
                .first()
            )
            if not access_exists:
                db.add(
                    UserTenantAccess(
                        tenant_id=tenant.id,
                        user_id=user.id,
                        company_id=company.id,
                        role_id=role.id,
                        is_active=True,
                        is_default=demo["role_slug"] == "company_admin",
                    )
                )

        db.flush()
        _seed_company_profile(db, tenant, company, actor_id)
        _seed_branches(db, tenant, actor_id)
        _seed_org_structure(db, tenant, actor_id)
        _seed_holidays(db, tenant, actor_id)

        db.commit()
        print("Demo seed completed.")
        print(f"Super admin: {settings.super_admin_email}")
        print("Demo tenant: ocmono / company: OCMONO")
        print("Seeded: company profile, 3 branches, departments, grades, designations, holidays")
        for demo in DEMO_USERS:
            print(f"  - {demo['email']} / {demo['password']} ({demo['role_slug']})")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()
