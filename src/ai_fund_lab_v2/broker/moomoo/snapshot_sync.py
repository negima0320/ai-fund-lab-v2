from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_fund_lab_v2.broker.models import (
    BrokerAccountSnapshot,
    BrokerBalanceSnapshot,
    BrokerExecutionSnapshot,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    utc_now_iso,
)
from ai_fund_lab_v2.broker.moomoo.mock_fixtures import build_moomoo_mock_response
from ai_fund_lab_v2.broker.moomoo.normalizer import normalize_moomoo_mock_response
from ai_fund_lab_v2.broker.runtime_paths import BrokerRuntimePaths
from ai_fund_lab_v2.broker.snapshot_writer import BrokerSnapshotWriteResult, BrokerSnapshotWriter
from ai_fund_lab_v2.broker.sync_result import BrokerSyncResult


@dataclass(frozen=True)
class MoomooNormalizedSnapshots:
    accounts: list[BrokerAccountSnapshot]
    balance: BrokerBalanceSnapshot
    positions: list[BrokerPositionSnapshot]
    orders: list[BrokerOrderSnapshot]
    executions: list[BrokerExecutionSnapshot]


@dataclass(frozen=True)
class MoomooMockSnapshotWriteResult:
    accounts: BrokerSnapshotWriteResult
    balance: BrokerSnapshotWriteResult
    positions: BrokerSnapshotWriteResult
    orders: BrokerSnapshotWriteResult
    executions: BrokerSnapshotWriteResult
    sync_result: BrokerSnapshotWriteResult
    broker_sync_result: BrokerSyncResult


def normalize_default_moomoo_mock_response() -> MoomooNormalizedSnapshots:
    normalized = normalize_moomoo_mock_response(build_moomoo_mock_response())
    return MoomooNormalizedSnapshots(
        accounts=list(normalized["accounts"]),  # type: ignore[arg-type]
        balance=normalized["balance"],  # type: ignore[assignment]
        positions=list(normalized["positions"]),  # type: ignore[arg-type]
        orders=list(normalized["orders"]),  # type: ignore[arg-type]
        executions=list(normalized["executions"]),  # type: ignore[arg-type]
    )


def write_moomoo_mock_snapshots(runtime_dir: Path) -> MoomooMockSnapshotWriteResult:
    paths = BrokerRuntimePaths.from_runtime_dir(runtime_dir) if hasattr(BrokerRuntimePaths, "from_runtime_dir") else None
    if paths is None:
        from ai_fund_lab_v2.runtime import RuntimePaths

        paths = BrokerRuntimePaths(RuntimePaths(runtime_dir=runtime_dir))
    writer = BrokerSnapshotWriter(paths)
    normalized = normalize_default_moomoo_mock_response()

    accounts_result = writer.write_accounts(normalized.accounts)
    balance_result = writer.write_balance(normalized.balance)
    positions_result = writer.write_positions(normalized.positions)
    orders_result = writer.write_orders(normalized.orders)
    executions_result = writer.write_executions(normalized.executions)

    snapshot_paths = tuple(
        str(result.data_path)
        for result in (accounts_result, balance_result, positions_result, orders_result, executions_result)
    )
    manifest_paths = tuple(
        str(result.manifest_path)
        for result in (accounts_result, balance_result, positions_result, orders_result, executions_result)
    )
    broker_sync_result = BrokerSyncResult(
        broker="moomoo",
        source="mock",
        finished_at=utc_now_iso(),
        status="success",
        account_snapshot_count=accounts_result.record_count,
        balance_snapshot_count=balance_result.record_count,
        position_snapshot_count=positions_result.record_count,
        order_snapshot_count=orders_result.record_count,
        execution_snapshot_count=executions_result.record_count,
        snapshot_paths=snapshot_paths,
        manifest_paths=manifest_paths,
    )
    sync_result = writer.write_sync_result(broker_sync_result)
    return MoomooMockSnapshotWriteResult(
        accounts=accounts_result,
        balance=balance_result,
        positions=positions_result,
        orders=orders_result,
        executions=executions_result,
        sync_result=sync_result,
        broker_sync_result=broker_sync_result,
    )

