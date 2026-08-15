from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


RUN_ID = "runtime-test-historical-extended-smoke-20260814T131647480030Z"
RUN_ROOT = Path("reports/runtime_tests/runs") / RUN_ID
OUT_ROOT = Path("reports/phase29_l21t_bf_valuation_contamination_scope_trading_state_impact_audit")


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    days = sorted(path.name for path in (RUN_ROOT / "daily").iterdir() if path.is_dir())
    valuation_rows, daily_states = _scan_valuations(days)
    contamination = [row for row in valuation_rows if row["contaminated"]]
    symbol_summary = _symbol_summary(contamination)
    propagation = _scan_propagation(days, daily_states, contamination)
    validity = _performance_validity(contamination, propagation)
    recovery = _recovery_boundary(contamination)
    summary = _summary(days, valuation_rows, contamination, symbol_summary, propagation, validity, recovery)

    _write_csv(OUT_ROOT / "contamination_events.csv", contamination)
    _write_csv(OUT_ROOT / "contaminated_symbols.csv", symbol_summary)
    _write_csv(OUT_ROOT / "trading_state_propagation.csv", propagation)
    _write_csv(OUT_ROOT / "performance_evidence_validity.csv", validity)
    _write_csv(OUT_ROOT / "recovery_boundary.csv", recovery)
    _write_json(OUT_ROOT / "summary.json", summary)


def _scan_valuations(days: list[str]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    daily_states: dict[str, dict[str, Any]] = {}
    previous_price_by_symbol: dict[str, float] = {}
    previous_mv_by_symbol: dict[str, float] = {}
    for day in days:
        manifest_path = RUN_ROOT / "daily" / day / "current_valuation_refresh" / "current_valuation_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = _read_json(manifest_path)
        artifact = manifest.get("artifact") if isinstance(manifest.get("artifact"), dict) else manifest
        current = artifact.get("candidate_current") if isinstance(artifact.get("candidate_current"), dict) else {}
        positions = current.get("positions") if isinstance(current.get("positions"), list) else []
        daily_states[day] = {
            "cash": _num(current.get("cash")),
            "buying_power": _num(current.get("buying_power")),
            "market_value": _num(current.get("market_value")),
            "total_equity": _num(current.get("total_equity")),
            "position_count": len(positions),
        }
        source_cache: dict[str, dict[str, dict[str, Any]]] = {}
        required_symbols = {str(position.get("symbol") or "") for position in positions if position.get("symbol")}
        for position in positions:
            symbol = str(position.get("symbol") or "")
            quantity = _num(position.get("quantity"))
            price = _num(position.get("current_price"))
            market_value = _num(position.get("market_value"))
            source = str(position.get("valuation_source") or "")
            source_row = _source_row(source_cache, source, day, symbol, required_symbols)
            price_source = str(source_row.get("PriceSource") or source_row.get("price_source") or "")
            reconciliation_status = str(
                position.get("valuation_price_authority")
                or position.get("economic_price_reconciliation_status")
                or source_row.get("economic_price_reconciliation_status")
                or source_row.get("EconomicPriceReconciliationStatus")
                or ""
            )
            economic_price = source_row.get("economic_valuation_price", source_row.get("EconomicValuationPrice"))
            provenance = str(
                position.get("valuation_price_provenance")
                or source_row.get("economic_price_provenance")
                or source_row.get("EconomicPriceProvenance")
                or ""
            )
            adjusted_consumed = price_source.lower() == "adjusted" or bool(position.get("valuation_adjusted"))
            reconciled = reconciliation_status == "PASS" and provenance and _positive_num(economic_price) is not None
            contaminated = bool(adjusted_consumed and not reconciled)
            previous_price = previous_price_by_symbol.get(symbol)
            previous_mv = previous_mv_by_symbol.get(symbol)
            price_delta = None if previous_price is None or price is None else price - previous_price
            mv_delta = None if previous_mv is None or market_value is None else market_value - previous_mv
            estimated_false = mv_delta if contaminated and _is_suspicious_step(previous_price, price, quantity) else 0.0
            rows.append(
                {
                    "date": day,
                    "symbol": symbol,
                    "quantity": quantity,
                    "previous_price": previous_price,
                    "applied_valuation_price": price,
                    "price_change": price_delta,
                    "previous_market_value": previous_mv,
                    "current_market_value": market_value,
                    "market_value_delta": mv_delta,
                    "adjusted_flag_position": bool(position.get("valuation_adjusted")),
                    "source_price_source": price_source,
                    "source_close": source_row.get("Close", source_row.get("close")),
                    "source_open": source_row.get("Open", source_row.get("open")),
                    "source_high": source_row.get("High", source_row.get("high")),
                    "source_low": source_row.get("Low", source_row.get("low")),
                    "provenance": provenance,
                    "reconciliation_status": reconciliation_status,
                    "economic_valuation_price": economic_price,
                    "contaminated": contaminated,
                    "suspicious_alternating_or_exact_step": _is_suspicious_step(previous_price, price, quantity),
                    "estimated_false_pnl_contribution": estimated_false,
                    "valuation_source": source,
                }
            )
            if price is not None:
                previous_price_by_symbol[symbol] = price
            if market_value is not None:
                previous_mv_by_symbol[symbol] = market_value
    return rows, daily_states


def _source_row(
    cache: dict[str, dict[str, dict[str, Any]]],
    source: str,
    day: str,
    symbol: str,
    required_symbols: set[str],
) -> dict[str, Any]:
    if not source:
        return {}
    if source not in cache:
        cache[source] = _read_parquet_by_day_symbol(Path(source), day=day, required_symbols=required_symbols)
    return cache[source].get(f"{day}|{symbol}") or cache[source].get(f"{day}|{symbol}0") or {}


def _read_parquet_by_day_symbol(path: Path, *, day: str, required_symbols: set[str]) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    try:
        import pyarrow.parquet as pq

        schema = pq.read_schema(path)
        names = [str(name) for name in schema.names]
        date_col = _first_name(names, ("target_date", "Date", "date", "market_date"))
        code_col = _first_name(names, ("code", "Code", "LocalCode", "symbol", "issue_code"))
        if not date_col or not code_col:
            return {}
        wanted = [
            column
            for column in (
                date_col,
                code_col,
                "Open",
                "High",
                "Low",
                "Close",
                "open",
                "high",
                "low",
                "close",
                "PriceSource",
                "price_source",
                "economic_price_reconciliation_status",
                "EconomicPriceReconciliationStatus",
                "economic_price_provenance",
                "EconomicPriceProvenance",
                "economic_valuation_price",
                "EconomicValuationPrice",
            )
            if column in names
        ]
        filters: list[tuple[str, str, Any]] = [(date_col, "==", day)]
        table = pq.read_table(path, columns=wanted, filters=filters)
        frame = table.to_pandas()
    except Exception:
        return {}
    if frame.empty:
        return {}
    if required_symbols:
        symbols = {symbol for item in required_symbols for symbol in (item, item + "0")}
        frame = frame[frame[code_col].astype(str).isin(symbols)].copy()
    result: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict(orient="records"):
        result[f"{row.get(date_col)}|{row.get(code_col)}"] = row
    return result


def _symbol_summary(contamination: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in contamination:
        by_symbol[str(row["symbol"])].append(row)
    result = []
    for symbol, rows in sorted(by_symbol.items()):
        false_values = [_num(row.get("estimated_false_pnl_contribution")) or 0.0 for row in rows]
        result.append(
            {
                "symbol": symbol,
                "contaminated_days": len({row["date"] for row in rows}),
                "first_date": min(str(row["date"]) for row in rows),
                "last_date": max(str(row["date"]) for row in rows),
                "gross_estimated_false_pnl": sum(abs(value) for value in false_values),
                "net_estimated_false_pnl": sum(false_values),
                "max_abs_estimated_false_pnl": max([abs(value) for value in false_values] or [0.0]),
                "suspicious_step_days": sum(1 for row in rows if row.get("suspicious_alternating_or_exact_step")),
            }
        )
    return result


def _scan_propagation(
    days: list[str],
    daily_states: dict[str, dict[str, Any]],
    contamination: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    contaminated_dates = {str(row["date"]) for row in contamination}
    earliest = min(contaminated_dates) if contaminated_dates else ""
    rows: list[dict[str, Any]] = []
    contaminated_seen_before_day = False
    for day in days:
        strategy_dir = RUN_ROOT / "daily" / day / "strategy"
        ps = _read_json_optional(strategy_dir / "position_sizing.json")
        pc = _read_json_optional(strategy_dir / "portfolio_construction.json")
        rp = _read_json_optional(strategy_dir / "runtime_planning.json")
        morning = _read_json_optional(RUN_ROOT / "daily" / day / "morning" / "planning_evidence.json")
        fills_payload = _read_json_optional_or_list(RUN_ROOT / "daily" / day / "execution" / "fills.json")
        fills = fills_payload if isinstance(fills_payload, list) else fills_payload.get("fills", [])
        plans = rp.get("plans") if isinstance(rp.get("plans"), list) else []
        ps_positions = ps.get("positions") if isinstance(ps.get("positions"), list) else []
        pc_members = pc.get("portfolio_members") if isinstance(pc.get("portfolio_members"), list) else []
        action_counts = Counter(str(plan.get("action") or plan.get("side") or plan.get("semantic_type") or "") for plan in plans)
        positive_plans = [
            plan
            for plan in plans
            if (
                _num(plan.get("planned_quantity"))
                or _num(plan.get("quantity_delta_candidate"))
                or _num(plan.get("target_quantity_candidate"))
                or 0.0
            )
            > 0
        ]
        buy_fills = [fill for fill in fills if str(fill.get("side") or "").upper() == "BUY"]
        sell_fills = [fill for fill in fills if str(fill.get("side") or "").upper() == "SELL"]
        exit_fills = [fill for fill in sell_fills if str(fill.get("source_decision_type") or "").upper() == "EXIT"]
        reduce_fills = [fill for fill in sell_fills if str(fill.get("source_decision_type") or "").upper() == "REDUCE"]
        rows.append(
            {
                "date": day,
                "contaminated_valuation_same_day": day in contaminated_dates,
                "contamination_seen_before_day": contaminated_seen_before_day,
                "earliest_contamination_boundary": earliest,
                "portfolio_total_equity": _num(ps.get("portfolio_total_equity")),
                "portfolio_value": _num(ps.get("portfolio_value")),
                "current_total_equity": daily_states.get(day, {}).get("total_equity"),
                "current_cash": daily_states.get(day, {}).get("cash"),
                "current_buying_power": daily_states.get(day, {}).get("buying_power"),
                "position_weight_fields_present": any("current_weight" in position for position in ps_positions + pc_members),
                "position_sizing_positions": len(ps_positions),
                "portfolio_members": len(pc_members),
                "runtime_plan_count": len(plans),
                "positive_quantity_plan_count": len(positive_plans),
                "pending_item_count": _num(morning.get("pending_item_count")),
                "fill_count": len(fills),
                "buy_fill_count": len(buy_fills),
                "sell_fill_count": len(sell_fills),
                "exit_fill_count": len(exit_fills),
                "reduce_fill_count": len(reduce_fills),
                "buy_new_count": _count_action(plans, "BUY_NEW"),
                "add_count": _count_action(plans, "ADD"),
                "reduce_count": _count_action(plans, "REDUCE"),
                "exit_count": _count_action(plans, "EXIT"),
                "action_count_raw": dict(action_counts),
                "capital_authority_reached": contaminated_seen_before_day and bool(ps),
                "sizing_quantity_authority_reached": contaminated_seen_before_day and bool(ps_positions or plans),
                "trading_decision_contamination_evidence": (
                    "capital_input_reached_quantity_authority"
                    if contaminated_seen_before_day and bool(ps_positions or plans)
                    else ""
                ),
            }
        )
        if day in contaminated_dates:
            contaminated_seen_before_day = True
    return rows


def _performance_validity(contamination: list[dict[str, Any]], propagation: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not contamination:
        status = "TRUSTWORTHY"
    elif any(row.get("capital_authority_reached") for row in propagation):
        status = "INVALID_AFTER_BOUNDARY"
    else:
        status = "PARTIALLY_CONTAMINATED"
    return [
        {"metric": "Equity curve", "validity": "INVALID_AFTER_BOUNDARY" if contamination else "TRUSTWORTHY"},
        {"metric": "Daily PnL", "validity": "INVALID_AFTER_BOUNDARY" if contamination else "TRUSTWORTHY"},
        {"metric": "Final Return", "validity": status},
        {"metric": "Max Drawdown", "validity": "INVALID_AFTER_BOUNDARY" if contamination else "TRUSTWORTHY"},
        {"metric": "Cash", "validity": "PARTIALLY_CONTAMINATED" if contamination else "TRUSTWORTHY"},
        {"metric": "Exposure", "validity": status},
        {"metric": "Position count", "validity": "PARTIALLY_CONTAMINATED" if contamination else "TRUSTWORTHY"},
        {"metric": "BUY_NEW count", "validity": status},
        {"metric": "ADD count", "validity": status},
        {"metric": "SELL count", "validity": status},
        {"metric": "Regime attribution", "validity": status},
        {"metric": "Entry forward return analysis", "validity": "PARTIALLY_CONTAMINATED" if contamination else "TRUSTWORTHY"},
        {"metric": "Winner giveback analysis", "validity": status},
    ]


def _recovery_boundary(contamination: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not contamination:
        return [{"required_action": "short fresh validation only", "boundary_date": "", "reason": "no contamination detected"}]
    earliest = min(contamination, key=lambda row: str(row["date"]))
    return [
        {
            "required_action": "full 4-year fresh-run required",
            "boundary_date": earliest["date"],
            "boundary_symbol": earliest["symbol"],
            "reason": "valuation contamination reaches Current equity and downstream capital authority; no counterfactual replay was executed",
        }
    ]


def _summary(
    days: list[str],
    valuation_rows: list[dict[str, Any]],
    contamination: list[dict[str, Any]],
    symbol_summary: list[dict[str, Any]],
    propagation: list[dict[str, Any]],
    validity: list[dict[str, str]],
    recovery: list[dict[str, Any]],
) -> dict[str, Any]:
    contaminated_symbols = sorted({str(row["symbol"]) for row in contamination})
    contaminated_days = sorted({str(row["date"]) for row in contamination})
    earliest = min(contamination, key=lambda row: str(row["date"])) if contamination else {}
    false_values = [_num(row.get("estimated_false_pnl_contribution")) or 0.0 for row in contamination]
    capital_reached = any(row.get("capital_authority_reached") for row in propagation)
    sizing_reached = any(row.get("sizing_quantity_authority_reached") for row in propagation)
    positive_after = [
        row
        for row in propagation
        if row.get("contamination_seen_before_day")
        and (
            int(row.get("positive_quantity_plan_count") or 0) > 0
            or int(row.get("pending_item_count") or 0) > 0
            or int(row.get("fill_count") or 0) > 0
        )
    ]
    validity_map = {row["metric"]: row["validity"] for row in validity}
    return {
        "task_id": "Phase29-L21T-BF",
        "mode": "READ_ONLY_AUDIT",
        "target_run": RUN_ID,
        "audited_days": len(days),
        "position_valuation_rows_scanned": len(valuation_rows),
        "primary_judgment": (
            "VALUATION_CONTAMINATION_REACHES_CAPITAL_AUTHORITY_FULL_FRESH_RUN_REQUIRED"
            if contamination and capital_reached
            else "VALUATION_CONTAMINATION_DISPLAY_ONLY_OR_NOT_FOUND"
        ),
        "earliest_contamination_date": earliest.get("date", ""),
        "earliest_contaminated_symbol": earliest.get("symbol", ""),
        "contaminated_symbols": contaminated_symbols,
        "contaminated_symbol_count": len(contaminated_symbols),
        "contaminated_days": len(contaminated_days),
        "contaminated_dates": contaminated_days,
        "estimated_false_pnl_gross_magnitude": sum(abs(value) for value in false_values),
        "estimated_false_pnl_net_magnitude": sum(false_values),
        "max_abs_estimated_false_pnl_contribution": max([abs(value) for value in false_values] or [0.0]),
        "67310_only": contaminated_symbols == ["67310"],
        "other_symbols_affected": [symbol for symbol in contaminated_symbols if symbol != "67310"],
        "false_equity_reached_capital_authority": capital_reached,
        "sizing_equity_contaminated": sizing_reached,
        "position_weights_contaminated": any(
            row.get("contamination_seen_before_day") and row.get("position_weight_fields_present") for row in propagation
        ),
        "buy_new_affected": (
            "POSSIBLE_NOT_COUNTERFACTUALLY_PROVEN"
            if any(int(row.get("buy_fill_count") or 0) > 0 for row in positive_after)
            else "NO_EVIDENCE"
        ),
        "add_affected": "POSSIBLE_NOT_COUNTERFACTUALLY_PROVEN" if positive_after else "NO_EVIDENCE",
        "reduce_affected": (
            "POSSIBLE_NOT_COUNTERFACTUALLY_PROVEN"
            if any(int(row.get("reduce_fill_count") or 0) > 0 for row in positive_after)
            else "NO_EVIDENCE"
        ),
        "exit_affected": (
            "POSSIBLE_NOT_COUNTERFACTUALLY_PROVEN"
            if any(int(row.get("exit_fill_count") or 0) > 0 for row in positive_after)
            else "NO_EVIDENCE"
        ),
        "trading_state_contamination_classification": (
            "CAPITAL_AUTHORITY_CONTAMINATED" if capital_reached else "DISPLAY_ONLY" if contamination else "INSUFFICIENT_EVIDENCE"
        ),
        "performance_evidence_validity": validity_map,
        "target_run_resume_safe": False,
        "bounded_recovery_possible": False,
        "full_fresh_run_required": bool(contamination and capital_reached),
        "runtime_mutated": False,
        "strategy_changed": False,
        "fresh_run_executed": False,
        "phase30_entered": False,
        "recovery_recommendation": recovery[0],
    }


def _is_suspicious_step(previous_price: float | None, price: float | None, quantity: float | None) -> bool:
    if previous_price is None or price is None or quantity is None or quantity <= 0:
        return False
    delta = abs(price - previous_price)
    if delta == 0:
        return False
    return delta >= 500 and math.isclose(delta % 1000, 0.0, abs_tol=1e-9) or delta >= 1000


def _count_action(plans: list[dict[str, Any]], needle: str) -> int:
    total = 0
    for plan in plans:
        haystack = " ".join(
            str(plan.get(key) or "")
            for key in (
                "action",
                "side",
                "semantic_type",
                "action_type",
                "intent",
                "source_pm_action",
                "source_decision_type",
                "planning_intent",
                "order_side_intent",
            )
        )
        if needle in haystack:
            total += 1
    return total


def _first_col(frame: Any, names: tuple[str, ...]) -> str:
    columns = {str(column): str(column) for column in frame.columns}
    lower = {str(column).lower(): str(column) for column in frame.columns}
    for name in names:
        if name in columns:
            return columns[name]
        match = lower.get(name.lower())
        if match:
            return match
    return ""


def _first_name(columns: list[str], names: tuple[str, ...]) -> str:
    exact = {column: column for column in columns}
    lower = {column.lower(): column for column in columns}
    for name in names:
        if name in exact:
            return exact[name]
        match = lower.get(name.lower())
        if match:
            return match
    return ""


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number


def _positive_num(value: Any) -> float | None:
    number = _num(value)
    return number if number is not None and number > 0 else None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return _read_json(path)
    except json.JSONDecodeError:
        return {}


def _read_json_optional_or_list(path: Path) -> dict[str, Any] | list[Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


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
