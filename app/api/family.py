import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.core.auth import get_current_user
from app.core.rate_limit import check_rate_limit
from app.models.family_jar import FamilyJar
from app.models.family_jar_log import FamilyJarLog
from app.models.family_jar_member import FamilyJarMember
from app.models.sadaqah_act import SadaqahAct
from app.models.user import User
from app.services.jumua_service import is_friday
from app.services.leaderboard_service import (
    get_top_family,
    increment_family_leaderboard,
)
from app.tasks.scheduled_tasks import family_jar_completion_celebration
from app.services.ramadan_service import is_ramadan, is_last_10_nights
from app.services.family_service import update_family_streak_on_contribution
from app.services.family_streak_service import check_family_badges
from app.services.badge_service import check_and_award_badges
from app.services.streak_service import update_streak
from app.core.ws_manager import manager
from app.utils.invite import generate_invite_code

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/family", tags=["family"])


def _require_membership(jar_id: int, user_id: int, db: Session) -> FamilyJarMember:
    member = (
        db.query(FamilyJarMember)
        .filter(
            FamilyJarMember.family_jar_id == jar_id,
            FamilyJarMember.user_id == user_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this jar")
    return member


def _require_admin(jar_id: int, user_id: int, db: Session) -> FamilyJarMember:
    """Return the member row if they have an admin/creator role, or raise 403."""
    member = _require_membership(jar_id, user_id, db)
    if member.role not in ("admin", "creator"):
        raise HTTPException(status_code=403, detail="Admin role required")
    return member


def require_family_member(
    jar_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FamilyJarMember:
    return _require_membership(jar_id, current_user.id, db)


@router.post("/create")
def create_family_jar(
    name: str,
    capacity: int = 33,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate inputs
    if not name or len(name.strip()) == 0:
        raise HTTPException(status_code=400, detail="Family jar name cannot be empty")
    if len(name) > 100:
        raise HTTPException(
            status_code=400, detail="Family jar name too long (max 100 chars)"
        )
    if capacity <= 0 or capacity > 1000:
        raise HTTPException(
            status_code=400, detail="Capacity must be between 1 and 1000"
        )

    user_id = current_user.id
    jar = FamilyJar(
        name=name,
        capacity=capacity,
        created_by=user_id,
        invite_code=generate_invite_code(),
    )
    db.add(jar)
    db.commit()
    db.refresh(jar)

    # Add creator as member
    member = FamilyJarMember(family_jar_id=jar.id, user_id=user_id, role="creator")
    db.add(member)
    db.commit()

    return {
        "jar_id": jar.id,
        "name": jar.name,
        "capacity": jar.capacity,
        "invite_code": jar.invite_code,
    }


@router.post("/join")
def join_family_jar(
    invite_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    user_id = current_user.id

    jar = (
        db.query(FamilyJar)
        .filter(FamilyJar.invite_code == invite_code, FamilyJar.is_active)
        .first()
    )

    if not jar:
        raise HTTPException(status_code=404, detail="Jar not found")

    # prevent duplicate joins
    existing = (
        db.query(FamilyJarMember)
        .filter(
            FamilyJarMember.family_jar_id == jar.id, FamilyJarMember.user_id == user_id
        )
        .first()
    )

    if existing:
        raise HTTPException(status_code=400, detail="Already a member")

    member = FamilyJarMember(family_jar_id=jar.id, user_id=user_id)

    db.add(member)
    db.commit()

    return {"message": "Joined family jar", "jar_id": jar.id}


@router.get("/mine")
def list_my_jars(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Authorization: get_current_user — returns only jars the caller belongs to.
    No additional check needed; the query is scoped to current_user.id.
    """
    user_id = current_user.id

    # Subquery: member count per jar (unfiltered — counts all members)
    member_count_subq = (
        db.query(
            FamilyJarMember.family_jar_id,
            func.count(FamilyJarMember.id).label("cnt"),
        )
        .group_by(FamilyJarMember.family_jar_id)
        .subquery()
    )

    rows = (
        db.query(
            FamilyJar.id,
            FamilyJar.name,
            FamilyJar.current_stars,
            FamilyJar.capacity,
            FamilyJar.completed_at,
            FamilyJar.is_active,
            FamilyJarMember.role,
            member_count_subq.c.cnt,
        )
        .join(FamilyJarMember, FamilyJarMember.family_jar_id == FamilyJar.id)
        .outerjoin(member_count_subq, member_count_subq.c.family_jar_id == FamilyJar.id)
        .filter(FamilyJarMember.user_id == user_id)
        .order_by(FamilyJar.created_at.desc())
        .all()
    )

    return [
        {
            "id": row.id,
            "name": row.name,
            "current_stars": row.current_stars,
            "capacity": row.capacity,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            "is_active": row.is_active,
            "role": row.role,
            "member_count": row.cnt,
        }
        for row in rows
    ]


@router.get("/{jar_id}")
def get_jar_detail(
    jar_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Authorization: get_current_user + _require_membership (403 if not a member).
    """
    user_id = current_user.id
    _require_membership(jar_id, user_id, db)

    jar = db.query(FamilyJar).filter(FamilyJar.id == jar_id).first()
    if not jar:
        raise HTTPException(status_code=404, detail="Jar not found")

    # Per-member contribution totals via grouped query
    member_contributions = (
        db.query(
            FamilyJarLog.user_id,
            func.sum(FamilyJarLog.stars_added).label("total_stars"),
            func.count(FamilyJarLog.id).label("total_acts"),
        )
        .filter(FamilyJarLog.family_jar_id == jar_id)
        .group_by(FamilyJarLog.user_id)
        .all()
    )
    contrib_map = {
        row.user_id: {"stars": int(row.total_stars or 0), "acts": row.total_acts}
        for row in member_contributions
    }

    members = (
        db.query(FamilyJarMember, User.username)
        .join(User, User.id == FamilyJarMember.user_id)
        .filter(FamilyJarMember.family_jar_id == jar_id)
        .all()
    )

    return {
        "id": jar.id,
        "name": jar.name,
        "invite_code": jar.invite_code,
        "capacity": jar.capacity,
        "current_stars": jar.current_stars,
        "completed_at": jar.completed_at.isoformat() if jar.completed_at else None,
        "is_active": jar.is_active,
        "created_at": jar.created_at.isoformat() if jar.created_at else None,
        "current_user_id": user_id,
        "group_current_streak": jar.group_current_streak,
        "group_longest_streak": jar.group_longest_streak,
        "members": [
            {
                "user_id": m.FamilyJarMember.user_id,
                "username": m.username,
                "role": m.FamilyJarMember.role,
                "joined_at": m.FamilyJarMember.joined_at.isoformat()
                if m.FamilyJarMember.joined_at
                else None,
                "contribution": contrib_map.get(
                    m.FamilyJarMember.user_id, {"stars": 0, "acts": 0}
                ),
            }
            for m in members
        ],
    }


@router.post("/{jar_id}/leave")
def leave_jar(
    jar_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Authorization: get_current_user + _require_membership (403 if not a member).
    If the caller is the last member, raise 400 — they must delete the jar instead.
    """
    user_id = current_user.id
    member = _require_membership(jar_id, user_id, db)

    member_count = (
        db.query(func.count(FamilyJarMember.id))
        .filter(FamilyJarMember.family_jar_id == jar_id)
        .scalar()
    )

    if member_count <= 1:
        raise HTTPException(
            status_code=400,
            detail="You are the only member. Delete the jar instead of leaving.",
        )

    db.delete(member)
    db.commit()

    return {"status": "ok"}


@router.delete("/{jar_id}/members/{target_user_id}")
def remove_member(
    jar_id: int,
    target_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Authorization: get_current_user + _require_admin (403 if caller is not admin/creator).
    The admin cannot remove themselves via this endpoint (use /leave instead).
    """
    user_id = current_user.id
    _require_admin(jar_id, user_id, db)

    if target_user_id == user_id:
        raise HTTPException(status_code=400, detail="Use /leave to remove yourself")

    target = (
        db.query(FamilyJarMember)
        .filter(
            FamilyJarMember.family_jar_id == jar_id,
            FamilyJarMember.user_id == target_user_id,
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(target)
    db.commit()

    return {"status": "ok"}


def _jar_snapshot(jar: FamilyJar) -> dict:
    return {
        "current_stars": jar.current_stars,
        "capacity": jar.capacity,
        "completed_at": jar.completed_at,
    }


def _log_snapshot(log: FamilyJarLog) -> dict:
    if log.response_current_stars is None or log.response_capacity is None:
        return {
            "current_stars": 0,
            "capacity": 0,
            "completed_at": log.response_completed_at,
        }
    return {
        "current_stars": log.response_current_stars,
        "capacity": log.response_capacity,
        "completed_at": log.response_completed_at,
    }


def _lookup_family_request_result(
    db: Session, user_id: int, jar_id: int, request_id: str
) -> dict | None:
    log = (
        db.query(FamilyJarLog)
        .filter(
            FamilyJarLog.user_id == user_id,
            FamilyJarLog.family_jar_id == jar_id,
            FamilyJarLog.request_id == request_id,
        )
        .first()
    )
    if not log:
        return None
    return _log_snapshot(log)


@router.post("/add-star")
async def add_star_family_jar(
    jar_id: int,
    act_id: int,
    request_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if act_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid act ID")

    user_id = current_user.id
    request_id = request_id.strip() if request_id else None

    # Rate limit (raise HTTP 429 if exceeded)
    if not check_rate_limit(user_id, limit=5, period=60):
        raise HTTPException(status_code=429, detail="Too many requests")

    today = datetime.now(timezone.utc).date()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    try:
        # 1) Row-level lock on the FamilyJar to prevent concurrent read-modify-write races.
        #    This is the critical fix: any concurrent transaction attempting to modify the
        #    same jar will wait here rather than corrupting current_stars.
        jar = (
            db.query(FamilyJar)
            .filter(FamilyJar.id == jar_id, FamilyJar.is_active)
            .with_for_update()
            .first()
        )
        if not jar:
            raise HTTPException(status_code=404, detail="Jar not found")

        # 2) Idempotency check — if this client_request_id was already processed,
        #    return the previous response snapshot (no-op).
        if request_id:
            existing_result = _lookup_family_request_result(
                db, user_id, jar_id, request_id
            )
            if existing_result is not None:
                return existing_result

        # 3) Verify membership inside the locked transaction.
        _require_membership(jar_id, user_id, db)

        # 4) Deduplicate same act same day per user.
        existing_log = (
            db.query(FamilyJarLog)
            .filter(
                FamilyJarLog.family_jar_id == jar.id,
                FamilyJarLog.user_id == user_id,
                FamilyJarLog.act_id == act_id,
                FamilyJarLog.date == today,
            )
            .first()
        )
        if existing_log:
            raise HTTPException(status_code=400, detail="Already added today")

        # 5) Validate act.
        act = (
            db.query(SadaqahAct)
            .filter(SadaqahAct.id == act_id, SadaqahAct.verified)
            .first()
        )
        if not act:
            raise HTTPException(status_code=404, detail="Act not found")

        # 6) Compute multiplier.
        multiplier = act.reward_weight or 1
        friday = is_friday()
        ramadan = is_ramadan(today)
        last10 = is_last_10_nights(today)

        if friday:
            multiplier *= 2
        if ramadan:
            multiplier *= act.ramadan_multiplier
        if last10:
            multiplier *= 2

        # 7) Create the log entry with pre-commit snapshot of jar state.
        log = FamilyJarLog(
            family_jar_id=jar.id,
            user_id=user_id,
            act_id=act_id,
            request_id=request_id,
            stars_added=multiplier,
            date=today,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            response_current_stars=jar.current_stars,
            response_capacity=jar.capacity,
            response_completed_at=jar.completed_at,
        )
        db.add(log)

        # 8) Atomic in-transaction updates.
        jar.current_stars += multiplier
        update_family_streak_on_contribution(jar, today)

        if jar.current_stars >= jar.capacity:
            jar.completed_at = now
            jar.is_active = False

        # 9) Update the log snapshot after mutation.
        log.response_current_stars = jar.current_stars
        log.response_capacity = jar.capacity
        log.response_completed_at = jar.completed_at

        # 10) Personal streak + badge logic in the same transaction.
        update_streak(db, user_id, commit=False)
        check_and_award_badges(db, user_id, commit=False)
        check_family_badges(db, jar_id)

        db.commit()
        db.refresh(jar)
    except IntegrityError:
        db.rollback()
        if request_id:
            existing_result = _lookup_family_request_result(
                db, user_id, jar_id, request_id
            )
            if existing_result is not None:
                return existing_result
        raise
    except Exception:
        db.rollback()
        raise

    # === Post-commit side-effects (non-critical failures are logged, never block the response) ===

    try:
        increment_family_leaderboard(jar.id, user_id, multiplier)
    except Exception:
        logger.exception(
            "Failed to update family leaderboard cache for jar %s user %s",
            jar_id,
            user_id,
        )

    try:
        await manager.send_family_event(
            jar.id,
            {
                "event": "family_update",
                "current_stars": jar.current_stars,
                "capacity": jar.capacity,
            },
        )
    except Exception:
        logger.exception("Failed to broadcast family update for jar %s", jar_id)

    if jar.completed_at:
        try:
            family_jar_completion_celebration.delay(jar.id)
        except Exception:
            logger.exception(
                "Failed to queue family jar completion celebration for jar %s", jar_id
            )

    return _jar_snapshot(jar)


@router.get("/{jar_id}/leaderboard")
def family_leaderboard(
    jar_id: int,
    limit: int = 10,
    member: FamilyJarMember = Depends(require_family_member),
):
    data = get_top_family(jar_id, limit)

    return [{"user_id": int(uid), "stars": int(score)} for uid, score in data]


@router.get("/{jar_id}/top-contributor")
def top_contributor(
    jar_id: int, member: FamilyJarMember = Depends(require_family_member)
):
    data = get_top_family(jar_id, 1)

    if not data:
        return {"message": "No contributions yet"}

    user_id, score = data[0]
    return {"user_id": int(user_id), "stars": int(score)}
