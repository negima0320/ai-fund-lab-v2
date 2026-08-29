"""Production-common consumer for Phase22 Strategy Planning Authority."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalDecision, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.approval.policy import (
    build_approval_artifact,
    build_approval_request,
    build_approved_order_conditions,
)
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.safety_authority import (
    HISTORICAL_NEUTRAL_SAFETY_POLICY_VERSION,
    HISTORICAL_NEUTRAL_SAFETY_SOURCE,
    materialize_historical_pending_safety_context,
)
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.order_reservation import resolve_order_cash_reservation
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    CapitalDeploymentPolicyError,
    load_capital_deployment_policy,
)
from ai_fund_lab_v2.runtime_v2.cash_exposure_authority import resolve_cash_exposure_authority
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import (
    RuntimeCurrentExposure,
    evaluate_buy_item_submit_feasibility,
    load_runtime_current_exposure,
)
from ai_fund_lab_v2.runtime_v2.position_count_authority import resolve_position_count_authority
from ai_fund_lab_v2.runtime_v2.position_sizing_authority import resolve_position_sizing_authority
from ai_fund_lab_v2.strategy.runtime_planning import (
    RuntimePlanningSchemaError,
    validate_runtime_planning_artifact,
)


SCHEMA_VERSION = "phase23_i_strategy_planning_authority_consumer.v1"
ROUND_LOT = 100


@dataclass(frozen=True)
class StrategyPlanningAuthorityResult:
    status: str
    reason: str
    business_date: str
    mode: str
    strategy_dir: str
    runtime_planning_artifact_path: str
    position_sizing_artifact_path: str
    order_plan_artifact_path: str
    pending_path: str
    approval_artifact_path: str
    pending_plan_id: str
    plan_count: int
    pending_item_count: int
    selected_symbols: tuple[str, ...]
    strategy_artifact_eligibility: str
    planning_consumer_eligibility: str
    production_decision_allowed: bool
    broker_write_allowed: bool
    broker_write_performed: bool
    legacy_planning_authority_used: bool
    legacy_formal_planning_authority_active: bool
    legacy_comparison_artifact_present: bool
    runtime_switch_performed: bool
    no_action: bool
    reason_codes: tuple[str, ...]
    lineage: dict[str, Any]
    pending_commit_status: str = "COMMITTED_CURRENT"
    pending_authority_eligibility: str = "AUTHORITY_ELIGIBLE"
    pending_retry_eligibility: str = "RETRY_INPUT_ELIGIBLE"
    atomic_commit_decision: str = "COMMIT"

    def to_stage_details(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["selected_symbols"] = list(self.selected_symbols)
        payload["reason_codes"] = list(self.reason_codes)
        return payload


@dataclass(frozen=True)
class StrategySellExitProvenance:
    symbol: str
    business_date: str
    source_decision_id: str
    source_decision_type: str
    position_campaign_id: str


def activate_strategy_planning_authority(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    strategy_dir: Path | str,
    target_session_date: str | None = None,
    price_by_symbol: Mapping[str, float] | None = None,
    environment_capability_context: Mapping[str, Any] | None = None,
    safety_authority_payload: Mapping[str, Any] | None = None,
    submit_policy_authority_payload: Mapping[str, Any] | None = None,
) -> StrategyPlanningAuthorityResult:
    """Consume Phase22 Strategy artifacts and write Runtime Pending.

    This is a Planning Authority switch, not a Broker Write switch. It never
    calls a broker and it never falls back to the legacy morning AI signals.
    """

    runtime_root_path = Path(runtime_root)
    strategy_path = Path(strategy_dir)
    target_session_date = target_session_date or business_date
    runtime_planning_path = strategy_path / "runtime_planning.json"
    position_sizing_path = strategy_path / "position_sizing.json"
    input_manifest_path = strategy_path / "input_manifest.json"
    order_plan_path = runtime_root_path / "runtime_state" / "strategy_planning" / business_date / "order_plan.json"
    approval_path = runtime_root_path / "runtime_state" / "strategy_planning" / business_date / "approval_artifact.json"
    pending_path = runtime_root_path / "pending_order_plan" / "pending_order_plan.json"
    order_plan_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path.parent.mkdir(parents=True, exist_ok=True)

    reason_codes: list[str] = []
    lineage = _base_lineage(strategy_path=strategy_path, business_date=business_date)
    safety_context = _resolve_pending_safety_context(
        mode=mode,
        business_date=business_date,
        target_session_date=target_session_date,
        safety_authority_payload=safety_authority_payload,
        environment_capability_context=environment_capability_context,
    )
    submit_policy_context = _resolve_submit_policy_context(submit_policy_authority_payload)
    accepted_generation_binding = _accepted_generation_binding_context(
        input_manifest_path=input_manifest_path,
        mode=mode,
        business_date=business_date,
    )
    submit_feasibility_policy = _load_submit_feasibility_policy(submit_policy_context)
    submit_feasibility_current = load_runtime_current_exposure(
        runtime_root_path / "persistent_ledger" / "state.json"
    )
    if not runtime_planning_path.is_file():
        return _write_review_pending(
            runtime_root=runtime_root_path,
            mode=mode,
            business_date=business_date,
            target_session_date=target_session_date,
            strategy_dir=strategy_path,
            runtime_planning_path=runtime_planning_path,
            position_sizing_path=position_sizing_path,
            order_plan_path=order_plan_path,
            approval_path=approval_path,
            pending_path=pending_path,
            reason="strategy_runtime_planning_artifact_missing",
            reason_codes=("strategy_runtime_planning_artifact_missing",),
            lineage=lineage,
            broker_write_allowed=_broker_write_allowed(mode, environment_capability_context),
        )
    try:
        runtime_planning_payload = _read_json(runtime_planning_path)
        validate_runtime_planning_artifact(runtime_planning_payload)
    except (OSError, json.JSONDecodeError, RuntimePlanningSchemaError) as exc:
        return _write_review_pending(
            runtime_root=runtime_root_path,
            mode=mode,
            business_date=business_date,
            target_session_date=target_session_date,
            strategy_dir=strategy_path,
            runtime_planning_path=runtime_planning_path,
            position_sizing_path=position_sizing_path,
            order_plan_path=order_plan_path,
            approval_path=approval_path,
            pending_path=pending_path,
            reason=f"strategy_runtime_planning_artifact_invalid:{exc}",
            reason_codes=("strategy_runtime_planning_artifact_invalid",),
            lineage=lineage,
            broker_write_allowed=_broker_write_allowed(mode, environment_capability_context),
        )
    if str(runtime_planning_payload.get("business_date") or "") != business_date:
        return _write_review_pending(
            runtime_root=runtime_root_path,
            mode=mode,
            business_date=business_date,
            target_session_date=target_session_date,
            strategy_dir=strategy_path,
            runtime_planning_path=runtime_planning_path,
            position_sizing_path=position_sizing_path,
            order_plan_path=order_plan_path,
            approval_path=approval_path,
            pending_path=pending_path,
            reason="strategy_runtime_planning_business_date_mismatch",
            reason_codes=("strategy_runtime_planning_business_date_mismatch",),
            lineage=lineage,
            broker_write_allowed=_broker_write_allowed(mode, environment_capability_context),
        )
    if str(runtime_planning_payload.get("producer_result_status") or "") == "BLOCK":
        return _write_review_pending(
            runtime_root=runtime_root_path,
            mode=mode,
            business_date=business_date,
            target_session_date=target_session_date,
            strategy_dir=strategy_path,
            runtime_planning_path=runtime_planning_path,
            position_sizing_path=position_sizing_path,
            order_plan_path=order_plan_path,
            approval_path=approval_path,
            pending_path=pending_path,
            reason="strategy_runtime_planning_blocked",
            reason_codes=tuple(runtime_planning_payload.get("reason_codes") or ("strategy_runtime_planning_blocked",)),
            lineage=lineage,
            broker_write_allowed=_broker_write_allowed(mode, environment_capability_context),
            status="BLOCKED",
        )
    position_sizing_payload = _read_json(position_sizing_path) if position_sizing_path.is_file() else {}
    portfolio_policy_path = strategy_path / "portfolio_policy.json"
    portfolio_policy_payload = _read_json(portfolio_policy_path) if portfolio_policy_path.is_file() else {}
    strategy_authority_context = _strategy_authority_context(
        strategy_path=strategy_path,
        position_sizing_path=position_sizing_path,
        position_sizing_payload=position_sizing_payload,
        portfolio_policy_path=portfolio_policy_path,
        portfolio_policy_payload=portfolio_policy_payload,
    )
    sell_exit_provenance_by_symbol = _same_day_pm_sell_exit_provenance_by_symbol(
        runtime_root=runtime_root_path,
        strategy_path=strategy_path,
        business_date=business_date,
    )
    sizing_by_symbol = {
        str(item.get("security_code") or ""): item
        for item in position_sizing_payload.get("positions", []) or []
        if isinstance(item, dict) and str(item.get("security_code") or "")
    }
    pending_items: list[PendingOrderItem] = []
    item_lineage: list[dict[str, Any]] = []
    plans = list(runtime_planning_payload.get("plans") or [])
    strategy_authority_lineage = (
        dict(runtime_planning_payload["strategy_authority_lineage"])
        if isinstance(runtime_planning_payload.get("strategy_authority_lineage"), Mapping)
        else {}
    )
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        item, item_reason = _pending_item_from_strategy_plan(
            plan=plan,
            sizing=sizing_by_symbol.get(str(plan.get("security_code") or "")) or {},
            business_date=business_date,
            mode=mode,
            runtime_root=runtime_root_path,
            submit_feasibility_policy=submit_feasibility_policy,
            submit_feasibility_current=submit_feasibility_current,
            runtime_planning_path=runtime_planning_path,
            strategy_authority_context=strategy_authority_context,
        )
        item_lineage.append(
            {
                "planning_id": str(plan.get("planning_id") or ""),
                "security_code": str(plan.get("security_code") or ""),
                "planning_intent": str(plan.get("planning_intent") or ""),
                "order_side_intent": str(plan.get("order_side_intent") or ""),
                "pending_item_generated": item is not None,
                "reason": item_reason,
                "position_sizing_used": bool(sizing_by_symbol.get(str(plan.get("security_code") or ""))),
                "strategy_authority_lineage_hash": str(
                    (plan.get("strategy_authority_lineage") or {}).get("lineage_hash")
                    if isinstance(plan.get("strategy_authority_lineage"), Mapping)
                    else ""
                ),
                **_rank_authority_lineage_from_plan(plan),
            }
        )
        if item is not None:
            item = _pending_item_with_strategy_sell_exit_pm_provenance(
                item=item,
                plan=plan,
                provenance_by_symbol=sell_exit_provenance_by_symbol,
                business_date=business_date,
            )
            item = _pending_item_with_accepted_generation_binding(
                item=item,
                accepted_generation_binding=accepted_generation_binding,
            )
            item = _pending_item_with_submit_policy_context(item=item, submit_policy_context=submit_policy_context)
            item = _pending_item_with_safety_context(item=item, safety_context=safety_context)
            pending_items.append(item)
        elif item_reason and not item_reason.startswith("no_action"):
            reason_codes.append(item_reason)

    pending_items = list(_canonical_marginal_capital_pending_order(tuple(pending_items)))
    active_pending_items, cash_feasible_batch = _cash_feasible_buy_batch(
        items=tuple(pending_items),
        current=submit_feasibility_current,
        policy=submit_feasibility_policy,
        business_date=business_date,
        mode=mode,
    )
    pending_items = list(active_pending_items)

    result_status = "PASS" if pending_items else ("REVIEW_REQUIRED" if reason_codes else "NO_ORDER_AUTHORIZED")
    order_plan_payload = {
        "schema_version": "phase23_i_strategy_authority_order_plan.v1",
        "order_plan_id": _order_plan_id(mode=mode, business_date=business_date, strategy_hash=_file_hash(runtime_planning_path)),
        "environment": mode,
        "business_date": business_date,
        "target_session_date": target_session_date,
        "status": "CREATED" if pending_items else result_status,
        "planning_authority": "phase22_strategy_runtime_planning",
        "planning_source": str(runtime_planning_path),
        "planning_authority_winner": "strategy_runtime_planning",
        "planning_consumer": "runtime_v2.planning.strategy_authority.activate_strategy_planning_authority",
        "planning_fallback_used": False,
        "legacy_planning_used": False,
        "buy_planning_status": _side_planning_status(item_lineage, side="BUY"),
        "sell_planning_status": _side_planning_status(item_lineage, side="SELL"),
        "buy_sell_independence_preserved": True,
        "strategy_artifact_path": str(runtime_planning_path),
        "strategy_artifact_hash": _file_hash(runtime_planning_path),
        "strategy_authority_lineage": strategy_authority_lineage,
        "strategy_authority_lineage_hash": str(strategy_authority_lineage.get("lineage_hash") or ""),
        "position_sizing_artifact_path": str(position_sizing_path),
        "position_sizing_artifact_hash": _file_hash(position_sizing_path),
        "items": [_pending_item_payload(item) for item in pending_items],
        "accepted_generation_binding": accepted_generation_binding,
        "accepted_generation_id": str(accepted_generation_binding.get("accepted_generation_id") or ""),
        "accepted_generation_business_date": str(accepted_generation_binding.get("accepted_generation_business_date") or ""),
        "accepted_generation_binding_status": str(accepted_generation_binding.get("generation_binding_status") or ""),
        "safety_context": safety_context,
        "strategy_item_lineage": item_lineage,
        "strategy_artifact_eligibility": _strategy_artifact_eligibility(runtime_planning_payload),
        "cash_feasible_buy_batch": cash_feasible_batch,
        "planning_consumer_eligibility": "ELIGIBLE" if pending_items else ("REVIEW_REQUIRED" if reason_codes else "NO_ORDER_AUTHORIZED"),
        "production_decision_allowed": bool(pending_items),
        "broker_write_allowed": _broker_write_allowed(mode, environment_capability_context),
        "broker_write_performed": False,
        "legacy_planning_authority_used": False,
        "legacy_formal_planning_authority_active": False,
        "legacy_comparison_artifact_present": False,
        "runtime_switch_performed": False,
        "silent_fallback_used": False,
        "latest_fallback_used": False,
        "future_information_used": False,
    }
    _write_json(order_plan_path, order_plan_payload)
    pending = promote_order_plan_to_pending(
        order_plan_id=order_plan_payload["order_plan_id"],
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash=_file_hash(order_plan_path),
        environment=mode,
        plan_created_date=business_date,
        intended_submit_date=target_session_date,
        target_session_date=target_session_date,
        items=tuple(pending_items),
        planning_lineage_context=_planning_lineage_context(order_plan_payload=order_plan_payload),
        submit_policy_context=submit_policy_context,
    )
    pending = replace(
        pending,
        accepted_generation_binding=accepted_generation_binding or None,
        accepted_generation_id=str(accepted_generation_binding.get("accepted_generation_id") or ""),
        accepted_generation_business_date=str(accepted_generation_binding.get("accepted_generation_business_date") or ""),
        accepted_generation_binding_status=str(accepted_generation_binding.get("generation_binding_status") or ""),
    )
    if safety_context:
        pending = replace(
            pending,
            safety_context=safety_context,
            safety_decision_id=str(safety_context.get("safety_decision_id") or ""),
            safety_policy_version=str(safety_context.get("safety_policy_version") or ""),
        )
    pending_commit_status = "COMMITTED_CURRENT"
    pending_authority_eligibility = "AUTHORITY_ELIGIBLE"
    pending_retry_eligibility = "RETRY_INPUT_ELIGIBLE"
    atomic_commit_decision = "COMMIT"
    if pending_items:
        request = build_approval_request(
            pending_plan=pending,
            business_date=business_date,
            expires_at=f"{business_date}T15:00:00+09:00",
        )
        approval = build_approval_artifact(
            request=request,
            decision=ApprovalDecision(
                status=ApprovalStatus.APPROVED,
                approved_item_ids=tuple(item.pending_item_id for item in pending_items),
                rejected_item_ids=(),
                reason="phase23_i_strategy_planning_authority_auto_approval_for_runtime_test_submit_decision",
                operator="runtime_v2_strategy_planning_authority",
                decided_at=f"{business_date}T08:45:00+09:00",
                approved_order_conditions=build_approved_order_conditions(
                    pending_items=pending_items,
                    target_session_date=target_session_date,
                ),
            ),
        )
        _write_json(approval_path, _jsonable(approval))
        pending = link_approval_to_pending(
            pending_plan=pending,
            approval_artifact=approval,
            planning_submit_feasibility_current=load_runtime_current_exposure(
                runtime_root_path / "persistent_ledger" / "state.json"
            ),
            planning_submit_feasibility_policy=submit_feasibility_policy,
        )
    elif reason_codes:
        _write_json(approval_path, {"status": "REVIEW_REQUIRED", "reason": "strategy_planning_authority_unresolved", "business_date": business_date, "reason_codes": sorted(set(reason_codes))})
        pending = replace(pending, state=PendingPlanState.REVIEW_REQUIRED)
        pending_commit_status = "NOT_COMMITTED_REVIEW_REQUIRED_EMPTY_UNSCOPED"
        pending_authority_eligibility = "AUTHORITY_INELIGIBLE"
        pending_retry_eligibility = "RETRY_INPUT_INELIGIBLE"
        atomic_commit_decision = "SKIP_CURRENT_PENDING_COMMIT"
    else:
        _write_no_order_approval_artifact(
            approval_path=approval_path,
            pending_plan_id=pending.pending_plan_id,
            order_plan_payload=order_plan_payload,
            order_plan_path=order_plan_path,
            runtime_planning_payload=runtime_planning_payload,
            runtime_planning_path=runtime_planning_path,
            position_sizing_path=position_sizing_path,
            business_date=business_date,
            target_session_date=target_session_date,
        )
        pending = replace(pending, state=PendingPlanState.EMPTY)
    if pending_commit_status == "COMMITTED_CURRENT":
        write_pending_order_plan(pending_path, pending)
    return StrategyPlanningAuthorityResult(
        status="PASS" if pending_items else ("REVIEW_REQUIRED" if reason_codes else "NO_ORDER_AUTHORIZED"),
        reason="" if pending_items else ("strategy_planning_authority_unresolved" if reason_codes else "strategy_planning_no_order_authorized"),
        business_date=business_date,
        mode=mode,
        strategy_dir=str(strategy_path),
        runtime_planning_artifact_path=str(runtime_planning_path),
        position_sizing_artifact_path=str(position_sizing_path),
        order_plan_artifact_path=str(order_plan_path),
        pending_path=str(pending_path),
        approval_artifact_path=str(approval_path),
        pending_plan_id=pending.pending_plan_id,
        plan_count=len(plans),
        pending_item_count=len(pending_items),
        selected_symbols=tuple(item.symbol for item in pending_items),
        strategy_artifact_eligibility=order_plan_payload["strategy_artifact_eligibility"],
        planning_consumer_eligibility=order_plan_payload["planning_consumer_eligibility"],
        production_decision_allowed=bool(pending_items),
        broker_write_allowed=order_plan_payload["broker_write_allowed"],
        broker_write_performed=False,
        legacy_planning_authority_used=False,
        legacy_formal_planning_authority_active=False,
        legacy_comparison_artifact_present=False,
        runtime_switch_performed=False,
        no_action=not pending_items and not reason_codes,
        reason_codes=tuple(sorted(set(reason_codes))),
        lineage={
            **lineage,
            "items": item_lineage,
            "cash_feasible_buy_batch": cash_feasible_batch,
            "safety_authority": _safety_lineage(safety_context=safety_context),
            "submit_policy_authority": _submit_policy_lineage(submit_policy_context=submit_policy_context),
        },
        pending_commit_status=pending_commit_status,
        pending_authority_eligibility=pending_authority_eligibility,
        pending_retry_eligibility=pending_retry_eligibility,
        atomic_commit_decision=atomic_commit_decision,
    )


def _cash_feasible_buy_batch(
    *,
    items: tuple[PendingOrderItem, ...],
    current: RuntimeCurrentExposure,
    policy: Any | None,
    business_date: str,
    mode: str,
) -> tuple[tuple[PendingOrderItem, ...], dict[str, Any]]:
    buy_items = tuple(item for item in items if item.side.upper() == "BUY")
    starting_cash = current.cash
    starting_buying_power = current.buying_power
    evidence: dict[str, Any] = {
        "contract_id": "phase30_ak3r2b_reserved_notional_aware_cash_feasible_buy_batch_v1",
        "authority": "PLANNING_PENDING_BUY_BATCH_CONSTRUCTION_USING_CANONICAL_RESERVED_NOTIONAL_AND_CANONICAL_STRATEGY_PRIORITY",
        "canonical_reserved_notional_producer": "runtime_v2.order_reservation.resolve_order_cash_reservation",
        "canonical_buy_priority_authority": "STRATEGY_RUNTIME_PLANNING_ORDER_DERIVED_FROM_PORTFOLIO_CONSTRUCTION_AND_POSITION_SIZING",
        "selection_semantic": "PRIORITY_ORDERED_RESERVED_NOTIONAL_SKIP_AND_CONTINUE_PRUNING",
        "new_investment_priority_created": False,
        "new_batch_optimization_created": False,
        "atomic_batch_requires_all_original_buy_candidates": False,
        "cash_pruned_valid_batch_can_submit": True,
        "cash_pruned_item_semantic": "DEFERRED_INSUFFICIENT_RESERVED_CASH",
        "ak2_one_lot_cash_priority_special_case_required": False,
        "starting_cash": starting_cash,
        "starting_buying_power": starting_buying_power,
        "candidate_buy_count": len(buy_items),
        "included_buy_count": 0,
        "cash_pruned_count": 0,
        "final_reserved_notional_total": 0.0,
        "remaining_reserved_cash": starting_cash,
        "priority_order_preservation": "PASS",
        "status": "PASS",
        "reason": "cash_feasible_buy_batch_constructed",
        "items": [],
    }
    if not buy_items:
        return items, evidence
    if policy is None:
        evidence.update(
            {
                "status": "NOT_APPLIED",
                "reason": "submit_feasibility_policy_missing",
                "priority_order_preservation": "NOT_APPLIED",
            }
        )
        return items, evidence

    active_items: list[PendingOrderItem] = []
    reserved_cash = current.cash
    reserved_buying_power = current.buying_power
    reserved_exposure = current.current_exposure
    reserved_positions = dict(current.positions)
    buy_priority_index = 0
    included_buy_count = 0
    cash_pruned_count = 0
    final_reserved_notional_total = 0.0

    for item in items:
        if item.side.upper() != "BUY":
            active_items.append(item)
            continue
        buy_priority_index += 1
        cash_before = reserved_cash
        reserved_cash_before = None if starting_cash is None or reserved_cash is None else starting_cash - reserved_cash
        remaining_cash_before = reserved_cash
        reserved_current = RuntimeCurrentExposure(
            cash=reserved_cash,
            buying_power=reserved_buying_power,
            current_exposure=reserved_exposure,
            current_total_equity=current.current_total_equity,
            active_deployment_capital=current.active_deployment_capital,
            selected_capital_source=current.selected_capital_source,
            capital_fallback_used=current.capital_fallback_used,
            initial_or_bootstrap_capital=current.initial_or_bootstrap_capital,
            positions=reserved_positions,
            position_market_values=dict(current.position_market_values),
            current_position_source=current.current_position_source,
            selected_current_source=current.selected_current_source,
            selected_cash_source=current.selected_cash_source,
            selected_positions_source=current.selected_positions_source,
            selected_valuation_source=current.selected_valuation_source,
            selected_projection_source=current.selected_projection_source,
            current_authority_winner=current.current_authority_winner,
            current_source_business_date=current.current_source_business_date,
            current_source_generation=current.current_source_generation,
            current_authority_status=current.current_authority_status,
            current_authority_reason=current.current_authority_reason,
            source_conflict_detected=current.source_conflict_detected,
            source_selection_reason=current.source_selection_reason,
            legacy_current_used=current.legacy_current_used,
            current_fallback_used=current.current_fallback_used,
            runtime_evaluation_capital_used_as_current=current.runtime_evaluation_capital_used_as_current,
        )
        item_result = evaluate_buy_item_submit_feasibility(
            item=item,
            policy=policy,
            current=reserved_current,
            authority_source="phase30_ak3r2b_cash_feasible_buy_batch_construction",
            sequence_index=buy_priority_index - 1,
            business_date=business_date,
            runtime_mode=mode,
        )
        reserved_notional = float(item_result.get("reserved_notional") or item.reserved_notional or item.estimated_amount or 0.0)
        decision = "INCLUDE"
        reason = str(item_result.get("reason") or "planning_submit_feasibility_pass")
        reserved_cash_after = reserved_cash
        if item_result.get("status") == "PASS":
            active_items.append(item)
            included_buy_count += 1
            final_reserved_notional_total = round(final_reserved_notional_total + reserved_notional, 2)
            if reserved_cash is not None:
                reserved_cash = reserved_cash - reserved_notional
                reserved_cash_after = reserved_cash
            if reserved_buying_power is not None:
                reserved_buying_power = reserved_buying_power - reserved_notional
            reserved_exposure += reserved_notional
            reserved_positions.setdefault(item.symbol, float(item.quantity or 0.0))
        elif str(item_result.get("violated_policy") or "") in {"cash", "buying_power"}:
            decision = "PRUNE"
            reason = "DEFERRED_INSUFFICIENT_RESERVED_CASH"
            cash_pruned_count += 1
        else:
            decision = "INCLUDE_REVIEW_REQUIRED"
            active_items.append(item)
            reserved_cash_after = reserved_cash

        evidence["items"].append(
            {
                "symbol": item.symbol,
                "pending_item_id": item.pending_item_id,
                "canonical_priority_index": buy_priority_index,
                "canonical_marginal_capital_priority_index": item.canonical_marginal_capital_priority_index,
                "marginal_capital_value_class": item.marginal_capital_value_class,
                "marginal_capital_value_authority": dict(item.marginal_capital_value_authority or {}),
                "canonical_strategy_order_index": item.canonical_strategy_order_index,
                "canonical_strategy_order_source": item.canonical_strategy_order_source,
                "executable_quantity": item.quantity,
                "reservation_price": item_result.get("reservation_price", item.reservation_price),
                "reserved_notional": reserved_notional,
                "cash_before_item": cash_before,
                "reserved_cash_before_item": reserved_cash_before,
                "remaining_cash_before_item": remaining_cash_before,
                "decision": decision,
                "reason": reason,
                "reserved_cash_after_item": reserved_cash_after,
                "source_submit_feasibility_status": str(item_result.get("status") or ""),
                "source_violated_policy": str(item_result.get("violated_policy") or ""),
            }
        )

    evidence.update(
        {
            "included_buy_count": included_buy_count,
            "cash_pruned_count": cash_pruned_count,
            "final_reserved_notional_total": final_reserved_notional_total,
            "remaining_reserved_cash": reserved_cash,
            "priority_order_preservation": "PASS"
            if [row["symbol"] for row in evidence["items"]] == [item.symbol for item in buy_items]
            else "REVIEW_REQUIRED",
        }
    )
    return tuple(active_items), evidence


def _canonical_marginal_capital_pending_order(items: tuple[PendingOrderItem, ...]) -> tuple[PendingOrderItem, ...]:
    indexed = list(enumerate(items))

    def key(item: tuple[int, PendingOrderItem]) -> tuple[Any, ...]:
        index, pending_item = item
        if pending_item.side.upper() == "BUY":
            priority = pending_item.canonical_marginal_capital_priority_index
            return (0, priority if priority is not None else 999999, index)
        return (1, index)

    return tuple(item for _, item in sorted(indexed, key=key))


def _pending_item_from_strategy_plan(
    *,
    plan: Mapping[str, Any],
    sizing: Mapping[str, Any],
    business_date: str,
    mode: str,
    runtime_root: Path,
    submit_feasibility_policy: Any | None,
    submit_feasibility_current: RuntimeCurrentExposure,
    runtime_planning_path: Path,
    strategy_authority_context: Mapping[str, Any] | None = None,
) -> tuple[PendingOrderItem | None, str]:
    symbol = str(plan.get("security_code") or "")
    intent = str(plan.get("planning_intent") or "")
    side = str(plan.get("order_side_intent") or "")
    if intent in {"NO_ACTION", "NO_ORDER"} or side == "NONE":
        return None, "no_action_strategy_intent"
    if side not in {"BUY", "SELL"}:
        return None, "strategy_plan_order_side_unresolved"
    planned_quantity = _planned_quantity(plan)
    if planned_quantity is None:
        return None, f"strategy_plan_quantity_schema_invalid:{symbol}"
    if planned_quantity <= 0:
        return None, f"strategy_plan_quantity_unresolved:{symbol}"
    price_resolution = _resolve_plan_price_authority(plan=plan, symbol=symbol, business_date=business_date)
    if price_resolution["status"] != "PASS":
        return None, f"{price_resolution['reason']}:{symbol}"
    price = float(price_resolution["resolved_price"])
    quantity_contract = _planning_quantity_contract(
        plan=plan,
        sizing=sizing,
        symbol=symbol,
        side=side,
        intent=intent,
        planned_quantity=planned_quantity,
        price=price,
        price_resolution=price_resolution,
        business_date=business_date,
        mode=mode,
        runtime_root=runtime_root,
        submit_feasibility_policy=submit_feasibility_policy,
        submit_feasibility_current=submit_feasibility_current,
        runtime_planning_path=runtime_planning_path,
        strategy_authority_context=strategy_authority_context,
    )
    pending_item_id = "strategy-" + hashlib.sha256(
        f"{business_date}|{symbol}|{intent}|{side}|{plan.get('planning_id')}".encode("utf-8")
    ).hexdigest()[:20]
    listed_info, listed_info_reason = _listed_info_for_strategy_pending(
        symbol=symbol,
        business_date=business_date,
        side=side,
        plan=plan,
        strategy_authority_context=strategy_authority_context,
    )
    if side == "SELL" and listed_info is None:
        return None, f"{listed_info_reason or 'strategy_sell_canonical_listed_info_missing'}:{symbol}"
    reservation = resolve_order_cash_reservation(
        runtime_root=runtime_root,
        business_date=business_date,
        symbol=symbol,
        side=side,
        order_type="MARKET",
        quantity=float(planned_quantity),
        reference_price=price,
        reference_price_authority=dict(plan.get("reference_price_authority") or {}),
    )
    source_decision_id = _strategy_plan_source_decision_id(plan, quantity_contract) if side == "BUY" else ""
    source_pm_decision_id = str(plan.get("pm_position_reference") or quantity_contract.get("source_pm_decision_id") or "")
    position_campaign_id = _strategy_plan_position_campaign_id(plan, quantity_contract) if side == "BUY" else ""
    return PendingOrderItem(
        pending_item_id=pending_item_id,
        symbol=symbol,
        side=side,
        quantity=float(planned_quantity),
        order_type="MARKET",
        estimated_price=price,
        estimated_amount=round(float(planned_quantity) * price, 2),
        approved=False,
        state="CREATED",
        listed_info=listed_info,
        price_source="jquants_raw_normalized_daily_quotes_close",
        price_as_of=str(price_resolution.get("price_date") or business_date),
        price_confidence="PIT",
        reference_price=price,
        reference_price_authority=dict(plan.get("reference_price_authority") or {}),
        reservation_price=reservation["reservation_price"],
        reservation_price_type=reservation["reservation_price_type"],
        reservation_price_authority=reservation["reservation_price_authority"],
        reservation_reason=reservation["reservation_reason"],
        reserved_notional=reservation["reserved_notional"],
        capital_allocation_amount=round(float(planned_quantity) * price, 2),
        policy_version="phase22_strategy_planning_authority",
        policy_source=str(plan.get("planning_id") or ""),
        planning_authority_version="phase22_strategy_planning_authority",
        planning_authority_source=str(plan.get("planning_id") or ""),
        planning_authority_hash=str(plan.get("planning_hash") or ""),
        buy_notional_policy="phase22_position_sizing_incremental_notional",
        sizing_policy_reason="derived_from_phase22_position_sizing_target_notional",
        quantity_contract=quantity_contract,
        strategy_authority_lineage=(
            dict(plan["strategy_authority_lineage"])
            if isinstance(plan.get("strategy_authority_lineage"), Mapping)
            else None
        ),
        strategy_authority_lineage_hash=str(
            (plan.get("strategy_authority_lineage") or {}).get("lineage_hash")
            if isinstance(plan.get("strategy_authority_lineage"), Mapping)
            else ""
        ),
        source_decision_id=source_decision_id,
        source_decision_type=intent,
        source_pm_decision_id=source_pm_decision_id,
        source_pm_business_date=business_date,
        source_position_symbol=symbol,
        position_campaign_id=position_campaign_id,
        add_candidate_signal=intent in {"BUY_NEW", "BUY_ADD"},
        capital_allocation_status="APPROVED",
        capital_allocation_reason="phase22_strategy_position_sizing_consumed",
        canonical_marginal_capital_priority_index=_int_or_none(plan.get("canonical_marginal_capital_priority_index")),
        marginal_capital_value_class=str(plan.get("marginal_capital_value_class") or ""),
        marginal_capital_value_authority=dict(plan.get("marginal_capital_value_authority") or {}),
        canonical_strategy_order_index=_int_or_none(plan.get("canonical_strategy_order_index")),
        canonical_strategy_order_source=str(plan.get("canonical_strategy_order_source") or ""),
    ), "pending_item_generated"


def _strategy_plan_source_decision_id(plan: Mapping[str, Any], quantity_contract: Mapping[str, Any]) -> str:
    lineage = plan.get("strategy_authority_lineage") if isinstance(plan.get("strategy_authority_lineage"), Mapping) else {}
    item = lineage.get("item") if isinstance(lineage.get("item"), Mapping) else {}
    return _first_text(
        plan.get("source_decision_id"),
        quantity_contract.get("source_decision_id"),
        plan.get("planning_id"),
        plan.get("portfolio_construction_reference"),
        item.get("pc_member_id"),
        quantity_contract.get("quality_decision_id"),
    )


def _strategy_plan_position_campaign_id(plan: Mapping[str, Any], quantity_contract: Mapping[str, Any]) -> str:
    lineage = plan.get("strategy_authority_lineage") if isinstance(plan.get("strategy_authority_lineage"), Mapping) else {}
    item = lineage.get("item") if isinstance(lineage.get("item"), Mapping) else {}
    return _first_text(
        plan.get("position_campaign_id"),
        plan.get("pm_position_campaign_id"),
        plan.get("current_position_campaign_id"),
        quantity_contract.get("position_campaign_id"),
        quantity_contract.get("pm_position_campaign_id"),
        lineage.get("position_campaign_id"),
        lineage.get("pm_position_campaign_id"),
        item.get("position_campaign_id"),
        item.get("pm_position_campaign_id"),
    )


def _same_day_pm_sell_exit_provenance_by_symbol(
    *,
    runtime_root: Path,
    strategy_path: Path,
    business_date: str,
) -> dict[str, StrategySellExitProvenance]:
    candidates: dict[str, list[tuple[int, StrategySellExitProvenance]]] = {}
    for source_priority, path in enumerate(_same_day_pm_decision_artifact_paths(
        runtime_root=runtime_root,
        strategy_path=strategy_path,
        business_date=business_date,
    )):
        payload = _read_json_optional(path)
        for row in payload.get("decisions") or ():
            if not isinstance(row, Mapping):
                continue
            provenance = _strategy_sell_exit_provenance_from_pm_row(
                row=row,
                payload=payload,
                business_date=business_date,
            )
            if provenance is None:
                continue
            candidates.setdefault(provenance.symbol, []).append((source_priority, provenance))
    resolved: dict[str, StrategySellExitProvenance] = {}
    for symbol, rows in candidates.items():
        for priority in sorted({priority for priority, _ in rows}):
            priority_rows = [row for row_priority, row in rows if row_priority == priority]
            unique_identity = {
                (
                    row.source_decision_id,
                    row.source_decision_type,
                    row.business_date,
                ): row
                for row in priority_rows
            }
            explicit_campaigns = {row.position_campaign_id for row in priority_rows if row.position_campaign_id}
            if len(unique_identity) == 1 and len(explicit_campaigns) <= 1:
                row = next(iter(unique_identity.values()))
                resolved[symbol] = StrategySellExitProvenance(
                    symbol=row.symbol,
                    business_date=row.business_date,
                    source_decision_id=row.source_decision_id,
                    source_decision_type=row.source_decision_type,
                    position_campaign_id=next(iter(explicit_campaigns)) if explicit_campaigns else "",
                )
                break
    return resolved


def _same_day_pm_decision_artifact_paths(
    *,
    runtime_root: Path,
    strategy_path: Path,
    business_date: str,
) -> tuple[Path, ...]:
    strategy_dir = strategy_path if strategy_path.is_dir() else strategy_path.parent
    day_dir = strategy_dir.parent if strategy_dir.name in {"strategy", "strategy_eod_shadow"} else strategy_path.parent
    paths = (
        strategy_dir / "position_management.json",
        day_dir / "strategy" / "position_management.json",
        day_dir / "strategy_eod_shadow" / "position_management.json",
        day_dir / "position_management" / "pm_decisions.json",
        runtime_root / "runtime_state" / "position_management" / business_date / "position_management_decisions.json",
    )
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return tuple(path for path in unique if path.is_file())


def _strategy_sell_exit_provenance_from_pm_row(
    *,
    row: Mapping[str, Any],
    payload: Mapping[str, Any],
    business_date: str,
) -> StrategySellExitProvenance | None:
    row_business_date = str(row.get("business_date") or payload.get("business_date") or business_date)
    if row_business_date != business_date:
        return None
    symbol = str(row.get("symbol") or row.get("security_code") or "").strip()
    if not symbol:
        return None
    decision = str(row.get("decision") or row.get("decision_type") or "").upper()
    status = str(row.get("decision_status") or "").upper()
    if decision != "EXIT" and status != "SELL_FULL_POSITION":
        return None
    source_decision_id = str(row.get("decision_id") or row.get("pm_decision_id") or "").strip()
    if not source_decision_id or source_decision_id.startswith("runtime-current-"):
        return None
    return StrategySellExitProvenance(
        symbol=symbol,
        business_date=row_business_date,
        source_decision_id=source_decision_id,
        source_decision_type="EXIT",
        position_campaign_id=str(row.get("position_campaign_id") or "").strip(),
    )


def _pending_item_with_strategy_sell_exit_pm_provenance(
    *,
    item: PendingOrderItem,
    plan: Mapping[str, Any],
    provenance_by_symbol: Mapping[str, StrategySellExitProvenance],
    business_date: str,
) -> PendingOrderItem:
    if item.side.upper() != "SELL" or str(item.source_decision_type or "").upper() != "SELL_EXIT":
        return item
    provenance = provenance_by_symbol.get(item.symbol)
    if provenance is None:
        return item
    if provenance.business_date != business_date:
        return item
    if _strategy_sell_exit_campaign_conflict(plan=plan, item=item, provenance=provenance):
        return item

    contract = dict(item.quantity_contract or {})
    contract.setdefault("planning_intent", "SELL_EXIT")
    contract.setdefault("source_decision_id", provenance.source_decision_id)
    contract.setdefault("source_pm_decision_id", provenance.source_decision_id)
    contract.setdefault("source_decision_type", provenance.source_decision_type)
    contract.setdefault("source_pm_business_date", provenance.business_date)
    contract.setdefault("source_position_symbol", provenance.symbol)
    if provenance.position_campaign_id:
        contract.setdefault("position_campaign_id", provenance.position_campaign_id)

    lineage = dict(item.strategy_authority_lineage or {})
    lineage.setdefault("source_decision_id", provenance.source_decision_id)
    lineage.setdefault("source_pm_decision_id", provenance.source_decision_id)
    lineage.setdefault("source_decision_type", provenance.source_decision_type)
    lineage.setdefault("source_pm_business_date", provenance.business_date)
    lineage.setdefault("source_position_symbol", provenance.symbol)
    if provenance.position_campaign_id:
        lineage.setdefault("position_campaign_id", provenance.position_campaign_id)

    return replace(
        item,
        quantity_contract=contract,
        strategy_authority_lineage=lineage or item.strategy_authority_lineage,
        source_decision_id=provenance.source_decision_id,
        source_decision_type=provenance.source_decision_type,
        source_pm_decision_id=provenance.source_decision_id,
        source_pm_business_date=provenance.business_date,
        source_position_symbol=provenance.symbol,
        position_campaign_id=provenance.position_campaign_id,
    )


def _strategy_sell_exit_campaign_conflict(
    *,
    plan: Mapping[str, Any],
    item: PendingOrderItem,
    provenance: StrategySellExitProvenance,
) -> bool:
    if not provenance.position_campaign_id:
        return False
    lineage = item.strategy_authority_lineage if isinstance(item.strategy_authority_lineage, Mapping) else {}
    contract = item.quantity_contract if isinstance(item.quantity_contract, Mapping) else {}
    explicit_values = (
        getattr(item, "position_campaign_id", ""),
        plan.get("position_campaign_id"),
        plan.get("pm_position_campaign_id"),
        plan.get("current_position_campaign_id"),
        lineage.get("position_campaign_id"),
        lineage.get("pm_position_campaign_id"),
        contract.get("position_campaign_id"),
        contract.get("pm_position_campaign_id"),
    )
    for value in explicit_values:
        text = str(value or "").strip()
        if text and text != provenance.position_campaign_id:
            return True
    return False


def _read_json_optional(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}



def _rank_authority_lineage_from_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    opportunity_authority = plan.get("opportunity_authority") if isinstance(plan.get("opportunity_authority"), Mapping) else {}
    source_rank = plan.get("opportunity_buy_rank")
    if source_rank in (None, ""):
        source_rank = opportunity_authority.get("opportunity_buy_rank", opportunity_authority.get("opportunity_rank"))
    source_path = str(plan.get("opportunity_artifact_path") or opportunity_authority.get("opportunity_artifact_path") or "")
    source_hash = str(plan.get("opportunity_artifact_hash") or opportunity_authority.get("opportunity_artifact_hash") or "")
    row_id = str(plan.get("opportunity_row_id") or opportunity_authority.get("opportunity_row_id") or "")
    row_hash = str(plan.get("opportunity_row_authority_hash") or opportunity_authority.get("row_authority_hash") or "")
    rank_authority = str(plan.get("rank_authority") or "")
    if not rank_authority and source_rank not in (None, ""):
        rank_authority = "OPPORTUNITY_BUY_RANK_AUTHORITY"
    portfolio_rank = plan.get("portfolio_input_opportunity_rank")
    if portfolio_rank in (None, ""):
        portfolio_rank = source_rank
    sizing_rank = plan.get("position_sizing_opportunity_buy_rank")
    if sizing_rank in (None, ""):
        sizing_rank = source_rank
    return {
        "opportunity_buy_rank": _int_or_none(source_rank),
        "portfolio_input_opportunity_rank": _int_or_none(portfolio_rank),
        "position_sizing_opportunity_buy_rank": _int_or_none(sizing_rank),
        "rank_authority_status": str(plan.get("rank_authority_status") or ("PASS" if source_rank not in (None, "") else "")),
        "rank_authority": rank_authority,
        "rank_authority_field": str(plan.get("rank_authority_field") or ("buy_rank" if source_rank not in (None, "") else "")),
        "rank_authority_reason": str(plan.get("rank_authority_reason") or ""),
        "opportunity_row_id": row_id,
        "opportunity_row_authority_hash": row_hash,
        "opportunity_artifact_path": source_path,
        "opportunity_artifact_hash": source_hash,
    }


def _planning_quantity_contract(
    *,
    plan: Mapping[str, Any],
    sizing: Mapping[str, Any],
    symbol: str,
    side: str,
    intent: str,
    planned_quantity: int,
    price: float,
    price_resolution: Mapping[str, Any],
    business_date: str,
    mode: str,
    runtime_root: Path,
    submit_feasibility_policy: Any | None,
    submit_feasibility_current: RuntimeCurrentExposure,
    runtime_planning_path: Path,
    strategy_authority_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    selected_dynamic_position_count = None
    position_count_fields: dict[str, Any] = {}
    cash_exposure_fields: dict[str, Any] = {}
    position_sizing_fields: dict[str, Any] = {}
    authority_context = strategy_authority_context if isinstance(strategy_authority_context, Mapping) else {}
    position_count_context = authority_context.get("position_count_authority")
    if not isinstance(position_count_context, Mapping):
        position_count_context = None
    elif _first_int(
        position_count_context.get("selected_dynamic_position_count"),
        position_count_context.get("target_position_count"),
        position_count_context.get("actual_target_position_count"),
        position_count_context.get("dynamic_position_count"),
    ) is None:
        position_count_context = None
    cash_exposure_context = authority_context.get("cash_exposure_authority")
    if not isinstance(cash_exposure_context, Mapping):
        cash_exposure_context = None
    elif _first_float(
        cash_exposure_context.get("selected_dynamic_cash_ratio"),
        cash_exposure_context.get("target_cash_ratio"),
    ) is None or _first_float(
        cash_exposure_context.get("selected_dynamic_exposure_ratio"),
        cash_exposure_context.get("target_gross_exposure_ratio"),
    ) is None:
        cash_exposure_context = None
    position_sizing_context = _position_sizing_authority_context_for_symbol(
        authority_context=authority_context,
        sizing=sizing,
        symbol=symbol,
    )
    if submit_feasibility_policy is not None:
        position_count_authority = resolve_position_count_authority(
            runtime_root=None if position_count_context is not None else runtime_root,
            business_date=business_date,
            runtime_mode=mode,
            current_position_count=len(submit_feasibility_current.positions),
            configured_legacy_max_positions=submit_feasibility_policy.max_positions,
            policy_context=position_count_context,
            consumer="strategy_planning_authority_position_count",
        )
        selected_dynamic_position_count = position_count_authority.selected_dynamic_position_count
        position_count_fields = position_count_authority.to_dict()
        cash_exposure_authority = resolve_cash_exposure_authority(
            runtime_root=None if cash_exposure_context is not None else runtime_root,
            business_date=business_date,
            runtime_mode=mode,
            current_total_equity=submit_feasibility_current.current_total_equity,
            active_deployment_capital=submit_feasibility_current.active_deployment_capital,
            current_cash=submit_feasibility_current.cash,
            current_market_value=submit_feasibility_current.current_exposure,
            policy_context=cash_exposure_context,
            consumer="strategy_planning_authority_cash_exposure",
        )
        cash_exposure_fields = cash_exposure_authority.to_dict()
        if side == "BUY":
            position_sizing_authority = resolve_position_sizing_authority(
                symbol=symbol,
                runtime_root=None if position_sizing_context else runtime_root,
                business_date=business_date,
                runtime_mode=mode,
                active_deployment_capital=submit_feasibility_current.active_deployment_capital,
                selected_dynamic_exposure_ratio=cash_exposure_authority.selected_dynamic_exposure_ratio,
                selected_runtime_exposure_limit=cash_exposure_authority.selected_runtime_exposure_limit,
                selected_dynamic_position_count=selected_dynamic_position_count,
                current_position_market_value=_position_market_value(submit_feasibility_current, symbol),
                policy_context=position_sizing_context,
                consumer="strategy_planning_authority_position_sizing",
            )
            position_sizing_fields = position_sizing_authority.with_lot_adjustment(
                quantity=planned_quantity,
                notional=round(float(planned_quantity) * float(price), 2),
            ).to_dict()
    requested_notional = sizing.get("incremental_buy_notional") if side == "BUY" else sizing.get("current_notional")
    selected_notional = round(float(planned_quantity) * float(price), 2)
    binding_constraint = (
        str(position_sizing_fields.get("position_sizing_binding_constraint") or "")
        if side == "BUY"
        else "SELL_EXIT_REDUCE_AUTHORITY"
    )
    return {
        "quantity_contract_version": "runtime_v2_strategy_planning_quantity_v2",
        "quantity_authority": "strategy_runtime_planning_authority",
        "planning_source": str(runtime_planning_path),
        "planning_authority_winner": "strategy_runtime_planning",
        "planning_consumer": "runtime_v2.planning.strategy_authority.activate_strategy_planning_authority",
        "planning_action": side,
        "planning_status": "PASS",
        "planning_intent": intent,
        "planning_intent_source": str(plan.get("planning_id") or ""),
        "planning_quantity_source": "position_sizing_quantity_candidate" if side == "BUY" else "sell_reduce_exit_quantity_contract",
        "planning_notional_source": "position_sizing_selected_notional" if side == "BUY" else "current_position_sell_notional",
        "planning_binding_constraint": binding_constraint,
        "planning_review_reason": "",
        "requested_quantity": plan.get("quantity_delta_candidate"),
        "selected_quantity": planned_quantity,
        "requested_notional": requested_notional,
        "selected_notional": selected_notional,
        "source_planning_id": str(plan.get("planning_id") or ""),
        "source_position_sizing_reference": str(sizing.get("position_reference") or ""),
        "planned_quantity": planned_quantity,
        "target_quantity_candidate": plan.get("target_quantity_candidate"),
        "quantity_delta_candidate": plan.get("quantity_delta_candidate"),
        "quantity_status": plan.get("quantity_status"),
        "target_notional": sizing.get("target_notional"),
        "incremental_buy_notional": sizing.get("incremental_buy_notional"),
        "lot_rounding": "already_applied_by_position_sizing",
        "price_authority": "phase23_bo_executable_plan_price_authority",
        "reference_price": price,
        "reference_price_authority": dict(plan.get("reference_price_authority") or {}),
        "reference_price_resolution": dict(plan.get("reference_price_resolution") or price_resolution.get("resolution") or {}),
        "reference_price_type": str(plan.get("reference_price_type") or ""),
        "reference_price_date": str(plan.get("reference_price_date") or ""),
        "position_count_authority": position_count_fields,
        "cash_exposure_authority": cash_exposure_fields,
        "position_sizing_authority": position_sizing_fields,
        "buy_quality_authority": _quality_authority_from_plan(plan),
        "quality_decision_id": str(plan.get("quality_decision_id") or ""),
        "quality_score": plan.get("quality_score"),
        "quality_band": str(plan.get("quality_band") or ""),
        "quality_action": str(plan.get("quality_action") or ""),
        "quality_status": str(plan.get("quality_status") or ""),
        "quality_reason_codes": list(plan.get("quality_reason_codes") or []),
        "component_scores": dict(plan.get("component_scores") or {}),
        "component_statuses": dict(plan.get("component_statuses") or {}),
        "quality_policy_version": str(plan.get("quality_policy_version") or ""),
        "quality_allocation_adjustment": plan.get("quality_allocation_adjustment"),
        "pre_quality_base_weight": plan.get("pre_quality_base_weight"),
        "post_quality_target_weight": plan.get("post_quality_target_weight"),
        **position_count_fields,
        **cash_exposure_fields,
        **position_sizing_fields,
        "legacy_planning_used": False,
        "planning_fallback_used": False,
        "runtime_mode": mode,
        "business_date": business_date,
    }


def _position_market_value(current: RuntimeCurrentExposure, symbol: str) -> float:
    for existing_symbol, market_value in current.position_market_values.items():
        if existing_symbol == symbol:
            return float(market_value)
    return 0.0


def _strategy_authority_context(
    *,
    strategy_path: Path,
    position_sizing_path: Path,
    position_sizing_payload: Mapping[str, Any],
    portfolio_policy_path: Path,
    portfolio_policy_payload: Mapping[str, Any],
) -> dict[str, Any]:
    source_artifacts = _strategy_authority_source_artifacts(
        strategy_path=strategy_path,
        position_sizing_path=position_sizing_path,
        portfolio_policy_path=portfolio_policy_path,
    )
    source_hashes = _strategy_authority_source_hashes(
        position_sizing_path=position_sizing_path,
        portfolio_policy_path=portfolio_policy_path,
    )
    target_position_count = _first_int(
        position_sizing_payload.get("dynamic_position_count"),
        position_sizing_payload.get("target_position_count"),
        portfolio_policy_payload.get("target_position_count"),
        portfolio_policy_payload.get("meaningful_allocation_position_count"),
    )
    cash_ratio = _first_float(
        portfolio_policy_payload.get("cash_reserve_ratio"),
        portfolio_policy_payload.get("cash_reserve"),
        position_sizing_payload.get("residual_cash_ratio"),
    )
    exposure_ratio = _first_float(
        position_sizing_payload.get("target_gross_exposure_ratio"),
        position_sizing_payload.get("dynamic_cash_exposure"),
        position_sizing_payload.get("aggregate_exposure_cap"),
        portfolio_policy_payload.get("target_gross_exposure_ratio"),
        portfolio_policy_payload.get("target_gross_exposure"),
    )
    maximum_exposure_ratio = _first_float(
        portfolio_policy_payload.get("maximum_gross_exposure_ratio"),
        position_sizing_payload.get("aggregate_exposure_cap"),
        exposure_ratio,
    )
    position_count_authority = {
        "selected_dynamic_position_count": target_position_count,
        "target_position_count": target_position_count,
        "actual_target_position_count": target_position_count,
        "safety_hard_maximum": _first_int(portfolio_policy_payload.get("maximum_position_count")),
        "source_artifacts": source_artifacts,
        "source_hashes": source_hashes,
        "producer": "strategy.runtime_planning.position_sizing",
        "consumer": "runtime_v2.planning.strategy_authority.activate_strategy_planning_authority",
    }
    cash_exposure_authority = {
        "selected_dynamic_cash_ratio": cash_ratio,
        "target_cash_ratio": cash_ratio,
        "selected_dynamic_exposure_ratio": exposure_ratio,
        "target_gross_exposure_ratio": exposure_ratio,
        "maximum_gross_exposure_ratio": maximum_exposure_ratio,
        "source_artifacts": source_artifacts,
        "source_hashes": source_hashes,
        "producer": "strategy.runtime_planning.portfolio_policy_and_position_sizing",
        "consumer": "runtime_v2.planning.strategy_authority.activate_strategy_planning_authority",
    }
    position_sizing_authority = dict(position_sizing_payload)
    position_sizing_authority.setdefault("source_artifacts", source_artifacts)
    position_sizing_authority.setdefault("source_hashes", source_hashes)
    position_sizing_authority["producer"] = "strategy.position_sizing"
    position_sizing_authority["consumer"] = "runtime_v2.planning.strategy_authority.activate_strategy_planning_authority"
    input_manifest_path = strategy_path / "input_manifest.json"
    input_manifest_payload = _read_json(input_manifest_path) if input_manifest_path.is_file() else {}
    return {
        "position_count_authority": position_count_authority,
        "cash_exposure_authority": cash_exposure_authority,
        "position_sizing_authority": position_sizing_authority,
        "input_manifest_path": str(input_manifest_path),
        "strategy_source_authority": _strategy_source_authority_from_input_manifest(input_manifest_payload),
        "source_artifacts": source_artifacts,
        "source_hashes": source_hashes,
    }


def _position_sizing_authority_context_for_symbol(
    *,
    authority_context: Mapping[str, Any],
    sizing: Mapping[str, Any],
    symbol: str,
) -> Mapping[str, Any]:
    nested = authority_context.get("position_sizing_authority")
    if isinstance(nested, Mapping):
        payload = dict(nested)
        positions = [dict(item) for item in payload.get("positions") or [] if isinstance(item, Mapping)]
        if not positions and sizing:
            row = dict(sizing)
            row.setdefault("security_code", symbol)
            positions = [row]
        payload["positions"] = positions
        return payload
    row = dict(sizing)
    row.setdefault("security_code", symbol)
    return {"positions": [row], "source_artifacts": list(authority_context.get("source_artifacts") or []), "source_hashes": list(authority_context.get("source_hashes") or [])}


def _strategy_authority_source_artifacts(
    *,
    strategy_path: Path,
    position_sizing_path: Path,
    portfolio_policy_path: Path,
) -> list[dict[str, Any]]:
    artifacts = []
    if portfolio_policy_path.is_file():
        artifacts.append({"role": "portfolio_policy", "path": str(portfolio_policy_path), "required": True, "status": "PASS"})
    if position_sizing_path.is_file():
        artifacts.append({"role": "position_sizing", "path": str(position_sizing_path), "required": True, "status": "PASS"})
    dynamic_position_count_path = strategy_path / "dynamic_position_count.json"
    dynamic_cash_exposure_path = strategy_path / "dynamic_cash_exposure.json"
    if dynamic_position_count_path.is_file():
        artifacts.append({"role": "dynamic_position_count", "path": str(dynamic_position_count_path), "required": False, "status": "PASS"})
    if dynamic_cash_exposure_path.is_file():
        artifacts.append({"role": "dynamic_cash_exposure", "path": str(dynamic_cash_exposure_path), "required": False, "status": "PASS"})
    return artifacts


def _strategy_authority_source_hashes(
    *,
    position_sizing_path: Path,
    portfolio_policy_path: Path,
) -> list[dict[str, Any]]:
    hashes = []
    if portfolio_policy_path.is_file():
        hashes.append({"role": "portfolio_policy", "path": str(portfolio_policy_path), "sha256": _file_hash(portfolio_policy_path)})
    if position_sizing_path.is_file():
        hashes.append({"role": "position_sizing", "path": str(position_sizing_path), "sha256": _file_hash(position_sizing_path)})
    return hashes


def _first_float(*values: Any) -> float | None:
    for value in values:
        if value in (None, "") or isinstance(value, bool):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _first_int(*values: Any) -> int | None:
    for value in values:
        if value in (None, "") or isinstance(value, bool):
            continue
        try:
            return int(float(value))
        except (TypeError, ValueError):
            continue
    return None


def _side_planning_status(item_lineage: list[dict[str, Any]], *, side: str) -> str:
    side_items = [item for item in item_lineage if str(item.get("order_side_intent") or "").upper() == side]
    if any(bool(item.get("pending_item_generated")) for item in side_items):
        return "PASS"
    if side_items:
        return "REVIEW_REQUIRED"
    return "NO_ORDER"


def _resolve_plan_price_authority(*, plan: Mapping[str, Any], symbol: str, business_date: str) -> dict[str, Any]:
    price = _positive_float(plan.get("reference_price"))
    if price <= 0:
        return {"status": "BLOCK", "reason": "strategy_plan_price_missing", "resolved_price": None}
    authority = plan.get("reference_price_authority")
    if not isinstance(authority, Mapping) or not authority:
        return {"status": "BLOCK", "reason": "strategy_plan_price_authority_missing", "resolved_price": None}
    authority_symbol = str(authority.get("symbol") or authority.get("security_code") or "").strip()
    if authority_symbol and authority_symbol != symbol:
        return {"status": "BLOCK", "reason": "strategy_plan_price_symbol_mismatch", "resolved_price": None}
    authority_business_date = str(authority.get("business_date") or "").strip()
    if authority_business_date and authority_business_date != business_date:
        return {"status": "BLOCK", "reason": "strategy_plan_price_business_date_mismatch", "resolved_price": None}
    price_date = str(authority.get("price_date") or plan.get("reference_price_date") or "").strip()
    if price_date and price_date > business_date:
        return {"status": "BLOCK", "reason": "strategy_plan_price_future_date", "resolved_price": None}
    if str(authority.get("PIT_status") or "") != "PASS":
        return {"status": "BLOCK", "reason": "strategy_plan_price_pit_not_pass", "resolved_price": None}
    resolution = plan.get("reference_price_resolution")
    if not isinstance(resolution, Mapping) or str(resolution.get("status") or "") != "PASS":
        return {"status": "BLOCK", "reason": "strategy_plan_price_resolution_not_pass", "resolved_price": None}
    resolved = _positive_float(resolution.get("resolved_price"), default=price)
    if resolved <= 0:
        return {"status": "BLOCK", "reason": "strategy_plan_price_missing", "resolved_price": None}
    return {
        "status": "PASS",
        "reason": "strategy_plan_price_resolved",
        "resolved_price": price,
        "price_date": price_date,
        "authority": dict(authority),
        "resolution": dict(resolution),
    }


def _listed_info_for_strategy_pending(
    *,
    symbol: str,
    business_date: str,
    side: str,
    plan: Mapping[str, Any],
    strategy_authority_context: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, str]:
    opportunity = _listed_info_from_opportunity_authority(
        symbol=symbol,
        business_date=business_date,
        opportunity_authority=plan.get("opportunity_authority") if isinstance(plan.get("opportunity_authority"), Mapping) else {},
        plan=plan,
    )
    if side != "SELL":
        return opportunity, ""
    canonical, reason = _canonical_listed_info_from_strategy_source_authority(
        symbol=symbol,
        business_date=business_date,
        strategy_authority_context=strategy_authority_context,
    )
    if canonical is None:
        return None, reason
    conflict_reason = _canonical_listed_info_opportunity_conflict_reason(
        canonical=canonical,
        opportunity_authority=plan.get("opportunity_authority") if isinstance(plan.get("opportunity_authority"), Mapping) else {},
    )
    if conflict_reason:
        return None, conflict_reason
    return canonical, ""


def _canonical_listed_info_from_strategy_source_authority(
    *,
    symbol: str,
    business_date: str,
    strategy_authority_context: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, str]:
    authority_context = strategy_authority_context if isinstance(strategy_authority_context, Mapping) else {}
    authority = authority_context.get("strategy_source_authority")
    if not isinstance(authority, Mapping) or not authority:
        return None, "strategy_sell_canonical_listed_info_authority_missing"
    if str(authority.get("status") or "") != "PASS":
        return None, "strategy_sell_canonical_listed_info_authority_not_pass"
    if str(authority.get("business_date") or business_date) != business_date:
        return None, "strategy_sell_canonical_listed_info_business_date_mismatch"
    paths = authority.get("paths") if isinstance(authority.get("paths"), Mapping) else {}
    source_records = authority.get("source_records") if isinstance(authority.get("source_records"), Mapping) else {}
    record = source_records.get("listed_issues") if isinstance(source_records.get("listed_issues"), Mapping) else {}
    source_path_text = str(record.get("path") or paths.get("listed_issues") or "")
    if not source_path_text:
        return None, "strategy_sell_canonical_listed_info_source_path_missing"
    source_path = Path(source_path_text)
    if not source_path.is_file():
        return None, "strategy_sell_canonical_listed_info_source_missing"
    if record and bool(record.get("exists")) is False:
        return None, "strategy_sell_canonical_listed_info_source_record_missing"
    if record and str(record.get("pit_status") or "") != "PASS":
        return None, "strategy_sell_canonical_listed_info_pit_not_pass"
    source_hash = _file_hash(source_path)
    expected_hash = str(record.get("sha256") or "")
    if expected_hash and expected_hash != source_hash:
        return None, "strategy_sell_canonical_listed_info_source_hash_mismatch"
    try:
        import pandas as pd

        frame = pd.read_parquet(source_path)
    except Exception:
        return None, "strategy_sell_canonical_listed_info_source_unreadable"
    required_columns = {"Code"}
    if not required_columns.issubset(set(str(column) for column in frame.columns)):
        return None, "strategy_sell_canonical_listed_info_code_column_missing"
    rows = frame[frame["Code"].map(_canonical_listed_symbol) == symbol].copy()
    if rows.empty:
        return None, "strategy_sell_canonical_listed_info_no_row"
    if "Date" in rows.columns:
        rows["_authority_date"] = rows["Date"].map(lambda value: str(value)[:10])
        if any(str(value) > business_date for value in rows["_authority_date"]):
            return None, "strategy_sell_canonical_listed_info_future_dated"
        rows = rows[rows["_authority_date"] <= business_date]
        if rows.empty:
            return None, "strategy_sell_canonical_listed_info_no_pit_row"
        latest_date = max(str(value) for value in rows["_authority_date"])
        rows = rows[rows["_authority_date"] == latest_date]
    else:
        latest_date = business_date
    if len(rows) != 1:
        return None, "strategy_sell_canonical_listed_info_multiple_rows"
    row = rows.iloc[0].to_dict()
    listed_info = _listed_info_from_canonical_row(
        row=row,
        symbol=symbol,
        business_date=business_date,
        source_path=source_path,
        source_hash=source_hash,
        source_record=record,
        authority=authority,
        row_date=latest_date,
    )
    if listed_info is None:
        return None, "strategy_sell_canonical_listed_info_validation_failed"
    return listed_info, ""


def _strategy_source_authority_from_input_manifest(input_manifest: Mapping[str, Any]) -> dict[str, Any]:
    direct = input_manifest.get("strategy_source_authority")
    if isinstance(direct, Mapping):
        return dict(direct)
    sources = input_manifest.get("strategy_input_sources")
    if isinstance(sources, Mapping):
        nested = sources.get("strategy_source_authority")
        if isinstance(nested, Mapping):
            return dict(nested)
    return {}


def _listed_info_from_canonical_row(
    *,
    row: Mapping[str, Any],
    symbol: str,
    business_date: str,
    source_path: Path,
    source_hash: str,
    source_record: Mapping[str, Any],
    authority: Mapping[str, Any],
    row_date: str,
) -> dict[str, Any] | None:
    code = _canonical_listed_symbol(row.get("Code"))
    market = _first_text(row.get("MktNm"), row.get("MarketCodeName"), row.get("MarketSegment"), row.get("market"))
    product_category = _first_text(row.get("ProdCat"), row.get("ProductCategory"), row.get("product_category"))
    security_type = _first_text(row.get("SecType"), row.get("Type"), row.get("security_type"), product_category)
    current_listed = _current_listed_from_canonical_row(row)
    if code != symbol:
        return None
    if not (market and product_category and security_type):
        return None
    if current_listed is not True:
        return None
    if row_date > business_date:
        return None
    return {
        "code": code,
        "market": market,
        "product_category": product_category,
        "security_type": security_type,
        "current_listed": True,
        "listed_info_authority": "canonical_pit_listed_issues",
        "listed_info_source": str(source_path),
        "listed_info_source_artifact": str(source_path),
        "listed_info_source_hash": source_hash,
        "listed_info_expected_source_hash": str(source_record.get("sha256") or ""),
        "listed_info_business_date": business_date,
        "listed_info_row_date": row_date,
        "listed_info_row_id": f"canonical_listed_issues:{row_date}:{code}",
        "listed_info_resolution_status": "PASS",
        "listed_info_resolution_reason": "canonical_pit_listed_issues_row_authority_bound",
        "listed_info_pit_status": str(source_record.get("pit_status") or "PASS"),
        "strategy_source_authority": str(authority.get("authority") or ""),
        "strategy_source_authority_status": str(authority.get("status") or ""),
        "strategy_source_resolution_source": str(authority.get("resolution_source") or ""),
        "strategy_source_manifest_path": str(authority.get("source_manifest_path") or ""),
        "strategy_source_manifest_hash": str(authority.get("source_manifest_hash") or ""),
        "run_scoped_historical_authority_used": bool(authority.get("run_scoped_historical_authority_used")),
        "operations_latest_fallback_used": bool(authority.get("operations_latest_fallback_used")),
    }


def _canonical_listed_info_opportunity_conflict_reason(
    *,
    canonical: Mapping[str, Any],
    opportunity_authority: Mapping[str, Any],
) -> str:
    if not opportunity_authority:
        return ""
    opportunity_symbol = str(opportunity_authority.get("opportunity_symbol") or opportunity_authority.get("symbol") or "").strip()
    if opportunity_symbol and opportunity_symbol != str(canonical.get("code") or ""):
        return "strategy_sell_canonical_listed_info_opportunity_symbol_mismatch"
    if opportunity_authority.get("current_listed") is False:
        return "strategy_sell_canonical_listed_info_opportunity_current_listed_conflict"
    for source_field, canonical_field, reason in (
        ("market", "market", "strategy_sell_canonical_listed_info_opportunity_market_mismatch"),
        ("product_category", "product_category", "strategy_sell_canonical_listed_info_opportunity_product_category_mismatch"),
        ("security_type", "security_type", "strategy_sell_canonical_listed_info_opportunity_security_type_mismatch"),
    ):
        explicit = str(opportunity_authority.get(source_field) or "").strip()
        if explicit and explicit != str(canonical.get(canonical_field) or ""):
            return reason
    return ""


def _canonical_listed_symbol(value: Any) -> str:
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def _first_text(*values: Any) -> str:
    for value in values:
        if value in (None, ""):
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            return text
    return ""


def _current_listed_from_canonical_row(row: Mapping[str, Any]) -> bool | None:
    for field in ("current_listed", "CurrentListed", "IsListed", "Listed"):
        if field not in row:
            continue
        value = row.get(field)
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"true", "1", "yes", "y", "listed"}:
            return True
        if text in {"false", "0", "no", "n", "delisted"}:
            return False
    return True


def _listed_info_from_opportunity_authority(
    *,
    symbol: str,
    business_date: str,
    opportunity_authority: Mapping[str, Any],
    plan: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not opportunity_authority:
        return None
    authority_symbol = str(opportunity_authority.get("opportunity_symbol") or "").strip()
    if authority_symbol and authority_symbol != symbol:
        return None
    opportunity_business_date = str(opportunity_authority.get("opportunity_business_date") or "")
    if opportunity_business_date and opportunity_business_date != business_date:
        return None
    artifact_path = str(opportunity_authority.get("opportunity_artifact_path") or "")
    artifact_hash = str(opportunity_authority.get("opportunity_artifact_hash") or "")
    row_id = str(opportunity_authority.get("opportunity_row_id") or "")
    if not (artifact_path and artifact_hash and row_id):
        return None
    opportunity_feature_date = str(opportunity_authority.get("opportunity_feature_date") or business_date)
    plan = plan or {}
    return {
        "code": symbol,
        "market": str(opportunity_authority.get("market") or "東証"),
        "product_category": str(opportunity_authority.get("product_category") or "011"),
        "security_type": str(opportunity_authority.get("security_type") or "011"),
        "current_listed": True,
        "opportunity_authority": str(opportunity_authority.get("opportunity_authority") or "runtime_v2_opportunity_ranking_row"),
        "opportunity_source": str(opportunity_authority.get("opportunity_source") or artifact_path),
        "opportunity_artifact_path": artifact_path,
        "opportunity_artifact_hash": artifact_hash,
        "opportunity_business_date": opportunity_business_date or business_date,
        "opportunity_feature_date": opportunity_feature_date,
        "opportunity_symbol": symbol,
        "opportunity_row_id": row_id,
        "opportunity_row_authority_hash": str(opportunity_authority.get("row_authority_hash") or ""),
        "opportunity_buy_eligibility_status": str(opportunity_authority.get("opportunity_status") or "PASS"),
        "opportunity_buy_eligibility": str(opportunity_authority.get("opportunity_eligibility") or "BUY_ELIGIBLE"),
        "opportunity_expected_edge_score": opportunity_authority.get("opportunity_expected_edge_score"),
        "opportunity_expected_return": opportunity_authority.get("opportunity_expected_return"),
        "opportunity_no_buy_reason": str(opportunity_authority.get("opportunity_no_buy_reason") or ""),
        "opportunity_buy_rank": opportunity_authority.get("opportunity_buy_rank") or opportunity_authority.get("opportunity_rank"),
        "opportunity_eligibility_policy_version": "runtime_v2_opportunity_buy_eligibility_v1",
        "opportunity_eligibility_reason": "opportunity_ranking_row_authority_bound",
        "ranking_schema_version": str(opportunity_authority.get("ranking_schema_version") or ""),
        "ranking_schema_name": str(opportunity_authority.get("ranking_schema_name") or ""),
        "ranking_artifact_role": str(opportunity_authority.get("ranking_artifact_role") or ""),
        "buy_quality_authority": _quality_authority_from_plan(plan),
        "quality_decision_id": str(plan.get("quality_decision_id") or ""),
        "quality_score": plan.get("quality_score"),
        "quality_band": str(plan.get("quality_band") or ""),
        "quality_action": str(plan.get("quality_action") or ""),
        "quality_status": str(plan.get("quality_status") or ""),
        "quality_reason_codes": list(plan.get("quality_reason_codes") or []),
        "component_scores": dict(plan.get("component_scores") or {}),
        "component_statuses": dict(plan.get("component_statuses") or {}),
        "quality_policy_version": str(plan.get("quality_policy_version") or ""),
        "quality_allocation_adjustment": plan.get("quality_allocation_adjustment"),
    }


def _quality_authority_from_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    authority = plan.get("buy_quality_authority")
    if isinstance(authority, Mapping):
        return dict(authority)
    return {
        "authority_type": "ADAPTIVE_BUY_QUALITY_AUTHORITY",
        "producer": "Production Strategy BUY Quality Resolver",
        "quality_decision_id": str(plan.get("quality_decision_id") or ""),
        "quality_action": str(plan.get("quality_action") or ""),
        "quality_status": str(plan.get("quality_status") or ""),
        "source_artifact_path": str(plan.get("buy_quality_artifact_path") or ""),
        "source_artifact_hash": str(plan.get("buy_quality_artifact_hash") or ""),
    }


def _resolve_pending_safety_context(
    *,
    mode: str,
    business_date: str,
    target_session_date: str,
    safety_authority_payload: Mapping[str, Any] | None,
    environment_capability_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(safety_authority_payload or {})
    if not payload:
        return {}
    decision = str(payload.get("safety_decision") or payload.get("decision") or "").upper()
    policy_version = str(payload.get("safety_policy_version") or "")
    source = str(payload.get("safety_source") or "")
    reason = str(payload.get("safety_reason") or payload.get("reason") or "")
    safety_business_date = str(
        payload.get("safety_business_date")
        or payload.get("safety_authority_business_date")
        or target_session_date
        or business_date
    )
    context = dict(environment_capability_context or {})
    runtime_test_run_id = str(payload.get("runtime_test_run_id") or context.get("runtime_test_run_id") or "")
    runtime_test_profile_id = str(payload.get("runtime_test_profile_id") or context.get("runtime_test_profile_id") or "")
    runtime_test_evidence_root = str(payload.get("runtime_test_evidence_root") or context.get("runtime_test_evidence_root") or "")
    if mode == "historical":
        return materialize_historical_pending_safety_context(
            safety_decision_id=str(payload.get("safety_decision_id") or ""),
            safety_policy_version=policy_version or HISTORICAL_NEUTRAL_SAFETY_POLICY_VERSION,
            safety_source=source or HISTORICAL_NEUTRAL_SAFETY_SOURCE,
            safety_decision=decision,
            safety_reason=reason,
            safety_business_date=safety_business_date,
            runtime_test_run_id=runtime_test_run_id,
            runtime_test_profile_id=runtime_test_profile_id,
            runtime_test_evidence_root=runtime_test_evidence_root,
        )
    required = {
        "safety_decision_id": str(payload.get("safety_decision_id") or ""),
        "safety_policy_version": policy_version,
        "safety_source": source,
        "safety_decision": decision,
    }
    if any(not value for value in required.values()):
        return {}
    safety_authority = str(payload.get("safety_authority") or payload.get("safety_authority_type") or "runtime_safety_decision")
    return {
        "safety_authority": safety_authority,
        **required,
        "safety_reason": reason,
        "safety_business_date": safety_business_date,
        "temporal_authority_business_date": str(payload.get("temporal_authority_business_date") or safety_business_date),
        "runtime_test_run_id": runtime_test_run_id,
        "runtime_test_profile_id": runtime_test_profile_id,
        "runtime_test_evidence_root": runtime_test_evidence_root,
    }


def _resolve_submit_policy_context(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    version = str(payload.get("submit_policy_version") or payload.get("policy_version") or "")
    source = str(payload.get("submit_policy_source") or payload.get("policy_source") or "")
    policy_hash = str(payload.get("submit_policy_hash") or payload.get("policy_hash") or payload.get("active_policy_hash") or "")
    if not (version and source and policy_hash):
        return {}
    return {
        "submit_policy_version": version,
        "submit_policy_source": source,
        "submit_policy_hash": policy_hash,
        "submit_policy_authority": str(payload.get("submit_policy_authority") or "capital_deployment_policy"),
        "submit_policy_schema_version": str(payload.get("submit_policy_schema_version") or "phase23_bb_submit_policy_authority.v1"),
    }


def _accepted_generation_binding_context(
    *,
    input_manifest_path: Path,
    mode: str,
    business_date: str,
) -> dict[str, Any]:
    if not input_manifest_path.is_file():
        return {
            "schema_version": "phase26_step8_accepted_generation_binding.v1",
            "consumer": "strategy_planning_authority",
            "mode": mode,
            "requested_business_date": business_date,
            "selected_business_date": "",
            "accepted_generation_id": "",
            "accepted_generation_business_date": "",
            "generation_binding_status": "REVIEW_REQUIRED",
            "temporal_binding_status": "REVIEW_REQUIRED",
            "generation_conflict": False,
            "business_date_conflict": True,
            "selection_reason": "strategy_input_manifest_missing",
            "latest_fallback_used": False,
            "shared_state_fallback_used": False,
            "default_generation_used": False,
        }
    try:
        manifest = _read_json(input_manifest_path)
    except (OSError, json.JSONDecodeError):
        manifest = {}
    binding = manifest.get("accepted_generation_binding")
    if not isinstance(binding, Mapping):
        binding = {}
    payload = dict(binding)
    payload.setdefault("schema_version", "phase26_step8_accepted_generation_binding.v1")
    payload["consumer"] = "strategy_planning_authority"
    payload["mode"] = mode
    payload["requested_business_date"] = business_date
    payload["accepted_generation_id"] = str(payload.get("accepted_generation_id") or manifest.get("accepted_generation_id") or "")
    payload["accepted_generation_business_date"] = str(
        payload.get("accepted_generation_business_date")
        or payload.get("selected_business_date")
        or manifest.get("business_date")
        or ""
    )
    payload["generation_binding_status"] = str(payload.get("generation_binding_status") or "REVIEW_REQUIRED")
    payload["temporal_binding_status"] = str(payload.get("temporal_binding_status") or "REVIEW_REQUIRED")
    payload["business_date_conflict"] = _accepted_generation_business_date_conflict(
        binding=payload,
        business_date=business_date,
    )
    payload.setdefault("generation_conflict", False)
    payload.setdefault("latest_fallback_used", False)
    payload.setdefault("shared_state_fallback_used", False)
    payload.setdefault("default_generation_used", False)
    return payload


def _accepted_generation_business_date_conflict(*, binding: Mapping[str, Any], business_date: str) -> bool:
    if _historical_evaluation_authority_temporal_separation(binding=binding, business_date=business_date):
        return False
    accepted_business_date = str(binding.get("accepted_generation_business_date") or "")
    return bool(
        binding.get("business_date_conflict")
        or (accepted_business_date and accepted_business_date != business_date)
    )


def _historical_evaluation_authority_temporal_separation(*, binding: Mapping[str, Any], business_date: str) -> bool:
    return (
        str(binding.get("temporal_authority_source") or "") == "evaluation_authority_time"
        and str(binding.get("temporal_authority_winner") or "") == "run_start_fixed_accepted_generation"
        and str(binding.get("historical_business_date_acceptance_comparison") or "") == "NOT_APPLIED_TO_ACCEPTED_GENERATION"
        and str(binding.get("market_as_of_business_date") or "") == business_date
        and str(binding.get("requested_business_date") or "") == business_date
        and str(binding.get("generation_binding_status") or "") == "PASS"
        and str(binding.get("temporal_binding_status") or "") == "PASS"
    )


def _load_submit_feasibility_policy(submit_policy_context: Mapping[str, Any]) -> Any | None:
    source = str(submit_policy_context.get("submit_policy_source") or "")
    if not source:
        return None
    try:
        return load_capital_deployment_policy(source)
    except (CapitalDeploymentPolicyError, OSError):
        return None


def _planning_lineage_context(*, order_plan_payload: Mapping[str, Any]) -> dict[str, Any]:
    strategy_authority_lineage = (
        dict(order_plan_payload["strategy_authority_lineage"])
        if isinstance(order_plan_payload.get("strategy_authority_lineage"), Mapping)
        else {}
    )
    return {
        "planning_authority_version": str(order_plan_payload.get("planning_authority") or "phase22_strategy_runtime_planning"),
        "planning_authority_source": str(order_plan_payload.get("order_plan_id") or ""),
        "planning_authority_hash": str(order_plan_payload.get("strategy_artifact_hash") or ""),
        "runtime_plan_id": str(order_plan_payload.get("order_plan_id") or ""),
        "strategy_artifact_path": str(order_plan_payload.get("strategy_artifact_path") or ""),
        "strategy_authority_lineage": strategy_authority_lineage,
        "strategy_authority_lineage_hash": str(order_plan_payload.get("strategy_authority_lineage_hash") or strategy_authority_lineage.get("lineage_hash") or ""),
    }


def _pending_item_with_safety_context(*, item: PendingOrderItem, safety_context: Mapping[str, Any]) -> PendingOrderItem:
    if not safety_context:
        return item
    return replace(
        item,
        safety_decision_id=str(safety_context.get("safety_decision_id") or ""),
        safety_policy_version=str(safety_context.get("safety_policy_version") or ""),
        safety_source=str(safety_context.get("safety_source") or ""),
        safety_decision=str(safety_context.get("safety_decision") or ""),
        safety_reason=str(safety_context.get("safety_reason") or ""),
        safety_authority=str(safety_context.get("safety_authority") or ""),
        safety_business_date=str(safety_context.get("safety_business_date") or ""),
        temporal_authority_business_date=str(safety_context.get("temporal_authority_business_date") or ""),
        runtime_test_run_id=str(safety_context.get("runtime_test_run_id") or ""),
        runtime_test_profile_id=str(safety_context.get("runtime_test_profile_id") or ""),
        runtime_test_evidence_root=str(safety_context.get("runtime_test_evidence_root") or ""),
    )


def _pending_item_with_accepted_generation_binding(
    *,
    item: PendingOrderItem,
    accepted_generation_binding: Mapping[str, Any],
) -> PendingOrderItem:
    return replace(
        item,
        accepted_generation_id=str(accepted_generation_binding.get("accepted_generation_id") or ""),
        accepted_generation_business_date=str(accepted_generation_binding.get("accepted_generation_business_date") or ""),
        accepted_generation_binding_status=str(accepted_generation_binding.get("generation_binding_status") or ""),
        accepted_generation_binding=dict(accepted_generation_binding),
    )


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


def _safety_lineage(*, safety_context: Mapping[str, Any]) -> dict[str, Any]:
    if not safety_context:
        return {"status": "UNBOUND", "reason": "explicit_safety_authority_payload_not_provided"}
    return {
        "status": "BOUND",
        "safety_authority": str(safety_context.get("safety_authority") or ""),
        "safety_decision": str(safety_context.get("safety_decision") or ""),
        "safety_decision_id": str(safety_context.get("safety_decision_id") or ""),
        "safety_policy_version": str(safety_context.get("safety_policy_version") or ""),
        "safety_source": str(safety_context.get("safety_source") or ""),
        "safety_business_date": str(safety_context.get("safety_business_date") or ""),
        "temporal_authority_business_date": str(safety_context.get("temporal_authority_business_date") or ""),
        "runtime_test_run_id": str(safety_context.get("runtime_test_run_id") or ""),
        "runtime_test_profile_id": str(safety_context.get("runtime_test_profile_id") or ""),
        "runtime_test_evidence_root": str(safety_context.get("runtime_test_evidence_root") or ""),
    }


def _submit_policy_lineage(*, submit_policy_context: Mapping[str, Any]) -> dict[str, Any]:
    if not submit_policy_context:
        return {"status": "UNBOUND", "reason": "explicit_submit_policy_authority_payload_not_provided"}
    return {
        "status": "BOUND",
        "submit_policy_version": str(submit_policy_context.get("submit_policy_version") or ""),
        "submit_policy_source": str(submit_policy_context.get("submit_policy_source") or ""),
        "submit_policy_hash": str(submit_policy_context.get("submit_policy_hash") or ""),
        "submit_policy_authority": str(submit_policy_context.get("submit_policy_authority") or ""),
    }


def _planned_quantity(plan: Mapping[str, Any]) -> int | None:
    value = plan.get("planned_quantity")
    if isinstance(value, bool) or value in {None, ""}:
        return None
    try:
        number = float(value)
    except Exception:
        return None
    if not math.isfinite(number) or not number.is_integer():
        return None
    return int(number)


def _strategy_notional(*, plan: Mapping[str, Any], sizing: Mapping[str, Any], side: str) -> float:
    if side == "BUY":
        return max(float(sizing.get("incremental_buy_notional") or 0.0), float(sizing.get("target_notional") or 0.0))
    if str(plan.get("planning_intent") or "") == "SELL_EXIT":
        return max(float(sizing.get("current_notional") or 0.0), abs(float(sizing.get("incremental_target_notional") or 0.0)))
    return abs(float(sizing.get("incremental_target_notional") or 0.0))


def _round_lot_quantity(notional: float, price: float) -> int:
    if notional <= 0 or price <= 0:
        return 0
    return int(math.floor(notional / price / ROUND_LOT) * ROUND_LOT)


def _write_review_pending(
    *,
    runtime_root: Path,
    mode: str,
    business_date: str,
    target_session_date: str,
    strategy_dir: Path,
    runtime_planning_path: Path,
    position_sizing_path: Path,
    order_plan_path: Path,
    approval_path: Path,
    pending_path: Path,
    reason: str,
    reason_codes: tuple[str, ...],
    lineage: dict[str, Any],
    broker_write_allowed: bool,
    status: str = "REVIEW_REQUIRED",
) -> StrategyPlanningAuthorityResult:
    order_plan_payload = {
        "schema_version": "phase23_i_strategy_authority_order_plan.v1",
        "order_plan_id": f"strategy-review-{business_date}",
        "environment": mode,
        "business_date": business_date,
        "target_session_date": target_session_date,
        "status": status,
        "reason": reason,
        "items": [],
        "planning_authority": "phase22_strategy_runtime_planning",
        "planning_consumer_eligibility": status,
        "production_decision_allowed": False,
        "broker_write_allowed": broker_write_allowed,
        "broker_write_performed": False,
        "legacy_planning_authority_used": False,
        "legacy_formal_planning_authority_active": False,
        "legacy_comparison_artifact_present": False,
        "runtime_switch_performed": False,
        "silent_fallback_used": False,
    }
    _write_json(order_plan_path, order_plan_payload)
    _write_json(approval_path, {"status": status, "reason": reason, "business_date": business_date})
    pending = promote_order_plan_to_pending(
        order_plan_id=order_plan_payload["order_plan_id"],
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash=_file_hash(order_plan_path),
        environment=mode,
        plan_created_date=business_date,
        intended_submit_date=target_session_date,
        target_session_date=target_session_date,
        items=(),
    )
    pending = replace(pending, state=PendingPlanState.BLOCKED if status == "BLOCKED" else PendingPlanState.REVIEW_REQUIRED)
    pending_commit_status = (
        "NOT_COMMITTED_BLOCKED_EMPTY_UNSCOPED"
        if status == "BLOCKED"
        else "NOT_COMMITTED_REVIEW_REQUIRED_EMPTY_UNSCOPED"
    )
    return StrategyPlanningAuthorityResult(
        status=status,
        reason=reason,
        business_date=business_date,
        mode=mode,
        strategy_dir=str(strategy_dir),
        runtime_planning_artifact_path=str(runtime_planning_path),
        position_sizing_artifact_path=str(position_sizing_path),
        order_plan_artifact_path=str(order_plan_path),
        pending_path=str(pending_path),
        approval_artifact_path=str(approval_path),
        pending_plan_id=pending.pending_plan_id,
        plan_count=0,
        pending_item_count=0,
        selected_symbols=(),
        strategy_artifact_eligibility="NOT_ELIGIBLE",
        planning_consumer_eligibility=status,
        production_decision_allowed=False,
        broker_write_allowed=broker_write_allowed,
        broker_write_performed=False,
        legacy_planning_authority_used=False,
        legacy_formal_planning_authority_active=False,
        legacy_comparison_artifact_present=False,
        runtime_switch_performed=False,
        no_action=False,
        reason_codes=reason_codes,
        lineage=lineage,
        pending_commit_status=pending_commit_status,
        pending_authority_eligibility="AUTHORITY_INELIGIBLE",
        pending_retry_eligibility="RETRY_INPUT_INELIGIBLE",
        atomic_commit_decision="SKIP_CURRENT_PENDING_COMMIT",
    )


def _write_no_order_approval_artifact(
    *,
    approval_path: Path,
    pending_plan_id: str,
    order_plan_payload: Mapping[str, Any],
    order_plan_path: Path,
    runtime_planning_payload: Mapping[str, Any],
    runtime_planning_path: Path,
    position_sizing_path: Path,
    business_date: str,
    target_session_date: str,
) -> None:
    plans = [plan for plan in runtime_planning_payload.get("plans", []) or [] if isinstance(plan, Mapping)]
    approval_payload = {
        "schema_version": "phase23_ab_no_order_authorized_approval.v1",
        "status": "NO_ORDER_AUTHORIZED",
        "reason": "strategy_planning_no_order_authorized",
        "business_date": business_date,
        "target_session_date": target_session_date,
        "pending_plan_id": pending_plan_id,
        "order_plan_id": str(order_plan_payload.get("order_plan_id") or ""),
        "order_plan_path": str(order_plan_path),
        "order_plan_hash": _file_hash(order_plan_path),
        "runtime_planning_path": str(runtime_planning_path),
        "runtime_planning_hash": _file_hash(runtime_planning_path),
        "position_sizing_path": str(position_sizing_path),
        "position_sizing_hash": _file_hash(position_sizing_path),
        "planning_consumer_eligibility": str(order_plan_payload.get("planning_consumer_eligibility") or ""),
        "runtime_planning_status": str(runtime_planning_payload.get("producer_result_status") or ""),
        "pending_item_count": 0,
        "quantity_unresolved_count": sum(
            1 for plan in plans if str(plan.get("quantity_status") or "").startswith("REVIEW_REQUIRED")
        ),
        "review_required_quantity_count": sum(
            1 for plan in plans if bool(plan.get("quantity_required")) and not plan.get("planned_quantity")
        ),
        "broker_write_allowed": bool(order_plan_payload.get("broker_write_allowed")),
        "broker_write_performed": bool(order_plan_payload.get("broker_write_performed")),
        "production_decision_allowed": bool(order_plan_payload.get("production_decision_allowed")),
        "legacy_planning_authority_used": bool(order_plan_payload.get("legacy_planning_authority_used")),
        "runtime_switch_performed": bool(order_plan_payload.get("runtime_switch_performed")),
        "silent_fallback_used": bool(order_plan_payload.get("silent_fallback_used")),
        "latest_fallback_used": bool(order_plan_payload.get("latest_fallback_used")),
        "future_information_used": bool(order_plan_payload.get("future_information_used")),
    }
    _write_json(approval_path, approval_payload)


def _strategy_artifact_eligibility(payload: Mapping[str, Any]) -> str:
    status = str(payload.get("producer_result_status") or "")
    if status == "PASS":
        return "ELIGIBLE_FOR_PLANNING_AUTHORITY"
    if status == "REVIEW_REQUIRED":
        return "ELIGIBLE_WITH_SCOPED_REVIEW"
    return "NOT_ELIGIBLE"


def _broker_write_allowed(mode: str, context: Mapping[str, Any] | None) -> bool:
    if mode == "historical":
        return False
    return bool((context or {}).get("broker_write"))


def _base_lineage(*, strategy_path: Path, business_date: str) -> dict[str, Any]:
    return {
        "schema_version": "phase23_i_strategy_consumer_lineage.v1",
        "business_date": business_date,
        "strategy_artifact": str(strategy_path),
        "consumer": "runtime_v2.planning.strategy_authority.activate_strategy_planning_authority",
        "planning_input": str(strategy_path / "runtime_planning.json"),
        "planning_output": "",
        "pending_plan": "",
        "submit_input": "",
    }


def _order_plan_id(*, mode: str, business_date: str, strategy_hash: str) -> str:
    return f"strategy-plan-{mode}-{business_date}-{strategy_hash[:16]}"


def _pending_item_payload(item: PendingOrderItem) -> dict[str, Any]:
    return asdict(item)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _positive_float(value: Any, *, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(result) or result <= 0:
        return default
    return result


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()
