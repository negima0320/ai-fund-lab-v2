from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from ai_fund_lab_v2.artifact_registry.checkpoint_writer import run_checkpoint
from ai_fund_lab_v2.artifact_registry.index_builder import run_index_build
from ai_fund_lab_v2.artifact_registry.resolver import RegistryArtifactResolveHalt, RegistryArtifactResolver


def _copy_registry(tmp_path: Path) -> Path:
    root = tmp_path / "artifact_registry"
    shutil.copytree(Path(".runtime/artifact_registry"), root)
    latest = root / "checkpoints/latest.json"
    payload = json.loads(latest.read_text(encoding="utf-8"))
    checkpoint_name = Path(payload["checkpoint_path"]).name
    payload["checkpoint_path"] = str(root / "checkpoints" / checkpoint_name)
    latest.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return root


def _resolver(root: Path) -> RegistryArtifactResolver:
    return RegistryArtifactResolver(
        registry_root=root,
        event_log=root / "events/registry_events.jsonl",
        index_path=root / "index/registry_index.json",
        repo_root=Path.cwd(),
    )


def test_resolves_accepted_candidate_from_formal_registry() -> None:
    result = RegistryArtifactResolver(repo_root=Path.cwd()).resolve("CANDIDATE_AI_SET")
    assert result["artifact_set_id"] == "ai.candidate.accepted_set"
    assert result["status"] == "ACCEPTED"
    assert result["runtime_use_eligible"] is True
    assert result["accepted_event_id"]
    assert result["checkpoint"]["event_count"] >= 15
    assert result["members"]


def test_cli_resolves_candidate() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/run_registry_resolver.py", "CANDIDATE_AI_SET"],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["overall_result"] == "PASS"
    assert payload["runtime_use_eligible"] is True


def test_validated_only_registry_rejected(tmp_path: Path) -> None:
    root = _copy_registry(tmp_path)
    log = root / "events/registry_events.jsonl"
    lines = log.read_text(encoding="utf-8").splitlines()
    log.write_text("\n".join(lines[:10]) + "\n", encoding="utf-8")
    (root / "checkpoints/latest.json").unlink()
    run_index_build(registry_root=root, event_log=log, output=tmp_path / "index_validated", repo_root=Path.cwd())
    run_checkpoint(registry_root=root, event_log=log, output=tmp_path / "checkpoint_validated", repo_root=Path.cwd())
    with pytest.raises(RegistryArtifactResolveHalt, match="accepted artifact set not found"):
        _resolver(root).resolve("CANDIDATE_AI_SET")


def test_entry_missing_rejected(tmp_path: Path) -> None:
    root = _copy_registry(tmp_path)
    index_path = root / "index/registry_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["entries"].pop("ai.candidate.accepted_set")
    index["entry_count"] = len(index["entries"])
    index_path.write_text(json.dumps(index, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(RegistryArtifactResolveHalt):
        _resolver(root).resolve("CANDIDATE_AI_SET")


def test_stale_index_rejected(tmp_path: Path) -> None:
    root = _copy_registry(tmp_path)
    index_path = root / "index/registry_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["event_count"] = 14
    index_path.write_text(json.dumps(index, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(RegistryArtifactResolveHalt, match="index"):
        _resolver(root).resolve("CANDIDATE_AI_SET")


def test_corrupt_index_rejected(tmp_path: Path) -> None:
    root = _copy_registry(tmp_path)
    (root / "index/registry_index.json").write_text("{not-json\n", encoding="utf-8")
    with pytest.raises(RegistryArtifactResolveHalt, match="index corrupt"):
        _resolver(root).resolve("CANDIDATE_AI_SET")


def test_checkpoint_mismatch_rejected(tmp_path: Path) -> None:
    root = _copy_registry(tmp_path)
    latest = root / "checkpoints/latest.json"
    payload = json.loads(latest.read_text(encoding="utf-8"))
    payload["checkpoint_hash"] = "0" * 64
    latest.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(RegistryArtifactResolveHalt, match="latest checkpoint hash mismatch"):
        _resolver(root).resolve("CANDIDATE_AI_SET")


def test_hash_mismatch_rejected(tmp_path: Path) -> None:
    root = _copy_registry(tmp_path)
    log = root / "events/registry_events.jsonl"
    events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    for event in events:
        if event.get("event_type") == "ARTIFACT_ACCEPTED" and event.get("artifact_set_type") == "CANDIDATE_AI_SET":
            event["content_hash"] = "1" * 64
            break
    log.write_text("\n".join(json.dumps(event, sort_keys=True, separators=(",", ":")) for event in events) + "\n", encoding="utf-8")
    with pytest.raises(RegistryArtifactResolveHalt, match="event log validation"):
        _resolver(root).resolve("CANDIDATE_AI_SET")


def test_duplicate_accepted_rejected(tmp_path: Path) -> None:
    root = _copy_registry(tmp_path)
    log = root / "events/registry_events.jsonl"
    lines = log.read_text(encoding="utf-8").splitlines()
    duplicate = json.loads(lines[-1])
    duplicate["event_id"] = "event-phase16au-duplicate"
    lines.append(json.dumps(duplicate, sort_keys=True, separators=(",", ":")))
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(RegistryArtifactResolveHalt):
        _resolver(root).resolve("FEATURE_SCHEMA_SET")


def test_revoked_entry_rejected(tmp_path: Path) -> None:
    root = _copy_registry(tmp_path)
    index_path = root / "index/registry_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["entries"]["ai.candidate.accepted_set"]["current_status"] = "REVOKED"
    index["entries"]["ai.candidate.accepted_set"]["runtime_use_eligible"] = False
    index_path.write_text(json.dumps(index, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(RegistryArtifactResolveHalt):
        _resolver(root).resolve("CANDIDATE_AI_SET")
