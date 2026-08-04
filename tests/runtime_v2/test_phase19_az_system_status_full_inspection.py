from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TEST = REPO_ROOT / "scripts/runtime_test.py"


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


def test_system_status_full_scope_output_is_full_inspection() -> None:
    result = _run_system_status("--scope", "full")

    assert result.returncode == 20
    assert "Historical Temporal Isolation" in result.stdout
    assert "Active Component Inventory" in result.stdout
    assert "Data Sources" in result.stdout
    assert "Datasets" in result.stdout
    assert "Runtime Features" in result.stdout
    assert "AI Models" in result.stdout
    assert "AI Data Window Summary" in result.stdout
    assert "Decision Subsystems" in result.stdout
    assert "Freshness Matrix" in result.stdout
    assert "Candidate Runtime Feature" in result.stdout
    assert "Opportunity Runtime Feature" in result.stdout
    assert "Position Runtime Feature" in result.stdout
    assert "Capital Runtime Feature" in result.stdout


def test_system_status_json_contains_complete_inventory() -> None:
    result = _run_system_status("--scope", "full", "--json")
    payload = json.loads(result.stdout)
    report = payload["system_status_report"]

    inventory_ids = {item["component_id"] for item in report["active_component_inventory"]["components"]}
    assert "candidate_ai" in inventory_ids
    assert "opportunity_ai" in inventory_ids
    assert "safety_decision" in inventory_ids
    assert "position_management" in inventory_ids
    assert "legacy_latest_model_resolver" in inventory_ids

    feature_ids = {item["component_id"] for item in report["data_inspection"]["runtime_features"]}
    assert "candidate_runtime_feature" in feature_ids
    assert "opportunity_runtime_feature" in feature_ids
    assert "position_runtime_feature" in feature_ids
    assert "capital_runtime_feature" in feature_ids
    assert report["inspection_context"]["inspection_mode"] == "HISTORICAL_LIFECYCLE_GATE_DONE"
    assert report["inspection_context"]["target_business_date"] == "2026-07-06"
    assert report["temporal_authority_audit"]["temporal_isolation_status"] == "PASS"
    assert report["temporal_authority_audit"]["future_state_reference_count"] == 0


def test_candidate_evaluated_count_and_output_count_are_separate() -> None:
    result = _run_system_status("--scope", "full", "--json")
    payload = json.loads(result.stdout)
    models = {
        item["component_id"]: item
        for item in payload["system_status_report"]["active_component_inventory"]["active_ai_models"]
    }

    candidate = models["candidate_ai"]
    opportunity = models["opportunity_ai"]

    assert candidate["evaluated_symbols"] == "NOT_YET_MATERIALIZED"
    assert candidate["candidate_output_count"] == 50
    assert candidate["candidate_top50_count"] == 50
    assert opportunity["input_candidate_count"] == 50
    assert opportunity["ranking_count"] == 50
    assert opportunity["top20_count"] == 20
    assert opportunity["dual_gate_status"] == "DUAL_GATE_PASS"
    assert opportunity["latest_inference_input_date"] == "2026-07-06"
    assert opportunity["artifact_created_at"].startswith("2026-07-05")


def test_runtime_feature_projection_separates_metadata_and_candidate_dependency() -> None:
    result = _run_system_status("--scope", "full", "--json")
    payload = json.loads(result.stdout)
    features = {
        item["component_id"]: item
        for item in payload["system_status_report"]["data_inspection"]["runtime_features"]
    }

    candidate = features["candidate_runtime_feature"]
    opportunity = features["opportunity_runtime_feature"]

    assert candidate["artifact_column_count"] == 0
    assert candidate["model_input_feature_count"] == 13
    assert candidate["missing_model_features"]
    assert candidate["feature_order_validation"] == "BLOCK"

    assert opportunity["artifact_column_count"] == 0
    assert opportunity["model_input_feature_count"] == 32
    assert opportunity["candidate_dependency_features"] == [
        "candidate_rank",
        "candidate_reason",
        "candidate_score",
    ]
    assert opportunity["missing_model_features"]
    assert opportunity["feature_order_validation"] == "BLOCK"


def test_evidence_writes_full_inspection_files(tmp_path: Path) -> None:
    result = _run_system_status("--scope", "full", "--json", "--write-evidence", "--evidence-root", str(tmp_path))
    payload = json.loads(result.stdout)
    evidence_path = Path(payload["evidence_path"])

    expected = {
        "active_component_inventory.json",
        "ai_system_inventory.md",
        "data_inspection.json",
        "decision_subsystems.json",
        "authority_generation.json",
        "temporal_authority_audit.json",
        "freshness_matrix.json",
        "target_period_data_sufficiency.json",
        "system_status_report.md",
    }
    assert expected.issubset({path.name for path in evidence_path.iterdir()})
