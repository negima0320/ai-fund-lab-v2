from __future__ import annotations

import argparse
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.artifact_registry.full_log_validator import (
    DEFAULT_EVENT_LOG_PATH,
    FullEventLogValidator,
    atomic_write_text,
)
from ai_fund_lab_v2.artifact_registry.inventory import stable_json_hash
from ai_fund_lab_v2.artifact_registry.validator import (
    ValidationSafetyError,
    ensure_safe_output_root,
    load_schemas,
    read_json,
    schema_validate,
)
from ai_fund_lab_v2.artifact_registry.writer import DEFAULT_REGISTRY_ROOT, LOCK_RELATIVE_PATH, _LockedFile


INDEX_BUILDER_VERSION = "phase16ad_materialized_registry_index_builder_v1"
INDEX_RELATIVE_PATH = Path("index/registry_index.json")


class RegistryIndexBuildError(RuntimeError):
    pass


class RegistryIndexValidationError(RegistryIndexBuildError):
    pass


class RegistryIndexDurabilityError(RegistryIndexBuildError):
    def __init__(self, message: str, *, index_replaced: bool) -> None:
        super().__init__(message)
        self.index_replaced = index_replaced


class MaterializedRegistryIndexBuilder:
    def __init__(
        self,
        *,
        registry_root: Path | str = DEFAULT_REGISTRY_ROOT,
        event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH,
        schema_root: Path | str = "docs/02_architecture/schemas",
        repo_root: Path | str | None = None,
        lock_timeout_seconds: float = 10.0,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
        self.registry_root = self._resolve(registry_root)
        self.event_log_path = self._resolve(event_log_path)
        self.schema_root = self._resolve(schema_root)
        self.lock_timeout_seconds = lock_timeout_seconds

    @property
    def index_path(self) -> Path:
        return self.registry_root / INDEX_RELATIVE_PATH

    @property
    def lock_path(self) -> Path:
        return self.registry_root / LOCK_RELATIVE_PATH

    def build(self) -> dict[str, Any]:
        before_index = self._read_existing_index()
        previous_index_hash = before_index.get("index_hash") if isinstance(before_index, dict) else None
        warnings: list[str] = []
        errors: list[str] = []
        existing_validation = self._validate_existing_index(before_index, warnings) if before_index is not None else {"status": "NOT_FOUND", "stale_fields": [], "rebuild_reason": None}

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.touch(exist_ok=True)
        with _LockedFile(self.lock_path, timeout_seconds=self.lock_timeout_seconds):
            validator = FullEventLogValidator(
                event_log_path=self.event_log_path,
                registry_root=self.registry_root,
                schema_root=self.schema_root,
                repo_root=self.repo_root,
            )
            validation = validator.validate(include_events=True)
            if validation["overall_result"] != "PASS" or validation["failure_class"] != "NONE":
                errors.append("FullEventLogValidator gate did not PASS.")
                return self._build_result(
                    build_status="FAILED",
                    overall_result="FAIL",
                    failure_class=validation["failure_class"] if validation["failure_class"] != "NONE" else "HALT",
                    validation=validation,
                    index_hash=None,
                    entry_count=0,
                    previous_index_hash=previous_index_hash,
                    index_replaced=False,
                    warnings=warnings,
                    errors=errors,
                )

            events = list(validation.get("events") or [])
            index = self._project_index(validation, events)
            self._validate_index(index)
            existing_validation = self._classify_existing_index(before_index, index, warnings)

            status = "EMPTY_REGISTRY" if validation["event_count"] == 0 else "BUILT"
            if existing_validation["status"] == "VALID_CURRENT" and self._is_no_change(before_index, index):
                status = "NO_CHANGE"
                replaced = False
                durability_status = "NOT_APPLICABLE"
            else:
                try:
                    durability_status = self._write_index_atomic(index)
                    replaced = True
                except RegistryIndexDurabilityError as exc:
                    errors.append(str(exc))
                    return self._build_result(
                        build_status="FAILED",
                        overall_result="REVIEW_REQUIRED",
                        failure_class="REVIEW_REQUIRED",
                        validation=validation,
                        index_hash=index["index_hash"],
                        entry_count=index["entry_count"],
                        previous_index_hash=previous_index_hash,
                        index_replaced=exc.index_replaced,
                        warnings=warnings + [f"existing_index_validation={existing_validation['status']}"],
                        errors=errors,
                        existing_index_status=existing_validation["status"],
                        stale_fields=existing_validation["stale_fields"],
                        rebuild_reason=existing_validation["rebuild_reason"],
                        semantic_validation_result="PASS",
                        durability_status="REVIEW_REQUIRED",
                    )

            return self._build_result(
                build_status=status,
                overall_result="PASS",
                failure_class="NONE",
                validation=validation,
                index_hash=index["index_hash"],
                entry_count=index["entry_count"],
                previous_index_hash=previous_index_hash,
                index_replaced=replaced,
                warnings=warnings + [f"existing_index_validation={existing_validation['status']}"],
                errors=errors,
                existing_index_status=existing_validation["status"],
                stale_fields=existing_validation["stale_fields"],
                rebuild_reason=existing_validation["rebuild_reason"],
                semantic_validation_result="PASS",
                durability_status=durability_status,
            )

    def _project_index(self, validation: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
        instances: dict[tuple[str, str], dict[str, Any]] = {}
        logical: dict[str, dict[str, Any]] = {}

        for event in events:
            event_type = event["event_type"]
            if event_type == "CHECKPOINT_CREATED":
                continue
            logical_id = event["logical_artifact_id"]
            instance_id = event["artifact_instance_id"]
            key = (logical_id, instance_id)
            instance = instances.setdefault(
                key,
                {
                    "logical_artifact_id": logical_id,
                    "artifact_instance_id": instance_id,
                    "artifact_type": event["artifact_type"],
                    "component": event["component"],
                    "current_status": event["previous_status"],
                    "runtime_use_eligible": False,
                    "physical_path": event["physical_path"],
                    "content_hash": event["content_hash"],
                    "schema_hash": event["schema_hash"],
                    "artifact_set_id": event["artifact_set_id"],
                    "accepted_event_id": None,
                    "accepted_at": None,
                    "accepted_by": None,
                    "last_event_id": event["event_id"],
                    "last_updated_at": event["event_created_at"],
                },
            )
            group = logical.setdefault(
                logical_id,
                {
                    "active_artifact_instance_id": None,
                    "legacy_instances": [],
                    "revoked_instances": [],
                    "replacement_lineage": [],
                    "rollback_lineage": [],
                    "last_instance_id": instance_id,
                },
            )

            if event_type == "PATH_MIGRATED":
                instance["physical_path"] = event["new_physical_path"]
            elif event_type == "PATH_REGISTERED":
                instance["physical_path"] = event["physical_path"]
            elif event_type == "ARTIFACT_REPLACED":
                self._append_unique(group["legacy_instances"], instance_id)
                group["replacement_lineage"].append({"event_id": event["event_id"], "artifact_instance_id": instance_id, "supersedes_event_id": event["supersedes_event_id"]})
                instance["current_status"] = "LEGACY"
                instance["runtime_use_eligible"] = False
                if group["active_artifact_instance_id"] == instance_id:
                    group["active_artifact_instance_id"] = None
            else:
                instance["current_status"] = event["new_status"]
                instance["runtime_use_eligible"] = bool(event["runtime_use_eligible"])
                instance["physical_path"] = event["physical_path"]
                instance["content_hash"] = event["content_hash"]
                instance["schema_hash"] = event["schema_hash"]
                instance["artifact_set_id"] = event["artifact_set_id"]

            if event_type == "ARTIFACT_ACCEPTED":
                instance["accepted_event_id"] = event["event_id"]
                instance["accepted_at"] = event["event_created_at"]
                instance["accepted_by"] = event.get("authority_ref") or event.get("actor_id")
                if event.get("previous_status") == "LEGACY":
                    group["rollback_lineage"].append({"event_id": event["event_id"], "artifact_instance_id": instance_id})
                if event["runtime_use_eligible"]:
                    if group["active_artifact_instance_id"] not in {None, instance_id}:
                        raise RegistryIndexValidationError(f"multiple active instances for {logical_id}")
                    group["active_artifact_instance_id"] = instance_id
            elif event_type == "ARTIFACT_LEGACY":
                self._append_unique(group["legacy_instances"], instance_id)
                if group["active_artifact_instance_id"] == instance_id:
                    group["active_artifact_instance_id"] = None
                instance["runtime_use_eligible"] = False
            elif event_type == "ARTIFACT_REVOKED":
                self._append_unique(group["revoked_instances"], instance_id)
                if group["active_artifact_instance_id"] == instance_id:
                    group["active_artifact_instance_id"] = None
                instance["runtime_use_eligible"] = False

            instance["last_event_id"] = event["event_id"]
            instance["last_updated_at"] = event["event_created_at"]
            group["last_instance_id"] = instance_id

        entries: dict[str, dict[str, Any]] = {}
        for logical_id in sorted(logical):
            group = logical[logical_id]
            active_id = group["active_artifact_instance_id"]
            selected_id = active_id or group["last_instance_id"]
            selected = instances[(logical_id, selected_id)]
            entries[logical_id] = {
                "schema_version": "artifact_registry_entry.v1",
                "logical_artifact_id": logical_id,
                "active_artifact_instance_id": active_id,
                "artifact_type": selected["artifact_type"],
                "component": selected["component"],
                "current_status": selected["current_status"],
                "runtime_use_eligible": bool(selected["runtime_use_eligible"] and selected["current_status"] == "ACCEPTED"),
                "physical_path": selected["physical_path"],
                "content_hash": selected["content_hash"],
                "schema_hash": selected["schema_hash"],
                "artifact_set_id": selected["artifact_set_id"],
                "accepted_event_id": selected["accepted_event_id"] if active_id else None,
                "accepted_at": selected["accepted_at"] if active_id else None,
                "accepted_by": selected["accepted_by"] if active_id else None,
                "legacy_instances": group["legacy_instances"],
                "revoked_instances": group["revoked_instances"],
                "last_event_id": selected["last_event_id"],
                "last_updated_at": selected["last_updated_at"],
                "derived_from_event_log": True,
            }

        index = {
            "schema_version": "artifact_registry_index.v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "event_log_path": str(self.event_log_path),
            "event_log_hash": validation["event_log_hash"],
            "event_count": validation["event_count"],
            "last_event_id": validation["last_event_id"],
            "entry_count": len(entries),
            "entries": entries,
            "index_hash": "",
            "derived_from_event_log": True,
            "builder_version": INDEX_BUILDER_VERSION,
        }
        index["index_hash"] = index_hash(index)
        return index

    def _validate_index(self, index: dict[str, Any]) -> None:
        schemas = load_schemas(self.schema_root)
        schema = schemas["artifact_registry_index.schema.json"]
        issues = schema_validate(index, schema, field_path="$")
        if issues:
            raise RegistryIndexValidationError("; ".join(issue["message"] for issue in issues))
        semantic_issues = index_semantic_issues(index)
        if semantic_issues:
            raise RegistryIndexValidationError("; ".join(semantic_issues))

    def _read_existing_index(self) -> dict[str, Any] | None:
        if not self.index_path.exists():
            return None
        try:
            return read_json(self.index_path)
        except Exception:
            return {"_invalid": True}

    def _validate_existing_index(self, existing: dict[str, Any] | None, warnings: list[str]) -> dict[str, str]:
        if existing is None:
            return {"status": "NOT_FOUND", "stale_fields": [], "rebuild_reason": None}
        if existing.get("_invalid") is True:
            warnings.append("Existing index is not valid JSON and will be replaced from Event Log if validation passes.")
            return {"status": "CORRUPT", "stale_fields": [], "rebuild_reason": "CORRUPT_DERIVED_INDEX"}
        try:
            schemas = load_schemas(self.schema_root)
            schema = schemas["artifact_registry_index.schema.json"]
            issues = schema_validate(existing, schema, field_path="$")
            if issues:
                raise RegistryIndexValidationError("; ".join(issue["message"] for issue in issues))
            if existing.get("index_hash") != index_hash(existing):
                raise RegistryIndexValidationError("index_hash self-consistency failed")
        except Exception as exc:
            warnings.append(f"Existing index validation failed; rebuilding from Event Log: {exc}")
            return {"status": "CORRUPT", "stale_fields": [], "rebuild_reason": "CORRUPT_DERIVED_INDEX"}
        return {"status": "VALID_CURRENT", "stale_fields": [], "rebuild_reason": None}

    def _classify_existing_index(self, existing: dict[str, Any] | None, new_index: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
        base = self._validate_existing_index(existing, warnings) if existing is not None else {"status": "NOT_FOUND", "stale_fields": [], "rebuild_reason": None}
        if base["status"] in {"NOT_FOUND", "CORRUPT"}:
            return base
        fields = ("event_log_hash", "event_count", "last_event_id", "entry_count", "index_hash")
        stale_fields = [field for field in fields if existing.get(field) != new_index.get(field)]
        if stale_fields:
            warnings.append("Existing index is stale and will be rebuilt from Event Log: " + ",".join(stale_fields))
            return {"status": "STALE", "stale_fields": stale_fields, "rebuild_reason": "STALE_DERIVED_INDEX"}
        semantic_issues = index_semantic_issues(existing)
        if semantic_issues:
            warnings.append("Existing index semantic validation failed; rebuilding from Event Log: " + "; ".join(semantic_issues))
            return {"status": "CORRUPT", "stale_fields": [], "rebuild_reason": "CORRUPT_DERIVED_INDEX"}
        return {"status": "VALID_CURRENT", "stale_fields": [], "rebuild_reason": None}

    def _is_no_change(self, existing: dict[str, Any] | None, new_index: dict[str, Any]) -> bool:
        if not existing or existing.get("_invalid") is True:
            return False
        keys = ("event_log_hash", "event_count", "last_event_id", "entry_count", "index_hash")
        return all(existing.get(key) == new_index.get(key) for key in keys)

    def _write_index_atomic(self, index: dict[str, Any]) -> str:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = canonical_json(index, include_newline=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{self.index_path.name}.", suffix=".tmp", dir=str(self.index_path.parent))
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            loaded = json.loads(temp_path.read_text(encoding="utf-8"))
            self._validate_index(loaded)
            os.replace(temp_path, self.index_path)
            dir_fd = os.open(self.index_path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            except Exception as exc:
                raise RegistryIndexDurabilityError("parent directory fsync failed after index replace; durability requires review", index_replaced=True) from exc
            finally:
                os.close(dir_fd)
            return "DURABLE"
        except Exception:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
            raise

    def _build_result(
        self,
        *,
        build_status: str,
        overall_result: str,
        failure_class: str,
        validation: dict[str, Any],
        index_hash: str | None,
        entry_count: int,
        previous_index_hash: str | None,
        index_replaced: bool,
        warnings: list[str],
        errors: list[str],
        existing_index_status: str = "UNKNOWN",
        stale_fields: list[str] | None = None,
        rebuild_reason: str | None = None,
        semantic_validation_result: str = "NOT_RUN",
        durability_status: str = "NOT_APPLICABLE",
    ) -> dict[str, Any]:
        return {
            "schema_version": "artifact_registry_index_build_result.v1",
            "build_id": f"index-build-{uuid.uuid4()}",
            "built_at": datetime.now(timezone.utc).isoformat(),
            "builder_version": INDEX_BUILDER_VERSION,
            "event_log_path": str(self.event_log_path),
            "event_log_hash": validation.get("event_log_hash"),
            "event_count": validation.get("event_count", 0),
            "last_event_id": validation.get("last_event_id"),
            "entry_count": entry_count,
            "index_path": str(self.index_path),
            "index_hash": index_hash,
            "build_status": build_status,
            "overall_result": overall_result,
            "failure_class": failure_class,
            "validation_ref": "FullEventLogValidator",
            "previous_index_hash": previous_index_hash,
            "index_replaced": index_replaced,
            "warnings": warnings,
            "errors": errors,
            "recommended_action": "No action required." if overall_result == "PASS" else "Review errors before rebuilding index.",
            "writer_integration": "NOT_IMPLEMENTED",
            "checkpoint_writer": "NOT_IMPLEMENTED",
            "existing_index_status": existing_index_status,
            "stale_fields": stale_fields or [],
            "rebuild_reason": rebuild_reason,
            "semantic_validation_result": semantic_validation_result,
            "durability_status": durability_status,
        }

    def _resolve(self, path: Path | str) -> Path:
        value = Path(path)
        return value if value.is_absolute() else self.repo_root / value

    @staticmethod
    def _append_unique(items: list[str], value: str) -> None:
        if value not in items:
            items.append(value)


def canonical_json(payload: dict[str, Any], *, include_newline: bool = False) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return text + "\n" if include_newline else text


def index_hash(index: dict[str, Any]) -> str:
    payload = {key: value for key, value in index.items() if key not in {"index_hash", "generated_at"}}
    return stable_json_hash(payload)


def index_semantic_issues(index: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    entries = index.get("entries")
    if not isinstance(entries, dict):
        return ["entries must be an object"]
    if index.get("entry_count") != len(entries):
        issues.append("entry_count must equal len(entries)")
    if index.get("derived_from_event_log") is not True:
        issues.append("derived_from_event_log must be true")
    event_count = index.get("event_count")
    last_event_id = index.get("last_event_id")
    if event_count == 0 and last_event_id is not None:
        issues.append("last_event_id must be null when event_count is zero")
    if isinstance(event_count, int) and event_count > 0 and last_event_id is None:
        issues.append("last_event_id must be present when event_count is nonzero")
    if index.get("index_hash") and index.get("index_hash") != index_hash(index):
        issues.append("index_hash self-consistency failed")
    for key, entry in entries.items():
        if not isinstance(entry, dict):
            issues.append(f"entry {key} must be an object")
            continue
        if entry.get("logical_artifact_id") != key:
            issues.append(f"entry key must match logical_artifact_id: {key}")
        status = entry.get("current_status")
        eligible = entry.get("runtime_use_eligible") is True
        if eligible and status != "ACCEPTED":
            issues.append(f"runtime_use_eligible requires ACCEPTED status: {key}")
        if status in {"LEGACY", "REVOKED", "REJECTED"} and eligible:
            issues.append(f"{status} entry must not be runtime eligible: {key}")
        if eligible and not entry.get("active_artifact_instance_id"):
            issues.append(f"eligible entry requires active_artifact_instance_id: {key}")
        for field in ("content_hash", "schema_hash"):
            value = entry.get(field)
            if value is not None and not _sha256_like(value):
                issues.append(f"{field} must be SHA-256 or null for {key}")
    if index.get("event_log_hash") is not None and not _sha256_like(index.get("event_log_hash")):
        issues.append("event_log_hash must be SHA-256")
    return issues


def _sha256_like(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    raw = value[7:] if value.startswith("sha256:") else value
    return len(raw) == 64 and all(ch in "0123456789abcdef" for ch in raw)


def write_build_outputs(result: dict[str, Any], output_root: Path, *, repo_root: Path, event_log_path: Path) -> None:
    ensure_safe_output_root(event_log_path.parent, output_root, repo_root=repo_root)
    atomic_write_text(output_root / "build_result.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    summary = {
        "schema_version": "phase16ad_index_build_summary.v1",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "overall_result": result["overall_result"],
        "failure_class": result["failure_class"],
        "build_status": result["build_status"],
        "event_count": result["event_count"],
        "entry_count": result["entry_count"],
        "last_event_id": result["last_event_id"],
        "index_hash": result["index_hash"],
        "index_replaced": result["index_replaced"],
    }
    atomic_write_text(output_root / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    atomic_write_text(output_root / "audit.md", render_audit(result))


def render_audit(result: dict[str, Any]) -> str:
    lines = [
        "# Materialized Artifact Registry Index Build Audit",
        "",
        f"- builder_version: {result['builder_version']}",
        f"- build_status: {result['build_status']}",
        f"- overall_result: {result['overall_result']}",
        f"- failure_class: {result['failure_class']}",
        f"- event_count: {result['event_count']}",
        f"- entry_count: {result['entry_count']}",
        f"- last_event_id: {result['last_event_id']}",
        f"- index_hash: {result['index_hash']}",
        f"- index_replaced: {result['index_replaced']}",
        f"- writer_integration: {result['writer_integration']}",
        f"- checkpoint_writer: {result['checkpoint_writer']}",
        "",
        "## Warnings",
    ]
    lines.extend(f"- {item}" for item in result["warnings"])
    lines.extend(["", "## Errors"])
    lines.extend(f"- {item}" for item in result["errors"])
    lines.append("")
    return "\n".join(lines)


def run_index_build(
    *,
    registry_root: Path = DEFAULT_REGISTRY_ROOT,
    event_log: Path = DEFAULT_EVENT_LOG_PATH,
    output: Path = Path("reports/phase16_registry_index_build"),
    repo_root: Path | None = None,
    lock_timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    repo_root = repo_root or Path.cwd()
    builder = MaterializedRegistryIndexBuilder(
        registry_root=registry_root,
        event_log_path=event_log,
        repo_root=repo_root,
        lock_timeout_seconds=lock_timeout_seconds,
    )
    result = builder.build()
    write_build_outputs(result, output, repo_root=repo_root, event_log_path=builder.event_log_path)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the derived Materialized Artifact Registry Index.")
    parser.add_argument("--registry-root", default=str(DEFAULT_REGISTRY_ROOT))
    parser.add_argument("--event-log", default=str(DEFAULT_EVENT_LOG_PATH))
    parser.add_argument("--output", default="reports/phase16_registry_index_build")
    args = parser.parse_args(argv)
    try:
        result = run_index_build(registry_root=Path(args.registry_root), event_log=Path(args.event_log), output=Path(args.output), repo_root=Path.cwd())
    except ValidationSafetyError as exc:
        print(f"VALIDATION_ERROR: {exc}")
        return 2
    print(json.dumps({key: result[key] for key in ("overall_result", "failure_class", "build_status", "event_count", "entry_count", "index_hash")}, sort_keys=True))
    return 0 if result["overall_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
