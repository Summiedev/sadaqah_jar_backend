import logging
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.rate_limit import check_rate_limit
from app.db.deps import get_db
from app.models.user import User
from app.models.jar import Jar
from app.models.sadaqah_act import SadaqahAct
from app.models.sadaqah_log import SadaqahLog

from app.core.auth import get_current_user
from app.core.cache import cache_daily_acts, get_cached_daily_acts
from app.core.ws_manager import manager
from app.models.evidence import Evidence
from app.schemas.sadaqah_act import (
    ActDetailResponse,
    ActListResponse,
    ActPageResponse,
    EvidenceResponse,
)

from app.services.streak_service import update_streak
from app.services.badge_service import check_and_award_badges

from app.services.hijri_service import is_last_10_nights as hijri_last10
from app.services.hijri_service import is_ramadan as hijri_is_ramadan
from app.services.jumua_service import is_friday
from app.services.ramadan_service import is_ramadan, is_last_10_nights
from app.services.leaderboard_service import (
    increment_friday,
    increment_global,
    increment_ramadan,
    increment_weekly,
)

from app.tasks.scheduled_tasks import jar_completion_celebration

router = APIRouter(prefix="/sadaqah", tags=["sadaqah"])
logger = logging.getLogger(__name__)


@router.get("/daily")
def get_daily_acts(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):

    user_id = current_user.id

    if not check_rate_limit(user_id, limit=60, period=60):
        raise HTTPException(status_code=429, detail="Too many requests")

    cached = get_cached_daily_acts(user_id)
    if cached:
        return cached

    if is_ramadan():
        acts = (
            db.query(SadaqahAct)
            .filter(SadaqahAct.verified)
            .order_by(func.random())
            .limit(20)
            .all()
        )
    else:
        acts = (
            db.query(SadaqahAct)
            .filter(SadaqahAct.verified, not SadaqahAct.is_ramadan_only)
            .order_by(func.random())
            .limit(20)
            .all()
        )

    response = [
        {
            "id": act.id,
            "title": act.title,
            "category": act.category,
            "difficulty": act.difficulty,
        }
        for act in acts[:5]
    ]

    cache_daily_acts(user_id, response)

    return response


@router.get("/acts", response_model=ActPageResponse)
def list_acts(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if limit < 1:
        limit = 20
    if limit > 100:
        limit = 100
    if offset < 0:
        offset = 0

    total = db.query(func.count(SadaqahAct.id)).scalar()
    rows = (
        db.query(SadaqahAct).order_by(SadaqahAct.id).offset(offset).limit(limit).all()
    )
    return ActPageResponse(
        total=total or 0,
        limit=limit,
        offset=offset,
        data=[ActListResponse.model_validate(a) for a in rows],
    )


@router.get("/acts/{act_id}", response_model=ActDetailResponse)
def get_act_detail(
    act_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    act = db.query(SadaqahAct).filter(SadaqahAct.id == act_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Act not found")

    evidence_row = db.query(Evidence).filter(Evidence.act_id == act_id).first()

    return ActDetailResponse(
        id=act.id,
        title=act.title,
        description=act.description,
        category=act.category.value
        if hasattr(act.category, "value")
        else str(act.category),
        difficulty=act.difficulty,
        reward_weight=act.reward_weight,
        evidence=EvidenceResponse(
            source_type=evidence_row.source_type,
            reference=evidence_row.reference,
            grade=evidence_row.grade,
            arabic_text=evidence_row.arabic_text,
            english_text=evidence_row.english_text,
            is_verified=evidence_row.is_verified,
        )
        if evidence_row
        else None,
    )


def _jar_snapshot(jar: Jar) -> dict:
    return {
        "current_stars": jar.current_stars,
        "capacity": jar.capacity,
        "completed_at": jar.completed_at,
    }


def _log_snapshot(log: SadaqahLog) -> dict:
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


def _lookup_request_result(db: Session, user_id: int, request_id: str) -> dict | None:
    log = (
        db.query(SadaqahLog)
        .filter(
            SadaqahLog.user_id == user_id,
            SadaqahLog.request_id == request_id,
        )
        .first()
    )
    if not log:
        return None
    return _log_snapshot(log)


@router.post("/jar/add-star")
async def add_star(
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

    today = datetime.utcnow().date()

    try:
        # Idempotency check — must happen inside the transaction to avoid
        # insert-vs-read races when the same request_id arrives concurrently.
        if request_id:
            existing_request = _lookup_request_result(db, user_id, request_id)
            if existing_request is not None:
                return existing_request

        # Validate the act exists and is verified.
        act = (
            db.query(SadaqahAct)
            .filter(SadaqahAct.id == act_id, SadaqahAct.verified)
            .first()
        )
        if not act:
            raise HTTPException(status_code=404, detail="Act not found")

        # Ensure we haven't already logged this act today for this user.
        existing = (
            db.query(SadaqahLog)
            .filter(
                SadaqahLog.user_id == user_id,
                SadaqahLog.act_id == act_id,
                SadaqahLog.date == today,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Already added today")

        # Compute multiplier.
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

        now = datetime.utcnow()

        # ── Atomic star increment ──────────────────────────────────────────
        # Use a single UPDATE to avoid the lost-update race that a
        # read-modify-write would allow.  The FOR UPDATE on the user row
        # serialises concurrent add-star requests for the same user so that
        # only one caller wins the capacity-at-limit trigger race.

        db.query(User.id).filter(User.id == user_id).with_for_update().one()

        # Find or create the active jar.
        active_jar = (
            db.query(Jar)
            .filter(Jar.user_id == user_id, Jar.completed_at.is_(None))
            .with_for_update()
            .first()
        )
        if not active_jar:
            active_jar = Jar(user_id=user_id)
            db.add(active_jar)
            db.flush()

        active_jar.current_stars += multiplier

        just_completed = False
        if (
            active_jar.current_stars >= active_jar.capacity
            and not active_jar.completed_at
        ):
            active_jar.completed_at = now
            just_completed = True

            # Create the replacement jar immediately so there is never an
            # intermediate state where the old jar is full but no new jar
            # exists.  The next add-star will pick this one up.
            new_jar = Jar(user_id=user_id)
            db.add(new_jar)
            db.flush()

        # Create the log row.
        log = SadaqahLog(
            user_id=user_id,
            act_id=act_id,
            request_id=request_id,
            date=today,
            created_at=now,
            stars_earned=multiplier,
            friday_boost=friday,
            ramadan_bonus=ramadan,
            response_current_stars=active_jar.current_stars,
            response_capacity=active_jar.capacity,
            response_completed_at=active_jar.completed_at,
        )
        db.add(log)

        # Keep streak/badge updates in the same database transaction as the
        # star increment — if these fail the star increment rolls back too.
        streak = update_streak(db, user_id, commit=False)
        check_and_award_badges(db, user_id, commit=False)

        log.response_current_stars = active_jar.current_stars
        log.response_capacity = active_jar.capacity
        log.response_completed_at = active_jar.completed_at

        db.commit()
        db.refresh(active_jar)
        db.refresh(streak)
    except IntegrityError:
        db.rollback()
        if request_id:
            existing_request = _lookup_request_result(db, user_id, request_id)
            if existing_request is not None:
                return existing_request
        raise
    except Exception:
        db.rollback()
        raise

    # ── Post-commit side effects ──────────────────────────────────────────
    # Leaderboard updates and websocket delivery are safe to fail without
    # rolling back the database write.  Log and continue.

    try:
        increment_global(user_id, multiplier)
        increment_weekly(user_id, multiplier)
        if ramadan:
            increment_ramadan(user_id, multiplier)
        if friday:
            increment_friday(user_id, multiplier)
    except Exception:
        logger.exception("Failed to update leaderboard caches for user %s", user_id)

    try:
        await manager.send_user_event(
            user_id,
            {
                "event": "jar_update",
                "current_stars": active_jar.current_stars,
                "capacity": active_jar.capacity,
                "streak": {
                    "current": streak.current_streak,
                    "longest": streak.longest_streak,
                },
            },
        )
    except Exception:
        logger.exception("Failed to broadcast jar update for user %s", user_id)

    if just_completed:
        try:
            jar_completion_celebration.delay(active_jar.user_id)
        except Exception:
            logger.exception(
                "Failed to queue jar completion celebration for user %s",
                active_jar.user_id,
            )

    return _jar_snapshot(active_jar)


@router.get("/jars/completed")
def list_completed_jars(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if limit < 1:
        limit = 20
    if limit > 100:
        limit = 100
    if offset < 0:
        offset = 0

    base_query = db.query(Jar).filter(
        Jar.user_id == current_user.id,
        Jar.completed_at.isnot(None),
    )

    total = base_query.count()

    rows = (
        base_query.order_by(Jar.completed_at.desc()).offset(offset).limit(limit).all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": j.id,
                "current_stars": j.current_stars,
                "capacity": j.capacity,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "days_to_complete": (j.completed_at - j.created_at).days
                if j.completed_at and j.created_at
                else None,
            }
            for j in rows
        ],
    }


@router.get("/jar")
def get_jar(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):

    user_id = current_user.id

    today = datetime.utcnow().date()
    mode_parts = []
    if hijri_is_ramadan(today):
        mode_parts.append("ramadan")
    if is_friday():
        mode_parts.append("friday")
    if hijri_last10(today):
        mode_parts.append("last_10_nights")
    current_mode = mode_parts[0] if mode_parts else "normal"

    jar = (
        db.query(Jar).filter(Jar.user_id == user_id, Jar.completed_at.is_(None)).first()
    )

    if not jar:
        return {"current_stars": 0, "capacity": 33, "current_mode": current_mode}

    return {
        "current_stars": jar.current_stars,
        "capacity": jar.capacity,
        "completed_at": jar.completed_at,
        "current_mode": current_mode,
    }
