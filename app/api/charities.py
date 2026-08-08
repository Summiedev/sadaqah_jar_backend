from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from app.core.rate_limit import check_rate_limit_key
from app.db.session import get_db
from app.models.charity import Charity
from app.services.storage import get_presigned_url, _get_bucket

router = APIRouter(prefix="/charities", tags=["Charities"])


def _enforce_public_rate_limit(request: Request, limit: int = 30, period: int = 60):
    client_host = request.client.host if request.client else "unknown"
    if not check_rate_limit_key(f"charities:{client_host}", limit=limit, period=period):
        raise HTTPException(status_code=429, detail="Too many requests")


def _key_from_url(raw_url: str | None, bucket: str) -> str | None:
    if not raw_url:
        return None
    return raw_url.split(f"/{bucket}/")[-1] if f"/{bucket}/" in raw_url else None


def _signed_urls(urls: list[str] | None) -> list[str]:
    if not urls:
        return []
    try:
        bucket = _get_bucket()
    except HTTPException:
        return [url for url in urls if url]
    signed = []
    for url in urls or []:
        key = _key_from_url(url, bucket)
        if not key:
            signed.append(url)
            continue
        try:
            signed.append(get_presigned_url(bucket=bucket, key=key, expires_in=3600))
        except HTTPException:
            signed.append(url)
    return signed


@router.get("/")
def list_charities(
    request: Request,
    category: str = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    _enforce_public_rate_limit(request)
    query = db.query(Charity).filter(
        Charity.is_verified, Charity.is_active, Charity.is_published
    )
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
                "title": row.title,
                "donation_type": row.donation_type,
                "case_name": row.case_name,
                "description": row.description,
                "website_url": row.website_url,
                "external_url": row.external_url,
                "category": row.category,
                "target_amount": float(row.target_amount)
                if row.target_amount is not None
                else None,
                "amount_raised": float(row.amount_raised)
                if row.amount_raised is not None
                else None,
                "currency": row.currency,
                "image_urls": _signed_urls(row.image_urls),
                "status": row.status,
                "deadline": row.deadline.isoformat() if row.deadline else None,
                "is_featured": row.is_featured,
            }
            for row in rows
        ],
    }


@router.get("/featured")
def featured_charities(request: Request, db: Session = Depends(get_db)):
    _enforce_public_rate_limit(request)
    rows = (
        db.query(Charity)
        .filter(
            Charity.is_verified,
            Charity.is_active,
            Charity.is_published,
            Charity.is_featured,
        )
        .all()
    )
    return [
        {
            "id": row.id,
            "name": row.name,
            "title": row.title,
            "donation_type": row.donation_type,
            "case_name": row.case_name,
            "description": row.description,
            "website_url": row.website_url,
            "external_url": row.external_url,
            "category": row.category,
            "target_amount": float(row.target_amount)
            if row.target_amount is not None
            else None,
            "amount_raised": float(row.amount_raised)
            if row.amount_raised is not None
            else None,
            "currency": row.currency,
            "image_urls": _signed_urls(row.image_urls),
            "status": row.status,
            "deadline": row.deadline.isoformat() if row.deadline else None,
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
            Charity.is_verified,
            Charity.is_active,
            Charity.is_published,
        )
        .first()
    )
    if not charity:
        raise HTTPException(status_code=404, detail="Charity not found")
    return {
        "id": charity.id,
        "name": charity.name,
        "title": charity.title,
        "donation_type": charity.donation_type,
        "case_name": charity.case_name,
        "description": charity.description,
        "website_url": charity.website_url,
        "external_url": charity.external_url,
        "category": charity.category,
        "target_amount": float(charity.target_amount)
        if charity.target_amount is not None
        else None,
        "amount_raised": float(charity.amount_raised)
        if charity.amount_raised is not None
        else None,
        "currency": charity.currency,
        "image_urls": _signed_urls(charity.image_urls),
        "evidence": charity.evidence,
        "evidence_urls": _signed_urls(charity.evidence_urls),
        "contact_info": charity.contact_info,
        "status": charity.status,
        "deadline": charity.deadline.isoformat() if charity.deadline else None,
        "is_featured": charity.is_featured,
        "is_verified": charity.is_verified,
        "is_active": charity.is_active,
    }
