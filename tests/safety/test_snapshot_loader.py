import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.broker import BrokerBalanceSnapshot, BrokerPositionSnapshot, BrokerRuntimePaths, BrokerSnapshotWriter
from ai_fund_lab_v2.runtime import RuntimePaths
from ai_fund_lab_v2.safety import SafetySnapshotLoadError, load_broker_snapshot, load_broker_state_from_snapshot_files


def test_snapshot_json_can_be_loaded(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps({"kind": "balance", "records": [{"snapshot_id": "balance-1"}]}), encoding="utf-8")

    payload = load_broker_snapshot(path)

    assert payload["kind"] == "balance"
    assert payload["records"][0]["snapshot_id"] == "balance-1"


def test_missing_snapshot_path_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(SafetySnapshotLoadError, match="does not exist"):
        load_broker_snapshot(tmp_path / "missing.json")


def test_broken_json_fails_clearly(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(SafetySnapshotLoadError, match="not valid JSON"):
        load_broker_snapshot(path)


def test_snapshot_files_can_build_broker_state(tmp_path: Path) -> None:
    broker_paths = BrokerRuntimePaths(RuntimePaths(runtime_dir=tmp_path / ".runtime"))
    writer = BrokerSnapshotWriter(broker_paths)
    balance_result = writer.write_balance(BrokerBalanceSnapshot(snapshot_id="balance-1", cash_available="1000", buying_power="900"))
    positions_result = writer.write_positions([BrokerPositionSnapshot(snapshot_id="position-1", issue_code="7203", quantity="100")])

    state = load_broker_state_from_snapshot_files([balance_result.data_path, positions_result.data_path])

    assert state.source_snapshot_id == "balance-1"
    assert state.cash == 1000
    assert state.positions[0].symbol == "7203"
    assert state.positions[0].quantity == 100
