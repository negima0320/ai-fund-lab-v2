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
from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import (
    get_broker_capability,
    is_symbol_allowed_by_capability,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.feature_date_contract import (
    FeatureDateContract,
    load_feature_date_contract,
    resolve_feature_date_contract,
)
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.pending.models import PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.planning.models import (
    AIPlanningSignal,
    CapitalAllocationSignal,
    PlanningInput,
    SafetySignal,
)
from ai_fund_lab_v2.runtime_v2.planning.planner import build_order_plan


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
    sample_order_sizing: tuple[dict[str, Any], ...] = ()

    def to_stage_details(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["selected_symbols"] = list(self.selected_symbols)
        payload["sample_order_sizing"] = list(self.sample_order_sizing)
        return payload


def run_morning_ai_planning_pending_pipeline(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    feature_root: Path | str = ".runtime/operations/feature_artifacts",
    feature_date: str | None = None,
    max_orders: int = 5,
) -> MorningPipelineResult:
    """Connect feature input to Planning, Approval, and Current Pending.

    The pipeline performs no Submit and no Broker write. It writes only the
    canonical Pending Current and derived morning artifacts.
    """

    if mode not in {"demo", "production"}:
        raise ValueError("morning pipeline supports demo/production capability only")

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
    evaluation_capital = capability.default_evaluation_capital or asset_state.total_equity or asset_state.buying_power
    available_cash = _available_cash(asset_state, capability_default=capability.default_evaluation_capital)
    planning_budget = available_cash
    current_exposure = _current_exposure(asset_state)
    current_position_symbols = _current_position_symbols(asset_state)
    if evaluation_capital is None:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
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
        )
    if planning_budget is None or planning_budget <= 0:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            business_date=business_date,
            feature_date=resolved_feature_date,
            feature_contract=feature_contract,
            target_session_date=target_session_date,
            reason="NO_SIGNAL:available_cash_missing_or_zero",
            evaluation_capital=evaluation_capital,
            available_cash=available_cash,
            planning_budget=planning_budget,
            current_exposure=current_exposure,
            current_position_symbols=current_position_symbols,
        )
    if feature_contract.status != "PASS":
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
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
        )

    feature_dir = Path(feature_root) / resolved_feature_date
    feature_inputs = _load_feature_inputs(feature_dir)
    missing = tuple(name for name, value in feature_inputs.items() if value is None)
    if missing:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            business_date=business_date,
            feature_date=resolved_feature_date,
            feature_contract=feature_contract,
            target_session_date=target_session_date,
            reason="feature_input_missing:" + ",".join(missing),
            status="REVIEW_REQUIRED",
            evaluation_capital=evaluation_capital,
            available_cash=available_cash,
            planning_budget=planning_budget,
            current_exposure=current_exposure,
            current_position_symbols=current_position_symbols,
        )

    candidate_rows = _candidate_rows(feature_inputs["candidate"])
    if not candidate_rows:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
            business_date=business_date,
            feature_date=resolved_feature_date,
            feature_contract=feature_contract,
            target_session_date=target_session_date,
            reason="NO_SIGNAL:candidate_rows_empty",
            evaluation_capital=evaluation_capital,
            available_cash=available_cash,
            planning_budget=planning_budget,
            current_exposure=current_exposure,
            current_position_symbols=current_position_symbols,
        )

    per_order_budget = min(float(planning_budget) / max(max_orders, 1), 100_000.0)
    price_source = _load_price_source(Path(feature_root), resolved_feature_date)
    if price_source is None:
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
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
        )

    selected_rows: list[dict[str, Any]] = []
    demo_filtered_9000_count = 0
    price_missing_count = 0
    budget_excluded_count = 0
    existing_position_excluded_count = 0
    for row in candidate_rows:
        symbol = _symbol(row)
        if not is_symbol_allowed_by_capability(symbol, capability):
            demo_filtered_9000_count += 1
            continue
        broker_symbol = _broker_symbol(symbol, _listed_info(row))
        if broker_symbol in current_position_symbols:
            existing_position_excluded_count += 1
            continue
        price = price_source.get(symbol)
        if price is None:
            price_missing_count += 1
            continue
        quantity = _round_lot_quantity(per_order_budget, price.price)
        if quantity <= 0:
            budget_excluded_count += 1
            continue
        selected_rows.append({**row, "__price_evidence": price, "__planned_quantity": quantity})
        if len(selected_rows) >= max_orders:
            break
    if not selected_rows:
        reason = (
            "NO_SIGNAL:demo_capability_filtered_all_9000_series"
            if demo_filtered_9000_count >= len(candidate_rows)
            else "NO_SIGNAL:no_affordable_candidates_with_reliable_price"
        )
        return _write_no_signal_pending(
            runtime_root=runtime_root_path,
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
        )

    planning_run_id = _planning_run_id(business_date)
    ai_signals = tuple(
        _ai_signal(row, rank, planning_run_id=planning_run_id)
        for rank, row in enumerate(selected_rows, start=1)
    )
    allocations = tuple(
        _allocation(row=row, signal=signal, per_order_budget=per_order_budget)
        for row, signal in zip(selected_rows, ai_signals)
    )
    safety = tuple(_safety(signal) for signal in ai_signals)
    planning_result = build_order_plan(
        PlanningInput(
            mode=mode,
            environment=mode,
            business_date=business_date,
            target_session_date=target_session_date,
            asset_state=asset_state,
            ai_signals=ai_signals,
            capital_allocations=allocations,
            safety_signals=safety,
        )
    )
    order_plan_path = _morning_artifact_dir(runtime_root_path, business_date) / "order_plan.json"
    order_plan_path.parent.mkdir(parents=True, exist_ok=True)
    order_plan_payload = _jsonable(planning_result.order_plan)
    order_plan_payload["feature_date_contract"] = _feature_contract_payload(feature_contract)
    order_plan_payload["market_data_freshness"] = _market_data_freshness_payload(feature_contract)
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
        existing_position_excluded_count=existing_position_excluded_count,
        selected_price_source="jquants_raw_normalized_daily_quotes_close",
        price_source_status="PASS",
        price_source_path=str(_price_source_path(Path(feature_root))),
        price_missing_count=price_missing_count,
        budget_excluded_count=budget_excluded_count,
        sample_order_sizing=tuple(_sizing_summary(item) for item in pending.items),
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
) -> MorningPipelineResult:
    order_plan_path = _morning_artifact_dir(runtime_root, business_date) / "order_plan.json"
    approval_path = _morning_artifact_dir(runtime_root, business_date) / "approval_artifact.json"
    order_plan_path.parent.mkdir(parents=True, exist_ok=True)
    order_plan_payload = {
        "schema_version": "1",
        "order_plan_id": f"order-plan-morning-no-signal-{business_date}",
        "environment": "demo",
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
        environment="demo",
        business_date=business_date,
        target_session_date=target_session_date,
        items=(),
    )
    pending = replace(pending, feature_date_contract=_feature_contract_payload(feature_contract))
    if status == "REVIEW_REQUIRED":
        pending = replace(pending, state=PendingPlanState.REVIEW_REQUIRED)
    elif status == "BLOCKED":
        pending = replace(pending, state=PendingPlanState.BLOCKED)
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    write_pending_order_plan(pending_path, pending)
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
        existing_position_excluded_count=existing_position_excluded_count,
        selected_price_source="jquants_raw_normalized_daily_quotes_close",
        price_source_status=price_source_status,
        price_source_path=price_source_path,
        price_missing_count=price_missing_count,
        budget_excluded_count=budget_excluded_count,
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


def _candidate_rows(frame) -> list[dict[str, Any]]:
    if frame is None or frame.empty:
        return []
    working = frame.copy()
    if "universe_eligible" in working.columns:
        working = working[working["universe_eligible"].fillna(False).astype(bool)]
    sort_columns = [
        column
        for column in (
            "price_momentum_return_20d",
            "price_momentum_return_5d",
            "liquidity_avg_volume_20d",
        )
        if column in working.columns
    ]
    if sort_columns:
        working = working.sort_values(sort_columns, ascending=[False] * len(sort_columns))
    return list(working.to_dict(orient="records"))


def _planning_run_id(business_date: str) -> str:
    return f"morning-run-{business_date}-{uuid.uuid4().hex[:12]}"


def _ai_signal(row: dict[str, Any], rank: int, *, planning_run_id: str) -> AIPlanningSignal:
    symbol = _symbol(row)
    score = _number(row.get("price_momentum_return_20d"), default=0.0)
    return AIPlanningSignal(
        signal_id=f"{planning_run_id}-ai-{symbol}-{rank:03d}",
        symbol=symbol,
        side="BUY",
        rank=rank,
        score=score,
        reason="feature momentum inference",
        source_ai="runtime_v2_morning_feature_inference",
    )


def _allocation(
    *,
    row: dict[str, Any],
    signal: AIPlanningSignal,
    per_order_budget: float,
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
    )


def _safety(signal: AIPlanningSignal) -> SafetySignal:
    return SafetySignal(
        safety_id=f"morning-safety-{signal.symbol}",
        symbol=signal.symbol,
        side=signal.side,
        allowed=True,
        review_required=False,
        blocked=False,
        reason="morning pipeline safety placeholder allow",
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
        price_source=item.price_source,
        price_as_of=item.price_as_of,
        price_confidence=item.price_confidence,
        price_required=item.price_required,
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
    return {
        "code": _symbol(row),
        "market": str(row.get("market_name") or row.get("market") or "東証").strip(),
        "product_category": str(row.get("product_category") or "011").strip(),
        "security_type": str(row.get("security_type") or row.get("product_category") or "011").strip(),
        "current_listed": bool(row.get("is_current_listed", True)),
    }


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
