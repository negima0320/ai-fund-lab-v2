from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal

from ai_fund_lab_v2.safety.models import (
    BrokerPositionState,
    BrokerState,
    OpenOrderState,
    PortfolioPositionState,
    PortfolioState,
    ReconciliationIssue,
    ReconciliationResult,
    ReconciliationSeverity,
    SafetyStatus,
    utc_now_iso,
)

DEFAULT_STALE_SECONDS = 24 * 60 * 60
ACTIVE_ORDER_STATUSES = {"open", "pending", "partial", "partially_filled"}


def reconcile_states(
    portfolio_state: PortfolioState,
    broker_state: BrokerState,
) -> ReconciliationResult:
    issues: list[ReconciliationIssue] = []
    issues.extend(_compare_cash(portfolio_state.cash, broker_state.cash))
    issues.extend(_compare_buying_power(portfolio_state.buying_power, broker_state.buying_power))
    issues.extend(_compare_positions(portfolio_state.positions, broker_state.positions))
    issues.extend(_compare_open_orders(portfolio_state.open_orders, broker_state.open_orders))
    issues.extend(_metadata_warnings(broker_state))
    status = _status_from_issues(issues)
    return ReconciliationResult(status=status, issues=tuple(issues), checked_at=utc_now_iso())


def _compare_cash(portfolio_cash: Decimal, broker_cash: Decimal) -> list[ReconciliationIssue]:
    if portfolio_cash == broker_cash:
        return []
    return [
        ReconciliationIssue(
            code="cash_mismatch",
            severity=ReconciliationSeverity.HALT,
            message="Portfolio cash does not match broker cash.",
            expected=str(broker_cash),
            actual=str(portfolio_cash),
        )
    ]


def _compare_buying_power(portfolio_buying_power: Decimal, broker_buying_power: Decimal) -> list[ReconciliationIssue]:
    if portfolio_buying_power == broker_buying_power:
        return []
    return [
        ReconciliationIssue(
            code="buying_power_mismatch",
            severity=ReconciliationSeverity.HALT,
            message="Portfolio buying power does not match broker buying power.",
            expected=str(broker_buying_power),
            actual=str(portfolio_buying_power),
        )
    ]


def _compare_positions(
    portfolio_positions: tuple[PortfolioPositionState, ...],
    broker_positions: tuple[BrokerPositionState, ...],
) -> list[ReconciliationIssue]:
    issues: list[ReconciliationIssue] = []
    portfolio_by_symbol = {position.symbol: position for position in portfolio_positions}
    broker_by_symbol = {position.symbol: position for position in broker_positions}
    symbols = sorted(set(portfolio_by_symbol) | set(broker_by_symbol))
    for symbol in symbols:
        portfolio_position = portfolio_by_symbol.get(symbol)
        broker_position = broker_by_symbol.get(symbol)
        if portfolio_position is None and broker_position is not None:
            issues.append(
                ReconciliationIssue(
                    code="unknown_position",
                    severity=ReconciliationSeverity.HALT,
                    message="Broker has a position missing from PortfolioState.",
                    symbol=symbol,
                    expected="present in broker",
                    actual="missing in portfolio",
                )
            )
            continue
        if portfolio_position is not None and broker_position is None:
            issues.append(
                ReconciliationIssue(
                    code="position_missing_in_broker",
                    severity=ReconciliationSeverity.HALT,
                    message="PortfolioState has a position missing from broker.",
                    symbol=symbol,
                    expected="present in broker",
                    actual="present in portfolio only",
                )
            )
            continue
        if portfolio_position is None or broker_position is None:
            continue
        issues.extend(_compare_position(symbol, portfolio_position, broker_position))
    return issues


def _compare_position(
    symbol: str,
    portfolio_position: PortfolioPositionState,
    broker_position: BrokerPositionState,
) -> list[ReconciliationIssue]:
    issues: list[ReconciliationIssue] = []
    if portfolio_position.quantity != broker_position.quantity:
        issues.append(
            ReconciliationIssue(
                code="position_quantity_mismatch",
                severity=ReconciliationSeverity.HALT,
                message="Portfolio position quantity does not match broker position quantity.",
                symbol=symbol,
                expected=str(broker_position.quantity),
                actual=str(portfolio_position.quantity),
            )
        )
    if portfolio_position.side != broker_position.side:
        issues.append(
            ReconciliationIssue(
                code="position_side_mismatch",
                severity=ReconciliationSeverity.HALT,
                message="Portfolio position side does not match broker position side.",
                symbol=symbol,
                expected=broker_position.side,
                actual=portfolio_position.side,
            )
        )
    if portfolio_position.account_type != broker_position.account_type:
        issues.append(
            ReconciliationIssue(
                code="position_account_type_mismatch",
                severity=ReconciliationSeverity.HALT,
                message="Portfolio position account type does not match broker position account type.",
                symbol=symbol,
                expected=broker_position.account_type,
                actual=portfolio_position.account_type,
            )
        )
    return issues


def _compare_open_orders(
    portfolio_orders: tuple[OpenOrderState, ...],
    broker_orders: tuple[OpenOrderState, ...],
) -> list[ReconciliationIssue]:
    issues: list[ReconciliationIssue] = []
    duplicate_symbols = _duplicate_open_order_keys(broker_orders)
    for symbol, side in duplicate_symbols:
        issues.append(
            ReconciliationIssue(
                code="duplicate_open_order_suspected",
                severity=ReconciliationSeverity.HALT,
                message="Broker has multiple active open orders for the same symbol and side.",
                symbol=symbol,
                expected="at most one active order",
                actual=side,
            )
        )
    if _order_fingerprint(portfolio_orders) != _order_fingerprint(broker_orders):
        issues.append(
            ReconciliationIssue(
                code="open_order_mismatch",
                severity=ReconciliationSeverity.HALT,
                message="Portfolio open orders do not match broker open orders.",
                expected=str(sorted(_order_fingerprint(broker_orders))),
                actual=str(sorted(_order_fingerprint(portfolio_orders))),
            )
        )
    return issues


def _metadata_warnings(broker_state: BrokerState) -> list[ReconciliationIssue]:
    issues: list[ReconciliationIssue] = []
    if not broker_state.source_snapshot_id:
        issues.append(
            ReconciliationIssue(
                code="broker_snapshot_id_missing",
                severity=ReconciliationSeverity.WARNING,
                message="BrokerState source_snapshot_id is missing.",
            )
        )
    if _is_stale(broker_state.as_of):
        issues.append(
            ReconciliationIssue(
                code="broker_state_stale",
                severity=ReconciliationSeverity.WARNING,
                message="BrokerState as_of is older than the allowed freshness threshold.",
                expected="fresh broker state",
                actual=broker_state.as_of,
            )
        )
    return issues


def _status_from_issues(issues: list[ReconciliationIssue]) -> SafetyStatus:
    if any(issue.severity == ReconciliationSeverity.HALT for issue in issues):
        return SafetyStatus.HALT
    if any(issue.severity == ReconciliationSeverity.WARNING for issue in issues):
        return SafetyStatus.WARNING
    return SafetyStatus.OK


def _order_fingerprint(orders: tuple[OpenOrderState, ...]) -> set[tuple[str, str, str, str, str]]:
    return {(order.order_id, order.symbol, order.side, str(order.quantity), order.status) for order in orders}


def _duplicate_open_order_keys(orders: tuple[OpenOrderState, ...]) -> set[tuple[str, str]]:
    keys = [(order.symbol, order.side) for order in orders if order.status.lower() in ACTIVE_ORDER_STATUSES]
    counts = Counter(keys)
    return {key for key, count in counts.items() if count > 1}


def _is_stale(as_of: str) -> bool:
    try:
        parsed = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    except ValueError:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - parsed).total_seconds() > DEFAULT_STALE_SECONDS
