from __future__ import annotations

import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ai_fund_lab_v2.artifact_registry.inventory import sha256_file
from ai_fund_lab_v2.artifact_registry.writer import (
    RegistryDuplicateEventError,
    RegistryEventLogWriter,
    RegistryEventValidationError,
    RegistryLockError,
    RegistryLogCorruptionError,
    event_fingerprint,
    read_event_log,
)


def _event(tmp_path: Path, *, status: str = "DRAFT", event_id: str | None = None, content: str = "artifact") -> dict:
    artifact = tmp_path / f"{content}.json"
    artifact.write_text(json.dumps({"content": content}) + "\n", encoding="utf-8")
    digest = sha256_file(artifact)
    previous_status = None if status == "DRAFT" else "DRAFT"
    event_type = "ARTIFACT_DISCOVERED" if status == "DRAFT" else "ARTIFACT_VALIDATED"
    return {
        "event_id": event_id,
        "event_type": event_type,
        "event_schema_version": "artifact_registry_event.v1",
        "event_created_at": datetime(2026, 7, 13, tzinfo=timezone.utc).isoformat(),
        "actor_type": "INVENTORY_TOOL" if status == "DRAFT" else "VALIDATION_TOOL",
        "actor_id": "phase16z-test",
        "authority_ref": "phase16z-test-authority",
        "logical_artifact_id": f"artifact.test.{content}",
        "artifact_instance_id": f"artifact.test.{content}@sha256-{digest[:16]}",
        "artifact_type": "TEST_ARTIFACT",
        "component": "Artifact Registry Test",
        "artifact_version": "v1",
        "previous_status": previous_status,
        "new_status": status,
        "runtime_use_eligible": False,
        "physical_path": str(artifact),
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
        "migration_status": "DRAFT" if status == "DRAFT" else "VALIDATED",
        "review_ref": None,
        "regression_ref": None,
        "acceptance_report_ref": None,
        "reason": None,
        "supersedes_event_id": None,
        "previous_physical_path": None,
        "new_physical_path": None,
    }


def _writer(tmp_path: Path, *, timeout: float = 1.0) -> RegistryEventLogWriter:
    return RegistryEventLogWriter(tmp_path / "registry", repo_root=Path.cwd(), lock_timeout_seconds=timeout)


def test_append_success_creates_formal_paths_and_event_line(tmp_path: Path) -> None:
    writer = _writer(tmp_path)
    result = writer.append_event(_event(tmp_path, status="DRAFT"))

    assert result.status == "APPENDED"
    assert result.event_count_after_append == 1
    assert (tmp_path / "registry/events/registry_events.jsonl").is_file()
    assert (tmp_path / "registry/locks/registry.lock").is_file()
    assert (tmp_path / "registry/schema").is_dir()
    assert (tmp_path / "registry/checkpoints").is_dir()

    rows = read_event_log(writer.event_log_path)
    assert len(rows) == 1
    assert rows[0]["event"]["new_status"] == "DRAFT"
    assert rows[0]["event"]["event_id"].endswith(result.fingerprint[:16])


def test_multiple_append_preserves_existing_lines(tmp_path: Path) -> None:
    writer = _writer(tmp_path)
    first = writer.append_event(_event(tmp_path, content="one"))
    second = writer.append_event(_event(tmp_path, content="two"))

    rows = read_event_log(writer.event_log_path)
    assert len(rows) == 2
    assert rows[0]["event"]["event_id"] == first.event_id
    assert rows[1]["event"]["event_id"] == second.event_id


def test_duplicate_fingerprint_rejected(tmp_path: Path) -> None:
    writer = _writer(tmp_path)
    event = _event(tmp_path)
    writer.append_event(event)
    duplicate = dict(event)
    duplicate["event_id"] = None

    with pytest.raises(RegistryDuplicateEventError):
        writer.append_event(duplicate)


def test_duplicate_event_id_rejected(tmp_path: Path) -> None:
    writer = _writer(tmp_path)
    writer.append_event(_event(tmp_path, event_id="event-fixed"))
    other = _event(tmp_path, event_id="event-fixed", content="other")

    with pytest.raises(RegistryDuplicateEventError):
        writer.append_event(other)


def test_writer_rejects_non_pass_validation(tmp_path: Path) -> None:
    writer = _writer(tmp_path)
    event = _event(tmp_path)
    event["content_hash"] = "0" * 64

    with pytest.raises(RegistryEventValidationError):
        writer.append_event(event)
    assert read_event_log(writer.event_log_path) == []


@pytest.mark.parametrize("status", ["ACCEPTED", "LEGACY", "REVOKED"])
def test_writer_rejects_promotion_statuses(tmp_path: Path, status: str) -> None:
    writer = _writer(tmp_path)
    event = _event(tmp_path, status="VALIDATED")
    event["new_status"] = status
    event["event_type"] = "ARTIFACT_ACCEPTED" if status == "ACCEPTED" else f"ARTIFACT_{status}"
    event["previous_status"] = "VALIDATED" if status == "ACCEPTED" else "ACCEPTED"

    with pytest.raises(RegistryEventValidationError):
        writer.append_event(event)
    assert read_event_log(writer.event_log_path) == []


def test_lock_rejects_concurrent_append(tmp_path: Path) -> None:
    writer = _writer(tmp_path, timeout=0.01)
    writer.initialize_storage()
    with writer.lock_path.open("a+b") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with pytest.raises(RegistryLockError):
                writer.append_event(_event(tmp_path))
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def test_corrupted_json_log_rejected(tmp_path: Path) -> None:
    writer = _writer(tmp_path)
    writer.initialize_storage()
    writer.event_log_path.write_text('{"bad": true}\nnot-json\n', encoding="utf-8")

    with pytest.raises(RegistryLogCorruptionError):
        writer.append_event(_event(tmp_path))


def test_partial_line_log_rejected(tmp_path: Path) -> None:
    writer = _writer(tmp_path)
    writer.initialize_storage()
    writer.event_log_path.write_bytes(b'{"bad": true}')

    with pytest.raises(RegistryLogCorruptionError):
        writer.append_event(_event(tmp_path))


def test_fsync_called_for_append(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    writer = _writer(tmp_path)
    calls: list[int] = []
    import ai_fund_lab_v2.artifact_registry.writer as writer_module

    original_fsync = writer_module.os.fsync

    def recording_fsync(fd: int) -> None:
        calls.append(fd)
        original_fsync(fd)

    monkeypatch.setattr(writer_module.os, "fsync", recording_fsync)
    writer.append_event(_event(tmp_path))

    assert calls


def test_failed_append_does_not_add_event(tmp_path: Path) -> None:
    writer = _writer(tmp_path)
    event = _event(tmp_path)
    event["new_status"] = "ACCEPTED"

    with pytest.raises(RegistryEventValidationError):
        writer.append_event(event)
    assert read_event_log(writer.event_log_path) == []


def test_event_fingerprint_is_stable(tmp_path: Path) -> None:
    event = _event(tmp_path)
    first = event_fingerprint(event)
    event["event_id"] = "different-id"
    assert event_fingerprint(event) == first
