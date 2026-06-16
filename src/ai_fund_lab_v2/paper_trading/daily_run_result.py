from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from decimal import Decimal
from typing import Any

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping


@dataclass(frozen=True)
class DailyCandidate:
    issue_code: str
    issue_name: str = ""
    side: str = ""
    rank: int | None = None
    planned_quantity: Decimal = Decimal("0")
    planned_amount: Decimal = Decimal("0")
    public_confidence_score: int | None = None
    public_confidence_label: str = ""
    short_reason: str = ""
    caution_note: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class DailyPosition:
    issue_code: str
    issue_name: str = ""
    quantity: Decimal = Decimal("0")
    average_cost: Decimal = Decimal("0")
    market_value: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    holding_days: int = 0

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class DailyRunResult:
    buy_candidates: tuple[DailyCandidate, ...] = ()
    sell_candidates: tuple[DailyCandidate, ...] = ()
    hold_candidates: tuple[DailyCandidate, ...] = ()
    cash: Decimal = Decimal("0")
    current_cash: Decimal = Decimal("0")
    positions: tuple[DailyPosition, ...] = ()
    current_positions: tuple[DailyPosition, ...] = ()
    pending_orders: tuple[dict[str, Any], ...] = ()
    total_equity: Decimal = Decimal("0")
    market_value: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    trade_count: int = 0
    safety_state: dict[str, Any] = field(default_factory=dict)
    review_state: dict[str, Any] = field(default_factory=dict)
    artifact_state: dict[str, Any] = field(default_factory=dict)
    execution_state: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "phase9.daily_run_result.v1"

    def to_dict(self) -> dict[str, Any]:
        return sanitize_mapping(_jsonable(asdict(self)))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value
