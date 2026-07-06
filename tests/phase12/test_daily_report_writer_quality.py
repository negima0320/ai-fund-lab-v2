from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.operations.io import OperationPaths, write_json
from ai_fund_lab_v2.operations.operations import _phase9_v4_payload_from_operations_model, _render_public_holdings_section, run_daily_report


TRADE_DATE = "2026-06-30"


def _write_minimal_operation_artifacts(root: Path) -> None:
    paths = OperationPaths(root)
    feature_dir = root / "feature_artifacts" / TRADE_DATE
    feature_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for idx in range(1, 51):
        code = "42650" if idx == 1 else f"{40000 + idx}0"
        rows.append(
            {
                "code": code,
                "universe_eligible": True,
                "price_momentum_return_5d": 0.20 - idx * 0.001,
                "price_momentum_return_20d": 0.50 - idx * 0.002,
                "volume_momentum_ratio_5d": 1.8 - idx * 0.01,
                "trend_close_over_ma_20d": 0.12 - idx * 0.001,
                "liquidity_avg_volume_20d": 100000 + idx,
                "volatility_return_std_20d": 0.02,
            }
        )
    pd.DataFrame(rows).to_parquet(feature_dir / "candidate_features.parquet")
    listed_path = root / "feature_refresh" / TRADE_DATE / "jquants" / "listed_issues" / "listed_info_for_feature.parquet"
    listed_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [{"Code": row["code"], "CoName": "Institution for a Global Society" if row["code"] == "42650" else f"候補{idx}", "MktNm": "グロース"} for idx, row in enumerate(rows, 1)]
    ).to_parquet(listed_path)
    write_json(
        paths.dated("market_refresh", TRADE_DATE, "market_refresh_manifest.json"),
        {
            "status": "PASS",
            "business_date": TRADE_DATE,
            "feature_freshness_status": "FEATURE_READY",
            "latest_available_market_date": TRADE_DATE,
        },
    )
    write_json(
        paths.dated("feature_refresh", TRADE_DATE, "feature_refresh_manifest.json"),
        {
            "status": "PASS",
            "business_date": TRADE_DATE,
            "candidate_feature_path": str(feature_dir / "candidate_features.parquet"),
        },
    )
    write_json(
        paths.dated("daily_plan", TRADE_DATE, "daily_plan_result.json"),
        {"status": "PASS", "business_date": TRADE_DATE, "buy_item_count": 1, "sell_item_count": 1},
    )
    write_json(
        paths.dated("order_plan", TRADE_DATE, "order_plan.json"),
        {
            "artifact_type": "order_plan",
            "status": "PASS",
            "business_date": TRADE_DATE,
            "buy_item_count": 1,
            "sell_item_count": 1,
            "feature_candidate_audit": {"candidate_count": 50, "candidate_feature_path": str(feature_dir / "candidate_features.parquet")},
            "items": [
                {
                    "item_id": "buy_1",
                    "side": "BUY",
                    "issue_code": "42650",
                    "code": "42650",
                    "quantity": "100",
                    "limit_price": "430",
                    "expected_notional": "43000",
                },
                {
                    "item_id": "sell_1",
                    "side": "SELL",
                    "issue_code": "72030",
                    "code": "72030",
                    "quantity": "100",
                    "limit_price": "1200",
                    "expected_notional": "120000",
                    "sell_reason": "trend_break",
                    "exit_source": "position_management_ai",
                },
            ],
        },
    )
    write_json(
        paths.dated("submitted_orders", TRADE_DATE, "submitted_orders.json"),
        {
            "artifact_type": "demo_submit",
            "business_date": TRADE_DATE,
            "status": "PASS",
            "submitted_orders": [
                {
                    "item_id": "buy_1",
                    "status": "ACCEPTED",
                    "broker_issue_code": "4265",
                    "normalized_limit_price": "430",
                    "normalized_expected_notional": "43000",
                }
            ],
        },
    )
    write_json(paths.dated("fill_events", TRADE_DATE, "fill_events.json"), {"status": "PASS", "fill_events": [{"item_id": "buy_1", "side": "BUY", "lifecycle": "FILLED"}]})
    write_json(paths.dated("safety_monitor", TRADE_DATE, "safety_monitor_result.json"), {"status": "PASS", "safety_state": "ALLOW", "system_faults": []})
    write_json(paths.dated("reconciliation_result", TRADE_DATE, "reconciliation_result.json"), {"status": "PASS", "classification": "PASS", "missing": []})
    write_json(paths.dir("audit_result") / "audit_result.json", {"status": "PASS", "leakage_audit": {"status": "PASS"}, "no_production_order_audit": True, "demo_production_parity_audit": {"status": "PASS", "unexpected_differences": []}})
    write_json(paths.dated("broker_buying_power", TRADE_DATE, "buying_power.json"), {"buying_power": "20000000", "cash_available": "20000000", "raw_response_saved": False, "secret_saved": False})
    write_json(
        paths.dated("broker_orders", TRADE_DATE, "orders.json"),
        {
            "orders": [
                {
                    "issue_code": "4265",
                    "side": "3",
                    "quantity": "100",
                    "executed_quantity": "100",
                    "remaining_quantity": "0",
                    "price": "430",
                    "status": "全部約定",
                    "raw_response_saved": False,
                    "secret_saved": False,
                }
            ],
            "raw_response_saved": False,
            "secret_saved": False,
        },
    )
    write_json(paths.dated("broker_positions", TRADE_DATE, "positions.json"), {"positions": [], "raw_response_saved": False, "secret_saved": False})
    write_json(
        paths.dated("broker_executions", TRADE_DATE, "executions.json"),
        {
            "executions": [
                {
                    "issue_code": "4265",
                    "side": "BUY",
                    "quantity": "100",
                    "price": "430",
                    "raw_response_saved": False,
                    "secret_saved": False,
                }
            ],
            "raw_response_saved": False,
            "secret_saved": False,
        },
    )
    write_json(
        paths.dated("ledger", TRADE_DATE, "ledger_summary.json"),
        {"status": "PASS", "buying_power_available": True, "positions_count": 0, "market_value_estimate": "0", "total_equity_estimate": "20000000"},
    )
    write_json(
        paths.dated("ledger", TRADE_DATE, "ledger_state.json"),
        {
            "orders_summary": {"count": 1},
            "executions_summary": {"count": 0},
            "positions_summary": {"count": 0, "market_value_estimate": "0"},
            "cash_or_buying_power_summary": {"buying_power": "20000000", "cash_available": "20000000"},
            "market_value_estimate": "0",
            "total_equity_estimate": "20000000",
        },
    )


def test_daily_report_writer_outputs_human_markdown_and_payloads(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    _write_minimal_operation_artifacts(tmp_path)

    result = run_daily_report(trade_date=TRADE_DATE, root=tmp_path)
    report_dir = tmp_path / "reports" / TRADE_DATE
    blog = (report_dir / "blog_draft.md").read_text(encoding="utf-8")
    public = (report_dir / "public_report.md").read_text(encoding="utf-8")
    line_payload = json.loads((report_dir / "line_payload.json").read_text(encoding="utf-8"))
    discord_payload = json.loads((report_dir / "discord_payload.json").read_text(encoding="utf-8"))

    assert result["daily_report_refs_path"]
    for text in (blog, public):
        assert "## Candidate Top50" in text
        assert "## 翌営業日の購入予定候補 Top5" in text
        assert "## なぜこの5銘柄が購入候補なのか" in text
        assert "### 4265 Institution for a Global Society" in text
        assert "公開用AI信頼度" in text
        assert "## AIの総括" in text
        assert "## Demo運用状況" in text
        assert "| Side |" not in text
        assert "{'" not in text
        assert "statuses: {" not in text
        assert "sell_summary:" not in text
        assert "Demo Special Fill Simulation: {" not in text
        assert "選定理由: -" not in text
        assert "確認中" not in text
        assert "現金: 957,000円" in text
        assert "現金: 20,000,000円" not in text
        assert "株式評価額: 43,000円" in text
        assert "現在資産: 1,000,000円" in text
        assert "損益: 未確定（Demo運用は100万円評価基準で開始。実現損益確定後に更新）" in text
        assert "実現損益: 0円" in text
        assert "含み損益: 0円" in text
        assert "現在保有中の銘柄はありません。" not in text
        assert "^4265" in text
    assert line_payload["summary_text"].startswith("AI Fund Lab Demo Operations Daily Report")
    assert "BUY候補Top5" in line_payload["summary_text"]
    assert any(section["heading"] == "BUY候補Top5" for section in line_payload["sections"])
    assert discord_payload["provider"] == "discord"
    assert line_payload["raw_response_saved"] is False
    assert discord_payload["secret_saved"] is False


def test_public_holdings_section_outputs_all_holdings_and_symbol_tags() -> None:
    holdings = [
        {"code": "5367", "name": "ニッカトー", "quantity": "100", "market_value_display": "167,800円", "unrealized_pnl": "6900"},
        {"code": "6966", "name": "三井ハイテック", "quantity": "100", "market_value_display": "99,200円", "unrealized_pnl": "-20200"},
        {"code": "6336", "name": "石井表記", "quantity": "100", "market_value_display": "191,100円", "unrealized_pnl": "-8900"},
        {"code": "7245", "name": "大同メタル工業", "quantity": "100", "market_value_display": "169,100円", "unrealized_pnl": "19000"},
        {"code": "3237", "name": "イントランス", "quantity": "2100", "market_value_display": "193,200円", "unrealized_pnl": "6300"},
    ]

    section = _render_public_holdings_section(holdings)

    assert "1. 5367 ニッカトー / 100株 / 評価額 167,800円 / 損益 +6,900円" in section
    assert "2. 6966 三井ハイテック / 100株 / 評価額 99,200円 / 損益 -20,200円" in section
    assert "5. 3237 イントランス / 2,100株 / 評価額 193,200円 / 損益 +6,300円" in section
    for code in ("5367", "6966", "6336", "7245", "3237"):
        assert f"^{code}" in section


def test_phase9_payload_uses_fill_sot_not_submitted_orders_for_bought_section() -> None:
    dry_run_row = {
        "side": "BUY",
        "status": "DRY_RUN_READY",
        "fill_status": "NOT_FILLED",
        "internal_code": "42650",
        "broker_issue_code": "4265",
        "name": "Institution for a Global Society",
        "quantity": "100",
        "limit_price": "430",
        "expected_notional": "43000",
        "candidate_rank": 1,
        "public_confidence_score": 100,
    }
    filled_row = {**dry_run_row, "status": "ACCEPTED", "fill_status": "FILLED"}
    base_model = {
        "business_date": TRADE_DATE,
        "environment": "demo",
        "broker": {"orders_count": 1, "positions_count": 0},
        "ledger": {"buying_power": "20000000", "cash_available": "20000000", "market_value_estimate": "0"},
        "positions": [],
        "sell_rows": [],
        "candidate_top50": [],
    }

    dry_payload = _phase9_v4_payload_from_operations_model({**base_model, "buy_rows": [dry_run_row]})
    filled_payload = _phase9_v4_payload_from_operations_model({**base_model, "buy_rows": [filled_row]})

    assert dry_payload["bought"] == []
    assert dry_payload["purchase_reason_details"] == []
    assert filled_payload["bought"][0]["code"] == "4265"
    assert filled_payload["purchase_reason_details"][0]["code"] == "4265"
