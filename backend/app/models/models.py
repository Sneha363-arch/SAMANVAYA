# models/models.py
import uuid
from sqlalchemy import (
    Column, String, DateTime, ForeignKey,
    UniqueConstraint, Boolean, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


# ─────────────────────────────────────────────
# PART 0: UBID Registry
# ─────────────────────────────────────────────

class UBIDRegistry(Base):
    __tablename__ = "ubid_registry"

    ubid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SystemIdentityMap(Base):
    __tablename__ = "system_identity_map"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ubid = Column(UUID(as_uuid=True), ForeignKey("ubid_registry.ubid"), nullable=False)
    system_name = Column(String, nullable=False)
    system_id = Column(String, nullable=False)
    # normalized_system_id stores the canonical form used for deduplication
    normalized_system_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Unique constraint on NORMALIZED id — prevents duplicates across formats
        UniqueConstraint("system_name", "normalized_system_id", name="unique_system_mapping_normalized"),
    )


# ─────────────────────────────────────────────
# PART 1: SWS Data Store
# ─────────────────────────────────────────────

class SWSRecord(Base):
    __tablename__ = "sws_records"

    sws_application_id = Column(String, primary_key=True)
    ubid = Column(UUID(as_uuid=True), ForeignKey("ubid_registry.ubid"), nullable=False)
    business_legal_name = Column(String, nullable=False)
    registered_address = Column(String, nullable=False)
    authorized_signatory_name = Column(String, nullable=False)
    business_type = Column(String, nullable=False)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ─────────────────────────────────────────────
# PART 2: FDS Data Store
# ─────────────────────────────────────────────

class FDSRecord(Base):
    __tablename__ = "fds_records"

    factory_license_id = Column(String, primary_key=True)
    ubid = Column(UUID(as_uuid=True), ForeignKey("ubid_registry.ubid"), nullable=False)
    enterprise_name = Column(String, nullable=False)
    factory_address = Column(String, nullable=False)
    owner_name = Column(String, nullable=False)
    license_type = Column(String, nullable=False)
    last_modified_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ─────────────────────────────────────────────
# PART 3: System Snapshots (Change Detection)
# ─────────────────────────────────────────────

class SystemSnapshot(Base):
    __tablename__ = "system_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ubid = Column(UUID(as_uuid=True), ForeignKey("ubid_registry.ubid"), nullable=False)
    system_name = Column(String, nullable=False)
    snapshot_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────────
# PART 5: Conflict Records
# ─────────────────────────────────────────────

class ConflictRecord(Base):
    __tablename__ = "conflict_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ubid = Column(UUID(as_uuid=True), ForeignKey("ubid_registry.ubid"), nullable=False)
    source_system = Column(String, nullable=False)
    version_a = Column(JSON)
    version_b = Column(JSON)
    resolution = Column(String)
    resolved_version = Column(JSON)
    reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────────
# PART 6: Audit Log (Immutable)
# ─────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ubid = Column(UUID(as_uuid=True), ForeignKey("ubid_registry.ubid"), nullable=False)
    source_system = Column(String, nullable=False)
    target_system = Column(String, nullable=False)
    action_type = Column(String, nullable=False)   # create / update / no_change
    changed_fields = Column(JSON)                  # list of changed field names
    payload_before = Column(JSON)
    payload_after = Column(JSON)
    status = Column(String, nullable=False)         # success / failed / skipped
    conflict_flag = Column(Boolean, default=False)
    retry_count = Column(String, default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────────
# PART 7: Idempotency Keys
# ─────────────────────────────────────────────

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key_hash = Column(String, primary_key=True)
    ubid = Column(UUID(as_uuid=True))
    source_system = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────────
# PART 10: Retry Queue
# ─────────────────────────────────────────────

class RetryQueue(Base):
    __tablename__ = "retry_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ubid = Column(UUID(as_uuid=True))
    direction = Column(String)   # sws_to_fds / fds_to_sws
    payload = Column(JSON)
    attempt_count = Column(String, default="0")
    last_attempted_at = Column(DateTime(timezone=True))
    status = Column(String, default="pending")   # pending / done / failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
