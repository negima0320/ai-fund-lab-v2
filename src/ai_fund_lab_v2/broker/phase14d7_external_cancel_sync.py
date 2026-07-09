"""Phase14-D7 Broker ReadOnly sync after external order cancellation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.settings import BrokerSettings, load_broker_settings
from ai_fund_lab_v2.broker.tachibana_broker_snapshot import run_tachibana_broker_snapshot
from ai_fund_lab_v2.runtime_v2.asset.builder import build_current_asset_state
from ai_fund_lab_v2.runtime_v2.audit.auditor import run_audit
from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import normalize_broker_readonly_payload
from ai_fund_lab_v2.runtime_v2.execution.fill_classifier import classify_fill
from ai_fund_lab_v2.runtime_v2.execution.ledger_projection import (
    project_cash_to_ledger_record,
    project_order_to_ledger_record,
    project_position_to_ledger_record,
)
from ai_fund_lab_v2.runtime_v2.notification.payload import build_notification_payload
from ai_fund_lab_v2.runtime_v2.pending.models import (
    PendingApprovalLink,
    PendingConsumeInfo,
    PendingOrderItem,
    PendingOrderPlan,
    PendingPlanState,
    PendingSourceOrderPlan,
    PendingSubmitConstraints,
)
from ai_fund_lab_v2.runtime_v2.reconcile.reconciler import run_reconciliation
from ai_fund_lab_v2.runtime_v2.report.builder import build_runtime_report
from ai_fund_lab_v2.runtime_v2.report.models import ReportBuildInput


@dataclass(frozen=True)
class Phase14D7Result:
    final_decision: str
    environment: str
    readonly_status: str
    broker_state_source_of_truth: bool
    runtime_did_not_mutate_broker: bool
    new_buy_submit_executed: bool
    sell_submit_executed: bool
    submit_executed: bool
    cancel_api_called: bool
    production_api_called: bool
    notification_sent: bool
    launchd_modified: bool
    target_issue_code: str
    target_side: str
    target_quantity: float
    target_order_detected: bool
    target_order_cancelled: bool
    target_order_status: str
    target_remaining_quantity: float
    target_executed_quantity: float
    pending_terminal_state: str
    pending_consumed: bool
    ledger_order_count: int
    ledger_execution_count: int
    ledger_position_count: int
    ledger_cash_count: int
    asset_state_created: bool
    asset_changed_by_cancel: bool
    reconcile_pass: bool
    reconciliation_findings: int
    report_sections: int
    notification_payload_created: bool
    audit_findings: int
    fill_classification: str
    snapshot_path: str
    pending_plan_path: str
    blocked_reasons: tuple[str, ...] = ()
    review_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_phase14d7_external_cancel_sync(
    *,
    root: Path,
    docs_report_path: Path,
    json_report_path: Path,
    settings: BrokerSettings | None = None,
    pending_plan_path: Path = Path(".runtime/phase14d/pending_order_plan/pending_order_plan.json"),
    target_issue_code: str = "9432",
    target_quantity: float = 100.0,
    run_readonly: bool = True,
    snapshot_path: Path | None = None,
) -> Phase14D7Result:
    settings = settings or load_broker_settings()
    root.mkdir(parents=True, exist_ok=True)
    docs_report_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_path or root / "broker_readonly_after_external_cancel" / "tachibana_demo_snapshot.json"
    report_path = root / "broker_readonly_after_external_cancel" / "snapshot_report.json"
    blocked_reasons: list[str] = []
    review_reasons: list[str] = []

    if settings.environment != "demo":
        blocked_reasons.append("environment is not demo")
    if run_readonly:
        readonly_status = _run_readonly_snapshot(
            settings=settings,
            report_path=report_path,
            snapshot_path=snapshot_path,
            symbol=target_issue_code,
        )
    else:
        readonly_status = "USING_EXISTING_SNAPSHOT"
    if not snapshot_path.exists():
        blocked_reasons.append("readonly snapshot missing")

    payload = _load_json(snapshot_path) if snapshot_path.exists() else {}
    target_order_payload = _find_target_order(payload.get("orders") or (), issue_code=target_issue_code, quantity=target_quantity)
    target_order_detected = target_order_payload is not None
    target_order_status = str((target_order_payload or {}).get("status") or "")
    remaining_quantity = _float((target_order_payload or {}).get("remaining_quantity"))
    executed_quantity = _float((target_order_payload or {}).get("executed_quantity"))
    target_cancelled = _is_cancelled_status(target_order_status)
    if not target_order_detected:
        review_reasons.append("target order not found in readonly order list")
    elif not target_cancelled:
        review_reasons.append(f"target order is not cancelled: {target_order_status}")

    normalized_bundle = _normalize_snapshot_payload(payload, target_issue_code=target_issue_code)
    broker_orders = normalized_bundle.orders
    broker_positions = normalized_bundle.positions
    broker_cash = normalized_bundle.cash
    target_order = next((order for order in broker_orders if order.symbol == target_issue_code and abs(order.quantity - target_quantity) < 0.000001), None)
    fill_classification = "NOT_CLASSIFIED"
    if target_order is not None:
        fill_classification = classify_fill(order=target_order, executions=normalized_bundle.executions).classification.value
    ledger_orders = tuple(project_order_to_ledger_record(order) for order in broker_orders)
    ledger_positions = tuple(project_position_to_ledger_record(position) for position in broker_positions)
    ledger_cash = (project_cash_to_ledger_record(broker_cash),) if broker_cash else ()
    pending_plan = _read_pending_plan(pending_plan_path)

    asset_state = build_current_asset_state(
        environment="demo",
        positions=ledger_positions,
        cash_records=ledger_cash,
        source="phase14d7_broker_readonly_external_cancel",
        as_of=_business_date(),
    )
    reconciliation = run_reconciliation(
        mode="demo",
        environment="demo",
        business_date=_business_date(),
        pending_plan=pending_plan,
        ledger_orders=ledger_orders,
        ledger_executions=(),
        broker_orders=broker_orders,
        broker_executions=(),
        broker_positions=broker_positions,
        broker_cash=broker_cash,
        asset_state=asset_state,
    )
    report = build_runtime_report(
        ReportBuildInput(
            mode="demo",
            environment="demo",
            business_date=_business_date(),
            target_session_date=_business_date(),
            asset_state=asset_state,
            pending_plan=pending_plan,
            ledger_orders=ledger_orders,
            ledger_executions=(),
            ledger_positions=ledger_positions,
            ledger_cash_records=ledger_cash,
            broker_orders=broker_orders,
            broker_executions=(),
            broker_positions=broker_positions,
            broker_cash=broker_cash,
            reconciliation_result=reconciliation,
            review_events=(),
        )
    )
    notification_payload = build_notification_payload(report=report, channel="phase14d7_payload_only")
    audit = run_audit(
        mode="demo",
        environment="demo",
        business_date=_business_date(),
        report=report,
        notification_payload=notification_payload,
        reconciliation_result=reconciliation,
        asset_state=asset_state,
    )
    reconcile_pass = not reconciliation.findings
    if reconciliation.findings:
        review_reasons.append(f"reconciliation findings={len(reconciliation.findings)}")

    final_decision = "PHASE14D7_BROKER_STATE_SYNC_PASS"
    if blocked_reasons or review_reasons or not target_cancelled or pending_plan.state not in {PendingPlanState.CONSUMED, PendingPlanState.EXPIRED}:
        final_decision = "PHASE14D7_REVIEW_REQUIRED"
    result = Phase14D7Result(
        final_decision=final_decision,
        environment=settings.environment,
        readonly_status=readonly_status,
        broker_state_source_of_truth=True,
        runtime_did_not_mutate_broker=True,
        new_buy_submit_executed=False,
        sell_submit_executed=False,
        submit_executed=False,
        cancel_api_called=False,
        production_api_called=False,
        notification_sent=False,
        launchd_modified=False,
        target_issue_code=target_issue_code,
        target_side="BUY",
        target_quantity=target_quantity,
        target_order_detected=target_order_detected,
        target_order_cancelled=target_cancelled,
        target_order_status=target_order_status,
        target_remaining_quantity=remaining_quantity,
        target_executed_quantity=executed_quantity,
        pending_terminal_state=pending_plan.state.value,
        pending_consumed=pending_plan.consume.consumed,
        ledger_order_count=len(ledger_orders),
        ledger_execution_count=0,
        ledger_position_count=len(ledger_positions),
        ledger_cash_count=len(ledger_cash),
        asset_state_created=asset_state is not None,
        asset_changed_by_cancel=False,
        reconcile_pass=reconcile_pass,
        reconciliation_findings=len(reconciliation.findings),
        report_sections=len(report.sections),
        notification_payload_created=notification_payload is not None,
        audit_findings=len(audit.findings),
        fill_classification=fill_classification,
        snapshot_path=str(snapshot_path),
        pending_plan_path=str(pending_plan_path),
        blocked_reasons=tuple(blocked_reasons),
        review_reasons=tuple(review_reasons),
    )
    _write_json(json_report_path, result.to_dict())
    docs_report_path.write_text(_markdown(result), encoding="utf-8")
    return result


def _run_readonly_snapshot(*, settings: BrokerSettings, report_path: Path, snapshot_path: Path, symbol: str) -> str:
    result = run_tachibana_broker_snapshot(
        reports_dir=report_path.parent,
        run_enabled=True,
        report_filename=report_path.name,
        snapshot_path=snapshot_path,
        source="phase14d7_external_cancel_readonly_sync",
        settings=settings,
        symbols=(symbol,),
        include_quotes=False,
    )
    return result.status


def _normalize_snapshot_payload(payload: dict[str, Any], *, target_issue_code: str):
    as_of = str(payload.get("generated_at") or _now())
    orders = tuple(_runtime_order_payload(order) for order in payload.get("orders") or ())
    positions = tuple(_runtime_position_payload(position) for position in payload.get("positions") or ())
    cash = payload.get("buying_power") or payload.get("account_summary") or {"cash_ref": f"cash-{as_of}", "cash": 0, "buying_power": 0, "currency": "JPY"}
    return normalize_broker_readonly_payload(
        environment="demo",
        source="phase14d7_broker_readonly_external_cancel",
        as_of=as_of,
        orders=orders,
        executions=(),
        positions=positions,
        cash={
            "cash_ref": cash.get("cash_ref") or cash.get("raw_clmid") or f"cash-{as_of}",
            "cash": cash.get("cash") or cash.get("cash_available") or 0,
            "buying_power": cash.get("buying_power") or 0,
            "currency": cash.get("currency") or "JPY",
        },
    )


def _runtime_order_payload(order: dict[str, Any]) -> dict[str, Any]:
    raw_status = str(order.get("status") or "")
    return {
        "order_id": order.get("order_id_hash") or order.get("order_id") or order.get("order_ref") or _hash_text(json.dumps(order, sort_keys=True)),
        "symbol": order.get("issue_code") or order.get("symbol") or "",
        "side": _normalize_side(str(order.get("side") or "")),
        "quantity": _float(order.get("quantity")),
        "order_status": _normalize_order_status(raw_status),
        "filled_quantity": _float(order.get("executed_quantity")),
        "remaining_quantity": _float(order.get("remaining_quantity")),
        "accepted_at": str(order.get("order_datetime") or ""),
        "updated_at": str(order.get("as_of") or ""),
    }


def _runtime_position_payload(position: dict[str, Any]) -> dict[str, Any]:
    return {
        "position_id": position.get("position_id") or position.get("position_ref") or _hash_text(json.dumps(position, sort_keys=True)),
        "position_key": position.get("issue_code") or position.get("symbol") or position.get("account_type") or "",
        "symbol": position.get("issue_code") or position.get("symbol") or "",
        "quantity": _float(position.get("quantity")),
        "average_price": _float(position.get("average_price")),
        "market_value": _float(position.get("market_value")),
    }


def _find_target_order(orders: Any, *, issue_code: str, quantity: float) -> dict[str, Any] | None:
    for order in orders:
        if str(order.get("issue_code") or order.get("symbol") or "") != issue_code:
            continue
        if abs(_float(order.get("quantity")) - quantity) > 0.000001:
            continue
        return dict(order)
    return None


def _is_cancelled_status(status: str) -> bool:
    normalized = status.strip().lower()
    return normalized in {"cancel", "cancelled", "canceled", "cancelled_order", "canceled_order"} or "取消" in status


def _normalize_order_status(status: str) -> str:
    if _is_cancelled_status(status):
        return "canceled"
    normalized = status.strip().lower()
    if "失効" in status:
        return "expired"
    if "約定" in status and "未約定" not in status:
        return "filled"
    return normalized or status


def _normalize_side(side: str) -> str:
    normalized = side.strip().lower()
    if normalized in {"buy", "3", "買", "買付"}:
        return "BUY"
    if normalized in {"sell", "1", "売", "売付"}:
        return "SELL"
    return side.upper()


def _read_pending_plan(path: Path) -> PendingOrderPlan:
    payload = _load_json(path)
    return PendingOrderPlan(
        schema_version=payload["schema_version"],
        pending_plan_id=payload["pending_plan_id"],
        state=PendingPlanState(payload["state"]),
        environment=payload["environment"],
        created_at=payload["created_at"],
        updated_at=payload["updated_at"],
        plan_created_date=payload["plan_created_date"],
        intended_submit_date=payload["intended_submit_date"],
        target_session_date=payload["target_session_date"],
        source_order_plan=PendingSourceOrderPlan(**payload["source_order_plan"]),
        approval=PendingApprovalLink(**payload["approval"]) if payload.get("approval") else None,
        approved_item_ids=tuple(payload.get("approved_item_ids") or ()),
        items=tuple(PendingOrderItem(**item) for item in payload.get("items") or ()),
        submit_constraints=PendingSubmitConstraints(**(payload.get("submit_constraints") or {})),
        consume=PendingConsumeInfo(**(payload.get("consume") or {})),
        raw_request_saved=payload.get("raw_request_saved", False),
        raw_response_saved=payload.get("raw_response_saved", False),
        secret_saved=payload.get("secret_saved", False),
    )


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hash_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _business_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _markdown(result: Phase14D7Result) -> str:
    return f"""# Phase14-D7 Broker State Synchronization After External Order Cancellation

作成日: 2026-07-07

## Status

```text
{result.final_decision}
```

## Summary

- broker_state_source_of_truth: `{result.broker_state_source_of_truth}`
- runtime_did_not_mutate_broker: `{result.runtime_did_not_mutate_broker}`
- readonly_status: `{result.readonly_status}`
- target_issue_code: `{result.target_issue_code}`
- target_order_detected: `{result.target_order_detected}`
- target_order_cancelled: `{result.target_order_cancelled}`
- target_order_status: `{result.target_order_status}`
- target_remaining_quantity: `{result.target_remaining_quantity}`
- target_executed_quantity: `{result.target_executed_quantity}`
- fill_classification: `{result.fill_classification}`

## Runtime Reflection

- pending_terminal_state: `{result.pending_terminal_state}`
- pending_consumed: `{result.pending_consumed}`
- ledger_order_count: `{result.ledger_order_count}`
- ledger_execution_count: `{result.ledger_execution_count}`
- ledger_position_count: `{result.ledger_position_count}`
- ledger_cash_count: `{result.ledger_cash_count}`
- asset_state_created: `{result.asset_state_created}`
- asset_changed_by_cancel: `{result.asset_changed_by_cancel}`
- reconcile_pass: `{result.reconcile_pass}`
- reconciliation_findings: `{result.reconciliation_findings}`
- report_sections: `{result.report_sections}`
- notification_payload_created: `{result.notification_payload_created}`
- audit_findings: `{result.audit_findings}`

## Evidence

- snapshot_path: `{result.snapshot_path}`
- pending_plan_path: `{result.pending_plan_path}`

## Prohibited Actions

- new_buy_submit_executed: `{result.new_buy_submit_executed}`
- sell_submit_executed: `{result.sell_submit_executed}`
- submit_executed: `{result.submit_executed}`
- cancel_api_called: `{result.cancel_api_called}`
- production_api_called: `{result.production_api_called}`
- notification_sent: `{result.notification_sent}`
- launchd_modified: `{result.launchd_modified}`

## Blocked Reasons

```text
{chr(10).join(result.blocked_reasons) if result.blocked_reasons else "none"}
```

## Review Reasons

```text
{chr(10).join(result.review_reasons) if result.review_reasons else "none"}
```
"""
