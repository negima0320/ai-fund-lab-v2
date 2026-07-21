from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


class OpportunityCalibrationError(ValueError):
    """Fail-closed error for Opportunity calibration failures."""


@dataclass(frozen=True)
class OpportunityCalibrationResult:
    status: str
    parameters: dict[str, Any]
    raw_scores: list[float]
    normalized_opportunity_score: list[float]
    percentile_diagnostic: list[float]
    quality_metrics: dict[str, Any]
    quality_gate_result: dict[str, Any]


def _spearman(left: np.ndarray, right: np.ndarray) -> float:
    return float(pd.Series(left).corr(pd.Series(right), method="spearman"))


def fit_opportunity_standardization(raw_scores: list[float] | np.ndarray) -> OpportunityCalibrationResult:
    scores = np.asarray(raw_scores, dtype=float).reshape(-1)
    if scores.size == 0:
        raise OpportunityCalibrationError("opportunity_empty_scores")
    if not np.isfinite(scores).all():
        raise OpportunityCalibrationError("opportunity_nan_or_inf")
    mean = float(np.mean(scores))
    std = float(np.std(scores))
    if std <= 0.0:
        raise OpportunityCalibrationError("opportunity_zero_std")
    normalized = (scores - mean) / std
    if not np.isfinite(normalized).all():
        raise OpportunityCalibrationError("opportunity_normalized_nan_or_inf")
    raw_order = np.argsort(scores, kind="mergesort")
    normalized_order = np.argsort(normalized, kind="mergesort")
    ordering_preserved = bool(np.array_equal(raw_order, normalized_order))
    spearman = _spearman(scores, normalized)
    unique_count = int(np.unique(np.round(normalized, 12)).size)
    collapse = unique_count <= 1
    explosion = bool(np.max(np.abs(normalized)) > 1e6)
    percentile = pd.Series(scores).rank(method="average", pct=True).to_numpy()
    reason_codes: list[str] = []
    if not ordering_preserved:
        reason_codes.append("opportunity_ordering_not_preserved")
    if not np.isclose(spearman, 1.0):
        reason_codes.append("opportunity_spearman_not_one")
    if collapse:
        reason_codes.append("opportunity_collapsed_prediction")
    if explosion:
        reason_codes.append("opportunity_prediction_explosion")
    metrics = {
        "mean": float(np.mean(normalized)),
        "std": float(np.std(normalized)),
        "quantiles": {str(q): float(np.quantile(normalized, q)) for q in [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]},
        "ordering_preservation": ordering_preserved,
        "spearman_rank_correlation": spearman,
        "outlier_rate_abs_gt_3": float(np.mean(np.abs(normalized) > 3.0)),
        "clipping_rate": 0.0,
        "finite_ratio": float(np.isfinite(normalized).mean()),
        "collapse": collapse,
        "explosion": explosion,
        "percentile_diagnostic_distribution": {
            "min": float(np.min(percentile)),
            "max": float(np.max(percentile)),
            "mean": float(np.mean(percentile)),
            "std": float(np.std(percentile)),
        },
    }
    status = "PASS" if not reason_codes else "OPPORTUNITY_CALIBRATION_REVIEW_REQUIRED"
    return OpportunityCalibrationResult(
        status=status,
        parameters={"method": "STANDARDIZED", "mean": mean, "std": std, "clipping": {"enabled": False}},
        raw_scores=[float(v) for v in scores],
        normalized_opportunity_score=[float(v) for v in normalized],
        percentile_diagnostic=[float(v) for v in percentile],
        quality_metrics=metrics,
        quality_gate_result={"status": status, "reason_codes": reason_codes},
    )

