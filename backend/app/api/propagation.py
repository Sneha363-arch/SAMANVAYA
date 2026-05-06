# api/propagation.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.audit_service import get_audit_by_ubid, get_all_audit_logs
from app.services.conflict_service import get_all_conflicts, get_conflicts_by_ubid
from app.services.reconciliation_service import compare_by_ubid, get_all_comparisons

router = APIRouter(tags=["Interoperability"])


# ── Comparison ────────────────────────────────────────────────────────────────

@router.get("/compare/{ubid}")
def compare(ubid: str, db: Session = Depends(get_db)):
    return compare_by_ubid(db, ubid)


@router.get("/compare")
def compare_all(db: Session = Depends(get_db)):
    return get_all_comparisons(db)


# ── Audit ─────────────────────────────────────────────────────────────────────

def _fmt_audit(e) -> dict:
    return {
        "id": str(e.id),
        "ubid": str(e.ubid),
        "source_system": e.source_system,
        "target_system": e.target_system,
        "action_type": e.action_type,
        "changed_fields": e.changed_fields or [],
        "payload_before": e.payload_before,
        "payload_after": e.payload_after,
        "status": e.status,
        "conflict_flag": e.conflict_flag,
        "retry_count": e.retry_count,
        "created_at": e.created_at.isoformat(),
    }


@router.get("/audit/{ubid}")
def audit_by_ubid(ubid: str, db: Session = Depends(get_db)):
    return [_fmt_audit(e) for e in get_audit_by_ubid(db, ubid)]


@router.get("/audit")
def all_audit(limit: int = 100, db: Session = Depends(get_db)):
    return [_fmt_audit(e) for e in get_all_audit_logs(db, limit=limit)]


# ── Conflicts ─────────────────────────────────────────────────────────────────

def _fmt_conflict(c) -> dict:
    return {
        "id": str(c.id),
        "ubid": str(c.ubid),
        "source_system": c.source_system,
        "version_a": c.version_a,
        "version_b": c.version_b,
        "resolution": c.resolution,
        "resolved_version": c.resolved_version,
        "reason": c.reason,
        "created_at": c.created_at.isoformat(),
    }


@router.get("/conflicts")
def all_conflicts(db: Session = Depends(get_db)):
    return [_fmt_conflict(c) for c in get_all_conflicts(db)]


@router.get("/conflicts/{ubid}")
def conflicts_by_ubid(ubid: str, db: Session = Depends(get_db)):
    return [_fmt_conflict(c) for c in get_conflicts_by_ubid(db, ubid)]


# ── Dashboard Stats ───────────────────────────────────────────────────────────

@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    from app.models.models import AuditLog, ConflictRecord, SWSRecord, FDSRecord
    total_sws = db.query(SWSRecord).count()
    total_fds = db.query(FDSRecord).count()
    total_audits = db.query(AuditLog).count()
    total_conflicts = db.query(ConflictRecord).count()
    success_audits = db.query(AuditLog).filter(AuditLog.status == "success").count()
    failed_audits = db.query(AuditLog).filter(AuditLog.status == "failed").count()

    comparisons = get_all_comparisons(db)
    synced = sum(1 for c in comparisons if c["sync_status"] == "synced")
    out_of_sync = sum(1 for c in comparisons if c["sync_status"] == "out_of_sync")
    partial = sum(1 for c in comparisons if c["sync_status"] == "partial")

    return {
        "total_sws_records": total_sws,
        "total_fds_records": total_fds,
        "total_audit_entries": total_audits,
        "total_conflicts": total_conflicts,
        "successful_propagations": success_audits,
        "failed_propagations": failed_audits,
        "synced_ubids": synced,
        "out_of_sync_ubids": out_of_sync,
        "partial_ubids": partial,
    }
