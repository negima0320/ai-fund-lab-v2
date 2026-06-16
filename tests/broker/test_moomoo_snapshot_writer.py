import json
from pathlib import Path

from ai_fund_lab_v2.broker.moomoo.snapshot_sync import write_moomoo_mock_snapshots


def test_moomoo_mock_snapshot_writer_saves_all_snapshot_kinds(tmp_path: Path) -> None:
    result = write_moomoo_mock_snapshots(tmp_path / ".runtime")

    assert result.accounts.data_path.parent.name == "accounts"
    assert result.balance.data_path.parent.name == "balance"
    assert result.positions.data_path.parent.name == "positions"
    assert result.orders.data_path.parent.name == "orders"
    assert result.executions.data_path.parent.name == "executions"
    assert result.sync_result.data_path.parent.name == "sync_results"

    payload = json.loads(result.balance.data_path.read_text(encoding="utf-8"))
    assert payload["kind"] == "balance"
    assert payload["records"][0]["broker"] == "moomoo"
    assert payload["records"][0]["cash_available"] == "1200000"

    sync_payload = json.loads(result.sync_result.data_path.read_text(encoding="utf-8"))
    sync_record = sync_payload["records"][0]
    assert sync_record["broker"] == "moomoo"
    assert sync_record["account_snapshot_count"] == 1
    assert sync_record["execution_snapshot_count"] == 2


def test_moomoo_snapshot_writer_does_not_save_plain_account_numbers(tmp_path: Path) -> None:
    result = write_moomoo_mock_snapshots(tmp_path / ".runtime")

    saved_text = (
        result.accounts.data_path.read_text(encoding="utf-8")
        + result.balance.data_path.read_text(encoding="utf-8")
        + result.sync_result.data_path.read_text(encoding="utf-8")
    )
    assert "acc_id" not in saved_text
    assert "card_num" not in saved_text
    assert "uni_card_num" not in saved_text

