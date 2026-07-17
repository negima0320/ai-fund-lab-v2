from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUEST_HASH = "sha256:56ebea4e14ffe7369f133260645720c49303711b74c21960973e833016b37f70"
BROKER_ORDER_HASH = "sha256:b80b43eeb157caa8a56c14684356cbbd0b9cddebc05905a49059f72e4861d153"
EXECUTION_ID = "phase15bv-demo-execution-equivalent-6501-sell-100"
CURRENT_HASH = "11cadb1bdda853fee9bef405acb951a5273848b0488d3c1c6ef007e1053b8bc4"


def _read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _read_jsonl(path: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (ROOT / path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _sha256(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def test_phase15bw_report_keeps_review_required_not_full_acceptance() -> None:
    report = _read_json("reports/phase_reports/phase15_bw_runtime_end_to_end_daily_system_test_review.json")

    assert report["phase"] == "Phase15-BW"
    assert report["broker_write_performed"] is False
    assert report["runtime_mutation_performed"] is False
    assert report["final_judgment"] == "END_TO_END_DAILY_SYSTEM_REVIEW_REQUIRED"
    assert report["recommended_next_prefix"] == "Phase15-BX Normal Runtime Mainline End-to-End Connection Closure"
    assert report["broker_connected_operational_test_readiness"] == "BROKER_CONNECTED_OPERATIONAL_TEST_NOT_READY"


def test_phase15bw_mainline_comparison_marks_harness_gaps() -> None:
    report = _read_json("reports/phase_reports/phase15_bw_runtime_end_to_end_daily_system_test_review.json")
    comparison = report["mainline_path_comparison"]

    assert comparison["submit_pipeline"] == "SIMULATION_ONLY"
    assert comparison["execution_processing"] == "ACCEPTANCE_HARNESS_ONLY"
    assert comparison["ledger"] == "ACCEPTANCE_HARNESS_ONLY"
    assert comparison["current"] == "ACCEPTANCE_HARNESS_ONLY"
    assert report["submit_path_status"] == (
        "REAL_BROKER_WRITE_ACCEPTED_BY_DIRECT_ADAPTER_BUT_NORMAL_SUBMIT_PIPELINE_REAL_WRITE_NOT_ACCEPTED"
    )
    assert report["execution_path_evaluation"]["acceptance_script_reimplemented_runtime_logic"] is True
    assert report["execution_path_evaluation"]["severity"] == "MAJOR_MAINLINE_GAP"


def test_phase15bw_artifact_linkage_from_bt_bu_bv_matches() -> None:
    bt = _read_json("reports/phase_reports/phase15_bt_explicit_demo_broker_write_execution.json")
    bu = _read_json("reports/phase_reports/phase15_bu_demo_broker_write_post_send_execution_evidence_review.json")
    bv = _read_json("reports/phase_reports/phase15_bv_execution_normalization_current_apply.json")
    normalized = _read_json("reports/phase_reports/phase15_bv/execution_normalization.json")

    assert bt["request_hash"] == REQUEST_HASH
    assert bt["broker_order_id_hash"] == BROKER_ORDER_HASH
    assert bu["final_judgment"] == "EXECUTION_EQUIVALENT_READY_DEMO_ONLY"
    assert bv["final_judgment"] == "CURRENT_APPLY_ACCEPTED_DEMO_ONLY"
    assert normalized["request_hash"] == REQUEST_HASH
    assert normalized["broker_order_hash"] == BROKER_ORDER_HASH
    assert normalized["execution_id"] == EXECUTION_ID
    assert normalized["execution_price"] == 100.0
    assert normalized["valuation_price"] == 4700.0
    assert normalized["production_equivalent"] is False


def test_phase15bw_current_integrity_and_idempotency_evidence_match() -> None:
    report = _read_json("reports/phase_reports/phase15_bw_runtime_end_to_end_daily_system_test_review.json")
    current = _read_json(".runtime_acceptance_phase15_demo_reinit/persistent_ledger/state.json")
    pending = _read_json(".runtime_acceptance_phase15_demo_reinit/pending_order_plan/pending_order_plan.json")
    attempt2 = _read_json("reports/phase_reports/phase15_bv/apply_attempt_2.json")

    assert _sha256(".runtime_acceptance_phase15_demo_reinit/persistent_ledger/state.json") == CURRENT_HASH
    assert report["current_integrity"]["current_hash"] == f"sha256:{CURRENT_HASH}"
    assert current["current_version"] == "phase15bv_current_v1"
    assert current["positions"][0]["quantity"] == 100.0
    assert current["cash_delta"] == 10000.0
    assert current["market_value"] == 470000.0
    assert current["positions"][0]["execution_price"] == 100.0
    assert current["positions"][0]["valuation_price"] == 4700.0
    assert current["production_equivalent"] is False
    assert pending["state"] == "CONSUMED"
    assert pending["consume"]["consumed"] is True
    assert attempt2["status"] == "NOOP_ALREADY_APPLIED"
    assert attempt2["idempotent"] is True


def test_phase15bw_ledger_dedup_and_demo_only_flags_remain() -> None:
    base = ".runtime_acceptance_phase15_demo_reinit/persistent_ledger"
    rows = []
    for name in ("orders", "executions", "positions", "cash", "events"):
        file_rows = _read_jsonl(f"{base}/{name}.jsonl")
        assert len(file_rows) == 1
        rows.extend(file_rows)

    dedup_keys = [row["dedup_key"] for row in rows]
    assert len(dedup_keys) == len(set(dedup_keys))
    assert all(row["production_equivalent"] is False for row in rows)
    assert any(row.get("execution_equivalent") is True for row in rows)
    assert _read_jsonl(f"{base}/executions.jsonl")[0]["demo_only"] is True


def test_phase15bw_existing_runtime_hashes_unchanged() -> None:
    protected = (
        ".runtime/pending_order_plan/pending_order_plan.json",
        ".runtime/runtime_state/safety/latest_safety_decision.json",
        ".runtime/persistent_ledger/state.json",
        ".runtime/runtime_state/current_state.json",
    )
    before = _snapshot_runtime_paths(protected)
    report = _read_json("reports/phase_reports/phase15_bw_runtime_end_to_end_daily_system_test_review.json")

    assert report["broker_write_performed"] is False
    assert report["runtime_mutation_performed"] is False
    assert _snapshot_runtime_paths(protected) == before


def _snapshot_runtime_paths(paths: tuple[str, ...]) -> dict[str, dict[str, object]]:
    snapshot: dict[str, dict[str, object]] = {}
    for relative in paths:
        path = ROOT / relative
        if not path.exists():
            snapshot[relative] = {"exists": False, "sha256": None, "size": None}
            continue
        data = path.read_bytes()
        snapshot[relative] = {
            "exists": True,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        }
    return snapshot
