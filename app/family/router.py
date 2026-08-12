"""Family domain router.

Thin endpoints — all business logic and authorization lives in the service layer.
Follows REST conventions with consistent response envelopes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.envelope import Envelope, Meta
from app.db.deps import get_db
from app.users.dependencies import get_current_user
from app.users.models import User
from app.family import service
from app.family.models import InvitationStatus
from app.family.schemas import (
    FamilyCreate,
    FamilyUpdate,
    FamilyActCreate,
    GoalCreate,
    GoalUpdate,
    PrayerRequestCreate,
    PrayerRespond,
    PrayerCommentCreate,
    ReflectionCreate,
    ReflectionEncourage,
    ReflectionCommentCreate,
    SettingsUpdate,
    MemberRoleUpdate,
    JoinRequest,
    FamilyGoalMilestoneCreate,
    FamilyGoalMilestoneUpdate,
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


@router.post("/create", response_model=Envelope, status_code=status.HTTP_201_CREATED)
def create_family_legacy(
    db: DbDep,
    current_user: CurrentUser,
    name: str = Query(..., min_length=1),
    capacity: int = Query(33, ge=1),
):
    """Legacy alias for POST /family/. Accepts query params for frontend compatibility."""
    family, event = service.create_family(
        db, FamilyCreate(name=name, cover_icon=None), current_user.id
    )
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
    return Envelope(data=None, message="Family deleted")


@router.post("/{family_id}/archive", response_model=Envelope)
def archive_family(family_id: int, db: DbDep, current_user: CurrentUser):
    """Archive a family. Owner only."""
    service.archive_family(db, family_id, current_user.id)
    return Envelope(data=None, message="Family archived")


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
    member = service.update_member_role(
        db, family_id, member_id, payload, current_user.id
    )
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
    return Envelope(data=None, message="Member removed")


@router.post("/{family_id}/leave", response_model=Envelope)
def leave_family(family_id: int, db: DbDep, current_user: CurrentUser):
    """Leave a family. Self-removal."""
    service.leave_family(db, family_id, current_user.id)
    return Envelope(data=None, message="Left family")


@router.get("/{family_id}/leaderboard", response_model=Envelope)
def get_leaderboard(
    family_id: int,
    db: DbDep,
    current_user: CurrentUser,
    limit: int = Query(10, ge=1, le=50),
):
    """Family leaderboard."""
    data = service.get_leaderboard(db, family_id, current_user.id, limit=limit)
    return Envelope(data=data)


@router.get("/{family_id}/top-contributor", response_model=Envelope)
def get_top_contributor(family_id: int, db: DbDep, current_user: CurrentUser):
    """Top contributor for a family."""
    data = service.get_top_contributor(db, family_id, current_user.id)
    return Envelope(data=data)


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


@router.get("/invitations", response_model=Envelope)
def list_all_invitations(db: DbDep, current_user: CurrentUser):
    """List all pending invitations across families the user is a member of."""
    families = service.list_user_families(db, current_user.id)
    results = []
    for family in families:
        invitations = service.list_invitations(db, family.id, current_user.id)
        for inv in invitations:
            if inv.status == InvitationStatus.PENDING:
                results.append(
                    {
                        "id": inv.id,
                        "family_id": inv.family_id,
                        "family_name": family.name,
                        "invite_code": inv.invite_code,
                        "status": inv.status.value,
                        "created_at": inv.created_at.isoformat(),
                        "expires_at": inv.expires_at.isoformat(),
                    }
                )
    return Envelope(data=results)


@router.post(
    "/{family_id}/invitations",
    response_model=Envelope,
    status_code=status.HTTP_201_CREATED,
)
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
    return Envelope(data=None, message="Invitation cancelled")


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
    return Envelope(data=None, message="Invitation declined")


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
    goals = service.list_goals(
        db, family_id, current_user.id, include_archived=include_archived
    )
    return Envelope(data=goals)


@router.post(
    "/{family_id}/goals", response_model=Envelope, status_code=status.HTTP_201_CREATED
)
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
            "completed_at": goal.completed_at.isoformat()
            if goal.completed_at
            else None,
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
    return Envelope(data=None, message="Goal archived")


@router.delete("/{family_id}/goals/{goal_id}", response_model=Envelope)
def delete_goal(
    family_id: int,
    goal_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    """Soft-delete a goal."""
    service.delete_goal(db, family_id, goal_id, current_user.id)
    return Envelope(data=None, message="Goal deleted")


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------


@router.get("/{family_id}/goals/{goal_id}/milestones", response_model=Envelope)
def list_milestones(
    family_id: int,
    goal_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    """List milestones for a family goal."""
    milestones = service.list_milestones(db, family_id, goal_id, current_user.id)
    return Envelope(data=milestones)


@router.post(
    "/{family_id}/goals/{goal_id}/milestones",
    response_model=Envelope,
    status_code=status.HTTP_201_CREATED,
)
def create_milestone(
    family_id: int,
    goal_id: int,
    payload: FamilyGoalMilestoneCreate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Create a milestone for a family goal."""
    milestone = service.create_milestone(
        db, family_id, goal_id, payload, current_user.id
    )
    return Envelope(
        data={
            "id": milestone.id,
            "goal_id": milestone.goal_id,
            "title": milestone.title,
            "target_value": milestone.target_value,
            "created_at": milestone.created_at.isoformat(),
        },
        message="Milestone created",
    )


@router.patch(
    "/{family_id}/goals/{goal_id}/milestones/{milestone_id}", response_model=Envelope
)
def update_milestone(
    family_id: int,
    goal_id: int,
    milestone_id: int,
    payload: FamilyGoalMilestoneUpdate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Update a milestone."""
    milestone = service.update_milestone(
        db, family_id, goal_id, milestone_id, payload, current_user.id
    )
    return Envelope(
        data={
            "id": milestone.id,
            "title": milestone.title,
            "current_value": milestone.current_value,
            "target_value": milestone.target_value,
        },
        message="Milestone updated",
    )


@router.post(
    "/{family_id}/goals/{goal_id}/milestones/{milestone_id}/achieve",
    response_model=Envelope,
)
def achieve_milestone(
    family_id: int,
    goal_id: int,
    milestone_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    """Mark a milestone as achieved."""
    milestone = service.achieve_milestone(
        db, family_id, goal_id, milestone_id, current_user.id
    )
    return Envelope(
        data={
            "id": milestone.id,
            "title": milestone.title,
            "is_achieved": milestone.is_achieved,
            "achieved_at": milestone.achieved_at.isoformat()
            if milestone.achieved_at
            else None,
        },
        message="Milestone achieved",
    )


@router.delete(
    "/{family_id}/goals/{goal_id}/milestones/{milestone_id}", response_model=Envelope
)
def delete_milestone(
    family_id: int,
    goal_id: int,
    milestone_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    """Delete a milestone."""
    service.delete_milestone(db, family_id, goal_id, milestone_id, current_user.id)
    return Envelope(data=None, message="Milestone deleted")


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
        db,
        family_id,
        current_user.id,
        include_answered=include_answered,
        limit=limit,
        offset=offset,
    )
    return Envelope(
        data=prayers,
        meta=Meta(total=total),
    )


@router.post(
    "/{family_id}/prayers", response_model=Envelope, status_code=status.HTTP_201_CREATED
)
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
    counts = service.respond_to_prayer(
        db, family_id, prayer_id, payload, current_user.id
    )
    return Envelope(data={"response_counts": counts})


@router.get("/{family_id}/prayers/{prayer_id}/comments", response_model=Envelope)
def list_prayer_comments(
    family_id: int,
    prayer_id: int,
    db: DbDep,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List comments for a prayer request."""
    comments, total = service.list_prayer_comments(
        db, family_id, prayer_id, current_user.id, limit=limit, offset=offset
    )
    return Envelope(
        data=comments,
        meta=Meta(total=total),
    )


@router.post(
    "/{family_id}/prayers/{prayer_id}/comments",
    response_model=Envelope,
    status_code=status.HTTP_201_CREATED,
)
def create_prayer_comment(
    family_id: int,
    prayer_id: int,
    payload: PrayerCommentCreate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Add a comment to a prayer request."""
    comment = service.create_prayer_comment(
        db, family_id, prayer_id, payload, current_user.id
    )
    return Envelope(
        data={
            "id": comment.id,
            "text": comment.text,
            "author_id": comment.author_id,
            "created_at": comment.created_at.isoformat(),
        },
        message="Comment added",
    )


@router.patch(
    "/{family_id}/prayers/{prayer_id}/comments/{comment_id}", response_model=Envelope
)
def update_prayer_comment(
    family_id: int,
    prayer_id: int,
    comment_id: int,
    payload: PrayerCommentCreate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Edit a comment. Author only."""
    comment = service.update_prayer_comment(
        db, family_id, prayer_id, comment_id, payload, current_user.id
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return Envelope(
        data={
            "id": comment.id,
            "text": comment.text,
        },
        message="Comment updated",
    )


@router.delete(
    "/{family_id}/prayers/{prayer_id}/comments/{comment_id}", response_model=Envelope
)
def delete_prayer_comment(
    family_id: int,
    prayer_id: int,
    comment_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    """Delete a comment. Author only."""
    service.delete_prayer_comment(db, family_id, prayer_id, comment_id, current_user.id)
    return Envelope(data=None, message="Comment deleted")


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


@router.post(
    "/{family_id}/reflections",
    response_model=Envelope,
    status_code=status.HTTP_201_CREATED,
)
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


@router.patch("/{family_id}/reflections/{reflection_id}", response_model=Envelope)
def update_reflection(
    family_id: int,
    reflection_id: int,
    payload: ReflectionCreate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Edit a reflection. Author only."""
    reflection = service.update_reflection(
        db, family_id, reflection_id, payload, current_user.id
    )
    return Envelope(
        data={
            "id": reflection.id,
            "text": reflection.text,
            "created_at": reflection.created_at.isoformat(),
        },
        message="Reflection updated",
    )


@router.delete("/{family_id}/reflections/{reflection_id}", response_model=Envelope)
def delete_reflection(
    family_id: int,
    reflection_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    """Delete a reflection. Author only."""

    service.delete_reflection(db, family_id, reflection_id, current_user.id)
    return Envelope(data=None, message="Reflection deleted")


@router.post(
    "/{family_id}/reflections/{reflection_id}/encourage", response_model=Envelope
)
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


@router.get(
    "/{family_id}/reflections/{reflection_id}/comments", response_model=Envelope
)
def list_reflection_comments(
    family_id: int,
    reflection_id: int,
    db: DbDep,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    comments, total = service.list_reflection_comments(
        db, family_id, reflection_id, current_user.id, limit=limit, offset=offset
    )
    return Envelope(data=comments, meta=Meta(total=total))


@router.post(
    "/{family_id}/reflections/{reflection_id}/comments",
    response_model=Envelope,
    status_code=status.HTTP_201_CREATED,
)
def create_reflection_comment(
    family_id: int,
    reflection_id: int,
    payload: ReflectionCommentCreate,
    db: DbDep,
    current_user: CurrentUser,
):
    comment = service.create_reflection_comment(
        db, family_id, reflection_id, payload, current_user.id
    )
    return Envelope(
        data={
            "id": comment.id,
            "reflection_id": comment.reflection_id,
            "author_id": comment.author_id,
            "text": comment.text,
            "created_at": comment.created_at.isoformat(),
        },
        message="Comment added",
    )


@router.delete(
    "/{family_id}/reflections/{reflection_id}/comments/{comment_id}",
    response_model=Envelope,
)
def delete_reflection_comment(
    family_id: int,
    reflection_id: int,
    comment_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    service.delete_reflection_comment(
        db, family_id, reflection_id, comment_id, current_user.id
    )
    return Envelope(data=None, message="Comment deleted")


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
    page = service.list_activities(
        db, family_id, current_user.id, limit=limit, cursor=cursor
    )
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


@router.post("/{family_id}/add-act", response_model=Envelope)
def add_family_act(
    family_id: int,
    db: DbDep,
    current_user: CurrentUser,
    payload: FamilyActCreate | None = None,
    request_id: str | None = None,
):
    """Add an act to the family jar. Increments the active goal's acts_done."""
    act_type = payload.act_type if payload else "sadaqah"
    note = payload.note if payload else None
    final_request_id = (
        payload.request_id if payload and payload.request_id else request_id
    )
    result = service.add_family_act(
        db,
        family_id,
        current_user.id,
        act_type=act_type,
        note=note,
        request_id=final_request_id,
    )
    return Envelope(data=result, message="Act added to family jar")
