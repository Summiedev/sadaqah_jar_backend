
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.deps import get_db
from app.models.evidence import Evidence
from app.models.sadaqah_act import SadaqahAct
from app.schemas.admin import EvidenceCreate

router = APIRouter(prefix="/admin/evidence", tags=["Admin Evidence"])


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

    return evidence

@router.get("/{act_id}")
def get_act_with_evidence(act_id: int, db: Session = Depends(get_db), admin = Depends(require_admin)):
    act = db.query(SadaqahAct).filter(SadaqahAct.id == act_id).first()

    if not act:
        raise HTTPException(status_code=404, detail="Act not found")

    return {
        "id": act.id,
        "name": act.name,
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