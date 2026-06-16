from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_phase9i_cli_dry_run_default(tmp_path: Path) -> None:
    command = [
        "python3",
        "scripts/run_phase9i_market_data_refresh.py",
        "--from-date",
        "2026-06-02",
        "--to-date",
        "2026-06-16",
        "--raw-output-root",
        str(tmp_path / "raw"),
        "--normalized-output-root",
        str(tmp_path / "raw_normalized"),
        "--manifest-output-root",
        str(tmp_path / "manifest"),
        "--markdown-report-path",
        str(tmp_path / "report.md"),
        "--json-report-path",
        str(tmp_path / "report.json"),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(completed.stdout)

    assert payload["status"] == "DRY_RUN"
    assert Path(payload["manifest"]).exists()
    assert not (tmp_path / "raw/jquants/equities_bars_daily/data.parquet").exists()


def test_phase9i_cli_requires_date_range() -> None:
    completed = subprocess.run(
        ["python3", "scripts/run_phase9i_market_data_refresh.py", "--from-date", "2026-06-02"],
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "--to-date" in completed.stderr
