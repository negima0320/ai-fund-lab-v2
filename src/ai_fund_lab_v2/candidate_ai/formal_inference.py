from __future__ import annotations

from typing import Any

import numpy as np

from ai_fund_lab_v2.candidate_ai.validation import is_forbidden_column


def build_scored_candidates(
    rows: list[dict[str, Any]],
    scores: np.ndarray,
    *,
    model_version: str,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row, score in zip(rows, scores):
        output.append(
            {
                "target_date": str(row.get("target_date")),
                "code": str(row.get("code")),
                "candidate_score": round(float(score), 8),
                "candidate_rank": None,
                "candidate_reason": _candidate_reason(row, score),
                "excluded_reason": "",
                "feature_snapshot_id": row.get("source_snapshot_id") or row.get("feature_version"),
                "model_version": model_version,
                "audit_flags": ["formal_inference", "not_buy_decision", "not_purchase_rank", "not_production_promotion"],
            }
        )
    return output


def audit_inference_features(feature_columns: list[str]) -> dict[str, Any]:
    stripped = [column.replace("feature__", "", 1) for column in feature_columns]
    future_columns = [column for column in stripped if is_forbidden_column(column)]
    label_columns = [
        column
        for column in feature_columns
        if column.startswith("label__") or "candidate_label" in column or "momentum_candidate_label" in column
    ]
    status = "OK" if all(column.startswith("feature__") for column in feature_columns) and not future_columns and not label_columns else "ERROR"
    return {
        "status": status,
        "future_column_used_as_feature": bool(future_columns),
        "future_columns": future_columns,
        "label_column_used_as_feature": bool(label_columns),
        "label_columns": label_columns,
    }


def validate_candidate_output(rows: list[dict[str, Any]]) -> bool:
    required = {
        "target_date",
        "code",
        "candidate_score",
        "candidate_rank",
        "candidate_reason",
        "excluded_reason",
        "feature_snapshot_id",
        "model_version",
        "audit_flags",
    }
    return bool(rows) and all(required.issubset(row.keys()) for row in rows)


def feature_matrix(frame: Any, feature_columns: list[str]) -> np.ndarray:
    values = frame[[column.replace("feature__", "", 1) for column in feature_columns]].copy()
    for column in values.columns:
        if values[column].dtype == bool:
            values[column] = values[column].astype(float)
    return values.astype(float).to_numpy()


def predict_scores(model: Any, x_input: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(x_input)
        if proba.ndim == 2 and proba.shape[1] > 1:
            return np.asarray(proba[:, 1], dtype=float)
    if hasattr(model, "decision_function"):
        raw = np.asarray(model.decision_function(x_input), dtype=float)
        return 1.0 / (1.0 + np.exp(-raw))
    return np.asarray(model.predict(x_input), dtype=float)


def _candidate_reason(row: dict[str, Any], score: float) -> str:
    reasons: list[str] = []
    if float(score) >= 0.5:
        reasons.append("high_candidate_score")
    if _numeric_value(row.get("price_momentum_return_20d")) > 0:
        reasons.append("price_momentum_positive")
    if _numeric_value(row.get("price_momentum_return_60d")) > 0:
        reasons.append("long_momentum_positive")
    if _numeric_value(row.get("volume_momentum_ratio_5d")) > 1:
        reasons.append("volume_momentum_positive")
    if _numeric_value(row.get("liquidity_avg_volume_20d")) > 0:
        reasons.append("liquidity_available")
    return "|".join(reasons) if reasons else "formal_score_ranked"


def _numeric_value(value: Any) -> float:
    if value is None:
        return np.nan
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


__all__ = [
    "audit_inference_features",
    "build_scored_candidates",
    "feature_matrix",
    "predict_scores",
    "validate_candidate_output",
]
