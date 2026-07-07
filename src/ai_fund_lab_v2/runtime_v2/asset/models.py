"""Asset Runtime models for Runtime v2."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentAssetPosition:
    symbol: str
    quantity: float
    average_price: float
    market_value: float
    source: str
    as_of: str


@dataclass(frozen=True)
class CurrentAssetState:
    schema_version: str
    asset_state_id: str
    environment: str
    source: str
    as_of: str
    positions: tuple[CurrentAssetPosition, ...] | None
    cash: float | None
    buying_power: float | None
    market_value: float | None
    total_equity: float | None
    review_required: bool
    production_equivalent: bool
    current_state_confirmed_empty: bool
    current_positions_unknown: bool
    cash_unknown: bool
    buying_power_unknown: bool
    generated_from: tuple[str, ...]
    created_at: str

