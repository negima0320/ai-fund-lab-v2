from __future__ import annotations

from ai_fund_lab_v2.paper_trading.approval_mode import AUTO_FOR_PAPER_TRADING, MANUAL_REQUIRED, REVIEW_ONLY, validate_approval_mode


def test_auto_for_paper_trading_allowed_in_paper_mode() -> None:
    result = validate_approval_mode(approval_mode=AUTO_FOR_PAPER_TRADING, execution_mode="paper-trading")

    assert result.allowed is True
    assert result.status == "APPROVAL_MODE_ALLOWED"


def test_auto_approval_blocked_in_broker_mode() -> None:
    result = validate_approval_mode(approval_mode=AUTO_FOR_PAPER_TRADING, execution_mode="broker")

    assert result.allowed is False
    assert "auto_approval_only_allowed_in_paper_trading_mode" in result.blocked_reasons
    assert "auto_approval_blocked_in_broker_mode" in result.blocked_reasons


def test_manual_required_and_review_only_are_valid_modes() -> None:
    assert validate_approval_mode(approval_mode=MANUAL_REQUIRED, execution_mode="broker").allowed is True
    assert validate_approval_mode(approval_mode=REVIEW_ONLY, execution_mode="paper-trading").allowed is True

