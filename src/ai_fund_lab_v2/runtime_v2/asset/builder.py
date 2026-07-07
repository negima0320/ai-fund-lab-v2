"""Current Asset State builder for Runtime v2."""

from __future__ import annotations

import hashlib
from typing import Sequence

from ai_fund_lab_v2.runtime_v2.asset.models import (
    CurrentAssetPosition,
    CurrentAssetState,
)
from ai_fund_lab_v2.runtime_v2.ledger.models import (
    LedgerCashRecord,
    LedgerPositionRecord,
)


def build_current_asset_state(
    *,
    environment: str,
    positions: Sequence[LedgerPositionRecord] | None,
    cash_records: Sequence[LedgerCashRecord] | None,
    source: str,
    as_of: str,
) -> CurrentAssetState:
    """Build CurrentAssetState from position and cash ledger records."""

    if not environment:
        raise ValueError("environment is required")
    if not source:
        raise ValueError("source is required")
    if not as_of:
        raise ValueError("as_of is required")

    position_items = None
    current_positions_unknown = positions is None
    if positions is not None:
        position_items = tuple(
            CurrentAssetPosition(
                symbol=position.symbol,
                quantity=position.quantity,
                average_price=position.average_price,
                market_value=position.market_value,
                source=position.source,
                as_of=position.as_of or as_of,
            )
            for position in positions
        )

    latest_cash = cash_records[-1] if cash_records else None
    cash_unknown = latest_cash is None
    buying_power_unknown = latest_cash is None
    cash = latest_cash.cash if latest_cash else None
    buying_power = latest_cash.buying_power if latest_cash else None

    market_value = None
    total_equity = None
    if position_items is not None:
        market_value = sum(position.market_value for position in position_items)
    if market_value is not None and cash is not None:
        total_equity = market_value + cash

    production_equivalent = source != "broker_orders_fallback"
    review_required = not production_equivalent
    review_required = review_required or any(
        not position.production_equivalent or position.review_required
        for position in (positions or ())
    )
    review_required = review_required or any(
        not cash_record.production_equivalent or cash_record.review_required
        for cash_record in (cash_records or ())
    )

    confirmed_empty = (
        position_items == ()
        and latest_cash is not None
        and not review_required
        and source != "broker_orders_fallback"
    )

    generated_from = tuple(
        record.record_id for record in (*(positions or ()), *(cash_records or ()))
    )

    return CurrentAssetState(
        schema_version="1",
        asset_state_id=_asset_state_id(environment, source, as_of, generated_from),
        environment=environment,
        source=source,
        as_of=as_of,
        positions=position_items,
        cash=cash,
        buying_power=buying_power,
        market_value=market_value,
        total_equity=total_equity,
        review_required=review_required,
        production_equivalent=production_equivalent,
        current_state_confirmed_empty=confirmed_empty,
        current_positions_unknown=current_positions_unknown,
        cash_unknown=cash_unknown,
        buying_power_unknown=buying_power_unknown,
        generated_from=generated_from,
        created_at=as_of,
    )


def build_current_asset_state_from_orders(*args, **kwargs) -> CurrentAssetState:
    """Reject order-only asset construction."""

    raise ValueError("orders alone cannot build CurrentAssetState")


def _asset_state_id(
    environment: str,
    source: str,
    as_of: str,
    generated_from: tuple[str, ...],
) -> str:
    raw = "|".join((environment, source, as_of, *generated_from))
    return "asset-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

