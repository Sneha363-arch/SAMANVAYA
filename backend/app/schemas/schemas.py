# schemas/schemas.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Any, List


class ResolveRequest(BaseModel):
    system_name: str = Field(..., min_length=2)
    system_id: str = Field(..., min_length=1)


class LinkRequest(BaseModel):
    ubid: UUID
    system_name: str
    system_id: str


class SWSUpdateRequest(BaseModel):
    sws_application_id: str = Field(..., min_length=1)
    business_legal_name: str = Field(..., min_length=2)
    registered_address: str = Field(..., min_length=5)
    authorized_signatory_name: str = Field(..., min_length=2)
    business_type: str = Field(..., min_length=2)


class SWSResponse(BaseModel):
    sws_application_id: str
    ubid: UUID
    business_legal_name: str
    registered_address: str
    authorized_signatory_name: str
    business_type: str
    last_updated_at: datetime

    class Config:
        from_attributes = True


class FDSUpdateRequest(BaseModel):
    factory_license_id: str = Field(..., min_length=1)
    enterprise_name: str = Field(..., min_length=2)
    factory_address: str = Field(..., min_length=5)
    owner_name: str = Field(..., min_length=2)
    license_type: str = Field(..., min_length=2)


class FDSResponse(BaseModel):
    factory_license_id: str
    ubid: UUID
    enterprise_name: str
    factory_address: str
    owner_name: str
    license_type: str
    last_modified_at: datetime

    class Config:
        from_attributes = True


class ComparisonResponse(BaseModel):
    ubid: str
    sws: Optional[dict] = None
    fds: Optional[dict] = None
    differences: List[str] = []
    sync_status: str


class AuditLogResponse(BaseModel):
    id: str
    ubid: str
    source_system: str
    target_system: str
    action_type: str
    changed_fields: Optional[List[str]] = []
    payload_before: Optional[Any]
    payload_after: Optional[Any]
    status: str
    conflict_flag: bool
    retry_count: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConflictResponse(BaseModel):
    id: str
    ubid: str
    source_system: str
    version_a: Optional[Any]
    version_b: Optional[Any]
    resolution: Optional[str]
    resolved_version: Optional[Any]
    reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
