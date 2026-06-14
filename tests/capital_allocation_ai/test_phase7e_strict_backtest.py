from __future__ import annotations

import pandas as pd

from ai_fund_lab_v2.capital_allocation_ai.phase7e_strict_backtest import StrictConfig, leakage_audit, simulate_strict


def ranked() -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=30, freq="B").strftime("%Y-%m-%d").tolist()
    rows = []
    for i, d in enumerate(dates):
        top = ["1001", "1002", "1003"] if i == 0 else ["2001", "2002", "2003"]
        for r, c in enumerate(top, 1):
            rows.append({"target_date": d, "code": c, "buy_rank": r, "expected_edge_score": 0.2 - r * 0.01})
        if i > 0:
            rows.append({"target_date": d, "code": "1001", "buy_rank": 51, "expected_edge_score": -1.0})
    return pd.DataFrame(rows)


def prices() -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=35, freq="B").strftime("%Y-%m-%d").tolist()
    return pd.DataFrame([{"target_date": d, "code": c, "close": 100.0 + i, "year": 2025} for i, d in enumerate(dates) for c in ["1001", "1002", "1003", "2001", "2002", "2003"]])


def test_strict_outputs_trade_daily_and_holdings_ledgers() -> None:
    result = simulate_strict(ranked(), prices(), StrictConfig("T", "T", "C3", minimum_holding_days=15))
    assert not result["daily"].empty
    assert "total_assets_net" in result["daily"].columns
    assert "share_count" in result["holdings"].columns
    assert result["metrics"]["order_executed"] is False


def test_costs_are_separated_from_net_return() -> None:
    result = simulate_strict(ranked(), prices(), StrictConfig("T", "T", "COST", minimum_holding_days=15, transaction_cost_bps=10, slippage_bps=10))
    assert result["metrics"]["transaction_cost_paid"] > 0
    assert result["metrics"]["slippage_cost_paid"] > 0
    assert "net_return_after_cost" in result["trades"].columns


def test_leakage_audit_passes() -> None:
    audit = leakage_audit(ranked(), prices(), "2026-01-01T00:00:00+00:00")
    assert audit["status"] == "PASS"
    assert audit["no_future_data_in_decision"] is True
    assert audit["future_rank_used_in_decision"] is False
