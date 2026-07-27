"""Base repository with reusable CRUD patterns."""

from datetime import datetime, timezone
from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from app.core.mixins import SoftDeleteMixin, TimestampMixin

ModelType = TypeVar("ModelType", bound=TimestampMixin)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    def get(self, db: Session, id: int) -> ModelType | None:
        return db.get(self.model, id)

    def list(
        self,
        db: Session,
        limit: int = 20,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> tuple[list[ModelType], int]:
        query = db.query(self.model)
        if issubclass(self.model, SoftDeleteMixin) and not include_deleted:
            query = query.filter(self.model.deleted_at.is_(None))

        total = query.count()
        rows = query.offset(offset).limit(limit).all()
        return rows, total

    def create(self, db: Session, payload: dict) -> ModelType:
        instance = self.model(**payload)
        db.add(instance)
        db.flush()
        db.refresh(instance)
        return instance

    def update(self, db: Session, instance: ModelType, payload: dict) -> ModelType:
        for key, value in payload.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        db.flush()
        db.commit()
        db.refresh(instance)
        return instance

    def delete(self, db: Session, instance: ModelType) -> None:
        if issubclass(self.model, SoftDeleteMixin):
            instance.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.flush()
        else:
            db.delete(instance)
            db.flush()
