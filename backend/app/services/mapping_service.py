# services/mapping_service.py
# Re-exports from schema_mapper for backward compatibility.
# All logic lives in schema_mapper.py (the canonical module per spec).

from app.services.schema_mapper import (
    translate_sws_to_fds,
    translate_fds_to_sws,
    detect_field_differences,
    SWS_TO_FDS_FIELD_MAP as SWS_TO_FDS_MAP,
    FDS_TO_SWS_FIELD_MAP as FDS_TO_SWS_MAP,
)

__all__ = [
    "translate_sws_to_fds",
    "translate_fds_to_sws",
    "detect_field_differences",
    "SWS_TO_FDS_MAP",
    "FDS_TO_SWS_MAP",
]
