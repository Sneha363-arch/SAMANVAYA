# api/fds.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.schemas import FDSUpdateRequest, FDSResponse
from app.services.fds_service import create_or_update_fds, get_fds_by_ubid, get_all_fds

router = APIRouter(prefix="/fds", tags=["FDS"])


@router.post("/update", response_model=FDSResponse)
def update_fds(data: FDSUpdateRequest, db: Session = Depends(get_db)):
    """Create or update an FDS record, then propagate to SWS."""
    try:
        record = create_or_update_fds(db, data)
        return record
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all")
def list_fds(db: Session = Depends(get_db)):
    """Return all FDS records from the database (no mock data)."""
    records = get_all_fds(db)
    return [
        {
            "factory_license_id": r.factory_license_id,
            "ubid": str(r.ubid),
            "enterprise_name": r.enterprise_name,
            "factory_address": r.factory_address,
            "owner_name": r.owner_name,
            "license_type": r.license_type,
            "last_modified_at": r.last_modified_at.isoformat() if r.last_modified_at else None,
        }
        for r in records
    ]


@router.get("/by-ubid/{ubid}")
def fds_by_ubid(ubid: str, db: Session = Depends(get_db)):
    record = get_fds_by_ubid(db, ubid)
    if not record:
        raise HTTPException(status_code=404, detail="FDS record not found")
    return {
        "factory_license_id": record.factory_license_id,
        "ubid": str(record.ubid),
        "enterprise_name": record.enterprise_name,
        "factory_address": record.factory_address,
        "owner_name": record.owner_name,
        "license_type": record.license_type,
        "last_modified_at": record.last_modified_at.isoformat() if record.last_modified_at else None,
    }
