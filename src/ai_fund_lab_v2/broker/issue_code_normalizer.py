from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


class BrokerIssueCodeNormalizationError(ValueError):
    """Raised when internal issue code cannot be safely mapped to broker code."""


@dataclass(frozen=True)
class ListedIssueInfo:
    code: str
    market: str
    product_category: str
    security_type: str = ""
    current_listed: bool = True


@dataclass(frozen=True)
class BrokerIssueCodeNormalizationResult:
    internal_code: str
    broker_issue_code: str
    broker_market_code: str
    normalization_rule: str
    normalization_status: str
    market: str
    product_category: str
    security_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BrokerSecurityClassification:
    tradable: bool
    broker_security_type: str
    normalization_mode: str
    reason: str
    authority: str


BROKER_CASH_EQUITY_PRODUCT_CATEGORIES = frozenset({"011"})
BROKER_UNSUPPORTED_PRODUCT_CATEGORIES = frozenset({"021"})
ORDINARY_STOCK_PRODUCT_CATEGORIES = BROKER_CASH_EQUITY_PRODUCT_CATEGORIES
TACHIBANA_TSE_MARKET_CODE = "00"
TSE_MARKET_NAMES = frozenset(
    {
        "プライム",
        "スタンダード",
        "グロース",
        "東証",
        "東京証券取引所",
        "Tokyo Stock Exchange",
        "TSE",
    }
)


def normalize_broker_issue_code(
    internal_code: str,
    *,
    listed_info: ListedIssueInfo | dict[str, Any] | None,
) -> BrokerIssueCodeNormalizationResult:
    code = str(internal_code or "").strip()
    info = _coerce_listed_info(listed_info)
    if not code:
        raise BrokerIssueCodeNormalizationError("internal_code_missing")
    if info is None:
        raise BrokerIssueCodeNormalizationError("listed_info_missing")
    if str(info.code) != code:
        raise BrokerIssueCodeNormalizationError("listed_info_code_mismatch")
    if not info.current_listed:
        raise BrokerIssueCodeNormalizationError("listed_info_not_current")
    classification = classify_broker_security(info)
    if not classification.tradable:
        raise BrokerIssueCodeNormalizationError(classification.reason)
    if not info.security_type:
        raise BrokerIssueCodeNormalizationError("security_type_missing")
    broker_market_code = _broker_market_code(info.market)
    if not broker_market_code:
        raise BrokerIssueCodeNormalizationError("market_not_mapped")
    if len(code) == 4:
        broker_code = code
        rule = "BROKER_4CHAR_ALREADY_NORMALIZED"
    elif len(code) == 5 and code.endswith("0"):
        broker_code = code[:-1]
        rule = "JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR"
    else:
        raise BrokerIssueCodeNormalizationError("unsupported_code_shape")
    if not _is_valid_broker_issue_code(broker_code):
        raise BrokerIssueCodeNormalizationError("broker_issue_code_malformed")
    return BrokerIssueCodeNormalizationResult(
        internal_code=code,
        broker_issue_code=broker_code,
        broker_market_code=broker_market_code,
        normalization_rule=rule,
        normalization_status="PASS",
        market=info.market,
        product_category=info.product_category,
        security_type=info.security_type,
    )


def classify_broker_security(listed_info: ListedIssueInfo | dict[str, Any] | None) -> BrokerSecurityClassification:
    info = _coerce_listed_info(listed_info)
    authority = "tachibana_e_shiten_cash_equity_product_contract"
    if info is None:
        return BrokerSecurityClassification(
            tradable=False,
            broker_security_type="UNKNOWN",
            normalization_mode="FAIL_CLOSED",
            reason="listed_info_missing",
            authority=authority,
        )
    if not info.product_category:
        return BrokerSecurityClassification(
            tradable=False,
            broker_security_type="UNKNOWN",
            normalization_mode="FAIL_CLOSED",
            reason="product_category_missing",
            authority=authority,
        )
    if info.product_category in BROKER_CASH_EQUITY_PRODUCT_CATEGORIES:
        return BrokerSecurityClassification(
            tradable=True,
            broker_security_type="TACHIBANA_CASH_EQUITY_LISTED_STOCK",
            normalization_mode="NORMALIZE_ISSUE_CODE_ONLY",
            reason="BROKER_PRODUCT_CATEGORY_SUPPORTED",
            authority=authority,
        )
    if info.product_category in BROKER_UNSUPPORTED_PRODUCT_CATEGORIES:
        return BrokerSecurityClassification(
            tradable=False,
            broker_security_type="UNSUPPORTED_FOREIGN_LISTED_STOCK",
            normalization_mode="FAIL_CLOSED",
            reason="BROKER_PRODUCT_CATEGORY_UNSUPPORTED",
            authority=authority,
        )
    return BrokerSecurityClassification(
        tradable=False,
        broker_security_type="UNKNOWN",
        normalization_mode="FAIL_CLOSED",
        reason="BROKER_PRODUCT_CATEGORY_UNKNOWN",
        authority=authority,
    )


def _coerce_listed_info(value: ListedIssueInfo | dict[str, Any] | None) -> ListedIssueInfo | None:
    if value is None:
        return None
    if isinstance(value, ListedIssueInfo):
        return value
    code = str(value.get("code") or value.get("Code") or "").strip()
    market = str(value.get("market") or value.get("MktNm") or value.get("market_name") or "").strip()
    product_category = str(value.get("product_category") or value.get("ProdCat") or "").strip()
    security_type = str(value.get("security_type") or value.get("SecType") or value.get("Type") or product_category).strip()
    current_raw = value.get("current_listed", value.get("is_current_listed", True))
    current_listed = str(current_raw).lower() not in {"false", "0", "no", "nan", "none", ""}
    return ListedIssueInfo(
        code=code,
        market=market,
        product_category=product_category,
        security_type=security_type,
        current_listed=current_listed,
    )


def _broker_market_code(market: str) -> str:
    normalized = str(market or "").strip()
    if normalized in TSE_MARKET_NAMES:
        return TACHIBANA_TSE_MARKET_CODE
    return ""


def _is_valid_broker_issue_code(value: str) -> bool:
    if len(value) != 4:
        return False
    return all(ch.isdigit() or ("A" <= ch.upper() <= "Z") for ch in value)
