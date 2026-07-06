from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.operations.io import OperationPaths, write_json
from ai_fund_lab_v2.operations.operations import run_daily_report


def test_incomplete_operation_day_does_not_render_normal_candidate_sections(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    paths = OperationPaths(tmp_path)
    trade_date = "2026-07-01"
    write_json(paths.dated("market_refresh", trade_date, "market_refresh_manifest.json"), {"business_date": trade_date, "status": "PASS"})
    write_json(paths.dated("daily_plan", trade_date, "daily_plan_result.json"), {"business_date": trade_date, "status": "SKIPPED_MARKET_CLOSED"})
    write_json(paths.dated("fill_events", trade_date, "fill_events.json"), {"business_date": trade_date, "status": "PASS", "fill_events": []})
    write_json(paths.dated("safety_monitor", trade_date, "safety_monitor_result.json"), {"business_date": trade_date, "status": "PASS", "safety_state": "ALLOW"})
    write_json(paths.dated("reconciliation_result", trade_date, "reconciliation_result.json"), {"business_date": trade_date, "status": "PASS", "classification": "PASS"})

    run_daily_report(trade_date=trade_date, root=tmp_path)

    public = (tmp_path / "reports" / trade_date / "public_report.md").read_text(encoding="utf-8")
    payload = json.loads((tmp_path / "reports" / trade_date / "line_payload.json").read_text(encoding="utf-8"))
    refs = json.loads((tmp_path / "daily_report_refs" / trade_date / "daily_report_refs.json").read_text(encoding="utf-8"))
    assert refs["operation_day_type"] == "INCOMPLETE_OPERATION_DAY"
    assert "## Candidate Top50" not in public
    assert "## 翌営業日の購入予定候補 Top5" not in public
    assert "通常運用が完了していません" in public
    assert payload["operation_day_type"] == "INCOMPLETE_OPERATION_DAY"
    assert payload["buy_candidates"] == []


def test_review_report_separates_today_submitted_orders_from_next_order_plan(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    paths = OperationPaths(tmp_path)
    trade_date = "2026-07-03"
    submitted_items = [
        ("buy_2026-07-02_65220_001", "65220", "6522"),
        ("buy_2026-07-02_78780_002", "78780", "7878"),
        ("buy_2026-07-02_61660_004", "61660", "6166"),
        ("buy_2026-07-02_42650_006", "42650", "4265"),
        ("buy_2026-07-02_68970_008", "68970", "6897"),
    ]
    next_plan_items = [
        ("buy_2026-07-03_65220_001", "65220", "1950"),
        ("buy_2026-07-03_61660_004", "61660", "930"),
    ]
    write_json(paths.dated("market_refresh", trade_date, "market_refresh_manifest.json"), {"business_date": trade_date, "status": "PASS"})
    write_json(paths.dated("feature_refresh", trade_date, "feature_refresh_manifest.json"), {"business_date": trade_date, "status": "PASS"})
    write_json(paths.dated("daily_plan", trade_date, "daily_plan_result.json"), {"business_date": trade_date, "status": "PASS"})
    write_json(
        paths.dated("order_plan", trade_date, "order_plan.json"),
        {
            "business_date": trade_date,
            "status": "PASS",
            "buy_item_count": 2,
            "sell_item_count": 0,
            "items": [
                {
                    "item_id": item_id,
                    "issue_code": code,
                    "code": code,
                    "side": "BUY",
                    "quantity": "100",
                    "limit_price": price,
                    "expected_notional": str(int(price) * 100),
                }
                for item_id, code, price in next_plan_items
            ],
        },
    )
    write_json(paths.dated("approval_artifact", trade_date, "approval_artifact.json"), {"business_date": trade_date, "status": "APPROVED"})
    write_json(
        paths.dated("submitted_orders", trade_date, "submitted_orders.json"),
        {
            "business_date": trade_date,
            "created_at": "2026-07-03T08:50:00+09:00",
            "status": "PASS",
            "accepted_order_count": 5,
            "order_plan_source_date": "2026-07-02",
            "approval_source_date": "2026-07-02",
            "submitted_orders": [
                {
                    "item_id": item_id,
                    "issue_code": code,
                    "code": code,
                    "side": "BUY",
                    "quantity": "100",
                    "limit_price": "1000",
                    "expected_notional": "100000",
                    "status": "ORDER_ACCEPTED",
                    "code_normalization": {"broker_issue_code": broker_code},
                }
                for item_id, code, broker_code in submitted_items
            ],
        },
    )
    write_json(
        paths.dated("fill_events", trade_date, "fill_events.json"),
        {
            "business_date": trade_date,
            "status": "PASS",
            "classification": "AVAILABLE",
            "broker_orders_count": 5,
            "broker_executions_count": 0,
            "fill_events": [{"item_id": item_id, "side": "BUY", "lifecycle": "ACCEPTED"} for item_id, _, _ in submitted_items],
        },
    )
    write_json(paths.dated("safety_monitor", trade_date, "safety_monitor_result.json"), {"business_date": trade_date, "status": "PASS", "safety_state": "ALLOW", "system_faults": []})
    write_json(paths.dated("reconciliation_result", trade_date, "reconciliation_result.json"), {"business_date": trade_date, "status": "REVIEW_REQUIRED", "classification": "REVIEW_REQUIRED", "missing": []})
    write_json(paths.dir("audit_result") / "audit_result.json", {"status": "REVIEW_REQUIRED", "leakage_audit": {"status": "PASS"}, "no_production_order_audit": True, "demo_production_parity_audit": {"status": "PASS", "unexpected_differences": []}})
    write_json(paths.dated("broker_orders", trade_date, "orders.json"), {"orders": [{"issue_code": broker_code, "side": "3", "quantity": "100", "executed_quantity": "100", "remaining_quantity": "0", "price": "1000", "status": "全部約定"} for _, _, broker_code in submitted_items]})
    write_json(paths.dated("broker_executions", trade_date, "executions.json"), {"executions": [], "classification": "AVAILABLE"})
    write_json(paths.dated("broker_positions", trade_date, "positions.json"), {"positions": []})
    write_json(paths.dated("broker_buying_power", trade_date, "buying_power.json"), {"buying_power": "1000000", "raw_response_saved": False, "secret_saved": False})

    run_daily_report(trade_date=trade_date, root=tmp_path)

    public = (tmp_path / "reports" / trade_date / "public_report.md").read_text(encoding="utf-8")
    line_payload = json.loads((tmp_path / "reports" / trade_date / "line_payload.json").read_text(encoding="utf-8"))
    discord_payload = json.loads((tmp_path / "reports" / trade_date / "discord_payload.json").read_text(encoding="utf-8"))
    refs = json.loads((tmp_path / "daily_report_refs" / trade_date / "daily_report_refs.json").read_text(encoding="utf-8"))

    assert "Brokerへ送信済みの注文は5件です。" in public
    assert "Source of Truth: submitted_orders/2026-07-03/submitted_orders.json" in public
    assert "次回用Order Planの候補は2件です。これは本日Submit結果ではありません。" in public
    assert "## Broker確認" in public
    assert "- Broker Orders: 5件" in public
    assert "- Broker Executions: 0件" in public
    assert "- Broker Positions: 0件" in public
    assert "Broker Executions API由来の確定約定は未確認です" in public
    assert "現在保有は確定扱いにしません" in public
    assert refs["submitted_order_count"] == 5
    assert refs["next_order_plan_count"] == 2
    assert refs["report_sot_policy"]["order_plan_used_as_today_submit_result"] is False
    for payload in (line_payload, discord_payload):
        assert payload["submitted_order_count"] == 5
        assert payload["next_order_plan_count"] == 2
        assert "submitted_count=5" in payload["summary_text"]
        assert "next_candidate_count=2" in payload["summary_text"]
