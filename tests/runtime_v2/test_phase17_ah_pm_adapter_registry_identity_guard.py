from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

from ai_fund_lab_v2.runtime_v2.artifact_lookup import RuntimeArtifactLookupHalt, RuntimeArtifactMember
from ai_fund_lab_v2.runtime_v2.position_management import producer as pm_producer
from ai_fund_lab_v2.runtime_v2.position_management.producer import (
    PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH,
    verify_position_management_runtime_adapter_authority,
)


PM_ADAPTER_RELATIVE_PATH = Path("src/ai_fund_lab_v2/runtime_v2/position_management/producer.py")


class FakeArtifactSet:
    artifact_instance_id = "phase17ah.fixture.pm.runtime_adapter@sha256-current"
    accepted_event_id = "phase17ah-fixture-accepted-current"

    def __init__(
        self,
        member: RuntimeArtifactMember | None,
        *,
        raw_members: list[dict[str, Any]] | None = None,
        schema_version: str | None = "artifact_registry_resolver_result.v1",
    ) -> None:
        self._member = member
        members = raw_members
        if members is None and member is not None:
            members = [
                {
                    "member_role": "RUNTIME_ADAPTER",
                    "physical_path": member.physical_path.as_posix(),
                    "content_hash": member.content_hash,
                    "authority_mode": "ACCEPTED_CURRENT_PATH",
                    "accepted_current_path": True,
                }
            ]
        self.raw_resolver_result = {"schema_version": schema_version, "members": members or []}

    def require_member(self, role: str) -> RuntimeArtifactMember:
        if self._member is None or role != "RUNTIME_ADAPTER":
            raise RuntimeArtifactLookupHalt(f"required artifact member missing: POSITION_MANAGEMENT_POLICY_SET:{role}")
        return self._member


def test_phase17_ah_current_adapter_identity_passes_with_isolated_accepted_set() -> None:
    source = Path(pm_producer.__file__).resolve()
    digest = _sha256(source)

    result = verify_position_management_runtime_adapter_authority(_fake_set(PM_ADAPTER_RELATIVE_PATH, digest))

    assert result["accepted_path"] == PM_ADAPTER_RELATIVE_PATH.as_posix()
    assert result["executing_source_path"] == PM_ADAPTER_RELATIVE_PATH.as_posix()
    assert result["accepted_hash"] == digest
    assert result["executing_source_hash"] == digest
    assert result["hash_algorithm"] == "sha256"
    assert result["canonical_identity"]["checkout_location_independent"] is True


def test_phase17_ah_one_character_adapter_change_fails_closed(tmp_path: Path) -> None:
    repo_root = _copy_adapter_to_repo(tmp_path, text_suffix="# changed\n")
    source = repo_root / PM_ADAPTER_RELATIVE_PATH

    with pytest.raises(RuntimeArtifactLookupHalt, match=PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH):
        verify_position_management_runtime_adapter_authority(
            _fake_set(PM_ADAPTER_RELATIVE_PATH, "0" * 64),
            executing_source_path=source,
            repo_root=repo_root,
        )


def test_phase17_ah_missing_registry_key_fails_closed() -> None:
    with pytest.raises(RuntimeArtifactLookupHalt, match="required artifact member missing"):
        verify_position_management_runtime_adapter_authority(FakeArtifactSet(None))


def test_phase17_ah_missing_executing_artifact_fails_closed(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    missing = repo_root / PM_ADAPTER_RELATIVE_PATH

    with pytest.raises(RuntimeArtifactLookupHalt, match="executing source file missing"):
        verify_position_management_runtime_adapter_authority(
            _fake_set(PM_ADAPTER_RELATIVE_PATH, "0" * 64),
            executing_source_path=missing,
            repo_root=repo_root,
        )


def test_phase17_ah_unknown_resolver_schema_fails_closed() -> None:
    source = Path(pm_producer.__file__).resolve()
    digest = _sha256(source)

    with pytest.raises(RuntimeArtifactLookupHalt, match="unsupported resolver schema_version"):
        verify_position_management_runtime_adapter_authority(
            _fake_set(PM_ADAPTER_RELATIVE_PATH, digest, schema_version="unknown.resolver.v9")
        )


def test_phase17_ah_wrong_path_fails_closed(tmp_path: Path) -> None:
    repo_root = _copy_adapter_to_repo(tmp_path)
    source = repo_root / PM_ADAPTER_RELATIVE_PATH

    with pytest.raises(RuntimeArtifactLookupHalt, match=PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH):
        verify_position_management_runtime_adapter_authority(
            _fake_set(Path("src/ai_fund_lab_v2/runtime_v2/position_management/other.py"), _sha256(source)),
            executing_source_path=source,
            repo_root=repo_root,
        )


def test_phase17_ah_canonical_identity_is_checkout_location_independent(tmp_path: Path) -> None:
    repo_a = _copy_adapter_to_repo(tmp_path / "a")
    repo_b = _copy_adapter_to_repo(tmp_path / "b")
    digest = _sha256(repo_a / PM_ADAPTER_RELATIVE_PATH)

    result_a = verify_position_management_runtime_adapter_authority(
        _fake_set(PM_ADAPTER_RELATIVE_PATH, digest),
        executing_source_path=repo_a / PM_ADAPTER_RELATIVE_PATH,
        repo_root=repo_a,
    )
    result_b = verify_position_management_runtime_adapter_authority(
        _fake_set(PM_ADAPTER_RELATIVE_PATH, digest),
        executing_source_path=repo_b / PM_ADAPTER_RELATIVE_PATH,
        repo_root=repo_b,
    )

    assert result_a["canonical_identity"] == result_b["canonical_identity"]
    assert result_a["executing_source_hash"] == result_b["executing_source_hash"]


def test_phase17_ah_timestamp_changes_do_not_change_hash(tmp_path: Path) -> None:
    repo_root = _copy_adapter_to_repo(tmp_path)
    source = repo_root / PM_ADAPTER_RELATIVE_PATH
    before = _sha256(source)

    os.utime(source, (1_800_000_000, 1_800_000_000))

    result = verify_position_management_runtime_adapter_authority(
        _fake_set(PM_ADAPTER_RELATIVE_PATH, before),
        executing_source_path=source,
        repo_root=repo_root,
    )
    assert result["executing_source_hash"] == before


def test_phase17_ah_demo_historical_production_share_same_adapter_identity() -> None:
    source = Path(pm_producer.__file__).resolve()
    digest = _sha256(source)

    identities = {
        mode: verify_position_management_runtime_adapter_authority(_fake_set(PM_ADAPTER_RELATIVE_PATH, digest))["canonical_identity"]
        for mode in ("demo", "historical", "production")
    }

    assert identities["demo"] == identities["historical"] == identities["production"]


def test_phase17_ah_dot_artifact_source_is_not_allowed() -> None:
    source = Path(pm_producer.__file__).resolve()

    with pytest.raises(RuntimeArtifactLookupHalt, match="cannot be empty or '.'"):
        verify_position_management_runtime_adapter_authority(_fake_set(Path("."), _sha256(source)))


def test_phase17_ah_duplicate_runtime_adapter_authority_fails_closed() -> None:
    source = Path(pm_producer.__file__).resolve()
    digest = _sha256(source)
    raw_member = {
        "member_role": "RUNTIME_ADAPTER",
        "physical_path": PM_ADAPTER_RELATIVE_PATH.as_posix(),
        "content_hash": digest,
    }

    with pytest.raises(RuntimeArtifactLookupHalt, match="expected exactly one RUNTIME_ADAPTER authority"):
        verify_position_management_runtime_adapter_authority(
            _fake_set(PM_ADAPTER_RELATIVE_PATH, digest, raw_members=[raw_member, dict(raw_member)])
        )


def _fake_set(
    path: Path,
    digest: str,
    *,
    raw_members: list[dict[str, Any]] | None = None,
    schema_version: str | None = "artifact_registry_resolver_result.v1",
) -> FakeArtifactSet:
    return FakeArtifactSet(
        RuntimeArtifactMember(
            member_role="RUNTIME_ADAPTER",
            physical_path=path,
            content_hash=digest,
            schema_hash=None,
            artifact_type="RUNTIME_ADAPTER",
            artifact_set_id="control.position_management.accepted_set",
            logical_artifact_id="control.position_management.accepted_set.runtime_adapter",
        ),
        raw_members=raw_members,
        schema_version=schema_version,
    )


def _copy_adapter_to_repo(tmp_path: Path, *, text_suffix: str = "") -> Path:
    repo_root = tmp_path / "repo"
    target = repo_root / PM_ADAPTER_RELATIVE_PATH
    target.parent.mkdir(parents=True)
    shutil.copy2(Path(pm_producer.__file__).resolve(), target)
    if text_suffix:
        target.write_text(target.read_text(encoding="utf-8") + text_suffix, encoding="utf-8")
    return repo_root


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
