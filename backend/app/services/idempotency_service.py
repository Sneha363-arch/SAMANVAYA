# services/idempotency_service.py
# PART 7: Idempotency Layer

import hashlib
import json
import uuid
from sqlalchemy.orm import Session

from app.models.models import IdempotencyKey


def compute_key(ubid: str, source_system: str, payload: dict) -> str:
    raw = f"{ubid}:{source_system}:{json.dumps(payload, sort_keys=True)}"
    return hashlib.sha256(raw.encode()).hexdigest()


def is_duplicate(db: Session, key_hash: str) -> bool:
    return db.query(IdempotencyKey).filter_by(key_hash=key_hash).first() is not None


def mark_processed(db: Session, key_hash: str, ubid: uuid.UUID, source_system: str):
    entry = IdempotencyKey(
        key_hash=key_hash,
        ubid=ubid,
        source_system=source_system,
    )
    db.add(entry)
    db.commit()
