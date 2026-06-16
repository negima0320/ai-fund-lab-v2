from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.broker.moomoo.normalizer import normalize_moomoo_mock_response
from ai_fund_lab_v2.broker.moomoo.readonly_client import (
    MoomooReadOnlyClient,
    MoomooReadOnlySettings,
    load_moomoo_readonly_settings,
)
from ai_fund_lab_v2.broker.runtime_paths import BrokerRuntimePaths
from ai_fund_lab_v2.broker.snapshot_writer import BrokerSnapshotWriter
from ai_fund_lab_v2.broker.sync_result import BrokerSyncResult
from ai_fund_lab_v2.runtime import RuntimePaths


@dataclass(frozen=True)
class MoomooReadOnlySmokeResult:
    status: str
    executed: bool
    report_path: Path
    snapshot_paths: tuple[str, ...] = ()
    manifest_paths: tuple[str, ...] = ()
    counts: dict[str, int] | None = None
    message: str = ""


def run_moomoo_readonly_smoke(
    *,
    runtime_dir: Path,
    reports_dir: Path,
    run_enabled: bool = False,
    env: dict[str, str] | None = None,
    settings: MoomooReadOnlySettings | None = None,
    continue_on_failure: bool = False,
) -> MoomooReadOnlySmokeResult:
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "phase8c_moomoo_readonly_smoke_result.json"
    if not run_enabled:
        payload = {
            "status": "SKIPPED",
            "executed": False,
            "created_at": utc_now_iso(),
            "message": "Explicit run flag was not provided; no external read-only smoke was executed.",
            "selected_trd_env": "NOT_SELECTED",
        }
        _write_json(report_path, payload)
        return MoomooReadOnlySmokeResult(status="SKIPPED", executed=False, report_path=report_path, message=payload["message"])

    resolved_settings = settings or load_moomoo_readonly_settings(runtime_dir, env=env)
    client = MoomooReadOnlyClient(resolved_settings, continue_on_failure=continue_on_failure)
    collect_result = client.collect_with_status()
    if not collect_result.ok:
        payload = {
            "status": "FAILED_READONLY_METHOD",
            "executed": True,
            "created_at": utc_now_iso(),
            "broker": "moomoo",
            "source": "readonly_smoke",
            "selected_trd_env": resolved_settings.environment,
            "method_results": collect_result.method_results,
            "method_errors": collect_result.method_errors,
            "account_summaries": collect_result.account_summaries,
            "account_discovery": collect_result.account_discovery,
            "attempted_args": collect_result.attempted_args,
            "continue_on_failure": continue_on_failure,
            "snapshot_paths": [],
            "manifest_paths": [],
            "config_source": resolved_settings.config_source,
            "raw_payload_saved": False,
            "secret_saved": False,
        }
        _write_json(report_path, payload)
        return MoomooReadOnlySmokeResult(
            status="FAILED_READONLY_METHOD",
            executed=True,
            report_path=report_path,
            counts={},
            message="One or more read-only methods failed; normalized snapshots were not written.",
        )
    raw_payload = collect_result.payload
    normalized = normalize_moomoo_mock_response(raw_payload)
    write_result = _write_normalized(runtime_dir, normalized)
    counts = {
        "accounts": write_result.broker_sync_result.account_snapshot_count,
        "balance": write_result.broker_sync_result.balance_snapshot_count,
        "positions": write_result.broker_sync_result.position_snapshot_count,
        "orders": write_result.broker_sync_result.order_snapshot_count,
        "executions": write_result.broker_sync_result.execution_snapshot_count,
    }
    payload = {
        "status": "PASS",
        "executed": True,
        "created_at": utc_now_iso(),
        "broker": "moomoo",
        "source": "readonly_smoke",
        "selected_trd_env": resolved_settings.environment,
        "counts": counts,
        "snapshot_paths": write_result.broker_sync_result.to_dict()["snapshot_paths"],
        "manifest_paths": write_result.broker_sync_result.to_dict()["manifest_paths"],
        "sync_result_path": str(write_result.sync_result.data_path),
        "config_source": resolved_settings.config_source,
        "raw_payload_saved": False,
        "secret_saved": False,
    }
    _write_json(report_path, payload)
    return MoomooReadOnlySmokeResult(
        status="PASS",
        executed=True,
        report_path=report_path,
        snapshot_paths=tuple(payload["snapshot_paths"]),
        manifest_paths=tuple(payload["manifest_paths"]),
        counts=counts,
    )


@dataclass(frozen=True)
class _WriteResult:
    sync_result: Any
    broker_sync_result: BrokerSyncResult


def _write_normalized(runtime_dir: Path, normalized: dict[str, object]) -> _WriteResult:
    paths = BrokerRuntimePaths(RuntimePaths(runtime_dir=runtime_dir))
    writer = BrokerSnapshotWriter(paths)
    accounts_result = writer.write_accounts(list(normalized["accounts"]))  # type: ignore[arg-type]
    balance_result = writer.write_balance(normalized["balance"])  # type: ignore[arg-type]
    positions_result = writer.write_positions(list(normalized["positions"]))  # type: ignore[arg-type]
    orders_result = writer.write_orders(list(normalized["orders"]))  # type: ignore[arg-type]
    executions_result = writer.write_executions(list(normalized["executions"]))  # type: ignore[arg-type]
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
        source="readonly_smoke",
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
    return _WriteResult(sync_result=writer.write_sync_result(broker_sync_result), broker_sync_result=broker_sync_result)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
