from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TEST = REPO_ROOT / "scripts" / "runtime_test.py"


def _run_system_status(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNTIME_TEST), "system-status", *args],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": "src"},
        text=True,
        capture_output=True,
        check=False,
    )


def test_phase19_bw_default_scope_is_compact_overview() -> None:
    result = _run_system_status()
    assert result.returncode == 20
    assert "AI Fund Lab v2 System Status" in result.stdout
    assert "Inspection          : BLOCK" in result.stdout
    assert "Runtime Execution   : PASS" in result.stdout
    assert "Model Health        : BLOCK" in result.stdout
    assert "Broker Connectivity : NOT_PERFORMED" in result.stdout
    assert "## 10. Complete Component Inventory" not in result.stdout
    assert len(result.stdout.splitlines()) <= 100


def test_phase19_bw_scope_json_matches_selected_scope_and_preserves_legacy_report() -> None:
    for scope in ("overview", "data", "ai", "runtime", "broker", "readiness", "lineage", "components", "full"):
        result = _run_system_status("--scope", scope, "--json")
        assert result.returncode == 20
        payload = json.loads(result.stdout)
        assert payload["scope"] == scope
        assert payload["system_status_schema_version"] == "runtime_test_system_status_v2"
        assert payload["status_summary"]["inspection_judgment"] == "BLOCK"
        assert payload["status_summary"]["runtime_execution_judgment"] == "PASS"
        assert payload["status_summary"]["model_health_judgment"] == "BLOCK"
        assert "system_status_report" in payload
        expected = set(payload["sections"]) if scope == "full" else {scope, "strategy_shadow_readiness"}
        assert set(payload["sections"]) == expected


def test_phase19_bw_invalid_scope_fails_clearly() -> None:
    result = _run_system_status("--scope", "nope")
    assert result.returncode != 0
    assert "invalid choice" in result.stderr


def test_phase19_bw_post_run_truthfulness_json() -> None:
    result = _run_system_status("--json")
    assert result.returncode == 20
    payload = json.loads(result.stdout)
    report = payload["system_status_report"]
    assert payload["status_summary"]["data_judgment"] == "BLOCK"
    assert payload["status_summary"]["runtime_execution_judgment"] == "PASS"
    assert payload["status_summary"]["model_health_runtime_impact"] == "NONE"
    target_business_date = report["inspection_context"]["target_business_date"]
    assert report["data_status"]["feature"]["feature_date"] == target_business_date
    assert report["data_status"]["feature"]["expected_inference_feature_date"] == target_business_date
    assert report["data_status"]["feature"]["future_fixture_artifact_excluded"] is True
    assert "post_run_execution_evidence_sufficiency" not in report["target_period_data_sufficiency"]
    assert "current_shared_runtime_artifact_retention" not in report["target_period_data_sufficiency"]
    position_feature = next(
        item
        for item in report["data_inspection"]["runtime_features"]
        if item["component_id"] == "position_runtime_feature"
    )
    assert position_feature["position_feature_authority_status"] in {"TEMPORAL_ISOLATION_PASS", "NOT_APPLICABLE"}
    if position_feature["position_feature_authority_status"] == "NOT_APPLICABLE":
        assert position_feature["position_feature_final_position_semantics"] == "target-date feature rows and final post-run positions are distinct authorities"
    if position_feature["final_post_run_position_count_authority"] == "CURRENT_RUNTIME_ROOT_FINAL_HASH_MATCH":
        state_path = REPO_ROOT / ".runtime" / "persistent_ledger" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert position_feature["final_post_run_position_count"] == len(state.get("positions") or [])
    else:
        assert isinstance(position_feature["final_post_run_position_count"], int)
        assert position_feature["final_post_run_position_count_authority"] in {
            "CURRENT_RUNTIME_ROOT",
            "CURRENT_RUNTIME_ROOT_FINAL_HASH_MISMATCH",
            "NOT_AVAILABLE_FINAL_STATE_HASH_MISMATCH",
        }
    assert position_feature["status"] == "PASS"
    age = report["authority_generation"]["accepted_generation_age"]
    assert {"accepted_at", "current_time", "age_seconds", "age_hours", "age_days", "human"} <= set(age)


def test_phase19_bw_system_status_is_read_only() -> None:
    before = _run_system_status("--json")
    assert before.returncode == 20
    before_hashes = json.loads(before.stdout)["system_status_report"]["inspection_context"]
    result = _run_system_status("--scope", "runtime", "--json")
    assert result.returncode == 20
    after = _run_system_status("--json")
    assert after.returncode == 20
    after_hashes = json.loads(after.stdout)["system_status_report"]["inspection_context"]
    assert before_hashes.get("runtime_test_run_id", "") == after_hashes.get("runtime_test_run_id", "")
    assert before_hashes["target_business_date"] == after_hashes["target_business_date"]
