from __future__ import annotations

from datetime import date, timedelta

from ai_fund_lab_v2.operations.broker_readonly import write_broker_readonly_artifacts_from_snapshot
from ai_fund_lab_v2.operations.io import read_json
from ai_fund_lab_v2.operations.ledger import write_operations_ledger_from_broker_readonly
from ai_fund_lab_v2.operations.operations import run_daily_plan, run_market_refresh, run_reconcile


TRADE_DATE = "2026-06-29"
LATEST_AVAILABLE = "2026-06-26"


class LatestAvailableFetcher:
    def fetch_daily_quotes(self, *, from_date: str, to_date: str):
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(LATEST_AVAILABLE)
        rows = []
        current = start
        price = 1000
        while current <= end:
            if current.weekday() < 5:
                rows.append({"Date": current.isoformat(), "Code": "72030", "O": price, "H": price + 5, "L": price - 5, "C": price + 3, "Vo": 100000})
                price += 2
            current += timedelta(days=1)
        return rows

    def fetch_listed_info(self, *, date: str):
        return [{"Date": date, "Code": "72030", "CoName": "Toyota", "ProdCat": "011", "MktNm": "プライム"}]

    def fetch_trading_calendar(self, *, from_date: str, to_date: str):
        rows = []
        current = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
        while current <= end:
            rows.append({"Date": current.isoformat(), "HolDiv": "1" if current.weekday() < 5 else "0"})
            current += timedelta(days=1)
        return rows


def test_market_refresh_uses_latest_available_market_date_for_features(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")

    result = run_market_refresh(
        trade_date=TRADE_DATE,
        root=tmp_path,
        allow_api_fetch=True,
        from_date="2026-05-01",
        fetch_mode="range",
        fetcher=LatestAvailableFetcher(),
    )
    marker = read_json(tmp_path / "feature_refresh" / TRADE_DATE / "latest_features.json")

    assert result["status"] == "PASS"
    assert result["latest_available_market_date"] == LATEST_AVAILABLE
    assert marker["data_until"] == LATEST_AVAILABLE
    assert marker["feature_freshness_status"] == "FEATURE_READY"
    assert marker["candidate_feature_path"]


def test_daily_plan_records_buy_zero_reason_when_feature_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_market_refresh(trade_date=TRADE_DATE, root=tmp_path)

    result = run_daily_plan(trade_date=TRADE_DATE, root=tmp_path)
    plan = read_json(tmp_path / "order_plan" / TRADE_DATE / "order_plan.json")

    assert result["status"] == "PASS"
    assert plan["buy_item_count"] == 0
    assert plan["feature_buy_adapter"]["status"] == "NO_FEATURE_ARTIFACT"
    assert plan["feature_buy_adapter"]["reason"] == "candidate_feature_path_missing"


def test_operations_ledger_is_written_for_empty_broker_state_and_reconcile_reads_it(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    write_broker_readonly_artifacts_from_snapshot(
        trade_date=TRADE_DATE,
        root=tmp_path,
        snapshot={
            "environment": "demo",
            "account_summary": {"total_assets": "20000000", "buying_power": "20000000"},
            "buying_power": {"buying_power": "20000000", "cash_available": "20000000"},
            "positions": [],
            "orders": [],
            "executions": [],
        },
    )

    ledger = write_operations_ledger_from_broker_readonly(trade_date=TRADE_DATE, root=tmp_path)
    reconcile = run_reconcile(trade_date=TRADE_DATE, root=tmp_path)
    state = read_json(tmp_path / "ledger" / TRADE_DATE / "ledger_state.json")

    assert ledger["status"] == "PASS"
    assert ledger["empty_broker_state_handled"] is True
    assert state["positions_summary"]["empty_classification"] == "NO_POSITIONS"
    assert state["orders_summary"]["empty_classification"] == "NO_ORDERS"
    assert state["executions_summary"]["empty_classification"] == "SKIPPED_NO_ORDERS"
    assert reconcile["targets"]["ledger"] is True
    assert reconcile["targets"]["ledger_state"] is True
    assert reconcile["ledger_state"]["empty_broker_state"] is True
    assert state["raw_response_saved"] is False
    assert state["secret_saved"] is False
