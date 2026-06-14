from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_OUTPUT_DIR = Path("reports/capital_allocation_ai/phase7b")
DEFAULT_RANKED_DAILY_PATH = Path("reports/phase7_prestudy/opportunity_ranked_daily.parquet")
DEFAULT_OPPORTUNITY_DATASET_PATH = Path("reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet")

COMPLETION_STATUS = "PHASE7B_CONSERVATIVE_REPLACEMENT_VALIDATION_COMPLETE"
MODEL_VERSION = "phase7b_lightweight_forward_label_validation_v1"
TRADING_DAYS_PER_YEAR = 245


@dataclass(frozen=True)
class ValidationConfig:
    policy_id: str
    policy_name: str
    minimum_holding_days: int = 5
    replacement_rank_degradation_threshold: int = 20
    replacement_edge_margin: float = 0.02
    confirmation_days: int = 2
    emergency_exit_pct: float | None = None
    defensive_review_enabled: bool = False
    daily_top3_sync: bool = False
    cash_buffer_ratio: float = 0.05
    max_position_weight: float = 0.20
    min_position_value: float = 50_000.0
    initial_assets: float = 1_000_000.0
    fixed_holding_days: int = 20
    transaction_cost_bps: float = 0.0


@dataclass
class OpenPosition:
    code: str
    entry_date: str
    entry_index: int
    entry_value: float
    entry_score: float
    entry_rank: int
    future_return_20d: float
    future_max_return_20d: float
    future_max_drawdown_20d: float
    downside_bad_20d: bool
    degradation_streak: int = 0
    defensive_review_recorded: bool = False


def run_phase7b_validation(
    *,
    ranked_daily_path: Path = DEFAULT_RANKED_DAILY_PATH,
    opportunity_dataset_path: Path = DEFAULT_OPPORTUNITY_DATASET_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    created_at: str | None = None,
) -> dict[str, Any]:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)

    ranked = load_validation_frame(ranked_daily_path, opportunity_dataset_path)
    configs = build_validation_configs()

    comparison_rows: list[dict[str, Any]] = []
    annual_rows: list[dict[str, Any]] = []
    trade_frames: list[pd.DataFrame] = []
    equity_frames: list[pd.DataFrame] = []

    for config in configs:
        result = simulate_policy(ranked, config)
        metrics = result["metrics"]
        comparison_rows.append(metrics)
        annual_rows.extend(result["annual_summary"])
        trade_frame = result["trades"].copy()
        if not trade_frame.empty:
            trade_frame.insert(0, "policy_id", config.policy_id)
            trade_frame.insert(1, "policy_name", config.policy_name)
        trade_frames.append(trade_frame)
        equity_frame = result["equity_curve"].copy()
        if not equity_frame.empty:
            equity_frame.insert(0, "policy_id", config.policy_id)
            equity_frame.insert(1, "policy_name", config.policy_name)
        equity_frames.append(equity_frame)

    policy_comparison = pd.DataFrame(comparison_rows).sort_values(["scenario_priority", "policy_id"])
    annual_summary = pd.DataFrame(annual_rows).sort_values(["policy_id", "year"]) if annual_rows else pd.DataFrame()
    trade_level = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()
    equity_curve = pd.concat(equity_frames, ignore_index=True) if equity_frames else pd.DataFrame()
    parameter_grid = policy_comparison[policy_comparison["scenario_priority"] > 1].copy()

    output_paths = {
        "validation_summary": output_dir / "validation_summary.json",
        "policy_comparison": output_dir / "policy_comparison.csv",
        "parameter_grid_summary": output_dir / "parameter_grid_summary.csv",
        "annual_summary": output_dir / "annual_summary.csv",
        "trade_level_decisions": output_dir / "trade_level_decisions.csv",
        "equity_curve": output_dir / "equity_curve.csv",
    }

    policy_comparison.to_csv(output_paths["policy_comparison"], index=False)
    parameter_grid.to_csv(output_paths["parameter_grid_summary"], index=False)
    annual_summary.to_csv(output_paths["annual_summary"], index=False)
    trade_level.to_csv(output_paths["trade_level_decisions"], index=False)
    equity_curve.to_csv(output_paths["equity_curve"], index=False)

    summary = build_summary(
        policy_comparison=policy_comparison,
        annual_summary=annual_summary,
        trade_level=trade_level,
        ranked=ranked,
        created_at=created_at,
        output_paths=output_paths,
    )
    write_json(output_paths["validation_summary"], summary)
    return {
        "summary": summary,
        "policy_comparison": policy_comparison,
        "annual_summary": annual_summary,
        "trade_level_decisions": trade_level,
        "equity_curve": equity_curve,
    }


def load_validation_frame(ranked_daily_path: Path, opportunity_dataset_path: Path) -> pd.DataFrame:
    ranked = pd.read_parquet(ranked_daily_path)
    labels = pd.read_parquet(opportunity_dataset_path)
    ranked["target_date"] = ranked["target_date"].astype(str)
    ranked["code"] = ranked["code"].astype(str)
    labels["target_date"] = labels["target_date"].astype(str)
    labels["code"] = labels["code"].astype(str)
    label_columns = [
        "target_date",
        "code",
        "label__future_return_20d",
        "label__future_max_return_20d",
        "label__future_max_drawdown_20d",
        "label__downside_bad_20d",
    ]
    frame = ranked.merge(labels[label_columns], on=["target_date", "code"], how="left")
    frame["year"] = pd.to_datetime(frame["target_date"]).dt.year
    for column in ["label__future_return_20d", "label__future_max_return_20d", "label__future_max_drawdown_20d"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    frame["label__downside_bad_20d"] = frame["label__downside_bad_20d"].fillna(False).astype(bool)
    return frame.sort_values(["target_date", "buy_rank", "code"]).reset_index(drop=True)


def build_validation_configs() -> list[ValidationConfig]:
    configs = [
        ValidationConfig(
            policy_id="A_FIXED_20BD",
            policy_name="Baseline A: Top3 fixed 20bd hold",
            minimum_holding_days=20,
            replacement_rank_degradation_threshold=999,
            replacement_edge_margin=999.0,
            confirmation_days=999,
            emergency_exit_pct=None,
            defensive_review_enabled=False,
        ),
        ValidationConfig(
            policy_id="B_PHASE7A_DEFAULT",
            policy_name="Policy B: Phase7-A conservative replacement",
        ),
    ]
    for pct in [-0.10, -0.12, -0.15, -0.20, -0.25]:
        configs.append(
            ValidationConfig(
                policy_id=f"C_EMERGENCY_{int(abs(pct) * 100):02d}",
                policy_name=f"Policy C: default + emergency {pct:.0%}",
                emergency_exit_pct=pct,
            )
        )
    configs.append(
        ValidationConfig(
            policy_id="D_DEFENSIVE_REVIEW",
            policy_name="Policy D: default + emergency -15% + defensive review",
            emergency_exit_pct=-0.15,
            defensive_review_enabled=True,
        )
    )
    configs.append(
        ValidationConfig(
            policy_id="E_DAILY_TOP3_SYNC",
            policy_name="Policy E: Daily Top3 sync replacement reference",
            minimum_holding_days=1,
            replacement_rank_degradation_threshold=3,
            replacement_edge_margin=-999.0,
            confirmation_days=1,
            daily_top3_sync=True,
        )
    )
    for cost_bps in [10.0, 30.0]:
        configs.append(
            ValidationConfig(
                policy_id=f"COST_DEFAULT_{int(cost_bps)}BPS",
                policy_name=f"Cost sensitivity: Phase7-A default {cost_bps:.0f}bps",
                transaction_cost_bps=cost_bps,
            )
        )
        configs.append(
            ValidationConfig(
                policy_id=f"COST_DAILY_SYNC_{int(cost_bps)}BPS",
                policy_name=f"Cost sensitivity: Daily Top3 sync {cost_bps:.0f}bps",
                minimum_holding_days=1,
                replacement_rank_degradation_threshold=3,
                replacement_edge_margin=-999.0,
                confirmation_days=1,
                daily_top3_sync=True,
                transaction_cost_bps=cost_bps,
            )
        )

    for days in [5, 10, 20]:
        configs.append(ValidationConfig(policy_id=f"GRID_MIN_HOLD_{days}", policy_name=f"Grid: minimum_holding_days={days}", minimum_holding_days=days))
    for days in [1, 2, 3]:
        configs.append(ValidationConfig(policy_id=f"GRID_CONFIRM_{days}", policy_name=f"Grid: confirmation_days={days}", confirmation_days=days))
    for margin in [0.00, 0.01, 0.02, 0.03]:
        configs.append(
            ValidationConfig(
                policy_id=f"GRID_EDGE_{int(margin * 100):02d}",
                policy_name=f"Grid: replacement_edge_margin={margin:.2f}",
                replacement_edge_margin=margin,
            )
        )
    for threshold in [10, 20, 50]:
        configs.append(
            ValidationConfig(
                policy_id=f"GRID_RANK_GT_{threshold}",
                policy_name=f"Grid: replacement_rank_degradation_threshold>{threshold}",
                replacement_rank_degradation_threshold=threshold,
            )
        )
    for buffer in [0.00, 0.05]:
        for weight in [0.20, 0.15, 0.10]:
            configs.append(
                ValidationConfig(
                    policy_id=f"GRID_CASH_{int(buffer * 100):02d}_WEIGHT_{int(weight * 100):02d}",
                    policy_name=f"Grid: cash_buffer={buffer:.0%}, max_position_weight={weight:.0%}",
                    cash_buffer_ratio=buffer,
                    max_position_weight=weight,
                )
            )
    return dedupe_configs(configs)


def dedupe_configs(configs: list[ValidationConfig]) -> list[ValidationConfig]:
    seen: set[str] = set()
    out: list[ValidationConfig] = []
    for config in configs:
        if config.policy_id in seen:
            continue
        seen.add(config.policy_id)
        out.append(config)
    return out


def simulate_policy(frame: pd.DataFrame, config: ValidationConfig) -> dict[str, Any]:
    dates = sorted(frame["target_date"].unique().tolist())
    date_index = {date: index for index, date in enumerate(dates)}
    by_date = {date: day.copy() for date, day in frame.groupby("target_date", sort=False)}
    row_lookup = {(str(row.target_date), str(row.code)): row for row in frame.itertuples(index=False)}

    cash = config.initial_assets
    open_positions: list[OpenPosition] = []
    trades: list[dict[str, Any]] = []
    equity_points: list[dict[str, Any]] = []
    defensive_review_count = 0
    replacement_count = 0
    emergency_exit_count = 0
    buy_count = 0

    for current_index, current_date in enumerate(dates):
        exits: list[OpenPosition] = []
        for position in list(open_positions):
            holding_days = current_index - position.entry_index
            row = row_lookup.get((current_date, position.code))
            current_rank = int(getattr(row, "buy_rank", 51)) if row is not None else 51
            current_score = float(getattr(row, "expected_edge_score", position.entry_score)) if row is not None else position.entry_score - 1.0
            downside_bad = bool(getattr(row, "label__downside_bad_20d", False)) if row is not None else False

            if config.defensive_review_enabled and not position.defensive_review_recorded and downside_bad:
                defensive_review_count += 1
                position.defensive_review_recorded = True

            if config.emergency_exit_pct is not None and position.future_max_drawdown_20d <= config.emergency_exit_pct:
                cash = close_position(
                    position=position,
                    exit_date=current_date,
                    exit_index=current_index,
                    realized_return=config.emergency_exit_pct,
                    exit_reason="EMERGENCY_EXIT",
                    cash=cash,
                    trades=trades,
                    config=config,
                    current_rank=current_rank,
                    current_score=current_score,
                    replacement_target_code="",
                )
                open_positions.remove(position)
                emergency_exit_count += 1
                continue

            if holding_days >= config.fixed_holding_days:
                exits.append(position)
                continue

            if should_replace_position(position, current_rank, current_score, holding_days, by_date[current_date], open_positions, config):
                target = first_replacement_target(by_date[current_date], open_positions, exclude_code=position.code)
                if target is not None:
                    realized = interpolate_return(position.future_return_20d, holding_days)
                    cash = close_position(
                        position=position,
                        exit_date=current_date,
                        exit_index=current_index,
                        realized_return=realized,
                        exit_reason="REPLACEMENT",
                        cash=cash,
                        trades=trades,
                        config=config,
                        current_rank=current_rank,
                        current_score=current_score,
                        replacement_target_code=str(target.code),
                    )
                    open_positions.remove(position)
                    replacement_count += 1
                    buy = open_new_position(target, current_date, current_index, cash, config)
                    if buy is not None:
                        position_new, buy_value = buy
                        open_positions.append(position_new)
                        cash -= buy_value
                        buy_count += 1
                    continue

        for position in exits:
            if position not in open_positions:
                continue
            cash = close_position(
                position=position,
                exit_date=current_date,
                exit_index=current_index,
                realized_return=position.future_return_20d,
                exit_reason="FIXED_20BD",
                cash=cash,
                trades=trades,
                config=config,
                current_rank=rank_for(row_lookup, current_date, position.code),
                current_score=score_for(row_lookup, current_date, position.code, position.entry_score),
                replacement_target_code="",
            )
            open_positions.remove(position)

        held_codes = {position.code for position in open_positions}
        for candidate in by_date[current_date].head(3).itertuples(index=False):
            if str(candidate.code) in held_codes:
                continue
            buy = open_new_position(candidate, current_date, current_index, cash, config)
            if buy is None:
                continue
            position, buy_value = buy
            open_positions.append(position)
            cash -= buy_value
            held_codes.add(position.code)
            buy_count += 1

        total_assets = cash + sum(mark_to_market_value(position, current_index) for position in open_positions)
        invested_value = sum(position.entry_value for position in open_positions)
        equity_points.append(
            {
                "target_date": current_date,
                "year": year_from_date(current_date),
                "cash": round_float(cash),
                "open_position_count": len(open_positions),
                "invested_value": round_float(invested_value),
                "total_assets": round_float(total_assets),
                "capital_utilization": round_float(invested_value / total_assets if total_assets else 0.0),
            }
        )

    final_date = dates[-1]
    final_index = len(dates) - 1
    for position in list(open_positions):
        holding_days = final_index - position.entry_index
        cash = close_position(
            position=position,
            exit_date=final_date,
            exit_index=final_index,
            realized_return=interpolate_return(position.future_return_20d, holding_days),
            exit_reason="FORCED_END_OF_SAMPLE",
            cash=cash,
            trades=trades,
            config=config,
            current_rank=rank_for(row_lookup, final_date, position.code),
            current_score=score_for(row_lookup, final_date, position.code, position.entry_score),
            replacement_target_code="",
        )
        open_positions.remove(position)

    trade_frame = pd.DataFrame(trades)
    equity_frame = pd.DataFrame(equity_points)
    metrics = calculate_metrics(
        trade_frame=trade_frame,
        equity_frame=equity_frame,
        config=config,
        defensive_review_count=defensive_review_count,
        replacement_count=replacement_count,
        emergency_exit_count=emergency_exit_count,
        buy_count=buy_count,
        source_start_date=dates[0],
        source_end_date=dates[-1],
    )
    annual = calculate_annual_summary(equity_frame, trade_frame, config)
    return {"metrics": metrics, "annual_summary": annual, "trades": trade_frame, "equity_curve": equity_frame}


def should_replace_position(
    position: OpenPosition,
    current_rank: int,
    current_score: float,
    holding_days: int,
    day_frame: pd.DataFrame,
    open_positions: list[OpenPosition],
    config: ValidationConfig,
) -> bool:
    if holding_days < config.minimum_holding_days:
        return False
    degraded = current_rank > config.replacement_rank_degradation_threshold
    if degraded:
        position.degradation_streak += 1
    else:
        position.degradation_streak = 0
        return False
    if position.degradation_streak < config.confirmation_days:
        return False
    target = first_replacement_target(day_frame, open_positions, exclude_code=position.code)
    if target is None:
        return False
    target_score = float(target.expected_edge_score)
    return target_score >= current_score + config.replacement_edge_margin


def first_replacement_target(day_frame: pd.DataFrame, open_positions: list[OpenPosition], *, exclude_code: str) -> Any | None:
    held = {position.code for position in open_positions if position.code != exclude_code}
    for row in day_frame.head(3).itertuples(index=False):
        code = str(row.code)
        if code in held:
            continue
        return row
    return None


def open_new_position(row: Any, current_date: str, current_index: int, cash: float, config: ValidationConfig) -> tuple[OpenPosition, float] | None:
    total_assets_proxy = max(config.initial_assets, cash)
    cash_buffer = total_assets_proxy * config.cash_buffer_ratio
    available_cash = max(0.0, cash - cash_buffer)
    target_value = total_assets_proxy * config.max_position_weight
    buy_value = min(target_value, available_cash)
    if buy_value < config.min_position_value:
        return None
    cost = buy_value * cost_rate(config)
    position = OpenPosition(
        code=str(row.code),
        entry_date=current_date,
        entry_index=current_index,
        entry_value=round_float(buy_value - cost),
        entry_score=float(row.expected_edge_score),
        entry_rank=int(row.buy_rank),
        future_return_20d=float(row.label__future_return_20d),
        future_max_return_20d=float(row.label__future_max_return_20d),
        future_max_drawdown_20d=float(row.label__future_max_drawdown_20d),
        downside_bad_20d=bool(row.label__downside_bad_20d),
    )
    return position, buy_value


def close_position(
    *,
    position: OpenPosition,
    exit_date: str,
    exit_index: int,
    realized_return: float,
    exit_reason: str,
    cash: float,
    trades: list[dict[str, Any]],
    config: ValidationConfig,
    current_rank: int,
    current_score: float,
    replacement_target_code: str,
) -> float:
    holding_days = max(0, exit_index - position.entry_index)
    gross_exit_value = position.entry_value * (1.0 + realized_return)
    sell_cost = gross_exit_value * cost_rate(config)
    exit_value = gross_exit_value - sell_cost
    fixed_return = position.future_return_20d
    trades.append(
        {
            "entry_date": position.entry_date,
            "exit_date": exit_date,
            "year": year_from_date(position.entry_date),
            "code": position.code,
            "entry_rank": position.entry_rank,
            "entry_expected_edge_score": round_float(position.entry_score),
            "exit_rank": current_rank,
            "exit_expected_edge_score": round_float(current_score),
            "entry_value": round_float(position.entry_value),
            "exit_value": round_float(exit_value),
            "realized_return": round_float(realized_return),
            "fixed_20bd_return": round_float(fixed_return),
            "future_max_return_20d": round_float(position.future_max_return_20d),
            "future_max_drawdown_20d": round_float(position.future_max_drawdown_20d),
            "holding_days": holding_days,
            "exit_reason": exit_reason,
            "replacement_target_code": replacement_target_code,
            "sold_then_up": bool(exit_reason in {"REPLACEMENT", "EMERGENCY_EXIT"} and fixed_return > realized_return),
            "sold_then_down": bool(exit_reason in {"REPLACEMENT", "EMERGENCY_EXIT"} and fixed_return <= realized_return),
            "early_exit_loss": bool(exit_reason in {"REPLACEMENT", "EMERGENCY_EXIT"} and realized_return < 0),
            "missed_winner": bool(exit_reason in {"REPLACEMENT", "EMERGENCY_EXIT"} and fixed_return >= realized_return + 0.05),
        }
    )
    return round_float(cash + exit_value)


def calculate_metrics(
    *,
    trade_frame: pd.DataFrame,
    equity_frame: pd.DataFrame,
    config: ValidationConfig,
    defensive_review_count: int,
    replacement_count: int,
    emergency_exit_count: int,
    buy_count: int,
    source_start_date: str,
    source_end_date: str,
) -> dict[str, Any]:
    final_assets = float(equity_frame["total_assets"].iloc[-1]) if not equity_frame.empty else config.initial_assets
    cumulative_return = final_assets / config.initial_assets - 1.0
    elapsed_years = max(1 / TRADING_DAYS_PER_YEAR, len(equity_frame) / TRADING_DAYS_PER_YEAR)
    annualized = (final_assets / config.initial_assets) ** (1.0 / elapsed_years) - 1.0 if final_assets > 0 else -1.0
    returns = trade_frame["realized_return"] if not trade_frame.empty else pd.Series(dtype=float)
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(abs(losses.sum()))
    trade_count = int(len(trade_frame))
    max_dd = max_drawdown(equity_frame["total_assets"].tolist()) if not equity_frame.empty else 0.0
    scenario_priority = 1 if config.policy_id in {"A_FIXED_20BD", "B_PHASE7A_DEFAULT", "D_DEFENSIVE_REVIEW", "E_DAILY_TOP3_SYNC"} or config.policy_id.startswith("C_EMERGENCY") else 2
    return {
        "policy_id": config.policy_id,
        "policy_name": config.policy_name,
        "scenario_priority": scenario_priority,
        "source_start_date": source_start_date,
        "source_end_date": source_end_date,
        "final_assets": round_float(final_assets),
        "cumulative_return": round_float(cumulative_return),
        "annualized_return": round_float(annualized),
        "profit_factor": round_float(gross_profit / gross_loss) if gross_loss else None,
        "max_drawdown": round_float(max_dd),
        "win_rate": round_float(float((returns > 0).mean())) if trade_count else 0.0,
        "trade_count": trade_count,
        "average_trade_return": round_float(float(returns.mean())) if trade_count else 0.0,
        "average_holding_days": round_float(float(trade_frame["holding_days"].mean())) if trade_count else 0.0,
        "median_holding_days": round_float(float(trade_frame["holding_days"].median())) if trade_count else 0.0,
        "turnover": round_float(trade_count / elapsed_years),
        "capital_utilization": round_float(float(equity_frame["capital_utilization"].mean())) if not equity_frame.empty else 0.0,
        "replacement_count": replacement_count,
        "replacement_rate": round_float(replacement_count / trade_count) if trade_count else 0.0,
        "emergency_exit_count": emergency_exit_count,
        "defensive_review_count": defensive_review_count,
        "sold_then_up_rate": rate(trade_frame, "sold_then_up"),
        "sold_then_down_rate": rate(trade_frame, "sold_then_down"),
        "early_exit_loss_count": int(trade_frame["early_exit_loss"].sum()) if not trade_frame.empty else 0,
        "missed_winner_rate": rate(trade_frame, "missed_winner"),
        "transaction_cost_bps": config.transaction_cost_bps,
        "transaction_cost_sensitivity": round_float(config.transaction_cost_bps),
        "minimum_holding_days": config.minimum_holding_days,
        "replacement_rank_degradation_threshold": config.replacement_rank_degradation_threshold,
        "replacement_edge_margin": config.replacement_edge_margin,
        "confirmation_days": config.confirmation_days,
        "emergency_exit_pct": config.emergency_exit_pct,
        "cash_buffer_ratio": config.cash_buffer_ratio,
        "max_position_weight": config.max_position_weight,
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "live_order_executed": False,
        "tachibana_api_called": False,
        "replacement_same_time_live_execution_enabled": False,
        "replacement_requires_sell_fill_before_buy": True,
    }


def calculate_annual_summary(equity_frame: pd.DataFrame, trade_frame: pd.DataFrame, config: ValidationConfig) -> list[dict[str, Any]]:
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
                "annual_replacement_count": int((year_trades["exit_reason"] == "REPLACEMENT").sum()) if not year_trades.empty else 0,
                "annual_emergency_exit_count": int((year_trades["exit_reason"] == "EMERGENCY_EXIT").sum()) if not year_trades.empty else 0,
            }
        )
    return rows


def build_summary(
    *,
    policy_comparison: pd.DataFrame,
    annual_summary: pd.DataFrame,
    trade_level: pd.DataFrame,
    ranked: pd.DataFrame,
    created_at: str,
    output_paths: dict[str, Path],
) -> dict[str, Any]:
    comparison = policy_comparison.set_index("policy_id")
    baseline_return = float(comparison.loc["A_FIXED_20BD", "cumulative_return"]) if "A_FIXED_20BD" in comparison.index else 0.0
    default_return = float(comparison.loc["B_PHASE7A_DEFAULT", "cumulative_return"]) if "B_PHASE7A_DEFAULT" in comparison.index else 0.0
    daily_turnover = float(comparison.loc["E_DAILY_TOP3_SYNC", "turnover"]) if "E_DAILY_TOP3_SYNC" in comparison.index else 0.0
    default_turnover = float(comparison.loc["B_PHASE7A_DEFAULT", "turnover"]) if "B_PHASE7A_DEFAULT" in comparison.index else 0.0
    emergency = policy_comparison[policy_comparison["policy_id"].str.startswith("C_EMERGENCY")].copy()
    best_emergency = emergency.sort_values(["max_drawdown", "cumulative_return"], ascending=[False, False]).head(1)
    best_emergency_record = best_emergency.to_dict("records")[0] if not best_emergency.empty else {}
    return {
        "phase": "Phase7-B",
        "created_at": created_at,
        "completion_status": COMPLETION_STATUS,
        "model_version": MODEL_VERSION,
        "source": {
            "ranked_daily": str(DEFAULT_RANKED_DAILY_PATH),
            "opportunity_dataset": str(DEFAULT_OPPORTUNITY_DATASET_PATH),
            "start_date": str(ranked["target_date"].min()),
            "end_date": str(ranked["target_date"].max()),
            "row_count": int(len(ranked)),
            "date_count": int(ranked["target_date"].nunique()),
        },
        "method_limitations": [
            "lightweight validation using Phase5-I forward labels, not a full daily close path backtest",
            "emergency exit is approximated from future_max_drawdown_20d because full daily close path is not yet integrated",
            "same-day replacement is allowed only for dry-run comparison; live execution must be SELL_FIRST_BUY_AFTER_FILL",
        ],
        "key_findings": {
            "phase7a_default_cumulative_return_delta_vs_fixed": round_float(default_return - baseline_return),
            "daily_top3_sync_turnover_multiple_vs_default": round_float(daily_turnover / default_turnover) if default_turnover else None,
            "best_emergency_by_drawdown_then_return": best_emergency_record,
        },
        "artifact_paths": {key: str(path) for key, path in output_paths.items()},
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "live_order_executed": False,
        "tachibana_api_called": False,
        "replacement_same_time_live_execution_enabled": False,
        "replacement_requires_sell_fill_before_buy": True,
        "policy_count": int(len(policy_comparison)),
        "annual_rows": int(len(annual_summary)),
        "trade_rows": int(len(trade_level)),
    }


def rank_for(row_lookup: dict[tuple[str, str], Any], current_date: str, code: str) -> int:
    row = row_lookup.get((current_date, code))
    return int(getattr(row, "buy_rank", 51)) if row is not None else 51


def score_for(row_lookup: dict[tuple[str, str], Any], current_date: str, code: str, default: float) -> float:
    row = row_lookup.get((current_date, code))
    return float(getattr(row, "expected_edge_score", default)) if row is not None else default


def year_from_date(date_text: str) -> int:
    return int(str(date_text)[:4])


def interpolate_return(future_return_20d: float, holding_days: int) -> float:
    ratio = min(max(holding_days, 0), 20) / 20.0
    return float(future_return_20d) * ratio


def mark_to_market_value(position: OpenPosition, current_index: int) -> float:
    holding_days = current_index - position.entry_index
    return position.entry_value * (1.0 + interpolate_return(position.future_return_20d, holding_days))


def max_drawdown(values: list[float]) -> float:
    if not values:
        return 0.0
    peak = values[0]
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        if peak:
            worst = min(worst, value / peak - 1.0)
    return worst


def cost_rate(config: ValidationConfig) -> float:
    return config.transaction_cost_bps / 10_000.0


def rate(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame:
        return 0.0
    denominator = int(frame[column].notna().sum())
    return round_float(float(frame[column].sum()) / denominator) if denominator else 0.0


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
