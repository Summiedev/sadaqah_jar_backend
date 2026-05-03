import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.core.auth import get_current_user
from app.models.family_jar import FamilyJar
from app.models.family_jar_log import FamilyJarLog
from app.models.family_jar_member import FamilyJarMember
from app.models.sadaqah_act import SadaqahAct
from app.models.user import User
from app.models.user_streak import UserStreak
from app.core.cache import get_cached_user_streak
from app.services.jumua_service import is_friday
from app.services.leaderboard_service import get_top_family, get_user_rank_ramadan, increment_family_leaderboard, get_user_rank_global
from app.tasks.scheduled_tasks import jar_completion_celebration
from app.services.ramadan_service import is_ramadan, is_last_10_nights
from app.services.family_service import update_family_streak_on_contribution
from app.core.ws_manager import manager
from app.utils.invite import generate_invite_code

router = APIRouter(prefix="/family", tags=["family"])

@router.post("/create")
def create_family_jar(name: str, capacity: int = 33, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Validate inputs
    if not name or len(name.strip()) == 0:
        raise HTTPException(status_code=400, detail="Family jar name cannot be empty")
    if len(name) > 100:
        raise HTTPException(status_code=400, detail="Family jar name too long (max 100 chars)")
    if capacity <= 0 or capacity > 1000:
        raise HTTPException(status_code=400, detail="Capacity must be between 1 and 1000")
    
    user_id = current_user.id
    jar = FamilyJar(name=name, capacity=capacity, created_by=user_id, invite_code=generate_invite_code())
    db.add(jar)
    db.commit()
    db.refresh(jar)

    # Add creator as member
    member = FamilyJarMember(family_jar_id=jar.id, user_id=user_id, role="creator")
    db.add(member)
    db.commit()

    return {"jar_id": jar.id, "name": jar.name, "capacity": jar.capacity, "invite_code": jar.invite_code}


@router.post("/join")
def join_family_jar(invite_code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    user_id = current_user.id

    jar = db.query(FamilyJar).filter(
        FamilyJar.invite_code == invite_code,
        FamilyJar.is_active == True
    ).first()

    if not jar:
        raise HTTPException(status_code=404, detail="Jar not found")

    # prevent duplicate joins
    existing = db.query(FamilyJarMember).filter(
        FamilyJarMember.family_jar_id == jar.id,
        FamilyJarMember.user_id == user_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already a member")

    member = FamilyJarMember(
        family_jar_id=jar.id,
        user_id=user_id
    )

    db.add(member)
    db.commit()

    return {"message": "Joined family jar", "jar_id": jar.id}

@router.post("/add-star")
async def add_star_family_jar(jar_id: int, act_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id
    today = datetime.date.today()
    jar = db.query(FamilyJar).filter(FamilyJar.id==jar_id, FamilyJar.is_active==True).first()
    if not jar:
        raise HTTPException(status_code=404, detail="Jar not found")

    # Verify user is a member
    is_member = db.query(FamilyJarMember).filter(
        FamilyJarMember.family_jar_id == jar.id,
        FamilyJarMember.user_id == user_id
    ).first()
    if not is_member:
        raise HTTPException(status_code=403, detail="Not a member of this jar")

    # Check daily log
    existing_log = db.query(FamilyJarLog).filter(
    FamilyJarLog.family_jar_id == jar.id,
    FamilyJarLog.user_id == current_user.id,
    FamilyJarLog.act_id == act_id,
    FamilyJarLog.date == today
).first()
    if existing_log:
        raise HTTPException(status_code=400, detail="Already added today")

    act = db.query(SadaqahAct).filter(SadaqahAct.id == act_id, SadaqahAct.verified == True).first()
    if not act:
        raise HTTPException(status_code=404, detail="Act not found")

    multiplier = act.reward_weight or 1
    if is_friday():
        multiplier *= 2
    if is_ramadan(today):
        multiplier *= act.ramadan_multiplier
    if is_last_10_nights(today):
        multiplier *= 2

    jar.current_stars += multiplier

    db.add(FamilyJarLog(family_jar_id=jar.id, user_id=current_user.id, act_id=act_id, stars_added=multiplier, date=today))
    db.commit()
    db.refresh(jar)
    
    

    
    increment_family_leaderboard(jar.id, current_user.id, multiplier)

# update family streak properly (call service)
    update_family_streak_on_contribution(db, jar.id, today)

    await manager.send_family_event(jar.id, {"event": "family_update", "current_stars": jar.current_stars})

    if jar.current_stars >= jar.capacity:
        jar.completed_at = datetime.datetime.utcnow()
        db.commit()
        jar_completion_celebration.delay(jar.id)

    return {"current_stars": jar.current_stars, "capacity": jar.capacity}

@router.get("/{jar_id}/leaderboard")
def family_leaderboard(jar_id: int, limit: int = 10):
    data = get_top_family(jar_id, limit)

    return [
        {"user_id": int(uid), "stars": int(score)}
        for uid, score in data
    ]
    
@router.get("/{jar_id}/top-contributor")
def top_contributor(jar_id: int):
    data = get_top_family(jar_id, 1)

    if not data:
        return {"message": "No contributions yet"}

    user_id, score = data[0]
    return {"user_id": int(user_id), "stars": int(score)}

