from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.ai_lifecycle.aq_authority_decision import run_phase19_aq


ROOT = Path(__file__).resolve().parents[2]


def test_phase19_aq_approves_and_materializes_without_runtime_pointer(tmp_path: Path) -> None:
    result = run_phase19_aq(repo_root=ROOT, runtime_output_root=tmp_path / "ai_lifecycle")

    assert result.accepted_decision["decision_status"] == "APPROVE"
    assert result.accepted_decision["runtime_transition_authorized"] is False
    assert result.accepted_decision["buy_restart_authorized"] is False
    assert result.accepted_generation_manifest is not None
    assert result.accepted_generation_manifest["accepted"] is True
    assert result.accepted_generation_manifest["runtime_eligibility"] is True
    assert result.authority_history_append_result["append_status"] == "APPENDED"
    assert result.final_judgment["final_judgment"] == [
        "PHASE19_AQ_ACCEPTED_GENERATION_COMPLETE",
        "PHASE19_AR_BLOCKED_PENDING_THRESHOLD_POLICY",
    ]
    assert not (tmp_path / "ai_lifecycle" / "runtime_state" / "accepted_buy_ai_bundle.json").exists()


def test_phase19_aq_idempotent_same_materialization(tmp_path: Path) -> None:
    first = run_phase19_aq(repo_root=ROOT, runtime_output_root=tmp_path / "ai_lifecycle")
    second = run_phase19_aq(repo_root=ROOT, runtime_output_root=tmp_path / "ai_lifecycle")

    assert first.accepted_generation_manifest is not None
    assert second.accepted_generation_manifest is not None
    assert first.accepted_generation_manifest["manifest_hash"] == second.accepted_generation_manifest["manifest_hash"]
    assert second.immutability_validation["accepted_generation_manifest"]["write_status"] == "IDEMPOTENT_ALREADY_PRESENT"
    assert second.authority_history_append_result["append_status"] == "IDEMPOTENT_ALREADY_PRESENT"


def test_phase19_aq_reviews_threshold_as_runtime_transition_blocker(tmp_path: Path) -> None:
    result = run_phase19_aq(repo_root=ROOT, runtime_output_root=tmp_path / "ai_lifecycle")

    assert result.baseline_threshold_policy_review["accepted_generation_impact"] == "ALLOWED"
    assert (
        result.baseline_threshold_policy_review["runtime_transition_impact"]
        == "RUNTIME_TRANSITION_BLOCKED_PENDING_THRESHOLD_POLICY"
    )
    assert result.baseline_threshold_policy_review["numeric_thresholds_invented"] is False
