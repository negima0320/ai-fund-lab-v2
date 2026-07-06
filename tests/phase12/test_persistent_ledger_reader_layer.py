from __future__ import annotations

import json

from ai_fund_lab_v2.operations.persistent_ledger import (
    append_cash_state,
    append_execution,
    append_order,
    append_position_state,
    get_current_cash,
    get_current_positions,
    get_execution_history,
    get_order_history,
    get_position_by_code,
    get_positions_source_summary,
    get_review_required_positions,
    read_persistent_ledger_state,
)


def test_reader_reads_current_positions_from_state(tmp_path):
    root = tmp_path / "operations"
    append_position_state(
        root=root,
        record={
            "business_date": "2026-07-03",
            "environment": "demo",
            "source": "broker_positions",
            "issue_code": "7203",
            "quantity": "100",
            "market_value": "200000",
        },
    )

    result = get_current_positions(root)

    assert result["state_missing"] is False
    assert result["current_position_count"] == 1
    assert result["current_market_value"] == "200000"
    assert result["current_positions"][0]["issue_code"] == "7203"
    assert result["current_positions_review_required"] is False
    assert result["review_required_position_count"] == 0


def test_reader_returns_state_missing_without_confirming_empty_positions(tmp_path):
    root = tmp_path / "operations"

    state = read_persistent_ledger_state(root)
    positions = get_current_positions(root)
    cash = get_current_cash(root)

    assert state["state_missing"] is True
    assert state["current_state_confirmed_empty"] is False
    assert positions["state_missing"] is True
    assert positions["current_position_count"] == 0
    assert positions["current_positions_review_required"] is True
    assert cash["state_missing"] is True
    assert cash["cash_review_required"] is True


def test_reader_finds_position_by_internal_or_broker_issue_code(tmp_path):
    root = tmp_path / "operations"
    append_position_state(
        root=root,
        record={
            "environment": "demo",
            "source": "broker_positions",
            "broker_issue_code": "6522",
            "quantity": "100",
            "market_value": "150000",
        },
    )

    by_broker_code = get_position_by_code(root, "6522")
    by_internal_code = get_position_by_code(root, "65220")

    assert by_broker_code is not None
    assert by_internal_code is not None
    assert by_broker_code["position_key"] == by_internal_code["position_key"]
    assert by_internal_code["issue_code"] == "6522"


def test_reader_extracts_review_required_fallback_positions(tmp_path):
    root = tmp_path / "operations"
    append_position_state(
        root=root,
        record={
            "environment": "demo",
            "source": "broker_orders_fallback",
            "broker_issue_code": "6522",
            "quantity": "100",
            "review_required": True,
            "production_equivalent": False,
        },
    )

    review_positions = get_review_required_positions(root)
    current = get_current_positions(root)

    assert len(review_positions) == 1
    assert review_positions[0]["review_required"] is True
    assert review_positions[0]["production_equivalent"] is False
    assert current["current_positions_review_required"] is True
    assert current["review_required_position_count"] == 1


def test_reader_reads_current_cash(tmp_path):
    root = tmp_path / "operations"
    append_cash_state(
        root=root,
        record={
            "environment": "production",
            "source": "broker_buying_power",
            "cash_state_key": "cash-1",
            "cash_available": "900000",
            "buying_power": "850000",
            "currency": "JPY",
        },
    )

    cash = get_current_cash(root)

    assert cash["cash_available"] == "900000"
    assert cash["buying_power"] == "850000"
    assert cash["evaluation_equity_basis"] == "850000"
    assert cash["cash_source"] == "broker_buying_power"
    assert cash["cash_review_required"] is False


def test_reader_filters_execution_and_order_history(tmp_path):
    root = tmp_path / "operations"
    append_order(root=root, record={"business_date": "2026-07-01", "environment": "demo", "source": "submitted_orders", "item_id": "old", "issue_code": "7203"})
    append_order(root=root, record={"business_date": "2026-07-03", "environment": "demo", "source": "submitted_orders", "item_id": "new", "issue_code": "6522"})
    append_execution(root=root, record={"business_date": "2026-07-02", "environment": "demo", "source": "broker_executions", "execution_key": "exec-old", "broker_issue_code": "6522", "quantity": "100"})
    append_execution(root=root, record={"business_date": "2026-07-04", "environment": "demo", "source": "broker_executions", "execution_key": "exec-new", "broker_issue_code": "6522", "quantity": "100"})

    orders = get_order_history(root, code="65220", date_from="2026-07-02", date_to="2026-07-03")
    executions = get_execution_history(root, code="6522", date_from="2026-07-03")

    assert [row["item_id"] for row in orders] == ["new"]
    assert [row["execution_key"] for row in executions] == ["exec-new"]


def test_reader_source_summary(tmp_path):
    root = tmp_path / "operations"
    append_position_state(root=root, record={"environment": "demo", "source": "broker_positions", "issue_code": "7203", "quantity": "100"})
    append_position_state(root=root, record={"environment": "demo", "source": "broker_orders_fallback", "issue_code": "6522", "quantity": "100", "review_required": True})

    summary = get_positions_source_summary(root)

    assert summary["position_count"] == 2
    assert summary["by_source"] == {"broker_orders_fallback": 1, "broker_positions": 1}
    assert summary["by_environment"] == {"demo": 2}
    assert summary["review_required_position_count"] == 1


def test_reader_does_not_return_secret_raw_or_plain_broker_ids(tmp_path):
    root = tmp_path / "operations"
    append_order(
        root=root,
        record={
            "business_date": "2026-07-03",
            "environment": "demo",
            "source": "submitted_orders",
            "item_id": "secret-order",
            "issue_code": "7203",
            "raw_request": {"password": "SECRET-PASSWORD"},
            "raw_response": {"broker_order_id": "RAW-BROKER-ID"},
            "broker_order_id": "RAW-BROKER-ID",
            "broker_order_id_hash": "sha256:hash",
        },
    )

    serialized = json.dumps(get_order_history(root), ensure_ascii=False)

    assert "SECRET-PASSWORD" not in serialized
    assert "RAW-BROKER-ID" not in serialized
    assert "broker_order_id_hash" in serialized
    assert '"raw_request":' not in serialized
    assert '"raw_response":' not in serialized
    assert '"raw_request_saved": false' in serialized
    assert '"raw_response_saved": false' in serialized


def test_reader_layer_does_not_create_runtime_daily_artifacts(tmp_path):
    root = tmp_path / "operations"
    append_position_state(root=root, record={"environment": "demo", "source": "broker_positions", "issue_code": "7203", "quantity": "100"})

    _ = get_current_positions(root)
    _ = get_current_cash(root)
    _ = get_order_history(root)
    _ = get_execution_history(root)

    assert (root / "persistent_ledger" / "state.json").exists()
    assert not (root / "order_plan").exists()
    assert not (root / "approval_artifact").exists()
    assert not (root / "reports").exists()
    assert not (root / "notifications").exists()
