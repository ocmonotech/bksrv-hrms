from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.shift import Roster, Shift, ShiftSwapRequest
from app.repositories.attendance_repository import RosterRepository, ShiftRepository
from app.repositories.tenant_scoped_repository import TenantScopedRepository
from app.schemas.shift import RosterResponse, ShiftResponse, ShiftSwapResponse
from app.services.company_setup.base import TenantScopedCRUDService


def shift_service(db: Session) -> TenantScopedCRUDService:
    return TenantScopedCRUDService(
        db,
        ShiftRepository(db),
        response_schema=ShiftResponse,
        resource_type="shift",
    )


def roster_service(db: Session) -> TenantScopedCRUDService:
    return TenantScopedCRUDService(
        db,
        RosterRepository(db),
        response_schema=RosterResponse,
        resource_type="roster",
    )


def shift_swap_service(db: Session) -> TenantScopedCRUDService:
    return TenantScopedCRUDService(
        db,
        TenantScopedRepository(db, ShiftSwapRequest),
        response_schema=ShiftSwapResponse,
        resource_type="shift_swap_request",
    )
