"""Phase14-D Runtime v2 Demo BUY single-order guarded harness."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.asset.builder import build_current_asset_state
from ai_fund_lab_v2.runtime_v2.audit.auditor import run_audit
from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import normalize_broker_readonly_payload
from ai_fund_lab_v2.runtime_v2.execution.ledger_projection import (
    project_cash_to_ledger_record,
    project_execution_to_ledger_record,
    project_order_to_ledger_record,
    project_position_to_ledger_record,
)
from ai_fund_lab_v2.runtime_v2.ledger.append import append_record
from ai_fund_lab_v2.runtime_v2.notification.payload import build_notification_payload
from ai_fund_lab_v2.runtime_v2.pending.consume import can_submit_pending_plan, consume_pending_plan
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.reconcile.reconciler import run_reconciliation
from ai_fund_lab_v2.runtime_v2.report.builder import build_runtime_report
from ai_fund_lab_v2.runtime_v2.report.models import ReportBuildInput


@dataclass(frozen=True)
class Phase14DDemoBuyResult:
    status: str
    report_path: str
    json_report_path: str
    pending_plan_path: str
    approval_artifact_path: str
    environment: str
    base_url_is_demo: bool
    base_url_is_production: bool
    production_order_executed: bool
    production_broker_api_write_executed: bool
    broker_api_called: bool
    demo_submit_executed: bool
    demo_order_accepted: bool
    post_send_unknown: bool
    readonly_before_status: str
    readonly_after_status: str
    submit_status: str
    submit_classification: str
    broker_readonly_order_status_confirmed: bool
    ledger_order_count: int
    ledger_execution_count: int
    ledger_position_count: int
    ledger_cash_count: int
    asset_state_created: bool
    reconciliation_findings: int
    report_sections: int
    notification_payload_created: bool
    audit_findings: int
    final_decision: str
    blocked_reasons: tuple[str, ...] = ()
    review_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Phase14DDemoBuyCommand:
    runtime_id: str
    environment: str
    issue_code: str
    side: str
    quantity: Decimal
    order_type: str
    price_type: str
    limit_price: Decimal
    estimated_amount: Decimal
    approval_id: str
    live_order_allowed: bool


@dataclass(frozen=True)
class Phase14DSubmitResult:
    status: str
    clm_kabu_new_order_called: bool
    demo_order_executed: bool
    broker_order_api_called: bool
    submit_classification: str
    post_send_unknown: bool
    error_classification: str = ""


@dataclass(frozen=True)
class Phase14DReadOnlyResult:
    status: str
    executed: bool
    snapshot_path: str


def run_demo_buy_single_order_guarded_test(
    *,
    root: Path,
    reports_dir: Path,
    docs_report_path: Path,
    json_report_path: Path,
    environment: str = "demo",
    base_url_is_demo: bool = True,
    base_url_is_production: bool = False,
    readonly_allow_prod: bool = False,
    second_password_file_configured: bool = True,
    issue_code: str = "9432",
    quantity: Decimal = Decimal("100"),
    estimated_price: Decimal = Decimal("200"),
    execute_submit: bool = True,
    submit_func: Callable[[Phase14DDemoBuyCommand], Phase14DSubmitResult] | None = None,
    readonly_before_func: Callable[[Path], Phase14DReadOnlyResult] | None = None,
    readonly_after_func: Callable[[Path], Phase14DReadOnlyResult] | None = None,
) -> Phase14DDemoBuyResult:
    reports_dir.mkdir(parents=True, exist_ok=True)
    root.mkdir(parents=True, exist_ok=True)
    blocked_reasons: list[str] = []
    review_reasons: list[str] = []
    if environment != "demo":
        blocked_reasons.append("environment guard failure")
    if not base_url_is_demo or base_url_is_production:
        blocked_reasons.append("demo base url guard failure")
    if readonly_allow_prod:
        blocked_reasons.append("readonly_allow_prod must be false")
    if not second_password_file_configured:
        blocked_reasons.append("second password file missing")
    if quantity != Decimal("100"):
        blocked_reasons.append("BUY order quantity must be exactly one minimum unit")
    if issue_code != "9432":
        blocked_reasons.append("Phase14-D initial BUY issue code must remain 9432")

    readonly_before_status = "NOT_EXECUTED"
    readonly_after_status = "NOT_EXECUTED"
    before_snapshot_path = root / "broker_readonly_before" / "tachibana_demo_snapshot.json"
    after_snapshot_path = root / "broker_readonly_after" / "tachibana_demo_snapshot.json"
    if not blocked_reasons:
        if readonly_before_func is None:
            before = Phase14DReadOnlyResult(status="NOT_EXECUTED", executed=False, snapshot_path=str(before_snapshot_path))
        else:
            before = readonly_before_func(before_snapshot_path)
        readonly_before_status = before.status
        if not before.executed:
            blocked_reasons.append("readonly sync before submit failed")

    pending_plan_path = root / "pending_order_plan" / "pending_order_plan.json"
    approval_artifact_path = root / "approval_artifact" / "approval_phase14d_demo_buy.json"
    pending_plan_path.parent.mkdir(parents=True, exist_ok=True)
    approval_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    pending_item = PendingOrderItem(
        pending_item_id="phase14d-buy-9432-100",
        symbol=issue_code,
        side="BUY",
        quantity=float(quantity),
        order_type="MARKET",
        estimated_price=float(estimated_price),
        estimated_amount=float(quantity * estimated_price),
        approved=False,
        state="PENDING_APPROVAL",
    )
    pending_plan = promote_order_plan_to_pending(
        order_plan_id="phase14d-demo-buy-order-plan",
        source_order_plan_path="order_plan/phase14d-demo-buy.json",
        source_order_plan_hash=_hash_text("phase14d-demo-buy-order-plan"),
        environment="demo",
        plan_created_date=_utc_now(),
        intended_submit_date=_utc_today(),
        target_session_date=_utc_today(),
        items=(pending_item,),
    )
    pending_plan_hash = _hash_json(_jsonable(pending_plan))
    approval = ApprovalArtifact(
        approval_id="phase14d-demo-buy-approval",
        approval_request_id="phase14d-demo-buy-approval-request",
        pending_plan_id=pending_plan.pending_plan_id,
        order_plan_id=pending_plan.source_order_plan.order_plan_id,
        status=ApprovalStatus.APPROVED,
        approved_item_ids=(pending_item.pending_item_id,),
        rejected_item_ids=(),
        approval_hash=pending_plan_hash,
        approved_at=_utc_now(),
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
        review_required=False,
        reason="Phase14-D manual guarded demo BUY approval",
    )
    pending_plan = link_approval_to_pending(pending_plan=pending_plan, approval_artifact=approval)
    _write_json(pending_plan_path, _jsonable(pending_plan))
    _write_json(approval_artifact_path, _jsonable(approval))

    if pending_plan.state != PendingPlanState.APPROVED:
        blocked_reasons.append("pending state is not APPROVED")
    if pending_plan.approval is None or pending_plan.approval.approval_hash != pending_plan_hash:
        blocked_reasons.append("pending/approval hash mismatch")
    if len(pending_plan.items) != 1 or len(pending_plan.approved_item_ids) != 1:
        blocked_reasons.append("pending plan must contain exactly one approved item")
    if not can_submit_pending_plan(pending_plan, set()):
        blocked_reasons.append("duplicate submit guard blocked or pending cannot submit")

    command = Phase14DDemoBuyCommand(
        runtime_id="phase14d-runtime-v2-demo-buy",
        environment="demo",
        issue_code=issue_code,
        side="BUY",
        quantity=quantity,
        order_type="CASH_EQUITY",
        price_type="MARKET",
        limit_price=Decimal("0"),
        estimated_amount=quantity * estimated_price,
        approval_id=approval.approval_id,
        live_order_allowed=True,
    )
    auth_reason = _authorize_demo_buy_command(
        command=command,
        approval=approval,
        second_password_present=second_password_file_configured,
        max_notional=quantity * estimated_price,
    )
    if auth_reason:
        blocked_reasons.append(f"authorization failed: {auth_reason}")

    submit_result = None
    if not blocked_reasons and execute_submit:
        if submit_func is None:
            blocked_reasons.append("submit_func missing")
        else:
            submit_result = submit_func(command)
    if submit_result is not None:
        if submit_result.post_send_unknown:
            review_reasons.append("broker response unknown")
        if submit_result.submit_classification == "PRE_SEND_FAILURE":
            blocked_reasons.append(f"broker submit failure: {submit_result.error_classification}")
        elif submit_result.submit_classification != "ACCEPTED":
            review_reasons.append(f"broker submit not accepted: {submit_result.submit_classification}")
    elif not execute_submit:
        blocked_reasons.append("execute_submit disabled")

    if submit_result and submit_result.broker_order_api_called:
        if readonly_after_func is None:
            after = Phase14DReadOnlyResult(status="NOT_EXECUTED", executed=False, snapshot_path=str(after_snapshot_path))
        else:
            after = readonly_after_func(after_snapshot_path)
        readonly_after_status = after.status
        if not after.executed:
            review_reasons.append("readonly sync after submit failed")
        if after.status not in {"PASS", "PASS_WITH_WARNINGS"}:
            review_reasons.append(f"readonly sync after submit status={after.status}")

    normalized_bundle = _bundle_from_snapshot(after_snapshot_path if after_snapshot_path.exists() else before_snapshot_path, as_of=_utc_today())
    broker_orders = normalized_bundle.orders
    broker_executions = normalized_bundle.executions
    broker_positions = normalized_bundle.positions
    broker_cash = normalized_bundle.cash
    ledger_orders = tuple(project_order_to_ledger_record(order) for order in broker_orders)
    ledger_executions = tuple(project_execution_to_ledger_record(execution) for execution in broker_executions)
    ledger_positions = tuple(project_position_to_ledger_record(position) for position in broker_positions)
    ledger_cash = (project_cash_to_ledger_record(broker_cash),) if broker_cash else ()
    if submit_result and submit_result.broker_order_api_called and ledger_orders:
        pending_plan = PendingPlanState.SUBMITTED  # type: ignore[assignment]
    if submit_result and submit_result.broker_order_api_called:
        linked_order_ids = tuple(order.order_ref_hash for order in broker_orders)
        linked_ledger_order_ids = tuple(order.record_id for order in ledger_orders)
        if linked_ledger_order_ids:
            from dataclasses import replace

            linked_pending = replace(_read_pending(pending_plan_path), state=PendingPlanState.SUBMITTED)
            linked_pending = consume_pending_plan(
                linked_pending,
                consume_reason="phase14d demo buy submit attempted",
                submitted_order_ids=linked_order_ids,
                ledger_order_record_ids=linked_ledger_order_ids,
            )
            pending_plan = linked_pending  # type: ignore[assignment]
            _write_json(pending_plan_path, _jsonable(linked_pending))
        else:
            pending_plan = _read_pending(pending_plan_path)  # type: ignore[assignment]
    else:
        pending_plan = _read_pending(pending_plan_path)  # type: ignore[assignment]

    asset_state = build_current_asset_state(
        environment="demo",
        positions=ledger_positions,
        cash_records=ledger_cash,
        source="phase14d_demo_broker_readonly",
        as_of=_utc_today(),
    )
    reconciliation = run_reconciliation(
        mode="demo",
        environment="demo",
        business_date=_utc_today(),
        pending_plan=pending_plan,  # type: ignore[arg-type]
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
            business_date=_utc_today(),
            target_session_date=_utc_today(),
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
    payload = build_notification_payload(report=report, channel="phase14d_payload_only")
    audit = run_audit(
        mode="demo",
        environment="demo",
        business_date=_utc_today(),
        report=report,
        notification_payload=payload,
        reconciliation_result=reconciliation,
        asset_state=asset_state,
    )

    final_decision = "PHASE14D_DEMO_BUY_SINGLE_ORDER_PASS"
    if blocked_reasons or review_reasons or not (submit_result and submit_result.demo_order_executed):
        final_decision = "PHASE14D_REVIEW_REQUIRED"
    result = Phase14DDemoBuyResult(
        status=final_decision,
        report_path=str(docs_report_path),
        json_report_path=str(json_report_path),
        pending_plan_path=str(pending_plan_path),
        approval_artifact_path=str(approval_artifact_path),
        environment=environment,
        base_url_is_demo=base_url_is_demo,
        base_url_is_production=base_url_is_production,
        production_order_executed=False,
        production_broker_api_write_executed=False,
        broker_api_called=bool(submit_result and submit_result.broker_order_api_called),
        demo_submit_executed=bool(submit_result and submit_result.clm_kabu_new_order_called),
        demo_order_accepted=bool(submit_result and submit_result.demo_order_executed),
        post_send_unknown=bool(submit_result and submit_result.post_send_unknown),
        readonly_before_status=readonly_before_status,
        readonly_after_status=readonly_after_status,
        submit_status=submit_result.status if submit_result else "NOT_EXECUTED",
        submit_classification=submit_result.submit_classification if submit_result else "NOT_EXECUTED",
        broker_readonly_order_status_confirmed=bool(broker_orders),
        ledger_order_count=len(ledger_orders),
        ledger_execution_count=len(ledger_executions),
        ledger_position_count=len(ledger_positions),
        ledger_cash_count=len(ledger_cash),
        asset_state_created=asset_state is not None,
        reconciliation_findings=len(reconciliation.findings),
        report_sections=len(report.sections),
        notification_payload_created=payload is not None,
        audit_findings=len(audit.findings),
        final_decision=final_decision,
        blocked_reasons=tuple(blocked_reasons),
        review_reasons=tuple(review_reasons),
    )
    _write_json(json_report_path, result.to_dict())
    docs_report_path.write_text(_markdown_report(result), encoding="utf-8")
    return result


def _bundle_from_snapshot(path: Path, *, as_of: str):
    if not path.exists():
        return normalize_broker_readonly_payload(
            environment="demo",
            source="phase14d_missing_broker_snapshot",
            as_of=as_of,
            cash={"cash_ref": f"missing-{as_of}", "cash": 0, "buying_power": 0, "currency": "JPY"},
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return normalize_broker_readonly_payload(
        environment="demo",
        source="phase14d_demo_broker_readonly",
        as_of=str(payload.get("generated_at") or as_of),
        orders=tuple(payload.get("orders") or ()),
        executions=tuple(payload.get("executions") or ()),
        positions=tuple(payload.get("positions") or ()),
        cash=payload.get("buying_power") or payload.get("account_summary") or {"cash": 0, "buying_power": 0, "currency": "JPY"},
    )


def _authorize_demo_buy_command(
    *,
    command: Phase14DDemoBuyCommand,
    approval: ApprovalArtifact,
    second_password_present: bool,
    max_notional: Decimal,
) -> str:
    if command.environment != "demo":
        return "environment_not_demo"
    if not command.live_order_allowed:
        return "live_order_allowed_false"
    if command.approval_id != approval.approval_id:
        return "approval_scope_mismatch"
    if approval.status != ApprovalStatus.APPROVED:
        return "approval_not_approved"
    if command.side != "BUY":
        return "side_not_buy"
    if command.quantity <= Decimal("0"):
        return "quantity_not_positive"
    if command.estimated_amount > max_notional:
        return "notional_exceeds_approval"
    if not second_password_present:
        return "second_password_missing"
    return ""


def _read_pending(path: Path):
    from ai_fund_lab_v2.runtime_v2.pending.models import (
        PendingApprovalLink,
        PendingConsumeInfo,
        PendingOrderPlan,
        PendingPlanState,
        PendingSourceOrderPlan,
        PendingSubmitConstraints,
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
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


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if hasattr(value, "value"):
        return value.value
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hash_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_json(payload: Any) -> str:
    return _hash_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _markdown_report(result: Phase14DDemoBuyResult) -> str:
    return f"""# Phase14-D Demo BUY Single-Order Guarded Test

## Status

```text
{result.final_decision}
```

## Summary

- environment: `{result.environment}`
- base_url_is_demo: `{result.base_url_is_demo}`
- base_url_is_production: `{result.base_url_is_production}`
- demo_submit_executed: `{result.demo_submit_executed}`
- demo_order_accepted: `{result.demo_order_accepted}`
- submit_status: `{result.submit_status}`
- submit_classification: `{result.submit_classification}`
- post_send_unknown: `{result.post_send_unknown}`
- readonly_before_status: `{result.readonly_before_status}`
- readonly_after_status: `{result.readonly_after_status}`
- broker_readonly_order_status_confirmed: `{result.broker_readonly_order_status_confirmed}`

## Runtime v2 Evidence

- pending_plan_path: `{result.pending_plan_path}`
- approval_artifact_path: `{result.approval_artifact_path}`
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
- notification_send_executed: `False`
- launchd_or_plist_modified: `False`

## Blocked Reasons

```text
{chr(10).join(result.blocked_reasons) if result.blocked_reasons else "none"}
```

## Review Reasons

```text
{chr(10).join(result.review_reasons) if result.review_reasons else "none"}
```
"""
