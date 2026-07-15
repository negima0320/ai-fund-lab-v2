from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.artifact_registry.resolver import (
    RegistryArtifactResolveHalt,
    RegistryArtifactResolver,
)


class RuntimeArtifactLookupError(RuntimeError):
    pass


class RuntimeArtifactLookupHalt(RuntimeArtifactLookupError):
    pass


@dataclass(frozen=True)
class RuntimeArtifactMember:
    member_role: str
    physical_path: Path
    content_hash: str
    schema_hash: str | None
    artifact_type: str
    artifact_set_id: str
    logical_artifact_id: str


@dataclass(frozen=True)
class RuntimeArtifactSet:
    artifact_set_id: str
    artifact_set_type: str
    logical_artifact_id: str
    artifact_instance_id: str
    accepted_event_id: str
    checkpoint_ref: str
    members: dict[str, RuntimeArtifactMember]
    raw_resolver_result: dict[str, Any]

    def require_member(self, role: str) -> RuntimeArtifactMember:
        try:
            return self.members[role]
        except KeyError as exc:
            raise RuntimeArtifactLookupHalt(f"required artifact member missing: {self.artifact_set_type}:{role}") from exc


def resolve_runtime_artifact_set(
    artifact_set_type: str,
    *,
    required_roles: tuple[str, ...],
    resolver: RegistryArtifactResolver | None = None,
    repo_root: Path | str | None = None,
) -> RuntimeArtifactSet:
    repo = Path(repo_root) if repo_root is not None else _default_repo_root()
    try:
        result = (resolver or RegistryArtifactResolver(repo_root=repo)).resolve(artifact_set_type)
    except RegistryArtifactResolveHalt as exc:
        raise RuntimeArtifactLookupHalt(str(exc)) from exc
    members: dict[str, RuntimeArtifactMember] = {}
    for member in result.get("members") or []:
        role = str(member.get("member_role") or member.get("role") or "")
        path = repo / str(member.get("physical_path") or "")
        content_hash = str(member.get("content_hash") or "")
        if not role:
            raise RuntimeArtifactLookupHalt(f"artifact member role missing: {artifact_set_type}")
        if not path.is_file():
            raise RuntimeArtifactLookupHalt(f"artifact member file missing: {artifact_set_type}:{role}:{path}")
        actual_hash = _sha256_file(path)
        if actual_hash != content_hash:
            raise RuntimeArtifactLookupHalt(f"artifact member hash mismatch: {artifact_set_type}:{role}")
        members[role] = RuntimeArtifactMember(
            member_role=role,
            physical_path=path,
            content_hash=content_hash,
            schema_hash=member.get("schema_hash"),
            artifact_type=str(member.get("artifact_type") or role),
            artifact_set_id=str(member.get("artifact_set_id") or result["artifact_set_id"]),
            logical_artifact_id=str(member.get("logical_artifact_id") or ""),
        )
    missing = [role for role in required_roles if role not in members]
    if missing:
        raise RuntimeArtifactLookupHalt(f"required artifact members missing: {artifact_set_type}:{','.join(missing)}")
    if result.get("status") != "ACCEPTED" or result.get("runtime_use_eligible") is not True:
        raise RuntimeArtifactLookupHalt(f"artifact set is not runtime eligible: {artifact_set_type}")
    return RuntimeArtifactSet(
        artifact_set_id=str(result["artifact_set_id"]),
        artifact_set_type=artifact_set_type,
        logical_artifact_id=str(result["logical_artifact_id"]),
        artifact_instance_id=str(result["acceptance_event"].get("artifact_instance_id") or ""),
        accepted_event_id=str(result["accepted_event_id"]),
        checkpoint_ref=str((result.get("checkpoint") or {}).get("checkpoint_path") or ""),
        members=members,
        raw_resolver_result=result,
    )


def require_diagnostic_path_matches_registry(path: Path | str | None, member: RuntimeArtifactMember, *, label: str) -> None:
    if path is None:
        return
    diagnostic_path = Path(path)
    if diagnostic_path != member.physical_path:
        raise RuntimeArtifactLookupHalt(f"{label} legacy path cannot override Registry authority: {diagnostic_path}")
    if _sha256_file(diagnostic_path) != member.content_hash:
        raise RuntimeArtifactLookupHalt(f"{label} diagnostic path hash mismatch")


def resolve_feature_schema_artifacts() -> RuntimeArtifactSet:
    return resolve_runtime_artifact_set(
        "FEATURE_SCHEMA_SET",
        required_roles=("FEATURE_SCHEMA", "POINT_IN_TIME_EVIDENCE", "CONSUMER_COMPATIBILITY", "SCHEMA_VALIDATION_EVIDENCE"),
    )


def resolve_position_management_policy_artifacts() -> RuntimeArtifactSet:
    return resolve_runtime_artifact_set(
        "POSITION_MANAGEMENT_POLICY_SET",
        required_roles=(
            "CODE_POLICY",
            "RUNTIME_ADAPTER",
            "POLICY_VERSION",
            "FEATURE_VERSION",
            "BEHAVIOR_CONTRACT",
            "REGRESSION_EVIDENCE",
            "CONSUMER_COMPATIBILITY",
        ),
    )


def resolve_capital_allocation_policy_artifacts() -> RuntimeArtifactSet:
    return resolve_runtime_artifact_set(
        "CAPITAL_ALLOCATION_POLICY_SET",
        required_roles=("POLICY", "POLICY_SCHEMA", "POLICY_VERSION", "VALIDATION_EVIDENCE", "REGRESSION_EVIDENCE", "CONSUMER_COMPATIBILITY"),
    )


def resolve_runtime_capital_policy_path(path: Path | str | None = None) -> Path:
    capital = resolve_capital_allocation_policy_artifacts()
    policy = capital.require_member("POLICY")
    version = capital.require_member("POLICY_VERSION")
    _validate_capital_policy_version(policy, version)
    require_diagnostic_path_matches_registry(path, policy, label="capital_deployment_policy")
    return policy.physical_path


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _validate_capital_policy_version(policy: RuntimeArtifactMember, version: RuntimeArtifactMember) -> None:
    try:
        payload = json.loads(version.physical_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeArtifactLookupHalt("capital POLICY_VERSION is unreadable") from exc
    if not isinstance(payload, dict):
        raise RuntimeArtifactLookupHalt("capital POLICY_VERSION must be a JSON object")
    expected_hash = payload.get("policy_content_hash") or payload.get("content_hash")
    if expected_hash and str(expected_hash).replace("sha256:", "") != policy.content_hash:
        raise RuntimeArtifactLookupHalt("capital POLICY_VERSION policy hash mismatch")
    if payload.get("policy_member_role") not in {None, "POLICY"}:
        raise RuntimeArtifactLookupHalt("capital POLICY_VERSION member role mismatch")
