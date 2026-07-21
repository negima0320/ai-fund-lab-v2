from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.ai_lifecycle.ad_u3_contract_bound_training_runner import (
    DEFAULT_POLICY_PATH,
    DEFAULT_SCHEMA_DIR,
    TrainingRunRequest,
    TrainingRunnerError,
    materialize_fixture_contract,
    run_contract_bound_training_runner,
)
from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_artifact_writer import file_hash
from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_quality_gate import (
    ModelQualityPolicyError,
    evaluate_training_quality,
    load_approved_model_quality_policy,
)


def test_validate_only_uses_contract_resolver_and_does_not_train(tmp_path: Path) -> None:
    result = run_contract_bound_training_runner(
        TrainingRunRequest(
            contract_path=Path("reports/phase19_ad_r2_ad_u2_to_ad_u3_gate_review/ad_u3_dataset_input_contract_corrected.json"),
            model_quality_policy_path=DEFAULT_POLICY_PATH,
            schema_dir=DEFAULT_SCHEMA_DIR,
            mode="VALIDATE_ONLY",
            report_dir=tmp_path,
        )
    )

    assert result["status"] == "PASS"
    assert result["training_executed"] is False
    assert result["formal_authority"]["direct_dataset_input_allowed"] is False
    assert result["candidate_resolved"]["split_definition"]["split_recomputed"] is False
    assert result["quality_policy"]["status"] == "PASS"


def test_fixture_smoke_writes_contract_bound_non_runtime_artifacts(tmp_path: Path) -> None:
    contract = materialize_fixture_contract(tmp_path)
    result = run_contract_bound_training_runner(
        TrainingRunRequest(
            contract_path=contract,
            model_quality_policy_path=DEFAULT_POLICY_PATH,
            schema_dir=DEFAULT_SCHEMA_DIR,
            mode="FIXTURE_SMOKE",
            report_dir=tmp_path / "reports",
        )
    )

    assert result["status"] == "PASS"
    assert result["formal_quality_result"] == "NOT_EVALUATED_FOR_ACCEPTANCE"
    assert result["runtime_eligibility"] is False
    assert result["formal_generation_candidate_created"] is False
    for key in ("candidate", "opportunity"):
        artifact = result[key]["artifact"]
        assert artifact["artifact_status"] == "FIXTURE_TRAINING_OUTPUT"
        assert artifact["runtime_eligibility"] is False
        assert artifact["accepted"] is False
        assert artifact["generation_eligibility"] is False
        assert result[key]["schema_validation"]["status"] == "PASS"
        assert result[key]["serialization_integrity"]["status"] == "PASS"
        assert file_hash(Path(artifact["model_file"])) == artifact["model_content_hash"]
        assert artifact["training_statistics"]["validation_test_holdout_used_for_imputer_fit"] is False
    assert result["opportunity"]["artifact"]["candidate_dependency_contract"]["dependency"] == "FIXTURE_TECHNICAL_BINDING"


def test_fixture_smoke_rejects_formal_contract(tmp_path: Path) -> None:
    with pytest.raises(TrainingRunnerError, match="fixture_smoke_requires_fixture_contract"):
        run_contract_bound_training_runner(
            TrainingRunRequest(
                contract_path=Path("reports/phase19_ad_r2_ad_u2_to_ad_u3_gate_review/ad_u3_dataset_input_contract_corrected.json"),
                model_quality_policy_path=DEFAULT_POLICY_PATH,
                schema_dir=DEFAULT_SCHEMA_DIR,
                mode="FIXTURE_SMOKE",
                report_dir=tmp_path,
            )
        )


def test_unknown_and_formal_modes_fail_closed(tmp_path: Path) -> None:
    contract = materialize_fixture_contract(tmp_path)
    with pytest.raises(TrainingRunnerError, match="unknown_execution_mode"):
        run_contract_bound_training_runner(
            TrainingRunRequest(
                contract_path=contract,
                model_quality_policy_path=DEFAULT_POLICY_PATH,
                schema_dir=DEFAULT_SCHEMA_DIR,
                mode="BAD",  # type: ignore[arg-type]
                report_dir=tmp_path,
            )
        )
    formal = run_contract_bound_training_runner(
        TrainingRunRequest(
            contract_path=contract,
            model_quality_policy_path=DEFAULT_POLICY_PATH,
            schema_dir=DEFAULT_SCHEMA_DIR,
            mode="FORMAL_BOOTSTRAP",
            report_dir=tmp_path,
        )
    )
    assert formal["status"] == "REJECTED"
    assert formal["formal_generation_candidate_created"] is False
    assert formal["broker_write_executed"] is False


def test_formal_mode_rejects_unapproved_or_hash_mismatched_plan(tmp_path: Path) -> None:
    contract = materialize_fixture_contract(tmp_path)
    draft_plan = tmp_path / "draft_plan.json"
    draft_plan.write_text(
        json.dumps(
            {
                "plan_status": "DRAFT_REVIEW_REQUIRED",
                "decision": "HUMAN_REVIEW_REQUIRED",
                "reviewer": None,
                "execution_mode": "FORMAL_BOOTSTRAP",
                "plan_hash": "1" * 64,
                "reviewed_plan_hash": None,
            }
        ),
        encoding="utf-8",
    )
    rejected = run_contract_bound_training_runner(
        TrainingRunRequest(
            contract_path=contract,
            model_quality_policy_path=DEFAULT_POLICY_PATH,
            schema_dir=DEFAULT_SCHEMA_DIR,
            mode="FORMAL_BOOTSTRAP",
            report_dir=tmp_path,
            confirm=True,
            approved_execution_plan=draft_plan,
        )
    )
    assert rejected["status"] == "REJECTED"
    assert "execution_plan_not_approved" in rejected["plan_validation"]["reason_codes"]

    mismatched_plan = tmp_path / "mismatched_plan.json"
    mismatched_plan.write_text(
        json.dumps(
            {
                "plan_status": "APPROVED",
                "decision": "APPROVE",
                "reviewer": "user:negishi",
                "execution_mode": "FORMAL_BOOTSTRAP",
                "plan_hash": "2" * 64,
                "reviewed_plan_hash": "3" * 64,
            }
        ),
        encoding="utf-8",
    )
    blocked = run_contract_bound_training_runner(
        TrainingRunRequest(
            contract_path=contract,
            model_quality_policy_path=DEFAULT_POLICY_PATH,
            schema_dir=DEFAULT_SCHEMA_DIR,
            mode="FORMAL_BOOTSTRAP",
            report_dir=tmp_path,
            confirm=True,
            approved_execution_plan=mismatched_plan,
        )
    )
    assert blocked["status"] == "BLOCK"
    assert "reviewed_plan_hash_mismatch" in blocked["plan_validation"]["reason_codes"]


def test_direct_bypass_and_prohibited_paths_reject(tmp_path: Path) -> None:
    contract = materialize_fixture_contract(tmp_path)
    request = TrainingRunRequest(
        contract_path=contract,
        model_quality_policy_path=DEFAULT_POLICY_PATH,
        schema_dir=DEFAULT_SCHEMA_DIR,
        mode="VALIDATE_ONLY",
        report_dir=tmp_path,
    )
    for override in (
        {"dataset_dir": "x"},
        {"dataset_path": "x"},
        {"split_path": "x"},
        {"recompute_split": True},
        {"random_split": True},
        {"latest_glob": "*"},
        {"runtime_state_path": ".runtime/runtime_state/current_state.json"},
        {"broker_state_path": "broker/snapshot.json"},
        {"model_quality_thresholds": {"minimum_training_rows": 1}},
    ):
        with pytest.raises(TrainingRunnerError):
            run_contract_bound_training_runner(request, **override)


def test_unapproved_policy_and_hash_mismatch_reject(tmp_path: Path) -> None:
    policy = json.loads(DEFAULT_POLICY_PATH.read_text(encoding="utf-8"))
    bad_status = tmp_path / "bad_status_policy.json"
    bad_status.write_text(json.dumps({**policy, "policy_status": "DRAFT_REVIEW_REQUIRED"}), encoding="utf-8")
    with pytest.raises(ModelQualityPolicyError, match="policy_not_approved"):
        load_approved_model_quality_policy(bad_status)

    bad_hash = tmp_path / "bad_hash_policy.json"
    bad_hash.write_text(json.dumps({**policy, "policy_hash": "0" * 64}), encoding="utf-8")
    with pytest.raises(ModelQualityPolicyError, match="reviewed_policy_hash_mismatch|policy_hash_mismatch"):
        load_approved_model_quality_policy(bad_hash)


def test_quality_gate_blocks_missing_and_one_sided_labels() -> None:
    policy = load_approved_model_quality_policy(DEFAULT_POLICY_PATH)
    base = {
        "training_rows": 10,
        "validation_rows": 5,
        "training_business_days": 5,
        "validation_business_days": 2,
        "distinct_issues": 3,
        "positive_labels": 5,
        "negative_labels": 5,
        "class_ratio": 0.5,
        "feature_coverage": 1.0,
        "missing_ratio": 0.0,
        "constant_feature_ratio": 0.0,
        "invalid_numeric_ratio": 0.0,
        "unexpected_constant_feature_count": 0,
        "critical_feature_missing": False,
    }
    missing = evaluate_training_quality(component="Candidate", policy=policy, metrics={**base, "missing_ratio": 0.5}, execution_mode="FIXTURE_SMOKE")
    one_sided = evaluate_training_quality(component="Candidate", policy=policy, metrics={**base, "negative_labels": 0}, execution_mode="FIXTURE_SMOKE")
    unexpected_constant = evaluate_training_quality(
        component="Candidate",
        policy=policy,
        metrics={**base, "unexpected_constant_feature_count": 1},
        execution_mode="FIXTURE_SMOKE",
    )

    assert missing["fixture_structural_result"] == "BLOCK"
    assert one_sided["fixture_structural_result"] == "BLOCK"
    assert unexpected_constant["fixture_structural_result"] == "BLOCK"
