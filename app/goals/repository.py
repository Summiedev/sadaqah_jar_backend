"""Goals domain repository layer.

Pure persistence — no business logic, no permission checks.
Uses synchronous SQLAlchemy sessions.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.goals.models import GoalStatus, MonthlyGoalReview, UserGoal


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# User Goals
# ---------------------------------------------------------------------------


def create_goal(
    db: Session,
    user_id: int,
    title: str,
    acts_target: int,
    subtitle: str | None = None,
    month: str | None = None,
) -> UserGoal:
    goal = UserGoal(
        user_id=user_id,
        title=title,
        subtitle=subtitle,
        acts_target=acts_target,
        month=month,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def get_goal(db: Session, goal_id: int, user_id: int) -> UserGoal | None:
    return db.scalar(
        select(UserGoal).where(
            UserGoal.id == goal_id,
            UserGoal.user_id == user_id,
            UserGoal.deleted_at.is_(None),
        )
    )


def get_user_goals(
    db: Session,
    user_id: int,
    status: str | None = None,
    month: str | None = None,
) -> list[UserGoal]:
    query = select(UserGoal).where(
        UserGoal.user_id == user_id,
        UserGoal.deleted_at.is_(None),
    )
    if status:
        query = query.where(UserGoal.status == GoalStatus(status))
    if month:
        query = query.where(UserGoal.month == month)
    query = query.order_by(UserGoal.created_at.desc())
    return list(db.scalars(query).all())


def get_user_goal_counts(db: Session, user_id: int) -> dict:
    active = db.scalar(
        select(func.count()).where(
            UserGoal.user_id == user_id,
            UserGoal.deleted_at.is_(None),
            UserGoal.status == GoalStatus.ACTIVE,
        )
    )
    completed = db.scalar(
        select(func.count()).where(
            UserGoal.user_id == user_id,
            UserGoal.deleted_at.is_(None),
            UserGoal.status == GoalStatus.COMPLETED,
        )
    )
    total = db.scalar(
        select(func.count()).where(
            UserGoal.user_id == user_id,
            UserGoal.deleted_at.is_(None),
        )
    )
    return {
        "active_count": active or 0,
        "completed_count": completed or 0,
        "total": total or 0,
    }


def update_goal_progress(
    db: Session, goal_id: int, user_id: int, acts_done: int
) -> UserGoal | None:
    goal = get_goal(db, goal_id, user_id)
    if goal is None:
        return None
    goal.acts_done = acts_done
    if acts_done >= goal.acts_target and goal.status == GoalStatus.ACTIVE:
        goal.status = GoalStatus.COMPLETED
        goal.completed_at = _utcnow()
    goal.updated_at = _utcnow()
    db.commit()
    db.refresh(goal)
    return goal


def update_goal_fields(
    db: Session,
    goal_id: int,
    user_id: int,
    title: str | None = None,
    subtitle: str | None = None,
    acts_target: int | None = None,
) -> UserGoal | None:
    goal = get_goal(db, goal_id, user_id)
    if goal is None:
        return None
    if title is not None:
        goal.title = title
    if subtitle is not None:
        goal.subtitle = subtitle
    if acts_target is not None:
        goal.acts_target = acts_target
    goal.updated_at = _utcnow()
    db.commit()
    db.refresh(goal)
    return goal


def update_goal_status(
    db: Session, goal_id: int, user_id: int, status: GoalStatus
) -> UserGoal | None:
    goal = get_goal(db, goal_id, user_id)
    if goal is None:
        return None
    goal.status = status
    if status == GoalStatus.COMPLETED:
        goal.completed_at = _utcnow()
    goal.updated_at = _utcnow()
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, goal_id: int, user_id: int) -> bool:
    goal = get_goal(db, goal_id, user_id)
    if goal is None:
        return False
    goal.deleted_at = _utcnow()
    db.commit()
    return True


def increment_monthly_goals(db: Session, user_id: int, month: str) -> list[UserGoal]:
    """Increment acts_done for all active goals in a given month."""
    goals = list(
        db.scalars(
            select(UserGoal).where(
                UserGoal.user_id == user_id,
                UserGoal.month == month,
                UserGoal.status == GoalStatus.ACTIVE,
                UserGoal.deleted_at.is_(None),
            )
        ).all()
    )
    now = _utcnow()
    for goal in goals:
        goal.acts_done += 1
        if goal.acts_done >= goal.acts_target:
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = now
        goal.updated_at = now
    db.commit()
    for goal in goals:
        db.refresh(goal)
    return goals


# ---------------------------------------------------------------------------
# Monthly Reviews
# ---------------------------------------------------------------------------


def create_monthly_review(
    db: Session,
    user_id: int,
    year_month: str,
    goals_completed: int,
    goals_active: int,
    total_acts_done: int,
    streak_at_review: int,
    action_taken: str | None = None,
    notes: str | None = None,
) -> MonthlyGoalReview:
    review = MonthlyGoalReview(
        user_id=user_id,
        year_month=year_month,
        goals_completed=goals_completed,
        goals_active=goals_active,
        total_acts_done=total_acts_done,
        streak_at_review=streak_at_review,
        action_taken=action_taken,
        notes=notes,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_monthly_review(db: Session, user_id: int, year_month: str) -> MonthlyGoalReview | None:
    return db.scalar(
        select(MonthlyGoalReview).where(
            MonthlyGoalReview.user_id == user_id,
            MonthlyGoalReview.year_month == year_month,
        )
    )


def get_latest_monthly_review(db: Session, user_id: int) -> MonthlyGoalReview | None:
    return db.scalar(
        select(MonthlyGoalReview)
        .where(MonthlyGoalReview.user_id == user_id)
        .order_by(MonthlyGoalReview.year_month.desc())
        .limit(1)
    )