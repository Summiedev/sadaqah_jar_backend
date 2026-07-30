"""Service layer for user goals and monthly reviews."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.goals import repository as repo
from app.goals.models import GoalStatus, UserGoal
from app.goals.schemas import (
    GoalCreate,
    GoalResponse,
    GoalListResponse,
    MonthlyReviewCheck,
    MonthlyReviewCreate,
    MonthlyReviewResponse,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _goal_to_response(goal: UserGoal) -> GoalResponse:
    progress = (
        (goal.acts_done / goal.acts_target) if goal.acts_target > 0 else 0.0
    )
    return GoalResponse(
        id=goal.id,
        title=goal.title,
        subtitle=goal.subtitle,
        acts_target=goal.acts_target,
        acts_done=goal.acts_done,
        status=goal.status.value,
        completed_at=goal.completed_at,
        month=goal.month,
        created_at=goal.created_at,
        progress=min(progress, 1.0),
    )


# ---------------------------------------------------------------------------
# User Goals
# ---------------------------------------------------------------------------


def create_goal(db: Session, user_id: int, data: GoalCreate) -> GoalResponse:
    goal = repo.create_goal(
        db,
        user_id=user_id,
        title=data.title,
        acts_target=data.acts_target,
        subtitle=data.subtitle,
        month=data.month,
    )
    return _goal_to_response(goal)


def get_goal(db: Session, goal_id: int, user_id: int) -> GoalResponse | None:
    goal = repo.get_goal(db, goal_id, user_id)
    if goal is None:
        return None
    return _goal_to_response(goal)


def list_goals(
    db: Session,
    user_id: int,
    status: str | None = None,
    month: str | None = None,
) -> GoalListResponse:
    goals = repo.get_user_goals(db, user_id, status, month)
    counts = repo.get_user_goal_counts(db, user_id)
    return GoalListResponse(
        goals=[_goal_to_response(g) for g in goals],
        total=counts["total"],
        active_count=counts["active_count"],
        completed_count=counts["completed_count"],
    )


def update_progress(
    db: Session, goal_id: int, user_id: int, acts_done: int
) -> GoalResponse | None:
    goal = repo.update_goal_progress(db, goal_id, user_id, acts_done)
    if goal is None:
        return None
    return _goal_to_response(goal)


def update_status(
    db: Session, goal_id: int, user_id: int, status: str
) -> GoalResponse | None:
    goal = repo.update_goal_status(db, goal_id, user_id, GoalStatus(status))
    if goal is None:
        return None
    return _goal_to_response(goal)


def delete_goal(db: Session, goal_id: int, user_id: int) -> bool:
    return repo.delete_goal(db, goal_id, user_id)


# ---------------------------------------------------------------------------
# Monthly Reviews
# ---------------------------------------------------------------------------


def check_review_due(db: Session, user_id: int) -> MonthlyReviewCheck:
    now = _utcnow()
    current_month = f"{now.year:04d}-{now.month:02d}"

    # Check if already reviewed this month
    existing = repo.get_monthly_review(db, user_id, current_month)
    if existing:
        return MonthlyReviewCheck(
            due=False,
            year_month=current_month,
            last_review=MonthlyReviewResponse(
                id=existing.id,
                year_month=existing.year_month,
                goals_completed=existing.goals_completed,
                goals_active=existing.goals_active,
                total_acts_done=existing.total_acts_done,
                streak_at_review=existing.streak_at_review,
                action_taken=existing.action_taken,
                notes=existing.notes,
                created_at=existing.created_at,
            ),
        )

    # Check if user has active goals this month
    goals = repo.get_user_goals(db, user_id, status="active", month=current_month)

    # Review is due if:
    # 1. No review exists for this month
    # 2. User has goals with activity
    # 3. At least 7 days into the month
    due = (
        existing is None
        and len(goals) > 0
        and now.day >= 7
    )

    latest_review = repo.get_latest_monthly_review(db, user_id)

    return MonthlyReviewCheck(
        due=due,
        year_month=current_month,
        last_review=(
            MonthlyReviewResponse(
                id=latest_review.id,
                year_month=latest_review.year_month,
                goals_completed=latest_review.goals_completed,
                goals_active=latest_review.goals_active,
                total_acts_done=latest_review.total_acts_done,
                streak_at_review=latest_review.streak_at_review,
                action_taken=latest_review.action_taken,
                notes=latest_review.notes,
                created_at=latest_review.created_at,
            )
            if latest_review
            else None
        ),
    )


def submit_review(db: Session, user_id: int, data: MonthlyReviewCreate) -> MonthlyReviewResponse:
    now = _utcnow()
    current_month = f"{now.year:04d}-{now.month:02d}"

    # Check if already reviewed
    existing = repo.get_monthly_review(db, user_id, current_month)
    if existing:
        raise ValueError("Already reviewed for this month")

    # Get goal counts
    goals = repo.get_user_goals(db, user_id, month=current_month)
    active_count = sum(1 for g in goals if g.status == GoalStatus.ACTIVE)
    completed_count = sum(1 for g in goals if g.status == GoalStatus.COMPLETED)

    review = repo.create_monthly_review(
        db,
        user_id=user_id,
        year_month=current_month,
        goals_completed=data.goals_completed or completed_count,
        goals_active=data.goals_active or active_count,
        total_acts_done=data.total_acts_done,
        streak_at_review=data.streak_at_review,
        action_taken=data.action_taken,
        notes=data.notes,
    )

    return MonthlyReviewResponse(
        id=review.id,
        year_month=review.year_month,
        goals_completed=review.goals_completed,
        goals_active=review.goals_active,
        total_acts_done=review.total_acts_done,
        streak_at_review=review.streak_at_review,
        action_taken=review.action_taken,
        notes=review.notes,
        created_at=review.created_at,
    )