from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.deps import get_db
from app.models.leaderboard_season import LeaderboardSeason
from app.schemas.admin import LeaderboardSeasonUpsert
from app.services.leaderboard_season_service import get_leaderboard_season

router = APIRouter(
    prefix="/admin/leaderboard-seasons", tags=["Admin Leaderboard Seasons"]
)


def _serialize(season: LeaderboardSeason) -> dict:
    return {
        "id": season.id,
        "season_name": season.season_name,
        "start_date": season.start_date.isoformat(),
        "end_date": season.end_date.isoformat(),
    }


@router.get("/")
def list_leaderboard_seasons(
    db: Session = Depends(get_db), admin=Depends(require_admin)
):
    rows = (
        db.query(LeaderboardSeason).order_by(LeaderboardSeason.season_name.asc()).all()
    )
    return [_serialize(row) for row in rows]


@router.put("/{season_name}")
def upsert_leaderboard_season(
    season_name: str,
    payload: LeaderboardSeasonUpsert,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    if payload.end_date < payload.start_date:
        raise HTTPException(
            status_code=400, detail="end_date must be on or after start_date"
        )

    season = get_leaderboard_season(db, season_name)
    if season is None:
        season = LeaderboardSeason(
            season_name=season_name,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
        db.add(season)
    else:
        season.start_date = payload.start_date
        season.end_date = payload.end_date

    db.commit()
    db.refresh(season)
    return _serialize(season)


@router.delete("/{season_name}")
def delete_leaderboard_season(
    season_name: str, db: Session = Depends(get_db), admin=Depends(require_admin)
):
    season = get_leaderboard_season(db, season_name)
    if season is None:
        raise HTTPException(status_code=404, detail="Season not found")

    db.delete(season)
    db.commit()
    return {"message": "Season deleted"}
