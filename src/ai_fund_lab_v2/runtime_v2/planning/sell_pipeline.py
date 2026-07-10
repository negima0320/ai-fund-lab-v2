"""Runtime v2 SELL planning pipeline from Current Position to Pending."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalDecision, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.approval.policy import build_approval_artifact, build_approval_request
from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetPosition, CurrentAssetState
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import CapitalDeploymentPolicy
from ai_fund_lab_v2.runtime_v2.planning.models import AIPlanningSignal, CapitalAllocationSignal, PlanningInput, RuntimeSafetyContext
from ai_fund_lab_v2.runtime_v2.planning.planner import build_order_plan
from ai_fund_lab_v2.runtime_v2.safety_decision import (
    RuntimeSafetyDecision,
    load_runtime_safety_decision,
    safety_allows_action,
    safety_manifest_fields,
)


@dataclass(frozen=True)
class SellExitDecision:
    symbol: str
    quantity: float
    reason: str
    score: float = 1.0


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

    def to_stage_details(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["selected_symbols"] = list(self.selected_symbols)
        return payload


def run_sell_planning_pending_pipeline(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    exit_decisions: tuple[SellExitDecision, ...],
    max_orders: int | None = None,
    capital_deployment_policy: CapitalDeploymentPolicy | None = None,
    safety_decision: RuntimeSafetyDecision | None = None,
) -> SellPlanningPipelineResult:
    """Build SELL OrderPlan/Approval/Pending from Current positions only.

    The pipeline performs no Broker write. Exit AI output is represented by
    ``exit_decisions``; BUY candidates are never accepted as SELL sources.
    """

    if mode not in {"demo", "production"}:
        raise ValueError("sell planning pipeline supports demo/production only")
    runtime_root_path = Path(runtime_root)
    _reject_mode_rooted_runtime_root(runtime_root_path)
    target_session_date = business_date
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
    if not current_positions:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            business_date=business_date,
            target_session_date=target_session_date,
            environment=mode,
            reason="NO_SIGNAL:current_position_missing",
            current_position_count=0,
            current_exposure=current_exposure,
            safety_decision=runtime_safety_decision,
        )

    selected_decisions = tuple(exit_decisions[:max_orders])
    if not selected_decisions:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            business_date=business_date,
            target_session_date=target_session_date,
            environment=mode,
            reason="NO_SIGNAL:exit_ai_no_sell_signal",
            current_position_count=len(current_positions),
            current_exposure=current_exposure,
            safety_decision=runtime_safety_decision,
        )

    ai_signals = tuple(_ai_signal(decision, index) for index, decision in enumerate(selected_decisions, start=1))
    policy_context = _policy_context(capital_deployment_policy)
    allocations = tuple(
        _allocation(
            decision=decision,
            signal=signal,
            position=current_positions.get(decision.symbol),
            policy_context=policy_context,
        )
        for decision, signal in zip(selected_decisions, ai_signals)
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
    order_plan_path.write_text(_json_dumps(_jsonable(planning_result.order_plan)), encoding="utf-8")
    pending_items = tuple(
        _pending_item(item)
        for item in planning_result.order_plan.items
        if not item.blocked and not item.review_required and item.quantity > 0
    )
    pending = promote_order_plan_to_pending(
        order_plan_id=planning_result.order_plan.order_plan_id,
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash=_hash(order_plan_path.read_text(encoding="utf-8")),
        environment=mode,
        plan_created_date=business_date,
        intended_submit_date=target_session_date,
        target_session_date=target_session_date,
        items=pending_items,
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
            ),
        )
        approval_path.write_text(_json_dumps(_jsonable(approval)), encoding="utf-8")
        pending = link_approval_to_pending(pending_plan=pending, approval_artifact=approval)
    else:
        approval_path.write_text(
            _json_dumps({"status": "NO_SIGNAL", "reason": "no pending SELL items after planning"}),
            encoding="utf-8",
        )

    pending_path = runtime_root_path / "pending_order_plan" / "pending_order_plan.json"
    write_pending_order_plan(pending_path, pending)
    blocked_count = sum(1 for item in planning_result.order_plan.items if item.blocked)
    return SellPlanningPipelineResult(
        status="PASS" if pending_items else "REVIEW_REQUIRED",
        reason="" if pending_items else "no pending SELL items after planning",
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
        **_result_safety_fields(runtime_safety_decision),
    )


def _write_no_signal_pending(
    *,
    runtime_root: Path,
    business_date: str,
    target_session_date: str,
    environment: str,
    reason: str,
    current_position_count: int,
    current_exposure: float,
    status: str = "NO_SIGNAL",
    safety_decision: RuntimeSafetyDecision | None = None,
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
    order_plan_path.write_text(_json_dumps(order_plan_payload), encoding="utf-8")
    approval_path.write_text(_json_dumps({"status": "NO_SIGNAL", "reason": reason}), encoding="utf-8")
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
        from dataclasses import replace

        pending = replace(
            pending,
            safety_context=_safety_context_payload(safety_decision),
            safety_decision_id=safety_decision.safety_decision_id,
            safety_policy_version=safety_decision.safety_policy_version,
        )
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    write_pending_order_plan(pending_path, pending)
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
        **_result_safety_fields(safety_decision),
    )


def _ai_signal(decision: SellExitDecision, rank: int) -> AIPlanningSignal:
    return AIPlanningSignal(
        signal_id=f"sell-exit-ai-{decision.symbol}-{rank:03d}",
        symbol=decision.symbol,
        side="SELL",
        rank=rank,
        score=decision.score,
        reason=decision.reason,
        source_ai="runtime_v2_exit_ai",
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


def _policy_context(policy: CapitalDeploymentPolicy | None) -> dict[str, Any] | None:
    if policy is None:
        return None
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
        "sizing_policy_reason": "sell liquidation governed by Capital Deployment Policy evidence",
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
