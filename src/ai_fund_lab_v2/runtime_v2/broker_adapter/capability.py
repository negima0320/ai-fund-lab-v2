"""Broker capability resolution for Runtime v2.

Capabilities are fixed by runtime mode. They are not loaded from user-edited
yaml/json/toml files.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrokerCapability:
    mode: str
    supports_daily_reset: bool
    cash_as_truth: bool
    buying_power_as_truth: bool
    positions_as_truth: bool
    executions_as_truth: bool
    order_status_as_truth: bool
    supports_9000_series_orders: bool
    default_evaluation_capital: float | None
    broker_cash_is_evidence_only: bool
    broker_positions_are_evidence_only_after_reset: bool


def get_broker_capability(mode: str) -> BrokerCapability:
    """Resolve BrokerCapability from runtime mode and fail closed otherwise."""

    if mode == "demo":
        return BrokerCapability(
            mode="demo",
            supports_daily_reset=True,
            cash_as_truth=False,
            buying_power_as_truth=False,
            positions_as_truth=False,
            executions_as_truth=True,
            order_status_as_truth=True,
            supports_9000_series_orders=False,
            default_evaluation_capital=1_000_000.0,
            broker_cash_is_evidence_only=True,
            broker_positions_are_evidence_only_after_reset=True,
        )
    if mode == "production":
        return BrokerCapability(
            mode="production",
            supports_daily_reset=False,
            cash_as_truth=True,
            buying_power_as_truth=True,
            positions_as_truth=True,
            executions_as_truth=True,
            order_status_as_truth=True,
            supports_9000_series_orders=True,
            default_evaluation_capital=None,
            broker_cash_is_evidence_only=False,
            broker_positions_are_evidence_only_after_reset=False,
        )
    if mode == "historical":
        return BrokerCapability(
            mode="historical",
            supports_daily_reset=False,
            cash_as_truth=False,
            buying_power_as_truth=False,
            positions_as_truth=False,
            executions_as_truth=True,
            order_status_as_truth=True,
            supports_9000_series_orders=False,
            default_evaluation_capital=1_000_000.0,
            broker_cash_is_evidence_only=True,
            broker_positions_are_evidence_only_after_reset=True,
        )
    raise ValueError(f"unsupported broker capability mode: {mode}")


def is_9000_series_symbol(symbol: str) -> bool:
    normalized = str(symbol).strip()
    return len(normalized) >= 4 and normalized[:1] == "9"


def is_symbol_allowed_by_capability(symbol: str, capability: BrokerCapability) -> bool:
    if is_9000_series_symbol(symbol) and not capability.supports_9000_series_orders:
        return False
    return True
