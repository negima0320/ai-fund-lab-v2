from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, TypeVar

from ai_fund_lab_v2.broker.models import (
    BrokerAccountSnapshot,
    BrokerBalanceSnapshot,
    BrokerExecutionSnapshot,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
)
from ai_fund_lab_v2.broker.runtime_paths import BrokerRuntimePaths
from ai_fund_lab_v2.broker.sync_result import BrokerSyncResult
from ai_fund_lab_v2.runtime import RuntimePaths


class BrokerSnapshotLoadError(RuntimeError):
    pass


@dataclass(frozen=True)
class BrokerSnapshotBundle:
    accounts: list[BrokerAccountSnapshot]
    balance: BrokerBalanceSnapshot
    positions: list[BrokerPositionSnapshot]
    orders: list[BrokerOrderSnapshot]
    executions: list[BrokerExecutionSnapshot]
    sync_result: BrokerSyncResult
    snapshot_batch_ids: dict[str, str]

    @property
    def broker_snapshot_id(self) -> str:
        return self.snapshot_batch_ids.get("balance", "")


T = TypeVar("T")


def load_latest_broker_snapshot_bundle(runtime_dir: Path | str = ".runtime") -> BrokerSnapshotBundle:
    paths = BrokerRuntimePaths(RuntimePaths(runtime_dir=Path(runtime_dir)))
    accounts_payload = _read_latest_payload(paths.account_snapshots, "accounts")
    balance_payload = _read_latest_payload(paths.balance_snapshots, "balance")
    positions_payload = _read_latest_payload(paths.positions_snapshots, "positions")
    orders_payload = _read_latest_payload(paths.orders_snapshots, "orders")
    executions_payload = _read_latest_payload(paths.executions_snapshots, "executions")
    sync_payload = _read_latest_payload(paths.sync_results, "sync_result")

    accounts = _records(accounts_payload, "accounts", lambda record: _account(record))
    balances = _records(balance_payload, "balance", lambda record: _balance(record))
    positions = _records(positions_payload, "positions", lambda record: _position(record))
    orders = _records(orders_payload, "orders", lambda record: _order(record))
    executions = _records(executions_payload, "executions", lambda record: _execution(record))
    sync_records = _records(sync_payload, "sync_result", lambda record: _sync_result(record))

    if len(balances) != 1:
        raise BrokerSnapshotLoadError("Balance snapshot must contain exactly one record.")
    if len(sync_records) != 1:
        raise BrokerSnapshotLoadError("Sync result must contain exactly one record.")
    _validate_as_of({balances[0].as_of, *(account.as_of for account in accounts), *(p.as_of for p in positions), *(o.as_of for o in orders), *(e.as_of for e in executions)})

    return BrokerSnapshotBundle(
        accounts=accounts,
        balance=balances[0],
        positions=positions,
        orders=orders,
        executions=executions,
        sync_result=sync_records[0],
        snapshot_batch_ids={
            "accounts": str(accounts_payload.get("batch_id", "")),
            "balance": str(balance_payload.get("batch_id", "")),
            "positions": str(positions_payload.get("batch_id", "")),
            "orders": str(orders_payload.get("batch_id", "")),
            "executions": str(executions_payload.get("batch_id", "")),
            "sync_result": str(sync_payload.get("batch_id", "")),
        },
    )


def _read_latest_payload(directory: Path, expected_kind: str) -> dict[str, Any]:
    if not directory.exists():
        raise BrokerSnapshotLoadError(f"Missing broker snapshot directory: {directory}")
    candidates = sorted(
        (path for path in directory.glob("*.json") if path.is_file() and not path.name.endswith(".manifest.json")),
        key=lambda path: (path.stat().st_mtime, path.name),
    )
    if not candidates:
        raise BrokerSnapshotLoadError(f"Missing broker snapshot file for kind={expected_kind}.")
    latest = candidates[-1]
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BrokerSnapshotLoadError(f"Invalid broker snapshot JSON for kind={expected_kind}: {latest}") from exc
    if not isinstance(payload, dict):
        raise BrokerSnapshotLoadError(f"Broker snapshot payload must be an object for kind={expected_kind}.")
    if payload.get("kind") != expected_kind:
        raise BrokerSnapshotLoadError(f"Broker snapshot kind mismatch: expected={expected_kind} actual={payload.get('kind')}")
    if "records" not in payload or not isinstance(payload["records"], list):
        raise BrokerSnapshotLoadError(f"Broker snapshot records missing for kind={expected_kind}.")
    return payload


def _records(payload: dict[str, Any], kind: str, factory: Callable[[dict[str, Any]], T]) -> list[T]:
    records = payload.get("records")
    if not isinstance(records, list):
        raise BrokerSnapshotLoadError(f"Snapshot records must be list for kind={kind}.")
    result: list[T] = []
    for record in records:
        if not isinstance(record, dict):
            raise BrokerSnapshotLoadError(f"Snapshot record must be object for kind={kind}.")
        result.append(factory(record))
    return result


def _account(record: dict[str, Any]) -> BrokerAccountSnapshot:
    return BrokerAccountSnapshot(
        broker=str(record.get("broker", "")),
        source=str(record.get("source", "")),
        as_of=str(record.get("as_of", "")),
        account_ref=str(record.get("account_ref", "")),
        account_label=str(record.get("account_label", "")),
        environment=str(record.get("environment", "")),
        account_type=str(record.get("account_type", "")),
        broker_account_status=str(record.get("broker_account_status", "")),
        trade_market_auth=tuple(str(value) for value in record.get("trade_market_auth", []) if value is not None),
        raw_method=str(record.get("raw_method", "")),
        raw_result_code=str(record.get("raw_result_code", "")),
        warnings=tuple(str(value) for value in record.get("warnings", []) if value is not None),
        snapshot_id=str(record.get("snapshot_id", "")),
    )


def _balance(record: dict[str, Any]) -> BrokerBalanceSnapshot:
    return BrokerBalanceSnapshot(
        broker=str(record.get("broker", "")),
        source=str(record.get("source", "")),
        as_of=str(record.get("as_of", "")),
        currency=str(record.get("currency", "JPY")),
        cash_available=_decimal(record.get("cash_available")),
        buying_power=_decimal(record.get("buying_power")),
        withdrawable_cash=_decimal(record.get("withdrawable_cash")),
        total_assets=_decimal(record.get("total_assets")),
        raw_clmid=str(record.get("raw_clmid", "")),
        raw_method=str(record.get("raw_method", "")),
        raw_result_code=str(record.get("raw_result_code", "")),
        warnings=tuple(str(value) for value in record.get("warnings", []) if value is not None),
        snapshot_id=str(record.get("snapshot_id", "")),
    )


def _position(record: dict[str, Any]) -> BrokerPositionSnapshot:
    return BrokerPositionSnapshot(
        broker=str(record.get("broker", "")),
        source=str(record.get("source", "")),
        as_of=str(record.get("as_of", "")),
        account_type=str(record.get("account_type", "cash")),
        issue_code=str(record.get("issue_code", "")),
        issue_name=str(record.get("issue_name", "")),
        quantity=_decimal(record.get("quantity")),
        available_quantity=_decimal(record.get("available_quantity")),
        average_price=_decimal(record.get("average_price")),
        market_price=_decimal(record.get("market_price")),
        market_value=_decimal(record.get("market_value")),
        unrealized_pnl=_decimal(record.get("unrealized_pnl")),
        raw_clmid=str(record.get("raw_clmid", "")),
        raw_method=str(record.get("raw_method", "")),
        raw_result_code=str(record.get("raw_result_code", "")),
        warnings=tuple(str(value) for value in record.get("warnings", []) if value is not None),
        snapshot_id=str(record.get("snapshot_id", "")),
    )


def _order(record: dict[str, Any]) -> BrokerOrderSnapshot:
    return BrokerOrderSnapshot(
        broker=str(record.get("broker", "")),
        source=str(record.get("source", "")),
        as_of=str(record.get("as_of", "")),
        order_id=str(record.get("order_id", "")),
        issue_code=str(record.get("issue_code", "")),
        issue_name=str(record.get("issue_name", "")),
        side=str(record.get("side", "")),
        order_type=str(record.get("order_type", "")),
        quantity=_decimal(record.get("quantity")),
        executed_quantity=_decimal(record.get("executed_quantity")),
        remaining_quantity=_decimal(record.get("remaining_quantity")),
        price=_decimal(record.get("price")),
        status=str(record.get("status", "")),
        order_datetime=str(record.get("order_datetime", "")),
        expire_date=str(record.get("expire_date", "")),
        raw_clmid=str(record.get("raw_clmid", "")),
        raw_method=str(record.get("raw_method", "")),
        raw_result_code=str(record.get("raw_result_code", "")),
        warnings=tuple(str(value) for value in record.get("warnings", []) if value is not None),
        snapshot_id=str(record.get("snapshot_id", "")),
    )


def _execution(record: dict[str, Any]) -> BrokerExecutionSnapshot:
    return BrokerExecutionSnapshot(
        broker=str(record.get("broker", "")),
        source=str(record.get("source", "")),
        as_of=str(record.get("as_of", "")),
        execution_id=str(record.get("execution_id", "")),
        order_id=str(record.get("order_id", "")),
        issue_code=str(record.get("issue_code", "")),
        issue_name=str(record.get("issue_name", "")),
        side=str(record.get("side", "")),
        quantity=_decimal(record.get("quantity")),
        price=_decimal(record.get("price")),
        executed_at=str(record.get("executed_at", "")),
        currency=str(record.get("currency", "JPY")),
        raw_method=str(record.get("raw_method", "")),
        raw_result_code=str(record.get("raw_result_code", "")),
        warnings=tuple(str(value) for value in record.get("warnings", []) if value is not None),
        snapshot_id=str(record.get("snapshot_id", "")),
    )


def _sync_result(record: dict[str, Any]) -> BrokerSyncResult:
    return BrokerSyncResult(
        broker=str(record.get("broker", "")),
        source=str(record.get("source", "")),
        started_at=str(record.get("started_at", "")),
        finished_at=str(record.get("finished_at", "")),
        status=str(record.get("status", "")),
        account_snapshot_count=int(record.get("account_snapshot_count", 0)),
        balance_snapshot_count=int(record.get("balance_snapshot_count", 0)),
        position_snapshot_count=int(record.get("position_snapshot_count", 0)),
        order_snapshot_count=int(record.get("order_snapshot_count", 0)),
        execution_snapshot_count=int(record.get("execution_snapshot_count", 0)),
        snapshot_paths=tuple(str(value) for value in record.get("snapshot_paths", [])),
        manifest_paths=tuple(str(value) for value in record.get("manifest_paths", [])),
        warnings=tuple(str(value) for value in record.get("warnings", [])),
        errors=tuple(str(value) for value in record.get("errors", [])),
        sync_id=str(record.get("sync_id", "")),
    )


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))


def _validate_as_of(values: set[str]) -> None:
    non_empty = {value for value in values if value}
    if not non_empty:
        raise BrokerSnapshotLoadError("Broker snapshot as_of is missing.")
    if len(non_empty) != 1:
        raise BrokerSnapshotLoadError("Broker snapshot as_of mismatch across snapshot kinds.")

