"""Shared Submit feasibility authority for Planning and Submit evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import CapitalDeploymentPolicy
from ai_fund_lab_v2.runtime_v2.cash_exposure_authority import (
    CashExposureAuthority,
    cash_exposure_authority_from_context,
)
from ai_fund_lab_v2.runtime_v2.position_count_authority import (
    PositionCountAuthority,
    position_count_authority_from_context,
)
from ai_fund_lab_v2.runtime_v2.position_sizing_authority import (
    PositionSizingAuthority,
    position_sizing_authority_from_context,
)
from ai_fund_lab_v2.runtime_v2.executable_membership_guard import (
    evaluate_precomputable_executable_membership_guard,
)
from ai_fund_lab_v2.runtime_v2.symbol_identity import contains_symbol_identity


@dataclass(frozen=True)
class RuntimeCurrentExposure:
    cash: float | None
    buying_power: float | None
    current_exposure: float
    current_total_equity: float | None
    active_deployment_capital: float | None
    selected_capital_source: str
    capital_fallback_used: bool
    initial_or_bootstrap_capital: float | None
    positions: dict[str, float]
    position_market_values: dict[str, float]
    current_position_source: str
    selected_current_source: str = "persistent_ledger/state.json"
    selected_cash_source: str = "persistent_ledger/state.json:cash"
    selected_positions_source: str = "persistent_ledger/state.json:positions"
    selected_valuation_source: str = "persistent_ledger/state.json:positions.market_value"
    selected_projection_source: str = ""
    current_authority_winner: str = "persistent_ledger_state"
    current_source_business_date: str = ""
    current_source_generation: str = ""
    current_authority_status: str = "PASS"
    current_authority_reason: str = "current_authority_resolved"
    source_conflict_detected: bool = False
    source_selection_reason: str = "explicit_persistent_ledger_state_current_authority"
    legacy_current_used: bool = False
    current_fallback_used: bool = False
    runtime_evaluation_capital_used_as_current: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "selected_current_source": self.selected_current_source,
            "selected_cash_source": self.selected_cash_source,
            "selected_positions_source": self.selected_positions_source,
            "selected_valuation_source": self.selected_valuation_source,
            "selected_projection_source": self.selected_projection_source,
            "current_authority_winner": self.current_authority_winner,
            "current_source_business_date": self.current_source_business_date,
            "current_source_generation": self.current_source_generation,
            "current_authority_status": self.current_authority_status,
            "current_authority_reason": self.current_authority_reason,
            "source_conflict_detected": self.source_conflict_detected,
            "source_selection_reason": self.source_selection_reason,
            "legacy_current_used": self.legacy_current_used,
            "current_fallback_used": self.current_fallback_used,
            "runtime_evaluation_capital_used_as_current": self.runtime_evaluation_capital_used_as_current,
            "cash": self.cash,
            "buying_power": self.buying_power,
            "current_exposure": self.current_exposure,
            "current_total_equity": self.current_total_equity,
            "active_deployment_capital": self.active_deployment_capital,
            "selected_capital_source": self.selected_capital_source,
            "capital_authority_winner": "current_total_equity",
            "capital_fallback_used": self.capital_fallback_used,
            "initial_or_bootstrap_capital": self.initial_or_bootstrap_capital,
            "positions": dict(self.positions),
            "position_market_values": dict(self.position_market_values),
            "current_position_source": self.current_position_source,
        }


@dataclass(frozen=True)
class SubmitFeasibilityResult:
    status: str
    reason: str
    review_required: bool
    halt_required: bool
    evidence: dict[str, Any]

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


def load_runtime_current_exposure(path: Path | str, *, business_date: str = "") -> RuntimeCurrentExposure:
    current_path = Path(path)
    empty = RuntimeCurrentExposure(
        cash=None,
        buying_power=None,
        current_exposure=0.0,
        current_total_equity=None,
        active_deployment_capital=None,
        selected_capital_source="missing_current_state",
        capital_fallback_used=False,
        initial_or_bootstrap_capital=None,
        positions={},
        position_market_values={},
        current_position_source=str(current_path),
        selected_current_source=str(current_path),
        selected_cash_source=str(current_path) + ":cash",
        selected_positions_source=str(current_path) + ":positions",
        selected_valuation_source=str(current_path) + ":positions.market_value",
        current_authority_winner="missing_current_state",
        current_authority_status="REVIEW_REQUIRED",
        current_authority_reason="current_state_missing",
    )
    if not current_path.exists():
        return empty
    try:
        payload = json.loads(current_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return empty
    positions: dict[str, float] = {}
    position_market_values: dict[str, float] = {}
    exposure = 0.0
    for position in payload.get("positions") or ():
        if not isinstance(position, Mapping):
            continue
        symbol = str(position.get("symbol") or position.get("issue_code") or "").strip()
        if not symbol:
            continue
        market_value = _float(position.get("market_value"))
        positions[symbol] = positions.get(symbol, 0.0) + _float(position.get("quantity"))
        position_market_values[symbol] = position_market_values.get(symbol, 0.0) + market_value
        exposure += market_value
    current_business_date = str(
        payload.get("as_of") or payload.get("business_date") or payload.get("position_state_as_of") or ""
    )
    generation = str(payload.get("asset_state_id") or payload.get("generation") or payload.get("created_at") or "")
    future_dated = bool(business_date and current_business_date and current_business_date > business_date)
    source_conflict_detected = bool(payload.get("source_conflict_detected", False))
    cash = None if future_dated else _optional_float(payload.get("cash"))
    buying_power = None if future_dated else _optional_float(payload.get("buying_power"))
    current_total_equity = _optional_float(payload.get("total_equity"))
    selected_source = "current_state.total_equity"
    if future_dated:
        current_total_equity = None
        selected_source = "future_dated_current_rejected"
    elif current_total_equity is None:
        selected_source = "current_state.total_equity_missing"
    projection_payload = payload.get("runtime_owned_projection")
    projection_source = (
        str(projection_payload.get("projection_source") or "")
        if isinstance(projection_payload, Mapping)
        else ""
    )
    return RuntimeCurrentExposure(
        cash=cash,
        buying_power=buying_power,
        current_exposure=exposure,
        current_total_equity=current_total_equity,
        active_deployment_capital=current_total_equity,
        selected_capital_source=selected_source if current_total_equity is not None else "current_state_unavailable",
        capital_fallback_used=False,
        initial_or_bootstrap_capital=_optional_float(payload.get("initial_capital"))
        or _optional_float(payload.get("bootstrap_capital"))
        or _optional_float(payload.get("runtime_evaluation_capital")),
        positions=positions,
        position_market_values=position_market_values,
        current_position_source=str(current_path),
        selected_current_source=str(current_path),
        selected_cash_source=str(current_path) + ":cash",
        selected_positions_source=str(current_path) + ":positions",
        selected_valuation_source=str(current_path) + ":positions.market_value",
        selected_projection_source=projection_source,
        current_authority_winner="persistent_ledger_state",
        current_source_business_date=current_business_date,
        current_source_generation=generation,
        current_authority_status="REVIEW_REQUIRED"
        if future_dated or source_conflict_detected or cash is None or buying_power is None or current_total_equity is None
        else "PASS",
        current_authority_reason="future_dated_current_rejected"
        if future_dated
        else "current_source_conflict_detected"
        if source_conflict_detected
        else "current_total_equity_missing"
        if current_total_equity is None
        else "current_cash_missing"
        if cash is None
        else "current_buying_power_missing"
        if buying_power is None
        else "current_authority_resolved",
        source_conflict_detected=source_conflict_detected,
        source_selection_reason=str(
            payload.get("source_selection_reason") or "explicit_persistent_ledger_state_current_authority"
        ),
        legacy_current_used=False,
        current_fallback_used=False,
        runtime_evaluation_capital_used_as_current=False,
    )


def evaluate_planning_submit_feasibility(
    *,
    items: Sequence[Any],
    policy: CapitalDeploymentPolicy,
    current: RuntimeCurrentExposure,
    authority_source: str = "planning_submit_feasibility_preflight",
    position_count_authority: PositionCountAuthority | None = None,
    cash_exposure_authority: CashExposureAuthority | None = None,
    business_date: str = "",
    runtime_mode: str = "",
) -> SubmitFeasibilityResult:
    reserved_cash = current.cash
    reserved_buying_power = current.buying_power
    reserved_exposure = current.current_exposure
    reserved_positions = dict(current.positions)
    item_evidence = []
    for index, item in enumerate(items):
        side = str(getattr(item, "side", "")).upper()
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
        )
        if side == "BUY":
            item_position_count_authority = _item_position_count_authority(
                position_count_authority=position_count_authority,
                item=item,
                policy=policy,
                current=reserved_current,
                business_date=business_date,
                runtime_mode=runtime_mode,
                authority_source=authority_source,
            )
            item_cash_exposure_authority = _item_cash_exposure_authority(
                cash_exposure_authority=cash_exposure_authority,
                item=item,
                current=reserved_current,
                business_date=business_date,
                runtime_mode=runtime_mode,
                authority_source=authority_source,
            )
            evidence = evaluate_buy_item_submit_feasibility(
                item=item,
                policy=policy,
                current=reserved_current,
                authority_source=authority_source,
                sequence_index=index,
                position_count_authority=item_position_count_authority,
                cash_exposure_authority=item_cash_exposure_authority,
                business_date=business_date,
                runtime_mode=runtime_mode,
            )
            if evidence["status"] == "PASS":
                estimated_amount = _reserved_notional(item)
                symbol = str(getattr(item, "symbol", "")).strip()
                if reserved_cash is not None:
                    reserved_cash = reserved_cash - estimated_amount
                if reserved_buying_power is not None:
                    reserved_buying_power = reserved_buying_power - estimated_amount
                reserved_exposure += estimated_amount
                if symbol:
                    reserved_positions.setdefault(symbol, _float(getattr(item, "quantity", 0.0)))
            item_evidence.append(evidence)
        else:
            item_evidence.append(
                _sell_item_evidence(
                    item=item,
                    policy=policy,
                    current=reserved_current,
                    authority_source=authority_source,
                    sequence_index=index,
                    cash_exposure_authority=cash_exposure_authority,
                    business_date=business_date,
                    runtime_mode=runtime_mode,
                )
            )
    blocked = [item for item in item_evidence if item["status"] != "PASS"]
    evidence = {
        "contract_id": "phase24_ht_planning_submit_feasibility_v1",
        "authority_source": authority_source,
        "reservation_contract": "phase24_id_aggregate_pending_batch_reservation_v1",
        "policy_source": policy.policy_source,
        "policy_version": policy.policy_version,
        "selected_current_source": current.selected_current_source,
        "selected_cash_source": current.selected_cash_source,
        "selected_positions_source": current.selected_positions_source,
        "selected_valuation_source": current.selected_valuation_source,
        "selected_projection_source": current.selected_projection_source,
        "current_authority_winner": current.current_authority_winner,
        "current_source_business_date": current.current_source_business_date,
        "current_source_generation": current.current_source_generation,
        "current_authority_status": current.current_authority_status,
        "current_authority_reason": current.current_authority_reason,
        "source_conflict_detected": current.source_conflict_detected,
        "source_selection_reason": current.source_selection_reason,
        "legacy_current_used": current.legacy_current_used,
        "current_fallback_used": current.current_fallback_used,
        "runtime_evaluation_capital_used_as_current": current.runtime_evaluation_capital_used_as_current,
        "current_position_source": current.current_position_source,
        "selected_capital_source": current.selected_capital_source,
        "selected_capital_value": current.active_deployment_capital,
        "capital_authority_winner": "current_total_equity",
        "active_deployment_capital": current.active_deployment_capital,
        "initial_or_bootstrap_capital": current.initial_or_bootstrap_capital,
        "current_total_equity": current.current_total_equity,
        "legacy_capital_config_used": False,
        "capital_fallback_used": current.capital_fallback_used,
        "current_exposure": current.current_exposure,
        "cash": current.cash,
        "buying_power": current.buying_power,
        "selected_runtime_exposure_limit": None if cash_exposure_authority is None else cash_exposure_authority.selected_runtime_exposure_limit,
        "remaining_exposure": None if cash_exposure_authority is None else cash_exposure_authority.remaining_exposure_capacity,
        "active_max_positions": None if position_count_authority is None else position_count_authority.selected_dynamic_position_count,
        "configured_legacy_max_positions": policy.max_positions,
        "legacy_runtime_max_positions": policy.max_positions,
        "legacy_position_count_config_used": False,
        "position_count_fallback_used": False,
        "starting_position_count": len(current.positions),
        "ending_reserved_cash": reserved_cash,
        "ending_reserved_buying_power": reserved_buying_power,
        "ending_reserved_exposure": reserved_exposure,
        "ending_reserved_position_count": len(reserved_positions),
        "item_count": len(item_evidence),
        "blocked_item_count": len(blocked),
        "items": item_evidence,
    }
    if blocked:
        reason = ";".join(str(item["reason"]) for item in blocked)
        evidence["status"] = "REVIEW_REQUIRED"
        evidence["reason"] = reason
        return SubmitFeasibilityResult(
            status="REVIEW_REQUIRED",
            reason=reason,
            review_required=True,
            halt_required=False,
            evidence=evidence,
        )
    evidence["status"] = "PASS"
    evidence["reason"] = "planning_submit_feasibility_pass"
    return SubmitFeasibilityResult(
        status="PASS",
        reason="planning_submit_feasibility_pass",
        review_required=False,
        halt_required=False,
        evidence=evidence,
    )


def evaluate_buy_item_submit_feasibility(
    *,
    item: Any,
    policy: CapitalDeploymentPolicy,
    current: RuntimeCurrentExposure,
    authority_source: str,
    sequence_index: int | None = None,
    position_count_authority: PositionCountAuthority | None = None,
    cash_exposure_authority: CashExposureAuthority | None = None,
    position_sizing_authority: PositionSizingAuthority | None = None,
    business_date: str = "",
    runtime_mode: str = "",
) -> dict[str, Any]:
    estimated_amount = _float(getattr(item, "estimated_amount", 0.0))
    reservation = _buy_reservation_authority(item)
    reserved_notional = reservation["reserved_notional"]
    symbol = str(getattr(item, "symbol", "")).strip()
    active_capital = current.active_deployment_capital
    current_position_count = len(current.positions)
    creates_new_position = bool(symbol and not contains_symbol_identity(current.positions.keys(), symbol) and reserved_notional > 0)
    resolved_position_count_authority = position_count_authority or _item_position_count_authority(
        position_count_authority=None,
        item=item,
        policy=policy,
        current=current,
        business_date=business_date,
        runtime_mode=runtime_mode,
        authority_source=authority_source,
    )
    resolved_position_count_authority = resolved_position_count_authority.with_current_position_count(current_position_count)
    resolved_cash_exposure_authority = _item_cash_exposure_authority(
        cash_exposure_authority=cash_exposure_authority,
        item=item,
        current=current,
        business_date=business_date,
        runtime_mode=runtime_mode,
        authority_source=authority_source,
    )
    resolved_position_sizing_authority = _item_position_sizing_authority(
        position_sizing_authority=position_sizing_authority,
        item=item,
        current=current,
        business_date=business_date,
        runtime_mode=runtime_mode,
        authority_source=authority_source,
        cash_exposure_authority=resolved_cash_exposure_authority,
        position_count_authority=resolved_position_count_authority,
    )
    post_position_count = current_position_count + (1 if creates_new_position else 0)
    position_count_fields = resolved_position_count_authority.to_dict()
    cash_exposure_fields = resolved_cash_exposure_authority.to_dict()
    position_sizing_fields = resolved_position_sizing_authority.to_dict()
    strategy_executable_notional = _strategy_executable_notional(
        item=item,
        estimated_amount=estimated_amount,
        position_sizing_authority=resolved_position_sizing_authority,
    )
    one_lot_submit_authority = _one_lot_submit_authority(
        item=item,
        symbol=symbol,
        strategy_executable_notional=strategy_executable_notional,
        position_sizing_authority=resolved_position_sizing_authority,
    )
    canonical_discrete_quantity_submit_authority = _canonical_discrete_quantity_submit_authority(
        item=item,
        symbol=symbol,
        position_sizing_authority=resolved_position_sizing_authority,
    )
    evidence = {
        "pending_item_id": str(getattr(item, "pending_item_id", "")),
        "symbol": symbol,
        "side": "BUY",
        "sequence_index": sequence_index,
        "reference_price": reservation["reference_price"],
        "estimated_amount": estimated_amount,
        "strategy_executable_notional": strategy_executable_notional,
        "strategy_sizing_comparison_basis": "strategy_reference_executable_notional",
        "reservation_price": reservation["reservation_price"],
        "reservation_price_authority": reservation["reservation_price_authority"],
        "reservation_reason": reservation["reservation_reason"],
        "reserved_notional": reserved_notional,
        "selected_current_source": current.selected_current_source,
        "selected_cash_source": current.selected_cash_source,
        "selected_positions_source": current.selected_positions_source,
        "selected_valuation_source": current.selected_valuation_source,
        "selected_projection_source": current.selected_projection_source,
        "current_authority_winner": current.current_authority_winner,
        "current_source_business_date": current.current_source_business_date,
        "current_source_generation": current.current_source_generation,
        "current_authority_status": current.current_authority_status,
        "current_authority_reason": current.current_authority_reason,
        "source_conflict_detected": current.source_conflict_detected,
        "source_selection_reason": current.source_selection_reason,
        "legacy_current_used": current.legacy_current_used,
        "current_fallback_used": current.current_fallback_used,
        "runtime_evaluation_capital_used_as_current": current.runtime_evaluation_capital_used_as_current,
        "selected_capital_source": current.selected_capital_source,
        "selected_capital_value": active_capital,
        "capital_authority_winner": "current_total_equity",
        "active_deployment_capital": active_capital,
        "initial_or_bootstrap_capital": current.initial_or_bootstrap_capital,
        "current_total_equity": current.current_total_equity,
        "legacy_capital_config_used": False,
        "capital_fallback_used": current.capital_fallback_used,
        "current_exposure": current.current_exposure,
        "cash": current.cash,
        "buying_power": current.buying_power,
        "selected_runtime_exposure_limit": resolved_cash_exposure_authority.selected_runtime_exposure_limit,
        "remaining_exposure": resolved_cash_exposure_authority.remaining_exposure_capacity,
        "position_sizing_authority": position_sizing_fields,
        **position_sizing_fields,
        "one_lot_submit_authority": one_lot_submit_authority,
        "one_lot_selected_position_overshoot_authorized": one_lot_submit_authority["status"] == "PASS",
        "canonical_discrete_quantity_submit_authority": canonical_discrete_quantity_submit_authority,
        "canonical_discrete_quantity_precedence_applied": canonical_discrete_quantity_submit_authority["status"] == "PASS",
        "active_max_positions": resolved_position_count_authority.selected_dynamic_position_count,
        "configured_legacy_max_positions": policy.max_positions,
        "legacy_runtime_max_positions": policy.max_positions,
        "current_position_count": current_position_count,
        "strategy_requested_position_count": resolved_position_count_authority.strategy_requested_position_count,
        "selected_dynamic_position_count": resolved_position_count_authority.selected_dynamic_position_count,
        "available_position_slots": resolved_position_count_authority.available_position_slots,
        "safety_hard_maximum": resolved_position_count_authority.safety_hard_maximum,
        "position_count_authority_winner": resolved_position_count_authority.position_count_authority_winner,
        "position_count_binding_constraint": resolved_position_count_authority.position_count_binding_constraint,
        "legacy_position_count_config_used": resolved_position_count_authority.legacy_position_count_config_used,
        "position_count_fallback_used": resolved_position_count_authority.position_count_fallback_used,
        "position_count_authority": position_count_fields,
        "cash_exposure_authority": cash_exposure_fields,
        **cash_exposure_fields,
        "creates_new_position": creates_new_position,
        "post_position_count": post_position_count,
        "post_buy_exposure": current.current_exposure + reserved_notional,
        "post_buy_cash": None if current.cash is None else current.cash - reserved_notional,
        "post_buy_buying_power": None
        if current.buying_power is None
        else current.buying_power - reserved_notional,
        "authority_source": authority_source,
        "policy_source": policy.policy_source,
        "policy_version": policy.policy_version,
        "current_position_source": current.current_position_source,
        "status": "PASS",
        "reason": "planning_submit_feasibility_pass",
        "violated_policy": "",
        "violated_policy_source": "",
    }
    violations: list[tuple[str, str, str]] = []
    amount_label = "estimated amount" if abs(reserved_notional - estimated_amount) <= 0.000001 else "reserved notional"
    if current.cash is None:
        violations.append(("cash_missing", "Current cash is missing", current.current_position_source))
    elif reserved_notional > float(current.cash):
        violations.append(("cash", f"{amount_label} exceeds Current cash", current.current_position_source))
    if current.buying_power is None:
        violations.append(("buying_power_missing", "Current buying_power is missing", current.current_position_source))
    elif reserved_notional > float(current.buying_power):
        violations.append(("buying_power", f"{amount_label} exceeds buying_power", current.current_position_source))
    if active_capital is None:
        violations.append(("active_deployment_capital_missing", "Current total equity authority is missing", current.current_position_source))
    if current.current_authority_status != "PASS":
        violations.append(("current_authority", current.current_authority_reason, current.current_position_source))
    if not resolved_cash_exposure_authority.passed:
        violations.append(("dynamic_cash_exposure", resolved_cash_exposure_authority.reason, resolved_cash_exposure_authority.authority_source))
    elif reserved_notional > resolved_cash_exposure_authority.available_cash_after_target:
        violations.append(("dynamic_cash", f"{amount_label} exceeds dynamic cash capacity", resolved_cash_exposure_authority.authority_source))
    elif current.current_exposure + reserved_notional > resolved_cash_exposure_authority.selected_runtime_exposure_limit:
        violations.append(("dynamic_exposure", f"{amount_label} exceeds selected_runtime_exposure_limit", resolved_cash_exposure_authority.authority_source))
    if creates_new_position and not resolved_position_count_authority.passed:
        violations.append(("safety_hard_maximum", resolved_position_count_authority.reason, resolved_position_count_authority.authority_source))
    elif (
        creates_new_position
        and resolved_position_count_authority.safety_hard_maximum is not None
        and post_position_count > resolved_position_count_authority.safety_hard_maximum
    ):
        violations.append(("safety_hard_maximum", "BUY would exceed safety_hard_maximum", resolved_position_count_authority.authority_source))
    if not resolved_position_sizing_authority.passed:
        violations.append(("position_sizing", resolved_position_sizing_authority.reason, resolved_position_sizing_authority.authority_source))
    elif one_lot_submit_authority["status"] == "REVIEW_REQUIRED":
        violations.append(("position_sizing", one_lot_submit_authority["reason"], resolved_position_sizing_authority.authority_source))
    elif canonical_discrete_quantity_submit_authority["status"] == "REVIEW_REQUIRED":
        violations.append(("position_sizing", canonical_discrete_quantity_submit_authority["reason"], resolved_position_sizing_authority.authority_source))
    elif (
        strategy_executable_notional > resolved_position_sizing_authority.selected_position_amount
        and one_lot_submit_authority["status"] != "PASS"
        and canonical_discrete_quantity_submit_authority["status"] != "PASS"
    ):
        strategy_amount_label = (
            "estimated amount"
            if abs(strategy_executable_notional - estimated_amount) <= 0.000001
            else "strategy executable notional"
        )
        violations.append(("position_sizing", f"{strategy_amount_label} exceeds selected_position_amount", resolved_position_sizing_authority.authority_source))
    if policy.max_buy_order_amount is not None and reserved_notional > policy.max_buy_order_amount:
        violations.append(("max_buy_order_amount", f"{amount_label} exceeds max_buy_order_amount", policy.policy_source))
    if reservation["status"] != "PASS":
        violations.append(("reservation_price_authority", reservation["reason"], reservation["authority_source"]))
    if not violations:
        membership_guard = evaluate_precomputable_executable_membership_guard(
            item=item,
            business_date=business_date,
            runtime_mode=runtime_mode,
            runtime_root=current.current_position_source,
        )
        if membership_guard.get("precomputable_executable_membership_guard_status") != "PASS":
            evidence.update(membership_guard)
            return evidence
        return evidence
    policy_name, reason, source = violations[0]
    evidence.update(
        {
            "status": "REVIEW_REQUIRED",
            "reason": reason,
            "violated_policy": policy_name,
            "violated_policy_source": source,
        }
    )
    return evidence


def _sell_item_evidence(
    *,
    item: Any,
    policy: CapitalDeploymentPolicy,
    current: RuntimeCurrentExposure,
    authority_source: str,
    sequence_index: int | None = None,
    cash_exposure_authority: CashExposureAuthority | None = None,
    business_date: str = "",
    runtime_mode: str = "",
) -> dict[str, Any]:
    resolved_cash_exposure_authority = (
        cash_exposure_authority.with_runtime_state(
            current_cash=current.cash,
            current_market_value=current.current_exposure,
            current_total_equity=current.current_total_equity,
            active_deployment_capital=current.active_deployment_capital,
        )
        if cash_exposure_authority is not None
        else None
    )
    cash_exposure_fields = resolved_cash_exposure_authority.to_dict() if resolved_cash_exposure_authority is not None else {}
    evidence = {
        "pending_item_id": str(getattr(item, "pending_item_id", "")),
        "symbol": str(getattr(item, "symbol", "")),
        "side": "SELL",
        "sequence_index": sequence_index,
        "estimated_amount": _float(getattr(item, "estimated_amount", 0.0)),
        "selected_current_source": current.selected_current_source,
        "selected_cash_source": current.selected_cash_source,
        "selected_positions_source": current.selected_positions_source,
        "selected_valuation_source": current.selected_valuation_source,
        "selected_projection_source": current.selected_projection_source,
        "current_authority_winner": current.current_authority_winner,
        "current_source_business_date": current.current_source_business_date,
        "current_source_generation": current.current_source_generation,
        "current_authority_status": current.current_authority_status,
        "current_authority_reason": current.current_authority_reason,
        "source_conflict_detected": current.source_conflict_detected,
        "source_selection_reason": current.source_selection_reason,
        "legacy_current_used": current.legacy_current_used,
        "current_fallback_used": current.current_fallback_used,
        "runtime_evaluation_capital_used_as_current": current.runtime_evaluation_capital_used_as_current,
        "selected_capital_source": current.selected_capital_source,
        "selected_capital_value": current.active_deployment_capital,
        "capital_authority_winner": "current_total_equity",
        "active_deployment_capital": current.active_deployment_capital,
        "initial_or_bootstrap_capital": current.initial_or_bootstrap_capital,
        "current_total_equity": current.current_total_equity,
        "legacy_capital_config_used": False,
        "capital_fallback_used": current.capital_fallback_used,
        "current_exposure": current.current_exposure,
        "selected_runtime_exposure_limit": None if resolved_cash_exposure_authority is None else resolved_cash_exposure_authority.selected_runtime_exposure_limit,
        "remaining_exposure": None if resolved_cash_exposure_authority is None else resolved_cash_exposure_authority.remaining_exposure_capacity,
        **cash_exposure_fields,
        "active_max_positions": None,
        "configured_legacy_max_positions": policy.max_positions,
        "legacy_runtime_max_positions": policy.max_positions,
        "legacy_position_count_config_used": False,
        "position_count_fallback_used": False,
        "current_position_count": len(current.positions),
        "post_position_count": len(current.positions),
        "authority_source": authority_source,
        "policy_source": policy.policy_source,
        "policy_version": policy.policy_version,
        "current_position_source": current.current_position_source,
        "status": "PASS",
        "reason": "sell_exposure_reducing_submit_feasibility_not_blocked_by_buy_dynamic_exposure",
        "violated_policy": "",
        "violated_policy_source": "",
    }
    membership_guard = evaluate_precomputable_executable_membership_guard(
        item=item,
        business_date=business_date,
        runtime_mode=runtime_mode,
        runtime_root=current.current_position_source,
    )
    if membership_guard.get("precomputable_executable_membership_guard_status") != "PASS":
        evidence.update(membership_guard)
    return evidence


def _reserved_notional(item: Any) -> float:
    return _buy_reservation_authority(item)["reserved_notional"]


def _strategy_executable_notional(
    *,
    item: Any,
    estimated_amount: float,
    position_sizing_authority: PositionSizingAuthority,
) -> float:
    if estimated_amount > 0:
        return estimated_amount
    quantity_contract = getattr(item, "quantity_contract", None)
    if isinstance(quantity_contract, Mapping):
        for key in (
            "lot_adjusted_notional",
            "selected_notional",
            "target_notional",
            "incremental_buy_notional",
        ):
            value = _optional_float(quantity_contract.get(key))
            if value is not None and value > 0:
                return value
    if position_sizing_authority.lot_adjusted_notional > 0:
        return position_sizing_authority.lot_adjusted_notional
    return estimated_amount


def _one_lot_submit_authority(
    *,
    item: Any,
    symbol: str,
    strategy_executable_notional: float,
    position_sizing_authority: PositionSizingAuthority,
) -> dict[str, Any]:
    payload = {
        "status": "NOT_APPLICABLE",
        "reason": "",
        "authority_type": "",
        "symbol": symbol,
        "authorized_quantity": position_sizing_authority.discrete_authorized_quantity,
        "authorized_notional": position_sizing_authority.discrete_authorized_notional,
    }
    if not position_sizing_authority.one_lot_authority_consumed:
        return payload
    payload["authority_type"] = "POSITION_SIZING_ONE_LOT_AUTHORITY"
    payload["reason"] = position_sizing_authority.one_lot_authority_reason
    quantity = _float(getattr(item, "quantity", 0.0))
    authorized_quantity = float(position_sizing_authority.discrete_authorized_quantity or 0.0)
    authorized_notional = float(position_sizing_authority.discrete_authorized_notional or 0.0)
    lot_resolution = position_sizing_authority.phase29_l19_lot_resolution or {}
    semantic = str(lot_resolution.get("semantic_type") or "").upper()
    if semantic not in {"BUY_NEW", "REENTRY", "BUY_ADD"}:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "one_lot_authority_semantic_missing_or_invalid"}
    authority = lot_resolution.get("minimum_executable_one_lot_authority")
    if isinstance(authority, Mapping):
        authority_symbol = str(authority.get("symbol") or "").strip()
        authority_intent = str(authority.get("intent") or "").upper()
        if authority_symbol and not contains_symbol_identity((authority_symbol,), symbol):
            return {**payload, "status": "REVIEW_REQUIRED", "reason": "one_lot_authority_symbol_mismatch"}
        if authority_intent and authority_intent != semantic:
            return {**payload, "status": "REVIEW_REQUIRED", "reason": "one_lot_authority_intent_mismatch"}
        if str(authority.get("decision") or "") and str(authority.get("decision") or "") != "ADMIT":
            return {**payload, "status": "REVIEW_REQUIRED", "reason": "one_lot_authority_decision_not_admit"}
    if authorized_quantity <= 0 or abs(quantity - authorized_quantity) > 0.000001:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "one_lot_authority_quantity_mismatch"}
    if authorized_notional <= 0:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "one_lot_authority_notional_missing"}
    tolerance = max(0.01, authorized_notional * 0.000001)
    if abs(strategy_executable_notional - authorized_notional) > tolerance:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "one_lot_authority_notional_mismatch"}
    if lot_resolution.get("safety_hard_cap_preserved") is False:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "one_lot_authority_safety_hard_cap_not_preserved"}
    if lot_resolution.get("strategy_cap_preserved") is False:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "one_lot_authority_strategy_cap_not_preserved"}
    return {**payload, "status": "PASS", "reason": position_sizing_authority.one_lot_authority_reason or "one_lot_authority_consumed"}


_PC_DISCRETE_STRATEGY_SOFT_CAP_OVERSHOOT_REASONS = {
    "LOT_AWARE_STRATEGY_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP",
    "ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP",
    "SECOND_LOT_PLUS_RESIDUAL_CAPITAL_AWARE_PROMOTION",
    "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED",
}
_G102_ITEM_SCOPED_PC_DISCRETE_QUANTITY_REASON = "G102_G97_G99_ITEM_SCOPED_PC_DISCRETE_QUANTITY_AUTHORITY"
_G61_LOT_COMPATIBILITY_SCHEMA_VERSION = "portfolio_construction.lot_aware_allocation_to_sizing_compatibility.v1"


def _pc_discrete_strategy_soft_cap_overshoot_authorized(lot_resolution: Mapping[str, Any]) -> bool:
    reason = str(lot_resolution.get("lot_overshoot_reason") or "")
    if not reason:
        return False
    if reason not in _PC_DISCRETE_STRATEGY_SOFT_CAP_OVERSHOOT_REASONS:
        return False
    if lot_resolution.get("safety_hard_cap_preserved") is False:
        return False
    one_lot_status = str(lot_resolution.get("one_lot_feasibility_status") or "")
    if one_lot_status and one_lot_status != "PASS":
        return False
    if reason == "SECOND_LOT_PLUS_RESIDUAL_CAPITAL_AWARE_PROMOTION":
        promotion = lot_resolution.get("second_lot_plus_promotion")
        if isinstance(promotion, Mapping) and promotion.get("promotion_candidate") is not True:
            return False
        if str(lot_resolution.get("semantic_type") or "").upper() != "BUY_ADD":
            return False
    if reason == "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED":
        authority = lot_resolution.get("minimum_executable_one_lot_authority")
        if isinstance(authority, Mapping):
            decision = str(authority.get("decision") or authority.get("admission_decision") or "")
            if decision and decision not in {"ADMIT", "PASS"}:
                return False
    return True


def _g102_item_scoped_pc_discrete_quantity_authorized(
    *,
    lot_resolution: Mapping[str, Any],
    authority: Mapping[str, Any],
    authorized_quantity: float,
    item_quantity: float,
    ps_final_quantity: float,
) -> bool:
    if str(lot_resolution.get("lot_overshoot_reason") or "") != _G102_ITEM_SCOPED_PC_DISCRETE_QUANTITY_REASON:
        return False
    if str(authority.get("authority_type") or "") != "PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY":
        return False
    if str(authority.get("status") or "") != "PASS":
        return False
    if authority.get("future_information_used") is not False:
        return False
    if authority.get("ps_must_consume_canonical_quantity") is not True:
        return False
    semantic = str(lot_resolution.get("semantic_type") or "").upper()
    if semantic not in {"BUY_NEW", "REENTRY", "BUY_ADD"}:
        return False
    if lot_resolution.get("strategy_cap_preserved") is not True:
        return False
    if lot_resolution.get("safety_hard_cap_preserved") is not True:
        return False
    if str(lot_resolution.get("one_lot_feasibility_status") or "") != "PASS":
        return False
    if authorized_quantity <= 0:
        return False
    for quantity in (item_quantity, ps_final_quantity):
        if abs(quantity - authorized_quantity) > 0.000001:
            return False
    for key in ("final_allocated_quantity", "executable_quantity_delta", "preflight_executable_quantity_delta"):
        quantity = _optional_float(lot_resolution.get(key))
        if quantity is None or abs(quantity - authorized_quantity) > 0.000001:
            return False
    compatibility = lot_resolution.get("lot_aware_allocation_to_sizing_compatibility")
    if not isinstance(compatibility, Mapping):
        return False
    if str(compatibility.get("schema_version") or "") != _G61_LOT_COMPATIBILITY_SCHEMA_VERSION:
        return False
    if str(compatibility.get("owner") or "") != "PORTFOLIO_CONSTRUCTION":
        return False
    if str(compatibility.get("compatibility_state") or "") != "LOT_EXECUTABLE_COMPATIBLE":
        return False
    if compatibility.get("future_information_used") is not False:
        return False
    if compatibility.get("historical_outcome_used") is not False:
        return False
    if compatibility.get("position_sizing_quantity_authority_preserved") is not True:
        return False
    if compatibility.get("pc_quantity_authority") is not False:
        return False
    if _optional_float(compatibility.get("projected_quantity_delta_evidence_only")) != authorized_quantity:
        return False
    trading_unit = _optional_float(compatibility.get("trading_unit"))
    reference_price = _optional_float(compatibility.get("reference_price"))
    portfolio_value = _optional_float(compatibility.get("portfolio_value"))
    if trading_unit is None or trading_unit <= 0:
        return False
    if reference_price is None or reference_price <= 0:
        return False
    if portfolio_value is None or portfolio_value <= 0:
        return False
    return True


def _canonical_discrete_quantity_submit_authority(
    *,
    item: Any,
    symbol: str,
    position_sizing_authority: PositionSizingAuthority,
) -> dict[str, Any]:
    lot_resolution = position_sizing_authority.phase29_l19_lot_resolution or {}
    authority = lot_resolution.get("pc_positive_executable_quantity_authority")
    payload: dict[str, Any] = {
        "status": "NOT_APPLICABLE",
        "reason": "",
        "authority_type": "",
        "symbol": symbol,
        "authorized_quantity": 0.0,
        "item_quantity": _float(getattr(item, "quantity", 0.0)),
        "ps_final_quantity": _float(getattr(item, "quantity", 0.0)),
    }
    if not isinstance(authority, Mapping):
        return payload
    payload["authority_type"] = str(authority.get("authority_type") or "")
    if payload["authority_type"] != "PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY":
        return payload
    payload["reason"] = str(authority.get("reason") or "pc_discrete_quantity_authority_verified")
    if str(authority.get("status") or "") != "PASS":
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "pc_discrete_quantity_authority_not_pass"}
    if authority.get("future_information_used") is not False:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "pc_discrete_quantity_authority_future_information_flag_invalid"}
    if authority.get("ps_must_consume_canonical_quantity") is not True:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "pc_discrete_quantity_authority_ps_consumption_missing"}
    semantic = str(lot_resolution.get("semantic_type") or "").upper()
    if semantic not in {"BUY_NEW", "REENTRY", "BUY_ADD"}:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "pc_discrete_quantity_authority_semantic_missing_or_invalid"}
    authorized_quantity = _buy_add_order_increment_authority_quantity(
        lot_resolution=lot_resolution,
        authority=authority,
        position_sizing_authority=position_sizing_authority,
    ) if semantic == "BUY_ADD" else _float(authority.get("final_allocated_quantity"))
    payload["authorized_quantity"] = authorized_quantity
    payload["quantity_scope"] = "ORDER_INCREMENT" if semantic == "BUY_ADD" else "TARGET_POSITION_OR_ORDER_QUANTITY"
    payload["buy_add_order_increment_authority"] = (
        "pc_positive_executable_quantity_authority.final_allocated_quantity"
        if semantic == "BUY_ADD"
        else ""
    )
    if authorized_quantity <= 0:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "pc_discrete_quantity_authority_quantity_missing"}
    item_quantity = payload["item_quantity"]
    ps_quantity = _optional_float(lot_resolution.get("ps_final_quantity"))
    if ps_quantity is None or ps_quantity <= 0:
        ps_quantity = _optional_float(getattr(position_sizing_authority, "lot_adjusted_quantity", None))
    if ps_quantity is None or ps_quantity <= 0:
        ps_quantity = _optional_float(getattr(position_sizing_authority, "discrete_authorized_quantity", None))
    if ps_quantity is not None and ps_quantity > 0:
        payload["ps_final_quantity"] = ps_quantity
    if abs(item_quantity - authorized_quantity) > 0.000001:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "pc_discrete_quantity_authority_quantity_mismatch"}
    if abs(payload["ps_final_quantity"] - authorized_quantity) > 0.000001:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "pc_discrete_quantity_authority_quantity_mismatch"}
    quantity_keys = ("final_allocated_quantity",) if semantic == "BUY_ADD" else (
        "final_allocated_quantity",
        "executable_quantity_delta",
        "preflight_executable_quantity_delta",
    )
    for key in quantity_keys:
        quantity = _optional_float(lot_resolution.get(key))
        if quantity is not None and abs(quantity - authorized_quantity) > 0.000001:
            return {**payload, "status": "REVIEW_REQUIRED", "reason": "pc_discrete_quantity_authority_quantity_mismatch"}
    lot_quantity = _optional_float(lot_resolution.get("one_lot_quantity"))
    if lot_quantity is not None and lot_quantity > 0:
        quotient = authorized_quantity / lot_quantity
        if abs(quotient - round(quotient)) > 0.000001:
            return {**payload, "status": "REVIEW_REQUIRED", "reason": "pc_discrete_quantity_authority_lot_quantity_invalid"}
    if lot_resolution.get("strategy_cap_preserved") is False:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "pc_discrete_quantity_authority_strategy_cap_not_preserved"}
    if lot_resolution.get("safety_hard_cap_preserved") is False:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "pc_discrete_quantity_authority_safety_hard_cap_not_preserved"}
    strategy_soft_cap_overshoot_authorized = _pc_discrete_strategy_soft_cap_overshoot_authorized(
        lot_resolution
    ) or _g102_item_scoped_pc_discrete_quantity_authorized(
        lot_resolution=lot_resolution,
        authority=authority,
        authorized_quantity=authorized_quantity,
        item_quantity=item_quantity,
        ps_final_quantity=payload["ps_final_quantity"],
    )
    executable_lots = _optional_float(lot_resolution.get("executable_lots"))
    max_strategy_lots = _optional_float(lot_resolution.get("maximum_strategy_feasible_lots"))
    max_safety_lots = _optional_float(lot_resolution.get("maximum_safety_feasible_lots"))
    if (
        executable_lots is not None
        and max_strategy_lots is not None
        and executable_lots > max_strategy_lots
        and not strategy_soft_cap_overshoot_authorized
    ):
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "pc_discrete_quantity_authority_strategy_cap_not_preserved"}
    if executable_lots is not None and max_safety_lots is not None and executable_lots > max_safety_lots:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "pc_discrete_quantity_authority_safety_hard_cap_not_preserved"}
    if str(lot_resolution.get("lot_overshoot_reason") or "") and not strategy_soft_cap_overshoot_authorized:
        return {**payload, "status": "REVIEW_REQUIRED", "reason": "pc_discrete_quantity_authority_lot_overshoot_unresolved"}
    return {**payload, "status": "PASS", "reason": payload["reason"]}


def _buy_add_order_increment_authority_quantity(
    *,
    lot_resolution: Mapping[str, Any],
    authority: Mapping[str, Any],
    position_sizing_authority: PositionSizingAuthority,
) -> float:
    candidates = (
        authority.get("order_increment_quantity"),
        authority.get("authorized_order_increment_quantity"),
        authority.get("final_allocated_quantity"),
        authority.get("discrete_authorized_quantity"),
        getattr(position_sizing_authority, "discrete_authorized_quantity", None),
        getattr(position_sizing_authority, "lot_adjusted_quantity", None),
    )
    for value in candidates:
        quantity = _optional_float(value)
        if quantity is not None and quantity > 0:
            return quantity
    return _float(lot_resolution.get("final_allocated_quantity"))


def _buy_reservation_authority(item: Any) -> dict[str, Any]:
    side = str(getattr(item, "side", "") or "").upper()
    estimated_price = _float(getattr(item, "estimated_price", 0.0))
    estimated_amount = _float(getattr(item, "estimated_amount", 0.0))
    quantity = _float(getattr(item, "quantity", 0.0))
    reference_price = _optional_float(getattr(item, "reference_price", None))
    reservation_price = _optional_float(getattr(item, "reservation_price", None))
    reserved_notional = _optional_float(getattr(item, "reserved_notional", None))
    authority = getattr(item, "reservation_price_authority", None)
    if not isinstance(authority, Mapping):
        authority = {}
    if side != "BUY":
        return {
            "status": "PASS",
            "reason": "reservation_not_required_for_sell",
            "authority_source": "sell_exposure_reducing_item",
            "reference_price": reference_price if reference_price is not None else estimated_price,
            "reservation_price": reservation_price if reservation_price is not None else estimated_price,
            "reservation_price_authority": dict(authority),
            "reservation_reason": str(getattr(item, "reservation_reason", "") or ""),
            "reserved_notional": reserved_notional if reserved_notional is not None else estimated_amount,
        }
    if reserved_notional is None and reservation_price is not None and quantity > 0:
        reserved_notional = round(reservation_price * quantity, 2)
    if reserved_notional is None:
        reserved_notional = estimated_amount
    if reservation_price is None and quantity > 0 and reserved_notional > 0:
        reservation_price = round(reserved_notional / quantity, 8)
    if reservation_price is None:
        reservation_price = estimated_price
    if reference_price is None:
        reference_price = estimated_price
    if not authority:
        authority = {
            "authority_type": "ORDER_CONDITION_DERIVED_RESERVATION_PRICE_AUTHORITY",
            "reservation_price_type": "legacy_estimated_amount_cash_estimate",
            "source_field": "estimated_amount",
            "future_execution_price_used": False,
            "runtime_path": "Production/Demo/Historical common runtime_v2",
            "legacy_fallback_used": True,
        }
    status = "PASS"
    reason = str(getattr(item, "reservation_reason", "") or "reservation_price_authority_resolved")
    if quantity <= 0:
        status = "REVIEW_REQUIRED"
        reason = "BUY reservation quantity missing"
    elif reserved_notional <= 0:
        status = "REVIEW_REQUIRED"
        reason = "BUY reserved notional missing"
    elif reservation_price <= 0:
        status = "REVIEW_REQUIRED"
        reason = "BUY reservation price missing"
    return {
        "status": status,
        "reason": reason,
        "authority_source": str(authority.get("authority_type") or "reservation_price_authority"),
        "reference_price": reference_price,
        "reservation_price": reservation_price,
        "reservation_price_authority": dict(authority),
        "reservation_reason": reason,
        "reserved_notional": reserved_notional,
    }


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _item_position_count_authority(
    *,
    position_count_authority: PositionCountAuthority | None,
    item: Any,
    policy: CapitalDeploymentPolicy,
    current: RuntimeCurrentExposure,
    business_date: str,
    runtime_mode: str,
    authority_source: str,
) -> PositionCountAuthority:
    if position_count_authority is not None:
        return position_count_authority.with_current_position_count(len(current.positions))
    context = getattr(item, "quantity_contract", None)
    if not isinstance(context, Mapping):
        context = {}
    nested = context.get("position_count_authority")
    policy_context = nested if isinstance(nested, Mapping) else context
    return position_count_authority_from_context(
        policy_context,
        business_date=business_date or str(getattr(item, "source_pm_business_date", "") or ""),
        runtime_mode=runtime_mode or "",
        current_position_count=len(current.positions),
        configured_legacy_max_positions=policy.max_positions,
        consumer=authority_source,
    )


def _item_cash_exposure_authority(
    *,
    cash_exposure_authority: CashExposureAuthority | None,
    item: Any,
    current: RuntimeCurrentExposure,
    business_date: str,
    runtime_mode: str,
    authority_source: str,
) -> CashExposureAuthority:
    if cash_exposure_authority is not None:
        return cash_exposure_authority.with_runtime_state(
            current_cash=current.cash,
            current_market_value=current.current_exposure,
            current_total_equity=current.current_total_equity,
            active_deployment_capital=current.active_deployment_capital,
        )
    context = getattr(item, "quantity_contract", None)
    if not isinstance(context, Mapping):
        context = {}
    nested = context.get("cash_exposure_authority")
    policy_context = nested if isinstance(nested, Mapping) else context
    return cash_exposure_authority_from_context(
        policy_context,
        business_date=business_date or str(getattr(item, "source_pm_business_date", "") or ""),
        runtime_mode=runtime_mode or "",
        current_total_equity=current.current_total_equity,
        active_deployment_capital=current.active_deployment_capital,
        current_cash=current.cash,
        current_market_value=current.current_exposure,
        consumer=authority_source,
    )


def _item_position_sizing_authority(
    *,
    position_sizing_authority: PositionSizingAuthority | None,
    item: Any,
    current: RuntimeCurrentExposure,
    business_date: str,
    runtime_mode: str,
    authority_source: str,
    cash_exposure_authority: CashExposureAuthority | None,
    position_count_authority: PositionCountAuthority | None,
) -> PositionSizingAuthority:
    symbol = str(getattr(item, "symbol", "") or "").strip()
    if position_sizing_authority is not None:
        return position_sizing_authority
    context = getattr(item, "quantity_contract", None)
    if not isinstance(context, Mapping):
        context = {}
    nested = context.get("position_sizing_authority")
    policy_context = nested if isinstance(nested, Mapping) else context
    return position_sizing_authority_from_context(
        policy_context,
        symbol=symbol,
        business_date=business_date or str(getattr(item, "source_pm_business_date", "") or ""),
        runtime_mode=runtime_mode or "",
        active_deployment_capital=current.active_deployment_capital,
        selected_dynamic_exposure_ratio=None if cash_exposure_authority is None else cash_exposure_authority.selected_dynamic_exposure_ratio,
        selected_runtime_exposure_limit=None if cash_exposure_authority is None else cash_exposure_authority.selected_runtime_exposure_limit,
        selected_dynamic_position_count=None if position_count_authority is None else position_count_authority.selected_dynamic_position_count,
        current_position_market_value=_current_position_market_value(current, symbol),
        consumer=authority_source,
    )


def _current_position_market_value(current: RuntimeCurrentExposure, symbol: str) -> float:
    for existing_symbol, market_value in current.position_market_values.items():
        if contains_symbol_identity((existing_symbol,), symbol):
            return float(market_value)
    return 0.0
