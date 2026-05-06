# services/reconciliation_service.py

import uuid
from sqlalchemy.orm import Session

from app.models.models import SWSRecord, FDSRecord, UBIDRegistry
from app.services.schema_mapper import detect_field_differences


def compare_by_ubid(db: Session, ubid_str: str) -> dict:
    try:
        ubid = uuid.UUID(ubid_str)
    except ValueError:
        return {"error": "Invalid UBID"}

    sws = db.query(SWSRecord).filter_by(ubid=ubid).first()
    fds = db.query(FDSRecord).filter_by(ubid=ubid).first()

    sws_dict = None
    fds_dict = None
    differences = []

    if sws:
        sws_dict = {
            "sws_application_id": sws.sws_application_id,
            "business_legal_name": sws.business_legal_name,
            "registered_address": sws.registered_address,
            "authorized_signatory_name": sws.authorized_signatory_name,
            "business_type": sws.business_type,
            "last_updated_at": sws.last_updated_at.isoformat() if sws.last_updated_at else None,
        }

    if fds:
        fds_dict = {
            "factory_license_id": fds.factory_license_id,
            "enterprise_name": fds.enterprise_name,
            "factory_address": fds.factory_address,
            "owner_name": fds.owner_name,
            "license_type": fds.license_type,
            "last_modified_at": fds.last_modified_at.isoformat() if fds.last_modified_at else None,
        }

    if sws_dict and fds_dict:
        differences = detect_field_differences(sws_dict, fds_dict)

    if sws_dict and fds_dict:
        sync_status = "synced" if not differences else "out_of_sync"
    elif sws_dict or fds_dict:
        sync_status = "partial"
    else:
        sync_status = "missing"

    return {
        "ubid": ubid_str,
        "sws": sws_dict,
        "fds": fds_dict,
        "differences": differences,
        "sync_status": sync_status,
    }


def get_all_comparisons(db: Session) -> list[dict]:
    ubids = db.query(UBIDRegistry).all()
    results = []
    for u in ubids:
        comp = compare_by_ubid(db, str(u.ubid))
        if comp.get("sws") or comp.get("fds"):
            results.append(comp)
    return results
