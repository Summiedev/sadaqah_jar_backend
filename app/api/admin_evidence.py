from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.deps import get_db
from app.models.evidence import Evidence
from app.models.sadaqah_act import SadaqahAct
from app.schemas.admin import EvidenceCreate, EvidenceUpdate

router = APIRouter(prefix="/admin/evidence", tags=["Admin Evidence"])


def _serialize_evidence(evidence: Evidence) -> dict:
    return {
        "id": evidence.id,
        "act_id": evidence.act_id,
        "source_type": evidence.source_type,
        "reference": evidence.reference,
        "arabic_text": evidence.arabic_text,
        "english_text": evidence.english_text,
        "grade": evidence.grade,
        "is_verified": evidence.is_verified,
    }


@router.get("/")
def list_evidence(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin = Depends(require_admin),
):
    query = db.query(Evidence).order_by(Evidence.id.desc())
    total = query.count()
    rows = query.offset(offset).limit(limit).all()
    return {"total": total, "limit": limit, "offset": offset, "data": [_serialize_evidence(evidence) for evidence in rows]}


@router.post("/")
def add_evidence(
    payload: EvidenceCreate,
    db: Session = Depends(get_db),
    admin = Depends(require_admin),
):
    evidence = Evidence(
        act_id=payload.act_id,
        source_type=payload.source_type,
        reference=payload.reference,
        arabic_text=payload.arabic_text,
        english_text=payload.english_text,
        grade=payload.grade,
    )

    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    return _serialize_evidence(evidence)

@router.get("/{act_id}")
def get_act_with_evidence(act_id: int, db: Session = Depends(get_db), admin = Depends(require_admin)):
    act = db.query(SadaqahAct).filter(SadaqahAct.id == act_id).first()

    if not act:
        raise HTTPException(status_code=404, detail="Act not found")

    return {
        "id": act.id,
        "name": act.title,
        "description": act.description,
        "evidence": [
            {
                "id": evidence.id,
                "source_type": evidence.source_type,
                "reference": evidence.reference,
                "arabic_text": evidence.arabic_text,
                "english_text": evidence.english_text,
                "grade": evidence.grade,
                "is_verified": evidence.is_verified,
            }
            for evidence in act.evidences
        ]
    }


@router.patch("/{evidence_id}")
def update_evidence(
    evidence_id: int,
    payload: EvidenceUpdate,
    db: Session = Depends(get_db),
    admin = Depends(require_admin),
):
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    if payload.act_id is not None:
        act = db.query(SadaqahAct).filter(SadaqahAct.id == payload.act_id).first()
        if not act:
            raise HTTPException(status_code=404, detail="Act not found")
        evidence.act_id = payload.act_id
    if payload.source_type is not None:
        evidence.source_type = payload.source_type
    if payload.reference is not None:
        evidence.reference = payload.reference
    if payload.arabic_text is not None:
        evidence.arabic_text = payload.arabic_text
    if payload.english_text is not None:
        evidence.english_text = payload.english_text
    if payload.grade is not None:
        evidence.grade = payload.grade
    if payload.is_verified is not None:
        evidence.is_verified = payload.is_verified

    db.commit()
    db.refresh(evidence)
    return _serialize_evidence(evidence)


@router.delete("/{evidence_id}")
def delete_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    admin = Depends(require_admin),
):
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    db.delete(evidence)
    db.commit()
    return {"message": "Evidence deleted"}
