from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


def send_announcement_task(
    tenant_id: str,
    announcement_id: str,
    actor_id: str,
    channels: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Background task: send announcement via email/SMS/WhatsApp."""
    from app.core.database import SessionLocal
    from app.services.extended_modules_service import CommunicationService

    db = SessionLocal()
    try:
        service = CommunicationService(db)
        result = service.send_announcement(
            UUID(tenant_id),
            UUID(announcement_id),
            actor_id=UUID(actor_id),
            channels=channels,
        )
        return {"status": "ok", "announcement_id": str(result.id)}
    finally:
        db.close()


def send_payslip_notification_task(
    tenant_id: str,
    employee_id: str,
    month: str,
) -> dict[str, Any]:
    """Background task: notify employee that payslip is ready."""
    from app.core.database import SessionLocal
    from app.repositories.employee_repository import EmployeeRepository
    from app.services.notification_service import notify_channels

    db = SessionLocal()
    try:
        employee = EmployeeRepository(db).get_by_id(UUID(employee_id), UUID(tenant_id))
        if not employee:
            return {"status": "skipped", "reason": "employee_not_found"}
        subject = f"Payslip ready — {month}"
        body = f"Your payslip for {month} is now available in OCMono HRMS."
        notify_channels(
            email=employee.email,
            mobile=employee.mobile,
            subject=subject,
            body=body,
            channels=["email", "in_app"],
        )
        return {"status": "ok", "employee_id": employee_id}
    finally:
        db.close()


def biometric_sync_task(tenant_id: str, device_id: str, actor_id: str) -> dict[str, Any]:
    """Background task: sync punches from biometric device."""
    from app.core.database import SessionLocal
    from app.services.attendance_service import AttendanceService

    db = SessionLocal()
    try:
        result = AttendanceService(db).sync_biometric_device(
            UUID(tenant_id),
            UUID(device_id),
            actor_id=UUID(actor_id),
            meta={},
        )
        return {
            "status": "ok",
            "records_synced": result.records_synced,
            "device_id": device_id,
        }
    finally:
        db.close()
