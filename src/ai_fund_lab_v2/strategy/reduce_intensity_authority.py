from __future__ import annotations

from types import MappingProxyType
from typing import Any


CANONICAL_REDUCE_INTENSITY_AUTHORITY_TYPE = "CANONICAL_REDUCE_INTENSITY_AUTHORITY"
CANONICAL_REDUCE_INTENSITY_CONTRACT_VERSION = "phase28_d34_canonical_reduce_intensity_authority.v1"
CANONICAL_REDUCE_INTENSITY_RATIOS = MappingProxyType(
    {
        "LIGHT": 0.25,
        "MEDIUM": 0.33,
        "STRONG": 0.50,
    }
)


def canonical_reduce_fraction(intensity: Any) -> float | None:
    return CANONICAL_REDUCE_INTENSITY_RATIOS.get(normalize_reduce_intensity(intensity))


def normalize_reduce_intensity(intensity: Any) -> str:
    return str(intensity or "").strip().upper()


def resolve_reduce_intensity_authority(intensity: Any, *, business_date: str = "", source_pm_decision_ref: str = "") -> dict[str, Any]:
    normalized = normalize_reduce_intensity(intensity)
    fraction = canonical_reduce_fraction(normalized)
    authority = {
        "authority_type": CANONICAL_REDUCE_INTENSITY_AUTHORITY_TYPE,
        "contract_version": CANONICAL_REDUCE_INTENSITY_CONTRACT_VERSION,
        "business_date": business_date,
        "source_pm_decision_ref": source_pm_decision_ref,
        "accepted_intensities": sorted(CANONICAL_REDUCE_INTENSITY_RATIOS.keys()),
    }
    if fraction is None:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "reduce_intensity_missing" if not normalized else "reduce_intensity_unknown",
            "reduce_intensity": normalized,
            "reduce_fraction": None,
            "authority": authority,
        }
    return {
        "status": "PASS",
        "reason": "reduce_intensity_resolved",
        "reduce_intensity": normalized,
        "reduce_fraction": fraction,
        "authority": {**authority, "reduce_intensity": normalized, "reduce_fraction": fraction},
    }
