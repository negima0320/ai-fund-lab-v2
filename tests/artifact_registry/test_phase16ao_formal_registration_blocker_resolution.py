from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.artifact_registry.formal_registration_preflight import (
    FormalRegistrationPreflight,
    MemberSpec,
    SetSpec,
    run_formal_registration_preflight,
    validate_formal_evidence,
)


def test_phase16ao_preflight_generates_real_preparation_outputs(tmp_path: Path) -> None:
    formal_event_log = Path(".runtime/artifact_registry/events/registry_events.jsonl").read_bytes()
    current = Path(".runtime/runtime_state/current_state.json").read_bytes()
    ledger = Path(".runtime/persistent_ledger/state.json").read_bytes()
    pending = Path(".runtime/pending_order_plan/pending_order_plan.json").read_bytes()

    result = run_formal_registration_preflight(output_root=tmp_path / "prep")

    assert result["formal_registration_ready"] == "BLOCKED"
    assert result["protected_hashes_unchanged"] is True
    assert result["formal_registry_changed"] is False
    assert set(result["set_results"]) == {"candidate", "opportunity", "pm", "capital_allocation", "feature_schema"}
    assert result["set_results"]["opportunity"]["artifact_candidate_ready"] == "READY"
    assert result["set_results"]["opportunity"]["approval_ready"] == "REVIEW_REQUIRED"
    assert result["set_results"]["opportunity"]["regression_ready"] == "READY"
    assert "Phase5-E fallback remains active" not in " ".join(result["set_results"]["opportunity"]["blockers"])
    assert result["set_results"]["candidate"]["formal_registration_ready"] == "BLOCKED"
    assert result["set_results"]["candidate"]["regression_ready"] == "READY"
    assert result["set_results"]["pm"]["regression_ready"] == "READY"
    assert result["set_results"]["capital_allocation"]["regression_ready"] == "READY"
    assert (tmp_path / "prep/formal_copy_plan.json").is_file()
    assert (tmp_path / "prep/regression/candidate_regression.json").is_file()
    assert (tmp_path / "prep/candidate/row_count_resolution.json").is_file()
    assert (tmp_path / "prep/regression/pm_semantic_regression.json").is_file()
    assert (tmp_path / "prep/regression/capital_allocation_semantic_regression.json").is_file()
    assert (tmp_path / "prep/approval_templates/opportunity_approval_templates.json").is_file()

    copy_plan = json.loads((tmp_path / "prep/formal_copy_plan.json").read_text())
    assert all(entry["overwrite"] is False for entry in copy_plan["entries"])
    assert all("phase16_formal_registration_dry_run" not in entry["source_path"] for entry in copy_plan["entries"])
    assert any(entry["source_path"].endswith("reports/opportunity_ai/phase5p/models/opportunity_model.pkl") for entry in copy_plan["entries"])
    assert any(entry["source_path"].endswith("reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json") for entry in copy_plan["entries"])
    assert all(entry["copy_status"] == "READY_TO_COPY" for entry in copy_plan["entries"])
    assert all("phase" not in entry["destination_path"].lower() for entry in copy_plan["entries"])

    row_count = json.loads((tmp_path / "prep/candidate/row_count_resolution.json").read_text())
    assert row_count["classification"] == "BUG"
    assert row_count["dataset_matches_training_summary"] is True
    assert row_count["manifest_matches_dataset"] is False

    pm_regression = json.loads((tmp_path / "prep/regression/pm_semantic_regression.json").read_text())
    capital_regression = json.loads((tmp_path / "prep/regression/capital_allocation_semantic_regression.json").read_text())
    assert pm_regression["overall_result"] == "READY"
    assert pm_regression["exit"]["exit_count"] == 1
    assert pm_regression["hold"]["hold_count"] == 1
    assert capital_regression["overall_result"] == "READY"
    assert capital_regression["submit_guard"]["guard_decision"] == "PASS"

    assert Path(".runtime/artifact_registry/events/registry_events.jsonl").read_bytes() == formal_event_log
    assert Path(".runtime/runtime_state/current_state.json").read_bytes() == current
    assert Path(".runtime/persistent_ledger/state.json").read_bytes() == ledger
    assert Path(".runtime/pending_order_plan/pending_order_plan.json").read_bytes() == pending


def test_synthetic_evidence_reject_mode() -> None:
    result = validate_formal_evidence(
        {
            "schema_version": "artifact_review_approval.v1",
            "reviewer_id": "dry-run-reviewer",
            "decision": "REVIEW_REQUIRED",
            "placeholder": True,
        },
        evidence_ref="reports/phase16_formal_registration_dry_run/sets/x/approval.json",
    )
    assert result["overall_result"] == "FAIL"
    assert result["failure_class"] == "HALT"
    assert len(result["errors"]) >= 3

    regression = validate_formal_evidence({"schema_version": "artifact_regression_evidence.v1", "result": "PASS"})
    assert regression["overall_result"] == "FAIL"
    assert any("execution_refs" in error for error in regression["errors"])


def test_preflight_blocks_wrong_opportunity_and_destination_issues(tmp_path: Path) -> None:
    source = tmp_path / "opportunity_artifact.json"
    source.write_text("{}\n", encoding="utf-8")
    spec = SetSpec(
        key="opportunity",
        artifact_set_id="ai.opportunity.accepted_set",
        artifact_set_type="OPPORTUNITY_AI_SET",
        component="Opportunity AI",
        members=(
            MemberSpec("MODEL", source, Path(".runtime/artifacts/ai/opportunity/model/formal/sha256-{hash}/model.pkl")),
            MemberSpec("METRICS", source, Path(".runtime/artifacts/ai/opportunity/metrics/formal/sha256-{hash}/metrics.json")),
        ),
    )
    preflight = FormalRegistrationPreflight(output_root=tmp_path / "out")
    copy_plan: dict = {"entries": []}
    result = preflight._run_set(spec, copy_plan)
    assert result["formal_registration_ready"] == "BLOCKED"
    assert any("wrong opportunity model" in item or "wrong opportunity metrics" in item for item in result["blockers"])

    phase_dest = MemberSpec("MODEL", source, Path(".runtime/artifacts/ai/candidate/model/phase4bf/sha256-{hash}/model.pkl"))
    entry = preflight._copy_plan_entry(
        SetSpec("candidate", "ai.candidate.accepted_set", "CANDIDATE_AI_SET", "Candidate", (phase_dest,)),
        phase_dest,
    )
    assert entry["copy_status"] == "BLOCKED"
    assert entry["phase_number_independent_destination"] is False


def test_preflight_blocks_missing_source_and_collision(tmp_path: Path) -> None:
    existing = tmp_path / "existing.json"
    existing.write_text("{}\n", encoding="utf-8")
    source = tmp_path / "source.json"
    source.write_text("{}\n", encoding="utf-8")
    rel_dest = existing.relative_to(Path.cwd()) if str(existing).startswith(str(Path.cwd())) else Path(str(existing))
    preflight = FormalRegistrationPreflight(output_root=tmp_path / "out")
    spec = SetSpec("candidate", "ai.candidate.accepted_set", "CANDIDATE_AI_SET", "Candidate", ())

    missing_entry = preflight._copy_plan_entry(spec, MemberSpec("MODEL", tmp_path / "missing.pkl", Path(".runtime/artifacts/ai/candidate/model/formal/sha256-{hash}/model.pkl")))
    assert missing_entry["copy_status"] == "SOURCE_MISSING"

    collision_entry = preflight._copy_plan_entry(spec, MemberSpec("MODEL", source, existing))
    assert collision_entry["copy_status"] == "READY_TO_COPY"
    assert collision_entry["collision_status"] == "EXISTING_IDENTICAL"

    different_existing = tmp_path / "different_existing.json"
    different_existing.write_text('{"different": true}\n', encoding="utf-8")
    collision_entry = preflight._copy_plan_entry(spec, MemberSpec("MODEL", source, different_existing))
    assert collision_entry["copy_status"] == "COLLISION"
