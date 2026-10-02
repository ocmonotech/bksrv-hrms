from __future__ import annotations
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.mixins import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, db: Session, model: type[ModelT]) -> None:
        self.db = db
        self.model = model

    def get_by_id(self, id: UUID) -> ModelT | None:
        return self.db.get(self.model, str(id))

    def add(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        self.db.flush()
        return entity

    def delete(self, entity: ModelT) -> None:
        self.db.delete(entity)
        self.db.flush()
