from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from scripts import runtime_test


START_DATE = "2026-07-06"
RUN_ID = "runtime-test-historical-smoke-new"
OLD_RUN_ID = "runtime-test-historical-smoke-old"


def test_phase17_al_clean_baseline_from_reset_state_passes(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_clean_state(root)

    result = runtime_test.build_baseline_compatibility(
        runtime_root=root,
        requested_start_date=START_DATE,
        run_id=RUN_ID,
        profile_id="historical-smoke",
        mode="historical",
    )

    assert result["baseline_compatibility_status"] == "PASS"
    assert result["mismatch_reasons"] == []


def test_phase17_al_terminal_empty_pending_future_date_halts(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_clean_state(root)
    _write_pending(root, active=False, target_date="2026-07-07", run_id="")

    result = _compat(root)

    assert result["baseline_compatibility_status"] == "REVIEW_REQUIRED"
    assert "pending_target_date_future" in result["mismatch_reasons"]


def test_phase17_al_terminal_empty_pending_foreign_run_halts(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_clean_state(root)
    _write_pending(root, active=False, target_date=START_DATE, run_id=OLD_RUN_ID)

    result = _compat(root)

    assert result["baseline_compatibility_status"] == "REVIEW_REQUIRED"
    assert "pending_foreign_runtime_test_run_id" in result["mismatch_reasons"]


def test_phase17_al_active_pending_halts_even_same_date(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_clean_state(root)
    _write_pending(root, active=True, target_date=START_DATE, run_id=RUN_ID)

    result = _compat(root)

    assert "pending_active" in result["mismatch_reasons"]


@pytest.mark.parametrize(
    "writer,expected",
    [
        (lambda root: _write_runtime_state(root, "2026-07-07"), "current_state_date_future"),
        (lambda root: _write_ledger(root, "2026-07-07"), "ledger_date_future"),
        (lambda root: _write_safety(root, "2026-07-07", RUN_ID), "safety_artifact_business_date_future"),
        (lambda root: _write_safety(root, START_DATE, OLD_RUN_ID), "safety_foreign_runtime_test_run_id"),
    ],
)
def test_phase17_al_future_or_foreign_state_halts(tmp_path: Path, writer, expected: str) -> None:
    root = _runtime_root(tmp_path)
    _write_clean_state(root)
    writer(root)

    result = _compat(root)

    assert expected in result["mismatch_reasons"]


def test_phase17_al_same_run_terminal_pending_is_compatible_resume_context(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_clean_state(root)
    _write_pending(root, active=False, target_date=START_DATE, run_id=RUN_ID)

    result = _compat(root)

    assert result["baseline_compatibility_status"] == "PASS"


@pytest.mark.parametrize("mode", ["production", "demo", "historical"])
def test_phase17_al_foreign_runtime_test_identity_not_relaxed_by_mode(tmp_path: Path, mode: str) -> None:
    root = _runtime_root(tmp_path)
    _write_clean_state(root, mode=mode)
    _write_pending(root, active=False, target_date=START_DATE, run_id=OLD_RUN_ID)

    result = runtime_test.build_baseline_compatibility(
        runtime_root=root,
        requested_start_date=START_DATE,
        run_id=RUN_ID,
        profile_id=f"{mode}-profile",
        mode=mode,
    )

    assert "pending_foreign_runtime_test_run_id" in result["mismatch_reasons"]


def test_phase17_al_plan_compatibility_read_does_not_mutate_runtime_state(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_clean_state(root)
    before = runtime_test.directory_hash(root)

    runtime_test.build_baseline_compatibility(
        runtime_root=root,
        requested_start_date=START_DATE,
        run_id=RUN_ID,
        profile_id="historical-smoke",
        mode="historical",
    )

    assert runtime_test.directory_hash(root) == before


def test_phase17_al_run_precondition_halts_before_any_runtime_job(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_root = _runtime_root(tmp_path)
    evidence_root = tmp_path / "reports" / "runtime_tests"
    _write_clean_state(runtime_root)
    _write_pending(runtime_root, active=False, target_date="2026-07-07", run_id=OLD_RUN_ID)
    _write_backup_manifest(evidence_root)
    _write_plan(evidence_root, run_id=RUN_ID)
    calls: list[list[str]] = []

    def fake_run_runtime_cli(command: list[str], *, cwd: Path):
        calls.append(command)
        raise AssertionError("runtime job must not execute")

    monkeypatch.setattr(runtime_test, "run_runtime_cli", fake_run_runtime_cli)

    with pytest.raises(runtime_test.RuntimeTestError) as exc:
        runtime_test.run_command(
            argparse.Namespace(
                run_id=RUN_ID,
                dry_run=False,
                confirm=True,
                explicit_mutation_confirm=True,
                business_days=None,
                start_date=None,
                date_from=None,
                date_to=None,
            ),
            profile=_profile(runtime_root),
            runtime_root=runtime_root,
            evidence_root=evidence_root,
        )

    assert exc.value.status == "HALT"
    assert "runtime_test_clean_baseline_mismatch" in str(exc.value)
    assert calls == []


def test_phase17_al_backup_classification_rejects_mid_run_state(tmp_path: Path) -> None:
    evidence_root = tmp_path / "reports" / "runtime_tests"
    backup_root = evidence_root / "backups" / "backup-midrun" / "state"
    _write_clean_state(backup_root)
    _write_pending(backup_root, active=False, target_date="2026-07-07", run_id=OLD_RUN_ID)
    manifest = _backup_manifest(evidence_root, "backup-midrun")

    result = runtime_test.classify_backup_for_clean_baseline(
        backup_manifest=manifest,
        requested_start_date=START_DATE,
        run_id=RUN_ID,
    )

    assert result["clean_baseline"] is False
    assert "pending_target_date_future" in result["rejected_reasons"]
    assert "pending_foreign_runtime_test_run_id" in result["rejected_reasons"]


def test_phase17_al_no_action_terminal_pending_distinguished_from_active_pending(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_clean_state(root)
    _write_pending(root, active=False, target_date=START_DATE, run_id="")
    terminal = _compat(root)
    _write_pending(root, active=True, target_date=START_DATE, run_id="")
    active = _compat(root)

    assert terminal["baseline_compatibility_status"] == "PASS"
    assert "pending_active" in active["mismatch_reasons"]


def _compat(root: Path) -> dict:
    return runtime_test.build_baseline_compatibility(
        runtime_root=root,
        requested_start_date=START_DATE,
        run_id=RUN_ID,
        profile_id="historical-smoke",
        mode="historical",
    )


def _runtime_root(tmp_path: Path) -> Path:
    return tmp_path / ".runtime"


def _write_clean_state(root: Path, *, mode: str = "historical") -> None:
    _write_ledger(root, "")
    _write_pending(root, active=False, target_date="", run_id="")
    _write_runtime_state(root, "", mode=mode)


def _write_ledger(root: Path, business_date: str) -> None:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "runtime_v2_current_temporal_v1",
            "environment": "historical",
            "business_date": business_date,
            "as_of": "2026-07-15T00:00:00+00:00",
            "positions": [],
            "current_state_confirmed_empty": True,
        },
    )


def _write_runtime_state(root: Path, business_date: str, *, mode: str = "historical") -> None:
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "runtime_v2_operation_state_v1",
            "environment": mode,
            "runtime_mode": mode,
            "business_date": business_date,
            "state": "READY",
        },
    )


def _write_pending(root: Path, *, active: bool, target_date: str, run_id: str) -> None:
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "state": "APPROVED" if active else "EMPTY",
            "status": "APPROVED" if active else "EMPTY",
            "active_pending": active,
            "target_session_date": target_date,
            "safety_context": {
                "runtime_test_run_id": run_id,
                "runtime_test_evidence_root": f"reports/runtime_tests/runs/{run_id}" if run_id else "",
                "safety_business_date": target_date,
            },
            "items": [{"symbol": "7203", "side": "SELL"}] if active else [],
        },
    )


def _write_safety(root: Path, business_date: str, run_id: str) -> None:
    _write_json(
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "schema_version": "runtime_v2_safety_decision_v1",
            "business_date": business_date,
            "runtime_test_run_id": run_id,
            "decision": "ALLOW",
            "safety_status": "PASS",
        },
    )


def _write_backup_manifest(evidence_root: Path) -> None:
    manifest = _backup_manifest(evidence_root, "backup-clean")
    path = evidence_root / "backups" / "backup-clean" / "backup_manifest.json"
    _write_json(path, manifest)


def _backup_manifest(evidence_root: Path, backup_id: str) -> dict:
    return {
        "schema_version": runtime_test.BACKUP_MANIFEST_SCHEMA_VERSION,
        "backup_id": backup_id,
        "backup_path": str(evidence_root / "backups" / backup_id),
        "profile_id": "historical-smoke",
        "created_at": "2026-07-15T00:00:00Z",
    }


def _write_plan(evidence_root: Path, *, run_id: str) -> None:
    _write_json(
        evidence_root / "runs" / run_id / "plan.json",
        {
            "schema_version": runtime_test.PLAN_SCHEMA_VERSION,
            "run_id": run_id,
            "profile_id": "historical-smoke",
            "business_dates": [
                {
                    "business_date": START_DATE,
                    "feature_date_evidence": _feature_evidence(),
                    "jobs": [{"job": "market_refresh", "business_date": START_DATE, "command": ["should-not-run"]}],
                }
            ],
        },
    )


def _feature_evidence() -> dict:
    return {
        "source": "runtime_test_plan_preflight",
        "status": "PASS",
        "contract_materialized": False,
        "contract_hash": "hash",
        "profile_value_used_as_authority": False,
        "profile_expected_selected_feature_date": START_DATE,
        "selected_feature_date": START_DATE,
    }


def _profile(runtime_root: Path) -> dict:
    return {
        "profile_id": "historical-smoke",
        "mode": "historical",
        "runtime_root": str(runtime_root),
        "broker_environment": "historical_simulated",
        "external_effect_policy": {},
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
