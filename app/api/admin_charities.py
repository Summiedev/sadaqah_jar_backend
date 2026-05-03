from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.charity import Charity
from app.schemas.admin import CharityCreate

router = APIRouter(prefix="/admin/charities", tags=["Admin Charities"])

@router.post("/")
def create_charity(
    payload: CharityCreate,
    db: Session = Depends(get_db),
    admin = Depends(require_admin),
):
    charity = Charity(
        name=payload.name,
        website_url=str(payload.website_url),
        description=payload.description,
        category=payload.category,
        is_verified=True
    )

    db.add(charity)
    db.commit()
    db.refresh(charity)

    return charity

@router.put("/{charity_id}/deactivate")
def deactivate_charity(charity_id: int, db: Session = Depends(get_db), admin = Depends(require_admin)):
    charity = db.query(Charity).filter(Charity.id == charity_id).first()

    if not charity:
        raise HTTPException(status_code=404, detail="Charity not found")

    charity.is_active = False
    db.commit()

    return {"message": "Charity deactivated"}

@router.put("/{charity_id}/feature")
def feature_charity(charity_id: int, db: Session = Depends(get_db), admin = Depends(require_admin)):
    charity = db.query(Charity).filter(Charity.id == charity_id).first()

    if not charity:
        raise HTTPException(status_code=404, detail="Charity not found")

    charity.is_featured = True
    db.commit()

    return {"message": "Charity featured"}
