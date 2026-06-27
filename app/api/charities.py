from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.rate_limit import check_rate_limit_key
from app.db.session import get_db
from app.models.charity import Charity

router = APIRouter(prefix="/charities", tags=["Charities"])


def _enforce_public_rate_limit(request: Request, limit: int = 30, period: int = 60):
    client_host = request.client.host if request.client else "unknown"
    if not check_rate_limit_key(f"charities:{client_host}", limit=limit, period=period):
        raise HTTPException(status_code=429, detail="Too many requests")


@router.get("/")
def list_charities(request: Request, category: str = None, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    _enforce_public_rate_limit(request)
    query = db.query(Charity).filter(Charity.is_verified == True, Charity.is_active == True)
    if category:
        query = query.filter(Charity.category == category)
    total = query.count()
    rows = query.order_by(Charity.name).limit(limit).offset(offset).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "website_url": row.website_url,
                "category": row.category,
                "is_featured": row.is_featured,
            }
            for row in rows
        ],
    }

@router.get("/featured")
def featured_charities(request: Request, db: Session = Depends(get_db)):
    _enforce_public_rate_limit(request)
    rows = db.query(Charity).filter(
        Charity.is_verified == True,
        Charity.is_active == True,
        Charity.is_featured == True
    ).all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "website_url": row.website_url,
            "category": row.category,
            "is_featured": row.is_featured,
        }
        for row in rows
    ]


@router.get("/{charity_id}")
def get_charity(charity_id: int, request: Request, db: Session = Depends(get_db)):
    _enforce_public_rate_limit(request)
    charity = (
        db.query(Charity)
        .filter(
            Charity.id == charity_id,
            Charity.is_verified == True,
            Charity.is_active == True,
        )
        .first()
    )
    if not charity:
        raise HTTPException(status_code=404, detail="Charity not found")
    return {
        "id": charity.id,
        "name": charity.name,
        "description": charity.description,
        "website_url": charity.website_url,
        "category": charity.category,
        "is_featured": charity.is_featured,
        "is_verified": charity.is_verified,
        "is_active": charity.is_active,
    }
