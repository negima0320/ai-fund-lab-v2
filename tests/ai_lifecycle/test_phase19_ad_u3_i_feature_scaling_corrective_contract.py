from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.ai_lifecycle.ad_u3_contract_bound_training_runner import (
    DEFAULT_POLICY_PATH,
    DEFAULT_SCHEMA_DIR,
    TrainingRunRequest,
    materialize_fixture_contract,
    run_contract_bound_training_runner,
    validate_model_scaler_binding,
)
from ai_fund_lab_v2.ai_lifecycle.ad_u3_scaling_contract import (
    DEFAULT_CORRECTIVE_ACTION_POLICY_PATH,
    CorrectiveActionPolicyError,
    load_approved_corrective_action_policy,
    scaler_method_decision,
)
from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_artifact_writer import file_hash


def test_corrective_action_policy_is_human_approved_and_hash_bound() -> None:
    policy = load_approved_corrective_action_policy(DEFAULT_CORRECTIVE_ACTION_POLICY_PATH)

    assert policy["policy_status"] == "APPROVED"
    assert policy["reviewer"] == "user:negishi"
    assert policy["decision"] == "APPROVE"
    assert policy["approved_option"] == "OPTION_A_CONTRACT_BOUND_FEATURE_SCALING"
    assert policy["reviewed_policy_hash"] == policy["policy_hash"]
    assert policy["approved_scope"]["formal_corrective_training_allowed"] is False


def test_fixture_scaling_smoke_requires_corrective_policy(tmp_path: Path) -> None:
    contract = materialize_fixture_contract(tmp_path)

    with pytest.raises(CorrectiveActionPolicyError, match="corrective_action_policy_required"):
        run_contract_bound_training_runner(
            TrainingRunRequest(
                contract_path=contract,
                model_quality_policy_path=DEFAULT_POLICY_PATH,
                schema_dir=DEFAULT_SCHEMA_DIR,
                mode="FIXTURE_SCALING_SMOKE",
                report_dir=tmp_path / "reports",
            )
        )


def test_fixture_scaling_smoke_writes_scaler_artifacts_and_bindings(tmp_path: Path) -> None:
    contract = materialize_fixture_contract(tmp_path)
    result = run_contract_bound_training_runner(
        TrainingRunRequest(
            contract_path=contract,
            model_quality_policy_path=DEFAULT_POLICY_PATH,
            schema_dir=DEFAULT_SCHEMA_DIR,
            mode="FIXTURE_SCALING_SMOKE",
            report_dir=tmp_path / "reports",
            corrective_action_policy_path=DEFAULT_CORRECTIVE_ACTION_POLICY_PATH,
        )
    )

    assert result["status"] == "PASS"
    assert result["scaler_method"] == "StandardScaler"
    assert result["formal_generation_candidate_created"] is False
    assert result["runtime_pointer_written"] is False
    assert result["broker_write_executed"] is False
    for key in ("candidate", "opportunity"):
        component = result[key]
        artifact = component["artifact"]
        scaler = component["scaler_artifact"]
        assert artifact["runtime_eligibility"] is False
        assert scaler["runtime_eligibility"] is False
        assert artifact["scaler_artifact_id"] == scaler["artifact_id"]
        assert artifact["scaler_artifact_hash"] == scaler["content_hash"]
        assert artifact["scaler_method"] == "StandardScaler"
        assert component["model_scaler_binding_validation"]["status"] == "PASS"
        assert component["leakage_guard_validation"]["status"] == "PASS"
        assert component["scaler_schema_validation"]["status"] == "PASS"
        assert component["schema_validation"]["status"] == "PASS"
        assert file_hash(Path(scaler["scaler_file"])) == scaler["scaler_content_hash"]
        assert "feature__liquidity_avg_volume_20d" in scaler["scaled_feature_columns"]
        assert "feature__missing_flags_price" in scaler["excluded_feature_columns"]
        assert component["metrics"]["validation_test_holdout_used_for_scaler_fit"] is False
        train_liquidity = component["metrics"]["scaled_train_statistics"]["feature__liquidity_avg_volume_20d"]
        assert abs(train_liquidity["mean"]) < 1e-12
        assert 0.99 < train_liquidity["std"] < 1.01


def test_scaler_method_decision_is_not_human_blocked() -> None:
    decision = scaler_method_decision()

    assert decision["status"] == "PASS"
    assert decision["decision"] == "STANDARD_SCALER"
    assert decision["human_review_required"] is False


def test_model_scaler_binding_blocks_component_hash_and_feature_order_mismatch(tmp_path: Path) -> None:
    contract = materialize_fixture_contract(tmp_path)
    result = run_contract_bound_training_runner(
        TrainingRunRequest(
            contract_path=contract,
            model_quality_policy_path=DEFAULT_POLICY_PATH,
            schema_dir=DEFAULT_SCHEMA_DIR,
            mode="FIXTURE_SCALING_SMOKE",
            report_dir=tmp_path / "reports",
            corrective_action_policy_path=DEFAULT_CORRECTIVE_ACTION_POLICY_PATH,
        )
    )

    candidate_model = dict(result["candidate"]["artifact"])
    opportunity_scaler = dict(result["opportunity"]["scaler_artifact"])
    component_mismatch = validate_model_scaler_binding(candidate_model, opportunity_scaler)
    assert component_mismatch["status"] == "BLOCK"
    assert "component_match" in component_mismatch["reason_codes"]

    candidate_scaler = dict(result["candidate"]["scaler_artifact"])
    candidate_scaler["input_feature_columns"] = list(reversed(candidate_scaler["input_feature_columns"]))
    order_mismatch = validate_model_scaler_binding(candidate_model, candidate_scaler)
    assert order_mismatch["status"] == "BLOCK"
    assert "feature_order_match" in order_mismatch["reason_codes"]


def test_unapproved_corrective_policy_rejected(tmp_path: Path) -> None:
    policy = json.loads(DEFAULT_CORRECTIVE_ACTION_POLICY_PATH.read_text(encoding="utf-8"))
    bad_policy = tmp_path / "bad_corrective_policy.json"
    bad_policy.write_text(json.dumps({**policy, "policy_status": "DRAFT_REVIEW_REQUIRED"}), encoding="utf-8")

    with pytest.raises(CorrectiveActionPolicyError, match="corrective_policy_not_approved"):
        load_approved_corrective_action_policy(bad_policy)


def test_corrective_bootstrap_is_not_executed_without_separate_plan(tmp_path: Path) -> None:
    contract = materialize_fixture_contract(tmp_path)
    result = run_contract_bound_training_runner(
        TrainingRunRequest(
            contract_path=contract,
            model_quality_policy_path=DEFAULT_POLICY_PATH,
            schema_dir=DEFAULT_SCHEMA_DIR,
            mode="CORRECTIVE_BOOTSTRAP",
            report_dir=tmp_path / "reports",
            corrective_action_policy_path=DEFAULT_CORRECTIVE_ACTION_POLICY_PATH,
        )
    )

    assert result["status"] == "REJECTED"
    assert result["formal_generation_candidate_created"] is False
    assert result["runtime_pointer_written"] is False
    assert result["broker_write_executed"] is False
