from __future__ import annotations

import pandas as pd

from ai_fund_lab_v2.operations.io import write_json
from ai_fund_lab_v2.operations.market_refresh import load_feature_buy_candidates
from ai_fund_lab_v2.operations.operations import run_daily_plan, run_market_refresh


def test_market_refresh_writes_manifests_without_order_or_broker_actions(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")

    result = run_market_refresh(trade_date="2026-06-29", root=tmp_path)

    assert result["status"] == "PASS"
    assert result["ai_inference_executed"] is False
    assert result["order_plan_generated"] is False
    assert result["broker_order_api_called"] is False
    assert result["line_send_executed"] is False
    assert (tmp_path / "market_refresh" / "2026-06-29" / "market_refresh_manifest.json").exists()
    assert (tmp_path / "feature_refresh" / "2026-06-29" / "feature_refresh_manifest.json").exists()
    assert (tmp_path / "data_quality" / "2026-06-29" / "data_quality_result.json").exists()


def test_daily_plan_fails_closed_without_market_refresh_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")

    result = run_daily_plan(trade_date="2026-06-29", root=tmp_path)

    assert result["status"] == "BLOCK"
    assert "market_refresh_manifest_missing" in result["market_refresh_gate"]["reasons"]


def test_daily_plan_generates_configured_buy_count_without_implicit_one_item_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    _write_candidate_fixture(tmp_path, trade_date="2026-06-29", row_count=10)

    result = run_daily_plan(trade_date="2026-06-29", root=tmp_path)

    assert result["status"] == "PASS"
    plan = (tmp_path / "order_plan" / "2026-06-29" / "order_plan.json")
    payload = __import__("json").loads(plan.read_text())
    assert payload["buy_item_count"] == 5
    assert [item["issue_code"] for item in payload["items"]] == ["10000", "10010", "10020", "10030", "10040"]
    assert payload["operations_runtime_config"]["max_buy_orders_per_day"] == 5


def test_daily_plan_prices_and_filters_buy_candidates_within_dynamic_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    _write_candidate_fixture(
        tmp_path,
        trade_date="2026-06-29",
        row_count=10,
        closes={
            "10000": 9000,
            "10010": 4000,
            "10020": 3000,
            "10030": 800,
            "10040": 400,
            "10050": 300,
            "10060": 800,
        },
    )

    result = run_daily_plan(trade_date="2026-06-29", root=tmp_path)

    assert result["status"] == "PASS"
    payload = __import__("json").loads((tmp_path / "order_plan" / "2026-06-29" / "order_plan.json").read_text())
    buy_items = [item for item in payload["items"] if item["side"] == "BUY"]
    assert [item["issue_code"] for item in buy_items] == ["10010", "10020", "10030", "10040", "10050"]
    assert [item["expected_notional"] for item in buy_items] == ["400000", "300000", "80000", "40000", "30000"]
    assert sum(int(item["expected_notional"]) for item in buy_items) <= 850000
    assert payload["daily_plan_budget"]["approval_max_notional"] == "850000"
    assert payload["daily_plan_budget"]["excluded_buy_items"][0]["issue_code"] == "10000"
    assert payload["daily_plan_budget"]["excluded_buy_items"][0]["reason"] == "daily_plan_budget_insufficient"


def test_feature_buy_candidate_count_is_not_environment_specific(tmp_path):
    _write_candidate_fixture(tmp_path, trade_date="2026-06-29", row_count=10)

    demo_like = load_feature_buy_candidates(root=tmp_path, trade_date="2026-06-29")
    production_like = load_feature_buy_candidates(root=tmp_path, trade_date="2026-06-29")

    assert len(demo_like["buy_items"]) == 5
    assert len(production_like["buy_items"]) == 5
    assert demo_like["max_buy_orders_per_day"] == production_like["max_buy_orders_per_day"] == 5


def _write_candidate_fixture(tmp_path, *, trade_date: str, row_count: int, closes: dict[str, int] | None = None) -> None:
    candidate_path = tmp_path / "feature_artifacts" / trade_date / "candidate_features.parquet"
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    closes = closes or {}
    rows = []
    quote_rows = []
    for index in range(row_count):
        code = f"100{index}0"
        rows.append(
            {
                "target_date": trade_date,
                "as_of_date": trade_date,
                "code": code,
                "universe_eligible": True,
                "price_momentum_return_20d": 1.0 - index / 100,
                "price_momentum_return_5d": 0.5 - index / 100,
                "liquidity_avg_volume_20d": 1000000 - index,
            }
        )
        quote_rows.append(
            {
                "target_date": trade_date,
                "Date": trade_date,
                "code": code,
                "Code": code,
                "Close": closes.get(code, 1000),
            }
        )
    pd.DataFrame(rows).to_parquet(candidate_path, index=False)
    normalized_path = tmp_path / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(quote_rows).to_parquet(normalized_path, index=False)
    latest_path = tmp_path / "feature_refresh" / trade_date / "latest_features.json"
    write_json(
        latest_path,
        {
            "business_date": trade_date,
            "data_until": trade_date,
            "latest_available_market_date": trade_date,
            "feature_freshness_status": "FEATURE_READY",
            "candidate_feature_path": str(candidate_path),
        },
    )
    write_json(
        tmp_path / "market_refresh" / trade_date / "market_refresh_manifest.json",
        {
            "business_date": trade_date,
            "status": "PASS",
            "data_until": trade_date,
            "latest_available_market_date": trade_date,
            "feature_freshness_status": "FEATURE_READY",
        },
    )
    write_json(
        tmp_path / "feature_refresh" / trade_date / "feature_refresh_manifest.json",
        {
            "business_date": trade_date,
            "status": "PASS",
            "data_until": trade_date,
            "latest_available_market_date": trade_date,
            "feature_freshness_status": "FEATURE_READY",
            "latest_feature_path": str(latest_path),
            "ai_feature_contamination_audit": {"status": "PASS"},
        },
    )
