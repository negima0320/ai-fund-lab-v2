from __future__ import annotations

import pandas as pd

from ai_fund_lab_v2.capital_allocation_ai.engine import build_capital_allocation_decisions
from ai_fund_lab_v2.capital_allocation_ai.policy import calculate_available_cash, calculate_target_position_value
from ai_fund_lab_v2.capital_allocation_ai.schema import Phase7AConfig, PortfolioSnapshot


def test_phase7a_buy_uses_top3_and_cash_buffer_caps_amount() -> None:
    decisions = _decisions(cash=240_000.0, replacement_enabled=False)
    by_code = _by_code(decisions)

    buy = by_code["7001"]
    assert buy.action == "BUY"
    assert buy.buy_amount <= calculate_target_position_value(1_000_000.0, Phase7AConfig())
    assert buy.buy_amount <= calculate_available_cash(buy.cash_before_action, 1_000_000.0, Phase7AConfig())


def test_phase7a_minimum_holding_days_holds_except_emergency() -> None:
    by_code = _by_code(_decisions())

    assert by_code["7101"].action == "HOLD"
    assert "hold_centered_policy" in by_code["7101"].validation_notes
    assert by_code["7107"].action == "HOLD"
    assert by_code["7107"].holding_days < Phase7AConfig().minimum_holding_days


def test_phase7a_emergency_exit_is_full_exit_candidate() -> None:
    by_code = _by_code(_decisions())

    decision = by_code["7102"]
    assert decision.action == "EMERGENCY_EXIT"
    assert decision.sell_amount == decision.current_position_value
    assert decision.emergency_reason


def test_phase7a_phase6_exit_single_signal_becomes_defensive_review() -> None:
    by_code = _by_code(_decisions())

    decision = by_code["7103"]
    assert decision.action == "DEFENSIVE_REVIEW"
    assert decision.sell_amount == 0.0
    assert "phase6_EXIT_signal" in decision.defensive_reason


def test_phase7a_top3_drop_alone_does_not_replace() -> None:
    by_code = _by_code(_decisions())

    decision = by_code["7104"]
    assert decision.action == "HOLD"
    assert decision.opportunity_rank == 25
    assert decision.replacement_reason == "confirmation_days_not_met"


def test_phase7a_replace_requires_minimum_days_rank_degradation_edge_and_confirmation() -> None:
    decisions = _decisions()
    by_code = _by_code(decisions)
    replace_buys = [decision for decision in decisions if decision.action == "REPLACE_BUY"]

    assert by_code["7105"].action == "REPLACE_SELL"
    assert by_code["7105"].sell_amount == by_code["7105"].current_position_value
    assert "minimum_holding_days_met" in by_code["7105"].replacement_reason
    assert "rank_degradation_met" in by_code["7105"].replacement_reason
    assert "edge_margin_met" in by_code["7105"].replacement_reason
    assert "confirmation_days_met" in by_code["7105"].replacement_reason
    assert len(replace_buys) == 1
    assert replace_buys[0].code == "7001"


def test_phase7a_sell_amount_never_exceeds_current_position_value() -> None:
    for decision in _decisions():
        assert decision.sell_amount <= decision.current_position_value


def _decisions(cash: float = 500_000.0, replacement_enabled: bool = True):
    return build_capital_allocation_decisions(
        portfolio=PortfolioSnapshot(target_date="2026-06-15", total_assets=1_000_000.0, cash=cash),
        opportunity_frame=_opportunities(),
        holdings_frame=_holdings(),
        position_signal_frame=_signals(replacement_enabled=replacement_enabled),
        config=Phase7AConfig(),
    )


def _by_code(decisions):
    return {decision.code: decision for decision in decisions}


def _opportunities() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2026-06-15", "code": "7001", "expected_edge_score": 0.12, "buy_rank": 1, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7002", "expected_edge_score": 0.10, "buy_rank": 2, "downside_risk_score": 0.25, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7003", "expected_edge_score": 0.09, "buy_rank": 3, "downside_risk_score": 0.30, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7004", "expected_edge_score": 0.07, "buy_rank": 4, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7005", "expected_edge_score": 0.06, "buy_rank": 5, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7101", "expected_edge_score": 0.08, "buy_rank": 8, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7102", "expected_edge_score": 0.04, "buy_rank": 12, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7103", "expected_edge_score": 0.03, "buy_rank": 18, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7104", "expected_edge_score": 0.01, "buy_rank": 25, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7105", "expected_edge_score": 0.09, "buy_rank": 22, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7106", "expected_edge_score": 0.05, "buy_rank": 30, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7107", "expected_edge_score": 0.02, "buy_rank": 28, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
        ]
    )


def _holdings() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2026-06-15", "code": "7101", "current_position_value": 180_000.0, "holding_days": 2, "unrealized_return": 0.03},
            {"target_date": "2026-06-15", "code": "7102", "current_position_value": 160_000.0, "holding_days": 8, "unrealized_return": -0.16},
            {"target_date": "2026-06-15", "code": "7103", "current_position_value": 140_000.0, "holding_days": 9, "unrealized_return": -0.02},
            {"target_date": "2026-06-15", "code": "7104", "current_position_value": 120_000.0, "holding_days": 10, "unrealized_return": 0.02},
            {"target_date": "2026-06-15", "code": "7105", "current_position_value": 130_000.0, "holding_days": 10, "unrealized_return": 0.04},
            {"target_date": "2026-06-15", "code": "7106", "current_position_value": 110_000.0, "holding_days": 10, "unrealized_return": 0.01},
            {"target_date": "2026-06-15", "code": "7107", "current_position_value": 100_000.0, "holding_days": 3, "unrealized_return": 0.00},
        ]
    )


def _signals(replacement_enabled: bool = True) -> pd.DataFrame:
    replacement_days = 2 if replacement_enabled else 0
    return pd.DataFrame(
        [
            {"target_date": "2026-06-15", "code": "7101", "position_signal": "HOLD", "replacement_confirmation_days": 0},
            {"target_date": "2026-06-15", "code": "7102", "position_signal": "HOLD", "replacement_confirmation_days": 0},
            {"target_date": "2026-06-15", "code": "7103", "position_signal": "EXIT", "replacement_confirmation_days": 0},
            {"target_date": "2026-06-15", "code": "7104", "position_signal": "HOLD", "replacement_confirmation_days": 0},
            {"target_date": "2026-06-15", "code": "7105", "position_signal": "HOLD", "replacement_confirmation_days": replacement_days},
            {"target_date": "2026-06-15", "code": "7106", "position_signal": "HOLD", "replacement_confirmation_days": 1},
            {"target_date": "2026-06-15", "code": "7107", "position_signal": "HOLD", "replacement_confirmation_days": 2},
        ]
    )
