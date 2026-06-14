from __future__ import annotations

import pandas as pd

from ai_fund_lab_v2.capital_allocation_ai.phase7b_validation import ValidationConfig, simulate_policy


def make_frame() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2025-01-01", periods=25, freq="B").strftime("%Y-%m-%d").tolist()
    for index, date in enumerate(dates):
        top_codes = ["1001", "1002", "1003"] if index == 0 else ["2001", "2002", "2003"]
        for rank, code in enumerate(top_codes, start=1):
            rows.append(
                {
                    "target_date": date,
                    "year": 2025,
                    "code": code,
                    "buy_rank": rank,
                    "expected_edge_score": 0.20 - rank * 0.01,
                    "split": "test",
                    "label__future_return_20d": 0.10,
                    "label__future_max_return_20d": 0.14,
                    "label__future_max_drawdown_20d": -0.05,
                    "label__downside_bad_20d": False,
                }
            )
        for rank, code in enumerate(["1001", "1002", "1003"], start=30):
            if index == 0:
                continue
            rows.append(
                {
                    "target_date": date,
                    "year": 2025,
                    "code": code,
                    "buy_rank": rank,
                    "expected_edge_score": 0.01,
                    "split": "test",
                    "label__future_return_20d": 0.10,
                    "label__future_max_return_20d": 0.14,
                    "label__future_max_drawdown_20d": -0.05,
                    "label__downside_bad_20d": False,
                }
            )
    return pd.DataFrame(rows)


def test_conservative_replacement_turnover_is_below_daily_sync() -> None:
    frame = make_frame()
    conservative = ValidationConfig(policy_id="B", policy_name="B", minimum_holding_days=5, confirmation_days=2)
    sync = ValidationConfig(
        policy_id="E",
        policy_name="E",
        minimum_holding_days=1,
        replacement_rank_degradation_threshold=3,
        replacement_edge_margin=-999.0,
        confirmation_days=1,
        daily_top3_sync=True,
    )

    conservative_result = simulate_policy(frame, conservative)["metrics"]
    sync_result = simulate_policy(frame, sync)["metrics"]

    assert sync_result["replacement_count"] > conservative_result["replacement_count"]
    assert conservative_result["replacement_requires_sell_fill_before_buy"] is True
    assert conservative_result["replacement_same_time_live_execution_enabled"] is False
    assert conservative_result["broker_api_executed"] is False


def test_emergency_exit_records_no_order_execution() -> None:
    frame = make_frame()
    frame.loc[frame["code"] == "1001", "label__future_max_drawdown_20d"] = -0.20
    config = ValidationConfig(policy_id="C", policy_name="C", emergency_exit_pct=-0.10)

    metrics = simulate_policy(frame, config)["metrics"]

    assert metrics["emergency_exit_count"] >= 1
    assert metrics["order_executed"] is False
    assert metrics["paper_trading_executed"] is False
    assert metrics["tachibana_api_called"] is False
