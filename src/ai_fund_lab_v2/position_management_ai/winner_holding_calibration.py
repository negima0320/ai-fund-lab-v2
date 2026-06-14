from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.training import to_jsonable
from ai_fund_lab_v2.position_management_ai.calibration import (
    CALIBRATED_MODEL_VERSION,
    build_calibrated_position_management_output,
)
from ai_fund_lab_v2.position_management_ai.historical_validation import (
    DEFAULT_LONG_FEATURE_PATH,
    DEFAULT_OPPORTUNITY_DATASET_PATH,
    DEFAULT_OPPORTUNITY_MODEL_PATH,
    build_action_statistics,
    build_comparison,
    build_validation_audit,
    load_checkpoint_features,
    load_model_payload,
    score_opportunity_dataset,
    select_validation_entries,
    simulate_position_management,
    write_json,
)
from ai_fund_lab_v2.position_management_ai.inference import (
    FEATURE_VERSION,
    calculate_add_score,
    calculate_exit_score,
    calculate_reduce_score,
    calculate_trend_continuation_score,
    get_first_numeric_series,
    get_numeric_series,
    round_float,
)

PHASE = "Phase6-I"
WINNER_HOLDING_MODEL_VERSION = "position_management_policy_phase6i_winner_holding_v1"
PHASE6_VALIDATED_WITH_WINNER_HOLDING_IMPROVEMENT = "PHASE6_VALIDATED_WITH_WINNER_HOLDING_IMPROVEMENT"
PHASE6_VALIDATED_FOR_RISK_NOT_WINNER_HOLDING = "PHASE6_VALIDATED_FOR_RISK_NOT_WINNER_HOLDING"
PHASE6_IMPLEMENTED_BUT_NOT_VALIDATED = "PHASE6_IMPLEMENTED_BUT_NOT_VALIDATED"

DEFAULT_OUTPUT_CSV_PATH = Path("reports/position_management_ai/phase6i_winner_holding_calibration.csv")
DEFAULT_OUTPUT_JSON_PATH = Path("reports/position_management_ai/phase6i_winner_holding_calibration.json")
DEFAULT_COMPARISON_PATH = Path("reports/position_management_ai/phase6i_old_vs_winner_holding_comparison.json")
DEFAULT_ACTION_STATS_PATH = Path("reports/position_management_ai/phase6i_winner_holding_action_statistics.json")
DEFAULT_MISMATCH_PATH = Path("reports/position_management_ai/phase6i_winner_holding_mismatch_cases.csv")


@dataclass(frozen=True)
class Phase6IWinnerHoldingResult:
    trades: pd.DataFrame
    summary: dict[str, Any]
    comparison: dict[str, Any]
    action_statistics: dict[str, Any]
    mismatches: pd.DataFrame


def run_phase6i_winner_holding_calibration(
    *,
    opportunity_dataset_path: Path = DEFAULT_OPPORTUNITY_DATASET_PATH,
    opportunity_model_path: Path = DEFAULT_OPPORTUNITY_MODEL_PATH,
    long_feature_path: Path = DEFAULT_LONG_FEATURE_PATH,
    output_csv_path: Path = DEFAULT_OUTPUT_CSV_PATH,
    output_json_path: Path = DEFAULT_OUTPUT_JSON_PATH,
    comparison_path: Path = DEFAULT_COMPARISON_PATH,
    action_stats_path: Path = DEFAULT_ACTION_STATS_PATH,
    mismatch_path: Path = DEFAULT_MISMATCH_PATH,
    validation_year: int = 2025,
    max_target_dates: int | None = 80,
    top_n: int = 5,
    created_at: str | None = None,
) -> Phase6IWinnerHoldingResult:
    created_at = created_at or now_utc()
    dataset = pd.read_parquet(opportunity_dataset_path)
    model_payload = load_model_payload(opportunity_model_path)
    scored = score_opportunity_dataset(dataset, model_payload, validation_year=validation_year)
    selected = select_validation_entries(scored, validation_year=validation_year, max_target_dates=max_target_dates, top_n=top_n)
    checkpoint_features = load_checkpoint_features(
        long_feature_path=long_feature_path,
        selected=selected,
        all_dates=sorted(scored["target_date"].astype(str).unique().tolist()),
    )
    old_trades = simulate_position_management(
        selected=selected,
        checkpoint_features=checkpoint_features,
        created_at=created_at,
    )
    new_trades = simulate_position_management(
        selected=selected,
        checkpoint_features=checkpoint_features,
        created_at=created_at,
        output_builder=build_winner_holding_position_management_output,
    )
    old_comparison = build_comparison(old_trades)
    new_comparison = build_comparison(new_trades)
    action_statistics = build_action_statistics(new_trades)
    old_action_statistics = build_action_statistics(old_trades)
    new_audit = build_validation_audit(
        selected=selected,
        trades=new_trades,
        comparison=new_comparison,
        action_statistics=action_statistics,
        created_at=created_at,
        validation_year=validation_year,
        max_target_dates=max_target_dates,
        top_n=top_n,
        opportunity_dataset_path=opportunity_dataset_path,
        opportunity_model_path=opportunity_model_path,
        long_feature_path=long_feature_path,
    )
    old_audit = build_validation_audit(
        selected=selected,
        trades=old_trades,
        comparison=old_comparison,
        action_statistics=old_action_statistics,
        created_at=created_at,
        validation_year=validation_year,
        max_target_dates=max_target_dates,
        top_n=top_n,
        opportunity_dataset_path=opportunity_dataset_path,
        opportunity_model_path=opportunity_model_path,
        long_feature_path=long_feature_path,
    )
    comparison = build_old_vs_winner_holding_comparison(
        old_comparison=old_comparison,
        new_comparison=new_comparison,
        old_audit=old_audit,
        new_audit=new_audit,
        old_action_statistics=old_action_statistics,
        new_action_statistics=action_statistics,
    )
    mismatches = extract_winner_holding_mismatch_cases(old_trades=old_trades, new_trades=new_trades)
    completion_status = decide_completion_status(comparison=comparison, audit=new_audit)
    summary = {
        "phase": PHASE,
        "created_at": created_at,
        "completion_status": completion_status,
        "status": "OK",
        "old_model_version": CALIBRATED_MODEL_VERSION,
        "winner_holding_model_version": WINNER_HOLDING_MODEL_VERSION,
        "validation_year": validation_year,
        "target_date_count": int(selected["target_date"].nunique()) if not selected.empty else 0,
        "code_count": int(selected["code"].nunique()) if not selected.empty else 0,
        "row_count": int(len(new_trades)),
        "calibration_summary": {
            "winner_protection_guard_added": True,
            "hard_exit_maintained": True,
            "reduce_requires_confirmed_risk_stack": True,
            "add_safety_unchanged": True,
        },
        "old_vs_winner_holding_comparison": comparison,
        "action_statistics": action_statistics,
        "old_action_statistics": old_action_statistics,
        "audit": new_audit,
        "old_audit": old_audit,
        "mismatch_count": int(len(mismatches)),
        "no_broker_api_executed": True,
        "no_order_executed": True,
        "no_paper_trading_executed": True,
        "no_capital_allocation_executed": True,
    }
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    new_trades.to_csv(output_csv_path, index=False)
    mismatches.to_csv(mismatch_path, index=False)
    write_json(output_json_path, summary)
    write_json(comparison_path, comparison)
    write_json(action_stats_path, action_statistics)
    return Phase6IWinnerHoldingResult(
        trades=new_trades,
        summary=summary,
        comparison=comparison,
        action_statistics=action_statistics,
        mismatches=mismatches,
    )


def build_winner_holding_position_management_output(frame: pd.DataFrame, created_at: str) -> pd.DataFrame:
    scored = frame.copy()
    scored["current_return"] = get_numeric_series(scored, "current_return", 0.0)
    scored["peak_return"] = get_numeric_series(scored, "peak_return", scored["current_return"].median())
    scored["drawdown_from_peak"] = (scored["current_return"] - scored["peak_return"]).map(round_float)
    scored["downside_risk_score"] = get_numeric_series(scored, "downside_risk_score", 0.50).clip(0.0, 1.0)
    scored["expected_edge_score"] = get_numeric_series(scored, "expected_edge_score", 0.0)
    scored["buy_rank"] = get_numeric_series(scored, "buy_rank", 999).astype(int)
    scored["hold_score"] = (
        0.48 * calculate_trend_continuation_score(scored)
        + 0.27 * (scored["expected_edge_score"].clip(lower=-0.05, upper=0.20) + 0.05) / 0.25
        + 0.15 * (1.0 - scored["downside_risk_score"])
        + 0.10 * (scored["current_return"] > 0).astype(float)
    ).clip(0.0, 1.0).map(round_float)
    scored["exit_score"] = calculate_exit_score(scored).map(round_float)
    scored["add_score"] = calculate_add_score(scored).map(round_float)
    scored["reduce_score"] = calculate_reduce_score(scored).map(round_float)
    actions = scored.apply(classify_winner_holding_action, axis=1)
    scored["action"] = actions.map(lambda item: item["action"])
    scored["continue_holding"] = scored["action"].isin(["HOLD", "ADD"])
    scored["exit_candidate"] = scored["action"] == "EXIT"
    scored["add_candidate"] = scored["action"] == "ADD"
    scored["reduce_candidate"] = scored["action"] == "REDUCE"
    scored["action_reason"] = actions.map(lambda item: item["action_reason"])
    scored["exit_reason"] = actions.map(lambda item: item["exit_reason"])
    if "risk_guard_status" not in scored.columns:
        scored["risk_guard_status"] = ""
    scored["risk_guard_status"] = scored["risk_guard_status"].fillna("").astype(str)
    if "feature_version" not in scored.columns:
        scored["feature_version"] = FEATURE_VERSION
    scored["model_version"] = WINNER_HOLDING_MODEL_VERSION
    scored["created_at"] = created_at
    return scored[
        [
            "target_date",
            "code",
            "action",
            "hold_score",
            "exit_score",
            "add_score",
            "reduce_score",
            "continue_holding",
            "exit_candidate",
            "add_candidate",
            "reduce_candidate",
            "action_reason",
            "exit_reason",
            "risk_guard_status",
            "feature_version",
            "model_version",
            "created_at",
        ]
    ]


def classify_winner_holding_action(row: pd.Series) -> dict[str, str]:
    current_return = float(row["current_return"])
    drawdown = float(row["drawdown_from_peak"])
    expected_edge = float(row["expected_edge_score"])
    buy_rank = int(row["buy_rank"])
    downside = float(row["downside_risk_score"])
    risk_guard_bad = str(row.get("risk_guard_status", "")).lower() in {"bad", "ng", "blocked", "risk_bad", "high_risk"}
    close_over_ma20 = float(get_first_numeric_series(pd.DataFrame([row]), ("feature__close_over_ma_20d", "feature__trend_close_over_ma_20d"), 1.0).iloc[0])
    ma_5_20 = float(get_first_numeric_series(pd.DataFrame([row]), ("feature__ma_5_20_ratio", "feature__trend_ma_5_20_ratio"), 1.0).iloc[0])
    return_5d = float(get_first_numeric_series(pd.DataFrame([row]), ("feature__return_5d", "feature__price_momentum_return_5d"), 0.0).iloc[0])
    volatility = float(get_first_numeric_series(pd.DataFrame([row]), ("feature__volatility_20d", "feature__volatility_return_std_20d"), 0.0).iloc[0])
    severe_trend_break = close_over_ma20 < 0.94 and ma_5_20 < 0.94
    trend_broken = close_over_ma20 < 0.97 and ma_5_20 < 0.97
    winner_protection = (
        current_return > 0
        and expected_edge >= 0.035
        and buy_rank <= 5
        and not risk_guard_bad
        and drawdown > -0.09
        and close_over_ma20 >= 0.94
        and ma_5_20 >= 0.94
    )

    if (
        risk_guard_bad
        and current_return <= -0.05
        and (severe_trend_break or downside >= 0.82 or drawdown <= -0.12 or return_5d <= -0.08)
    ) or (
        current_return <= -0.14 and trend_broken
    ):
        return {"action": "EXIT", "action_reason": "winner_holding_hard_exit", "exit_reason": "confirmed_hard_break"}

    if (
        current_return > 0
        and current_return <= 0.055
        and expected_edge >= 0.12
        and buy_rank <= 5
        and downside <= 0.45
        and not risk_guard_bad
        and close_over_ma20 >= 0.98
        and ma_5_20 >= 0.98
        and drawdown > -0.05
    ):
        return {"action": "ADD", "action_reason": "winner_holding_add_safe_early_winner", "exit_reason": ""}

    if winner_protection:
        return {"action": "HOLD", "action_reason": "winner_protection_guard", "exit_reason": ""}

    reduce_risk_stack = (
        current_return > 0
        and downside >= 0.72
        and (
            drawdown <= -0.055
            or (trend_broken and volatility >= 0.05)
            or (return_5d <= -0.06 and close_over_ma20 < 0.98)
        )
        and not (expected_edge >= 0.08 and buy_rank <= 5 and drawdown > -0.08 and close_over_ma20 >= 0.96 and ma_5_20 >= 0.96)
    )
    if reduce_risk_stack:
        return {"action": "REDUCE", "action_reason": "winner_holding_reduce_confirmed_risk_stack", "exit_reason": ""}

    if risk_guard_bad and current_return < -0.03:
        return {"action": "REDUCE", "action_reason": "winner_holding_reduce_risk_guard_loss", "exit_reason": ""}

    return {"action": "HOLD", "action_reason": "winner_holding_hold_default", "exit_reason": ""}


def build_old_vs_winner_holding_comparison(
    *,
    old_comparison: dict[str, Any],
    new_comparison: dict[str, Any],
    old_audit: dict[str, Any],
    new_audit: dict[str, Any],
    old_action_statistics: dict[str, Any],
    new_action_statistics: dict[str, Any],
) -> dict[str, Any]:
    old = old_comparison["position_managed"]
    new = new_comparison["position_managed"]
    metrics = (
        "average_return",
        "profit_retention_rate",
        "profit_decay_before_exit",
        "winner_to_loser_rate",
        "continue_winner_capture_rate",
        "false_exit_rate",
        "exit_before_drawdown_rate",
    )
    deltas = {metric: round_float(float(new.get(metric, 0.0)) - float(old.get(metric, 0.0))) for metric in metrics}
    return {
        "phase": PHASE,
        "old_model_version": CALIBRATED_MODEL_VERSION,
        "winner_holding_model_version": WINNER_HOLDING_MODEL_VERSION,
        "old_position_metrics": old,
        "winner_holding_position_metrics": new,
        "metric_delta_new_minus_old": deltas,
        "old_continue_winner_false_exit_count": int(old_audit.get("continue_winner_wrong_exit_count", 0)),
        "winner_holding_continue_winner_false_exit_count": int(new_audit.get("continue_winner_wrong_exit_count", 0)),
        "old_continue_winner_over_reduce_count": int(old_audit.get("continue_winner_over_reduce_count", 0)),
        "winner_holding_continue_winner_over_reduce_count": int(new_audit.get("continue_winner_over_reduce_count", 0)),
        "old_action_statistics": old_action_statistics,
        "winner_holding_action_statistics": new_action_statistics,
        "capture_rate_improved": bool(new["continue_winner_capture_rate"] > old["continue_winner_capture_rate"]),
        "over_reduce_decreased": bool(new_audit.get("continue_winner_over_reduce_count", 0) < old_audit.get("continue_winner_over_reduce_count", 0)),
        "false_exit_not_increased": bool(new_audit.get("continue_winner_wrong_exit_count", 0) <= old_audit.get("continue_winner_wrong_exit_count", 0)),
        "false_exit_rate_improved": bool(new["false_exit_rate"] < old["false_exit_rate"]),
        "average_return_not_materially_worse": bool(new["average_return"] >= old["average_return"] - 0.02),
        "profit_retention_not_materially_worse": bool(new["profit_retention_rate"] >= old["profit_retention_rate"] - 0.03),
        "profit_decay_not_materially_worse": bool(new["profit_decay_before_exit"] <= old["profit_decay_before_exit"] + 0.03),
    }


def extract_winner_holding_mismatch_cases(*, old_trades: pd.DataFrame, new_trades: pd.DataFrame) -> pd.DataFrame:
    columns = ["target_date", "code", "buy_rank"]
    merged = old_trades.merge(
        new_trades,
        on=columns,
        suffixes=("_old", "_new"),
        how="inner",
        validate="one_to_one",
    )
    mask = (
        merged["label_continue_winner_old"].astype(bool)
        & (
            merged["position_terminal_action_old"].isin(["EXIT", "REDUCE"])
            | merged["position_terminal_action_new"].isin(["EXIT", "REDUCE"])
        )
    )
    out = merged[mask].copy()
    if out.empty:
        return pd.DataFrame(columns=columns + ["position_terminal_action_old", "position_terminal_action_new", "mismatch_reason"])
    out["mismatch_reason"] = out.apply(classify_mismatch_reason, axis=1)
    keep = [
        "target_date",
        "code",
        "buy_rank",
        "expected_edge_score_old",
        "baseline_return_old",
        "position_return_old",
        "position_return_new",
        "future_max_return_20d_old",
        "future_max_drawdown_20d_old",
        "position_terminal_action_old",
        "position_terminal_action_new",
        "position_terminal_reason_old",
        "position_terminal_reason_new",
        "action_trace_old",
        "action_trace_new",
        "false_exit_old",
        "false_exit_new",
        "mismatch_reason",
    ]
    return out[keep].sort_values(["mismatch_reason", "target_date", "buy_rank", "code"]).reset_index(drop=True)


def classify_mismatch_reason(row: pd.Series) -> str:
    old_action = str(row["position_terminal_action_old"])
    new_action = str(row["position_terminal_action_new"])
    if old_action in {"EXIT", "REDUCE"} and new_action in {"HOLD", "ADD"}:
        return "winner_protected_by_new_rule"
    if new_action in {"EXIT", "REDUCE"}:
        return "winner_still_reduced_or_exited"
    return "winner_not_terminally_reduced_or_exited"


def decide_completion_status(*, comparison: dict[str, Any], audit: dict[str, Any]) -> str:
    if audit["forbidden_feature_audit_status"] != "OK" or audit["leakage_audit_status"] != "OK":
        return PHASE6_IMPLEMENTED_BUT_NOT_VALIDATED
    if comparison["capture_rate_improved"] or comparison["over_reduce_decreased"]:
        if comparison["average_return_not_materially_worse"] and comparison["profit_retention_not_materially_worse"] and comparison["profit_decay_not_materially_worse"]:
            return PHASE6_VALIDATED_WITH_WINNER_HOLDING_IMPROVEMENT
        return PHASE6_VALIDATED_FOR_RISK_NOT_WINNER_HOLDING
    return PHASE6_VALIDATED_FOR_RISK_NOT_WINNER_HOLDING


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
