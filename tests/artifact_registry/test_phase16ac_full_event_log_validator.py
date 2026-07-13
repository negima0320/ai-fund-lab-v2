from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ai_fund_lab_v2.artifact_registry.full_log_validator import (
    FullEventLogValidator,
    run_full_log_validation,
)
from ai_fund_lab_v2.artifact_registry.inventory import sha256_file


def _write_log(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [{key: value for key, value in event.items() if key != "_line_number"} for event in events]
    path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def _artifact(tmp_path: Path, name: str, payload: object | None = None) -> tuple[Path, str]:
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(payload if payload is not None else {"name": name}, sort_keys=True) + "\n", encoding="utf-8")
    return path, sha256_file(path)


def _event(
    tmp_path: Path,
    *,
    event_id: str,
    logical_id: str = "artifact.test.model",
    instance_id: str | None = None,
    event_type: str = "ARTIFACT_DISCOVERED",
    previous_status: str | None = None,
    new_status: str | None = "DRAFT",
    artifact_name: str = "artifact",
    content_hash: str | None = None,
    physical_path: str | None = None,
    runtime_use_eligible: bool = False,
    event_created_at: str = "2026-07-13T00:00:00+00:00",
    actor_type: str = "INVENTORY_TOOL",
    authority_ref: str | None = "test-authority",
) -> dict:
    artifact_path, digest = _artifact(tmp_path, artifact_name)
    digest = content_hash or digest
    instance = instance_id or f"{logical_id}@sha256-{digest[:16]}"
    return {
        "event_id": event_id,
        "event_type": event_type,
        "event_schema_version": "artifact_registry_event.v1",
        "event_created_at": event_created_at,
        "actor_type": actor_type,
        "actor_id": "phase16ac-test",
        "authority_ref": authority_ref,
        "logical_artifact_id": logical_id,
        "artifact_instance_id": instance,
        "artifact_type": "TEST_ARTIFACT",
        "component": "Artifact Registry Test",
        "artifact_version": "v1",
        "previous_status": previous_status,
        "new_status": new_status,
        "runtime_use_eligible": runtime_use_eligible,
        "physical_path": physical_path or str(artifact_path),
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
        "migration_status": "DRAFT",
        "review_ref": None,
        "regression_ref": None,
        "acceptance_report_ref": None,
        "reason": None,
        "supersedes_event_id": None,
        "previous_physical_path": None,
        "new_physical_path": None,
    }


def _validated_event(tmp_path: Path, draft: dict, *, event_id: str = "event-validated", **updates: object) -> dict:
    event = dict(draft)
    event.update(
        {
            "event_id": event_id,
            "event_type": "ARTIFACT_VALIDATED",
            "actor_type": "VALIDATION_TOOL",
            "previous_status": "DRAFT",
            "new_status": "VALIDATED",
            "migration_status": "VALIDATED",
        }
    )
    event.update(updates)
    return event


def _accepted_event(tmp_path: Path, validated: dict, *, event_id: str = "event-accepted", logical_id: str | None = None) -> dict:
    event = dict(validated)
    event.update(
        {
            "event_id": event_id,
            "event_type": "ARTIFACT_ACCEPTED",
            "actor_type": "HUMAN",
            "logical_artifact_id": logical_id or validated["logical_artifact_id"],
            "previous_status": "VALIDATED",
            "new_status": "ACCEPTED",
            "runtime_use_eligible": True,
            "consumer_compatibility": [{"consumer": "Runtime", "compatible": True, "reason": None}],
            "point_in_time_status": "PASS",
        }
    )
    return _write_evidence(tmp_path, event)


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_evidence(tmp_path: Path, event: dict, *, decision: str = "ACCEPT") -> dict:
    subject = event["artifact_instance_id"]
    schema_hash = event["schema_hash"]
    report = {
        "schema_version": "artifact_acceptance_report.v1",
        "acceptance_report_id": f"report-{event['event_id']}",
        "artifact_or_set_ref": subject,
        "reviewed_artifact_hashes": {subject: event["content_hash"]},
        "reviewed_schema_hashes": {subject: schema_hash},
        "reviewed_source_refs": [],
        "human_reviewer": "human",
        "architecture_reviewer": "arch",
        "regression_reviewer": "reg",
        "release_approver": "release",
        "review_started_at": "2026-07-13T00:00:00+00:00",
        "review_completed_at": "2026-07-13T01:00:00+00:00",
        "decision": decision,
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
        "regression_evidence_id": f"regression-{event['event_id']}",
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
            "approval_id": f"approval-{event['event_id']}-{approval_type}",
            "approval_type": approval_type,
            "subject_ref": subject,
            "reviewer_id": approval_type.lower(),
            "reviewer_role": approval_type,
            "decision": "APPROVED",
            "approved_at": "2026-07-13T02:00:00+00:00",
            "evidence_refs": [f"report-{event['event_id']}"],
            "conditions": [],
            "expires_at": None,
            "supersedes_approval_id": None,
        }
        for approval_type in ("HUMAN_REVIEW", "ARCHITECTURE_ACCEPTANCE", "REGRESSION_ACCEPTANCE", "RELEASE_APPROVAL")
    ]
    event["acceptance_report_ref"] = str(_write_json(tmp_path / f"report-{event['event_id']}.json", report))
    event["regression_ref"] = str(_write_json(tmp_path / f"regression-{event['event_id']}.json", regression))
    event["review_ref"] = str(_write_json(tmp_path / f"approvals-{event['event_id']}.json", approvals))
    return event


def _validate(log_path: Path) -> dict:
    return FullEventLogValidator(event_log_path=log_path, registry_root=log_path.parents[1], repo_root=Path.cwd()).validate()


def test_empty_log_pass(tmp_path: Path) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text("", encoding="utf-8")
    result = _validate(log)
    assert result["overall_result"] == "PASS"
    assert result["failure_class"] == "NONE"
    assert result["event_count"] == 0
    assert result["empty_registry"] is True


def test_single_draft_pass_and_hash_deterministic(tmp_path: Path) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    draft = _event(tmp_path, event_id="event-draft")
    _write_log(log, [draft])
    result = _validate(log)
    assert result["overall_result"] == "PASS"
    assert result["event_count"] == 1
    assert result["last_event_id"] == "event-draft"
    assert result["event_log_hash"] == hashlib.sha256(log.read_bytes()).hexdigest()


def test_draft_to_validated_and_multiple_logical_ids_pass(tmp_path: Path) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    first = _event(tmp_path, event_id="event-a", logical_id="artifact.test.a", artifact_name="a")
    second = _validated_event(tmp_path, first, event_id="event-a-validated")
    third = _event(tmp_path, event_id="event-b", logical_id="artifact.test.b", artifact_name="b")
    _write_log(log, [first, second, third])
    assert _validate(log)["overall_result"] == "PASS"


def test_duplicate_event_id_halts(tmp_path: Path) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    first = _event(tmp_path, event_id="event-same", artifact_name="a")
    second = _event(tmp_path, event_id="event-same", logical_id="artifact.test.b", artifact_name="b")
    _write_log(log, [first, second])
    assert _validate(log)["failure_class"] == "HALT"


def test_duplicate_fingerprint_halts(tmp_path: Path) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    first = _event(tmp_path, event_id="event-a")
    second = dict(first)
    second["event_id"] = "event-b"
    _write_log(log, [first, second])
    assert _validate(log)["failure_class"] == "HALT"


def test_illegal_lifecycle_halts(tmp_path: Path) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    event = _event(tmp_path, event_id="event-bad", event_type="ARTIFACT_VALIDATED", previous_status="DRAFT", new_status="VALIDATED")
    _write_log(log, [event])
    result = _validate(log)
    assert result["failure_class"] == "HALT"
    assert any("previous_status" in error for error in result["errors"])


def test_invalid_schema_event_halts(tmp_path: Path) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    event = _event(tmp_path, event_id="event-bad")
    event.pop("event_schema_version")
    _write_log(log, [event])
    assert _validate(log)["failure_class"] == "HALT"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (b'{"event_id":"x"}', "partial"),
        (b"not-json\n", "invalid JSON"),
        ("{}".encode("utf-16"), "invalid UTF-8"),
        (b"\xef\xbb\xbf{}\n", "BOM"),
        (b"\n", "blank line"),
        (b"[]\n", "non-object"),
    ],
)
def test_file_structure_halts(tmp_path: Path, raw: bytes, expected: str) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    log.parent.mkdir(parents=True)
    log.write_bytes(raw)
    result = _validate(log)
    assert result["failure_class"] == "HALT"
    assert any(expected in error for error in result["errors"])


def test_identity_mutation_halts(tmp_path: Path) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    first = _event(tmp_path, event_id="event-a", artifact_name="a")
    other_path, other_hash = _artifact(tmp_path, "other")
    second = _validated_event(tmp_path, first, event_id="event-b", physical_path=str(other_path), content_hash=other_hash)
    _write_log(log, [first, second])
    assert _validate(log)["failure_class"] == "HALT"


def test_validated_runtime_eligible_halts(tmp_path: Path) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    draft = _event(tmp_path, event_id="event-a")
    validated = _validated_event(tmp_path, draft, event_id="event-b", runtime_use_eligible=True)
    _write_log(log, [draft, validated])
    assert _validate(log)["failure_class"] == "HALT"


def test_multiple_active_accepted_instance_halts(tmp_path: Path) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    first_draft = _event(tmp_path, event_id="event-a", logical_id="artifact.test.active", artifact_name="a")
    first_validated = _validated_event(tmp_path, first_draft, event_id="event-b")
    first_accepted = _accepted_event(tmp_path, first_validated, event_id="event-c")
    second_draft = _event(tmp_path, event_id="event-d", logical_id="artifact.test.active", artifact_name="d")
    second_validated = _validated_event(tmp_path, second_draft, event_id="event-e")
    second_accepted = _accepted_event(tmp_path, second_validated, event_id="event-f")
    _write_log(log, [first_draft, first_validated, first_accepted, second_draft, second_validated, second_accepted])
    assert _validate(log)["failure_class"] == "HALT"


def test_path_registered_and_migrated_valid(tmp_path: Path) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    old_path, old_hash = _artifact(tmp_path, "old")
    new_path, _ = _artifact(tmp_path, "new")
    draft = _event(tmp_path, event_id="event-a", physical_path=str(old_path), content_hash=old_hash)
    registered = dict(draft)
    registered.update({"event_id": "event-b", "event_type": "PATH_REGISTERED", "previous_status": "DRAFT", "new_status": "DRAFT"})
    migrated = dict(draft)
    migrated.update(
        {
            "event_id": "event-c",
            "event_type": "PATH_MIGRATED",
            "previous_status": "DRAFT",
            "new_status": "DRAFT",
            "previous_physical_path": str(old_path),
            "new_physical_path": str(new_path),
        }
    )
    _write_log(log, [draft, registered, migrated])
    assert _validate(log)["overall_result"] == "PASS"


def test_path_migrated_previous_mismatch_halts(tmp_path: Path) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    old_path, old_hash = _artifact(tmp_path, "old")
    new_path, _ = _artifact(tmp_path, "new")
    draft = _event(tmp_path, event_id="event-a", physical_path=str(old_path), content_hash=old_hash)
    migrated = dict(draft)
    migrated.update(
        {
            "event_id": "event-b",
            "event_type": "PATH_MIGRATED",
            "previous_status": "DRAFT",
            "new_status": "DRAFT",
            "previous_physical_path": str(tmp_path / "wrong.json"),
            "new_physical_path": str(new_path),
        }
    )
    _write_log(log, [draft, migrated])
    assert _validate(log)["failure_class"] == "HALT"


def test_acceptance_evidence_mismatch_halts(tmp_path: Path) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    draft = _event(tmp_path, event_id="event-a")
    validated = _validated_event(tmp_path, draft, event_id="event-b")
    accepted = _accepted_event(tmp_path, validated, event_id="event-c")
    report = json.loads(Path(accepted["acceptance_report_ref"]).read_text(encoding="utf-8"))
    report["decision"] = "REJECT"
    Path(accepted["acceptance_report_ref"]).write_text(json.dumps(report), encoding="utf-8")
    _write_log(log, [draft, validated, accepted])
    assert _validate(log)["failure_class"] == "HALT"


def test_physical_line_order_respected_and_event_created_at_ignored(tmp_path: Path) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    draft = _event(tmp_path, event_id="event-a", event_created_at="2026-07-13T02:00:00+00:00")
    validated = _validated_event(tmp_path, draft, event_id="event-b", event_created_at="2026-07-13T01:00:00+00:00")
    _write_log(log, [draft, validated])
    assert _validate(log)["overall_result"] == "PASS"

    _write_log(log, [validated, draft])
    assert _validate(log)["failure_class"] == "HALT"


def test_input_event_log_unchanged_and_atomic_report_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log = tmp_path / "registry/events/registry_events.jsonl"
    _write_log(log, [_event(tmp_path, event_id="event-a")])
    before = log.read_bytes()
    fsync_calls: list[int] = []

    import ai_fund_lab_v2.artifact_registry.full_log_validator as module

    original_fsync = module.os.fsync

    def recording_fsync(fd: int) -> None:
        fsync_calls.append(fd)
        original_fsync(fd)

    monkeypatch.setattr(module.os, "fsync", recording_fsync)
    result = run_full_log_validation(event_log=log, output=tmp_path / "reports/full_log", registry_root=tmp_path / "registry", repo_root=Path.cwd())
    assert result["event_log_bytes_unchanged"] is True
    assert log.read_bytes() == before
    assert fsync_calls
    assert (tmp_path / "reports/full_log/full_log_validation_result.json").is_file()
    assert not list((tmp_path / "reports/full_log").glob("*.tmp"))
