from __future__ import annotations

import argparse
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.artifact_registry.full_log_validator import DEFAULT_EVENT_LOG_PATH, FullEventLogValidator, atomic_write_text
from ai_fund_lab_v2.artifact_registry.index_builder import INDEX_RELATIVE_PATH, index_hash, index_semantic_issues
from ai_fund_lab_v2.artifact_registry.inventory import stable_json_hash
from ai_fund_lab_v2.artifact_registry.validator import ValidationSafetyError, ensure_safe_output_root, load_schemas, read_json, schema_validate
from ai_fund_lab_v2.artifact_registry.writer import DEFAULT_REGISTRY_ROOT, LOCK_RELATIVE_PATH, _LockedFile


CHECKPOINT_WRITER_VERSION = "phase16ag_artifact_registry_checkpoint_writer_v1"
CHECKPOINTS_RELATIVE_PATH = Path("checkpoints")
LATEST_RELATIVE_PATH = Path("checkpoints/latest.json")


class RegistryCheckpointError(RuntimeError):
    pass


class RegistryCheckpointValidationError(RegistryCheckpointError):
    pass


class RegistryCheckpointWriter:
    def __init__(
        self,
        *,
        registry_root: Path | str = DEFAULT_REGISTRY_ROOT,
        event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH,
        index_path: Path | str | None = None,
        schema_root: Path | str = "docs/02_architecture/schemas",
        repo_root: Path | str | None = None,
        lock_timeout_seconds: float = 10.0,
        created_by: str = "artifact_registry_checkpoint_writer",
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
        self.registry_root = self._resolve(registry_root)
        self.event_log_path = self._resolve(event_log_path)
        self.index_path = self._resolve(index_path) if index_path is not None else self.registry_root / INDEX_RELATIVE_PATH
        self.schema_root = self._resolve(schema_root)
        self.lock_timeout_seconds = lock_timeout_seconds
        self.created_by = created_by

    @property
    def checkpoints_dir(self) -> Path:
        return self.registry_root / CHECKPOINTS_RELATIVE_PATH

    @property
    def latest_path(self) -> Path:
        return self.registry_root / LATEST_RELATIVE_PATH

    @property
    def lock_path(self) -> Path:
        return self.registry_root / LOCK_RELATIVE_PATH

    def write_checkpoint(self) -> dict[str, Any]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.touch(exist_ok=True)
        with _LockedFile(self.lock_path, timeout_seconds=self.lock_timeout_seconds):
            validation = self._full_log_gate()
            index = self._read_and_validate_index(validation)
            previous = self._read_latest_checkpoint()
            previous_ref = str(previous["path"]) if previous else None
            if previous:
                self._validate_previous_checkpoint(previous["checkpoint"], validation, index)
                if self._same_state(previous["checkpoint"], validation, index):
                    return self._result(
                        checkpoint_status="NO_CHANGE",
                        overall_result="PASS",
                        failure_class="NONE",
                        validation=validation,
                        index=index,
                        checkpoint_id=previous["checkpoint"]["checkpoint_id"],
                        checkpoint_path=str(previous["path"]),
                        checkpoint_hash=previous["checkpoint"]["checkpoint_hash"],
                        checkpoint_created=False,
                        previous_checkpoint_ref=previous["checkpoint"].get("previous_checkpoint_ref"),
                        latest_ref_updated=False,
                        warnings=[],
                        errors=[],
                    )

            checkpoint = self._checkpoint_payload(validation, index, previous_ref)
            self._validate_checkpoint(checkpoint)
            checkpoint_path = self.checkpoints_dir / f"{checkpoint['checkpoint_id']}.json"
            self._write_checkpoint_atomic(checkpoint_path, checkpoint)
            self._write_latest_atomic(checkpoint_path, checkpoint)
            status = "EMPTY_REGISTRY_CREATED" if validation["event_count"] == 0 and index["entry_count"] == 0 else "CREATED"
            return self._result(
                checkpoint_status=status,
                overall_result="PASS",
                failure_class="NONE",
                validation=validation,
                index=index,
                checkpoint_id=checkpoint["checkpoint_id"],
                checkpoint_path=str(checkpoint_path),
                checkpoint_hash=checkpoint["checkpoint_hash"],
                checkpoint_created=True,
                previous_checkpoint_ref=previous_ref,
                latest_ref_updated=True,
                warnings=[],
                errors=[],
            )

    def _full_log_gate(self) -> dict[str, Any]:
        result = FullEventLogValidator(event_log_path=self.event_log_path, registry_root=self.registry_root, schema_root=self.schema_root, repo_root=self.repo_root).validate()
        if result["overall_result"] != "PASS" or result["failure_class"] != "NONE":
            raise RegistryCheckpointValidationError("FullEventLogValidator gate did not PASS")
        return result

    def _read_and_validate_index(self, validation: dict[str, Any]) -> dict[str, Any]:
        if not self.index_path.is_file():
            raise RegistryCheckpointValidationError(f"materialized index is missing: {self.index_path}")
        try:
            index = read_json(self.index_path)
        except Exception as exc:
            raise RegistryCheckpointValidationError("materialized index is not valid JSON") from exc
        schemas = load_schemas(self.schema_root)
        issues = schema_validate(index, schemas["artifact_registry_index.schema.json"], field_path="$")
        semantic = index_semantic_issues(index)
        if issues or semantic:
            raise RegistryCheckpointValidationError("materialized index validation failed: " + "; ".join([i["message"] for i in issues] + semantic))
        if index.get("index_hash") != index_hash(index):
            raise RegistryCheckpointValidationError("materialized index hash mismatch")
        pairs = {
            "event_log_hash": validation["event_log_hash"],
            "event_count": validation["event_count"],
            "last_event_id": validation["last_event_id"],
        }
        for field, expected in pairs.items():
            if index.get(field) != expected:
                raise RegistryCheckpointValidationError(f"Event Log / Index mismatch: {field}")
        return index

    def _read_latest_checkpoint(self) -> dict[str, Any] | None:
        if not self.latest_path.exists():
            return None
        try:
            latest = read_json(self.latest_path)
            path = Path(latest["checkpoint_path"])
            if not path.is_absolute():
                path = self.repo_root / path
            checkpoint = read_json(path)
            self._validate_checkpoint(checkpoint)
            return {"latest": latest, "path": path, "checkpoint": checkpoint}
        except Exception as exc:
            raise RegistryCheckpointValidationError("latest checkpoint reference is corrupt or unreadable") from exc

    def _validate_previous_checkpoint(self, checkpoint: dict[str, Any], validation: dict[str, Any], index: dict[str, Any]) -> None:
        if checkpoint.get("checkpoint_hash") != checkpoint_hash(checkpoint):
            raise RegistryCheckpointValidationError("previous checkpoint hash mismatch")
        if int(validation["event_count"]) < int(checkpoint["event_count"]):
            raise RegistryCheckpointValidationError("event count rollback detected")
        if checkpoint.get("event_log_hash") != validation["event_log_hash"] and int(validation["event_count"]) == int(checkpoint["event_count"]):
            raise RegistryCheckpointValidationError("same event count with different Event Log hash")

    def _same_state(self, checkpoint: dict[str, Any], validation: dict[str, Any], index: dict[str, Any]) -> bool:
        return all(
            [
                checkpoint.get("event_log_hash") == validation["event_log_hash"],
                checkpoint.get("event_count") == validation["event_count"],
                checkpoint.get("last_event_id") == validation["last_event_id"],
                checkpoint.get("materialized_index_hash") == index["index_hash"],
                checkpoint.get("entry_count") == index["entry_count"],
                checkpoint.get("schema_versions") == schema_versions(),
            ]
        )

    def _checkpoint_payload(self, validation: dict[str, Any], index: dict[str, Any], previous_ref: str | None) -> dict[str, Any]:
        fingerprint = stable_json_hash(
            {
                "event_log_hash": validation["event_log_hash"],
                "event_count": validation["event_count"],
                "last_event_id": validation["last_event_id"],
                "materialized_index_hash": index["index_hash"],
                "entry_count": index["entry_count"],
                "previous_checkpoint_ref": previous_ref,
                "schema_versions": schema_versions(),
            }
        )
        payload = {
            "schema_version": "artifact_registry_checkpoint.v1",
            "checkpoint_id": f"checkpoint-{uuid.uuid4()}-{fingerprint[:16]}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "event_log_path": str(self.event_log_path),
            "event_log_hash": validation["event_log_hash"],
            "event_count": validation["event_count"],
            "last_event_id": validation["last_event_id"],
            "materialized_index_path": str(self.index_path),
            "materialized_index_hash": index["index_hash"],
            "entry_count": index["entry_count"],
            "schema_versions": schema_versions(),
            "validation_result": "PASS",
            "previous_checkpoint_ref": previous_ref,
            "created_by": self.created_by,
            "checkpoint_hash": "",
            "authority_change": False,
        }
        payload["checkpoint_hash"] = checkpoint_hash(payload)
        return payload

    def _validate_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        schemas = load_schemas(self.schema_root)
        issues = schema_validate(checkpoint, schemas["artifact_registry_checkpoint.schema.json"], field_path="$")
        if issues:
            raise RegistryCheckpointValidationError("; ".join(issue["message"] for issue in issues))
        if checkpoint.get("checkpoint_hash") != checkpoint_hash(checkpoint):
            raise RegistryCheckpointValidationError("checkpoint hash self-consistency failed")
        if checkpoint.get("authority_change") is not False:
            raise RegistryCheckpointValidationError("checkpoint must not change authority")

    def _write_checkpoint_atomic(self, path: Path, checkpoint: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise RegistryCheckpointValidationError(f"duplicate checkpoint id: {checkpoint['checkpoint_id']}")
        self._atomic_write_json(path, checkpoint, replace_existing=False)

    def _write_latest_atomic(self, checkpoint_path: Path, checkpoint: dict[str, Any]) -> None:
        latest = {
            "schema_version": "artifact_registry_latest_checkpoint_ref.v1",
            "checkpoint_id": checkpoint["checkpoint_id"],
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_hash": checkpoint["checkpoint_hash"],
            "event_log_hash": checkpoint["event_log_hash"],
            "materialized_index_hash": checkpoint["materialized_index_hash"],
            "created_at": checkpoint["created_at"],
            "authority_change": False,
        }
        self._atomic_write_json(self.latest_path, latest, replace_existing=True)

    def _atomic_write_json(self, path: Path, payload: dict[str, Any], *, replace_existing: bool) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            loaded = read_json(temp_path)
            if loaded.get("schema_version") == "artifact_registry_checkpoint.v1":
                self._validate_checkpoint(loaded)
            if not replace_existing and path.exists():
                raise RegistryCheckpointValidationError(f"checkpoint already exists: {path}")
            os.replace(temp_path, path)
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except Exception:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
            raise

    def _result(
        self,
        *,
        checkpoint_status: str,
        overall_result: str,
        failure_class: str,
        validation: dict[str, Any],
        index: dict[str, Any],
        checkpoint_id: str | None,
        checkpoint_path: str | None,
        checkpoint_hash: str | None,
        checkpoint_created: bool,
        previous_checkpoint_ref: str | None,
        latest_ref_updated: bool,
        warnings: list[str],
        errors: list[str],
    ) -> dict[str, Any]:
        return {
            "schema_version": "artifact_registry_checkpoint_result.v1",
            "operation_id": f"checkpoint-operation-{uuid.uuid4()}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "checkpoint_status": checkpoint_status,
            "overall_result": overall_result,
            "failure_class": failure_class,
            "checkpoint_id": checkpoint_id,
            "checkpoint_path": checkpoint_path,
            "checkpoint_hash": checkpoint_hash,
            "checkpoint_created": checkpoint_created,
            "previous_checkpoint_ref": previous_checkpoint_ref,
            "event_log_hash": validation.get("event_log_hash"),
            "event_count": validation.get("event_count"),
            "last_event_id": validation.get("last_event_id"),
            "materialized_index_hash": index.get("index_hash"),
            "entry_count": index.get("entry_count"),
            "validation_ref": validation.get("validation_id"),
            "index_validation_result": "PASS",
            "latest_ref_updated": latest_ref_updated,
            "warnings": warnings,
            "errors": errors,
            "recommended_action": "No action required." if overall_result == "PASS" else "Run Full Log validation and Index Builder before retrying.",
            "writer_integration": "NOT_IMPLEMENTED",
            "index_builder_integration": "NOT_IMPLEMENTED",
            "authority_change": False,
        }

    def _resolve(self, path: Path | str) -> Path:
        value = Path(path)
        return value if value.is_absolute() else self.repo_root / value


def schema_versions() -> dict[str, str]:
    return {
        "artifact_registry_checkpoint": "artifact_registry_checkpoint.v1",
        "artifact_registry_event": "artifact_registry_event.v1",
        "artifact_registry_index": "artifact_registry_index.v1",
        "artifact_registry_entry": "artifact_registry_entry.v1",
    }


def checkpoint_hash(checkpoint: dict[str, Any]) -> str:
    payload = {key: value for key, value in checkpoint.items() if key not in {"checkpoint_hash", "created_at"}}
    return stable_json_hash(payload)


def write_checkpoint_outputs(result: dict[str, Any], output_root: Path, *, repo_root: Path, event_log_path: Path) -> None:
    ensure_safe_output_root(event_log_path.parent, output_root, repo_root=repo_root)
    atomic_write_text(output_root / "checkpoint_result.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    summary = {key: result[key] for key in ("schema_version", "created_at", "checkpoint_status", "overall_result", "failure_class", "checkpoint_id", "checkpoint_hash", "event_count", "entry_count", "latest_ref_updated")}
    atomic_write_text(output_root / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    audit = "\n".join(
        [
            "# Artifact Registry Checkpoint Audit",
            "",
            f"- checkpoint_status: {result['checkpoint_status']}",
            f"- overall_result: {result['overall_result']}",
            f"- failure_class: {result['failure_class']}",
            f"- checkpoint_id: {result['checkpoint_id']}",
            f"- checkpoint_created: {result['checkpoint_created']}",
            f"- previous_checkpoint_ref: {result['previous_checkpoint_ref']}",
            f"- event_count: {result['event_count']}",
            f"- entry_count: {result['entry_count']}",
            f"- authority_change: {result['authority_change']}",
            "",
        ]
    )
    atomic_write_text(output_root / "audit.md", audit)


def run_checkpoint(
    *,
    registry_root: Path = DEFAULT_REGISTRY_ROOT,
    event_log: Path = DEFAULT_EVENT_LOG_PATH,
    index_path: Path | None = None,
    output: Path = Path("reports/phase16_registry_checkpoint"),
    repo_root: Path | None = None,
    lock_timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    repo_root = repo_root or Path.cwd()
    writer = RegistryCheckpointWriter(registry_root=registry_root, event_log_path=event_log, index_path=index_path, repo_root=repo_root, lock_timeout_seconds=lock_timeout_seconds)
    try:
        result = writer.write_checkpoint()
    except RegistryCheckpointValidationError as exc:
        result = {
            "schema_version": "artifact_registry_checkpoint_result.v1",
            "operation_id": f"checkpoint-operation-{uuid.uuid4()}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "checkpoint_status": "FAILED",
            "overall_result": "FAIL",
            "failure_class": "HALT",
            "checkpoint_id": None,
            "checkpoint_path": None,
            "checkpoint_hash": None,
            "checkpoint_created": False,
            "previous_checkpoint_ref": None,
            "event_log_hash": None,
            "event_count": None,
            "last_event_id": None,
            "materialized_index_hash": None,
            "entry_count": None,
            "validation_ref": None,
            "index_validation_result": "FAIL",
            "latest_ref_updated": False,
            "warnings": [],
            "errors": [str(exc)],
            "recommended_action": "Run Full Log validation and Index Builder before retrying.",
            "writer_integration": "NOT_IMPLEMENTED",
            "index_builder_integration": "NOT_IMPLEMENTED",
            "authority_change": False,
        }
    write_checkpoint_outputs(result, output, repo_root=repo_root, event_log_path=writer.event_log_path)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write Artifact Registry integrity checkpoint.")
    parser.add_argument("--registry-root", default=str(DEFAULT_REGISTRY_ROOT))
    parser.add_argument("--event-log", default=str(DEFAULT_EVENT_LOG_PATH))
    parser.add_argument("--index-path", default=None)
    parser.add_argument("--output", default="reports/phase16_registry_checkpoint")
    args = parser.parse_args(argv)
    try:
        result = run_checkpoint(registry_root=Path(args.registry_root), event_log=Path(args.event_log), index_path=Path(args.index_path) if args.index_path else None, output=Path(args.output), repo_root=Path.cwd())
    except ValidationSafetyError as exc:
        print(f"VALIDATION_ERROR: {exc}")
        return 2
    print(json.dumps({key: result[key] for key in ("overall_result", "failure_class", "checkpoint_status", "checkpoint_id", "checkpoint_created")}, sort_keys=True))
    return 0 if result["overall_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
