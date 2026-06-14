from __future__ import annotations

from ai_fund_lab_v2.capital_allocation_ai.schema import (
    DECISION_COLUMNS,
    CapitalAllocationAction,
    DecisionRecord,
    Phase7AConfig,
)


def test_phase7a_config_defaults_match_design() -> None:
    config = Phase7AConfig()

    assert config.initial_total_assets == 1_000_000
    assert config.cash_buffer_ratio == 0.05
    assert config.max_position_weight == 0.20
    assert config.min_position_value == 50_000
    assert config.max_position_value is None
    assert config.minimum_holding_days == 5
    assert config.replacement_rank_degradation_threshold == 20
    assert config.replacement_edge_margin == 0.02
    assert config.confirmation_days == 2
    assert config.emergency_exit_pct == -0.15


def test_phase7a_action_schema_contains_required_actions() -> None:
    assert {action.value for action in CapitalAllocationAction} == {
        "BUY",
        "HOLD",
        "NO_ACTION",
        "REPLACE_SELL",
        "REPLACE_BUY",
        "EMERGENCY_EXIT",
        "DEFENSIVE_REVIEW",
    }


def test_phase7a_decision_record_schema_order() -> None:
    assert DECISION_COLUMNS == tuple(DecisionRecord.__dataclass_fields__.keys())
    assert "buy_amount" in DECISION_COLUMNS
    assert "sell_amount" in DECISION_COLUMNS
    assert "cash_after_action" in DECISION_COLUMNS
    assert "validation_notes" in DECISION_COLUMNS
