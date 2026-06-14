from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.training import to_jsonable
from ai_fund_lab_v2.position_management_ai.alignment_audit import (
    DEFAULT_PHASE6C_DATASET_PATH,
    READY_FOR_PHASE6E_BASELINE_REVIEW,
    action_distribution,
    alignment_metrics,
    apply_baseline_to_label_dataset,
    build_alignment_table,
    build_summary,
    dataset_to_inference_frame,
    extract_mismatches,
    label_distribution,
)
from ai_fund_lab_v2.position_management_ai.inference import (
    FEATURE_VERSION,
    MODEL_VERSION,
    audit_position_feature_frame,
    calculate_add_score,
    calculate_exit_score,
    calculate_reduce_score,
    calculate_trend_continuation_score,
    get_first_numeric_series,
    get_numeric_series,
    round_float,
)
from ai_fund_lab_v2.position_management_ai.label_dataset import audit_position_label_dataset, run_phase6c_position_label_dataset_dry_run

PHASE = "Phase6-E"
CALIBRATED_MODEL_VERSION = "position_management_policy_phase6e_calibrated_v1"
READY_FOR_PHASE6F_POLICY_REVIEW = "READY_FOR_PHASE6F_POLICY_REVIEW"
BLOCKED_BY_CALIBRATION_AUDIT = "BLOCKED_BY_CALIBRATION_AUDIT"

DEFAULT_ALIGNMENT_CSV_PATH = Path("reports/position_management_ai/phase6e_calibrated_baseline_alignment.csv")
DEFAULT_ALIGNMENT_JSON_PATH = Path("reports/position_management_ai/phase6e_calibrated_baseline_alignment.json")
DEFAULT_MISMATCH_CSV_PATH = Path("reports/position_management_ai/phase6e_calibrated_baseline_mismatches.csv")
DEFAULT_AUDIT_PATH = Path("reports/position_management_ai/phase6e_calibrated_baseline_audit.json")
DEFAULT_COMPARISON_PATH = Path("reports/position_management_ai/phase6e_old_vs_calibrated_comparison.json")


@dataclass(frozen=True)
class Phase6ECalibrationResult:
    alignment: pd.DataFrame
    mismatches: pd.DataFrame
    summary: dict[str, Any]
    audit: dict[str, Any]
    comparison: dict[str, Any]


def run_phase6e_baseline_calibration(
    *,
    dataset_path: Path = DEFAULT_PHASE6C_DATASET_PATH,
    alignment_csv_path: Path = DEFAULT_ALIGNMENT_CSV_PATH,
    alignment_json_path: Path = DEFAULT_ALIGNMENT_JSON_PATH,
    mismatch_csv_path: Path = DEFAULT_MISMATCH_CSV_PATH,
    audit_path: Path = DEFAULT_AUDIT_PATH,
    comparison_path: Path = DEFAULT_COMPARISON_PATH,
    created_at: str | None = None,
) -> Phase6ECalibrationResult:
    created_at = created_at or now_utc()
    if not dataset_path.is_file():
        run_phase6c_position_label_dataset_dry_run(created_at=created_at)
    dataset = pd.read_csv(dataset_path, dtype={"code": str})
    old_frame = apply_baseline_to_label_dataset(dataset, created_at=created_at)
    calibrated_frame = apply_calibrated_baseline_to_label_dataset(dataset, created_at=created_at)

    label_audit = audit_position_label_dataset(dataset, created_at=created_at)
    feature_audit = audit_position_feature_frame(dataset_to_inference_frame(dataset), input_holding_count=len(dataset), created_at=created_at)
    readiness_status = (
        READY_FOR_PHASE6F_POLICY_REVIEW
        if label_audit["label_leakage_audit_status"] == "OK" and feature_audit["leakage_audit_status"] == "OK"
        else BLOCKED_BY_CALIBRATION_AUDIT
    )

    alignment = build_alignment_table(calibrated_frame)
    mismatches = extract_mismatches(calibrated_frame)
    old_mismatches = extract_mismatches(old_frame)
    audit = build_calibrated_audit(
        calibrated_frame=calibrated_frame,
        mismatches=mismatches,
        label_audit=label_audit,
        feature_audit=feature_audit,
        readiness_status=readiness_status,
        created_at=created_at,
    )
    summary = build_summary(
        alignment=alignment,
        mismatches=mismatches,
        audit=audit,
        dataset_path=dataset_path,
        alignment_csv_path=alignment_csv_path,
        alignment_json_path=alignment_json_path,
        mismatch_csv_path=mismatch_csv_path,
        audit_path=audit_path,
        created_at=created_at,
        readiness_status=READY_FOR_PHASE6E_BASELINE_REVIEW if readiness_status == READY_FOR_PHASE6F_POLICY_REVIEW else readiness_status,
    )
    summary = {
        **summary,
        "phase": PHASE,
        "readiness_status": readiness_status,
        "status": "OK" if readiness_status == READY_FOR_PHASE6F_POLICY_REVIEW else "BLOCKED",
        "model_version": CALIBRATED_MODEL_VERSION,
    }
    comparison = build_old_vs_calibrated_comparison(old_frame=old_frame, calibrated_frame=calibrated_frame, old_mismatches=old_mismatches, calibrated_mismatches=mismatches)

    alignment_csv_path.parent.mkdir(parents=True, exist_ok=True)
    alignment.to_csv(alignment_csv_path, index=False)
    mismatches.to_csv(mismatch_csv_path, index=False)
    write_json(alignment_json_path, summary)
    write_json(audit_path, audit)
    write_json(comparison_path, comparison)
    return Phase6ECalibrationResult(alignment=alignment, mismatches=mismatches, summary=summary, audit=audit, comparison=comparison)


def apply_calibrated_baseline_to_label_dataset(dataset: pd.DataFrame, *, created_at: str) -> pd.DataFrame:
    inference_frame = dataset_to_inference_frame(dataset)
    output = build_calibrated_position_management_output(inference_frame, created_at=created_at)
    label_columns = [
        "target_date",
        "entry_date",
        "code",
        "label__label_continue_winner",
        "label__label_exit_before_drawdown",
        "label__label_add_candidate",
        "label__label_reduce_candidate",
    ]
    return dataset[label_columns + ["feature__unrealized_return"]].merge(
        output[
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
            ]
        ],
        on=["target_date", "code"],
        how="inner",
        validate="one_to_one",
    )


def build_calibrated_position_management_output(frame: pd.DataFrame, *, created_at: str) -> pd.DataFrame:
    scored = frame.copy()
    scored["current_return"] = get_numeric_series(scored, "current_return", 0.0)
    scored["peak_return"] = get_numeric_series(scored, "peak_return", scored["current_return"].median())
    scored["drawdown_from_peak"] = (scored["current_return"] - scored["peak_return"]).map(round_float)
    scored["downside_risk_score"] = get_numeric_series(scored, "downside_risk_score", 0.50).clip(0.0, 1.0)
    scored["expected_edge_score"] = get_numeric_series(scored, "expected_edge_score", 0.0)
    scored["buy_rank"] = get_numeric_series(scored, "buy_rank", 999).astype(int)
    scored["hold_score"] = (
        0.45 * calculate_trend_continuation_score(scored)
        + 0.25 * (scored["expected_edge_score"].clip(lower=-0.05, upper=0.20) + 0.05) / 0.25
        + 0.20 * (1.0 - scored["downside_risk_score"])
        + 0.10 * (scored["current_return"] > 0).astype(float)
    ).clip(0.0, 1.0).map(round_float)
    scored["exit_score"] = calculate_exit_score(scored).map(round_float)
    scored["add_score"] = calculate_add_score(scored).map(round_float)
    scored["reduce_score"] = calculate_reduce_score(scored).map(round_float)
    actions = scored.apply(classify_calibrated_action, axis=1)
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
    scored["model_version"] = CALIBRATED_MODEL_VERSION
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


def classify_calibrated_action(row: pd.Series) -> dict[str, str]:
    current_return = float(row["current_return"])
    drawdown = float(row["drawdown_from_peak"])
    expected_edge = float(row["expected_edge_score"])
    buy_rank = int(row["buy_rank"])
    downside = float(row["downside_risk_score"])
    risk_guard_bad = str(row.get("risk_guard_status", "")).lower() in {"bad", "ng", "blocked", "risk_bad", "high_risk"}
    close_over_ma20 = float(get_first_numeric_series(pd.DataFrame([row]), ("feature__close_over_ma_20d", "feature__trend_close_over_ma_20d"), 1.0).iloc[0])
    ma_5_20 = float(get_first_numeric_series(pd.DataFrame([row]), ("feature__ma_5_20_ratio", "feature__trend_ma_5_20_ratio"), 1.0).iloc[0])
    trend_score = float(calculate_trend_continuation_score(pd.DataFrame([row])).iloc[0])
    trend_broken = close_over_ma20 < 0.97 and ma_5_20 < 0.97
    soft_trend_ok = close_over_ma20 >= 0.98 and ma_5_20 >= 0.98

    if (
        risk_guard_bad
        and current_return <= -0.01
        and (trend_broken or downside >= 0.75 or drawdown <= -0.10)
    ) or (
        current_return <= -0.12 and trend_broken
    ):
        return {"action": "EXIT", "action_reason": "calibrated_exit_strict", "exit_reason": "risk_guard_or_trend_break_with_loss"}

    if (
        current_return > 0
        and current_return <= 0.055
        and expected_edge >= 0.12
        and buy_rank <= 5
        and downside <= 0.45
        and not risk_guard_bad
        and soft_trend_ok
        and drawdown > -0.05
    ):
        return {"action": "ADD", "action_reason": "calibrated_add_safe_early_winner", "exit_reason": ""}

    if (
        current_return > 0
        and expected_edge >= 0.08
        and buy_rank <= 5
        and downside <= 0.50
        and not risk_guard_bad
        and drawdown > -0.06
        and close_over_ma20 >= 0.98
        and ma_5_20 >= 0.98
    ):
        return {"action": "HOLD", "action_reason": "calibrated_hold_winner", "exit_reason": ""}

    if (
        current_return > 0
        and (downside >= 0.65 or (downside >= 0.60 and drawdown <= -0.015 and buy_rank <= 10))
        and not (expected_edge >= 0.08 and buy_rank <= 5 and downside <= 0.50)
    ):
        return {"action": "REDUCE", "action_reason": "calibrated_reduce_profit_risk", "exit_reason": ""}

    if risk_guard_bad and current_return < 0:
        return {"action": "REDUCE", "action_reason": "calibrated_reduce_risk_guard_loss", "exit_reason": ""}

    return {"action": "HOLD", "action_reason": "calibrated_hold_default", "exit_reason": ""}


def build_calibrated_audit(
    *,
    calibrated_frame: pd.DataFrame,
    mismatches: pd.DataFrame,
    label_audit: dict[str, Any],
    feature_audit: dict[str, Any],
    readiness_status: str,
    created_at: str,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "created_at": created_at,
        "readiness_status": readiness_status,
        "row_count": int(len(calibrated_frame)),
        "action_distribution": action_distribution(calibrated_frame),
        "label_distribution": label_distribution(calibrated_frame),
        "alignment_metrics": alignment_metrics(calibrated_frame),
        "mismatch_count": int(len(mismatches)),
        "add_loss_position_count": int(((calibrated_frame["action"] == "ADD") & (calibrated_frame["feature__unrealized_return"] <= 0)).sum()),
        "add_exit_label_overlap_count": int(((calibrated_frame["action"] == "ADD") & (calibrated_frame["label__label_exit_before_drawdown"])).sum()),
        "exit_continue_winner_count": int(((calibrated_frame["action"] == "EXIT") & (calibrated_frame["label__label_continue_winner"])).sum()),
        "reduce_continue_winner_count": int(((calibrated_frame["action"] == "REDUCE") & (calibrated_frame["label__label_continue_winner"])).sum()),
        "label_audit": label_audit,
        "feature_audit": feature_audit,
        "forbidden_feature_audit_status": "OK" if feature_audit["leakage_audit_status"] == "OK" and label_audit["forbidden_feature_audit_status"] == "OK" else "ERROR",
        "leakage_audit_status": "OK" if readiness_status == READY_FOR_PHASE6F_POLICY_REVIEW else "ERROR",
        "training_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
    }


def build_old_vs_calibrated_comparison(
    *,
    old_frame: pd.DataFrame,
    calibrated_frame: pd.DataFrame,
    old_mismatches: pd.DataFrame,
    calibrated_mismatches: pd.DataFrame,
) -> dict[str, Any]:
    old_metrics = alignment_metrics(old_frame)
    calibrated_metrics = alignment_metrics(calibrated_frame)
    return {
        "phase": PHASE,
        "old_model_version": MODEL_VERSION,
        "calibrated_model_version": CALIBRATED_MODEL_VERSION,
        "row_count": int(len(calibrated_frame)),
        "old_action_distribution": action_distribution(old_frame),
        "calibrated_action_distribution": action_distribution(calibrated_frame),
        "old_alignment_metrics": old_metrics,
        "calibrated_alignment_metrics": calibrated_metrics,
        "old_mismatch_count": int(len(old_mismatches)),
        "calibrated_mismatch_count": int(len(calibrated_mismatches)),
        "mismatch_delta": int(len(calibrated_mismatches) - len(old_mismatches)),
        "old_add_loss_position_count": int(((old_frame["action"] == "ADD") & (old_frame["feature__unrealized_return"] <= 0)).sum()),
        "calibrated_add_loss_position_count": int(((calibrated_frame["action"] == "ADD") & (calibrated_frame["feature__unrealized_return"] <= 0)).sum()),
        "old_add_exit_label_overlap_count": int(((old_frame["action"] == "ADD") & (old_frame["label__label_exit_before_drawdown"])).sum()),
        "calibrated_add_exit_label_overlap_count": int(((calibrated_frame["action"] == "ADD") & (calibrated_frame["label__label_exit_before_drawdown"])).sum()),
        "old_exit_continue_winner_count": int(((old_frame["action"] == "EXIT") & (old_frame["label__label_continue_winner"])).sum()),
        "calibrated_exit_continue_winner_count": int(((calibrated_frame["action"] == "EXIT") & (calibrated_frame["label__label_continue_winner"])).sum()),
        "continue_winner_hold_or_add_old_count": int((old_frame[old_frame["label__label_continue_winner"]]["action"].isin(["HOLD", "ADD"])).sum()),
        "continue_winner_hold_or_add_calibrated_count": int((calibrated_frame[calibrated_frame["label__label_continue_winner"]]["action"].isin(["HOLD", "ADD"])).sum()),
        "exit_before_drawdown_exit_or_reduce_old_count": int((old_frame[old_frame["label__label_exit_before_drawdown"]]["action"].isin(["EXIT", "REDUCE"])).sum()),
        "exit_before_drawdown_exit_or_reduce_calibrated_count": int((calibrated_frame[calibrated_frame["label__label_exit_before_drawdown"]]["action"].isin(["EXIT", "REDUCE"])).sum()),
    }


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
