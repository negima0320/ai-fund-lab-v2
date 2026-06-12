from __future__ import annotations

from ai_fund_lab_v2.safety.models import BrokerState, PortfolioPositionState, PortfolioState


def build_mock_portfolio_state_from_broker_state(
    broker_state: BrokerState,
) -> PortfolioState:
    return PortfolioState(
        cash=broker_state.cash,
        buying_power=broker_state.buying_power,
        positions=tuple(
            PortfolioPositionState(
                symbol=position.symbol,
                quantity=position.quantity,
                side=position.side,
                account_type=position.account_type,
                average_price=position.average_price,
            )
            for position in broker_state.positions
        ),
        open_orders=broker_state.open_orders,
        as_of=broker_state.as_of,
    )
