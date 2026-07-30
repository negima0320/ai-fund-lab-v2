from __future__ import annotations

from pathlib import Path

from scripts import runtime_test


def test_phase23_p_run_job_command_injects_historical_evaluation_authority(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    (runtime_root / "operations").mkdir(parents=True)
    authority_path = tmp_path / "run" / "historical_evaluation_authority.json"
    authority_path.parent.mkdir(parents=True)
    authority_path.write_text("{}", encoding="utf-8")
    job_record = {
        "business_date": "2022-09-01",
        "job": "morning",
        "feature_date": "2022-08-31",
        "command": [
            "python",
            "-m",
            "ai_fund_lab_v2.runtime_v2.cli.run_daily_operation",
            "--mode",
            "historical",
            "--business-date",
            "2022-09-01",
            "--job",
            "morning",
        ],
    }

    result = runtime_test.resolve_run_job_command(
        runtime_root=runtime_root,
        job_record=job_record,
        historical_evaluation_authority={"authority_path": str(authority_path)},
    )

    command = result["command"]
    assert "--historical-evaluation-authority" in command
    assert command[command.index("--historical-evaluation-authority") + 1] == str(authority_path)


def test_phase23_p_run_job_command_does_not_inject_authority_for_non_historical_mode(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    (runtime_root / "operations").mkdir(parents=True)
    job_record = {
        "business_date": "2026-07-21",
        "job": "morning",
        "command": [
            "python",
            "-m",
            "ai_fund_lab_v2.runtime_v2.cli.run_daily_operation",
            "--mode",
            "demo",
            "--business-date",
            "2026-07-21",
            "--job",
            "morning",
        ],
    }

    result = runtime_test.resolve_run_job_command(
        runtime_root=runtime_root,
        job_record=job_record,
        historical_evaluation_authority={"authority_path": str(tmp_path / "authority.json")},
    )

    assert "--historical-evaluation-authority" not in result["command"]
