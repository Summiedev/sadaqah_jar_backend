from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.charity import Charity
from app.schemas.admin import CharityCreate, CharityUpdate

router = APIRouter(prefix="/admin/charities", tags=["Admin Charities"])


def _serialize_charity(charity: Charity) -> dict:
    return {
        "id": charity.id,
        "name": charity.name,
        "description": charity.description,
        "website_url": charity.website_url,
        "category": charity.category,
        "is_verified": charity.is_verified,
        "is_active": charity.is_active,
        "is_featured": charity.is_featured,
    }


@router.get("/")
def list_charities(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin = Depends(require_admin),
):
    query = db.query(Charity).order_by(Charity.id.desc())
    total = query.count()
    rows = query.offset(offset).limit(limit).all()
    return {"total": total, "limit": limit, "offset": offset, "data": [_serialize_charity(charity) for charity in rows]}


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

    return _serialize_charity(charity)


@router.patch("/{charity_id}")
def update_charity(
    charity_id: int,
    payload: CharityUpdate,
    db: Session = Depends(get_db),
    admin = Depends(require_admin),
):
    charity = db.query(Charity).filter(Charity.id == charity_id).first()
    if not charity:
        raise HTTPException(status_code=404, detail="Charity not found")

    if payload.name is not None:
        charity.name = payload.name
    if payload.website_url is not None:
        charity.website_url = str(payload.website_url)
    if payload.description is not None:
        charity.description = payload.description
    if payload.category is not None:
        charity.category = payload.category
    if payload.is_verified is not None:
        charity.is_verified = payload.is_verified
    if payload.is_active is not None:
        charity.is_active = payload.is_active
    if payload.is_featured is not None:
        charity.is_featured = payload.is_featured

    db.commit()
    db.refresh(charity)
    return _serialize_charity(charity)

@router.put("/{charity_id}/deactivate")
def deactivate_charity(charity_id: int, db: Session = Depends(get_db), admin = Depends(require_admin)):
    charity = db.query(Charity).filter(Charity.id == charity_id).first()

    if not charity:
        raise HTTPException(status_code=404, detail="Charity not found")

    charity.is_active = False
    db.commit()

    return {"message": "Charity deactivated"}


@router.delete("/{charity_id}")
def delete_charity(charity_id: int, db: Session = Depends(get_db), admin = Depends(require_admin)):
    charity = db.query(Charity).filter(Charity.id == charity_id).first()

    if not charity:
        raise HTTPException(status_code=404, detail="Charity not found")

    charity.is_active = False
    db.commit()

    return {"message": "Charity deleted"}

@router.put("/{charity_id}/feature")
def feature_charity(charity_id: int, db: Session = Depends(get_db), admin = Depends(require_admin)):
    charity = db.query(Charity).filter(Charity.id == charity_id).first()

    if not charity:
        raise HTTPException(status_code=404, detail="Charity not found")

    charity.is_featured = True
    db.commit()

    return {"message": "Charity featured"}
