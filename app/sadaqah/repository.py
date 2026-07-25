"""Sadaqah domain repository."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.sadaqah.models import (
    ActivityCompletion,
    ActivityContext,
    ActivitySession,
    ActivityStreak,
    ActivityType,
)


class ActivityCompletionRepository:
    def create(self, db: Session, payload: dict) -> ActivityCompletion:
        completion = ActivityCompletion(**payload)
        db.add(completion)
        db.flush()
        db.refresh(completion)
        return completion

    def get(self, db: Session, completion_id: int, user_id: int) -> ActivityCompletion | None:
        return db.scalar(
            select(ActivityCompletion).where(
                ActivityCompletion.id == completion_id,
                ActivityCompletion.user_id == user_id,
                ActivityCompletion.deleted_at.is_(None),
            )
        )

    def list(
        self,
        db: Session,
        user_id: int,
        activity_type: Optional[ActivityType] = None,
        context: Optional[ActivityContext] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ActivityCompletion], int]:
        query = select(ActivityCompletion).where(
            ActivityCompletion.user_id == user_id,
            ActivityCompletion.deleted_at.is_(None),
        )

        if activity_type is not None:
            query = query.where(ActivityCompletion.activity_type == activity_type)
        if context is not None:
            query = query.where(ActivityCompletion.context == context)
        if start_date is not None:
            query = query.where(ActivityCompletion.completed_at >= start_date)
        if end_date is not None:
            query = query.where(ActivityCompletion.completed_at <= end_date + timedelta(days=1))

        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

        rows = db.scalars(
            query.order_by(ActivityCompletion.completed_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

        return list(rows), total

    def get_by_date_range(
        self, db: Session, user_id: int, start_date: date, end_date: date
    ) -> list[ActivityCompletion]:
        return list(
            db.scalars(
                select(ActivityCompletion).where(
                    ActivityCompletion.user_id == user_id,
                    ActivityCompletion.completed_at >= start_date,
                    ActivityCompletion.completed_at < end_date + timedelta(days=1),
                    ActivityCompletion.deleted_at.is_(None),
                ).order_by(ActivityCompletion.completed_at.desc())
            )
        )

    def count_by_type(
        self, db: Session, user_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> dict[str, int]:
        query = select(
            ActivityCompletion.activity_type,
            func.count(ActivityCompletion.id).label("count"),
        ).where(
            ActivityCompletion.user_id == user_id,
            ActivityCompletion.deleted_at.is_(None),
        )
        if start_date is not None:
            query = query.where(ActivityCompletion.completed_at >= start_date)
        if end_date is not None:
            query = query.where(ActivityCompletion.completed_at < end_date + timedelta(days=1))

        query = query.group_by(ActivityCompletion.activity_type)
        rows = db.execute(query).all()
        return {str(row[0].value): row[1] for row in rows}


class ActivitySessionRepository:
    def create(self, db: Session, payload: dict) -> ActivitySession:
        session = ActivitySession(**payload)
        db.add(session)
        db.flush()
        db.refresh(session)
        return session

    def get(self, db: Session, session_id: int, user_id: int) -> ActivitySession | None:
        return db.scalar(
            select(ActivitySession).where(
                ActivitySession.id == session_id,
                ActivitySession.user_id == user_id,
                ActivitySession.deleted_at.is_(None),
            )
        )

    def list(
        self,
        db: Session,
        user_id: int,
        activity_type: Optional[ActivityType] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ActivitySession], int]:
        query = select(ActivitySession).where(
            ActivitySession.user_id == user_id,
            ActivitySession.deleted_at.is_(None),
        )

        if activity_type is not None:
            query = query.where(ActivitySession.activity_type == activity_type)
        if start_date is not None:
            query = query.where(ActivitySession.started_at >= start_date)
        if end_date is not None:
            query = query.where(ActivitySession.started_at <= end_date + timedelta(days=1))

        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

        rows = db.scalars(
            query.order_by(ActivitySession.started_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

        return list(rows), total

    def get_in_progress(self, db: Session, user_id: int, activity_type: Optional[ActivityType] = None) -> ActivitySession | None:
        query = select(ActivitySession).where(
            ActivitySession.user_id == user_id,
            ActivitySession.ended_at.is_(None),
            ActivitySession.deleted_at.is_(None),
        )
        if activity_type is not None:
            query = query.where(ActivitySession.activity_type == activity_type)
        return db.scalar(query.order_by(ActivitySession.started_at.desc()))


class ActivityStreakRepository:
    def get(self, db: Session, user_id: int, activity_type: ActivityType) -> ActivityStreak | None:
        return db.scalar(
            select(ActivityStreak).where(
                ActivityStreak.user_id == user_id,
                ActivityStreak.activity_type == activity_type,
            )
        )

    def get_or_create(self, db: Session, user_id: int, activity_type: ActivityType) -> ActivityStreak:
        streak = self.get(db, user_id, activity_type)
        if streak is None:
            streak = ActivityStreak(user_id=user_id, activity_type=activity_type)
            db.add(streak)
            db.flush()
            db.refresh(streak)
        return streak

    def update(self, db: Session, streak: ActivityStreak, payload: dict) -> ActivityStreak:
        for key, value in payload.items():
            if hasattr(streak, key):
                setattr(streak, key, value)
        db.flush()
        db.refresh(streak)
        return streak

    def list_for_user(self, db: Session, user_id: int) -> list[ActivityStreak]:
        return list(
            db.scalars(
                select(ActivityStreak)
                .where(ActivityStreak.user_id == user_id)
                .order_by(ActivityStreak.current_streak.desc())
            )
        )
