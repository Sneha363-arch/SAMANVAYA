# api/ubid.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.schemas import ResolveRequest, LinkRequest
from app.services.ubid_service import resolve_ubid, link_system, get_systems_by_ubid

router = APIRouter(prefix="/ubid", tags=["UBID"])


@router.post("/resolve")
def resolve(data: ResolveRequest, db: Session = Depends(get_db)):
    """Resolve (or create) a UBID for a system+id pair. Normalizes before lookup."""
    try:
        ubid = resolve_ubid(db, data.system_name, data.system_id)
        return {"ubid": str(ubid), "system_name": data.system_name, "system_id": data.system_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/link")
def link(data: LinkRequest, db: Session = Depends(get_db)):
    """Link an existing UBID to another system/id pair."""
    try:
        mapping = link_system(db, data.ubid, data.system_name, data.system_id)
        return {"ubid": str(mapping.ubid), "system_name": mapping.system_name, "system_id": mapping.system_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{ubid}/systems")
def systems_for_ubid(ubid: str, db: Session = Depends(get_db)):
    """List all system mappings for a given UBID."""
    systems = get_systems_by_ubid(db, ubid)
    return {"ubid": ubid, "systems": systems}
