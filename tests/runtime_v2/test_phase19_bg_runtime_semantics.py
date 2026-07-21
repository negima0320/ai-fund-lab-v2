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


def _report() -> dict:
    result = _run_system_status("--runtime-root", str(ISOLATED_ROOT), "--json")
    assert result.returncode == 0
    return json.loads(result.stdout)["system_status_report"]


def _component(report: dict, component_id: str) -> dict:
    return next(item for item in report["complete_component_inventory"]["components"] if item["component_id"] == component_id)


def test_pre_run_runtime_result_status_is_not_conflated_with_inspection_pass() -> None:
    report = _report()

    for component_id in [
        "runtime_baseline",
        "freshness_evaluation",
        "lifecycle_monitoring",
        "safety_decision",
        "capital_policy",
        "buy_planning",
        "sell_planning_continuity",
        "approval",
    ]:
        component = _component(report, component_id)
        assert component["inspection_status"] == "PASS"
        assert component["configuration_status"] == "PASS"
        assert component["target_date_execution_status"] == "NOT_YET_APPLICABLE"
        assert component["runtime_result_status"] == "NOT_YET_MATERIALIZED"

    for component_id in ["submit_guard", "execution_guard", "ledger_update", "reporting", "notification"]:
        component = _component(report, component_id)
        assert component["inspection_status"] == "PASS"
        assert component["configuration_status"] == "PASS"
        assert component["target_date_execution_status"] == "NOT_PERFORMED"
        assert component["runtime_result_status"] == "NOT_PERFORMED"


def test_model_loadability_and_target_date_inference_are_separated() -> None:
    report = _report()

    for component_id in ["candidate_ai", "opportunity_ai"]:
        component = _component(report, component_id)
        assert component["model_load_status"] == "PASS"
        assert component["target_date_execution_status"] == "NOT_YET_APPLICABLE"
        assert component["runtime_result_status"] == "NOT_YET_MATERIALIZED"
        assert component["runtime_status"] == "MODEL_LOADABLE"


def test_runtime_chain_contains_separate_semantic_status_fields() -> None:
    report = _report()

    for item in report["runtime_chain_inspection"]["chain"]:
        assert item["inspection_status"] == "PASS"
        assert item["configuration_status"] == "PASS"
        assert item["authority_resolution_status"] == "PASS"
        assert item["target_date_execution_status"] != ""
        assert item["runtime_result_status"] != ""
    reporting = next(item for item in report["runtime_chain_inspection"]["chain"] if item["component_id"] == "reporting")
    assert reporting["target_date_execution_status"] == "NOT_PERFORMED"
    assert reporting["runtime_result_status"] == "NOT_PERFORMED"


def test_jquants_dependency_type_and_paths_are_contractual() -> None:
    report = _report()
    dependencies = report["jquants_dependency_matrix"]["dependencies"]
    by_id = {item["component_id"]: item for item in dependencies}

    assert {item["jquants_dependency_type"] for item in dependencies}.issubset({"DIRECT", "INDIRECT", "NONE"})
    assert by_id["market_refresh"]["jquants_dependency_type"] == "DIRECT"
    assert by_id["feature_refresh"]["jquants_dependency_type"] == "DIRECT"
    assert by_id["candidate_ai"]["jquants_dependency_type"] == "DIRECT"
    assert by_id["opportunity_ai"]["jquants_dependency_type"] == "DIRECT"
    assert by_id["capital_policy"]["jquants_dependency_type"] == "INDIRECT"
    assert by_id["buy_planning"]["jquants_dependency_type"] == "INDIRECT"
    assert by_id["sell_planning_continuity"]["jquants_dependency_type"] == "INDIRECT"
    assert by_id["approval"]["jquants_dependency_type"] == "NONE"
    assert by_id["submit_guard"]["jquants_dependency_type"] == "NONE"
    assert by_id["execution_guard"]["jquants_dependency_type"] == "NONE"
    assert by_id["reporting"]["jquants_dependency_type"] == "NONE"
    assert by_id["notification"]["jquants_dependency_type"] == "NONE"
    for item in dependencies:
        assert item["jquants_dependency_path"]
        assert item["jquants_dependency_reason"] != ""


def test_historical_source_coverage_and_consumer_cutoff_are_separated() -> None:
    report = _report()
    cutoff = report["historical_source_consumer_cutoff"]
    market = _component(report, "market_refresh")

    assert cutoff["source_available_through_date"] == "2026-07-14"
    assert cutoff["required_through_date"] == "2026-07-06"
    assert cutoff["consumer_cutoff_date"] == "2026-07-06"
    assert cutoff["future_rows_available"] is True
    assert cutoff["future_rows_consumed"] == "NOT_YET_MATERIALIZED"
    assert cutoff["temporal_contract_status"] == "PASS"
    assert market["source_materialization_mode"] == "PRELOADED_HISTORICAL_SOURCE"
    assert market["refresh_command_execution_status"] == "NOT_PERFORMED"
    assert market["historical_source_coverage_status"] == "PASS"


def test_no_empty_values_and_human_json_parity_for_bg_fields() -> None:
    report = _report()
    hits: list[str] = []

    def walk(value, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else key
                if child == "":
                    hits.append(child_path)
                walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    walk(report)
    assert hits == []
    human = report["human_summary"]
    for text in [
        "Overall Status Scope",
        "Historical Source / Consumer Cutoff",
        "target_date_execution_status",
        "runtime_result_status",
        "jquants_dependency_type",
        "jquants_dependency_path",
        "future_rows_consumed",
    ]:
        assert text in human


def test_bg_non_mutation_and_be_bf_regression_surfaces_remain() -> None:
    before = protected_shared_runtime_hashes(REPO_ROOT / ".runtime")
    report = _report()
    after = protected_shared_runtime_hashes(REPO_ROOT / ".runtime")

    assert before == after
    assert report["candidate_input_lineage"]["status"] == "PASS"
    assert report["opportunity_input_lineage"]["status"] == "PASS"
    assert report["complete_component_inventory"]["status"] == "PASS"
    assert report["inspection_coverage"]["status"] == "PASS"
    assert report["authority_generation"]["status"] == "PASS"
    assert report["non_mutation"]["broker_access"] == "NOT_PERFORMED"
    assert report["non_mutation"]["broker_write"] == 0
