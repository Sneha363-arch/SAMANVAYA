# services/audit_service.py
# PART 6: Audit & Traceability

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.models import AuditLog


def log_audit(
    db: Session,
    ubid: uuid.UUID,
    source_system: str,
    target_system: str,
    action_type: str,
    payload_before: dict | None,
    payload_after: dict | None,
    status: str,
    changed_fields: list | None = None,
    conflict_flag: bool = False,
    retry_count: int = 0,
):
    entry = AuditLog(
        id=uuid.uuid4(),
        ubid=ubid,
        source_system=source_system,
        target_system=target_system,
        action_type=action_type,
        changed_fields=changed_fields or [],
        payload_before=payload_before,
        payload_after=payload_after,
        status=status,
        conflict_flag=conflict_flag,
        retry_count=str(retry_count),
    )
    db.add(entry)
    db.commit()
    return entry


def get_audit_by_ubid(db: Session, ubid_str: str) -> list:
    try:
        ubid = uuid.UUID(ubid_str)
    except ValueError:
        return []
    return (
        db.query(AuditLog)
        .filter(AuditLog.ubid == ubid)
        .order_by(AuditLog.created_at.desc())
        .all()
    )


def get_all_audit_logs(db: Session, limit: int = 100) -> list:
    return (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
