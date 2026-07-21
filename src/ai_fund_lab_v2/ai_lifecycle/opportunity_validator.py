from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from ai_fund_lab_v2.ai_lifecycle.candidate_validator import quantiles, resolve_formal_test_policy_checks


def validate_opportunity_primary(
    *,
    raw_predictions: np.ndarray,
    target: np.ndarray,
    calibration_parameters: dict[str, Any],
    policy_requirements: dict[str, Any],
    business_days: int,
) -> dict[str, Any]:
    mean = float(calibration_parameters["mean"])
    std = float(calibration_parameters["std"])
    normalized = (raw_predictions - mean) / std
    sample_count = int(raw_predictions.size)
    finite_ratio = float(np.isfinite(normalized).mean()) if sample_count else 0.0
    collapse = bool(np.unique(np.round(normalized, 12)).size <= 1)
    explosion = bool(np.max(np.abs(normalized)) > 1e6) if sample_count else True
    ordering = bool(np.array_equal(np.argsort(raw_predictions, kind="mergesort"), np.argsort(normalized, kind="mergesort")))
    pearson = float(pd.Series(normalized).corr(pd.Series(target), method="pearson"))
    spearman = float(pd.Series(normalized).corr(pd.Series(target), method="spearman"))
    pred_std = float(np.std(normalized))
    target_std = float(np.std(target))
    metrics = {
        "sample_count": sample_count,
        "raw_prediction_distribution": {
            "min": float(np.min(raw_predictions)),
            "max": float(np.max(raw_predictions)),
            "mean": float(np.mean(raw_predictions)),
            "std": float(np.std(raw_predictions)),
            "quantiles": quantiles(raw_predictions),
        },
        "normalized_score_distribution": {
            "min": float(np.min(normalized)),
            "max": float(np.max(normalized)),
            "mean": float(np.mean(normalized)),
            "std": pred_std,
            "quantiles": quantiles(normalized),
        },
        "finite_ratio": finite_ratio,
        "collapse": collapse,
        "explosion": explosion,
        "ordering_preservation": ordering,
        "mae": float(mean_absolute_error(target, normalized)),
        "rmse": float(np.sqrt(mean_squared_error(target, normalized))),
        "target_mean": float(np.mean(target)),
        "target_std": target_std,
        "prediction_to_target_scale_ratio": float(pred_std / target_std) if target_std > 0 else None,
        "pearson_correlation": pearson,
        "spearman_rank_correlation": spearman,
        "business_days": int(business_days),
        "percentile_diagnostic_only": True,
    }
    positive = int(np.sum(target > 0))
    negative = int(np.sum(target <= 0))
    class_ratio = min(positive, negative) / sample_count if sample_count else 0.0
    policy_resolution = resolve_formal_test_policy_checks(
        policy_requirements=policy_requirements,
        sample_count=sample_count,
        business_days=int(business_days),
        positive_count=positive,
        negative_count=negative,
        class_balance=class_ratio,
    )
    checks = {
        **policy_resolution["checks"],
        "fit_std_gt_0": std > 0.0,
        "finite_ratio": finite_ratio == 1.0,
        "collapse_absent": not collapse,
        "explosion_absent": not explosion,
        "ordering_preservation": ordering,
    }
    status = (
        "OPPORTUNITY_FORMAL_VALIDATION_REVIEW_REQUIRED"
        if policy_resolution["status"] == "REVIEW_REQUIRED"
        else ("OPPORTUNITY_FORMAL_VALIDATION_PASS" if all(checks.values()) else "OPPORTUNITY_FORMAL_VALIDATION_FAIL")
    )
    return {
        "status": status,
        "checks": checks,
        "metrics": metrics,
        "policy_scope_resolution": policy_resolution,
        "output": normalized,
    }
