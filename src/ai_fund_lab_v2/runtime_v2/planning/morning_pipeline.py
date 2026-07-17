"""Morning AI/Planning/Pending pipeline for Runtime v2."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import date, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalDecision, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.approval.policy import (
    build_approval_artifact,
    build_approval_request,
)
from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetPosition, CurrentAssetState
from ai_fund_lab_v2.runtime_v2.buy_ai.opportunity_eligibility import evaluate_opportunity_buy_eligibility
from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import (
    get_broker_capability,
    is_symbol_allowed_by_capability,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.feature_date_contract import (
    FeatureDateContract,
    load_feature_date_contract,
    resolve_feature_date_contract,
)
from ai_fund_lab_v2.runtime_v2.market_status.buy_eligibility import evaluate_buy_eligibility
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.pending.models import PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    CapitalDeploymentPolicy,
    CapitalDeploymentPolicyError,
    capital_deployment_policy_hash_from_context,
    load_capital_deployment_policy,
)
from ai_fund_lab_v2.runtime_v2.planning.models import (
    AIPlanningSignal,
    CapitalAllocationSignal,
    PlanningInput,
    RuntimeSafetyContext,
)
from ai_fund_lab_v2.runtime_v2.planning.planner import build_order_plan
from ai_fund_lab_v2.runtime_v2.safety_decision import (
    RuntimeSafetyDecision,
    load_runtime_safety_decision,
    safety_allows_action,
    safety_manifest_fields,
)


@dataclass(frozen=True)
class PriceEvidence:
    symbol: str
    price: float
    price_source: str
    price_as_of: str
    price_confidence: str
    artifact_path: str


@dataclass(frozen=True)
class MorningPipelineResult:
    status: str
    reason: str
    feature_date: str
    candidate_count: int
    selected_count: int
    demo_filtered_9000_count: int
    pending_path: str
    pending_plan_id: str
    approval_artifact_path: str
    order_plan_artifact_path: str
    target_session_date: str
    evaluation_capital: float | None
    selected_symbols: tuple[str, ...]
    requested_feature_date: str = ""
    selected_feature_date: str = ""
    latest_available_market_date: str = ""
    carryover_used: bool = False
    carryover_reason: str = ""
    freshness_lag_business_days: int | None = None
    freshness_limit_business_days: int = 1
    feature_date_contract_status: str = ""
    feature_date_contract_reason: str = ""
    feature_date_contract_path: str = ""
    consumer_ready: bool = False
    schema_version: str = ""
    candidate_schema_status: str = ""
    candidate_missing_columns: tuple[str, ...] = ()
    opportunity_schema_status: str = ""
    pm_schema_status: str = ""
    consumer_readiness_artifact_path: str = ""
    available_cash: float | None = None
    planning_budget: float | None = None
    current_exposure: float = 0.0
    current_position_symbols: tuple[str, ...] = ()
    existing_position_excluded_count: int = 0
    selected_price_source: str = ""
    price_source_status: str = ""
    price_source_path: str = ""
    price_missing_count: int = 0
    budget_excluded_count: int = 0
    buy_eligibility_status: str = ""
    buy_eligibility_authority_source: str = ""
    buy_eligibility_authority_path: str = ""
    buy_eligibility_filtered_count: int = 0
    buy_eligibility_review_count: int = 0
    buy_eligibility_evidence: tuple[dict[str, Any], ...] = ()
    opportunity_buy_eligibility_status: str = ""
    opportunity_buy_eligibility_filtered_count: int = 0
    opportunity_buy_eligibility_review_count: int = 0
    opportunity_buy_eligibility_evidence: tuple[dict[str, Any], ...] = ()
    sample_order_sizing: tuple[dict[str, Any], ...] = ()
    capital_deployment_policy_used_by_morning: bool = False
    morning_policy_source: str = ""
    morning_policy_version: str = ""
    morning_policy_sizing_method: str = ""
    morning_policy_target_investment_ratio: float | None = None
    morning_policy_cash_buffer: float | None = None
    morning_policy_max_exposure: float | None = None
    morning_policy_max_position_weight: float | None = None
    morning_policy_max_positions: int | None = None
    morning_policy_max_buy_order_amount: float | None = None
    morning_policy_min_order_amount: float | None = None
    morning_order_count_source: str = ""
    morning_per_order_budget_source: str = ""
    morning_hidden_cap_removed: bool = False
    safety_decision_id: str = ""
    safety_policy_version: str = ""
    safety_source: str = ""
    safety_decision: str = ""
    safety_reason: str = ""
    safety_status: str = ""
    safety_block_buy: bool = False
    safety_block_sell: bool = False
    safety_block_submit: bool = False
    safety_halt_runtime: bool = False

    def to_stage_details(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["selected_symbols"] = list(self.selected_symbols)
        payload["candidate_missing_columns"] = list(self.candidate_missing_columns)
        payload["sample_order_sizing"] = list(self.sample_order_sizing)
        payload["buy_eligibility_evidence"] = list(self.buy_eligibility_evidence)
        payload["opportunity_buy_eligibility_evidence"] = list(self.opportunity_buy_eligibility_evidence)
        return payload


@dataclass(frozen=True)
class MorningCapabilityDecision:
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


HISTORICAL_ALLOWED_MORNING_PROCESSING: tuple[str, ...] = (
    "data_readiness",
    "candidate_ai",
    "opportunity_ai",
    "capital_allocation",
    "buy_planning",
    "historical_approval_policy",
    "pending_generation",
    "historical_execution_handoff",
    "run_scoped_evidence",
)

HISTORICAL_PROHIBITED_MORNING_EXTERNAL_EFFECTS: tuple[str, ...] = (
    "tachibana_demo_api_write",
    "tachibana_production_api_write",
    "broker_order_api_call",
    "demo_submit",
    "production_submit",
    "external_notification_delivery",
    "line_send",
    "discord_send",
    "broker_snapshot_external_update",
    "jquants_api_fetch",
    "production_access",
)


def evaluate_morning_capability(
    *,
    mode: str,
    context: dict[str, Any] | None = None,
) -> MorningCapabilityDecision:
    """Resolve Morning capability from environment composition, not mode name alone."""

    if mode in {"demo", "production"}:
        return MorningCapabilityDecision(
            status="PASS",
            reason=f"{mode}_morning_capability_ready",
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
            allowed_processing=("common_runtime_morning_core",),
            prohibited_external_effects=(),
        )
    if mode != "historical":
        return _morning_capability_block(
            mode=mode,
            context=context,
            reason="unsupported_runtime_mode_for_morning",
            failed_checks=("runtime_mode_supported",),
        )
    if not context:
        return _morning_capability_block(
            mode=mode,
            context={},
            reason="historical_morning_capability_context_missing",
            failed_checks=("environment_capability_context_present",),
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
        return _morning_capability_block(
            mode=mode,
            context=context,
            reason="historical_morning_capability_fail_closed:" + ",".join(failed),
            failed_checks=failed,
        )
    return MorningCapabilityDecision(
        status="PASS",
        reason="historical_morning_capability_ready",
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
        allowed_processing=HISTORICAL_ALLOWED_MORNING_PROCESSING,
        prohibited_external_effects=HISTORICAL_PROHIBITED_MORNING_EXTERNAL_EFFECTS,
    )


def _morning_capability_block(
    *,
    mode: str,
    context: dict[str, Any] | None,
    reason: str,
    failed_checks: tuple[str, ...],
) -> MorningCapabilityDecision:
    context = context or {}
    return MorningCapabilityDecision(
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
        prohibited_external_effects=HISTORICAL_PROHIBITED_MORNING_EXTERNAL_EFFECTS if mode == "historical" else (),
        failed_checks=failed_checks,
    )


def run_morning_ai_planning_pending_pipeline(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    feature_root: Path | str = ".runtime/operations/feature_artifacts",
    feature_date: str | None = None,
    max_orders: int | None = None,
    capital_deployment_policy: CapitalDeploymentPolicy | None = None,
    capital_deployment_policy_path: Path | str | None = None,
    safety_decision: RuntimeSafetyDecision | None = None,
    ai_signals: tuple[AIPlanningSignal, ...] | None = None,
    buy_ai_context: dict[str, Any] | None = None,
    environment_capability_context: dict[str, Any] | None = None,
) -> MorningPipelineResult:
    """Connect feature input to Planning, Approval, and Current Pending.

    The pipeline performs no Submit and no Broker write. It writes only the
    canonical Pending Current and derived morning artifacts.
    """

    capability_decision = evaluate_morning_capability(
        mode=mode,
        context=environment_capability_context,
    )
    if capability_decision.status != "PASS":
        raise ValueError(capability_decision.reason)

    runtime_root_path = Path(runtime_root)
    _reject_mode_rooted_runtime_root(runtime_root_path)
    target_session_date = business_date
    requested_feature_date = feature_date or _previous_calendar_day(business_date)
    feature_contract = _resolve_morning_feature_date_contract(
        feature_root=Path(feature_root),
        requested_feature_date=requested_feature_date,
        explicit_feature_date=feature_date is not None,
    )
    resolved_feature_date = feature_contract.selected_feature_date or requested_feature_date
    capability = get_broker_capability(mode)
    asset_state = _load_asset_state(runtime_root_path / "persistent_ledger" / "state.json")
    runtime_safety_decision = safety_decision or load_runtime_safety_decision(
        runtime_root=runtime_root_path,
        business_date=business_date,
        mode=mode,
    )
    safety_allowed, safety_status, safety_reason = safety_allows_action(runtime_safety_decision, action="planning", side="BUY")
    if not safety_allowed:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            environment=mode,
            environment_capability_context=environment_capability_context,
            business_date=business_date,
            feature_date=resolved_feature_date,
            feature_contract=feature_contract,
            target_session_date=target_session_date,
            reason=safety_reason,
            status=safety_status,
            evaluation_capital=None,
            price_source_status="NOT_EVALUATED",
            price_source_path=str(_price_source_path(Path(feature_root))),
            policy_context=_empty_morning_policy_context(operator_max_orders=max_orders),
            safety_decision=runtime_safety_decision,
        )
    policy = capital_deployment_policy
    if policy is None and capital_deployment_policy_path is not None:
        try:
            policy = load_capital_deployment_policy(capital_deployment_policy_path)
        except CapitalDeploymentPolicyError:
            policy = None
    if policy is None:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            environment=mode,
            environment_capability_context=environment_capability_context,
            business_date=business_date,
            feature_date=resolved_feature_date,
            feature_contract=feature_contract,
            target_session_date=target_session_date,
            reason="capital_deployment_policy_missing",
            status="REVIEW_REQUIRED",
            evaluation_capital=None,
            price_source_status="NOT_EVALUATED",
            price_source_path=str(_price_source_path(Path(feature_root))),
            policy_context=_empty_morning_policy_context(operator_max_orders=max_orders),
            safety_decision=runtime_safety_decision,
        )
    evaluation_capital = policy.evaluation_capital
    available_cash = _available_cash(asset_state, capability_default=capability.default_evaluation_capital)
    current_exposure = _current_exposure(asset_state)
    current_position_symbols = _current_position_symbols(asset_state)
    effective_order_limit = _effective_order_limit(
        policy=policy,
        current_position_count=len(current_position_symbols),
        operator_max_orders=max_orders,
    )
    planning_budget = _policy_planning_budget(
        policy=policy,
        available_cash=available_cash,
        current_exposure=current_exposure,
    )
    per_order_budget = _policy_per_order_budget(
        policy=policy,
        planning_budget=planning_budget,
        effective_order_limit=effective_order_limit,
    )
    policy_context = _morning_policy_context(
        policy,
        operator_max_orders=max_orders,
        effective_order_limit=effective_order_limit,
        planning_budget=planning_budget,
        per_order_budget=per_order_budget,
        current_exposure=current_exposure,
        available_cash=available_cash,
    )
    if evaluation_capital is None:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            environment=mode,
            environment_capability_context=environment_capability_context,
            business_date=business_date,
            feature_date=resolved_feature_date,
            feature_contract=feature_contract,
            target_session_date=target_session_date,
            reason="evaluation_capital_missing",
            evaluation_capital=evaluation_capital,
            available_cash=available_cash,
            planning_budget=planning_budget,
            current_exposure=current_exposure,
            current_position_symbols=current_position_symbols,
            policy_context=policy_context,
            safety_decision=runtime_safety_decision,
        )
    if planning_budget <= 0 or effective_order_limit <= 0 or per_order_budget <= 0:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            environment=mode,
            environment_capability_context=environment_capability_context,
            business_date=business_date,
            feature_date=resolved_feature_date,
            feature_contract=feature_contract,
            target_session_date=target_session_date,
            reason=_budget_no_signal_reason(
                planning_budget=planning_budget,
                effective_order_limit=effective_order_limit,
                per_order_budget=per_order_budget,
            ),
            evaluation_capital=evaluation_capital,
            available_cash=available_cash,
            planning_budget=planning_budget,
            current_exposure=current_exposure,
            current_position_symbols=current_position_symbols,
            policy_context=policy_context,
            safety_decision=runtime_safety_decision,
        )
    if feature_contract.status != "PASS":
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            environment=mode,
            environment_capability_context=environment_capability_context,
            business_date=business_date,
            feature_date=resolved_feature_date,
            feature_contract=feature_contract,
            target_session_date=target_session_date,
            reason=feature_contract.reason,
            status=feature_contract.status,
            evaluation_capital=evaluation_capital,
            available_cash=available_cash,
            planning_budget=planning_budget,
            current_exposure=current_exposure,
            current_position_symbols=current_position_symbols,
            price_source_status="NOT_EVALUATED",
            price_source_path=str(_price_source_path(Path(feature_root))),
            policy_context=policy_context,
            safety_decision=runtime_safety_decision,
        )

    if ai_signals is None:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            environment=mode,
            environment_capability_context=environment_capability_context,
            business_date=business_date,
            feature_date=resolved_feature_date,
            feature_contract=feature_contract,
            target_session_date=target_session_date,
            reason="buy_ai_opportunity_artifact_missing",
            status="REVIEW_REQUIRED",
            evaluation_capital=evaluation_capital,
            available_cash=available_cash,
            planning_budget=planning_budget,
            current_exposure=current_exposure,
            current_position_symbols=current_position_symbols,
            policy_context=policy_context,
            safety_decision=runtime_safety_decision,
        )

    candidate_rows = tuple(ai_signals)
    if not candidate_rows:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            environment=mode,
            environment_capability_context=environment_capability_context,
            business_date=business_date,
            feature_date=resolved_feature_date,
            feature_contract=feature_contract,
            target_session_date=target_session_date,
            reason="NO_SIGNAL:opportunity_ai_rankings_empty",
            evaluation_capital=evaluation_capital,
            available_cash=available_cash,
            planning_budget=planning_budget,
            current_exposure=current_exposure,
            current_position_symbols=current_position_symbols,
            policy_context=policy_context,
            safety_decision=runtime_safety_decision,
        )

    price_source = _load_price_source(Path(feature_root), resolved_feature_date)
    if price_source is None:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            environment=mode,
            environment_capability_context=environment_capability_context,
            business_date=business_date,
            feature_date=resolved_feature_date,
            feature_contract=feature_contract,
            target_session_date=target_session_date,
            reason="reliable_price_source_missing",
            status="REVIEW_REQUIRED",
            evaluation_capital=evaluation_capital,
            available_cash=available_cash,
            planning_budget=planning_budget,
            current_exposure=current_exposure,
            current_position_symbols=current_position_symbols,
            candidate_count=len(candidate_rows),
            price_source_status="MISSING",
            price_source_path=str(_price_source_path(Path(feature_root))),
            policy_context=policy_context,
            safety_decision=runtime_safety_decision,
        )

    selected_rows: list[dict[str, Any]] = []
    demo_filtered_9000_count = 0
    price_missing_count = 0
    budget_excluded_count = 0
    existing_position_excluded_count = 0
    buy_eligibility_filtered_count = 0
    buy_eligibility_review_count = 0
    buy_eligibility_evidence: list[dict[str, Any]] = []
    buy_eligibility_authority_path = _buy_eligibility_snapshot_path(
        runtime_root=runtime_root_path,
        business_date=business_date,
        mode=mode,
    )
    opportunity_context = _opportunity_context(buy_ai_context)
    opportunity_buy_eligibility_filtered_count = 0
    opportunity_buy_eligibility_review_count = 0
    opportunity_buy_eligibility_evidence: list[dict[str, Any]] = []
    for signal in candidate_rows:
        symbol = signal.symbol
        if not is_symbol_allowed_by_capability(symbol, capability):
            demo_filtered_9000_count += 1
            continue
        broker_symbol = _broker_symbol(symbol, {})
        if broker_symbol in current_position_symbols:
            existing_position_excluded_count += 1
            continue
        price = price_source.get(symbol)
        if price is None:
            price_missing_count += 1
            continue
        opportunity_eligibility = None
        if opportunity_context["opportunity_artifact_path"]:
            opportunity_eligibility = evaluate_opportunity_buy_eligibility(
                symbol=symbol,
                business_date=business_date,
                feature_date=resolved_feature_date,
                opportunity_artifact_path=opportunity_context["opportunity_artifact_path"],
                excluded_at_stage="morning_candidate_selection",
            )
            opportunity_buy_eligibility_evidence.append(opportunity_eligibility.to_payload())
            if not opportunity_eligibility.eligible:
                opportunity_buy_eligibility_filtered_count += 1
                continue
        buy_eligibility = None
        if buy_eligibility_authority_path is not None:
            buy_eligibility = evaluate_buy_eligibility(
                symbol=symbol,
                business_date=business_date,
                mode=mode,
                listed_snapshot_path=buy_eligibility_authority_path,
                authority_source="morning_candidate_listed_issues_snapshot",
            )
            buy_eligibility_evidence.append(buy_eligibility.to_payload())
            if buy_eligibility.status == "REVIEW_REQUIRED":
                buy_eligibility_review_count += 1
                continue
            if not buy_eligibility.eligible:
                buy_eligibility_filtered_count += 1
                continue
        quantity = _round_lot_quantity(per_order_budget, price.price)
        if quantity <= 0:
            budget_excluded_count += 1
            continue
        selected_rows.append(
            {
                "code": symbol,
                "__price_evidence": price,
                "__planned_quantity": quantity,
                "__ai_signal": signal,
                "__buy_eligibility": buy_eligibility.to_payload() if buy_eligibility is not None else {},
                "__opportunity_buy_eligibility": (
                    opportunity_eligibility.to_payload() if opportunity_eligibility is not None else {}
                ),
            }
        )
        if len(selected_rows) >= effective_order_limit:
            break
    if not selected_rows:
        reason = (
            "NO_SIGNAL:demo_capability_filtered_all_9000_series"
            if demo_filtered_9000_count >= len(candidate_rows)
            else "NO_SIGNAL:no_affordable_candidates_with_reliable_price"
        )
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            environment=mode,
            environment_capability_context=environment_capability_context,
            business_date=business_date,
            feature_date=resolved_feature_date,
            feature_contract=feature_contract,
            target_session_date=target_session_date,
            reason=reason,
            evaluation_capital=evaluation_capital,
            available_cash=available_cash,
            planning_budget=planning_budget,
            current_exposure=current_exposure,
            current_position_symbols=current_position_symbols,
            candidate_count=len(candidate_rows),
            demo_filtered_9000_count=demo_filtered_9000_count,
            price_source_status="PASS",
            price_source_path=str(_price_source_path(Path(feature_root))),
            price_missing_count=price_missing_count,
            budget_excluded_count=budget_excluded_count,
            existing_position_excluded_count=existing_position_excluded_count,
            buy_eligibility_status="REVIEW_REQUIRED" if buy_eligibility_review_count else "PASS",
            buy_eligibility_authority_source=(
                "morning_candidate_listed_issues_snapshot" if buy_eligibility_authority_path is not None else ""
            ),
            buy_eligibility_authority_path=str(buy_eligibility_authority_path or ""),
            buy_eligibility_filtered_count=buy_eligibility_filtered_count,
            buy_eligibility_review_count=buy_eligibility_review_count,
            buy_eligibility_evidence=tuple(buy_eligibility_evidence),
            opportunity_buy_eligibility_status=(
                "REVIEW_REQUIRED" if opportunity_buy_eligibility_review_count else "PASS"
            ),
            opportunity_buy_eligibility_filtered_count=opportunity_buy_eligibility_filtered_count,
            opportunity_buy_eligibility_review_count=opportunity_buy_eligibility_review_count,
            opportunity_buy_eligibility_evidence=tuple(opportunity_buy_eligibility_evidence),
            policy_context=policy_context,
            safety_decision=runtime_safety_decision,
        )

    planning_run_id = _planning_run_id(business_date)
    selected_ai_signals = tuple(
        _runtime_ai_signal(row["__ai_signal"], rank, planning_run_id=planning_run_id)
        for rank, row in enumerate(selected_rows, start=1)
    )
    allocations = tuple(
        _allocation(row=row, signal=signal, per_order_budget=per_order_budget, policy_context=policy_context)
        for row, signal in zip(selected_rows, selected_ai_signals)
    )
    planning_result = build_order_plan(
        PlanningInput(
            mode=mode,
            environment=mode,
            business_date=business_date,
            target_session_date=target_session_date,
            asset_state=asset_state,
            ai_signals=selected_ai_signals,
            capital_allocations=allocations,
            runtime_safety=_runtime_safety_context(runtime_safety_decision),
        )
    )
    order_plan_path = _morning_artifact_dir(runtime_root_path, business_date) / "order_plan.json"
    order_plan_path.parent.mkdir(parents=True, exist_ok=True)
    order_plan_payload = _jsonable(planning_result.order_plan)
    order_plan_payload["policy_context"] = policy_context
    order_plan_payload["feature_date_contract"] = _feature_contract_payload(feature_contract)
    order_plan_payload["market_data_freshness"] = _market_data_freshness_payload(feature_contract)
    order_plan_payload["buy_ai_context"] = buy_ai_context or {}
    order_plan_payload["buy_eligibility_contract"] = {
        "status": "REVIEW_REQUIRED" if buy_eligibility_review_count else "PASS",
        "authority_source": "morning_candidate_listed_issues_snapshot" if buy_eligibility_authority_path is not None else "",
        "authority_path": str(buy_eligibility_authority_path or ""),
        "filtered_count": buy_eligibility_filtered_count,
        "review_count": buy_eligibility_review_count,
        "evidence": buy_eligibility_evidence,
    }
    order_plan_payload["opportunity_buy_eligibility_contract"] = {
        "status": "REVIEW_REQUIRED" if opportunity_buy_eligibility_review_count else "PASS",
        "policy_version": "runtime_v2_opportunity_buy_eligibility_v1",
        "artifact_path": opportunity_context["opportunity_artifact_path"],
        "artifact_hash": opportunity_context["opportunity_artifact_hash"],
        "business_date": business_date,
        "feature_date": resolved_feature_date,
        "filtered_count": opportunity_buy_eligibility_filtered_count,
        "review_count": opportunity_buy_eligibility_review_count,
        "evidence": opportunity_buy_eligibility_evidence,
    }
    order_plan_path.write_text(_json_dumps(order_plan_payload), encoding="utf-8")
    order_plan_hash = _hash(order_plan_path.read_text(encoding="utf-8"))

    listed_info_by_symbol = {_symbol(row): _listed_info(row) for row in selected_rows}
    pending_items = tuple(
        replace(_pending_item(item), listed_info=listed_info_by_symbol.get(item.symbol))
        for item in planning_result.order_plan.items
        if not item.blocked and not item.review_required and item.quantity > 0
    )
    pending = _pending_from_items(
        order_plan_id=planning_result.order_plan.order_plan_id,
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash=order_plan_hash,
        environment=mode,
        business_date=business_date,
        target_session_date=target_session_date,
        items=pending_items,
    )
    pending = replace(pending, feature_date_contract=_feature_contract_payload(feature_contract))
    pending = _attach_historical_safety_authority(
        pending=pending,
        business_date=business_date,
        safety_decision=runtime_safety_decision,
        environment_capability_context=environment_capability_context,
    )
    approved_item_ids = tuple(item.pending_item_id for item in pending.items)
    approval_path = _morning_artifact_dir(runtime_root_path, business_date) / "approval_artifact.json"
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
                reason="phase14e15 morning auto approval for demo operation",
                operator="runtime_v2_morning_job",
                decided_at=f"{business_date}T08:45:00+09:00",
            ),
        )
        approval_path.write_text(_json_dumps(_jsonable(approval)), encoding="utf-8")
        pending = link_approval_to_pending(pending_plan=pending, approval_artifact=approval)
    else:
        approval_path.write_text(
            _json_dumps(
                {
                    "status": "NO_SIGNAL",
                    "reason": "no pending items after planning",
                    "business_date": business_date,
                }
            ),
            encoding="utf-8",
        )

    pending_path = runtime_root_path / "pending_order_plan" / "pending_order_plan.json"
    write_pending_order_plan(pending_path, pending)
    return MorningPipelineResult(
        status="PASS" if pending_items else "NO_SIGNAL",
        reason="" if pending_items else "no pending items after planning",
        feature_date=resolved_feature_date,
        candidate_count=len(candidate_rows),
        selected_count=len(pending_items),
        demo_filtered_9000_count=demo_filtered_9000_count,
        pending_path=str(pending_path),
        pending_plan_id=pending.pending_plan_id,
        approval_artifact_path=str(approval_path),
        order_plan_artifact_path=str(order_plan_path),
        target_session_date=target_session_date,
        evaluation_capital=float(evaluation_capital),
        available_cash=float(available_cash) if available_cash is not None else None,
        planning_budget=float(planning_budget) if planning_budget is not None else None,
        current_exposure=float(current_exposure),
        current_position_symbols=current_position_symbols,
        selected_symbols=tuple(item.symbol for item in pending.items),
        requested_feature_date=feature_contract.requested_feature_date,
        selected_feature_date=feature_contract.selected_feature_date,
        latest_available_market_date=feature_contract.latest_available_market_date,
        carryover_used=feature_contract.carryover_used,
        carryover_reason=feature_contract.carryover_reason,
        freshness_lag_business_days=feature_contract.freshness_lag_business_days,
        freshness_limit_business_days=feature_contract.freshness_limit_business_days,
        feature_date_contract_status=feature_contract.status,
        feature_date_contract_reason=feature_contract.reason,
        feature_date_contract_path=feature_contract.contract_artifact_path,
        consumer_ready=feature_contract.consumer_ready,
        schema_version=feature_contract.schema_version,
        candidate_schema_status=feature_contract.candidate_schema_status,
        candidate_missing_columns=feature_contract.candidate_missing_columns,
        opportunity_schema_status=feature_contract.opportunity_schema_status,
        pm_schema_status=feature_contract.pm_schema_status,
        consumer_readiness_artifact_path=feature_contract.consumer_readiness_artifact_path,
        existing_position_excluded_count=existing_position_excluded_count,
        selected_price_source="jquants_raw_normalized_daily_quotes_close",
        price_source_status="PASS",
        price_source_path=str(_price_source_path(Path(feature_root))),
        price_missing_count=price_missing_count,
        budget_excluded_count=budget_excluded_count,
        buy_eligibility_status="REVIEW_REQUIRED" if buy_eligibility_review_count else "PASS",
        buy_eligibility_authority_source=(
            "morning_candidate_listed_issues_snapshot" if buy_eligibility_authority_path is not None else ""
        ),
        buy_eligibility_authority_path=str(buy_eligibility_authority_path or ""),
        buy_eligibility_filtered_count=buy_eligibility_filtered_count,
        buy_eligibility_review_count=buy_eligibility_review_count,
        buy_eligibility_evidence=tuple(buy_eligibility_evidence),
        opportunity_buy_eligibility_status=(
            "REVIEW_REQUIRED" if opportunity_buy_eligibility_review_count else "PASS"
        ),
        opportunity_buy_eligibility_filtered_count=opportunity_buy_eligibility_filtered_count,
        opportunity_buy_eligibility_review_count=opportunity_buy_eligibility_review_count,
        opportunity_buy_eligibility_evidence=tuple(opportunity_buy_eligibility_evidence),
        sample_order_sizing=tuple(_sizing_summary(item) for item in pending.items),
        **_result_policy_fields(policy_context),
        **_result_safety_fields(runtime_safety_decision),
    )


def _pending_from_items(
    *,
    order_plan_id: str,
    source_order_plan_path: str,
    source_order_plan_hash: str,
    environment: str,
    business_date: str,
    target_session_date: str,
    items: tuple[PendingOrderItem, ...],
):
    from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending

    return promote_order_plan_to_pending(
        order_plan_id=order_plan_id,
        source_order_plan_path=source_order_plan_path,
        source_order_plan_hash=source_order_plan_hash,
        environment=environment,
        plan_created_date=business_date,
        intended_submit_date=target_session_date,
        target_session_date=target_session_date,
        items=items,
    )


def _write_no_signal_pending(
    *,
    runtime_root: Path,
    environment: str,
    environment_capability_context: dict[str, Any] | None,
    business_date: str,
    feature_date: str,
    feature_contract: FeatureDateContract,
    target_session_date: str,
    reason: str,
    status: str = "NO_SIGNAL",
    evaluation_capital: float | None,
    available_cash: float | None = None,
    planning_budget: float | None = None,
    current_exposure: float = 0.0,
    current_position_symbols: tuple[str, ...] = (),
    candidate_count: int = 0,
    demo_filtered_9000_count: int = 0,
    price_source_status: str = "",
    price_source_path: str = "",
    price_missing_count: int = 0,
    budget_excluded_count: int = 0,
    existing_position_excluded_count: int = 0,
    buy_eligibility_status: str = "",
    buy_eligibility_authority_source: str = "",
    buy_eligibility_authority_path: str = "",
    buy_eligibility_filtered_count: int = 0,
    buy_eligibility_review_count: int = 0,
    buy_eligibility_evidence: tuple[dict[str, Any], ...] = (),
    opportunity_buy_eligibility_status: str = "",
    opportunity_buy_eligibility_filtered_count: int = 0,
    opportunity_buy_eligibility_review_count: int = 0,
    opportunity_buy_eligibility_evidence: tuple[dict[str, Any], ...] = (),
    policy_context: dict[str, Any] | None = None,
    safety_decision: RuntimeSafetyDecision | None = None,
) -> MorningPipelineResult:
    order_plan_path = _morning_artifact_dir(runtime_root, business_date) / "order_plan.json"
    approval_path = _morning_artifact_dir(runtime_root, business_date) / "approval_artifact.json"
    order_plan_path.parent.mkdir(parents=True, exist_ok=True)
    order_plan_payload = {
        "schema_version": "1",
        "order_plan_id": f"order-plan-morning-no-signal-{business_date}",
        "environment": environment,
        "business_date": business_date,
        "target_session_date": target_session_date,
        "status": "NO_ACTION",
        "items": [],
        "reason": reason,
        "feature_date_contract": _feature_contract_payload(feature_contract),
        "market_data_freshness": _market_data_freshness_payload(feature_contract),
        "price_source_contract": {
            "required_for_buy": True,
            "selected_price_source": "jquants_raw_normalized_daily_quotes_close",
            "price_source_status": price_source_status,
            "price_source_path": price_source_path,
            "fallback_allowed": False,
        },
        "policy_context": policy_context or {},
        "safety_context": _safety_context_payload(safety_decision),
        "buy_eligibility_contract": {
            "status": buy_eligibility_status,
            "authority_source": buy_eligibility_authority_source,
            "authority_path": buy_eligibility_authority_path,
            "filtered_count": buy_eligibility_filtered_count,
            "review_count": buy_eligibility_review_count,
            "evidence": list(buy_eligibility_evidence),
        },
        "opportunity_buy_eligibility_contract": {
            "status": opportunity_buy_eligibility_status,
            "policy_version": "runtime_v2_opportunity_buy_eligibility_v1",
            "filtered_count": opportunity_buy_eligibility_filtered_count,
            "review_count": opportunity_buy_eligibility_review_count,
            "evidence": list(opportunity_buy_eligibility_evidence),
        },
    }
    order_plan_path.write_text(_json_dumps(order_plan_payload), encoding="utf-8")
    approval_path.write_text(
        _json_dumps({"status": "NO_SIGNAL", "reason": reason, "business_date": business_date}),
        encoding="utf-8",
    )
    pending = _pending_from_items(
        order_plan_id=order_plan_payload["order_plan_id"],
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash=_hash(order_plan_path.read_text(encoding="utf-8")),
        environment=environment,
        business_date=business_date,
        target_session_date=target_session_date,
        items=(),
    )
    pending = replace(pending, feature_date_contract=_feature_contract_payload(feature_contract))
    if safety_decision is not None:
        pending = replace(
            pending,
            safety_context=_safety_context_payload(safety_decision),
            safety_decision_id=safety_decision.safety_decision_id,
            safety_policy_version=safety_decision.safety_policy_version,
        )
    if policy_context:
        pending = replace(
            pending,
            policy_context=policy_context,
            policy_version=str(policy_context.get("policy_version") or ""),
            policy_source=str(policy_context.get("policy_source") or ""),
            pending_policy_hash=_policy_hash(policy_context),
        )
    pending = _attach_historical_safety_authority(
        pending=pending,
        business_date=business_date,
        safety_decision=safety_decision,
        environment_capability_context=environment_capability_context,
    )
    if status == "REVIEW_REQUIRED":
        pending = replace(pending, state=PendingPlanState.REVIEW_REQUIRED)
    elif status == "BLOCKED":
        pending = replace(pending, state=PendingPlanState.BLOCKED)
    elif not pending.items:
        pending = replace(pending, state=PendingPlanState.EMPTY)
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    write_pending_order_plan(pending_path, pending)
    if pending.state == PendingPlanState.EMPTY:
        pending_payload = json.loads(pending_path.read_text(encoding="utf-8"))
        pending_payload["status"] = "EMPTY"
        pending_payload["active_pending"] = False
        pending_payload["no_action_reason"] = reason
        pending_path.write_text(_json_dumps(pending_payload), encoding="utf-8")
    return MorningPipelineResult(
        status=status,
        reason=reason,
        feature_date=feature_date,
        candidate_count=candidate_count,
        selected_count=0,
        demo_filtered_9000_count=demo_filtered_9000_count,
        pending_path=str(pending_path),
        pending_plan_id=pending.pending_plan_id,
        approval_artifact_path=str(approval_path),
        order_plan_artifact_path=str(order_plan_path),
        target_session_date=target_session_date,
        evaluation_capital=float(evaluation_capital) if evaluation_capital is not None else None,
        available_cash=float(available_cash) if available_cash is not None else None,
        planning_budget=float(planning_budget) if planning_budget is not None else None,
        current_exposure=float(current_exposure),
        current_position_symbols=current_position_symbols,
        selected_symbols=(),
        requested_feature_date=feature_contract.requested_feature_date,
        selected_feature_date=feature_contract.selected_feature_date,
        latest_available_market_date=feature_contract.latest_available_market_date,
        carryover_used=feature_contract.carryover_used,
        carryover_reason=feature_contract.carryover_reason,
        freshness_lag_business_days=feature_contract.freshness_lag_business_days,
        freshness_limit_business_days=feature_contract.freshness_limit_business_days,
        feature_date_contract_status=feature_contract.status,
        feature_date_contract_reason=feature_contract.reason,
        feature_date_contract_path=feature_contract.contract_artifact_path,
        consumer_ready=feature_contract.consumer_ready,
        schema_version=feature_contract.schema_version,
        candidate_schema_status=feature_contract.candidate_schema_status,
        candidate_missing_columns=feature_contract.candidate_missing_columns,
        opportunity_schema_status=feature_contract.opportunity_schema_status,
        pm_schema_status=feature_contract.pm_schema_status,
        consumer_readiness_artifact_path=feature_contract.consumer_readiness_artifact_path,
        existing_position_excluded_count=existing_position_excluded_count,
        selected_price_source="jquants_raw_normalized_daily_quotes_close",
        price_source_status=price_source_status,
        price_source_path=price_source_path,
        price_missing_count=price_missing_count,
        budget_excluded_count=budget_excluded_count,
        buy_eligibility_status=buy_eligibility_status,
        buy_eligibility_authority_source=buy_eligibility_authority_source,
        buy_eligibility_authority_path=buy_eligibility_authority_path,
        buy_eligibility_filtered_count=buy_eligibility_filtered_count,
        buy_eligibility_review_count=buy_eligibility_review_count,
        buy_eligibility_evidence=buy_eligibility_evidence,
        opportunity_buy_eligibility_status=opportunity_buy_eligibility_status,
        opportunity_buy_eligibility_filtered_count=opportunity_buy_eligibility_filtered_count,
        opportunity_buy_eligibility_review_count=opportunity_buy_eligibility_review_count,
        opportunity_buy_eligibility_evidence=opportunity_buy_eligibility_evidence,
        **_result_policy_fields(policy_context),
        **_result_safety_fields(safety_decision),
    )


def _attach_historical_safety_authority(
    *,
    pending,
    business_date: str,
    safety_decision: RuntimeSafetyDecision | None,
    environment_capability_context: dict[str, Any] | None,
):
    if safety_decision is None or str(safety_decision.decision or "").upper() != "ALLOW":
        return pending
    context = environment_capability_context or {}
    if str(context.get("runtime_mode") or "") != "historical":
        return pending
    safety_context = {
        **_safety_context_payload(safety_decision),
        "safety_authority": "historical_initial_no_external_effect",
        "safety_business_date": business_date,
    }
    if context.get("runtime_test_run_id"):
        safety_context["runtime_test_run_id"] = str(context.get("runtime_test_run_id") or "")
    if context.get("runtime_test_profile_id"):
        safety_context["runtime_test_profile_id"] = str(context.get("runtime_test_profile_id") or "")
    if context.get("runtime_test_evidence_root"):
        safety_context["runtime_test_evidence_root"] = str(context.get("runtime_test_evidence_root") or "")
    return replace(
        pending,
        safety_context=safety_context,
        safety_decision_id=safety_decision.safety_decision_id,
        safety_policy_version=safety_decision.safety_policy_version,
    )


def _load_feature_inputs(feature_dir: Path) -> dict[str, Any | None]:
    import pandas as pd

    paths = {
        "candidate": feature_dir / "candidate_features.parquet",
        "opportunity": feature_dir / "opportunity_feature_input.parquet",
        "position": feature_dir / "position_feature_input.parquet",
        "capital": feature_dir / "capital_policy_input.parquet",
    }
    loaded: dict[str, Any | None] = {}
    for name, path in paths.items():
        if not path.exists():
            loaded[name] = None
            continue
        loaded[name] = pd.read_parquet(path)
    return loaded


def _resolve_morning_feature_date_contract(
    *,
    feature_root: Path,
    requested_feature_date: str,
    explicit_feature_date: bool,
) -> FeatureDateContract:
    operations_root = feature_root.parent
    if explicit_feature_date:
        return resolve_feature_date_contract(
            operations_root=operations_root,
            requested_feature_date=requested_feature_date,
            latest_available_market_date=requested_feature_date,
        )
    existing = load_feature_date_contract(
        operations_root=operations_root,
        requested_feature_date=requested_feature_date,
    )
    if existing is not None:
        return existing
    return resolve_feature_date_contract(
        operations_root=operations_root,
        requested_feature_date=requested_feature_date,
    )


def _feature_contract_payload(contract: FeatureDateContract) -> dict[str, Any]:
    return contract.to_payload()


def _buy_eligibility_snapshot_path(
    *,
    runtime_root: Path,
    business_date: str,
    mode: str,
) -> Path | None:
    if mode != "historical":
        return None
    from ai_fund_lab_v2.runtime_v2.historical_support.listed_issues_snapshots import (
        resolve_listed_issues_snapshot,
    )

    snapshot_root = runtime_root / "operations" / "jquants" / "historical_snapshots" / "listed_issues"
    if not (snapshot_root / "index.json").is_file():
        return None
    resolution = resolve_listed_issues_snapshot(
        snapshot_root=snapshot_root,
        business_date=business_date,
        mode="historical",
    )
    if resolution.status != "PASS":
        return None
    return Path(resolution.selected_snapshot_path)


def _opportunity_context(context: dict[str, Any] | None) -> dict[str, str]:
    payload = context or {}
    artifact_path = str(payload.get("opportunity_artifact_path") or "")
    return {
        "opportunity_artifact_path": artifact_path,
        "opportunity_artifact_hash": _hash(Path(artifact_path).read_text(encoding="utf-8")) if artifact_path and Path(artifact_path).is_file() else "",
    }


def _market_data_freshness_payload(contract: FeatureDateContract) -> dict[str, Any]:
    return {
        "requested_feature_date": contract.requested_feature_date,
        "selected_feature_date": contract.selected_feature_date,
        "latest_available_market_date": contract.latest_available_market_date,
        "carryover_used": contract.carryover_used,
        "carryover_reason": contract.carryover_reason,
        "freshness_lag_business_days": contract.freshness_lag_business_days,
        "freshness_limit_business_days": contract.freshness_limit_business_days,
        "status": contract.status,
        "reason": contract.reason,
    }


def _planning_run_id(business_date: str) -> str:
    return f"morning-run-{business_date}-{uuid.uuid4().hex[:12]}"


def _runtime_ai_signal(signal: AIPlanningSignal, rank: int, *, planning_run_id: str) -> AIPlanningSignal:
    return AIPlanningSignal(
        signal_id=f"{planning_run_id}-{signal.signal_id}",
        symbol=signal.symbol,
        side=signal.side,
        rank=rank,
        score=signal.score,
        reason=signal.reason,
        source_ai=signal.source_ai,
    )


def _allocation(
    *,
    row: dict[str, Any],
    signal: AIPlanningSignal,
    per_order_budget: float,
    policy_context: dict[str, Any],
) -> CapitalAllocationSignal:
    price = row.get("__price_evidence")
    if not isinstance(price, PriceEvidence):
        return CapitalAllocationSignal(
            allocation_id=f"morning-allocation-{signal.symbol}",
            symbol=signal.symbol,
            side=signal.side,
            allocated_amount=0.0,
            max_amount=per_order_budget,
            cash_required=0.0,
            reason="reliable_price_source_missing",
            estimated_price=0.0,
            price_source="",
            price_as_of="",
            price_confidence="",
            price_required=True,
            policy_version=str(policy_context.get("policy_version") or ""),
            policy_source=str(policy_context.get("policy_source") or ""),
            sizing_policy_reason=str(policy_context.get("sizing_policy_reason") or ""),
            policy_context=policy_context,
        )
    estimated_price = price.price
    quantity = _round_lot_quantity(per_order_budget, estimated_price)
    cash_required = quantity * estimated_price
    if quantity <= 0:
        cash_required = 0.0
    return CapitalAllocationSignal(
        allocation_id=f"morning-allocation-{signal.symbol}",
        symbol=signal.symbol,
        side=signal.side,
        allocated_amount=cash_required,
        max_amount=per_order_budget,
        cash_required=cash_required,
        reason=f"runtime_evaluation_capital_allocation price={estimated_price} source={price.price_source}",
        estimated_price=estimated_price,
        price_source=price.price_source,
        price_as_of=price.price_as_of,
        price_confidence=price.price_confidence,
        price_required=True,
        policy_version=str(policy_context.get("policy_version") or ""),
        policy_source=str(policy_context.get("policy_source") or ""),
        sizing_policy_reason=str(policy_context.get("sizing_policy_reason") or ""),
        policy_context=policy_context,
    )


def _effective_order_limit(
    *,
    policy: CapitalDeploymentPolicy,
    current_position_count: int,
    operator_max_orders: int | None,
) -> int:
    remaining_slots = max(policy.max_positions - current_position_count, 0)
    if operator_max_orders is None:
        return remaining_slots
    return max(min(operator_max_orders, remaining_slots), 0)


def _policy_planning_budget(
    *,
    policy: CapitalDeploymentPolicy,
    available_cash: float | None,
    current_exposure: float,
) -> float:
    target_exposure = policy.evaluation_capital * policy.target_investment_ratio
    cash_buffer_amount = policy.evaluation_capital * policy.cash_buffer
    target_remaining = max(target_exposure - current_exposure, 0.0)
    exposure_remaining = max(policy.max_exposure - current_exposure, 0.0)
    cash_capacity = 0.0 if available_cash is None else max(float(available_cash) - cash_buffer_amount, 0.0)
    return min(target_remaining, exposure_remaining, cash_capacity)


def _policy_per_order_budget(
    *,
    policy: CapitalDeploymentPolicy,
    planning_budget: float,
    effective_order_limit: int,
) -> float:
    if effective_order_limit <= 0 or planning_budget <= 0:
        return 0.0
    candidates = [
        float(planning_budget) / float(effective_order_limit),
        policy.evaluation_capital * policy.max_position_weight,
    ]
    if policy.max_buy_order_amount is not None:
        candidates.append(policy.max_buy_order_amount)
    return max(min(candidates), 0.0)


def _budget_no_signal_reason(
    *,
    planning_budget: float,
    effective_order_limit: int,
    per_order_budget: float,
) -> str:
    if effective_order_limit <= 0:
        return "NO_SIGNAL:max_positions_reached"
    if planning_budget <= 0:
        return "NO_SIGNAL:available_cash_missing_or_zero"
    if per_order_budget <= 0:
        return "NO_SIGNAL:per_order_budget_missing_or_zero"
    return "NO_SIGNAL:capital_allocation_budget_unavailable"


def _morning_policy_context(
    policy: CapitalDeploymentPolicy,
    *,
    operator_max_orders: int | None,
    effective_order_limit: int,
    planning_budget: float,
    per_order_budget: float,
    current_exposure: float,
    available_cash: float | None,
) -> dict[str, Any]:
    order_count_source = (
        "operator_override_capped_by_policy_max_positions"
        if operator_max_orders is not None
        else "capital_deployment_policy.max_positions"
    )
    return {
        "policy_version": policy.policy_version,
        "policy_source": policy.policy_source,
        "evaluation_capital": policy.evaluation_capital,
        "target_investment_ratio": policy.target_investment_ratio,
        "cash_buffer": policy.cash_buffer,
        "max_exposure": policy.max_exposure,
        "max_position_weight": policy.max_position_weight,
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
        "effective_order_limit": effective_order_limit,
        "operator_max_orders": operator_max_orders,
        "planning_budget": planning_budget,
        "per_order_budget": per_order_budget,
        "current_exposure": current_exposure,
        "available_cash": available_cash,
        "capital_deployment_policy_used_by_morning": True,
        "morning_policy_sizing_method": "target_ratio_cash_buffer_exposure_position_weight",
        "morning_order_count_source": order_count_source,
        "morning_per_order_budget_source": "capital_deployment_policy_derived",
        "morning_hidden_cap_removed": True,
        "sizing_policy_reason": (
            "derived_from Capital Deployment Policy: target_investment_ratio, cash_buffer, "
            "max_exposure, max_position_weight, max_positions, max_buy_order_amount"
        ),
    }


def _empty_morning_policy_context(*, operator_max_orders: int | None) -> dict[str, Any]:
    return {
        "policy_version": "",
        "policy_source": "",
        "operator_max_orders": operator_max_orders,
        "capital_deployment_policy_used_by_morning": False,
        "morning_policy_sizing_method": "",
        "morning_order_count_source": "POLICY_MISSING",
        "morning_per_order_budget_source": "POLICY_MISSING",
        "morning_hidden_cap_removed": True,
    }


def _result_policy_fields(policy_context: dict[str, Any] | None) -> dict[str, Any]:
    context = policy_context or {}
    return {
        "capital_deployment_policy_used_by_morning": bool(context.get("capital_deployment_policy_used_by_morning")),
        "morning_policy_source": str(context.get("policy_source") or ""),
        "morning_policy_version": str(context.get("policy_version") or ""),
        "morning_policy_sizing_method": str(context.get("morning_policy_sizing_method") or ""),
        "morning_policy_target_investment_ratio": context.get("target_investment_ratio"),
        "morning_policy_cash_buffer": context.get("cash_buffer"),
        "morning_policy_max_exposure": context.get("max_exposure"),
        "morning_policy_max_position_weight": context.get("max_position_weight"),
        "morning_policy_max_positions": context.get("max_positions"),
        "morning_policy_max_buy_order_amount": context.get("max_buy_order_amount"),
        "morning_policy_min_order_amount": context.get("min_order_amount"),
        "morning_order_count_source": str(context.get("morning_order_count_source") or ""),
        "morning_per_order_budget_source": str(context.get("morning_per_order_budget_source") or ""),
        "morning_hidden_cap_removed": bool(context.get("morning_hidden_cap_removed")),
    }


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
        "safety_block_submit": bool(fields.get("safety_block_submit")),
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


def _policy_hash(policy_context: dict[str, Any]) -> str:
    return capital_deployment_policy_hash_from_context(policy_context)


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
        price_source=item.price_source,
        price_as_of=item.price_as_of,
        price_confidence=item.price_confidence,
        price_required=item.price_required,
        capital_allocation_amount=item.capital_allocation_amount,
        policy_version=item.policy_version,
        policy_source=item.policy_source,
        evaluation_capital=item.evaluation_capital,
        target_investment_ratio=item.target_investment_ratio,
        cash_buffer=item.cash_buffer,
        max_exposure=item.max_exposure,
        max_position_weight=item.max_position_weight,
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
    )


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


def _available_cash(asset_state: CurrentAssetState, *, capability_default: float | None) -> float | None:
    """Return cash available for new BUY planning from Current SoT.

    Capability default is an initial operating capital fallback only when
    Current has no usable cash/buying_power evidence. It must not reset
    continuity once Runtime-owned Current exists.
    """

    cash = None if asset_state.cash_unknown else asset_state.cash
    buying_power = None if asset_state.buying_power_unknown else asset_state.buying_power
    if cash is not None and buying_power is not None:
        return min(float(cash), float(buying_power))
    if cash is not None:
        return float(cash)
    if buying_power is not None:
        return float(buying_power)
    return float(capability_default) if capability_default is not None else None


def _current_exposure(asset_state: CurrentAssetState) -> float:
    if not asset_state.positions:
        return 0.0
    return float(sum(max(position.market_value, 0.0) for position in asset_state.positions if position.quantity > 0))


def _current_position_symbols(asset_state: CurrentAssetState) -> tuple[str, ...]:
    if not asset_state.positions:
        return ()
    symbols = {
        str(position.symbol).strip()
        for position in asset_state.positions
        if str(position.symbol).strip() and position.quantity > 0
    }
    return tuple(sorted(symbols))


def _symbol(row: dict[str, Any]) -> str:
    return str(row.get("code") or row.get("issue_code") or "").strip()


def _listed_info(row: dict[str, Any]) -> dict[str, Any]:
    info = {
        "code": _symbol(row),
        "market": str(row.get("market_name") or row.get("market") or "東証").strip(),
        "product_category": str(row.get("product_category") or "011").strip(),
        "security_type": str(row.get("security_type") or row.get("product_category") or "011").strip(),
        "current_listed": bool(row.get("is_current_listed", True)),
    }
    buy_eligibility = row.get("__buy_eligibility")
    if isinstance(buy_eligibility, dict) and buy_eligibility:
        info.update(
            {
                "buy_eligibility": buy_eligibility.get("buy_eligibility"),
                "buy_eligibility_status": buy_eligibility.get("status"),
                "buy_ineligible_reason": buy_eligibility.get("reason_code"),
                "market_status_authority_source": buy_eligibility.get("authority_source"),
                "market_status_authority_path": buy_eligibility.get("authority_path"),
                "market_status_authority_hash": buy_eligibility.get("authority_hash"),
                "market_status_authority_as_of": buy_eligibility.get("authority_as_of"),
                "market_status": buy_eligibility.get("market_status"),
                "listing_status": buy_eligibility.get("listing_status"),
                "special_supervision_status": buy_eligibility.get("special_supervision_status"),
                "delisting_date": buy_eligibility.get("delisting_date"),
            }
        )
    opportunity_eligibility = row.get("__opportunity_buy_eligibility")
    if isinstance(opportunity_eligibility, dict) and opportunity_eligibility:
        info.update(
            {
                "opportunity_buy_eligibility_status": opportunity_eligibility.get("status"),
                "opportunity_buy_eligibility": opportunity_eligibility.get("buy_eligibility"),
                "opportunity_expected_edge_score": opportunity_eligibility.get("expected_edge_score"),
                "opportunity_expected_return": opportunity_eligibility.get("expected_return"),
                "opportunity_no_buy_reason": opportunity_eligibility.get("no_buy_reason"),
                "opportunity_buy_rank": opportunity_eligibility.get("buy_rank"),
                "opportunity_artifact_path": opportunity_eligibility.get("opportunity_artifact_path"),
                "opportunity_artifact_hash": opportunity_eligibility.get("opportunity_artifact_hash"),
                "opportunity_business_date": opportunity_eligibility.get("business_date"),
                "opportunity_feature_date": opportunity_eligibility.get("feature_date"),
                "opportunity_eligibility_policy_version": "runtime_v2_opportunity_buy_eligibility_v1",
                "opportunity_eligibility_reason": opportunity_eligibility.get("reason_code"),
            }
        )
    return info


def _broker_symbol(symbol: str, listed_info: dict[str, Any]) -> str:
    del listed_info
    code = str(symbol).strip()
    if len(code) == 5 and code.endswith("0"):
        return code[:-1]
    return code


def _round_lot_quantity(budget: float, price: float) -> float:
    if price <= 0:
        return 0.0
    lots = math.floor((budget / price) / 100.0)
    return float(max(lots, 0) * 100)


def _load_price_source(feature_root: Path, feature_date: str) -> dict[str, PriceEvidence] | None:
    import pandas as pd

    path = _price_source_path(feature_root)
    if not path.exists():
        return None
    frame = pd.read_parquet(path, columns=["Code", "Date", "Close", "PriceSource"])
    if frame.empty:
        return {}
    working = frame[frame["Date"].astype(str) == feature_date].copy()
    if working.empty:
        return {}
    result: dict[str, PriceEvidence] = {}
    for row in working.to_dict(orient="records"):
        symbol = str(row.get("Code") or "").strip()
        price = _optional_float(row.get("Close"))
        if not symbol or price is None or price <= 0:
            continue
        result[symbol] = PriceEvidence(
            symbol=symbol,
            price=price,
            price_source="jquants_raw_normalized_daily_quotes_close",
            price_as_of=str(row.get("Date") or feature_date),
            price_confidence=str(row.get("PriceSource") or "normalized_close"),
            artifact_path=str(path),
        )
    return result


def _price_source_path(feature_root: Path) -> Path:
    operations_root = feature_root.parent
    return operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"


def _sizing_summary(item: PendingOrderItem) -> dict[str, Any]:
    return {
        "symbol": item.symbol,
        "quantity": item.quantity,
        "estimated_price": item.estimated_price,
        "estimated_amount": item.estimated_amount,
        "price_source": item.price_source,
        "price_as_of": item.price_as_of,
        "price_confidence": item.price_confidence,
    }


def _number(value: Any, *, default: float) -> float:
    parsed = _optional_float(value)
    return default if parsed is None else parsed


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed):
        return None
    return parsed


def _previous_calendar_day(value: str) -> str:
    return (date.fromisoformat(value) - timedelta(days=1)).isoformat()


def _morning_artifact_dir(runtime_root: Path, business_date: str) -> Path:
    return runtime_root / "runtime_state" / "morning_pipeline" / business_date


def _reject_mode_rooted_runtime_root(root: Path) -> None:
    text = str(root)
    if text.endswith("/demo") or "/demo/" in text:
        raise ValueError("mode-rooted Current path is not allowed")


def _hash(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
