from __future__ import annotations

import pandas as pd

from ai_fund_lab_v2.capital_allocation_ai.phase7f_turnover_reduction_validation import (
    build_phase7f_configs,
    enrich_metrics,
)


def test_phase7f_configs_include_required_scenarios() -> None:
    ids = {c.policy_id for c in build_phase7f_configs()}
    assert "A_FIXED_20BD" in ids
    assert "C3_MIN15_T2" in ids
    assert "CAP3" in ids
    assert "CAP8" in ids
    assert "COOLDOWN10" in ids
    assert "EDGE10" in ids
    assert "RANK_OUT10" in ids
    assert "CONFIRM5" in ids
    assert "POLICY_X_CAP5_EDGE05_CONF3" in ids
    assert "ROBUST_POLICY_X_30BPS" in ids


def test_phase7f_config_defaults_match_phase7e_winner() -> None:
    configs = {c.policy_id: c for c in build_phase7f_configs()}
    c3 = configs["C3_MIN15_T2"]
    assert c3.minimum_holding_days == 15
    assert c3.replacement_rank_threshold == 50
    assert c3.replacement_edge_margin == 0.02
    assert c3.confirmation_days == 2
    assert c3.settlement_mode == "conservative_T2_cash_unavailable"


def test_enrich_metrics_adds_2026_columns() -> None:
    metrics = {
        "policy_id": "CAP5",
        "cumulative_return_net": 10.0,
        "replacement_rate": 0.4,
    }
    annual = [
        {
            "policy_id": "CAP5",
            "year": 2026,
            "annual_return_net_by_year": 0.12,
            "annual_max_drawdown_net_by_year": -0.08,
            "annual_trade_count_by_year": 11,
            "annual_replacement_count_by_year": 4,
        }
    ]
    row = enrich_metrics(metrics, annual)
    assert row["scenario_group"] == "turnover"
    assert row["annual_return_2026"] == 0.12
    assert row["annual_dd_2026"] == -0.08
    assert row["cost_adjusted_return"] == 10.0


def test_policy_comparison_target_band_filter_shape() -> None:
    frame = pd.DataFrame(
        [
            {"policy_id": "LOW", "replacement_rate": 0.1, "cumulative_return_net": 1},
            {"policy_id": "MID", "replacement_rate": 0.3, "cumulative_return_net": 2},
            {"policy_id": "HIGH", "replacement_rate": 0.8, "cumulative_return_net": 3},
        ]
    )
    target = frame[(frame["replacement_rate"] >= 0.2) & (frame["replacement_rate"] <= 0.5)]
    assert target["policy_id"].tolist() == ["MID"]

