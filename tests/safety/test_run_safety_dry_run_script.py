import json
from pathlib import Path

from ai_fund_lab_v2.broker import BrokerBalanceSnapshot, BrokerPositionSnapshot, BrokerRuntimePaths, BrokerSnapshotWriter
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.safety.run_safety_dry_run import build_parser, main


def test_dry_run_script_outputs_ok_result(tmp_path: Path, capsys) -> None:
    balance_path, positions_path = write_broker_snapshots(tmp_path)

    exit_code = main(
        [
            "--broker-snapshot",
            str(balance_path),
            "--broker-snapshot",
            str(positions_path),
            "--runtime-dir",
            str(tmp_path / ".runtime"),
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["status"] == "OK"
    assert output["issue_count"] == 0
    assert output["trading_locked"] is False
    assert Path(output["report_path"]).is_file()
    assert Path(output["lock_path"]).is_file()
    assert Path(output["audit_path"]).is_file()


def test_dry_run_script_outputs_halt_result(tmp_path: Path, capsys) -> None:
    balance_path, positions_path = write_broker_snapshots(tmp_path)

    exit_code = main(
        [
            "--broker-snapshot",
            str(balance_path),
            "--broker-snapshot",
            str(positions_path),
            "--runtime-dir",
            str(tmp_path / ".runtime"),
            "--mock-mismatch",
            "position_quantity",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert output["status"] == "HALT"
    assert output["issue_count"] == 1
    assert output["trading_locked"] is True


def test_dry_run_script_has_no_live_mode_or_real_api_args() -> None:
    parser = build_parser()
    option_strings = {option for action in parser._actions for option in action.option_strings}

    assert "--mode" not in option_strings
    assert "--live" not in option_strings
    assert "--base-url" not in option_strings
    assert "--api-key" not in option_strings


def test_dry_run_script_output_does_not_include_secret_or_url(tmp_path: Path, capsys) -> None:
    balance_path, positions_path = write_broker_snapshots(tmp_path, include_secret_like_warning=True)

    exit_code = main(
        [
            "--broker-snapshot",
            str(balance_path),
            "--broker-snapshot",
            str(positions_path),
            "--runtime-dir",
            str(tmp_path / ".runtime"),
        ]
    )

    captured = capsys.readouterr()
    saved_text = "".join(path.read_text(encoding="utf-8") for path in (tmp_path / ".runtime" / "safety").rglob("*.json"))
    assert exit_code == 0
    assert "secret-token" not in captured.out
    assert "https://example.invalid/session" not in captured.out
    assert "secret-token" not in saved_text
    assert "https://example.invalid/session" not in saved_text


def write_broker_snapshots(tmp_path: Path, include_secret_like_warning: bool = False) -> tuple[Path, Path]:
    writer = BrokerSnapshotWriter(BrokerRuntimePaths(RuntimePaths(runtime_dir=tmp_path / ".runtime")))
    warnings = ("token=secret-token https://example.invalid/session",) if include_secret_like_warning else ()
    balance_result = writer.write_balance(
        BrokerBalanceSnapshot(
            snapshot_id="balance-snapshot-1",
            as_of="2999-01-01T00:00:00+00:00",
            cash_available="1000",
            buying_power="900",
            warnings=warnings,
        )
    )
    positions_result = writer.write_positions(
        [
            BrokerPositionSnapshot(
                snapshot_id="position-snapshot-1",
                issue_code="7203",
                quantity="100",
                account_type="cash",
            )
        ]
    )
    return balance_result.data_path, positions_result.data_path
