"""Runtime v2 SELL planning pipeline from Current Position to Pending."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalDecision, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.approval.policy import (
    build_approval_artifact,
    build_approval_request,
    build_approved_order_conditions,
)
from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetPosition, CurrentAssetState
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingOrderPlan, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.composition import compose_with_existing_buy_pending, read_active_buy_pending
from ai_fund_lab_v2.runtime_v2.pending.no_order_authority import materialize_empty_pending_no_order_authority
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.safety_authority import (
    HISTORICAL_NEUTRAL_SAFETY_POLICY_VERSION,
    HISTORICAL_NEUTRAL_SAFETY_SOURCE,
    materialize_historical_pending_safety_context,
)
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import CapitalDeploymentPolicy, capital_deployment_policy_hash
from ai_fund_lab_v2.runtime_v2.cash_exposure_authority import resolve_cash_exposure_authority
from ai_fund_lab_v2.runtime_v2.position_sizing_authority import resolve_position_sizing_authority
from ai_fund_lab_v2.runtime_v2.planning.add_consumer import AddConsumerResult, build_add_pending_items
from ai_fund_lab_v2.runtime_v2.planning.models import AIPlanningSignal, CapitalAllocationSignal, PlanningInput, RuntimeSafetyContext
from ai_fund_lab_v2.runtime_v2.planning.planner import build_order_plan
from ai_fund_lab_v2.runtime_v2.safety_decision import (
    RuntimeSafetyDecision,
    load_runtime_safety_decision,
    safety_allows_action,
    safety_manifest_fields,
)
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import load_runtime_current_exposure
from ai_fund_lab_v2.runtime_v2.symbol_identity import same_symbol_identity


@dataclass(frozen=True)
class SellExitDecision:
    symbol: str
    quantity: float
    reason: str
    score: float = 1.0
    source_decision: str = "EXIT"
    reduce_intensity: str = ""
    source_decision_artifact: str = ""
    source_decision_id: str = ""
    quantity_contract: dict[str, Any] | None = None


REDUCE_QUANTITY_CONTRACT_VERSION = "runtime_v2_pm_reduce_quantity_v1"
DEFAULT_TRADABLE_UNIT = 100.0
REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY_REASON = "REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY"
REDUCE_INTENSITY_RATIOS: dict[str, float] = {
    "LIGHT": 0.25,
    "MEDIUM": 0.33,
    "STRONG": 0.50,
}


@dataclass(frozen=True)
class SellPlanningPipelineResult:
    status: str
    reason: str
    current_position_count: int
    selected_count: int
    blocked_count: int
    pending_path: str
    pending_plan_id: str
    approval_artifact_path: str
    order_plan_artifact_path: str
    target_session_date: str
    selected_symbols: tuple[str, ...]
    current_exposure: float
    safety_decision_id: str = ""
    safety_policy_version: str = ""
    safety_source: str = ""
    safety_decision: str = ""
    safety_reason: str = ""
    safety_status: str = ""
    safety_block_buy: bool = False
    safety_block_sell: bool = False
    safety_halt_runtime: bool = False
    pending_composition_model: str = ""
    pending_composition_status: str = ""
    preserved_existing_buy_pending: bool = False
    composite_pending: bool = False
    add_consumer_status: str = ""
    add_consumer_reason: str = ""
    add_accepted_count: int = 0
    add_rejected_count: int = 0

    def to_stage_details(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["selected_symbols"] = list(self.selected_symbols)
        return payload


@dataclass(frozen=True)
class SellPlanningCapabilityDecision:
    status: str
    reason: str
    runtime_mode: str
    broker_environment: str
    historical_replay: bool
    simulation: bool
    broker_write: bool
    external_delivery: bool
    tachibana_demo_write: bool
    tachibana_production_write: bool
    submit_enabled: bool
    runtime_test_run_id_present: bool
    runtime_test_profile_id: str
    runtime_test_evidence_root_present: bool
    allowed_processing: tuple[str, ...]
    prohibited_external_effects: tuple[str, ...]
    failed_checks: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_processing"] = list(self.allowed_processing)
        payload["prohibited_external_effects"] = list(self.prohibited_external_effects)
        payload["failed_checks"] = list(self.failed_checks)
        return payload


HISTORICAL_ALLOWED_SELL_PLANNING_PROCESSING: tuple[str, ...] = (
    "data_readiness",
    "position_management_ai",
    "sell_planning",
    "historical_approval_policy",
    "pending_continuity_check",
    "run_scoped_evidence",
)

HISTORICAL_PROHIBITED_SELL_PLANNING_EXTERNAL_EFFECTS: tuple[str, ...] = (
    "tachibana_demo_api_write",
    "tachibana_production_api_write",
    "broker_order_api_call",
    "demo_submit",
    "production_submit",
    "external_notification_delivery",
    "line_send",
    "discord_send",
    "production_access",
)


def evaluate_sell_planning_capability(
    *,
    mode: str,
    context: dict[str, Any] | None = None,
) -> SellPlanningCapabilityDecision:
    if mode in {"demo", "production"}:
        return SellPlanningCapabilityDecision(
            status="PASS",
            reason=f"{mode}_sell_planning_capability_ready",
            runtime_mode=mode,
            broker_environment=str((context or {}).get("broker_environment") or ("tachibana_demo" if mode == "demo" else "tachibana_production")),
            historical_replay=False,
            simulation=False,
            broker_write=bool((context or {}).get("broker_write")),
            external_delivery=bool((context or {}).get("external_delivery")),
            tachibana_demo_write=bool((context or {}).get("tachibana_demo_write")),
            tachibana_production_write=bool((context or {}).get("tachibana_production_write")),
            submit_enabled=bool((context or {}).get("submit_enabled")),
            runtime_test_run_id_present=bool((context or {}).get("runtime_test_run_id")),
            runtime_test_profile_id=str((context or {}).get("runtime_test_profile_id") or ""),
            runtime_test_evidence_root_present=bool((context or {}).get("runtime_test_evidence_root")),
            allowed_processing=("common_runtime_sell_planning_core",),
            prohibited_external_effects=(),
        )
    if mode != "historical" or not context:
        return _sell_planning_capability_block(
            mode=mode,
            context=context or {},
            reason="historical_sell_planning_capability_context_missing" if mode == "historical" else "unsupported_runtime_mode_for_sell_planning",
            failed_checks=("environment_capability_context_present",) if mode == "historical" else ("runtime_mode_supported",),
        )
    checks = {
        "runtime_mode_historical": str(context.get("runtime_mode") or mode) == "historical",
        "historical_replay_true": bool(context.get("historical_replay")) is True,
        "broker_environment_historical_simulated": str(context.get("broker_environment") or "") == "historical_simulated",
        "simulation_true": bool(context.get("simulation")) is True,
        "broker_write_false": bool(context.get("broker_write")) is False,
        "external_delivery_false": bool(context.get("external_delivery")) is False,
        "tachibana_demo_write_false": bool(context.get("tachibana_demo_write")) is False,
        "tachibana_production_write_false": bool(context.get("tachibana_production_write")) is False,
        "submit_enabled_false": bool(context.get("submit_enabled")) is False,
    }
    failed = tuple(name for name, passed in checks.items() if not passed)
    if failed:
        return _sell_planning_capability_block(
            mode=mode,
            context=context,
            reason="historical_sell_planning_capability_fail_closed:" + ",".join(failed),
            failed_checks=failed,
        )
    return SellPlanningCapabilityDecision(
        status="PASS",
        reason="historical_sell_planning_capability_ready",
        runtime_mode="historical",
        broker_environment="historical_simulated",
        historical_replay=True,
        simulation=True,
        broker_write=False,
        external_delivery=False,
        tachibana_demo_write=False,
        tachibana_production_write=False,
        submit_enabled=False,
        runtime_test_run_id_present=bool(str(context.get("runtime_test_run_id") or "")),
        runtime_test_profile_id=str(context.get("runtime_test_profile_id") or ""),
        runtime_test_evidence_root_present=bool(str(context.get("runtime_test_evidence_root") or "")),
        allowed_processing=HISTORICAL_ALLOWED_SELL_PLANNING_PROCESSING,
        prohibited_external_effects=HISTORICAL_PROHIBITED_SELL_PLANNING_EXTERNAL_EFFECTS,
    )


def _sell_planning_capability_block(
    *,
    mode: str,
    context: dict[str, Any] | None,
    reason: str,
    failed_checks: tuple[str, ...],
) -> SellPlanningCapabilityDecision:
    context = context or {}
    return SellPlanningCapabilityDecision(
        status="BLOCKED",
        reason=reason,
        runtime_mode=str(context.get("runtime_mode") or mode),
        broker_environment=str(context.get("broker_environment") or ""),
        historical_replay=bool(context.get("historical_replay")),
        simulation=bool(context.get("simulation")),
        broker_write=bool(context.get("broker_write")),
        external_delivery=bool(context.get("external_delivery")),
        tachibana_demo_write=bool(context.get("tachibana_demo_write")),
        tachibana_production_write=bool(context.get("tachibana_production_write")),
        submit_enabled=bool(context.get("submit_enabled")),
        runtime_test_run_id_present=bool(str(context.get("runtime_test_run_id") or "")),
        runtime_test_profile_id=str(context.get("runtime_test_profile_id") or ""),
        runtime_test_evidence_root_present=bool(str(context.get("runtime_test_evidence_root") or "")),
        allowed_processing=(),
        prohibited_external_effects=HISTORICAL_PROHIBITED_SELL_PLANNING_EXTERNAL_EFFECTS if mode == "historical" else (),
        failed_checks=failed_checks,
    )


def run_sell_planning_pending_pipeline(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    exit_decisions: tuple[SellExitDecision, ...],
    max_orders: int | None = None,
    capital_deployment_policy: CapitalDeploymentPolicy | None = None,
    submit_policy_context: Mapping[str, Any] | None = None,
    accepted_generation_binding: Mapping[str, Any] | None = None,
    safety_decision: RuntimeSafetyDecision | None = None,
    environment_capability_context: dict[str, Any] | None = None,
) -> SellPlanningPipelineResult:
    """Build SELL OrderPlan/Approval/Pending from Current positions only.

    The pipeline performs no Broker write. Exit AI output is represented by
    ``exit_decisions``; BUY candidates are never accepted as SELL sources.
    """

    capability_decision = evaluate_sell_planning_capability(
        mode=mode,
        context=environment_capability_context,
    )
    if capability_decision.status != "PASS":
        raise ValueError(capability_decision.reason)
    runtime_root_path = Path(runtime_root)
    _reject_mode_rooted_runtime_root(runtime_root_path)
    target_session_date = business_date
    canonical_submit_policy_context = _submit_policy_context(
        submit_policy_context,
        capital_deployment_policy=capital_deployment_policy,
    )
    runtime_safety_decision = safety_decision or load_runtime_safety_decision(
        runtime_root=runtime_root_path,
        business_date=business_date,
        mode=mode,
    )
    safety_allowed, safety_status, safety_reason = safety_allows_action(runtime_safety_decision, action="planning", side="SELL")
    if not safety_allowed:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            business_date=business_date,
            target_session_date=target_session_date,
            environment=mode,
            environment_capability_context=environment_capability_context,
            reason=safety_reason,
            current_position_count=0,
            current_exposure=0.0,
            status=safety_status,
            safety_decision=runtime_safety_decision,
        )
    asset_state = _load_asset_state(runtime_root_path / "persistent_ledger" / "state.json")
    current_positions = {
        str(position.symbol).strip(): position
        for position in asset_state.positions or ()
        if str(position.symbol).strip() and position.quantity > 0
    }
    current_exposure = float(sum(position.market_value for position in current_positions.values()))
    active_deployment_capital = _active_deployment_capital(asset_state, current_exposure=current_exposure)
    cash_exposure_authority = resolve_cash_exposure_authority(
        runtime_root=runtime_root_path,
        business_date=business_date,
        runtime_mode=mode,
        current_total_equity=active_deployment_capital,
        active_deployment_capital=active_deployment_capital,
        current_cash=_available_cash(asset_state),
        current_market_value=current_exposure,
        consumer="pm_add_cash_exposure",
    )
    position_sizing_authorities = {}
    for decision in exit_decisions:
        decision_symbol = str(decision.symbol or "").strip()
        if str(getattr(decision, "source_decision", "") or "").upper() != "ADD" or not decision_symbol:
            continue
        matched_position = _matching_position(current_positions, decision_symbol)
        authority_symbol = str(matched_position.symbol).strip() if matched_position is not None else decision_symbol
        position_sizing_authorities[decision_symbol] = resolve_position_sizing_authority(
            symbol=authority_symbol,
            runtime_root=runtime_root_path,
            business_date=business_date,
            runtime_mode=mode,
            active_deployment_capital=active_deployment_capital,
            selected_dynamic_exposure_ratio=cash_exposure_authority.selected_dynamic_exposure_ratio,
            selected_runtime_exposure_limit=cash_exposure_authority.selected_runtime_exposure_limit,
            selected_dynamic_position_count=None,
            current_position_market_value=0.0 if matched_position is None else float(matched_position.market_value),
            consumer="pm_add_position_sizing",
        )
    if not current_positions:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            business_date=business_date,
            target_session_date=target_session_date,
            environment=mode,
            environment_capability_context=environment_capability_context,
            reason="NO_SIGNAL:current_position_missing",
            current_position_count=0,
            current_exposure=current_exposure,
            safety_decision=runtime_safety_decision,
        )

    existing_buy_pending, existing_buy_pending_reason = read_active_buy_pending(
        runtime_root=runtime_root_path,
        environment=mode,
        business_date=business_date,
        target_session_date=target_session_date,
    )
    add_result = build_add_pending_items(
        add_decisions=exit_decisions,
        asset_state=asset_state,
        current_positions=current_positions,
        existing_buy_pending=existing_buy_pending,
        business_date=business_date,
        target_session_date=target_session_date,
        environment=mode,
        capital_deployment_policy=capital_deployment_policy,
        safety_decision=runtime_safety_decision,
        cash_exposure_authority=cash_exposure_authority,
        position_sizing_authorities=position_sizing_authorities,
    )
    prioritized_decisions = _apply_exit_priority(
        tuple(
            decision
            for decision in exit_decisions
            if str(decision.source_decision or "EXIT").upper() in {"EXIT", "REDUCE"}
        )
    )
    selected_decisions = tuple(prioritized_decisions[:max_orders])
    if not selected_decisions:
        if add_result.accepted_items:
            return _write_add_pending(
                runtime_root=runtime_root_path,
                business_date=business_date,
                target_session_date=target_session_date,
                environment=mode,
                environment_capability_context=environment_capability_context,
                current_position_count=len(current_positions),
                current_exposure=current_exposure,
                add_result=add_result,
                existing_buy_pending=existing_buy_pending,
                capital_deployment_policy=capital_deployment_policy,
                submit_policy_context=canonical_submit_policy_context,
                accepted_generation_binding=accepted_generation_binding,
                safety_decision=runtime_safety_decision,
            )
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            business_date=business_date,
            target_session_date=target_session_date,
            environment=mode,
            environment_capability_context=environment_capability_context,
            reason="NO_SIGNAL:exit_ai_no_sell_signal",
            current_position_count=len(current_positions),
            current_exposure=current_exposure,
            safety_decision=runtime_safety_decision,
            existing_buy_pending=existing_buy_pending,
            existing_buy_pending_reason=existing_buy_pending_reason,
            add_result=add_result,
        )

    pending_conflict = _pending_sell_conflict(
        runtime_root=runtime_root_path,
        symbols=tuple(decision.symbol for decision in selected_decisions),
    )
    if pending_conflict:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            business_date=business_date,
            target_session_date=target_session_date,
            environment=mode,
            environment_capability_context=environment_capability_context,
            reason="REVIEW_REQUIRED_REDUCE_PENDING_SELL_CONFLICT:" + ",".join(pending_conflict),
            current_position_count=len(current_positions),
            current_exposure=current_exposure,
            status="REVIEW_REQUIRED",
            safety_decision=runtime_safety_decision,
        )

    quantity_decisions = tuple(
        _quantity_contract_decision(
            decision=decision,
            position=_current_position_by_identity(current_positions, decision.symbol),
            runtime_root=runtime_root_path,
            mode=mode,
        )
        for decision in selected_decisions
    )
    non_executable_decisions = tuple(
        decision for decision in quantity_decisions if _is_non_executable_reduce_quantity_contract(decision.quantity_contract)
    )
    quantity_failures = tuple(
        decision
        for decision in quantity_decisions
        if decision.quantity <= 0 and not _is_non_executable_reduce_quantity_contract(decision.quantity_contract)
    )
    if quantity_failures:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            business_date=business_date,
            target_session_date=target_session_date,
            environment=mode,
            environment_capability_context=environment_capability_context,
            reason=";".join(str((decision.quantity_contract or {}).get("reason") or "reduce_quantity_contract_failed") for decision in quantity_failures),
            current_position_count=len(current_positions),
            current_exposure=current_exposure,
            status="REVIEW_REQUIRED",
            safety_decision=runtime_safety_decision,
        )
    executable_quantity_decisions = tuple(decision for decision in quantity_decisions if decision.quantity > 0)
    if not executable_quantity_decisions:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            business_date=business_date,
            target_session_date=target_session_date,
            environment=mode,
            environment_capability_context=environment_capability_context,
            reason=REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY_REASON,
            current_position_count=len(current_positions),
            current_exposure=current_exposure,
            status="PASS",
            safety_decision=runtime_safety_decision,
            non_executable_decisions=non_executable_decisions,
        )

    ai_signals = tuple(_ai_signal(decision, index) for index, decision in enumerate(executable_quantity_decisions, start=1))
    policy_context = _policy_context(capital_deployment_policy)
    allocations = tuple(
        _allocation(
            decision=decision,
            signal=signal,
            position=_current_position_by_identity(current_positions, decision.symbol),
            policy_context=policy_context,
        )
        for decision, signal in zip(executable_quantity_decisions, ai_signals)
    )
    planning_result = build_order_plan(
        PlanningInput(
            mode=mode,
            environment=mode,
            business_date=business_date,
            target_session_date=target_session_date,
            asset_state=asset_state,
            ai_signals=ai_signals,
            capital_allocations=allocations,
            runtime_safety=_runtime_safety_context(runtime_safety_decision),
        )
    )

    artifact_dir = _sell_artifact_dir(runtime_root_path, business_date)
    order_plan_path = artifact_dir / "order_plan.json"
    approval_path = artifact_dir / "approval_artifact.json"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    order_plan_payload = _jsonable(planning_result.order_plan)
    if non_executable_decisions:
        order_plan_payload["non_executable_sell_decisions"] = _non_executable_decision_payload(non_executable_decisions)
    if add_result.requested_count:
        order_plan_payload["pm_add_consumer"] = add_result.to_evidence()
    order_plan_path.write_text(_json_dumps(order_plan_payload), encoding="utf-8")
    sell_pending_items = tuple(
        _pending_item(item)
        for item in planning_result.order_plan.items
        if not item.blocked and not item.review_required and item.quantity > 0
    )
    pending_items = tuple(
        _pending_item_with_accepted_generation_binding(
            item=_pending_item_with_submit_policy_context(item=item, submit_policy_context=canonical_submit_policy_context),
            accepted_generation_binding=accepted_generation_binding,
        )
        for item in sell_pending_items + add_result.accepted_items
    )
    order_plan_payload["submit_policy_context"] = canonical_submit_policy_context or None
    order_plan_payload["submit_policy_version"] = str(canonical_submit_policy_context.get("submit_policy_version") or "")
    order_plan_payload["submit_policy_source"] = str(canonical_submit_policy_context.get("submit_policy_source") or "")
    order_plan_payload["submit_policy_hash"] = str(canonical_submit_policy_context.get("submit_policy_hash") or "")
    order_plan_payload["items"] = [_jsonable(item) for item in pending_items]
    order_plan_path.write_text(_json_dumps(order_plan_payload), encoding="utf-8")
    pending = promote_order_plan_to_pending(
        order_plan_id=planning_result.order_plan.order_plan_id,
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash=_hash(order_plan_path.read_text(encoding="utf-8")),
        environment=mode,
        plan_created_date=business_date,
        intended_submit_date=target_session_date,
        target_session_date=target_session_date,
        items=pending_items,
        submit_policy_context=canonical_submit_policy_context,
    )
    pending = _attach_accepted_generation_binding_to_pending(
        pending=pending,
        accepted_generation_binding=accepted_generation_binding,
    )
    pending = _attach_historical_safety_authority(
        pending=pending,
        business_date=business_date,
        safety_decision=runtime_safety_decision,
        environment_capability_context=environment_capability_context,
    )
    approved_item_ids = tuple(item.pending_item_id for item in pending.items)
    if approved_item_ids:
        request = build_approval_request(
            pending_plan=pending,
            business_date=business_date,
            expires_at=f"{business_date}T15:00:00+09:00",
        )
        approval = build_approval_artifact(
            request=request,
            decision=ApprovalDecision(
                status=ApprovalStatus.APPROVED,
                approved_item_ids=approved_item_ids,
                rejected_item_ids=(),
                reason="runtime v2 sell daily operation approval",
                operator="runtime_v2_sell_planning_job",
                decided_at=f"{business_date}T08:45:00+09:00",
                approved_order_conditions=build_approved_order_conditions(
                    pending_items=pending.items,
                    target_session_date=target_session_date,
                ),
            ),
        )
        approval_path.write_text(_json_dumps(_jsonable(approval)), encoding="utf-8")
        pending = link_approval_to_pending(
            pending_plan=pending,
            approval_artifact=approval,
            planning_submit_feasibility_current=load_runtime_current_exposure(
                runtime_root_path / "persistent_ledger" / "state.json"
            ),
            planning_submit_feasibility_policy=capital_deployment_policy,
        )
    else:
        approval_path.write_text(
            _json_dumps({"status": "NO_SIGNAL", "reason": "no pending SELL items after planning"}),
            encoding="utf-8",
        )

    pending, order_plan_path, approval_path, composition_evidence = compose_with_existing_buy_pending(
        existing_buy_pending=existing_buy_pending,
        pending=pending,
        artifact_dir=artifact_dir,
        business_date=business_date,
        target_session_date=target_session_date,
        environment=mode,
        reason="SELL Planning composed with active BUY Pending",
        planning_submit_feasibility_current=load_runtime_current_exposure(
            runtime_root_path / "persistent_ledger" / "state.json"
        ),
        planning_submit_feasibility_policy=capital_deployment_policy,
        accepted_generation_binding=accepted_generation_binding,
    )
    pending_path = runtime_root_path / "pending_order_plan" / "pending_order_plan.json"
    write_pending_order_plan(pending_path, pending)
    blocked_count = sum(1 for item in planning_result.order_plan.items if item.blocked)
    return SellPlanningPipelineResult(
        status="PASS" if pending_items else "REVIEW_REQUIRED",
        reason="" if pending_items else "no pending SELL/ADD items after planning",
        current_position_count=len(current_positions),
        selected_count=len(pending_items),
        blocked_count=blocked_count,
        pending_path=str(pending_path),
        pending_plan_id=pending.pending_plan_id,
        approval_artifact_path=str(approval_path),
        order_plan_artifact_path=str(order_plan_path),
        target_session_date=target_session_date,
        selected_symbols=tuple(item.symbol for item in pending.items),
        current_exposure=current_exposure,
        pending_composition_model=str(composition_evidence.get("composition_model") or ""),
        pending_composition_status=str(composition_evidence.get("composition_status") or ""),
        preserved_existing_buy_pending=bool(composition_evidence.get("preserved_existing_buy_pending")),
        composite_pending=bool(composition_evidence.get("composite_pending")),
        add_consumer_status=add_result.status,
        add_consumer_reason=add_result.reason,
        add_accepted_count=add_result.accepted_count,
        add_rejected_count=add_result.rejected_count,
        **_result_safety_fields(runtime_safety_decision),
    )


def _write_no_signal_pending(
    *,
    runtime_root: Path,
    business_date: str,
    target_session_date: str,
    environment: str,
    environment_capability_context: dict[str, Any] | None,
    reason: str,
    current_position_count: int,
    current_exposure: float,
    status: str = "NO_SIGNAL",
    safety_decision: RuntimeSafetyDecision | None = None,
    non_executable_decisions: tuple[SellExitDecision, ...] = (),
    existing_buy_pending=None,
    existing_buy_pending_reason: str = "",
    add_result: AddConsumerResult | None = None,
) -> SellPlanningPipelineResult:
    artifact_dir = _sell_artifact_dir(runtime_root, business_date)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    order_plan_path = artifact_dir / "order_plan.json"
    approval_path = artifact_dir / "approval_artifact.json"
    order_plan_payload = {
        "schema_version": "1",
        "order_plan_id": f"order-plan-sell-no-signal-{business_date}",
        "environment": environment,
        "business_date": business_date,
        "target_session_date": target_session_date,
        "status": "NO_ACTION",
        "items": [],
        "reason": reason,
        "sell_source_contract": "Current Position is the only SELL source",
        "safety_context": _safety_context_payload(safety_decision),
    }
    if non_executable_decisions:
        order_plan_payload["non_executable_sell_decisions"] = _non_executable_decision_payload(non_executable_decisions)
    if add_result is not None:
        order_plan_payload["pm_add_consumer"] = add_result.to_evidence()
    order_plan_path.write_text(_json_dumps(order_plan_payload), encoding="utf-8")
    approval_path.write_text(_json_dumps({"status": "NO_SIGNAL", "reason": reason}), encoding="utf-8")
    if existing_buy_pending is None and status not in {"REVIEW_REQUIRED", "BLOCKED"}:
        existing_buy_pending, existing_buy_pending_reason = read_active_buy_pending(
            runtime_root=runtime_root,
            environment=environment,
            business_date=business_date,
            target_session_date=target_session_date,
        )
    if existing_buy_pending is not None and status not in {"REVIEW_REQUIRED", "BLOCKED"}:
        pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
        return SellPlanningPipelineResult(
            status=status,
            reason=reason,
            current_position_count=current_position_count,
            selected_count=0,
            blocked_count=0,
            pending_path=str(pending_path),
            pending_plan_id=existing_buy_pending.pending_plan_id,
            approval_artifact_path=str(approval_path),
            order_plan_artifact_path=str(order_plan_path),
            target_session_date=target_session_date,
            selected_symbols=tuple(item.symbol for item in existing_buy_pending.items if item.side.upper() == "BUY"),
            current_exposure=current_exposure,
            pending_composition_model="PRESERVE_EXISTING_BUY_PENDING",
            pending_composition_status="PASS",
            preserved_existing_buy_pending=True,
            composite_pending=False,
            add_consumer_status=add_result.status if add_result is not None else "",
            add_consumer_reason=add_result.reason if add_result is not None else existing_buy_pending_reason,
            add_accepted_count=add_result.accepted_count if add_result is not None else 0,
            add_rejected_count=add_result.rejected_count if add_result is not None else 0,
            **_result_safety_fields(safety_decision),
        )
    pending = promote_order_plan_to_pending(
        order_plan_id=order_plan_payload["order_plan_id"],
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash=_hash(order_plan_path.read_text(encoding="utf-8")),
        environment=environment,
        plan_created_date=business_date,
        intended_submit_date=target_session_date,
        target_session_date=target_session_date,
        items=(),
    )
    if safety_decision is not None:
        pending = replace(
            pending,
            safety_context=_safety_context_payload(safety_decision),
            safety_decision_id=safety_decision.safety_decision_id,
            safety_policy_version=safety_decision.safety_policy_version,
        )
    pending = _attach_historical_safety_authority(
        pending=pending,
        business_date=business_date,
        safety_decision=safety_decision,
        environment_capability_context=environment_capability_context,
    )
    if not pending.items and status not in {"REVIEW_REQUIRED", "BLOCKED"}:
        pending = replace(pending, state=PendingPlanState.EMPTY)
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    write_pending_order_plan(pending_path, pending)
    if pending.state == PendingPlanState.EMPTY:
        pending_payload = json.loads(pending_path.read_text(encoding="utf-8"))
        pending_payload["status"] = "EMPTY"
        pending_payload["active_pending"] = False
        pending_payload["no_action_reason"] = reason
        if non_executable_decisions:
            pending_payload["non_executable_sell_decisions"] = _non_executable_decision_payload(non_executable_decisions)
        pending_payload["pending_composition_model"] = "EMPTY_NO_EXISTING_BUY_PENDING"
        pending_payload["pending_composition_status"] = existing_buy_pending_reason or "NOT_REQUIRED"
        if add_result is not None:
            pending_payload["pm_add_consumer"] = add_result.to_evidence()
        pending_payload = materialize_empty_pending_no_order_authority(
            pending_payload,
            runtime_root=runtime_root,
            business_date=business_date,
            target_session_date=target_session_date,
            environment=environment,
            authority_reason="empty_pending_no_executable_order_items",
            sell_order_plan_path=order_plan_path,
            sell_approval_path=approval_path,
            sell_reason=reason,
            add_evidence=add_result.to_evidence() if add_result is not None else None,
        )
        pending_path.write_text(_json_dumps(pending_payload), encoding="utf-8")
    return SellPlanningPipelineResult(
        status=status,
        reason=reason,
        current_position_count=current_position_count,
        selected_count=0,
        blocked_count=0,
        pending_path=str(pending_path),
        pending_plan_id=pending.pending_plan_id,
        approval_artifact_path=str(approval_path),
        order_plan_artifact_path=str(order_plan_path),
        target_session_date=target_session_date,
        selected_symbols=(),
        current_exposure=current_exposure,
        pending_composition_model="EMPTY_NO_EXISTING_BUY_PENDING",
        pending_composition_status=existing_buy_pending_reason or "NOT_REQUIRED",
        preserved_existing_buy_pending=False,
        composite_pending=False,
        add_consumer_status=add_result.status if add_result is not None else "",
        add_consumer_reason=add_result.reason if add_result is not None else "",
        add_accepted_count=add_result.accepted_count if add_result is not None else 0,
        add_rejected_count=add_result.rejected_count if add_result is not None else 0,
        **_result_safety_fields(safety_decision),
    )


def _write_add_pending(
    *,
    runtime_root: Path,
    business_date: str,
    target_session_date: str,
    environment: str,
    environment_capability_context: dict[str, Any] | None,
    current_position_count: int,
    current_exposure: float,
    add_result: AddConsumerResult,
    existing_buy_pending,
    capital_deployment_policy: CapitalDeploymentPolicy | None = None,
    submit_policy_context: Mapping[str, Any] | None = None,
    accepted_generation_binding: Mapping[str, Any] | None = None,
    safety_decision: RuntimeSafetyDecision | None = None,
) -> SellPlanningPipelineResult:
    artifact_dir = _sell_artifact_dir(runtime_root, business_date)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    order_plan_path = artifact_dir / "pm_add_order_plan.json"
    approval_path = artifact_dir / "pm_add_approval_artifact.json"
    canonical_submit_policy_context = _submit_policy_context(submit_policy_context)
    pending_items = tuple(
        _pending_item_with_accepted_generation_binding(
            item=_pending_item_with_submit_policy_context(item=item, submit_policy_context=canonical_submit_policy_context),
            accepted_generation_binding=accepted_generation_binding,
        )
        for item in add_result.accepted_items
    )
    order_plan_payload = {
        "schema_version": "1",
        "order_plan_id": f"order-plan-pm-add-{business_date}",
        "environment": environment,
        "business_date": business_date,
        "target_session_date": target_session_date,
        "status": "PASS",
        "submit_policy_context": canonical_submit_policy_context or None,
        "submit_policy_version": str(canonical_submit_policy_context.get("submit_policy_version") or ""),
        "submit_policy_source": str(canonical_submit_policy_context.get("submit_policy_source") or ""),
        "submit_policy_hash": str(canonical_submit_policy_context.get("submit_policy_hash") or ""),
        "pm_add_consumer": add_result.to_evidence(),
        "items": [_jsonable(item) for item in pending_items],
    }
    order_plan_path.write_text(_json_dumps(order_plan_payload), encoding="utf-8")
    pending = promote_order_plan_to_pending(
        order_plan_id=order_plan_payload["order_plan_id"],
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash=_hash(order_plan_path.read_text(encoding="utf-8")),
        environment=environment,
        plan_created_date=business_date,
        intended_submit_date=target_session_date,
        target_session_date=target_session_date,
        items=pending_items,
        submit_policy_context=canonical_submit_policy_context,
    )
    pending = _attach_accepted_generation_binding_to_pending(
        pending=pending,
        accepted_generation_binding=accepted_generation_binding,
    )
    pending = _attach_historical_safety_authority(
        pending=pending,
        business_date=business_date,
        safety_decision=safety_decision,
        environment_capability_context=environment_capability_context,
    )
    approved_item_ids = tuple(item.pending_item_id for item in pending.items)
    request = build_approval_request(
        pending_plan=pending,
        business_date=business_date,
        expires_at=f"{business_date}T15:00:00+09:00",
    )
    approval = build_approval_artifact(
        request=request,
        decision=ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            approved_item_ids=approved_item_ids,
            rejected_item_ids=(),
            reason="runtime v2 pm add planning approval",
            operator="runtime_v2_pm_add_planning_job",
            decided_at=f"{business_date}T08:46:00+09:00",
            approved_order_conditions=build_approved_order_conditions(
                pending_items=pending.items,
                target_session_date=target_session_date,
            ),
        ),
    )
    approval_path.write_text(_json_dumps(_jsonable(approval)), encoding="utf-8")
    pending = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=approval,
        planning_submit_feasibility_current=load_runtime_current_exposure(
            runtime_root / "persistent_ledger" / "state.json"
        ),
        planning_submit_feasibility_policy=capital_deployment_policy,
    )
    pending, order_plan_path, approval_path, composition_evidence = compose_with_existing_buy_pending(
        existing_buy_pending=existing_buy_pending,
        pending=pending,
        artifact_dir=artifact_dir,
        business_date=business_date,
        target_session_date=target_session_date,
        environment=environment,
        reason="PM ADD Pending composed with active BUY Pending",
        planning_submit_feasibility_current=load_runtime_current_exposure(
            runtime_root / "persistent_ledger" / "state.json"
        ),
        planning_submit_feasibility_policy=capital_deployment_policy,
    )
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    write_pending_order_plan(pending_path, pending)
    return SellPlanningPipelineResult(
        status="PASS",
        reason="PM ADD BUY pending generated",
        current_position_count=current_position_count,
        selected_count=len(pending.items),
        blocked_count=0,
        pending_path=str(pending_path),
        pending_plan_id=pending.pending_plan_id,
        approval_artifact_path=str(approval_path),
        order_plan_artifact_path=str(order_plan_path),
        target_session_date=target_session_date,
        selected_symbols=tuple(item.symbol for item in pending.items),
        current_exposure=current_exposure,
        pending_composition_model=str(composition_evidence.get("composition_model") or ""),
        pending_composition_status=str(composition_evidence.get("composition_status") or ""),
        preserved_existing_buy_pending=bool(composition_evidence.get("preserved_existing_buy_pending")),
        composite_pending=bool(composition_evidence.get("composite_pending")),
        add_consumer_status=add_result.status,
        add_consumer_reason=add_result.reason,
        add_accepted_count=add_result.accepted_count,
        add_rejected_count=add_result.rejected_count,
        **_result_safety_fields(safety_decision),
    )


def _attach_historical_safety_authority(
    *,
    pending,
    business_date: str,
    safety_decision: RuntimeSafetyDecision | None,
    environment_capability_context: dict[str, Any] | None,
):
    if safety_decision is None:
        return pending
    context = environment_capability_context or {}
    if str(context.get("runtime_mode") or "") != "historical":
        return pending
    safety_context = materialize_historical_pending_safety_context(
        safety_decision_id=safety_decision.safety_decision_id,
        safety_policy_version=safety_decision.safety_policy_version or HISTORICAL_NEUTRAL_SAFETY_POLICY_VERSION,
        safety_source=safety_decision.safety_source or HISTORICAL_NEUTRAL_SAFETY_SOURCE,
        safety_decision=safety_decision.decision,
        safety_reason=safety_decision.reason,
        safety_business_date=business_date,
        runtime_test_run_id=str(context.get("runtime_test_run_id") or ""),
        runtime_test_profile_id=str(context.get("runtime_test_profile_id") or ""),
        runtime_test_evidence_root=str(context.get("runtime_test_evidence_root") or ""),
    )
    if not safety_context:
        return pending
    return replace(
        pending,
        safety_context=safety_context,
        safety_decision_id=safety_context["safety_decision_id"],
        safety_policy_version=safety_context["safety_policy_version"],
        items=tuple(_pending_item_with_safety_context(item=item, safety_context=safety_context) for item in pending.items),
    )


def _pending_item_with_safety_context(*, item: PendingOrderItem, safety_context: Mapping[str, Any]) -> PendingOrderItem:
    return replace(
        item,
        safety_authority=str(safety_context.get("safety_authority") or item.safety_authority),
        safety_business_date=str(safety_context.get("safety_business_date") or item.safety_business_date),
        safety_decision=str(safety_context.get("safety_decision") or item.safety_decision),
        safety_decision_id=str(safety_context.get("safety_decision_id") or item.safety_decision_id),
        safety_policy_version=str(safety_context.get("safety_policy_version") or item.safety_policy_version),
        safety_reason=str(safety_context.get("safety_reason") or item.safety_reason),
        safety_source=str(safety_context.get("safety_source") or item.safety_source),
        temporal_authority_business_date=str(
            safety_context.get("temporal_authority_business_date") or item.temporal_authority_business_date
        ),
        runtime_test_evidence_root=str(safety_context.get("runtime_test_evidence_root") or item.runtime_test_evidence_root),
        runtime_test_profile_id=str(safety_context.get("runtime_test_profile_id") or item.runtime_test_profile_id),
        runtime_test_run_id=str(safety_context.get("runtime_test_run_id") or item.runtime_test_run_id),
    )


def _ai_signal(decision: SellExitDecision, rank: int) -> AIPlanningSignal:
    source_decision = str(decision.source_decision or "EXIT").upper()
    return AIPlanningSignal(
        signal_id=f"sell-{source_decision.lower()}-pm-{decision.symbol}-{rank:03d}",
        symbol=decision.symbol,
        side="SELL",
        rank=rank,
        score=decision.score,
        reason=decision.reason,
        source_ai="runtime_v2_position_management",
    )


def _allocation(
    *,
    decision: SellExitDecision,
    signal: AIPlanningSignal,
    position: CurrentAssetPosition | None,
    policy_context: dict[str, Any] | None = None,
) -> CapitalAllocationSignal:
    price = _position_price(position)
    quantity = max(float(decision.quantity), 0.0)
    estimated_amount = quantity * price
    return CapitalAllocationSignal(
        allocation_id=f"sell-allocation-{signal.symbol}",
        symbol=signal.symbol,
        side=signal.side,
        allocated_amount=estimated_amount,
        max_amount=estimated_amount,
        cash_required=0.0,
        reason="current_position_exit_allocation",
        estimated_price=price,
        price_source="current_sot_position_valuation" if price > 0 else "",
        price_as_of=str(position.as_of if position else ""),
        price_confidence="current_sot",
        price_required=True,
        policy_version=str((policy_context or {}).get("policy_version") or ""),
        policy_source=str((policy_context or {}).get("policy_source") or ""),
        sizing_policy_reason=str((policy_context or {}).get("sizing_policy_reason") or ""),
        policy_context=policy_context,
        quantity_contract=decision.quantity_contract,
    )


def _pending_item(item) -> PendingOrderItem:
    return PendingOrderItem(
        pending_item_id=item.order_plan_item_id,
        symbol=item.symbol,
        side=item.side,
        quantity=item.quantity,
        order_type="MARKET",
        estimated_price=item.estimated_price,
        estimated_amount=item.estimated_amount,
        approved=False,
        state=item.status.value if isinstance(item.status, Enum) else str(item.status),
        listed_info={
            "code": item.symbol,
            "market": "東証",
            "product_category": "011",
            "security_type": "011",
            "current_listed": True,
        },
        price_source=item.price_source,
        price_as_of=item.price_as_of,
        price_confidence=item.price_confidence,
        price_required=item.price_required,
        capital_allocation_amount=item.capital_allocation_amount,
        policy_version=item.policy_version,
        policy_source=item.policy_source,
        evaluation_capital=item.evaluation_capital,
        target_investment_ratio=None,
        cash_buffer=None,
        max_exposure=None,
        max_positions=item.max_positions,
        max_buy_order_amount=item.max_buy_order_amount,
        max_sell_liquidation_amount=item.max_sell_liquidation_amount,
        min_order_amount=item.min_order_amount,
        buy_notional_policy=item.buy_notional_policy,
        sell_liquidation_policy=item.sell_liquidation_policy,
        manual_review_threshold=item.manual_review_threshold,
        sizing_policy_reason=item.sizing_policy_reason,
        safety_decision_id=item.safety_decision_id,
        safety_policy_version=item.safety_policy_version,
        safety_source=item.safety_source,
        safety_decision=item.safety_decision,
        safety_reason=item.safety_reason,
        quantity_contract=item.quantity_contract,
    )


def _submit_policy_context(
    payload: Mapping[str, Any] | None,
    *,
    capital_deployment_policy: CapitalDeploymentPolicy | None = None,
) -> dict[str, Any]:
    if not payload:
        if capital_deployment_policy is None:
            return {}
        return {
            "submit_policy_authority": "capital_deployment_policy",
            "submit_policy_schema_version": "phase23_bb_submit_policy_authority.v1",
            "submit_policy_version": capital_deployment_policy.policy_version,
            "submit_policy_source": capital_deployment_policy.policy_source,
            "submit_policy_hash": capital_deployment_policy_hash(capital_deployment_policy),
        }
    policy_version = str(payload.get("submit_policy_version") or "")
    policy_source = str(payload.get("submit_policy_source") or "")
    policy_hash = str(payload.get("submit_policy_hash") or "")
    if not policy_version and not policy_source and not policy_hash:
        return {}
    return {
        "submit_policy_authority": str(payload.get("submit_policy_authority") or "capital_deployment_policy"),
        "submit_policy_schema_version": str(
            payload.get("submit_policy_schema_version") or "phase23_bb_submit_policy_authority.v1"
        ),
        "submit_policy_version": policy_version,
        "submit_policy_source": policy_source,
        "submit_policy_hash": policy_hash,
    }


def _pending_item_with_submit_policy_context(
    *,
    item: PendingOrderItem,
    submit_policy_context: Mapping[str, Any],
) -> PendingOrderItem:
    if not submit_policy_context:
        return item
    return replace(
        item,
        submit_policy_version=str(submit_policy_context.get("submit_policy_version") or ""),
        submit_policy_source=str(submit_policy_context.get("submit_policy_source") or ""),
        submit_policy_hash=str(submit_policy_context.get("submit_policy_hash") or ""),
    )


def _attach_accepted_generation_binding_to_pending(
    *,
    pending: PendingOrderPlan,
    accepted_generation_binding: Mapping[str, Any] | None,
) -> PendingOrderPlan:
    if not accepted_generation_binding:
        return pending
    binding = dict(accepted_generation_binding)
    return replace(
        pending,
        accepted_generation_binding=binding,
        accepted_generation_id=str(binding.get("accepted_generation_id") or ""),
        accepted_generation_business_date=str(binding.get("accepted_generation_business_date") or ""),
        accepted_generation_binding_status=str(binding.get("generation_binding_status") or ""),
        items=tuple(
            _pending_item_with_accepted_generation_binding(
                item=item,
                accepted_generation_binding=binding,
            )
            for item in pending.items
        ),
    )


def _pending_item_with_accepted_generation_binding(
    *,
    item: PendingOrderItem,
    accepted_generation_binding: Mapping[str, Any] | None,
) -> PendingOrderItem:
    if not accepted_generation_binding:
        return item
    binding = dict(accepted_generation_binding)
    return replace(
        item,
        accepted_generation_id=str(binding.get("accepted_generation_id") or ""),
        accepted_generation_business_date=str(binding.get("accepted_generation_business_date") or ""),
        accepted_generation_binding_status=str(binding.get("generation_binding_status") or ""),
        accepted_generation_binding=binding,
    )


def _quantity_contract_decision(
    *,
    decision: SellExitDecision,
    position: CurrentAssetPosition | None,
    runtime_root: Path,
    mode: str,
) -> SellExitDecision:
    source_decision = str(decision.source_decision or "EXIT").upper()
    position_quantity = float(position.quantity) if position is not None else 0.0
    sellable = _sellable_quantity_evidence(
        runtime_root=runtime_root,
        symbol=decision.symbol,
        position_quantity=position_quantity,
        mode=mode,
    )
    sellable_quantity = float(sellable["sellable_quantity"])
    if source_decision == "EXIT":
        requested_quantity = float(decision.quantity or 0.0) or position_quantity
        quantity = min(requested_quantity, sellable_quantity)
        status = "PASS" if quantity > 0 else "REVIEW_REQUIRED"
        reason = (
            "EXIT sells the requested/current full sellable quantity"
            if status == "PASS"
            else "REVIEW_REQUIRED_EXIT_SELLABLE_QUANTITY_ZERO"
        )
        contract = {
            "quantity_contract_version": "runtime_v2_pm_exit_full_quantity_v1",
            "source_decision": "EXIT",
            "position_quantity_before": position_quantity,
            "requested_sell_quantity": requested_quantity,
            "sellable_quantity": sellable_quantity,
            "sellable_quantity_source": sellable["sellable_quantity_source"],
            "restricted_quantity": sellable["restricted_quantity"],
            "final_sell_quantity": quantity,
            "expected_remaining_quantity": max(position_quantity - quantity, 0.0),
            "status": status,
            "reason": reason,
        }
        return replace(
            decision,
            quantity=quantity,
            reason=decision.reason if status == "PASS" else reason,
            source_decision="EXIT",
            quantity_contract=contract,
        )
    if source_decision != "REDUCE":
        return replace(
            decision,
            quantity=0.0,
            quantity_contract={
                "quantity_contract_version": REDUCE_QUANTITY_CONTRACT_VERSION,
                "source_decision": source_decision,
                "status": "REVIEW_REQUIRED",
                "reason": "REVIEW_REQUIRED_UNSUPPORTED_SELL_SOURCE_DECISION",
            },
        )
    contract = calculate_reduce_quantity_contract(
        position_quantity=float(position.quantity) if position is not None else 0.0,
        sellable_quantity=sellable_quantity,
        sellable_quantity_source=str(sellable["sellable_quantity_source"]),
        restricted_quantity=float(sellable["restricted_quantity"]),
        reduce_intensity=decision.reduce_intensity,
        tradable_unit=DEFAULT_TRADABLE_UNIT,
    )
    return replace(
        decision,
        quantity=float(contract.get("final_sell_quantity") or 0.0),
        source_decision="REDUCE",
        quantity_contract=contract,
    )


def calculate_reduce_quantity_contract(
    *,
    position_quantity: float,
    reduce_intensity: str,
    sellable_quantity: float | None = None,
    sellable_quantity_source: str = "current_position_quantity",
    restricted_quantity: float = 0.0,
    tradable_unit: float | None = DEFAULT_TRADABLE_UNIT,
) -> dict[str, Any]:
    intensity = str(reduce_intensity or "").upper()
    target_reduce_ratio = REDUCE_INTENSITY_RATIOS.get(intensity)
    position_quantity_value = float(position_quantity)
    tradable_unit_value = float(tradable_unit) if tradable_unit is not None else 0.0
    sellable_quantity_value = float(sellable_quantity if sellable_quantity is not None else position_quantity_value)
    effective_sellable_quantity = min(position_quantity_value, sellable_quantity_value)
    base = {
        "quantity_contract_version": REDUCE_QUANTITY_CONTRACT_VERSION,
        "source_decision": "REDUCE",
        "reduce_intensity": intensity,
        "target_reduce_ratio": target_reduce_ratio,
        "position_quantity_before": position_quantity_value,
        "sellable_quantity": effective_sellable_quantity,
        "sellable_quantity_source": sellable_quantity_source,
        "restricted_quantity": float(restricted_quantity),
        "tradable_unit": tradable_unit_value,
        "minimum_order_quantity": tradable_unit_value,
        "minimum_remaining_quantity": tradable_unit_value,
        "rounding_policy": "floor_to_tradable_unit_to_avoid_oversell",
    }
    if position_quantity_value <= 0:
        return {**base, "status": "REVIEW_REQUIRED", "reason": "REVIEW_REQUIRED_REDUCE_CURRENT_POSITION_MISSING", "final_sell_quantity": 0.0}
    if tradable_unit_value <= 0:
        return {**base, "status": "REVIEW_REQUIRED", "reason": "REVIEW_REQUIRED_REDUCE_TRADABLE_UNIT_UNKNOWN", "final_sell_quantity": 0.0}
    if target_reduce_ratio is None:
        return {**base, "status": "REVIEW_REQUIRED", "reason": "REVIEW_REQUIRED_REDUCE_INTENSITY_UNKNOWN", "final_sell_quantity": 0.0}
    if sellable_quantity_value < 0:
        return {**base, "status": "REVIEW_REQUIRED", "reason": "REVIEW_REQUIRED_REDUCE_SELLABLE_QUANTITY_NEGATIVE", "final_sell_quantity": 0.0}
    if effective_sellable_quantity < tradable_unit_value:
        return _non_executable_reduce_quantity_contract(
            base=base,
            raw_reduce_quantity=effective_sellable_quantity * target_reduce_ratio,
            rounded_reduce_quantity=0.0,
            position_quantity=position_quantity_value,
        )
    raw_reduce_quantity = effective_sellable_quantity * target_reduce_ratio
    rounded_reduce_quantity = math.floor(raw_reduce_quantity / tradable_unit_value) * tradable_unit_value
    expected_remaining_quantity = position_quantity_value - rounded_reduce_quantity
    if rounded_reduce_quantity <= 0:
        return _non_executable_reduce_quantity_contract(
            base=base,
            raw_reduce_quantity=raw_reduce_quantity,
            rounded_reduce_quantity=rounded_reduce_quantity,
            position_quantity=position_quantity_value,
        )
    if rounded_reduce_quantity >= position_quantity_value:
        return {
            **base,
            "status": "REVIEW_REQUIRED",
            "reason": "REVIEW_REQUIRED_REDUCE_QUANTITY_EXCEEDS_OR_EQUALS_POSITION",
            "raw_reduce_quantity": raw_reduce_quantity,
            "rounded_reduce_quantity": rounded_reduce_quantity,
            "final_sell_quantity": 0.0,
            "expected_remaining_quantity": expected_remaining_quantity,
        }
    if expected_remaining_quantity < tradable_unit:
        return {
            **base,
            "status": "REVIEW_REQUIRED",
            "reason": "REVIEW_REQUIRED_REDUCE_MINIMUM_REMAINING_QUANTITY_VIOLATION",
            "raw_reduce_quantity": raw_reduce_quantity,
            "rounded_reduce_quantity": rounded_reduce_quantity,
            "final_sell_quantity": 0.0,
            "expected_remaining_quantity": expected_remaining_quantity,
        }
    return {
        **base,
        "status": "PASS",
        "reason": "reduce_quantity_contract_pass",
        "raw_reduce_quantity": raw_reduce_quantity,
        "rounded_reduce_quantity": rounded_reduce_quantity,
        "final_sell_quantity": rounded_reduce_quantity,
        "expected_remaining_quantity": expected_remaining_quantity,
    }


def _non_executable_reduce_quantity_contract(
    *,
    base: dict[str, Any],
    raw_reduce_quantity: float,
    rounded_reduce_quantity: float,
    position_quantity: float,
) -> dict[str, Any]:
    return {
        **base,
        "status": "NOT_EXECUTABLE",
        "reason": REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY_REASON,
        "raw_reduce_quantity": raw_reduce_quantity,
        "rounded_reduce_quantity": rounded_reduce_quantity,
        "rounded_executable_quantity": 0.0,
        "final_sell_quantity": 0.0,
        "expected_remaining_quantity": position_quantity,
        "execution_feasibility_status": "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY",
        "effective_action": "NO_SELL_ORDER",
        "pending_order_generated": False,
        "position_quantity_after": position_quantity,
        "runtime_continuation_status": "PASS",
        "position_lifecycle_event": "REDUCE_NOT_EXECUTED_MINIMUM_TRADABLE_QUANTITY",
    }


def _is_non_executable_reduce_quantity_contract(contract: Mapping[str, Any] | None) -> bool:
    if not isinstance(contract, Mapping):
        return False
    return (
        str(contract.get("source_decision") or "").upper() == "REDUCE"
        and str(contract.get("status") or "").upper() == "NOT_EXECUTABLE"
        and str(contract.get("reason") or "") == REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY_REASON
    )


def _non_executable_decision_payload(decisions: tuple[SellExitDecision, ...]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for decision in decisions:
        contract = dict(decision.quantity_contract or {})
        payload.append(
            {
                "symbol": decision.symbol,
                "original_decision": str(decision.source_decision or "").upper(),
                "source_decision_id": decision.source_decision_id,
                "reason": decision.reason,
                "quantity_contract": contract,
                "execution_feasibility_status": contract.get("execution_feasibility_status") or "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY",
                "effective_action": contract.get("effective_action") or "NO_SELL_ORDER",
                "pending_order_generated": bool(contract.get("pending_order_generated")),
                "position_quantity_after": contract.get("position_quantity_after", contract.get("position_quantity_before")),
                "runtime_continuation_status": contract.get("runtime_continuation_status") or "PASS",
            }
        )
    return payload


def _apply_exit_priority(decisions: tuple[SellExitDecision, ...]) -> tuple[SellExitDecision, ...]:
    exit_symbols = {
        str(decision.symbol).strip()
        for decision in decisions
        if str(decision.source_decision or "EXIT").upper() == "EXIT" and str(decision.symbol).strip()
    }
    result: list[SellExitDecision] = []
    seen: set[tuple[str, str]] = set()
    for decision in decisions:
        symbol = str(decision.symbol).strip()
        source_decision = str(decision.source_decision or "EXIT").upper()
        if source_decision == "REDUCE" and symbol in exit_symbols:
            continue
        key = (symbol, source_decision)
        if key in seen:
            continue
        seen.add(key)
        result.append(decision)
    return tuple(result)


def _pending_sell_conflict(*, runtime_root: Path, symbols: tuple[str, ...]) -> tuple[str, ...]:
    path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    if not path.is_file():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ("PENDING_SLOT_UNREADABLE",)
    state = str(payload.get("state") or payload.get("status") or "").upper()
    active_pending = bool(payload.get("active_pending", state not in {"", "EMPTY", "CONSUMED", "NOT_REQUIRED"}))
    if not active_pending:
        return ()
    requested = {str(symbol).strip() for symbol in symbols if str(symbol).strip()}
    conflicts: list[str] = []
    for item in payload.get("items") or ():
        if str(item.get("side") or "").upper() != "SELL":
            continue
        symbol = str(item.get("symbol") or "").strip()
        if any(same_symbol_identity(symbol, requested_symbol) for requested_symbol in requested) and float(item.get("quantity") or 0.0) > 0:
            conflicts.append(symbol)
    return tuple(sorted(set(conflicts)))


def _sellable_quantity_evidence(
    *,
    runtime_root: Path,
    symbol: str,
    position_quantity: float,
    mode: str,
) -> dict[str, Any]:
    if position_quantity <= 0:
        return {
            "sellable_quantity": 0.0,
            "restricted_quantity": 0.0,
            "sellable_quantity_source": "current_position_missing",
        }
    if mode == "historical":
        restricted = _historical_restricted_sell_quantity(runtime_root=runtime_root, symbol=symbol)
        return {
            "sellable_quantity": max(float(position_quantity) - restricted, 0.0),
            "restricted_quantity": restricted,
            "sellable_quantity_source": "historical_simulated_broker_authority",
        }
    snapshot = _load_broker_positions_snapshot(runtime_root)
    snapshot_quantity = _broker_snapshot_available_quantity(snapshot=snapshot, symbol=symbol)
    if snapshot_quantity is None:
        return {
            "sellable_quantity": float(position_quantity),
            "restricted_quantity": 0.0,
            "sellable_quantity_source": "current_position_quantity_submit_guard_final_authority",
        }
    available = min(float(position_quantity), snapshot_quantity)
    return {
        "sellable_quantity": available,
        "restricted_quantity": max(float(position_quantity) - available, 0.0),
        "sellable_quantity_source": "broker_readonly_available_quantity_snapshot",
    }


def _historical_restricted_sell_quantity(*, runtime_root: Path, symbol: str) -> float:
    normalized_symbol = str(symbol).strip()
    sell_order_quantity = 0.0
    sell_execution_quantity = 0.0
    for record in _read_jsonl_records(runtime_root / "persistent_ledger" / "orders.jsonl"):
        if str(record.get("environment") or "") != "historical":
            continue
        if str(record.get("side") or "").upper() != "SELL":
            continue
        if str(record.get("symbol") or "").strip() != normalized_symbol:
            continue
        if not _is_historical_open_sell_order(record):
            continue
        sell_order_quantity += _safe_float(record.get("quantity"))
    for record in _read_jsonl_records(runtime_root / "persistent_ledger" / "executions.jsonl"):
        if str(record.get("environment") or record.get("mode") or "") != "historical":
            continue
        if str(record.get("side") or "").upper() != "SELL":
            continue
        if str(record.get("symbol") or record.get("broker_issue_code") or "").strip() != normalized_symbol:
            continue
        if str(record.get("execution_status") or "").lower() not in {"filled", "partial_fill", "partially_filled"}:
            continue
        sell_execution_quantity += _safe_float(record.get("filled_quantity") or record.get("quantity"))
    return max(sell_order_quantity - sell_execution_quantity, 0.0)


def _is_historical_open_sell_order(record: Mapping[str, Any]) -> bool:
    status = str(record.get("status") or record.get("order_status") or "").strip().upper()
    if status in {
        "REJECTED",
        "CANCELLED",
        "CANCELED",
        "FILLED",
        "FILL",
        "FULL_FILL",
        "FULLY_FILLED",
        "DONE",
    }:
        return False
    source = str(record.get("source") or "").strip()
    if source == "runtime_v2_execution_readonly_simulation":
        return False
    return True


def _load_broker_positions_snapshot(runtime_root: Path) -> dict[str, Any]:
    snapshot_dir = runtime_root / "broker" / "snapshots" / "positions"
    if not snapshot_dir.exists():
        return {}
    candidates = [
        path
        for path in snapshot_dir.glob("*.json")
        if path.is_file() and not path.name.endswith(".manifest.json")
    ]
    if not candidates:
        return {}
    path = max(candidates, key=lambda candidate: (candidate.stat().st_mtime, candidate.name))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _broker_snapshot_available_quantity(*, snapshot: dict[str, Any], symbol: str) -> float | None:
    records = snapshot.get("records")
    if not isinstance(records, list):
        records = snapshot.get("positions")
    if not isinstance(records, list):
        return None
    values: list[float] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        record_symbol = str(record.get("issue_code") or record.get("symbol") or record.get("position_key") or "").strip()
        requested = str(symbol).strip()
        if record_symbol != requested and record_symbol[:4] != requested[:4]:
            continue
        value = _optional_float(record.get("available_quantity"))
        if value is None:
            return None
        values.append(float(value))
    if not values:
        return None
    return sum(values)


def _read_jsonl_records(path: Path) -> tuple[dict[str, Any], ...]:
    if not path.is_file():
        return ()
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return tuple(records)


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _policy_context(policy: CapitalDeploymentPolicy | None) -> dict[str, Any] | None:
    if policy is None:
        return None
    return {
        "policy_version": policy.policy_version,
        "policy_source": policy.policy_source,
        "evaluation_capital": policy.evaluation_capital,
        "max_positions": policy.max_positions,
        "max_buy_order_amount": policy.max_buy_order_amount,
        "max_sell_liquidation_amount": policy.max_sell_liquidation_amount,
        "min_order_amount": policy.min_order_amount,
        "buy_notional_policy": policy.buy_notional_policy,
        "sell_liquidation_policy": policy.sell_liquidation_policy,
        "manual_review_threshold": {
            "buy_amount": policy.manual_review_threshold.buy_amount,
            "sell_liquidation_amount": policy.manual_review_threshold.sell_liquidation_amount,
        },
        "sizing_policy_reason": "sell liquidation governed by Capital Deployment Policy evidence",
    }


def _active_deployment_capital(asset_state: CurrentAssetState, *, current_exposure: float) -> float | None:
    if asset_state.total_equity is not None:
        return float(asset_state.total_equity)
    if asset_state.cash is not None:
        return float(asset_state.cash) + float(current_exposure)
    return None


def _available_cash(asset_state: CurrentAssetState) -> float | None:
    values = [
        float(value)
        for value in (asset_state.cash, asset_state.buying_power)
        if value is not None and float(value) >= 0
    ]
    if not values:
        return None
    return min(values)


def _matching_position(
    current_positions: Mapping[str, CurrentAssetPosition],
    symbol: str,
) -> CurrentAssetPosition | None:
    for existing_symbol, position in current_positions.items():
        if same_symbol_identity(existing_symbol, symbol):
            return position
    return None


def _result_safety_fields(decision: RuntimeSafetyDecision | None) -> dict[str, Any]:
    fields = safety_manifest_fields(decision)
    return {
        "safety_decision_id": str(fields.get("safety_decision_id") or ""),
        "safety_policy_version": str(fields.get("safety_policy_version") or ""),
        "safety_source": str(fields.get("safety_source") or ""),
        "safety_decision": str(fields.get("safety_decision") or ""),
        "safety_reason": str(fields.get("safety_reason") or ""),
        "safety_status": str(fields.get("safety_status") or ""),
        "safety_block_buy": bool(fields.get("safety_block_buy")),
        "safety_block_sell": bool(fields.get("safety_block_sell")),
        "safety_halt_runtime": bool(fields.get("safety_halt_runtime")),
    }


def _runtime_safety_context(decision: RuntimeSafetyDecision) -> RuntimeSafetyContext:
    return RuntimeSafetyContext(
        safety_decision_id=decision.safety_decision_id,
        safety_policy_version=decision.safety_policy_version,
        safety_source=decision.safety_source or decision.artifact_path,
        safety_decision=decision.decision,
        safety_reason=decision.reason,
        review_required=decision.review_required,
        block_buy=decision.block_buy,
        block_sell=decision.block_sell,
        block_submit=decision.block_submit,
        halt_runtime=decision.halt_runtime,
        emergency_stop=decision.emergency_stop,
        generated_at=decision.generated_at,
        expires_at=decision.expires_at,
    )


def _safety_context_payload(decision: RuntimeSafetyDecision | None) -> dict[str, Any]:
    if decision is None:
        return {}
    return {
        "safety_decision_id": decision.safety_decision_id,
        "safety_policy_version": decision.safety_policy_version,
        "safety_source": decision.safety_source or decision.artifact_path,
        "safety_decision": decision.decision,
        "safety_reason": decision.reason,
    }


def _position_price(position: CurrentAssetPosition | None) -> float:
    if position is None or position.quantity <= 0:
        return 0.0
    if position.market_value > 0:
        return float(position.market_value) / float(position.quantity)
    return float(position.average_price)


def _current_position_by_identity(
    current_positions: Mapping[str, CurrentAssetPosition],
    symbol: str,
) -> CurrentAssetPosition | None:
    for existing_symbol, position in current_positions.items():
        if same_symbol_identity(existing_symbol, symbol):
            return position
    return None


def _load_asset_state(path: Path) -> CurrentAssetState:
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
        source=str(payload.get("source") or "current_asset_state"),
        as_of=str(payload.get("as_of") or payload.get("updated_at") or ""),
        positions=positions,
        cash=_optional_float(payload.get("cash")),
        buying_power=_optional_float(payload.get("buying_power")),
        market_value=_optional_float(payload.get("market_value")),
        total_equity=_optional_float(payload.get("total_equity")),
        review_required=bool(payload.get("review_required")),
        production_equivalent=bool(payload.get("production_equivalent", False)),
        current_state_confirmed_empty=bool(payload.get("current_state_confirmed_empty", False)),
        current_positions_unknown=bool(payload.get("current_positions_unknown", positions is None)),
        cash_unknown=bool(payload.get("cash_unknown", payload.get("cash") is None)),
        buying_power_unknown=bool(payload.get("buying_power_unknown", payload.get("buying_power") is None)),
        generated_from=tuple(payload.get("generated_from") or ()),
        created_at=str(payload.get("created_at") or payload.get("updated_at") or ""),
    )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _sell_artifact_dir(runtime_root: Path, business_date: str) -> Path:
    return runtime_root / "runtime_state" / "sell_pipeline" / business_date


def _reject_mode_rooted_runtime_root(root: Path) -> None:
    text = str(root)
    if text.endswith("/demo") or "/demo/" in text:
        raise ValueError("mode-rooted Current path is not allowed")


def _hash(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: _jsonable(val) for key, val in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(val) for key, val in value.items()}
    return value


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
