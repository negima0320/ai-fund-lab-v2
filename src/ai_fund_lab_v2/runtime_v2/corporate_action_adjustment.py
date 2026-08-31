"""Corporate action adjustment authority for Runtime v2 submit boundaries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


AUTHORITY_SCHEMA_VERSION = "runtime_v2_corporate_action_adjustment_authority_v1"


def materialize_corporate_action_adjustment_authority(
    *,
    runtime_root: Path | str,
    business_date: str,
    symbol: str,
    event_evidence: Mapping[str, Any],
    current_quantity: float | None = None,
    broker_available_quantity: float | None = None,
    pending_quantity: float | None = None,
    submit_quantity: float | None = None,
) -> dict[str, Any]:
    """Materialize the canonical authority artifact before submit consumers run."""

    runtime_root_path = Path(runtime_root)
    symbol_text = str(symbol).strip()
    event = dict(event_evidence)
    event_status = str(event.get("corporate_action_status") or "NOT_DETECTED")
    authority_path = _authority_path(runtime_root_path, business_date, symbol_text)
    if event_status == "PASS":
        return {
            "schema_version": AUTHORITY_SCHEMA_VERSION,
            "business_date": business_date,
            "symbol": symbol_text,
            "normalized_symbol": symbol_text,
            "status": "PASS",
            "event_status": "NOT_DETECTED",
            "event_type": "NOT_DETECTED",
            "event_type_authority": str(event.get("corporate_action_type_authority") or ""),
            "effective_date": str(event.get("corporate_action_effective_date") or business_date),
            "adjustment_factor": event.get("corporate_action_adjustment_factor"),
            "source_artifact_path": str(event.get("corporate_action_artifact_path") or ""),
            "source_artifact_hash": _sha256_file(Path(str(event.get("corporate_action_artifact_path") or ""))),
            "pit_validation_status": "PASS",
            "future_data_used": False,
            "current_quantity": current_quantity,
            "broker_available_quantity": broker_available_quantity,
            "pending_quantity": pending_quantity,
            "submit_quantity": submit_quantity,
            "already_applied_status": "NOT_REQUIRED",
            "quantity_reconciliation_status": "PASS",
            "price_reconciliation_status": "NOT_REQUIRED",
            "double_adjustment_detected": False,
            "reason": "corporate_action_not_detected",
            "reason_codes": [],
            "corporate_action_adjustment_authority_path": "",
            "corporate_action_adjustment_authority_hash": "",
        }
    existing = _read_json(authority_path)
    if existing and _authority_matches_event(
        existing,
        event=event,
        business_date=business_date,
        symbol=symbol_text,
    ):
        return {
            **existing,
            "corporate_action_adjustment_authority_path": str(authority_path),
            "corporate_action_adjustment_authority_hash": _sha256_file(authority_path),
        }
    source_path = Path(str(event.get("corporate_action_artifact_path") or ""))
    reason_codes = ["corporate_action_type_unresolved", "corporate_action_already_applied_unknown"]
    payload = {
        "schema_version": AUTHORITY_SCHEMA_VERSION,
        "business_date": business_date,
        "symbol": symbol_text,
        "normalized_symbol": symbol_text,
        "status": "REVIEW_REQUIRED",
        "event_status": event_status,
        "event_type": str(event.get("corporate_action_type") or "UNKNOWN"),
        "event_type_authority": str(event.get("corporate_action_type_authority") or "not_available"),
        "effective_date": str(event.get("corporate_action_effective_date") or business_date),
        "adjustment_factor": event.get("corporate_action_adjustment_factor"),
        "source": str(event.get("corporate_action_source") or ""),
        "source_artifact_path": str(source_path),
        "source_artifact_hash": _sha256_file(source_path),
        "pit_validation_status": "PASS",
        "future_data_used": False,
        "current_quantity": current_quantity,
        "broker_available_quantity": broker_available_quantity,
        "pending_quantity": pending_quantity,
        "submit_quantity": submit_quantity,
        "already_applied_status": "UNKNOWN",
        "quantity_reconciliation_status": "REVIEW_REQUIRED",
        "price_reconciliation_status": "REVIEW_REQUIRED",
        "double_adjustment_detected": False,
        "ledger_adjustment_status": "UNKNOWN",
        "current_adjustment_status": "UNKNOWN",
        "pending_adjustment_status": "UNKNOWN",
        "pre_adjustment_quantity": None,
        "post_adjustment_quantity": None,
        "pre_adjustment_price": event.get("corporate_action_old_price"),
        "post_adjustment_price": event.get("corporate_action_new_price"),
        "lineage": {
            "producer": "runtime_v2_corporate_action_adjustment_authority",
            "event_evidence": event,
        },
        "reason": "corporate_action_event_type_or_adjustment_application_unresolved",
        "reason_codes": reason_codes,
    }
    authority_path.parent.mkdir(parents=True, exist_ok=True)
    authority_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        **payload,
        "corporate_action_adjustment_authority_path": str(authority_path),
        "corporate_action_adjustment_authority_hash": _sha256_file(authority_path),
    }


def evaluate_corporate_action_adjustment_authority(
    *,
    runtime_root: Path | str,
    business_date: str,
    symbol: str,
    side: str,
    submit_quantity: float,
    pending_quantity: float | None = None,
    current_quantity: float | None = None,
    broker_available_quantity: float | None = None,
    event_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate that corporate action adjustment lineage is submit-safe.

    This authority does not infer event type from price adjustment factors. It
    accepts an impacted submit only when a Runtime-owned adjustment artifact can
    prove PIT source binding, idempotency, and quantity reconciliation.
    """

    runtime_root_path = Path(runtime_root)
    symbol_text = str(symbol).strip()
    side_text = str(side).upper()
    event = dict(event_evidence or {})
    event_status = str(event.get("corporate_action_status") or "NOT_DETECTED")
    event_factor = _optional_float(event.get("corporate_action_adjustment_factor"))
    authority_path = _authority_path(runtime_root_path, business_date, symbol_text)
    authority_payload = _read_json(authority_path)
    authority_hash = _sha256_file(authority_path)
    base = {
        "schema_version": AUTHORITY_SCHEMA_VERSION,
        "corporate_action_adjustment_authority_status": "PASS",
        "corporate_action_adjustment_authority_reason": "corporate_action_not_detected",
        "corporate_action_adjustment_authority_path": str(authority_path) if authority_path.exists() else "",
        "corporate_action_adjustment_authority_hash": authority_hash,
        "corporate_action_event_status": event_status,
        "corporate_action_event_type": str(event.get("corporate_action_type") or "NOT_DETECTED"),
        "corporate_action_effective_date": str(event.get("corporate_action_effective_date") or ""),
        "corporate_action_adjustment_factor": event_factor,
        "event_type_authority": str(event.get("corporate_action_type_authority") or ""),
        "pit_validation_status": "PASS" if event_status in {"PASS", "NOT_DETECTED"} else "",
        "future_data_used": False,
        "ledger_quantity_before": None,
        "ledger_quantity_after": current_quantity,
        "current_quantity": current_quantity,
        "broker_available_quantity": broker_available_quantity,
        "pending_quantity": pending_quantity,
        "submit_quantity": submit_quantity,
        "quantity_reconciliation_status": "PASS",
        "price_reconciliation_status": "NOT_REQUIRED",
        "already_applied_status": "NOT_REQUIRED",
        "double_adjustment_detected": False,
        "reason_codes": [],
    }
    if event_status in {"PASS", "NOT_DETECTED"}:
        return base
    if event_status in {"MISSING", "MISSING_ADJFACTOR", "MISSING_CODE", "UNREADABLE"}:
        return _review(base, "corporate_action_event_authority_unusable", "corporate_action_authority_missing")
    if not authority_payload:
        return _review(base, "corporate_action_adjustment_authority_missing", "corporate_action_authority_missing")

    evidence = {**base, "corporate_action_adjustment_authority_path": str(authority_path), "corporate_action_adjustment_authority_hash": authority_hash}
    evidence.update(_authority_fields(authority_payload))
    reason_codes: list[str] = []
    if str(authority_payload.get("schema_version") or "") != AUTHORITY_SCHEMA_VERSION:
        reason_codes.append("corporate_action_authority_schema_mismatch")
    if str(authority_payload.get("business_date") or "") != business_date:
        reason_codes.append("corporate_action_authority_business_date_mismatch")
    if str(authority_payload.get("symbol") or "").strip() != symbol_text:
        reason_codes.append("corporate_action_authority_symbol_mismatch")
    if str(authority_payload.get("status") or authority_payload.get("event_status") or "") != "PASS":
        reason_codes.append("corporate_action_event_not_resolved")
    event_type = str(authority_payload.get("event_type") or "")
    if not event_type or event_type.startswith("UNKNOWN"):
        reason_codes.append("corporate_action_type_unresolved")
    if str(authority_payload.get("effective_date") or "") != str(event.get("corporate_action_effective_date") or business_date):
        reason_codes.append("corporate_action_effective_date_mismatch")
    if event_factor is not None and _optional_float(authority_payload.get("adjustment_factor")) != event_factor:
        reason_codes.append("corporate_action_adjustment_factor_mismatch")
    event_source_path = str(event.get("corporate_action_artifact_path") or "")
    if event_source_path and str(authority_payload.get("source_artifact_path") or "") != event_source_path:
        reason_codes.append("corporate_action_source_artifact_mismatch")
    source_path = Path(str(authority_payload.get("source_artifact_path") or ""))
    expected_source_hash = _sha256_file(source_path) if source_path.is_file() else ""
    if expected_source_hash and str(authority_payload.get("source_artifact_hash") or "") != expected_source_hash:
        reason_codes.append("corporate_action_source_hash_mismatch")
    event_source_hash = _sha256_file(Path(event_source_path)) if event_source_path else ""
    if event_source_hash and str(authority_payload.get("source_artifact_hash") or "") != event_source_hash:
        reason_codes.append("corporate_action_event_source_hash_mismatch")
    if str(authority_payload.get("pit_validation_status") or "") != "PASS":
        reason_codes.append("corporate_action_pit_validation_not_pass")
    if bool(authority_payload.get("future_data_used")):
        reason_codes.append("corporate_action_future_snapshot_rejected")
    if bool(authority_payload.get("double_adjustment_detected")):
        evidence["double_adjustment_detected"] = True
        reason_codes.append("corporate_action_double_adjustment_risk")
    for key, code in (
        ("ledger_adjustment_status", "corporate_action_ledger_adjustment_missing"),
        ("current_adjustment_status", "corporate_action_current_adjustment_missing"),
        ("pending_adjustment_status", "corporate_action_pending_quantity_stale"),
        ("already_applied_status", "corporate_action_already_applied_not_confirmed"),
    ):
        if str(authority_payload.get(key) or "") not in {"PASS", "APPLIED", "CONFIRMED"}:
            reason_codes.append(code)
    adjusted_quantity = _optional_float(
        authority_payload.get("post_adjustment_quantity")
        if authority_payload.get("post_adjustment_quantity") not in (None, "")
        else authority_payload.get("adjusted_runtime_owned_quantity")
    )
    if side_text == "SELL":
        if adjusted_quantity is None or adjusted_quantity <= 0:
            reason_codes.append("corporate_action_adjusted_quantity_missing")
        if current_quantity is None:
            reason_codes.append("corporate_action_current_quantity_missing")
        elif adjusted_quantity is not None and float(current_quantity) != adjusted_quantity:
            reason_codes.append("corporate_action_current_quantity_mismatch")
        if broker_available_quantity is None:
            reason_codes.append("corporate_action_broker_quantity_missing")
        elif adjusted_quantity is not None and float(broker_available_quantity) > adjusted_quantity:
            reason_codes.append("corporate_action_broker_quantity_mismatch")
        if adjusted_quantity is not None and float(submit_quantity) > adjusted_quantity:
            reason_codes.append("corporate_action_submit_quantity_exceeds_adjusted_quantity")
        if broker_available_quantity is not None and float(submit_quantity) > float(broker_available_quantity):
            reason_codes.append("corporate_action_submit_quantity_exceeds_adjusted_broker_available")
        if pending_quantity is not None and adjusted_quantity is not None and float(pending_quantity) > adjusted_quantity:
            reason_codes.append("corporate_action_pending_quantity_stale")
    if reason_codes:
        status = "BLOCK" if "corporate_action_double_adjustment_risk" in reason_codes or any("exceeds" in code for code in reason_codes) else "REVIEW_REQUIRED"
        evidence.update(
            {
                "corporate_action_adjustment_authority_status": status,
                "corporate_action_adjustment_authority_reason": reason_codes[0],
                "quantity_reconciliation_status": "BLOCK" if status == "BLOCK" else "REVIEW_REQUIRED",
                "price_reconciliation_status": str(authority_payload.get("price_reconciliation_status") or "REVIEW_REQUIRED"),
                "reason_codes": reason_codes,
            }
        )
        return evidence
    evidence.update(
        {
            "corporate_action_adjustment_authority_status": "PASS",
            "corporate_action_adjustment_authority_reason": "corporate_action_adjustment_authority_confirmed",
            "quantity_reconciliation_status": "PASS",
            "price_reconciliation_status": str(authority_payload.get("price_reconciliation_status") or "PASS"),
            "already_applied_status": str(authority_payload.get("already_applied_status") or "CONFIRMED"),
            "reason_codes": [],
        }
    )
    return evidence


def _authority_path(runtime_root: Path, business_date: str, symbol: str) -> Path:
    return runtime_root / "runtime_state" / "corporate_action_adjustments" / business_date / f"{symbol}.json"


def _authority_matches_event(
    payload: Mapping[str, Any],
    *,
    event: Mapping[str, Any],
    business_date: str,
    symbol: str,
) -> bool:
    if str(payload.get("schema_version") or "") != AUTHORITY_SCHEMA_VERSION:
        return False
    if str(payload.get("business_date") or "") != business_date:
        return False
    if str(payload.get("symbol") or "").strip() != symbol:
        return False
    event_source_path = str(event.get("corporate_action_artifact_path") or "")
    if event_source_path and str(payload.get("source_artifact_path") or "") != event_source_path:
        return False
    event_source_hash = _sha256_file(Path(event_source_path)) if event_source_path else ""
    if event_source_hash and str(payload.get("source_artifact_hash") or "") != event_source_hash:
        return False
    event_factor = _optional_float(event.get("corporate_action_adjustment_factor"))
    if event_factor is not None and _optional_float(payload.get("adjustment_factor")) != event_factor:
        return False
    expected_effective_date = str(event.get("corporate_action_effective_date") or business_date)
    if str(payload.get("effective_date") or "") != expected_effective_date:
        return False
    return True


def _authority_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "corporate_action_event_status": str(payload.get("event_status") or ""),
        "corporate_action_event_type": str(payload.get("event_type") or ""),
        "corporate_action_effective_date": str(payload.get("effective_date") or ""),
        "corporate_action_adjustment_factor": _optional_float(payload.get("adjustment_factor")),
        "event_type_authority": str(payload.get("event_type_authority") or payload.get("source") or ""),
        "pit_validation_status": str(payload.get("pit_validation_status") or ""),
        "future_data_used": bool(payload.get("future_data_used")),
        "ledger_quantity_before": _optional_float(payload.get("pre_adjustment_quantity")),
        "ledger_quantity_after": _optional_float(payload.get("post_adjustment_quantity")),
        "already_applied_status": str(payload.get("already_applied_status") or ""),
        "double_adjustment_detected": bool(payload.get("double_adjustment_detected")),
        "lineage": dict(payload.get("lineage") or {}),
    }


def _review(evidence: dict[str, Any], reason: str, code: str) -> dict[str, Any]:
    evidence.update(
        {
            "corporate_action_adjustment_authority_status": "REVIEW_REQUIRED",
            "corporate_action_adjustment_authority_reason": reason,
            "quantity_reconciliation_status": "REVIEW_REQUIRED",
            "price_reconciliation_status": "REVIEW_REQUIRED",
            "already_applied_status": "UNKNOWN",
            "reason_codes": [code],
        }
    )
    return evidence


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _sha256_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
