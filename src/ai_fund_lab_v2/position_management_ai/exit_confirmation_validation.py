from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ai_fund_lab_v2.end_to_end.expanded_random_validation import (
    DEFAULT_CANDIDATE_PATH,
    DEFAULT_LABEL_PATH,
    DEFAULT_OPPORTUNITY_DATASET_PATH,
    DEFAULT_OPPORTUNITY_MODEL_PATH,
    SEED,
    TARGET_YEARS,
    score_opportunity_top10,
    select_random_dates,
    subset_for_dates,
)
from ai_fund_lab_v2.opportunity_ai.training import to_jsonable
from ai_fund_lab_v2.position_management_ai.historical_validation import (
    CHECKPOINT_DAYS,
    DEFAULT_LONG_FEATURE_PATH,
    build_checkpoint_inference_frame,
    load_checkpoint_features,
    load_model_payload,
    rate,
    retention_rate,
)
from ai_fund_lab_v2.position_management_ai.inference import audit_position_feature_frame
from ai_fund_lab_v2.position_management_ai.top3_fixed_vs_position_validation import (
    build_audit as build_phase6m_like_audit,
    build_top3_selected,
    profit_decay,
    safe_float,
    simulate_top3_position_management,
)
from ai_fund_lab_v2.position_management_ai.winner_holding_calibration import (
    WINNER_HOLDING_MODEL_VERSION,
    build_winner_holding_position_management_output,
)

PHASE = "Phase6-O"
PHASE6O_EXIT_CONFIRMATION_VALIDATED = "PHASE6O_EXIT_CONFIRMATION_VALIDATED"
PHASE6O_EXIT_CONFIRMATION_WITH_FINDINGS = "PHASE6O_EXIT_CONFIRMATION_WITH_FINDINGS"
PHASE6O_EXIT_CONFIRMATION_NOT_VALIDATED = "PHASE6O_EXIT_CONFIRMATION_NOT_VALIDATED"

EXIT_CONFIRMATION_MODEL_VERSION = "position_management_policy_phase6o_exit_confirmation_v1"

DEFAULT_OUTPUT_CSV_PATH = Path("reports/position_management_ai/phase6o_exit_confirmation_validation.csv")
DEFAULT_OUTPUT_JSON_PATH = Path("reports/position_management_ai/phase6o_exit_confirmation_validation.json")
DEFAULT_SUMMARY_PATH = Path("reports/position_management_ai/phase6o_exit_confirmation_summary.json")
DEFAULT_YEARLY_SUMMARY_PATH = Path("reports/position_management_ai/phase6o_exit_confirmation_yearly_summary.json")
DEFAULT_ACTION_STATS_PATH = Path("reports/position_management_ai/phase6o_exit_confirmation_action_statistics.json")

STRATEGIES = ("Fixed_20bd", "Current_Position_Managed", "Exit_Immediate", "Exit_Confirm_2", "Exit_Confirm_3")


@dataclass(frozen=True)
class Phase6OExitConfirmationResult:
    trades: pd.DataFrame
    summary: dict[str, Any]
    comparison: dict[str, Any]
    yearly_summary: dict[str, Any]
    action_statistics: dict[str, Any]


def run_phase6o_exit_confirmation_validation(
    *,
    candidate_path: Path = DEFAULT_CANDIDATE_PATH,
    opportunity_dataset_path: Path = DEFAULT_OPPORTUNITY_DATASET_PATH,
    opportunity_model_path: Path = DEFAULT_OPPORTUNITY_MODEL_PATH,
    label_path: Path = DEFAULT_LABEL_PATH,
    long_feature_path: Path = DEFAULT_LONG_FEATURE_PATH,
    output_csv_path: Path = DEFAULT_OUTPUT_CSV_PATH,
    output_json_path: Path = DEFAULT_OUTPUT_JSON_PATH,
    summary_path: Path = DEFAULT_SUMMARY_PATH,
    yearly_summary_path: Path = DEFAULT_YEARLY_SUMMARY_PATH,
    action_stats_path: Path = DEFAULT_ACTION_STATS_PATH,
    target_years: tuple[int, ...] = TARGET_YEARS,
    dates_per_year: int = 5,
    seed: int = SEED,
    created_at: str | None = None,
) -> Phase6OExitConfirmationResult:
    created_at = created_at or now_utc()
    candidate = pd.read_parquet(candidate_path)
    opportunity_dataset = pd.read_parquet(opportunity_dataset_path)
    model_payload = load_model_payload(opportunity_model_path)
    selected_dates, skipped_years = select_random_dates(
        opportunity_dataset,
        target_years=target_years,
        dates_per_year=dates_per_year,
        seed=seed,
    )
    flat_dates = [date for dates in selected_dates.values() for date in dates]
    candidate_subset = subset_for_dates(candidate, flat_dates)
    opportunity_subset = subset_for_dates(opportunity_dataset, flat_dates)
    scored = score_opportunity_top10(opportunity_subset, model_payload=model_payload, created_at=created_at)
    all_dates = sorted(opportunity_dataset["target_date"].astype(str).unique())
    selected = build_top3_selected(scored=scored, label_path=label_path, all_dates=all_dates)
    checkpoint_features = load_checkpoint_features(
        long_feature_path=long_feature_path,
        selected=selected,
        all_dates=all_dates,
    )
    current_trades = simulate_top3_position_management(
        selected=selected,
        checkpoint_features=checkpoint_features,
        created_at=created_at,
    )
    trades = simulate_exit_confirmation(
        selected=selected,
        checkpoint_features=checkpoint_features,
        current_trades=current_trades,
        created_at=created_at,
    )
    comparison = build_strategy_comparison(trades)
    yearly_summary = build_yearly_summary(trades)
    action_statistics = build_action_statistics(trades)
    audit = build_audit(
        selected=selected,
        trades=trades,
        current_trades=current_trades,
        comparison=comparison,
        action_statistics=action_statistics,
        created_at=created_at,
        candidate_count=len(candidate_subset),
        opportunity_model_payload=model_payload,
        candidate_path=candidate_path,
        opportunity_dataset_path=opportunity_dataset_path,
        opportunity_model_path=opportunity_model_path,
        label_path=label_path,
        long_feature_path=long_feature_path,
    )
    completion_status = decide_completion_status(comparison=comparison, audit=audit)
    summary = {
        "phase": PHASE,
        "created_at": created_at,
        "completion_status": completion_status,
        "seed": seed,
        "dates_per_year": dates_per_year,
        "target_years": list(target_years),
        "selected_target_dates": {str(year): dates for year, dates in selected_dates.items()},
        "skipped_years": {str(year): reason for year, reason in skipped_years.items()},
        "candidate_count": int(len(candidate_subset)),
        "row_count": int(len(trades)),
        "top_n": 3,
        "current_model_version": WINNER_HOLDING_MODEL_VERSION,
        "exit_confirmation_model_version": EXIT_CONFIRMATION_MODEL_VERSION,
        "candidate_source": "precomputed Phase4 historical Candidate Top50 artifact",
        "opportunity_source": "Phase5 formal Opportunity model re-scoring",
        "price_path_source": "Phase4 future labels at 5/10/20bd checkpoints; evaluation-only approximation",
        "fixed_20bd_definition": "Top3 fixed hold to 20bd checkpoint; return=future_return_20bd",
        "current_position_managed_definition": "Phase6-M current Position Managed policy with EXIT/REDUCE/ADD signals",
        "exit_immediate_definition": "EXIT signal once exits immediately; REDUCE/ADD signals are HOLD",
        "exit_confirm_2_definition": "Two consecutive EXIT signals are required; first EXIT signal is HOLD with warning",
        "exit_confirm_3_definition": "Three consecutive EXIT signals are required; first and second EXIT signals are HOLD with warning",
        "reduce_handling": "REDUCE signal is recorded only; actual action remains HOLD",
        "add_handling": "ADD signal is recorded only; actual action remains HOLD",
        "comparison": comparison,
        "yearly_summary": yearly_summary,
        "action_statistics": action_statistics,
        "audit": audit,
    }
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    trades.to_csv(output_csv_path, index=False)
    write_json(output_json_path, {"phase": PHASE, "created_at": created_at, "summary": summary, "rows": trades.to_dict("records")})
    write_json(summary_path, summary)
    write_json(yearly_summary_path, yearly_summary)
    write_json(action_stats_path, action_statistics)
    return Phase6OExitConfirmationResult(
        trades=trades,
        summary=summary,
        comparison=comparison,
        yearly_summary=yearly_summary,
        action_statistics=action_statistics,
    )


def simulate_exit_confirmation(
    *,
    selected: pd.DataFrame,
    checkpoint_features: pd.DataFrame,
    current_trades: pd.DataFrame,
    created_at: str,
) -> pd.DataFrame:
    current_lookup = {
        (str(row["target_date"]), str(row["code"]), int(row["buy_rank"])): row
        for row in current_trades.to_dict("records")
    }
    feature_lookup = {
        (str(row["target_date"]), str(row["code"])): row
        for row in checkpoint_features.to_dict("records")
    }
    rows: list[dict[str, Any]] = []
    for entry in selected.to_dict("records"):
        target_date = str(entry["target_date"])
        code = str(entry["code"])
        buy_rank = int(entry["buy_rank"])
        current = current_lookup[(target_date, code, buy_rank)]
        path = {
            5: safe_float(entry.get("eval_future_return_5bd")),
            10: safe_float(entry.get("eval_future_return_10bd")),
            20: safe_float(entry.get("eval_future_return_20bd")),
        }
        future_max = safe_float(entry.get("eval_future_max_return_20bd"))
        future_min = safe_float(entry.get("eval_future_min_return_20bd"))
        signal_trace = build_signal_trace(
            entry=entry,
            code=code,
            target_date=target_date,
            path=path,
            feature_lookup=feature_lookup,
            created_at=created_at,
        )
        immediate = apply_confirmation_policy(path=path, signal_trace=signal_trace, required_consecutive_exit=1)
        confirm2 = apply_confirmation_policy(path=path, signal_trace=signal_trace, required_consecutive_exit=2)
        confirm3 = apply_confirmation_policy(path=path, signal_trace=signal_trace, required_consecutive_exit=3)
        label_continue_winner = bool(current["label_continue_winner"])
        label_exit_before_drawdown = bool(current["label_exit_before_drawdown"])
        base = {
            "year": int(str(target_date)[:4]),
            "target_date": target_date,
            "code": code,
            "buy_rank": buy_rank,
            "expected_edge_score": round_float(safe_float(entry.get("expected_edge_score"))),
            "downside_risk_score": round_float(safe_float(entry.get("downside_risk_score"))),
            "risk_guard_status": str(entry.get("risk_guard_status", "")),
            "fixed_20bd_return": round_float(path[20]),
            "current_position_return": round_float(safe_float(current["position_managed_return"])),
            "exit_immediate_return": round_float(immediate["return"]),
            "exit_confirm_2_return": round_float(confirm2["return"]),
            "exit_confirm_3_return": round_float(confirm3["return"]),
            "future_return_5bd": round_float(path[5]),
            "future_return_10bd": round_float(path[10]),
            "future_return_20bd": round_float(path[20]),
            "future_max_return_20bd": round_float(future_max),
            "future_min_return_20bd": round_float(future_min),
            "fixed_20bd_hold_days": 20,
            "current_position_hold_days": int(current["position_hold_days"]),
            "exit_immediate_hold_days": int(immediate["hold_days"]),
            "exit_confirm_2_hold_days": int(confirm2["hold_days"]),
            "exit_confirm_3_hold_days": int(confirm3["hold_days"]),
            "current_terminal_action": str(current["position_terminal_action"]),
            "signal_trace": "|".join(item["signal"] for item in signal_trace),
            "signal_day_trace": "|".join(f"{item['day']}:{item['signal']}" for item in signal_trace),
            "exit_signal_count": int(sum(item["signal"] == "EXIT" for item in signal_trace)),
            "reduce_signal_count": int(sum(item["signal"] == "REDUCE" for item in signal_trace)),
            "add_signal_count": int(sum(item["signal"] == "ADD" for item in signal_trace)),
            "label_continue_winner": label_continue_winner,
            "label_exit_before_drawdown": label_exit_before_drawdown,
            "fixed_20bd_profit_retention": retention_rate(path[20], future_max),
            "current_profit_retention": retention_rate(safe_float(current["position_managed_return"]), future_max),
            "exit_immediate_profit_retention": retention_rate(immediate["return"], future_max),
            "exit_confirm_2_profit_retention": retention_rate(confirm2["return"], future_max),
            "exit_confirm_3_profit_retention": retention_rate(confirm3["return"], future_max),
            "fixed_20bd_profit_decay": profit_decay(path[20], future_max),
            "current_profit_decay": profit_decay(safe_float(current["position_managed_return"]), future_max),
            "exit_immediate_profit_decay": profit_decay(immediate["return"], future_max),
            "exit_confirm_2_profit_decay": profit_decay(confirm2["return"], future_max),
            "exit_confirm_3_profit_decay": profit_decay(confirm3["return"], future_max),
        }
        for prefix, result in (("exit_immediate", immediate), ("exit_confirm_2", confirm2), ("exit_confirm_3", confirm3)):
            base[f"{prefix}_terminal_action"] = result["terminal_action"]
            base[f"{prefix}_actual_action_trace"] = result["actual_action_trace"]
            base[f"{prefix}_hold_after_first_exit"] = result["hold_after_first_exit"]
            base[f"{prefix}_hold_after_second_exit"] = result["hold_after_second_exit"]
            base[f"{prefix}_false_exit"] = bool(result["terminal_action"] == "EXIT" and future_max > result["return"] + 0.05)
            base[f"{prefix}_exit_before_drawdown"] = bool(result["terminal_action"] == "EXIT" and label_exit_before_drawdown)
            base[f"{prefix}_continue_winner_false_exit"] = bool(result["terminal_action"] == "EXIT" and label_continue_winner)
        rows.append(base)
    return pd.DataFrame(rows)


def build_signal_trace(
    *,
    entry: dict[str, Any],
    code: str,
    target_date: str,
    path: dict[int, float],
    feature_lookup: dict[tuple[str, str], dict[str, Any]],
    created_at: str,
) -> list[dict[str, Any]]:
    peak_so_far = 0.0
    trace: list[dict[str, Any]] = []
    for day in CHECKPOINT_DAYS:
        current_return = path[day]
        peak_so_far = max(peak_so_far, current_return)
        checkpoint_date = str(entry.get(f"checkpoint_date_{day}bd") or target_date)
        feature_row = feature_lookup.get((checkpoint_date, code), entry)
        inference_frame = build_checkpoint_inference_frame(
            entry=entry,
            feature_row=feature_row,
            checkpoint_date=checkpoint_date,
            holding_days=day,
            current_return=current_return,
            peak_return=peak_so_far,
        )
        output = build_winner_holding_position_management_output(inference_frame, created_at).iloc[0].to_dict()
        trace.append({"day": day, "signal": str(output["action"]), "return": current_return})
    return trace


def apply_confirmation_policy(*, path: dict[int, float], signal_trace: list[dict[str, Any]], required_consecutive_exit: int) -> dict[str, Any]:
    consecutive_exit = 0
    action_trace: list[str] = []
    hold_after_first = 0
    hold_after_second = 0
    for item in signal_trace:
        signal = item["signal"]
        day = int(item["day"])
        if signal == "EXIT":
            consecutive_exit += 1
            if consecutive_exit >= required_consecutive_exit:
                action_trace.append("EXIT")
                return {
                    "return": float(item["return"]),
                    "hold_days": day,
                    "terminal_action": "EXIT",
                    "actual_action_trace": "|".join(action_trace),
                    "hold_after_first_exit": hold_after_first,
                    "hold_after_second_exit": hold_after_second,
                }
            if consecutive_exit == 1:
                hold_after_first += 1
            if consecutive_exit == 2:
                hold_after_second += 1
            action_trace.append("HOLD_AFTER_EXIT_SIGNAL")
        else:
            consecutive_exit = 0
            action_trace.append("HOLD")
    return {
        "return": float(path[20]),
        "hold_days": 20,
        "terminal_action": "HOLD",
        "actual_action_trace": "|".join(action_trace),
        "hold_after_first_exit": hold_after_first,
        "hold_after_second_exit": hold_after_second,
    }


def build_strategy_comparison(trades: pd.DataFrame) -> dict[str, Any]:
    comparison = {
        "Fixed_20bd": strategy_metric_block(
            trades,
            return_column="fixed_20bd_return",
            hold_days_column="fixed_20bd_hold_days",
            retention_column="fixed_20bd_profit_retention",
            decay_column="fixed_20bd_profit_decay",
            strategy="Fixed_20bd",
        ),
        "Current_Position_Managed": strategy_metric_block(
            trades,
            return_column="current_position_return",
            hold_days_column="current_position_hold_days",
            retention_column="current_profit_retention",
            decay_column="current_profit_decay",
            strategy="Current_Position_Managed",
        ),
        "Exit_Immediate": strategy_metric_block(
            trades,
            return_column="exit_immediate_return",
            hold_days_column="exit_immediate_hold_days",
            retention_column="exit_immediate_profit_retention",
            decay_column="exit_immediate_profit_decay",
            strategy="Exit_Immediate",
        ),
        "Exit_Confirm_2": strategy_metric_block(
            trades,
            return_column="exit_confirm_2_return",
            hold_days_column="exit_confirm_2_hold_days",
            retention_column="exit_confirm_2_profit_retention",
            decay_column="exit_confirm_2_profit_decay",
            strategy="Exit_Confirm_2",
        ),
        "Exit_Confirm_3": strategy_metric_block(
            trades,
            return_column="exit_confirm_3_return",
            hold_days_column="exit_confirm_3_hold_days",
            retention_column="exit_confirm_3_profit_retention",
            decay_column="exit_confirm_3_profit_decay",
            strategy="Exit_Confirm_3",
        ),
    }
    fixed = comparison["Fixed_20bd"]
    current = comparison["Current_Position_Managed"]
    for name in ("Exit_Immediate", "Exit_Confirm_2", "Exit_Confirm_3"):
        item = comparison[name]
        comparison[f"{name}_vs_fixed_20bd"] = {
            "mean_return_delta": round_float(item["mean_return"] - fixed["mean_return"]),
            "worst_return_delta": round_float(item["worst_return"] - fixed["worst_return"]),
            "drawdown_avoidance_delta": round_float(item["drawdown_avoidance_rate"] - fixed["drawdown_avoidance_rate"]),
            "profit_retention_delta": round_float(item["profit_retention_rate"] - fixed["profit_retention_rate"]),
        }
        comparison[f"{name}_vs_current_position"] = {
            "mean_return_delta": round_float(item["mean_return"] - current["mean_return"]),
            "false_exit_rate_delta": round_float(item["false_exit_rate"] - current["false_exit_rate"]),
            "profit_retention_delta": round_float(item["profit_retention_rate"] - current["profit_retention_rate"]),
        }
    comparison["recommended_policy"] = recommend_policy(comparison)
    return comparison


def strategy_metric_block(
    trades: pd.DataFrame,
    *,
    return_column: str,
    hold_days_column: str,
    retention_column: str,
    decay_column: str,
    strategy: str,
) -> dict[str, Any]:
    returns = pd.to_numeric(trades[return_column], errors="coerce").fillna(0.0)
    hold_days = pd.to_numeric(trades[hold_days_column], errors="coerce").fillna(0.0)
    positive = returns > 0
    continue_winner = trades["label_continue_winner"].astype(bool)
    exit_label = trades["label_exit_before_drawdown"].astype(bool)
    if strategy == "Current_Position_Managed":
        terminal = trades["current_terminal_action"]
        exits_or_reduce = terminal.isin(["EXIT", "REDUCE"])
        false_exit_count = int(
            (
                (terminal == "EXIT")
                & (pd.to_numeric(trades["future_max_return_20bd"], errors="coerce").fillna(0.0) > returns + 0.05)
            ).sum()
        )
        continue_false_exit_count = int(((terminal == "EXIT") & continue_winner).sum())
        false_exit_rate = rate(false_exit_count, int(exits_or_reduce.sum()))
        drawdown_avoidance_rate = rate(int((exits_or_reduce & exit_label).sum()), int(exit_label.sum()))
        continue_capture = continue_winner & terminal.isin(["HOLD", "ADD"]) & (returns > 0)
        over_reduce_count = int(((terminal == "REDUCE") & continue_winner).sum())
        confirmed_exit_count = int((terminal == "EXIT").sum())
        hold_after_first = 0
        hold_after_second = 0
    elif strategy.startswith("Exit_"):
        prefix = strategy.lower()
        terminal = trades[f"{prefix}_terminal_action"]
        exits = terminal == "EXIT"
        false_exit_count = int(trades[f"{prefix}_false_exit"].sum())
        continue_false_exit_count = int(trades[f"{prefix}_continue_winner_false_exit"].sum())
        false_exit_rate = rate(false_exit_count, int(exits.sum()))
        drawdown_avoidance_rate = rate(int((trades[f"{prefix}_exit_before_drawdown"] & exits).sum()), int(exit_label.sum()))
        continue_capture = continue_winner & ~exits & (returns > 0)
        over_reduce_count = 0
        confirmed_exit_count = int(exits.sum())
        hold_after_first = int(trades[f"{prefix}_hold_after_first_exit"].sum())
        hold_after_second = int(trades[f"{prefix}_hold_after_second_exit"].sum())
    else:
        continue_false_exit_count = 0
        false_exit_rate = 0.0
        drawdown_avoidance_rate = 0.0
        continue_capture = continue_winner & (returns > 0)
        over_reduce_count = 0
        confirmed_exit_count = 0
        hold_after_first = 0
        hold_after_second = 0
    return {
        "count": int(len(trades)),
        "mean_return": round_float(float(returns.mean())),
        "median_return": round_float(float(returns.median())),
        "positive_return_rate": rate(int(positive.sum()), len(trades)),
        "worst_return": round_float(float(returns.min())),
        "best_return": round_float(float(returns.max())),
        "avg_hold_days": round_float(float(hold_days.mean())),
        "drawdown_avoidance_rate": round_float(drawdown_avoidance_rate),
        "mean_min_return_20bd": round_float(float(pd.to_numeric(trades["future_min_return_20bd"], errors="coerce").fillna(0.0).mean())),
        "worst_min_return_20bd": round_float(float(pd.to_numeric(trades["future_min_return_20bd"], errors="coerce").fillna(0.0).min())),
        "profit_retention_rate": round_float(float(pd.to_numeric(trades[retention_column], errors="coerce").fillna(0.0).mean())),
        "profit_decay_before_exit": round_float(float(pd.to_numeric(trades[decay_column], errors="coerce").fillna(0.0).mean())),
        "captured_vs_max_return_rate": round_float(float(pd.to_numeric(trades[retention_column], errors="coerce").fillna(0.0).mean())),
        "continue_winner_capture_rate": rate(int(continue_capture.sum()), int(continue_winner.sum())),
        "false_exit_rate": round_float(false_exit_rate),
        "continue_winner_false_exit_count": continue_false_exit_count,
        "over_reduce_count": over_reduce_count,
        "exit_signal_count": int(trades["exit_signal_count"].sum()),
        "confirmed_exit_count": confirmed_exit_count,
        "hold_after_first_exit_count": hold_after_first,
        "hold_after_second_exit_count": hold_after_second,
        "reduce_signal_count": int(trades["reduce_signal_count"].sum()),
        "add_signal_count": int(trades["add_signal_count"].sum()),
        "actual_hold_count": int(len(trades) - confirmed_exit_count),
        "actual_exit_count": confirmed_exit_count,
    }


def build_yearly_summary(trades: pd.DataFrame) -> dict[str, Any]:
    return {
        str(year): build_strategy_comparison(frame)
        for year, frame in sorted(trades.groupby("year"), key=lambda item: item[0])
    }


def build_action_statistics(trades: pd.DataFrame) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "exit_signal_count": int(trades["exit_signal_count"].sum()),
        "reduce_signal_count": int(trades["reduce_signal_count"].sum()),
        "add_signal_count": int(trades["add_signal_count"].sum()),
    }
    for name in ("exit_immediate", "exit_confirm_2", "exit_confirm_3"):
        terminal = trades[f"{name}_terminal_action"]
        stats[name] = {
            "terminal_action_counts": {str(k): int(v) for k, v in terminal.value_counts().to_dict().items()},
            "confirmed_exit_count": int((terminal == "EXIT").sum()),
            "actual_hold_count": int((terminal == "HOLD").sum()),
            "hold_after_first_exit_count": int(trades[f"{name}_hold_after_first_exit"].sum()),
            "hold_after_second_exit_count": int(trades[f"{name}_hold_after_second_exit"].sum()),
        }
    stats["current_position_managed"] = {
        "terminal_action_counts": {str(k): int(v) for k, v in trades["current_terminal_action"].value_counts().to_dict().items()}
    }
    return stats


def build_audit(
    *,
    selected: pd.DataFrame,
    trades: pd.DataFrame,
    current_trades: pd.DataFrame,
    comparison: dict[str, Any],
    action_statistics: dict[str, Any],
    created_at: str,
    candidate_count: int,
    opportunity_model_payload: dict[str, Any],
    candidate_path: Path,
    opportunity_dataset_path: Path,
    opportunity_model_path: Path,
    label_path: Path,
    long_feature_path: Path,
) -> dict[str, Any]:
    phase6m_audit = build_phase6m_like_audit(
        selected=selected,
        trades=current_trades,
        comparison={
            "Fixed_20bd": {"mean_return": comparison["Fixed_20bd"]["mean_return"]},
            "Position_Managed": {"mean_return": comparison["Current_Position_Managed"]["mean_return"]},
            "improved_major_metric_count": 0,
        },
        action_statistics={"terminal_action_counts": {}},
        created_at=created_at,
        candidate_count=candidate_count,
        opportunity_model_payload=opportunity_model_payload,
        candidate_path=candidate_path,
        opportunity_dataset_path=opportunity_dataset_path,
        opportunity_model_path=opportunity_model_path,
        label_path=label_path,
        long_feature_path=long_feature_path,
    )
    inference_probe = pd.DataFrame(
        {
            "target_date": selected["target_date"].head(10).astype(str),
            "code": selected["code"].head(10).astype(str),
        }
    )
    feature_audit = audit_position_feature_frame(inference_probe, input_holding_count=len(inference_probe), created_at=created_at)
    return {
        **phase6m_audit,
        "phase": PHASE,
        "feature_audit": feature_audit,
        "leakage_audit_status": "OK"
        if phase6m_audit["leakage_audit_status"] == "OK" and feature_audit["leakage_audit_status"] == "OK"
        else "ERROR",
        "action_statistics": action_statistics,
        "actual_reduce_count": 0,
        "actual_add_count": 0,
        "confirmation_policy_applied": True,
        "broker_api_executed": False,
        "order_executed": False,
        "paper_trading_executed": False,
        "capital_allocation_executed": False,
        "live_order_executed": False,
        "real_account_updated": False,
        "full_backtest_executed": False,
    }


def recommend_policy(comparison: dict[str, Any]) -> str:
    fixed = comparison["Fixed_20bd"]
    candidates = ["Exit_Confirm_2", "Exit_Confirm_3", "Exit_Immediate"]
    ranked = sorted(
        candidates,
        key=lambda name: (
            comparison[name]["mean_return"] >= fixed["mean_return"] - 0.002,
            -comparison[name]["false_exit_rate"],
            comparison[name]["mean_return"],
            -comparison[name]["actual_exit_count"],
            comparison[name]["drawdown_avoidance_rate"],
        ),
        reverse=True,
    )
    return ranked[0]


def decide_completion_status(*, comparison: dict[str, Any], audit: dict[str, Any]) -> str:
    if audit["leakage_audit_status"] != "OK":
        return PHASE6O_EXIT_CONFIRMATION_NOT_VALIDATED
    fixed = comparison["Fixed_20bd"]
    current = comparison["Current_Position_Managed"]
    for name in ("Exit_Confirm_2", "Exit_Confirm_3"):
        item = comparison[name]
        near_fixed = item["mean_return"] >= fixed["mean_return"] - 0.003
        improves_current = item["mean_return"] > current["mean_return"] and item["false_exit_rate"] < current["false_exit_rate"]
        improves_risk_or_false_exit = (
            item["worst_return"] > current["worst_return"]
            or item["drawdown_avoidance_rate"] > current["drawdown_avoidance_rate"]
            or item["false_exit_rate"] < current["false_exit_rate"]
        )
        if near_fixed and improves_risk_or_false_exit:
            return PHASE6O_EXIT_CONFIRMATION_VALIDATED
        if improves_current:
            return PHASE6O_EXIT_CONFIRMATION_WITH_FINDINGS
    return PHASE6O_EXIT_CONFIRMATION_NOT_VALIDATED


def round_float(value: float) -> float:
    if not np.isfinite(value):
        return 0.0
    return round(float(value), 6)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
