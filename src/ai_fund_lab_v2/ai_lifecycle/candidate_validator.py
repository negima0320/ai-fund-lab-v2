from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from ai_fund_lab_v2.ai_lifecycle.candidate_calibration import calibration_curve, expected_calibration_error, prediction_histogram, sigmoid


FORMAL_TEST_SCOPED_FIELDS = {
    "minimum_test_rows",
    "minimum_test_business_days",
    "minimum_test_positive_labels",
    "minimum_test_negative_labels",
}
LIFECYCLE_SCOPED_FIELDS = {
    "minimum_positive_labels",
    "minimum_negative_labels",
    "minimum_class_ratio",
}
KNOWN_NON_TEST_FIELDS = {
    "minimum_training_rows",
    "minimum_training_business_days",
    "minimum_validation_rows",
    "minimum_validation_business_days",
    "minimum_validation_positive_labels",
    "minimum_validation_negative_labels",
    "minimum_recent_holdout_rows",
    "minimum_recent_holdout_business_days",
    "minimum_distinct_issues",
    "minimum_feature_coverage",
    "maximum_missing_ratio",
    "maximum_invalid_numeric_ratio",
    "maximum_constant_feature_ratio",
    "critical_feature_missing",
    "unexpected_constant_feature_count",
}


def quantiles(values: np.ndarray) -> dict[str, float]:
    return {str(q): float(np.quantile(values, q)) for q in [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]}


def resolve_formal_test_policy_checks(
    *,
    policy_requirements: dict[str, Any],
    sample_count: int,
    business_days: int,
    positive_count: int,
    negative_count: int,
    class_balance: float,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    applied_fields: dict[str, dict[str, Any]] = {}
    excluded_fields: dict[str, dict[str, Any]] = {}
    review_required_fields: dict[str, dict[str, Any]] = {}

    def apply_field(field: str, observed: int | float, threshold: int | float, stage: str, window: str) -> None:
        checks[field] = observed >= threshold
        applied_fields[field] = {
            "observed": observed,
            "threshold": threshold,
            "field_scope": stage,
            "applicable_dataset_window": window,
            "failure_behavior": "FORMAL_TEST_GATE_FAIL",
        }

    if "minimum_test_rows" in policy_requirements:
        apply_field("minimum_test_rows", sample_count, int(policy_requirements["minimum_test_rows"]), "FORMAL_TEST_DATA_SUFFICIENCY", "test")
    else:
        review_required_fields["minimum_test_rows"] = {
            "field_scope": "FORMAL_TEST_DATA_SUFFICIENCY",
            "reason": "missing_required_formal_test_rows_field",
        }
    if "minimum_test_business_days" in policy_requirements:
        apply_field(
            "minimum_test_business_days",
            int(business_days),
            int(policy_requirements["minimum_test_business_days"]),
            "FORMAL_TEST_DATA_SUFFICIENCY",
            "test",
        )
    else:
        review_required_fields["minimum_test_business_days"] = {
            "field_scope": "FORMAL_TEST_DATA_SUFFICIENCY",
            "reason": "missing_required_formal_test_business_days_field",
        }
    if "minimum_test_positive_labels" in policy_requirements:
        apply_field(
            "minimum_test_positive_labels",
            positive_count,
            int(policy_requirements["minimum_test_positive_labels"]),
            "FORMAL_TEST_DATA_SUFFICIENCY",
            "test",
        )
    if "minimum_test_negative_labels" in policy_requirements:
        apply_field(
            "minimum_test_negative_labels",
            negative_count,
            int(policy_requirements["minimum_test_negative_labels"]),
            "FORMAL_TEST_DATA_SUFFICIENCY",
            "test",
        )
    if "minimum_class_ratio" in policy_requirements:
        checks["minimum_class_ratio"] = min(class_balance, 1.0 - class_balance) >= float(policy_requirements["minimum_class_ratio"])
        applied_fields["minimum_class_ratio"] = {
            "observed": min(class_balance, 1.0 - class_balance),
            "threshold": float(policy_requirements["minimum_class_ratio"]),
            "field_scope": "FORMAL_TEST_DATA_SUFFICIENCY",
            "applicable_dataset_window": "test",
            "failure_behavior": "FORMAL_TEST_GATE_FAIL",
            "note": "ratio guard is window-normalized and does not reuse top-level absolute label floors",
        }

    for field in sorted(LIFECYCLE_SCOPED_FIELDS):
        if field in policy_requirements and field != "minimum_class_ratio":
            excluded_fields[field] = {
                "threshold": policy_requirements[field],
                "field_scope": "LIFECYCLE_DATA_SUFFICIENCY",
                "applicable_dataset_window": "not_implicitly_test",
                "failure_behavior": "EXCLUDED_FROM_FORMAL_TEST_GATE_AND_REVIEW_REQUIRED",
                "reason": "top_level_lifecycle_label_floor_has_no_explicit_test_window_scope",
            }
            review_required_fields[field] = {
                "threshold": policy_requirements[field],
                "field_scope": "UNSCOPED_REVIEW_REQUIRED",
                "reason": "policy_field_scope_ambiguous_for_formal_test_window",
            }

    for field in sorted(policy_requirements):
        if field in FORMAL_TEST_SCOPED_FIELDS or field in LIFECYCLE_SCOPED_FIELDS or field in KNOWN_NON_TEST_FIELDS:
            continue
        if field.startswith(("minimum_", "maximum_")):
            review_required_fields[field] = {
                "threshold": policy_requirements[field],
                "field_scope": "UNSCOPED_REVIEW_REQUIRED",
                "reason": "unknown_policy_field_scope",
            }

    return {
        "checks": checks,
        "status": "REVIEW_REQUIRED" if review_required_fields else "PASS",
        "applied_fields": applied_fields,
        "excluded_fields": excluded_fields,
        "review_required_fields": review_required_fields,
    }


def validate_candidate_primary(
    *,
    raw_scores: np.ndarray,
    labels: np.ndarray,
    calibration_parameters: dict[str, Any],
    policy_requirements: dict[str, Any],
    business_days: int,
) -> dict[str, Any]:
    probabilities = sigmoid(float(calibration_parameters["intercept"]) + float(calibration_parameters["coefficient"]) * raw_scores)
    positive_count = int(np.sum(labels == 1))
    negative_count = int(np.sum(labels == 0))
    sample_count = int(labels.size)
    finite_ratio = float(np.isfinite(probabilities).mean()) if sample_count else 0.0
    collapse = bool(np.unique(np.round(probabilities, 12)).size <= 1)
    class_balance = float(np.mean(labels)) if sample_count else 0.0
    metrics = {
        "sample_count": sample_count,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "class_balance": class_balance,
        "probability_distribution": {
            "min": float(np.min(probabilities)),
            "max": float(np.max(probabilities)),
            "mean": float(np.mean(probabilities)),
            "std": float(np.std(probabilities)),
            "quantiles": quantiles(probabilities),
            "histogram": prediction_histogram(probabilities, bins=20),
        },
        "brier_score": float(brier_score_loss(labels, probabilities)),
        "log_loss": float(log_loss(labels, np.clip(probabilities, 1e-15, 1.0 - 1e-15), labels=[0, 1])),
        "expected_calibration_error": expected_calibration_error(probabilities, labels),
        "calibration_curve": calibration_curve(probabilities, labels),
        "roc_auc": float(roc_auc_score(labels, probabilities)) if positive_count and negative_count else None,
        "pr_auc": float(average_precision_score(labels, probabilities)) if positive_count and negative_count else None,
        "finite_ratio": finite_ratio,
        "range_0_1": bool(np.min(probabilities) >= 0.0 and np.max(probabilities) <= 1.0),
        "collapse": collapse,
        "class_coverage": {"positive_present": positive_count > 0, "negative_present": negative_count > 0},
        "business_days": int(business_days),
    }
    policy_resolution = resolve_formal_test_policy_checks(
        policy_requirements=policy_requirements,
        sample_count=sample_count,
        business_days=int(business_days),
        positive_count=positive_count,
        negative_count=negative_count,
        class_balance=class_balance,
    )
    checks = {
        **policy_resolution["checks"],
        "finite_ratio": finite_ratio == 1.0,
        "range_0_1": metrics["range_0_1"],
        "collapse_absent": not collapse,
        "class_coverage": positive_count > 0 and negative_count > 0,
    }
    status = (
        "CANDIDATE_FORMAL_VALIDATION_REVIEW_REQUIRED"
        if policy_resolution["status"] == "REVIEW_REQUIRED"
        else ("CANDIDATE_FORMAL_VALIDATION_PASS" if all(checks.values()) else "CANDIDATE_FORMAL_VALIDATION_FAIL")
    )
    return {
        "status": status,
        "checks": checks,
        "metrics": metrics,
        "policy_scope_resolution": policy_resolution,
        "output": probabilities,
    }
