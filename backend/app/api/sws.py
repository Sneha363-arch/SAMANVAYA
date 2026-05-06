# api/sws.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.schemas import SWSUpdateRequest, SWSResponse
from app.services.sws_service import create_or_update_sws, get_sws_by_ubid, get_all_sws

router = APIRouter(prefix="/sws", tags=["SWS"])


@router.post("/update", response_model=SWSResponse)
def update_sws(data: SWSUpdateRequest, db: Session = Depends(get_db)):
    """Create or update an SWS record, then propagate to FDS."""
    try:
        record = create_or_update_sws(db, data)
        return record
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all")
def list_sws(db: Session = Depends(get_db)):
    """Return all SWS records from the database (no mock data)."""
    records = get_all_sws(db)
    return [
        {
            "sws_application_id": r.sws_application_id,
            "ubid": str(r.ubid),
            "business_legal_name": r.business_legal_name,
            "registered_address": r.registered_address,
            "authorized_signatory_name": r.authorized_signatory_name,
            "business_type": r.business_type,
            "last_updated_at": r.last_updated_at.isoformat() if r.last_updated_at else None,
        }
        for r in records
    ]


@router.get("/by-ubid/{ubid}")
def sws_by_ubid(ubid: str, db: Session = Depends(get_db)):
    record = get_sws_by_ubid(db, ubid)
    if not record:
        raise HTTPException(status_code=404, detail="SWS record not found")
    return {
        "sws_application_id": record.sws_application_id,
        "ubid": str(record.ubid),
        "business_legal_name": record.business_legal_name,
        "registered_address": record.registered_address,
        "authorized_signatory_name": record.authorized_signatory_name,
        "business_type": record.business_type,
        "last_updated_at": record.last_updated_at.isoformat() if record.last_updated_at else None,
    }
