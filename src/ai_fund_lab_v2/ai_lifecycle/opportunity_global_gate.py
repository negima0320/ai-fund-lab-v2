from __future__ import annotations

from typing import Any


GATE_ID = "OPPORTUNITY_GLOBAL_QUALITY_GATE_V1"
PASS = "PASS"
FAIL = "FAIL"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
METRIC_UNAVAILABLE = "METRIC_UNAVAILABLE"

REQUIRED_METRICS = (
    "finite_ratio",
    "nan_count",
    "inf_count",
    "collapse",
    "explosion",
    "calibration_status",
    "ordering_preservation",
    "baseline_comparison",
    "pearson_correlation",
    "spearman_rank_correlation",
    "prediction_distribution",
)


def evaluate_opportunity_global_gate(
    *,
    metric_payload: dict[str, Any],
    bindings: dict[str, Any],
    approved_status_semantics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    semantics = approved_status_semantics or {}
    missing = [name for name in REQUIRED_METRICS if name not in metric_payload]
    binding_reasons = _binding_reasons(bindings)
    if missing:
        return _result(METRIC_UNAVAILABLE, ["missing_metric:" + name for name in missing] + binding_reasons, metric_payload, bindings)
    if binding_reasons:
        return _result(FAIL, binding_reasons, metric_payload, bindings)

    hard_failures: list[str] = []
    if float(metric_payload["finite_ratio"]) != 1.0:
        hard_failures.append("finite_ratio_not_one")
    if int(metric_payload["nan_count"]) != 0:
        hard_failures.append("nan_present")
    if int(metric_payload["inf_count"]) != 0:
        hard_failures.append("inf_present")
    if bool(metric_payload["collapse"]):
        hard_failures.append("collapsed_prediction")
    if bool(metric_payload["explosion"]):
        hard_failures.append("prediction_explosion")
    if metric_payload["calibration_status"] != PASS:
        hard_failures.append("calibration_not_pass")
    if bool(metric_payload["ordering_preservation"]) is not True:
        hard_failures.append("ordering_not_preserved")
    distribution = metric_payload["prediction_distribution"]
    if not isinstance(distribution, dict) or "std" not in distribution or "quantiles" not in distribution:
        hard_failures.append("prediction_distribution_incomplete")
    if hard_failures:
        return _result(FAIL, hard_failures, metric_payload, bindings)

    threshold_required = ("baseline_comparison", "pearson_correlation", "spearman_rank_correlation")
    missing_semantics = [name for name in threshold_required if name not in semantics]
    if missing_semantics:
        return _result(REVIEW_REQUIRED, ["approved_status_semantics_missing:" + name for name in missing_semantics], metric_payload, bindings)

    semantic_failures = [_evaluate_semantic(name, metric_payload[name], semantics[name]) for name in threshold_required]
    semantic_failures = [reason for reason in semantic_failures if reason]
    if semantic_failures:
        return _result(FAIL, semantic_failures, metric_payload, bindings)
    return _result(PASS, [], metric_payload, bindings)


def _binding_reasons(bindings: dict[str, Any]) -> list[str]:
    required = (
        "formal_validation_artifact_id",
        "formal_validation_artifact_hash",
        "opportunity_model_hash",
        "opportunity_scaler_hash",
        "opportunity_calibration_artifact_hash",
        "dataset_revision",
        "split_id",
        "policy_hash",
    )
    return ["missing_binding:" + name for name in required if not bindings.get(name)]


def _evaluate_semantic(name: str, value: Any, semantic: dict[str, Any]) -> str | None:
    if semantic.get("status_policy") == "DIAGNOSTIC_ONLY":
        return None
    if "minimum" in semantic and float(value) < float(semantic["minimum"]):
        return f"{name}_below_approved_minimum"
    if "maximum" in semantic and float(value) > float(semantic["maximum"]):
        return f"{name}_above_approved_maximum"
    if "equals" in semantic and value != semantic["equals"]:
        return f"{name}_approved_equals_mismatch"
    if "all_true" in semantic:
        required = semantic["all_true"]
        missing = [key for key in required if not isinstance(value, dict) or value.get(key) is not True]
        if missing:
            return f"{name}_approved_boolean_checks_failed"
    return None


def _result(status: str, reasons: list[str], metric_payload: dict[str, Any], bindings: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate_id": GATE_ID,
        "status": status,
        "reason_codes": reasons,
        "generation_eligibility": status == PASS,
        "runtime_eligibility": False,
        "metric_payload": metric_payload,
        "bindings": bindings,
    }
