from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from ai_fund_lab_v2.operations.broker_readonly import write_broker_readonly_artifacts_from_snapshot
from ai_fund_lab_v2.operations.io import read_json
from ai_fund_lab_v2.operations.operations import (
    run_daily_plan,
    run_fill_monitor,
    run_market_refresh,
    run_preflight,
    run_reconcile,
    run_safety_monitor,
)


TRADE_DATE = "2026-06-29"


class FakeJQuantsFetcher:
    def fetch_daily_quotes(self, *, from_date: str, to_date: str):
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
        rows = []
        current = start
        price = 1000
        while current <= end:
            if current.weekday() < 5:
                day = current.isoformat()
                rows.append(
                    {
                        "Date": day,
                        "Code": "72030",
                        "O": price,
                        "H": price + 10,
                        "L": price - 10,
                        "C": price + 5,
                        "Vo": 100000 + price,
                    }
                )
                price += 1
            current += timedelta(days=1)
        return rows

    def fetch_listed_info(self, *, date: str):
        return [{"Date": date, "Code": "72030", "CoName": "Toyota", "ProdCat": "011", "MktNm": "プライム"}]

    def fetch_trading_calendar(self, *, from_date: str, to_date: str):
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
        rows = []
        current = start
        while current <= end:
            rows.append({"Date": current.isoformat(), "HolDiv": "1" if current.weekday() < 5 else "0"})
            current += timedelta(days=1)
        return rows


def test_operations_market_refresh_can_execute_jquants_refresh_with_isolated_root(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")

    result = run_market_refresh(
        trade_date=TRADE_DATE,
        root=tmp_path,
        allow_api_fetch=True,
        from_date="2026-05-01",
        fetch_mode="range",
        fetcher=FakeJQuantsFetcher(),
    )
    market = read_json(tmp_path / "market_refresh" / TRADE_DATE / "market_refresh_manifest.json")
    feature = read_json(tmp_path / "feature_refresh" / TRADE_DATE / "latest_features.json")

    assert result["status"] == "PASS"
    assert market["jquants_api_fetch_executed"] is True
    assert market["raw_daily_quotes_updated"] is True
    assert market["canonical_normalized_updated"] is True
    assert market["feature_refresh_executed"] is True
    assert feature["broker_snapshot_used_for_ai"] is False
    assert "paper_trading" not in market["market_data_refresh_detail"]["manifest_path"]
    assert (tmp_path / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet").exists()


def test_broker_readonly_artifacts_are_redacted_and_feed_preflight_safety_fill_reconcile(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    write_broker_readonly_artifacts_from_snapshot(
        trade_date=TRADE_DATE,
        root=tmp_path,
        snapshot={
            "schema_version": "tachibana_broker_snapshot_v1",
            "environment": "demo",
            "generated_at": "2026-06-29T00:00:00+00:00",
            "account_summary": {"total_assets": "1000000", "buying_power": "500000"},
            "buying_power": {"buying_power": "500000", "cash_available": "500000"},
            "positions": [
                {
                    "issue_code": "7203",
                    "quantity": "100",
                    "average_price": "1200",
                    "market_price": "1000",
                    "market_value": "100000",
                }
            ],
            "orders": [],
            "executions": [],
            "health": {"orders": {"status": "PASS"}, "executions": {"status": "SKIPPED_NO_ORDERS"}},
            "redaction_status": {"raw_response_saved": False, "auth_identifier_saved": False},
        },
    )

    preflight = run_preflight(trade_date=TRADE_DATE, root=tmp_path, required_env=[])
    safety = run_safety_monitor(trade_date=TRADE_DATE, root=tmp_path)
    fill = run_fill_monitor(trade_date=TRADE_DATE, root=tmp_path)
    reconcile = run_reconcile(trade_date=TRADE_DATE, root=tmp_path)
    positions = read_json(tmp_path / "positions" / TRADE_DATE / "positions.json")
    orders = read_json(tmp_path / "broker_orders" / TRADE_DATE / "orders.json")

    assert preflight["status"] == "PASS"
    assert preflight["broker_snapshot_summary"]["positions_count"] == 1
    assert preflight["broker_snapshot_summary"]["buying_power"] == "500000"
    assert safety["broker_readonly_artifact_bundle"]["positions_count"] == 1
    assert safety["buying_power_available"] is True
    assert fill["classification"] == "SKIPPED_NO_ORDERS"
    assert reconcile["targets"]["broker_snapshot"] is True
    assert reconcile["targets"]["buying_power"] is True
    assert positions["positions"][0]["position_id"].startswith("position_")
    assert "order_id" not in str(orders)
    assert positions["positions"][0]["raw_response_saved"] is False
    assert positions["positions"][0]["secret_saved"] is False


def test_daily_plan_uses_feature_buy_candidates_and_broker_positions_for_sell(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    feature_root = tmp_path / "feature_artifacts" / TRADE_DATE
    feature_root.mkdir(parents=True)
    candidate_path = feature_root / "candidate_features.parquet"
    pd.DataFrame(
        [
            {
                "target_date": TRADE_DATE,
                "as_of_date": TRADE_DATE,
                "code": "67580",
                "universe_eligible": True,
                "price_momentum_return_20d": 0.2,
                "price_momentum_return_5d": 0.05,
                "liquidity_avg_volume_20d": 1000000,
            }
        ]
    ).to_parquet(candidate_path, index=False)
    write_broker_readonly_artifacts_from_snapshot(
        trade_date=TRADE_DATE,
        root=tmp_path,
        snapshot={
            "environment": "demo",
            "account_summary": {"total_assets": "1000000"},
            "buying_power": {"buying_power": "500000"},
            "positions": [{"issue_code": "7203", "quantity": "100", "average_price": "1200", "market_price": "1000", "market_value": "100000"}],
            "orders": [],
            "executions": [],
        },
    )
    run_market_refresh(trade_date=TRADE_DATE, root=tmp_path)
    marker = tmp_path / "feature_refresh" / TRADE_DATE / "latest_features.json"
    payload = read_json(marker)
    payload["candidate_feature_path"] = str(candidate_path)
    marker.write_text(__import__("json").dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_daily_plan(trade_date=TRADE_DATE, root=tmp_path)
    plan = read_json(tmp_path / "order_plan" / TRADE_DATE / "order_plan.json")

    assert result["status"] == "PASS"
    assert plan["buy_item_count"] == 1
    assert plan["sell_item_count"] == 1
    assert plan["feature_buy_adapter"]["status"] == "PASS"
    assert plan["exit_adapter"]["runtime_position_input_used"] is True
