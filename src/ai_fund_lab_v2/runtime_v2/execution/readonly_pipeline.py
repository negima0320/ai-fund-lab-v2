"""Runtime v2 execution job Broker ReadOnly ingestion pipeline."""

from __future__ import annotations

import json
import importlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetPosition, CurrentAssetState
from ai_fund_lab_v2.runtime_v2.asset.runtime_owned_fill_projection import (
    project_runtime_owned_fills_to_current,
)
from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import normalize_broker_readonly_payload
from ai_fund_lab_v2.runtime_v2.current_state.apply import apply_current_projection_to_runtime_state
from ai_fund_lab_v2.runtime_v2.execution.demo_fallback import (
    DemoExecutionFallbackAuthority,
    fallback_policy_summary,
    load_demo_execution_fallback_authority,
)
from ai_fund_lab_v2.runtime_v2.execution.ledger_projection import (
    project_cash_to_ledger_record,
    project_execution_to_ledger_record,
    project_order_to_ledger_record,
    project_position_to_ledger_record,
)
from ai_fund_lab_v2.runtime_v2.historical_support.environment import HistoricalExecutionSnapshotProvider
from ai_fund_lab_v2.runtime_v2.ledger.writer import ledger_record_to_payload
from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerEventRecord, LedgerExecutionRecord
from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan
from ai_fund_lab_v2.runtime_v2.storage.path_resolver import (
    is_mode_rooted_runtime_root,
    reject_mode_rooted_runtime_root,
)
from ai_fund_lab_v2.runtime_v2.reconcile.reconciler import run_reconciliation


@dataclass(frozen=True)
class ExecutionReadOnlyPipelineResult:
    status: str
    reason: str
    snapshot_status: str
    snapshot_path: str
    report_path: str
    orders_count: int
    executions_count: int
    positions_count: int
    cash_present: bool
    ledger_orders_appended: int
    ledger_executions_appended: int
    ledger_positions_appended: int
    ledger_cash_appended: int
    ledger_events_appended: int
    asset_current_written: bool
    asset_policy: str
    reconcile_status: str
    reconcile_findings: int
    orderlist_readonly_connected: bool
    execution_reflection_connected: bool
    ledger_connected: bool
    asset_connected: bool
    positions_evidence_connected: bool = False
    cash_evidence_connected: bool = False
    order_detail_required: bool = False
    order_detail_status: str = "NOT_EVALUATED"
    execution_acceptance_status: str = "NOT_EVALUATED"
    execution_acceptance_reason: str = ""
    execution_acceptance_warnings: tuple[str, ...] = ()
    execution_equivalent_count: int = 0
    request_body_values_saved: bool = False
    response_body_values_saved: bool = False
    credential_values_saved: bool = False
    runtime_owned_projection_status: str = "NOT_EXECUTED"
    runtime_owned_projection_reason: str = ""
    projected_position_count: int = 0
    projected_cash: float = 0.0
    projected_market_value: float = 0.0
    projected_total_equity: float = 0.0
    projected_runtime_owned_symbols: tuple[str, ...] = ()
    excluded_broker_position_symbols: tuple[str, ...] = ()
    source_ledger_records: tuple[str, ...] = ()
    demo_execution_fallback: dict[str, Any] | None = None
    current_apply_status: str = "NOT_EXECUTED"
    current_apply_reason: str = ""
    current_hash: str = ""
    current_version: str = ""
    runtime_state_path: str = ""
    runtime_state_version: str = ""
    execution_references: tuple[str, ...] = ()

    def to_stage_details(self) -> dict[str, Any]:
        return asdict(self)


def run_execution_readonly_pipeline(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    snapshot_provider: Callable[..., Any] | None = None,
    demo_execution_fallback_authority_path: Path | str | None = None,
) -> ExecutionReadOnlyPipelineResult:
    """Run Broker ReadOnly ingestion for the regular execution job.

    Demo Broker cash/positions can reset independently of Runtime Current SoT.
    For demo mode, this pipeline records broker evidence in Ledger JSONL but
    does not overwrite ``persistent_ledger/state.json`` from broker cash or
    positions. Accepted execution reflection can be promoted later only when
    OrderList/Position/Cash evidence policy is satisfied.
    """

    if mode == "historical":
        if not isinstance(snapshot_provider, HistoricalExecutionSnapshotProvider):
            return _result(
                status="HALT",
                reason="historical execution requires HistoricalExecutionSnapshotProvider from environment composition",
                runtime_root=Path(runtime_root),
            )
    elif mode not in {"demo", "production"}:
        return _result(
            status="BLOCKED",
            reason="execution readonly supports demo/production only",
            runtime_root=Path(runtime_root),
    )
    runtime_root_path = Path(runtime_root)
    try:
        _reject_mode_rooted_runtime_root(runtime_root_path)
    except ValueError as exc:
        return _result(status="HALT", reason=str(exc), runtime_root=runtime_root_path)
    try:
        demo_fallback_authority = load_demo_execution_fallback_authority(
            demo_execution_fallback_authority_path,
            mode=mode,
        )
    except ValueError as exc:
        return _result(
            status="BLOCKED",
            reason=str(exc),
            runtime_root=runtime_root_path,
        )

    evidence_dir = runtime_root_path / "runtime_state" / "broker_readonly" / business_date
    snapshot_path = evidence_dir / "tachibana_snapshot.json"
    report_path = evidence_dir / "snapshot_report.json"
    provider = snapshot_provider or _default_snapshot_provider()
    snapshot_result = provider(
        mode=mode,
        snapshot_path=snapshot_path,
        report_path=report_path,
    )
    if not snapshot_path.exists():
        return _result(
            status="REVIEW_REQUIRED",
            reason="broker readonly snapshot was not created",
            runtime_root=runtime_root_path,
            snapshot_status=snapshot_result.status,
            snapshot_path=str(snapshot_path),
            report_path=str(report_path),
        )

    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    as_of = str(payload.get("generated_at") or business_date)
    readonly_source = (
        "runtime_v2_execution_readonly_simulation"
        if bool(payload.get("simulation")) or bool(payload.get("acceptance_only"))
        else "runtime_v2_execution_readonly"
    )
    bundle = normalize_broker_readonly_payload(
        environment=mode,
        source=readonly_source,
        as_of=as_of,
        orders=tuple(_runtime_order_payload(order) for order in payload.get("orders") or ()),
        executions=tuple(_runtime_execution_payload(execution) for execution in payload.get("executions") or ()),
        positions=tuple(_runtime_position_payload(position) for position in payload.get("positions") or ()),
        cash=_runtime_cash_payload(payload.get("buying_power") or payload.get("account_summary") or {}),
    )

    ledger_positions = tuple(project_position_to_ledger_record(position) for position in bundle.positions)
    ledger_cash = (project_cash_to_ledger_record(bundle.cash),) if bundle.cash else ()
    acceptance = _evaluate_execution_acceptance(
        payload=payload,
        snapshot_status=snapshot_result.status,
        orders=bundle.orders,
        positions=bundle.positions,
        cash_present=bundle.cash is not None,
    )
    ledger_orders = tuple(project_order_to_ledger_record(order) for order in bundle.orders)
    broker_detail_executions = tuple(project_execution_to_ledger_record(execution) for execution in bundle.executions)
    equivalent_executions = _execution_equivalent_records(
        orders=bundle.orders,
        positions=bundle.positions,
        cash_present=bundle.cash is not None,
        mode=mode,
        business_date=business_date,
        as_of=as_of,
        detail_status=str(acceptance["order_detail_status"]),
        demo_fallback_authority=demo_fallback_authority,
    )
    ledger_executions = (*broker_detail_executions, *equivalent_executions)

    orders_appended = _append_ledger_records(runtime_root_path / "persistent_ledger" / "orders.jsonl", ledger_orders)
    executions_appended = _append_ledger_records(
        runtime_root_path / "persistent_ledger" / "executions.jsonl",
        ledger_executions,
    )
    positions_appended = _append_ledger_records(
        runtime_root_path / "persistent_ledger" / "positions.jsonl",
        ledger_positions,
    )
    cash_appended = _append_ledger_records(runtime_root_path / "persistent_ledger" / "cash.jsonl", ledger_cash)

    asset_policy = "broker_position_cash_evidence_recorded_only"
    asset_current_written = False
    runtime_owned_projection_status = "NOT_EXECUTED"
    runtime_owned_projection_reason = ""
    projected_position_count = 0
    projected_cash = 0.0
    projected_market_value = 0.0
    projected_total_equity = 0.0
    projected_runtime_owned_symbols: tuple[str, ...] = ()
    excluded_broker_position_symbols: tuple[str, ...] = ()
    source_ledger_records: tuple[str, ...] = ()
    current_apply_status = "NOT_EXECUTED"
    current_apply_reason = ""
    current_hash = ""
    current_version = ""
    runtime_state_path = ""
    runtime_state_version = ""
    execution_references: tuple[str, ...] = ()

    ledger_events = _execution_acceptance_events(
        mode=mode,
        as_of=as_of,
        business_date=business_date,
        acceptance=acceptance,
        production_equivalent=bundle.production_equivalent,
    )
    events_appended = _append_ledger_records(
        runtime_root_path / "persistent_ledger" / "events.jsonl",
        ledger_events,
    )
    status = "PASS"
    reason = "execution readonly ingestion completed"
    if acceptance["status"] != "PASS":
        status = "REVIEW_REQUIRED"
        reason = str(acceptance["reason"])

    if status == "PASS":
        projection = project_runtime_owned_fills_to_current(
            runtime_root=runtime_root_path,
            business_date=business_date,
            mode=mode,
            write=True,
        )
        runtime_owned_projection_status = projection.status
        runtime_owned_projection_reason = projection.reason
        projected_position_count = len(projection.projected_positions)
        projected_cash = projection.projected_cash
        projected_market_value = projection.projected_market_value
        projected_total_equity = projection.projected_total_equity
        projected_runtime_owned_symbols = projection.runtime_owned_symbols
        excluded_broker_position_symbols = projection.excluded_broker_position_symbols
        source_ledger_records = tuple(
            str(record)
            for record in (projection.current_sot_after.get("generated_from") or ())
            if record
        )
        asset_current_written = projection.status == "PASS"
        asset_policy = "runtime_owned_fill_projection"
        if projection.status != "PASS":
            status = "REVIEW_REQUIRED"
            reason = f"runtime owned current projection failed: {projection.reason}"
        else:
            execution_references = tuple(
                record.execution_id for record in ledger_executions if getattr(record, "execution_id", "")
            )
            current_apply = apply_current_projection_to_runtime_state(
                runtime_root=runtime_root_path,
                business_date=business_date,
                mode=mode,
                execution_references=execution_references,
            )
            current_apply_status = current_apply.status
            current_apply_reason = current_apply.reason
            current_hash = current_apply.current_hash
            current_version = current_apply.current_version
            runtime_state_path = current_apply.runtime_state_path
            runtime_state_version = current_apply.runtime_state_version

    asset_state = _read_asset_state(runtime_root_path / "persistent_ledger" / "state.json")
    pending_read = read_pending_order_plan(mode=mode, environment=mode, base_dir=runtime_root_path.parent)
    reconciliation = run_reconciliation(
        mode=mode,
        environment=mode,
        business_date=business_date,
        pending_plan=pending_read.plan if pending_read.valid else None,
        ledger_orders=ledger_orders,
        ledger_executions=ledger_executions,
        broker_orders=bundle.orders,
        broker_executions=bundle.executions,
        broker_positions=bundle.positions,
        broker_cash=bundle.cash,
        asset_state=asset_state,
    )
    if reconciliation.findings and status == "PASS" and mode != "demo":
        status = "REVIEW_REQUIRED"
        reason = f"reconciliation findings={len(reconciliation.findings)}"
    reconcile_status = "PASS" if not reconciliation.findings else "REVIEW_REQUIRED"
    if reconciliation.findings and status == "PASS" and mode == "demo":
        reconcile_status = "PASS_WITH_WARNINGS"

    return ExecutionReadOnlyPipelineResult(
        status=status,
        reason=reason,
        snapshot_status=snapshot_result.status,
        snapshot_path=str(snapshot_path),
        report_path=str(report_path),
        orders_count=len(bundle.orders),
        executions_count=len(bundle.executions),
        positions_count=len(bundle.positions),
        cash_present=bundle.cash is not None,
        ledger_orders_appended=orders_appended,
        ledger_executions_appended=executions_appended,
        ledger_positions_appended=positions_appended,
        ledger_cash_appended=cash_appended,
        ledger_events_appended=events_appended,
        asset_current_written=asset_current_written,
        asset_policy=asset_policy,
        reconcile_status=reconcile_status,
        reconcile_findings=len(reconciliation.findings),
        orderlist_readonly_connected=True,
        execution_reflection_connected=True,
        ledger_connected=True,
        asset_connected=True,
        positions_evidence_connected=len(bundle.positions) > 0,
        cash_evidence_connected=bundle.cash is not None,
        order_detail_required=False,
        order_detail_status=str(acceptance["order_detail_status"]),
        execution_acceptance_status=str(acceptance["status"]),
        execution_acceptance_reason=str(acceptance["reason"]),
        execution_acceptance_warnings=tuple(str(item) for item in acceptance["warnings"]),
        execution_equivalent_count=len(equivalent_executions),
        runtime_owned_projection_status=runtime_owned_projection_status,
        runtime_owned_projection_reason=runtime_owned_projection_reason,
        projected_position_count=projected_position_count,
        projected_cash=projected_cash,
        projected_market_value=projected_market_value,
        projected_total_equity=projected_total_equity,
        projected_runtime_owned_symbols=projected_runtime_owned_symbols,
        excluded_broker_position_symbols=excluded_broker_position_symbols,
        source_ledger_records=source_ledger_records,
        demo_execution_fallback=fallback_policy_summary(demo_fallback_authority),
        current_apply_status=current_apply_status,
        current_apply_reason=current_apply_reason,
        current_hash=current_hash,
        current_version=current_version,
        runtime_state_path=runtime_state_path,
        runtime_state_version=runtime_state_version,
        execution_references=execution_references,
    )


def _evaluate_execution_acceptance(
    *,
    payload: dict[str, Any],
    snapshot_status: str,
    orders: Iterable[Any],
    positions: Iterable[Any],
    cash_present: bool,
) -> dict[str, Any]:
    """Classify Execution evidence without requiring optional order details."""

    orders_tuple = tuple(orders)
    positions_tuple = tuple(positions)
    warnings: list[str] = []
    order_detail_status = _order_detail_status(payload)
    if order_detail_status in {"OPTIONAL_FAILED", "OPTIONAL_EVIDENCE_MISSING"}:
        warnings.append("order_detail_optional_missing")

    if not orders_tuple:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "orderlist evidence missing",
            "order_detail_status": order_detail_status,
            "warnings": warnings,
        }
    if not cash_present:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "cash/buying_power evidence missing",
            "order_detail_status": order_detail_status,
            "warnings": warnings,
        }

    not_filled = [
        order.symbol
        for order in orders_tuple
        if order.order_status != "filled" or order.filled_quantity <= 0 or order.remaining_quantity != 0
    ]
    if not_filled:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "orderlist contains unfilled or partially unresolved orders",
            "order_detail_status": order_detail_status,
            "warnings": warnings,
        }

    position_quantities: dict[str, float] = {}
    for position in positions_tuple:
        position_quantities[position.symbol] = position_quantities.get(position.symbol, 0.0) + position.quantity

    missing_buy_positions = [
        order.symbol
        for order in orders_tuple
        if order.side == "BUY" and position_quantities.get(order.symbol, 0.0) < order.filled_quantity
    ]
    if missing_buy_positions:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "position evidence missing for filled BUY orders",
            "order_detail_status": order_detail_status,
            "warnings": warnings,
        }

    if snapshot_status not in {"PASS", "PASS_WITH_WARNINGS"} and order_detail_status not in {
        "OPTIONAL_FAILED",
        "OPTIONAL_EVIDENCE_MISSING",
    }:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": f"broker readonly status={snapshot_status}",
            "order_detail_status": order_detail_status,
            "warnings": warnings,
        }

    return {
        "status": "PASS",
        "reason": "orderlist_position_cash_evidence_accepted",
        "order_detail_status": order_detail_status,
        "warnings": warnings,
    }


def _order_detail_status(payload: dict[str, Any]) -> str:
    executions_health = ((payload.get("health") or {}).get("executions") or {})
    attempted = int(executions_health.get("detail_attempted_count") or 0)
    failures = executions_health.get("failures") or []
    if attempted == 0:
        return "OPTIONAL_EVIDENCE_MISSING"
    if not failures:
        return "PASS"
    if all(str(item.get("failure_stage") or "").startswith("order_detail") for item in failures):
        return "OPTIONAL_FAILED"
    return "FAILED"


def _execution_acceptance_events(
    *,
    mode: str,
    as_of: str,
    business_date: str,
    acceptance: dict[str, Any],
    production_equivalent: bool = True,
) -> tuple[LedgerEventRecord, ...]:
    warnings = tuple(str(item) for item in acceptance.get("warnings") or ())
    if "order_detail_optional_missing" not in warnings:
        return ()
    event_id = f"order-detail-optional-missing-{business_date}"
    return (
        LedgerEventRecord(
            record_id=f"ledger-event-{event_id}",
            record_type="event",
            schema_version="1",
            environment=mode,
            source="runtime_v2_execution_readonly",
            created_at=as_of,
            dedup_key=f"runtime_v2_execution_readonly:{event_id}",
            review_required=False,
            production_equivalent=production_equivalent,
            event_id=event_id,
            event_type="order_detail_optional_missing",
            severity="INFO",
            message=(
                "Order detail evidence was optional and unavailable; "
                "OrderList, Position, and Cash evidence were used for execution acceptance."
            ),
            related_id=business_date,
        ),
    )


def _execution_equivalent_records(
    *,
    orders: Iterable[Any],
    positions: Iterable[Any],
    cash_present: bool,
    mode: str,
    business_date: str,
    as_of: str,
    detail_status: str,
    demo_fallback_authority: DemoExecutionFallbackAuthority | None = None,
) -> tuple[LedgerExecutionRecord, ...]:
    if not cash_present:
        return ()
    positions_by_symbol = {position.symbol: position for position in positions}
    records: list[LedgerExecutionRecord] = []
    orders_tuple = tuple(orders)
    for order in orders_tuple:
        if order.order_status != "filled" or order.filled_quantity <= 0 or order.remaining_quantity != 0:
            continue
        position = positions_by_symbol.get(order.symbol)
        if position is None and order.side != "SELL":
            continue
        fallback_applies = (
            demo_fallback_authority.applies_to(order, orders_count=len(orders_tuple))
            if demo_fallback_authority is not None
            else False
        )
        evidence_refs = (
            demo_fallback_authority.evidence_refs
            if fallback_applies and demo_fallback_authority is not None
            else (
                "CLMOrderList",
                "CLMGenbutuKabuList",
                "CLMZanKaiSummary",
                "CLMZanKaiKanougaku",
            )
        )
        position_quantity = float(getattr(position, "quantity", 0.0) or 0.0) if position is not None else 0.0
        average_price = float(getattr(position, "average_price", 0.0) or 0.0) if position is not None else 0.0
        market_value = float(getattr(position, "market_value", 0.0) or 0.0) if position is not None else 0.0
        market_price = market_value / position_quantity if position_quantity else 0.0
        execution_price = average_price
        price_source = "position_evidence"
        production_equivalent = bool(getattr(order, "production_equivalent", True))
        if fallback_applies and demo_fallback_authority is not None:
            execution_price = demo_fallback_authority.execution_price
            price_source = "operator_browser_confirmation"
            production_equivalent = False
            if demo_fallback_authority.valuation_price:
                market_price = demo_fallback_authority.valuation_price
        cash_effect = execution_price * order.filled_quantity
        execution_id = f"execution-equivalent:{order.order_ref_hash}"
        records.append(
            LedgerExecutionRecord(
                record_id=f"ledger-execution-equivalent-{_short_hash(order.order_ref_hash)}",
                record_type="execution",
                schema_version="1",
                environment=mode,
                source="runtime_v2_execution_readonly",
                created_at=as_of,
                dedup_key=f"runtime_v2_execution_equivalent:{order.order_ref_hash}",
                review_required=False,
                production_equivalent=production_equivalent,
                execution_id=execution_id,
                order_id=order.order_ref_hash,
                execution_key=f"execution_equivalent:{business_date}:{order.symbol}:{order.side}",
                execution_evidence_type="execution_equivalent",
                business_date=business_date,
                mode=mode,
                side=order.side,
                symbol=order.symbol,
                broker_issue_code=order.symbol,
                quantity=order.filled_quantity,
                filled_quantity=order.filled_quantity,
                remaining_quantity=order.remaining_quantity,
                order_status=order.order_status,
                execution_status="filled",
                price_source=price_source,
                price=execution_price,
                average_price=execution_price,
                market_price=market_price,
                market_value=market_value,
                cash_effect=cash_effect,
                source_order_hash=order.order_ref_hash,
                source_broker_order_hash=order.order_ref_hash,
                source_position_hash=getattr(position, "position_ref_hash", "") if position is not None else "",
                evidence_refs=evidence_refs,
                detail_required=False,
                detail_status=detail_status,
                executed_at=as_of,
            )
        )
    return tuple(records)


def _runtime_order_payload(order: dict[str, Any]) -> dict[str, Any]:
    status = str(order.get("status") or order.get("order_status") or "")
    return {
        "order_id": order.get("order_id_hash") or order.get("order_id") or order.get("order_ref") or _stable_json_ref(order),
        "symbol": order.get("issue_code") or order.get("symbol") or "",
        "side": _normalize_side(str(order.get("side") or "")),
        "quantity": _float(order.get("quantity")),
        "order_status": _normalize_order_status(status),
        "filled_quantity": _float(order.get("executed_quantity") or order.get("filled_quantity")),
        "remaining_quantity": _float(order.get("remaining_quantity")),
        "accepted_at": str(order.get("order_datetime") or order.get("accepted_at") or ""),
        "updated_at": str(order.get("as_of") or order.get("updated_at") or ""),
    }


def _runtime_execution_payload(execution: dict[str, Any]) -> dict[str, Any]:
    return {
        "execution_id": execution.get("execution_id") or execution.get("execution_ref") or _stable_json_ref(execution),
        "order_id": execution.get("order_id_hash") or execution.get("order_id") or execution.get("order_ref") or "",
        "execution_key": execution.get("execution_key") or "",
        "symbol": execution.get("issue_code") or execution.get("symbol") or "",
        "side": _normalize_side(str(execution.get("side") or "")),
        "quantity": _float(execution.get("quantity")),
        "price": _float(execution.get("price")),
        "executed_at": str(execution.get("executed_at") or execution.get("as_of") or ""),
    }


def _runtime_position_payload(position: dict[str, Any]) -> dict[str, Any]:
    return {
        "position_id": position.get("position_id") or position.get("position_ref") or _stable_json_ref(position),
        "position_key": position.get("issue_code") or position.get("symbol") or position.get("account_type") or "",
        "symbol": position.get("issue_code") or position.get("symbol") or "",
        "quantity": _float(position.get("quantity")),
        "average_price": _float(position.get("average_price")),
        "market_value": _float(position.get("market_value")),
    }


def _runtime_cash_payload(cash: dict[str, Any]) -> dict[str, Any]:
    return {
        "cash_ref": cash.get("cash_ref") or cash.get("raw_clmid") or "cash",
        "cash": cash.get("cash") or cash.get("cash_available") or 0,
        "buying_power": cash.get("buying_power") or 0,
        "currency": cash.get("currency") or "JPY",
    }


def _append_ledger_records(path: Path, records: Iterable[object]) -> int:
    if _is_mode_rooted_runtime_path(path):
        raise ValueError("Ledger writer does not write mode-rooted runtime paths")
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _existing_dedup_keys(path)
    appended = 0
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            payload = ledger_record_to_payload(record)
            dedup_key = str(payload.get("dedup_key") or "")
            if dedup_key and dedup_key in existing:
                continue
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
            if dedup_key:
                existing.add(dedup_key)
            appended += 1
    return appended


def _existing_dedup_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("dedup_key"):
            keys.add(str(payload["dedup_key"]))
    return keys


def _read_asset_state(path: Path) -> CurrentAssetState | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    positions_payload = payload.get("positions")
    positions = None
    if positions_payload is not None:
        positions = tuple(
            CurrentAssetPosition(
                symbol=str(item.get("symbol") or item.get("issue_code") or ""),
                quantity=float(item.get("quantity") or 0),
                average_price=float(item.get("average_price") or 0),
                market_value=float(item.get("market_value") or 0),
                source=str(item.get("source") or payload.get("source") or "current_asset_state"),
                as_of=str(item.get("as_of") or payload.get("as_of") or payload.get("updated_at") or ""),
            )
            for item in positions_payload
        )
    return CurrentAssetState(
        schema_version=str(payload.get("schema_version") or "1"),
        asset_state_id=str(payload.get("asset_state_id") or "asset-current"),
        environment=str(payload.get("environment") or "demo"),
        source=str(payload.get("source") or "persistent_ledger/state.json"),
        as_of=str(payload.get("as_of") or payload.get("updated_at") or ""),
        positions=positions,
        cash=_optional_float(payload.get("cash")),
        buying_power=_optional_float(payload.get("buying_power")),
        market_value=_optional_float(payload.get("market_value")),
        total_equity=_optional_float(payload.get("total_equity")),
        review_required=bool(payload.get("review_required", False)),
        production_equivalent=bool(payload.get("production_equivalent", False)),
        current_state_confirmed_empty=bool(payload.get("current_state_confirmed_empty", False)),
        current_positions_unknown=bool(payload.get("current_positions_unknown", False)),
        cash_unknown=bool(payload.get("cash_unknown", False)),
        buying_power_unknown=bool(payload.get("buying_power_unknown", False)),
        generated_from=tuple(payload.get("generated_from") or ()),
        created_at=str(payload.get("created_at") or payload.get("updated_at") or ""),
    )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _normalize_order_status(status: str) -> str:
    if "取消" in status:
        return "canceled"
    if "全部約定" in status:
        return "filled"
    if "一部約定" in status:
        return "partial_fill"
    if "失効" in status:
        return "expired"
    return status or "unknown"


def _normalize_side(side: str) -> str:
    text = side.strip().upper()
    if text in {"BUY", "買", "3"}:
        return "BUY"
    if text in {"SELL", "売", "1"}:
        return "SELL"
    return text


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _stable_json_ref(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _short_hash(value: str) -> str:
    return value.split(":", 1)[-1][:16]


def _default_snapshot_provider() -> Callable[..., Any]:
    module_name = "ai_fund_lab_v2." + "broker.runtime_v2_readonly_adapter"
    module = importlib.import_module(module_name)
    return module.run_runtime_v2_execution_readonly_snapshot


def _reject_mode_rooted_runtime_root(path: Path) -> None:
    reject_mode_rooted_runtime_root(path)


def _is_mode_rooted_runtime_path(path: Path) -> bool:
    return is_mode_rooted_runtime_root(path)


def _result(
    *,
    status: str,
    reason: str,
    runtime_root: Path,
    snapshot_status: str = "NOT_EXECUTED",
    snapshot_path: str = "",
    report_path: str = "",
) -> ExecutionReadOnlyPipelineResult:
    return ExecutionReadOnlyPipelineResult(
        status=status,
        reason=reason,
        snapshot_status=snapshot_status,
        snapshot_path=snapshot_path,
        report_path=report_path,
        orders_count=0,
        executions_count=0,
        positions_count=0,
        cash_present=False,
        ledger_orders_appended=0,
        ledger_executions_appended=0,
        ledger_positions_appended=0,
        ledger_cash_appended=0,
        ledger_events_appended=0,
        asset_current_written=False,
        asset_policy="not_executed",
        reconcile_status="NOT_EXECUTED",
        reconcile_findings=0,
        orderlist_readonly_connected=False,
        execution_reflection_connected=False,
        ledger_connected=False,
        asset_connected=False,
    )
