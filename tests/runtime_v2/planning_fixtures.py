from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetPosition, CurrentAssetState
from ai_fund_lab_v2.runtime_v2.planning.models import (
    AIPlanningSignal,
    CapitalAllocationSignal,
    PlanningInput,
    RuntimeSafetyContext,
)


def make_asset_state(
    *,
    cash=100000.0,
    buying_power=100000.0,
    positions=(),
    current_positions_unknown=False,
    cash_unknown=False,
    buying_power_unknown=False,
    confirmed_empty=False,
) -> CurrentAssetState:
    return CurrentAssetState(
        schema_version="1",
        asset_state_id="asset-1",
        environment="demo",
        source="broker_positions",
        as_of="2026-07-07",
        positions=positions,
        cash=cash,
        buying_power=buying_power,
        market_value=0.0,
        total_equity=cash if cash is not None else None,
        review_required=False,
        production_equivalent=True,
        current_state_confirmed_empty=confirmed_empty,
        current_positions_unknown=current_positions_unknown,
        cash_unknown=cash_unknown,
        buying_power_unknown=buying_power_unknown,
        generated_from=("fixture",),
        created_at="2026-07-07",
    )


def make_ai_signal(symbol="7203", rank=1) -> AIPlanningSignal:
    return AIPlanningSignal(
        signal_id=f"signal-{symbol}",
        symbol=symbol,
        side="BUY",
        rank=rank,
        score=0.9,
        reason="ai fixture",
        source_ai="fixture_ai",
    )


def make_allocation(symbol="7203", cash_required=50000.0) -> CapitalAllocationSignal:
    return CapitalAllocationSignal(
        allocation_id=f"allocation-{symbol}",
        symbol=symbol,
        side="BUY",
        allocated_amount=cash_required,
        max_amount=cash_required,
        cash_required=cash_required,
        reason="allocation fixture",
        estimated_price=2500.0,
        price_source="fixture_close",
        price_as_of="2026-07-07",
        price_confidence="fixture",
        price_required=True,
    )


def make_runtime_safety(decision="ALLOW", review_required=False, block_buy=False, block_sell=False):
    return RuntimeSafetyContext(
        safety_decision_id="safety-fixture",
        safety_policy_version="safety_fixture_v1",
        safety_source="tests.runtime_v2.planning_fixtures",
        safety_decision=decision,
        safety_reason="runtime safety fixture",
        review_required=review_required,
        block_buy=block_buy,
        block_sell=block_sell,
        block_submit=False,
        halt_runtime=decision == "HALT",
        emergency_stop=False,
        generated_at="2026-07-07T00:00:00+09:00",
        expires_at="2026-07-08T00:00:00+09:00",
    )


def make_planning_input(
    *,
    asset_state=None,
    ai_signals=None,
    capital_allocations=None,
    runtime_safety=None,
) -> PlanningInput:
    if asset_state is None:
        asset_state = make_asset_state()
    if ai_signals is None:
        ai_signals = (make_ai_signal(),)
    if capital_allocations is None:
        capital_allocations = (make_allocation(),)
    if runtime_safety is None:
        runtime_safety = make_runtime_safety()
    return PlanningInput(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
        target_session_date="2026-07-08",
        asset_state=asset_state,
        ai_signals=tuple(ai_signals),
        capital_allocations=tuple(capital_allocations),
        runtime_safety=runtime_safety,
    )


def make_position(symbol="7203") -> CurrentAssetPosition:
    return CurrentAssetPosition(
        symbol=symbol,
        quantity=100,
        average_price=2500,
        market_value=250000,
        source="broker_positions",
        as_of="2026-07-07",
    )
