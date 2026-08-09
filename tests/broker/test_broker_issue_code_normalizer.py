from __future__ import annotations

import pytest

from ai_fund_lab_v2.broker.issue_code_normalizer import (
    BrokerIssueCodeNormalizationError,
    ListedIssueInfo,
    classify_broker_security,
    normalize_broker_issue_code,
)


def test_jquants_trailing_zero_code_is_normalized_for_ordinary_stock() -> None:
    result = normalize_broker_issue_code(
        "92560",
        listed_info=ListedIssueInfo(code="92560", market="グロース", product_category="011", security_type="011"),
    )

    assert result.internal_code == "92560"
    assert result.broker_issue_code == "9256"
    assert result.broker_market_code == "00"
    assert result.normalization_rule == "JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR"
    assert result.normalization_status == "PASS"


def test_alphanumeric_jquants_trailing_zero_code_is_normalized_when_listed_info_allows_it() -> None:
    result = normalize_broker_issue_code(
        "148A0",
        listed_info={"Code": "148A0", "MktNm": "東証", "ProdCat": "011"},
    )

    assert result.broker_issue_code == "148A"


def test_missing_listed_info_fails_closed() -> None:
    with pytest.raises(BrokerIssueCodeNormalizationError, match="listed_info_missing"):
        normalize_broker_issue_code("92560", listed_info=None)


def test_disallowed_product_category_fails_closed() -> None:
    with pytest.raises(BrokerIssueCodeNormalizationError, match="BROKER_PRODUCT_CATEGORY_UNKNOWN"):
        normalize_broker_issue_code(
            "13430",
            listed_info=ListedIssueInfo(code="13430", market="東証", product_category="013", security_type="013"),
        )


def test_phase28_d48_foreign_listed_stock_category_fails_closed_with_explicit_reason() -> None:
    classification = classify_broker_security(
        ListedIssueInfo(code="93990", market="スタンダード", product_category="021", security_type="021")
    )

    assert classification.tradable is False
    assert classification.broker_security_type == "UNSUPPORTED_FOREIGN_LISTED_STOCK"
    assert classification.normalization_mode == "FAIL_CLOSED"
    assert classification.reason == "BROKER_PRODUCT_CATEGORY_UNSUPPORTED"

    with pytest.raises(BrokerIssueCodeNormalizationError, match="BROKER_PRODUCT_CATEGORY_UNSUPPORTED"):
        normalize_broker_issue_code(
            "93990",
            listed_info=ListedIssueInfo(code="93990", market="スタンダード", product_category="021", security_type="021"),
        )


def test_phase28_d48_unknown_product_category_fails_closed_with_distinct_reason() -> None:
    classification = classify_broker_security(
        ListedIssueInfo(code="99990", market="東証", product_category="999", security_type="999")
    )

    assert classification.tradable is False
    assert classification.broker_security_type == "UNKNOWN"
    assert classification.reason == "BROKER_PRODUCT_CATEGORY_UNKNOWN"

    with pytest.raises(BrokerIssueCodeNormalizationError, match="BROKER_PRODUCT_CATEGORY_UNKNOWN"):
        normalize_broker_issue_code(
            "99990",
            listed_info=ListedIssueInfo(code="99990", market="東証", product_category="999", security_type="999"),
        )


def test_non_trailing_zero_five_character_code_fails_closed() -> None:
    with pytest.raises(BrokerIssueCodeNormalizationError, match="unsupported_code_shape"):
        normalize_broker_issue_code(
            "92561",
            listed_info=ListedIssueInfo(code="92561", market="東証", product_category="011", security_type="011"),
        )
