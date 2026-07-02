from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.tachibana_broker_snapshot import run_tachibana_broker_snapshot
from ai_fund_lab_v2.operations.io import OperationPaths, read_json, stable_hash, utc_now_iso, write_json


def refresh_demo_broker_readonly_artifacts(
    *,
    trade_date: str,
    root: Path,
    run_enabled: bool = False,
    include_quotes: bool = False,
) -> dict[str, Any]:
    paths = OperationPaths(root)
    snapshot_path = paths.dated("broker_readonly_source", trade_date, "tachibana_demo_snapshot.json")
    report = run_tachibana_broker_snapshot(
        reports_dir=paths.dated("broker_readonly_reports", trade_date, "placeholder.json").parent,
        run_enabled=run_enabled,
        report_filename="broker_readonly_snapshot_report.json",
        snapshot_path=snapshot_path,
        source="operations_broker_readonly_mainline",
        include_quotes=include_quotes,
    )
    if not report.executed or not snapshot_path.exists():
        return {
            "status": "SKIPPED" if not run_enabled else "BLOCK",
            "api_called": bool(report.executed),
            "report_path": str(report.report_path),
            "snapshot_path": str(snapshot_path),
            "artifacts_written": False,
            "blocked_reasons": [report.message] if report.message else ["broker_snapshot_not_written"],
        }
    return write_broker_readonly_artifacts_from_snapshot(trade_date=trade_date, root=root, snapshot=read_json(snapshot_path), report_path=report.report_path)


def write_broker_readonly_artifacts_from_snapshot(
    *,
    trade_date: str,
    root: Path,
    snapshot: dict[str, Any],
    report_path: Path | str = "",
) -> dict[str, Any]:
    paths = OperationPaths(root)
    env = str(snapshot.get("environment") or "UNKNOWN")
    raw_positions = snapshot.get("positions") or []
    positions = [
        item
        for item in (_normalize_position(row, index=index) for index, row in enumerate(raw_positions, start=1))
        if item["issue_code"] and _decimal(item["quantity"]) > 0
    ]
    orders = [_normalize_order(row) for row in snapshot.get("orders") or []]
    executions = [_normalize_execution(row) for row in snapshot.get("executions") or []]
    buying_power = _normalize_buying_power(snapshot.get("buying_power") or snapshot.get("account_summary") or {})
    account_summary = _normalize_account_summary(snapshot.get("account_summary") or {})
    quotes = [_normalize_quote(row) for row in snapshot.get("quotes") or []]

    counts = {
        "positions": len(positions),
        "orders": len(orders),
        "executions": len(executions),
        "quotes": len(quotes),
    }
    health = snapshot.get("health") or {}
    summary = {
        "artifact_type": "broker_snapshot_summary",
        "business_date": trade_date,
        "environment": env,
        "snapshot_freshness": "FRESH",
        "snapshot_generated_at": snapshot.get("generated_at", ""),
        "broker_actual_equity": account_summary.get("total_assets") or buying_power.get("buying_power") or "0",
        "buying_power": buying_power.get("buying_power") or "0",
        "current_exposure": str(sum(_decimal(row.get("market_value")) for row in positions)),
        "positions_count": len(positions),
        "orders_count": len(orders),
        "executions_count": len(executions),
        "orders_status": (health.get("orders") or {}).get("status", "UNKNOWN"),
        "executions_status": (health.get("executions") or {}).get("status", "UNKNOWN"),
        "buying_power_available": bool(buying_power.get("buying_power")),
        "raw_response_saved": False,
        "secret_saved": False,
        "source": "operations_broker_readonly_artifact_writer",
    }
    snapshot_out = {
        "artifact_type": "broker_snapshot",
        "business_date": trade_date,
        "environment": env,
        "generated_at": snapshot.get("generated_at", utc_now_iso()),
        "schema_version": snapshot.get("schema_version", "tachibana_broker_snapshot_v1"),
        "session_status": snapshot.get("session_status", "UNKNOWN"),
        "counts": counts,
        "health": health,
        "summary": summary,
        "source_counts": {
            "positions": len(raw_positions),
            "orders": len(snapshot.get("orders") or []),
            "executions": len(snapshot.get("executions") or []),
            "quotes": len(snapshot.get("quotes") or []),
        },
        "redaction_status": {
            **(snapshot.get("redaction_status") or {}),
            "raw_response_saved": False,
            "private_secret_saved": False,
            "auth_identifier_saved": False,
            "virtual_url_saved": False,
        },
        "raw_response_saved": False,
        "secret_saved": False,
        "report_path": str(report_path),
    }
    artifacts = {
        "broker_snapshot": snapshot_out,
        "broker_positions": {"artifact_type": "broker_positions", "business_date": trade_date, "positions": positions, "raw_response_saved": False, "secret_saved": False},
        "positions": {
            "artifact_type": "positions",
            "business_date": trade_date,
            "exit_source": "broker_readonly",
            "positions": positions,
            "raw_response_saved": False,
            "secret_saved": False,
        },
        "broker_orders": {"artifact_type": "broker_orders", "business_date": trade_date, "orders": orders, "raw_response_saved": False, "secret_saved": False},
        "broker_executions": {
            "artifact_type": "broker_executions",
            "business_date": trade_date,
            "executions": executions,
            "classification": "SKIPPED_NO_ORDERS" if not orders and not executions else "AVAILABLE",
            "raw_response_saved": False,
            "secret_saved": False,
        },
        "broker_buying_power": {
            "artifact_type": "broker_buying_power",
            "business_date": trade_date,
            **buying_power,
            "raw_response_saved": False,
            "secret_saved": False,
        },
        "broker_account_summary": {
            "artifact_type": "broker_account_summary",
            "business_date": trade_date,
            **account_summary,
            "raw_response_saved": False,
            "secret_saved": False,
        },
        "broker_quotes": {"artifact_type": "broker_quotes", "business_date": trade_date, "quotes": quotes, "raw_response_saved": False, "secret_saved": False},
        "broker_snapshot_summary": summary,
    }
    output_paths = {
        "broker_snapshot": paths.dated("broker_snapshot", trade_date, "broker_snapshot.json"),
        "broker_positions": paths.dated("broker_positions", trade_date, "positions.json"),
        "positions": paths.dated("positions", trade_date, "positions.json"),
        "broker_orders": paths.dated("broker_orders", trade_date, "orders.json"),
        "broker_executions": paths.dated("broker_executions", trade_date, "executions.json"),
        "broker_buying_power": paths.dated("broker_buying_power", trade_date, "buying_power.json"),
        "broker_account_summary": paths.dated("broker_account_summary", trade_date, "account_summary.json"),
        "broker_quotes": paths.dated("broker_quotes", trade_date, "quotes.json"),
        "broker_snapshot_summary": paths.dated("broker_snapshot_summary", trade_date, "broker_snapshot_summary.json"),
    }
    for key, path in output_paths.items():
        write_json(path, artifacts[key])
    return {
        "status": "PASS",
        "api_called": bool(report_path),
        "artifacts_written": True,
        "counts": counts,
        "buying_power_available": bool(buying_power.get("buying_power")),
        "executions_classification": artifacts["broker_executions"]["classification"],
        "paths": {key: str(path) for key, path in output_paths.items()},
        "raw_response_saved": False,
        "secret_saved": False,
        "blocked_reasons": [],
    }


def load_broker_artifact_bundle(*, trade_date: str, root: Path) -> dict[str, Any]:
    paths = OperationPaths(root)
    refs = {
        "broker_snapshot": paths.dated("broker_snapshot", trade_date, "broker_snapshot.json"),
        "broker_positions": paths.dated("broker_positions", trade_date, "positions.json"),
        "broker_orders": paths.dated("broker_orders", trade_date, "orders.json"),
        "broker_executions": paths.dated("broker_executions", trade_date, "executions.json"),
        "broker_buying_power": paths.dated("broker_buying_power", trade_date, "buying_power.json"),
        "broker_account_summary": paths.dated("broker_account_summary", trade_date, "account_summary.json"),
        "broker_quotes": paths.dated("broker_quotes", trade_date, "quotes.json"),
        "broker_snapshot_summary": paths.dated("broker_snapshot_summary", trade_date, "broker_snapshot_summary.json"),
    }
    artifacts = {key: read_json(path) for key, path in refs.items() if path.exists()}
    missing = [key for key, path in refs.items() if not path.exists() and key != "broker_quotes"]
    return {
        "status": "PASS" if not missing else "REVIEW_REQUIRED",
        "missing": missing,
        "paths": {key: str(path) for key, path in refs.items()},
        "artifacts": artifacts,
        "positions_count": len((artifacts.get("broker_positions") or {}).get("positions") or []),
        "orders_count": len((artifacts.get("broker_orders") or {}).get("orders") or []),
        "executions_count": len((artifacts.get("broker_executions") or {}).get("executions") or []),
        "buying_power_available": bool((artifacts.get("broker_buying_power") or {}).get("buying_power")),
        "raw_response_saved": any((item or {}).get("raw_response_saved") is True for item in artifacts.values()),
        "secret_saved": any((item or {}).get("secret_saved") is True for item in artifacts.values()),
    }


def _normalize_position(row: dict[str, Any], *, index: int) -> dict[str, Any]:
    code = str(row.get("issue_code") or row.get("code") or "")
    quantity = str(row.get("quantity") or "0")
    market_price = str(row.get("market_price") or row.get("current_price") or "0")
    average_price = str(row.get("average_price") or row.get("entry_price") or "0")
    return {
        "position_id": _hashed_id("position", code, quantity, average_price, index),
        "lot_reference": _hashed_id("lot", code, quantity, average_price, index),
        "issue_code": code,
        "code": code,
        "issue_name": str(row.get("issue_name") or ""),
        "account_type": str(row.get("account_type") or "cash"),
        "quantity": quantity,
        "available_quantity": str(row.get("available_quantity") or quantity),
        "average_cost": average_price,
        "entry_price": average_price,
        "position_entry_price": average_price,
        "current_price": market_price,
        "market_price": market_price,
        "market_value": str(row.get("market_value") or (_decimal(quantity) * _decimal(market_price)).quantize(Decimal("1"))),
        "unrealized_pnl": str(row.get("unrealized_pnl") or "0"),
        "unrealized_return": _unrealized_return(average_price, market_price),
        "lot_size": "100",
        "source": "broker_readonly",
        "raw_response_saved": False,
        "secret_saved": False,
    }


def _normalize_order(row: dict[str, Any]) -> dict[str, Any]:
    order_id = str(row.get("order_id") or "")
    return {
        "broker_order_id_hash": stable_hash({"order_id": order_id}) if order_id else "",
        "issue_code": str(row.get("issue_code") or ""),
        "side": str(row.get("side") or "").upper(),
        "quantity": str(row.get("quantity") or "0"),
        "executed_quantity": str(row.get("executed_quantity") or "0"),
        "remaining_quantity": str(row.get("remaining_quantity") or "0"),
        "price": str(row.get("price") or "0"),
        "status": str(row.get("status") or ""),
        "order_datetime": str(row.get("order_datetime") or ""),
        "raw_response_saved": False,
        "secret_saved": False,
    }


def _normalize_execution(row: dict[str, Any]) -> dict[str, Any]:
    execution_id = str(row.get("execution_id") or "")
    order_id = str(row.get("order_id") or "")
    return {
        "broker_execution_id_hash": stable_hash({"execution_id": execution_id}) if execution_id else "",
        "broker_order_id_hash": stable_hash({"order_id": order_id}) if order_id else "",
        "issue_code": str(row.get("issue_code") or ""),
        "side": str(row.get("side") or "").upper(),
        "quantity": str(row.get("quantity") or "0"),
        "price": str(row.get("price") or "0"),
        "executed_at": str(row.get("executed_at") or ""),
        "raw_response_saved": False,
        "secret_saved": False,
    }


def _normalize_buying_power(row: dict[str, Any]) -> dict[str, str]:
    return {
        "currency": str(row.get("currency") or "JPY"),
        "cash_available": str(row.get("cash_available") or "0"),
        "buying_power": str(row.get("buying_power") or row.get("total_assets") or "0"),
        "withdrawable_cash": str(row.get("withdrawable_cash") or "0"),
    }


def _normalize_account_summary(row: dict[str, Any]) -> dict[str, str]:
    return {
        "currency": str(row.get("currency") or "JPY"),
        "cash_available": str(row.get("cash_available") or "0"),
        "buying_power": str(row.get("buying_power") or "0"),
        "total_assets": str(row.get("total_assets") or row.get("buying_power") or "0"),
    }


def _normalize_quote(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "issue_code": str(row.get("issue_code") or ""),
        "last_price": str(row.get("last_price") or ""),
        "quote_time": str(row.get("quote_time") or ""),
        "raw_response_saved": False,
    }


def _hashed_id(prefix: str, *parts: Any) -> str:
    return f"{prefix}_{stable_hash({'parts': [str(part) for part in parts]})[-16:]}"


def _unrealized_return(entry_price: Any, current_price: Any) -> str:
    entry = _decimal(entry_price)
    current = _decimal(current_price)
    if entry <= 0 or current <= 0:
        return "0"
    return str((current / entry) - Decimal("1"))


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))
