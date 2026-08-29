"""Project Runtime-owned filled positions into fixed Current SoT."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetPosition, CurrentAssetState
from ai_fund_lab_v2.runtime_v2.asset.writer import write_current_asset_state
from ai_fund_lab_v2.runtime_v2.ledger.performance_events import (
    CanonicalPerformanceExecutionEvent,
    resolve_performance_fills,
)
from ai_fund_lab_v2.runtime_v2.ledger.writer import ledger_record_to_payload

EXECUTION_READONLY_SOURCES = {
    "runtime_v2_execution_readonly",
    "runtime_v2_execution_readonly_simulation",
}
POSITION_QUANTITY_EPSILON = 0.000001


@dataclass(frozen=True)
class RuntimeOwnedFillProjectionResult:
    status: str
    reason: str
    state_path: str
    runtime_owned_symbols: tuple[str, ...]
    excluded_broker_position_symbols: tuple[str, ...]
    projected_positions: tuple[dict[str, Any], ...]
    projected_market_value: float
    projected_cost_basis: float
    projected_cash: float
    projected_buying_power: float
    projected_total_equity: float
    current_sot_before: dict[str, Any]
    current_sot_after: dict[str, Any]
    broker_cash_copied: bool
    unrelated_demo_positions_copied: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def project_runtime_owned_fills_to_current(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    write: bool = True,
    candidate_orders: tuple[object, ...] = (),
    candidate_executions: tuple[object, ...] = (),
    candidate_positions: tuple[object, ...] = (),
) -> RuntimeOwnedFillProjectionResult:
    """Project Runtime-owned filled BUY/SELL positions into Current SoT.

    Demo broker account-wide cash and unrelated reset positions are deliberately
    excluded. The accepted Runtime Submit records define ownership; matching
    Ledger Position records define valuation evidence.
    """

    if mode not in {"demo", "historical", "production"}:
        raise ValueError("runtime-owned fill projection supports demo/historical/production only")
    root = Path(runtime_root)
    _reject_mode_rooted_runtime_root(root)
    ledger_dir = root / "persistent_ledger"
    state_path = ledger_dir / "state.json"
    before = _load_json(state_path)
    submit_orders = _merge_candidate_rows(_load_jsonl(ledger_dir / "orders.jsonl"), candidate_orders)
    ledger_executions = _merge_candidate_rows(_load_jsonl(ledger_dir / "executions.jsonl"), candidate_executions)
    ledger_positions = _merge_candidate_rows(_load_jsonl(ledger_dir / "positions.jsonl"), candidate_positions)

    runtime_owned_symbols = _runtime_owned_broker_symbols(submit_orders)
    if not runtime_owned_symbols:
        return _result(
            status="REVIEW_REQUIRED",
            reason="runtime owned accepted submit evidence missing",
            state_path=state_path,
            runtime_owned_symbols=(),
            excluded=(),
            positions=(),
            before=before,
            after=before,
        )

    latest_positions = _latest_positions_by_symbol(ledger_positions)
    execution_rows = [row for row in ledger_executions if row.get("source") in EXECUTION_READONLY_SOURCES]
    fill_resolution = resolve_performance_fills(executions=execution_rows, orders=submit_orders)
    canonical_events = _runtime_owned_canonical_events(
        fill_resolution.events,
        runtime_owned_symbols=runtime_owned_symbols,
    )
    pending_events = _business_date_pending_events(
        canonical_events=canonical_events,
        current_sot_before=before,
        business_date=business_date,
    )
    quantity_projection = _projected_quantities(
        canonical_events=pending_events,
        latest_positions=latest_positions,
        current_sot_before=before,
        runtime_owned_symbols=runtime_owned_symbols,
        mode=mode,
    )
    cost_projection = _projected_open_costs(
        canonical_events=pending_events,
        runtime_owned_symbols=runtime_owned_symbols,
        current_sot_before=before,
    )
    projection_errors = list(quantity_projection["errors"])
    projection_errors.extend(_current_acquisition_authority_errors(before))
    projection_errors.extend(
        _basis_projection_errors(
            latest_positions=latest_positions,
            current_sot_before=before,
            canonical_events=pending_events,
            projected_quantities=quantity_projection["quantities"],
        )
    )
    if pending_events:
        for symbol, quantity in quantity_projection["quantities"].items():
            cost_quantity = _number((cost_projection.get(symbol) or {}).get("quantity"))
            if abs(quantity - cost_quantity) > POSITION_QUANTITY_EPSILON:
                projection_errors.append(f"runtime_owned_quantity_cost_basis_mismatch:{symbol}")
    if projection_errors:
        return _result(
            status="REVIEW_REQUIRED",
            reason="runtime owned position projection invalid: " + ",".join(projection_errors),
            state_path=state_path,
            runtime_owned_symbols=runtime_owned_symbols,
            excluded=tuple(symbol for symbol in latest_positions if symbol not in runtime_owned_symbols),
            positions=(),
            before=before,
            after=before,
        )
    projected_rows = tuple(
        _projected_position_row(
            symbol=symbol,
            quantity=quantity,
            projected_cost=cost_projection.get(symbol),
            latest_positions=latest_positions,
            business_date=business_date,
            current_sot_before=before,
            canonical_events=pending_events,
        )
        for symbol, quantity in quantity_projection["quantities"].items()
        if quantity > 0
    )
    missing = tuple(
        symbol
        for symbol, quantity in quantity_projection["quantities"].items()
        if quantity > 0 and symbol not in latest_positions
    )
    if missing:
        return _result(
            status="REVIEW_REQUIRED",
            reason="runtime owned position evidence missing: " + ",".join(missing),
            state_path=state_path,
            runtime_owned_symbols=runtime_owned_symbols,
            excluded=tuple(symbol for symbol in latest_positions if symbol not in runtime_owned_symbols),
            positions=(),
            before=before,
            after=before,
        )

    positions = tuple(_current_position(row, business_date=business_date) for row in projected_rows)
    market_value = sum(position.market_value for position in positions)
    cost_basis = sum(position.quantity * position.average_price for position in positions)
    if before.get("cash") in (None, ""):
        return _result(
            status="REVIEW_REQUIRED",
            reason="current cash missing; no runtime_evaluation_capital or initial capital projection fallback",
            state_path=state_path,
            runtime_owned_symbols=runtime_owned_symbols,
            excluded=tuple(symbol for symbol in latest_positions if symbol not in runtime_owned_symbols),
            positions=tuple(_public_position(position) for position in positions),
            before=before,
            after={
                **before,
                "runtime_owned_projection": {
                    "projection_status": "REVIEW_REQUIRED",
                    "projection_source": "runtime_owned_accepted_submit_and_execution_cash_effect",
                    "broker_cash_copied": False,
                    "unrelated_demo_positions_copied": False,
                    "cash_policy": "current_cash_required",
                    "runtime_evaluation_capital_used_as_current": False,
                    "current_fallback_used": False,
                    "legacy_current_used": False,
                },
            },
        )
    starting_cash = _number(before.get("cash"))
    projected_cash = _projected_cash(
        starting_cash=starting_cash,
        cost_basis=cost_basis,
        submit_orders=submit_orders,
        ledger_executions=ledger_executions,
        runtime_owned_symbols=runtime_owned_symbols,
        current_sot_before=before,
        business_date=business_date,
    )
    if projected_cash < -POSITION_QUANTITY_EPSILON:
        after = {
            **before,
            "runtime_owned_projection": {
                "projection_status": "REVIEW_REQUIRED",
                "projection_source": "runtime_owned_accepted_submit_and_execution_cash_effect",
                "broker_cash_copied": False,
                "unrelated_demo_positions_copied": False,
                "cash_policy": "current_cash_plus_runtime_owned_execution_cash_effect",
                "position_policy": "runtime_submit_accepted_and_orderlist_filled_and_ledger_position_matched",
                "raw_projected_cash": projected_cash,
                "runtime_evaluation_capital_used_as_current": False,
                "current_fallback_used": False,
                "legacy_current_used": False,
            },
        }
        return _result(
            status="REVIEW_REQUIRED",
            reason=f"runtime owned cash projection negative: {projected_cash}",
            state_path=state_path,
            runtime_owned_symbols=runtime_owned_symbols,
            excluded=tuple(symbol for symbol in latest_positions if symbol not in runtime_owned_symbols),
            positions=tuple(_public_position(position) for position in positions),
            before=before,
            after=after,
            projected_market_value=market_value,
            projected_cost_basis=cost_basis,
            projected_cash=projected_cash,
            projected_buying_power=projected_cash,
            projected_total_equity=projected_cash + market_value,
        )
    realized_pnl = _projected_realized_pnl(
        submit_orders=submit_orders,
        ledger_executions=ledger_executions,
        runtime_owned_symbols=runtime_owned_symbols,
        current_sot_before=before,
        business_date=business_date,
    )
    projected_buying_power = projected_cash
    projected_total_equity = projected_cash + market_value
    generated_from = tuple(
        str(row.get("record_id") or row.get("ledger_record_id") or "")
        for row in projected_rows
        if row.get("record_id") or row.get("ledger_record_id")
    )
    state = CurrentAssetState(
        schema_version="1",
        asset_state_id=_asset_state_id(
            environment=mode,
            source="runtime_v2_runtime_owned_fill_projection",
            as_of=business_date,
            generated_from=generated_from,
        ),
        environment=mode,
        source="runtime_v2_runtime_owned_fill_projection",
        as_of=business_date,
        positions=positions,
        cash=projected_cash,
        buying_power=projected_buying_power,
        market_value=market_value,
        total_equity=projected_total_equity,
        review_required=False,
        production_equivalent=mode == "production",
        current_state_confirmed_empty=False,
        current_positions_unknown=False,
        cash_unknown=False,
        buying_power_unknown=False,
        generated_from=generated_from,
        created_at=business_date,
    )
    if write:
        write_current_asset_state(state_path, state)
    after = json.loads(
        json.dumps(
            _state_payload_with_metadata(
                state,
                before,
                realized_pnl=realized_pnl,
                applied_events=pending_events,
            ),
            sort_keys=True,
        )
    )
    if write:
        state_path.write_text(json.dumps(after, sort_keys=True), encoding="utf-8")

    excluded = tuple(symbol for symbol in latest_positions if symbol not in runtime_owned_symbols)
    return RuntimeOwnedFillProjectionResult(
        status="PASS",
        reason="runtime_owned_fills_projected_to_current",
        state_path=str(state_path),
        runtime_owned_symbols=runtime_owned_symbols,
        excluded_broker_position_symbols=excluded,
        projected_positions=tuple(_public_position(position) for position in positions),
        projected_market_value=market_value,
        projected_cost_basis=cost_basis,
        projected_cash=projected_cash,
        projected_buying_power=projected_buying_power,
        projected_total_equity=projected_total_equity,
        current_sot_before=before,
        current_sot_after=after,
        broker_cash_copied=False,
        unrelated_demo_positions_copied=False,
    )


def _runtime_owned_broker_symbols(orders: list[dict[str, Any]]) -> tuple[str, ...]:
    symbols: list[str] = []
    for order in orders:
        if order.get("source") != "runtime_v2_submit_pipeline":
            continue
        if str(order.get("status") or "").upper() != "ACCEPTED":
            continue
        normalization = order.get("issue_code_normalization") or {}
        broker_symbol = str(normalization.get("broker_issue_code") or order.get("symbol") or "").strip()
        if broker_symbol and broker_symbol not in symbols:
            symbols.append(broker_symbol)
    return tuple(symbols)


def _latest_positions_by_symbol(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("source") not in EXECUTION_READONLY_SOURCES:
            continue
        symbol = str(row.get("symbol") or "").strip()
        if not symbol:
            continue
        current = latest.get(symbol)
        if current is None or str(row.get("recorded_at") or row.get("as_of") or "") >= str(
            current.get("recorded_at") or current.get("as_of") or ""
        ):
            latest[symbol] = row
    return latest


def _current_position(row: dict[str, Any], *, business_date: str) -> CurrentAssetPosition:
    quantity = _number(row.get("quantity"))
    market_value = _number(row.get("market_value"))
    current_price = _number(row.get("current_price"))
    if current_price <= POSITION_QUANTITY_EPSILON and quantity > POSITION_QUANTITY_EPSILON:
        current_price = market_value / quantity
    return CurrentAssetPosition(
        symbol=str(row.get("symbol") or ""),
        quantity=quantity,
        average_price=_number(row.get("average_price")),
        market_value=market_value,
        source="runtime_v2_runtime_owned_fill_projection",
        as_of=str(row.get("as_of") or row.get("recorded_at") or business_date),
        current_price=current_price if current_price > POSITION_QUANTITY_EPSILON else None,
        quantity_basis=str(row.get("quantity_basis") or ""),
        quantity_basis_provenance=str(row.get("quantity_basis_provenance") or ""),
        valuation_price_basis=str(row.get("valuation_price_basis") or ""),
        valuation_price_role=str(row.get("valuation_price_role") or ""),
        valuation_price_provenance=str(row.get("valuation_price_provenance") or ""),
        valuation_as_of=str(row.get("valuation_as_of") or ""),
        source_market_date=str(row.get("source_market_date") or ""),
        valuation_source=str(row.get("valuation_source") or ""),
        valuation_price_type=str(row.get("valuation_price_type") or ""),
        valuation_quote_status=str(row.get("valuation_quote_status") or ""),
        quote_business_date=str(row.get("quote_business_date") or ""),
        valuation_business_date=str(row.get("valuation_business_date") or ""),
        execution_price_basis=str(row.get("execution_price_basis") or ""),
        fill_price_basis=str(row.get("fill_price_basis") or ""),
        position_campaign_id=str(row.get("position_campaign_id") or ""),
    )


def _projected_quantities(
    *,
    canonical_events: tuple[CanonicalPerformanceExecutionEvent, ...],
    latest_positions: dict[str, dict[str, Any]],
    current_sot_before: dict[str, Any],
    runtime_owned_symbols: tuple[str, ...],
    mode: str,
) -> dict[str, Any]:
    if mode != "historical":
        return {
            "quantities": {
                symbol: _number((latest_positions.get(symbol) or {}).get("quantity"))
                for symbol in runtime_owned_symbols
            },
            "errors": (),
        }
    by_symbol: dict[str, list[CanonicalPerformanceExecutionEvent]] = {symbol: [] for symbol in runtime_owned_symbols}
    for event in sorted(canonical_events, key=lambda item: (item.executed_at, item.canonical_dedup_key)):
        by_symbol.setdefault(event.symbol, []).append(event)
    quantities: dict[str, float] = {}
    errors: list[str] = []
    before_positions = {
        str(item.get("symbol") or "").strip(): item
        for item in current_sot_before.get("positions") or ()
        if str(item.get("symbol") or "").strip()
    }
    for symbol in runtime_owned_symbols:
        events = by_symbol.get(symbol) or []
        has_buy_event = any(event.side.upper() == "BUY" for event in events)
        if symbol in before_positions:
            quantity = _number(before_positions[symbol].get("quantity"))
        elif has_buy_event:
            quantity = 0.0
        elif symbol in latest_positions:
            sell_quantity = sum(event.quantity for event in events if event.side.upper() == "SELL")
            quantity = _number(latest_positions[symbol].get("quantity")) + sell_quantity
        else:
            quantity = 0.0
        for event in events:
            side = event.side.upper()
            if side == "BUY":
                quantity += event.quantity
            elif side == "SELL":
                quantity -= event.quantity
            if quantity < -0.000001:
                errors.append(f"sell_execution_exceeds_runtime_owned_quantity:{symbol}")
                quantity = 0.0
        quantities[symbol] = max(quantity, 0.0)
    return {"quantities": quantities, "errors": tuple(errors)}


def _projected_position_row(
    *,
    symbol: str,
    quantity: float,
    projected_cost: dict[str, float] | None,
    latest_positions: dict[str, dict[str, Any]],
    business_date: str,
    current_sot_before: dict[str, Any],
    canonical_events: tuple[CanonicalPerformanceExecutionEvent, ...],
) -> dict[str, Any]:
    latest = latest_positions.get(symbol) or {}
    latest_quantity = _number(latest.get("quantity"))
    projected_open_cost = _number((projected_cost or {}).get("cost"))
    average_price = (
        projected_open_cost / quantity
        if quantity > POSITION_QUANTITY_EPSILON and projected_open_cost > POSITION_QUANTITY_EPSILON
        else _number(latest.get("average_price"))
    )
    market_price = _number(latest.get("market_value")) / latest_quantity if latest_quantity else average_price
    row = dict(latest)
    row["symbol"] = symbol
    row["position_key"] = row.get("position_key") or symbol
    row["quantity"] = quantity
    row["average_price"] = average_price
    row["market_value"] = quantity * market_price
    row["current_price"] = market_price
    row["as_of"] = row.get("as_of") or row.get("recorded_at") or business_date
    row["position_campaign_id"] = _projected_position_campaign_id(
        symbol=symbol,
        latest_position=latest,
        current_sot_before=current_sot_before,
        canonical_events=canonical_events,
    )
    row.update(
        _position_basis_metadata(
            symbol=symbol,
            latest_position=latest,
            current_sot_before=current_sot_before,
            canonical_events=canonical_events,
        )
    )
    row.update(
        _position_valuation_metadata(
            symbol=symbol,
            latest_position=latest,
            current_sot_before=current_sot_before,
        )
    )
    return row


def _position_basis_metadata(
    *,
    symbol: str,
    latest_position: dict[str, Any],
    current_sot_before: dict[str, Any],
    canonical_events: tuple[CanonicalPerformanceExecutionEvent, ...],
) -> dict[str, str]:
    before_position = _current_position_payload(symbol, current_sot_before=current_sot_before)
    before_basis = _basis_value(before_position)
    latest_basis = _basis_value(latest_position)
    event_basis = _basis_value_from_events(symbol=symbol, canonical_events=canonical_events)
    basis = before_basis or latest_basis or event_basis or "ADJUSTED"
    provenance = (
        _basis_provenance(before_position)
        or _basis_provenance(latest_position)
        or _basis_provenance_from_events(symbol=symbol, canonical_events=canonical_events)
        or "runtime_execution_price_authority:adjusted_reference_price_basis"
    )
    metadata = {
        "quantity_basis": basis,
        "quantity_basis_provenance": provenance,
        "execution_price_basis": event_basis or latest_basis or before_basis or basis,
        "fill_price_basis": event_basis or latest_basis or before_basis or basis,
    }
    valuation_basis = str(before_position.get("valuation_price_basis") or latest_position.get("valuation_price_basis") or "")
    if valuation_basis:
        metadata["valuation_price_basis"] = valuation_basis
    valuation_role = str(before_position.get("valuation_price_role") or latest_position.get("valuation_price_role") or "")
    if valuation_role:
        metadata["valuation_price_role"] = valuation_role
    valuation_provenance = str(
        before_position.get("valuation_price_provenance") or latest_position.get("valuation_price_provenance") or ""
    )
    if valuation_provenance:
        metadata["valuation_price_provenance"] = valuation_provenance
    return metadata


def _current_position_payload(symbol: str, *, current_sot_before: dict[str, Any]) -> dict[str, Any]:
    for row in current_sot_before.get("positions") or ():
        if str(row.get("symbol") or "").strip() == symbol:
            return dict(row)
    return {}


def _basis_value(row: dict[str, Any]) -> str:
    for key in (
        "quantity_basis",
        "position_quantity_basis",
        "fill_price_basis",
        "execution_price_basis",
        "valuation_price_basis",
        "price_basis",
    ):
        value = str(row.get(key) or "").upper()
        if value in {"RAW", "ADJUSTED", "RECONCILED"}:
            return "RAW" if value == "RECONCILED" else value
    return ""


def _basis_provenance(row: dict[str, Any]) -> str:
    for key in (
        "quantity_basis_provenance",
        "position_quantity_basis_provenance",
        "fill_price_basis_provenance",
        "execution_price_basis_provenance",
        "valuation_price_provenance",
        "price_provenance",
    ):
        value = str(row.get(key) or "")
        if value:
            return value
    return ""


def _position_valuation_metadata(
    *,
    symbol: str,
    latest_position: dict[str, Any],
    current_sot_before: dict[str, Any],
) -> dict[str, str]:
    before_position = _current_position_payload(symbol, current_sot_before=current_sot_before)
    metadata: dict[str, str] = {}
    for field in (
        "valuation_as_of",
        "source_market_date",
        "valuation_source",
        "valuation_price_type",
        "valuation_quote_status",
        "quote_business_date",
        "valuation_business_date",
    ):
        value = str(before_position.get(field) or latest_position.get(field) or "")
        if value:
            metadata[field] = value
    if not metadata.get("valuation_as_of"):
        value = str(current_sot_before.get("valuation_as_of") or "")
        if value:
            metadata["valuation_as_of"] = value
    if not metadata.get("source_market_date"):
        value = str(current_sot_before.get("source_market_date") or "")
        if value:
            metadata["source_market_date"] = value
    if not metadata.get("valuation_source"):
        value = str(before_position.get("valuation_price_provenance") or latest_position.get("valuation_price_provenance") or "")
        if value:
            metadata["valuation_source"] = value
    return metadata


def _basis_value_from_events(
    *,
    symbol: str,
    canonical_events: tuple[CanonicalPerformanceExecutionEvent, ...],
) -> str:
    for event in reversed(canonical_events):
        if event.symbol != symbol:
            continue
        value = _basis_value(event.lineage or {})
        if value:
            return value
    return ""


def _basis_provenance_from_events(
    *,
    symbol: str,
    canonical_events: tuple[CanonicalPerformanceExecutionEvent, ...],
) -> str:
    for event in reversed(canonical_events):
        if event.symbol != symbol:
            continue
        value = _basis_provenance(event.lineage or {})
        if value:
            return value
    return ""


def _basis_projection_errors(
    *,
    latest_positions: dict[str, dict[str, Any]],
    current_sot_before: dict[str, Any],
    canonical_events: tuple[CanonicalPerformanceExecutionEvent, ...],
    projected_quantities: dict[str, float],
) -> list[str]:
    errors: list[str] = []
    for symbol, quantity in projected_quantities.items():
        if quantity <= POSITION_QUANTITY_EPSILON:
            continue
        before_basis = _basis_value(_current_position_payload(symbol, current_sot_before=current_sot_before))
        latest_basis = _basis_value(latest_positions.get(symbol) or {})
        event_basis = _basis_value_from_events(symbol=symbol, canonical_events=canonical_events)
        explicit = [basis for basis in (before_basis, latest_basis, event_basis) if basis]
        if len(set(explicit)) > 1:
            errors.append(f"runtime_owned_position_basis_conflict:{symbol}")
    return errors


def _projected_open_costs(
    *,
    canonical_events: tuple[CanonicalPerformanceExecutionEvent, ...],
    runtime_owned_symbols: tuple[str, ...],
    current_sot_before: dict[str, Any],
) -> dict[str, dict[str, float]]:
    positions: dict[str, dict[str, float]] = {
        symbol: _current_open_cost(symbol, current_sot_before=current_sot_before)
        for symbol in runtime_owned_symbols
    }
    rows = sorted(
        _runtime_owned_canonical_events(canonical_events, runtime_owned_symbols=runtime_owned_symbols),
        key=lambda event: (event.executed_at, event.canonical_dedup_key),
    )
    for row in rows:
        symbol = row.symbol
        state = positions.setdefault(symbol, {"quantity": 0.0, "cost": 0.0})
        quantity = row.quantity
        price = row.price
        side = row.side.upper()
        if side == "BUY":
            state["quantity"] += quantity
            state["cost"] += quantity * price
        elif side == "SELL" and quantity > 0:
            average_cost = state["cost"] / state["quantity"] if state["quantity"] > 0 else 0.0
            state["quantity"] = max(state["quantity"] - quantity, 0.0)
            if state["quantity"] <= POSITION_QUANTITY_EPSILON:
                state["quantity"] = 0.0
                state["cost"] = 0.0
            else:
                state["cost"] = max(state["cost"] - average_cost * quantity, 0.0)
    return positions


def _current_open_cost(symbol: str, *, current_sot_before: dict[str, Any]) -> dict[str, float]:
    for row in current_sot_before.get("positions") or ():
        if str(row.get("symbol") or "").strip() != symbol:
            continue
        quantity = _number(row.get("quantity"))
        if quantity <= POSITION_QUANTITY_EPSILON:
            return {"quantity": 0.0, "cost": 0.0}
        cost_basis = _number(row.get("cost_basis"))
        if cost_basis <= POSITION_QUANTITY_EPSILON:
            cost_basis = quantity * _number(row.get("average_price"))
        return {"quantity": quantity, "cost": cost_basis}
    return {"quantity": 0.0, "cost": 0.0}


def _current_acquisition_authority_errors(current_sot_before: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for row in current_sot_before.get("positions") or ():
        symbol = str(row.get("symbol") or "").strip()
        if not symbol:
            continue
        quantity = _number(row.get("quantity"))
        average_price = _number(row.get("average_price"))
        if row.get("cost_basis") in (None, ""):
            continue
        cost_basis = _number(row.get("cost_basis"))
        expected_cost_basis = quantity * average_price
        if abs(cost_basis - expected_cost_basis) > POSITION_QUANTITY_EPSILON:
            errors.append(f"runtime_owned_cost_basis_average_price_mismatch:{symbol}")
    return errors


def _projected_cash(
    *,
    starting_cash: float,
    cost_basis: float,
    submit_orders: list[dict[str, Any]],
    ledger_executions: list[dict[str, Any]],
    runtime_owned_symbols: tuple[str, ...],
    current_sot_before: dict[str, Any],
    business_date: str,
) -> float:
    execution_rows = [row for row in ledger_executions if row.get("source") in EXECUTION_READONLY_SOURCES]
    if not execution_rows:
        return starting_cash - cost_basis
    resolution = resolve_performance_fills(executions=execution_rows, orders=submit_orders)
    canonical_events = _runtime_owned_canonical_events(resolution.events, runtime_owned_symbols=runtime_owned_symbols)
    canonical_events = _business_date_pending_events(
        canonical_events=canonical_events,
        current_sot_before=current_sot_before,
        business_date=business_date,
    )
    if not canonical_events:
        return starting_cash
    cash = starting_cash
    for event in canonical_events:
        amount = event.gross_notional
        side = event.side.upper()
        if side == "BUY":
            cash -= amount
        elif side == "SELL":
            cash += amount
    return cash


def _projected_realized_pnl(
    *,
    submit_orders: list[dict[str, Any]],
    ledger_executions: list[dict[str, Any]],
    runtime_owned_symbols: tuple[str, ...],
    current_sot_before: dict[str, Any],
    business_date: str,
) -> float:
    positions: dict[str, dict[str, float]] = {
        symbol: {"quantity": 0.0, "cost": 0.0}
        for symbol in runtime_owned_symbols
    }
    realized = 0.0
    execution_rows = [row for row in ledger_executions if row.get("source") in EXECUTION_READONLY_SOURCES]
    resolution = resolve_performance_fills(executions=execution_rows, orders=submit_orders)
    canonical_events = _business_date_pending_events(
        canonical_events=_runtime_owned_canonical_events(resolution.events, runtime_owned_symbols=runtime_owned_symbols),
        current_sot_before=current_sot_before,
        business_date=business_date,
    )
    rows = sorted(
        canonical_events,
        key=lambda event: event.executed_at,
    )
    for row in rows:
        symbol = row.symbol
        state = positions.setdefault(symbol, {"quantity": 0.0, "cost": 0.0})
        quantity = row.quantity
        price = row.price
        side = row.side.upper()
        if side == "BUY":
            state["quantity"] += quantity
            state["cost"] += quantity * price
        elif side == "SELL" and quantity > 0:
            average_cost = state["cost"] / state["quantity"] if state["quantity"] > 0 else 0.0
            realized += (price - average_cost) * quantity
            state["quantity"] = max(state["quantity"] - quantity, 0.0)
            state["cost"] = max(state["cost"] - average_cost * quantity, 0.0)
    return realized


def _runtime_owned_canonical_events(
    events: tuple[CanonicalPerformanceExecutionEvent, ...],
    *,
    runtime_owned_symbols: tuple[str, ...],
) -> tuple[CanonicalPerformanceExecutionEvent, ...]:
    return tuple(event for event in events if event.symbol in runtime_owned_symbols)


def _business_date_pending_events(
    *,
    canonical_events: tuple[CanonicalPerformanceExecutionEvent, ...],
    current_sot_before: dict[str, Any],
    business_date: str,
) -> tuple[CanonicalPerformanceExecutionEvent, ...]:
    current_as_of = str(current_sot_before.get("as_of") or current_sot_before.get("business_date") or "").strip()
    applied = _current_applied_execution_keys(current_sot_before)
    current_projection_without_identity = (
        (
            (current_sot_before.get("runtime_owned_projection") or {}).get("projection_status") == "PASS"
            or str(current_sot_before.get("source") or "") == "runtime_v2_runtime_owned_fill_projection"
        )
        and bool(current_sot_before.get("positions") or ())
        and not applied
    )
    pending: list[CanonicalPerformanceExecutionEvent] = []
    for event in canonical_events:
        event_date = str(event.business_date or event.executed_at[:10] or "").strip()
        if not event_date:
            continue
        if event_date > business_date:
            continue
        if _execution_key(event) in applied:
            continue
        if current_as_of and current_as_of <= business_date and event_date < current_as_of:
            continue
        if event_date == current_as_of and current_projection_without_identity:
            continue
        pending.append(event)
    return tuple(pending)


def _current_applied_execution_keys(current_sot_before: dict[str, Any]) -> set[str]:
    projection = current_sot_before.get("runtime_owned_projection") or {}
    raw_values = (
        *(projection.get("applied_execution_ids") or ()),
        *(projection.get("applied_execution_dedup_keys") or ()),
        *(current_sot_before.get("applied_execution_ids") or ()),
        *(current_sot_before.get("applied_execution_dedup_keys") or ()),
        *(current_sot_before.get("execution_references") or ()),
    )
    return {str(value) for value in raw_values if str(value)}


def _execution_key(event: CanonicalPerformanceExecutionEvent) -> str:
    return event.canonical_dedup_key or event.source_execution_id or event.canonical_execution_id


def _state_payload_with_metadata(
    state: CurrentAssetState,
    before: dict[str, Any],
    *,
    realized_pnl: float = 0.0,
    applied_events: tuple[CanonicalPerformanceExecutionEvent, ...] = (),
) -> dict[str, Any]:
    public_positions = [_public_position(position) for position in state.positions or ()]
    unrealized_pnl = sum(_number(position.get("unrealized_pnl")) for position in public_positions)
    payload = {
        "schema_version": state.schema_version,
        "asset_state_id": state.asset_state_id,
        "environment": state.environment,
        "source": state.source,
        "as_of": state.as_of,
        "positions": public_positions,
        "cash": state.cash,
        "buying_power": state.buying_power,
        "market_value": state.market_value,
        "total_equity": state.total_equity,
        "realized_pnl": realized_pnl,
        "new_unrealized_pnl": unrealized_pnl,
        "review_required": state.review_required,
        "production_equivalent": state.production_equivalent,
        "acceptance_only": bool(before.get("acceptance_only", False)) or not state.production_equivalent,
        "simulation": bool(before.get("simulation", False)) or state.environment == "demo" and not state.production_equivalent,
        "current_state_confirmed_empty": state.current_state_confirmed_empty,
        "current_positions_unknown": state.current_positions_unknown,
        "cash_unknown": state.cash_unknown,
        "buying_power_unknown": state.buying_power_unknown,
        "generated_from": list(state.generated_from),
        "created_at": state.created_at,
        "updated_at": state.created_at,
        "cash_confirmed": state.cash is not None,
        "buying_power_confirmed": state.buying_power is not None,
        "initial_or_bootstrap_capital": before.get("initial_capital")
        or before.get("bootstrap_capital")
        or before.get("runtime_evaluation_capital"),
        "runtime_owned_projection": {
            "projection_status": "PASS",
            "projection_source": "runtime_owned_accepted_submit_and_execution_cash_effect",
            "broker_cash_copied": False,
            "unrelated_demo_positions_copied": False,
            "cash_policy": "current_cash_plus_runtime_owned_execution_cash_effect",
            "runtime_evaluation_capital_used_as_current": False,
            "current_fallback_used": False,
            "legacy_current_used": False,
            "position_policy": "runtime_submit_accepted_and_orderlist_filled_and_ledger_position_matched",
            "execution_application_boundary": "identity_after_current_as_of_to_target_business_date",
            "applied_execution_ids": sorted(
                {
                    *(
                        str(value)
                        for value in (before.get("runtime_owned_projection") or {}).get("applied_execution_ids", ())
                        if str(value)
                    ),
                    *(event.source_execution_id for event in applied_events if event.source_execution_id),
                }
            ),
            "applied_execution_dedup_keys": sorted(
                {
                    *(
                        str(value)
                        for value in (before.get("runtime_owned_projection") or {}).get("applied_execution_dedup_keys", ())
                        if str(value)
                    ),
                    *(_execution_key(event) for event in applied_events if _execution_key(event)),
                }
            ),
        },
    }
    return payload


def _public_position(position: CurrentAssetPosition) -> dict[str, Any]:
    cost_basis = position.quantity * position.average_price
    payload = {
        "symbol": position.symbol,
        "quantity": position.quantity,
        "average_price": position.average_price,
        "market_value": position.market_value,
        "cost_basis": cost_basis,
        "unrealized_pnl": position.market_value - cost_basis,
        "source": position.source,
        "as_of": position.as_of,
    }
    if position.current_price is not None:
        payload["current_price"] = position.current_price
    for field in (
        "quantity_basis",
        "quantity_basis_provenance",
        "valuation_price_basis",
        "valuation_price_role",
        "valuation_price_provenance",
        "valuation_as_of",
        "source_market_date",
        "valuation_source",
        "valuation_price_type",
        "valuation_quote_status",
        "quote_business_date",
        "valuation_business_date",
        "execution_price_basis",
        "fill_price_basis",
        "position_campaign_id",
    ):
        value = getattr(position, field)
        if value:
            payload[field] = value
    return payload


def _projected_position_campaign_id(
    *,
    symbol: str,
    latest_position: dict[str, Any],
    current_sot_before: dict[str, Any],
    canonical_events: tuple[CanonicalPerformanceExecutionEvent, ...],
) -> str:
    before_position = _current_position_payload(symbol, current_sot_before=current_sot_before)
    inherited = str(
        before_position.get("position_campaign_id")
        or before_position.get("campaign_id")
        or latest_position.get("position_campaign_id")
        or latest_position.get("campaign_id")
        or ""
    ).strip()
    if inherited:
        return inherited
    quantity = 0.0
    campaign_index = 0
    campaign_id = ""
    for event in sorted(canonical_events, key=lambda item: (item.business_date, item.executed_at, item.canonical_dedup_key)):
        if event.symbol != symbol:
            continue
        side = event.side.upper()
        if side == "BUY":
            if quantity <= POSITION_QUANTITY_EPSILON:
                campaign_index += 1
                campaign_id = _event_campaign_id(event=event, symbol=symbol, sequence=campaign_index)
            quantity += event.quantity
            continue
        if side == "SELL" and quantity > POSITION_QUANTITY_EPSILON:
            quantity = max(quantity - event.quantity, 0.0)
            if quantity <= POSITION_QUANTITY_EPSILON:
                quantity = 0.0
                campaign_id = ""
    return campaign_id


def _event_campaign_id(*, event: CanonicalPerformanceExecutionEvent, symbol: str, sequence: int) -> str:
    existing = str(event.position_campaign_id or event.lineage.get("position_campaign_id") or "").strip()
    if existing and not existing.startswith("ledger-derived-"):
        return existing
    execution_ref = str(event.source_execution_id or event.canonical_dedup_key or event.canonical_execution_id)

    return f"pc-{hashlib.sha256(f'{symbol}|{sequence}|{execution_ref}'.encode('utf-8')).hexdigest()[:16]}-{symbol}-{sequence:04d}"


def _asset_state_id(*, environment: str, source: str, as_of: str, generated_from: tuple[str, ...]) -> str:
    raw = "|".join((environment, source, as_of, *generated_from))
    return "asset-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _merge_candidate_rows(existing_rows: list[dict[str, Any]], candidate_records: tuple[object, ...]) -> list[dict[str, Any]]:
    if not candidate_records:
        return list(existing_rows)
    rows = list(existing_rows)
    existing_dedup = {str(row.get("dedup_key") or "") for row in rows if row.get("dedup_key")}
    for record in candidate_records:
        payload = record if isinstance(record, dict) else ledger_record_to_payload(record)
        dedup_key = str(payload.get("dedup_key") or "")
        if dedup_key and dedup_key in existing_dedup:
            continue
        rows.append(payload)
        if dedup_key:
            existing_dedup.add(dedup_key)
    return rows


def _number(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _result(
    *,
    status: str,
    reason: str,
    state_path: Path,
    runtime_owned_symbols: tuple[str, ...],
    excluded: tuple[str, ...],
    positions: tuple[dict[str, Any], ...],
    before: dict[str, Any],
    after: dict[str, Any],
    projected_market_value: float = 0.0,
    projected_cost_basis: float = 0.0,
    projected_cash: float = 0.0,
    projected_buying_power: float = 0.0,
    projected_total_equity: float = 0.0,
) -> RuntimeOwnedFillProjectionResult:
    return RuntimeOwnedFillProjectionResult(
        status=status,
        reason=reason,
        state_path=str(state_path),
        runtime_owned_symbols=runtime_owned_symbols,
        excluded_broker_position_symbols=excluded,
        projected_positions=positions,
        projected_market_value=projected_market_value,
        projected_cost_basis=projected_cost_basis,
        projected_cash=projected_cash,
        projected_buying_power=projected_buying_power,
        projected_total_equity=projected_total_equity,
        current_sot_before=before,
        current_sot_after=after,
        broker_cash_copied=False,
        unrelated_demo_positions_copied=False,
    )


def _reject_mode_rooted_runtime_root(path: Path) -> None:
    parts = path.parts
    runtime_modes = {"production", "demo", "simulation", "backtest"}
    if any(
        part == ".runtime" and index + 1 < len(parts) and parts[index + 1] in runtime_modes
        for index, part in enumerate(parts)
    ):
        raise ValueError("Runtime-owned projection must use fixed Current path, not mode-rooted path")
