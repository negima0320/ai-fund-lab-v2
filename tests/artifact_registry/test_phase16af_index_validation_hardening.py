from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.artifact_registry.full_log_validator import FullEventLogValidator
from ai_fund_lab_v2.artifact_registry.index_builder import (
    MaterializedRegistryIndexBuilder,
    RegistryIndexDurabilityError,
    RegistryIndexValidationError,
    index_hash,
    index_semantic_issues,
)
from ai_fund_lab_v2.artifact_registry.inventory import sha256_file


def _write_log(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n" for event in events), encoding="utf-8")


def _artifact(tmp_path: Path, name: str) -> tuple[Path, str]:
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps({"name": name}, sort_keys=True) + "\n", encoding="utf-8")
    return path, sha256_file(path)


def _event(tmp_path: Path, *, event_id: str, logical_id: str = "artifact.test.accepted", status: str = "DRAFT", artifact_name: str = "artifact") -> dict:
    path, digest = _artifact(tmp_path, artifact_name)
    return {
        "event_id": event_id,
        "event_type": "ARTIFACT_DISCOVERED" if status == "DRAFT" else "ARTIFACT_VALIDATED",
        "event_schema_version": "artifact_registry_event.v1",
        "event_created_at": "2026-07-13T00:00:00+00:00",
        "actor_type": "INVENTORY_TOOL" if status == "DRAFT" else "VALIDATION_TOOL",
        "actor_id": "phase16af-test",
        "authority_ref": "test-authority",
        "logical_artifact_id": logical_id,
        "artifact_instance_id": f"{logical_id}@sha256-{digest[:16]}",
        "artifact_type": "TEST_ARTIFACT",
        "component": "Artifact Registry Test",
        "artifact_version": "v1",
        "previous_status": None if status == "DRAFT" else "DRAFT",
        "new_status": status,
        "runtime_use_eligible": False,
        "physical_path": str(path),
        "content_hash": digest,
        "schema_version": None,
        "schema_hash": None,
        "artifact_set_id": None,
        "business_date": None,
        "feature_date": None,
        "as_of": None,
        "producer": "test",
        "producer_version": "v1",
        "consumer_compatibility": [],
        "source_refs": [],
        "source_hashes": [],
        "point_in_time_status": "NOT_APPLICABLE",
        "retention_class": "test",
        "path_classification": "TEST",
        "migration_status": status,
        "review_ref": None,
        "regression_ref": None,
        "acceptance_report_ref": None,
        "reason": None,
        "supersedes_event_id": None,
        "previous_physical_path": None,
        "new_physical_path": None,
    }


def _validated(draft: dict, *, event_id: str) -> dict:
    event = dict(draft)
    event.update({"event_id": event_id, "event_type": "ARTIFACT_VALIDATED", "previous_status": "DRAFT", "new_status": "VALIDATED", "actor_type": "VALIDATION_TOOL", "migration_status": "VALIDATED"})
    return event


def _write_json(path: Path, payload: object) -> str:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return str(path)


def _accepted(tmp_path: Path, validated: dict, *, event_id: str = "event-accepted") -> dict:
    event = dict(validated)
    event.update(
        {
            "event_id": event_id,
            "event_type": "ARTIFACT_ACCEPTED",
            "previous_status": "VALIDATED",
            "new_status": "ACCEPTED",
            "actor_type": "HUMAN",
            "runtime_use_eligible": True,
            "consumer_compatibility": [{"consumer": "Runtime", "compatible": True, "reason": None}],
            "point_in_time_status": "PASS",
        }
    )
    subject = event["artifact_instance_id"]
    report = {
        "schema_version": "artifact_acceptance_report.v1",
        "acceptance_report_id": "report",
        "artifact_or_set_ref": subject,
        "reviewed_artifact_hashes": {subject: event["content_hash"]},
        "reviewed_schema_hashes": {subject: event["schema_hash"]},
        "reviewed_source_refs": [],
        "human_reviewer": "human",
        "architecture_reviewer": "arch",
        "regression_reviewer": "reg",
        "release_approver": "release",
        "review_started_at": "2026-07-13T00:00:00+00:00",
        "review_completed_at": "2026-07-13T01:00:00+00:00",
        "decision": "ACCEPT",
        "acceptance_criteria_results": {"identity": "PASS"},
        "regression_results": ["PASS"],
        "known_limitations": [],
        "risk_classification": "LOW",
        "rollback_target": None,
        "replacement_target": None,
        "git_commit": None,
        "runtime_version": None,
        "feature_schema_version": None,
        "canonical_data_manifest_ref": None,
        "model_freeze_manifest_ref": None,
        "approval_signatures": ["sig"],
        "notes": None,
    }
    regression = {
        "schema_version": "artifact_regression_evidence.v1",
        "regression_evidence_id": "regression",
        "artifact_or_set_ref": subject,
        "profile": "CANDIDATE",
        "test_scope": "unit",
        "test_command": None,
        "test_environment": "test",
        "before_refs": [],
        "after_refs": [],
        "semantic_comparison": "PASS",
        "hash_comparison": "PASS",
        "schema_comparison": "PASS",
        "candidate_decision_parity": "PASS",
        "opportunity_decision_parity": "NOT_APPLICABLE",
        "pm_decision_parity": "NOT_APPLICABLE",
        "capital_allocation_parity": "NOT_APPLICABLE",
        "planning_parity": "PASS",
        "pending_parity": "PASS",
        "submit_guard_parity": "PASS",
        "current_unchanged": True,
        "ledger_unchanged": True,
        "pending_unchanged": True,
        "runtime_state_unchanged": True,
        "result": "PASS",
        "failures": [],
        "timestamp_only_differences": [],
        "reviewer": "reg",
    }
    approvals = [
        {
            "schema_version": "artifact_review_approval.v1",
            "approval_id": f"approval-{approval}",
            "approval_type": approval,
            "subject_ref": subject,
            "reviewer_id": approval.lower(),
            "reviewer_role": approval,
            "decision": "APPROVED",
            "approved_at": "2026-07-13T02:00:00+00:00",
            "evidence_refs": ["report"],
            "conditions": [],
            "expires_at": None,
            "supersedes_approval_id": None,
        }
        for approval in ("HUMAN_REVIEW", "ARCHITECTURE_ACCEPTANCE", "REGRESSION_ACCEPTANCE", "RELEASE_APPROVAL")
    ]
    event["acceptance_report_ref"] = _write_json(tmp_path / "report.json", report)
    event["regression_ref"] = _write_json(tmp_path / "regression.json", regression)
    event["review_ref"] = _write_json(tmp_path / "approvals.json", approvals)
    return event


def _builder(tmp_path: Path) -> tuple[MaterializedRegistryIndexBuilder, Path]:
    root = tmp_path / "registry"
    log = root / "events/registry_events.jsonl"
    return MaterializedRegistryIndexBuilder(registry_root=root, event_log_path=log, repo_root=Path.cwd(), lock_timeout_seconds=0.05), log


def test_warning_semantics_and_builder_rejects_pass_with_warnings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    _write_log(log, [])
    assert FullEventLogValidator(event_log_path=log, repo_root=Path.cwd()).validate()["overall_result"] == "PASS"

    validator = FullEventLogValidator(event_log_path=log, repo_root=Path.cwd())
    result = validator._result([], [], ["warning only"], event_count=0, last_event_id=None, event_log_hash="0" * 64)
    assert result["overall_result"] == "PASS_WITH_WARNINGS"
    assert result["failure_class"] == "NONE"

    builder, build_log = _builder(tmp_path)
    _write_log(build_log, [])

    def warning_validate(self: FullEventLogValidator, *, include_events: bool = False) -> dict:
        return {"overall_result": "PASS_WITH_WARNINGS", "failure_class": "NONE", "event_count": 0, "last_event_id": None, "event_log_hash": "0" * 64, "events": []}

    monkeypatch.setattr(FullEventLogValidator, "validate", warning_validate)
    build = builder.build()
    assert build["overall_result"] == "FAIL"
    assert build["build_status"] == "FAILED"
    assert not builder.index_path.exists()


@pytest.mark.parametrize("field,value", [("event_log_hash", "1" * 64), ("event_count", 999), ("last_event_id", "wrong"), ("entry_count", 99)])
def test_stale_existing_index_metadata_classified_and_rebuilt(tmp_path: Path, field: str, value: object) -> None:
    builder, log = _builder(tmp_path)
    _write_log(log, [_event(tmp_path, event_id="event-a")])
    builder.build()
    index = json.loads(builder.index_path.read_text(encoding="utf-8"))
    index[field] = value
    index["index_hash"] = index_hash(index)
    builder.index_path.write_text(json.dumps(index, sort_keys=True) + "\n", encoding="utf-8")

    result = builder.build()
    assert result["existing_index_status"] == "STALE"
    assert field in result["stale_fields"]
    assert result["rebuild_reason"] == "STALE_DERIVED_INDEX"
    assert result["index_replaced"] is True


def test_index_hash_mismatch_classified_corrupt_and_rebuilt(tmp_path: Path) -> None:
    builder, log = _builder(tmp_path)
    _write_log(log, [_event(tmp_path, event_id="event-a")])
    builder.build()
    index = json.loads(builder.index_path.read_text(encoding="utf-8"))
    index["index_hash"] = "0" * 64
    builder.index_path.write_text(json.dumps(index, sort_keys=True) + "\n", encoding="utf-8")

    result = builder.build()
    assert result["existing_index_status"] == "CORRUPT"
    assert result["rebuild_reason"] == "CORRUPT_DERIVED_INDEX"
    assert result["index_replaced"] is True


@pytest.mark.parametrize(
    "mutation",
    [
        lambda idx: idx.update({"entry_count": 99}),
        lambda idx: idx["entries"].__setitem__("wrong", {**next(iter(idx["entries"].values())), "logical_artifact_id": "different"}),
        lambda idx: idx.update({"event_count": 0, "last_event_id": "event-a"}),
        lambda idx: idx.update({"event_count": 1, "last_event_id": None}),
        lambda idx: next(iter(idx["entries"].values())).update({"current_status": "VALIDATED", "runtime_use_eligible": True}),
        lambda idx: next(iter(idx["entries"].values())).update({"current_status": "LEGACY", "runtime_use_eligible": True}),
        lambda idx: next(iter(idx["entries"].values())).update({"current_status": "ACCEPTED", "runtime_use_eligible": True, "active_artifact_instance_id": None}),
        lambda idx: idx.update({"index_hash": "0" * 64}),
    ],
)
def test_cross_field_invariant_rejects_invalid_index(tmp_path: Path, mutation) -> None:
    builder, log = _builder(tmp_path)
    draft = _event(tmp_path, event_id="event-a")
    validated = _validated(draft, event_id="event-b")
    accepted = _accepted(tmp_path, validated)
    _write_log(log, [draft, validated, accepted])
    builder.build()
    index = json.loads(builder.index_path.read_text(encoding="utf-8"))
    mutation(index)
    assert index_semantic_issues(index)
    with pytest.raises(RegistryIndexValidationError):
        builder._validate_index(index)


def test_accepted_artifact_projection(tmp_path: Path) -> None:
    builder, log = _builder(tmp_path)
    draft = _event(tmp_path, event_id="event-a")
    validated = _validated(draft, event_id="event-b")
    accepted = _accepted(tmp_path, validated, event_id="event-c")
    _write_log(log, [draft, validated, accepted])
    result = builder.build()
    index = json.loads(builder.index_path.read_text(encoding="utf-8"))
    entry = index["entries"][draft["logical_artifact_id"]]
    assert result["entry_count"] == 1
    assert entry["active_artifact_instance_id"] == draft["artifact_instance_id"]
    assert entry["runtime_use_eligible"] is True
    assert entry["accepted_event_id"] == "event-c"
    assert entry["accepted_at"] == accepted["event_created_at"]
    assert entry["accepted_by"] == accepted["authority_ref"]
    assert index["index_hash"] == index_hash(index)


def test_replace_failure_and_fsync_failure_preserve_old_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    builder, log = _builder(tmp_path)
    _write_log(log, [_event(tmp_path, event_id="event-a")])
    builder.build()
    before = builder.index_path.read_text(encoding="utf-8")
    index = json.loads(before)
    index["generated_at"] = "2099-01-01T00:00:00+00:00"

    import ai_fund_lab_v2.artifact_registry.index_builder as module

    def failing_replace(src: object, dst: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(module.os, "replace", failing_replace)
    with pytest.raises(OSError):
        builder._write_index_atomic(index)
    assert builder.index_path.read_text(encoding="utf-8") == before
    assert not list(builder.index_path.parent.glob("*.tmp"))

    monkeypatch.setattr(module.os, "replace", module.os.replace)

    def failing_fsync(fd: int) -> None:
        raise OSError("fsync failed")

    monkeypatch.setattr(module.os, "fsync", failing_fsync)
    with pytest.raises(OSError):
        builder._write_index_atomic(index)
    assert builder.index_path.read_text(encoding="utf-8") == before
    assert not list(builder.index_path.parent.glob("*.tmp"))


def test_parent_fsync_failure_reports_review_required_after_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    builder, log = _builder(tmp_path)
    _write_log(log, [_event(tmp_path, event_id="event-a")])
    builder.build()
    draft2 = _event(tmp_path, event_id="event-b", logical_id="artifact.test.b", artifact_name="b")
    _write_log(log, [_event(tmp_path, event_id="event-a"), draft2])

    import ai_fund_lab_v2.artifact_registry.index_builder as module

    calls = {"count": 0}
    original_fsync = module.os.fsync

    def failing_parent_fsync(fd: int) -> None:
        calls["count"] += 1
        if calls["count"] >= 2:
            raise OSError("parent fsync failed")
        original_fsync(fd)

    monkeypatch.setattr(module.os, "fsync", failing_parent_fsync)
    result = builder.build()
    assert result["overall_result"] == "REVIEW_REQUIRED"
    assert result["durability_status"] == "REVIEW_REQUIRED"
    assert result["index_replaced"] is True


def test_lock_release_on_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    builder, log = _builder(tmp_path)
    _write_log(log, [_event(tmp_path, event_id="event-a")])

    def boom(index: dict) -> None:
        raise RegistryIndexValidationError("boom")

    monkeypatch.setattr(builder, "_validate_index", boom)
    with pytest.raises(RegistryIndexValidationError):
        builder.build()
    monkeypatch.undo()
    assert builder.build()["overall_result"] == "PASS"
