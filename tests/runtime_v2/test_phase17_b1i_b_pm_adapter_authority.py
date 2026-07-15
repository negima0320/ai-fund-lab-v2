from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.artifact_lookup import RuntimeArtifactLookupHalt, RuntimeArtifactMember, resolve_position_management_policy_artifacts
from ai_fund_lab_v2.runtime_v2.position_management.producer import (
    PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH,
    verify_position_management_runtime_adapter_authority,
)


class FakeArtifactSet:
    def __init__(self, member: RuntimeArtifactMember) -> None:
        self.artifact_instance_id = "fake.pm.set@sha256-test"
        self.accepted_event_id = "event-test"
        self.raw_resolver_result = {
            "members": [
                {
                    "member_role": "RUNTIME_ADAPTER",
                    "physical_path": member.physical_path.as_posix(),
                    "content_hash": member.content_hash,
                    "authority_mode": "ACCEPTED_CURRENT_PATH",
                    "accepted_current_path": True,
                }
            ]
        }
        self._member = member

    def require_member(self, role: str) -> RuntimeArtifactMember:
        if role != "RUNTIME_ADAPTER":
            raise RuntimeArtifactLookupHalt(role)
        return self._member


def test_pm_runtime_adapter_authority_passes_when_path_and_hash_match(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    source = repo_root / "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py"
    source.parent.mkdir(parents=True)
    source.write_text("print('authority')\n", encoding="utf-8")
    digest = _sha256(source)
    result = verify_position_management_runtime_adapter_authority(
        _fake_set(Path("src/ai_fund_lab_v2/runtime_v2/position_management/producer.py"), digest),
        executing_source_path=source,
        repo_root=repo_root,
    )

    assert result["authority_mode"] == "ACCEPTED_CURRENT_PATH"
    assert result["accepted_hash"] == digest
    assert result["executing_source_hash"] == digest
    assert result["executing_source_path"] == "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py"


def test_pm_runtime_adapter_authority_halts_on_path_mismatch(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    accepted = repo_root / "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py"
    actual = repo_root / "src/ai_fund_lab_v2/runtime_v2/position_management/other.py"
    accepted.parent.mkdir(parents=True)
    accepted.write_text("print('same')\n", encoding="utf-8")
    actual.write_text(accepted.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(RuntimeArtifactLookupHalt, match=PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH):
        verify_position_management_runtime_adapter_authority(
            _fake_set(Path("src/ai_fund_lab_v2/runtime_v2/position_management/producer.py"), _sha256(accepted)),
            executing_source_path=actual,
            repo_root=repo_root,
        )


def test_pm_runtime_adapter_authority_halts_on_hash_mismatch(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    source = repo_root / "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py"
    source.parent.mkdir(parents=True)
    source.write_text("print('actual')\n", encoding="utf-8")

    with pytest.raises(RuntimeArtifactLookupHalt, match=PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH):
        verify_position_management_runtime_adapter_authority(
            _fake_set(Path("src/ai_fund_lab_v2/runtime_v2/position_management/producer.py"), "0" * 64),
            executing_source_path=source,
            repo_root=repo_root,
        )


def test_registry_resolver_returns_current_pm_source_authority() -> None:
    source = Path("src/ai_fund_lab_v2/runtime_v2/position_management/producer.py").resolve()
    result = verify_position_management_runtime_adapter_authority(resolve_position_management_policy_artifacts())

    assert Path(result["accepted_path"]).as_posix() == "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py"
    assert result["accepted_hash"] == _sha256(source)
    assert result["authority_mode"] == "ACCEPTED_CURRENT_PATH"


def _fake_set(path: Path, digest: str) -> FakeArtifactSet:
    return FakeArtifactSet(
        RuntimeArtifactMember(
            member_role="RUNTIME_ADAPTER",
            physical_path=path,
            content_hash=digest,
            schema_hash=None,
            artifact_type="RUNTIME_ADAPTER",
            artifact_set_id="control.position_management.accepted_set",
            logical_artifact_id="control.position_management.accepted_set.runtime_adapter",
        )
    )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()
