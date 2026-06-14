from __future__ import annotations

import pandas as pd

from ai_fund_lab_v2.capital_allocation_ai.phase7d_execution_constraints_validation import (
    ExecutionConfig,
    build_leakage_audit,
    simulate_policy,
)


def make_ranked() -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=30, freq="B").strftime("%Y-%m-%d").tolist()
    rows = []
    for i, date in enumerate(dates):
        top = ["1001", "1002", "1003"] if i == 0 else ["2001", "2002", "2003"]
        for rank, code in enumerate(top, start=1):
            rows.append({"target_date": date, "code": code, "buy_rank": rank, "expected_edge_score": 0.2 - rank * 0.01})
        if i > 0:
            rows.append({"target_date": date, "code": "1001", "buy_rank": 51, "expected_edge_score": -1.0})
    return pd.DataFrame(rows)


def make_prices(price: float = 100.0) -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=35, freq="B").strftime("%Y-%m-%d").tolist()
    rows = []
    for i, date in enumerate(dates):
        for code in ["1001", "1002", "1003", "2001", "2002", "2003"]:
            rows.append({"target_date": date, "code": code, "close": price + i, "year": 2025})
    return pd.DataFrame(rows)


def test_lot_size_blocks_high_price_position() -> None:
    result = simulate_policy(
        make_ranked(),
        make_prices(price=10_000.0),
        ExecutionConfig("T", "T", "C3", minimum_holding_days=10, initial_assets=1_000_000, max_position_weight=0.1),
    )

    assert result["metrics"]["skipped_due_to_lot_size_count"] > 0
    assert result["metrics"]["jquants_api_called"] is False


def test_transaction_and_slippage_costs_are_recorded() -> None:
    result = simulate_policy(
        make_ranked(),
        make_prices(),
        ExecutionConfig("T", "T", "C3", minimum_holding_days=10, transaction_cost_bps=10, slippage_bps=10),
    )

    assert result["metrics"]["transaction_cost_paid"] > 0
    assert result["metrics"]["slippage_cost_paid"] > 0
    assert result["metrics"]["live_order_executed"] is False


def test_leakage_audit_passes() -> None:
    audit = build_leakage_audit(make_ranked(), make_prices(), "2026-01-01T00:00:00+00:00")

    assert audit["status"] == "PASS"
    assert audit["no_future_data_in_decision"] is True
    assert audit["backtest_outcome_used_in_decision"] is False
    assert audit["future_price_used_in_decision"] is False
    assert audit["future_rank_used_in_decision"] is False
    assert audit["decision_evaluation_separated"] is True
