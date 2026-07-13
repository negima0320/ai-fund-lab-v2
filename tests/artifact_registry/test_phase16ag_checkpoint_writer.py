from __future__ import annotations

import fcntl
import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.artifact_registry.checkpoint_writer import (
    RegistryCheckpointValidationError,
    RegistryCheckpointWriter,
    checkpoint_hash,
    run_checkpoint,
)
from ai_fund_lab_v2.artifact_registry.index_builder import run_index_build
from ai_fund_lab_v2.artifact_registry.inventory import sha256_file
from ai_fund_lab_v2.artifact_registry.writer import RegistryLockError


def _write_log(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n" for event in events), encoding="utf-8")


def _artifact(tmp_path: Path, name: str) -> tuple[Path, str]:
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps({"name": name}, sort_keys=True) + "\n", encoding="utf-8")
    return path, sha256_file(path)


def _event(tmp_path: Path, *, event_id: str, logical_id: str = "artifact.test.a", artifact_name: str = "a") -> dict:
    path, digest = _artifact(tmp_path, artifact_name)
    return {
        "event_id": event_id,
        "event_type": "ARTIFACT_DISCOVERED",
        "event_schema_version": "artifact_registry_event.v1",
        "event_created_at": "2026-07-13T00:00:00+00:00",
        "actor_type": "INVENTORY_TOOL",
        "actor_id": "phase16ag-test",
        "authority_ref": "test-authority",
        "logical_artifact_id": logical_id,
        "artifact_instance_id": f"{logical_id}@sha256-{digest[:16]}",
        "artifact_type": "TEST_ARTIFACT",
        "component": "Artifact Registry Test",
        "artifact_version": "v1",
        "previous_status": None,
        "new_status": "DRAFT",
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
        "migration_status": "DRAFT",
        "review_ref": None,
        "regression_ref": None,
        "acceptance_report_ref": None,
        "reason": None,
        "supersedes_event_id": None,
        "previous_physical_path": None,
        "new_physical_path": None,
    }


def _registry(tmp_path: Path, events: list[dict] | None = None) -> tuple[Path, Path]:
    root = tmp_path / "registry"
    log = root / "events/registry_events.jsonl"
    _write_log(log, events or [])
    run_index_build(registry_root=root, event_log=log, output=tmp_path / "reports/index", repo_root=Path.cwd())
    return root, log


def _checkpoint(root: Path, log: Path, tmp_path: Path) -> dict:
    return run_checkpoint(registry_root=root, event_log=log, output=tmp_path / "reports/checkpoint", repo_root=Path.cwd())


def test_empty_registry_initial_checkpoint_and_no_change(tmp_path: Path) -> None:
    root, log = _registry(tmp_path)
    result = _checkpoint(root, log, tmp_path)
    assert result["checkpoint_status"] == "EMPTY_REGISTRY_CREATED"
    assert result["checkpoint_created"] is True
    checkpoint = json.loads(Path(result["checkpoint_path"]).read_text(encoding="utf-8"))
    assert checkpoint["event_count"] == 0
    assert checkpoint["entry_count"] == 0
    assert checkpoint["previous_checkpoint_ref"] is None
    assert checkpoint["checkpoint_hash"] == checkpoint_hash(checkpoint)
    assert (root / "checkpoints/latest.json").is_file()

    second = _checkpoint(root, log, tmp_path)
    assert second["checkpoint_status"] == "NO_CHANGE"
    assert second["checkpoint_created"] is False


def test_normal_checkpoint_creation_and_previous_chain(tmp_path: Path) -> None:
    first = _event(tmp_path, event_id="event-a")
    root, log = _registry(tmp_path, [first])
    initial = _checkpoint(root, log, tmp_path)

    second_event = _event(tmp_path, event_id="event-b", logical_id="artifact.test.b", artifact_name="b")
    _write_log(log, [first, second_event])
    run_index_build(registry_root=root, event_log=log, output=tmp_path / "reports/index", repo_root=Path.cwd())
    chained = _checkpoint(root, log, tmp_path)
    assert chained["checkpoint_status"] == "CREATED"
    assert chained["previous_checkpoint_ref"] == initial["checkpoint_path"]
    assert json.loads(Path(chained["checkpoint_path"]).read_text(encoding="utf-8"))["previous_checkpoint_ref"] == initial["checkpoint_path"]


def test_full_log_validation_failure_blocks_checkpoint(tmp_path: Path) -> None:
    root, log = _registry(tmp_path)
    log.write_text("not-json\n", encoding="utf-8")
    result = _checkpoint(root, log, tmp_path)
    assert result["overall_result"] == "FAIL"
    assert result["checkpoint_created"] is False


@pytest.mark.parametrize("field,value", [("event_log_hash", "1" * 64), ("event_count", 99), ("last_event_id", "wrong"), ("index_hash", "0" * 64)])
def test_stale_or_corrupt_index_blocks_checkpoint(tmp_path: Path, field: str, value: object) -> None:
    root, log = _registry(tmp_path, [_event(tmp_path, event_id="event-a")])
    index_path = root / "index/registry_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if field == "index_hash":
        index[field] = value
    else:
        index[field] = value
        from ai_fund_lab_v2.artifact_registry.index_builder import index_hash
        index["index_hash"] = index_hash(index)
    index_path.write_text(json.dumps(index, sort_keys=True) + "\n", encoding="utf-8")
    result = _checkpoint(root, log, tmp_path)
    assert result["overall_result"] == "FAIL"
    assert result["checkpoint_created"] is False


def test_previous_checkpoint_missing_hash_mismatch_and_event_count_rollback(tmp_path: Path) -> None:
    root, log = _registry(tmp_path, [_event(tmp_path, event_id="event-a")])
    initial = _checkpoint(root, log, tmp_path)
    checkpoint_path = Path(initial["checkpoint_path"])
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["checkpoint_hash"] = "0" * 64
    checkpoint_path.write_text(json.dumps(checkpoint, sort_keys=True) + "\n", encoding="utf-8")
    assert _checkpoint(root, log, tmp_path)["overall_result"] == "FAIL"

    checkpoint_path.unlink()
    assert _checkpoint(root, log, tmp_path)["overall_result"] == "FAIL"


def test_deterministic_checkpoint_hash_excludes_created_at(tmp_path: Path) -> None:
    root, log = _registry(tmp_path)
    result = _checkpoint(root, log, tmp_path)
    checkpoint = json.loads(Path(result["checkpoint_path"]).read_text(encoding="utf-8"))
    changed = dict(checkpoint)
    changed["created_at"] = "2099-01-01T00:00:00+00:00"
    assert checkpoint_hash(changed) == checkpoint["checkpoint_hash"]


def test_atomic_checkpoint_write_latest_and_failed_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, log = _registry(tmp_path)
    writer = RegistryCheckpointWriter(registry_root=root, event_log_path=log, repo_root=Path.cwd())
    validation = writer._full_log_gate()
    index = writer._read_and_validate_index(validation)
    checkpoint = writer._checkpoint_payload(validation, index, None)
    path = writer.checkpoints_dir / f"{checkpoint['checkpoint_id']}.json"

    import ai_fund_lab_v2.artifact_registry.checkpoint_writer as module

    def failing_replace(src: object, dst: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(module.os, "replace", failing_replace)
    with pytest.raises(OSError):
        writer._write_checkpoint_atomic(path, checkpoint)
    assert not path.exists()
    assert not list(writer.checkpoints_dir.glob("*.tmp"))

    monkeypatch.undo()
    result = writer.write_checkpoint()
    assert result["latest_ref_updated"] is True
    latest = json.loads(writer.latest_path.read_text(encoding="utf-8"))
    assert latest["checkpoint_id"] == result["checkpoint_id"]


def test_duplicate_checkpoint_id_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, log = _registry(tmp_path)
    writer = RegistryCheckpointWriter(registry_root=root, event_log_path=log, repo_root=Path.cwd())
    validation = writer._full_log_gate()
    index = writer._read_and_validate_index(validation)
    checkpoint = writer._checkpoint_payload(validation, index, None)
    path = writer.checkpoints_dir / f"{checkpoint['checkpoint_id']}.json"
    writer._write_checkpoint_atomic(path, checkpoint)
    with pytest.raises(RegistryCheckpointValidationError):
        writer._write_checkpoint_atomic(path, checkpoint)


def test_lock_contention_and_release_on_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, log = _registry(tmp_path)
    writer = RegistryCheckpointWriter(registry_root=root, event_log_path=log, repo_root=Path.cwd(), lock_timeout_seconds=0.01)
    writer.lock_path.parent.mkdir(parents=True, exist_ok=True)
    writer.lock_path.touch()
    with writer.lock_path.open("a+b") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with pytest.raises(RegistryLockError):
                writer.write_checkpoint()
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def boom() -> dict:
        raise RegistryCheckpointValidationError("boom")

    monkeypatch.setattr(writer, "_full_log_gate", boom)
    with pytest.raises(RegistryCheckpointValidationError):
        writer.write_checkpoint()
    monkeypatch.undo()
    assert writer.write_checkpoint()["overall_result"] == "PASS"


def test_event_log_and_index_unchanged(tmp_path: Path) -> None:
    root, log = _registry(tmp_path, [_event(tmp_path, event_id="event-a")])
    index_path = root / "index/registry_index.json"
    before_log = log.read_bytes()
    before_index = index_path.read_bytes()
    _checkpoint(root, log, tmp_path)
    assert log.read_bytes() == before_log
    assert index_path.read_bytes() == before_index
