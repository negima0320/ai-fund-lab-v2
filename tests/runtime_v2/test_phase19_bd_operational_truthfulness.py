from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.historical_support.isolated_root import protected_shared_runtime_hashes


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


def _isolated_report() -> dict:
    result = _run_system_status("--runtime-root", str(ISOLATED_ROOT), "--json")
    assert result.returncode in {0, 20}
    return json.loads(result.stdout)["system_status_report"]


def test_inspection_context_and_environment_readiness_are_truthful() -> None:
    report = _isolated_report()
    context = report["inspection_context"]
    readiness = report["environment_readiness"]

    assert context["inspection_mode"] == "HISTORICAL_PRE_RUN"
    assert context["runtime_mode"] == "historical"
    assert context["broker_environment"] == "historical_simulated"
    assert context["runtime_root_type"] == "ISOLATED_RUNTIME_TEST_ROOT"
    assert context["shared_runtime_root_used"] is False
    assert context["target_business_date"] == "2026-07-06"
    assert readiness["historical_pre_run_readiness"] == "NOT_APPLICABLE"
    assert readiness["single_day_runtime_readiness"] == "NOT_EVALUATED"
    assert readiness["production_current_data_readiness"] == "NOT_EVALUATED"
    assert readiness["demo_current_data_readiness"] == "NOT_EVALUATED"
    assert readiness["production_ready"] is False
    assert readiness["buy_ready"] is False


def test_broker_not_performed_is_not_connectivity_pass() -> None:
    report = _isolated_report()
    broker = report["broker_truthfulness_audit"]
    broker_layer = report["broker_layer_status"]

    assert broker["broker_configuration_status"] == "PASS"
    assert broker["broker_connectivity_check_status"] == "NOT_PERFORMED"
    assert broker["credential_access_status"] == "NOT_PERFORMED"
    assert broker["broker_write_status"] == "PROHIBITED"
    assert broker_layer["broker_connection"]["status"] == "NOT_PERFORMED"
    assert broker_layer["summary"]["status"] == "CONFIGURATION_PASS_CONNECTIVITY_NOT_PERFORMED"


def test_current_data_freshness_is_separate_from_historical_coverage() -> None:
    report = _isolated_report()

    assert report["historical_coverage"]["status"] == "PASS"
    assert report["production_freshness"]["status"] == "NOT_EVALUATED"
    assert report["demo_freshness"]["status"] == "NOT_EVALUATED"
    assert report["production_freshness"]["expected_date_source"] == "local_trading_calendar_policy_and_current_time"
    assert report["production_freshness"]["refresh_status"] == "EXTERNAL_AVAILABILITY_NOT_VERIFIED"


def test_baseline_and_freshness_traceability_are_resolved() -> None:
    report = _isolated_report()
    baseline = report["baseline_traceability"]
    freshness = report["freshness_policy_traceability"]

    assert baseline["baseline_scope"] == "GENERATION_SHARED"
    assert baseline["baseline_storage_mode"] == "EMBEDDED_IN_ACCEPTED_GENERATION"
    assert baseline["baseline_binding_hash"]
    assert baseline["baseline_resolution_status"] == "REVIEW_REQUIRED"
    assert freshness["freshness_binding_hash"]
    assert freshness["resolution_status"] == "REVIEW_REQUIRED"
    assert freshness["target_date_decision_status"] == "NOT_YET_APPLICABLE"


def test_recent_holdout_and_calibration_semantics_are_explicit() -> None:
    report = _isolated_report()

    for item in report["recent_holdout_usage_audit"]["items"]:
        assert item["recent_holdout_usage_status"] == "NOT_USED_IN_PHASE19"
        assert item["recent_holdout_runtime_authority_impact"] == "NONE"
    for item in report["calibration_validation_independence_audit"]["items"]:
        assert item["calibration_mode"] == "SHARED_WITH_VALIDATION"
        assert item["model_selection_used_this_window"] is False
        assert item["independent_final_evaluation_window"]


def test_active_data_and_model_inventory_are_complete() -> None:
    report = _isolated_report()
    data_ids = {item["component_id"] for item in report["data_source_inventory"]["items"]}

    assert {"raw_jquants_daily_quotes", "normalized_jquants_daily_quotes", "listed_issues", "trading_calendar", "universe_eligibility"}.issubset(data_ids)
    assert report["active_model_summary"]["active_trained_model_count"] == 2
    assert report["active_model_summary"]["models_with_complete_artifact_validation"] == 0
    assert report["active_model_summary"]["models_with_unresolved_artifact_validation"] == 2


def test_no_dot_placeholder_or_empty_materialized_dates() -> None:
    report = _isolated_report()
    dot_hits: list[str] = []
    empty_materialized_dates: list[str] = []

    def walk(value, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{path}.{key}" if path else key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                if path.endswith("runtime_feature_materialized_dates") and child == "":
                    empty_materialized_dates.append(f"{path}[{index}]")
                walk(child, f"{path}[{index}]")
        elif value == ".":
            dot_hits.append(path)

    walk(report)
    assert set(dot_hits) <= {
        "ai_status.accepted_generation.manifest_path",
        "ai_status.accepted_generation_status.manifest_path",
        "runtime_status.committed.manifest_path",
    }
    assert empty_materialized_dates == []


def test_human_output_matches_json_operational_summary_and_non_mutation() -> None:
    before = protected_shared_runtime_hashes(REPO_ROOT / ".runtime")
    result = _run_system_status("--runtime-root", str(ISOLATED_ROOT), "--json")
    after = protected_shared_runtime_hashes(REPO_ROOT / ".runtime")
    payload = json.loads(result.stdout)
    report = payload["system_status_report"]
    human = report["human_summary"]

    assert "Inspection Mode: HISTORICAL_PRE_RUN" in human
    assert "Production Current-data Readiness: NOT_EVALUATED" in human
    assert "Broker Connectivity Readiness: NOT_PERFORMED" in human
    assert "Active trained model count: 2" in human
    assert report["operational_summary"]["not_evaluated"]
    assert before == after
    assert report["non_mutation"]["broker_access"] == "NOT_PERFORMED"
    assert report["non_mutation"]["broker_write"] == 0
