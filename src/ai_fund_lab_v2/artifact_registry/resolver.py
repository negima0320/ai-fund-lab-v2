from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.artifact_registry.checkpoint_writer import LATEST_RELATIVE_PATH, checkpoint_hash
from ai_fund_lab_v2.artifact_registry.full_log_validator import DEFAULT_EVENT_LOG_PATH, FullEventLogValidator
from ai_fund_lab_v2.artifact_registry.index_builder import INDEX_RELATIVE_PATH, index_hash, index_semantic_issues
from ai_fund_lab_v2.artifact_registry.validator import load_schemas, read_json, schema_validate
from ai_fund_lab_v2.artifact_registry.writer import DEFAULT_REGISTRY_ROOT


RESOLVER_VERSION = "phase16au_registry_artifact_resolver_v1"
SUPPORTED_ARTIFACT_SET_TYPES = {
    "CANDIDATE_AI_SET",
    "OPPORTUNITY_AI_SET",
    "POSITION_MANAGEMENT_POLICY_SET",
    "CAPITAL_ALLOCATION_POLICY_SET",
    "FEATURE_SCHEMA_SET",
}


class RegistryArtifactResolverError(RuntimeError):
    pass


class RegistryArtifactResolveHalt(RegistryArtifactResolverError):
    pass


@dataclass(frozen=True)
class RegistryArtifactResolver:
    registry_root: Path = DEFAULT_REGISTRY_ROOT
    event_log: Path = DEFAULT_EVENT_LOG_PATH
    index_path: Path | None = None
    schema_root: Path = Path("docs/02_architecture/schemas")
    repo_root: Path = Path.cwd()

    def resolve(self, artifact_set_type: str) -> dict[str, Any]:
        if artifact_set_type not in SUPPORTED_ARTIFACT_SET_TYPES:
            raise RegistryArtifactResolveHalt(f"unsupported artifact_set_type: {artifact_set_type}")
        paths = self._paths()
        validation = self._validate_event_log(paths)
        index = self._read_and_validate_index(paths, validation)
        checkpoint = self._read_and_validate_checkpoint(paths, validation, index)
        eligible_entries = [
            entry
            for entry in (index.get("entries") or {}).values()
            if entry.get("artifact_set_id")
            and entry.get("current_status") == "ACCEPTED"
            and entry.get("runtime_use_eligible") is True
        ]
        matching_entries = [
            entry
            for entry in eligible_entries
            if any(
                event.get("event_id") == entry.get("accepted_event_id")
                and event.get("artifact_set_type") == artifact_set_type
                for event in validation["events"]
            )
        ]
        if not matching_entries:
            raise RegistryArtifactResolveHalt(f"accepted artifact set not found: {artifact_set_type}")
        if len(matching_entries) != 1:
            raise RegistryArtifactResolveHalt(f"multiple active accepted artifact sets found for {artifact_set_type}: {len(matching_entries)}")
        entry = matching_entries[0]
        accepted = next(
            event
            for event in validation["events"]
            if event.get("event_id") == entry.get("accepted_event_id")
        )
        set_id = str(accepted.get("logical_artifact_id") or accepted.get("artifact_set_id") or "")
        entry = (index.get("entries") or {}).get(set_id)
        if not isinstance(entry, dict):
            raise RegistryArtifactResolveHalt(f"index entry not found for accepted set: {set_id}")
        self._validate_entry(entry, accepted)
        report = self._read_acceptance_report(accepted)
        manifest = self._read_manifest(report, accepted)
        self._validate_manifest(manifest, accepted, entry)
        return self._result(artifact_set_type, set_id, entry, accepted, manifest, report, checkpoint, validation, index)

    def _paths(self) -> dict[str, Path]:
        repo_root = Path(self.repo_root)
        registry_root = self.registry_root if self.registry_root.is_absolute() else repo_root / self.registry_root
        event_log = self.event_log if self.event_log.is_absolute() else repo_root / self.event_log
        index_path = self.index_path or registry_root / INDEX_RELATIVE_PATH
        if not index_path.is_absolute():
            index_path = repo_root / index_path
        schema_root = self.schema_root if self.schema_root.is_absolute() else repo_root / self.schema_root
        return {
            "repo_root": repo_root,
            "registry_root": registry_root,
            "event_log": event_log,
            "index_path": index_path,
            "schema_root": schema_root,
            "latest_checkpoint": registry_root / LATEST_RELATIVE_PATH,
        }

    def _validate_event_log(self, paths: dict[str, Path]) -> dict[str, Any]:
        validator = FullEventLogValidator(
            event_log_path=paths["event_log"],
            registry_root=paths["registry_root"],
            schema_root=paths["schema_root"],
            repo_root=paths["repo_root"],
        )
        result = validator.validate(include_events=True)
        if result.get("overall_result") != "PASS" or result.get("failure_class") != "NONE":
            raise RegistryArtifactResolveHalt("event log validation did not PASS/NONE")
        return result

    def _read_and_validate_index(self, paths: dict[str, Path], validation: dict[str, Any]) -> dict[str, Any]:
        if not paths["index_path"].is_file():
            raise RegistryArtifactResolveHalt(f"materialized index missing: {paths['index_path']}")
        try:
            index = read_json(paths["index_path"])
        except Exception as exc:
            raise RegistryArtifactResolveHalt("materialized index corrupt or unreadable") from exc
        schemas = load_schemas(paths["schema_root"])
        issues = schema_validate(index, schemas["artifact_registry_index.schema.json"], field_path="$")
        semantic = index_semantic_issues(index)
        if issues or semantic:
            messages = [issue["message"] for issue in issues] + semantic
            raise RegistryArtifactResolveHalt("materialized index validation failed: " + "; ".join(messages))
        if index.get("index_hash") != index_hash(index):
            raise RegistryArtifactResolveHalt("materialized index hash mismatch")
        expected = {
            "event_log_hash": validation["event_log_hash"],
            "event_count": validation["event_count"],
            "last_event_id": validation["last_event_id"],
        }
        for field, value in expected.items():
            if index.get(field) != value:
                raise RegistryArtifactResolveHalt(f"materialized index is stale: {field}")
        return index

    def _read_and_validate_checkpoint(self, paths: dict[str, Path], validation: dict[str, Any], index: dict[str, Any]) -> dict[str, Any]:
        if not paths["latest_checkpoint"].is_file():
            raise RegistryArtifactResolveHalt("latest checkpoint missing")
        try:
            latest = read_json(paths["latest_checkpoint"])
            checkpoint_path = Path(latest["checkpoint_path"])
            if not checkpoint_path.is_absolute():
                checkpoint_path = paths["repo_root"] / checkpoint_path
            checkpoint = read_json(checkpoint_path)
        except Exception as exc:
            raise RegistryArtifactResolveHalt("latest checkpoint corrupt or unreadable") from exc
        if checkpoint.get("checkpoint_hash") != checkpoint_hash(checkpoint):
            raise RegistryArtifactResolveHalt("checkpoint hash mismatch")
        if latest.get("checkpoint_hash") != checkpoint.get("checkpoint_hash"):
            raise RegistryArtifactResolveHalt("latest checkpoint hash mismatch")
        checks = {
            "event_log_hash": validation["event_log_hash"],
            "event_count": validation["event_count"],
            "last_event_id": validation["last_event_id"],
            "materialized_index_hash": index["index_hash"],
            "entry_count": index["entry_count"],
        }
        for field, value in checks.items():
            if checkpoint.get(field) != value:
                raise RegistryArtifactResolveHalt(f"checkpoint mismatch: {field}")
        return {"latest_ref": latest, "checkpoint": checkpoint, "checkpoint_path": str(checkpoint_path)}

    def _validate_entry(self, entry: dict[str, Any], accepted: dict[str, Any]) -> None:
        if entry.get("current_status") != "ACCEPTED":
            raise RegistryArtifactResolveHalt(f"entry status is not ACCEPTED: {entry.get('current_status')}")
        if entry.get("runtime_use_eligible") is not True:
            raise RegistryArtifactResolveHalt("entry runtime_use_eligible is not true")
        if entry.get("accepted_event_id") != accepted.get("event_id"):
            raise RegistryArtifactResolveHalt("entry accepted_event_id mismatch")
        if entry.get("active_artifact_instance_id") != accepted.get("artifact_instance_id"):
            raise RegistryArtifactResolveHalt("entry active_artifact_instance_id mismatch")
        for field in ("content_hash", "schema_hash", "artifact_type", "component", "artifact_set_id"):
            if entry.get(field) != accepted.get(field):
                raise RegistryArtifactResolveHalt(f"entry/event mismatch: {field}")

    def _read_acceptance_report(self, accepted: dict[str, Any]) -> dict[str, Any]:
        ref = accepted.get("acceptance_report_ref")
        if not ref:
            raise RegistryArtifactResolveHalt("accepted event missing acceptance_report_ref")
        try:
            return read_json(Path(str(ref)))
        except Exception as exc:
            raise RegistryArtifactResolveHalt(f"acceptance report unreadable: {ref}") from exc

    def _read_manifest(self, report: dict[str, Any], accepted: dict[str, Any]) -> dict[str, Any]:
        ref = report.get("artifact_set_manifest_ref")
        if not ref:
            raise RegistryArtifactResolveHalt("acceptance report missing artifact_set_manifest_ref")
        try:
            return read_json(Path(str(ref)))
        except Exception as exc:
            raise RegistryArtifactResolveHalt(f"artifact set manifest unreadable: {ref}") from exc

    def _validate_manifest(self, manifest: dict[str, Any], accepted: dict[str, Any], entry: dict[str, Any]) -> None:
        if manifest.get("artifact_set_id") != accepted.get("artifact_set_id"):
            raise RegistryArtifactResolveHalt("manifest artifact_set_id mismatch")
        if manifest.get("artifact_set_type") != accepted.get("artifact_set_type"):
            raise RegistryArtifactResolveHalt("manifest artifact_set_type mismatch")
        if manifest.get("artifact_set_hash") != accepted.get("content_hash"):
            raise RegistryArtifactResolveHalt("manifest artifact_set_hash mismatch")
        if manifest.get("runtime_use_eligible") is not False:
            raise RegistryArtifactResolveHalt("manifest must remain runtime_use_eligible=false; set eligibility comes from accepted event")
        members = manifest.get("member_artifacts")
        if not isinstance(members, list) or not members:
            raise RegistryArtifactResolveHalt("manifest member_artifacts missing")
        member_hashes = manifest.get("member_hashes") or {}
        schema_hashes = manifest.get("schema_hashes") or {}
        for member in members:
            logical_id = member.get("logical_artifact_id")
            if member_hashes.get(logical_id) != member.get("content_hash"):
                raise RegistryArtifactResolveHalt(f"member hash mismatch: {logical_id}")
            if schema_hashes.get(logical_id) != member.get("schema_hash"):
                raise RegistryArtifactResolveHalt(f"member schema hash mismatch: {logical_id}")
            physical = member.get("physical_path")
            if physical and not (self._paths()["repo_root"] / physical).exists():
                raise RegistryArtifactResolveHalt(f"member physical_path missing: {physical}")

    def _result(
        self,
        artifact_set_type: str,
        set_id: str,
        entry: dict[str, Any],
        accepted: dict[str, Any],
        manifest: dict[str, Any],
        report: dict[str, Any],
        checkpoint: dict[str, Any],
        validation: dict[str, Any],
        index: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema_version": "artifact_registry_resolver_result.v1",
            "resolver_version": RESOLVER_VERSION,
            "artifact_set_type": artifact_set_type,
            "artifact_set_id": set_id,
            "logical_artifact_id": entry["logical_artifact_id"],
            "artifact_type": entry["artifact_type"],
            "component": entry["component"],
            "status": entry["current_status"],
            "runtime_use_eligible": entry["runtime_use_eligible"],
            "physical_path": entry.get("physical_path"),
            "content_hash": entry["content_hash"],
            "schema_hash": entry["schema_hash"],
            "accepted_event_id": entry["accepted_event_id"],
            "accepted_at": entry.get("accepted_at"),
            "accepted_by": entry.get("accepted_by"),
            "acceptance_event": accepted,
            "acceptance_report_ref": accepted.get("acceptance_report_ref"),
            "artifact_set_manifest_ref": report.get("artifact_set_manifest_ref"),
            "members": manifest["member_artifacts"],
            "member_hashes": manifest["member_hashes"],
            "schema_hashes": manifest["schema_hashes"],
            "consumer_compatibility": accepted.get("consumer_compatibility") or [],
            "checkpoint": {
                "checkpoint_id": checkpoint["checkpoint"].get("checkpoint_id"),
                "checkpoint_path": checkpoint["checkpoint_path"],
                "checkpoint_hash": checkpoint["checkpoint"].get("checkpoint_hash"),
                "event_log_hash": checkpoint["checkpoint"].get("event_log_hash"),
                "materialized_index_hash": checkpoint["checkpoint"].get("materialized_index_hash"),
                "event_count": checkpoint["checkpoint"].get("event_count"),
                "entry_count": checkpoint["checkpoint"].get("entry_count"),
            },
            "validation": {
                "event_log_hash": validation["event_log_hash"],
                "event_count": validation["event_count"],
                "index_hash": index["index_hash"],
                "entry_count": index["entry_count"],
            },
        }


def run_resolver_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve a runtime-eligible ACCEPTED Artifact Set from the formal Artifact Registry.")
    parser.add_argument("artifact_set_type")
    parser.add_argument("--registry-root", default=str(DEFAULT_REGISTRY_ROOT))
    parser.add_argument("--event-log", default=str(DEFAULT_EVENT_LOG_PATH))
    parser.add_argument("--index", default=None)
    args = parser.parse_args(argv)
    resolver = RegistryArtifactResolver(
        registry_root=Path(args.registry_root),
        event_log=Path(args.event_log),
        index_path=Path(args.index) if args.index else None,
        repo_root=Path.cwd(),
    )
    try:
        result = resolver.resolve(args.artifact_set_type)
    except RegistryArtifactResolverError as exc:
        print(json.dumps({"overall_result": "HALT", "artifact_set_type": args.artifact_set_type, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"overall_result": "PASS", "artifact_set_type": args.artifact_set_type, "artifact_set_id": result["artifact_set_id"], "accepted_event_id": result["accepted_event_id"], "runtime_use_eligible": result["runtime_use_eligible"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_resolver_cli())
