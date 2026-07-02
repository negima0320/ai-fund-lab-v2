from __future__ import annotations

from datetime import date, timedelta

from ai_fund_lab_v2.operations.io import read_json, write_json
from ai_fund_lab_v2.operations.operations import run_daily_plan, run_daily_report, run_market_refresh


TRADE_DATE = "2026-06-29"


class CandidateAuditFetcher:
    def fetch_daily_quotes(self, *, from_date: str, to_date: str):
        start = date.fromisoformat(from_date)
        end = date.fromisoformat("2026-06-26")
        rows = []
        current = start
        price = 1000
        while current <= end:
            if current.weekday() < 5:
                rows.append({"Date": current.isoformat(), "Code": "72030", "O": price, "H": price + 5, "L": price - 5, "C": price + 2, "Vo": 100000})
                price += 1
            current += timedelta(days=1)
        return rows

    def fetch_listed_info(self, *, date: str):
        return [{"Date": date, "Code": "72030", "CoName": "Toyota", "ProdCat": "011", "MktNm": "プライム"}]

    def fetch_trading_calendar(self, *, from_date: str, to_date: str):
        current = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
        rows = []
        while current <= end:
            rows.append({"Date": current.isoformat(), "HolDiv": "1" if current.weekday() < 5 else "0"})
            current += timedelta(days=1)
        return rows


def test_daily_report_ignores_stale_submit_status(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_market_refresh(trade_date=TRADE_DATE, root=tmp_path)
    stale_submit_path = tmp_path / "submitted_orders" / TRADE_DATE / "submitted_orders.json"
    write_json(
        stale_submit_path,
        {
            "artifact_type": "demo_submit",
            "business_date": TRADE_DATE,
            "created_at": "2026-06-29T00:00:00+00:00",
            "status": "BLOCK",
            "submitted_orders": [],
            "demo_order_submitted": False,
            "production_order_submitted": False,
        },
    )
    run_daily_plan(trade_date=TRADE_DATE, root=tmp_path)

    result = run_daily_report(trade_date=TRADE_DATE, root=tmp_path)
    refs = read_json(tmp_path / "daily_report_refs" / TRADE_DATE / "daily_report_refs.json")
    manifest = read_json(tmp_path / "daily_manifest" / TRADE_DATE / "daily_manifest.json")

    assert result["status"] == "PASS"
    assert refs["current_operation_statuses"]["submit"] == "STALE_IGNORED"
    assert refs["stale_artifact_policy"]["submit_status_stale_ignored"] is True
    assert manifest["submit_status"] == "STALE_IGNORED"


def test_candidate_path_audit_records_counts_and_zero_reason(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_market_refresh(
        trade_date=TRADE_DATE,
        root=tmp_path,
        allow_api_fetch=True,
        from_date="2026-05-01",
        fetch_mode="range",
        fetcher=CandidateAuditFetcher(),
    )

    run_daily_plan(trade_date=TRADE_DATE, root=tmp_path)
    audit = read_json(tmp_path / "feature_candidate_audit" / TRADE_DATE / "feature_candidate_audit.json")
    plan = read_json(tmp_path / "order_plan" / TRADE_DATE / "order_plan.json")

    assert audit["feature_path_audited"] is True
    assert audit["candidate_path_audited"] is True
    assert audit["jquants_raw_rows"] > 0
    assert audit["normalized_rows"] > 0
    assert audit["feature_rows"] == audit["universe_rows_before_gate"]
    assert audit["opportunity_count"] >= audit["candidate_count"]
    assert plan["feature_buy_adapter"]["reason"] in {"candidate_no_universe_eligible_rows", ""}
