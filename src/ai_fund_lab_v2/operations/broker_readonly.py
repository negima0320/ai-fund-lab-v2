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
    source_classification = _broker_snapshot_source_classification(snapshot)
    mock_source_detected = source_classification == "MOCK"
    raw_positions = snapshot.get("positions") or []
    positions = [
        item
        for item in (_normalize_position(row, index=index) for index, row in enumerate(raw_positions, start=1))
        if item["issue_code"] and _decimal(item["quantity"]) > 0
    ]
    orders = [_normalize_order(row) for row in snapshot.get("orders") or []]
    executions = [_normalize_execution(row) for row in snapshot.get("executions") or []]
    positions_safe_diagnosis = _positions_safe_diagnosis(raw_positions, positions)
    fallback_executions = []
    executions_health_status = ((snapshot.get("health") or {}).get("executions") or {}).get("status", "UNKNOWN")
    if not executions and orders:
        fallback_executions = [_fallback_execution_from_order(order, index=index, executions_health_status=executions_health_status) for index, order in enumerate(orders, start=1) if _order_status_indicates_filled(order)]
        executions = fallback_executions
    executions_classification = (
        "SKIPPED_NO_ORDERS"
        if not orders and not executions
        else "ORDER_STATUS_FILLED_FALLBACK_REVIEW"
        if fallback_executions
        else "AVAILABLE"
    )
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
        "executions_classification": executions_classification,
        "positions_safe_diagnosis": positions_safe_diagnosis,
        "buying_power_available": bool(buying_power.get("buying_power")),
        "raw_response_saved": False,
        "secret_saved": False,
        "source": "operations_broker_readonly_artifact_writer",
        "upstream_source": snapshot.get("source", ""),
        "source_classification": source_classification,
        "mock_source_detected": mock_source_detected,
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
        "positions_safe_diagnosis": positions_safe_diagnosis,
        "executions_classification": executions_classification,
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
        "upstream_source": snapshot.get("source", ""),
        "source_classification": source_classification,
        "mock_source_detected": mock_source_detected,
    }
    artifacts = {
        "broker_snapshot": snapshot_out,
        "broker_positions": {
            "artifact_type": "broker_positions",
            "business_date": trade_date,
            "positions": positions,
            "positions_safe_diagnosis": positions_safe_diagnosis,
            "raw_response_saved": False,
            "secret_saved": False,
        },
        "positions": {
            "artifact_type": "positions",
            "business_date": trade_date,
            "exit_source": "broker_readonly",
            "positions": positions,
            "positions_safe_diagnosis": positions_safe_diagnosis,
            "raw_response_saved": False,
            "secret_saved": False,
        },
        "broker_orders": {"artifact_type": "broker_orders", "business_date": trade_date, "orders": orders, "raw_response_saved": False, "secret_saved": False},
        "broker_executions": {
            "artifact_type": "broker_executions",
            "business_date": trade_date,
            "executions": executions,
            "classification": executions_classification,
            "review_required": bool(fallback_executions),
            "fallback_execution_count": len(fallback_executions),
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
    status = "REVIEW_REQUIRED" if mock_source_detected else "PASS"
    blocked_reasons = ["broker_readonly_snapshot_source_mock"] if mock_source_detected else []
    return {
        "status": status,
        "api_called": bool(report_path),
        "artifacts_written": True,
        "counts": counts,
        "source_classification": source_classification,
        "mock_source_detected": mock_source_detected,
        "buying_power_available": bool(buying_power.get("buying_power")),
        "executions_classification": artifacts["broker_executions"]["classification"],
        "positions_safe_diagnosis": positions_safe_diagnosis,
        "paths": {key: str(path) for key, path in output_paths.items()},
        "raw_response_saved": False,
        "secret_saved": False,
        "blocked_reasons": blocked_reasons,
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
    mock_source_detected = any(_artifact_contains_mock_source(item) for item in artifacts.values())
    broker_executions = artifacts.get("broker_executions") or {}
    fallback_execution_count = int(broker_executions.get("fallback_execution_count") or 0)
    executions_classification = str(broker_executions.get("classification") or "")
    status = "PASS" if not missing and not mock_source_detected else "REVIEW_REQUIRED"
    review_reasons = []
    if missing:
        review_reasons.append("broker_readonly_artifact_missing_or_incomplete")
    if mock_source_detected:
        review_reasons.append("broker_readonly_snapshot_source_mock")
    return {
        "status": status,
        "missing": missing,
        "review_reasons": review_reasons,
        "source_classification": "MOCK" if mock_source_detected else ("MISSING" if missing else "BROKER_API_OR_SANITIZED_BROKER"),
        "mock_source_detected": mock_source_detected,
        "paths": {key: str(path) for key, path in refs.items()},
        "artifacts": artifacts,
        "positions_count": len((artifacts.get("broker_positions") or {}).get("positions") or []),
        "orders_count": len((artifacts.get("broker_orders") or {}).get("orders") or []),
        "executions_count": len((artifacts.get("broker_executions") or {}).get("executions") or []),
        "broker_executions_classification": executions_classification,
        "fallback_execution_count": fallback_execution_count,
        "order_status_filled_fallback_review": executions_classification == "ORDER_STATUS_FILLED_FALLBACK_REVIEW" or fallback_execution_count > 0,
        "positions_safe_diagnosis": (artifacts.get("broker_positions") or {}).get("positions_safe_diagnosis") or (artifacts.get("broker_snapshot") or {}).get("positions_safe_diagnosis") or {},
        "buying_power_available": bool((artifacts.get("broker_buying_power") or {}).get("buying_power")),
        "raw_response_saved": any((item or {}).get("raw_response_saved") is True for item in artifacts.values()),
        "secret_saved": any((item or {}).get("secret_saved") is True for item in artifacts.values()),
    }


def _broker_snapshot_source_classification(snapshot: dict[str, Any]) -> str:
    if _artifact_contains_mock_source(snapshot):
        return "MOCK"
    if snapshot.get("session_status") or snapshot.get("generated_at"):
        return "BROKER_API_OR_SANITIZED_BROKER"
    return "UNKNOWN"


def _artifact_contains_mock_source(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() == "source" and str(item).strip().lower() == "mock":
                return True
            if _artifact_contains_mock_source(item):
                return True
    if isinstance(value, list):
        return any(_artifact_contains_mock_source(item) for item in value)
    return False


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
    issue_code = str(row.get("issue_code") or row.get("code") or "")
    return {
        "broker_order_id_hash": stable_hash({"order_id": order_id}) if order_id else "",
        "issue_code": issue_code,
        "code": issue_code,
        "broker_issue_code": issue_code,
        "side": _normalize_tachibana_side(row.get("side")),
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
        "issue_code": str(row.get("issue_code") or row.get("code") or ""),
        "code": str(row.get("issue_code") or row.get("code") or ""),
        "side": _normalize_tachibana_side(row.get("side")),
        "quantity": str(row.get("quantity") or "0"),
        "price": str(row.get("price") or "0"),
        "executed_at": str(row.get("executed_at") or ""),
        "raw_response_saved": False,
        "secret_saved": False,
    }


def _fallback_execution_from_order(order: dict[str, Any], *, index: int, executions_health_status: str) -> dict[str, Any]:
    issue_code = str(order.get("issue_code") or order.get("code") or "")
    return {
        "broker_execution_id_hash": stable_hash({"fallback": "broker_orders", "issue_code": issue_code, "index": index}),
        "broker_order_id_hash": str(order.get("broker_order_id_hash") or ""),
        "issue_code": issue_code,
        "code": issue_code,
        "side": _normalize_tachibana_side(order.get("side")),
        "quantity": str(order.get("executed_quantity") or order.get("quantity") or "0"),
        "price": str(order.get("price") or "0"),
        "executed_at": str(order.get("order_datetime") or ""),
        "source": "broker_orders_fallback",
        "classification": "ORDER_STATUS_FILLED_FALLBACK_REVIEW",
        "review_required": True,
        "broker_executions_api_failed": executions_health_status == "FAIL",
        "order_status": str(order.get("status") or ""),
        "executed_quantity": str(order.get("executed_quantity") or "0"),
        "remaining_quantity": str(order.get("remaining_quantity") or "0"),
        "raw_response_saved": False,
        "secret_saved": False,
        "raw_broker_order_id_saved": False,
    }


def _order_status_indicates_filled(order: dict[str, Any]) -> bool:
    executed = _decimal(order.get("executed_quantity"))
    remaining = _decimal(order.get("remaining_quantity"))
    status = str(order.get("status") or "").upper()
    return executed > 0 and remaining == 0 and status in {"全部約定", "FILLED", "DONE", "約定済"}


def _normalize_tachibana_side(value: Any) -> str:
    text = str(value or "").upper()
    return {"3": "BUY", "1": "SELL", "BUY": "BUY", "SELL": "SELL", "買": "BUY", "売": "SELL"}.get(text, text)


def _positions_safe_diagnosis(raw_positions: list[dict[str, Any]], positions: list[dict[str, Any]]) -> dict[str, Any]:
    issue_keys = ("issue_code", "code", "sIssueCode", "sMeigaraCode")
    quantity_keys = ("quantity", "available_quantity", "sQuantity", "sZanKabuSuu", "sSuryou", "sTategyokuSuryou")
    return {
        "positions_source_count": len(raw_positions),
        "positions_valid_count": len(positions),
        "candidate_key_presence": {
            "issue_code_keys_present": _present_keys(raw_positions, issue_keys),
            "quantity_keys_present": _present_keys(raw_positions, quantity_keys),
        },
        "all_rows_empty_or_zero": bool(raw_positions) and all(
            not str(row.get("issue_code") or row.get("code") or "").strip() and _decimal(row.get("quantity")) <= 0
            for row in raw_positions
        ),
        "raw_response_saved": False,
        "secret_saved": False,
        "account_identifier_saved": False,
    }


def _present_keys(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[str]:
    present = []
    for key in keys:
        if any(key in row for row in rows):
            present.append(key)
    return present


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
