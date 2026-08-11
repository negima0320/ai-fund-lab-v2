"""Historical-only Corporate Action symbol quarantine registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "historical_corporate_action_symbol_quarantine_registry_v1"
QUARANTINE_STATUS = "QUARANTINED"
RUN_CONTINUATION_ELIGIBILITY = "ALLOWED_FOR_HISTORICAL_REPLAY_ONLY"
PRODUCTION_APPLICABILITY = "NEVER"


def registry_path(runtime_root: Path | str) -> Path:
    return Path(runtime_root) / "runtime_state" / "corporate_action_quarantine" / "historical_symbol_registry.json"


def read_registry(runtime_root: Path | str) -> dict[str, Any]:
    path = registry_path(runtime_root)
    if not path.is_file():
        return _empty_registry()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _empty_registry()
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        return _empty_registry()
    symbols = payload.get("symbols")
    if not isinstance(symbols, dict):
        payload["symbols"] = {}
    return payload


def unresolved_entry(runtime_root: Path | str, symbol: str) -> dict[str, Any] | None:
    normalized = _normalize_symbol(symbol)
    if not normalized:
        return None
    entry = read_registry(runtime_root).get("symbols", {}).get(normalized)
    if not isinstance(entry, dict):
        return None
    if str(entry.get("resolution_status") or "") == "RESOLVED":
        return None
    if str(entry.get("corporate_action_quarantine_status") or "") != QUARANTINE_STATUS:
        return None
    return dict(entry)


def upsert_quarantine(
    *,
    runtime_root: Path | str,
    business_date: str,
    symbol: str,
    reason: str,
    event_status: str,
    source_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = _normalize_symbol(symbol)
    registry = read_registry(runtime_root)
    symbols = dict(registry.get("symbols") or {})
    previous = symbols.get(normalized) if isinstance(symbols.get(normalized), dict) else {}
    first_detected = str(previous.get("first_detected_date") or business_date)
    entry = {
        **previous,
        "symbol": normalized,
        "first_detected_date": first_detected,
        "latest_checked_date": business_date,
        "reason": reason,
        "event_status": event_status,
        "resolution_status": "UNRESOLVED",
        "source_evidence": dict(source_evidence or {}),
        **quarantine_fields(symbol=normalized, reason=reason),
    }
    symbols[normalized] = entry
    payload = {
        "schema_version": SCHEMA_VERSION,
        "registry_scope": "HISTORICAL_REPLAY_ONLY",
        "production_applicability": PRODUCTION_APPLICABILITY,
        "symbols": symbols,
    }
    path = registry_path(runtime_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return entry


def quarantine_fields(*, symbol: str, reason: str) -> dict[str, Any]:
    normalized = _normalize_symbol(symbol)
    return {
        "corporate_action_quarantine_status": QUARANTINE_STATUS,
        "corporate_action_quarantined_symbol": normalized,
        "corporate_action_quarantine_reason": reason,
        "corporate_action_quarantine_scope": "SYMBOL_ONLY",
        "corporate_action_run_continuation_eligibility": RUN_CONTINUATION_ELIGIBILITY,
        "corporate_action_run_continuation_reason": reason,
        "production_applicability": PRODUCTION_APPLICABILITY,
        "corporate_action_split_inference_used": False,
        "corporate_action_quantity_adjustment_performed": False,
        "portfolio_performance_limitation_status": "REVIEW_REQUIRED",
        "portfolio_performance_limitation_reason": (
            "unresolved_corporate_action_without_historical_broker_state_transition"
        ),
        "portfolio_performance_limitation_code": "CORPORATE_ACTION_UNRESOLVED_LIMITATION",
        "affected_symbols": [normalized] if normalized else [],
    }


def _empty_registry() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "registry_scope": "HISTORICAL_REPLAY_ONLY",
        "production_applicability": PRODUCTION_APPLICABILITY,
        "symbols": {},
    }


def _normalize_symbol(symbol: str) -> str:
    return str(symbol or "").strip().upper()
