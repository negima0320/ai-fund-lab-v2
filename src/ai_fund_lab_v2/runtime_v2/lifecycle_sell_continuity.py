from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SellContinuityDecision:
    status: str
    reason: str
    block_buy: bool
    block_sell: bool
    block_submit: bool
    current_refresh_allowed: bool
    valuation_refresh_allowed: bool
    position_management_allowed: bool
    safety_allowed: bool
    sell_planning_allowed: bool
    sell_submit_authorization_allowed: bool
    allow_current_refresh: bool
    allow_valuation_refresh: bool
    allow_position_management: bool
    allow_safety_evaluation: bool
    allow_sell_planning: bool
    allow_sell_submit_authorization: bool
    buy_planning_permission: str
    buy_submit_permission: str
    sell_planning_permission: str
    sell_submit_authorization_permission: str
    broker_write_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_sell_continuity_from_buy_lifecycle_gate(gate: dict[str, Any]) -> SellContinuityDecision:
    block_buy = bool(gate.get("block_buy") or gate.get("block_buy_planning"))
    block_buy_submit = bool(gate.get("block_buy_submit", gate.get("block_submit")))
    block_sell = bool(gate.get("block_sell") or gate.get("block_sell_planning"))
    block_sell_submit = bool(gate.get("block_sell_submit", False))
    if block_sell:
        return SellContinuityDecision(
            status="BLOCKED",
            reason="ai_lifecycle_gate_blocks_sell",
            block_buy=block_buy,
            block_sell=block_sell,
            block_submit=block_buy_submit,
            current_refresh_allowed=False,
            valuation_refresh_allowed=False,
            position_management_allowed=False,
            safety_allowed=False,
            sell_planning_allowed=False,
            sell_submit_authorization_allowed=False,
            allow_current_refresh=False,
            allow_valuation_refresh=False,
            allow_position_management=False,
            allow_safety_evaluation=False,
            allow_sell_planning=False,
            allow_sell_submit_authorization=False,
            buy_planning_permission="BLOCK" if block_buy else "PASS",
            buy_submit_permission="BLOCK" if block_buy_submit else "PASS",
            sell_planning_permission="BLOCK",
            sell_submit_authorization_permission="BLOCK" if block_sell_submit else "PASS",
        )
    return SellContinuityDecision(
        status="PASS",
        reason="buy_lifecycle_gate_does_not_block_sell_continuity",
        block_buy=block_buy,
        block_sell=False,
        block_submit=block_buy_submit,
        current_refresh_allowed=True,
        valuation_refresh_allowed=True,
        position_management_allowed=True,
        safety_allowed=True,
        sell_planning_allowed=True,
        sell_submit_authorization_allowed=True,
        allow_current_refresh=True,
        allow_valuation_refresh=True,
        allow_position_management=True,
        allow_safety_evaluation=True,
        allow_sell_planning=True,
        allow_sell_submit_authorization=True,
        buy_planning_permission="BLOCK" if block_buy else "PASS",
        buy_submit_permission="BLOCK" if block_buy_submit else "PASS",
        sell_planning_permission="PASS",
        sell_submit_authorization_permission="PASS",
    )
