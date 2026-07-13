from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ai_fund_lab_v2.artifact_registry.resolver import RegistryArtifactResolver
from ai_fund_lab_v2.runtime_v2.artifact_lookup import (
    RuntimeArtifactLookupHalt,
    resolve_capital_allocation_policy_artifacts,
    resolve_feature_schema_artifacts,
    resolve_position_management_policy_artifacts,
    resolve_runtime_artifact_set,
)


def test_runtime_lookup_adapter_resolves_all_five_sets() -> None:
    resolved = [
        resolve_runtime_artifact_set("CANDIDATE_AI_SET", required_roles=("MODEL", "MODEL_MANIFEST", "FEATURE_SCHEMA")),
        resolve_runtime_artifact_set("OPPORTUNITY_AI_SET", required_roles=("MODEL", "METRICS", "FEATURE_SCHEMA")),
        resolve_position_management_policy_artifacts(),
        resolve_capital_allocation_policy_artifacts(),
        resolve_feature_schema_artifacts(),
    ]
    assert {item.artifact_set_type for item in resolved} == {
        "CANDIDATE_AI_SET",
        "OPPORTUNITY_AI_SET",
        "POSITION_MANAGEMENT_POLICY_SET",
        "CAPITAL_ALLOCATION_POLICY_SET",
        "FEATURE_SCHEMA_SET",
    }
    assert all(item.accepted_event_id for item in resolved)


def test_missing_role_halts() -> None:
    with pytest.raises(RuntimeArtifactLookupHalt, match="required artifact members missing"):
        resolve_runtime_artifact_set("CANDIDATE_AI_SET", required_roles=("NO_SUCH_ROLE",))


def test_member_hash_mismatch_halts(tmp_path: Path) -> None:
    root = tmp_path / "registry"
    shutil.copytree(Path(".runtime/artifact_registry"), root)
    resolver = RegistryArtifactResolver(registry_root=root, event_log=root / "events/registry_events.jsonl", index_path=root / "index/registry_index.json", repo_root=Path.cwd())
    target = Path(".runtime/artifacts/ai/candidate/model/formal_candidate_model/sha256-2ea75d14d3fe3682/model.pkl")
    backup = target.read_bytes()
    try:
        target.write_bytes(backup + b"phase16av")
        with pytest.raises(RuntimeArtifactLookupHalt, match="hash mismatch"):
            resolve_runtime_artifact_set("CANDIDATE_AI_SET", required_roles=("MODEL",), resolver=resolver)
    finally:
        target.write_bytes(backup)


def test_checkpoint_mismatch_halts(tmp_path: Path) -> None:
    root = tmp_path / "registry"
    shutil.copytree(Path(".runtime/artifact_registry"), root)
    latest = root / "checkpoints/latest.json"
    payload = json.loads(latest.read_text(encoding="utf-8"))
    payload["checkpoint_hash"] = "0" * 64
    latest.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    resolver = RegistryArtifactResolver(registry_root=root, event_log=root / "events/registry_events.jsonl", index_path=root / "index/registry_index.json", repo_root=Path.cwd())
    with pytest.raises(RuntimeArtifactLookupHalt, match="latest checkpoint hash mismatch"):
        resolve_runtime_artifact_set("CANDIDATE_AI_SET", required_roles=("MODEL",), resolver=resolver)
