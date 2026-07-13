from __future__ import annotations

import fcntl
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ai_fund_lab_v2.artifact_registry.index_builder import (
    MaterializedRegistryIndexBuilder,
    index_hash,
    run_index_build,
)
from ai_fund_lab_v2.artifact_registry.inventory import sha256_file
from ai_fund_lab_v2.artifact_registry.writer import RegistryLockError


def _write_log(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n" for event in events), encoding="utf-8")


def _artifact(tmp_path: Path, name: str) -> tuple[Path, str]:
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps({"name": name}, sort_keys=True) + "\n", encoding="utf-8")
    return path, sha256_file(path)


def _event(
    tmp_path: Path,
    *,
    event_id: str,
    logical_id: str = "artifact.test.a",
    event_type: str = "ARTIFACT_DISCOVERED",
    previous_status: str | None = None,
    new_status: str | None = "DRAFT",
    artifact_name: str = "a",
    physical_path: str | None = None,
    content_hash: str | None = None,
    event_created_at: str = "2026-07-13T00:00:00+00:00",
    runtime_use_eligible: bool = False,
) -> dict:
    path, digest = _artifact(tmp_path, artifact_name)
    digest = content_hash or digest
    return {
        "event_id": event_id,
        "event_type": event_type,
        "event_schema_version": "artifact_registry_event.v1",
        "event_created_at": event_created_at,
        "actor_type": "INVENTORY_TOOL" if event_type == "ARTIFACT_DISCOVERED" else "VALIDATION_TOOL",
        "actor_id": "phase16ad-test",
        "authority_ref": "test-authority",
        "logical_artifact_id": logical_id,
        "artifact_instance_id": f"{logical_id}@sha256-{digest[:16]}",
        "artifact_type": "TEST_ARTIFACT",
        "component": "Artifact Registry Test",
        "artifact_version": "v1",
        "previous_status": previous_status,
        "new_status": new_status,
        "runtime_use_eligible": runtime_use_eligible,
        "physical_path": physical_path or str(path),
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


def _validated(draft: dict, *, event_id: str, **updates: object) -> dict:
    event = dict(draft)
    event.update({"event_id": event_id, "event_type": "ARTIFACT_VALIDATED", "previous_status": "DRAFT", "new_status": "VALIDATED", "migration_status": "VALIDATED"})
    event.update(updates)
    return event


def _builder(tmp_path: Path) -> tuple[MaterializedRegistryIndexBuilder, Path]:
    root = tmp_path / "registry"
    log = root / "events/registry_events.jsonl"
    return MaterializedRegistryIndexBuilder(registry_root=root, event_log_path=log, repo_root=Path.cwd(), lock_timeout_seconds=0.05), log


def _read_index(builder: MaterializedRegistryIndexBuilder) -> dict:
    return json.loads(builder.index_path.read_text(encoding="utf-8"))


def test_empty_log_builds_empty_registry_index(tmp_path: Path) -> None:
    builder, log = _builder(tmp_path)
    _write_log(log, [])
    before = hashlib.sha256(log.read_bytes()).hexdigest()
    result = builder.build()
    after = hashlib.sha256(log.read_bytes()).hexdigest()

    assert result["build_status"] == "EMPTY_REGISTRY"
    assert result["entry_count"] == 0
    assert result["index_replaced"] is True
    assert before == after
    index = _read_index(builder)
    assert index["entries"] == {}
    assert index["event_count"] == 0
    assert index["index_hash"] == index_hash(index)


def test_single_draft_validated_and_multiple_logical_ids_project(tmp_path: Path) -> None:
    builder, log = _builder(tmp_path)
    first = _event(tmp_path, event_id="event-a", logical_id="artifact.test.a", artifact_name="a")
    first_validated = _validated(first, event_id="event-b")
    second = _event(tmp_path, event_id="event-c", logical_id="artifact.test.c", artifact_name="c")
    _write_log(log, [first, first_validated, second])
    result = builder.build()
    index = _read_index(builder)

    assert result["build_status"] == "BUILT"
    assert index["entry_count"] == 2
    assert index["entries"]["artifact.test.a"]["current_status"] == "VALIDATED"
    assert index["entries"]["artifact.test.c"]["current_status"] == "DRAFT"


def test_physical_line_order_and_event_created_at_ignored(tmp_path: Path) -> None:
    builder, log = _builder(tmp_path)
    draft = _event(tmp_path, event_id="event-a", event_created_at="2026-07-13T02:00:00+00:00")
    validated = _validated(draft, event_id="event-b", event_created_at="2026-07-13T01:00:00+00:00")
    _write_log(log, [draft, validated])
    assert builder.build()["overall_result"] == "PASS"

    builder2, log2 = _builder(tmp_path / "bad")
    _write_log(log2, [validated, draft])
    result = builder2.build()
    assert result["overall_result"] == "FAIL"


def test_path_registered_and_migrated_project(tmp_path: Path) -> None:
    builder, log = _builder(tmp_path)
    old_path, old_hash = _artifact(tmp_path, "old")
    new_path, _ = _artifact(tmp_path, "new")
    draft = _event(tmp_path, event_id="event-a", physical_path=str(old_path), content_hash=old_hash)
    registered = dict(draft)
    registered.update({"event_id": "event-b", "event_type": "PATH_REGISTERED", "previous_status": "DRAFT", "new_status": "DRAFT"})
    migrated = dict(draft)
    migrated.update({"event_id": "event-c", "event_type": "PATH_MIGRATED", "previous_status": "DRAFT", "new_status": "DRAFT", "previous_physical_path": str(old_path), "new_physical_path": str(new_path)})
    _write_log(log, [draft, registered, migrated])
    builder.build()
    entry = _read_index(builder)["entries"]["artifact.test.a"]
    assert entry["physical_path"] == str(new_path)
    assert entry["current_status"] == "DRAFT"


def test_legacy_and_revoked_history(tmp_path: Path) -> None:
    builder, log = _builder(tmp_path)
    draft = _event(tmp_path, event_id="event-a")
    validated = _validated(draft, event_id="event-b")
    revoked = dict(validated)
    revoked.update({"event_id": "event-c", "event_type": "ARTIFACT_REVOKED", "previous_status": "VALIDATED", "new_status": "REVOKED"})
    _write_log(log, [draft, validated, revoked])
    builder.build()
    entry = _read_index(builder)["entries"]["artifact.test.a"]
    assert entry["revoked_instances"] == [draft["artifact_instance_id"]]
    assert entry["current_status"] == "REVOKED"


def test_full_validator_failure_blocks_build_and_preserves_existing_index(tmp_path: Path) -> None:
    builder, log = _builder(tmp_path)
    _write_log(log, [_event(tmp_path, event_id="event-a")])
    builder.build()
    existing = builder.index_path.read_text(encoding="utf-8")

    log.write_text("not-json\n", encoding="utf-8")
    result = builder.build()
    assert result["overall_result"] == "FAIL"
    assert builder.index_path.read_text(encoding="utf-8") == existing


def test_duplicate_event_log_blocks_build(tmp_path: Path) -> None:
    builder, log = _builder(tmp_path)
    first = _event(tmp_path, event_id="event-a")
    second = dict(first)
    second["event_id"] = "event-b"
    _write_log(log, [first, second])
    assert builder.build()["overall_result"] == "FAIL"


def test_deterministic_index_hash_and_generated_at_excluded(tmp_path: Path) -> None:
    builder, log = _builder(tmp_path)
    _write_log(log, [_event(tmp_path, event_id="event-a")])
    builder.build()
    first = _read_index(builder)
    first["generated_at"] = "2099-01-01T00:00:00+00:00"
    assert index_hash(first) == first["index_hash"]


def test_no_change_does_not_rewrite(tmp_path: Path) -> None:
    builder, log = _builder(tmp_path)
    _write_log(log, [_event(tmp_path, event_id="event-a")])
    builder.build()
    before = builder.index_path.read_text(encoding="utf-8")
    result = builder.build()
    assert result["build_status"] == "NO_CHANGE"
    assert result["index_replaced"] is False
    assert builder.index_path.read_text(encoding="utf-8") == before


def test_invalid_existing_index_rebuilds_from_event_log(tmp_path: Path) -> None:
    builder, log = _builder(tmp_path)
    _write_log(log, [_event(tmp_path, event_id="event-a")])
    builder.index_path.parent.mkdir(parents=True)
    builder.index_path.write_text("not-json\n", encoding="utf-8")
    result = builder.build()
    assert result["overall_result"] == "PASS"
    assert json.loads(builder.index_path.read_text(encoding="utf-8"))["entry_count"] == 1


def test_lock_contention_blocks_build(tmp_path: Path) -> None:
    builder, log = _builder(tmp_path)
    _write_log(log, [])
    builder.lock_path.parent.mkdir(parents=True)
    builder.lock_path.touch()
    with builder.lock_path.open("a+b") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with pytest.raises(RegistryLockError):
                builder.build()
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    assert not builder.index_path.exists()


def test_atomic_index_write_and_report_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    builder, log = _builder(tmp_path)
    _write_log(log, [_event(tmp_path, event_id="event-a")])
    calls: list[int] = []
    import ai_fund_lab_v2.artifact_registry.index_builder as module

    original_fsync = module.os.fsync

    def recording_fsync(fd: int) -> None:
        calls.append(fd)
        original_fsync(fd)

    monkeypatch.setattr(module.os, "fsync", recording_fsync)
    result = run_index_build(registry_root=builder.registry_root, event_log=log, output=tmp_path / "reports/index_build", repo_root=Path.cwd())
    assert result["overall_result"] == "PASS"
    assert calls
    assert not list(builder.index_path.parent.glob("*.tmp"))
    assert (tmp_path / "reports/index_build/build_result.json").is_file()
