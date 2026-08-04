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
    assert result.returncode in {0, 20}
    return json.loads(result.stdout)["system_status_report"]


def test_complete_component_inventory_contains_all_operational_components() -> None:
    report = _report()
    inventory = report["complete_component_inventory"]
    component_ids = {item["component_id"] for item in inventory["components"]}

    assert inventory["status"] == "PASS"
    assert {
        "candidate_ai",
        "opportunity_ai",
        "runtime_baseline",
        "freshness_evaluation",
        "lifecycle_monitoring",
        "safety_decision",
        "position_management",
        "capital_policy",
        "buy_planning",
        "sell_planning_continuity",
        "approval",
        "submit_guard",
        "execution_guard",
        "reporting",
        "notification",
    }.issubset(component_ids)
    assert inventory["unresolved_components"] == []


def test_component_contract_fields_are_complete_and_non_empty() -> None:
    report = _report()
    required = {
        "component_name",
        "component_type",
        "active_or_inactive",
        "authority",
        "implementation",
        "input_artifact",
        "output_artifact",
        "input_components",
        "input_business_date",
        "output_business_date",
        "configuration_status",
        "runtime_status",
        "inspection_status",
    }
    allowed_missing = {"NOT_APPLICABLE", "NOT_YET_MATERIALIZED", "NOT_RECORDED", "UNRESOLVED"}

    for component in report["complete_component_inventory"]["components"]:
        assert required.issubset(component)
        for key in required:
            value = component[key]
            assert value != ""
            if isinstance(value, list):
                assert value
                assert all(item != "" for item in value)
            elif isinstance(value, str) and value.startswith("UNRESOLVED"):
                assert value in {"UNRESOLVED", "UNRESOLVED_COMPONENT"} or value in allowed_missing
        assert component["inspection_status"] == "PASS"


def test_runtime_chain_dependency_jquants_and_state_coverage_pass() -> None:
    report = _report()
    chain = report["runtime_chain_inspection"]
    dependencies = report["component_dependency_matrix"]
    jquants = report["jquants_dependency_matrix"]
    state = report["runtime_state_coverage"]

    assert chain["status"] == "PASS"
    assert [item["component_id"] for item in chain["chain"]] == [
        "market_refresh",
        "feature_refresh",
        "candidate_ai",
        "opportunity_ai",
        "lifecycle_monitoring",
        "safety_decision",
        "buy_planning",
        "sell_planning_continuity",
        "approval",
        "submit_guard",
        "execution_guard",
        "ledger_update",
        "reporting",
        "notification",
    ]
    assert dependencies["status"] == "PASS"
    assert jquants["status"] == "PASS"
    by_id = {item["component_id"]: item["JQUANTS_DEPENDENT"] for item in jquants["dependencies"]}
    assert by_id["candidate_ai"] == "YES"
    assert by_id["opportunity_ai"] == "YES"
    assert by_id["approval"] == "NO"
    assert by_id["submit_guard"] == "NO"
    assert by_id["execution_guard"] == "NO"
    assert by_id["reporting"] == "NO"
    assert by_id["notification"] == "NO"
    assert state["status"] == "PASS"
    assert {"current", "pending", "ledger", "pm", "safety", "approval", "planning", "reporting", "notification"}.issubset(
        {item["component_id"] for item in state["items"]}
    )


def test_inspection_coverage_and_human_json_parity() -> None:
    report = _report()
    coverage = report["inspection_coverage"]
    human = report["human_summary"]

    assert coverage["status"] == "PASS"
    assert coverage["total_active_components"] == coverage["inspected_components"]
    assert coverage["unresolved"] == 0
    assert coverage["repository_scan_matches_inventory"] is True
    for section in [
        "Complete Component Inventory",
        "Component Dependency Matrix",
        "Runtime Chain Inspection",
        "J-Quants Dependency Matrix",
        "Runtime State Coverage",
        "Inspection Coverage",
        "Total active operational components",
        "Unresolved operational components: 0",
    ]:
        assert section in human


def test_bf_non_mutation_and_be_regression_surfaces_remain() -> None:
    before = protected_shared_runtime_hashes(REPO_ROOT / ".runtime")
    report = _report()
    after = protected_shared_runtime_hashes(REPO_ROOT / ".runtime")

    assert before == after
    assert report["candidate_input_lineage"]["status"] == "PASS"
    assert report["opportunity_input_lineage"]["status"] == "PASS"
    assert report["runtime_input_lineage_contract"]["status"] == "PASS"
    assert report["baseline_traceability"]["status"] == "REVIEW_REQUIRED"
    assert report["freshness_policy_traceability"]["status"] == "REVIEW_REQUIRED"
    assert report["authority_generation"]["status"] == "BLOCK"
    assert report["non_mutation"]["broker_access"] == "NOT_PERFORMED"
    assert report["non_mutation"]["broker_write"] == 0
