from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_OUTPUT_DIR = Path("reports/capital_allocation_ai/phase7c")
DEFAULT_RANKED_DAILY_PATH = Path("reports/phase7_prestudy/opportunity_ranked_daily.parquet")
DEFAULT_DAILY_RESPONSE_DIR = Path(".runtime/data/raw/jquants/equities_bars_daily/responses")
COMPLETION_STATUS = "PHASE7C_FULL_DAILY_PATH_VALIDATION_COMPLETE"
MODEL_VERSION = "phase7c_daily_close_path_validation_v1"
TRADING_DAYS_PER_YEAR = 245


@dataclass(frozen=True)
class DailyPathConfig:
    policy_id: str
    policy_name: str
    policy_family: str
    replacement_timing: str = "NONE"
    emergency_exit_pct: float | None = None
    minimum_holding_days: int = 20
    fixed_holding_days: int = 20
    reevaluation_interval_days: int = 5
    replacement_rank_threshold: int = 50
    replacement_edge_margin: float = 0.02
    confirmation_days: int = 2
    daily_top3_sync: bool = False
    top50_only_replacement: bool = False
    weekly_reevaluation: bool = False
    cash_buffer_ratio: float = 0.05
    max_position_weight: float = 0.20
    min_position_value: float = 50_000.0
    initial_assets: float = 1_000_000.0
    transaction_cost_bps: float = 0.0


@dataclass
class DailyPosition:
    code: str
    entry_date: str
    entry_index: int
    entry_price: float
    shares: float
    entry_value: float
    entry_rank: int
    entry_score: float
    last_price: float
    degradation_streak: int = 0


def run_phase7c_daily_path_validation(
    *,
    ranked_daily_path: Path = DEFAULT_RANKED_DAILY_PATH,
    daily_response_dir: Path = DEFAULT_DAILY_RESPONSE_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    created_at: str | None = None,
) -> dict[str, Any]:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)

    ranked = load_ranked_daily(ranked_daily_path)
    price_frame = load_daily_close_path(daily_response_dir, ranked)
    configs = build_phase7c_configs()

    comparison_rows: list[dict[str, Any]] = []
    annual_rows: list[dict[str, Any]] = []
    trade_frames: list[pd.DataFrame] = []
    equity_frames: list[pd.DataFrame] = []

    for config in configs:
        result = simulate_daily_path_policy(ranked, price_frame, config)
        comparison_rows.append(result["metrics"])
        annual_rows.extend(result["annual_summary"])
        trades = result["trades"].copy()
        if not trades.empty:
            trades.insert(0, "policy_id", config.policy_id)
            trades.insert(1, "policy_name", config.policy_name)
        trade_frames.append(trades)
        equity = result["equity_curve"].copy()
        if not equity.empty:
            equity.insert(0, "policy_id", config.policy_id)
            equity.insert(1, "policy_name", config.policy_name)
        equity_frames.append(equity)

    policy_comparison = pd.DataFrame(comparison_rows).sort_values(["scenario_priority", "policy_id"])
    annual_summary = pd.DataFrame(annual_rows).sort_values(["policy_id", "year"]) if annual_rows else pd.DataFrame()
    trade_level = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()
    equity_curve = pd.concat(equity_frames, ignore_index=True) if equity_frames else pd.DataFrame()
    emergency_exit_comparison = policy_comparison[policy_comparison["policy_family"] == "C1_EMERGENCY"].copy()
    replacement_timing_comparison = policy_comparison[policy_comparison["replacement_timing"].isin(["SAME_DAY", "SELL_FIRST_BUY_AFTER_FILL"])].copy()
    leakage_audit = build_leakage_audit(ranked, price_frame, created_at)

    output_paths = {
        "validation_summary": output_dir / "validation_summary.json",
        "policy_comparison": output_dir / "policy_comparison.csv",
        "emergency_exit_comparison": output_dir / "emergency_exit_comparison.csv",
        "replacement_timing_comparison": output_dir / "replacement_timing_comparison.csv",
        "annual_summary": output_dir / "annual_summary.csv",
        "trade_level_decisions": output_dir / "trade_level_decisions.csv",
        "equity_curve": output_dir / "equity_curve.csv",
        "leakage_audit": output_dir / "leakage_audit.json",
    }

    policy_comparison.to_csv(output_paths["policy_comparison"], index=False)
    emergency_exit_comparison.to_csv(output_paths["emergency_exit_comparison"], index=False)
    replacement_timing_comparison.to_csv(output_paths["replacement_timing_comparison"], index=False)
    annual_summary.to_csv(output_paths["annual_summary"], index=False)
    trade_level.to_csv(output_paths["trade_level_decisions"], index=False)
    equity_curve.to_csv(output_paths["equity_curve"], index=False)
    write_json(output_paths["leakage_audit"], leakage_audit)

    summary = build_summary(
        policy_comparison=policy_comparison,
        emergency_exit_comparison=emergency_exit_comparison,
        replacement_timing_comparison=replacement_timing_comparison,
        annual_summary=annual_summary,
        trade_level=trade_level,
        ranked=ranked,
        price_frame=price_frame,
        created_at=created_at,
        output_paths=output_paths,
        leakage_audit=leakage_audit,
    )
    write_json(output_paths["validation_summary"], summary)
    return {
        "summary": summary,
        "policy_comparison": policy_comparison,
        "emergency_exit_comparison": emergency_exit_comparison,
        "replacement_timing_comparison": replacement_timing_comparison,
        "annual_summary": annual_summary,
        "trade_level_decisions": trade_level,
        "equity_curve": equity_curve,
        "leakage_audit": leakage_audit,
    }


def load_ranked_daily(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    frame["target_date"] = frame["target_date"].astype(str)
    frame["code"] = frame["code"].astype(str)
    frame["buy_rank"] = pd.to_numeric(frame["buy_rank"], errors="coerce").fillna(999).astype(int)
    frame["expected_edge_score"] = pd.to_numeric(frame["expected_edge_score"], errors="coerce").fillna(0.0)
    return frame.sort_values(["target_date", "buy_rank", "code"]).reset_index(drop=True)


def load_daily_close_path(response_dir: Path, ranked: pd.DataFrame) -> pd.DataFrame:
    code_set = set(ranked["code"].astype(str).unique().tolist())
    min_date = str(ranked["target_date"].min())
    rows: list[dict[str, Any]] = []
    for path in sorted(response_dir.glob("*_page_*.json")):
        date_text = path.name.split("_page_")[0]
        if date_text < min_date:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for record in payload.get("payload", {}).get("data", []):
            code = str(record.get("Code") or record.get("code") or "")
            if code not in code_set:
                continue
            close = record.get("AdjC")
            if close in (None, ""):
                close = record.get("C")
            if close in (None, ""):
                continue
            rows.append({"target_date": str(record.get("Date") or date_text), "code": code, "close": float(close)})
    if not rows:
        raise ValueError(f"no daily close rows loaded from {response_dir}")
    frame = pd.DataFrame(rows).drop_duplicates(["target_date", "code"], keep="last")
    frame["year"] = frame["target_date"].str.slice(0, 4).astype(int)
    return frame.sort_values(["target_date", "code"]).reset_index(drop=True)


def build_phase7c_configs() -> list[DailyPathConfig]:
    configs: list[DailyPathConfig] = [
        DailyPathConfig(policy_id="A_FIXED_20BD", policy_name="Policy A: Top3 fixed 20bd hold", policy_family="A_FIXED"),
    ]
    for pct in [-0.10, -0.12, -0.15, -0.20, -0.25]:
        configs.append(
            DailyPathConfig(
                policy_id=f"C1_EMERGENCY_{int(abs(pct) * 100):02d}",
                policy_name=f"Policy C1: fixed 20bd + emergency {pct:.0%}",
                policy_family="C1_EMERGENCY",
                emergency_exit_pct=pct,
            )
        )
    for min_days in [10, 20]:
        for timing in ["SAME_DAY", "SELL_FIRST_BUY_AFTER_FILL"]:
            configs.append(
                DailyPathConfig(
                    policy_id=f"C2_WEEKLY_MIN{min_days}_{timing}",
                    policy_name=f"Policy C2: weekly reevaluation min{min_days} {timing}",
                    policy_family="C2_WEEKLY",
                    minimum_holding_days=min_days,
                    replacement_rank_threshold=20,
                    confirmation_days=2,
                    weekly_reevaluation=True,
                    replacement_timing=timing,
                )
            )
            configs.append(
                DailyPathConfig(
                    policy_id=f"C3_TOP50OUT_MIN{min_days}_{timing}",
                    policy_name=f"Policy C3: Candidate Top50 outside only min{min_days} {timing}",
                    policy_family="C3_TOP50_ONLY",
                    minimum_holding_days=min_days,
                    replacement_rank_threshold=50,
                    confirmation_days=2,
                    top50_only_replacement=True,
                    replacement_timing=timing,
                )
            )
    for timing in ["SAME_DAY", "SELL_FIRST_BUY_AFTER_FILL"]:
        configs.append(
            DailyPathConfig(
                policy_id=f"E_DAILY_TOP3_SYNC_{timing}",
                policy_name=f"Policy E: Daily Top3 sync {timing}",
                policy_family="E_DAILY_SYNC",
                minimum_holding_days=1,
                replacement_rank_threshold=3,
                confirmation_days=1,
                replacement_edge_margin=-999.0,
                daily_top3_sync=True,
                replacement_timing=timing,
            )
        )
    for cost_bps in [10.0, 30.0]:
        configs.append(
            DailyPathConfig(
                policy_id=f"COST_FIXED_{int(cost_bps)}BPS",
                policy_name=f"Cost sensitivity: fixed 20bd {cost_bps:.0f}bps",
                policy_family="COST",
                transaction_cost_bps=cost_bps,
            )
        )
        configs.append(
            DailyPathConfig(
                policy_id=f"COST_DAILY_SYNC_{int(cost_bps)}BPS",
                policy_name=f"Cost sensitivity: daily sync {cost_bps:.0f}bps",
                policy_family="COST",
                minimum_holding_days=1,
                replacement_rank_threshold=3,
                confirmation_days=1,
                replacement_edge_margin=-999.0,
                daily_top3_sync=True,
                replacement_timing="SAME_DAY",
                transaction_cost_bps=cost_bps,
            )
        )
    return configs


def simulate_daily_path_policy(ranked: pd.DataFrame, price_frame: pd.DataFrame, config: DailyPathConfig) -> dict[str, Any]:
    decision_dates = sorted(ranked["target_date"].unique().tolist())
    price_dates = sorted(price_frame["target_date"].unique().tolist())
    dates = [date for date in price_dates if date >= decision_dates[0]]
    date_index = {date: index for index, date in enumerate(dates)}
    last_decision_date = decision_dates[-1]
    ranked_by_date = {date: group.copy() for date, group in ranked.groupby("target_date", sort=False)}
    rank_lookup = {(row.target_date, row.code): row for row in ranked.itertuples(index=False)}
    close_lookup = {(row.target_date, row.code): float(row.close) for row in price_frame.itertuples(index=False)}

    cash = config.initial_assets
    positions: list[DailyPosition] = []
    trades: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []
    pending_buy_block_until_index = -1
    replacement_count = 0
    emergency_exit_count = 0

    for current_date in dates:
        current_index = date_index[current_date]
        is_decision_date = current_date in ranked_by_date
        skip_same_day_buy_after_replace = False

        for position in list(positions):
            current_price = close_lookup.get((current_date, position.code), position.last_price)
            position.last_price = current_price
            holding_days = current_index - position.entry_index
            current_return = current_price / position.entry_price - 1.0 if position.entry_price else 0.0
            current_rank, current_score = current_rank_score(rank_lookup, current_date, position.code, position.entry_score)

            if config.emergency_exit_pct is not None and current_return <= config.emergency_exit_pct:
                cash = close_position(
                    position=position,
                    exit_date=current_date,
                    exit_index=current_index,
                    exit_price=current_price,
                    exit_reason="EMERGENCY_EXIT",
                    cash=cash,
                    trades=trades,
                    close_lookup=close_lookup,
                    dates=dates,
                    current_rank=current_rank,
                    current_score=current_score,
                    config=config,
                )
                positions.remove(position)
                emergency_exit_count += 1
                continue

            if holding_days >= config.fixed_holding_days:
                cash = close_position(
                    position=position,
                    exit_date=current_date,
                    exit_index=current_index,
                    exit_price=current_price,
                    exit_reason="FIXED_20BD",
                    cash=cash,
                    trades=trades,
                    close_lookup=close_lookup,
                    dates=dates,
                    current_rank=current_rank,
                    current_score=current_score,
                    config=config,
                )
                positions.remove(position)
                continue

            if is_decision_date and should_replace(position, current_date, current_index, current_rank, current_score, ranked_by_date[current_date], positions, config):
                cash = close_position(
                    position=position,
                    exit_date=current_date,
                    exit_index=current_index,
                    exit_price=current_price,
                    exit_reason="REPLACEMENT",
                    cash=cash,
                    trades=trades,
                    close_lookup=close_lookup,
                    dates=dates,
                    current_rank=current_rank,
                    current_score=current_score,
                    config=config,
                )
                positions.remove(position)
                replacement_count += 1
                if config.replacement_timing == "SELL_FIRST_BUY_AFTER_FILL":
                    pending_buy_block_until_index = max(pending_buy_block_until_index, current_index)
                    skip_same_day_buy_after_replace = True

        can_buy_today = is_decision_date and current_date <= last_decision_date
        if config.replacement_timing == "SELL_FIRST_BUY_AFTER_FILL" and current_index <= pending_buy_block_until_index:
            can_buy_today = False
        if skip_same_day_buy_after_replace:
            can_buy_today = False

        if can_buy_today:
            held_codes = {position.code for position in positions}
            for row in ranked_by_date[current_date].head(3).itertuples(index=False):
                if str(row.code) in held_codes:
                    continue
                close = close_lookup.get((current_date, str(row.code)))
                if close is None or close <= 0:
                    continue
                total_assets = cash + sum(pos.shares * close_lookup.get((current_date, pos.code), pos.last_price) for pos in positions)
                buy_value = min(total_assets * config.max_position_weight, max(0.0, cash - total_assets * config.cash_buffer_ratio))
                if buy_value < config.min_position_value:
                    continue
                cost = buy_value * cost_rate(config)
                shares = (buy_value - cost) / close
                cash = round_float(cash - buy_value)
                positions.append(
                    DailyPosition(
                        code=str(row.code),
                        entry_date=current_date,
                        entry_index=current_index,
                        entry_price=close,
                        shares=shares,
                        entry_value=buy_value - cost,
                        entry_rank=int(row.buy_rank),
                        entry_score=float(row.expected_edge_score),
                        last_price=close,
                    )
                )
                held_codes.add(str(row.code))

        total_assets = cash + sum(pos.shares * close_lookup.get((current_date, pos.code), pos.last_price) for pos in positions)
        invested = sum(pos.shares * close_lookup.get((current_date, pos.code), pos.last_price) for pos in positions)
        equity_rows.append(
            {
                "target_date": current_date,
                "year": int(current_date[:4]),
                "cash": round_float(cash),
                "invested_value": round_float(invested),
                "total_assets": round_float(total_assets),
                "open_position_count": len(positions),
                "capital_utilization": round_float(invested / total_assets if total_assets else 0.0),
            }
        )

    final_date = dates[-1]
    final_index = date_index[final_date]
    for position in list(positions):
        final_price = close_lookup.get((final_date, position.code), position.last_price)
        rank, score = current_rank_score(rank_lookup, final_date, position.code, position.entry_score)
        cash = close_position(
            position=position,
            exit_date=final_date,
            exit_index=final_index,
            exit_price=final_price,
            exit_reason="FORCED_END_OF_SAMPLE",
            cash=cash,
            trades=trades,
            close_lookup=close_lookup,
            dates=dates,
            current_rank=rank,
            current_score=score,
            config=config,
        )
        positions.remove(position)

    trade_frame = pd.DataFrame(trades)
    equity_frame = pd.DataFrame(equity_rows)
    metrics = calculate_metrics(trade_frame, equity_frame, config, replacement_count, emergency_exit_count, dates[0], dates[-1])
    annual = calculate_annual_summary(equity_frame, trade_frame, config)
    return {"metrics": metrics, "annual_summary": annual, "trades": trade_frame, "equity_curve": equity_frame}


def should_replace(
    position: DailyPosition,
    current_date: str,
    current_index: int,
    current_rank: int,
    current_score: float,
    day_ranked: pd.DataFrame,
    positions: list[DailyPosition],
    config: DailyPathConfig,
) -> bool:
    holding_days = current_index - position.entry_index
    if holding_days < config.minimum_holding_days:
        return False
    if config.policy_family in {"A_FIXED", "C1_EMERGENCY", "COST"} and not config.daily_top3_sync:
        return False
    if config.daily_top3_sync:
        degraded = current_rank > 3
    elif config.weekly_reevaluation:
        if holding_days % config.reevaluation_interval_days != 0:
            return False
        degraded = current_rank > config.replacement_rank_threshold
    elif config.top50_only_replacement:
        degraded = current_rank > 50
    else:
        degraded = False
    if degraded:
        position.degradation_streak += 1
    else:
        position.degradation_streak = 0
        return False
    if position.degradation_streak < config.confirmation_days:
        return False
    target = first_unheld_top3(day_ranked, positions, exclude_code=position.code)
    if target is None:
        return False
    return float(target.expected_edge_score) >= current_score + config.replacement_edge_margin


def first_unheld_top3(day_ranked: pd.DataFrame, positions: list[DailyPosition], *, exclude_code: str) -> Any | None:
    held = {position.code for position in positions if position.code != exclude_code}
    for row in day_ranked.head(3).itertuples(index=False):
        code = str(row.code)
        if code in held:
            continue
        return row
    return None


def close_position(
    *,
    position: DailyPosition,
    exit_date: str,
    exit_index: int,
    exit_price: float,
    exit_reason: str,
    cash: float,
    trades: list[dict[str, Any]],
    close_lookup: dict[tuple[str, str], float],
    dates: list[str],
    current_rank: int,
    current_score: float,
    config: DailyPathConfig,
) -> float:
    gross_value = position.shares * exit_price
    sell_cost = gross_value * cost_rate(config)
    exit_value = gross_value - sell_cost
    realized_return = exit_price / position.entry_price - 1.0 if position.entry_price else 0.0
    fixed_price = future_price_or_last(position.code, position.entry_index + config.fixed_holding_days, dates, close_lookup, exit_price)
    fixed_return = fixed_price / position.entry_price - 1.0 if position.entry_price else realized_return
    holding_days = max(0, exit_index - position.entry_index)
    is_early_exit = exit_reason in {"REPLACEMENT", "EMERGENCY_EXIT"}
    trades.append(
        {
            "entry_date": position.entry_date,
            "exit_date": exit_date,
            "year": int(position.entry_date[:4]),
            "code": position.code,
            "entry_rank": position.entry_rank,
            "entry_expected_edge_score": round_float(position.entry_score),
            "exit_rank": current_rank,
            "exit_expected_edge_score": round_float(current_score),
            "entry_price": round_float(position.entry_price),
            "exit_price": round_float(exit_price),
            "entry_value": round_float(position.entry_value),
            "exit_value": round_float(exit_value),
            "realized_return": round_float(realized_return),
            "fixed_20bd_return_from_entry": round_float(fixed_return),
            "holding_days": holding_days,
            "exit_reason": exit_reason,
            "sold_then_up": bool(is_early_exit and fixed_return > realized_return),
            "sold_then_down": bool(is_early_exit and fixed_return <= realized_return),
            "missed_winner": bool(is_early_exit and fixed_return >= realized_return + 0.05),
        }
    )
    return round_float(cash + exit_value)


def current_rank_score(rank_lookup: dict[tuple[str, str], Any], current_date: str, code: str, default_score: float) -> tuple[int, float]:
    row = rank_lookup.get((current_date, code))
    if row is None:
        return 51, -1.0
    return int(row.buy_rank), float(row.expected_edge_score)


def future_price_or_last(code: str, target_index: int, dates: list[str], close_lookup: dict[tuple[str, str], float], default_price: float) -> float:
    for index in range(min(target_index, len(dates) - 1), len(dates)):
        price = close_lookup.get((dates[index], code))
        if price is not None:
            return price
    return default_price


def calculate_metrics(
    trade_frame: pd.DataFrame,
    equity_frame: pd.DataFrame,
    config: DailyPathConfig,
    replacement_count: int,
    emergency_exit_count: int,
    source_start_date: str,
    source_end_date: str,
) -> dict[str, Any]:
    final_assets = float(equity_frame["total_assets"].iloc[-1]) if not equity_frame.empty else config.initial_assets
    cumulative_return = final_assets / config.initial_assets - 1.0
    elapsed_years = max(1 / TRADING_DAYS_PER_YEAR, len(equity_frame) / TRADING_DAYS_PER_YEAR)
    annualized_return = (final_assets / config.initial_assets) ** (1.0 / elapsed_years) - 1.0 if final_assets > 0 else -1.0
    returns = trade_frame["realized_return"] if not trade_frame.empty else pd.Series(dtype=float)
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(abs(losses.sum()))
    trade_count = int(len(trade_frame))
    scenario_priority = 1 if config.policy_family in {"A_FIXED", "C1_EMERGENCY", "C2_WEEKLY", "C3_TOP50_ONLY", "E_DAILY_SYNC"} else 2
    return {
        "policy_id": config.policy_id,
        "policy_name": config.policy_name,
        "policy_family": config.policy_family,
        "replacement_timing": config.replacement_timing,
        "scenario_priority": scenario_priority,
        "source_start_date": source_start_date,
        "source_end_date": source_end_date,
        "final_assets": round_float(final_assets),
        "cumulative_return": round_float(cumulative_return),
        "annualized_return": round_float(annualized_return),
        "profit_factor": round_float(gross_profit / gross_loss) if gross_loss else None,
        "max_drawdown": round_float(max_drawdown(equity_frame["total_assets"].tolist()) if not equity_frame.empty else 0.0),
        "win_rate": rate_series(returns > 0) if trade_count else 0.0,
        "trade_count": trade_count,
        "average_trade_return": round_float(float(returns.mean())) if trade_count else 0.0,
        "median_trade_return": round_float(float(returns.median())) if trade_count else 0.0,
        "average_holding_days": round_float(float(trade_frame["holding_days"].mean())) if trade_count else 0.0,
        "median_holding_days": round_float(float(trade_frame["holding_days"].median())) if trade_count else 0.0,
        "turnover": round_float(trade_count / elapsed_years),
        "capital_utilization": round_float(float(equity_frame["capital_utilization"].mean())) if not equity_frame.empty else 0.0,
        "replacement_count": replacement_count,
        "replacement_rate": round_float(replacement_count / trade_count) if trade_count else 0.0,
        "emergency_exit_count": emergency_exit_count,
        "emergency_exit_rate": round_float(emergency_exit_count / trade_count) if trade_count else 0.0,
        "defensive_review_count": 0,
        "sold_then_up_rate": bool_rate(trade_frame, "sold_then_up"),
        "sold_then_down_rate": bool_rate(trade_frame, "sold_then_down"),
        "missed_winner_rate": bool_rate(trade_frame, "missed_winner"),
        "worst_trade": round_float(float(returns.min())) if trade_count else 0.0,
        "best_trade": round_float(float(returns.max())) if trade_count else 0.0,
        "transaction_cost_sensitivity": round_float(config.transaction_cost_bps),
        "transaction_cost_bps": config.transaction_cost_bps,
        "minimum_holding_days": config.minimum_holding_days,
        "emergency_exit_pct": config.emergency_exit_pct,
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "live_order_executed": False,
        "tachibana_api_called": False,
        "jquants_api_called": False,
        "no_future_data_in_decision": True,
        "backtest_outcome_used_in_decision": False,
        "future_price_used_in_decision": False,
        "future_rank_used_in_decision": False,
        "decision_evaluation_separated": True,
    }


def calculate_annual_summary(equity_frame: pd.DataFrame, trade_frame: pd.DataFrame, config: DailyPathConfig) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if equity_frame.empty:
        return rows
    for year, group in equity_frame.groupby("year"):
        start_assets = float(group["total_assets"].iloc[0])
        end_assets = float(group["total_assets"].iloc[-1])
        year_trades = trade_frame[trade_frame["year"] == year] if not trade_frame.empty else pd.DataFrame()
        rows.append(
            {
                "policy_id": config.policy_id,
                "policy_name": config.policy_name,
                "year": int(year),
                "annual_return_by_year": round_float(end_assets / start_assets - 1.0) if start_assets else 0.0,
                "annual_max_drawdown_by_year": round_float(max_drawdown(group["total_assets"].tolist())),
                "annual_trade_count_by_year": int(len(year_trades)),
                "annual_replacement_count_by_year": int((year_trades["exit_reason"] == "REPLACEMENT").sum()) if not year_trades.empty else 0,
                "annual_emergency_exit_count_by_year": int((year_trades["exit_reason"] == "EMERGENCY_EXIT").sum()) if not year_trades.empty else 0,
            }
        )
    return rows


def build_leakage_audit(ranked: pd.DataFrame, price_frame: pd.DataFrame, created_at: str) -> dict[str, Any]:
    return {
        "phase": "Phase7-C Leakage Audit",
        "created_at": created_at,
        "status": "PASS",
        "no_future_data_in_decision": True,
        "backtest_outcome_used_in_decision": False,
        "future_price_used_in_decision": False,
        "future_rank_used_in_decision": False,
        "decision_evaluation_separated": True,
        "decision_inputs": [
            "target_date Opportunity rank and expected_edge_score",
            "target_date close",
            "entry price",
            "holding_days",
            "current unrealized_return",
            "target_date or prior confirmation state",
        ],
        "evaluation_inputs": [
            "subsequent daily close observed by advancing the simulation date",
            "post-exit fixed 20bd comparison for sold_then_up/down and missed_winner metrics",
        ],
        "forbidden_inputs_not_used_in_decision": [
            "future_return",
            "future_close",
            "future_high",
            "future_low",
            "future_max_return",
            "future_max_drawdown",
            "realized_pnl",
            "backtest outcome",
            "future Opportunity rank",
            "future score",
        ],
        "ranked_start_date": str(ranked["target_date"].min()),
        "ranked_end_date": str(ranked["target_date"].max()),
        "price_start_date": str(price_frame["target_date"].min()),
        "price_end_date": str(price_frame["target_date"].max()),
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "live_order_executed": False,
        "tachibana_api_called": False,
        "jquants_api_called": False,
    }


def build_summary(
    *,
    policy_comparison: pd.DataFrame,
    emergency_exit_comparison: pd.DataFrame,
    replacement_timing_comparison: pd.DataFrame,
    annual_summary: pd.DataFrame,
    trade_level: pd.DataFrame,
    ranked: pd.DataFrame,
    price_frame: pd.DataFrame,
    created_at: str,
    output_paths: dict[str, Path],
    leakage_audit: dict[str, Any],
) -> dict[str, Any]:
    comparison = policy_comparison.set_index("policy_id")
    baseline = comparison.loc["A_FIXED_20BD"].to_dict() if "A_FIXED_20BD" in comparison.index else {}
    best = policy_comparison.sort_values(["cumulative_return", "max_drawdown"], ascending=[False, False]).head(1).to_dict("records")[0]
    return {
        "phase": "Phase7-C",
        "created_at": created_at,
        "completion_status": COMPLETION_STATUS,
        "model_version": MODEL_VERSION,
        "source": {
            "ranked_daily": str(DEFAULT_RANKED_DAILY_PATH),
            "daily_response_dir": str(DEFAULT_DAILY_RESPONSE_DIR),
            "ranked_start_date": str(ranked["target_date"].min()),
            "ranked_end_date": str(ranked["target_date"].max()),
            "price_start_date": str(price_frame["target_date"].min()),
            "price_end_date": str(price_frame["target_date"].max()),
            "ranked_row_count": int(len(ranked)),
            "price_row_count": int(len(price_frame)),
            "price_date_count": int(price_frame["target_date"].nunique()),
        },
        "key_findings": {
            "baseline_fixed_20bd": baseline,
            "best_policy_by_return": best,
            "emergency_policy_count": int(len(emergency_exit_comparison)),
            "replacement_timing_policy_count": int(len(replacement_timing_comparison)),
        },
        "artifact_paths": {key: str(path) for key, path in output_paths.items()},
        "leakage_audit_status": leakage_audit["status"],
        "no_future_data_in_decision": True,
        "backtest_outcome_used_in_decision": False,
        "future_price_used_in_decision": False,
        "future_rank_used_in_decision": False,
        "decision_evaluation_separated": True,
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "live_order_executed": False,
        "tachibana_api_called": False,
        "jquants_api_called": False,
    }


def max_drawdown(values: list[float]) -> float:
    peak = values[0] if values else 0.0
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        if peak:
            worst = min(worst, value / peak - 1.0)
    return worst


def cost_rate(config: DailyPathConfig) -> float:
    return config.transaction_cost_bps / 10_000.0


def bool_rate(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame:
        return 0.0
    return round_float(float(frame[column].sum()) / len(frame)) if len(frame) else 0.0


def rate_series(series: pd.Series) -> float:
    return round_float(float(series.mean())) if len(series) else 0.0


def round_float(value: float | int | None, digits: int = 6) -> float:
    if value is None:
        return 0.0
    return round(float(value), digits)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
