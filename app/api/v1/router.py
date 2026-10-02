from __future__ import annotations
from fastapi import APIRouter

from app.api.v1.routes import (
    ai,
    assets,
    attendance,
    auth,
    communication,
    company_setup,
    dashboard,
    documents,
    employees,
    exit,
    expenses,
    health,
    helpdesk,
    leaves,
    onboarding,
    payroll,
    performance,
    permissions,
    recruitment,
    reports,
    roles,
    shifts,
    surveys,
    tenants,
    timesheets,
    training,
    travel,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(tenants.router)
api_router.include_router(roles.router)
api_router.include_router(permissions.router)
api_router.include_router(company_setup.router)
api_router.include_router(dashboard.router)
api_router.include_router(employees.router)
api_router.include_router(attendance.router)
api_router.include_router(shifts.router)
api_router.include_router(leaves.router)
api_router.include_router(payroll.router)
api_router.include_router(recruitment.router)
api_router.include_router(onboarding.router)
api_router.include_router(performance.router)
api_router.include_router(ai.router)
api_router.include_router(documents.router)
api_router.include_router(helpdesk.router)
api_router.include_router(reports.router)
api_router.include_router(expenses.router)
api_router.include_router(travel.router)
api_router.include_router(assets.router)
api_router.include_router(communication.router)
api_router.include_router(exit.router)
api_router.include_router(timesheets.router)
api_router.include_router(training.router)
api_router.include_router(surveys.router)
