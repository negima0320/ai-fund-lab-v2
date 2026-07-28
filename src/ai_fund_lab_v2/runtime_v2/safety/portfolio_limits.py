from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "portfolio_safety_limits.v1"
AUTHORITY_OWNER = "Safety Layer"
POSITION_COUNT_AUTHORITY = "Safety hard limit"
REQUIRED_SCOPES = ("production", "demo", "historical")


class PortfolioSafetyLimitsError(ValueError):
    pass


@dataclass(frozen=True)
class PortfolioSafetyLimits:
    config_version: str
    config_source: str
    authority_owner: str
    safety_hard_maximum: int | None
    minimum_cash_ratio: float
    maximum_gross_exposure_ratio: float
    maximum_position_weight: float
    position_count_authority: str
    cash_exposure_authority: str
    concentration_authority: str
    rationale: str
    effective_scope: tuple[str, ...]
    override_allowed: bool
    source_references: tuple[str, ...]
    config_hash: str

    def to_contract_payload(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "config_version": self.config_version,
            "config_source": self.config_source,
            "authority_owner": self.authority_owner,
            "position_count": {
                "safety_hard_maximum": self.safety_hard_maximum,
                "authority": self.position_count_authority,
                "rationale": self.rationale,
                "effective_scope": list(self.effective_scope),
                "override_allowed": self.override_allowed,
                "source_references": list(self.source_references),
            },
            "cash_exposure": {
                "minimum_cash_ratio": self.minimum_cash_ratio,
                "maximum_gross_exposure_ratio": self.maximum_gross_exposure_ratio,
                "authority": self.cash_exposure_authority,
                "override_allowed": self.override_allowed,
            },
            "concentration": {
                "maximum_position_weight": self.maximum_position_weight,
                "authority": self.concentration_authority,
                "override_allowed": self.override_allowed,
            },
            "config_hash": self.config_hash,
            "runtime_switch_performed": False,
            "legacy_active_max_positions_changed": False,
        }


def load_portfolio_safety_limits(
    path: Path | str,
    *,
    expected_config_hash: str | None = None,
    legacy_active_max_positions: int | None = None,
) -> PortfolioSafetyLimits:
    config_path = Path(path)
    if not config_path.is_file():
        raise PortfolioSafetyLimitsError(f"portfolio safety limits config missing: {config_path}")
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PortfolioSafetyLimitsError(f"portfolio safety limits invalid json: {exc}") from exc
    if not isinstance(payload, dict):
        raise PortfolioSafetyLimitsError("portfolio safety limits config must be a JSON object")
    actual_file_hash = sha256_file(config_path)
    if expected_config_hash and _strip_sha256(expected_config_hash) != actual_file_hash:
        raise PortfolioSafetyLimitsError("portfolio safety limits config hash mismatch")
    return validate_portfolio_safety_limits_payload(
        payload,
        config_source=str(config_path),
        config_hash=actual_file_hash,
        legacy_active_max_positions=legacy_active_max_positions,
    )


def validate_portfolio_safety_limits_payload(
    payload: dict[str, Any],
    *,
    config_source: str,
    config_hash: str,
    legacy_active_max_positions: int | None = None,
) -> PortfolioSafetyLimits:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise PortfolioSafetyLimitsError("unsupported portfolio safety limits schema_version")
    config_version = _required_text(payload, "config_version")
    authority_owner = _required_text(payload, "authority_owner")
    if authority_owner != AUTHORITY_OWNER:
        raise PortfolioSafetyLimitsError("portfolio safety limits authority_owner must be Safety Layer")
    position_count = payload.get("position_count")
    if not isinstance(position_count, dict):
        raise PortfolioSafetyLimitsError("position_count must be an object")
    cash_exposure = payload.get("cash_exposure")
    if not isinstance(cash_exposure, dict):
        raise PortfolioSafetyLimitsError("cash_exposure must be an object")
    concentration = payload.get("concentration")
    if not isinstance(concentration, dict):
        raise PortfolioSafetyLimitsError("concentration must be an object")
    safety_hard_maximum = _optional_positive_int(position_count, "safety_hard_maximum")
    if legacy_active_max_positions is not None and safety_hard_maximum == legacy_active_max_positions:
        raise PortfolioSafetyLimitsError("legacy max_positions must not be reused as safety hard maximum")
    position_count_authority = _required_text(position_count, "authority")
    if position_count_authority not in {POSITION_COUNT_AUTHORITY, "No routine fixed position-count safety cap"}:
        raise PortfolioSafetyLimitsError("position_count authority must be Safety hard limit or disabled fixed cap")
    cash_exposure_authority = _required_text(cash_exposure, "authority")
    if cash_exposure_authority != POSITION_COUNT_AUTHORITY:
        raise PortfolioSafetyLimitsError("cash_exposure authority must be Safety hard limit")
    concentration_authority = _required_text(concentration, "authority")
    if concentration_authority != POSITION_COUNT_AUTHORITY:
        raise PortfolioSafetyLimitsError("concentration authority must be Safety hard limit")
    minimum_cash_ratio = _required_ratio(cash_exposure, "minimum_cash_ratio")
    maximum_gross_exposure_ratio = _required_ratio(cash_exposure, "maximum_gross_exposure_ratio")
    if minimum_cash_ratio + maximum_gross_exposure_ratio > 1.0:
        raise PortfolioSafetyLimitsError("minimum_cash_ratio + maximum_gross_exposure_ratio must be <= 1.0")
    maximum_position_weight = _required_ratio(concentration, "maximum_position_weight")
    if maximum_position_weight <= 0:
        raise PortfolioSafetyLimitsError("maximum_position_weight must be > 0")
    if maximum_position_weight == 0.20:
        raise PortfolioSafetyLimitsError("legacy max_position_weight=0.20 must not be reused as concentration safety hard limit")
    rationale = _required_text(position_count, "rationale")
    _required_text(cash_exposure, "rationale")
    _required_text(concentration, "rationale")
    scope = position_count.get("effective_scope")
    cash_scope = cash_exposure.get("effective_scope")
    concentration_scope = concentration.get("effective_scope")
    if not isinstance(scope, list) or not all(isinstance(item, str) for item in scope):
        raise PortfolioSafetyLimitsError("effective_scope must be a list of strings")
    scope_tuple = tuple(scope)
    if tuple(sorted(scope_tuple)) != tuple(sorted(REQUIRED_SCOPES)):
        raise PortfolioSafetyLimitsError("effective_scope must be production/demo/historical")
    if not isinstance(cash_scope, list) or tuple(sorted(cash_scope)) != tuple(sorted(REQUIRED_SCOPES)):
        raise PortfolioSafetyLimitsError("cash_exposure effective_scope must be production/demo/historical")
    if not isinstance(concentration_scope, list) or tuple(sorted(concentration_scope)) != tuple(sorted(REQUIRED_SCOPES)):
        raise PortfolioSafetyLimitsError("concentration effective_scope must be production/demo/historical")
    override_allowed = position_count.get("override_allowed")
    if override_allowed is not False or cash_exposure.get("override_allowed") is not False or concentration.get("override_allowed") is not False:
        raise PortfolioSafetyLimitsError("override_allowed must be false")
    source_references = position_count.get("source_references")
    if not isinstance(source_references, list) or not source_references or not all(isinstance(item, str) and item for item in source_references):
        raise PortfolioSafetyLimitsError("source_references must be a non-empty string list")
    return PortfolioSafetyLimits(
        config_version=config_version,
        config_source=config_source,
        authority_owner=authority_owner,
        safety_hard_maximum=safety_hard_maximum,
        minimum_cash_ratio=minimum_cash_ratio,
        maximum_gross_exposure_ratio=maximum_gross_exposure_ratio,
        maximum_position_weight=maximum_position_weight,
        position_count_authority=position_count_authority,
        cash_exposure_authority=cash_exposure_authority,
        concentration_authority=concentration_authority,
        rationale=rationale,
        effective_scope=scope_tuple,
        override_allowed=False,
        source_references=tuple(source_references),
        config_hash=config_hash,
    )


def safety_hard_maximum_review_required(path: Path | str | None, *, reason: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "config_source": str(path or ""),
        "authority_owner": AUTHORITY_OWNER,
        "safety_hard_maximum": None,
        "safety_hard_maximum_status": "REVIEW_REQUIRED",
        "override_allowed": False,
        "reason": reason,
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _required_text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PortfolioSafetyLimitsError(f"{field} must be a non-empty string")
    return value.strip()


def _required_positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PortfolioSafetyLimitsError(f"{field} must be a positive integer")
    return value


def _optional_positive_int(payload: dict[str, Any], field: str) -> int | None:
    value = payload.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PortfolioSafetyLimitsError(f"{field} must be a positive integer when present")
    return value


def _required_ratio(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
        raise PortfolioSafetyLimitsError(f"{field} must be a ratio in [0, 1]")
    return float(value)


def _strip_sha256(value: str) -> str:
    return value[7:] if value.startswith("sha256:") else value
