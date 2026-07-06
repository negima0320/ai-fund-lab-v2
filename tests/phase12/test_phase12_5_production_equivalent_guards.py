from __future__ import annotations

from ai_fund_lab_v2.broker.settings import DEMO_BASE_URL, PROD_BASE_URL, load_broker_settings
from ai_fund_lab_v2.operations.broker_readonly import write_broker_readonly_artifacts_from_snapshot
from ai_fund_lab_v2.operations.guards import validate_runtime_environment
from ai_fund_lab_v2.operations.io import read_json, write_json
from ai_fund_lab_v2.operations.notifications import run_operation_notifications
from ai_fund_lab_v2.operations.operations import run_reconcile


def test_prod_and_production_resolve_to_same_base_url() -> None:
    prod = load_broker_settings({"TACHIBANA_API_ENV": "prod"})
    production = load_broker_settings({"TACHIBANA_API_ENV": "production"})

    assert prod.environment == "production"
    assert production.environment == "production"
    assert prod.base_url == PROD_BASE_URL
    assert production.base_url == PROD_BASE_URL


def test_runtime_environment_blocks_crossed_env_and_base_url() -> None:
    assert validate_runtime_environment("production", base_url=DEMO_BASE_URL)["status"] == "BLOCK"
    assert validate_runtime_environment("demo", base_url=PROD_BASE_URL)["status"] == "BLOCK"


def test_broker_readonly_mock_snapshot_is_review_required(tmp_path) -> None:
    result = write_broker_readonly_artifacts_from_snapshot(
        trade_date="2026-06-29",
        root=tmp_path,
        snapshot={
            "environment": "demo",
            "source": "mock",
            "generated_at": "2026-06-29T00:00:00+00:00",
            "positions": [],
            "orders": [],
            "executions": [],
            "buying_power": {"buying_power": "1000000"},
            "account_summary": {"total_assets": "1000000"},
        },
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["mock_source_detected"] is True
    assert "broker_readonly_snapshot_source_mock" in result["blocked_reasons"]


def test_broker_orders_filled_fallback_writes_review_executions_and_safe_positions_diagnosis(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    trade_date = "2026-06-29"
    result = write_broker_readonly_artifacts_from_snapshot(
        trade_date=trade_date,
        root=tmp_path,
        snapshot={
            "environment": "demo",
            "source": "operations_broker_readonly_mainline",
            "generated_at": "2026-06-29T00:00:00+00:00",
            "health": {"orders": {"status": "PASS"}, "executions": {"status": "FAIL"}, "positions": {"status": "PASS"}},
            "positions": [
                {"issue_code": "", "code": "", "quantity": "0", "market_value": "0"},
                {"issue_code": "", "code": "", "quantity": "0", "market_value": "0"},
            ],
            "orders": [
                {
                    "issue_code": "6522",
                    "side": "3",
                    "quantity": "100",
                    "executed_quantity": "100",
                    "remaining_quantity": "0",
                    "price": "1960",
                    "status": "全部約定",
                    "order_datetime": "20260703082730",
                },
                {
                    "issue_code": "4265",
                    "side": "1",
                    "quantity": "100",
                    "executed_quantity": "100",
                    "remaining_quantity": "0",
                    "price": "395",
                    "status": "全部約定",
                    "order_datetime": "20260703082731",
                },
            ],
            "executions": [],
            "buying_power": {"buying_power": "1000000"},
            "account_summary": {"total_assets": "1000000"},
        },
    )

    orders = read_json(tmp_path / "broker_orders" / trade_date / "orders.json")["orders"]
    executions_artifact = read_json(tmp_path / "broker_executions" / trade_date / "executions.json")
    positions_artifact = read_json(tmp_path / "broker_positions" / trade_date / "positions.json")

    assert result["status"] == "PASS"
    assert orders[0]["issue_code"] == "6522"
    assert orders[0]["code"] == "6522"
    assert orders[0]["side"] == "BUY"
    assert orders[1]["side"] == "SELL"
    assert executions_artifact["classification"] == "ORDER_STATUS_FILLED_FALLBACK_REVIEW"
    assert executions_artifact["review_required"] is True
    assert executions_artifact["fallback_execution_count"] == 2
    assert executions_artifact["executions"][0]["source"] == "broker_orders_fallback"
    assert executions_artifact["executions"][0]["review_required"] is True
    assert executions_artifact["executions"][0]["raw_broker_order_id_saved"] is False
    assert positions_artifact["positions"] == []
    assert positions_artifact["positions_safe_diagnosis"]["positions_source_count"] == 2
    assert positions_artifact["positions_safe_diagnosis"]["positions_valid_count"] == 0
    assert positions_artifact["positions_safe_diagnosis"]["all_rows_empty_or_zero"] is True
    serialized = __import__("json").dumps(executions_artifact, ensure_ascii=False)
    assert "raw_response" not in serialized or '"raw_response_saved": false' in serialized
    assert "secret" not in serialized or '"secret_saved": false' in serialized


def test_reconcile_keeps_orders_fallback_review_required(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    trade_date = "2026-06-29"
    write_json(tmp_path / "market_refresh" / trade_date / "market_refresh_manifest.json", {"status": "PASS"})
    write_json(tmp_path / "feature_refresh" / trade_date / "feature_refresh_manifest.json", {"status": "PASS"})
    write_json(tmp_path / "daily_plan" / trade_date / "daily_plan_result.json", {"status": "PASS"})
    write_json(tmp_path / "order_plan" / trade_date / "order_plan.json", {"status": "PASS"})
    write_json(tmp_path / "approval_artifact" / trade_date / "approval_artifact.json", {"status": "APPROVED"})
    write_json(tmp_path / "safety_result" / trade_date / "safety_result.json", {"status": "PASS"})
    write_json(tmp_path / "safety_monitor" / trade_date / "safety_monitor_result.json", {"status": "PASS", "safety_state": "ALLOW"})
    write_json(tmp_path / "fill_events" / trade_date / "fill_events.json", {"status": "PASS", "fill_events": [{"item_id": "buy_1", "lifecycle": "ACCEPTED"}]})
    write_json(
        tmp_path / "submitted_orders" / trade_date / "submitted_orders.json",
        {
            "status": "PASS",
            "submitted_orders": [
                {
                    "item_id": "buy_1",
                    "status": "ORDER_ACCEPTED",
                    "code_normalization": {"broker_issue_code": "6522"},
                }
            ],
        },
    )
    write_broker_readonly_artifacts_from_snapshot(
        trade_date=trade_date,
        root=tmp_path,
        snapshot={
            "environment": "demo",
            "source": "operations_broker_readonly_mainline",
            "generated_at": "2026-06-29T00:00:00+00:00",
            "health": {"orders": {"status": "PASS"}, "executions": {"status": "FAIL"}},
            "positions": [],
            "orders": [{"issue_code": "6522", "side": "3", "quantity": "100", "executed_quantity": "100", "remaining_quantity": "0", "status": "全部約定"}],
            "executions": [],
            "buying_power": {"buying_power": "1000000"},
            "account_summary": {"total_assets": "1000000"},
        },
    )
    write_json(tmp_path / "ledger" / trade_date / "ledger_state.json", {"status": "PASS"})
    write_json(tmp_path / "ledger" / trade_date / "ledger_summary.json", {"status": "PASS"})
    write_json(tmp_path / "ledger" / trade_date / "ledger_update_manifest.json", {"status": "PASS"})

    result = run_reconcile(trade_date=trade_date, root=tmp_path)

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["submit_reconciliation"]["order_status_filled_fallback_review"] is True
    assert result["submit_reconciliation"]["broker_orders_used_as_execution_fallback"] is True
    assert result["submit_reconciliation"]["fallback_execution_count"] == 1


def test_notification_dry_run_is_not_delivery_confirmation(tmp_path) -> None:
    result = run_operation_notifications(
        trade_date="2026-06-29",
        root=tmp_path,
        report_refs={"paths": {"public_report": "reports/public_report.md"}, "notification_summary_text": "summary"},
        dry_run=True,
        env={
            "AIFUNDLAB_LINE_CHANNEL_ACCESS_TOKEN": "line-token",
            "AIFUNDLAB_LINE_TO_ID": "line-to",
            "AIFUNDLAB_DISCORD_WEBHOOK_URL": "https://example.invalid/webhook",
        },
    )

    assert result["status"] == "PASS"
    assert result["line_send_attempted"] is True
    assert result["line_send_executed"] is False
    assert result["discord_send_attempted"] is True
    assert result["discord_send_executed"] is False
    assert result["delivery_confirmation"] is False
    assert "HTTP request" in result["send_success_semantics"]
