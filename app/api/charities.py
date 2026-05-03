from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.charity import Charity

router = APIRouter(prefix="/charities", tags=["Charities"])


@router.get("/")
def list_charities(category: str = None, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    query = db.query(Charity).filter(Charity.is_verified == True, Charity.is_active == True)
    if category:
        query = query.filter(Charity.category == category)
    total = query.count()
    rows = query.order_by(Charity.name).limit(limit).offset(offset).all()
    return {"total": total, "limit": limit, "offset": offset, "data": rows}

@router.get("/featured")
def featured_charities(db: Session = Depends(get_db)):
    return db.query(Charity).filter(
        Charity.is_verified == True,
        Charity.is_active == True,
        Charity.is_featured == True
    ).all()