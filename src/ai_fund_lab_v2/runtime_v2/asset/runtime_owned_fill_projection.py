"""Project Runtime-owned filled positions into fixed Current SoT."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetPosition, CurrentAssetState
from ai_fund_lab_v2.runtime_v2.asset.writer import write_current_asset_state

EXECUTION_READONLY_SOURCES = {
    "runtime_v2_execution_readonly",
    "runtime_v2_execution_readonly_simulation",
}


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
) -> RuntimeOwnedFillProjectionResult:
    """Project Runtime-owned filled BUY/SELL positions into Current SoT.

    Demo broker account-wide cash and unrelated reset positions are deliberately
    excluded. The accepted Runtime Submit records define ownership; matching
    Ledger Position records define valuation evidence.
    """

    if mode not in {"demo", "production"}:
        raise ValueError("runtime-owned fill projection supports demo/production only")
    root = Path(runtime_root)
    _reject_mode_rooted_runtime_root(root)
    ledger_dir = root / "persistent_ledger"
    state_path = ledger_dir / "state.json"
    before = _load_json(state_path)
    submit_orders = _load_jsonl(ledger_dir / "orders.jsonl")
    ledger_executions = _load_jsonl(ledger_dir / "executions.jsonl")
    ledger_positions = _load_jsonl(ledger_dir / "positions.jsonl")

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
    projected_rows = tuple(
        latest_positions[symbol]
        for symbol in runtime_owned_symbols
        if symbol in latest_positions and _number(latest_positions[symbol].get("quantity")) > 0
    )
    missing = tuple(symbol for symbol in runtime_owned_symbols if symbol not in latest_positions)
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
    starting_cash = _number(before.get("runtime_evaluation_capital") or before.get("cash"))
    projected_cash = _projected_cash(
        starting_cash=starting_cash,
        cost_basis=cost_basis,
        ledger_executions=ledger_executions,
        runtime_owned_symbols=runtime_owned_symbols,
    )
    realized_pnl = _projected_realized_pnl(
        ledger_executions=ledger_executions,
        runtime_owned_symbols=runtime_owned_symbols,
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
        production_equivalent=False if mode == "demo" else True,
        current_state_confirmed_empty=False,
        current_positions_unknown=False,
        cash_unknown=False,
        buying_power_unknown=False,
        generated_from=generated_from,
        created_at=business_date,
    )
    if write:
        write_current_asset_state(state_path, state)
    after = json.loads(json.dumps(_state_payload_with_metadata(state, before, realized_pnl=realized_pnl), sort_keys=True))
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
    return CurrentAssetPosition(
        symbol=str(row.get("symbol") or ""),
        quantity=_number(row.get("quantity")),
        average_price=_number(row.get("average_price")),
        market_value=_number(row.get("market_value")),
        source="runtime_v2_runtime_owned_fill_projection",
        as_of=str(row.get("as_of") or row.get("recorded_at") or business_date),
    )


def _projected_cash(
    *,
    starting_cash: float,
    cost_basis: float,
    ledger_executions: list[dict[str, Any]],
    runtime_owned_symbols: tuple[str, ...],
) -> float:
    execution_rows = [
        row
        for row in ledger_executions
        if row.get("source") in EXECUTION_READONLY_SOURCES
        and row.get("execution_evidence_type") == "execution_equivalent"
        and str(row.get("symbol") or "") in runtime_owned_symbols
    ]
    if not execution_rows:
        return max(starting_cash - cost_basis, 0.0)
    cash = starting_cash
    for row in execution_rows:
        amount = _number(row.get("cash_effect"))
        side = str(row.get("side") or "").upper()
        if side == "BUY":
            cash -= amount
        elif side == "SELL":
            cash += amount
    return max(cash, 0.0)


def _projected_realized_pnl(
    *,
    ledger_executions: list[dict[str, Any]],
    runtime_owned_symbols: tuple[str, ...],
) -> float:
    positions: dict[str, dict[str, float]] = {
        symbol: {"quantity": 0.0, "cost": 0.0}
        for symbol in runtime_owned_symbols
    }
    realized = 0.0
    rows = sorted(
        (
            row
            for row in ledger_executions
            if row.get("source") in EXECUTION_READONLY_SOURCES
            and row.get("execution_evidence_type") == "execution_equivalent"
            and str(row.get("symbol") or "") in runtime_owned_symbols
        ),
        key=lambda row: str(row.get("executed_at") or row.get("recorded_at") or row.get("created_at") or ""),
    )
    for row in rows:
        symbol = str(row.get("symbol") or "")
        state = positions.setdefault(symbol, {"quantity": 0.0, "cost": 0.0})
        quantity = _number(row.get("filled_quantity") or row.get("quantity"))
        price = _number(row.get("price") or row.get("average_price"))
        side = str(row.get("side") or "").upper()
        if side == "BUY":
            state["quantity"] += quantity
            state["cost"] += quantity * price
        elif side == "SELL" and quantity > 0:
            average_cost = state["cost"] / state["quantity"] if state["quantity"] > 0 else 0.0
            realized += (price - average_cost) * quantity
            state["quantity"] = max(state["quantity"] - quantity, 0.0)
            state["cost"] = max(state["cost"] - average_cost * quantity, 0.0)
    return realized


def _state_payload_with_metadata(
    state: CurrentAssetState,
    before: dict[str, Any],
    *,
    realized_pnl: float = 0.0,
) -> dict[str, Any]:
    payload = {
        "schema_version": state.schema_version,
        "asset_state_id": state.asset_state_id,
        "environment": state.environment,
        "source": state.source,
        "as_of": state.as_of,
        "positions": [_public_position(position) for position in state.positions or ()],
        "cash": state.cash,
        "buying_power": state.buying_power,
        "market_value": state.market_value,
        "total_equity": state.total_equity,
        "realized_pnl": realized_pnl,
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
        "runtime_evaluation_capital": before.get("runtime_evaluation_capital") or before.get("cash"),
        "runtime_owned_projection": {
            "broker_cash_copied": False,
            "unrelated_demo_positions_copied": False,
            "cash_policy": "runtime_evaluation_capital_plus_runtime_owned_execution_cash_effect",
            "position_policy": "runtime_submit_accepted_and_orderlist_filled_and_ledger_position_matched",
        },
    }
    return payload


def _public_position(position: CurrentAssetPosition) -> dict[str, Any]:
    cost_basis = position.quantity * position.average_price
    return {
        "symbol": position.symbol,
        "quantity": position.quantity,
        "average_price": position.average_price,
        "market_value": position.market_value,
        "cost_basis": cost_basis,
        "unrealized_pnl": position.market_value - cost_basis,
        "source": position.source,
        "as_of": position.as_of,
    }


def _asset_state_id(*, environment: str, source: str, as_of: str, generated_from: tuple[str, ...]) -> str:
    import hashlib

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
) -> RuntimeOwnedFillProjectionResult:
    return RuntimeOwnedFillProjectionResult(
        status=status,
        reason=reason,
        state_path=str(state_path),
        runtime_owned_symbols=runtime_owned_symbols,
        excluded_broker_position_symbols=excluded,
        projected_positions=positions,
        projected_market_value=0.0,
        projected_cost_basis=0.0,
        projected_cash=0.0,
        projected_buying_power=0.0,
        projected_total_equity=0.0,
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
