from ai_fund_lab_v2.operations.demo_ledger import (
    detect_demo_broker_daily_reset,
    record_demo_readonly_monitoring,
    record_demo_submit_result,
    summarize_demo_ledger,
)


def test_persistent_demo_ledger_records_rejected_order_without_raw_values(tmp_path):
    payload = {
        "artifact_type": "demo_submit",
        "business_date": "2026-06-29",
        "submitted_orders": [
            {
                "run_id": "operation_2026-06-29_approval_retry_buy",
                "approval_id": "approval_retry",
                "item_id": "buy_2026-06-29_92560_001",
                "side": "BUY",
                "code": "92560",
                "quantity": "100",
                "limit_price": "5410",
                "expected_notional": "541000",
                "status": "REJECTED_OR_UNKNOWN",
                "broker_order_id_hash": "",
                "normalized_order": {"order_type": "CASH_EQUITY", "price_type": "LIMIT"},
                "wire_execution_result": {"response": {"accepted": False, "rejected": True}},
            }
        ],
    }
    retry_parent = {"phase": "Phase12-Q", "accepted": False, "rejected": True}

    state = record_demo_submit_result(root=tmp_path, trade_date="2026-06-29", submit_payload=payload, retry_parent=retry_parent)

    assert state["order_history_count"] == 1
    assert state["rejected_order_count"] == 1
    assert state["broker_snapshot_overwrites_demo_ledger"] is False
    assert state["raw_request_saved"] is False
    assert state["raw_response_saved"] is False
    assert state["secret_saved"] is False
    assert "Phase12-Q" in (tmp_path / "demo_ledger" / "orders.jsonl").read_text(encoding="utf-8")


def test_demo_broker_reset_detection_keeps_persistent_history(tmp_path):
    payload = {
        "submitted_orders": [
            {
                "run_id": "operation_accepted",
                "approval_id": "approval_retry",
                "item_id": "buy",
                "side": "BUY",
                "code": "92560",
                "quantity": "100",
                "status": "ORDER_ACCEPTED",
                "wire_execution_result": {"response": {"accepted": True, "rejected": False}},
            }
        ]
    }
    record_demo_submit_result(root=tmp_path, trade_date="2026-06-29", submit_payload=payload)

    reset = detect_demo_broker_daily_reset(
        root=tmp_path,
        trade_date="2026-06-30",
        broker_orders_count=0,
        broker_executions_count=0,
        broker_positions_count=0,
    )
    state = summarize_demo_ledger(root=tmp_path)

    assert reset["broker_daily_reset_detected"] is True
    assert reset["classification"] == "DEMO_BROKER_DAILY_RESET_DETECTED"
    assert state["order_history_count"] == 1
    assert state["broker_reset_event_count"] == 1


def test_demo_readonly_monitoring_updates_ledger_without_raw_values(tmp_path):
    state = record_demo_readonly_monitoring(
        root=tmp_path,
        trade_date="2026-06-29",
        submitted_orders=[{"item_id": "buy_1", "side": "BUY", "issue_code": "92560"}],
        broker_orders=[
            {
                "issue_code": "9256",
                "side": "3",
                "quantity": "100",
                "executed_quantity": "0",
                "remaining_quantity": "100",
                "status": "未約定",
            }
        ],
        broker_executions=[],
        broker_positions=[],
        buying_power={"buying_power": "19458494", "cash_available": "19458494", "currency": "JPY"},
        fill_events=[{"item_id": "buy_1", "issue_code": "92560", "side": "BUY", "quantity": "100", "lifecycle": "ACCEPTED"}],
    )

    assert state["order_status_history_count"] == 1
    assert state["cash_history_count"] == 1
    assert state["execution_history_count"] == 0
    assert state["position_history_count"] == 0
    assert state["raw_request_saved"] is False
    assert state["raw_response_saved"] is False
    assert state["secret_saved"] is False
    assert "19458494" in (tmp_path / "demo_ledger" / "cash_history.jsonl").read_text(encoding="utf-8")
