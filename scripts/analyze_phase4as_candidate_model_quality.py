#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import pickle
import statistics
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts.train_phase4ap_candidate_smoke import (  # noqa: E402
    TARGET_LABEL,
    build_smoke_time_series_split,
)

PHASE = "Phase4-AS"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4as_candidate_model_quality_root_cause_summary.json")
PHASE4AO_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ao_dataset_retry_summary.json")
PHASE4AP_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ap_candidate_training_smoke_summary.json")
PHASE4AQ_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4aq_candidate_inference_smoke_summary.json")
PHASE4AR_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ar_candidate_output_smoke_summary.json")

READY = "READY_FOR_MODEL_FIX_PLAN"
BLOCKED_MODEL = "BLOCKED_BY_MISSING_MODEL_ARTIFACT"
BLOCKED_DATASET = "BLOCKED_BY_MISSING_DATASET"
BLOCKED_ANALYSIS = "BLOCKED_BY_ANALYSIS_FAILURE"

HIGH_NULL_THRESHOLD = 0.5
NEAR_CONSTANT_DOMINANCE_THRESHOLD = 0.99


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze Phase4-AS Candidate model quality root cause.")
    parser.add_argument("--phase4ao-summary", default=str(PHASE4AO_SUMMARY_PATH))
    parser.add_argument("--phase4ap-summary", default=str(PHASE4AP_SUMMARY_PATH))
    parser.add_argument("--phase4aq-summary", default=str(PHASE4AQ_SUMMARY_PATH))
    parser.add_argument("--phase4ar-summary", default=str(PHASE4AR_SUMMARY_PATH))
    parser.add_argument("--summary-path", default=str(SUMMARY_PATH))
    args = parser.parse_args(argv)
    summary = analyze_phase4as_candidate_model_quality(
        phase4ao_summary_path=Path(args.phase4ao_summary),
        phase4ap_summary_path=Path(args.phase4ap_summary),
        phase4aq_summary_path=Path(args.phase4aq_summary),
        phase4ar_summary_path=Path(args.phase4ar_summary),
        summary_path=Path(args.summary_path),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def analyze_phase4as_candidate_model_quality(
    *,
    phase4ao_summary_path: Path = PHASE4AO_SUMMARY_PATH,
    phase4ap_summary_path: Path = PHASE4AP_SUMMARY_PATH,
    phase4aq_summary_path: Path = PHASE4AQ_SUMMARY_PATH,
    phase4ar_summary_path: Path = PHASE4AR_SUMMARY_PATH,
    summary_path: Path = SUMMARY_PATH,
) -> dict[str, Any]:
    ao_summary = _read_json_optional(phase4ao_summary_path)
    ap_summary = _read_json_optional(phase4ap_summary_path)
    aq_summary = _read_json_optional(phase4aq_summary_path)
    ar_summary = _read_json_optional(phase4ar_summary_path)
    model_path = Path(str(ap_summary.get("model_artifact_path") or ""))
    model_manifest_path = Path(str(ap_summary.get("model_manifest_path") or ""))
    dataset_path = Path(str(ao_summary.get("dataset_output_path") or ""))
    latest_inference_path = Path(str(aq_summary.get("inference_output_path") or ""))

    if not model_path.is_file() or not model_manifest_path.is_file():
        summary = _blocked_summary(BLOCKED_MODEL, "Phase4-AP model artifact or manifest is missing.", summary_path)
        _write_json(summary_path, summary)
        return summary
    if not dataset_path.is_file():
        summary = _blocked_summary(BLOCKED_DATASET, "Phase4-AO dataset artifact is missing.", summary_path)
        _write_json(summary_path, summary)
        return summary

    try:
        model_payload = _read_pickle(model_path)
        model = model_payload["model"]
        feature_columns = [str(column) for column in model_payload.get("feature_columns", [])]
        model_type = str(model_payload.get("model_type") or ap_summary.get("model_type") or type(model).__name__)
        dataset_rows = _rows(_read_json_optional(dataset_path))
        split = build_smoke_time_series_split(dataset_rows)
        train_rows = [dataset_rows[index] for index in split["train_indices"]]
        validation_rows = [dataset_rows[index] for index in split["validation_indices"]]
        y_train = _target_array(train_rows)
        y_validation = _target_array(validation_rows)
        feature_stats = analyze_feature_stats(dataset_rows, feature_columns)
        train_predictions = predict_scores(model, feature_matrix(train_rows, feature_columns)) if train_rows else np.asarray([])
        validation_predictions = predict_scores(model, feature_matrix(validation_rows, feature_columns)) if validation_rows else np.asarray([])
        latest_scores = latest_prediction_scores(latest_inference_path)
        importance = extract_feature_importance(model, feature_columns)
        tree_stats = extract_tree_stats(model)
        root_cause = determine_root_causes(
            feature_stats=feature_stats,
            importance=importance,
            tree_stats=tree_stats,
            train_predictions=train_predictions,
            validation_predictions=validation_predictions,
            latest_predictions=latest_scores,
            y_train=y_train,
            y_validation=y_validation,
            ar_summary=ar_summary,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        summary = _blocked_summary(BLOCKED_ANALYSIS, f"Analysis failed: {type(exc).__name__}", summary_path)
        _write_json(summary_path, summary)
        return summary

    train_positive_count = int(y_train.sum()) if len(y_train) else 0
    validation_positive_count = int(y_validation.sum()) if len(y_validation) else 0
    summary = {
        "phase": PHASE,
        "status": "OK",
        "readiness_status": READY,
        "root_cause_analysis_executed": True,
        "model_type": model_type,
        "dataset_row_count": len(dataset_rows),
        "smoke_train_row_count": len(train_rows),
        "smoke_validation_row_count": len(validation_rows),
        "train_positive_count": train_positive_count,
        "validation_positive_count": validation_positive_count,
        "train_positive_rate": _rate(train_positive_count, len(train_rows)),
        "validation_positive_rate": _rate(validation_positive_count, len(validation_rows)),
        "feature_column_count": len(feature_columns),
        "constant_feature_count": feature_stats["constant_feature_count"],
        "near_constant_feature_count": feature_stats["near_constant_feature_count"],
        "high_null_feature_count": feature_stats["high_null_feature_count"],
        "feature_importance_nonzero_count": importance["feature_importance_nonzero_count"],
        "tree_count": tree_stats["tree_count"],
        "effective_split_count": tree_stats["effective_split_count"],
        "train_prediction_unique_count": prediction_stats(train_predictions)["unique_count"],
        "validation_prediction_unique_count": prediction_stats(validation_predictions)["unique_count"],
        "latest_prediction_unique_count": prediction_stats(latest_scores)["unique_count"],
        "train_prediction_std": prediction_stats(train_predictions)["std"],
        "validation_prediction_std": prediction_stats(validation_predictions)["std"],
        "latest_prediction_std": prediction_stats(latest_scores)["std"],
        "all_same_score_direct_cause": root_cause["all_same_score_direct_cause"],
        "likely_root_causes": root_cause["likely_root_causes"],
        "blocking_issue": root_cause["blocking_issue"],
        "recommended_fix_plan": root_cause["recommended_fix_plan"],
        "retraining_recommended": True,
        "more_history_required": True,
        "feature_improvement_required": True,
        "label_review_required": root_cause["label_review_required"],
        "feature_stats": feature_stats,
        "feature_importance": importance["feature_importance"],
        "smoke_train_date_min": split["train_date_min"],
        "smoke_train_date_max": split["train_date_max"],
        "smoke_validation_date_min": split["validation_date_min"],
        "smoke_validation_date_max": split["validation_date_max"],
        "phase4ar_readiness_status": ar_summary.get("readiness_status"),
        "backtest_executed": False,
        "trading_executed": False,
        "recommended_next_action": "Phase4-AT Candidate Model Fix Plan; do not backtest or trade.",
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    _write_markdown_report(Path("docs/phase_reports/phase4as_candidate_model_quality_root_cause.md"), summary)
    return summary


def analyze_feature_stats(rows: list[dict[str, Any]], feature_columns: list[str]) -> dict[str, Any]:
    per_feature: dict[str, dict[str, Any]] = {}
    constant_count = 0
    near_constant_count = 0
    high_null_count = 0
    for column in feature_columns:
        values = [_numeric_value(row.get(column)) for row in rows]
        non_null = [value for value in values if not math.isnan(value)]
        null_rate = 1.0 - (len(non_null) / len(values)) if values else 1.0
        unique_count = len({round(value, 12) for value in non_null})
        constant = unique_count <= 1
        dominance = _dominance_ratio(non_null)
        near_constant = constant or dominance >= NEAR_CONSTANT_DOMINANCE_THRESHOLD
        high_null = null_rate >= HIGH_NULL_THRESHOLD
        constant_count += int(constant)
        near_constant_count += int(near_constant)
        high_null_count += int(high_null)
        per_feature[column] = {
            "null_rate": round(null_rate, 6),
            "unique_count": unique_count,
            "constant": constant,
            "near_constant": near_constant,
            "dominance_ratio": round(dominance, 6),
            "mean": round(statistics.fmean(non_null), 6) if non_null else None,
            "std": round(statistics.pstdev(non_null), 6) if len(non_null) > 1 else 0.0,
        }
    return {
        "constant_feature_count": constant_count,
        "near_constant_feature_count": near_constant_count,
        "high_null_feature_count": high_null_count,
        "per_feature": per_feature,
    }


def extract_feature_importance(model: Any, feature_columns: list[str]) -> dict[str, Any]:
    raw = getattr(model, "feature_importances_", None)
    if raw is None and hasattr(model, "coef_"):
        raw = np.abs(np.asarray(model.coef_)).ravel()
    if raw is None:
        values = [0.0 for _ in feature_columns]
    else:
        values = [float(value) for value in list(raw)]
    pairs = {
        column: values[index] if index < len(values) else 0.0
        for index, column in enumerate(feature_columns)
    }
    return {
        "feature_importance_nonzero_count": sum(1 for value in pairs.values() if value != 0),
        "feature_importance": pairs,
    }


def extract_tree_stats(model: Any) -> dict[str, int]:
    if hasattr(model, "booster_"):
        dump = model.booster_.dump_model()
        tree_info = dump.get("tree_info", [])
        return {
            "tree_count": len(tree_info),
            "effective_split_count": sum(_count_splits(tree.get("tree_structure", {})) for tree in tree_info),
        }
    if hasattr(model, "coef_"):
        return {"tree_count": 0, "effective_split_count": int(np.count_nonzero(model.coef_))}
    if hasattr(model, "n_iter_"):
        value = getattr(model, "n_iter_", 0)
        if isinstance(value, np.ndarray):
            value = int(value.ravel()[0]) if value.size else 0
        return {"tree_count": int(value), "effective_split_count": int(value)}
    return {"tree_count": 0, "effective_split_count": 0}


def determine_root_causes(
    *,
    feature_stats: dict[str, Any],
    importance: dict[str, Any],
    tree_stats: dict[str, int],
    train_predictions: np.ndarray,
    validation_predictions: np.ndarray,
    latest_predictions: np.ndarray,
    y_train: np.ndarray,
    y_validation: np.ndarray,
    ar_summary: dict[str, Any],
) -> dict[str, Any]:
    causes: list[str] = []
    if tree_stats["effective_split_count"] == 0:
        causes.append("model_has_no_effective_splits")
    if importance["feature_importance_nonzero_count"] == 0:
        causes.append("all_feature_importance_zero")
        causes.append("current_features_do_not_explain_momentum_candidate_label_in_smoke_window")
    if prediction_stats(train_predictions)["unique_count"] <= 1:
        causes.append("train_predictions_are_constant")
    if prediction_stats(validation_predictions)["unique_count"] <= 1:
        causes.append("validation_predictions_are_constant")
    if prediction_stats(latest_predictions)["unique_count"] <= 1:
        causes.append("latest_inference_predictions_are_constant")
    if feature_stats["near_constant_feature_count"] > 0:
        causes.append("some_features_are_constant_or_near_constant")
    if feature_stats["high_null_feature_count"] > 0:
        causes.append("some_features_have_high_null_rate")
    if len(y_train) and min(_rate(int(y_train.sum()), len(y_train)), 1 - _rate(int(y_train.sum()), len(y_train))) < 0.15:
        causes.append("train_label_class_imbalance")
    if len(y_validation) and min(_rate(int(y_validation.sum()), len(y_validation)), 1 - _rate(int(y_validation.sum()), len(y_validation))) < 0.15:
        causes.append("validation_label_class_imbalance")
    causes.append("only_60_business_days_available_for_smoke_training")
    causes.append("formal_train_validation_periods_are_missing")

    if tree_stats["effective_split_count"] == 0:
        direct = "LightGBM produced a one-leaf model with zero effective splits, so every inference row receives the same base probability."
    elif prediction_stats(latest_predictions)["unique_count"] <= 1:
        direct = "Latest inference feature distribution falls into the same model output path for every eligible row."
    else:
        direct = "Candidate scores are not all same in the analyzed predictions."

    fix_plan = [
        "Design Phase4-AT model fix plan before any retraining.",
        "Tune LightGBM smoke parameters such as min_child_samples, num_leaves, class_weight or scale_pos_weight.",
        "Train only on appropriate eligible rows or explicitly test eligible/excluded treatment.",
        "Add diagnostics for feature variance, null handling, and target-date grouped evaluation.",
        "Plan longer historical coverage before formal Candidate Quality Audit.",
        "Review whether current price/volume features explain momentum_candidate_label.",
    ]
    return {
        "all_same_score_direct_cause": direct,
        "likely_root_causes": causes,
        "blocking_issue": "candidate_scores_are_all_same_and_ranking_is_ineffective"
        if ar_summary.get("all_same_score") is True
        else "candidate_quality_not_yet_formally_validated",
        "recommended_fix_plan": fix_plan,
        "label_review_required": "current_features_do_not_explain_momentum_candidate_label_in_smoke_window" in causes,
    }


def prediction_stats(values: np.ndarray) -> dict[str, Any]:
    if values.size == 0:
        return {"unique_count": 0, "std": None}
    rounded = [round(float(value), 12) for value in values.tolist()]
    return {"unique_count": len(set(rounded)), "std": round(float(np.std(values)), 6)}


def predict_scores(model: Any, x_input: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(x_input)
        if proba.ndim == 2 and proba.shape[1] > 1:
            return np.asarray(proba[:, 1], dtype=float)
    if hasattr(model, "decision_function"):
        raw = np.asarray(model.decision_function(x_input), dtype=float)
        return 1.0 / (1.0 + np.exp(-raw))
    return np.asarray(model.predict(x_input), dtype=float)


def feature_matrix(rows: list[dict[str, Any]], feature_columns: list[str]) -> np.ndarray:
    return np.asarray([[_numeric_value(row.get(column)) for column in feature_columns] for row in rows], dtype=float)


def latest_prediction_scores(path: Path) -> np.ndarray:
    rows = _rows(_read_json_optional(path))
    return np.asarray([float(row.get("candidate_score")) for row in rows if row.get("candidate_score") is not None], dtype=float)


def _target_array(rows: list[dict[str, Any]]) -> np.ndarray:
    return np.asarray([1 if row.get(TARGET_LABEL) is True else 0 for row in rows], dtype=np.int8)


def _count_splits(node: dict[str, Any]) -> int:
    if not isinstance(node, dict) or "split_index" not in node:
        return 0
    return 1 + _count_splits(node.get("left_child", {})) + _count_splits(node.get("right_child", {}))


def _numeric_value(value: Any) -> float:
    if value is None:
        return math.nan
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _dominance_ratio(values: list[float]) -> float:
    if not values:
        return 1.0
    counts: dict[float, int] = {}
    for value in values:
        key = round(value, 12)
        counts[key] = counts.get(key, 0) + 1
    return max(counts.values()) / len(values)


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _blocked_summary(readiness_status: str, reason: str, summary_path: Path) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "block_reason": reason,
        "root_cause_analysis_executed": False,
        "model_type": None,
        "dataset_row_count": 0,
        "smoke_train_row_count": 0,
        "smoke_validation_row_count": 0,
        "train_positive_count": 0,
        "validation_positive_count": 0,
        "train_positive_rate": 0.0,
        "validation_positive_rate": 0.0,
        "feature_column_count": 0,
        "constant_feature_count": 0,
        "near_constant_feature_count": 0,
        "high_null_feature_count": 0,
        "feature_importance_nonzero_count": 0,
        "tree_count": 0,
        "effective_split_count": 0,
        "train_prediction_unique_count": 0,
        "validation_prediction_unique_count": 0,
        "latest_prediction_unique_count": 0,
        "train_prediction_std": None,
        "validation_prediction_std": None,
        "latest_prediction_std": None,
        "all_same_score_direct_cause": "",
        "likely_root_causes": [],
        "blocking_issue": reason,
        "recommended_fix_plan": [],
        "retraining_recommended": False,
        "more_history_required": False,
        "feature_improvement_required": False,
        "label_review_required": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(summary_path),
    }


def _write_markdown_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AS Candidate Model Quality Root Cause Analysis",
        "",
        "## Result",
        "",
        f"- status: {summary['status']}",
        f"- readiness_status: `{summary['readiness_status']}`",
        f"- model_type: `{summary['model_type']}`",
        f"- blocking_issue: `{summary['blocking_issue']}`",
        "",
        "## Direct Cause",
        "",
        summary["all_same_score_direct_cause"],
        "",
        "## Key Metrics",
        "",
        f"- train_positive_rate: {summary['train_positive_rate']}",
        f"- validation_positive_rate: {summary['validation_positive_rate']}",
        f"- feature_importance_nonzero_count: {summary['feature_importance_nonzero_count']}",
        f"- tree_count: {summary['tree_count']}",
        f"- effective_split_count: {summary['effective_split_count']}",
        f"- latest_prediction_unique_count: {summary['latest_prediction_unique_count']}",
        f"- latest_prediction_std: {summary['latest_prediction_std']}",
        "",
        "## Likely Root Causes",
        "",
    ]
    for cause in summary["likely_root_causes"]:
        lines.append(f"- {cause}")
    lines.extend(["", "## Recommended Fix Plan", ""])
    for item in summary["recommended_fix_plan"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- This phase performs root cause analysis only.",
            "- It does not add features, change labels, retrain, run inference, backtest, trade, promote a model, or place orders.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    return [dict(row) for row in rows]


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_pickle(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
