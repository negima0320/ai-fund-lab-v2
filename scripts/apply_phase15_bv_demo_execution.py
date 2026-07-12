from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUEST_HASH = "sha256:56ebea4e14ffe7369f133260645720c49303711b74c21960973e833016b37f70"
BROKER_ORDER_HASH_FULL = "sha256:b80b43eeb157caa8a56c14684356cbbd0b9cddebc05905a49059f72e4861d153"
BROKER_ORDER_HASH_SHORT = "order_b80b43eeb157caa8"
EXECUTION_ID = "phase15bv-demo-execution-equivalent-6501-sell-100"
LEDGER_ORDER_ID = "ledger-order-phase15bv-6501-sell-100"
LEDGER_EXECUTION_ID = "ledger-execution-phase15bv-6501-sell-100"
LEDGER_POSITION_ID = "ledger-position-phase15bv-6501-after-sell"
LEDGER_CASH_ID = "ledger-cash-phase15bv-after-sell"
LEDGER_EVENT_ID = "ledger-event-phase15bv-current-apply"
CURRENT_VERSION = "phase15bv_current_v1"
RUNTIME_STATE_VERSION = "phase15bv_runtime_state_v1"
BUSINESS_DATE = "2026-07-13"
EXECUTION_DATE = "2026-07-12"
EXECUTION_PRICE = 100.0
VALUATION_PRICE = 4700.0
QUANTITY = 100.0
POSITION_BEFORE = 200.0
POSITION_AFTER = 100.0
CASH_AFTER = 17704424.0
BUYING_POWER_AFTER = 20009824.0
CASH_BEFORE = CASH_AFTER - EXECUTION_PRICE * QUANTITY
MARKET_VALUE_AFTER = POSITION_AFTER * VALUATION_PRICE
PORTFOLIO_VALUE_AFTER = CASH_AFTER + MARKET_VALUE_AFTER
MARKET_VALUE_BEFORE = POSITION_BEFORE * VALUATION_PRICE
PORTFOLIO_VALUE_BEFORE = CASH_BEFORE + MARKET_VALUE_BEFORE


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", default=".runtime_acceptance_phase15_demo_reinit")
    parser.add_argument("--reports-root", default="reports/phase_reports/phase15_bv")
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()

    root = Path(args.runtime_root)
    reports_root = Path(args.reports_root)
    reports_root.mkdir(parents=True, exist_ok=True)

    before = snapshot(root)
    now = datetime.now(timezone.utc).isoformat()

    state_path = root / "persistent_ledger" / "state.json"
    current_before = read_json(state_path, default={})
    already_applied = bool(current_before.get("phase15_bv_current_apply", {}).get("applied"))

    result: dict[str, Any] = {
        "schema_version": "phase15bv_apply_attempt_v1",
        "attempt": args.attempt,
        "generated_at": now,
        "runtime_root": str(root),
        "business_date": BUSINESS_DATE,
        "already_applied_before_attempt": already_applied,
        "new_broker_write": False,
        "resubmit": False,
        "auto_cancel": False,
        "notification_send": False,
        "production_write": False,
    }

    if already_applied:
        after = snapshot(root)
        result.update(
            {
                "status": "NOOP_ALREADY_APPLIED",
                "ledger_records_appended": 0,
                "current_apply_performed": False,
                "idempotent": before == after,
                "before": before,
                "after": after,
            }
        )
        write_json(reports_root / f"apply_attempt_{args.attempt}.json", result)
        return

    ledger_dir = root / "persistent_ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)

    normalized = normalized_execution(now)
    write_json(reports_root / "execution_normalization.json", normalized)

    orders_added = append_jsonl_once(ledger_dir / "orders.jsonl", ledger_order(now))
    executions_added = append_jsonl_once(ledger_dir / "executions.jsonl", ledger_execution(now))
    positions_added = append_jsonl_once(ledger_dir / "positions.jsonl", ledger_position(now))
    cash_added = append_jsonl_once(ledger_dir / "cash.jsonl", ledger_cash(now))
    events_added = append_jsonl_once(ledger_dir / "events.jsonl", ledger_event(now))

    current_payload = current_state_payload(now)
    write_json(state_path, current_payload)

    pending_result = update_pending(root / "pending_order_plan" / "pending_order_plan.json", now)
    runtime_state_result = update_runtime_state(root / "runtime_state" / "current_state.json", state_path, now)

    projection = {
        "schema_version": "phase15bv_current_projection_v1",
        "source": "DEMO_ORDERLIST_POSITION_EXECUTION_EQUIVALENT_FALLBACK_V1",
        "business_date": BUSINESS_DATE,
        "execution_id": EXECUTION_ID,
        "position_before": POSITION_BEFORE,
        "position_after": POSITION_AFTER,
        "position_delta": POSITION_AFTER - POSITION_BEFORE,
        "cash_before": CASH_BEFORE,
        "cash_after": CASH_AFTER,
        "cash_delta": CASH_AFTER - CASH_BEFORE,
        "buying_power_after": BUYING_POWER_AFTER,
        "market_value_before": MARKET_VALUE_BEFORE,
        "market_value_after": MARKET_VALUE_AFTER,
        "portfolio_value_before": PORTFOLIO_VALUE_BEFORE,
        "portfolio_value_after": PORTFOLIO_VALUE_AFTER,
        "execution_price": EXECUTION_PRICE,
        "valuation_price": VALUATION_PRICE,
        "production_equivalent": False,
        "broker_cash_copied": False,
        "unrelated_demo_positions_copied": False,
    }
    write_json(reports_root / "current_projection.json", projection)

    after = snapshot(root)
    result.update(
        {
            "status": "APPLIED",
            "execution_normalization_performed": True,
            "ledger_append_performed": True,
            "current_projection_performed": True,
            "current_apply_performed": True,
            "runtime_state_update_performed": True,
            "pending_update_performed": pending_result["updated"],
            "runtime_state_result": runtime_state_result,
            "pending_result": pending_result,
            "ledger_records_appended": orders_added + executions_added + positions_added + cash_added + events_added,
            "ledger_appended_by_file": {
                "orders": orders_added,
                "executions": executions_added,
                "positions": positions_added,
                "cash": cash_added,
                "events": events_added,
            },
            "before": before,
            "after": after,
            "current_hash_changed": before.get("current_hash") != after.get("current_hash"),
            "current_hash": after.get("current_hash"),
            "current_version": CURRENT_VERSION,
            "runtime_state_version": RUNTIME_STATE_VERSION,
        }
    )
    write_json(reports_root / f"apply_attempt_{args.attempt}.json", result)


def normalized_execution(generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": "phase15bv_execution_normalization_v1",
        "execution_id": EXECUTION_ID,
        "issue_code": "6501",
        "side": "SELL",
        "quantity": QUANTITY,
        "execution_price": EXECUTION_PRICE,
        "execution_currency": "JPY",
        "execution_date": EXECUTION_DATE,
        "execution_source": "DEMO_ORDERLIST_POSITION_EXECUTION_EQUIVALENT_FALLBACK_V1",
        "broker_order_hash": BROKER_ORDER_HASH_FULL,
        "broker_order_hash_short": BROKER_ORDER_HASH_SHORT,
        "request_hash": REQUEST_HASH,
        "execution_equivalent": True,
        "production_equivalent": False,
        "demo_only": True,
        "valuation_price": VALUATION_PRICE,
        "valuation_price_used_as_execution_price": False,
        "generated_at": generated_at,
    }


def ledger_base(record_id: str, record_type: str, source: str, created_at: str) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "ledger_record_id": record_id,
        "record_type": record_type,
        "schema_version": "1",
        "environment": "demo",
        "source": source,
        "created_at": created_at,
        "recorded_at": created_at,
        "review_required": False,
        "production_equivalent": False,
    }


def ledger_order(created_at: str) -> dict[str, Any]:
    payload = ledger_base(LEDGER_ORDER_ID, "order", "phase15bv_demo_fallback_current_apply", created_at)
    payload.update(
        {
            "dedup_key": f"phase15bv:order:{REQUEST_HASH}",
            "order_id": BROKER_ORDER_HASH_FULL,
            "business_date": BUSINESS_DATE,
            "pending_plan_id": "pending-order-plan-phase15bs-sell-6501",
            "pending_item_id": "phase15bs-sell-6501",
            "side": "SELL",
            "symbol": "6501",
            "quantity": QUANTITY,
            "status": "ACCEPTED_FILLED_DEMO_EQUIVALENT",
            "request_hash": REQUEST_HASH,
            "broker_order_hash": BROKER_ORDER_HASH_FULL,
            "execution_equivalent": True,
        }
    )
    return payload


def ledger_execution(created_at: str) -> dict[str, Any]:
    payload = ledger_base(LEDGER_EXECUTION_ID, "execution", "phase15bv_demo_fallback_current_apply", created_at)
    payload.update(
        {
            "dedup_key": f"phase15bv:execution:{REQUEST_HASH}",
            "execution_id": EXECUTION_ID,
            "order_id": BROKER_ORDER_HASH_FULL,
            "execution_key": f"execution_equivalent:{BUSINESS_DATE}:6501:SELL",
            "execution_evidence_type": "demo_orderlist_position_execution_equivalent",
            "business_date": BUSINESS_DATE,
            "mode": "demo",
            "side": "SELL",
            "symbol": "6501",
            "broker_issue_code": "6501",
            "quantity": QUANTITY,
            "filled_quantity": QUANTITY,
            "remaining_quantity": 0.0,
            "order_status": "filled",
            "execution_status": "filled",
            "price_source": "demo_browser_confirmation",
            "price": EXECUTION_PRICE,
            "average_price": EXECUTION_PRICE,
            "market_price": VALUATION_PRICE,
            "market_value": MARKET_VALUE_AFTER,
            "cash_effect": EXECUTION_PRICE * QUANTITY,
            "request_hash": REQUEST_HASH,
            "broker_order_hash": BROKER_ORDER_HASH_FULL,
            "source_order_hash": BROKER_ORDER_HASH_FULL,
            "source_broker_order_hash": BROKER_ORDER_HASH_FULL,
            "evidence_refs": [
                "CLMOrderList",
                "CLMGenbutuKabuList",
                "CLMZanKaiSummary",
                "CLMZanKaiKanougaku",
                "operator_browser_confirmation",
            ],
            "detail_required": False,
            "detail_status": "DEMO_FALLBACK_ACCEPTED",
            "executed_at": "2026-07-12T10:04:00+09:00",
            "execution_equivalent": True,
            "demo_only": True,
        }
    )
    return payload


def ledger_position(created_at: str) -> dict[str, Any]:
    payload = ledger_base(LEDGER_POSITION_ID, "position", "phase15bv_demo_fallback_current_apply", created_at)
    payload.update(
        {
            "dedup_key": f"phase15bv:position:6501:{REQUEST_HASH}",
            "position_key": "6501:cash",
            "symbol": "6501",
            "quantity": POSITION_AFTER,
            "average_price": VALUATION_PRICE,
            "market_value": MARKET_VALUE_AFTER,
            "valuation_price": VALUATION_PRICE,
            "execution_price": EXECUTION_PRICE,
            "as_of": "2026-07-12T01:38:37.699366+00:00",
            "request_hash": REQUEST_HASH,
            "broker_order_hash": BROKER_ORDER_HASH_FULL,
        }
    )
    return payload


def ledger_cash(created_at: str) -> dict[str, Any]:
    payload = ledger_base(LEDGER_CASH_ID, "cash", "phase15bv_demo_fallback_current_apply", created_at)
    payload.update(
        {
            "dedup_key": f"phase15bv:cash:{REQUEST_HASH}",
            "cash_key": "phase15bv-after-sell-cash",
            "cash_snapshot_key": "phase15bv-after-sell-cash",
            "cash": CASH_AFTER,
            "cash_before": CASH_BEFORE,
            "cash_delta": CASH_AFTER - CASH_BEFORE,
            "buying_power": BUYING_POWER_AFTER,
            "currency": "JPY",
            "as_of": "2026-07-12T01:38:37.416016+00:00",
            "request_hash": REQUEST_HASH,
            "broker_order_hash": BROKER_ORDER_HASH_FULL,
        }
    )
    return payload


def ledger_event(created_at: str) -> dict[str, Any]:
    payload = ledger_base(LEDGER_EVENT_ID, "event", "phase15bv_demo_fallback_current_apply", created_at)
    payload.update(
        {
            "dedup_key": f"phase15bv:event:{REQUEST_HASH}",
            "event_id": "phase15bv-current-apply-6501",
            "event_type": "DEMO_EXECUTION_EQUIVALENT_CURRENT_APPLIED",
            "severity": "INFO",
            "message": "Phase15-BV applied demo-only execution-equivalent evidence for 6501 SELL 100 to isolated Current.",
            "related_id": EXECUTION_ID,
            "request_hash": REQUEST_HASH,
            "broker_order_hash": BROKER_ORDER_HASH_FULL,
        }
    )
    return payload


def current_state_payload(generated_at: str) -> dict[str, Any]:
    generated_from = [LEDGER_EXECUTION_ID, LEDGER_POSITION_ID, LEDGER_CASH_ID]
    payload = {
        "schema_version": "runtime_v2_current_temporal_v1",
        "temporal_schema_version": "runtime_v2_current_temporal_v1",
        "current_version": CURRENT_VERSION,
        "asset_state_id": stable_id("asset", "|".join(generated_from)),
        "environment": "demo",
        "source": "phase15bv_demo_fallback_current_apply",
        "as_of": BUSINESS_DATE,
        "business_date": BUSINESS_DATE,
        "position_state_as_of": EXECUTION_DATE,
        "valuation_as_of": BUSINESS_DATE,
        "last_execution_date": EXECUTION_DATE,
        "last_reconciled_at": generated_at,
        "source_market_date": BUSINESS_DATE,
        "positions": [
            {
                "symbol": "6501",
                "quantity": POSITION_AFTER,
                "average_price": VALUATION_PRICE,
                "market_value": MARKET_VALUE_AFTER,
                "cost_basis": POSITION_AFTER * VALUATION_PRICE,
                "unrealized_pnl": 0.0,
                "source": "phase15bv_demo_fallback_current_apply",
                "as_of": "2026-07-12T01:38:37.699366+00:00",
                "execution_price": EXECUTION_PRICE,
                "valuation_price": VALUATION_PRICE,
                "execution_price_used_for_valuation": False,
                "production_equivalent": False,
            }
        ],
        "cash": CASH_AFTER,
        "cash_before": CASH_BEFORE,
        "cash_delta": CASH_AFTER - CASH_BEFORE,
        "buying_power": BUYING_POWER_AFTER,
        "market_value": MARKET_VALUE_AFTER,
        "total_equity": PORTFOLIO_VALUE_AFTER,
        "broker_total_assets_reference": BUYING_POWER_AFTER,
        "portfolio_scope": "phase15bv_6501_acceptance_current_scope",
        "review_required": False,
        "production_equivalent": False,
        "current_state_confirmed_empty": False,
        "current_positions_unknown": False,
        "cash_unknown": False,
        "buying_power_unknown": False,
        "cash_confirmed": True,
        "buying_power_confirmed": True,
        "generated_from": generated_from,
        "created_at": generated_at,
        "updated_at": generated_at,
        "current_position_status": "READY",
        "current_valuation_status": "READY",
        "temporal_status": "READY",
        "position_state_source": "DEMO_ORDERLIST_POSITION_EXECUTION_EQUIVALENT_FALLBACK_V1",
        "valuation_source": "CLMGenbutuKabuList",
        "runtime_owned_projection": {
            "broker_cash_copied": False,
            "unrelated_demo_positions_copied": False,
            "position_policy": "phase15bv_demo_6501_acceptance_only",
            "cash_policy": "broker_cash_after_demo_sell_plus_execution_cash_delta_audit",
            "production_applicable": False,
        },
        "phase15_bv_current_apply": {
            "applied": True,
            "execution_id": EXECUTION_ID,
            "request_hash": REQUEST_HASH,
            "broker_order_hash": BROKER_ORDER_HASH_FULL,
            "execution_equivalent": True,
            "demo_only": True,
            "position_before": POSITION_BEFORE,
            "position_after": POSITION_AFTER,
            "cash_before": CASH_BEFORE,
            "cash_after": CASH_AFTER,
            "execution_price": EXECUTION_PRICE,
            "valuation_price": VALUATION_PRICE,
        },
    }
    return payload


def update_pending(path: Path, generated_at: str) -> dict[str, Any]:
    payload = read_json(path, default={})
    before_hash = sha256_path(path) if path.exists() else ""
    if payload.get("state") != "CONSUMED":
        payload["state"] = "CONSUMED"
        payload["updated_at"] = generated_at
        consume = payload.setdefault("consume", {})
        consume["consumed"] = True
        consume["consumed_at"] = generated_at
        consume["consume_reason"] = "phase15bv_execution_normalization_ledger_current_apply_completed"
        consume["submitted_order_ids"] = [BROKER_ORDER_HASH_FULL]
        consume["ledger_order_record_ids"] = [LEDGER_ORDER_ID]
        for item in payload.get("items") or []:
            if item.get("pending_item_id") == "phase15bs-sell-6501":
                item["state"] = "CURRENT_APPLIED"
                item["execution_id"] = EXECUTION_ID
                item["ledger_execution_record_id"] = LEDGER_EXECUTION_ID
        write_json(path, payload)
        updated = True
    else:
        updated = False
    return {"updated": updated, "before_hash": before_hash, "after_hash": sha256_path(path)}


def update_runtime_state(path: Path, current_path: Path, generated_at: str) -> dict[str, Any]:
    payload = read_json(path, default={})
    before_hash = sha256_path(path) if path.exists() else ""
    payload.update(
        {
            "schema_version": "runtime_v2_operation_state_v1",
            "role": "authoritative_runtime_operation_state",
            "business_date": BUSINESS_DATE,
            "generated_at": payload.get("generated_at") or generated_at,
            "updated_at": generated_at,
            "environment": "demo",
            "runtime_mode": "demo",
            "state": "CURRENT_APPLIED",
            "safety_state": payload.get("safety_state") or "NORMAL",
            "current_safety_state": payload.get("current_safety_state") or "NORMAL",
            "source": "runtime_v2_runtime_state_producer",
            "producer": "phase15bv_execution_current_apply",
            "reason": "phase15bv_current_apply_completed",
            "asset_state_source": "persistent_ledger/state.json",
            "pending_state_source": "pending_order_plan/pending_order_plan.json",
            "asset_state_is_authoritative_here": False,
            "pending_state_is_authoritative_here": False,
            "production_equivalent": False,
            "runtime_state_version": RUNTIME_STATE_VERSION,
            "current_pointer": str(current_path),
            "current_version": CURRENT_VERSION,
            "current_hash": "sha256:" + sha256_path(current_path),
            "current_timestamp": generated_at,
            "execution_reference": EXECUTION_ID,
            "execution_reference_hash": BROKER_ORDER_HASH_FULL,
        }
    )
    write_json(path, payload)
    return {"updated": True, "before_hash": before_hash, "after_hash": sha256_path(path)}


def append_jsonl_once(path: Path, record: dict[str, Any]) -> int:
    rows = read_jsonl(path)
    dedup = record["dedup_key"]
    if any(row.get("dedup_key") == dedup for row in rows):
        return 0
    rows.append(record)
    write_jsonl(path, rows)
    return 1


def snapshot(root: Path) -> dict[str, Any]:
    paths = {
        "orders": root / "persistent_ledger" / "orders.jsonl",
        "executions": root / "persistent_ledger" / "executions.jsonl",
        "positions": root / "persistent_ledger" / "positions.jsonl",
        "cash": root / "persistent_ledger" / "cash.jsonl",
        "events": root / "persistent_ledger" / "events.jsonl",
        "current": root / "persistent_ledger" / "state.json",
        "pending": root / "pending_order_plan" / "pending_order_plan.json",
        "runtime_state": root / "runtime_state" / "current_state.json",
    }
    current = read_json(paths["current"], default={})
    return {
        "ledger_counts": {key: len(read_jsonl(path)) for key, path in paths.items() if key in {"orders", "executions", "positions", "cash", "events"}},
        "current_exists": paths["current"].exists(),
        "current_hash": sha256_path(paths["current"]) if paths["current"].exists() else "",
        "pending_hash": sha256_path(paths["pending"]) if paths["pending"].exists() else "",
        "runtime_state_hash": sha256_path(paths["runtime_state"]) if paths["runtime_state"].exists() else "",
        "position_6501_quantity": (((current.get("positions") or [{}])[0]).get("quantity") if current.get("positions") else None),
        "cash": current.get("cash"),
        "buying_power": current.get("buying_power"),
        "market_value": current.get("market_value"),
        "total_equity": current.get("total_equity"),
        "current_version": current.get("current_version"),
    }


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return deepcopy(default)
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_id(prefix: str, raw: str) -> str:
    return prefix + "-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


if __name__ == "__main__":
    main()
