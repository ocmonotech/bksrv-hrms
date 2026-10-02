from __future__ import annotations

import json
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tenant_setting import TenantSetting


class TenantSettingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, tenant_id: UUID, key: str) -> Optional[TenantSetting]:
        stmt = select(TenantSetting).where(
            TenantSetting.tenant_id == str(tenant_id),
            TenantSetting.key == key,
        )
        return self.db.scalar(stmt)

    def upsert(
        self,
        tenant_id: UUID,
        key: str,
        value: dict[str, Any] | list[Any],
    ) -> TenantSetting:
        entity = self.get(tenant_id, key)
        payload = json.dumps(value)
        if entity:
            entity.value_json = payload
        else:
            entity = TenantSetting(
                tenant_id=str(tenant_id),
                key=key,
                value_json=payload,
            )
            self.db.add(entity)
        self.db.flush()
        return entity

    def get_value(self, tenant_id: UUID, key: str, default: Any = None) -> Any:
        entity = self.get(tenant_id, key)
        if not entity:
            return default
        try:
            return json.loads(entity.value_json or "{}")
        except json.JSONDecodeError:
            return default
