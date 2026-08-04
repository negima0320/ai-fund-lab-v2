from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import median
from typing import Any, Iterable


REPORT_SCHEMA_VERSION = "phase26_i_performance_analysis_report_v1"
DEFAULT_EVIDENCE_ROOT = Path("reports/runtime_tests/runs")
QUALITY_BUCKETS = ("FULL", "REDUCED", "REVIEW", "REJECT")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def safe_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, dict):
        value = value.get("value")
    if value in (None, "", "MISSING", "NOT_AVAILABLE"):
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(result) or math.isinf(result):
        return default
    return result


def safe_int(value: Any, default: int = 0) -> int:
    return int(round(safe_float(value, float(default))))


def run_dir_for(run_id: str, evidence_root: Path = DEFAULT_EVIDENCE_ROOT) -> Path:
    if not run_id or "/" in run_id or "\\" in run_id or run_id in {".", ".."}:
        raise SystemExit(f"invalid --run-id: {run_id!r}")
    run_dir = (evidence_root / run_id).resolve()
    root = evidence_root.resolve()
    if root not in run_dir.parents:
        raise SystemExit("run directory must stay under reports/runtime_tests/runs")
    if not run_dir.is_dir():
        raise SystemExit(f"run evidence not found: {run_dir}")
    return run_dir


def ensure_run_scoped_path(path: Path, run_dir: Path) -> Path:
    resolved = path.resolve()
    if run_dir.resolve() not in resolved.parents and resolved != run_dir.resolve():
        raise RuntimeError(f"non run-scoped path rejected: {path}")
    return resolved


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def business_days(run_dir: Path) -> list[str]:
    daily = ensure_run_scoped_path(run_dir / "daily", run_dir)
    if not daily.is_dir():
        return []
    return sorted(path.name for path in daily.iterdir() if path.is_dir())


@dataclass(frozen=True)
class Analysis:
    run_id: str
    run_dir: Path
    output_dir: Path
    trade_history: list[dict[str, Any]]
    trade_with_quality: list[dict[str, Any]]
    symbol_statistics: list[dict[str, Any]]
    quality_statistics: list[dict[str, Any]]
    rank_statistics: list[dict[str, Any]]
    equity_curve: list[dict[str, Any]]
    drawdown: list[dict[str, Any]]
    drawdown_summary: dict[str, Any]
    cash_exposure: list[dict[str, Any]]
    cash_exposure_statistics: list[dict[str, Any]]
    holding_period: list[dict[str, Any]]
    reentry_statistics: list[dict[str, Any]]
    summary: dict[str, Any]


def load_fills(run_dir: Path) -> list[dict[str, Any]]:
    fills: list[dict[str, Any]] = []
    for day in business_days(run_dir):
        path = run_dir / "daily" / day / "execution" / "fills.json"
        if not path.is_file():
            continue
        payload = read_json(ensure_run_scoped_path(path, run_dir))
        for item in payload.get("fills") or []:
            if not isinstance(item, dict):
                continue
            amount = safe_float(item.get("gross_notional"))
            fills.append(
                {
                    "Date": item.get("business_date") or day,
                    "BUY/SELL": str(item.get("side") or ""),
                    "Symbol": str(item.get("symbol") or item.get("security_code") or ""),
                    "Qty": safe_float(item.get("quantity")),
                    "Price": safe_float(item.get("execution_price")),
                    "Amount": amount,
                    "Campaign": str(item.get("position_campaign_id") or ""),
                    "execution_id": str(item.get("execution_id") or ""),
                    "order_id": str(item.get("order_id") or ""),
                    "pending_item_id": str(item.get("pending_item_id") or ""),
                    "cash_effect": safe_float(item.get("cash_effect")),
                }
            )
    return sorted(fills, key=lambda row: (row["Date"], row["BUY/SELL"], row["Symbol"], row["execution_id"]))


def load_submit_quality(run_dir: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    quality: dict[tuple[str, str, str], dict[str, Any]] = {}
    for day in business_days(run_dir):
        path = run_dir / "daily" / day / "submit" / "runtime_manifest.json"
        if not path.is_file():
            continue
        payload = read_json(ensure_run_scoped_path(path, run_dir))
        for item in payload.get("submit_guard_item_evidence") or []:
            if not isinstance(item, dict):
                continue
            qc = item.get("quantity_contract") if isinstance(item.get("quantity_contract"), dict) else {}
            symbol = str(item.get("symbol") or "")
            side = str(item.get("side") or "")
            record = {
                "Quality Score": safe_float(qc.get("quality_score") or item.get("quality_score"), 0.0),
                "Quality Action": str(qc.get("quality_action") or item.get("quality_action") or ""),
                "Quality Adjustment": safe_float(qc.get("quality_allocation_adjustment") or item.get("quality_allocation_adjustment"), 0.0),
                "Rank": safe_int(item.get("opportunity_buy_rank") or qc.get("opportunity_buy_rank"), 0),
                "Entry Rank": safe_int(item.get("opportunity_buy_rank") or qc.get("opportunity_buy_rank"), 0),
                "Opportunity Score": safe_float(item.get("opportunity_expected_edge_score") or item.get("opportunity_expected_return"), 0.0),
                "quality_decision_id": str(qc.get("quality_decision_id") or item.get("quality_decision_id") or ""),
                "pending_item_id": str(item.get("pending_item_id") or ""),
                "selected_notional": safe_float(qc.get("selected_notional") or item.get("capital_allocation_amount"), 0.0),
            }
            quality[(day, side, symbol)] = record
            pending = record["pending_item_id"]
            if pending:
                quality[(day, pending, symbol)] = record
    return quality


def load_equity_curve(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for day in business_days(run_dir):
        path = run_dir / "daily" / day / "current_valuation_refresh" / "current_valuation_manifest.json"
        if not path.is_file():
            continue
        payload = read_json(ensure_run_scoped_path(path, run_dir))
        current = payload.get("artifact", {}).get("candidate_current") if isinstance(payload.get("artifact"), dict) else {}
        if not isinstance(current, dict):
            continue
        total = safe_float(current.get("total_equity"))
        cash = safe_float(current.get("cash"))
        market_value = safe_float(current.get("market_value") or current.get("new_total_market_value"))
        invested = market_value / total if total else 0.0
        rows.append(
            {
                "Date": str(current.get("business_date") or day),
                "Cash": cash,
                "Market Value": market_value,
                "Total Equity": total,
                "Cash Ratio": cash / total if total else 0.0,
                "Invested Ratio": invested,
                "Position Count": len(current.get("positions") or []),
                "Realized PnL": safe_float(current.get("realized_pnl")),
                "Unrealized PnL": safe_float(current.get("new_unrealized_pnl")),
            }
        )
    return sorted(rows, key=lambda row: row["Date"])


def quality_bucket(action: str) -> str:
    value = (action or "").upper()
    if value.startswith("FULL"):
        return "FULL"
    if value.startswith("REDUCED"):
        return "REDUCED"
    if "REVIEW" in value:
        return "REVIEW"
    if "REJECT" in value:
        return "REJECT"
    return "UNKNOWN"


def build_campaigns(trades: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    campaigns: dict[str, dict[str, Any]] = {}
    for trade in trades:
        campaign = trade["Campaign"] or f"{trade['Symbol']}:UNSCOPED"
        row = campaigns.setdefault(
            campaign,
            {
                "Campaign": campaign,
                "Symbol": trade["Symbol"],
                "Entry": "",
                "Exit": "",
                "buy_qty": 0.0,
                "sell_qty": 0.0,
                "buy_amount": 0.0,
                "sell_amount": 0.0,
                "entry_rank": 0,
                "quality_action": "",
                "quality_bucket": "UNKNOWN",
                "quality_score": 0.0,
                "quality_adjustment": 0.0,
                "opportunity_score": 0.0,
            },
        )
        if trade["BUY/SELL"] == "BUY":
            row["Entry"] = row["Entry"] or trade["Date"]
            row["buy_qty"] += safe_float(trade["Qty"])
            row["buy_amount"] += safe_float(trade["Amount"])
            for key, target in (
                ("Entry Rank", "entry_rank"),
                ("Quality Action", "quality_action"),
                ("Quality Score", "quality_score"),
                ("Quality Adjustment", "quality_adjustment"),
                ("Opportunity Score", "opportunity_score"),
            ):
                if trade.get(key) not in ("", 0, 0.0, None):
                    row[target] = trade.get(key)
            row["quality_bucket"] = quality_bucket(str(row.get("quality_action") or ""))
        elif trade["BUY/SELL"] == "SELL":
            row["Exit"] = trade["Date"]
            row["sell_qty"] += safe_float(trade["Qty"])
            row["sell_amount"] += safe_float(trade["Amount"])
    holding: list[dict[str, Any]] = []
    for row in campaigns.values():
        cost_for_sold = row["buy_amount"] * (row["sell_qty"] / row["buy_qty"]) if row["buy_qty"] else 0.0
        pnl = row["sell_amount"] - cost_for_sold
        holding_days = date_diff(row.get("Entry"), row.get("Exit"))
        result = {
            "Campaign": row["Campaign"],
            "Symbol": row["Symbol"],
            "Entry": row["Entry"],
            "Exit": row["Exit"],
            "Holding Days": holding_days,
            "Winner": pnl > 0,
            "Loser": pnl < 0,
            "PnL": pnl,
            "Return": pnl / cost_for_sold if cost_for_sold else 0.0,
            "Quality Bucket": row["quality_bucket"],
            "Quality Action": row["quality_action"],
            "Quality Score": row["quality_score"],
            "Quality Adjustment": row["quality_adjustment"],
            "Entry Rank": row["entry_rank"],
            "Opportunity Score": row["opportunity_score"],
            "Closed": bool(row["Exit"]),
        }
        holding.append(result)
        row.update(result)
    return sorted(holding, key=lambda row: (row["Entry"], row["Campaign"])), campaigns


def date_diff(start: Any, end: Any) -> int:
    if not start or not end:
        return 0
    try:
        return (date.fromisoformat(str(end)) - date.fromisoformat(str(start))).days
    except ValueError:
        return 0


def drawdown_rows(equity: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    peak = 0.0
    peak_date = ""
    max_row: dict[str, Any] = {}
    for item in equity:
        total = safe_float(item.get("Total Equity"))
        if not rows or total >= peak:
            peak = total
            peak_date = str(item.get("Date") or "")
        amount = total - peak
        rate = amount / peak if peak else 0.0
        row = {
            "Date": item.get("Date"),
            "Total Equity": total,
            "Peak Equity": peak,
            "Peak Date": peak_date,
            "Drawdown": amount,
            "Drawdown %": rate,
        }
        rows.append(row)
        if not max_row or amount < safe_float(max_row.get("Drawdown")):
            max_row = row
    recovery_date = ""
    if max_row:
        bottom_seen = False
        for row in rows:
            if row["Date"] == max_row["Date"]:
                bottom_seen = True
            if bottom_seen and safe_float(row.get("Drawdown")) >= 0:
                recovery_date = str(row.get("Date") or "")
                break
    summary = {
        "Max DD": safe_float(max_row.get("Drawdown")) if max_row else 0.0,
        "Drawdown %": safe_float(max_row.get("Drawdown %")) if max_row else 0.0,
        "Peak Date": max_row.get("Peak Date", "") if max_row else "",
        "Bottom Date": max_row.get("Date", "") if max_row else "",
        "Recovery Date": recovery_date or "UNRECOVERED" if max_row else "",
        "Recovery Days": date_diff(max_row.get("Date"), recovery_date) if max_row and recovery_date else 0,
    }
    return rows, summary


def profit_stats(pnls: Iterable[float]) -> dict[str, Any]:
    values = [safe_float(v) for v in pnls]
    wins = [v for v in values if v > 0]
    losses = [v for v in values if v < 0]
    gross_profit = sum(wins)
    gross_loss = sum(losses)
    avg_win = gross_profit / len(wins) if wins else 0.0
    avg_loss = gross_loss / len(losses) if losses else 0.0
    return {
        "Gross Profit": gross_profit,
        "Gross Loss": gross_loss,
        "Net Profit": gross_profit + gross_loss,
        "Profit Factor": gross_profit / abs(gross_loss) if gross_loss else None if gross_profit else 0.0,
        "Win Rate": len(wins) / len(values) if values else 0.0,
        "Average Win": avg_win,
        "Average Loss": avg_loss,
        "Payoff Ratio": avg_win / abs(avg_loss) if avg_loss else None if avg_win else 0.0,
        "Expectancy": (sum(values) / len(values)) if values else 0.0,
        "Count": len(values),
    }


def grouped_stats(rows: list[dict[str, Any]], key: str, include_all_quality: bool = False) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key) or "UNKNOWN")].append(row)
    if include_all_quality:
        for bucket in QUALITY_BUCKETS:
            groups.setdefault(bucket, [])
    output = []
    for name in sorted(groups):
        items = groups[name]
        stats = profit_stats([safe_float(item.get("PnL")) for item in items])
        holding = [safe_float(item.get("Holding Days")) for item in items if safe_float(item.get("Holding Days"))]
        returns = [safe_float(item.get("Return")) for item in items]
        output.append(
            {
                key: name,
                "Count": stats["Count"],
                "Win Rate": stats["Win Rate"],
                "PF": stats["Profit Factor"],
                "Average PnL": stats["Expectancy"],
                "Average Holding Days": sum(holding) / len(holding) if holding else 0.0,
                "Average Return": sum(returns) / len(returns) if returns else 0.0,
            }
        )
    return output


def cash_exposure_stats(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for metric in ("Cash", "Cash Ratio", "Invested Ratio", "Position Count"):
        values = [safe_float(row.get(metric)) for row in rows]
        output.append(
            {
                "Metric": metric,
                "Average": sum(values) / len(values) if values else 0.0,
                "Median": median(values) if values else 0.0,
                "Min": min(values) if values else 0.0,
                "Max": max(values) if values else 0.0,
            }
        )
    return output


def reentry_stats(campaigns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in campaigns:
        grouped[str(row.get("Symbol") or "")].append(row)
    output = []
    for symbol, items in sorted(grouped.items()):
        items = sorted(items, key=lambda row: row.get("Entry") or "")
        intervals = [
            date_diff(items[index - 1].get("Exit") or items[index - 1].get("Entry"), items[index].get("Entry"))
            for index in range(1, len(items))
        ]
        output.append(
            {
                "Symbol": symbol,
                "Entry Count": sum(1 for item in items if item.get("Entry")),
                "Exit Count": sum(1 for item in items if item.get("Exit")),
                "Re-entry Count": max(0, sum(1 for item in items if item.get("Entry")) - 1),
                "Average Re-entry Interval": sum(intervals) / len(intervals) if intervals else 0.0,
                "PnL": sum(safe_float(item.get("PnL")) for item in items),
            }
        )
    return output


def analyze_run(run_id: str, evidence_root: Path = DEFAULT_EVIDENCE_ROOT) -> Analysis:
    run_dir = run_dir_for(run_id, evidence_root)
    output_dir = run_dir / "performance_report"
    fills = load_fills(run_dir)
    quality = load_submit_quality(run_dir)
    trade_history = [
        {key: row[key] for key in ("Date", "BUY/SELL", "Symbol", "Qty", "Price", "Amount", "Campaign")}
        for row in fills
    ]
    trade_with_quality: list[dict[str, Any]] = []
    for row in fills:
        q = quality.get((row["Date"], row["BUY/SELL"], row["Symbol"])) or quality.get((row["Date"], row["pending_item_id"], row["Symbol"])) or {}
        enriched = {
            "Date": row["Date"],
            "BUY/SELL": row["BUY/SELL"],
            "Symbol": row["Symbol"],
            "Qty": row["Qty"],
            "Price": row["Price"],
            "Amount": row["Amount"],
            "Campaign": row["Campaign"],
            "Quality Score": q.get("Quality Score", ""),
            "Quality Action": q.get("Quality Action", ""),
            "Quality Adjustment": q.get("Quality Adjustment", ""),
            "Rank": q.get("Rank", ""),
            "Entry Rank": q.get("Entry Rank", ""),
            "Opportunity Score": q.get("Opportunity Score", ""),
            "PnL": 0.0,
            "Holding Days": 0,
        }
        trade_with_quality.append(enriched)
    holding_period, campaigns = build_campaigns(trade_with_quality)
    campaign_by_id = {row["Campaign"]: row for row in holding_period}
    for row in trade_with_quality:
        campaign = campaign_by_id.get(row["Campaign"]) or {}
        if row["BUY/SELL"] == "BUY":
            row["PnL"] = campaign.get("PnL", 0.0)
            row["Holding Days"] = campaign.get("Holding Days", 0)
    equity_curve = load_equity_curve(run_dir)
    drawdowns, dd_summary = drawdown_rows(equity_curve)
    closed = [row for row in holding_period if row.get("Closed")]
    stats = profit_stats([safe_float(row.get("PnL")) for row in closed])
    first_equity = safe_float(equity_curve[0].get("Total Equity")) if equity_curve else 0.0
    final_equity = safe_float(equity_curve[-1].get("Total Equity")) if equity_curve else 0.0
    first_realized = safe_float(equity_curve[0].get("Realized PnL")) if equity_curve else 0.0
    first_unrealized = safe_float(equity_curve[0].get("Unrealized PnL")) if equity_curve else 0.0
    initial_equity = first_equity - first_realized - first_unrealized
    if not initial_equity:
        initial_equity = 1_000_000.0 if equity_curve else 0.0
    total_return = final_equity - initial_equity
    elapsed_days = max(1, date_diff(equity_curve[0]["Date"], equity_curve[-1]["Date"]) or len(equity_curve)) if equity_curve else 1
    annualized = (final_equity / initial_equity) ** (365.0 / elapsed_days) - 1.0 if initial_equity and final_equity > 0 else 0.0
    avg_holding = sum(safe_float(row.get("Holding Days")) for row in holding_period) / len(holding_period) if holding_period else 0.0
    final_cash_ratio = safe_float(equity_curve[-1].get("Cash Ratio")) if equity_curve else 0.0
    final_invested_ratio = safe_float(equity_curve[-1].get("Invested Ratio")) if equity_curve else 0.0
    summary = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "run_id": run_id,
        "source": "run_scoped_runtime_test_evidence_only",
        "runtime_input_policy": {
            "strategy_input_added": False,
            "historical_result_used_as_strategy_input": False,
            "paper_ledger_used_as_strategy_input": False,
            "future_information_used": False,
            "run_scoped_only": True,
            "production_demo_historical_compatible": True,
        },
        "Return": total_return,
        "Return %": total_return / initial_equity if initial_equity else 0.0,
        "Annualized Return": annualized,
        "Initial Equity": initial_equity,
        "Final Equity": final_equity,
        "Gross Profit": stats["Gross Profit"],
        "Gross Loss": stats["Gross Loss"],
        "Net Profit": stats["Net Profit"],
        "Profit Factor": stats["Profit Factor"],
        "Win Rate": stats["Win Rate"],
        "Average Win": stats["Average Win"],
        "Average Loss": stats["Average Loss"],
        "Payoff Ratio": stats["Payoff Ratio"],
        "Expectancy": stats["Expectancy"],
        "Max Drawdown": dd_summary.get("Max DD", 0.0),
        "Drawdown %": dd_summary.get("Drawdown %", 0.0),
        "Average Holding Days": avg_holding,
        "BUY Count": sum(1 for row in fills if row["BUY/SELL"] == "BUY"),
        "SELL Count": sum(1 for row in fills if row["BUY/SELL"] == "SELL"),
        "Current Positions": safe_int(equity_curve[-1].get("Position Count")) if equity_curve else 0,
        "Cash Ratio": final_cash_ratio,
        "Invested Ratio": final_invested_ratio,
        "drawdown": dd_summary,
        "output_files": {},
    }
    symbol_rows = grouped_stats(holding_period, "Symbol")
    for row in symbol_rows:
        symbol = row["Symbol"]
        row["Campaign Count"] = sum(1 for item in holding_period if item.get("Symbol") == symbol)
        row["Holding Days"] = row.pop("Average Holding Days")
        row["Re-entry Count"] = next((item["Re-entry Count"] for item in reentry_stats(holding_period) if item["Symbol"] == symbol), 0)
    quality_rows = grouped_stats(holding_period, "Quality Bucket", include_all_quality=True)
    rank_rows = grouped_stats(holding_period, "Entry Rank")
    cash_rows = cash_exposure_stats(equity_curve)
    return Analysis(
        run_id=run_id,
        run_dir=run_dir,
        output_dir=output_dir,
        trade_history=trade_history,
        trade_with_quality=trade_with_quality,
        symbol_statistics=symbol_rows,
        quality_statistics=quality_rows,
        rank_statistics=rank_rows,
        equity_curve=equity_curve,
        drawdown=drawdowns,
        drawdown_summary=dd_summary,
        cash_exposure=equity_curve,
        cash_exposure_statistics=cash_rows,
        holding_period=holding_period,
        reentry_statistics=reentry_stats(holding_period),
        summary=summary,
    )


def write_all(analysis: Analysis) -> None:
    out = analysis.output_dir
    write_csv(out / "trade_history.csv", analysis.trade_history, ["Date", "BUY/SELL", "Symbol", "Qty", "Price", "Amount", "Campaign"])
    write_csv(
        out / "trade_with_quality.csv",
        analysis.trade_with_quality,
        ["Date", "BUY/SELL", "Symbol", "Qty", "Price", "Amount", "Campaign", "Quality Score", "Quality Action", "Quality Adjustment", "Rank", "Entry Rank", "Opportunity Score", "PnL", "Holding Days"],
    )
    write_csv(out / "symbol_statistics.csv", analysis.symbol_statistics, ["Symbol", "Campaign Count", "Win Rate", "PF", "Average PnL", "Holding Days", "Re-entry Count", "Average Return"])
    write_csv(out / "quality_statistics.csv", analysis.quality_statistics, ["Quality Bucket", "Count", "Win Rate", "PF", "Average PnL", "Average Holding Days", "Average Return"])
    write_csv(out / "rank_statistics.csv", analysis.rank_statistics, ["Entry Rank", "Count", "Win Rate", "PF", "Average PnL", "Average Holding Days", "Average Return"])
    write_csv(out / "equity_curve.csv", analysis.equity_curve, ["Date", "Cash", "Market Value", "Total Equity", "Cash Ratio", "Invested Ratio", "Position Count", "Realized PnL", "Unrealized PnL"])
    write_csv(out / "drawdown.csv", analysis.drawdown, ["Date", "Total Equity", "Peak Equity", "Peak Date", "Drawdown", "Drawdown %"])
    write_csv(out / "cash_exposure.csv", analysis.cash_exposure, ["Date", "Cash", "Cash Ratio", "Invested Ratio", "Position Count"])
    write_csv(out / "cash_exposure_statistics.csv", analysis.cash_exposure_statistics, ["Metric", "Average", "Median", "Min", "Max"])
    write_csv(out / "holding_period.csv", analysis.holding_period, ["Campaign", "Symbol", "Entry", "Exit", "Holding Days", "Winner", "Loser", "PnL", "Return", "Quality Bucket", "Quality Action", "Entry Rank", "Closed"])
    write_csv(out / "reentry_statistics.csv", analysis.reentry_statistics, ["Symbol", "Entry Count", "Exit Count", "Re-entry Count", "Average Re-entry Interval", "PnL"])
    summary = dict(analysis.summary)
    summary["output_files"] = {
        name: str(out / name)
        for name in (
            "performance_summary.json",
            "trade_history.csv",
            "trade_with_quality.csv",
            "symbol_statistics.csv",
            "quality_statistics.csv",
            "rank_statistics.csv",
            "equity_curve.csv",
            "drawdown.csv",
            "cash_exposure.csv",
            "cash_exposure_statistics.csv",
            "holding_period.csv",
            "reentry_statistics.csv",
        )
    }
    analysis.summary["output_files"] = summary["output_files"]
    write_json(out / "performance_summary.json", summary)


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


def run_cli(section: str) -> None:
    parser = argparse.ArgumentParser(description=f"Phase26-I performance analysis: {section}")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-root", default=str(DEFAULT_EVIDENCE_ROOT))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    analysis = analyze_run(args.run_id, Path(args.evidence_root))
    write_all(analysis)
    section_payload = {
        "summary": analysis.summary,
        "trade_history": analysis.trade_history,
        "trade_with_quality": analysis.trade_with_quality,
        "symbol_statistics": analysis.symbol_statistics,
        "quality_statistics": analysis.quality_statistics,
        "rank_statistics": analysis.rank_statistics,
        "equity_curve": analysis.equity_curve,
        "drawdown": {"summary": analysis.drawdown_summary, "rows": analysis.drawdown},
        "profit_factor": {key: analysis.summary.get(key) for key in ("Gross Profit", "Gross Loss", "Profit Factor", "Win Rate", "Average Win", "Average Loss", "Payoff Ratio", "Expectancy")},
        "cash_exposure": {"rows": analysis.cash_exposure, "statistics": analysis.cash_exposure_statistics},
        "holding_period": analysis.holding_period,
        "reentry_analysis": analysis.reentry_statistics,
    }[section]
    if args.json or section == "summary":
        print_json(section_payload)
    else:
        print(f"wrote {section} to {analysis.output_dir}")
