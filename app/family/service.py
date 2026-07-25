"""Family domain service layer.

All business logic and authorization lives here.
Routers are thin — they parse requests, call services, and return responses.

Permission model
----------------
- Owner: full control, can delete family, change roles, remove any member
- Admin: can manage members, goals, prayers, reflections; cannot delete family or change roles
- Member: can create goals, prayers, reflections; cannot manage other members

Domain events
-------------
Services return FamilyEvent dataclass instances for important actions.
These are logged to the activity timeline and prepared for future event bus consumption.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
import secrets

from app.family.exceptions import (
    BusinessRuleException,
    FamilyNotFoundException,
    FamilyPermissionDeniedException,
    GoalAlreadyCompletedException,
    GoalNotFoundException,
    InvitationExpiredException,
    InvitationNotFoundException,
    InvalidInviteCodeException,
    MemberNotFoundException,
    PrayerRequestNotFoundException,
    ReflectionNotFoundException,
    SettingsNotFoundException,
)
from sqlalchemy.orm import Session

from app.family import repository as repo
from app.family.models import (
    EventType,
    FamilyRole,
    InvitationStatus,
    Family,
    FamilyInvitation,
    FamilyMember,
    FamilyGoal,
    PrayerRequest,
    FamilyReflection,
    FamilySettings,
)
from app.core.envelope import Meta
from app.family.schemas import (
    FamilyCreate,
    FamilyUpdate,
    GoalCreate,
    GoalUpdate,
    PrayerRequestCreate,
    PrayerRespond,
    ReflectionCreate,
    ReflectionEncourage,
    SettingsUpdate,
    MemberRoleUpdate,
    JoinRequest,
    FamilyResponse,
    FamilyDetailResponse,
    FamilyMemberResponse,
    FamilyGoalResponse,
    PrayerRequestResponse,
    ReflectionResponse,
    ActivityResponse,
    ActivityPage,
)


# ---------------------------------------------------------------------------
# Domain Events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FamilyEvent:
    event_type: EventType
    family_id: int
    actor_id: int | None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    extra: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------


class Permission:
    """Granular permissions mapped to roles."""

    MANAGE_FAMILY = "manage_family"          # update name, cover, delete
    MANAGE_MEMBERS = "manage_members"        # remove members
    MANAGE_ROLES = "manage_roles"            # change member roles
    CREATE_INVITATION = "create_invitation"
    CANCEL_INVITATION = "cancel_invitation"
    MANAGE_GOALS = "manage_goals"            # create, update, archive any goal
    MANAGE_OWN_GOALS = "manage_own_goals"    # update/archive own goal
    CREATE_PRAYER = "create_prayer"
    ANSWER_PRAYER = "answer_prayer"          # mark own prayer as answered
    CREATE_REFLECTION = "create_reflection"
    MANAGE_SETTINGS = "manage_settings"
    VIEW_ACTIVITY = "view_activity"
    VIEW_MEMBERS = "view_members"
    LEAVE_FAMILY = "leave_family"


ROLE_PERMISSIONS: dict[FamilyRole, set[str]] = {
    FamilyRole.OWNER: {
        Permission.MANAGE_FAMILY,
        Permission.MANAGE_MEMBERS,
        Permission.MANAGE_ROLES,
        Permission.CREATE_INVITATION,
        Permission.CANCEL_INVITATION,
        Permission.MANAGE_GOALS,
        Permission.CREATE_PRAYER,
        Permission.ANSWER_PRAYER,
        Permission.CREATE_REFLECTION,
        Permission.MANAGE_SETTINGS,
        Permission.VIEW_ACTIVITY,
        Permission.VIEW_MEMBERS,
        Permission.LEAVE_FAMILY,
    },
    FamilyRole.ADMIN: {
        Permission.MANAGE_MEMBERS,
        Permission.CREATE_INVITATION,
        Permission.CANCEL_INVITATION,
        Permission.MANAGE_GOALS,
        Permission.CREATE_PRAYER,
        Permission.ANSWER_PRAYER,
        Permission.CREATE_REFLECTION,
        Permission.MANAGE_SETTINGS,
        Permission.VIEW_ACTIVITY,
        Permission.VIEW_MEMBERS,
        Permission.LEAVE_FAMILY,
    },
    FamilyRole.MEMBER: {
        Permission.MANAGE_OWN_GOALS,
        Permission.CREATE_INVITATION,
        Permission.CREATE_PRAYER,
        Permission.ANSWER_PRAYER,
        Permission.CREATE_REFLECTION,
        Permission.VIEW_ACTIVITY,
        Permission.VIEW_MEMBERS,
        Permission.LEAVE_FAMILY,
    },
}


def _require_permission(
    db: Session, family_id: int, user_id: int, permission: str
) -> FamilyMember:
    """Check that the user has the given permission for the family.

    Returns the FamilyMember record if authorized.
    Raises 403 if not a member or lacks permission.
    Raises 404 if the family doesn't exist.
    """
    family = repo.get_family_by_id(db, family_id)
    if not family:
        raise FamilyNotFoundException()

    member = repo.get_member(db, family_id, user_id)
    if not member:
        raise FamilyPermissionDeniedException("Not a member of this family")

    permissions = ROLE_PERMISSIONS.get(member.role, set())
    if permission not in permissions:
        raise FamilyPermissionDeniedException("Insufficient permissions")

    return member


def _require_family_access(
    db: Session, family_id: int, user_id: int
) -> Family:
    """Verify the user is a member of the family. Returns the family."""
    family = repo.get_family_by_id(db, family_id)
    if not family:
        raise FamilyNotFoundException()

    member = repo.get_member(db, family_id, user_id)
    if not member:
        raise FamilyPermissionDeniedException("Not a member of this family")

    return family


def _log_and_return(
    db: Session,
    family_id: int,
    event_type: EventType,
    actor_id: int | None = None,
    extra: dict[str, Any] | None = None,
) -> FamilyEvent:
    """Log an activity and return the event."""
    repo.log_activity(
        db,
        family_id=family_id,
        event_type=event_type,
        actor_id=actor_id,
        extra=extra,
    )
    return FamilyEvent(
        event_type=event_type,
        family_id=family_id,
        actor_id=actor_id,
        extra=extra,
    )


def _generate_invite_code() -> str:
    """Generate a unique invite code with 48 bits of entropy."""
    random_suffix = secrets.token_urlsafe(8)
    return f"MIZAN-{random_suffix}"


def _get_username(db: Session, user_id: int) -> str:
    """Get username for a user ID."""
    from app.users.models import User
    user = db.get(User, user_id)
    return user.username if user else "Unknown"


# ---------------------------------------------------------------------------
# Family CRUD
# ---------------------------------------------------------------------------


def create_family(
    db: Session, payload: FamilyCreate, user_id: int
) -> tuple[Family, FamilyEvent]:
    """Create a new family. The creator becomes the owner."""
    invite_code = _generate_invite_code()

    family = repo.create_family(
        db,
        name=payload.name,
        invite_code=invite_code,
        created_by=user_id,
        cover_icon=payload.cover_icon,
    )

    # Add creator as owner
    repo.add_member(db, family_id=family.id, user_id=user_id, role=FamilyRole.OWNER)

    db.commit()
    db.refresh(family)

    event = _log_and_return(
        db,
        family_id=family.id,
        event_type=EventType.FAMILY_CREATED,
        actor_id=user_id,
        extra={"name": payload.name},
    )
    db.commit()

    return family, event


def get_family_detail(db: Session, family_id: int, user_id: int) -> FamilyDetailResponse:
    """Get family detail with members and goals."""
    family = _require_family_access(db, family_id, user_id)

    members = repo.list_members(db, family_id)
    goals = repo.list_family_goals(db, family_id)

    member_responses = []
    for m in members:
        username = _get_username(db, m.user_id)
        member_responses.append(
            FamilyMemberResponse(
                id=m.id,
                user_id=m.user_id,
                username=username,
                role=m.role,
                joined_at=m.joined_at,
            )
        )

    goal_responses = []
    for g in goals:
        progress = (g.acts_done / g.acts_target) if g.acts_target > 0 else 0.0
        goal_responses.append(
            FamilyGoalResponse(
                id=g.id,
                title=g.title,
                subtitle=g.subtitle,
                progress=round(progress, 4),
                acts_done=g.acts_done,
                acts_target=g.acts_target,
                is_archived=g.is_archived,
                completed_at=g.completed_at,
                created_by=g.created_by,
                created_at=g.created_at,
            )
        )

    return FamilyDetailResponse(
        id=family.id,
        name=family.name,
        cover_icon=family.cover_icon,
        invite_code=family.invite_code,
        members=member_responses,
        goals=goal_responses,
        created_by=family.created_by,
        created_at=family.created_at,
    )


def list_user_families(db: Session, user_id: int) -> list[FamilyResponse]:
    """List all families the user belongs to."""
    families = repo.list_user_families(db, user_id)

    results = []
    for family in families:
        member_count = repo.count_family_members(db, family.id)
        goals = repo.list_family_goals(db, family.id)
        goal_count = len(goals)

        # Get last activity
        activities, _ = repo.list_activities(db, family.id, limit=1)
        last_activity = None
        if activities:
            last_activity = activities[0].event_type.value

        results.append(
            FamilyResponse(
                id=family.id,
                name=family.name,
                cover_icon=family.cover_icon,
                invite_code=family.invite_code,
                member_count=member_count,
                goal_count=goal_count,
                last_activity=last_activity,
                created_by=family.created_by,
                created_at=family.created_at,
            )
        )

    return results


def update_family(
    db: Session, family_id: int, payload: FamilyUpdate, user_id: int
) -> Family:
    """Update family name/cover. Owner only."""
    _require_permission(db, family_id, user_id, Permission.MANAGE_FAMILY)
    family = repo.get_family_by_id(db, family_id)
    if not family:
        raise FamilyNotFoundException()

    family = repo.update_family(
        db,
        family,
        name=payload.name,
        cover_icon=payload.cover_icon,
    )
    db.commit()
    db.refresh(family)
    return family


def delete_family(db: Session, family_id: int, user_id: int) -> None:
    """Soft delete a family. Owner only."""
    _require_permission(db, family_id, user_id, Permission.MANAGE_FAMILY)
    family = repo.get_family_by_id(db, family_id)
    if not family:
        raise FamilyNotFoundException()

    repo.soft_delete_family(db, family)
    db.commit()


def archive_family(db: Session, family_id: int, user_id: int) -> None:
    """Archive a family. Owner only. Alias for soft delete."""
    _require_permission(db, family_id, user_id, Permission.MANAGE_FAMILY)
    family = repo.get_family_by_id(db, family_id)
    if not family:
        raise FamilyNotFoundException()

    repo.soft_delete_family(db, family)
    db.commit()


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


def list_members(db: Session, family_id: int, user_id: int) -> list[FamilyMemberResponse]:
    """List family members."""
    _require_permission(db, family_id, user_id, Permission.VIEW_MEMBERS)
    members = repo.list_members(db, family_id)

    results = []
    for m in members:
        username = _get_username(db, m.user_id)
        results.append(
            FamilyMemberResponse(
                id=m.id,
                user_id=m.user_id,
                username=username,
                role=m.role,
                joined_at=m.joined_at,
            )
        )
    return results


def update_member_role(
    db: Session, family_id: int, member_id: int, payload: MemberRoleUpdate, user_id: int
) -> FamilyMember:
    """Change a member's role. Owner only."""
    _require_permission(db, family_id, user_id, Permission.MANAGE_ROLES)

    member = repo.get_member_by_id(db, member_id)
    if not member or member.family_id != family_id:
        raise MemberNotFoundException()

    # Cannot change the owner's role
    if member.role == FamilyRole.OWNER:
        raise BusinessRuleException("Cannot change the owner's role")

    member = repo.update_member_role(db, member, payload.role)
    db.commit()
    db.refresh(member)

    _log_and_return(
        db,
        family_id=family_id,
        event_type=EventType.MEMBER_ROLE_CHANGED,
        actor_id=user_id,
        extra={"target_user_id": member.user_id, "new_role": payload.role.value},
    )
    db.commit()

    return member


def remove_member(db: Session, family_id: int, member_id: int, user_id: int) -> None:
    """Remove a member from the family. Admin+ or self-removal."""
    target_member = repo.get_member_by_id(db, member_id)
    if not target_member or target_member.family_id != family_id:
        raise MemberNotFoundException()

    # Self-removal (leave) is allowed for any member
    if target_member.user_id == user_id:
        repo.soft_delete_member(db, target_member)
        db.commit()
        _log_and_return(
            db,
            family_id=family_id,
            event_type=EventType.MEMBER_LEFT,
            actor_id=user_id,
        )
        db.commit()
        return

    # Removing others requires MANAGE_MEMBERS permission
    _require_permission(db, family_id, user_id, Permission.MANAGE_MEMBERS)

    # Cannot remove the owner
    if target_member.role == FamilyRole.OWNER:
        raise BusinessRuleException("Cannot remove the owner")

    repo.soft_delete_member(db, target_member)
    db.commit()

    _log_and_return(
        db,
        family_id=family_id,
        event_type=EventType.MEMBER_LEFT,
        actor_id=user_id,
        extra={"removed_user_id": target_member.user_id},
    )
    db.commit()


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


def create_invitation(
    db: Session, family_id: int, user_id: int
) -> tuple[FamilyInvitation, FamilyEvent]:
    """Create a new invitation for the family."""
    _require_permission(db, family_id, user_id, Permission.CREATE_INVITATION)

    invite_code = _generate_invite_code()
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)

    invitation = repo.create_invitation(
        db,
        family_id=family_id,
        invited_by=user_id,
        invite_code=invite_code,
        expires_at=expires_at,
    )
    db.commit()
    db.refresh(invitation)

    return invitation, FamilyEvent(
        event_type=EventType.INVITATION_ACCEPTED,
        family_id=family_id,
        actor_id=user_id,
    )


def list_invitations(
    db: Session, family_id: int, user_id: int
) -> list[FamilyInvitation]:
    """List pending invitations for the family."""
    _require_permission(db, family_id, user_id, Permission.VIEW_MEMBERS)
    repo.expire_pending_invitations(db, family_id)
    return repo.list_family_invitations(db, family_id, status=InvitationStatus.PENDING)


def cancel_invitation(
    db: Session, family_id: int, invitation_id: int, user_id: int
) -> None:
    """Cancel a pending invitation."""
    _require_permission(db, family_id, user_id, Permission.CANCEL_INVITATION)

    invitation = repo.get_invitation_by_id(db, invitation_id)
    if not invitation or invitation.family_id != family_id:
        raise InvitationNotFoundException()

    repo.update_invitation_status(db, invitation, InvitationStatus.CANCELLED)
    db.commit()


def join_family(db: Session, payload: JoinRequest, user_id: int) -> Family:
    """Join a family using an invite code."""
    invitation = repo.get_invitation_by_code(db, payload.invite_code)
    if not invitation:
        raise InvalidInviteCodeException()

    if invitation.status != InvitationStatus.PENDING:
        raise InvitationExpiredException("Invitation is no longer valid")

    if invitation.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        repo.update_invitation_status(db, invitation, InvitationStatus.EXPIRED)
        db.commit()
        raise InvitationExpiredException("Invitation has expired")

    # Check if already a member
    existing = repo.get_member(db, invitation.family_id, user_id)
    if existing:
        raise FamilyPermissionDeniedException("Already a member of this family")

    # Add member
    repo.add_member(db, family_id=invitation.family_id, user_id=user_id)
    repo.update_invitation_status(db, invitation, InvitationStatus.ACCEPTED)
    db.commit()

    family = repo.get_family_by_id(db, invitation.family_id)

    _log_and_return(
        db,
        family_id=invitation.family_id,
        event_type=EventType.MEMBER_JOINED,
        actor_id=user_id,
    )
    db.commit()

    return family


def accept_invitation(db: Session, invite_code: str, user_id: int) -> Family:
    """Accept an invitation by code (alias for join)."""
    return join_family(db, JoinRequest(invite_code=invite_code), user_id)


def decline_invitation(db: Session, invite_code: str, user_id: int) -> None:
    """Decline an invitation by code."""
    invitation = repo.get_invitation_by_code(db, invite_code)
    if not invitation:
        raise InvalidInviteCodeException()

    repo.update_invitation_status(db, invitation, InvitationStatus.DECLINED)
    db.commit()

    _log_and_return(
        db,
        family_id=invitation.family_id,
        event_type=EventType.INVITATION_DECLINED,
        actor_id=user_id,
    )
    db.commit()


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------


def list_goals(
    db: Session, family_id: int, user_id: int, include_archived: bool = False
) -> list[FamilyGoalResponse]:
    """List family goals."""
    _require_permission(db, family_id, user_id, Permission.VIEW_ACTIVITY)
    goals = repo.list_family_goals(db, family_id, include_archived=include_archived)

    results = []
    for g in goals:
        progress = (g.acts_done / g.acts_target) if g.acts_target > 0 else 0.0
        results.append(
            FamilyGoalResponse(
                id=g.id,
                title=g.title,
                subtitle=g.subtitle,
                progress=round(progress, 4),
                acts_done=g.acts_done,
                acts_target=g.acts_target,
                is_archived=g.is_archived,
                completed_at=g.completed_at,
                created_by=g.created_by,
                created_at=g.created_at,
            )
        )
    return results


def create_goal(
    db: Session, family_id: int, payload: GoalCreate, user_id: int
) -> FamilyGoal:
    """Create a new family goal."""
    _require_permission(db, family_id, user_id, Permission.MANAGE_GOALS)

    goal = repo.create_goal(
        db,
        family_id=family_id,
        created_by=user_id,
        title=payload.title,
        subtitle=payload.subtitle,
        acts_target=payload.acts_target,
    )
    db.commit()
    db.refresh(goal)

    _log_and_return(
        db,
        family_id=family_id,
        event_type=EventType.GOAL_CREATED,
        actor_id=user_id,
        extra={"goal_id": goal.id, "title": payload.title},
    )
    db.commit()

    return goal


def update_goal(
    db: Session, family_id: int, goal_id: int, payload: GoalUpdate, user_id: int
) -> FamilyGoal:
    """Update a goal. Owner/Admin can update any goal; Member can update own."""
    goal = repo.get_goal_by_id(db, goal_id)
    if not goal or goal.family_id != family_id:
        raise GoalNotFoundException()

    # Check permission
    member = _require_permission(db, family_id, user_id, Permission.MANAGE_GOALS)
    if member.role == FamilyRole.MEMBER and goal.created_by != user_id:
        raise FamilyPermissionDeniedException("Cannot update another member's goal")

    goal = repo.update_goal(
        db,
        goal,
        title=payload.title,
        subtitle=payload.subtitle,
        acts_target=payload.acts_target,
        acts_done=payload.acts_done,
    )
    db.commit()
    db.refresh(goal)
    return goal


def complete_goal(db: Session, family_id: int, goal_id: int, user_id: int) -> FamilyGoal:
    """Mark a goal as completed."""
    goal = repo.get_goal_by_id(db, goal_id)
    if not goal or goal.family_id != family_id:
        raise GoalNotFoundException()

    _require_permission(db, family_id, user_id, Permission.MANAGE_GOALS)

    if goal.completed_at:
        raise GoalAlreadyCompletedException()

    goal = repo.complete_goal(db, goal)
    db.commit()
    db.refresh(goal)

    _log_and_return(
        db,
        family_id=family_id,
        event_type=EventType.GOAL_COMPLETED,
        actor_id=user_id,
        extra={"goal_id": goal.id, "title": goal.title},
    )
    db.commit()

    return goal


def archive_goal(db: Session, family_id: int, goal_id: int, user_id: int) -> FamilyGoal:
    """Archive a goal."""
    goal = repo.get_goal_by_id(db, goal_id)
    if not goal or goal.family_id != family_id:
        raise GoalNotFoundException()

    member = _require_permission(db, family_id, user_id, Permission.MANAGE_GOALS)
    if member.role == FamilyRole.MEMBER and goal.created_by != user_id:
        raise FamilyPermissionDeniedException("Cannot archive another member's goal")

    goal = repo.archive_goal(db, goal)
    db.commit()
    db.refresh(goal)
    return goal


# ---------------------------------------------------------------------------
# Prayer Requests
# ---------------------------------------------------------------------------


def list_prayer_requests(
    db: Session,
    family_id: int,
    user_id: int,
    include_answered: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[PrayerRequestResponse], int]:
    """List prayer requests for the family."""
    _require_permission(db, family_id, user_id, Permission.VIEW_ACTIVITY)

    prayers, total = repo.list_prayer_requests(
        db, family_id, include_answered=include_answered, limit=limit, offset=offset
    )

    results = []
    for p in prayers:
        author_name = _get_username(db, p.author_id)
        response_counts = repo.get_prayer_response_counts(db, p.id)
        results.append(
            PrayerRequestResponse(
                id=p.id,
                family_id=p.family_id,
                author_id=p.author_id,
                author_name=author_name,
                text=p.text,
                is_answered=p.is_answered,
                is_private=p.is_private,
                response_counts=response_counts,
                created_at=p.created_at,
            )
        )

    return results, total


def create_prayer_request(
    db: Session, family_id: int, payload: PrayerRequestCreate, user_id: int
) -> PrayerRequest:
    """Create a prayer request."""
    _require_permission(db, family_id, user_id, Permission.CREATE_PRAYER)

    prayer = repo.create_prayer_request(
        db,
        family_id=family_id,
        author_id=user_id,
        text=payload.text,
        is_private=payload.is_private,
    )
    db.commit()
    db.refresh(prayer)

    _log_and_return(
        db,
        family_id=family_id,
        event_type=EventType.PRAYER_REQUEST_CREATED,
        actor_id=user_id,
    )
    db.commit()

    return prayer


def respond_to_prayer(
    db: Session, family_id: int, prayer_id: int, payload: PrayerRespond, user_id: int
) -> dict[str, int]:
    """Add a response to a prayer request."""
    _require_permission(db, family_id, user_id, Permission.VIEW_ACTIVITY)

    prayer = repo.get_prayer_request_by_id(db, prayer_id)
    if not prayer or prayer.family_id != family_id:
        raise PrayerRequestNotFoundException()

    repo.add_prayer_response(
        db,
        prayer_request_id=prayer_id,
        user_id=user_id,
        response_type=payload.response_type.value,
    )
    db.commit()

    return repo.get_prayer_response_counts(db, prayer_id)


def answer_prayer(
    db: Session, family_id: int, prayer_id: int, user_id: int
) -> PrayerRequest:
    """Mark a prayer request as answered. Author only."""
    _require_permission(db, family_id, user_id, Permission.ANSWER_PRAYER)

    prayer = repo.get_prayer_request_by_id(db, prayer_id)
    if not prayer or prayer.family_id != family_id:
        raise PrayerRequestNotFoundException()

    if prayer.author_id != user_id:
        raise FamilyPermissionDeniedException("Only the author can mark a prayer as answered")

    prayer = repo.mark_prayer_answered(db, prayer)
    db.commit()
    db.refresh(prayer)

    _log_and_return(
        db,
        family_id=family_id,
        event_type=EventType.PRAYER_REQUEST_ANSWERED,
        actor_id=user_id,
    )
    db.commit()

    return prayer


# ---------------------------------------------------------------------------
# Reflections
# ---------------------------------------------------------------------------


def list_reflections(
    db: Session,
    family_id: int,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ReflectionResponse], int]:
    """List family reflections."""
    _require_permission(db, family_id, user_id, Permission.VIEW_ACTIVITY)

    reflections, total = repo.list_reflections(db, family_id, limit=limit, offset=offset)

    results = []
    for r in reflections:
        author_name = _get_username(db, r.author_id)
        encouragement_counts = repo.get_encouragement_counts(db, r.id)
        results.append(
            ReflectionResponse(
                id=r.id,
                family_id=r.family_id,
                author_id=r.author_id,
                author_name=author_name,
                text=r.text,
                encouragement_counts=encouragement_counts,
                created_at=r.created_at,
            )
        )

    return results, total


def create_reflection(
    db: Session, family_id: int, payload: ReflectionCreate, user_id: int
) -> FamilyReflection:
    """Create a family reflection."""
    _require_permission(db, family_id, user_id, Permission.CREATE_REFLECTION)

    reflection = repo.create_reflection(
        db,
        family_id=family_id,
        author_id=user_id,
        text=payload.text,
    )
    db.commit()
    db.refresh(reflection)

    _log_and_return(
        db,
        family_id=family_id,
        event_type=EventType.REFLECTION_SHARED,
        actor_id=user_id,
    )
    db.commit()

    return reflection


def encourage_reflection(
    db: Session, family_id: int, reflection_id: int, payload: ReflectionEncourage, user_id: int
) -> dict[str, int]:
    """Add encouragement to a reflection."""
    _require_permission(db, family_id, user_id, Permission.VIEW_ACTIVITY)

    reflection = repo.get_reflection_by_id(db, reflection_id)
    if not reflection or reflection.family_id != family_id:
        raise ReflectionNotFoundException()

    repo.add_encouragement(
        db,
        reflection_id=reflection_id,
        user_id=user_id,
        encouragement_type=payload.encouragement_type.value,
    )
    db.commit()

    return repo.get_encouragement_counts(db, reflection_id)


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------


def list_activities(
    db: Session,
    family_id: int,
    user_id: int,
    limit: int = 20,
    cursor: str | None = None,
) -> ActivityPage:
    """List family activity timeline with cursor-based pagination."""
    _require_permission(db, family_id, user_id, Permission.VIEW_ACTIVITY)

    activities, next_cursor = repo.list_activities(
        db, family_id, limit=limit, cursor=cursor
    )

    results = []
    for a in activities:
        actor_name = _get_username(db, a.actor_id) if a.actor_id else None
        results.append(
            ActivityResponse(
                id=a.id,
                actor_id=a.actor_id,
                actor_name=actor_name,
                event_type=a.event_type,
                metadata=a.extra,
                created_at=a.created_at,
            )
        )

    return ActivityPage(
        data=results,
        meta=Meta(
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
        ),
    )


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def get_settings(db: Session, family_id: int, user_id: int) -> FamilySettings:
    """Get family settings."""
    _require_permission(db, family_id, user_id, Permission.VIEW_ACTIVITY)

    settings = repo.get_settings(db, family_id)
    if not settings:
        raise SettingsNotFoundException()

    return settings


def update_settings(
    db: Session, family_id: int, payload: SettingsUpdate, user_id: int
) -> FamilySettings:
    """Update family settings. Admin+ only."""
    _require_permission(db, family_id, user_id, Permission.MANAGE_SETTINGS)

    settings = repo.get_settings(db, family_id)
    if not settings:
        raise SettingsNotFoundException()

    settings = repo.update_settings(
        db,
        settings,
        notification_preferences=payload.notification_preferences,
    )
    db.commit()
    db.refresh(settings)
    return settings


# ---------------------------------------------------------------------------
# Legacy / Frontend compatibility endpoints
# ---------------------------------------------------------------------------


def leave_family(db: Session, family_id: int, user_id: int) -> None:
    """Self-removal (leave). Reuses remove_member with member_id == user_id."""
    member = repo.get_member_by_user(db, family_id, user_id)
    if not member:
        raise MemberNotFoundException()
    remove_member(db, family_id, member.id, user_id)


def get_leaderboard(db: Session, family_id: int, user_id: int, limit: int = 10) -> list[dict]:
    """Return a simple family leaderboard. Frontend compatibility endpoint."""
    _require_permission(db, family_id, user_id, Permission.VIEW_ACTIVITY)
    members = repo.list_members(db, family_id, include_deleted=False)
    results = []
    for m in members:
        member_user = db.get(User, m.user_id)
        if not member_user:
            continue
        results.append({
            "user_id": m.user_id,
            "username": member_user.username,
            "contribution_count": 0,
            "stars_earned": 0,
        })
    return results[:limit]


def get_top_contributor(db: Session, family_id: int, user_id: int) -> dict | None:
    """Return the top contributor for a family. Frontend compatibility endpoint."""
    _require_permission(db, family_id, user_id, Permission.VIEW_ACTIVITY)
    members = repo.list_members(db, family_id, include_deleted=False)
    best = None
    for m in members:
        member_user = db.get(User, m.user_id)
        if not member_user:
            continue
        best = {
            "user_id": m.user_id,
            "username": member_user.username,
            "contribution_count": 0,
            "stars_earned": 0,
        }
        break
    return best
