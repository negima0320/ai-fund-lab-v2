"""Runtime v2 execution job Broker ReadOnly ingestion pipeline."""

from __future__ import annotations

import json
import importlib
import hashlib
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
from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerEventRecord, LedgerExecutionRecord, LedgerPositionRecord
from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan
from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan_path
from ai_fund_lab_v2.runtime_v2.pending.models import PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.review_scope_authority import (
    build_pending_review_scope_authority,
    pending_scope_no_submission_terminal_authority,
)
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
    execution_action: str = "EXECUTE"
    orderlist_required: bool = True
    orderlist_status: str = "REQUIRED"
    submitted_order_count: int = 0
    fill_count: int = 0
    pending_terminalization_status: str = "NOT_EVALUATED"
    pending_consumed: bool = False
    pending_mutated: bool = False
    pending_read_valid: bool = False
    pending_classification: str = ""
    pending_active: bool | None = None
    pending_plan_present: bool = False
    pending_item_count: int = 0
    no_action_reason: str = ""
    submit_authority_status: str = ""
    submit_action: str = ""
    submit_authority_path: str = ""
    submit_authority_reason: str = ""
    item_lifecycle_authority: dict[str, Any] | None = None
    pre_commit_cash_feasibility_status: str = "NOT_EVALUATED"
    pre_commit_cash_feasibility_reason: str = ""
    pre_commit_starting_cash: float | None = None
    aggregate_candidate_buy_notional: float = 0.0
    aggregate_candidate_sell_notional: float = 0.0
    candidate_projected_cash: float | None = None
    transaction_validation_status: str = "NOT_EVALUATED"
    transaction_validation_reason: str = ""
    source_current_hash: str = ""
    candidate_current_hash: str = ""
    candidate_cash: float | None = None
    candidate_position_count: int = 0
    candidate_execution_count: int = 0
    persistent_commit_started: bool = False
    persistent_commit_completed: bool = False
    ledger_commit_status: str = "NOT_EXECUTED"
    current_commit_status: str = "NOT_EXECUTED"
    transaction_consistency_status: str = "NOT_EVALUATED"
    execution_transaction_id: str = ""

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
    no_action = _resolve_no_action_execution_authority(
        runtime_root=runtime_root_path,
        business_date=business_date,
        mode=mode,
    )
    if no_action["status"] == "PASS":
        return _no_action_result(
            runtime_root=runtime_root_path,
            business_date=business_date,
            no_action=no_action,
        )
    if no_action["status"] in {"BLOCKED", "REVIEW_REQUIRED"}:
        return _result(
            status=str(no_action["status"]),
            reason=str(no_action["reason"]),
            runtime_root=runtime_root_path,
            pending_read_valid=bool(no_action.get("pending_read_valid")),
            pending_classification=str(no_action.get("pending_classification") or ""),
            pending_active=no_action.get("pending_active"),
            pending_plan_present=bool(no_action.get("pending_plan_present")),
            pending_item_count=int(no_action.get("pending_item_count") or 0),
            no_action_reason=str(no_action.get("no_action_reason") or ""),
            submit_authority_status=str(no_action.get("submit_authority_status") or ""),
            submit_action=str(no_action.get("submit_action") or ""),
            submit_authority_path=str(no_action.get("submit_authority_path") or ""),
            submit_authority_reason=str(no_action.get("submit_authority_reason") or ""),
        )
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
    orders_by_ref = {order.order_ref_hash: order for order in bundle.orders}
    broker_detail_executions = (
        ()
        if mode == "historical"
        else tuple(
            project_execution_to_ledger_record(
                execution,
                source_order=orders_by_ref.get(execution.order_ref_hash),
            )
            for execution in bundle.executions
        )
    )
    equivalent_executions = _execution_equivalent_records(
        orders=bundle.orders,
        executions=bundle.executions,
        positions=bundle.positions,
        cash_present=bundle.cash is not None,
        mode=mode,
        business_date=business_date,
        as_of=as_of,
        detail_status=str(acceptance["order_detail_status"]),
        demo_fallback_authority=demo_fallback_authority,
    )
    ledger_executions = (*broker_detail_executions, *equivalent_executions)
    historical_position_transitions: tuple[LedgerPositionRecord, ...] = ()
    historical_transition_errors: tuple[str, ...] = ()
    if mode == "historical":
        historical_position_transitions, historical_transition_errors = _historical_position_transition_records(
            runtime_root=runtime_root_path,
            business_date=business_date,
            as_of=as_of,
            executions=equivalent_executions,
            broker_position_symbols=tuple(position.symbol for position in bundle.positions),
        )
        if historical_transition_errors:
            return _result(
                status="REVIEW_REQUIRED",
                reason="historical position transition invalid: " + ",".join(historical_transition_errors),
                runtime_root=runtime_root_path,
                snapshot_status=snapshot_result.status,
                snapshot_path=str(snapshot_path),
                report_path=str(report_path),
                )
    ledger_positions = (*ledger_positions, *historical_position_transitions)

    pending_read = read_pending_order_plan(mode=mode, environment=mode, base_dir=runtime_root_path.parent)
    item_lifecycle_authority = None
    ledger_events = _execution_acceptance_events(
        mode=mode,
        as_of=as_of,
        business_date=business_date,
        acceptance=acceptance,
        production_equivalent=bundle.production_equivalent,
    )
    execution_transaction_id = _execution_transaction_id(
        business_date=business_date,
        ledger_orders=ledger_orders,
        ledger_executions=ledger_executions,
        ledger_positions=ledger_positions,
        ledger_cash=ledger_cash,
        ledger_events=ledger_events,
    )
    pre_commit_cash_feasibility = _evaluate_pre_commit_cash_feasibility(
        runtime_root=runtime_root_path,
        business_date=business_date,
        candidate_executions=equivalent_executions,
    )
    pre_commit_cash_feasibility_status = str(pre_commit_cash_feasibility["status"])
    pre_commit_cash_feasibility_reason = str(pre_commit_cash_feasibility["reason"])
    pre_commit_starting_cash = pre_commit_cash_feasibility.get("starting_cash")
    aggregate_candidate_buy_notional = float(pre_commit_cash_feasibility.get("aggregate_candidate_buy_notional") or 0.0)
    aggregate_candidate_sell_notional = float(pre_commit_cash_feasibility.get("aggregate_candidate_sell_notional") or 0.0)
    candidate_projected_cash = pre_commit_cash_feasibility.get("candidate_projected_cash")
    if pre_commit_cash_feasibility_status != "PASS":
        return ExecutionReadOnlyPipelineResult(
            status="REVIEW_REQUIRED",
            reason=f"pre-commit execution cash feasibility failed: {pre_commit_cash_feasibility_reason}",
            snapshot_status=snapshot_result.status,
            snapshot_path=str(snapshot_path),
            report_path=str(report_path),
            orders_count=len(bundle.orders),
            executions_count=len(bundle.executions),
            positions_count=len(bundle.positions),
            cash_present=bundle.cash is not None,
            ledger_orders_appended=0,
            ledger_executions_appended=0,
            ledger_positions_appended=0,
            ledger_cash_appended=0,
            ledger_events_appended=0,
            asset_current_written=False,
            asset_policy="not_executed_pre_commit_cash_feasibility",
            reconcile_status="NOT_EXECUTED",
            reconcile_findings=0,
            orderlist_readonly_connected=True,
            execution_reflection_connected=True,
            ledger_connected=True,
            asset_connected=False,
            positions_evidence_connected=len(bundle.positions) > 0,
            cash_evidence_connected=bundle.cash is not None,
            order_detail_required=False,
            order_detail_status=str(acceptance["order_detail_status"]),
            execution_acceptance_status=str(acceptance["status"]),
            execution_acceptance_reason=str(acceptance["reason"]),
            execution_acceptance_warnings=tuple(str(item) for item in acceptance["warnings"]),
            execution_equivalent_count=len(equivalent_executions),
            runtime_owned_projection_status="NOT_EXECUTED",
            runtime_owned_projection_reason="pre-commit execution cash feasibility failed",
            current_apply_status="NOT_EXECUTED",
            current_apply_reason="pre-commit execution cash feasibility failed",
            execution_action="EXECUTE",
            orderlist_required=True,
            orderlist_status="READY" if bundle.orders else "MISSING",
            submitted_order_count=len(bundle.orders),
            fill_count=len(ledger_executions),
            pending_terminalization_status="NOT_EXECUTED",
            pending_consumed=False,
            pending_mutated=False,
            pending_read_valid=bool(pending_read.valid),
            pending_classification=str(pending_read.classification),
            pending_active=_payload_bool(pending_read.payload, "active_pending"),
            pending_plan_present=pending_read.plan is not None,
            pending_item_count=_payload_item_count(pending_read.payload),
            item_lifecycle_authority=item_lifecycle_authority,
            pre_commit_cash_feasibility_status=pre_commit_cash_feasibility_status,
            pre_commit_cash_feasibility_reason=pre_commit_cash_feasibility_reason,
            pre_commit_starting_cash=pre_commit_starting_cash if pre_commit_starting_cash is None else float(pre_commit_starting_cash),
            aggregate_candidate_buy_notional=aggregate_candidate_buy_notional,
            aggregate_candidate_sell_notional=aggregate_candidate_sell_notional,
            candidate_projected_cash=candidate_projected_cash if candidate_projected_cash is None else float(candidate_projected_cash),
            transaction_validation_status="REVIEW_REQUIRED",
            transaction_validation_reason=pre_commit_cash_feasibility_reason,
            candidate_cash=candidate_projected_cash if candidate_projected_cash is None else float(candidate_projected_cash),
            candidate_execution_count=len(equivalent_executions),
            transaction_consistency_status="NOT_EXECUTED",
            execution_transaction_id=execution_transaction_id,
        )

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

    status = "PASS"
    reason = "execution readonly ingestion completed"
    if acceptance["status"] != "PASS":
        status = "REVIEW_REQUIRED"
        reason = str(acceptance["reason"])
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
            ledger_orders_appended=0,
            ledger_executions_appended=0,
            ledger_positions_appended=0,
            ledger_cash_appended=0,
            ledger_events_appended=0,
            asset_current_written=False,
            asset_policy="not_executed_transaction_validation",
            reconcile_status="NOT_EXECUTED",
            reconcile_findings=0,
            orderlist_readonly_connected=True,
            execution_reflection_connected=True,
            ledger_connected=True,
            asset_connected=False,
            positions_evidence_connected=len(bundle.positions) > 0,
            cash_evidence_connected=bundle.cash is not None,
            order_detail_required=False,
            order_detail_status=str(acceptance["order_detail_status"]),
            execution_acceptance_status=str(acceptance["status"]),
            execution_acceptance_reason=str(acceptance["reason"]),
            execution_acceptance_warnings=tuple(str(item) for item in acceptance["warnings"]),
            execution_equivalent_count=len(equivalent_executions),
            runtime_owned_projection_status="NOT_EXECUTED",
            runtime_owned_projection_reason="execution acceptance failed before transaction commit",
            current_apply_status="NOT_EXECUTED",
            current_apply_reason="execution acceptance failed before transaction commit",
            execution_action="EXECUTE",
            orderlist_required=True,
            orderlist_status="READY" if bundle.orders else "MISSING",
            submitted_order_count=len(bundle.orders),
            fill_count=len(ledger_executions),
            pending_terminalization_status="NOT_EXECUTED",
            pending_consumed=False,
            pending_mutated=False,
            pending_read_valid=bool(pending_read.valid),
            pending_classification=str(pending_read.classification),
            pending_active=_payload_bool(pending_read.payload, "active_pending"),
            pending_plan_present=pending_read.plan is not None,
            pending_item_count=_payload_item_count(pending_read.payload),
            item_lifecycle_authority=item_lifecycle_authority,
            pre_commit_cash_feasibility_status=pre_commit_cash_feasibility_status,
            pre_commit_cash_feasibility_reason=pre_commit_cash_feasibility_reason,
            pre_commit_starting_cash=pre_commit_starting_cash if pre_commit_starting_cash is None else float(pre_commit_starting_cash),
            aggregate_candidate_buy_notional=aggregate_candidate_buy_notional,
            aggregate_candidate_sell_notional=aggregate_candidate_sell_notional,
            candidate_projected_cash=candidate_projected_cash if candidate_projected_cash is None else float(candidate_projected_cash),
            transaction_validation_status="REVIEW_REQUIRED",
            transaction_validation_reason=reason,
            candidate_cash=candidate_projected_cash if candidate_projected_cash is None else float(candidate_projected_cash),
            candidate_execution_count=len(equivalent_executions),
            transaction_consistency_status="NOT_EXECUTED",
            execution_transaction_id=execution_transaction_id,
        )

    projection = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root_path,
        business_date=business_date,
        mode=mode,
        write=False,
        candidate_orders=ledger_orders,
        candidate_executions=ledger_executions,
        candidate_positions=ledger_positions,
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
    source_current_hash = _payload_hash(projection.current_sot_before)
    candidate_current_hash = _payload_hash(projection.current_sot_after)
    if projection.status != "PASS":
        return ExecutionReadOnlyPipelineResult(
            status="REVIEW_REQUIRED",
            reason=f"runtime owned current projection failed before transaction commit: {projection.reason}",
            snapshot_status=snapshot_result.status,
            snapshot_path=str(snapshot_path),
            report_path=str(report_path),
            orders_count=len(bundle.orders),
            executions_count=len(bundle.executions),
            positions_count=len(bundle.positions),
            cash_present=bundle.cash is not None,
            ledger_orders_appended=0,
            ledger_executions_appended=0,
            ledger_positions_appended=0,
            ledger_cash_appended=0,
            ledger_events_appended=0,
            asset_current_written=False,
            asset_policy="not_executed_transaction_validation",
            reconcile_status="NOT_EXECUTED",
            reconcile_findings=0,
            orderlist_readonly_connected=True,
            execution_reflection_connected=True,
            ledger_connected=True,
            asset_connected=False,
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
            current_apply_status="NOT_EXECUTED",
            current_apply_reason="runtime owned current projection failed before transaction commit",
            execution_action="EXECUTE",
            orderlist_required=True,
            orderlist_status="READY" if bundle.orders else "MISSING",
            submitted_order_count=len(bundle.orders),
            fill_count=len(ledger_executions),
            pending_terminalization_status="NOT_EXECUTED",
            pending_consumed=False,
            pending_mutated=False,
            pending_read_valid=bool(pending_read.valid),
            pending_classification=str(pending_read.classification),
            pending_active=_payload_bool(pending_read.payload, "active_pending"),
            pending_plan_present=pending_read.plan is not None,
            pending_item_count=_payload_item_count(pending_read.payload),
            item_lifecycle_authority=item_lifecycle_authority,
            pre_commit_cash_feasibility_status=pre_commit_cash_feasibility_status,
            pre_commit_cash_feasibility_reason=pre_commit_cash_feasibility_reason,
            pre_commit_starting_cash=pre_commit_starting_cash if pre_commit_starting_cash is None else float(pre_commit_starting_cash),
            aggregate_candidate_buy_notional=aggregate_candidate_buy_notional,
            aggregate_candidate_sell_notional=aggregate_candidate_sell_notional,
            candidate_projected_cash=candidate_projected_cash if candidate_projected_cash is None else float(candidate_projected_cash),
            transaction_validation_status="REVIEW_REQUIRED",
            transaction_validation_reason=projection.reason,
            source_current_hash=source_current_hash,
            candidate_current_hash=candidate_current_hash,
            candidate_cash=projection.projected_cash,
            candidate_position_count=len(projection.projected_positions),
            candidate_execution_count=len(equivalent_executions),
            transaction_consistency_status="NOT_EXECUTED",
            execution_transaction_id=execution_transaction_id,
        )

    transaction_validation_status = "PASS"
    transaction_validation_reason = "execution transaction candidate validated before persistent commit"
    persistent_commit_started = True
    persistent_commit_completed = False
    orders_appended = 0
    executions_appended = 0
    positions_appended = 0
    cash_appended = 0
    events_appended = 0
    ledger_commit_status = "NOT_EXECUTED"
    current_commit_status = "NOT_EXECUTED"
    transaction_consistency_status = "NOT_EVALUATED"
    try:
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
        events_appended = _append_ledger_records(
            runtime_root_path / "persistent_ledger" / "events.jsonl",
            ledger_events,
        )
        ledger_commit_status = "PASS"
        _write_current_projection_payload(runtime_root_path / "persistent_ledger" / "state.json", projection.current_sot_after)
        asset_current_written = True
        asset_policy = "runtime_owned_fill_projection"
        current_commit_status = "CURRENT_WRITTEN"
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
        current_commit_status = current_apply.status
        persistent_commit_completed = current_apply.status in {"APPLIED", "NOOP_ALREADY_APPLIED"}
        transaction_consistency_status = "PASS" if persistent_commit_completed else "REVIEW_REQUIRED"
    except Exception as exc:
        status = "REVIEW_REQUIRED"
        reason = f"execution transaction commit failed: {exc}"
        transaction_consistency_status = "REVIEW_REQUIRED"
        current_apply_status = "NOT_EXECUTED" if current_apply_status == "NOT_EXECUTED" else current_apply_status
        current_apply_reason = str(exc)
    if status == "PASS" and not persistent_commit_completed:
        status = "REVIEW_REQUIRED"
        reason = "execution transaction commit did not complete"
        transaction_consistency_status = "REVIEW_REQUIRED"

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
    if persistent_commit_completed and reconciliation.findings and status == "PASS" and mode != "demo":
        status = "REVIEW_REQUIRED"
        reason = f"reconciliation findings={len(reconciliation.findings)}"
    reconcile_status = "PASS" if not reconciliation.findings else "REVIEW_REQUIRED"
    if not persistent_commit_completed:
        reconcile_status = "NOT_EXECUTED"
    if persistent_commit_completed and reconciliation.findings and status == "PASS" and mode == "demo":
        reconcile_status = "PASS_WITH_WARNINGS"
    item_lifecycle_authority = _historical_mixed_item_lifecycle_authority(
        runtime_root=runtime_root_path,
        business_date=business_date,
        mode=mode,
        orders=bundle.orders,
    )
    pending_terminalization_status = (
        "PENDING_LIFECYCLE_REQUIRED"
        if persistent_commit_completed and item_lifecycle_authority.get("status") == "PASS"
        else "NOT_REQUIRED"
    )
    if not persistent_commit_completed:
        pending_terminalization_status = "NOT_EXECUTED"

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
        execution_action="EXECUTE",
        orderlist_required=True,
        orderlist_status="READY" if bundle.orders else "MISSING",
        submitted_order_count=len(bundle.orders),
        fill_count=len(ledger_executions),
        pending_terminalization_status=pending_terminalization_status,
        pending_consumed=False,
        pending_mutated=False,
        pending_read_valid=bool(pending_read.valid),
        pending_classification=str(pending_read.classification),
        pending_active=_payload_bool(pending_read.payload, "active_pending"),
        pending_plan_present=pending_read.plan is not None,
        pending_item_count=_payload_item_count(pending_read.payload),
        item_lifecycle_authority=item_lifecycle_authority,
        pre_commit_cash_feasibility_status=pre_commit_cash_feasibility_status,
        pre_commit_cash_feasibility_reason=pre_commit_cash_feasibility_reason,
        pre_commit_starting_cash=pre_commit_starting_cash if pre_commit_starting_cash is None else float(pre_commit_starting_cash),
        aggregate_candidate_buy_notional=aggregate_candidate_buy_notional,
        aggregate_candidate_sell_notional=aggregate_candidate_sell_notional,
        candidate_projected_cash=candidate_projected_cash if candidate_projected_cash is None else float(candidate_projected_cash),
        transaction_validation_status=transaction_validation_status,
        transaction_validation_reason=transaction_validation_reason,
        source_current_hash=source_current_hash,
        candidate_current_hash=candidate_current_hash,
        candidate_cash=projection.projected_cash,
        candidate_position_count=len(projection.projected_positions),
        candidate_execution_count=len(equivalent_executions),
        persistent_commit_started=persistent_commit_started,
        persistent_commit_completed=persistent_commit_completed,
        ledger_commit_status=ledger_commit_status,
        current_commit_status=current_commit_status,
        transaction_consistency_status=transaction_consistency_status,
        execution_transaction_id=execution_transaction_id,
    )


def _resolve_no_action_execution_authority(
    *,
    runtime_root: Path,
    business_date: str,
    mode: str,
) -> dict[str, Any]:
    pending_read = read_pending_order_plan_path(
        path=runtime_root / "pending_order_plan" / "pending_order_plan.json",
        environment=mode,
    )
    evidence = {
        "pending_read_valid": pending_read.valid,
        "pending_classification": pending_read.classification,
        "pending_active": _payload_bool(pending_read.payload, "active_pending"),
        "pending_plan_present": pending_read.plan is not None,
        "pending_item_count": _payload_item_count(pending_read.payload),
        "no_action_reason": _payload_text(pending_read.payload, "no_action_reason"),
    }
    if mode == "historical":
        quarantine_authority = _load_historical_quarantine_no_submitted_authority(
            runtime_root=runtime_root,
            business_date=business_date,
            pending_evidence=evidence,
        )
        if quarantine_authority["status"] in {"PASS", "REVIEW_REQUIRED"}:
            return quarantine_authority
    if not pending_read.valid:
        return {"status": "NOT_APPLICABLE", "reason": "pending_not_empty", **evidence}
    active_no_order = pending_read.plan is not None and pending_read.plan.state == PendingPlanState.EMPTY
    active_buy_item_review_no_submission = (
        pending_read.plan is not None
        and _is_buy_item_scoped_review_no_submission_pending(pending_read.plan, business_date=business_date)
    )
    active_submit_aggregate_terminal_noop = (
        pending_read.plan is not None
        and pending_read.classification == "VALID"
        and _latest_submit_manifest_has_terminal_noop_authority(runtime_root=runtime_root, business_date=business_date)
    )
    if (
        pending_read.classification != "EMPTY"
        and not active_no_order
        and not active_buy_item_review_no_submission
        and not active_submit_aggregate_terminal_noop
    ):
        return {"status": "NOT_APPLICABLE", "reason": "pending_not_empty", **evidence}
    if pending_read.classification == "EMPTY":
        empty_reason = _validate_empty_pending_payload(
            pending_read.payload,
            business_date=business_date,
            environment=mode,
        )
        if empty_reason:
            return {"status": "BLOCKED", "reason": empty_reason, **evidence}
    elif active_no_order and pending_read.plan is not None:
        if pending_read.plan.target_session_date != business_date:
            return {"status": "BLOCKED", "reason": "pending EMPTY target_session_date mismatch", **evidence}
        if pending_read.plan.items:
            return {"status": "BLOCKED", "reason": "pending EMPTY active no-order requires empty items", **evidence}
    elif active_buy_item_review_no_submission and pending_read.plan is not None:
        if pending_read.plan.target_session_date != business_date:
            return {"status": "BLOCKED", "reason": "pending BUY_ITEM_SCOPED_REVIEW target_session_date mismatch", **evidence}
    elif active_submit_aggregate_terminal_noop and pending_read.plan is not None:
        if pending_read.plan.target_session_date != business_date:
            return {"status": "BLOCKED", "reason": "pending aggregate terminal target_session_date mismatch", **evidence}
    submit = _load_submit_no_action_authority(runtime_root=runtime_root, business_date=business_date)
    evidence.update(
        {
            "submit_authority_status": submit["status"],
            "submit_action": submit["submit_action"],
            "submit_authority_path": submit["path"],
            "submit_authority_reason": submit["reason"],
        }
    )
    if submit["status"] != "PASS":
        return {"status": "REVIEW_REQUIRED", "reason": submit["reason"], **evidence}
    return {"status": "PASS", "reason": "no_submitted_orders", **evidence}


def _load_submit_no_action_authority(*, runtime_root: Path, business_date: str) -> dict[str, Any]:
    manifest_dir = runtime_root / "runtime_state" / "run_manifest" / business_date
    manifests = sorted(manifest_dir.glob("runtime-v2-submit-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not manifests:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "submit NO_ACTION authority missing",
            "path": "",
            "submit_action": "",
        }
    for path in manifests:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if str(payload.get("job") or "") != "submit":
            continue
        if str(payload.get("business_date") or "") != business_date:
            return {
                "status": "REVIEW_REQUIRED",
                "reason": "submit NO_ACTION authority business_date mismatch",
                "path": str(path),
                "submit_action": str(payload.get("submit_action") or ""),
            }
        submit_action = str(payload.get("submit_action") or "")
        if (
            _int_value(payload.get("exit_code"), -1) == 0
            and str(payload.get("final_state") or "") != "BLOCKED"
            and bool(payload.get("pending_read_valid")) is True
            and (
                (
                    str(payload.get("pending_classification") or "") == "EMPTY"
                    and bool(payload.get("pending_active")) is False
                    and bool(payload.get("pending_plan_present")) is False
                    and submit_action == "NO_ACTION"
                    and _int_value(payload.get("pending_item_count"), 0) == 0
                )
                or _valid_pending_submit_no_action_authority_pass(payload, submit_action=submit_action)
            )
            and _int_value(payload.get("submitted_count"), 0) == 0
            and _int_value(payload.get("blocked_count"), 0) == 0
            and bool(payload.get("review_required")) is False
            and bool(payload.get("halt_required")) is False
            and not bool((payload.get("prohibited_actions") or {}).get("demo_submit_executed"))
            and not bool((payload.get("prohibited_actions") or {}).get("production_order_executed"))
        ):
            return {
                "status": "PASS",
                "reason": "submit_no_action_authority_ready",
                "path": str(path),
                "submit_action": submit_action,
            }
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "submit NO_ACTION authority inconsistent",
            "path": str(path),
            "submit_action": submit_action,
        }
    return {
        "status": "REVIEW_REQUIRED",
        "reason": "submit NO_ACTION authority unreadable",
        "path": "",
        "submit_action": "",
    }


def _valid_pending_submit_no_action_authority_pass(payload: dict[str, Any], *, submit_action: str) -> bool:
    if str(payload.get("pending_classification") or "") != "VALID" or bool(payload.get("pending_plan_present")) is not True:
        return False
    no_order = payload.get("no_order_authority_evidence") or {}
    conventional_no_order_status_pass = (
        str(payload.get("no_order_authority_status") or "") == "PASS"
        and str(no_order.get("status") or "") == "PASS"
    )
    return bool(
        (
            conventional_no_order_status_pass
            and (
                _submit_authorized_no_order_authority_pass(payload, submit_action=submit_action)
                or _submit_buy_item_scoped_review_no_submission_pass(payload, submit_action=submit_action)
            )
        )
        or _submit_aggregate_terminal_noop_authority_pass(payload)
    )


def _submit_authorized_no_order_authority_pass(payload: dict[str, Any], *, submit_action: str) -> bool:
    no_order = payload.get("no_order_authority_evidence") or {}
    return bool(
        submit_action == "NO_SUBMISSION_REQUIRED"
        and str(no_order.get("authority_type") or "") == "AUTHORIZED_NO_ORDER"
        and str(no_order.get("order_plan_status") or "") == "NO_ORDER_AUTHORIZED"
        and str(no_order.get("planning_consumer_eligibility") or "") == "NO_ORDER_AUTHORIZED"
        and str(no_order.get("approval_status") or "") == "NO_ORDER_AUTHORIZED"
        and str(no_order.get("pending_state") or "") == "EMPTY"
        and _int_value(no_order.get("pending_item_count"), -1) == 0
        and _int_value(no_order.get("pending_approved_item_count"), -1) == 0
        and _int_value(payload.get("pending_item_count"), -1) == 0
    )


def _submit_buy_item_scoped_review_no_submission_pass(payload: dict[str, Any], *, submit_action: str) -> bool:
    no_order = payload.get("no_order_authority_evidence") or {}
    return bool(
        submit_action == "NO_SUBMISSION_REQUIRED"
        and str(no_order.get("authority_type") or "") == "BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION"
        and _int_value(payload.get("pending_item_count"), 0) > 0
    )


def _submit_aggregate_terminal_noop_authority_pass(payload: dict[str, Any]) -> bool:
    no_order = payload.get("no_order_authority_evidence")
    if not isinstance(no_order, dict):
        return False
    aggregate = no_order.get("submit_aggregate_terminal_noop_authority")
    if not isinstance(aggregate, dict):
        return False
    if str(aggregate.get("authority_type") or "") != "SUBMIT_AGGREGATE_TERMINAL_NOOP_CONTINUATION":
        return False
    if str(aggregate.get("status") or "") != "PASS":
        return False
    if str(aggregate.get("reason") or "") != "zero_submission_terminal_noop_continuation":
        return False
    if not bool(aggregate.get("zero_submission_safe_terminal_pass_supported")):
        return False
    if _int_value(aggregate.get("submitted_count"), -1) != 0 or _int_value(aggregate.get("accepted_count"), -1) != 0:
        return False
    counts = aggregate.get("counts") if isinstance(aggregate.get("counts"), dict) else {}
    if any(
        _int_value(counts.get(key), 0) != 0
        for key in ("blocked", "rejected", "retryable_executable", "unknown_or_ambiguous")
    ):
        return False
    if _int_value(counts.get("submitted_or_reconciled"), 0) != 0:
        return False
    safe_count = _int_value(aggregate.get("known_safe_terminal_or_deferred_count"), 0)
    if safe_count <= 0:
        return False
    if _int_value(counts.get("terminal_not_executable"), 0) + _int_value(counts.get("deferred_item_scoped_review"), 0) != safe_count:
        return False
    if any(
        bool(aggregate.get(key))
        for key in ("fake_submission_created", "fake_execution_created", "fake_cash_mutation", "fake_position_mutation")
    ):
        return False
    item_classes = aggregate.get("item_classes") if isinstance(aggregate.get("item_classes"), dict) else {}
    if not item_classes or any(
        str(value) not in {"DEFERRED_ITEM_SCOPED_REVIEW", "TERMINAL_NOT_EXECUTABLE"}
        for value in item_classes.values()
    ):
        return False
    scope = aggregate.get("pending_review_scope_authority")
    if not isinstance(scope, dict):
        return False
    if str(scope.get("structural_validity") or "") != "PASS":
        return False
    if bool(scope.get("batch_blocked")):
        return False
    if scope.get("executable_item_ids") or scope.get("non_terminal_item_ids") or scope.get("reviewed_sell_item_ids"):
        return False
    if not (scope.get("terminal_item_ids") or scope.get("reviewed_item_ids")):
        return False
    checks = aggregate.get("checks")
    if isinstance(checks, dict):
        required_checks = (
            "all_items_have_known_dispositions",
            "blocked_absent",
            "item_scoped_reviews_deferred_by_authority",
            "pending_review_scope_no_executable_items_after_terminalization",
            "pending_review_scope_no_non_terminal_items_after_terminalization",
            "pending_review_scope_not_batch_blocked",
            "pending_review_scope_structural_valid",
            "rejected_absent",
            "retryable_executable_absent",
            "reviewed_sell_absent",
            "terminal_not_executable_items_safety_qualified",
            "unknown_or_ambiguous_absent",
        )
        if not all(bool(checks.get(key)) for key in required_checks):
            return False
    return True


def _latest_submit_manifest_has_terminal_noop_authority(*, runtime_root: Path, business_date: str) -> bool:
    latest = _latest_submit_manifest(runtime_root=runtime_root, business_date=business_date)
    if latest is None:
        return False
    _, payload = latest
    no_order = payload.get("no_order_authority_evidence")
    if not isinstance(no_order, dict):
        return False
    aggregate = no_order.get("submit_aggregate_terminal_noop_authority")
    if not isinstance(aggregate, dict):
        return False
    return str(aggregate.get("authority_type") or "") == "SUBMIT_AGGREGATE_TERMINAL_NOOP_CONTINUATION"


def _is_buy_item_scoped_review_no_submission_pending(pending, *, business_date: str) -> bool:
    authority = build_pending_review_scope_authority(pending)
    if not pending_scope_no_submission_terminal_authority(authority):
        return False
    return pending.target_session_date == business_date


def _load_historical_quarantine_no_submitted_authority(
    *,
    runtime_root: Path,
    business_date: str,
    pending_evidence: dict[str, Any],
) -> dict[str, Any]:
    submit = _latest_submit_manifest(runtime_root=runtime_root, business_date=business_date)
    if submit is None:
        return {"status": "NOT_APPLICABLE", "reason": "historical quarantine submit authority missing", **pending_evidence}
    path, payload = submit
    if str(payload.get("job") or "") != "submit" or str(payload.get("business_date") or "") != business_date:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "historical quarantine submit authority business_date mismatch",
            **pending_evidence,
            "submit_authority_status": "REVIEW_REQUIRED",
            "submit_action": str(payload.get("submit_action") or ""),
            "submit_authority_path": str(path),
            "submit_authority_reason": "historical quarantine submit authority business_date mismatch",
        }
    if not _manifest_indicates_historical(payload):
        return {"status": "NOT_APPLICABLE", "reason": "historical quarantine authority not applicable", **pending_evidence}
    if _int_value(payload.get("submitted_count"), 0) != 0:
        return {"status": "NOT_APPLICABLE", "reason": "submitted_orders_present", **pending_evidence}

    continuation_path = _historical_quarantine_continuation_path(payload, business_date)
    continuation = _load_json_optional(continuation_path)
    checks = _historical_quarantine_no_submitted_checks(
        submit_payload=payload,
        continuation=continuation,
        business_date=business_date,
        submit_manifest_path=path,
    )
    if not all(checks.values()):
        return {"status": "NOT_APPLICABLE", "reason": "historical quarantine no-submitted authority not applicable", **pending_evidence}

    affected_symbols = tuple(str(symbol) for symbol in continuation.get("affected_symbols") or ())
    return {
        "status": "PASS",
        "reason": "historical_corporate_action_quarantine_no_submitted_orders",
        **pending_evidence,
        "submit_authority_status": "PASS",
        "submit_action": str(payload.get("submit_action") or ""),
        "submit_authority_path": str(path),
        "submit_authority_reason": "historical_corporate_action_quarantine_no_submitted_orders",
        "historical_quarantine_continuation_path": str(continuation_path),
        "historical_quarantine_continuation_status": str(continuation.get("status") or ""),
        "historical_quarantine_affected_symbols": affected_symbols,
    }


def _latest_submit_manifest(*, runtime_root: Path, business_date: str) -> tuple[Path, dict[str, Any]] | None:
    manifest_dir = runtime_root / "runtime_state" / "run_manifest" / business_date
    manifests = sorted(manifest_dir.glob("runtime-v2-submit-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in manifests:
        payload = _load_json_optional(path)
        if payload and str(payload.get("job") or "") == "submit":
            return path, payload
    return None


def _historical_quarantine_continuation_path(submit_payload: dict[str, Any], business_date: str) -> Path:
    evidence_root = str(submit_payload.get("runtime_test_evidence_root") or "")
    run_id = str(submit_payload.get("runtime_test_run_id") or "")
    if evidence_root and Path(evidence_root).name == run_id:
        run_dir = Path(evidence_root)
    else:
        run_dir = Path(evidence_root) / "runs" / run_id if evidence_root and run_id else Path()
    return run_dir / "daily" / business_date / "submit" / "corporate_action_symbol_quarantine_continuation.json"


def _historical_quarantine_no_submitted_checks(
    *,
    submit_payload: dict[str, Any],
    continuation: dict[str, Any],
    business_date: str,
    submit_manifest_path: Path,
) -> dict[str, bool]:
    guard_items = submit_payload.get("submit_guard_item_evidence")
    guard_items = guard_items if isinstance(guard_items, list) else []
    affected_symbols = [str(symbol).strip().upper() for symbol in continuation.get("affected_symbols") or () if str(symbol).strip()]
    continuation_checks = continuation.get("checks") if isinstance(continuation.get("checks"), dict) else {}
    prohibited = submit_payload.get("prohibited_actions") if isinstance(submit_payload.get("prohibited_actions"), dict) else {}
    blocked_count = _int_value(submit_payload.get("blocked_count"), 0)
    submitted_count = _int_value(submit_payload.get("submitted_count"), 0)
    pending_item_count = _int_value(submit_payload.get("pending_item_count"), 0)
    ca_blocked_items = [
        item
        for item in guard_items
        if str(item.get("submit_item_status") or "") == "REVIEW_REQUIRED"
        and str(item.get("guard_decision") or "") == "BLOCKED"
        and str(item.get("guard_reason") or item.get("blocked_at_submit_reason") or "") == "corporate_action_event_not_resolved"
        and str(item.get("violated_policy") or "") == "historical_corporate_action_symbol_quarantine"
    ]
    return {
        "mode_historical": _manifest_indicates_historical(submit_payload),
        "continuation_artifact_present": bool(continuation),
        "continuation_status": str(continuation.get("status") or "") == "COMPLETED_WITH_SYMBOL_QUARANTINE",
        "continuation_business_date": str(continuation.get("business_date") or "") == business_date,
        "continuation_job": str(continuation.get("job") or "") == "submit",
        "continuation_scope": str(continuation.get("scope") or "") == "CORPORATE_ACTION_SYMBOL_ONLY",
        "production_never": str(continuation.get("production_applicability") or "") == "NEVER",
        "run_continuation_historical_only": (
            str(continuation.get("corporate_action_run_continuation_eligibility") or "")
            == "ALLOWED_FOR_HISTORICAL_REPLAY_ONLY"
        ),
        "affected_symbols_present": bool(affected_symbols),
        "submitted_count_zero": submitted_count == 0,
        "blocked_count_positive": blocked_count > 0,
        "pending_count_matches_guard": pending_item_count > 0 and len(guard_items) == pending_item_count,
        "all_pending_items_classified_ca_blocked": len(ca_blocked_items) == pending_item_count == blocked_count,
        "no_generic_review_mixed_in": blocked_count == len(ca_blocked_items),
        "submit_review_required": str(submit_payload.get("final_state") or "") == "REVIEW_REQUIRED",
        "submit_nonzero": _int_value(submit_payload.get("exit_code"), -1) != 0,
        "no_broker_write": (
            not bool(submit_payload.get("broker_write"))
            and not bool(submit_payload.get("external_delivery"))
            and not bool(prohibited.get("demo_submit_executed"))
            and not bool(prohibited.get("production_order_executed"))
            and not bool(prohibited.get("broker_write"))
            and not bool(prohibited.get("external_delivery"))
        ),
        "continuation_runtime_manifest_bound": (
            str(continuation.get("runtime_manifest_path") or "") in {"", str(submit_manifest_path)}
            or Path(str(continuation.get("runtime_manifest_path") or "")).name == submit_manifest_path.name
            or str(continuation.get("runtime_manifest_path") or "").endswith(
                f"/daily/{business_date}/submit/runtime_manifest.json"
            )
        ),
        "classifier_checks_pass": all(bool(value) for value in continuation_checks.values()) if continuation_checks else False,
    }


def _manifest_indicates_historical(payload: dict[str, Any]) -> bool:
    if str(payload.get("run_type") or "").upper() == "HISTORICAL":
        return True
    if str(payload.get("runtime_mode") or payload.get("mode") or "").lower() == "historical":
        return True
    for stage in payload.get("stages") or ():
        if not isinstance(stage, dict):
            continue
        details = stage.get("details") if isinstance(stage.get("details"), dict) else {}
        if bool(details.get("historical_replay")) or str(details.get("run_type") or "").upper() == "HISTORICAL":
            return True
    return False


def _no_action_result(*, runtime_root: Path, business_date: str, no_action: dict[str, Any]) -> ExecutionReadOnlyPipelineResult:
    pending_terminalization_status = "ALREADY_TERMINAL"
    if bool(no_action.get("pending_plan_present")) and int(no_action.get("pending_item_count") or 0) > 0:
        pending_terminalization_status = "PENDING_LIFECYCLE_REQUIRED"
    return ExecutionReadOnlyPipelineResult(
        status="PASS",
        reason="no_submitted_orders",
        snapshot_status="NOT_REQUIRED",
        snapshot_path="",
        report_path="",
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
        asset_policy="not_required_no_submitted_orders",
        reconcile_status="NOT_REQUIRED",
        reconcile_findings=0,
        orderlist_readonly_connected=False,
        execution_reflection_connected=False,
        ledger_connected=True,
        asset_connected=False,
        order_detail_required=False,
        order_detail_status="NOT_REQUIRED",
        execution_acceptance_status="PASS",
        execution_acceptance_reason="no_submitted_orders",
        execution_acceptance_warnings=(),
        execution_equivalent_count=0,
        runtime_owned_projection_status="NOT_REQUIRED",
        runtime_owned_projection_reason="no_submitted_orders",
        current_apply_status="NOT_REQUIRED",
        current_apply_reason="no_submitted_orders",
        execution_references=(),
        execution_action="NO_ACTION",
        orderlist_required=False,
        orderlist_status="NOT_REQUIRED",
        submitted_order_count=0,
        fill_count=0,
        pending_terminalization_status=pending_terminalization_status,
        pending_consumed=False,
        pending_mutated=False,
        pending_read_valid=bool(no_action.get("pending_read_valid")),
        pending_classification=str(no_action.get("pending_classification") or ""),
        pending_active=no_action.get("pending_active"),
        pending_plan_present=bool(no_action.get("pending_plan_present")),
        pending_item_count=int(no_action.get("pending_item_count") or 0),
        no_action_reason=str(no_action.get("no_action_reason") or ""),
        submit_authority_status=str(no_action.get("submit_authority_status") or ""),
        submit_action=str(no_action.get("submit_action") or ""),
        submit_authority_path=str(no_action.get("submit_authority_path") or ""),
        submit_authority_reason=str(no_action.get("submit_authority_reason") or ""),
    )


def _validate_empty_pending_payload(
    payload: dict[str, Any] | None,
    *,
    business_date: str,
    environment: str,
) -> str:
    _ = business_date, environment
    if not isinstance(payload, dict):
        return "pending EMPTY classification payload missing"
    if bool(payload.get("active_pending", True)):
        return "pending EMPTY classification active_pending contradiction"
    if str(payload.get("state") or payload.get("status") or "").upper() != "EMPTY":
        return "pending EMPTY classification state mismatch"
    items = payload.get("items")
    if items not in (None, []) and not (isinstance(items, tuple) and not items):
        return "pending EMPTY classification requires empty items"
    return ""


def _payload_text(payload: dict[str, Any] | None, key: str) -> str:
    if not isinstance(payload, dict):
        return ""
    return str(payload.get(key) or "")


def _payload_bool(payload: dict[str, Any] | None, key: str) -> bool | None:
    if not isinstance(payload, dict) or key not in payload:
        return None
    return bool(payload.get(key))


def _payload_item_count(payload: dict[str, Any] | None) -> int:
    if not isinstance(payload, dict):
        return 0
    items = payload.get("items")
    return len(items) if isinstance(items, list) else 0


def _int_value(value: Any, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


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
    executions: Iterable[Any] = (),
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
    executions_by_order = {execution.order_ref_hash: execution for execution in executions}
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
        source_execution = executions_by_order.get(order.order_ref_hash)
        if source_execution is not None and (position is None or mode == "historical"):
            execution_price = float(getattr(source_execution, "price", 0.0) or 0.0)
            market_price = execution_price
            price_source = "historical_execution_authority" if mode == "historical" else "broker_execution_evidence"
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
                source_decision_id=order.source_decision_id or order.source_pm_decision_id,
                source_pm_decision_id=order.source_pm_decision_id,
                source_decision_type=order.source_decision_type,
                source_pm_business_date=order.source_pm_business_date,
                source_position_symbol=order.source_position_symbol,
                position_campaign_id=order.position_campaign_id,
                source_position_hash=getattr(position, "position_ref_hash", "") if position is not None else "",
                evidence_refs=evidence_refs,
                detail_required=False,
                detail_status=detail_status,
                executed_at=as_of,
            )
        )
    return tuple(records)


def _evaluate_pre_commit_cash_feasibility(
    *,
    runtime_root: Path,
    business_date: str,
    candidate_executions: Iterable[LedgerExecutionRecord],
) -> dict[str, Any]:
    state_path = runtime_root / "persistent_ledger" / "state.json"
    state = _load_json_dict(state_path)
    applied_execution_keys = _current_applied_execution_keys(state)
    raw_cash = state.get("cash")
    if raw_cash in (None, ""):
        return {
            "schema_version": "runtime_v2_pre_commit_execution_cash_feasibility.v1",
            "status": "REVIEW_REQUIRED",
            "reason": "current cash missing",
            "business_date": business_date,
            "current_state_path": str(state_path),
            "persistent_execution_commit_allowed": False,
        }
    starting_cash = _float(raw_cash)
    cash = starting_cash
    buy_notional = 0.0
    sell_notional = 0.0
    items: list[dict[str, Any]] = []
    already_applied_count = 0
    selected_count = 0
    for execution in candidate_executions:
        side = str(getattr(execution, "side", "") or "").upper()
        quantity = _float(getattr(execution, "filled_quantity", 0.0) or getattr(execution, "quantity", 0.0))
        price = _float(getattr(execution, "price", 0.0) or getattr(execution, "average_price", 0.0))
        notional = _float(getattr(execution, "cash_effect", None)) or quantity * price
        execution_id = str(getattr(execution, "execution_id", "") or "")
        dedup_key = str(getattr(execution, "dedup_key", "") or "")
        if side == "BUY":
            cash_effect = -notional
        elif side == "SELL":
            cash_effect = notional
        else:
            return {
                "schema_version": "runtime_v2_pre_commit_execution_cash_feasibility.v1",
                "status": "REVIEW_REQUIRED",
                "reason": f"candidate execution side invalid: {side}",
                "business_date": business_date,
                "current_state_path": str(state_path),
                "starting_cash": starting_cash,
                "persistent_execution_commit_allowed": False,
            }
        already_applied = bool(
            (execution_id and execution_id in applied_execution_keys)
            or (dedup_key and dedup_key in applied_execution_keys)
        )
        selected = not already_applied
        if already_applied:
            already_applied_count += 1
        else:
            selected_count += 1
            cash += cash_effect
            if side == "BUY":
                buy_notional += notional
            elif side == "SELL":
                sell_notional += notional
        items.append(
            {
                "symbol": str(getattr(execution, "symbol", "") or ""),
                "side": side,
                "quantity": quantity,
                "actual_candidate_execution_price": price,
                "actual_candidate_notional": notional,
                "cash_effect_if_selected": cash_effect,
                "execution_id": execution_id,
                "dedup_key": dedup_key,
                "already_applied": already_applied,
                "selected_into_candidate_projection": selected,
            }
        )
    status = "PASS" if cash >= -0.000001 else "REVIEW_REQUIRED"
    reason = (
        "pre_commit_execution_cash_feasibility_pass"
        if status == "PASS"
        else f"candidate execution cash projection negative: {cash}"
    )
    return {
        "schema_version": "runtime_v2_pre_commit_execution_cash_feasibility.v1",
        "status": status,
        "reason": reason,
        "business_date": business_date,
        "current_state_path": str(state_path),
        "starting_cash": starting_cash,
        "aggregate_candidate_buy_notional": buy_notional,
        "aggregate_candidate_sell_notional": sell_notional,
        "candidate_projected_cash": cash,
        "candidate_execution_count": len(items),
        "selected_candidate_execution_count": selected_count,
        "already_applied_candidate_execution_count": already_applied_count,
        "items": items,
        "persistent_execution_commit_allowed": status == "PASS",
    }


def _current_applied_execution_keys(current_state: dict[str, Any]) -> set[str]:
    projection = current_state.get("runtime_owned_projection") or {}
    raw_values = (
        *(projection.get("applied_execution_ids") or ()),
        *(projection.get("applied_execution_dedup_keys") or ()),
        *(current_state.get("applied_execution_ids") or ()),
        *(current_state.get("applied_execution_dedup_keys") or ()),
        *(current_state.get("execution_references") or ()),
    )
    return {str(value) for value in raw_values if str(value)}


def _historical_position_transition_records(
    *,
    runtime_root: Path,
    business_date: str,
    as_of: str,
    executions: Iterable[LedgerExecutionRecord],
    broker_position_symbols: tuple[str, ...] = (),
) -> tuple[tuple[LedgerPositionRecord, ...], tuple[str, ...]]:
    state = _load_json_dict(runtime_root / "persistent_ledger" / "state.json")
    current_positions = {
        str(row.get("symbol") or "").strip(): row
        for row in state.get("positions") or ()
        if str(row.get("symbol") or "").strip()
    }
    records: list[LedgerPositionRecord] = []
    errors: list[str] = []
    broker_symbols = {str(symbol).strip() for symbol in broker_position_symbols if str(symbol).strip()}
    existing_execution_keys = _existing_dedup_keys(runtime_root / "persistent_ledger" / "executions.jsonl")
    for execution in executions:
        if execution.side.upper() != "SELL":
            continue
        symbol = str(execution.symbol).strip()
        if symbol in broker_symbols:
            continue
        current = current_positions.get(symbol)
        if current is None:
            if execution.dedup_key and execution.dedup_key in existing_execution_keys:
                continue
            errors.append(f"current_position_missing:{symbol}")
            continue
        current_quantity = _float(current.get("quantity"))
        executed_quantity = float(execution.filled_quantity or execution.quantity or 0.0)
        if executed_quantity > current_quantity:
            errors.append(f"executed_quantity_exceeds_current:{symbol}")
            continue
        remaining_quantity = max(current_quantity - executed_quantity, 0.0)
        average_price = _float(current.get("average_price"))
        current_market_value = _float(current.get("market_value"))
        market_price = current_market_value / current_quantity if current_quantity else average_price
        market_value = remaining_quantity * market_price
        transition_id = f"historical-position-transition:{business_date}:{symbol}:{execution.execution_id}"
        records.append(
            LedgerPositionRecord(
                record_id=f"ledger-position-transition-{_short_hash(transition_id)}",
                record_type="position",
                schema_version="1",
                environment="historical",
                source="runtime_v2_execution_readonly_simulation",
                created_at=as_of,
                dedup_key=transition_id,
                review_required=True,
                production_equivalent=False,
                position_key=symbol,
                symbol=symbol,
                quantity=remaining_quantity,
                average_price=average_price,
                market_value=market_value,
                as_of=business_date,
                position_campaign_id=str(current.get("position_campaign_id") or current.get("campaign_id") or execution.position_campaign_id or ""),
            )
        )
    return tuple(records), tuple(errors)


def _runtime_order_payload(order: dict[str, Any]) -> dict[str, Any]:
    status = str(order.get("status") or order.get("order_status") or "")
    return {
        "order_id": order.get("order_id_hash") or order.get("order_id") or order.get("order_ref") or _stable_json_ref(order),
        "pending_plan_id": order.get("pending_plan_id") or "",
        "pending_item_id": order.get("pending_item_id") or "",
        "strategy_authority_lineage": order.get("strategy_authority_lineage") or {},
        "strategy_authority_lineage_hash": order.get("strategy_authority_lineage_hash") or "",
        "source_decision_id": order.get("source_decision_id") or order.get("source_pm_decision_id") or "",
        "source_pm_decision_id": order.get("source_pm_decision_id") or "",
        "source_decision_type": order.get("source_decision_type") or "",
        "source_pm_business_date": order.get("source_pm_business_date") or "",
        "source_position_symbol": order.get("source_position_symbol") or "",
        "position_campaign_id": order.get("position_campaign_id") or "",
        "symbol": order.get("issue_code") or order.get("symbol") or "",
        "side": _normalize_side(str(order.get("side") or "")),
        "quantity": _float(order.get("quantity")),
        "order_status": _normalize_order_status(status),
        "filled_quantity": _float(order.get("executed_quantity") or order.get("filled_quantity")),
        "remaining_quantity": _float(order.get("remaining_quantity")),
        "accepted_at": str(order.get("order_datetime") or order.get("accepted_at") or ""),
        "updated_at": str(order.get("as_of") or order.get("updated_at") or ""),
    }


def _historical_mixed_item_lifecycle_authority(
    *,
    runtime_root: Path,
    business_date: str,
    mode: str,
    orders: Iterable[Any],
) -> dict[str, Any]:
    if mode != "historical":
        return {"status": "NOT_APPLICABLE", "reason": "not_historical"}
    pending_payload = _load_json_optional(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    pending_items = pending_payload.get("items") if isinstance(pending_payload.get("items"), list) else []
    if not pending_items:
        return {"status": "NOT_APPLICABLE", "reason": "pending_items_missing"}
    if str(pending_payload.get("target_session_date") or "") != business_date:
        return {"status": "NOT_APPLICABLE", "reason": "target_session_date_not_current_business_date"}
    submit = _latest_submit_manifest(runtime_root=runtime_root, business_date=business_date)
    if submit is None:
        return {"status": "NOT_APPLICABLE", "reason": "submit_manifest_missing"}
    submit_path, submit_payload = submit
    if str(submit_payload.get("final_state") or "") == "POST_SEND_UNKNOWN":
        return {"status": "REVIEW_REQUIRED", "reason": "post_send_unknown"}
    submitted_count = _int_value(submit_payload.get("submitted_count"), 0)
    blocked_count = _int_value(submit_payload.get("blocked_count"), 0)
    if submitted_count <= 0 or blocked_count <= 0:
        return {"status": "NOT_APPLICABLE", "reason": "not_mixed_submitted_and_blocked"}
    continuation_path = _historical_quarantine_continuation_path(submit_payload, business_date)
    continuation = _load_json_optional(continuation_path)
    base_checks = _historical_mixed_item_lifecycle_checks(
        submit_payload=submit_payload,
        continuation=continuation,
        business_date=business_date,
        submit_manifest_path=submit_path,
    )
    item_outcomes = _derive_mixed_item_outcomes(
        pending_items=pending_items,
        submit_payload=submit_payload,
        continuation=continuation,
        orders=tuple(orders),
    )
    terminal_count = sum(1 for item in item_outcomes if bool(item.get("terminal")))
    broker_uncertain = any(bool(item.get("broker_uncertainty")) for item in item_outcomes)
    checks = {
        **base_checks,
        "all_items_classified": len(item_outcomes) == len(pending_items) > 0,
        "all_items_terminal": terminal_count == len(pending_items) > 0,
        "no_broker_uncertainty": not broker_uncertain,
        "has_filled_item": any(str(item.get("outcome") or "") == "FILLED" for item in item_outcomes),
        "has_quarantined_not_submitted_item": any(
            str(item.get("outcome") or "") == "QUARANTINED_NOT_SUBMITTED" for item in item_outcomes
        ),
        "no_unresolved_review_required_item": not any(
            str(item.get("outcome") or "") == "REVIEW_REQUIRED" for item in item_outcomes
        ),
    }
    if not all(checks.values()):
        return {
            "status": "NOT_APPLICABLE",
            "reason": "historical_mixed_item_lifecycle_checks_failed",
            "checks": checks,
            "item_outcomes": item_outcomes,
            "submit_manifest_path": str(submit_path),
            "continuation_path": str(continuation_path),
        }
    return {
        "status": "PASS",
        "reason": "historical_mixed_filled_and_ca_quarantined_items_terminal",
        "checks": checks,
        "item_outcomes": item_outcomes,
        "submit_manifest_path": str(submit_path),
        "continuation_path": str(continuation_path),
        "derived_plan_state": "CONSUMED",
    }


def _historical_mixed_item_lifecycle_checks(
    *,
    submit_payload: dict[str, Any],
    continuation: dict[str, Any],
    business_date: str,
    submit_manifest_path: Path,
) -> dict[str, bool]:
    prohibited = submit_payload.get("prohibited_actions") if isinstance(submit_payload.get("prohibited_actions"), dict) else {}
    continuation_checks = continuation.get("checks") if isinstance(continuation.get("checks"), dict) else {}
    text = json.dumps(submit_payload, ensure_ascii=False)
    return {
        "mode_historical": _manifest_indicates_historical(submit_payload),
        "same_business_date": str(submit_payload.get("business_date") or "") == business_date,
        "submit_review_required": str(submit_payload.get("final_state") or "") == "REVIEW_REQUIRED",
        "submitted_count_positive": _int_value(submit_payload.get("submitted_count"), 0) > 0,
        "blocked_count_positive": _int_value(submit_payload.get("blocked_count"), 0) > 0,
        "no_post_send_unknown": "POST_SEND_UNKNOWN" not in text,
        "no_broker_write": (
            not bool(submit_payload.get("broker_write"))
            and not bool(submit_payload.get("external_delivery"))
            and not bool(prohibited.get("demo_submit_executed"))
            and not bool(prohibited.get("production_order_executed"))
            and not bool(prohibited.get("broker_write"))
            and not bool(prohibited.get("external_delivery"))
        ),
        "continuation_artifact_present": bool(continuation),
        "continuation_status": str(continuation.get("status") or "") == "COMPLETED_WITH_SYMBOL_QUARANTINE",
        "continuation_business_date": str(continuation.get("business_date") or "") == business_date,
        "continuation_scope": str(continuation.get("scope") or "") == "CORPORATE_ACTION_SYMBOL_ONLY",
        "production_never": str(continuation.get("production_applicability") or "") == "NEVER",
        "run_continuation_historical_only": (
            str(continuation.get("corporate_action_run_continuation_eligibility") or "")
            == "ALLOWED_FOR_HISTORICAL_REPLAY_ONLY"
        ),
        "classifier_checks_pass": all(bool(value) for value in continuation_checks.values()) if continuation_checks else False,
        "continuation_runtime_manifest_bound": (
            str(continuation.get("runtime_manifest_path") or "") in {"", str(submit_manifest_path)}
            or Path(str(continuation.get("runtime_manifest_path") or "")).name == submit_manifest_path.name
            or str(continuation.get("runtime_manifest_path") or "").endswith(
                f"/daily/{business_date}/submit/runtime_manifest.json"
            )
        ),
    }


def _derive_mixed_item_outcomes(
    *,
    pending_items: list[Any],
    submit_payload: dict[str, Any],
    continuation: dict[str, Any],
    orders: tuple[Any, ...],
) -> list[dict[str, Any]]:
    guard_items = submit_payload.get("submit_guard_item_evidence")
    guard_items = guard_items if isinstance(guard_items, list) else []
    affected_symbols = {str(symbol).strip().upper() for symbol in continuation.get("affected_symbols") or () if str(symbol).strip()}
    outcomes: list[dict[str, Any]] = []
    for item in pending_items:
        if not isinstance(item, dict):
            continue
        pending_item_id = str(item.get("pending_item_id") or "")
        symbol = str(item.get("symbol") or "").strip().upper()
        side = str(item.get("side") or "").strip().upper()
        quantity = _float(item.get("quantity"))
        guard = next((guard_item for guard_item in guard_items if str(guard_item.get("pending_item_id") or "") == pending_item_id), {})
        base = {
            "pending_item_id": pending_item_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "terminal": False,
            "broker_uncertainty": False,
            "source": "",
        }
        if _is_ca_quarantine_guard_item(guard) and symbol in affected_symbols:
            outcomes.append(
                {
                    **base,
                    "outcome": "QUARANTINED_NOT_SUBMITTED",
                    "terminal": True,
                    "source": "submit_guard_historical_corporate_action_quarantine",
                }
            )
            continue
        order = _matching_filled_order(
            orders=orders,
            pending_item_id=pending_item_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
        )
        if order is not None:
            outcomes.append(
                {
                    **base,
                    "outcome": "FILLED",
                    "terminal": True,
                    "source": "execution_orderlist_full_fill",
                    "order_id": str(getattr(order, "order_ref_hash", "") or ""),
                    "filled_quantity": float(getattr(order, "filled_quantity", 0.0) or 0.0),
                }
            )
            continue
        if str(guard.get("submit_item_status") or "") == "PASS":
            outcomes.append({**base, "outcome": "REVIEW_REQUIRED", "source": "submitted_item_fill_not_confirmed"})
            continue
        outcomes.append({**base, "outcome": "REVIEW_REQUIRED", "source": "unclassified_submit_item"})
    return outcomes


def _is_ca_quarantine_guard_item(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    return (
        str(item.get("submit_item_status") or "") == "REVIEW_REQUIRED"
        and str(item.get("guard_decision") or "") == "BLOCKED"
        and str(item.get("guard_reason") or item.get("blocked_at_submit_reason") or "") == "corporate_action_event_not_resolved"
        and str(item.get("violated_policy") or "") == "historical_corporate_action_symbol_quarantine"
        and str(item.get("submit_status") or "NOT_SUBMITTED") in {"", "NOT_SUBMITTED"}
    )


def _matching_filled_order(
    *,
    orders: tuple[Any, ...],
    pending_item_id: str,
    symbol: str,
    side: str,
    quantity: float,
) -> Any | None:
    for order in orders:
        order_pending_item_id = str(getattr(order, "pending_item_id", "") or "")
        order_symbol = str(getattr(order, "symbol", "") or "").strip().upper()
        order_side = str(getattr(order, "side", "") or "").strip().upper()
        order_quantity = float(getattr(order, "quantity", 0.0) or 0.0)
        filled_quantity = float(getattr(order, "filled_quantity", 0.0) or 0.0)
        remaining_quantity = float(getattr(order, "remaining_quantity", 0.0) or 0.0)
        order_status = str(getattr(order, "order_status", "") or "").lower()
        id_match = bool(pending_item_id and order_pending_item_id == pending_item_id)
        symbol_match = order_symbol == symbol and order_side == side and abs(order_quantity - quantity) < 0.000001
        if (id_match or symbol_match) and filled_quantity > 0 and remaining_quantity == 0 and order_status == "filled":
            return order
    return None


def _load_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _runtime_execution_payload(execution: dict[str, Any]) -> dict[str, Any]:
    return {
        "execution_id": execution.get("execution_id") or execution.get("execution_ref") or _stable_json_ref(execution),
        "order_id": execution.get("order_id_hash") or execution.get("order_id") or execution.get("order_ref") or "",
        "execution_key": execution.get("execution_key") or "",
        "strategy_authority_lineage": execution.get("strategy_authority_lineage") or {},
        "strategy_authority_lineage_hash": execution.get("strategy_authority_lineage_hash") or "",
        "source_decision_id": execution.get("source_decision_id") or execution.get("source_pm_decision_id") or "",
        "source_pm_decision_id": execution.get("source_pm_decision_id") or "",
        "source_decision_type": execution.get("source_decision_type") or "",
        "source_pm_business_date": execution.get("source_pm_business_date") or "",
        "source_position_symbol": execution.get("source_position_symbol") or "",
        "position_campaign_id": execution.get("position_campaign_id") or "",
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


def _write_current_projection_payload(path: Path, payload: dict[str, Any]) -> None:
    if _is_mode_rooted_runtime_path(path):
        raise ValueError("Current projection writer does not write mode-rooted runtime paths")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


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


def _execution_transaction_id(
    *,
    business_date: str,
    ledger_orders: tuple[object, ...],
    ledger_executions: tuple[object, ...],
    ledger_positions: tuple[object, ...],
    ledger_cash: tuple[object, ...],
    ledger_events: tuple[object, ...],
) -> str:
    payload = {
        "business_date": business_date,
        "orders": _record_dedup_keys(ledger_orders),
        "executions": _record_dedup_keys(ledger_executions),
        "positions": _record_dedup_keys(ledger_positions),
        "cash": _record_dedup_keys(ledger_cash),
        "events": _record_dedup_keys(ledger_events),
    }
    return "execution-tx-" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _record_dedup_keys(records: tuple[object, ...]) -> tuple[str, ...]:
    keys: list[str] = []
    for record in records:
        payload = record if isinstance(record, dict) else ledger_record_to_payload(record)
        key = str(payload.get("dedup_key") or payload.get("record_id") or "")
        if key:
            keys.append(key)
    return tuple(sorted(keys))


def _payload_hash(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


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
                position_campaign_id=str(item.get("position_campaign_id") or item.get("campaign_id") or ""),
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
    pending_read_valid: bool = False,
    pending_classification: str = "",
    pending_active: bool | None = None,
    pending_plan_present: bool = False,
    pending_item_count: int = 0,
    no_action_reason: str = "",
    submit_authority_status: str = "",
    submit_action: str = "",
    submit_authority_path: str = "",
    submit_authority_reason: str = "",
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
        execution_action="BLOCKED" if status in {"BLOCKED", "HALT"} else "NOT_EXECUTED",
        orderlist_required=True,
        orderlist_status="NOT_EVALUATED",
        submitted_order_count=0,
        fill_count=0,
        pending_terminalization_status="NOT_EVALUATED",
        pending_consumed=False,
        pending_mutated=False,
        pending_read_valid=pending_read_valid,
        pending_classification=pending_classification,
        pending_active=pending_active,
        pending_plan_present=pending_plan_present,
        pending_item_count=pending_item_count,
        no_action_reason=no_action_reason,
        submit_authority_status=submit_authority_status,
        submit_action=submit_action,
        submit_authority_path=submit_authority_path,
        submit_authority_reason=submit_authority_reason,
    )
