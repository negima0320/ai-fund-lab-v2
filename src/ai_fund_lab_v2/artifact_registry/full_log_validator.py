from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.artifact_registry.inventory import stable_json_hash
from ai_fund_lab_v2.artifact_registry.validator import (
    ValidationSafetyError,
    add_check,
    classify_failure,
    ensure_safe_output_root,
    load_schemas,
    make_result,
    recommended_action,
    validate_registry_event,
)
from ai_fund_lab_v2.artifact_registry.writer import event_fingerprint


FULL_LOG_VALIDATOR_VERSION = "phase16ac_full_event_log_validator_v1"
DEFAULT_EVENT_LOG_PATH = Path(".runtime/artifact_registry/events/registry_events.jsonl")


class FullEventLogValidationError(RuntimeError):
    pass


class FullEventLogValidator:
    def __init__(
        self,
        *,
        event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH,
        registry_root: Path | str = ".runtime/artifact_registry",
        schema_root: Path | str = "docs/02_architecture/schemas",
        evidence_root: Path | str | None = None,
        repo_root: Path | str | None = None,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
        self.event_log_path = self._resolve(event_log_path)
        self.registry_root = self._resolve(registry_root)
        self.schema_root = self._resolve(schema_root)
        self.evidence_root = self._resolve(evidence_root) if evidence_root is not None else None

    def validate(self, *, include_events: bool = False) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        errors: list[str] = []
        warnings: list[str] = []
        events: list[dict[str, Any]] = []
        event_log_hash: str | None = None
        last_event_id: str | None = None

        if not self.event_log_path.exists() or not self.event_log_path.is_file():
            add_check(checks, False, "input_path", "event log path is a readable file", "$.event_log_path", failure_class="VALIDATION_ERROR")
            errors.append(f"event log path is not a file: {self.event_log_path}")
            return self._result(checks, errors, warnings, event_count=0, last_event_id=None, event_log_hash=None, events=[] if include_events else None)
        if not self.schema_root.exists() or not self.schema_root.is_dir():
            add_check(checks, False, "schema_root", "schema root is a directory", "$.schema_root", failure_class="VALIDATION_ERROR")
            errors.append(f"schema root is not a directory: {self.schema_root}")
            return self._result(checks, errors, warnings, event_count=0, last_event_id=None, event_log_hash=None, events=[] if include_events else None)

        raw = self.event_log_path.read_bytes()
        event_log_hash = hashlib.sha256(raw).hexdigest()
        add_check(checks, True, "event_log_hash", "event log byte hash calculated", "$.event_log_hash")

        events = self._parse_event_log(raw, checks, errors)
        if classify_failure(checks) in {"HALT", "VALIDATION_ERROR"}:
            return self._result(checks, errors, warnings, event_count=len(events), last_event_id=None, event_log_hash=event_log_hash, events=[] if include_events else None)

        if not events:
            add_check(checks, True, "empty_registry", "empty event log is valid", "$.event_count")

        schemas = load_schemas(self.schema_root)
        self._validate_all_events(events, checks, errors, warnings, schemas)
        self._validate_duplicates(events, checks, errors)
        self._validate_replay(events, checks, errors)

        if events:
            last_event_id = str(events[-1].get("event_id"))
        return self._result(checks, errors, warnings, event_count=len(events), last_event_id=last_event_id, event_log_hash=event_log_hash, events=events if include_events else None)

    def _parse_event_log(self, raw: bytes, checks: list[dict[str, Any]], errors: list[str]) -> list[dict[str, Any]]:
        if raw.startswith(b"\xef\xbb\xbf"):
            add_check(checks, False, "file_structure", "UTF-8 BOM is prohibited", "$.bytes[0:3]", failure_class="HALT")
            errors.append("UTF-8 BOM is prohibited.")
            return []

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            add_check(checks, False, "file_structure", "event log is valid UTF-8", "$.bytes", failure_class="HALT")
            errors.append(f"invalid UTF-8 at byte {exc.start}")
            return []
        add_check(checks, True, "file_structure", "event log is valid UTF-8", "$.bytes")

        if raw and not raw.endswith(b"\n"):
            add_check(checks, False, "file_structure", "every event line ends with newline", "$.lines[-1]", failure_class="HALT")
            errors.append("partial trailing line without newline.")
            return []
        add_check(checks, True, "file_structure", "all event lines are newline terminated", "$.lines")

        events: list[dict[str, Any]] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            field_path = f"$.lines[{line_number}]"
            if not line.strip():
                add_check(checks, False, "file_structure", "blank lines are prohibited", field_path, failure_class="HALT")
                errors.append(f"blank line at {line_number}")
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                add_check(checks, False, "file_structure", "line is valid JSON", field_path, failure_class="HALT")
                errors.append(f"invalid JSON at line {line_number}: {exc.msg}")
                continue
            if not isinstance(payload, dict):
                add_check(checks, False, "file_structure", "line JSON value is an object", field_path, failure_class="HALT")
                errors.append(f"non-object JSON row at line {line_number}")
                continue
            add_check(checks, True, "file_structure", "line is one JSON object", field_path)
            payload["_line_number"] = line_number
            events.append(payload)
        return events

    def _validate_all_events(
        self,
        events: list[dict[str, Any]],
        checks: list[dict[str, Any]],
        errors: list[str],
        warnings: list[str],
        schemas: dict[str, dict[str, Any]],
    ) -> None:
        for event in events:
            line_number = event["_line_number"]
            event_for_validation = {key: value for key, value in event.items() if key != "_line_number"}
            result = validate_registry_event(
                event_for_validation,
                schemas=schemas,
                repo_root=self.repo_root,
                subject_ref=f"{self.event_log_path}:{line_number}",
            )
            if result["overall_result"] != "PASS" or result["failure_class"] != "NONE":
                add_check(
                    checks,
                    False,
                    "event_schema_contract",
                    f"event at physical line {line_number} passes registry event validator",
                    f"$.lines[{line_number}]",
                    failure_class="HALT",
                )
                errors.extend(f"line {line_number}: {item}" for item in result["errors"])
                warnings.extend(f"line {line_number}: {item}" for item in result["warnings"])
            else:
                add_check(checks, True, "event_schema_contract", f"event at physical line {line_number} passes registry event validator", f"$.lines[{line_number}]")

    def _validate_duplicates(self, events: list[dict[str, Any]], checks: list[dict[str, Any]], errors: list[str]) -> None:
        seen_event_ids: dict[str, int] = {}
        seen_fingerprints: dict[str, int] = {}
        for event in events:
            line_number = int(event["_line_number"])
            event_id = str(event.get("event_id"))
            if event_id in seen_event_ids:
                add_check(checks, False, "duplicate_event_id", f"duplicate event_id {event_id}", f"$.lines[{line_number}].event_id", failure_class="HALT")
                errors.append(f"duplicate event_id {event_id} at lines {seen_event_ids[event_id]} and {line_number}")
            else:
                seen_event_ids[event_id] = line_number

            fingerprint = event_fingerprint(event)
            if fingerprint in seen_fingerprints:
                add_check(checks, False, "duplicate_fingerprint", f"duplicate event fingerprint {fingerprint}", f"$.lines[{line_number}]", failure_class="HALT")
                errors.append(f"duplicate fingerprint {fingerprint} at lines {seen_fingerprints[fingerprint]} and {line_number}")
            else:
                seen_fingerprints[fingerprint] = line_number

        add_check(checks, True, "duplicate_event_id", "full log event_id uniqueness scan completed", "$.event_id")
        add_check(checks, True, "duplicate_fingerprint", "full log fingerprint uniqueness scan completed", "$.fingerprint")

    def _validate_replay(self, events: list[dict[str, Any]], checks: list[dict[str, Any]], errors: list[str]) -> None:
        state_by_instance: dict[tuple[str, str], dict[str, Any]] = {}
        identity_by_instance: dict[str, dict[str, Any]] = {}
        active_eligible_by_logical: dict[str, str] = {}

        for event in events:
            line_number = int(event["_line_number"])
            event_type = event.get("event_type")
            logical_id = event.get("logical_artifact_id")
            instance_id = event.get("artifact_instance_id")
            if event_type == "CHECKPOINT_CREATED":
                add_check(checks, True, "lifecycle_replay", "checkpoint event does not affect artifact lifecycle", f"$.lines[{line_number}]")
                continue
            if not logical_id or not instance_id:
                add_check(checks, False, "identity_replay", "artifact event has logical and instance identity", f"$.lines[{line_number}]", failure_class="HALT")
                errors.append(f"missing artifact identity at line {line_number}")
                continue

            key = (str(logical_id), str(instance_id))
            current = state_by_instance.get(key, {})
            current_status = current.get("status")
            previous_status = event.get("previous_status")
            new_status = event.get("new_status")

            if previous_status != current_status:
                add_check(checks, False, "lifecycle_replay", f"previous_status matches replay state at line {line_number}", f"$.lines[{line_number}].previous_status", failure_class="HALT")
                errors.append(f"line {line_number} previous_status={previous_status!r} does not match replay state {current_status!r}")
            else:
                add_check(checks, True, "lifecycle_replay", f"previous_status matches replay state at line {line_number}", f"$.lines[{line_number}].previous_status")

            if current_status == "REVOKED" and new_status != "REVOKED":
                add_check(checks, False, "lifecycle_replay", "REVOKED instance must not return to active lifecycle", f"$.lines[{line_number}].new_status", failure_class="HALT")
                errors.append(f"line {line_number} attempts to move REVOKED instance to {new_status}")

            self._validate_identity(event, identity_by_instance, checks, errors)
            self._validate_path_event(event, current, checks, errors)

            eligible = bool(event.get("runtime_use_eligible"))
            if eligible and new_status != "ACCEPTED":
                add_check(checks, False, "runtime_eligibility_replay", "runtime_use_eligible=true requires ACCEPTED replay status", f"$.lines[{line_number}].runtime_use_eligible", failure_class="HALT")
                errors.append(f"line {line_number} has runtime_use_eligible=true for {new_status}")

            previous_active = active_eligible_by_logical.get(str(logical_id))
            if new_status in {"LEGACY", "REVOKED", "REJECTED"} and previous_active == str(instance_id):
                active_eligible_by_logical.pop(str(logical_id), None)
            if new_status == "ACCEPTED" and eligible:
                if previous_active is not None and previous_active != str(instance_id):
                    add_check(checks, False, "active_instance_uniqueness", "only one active eligible instance per logical_artifact_id", f"$.lines[{line_number}]", failure_class="HALT")
                    errors.append(f"multiple active eligible instances for {logical_id}: {previous_active}, {instance_id}")
                active_eligible_by_logical[str(logical_id)] = str(instance_id)

            if event_type in {"PATH_REGISTERED", "PATH_MIGRATED", "ELIGIBILITY_CHANGED"}:
                status_after = current_status if new_status == previous_status else new_status
            else:
                status_after = new_status
            state_by_instance[key] = {
                "status": status_after,
                "physical_path": event.get("new_physical_path") if event_type == "PATH_MIGRATED" else event.get("physical_path"),
                "runtime_use_eligible": eligible,
            }

        add_check(checks, True, "lifecycle_replay", "physical line order lifecycle replay completed", "$.lines")
        add_check(checks, True, "identity_replay", "identity consistency replay completed", "$.lines")
        add_check(checks, True, "runtime_eligibility_replay", "runtime eligibility replay completed", "$.lines")
        add_check(checks, True, "active_instance_uniqueness", "active eligible instance uniqueness scan completed", "$.logical_artifact_id")

    def _validate_identity(
        self,
        event: dict[str, Any],
        identity_by_instance: dict[str, dict[str, Any]],
        checks: list[dict[str, Any]],
        errors: list[str],
    ) -> None:
        line_number = int(event["_line_number"])
        instance_id = str(event.get("artifact_instance_id"))
        fields = ("logical_artifact_id", "artifact_type", "component", "content_hash", "schema_hash", "artifact_set_id")
        existing = identity_by_instance.setdefault(instance_id, {})
        for field in fields:
            value = event.get(field)
            if value is None:
                continue
            if field not in existing:
                existing[field] = value
            elif field == "content_hash" and event.get("event_type") == "ARTIFACT_ACCEPTED":
                existing[field] = value
            elif (
                field == "content_hash"
                and event.get("event_type") == "ARTIFACT_VALIDATED"
                and event.get("artifact_type") == "ARTIFACT_SET"
                and event.get("runtime_use_eligible") is False
            ):
                existing[field] = value
            elif existing[field] != value:
                add_check(checks, False, "identity_replay", f"{field} must not mutate for artifact_instance_id", f"$.lines[{line_number}].{field}", failure_class="HALT")
                errors.append(f"line {line_number} mutates {field} for {instance_id}: {existing[field]!r} -> {value!r}")

    def _validate_path_event(
        self,
        event: dict[str, Any],
        current: dict[str, Any],
        checks: list[dict[str, Any]],
        errors: list[str],
    ) -> None:
        event_type = event.get("event_type")
        if event_type not in {"PATH_REGISTERED", "PATH_MIGRATED"}:
            return
        line_number = int(event["_line_number"])
        if event.get("previous_status") != event.get("new_status"):
            add_check(checks, False, "path_event_replay", "path event must not change status", f"$.lines[{line_number}].new_status", failure_class="HALT")
            errors.append(f"line {line_number} path event changes status")
        if bool(event.get("runtime_use_eligible")) != bool(current.get("runtime_use_eligible", False)):
            add_check(checks, False, "path_event_replay", "path event must not change runtime_use_eligible", f"$.lines[{line_number}].runtime_use_eligible", failure_class="HALT")
            errors.append(f"line {line_number} path event changes runtime eligibility")
        if event_type == "PATH_MIGRATED":
            previous_path = event.get("previous_physical_path")
            new_path = event.get("new_physical_path")
            current_path = current.get("physical_path")
            ok = bool(previous_path and new_path and previous_path != new_path and previous_path == current_path)
            add_check(checks, ok, "path_event_replay", "PATH_MIGRATED previous path matches replay state", f"$.lines[{line_number}].previous_physical_path", failure_class="HALT")
            if not ok:
                errors.append(f"line {line_number} PATH_MIGRATED previous path mismatch: {previous_path!r} != {current_path!r}")
        else:
            add_check(checks, True, "path_event_replay", "PATH_REGISTERED path replay valid", f"$.lines[{line_number}].physical_path")

    def _result(
        self,
        checks: list[dict[str, Any]],
        errors: list[str],
        warnings: list[str],
        *,
        event_count: int,
        last_event_id: str | None,
        event_log_hash: str | None,
        events: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        base = make_result(
            subject_type="REGISTRY_EVENT_LOG",
            subject_ref=str(self.event_log_path),
            validated_schema_version="artifact_registry_event.v1",
            checks=checks,
            errors=errors,
            warnings=warnings,
            evidence_refs=[str(self.event_log_path)],
            recommended_action=recommended_action(checks),
        )
        base["validator_version"] = FULL_LOG_VALIDATOR_VERSION
        base.update(
            {
                "event_count": event_count,
                "last_event_id": last_event_id,
                "event_log_hash": event_log_hash,
                "validation_scope": "FULL_LOG_VALIDATION",
                "empty_registry": event_count == 0,
                "writer_integration": "NOT_IMPLEMENTED",
                "index_builder": "NOT_IMPLEMENTED",
                "event_ordering": "PHYSICAL_LINE_ORDER",
            }
        )
        if events is not None:
            base["events"] = [{key: value for key, value in event.items() if key != "_line_number"} for event in events]
        return base

    def _resolve(self, path: Path | str) -> Path:
        value = Path(path)
        return value if value.is_absolute() else self.repo_root / value


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
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


def write_validation_outputs(result: dict[str, Any], output_root: Path, *, repo_root: Path, input_path: Path) -> None:
    ensure_safe_output_root(input_path.parent, output_root, repo_root=repo_root)
    atomic_write_text(output_root / "full_log_validation_result.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    summary = {
        "schema_version": "phase16ac_full_log_validation_summary.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "overall_result": result["overall_result"],
        "failure_class": result["failure_class"],
        "event_count": result["event_count"],
        "last_event_id": result["last_event_id"],
        "event_log_hash": result["event_log_hash"],
        "empty_registry": result["empty_registry"],
    }
    atomic_write_text(output_root / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    audit = render_audit(result)
    atomic_write_text(output_root / "audit.md", audit)


def render_audit(result: dict[str, Any]) -> str:
    lines = [
        "# Artifact Registry Full Event Log Validation Audit",
        "",
        f"- validator_version: {result['validator_version']}",
        f"- subject_ref: {result['subject_ref']}",
        f"- overall_result: {result['overall_result']}",
        f"- failure_class: {result['failure_class']}",
        f"- event_count: {result['event_count']}",
        f"- last_event_id: {result['last_event_id']}",
        f"- event_log_hash: {result['event_log_hash']}",
        f"- empty_registry: {result['empty_registry']}",
        f"- writer_integration: {result['writer_integration']}",
        f"- index_builder: {result['index_builder']}",
        "",
        "## Errors",
    ]
    lines.extend(f"- {item}" for item in result["errors"])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in result["warnings"])
    lines.extend(["", "## Checks"])
    for check in result["checks"]:
        lines.append(f"- {check['result']} / {check['check_type']}: {check['message']}")
    lines.append("")
    return "\n".join(lines)


def run_full_log_validation(
    *,
    event_log: Path,
    output: Path,
    registry_root: Path = Path(".runtime/artifact_registry"),
    schema_root: Path = Path("docs/02_architecture/schemas"),
    repo_root: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root or Path.cwd()
    before_hash = hashlib.sha256(event_log.read_bytes()).hexdigest() if event_log.exists() else None
    validator = FullEventLogValidator(event_log_path=event_log, registry_root=registry_root, schema_root=schema_root, repo_root=repo_root)
    result = validator.validate()
    after_hash = hashlib.sha256(event_log.read_bytes()).hexdigest() if event_log.exists() else None
    result["event_log_before_hash"] = before_hash
    result["event_log_after_hash"] = after_hash
    result["event_log_bytes_unchanged"] = before_hash == after_hash
    write_validation_outputs(result, output, repo_root=repo_root, input_path=event_log)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run read-only full Artifact Registry Event Log validation.")
    parser.add_argument("--event-log", default=str(DEFAULT_EVENT_LOG_PATH))
    parser.add_argument("--registry-root", default=".runtime/artifact_registry")
    parser.add_argument("--schema-root", default="docs/02_architecture/schemas")
    parser.add_argument("--output", default="reports/phase16_registry_full_log_validation")
    args = parser.parse_args(argv)
    try:
        result = run_full_log_validation(
            event_log=Path(args.event_log),
            registry_root=Path(args.registry_root),
            schema_root=Path(args.schema_root),
            output=Path(args.output),
            repo_root=Path.cwd(),
        )
    except ValidationSafetyError as exc:
        print(f"VALIDATION_ERROR: {exc}")
        return 2
    print(json.dumps({key: result[key] for key in ("overall_result", "failure_class", "event_count", "event_log_hash")}, sort_keys=True))
    return 0 if result["failure_class"] == "NONE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
