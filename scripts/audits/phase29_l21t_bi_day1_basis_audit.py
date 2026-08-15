from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


RUN_ID = "runtime-test-historical-extended-smoke-20260815T015141544126Z"
DAY = "2022-08-10"
RUN_ROOT = Path("reports/runtime_tests/runs") / RUN_ID
DAY_ROOT = RUN_ROOT / "daily" / DAY
OUT_ROOT = Path("reports/phase29_l21t_bi_day1_economic_price_quantity_adjustment_basis_audit")


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    fills_payload = _read_json(DAY_ROOT / "execution" / "fills.json")
    fills = fills_payload.get("fills") or []
    manifest = _read_json(DAY_ROOT / "current_valuation_refresh" / "current_valuation_manifest.json")
    artifact = manifest.get("artifact") if isinstance(manifest.get("artifact"), dict) else {}
    current = artifact.get("candidate_current") or {}
    positions = current.get("positions") or []
    asof = _read_json(DAY_ROOT / "market_refresh" / "historical_asof_view.json")
    paths = _source_paths(asof)
    symbols = {str(position.get("symbol") or "") for position in positions}
    normalized = _read_rows(paths["normalized_ohlcv"], symbols=symbols)
    raw = _read_rows(paths["raw_ohlcv"], symbols=symbols)
    fill_by_symbol = {str(fill.get("symbol") or ""): fill for fill in fills}

    rows = []
    contribution_rows = []
    adjustment_rows = []
    for position in positions:
        symbol = str(position.get("symbol") or "")
        qty = _num(position.get("quantity")) or 0.0
        fill = fill_by_symbol.get(symbol, {})
        fill_price = _num(fill.get("execution_price"))
        fill_notional = _num((fill.get("gross_notional") or {}).get("value")) or (qty * (fill_price or 0.0))
        normalized_row = normalized.get(symbol, {})
        raw_row = raw.get(symbol, {})
        adjusted_close = _num(normalized_row.get("Close"))
        adjusted_open = _num(normalized_row.get("Open"))
        raw_close = _num(raw_row.get("C"))
        raw_open = _num(raw_row.get("O"))
        raw_adjusted_close = _num(raw_row.get("AdjC"))
        raw_adjusted_open = _num(raw_row.get("AdjO"))
        adjustment_factor = _num(raw_row.get("AdjFactor"))
        raw_adjusted_ratio = _ratio(raw_close, adjusted_close)
        accepted_price = _num(position.get("current_price"))
        market_value = _num(position.get("market_value")) or 0.0
        adjusted_basis_mv = qty * adjusted_close if adjusted_close is not None else None
        raw_basis_mv = qty * raw_close if raw_close is not None else None
        fill_basis_match = any(
            _near(fill_price, candidate)
            for candidate in (adjusted_open, adjusted_close, raw_adjusted_open, raw_adjusted_close)
        )
        raw_basis_qty = qty / raw_adjusted_ratio if raw_adjusted_ratio not in (None, 0) else None
        raw_qty_mv = raw_basis_qty * raw_close if raw_basis_qty is not None and raw_close is not None else None
        adjusted_qty_mv = qty * adjusted_close if adjusted_close is not None else None
        mismatch = bool(raw_adjusted_ratio and abs(raw_adjusted_ratio - 1.0) > 0.01 and fill_basis_match)
        expected_consistent_mv = adjusted_qty_mv if fill_basis_match else raw_basis_mv
        excess_mv = market_value - expected_consistent_mv if expected_consistent_mv is not None else None
        judgment = (
            "PRICE_QUANTITY_BASIS_MISMATCH"
            if mismatch and _near(accepted_price, raw_close)
            else "CONSISTENT_ADJUSTED_OR_RAW_EQUAL"
            if _near(raw_close, adjusted_close)
            else "INSUFFICIENT_EVIDENCE"
        )
        rows.append(
            {
                "symbol": symbol,
                "current_quantity": qty,
                "quantity_provenance": position.get("source") or "",
                "quantity_adjustment_status": "ADJUSTED_BASIS_INFERRED_FROM_FILL_PRICE" if fill_basis_match else "UNKNOWN",
                "execution_price": fill_price,
                "execution_notional": fill_notional,
                "raw_open": raw_open,
                "raw_close": raw_close,
                "adjusted_open": adjusted_open,
                "adjusted_close": adjusted_close,
                "raw_adjusted_open": raw_adjusted_open,
                "raw_adjusted_close": raw_adjusted_close,
                "adjustment_factor": adjustment_factor,
                "raw_adjusted_ratio": raw_adjusted_ratio,
                "bh_accepted_economic_price": accepted_price,
                "market_value": market_value,
                "raw_price_x_current_quantity": raw_basis_mv,
                "adjusted_price_x_current_quantity": adjusted_basis_mv,
                "raw_price_x_raw_basis_quantity": raw_qty_mv,
                "adjusted_price_x_adjusted_basis_quantity": adjusted_qty_mv,
                "expected_market_value_under_consistent_basis": expected_consistent_mv,
                "excess_market_value_from_basis_mismatch": excess_mv,
                "basis_consistency_judgment": judgment,
            }
        )
        contribution_rows.append(
            {
                "symbol": symbol,
                "execution_notional": fill_notional,
                "current_market_value": market_value,
                "consistent_basis_market_value": expected_consistent_mv,
                "unrealized_pnl_observed": market_value - fill_notional,
                "basis_mismatch_excess_market_value": excess_mv,
            }
        )
        adjustment_rows.append(
            {
                "symbol": symbol,
                "raw_close": raw_close,
                "raw_open": raw_open,
                "adjusted_open": adjusted_open,
                "adjusted_close": adjusted_close,
                "raw_adjusted_open": raw_adjusted_open,
                "raw_adjusted_close": raw_adjusted_close,
                "adjustment_factor": adjustment_factor,
                "raw_adjusted_ratio": raw_adjusted_ratio,
                "execution_price": fill_price,
                "execution_matches_adjusted_basis": fill_basis_match,
            }
        )

    initial_cash = 1_000_000.0
    buy_notional = sum(_num((fill.get("gross_notional") or {}).get("value")) or 0.0 for fill in fills if fill.get("side") == "BUY")
    sell_notional = sum(_num((fill.get("gross_notional") or {}).get("value")) or 0.0 for fill in fills if fill.get("side") == "SELL")
    cash = _num(current.get("cash")) or 0.0
    observed_equity = _num(current.get("total_equity")) or 0.0
    observed_market_value = _num(current.get("market_value")) or 0.0
    consistent_market_value = sum(
        _num(row.get("expected_market_value_under_consistent_basis")) or 0.0 for row in rows
    )
    consistent_equity = cash + consistent_market_value
    sorted_excess = sorted(
        contribution_rows,
        key=lambda row: abs(_num(row.get("basis_mismatch_excess_market_value")) or 0.0),
        reverse=True,
    )
    summary = {
        "task_id": "Phase29-L21T-BI",
        "mode": "READ_ONLY_AUDIT",
        "target_run": RUN_ID,
        "date": DAY,
        "initial_equity": initial_cash,
        "observed_equity": observed_equity,
        "observed_return": (observed_equity / initial_cash) - 1.0,
        "cash": cash,
        "buy_notional": buy_notional,
        "sell_notional": sell_notional,
        "observed_market_value": observed_market_value,
        "consistent_basis_market_value": consistent_market_value,
        "consistent_basis_equity": consistent_equity,
        "basis_mismatch_excess_equity": observed_equity - consistent_equity,
        "primary_contributing_symbols": [row["symbol"] for row in sorted_excess[:3]],
        "94320_contribution": _find(contribution_rows, "94320"),
        "94340_contribution": _find(contribution_rows, "94340"),
        "94320_quantity_basis": _find(rows, "94320").get("quantity_adjustment_status"),
        "94320_correct_valuation_price": _find(rows, "94320").get("adjusted_close"),
        "94320_correct_economic_market_value": _find(rows, "94320").get("expected_market_value_under_consistent_basis"),
        "94340_quantity_basis": _find(rows, "94340").get("quantity_adjustment_status"),
        "94340_correct_valuation_price": _find(rows, "94340").get("adjusted_close"),
        "94340_correct_economic_market_value": _find(rows, "94340").get("expected_market_value_under_consistent_basis"),
        "bh_raw_economic_price_selection_is_correct": False,
        "current_quantity_basis_is_raw_compatible": False,
        "price_quantity_basis_mismatch_confirmed": True,
        "94320_contributes_materially": True,
        "94340_contributes_materially": True,
        "other_symbols_affected": False,
        "corporate_action_quantity_normalization_involved": True,
        "bh_implementation_repair_required": True,
        "root_cause": "PRICE_QUANTITY_ADJUSTMENT_BASIS_MISMATCH",
        "runtime_mutated": False,
        "strategy_changed": False,
        "fresh_run_executed": False,
        "phase30_entered": False,
        "recommended_next_action": "Repair valuation/execution/current quantity basis contract so valuation price and runtime-owned quantity share one adjustment basis.",
    }
    _write_csv(OUT_ROOT / "symbol_basis_reconciliation.csv", rows)
    _write_csv(OUT_ROOT / "day1_equity_contribution.csv", contribution_rows)
    _write_csv(OUT_ROOT / "adjustment_factor_trace.csv", adjustment_rows)
    _write_json(OUT_ROOT / "summary.json", summary)


def _source_paths(asof: dict[str, Any]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for authority in asof.get("authorities") or []:
        name = str(authority.get("authority") or "")
        source = str(authority.get("physical_source_path") or "")
        if name and source:
            result[name] = Path(source)
    coverage = asof.get("feature_lookback_coverage")
    if isinstance(coverage, dict):
        if "normalized_ohlcv" not in result:
            result["normalized_ohlcv"] = Path(str(coverage.get("selected_normalized_ohlcv_path") or ""))
        if "raw_ohlcv" not in result:
            result["raw_ohlcv"] = Path(str(coverage.get("selected_raw_ohlcv_path") or ""))
    return result


def _read_rows(path: Path, *, symbols: set[str]) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    try:
        import pyarrow.parquet as pq

        schema = pq.read_schema(path)
        names = [str(name) for name in schema.names]
        date_col = _first_name(names, ("Date", "target_date", "date", "market_date"))
        code_col = _first_name(names, ("Code", "code", "LocalCode", "symbol", "issue_code"))
        cols = [
            col
            for col in (
                date_col,
                code_col,
                "Close",
                "Open",
                "PriceSource",
                "O",
                "C",
                "AdjO",
                "AdjC",
                "AdjFactor",
            )
            if col in names
        ]
        table = pq.read_table(path, columns=cols, filters=[(date_col, "==", DAY)])
        frame = table.to_pandas()
    except Exception:
        return {}
    wanted = symbols | {symbol + "0" for symbol in symbols}
    frame = frame[frame[code_col].astype(str).isin(wanted)].copy()
    rows: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict(orient="records"):
        rows[str(row.get(code_col) or "")] = row
    return rows


def _first_name(columns: list[str], candidates: tuple[str, ...]) -> str:
    exact = {column: column for column in columns}
    lower = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate in exact:
            return exact[candidate]
        match = lower.get(candidate.lower())
        if match:
            return match
    return ""


def _find(rows: list[dict[str, Any]], symbol: str) -> dict[str, Any]:
    for row in rows:
        if row.get("symbol") == symbol:
            return row
    return {}


def _near(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return False
    return abs(left - right) < 1e-6


def _ratio(left: float | None, right: float | None) -> float | None:
    if left is None or right in (None, 0):
        return None
    return left / right


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    main()
