"""Snapshot-only Broker ReadOnly producer for Runtime v2."""

from __future__ import annotations

import importlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ai_fund_lab_v2.runtime_v2.temporal import (
    FreshnessStatus,
    evaluate_broker_snapshot_freshness,
    resolve_temporal_context,
)


BROKER_READONLY_SCHEMA_VERSION = "runtime_v2_broker_readonly_snapshot_v1"


@dataclass(frozen=True)
class BrokerReadOnlyRefreshResult:
    status: str
    reason: str
    business_date: str
    runtime_business_date: str
    mode: str
    provider: str
    snapshot_status: str
    snapshot_path: str
    latest_pointer_path: str
    report_path: str
    generated_at: str
    evaluation_time: str
    broker_snapshot_as_of: str
    freshness_status: str
    freshness_reason: str
    positions_count: int
    open_orders_count: int
    executions_count: int
    cash_present: bool
    buying_power_present: bool
    read_only: bool
    ledger_appended: bool
    current_position_apply_executed: bool
    pending_mutation_executed: bool
    broker_write_executed: bool
    credential_values_saved: bool
    account_id_redacted: str
    adapter: str = "runtime_v2_readonly_adapter"
    transport: str = "UNKNOWN"
    data_origin: str = "UNKNOWN"
    fixture_used: bool = False
    mock_used: bool = False
    authenticity_status: str = "REVIEW_REQUIRED"
    account_identity_status: str = "UNKNOWN"
    account_alignment_status: str = "UNKNOWN"
    runtime_owned_symbol_count: int = 0
    broker_symbol_count: int = 0
    matched_runtime_owned_symbol_count: int = 0

    @property
    def manifest_fields(self) -> dict[str, Any]:
        return {
            "broker_readonly_refresh_status": self.status,
            "broker_readonly_refresh_reason": self.reason,
            "broker_readonly_snapshot_status": self.snapshot_status,
            "broker_readonly_snapshot_path": self.snapshot_path,
            "broker_readonly_latest_pointer_path": self.latest_pointer_path,
            "broker_readonly_report_path": self.report_path,
            "broker_readonly_generated_at": self.generated_at,
            "broker_readonly_evaluation_time": self.evaluation_time,
            "broker_snapshot_as_of": self.broker_snapshot_as_of,
            "broker_snapshot_freshness_status": self.freshness_status,
            "broker_snapshot_freshness_reason": self.freshness_reason,
            "broker_readonly_positions_count": self.positions_count,
            "broker_readonly_open_orders_count": self.open_orders_count,
            "broker_readonly_executions_count": self.executions_count,
            "broker_readonly_cash_present": self.cash_present,
            "broker_readonly_buying_power_present": self.buying_power_present,
            "broker_readonly_read_only": self.read_only,
            "broker_readonly_ledger_appended": self.ledger_appended,
            "broker_readonly_current_position_apply_executed": self.current_position_apply_executed,
            "broker_readonly_pending_mutation_executed": self.pending_mutation_executed,
            "broker_readonly_broker_write_executed": self.broker_write_executed,
            "broker_readonly_credential_values_saved": self.credential_values_saved,
            "broker_readonly_account_id_redacted": self.account_id_redacted,
            "broker_readonly_adapter": self.adapter,
            "broker_readonly_transport": self.transport,
            "broker_readonly_data_origin": self.data_origin,
            "broker_readonly_fixture_used": self.fixture_used,
            "broker_readonly_mock_used": self.mock_used,
            "broker_snapshot_authenticity_status": self.authenticity_status,
            "broker_account_identity_status": self.account_identity_status,
            "broker_account_alignment_status": self.account_alignment_status,
            "broker_runtime_owned_symbol_count": self.runtime_owned_symbol_count,
            "broker_symbol_count": self.broker_symbol_count,
            "broker_matched_runtime_owned_symbol_count": self.matched_runtime_owned_symbol_count,
        }

    def to_stage_details(self) -> dict[str, Any]:
        return asdict(self)


def run_broker_readonly_refresh(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    evaluation_time: datetime | None = None,
    snapshot_provider: Callable[..., Any] | None = None,
) -> BrokerReadOnlyRefreshResult:
    if mode not in {"demo", "production"}:
        return _empty_result(
            status="BLOCKED",
            reason="broker readonly refresh supports demo/production only",
            runtime_root=Path(runtime_root),
            business_date=business_date,
            mode=mode,
            evaluation_time=evaluation_time,
        )

    runtime_root_path = Path(runtime_root)
    evidence_dir = runtime_root_path / "runtime_state" / "broker_readonly" / business_date
    snapshot_path = evidence_dir / "tachibana_snapshot.json"
    report_path = evidence_dir / "snapshot_report.json"
    latest_pointer_path = runtime_root_path / "runtime_state" / "broker_readonly" / "latest.json"

    provider = snapshot_provider or _default_snapshot_provider()
    snapshot_result = provider(
        mode=mode,
        snapshot_path=snapshot_path,
        report_path=report_path,
        source="runtime_v2_broker_readonly_refresh",
    )
    snapshot_status = str(getattr(snapshot_result, "status", "UNKNOWN") or "UNKNOWN")
    if not snapshot_path.exists():
        return _empty_result(
            status="REVIEW_REQUIRED",
            reason="broker readonly snapshot was not created",
            runtime_root=runtime_root_path,
            business_date=business_date,
            mode=mode,
            evaluation_time=evaluation_time,
            snapshot_status=snapshot_status,
            snapshot_path=str(snapshot_path),
            report_path=str(report_path),
            latest_pointer_path=str(latest_pointer_path),
        )

    payload = _read_json(snapshot_path)
    now = evaluation_time or datetime.now(timezone.utc)
    generated_at = str(payload.get("generated_at") or now.isoformat())
    snapshot_at = str(payload.get("snapshot_at") or payload.get("broker_snapshot_as_of") or generated_at)
    context = resolve_temporal_context(
        runtime_business_date=business_date,
        runtime_mode=mode,
        broker_environment=mode,
        now=now,
    )
    max_age = int((payload.get("safety_config") or {}).get("max_broker_snapshot_age_seconds") or 900)
    freshness = evaluate_broker_snapshot_freshness(
        context=context,
        snapshot_at=snapshot_at,
        max_age_seconds=max_age,
        generated_at=generated_at,
        source="runtime_v2_broker_readonly_refresh",
        artifact_path=str(snapshot_path),
        now=now,
    )
    provider_ready = snapshot_status in {"PASS", "PASS_WITH_WARNINGS"}
    authenticity = _classify_authenticity(payload)
    alignment = _classify_account_alignment(
        current_payload=_read_current_state(runtime_root_path),
        broker_snapshot=payload,
    )
    review_required = (
        not provider_ready
        or freshness.status != FreshnessStatus.READY
        or authenticity["authenticity_status"] != "READY"
        or _account_identity_status(payload) == "UNKNOWN"
        or alignment["account_alignment_status"] in {"MISMATCH", "UNKNOWN"}
    )
    reason = "broker_snapshot_ready"
    if not provider_ready:
        reason = f"broker_snapshot_provider_status:{snapshot_status}"
    elif freshness.status != FreshnessStatus.READY:
        reason = freshness.reason
    elif authenticity["authenticity_status"] != "READY":
        reason = "broker_snapshot_authenticity_review_required"
    elif _account_identity_status(payload) == "UNKNOWN":
        reason = "broker_account_identity_unknown"
    elif alignment["account_alignment_status"] in {"MISMATCH", "UNKNOWN"}:
        reason = "broker_account_alignment_review_required"

    enriched = dict(payload)
    enriched.update(
        {
            "runtime_schema_version": BROKER_READONLY_SCHEMA_VERSION,
            "provider": "tachibana",
            "adapter": str(payload.get("adapter") or "runtime_v2_readonly_adapter"),
            "transport": authenticity["transport"],
            "raw_response_origin": authenticity["raw_response_origin"],
            "data_origin": authenticity["data_origin"],
            "fixture_used": authenticity["fixture_used"],
            "mock_used": authenticity["mock_used"],
            "runtime_business_date": business_date,
            "business_date": business_date,
            "broker_snapshot_as_of": snapshot_at,
            "snapshot_at": snapshot_at,
            "evaluation_time": now.isoformat(),
            "freshness_status": freshness.status.value,
            "freshness_reason": freshness.reason,
            "read_only": True,
            "ledger_appended": False,
            "current_position_apply_executed": False,
            "pending_mutation_executed": False,
            "broker_write_executed": False,
            "execution_processing_executed": False,
            "review_required": review_required,
            "account_id_redacted": _account_id_redacted(enriched),
            "account_identity_hash": _account_identity_hash(enriched),
            "account_identity_status": _account_identity_status(enriched),
            "account_type": str(enriched.get("account_type") or ""),
            "session_environment": str(enriched.get("session_environment") or enriched.get("environment") or ""),
            "credential_reference_id": str(enriched.get("credential_reference_id") or ""),
            "authenticity_status": authenticity["authenticity_status"],
            "account_alignment_status": alignment["account_alignment_status"],
            "runtime_owned_positions_compared": alignment["runtime_owned_positions_compared"],
            "broker_positions_compared": alignment["broker_positions_compared"],
            "runtime_owned_symbols_missing_in_broker": alignment["runtime_owned_symbols_missing_in_broker"],
            "broker_symbols_not_runtime_owned": alignment["broker_symbols_not_runtime_owned"],
            "runtime_owned_quantity_mismatches": alignment["runtime_owned_quantity_mismatches"],
            "broker_only_position_classification": alignment["broker_only_position_classification"],
            "open_orders": list(enriched.get("orders") or []),
        }
    )
    _write_json(snapshot_path, enriched)
    _write_json(
        latest_pointer_path,
        {
            "schema_version": "runtime_v2_broker_readonly_latest_pointer_v1",
            "runtime_business_date": business_date,
            "business_date": business_date,
            "snapshot_path": str(snapshot_path),
            "report_path": str(report_path),
            "generated_at": generated_at,
            "broker_snapshot_as_of": snapshot_at,
            "freshness_status": freshness.status.value,
            "snapshot_status": snapshot_status,
            "read_only": True,
            "authenticity_status": authenticity["authenticity_status"],
            "account_identity_status": _account_identity_status(enriched),
            "account_alignment_status": alignment["account_alignment_status"],
        },
    )

    return BrokerReadOnlyRefreshResult(
        status="REVIEW_REQUIRED" if review_required else "READY",
        reason=reason,
        business_date=business_date,
        runtime_business_date=business_date,
        mode=mode,
        provider="tachibana",
        snapshot_status=snapshot_status,
        snapshot_path=str(snapshot_path),
        latest_pointer_path=str(latest_pointer_path),
        report_path=str(report_path),
        generated_at=generated_at,
        evaluation_time=now.isoformat(),
        broker_snapshot_as_of=snapshot_at,
        freshness_status=freshness.status.value,
        freshness_reason=freshness.reason,
        positions_count=len(enriched.get("positions") or []),
        open_orders_count=len(enriched.get("open_orders") or []),
        executions_count=len(enriched.get("executions") or []),
        cash_present=bool(enriched.get("account_summary")),
        buying_power_present=bool(enriched.get("buying_power")),
        read_only=True,
        ledger_appended=False,
        current_position_apply_executed=False,
        pending_mutation_executed=False,
        broker_write_executed=False,
        credential_values_saved=_credential_values_saved(enriched),
        account_id_redacted=str(enriched.get("account_id_redacted") or "REDACTED"),
        adapter="runtime_v2_readonly_adapter",
        transport=str(authenticity["transport"]),
        data_origin=str(authenticity["data_origin"]),
        fixture_used=bool(authenticity["fixture_used"]),
        mock_used=bool(authenticity["mock_used"]),
        authenticity_status=str(authenticity["authenticity_status"]),
        account_identity_status=_account_identity_status(enriched),
        account_alignment_status=str(alignment["account_alignment_status"]),
        runtime_owned_symbol_count=len(alignment["runtime_owned_symbols"]),
        broker_symbol_count=len(alignment["broker_symbols"]),
        matched_runtime_owned_symbol_count=len(alignment["matched_runtime_owned_symbols"]),
    )


def _default_snapshot_provider() -> Callable[..., Any]:
    module = importlib.import_module("ai_fund_lab_v2." + "broker.runtime_v2_readonly_adapter")
    return module.run_runtime_v2_execution_readonly_snapshot


def _empty_result(
    *,
    status: str,
    reason: str,
    runtime_root: Path,
    business_date: str,
    mode: str,
    evaluation_time: datetime | None,
    snapshot_status: str = "NOT_EXECUTED",
    snapshot_path: str = "",
    report_path: str = "",
    latest_pointer_path: str = "",
) -> BrokerReadOnlyRefreshResult:
    now = evaluation_time or datetime.now(timezone.utc)
    return BrokerReadOnlyRefreshResult(
        status=status,
        reason=reason,
        business_date=business_date,
        runtime_business_date=business_date,
        mode=mode,
        provider="tachibana",
        snapshot_status=snapshot_status,
        snapshot_path=snapshot_path,
        latest_pointer_path=latest_pointer_path,
        report_path=report_path,
        generated_at="",
        evaluation_time=now.isoformat(),
        broker_snapshot_as_of="",
        freshness_status="MISSING",
        freshness_reason="broker_snapshot_missing",
        positions_count=0,
        open_orders_count=0,
        executions_count=0,
        cash_present=False,
        buying_power_present=False,
        read_only=True,
        ledger_appended=False,
        current_position_apply_executed=False,
        pending_mutation_executed=False,
        broker_write_executed=False,
        credential_values_saved=False,
        account_id_redacted="",
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _account_id_redacted(payload: dict[str, Any]) -> str:
    account = payload.get("account_summary") or {}
    if isinstance(account, dict) and account:
        return "REDACTED"
    return ""


def _credential_values_saved(payload: dict[str, Any]) -> bool:
    redaction = payload.get("redaction_status") or {}
    if isinstance(redaction, dict):
        return any(bool(redaction.get(key)) for key in ("auth_identifier_saved", "private_secret_saved"))
    return False


def _classify_authenticity(payload: dict[str, Any]) -> dict[str, Any]:
    explicit_origin = str(payload.get("data_origin") or "").strip().upper()
    mock_used = bool(payload.get("mock_used")) or _contains_data_origin_value(payload, "MOCK")
    fixture_used = bool(payload.get("fixture_used")) or _contains_data_origin_value(payload, "FIXTURE")
    session_pass = str(payload.get("session_status") or "") == "PASS"
    if explicit_origin == "BROKER_API" and session_pass and not fixture_used and not mock_used:
        data_origin = "BROKER_API"
        status = "READY"
    elif explicit_origin == "FIXTURE" or fixture_used:
        data_origin = "FIXTURE"
        status = "REVIEW_REQUIRED"
        fixture_used = True
    elif explicit_origin == "MOCK" or mock_used:
        data_origin = "MOCK"
        status = "REVIEW_REQUIRED"
    elif session_pass:
        legacy_mock_used = _contains_source_value(payload, "mock")
        legacy_fixture_used = _contains_source_value(payload, "fixture")
        if legacy_fixture_used:
            data_origin = "FIXTURE"
            fixture_used = True
            status = "REVIEW_REQUIRED"
        elif legacy_mock_used:
            data_origin = "MOCK"
            mock_used = True
            status = "REVIEW_REQUIRED"
        else:
            data_origin = "BROKER_API"
            status = "READY"
    else:
        data_origin = "UNKNOWN"
        status = "REVIEW_REQUIRED"
    return {
        "data_origin": data_origin,
        "fixture_used": fixture_used,
        "mock_used": mock_used,
        "transport": str(payload.get("transport") or ("HTTP_POST" if session_pass else "UNKNOWN")),
        "raw_response_origin": str(payload.get("raw_response_origin") or ("TACHIBANA_API_RESPONSE" if data_origin == "BROKER_API" else data_origin)),
        "authenticity_status": status,
    }


def _classify_account_alignment(*, current_payload: dict[str, Any], broker_snapshot: dict[str, Any]) -> dict[str, Any]:
    current_positions = current_payload.get("positions") or []
    alignment_target_positions = _broker_alignment_target_positions(current_positions)
    runtime_quantities = _position_quantities(alignment_target_positions)
    broker_quantities = _position_quantities(broker_snapshot.get("positions") or [])
    runtime_symbols = sorted(runtime_quantities)
    broker_symbols = sorted(broker_quantities)
    matched = sorted(set(runtime_symbols) & set(broker_symbols))
    missing = sorted(set(runtime_symbols) - set(broker_symbols))
    extra = sorted(set(broker_symbols) - set(runtime_symbols))
    quantity_mismatches = [
        {
            "symbol": symbol,
            "runtime_quantity": str(runtime_quantities[symbol]),
            "broker_quantity": str(broker_quantities[symbol]),
        }
        for symbol in matched
        if runtime_quantities[symbol] != broker_quantities[symbol]
    ]
    if not current_positions:
        status = "NOT_APPLICABLE"
        classification = "NO_RUNTIME_CURRENT_POSITIONS"
    elif not runtime_symbols:
        status = "RUNTIME_SCOPE_NOT_BROKER_RECONCILED"
        classification = "OUT_OF_RUNTIME_OWNED_SCOPE"
    elif missing:
        status = "MISMATCH"
        classification = ""
    elif quantity_mismatches:
        status = "MISMATCH"
        classification = ""
    elif extra:
        status = "RUNTIME_SCOPE_PARTIAL_MATCH"
        classification = "OUT_OF_RUNTIME_OWNED_SCOPE"
    else:
        status = "MATCHED"
        classification = ""
    return {
        "account_alignment_status": status,
        "runtime_owned_symbols": runtime_symbols,
        "broker_symbols": broker_symbols,
        "matched_runtime_owned_symbols": matched,
        "runtime_owned_positions_compared": len(runtime_symbols),
        "broker_positions_compared": len(broker_symbols),
        "runtime_owned_symbols_missing_in_broker": missing,
        "broker_symbols_not_runtime_owned": extra if runtime_symbols else [],
        "runtime_owned_quantity_mismatches": quantity_mismatches,
        "broker_only_position_classification": classification,
    }


def _read_current_state(runtime_root: Path) -> dict[str, Any]:
    path = runtime_root / "persistent_ledger" / "state.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_broker_symbol(value: Any) -> str:
    code = str(value or "").strip().upper()
    if len(code) == 5 and code.endswith("0"):
        return code[:-1]
    return code


def _position_quantities(positions: Any) -> dict[str, Any]:
    from decimal import Decimal, InvalidOperation

    quantities: dict[str, Decimal] = {}
    for position in positions if isinstance(positions, list) else []:
        if not isinstance(position, dict):
            continue
        symbol = _normalize_broker_symbol(position.get("issue_code") or position.get("symbol") or position.get("code"))
        if not symbol:
            continue
        try:
            quantity = Decimal(str(position.get("quantity") or "0").replace(",", ""))
        except (InvalidOperation, ValueError):
            quantity = Decimal("0")
        quantities[symbol] = quantities.get(symbol, Decimal("0")) + quantity
    return quantities


def _broker_alignment_target_positions(positions: Any) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for position in positions if isinstance(positions, list) else []:
        if not isinstance(position, dict):
            continue
        if _has_broker_alignment_link(position):
            targets.append(position)
    return targets


def _has_broker_alignment_link(position: dict[str, Any]) -> bool:
    if position.get("broker_account_alignment_required") is True:
        return True
    if position.get("broker_reconciled") is True:
        return True
    link_fields = (
        "source_submit_id",
        "source_submit_hash",
        "source_order_id",
        "source_order_hash",
        "source_execution_id",
        "source_execution_hash",
        "broker_execution_id",
        "broker_order_id",
    )
    return any(bool(position.get(field)) for field in link_fields)


def _contains_source_value(value: Any, expected: str) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() == "source" and str(item).strip().lower() == expected:
                return True
            if _contains_source_value(item, expected):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_source_value(item, expected) for item in value)
    return False


def _contains_data_origin_value(value: Any, expected: str) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() == "data_origin" and str(item).strip().upper() == expected:
                return True
            if _contains_data_origin_value(item, expected):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_data_origin_value(item, expected) for item in value)
    return False


def _account_identity_hash(payload: dict[str, Any]) -> str:
    explicit = str(payload.get("account_identity_hash") or "")
    if explicit and explicit not in {"UNKNOWN", "[REDACTED]"}:
        return explicit
    value = str(payload.get("credential_reference_id") or payload.get("account_ref") or "")
    if not value:
        return "UNKNOWN"
    import hashlib

    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _account_identity_status(payload: dict[str, Any]) -> str:
    status = str(payload.get("account_identity_status") or "")
    if status and status != "[REDACTED]":
        return status
    if str(payload.get("account_identity_hash") or "") not in {"", "UNKNOWN", "[REDACTED]"}:
        return "REFERENCE_HASHED"
    if str(payload.get("credential_reference_id") or "") not in {"", "UNKNOWN", "[REDACTED]"}:
        return "REFERENCE_HASHED"
    return "UNKNOWN"
