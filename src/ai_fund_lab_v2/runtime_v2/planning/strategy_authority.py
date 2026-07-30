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
from ai_fund_lab_v2.runtime_v2.approval.policy import build_approval_artifact, build_approval_request
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.safety_authority import (
    HISTORICAL_NEUTRAL_SAFETY_POLICY_VERSION,
    HISTORICAL_NEUTRAL_SAFETY_SOURCE,
    materialize_historical_pending_safety_context,
)
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
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

    def to_stage_details(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["selected_symbols"] = list(self.selected_symbols)
        payload["reason_codes"] = list(self.reason_codes)
        return payload


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
    sizing_by_symbol = {
        str(item.get("security_code") or ""): item
        for item in position_sizing_payload.get("positions", []) or []
        if isinstance(item, dict) and str(item.get("security_code") or "")
    }
    pending_items: list[PendingOrderItem] = []
    item_lineage: list[dict[str, Any]] = []
    plans = list(runtime_planning_payload.get("plans") or [])
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        item, item_reason = _pending_item_from_strategy_plan(
            plan=plan,
            sizing=sizing_by_symbol.get(str(plan.get("security_code") or "")) or {},
            business_date=business_date,
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
            }
        )
        if item is not None:
            item = _pending_item_with_submit_policy_context(item=item, submit_policy_context=submit_policy_context)
            item = _pending_item_with_safety_context(item=item, safety_context=safety_context)
            pending_items.append(item)
        elif item_reason and not item_reason.startswith("no_action"):
            reason_codes.append(item_reason)

    result_status = "PASS" if pending_items else ("REVIEW_REQUIRED" if reason_codes else "NO_ORDER_AUTHORIZED")
    order_plan_payload = {
        "schema_version": "phase23_i_strategy_authority_order_plan.v1",
        "order_plan_id": _order_plan_id(mode=mode, business_date=business_date, strategy_hash=_file_hash(runtime_planning_path)),
        "environment": mode,
        "business_date": business_date,
        "target_session_date": target_session_date,
        "status": "CREATED" if pending_items else result_status,
        "planning_authority": "phase22_strategy_runtime_planning",
        "strategy_artifact_path": str(runtime_planning_path),
        "strategy_artifact_hash": _file_hash(runtime_planning_path),
        "position_sizing_artifact_path": str(position_sizing_path),
        "position_sizing_artifact_hash": _file_hash(position_sizing_path),
        "items": [_pending_item_payload(item) for item in pending_items],
        "safety_context": safety_context,
        "strategy_item_lineage": item_lineage,
        "strategy_artifact_eligibility": _strategy_artifact_eligibility(runtime_planning_payload),
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
    if safety_context:
        pending = replace(
            pending,
            safety_context=safety_context,
            safety_decision_id=str(safety_context.get("safety_decision_id") or ""),
            safety_policy_version=str(safety_context.get("safety_policy_version") or ""),
        )
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
            ),
        )
        _write_json(approval_path, _jsonable(approval))
        pending = link_approval_to_pending(pending_plan=pending, approval_artifact=approval)
    elif reason_codes:
        _write_json(approval_path, {"status": "REVIEW_REQUIRED", "reason": "strategy_planning_authority_unresolved", "business_date": business_date, "reason_codes": sorted(set(reason_codes))})
        pending = replace(pending, state=PendingPlanState.REVIEW_REQUIRED)
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
            "safety_authority": _safety_lineage(safety_context=safety_context),
            "submit_policy_authority": _submit_policy_lineage(submit_policy_context=submit_policy_context),
        },
    )


def _pending_item_from_strategy_plan(
    *,
    plan: Mapping[str, Any],
    sizing: Mapping[str, Any],
    business_date: str,
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
    pending_item_id = "strategy-" + hashlib.sha256(
        f"{business_date}|{symbol}|{intent}|{side}|{plan.get('planning_id')}".encode("utf-8")
    ).hexdigest()[:20]
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
        listed_info=_listed_info_from_opportunity_authority(
            symbol=symbol,
            business_date=business_date,
            opportunity_authority=plan.get("opportunity_authority") if isinstance(plan.get("opportunity_authority"), Mapping) else {},
        ),
        price_source="jquants_raw_normalized_daily_quotes_close",
        price_as_of=str(price_resolution.get("price_date") or business_date),
        price_confidence="PIT",
        capital_allocation_amount=round(float(planned_quantity) * price, 2),
        policy_version="phase22_strategy_planning_authority",
        policy_source=str(plan.get("planning_id") or ""),
        planning_authority_version="phase22_strategy_planning_authority",
        planning_authority_source=str(plan.get("planning_id") or ""),
        planning_authority_hash=str(plan.get("planning_hash") or ""),
        buy_notional_policy="phase22_position_sizing_incremental_notional",
        sizing_policy_reason="derived_from_phase22_position_sizing_target_notional",
        quantity_contract={
            "quantity_authority": "phase23_i_strategy_planning_authority_consumer",
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
            "reference_price_resolution": dict(plan.get("reference_price_resolution") or {}),
            "reference_price_type": str(plan.get("reference_price_type") or ""),
            "reference_price_date": str(plan.get("reference_price_date") or ""),
        },
        source_decision_type=intent,
        source_pm_decision_id=str(plan.get("pm_position_reference") or ""),
        source_pm_business_date=business_date,
        source_position_symbol=symbol,
        add_candidate_signal=intent in {"BUY_NEW", "BUY_ADD"},
        capital_allocation_status="APPROVED",
        capital_allocation_reason="phase22_strategy_position_sizing_consumed",
    ), "pending_item_generated"


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


def _listed_info_from_opportunity_authority(
    *,
    symbol: str,
    business_date: str,
    opportunity_authority: Mapping[str, Any],
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


def _planning_lineage_context(*, order_plan_payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "planning_authority_version": str(order_plan_payload.get("planning_authority") or "phase22_strategy_runtime_planning"),
        "planning_authority_source": str(order_plan_payload.get("order_plan_id") or ""),
        "planning_authority_hash": str(order_plan_payload.get("strategy_artifact_hash") or ""),
        "runtime_plan_id": str(order_plan_payload.get("order_plan_id") or ""),
        "strategy_artifact_path": str(order_plan_payload.get("strategy_artifact_path") or ""),
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
    write_pending_order_plan(pending_path, pending)
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


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()
