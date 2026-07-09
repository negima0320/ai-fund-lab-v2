"""Asset reflection policy driven by broker capability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import BrokerCapability
from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerEventRecord


@dataclass(frozen=True)
class AssetReflectionDecision:
    use_broker_cash: bool
    use_broker_buying_power: bool
    use_broker_positions: bool
    review_required: bool
    reason: str
    event: LedgerEventRecord | None = None


def decide_asset_reflection_from_broker_evidence(
    *,
    capability: BrokerCapability,
    runtime_cash: float | None,
    runtime_buying_power: float | None,
    runtime_positions: Sequence[object] | None,
    broker_cash: float | None,
    broker_buying_power: float | None,
    broker_positions: Sequence[object] | None,
    business_date: str,
) -> AssetReflectionDecision:
    """Decide whether broker cash/positions may update Runtime Asset Current."""

    if capability.cash_as_truth and capability.positions_as_truth:
        return AssetReflectionDecision(
            use_broker_cash=True,
            use_broker_buying_power=capability.buying_power_as_truth,
            use_broker_positions=True,
            review_required=False,
            reason="broker evidence is current asset truth",
        )

    if capability.supports_daily_reset:
        reset_like = _looks_like_demo_reset(
            capability=capability,
            runtime_cash=runtime_cash,
            runtime_buying_power=runtime_buying_power,
            runtime_positions=runtime_positions,
            broker_cash=broker_cash,
            broker_buying_power=broker_buying_power,
            broker_positions=broker_positions,
        )
        return AssetReflectionDecision(
            use_broker_cash=False,
            use_broker_buying_power=False,
            use_broker_positions=False,
            review_required=reset_like,
            reason=(
                "demo broker daily reset detected; broker cash/positions are evidence only"
                if reset_like
                else "demo broker cash/positions are evidence only"
            ),
            event=(
                _demo_reset_event(business_date=business_date)
                if reset_like
                else None
            ),
        )

    return AssetReflectionDecision(
        use_broker_cash=False,
        use_broker_buying_power=False,
        use_broker_positions=False,
        review_required=True,
        reason="broker capability does not allow automatic asset reflection",
    )


def apply_broker_cash_policy(
    *,
    capability: BrokerCapability,
    runtime_cash: float,
    runtime_buying_power: float,
    broker_cash: float,
    broker_buying_power: float,
) -> tuple[float, float]:
    """Return the Asset cash/buying power after applying capability policy."""

    if capability.cash_as_truth:
        cash = broker_cash
    else:
        cash = runtime_cash
    if capability.buying_power_as_truth:
        buying_power = broker_buying_power
    else:
        buying_power = runtime_buying_power
    return cash, buying_power


def should_auto_replace_positions_from_broker(
    *,
    capability: BrokerCapability,
    runtime_positions: Sequence[object],
    broker_positions: Sequence[object],
) -> bool:
    """Return whether broker positions may replace Runtime Current positions."""

    if capability.positions_as_truth:
        return True
    if capability.broker_positions_are_evidence_only_after_reset:
        return False
    return False


def _looks_like_demo_reset(
    *,
    capability: BrokerCapability,
    runtime_cash: float | None,
    runtime_buying_power: float | None,
    runtime_positions: Sequence[object] | None,
    broker_cash: float | None,
    broker_buying_power: float | None,
    broker_positions: Sequence[object] | None,
) -> bool:
    if not capability.supports_daily_reset:
        return False
    broker_cash_reset = broker_cash is not None and broker_cash >= 10_000_000
    broker_buying_power_reset = broker_buying_power is not None and broker_buying_power >= 10_000_000
    runtime_cash_differs = runtime_cash is not None and broker_cash is not None and broker_cash != runtime_cash
    runtime_bp_differs = (
        runtime_buying_power is not None
        and broker_buying_power is not None
        and broker_buying_power != runtime_buying_power
    )
    positions_reset = bool(runtime_positions) and not bool(broker_positions)
    return (broker_cash_reset and runtime_cash_differs) or (broker_buying_power_reset and runtime_bp_differs) or positions_reset


def _demo_reset_event(*, business_date: str) -> LedgerEventRecord:
    return LedgerEventRecord(
        record_id=f"ledger-event-phase14e8-demo-reset-{business_date}",
        record_type="event",
        schema_version="1",
        environment="demo",
        source="broker_capability",
        created_at=business_date,
        dedup_key=f"phase14e8:demo-reset:{business_date}",
        review_required=True,
        production_equivalent=False,
        event_id=f"phase14e8-demo-reset-{business_date}",
        event_type="DEMO_BROKER_DAILY_RESET_DETECTED",
        severity="REVIEW_REQUIRED",
        message="Demo broker reset-like cash/position evidence detected; Runtime Current was not auto-reset.",
        related_id="broker_capability",
    )
