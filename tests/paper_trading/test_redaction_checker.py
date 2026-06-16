import pytest

from ai_fund_lab_v2.paper_trading.reporting.redaction_checker import (
    PUBLIC_REPORT_NOT_READY,
    PublicReportNotReadyError,
    assert_public_report_ready,
    check_public_report_redaction,
)


def test_redaction_checker_allows_public_text() -> None:
    result = check_public_report_redaction("仮想運用の検証中です。投資判断は自己責任でお願いします。")
    assert result.ready


def test_redaction_checker_blocks_internal_terms() -> None:
    result = check_public_report_redaction("raw model score and feature schema hash leaked")
    assert result.status == PUBLIC_REPORT_NOT_READY
    assert "raw model score" in result.violations
    with pytest.raises(PublicReportNotReadyError):
        assert_public_report_ready("broker account data")

