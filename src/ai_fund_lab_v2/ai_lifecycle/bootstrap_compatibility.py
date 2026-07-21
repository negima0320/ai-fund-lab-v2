from __future__ import annotations

from dataclasses import dataclass
from typing import Any


APPROVE_ELIGIBLE = "APPROVE_ELIGIBLE"
REJECT_REQUIRED = "REJECT_REQUIRED"
REVIEW_REQUIRED_WITH_EXPLICIT_BLOCKERS = "REVIEW_REQUIRED_WITH_EXPLICIT_BLOCKERS"


@dataclass(frozen=True)
class CompatibilityResult:
    decision: str
    reason: str
    evidence: dict[str, Any]


def classify_known_exception(text: str) -> dict[str, Any]:
    lowered = text.lower()
    if "pit" in lowered or "proxy" in lowered or "requires review" in lowered:
        classification = "REQUIRES_REVALIDATION"
    elif "row-count" in lowered or "reporting bug" in lowered:
        classification = "BOOTSTRAP_COMPATIBLE_WITH_LIMITATION"
    elif "runtime_use_eligible remains false" in lowered or "accepted promotion is out of scope" in lowered:
        classification = "DOCUMENTATION_ONLY"
    elif not text.strip():
        classification = "UNKNOWN"
    else:
        classification = "UNKNOWN"
    return {
        "exception": text,
        "classification": classification,
        "approval_blocking": classification in {"REQUIRES_REVALIDATION", "BLOCKING", "UNKNOWN"},
    }


def evaluate_validation_applicability(
    *,
    validated_model_hash: str | None,
    bootstrap_model_hash: str | None,
    validated_schema_hash: str | None,
    bootstrap_schema_hash: str | None,
    validated_dataset_hash: str | None = None,
    bootstrap_dataset_hash: str | None = None,
    required_binding_proven: bool = True,
) -> CompatibilityResult:
    mismatches = []
    missing = []
    _compare("model_hash", validated_model_hash, bootstrap_model_hash, mismatches, missing)
    _compare("schema_hash", validated_schema_hash, bootstrap_schema_hash, mismatches, missing)
    if validated_dataset_hash is not None or bootstrap_dataset_hash is not None:
        _compare("dataset_hash", validated_dataset_hash, bootstrap_dataset_hash, mismatches, missing)
    if not required_binding_proven:
        missing.append("candidate_binding")
    if mismatches:
        decision = "NOT_APPLICABLE"
    elif missing:
        decision = "PARTIALLY_APPLICABLE"
    else:
        decision = "APPLICABLE"
    return CompatibilityResult(decision, ";".join(mismatches or missing or ["validation_applicable"]), {"mismatches": mismatches, "missing": missing})


def evaluate_opportunity_candidate_binding(
    *,
    training_candidate_identity: str | None,
    bootstrap_candidate_identity: str | None,
    schema_compatible: bool | None,
) -> CompatibilityResult:
    if not training_candidate_identity:
        return CompatibilityResult("UNPROVEN_BINDING", "opportunity_training_candidate_identity_missing", {"schema_compatible": schema_compatible})
    if training_candidate_identity == bootstrap_candidate_identity:
        return CompatibilityResult("EXACT_BINDING", "candidate_identity_exact_match", {"schema_compatible": schema_compatible})
    if schema_compatible is True:
        return CompatibilityResult(
            "COMPATIBLE_BINDING",
            "candidate_identity_differs_but_schema_compatibility_evidence_present",
            {"training_candidate_identity": training_candidate_identity, "bootstrap_candidate_identity": bootstrap_candidate_identity},
        )
    if schema_compatible is False:
        return CompatibilityResult(
            "INCOMPATIBLE_BINDING",
            "candidate_identity_differs_and_schema_incompatible",
            {"training_candidate_identity": training_candidate_identity, "bootstrap_candidate_identity": bootstrap_candidate_identity},
        )
    return CompatibilityResult(
        "UNPROVEN_BINDING",
        "candidate_identity_differs_without_compatibility_evidence",
        {"training_candidate_identity": training_candidate_identity, "bootstrap_candidate_identity": bootstrap_candidate_identity},
    )


def evaluate_calibration_compatibility(
    *,
    calibration_model_hash: str | None,
    opportunity_model_hash: str | None,
    calibration_target: str | None,
    opportunity_target: str | None,
) -> CompatibilityResult:
    mismatches = []
    missing = []
    _compare("opportunity_model_hash", calibration_model_hash, opportunity_model_hash, mismatches, missing)
    _compare("target", calibration_target, opportunity_target, mismatches, missing)
    if mismatches:
        decision = "NOT_APPLICABLE"
    elif missing:
        decision = "UNPROVEN"
    else:
        decision = "EXACT_MATCH"
    return CompatibilityResult(decision, ";".join(mismatches or missing or ["calibration_exact_match"]), {"mismatches": mismatches, "missing": missing})


def evaluate_baseline_compatibility(
    *,
    baseline_model_hashes: dict[str, str | None],
    bootstrap_model_hashes: dict[str, str | None],
    baseline_calibration_hash: str | None = None,
    bootstrap_calibration_hash: str | None = None,
) -> CompatibilityResult:
    mismatches = []
    missing = []
    for key in sorted(set(baseline_model_hashes) | set(bootstrap_model_hashes)):
        _compare(f"{key}_model_hash", baseline_model_hashes.get(key), bootstrap_model_hashes.get(key), mismatches, missing)
    _compare("calibration_hash", baseline_calibration_hash, bootstrap_calibration_hash, mismatches, missing)
    if mismatches:
        decision = "INCOMPATIBLE"
    elif missing:
        decision = "UNPROVEN"
    else:
        decision = "COMPATIBLE"
    return CompatibilityResult(decision, ";".join(mismatches or missing or ["baseline_compatible"]), {"mismatches": mismatches, "missing": missing})


def evaluate_freshness_taxonomy(*, taxonomy: dict[str, dict[str, Any]], policy_versions: dict[str, str] | None) -> dict[str, Any]:
    results: dict[str, Any] = {}
    policy_missing = not policy_versions or any(not value for value in policy_versions.values())
    for key, payload in taxonomy.items():
        status = payload.get("status")
        if policy_missing and key in {"model_training_freshness", "accepted_generation_age"}:
            status = "REVIEW_REQUIRED_POLICY_MISSING"
        results[key] = {**payload, "status": status or "UNKNOWN"}
    overall = "REVIEW_REQUIRED_POLICY_MISSING" if any(item["status"] == "REVIEW_REQUIRED_POLICY_MISSING" for item in results.values()) else "PASS"
    return {"overall_result": overall, "policy_versions": policy_versions or {}, "taxonomy": results}


def decide_human_review_recommendation(*, findings: dict[str, str]) -> str:
    reject_values = {
        "NOT_APPLICABLE",
        "INCOMPATIBLE",
        "INCOMPATIBLE_BINDING",
        "BLOCKING",
    }
    review_values = {
        "PARTIALLY_APPLICABLE",
        "MISSING",
        "UNKNOWN",
        "UNPROVEN",
        "UNPROVEN_BINDING",
        "REVIEW_REQUIRED_POLICY_MISSING",
        "REQUIRES_REVALIDATION",
    }
    if any(value in reject_values for value in findings.values()):
        return REJECT_REQUIRED
    if any(value in review_values for value in findings.values()):
        return REVIEW_REQUIRED_WITH_EXPLICIT_BLOCKERS
    return APPROVE_ELIGIBLE


def _compare(field: str, left: str | None, right: str | None, mismatches: list[str], missing: list[str]) -> None:
    if not left or not right:
        missing.append(field)
    elif left != right:
        mismatches.append(field)
