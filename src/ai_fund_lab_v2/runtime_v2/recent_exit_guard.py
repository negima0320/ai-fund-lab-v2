"""Bounded recent-exit guard materialization for Runtime v2.

The current BUY hot path consumes only this compact index. It must not rebuild
prior-exit state by scanning whole-run ledger or PM history.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping

from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerExecutionRecord, LedgerOrderRecord

RECENT_EXIT_GUARD_SCHEMA_VERSION = "runtime_v2.recent_exit_guard_index.v1"
RECENT_EXIT_GUARD_CONTRACT_ID = "phase32_ez_bounded_recent_exit_guard_materialization.v1"
RECENT_EXIT_GUARD_TTL_BUSINESS_DAYS = 3
FULL_EXIT_DECISION_TYPES = frozenset({"SELL_EXIT", "EXIT"})


@dataclass(frozen=True)
class RecentExitGuardMaterializationResult:
    status: str
    reason: str
    output_path: str
    run_id: str
    business_date: str
    emitted_count: int
    retained_count: int
    expired_count: int
    malformed_count: int
    rows: tuple[dict[str, Any], ...]


def materialize_recent_exit_guard_from_execution(
    *,
    runtime_root: Path | str,
    business_date: str,
    ledger_orders: Iterable[LedgerOrderRecord],
    ledger_executions: Iterable[LedgerExecutionRecord],
    runtime_test_run_id: str = "",
) -> RecentExitGuardMaterializationResult:
    """Write the bounded current-decision recent-exit guard index.

    Rows are sourced from same-day, committed full SELL_EXIT/EXIT execution
    evidence. Existing active rows are retained only while still inside the
    bounded guard window; old rows are compacted away.
    """

    runtime_root_path = Path(runtime_root)
    output_path = runtime_root_path / "runtime_state" / "recent_exit_guard.json"
    existing_rows = _load_existing_rows(output_path)
    retained_rows: list[dict[str, Any]] = []
    expired_count = 0
    malformed_count = 0
    for row in existing_rows:
        normalized = _normalize_existing_row(row)
        if normalized is None:
            malformed_count += 1
            continue
        if _is_active_for_storage(normalized["most_recent_full_exit_business_date"], business_date):
            retained_rows.append(normalized)
        else:
            expired_count += 1

    order_by_id = _orders_by_id(ledger_orders)
    emitted_rows: list[dict[str, Any]] = []
    malformed_exit_rows: list[dict[str, str]] = []
    for execution in ledger_executions:
        order = order_by_id.get(str(execution.order_id or ""))
        if _is_full_exit_execution(execution=execution, order=order):
            malformed_reason = _full_exit_guard_malformed_reason(execution=execution, order=order)
            if malformed_reason:
                malformed_exit_rows.append(
                    {
                        "symbol": str(execution.symbol or ""),
                        "execution_id": str(execution.execution_id or ""),
                        "reason": malformed_reason,
                    }
                )
                continue
        row = _guard_row_from_execution(
            execution=execution,
            order=order,
            business_date=business_date,
            runtime_test_run_id=runtime_test_run_id,
        )
        if row is not None:
            emitted_rows.append(row)

    by_symbol: dict[str, dict[str, Any]] = {}
    for row in (*retained_rows, *emitted_rows):
        by_symbol[str(row["symbol"])] = row
    rows = tuple(sorted(by_symbol.values(), key=lambda item: str(item["symbol"])))
    emitted_guard_ids = {str(row.get("guard_id") or "") for row in emitted_rows}
    retained_count = sum(1 for row in rows if str(row.get("guard_id") or "") not in emitted_guard_ids)
    status = "PASS" if not malformed_exit_rows else "REVIEW_REQUIRED"
    reason = (
        "bounded_recent_exit_guard_materialized_from_committed_execution"
        if status == "PASS"
        else "full_exit_execution_missing_recent_exit_guard_minimal_provenance"
    )
    payload = {
        "schema_version": RECENT_EXIT_GUARD_SCHEMA_VERSION,
        "contract_id": RECENT_EXIT_GUARD_CONTRACT_ID,
        "authority": "BOUNDED_RECENT_EXIT_GUARD_INDEX",
        "status": status,
        "reason": reason,
        "business_date": business_date,
        "runtime_test_run_id": runtime_test_run_id,
        "guard_ttl_business_days": RECENT_EXIT_GUARD_TTL_BUSINESS_DAYS,
        "full_exit_decision_types": sorted(FULL_EXIT_DECISION_TYPES),
        "bounded_storage": {
            "current_decision_hot_path_whole_run_scan": False,
            "compaction_rule": "retain rows only while exit_date is within recent-exit guard TTL for the materialization business_date",
        },
        "emitted_count": len(emitted_rows),
        "retained_count": retained_count,
        "expired_count": expired_count,
        "malformed_count": malformed_count + len(malformed_exit_rows),
        "malformed_exit_rows": malformed_exit_rows,
        "rows": [dict(row) for row in rows],
    }
    _write_json(output_path, payload)
    return RecentExitGuardMaterializationResult(
        status=status,
        reason=reason,
        output_path=str(output_path),
        run_id=runtime_test_run_id,
        business_date=business_date,
        emitted_count=len(emitted_rows),
        retained_count=retained_count,
        expired_count=expired_count,
        malformed_count=malformed_count + len(malformed_exit_rows),
        rows=rows,
    )


def _is_full_exit_execution(*, execution: LedgerExecutionRecord, order: LedgerOrderRecord | None) -> bool:
    side = str(execution.side or "").upper()
    decision_type = str(execution.source_decision_type or (order.source_decision_type if order else "") or "").upper()
    quantity = float(execution.filled_quantity or execution.quantity or 0.0)
    return side == "SELL" and decision_type in FULL_EXIT_DECISION_TYPES and quantity > 0.0


def _full_exit_guard_malformed_reason(*, execution: LedgerExecutionRecord, order: LedgerOrderRecord | None) -> str:
    symbol = str(execution.symbol or "").strip()
    campaign_id = str(execution.position_campaign_id or execution.campaign_id or (order.position_campaign_id if order else "") or "").strip()
    source_decision_id = str(execution.source_decision_id or (order.source_decision_id if order else "") or "").strip()
    source_pm_decision_id = str(execution.source_pm_decision_id or (order.source_pm_decision_id if order else "") or source_decision_id).strip()
    missing = [
        field
        for field, value in (
            ("symbol", symbol),
            ("prior_campaign_id", campaign_id),
            ("source_decision_id", source_decision_id),
            ("source_pm_decision_id", source_pm_decision_id),
        )
        if not value
    ]
    return "missing_" + "_".join(missing) if missing else ""


def recent_exit_guard_materialization_to_dict(result: RecentExitGuardMaterializationResult) -> dict[str, Any]:
    return asdict(result)


def _guard_row_from_execution(
    *,
    execution: LedgerExecutionRecord,
    order: LedgerOrderRecord | None,
    business_date: str,
    runtime_test_run_id: str,
) -> dict[str, Any] | None:
    side = str(execution.side or "").upper()
    decision_type = str(execution.source_decision_type or (order.source_decision_type if order else "") or "").upper()
    quantity = float(execution.filled_quantity or execution.quantity or 0.0)
    if side != "SELL" or decision_type not in FULL_EXIT_DECISION_TYPES or quantity <= 0.0:
        return None
    symbol = str(execution.symbol or "").strip()
    campaign_id = str(execution.position_campaign_id or execution.campaign_id or (order.position_campaign_id if order else "") or "").strip()
    source_decision_id = str(execution.source_decision_id or (order.source_decision_id if order else "") or "").strip()
    source_pm_decision_id = str(execution.source_pm_decision_id or (order.source_pm_decision_id if order else "") or source_decision_id).strip()
    if not symbol or not campaign_id or not source_decision_id or not source_pm_decision_id:
        return None
    reason_codes = _reason_codes_from_order(order)
    prior_exit_reason = _prior_exit_reason_from_order(order) or decision_type
    row_identity = {
        "symbol": symbol,
        "business_date": business_date,
        "campaign_id": campaign_id,
        "source_decision_id": source_decision_id,
        "execution_id": execution.execution_id,
    }
    return {
        "guard_id": "recent-exit-guard-" + _stable_hash(row_identity)[:20],
        "symbol": symbol,
        "most_recent_full_exit_business_date": business_date,
        "prior_exit_business_date": business_date,
        "prior_campaign_id": campaign_id,
        "prior_exit_campaign_id": campaign_id,
        "source_pm_decision_id": source_pm_decision_id,
        "source_decision_id": source_decision_id,
        "source_decision_type": decision_type,
        "prior_exit_provenance_status": "PASS",
        "prior_exit_reason": prior_exit_reason,
        "reason_codes": reason_codes,
        "recent_exit_guard_state": "ACTIVE_RECENT_EXIT_GUARD",
        "recent_exit_guard_status": "FAIL_CLOSED",
        "recent_exit_guard_reason": "recent_exit_churn_guard_active",
        "guard_ttl_business_days": RECENT_EXIT_GUARD_TTL_BUSINESS_DAYS,
        "runtime_test_run_id": runtime_test_run_id,
        "materialized_from": {
            "authority": "committed_ledger_execution",
            "execution_id": execution.execution_id,
            "order_id": execution.order_id,
            "pending_item_id": execution.pending_item_id,
            "order_plan_item_id": execution.order_plan_item_id,
        },
    }


def _orders_by_id(orders: Iterable[LedgerOrderRecord]) -> dict[str, LedgerOrderRecord]:
    result: dict[str, LedgerOrderRecord] = {}
    for order in orders:
        for key in (order.order_id, order.dedup_key, order.record_id):
            text = str(key or "")
            if text:
                result[text] = order
    return result


def _reason_codes_from_order(order: LedgerOrderRecord | None) -> list[str]:
    if order is None:
        return []
    values: list[str] = []
    _collect_reason_codes(order.strategy_authority_lineage, values)
    return sorted(set(values))


def _prior_exit_reason_from_order(order: LedgerOrderRecord | None) -> str:
    if order is None:
        return ""
    lineage = order.strategy_authority_lineage
    if not isinstance(lineage, Mapping):
        return ""
    for key in ("prior_exit_reason", "pm_reason", "reason", "exit_reason"):
        value = lineage.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _collect_reason_codes(value: Any, result: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in {"reason_codes", "prior_exit_reason_codes", "pm_reason_codes"} and isinstance(nested, list):
                result.extend(str(item) for item in nested if str(item))
            else:
                _collect_reason_codes(nested, result)
    elif isinstance(value, list):
        for item in value:
            _collect_reason_codes(item, result)


def _load_existing_rows(path: Path) -> list[Any]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    rows = payload.get("rows") if isinstance(payload, Mapping) else None
    return rows if isinstance(rows, list) else []


def _normalize_existing_row(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, Mapping):
        return None
    symbol = str(row.get("symbol") or row.get("security_code") or row.get("code") or "").strip()
    exit_date = str(row.get("most_recent_full_exit_business_date") or row.get("prior_exit_business_date") or "").strip()
    if not symbol or not exit_date:
        return None
    normalized = dict(row)
    normalized["symbol"] = symbol
    normalized["most_recent_full_exit_business_date"] = exit_date
    normalized["prior_exit_business_date"] = exit_date
    normalized.setdefault("guard_ttl_business_days", RECENT_EXIT_GUARD_TTL_BUSINESS_DAYS)
    return normalized


def _is_active_for_storage(exit_date: str, business_date: str) -> bool:
    return _completed_business_days_between(exit_date, business_date) < RECENT_EXIT_GUARD_TTL_BUSINESS_DAYS


def _completed_business_days_between(start_date: str, end_date: str) -> int:
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        return RECENT_EXIT_GUARD_TTL_BUSINESS_DAYS
    if end <= start:
        return 0
    days = 0
    current = start
    while True:
        current = date.fromordinal(current.toordinal() + 1)
        if current >= end:
            break
        if current.weekday() < 5:
            days += 1
    return days


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _stable_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")).hexdigest()
