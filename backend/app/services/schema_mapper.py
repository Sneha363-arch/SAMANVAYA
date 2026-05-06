# services/schema_mapper.py
"""
Schema Translation Engine — Samanvaya Interoperability Layer

Defines bidirectional field mapping between SWS and FDS schemas.
All translations go through this single module so that mapping
changes only need to be made in ONE place.

SWS → FDS:
  business_legal_name      → enterprise_name
  registered_address       → factory_address
  authorized_signatory_name → owner_name

FDS → SWS:
  enterprise_name  → business_legal_name
  factory_address  → registered_address
  owner_name       → authorized_signatory_name
"""

from typing import Any

# ── Field mapping tables ───────────────────────────────────────────────────────

SWS_TO_FDS_FIELD_MAP: dict[str, str] = {
    "business_legal_name": "enterprise_name",
    "registered_address": "factory_address",
    "authorized_signatory_name": "owner_name",
    # business_type has no FDS counterpart; passed through as-is for future use
}

FDS_TO_SWS_FIELD_MAP: dict[str, str] = {
    "enterprise_name": "business_legal_name",
    "factory_address": "registered_address",
    "owner_name": "authorized_signatory_name",
    # license_type has no SWS counterpart; passed through as-is for future use
}


# ── Translation functions ──────────────────────────────────────────────────────

def translate_sws_to_fds(sws_data: dict[str, Any]) -> dict[str, Any]:
    """
    Translate an SWS payload to FDS schema.
    Only mapped fields are included in the output.
    """
    result: dict[str, Any] = {}
    for sws_key, fds_key in SWS_TO_FDS_FIELD_MAP.items():
        if sws_key in sws_data:
            result[fds_key] = sws_data[sws_key]
    return result


def translate_fds_to_sws(fds_data: dict[str, Any]) -> dict[str, Any]:
    """
    Translate an FDS payload to SWS schema.
    Only mapped fields are included in the output.
    """
    result: dict[str, Any] = {}
    for fds_key, sws_key in FDS_TO_SWS_FIELD_MAP.items():
        if fds_key in fds_data:
            result[sws_key] = fds_data[fds_key]
    return result


def detect_field_differences(sws_data: dict, fds_data: dict) -> list[str]:
    """
    Compare SWS vs FDS values using the canonical field mapping.
    Returns a list of human-readable difference descriptions.
    """
    differences: list[str] = []
    for sws_field, fds_field in SWS_TO_FDS_FIELD_MAP.items():
        sws_val = sws_data.get(sws_field)
        fds_val = fds_data.get(fds_field)
        if sws_val != fds_val:
            differences.append(f"{sws_field} ↔ {fds_field}")
    return differences
