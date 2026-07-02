from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.operations.broker_readonly import load_broker_artifact_bundle
from ai_fund_lab_v2.operations.io import OperationPaths, stable_hash, utc_now_iso, write_json


def write_operations_ledger_from_broker_readonly(*, trade_date: str, root: Path) -> dict[str, Any]:
    paths = OperationPaths(root)
    bundle = load_broker_artifact_bundle(trade_date=trade_date, root=paths.root)
    artifacts = bundle.get("artifacts", {})
    positions = (artifacts.get("broker_positions") or {}).get("positions") or []
    orders = (artifacts.get("broker_orders") or {}).get("orders") or []
    executions = (artifacts.get("broker_executions") or {}).get("executions") or []
    buying_power = artifacts.get("broker_buying_power") or {}
    account = artifacts.get("broker_account_summary") or {}
    market_value = sum(_decimal(row.get("market_value")) for row in positions)
    total_equity = _decimal(account.get("total_assets")) or _decimal(buying_power.get("buying_power")) + market_value
    ledger_state = {
        "artifact_type": "operations_ledger_state",
        "business_date": trade_date,
        "source": "broker_readonly_snapshot",
        "broker_source_of_truth": True,
        "positions_summary": {
            "count": len(positions),
            "market_value_estimate": str(market_value),
            "empty_classification": "NO_POSITIONS" if not positions else "POSITIONS_AVAILABLE",
            "position_refs": [
                {
                    "position_id": row.get("position_id", ""),
                    "issue_code": row.get("issue_code", ""),
                    "quantity": row.get("quantity", "0"),
                    "market_value": row.get("market_value", "0"),
                }
                for row in positions
            ],
        },
        "cash_or_buying_power_summary": {
            "buying_power": str(buying_power.get("buying_power") or "0"),
            "cash_available": str(buying_power.get("cash_available") or account.get("cash_available") or "0"),
            "currency": str(buying_power.get("currency") or account.get("currency") or "JPY"),
        },
        "executions_summary": {
            "count": len(executions),
            "empty_classification": "SKIPPED_NO_ORDERS" if not orders and not executions else ("NO_EXECUTIONS" if not executions else "EXECUTIONS_AVAILABLE"),
        },
        "orders_summary": {
            "count": len(orders),
            "empty_classification": "NO_ORDERS" if not orders else "ORDERS_AVAILABLE",
        },
        "market_value_estimate": str(market_value),
        "total_equity_estimate": str(total_equity),
        "redaction_status": {
            "raw_response_saved": False,
            "secret_saved": False,
            "account_id_plaintext_saved": False,
            "order_id_plaintext_saved": False,
            "execution_id_plaintext_saved": False,
        },
        "raw_response_saved": False,
        "secret_saved": False,
        "ai_training_input_allowed": False,
        "paper_ledger_used_for_ai_training": False,
        "operations_ledger_used_for_ai_training": False,
    }
    manifest = {
        "artifact_type": "operations_ledger_update_manifest",
        "business_date": trade_date,
        "status": "PASS" if bundle.get("status") == "PASS" else "REVIEW_REQUIRED",
        "created_at": utc_now_iso(),
        "source": "broker_readonly_snapshot",
        "broker_bundle_status": bundle.get("status"),
        "missing_broker_artifacts": bundle.get("missing", []),
        "ledger_state_hash": stable_hash(ledger_state),
        "ledger_state_path": str(paths.dated("ledger", trade_date, "ledger_state.json")),
        "raw_response_saved": False,
        "secret_saved": False,
    }
    state_path = paths.dated("ledger", trade_date, "ledger_state.json")
    manifest_path = paths.dated("ledger", trade_date, "ledger_update_manifest.json")
    summary_path = paths.dated("ledger", trade_date, "ledger_summary.json")
    write_json(state_path, ledger_state)
    write_json(manifest_path, manifest)
    write_json(
        summary_path,
        {
            "artifact_type": "operations_ledger_summary",
            "business_date": trade_date,
            "status": manifest["status"],
            "positions_count": len(positions),
            "orders_count": len(orders),
            "executions_count": len(executions),
            "buying_power_available": bool(buying_power.get("buying_power")),
            "market_value_estimate": str(market_value),
            "total_equity_estimate": str(total_equity),
            "raw_response_saved": False,
            "secret_saved": False,
        },
    )
    return {
        "status": manifest["status"],
        "ledger_state_path": str(state_path),
        "ledger_update_manifest_path": str(manifest_path),
        "ledger_summary_path": str(summary_path),
        "positions_count": len(positions),
        "orders_count": len(orders),
        "executions_count": len(executions),
        "buying_power_available": bool(buying_power.get("buying_power")),
        "empty_broker_state_handled": not positions and not orders and not executions,
        "raw_response_saved": False,
        "secret_saved": False,
    }


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))
