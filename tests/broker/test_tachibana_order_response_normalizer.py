from __future__ import annotations

from ai_fund_lab_v2.broker.tachibana_order_request import normalize_redacted_order_submit_result


def test_order_response_accepts_only_success_result_with_order_number() -> None:
    result = normalize_redacted_order_submit_result(
        {
            "p_errno": "0",
            "sResultCode": "0",
            "sWarningCode": "0",
            "sOrderNumber": "9000015",
            "sEigyouDay": "20260629",
        }
    )

    assert result.status == "ACCEPTED"
    assert result.accepted is True
    assert result.rejected is False
    assert result.order_number_present is True
    assert result.broker_order_id_hash.startswith("sha256:")
    assert result.raw_order_id_saved is False
    assert result.raw_response_saved is False
    assert "9000015" not in str(result.to_dict())


def test_order_response_p_errno_zero_without_order_number_is_not_accepted() -> None:
    result = normalize_redacted_order_submit_result({"p_errno": "0", "sResultCode": "0", "sWarningCode": "0"})

    assert result.status == "REJECTED_OR_UNKNOWN"
    assert result.accepted is False
    assert result.rejected is True
    assert result.order_number_present is False
    assert result.p_err_classification == "ORDER_NUMBER_MISSING_AFTER_SUCCESS_RESULT"


def test_order_response_business_reject_is_classified_without_raw_text() -> None:
    result = normalize_redacted_order_submit_result({"p_errno": "0", "sResultCode": "1234", "sResultText": "dummy business text"})

    assert result.status == "REJECTED_OR_UNKNOWN"
    assert result.accepted is False
    assert result.rejected is True
    assert result.business_classification == "BUSINESS_REJECT"
    assert result.p_err is None
    assert result.p_err_classification == "BUSINESS_REJECT"
    assert result.raw_response_saved is False


def test_order_response_warning_keeps_accepted_but_requires_review() -> None:
    result = normalize_redacted_order_submit_result(
        {
            "p_errno": "0",
            "sResultCode": "0",
            "sWarningCode": "777",
            "sWarningText": "dummy warning text",
            "sOrderNumber": "9000015",
        }
    )

    assert result.status == "ACCEPTED_WITH_WARNING_REVIEW"
    assert result.accepted is True
    assert result.rejected is False
    assert result.accepted_with_warning is True
    assert result.business_classification == "BUSINESS_WARNING"
    assert result.p_err_classification == "BUSINESS_WARNING_REVIEW"
    assert result.raw_response_saved is False
