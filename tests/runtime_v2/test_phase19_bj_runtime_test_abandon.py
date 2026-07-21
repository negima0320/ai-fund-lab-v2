from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.runtime_v2.test_phase17_k_runtime_test_runner import CONFIRM_FLAG, call_main, load_runner, make_runtime_root


RUN_ID = "runtime-test-halt-abandon-fixture"


def test_phase19_bj_halt_run_is_active_until_abandoned(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    _write_halt_run(runner, root=root, evidence=evidence)

    payload = call_main(runner, ["status", "--runtime-root", str(root), "--evidence-root", str(evidence)], capsys)

    assert payload["status"] == "PASS"
    assert payload["active_test_run"] == RUN_ID
    assert payload["run_status"] == "HALT"
    assert payload["next_job"] == "2026-07-06:submit"


def test_phase19_bj_abandon_dry_run_does_not_write_or_clear_active(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    run_dir = _write_halt_run(runner, root=root, evidence=evidence)
    before_runtime = runner.directory_hash(root)
    before_run = runner.directory_hash(run_dir)

    payload = call_main(
        runner,
        ["abandon", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", RUN_ID, "--dry-run"],
        capsys,
    )
    status_payload = call_main(runner, ["status", "--runtime-root", str(root), "--evidence-root", str(evidence)], capsys)

    assert payload["status"] == "DRY_RUN"
    assert payload["current_status"] == "HALT"
    assert payload["active_run"] is True
    assert payload["abandonment_possible"] is True
    assert payload["dry_run_no_mutation"] is True
    assert payload["trading_state_mutation"] is False
    assert payload["files_to_create"]
    assert payload["files_to_modify"] == []
    assert not (run_dir / "abandonment.json").exists()
    assert not (run_dir / "final_summary.json").exists()
    assert runner.directory_hash(root) == before_runtime
    assert runner.directory_hash(run_dir) == before_run
    assert status_payload["active_test_run"] == RUN_ID


def test_phase19_bj_actual_abandon_excludes_run_from_active_and_preserves_evidence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    run_dir = _write_halt_run(runner, root=root, evidence=evidence)
    daily_evidence = run_dir / "daily" / "2026-07-06" / "submit" / "runtime_manifest.json"
    before_runtime = runner.directory_hash(root)
    run_state_before = json.loads((run_dir / "run_state.json").read_text(encoding="utf-8"))

    payload = call_main(
        runner,
        [
            "abandon",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(evidence),
            "--run-id",
            RUN_ID,
            "--confirm",
            CONFIRM_FLAG,
        ],
        capsys,
    )
    status_payload = call_main(runner, ["status", "--runtime-root", str(root), "--evidence-root", str(evidence)], capsys)

    abandonment = json.loads((run_dir / "abandonment.json").read_text(encoding="utf-8"))
    final_summary = json.loads((run_dir / "final_summary.json").read_text(encoding="utf-8"))
    run_state_after = json.loads((run_dir / "run_state.json").read_text(encoding="utf-8"))

    assert payload["status"] == "ABANDONED"
    assert payload["_exit_code"] == 0
    assert payload["resume_disabled"] is True
    assert payload["trading_state_mutated"] is False
    assert payload["broker_access"] is False
    assert payload["broker_write"] is False
    assert payload["external_delivery"] is False
    assert status_payload["active_test_run"] == ""
    assert status_payload["run_status"] == "IDLE"
    assert status_payload["next_job"] == ""
    assert abandonment["previous_status"] == "HALT"
    assert abandonment["resume_disabled"] is True
    assert final_summary["status"] == "ABANDONED"
    assert final_summary["abandoned_at"]
    assert run_state_after == run_state_before
    assert daily_evidence.exists()
    assert runner.directory_hash(root) == before_runtime


def test_phase19_bj_abandoned_run_rejects_resume_and_allows_new_fresh_run_dry_run(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    _write_halt_run(runner, root=root, evidence=evidence)
    call_main(
        runner,
        [
            "abandon",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(evidence),
            "--run-id",
            RUN_ID,
            "--confirm",
            CONFIRM_FLAG,
        ],
        capsys,
    )

    resume = call_main(
        runner,
        ["resume", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", RUN_ID, "--dry-run"],
        capsys,
    )
    fresh = call_main(
        runner,
        [
            "fresh-run",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(evidence),
            "--business-days",
            "1",
            "--start-date",
            "2026-07-06",
            "--initial-cash",
            "1000000",
            "--dry-run",
        ],
        capsys,
    )

    assert resume["status"] == "PRECONDITION_FAILURE"
    assert "run is closed" in resume["error"]
    assert fresh["status"] == "DRY_RUN"
    assert fresh["active_run_conflict"] is False


def test_phase19_bj_running_run_abandon_is_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    _write_halt_run(runner, root=root, evidence=evidence, status="RUNNING")

    payload = call_main(
        runner,
        ["abandon", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", RUN_ID, "--confirm", CONFIRM_FLAG],
        capsys,
    )

    assert payload["status"] == "PRECONDITION_FAILURE"
    assert "RUNNING run" in payload["error"]


def test_phase19_bj_reabandon_is_idempotent(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    _write_halt_run(runner, root=root, evidence=evidence)
    first = call_main(
        runner,
        ["abandon", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", RUN_ID, "--confirm", CONFIRM_FLAG],
        capsys,
    )
    second = call_main(
        runner,
        ["abandon", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", RUN_ID, "--confirm", CONFIRM_FLAG],
        capsys,
    )

    assert first["status"] == "ABANDONED"
    assert second["status"] == "ABANDONED"
    assert second["already_abandoned"] is True


def _write_halt_run(
    runner,
    *,
    root: Path,
    evidence: Path,
    status: str = "HALT",
) -> Path:
    profile = runner.load_profile("historical-smoke")
    plan = runner.build_plan(
        profile=profile,
        runtime_root=root,
        evidence_root=evidence,
        business_days=1,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id=RUN_ID,
    )
    run_dir = evidence / "runs" / RUN_ID
    runner.write_json_atomic(run_dir / "plan.json", plan)
    runner.write_json_atomic(
        run_dir / "run_state.json",
        {
            "schema_version": runner.RUN_STATE_SCHEMA_VERSION,
            "run_id": RUN_ID,
            "profile_id": "historical-smoke",
            "status": status,
            "next_job": "2026-07-06:submit",
            "completed_business_days": [],
            "completed_jobs": [
                {"business_date": "2026-07-06", "job": "market_refresh", "exit_code": 0},
                {"business_date": "2026-07-06", "job": "data_readiness", "exit_code": 0},
                {
                    "business_date": "2026-07-06",
                    "job": "submit",
                    "exit_code": 10,
                    "command": ["runtime-cli", "--job", "submit"],
                },
            ],
            "halted_at": {"business_date": "2026-07-06", "job": "submit", "exit_code": 10},
            "source_baseline": runner.source_baseline(root),
        },
    )
    runner.write_json_atomic(
        run_dir / "daily" / "2026-07-06" / "submit" / "runtime_manifest.json",
        {
            "run_id": "runtime-v2-submit-fixture",
            "job": "submit",
            "business_date": "2026-07-06",
            "exit_code": 10,
            "final_state": "BLOCKED",
            "reason": "fixture halt",
        },
    )
    runner.write_json_atomic(
        run_dir / "fresh_run_summary.json",
        {
            "schema_version": runner.FRESH_RUN_SUMMARY_SCHEMA_VERSION,
            "subcommand": "fresh-run",
            "fresh_run_id": "fresh-run-fixture",
            "run_id": RUN_ID,
            "profile_id": "historical-smoke",
            "status": status,
            "backup_id": "backup-fixture",
            "rollback_possible": True,
            "resume_possible": status == "HALT",
        },
    )
    return run_dir
