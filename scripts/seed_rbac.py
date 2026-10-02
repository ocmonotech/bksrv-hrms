from __future__ import annotations

"""Seed global permissions catalog and system roles."""

from app.core.database import SessionLocal
from app.services.rbac_seed_service import RBACSeedService


def seed_rbac() -> None:
    db = SessionLocal()
    try:
        RBACSeedService(db).seed_all()
        db.commit()
        print("RBAC seed completed: permissions catalog and system roles.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_rbac()
