from __future__ import annotations

import json
import random
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
from ai_fund_lab_v2.end_to_end.random_yearly_smoke_test import load_future_outcomes
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
from ai_fund_lab_v2.position_management_ai.winner_holding_calibration import (
    WINNER_HOLDING_MODEL_VERSION,
    build_winner_holding_position_management_output,
)

PHASE = "Phase6-M"
PHASE6M_POSITION_AI_OUTPERFORMS_FIXED_HOLD = "PHASE6M_POSITION_AI_OUTPERFORMS_FIXED_HOLD"
PHASE6M_POSITION_AI_MIXED_RESULTS = "PHASE6M_POSITION_AI_MIXED_RESULTS"
PHASE6M_POSITION_AI_UNDERPERFORMS_FIXED_HOLD = "PHASE6M_POSITION_AI_UNDERPERFORMS_FIXED_HOLD"

DEFAULT_OUTPUT_CSV_PATH = Path("reports/position_management_ai/phase6m_top3_fixed_vs_position_validation.csv")
DEFAULT_OUTPUT_JSON_PATH = Path("reports/position_management_ai/phase6m_top3_fixed_vs_position_validation.json")
DEFAULT_SUMMARY_PATH = Path("reports/position_management_ai/phase6m_top3_fixed_vs_position_summary.json")
DEFAULT_YEARLY_SUMMARY_PATH = Path("reports/position_management_ai/phase6m_top3_fixed_vs_position_yearly_summary.json")
DEFAULT_ACTION_STATS_PATH = Path("reports/position_management_ai/phase6m_top3_position_action_statistics.json")


@dataclass(frozen=True)
class Phase6MTop3FixedVsPositionResult:
    trades: pd.DataFrame
    summary: dict[str, Any]
    comparison: dict[str, Any]
    yearly_summary: dict[str, Any]
    action_statistics: dict[str, Any]


def run_phase6m_top3_fixed_vs_position_validation(
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
) -> Phase6MTop3FixedVsPositionResult:
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
    selected = build_top3_selected(scored=scored, label_path=label_path, all_dates=sorted(opportunity_dataset["target_date"].astype(str).unique()))
    checkpoint_features = load_checkpoint_features(
        long_feature_path=long_feature_path,
        selected=selected,
        all_dates=sorted(opportunity_dataset["target_date"].astype(str).unique()),
    )
    trades = simulate_top3_position_management(
        selected=selected,
        checkpoint_features=checkpoint_features,
        created_at=created_at,
    )
    comparison = build_strategy_comparison(trades)
    yearly_summary = build_yearly_summary(trades)
    action_statistics = build_action_statistics(trades)
    audit = build_audit(
        selected=selected,
        trades=trades,
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
        "model_version": WINNER_HOLDING_MODEL_VERSION,
        "candidate_source": "precomputed Phase4 historical Candidate Top50 artifact",
        "opportunity_source": "Phase5 formal Opportunity model re-scoring",
        "price_path_source": "Phase4 future labels at 5/10/20bd checkpoints; evaluation-only approximation",
        "baseline_fixed_10bd_definition": "Top3 fixed hold to 10bd checkpoint; return=future_return_10bd",
        "baseline_fixed_20bd_definition": "Top3 fixed hold to 20bd checkpoint; return=future_return_20bd",
        "position_managed_definition": "Top3 with Phase6-I winner-holding Position AI at 5/10/20bd checkpoints",
        "reduce_approximation": "REDUCE = 0.5 * checkpoint_return + 0.5 * future_return_20bd",
        "add_handling": "ADD is not executed; treated as HOLD continuation and counted as add_candidate",
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
    return Phase6MTop3FixedVsPositionResult(
        trades=trades,
        summary=summary,
        comparison=comparison,
        yearly_summary=yearly_summary,
        action_statistics=action_statistics,
    )


def build_top3_selected(*, scored: pd.DataFrame, label_path: Path, all_dates: list[str]) -> pd.DataFrame:
    selected = scored[scored["buy_rank"] <= 3].copy()
    labels = load_future_outcomes(label_path, selected[["target_date", "code"]]).rename(
        columns={
            "future_return_5d": "eval_future_return_5bd",
            "future_return_10d": "eval_future_return_10bd",
            "future_return_20d": "eval_future_return_20bd",
            "future_max_return_20d": "eval_future_max_return_20bd",
            "future_max_drawdown_20d": "eval_future_min_return_20bd",
        }
    )
    selected = selected.merge(labels, on=["target_date", "code"], how="left", validate="one_to_one")
    selected["label__future_return_20d"] = selected["eval_future_return_20bd"]
    selected["label__future_max_return_20d"] = selected["eval_future_max_return_20bd"]
    selected["label__future_max_drawdown_20d"] = selected["eval_future_min_return_20bd"]
    selected["entry_year"] = selected["target_date"].astype(str).str[:4].astype(int)
    date_index = {date: index for index, date in enumerate(all_dates)}
    for days in CHECKPOINT_DAYS:
        selected[f"checkpoint_date_{days}bd"] = selected["target_date"].astype(str).map(
            lambda target_date: all_dates[date_index[target_date] + days]
            if target_date in date_index and date_index[target_date] + days < len(all_dates)
            else ""
        )
    return selected.sort_values(["target_date", "buy_rank", "code"]).reset_index(drop=True)


def simulate_top3_position_management(*, selected: pd.DataFrame, checkpoint_features: pd.DataFrame, created_at: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    feature_lookup = {
        (str(row["target_date"]), str(row["code"])): row
        for row in checkpoint_features.to_dict("records")
    }
    for entry in selected.to_dict("records"):
        target_date = str(entry["target_date"])
        code = str(entry["code"])
        path = {
            5: safe_float(entry.get("eval_future_return_5bd")),
            10: safe_float(entry.get("eval_future_return_10bd")),
            20: safe_float(entry.get("eval_future_return_20bd")),
        }
        future_max = safe_float(entry.get("eval_future_max_return_20bd"))
        future_min = safe_float(entry.get("eval_future_min_return_20bd"))
        peak_so_far = 0.0
        action_trace: list[str] = []
        exit_day = 20
        managed_return = path[20]
        terminal_action = "HOLD"
        terminal_reason = "fixed_horizon_reached"
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
            action = str(output["action"])
            action_trace.append(action)
            if action == "EXIT":
                exit_day = day
                managed_return = current_return
                terminal_action = action
                terminal_reason = str(output["action_reason"])
                break
            if action == "REDUCE":
                exit_day = day
                managed_return = 0.5 * current_return + 0.5 * path[20]
                terminal_action = action
                terminal_reason = str(output["action_reason"])
                break
            if action == "ADD":
                terminal_action = action
                terminal_reason = str(output["action_reason"])
        label_continue_winner = bool(path[20] > 0 and future_max > path[20] + 0.03 and future_min > -0.08)
        label_exit_before_drawdown = bool(future_min <= -0.08)
        rows.append(
            {
                "year": int(str(target_date)[:4]),
                "target_date": target_date,
                "code": code,
                "buy_rank": int(entry["buy_rank"]),
                "expected_edge_score": round_float(safe_float(entry.get("expected_edge_score"))),
                "downside_risk_score": round_float(safe_float(entry.get("downside_risk_score"))),
                "risk_guard_status": str(entry.get("risk_guard_status", "")),
                "fixed_10bd_return": round_float(path[10]),
                "fixed_20bd_return": round_float(path[20]),
                "position_managed_return": round_float(managed_return),
                "future_return_5bd": round_float(path[5]),
                "future_return_10bd": round_float(path[10]),
                "future_return_20bd": round_float(path[20]),
                "future_max_return_20bd": round_float(future_max),
                "future_min_return_20bd": round_float(future_min),
                "fixed_10bd_hold_days": 10,
                "fixed_20bd_hold_days": 20,
                "position_hold_days": int(exit_day),
                "position_terminal_action": terminal_action,
                "position_terminal_reason": terminal_reason,
                "action_trace": "|".join(action_trace),
                "label_continue_winner": label_continue_winner,
                "label_exit_before_drawdown": label_exit_before_drawdown,
                "fixed_10bd_profit_retention": retention_rate(path[10], future_max),
                "fixed_20bd_profit_retention": retention_rate(path[20], future_max),
                "position_profit_retention": retention_rate(managed_return, future_max),
                "fixed_10bd_profit_decay": profit_decay(path[10], future_max),
                "fixed_20bd_profit_decay": profit_decay(path[20], future_max),
                "position_profit_decay": profit_decay(managed_return, future_max),
                "add_on_loss": bool("ADD" in action_trace and any(path[day] <= 0 for day, action in zip(CHECKPOINT_DAYS, action_trace) if action == "ADD")),
                "add_exit_label_overlap": bool("ADD" in action_trace and label_exit_before_drawdown),
                "false_exit": bool(terminal_action == "EXIT" and future_max > managed_return + 0.05),
                "exit_before_drawdown": bool(terminal_action in {"EXIT", "REDUCE"} and label_exit_before_drawdown),
                "over_reduce_continue_winner": bool(terminal_action == "REDUCE" and label_continue_winner),
            }
        )
    return pd.DataFrame(rows)


def build_strategy_comparison(trades: pd.DataFrame) -> dict[str, Any]:
    comparison = {
        "Fixed_10bd": strategy_metric_block(
            trades,
            return_column="fixed_10bd_return",
            hold_days_column="fixed_10bd_hold_days",
            retention_column="fixed_10bd_profit_retention",
            decay_column="fixed_10bd_profit_decay",
            strategy="Fixed_10bd",
        ),
        "Fixed_20bd": strategy_metric_block(
            trades,
            return_column="fixed_20bd_return",
            hold_days_column="fixed_20bd_hold_days",
            retention_column="fixed_20bd_profit_retention",
            decay_column="fixed_20bd_profit_decay",
            strategy="Fixed_20bd",
        ),
        "Position_Managed": strategy_metric_block(
            trades,
            return_column="position_managed_return",
            hold_days_column="position_hold_days",
            retention_column="position_profit_retention",
            decay_column="position_profit_decay",
            strategy="Position_Managed",
        ),
    }
    fixed20 = comparison["Fixed_20bd"]
    managed = comparison["Position_Managed"]
    improvements = {
        "mean_return_improved_vs_fixed_20bd": managed["mean_return"] > fixed20["mean_return"],
        "median_return_improved_vs_fixed_20bd": managed["median_return"] > fixed20["median_return"],
        "profit_retention_improved_vs_fixed_20bd": managed["profit_retention_rate"] > fixed20["profit_retention_rate"],
        "profit_decay_improved_vs_fixed_20bd": managed["profit_decay_before_exit"] < fixed20["profit_decay_before_exit"],
        "drawdown_avoidance_improved_vs_fixed_20bd": managed["drawdown_avoidance_rate"] > fixed20["drawdown_avoidance_rate"],
        "worst_return_improved_vs_fixed_20bd": managed["worst_return"] > fixed20["worst_return"],
    }
    comparison["improvements_vs_fixed_20bd"] = improvements
    comparison["improved_major_metric_count"] = int(sum(bool(value) for value in improvements.values()))
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
    if strategy == "Position_Managed":
        terminal = trades["position_terminal_action"]
        exited_or_reduced = terminal.isin(["EXIT", "REDUCE"])
        continue_capture = continue_winner & terminal.isin(["HOLD", "ADD"]) & (returns > 0)
        false_exit_denominator = int(exited_or_reduced.sum())
        false_exit_rate = rate(int(trades["false_exit"].sum()), false_exit_denominator)
        drawdown_avoidance_rate = rate(int((trades["exit_before_drawdown"] & exited_or_reduced).sum()), int(exit_label.sum()))
        over_reduce_count = int(trades["over_reduce_continue_winner"].sum())
    elif strategy == "Fixed_10bd":
        continue_capture = continue_winner & (returns > 0)
        false_exit_rate = rate(int((continue_winner & (returns <= 0)).sum()), int(continue_winner.sum()))
        drawdown_avoidance_rate = 0.0
        over_reduce_count = 0
    else:
        continue_capture = continue_winner & (returns > 0)
        false_exit_rate = 0.0
        drawdown_avoidance_rate = 0.0
        over_reduce_count = 0
    return {
        "count": int(len(trades)),
        "mean_return": round_float(float(returns.mean())),
        "median_return": round_float(float(returns.median())),
        "positive_return_rate": rate(int(positive.sum()), len(trades)),
        "worst_return": round_float(float(returns.min())),
        "best_return": round_float(float(returns.max())),
        "avg_hold_days": round_float(float(hold_days.mean())),
        "winner_hold_days": round_float(float(hold_days[positive].mean())) if positive.any() else 0.0,
        "loser_hold_days": round_float(float(hold_days[~positive].mean())) if (~positive).any() else 0.0,
        "mean_min_return_20bd": round_float(float(pd.to_numeric(trades["future_min_return_20bd"], errors="coerce").fillna(0.0).mean())),
        "worst_min_return_20bd": round_float(float(pd.to_numeric(trades["future_min_return_20bd"], errors="coerce").fillna(0.0).min())),
        "drawdown_avoidance_rate": round_float(drawdown_avoidance_rate),
        "profit_retention_rate": round_float(float(pd.to_numeric(trades[retention_column], errors="coerce").fillna(0.0).mean())),
        "profit_decay_before_exit": round_float(float(pd.to_numeric(trades[decay_column], errors="coerce").fillna(0.0).mean())),
        "mean_max_return_20bd": round_float(float(pd.to_numeric(trades["future_max_return_20bd"], errors="coerce").fillna(0.0).mean())),
        "captured_vs_max_return_rate": round_float(float(pd.to_numeric(trades[retention_column], errors="coerce").fillna(0.0).mean())),
        "continue_winner_capture_rate": rate(int(continue_capture.sum()), int(continue_winner.sum())),
        "false_exit_rate": round_float(false_exit_rate),
        "over_reduce_count": over_reduce_count,
    }


def build_yearly_summary(trades: pd.DataFrame) -> dict[str, Any]:
    return {
        str(year): build_strategy_comparison(frame)
        for year, frame in sorted(trades.groupby("year"), key=lambda item: item[0])
    }


def build_action_statistics(trades: pd.DataFrame) -> dict[str, Any]:
    trace_actions: list[str] = []
    for trace in trades["action_trace"].fillna(""):
        trace_actions.extend([action for action in str(trace).split("|") if action])
    checkpoint_counts = pd.Series(trace_actions, dtype="object").value_counts().to_dict() if trace_actions else {}
    terminal_counts = trades["position_terminal_action"].value_counts().to_dict()
    return {
        "checkpoint_action_counts": {str(key): int(value) for key, value in checkpoint_counts.items()},
        "terminal_action_counts": {str(key): int(value) for key, value in terminal_counts.items()},
        "HOLD_count": int(checkpoint_counts.get("HOLD", 0)),
        "EXIT_count": int(checkpoint_counts.get("EXIT", 0)),
        "REDUCE_count": int(checkpoint_counts.get("REDUCE", 0)),
        "ADD_count": int(checkpoint_counts.get("ADD", 0)),
    }


def build_audit(
    *,
    selected: pd.DataFrame,
    trades: pd.DataFrame,
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
    feature_columns = list(opportunity_model_payload.get("feature_columns") or [])
    forbidden_columns = [column for column in feature_columns if is_forbidden_feature_name(column.replace("feature__", "", 1))]
    future_feature_columns = [column for column in feature_columns if "future" in str(column).lower()]
    inference_probe = pd.DataFrame(
        {
            "target_date": selected["target_date"].head(10).astype(str),
            "code": selected["code"].head(10).astype(str),
        }
    )
    feature_audit = audit_position_feature_frame(inference_probe, input_holding_count=len(inference_probe), created_at=created_at)
    audit_ok = not forbidden_columns and not future_feature_columns and feature_audit["leakage_audit_status"] == "OK"
    return {
        "phase": PHASE,
        "created_at": created_at,
        "candidate_count": int(candidate_count),
        "row_count": int(len(trades)),
        "top_n": 3,
        "target_date_count": int(trades["target_date"].nunique()) if not trades.empty else 0,
        "code_count": int(trades["code"].nunique()) if not trades.empty else 0,
        "candidate_path": str(candidate_path),
        "opportunity_dataset_path": str(opportunity_dataset_path),
        "opportunity_model_path": str(opportunity_model_path),
        "label_path": str(label_path),
        "long_feature_path": str(long_feature_path),
        "feature_column_count": len(feature_columns),
        "forbidden_feature_columns": forbidden_columns,
        "forbidden_feature_column_count": len(forbidden_columns),
        "forbidden_feature_audit_status": "OK" if not forbidden_columns else "ERROR",
        "future_columns_not_used_for_inference": not future_feature_columns,
        "future_feature_columns": future_feature_columns,
        "leakage_audit_status": "OK" if audit_ok else "ERROR",
        "feature_audit": feature_audit,
        "feature_label_separation_status": "OK" if not forbidden_columns and not future_feature_columns else "ERROR",
        "add_loss_position_count": int(trades["add_on_loss"].sum()),
        "add_exit_label_overlap_count": int(trades["add_exit_label_overlap"].sum()),
        "continue_winner_wrong_exit_count": int(((trades["position_terminal_action"] == "EXIT") & trades["label_continue_winner"]).sum()),
        "continue_winner_over_reduce_count": int(trades["over_reduce_continue_winner"].sum()),
        "action_statistics": action_statistics,
        "improved_major_metric_count": int(comparison["improved_major_metric_count"]),
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
        return PHASE6M_POSITION_AI_UNDERPERFORMS_FIXED_HOLD
    fixed20 = comparison["Fixed_20bd"]
    managed = comparison["Position_Managed"]
    if (
        managed["mean_return"] > fixed20["mean_return"]
        and comparison["improved_major_metric_count"] >= 2
    ):
        return PHASE6M_POSITION_AI_OUTPERFORMS_FIXED_HOLD
    if comparison["improved_major_metric_count"] >= 1:
        return PHASE6M_POSITION_AI_MIXED_RESULTS
    return PHASE6M_POSITION_AI_UNDERPERFORMS_FIXED_HOLD


def profit_decay(realized_return: float, max_return: float) -> float:
    if max_return <= 0:
        return 0.0
    return round_float(max_return - realized_return)


def is_forbidden_feature_name(name: str) -> bool:
    lowered = str(name).lower()
    prefixes = (
        "future_return_",
        "future_max_return_",
        "future_max_drawdown_",
        "future_min_return_",
        "top_decile_",
        "downside_bad_",
    )
    terms = (
        "trade_result",
        "future_profit",
        "future_sell_price",
        "future_best_price",
        "sold",
        "bought",
        "cash",
        "portfolio",
        "final_assets",
    )
    return lowered.startswith(prefixes) or any(term in lowered for term in terms)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(out):
        return default
    return out


def round_float(value: float) -> float:
    if not np.isfinite(value):
        return 0.0
    return round(float(value), 6)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
