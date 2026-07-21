from __future__ import annotations

from pathlib import Path

import pytest

from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_artifact_writer import file_hash, validate_artifact_against_schema
from ai_fund_lab_v2.ai_lifecycle.calibration_hash_inventory import self_reference_safe_manifest_hash, validate_hash_inventory
from ai_fund_lab_v2.ai_lifecycle.calibration_runner import (
    DEFAULT_SCHEMA_DIR,
    CalibrationRunRequest,
    CalibrationRunnerError,
    run_calibration_runner,
    validate_artifact_binding,
)
from ai_fund_lab_v2.ai_lifecycle.candidate_calibration import CandidateCalibrationError, fit_candidate_platt
from ai_fund_lab_v2.ai_lifecycle.opportunity_calibration import OpportunityCalibrationError, fit_opportunity_standardization


def test_candidate_platt_scaling_and_failure_fixtures() -> None:
    normal = fit_candidate_platt([-4, -3, -2, -1, 1, 2, 3, 4], [0, 0, 0, 0, 1, 1, 1, 1])
    assert normal.status == "PASS"
    assert all(0.0 <= value <= 1.0 for value in normal.calibrated_probability)
    assert normal.quality_metrics["platt"]["finite"] is True
    assert normal.quality_metrics["platt"]["collapse"] is False

    degraded = fit_candidate_platt([-8, -6, -4, -2, 2, 4, 6, 8], [1, 1, 1, 1, 0, 0, 0, 0])
    assert degraded.status == "CANDIDATE_CALIBRATION_REVIEW_REQUIRED"
    assert "candidate_platt_worse_than_identity" in degraded.quality_gate_result["reason_codes"]

    with pytest.raises(CandidateCalibrationError):
        fit_candidate_platt([1, 1, 1, 1], [1, 1, 1, 1])
    with pytest.raises(CandidateCalibrationError):
        fit_candidate_platt([0, 1, float("nan")], [0, 1, 0])


def test_opportunity_standardization_and_failure_fixtures() -> None:
    normal = fit_opportunity_standardization([-2, -1, 0, 1, 2, 3])
    assert normal.status == "PASS"
    assert normal.quality_metrics["ordering_preservation"] is True
    assert normal.quality_metrics["spearman_rank_correlation"] == pytest.approx(1.0)
    assert normal.quality_metrics["collapse"] is False
    assert normal.quality_metrics["explosion"] is False

    with pytest.raises(OpportunityCalibrationError):
        fit_opportunity_standardization([1, 1, 1])
    with pytest.raises(OpportunityCalibrationError):
        fit_opportunity_standardization([1, float("inf"), 2])


def test_fixture_smoke_writes_schema_valid_hash_bound_artifacts(tmp_path: Path) -> None:
    result = run_calibration_runner(
        CalibrationRunRequest(
            mode="FIXTURE_SMOKE",
            report_dir=tmp_path,
            schema_dir=DEFAULT_SCHEMA_DIR,
        )
    )
    assert result["status"] == "PASS"
    assert result["formal_calibration_executed"] is False
    assert result["test_evaluation_executed"] is False
    assert result["recent_holdout_evaluation_executed"] is False
    assert result["runtime_pointer_written"] is False
    assert result["broker_write_executed"] is False

    for component in ("candidate", "opportunity"):
        artifact = result[component]["artifact_result"]["artifact"]
        artifact_path = Path(result[component]["artifact_result"]["artifact_path"])
        assert artifact["artifact_status"] == "CALIBRATION_OUTPUT"
        assert artifact["runtime_eligibility"] is False
        assert artifact["generation_eligibility"] is False
        assert artifact["accepted"] is False
        assert validate_artifact_against_schema(artifact, DEFAULT_SCHEMA_DIR / "calibration_artifact.schema.json")["status"] == "PASS"
        assert validate_hash_inventory(artifact=artifact, artifact_path=artifact_path)["status"] == "PASS"
        assert artifact["hash_inventory"]["artifact_file_sha256"]["sha256"] == self_reference_safe_manifest_hash(artifact)


def test_runner_rejects_unknown_mode(tmp_path: Path) -> None:
    with pytest.raises(CalibrationRunnerError, match="formal_calibration_not_allowed|unknown"):
        run_calibration_runner(CalibrationRunRequest(mode="BAD", report_dir=tmp_path))  # type: ignore[arg-type]


def test_binding_guard_rejects_hash_feature_and_dataset_usage_mismatches(tmp_path: Path) -> None:
    model_file = tmp_path / "model.pkl"
    scaler_file = tmp_path / "scaler.pkl"
    model_file.write_bytes(b"model")
    scaler_file.write_bytes(b"scaler")
    source = {
        "artifact_status": "TRAINING_OUTPUT",
        "runtime_eligibility": False,
        "accepted": False,
        "dataset_revision_id": "revision",
        "split_id": "split",
        "split_content_hash": "1" * 64,
        "artifact_id": "model_artifact",
        "feature_columns": ["a", "b"],
    }
    scaler = {"artifact_id": "scaler_artifact", "input_feature_columns": ["a", "b"]}
    binding = {
        "dataset_revision_id": "revision",
        "split_id": "split",
        "split_hash": "1" * 64,
        "dataset_usage_contract_hash": "2" * 64,
        "source_model_artifact_id": "model_artifact",
        "source_model_hash": file_hash(model_file),
        "source_scaler_artifact_id": "scaler_artifact",
        "source_scaler_hash": file_hash(scaler_file),
    }
    assert validate_artifact_binding(
        source_model_artifact=source,
        source_scaler_artifact=scaler,
        source_model_file=model_file,
        source_scaler_file=scaler_file,
        binding=binding,
        dataset_usage_contract={"contract_hash": "2" * 64},
    )["status"] == "PASS"

    bad = validate_artifact_binding(
        source_model_artifact={**source, "feature_columns": ["b", "a"]},
        source_scaler_artifact=scaler,
        source_model_file=model_file,
        source_scaler_file=scaler_file,
        binding={**binding, "source_model_hash": "0" * 64},
        dataset_usage_contract={"contract_hash": "3" * 64},
    )
    assert bad["status"] == "REVIEW_REQUIRED"
    assert "source_model_hash_mismatch" in bad["reason_codes"]
    assert "dataset_usage_contract_mismatch" in bad["reason_codes"]
    assert "feature_order_mismatch" in bad["reason_codes"]
