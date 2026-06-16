from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any


class AllocationDecisionLoadError(RuntimeError):
    pass


@dataclass(frozen=True)
class AllocationDecision:
    decision_id: str
    issue_code: str
    side: str
    action: str
    quantity: Decimal
    estimated_price: Decimal
    issue_name: str = ""
    reason_code: str = ""
    replacement_group_id: str = ""

    @property
    def estimated_value(self) -> Decimal:
        return self.quantity * self.estimated_price


@dataclass(frozen=True)
class AllocationDecisionSet:
    policy_id: str
    decisions: tuple[AllocationDecision, ...]
    source_path: str
    cash_buffer_ratio: Decimal = Decimal("0.05")
    max_position_weight: Decimal = Decimal("0.20")
    lot_size: int = 100
    settlement: str = "conservative_T2_cash_unavailable"
    shadow_policies: tuple[str, ...] = ("CAP4", "POLICY_Y_CAP4_EDGE08_CONF5")


def load_allocation_decision_set(path: Path) -> AllocationDecisionSet:
    if not path.exists():
        raise AllocationDecisionLoadError(f"Allocation decision input missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AllocationDecisionLoadError(f"Allocation decision input is invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise AllocationDecisionLoadError("Allocation decision payload must be an object.")
    policy_id = str(payload.get("policy_id") or "CAP5")
    records = payload.get("decisions")
    if not isinstance(records, list):
        raise AllocationDecisionLoadError("Allocation decision payload must contain decisions list.")
    decisions = tuple(_decision(record) for record in records if isinstance(record, dict))
    if len(decisions) != len(records):
        raise AllocationDecisionLoadError("Allocation decisions must all be objects.")
    return AllocationDecisionSet(
        policy_id=policy_id,
        decisions=decisions,
        source_path=str(path),
        cash_buffer_ratio=_decimal(payload.get("cash_buffer_ratio", "0.05")),
        max_position_weight=_decimal(payload.get("max_position_weight", "0.20")),
        lot_size=int(payload.get("lot_size", 100)),
        settlement=str(payload.get("settlement") or "conservative_T2_cash_unavailable"),
        shadow_policies=tuple(str(value) for value in payload.get("shadow_policies", ["CAP4", "POLICY_Y_CAP4_EDGE08_CONF5"])),
    )


def _decision(record: dict[str, Any]) -> AllocationDecision:
    quantity = _decimal(record.get("quantity"))
    if quantity % Decimal("100") != 0:
        raise AllocationDecisionLoadError("Allocation decision quantity must respect 100-share lots.")
    side = str(record.get("side") or record.get("action") or "").upper()
    if side not in {"BUY", "SELL", "HOLD"}:
        raise AllocationDecisionLoadError(f"Unsupported allocation side: {side}")
    return AllocationDecision(
        decision_id=str(record.get("decision_id") or ""),
        issue_code=str(record.get("issue_code") or ""),
        issue_name=str(record.get("issue_name") or ""),
        side=side,
        action=str(record.get("action") or side),
        quantity=quantity,
        estimated_price=_decimal(record.get("estimated_price")),
        reason_code=str(record.get("reason_code") or ""),
        replacement_group_id=str(record.get("replacement_group_id") or ""),
    )


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))

