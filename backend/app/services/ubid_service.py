# services/ubid_service.py
"""
UBID Resolver with canonical normalization.

normalize_id("SWS_123")   → "sws123"
normalize_id(" sws-123 ") → "sws123"

The normalized form is stored in system_identity_map.normalized_system_id
and used for all lookups, so the same logical entity always maps to ONE UBID
regardless of how the ID is formatted by the caller.
"""

import uuid
import hashlib
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.models import UBIDRegistry, SystemIdentityMap

logger = logging.getLogger(__name__)


def normalize_id(system_name: str, system_id: str) -> tuple[str, str, str]:
    """
    Returns (normalized_system_name, raw_system_id, normalized_system_id).

    Normalization rules:
      - strip leading/trailing whitespace
      - convert to lowercase
      - remove all spaces
      - remove underscores and hyphens

    Examples:
      "SWS", "SWS_123"   → ("sws", "SWS_123", "sws123")
      "sws", " sws-123 " → ("sws", " sws-123 ", "sws123")
      "FDS", "FDS-FL-001" → ("fds", "FDS-FL-001", "fdsfl001")
    """
    norm_name = system_name.strip().lower()
    norm_id = (
        system_id
        .strip()
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
    )
    return norm_name, system_id, norm_id


def generate_idempotency_key(ubid: str, source_system: str, payload: dict) -> str:
    import json
    raw = f"{ubid}:{source_system}:{json.dumps(payload, sort_keys=True)}"
    return hashlib.sha256(raw.encode()).hexdigest()


def resolve_ubid(db: Session, system_name: str, system_id: str) -> uuid.UUID:
    """
    Resolve (or create) a UBID for the given system+id pair.
    Uses the normalized form for deduplication so that
    "SWS_123", "sws123", "SWS-123" all resolve to the same UBID.
    """
    norm_name, raw_id, norm_id = normalize_id(system_name, system_id)

    mapping = db.query(SystemIdentityMap).filter_by(
        system_name=norm_name,
        normalized_system_id=norm_id,
    ).first()

    if mapping:
        return mapping.ubid

    new_ubid = uuid.uuid4()
    try:
        ubid_entry = UBIDRegistry(ubid=new_ubid)
        db.add(ubid_entry)
        db.flush()

        mapping = SystemIdentityMap(
            ubid=new_ubid,
            system_name=norm_name,
            system_id=raw_id,                 # keep original for display
            normalized_system_id=norm_id,     # used for uniqueness constraint
        )
        db.add(mapping)
        db.commit()
        logger.info("Created UBID %s for %s:%s (normalized: %s)", new_ubid, norm_name, raw_id, norm_id)
        return new_ubid

    except IntegrityError:
        db.rollback()
        # Race condition: another request already created it
        mapping = db.query(SystemIdentityMap).filter_by(
            system_name=norm_name,
            normalized_system_id=norm_id,
        ).first()
        if mapping:
            return mapping.ubid
        raise Exception("UBID resolution failed after retry")


def link_system(db: Session, ubid: uuid.UUID, system_name: str, system_id: str):
    """Link an existing UBID to a new system/id pair."""
    norm_name, raw_id, norm_id = normalize_id(system_name, system_id)

    existing = db.query(SystemIdentityMap).filter_by(
        system_name=norm_name,
        normalized_system_id=norm_id,
    ).first()
    if existing:
        return existing
    try:
        mapping = SystemIdentityMap(
            ubid=ubid,
            system_name=norm_name,
            system_id=raw_id,
            normalized_system_id=norm_id,
        )
        db.add(mapping)
        db.commit()
        return mapping
    except IntegrityError:
        db.rollback()
        raise Exception("Duplicate mapping attempted")


def get_ubid_by_system(db: Session, system_name: str, system_id: str):
    norm_name, _, norm_id = normalize_id(system_name, system_id)
    mapping = db.query(SystemIdentityMap).filter_by(
        system_name=norm_name,
        normalized_system_id=norm_id,
    ).first()
    return mapping.ubid if mapping else None


def get_systems_by_ubid(db: Session, ubid_str: str):
    try:
        ubid = uuid.UUID(ubid_str)
    except ValueError:
        return []
    mappings = db.query(SystemIdentityMap).filter_by(ubid=ubid).all()
    return [
        {
            "system_name": m.system_name,
            "system_id": m.system_id,
            "normalized_system_id": m.normalized_system_id,
        }
        for m in mappings
    ]
