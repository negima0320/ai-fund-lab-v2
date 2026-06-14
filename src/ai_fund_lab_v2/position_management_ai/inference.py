from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.dataset_builder import FEATURE_META_COLUMNS, read_table
from ai_fund_lab_v2.opportunity_ai.training import contains_any, to_jsonable

PHASE = "Phase6-A"
MODEL_VERSION = "position_management_policy_phase6a_v1"
FEATURE_VERSION = "position_management_feature_v1"

READY_FOR_PHASE6_VALIDATION = "READY_FOR_PHASE6_VALIDATION"
BLOCKED_BY_INPUT = "BLOCKED_BY_INPUT"
BLOCKED_BY_JOIN_COVERAGE = "BLOCKED_BY_JOIN_COVERAGE"
BLOCKED_BY_LEAKAGE_AUDIT = "BLOCKED_BY_LEAKAGE_AUDIT"

DEFAULT_HOLDING_PATH = Path("reports/position_management_ai/phase6a/current_holdings_snapshot.parquet")
DEFAULT_OPPORTUNITY_PATH = Path("reports/opportunity_ai/phase5f/latest_opportunity_inference.parquet")
DEFAULT_FEATURE_PATH = Path(".runtime/candidate_ai/features/phase4bc_long_history_features_2021-06-14_2026-06-12.parquet")
DEFAULT_OUTPUT_DIR = Path("reports/position_management_ai/phase6a")

INFERENCE_FILENAME = "position_management_inference.parquet"
ACTION_CSV_FILENAME = "position_management_actions.csv"
SUMMARY_FILENAME = "position_management_inference_summary.json"
AUDIT_FILENAME = "position_management_inference_audit.json"

HOLDING_COLUMNS = {
    "target_date",
    "code",
    "entry_price",
    "current_price",
    "holding_days",
    "position_size",
    "current_return",
    "peak_return",
}

OPPORTUNITY_COLUMNS = {
    "target_date",
    "code",
    "expected_edge_score",
    "buy_rank",
    "downside_risk_score",
    "risk_guard_status",
    "candidate_score",
    "candidate_rank",
    "buy_reason",
    "no_buy_reason",
    "calibration_policy_name",
}

FORBIDDEN_FEATURE_PREFIXES = (
    "future_return_",
    "future_max_return_",
    "future_max_drawdown_",
    "top_decile_",
    "downside_bad_",
    "expected_edge_label_",
    "risk_adjusted_future_return_",
    "opportunity_rank_label_",
)

FORBIDDEN_FEATURE_TERMS = (
    "trade_result",
    "future_profit",
    "future_sell_price",
    "future_best_price",
    "backtest",
    "paper_trading",
    "annual_return",
    "final_assets",
    "cash",
    "portfolio",
    "bought",
    "sold",
    "order",
    "broker",
)

OUTPUT_COLUMNS = (
    "target_date",
    "code",
    "action",
    "hold_score",
    "exit_score",
    "add_score",
    "reduce_score",
    "continue_holding",
    "add_candidate",
    "reduce_candidate",
    "exit_candidate",
    "action_reason",
    "exit_reason",
    "risk_guard_status",
    "feature_version",
    "model_version",
    "created_at",
)


@dataclass(frozen=True)
class PositionManagementInferenceResult:
    output: pd.DataFrame
    summary: dict[str, Any]
    audit: dict[str, Any]


def run_position_management_inference(
    *,
    holding_path: Path = DEFAULT_HOLDING_PATH,
    opportunity_path: Path = DEFAULT_OPPORTUNITY_PATH,
    feature_path: Path = DEFAULT_FEATURE_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    created_at: str | None = None,
    inference_run_id: str | None = None,
) -> PositionManagementInferenceResult:
    created_at = created_at or now_utc()
    inference_run_id = inference_run_id or f"phase6a_{created_at.replace(':', '').replace('+', 'Z')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / INFERENCE_FILENAME
    action_csv_path = output_dir / ACTION_CSV_FILENAME
    summary_path = output_dir / SUMMARY_FILENAME
    audit_path = output_dir / AUDIT_FILENAME

    missing_inputs = [str(path) for path in (holding_path, opportunity_path, feature_path) if not path.is_file()]
    if missing_inputs:
        return _blocked_result(
            BLOCKED_BY_INPUT,
            f"required Phase6 input artifact is missing: {', '.join(missing_inputs)}",
            holding_path=holding_path,
            opportunity_path=opportunity_path,
            feature_path=feature_path,
            output_path=output_path,
            action_csv_path=action_csv_path,
            summary_path=summary_path,
            audit_path=audit_path,
            created_at=created_at,
        )

    holding = normalize_holding_frame(read_table(holding_path))
    target_dates = sorted(holding["target_date"].dropna().astype(str).unique().tolist())
    opportunity = read_table(opportunity_path)
    feature = read_feature_frame_for_dates(feature_path, target_dates)
    frame = build_position_feature_frame(holding_frame=holding, opportunity_frame=opportunity, feature_frame=feature)
    audit = audit_position_feature_frame(frame, input_holding_count=len(holding), created_at=created_at)
    if audit["leakage_audit_status"] != "OK":
        summary = build_summary(
            readiness_status=BLOCKED_BY_LEAKAGE_AUDIT,
            status="BLOCKED",
            holding_path=holding_path,
            opportunity_path=opportunity_path,
            feature_path=feature_path,
            output_path=output_path,
            action_csv_path=action_csv_path,
            summary_path=summary_path,
            audit_path=audit_path,
            created_at=created_at,
            audit=audit,
            output_count=0,
        )
        write_json(summary_path, summary)
        write_json(audit_path, audit)
        return PositionManagementInferenceResult(output=pd.DataFrame(columns=OUTPUT_COLUMNS), summary=summary, audit=audit)
    if frame.empty:
        audit = {**audit, "readiness_status": BLOCKED_BY_JOIN_COVERAGE}
        summary = build_summary(
            readiness_status=BLOCKED_BY_JOIN_COVERAGE,
            status="BLOCKED",
            holding_path=holding_path,
            opportunity_path=opportunity_path,
            feature_path=feature_path,
            output_path=output_path,
            action_csv_path=action_csv_path,
            summary_path=summary_path,
            audit_path=audit_path,
            created_at=created_at,
            audit=audit,
            output_count=0,
        )
        write_json(summary_path, summary)
        write_json(audit_path, audit)
        return PositionManagementInferenceResult(output=pd.DataFrame(columns=OUTPUT_COLUMNS), summary=summary, audit=audit)

    output = build_position_management_output(frame, created_at=created_at, inference_run_id=inference_run_id)
    audit = {
        **audit,
        "output_count": int(len(output)),
        "hold_count": int((output["action"] == "HOLD").sum()),
        "exit_count": int(output["exit_candidate"].sum()),
        "add_candidate_count": int(output["add_candidate"].sum()),
        "reduce_count": int(output["reduce_candidate"].sum()),
        "readiness_status": READY_FOR_PHASE6_VALIDATION,
    }
    output.to_parquet(output_path, index=False, engine="pyarrow")
    output.to_csv(action_csv_path, index=False)
    summary = build_summary(
        readiness_status=READY_FOR_PHASE6_VALIDATION,
        status="OK",
        holding_path=holding_path,
        opportunity_path=opportunity_path,
        feature_path=feature_path,
        output_path=output_path,
        action_csv_path=action_csv_path,
        summary_path=summary_path,
        audit_path=audit_path,
        created_at=created_at,
        audit=audit,
        output_count=len(output),
    )
    write_json(summary_path, summary)
    write_json(audit_path, audit)
    return PositionManagementInferenceResult(output=output, summary=summary, audit=audit)


def build_position_feature_frame(
    *,
    holding_frame: pd.DataFrame,
    opportunity_frame: pd.DataFrame,
    feature_frame: pd.DataFrame,
) -> pd.DataFrame:
    holding = normalize_holding_frame(holding_frame)
    opportunity = normalize_opportunity_frame(opportunity_frame)
    feature = feature_frame.copy()
    if "target_date" not in feature.columns or "code" not in feature.columns:
        raise ValueError("feature artifact must contain target_date and code")
    feature["target_date"] = feature["target_date"].astype(str)
    feature["code"] = feature["code"].astype(str)
    feature = feature.drop_duplicates(["target_date", "code"], keep="first")

    holding_part = holding[[column for column in HOLDING_COLUMNS if column in holding.columns]]
    opportunity_part = opportunity[[column for column in OPPORTUNITY_COLUMNS if column in opportunity.columns]]
    jq_feature_columns = [column for column in feature.columns if column not in FEATURE_META_COLUMNS]
    feature_part = feature[["target_date", "code"] + optional_columns(feature, ("as_of_date", "feature_version")) + jq_feature_columns].rename(
        columns={column: f"feature__{column}" for column in jq_feature_columns}
    )

    frame = holding_part.merge(opportunity_part, on=["target_date", "code"], how="left", validate="one_to_one")
    frame = frame.merge(feature_part, on=["target_date", "code"], how="left", validate="one_to_one")
    if "as_of_date" not in frame.columns:
        frame["as_of_date"] = frame["target_date"]
    if "feature_version" not in frame.columns:
        frame["feature_version"] = FEATURE_VERSION
    return frame


def build_position_management_output(
    frame: pd.DataFrame,
    *,
    created_at: str,
    inference_run_id: str,
) -> pd.DataFrame:
    scored = frame.copy()
    scored["current_return"] = calculate_current_return(scored)
    scored["peak_return"] = pd.to_numeric(scored.get("peak_return", scored["current_return"]), errors="coerce").fillna(scored["current_return"])
    scored["drawdown_from_peak"] = (scored["current_return"] - scored["peak_return"]).map(round_float)
    scored["downside_risk_score"] = get_numeric_series(scored, "downside_risk_score", 0.50).clip(0.0, 1.0)
    scored["expected_edge_score"] = get_numeric_series(scored, "expected_edge_score", 0.0)
    scored["buy_rank"] = get_numeric_series(scored, "buy_rank", 999).astype(int)
    scored["position_size"] = get_numeric_series(scored, "position_size", 0.0)
    scored["holding_days"] = get_numeric_series(scored, "holding_days", 0).astype(int)

    trend_score = calculate_trend_continuation_score(scored)
    opportunity_score = calculate_opportunity_continuation_score(scored)
    profit_score = ((scored["current_return"] + 0.08) / 0.28).clip(0.0, 1.0)
    risk_penalty = calculate_position_risk_score(scored)
    scored["hold_score"] = (
        0.35 * trend_score + 0.25 * opportunity_score + 0.20 * profit_score + 0.20 * (1.0 - risk_penalty)
    ).map(round_float)
    scored["exit_score"] = calculate_exit_score(scored).map(round_float)
    scored["add_score"] = calculate_add_score(scored).map(round_float)
    scored["reduce_score"] = calculate_reduce_score(scored).map(round_float)

    actions = scored.apply(classify_position_action, axis=1)
    scored["action"] = actions.map(lambda item: item["action"])
    scored["continue_holding"] = scored["action"].isin(["HOLD", "ADD"])
    scored["add_candidate"] = scored["action"] == "ADD"
    scored["reduce_candidate"] = scored["action"] == "REDUCE"
    scored["exit_candidate"] = scored["action"] == "EXIT"
    scored["action_reason"] = actions.map(lambda item: item["action_reason"])
    scored["exit_reason"] = actions.map(lambda item: item["exit_reason"])
    scored["risk_guard_status"] = get_numeric_or_string_series(scored, "risk_guard_status", "").fillna("").astype(str)
    scored["model_version"] = MODEL_VERSION
    scored["created_at"] = created_at

    output = scored.sort_values(["target_date", "action", "hold_score", "code"], ascending=[True, True, False, True]).copy()
    return output[list(OUTPUT_COLUMNS)]


def classify_position_action(row: pd.Series) -> dict[str, str]:
    hold_score = float(row["hold_score"])
    exit_score = float(row["exit_score"])
    add_score = float(row["add_score"])
    reduce_score = float(row["reduce_score"])
    current_return = float(row["current_return"])
    drawdown_from_peak = float(row["drawdown_from_peak"])
    trend_score = float(calculate_trend_continuation_score(pd.DataFrame([row])).iloc[0])
    buy_rank = int(row["buy_rank"])
    expected_edge = float(row["expected_edge_score"])
    risk_guard_status = str(row.get("risk_guard_status", "")).lower()

    exit_reasons: list[str] = []
    risk_reasons: list[str] = []
    hold_reasons: list[str] = []

    if current_return <= -0.08:
        exit_reasons.append("hard_stop_current_return")
    if drawdown_from_peak <= -0.12:
        exit_reasons.append("profit_retention_break")
    if trend_score < 0.30 and expected_edge <= 0:
        exit_reasons.append("trend_and_opportunity_broken")
    if float(row["downside_risk_score"]) >= 0.75:
        risk_reasons.append("high_downside_risk_score")
    if risk_guard_status in {"bad", "ng", "blocked", "risk_bad", "high_risk"}:
        exit_reasons.append("risk_guard_status_bad")
    if drawdown_from_peak <= -0.07:
        risk_reasons.append("peak_drawdown_warning")

    if exit_reasons or exit_score >= 0.80:
        if not exit_reasons:
            exit_reasons.append("exit_score_high")
        return {
            "action": "EXIT",
            "action_reason": "exit_rule_triggered",
            "exit_reason": "|".join(exit_reasons),
        }

    if float(row["downside_risk_score"]) >= 0.65 or drawdown_from_peak <= -0.07 or reduce_score >= 0.62 or hold_score < 0.42:
        if trend_score >= 0.35 or expected_edge > 0:
            return {
                "action": "REDUCE",
                "action_reason": "|".join(risk_reasons or ["risk_increased_but_trend_not_broken"]),
                "exit_reason": "",
            }
        return {
            "action": "EXIT",
            "action_reason": "exit_rule_triggered",
            "exit_reason": "weak_hold_score",
        }

    if add_score >= 0.72 and current_return > 0 and buy_rank <= 5 and float(row["downside_risk_score"]) < 0.50:
        hold_reasons.extend(["strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"])
        return {
            "action": "ADD",
            "action_reason": "|".join(hold_reasons),
            "exit_reason": "",
        }

    if trend_score >= 0.50:
        hold_reasons.append("trend_continuation")
    if expected_edge > 0:
        hold_reasons.append("positive_expected_edge")
    if float(row["downside_risk_score"]) < 0.50:
        hold_reasons.append("downside_risk_contained")
    return {
        "action": "HOLD",
        "action_reason": "|".join(hold_reasons or ["hold_score_above_exit_threshold"]),
        "exit_reason": "",
    }


def normalize_holding_frame(holding: pd.DataFrame) -> pd.DataFrame:
    holding = holding.copy()
    if "target_date" not in holding.columns or "code" not in holding.columns:
        raise ValueError("holding snapshot must contain target_date and code")
    holding["target_date"] = holding["target_date"].astype(str)
    holding["code"] = holding["code"].astype(str)
    if "current_return" not in holding.columns and not {"entry_price", "current_price"}.issubset(holding.columns):
        raise ValueError("holding snapshot must contain current_return or entry_price/current_price")
    if "holding_days" not in holding.columns:
        holding["holding_days"] = 0
    if "position_size" not in holding.columns:
        holding["position_size"] = 0.0
    if "peak_return" not in holding.columns:
        holding["peak_return"] = np.nan
    return holding.drop_duplicates(["target_date", "code"], keep="first")


def normalize_opportunity_frame(opportunity: pd.DataFrame) -> pd.DataFrame:
    opportunity = opportunity.copy()
    if "target_date" not in opportunity.columns or "code" not in opportunity.columns:
        raise ValueError("opportunity artifact must contain target_date and code")
    opportunity["target_date"] = opportunity["target_date"].astype(str)
    opportunity["code"] = opportunity["code"].astype(str)
    return opportunity.drop_duplicates(["target_date", "code"], keep="first")


def read_feature_frame_for_dates(feature_path: Path, target_dates: list[str]) -> pd.DataFrame:
    if feature_path.suffix == ".parquet" and target_dates:
        try:
            return pd.read_parquet(feature_path, filters=[("target_date", "in", target_dates)])
        except Exception:
            pass
    feature = read_table(feature_path)
    if "target_date" not in feature.columns:
        raise ValueError("feature artifact must contain target_date")
    return feature[feature["target_date"].astype(str).isin(target_dates)].copy()


def calculate_current_return(frame: pd.DataFrame) -> pd.Series:
    if "current_return" in frame.columns:
        current_return = pd.to_numeric(frame["current_return"], errors="coerce")
    else:
        entry = pd.to_numeric(frame.get("entry_price", np.nan), errors="coerce")
        current = pd.to_numeric(frame.get("current_price", np.nan), errors="coerce")
        current_return = (current / entry) - 1.0
    return current_return.fillna(0.0).map(round_float)


def calculate_trend_continuation_score(frame: pd.DataFrame) -> pd.Series:
    return_5d = get_first_numeric_series(frame, ("feature__return_5d", "feature__price_momentum_return_5d"), 0.0)
    return_20d = get_first_numeric_series(frame, ("feature__return_20d", "feature__price_momentum_return_20d"), 0.0)
    trend = normalize_ratio_or_delta(get_first_numeric_series(frame, ("feature__close_over_ma_20d", "feature__trend_close_over_ma_20d"), 0.0))
    ma_ratio = get_first_numeric_series(frame, ("feature__ma_5_20_ratio", "feature__trend_ma_5_20_ratio"), 1.0)
    volume = get_first_numeric_series(frame, ("feature__volume_ratio_5d", "feature__volume_momentum_ratio_5d"), 1.0)
    score = (
        0.30 * normalize_range(return_5d, -0.08, 0.12)
        + 0.30 * normalize_range(return_20d, -0.15, 0.25)
        + 0.20 * normalize_range(trend, -0.12, 0.18)
        + 0.10 * normalize_range(ma_ratio - 1.0, -0.08, 0.08)
        + 0.10 * normalize_range(volume - 1.0, -0.50, 1.50)
    )
    return score.clip(0.0, 1.0)


def calculate_opportunity_continuation_score(frame: pd.DataFrame) -> pd.Series:
    edge = get_numeric_series(frame, "expected_edge_score", 0.0)
    rank = get_numeric_series(frame, "buy_rank", 999)
    edge_score = normalize_range(edge, -0.10, 0.20)
    rank_score = (1.0 - ((rank - 1.0) / 19.0)).clip(0.0, 1.0)
    return (0.65 * edge_score + 0.35 * rank_score).clip(0.0, 1.0)


def calculate_position_risk_score(frame: pd.DataFrame) -> pd.Series:
    downside = get_numeric_series(frame, "downside_risk_score", 0.50).clip(0.0, 1.0)
    volatility = get_first_numeric_series(frame, ("feature__volatility_20d", "feature__volatility_return_std_20d"), 0.0)
    current_return = get_numeric_series(frame, "current_return", 0.0)
    drawdown = get_numeric_series(frame, "drawdown_from_peak", 0.0)
    score = (
        0.45 * downside
        + 0.20 * (volatility / 0.08).clip(0.0, 1.0)
        + 0.20 * ((-current_return) / 0.10).clip(0.0, 1.0)
        + 0.15 * ((-drawdown) / 0.12).clip(0.0, 1.0)
    )
    return score.clip(0.0, 1.0)


def calculate_exit_score(frame: pd.DataFrame) -> pd.Series:
    trend = normalize_ratio_or_delta(get_first_numeric_series(frame, ("feature__close_over_ma_20d", "feature__trend_close_over_ma_20d"), 0.0))
    ma_ratio = get_first_numeric_series(frame, ("feature__ma_5_20_ratio", "feature__trend_ma_5_20_ratio"), 1.0)
    drawdown = get_numeric_series(frame, "drawdown_from_peak", 0.0)
    current_return = get_numeric_series(frame, "current_return", 0.0)
    downside = get_numeric_series(frame, "downside_risk_score", 0.50).clip(0.0, 1.0)
    risk_guard_bad = get_numeric_or_string_series(frame, "risk_guard_status", "").fillna("").astype(str).str.lower().isin(
        {"bad", "ng", "blocked", "risk_bad", "high_risk"}
    )
    score = (
        0.25 * normalize_range(-trend, -0.08, 0.12)
        + 0.20 * normalize_range(1.0 - ma_ratio, -0.04, 0.08)
        + 0.25 * normalize_range(-drawdown, 0.02, 0.14)
        + 0.15 * normalize_range(-current_return, -0.03, 0.10)
        + 0.15 * downside
    )
    return score.clip(0.0, 1.0).where(~risk_guard_bad, 1.0)


def calculate_add_score(frame: pd.DataFrame) -> pd.Series:
    current_return = get_numeric_series(frame, "current_return", 0.0)
    trend_score = calculate_trend_continuation_score(frame)
    edge = get_numeric_series(frame, "expected_edge_score", 0.0)
    rank = get_numeric_series(frame, "buy_rank", 999)
    downside = get_numeric_series(frame, "downside_risk_score", 0.50).clip(0.0, 1.0)
    profit_ok = (current_return > 0).astype(float)
    score = (
        0.25 * profit_ok
        + 0.30 * trend_score
        + 0.20 * normalize_range(edge, 0.0, 0.20)
        + 0.15 * (1.0 - ((rank - 1.0) / 9.0)).clip(0.0, 1.0)
        + 0.10 * (1.0 - downside)
    )
    return score.clip(0.0, 1.0).where(current_return > 0, 0.0)


def calculate_reduce_score(frame: pd.DataFrame) -> pd.Series:
    trend_score = calculate_trend_continuation_score(frame)
    risk_score = calculate_position_risk_score(frame)
    drawdown = get_numeric_series(frame, "drawdown_from_peak", 0.0)
    downside = get_numeric_series(frame, "downside_risk_score", 0.50).clip(0.0, 1.0)
    score = (
        0.30 * trend_score
        + 0.30 * risk_score
        + 0.25 * normalize_range(-drawdown, 0.03, 0.10)
        + 0.15 * downside
    )
    return score.clip(0.0, 1.0)


def audit_position_feature_frame(frame: pd.DataFrame, *, input_holding_count: int, created_at: str | None = None) -> dict[str, Any]:
    created_at = created_at or now_utc()
    feature_columns = [column for column in frame.columns if str(column).startswith("feature__")]
    forbidden_feature_columns = [
        column for column in feature_columns if is_forbidden_position_feature_column(column.replace("feature__", "", 1))
    ]
    forbidden_input_columns = [
        column for column in frame.columns if is_forbidden_position_feature_column(str(column)) and not str(column).startswith("feature__")
    ]
    label_columns = [column for column in frame.columns if str(column).startswith("label__")]
    as_of_violations = count_as_of_date_violations(frame)
    leakage_ok = not (forbidden_feature_columns or forbidden_input_columns or label_columns or as_of_violations)
    return {
        "phase": PHASE,
        "created_at": created_at,
        "input_holding_count": int(input_holding_count),
        "joined_row_count": int(len(frame)),
        "join_success_rate": rate(len(frame), input_holding_count),
        "feature_column_count": len(feature_columns),
        "forbidden_feature_column_count": len(forbidden_feature_columns),
        "forbidden_feature_columns": forbidden_feature_columns,
        "forbidden_input_column_count": len(forbidden_input_columns),
        "forbidden_input_columns": forbidden_input_columns,
        "future_feature_column_count": len(
            [
                column
                for column in forbidden_feature_columns
                if column.replace("feature__", "", 1).startswith(("future_return_", "future_max_return_", "future_max_drawdown_", "top_decile_", "downside_bad_"))
            ]
        ),
        "label_column_count": len(label_columns),
        "as_of_date_violation_count": as_of_violations,
        "broker_api_executed": False,
        "order_executed": False,
        "paper_trading_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "leakage_audit_status": "OK" if leakage_ok else "ERROR",
        "readiness_status": READY_FOR_PHASE6_VALIDATION if leakage_ok else BLOCKED_BY_LEAKAGE_AUDIT,
    }


def build_summary(
    *,
    readiness_status: str,
    status: str,
    holding_path: Path,
    opportunity_path: Path,
    feature_path: Path,
    output_path: Path,
    action_csv_path: Path,
    summary_path: Path,
    audit_path: Path,
    created_at: str,
    audit: dict[str, Any],
    output_count: int,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": status,
        "readiness_status": readiness_status,
        "created_at": created_at,
        "model_version": MODEL_VERSION,
        "holding_path": str(holding_path),
        "opportunity_path": str(opportunity_path),
        "feature_path": str(feature_path),
        "output_path": str(output_path),
        "action_csv_path": str(action_csv_path),
        "summary_path": str(summary_path),
        "audit_path": str(audit_path),
        "input_holding_count": int(audit.get("input_holding_count", 0)),
        "joined_row_count": int(audit.get("joined_row_count", 0)),
        "output_count": int(output_count),
        "hold_count": int(audit.get("hold_count", 0)),
        "exit_count": int(audit.get("exit_count", 0)),
        "add_candidate_count": int(audit.get("add_candidate_count", 0)),
        "reduce_count": int(audit.get("reduce_count", 0)),
        "forbidden_feature_column_count": int(audit.get("forbidden_feature_column_count", 0)),
        "forbidden_input_column_count": int(audit.get("forbidden_input_column_count", 0)),
        "future_feature_column_count": int(audit.get("future_feature_column_count", 0)),
        "label_column_count": int(audit.get("label_column_count", 0)),
        "as_of_date_violation_count": int(audit.get("as_of_date_violation_count", 0)),
        "leakage_audit_status": audit.get("leakage_audit_status", "NOT_RUN"),
        "inference_executed": status == "OK",
        "training_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "recommended_next_action": (
            "Proceed to Phase6 validation / profit_retention audit."
            if readiness_status == READY_FOR_PHASE6_VALIDATION
            else "Fix Phase6 Position Management inference blocker before validation."
        ),
    }


def _blocked_result(
    readiness_status: str,
    reason: str,
    *,
    holding_path: Path,
    opportunity_path: Path,
    feature_path: Path,
    output_path: Path,
    action_csv_path: Path,
    summary_path: Path,
    audit_path: Path,
    created_at: str,
) -> PositionManagementInferenceResult:
    audit = {
        "phase": PHASE,
        "created_at": created_at,
        "input_holding_count": 0,
        "joined_row_count": 0,
        "feature_column_count": 0,
        "forbidden_feature_column_count": 0,
        "forbidden_feature_columns": [],
        "forbidden_input_column_count": 0,
        "forbidden_input_columns": [],
        "future_feature_column_count": 0,
        "label_column_count": 0,
        "as_of_date_violation_count": 0,
        "leakage_audit_status": "NOT_RUN",
        "readiness_status": readiness_status,
        "block_reason": reason,
    }
    summary = build_summary(
        readiness_status=readiness_status,
        status="BLOCKED",
        holding_path=holding_path,
        opportunity_path=opportunity_path,
        feature_path=feature_path,
        output_path=output_path,
        action_csv_path=action_csv_path,
        summary_path=summary_path,
        audit_path=audit_path,
        created_at=created_at,
        audit=audit,
        output_count=0,
    )
    summary["block_reason"] = reason
    write_json(summary_path, summary)
    write_json(audit_path, audit)
    return PositionManagementInferenceResult(output=pd.DataFrame(columns=OUTPUT_COLUMNS), summary=summary, audit=audit)


def is_forbidden_position_feature_column(column: str) -> bool:
    normalized = column.strip().lower().replace("-", "_")
    if normalized.startswith(FORBIDDEN_FEATURE_PREFIXES):
        return True
    return contains_any(normalized, FORBIDDEN_FEATURE_TERMS)


def normalize_range(values: pd.Series, lower: float, upper: float) -> pd.Series:
    if upper == lower:
        return pd.Series(0.0, index=values.index)
    return ((values - lower) / (upper - lower)).clip(0.0, 1.0)


def normalize_ratio_or_delta(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").fillna(0.0)
    if numeric.abs().median() > 0.50:
        return numeric - 1.0
    return numeric


def get_numeric_series(frame: pd.DataFrame, column: str, default: float) -> pd.Series:
    if column in frame.columns:
        values = frame[column]
    else:
        values = pd.Series(default, index=frame.index)
    return pd.to_numeric(values, errors="coerce").fillna(default)


def get_first_numeric_series(frame: pd.DataFrame, columns: tuple[str, ...], default: float) -> pd.Series:
    for column in columns:
        if column in frame.columns:
            return get_numeric_series(frame, column, default)
    return pd.Series(default, index=frame.index)


def get_numeric_or_string_series(frame: pd.DataFrame, column: str, default: str) -> pd.Series:
    if column in frame.columns:
        return frame[column]
    return pd.Series(default, index=frame.index)


def count_as_of_date_violations(frame: pd.DataFrame) -> int:
    if "as_of_date" not in frame.columns or "target_date" not in frame.columns:
        return 0
    as_of = pd.to_datetime(frame["as_of_date"], errors="coerce")
    target = pd.to_datetime(frame["target_date"], errors="coerce")
    return int(((as_of > target) | as_of.isna() | target.isna()).sum())


def optional_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> list[str]:
    return [column for column in columns if column in frame.columns]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def round_float(value: Any, digits: int = 8) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(numeric) or math.isinf(numeric):
        return 0.0
    return round(numeric, digits)


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
