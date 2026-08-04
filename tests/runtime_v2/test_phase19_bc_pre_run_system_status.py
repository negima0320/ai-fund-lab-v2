from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.historical_support.isolated_root import protected_shared_runtime_hashes
from ai_fund_lab_v2.runtime_v2.system_status import classify_stage_artifact_materialization


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TEST = REPO_ROOT / "scripts/runtime_test.py"
ISOLATED_ROOT = REPO_ROOT / ".runtime/runtime_tests/phase19_bb_historical_smoke_20260706_clean_day1/.runtime"


def _run_system_status(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src:."
    return subprocess.run(
        [sys.executable, str(RUNTIME_TEST), "system-status", *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_clean_pre_run_isolated_root_system_status_pass() -> None:
    before = protected_shared_runtime_hashes(REPO_ROOT / ".runtime")
    result = _run_system_status("--runtime-root", str(ISOLATED_ROOT), "--json")
    after = protected_shared_runtime_hashes(REPO_ROOT / ".runtime")
    payload = json.loads(result.stdout)
    report = payload["system_status_report"]

    assert result.returncode == 20
    assert payload["status"] == "BLOCK"
    assert report["runtime_stage_contract"]["runtime_stage"] == "PRE_RUN"
    assert report["runtime_stage_contract"]["pre_run_readiness"] == "PASS"
    assert report["runtime_stage_contract"]["day1_start_permission"] == "ALLOWED"
    assert report["overall_status"]["status"] == "BLOCK"
    assert before == after
    assert report["non_mutation"]["broker_access"] == "NOT_PERFORMED"
    assert report["non_mutation"]["broker_write"] == 0


def test_model_loadability_and_pre_run_missing_artifacts_are_separated() -> None:
    result = _run_system_status("--runtime-root", str(ISOLATED_ROOT), "--json")
    report = json.loads(result.stdout)["system_status_report"]
    models = {item["component_id"]: item for item in report["active_component_inventory"]["active_ai_models"]}
    features = {item["component_id"]: item for item in report["data_inspection"]["runtime_features"]}
    subsystems = {item["component_id"]: item for item in report["decision_subsystems"]["subsystems"]}

    for model in (models["candidate_ai"], models["opportunity_ai"]):
        assert model["model_authority_resolution_status"] == "BLOCK"
        assert model["model_artifact_resolution_status"] == "PASS"
        assert model["model_hash_validation_status"] == "PASS"
        assert model["scaler_resolution_status"] == "BLOCK"
        assert model["calibration_resolution_status"] == "BLOCK"
        assert model["model_loader_validation_status"] == "PASS"
        assert model["target_date_feature_status"] == "NOT_YET_APPLICABLE"
        assert model["target_date_inference_status"] == "NOT_YET_APPLICABLE"
        assert model["missing_state_classification"] == "PRE_RUN_NOT_MATERIALIZED"

    assert features["candidate_runtime_feature"]["status"] == "NOT_YET_APPLICABLE"
    assert features["opportunity_runtime_feature"]["status"] == "NOT_YET_APPLICABLE"
    assert subsystems["lifecycle_monitoring"]["status"] == "NOT_YET_APPLICABLE"
    assert subsystems["buy_planning"]["status"] == "NOT_YET_APPLICABLE"


def test_post_stage_missing_artifacts_block() -> None:
    cases = [
        ("candidate_runtime_feature", "FEATURE_READY", "FEATURE_READY"),
        ("candidate_inference", "AI_INFERENCE_DONE", "AI_INFERENCE_DONE"),
        ("opportunity_inference", "AI_INFERENCE_DONE", "AI_INFERENCE_DONE"),
        ("ai_lifecycle_gate", "LIFECYCLE_GATE_DONE", "LIFECYCLE_GATE_DONE"),
        ("buy_planning", "DAILY_PLAN_CREATED", "DAILY_PLAN_CREATED"),
    ]
    for component_id, expected_stage, current_stage in cases:
        result = classify_stage_artifact_materialization(
            component_id=component_id,
            expected_generation_stage=expected_stage,
            current_runtime_stage=current_stage,
            exists=False,
        )
        assert result["status"] == "BLOCK"
        assert result["missing_state_classification"] == "POST_STAGE_MATERIALIZATION_MISSING"


def test_freshness_coverage_and_calibration_window_semantics() -> None:
    result = _run_system_status("--runtime-root", str(ISOLATED_ROOT), "--json")
    report = json.loads(result.stdout)["system_status_report"]
    freshness = {item["component_id"]: item for item in report["freshness_matrix"]["items"]}
    windows = {item["component_id"]: item for item in report["ai_data_window_summary"]["items"]}

    normalized = freshness["normalized_j-quants_daily_quotes"]
    assert normalized["required_through_date"] == "2026-07-06"
    assert normalized["available_through_date"] == "2026-07-14"
    assert normalized["missing_required_business_days"] == 0
    assert normalized["coverage_ahead_business_days"] > 0
    assert normalized["freshness_date_semantics"] == "historical_coverage_not_lag"

    assert windows["candidate_data_window_summary"]["calibration"]["mode"] == "SHARED_WITH_VALIDATION"
    assert windows["candidate_data_window_summary"]["calibration"]["fit_window_role"] == "CALIBRATION_FIT_WINDOW"
    assert windows["opportunity_data_window_summary"]["calibration"]["status"] == "REVIEW_REQUIRED"


def test_active_trained_ai_inventory_is_evidenced() -> None:
    result = _run_system_status("--runtime-root", str(ISOLATED_ROOT), "--json")
    report = json.loads(result.stdout)["system_status_report"]
    inventory = report["active_trained_ai_inventory"]

    assert inventory["status"] == "PASS"
    assert inventory["active_trained_model_count"] == 2
    assert inventory["active_trained_models"] == ["candidate_ai", "opportunity_ai"]
    assert inventory["inventory_evidence"]
