"""Phase14-D8 pure Runtime v2 Demo BUY retest after external cancel sync."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

from ai_fund_lab_v2.broker.phase14d7_external_cancel_sync import _is_cancelled_status
from ai_fund_lab_v2.broker.settings import DEMO_BASE_URL, PROD_BASE_URL, BrokerSettings, load_broker_settings
from ai_fund_lab_v2.broker.tachibana_broker_snapshot import run_tachibana_broker_snapshot
from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.asset.builder import build_current_asset_state
from ai_fund_lab_v2.runtime_v2.audit.auditor import run_audit
from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import normalize_broker_readonly_payload
from ai_fund_lab_v2.runtime_v2.execution.fill_classifier import classify_fill
from ai_fund_lab_v2.runtime_v2.execution.ledger_projection import (
    project_cash_to_ledger_record,
    project_execution_to_ledger_record,
    project_order_to_ledger_record,
    project_position_to_ledger_record,
)
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
class Phase14D8Result:
    final_decision: str
    environment: str
    base_url_is_demo: bool
    base_url_is_production: bool
    d7_sync_pass: bool
    existing_9432_cancelled: bool
    symbol: str
    side: str
    quantity: float
    runtime_v2_pure_submit_path: bool
    legacy_order_command_submit_authority_used: bool
    legacy_runtime_mode_submit_authority_used: bool
    production_order_executed: bool
    production_broker_api_write_executed: bool
    sell_submit_executed: bool
    demo_submit_executed: bool
    demo_order_accepted: bool
    broker_api_called: bool
    post_send_unknown: bool
    readonly_before_status: str
    readonly_after_status: str
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
    ledger_position_count: int
    ledger_cash_count: int
    asset_state_created: bool
    order_status_readonly_confirmed: bool
    execution_state_classification: str
    fill_classifications: tuple[str, ...]
    reconciliation_findings: int
    report_sections: int
    notification_payload_created: bool
    audit_findings: int
    notification_sent: bool
    launchd_or_plist_modified: bool
    blocked_reasons: tuple[str, ...] = ()
    review_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_phase14d8_pure_runtime_v2_demo_buy_retest(
    *,
    root: Path,
    docs_report_path: Path,
    json_report_path: Path,
    adapter: RuntimeV2SubmitAdapter,
    settings: BrokerSettings | None = None,
    symbol: str = "7203",
    quantity: float = 100.0,
    estimated_price: float = 3000.0,
    max_order_amount: float = 500000.0,
    d7_report_path: Path = Path("reports/phase_reports/phase14_d7_external_cancel_sync.json"),
    run_submit: bool = True,
) -> Phase14D8Result:
    settings = settings or load_broker_settings()
    root.mkdir(parents=True, exist_ok=True)
    docs_report_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    blocked_reasons: list[str] = []
    review_reasons: list[str] = []
    base_url = settings.base_url.rstrip("/")
    base_url_is_demo = base_url == DEMO_BASE_URL
    base_url_is_production = base_url == PROD_BASE_URL
    d7 = _load_json(d7_report_path) if d7_report_path.exists() else {}
    d7_sync_pass = d7.get("final_decision") == "PHASE14D7_BROKER_STATE_SYNC_PASS"
    existing_9432_cancelled = bool(d7.get("target_order_cancelled") and d7.get("pending_consumed"))
    if not d7_sync_pass:
        blocked_reasons.append("Phase14-D7 sync pass is required")
    if not existing_9432_cancelled:
        blocked_reasons.append("existing 9432 order is not resolved")
    if settings.environment != "demo":
        blocked_reasons.append("environment guard failure")
    if not base_url_is_demo or base_url_is_production:
        blocked_reasons.append("demo-only guard failure")
    if symbol.startswith("9"):
        blocked_reasons.append("9000-series symbols excluded")
    if quantity != 100.0:
        blocked_reasons.append("BUY order quantity must be exactly one minimum unit")

    before_snapshot_path = root / "broker_readonly_before" / "tachibana_demo_snapshot.json"
    after_snapshot_path = root / "broker_readonly_after" / "tachibana_demo_snapshot.json"
    before_status = _readonly_snapshot(
        settings=settings,
        report_path=root / "broker_readonly_before" / "snapshot_report.json",
        snapshot_path=before_snapshot_path,
        symbol=symbol,
        source="phase14d8_readonly_before",
    )
    before_payload = _load_json(before_snapshot_path) if before_snapshot_path.exists() else {}
    unresolved = _unresolved_9432_open_order(before_payload)
    if unresolved:
        blocked_reasons.append("existing 9432 order is still open")
    if before_status not in {"PASS", "PASS_WITH_WARNINGS"} and not _orders_health_pass(before_payload):
        blocked_reasons.append(f"readonly before status={before_status}")

    pending_plan, approval = _build_pending_and_approval(symbol=symbol, quantity=quantity, estimated_price=estimated_price)
    pending_plan_path = root / "pending_order_plan" / "pending_order_plan.json"
    approval_artifact_path = root / "approval_artifact" / "approval_phase14d8_demo_buy.json"
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
    if submit_result and submit_result.broker_api_called:
        after_status = _readonly_snapshot(
            settings=settings,
            report_path=root / "broker_readonly_after" / "snapshot_report.json",
            snapshot_path=after_snapshot_path,
            symbol=symbol,
            source="phase14d8_readonly_after",
        )
        after_payload = _load_json(after_snapshot_path) if after_snapshot_path.exists() else {}
        if after_status not in {"PASS", "PASS_WITH_WARNINGS"} and not _orders_health_pass(after_payload):
            review_reasons.append(f"readonly after status={after_status}")
    bundle = _bundle_from_snapshot(after_snapshot_path if after_snapshot_path.exists() else before_snapshot_path)
    broker_orders = bundle.orders
    broker_executions = bundle.executions
    broker_positions = bundle.positions
    broker_cash = bundle.cash
    ledger_orders = tuple(project_order_to_ledger_record(order) for order in broker_orders)
    ledger_executions = tuple(project_execution_to_ledger_record(execution) for execution in broker_executions)
    ledger_positions = tuple(project_position_to_ledger_record(position) for position in broker_positions)
    ledger_cash = (project_cash_to_ledger_record(broker_cash),) if broker_cash else ()
    if submit_result and submit_result.broker_api_called and ledger_orders:
        pending_plan = replace(pending_plan, state=PendingPlanState.SUBMITTED, updated_at=_now())
        pending_plan = consume_pending_plan(
            pending_plan,
            consume_reason="phase14d8 pure runtime v2 demo buy submit attempted",
            submitted_order_ids=tuple(order.order_ref_hash for order in broker_orders),
            ledger_order_record_ids=tuple(order.record_id for order in ledger_orders),
        )
        _write_json(pending_plan_path, _jsonable(pending_plan))
    asset_state = build_current_asset_state(
        environment="demo",
        positions=ledger_positions,
        cash_records=ledger_cash,
        source="phase14d8_demo_broker_readonly",
        as_of=_business_date(),
    )
    reconciliation = run_reconciliation(
        mode="demo",
        environment="demo",
        business_date=_business_date(),
        pending_plan=pending_plan,
        ledger_orders=ledger_orders,
        ledger_executions=ledger_executions,
        broker_orders=broker_orders,
        broker_executions=broker_executions,
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
            ledger_executions=ledger_executions,
            ledger_positions=ledger_positions,
            ledger_cash_records=ledger_cash,
            broker_orders=broker_orders,
            broker_executions=broker_executions,
            broker_positions=broker_positions,
            broker_cash=broker_cash,
            approval_artifact=approval,
            reconciliation_result=reconciliation,
        )
    )
    notification_payload = build_notification_payload(report=report, channel="phase14d8_payload_only")
    audit = run_audit(
        mode="demo",
        environment="demo",
        business_date=_business_date(),
        report=report,
        notification_payload=notification_payload,
        reconciliation_result=reconciliation,
        asset_state=asset_state,
    )
    fill_classifications = tuple(classify_fill(order=order, executions=broker_executions).classification.value for order in broker_orders)
    target_order_confirmed = any(order.symbol == symbol and order.side == "BUY" and abs(order.quantity - quantity) < 0.000001 for order in broker_orders)
    order_status_fill_without_execution = any(order.symbol == symbol and order.filled_quantity > 0 for order in broker_orders) and not broker_executions
    if order_status_fill_without_execution:
        review_reasons.append("order status indicates fill but execution detail evidence is unavailable")
    if broker_executions:
        execution_classification = "FILLED_WITH_EXECUTION_EVIDENCE"
    elif order_status_fill_without_execution:
        execution_classification = "FILLED_BY_ORDER_STATUS_EXECUTION_DETAIL_REVIEW"
    else:
        execution_classification = "UNFILLED_OR_NOT_CONFIRMED"
    if "REVIEW_REQUIRED" in fill_classifications:
        review_reasons.append("fill classification requires review")
    final_decision = "PHASE14D8_PURE_RUNTIME_V2_DEMO_BUY_PASS"
    if blocked_reasons or review_reasons or not (submit_result and submit_result.accepted) or not target_order_confirmed:
        final_decision = "PHASE14D8_REVIEW_REQUIRED"
    result = Phase14D8Result(
        final_decision=final_decision,
        environment=settings.environment,
        base_url_is_demo=base_url_is_demo,
        base_url_is_production=base_url_is_production,
        d7_sync_pass=d7_sync_pass,
        existing_9432_cancelled=existing_9432_cancelled,
        symbol=symbol,
        side="BUY",
        quantity=quantity,
        runtime_v2_pure_submit_path=True,
        legacy_order_command_submit_authority_used=False,
        legacy_runtime_mode_submit_authority_used=False,
        production_order_executed=False,
        production_broker_api_write_executed=False,
        sell_submit_executed=False,
        demo_submit_executed=bool(submit_result and submit_result.submitted),
        demo_order_accepted=bool(submit_result and submit_result.accepted),
        broker_api_called=bool(submit_result and submit_result.broker_api_called),
        post_send_unknown=bool(submit_result and submit_result.post_send_unknown),
        readonly_before_status=before_status,
        readonly_after_status=after_status,
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
        ledger_execution_count=len(ledger_executions),
        ledger_position_count=len(ledger_positions),
        ledger_cash_count=len(ledger_cash),
        asset_state_created=asset_state is not None,
        order_status_readonly_confirmed=target_order_confirmed,
        execution_state_classification=execution_classification,
        fill_classifications=fill_classifications,
        reconciliation_findings=len(reconciliation.findings),
        report_sections=len(report.sections),
        notification_payload_created=notification_payload is not None,
        audit_findings=len(audit.findings),
        notification_sent=False,
        launchd_or_plist_modified=False,
        blocked_reasons=tuple(blocked_reasons),
        review_reasons=tuple(review_reasons),
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
        pending_item_id=f"phase14d8-buy-{symbol}-{int(quantity)}",
        symbol=symbol,
        side="BUY",
        quantity=quantity,
        order_type="MARKET",
        estimated_price=estimated_price,
        estimated_amount=quantity * estimated_price,
        approved=False,
        state="PENDING_APPROVAL",
    )
    plan = promote_order_plan_to_pending(
        order_plan_id=f"phase14d8-demo-buy-{symbol}",
        source_order_plan_path="order_plan/phase14d8-demo-buy.json",
        source_order_plan_hash=_hash_text(f"phase14d8-demo-buy-{symbol}"),
        environment="demo",
        plan_created_date=_now(),
        intended_submit_date=_business_date(),
        target_session_date=_business_date(),
        items=(item,),
    )
    plan_hash = _hash_json(_jsonable(plan))
    approval = ApprovalArtifact(
        approval_id="approval_phase14d8_demo_buy",
        approval_request_id="approval_request_phase14d8_demo_buy",
        pending_plan_id=plan.pending_plan_id,
        order_plan_id=plan.source_order_plan.order_plan_id,
        status=ApprovalStatus.APPROVED,
        approved_item_ids=(item.pending_item_id,),
        rejected_item_ids=(),
        approval_hash=plan_hash,
        approved_at=_now(),
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
        review_required=False,
        reason=f"Phase14-D8 manual approval for pure Runtime v2 Demo BUY {symbol}",
    )
    return link_approval_to_pending(pending_plan=plan, approval_artifact=approval), approval


def _bundle_from_snapshot(path: Path):
    if not path.exists():
        return normalize_broker_readonly_payload(
            environment="demo",
            source="phase14d8_missing_snapshot",
            as_of=_business_date(),
            cash={"cash_ref": f"missing-{_business_date()}", "cash": 0, "buying_power": 0, "currency": "JPY"},
        )
    payload = _load_json(path)
    return normalize_broker_readonly_payload(
        environment="demo",
        source="phase14d8_demo_broker_readonly",
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


def _orders_health_pass(payload: dict[str, Any]) -> bool:
    return str(((payload.get("health") or {}).get("orders") or {}).get("status") or "") == "PASS"


def _unresolved_9432_open_order(payload: dict[str, Any]) -> bool:
    for order in payload.get("orders") or ():
        if str(order.get("issue_code") or order.get("symbol") or "") != "9432":
            continue
        if _is_cancelled_status(str(order.get("status") or "")):
            continue
        if _float(order.get("remaining_quantity")) > 0:
            return True
    return False


def _normalize_order_status(status: str) -> str:
    if _is_cancelled_status(status):
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


def _markdown_report(result: Phase14D8Result) -> str:
    return f"""# Phase14-D8 Pure Runtime v2 Demo BUY Single-Order Re-test After External Cancel Sync

作成日: 2026-07-07

## Status

```text
{result.final_decision}
```

## Summary

- d7_sync_pass: `{result.d7_sync_pass}`
- existing_9432_cancelled: `{result.existing_9432_cancelled}`
- runtime_v2_pure_submit_path: `{result.runtime_v2_pure_submit_path}`
- legacy_order_command_submit_authority_used: `{result.legacy_order_command_submit_authority_used}`
- legacy_runtime_mode_submit_authority_used: `{result.legacy_runtime_mode_submit_authority_used}`
- environment: `{result.environment}`
- base_url_is_demo: `{result.base_url_is_demo}`
- base_url_is_production: `{result.base_url_is_production}`
- symbol: `{result.symbol}`
- side: `{result.side}`
- quantity: `{result.quantity}`
- demo_submit_executed: `{result.demo_submit_executed}`
- demo_order_accepted: `{result.demo_order_accepted}`
- broker_api_called: `{result.broker_api_called}`
- post_send_unknown: `{result.post_send_unknown}`
- submit_status: `{result.submit_status}`
- execution_state_classification: `{result.execution_state_classification}`
- fill_classifications: `{", ".join(result.fill_classifications) if result.fill_classifications else "none"}`

## Evidence

- pending_plan_path: `{result.pending_plan_path}`
- approval_artifact_path: `{result.approval_artifact_path}`
- broker_response_path: `{result.broker_response_path}`
- readonly_before_snapshot_path: `{result.readonly_before_snapshot_path}`
- readonly_after_snapshot_path: `{result.readonly_after_snapshot_path}`
- readonly_before_status: `{result.readonly_before_status}`
- readonly_after_status: `{result.readonly_after_status}`
- submit_preflight_status: `{result.submit_preflight_status}`
- adapter_preflight_status: `{result.adapter_preflight_status}`
- order_status_readonly_confirmed: `{result.order_status_readonly_confirmed}`

## Runtime v2 Reflection

- ledger_order_count: `{result.ledger_order_count}`
- ledger_execution_count: `{result.ledger_execution_count}`
- ledger_position_count: `{result.ledger_position_count}`
- ledger_cash_count: `{result.ledger_cash_count}`
- asset_state_created: `{result.asset_state_created}`
- reconciliation_findings: `{result.reconciliation_findings}`
- report_sections: `{result.report_sections}`
- notification_payload_created: `{result.notification_payload_created}`
- audit_findings: `{result.audit_findings}`

## Prohibited Actions

- production_order_executed: `{result.production_order_executed}`
- production_broker_api_write_executed: `{result.production_broker_api_write_executed}`
- sell_submit_executed: `{result.sell_submit_executed}`
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
"""
