"""Family domain router.

Thin endpoints — all business logic and authorization lives in the service layer.
Follows REST conventions with consistent response envelopes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.envelope import Envelope, Meta
from app.db.deps import get_db
from app.users.dependencies import get_current_user
from app.users.models import User
from app.family import service
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
)

router = APIRouter(prefix="/family", tags=["family"])

DbDep = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Family CRUD
# ---------------------------------------------------------------------------


@router.get("/", response_model=Envelope)
def list_families(db: DbDep, current_user: CurrentUser):
    """List all families the current user belongs to."""
    families = service.list_user_families(db, current_user.id)
    return Envelope(data=families)


@router.post("/", response_model=Envelope, status_code=status.HTTP_201_CREATED)
def create_family(payload: FamilyCreate, db: DbDep, current_user: CurrentUser):
    """Create a new family. The creator becomes the owner."""
    family, event = service.create_family(db, payload, current_user.id)
    return Envelope(
        data={
            "id": family.id,
            "name": family.name,
            "invite_code": family.invite_code,
            "cover_icon": family.cover_icon,
            "created_at": family.created_at.isoformat(),
        },
        message="Family created",
    )


@router.get("/{family_id}", response_model=Envelope)
def get_family(family_id: int, db: DbDep, current_user: CurrentUser):
    """Get family detail with members and goals."""
    detail = service.get_family_detail(db, family_id, current_user.id)
    return Envelope(data=detail)


@router.patch("/{family_id}", response_model=Envelope)
def update_family(
    family_id: int, payload: FamilyUpdate, db: DbDep, current_user: CurrentUser
):
    """Update family name/cover. Owner only."""
    family = service.update_family(db, family_id, payload, current_user.id)
    return Envelope(
        data={
            "id": family.id,
            "name": family.name,
            "cover_icon": family.cover_icon,
        },
        message="Family updated",
    )


@router.delete("/{family_id}", response_model=Envelope, status_code=status.HTTP_200_OK)
def delete_family(family_id: int, db: DbDep, current_user: CurrentUser):
    """Soft delete a family. Owner only."""
    service.delete_family(db, family_id, current_user.id)
    return Envelope(message="Family deleted")


@router.post("/{family_id}/archive", response_model=Envelope)
def archive_family(family_id: int, db: DbDep, current_user: CurrentUser):
    """Archive a family. Owner only."""
    service.archive_family(db, family_id, current_user.id)
    return Envelope(message="Family archived")


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


@router.get("/{family_id}/members", response_model=Envelope)
def list_members(family_id: int, db: DbDep, current_user: CurrentUser):
    """List family members."""
    members = service.list_members(db, family_id, current_user.id)
    return Envelope(data=members)


@router.patch("/{family_id}/members/{member_id}/role", response_model=Envelope)
def update_member_role(
    family_id: int,
    member_id: int,
    payload: MemberRoleUpdate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Change a member's role. Owner only."""
    member = service.update_member_role(db, family_id, member_id, payload, current_user.id)
    return Envelope(
        data={
            "id": member.id,
            "user_id": member.user_id,
            "role": member.role.value,
        },
        message="Role updated",
    )


@router.delete("/{family_id}/members/{member_id}", response_model=Envelope)
def remove_member(
    family_id: int,
    member_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    """Remove a member. Admin+ or self-removal (leave)."""
    service.remove_member(db, family_id, member_id, current_user.id)
    return Envelope(message="Member removed")


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


@router.post("/{family_id}/invitations", response_model=Envelope, status_code=status.HTTP_201_CREATED)
def create_invitation(family_id: int, db: DbDep, current_user: CurrentUser):
    """Create a new invitation for the family."""
    invitation, event = service.create_invitation(db, family_id, current_user.id)
    return Envelope(
        data={
            "id": invitation.id,
            "invite_code": invitation.invite_code,
            "expires_at": invitation.expires_at.isoformat(),
        },
        message="Invitation created",
    )


@router.get("/{family_id}/invitations", response_model=Envelope)
def list_invitations(family_id: int, db: DbDep, current_user: CurrentUser):
    """List pending invitations for the family."""
    invitations = service.list_invitations(db, family_id, current_user.id)
    return Envelope(
        data=[
            {
                "id": inv.id,
                "invite_code": inv.invite_code,
                "status": inv.status.value,
                "created_at": inv.created_at.isoformat(),
                "expires_at": inv.expires_at.isoformat(),
            }
            for inv in invitations
        ]
    )


@router.delete("/{family_id}/invitations/{invitation_id}", response_model=Envelope)
def cancel_invitation(
    family_id: int,
    invitation_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    """Cancel a pending invitation."""
    service.cancel_invitation(db, family_id, invitation_id, current_user.id)
    return Envelope(message="Invitation cancelled")


@router.post("/join", response_model=Envelope)
def join_family(payload: JoinRequest, db: DbDep, current_user: CurrentUser):
    """Join a family using an invite code."""
    family = service.join_family(db, payload, current_user.id)
    return Envelope(
        data={
            "id": family.id,
            "name": family.name,
            "invite_code": family.invite_code,
        },
        message="Joined family",
    )


@router.post("/invitations/{code}/accept", response_model=Envelope)
def accept_invitation(code: str, db: DbDep, current_user: CurrentUser):
    """Accept an invitation by code."""
    family = service.accept_invitation(db, code, current_user.id)
    return Envelope(
        data={
            "id": family.id,
            "name": family.name,
        },
        message="Invitation accepted",
    )


@router.post("/invitations/{code}/decline", response_model=Envelope)
def decline_invitation(code: str, db: DbDep, current_user: CurrentUser):
    """Decline an invitation by code."""
    service.decline_invitation(db, code, current_user.id)
    return Envelope(message="Invitation declined")


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------


@router.get("/{family_id}/goals", response_model=Envelope)
def list_goals(
    family_id: int,
    db: DbDep,
    current_user: CurrentUser,
    include_archived: bool = Query(False),
):
    """List family goals."""
    goals = service.list_goals(db, family_id, current_user.id, include_archived=include_archived)
    return Envelope(data=goals)


@router.post("/{family_id}/goals", response_model=Envelope, status_code=status.HTTP_201_CREATED)
def create_goal(
    family_id: int,
    payload: GoalCreate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Create a new family goal."""
    goal = service.create_goal(db, family_id, payload, current_user.id)
    return Envelope(
        data={
            "id": goal.id,
            "title": goal.title,
            "acts_target": goal.acts_target,
            "created_at": goal.created_at.isoformat(),
        },
        message="Goal created",
    )


@router.patch("/{family_id}/goals/{goal_id}", response_model=Envelope)
def update_goal(
    family_id: int,
    goal_id: int,
    payload: GoalUpdate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Update a goal."""
    goal = service.update_goal(db, family_id, goal_id, payload, current_user.id)
    return Envelope(
        data={
            "id": goal.id,
            "title": goal.title,
            "acts_done": goal.acts_done,
            "acts_target": goal.acts_target,
        },
        message="Goal updated",
    )


@router.post("/{family_id}/goals/{goal_id}/complete", response_model=Envelope)
def complete_goal(
    family_id: int,
    goal_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    """Mark a goal as completed."""
    goal = service.complete_goal(db, family_id, goal_id, current_user.id)
    return Envelope(
        data={
            "id": goal.id,
            "title": goal.title,
            "completed_at": goal.completed_at.isoformat() if goal.completed_at else None,
        },
        message="Goal completed",
    )


@router.post("/{family_id}/goals/{goal_id}/archive", response_model=Envelope)
def archive_goal(
    family_id: int,
    goal_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    """Archive a goal."""
    service.archive_goal(db, family_id, goal_id, current_user.id)
    return Envelope(message="Goal archived")


# ---------------------------------------------------------------------------
# Prayer Requests
# ---------------------------------------------------------------------------


@router.get("/{family_id}/prayers", response_model=Envelope)
def list_prayer_requests(
    family_id: int,
    db: DbDep,
    current_user: CurrentUser,
    include_answered: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List prayer requests for the family."""
    prayers, total = service.list_prayer_requests(
        db, family_id, current_user.id,
        include_answered=include_answered,
        limit=limit,
        offset=offset,
    )
    return Envelope(
        data=prayers,
        meta=Meta(total=total),
    )


@router.post("/{family_id}/prayers", response_model=Envelope, status_code=status.HTTP_201_CREATED)
def create_prayer_request(
    family_id: int,
    payload: PrayerRequestCreate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Create a prayer request."""
    prayer = service.create_prayer_request(db, family_id, payload, current_user.id)
    return Envelope(
        data={
            "id": prayer.id,
            "text": prayer.text,
            "is_private": prayer.is_private,
            "created_at": prayer.created_at.isoformat(),
        },
        message="Prayer request created",
    )


@router.post("/{family_id}/prayers/{prayer_id}/respond", response_model=Envelope)
def respond_to_prayer(
    family_id: int,
    prayer_id: int,
    payload: PrayerRespond,
    db: DbDep,
    current_user: CurrentUser,
):
    """Add a response to a prayer request."""
    counts = service.respond_to_prayer(db, family_id, prayer_id, payload, current_user.id)
    return Envelope(data={"response_counts": counts})


@router.post("/{family_id}/prayers/{prayer_id}/answer", response_model=Envelope)
def answer_prayer(
    family_id: int,
    prayer_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    """Mark a prayer request as answered. Author only."""
    prayer = service.answer_prayer(db, family_id, prayer_id, current_user.id)
    return Envelope(
        data={
            "id": prayer.id,
            "is_answered": prayer.is_answered,
        },
        message="Prayer marked as answered",
    )


# ---------------------------------------------------------------------------
# Reflections
# ---------------------------------------------------------------------------


@router.get("/{family_id}/reflections", response_model=Envelope)
def list_reflections(
    family_id: int,
    db: DbDep,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List family reflections."""
    reflections, total = service.list_reflections(
        db, family_id, current_user.id, limit=limit, offset=offset
    )
    return Envelope(
        data=reflections,
        meta=Meta(total=total),
    )


@router.post("/{family_id}/reflections", response_model=Envelope, status_code=status.HTTP_201_CREATED)
def create_reflection(
    family_id: int,
    payload: ReflectionCreate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Create a family reflection."""
    reflection = service.create_reflection(db, family_id, payload, current_user.id)
    return Envelope(
        data={
            "id": reflection.id,
            "text": reflection.text,
            "created_at": reflection.created_at.isoformat(),
        },
        message="Reflection shared",
    )


@router.post("/{family_id}/reflections/{reflection_id}/encourage", response_model=Envelope)
def encourage_reflection(
    family_id: int,
    reflection_id: int,
    payload: ReflectionEncourage,
    db: DbDep,
    current_user: CurrentUser,
):
    """Add encouragement to a reflection."""
    counts = service.encourage_reflection(
        db, family_id, reflection_id, payload, current_user.id
    )
    return Envelope(data={"encouragement_counts": counts})


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------


@router.get("/{family_id}/activity", response_model=Envelope)
def list_activities(
    family_id: int,
    db: DbDep,
    current_user: CurrentUser,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
):
    """List family activity timeline with cursor-based pagination."""
    page = service.list_activities(db, family_id, current_user.id, limit=limit, cursor=cursor)
    return Envelope(data=page.data, meta=page.meta)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@router.get("/{family_id}/settings", response_model=Envelope)
def get_settings(family_id: int, db: DbDep, current_user: CurrentUser):
    """Get family settings."""
    settings = service.get_settings(db, family_id, current_user.id)
    return Envelope(
        data={
            "id": settings.id,
            "family_id": settings.family_id,
            "notification_preferences": settings.notification_preferences,
            "version": settings.version,
            "created_at": settings.created_at.isoformat(),
            "updated_at": settings.updated_at.isoformat(),
        }
    )


@router.patch("/{family_id}/settings", response_model=Envelope)
def update_settings(
    family_id: int,
    payload: SettingsUpdate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Update family settings. Admin+ only."""
    settings = service.update_settings(db, family_id, payload, current_user.id)
    return Envelope(
        data={
            "id": settings.id,
            "family_id": settings.family_id,
            "notification_preferences": settings.notification_preferences,
            "version": settings.version,
        },
        message="Settings updated",
    )