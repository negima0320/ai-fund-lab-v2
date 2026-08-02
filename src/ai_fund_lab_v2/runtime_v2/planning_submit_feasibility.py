"""Shared Submit feasibility authority for Planning and Submit evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import CapitalDeploymentPolicy


@dataclass(frozen=True)
class RuntimeCurrentExposure:
    cash: float | None
    buying_power: float | None
    current_exposure: float
    positions: dict[str, float]
    current_position_source: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "cash": self.cash,
            "buying_power": self.buying_power,
            "current_exposure": self.current_exposure,
            "positions": dict(self.positions),
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


def load_runtime_current_exposure(path: Path | str) -> RuntimeCurrentExposure:
    current_path = Path(path)
    empty = RuntimeCurrentExposure(
        cash=None,
        buying_power=None,
        current_exposure=0.0,
        positions={},
        current_position_source=str(current_path),
    )
    if not current_path.exists():
        return empty
    try:
        payload = json.loads(current_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return empty
    positions: dict[str, float] = {}
    exposure = 0.0
    for position in payload.get("positions") or ():
        if not isinstance(position, Mapping):
            continue
        symbol = str(position.get("symbol") or position.get("issue_code") or "").strip()
        if not symbol:
            continue
        positions[symbol] = positions.get(symbol, 0.0) + _float(position.get("quantity"))
        exposure += _float(position.get("market_value"))
    return RuntimeCurrentExposure(
        cash=_optional_float(payload.get("cash")),
        buying_power=_optional_float(payload.get("buying_power")),
        current_exposure=exposure,
        positions=positions,
        current_position_source=str(current_path),
    )


def evaluate_planning_submit_feasibility(
    *,
    items: Sequence[Any],
    policy: CapitalDeploymentPolicy,
    current: RuntimeCurrentExposure,
    authority_source: str = "planning_submit_feasibility_preflight",
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
            positions=reserved_positions,
            current_position_source=current.current_position_source,
        )
        if side == "BUY":
            evidence = evaluate_buy_item_submit_feasibility(
                item=item,
                policy=policy,
                current=reserved_current,
                authority_source=authority_source,
                sequence_index=index,
            )
            if evidence["status"] == "PASS":
                estimated_amount = _float(getattr(item, "estimated_amount", 0.0))
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
                )
            )
    blocked = [item for item in item_evidence if item["status"] != "PASS"]
    evidence = {
        "contract_id": "phase24_ht_planning_submit_feasibility_v1",
        "authority_source": authority_source,
        "reservation_contract": "phase24_id_aggregate_pending_batch_reservation_v1",
        "policy_source": policy.policy_source,
        "policy_version": policy.policy_version,
        "current_position_source": current.current_position_source,
        "current_exposure": current.current_exposure,
        "cash": current.cash,
        "buying_power": current.buying_power,
        "max_exposure": policy.max_exposure,
        "remaining_exposure": policy.max_exposure - current.current_exposure,
        "active_max_positions": policy.max_positions,
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
) -> dict[str, Any]:
    estimated_amount = _float(getattr(item, "estimated_amount", 0.0))
    symbol = str(getattr(item, "symbol", "")).strip()
    max_position_amount = policy.evaluation_capital * policy.max_position_weight
    current_position_count = len(current.positions)
    creates_new_position = bool(symbol and symbol not in current.positions and estimated_amount > 0)
    post_position_count = current_position_count + (1 if creates_new_position else 0)
    evidence = {
        "pending_item_id": str(getattr(item, "pending_item_id", "")),
        "symbol": symbol,
        "side": "BUY",
        "sequence_index": sequence_index,
        "estimated_amount": estimated_amount,
        "current_exposure": current.current_exposure,
        "cash": current.cash,
        "buying_power": current.buying_power,
        "max_exposure": policy.max_exposure,
        "remaining_exposure": policy.max_exposure - current.current_exposure,
        "max_position_amount": max_position_amount,
        "active_max_positions": policy.max_positions,
        "current_position_count": current_position_count,
        "creates_new_position": creates_new_position,
        "post_position_count": post_position_count,
        "post_buy_exposure": current.current_exposure + estimated_amount,
        "post_buy_cash": None if current.cash is None else current.cash - estimated_amount,
        "post_buy_buying_power": None
        if current.buying_power is None
        else current.buying_power - estimated_amount,
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
    if current.cash is None:
        violations.append(("cash_missing", "Current cash is missing", current.current_position_source))
    elif estimated_amount > float(current.cash):
        violations.append(("cash", "estimated amount exceeds Current cash", current.current_position_source))
    if current.buying_power is None:
        violations.append(("buying_power_missing", "Current buying_power is missing", current.current_position_source))
    elif estimated_amount > float(current.buying_power):
        violations.append(("buying_power", "estimated amount exceeds buying_power", current.current_position_source))
    if current.current_exposure + estimated_amount > policy.max_exposure:
        violations.append(("max_exposure", "estimated amount exceeds remaining max_exposure", policy.policy_source))
    if creates_new_position and post_position_count > policy.max_positions:
        violations.append(("max_positions", "BUY would exceed active max_positions", policy.policy_source))
    if estimated_amount > max_position_amount:
        violations.append(("max_position_weight", "estimated amount exceeds max_position_weight", policy.policy_source))
    if policy.max_buy_order_amount is not None and estimated_amount > policy.max_buy_order_amount:
        violations.append(("max_buy_order_amount", "estimated amount exceeds max_buy_order_amount", policy.policy_source))
    if not violations:
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
) -> dict[str, Any]:
    return {
        "pending_item_id": str(getattr(item, "pending_item_id", "")),
        "symbol": str(getattr(item, "symbol", "")),
        "side": "SELL",
        "sequence_index": sequence_index,
        "estimated_amount": _float(getattr(item, "estimated_amount", 0.0)),
        "current_exposure": current.current_exposure,
        "max_exposure": policy.max_exposure,
        "remaining_exposure": policy.max_exposure - current.current_exposure,
        "active_max_positions": policy.max_positions,
        "current_position_count": len(current.positions),
        "post_position_count": len(current.positions),
        "authority_source": authority_source,
        "policy_source": policy.policy_source,
        "policy_version": policy.policy_version,
        "current_position_source": current.current_position_source,
        "status": "PASS",
        "reason": "sell_exposure_reducing_submit_feasibility_not_blocked_by_buy_max_exposure",
        "violated_policy": "",
        "violated_policy_source": "",
    }


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)
