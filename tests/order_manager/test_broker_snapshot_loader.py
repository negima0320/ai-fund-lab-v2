import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.broker.moomoo.snapshot_sync import write_moomoo_mock_snapshots
from ai_fund_lab_v2.order_manager.broker_snapshot_loader import (
    BrokerSnapshotLoadError,
    load_latest_broker_snapshot_bundle,
)


def test_broker_snapshot_loader_reads_latest_normalized_snapshots(tmp_path: Path) -> None:
    write_moomoo_mock_snapshots(tmp_path / ".runtime")

    bundle = load_latest_broker_snapshot_bundle(tmp_path / ".runtime")

    assert bundle.accounts[0].broker == "moomoo"
    assert bundle.balance.cash_available > 0
    assert [position.issue_code for position in bundle.positions] == ["7203", "6758"]
    assert len(bundle.orders) == 2
    assert len(bundle.executions) == 2
    assert bundle.sync_result.broker == "moomoo"
    assert bundle.broker_snapshot_id.startswith("balance_")


def test_broker_snapshot_loader_fail_closed_on_missing_snapshot(tmp_path: Path) -> None:
    with pytest.raises(BrokerSnapshotLoadError):
        load_latest_broker_snapshot_bundle(tmp_path / ".runtime")


def test_broker_snapshot_loader_fail_closed_on_corrupt_snapshot(tmp_path: Path) -> None:
    write_moomoo_mock_snapshots(tmp_path / ".runtime")
    balance_file = _data_json(tmp_path / ".runtime" / "broker" / "snapshots" / "balance")
    balance_file.write_text("{not-json", encoding="utf-8")

    with pytest.raises(BrokerSnapshotLoadError):
        load_latest_broker_snapshot_bundle(tmp_path / ".runtime")


def test_broker_snapshot_loader_fail_closed_on_as_of_mismatch(tmp_path: Path) -> None:
    write_moomoo_mock_snapshots(tmp_path / ".runtime")
    positions_file = _data_json(tmp_path / ".runtime" / "broker" / "snapshots" / "positions")
    payload = json.loads(positions_file.read_text(encoding="utf-8"))
    payload["records"][0]["as_of"] = "2026-06-16T00:00:00+09:00"
    positions_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BrokerSnapshotLoadError, match="as_of mismatch"):
        load_latest_broker_snapshot_bundle(tmp_path / ".runtime")


def _data_json(directory: Path) -> Path:
    return next(path for path in directory.glob("*.json") if not path.name.endswith(".manifest.json"))
