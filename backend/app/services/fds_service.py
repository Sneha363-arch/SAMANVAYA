# services/fds_service.py
"""
FDS Service — handles FDS records and triggers propagation to SWS.

Key fixes:
  1. UBID normalization applied before ALL lookups
  2. Change detection — skips DB write if nothing changed (idempotent)
  3. Propagation NOW CREATES an SWS record if one doesn't exist yet
  4. Idempotency key prevents duplicate propagation
  5. Transactional writes — rollback on error
"""

import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.models import FDSRecord, SWSRecord
from app.services.ubid_service import resolve_ubid
from app.services.schema_mapper import translate_fds_to_sws
from app.services.audit_service import log_audit
from app.services.conflict_service import detect_and_resolve_conflict
from app.services.idempotency_service import compute_key, is_duplicate, mark_processed
from app.services.change_detection_service import save_snapshot, has_changed, get_latest_snapshot
from app.schemas.schemas import FDSUpdateRequest

logger = logging.getLogger(__name__)


def _record_to_dict(record: FDSRecord) -> dict:
    return {
        "factory_license_id": record.factory_license_id,
        "enterprise_name": record.enterprise_name,
        "factory_address": record.factory_address,
        "owner_name": record.owner_name,
        "license_type": record.license_type,
    }


def create_or_update_fds(db: Session, data: FDSUpdateRequest) -> FDSRecord:
    # Step 1: Resolve UBID (normalization happens inside resolve_ubid)
    ubid = resolve_ubid(db, "fds", data.factory_license_id)

    existing = db.query(FDSRecord).filter_by(factory_license_id=data.factory_license_id).first()
    payload_before = _record_to_dict(existing) if existing else None

    incoming = {
        "enterprise_name": data.enterprise_name,
        "factory_address": data.factory_address,
        "owner_name": data.owner_name,
        "license_type": data.license_type,
    }

    # Step 2: Change detection
    latest_snapshot = get_latest_snapshot(db, ubid, "fds")
    if not has_changed(latest_snapshot, {**incoming, "factory_license_id": data.factory_license_id}):
        logger.info("No changes detected for FDS %s — skipping update.", data.factory_license_id)
        return existing

    # Step 3: Idempotency check
    idem_key = compute_key(str(ubid), "fds", incoming)
    if is_duplicate(db, idem_key):
        logger.info("Duplicate FDS update detected (idem key), skipping propagation.")
        return existing

    # Step 4: Conflict detection
    existing_updated_at = existing.last_modified_at if existing else None
    resolved_payload, was_conflict, conflict_id = detect_and_resolve_conflict(
        db, ubid, "fds", payload_before, incoming, existing_updated_at
    )

    # Detect changed fields
    changed_fields = []
    if payload_before:
        changed_fields = [k for k in incoming if incoming.get(k) != payload_before.get(k)]
    else:
        changed_fields = list(incoming.keys())

    # Step 5: Write FDS record (transactional)
    try:
        if existing:
            existing.enterprise_name = resolved_payload["enterprise_name"]
            existing.factory_address = resolved_payload["factory_address"]
            existing.owner_name = resolved_payload["owner_name"]
            existing.license_type = resolved_payload["license_type"]
            existing.last_modified_at = datetime.now(timezone.utc)
            record = existing
        else:
            record = FDSRecord(
                factory_license_id=data.factory_license_id,
                ubid=ubid,
                **resolved_payload,
                last_modified_at=datetime.now(timezone.utc),
            )
            db.add(record)

        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()
        raise

    # Step 6: Save snapshot
    snapshot_data = _record_to_dict(record)
    save_snapshot(db, ubid, "fds", snapshot_data)

    # Step 7: Audit log
    log_audit(
        db, ubid, "fds", "sws",
        action_type="update" if existing else "create",
        changed_fields=changed_fields,
        payload_before=payload_before,
        payload_after=_record_to_dict(record),
        status="success",
        conflict_flag=was_conflict,
    )

    # Step 8: Mark idempotency key
    mark_processed(db, idem_key, ubid, "fds")

    # Step 9: Propagate to SWS
    _propagate_fds_to_sws(db, ubid, record)

    return record


def _propagate_fds_to_sws(db: Session, ubid: uuid.UUID, fds_record: FDSRecord):
    """
    Direction 2: FDS → SWS

    - If SWS record exists for this UBID → update translated fields
    - If NO SWS record exists → CREATE one (mirroring the SWS→FDS fix)
    """
    fds_dict = _record_to_dict(fds_record)
    sws_translated = translate_fds_to_sws(fds_dict)

    sws_existing = db.query(SWSRecord).filter_by(ubid=ubid).first()

    try:
        if sws_existing:
            sws_existing.business_legal_name = sws_translated.get("business_legal_name", sws_existing.business_legal_name)
            sws_existing.registered_address = sws_translated.get("registered_address", sws_existing.registered_address)
            sws_existing.authorized_signatory_name = sws_translated.get("authorized_signatory_name", sws_existing.authorized_signatory_name)
            sws_existing.last_updated_at = datetime.now(timezone.utc)
            db.commit()
            logger.info("Updated SWS record for UBID %s (FDS → SWS)", ubid)
        else:
            # CREATE a new SWS record from FDS data
            new_sws = SWSRecord(
                sws_application_id=f"SWS-{fds_record.factory_license_id}",
                ubid=ubid,
                business_legal_name=sws_translated["business_legal_name"],
                registered_address=sws_translated["registered_address"],
                authorized_signatory_name=sws_translated["authorized_signatory_name"],
                business_type="FDS-Propagated",  # placeholder until SWS updates it
                last_updated_at=datetime.now(timezone.utc),
            )
            db.add(new_sws)
            db.commit()
            logger.info("Created SWS record for UBID %s (FDS → SWS propagation)", ubid)
    except Exception:
        db.rollback()
        logger.exception("Propagation FDS→SWS failed for UBID %s", ubid)
        raise


def get_fds_by_ubid(db: Session, ubid_str: str) -> FDSRecord | None:
    try:
        ubid = uuid.UUID(ubid_str)
    except ValueError:
        return None
    return db.query(FDSRecord).filter_by(ubid=ubid).first()


def get_all_fds(db: Session) -> list[FDSRecord]:
    """Returns all FDS records from the database. No mock data."""
    return db.query(FDSRecord).order_by(FDSRecord.last_modified_at.desc()).all()
