from __future__ import annotations

import pandas as pd

from ai_fund_lab_v2.capital_allocation_ai.phase7g_final_integrated_backtest import (
    INITIAL_CAPITAL,
    add_issue_names,
    build_monthly_summary,
    build_phase7g_configs,
    build_symbol_summary,
    display_stock_code,
    normalize_jquants_code,
)


def test_phase7g_configs_cover_final_policy_set() -> None:
    ids = {c.policy_id for c in build_phase7g_configs()}
    for base in ["CAP5", "CAP4", "POLICY_Y_CAP4_EDGE08_CONF5", "A_FIXED_20BD", "C3_MIN15_T2"]:
        assert f"{base}_0BPS" in ids
        assert f"{base}_10BPS" in ids
        assert f"{base}_30BPS" in ids
    assert len(ids) == 15


def test_phase7g_initial_capital_is_one_million_jpy() -> None:
    assert INITIAL_CAPITAL == 1_000_000.0


def test_build_monthly_summary_calculates_return() -> None:
    daily = pd.DataFrame(
        [
            {"policy_id": "P", "policy_name": "Policy", "policy_role": "primary", "cost_slippage_bps": 0.0, "target_date": "2026-01-01", "total_assets_net": 100.0},
            {"policy_id": "P", "policy_name": "Policy", "policy_role": "primary", "cost_slippage_bps": 0.0, "target_date": "2026-01-31", "total_assets_net": 120.0},
        ]
    )
    monthly = build_monthly_summary(daily)
    assert monthly.iloc[0]["monthly_return"] == 0.2
    assert monthly.iloc[0]["monthly_profit"] == 20.0


def test_build_symbol_summary_splits_best_and_worst() -> None:
    trades = pd.DataFrame(
        [
            {"policy_id": "P", "action": "SELL", "code": "A", "display_code": "A", "company_name": "Alpha", "listed_issue_lookup_status": "FOUND", "realized_pnl": 100.0, "holding_days": 10},
            {"policy_id": "P", "action": "SELL", "code": "B", "display_code": "B", "company_name": "Beta", "listed_issue_lookup_status": "FOUND", "realized_pnl": -50.0, "holding_days": 20},
            {"policy_id": "Q", "action": "SELL", "code": "C", "display_code": "C", "company_name": "Gamma", "listed_issue_lookup_status": "FOUND", "realized_pnl": 999.0, "holding_days": 1},
        ]
    )
    best, worst = build_symbol_summary(trades, "P")
    assert best.iloc[0]["code"] == "A"
    assert best.iloc[0]["company_name"] == "Alpha"
    assert worst.iloc[0]["code"] == "B"


def test_stock_code_normalization_and_display() -> None:
    assert normalize_jquants_code(93670) == "93670"
    assert display_stock_code("93670") == "9367"
    assert normalize_jquants_code("148A0") == "148A0"
    assert display_stock_code("148A0") == "148A"


def test_add_issue_names_joins_local_master_shape() -> None:
    trades = pd.DataFrame([{"code": 93670, "policy_id": "P", "action": "SELL"}])
    master = pd.DataFrame(
        [
            {
                "jquants_code": "93670",
                "display_code": "9367",
                "company_name": "大東港運",
                "master_date": "2026-06-01",
                "market_name": "スタンダード",
            }
        ]
    )
    out = add_issue_names(trades, master)
    assert out.iloc[0]["display_code"] == "9367"
    assert out.iloc[0]["company_name"] == "大東港運"
    assert out.iloc[0]["listed_issue_lookup_status"] == "FOUND_IN_2026_06_01_MASTER"
