# services/sws_service.py
"""
SWS Service — handles SWS records and triggers propagation to FDS.

Key fixes:
  1. UBID normalization applied before ALL lookups
  2. Change detection — skips DB write if nothing changed (idempotent)
  3. Propagation NOW CREATES an FDS record if one doesn't exist yet
  4. Idempotency key prevents duplicate propagation
  5. Transactional writes — rollback on error
"""

import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.models import SWSRecord, FDSRecord
from app.services.ubid_service import resolve_ubid
from app.services.schema_mapper import translate_sws_to_fds, detect_field_differences
from app.services.audit_service import log_audit
from app.services.conflict_service import detect_and_resolve_conflict
from app.services.idempotency_service import compute_key, is_duplicate, mark_processed
from app.services.change_detection_service import save_snapshot, has_changed, get_latest_snapshot
from app.schemas.schemas import SWSUpdateRequest

logger = logging.getLogger(__name__)


def _record_to_dict(record: SWSRecord) -> dict:
    return {
        "sws_application_id": record.sws_application_id,
        "business_legal_name": record.business_legal_name,
        "registered_address": record.registered_address,
        "authorized_signatory_name": record.authorized_signatory_name,
        "business_type": record.business_type,
    }


def create_or_update_sws(db: Session, data: SWSUpdateRequest) -> SWSRecord:
    # Step 1: Resolve UBID (normalization happens inside resolve_ubid)
    ubid = resolve_ubid(db, "sws", data.sws_application_id)

    existing = db.query(SWSRecord).filter_by(sws_application_id=data.sws_application_id).first()
    payload_before = _record_to_dict(existing) if existing else None

    incoming = {
        "business_legal_name": data.business_legal_name,
        "registered_address": data.registered_address,
        "authorized_signatory_name": data.authorized_signatory_name,
        "business_type": data.business_type,
    }

    # Step 2: Change detection — skip if nothing actually changed
    latest_snapshot = get_latest_snapshot(db, ubid, "sws")
    if not has_changed(latest_snapshot, {**incoming, "sws_application_id": data.sws_application_id}):
        logger.info("No changes detected for SWS %s — skipping update.", data.sws_application_id)
        return existing

    # Step 3: Idempotency check (same ubid + payload already processed)
    idem_key = compute_key(str(ubid), "sws", incoming)
    if is_duplicate(db, idem_key):
        logger.info("Duplicate SWS update detected (idem key), skipping propagation.")
        return existing

    # Step 4: Conflict detection
    existing_updated_at = existing.last_updated_at if existing else None
    resolved_payload, was_conflict, conflict_id = detect_and_resolve_conflict(
        db, ubid, "sws", payload_before, incoming, existing_updated_at
    )

    # Detect which fields actually changed
    changed_fields = []
    if payload_before:
        changed_fields = [k for k in incoming if incoming.get(k) != payload_before.get(k)]
    else:
        changed_fields = list(incoming.keys())

    # Step 5: Write SWS record (transactional)
    try:
        if existing:
            existing.business_legal_name = resolved_payload["business_legal_name"]
            existing.registered_address = resolved_payload["registered_address"]
            existing.authorized_signatory_name = resolved_payload["authorized_signatory_name"]
            existing.business_type = resolved_payload["business_type"]
            existing.last_updated_at = datetime.now(timezone.utc)
            record = existing
        else:
            record = SWSRecord(
                sws_application_id=data.sws_application_id,
                ubid=ubid,
                **resolved_payload,
                last_updated_at=datetime.now(timezone.utc),
            )
            db.add(record)

        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()
        raise

    # Step 6: Save snapshot for future change detection
    snapshot_data = _record_to_dict(record)
    save_snapshot(db, ubid, "sws", snapshot_data)

    # Step 7: Audit log
    log_audit(
        db, ubid, "sws", "fds",
        action_type="update" if existing else "create",
        changed_fields=changed_fields,
        payload_before=payload_before,
        payload_after=_record_to_dict(record),
        status="success",
        conflict_flag=was_conflict,
    )

    # Step 8: Mark idempotency key
    mark_processed(db, idem_key, ubid, "sws")

    # Step 9: Propagate to FDS
    _propagate_sws_to_fds(db, ubid, record)

    return record


def _propagate_sws_to_fds(db: Session, ubid: uuid.UUID, sws_record: SWSRecord):
    """
    Direction 1: SWS → FDS

    - If FDS record exists for this UBID → update translated fields
    - If NO FDS record exists → CREATE one (this was the missing piece!)
    - Uses license_type placeholder 'SWS-Propagated' when creating from SWS
    """
    sws_dict = _record_to_dict(sws_record)
    fds_translated = translate_sws_to_fds(sws_dict)

    fds_existing = db.query(FDSRecord).filter_by(ubid=ubid).first()

    try:
        if fds_existing:
            # Update only the mapped fields; leave license_type untouched
            fds_existing.enterprise_name = fds_translated.get("enterprise_name", fds_existing.enterprise_name)
            fds_existing.factory_address = fds_translated.get("factory_address", fds_existing.factory_address)
            fds_existing.owner_name = fds_translated.get("owner_name", fds_existing.owner_name)
            fds_existing.last_modified_at = datetime.now(timezone.utc)
            db.commit()
            logger.info("Updated FDS record for UBID %s (SWS → FDS)", ubid)
        else:
            # CREATE a new FDS record from SWS data
            new_fds = FDSRecord(
                factory_license_id=f"FDS-{sws_record.sws_application_id}",
                ubid=ubid,
                enterprise_name=fds_translated["enterprise_name"],
                factory_address=fds_translated["factory_address"],
                owner_name=fds_translated["owner_name"],
                license_type="SWS-Propagated",   # placeholder until FDS updates it
                last_modified_at=datetime.now(timezone.utc),
            )
            db.add(new_fds)
            db.commit()
            logger.info("Created FDS record for UBID %s (SWS → FDS propagation)", ubid)
    except Exception:
        db.rollback()
        logger.exception("Propagation SWS→FDS failed for UBID %s", ubid)
        raise


def get_sws_by_ubid(db: Session, ubid_str: str) -> SWSRecord | None:
    try:
        ubid = uuid.UUID(ubid_str)
    except ValueError:
        return None
    return db.query(SWSRecord).filter_by(ubid=ubid).first()


def get_all_sws(db: Session) -> list[SWSRecord]:
    """Returns all SWS records from the database. No mock data."""
    return db.query(SWSRecord).order_by(SWSRecord.last_updated_at.desc()).all()
