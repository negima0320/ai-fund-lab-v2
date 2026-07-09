"""Runtime v2 simulation harness built from existing Runtime v2 components."""

from __future__ import annotations

import hashlib
from dataclasses import replace

from ai_fund_lab_v2.runtime_v2.approval.models import (
    ApprovalArtifact,
    ApprovalStatus,
)
from ai_fund_lab_v2.runtime_v2.asset.builder import build_current_asset_state
from ai_fund_lab_v2.runtime_v2.audit.auditor import run_audit
from ai_fund_lab_v2.runtime_v2.execution.fill_classifier import classify_fill
from ai_fund_lab_v2.runtime_v2.execution.ledger_projection import (
    project_cash_to_ledger_record,
    project_execution_to_ledger_record,
    project_order_to_ledger_record,
    project_position_to_ledger_record,
)
from ai_fund_lab_v2.runtime_v2.ledger.append import append_record
from ai_fund_lab_v2.runtime_v2.ledger.models import (
    LedgerCashRecord,
    LedgerExecutionRecord,
    LedgerOrderRecord,
    LedgerPositionRecord,
)
from ai_fund_lab_v2.runtime_v2.notification.payload import build_notification_payload
from ai_fund_lab_v2.runtime_v2.pending.consume import can_submit_pending_plan, consume_pending_plan
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.planning.models import (
    AIPlanningSignal,
    CapitalAllocationSignal,
    PlanningInput,
    SafetySignal,
)
from ai_fund_lab_v2.runtime_v2.planning.planner import build_order_plan
from ai_fund_lab_v2.runtime_v2.reconcile.reconciler import run_reconciliation
from ai_fund_lab_v2.runtime_v2.report.builder import build_runtime_report
from ai_fund_lab_v2.runtime_v2.report.models import ReportBuildInput
from ai_fund_lab_v2.runtime_v2.simulation.broker import SimulationBroker
from ai_fund_lab_v2.runtime_v2.simulation.models import (
    SimulationBrokerPosition,
    SimulationBrokerState,
    SimulationDayResult,
    SimulationOrderInstruction,
    SimulationReplayResult,
)


def run_simulation_replay(
    *,
    initial_state: SimulationBrokerState,
    instructions: tuple[SimulationOrderInstruction, ...],
    mode: str = "simulation",
    environment: str = "simulation",
) -> SimulationReplayResult:
    broker = SimulationBroker(initial_state)
    ledger_orders: tuple[LedgerOrderRecord, ...] = ()
    ledger_executions: tuple[LedgerExecutionRecord, ...] = ()
    latest_position_records: tuple[LedgerPositionRecord, ...] = ()
    latest_cash_records: tuple[LedgerCashRecord, ...] = ()
    day_results: list[SimulationDayResult] = []

    for instruction in instructions:
        before_bundle = broker.snapshot(business_date=instruction.business_date)
        before_positions = tuple(project_position_to_ledger_record(item) for item in before_bundle.positions)
        before_cash = (project_cash_to_ledger_record(before_bundle.cash),) if before_bundle.cash else ()
        asset_before = build_current_asset_state(
            environment=environment,
            positions=before_positions,
            cash_records=before_cash,
            source="simulation_broker",
            as_of=instruction.business_date,
        )
        planning_result = build_order_plan(
            PlanningInput(
                mode=mode,
                environment=environment,
                business_date=instruction.business_date,
                target_session_date=instruction.business_date,
                asset_state=asset_before,
                ai_signals=(
                    AIPlanningSignal(
                        signal_id=f"signal-{instruction.business_date}-{instruction.side}-{instruction.symbol}",
                        symbol=instruction.symbol,
                        side=instruction.side,
                        rank=1,
                        score=1.0,
                        reason="simulation replay instruction",
                        source_ai="simulation_replay",
                    ),
                ),
                capital_allocations=(
                    CapitalAllocationSignal(
                        allocation_id=f"allocation-{instruction.business_date}-{instruction.side}-{instruction.symbol}",
                        symbol=instruction.symbol,
                        side=instruction.side,
                        allocated_amount=instruction.quantity * instruction.price,
                        max_amount=instruction.quantity * instruction.price,
                        cash_required=instruction.quantity * instruction.price if instruction.side == "BUY" else 0.0,
                        reason="simulation allocation",
                    ),
                ),
                safety_signals=(
                    SafetySignal(
                        safety_id=f"safety-{instruction.business_date}-{instruction.side}-{instruction.symbol}",
                        symbol=instruction.symbol,
                        side=instruction.side,
                        allowed=True,
                        review_required=False,
                        blocked=False,
                        reason="simulation safety pass",
                    ),
                ),
            )
        )
        pending_item_id = instruction.pending_item_id or f"pending-item-{instruction.business_date}-{instruction.side}-{instruction.symbol}"
        pending_item = PendingOrderItem(
            pending_item_id=pending_item_id,
            symbol=instruction.symbol,
            side=instruction.side,
            quantity=instruction.quantity,
            order_type=instruction.order_type,
            estimated_price=instruction.price,
            estimated_amount=instruction.quantity * instruction.price,
            approved=False,
            state="PENDING_APPROVAL",
        )
        pending_plan = promote_order_plan_to_pending(
            order_plan_id=planning_result.order_plan.order_plan_id,
            source_order_plan_path=f"order_plan/{instruction.business_date}.json",
            source_order_plan_hash=_hash(planning_result.order_plan.order_plan_id),
            environment=environment,
            plan_created_date=instruction.business_date,
            intended_submit_date=instruction.business_date,
            target_session_date=instruction.business_date,
            items=(pending_item,),
        )
        approval = ApprovalArtifact(
            approval_id=f"approval-{pending_plan.pending_plan_id}",
            approval_request_id=f"approval-request-{pending_plan.pending_plan_id}",
            pending_plan_id=pending_plan.pending_plan_id,
            order_plan_id=planning_result.order_plan.order_plan_id,
            status=ApprovalStatus.APPROVED,
            approved_item_ids=(pending_item_id,),
            rejected_item_ids=(),
            approval_hash=_hash(pending_plan.pending_plan_id),
            approved_at=instruction.business_date,
            expires_at=instruction.business_date,
            review_required=False,
            reason="simulation approval",
        )
        from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending

        pending_plan = link_approval_to_pending(pending_plan=pending_plan, approval_artifact=approval)
        approved_item = next(item for item in pending_plan.items if item.pending_item_id == pending_item_id)
        existing_dedup_keys = {order.pending_item_id for order in ledger_orders}
        submit_allowed = can_submit_pending_plan(pending_plan, existing_dedup_keys)
        submit_result = broker.submit(
            pending_plan_id=pending_plan.pending_plan_id,
            item=approved_item,
            business_date=instruction.business_date,
        ) if submit_allowed else None

        after_bundle = broker.snapshot(business_date=instruction.business_date)
        day_broker_orders = tuple(order for order in after_bundle.orders if order.pending_plan_id == pending_plan.pending_plan_id)
        day_broker_executions = tuple(execution for execution in after_bundle.executions if any(execution.order_ref_hash == order.order_ref_hash for order in day_broker_orders))
        fill_classification = "BLOCKED"
        day_ledger_orders: tuple[LedgerOrderRecord, ...] = ()
        day_ledger_executions: tuple[LedgerExecutionRecord, ...] = ()
        if submit_result and submit_result.submitted:
            for order in day_broker_orders:
                fill_classification = classify_fill(order=order, executions=day_broker_executions).classification.value
                order_record = project_order_to_ledger_record(order)
                ledger_orders = append_record(ledger_orders, order_record)  # type: ignore[assignment]
                day_ledger_orders = append_record(day_ledger_orders, order_record)  # type: ignore[assignment]
            for execution in day_broker_executions:
                execution_record = project_execution_to_ledger_record(execution)
                ledger_executions = append_record(ledger_executions, execution_record)  # type: ignore[assignment]
                day_ledger_executions = append_record(day_ledger_executions, execution_record)  # type: ignore[assignment]
            pending_plan = replace(pending_plan, state=PendingPlanState.SUBMITTED)
            pending_plan = consume_pending_plan(
                pending_plan,
                consume_reason="simulation submit accepted",
                submitted_order_ids=tuple(order.order_ref_hash for order in day_broker_orders),
                ledger_order_record_ids=tuple(order.record_id for order in day_ledger_orders),
            )

        latest_position_records = tuple(project_position_to_ledger_record(item) for item in after_bundle.positions)
        latest_cash_records = (project_cash_to_ledger_record(after_bundle.cash),) if after_bundle.cash else ()
        asset_state = build_current_asset_state(
            environment=environment,
            positions=latest_position_records,
            cash_records=latest_cash_records,
            source="simulation_broker",
            as_of=instruction.business_date,
        )
        reconciliation = run_reconciliation(
            mode=mode,
            environment=environment,
            business_date=instruction.business_date,
            pending_plan=pending_plan,
            ledger_orders=day_ledger_orders,
            ledger_executions=day_ledger_executions,
            broker_orders=day_broker_orders,
            broker_executions=day_broker_executions,
            broker_positions=after_bundle.positions,
            broker_cash=after_bundle.cash,
            asset_state=asset_state,
        )
        report = build_runtime_report(
            ReportBuildInput(
                mode=mode,
                environment=environment,
                business_date=instruction.business_date,
                target_session_date=instruction.business_date,
                asset_state=asset_state,
                pending_plan=pending_plan,
                ledger_orders=day_ledger_orders,
                ledger_executions=day_ledger_executions,
                ledger_positions=latest_position_records,
                ledger_cash_records=latest_cash_records,
                broker_orders=day_broker_orders,
                broker_executions=day_broker_executions,
                broker_positions=after_bundle.positions,
                broker_cash=after_bundle.cash,
                planning_result=planning_result,
                approval_artifact=approval,
                reconciliation_result=reconciliation,
            )
        )
        payload = build_notification_payload(report=report, channel="simulation")
        audit = run_audit(
            mode=mode,
            environment=environment,
            business_date=instruction.business_date,
            report=report,
            notification_payload=payload,
            reconciliation_result=reconciliation,
            asset_state=asset_state,
        )
        final_positions = tuple(
            SimulationBrokerPosition(
                symbol=position.symbol,
                quantity=position.quantity,
                average_price=position.average_price,
                market_value=position.market_value,
            )
            for position in (asset_state.positions or ())
        )
        day_results.append(
            SimulationDayResult(
                business_date=instruction.business_date,
                order_side=instruction.side,
                submit_status=(submit_result.status if submit_result else "BLOCKED"),
                blocked=(submit_result.blocked if submit_result else True),
                review_required=(submit_result.review_required if submit_result else False),
                pending_state=pending_plan.state.value,
                fill_classification=fill_classification,
                ledger_order_count=len(day_ledger_orders),
                ledger_execution_count=len(day_ledger_executions),
                ledger_position_count=len(latest_position_records),
                ledger_cash_count=len(latest_cash_records),
                asset_cash=asset_state.cash,
                asset_buying_power=asset_state.buying_power,
                asset_positions=final_positions,
                realized_pnl=(submit_result.realized_pnl if submit_result else None),
                reconciliation_findings=len(reconciliation.findings),
                report_sections=len(report.sections),
                notification_payload_created=payload is not None,
                audit_findings=len(audit.findings),
            )
        )

    return SimulationReplayResult(
        status="PASS",
        mode=mode,
        environment=environment,
        day_results=tuple(day_results),
        ledger_order_count=len(ledger_orders),
        ledger_execution_count=len(ledger_executions),
        final_cash=day_results[-1].asset_cash if day_results else initial_state.cash,
        final_positions=day_results[-1].asset_positions if day_results else initial_state.positions,
    )


def _hash(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()
