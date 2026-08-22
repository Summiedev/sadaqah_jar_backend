from pathlib import Path
from uuid import uuid4
import io
import os

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.charity import Charity
from app.schemas.admin import CharityCreate, CharityUpdate
from app.services.storage import upload_file, delete_file, _get_bucket
from app.services.file_validation import (
    JPEG_MIME,
    PDF_MIME,
    PNG_MIME,
    validate_file_content,
)

router = APIRouter(prefix="/admin/charities", tags=["Admin Charities"])


def _object_url(bucket: str, key: str) -> str:
    return f"{os.getenv('S3_ENDPOINT_URL', 'http://127.0.0.1:9000').rstrip('/')}/{bucket}/{key}"


def _key_from_url(raw_url: str | None, bucket: str) -> str | None:
    if not raw_url:
        return None
    return raw_url.split(f"/{bucket}/")[-1] if f"/{bucket}/" in raw_url else None


def _extension(filename: str | None) -> str:
    return Path(filename or "").suffix.lower()


def _serialize_charity(charity: Charity) -> dict:
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
        "image_urls": charity.image_urls or [],
        "evidence": charity.evidence,
        "evidence_urls": charity.evidence_urls or [],
        "contact_info": charity.contact_info,
        "status": charity.status,
        "deadline": charity.deadline.isoformat() if charity.deadline else None,
        "is_published": charity.is_published,
        "is_verified": charity.is_verified,
        "is_active": charity.is_active,
        "is_featured": charity.is_featured,
    }


@router.get("/")
def list_charities(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    query = db.query(Charity).filter(Charity.is_active).order_by(Charity.id.desc())
    total = query.count()
    rows = query.offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [_serialize_charity(charity) for charity in rows],
    }


@router.post("/")
def create_charity(
    payload: CharityCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    charity = Charity(
        name=payload.name,
        title=payload.title,
        donation_type=payload.donation_type,
        case_name=payload.case_name,
        website_url=str(payload.website_url) if payload.website_url else "",
        external_url=str(payload.website_url) if payload.website_url else None,
        description=payload.description,
        category=payload.category,
        target_amount=payload.target_amount,
        amount_raised=payload.amount_raised,
        currency=payload.currency.upper(),
        image_urls=payload.image_urls or [],
        evidence=payload.evidence,
        evidence_urls=payload.evidence_urls or [],
        contact_info=payload.contact_info,
        status=payload.status,
        deadline=payload.deadline,
        is_published=payload.is_published,
        is_verified=True,
        is_featured=payload.is_featured,
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
    admin=Depends(require_admin),
):
    charity = db.query(Charity).filter(Charity.id == charity_id).first()
    if not charity:
        raise HTTPException(status_code=404, detail="Charity not found")

    if payload.name is not None:
        charity.name = payload.name
    if payload.title is not None:
        charity.title = payload.title
    if payload.donation_type is not None:
        charity.donation_type = payload.donation_type
    if payload.case_name is not None:
        charity.case_name = payload.case_name
    if payload.website_url is not None:
        charity.website_url = str(payload.website_url)
        charity.external_url = str(payload.website_url)
    if payload.description is not None:
        charity.description = payload.description
    if payload.category is not None:
        charity.category = payload.category
    if payload.target_amount is not None:
        charity.target_amount = payload.target_amount
    if payload.amount_raised is not None:
        charity.amount_raised = payload.amount_raised
    if payload.currency is not None:
        charity.currency = payload.currency.upper()
    if payload.image_urls is not None:
        charity.image_urls = payload.image_urls
    if payload.evidence is not None:
        charity.evidence = payload.evidence
    if payload.evidence_urls is not None:
        charity.evidence_urls = payload.evidence_urls
    if payload.contact_info is not None:
        charity.contact_info = payload.contact_info
    if payload.status is not None:
        charity.status = payload.status
    if payload.deadline is not None:
        charity.deadline = payload.deadline
    if payload.is_published is not None:
        charity.is_published = payload.is_published
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
def deactivate_charity(
    charity_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)
):
    charity = db.query(Charity).filter(Charity.id == charity_id).first()

    if not charity:
        raise HTTPException(status_code=404, detail="Charity not found")

    # Keep the row for historical donation-intent references, but make the
    # campaign disappear everywhere and remove its private media.
    try:
        bucket = _get_bucket()
    except HTTPException:
        bucket = None
    if bucket:
        for raw_url in [*(charity.image_urls or []), *(charity.evidence_urls or [])]:
            key = _key_from_url(raw_url, bucket)
            if key:
                try:
                    delete_file(bucket=bucket, key=key)
                except HTTPException:
                    # Storage cleanup must not leave the database campaign
                    # visible if an old object has already disappeared.
                    pass
    charity.image_urls = []
    charity.evidence_urls = []
    charity.is_active = False
    charity.is_published = False
    charity.status = "closed"
    db.commit()

    return {"message": "Charity deactivated"}


@router.delete("/{charity_id}")
def delete_charity(
    charity_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)
):
    charity = db.query(Charity).filter(Charity.id == charity_id).first()

    if not charity:
        raise HTTPException(status_code=404, detail="Charity not found")

    try:
        bucket = _get_bucket()
    except HTTPException:
        bucket = None
    if bucket:
        for raw_url in [*(charity.image_urls or []), *(charity.evidence_urls or [])]:
            key = _key_from_url(raw_url, bucket)
            if key:
                try:
                    delete_file(bucket=bucket, key=key)
                except HTTPException:
                    pass
    charity.image_urls = []
    charity.evidence_urls = []
    charity.is_active = False
    charity.is_published = False
    charity.status = "closed"
    db.commit()

    return {"message": "Charity deleted"}


@router.post("/{charity_id}/images")
async def upload_charity_images(
    charity_id: int,
    files: list[UploadFile] = File(...),
    replace: bool = Query(default=False),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    charity = db.query(Charity).filter(Charity.id == charity_id).first()
    if not charity:
        raise HTTPException(status_code=404, detail="Donation not found")
    if not files:
        raise HTTPException(status_code=400, detail="Select at least one image")

    bucket = _get_bucket()
    if replace:
        for url in charity.image_urls or []:
            key = _key_from_url(url, bucket)
            if key:
                try:
                    delete_file(bucket=bucket, key=key)
                except HTTPException:
                    pass
        charity.image_urls = []

    urls = list(charity.image_urls or [])
    for file in files:
        suffix = _extension(file.filename)
        if suffix not in {".jpg", ".jpeg", ".png"}:
            raise HTTPException(status_code=400, detail="Images must be JPG or PNG")
        content = await file.read()
        content_type = validate_file_content(
            content,
            allowed_mimes={JPEG_MIME, PNG_MIME},
            max_size_bytes=12 * 1024 * 1024,
            label="Image",
        )
        key = f"donations/{charity_id}/images/{uuid4().hex}{suffix}"
        upload_file(
            bucket=bucket,
            key=key,
            data=io.BytesIO(content),
            content_type=content_type,
            max_size_bytes=12 * 1024 * 1024,
        )
        urls.append(_object_url(bucket, key))

    charity.image_urls = urls
    db.add(charity)
    db.commit()
    db.refresh(charity)
    return _serialize_charity(charity)


@router.post("/{charity_id}/evidence")
async def upload_charity_evidence(
    charity_id: int,
    files: list[UploadFile] = File(...),
    replace: bool = Query(default=False),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    charity = db.query(Charity).filter(Charity.id == charity_id).first()
    if not charity:
        raise HTTPException(status_code=404, detail="Donation not found")
    if not files:
        raise HTTPException(status_code=400, detail="Select at least one evidence file")

    bucket = _get_bucket()
    if replace:
        for url in charity.evidence_urls or []:
            key = _key_from_url(url, bucket)
            if key:
                try:
                    delete_file(bucket=bucket, key=key)
                except HTTPException:
                    pass
        charity.evidence_urls = []

    urls = list(charity.evidence_urls or [])
    for file in files:
        suffix = _extension(file.filename)
        if suffix not in {".jpg", ".jpeg", ".png", ".pdf"}:
            raise HTTPException(
                status_code=400, detail="Evidence files must be JPG, PNG, or PDF"
            )
        content = await file.read()
        content_type = validate_file_content(
            content,
            allowed_mimes={JPEG_MIME, PNG_MIME, PDF_MIME},
            max_size_bytes=20 * 1024 * 1024,
            label="Evidence file",
        )
        key = f"donations/{charity_id}/evidence/{uuid4().hex}{suffix}"
        upload_file(
            bucket=bucket,
            key=key,
            data=io.BytesIO(content),
            content_type=content_type,
            max_size_bytes=20 * 1024 * 1024,
        )
        urls.append(_object_url(bucket, key))

    charity.evidence_urls = urls
    db.add(charity)
    db.commit()
    db.refresh(charity)
    return _serialize_charity(charity)


@router.put("/{charity_id}/feature")
def feature_charity(
    charity_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)
):
    charity = db.query(Charity).filter(Charity.id == charity_id).first()

    if not charity:
        raise HTTPException(status_code=404, detail="Charity not found")

    charity.is_featured = True
    db.commit()

    return {"message": "Charity featured"}
