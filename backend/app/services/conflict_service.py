# services/conflict_service.py
# PART 5: Conflict Resolution Engine

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.models import ConflictRecord

CONFLICT_WINDOW_SECONDS = 30


def detect_and_resolve_conflict(
    db: Session,
    ubid: uuid.UUID,
    source_system: str,
    existing_data: dict | None,
    incoming_data: dict,
    existing_updated_at: datetime | None,
) -> tuple[dict, bool, str | None]:
    """Returns (resolved_payload, was_conflict, conflict_id)."""
    if existing_data is None:
        return incoming_data, False, None

    now = datetime.now(timezone.utc)

    if existing_updated_at and existing_updated_at.tzinfo is None:
        existing_updated_at = existing_updated_at.replace(tzinfo=timezone.utc)

    if existing_updated_at:
        delta = (now - existing_updated_at).total_seconds()
        if delta < CONFLICT_WINDOW_SECONDS:
            conflict = ConflictRecord(
                id=uuid.uuid4(),
                ubid=ubid,
                source_system=source_system,
                version_a=existing_data,
                version_b=incoming_data,
                resolution="last_write_wins",
                resolved_version=incoming_data,
                reason=f"Update within {int(delta)}s conflict window. Incoming wins (LWW).",
            )
            db.add(conflict)
            db.commit()
            return incoming_data, True, str(conflict.id)

    return incoming_data, False, None


def get_all_conflicts(db: Session, limit: int = 100) -> list:
    return (
        db.query(ConflictRecord)
        .order_by(ConflictRecord.created_at.desc())
        .limit(limit)
        .all()
    )


def get_conflicts_by_ubid(db: Session, ubid_str: str) -> list:
    try:
        ubid = uuid.UUID(ubid_str)
    except ValueError:
        return []
    return db.query(ConflictRecord).filter(ConflictRecord.ubid == ubid).all()
