from __future__ import annotations

from ai_fund_lab_v2.ai_lifecycle.bootstrap_compatibility import (
    APPROVE_ELIGIBLE,
    REJECT_REQUIRED,
    REVIEW_REQUIRED_WITH_EXPLICIT_BLOCKERS,
    classify_known_exception,
    decide_human_review_recommendation,
    evaluate_baseline_compatibility,
    evaluate_calibration_compatibility,
    evaluate_freshness_taxonomy,
    evaluate_opportunity_candidate_binding,
    evaluate_validation_applicability,
)


def test_calibration_model_hash_mismatch_is_not_applicable_and_rejects_recommendation() -> None:
    result = evaluate_calibration_compatibility(
        calibration_model_hash="phase18h-model",
        opportunity_model_hash="legacy-opportunity-model",
        calibration_target="label__expected_edge_label_20d",
        opportunity_target="label__expected_edge_label_20d",
    )

    assert result.decision == "NOT_APPLICABLE"
    assert decide_human_review_recommendation(findings={"calibration": result.decision}) == REJECT_REQUIRED


def test_baseline_model_mismatch_is_incompatible() -> None:
    result = evaluate_baseline_compatibility(
        baseline_model_hashes={"candidate": "candidate-a", "opportunity": "opportunity-new"},
        bootstrap_model_hashes={"candidate": "candidate-a", "opportunity": "opportunity-legacy"},
        baseline_calibration_hash="cal-a",
        bootstrap_calibration_hash="cal-a",
    )

    assert result.decision == "INCOMPATIBLE"
    assert "opportunity_model_hash" in result.reason


def test_opportunity_candidate_binding_absent_is_unproven() -> None:
    result = evaluate_opportunity_candidate_binding(
        training_candidate_identity=None,
        bootstrap_candidate_identity="candidate:legacy",
        schema_compatible=None,
    )

    assert result.decision == "UNPROVEN_BINDING"


def test_validation_references_different_model_hash_is_not_applicable() -> None:
    result = evaluate_validation_applicability(
        validated_model_hash="validated-model",
        bootstrap_model_hash="bootstrap-model",
        validated_schema_hash="same-schema",
        bootstrap_schema_hash="same-schema",
    )

    assert result.decision == "NOT_APPLICABLE"
    assert "model_hash" in result.reason


def test_freshness_policy_missing_keeps_review_required_without_invented_threshold() -> None:
    result = evaluate_freshness_taxonomy(
        taxonomy={
            "model_training_freshness": {"model_training_cutoff": "2024-12-02"},
            "accepted_generation_age": {"accepted_at": None},
        },
        policy_versions={},
    )

    assert result["overall_result"] == "REVIEW_REQUIRED_POLICY_MISSING"
    assert result["taxonomy"]["model_training_freshness"]["status"] == "REVIEW_REQUIRED_POLICY_MISSING"


def test_dataset_schema_mismatch_is_not_applicable() -> None:
    result = evaluate_validation_applicability(
        validated_model_hash="model",
        bootstrap_model_hash="model",
        validated_schema_hash="schema-a",
        bootstrap_schema_hash="schema-b",
    )

    assert result.decision == "NOT_APPLICABLE"
    assert "schema_hash" in result.reason


def test_blocking_known_exception_routes_to_review_or_reject() -> None:
    classified = classify_known_exception("Phase5-P point-in-time sector proxy requires review")

    assert classified["classification"] == "REQUIRES_REVALIDATION"
    assert classified["approval_blocking"] is True
    assert decide_human_review_recommendation(findings={"known_exception": classified["classification"]}) == REVIEW_REQUIRED_WITH_EXPLICIT_BLOCKERS


def test_missing_evidence_file_stays_unknown_review_required() -> None:
    assert decide_human_review_recommendation(findings={"evidence": "UNKNOWN"}) == REVIEW_REQUIRED_WITH_EXPLICIT_BLOCKERS


def test_all_contracts_exact_match_can_recommend_approve_without_accepting() -> None:
    recommendation = decide_human_review_recommendation(
        findings={
            "candidate": "REUSE_ELIGIBLE",
            "opportunity": "REUSE_ELIGIBLE",
            "binding": "EXACT_BINDING",
            "calibration": "EXACT_MATCH",
            "baseline": "COMPATIBLE",
            "validation": "APPLICABLE",
            "freshness": "PASS",
            "dataset": "COMPATIBLE",
            "policy": "COMPATIBLE",
        }
    )

    assert recommendation == APPROVE_ELIGIBLE
