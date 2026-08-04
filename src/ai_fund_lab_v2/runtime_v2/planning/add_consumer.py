"""PM ADD consumer for Runtime v2 Pending BUY planning."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetPosition, CurrentAssetState
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingOrderPlan
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import CapitalDeploymentPolicy
from ai_fund_lab_v2.runtime_v2.cash_exposure_authority import CashExposureAuthority
from ai_fund_lab_v2.runtime_v2.position_sizing_authority import PositionSizingAuthority
from ai_fund_lab_v2.runtime_v2.safety_decision import RuntimeSafetyDecision
from ai_fund_lab_v2.runtime_v2.symbol_identity import contains_symbol_identity, same_symbol_identity


DEFAULT_TRADABLE_UNIT = 100.0


@dataclass(frozen=True)
class AddConsumerResult:
    status: str
    reason: str
    accepted_items: tuple[PendingOrderItem, ...]
    rejected: tuple[dict[str, Any], ...]
    requested_count: int
    accepted_count: int
    rejected_count: int

    def to_evidence(self) -> dict[str, Any]:
        return {
            "add_consumer_status": self.status,
            "add_consumer_reason": self.reason,
            "requested_count": self.requested_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "accepted_pending_item_ids": [item.pending_item_id for item in self.accepted_items],
            "rejected": list(self.rejected),
        }


def build_add_pending_items(
    *,
    add_decisions: Sequence[Any],
    asset_state: CurrentAssetState,
    current_positions: Mapping[str, CurrentAssetPosition],
    existing_buy_pending: PendingOrderPlan | None,
    business_date: str,
    target_session_date: str,
    environment: str,
    capital_deployment_policy: CapitalDeploymentPolicy | None,
    safety_decision: RuntimeSafetyDecision | None,
    cash_exposure_authority: CashExposureAuthority | None = None,
    position_sizing_authorities: Mapping[str, PositionSizingAuthority] | None = None,
) -> AddConsumerResult:
    add_candidates = tuple(
        decision
        for decision in add_decisions
        if str(getattr(decision, "source_decision", "") or "").upper() == "ADD"
    )
    if not add_candidates:
        return AddConsumerResult("NOT_REQUIRED", "ADD decision missing", (), (), 0, 0, 0)
    rejected: list[dict[str, Any]] = []
    if capital_deployment_policy is None:
        return AddConsumerResult(
            "REJECTED",
            "AUTHORITY_NOT_ACCEPTED",
            (),
            tuple(_reject(decision, "AUTHORITY_NOT_ACCEPTED", business_date) for decision in add_candidates),
            len(add_candidates),
            0,
            len(add_candidates),
        )
    if safety_decision is not None and bool(safety_decision.block_buy):
        return AddConsumerResult(
            "REJECTED",
            "AUTHORITY_NOT_ACCEPTED",
            (),
            tuple(_reject(decision, "AUTHORITY_NOT_ACCEPTED", business_date) for decision in add_candidates),
            len(add_candidates),
            0,
            len(add_candidates),
        )

    existing_pending_buy_symbols = {
        item.symbol
        for item in (existing_buy_pending.items if existing_buy_pending is not None else ())
        if item.side.upper() == "BUY" and item.quantity > 0
    }
    accepted: list[PendingOrderItem] = []
    accepted_symbols: set[str] = set()
    current_exposure = float(sum(position.market_value for position in current_positions.values()))
    active_deployment_capital = _active_deployment_capital(asset_state, current_exposure=current_exposure)
    selected_cash_exposure = (
        cash_exposure_authority.with_runtime_state(
            current_cash=_cash_capacity(asset_state),
            current_market_value=current_exposure,
            current_total_equity=active_deployment_capital,
            active_deployment_capital=active_deployment_capital,
        )
        if cash_exposure_authority is not None
        else None
    )
    if selected_cash_exposure is None or not selected_cash_exposure.passed:
        return AddConsumerResult(
            "REJECTED",
            "DYNAMIC_CASH_EXPOSURE_AUTHORITY_MISSING",
            (),
            tuple(_reject(decision, "DYNAMIC_CASH_EXPOSURE_AUTHORITY_MISSING", business_date) for decision in add_candidates),
            len(add_candidates),
            0,
            len(add_candidates),
        )
    remaining_exposure = max(selected_cash_exposure.remaining_exposure_capacity, 0.0)
    remaining_cash = max(selected_cash_exposure.available_cash_after_target, 0.0)
    for index, decision in enumerate(add_candidates, start=1):
        symbol = str(getattr(decision, "symbol", "") or "").strip()
        position = _matching_position(current_positions, symbol)
        if position is None or position.quantity <= 0:
            rejected.append(_reject(decision, "INVALID_CURRENT_POSITION", business_date))
            continue
        if contains_symbol_identity(existing_pending_buy_symbols, symbol) or contains_symbol_identity(accepted_symbols, symbol):
            rejected.append(_reject(decision, "DUPLICATE_PENDING_ORDER", business_date))
            continue
        price = _position_price(position)
        if price <= 0:
            rejected.append(_reject(decision, "OPPORTUNITY_NO_LONGER_ELIGIBLE", business_date))
            continue
        if position.average_price > 0 and price < position.average_price:
            rejected.append(_reject(decision, "NO_LOSS_AVERAGING_GUARD", business_date))
            continue
        if active_deployment_capital is None:
            rejected.append(_reject(decision, "ACTIVE_DEPLOYMENT_CAPITAL_MISSING", business_date))
            continue
        selected_position_sizing = _matching_position_sizing_authority(position_sizing_authorities or {}, symbol)
        if selected_position_sizing is None or not selected_position_sizing.passed:
            rejected.append(_reject(decision, "POSITION_SIZING_AUTHORITY_MISSING", business_date))
            continue
        position_capacity = max(float(selected_position_sizing.remaining_add_capacity), 0.0)
        if position_capacity <= 0:
            rejected.append(_reject(decision, "POSITION_SIZING_NO_ADD_CAPACITY", business_date))
            continue
        if remaining_exposure <= 0:
            rejected.append(_reject(decision, "MAX_EXPOSURE", business_date))
            continue
        if remaining_cash <= 0:
            rejected.append(_reject(decision, "INSUFFICIENT_CASH", business_date))
            continue
        requested_notional = min(
            position_capacity,
            remaining_exposure,
            remaining_cash,
            _optional_cap(capital_deployment_policy.max_buy_order_amount),
        )
        if requested_notional < float(capital_deployment_policy.min_order_amount):
            rejected.append(_reject(decision, "INSUFFICIENT_CASH", business_date, requested_notional=requested_notional))
            continue
        quantity = math.floor((requested_notional / price) / DEFAULT_TRADABLE_UNIT) * DEFAULT_TRADABLE_UNIT
        approved_notional = quantity * price
        if quantity <= 0 or approved_notional < float(capital_deployment_policy.min_order_amount):
            rejected.append(_reject(decision, "LOT_SIZE_NOT_VIABLE", business_date, requested_notional=requested_notional))
            continue
        item = PendingOrderItem(
            pending_item_id=f"opi-pm-add-{business_date}-{symbol}-{index:03d}",
            symbol=symbol,
            side="BUY",
            quantity=quantity,
            order_type="MARKET",
            estimated_price=price,
            estimated_amount=approved_notional,
            approved=False,
            state="READY",
            listed_info={
                "code": symbol,
                "market": "東証",
                "product_category": "011",
                "security_type": "011",
                "current_listed": True,
                "opportunity_business_date": business_date,
                "opportunity_feature_date": target_session_date,
                "opportunity_expected_edge_score": max(float(getattr(decision, "score", 0.0) or 0.0), 0.000001),
                "opportunity_expected_return": None,
                "opportunity_no_buy_reason": "",
                "opportunity_buy_rank": None,
                "opportunity_artifact_path": str(getattr(decision, "source_decision_artifact", "") or ""),
                "opportunity_artifact_hash": "",
            },
            price_source="current_sot_position_valuation",
            price_as_of=str(position.as_of or asset_state.as_of),
            price_confidence="current_sot",
            price_required=True,
            capital_allocation_amount=approved_notional,
            policy_version=capital_deployment_policy.policy_version,
            policy_source=capital_deployment_policy.policy_source,
            evaluation_capital=capital_deployment_policy.evaluation_capital,
            target_investment_ratio=None,
            cash_buffer=None,
            max_exposure=None,
            max_positions=capital_deployment_policy.max_positions,
            max_buy_order_amount=capital_deployment_policy.max_buy_order_amount,
            max_sell_liquidation_amount=capital_deployment_policy.max_sell_liquidation_amount,
            min_order_amount=capital_deployment_policy.min_order_amount,
            buy_notional_policy=capital_deployment_policy.buy_notional_policy,
            sell_liquidation_policy=capital_deployment_policy.sell_liquidation_policy,
            manual_review_threshold=capital_deployment_policy.manual_review_threshold.__dict__,
            sizing_policy_reason="pm_add_position_sizing_authority",
            safety_decision_id=str(safety_decision.safety_decision_id if safety_decision is not None else ""),
            safety_policy_version=str(safety_decision.safety_policy_version if safety_decision is not None else ""),
            safety_source=str(safety_decision.safety_source if safety_decision is not None else ""),
            safety_decision=str(safety_decision.decision if safety_decision is not None else ""),
            safety_reason=str(safety_decision.reason if safety_decision is not None else ""),
            quantity_contract={
                "quantity_contract_version": "runtime_v2_pm_add_quantity_v1",
                "source_decision": "ADD",
                "selected_capital_source": _capital_source(asset_state),
                "selected_capital_value": active_deployment_capital,
                "capital_authority_winner": "current_total_equity",
                "active_deployment_capital": active_deployment_capital,
                "legacy_capital_config_used": False,
                "capital_fallback_used": False,
                "cash_exposure_authority": selected_cash_exposure.to_dict(),
                **selected_cash_exposure.to_dict(),
                "position_sizing_authority": selected_position_sizing.with_lot_adjustment(
                    quantity=quantity,
                    notional=approved_notional,
                ).to_dict(),
                **selected_position_sizing.with_lot_adjustment(
                    quantity=quantity,
                    notional=approved_notional,
                ).to_dict(),
                "requested_add_notional": requested_notional,
                "approved_add_notional": approved_notional,
                "tradable_unit": DEFAULT_TRADABLE_UNIT,
                "final_buy_quantity": quantity,
                "status": "PASS",
                "reason": "pm_add_position_sizing_allocation_pass",
            },
            source_decision_type="ADD",
            source_pm_decision_id=str(getattr(decision, "source_decision_id", "") or ""),
            source_pm_business_date=business_date,
            source_position_symbol=str(position.symbol),
            add_candidate_signal=True,
            capital_allocation_status="APPROVED",
            capital_allocation_reason="pm_add_position_sizing_allocation_pass",
            requested_add_notional=requested_notional,
            approved_add_notional=approved_notional,
            rejected_reason="",
        )
        accepted.append(item)
        accepted_symbols.add(symbol)
        remaining_exposure = max(remaining_exposure - approved_notional, 0.0)
        remaining_cash = max(remaining_cash - approved_notional, 0.0)
    status = "PASS" if accepted else "REJECTED"
    reason = "ADD pending items generated" if accepted else "all ADD candidates rejected"
    return AddConsumerResult(status, reason, tuple(accepted), tuple(rejected), len(add_candidates), len(accepted), len(rejected))


def _matching_position(
    current_positions: Mapping[str, CurrentAssetPosition],
    symbol: str,
) -> CurrentAssetPosition | None:
    for existing_symbol, position in current_positions.items():
        if same_symbol_identity(existing_symbol, symbol):
            return position
    return None


def _matching_position_sizing_authority(
    authorities: Mapping[str, PositionSizingAuthority],
    symbol: str,
) -> PositionSizingAuthority | None:
    for existing_symbol, authority in authorities.items():
        if same_symbol_identity(existing_symbol, symbol):
            return authority
    return None


def _position_price(position: CurrentAssetPosition) -> float:
    if position.quantity <= 0:
        return 0.0
    if position.market_value > 0:
        return float(position.market_value) / float(position.quantity)
    return float(position.average_price)


def _cash_capacity(asset_state: CurrentAssetState) -> float:
    values = [
        float(value)
        for value in (asset_state.buying_power, asset_state.cash)
        if value is not None and float(value) >= 0
    ]
    if not values:
        return 0.0
    return min(values)


def _active_deployment_capital(asset_state: CurrentAssetState, *, current_exposure: float) -> float | None:
    _ = current_exposure
    if asset_state.total_equity is not None:
        return float(asset_state.total_equity)
    return None


def _capital_source(asset_state: CurrentAssetState) -> str:
    if asset_state.total_equity is not None:
        return "current_state.total_equity"
    return "current_state.total_equity_missing"


def _optional_cap(value: float | None) -> float:
    if value is None:
        return float("inf")
    return float(value)


def _reject(
    decision: Any,
    reason: str,
    business_date: str,
    *,
    requested_notional: float | None = None,
) -> dict[str, Any]:
    return {
        "source_decision_type": "ADD",
        "source_pm_decision_id": str(getattr(decision, "source_decision_id", "") or ""),
        "source_pm_business_date": business_date,
        "source_position_symbol": str(getattr(decision, "symbol", "") or ""),
        "add_candidate_signal": True,
        "capital_allocation_status": "REJECTED",
        "capital_allocation_reason": reason,
        "requested_add_notional": requested_notional,
        "approved_add_notional": 0.0,
        "quantity": 0.0,
        "rejected_reason": reason,
    }
