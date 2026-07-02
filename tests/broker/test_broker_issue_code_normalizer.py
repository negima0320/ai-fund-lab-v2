from __future__ import annotations

import pytest

from ai_fund_lab_v2.broker.issue_code_normalizer import (
    BrokerIssueCodeNormalizationError,
    ListedIssueInfo,
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
    with pytest.raises(BrokerIssueCodeNormalizationError, match="product_category_not_allowed"):
        normalize_broker_issue_code(
            "13430",
            listed_info=ListedIssueInfo(code="13430", market="東証", product_category="013", security_type="013"),
        )


def test_non_trailing_zero_five_character_code_fails_closed() -> None:
    with pytest.raises(BrokerIssueCodeNormalizationError, match="unsupported_code_shape"):
        normalize_broker_issue_code(
            "92561",
            listed_info=ListedIssueInfo(code="92561", market="東証", product_category="011", security_type="011"),
        )
