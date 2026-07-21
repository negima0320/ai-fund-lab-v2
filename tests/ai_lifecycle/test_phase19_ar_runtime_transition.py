from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.ai_lifecycle.ar_runtime_transition import (
    ACCEPTED_MANIFEST,
    evaluate_threshold_policy,
    run_phase19_ar,
)
from ai_fund_lab_v2.runtime_v2.accepted_generation_consumer_adapter import validate_manifest_compatibility
from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation


ROOT = Path(__file__).resolve().parents[2]


def test_phase19_ar_transition_commits_aq_accepted_generation_in_temp_runtime(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    evidence_dir = tmp_path / "evidence"

    result = run_phase19_ar(
        repo_root=ROOT,
        runtime_root=runtime_root,
        evidence_dir=evidence_dir,
        write_runtime_pointer=True,
    )

    assert result.prepared_transaction["transaction_state"] == "PREPARED"
    assert result.staged_pointer["transaction_state"] == "STAGED"
    assert result.smoke_verification["status"] == "PASS"
    assert result.committed_pointer["transaction_state"] == "COMMITTED"
    assert result.runtime_reload_validation["status"] == "PASS"
    assert result.rollback_validation["status"] == "PASS"
    assert result.final_judgment["status"] == "PASS"
    assert (runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json").is_file()
    assert (runtime_root / "runtime_state" / "staged_accepted_buy_ai_bundle.json").is_file()
    assert (evidence_dir / "final_judgment.json").is_file()


def test_phase19_ar_runtime_resolver_reads_formal_aq_manifest(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    result = run_phase19_ar(repo_root=ROOT, runtime_root=runtime_root, evidence_dir=tmp_path / "evidence")

    resolution = resolve_accepted_generation(runtime_root)

    assert resolution.is_resolved
    assert resolution.generation_id == result.prepared_transaction["accepted_generation_id"]
    assert resolution.aggregate_hash == result.prepared_transaction["aggregate_hash"]
    assert resolution.candidate_member is not None
    assert resolution.opportunity_member is not None
    assert resolution.artifact_paths()["candidate_model"].is_file()
    assert resolution.artifact_paths()["opportunity_model"].is_file()


def test_phase19_ar_consumer_adapter_accepts_formal_accepted_manifest() -> None:
    manifest = json.loads((ROOT / ACCEPTED_MANIFEST).read_text(encoding="utf-8"))

    result = validate_manifest_compatibility(manifest, repo_root=ROOT, load_pickles=False)

    assert result.status == "PASS"
    assert result.block_buy is False
    assert result.block_sell is False


def test_phase19_ar_threshold_policy_matches_human_decision() -> None:
    structural = evaluate_threshold_policy("Hash mismatch")
    drift = evaluate_threshold_policy("Distribution Drift")

    assert structural["action"] == "BUY_ONLY_BLOCK"
    assert structural["block_buy"] is True
    assert structural["block_sell"] is False
    assert drift["action"] == "REVIEW_REQUIRED"
    assert drift["block_buy"] is False
    assert drift["block_sell"] is False


def test_phase19_ar_non_mutation_and_bootstrap_rollback(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    result = run_phase19_ar(repo_root=ROOT, runtime_root=runtime_root, evidence_dir=tmp_path / "evidence")

    assert result.rollback_validation["rollback_executed"] is False
    assert result.rollback_validation["rollback_pointer_mutation"] is False
    assert result.rollback_validation["rollback_state"] == "ROLLBACK_NOT_AVAILABLE_BOOTSTRAP_NO_PREVIOUS_GENERATION"
    assert result.non_mutation["broker_write"] == 0
    assert result.non_mutation["buy_restart"] == 0
    assert result.non_mutation["sell_state_mutated"] is False
