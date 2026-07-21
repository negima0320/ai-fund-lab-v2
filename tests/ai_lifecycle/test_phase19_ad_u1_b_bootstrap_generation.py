from __future__ import annotations

from pathlib import Path

import pytest

from ai_fund_lab_v2.ai_lifecycle.bootstrap_generation import (
    REUSE_BLOCKED,
    REUSE_ELIGIBLE,
    build_bootstrap_generation_candidate,
    build_human_review_artifact,
    evaluate_component_reuse,
    materialize_accepted_generation,
    validate_bootstrap_generation_manifest,
)


def test_bootstrap_candidate_requires_candidate_and_opportunity_membership(tmp_path: Path) -> None:
    candidate = _component(tmp_path, "candidate")
    opportunity = _component(tmp_path, "opportunity")
    candidate_reuse = _reuse(tmp_path, candidate, "candidate")
    opportunity_reuse = _reuse(tmp_path, opportunity, "opportunity")

    manifest = _candidate_manifest(candidate, opportunity, candidate_reuse, opportunity_reuse)

    validation = validate_bootstrap_generation_manifest(manifest)
    assert validation["overall_result"] == "PASS"
    assert manifest["authority_decision"] == "REVIEW_REQUIRED"
    assert manifest["opportunity_member"]["candidate_member_ref"] == manifest["candidate_member"]["member_id"]
    assert manifest["runtime_pointer_written"] is False


def test_human_review_approve_materializes_accepted_decision_without_committed_pointer(tmp_path: Path) -> None:
    candidate = _component(tmp_path, "candidate")
    opportunity = _component(tmp_path, "opportunity")
    manifest = _candidate_manifest(candidate, opportunity, _reuse(tmp_path, candidate, "candidate"), _reuse(tmp_path, opportunity, "opportunity"))
    review = build_human_review_artifact(
        generation_manifest=manifest,
        reviewer="human-reviewer@example.test",
        decision="APPROVE",
        decision_reason="bootstrap reuse evidence reviewed",
    )

    result = materialize_accepted_generation(generation_candidate=manifest, human_review=review)

    assert result.human_review_validation["overall_result"] == "PASS"
    assert result.accepted_decision is not None
    assert result.accepted_manifest is not None
    assert result.accepted_manifest["authority_decision"] == "ACCEPTED"
    assert result.accepted_manifest["runtime_transition_state"] == "NOT_COMMITTED"
    assert result.accepted_manifest["runtime_pointer_written"] is False


def test_missing_human_review_does_not_materialize_accepted_generation(tmp_path: Path) -> None:
    candidate = _component(tmp_path, "candidate")
    opportunity = _component(tmp_path, "opportunity")
    manifest = _candidate_manifest(candidate, opportunity, _reuse(tmp_path, candidate, "candidate"), _reuse(tmp_path, opportunity, "opportunity"))

    result = materialize_accepted_generation(generation_candidate=manifest, human_review=None)

    assert result.accepted_manifest is None
    assert result.accepted_decision is None
    assert "human_review_missing" in result.human_review_validation["errors"]


def test_human_review_hash_mismatch_rejects_acceptance(tmp_path: Path) -> None:
    candidate = _component(tmp_path, "candidate")
    opportunity = _component(tmp_path, "opportunity")
    manifest = _candidate_manifest(candidate, opportunity, _reuse(tmp_path, candidate, "candidate"), _reuse(tmp_path, opportunity, "opportunity"))
    review = build_human_review_artifact(
        generation_manifest=manifest,
        reviewer="human-reviewer@example.test",
        decision="APPROVE",
        decision_reason="bootstrap reuse evidence reviewed",
    )
    review["reviewed_hash"] = "not-the-generation-hash"

    result = materialize_accepted_generation(generation_candidate=manifest, human_review=review)

    assert result.accepted_manifest is None
    assert "human_review_hash_mismatch" in result.human_review_validation["errors"]


def test_blocked_candidate_or_opportunity_reuse_prevents_generation(tmp_path: Path) -> None:
    candidate = _component(tmp_path, "candidate")
    opportunity = _component(tmp_path, "opportunity")
    blocked_candidate = _reuse(tmp_path, candidate, "candidate")
    blocked_candidate["reuse_decision"] = REUSE_BLOCKED

    with pytest.raises(Exception, match="candidate reuse is blocked"):
        _candidate_manifest(candidate, opportunity, blocked_candidate, _reuse(tmp_path, opportunity, "opportunity"))

    blocked_opportunity = _reuse(tmp_path, opportunity, "opportunity")
    blocked_opportunity["reuse_decision"] = REUSE_BLOCKED
    with pytest.raises(Exception, match="opportunity reuse is blocked"):
        _candidate_manifest(candidate, opportunity, _reuse(tmp_path, candidate, "candidate"), blocked_opportunity)


def test_schema_hash_mismatch_blocks_reuse(tmp_path: Path) -> None:
    component = _component(tmp_path, "candidate")

    reuse = evaluate_component_reuse(
        component_type="candidate",
        component=component,
        repo_root=tmp_path,
        expected_schema_hashes={"MODEL": "different-schema"},
        validation_applicability={"status": "PASS"},
        freshness={"status": "PASS"},
        policy_version="bootstrap_policy_v1",
    )

    assert reuse["reuse_decision"] == REUSE_BLOCKED
    assert "schema_hash_mismatch:MODEL" in reuse["reuse_reason"]


def _component(tmp_path: Path, component_type: str) -> dict:
    members = []
    for role in ("MODEL", "FEATURE_SCHEMA", "TRAINING_METADATA", "TRAINING_DATA_LINEAGE", "VALIDATION_EVIDENCE"):
        path = tmp_path / component_type / f"{role.lower()}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'{{"role":"{role}","component":"{component_type}"}}\n', encoding="utf-8")
        members.append(
            {
                "logical_artifact_id": f"ai.{component_type}.accepted_set.{role.lower()}",
                "member_role": role,
                "physical_path": str(path.relative_to(tmp_path)),
                "content_hash": __import__("hashlib").sha256(path.read_bytes()).hexdigest(),
                "schema_hash": f"{role.lower()}-schema",
            }
        )
    return {
        "artifact_set_id": f"ai.{component_type}.accepted_set",
        "artifact_set_hash": f"{component_type}-set-hash",
        "source_lineage_ref": f"lineage/{component_type}.json",
        "training_cutoff": "2026-01-31",
        "members": members,
        "schema_hashes": {member["logical_artifact_id"]: member["schema_hash"] for member in members},
    }


def _reuse(tmp_path: Path, component: dict, component_type: str) -> dict:
    reuse = evaluate_component_reuse(
        component_type=component_type,
        component=component,
        repo_root=tmp_path,
        validation_applicability={"status": "PASS"},
        freshness={"status": "PASS"},
        policy_version="bootstrap_policy_v1",
    )
    assert reuse["reuse_decision"] == REUSE_ELIGIBLE
    return reuse


def _candidate_manifest(candidate: dict, opportunity: dict, candidate_reuse: dict, opportunity_reuse: dict) -> dict:
    return build_bootstrap_generation_candidate(
        generation_id="bootstrap-generation-test",
        candidate_component=candidate,
        opportunity_component=opportunity,
        candidate_reuse=candidate_reuse,
        opportunity_reuse=opportunity_reuse,
        calibration_member={"artifact_path": "calibration.json", "content_hash": "calibration-hash"},
        validation={"validation_applicability": {"status": "PASS"}},
        runtime_baseline={"baseline_hash": "baseline-hash"},
        freshness={"status": "PASS", "model_training_cutoff": "2026-01-31"},
        dataset_lineage={
            "dataset_version": "dataset-v1",
            "training_cutoff": "2026-01-31",
            "calibration_cutoff": "2026-02-28",
        },
        split={"calibration": {"end": "2026-02-28"}},
        source_commit="test-commit",
        policy_versions={"bootstrap": "bootstrap_policy_v1"},
        effective_from="2026-03-01",
        rollback_reference={"previous_generation": None},
        bootstrap_reason="unit test",
    )
