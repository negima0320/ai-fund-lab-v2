from __future__ import annotations

import pandas as pd

from ai_fund_lab_v2.capital_allocation_ai.phase7c_daily_path_validation import (
    DailyPathConfig,
    build_leakage_audit,
    simulate_daily_path_policy,
)


def make_ranked() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2025-01-01", periods=25, freq="B").strftime("%Y-%m-%d").tolist()
    for i, date in enumerate(dates):
        top = ["1001", "1002", "1003"] if i == 0 else ["2001", "2002", "2003"]
        for rank, code in enumerate(top, start=1):
            rows.append({"target_date": date, "code": code, "buy_rank": rank, "expected_edge_score": 0.20 - rank * 0.01})
        if i > 0:
            rows.append({"target_date": date, "code": "1001", "buy_rank": 51, "expected_edge_score": -1.0})
    return pd.DataFrame(rows)


def make_prices() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2025-01-01", periods=30, freq="B").strftime("%Y-%m-%d").tolist()
    for i, date in enumerate(dates):
        for code in ["1001", "1002", "1003", "2001", "2002", "2003"]:
            rows.append({"target_date": date, "code": code, "close": 100.0 + i, "year": 2025})
    return pd.DataFrame(rows)


def test_daily_sync_sell_first_has_no_live_execution_and_records_replacements() -> None:
    ranked = make_ranked()
    prices = make_prices()
    config = DailyPathConfig(
        policy_id="E",
        policy_name="E",
        policy_family="E_DAILY_SYNC",
        replacement_timing="SELL_FIRST_BUY_AFTER_FILL",
        minimum_holding_days=1,
        replacement_rank_threshold=3,
        confirmation_days=1,
        replacement_edge_margin=-999.0,
        daily_top3_sync=True,
    )

    result = simulate_daily_path_policy(ranked, prices, config)
    metrics = result["metrics"]

    assert metrics["replacement_count"] >= 1
    assert metrics["live_order_executed"] is False
    assert metrics["jquants_api_called"] is False
    assert metrics["no_future_data_in_decision"] is True


def test_emergency_exit_uses_daily_close_path() -> None:
    ranked = make_ranked()
    prices = make_prices()
    prices.loc[(prices["code"] == "1001") & (prices["target_date"] == "2025-01-03"), "close"] = 85.0
    config = DailyPathConfig(
        policy_id="C1",
        policy_name="C1",
        policy_family="C1_EMERGENCY",
        emergency_exit_pct=-0.10,
    )

    result = simulate_daily_path_policy(ranked, prices, config)

    assert result["metrics"]["emergency_exit_count"] >= 1
    assert "EMERGENCY_EXIT" in set(result["trades"]["exit_reason"])


def test_leakage_audit_flags_pass() -> None:
    audit = build_leakage_audit(make_ranked(), make_prices(), "2026-01-01T00:00:00+00:00")

    assert audit["status"] == "PASS"
    assert audit["no_future_data_in_decision"] is True
    assert audit["backtest_outcome_used_in_decision"] is False
    assert audit["future_price_used_in_decision"] is False
    assert audit["future_rank_used_in_decision"] is False
    assert audit["decision_evaluation_separated"] is True
