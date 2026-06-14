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
    build_action_statistics as build_current_action_statistics,
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

PHASE = "Phase6-N"
PHASE6N_DANGER_ONLY_EXIT_OUTPERFORMS_FIXED_HOLD = "PHASE6N_DANGER_ONLY_EXIT_OUTPERFORMS_FIXED_HOLD"
PHASE6N_DANGER_ONLY_EXIT_IMPROVES_POSITION_AI = "PHASE6N_DANGER_ONLY_EXIT_IMPROVES_POSITION_AI"
PHASE6N_DANGER_ONLY_EXIT_NOT_VALIDATED = "PHASE6N_DANGER_ONLY_EXIT_NOT_VALIDATED"

DANGER_ONLY_MODEL_VERSION = "position_management_policy_phase6n_danger_only_exit_v1"

DEFAULT_OUTPUT_CSV_PATH = Path("reports/position_management_ai/phase6n_danger_only_exit_validation.csv")
DEFAULT_OUTPUT_JSON_PATH = Path("reports/position_management_ai/phase6n_danger_only_exit_validation.json")
DEFAULT_SUMMARY_PATH = Path("reports/position_management_ai/phase6n_danger_only_exit_summary.json")
DEFAULT_YEARLY_SUMMARY_PATH = Path("reports/position_management_ai/phase6n_danger_only_exit_yearly_summary.json")
DEFAULT_ACTION_STATS_PATH = Path("reports/position_management_ai/phase6n_danger_only_exit_action_statistics.json")


@dataclass(frozen=True)
class Phase6NDangerOnlyExitResult:
    trades: pd.DataFrame
    summary: dict[str, Any]
    comparison: dict[str, Any]
    yearly_summary: dict[str, Any]
    action_statistics: dict[str, Any]


def run_phase6n_danger_only_exit_validation(
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
) -> Phase6NDangerOnlyExitResult:
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
    danger_trades = simulate_danger_only_exit(
        selected=selected,
        checkpoint_features=checkpoint_features,
        current_trades=current_trades,
        created_at=created_at,
    )
    comparison = build_strategy_comparison(danger_trades)
    yearly_summary = build_yearly_summary(danger_trades)
    action_statistics = build_action_statistics(danger_trades)
    audit = build_audit(
        selected=selected,
        trades=danger_trades,
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
        "row_count": int(len(danger_trades)),
        "top_n": 3,
        "current_model_version": WINNER_HOLDING_MODEL_VERSION,
        "danger_only_model_version": DANGER_ONLY_MODEL_VERSION,
        "candidate_source": "precomputed Phase4 historical Candidate Top50 artifact",
        "opportunity_source": "Phase5 formal Opportunity model re-scoring",
        "price_path_source": "Phase4 future labels at 5/10/20bd checkpoints; evaluation-only approximation",
        "fixed_20bd_definition": "Top3 fixed hold to 20bd checkpoint; return=future_return_20bd",
        "current_position_managed_definition": "Phase6-M current Position Managed policy with EXIT/REDUCE/ADD signals",
        "danger_only_exit_definition": "Top3 holds to 20bd unless danger_score>=3 or hard_break; REDUCE/ADD signals are recorded only",
        "danger_score_definition": danger_score_definition(),
        "reduce_handling": "REDUCE signal is recorded only; actual action remains HOLD",
        "add_handling": "ADD signal is recorded only; actual action remains HOLD",
        "comparison": comparison,
        "yearly_summary": yearly_summary,
        "action_statistics": action_statistics,
        "audit": audit,
    }
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    danger_trades.to_csv(output_csv_path, index=False)
    write_json(output_json_path, {"phase": PHASE, "created_at": created_at, "summary": summary, "rows": danger_trades.to_dict("records")})
    write_json(summary_path, summary)
    write_json(yearly_summary_path, yearly_summary)
    write_json(action_stats_path, action_statistics)
    return Phase6NDangerOnlyExitResult(
        trades=danger_trades,
        summary=summary,
        comparison=comparison,
        yearly_summary=yearly_summary,
        action_statistics=action_statistics,
    )


def simulate_danger_only_exit(
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
        peak_so_far = 0.0
        actual_action_trace: list[str] = []
        signal_trace: list[str] = []
        danger_trace: list[str] = []
        exit_day = 20
        danger_return = path[20]
        terminal_action = "HOLD"
        terminal_reason = "danger_only_hold_to_20bd"
        max_danger_score = 0
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
            signal = build_winner_holding_position_management_output(inference_frame, created_at).iloc[0].to_dict()
            signal_trace.append(str(signal["action"]))
            danger = calculate_danger_state(inference_frame.iloc[0])
            max_danger_score = max(max_danger_score, int(danger["danger_score"]))
            danger_trace.append(f"{day}bd:{danger['danger_score']}:{danger['danger_reason']}")
            if danger["hard_break"] or int(danger["danger_score"]) >= 3:
                exit_day = day
                danger_return = current_return
                terminal_action = "EXIT"
                terminal_reason = f"danger_only_exit:{danger['danger_reason']}"
                actual_action_trace.append("EXIT")
                break
            actual_action_trace.append("HOLD")
        label_continue_winner = bool(current["label_continue_winner"])
        label_exit_before_drawdown = bool(current["label_exit_before_drawdown"])
        rows.append(
            {
                "year": int(str(target_date)[:4]),
                "target_date": target_date,
                "code": code,
                "buy_rank": buy_rank,
                "expected_edge_score": round_float(safe_float(entry.get("expected_edge_score"))),
                "downside_risk_score": round_float(safe_float(entry.get("downside_risk_score"))),
                "risk_guard_status": str(entry.get("risk_guard_status", "")),
                "fixed_20bd_return": round_float(path[20]),
                "current_position_return": round_float(safe_float(current["position_managed_return"])),
                "danger_only_return": round_float(danger_return),
                "future_return_5bd": round_float(path[5]),
                "future_return_10bd": round_float(path[10]),
                "future_return_20bd": round_float(path[20]),
                "future_max_return_20bd": round_float(future_max),
                "future_min_return_20bd": round_float(future_min),
                "fixed_20bd_hold_days": 20,
                "current_position_hold_days": int(current["position_hold_days"]),
                "danger_only_hold_days": int(exit_day),
                "current_terminal_action": str(current["position_terminal_action"]),
                "danger_terminal_action": terminal_action,
                "danger_terminal_reason": terminal_reason,
                "current_action_trace": str(current["action_trace"]),
                "danger_actual_action_trace": "|".join(actual_action_trace),
                "danger_signal_trace": "|".join(signal_trace),
                "danger_trace": "|".join(danger_trace),
                "max_danger_score": max_danger_score,
                "label_continue_winner": label_continue_winner,
                "label_exit_before_drawdown": label_exit_before_drawdown,
                "fixed_20bd_profit_retention": retention_rate(path[20], future_max),
                "current_profit_retention": retention_rate(safe_float(current["position_managed_return"]), future_max),
                "danger_profit_retention": retention_rate(danger_return, future_max),
                "fixed_20bd_profit_decay": profit_decay(path[20], future_max),
                "current_profit_decay": profit_decay(safe_float(current["position_managed_return"]), future_max),
                "danger_profit_decay": profit_decay(danger_return, future_max),
                "danger_false_exit": bool(terminal_action == "EXIT" and future_max > danger_return + 0.05),
                "danger_exit_before_drawdown": bool(terminal_action == "EXIT" and label_exit_before_drawdown),
                "danger_continue_winner_false_exit": bool(terminal_action == "EXIT" and label_continue_winner),
                "danger_reduce_signal": "REDUCE" in signal_trace,
                "danger_add_signal": "ADD" in signal_trace,
            }
        )
    return pd.DataFrame(rows)


def calculate_danger_state(row: pd.Series) -> dict[str, Any]:
    current_return = safe_float(row.get("current_return"))
    peak_return = safe_float(row.get("peak_return"))
    drawdown = current_return - peak_return
    downside = safe_float(row.get("downside_risk_score"), 0.5)
    risk_guard_bad = str(row.get("risk_guard_status", "")).lower() in {"bad", "ng", "blocked", "risk_bad", "high_risk"}
    close_ma20 = safe_float(row.get("feature__close_over_ma_20d"), 1.0)
    ma_5_20 = safe_float(row.get("feature__ma_5_20_ratio"), 1.0)
    return_5d = safe_float(row.get("feature__return_5d"), 0.0)
    volatility = safe_float(row.get("feature__volatility_20d"), 0.0)
    reasons: list[str] = []
    if risk_guard_bad and downside >= 0.72:
        reasons.append("risk_guard_bad_high_downside")
    if drawdown <= -0.12:
        reasons.append("deep_drawdown_from_peak")
    if close_ma20 < 0.94 and ma_5_20 < 0.94:
        reasons.append("ma_hard_break")
    if return_5d <= -0.08:
        reasons.append("sharp_5d_decline")
    if volatility >= 0.08 and current_return < 0:
        reasons.append("high_volatility_loss")
    hard_break = (
        current_return <= -0.14
        and close_ma20 < 0.96
        and ma_5_20 < 0.96
    ) or (
        risk_guard_bad
        and current_return <= -0.08
        and (drawdown <= -0.12 or return_5d <= -0.08)
    )
    if hard_break and "hard_break" not in reasons:
        reasons.append("hard_break")
    return {
        "danger_score": len(reasons),
        "hard_break": bool(hard_break),
        "danger_reason": ",".join(reasons) if reasons else "no_hard_danger",
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
        "Danger_Only_Exit": strategy_metric_block(
            trades,
            return_column="danger_only_return",
            hold_days_column="danger_only_hold_days",
            retention_column="danger_profit_retention",
            decay_column="danger_profit_decay",
            strategy="Danger_Only_Exit",
        ),
    }
    fixed = comparison["Fixed_20bd"]
    current = comparison["Current_Position_Managed"]
    danger = comparison["Danger_Only_Exit"]
    comparison["danger_vs_fixed_20bd"] = {
        "mean_return_delta": round_float(danger["mean_return"] - fixed["mean_return"]),
        "worst_return_delta": round_float(danger["worst_return"] - fixed["worst_return"]),
        "drawdown_avoidance_delta": round_float(danger["drawdown_avoidance_rate"] - fixed["drawdown_avoidance_rate"]),
        "profit_retention_delta": round_float(danger["profit_retention_rate"] - fixed["profit_retention_rate"]),
    }
    comparison["danger_vs_current_position"] = {
        "mean_return_delta": round_float(danger["mean_return"] - current["mean_return"]),
        "false_exit_rate_delta": round_float(danger["false_exit_rate"] - current["false_exit_rate"]),
        "over_reduce_count_delta": int(danger["over_reduce_count"] - current["over_reduce_count"]),
        "profit_retention_delta": round_float(danger["profit_retention_rate"] - current["profit_retention_rate"]),
    }
    comparison["danger_improves_fixed_risk"] = bool(
        danger["worst_return"] > fixed["worst_return"]
        and danger["drawdown_avoidance_rate"] > fixed["drawdown_avoidance_rate"]
    )
    comparison["danger_improves_current_position"] = bool(
        danger["mean_return"] > current["mean_return"]
        and danger["false_exit_rate"] < current["false_exit_rate"]
    )
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
    if strategy == "Danger_Only_Exit":
        exits = trades["danger_terminal_action"] == "EXIT"
        continue_false_exit_count = int((exits & continue_winner).sum())
        false_exit_rate = rate(int(trades["danger_false_exit"].sum()), int(exits.sum()))
        drawdown_avoidance_rate = rate(int((trades["danger_exit_before_drawdown"] & exits).sum()), int(exit_label.sum()))
        continue_capture = continue_winner & ~exits & (returns > 0)
        over_reduce_count = 0
    elif strategy == "Current_Position_Managed":
        terminal = trades["current_terminal_action"]
        exits_or_reduce = terminal.isin(["EXIT", "REDUCE"])
        continue_false_exit_count = int(((terminal == "EXIT") & continue_winner).sum())
        false_exit_count = 0
        for row in trades.to_dict("records"):
            if str(row["current_terminal_action"]) == "EXIT" and safe_float(row["future_max_return_20bd"]) > safe_float(row["current_position_return"]) + 0.05:
                false_exit_count += 1
        false_exit_rate = rate(false_exit_count, int(exits_or_reduce.sum()))
        drawdown_avoidance_rate = rate(int((exits_or_reduce & exit_label).sum()), int(exit_label.sum()))
        continue_capture = continue_winner & terminal.isin(["HOLD", "ADD"]) & (returns > 0)
        over_reduce_count = int(((terminal == "REDUCE") & continue_winner).sum())
    else:
        continue_false_exit_count = 0
        false_exit_rate = 0.0
        drawdown_avoidance_rate = 0.0
        continue_capture = continue_winner & (returns > 0)
        over_reduce_count = 0
    return {
        "count": int(len(trades)),
        "mean_return": round_float(float(returns.mean())),
        "median_return": round_float(float(returns.median())),
        "positive_return_rate": rate(int(positive.sum()), len(trades)),
        "worst_return": round_float(float(returns.min())),
        "best_return": round_float(float(returns.max())),
        "avg_hold_days": round_float(float(hold_days.mean())),
        "mean_min_return_20bd": round_float(float(pd.to_numeric(trades["future_min_return_20bd"], errors="coerce").fillna(0.0).mean())),
        "worst_min_return_20bd": round_float(float(pd.to_numeric(trades["future_min_return_20bd"], errors="coerce").fillna(0.0).min())),
        "drawdown_avoidance_rate": round_float(drawdown_avoidance_rate),
        "profit_retention_rate": round_float(float(pd.to_numeric(trades[retention_column], errors="coerce").fillna(0.0).mean())),
        "profit_decay_before_exit": round_float(float(pd.to_numeric(trades[decay_column], errors="coerce").fillna(0.0).mean())),
        "captured_vs_max_return_rate": round_float(float(pd.to_numeric(trades[retention_column], errors="coerce").fillna(0.0).mean())),
        "continue_winner_capture_rate": rate(int(continue_capture.sum()), int(continue_winner.sum())),
        "false_exit_rate": round_float(false_exit_rate),
        "continue_winner_false_exit_count": continue_false_exit_count,
        "over_reduce_count": over_reduce_count,
    }


def build_yearly_summary(trades: pd.DataFrame) -> dict[str, Any]:
    return {
        str(year): build_strategy_comparison(frame)
        for year, frame in sorted(trades.groupby("year"), key=lambda item: item[0])
    }


def build_action_statistics(trades: pd.DataFrame) -> dict[str, Any]:
    current_stats = {
        "terminal_action_counts": {str(k): int(v) for k, v in trades["current_terminal_action"].value_counts().to_dict().items()},
        "source": "Current Position Managed from Phase6-M",
    }
    signal_actions: list[str] = []
    actual_actions: list[str] = []
    for signal_trace in trades["danger_signal_trace"].fillna(""):
        signal_actions.extend([action for action in str(signal_trace).split("|") if action])
    for actual_trace in trades["danger_actual_action_trace"].fillna(""):
        actual_actions.extend([action for action in str(actual_trace).split("|") if action])
    signal_counts = pd.Series(signal_actions, dtype="object").value_counts().to_dict() if signal_actions else {}
    actual_counts = pd.Series(actual_actions, dtype="object").value_counts().to_dict() if actual_actions else {}
    return {
        "current_position_managed": current_stats,
        "danger_only_exit": {
            "signal_action_counts": {str(k): int(v) for k, v in signal_counts.items()},
            "actual_action_counts": {str(k): int(v) for k, v in actual_counts.items()},
            "HOLD_count": int(actual_counts.get("HOLD", 0)),
            "EXIT_count": int(actual_counts.get("EXIT", 0)),
            "REDUCE_signal_count": int(signal_counts.get("REDUCE", 0)),
            "ADD_signal_count": int(signal_counts.get("ADD", 0)),
            "actual_exit_count": int((trades["danger_terminal_action"] == "EXIT").sum()),
            "actual_hold_count": int((trades["danger_terminal_action"] == "HOLD").sum()),
            "max_danger_score_counts": {str(k): int(v) for k, v in trades["max_danger_score"].value_counts().sort_index().to_dict().items()},
        },
    }


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
        action_statistics=build_current_action_statistics(current_trades),
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
        "danger_actual_reduce_count": 0,
        "danger_actual_add_count": 0,
        "danger_condition_applied": bool((trades["max_danger_score"] >= 2).any() or (trades["danger_terminal_action"] == "EXIT").any()),
        "broker_api_executed": False,
        "order_executed": False,
        "paper_trading_executed": False,
        "capital_allocation_executed": False,
        "live_order_executed": False,
        "real_account_updated": False,
        "full_backtest_executed": False,
    }


def decide_completion_status(*, comparison: dict[str, Any], audit: dict[str, Any]) -> str:
    if audit["leakage_audit_status"] != "OK":
        return PHASE6N_DANGER_ONLY_EXIT_NOT_VALIDATED
    fixed = comparison["Fixed_20bd"]
    current = comparison["Current_Position_Managed"]
    danger = comparison["Danger_Only_Exit"]
    mean_equal_or_better = danger["mean_return"] >= fixed["mean_return"] - 0.000001
    risk_better = danger["worst_return"] > fixed["worst_return"] and danger["drawdown_avoidance_rate"] > fixed["drawdown_avoidance_rate"]
    if mean_equal_or_better and risk_better:
        return PHASE6N_DANGER_ONLY_EXIT_OUTPERFORMS_FIXED_HOLD
    if danger["mean_return"] > current["mean_return"] and danger["false_exit_rate"] < current["false_exit_rate"]:
        return PHASE6N_DANGER_ONLY_EXIT_IMPROVES_POSITION_AI
    return PHASE6N_DANGER_ONLY_EXIT_NOT_VALIDATED


def danger_score_definition() -> dict[str, Any]:
    return {
        "exit_rule": "EXIT only when hard_break is true or danger_score >= 3",
        "danger_components": [
            "risk_guard_status bad and downside_risk_score >= 0.72",
            "drawdown_from_peak <= -0.12",
            "close_over_ma_20d < 0.94 and ma_5_20_ratio < 0.94",
            "return_5d <= -0.08",
            "volatility_20d >= 0.08 and current_return < 0",
        ],
        "hard_break": [
            "current_return <= -0.14 and close_over_ma_20d < 0.96 and ma_5_20_ratio < 0.96",
            "risk_guard bad and current_return <= -0.08 and deep drawdown or sharp 5d decline",
        ],
    }


def round_float(value: float) -> float:
    if not np.isfinite(value):
        return 0.0
    return round(float(value), 6)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
