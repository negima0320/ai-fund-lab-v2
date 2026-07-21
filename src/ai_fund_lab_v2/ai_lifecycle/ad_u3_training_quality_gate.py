from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal


Component = Literal["Candidate", "Opportunity"]


class ModelQualityPolicyError(ValueError):
    """Fail-closed error for unapproved or corrupted model quality policies."""


def load_approved_model_quality_policy(path: Path | str) -> dict[str, Any]:
    policy_path = Path(path)
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    result = validate_approved_model_quality_policy(policy)
    if result["status"] != "PASS":
        raise ModelQualityPolicyError(";".join(result["reason_codes"]))
    return policy


def validate_approved_model_quality_policy(policy: dict[str, Any]) -> dict[str, Any]:
    reason_codes: list[str] = []
    if policy.get("policy_status") != "APPROVED":
        reason_codes.append("policy_not_approved")
    if policy.get("reviewer") != "user:negishi":
        reason_codes.append("wrong_reviewer")
    if policy.get("decision") != "APPROVE":
        reason_codes.append("decision_not_approve")
    if policy.get("reviewed_policy_hash") != policy.get("policy_hash"):
        reason_codes.append("reviewed_policy_hash_mismatch")
    if "Human Review decision user:negishi" not in str(policy.get("authority") or ""):
        reason_codes.append("authority_mismatch")
    computed_hash = approved_policy_hash(policy)
    if computed_hash != policy.get("policy_hash"):
        reason_codes.append("policy_hash_mismatch")
    return {
        "status": "PASS" if not reason_codes else "BLOCK",
        "reason_codes": reason_codes,
        "computed_policy_hash": computed_hash,
        "policy_hash": policy.get("policy_hash"),
        "reviewed_policy_hash": policy.get("reviewed_policy_hash"),
    }


def approved_policy_hash(policy: dict[str, Any]) -> str:
    payload = {key: value for key, value in policy.items() if key not in {"policy_hash", "reviewed_policy_hash"}}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def component_requirements(policy: dict[str, Any], component: Component) -> dict[str, Any]:
    key = "candidate_requirements" if component == "Candidate" else "opportunity_requirements"
    requirements = policy.get(key)
    if not isinstance(requirements, dict):
        raise ModelQualityPolicyError(f"missing_component_requirements:{component}")
    return requirements


def evaluate_training_quality(
    *,
    component: Component,
    policy: dict[str, Any],
    metrics: dict[str, Any],
    execution_mode: str,
) -> dict[str, Any]:
    requirements = component_requirements(policy, component)
    checks = {
        "training_rows": int(metrics.get("training_rows") or 0) >= int(requirements["minimum_training_rows"]),
        "validation_rows": int(metrics.get("validation_rows") or 0) >= int(requirements["minimum_validation_rows"]),
        "training_business_days": int(metrics.get("training_business_days") or 0) >= int(requirements["minimum_training_business_days"]),
        "validation_business_days": int(metrics.get("validation_business_days") or 0) >= int(requirements["minimum_validation_business_days"]),
        "distinct_issues": int(metrics.get("distinct_issues") or 0) >= int(requirements["minimum_distinct_issues"]),
        "positive_labels": int(metrics.get("positive_labels") or 0) >= int(requirements["minimum_positive_labels"]),
        "negative_labels": int(metrics.get("negative_labels") or 0) >= int(requirements["minimum_negative_labels"]),
        "class_ratio": float(metrics.get("class_ratio") or 0.0) >= float(requirements["minimum_class_ratio"]),
        "feature_coverage": float(metrics.get("feature_coverage") or 0.0) >= float(requirements["minimum_feature_coverage"]),
        "missing_ratio": float(metrics.get("missing_ratio") or 0.0) <= float(requirements["maximum_missing_ratio"]),
        "constant_feature_ratio": float(metrics.get("constant_feature_ratio") or 0.0) <= float(requirements["maximum_constant_feature_ratio"]),
        "invalid_numeric_ratio": float(metrics.get("invalid_numeric_ratio") or 0.0) <= float(requirements["maximum_invalid_numeric_ratio"]),
        "unexpected_constant_feature_count": int(metrics.get("unexpected_constant_feature_count") or 0)
        <= int(requirements["unexpected_constant_feature_count"]),
        "critical_feature_missing": bool(metrics.get("critical_feature_missing")) is bool(requirements["critical_feature_missing"]),
    }
    failing = [name for name, passed in checks.items() if not passed]
    fixture_structural_checks = {
        "non_empty_train_validation": int(metrics.get("training_rows") or 0) > 0 and int(metrics.get("validation_rows") or 0) > 0,
        "two_sided_label": int(metrics.get("positive_labels") or 0) > 0 and int(metrics.get("negative_labels") or 0) > 0,
        "missing_ratio_within_policy": checks["missing_ratio"],
        "invalid_numeric_within_policy": checks["invalid_numeric_ratio"],
        "unexpected_constant_feature_absent": checks["unexpected_constant_feature_count"],
    }
    fixture_failing = [name for name, passed in fixture_structural_checks.items() if not passed]
    if execution_mode == "FIXTURE_SMOKE":
        return {
            "component": component,
            "formal_quality_result": "NOT_EVALUATED_FOR_ACCEPTANCE",
            "fixture_structural_result": "PASS" if not fixture_failing else "BLOCK",
            "runtime_eligibility": False,
            "generation_eligibility": False,
            "policy_thresholds_relaxed": False,
            "checks": checks,
            "fixture_structural_checks": fixture_structural_checks,
            "failing_checks": fixture_failing,
        }
    return {
        "component": component,
        "formal_quality_result": "PASS" if not failing else "BLOCK",
        "fixture_structural_result": "NOT_APPLICABLE",
        "runtime_eligibility": False,
        "generation_eligibility": False,
        "policy_thresholds_relaxed": False,
        "checks": checks,
        "failing_checks": failing,
    }
