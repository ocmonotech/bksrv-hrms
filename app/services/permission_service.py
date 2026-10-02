from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.permission_repository import PermissionRepository
from app.schemas.role import PermissionCatalogItem, PermissionCatalogResponse


class PermissionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PermissionRepository(db)

    def list_permissions(self) -> PermissionCatalogResponse:
        items = self.repo.list_all()
        grouped: dict[str, list[str]] = {}
        for perm in items:
            grouped.setdefault(perm.module, []).append(perm.action)

        catalog = [
            PermissionCatalogItem(module=module, actions=sorted(actions))
            for module, actions in sorted(grouped.items())
        ]
        return PermissionCatalogResponse(
            permissions=catalog,
            total=len(items),
        )
