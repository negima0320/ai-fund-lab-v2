import json
from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.broker import (
    BrokerBalanceSnapshot,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    BrokerRuntimePaths,
    BrokerSnapshotWriter,
)
from ai_fund_lab_v2.runtime import RuntimePaths


def test_snapshot_writer_saves_balance_under_runtime_broker(tmp_path: Path) -> None:
    paths = BrokerRuntimePaths(RuntimePaths(runtime_dir=tmp_path / ".runtime"))
    writer = BrokerSnapshotWriter(paths)
    snapshot = BrokerBalanceSnapshot(
        as_of="2026-06-12T00:00:00+00:00",
        cash_available=Decimal("100000"),
        buying_power=Decimal("90000"),
        withdrawable_cash=Decimal("80000"),
        total_assets=Decimal("120000"),
        raw_clmid="CLMZanKaiSummary",
        raw_result_code="0",
    )

    result = writer.write_balance(snapshot)

    assert result.record_count == 1
    assert result.data_path.is_file()
    assert result.manifest_path.is_file()
    assert result.data_path.parent == paths.balance_snapshots
    assert str(result.data_path).startswith(str(paths.broker_root))
    payload = json.loads(result.data_path.read_text(encoding="utf-8"))
    assert payload["kind"] == "balance"
    assert payload["records"][0]["cash_available"] == "100000"


def test_snapshot_writer_saves_positions_and_orders_as_json(tmp_path: Path) -> None:
    paths = BrokerRuntimePaths(RuntimePaths(runtime_dir=tmp_path / ".runtime"))
    writer = BrokerSnapshotWriter(paths)

    positions_result = writer.write_positions(
        [
            BrokerPositionSnapshot(
                as_of="2026-06-12T00:00:00+00:00",
                issue_code="7203",
                quantity=Decimal("100"),
                raw_clmid="CLMGenbutuKabuList",
                raw_result_code="0",
            )
        ]
    )
    orders_result = writer.write_orders(
        [
            BrokerOrderSnapshot(
                as_of="2026-06-12T00:00:00+00:00",
                order_id="ORD-001",
                issue_code="7203",
                quantity=Decimal("100"),
                price=Decimal("2500.5"),
                raw_clmid="CLMOrderList",
                raw_result_code="0",
            )
        ]
    )

    positions_payload = json.loads(positions_result.data_path.read_text(encoding="utf-8"))
    orders_payload = json.loads(orders_result.data_path.read_text(encoding="utf-8"))

    assert positions_result.data_path.parent == paths.positions_snapshots
    assert orders_result.data_path.parent == paths.orders_snapshots
    assert positions_payload["records"][0]["quantity"] == "100"
    assert orders_payload["records"][0]["price"] == "2500.5"


def test_snapshot_writer_sanitizes_secret_values_before_saving(tmp_path: Path) -> None:
    paths = BrokerRuntimePaths(RuntimePaths(runtime_dir=tmp_path / ".runtime"))
    writer = BrokerSnapshotWriter(paths)
    snapshot = BrokerBalanceSnapshot(
        as_of="2026-06-12T00:00:00+00:00",
        cash_available=Decimal("100000"),
        buying_power=Decimal("90000"),
        withdrawable_cash=Decimal("80000"),
        total_assets=Decimal("120000"),
        raw_clmid="CLMZanKaiSummary",
        raw_result_code="0",
        warnings=("token leaked? https://example.invalid/session", "sAuthId=secret-auth-id", "account_id=123456"),
    )

    result = writer.write_balance(snapshot)

    data_text = result.data_path.read_text(encoding="utf-8")
    manifest_text = result.manifest_path.read_text(encoding="utf-8")
    saved_text = data_text + manifest_text
    assert "https://example.invalid/session" not in saved_text
    assert "secret-auth-id" not in saved_text
    assert "123456" not in saved_text
    assert "[REDACTED]" in saved_text
