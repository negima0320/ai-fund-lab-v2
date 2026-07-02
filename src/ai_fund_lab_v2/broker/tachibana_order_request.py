from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from typing import Any

from ai_fund_lab_v2.broker.request_builder import _tachibana_datetime
from ai_fund_lab_v2.broker.request_sequence import RequestSequenceManager
from ai_fund_lab_v2.broker.tachibana_codec import TachibanaV4R9Codec
from ai_fund_lab_v2.runtime.order_command import OrderCommand, OrderSide, OrderType, PriceType


class TachibanaOrderRequestError(ValueError):
    """Raised when a mock Tachibana order request shape is invalid."""


class TachibanaCashMarginType(str, Enum):
    CASH = "0"


class TachibanaMarketCode(str, Enum):
    TSE = "00"


class TachibanaAccountType(str, Enum):
    SPECIFIC = "1"


@dataclass(frozen=True)
class TachibanaCashStockOrderRequest:
    issue_code: str
    side: OrderSide
    quantity: Decimal
    order_price_type: PriceType
    order_price: Decimal = Decimal("0")
    market_code: str = TachibanaMarketCode.TSE.value
    cash_margin_type: str = TachibanaCashMarginType.CASH.value
    account_type: str = TachibanaAccountType.SPECIFIC.value
    time_in_force: str = "0"
    condition: str = "0"
    reverse_order_type: str = "0"
    reverse_trigger_condition: str = "0"
    reverse_price: str = "*"
    margin_position_day_type: str = "*"
    margin_position_tax_type: str = "*"
    second_password_required: bool = True
    second_password_present: bool = False
    production_allowed: bool = False

    def __post_init__(self) -> None:
        if not self.issue_code:
            raise TachibanaOrderRequestError("issue_code is required.")
        if self.quantity <= Decimal("0"):
            raise TachibanaOrderRequestError("quantity must be positive.")
        if self.order_price_type is PriceType.MARKET and self.order_price != Decimal("0"):
            raise TachibanaOrderRequestError("market order price must be zero.")
        if self.order_price_type is PriceType.LIMIT and self.order_price <= Decimal("0"):
            raise TachibanaOrderRequestError("limit order price must be positive.")
        if self.production_allowed:
            raise TachibanaOrderRequestError("production order request generation is prohibited in Phase10-S.")

    @classmethod
    def from_order_command(cls, command: OrderCommand, *, second_password_present: bool = False) -> "TachibanaCashStockOrderRequest":
        if command.order_type is not OrderType.CASH_EQUITY:
            raise TachibanaOrderRequestError("Phase10-S supports cash equity order shape only.")
        price = Decimal("0") if command.price_type is PriceType.MARKET else command.limit_price
        return cls(
            issue_code=command.issue_code,
            side=command.side,
            quantity=command.quantity,
            order_price_type=command.price_type,
            order_price=price,
            second_password_present=second_password_present,
        )

    def safe_metadata(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["side"] = self.side.value
        payload["quantity"] = str(self.quantity)
        payload["order_price"] = str(self.order_price)
        payload["order_price_type"] = self.order_price_type.value
        payload["second_password_value_saved"] = False
        payload["raw_order_request_saved"] = False
        payload["broker_api_called"] = False
        return payload


@dataclass(frozen=True)
class TachibanaCashStockOrderRequestBuilder:
    sequence_no: int = 0
    codec: TachibanaV4R9Codec | None = None
    sequence_manager: RequestSequenceManager | None = None

    def __post_init__(self) -> None:
        if self.sequence_manager is None:
            object.__setattr__(self, "sequence_manager", RequestSequenceManager(self.sequence_no))

    def build(self, request: TachibanaCashStockOrderRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "p_no": self._next_no(),
            "p_sd_date": _tachibana_datetime(),
            "sCLMID": "CLMKabuNewOrder",
            "sZyoutoekiKazeiC": request.account_type,
            "sIssueCode": request.issue_code,
            "sSizyouC": request.market_code,
            "sBaibaiKubun": _tachibana_side(request.side),
            "sCondition": request.condition,
            "sOrderPrice": _format_decimal(request.order_price),
            "sOrderSuryou": _format_decimal(request.quantity),
            "sGenkinShinyouKubun": request.cash_margin_type,
            "sOrderExpireDay": request.time_in_force,
            "sGyakusasiOrderType": request.reverse_order_type,
            "sGyakusasiZyouken": request.reverse_trigger_condition,
            "sGyakusasiPrice": request.reverse_price,
            "sTatebiType": request.margin_position_day_type,
            "sTategyokuZyoutoekiKazeiC": request.margin_position_tax_type,
        }
        # sSecondPassword is intentionally omitted in Phase10-S. Only presence
        # is carried through the authorization layer, never the secret value.
        return payload

    def build_final_payload_with_second_password(
        self,
        request: TachibanaCashStockOrderRequest,
        *,
        second_password_value: str,
    ) -> dict[str, Any]:
        if not second_password_value:
            raise TachibanaOrderRequestError("second password is required for final demo order payload.")
        payload = self.build(request)
        payload["sSecondPassword"] = second_password_value
        return payload

    def build_encoded_mock(self, request: TachibanaCashStockOrderRequest) -> dict[str, Any]:
        return (self.codec or TachibanaV4R9Codec()).encode_request(self.build(request))

    def build_final_payload_summary(self, request: TachibanaCashStockOrderRequest, *, dry_run: bool) -> dict[str, Any]:
        payload = self.build(request)
        return {
            "sCLMID": payload["sCLMID"],
            "p_no": payload["p_no"],
            "payload_key_count": len(payload) if dry_run else len(payload) + 1,
            "second_password_injected": False if dry_run else request.second_password_present,
            "second_password_value_saved": False,
            "raw_payload_saved": False,
            "broker_api_called": False,
            "dry_run": dry_run,
        }

    def build_safe_summary(self, request: TachibanaCashStockOrderRequest) -> dict[str, Any]:
        payload = self.build(request)
        return {
            "sCLMID": payload["sCLMID"],
            "p_no": payload["p_no"],
            "issue_code": request.issue_code,
            "side": request.side.value,
            "quantity": _format_decimal(request.quantity),
            "order_price_type": request.order_price_type.value,
            "order_price": _format_decimal(request.order_price),
            "second_password_required": request.second_password_required,
            "second_password_present": request.second_password_present,
            "second_password_value_saved": False,
            "production_allowed": request.production_allowed,
            "broker_api_called": False,
        }

    def _next_no(self) -> int:
        if self.sequence_manager is None:
            object.__setattr__(self, "sequence_manager", RequestSequenceManager(self.sequence_no))
        value = self.sequence_manager.next_no()
        object.__setattr__(self, "sequence_no", value)
        return value


def _tachibana_side(side: OrderSide) -> str:
    if side is OrderSide.SELL:
        return "1"
    if side is OrderSide.BUY:
        return "3"
    raise TachibanaOrderRequestError(f"Unsupported order side: {side!r}")


def _format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f")


@dataclass(frozen=True)
class RedactedOrderSubmitResult:
    status: str
    accepted: bool = False
    rejected: bool = False
    skipped: bool = False
    reason: str = ""
    broker_order_id_hash: str = ""
    p_errno: str | None = None
    p_err: str | None = None
    p_err_classification: str = ""
    result_code_present: bool = False
    result_code_value: str = ""
    result_code_zero: bool = False
    warning_code_present: bool = False
    warning_code_value: str = ""
    warning_code_zero: bool = False
    order_number_present: bool = False
    business_classification: str = ""
    accepted_with_warning: bool = False
    eigyou_day_present: bool = False
    raw_order_id_saved: bool = False
    raw_response_saved: bool = False

    def __post_init__(self) -> None:
        if self.broker_order_id_hash and not self.broker_order_id_hash.startswith("sha256:"):
            raise TachibanaOrderRequestError("broker_order_id_hash must be sha256-prefixed or omitted.")
        if self.raw_order_id_saved or self.raw_response_saved:
            raise TachibanaOrderRequestError("raw order id and raw response must not be saved.")
        if self.order_number_present and not self.broker_order_id_hash:
            raise TachibanaOrderRequestError("broker order id must be hashed when present.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_redacted_order_submit_result(raw: dict[str, Any]) -> RedactedOrderSubmitResult:
    order_id = str(
        raw.get("sOrderNumber")
        or raw.get("sOrderOrderNumber")
        or raw.get("sOrderUketsukeNumber")
        or raw.get("sOrderID")
        or raw.get("order_number")
        or raw.get("order_id")
        or ""
    )
    p_errno = str(raw.get("p_errno") or "")
    result_code_present = "sResultCode" in raw
    result_code = str(raw.get("sResultCode") or "")
    warning_code_present = "sWarningCode" in raw
    warning_code = str(raw.get("sWarningCode") or "")
    p_err = raw.get("p_err")
    protocol_error = bool(p_errno and p_errno != "0")
    result_success = result_code_present and result_code == "0"
    warning_success = (not warning_code_present) or warning_code in {"", "0"}
    accepted = not protocol_error and result_success and bool(order_id)
    accepted_with_warning = accepted and not warning_success
    if protocol_error:
        status = "REJECTED_OR_UNKNOWN"
        business_classification = "PROTOCOL_ERROR"
    elif result_code_present and result_code != "0":
        status = "REJECTED_OR_UNKNOWN"
        business_classification = "BUSINESS_REJECT"
    elif accepted_with_warning:
        status = "ACCEPTED_WITH_WARNING_REVIEW"
        business_classification = "BUSINESS_WARNING"
    elif accepted:
        status = "ACCEPTED"
        business_classification = "ACCEPTED"
    else:
        status = "REJECTED_OR_UNKNOWN"
        business_classification = "UNKNOWN_NO_ORDER_NUMBER"
    return RedactedOrderSubmitResult(
        status=status,
        accepted=accepted,
        rejected=not accepted,
        reason="normalized_redacted_order_submit_result",
        broker_order_id_hash=_hash_order_id(order_id),
        p_errno=p_errno if "p_errno" in raw else None,
        p_err=None,
        p_err_classification=_classify_redacted_order_error(
            str(p_err or ""),
            protocol_error=protocol_error,
            result_code_present=result_code_present,
            result_code=result_code,
            warning_code_present=warning_code_present,
            warning_code=warning_code,
            order_number_present=bool(order_id),
        ),
        result_code_present=result_code_present,
        result_code_value=result_code,
        result_code_zero=result_code_present and result_code == "0",
        warning_code_present=warning_code_present,
        warning_code_value=warning_code,
        warning_code_zero=warning_code_present and warning_code == "0",
        order_number_present=bool(order_id),
        business_classification=business_classification,
        accepted_with_warning=accepted_with_warning,
        eigyou_day_present=bool(raw.get("sEigyouDay")),
        raw_order_id_saved=False,
        raw_response_saved=False,
    )


def _hash_order_id(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return ""
    return f"sha256:{sha256(normalized.encode('utf-8')).hexdigest()}"


def _classify_redacted_order_error(
    text: str,
    *,
    protocol_error: bool = False,
    result_code_present: bool = False,
    result_code: str = "",
    warning_code_present: bool = False,
    warning_code: str = "",
    order_number_present: bool = False,
) -> str:
    if protocol_error:
        return "PROTOCOL_ERROR"
    if result_code_present and result_code != "0":
        return "BUSINESS_REJECT"
    if warning_code_present and warning_code not in {"", "0"} and order_number_present:
        return "BUSINESS_WARNING_REVIEW"
    if result_code_present and result_code == "0" and not order_number_present:
        return "ORDER_NUMBER_MISSING_AFTER_SUCCESS_RESULT"
    lowered = text.lower()
    if "p_no" in lowered or "前要求" in text:
        return "SESSION_SEQUENCE_OR_AUTH_ERROR"
    if "second" in lowered or "暗証" in text:
        return "SECOND_PASSWORD_FIELD_OR_VALUE_ERROR"
    if "引数" in text:
        return "BROKER_ARGUMENT_ERROR"
    return "BROKER_REJECTED_OR_UNKNOWN"
