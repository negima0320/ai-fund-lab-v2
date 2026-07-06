from __future__ import annotations

import json

from ai_fund_lab_v2.operations.persistent_ledger import (
    append_cash_state,
    append_event,
    append_execution,
    append_order,
    append_position_state,
    summarize_persistent_ledger,
)


def test_persistent_ledger_writes_all_jsonl_and_state(tmp_path):
    root = tmp_path / "operations"

    append_order(
        root=root,
        record={
            "business_date": "2026-07-03",
            "environment": "demo",
            "source": "submitted_orders",
            "item_id": "item-1",
            "issue_code": "7203",
            "side": "BUY",
            "quantity": "100",
            "broker_order_id": "RAW-BROKER-ORDER-ID",
        },
    )
    append_execution(
        root=root,
        record={
            "business_date": "2026-07-03",
            "environment": "demo",
            "source": "broker_executions",
            "execution_key": "exec-1",
            "issue_code": "7203",
            "side": "BUY",
            "quantity": "100",
            "price": "2000",
            "execution_id": "RAW-EXECUTION-ID",
        },
    )
    append_position_state(
        root=root,
        record={
            "business_date": "2026-07-03",
            "environment": "demo",
            "source": "broker_positions",
            "issue_code": "7203",
            "account_type": "cash",
            "quantity": "100",
            "average_price": "2000",
            "market_value": "200000",
        },
    )
    append_cash_state(
        root=root,
        record={
            "business_date": "2026-07-03",
            "environment": "demo",
            "source": "broker_buying_power",
            "cash_state_key": "cash-2026-07-03",
            "cash_available": "800000",
            "buying_power": "800000",
            "currency": "JPY",
        },
    )
    append_event(
        root=root,
        record={
            "business_date": "2026-07-03",
            "environment": "demo",
            "source": "fill_monitor",
            "event_id": "event-1",
            "event": "position_confirmed",
        },
    )

    ledger_root = root / "persistent_ledger"
    for file_name in ("orders.jsonl", "executions.jsonl", "positions.jsonl", "cash_history.jsonl", "events.jsonl", "migrations.jsonl"):
        assert (ledger_root / file_name).exists()

    state = json.loads((ledger_root / "state.json").read_text(encoding="utf-8"))
    assert state["artifact_type"] == "persistent_ledger_state"
    assert state["orders_count"] == 1
    assert state["executions_count"] == 1
    assert state["position_history_count"] == 1
    assert state["cash_history_count"] == 1
    assert state["event_count"] == 1
    assert state["current_position_count"] == 1
    assert state["current_positions"][0]["issue_code"] == "7203"
    assert state["current_positions"][0]["quantity"] == "100"
    assert state["current_cash"]["buying_power"] == "800000"
    assert state["demo_production_common_storage"] is True
    assert state["runtime_reference_switched"] is False


def test_persistent_ledger_dedups_by_item_and_execution_key(tmp_path):
    root = tmp_path / "operations"
    first = append_order(root=root, record={"environment": "production", "source": "submitted_orders", "item_id": "same-item", "issue_code": "7203"})
    second = append_order(root=root, record={"environment": "production", "source": "submitted_orders", "item_id": "same-item", "issue_code": "7203"})
    assert first["status"] == "APPENDED"
    assert second["status"] == "DEDUP_SKIPPED"

    append_execution(root=root, record={"environment": "production", "source": "broker_executions", "execution_key": "same-exec", "issue_code": "7203", "quantity": "100"})
    append_execution(root=root, record={"environment": "production", "source": "broker_executions", "execution_key": "same-exec", "issue_code": "7203", "quantity": "100"})

    state = summarize_persistent_ledger(root=root)
    assert state["orders_count"] == 1
    assert state["executions_count"] == 1


def test_persistent_ledger_does_not_save_secret_raw_or_plain_broker_ids(tmp_path):
    root = tmp_path / "operations"
    append_order(
        root=root,
        record={
            "environment": "demo",
            "source": "submitted_orders",
            "item_id": "secret-test",
            "issue_code": "7203",
            "raw_request": {"sPassword": "SECRET-PASSWORD"},
            "raw_response": {"broker_order_id": "RAW-BROKER-ID"},
            "secret": "SECRET-VALUE",
            "token": "TOKEN-VALUE",
            "url": "https://secret.example.invalid",
            "broker_order_id": "RAW-BROKER-ID",
            "broker_order_id_hash": "sha256:broker-hash",
        },
    )
    serialized = (root / "persistent_ledger" / "orders.jsonl").read_text(encoding="utf-8")
    assert "SECRET-PASSWORD" not in serialized
    assert "SECRET-VALUE" not in serialized
    assert "TOKEN-VALUE" not in serialized
    assert "secret.example" not in serialized
    assert "RAW-BROKER-ID" not in serialized
    assert "broker_order_id_hash" in serialized
    assert '"raw_request_saved": false' in serialized
    assert '"raw_response_saved": false' in serialized
    assert '"secret_saved": false' in serialized
    assert '"plain_broker_ids_saved": false' in serialized


def test_persistent_ledger_supports_demo_and_production_metadata(tmp_path):
    root = tmp_path / "operations"
    append_event(root=root, record={"environment": "demo", "source": "broker_readonly", "event_id": "demo-event", "event": "demo_check"})
    append_event(root=root, record={"environment": "production", "source": "broker_readonly", "event_id": "prod-event", "event": "prod_check"})

    state = summarize_persistent_ledger(root=root)
    assert state["environments"] == ["demo", "production"]
    assert state["sources"] == ["broker_readonly"]
    assert state["demo_production_common_storage"] is True


def test_persistent_ledger_phase_a_does_not_create_runtime_daily_artifacts(tmp_path):
    root = tmp_path / "operations"
    append_position_state(root=root, record={"environment": "demo", "source": "broker_positions", "issue_code": "7203", "quantity": "100"})

    assert (root / "persistent_ledger" / "state.json").exists()
    assert not (root / "order_plan").exists()
    assert not (root / "approval_artifact").exists()
    assert not (root / "submitted_orders").exists()
    assert not (root / "reports").exists()
