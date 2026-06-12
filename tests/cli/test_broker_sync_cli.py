import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.cli.broker_sync import main


def test_broker_sync_cli_runs_mock_mode_and_writes_under_runtime(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / ".runtime"

    exit_code = main(["--mode", "mock", "--runtime-dir", str(runtime_dir)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["source"] == "mock"
    assert payload["balance_snapshot_count"] == 1
    assert payload["position_snapshot_count"] == 1
    assert payload["order_snapshot_count"] == 1
    assert all(str(path).startswith(str(runtime_dir / "broker")) for path in payload["snapshot_paths"])
    assert (runtime_dir / "broker" / "snapshots" / "balance").is_dir()
    assert (runtime_dir / "broker" / "snapshots" / "positions").is_dir()
    assert (runtime_dir / "broker" / "snapshots" / "orders").is_dir()


def test_broker_sync_cli_is_mock_only(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["--mode", "live"])

    captured = capsys.readouterr()
    assert "invalid choice" in captured.err


def test_broker_sync_cli_does_not_print_secret_values(tmp_path: Path, capsys, monkeypatch) -> None:
    secret = "tachibana-secret-value"
    monkeypatch.setenv("TACHIBANA_API_AUTH_ID", secret)
    runtime_dir = tmp_path / ".runtime"

    exit_code = main(["--mode", "mock", "--runtime-dir", str(runtime_dir)])

    captured = capsys.readouterr()
    all_files_text = "".join(path.read_text(encoding="utf-8") for path in (runtime_dir / "broker").rglob("*.json"))
    assert exit_code == 0
    assert secret not in captured.out
    assert secret not in captured.err
    assert secret not in all_files_text
    assert "CLMAuthLoginRequest" not in all_files_text
