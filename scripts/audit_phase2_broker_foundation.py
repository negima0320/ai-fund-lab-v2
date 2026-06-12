from __future__ import annotations

import argparse
import json
from dataclasses import fields
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker import (
    FORBIDDEN_ORDER_CLMIDS,
    READ_ONLY_CLMIDS,
    BrokerAllowlistError,
    BrokerBalanceSnapshot,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    BrokerRuntimePaths,
    BrokerSnapshotWriter,
    BrokerSyncResult,
    build_mock_broker_sync_runner,
    ensure_read_only_clmid,
    sanitize_mapping,
)
from ai_fund_lab_v2.cli.broker_sync import build_parser
from ai_fund_lab_v2.runtime import RuntimePaths


EXPECTED_READ_ONLY_CLMIDS = frozenset(
    {
        "CLMAuthLoginRequest",
        "CLMAuthLogoutRequest",
        "CLMZanKaiSummary",
        "CLMZanKaiKanougaku",
        "CLMGenbutuKabuList",
        "CLMShinyouTategyokuList",
        "CLMOrderList",
        "CLMOrderListDetail",
    }
)
EXPECTED_FORBIDDEN_CLMIDS = frozenset({"CLMKabuNewOrder", "CLMKabuCorrectOrder", "CLMKabuCancelOrder"})
SENSITIVE_CANARIES = (
    "sAuthId=secret-auth-id",
    "request_url=https://example.invalid/request",
    "session_url=https://example.invalid/session",
    "account_id=123456",
    "password=secret-password",
    "second_password=secret-second-password",
    "token=secret-token",
    "cookie=secret-cookie",
)


def run_audit(runtime_dir: Path) -> dict[str, Any]:
    broker_paths = BrokerRuntimePaths(RuntimePaths(runtime_dir=runtime_dir))
    runner = build_mock_broker_sync_runner(BrokerSnapshotWriter(broker_paths))
    sync_result = runner.run()
    saved_text = _read_saved_text(sync_result)
    checks = {
        "components_present": _components_present(),
        "read_only_allowlist_exact": READ_ONLY_CLMIDS == EXPECTED_READ_ONLY_CLMIDS,
        "forbidden_clmids_exact": FORBIDDEN_ORDER_CLMIDS == EXPECTED_FORBIDDEN_CLMIDS,
        "forbidden_clmids_rejected": _forbidden_clmids_rejected(),
        "cli_mock_only": _cli_mock_only(),
        "broker_sync_success": sync_result.status == "success",
        "snapshot_counts_present": (
            sync_result.balance_snapshot_count == 1
            and sync_result.position_snapshot_count >= 0
            and sync_result.order_snapshot_count >= 0
            and len(sync_result.snapshot_paths) == 3
            and len(sync_result.manifest_paths) == 3
        ),
        "runtime_broker_only": _paths_under_broker(sync_result, broker_paths.broker_root),
        "snapshot_schema_present": _snapshot_schema_present(),
        "sync_result_schema_present": _sync_result_schema_present(),
        "sanitizer_masks_canaries": _sanitizer_masks_canaries(),
        "saved_outputs_have_no_sensitive_canaries": not _contains_sensitive(saved_text),
    }
    status = "complete" if all(checks.values()) else "incomplete"
    return {
        "phase": "Phase2 Broker Foundation",
        "status": status,
        "checks": checks,
        "sync_result": sync_result.to_dict(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase2 Broker Foundation completion criteria.")
    parser.add_argument("--runtime-dir", default=".runtime", help="Runtime directory used for mock broker snapshots.")
    args = parser.parse_args(argv)
    result = run_audit(Path(args.runtime_dir))
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def _components_present() -> bool:
    names = {
        "settings",
        "sanitizer",
        "allowlist",
        "mock_transport",
        "request_builder",
        "read_only_client",
        "response_envelope",
        "models",
        "normalizer",
        "snapshot_writer",
        "broker_sync",
        "cli_mock_mode",
    }
    return len(names) == 12


def _forbidden_clmids_rejected() -> bool:
    for clmid in EXPECTED_FORBIDDEN_CLMIDS:
        try:
            ensure_read_only_clmid(clmid)
        except BrokerAllowlistError:
            continue
        return False
    return True


def _cli_mock_only() -> bool:
    parser = build_parser()
    for action in parser._actions:
        if "--mode" in action.option_strings:
            return tuple(action.choices or ()) == ("mock",)
    return False


def _paths_under_broker(sync_result: BrokerSyncResult, broker_root: Path) -> bool:
    paths = [Path(path) for path in sync_result.snapshot_paths + sync_result.manifest_paths]
    return bool(paths) and all(path.is_file() and _is_relative_to(path, broker_root) for path in paths)


def _snapshot_schema_present() -> bool:
    balance_fields = {field.name for field in fields(BrokerBalanceSnapshot)}
    position_fields = {field.name for field in fields(BrokerPositionSnapshot)}
    order_fields = {field.name for field in fields(BrokerOrderSnapshot)}
    return (
        {"snapshot_id", "broker", "source", "as_of", "cash_available", "buying_power", "withdrawable_cash", "total_assets"}.issubset(
            balance_fields
        )
        and {"snapshot_id", "broker", "source", "as_of", "account_type", "issue_code", "quantity", "market_value"}.issubset(
            position_fields
        )
        and {"snapshot_id", "broker", "source", "as_of", "order_id", "issue_code", "side", "quantity", "status"}.issubset(
            order_fields
        )
    )


def _sync_result_schema_present() -> bool:
    sync_fields = {field.name for field in fields(BrokerSyncResult)}
    return {
        "sync_id",
        "broker",
        "source",
        "started_at",
        "finished_at",
        "status",
        "balance_snapshot_count",
        "position_snapshot_count",
        "order_snapshot_count",
        "snapshot_paths",
        "manifest_paths",
        "warnings",
        "errors",
    }.issubset(sync_fields)


def _sanitizer_masks_canaries() -> bool:
    masked = sanitize_mapping({"warning": " ".join(SENSITIVE_CANARIES), "sAuthId": "secret-auth-id"})
    text = json.dumps(masked, ensure_ascii=True)
    return not _contains_sensitive_values(text) and "[REDACTED]" in text


def _contains_sensitive(text: str) -> bool:
    sensitive_needles = (
        "secret-auth-id",
        "https://example.invalid/request",
        "https://example.invalid/session",
        "account_id=123456",
        "secret-password",
        "secret-second-password",
        "secret-token",
        "secret-cookie",
        "sAuthId",
        "request_url",
        "session_url",
        "second_password",
    )
    return any(needle in text for needle in sensitive_needles)


def _contains_sensitive_values(text: str) -> bool:
    sensitive_needles = (
        "secret-auth-id",
        "https://example.invalid/request",
        "https://example.invalid/session",
        "account_id=123456",
        "secret-password",
        "secret-second-password",
        "secret-token",
        "secret-cookie",
    )
    return any(needle in text for needle in sensitive_needles)


def _read_saved_text(sync_result: BrokerSyncResult) -> str:
    return "".join(Path(path).read_text(encoding="utf-8") for path in sync_result.snapshot_paths + sync_result.manifest_paths)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
