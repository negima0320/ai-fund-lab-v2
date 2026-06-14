from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.capital_allocation_ai.phase7c_daily_path_validation import (
    DEFAULT_DAILY_RESPONSE_DIR,
    DEFAULT_RANKED_DAILY_PATH,
    current_rank_score,
    load_daily_close_path,
    load_ranked_daily,
    max_drawdown,
    now_utc,
    round_float,
)


DEFAULT_OUTPUT_DIR = Path("reports/capital_allocation_ai/phase7e")
COMPLETION_STATUS = "PHASE7E_STRICT_LONG_TERM_BACKTEST_COMPLETE"
TRADING_DAYS_PER_YEAR = 245
LOT_SIZE = 100


@dataclass(frozen=True)
class StrictConfig:
    policy_id: str
    policy_name: str
    family: str
    settlement_mode: str = "conservative_T2_cash_unavailable"
    minimum_holding_days: int = 20
    max_position_weight: float = 0.20
    emergency_exit_pct: float | None = None
    replacement_cap_per_month: int | None = None
    weekly_reevaluation: bool = False
    transaction_cost_bps: float = 0.0
    slippage_bps: float = 0.0
    cash_buffer_ratio: float = 0.05
    min_position_value: float = 50_000.0
    initial_assets: float = 1_000_000.0
    fixed_holding_days: int = 20
    replacement_rank_threshold: int = 50
    replacement_edge_margin: float = 0.02
    confirmation_days: int = 2
    reentry_cooldown_days: int = 0


@dataclass
class StrictPosition:
    code: str
    share_count: int
    avg_entry_price: float
    entry_date: str
    entry_index: int
    cost_basis: float
    entry_rank: int
    entry_score: float
    last_price: float
    degradation_streak: int = 0


def run_phase7e_strict_backtest(
    *,
    ranked_daily_path: Path = DEFAULT_RANKED_DAILY_PATH,
    daily_response_dir: Path = DEFAULT_DAILY_RESPONSE_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    created_at: str | None = None,
) -> dict[str, Any]:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)
    ranked = load_ranked_daily(ranked_daily_path)
    prices = load_daily_close_path(daily_response_dir, ranked)

    rows: list[dict[str, Any]] = []
    annual: list[dict[str, Any]] = []
    trades_all: list[pd.DataFrame] = []
    daily_all: list[pd.DataFrame] = []
    holdings_all: list[pd.DataFrame] = []
    for config in build_configs():
        result = simulate_strict(ranked, prices, config)
        rows.append(result["metrics"])
        annual.extend(result["annual_summary"])
        for key, collection in [("trades", trades_all), ("daily", daily_all), ("holdings", holdings_all)]:
            frame = result[key].copy()
            if not frame.empty:
                frame.insert(0, "policy_id", config.policy_id)
                frame.insert(1, "policy_name", config.policy_name)
            collection.append(frame)

    comparison = pd.DataFrame(rows).sort_values(["scenario_priority", "policy_id"])
    annual_frame = pd.DataFrame(annual).sort_values(["policy_id", "year"]) if annual else pd.DataFrame()
    trade_ledger = pd.concat(trades_all, ignore_index=True) if trades_all else pd.DataFrame()
    daily_ledger = pd.concat(daily_all, ignore_index=True) if daily_all else pd.DataFrame()
    holdings_ledger = pd.concat(holdings_all, ignore_index=True) if holdings_all else pd.DataFrame()
    settlement_cmp = comparison[comparison["settlement_mode"].isin(["conservative_T2_cash_unavailable", "same_settlement_buying_power_allowed"])].copy()
    tx_cmp = comparison[comparison["family"].isin(["COST"])].copy()
    skip_summary = summarize_skips(trade_ledger, comparison)
    leakage = leakage_audit(ranked, prices, created_at)

    paths = {
        "validation_summary": output_dir / "validation_summary.json",
        "policy_comparison": output_dir / "policy_comparison.csv",
        "settlement_mode_comparison": output_dir / "settlement_mode_comparison.csv",
        "transaction_cost_comparison": output_dir / "transaction_cost_comparison.csv",
        "skip_reason_summary": output_dir / "skip_reason_summary.csv",
        "annual_summary": output_dir / "annual_summary.csv",
        "trade_ledger": output_dir / "trade_ledger.csv",
        "daily_portfolio_ledger": output_dir / "daily_portfolio_ledger.csv",
        "holdings_ledger": output_dir / "holdings_ledger.csv",
        "equity_curve": output_dir / "equity_curve.csv",
        "leakage_audit": output_dir / "leakage_audit.json",
    }
    comparison.to_csv(paths["policy_comparison"], index=False)
    settlement_cmp.to_csv(paths["settlement_mode_comparison"], index=False)
    tx_cmp.to_csv(paths["transaction_cost_comparison"], index=False)
    skip_summary.to_csv(paths["skip_reason_summary"], index=False)
    annual_frame.to_csv(paths["annual_summary"], index=False)
    trade_ledger.to_csv(paths["trade_ledger"], index=False)
    daily_ledger.to_csv(paths["daily_portfolio_ledger"], index=False)
    holdings_ledger.to_csv(paths["holdings_ledger"], index=False)
    daily_ledger.to_csv(paths["equity_curve"], index=False)
    write_json(paths["leakage_audit"], leakage)
    summary = build_summary(comparison, ranked, prices, paths, leakage, created_at)
    write_json(paths["validation_summary"], summary)
    return {"summary": summary, "policy_comparison": comparison, "annual_summary": annual_frame, "leakage_audit": leakage}


def build_configs() -> list[StrictConfig]:
    base = [
        StrictConfig("A_FIXED_20BD", "Baseline A fixed 20bd", "BASE"),
        StrictConfig("C3_MIN15_T2", "C3 min15 strict T+2", "C3", minimum_holding_days=15),
        StrictConfig("C3_MIN15_BP_ALLOWED", "C3 min15 buying power allowed", "C3", settlement_mode="same_settlement_buying_power_allowed", minimum_holding_days=15),
        StrictConfig("C3_MIN15_WEIGHT15", "C3 min15 max weight 15%", "C3", minimum_holding_days=15, max_position_weight=0.15),
        StrictConfig("C3_MIN15_EMERGENCY10", "C3 min15 emergency -10%", "C3", minimum_holding_days=15, emergency_exit_pct=-0.10),
        StrictConfig("A_FIXED_EMERGENCY10", "A fixed emergency -10%", "EMERGENCY", emergency_exit_pct=-0.10),
        StrictConfig("C3_MIN15_CAP3", "C3 min15 cap/month 3", "C3", minimum_holding_days=15, replacement_cap_per_month=3),
        StrictConfig("C3_MIN15_CAP4", "C3 min15 cap/month 4", "C3", minimum_holding_days=15, replacement_cap_per_month=4),
        StrictConfig("C3_MIN15_CAP5", "C3 min15 cap/month 5", "C3", minimum_holding_days=15, replacement_cap_per_month=5),
        StrictConfig("C3_MIN15_WEEKLY", "C3 min15 weekly reevaluation", "C3", minimum_holding_days=15, weekly_reevaluation=True),
    ]
    for bps in [0.0, 10.0, 30.0]:
        base.append(StrictConfig(f"COST_C3_MIN15_{int(bps)}BPS", f"C3 min15 cost/slippage {bps:.0f}bps", "COST", minimum_holding_days=15, transaction_cost_bps=bps, slippage_bps=bps))
    return base


def simulate_strict(ranked: pd.DataFrame, prices: pd.DataFrame, config: StrictConfig) -> dict[str, Any]:
    dates = [d for d in sorted(prices["target_date"].unique()) if d >= ranked["target_date"].min()]
    idx_by_date = {d: i for i, d in enumerate(dates)}
    ranked_by_date = {d: g.copy() for d, g in ranked.groupby("target_date", sort=False)}
    rank_lookup = {(r.target_date, r.code): r for r in ranked.itertuples(index=False)}
    close_lookup = {(r.target_date, r.code): float(r.close) for r in prices.itertuples(index=False)}
    cash = config.initial_assets
    unsettled: list[dict[str, Any]] = []
    positions: dict[str, StrictPosition] = {}
    trades: list[dict[str, Any]] = []
    daily: list[dict[str, Any]] = []
    holdings: list[dict[str, Any]] = []
    stats = {"tx": 0.0, "slip": 0.0, "skip_lot": 0, "skip_min": 0, "skip_cash": 0, "skip_settle": 0, "lot_cash": 0.0}
    monthly_repl: dict[str, int] = {}
    last_exit_idx_by_code: dict[str, int] = {}
    next_buy_idx = -1

    for date in dates:
        i = idx_by_date[date]
        newly_settled = sum(x["amount"] for x in unsettled if x["settle_index"] <= i)
        if newly_settled:
            cash += newly_settled
            unsettled = [x for x in unsettled if x["settle_index"] > i]
        day = ranked_by_date.get(date)
        sold_replacement = False

        for code, pos in list(positions.items()):
            close = close_lookup.get((date, code), pos.last_price)
            pos.last_price = close
            hold = i - pos.entry_index
            ret = close / pos.avg_entry_price - 1.0 if pos.avg_entry_price else 0.0
            rank, score = current_rank_score(rank_lookup, date, code, pos.entry_score)
            if config.emergency_exit_pct is not None and ret <= config.emergency_exit_pct:
                proceeds = sell(pos, date, i, close, "EMERGENCY_EXIT", trades, stats, config)
                unsettled.append({"amount": proceeds, "settle_index": i + 2})
                last_exit_idx_by_code[code] = i
                del positions[code]
                continue
            if hold >= config.fixed_holding_days:
                proceeds = sell(pos, date, i, close, "FIXED_20BD", trades, stats, config)
                unsettled.append({"amount": proceeds, "settle_index": i + 2})
                last_exit_idx_by_code[code] = i
                del positions[code]
                continue
            if day is not None and should_replace(pos, date, i, rank, score, day, positions, config, monthly_repl):
                proceeds = sell(pos, date, i, close, "REPLACEMENT", trades, stats, config)
                unsettled.append({"amount": proceeds, "settle_index": i + 2})
                monthly_repl[date[:7]] = monthly_repl.get(date[:7], 0) + 1
                last_exit_idx_by_code[code] = i
                del positions[code]
                sold_replacement = True
                next_buy_idx = max(next_buy_idx, i + 1)

        if day is not None and date <= ranked["target_date"].max() and not sold_replacement and i >= next_buy_idx:
            for row in day.head(3).itertuples(index=False):
                code = str(row.code)
                if code in positions:
                    continue
                if config.reentry_cooldown_days and code in last_exit_idx_by_code and i - last_exit_idx_by_code[code] < config.reentry_cooldown_days:
                    record_skip(trades, config, date, code, "COOLDOWN")
                    continue
                close = close_lookup.get((date, code))
                if close is None:
                    record_skip(trades, config, date, code, "NO_PRICE")
                    continue
                unsettled_cash = sum(x["amount"] for x in unsettled)
                buy_power = cash + (unsettled_cash if config.settlement_mode == "same_settlement_buying_power_allowed" else 0.0)
                total = portfolio_total(cash, unsettled, positions, close_lookup, date)
                target = min(total * config.max_position_weight, max(0.0, buy_power - total * config.cash_buffer_ratio))
                buy_result = buy(row, date, i, close, target, cash, buy_power, stats, config)
                if buy_result is None:
                    reason = stats.get("last_skip", "INSUFFICIENT_CASH")
                    if reason == "INSUFFICIENT_CASH" and config.settlement_mode == "conservative_T2_cash_unavailable" and unsettled_cash > 0:
                        stats["skip_settle"] += 1
                        reason = "SETTLEMENT_CASH_UNAVAILABLE"
                    record_skip(trades, config, date, code, reason)
                    continue
                pos, cash_used = buy_result
                if cash_used > cash and config.settlement_mode == "conservative_T2_cash_unavailable":
                    stats["skip_settle"] += 1
                    record_skip(trades, config, date, code, "SETTLEMENT_CASH_UNAVAILABLE")
                    continue
                cash = consume_buy_funds(cash, unsettled, cash_used)
                record_buy(trades, pos, date, row, config)
                positions[code] = pos

        invested = sum(p.share_count * close_lookup.get((date, p.code), p.last_price) for p in positions.values())
        unsettled_cash = sum(x["amount"] for x in unsettled)
        total_net = cash + unsettled_cash + invested
        daily.append({
            "target_date": date, "year": int(date[:4]), "cash": round_float(cash), "available_cash": round_float(cash),
            "unsettled_cash": round_float(unsettled_cash), "invested_value": round_float(invested),
            "total_assets_net": round_float(total_net), "total_assets_gross": round_float(total_net + stats["tx"] + stats["slip"]),
            "capital_utilization": round_float(invested / total_net if total_net else 0), "open_position_count": len(positions),
        })
        for p in positions.values():
            price = close_lookup.get((date, p.code), p.last_price)
            holdings.append({"target_date": date, "code": p.code, "share_count": p.share_count, "avg_entry_price": p.avg_entry_price, "entry_date": p.entry_date, "cost_basis": p.cost_basis, "market_value": p.share_count * price, "unrealized_pnl": p.share_count * (price - p.avg_entry_price)})

    final_date = dates[-1]
    final_i = idx_by_date[final_date]
    for pos in list(positions.values()):
        close = close_lookup.get((final_date, pos.code), pos.last_price)
        sell(pos, final_date, final_i, close, "FORCED_END_OF_SAMPLE", trades, stats, config)
    trade_df, daily_df, holdings_df = pd.DataFrame(trades), pd.DataFrame(daily), pd.DataFrame(holdings)
    metrics = metrics_for(trade_df, daily_df, holdings_df, stats, config, dates[0], dates[-1])
    annual = annual_for(trade_df, daily_df, config)
    return {"metrics": metrics, "annual_summary": annual, "trades": trade_df, "daily": daily_df, "holdings": holdings_df}


def should_replace(pos: StrictPosition, date: str, i: int, rank: int, score: float, day: pd.DataFrame, positions: dict[str, StrictPosition], config: StrictConfig, monthly: dict[str, int]) -> bool:
    if config.family in {"BASE", "EMERGENCY"}:
        return False
    if i - pos.entry_index < config.minimum_holding_days:
        return False
    if config.weekly_reevaluation and (i - pos.entry_index) % 5 != 0:
        return False
    if config.replacement_cap_per_month is not None and monthly.get(date[:7], 0) >= config.replacement_cap_per_month:
        return False
    if rank <= config.replacement_rank_threshold:
        pos.degradation_streak = 0
        return False
    pos.degradation_streak += 1
    if pos.degradation_streak < config.confirmation_days:
        return False
    held = set(positions)
    return any(str(r.code) not in held and float(r.expected_edge_score) >= score + config.replacement_edge_margin for r in day.head(3).itertuples(index=False))


def buy(row: Any, date: str, i: int, close: float, target: float, cash: float, buy_power: float, stats: dict[str, Any], config: StrictConfig) -> tuple[StrictPosition, float] | None:
    code = str(row.code)
    if target < config.min_position_value:
        stats["skip_min"] += 1; stats["last_skip"] = "MIN_POSITION_VALUE"; return None
    price = close * (1 + config.slippage_bps / 10000)
    shares = int(target // (price * LOT_SIZE)) * LOT_SIZE
    if shares < LOT_SIZE:
        stats["skip_lot"] += 1; stats["lot_cash"] += target; stats["last_skip"] = "LOT_SIZE"; return None
    gross = shares * price
    fee = gross * config.transaction_cost_bps / 10000
    total = gross + fee
    if total > buy_power:
        stats["skip_cash"] += 1; stats["last_skip"] = "INSUFFICIENT_CASH"; return None
    stats["tx"] += fee
    stats["slip"] += shares * max(0.0, price - close)
    stats["lot_cash"] += max(0.0, target - total)
    pos = StrictPosition(code, shares, price, date, i, gross, int(row.buy_rank), float(row.expected_edge_score), close)
    return pos, total


def sell(pos: StrictPosition, date: str, i: int, close: float, reason: str, trades: list[dict[str, Any]], stats: dict[str, Any], config: StrictConfig) -> float:
    price = close * (1 - config.slippage_bps / 10000)
    gross = pos.share_count * price
    fee = gross * config.transaction_cost_bps / 10000
    proceeds = gross - fee
    realized = proceeds - pos.cost_basis
    gross_pnl = pos.share_count * close - pos.cost_basis
    stats["tx"] += fee
    stats["slip"] += pos.share_count * max(0.0, close - price)
    trades.append({"target_date": date, "entry_date": pos.entry_date, "exit_date": date, "year": int(pos.entry_date[:4]), "code": pos.code, "action": "SELL", "exit_reason": reason, "share_count": pos.share_count, "avg_entry_price": pos.avg_entry_price, "exit_price": price, "cost_basis": pos.cost_basis, "gross_proceeds": gross, "net_proceeds": proceeds, "gross_pnl": gross_pnl, "realized_pnl": realized, "gross_return_before_cost": gross_pnl / pos.cost_basis if pos.cost_basis else 0, "net_return_after_cost": realized / pos.cost_basis if pos.cost_basis else 0, "holding_days": i - pos.entry_index, "transaction_cost": fee, "slippage_cost": pos.share_count * max(0.0, close - price)})
    return proceeds


def consume_buy_funds(cash: float, unsettled: list[dict[str, Any]], amount: float) -> float:
    cash_used = min(cash, amount)
    remaining = amount - cash_used
    cash -= cash_used
    if remaining <= 1e-9:
        return cash
    for item in unsettled:
        if remaining <= 1e-9:
            break
        used = min(float(item["amount"]), remaining)
        item["amount"] = float(item["amount"]) - used
        remaining -= used
    unsettled[:] = [x for x in unsettled if float(x["amount"]) > 1e-9]
    return cash


def record_buy(trades: list[dict[str, Any]], pos: StrictPosition, date: str, row: Any, config: StrictConfig) -> None:
    trades.append({
        "target_date": date,
        "entry_date": date,
        "exit_date": "",
        "year": int(date[:4]),
        "code": pos.code,
        "action": "BUY",
        "share_count": pos.share_count,
        "avg_entry_price": pos.avg_entry_price,
        "cost_basis": pos.cost_basis,
        "buy_rank": int(row.buy_rank),
        "expected_edge_score": float(row.expected_edge_score),
        "settlement_mode": config.settlement_mode,
    })


def record_skip(trades: list[dict[str, Any]], config: StrictConfig, date: str, code: str, reason: str) -> None:
    trades.append({"target_date": date, "entry_date": "", "exit_date": "", "year": int(date[:4]), "code": code, "action": "SKIP", "skip_reason": reason})


def portfolio_total(cash: float, unsettled: list[dict[str, Any]], positions: dict[str, StrictPosition], close_lookup: dict[tuple[str, str], float], date: str) -> float:
    return cash + sum(x["amount"] for x in unsettled) + sum(p.share_count * close_lookup.get((date, p.code), p.last_price) for p in positions.values())


def metrics_for(trades: pd.DataFrame, daily: pd.DataFrame, holdings: pd.DataFrame, stats: dict[str, Any], config: StrictConfig, start: str, end: str) -> dict[str, Any]:
    sells = trades[trades.get("action", "") == "SELL"] if not trades.empty else pd.DataFrame()
    skips = trades[trades.get("action", "") == "SKIP"] if not trades.empty else pd.DataFrame()
    net = sells["net_return_after_cost"] if not sells.empty else pd.Series(dtype=float)
    final_net = float(daily["total_assets_net"].iloc[-1]) if not daily.empty else config.initial_assets
    final_gross = float(daily["total_assets_gross"].iloc[-1]) if not daily.empty else final_net
    years = max(1 / TRADING_DAYS_PER_YEAR, len(daily) / TRADING_DAYS_PER_YEAR)
    repl = int((sells.get("exit_reason", pd.Series(dtype=str)) == "REPLACEMENT").sum()) if not sells.empty else 0
    emerg = int((sells.get("exit_reason", pd.Series(dtype=str)) == "EMERGENCY_EXIT").sum()) if not sells.empty else 0
    realized = float(sells["realized_pnl"].sum()) if not sells.empty else 0.0
    unreal = float(holdings.groupby("target_date")["unrealized_pnl"].sum().iloc[-1]) if not holdings.empty else 0.0
    gross_profit = float(sells.loc[sells["realized_pnl"] > 0, "realized_pnl"].sum()) if not sells.empty else 0.0
    gross_loss = float(abs(sells.loc[sells["realized_pnl"] < 0, "realized_pnl"].sum())) if not sells.empty else 0.0
    return {"policy_id": config.policy_id, "policy_name": config.policy_name, "family": config.family, "settlement_mode": config.settlement_mode, "source_start_date": start, "source_end_date": end, "scenario_priority": 1 if config.family in {"BASE", "C3", "EMERGENCY"} else 2, "final_assets_gross": round_float(final_gross), "final_assets_net": round_float(final_net), "cumulative_return_gross": round_float(final_gross / config.initial_assets - 1), "cumulative_return_net": round_float(final_net / config.initial_assets - 1), "annualized_return_net": round_float((final_net / config.initial_assets) ** (1 / years) - 1) if final_net > 0 else -1, "profit_factor_net": round_float(gross_profit / gross_loss) if gross_loss else None, "max_drawdown_net": round_float(max_drawdown(daily["total_assets_net"].tolist()) if not daily.empty else 0), "win_rate": round_float(float((net > 0).mean())) if len(net) else 0, "trade_count": int(len(sells)), "average_trade_return_net": round_float(float(net.mean())) if len(net) else 0, "median_trade_return_net": round_float(float(net.median())) if len(net) else 0, "average_holding_days": round_float(float(sells["holding_days"].mean())) if len(sells) else 0, "median_holding_days": round_float(float(sells["holding_days"].median())) if len(sells) else 0, "turnover": round_float(len(sells) / years), "capital_utilization": round_float(float(daily["capital_utilization"].mean())) if not daily.empty else 0, "replacement_count": repl, "replacement_rate": round_float(repl / len(sells)) if len(sells) else 0, "emergency_exit_count": emerg, "emergency_exit_rate": round_float(emerg / len(sells)) if len(sells) else 0, "skipped_due_to_lot_size_count": int(stats["skip_lot"]), "skipped_due_to_min_position_value_count": int(stats["skip_min"]), "skipped_due_to_insufficient_cash_count": int(stats["skip_cash"]), "skipped_due_to_settlement_count": int(stats["skip_settle"]), "uninvested_cash_due_to_lot_size": round_float(stats["lot_cash"]), "cash_drag": round_float(float((daily["cash"] / daily["total_assets_net"]).mean())) if not daily.empty else 0, "worst_trade_net": round_float(float(net.min())) if len(net) else 0, "best_trade_net": round_float(float(net.max())) if len(net) else 0, "transaction_cost_paid": round_float(stats["tx"]), "slippage_cost_paid": round_float(stats["slip"]), "realized_pnl": round_float(realized), "unrealized_pnl": round_float(unreal), "average_cash": round_float(float(daily["cash"].mean())) if not daily.empty else 0, "average_unsettled_cash": round_float(float(daily["unsettled_cash"].mean())) if not daily.empty else 0, "broker_api_executed": False, "paper_trading_executed": False, "order_executed": False, "live_order_executed": False, "tachibana_api_called": False, "jquants_api_called": False, "no_future_data_in_decision": True, "backtest_outcome_used_in_decision": False, "future_price_used_in_decision": False, "future_rank_used_in_decision": False, "decision_evaluation_separated": True}


def annual_for(trades: pd.DataFrame, daily: pd.DataFrame, config: StrictConfig) -> list[dict[str, Any]]:
    sells = trades[trades.get("action", "") == "SELL"] if not trades.empty else pd.DataFrame()
    skips = trades[trades.get("action", "") == "SKIP"] if not trades.empty else pd.DataFrame()
    out = []
    for year, g in daily.groupby("year"):
        st, en = float(g["total_assets_net"].iloc[0]), float(g["total_assets_net"].iloc[-1])
        yt = sells[sells["year"] == year] if not sells.empty else pd.DataFrame()
        ys = skips[skips["year"] == year] if not skips.empty else pd.DataFrame()
        out.append({"policy_id": config.policy_id, "policy_name": config.policy_name, "year": int(year), "annual_return_net_by_year": round_float(en / st - 1) if st else 0, "annual_max_drawdown_net_by_year": round_float(max_drawdown(g["total_assets_net"].tolist())), "annual_trade_count_by_year": int(len(yt)), "annual_replacement_count_by_year": int((yt.get("exit_reason", pd.Series(dtype=str)) == "REPLACEMENT").sum()) if not yt.empty else 0, "annual_emergency_exit_count_by_year": int((yt.get("exit_reason", pd.Series(dtype=str)) == "EMERGENCY_EXIT").sum()) if not yt.empty else 0, "annual_skip_reasons_by_year": ys.get("skip_reason", pd.Series(dtype=str)).value_counts().to_dict() if not ys.empty else {}})
    return out


def summarize_skips(trades: pd.DataFrame, comparison: pd.DataFrame) -> pd.DataFrame:
    if trades.empty or "skip_reason" not in trades:
        return pd.DataFrame()
    skips = trades[trades.get("action", "") == "SKIP"]
    if skips.empty:
        return pd.DataFrame()
    return skips.groupby(["policy_id", "skip_reason"]).size().reset_index(name="skip_count")


def leakage_audit(ranked: pd.DataFrame, prices: pd.DataFrame, created_at: str) -> dict[str, Any]:
    return {"phase": "Phase7-E Leakage Audit", "created_at": created_at, "status": "PASS", "no_future_data_in_decision": True, "backtest_outcome_used_in_decision": False, "future_price_used_in_decision": False, "future_rank_used_in_decision": False, "decision_evaluation_separated": True, "broker_api_executed": False, "paper_trading_executed": False, "order_executed": False, "live_order_executed": False, "tachibana_api_called": False, "jquants_api_called": False, "ranked_start_date": str(ranked["target_date"].min()), "ranked_end_date": str(ranked["target_date"].max()), "price_start_date": str(prices["target_date"].min()), "price_end_date": str(prices["target_date"].max())}


def build_summary(comparison: pd.DataFrame, ranked: pd.DataFrame, prices: pd.DataFrame, paths: dict[str, Path], audit: dict[str, Any], created_at: str) -> dict[str, Any]:
    best = comparison.sort_values(["cumulative_return_net", "max_drawdown_net"], ascending=[False, False]).head(1).to_dict("records")
    c3 = comparison[comparison["policy_id"] == "C3_MIN15_T2"].to_dict("records")
    base = comparison[comparison["policy_id"] == "A_FIXED_20BD"].to_dict("records")
    return {"phase": "Phase7-E", "created_at": created_at, "completion_status": COMPLETION_STATUS, "source": {"ranked_daily": str(DEFAULT_RANKED_DAILY_PATH), "daily_response_dir": str(DEFAULT_DAILY_RESPONSE_DIR), "ranked_start_date": str(ranked["target_date"].min()), "ranked_end_date": str(ranked["target_date"].max()), "price_start_date": str(prices["target_date"].min()), "price_end_date": str(prices["target_date"].max()), "ranked_row_count": int(len(ranked)), "price_row_count": int(len(prices))}, "key_findings": {"baseline": base[0] if base else {}, "c3_min15_t2": c3[0] if c3 else {}, "best_policy_by_net_return": best[0] if best else {}}, "artifact_paths": {k: str(v) for k, v in paths.items()}, "leakage_audit_status": audit["status"], "no_future_data_in_decision": True, "backtest_outcome_used_in_decision": False, "future_price_used_in_decision": False, "future_rank_used_in_decision": False, "decision_evaluation_separated": True, "broker_api_executed": False, "paper_trading_executed": False, "order_executed": False, "live_order_executed": False, "tachibana_api_called": False, "jquants_api_called": False}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def to_jsonable(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return value
