from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ai_fund_lab_v2.ai_lifecycle.as_update_rollback_closure import GENERATION_A_ID, run_phase19_as
from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation


ROOT = Path(__file__).resolve().parents[2]
A_MANIFEST = ROOT / ".runtime/ai_lifecycle/generations/phase19_aq_accepted_generation_641e6e313543f013/accepted_generation_manifest.json"


def test_phase19_as_update_to_b_and_rollback_to_a_in_temp_runtime(tmp_path: Path) -> None:
    runtime = _runtime_with_generation_a(tmp_path)

    result = run_phase19_as(repo_root=ROOT, runtime_root=runtime, evidence_dir=tmp_path / "evidence")

    assert result.generation_a_pre_transition_snapshot["status"] == "PASS"
    assert result.generation_b_fixture_or_artifact_review["status"] == "PASS"
    assert result.generation_b_fixture_or_artifact_review["test_only_identity"] is True
    assert result.update_prepared_transaction["previous_generation_id"] == GENERATION_A_ID
    assert result.update_staged_pointer["normal_runtime_resolver_remains_a"] is True
    assert result.generation_b_smoke_verification["status"] == "PASS"
    assert result.update_committed_pointer["transaction_state"] == "COMMITTED"
    assert result.runtime_reload_b_validation["status"] == "PASS"
    assert result.rollback_decision["decision"] == "ROLLBACK_APPROVED"
    assert result.rollback_committed_pointer["transaction_state"] == "ROLLED_BACK"
    assert result.runtime_reload_a_validation["status"] == "PASS"
    assert result.final_judgment["status"] == "PASS"
    assert resolve_accepted_generation(runtime).generation_id == GENERATION_A_ID


def test_phase19_as_history_cleanup_and_failure_injection_pass(tmp_path: Path) -> None:
    runtime = _runtime_with_generation_a(tmp_path)

    result = run_phase19_as(repo_root=ROOT, runtime_root=runtime, evidence_dir=tmp_path / "evidence")

    assert result.authority_history_append_only_validation["status"] == "PASS"
    assert result.transaction_history_validation["status"] == "PASS"
    assert result.staged_and_transaction_cleanup_validation["status"] == "PASS"
    assert result.staged_and_transaction_cleanup_validation["staged_pointer_payload"]["active_authority_candidate"] is False
    assert result.failure_injection_results["status"] == "PASS"
    assert result.failure_injection_results["items"]["F2_STAGED_after_crash"]["b_normal_runtime_authority"] is False
    assert result.failure_injection_results["items"]["F4_commit_pointer_write_interruption"]["partial_authority"] is False


def test_phase19_as_contract_consistency_and_non_mutation(tmp_path: Path) -> None:
    runtime = _runtime_with_generation_a(tmp_path)
    _write_json(runtime / "persistent_ledger/state.json", {"cash": 1000000, "positions": []})
    _write_json(runtime / "pending_order_plan/pending_order_plan.json", {"state": "CONSUMED", "items": []})
    _write_json(runtime / "runtime_state/current_state.json", {"state": "CURRENT_STATE_LOADED"})

    result = run_phase19_as(repo_root=ROOT, runtime_root=runtime, evidence_dir=tmp_path / "evidence")

    assert result.bootstrap_update_contract_consistency["status"] == "PASS"
    assert result.runtime_boundary_validation["status"] == "PASS"
    assert result.trading_state_non_mutation["status"] == "PASS"
    assert result.trading_state_non_mutation["broker_write"] == 0
    assert result.trading_state_non_mutation["buy_restart"] == 0


def _runtime_with_generation_a(tmp_path: Path) -> Path:
    runtime = tmp_path / ".runtime"
    manifest = json.loads(A_MANIFEST.read_text(encoding="utf-8"))
    pointer = {
        "schema_version": "phase19_ar_runtime_pointer.v1",
        "transaction_state": "COMMITTED",
        "transaction_id": "test-a",
        "accepted_generation_id": manifest["generation_id"],
        "bundle_manifest_path": str(A_MANIFEST),
        "aggregate_hash": manifest["aggregate_hash"],
        "manifest_hash": manifest["manifest_hash"],
        "accepted_at": manifest["accepted_at"],
        "effective_from": manifest["effective_from"],
        "previous_generation": None,
        "authority_decision": "COMMITTED Accepted Generation pointer only",
        "created_at": "2026-07-21T00:00:00+09:00",
    }
    _write_json(runtime / "runtime_state/accepted_buy_ai_bundle.json", pointer)
    history = {
        "event_type": "ACCEPTED_GENERATION_CREATED",
        "generation_id": manifest["generation_id"],
        "aggregate_hash": manifest["aggregate_hash"],
        "event_hash": hashlib.sha256(manifest["aggregate_hash"].encode("utf-8")).hexdigest(),
    }
    path = runtime / "ai_lifecycle/authority_history/accepted_generation_history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, sort_keys=True) + "\n", encoding="utf-8")
    return runtime


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
