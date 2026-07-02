from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.operations.io import stable_hash, utc_now_iso, write_json


DEMO_LEDGER_DIR = "demo_ledger"


def record_demo_submit_result(
    *,
    root: Path,
    trade_date: str,
    submit_payload: dict[str, Any],
    retry_parent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ledger_root = Path(root) / DEMO_LEDGER_DIR
    ledger_root.mkdir(parents=True, exist_ok=True)
    order_records = []
    event_records = []
    for row in submit_payload.get("submitted_orders", []):
        response = ((row.get("wire_execution_result") or {}).get("response") or {})
        record = {
            "record_type": "demo_order_history",
            "recorded_at": utc_now_iso(),
            "business_date": trade_date,
            "item_id": row.get("item_id", ""),
            "run_id": row.get("run_id", ""),
            "approval_id": row.get("approval_id", ""),
            "side": row.get("side", ""),
            "code": row.get("code") or row.get("issue_code", ""),
            "quantity": row.get("quantity", ""),
            "order_type": (row.get("normalized_order") or {}).get("order_type", "CASH_EQUITY"),
            "price_type": (row.get("normalized_order") or {}).get("price_type", ""),
            "limit_price": row.get("limit_price", ""),
            "expected_notional": row.get("expected_notional", ""),
            "status": row.get("status", ""),
            "accepted": response.get("accepted") is True,
            "rejected": response.get("rejected") is True,
            "broker_order_ref_hash": row.get("broker_order_id_hash", ""),
            "retry_parent": retry_parent or {},
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
            "plain_broker_ids_saved": False,
        }
        order_records.append(record)
        event_records.append(
            {
                "record_type": "demo_lifecycle_event",
                "recorded_at": record["recorded_at"],
                "business_date": trade_date,
                "event": "demo_order_submit_result",
                "item_id": record["item_id"],
                "run_id": record["run_id"],
                "side": record["side"],
                "status": record["status"],
                "accepted": record["accepted"],
                "rejected": record["rejected"],
                "retry_parent_hash": stable_hash(retry_parent) if retry_parent else "",
                "raw_request_saved": False,
                "raw_response_saved": False,
                "secret_saved": False,
            }
        )
    for record in order_records:
        _append_jsonl(ledger_root / "orders.jsonl", record)
    for record in event_records:
        _append_jsonl(ledger_root / "events.jsonl", record)
    state = summarize_demo_ledger(root=root)
    write_json(ledger_root / "state.json", state)
    return state


def record_demo_readonly_monitoring(
    *,
    root: Path,
    trade_date: str,
    submitted_orders: list[dict[str, Any]],
    broker_orders: list[dict[str, Any]],
    broker_executions: list[dict[str, Any]],
    broker_positions: list[dict[str, Any]],
    buying_power: dict[str, Any],
    fill_events: list[dict[str, Any]],
) -> dict[str, Any]:
    ledger_root = Path(root) / DEMO_LEDGER_DIR
    ledger_root.mkdir(parents=True, exist_ok=True)
    recorded_at = utc_now_iso()
    order_status = {
        "record_type": "demo_order_status_history",
        "recorded_at": recorded_at,
        "business_date": trade_date,
        "submitted_order_count": len(submitted_orders),
        "broker_order_count": len(broker_orders),
        "broker_execution_count": len(broker_executions),
        "broker_position_count": len(broker_positions),
        "fill_events": [_safe_fill_event(row) for row in fill_events],
        "broker_orders": [_safe_broker_order(row) for row in broker_orders],
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
        "plain_broker_ids_saved": False,
    }
    _append_jsonl(ledger_root / "order_status.jsonl", order_status)
    for row in broker_executions:
        _append_jsonl(
            ledger_root / "executions.jsonl",
            {
                "record_type": "demo_execution_history",
                "recorded_at": recorded_at,
                "business_date": trade_date,
                **_safe_execution(row),
                "raw_request_saved": False,
                "raw_response_saved": False,
                "secret_saved": False,
                "plain_broker_ids_saved": False,
            },
        )
    for row in broker_positions:
        _append_jsonl(
            ledger_root / "positions.jsonl",
            {
                "record_type": "demo_position_history",
                "recorded_at": recorded_at,
                "business_date": trade_date,
                **_safe_position(row),
                "raw_request_saved": False,
                "raw_response_saved": False,
                "secret_saved": False,
                "plain_broker_ids_saved": False,
            },
        )
    _append_jsonl(
        ledger_root / "cash_history.jsonl",
        {
            "record_type": "demo_cash_history",
            "recorded_at": recorded_at,
            "business_date": trade_date,
            "buying_power": str(buying_power.get("buying_power") or ""),
            "cash_available": str(buying_power.get("cash_available") or ""),
            "currency": str(buying_power.get("currency") or ""),
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
        },
    )
    _append_jsonl(
        ledger_root / "events.jsonl",
        {
            "record_type": "demo_lifecycle_event",
            "recorded_at": recorded_at,
            "business_date": trade_date,
            "event": "demo_readonly_fill_monitoring",
            "buy_fill_status": _buy_fill_status(fill_events),
            "sell_order_attempted": False,
            "auto_resubmit": False,
            "auto_cancel": False,
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
        },
    )
    state = summarize_demo_ledger(root=root)
    write_json(ledger_root / "state.json", state)
    return state


def record_demo_special_fill_simulation(
    *,
    root: Path,
    trade_date: str,
    buy_fill: dict[str, Any],
    sell_fill: dict[str, Any],
) -> dict[str, Any]:
    ledger_root = Path(root) / DEMO_LEDGER_DIR
    ledger_root.mkdir(parents=True, exist_ok=True)
    recorded_at = utc_now_iso()
    for fill in (buy_fill, sell_fill):
        _append_jsonl(
            ledger_root / "executions.jsonl",
            {
                "record_type": "demo_special_simulated_execution",
                "recorded_at": recorded_at,
                "business_date": trade_date,
                "internal_code": str(fill.get("internal_code") or ""),
                "broker_issue_code": str(fill.get("broker_issue_code") or ""),
                "side": str(fill.get("side") or ""),
                "quantity": str(fill.get("quantity") or ""),
                "fill_price": str(fill.get("fill_price") or ""),
                "fill_notional": str(fill.get("fill_notional") or ""),
                "broker_confirmed_fill": False,
                "simulated_fill": True,
                "demo_special_rule": True,
                "simulation_reason": "demo_9000_series_non_fill_rule",
                "performance_metrics_excluded": True,
                "raw_request_saved": False,
                "raw_response_saved": False,
                "secret_saved": False,
                "plain_broker_ids_saved": False,
            },
        )
    _append_jsonl(
        ledger_root / "positions.jsonl",
        {
            "record_type": "demo_special_simulated_position",
            "recorded_at": recorded_at,
            "business_date": trade_date,
            "internal_code": str(buy_fill.get("internal_code") or ""),
            "broker_issue_code": str(buy_fill.get("broker_issue_code") or ""),
            "position_state": "OPENED_THEN_CLOSED_BY_SIMULATION",
            "opened_quantity": str(buy_fill.get("quantity") or ""),
            "closed_quantity": str(sell_fill.get("quantity") or ""),
            "net_quantity": "0",
            "broker_confirmed_fill": False,
            "simulated_fill": True,
            "demo_special_rule": True,
            "performance_metrics_excluded": True,
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
            "plain_broker_ids_saved": False,
        },
    )
    _append_jsonl(
        ledger_root / "events.jsonl",
        {
            "record_type": "demo_lifecycle_event",
            "recorded_at": recorded_at,
            "business_date": trade_date,
            "event": "demo_special_fill_simulation_9000_series",
            "buy_lifecycle": "SIMULATED_FILLED",
            "sell_lifecycle": "SIMULATED_FILLED",
            "broker_confirmed_fill": False,
            "simulated_fill": True,
            "demo_special_rule": True,
            "simulation_reason": "demo_9000_series_non_fill_rule",
            "performance_metrics_excluded": True,
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
        },
    )
    state = summarize_demo_ledger(root=root)
    write_json(ledger_root / "state.json", state)
    return state


def summarize_demo_ledger(*, root: Path) -> dict[str, Any]:
    ledger_root = Path(root) / DEMO_LEDGER_DIR
    orders = _read_jsonl(ledger_root / "orders.jsonl")
    order_statuses = _read_jsonl(ledger_root / "order_status.jsonl")
    executions = _read_jsonl(ledger_root / "executions.jsonl")
    positions = _read_jsonl(ledger_root / "positions.jsonl")
    cash = _read_jsonl(ledger_root / "cash_history.jsonl")
    events = _read_jsonl(ledger_root / "events.jsonl")
    reset_events = _read_jsonl(ledger_root / "broker_reset_events.jsonl")
    return {
        "artifact_type": "persistent_demo_ledger_state",
        "generated_at": utc_now_iso(),
        "ledger_root": str(ledger_root),
        "order_history_count": len(orders),
        "order_status_history_count": len(order_statuses),
        "execution_history_count": len(executions),
        "position_history_count": len(positions),
        "cash_history_count": len(cash),
        "lifecycle_event_count": len(events),
        "broker_reset_event_count": len(reset_events),
        "accepted_order_count": sum(1 for row in orders if row.get("accepted") is True),
        "rejected_order_count": sum(1 for row in orders if row.get("rejected") is True),
        "simulated_execution_count": sum(1 for row in executions if row.get("simulated_fill") is True),
        "simulated_position_count": sum(1 for row in positions if row.get("simulated_fill") is True),
        "demo_special_fill_simulation_used": any(row.get("event") == "demo_special_fill_simulation_9000_series" for row in events),
        "performance_metrics_excluded": True,
        "broker_snapshot_overwrites_demo_ledger": False,
        "persistent_demo_ledger_used_for_multiday_history": True,
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
        "plain_broker_ids_saved": False,
    }


def detect_demo_broker_daily_reset(
    *,
    root: Path,
    trade_date: str,
    broker_orders_count: int,
    broker_executions_count: int,
    broker_positions_count: int,
) -> dict[str, Any]:
    state = summarize_demo_ledger(root=root)
    has_prior_activity = (
        int(state.get("accepted_order_count", 0) or 0) > 0
        or int(state.get("execution_history_count", 0) or 0) > 0
        or int(state.get("position_history_count", 0) or 0) > 0
    )
    broker_empty = broker_orders_count == 0 and broker_executions_count == 0 and broker_positions_count == 0
    detected = has_prior_activity and broker_empty
    event = {
        "record_type": "broker_reset_event",
        "recorded_at": utc_now_iso(),
        "business_date": trade_date,
        "broker_daily_reset_detected": detected,
        "broker_orders_count": broker_orders_count,
        "broker_executions_count": broker_executions_count,
        "broker_positions_count": broker_positions_count,
        "classification": "DEMO_BROKER_DAILY_RESET_DETECTED" if detected else "NO_DEMO_BROKER_RESET",
        "demo_ledger_continues": True,
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
    }
    if detected:
        _append_jsonl(Path(root) / DEMO_LEDGER_DIR / "broker_reset_events.jsonl", event)
        write_json(Path(root) / DEMO_LEDGER_DIR / "state.json", summarize_demo_ledger(root=root))
    return event


def _safe_broker_order(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "issue_code": str(row.get("issue_code") or ""),
        "side": str(row.get("side") or ""),
        "quantity": str(row.get("quantity") or ""),
        "executed_quantity": str(row.get("executed_quantity") or ""),
        "remaining_quantity": str(row.get("remaining_quantity") or ""),
        "status": str(row.get("status") or ""),
        "price": str(row.get("price") or ""),
        "broker_order_id_hash": str(row.get("broker_order_id_hash") or ""),
    }


def _safe_execution(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "issue_code": str(row.get("issue_code") or ""),
        "side": str(row.get("side") or ""),
        "quantity": str(row.get("quantity") or row.get("executed_quantity") or ""),
        "price": str(row.get("price") or row.get("execution_price") or ""),
        "execution_datetime": str(row.get("execution_datetime") or row.get("datetime") or ""),
        "broker_order_id_hash": str(row.get("broker_order_id_hash") or ""),
    }


def _safe_position(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "position_id": str(row.get("position_id") or ""),
        "lot_reference": str(row.get("lot_reference") or ""),
        "issue_code": str(row.get("issue_code") or row.get("code") or ""),
        "quantity": str(row.get("quantity") or ""),
        "available_quantity": str(row.get("available_quantity") or ""),
        "average_cost": str(row.get("average_cost") or row.get("average_price") or ""),
        "market_price": str(row.get("market_price") or row.get("current_price") or ""),
        "market_value": str(row.get("market_value") or ""),
    }


def _safe_fill_event(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": str(row.get("item_id") or ""),
        "issue_code": str(row.get("issue_code") or ""),
        "side": str(row.get("side") or ""),
        "quantity": str(row.get("quantity") or ""),
        "lifecycle": str(row.get("lifecycle") or ""),
        "requires_human_review": row.get("requires_human_review") is True,
    }


def _buy_fill_status(fill_events: list[dict[str, Any]]) -> str:
    buy_events = [row for row in fill_events if str(row.get("side") or "").upper() == "BUY"]
    if not buy_events:
        return "NO_BUY_EVENT"
    lifecycles = {str(row.get("lifecycle") or "").upper() for row in buy_events}
    if "FILLED" in lifecycles:
        return "FILLED"
    if "PARTIALLY_FILLED" in lifecycles:
        return "PARTIALLY_FILLED"
    if "ACCEPTED" in lifecycles or "WAITING_FILL" in lifecycles:
        return "WAITING_FILL"
    if "UNKNOWN_STATUS" in lifecycles:
        return "UNKNOWN_STATUS"
    return sorted(lifecycles)[0] if lifecycles else "UNKNOWN"


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sanitized = sanitize_mapping(payload)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(sanitized, ensure_ascii=True, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows
