"""Phase14-D15 pure Runtime v2 Demo SELL single-order guarded test."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

from ai_fund_lab_v2.broker.settings import DEMO_BASE_URL, PROD_BASE_URL, BrokerSettings, load_broker_settings
from ai_fund_lab_v2.broker.tachibana_broker_snapshot import run_tachibana_broker_snapshot
from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.asset.builder import build_current_asset_state
from ai_fund_lab_v2.runtime_v2.audit.auditor import run_audit
from ai_fund_lab_v2.runtime_v2.broker_readonly.models import BrokerOrderSnapshot
from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import normalize_broker_readonly_payload
from ai_fund_lab_v2.runtime_v2.execution.ledger_projection import (
    project_cash_to_ledger_record,
    project_order_to_ledger_record,
    project_position_to_ledger_record,
)
from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerEventRecord
from ai_fund_lab_v2.runtime_v2.notification.payload import build_notification_payload
from ai_fund_lab_v2.runtime_v2.pending.consume import consume_pending_plan
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingOrderPlan, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.reconcile.reconciler import run_reconciliation
from ai_fund_lab_v2.runtime_v2.report.builder import build_runtime_report
from ai_fund_lab_v2.runtime_v2.report.models import ReportBuildInput
from ai_fund_lab_v2.runtime_v2.submit.guards import run_submit_preflight
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand, RuntimeV2SubmitResult


class RuntimeV2SubmitAdapter(Protocol):
    def preflight(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        ...

    def submit(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        ...


@dataclass(frozen=True)
class Phase14D15Result:
    final_decision: str
    environment: str
    base_url_is_demo: bool
    base_url_is_production: bool
    symbol: str
    side: str
    quantity: float
    account_type: str
    before_position_quantity: float
    before_available_quantity: float
    after_position_quantity: float
    position_decreased_or_disappeared: bool
    cash_before: float | None
    cash_after: float | None
    buying_power_before: float | None
    buying_power_after: float | None
    cash_or_buying_power_updated: bool
    runtime_v2_pure_submit_path: bool
    legacy_order_command_submit_authority_used: bool
    legacy_runtime_mode_submit_authority_used: bool
    production_order_executed: bool
    production_broker_api_write_executed: bool
    buy_submit_executed: bool
    sell_submit_executed: bool
    demo_submit_executed: bool
    demo_order_accepted: bool
    broker_api_called: bool
    post_send_unknown: bool
    readonly_before_status: str
    readonly_after_status: str
    readonly_before_health_ok: bool
    readonly_after_health_ok: bool
    submit_preflight_status: str
    adapter_preflight_status: str
    submit_status: str
    submit_reason: str
    pending_plan_path: str
    approval_artifact_path: str
    broker_response_path: str
    readonly_before_snapshot_path: str
    readonly_after_snapshot_path: str
    ledger_order_count: int
    ledger_execution_count: int
    ledger_event_count: int
    ledger_position_count: int
    ledger_cash_count: int
    asset_state_created: bool
    order_status_readonly_confirmed: bool
    target_order_status: str
    target_order_filled_quantity: float
    target_order_remaining_quantity: float
    sell_fill_classification: str
    orderlist_position_cash_evidence_used: bool
    asset_built_from_broker_order_only: bool
    reconcile_pass: bool
    reconciliation_findings: int
    report_sections: int
    notification_payload_created: bool
    notification_sent: bool
    audit_pass: bool
    audit_findings: int
    launchd_or_plist_modified: bool
    blocked_reasons: tuple[str, ...] = ()
    review_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_phase14d15_demo_sell_single_order_guarded_test(
    *,
    root: Path,
    docs_report_path: Path,
    json_report_path: Path,
    adapter: RuntimeV2SubmitAdapter,
    settings: BrokerSettings | None = None,
    symbol: str = "7203",
    quantity: float = 100.0,
    estimated_price: float = 2941.0,
    max_order_amount: float = 500000.0,
    run_submit: bool = True,
) -> Phase14D15Result:
    settings = settings or load_broker_settings()
    root.mkdir(parents=True, exist_ok=True)
    docs_report_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    blocked_reasons: list[str] = []
    review_reasons: list[str] = []
    base_url = settings.base_url.rstrip("/")
    base_url_is_demo = base_url == DEMO_BASE_URL
    base_url_is_production = base_url == PROD_BASE_URL

    if settings.environment != "demo":
        blocked_reasons.append("environment guard failure")
    if not base_url_is_demo or base_url_is_production:
        blocked_reasons.append("demo-only guard failure")
    if symbol != "7203":
        blocked_reasons.append("Phase14-D15 target must be 7203")
    if quantity != 100.0:
        blocked_reasons.append("Phase14-D15 SELL quantity must be exactly 100")
    if symbol.startswith("9"):
        blocked_reasons.append("9000-series symbols excluded")

    before_snapshot_path = root / "broker_readonly_before" / "tachibana_demo_snapshot.json"
    after_snapshot_path = root / "broker_readonly_after" / "tachibana_demo_snapshot.json"
    before_status = _readonly_snapshot(
        settings=settings,
        report_path=root / "broker_readonly_before" / "snapshot_report.json",
        snapshot_path=before_snapshot_path,
        symbol=symbol,
        source="phase14d15_readonly_before",
    )
    before_payload = _load_json(before_snapshot_path) if before_snapshot_path.exists() else {}
    before_health_ok = _readonly_health_ok(before_payload)
    if not before_health_ok:
        blocked_reasons.append(f"readonly before health is not sufficient: {before_status}")
    before_position_quantity, before_available_quantity = _target_raw_position_quantities(before_payload, symbol=symbol)
    if before_position_quantity < quantity:
        blocked_reasons.append("7203 position quantity is below planned SELL quantity")
    if before_available_quantity < quantity:
        blocked_reasons.append("7203 available_quantity is below planned SELL quantity")

    pending_plan, approval = _build_pending_and_approval(
        symbol=symbol,
        quantity=quantity,
        estimated_price=estimated_price,
    )
    pending_plan_path = root / "pending_order_plan" / "pending_order_plan.json"
    approval_artifact_path = root / "approval_artifact" / "approval_phase14d15_demo_sell.json"
    _write_json(pending_plan_path, _jsonable(pending_plan))
    _write_json(approval_artifact_path, _jsonable(approval))
    preflight = run_submit_preflight(
        pending_plan=pending_plan,
        approval_artifact=approval,
        approved_item_id=pending_plan.approved_item_ids[0],
        existing_order_dedup_keys=set(),
        environment=settings.environment,
        base_url_is_demo=base_url_is_demo,
        base_url_is_production=base_url_is_production,
        live_order_allowed=True,
        broker_position_quantity=before_position_quantity,
        broker_available_quantity=before_available_quantity,
    )
    command = preflight.command
    adapter_preflight_result: RuntimeV2SubmitResult | None = None
    submit_result: RuntimeV2SubmitResult | None = None
    broker_response_path = root / "submit_response" / "runtime_v2_submit_result.json"
    if not preflight.allowed or command is None:
        blocked_reasons.append(f"submit preflight blocked: {preflight.reason}")
    elif not blocked_reasons:
        adapter_preflight_result = adapter.preflight(command)
        if adapter_preflight_result.status != "DRY_RUN_READY":
            blocked_reasons.append(f"adapter preflight blocked: {adapter_preflight_result.reason}")
    if not blocked_reasons and run_submit and command is not None:
        submit_result = adapter.submit(command)
        _write_json(broker_response_path, _jsonable(submit_result))
        if submit_result.post_send_unknown:
            review_reasons.append("POST_SEND_UNKNOWN; automatic resubmit forbidden")
        elif submit_result.blocked:
            blocked_reasons.append(f"submit blocked: {submit_result.reason}")
        elif not submit_result.accepted:
            review_reasons.append(f"submit not accepted: {submit_result.status}:{submit_result.reason}")
    elif not run_submit:
        blocked_reasons.append("run_submit disabled")

    after_status = "NOT_EXECUTED"
    after_payload: dict[str, Any] = {}
    if submit_result and submit_result.broker_api_called:
        after_status = _readonly_snapshot(
            settings=settings,
            report_path=root / "broker_readonly_after" / "snapshot_report.json",
            snapshot_path=after_snapshot_path,
            symbol=symbol,
            source="phase14d15_readonly_after",
        )
        after_payload = _load_json(after_snapshot_path) if after_snapshot_path.exists() else {}
        if not _readonly_health_ok(after_payload):
            review_reasons.append(f"readonly after health is not sufficient: {after_status}")
    else:
        after_payload = before_payload
    after_health_ok = _readonly_health_ok(after_payload)

    before_bundle = _bundle_from_payload(before_payload, source="phase14d15_demo_broker_readonly_before")
    after_bundle = _bundle_from_payload(after_payload, source="phase14d15_demo_broker_readonly_after")
    after_position_quantity, _after_available_quantity = _target_raw_position_quantities(after_payload, symbol=symbol)
    cash_before = before_bundle.cash.cash if before_bundle.cash else None
    cash_after = after_bundle.cash.cash if after_bundle.cash else None
    buying_power_before = before_bundle.cash.buying_power if before_bundle.cash else None
    buying_power_after = after_bundle.cash.buying_power if after_bundle.cash else None
    target_order = _find_target_sell_order(after_bundle.orders, symbol=symbol, quantity=quantity)
    position_decreased_or_disappeared = after_position_quantity <= before_position_quantity - quantity
    cash_or_buying_power_updated = (
        (cash_before is not None and cash_after is not None and cash_after != cash_before)
        or (
            buying_power_before is not None
            and buying_power_after is not None
            and buying_power_after != buying_power_before
        )
    )
    target_order_full_fill = bool(
        target_order
        and target_order.filled_quantity >= quantity
        and abs(target_order.remaining_quantity) < 0.000001
    )
    orderlist_position_cash_evidence_used = bool(
        target_order_full_fill
        and position_decreased_or_disappeared
        and cash_or_buying_power_updated
        and after_bundle.cash is not None
    )
    if target_order is None and submit_result and submit_result.broker_api_called:
        review_reasons.append("SELL order not found in CLMOrderList")
    if target_order and not target_order_full_fill:
        review_reasons.append("SELL order is not fully filled in CLMOrderList")
    if target_order_full_fill and not position_decreased_or_disappeared:
        review_reasons.append("SELL fill does not have corroborating Position decrease/disappearance")
    if target_order_full_fill and not cash_or_buying_power_updated:
        review_reasons.append("SELL fill does not have corroborating Cash/Buying Power update")

    ledger_orders = tuple(project_order_to_ledger_record(order) for order in after_bundle.orders)
    ledger_positions = tuple(project_position_to_ledger_record(position) for position in after_bundle.positions)
    ledger_cash = (project_cash_to_ledger_record(after_bundle.cash),) if after_bundle.cash else ()
    ledger_events = (
        _sell_execution_equivalent_event(
            target_order,
            symbol=symbol,
            quantity=quantity,
            allowed=orderlist_position_cash_evidence_used,
        )
        if target_order is not None
        else ()
    )
    if submit_result and submit_result.broker_api_called and ledger_orders:
        pending_plan = replace(pending_plan, state=PendingPlanState.SUBMITTED, updated_at=_now())
        pending_plan = consume_pending_plan(
            pending_plan,
            consume_reason="phase14d15 pure runtime v2 demo sell submit attempted",
            submitted_order_ids=tuple(order.order_ref_hash for order in after_bundle.orders if order.side == "SELL"),
            ledger_order_record_ids=tuple(order.record_id for order in ledger_orders),
        )
        _write_json(pending_plan_path, _jsonable(pending_plan))
    asset_state = build_current_asset_state(
        environment="demo",
        positions=ledger_positions,
        cash_records=ledger_cash,
        source="phase14d15_orderlist_position_cash_reflection",
        as_of=_business_date(),
    )
    reconciliation = run_reconciliation(
        mode="demo",
        environment="demo",
        business_date=_business_date(),
        pending_plan=pending_plan,
        ledger_orders=ledger_orders,
        ledger_executions=(),
        broker_orders=after_bundle.orders,
        broker_executions=(),
        broker_positions=after_bundle.positions,
        broker_cash=after_bundle.cash,
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
            broker_orders=after_bundle.orders,
            broker_executions=(),
            broker_positions=after_bundle.positions,
            broker_cash=after_bundle.cash,
            approval_artifact=approval,
            reconciliation_result=reconciliation,
            review_events=ledger_events,
        )
    )
    notification_payload = build_notification_payload(report=report, channel="phase14d15_payload_only")
    audit = run_audit(
        mode="demo",
        environment="demo",
        business_date=_business_date(),
        report=report,
        notification_payload=notification_payload,
        reconciliation_result=reconciliation,
        asset_state=asset_state,
    )
    if reconciliation.findings:
        review_reasons.append(f"reconciliation findings={len(reconciliation.findings)}")
    if audit.findings:
        review_reasons.append(f"audit findings={len(audit.findings)}")

    _write_json(root / "ledger_events" / "phase14d15_sell_events.json", {"events": _jsonable(ledger_events)})
    _write_json(root / "asset_state" / "asset_state.json", _jsonable(asset_state))
    _write_json(root / "report" / "runtime_report.json", _jsonable(report))
    _write_json(root / "notification" / "notification_payload.json", _jsonable(notification_payload))
    _write_json(root / "audit" / "audit_result.json", _jsonable(audit))

    final_decision = "PHASE14D15_DEMO_SELL_SINGLE_ORDER_PASS"
    if (
        blocked_reasons
        or review_reasons
        or not (submit_result and submit_result.accepted)
        or not target_order
        or not orderlist_position_cash_evidence_used
        or reconciliation.findings
        or audit.findings
    ):
        final_decision = "PHASE14D15_REVIEW_REQUIRED"

    result = Phase14D15Result(
        final_decision=final_decision,
        environment=settings.environment,
        base_url_is_demo=base_url_is_demo,
        base_url_is_production=base_url_is_production,
        symbol=symbol,
        side="SELL",
        quantity=quantity,
        account_type="cash",
        before_position_quantity=before_position_quantity,
        before_available_quantity=before_available_quantity,
        after_position_quantity=after_position_quantity,
        position_decreased_or_disappeared=position_decreased_or_disappeared,
        cash_before=cash_before,
        cash_after=cash_after,
        buying_power_before=buying_power_before,
        buying_power_after=buying_power_after,
        cash_or_buying_power_updated=cash_or_buying_power_updated,
        runtime_v2_pure_submit_path=True,
        legacy_order_command_submit_authority_used=False,
        legacy_runtime_mode_submit_authority_used=False,
        production_order_executed=False,
        production_broker_api_write_executed=False,
        buy_submit_executed=False,
        sell_submit_executed=bool(submit_result and submit_result.submitted),
        demo_submit_executed=bool(submit_result and submit_result.submitted),
        demo_order_accepted=bool(submit_result and submit_result.accepted),
        broker_api_called=bool(submit_result and submit_result.broker_api_called),
        post_send_unknown=bool(submit_result and submit_result.post_send_unknown),
        readonly_before_status=before_status,
        readonly_after_status=after_status,
        readonly_before_health_ok=before_health_ok,
        readonly_after_health_ok=after_health_ok,
        submit_preflight_status="PASS" if preflight.allowed else "BLOCKED",
        adapter_preflight_status=adapter_preflight_result.status if adapter_preflight_result else "NOT_EXECUTED",
        submit_status=submit_result.status if submit_result else "NOT_EXECUTED",
        submit_reason=submit_result.reason if submit_result else "",
        pending_plan_path=str(pending_plan_path),
        approval_artifact_path=str(approval_artifact_path),
        broker_response_path=str(broker_response_path),
        readonly_before_snapshot_path=str(before_snapshot_path),
        readonly_after_snapshot_path=str(after_snapshot_path),
        ledger_order_count=len(ledger_orders),
        ledger_execution_count=0,
        ledger_event_count=len(ledger_events),
        ledger_position_count=len(ledger_positions),
        ledger_cash_count=len(ledger_cash),
        asset_state_created=asset_state is not None,
        order_status_readonly_confirmed=target_order is not None,
        target_order_status=target_order.order_status if target_order else "",
        target_order_filled_quantity=target_order.filled_quantity if target_order else 0.0,
        target_order_remaining_quantity=target_order.remaining_quantity if target_order else 0.0,
        sell_fill_classification="ORDER_LIST_POSITION_CASH_DERIVED_FULL_SELL"
        if orderlist_position_cash_evidence_used
        else "REVIEW_REQUIRED",
        orderlist_position_cash_evidence_used=orderlist_position_cash_evidence_used,
        asset_built_from_broker_order_only=False,
        reconcile_pass=not reconciliation.findings,
        reconciliation_findings=len(reconciliation.findings),
        report_sections=len(report.sections),
        notification_payload_created=notification_payload is not None,
        notification_sent=False,
        audit_pass=not audit.findings,
        audit_findings=len(audit.findings),
        launchd_or_plist_modified=False,
        blocked_reasons=tuple(blocked_reasons),
        review_reasons=tuple(dict.fromkeys(review_reasons)),
    )
    _write_json(json_report_path, result.to_dict())
    docs_report_path.write_text(_markdown_report(result), encoding="utf-8")
    return result


def _readonly_snapshot(*, settings: BrokerSettings, report_path: Path, snapshot_path: Path, symbol: str, source: str) -> str:
    result = run_tachibana_broker_snapshot(
        reports_dir=report_path.parent,
        run_enabled=True,
        report_filename=report_path.name,
        snapshot_path=snapshot_path,
        source=source,
        settings=settings,
        symbols=(symbol,),
        include_quotes=True,
    )
    return result.status


def _build_pending_and_approval(*, symbol: str, quantity: float, estimated_price: float) -> tuple[PendingOrderPlan, ApprovalArtifact]:
    item = PendingOrderItem(
        pending_item_id=f"phase14d15-sell-{symbol}-{int(quantity)}",
        symbol=symbol,
        side="SELL",
        quantity=quantity,
        order_type="MARKET",
        estimated_price=estimated_price,
        estimated_amount=quantity * estimated_price,
        approved=False,
        state="PENDING_APPROVAL",
    )
    plan = promote_order_plan_to_pending(
        order_plan_id=f"phase14d15-demo-sell-{symbol}",
        source_order_plan_path="order_plan/phase14d15-demo-sell.json",
        source_order_plan_hash=_hash_text(f"phase14d15-demo-sell-{symbol}"),
        environment="demo",
        plan_created_date=_now(),
        intended_submit_date=_business_date(),
        target_session_date=_business_date(),
        items=(item,),
    )
    plan_hash = _hash_json(_jsonable(plan))
    approval = ApprovalArtifact(
        approval_id="approval_phase14d15_demo_sell",
        approval_request_id="approval_request_phase14d15_demo_sell",
        pending_plan_id=plan.pending_plan_id,
        order_plan_id=plan.source_order_plan.order_plan_id,
        status=ApprovalStatus.APPROVED,
        approved_item_ids=(item.pending_item_id,),
        rejected_item_ids=(),
        approval_hash=plan_hash,
        approved_at=_now(),
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
        review_required=False,
        reason=f"Phase14-D15 manual approval for pure Runtime v2 Demo SELL {symbol}",
        approved_order_conditions={
            item.pending_item_id: {
                "order_type": item.order_type,
                "target_session": plan.target_session_date,
                "quantity": item.quantity,
                "side": item.side,
                "issue_code": item.symbol,
                "limit_price": None,
                "time_in_force": "DAY",
                "price_condition": item.order_type,
            }
        },
    )
    return link_approval_to_pending(pending_plan=plan, approval_artifact=approval), approval


def _bundle_from_payload(payload: dict[str, Any], *, source: str):
    return normalize_broker_readonly_payload(
        environment="demo",
        source=source,
        as_of=str(payload.get("generated_at") or _business_date()),
        orders=tuple(_runtime_order_payload(order) for order in payload.get("orders") or ()),
        executions=tuple(_runtime_execution_payload(execution) for execution in payload.get("executions") or ()),
        positions=tuple(_runtime_position_payload(position) for position in payload.get("positions") or ()),
        cash=_runtime_cash_payload(payload.get("buying_power") or payload.get("account_summary") or {}),
    )


def _runtime_order_payload(order: dict[str, Any]) -> dict[str, Any]:
    status = str(order.get("status") or order.get("order_status") or "")
    return {
        "order_id": order.get("order_id_hash") or order.get("order_id") or order.get("order_ref") or _hash_text(json.dumps(order, sort_keys=True)),
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
        "execution_id": execution.get("execution_id") or execution.get("execution_ref") or _hash_text(json.dumps(execution, sort_keys=True)),
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
        "position_id": position.get("position_id") or position.get("position_ref") or _hash_text(json.dumps(position, sort_keys=True)),
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


def _find_target_sell_order(orders: tuple[BrokerOrderSnapshot, ...], *, symbol: str, quantity: float) -> BrokerOrderSnapshot | None:
    candidates = [
        order
        for order in orders
        if order.symbol == symbol
        and order.side.upper() == "SELL"
        and abs(order.quantity - quantity) < 0.000001
    ]
    filled = [order for order in candidates if order.filled_quantity >= quantity and abs(order.remaining_quantity) < 0.000001]
    if filled:
        return filled[0]
    return candidates[0] if candidates else None


def _target_raw_position_quantities(payload: dict[str, Any], *, symbol: str) -> tuple[float, float]:
    candidates = [
        position
        for position in payload.get("positions") or ()
        if str(position.get("issue_code") or position.get("symbol") or "") == symbol
    ]
    if not candidates:
        return 0.0, 0.0
    position = candidates[0]
    quantity = _float(position.get("quantity"))
    available = _float(position.get("available_quantity"))
    return quantity, available


def _sell_execution_equivalent_event(
    order: BrokerOrderSnapshot,
    *,
    symbol: str,
    quantity: float,
    allowed: bool,
) -> tuple[LedgerEventRecord, ...]:
    message = "SELL OrderList/Position/Cash evidence"
    if allowed:
        message += " accepted as execution-equivalent evidence"
    else:
        message += " requires review"
    return (
        LedgerEventRecord(
            record_id=f"ledger-event-phase14d15-sell-{symbol}",
            record_type="event",
            schema_version="1",
            environment="demo",
            source="phase14d15_orderlist_position_cash_reflection",
            created_at=order.as_of,
            dedup_key=f"phase14d15:{symbol}:sell:{int(quantity)}:{order.order_ref_hash}",
            review_required=not allowed,
            production_equivalent=True,
            event_id=f"phase14d15:{symbol}:sell_order_list_position_cash",
            event_type="sell_execution_equivalent",
            severity="INFO" if allowed else "REVIEW_REQUIRED",
            message=message,
            related_id=order.order_ref_hash,
        ),
    )


def _readonly_health_ok(payload: dict[str, Any]) -> bool:
    health = payload.get("health") or {}
    return all(
        str(((health.get(key) or {}).get("status") or "")) == "PASS"
        for key in ("orders", "positions", "account")
    )


def _normalize_order_status(status: str) -> str:
    if "取消" in status:
        return "canceled"
    if "失効" in status:
        return "expired"
    if "未約定" in status:
        return "open"
    if "約定" in status:
        return "filled"
    return status.strip().lower() or status


def _normalize_side(side: str) -> str:
    normalized = side.strip().lower()
    if normalized in {"buy", "3", "買", "買付"}:
        return "BUY"
    if normalized in {"sell", "1", "売", "売付"}:
        return "SELL"
    return side.upper()


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if hasattr(value, "value"):
        return value.value
    return value


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hash_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_json(payload: Any) -> str:
    return _hash_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _business_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _markdown_report(result: Phase14D15Result) -> str:
    return f"""# Phase14-D15 Demo SELL Single-Order Guarded Test

作成日: 2026-07-07

## Status

```text
{result.final_decision}
```

## Summary

- runtime_v2_pure_submit_path: `{result.runtime_v2_pure_submit_path}`
- legacy_order_command_submit_authority_used: `{result.legacy_order_command_submit_authority_used}`
- legacy_runtime_mode_submit_authority_used: `{result.legacy_runtime_mode_submit_authority_used}`
- environment: `{result.environment}`
- base_url_is_demo: `{result.base_url_is_demo}`
- base_url_is_production: `{result.base_url_is_production}`
- symbol: `{result.symbol}`
- side: `{result.side}`
- quantity: `{result.quantity}`
- account_type: `{result.account_type}`
- demo_submit_executed: `{result.demo_submit_executed}`
- sell_submit_executed: `{result.sell_submit_executed}`
- demo_order_accepted: `{result.demo_order_accepted}`
- broker_api_called: `{result.broker_api_called}`
- post_send_unknown: `{result.post_send_unknown}`
- submit_status: `{result.submit_status}`
- sell_fill_classification: `{result.sell_fill_classification}`

## Guard Evidence

- before_position_quantity: `{result.before_position_quantity}`
- before_available_quantity: `{result.before_available_quantity}`
- submit_preflight_status: `{result.submit_preflight_status}`
- adapter_preflight_status: `{result.adapter_preflight_status}`
- readonly_before_status: `{result.readonly_before_status}`
- readonly_before_health_ok: `{result.readonly_before_health_ok}`
- readonly_after_status: `{result.readonly_after_status}`
- readonly_after_health_ok: `{result.readonly_after_health_ok}`

## Broker Reflection

- order_status_readonly_confirmed: `{result.order_status_readonly_confirmed}`
- target_order_status: `{result.target_order_status}`
- target_order_filled_quantity: `{result.target_order_filled_quantity}`
- target_order_remaining_quantity: `{result.target_order_remaining_quantity}`
- after_position_quantity: `{result.after_position_quantity}`
- position_decreased_or_disappeared: `{result.position_decreased_or_disappeared}`
- cash_before: `{result.cash_before}`
- cash_after: `{result.cash_after}`
- buying_power_before: `{result.buying_power_before}`
- buying_power_after: `{result.buying_power_after}`
- cash_or_buying_power_updated: `{result.cash_or_buying_power_updated}`
- orderlist_position_cash_evidence_used: `{result.orderlist_position_cash_evidence_used}`
- asset_built_from_broker_order_only: `{result.asset_built_from_broker_order_only}`

## Runtime v2 Outputs

- pending_plan_path: `{result.pending_plan_path}`
- approval_artifact_path: `{result.approval_artifact_path}`
- broker_response_path: `{result.broker_response_path}`
- readonly_before_snapshot_path: `{result.readonly_before_snapshot_path}`
- readonly_after_snapshot_path: `{result.readonly_after_snapshot_path}`
- ledger_order_count: `{result.ledger_order_count}`
- ledger_execution_count: `{result.ledger_execution_count}`
- ledger_event_count: `{result.ledger_event_count}`
- ledger_position_count: `{result.ledger_position_count}`
- ledger_cash_count: `{result.ledger_cash_count}`
- asset_state_created: `{result.asset_state_created}`
- reconcile_pass: `{result.reconcile_pass}`
- reconciliation_findings: `{result.reconciliation_findings}`
- report_sections: `{result.report_sections}`
- notification_payload_created: `{result.notification_payload_created}`
- notification_sent: `{result.notification_sent}`
- audit_pass: `{result.audit_pass}`
- audit_findings: `{result.audit_findings}`

## Prohibited Actions

- buy_submit_executed: `{result.buy_submit_executed}`
- production_order_executed: `{result.production_order_executed}`
- production_broker_api_write_executed: `{result.production_broker_api_write_executed}`
- notification_sent: `{result.notification_sent}`
- launchd_or_plist_modified: `{result.launchd_or_plist_modified}`

## Blocked Reasons

```text
{chr(10).join(result.blocked_reasons) if result.blocked_reasons else "none"}
```

## Review Reasons

```text
{chr(10).join(result.review_reasons) if result.review_reasons else "none"}
```

## Final Decision

```text
{result.final_decision}
```
"""
