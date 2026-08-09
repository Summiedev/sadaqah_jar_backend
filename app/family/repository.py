"""Family domain repository layer.

Pure persistence — no business logic, no permission checks.
Each aggregate root has its own set of repository functions.
"""

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.family.models import (
    Family,
    FamilyMember,
    FamilyInvitation,
    FamilyGoal,
    FamilyGoalMilestone,
    PrayerRequest,
    PrayerComment,
    PrayerRequestResponse,
    FamilyReflection,
    FamilyReflectionComment,
    ReflectionEncouragement,
    FamilyActivity,
    FamilySettings,
    EventType,
    FamilyRole,
    InvitationStatus,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Family
# ---------------------------------------------------------------------------


def get_family_by_id(db: Session, family_id: int) -> Family | None:
    return db.scalar(
        select(Family).where(Family.id == family_id, Family.deleted_at.is_(None))
    )


def get_family_by_invite_code(db: Session, invite_code: str) -> Family | None:
    return db.scalar(
        select(Family).where(
            Family.invite_code == invite_code, Family.deleted_at.is_(None)
        )
    )


def list_user_families(db: Session, user_id: int) -> Sequence[Family]:
    """Return all active families the user is a member of."""
    return db.scalars(
        select(Family)
        .join(FamilyMember, FamilyMember.family_id == Family.id)
        .where(
            FamilyMember.user_id == user_id,
            FamilyMember.deleted_at.is_(None),
            Family.deleted_at.is_(None),
        )
        .order_by(Family.created_at.desc())
    ).all()


def create_family(
    db: Session,
    *,
    name: str,
    invite_code: str,
    created_by: int,
    cover_icon: str | None = None,
) -> Family:
    family = Family(
        name=name,
        invite_code=invite_code,
        created_by=created_by,
        cover_icon=cover_icon,
    )
    db.add(family)
    db.flush()
    # Create default settings
    db.add(FamilySettings(family_id=family.id))
    db.flush()
    return family


def update_family(
    db: Session,
    family: Family,
    *,
    name: str | None = None,
    cover_icon: str | None = None,
) -> Family:
    if name is not None:
        family.name = name
    if cover_icon is not None:
        family.cover_icon = cover_icon
    db.add(family)
    db.flush()
    return family


def soft_delete_family(db: Session, family: Family) -> None:
    family.deleted_at = _utcnow()
    db.add(family)
    db.flush()


def count_user_families(db: Session, user_id: int) -> int:
    return (
        db.scalar(
            select(func.count(Family.id))
            .join(FamilyMember, FamilyMember.family_id == Family.id)
            .where(
                FamilyMember.user_id == user_id,
                FamilyMember.deleted_at.is_(None),
                Family.deleted_at.is_(None),
            )
        )
        or 0
    )


# ---------------------------------------------------------------------------
# FamilyMember
# ---------------------------------------------------------------------------


def get_member(db: Session, family_id: int, user_id: int) -> FamilyMember | None:
    return db.scalar(
        select(FamilyMember).where(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user_id,
            FamilyMember.deleted_at.is_(None),
        )
    )


def get_member_by_id(db: Session, member_id: int) -> FamilyMember | None:
    return db.scalar(
        select(FamilyMember).where(
            FamilyMember.id == member_id,
            FamilyMember.deleted_at.is_(None),
        )
    )


def list_members(db: Session, family_id: int) -> Sequence[FamilyMember]:
    return db.scalars(
        select(FamilyMember)
        .where(
            FamilyMember.family_id == family_id,
            FamilyMember.deleted_at.is_(None),
        )
        .order_by(FamilyMember.joined_at.asc())
    ).all()


def add_member(
    db: Session,
    *,
    family_id: int,
    user_id: int,
    role: FamilyRole = FamilyRole.MEMBER,
) -> FamilyMember:
    member = FamilyMember(family_id=family_id, user_id=user_id, role=role)
    db.add(member)
    db.flush()
    return member


def update_member_role(
    db: Session, member: FamilyMember, role: FamilyRole
) -> FamilyMember:
    member.role = role
    db.add(member)
    db.flush()
    return member


def soft_delete_member(db: Session, member: FamilyMember) -> None:
    member.deleted_at = _utcnow()
    db.add(member)
    db.flush()


def count_family_members(db: Session, family_id: int) -> int:
    return (
        db.scalar(
            select(func.count(FamilyMember.id)).where(
                FamilyMember.family_id == family_id,
                FamilyMember.deleted_at.is_(None),
            )
        )
        or 0
    )


# ---------------------------------------------------------------------------
# FamilyInvitation
# ---------------------------------------------------------------------------


def get_invitation_by_code(db: Session, invite_code: str) -> FamilyInvitation | None:
    return db.scalar(
        select(FamilyInvitation).where(
            FamilyInvitation.invite_code == invite_code,
            FamilyInvitation.deleted_at.is_(None),
        )
    )


def get_invitation_by_id(db: Session, invitation_id: int) -> FamilyInvitation | None:
    return db.scalar(
        select(FamilyInvitation).where(
            FamilyInvitation.id == invitation_id,
            FamilyInvitation.deleted_at.is_(None),
        )
    )


def list_family_invitations(
    db: Session, family_id: int, status: InvitationStatus | None = None
) -> Sequence[FamilyInvitation]:
    query = select(FamilyInvitation).where(
        FamilyInvitation.family_id == family_id,
        FamilyInvitation.deleted_at.is_(None),
    )
    if status is not None:
        query = query.where(FamilyInvitation.status == status)
    return db.scalars(query.order_by(FamilyInvitation.created_at.desc())).all()


def create_invitation(
    db: Session,
    *,
    family_id: int,
    invited_by: int,
    invite_code: str,
    expires_at: datetime,
) -> FamilyInvitation:
    invitation = FamilyInvitation(
        family_id=family_id,
        invited_by=invited_by,
        invite_code=invite_code,
        expires_at=expires_at,
    )
    db.add(invitation)
    db.flush()
    return invitation


def update_invitation_status(
    db: Session, invitation: FamilyInvitation, status: InvitationStatus
) -> FamilyInvitation:
    invitation.status = status
    db.add(invitation)
    db.flush()
    return invitation


def soft_delete_invitation(db: Session, invitation: FamilyInvitation) -> None:
    invitation.deleted_at = _utcnow()
    db.add(invitation)
    db.flush()


def expire_pending_invitations(db: Session, family_id: int) -> int:
    now = _utcnow()
    count = (
        db.query(FamilyInvitation)
        .filter(
            FamilyInvitation.family_id == family_id,
            FamilyInvitation.status == InvitationStatus.PENDING,
            FamilyInvitation.expires_at <= now,
            FamilyInvitation.deleted_at.is_(None),
        )
        .update(
            {"status": InvitationStatus.EXPIRED},
            synchronize_session=False,
        )
    )
    db.commit()
    return count


# ---------------------------------------------------------------------------
# FamilyGoal
# ---------------------------------------------------------------------------


def get_goal_by_id(db: Session, goal_id: int) -> FamilyGoal | None:
    return db.scalar(
        select(FamilyGoal).where(
            FamilyGoal.id == goal_id,
            FamilyGoal.deleted_at.is_(None),
        )
    )


def list_family_goals(
    db: Session, family_id: int, include_archived: bool = False
) -> Sequence[FamilyGoal]:
    query = select(FamilyGoal).where(
        FamilyGoal.family_id == family_id,
        FamilyGoal.deleted_at.is_(None),
    )
    if not include_archived:
        query = query.where(FamilyGoal.is_archived.is_(False))
    return db.scalars(query.order_by(FamilyGoal.created_at.desc())).all()


def create_goal(
    db: Session,
    *,
    family_id: int,
    created_by: int,
    title: str,
    acts_target: int,
    subtitle: str | None = None,
) -> FamilyGoal:
    goal = FamilyGoal(
        family_id=family_id,
        created_by=created_by,
        title=title,
        subtitle=subtitle,
        acts_target=acts_target,
    )
    db.add(goal)
    db.flush()
    return goal


def update_goal(
    db: Session,
    goal: FamilyGoal,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    acts_target: int | None = None,
    acts_done: int | None = None,
) -> FamilyGoal:
    if title is not None:
        goal.title = title
    if subtitle is not None:
        goal.subtitle = subtitle
    if acts_target is not None:
        goal.acts_target = acts_target
    if acts_done is not None:
        goal.acts_done = acts_done
    goal.version += 1
    db.add(goal)
    db.flush()
    return goal


def complete_goal(db: Session, goal: FamilyGoal) -> FamilyGoal:
    goal.completed_at = _utcnow()
    goal.version += 1
    db.add(goal)
    db.flush()
    return goal


def archive_goal(db: Session, goal: FamilyGoal) -> FamilyGoal:
    goal.is_archived = True
    goal.version += 1
    db.add(goal)
    db.flush()
    return goal


# ---------------------------------------------------------------------------
# FamilyGoalMilestone
# ---------------------------------------------------------------------------


def get_milestone_by_id(db: Session, milestone_id: int) -> FamilyGoalMilestone | None:
    return db.scalar(
        select(FamilyGoalMilestone).where(
            FamilyGoalMilestone.id == milestone_id,
            FamilyGoalMilestone.deleted_at.is_(None),
        )
    )


def list_milestones(db: Session, goal_id: int) -> Sequence[FamilyGoalMilestone]:
    return db.scalars(
        select(FamilyGoalMilestone)
        .where(
            FamilyGoalMilestone.goal_id == goal_id,
            FamilyGoalMilestone.deleted_at.is_(None),
        )
        .order_by(FamilyGoalMilestone.sort_order.asc(), FamilyGoalMilestone.id.asc())
    ).all()


def create_milestone(
    db: Session,
    *,
    goal_id: int,
    title: str,
    target_value: int,
    description: str | None = None,
    sort_order: int = 0,
) -> FamilyGoalMilestone:
    milestone = FamilyGoalMilestone(
        goal_id=goal_id,
        title=title,
        description=description,
        target_value=target_value,
        sort_order=sort_order,
    )
    db.add(milestone)
    db.flush()
    return milestone


def update_milestone(
    db: Session,
    milestone: FamilyGoalMilestone,
    *,
    title: str | None = None,
    description: str | None = None,
    target_value: int | None = None,
    current_value: int | None = None,
    sort_order: int | None = None,
) -> FamilyGoalMilestone:
    if title is not None:
        milestone.title = title
    if description is not None:
        milestone.description = description
    if target_value is not None:
        milestone.target_value = target_value
    if current_value is not None:
        milestone.current_value = current_value
    if sort_order is not None:
        milestone.sort_order = sort_order
    db.add(milestone)
    db.flush()
    return milestone


def achieve_milestone(
    db: Session, milestone: FamilyGoalMilestone
) -> FamilyGoalMilestone:
    milestone.is_achieved = True
    milestone.achieved_at = _utcnow()
    db.add(milestone)
    db.flush()
    return milestone


def soft_delete_milestone(db: Session, milestone: FamilyGoalMilestone) -> None:
    milestone.deleted_at = _utcnow()
    db.add(milestone)
    db.flush()


def increment_goal_acts_done(db: Session, goal: FamilyGoal) -> FamilyGoal:
    goal.acts_done = (goal.acts_done or 0) + 1
    goal.version += 1
    db.add(goal)
    db.flush()
    return goal


def soft_delete_goal(db: Session, goal: FamilyGoal) -> None:
    goal.deleted_at = _utcnow()
    db.add(goal)
    db.flush()


# ---------------------------------------------------------------------------
# PrayerRequest
# ---------------------------------------------------------------------------


def get_prayer_request_by_id(db: Session, prayer_id: int) -> PrayerRequest | None:
    return db.scalar(
        select(PrayerRequest).where(
            PrayerRequest.id == prayer_id,
            PrayerRequest.deleted_at.is_(None),
        )
    )


def list_prayer_requests(
    db: Session,
    family_id: int,
    include_answered: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[Sequence[PrayerRequest], int]:
    query = select(PrayerRequest).where(
        PrayerRequest.family_id == family_id,
        PrayerRequest.deleted_at.is_(None),
    )
    if not include_answered:
        query = query.where(PrayerRequest.is_answered.is_(False))

    total = (
        db.scalar(
            select(func.count(PrayerRequest.id)).where(
                PrayerRequest.family_id == family_id,
                PrayerRequest.deleted_at.is_(None),
                PrayerRequest.is_answered.is_(False),
            )
        )
        or 0
    )

    rows = db.scalars(
        query.order_by(PrayerRequest.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return rows, total


def create_prayer_request(
    db: Session,
    *,
    family_id: int,
    author_id: int,
    text: str,
    is_private: bool = False,
) -> PrayerRequest:
    prayer = PrayerRequest(
        family_id=family_id,
        author_id=author_id,
        text=text,
        is_private=is_private,
    )
    db.add(prayer)
    db.flush()
    return prayer


def mark_prayer_answered(db: Session, prayer: PrayerRequest) -> PrayerRequest:
    prayer.is_answered = True
    db.add(prayer)
    db.flush()
    return prayer


def soft_delete_prayer_request(db: Session, prayer: PrayerRequest) -> None:
    prayer.deleted_at = _utcnow()
    db.add(prayer)
    db.flush()


# ---------------------------------------------------------------------------
# PrayerRequestResponse
# ---------------------------------------------------------------------------


def get_prayer_response_counts(db: Session, prayer_request_id: int) -> dict[str, int]:
    rows = db.execute(
        select(
            PrayerRequestResponse.response_type,
            func.count(PrayerRequestResponse.id),
        )
        .where(
            PrayerRequestResponse.prayer_request_id == prayer_request_id,
        )
        .group_by(PrayerRequestResponse.response_type)
    ).all()
    return {row[0].value: row[1] for row in rows}


def get_prayer_comment_count(db: Session, prayer_request_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(PrayerComment.id)).where(
                PrayerComment.prayer_request_id == prayer_request_id,
                PrayerComment.deleted_at.is_(None),
            )
        )
        or 0
    )


def add_prayer_response(
    db: Session,
    *,
    prayer_request_id: int,
    user_id: int,
    response_type: str,
) -> PrayerRequestResponse | None:
    """Add a response. Returns None if already exists (unique constraint)."""
    from sqlalchemy.exc import IntegrityError

    try:
        response = PrayerRequestResponse(
            prayer_request_id=prayer_request_id,
            user_id=user_id,
            response_type=response_type,
        )
        db.add(response)
        db.flush()
        return response
    except IntegrityError:
        db.rollback()
        return None


# ---------------------------------------------------------------------------
# PrayerComment
# ---------------------------------------------------------------------------


def get_prayer_comment_by_id(db: Session, comment_id: int) -> PrayerComment | None:
    return db.scalar(
        select(PrayerComment).where(
            PrayerComment.id == comment_id,
            PrayerComment.deleted_at.is_(None),
        )
    )


def list_prayer_comments(
    db: Session, prayer_request_id: int, limit: int = 50, offset: int = 0
) -> tuple[Sequence[PrayerComment], int]:
    total = (
        db.scalar(
            select(func.count(PrayerComment.id)).where(
                PrayerComment.prayer_request_id == prayer_request_id,
                PrayerComment.deleted_at.is_(None),
            )
        )
        or 0
    )

    rows = db.scalars(
        select(PrayerComment)
        .where(
            PrayerComment.prayer_request_id == prayer_request_id,
            PrayerComment.deleted_at.is_(None),
        )
        .order_by(PrayerComment.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return rows, total


def create_prayer_comment(
    db: Session,
    *,
    prayer_request_id: int,
    author_id: int,
    text: str,
) -> PrayerComment:
    comment = PrayerComment(
        prayer_request_id=prayer_request_id,
        author_id=author_id,
        text=text,
    )
    db.add(comment)
    db.flush()
    return comment


def update_prayer_comment(
    db: Session, comment: PrayerComment, text: str
) -> PrayerComment:
    comment.text = text
    db.add(comment)
    db.flush()
    return comment


def soft_delete_prayer_comment(db: Session, comment: PrayerComment) -> None:
    comment.deleted_at = _utcnow()
    db.add(comment)
    db.flush()


# ---------------------------------------------------------------------------
# FamilyReflection
# ---------------------------------------------------------------------------


def get_reflection_by_id(db: Session, reflection_id: int) -> FamilyReflection | None:
    return db.scalar(
        select(FamilyReflection).where(
            FamilyReflection.id == reflection_id,
            FamilyReflection.deleted_at.is_(None),
        )
    )


def list_reflections(
    db: Session,
    family_id: int,
    limit: int = 50,
    offset: int = 0,
) -> tuple[Sequence[FamilyReflection], int]:
    total = (
        db.scalar(
            select(func.count(FamilyReflection.id)).where(
                FamilyReflection.family_id == family_id,
                FamilyReflection.deleted_at.is_(None),
            )
        )
        or 0
    )

    rows = db.scalars(
        select(FamilyReflection)
        .where(
            FamilyReflection.family_id == family_id,
            FamilyReflection.deleted_at.is_(None),
        )
        .order_by(FamilyReflection.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return rows, total


def create_reflection(
    db: Session,
    *,
    family_id: int,
    author_id: int,
    text: str,
) -> FamilyReflection:
    reflection = FamilyReflection(
        family_id=family_id,
        author_id=author_id,
        text=text,
    )
    db.add(reflection)
    db.flush()
    return reflection


def update_reflection(
    db: Session, reflection: FamilyReflection, text: str
) -> FamilyReflection:
    reflection.text = text
    db.flush()
    return reflection


def soft_delete_reflection(db: Session, reflection: FamilyReflection) -> None:
    reflection.deleted_at = _utcnow()

    db.add(reflection)
    db.flush()


def list_reflection_comments(
    db: Session, reflection_id: int, limit: int = 50, offset: int = 0
) -> tuple[Sequence[FamilyReflectionComment], int]:
    total = (
        db.scalar(
            select(func.count(FamilyReflectionComment.id)).where(
                FamilyReflectionComment.reflection_id == reflection_id,
                FamilyReflectionComment.deleted_at.is_(None),
            )
        )
        or 0
    )
    rows = db.scalars(
        select(FamilyReflectionComment)
        .where(
            FamilyReflectionComment.reflection_id == reflection_id,
            FamilyReflectionComment.deleted_at.is_(None),
        )
        .order_by(FamilyReflectionComment.created_at.asc())
        .offset(offset)
        .limit(limit)
    ).all()
    return rows, total


def create_reflection_comment(
    db: Session, *, reflection_id: int, author_id: int, text: str
) -> FamilyReflectionComment:
    comment = FamilyReflectionComment(
        reflection_id=reflection_id,
        author_id=author_id,
        text=text,
    )
    db.add(comment)
    db.flush()
    return comment


def soft_delete_reflection_comment(
    db: Session, comment: FamilyReflectionComment
) -> None:
    comment.deleted_at = _utcnow()
    db.add(comment)
    db.flush()


# ---------------------------------------------------------------------------
# ReflectionEncouragement
# ---------------------------------------------------------------------------


def get_encouragement_counts(db: Session, reflection_id: int) -> dict[str, int]:
    rows = db.execute(
        select(
            ReflectionEncouragement.encouragement_type,
            func.count(ReflectionEncouragement.id),
        )
        .where(
            ReflectionEncouragement.reflection_id == reflection_id,
        )
        .group_by(ReflectionEncouragement.encouragement_type)
    ).all()
    return {row[0].value: row[1] for row in rows}


def add_encouragement(
    db: Session,
    *,
    reflection_id: int,
    user_id: int,
    encouragement_type: str,
) -> ReflectionEncouragement | None:
    """Add encouragement. Returns None if already exists (unique constraint)."""
    from sqlalchemy.exc import IntegrityError

    try:
        encouragement = ReflectionEncouragement(
            reflection_id=reflection_id,
            user_id=user_id,
            encouragement_type=encouragement_type,
        )
        db.add(encouragement)
        db.flush()
        return encouragement
    except IntegrityError:
        db.rollback()
        return None


# ---------------------------------------------------------------------------
# FamilyActivity
# ---------------------------------------------------------------------------


def log_activity(
    db: Session,
    *,
    family_id: int,
    event_type: EventType,
    actor_id: int | None = None,
    extra: dict | None = None,
    request_id: str | None = None,
) -> FamilyActivity:
    activity = FamilyActivity(
        family_id=family_id,
        actor_id=actor_id,
        event_type=event_type,
        extra=extra,
        request_id=request_id,
    )
    db.add(activity)
    db.flush()
    return activity


def get_family_activity_by_request_id(
    db: Session, request_id: str
) -> FamilyActivity | None:
    return db.scalar(
        select(FamilyActivity).where(
            FamilyActivity.request_id == request_id,
        )
    )


def list_activities(
    db: Session,
    family_id: int,
    *,
    limit: int = 20,
    cursor: str | None = None,
) -> tuple[Sequence[FamilyActivity], str | None]:
    """Cursor-based pagination. Cursor format: 'created_at_iso,id'."""
    query = select(FamilyActivity).where(
        FamilyActivity.family_id == family_id,
    )

    if cursor:
        try:
            cursor_created_at_str, cursor_id = cursor.rsplit(",", 1)
            cursor_created_at = datetime.fromisoformat(cursor_created_at_str)
            cursor_id = int(cursor_id)
            query = query.where(
                or_(
                    FamilyActivity.created_at < cursor_created_at,
                    (FamilyActivity.created_at == cursor_created_at)
                    & (FamilyActivity.id < cursor_id),
                )
            )
        except (ValueError, TypeError):
            pass

    rows = db.scalars(
        query.order_by(
            FamilyActivity.created_at.desc(), FamilyActivity.id.desc()
        ).limit(limit + 1)
    ).all()

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    next_cursor: str | None = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = f"{last.created_at.isoformat()},{last.id}"

    return rows, next_cursor


# ---------------------------------------------------------------------------
# FamilySettings
# ---------------------------------------------------------------------------


def get_settings(db: Session, family_id: int) -> FamilySettings | None:
    return db.scalar(
        select(FamilySettings).where(
            FamilySettings.family_id == family_id,
            FamilySettings.deleted_at.is_(None),
        )
    )


def update_settings(
    db: Session,
    settings: FamilySettings,
    *,
    notification_preferences: dict | None = None,
) -> FamilySettings:
    if notification_preferences is not None:
        settings.notification_preferences = notification_preferences
    settings.version += 1
    db.add(settings)
    db.flush()
    return settings
