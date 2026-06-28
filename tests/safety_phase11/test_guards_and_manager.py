from ai_fund_lab_v2.safety_phase11.guards import BrokerDivergenceGuard, DailyLossGuard, DuplicateOrderGuard, IndividualCrashGuard, MarketCrashGuard, MarketRecoveryGuard, MaxExposureGuard, QuoteStaleGuard
from ai_fund_lab_v2.safety_phase11.models import SafetyCheckInput, SafetyDecision, SafetyState
from ai_fund_lab_v2.safety_phase11.safety_manager import SafetyManager


def test_market_crash_guard_requires_market_stress_review_not_emergency():
    result = MarketCrashGuard().evaluate(SafetyCheckInput(market={"market_crash": True}))
    assert result.decision is SafetyDecision.REVIEW_REQUIRED
    assert result.state_after is SafetyState.MARKET_STRESS
    assert result.reason_code == "MARKET_STRESS"
    assert result.details["emergency_stop"] is False


def test_recovery_guard_does_not_auto_return_to_normal():
    result = MarketRecoveryGuard().evaluate(SafetyCheckInput(current_state=SafetyState.BUY_STOP, market={"recovery_candidate": True}))
    assert result.decision is SafetyDecision.REVIEW_REQUIRED
    assert result.state_after is SafetyState.RECOVERY_CANDIDATE
    assert result.state_after is not SafetyState.NORMAL


def test_individual_crash_guard_classifies_7_10_15_percent_thresholds():
    warning = IndividualCrashGuard().evaluate(
        SafetyCheckInput(positions=({"issue_code": "7203", "average_price": "1000", "latest_price": "930"},))
    )
    assert warning.decision is SafetyDecision.REVIEW_REQUIRED
    assert warning.reason_code == "INDIVIDUAL_DRAWDOWN_WARNING"

    stop_loss = IndividualCrashGuard().evaluate(
        SafetyCheckInput(positions=({"issue_code": "7203", "average_price": "1000", "latest_price": "900"},))
    )
    assert stop_loss.decision is SafetyDecision.REVIEW_REQUIRED
    assert stop_loss.reason_code == "SELL_REVIEW_REQUIRED"

    emergency = IndividualCrashGuard().evaluate(
        SafetyCheckInput(positions=({"issue_code": "7203", "average_price": "1000", "latest_price": "850"},))
    )
    assert emergency.decision is SafetyDecision.REVIEW_REQUIRED
    assert emergency.reason_code == "HIGH_RISK_REVIEW"
    assert emergency.details["emergency_stop"] is False


def test_duplicate_order_guard_blocks_same_issue_and_side():
    result = DuplicateOrderGuard().evaluate(
        SafetyCheckInput(
            order_plan={"issue_code": "7203", "side": "BUY"},
            open_orders=({"issue_code": "7203", "side": "BUY", "status": "OPEN"},),
        )
    )
    assert result.decision is SafetyDecision.EMERGENCY_STOP
    assert result.reason_code == "DUPLICATE_ORDER_SYSTEM_EMERGENCY"


def test_quote_stale_guard_blocks_stale_quote():
    result = QuoteStaleGuard().evaluate(
        SafetyCheckInput(
            order_plan={"issue_code": "7203", "side": "BUY"},
            quotes={"7203": {"age_seconds": "999", "price": "1000"}},
            config={"max_quote_age_seconds": "300"},
        )
    )
    assert result.decision is SafetyDecision.BLOCK
    assert result.reason_code == "QUOTE_STALE"


def test_max_exposure_guard_does_not_block_exposure_reducing_sell():
    result = MaxExposureGuard().evaluate(
        SafetyCheckInput(
            order_plan={"issue_code": "7203", "side": "SELL", "notional": "0"},
            positions=({"issue_code": "7203", "market_value": "900000"},),
            config={"max_total_exposure": "850000"},
        )
    )
    assert result.decision is SafetyDecision.ALLOW
    assert result.reason_code == "EXPOSURE_REDUCING_ORDER"


def test_max_exposure_ratio_cap_scales_with_equity():
    cases = (("1000000", "850000.00"), ("2000000", "1700000.00"), ("5000000", "4250000.00"))
    for equity, expected_cap in cases:
        result = MaxExposureGuard().evaluate(
            SafetyCheckInput(
                order_plan={"issue_code": "7203", "side": "BUY", "notional": "100000", "cash_basis": equity},
                positions=(),
                config={"max_total_exposure_ratio": "0.85", "base_equity": equity},
            )
        )
        assert result.decision is SafetyDecision.ALLOW
        assert result.details["max_allowed_exposure"] == expected_cap


def test_max_exposure_ratio_cap_blocks_projected_exposure_over_limit():
    result = MaxExposureGuard().evaluate(
        SafetyCheckInput(
            order_plan={"issue_code": "7203", "side": "BUY", "notional": "200000", "cash_basis": "1000000"},
            positions=({"issue_code": "6758", "market_value": "800000"},),
            config={"max_total_exposure_ratio": "0.85", "base_equity": "1000000"},
        )
    )
    assert result.decision is SafetyDecision.BLOCK
    assert result.reason_code == "MAX_EXPOSURE_EXCEEDED"
    assert result.details["current_exposure"] == "800000"
    assert result.details["projected_exposure"] == "1000000"
    assert result.details["base_equity"] == "1000000"
    assert result.details["max_total_exposure_ratio"] == "0.85"
    assert result.details["max_allowed_exposure"] == "850000.00"
    assert result.details["cash_available"] == "1000000"
    assert result.details["position_count"] == 1
    assert result.details["side"] == "BUY"
    assert result.details["issue_code"] == "7203"


def test_max_exposure_ratio_cap_allows_buy_within_limit():
    result = MaxExposureGuard().evaluate(
        SafetyCheckInput(
            order_plan={"issue_code": "7203", "side": "BUY", "notional": "50000", "cash_basis": "1000000"},
            positions=({"issue_code": "6758", "market_value": "750000"},),
            config={"max_total_exposure_ratio": "0.85", "base_equity": "1000000"},
        )
    )
    assert result.decision is SafetyDecision.ALLOW
    assert result.details["projected_exposure"] == "800000"
    assert result.details["max_allowed_exposure"] == "850000.00"


def test_max_exposure_absent_absolute_cap_does_not_use_fixed_850k():
    result = MaxExposureGuard().evaluate(
        SafetyCheckInput(
            order_plan={"issue_code": "7203", "side": "BUY", "notional": "200000", "cash_basis": "5000000"},
            positions=({"issue_code": "6758", "market_value": "900000"},),
            config={"max_total_exposure_ratio": "0.85", "base_equity": "5000000"},
        )
    )
    assert result.decision is SafetyDecision.ALLOW
    assert result.details["max_allowed_exposure"] == "4250000.00"
    assert result.details["max_total_exposure_absolute_cap"] is None


def test_max_exposure_optional_absolute_cap_applies_only_when_configured():
    result = MaxExposureGuard().evaluate(
        SafetyCheckInput(
            order_plan={"issue_code": "7203", "side": "BUY", "notional": "200000", "cash_basis": "5000000"},
            positions=({"issue_code": "6758", "market_value": "900000"},),
            config={"max_total_exposure_ratio": "0.85", "base_equity": "5000000", "max_total_exposure_absolute_cap": "850000"},
        )
    )
    assert result.decision is SafetyDecision.BLOCK
    assert result.reason_code == "MAX_EXPOSURE_EXCEEDED"
    assert result.details["max_total_exposure_absolute_cap"] == "850000"
    assert result.details["max_allowed_exposure"] == "850000"


def test_daily_loss_only_requires_review_not_emergency():
    result = DailyLossGuard().evaluate(SafetyCheckInput(market={"daily_loss_pct": "-0.12"}))
    assert result.decision is SafetyDecision.REVIEW_REQUIRED
    assert result.state_after is SafetyState.MARKET_STRESS
    assert result.reason_code == "MARKET_STRESS_DAILY_LOSS"
    assert result.details["emergency_stop"] is False


def test_severe_broker_divergence_is_system_emergency():
    result = BrokerDivergenceGuard().evaluate(
        SafetyCheckInput(broker_snapshot={"divergence": "POSITION_MISMATCH", "divergence_severity": "SEVERE"})
    )
    assert result.decision is SafetyDecision.EMERGENCY_STOP
    assert result.state_after is SafetyState.SYSTEM_EMERGENCY_STOP
    assert result.details["system_fault"] is True


def test_safety_manager_keeps_market_and_price_drawdown_in_review():
    manager = SafetyManager(guards=(MarketCrashGuard(), IndividualCrashGuard()))
    result = manager.evaluate(
        SafetyCheckInput(
            market={"market_crash": True},
            positions=({"issue_code": "7203", "average_price": "1000", "latest_price": "850"},),
        )
    )
    assert result.overall_decision is SafetyDecision.REVIEW_REQUIRED
    assert result.state_candidate in {SafetyState.BUY_OPPORTUNITY_REVIEW, SafetyState.MARKET_STRESS, SafetyState.WARNING}
    assert "MARKET_CRASH" in result.triggered_guards
    assert "INDIVIDUAL_CRASH" in result.triggered_guards
