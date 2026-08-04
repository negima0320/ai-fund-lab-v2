from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from tests.runtime_v2.test_phase17_k_runtime_test_runner import CONFIRM_FLAG, call_main, load_runner, make_runtime_root


def test_phase19_bh_fresh_run_plan_namespace_has_required_contract_fields() -> None:
    runner = load_runner()
    fresh_args = argparse.Namespace(
        business_days=1,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
    )

    plan_args = runner.plan_namespace_from_fresh_run(fresh_args)
    contract = runner.validate_plan_namespace(plan_args)

    assert contract["status"] == "PASS"
    assert contract["run_id_required_before_plan"] is False
    assert hasattr(plan_args, "run_id")
    assert plan_args.run_id is None
    assert plan_args.business_days == 1
    assert plan_args.start_date == "2026-07-06"


def test_phase19_bh_missing_plan_namespace_attribute_fails_explicitly() -> None:
    runner = load_runner()

    with pytest.raises(runner.RuntimeTestError) as excinfo:
        runner.validate_plan_namespace(argparse.Namespace(business_days=1, start_date="2026-07-06"))

    assert excinfo.value.status == "INVALID_ARGUMENT"
    assert "date_from" in str(excinfo.value)
    assert "run_id" in str(excinfo.value)


def test_phase19_bh_fresh_run_dry_run_validates_plan_request_contract(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    before_root = runner.directory_hash(root)

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
            "--dry-run",
        ],
        capsys,
    )

    assert payload["status"] == "DRY_RUN"
    assert payload["exit_code"] == 0
    assert payload["error"] == ""
    assert payload["plan_request_contract"]["plan_request_construction"] == "PASS"
    assert payload["plan_request_contract"]["runtime_test_run_id_generated_by"] == "plan"
    assert payload["plan_request_contract"]["fresh_run_id_is_runtime_test_run_id"] is False
    assert payload["plan_request_contract"]["backup_id_is_runtime_test_run_id"] is False
    assert payload["steps"]["plan"]["summary"]["plan_request_construction"] == "PASS"
    assert payload["run_id"].startswith("runtime-test-")
    assert payload["fresh_run_id"].startswith("fresh-run-")
    assert payload["run_id"] != payload["fresh_run_id"]
    assert runner.directory_hash(root) == before_root


def test_phase19_bh_runtime_test_run_id_is_passed_to_run_validate_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    commands: list[list[str]] = []
    validate_run_ids: list[str] = []
    close_run_ids: list[str] = []

    def fake_run(command: list[str], *, cwd: Path):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    original_validate = runner.validate_command
    original_close = runner.close_command

    def spy_validate(args, **kwargs):
        validate_run_ids.append(args.run_id)
        return original_validate(args, **kwargs)

    def spy_close(args, **kwargs):
        close_run_ids.append(args.run_id)
        return original_close(args, **kwargs)

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    monkeypatch.setattr(runner, "validate_command", spy_validate)
    monkeypatch.setattr(runner, "close_command", spy_close)

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
    assert payload["run_id"].startswith("runtime-test-")
    assert payload["fresh_run_id"].startswith("fresh-run-")
    assert payload["backup_id"].startswith("backup-")
    assert payload["run_id"] != payload["fresh_run_id"]
    assert payload["run_id"] != payload["backup_id"]
    assert validate_run_ids
    assert set(validate_run_ids) == {payload["run_id"]}
    assert close_run_ids == [payload["run_id"]]
    assert payload["steps"]["run"]["run_id"] == payload["run_id"]
    assert payload["steps"]["validate"]["status"] == "PASS"
    assert payload["steps"]["close"]["status"] == "BLOCK"
    assert all(payload["run_id"] in " ".join(command) for command in commands)
    assert payload["plan_request_contract"]["generated_runtime_test_run_id"] == payload["run_id"]
    assert payload["broker_write_performed"] is False
