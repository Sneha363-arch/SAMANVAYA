# services/change_detection_service.py
# PART 3: Change Detection Engine

import uuid
import json
from sqlalchemy.orm import Session

from app.models.models import SystemSnapshot


def get_latest_snapshot(db: Session, ubid: uuid.UUID, system_name: str) -> dict | None:
    snap = (
        db.query(SystemSnapshot)
        .filter_by(ubid=ubid, system_name=system_name)
        .order_by(SystemSnapshot.created_at.desc())
        .first()
    )
    return snap.snapshot_data if snap else None


def save_snapshot(db: Session, ubid: uuid.UUID, system_name: str, data: dict):
    snap = SystemSnapshot(
        id=uuid.uuid4(),
        ubid=ubid,
        system_name=system_name,
        snapshot_data=data,
    )
    db.add(snap)
    db.commit()


def has_changed(old_snapshot: dict | None, new_data: dict) -> bool:
    """Returns True if new_data differs from the last snapshot."""
    if old_snapshot is None:
        return True
    return json.dumps(old_snapshot, sort_keys=True) != json.dumps(new_data, sort_keys=True)
