from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests.runtime_v2.test_phase17_k_runtime_test_runner import CONFIRM_FLAG, call_main, load_runner, make_runtime_root


def test_phase18v_fresh_run_dry_run_has_full_plan_and_no_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"

    def forbidden_run(command: list[str], *, cwd: Path):
        raise AssertionError("Runtime CLI must not run during fresh-run dry-run")

    monkeypatch.setattr(runner, "run_runtime_cli", forbidden_run)
    before_root = runner.directory_hash(root)
    before_evidence_exists = evidence.exists()
    payload = call_main(
        runner,
        [
            "fresh-run",
            "--profile",
            "historical-extended-smoke",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(evidence),
            "--date-from",
            "2026-06-29",
            "--date-to",
            "2026-07-10",
            "--business-days",
            "10",
            "--initial-cash",
            "1000000",
            "--dry-run",
        ],
        capsys,
    )
    assert payload["status"] == "DRY_RUN"
    assert payload["dry_run_no_mutation"] is True
    assert payload["steps"]["backup"]["status"] == "PLANNED_NO_WRITE"
    assert payload["steps"]["run"]["status"] == "PLANNED_NO_EXECUTION"
    assert payload["business_days"] == 10
    assert payload["date_from"] == "2026-06-29"
    assert payload["date_to"] == "2026-07-10"
    assert payload["external_effect_policy"]["broker_write"] is False
    assert runner.directory_hash(root) == before_root
    assert evidence.exists() is before_evidence_exists


def test_phase18v_fresh_run_happy_path_reuses_normal_runtime_cli_and_closes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
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
            "--confirm",
            CONFIRM_FLAG,
        ],
        capsys,
    )
    assert payload["status"] == "BLOCK"
    assert payload["backup_id"].startswith("backup-")
    assert payload["run_id"].startswith("runtime-test-")
    assert payload["steps"]["run"]["status"] == "PASS"
    assert payload["steps"]["validate"]["status"] == "PASS"
    assert payload["steps"]["close"]["status"] == "BLOCK"
    assert len(commands) == len(runner.JOB_SEQUENCE)
    assert commands[0][commands[0].index("-m") + 1] == runner.RUNTIME_CLI_MODULE
    assert (evidence / "runs" / payload["run_id"] / "plan.json").is_file()
    assert (evidence / "runs" / payload["run_id"] / "fresh_run_summary.json").is_file()
    assert payload["registry_unchanged"] is True
    assert payload["broker_write_performed"] is False


def test_phase18v_fresh_run_backup_failure_stops_before_reset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)

    def fail_backup(*_args, **_kwargs):
        raise runner.RuntimeTestError("backup failed fixture", status="PRECONDITION_FAILURE", exit_code=runner.EXIT_PRECONDITION_FAILURE)

    monkeypatch.setattr(runner, "backup_command", fail_backup)
    payload = call_main(
        runner,
        ["fresh-run", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    assert payload["status"] == "PRECONDITION_FAILURE"
    assert payload["failed_step"] == "backup"
    assert payload["steps"]["reset"]["status"] == "NOT_EXECUTED"
    assert payload["steps"]["run"]["status"] == "NOT_EXECUTED"


def test_phase18v_fresh_run_reset_failure_stops_before_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)

    def fail_reset(*_args, **_kwargs):
        raise runner.RuntimeTestError("reset failed fixture", status="ROLLBACK_REQUIRED", exit_code=runner.EXIT_ROLLBACK_FAILURE)

    monkeypatch.setattr(runner, "reset_command", fail_reset)
    payload = call_main(
        runner,
        ["fresh-run", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    assert payload["status"] == "ROLLBACK_REQUIRED"
    assert payload["failed_step"] == "reset"
    assert payload["steps"]["plan"]["status"] == "NOT_EXECUTED"
    assert payload["rollback_possible"] is True


def test_phase18v_fresh_run_plan_failure_stops_before_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)

    def fail_plan(*_args, **_kwargs):
        raise runner.RuntimeTestError("plan failed fixture", status="PRECONDITION_FAILURE", exit_code=runner.EXIT_PRECONDITION_FAILURE)

    monkeypatch.setattr(runner, "plan_command", fail_plan)
    payload = call_main(
        runner,
        ["fresh-run", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    assert payload["status"] == "PRECONDITION_FAILURE"
    assert payload["failed_step"] == "plan"
    assert payload["steps"]["run"]["status"] == "NOT_EXECUTED"


def test_phase18v_fresh_run_run_halt_skips_validate_and_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)

    def halt_run(command: list[str], *, cwd: Path):
        return subprocess.CompletedProcess(command, 30, "", "halt")

    monkeypatch.setattr(runner, "run_runtime_cli", halt_run)
    payload = call_main(
        runner,
        ["fresh-run", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    assert payload["status"] == "HALT"
    assert payload["failed_step"] == "run"
    assert payload["steps"]["validate"]["status"] == "NOT_EXECUTED"
    assert payload["steps"]["close"]["status"] == "NOT_EXECUTED"
    assert payload["resume_possible"] is True
    assert payload["rollback_possible"] is True


def test_phase18v_fresh_run_validate_failure_skips_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)

    def fake_run(command: list[str], *, cwd: Path):
        return subprocess.CompletedProcess(command, 0, "", "")

    def fail_validate(*_args, **_kwargs):
        return runner.CommandResult("VALIDATION_FAILURE", runner.EXIT_VALIDATION_FAILURE, {"status": "VALIDATION_FAILURE", "exit_code": runner.EXIT_VALIDATION_FAILURE, "error": "validate failed fixture"})

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    monkeypatch.setattr(runner, "validate_command", fail_validate)
    payload = call_main(
        runner,
        ["fresh-run", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    assert payload["status"] == "VALIDATION_FAILURE"
    assert payload["failed_step"] == "validate"
    assert payload["steps"]["close"]["status"] == "NOT_EXECUTED"


def test_phase18v_auto_prepare_is_not_ambiguous_noop(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    payload = call_main(
        runner,
        ["run", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--business-days", "1", "--start-date", "2026-07-06", "--auto-prepare", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    assert payload["status"] == "INVALID_ARGUMENT"
    assert "fresh-run" in payload["error"]


def test_phase18v_fresh_run_production_profile_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    production_profile = tmp_path / "production_profile.json"
    profile = json.loads(Path("config/runtime_tests/historical_smoke_5bd.json").read_text(encoding="utf-8"))
    profile["profile_id"] = "production-fixture"
    profile["mode"] = "production"
    profile["runtime_root"] = str(root)
    production_profile.write_text(json.dumps(profile), encoding="utf-8")
    payload = call_main(
        runner,
        ["fresh-run", "--profile", str(production_profile), "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--business-days", "1", "--dry-run"],
        capsys,
    )
    assert payload["status"] == "HALT"
