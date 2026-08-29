"""Canonical performance event view for Runtime v2 Persistent Ledger."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


CANONICAL_EXECUTION_EVIDENCE_TYPE = "execution_equivalent"
RAW_BROKER_DETAIL_EXECUTION_EVIDENCE_TYPE = "broker_detail_execution"


@dataclass(frozen=True)
class CanonicalPerformanceExecutionEvent:
    canonical_execution_id: str
    source_execution_id: str
    source_order_id: str
    pending_item_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    executed_at: str
    business_date: str
    gross_notional: float
    execution_environment: str
    evidence_type: str
    source: str
    canonical_dedup_key: str
    lineage: dict[str, Any]
    source_decision_id: str = ""
    source_pm_decision_id: str = ""
    source_decision_type: str = ""
    source_pm_business_date: str = ""
    source_position_symbol: str = ""
    position_campaign_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CanonicalPerformanceFillResolution:
    status: str
    reason: str
    events: tuple[CanonicalPerformanceExecutionEvent, ...]
    raw_execution_count: int
    canonical_execution_count: int
    raw_broker_detail_count: int
    duplicate_canonical_count: int
    missing_canonical_equivalent_count: int
    errors: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return self.status == "PASS"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["events"] = [event.to_dict() for event in self.events]
        payload["valid"] = self.valid
        return payload


def load_canonical_execution_events(
    *,
    executions_path: Path | str,
    orders_path: Path | str | None = None,
) -> CanonicalPerformanceFillResolution:
    """Load canonical performance fills from Persistent Ledger JSONL files."""

    executions = _load_jsonl(Path(executions_path))
    orders = _load_jsonl(Path(orders_path)) if orders_path is not None else ()
    return resolve_performance_fills(executions=executions, orders=orders)


def iter_canonical_ledger_executions(
    executions: Iterable[dict[str, Any]],
    *,
    orders: Iterable[dict[str, Any]] = (),
) -> tuple[CanonicalPerformanceExecutionEvent, ...]:
    """Return canonical executions or raise when the ledger is not performance-ready."""

    resolution = resolve_performance_fills(executions=executions, orders=orders)
    if not resolution.valid:
        raise ValueError(resolution.reason)
    return resolution.events


def resolve_performance_fills(
    *,
    executions: Iterable[dict[str, Any]],
    orders: Iterable[dict[str, Any]] = (),
) -> CanonicalPerformanceFillResolution:
    """Resolve ledger executions into the canonical performance fill view.

    The canonical performance representation is intentionally the same
    authority that Runtime-owned accounting uses: ``execution_equivalent``.
    Raw broker-detail executions remain audit evidence and are not counted for
    trade count, turnover, return attribution, or holding-period metrics.
    """

    execution_rows = tuple(dict(row) for row in executions)
    order_rows = tuple(dict(row) for row in orders)
    canonical_rows = tuple(
        row
        for row in execution_rows
        if str(row.get("execution_evidence_type") or "") == CANONICAL_EXECUTION_EVIDENCE_TYPE
    )
    raw_detail_rows = tuple(
        row
        for row in execution_rows
        if str(row.get("execution_evidence_type") or "") == RAW_BROKER_DETAIL_EXECUTION_EVIDENCE_TYPE
    )
    if raw_detail_rows and not canonical_rows:
        return CanonicalPerformanceFillResolution(
            status="REVIEW_REQUIRED",
            reason="canonical_execution_equivalent_missing",
            events=(),
            raw_execution_count=len(execution_rows),
            canonical_execution_count=0,
            raw_broker_detail_count=len(raw_detail_rows),
            duplicate_canonical_count=0,
            missing_canonical_equivalent_count=len(raw_detail_rows),
            errors=("raw_broker_detail_without_execution_equivalent",),
        )

    submit_orders = _submit_orders_by_match_key(order_rows)
    seen: set[str] = set()
    duplicate_count = 0
    events: list[CanonicalPerformanceExecutionEvent] = []
    errors: list[str] = []
    for row in canonical_rows:
        event = _canonical_event(row, submit_orders=submit_orders)
        if not event.canonical_dedup_key:
            errors.append("canonical_execution_dedup_key_missing")
            continue
        if event.canonical_dedup_key in seen:
            duplicate_count += 1
            continue
        seen.add(event.canonical_dedup_key)
        events.append(event)

    if errors:
        return CanonicalPerformanceFillResolution(
            status="REVIEW_REQUIRED",
            reason="canonical_execution_contract_invalid",
            events=tuple(events),
            raw_execution_count=len(execution_rows),
            canonical_execution_count=len(events),
            raw_broker_detail_count=len(raw_detail_rows),
            duplicate_canonical_count=duplicate_count,
            missing_canonical_equivalent_count=0,
            errors=tuple(errors),
        )

    return CanonicalPerformanceFillResolution(
        status="PASS",
        reason="canonical_execution_equivalent_resolved",
        events=tuple(events),
        raw_execution_count=len(execution_rows),
        canonical_execution_count=len(events),
        raw_broker_detail_count=len(raw_detail_rows),
        duplicate_canonical_count=duplicate_count,
        missing_canonical_equivalent_count=0,
    )


def _canonical_event(
    row: dict[str, Any],
    *,
    submit_orders: dict[tuple[str, str, float, str], dict[str, Any]],
) -> CanonicalPerformanceExecutionEvent:
    symbol = str(row.get("symbol") or row.get("broker_issue_code") or "").strip()
    side = str(row.get("side") or "").upper()
    quantity = _number(row.get("filled_quantity") or row.get("quantity"))
    price = _number(row.get("price") or row.get("average_price"))
    business_date = str(row.get("business_date") or "")
    submit = submit_orders.get((symbol, side, quantity, business_date)) or submit_orders.get((symbol, side, quantity, ""))
    source_execution_id = str(row.get("execution_id") or row.get("record_id") or "")
    source_order_id = str(row.get("order_id") or row.get("source_order_hash") or "")
    canonical_dedup_key = str(row.get("dedup_key") or source_execution_id or row.get("execution_key") or "")
    return CanonicalPerformanceExecutionEvent(
        canonical_execution_id=f"canonical-performance:{canonical_dedup_key}",
        source_execution_id=source_execution_id,
        source_order_id=source_order_id,
        pending_item_id=str((submit or {}).get("pending_item_id") or row.get("pending_item_id") or ""),
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        executed_at=str(row.get("executed_at") or row.get("recorded_at") or row.get("created_at") or ""),
        business_date=business_date,
        gross_notional=_number(row.get("cash_effect")) or quantity * price,
        execution_environment=str(row.get("mode") or row.get("environment") or ""),
        evidence_type=CANONICAL_EXECUTION_EVIDENCE_TYPE,
        source=str(row.get("source") or ""),
        canonical_dedup_key=canonical_dedup_key,
        source_decision_id=str(row.get("source_decision_id") or row.get("source_pm_decision_id") or ""),
        source_pm_decision_id=str(row.get("source_pm_decision_id") or row.get("source_decision_id") or ""),
        source_decision_type=str(row.get("source_decision_type") or ""),
        source_pm_business_date=str(row.get("source_pm_business_date") or ""),
        source_position_symbol=str(row.get("source_position_symbol") or ""),
        position_campaign_id=str(row.get("position_campaign_id") or ""),
        lineage={
            "submit_order_record_id": str((submit or {}).get("record_id") or ""),
            "submit_order_id": str((submit or {}).get("order_id") or ""),
            "pending_plan_id": str((submit or {}).get("pending_plan_id") or ""),
            "pending_item_id": str((submit or {}).get("pending_item_id") or row.get("pending_item_id") or ""),
            "source_order_hash": str(row.get("source_order_hash") or ""),
            "source_broker_order_hash": str(row.get("source_broker_order_hash") or ""),
            "source_position_hash": str(row.get("source_position_hash") or ""),
            "source_decision_id": str(row.get("source_decision_id") or row.get("source_pm_decision_id") or ""),
            "source_pm_decision_id": str(row.get("source_pm_decision_id") or row.get("source_decision_id") or ""),
            "source_decision_type": str(row.get("source_decision_type") or ""),
            "source_pm_business_date": str(row.get("source_pm_business_date") or ""),
            "source_position_symbol": str(row.get("source_position_symbol") or ""),
            "position_campaign_id": str(row.get("position_campaign_id") or ""),
            "source_execution_record_id": str(row.get("record_id") or ""),
            "source_execution_dedup_key": str(row.get("dedup_key") or ""),
        },
    )


def _submit_orders_by_match_key(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str, float, str], dict[str, Any]]:
    result: dict[tuple[str, str, float, str], dict[str, Any]] = {}
    for row in rows:
        if row.get("source") != "runtime_v2_submit_pipeline":
            continue
        if str(row.get("status") or "").upper() != "ACCEPTED":
            continue
        normalization = row.get("issue_code_normalization") or {}
        symbol = str(normalization.get("broker_issue_code") or row.get("symbol") or "").strip()
        side = str(row.get("side") or "").upper()
        quantity = _number(row.get("quantity"))
        business_date = str(row.get("business_date") or "")
        result.setdefault((symbol, side, quantity, business_date), row)
        result.setdefault((symbol, side, quantity, ""), row)
    return result


def _load_jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    if not path.exists():
        return ()
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return tuple(rows)


def _number(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
