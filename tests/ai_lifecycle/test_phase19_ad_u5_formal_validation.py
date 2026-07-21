from __future__ import annotations

from pathlib import Path

import numpy as np

from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_artifact_writer import validate_artifact_against_schema
from ai_fund_lab_v2.ai_lifecycle.candidate_validator import validate_candidate_primary
from ai_fund_lab_v2.ai_lifecycle.opportunity_validator import validate_opportunity_primary
from ai_fund_lab_v2.ai_lifecycle.temporal_robustness_validator import review_recent_holdout
from ai_fund_lab_v2.ai_lifecycle.validation_artifact_writer import write_validation_artifact


def test_candidate_top_level_lifecycle_label_floor_is_not_test_gate() -> None:
    labels = np.array([0, 0, 0, 1, 1, 1], dtype=int)
    raw_scores = np.array([-4.0, -3.0, -2.0, 2.0, 3.0, 4.0])
    base_policy = {
        "minimum_test_rows": 6,
        "minimum_test_business_days": 2,
        "minimum_positive_labels": 100,
        "minimum_negative_labels": 100,
        "minimum_class_ratio": 0.3,
    }

    result = validate_candidate_primary(
        raw_scores=raw_scores,
        labels=labels,
        calibration_parameters={"intercept": 0.0, "coefficient": 1.0},
        policy_requirements=base_policy,
        business_days=2,
    )
    assert result["status"] == "CANDIDATE_FORMAL_VALIDATION_REVIEW_REQUIRED"
    assert "minimum_positive_labels" not in result["checks"]
    assert "minimum_negative_labels" not in result["checks"]
    assert result["checks"]["minimum_test_rows"] is True
    assert result["policy_scope_resolution"]["excluded_fields"]["minimum_positive_labels"]["field_scope"] == "LIFECYCLE_DATA_SUFFICIENCY"


def test_candidate_explicit_test_label_floor_is_applied_to_test_window() -> None:
    labels = np.array([0, 0, 0, 1, 1, 1], dtype=int)
    raw_scores = np.array([-4.0, -3.0, -2.0, 2.0, 3.0, 4.0])
    policy = {
        "minimum_test_rows": 6,
        "minimum_test_business_days": 2,
        "minimum_test_positive_labels": 4,
        "minimum_test_negative_labels": 3,
        "minimum_class_ratio": 0.3,
    }

    result = validate_candidate_primary(
        raw_scores=raw_scores,
        labels=labels,
        calibration_parameters={"intercept": 0.0, "coefficient": 1.0},
        policy_requirements=policy,
        business_days=2,
    )
    assert result["status"] == "CANDIDATE_FORMAL_VALIDATION_FAIL"
    assert result["checks"]["minimum_test_positive_labels"] is False
    assert result["checks"]["minimum_test_negative_labels"] is True


def test_opportunity_regression_sign_coverage_uses_explicit_test_fields_only() -> None:
    raw_predictions = np.array([-0.3, -0.2, -0.1, 0.1, 0.2, 0.3], dtype=float)
    target = np.array([-0.2, -0.1, -0.05, 0.05, 0.1, 0.2], dtype=float)
    top_level_policy = {
        "minimum_test_rows": 6,
        "minimum_test_business_days": 2,
        "minimum_positive_labels": 100,
        "minimum_negative_labels": 100,
        "minimum_class_ratio": 0.3,
    }

    review = validate_opportunity_primary(
        raw_predictions=raw_predictions,
        target=target,
        calibration_parameters={"mean": 0.0, "std": 0.1},
        policy_requirements=top_level_policy,
        business_days=2,
    )
    assert review["status"] == "OPPORTUNITY_FORMAL_VALIDATION_REVIEW_REQUIRED"
    assert "minimum_positive_labels" not in review["checks"]
    assert "minimum_negative_labels" not in review["checks"]

    failed = validate_opportunity_primary(
        raw_predictions=raw_predictions,
        target=target,
        calibration_parameters={"mean": 0.0, "std": 0.1},
        policy_requirements={
            "minimum_test_rows": 6,
            "minimum_test_business_days": 2,
            "minimum_test_positive_labels": 3,
            "minimum_test_negative_labels": 4,
            "minimum_class_ratio": 0.3,
        },
        business_days=2,
    )
    assert failed["status"] == "OPPORTUNITY_FORMAL_VALIDATION_FAIL"
    assert failed["checks"]["minimum_test_negative_labels"] is False
    assert failed["metrics"]["ordering_preservation"] is True
    assert failed["metrics"]["collapse"] is False
    assert failed["metrics"]["explosion"] is False


def test_unknown_policy_scope_causes_review_required() -> None:
    labels = np.array([0, 0, 0, 1, 1, 1], dtype=int)
    raw_scores = np.array([-4.0, -3.0, -2.0, 2.0, 3.0, 4.0])
    result = validate_candidate_primary(
        raw_scores=raw_scores,
        labels=labels,
        calibration_parameters={"intercept": 0.0, "coefficient": 1.0},
        policy_requirements={
            "minimum_test_rows": 6,
            "minimum_test_business_days": 2,
            "minimum_eval_positive_labels": 3,
            "minimum_class_ratio": 0.3,
        },
        business_days=2,
    )
    assert result["status"] == "CANDIDATE_FORMAL_VALIDATION_REVIEW_REQUIRED"
    assert result["policy_scope_resolution"]["review_required_fields"]["minimum_eval_positive_labels"]["reason"] == "unknown_policy_field_scope"


def test_result_driven_top_level_threshold_mutation_does_not_create_test_pass() -> None:
    labels = np.array([0, 0, 0, 1, 1, 1], dtype=int)
    raw_scores = np.array([-4.0, -3.0, -2.0, 2.0, 3.0, 4.0])
    result = validate_candidate_primary(
        raw_scores=raw_scores,
        labels=labels,
        calibration_parameters={"intercept": 0.0, "coefficient": 1.0},
        policy_requirements={
            "minimum_test_rows": 6,
            "minimum_test_business_days": 2,
            "minimum_positive_labels": 1,
            "minimum_negative_labels": 1,
            "minimum_class_ratio": 0.3,
        },
        business_days=2,
    )
    assert result["status"] == "CANDIDATE_FORMAL_VALIDATION_REVIEW_REQUIRED"
    assert "minimum_positive_labels" not in result["checks"]
    assert "minimum_negative_labels" not in result["checks"]


def test_recent_holdout_review_requires_explicit_degradation_policy() -> None:
    review = review_recent_holdout(
        candidate_metrics={"sample_count": 10},
        opportunity_metrics={"sample_count": 10},
        policy={
            "candidate_requirements": {"minimum_recent_holdout_rows": 10, "minimum_recent_holdout_business_days": 2},
            "opportunity_requirements": {"minimum_recent_holdout_rows": 10, "minimum_recent_holdout_business_days": 2},
        },
    )
    assert review["status"] == "REVIEW_REQUIRED"
    assert "recent_holdout_relative_degradation_threshold_not_defined_in_approved_policy" in review["reason_codes"]
    assert review["generation_eligibility"] is False


def test_validation_artifact_writer_schema_and_hash_inventory(tmp_path: Path) -> None:
    candidate_calibration = tmp_path / "candidate_calibration.json"
    opportunity_calibration = tmp_path / "opportunity_calibration.json"
    candidate_model = tmp_path / "candidate_model.pkl"
    opportunity_model = tmp_path / "opportunity_model.pkl"
    candidate_scaler = tmp_path / "candidate_scaler.pkl"
    opportunity_scaler = tmp_path / "opportunity_scaler.pkl"
    policy = tmp_path / "policy.json"
    for path, payload in (
        (candidate_calibration, b"candidate-calibration"),
        (opportunity_calibration, b"opportunity-calibration"),
        (candidate_model, b"candidate-model"),
        (opportunity_model, b"opportunity-model"),
        (candidate_scaler, b"candidate-scaler"),
        (opportunity_scaler, b"opportunity-scaler"),
        (policy, b"policy"),
    ):
        path.write_bytes(payload)

    artifact = {
        "artifact_id": "formal_validation_fixture",
        "artifact_type": "FORMAL_VALIDATION",
        "artifact_version": "phase19_ad_u5_formal_validation.v1",
        "artifact_status": "FORMAL_VALIDATION_FAIL",
        "created_at": "2026-07-20T00:00:00+09:00",
        "producer": "test",
        "source_phase": "PHASE19_AD_U5",
        "component": "Validation",
        "generation_candidate_id": None,
        "schema_version": "phase19_ad_u5_formal_validation_artifact.v1",
        "authority": "not runtime",
        "validation_run_id": "fixture",
        "formal_cycle_number": 1,
        "formal_validation_policy": {"formal_cycle_number": 1},
        "source_bindings": {},
        "validated_artifact_ids": ["candidate", "opportunity"],
        "validated_artifact_hashes": ["1" * 64, "2" * 64],
        "dataset_usage_contract_hash": "3" * 64,
        "model_quality_policy_hash": "4" * 64,
        "candidate_result": {"status": "CANDIDATE_FORMAL_VALIDATION_FAIL"},
        "opportunity_result": {"status": "OPPORTUNITY_FORMAL_VALIDATION_FAIL"},
        "combined_quality_gate": {"status": "PRIMARY_FORMAL_VALIDATION_FAIL"},
        "recent_holdout_review": {"status": "NOT_EXECUTED"},
        "window_usage": {"test_accessed": True, "recent_holdout_accessed": False},
        "runtime_eligibility": False,
        "generation_eligibility": False,
        "accepted": False,
        "hash_inventory": {},
        "content_hash": "0" * 64,
    }
    from ai_fund_lab_v2.ai_lifecycle.validation_artifact_writer import build_hash_inventory

    artifact["hash_inventory"] = build_hash_inventory(
        artifact=artifact,
        candidate_calibration_artifact_path=candidate_calibration,
        opportunity_calibration_artifact_path=opportunity_calibration,
        source_model_files=[candidate_model, opportunity_model],
        source_scaler_files=[candidate_scaler, opportunity_scaler],
        validation_policy_path=policy,
        metric_payload={"fixture": True},
    )
    result = write_validation_artifact(
        artifact=artifact,
        path=tmp_path / "formal_validation_artifact.json",
        schema_dir=Path("schemas/ai_lifecycle"),
    )
    assert result["status"] == "PASS"
    assert validate_artifact_against_schema(result["artifact"], Path("schemas/ai_lifecycle/formal_validation_artifact.schema.json"))["status"] == "PASS"
    assert result["artifact"]["runtime_eligibility"] is False
    assert result["artifact"]["accepted"] is False
    assert result["artifact"]["hash_inventory"]["validation_artifact_file_sha256"]["sha256"] != "0" * 64
