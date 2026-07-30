from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.runtime import RuntimePaths
from scripts import repair_jquants_raw_business_keys as repair_cli


def test_repair_fins_summary_legacy_key_dry_run_does_not_write(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    path = write_fins_summary(runtime_dir)
    before = path.read_bytes()

    exit_code = repair_cli.main(
        [
            "--endpoint",
            "fins_summary",
            "--from-date",
            "2026-07-06",
            "--to-date",
            "2026-07-17",
            "--runtime-dir",
            str(runtime_dir),
            "--dry-run",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "DRY_RUN"
    assert payload["legacy_rows_removed"] == 1
    assert payload["pre_summary"]["target_range_repaired_rows"] == 2
    assert payload["pre_summary"]["target_range_unknown_rows"] == 1
    assert path.read_bytes() == before


def test_repair_fins_summary_legacy_key_live_keeps_repaired_unknown_and_outside_rows(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    path = write_fins_summary(runtime_dir)
    manifest = RuntimePaths(runtime_dir=runtime_dir).raw_data / "jquants" / "manifest.jsonl"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text('{"existing": true}\n', encoding="utf-8")

    exit_code = repair_cli.main(
        [
            "--endpoint",
            "fins_summary",
            "--from-date",
            "2026-07-06",
            "--to-date",
            "2026-07-17",
            "--runtime-dir",
            str(runtime_dir),
            "--confirm",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    frame = pd.read_parquet(path)
    assert exit_code == 0
    assert payload["status"] == "REPAIRED"
    assert payload["legacy_rows_removed"] == 1
    assert len(frame) == 4
    assert "72030" not in set(frame["business_key"])
    assert "mystery-key" in set(frame["business_key"])
    assert "13010" in set(frame["business_key"])
    assert manifest.read_text(encoding="utf-8") == '{"existing": true}\n'
    backup_dir = Path(payload["backup_dir"])
    assert (backup_dir / "data.parquet").is_file()
    assert (backup_dir / "manifest.jsonl").is_file()
    assert (backup_dir / "pre_cleanup_summary.json").is_file()
    assert (backup_dir / "pre_cleanup_hashes.json").is_file()
    assert (backup_dir / "repair_result.json").is_file()


def test_repair_fins_summary_legacy_key_requires_confirm_for_live(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    write_fins_summary(runtime_dir)

    exit_code = repair_cli.main(
        [
            "--endpoint",
            "fins_summary",
            "--from-date",
            "2026-07-06",
            "--to-date",
            "2026-07-17",
            "--runtime-dir",
            str(runtime_dir),
        ]
    )

    assert exit_code == 2
    assert "requires --confirm" in capsys.readouterr().err


def test_repair_fins_summary_legacy_key_is_idempotent_no_change(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    path = write_fins_summary(runtime_dir)
    args = [
        "--endpoint",
        "fins_summary",
        "--from-date",
        "2026-07-06",
        "--to-date",
        "2026-07-17",
        "--runtime-dir",
        str(runtime_dir),
        "--confirm",
    ]

    assert repair_cli.main(args) == 0
    capsys.readouterr()
    after_first = path.read_bytes()
    assert repair_cli.main(args) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "NO_CHANGE"
    assert payload["legacy_rows_removed"] == 0
    assert path.read_bytes() == after_first


def test_repair_fins_summary_legacy_key_failure_keeps_original_and_manifest(tmp_path: Path, monkeypatch, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    path = write_fins_summary(runtime_dir)
    before = path.read_bytes()
    manifest = RuntimePaths(runtime_dir=runtime_dir).raw_data / "jquants" / "manifest.jsonl"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text('{"existing": true}\n', encoding="utf-8")

    class FailedValidation:
        status = "ERROR"
        messages = ["forced failure"]

        def to_dict(self) -> dict[str, Any]:
            return {"status": self.status, "messages": self.messages}

    monkeypatch.setattr(repair_cli, "validate_records", lambda *args, **kwargs: FailedValidation())

    try:
        repair_cli.main(
            [
                "--endpoint",
                "fins_summary",
                "--from-date",
                "2026-07-06",
                "--to-date",
                "2026-07-17",
                "--runtime-dir",
                str(runtime_dir),
                "--confirm",
            ]
        )
    except RuntimeError as exc:
        assert "post-cleanup validation failed" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")

    assert path.read_bytes() == before
    assert manifest.read_text(encoding="utf-8") == '{"existing": true}\n'


def write_fins_summary(runtime_dir: Path) -> Path:
    path = runtime_dir / "data" / "raw" / "jquants" / "fins_summary" / "data.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "DiscDate": "2026-07-06",
                "target_date": "2026-07-06",
                "Code": "72030",
                "DiscNo": "20260706590001",
                "business_key": "72030",
                "endpoint": "/v2/fins/summary",
            },
            {
                "DiscDate": "2026-07-06",
                "target_date": "2026-07-06",
                "Code": "72030",
                "DiscNo": "20260706590001",
                "business_key": "fins_summary:2026-07-06:72030:20260706590001",
                "endpoint": "/v2/fins/summary",
            },
            {
                "DiscDate": "2026-07-06",
                "target_date": "2026-07-06",
                "Code": "72030",
                "DiscNo": "20260706590002",
                "business_key": "fins_summary:2026-07-06:72030:20260706590002",
                "endpoint": "/v2/fins/summary",
            },
            {
                "DiscDate": "2026-07-06",
                "target_date": "2026-07-06",
                "Code": "99990",
                "DiscNo": "20260706590003",
                "business_key": "mystery-key",
                "endpoint": "/v2/fins/summary",
            },
            {
                "DiscDate": "2026-06-01",
                "target_date": "2026-06-01",
                "Code": "13010",
                "DiscNo": "20260601590001",
                "business_key": "13010",
                "endpoint": "/v2/fins/summary",
            },
        ]
    ).to_parquet(path, index=False)
    return path
