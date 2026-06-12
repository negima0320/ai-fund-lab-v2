from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ai_fund_lab_v2.broker.models import (
    BrokerBalanceSnapshot,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    decimal_or_zero,
    utc_now_iso,
)
from ai_fund_lab_v2.broker.response import BrokerResponseEnvelope


def normalize_balance_summary(envelope: BrokerResponseEnvelope) -> BrokerBalanceSnapshot:
    raw = envelope.raw
    warnings = _warnings(envelope)
    return BrokerBalanceSnapshot(
        source="mock",
        as_of=_as_of(raw),
        currency=str(_first(raw, "currency", "sCurrency", default="JPY") or "JPY"),
        cash_available=decimal_or_zero(_first(raw, "cash_available", "sCashAvailable", "sGenkinZandaka")),
        buying_power=decimal_or_zero(_first(raw, "buying_power", "sBuyingPower", "sGenbutuKabuKaituke")),
        withdrawable_cash=decimal_or_zero(_first(raw, "withdrawable_cash", "sWithdrawableCash", "sSyukkinKanougaku")),
        total_assets=decimal_or_zero(_first(raw, "total_assets", "sTotalAssets", "sHyokaGakuGoukei")),
        raw_clmid=envelope.clmid,
        raw_result_code=envelope.result_code,
        warnings=warnings,
    )


def normalize_buying_power(envelope: BrokerResponseEnvelope) -> BrokerBalanceSnapshot:
    raw = envelope.raw
    buying_power = decimal_or_zero(_first(raw, "buying_power", "sBuyingPower", "sGenbutuKabuKaituke", "sKanougaku"))
    return BrokerBalanceSnapshot(
        source="mock",
        as_of=_as_of(raw),
        currency=str(_first(raw, "currency", "sCurrency", default="JPY") or "JPY"),
        cash_available=decimal_or_zero(_first(raw, "cash_available", "sCashAvailable", "sGenkinZandaka")),
        buying_power=buying_power,
        withdrawable_cash=decimal_or_zero(_first(raw, "withdrawable_cash", "sWithdrawableCash", "sSyukkinKanougaku")),
        total_assets=decimal_or_zero(_first(raw, "total_assets", "sTotalAssets", default=buying_power)),
        raw_clmid=envelope.clmid,
        raw_result_code=envelope.result_code,
        warnings=_warnings(envelope),
    )


def normalize_cash_positions(envelope: BrokerResponseEnvelope) -> list[BrokerPositionSnapshot]:
    return _normalize_positions(envelope, account_type="cash", list_keys=("positions", "aGenbutuKabuList", "aCLMGenbutuKabuList"))


def normalize_margin_positions(envelope: BrokerResponseEnvelope) -> list[BrokerPositionSnapshot]:
    return _normalize_positions(envelope, account_type="margin", list_keys=("positions", "aShinyouTategyokuList", "aCLMShinyouTategyokuList"))


def normalize_order_list(envelope: BrokerResponseEnvelope) -> list[BrokerOrderSnapshot]:
    return _normalize_orders(envelope, list_keys=("orders", "aOrderList", "aCLMOrderList"))


def normalize_order_list_detail(envelope: BrokerResponseEnvelope) -> list[BrokerOrderSnapshot]:
    return _normalize_orders(envelope, list_keys=("orders", "order_details", "aOrderListDetail", "aCLMOrderListDetail"))


def _normalize_positions(
    envelope: BrokerResponseEnvelope, *, account_type: str, list_keys: tuple[str, ...]
) -> list[BrokerPositionSnapshot]:
    as_of = _as_of(envelope.raw)
    warnings = _warnings(envelope)
    return [
        BrokerPositionSnapshot(
            source="mock",
            as_of=as_of,
            account_type=str(_first(item, "account_type", "sAccountType", default=account_type) or account_type),
            issue_code=str(_first(item, "issue_code", "sIssueCode", "sMeigaraCode", default="") or ""),
            issue_name=str(_first(item, "issue_name", "sIssueName", "sMeigaraName", default="") or ""),
            quantity=decimal_or_zero(_first(item, "quantity", "sQuantity", "sZanKabuSuu")),
            available_quantity=decimal_or_zero(_first(item, "available_quantity", "sAvailableQuantity", "sUritukeKanouSuu")),
            average_price=decimal_or_zero(_first(item, "average_price", "sAveragePrice", "sBokaTanka")),
            market_price=decimal_or_zero(_first(item, "market_price", "sMarketPrice", "sGenzaine")),
            market_value=decimal_or_zero(_first(item, "market_value", "sMarketValue", "sHyokaGaku")),
            unrealized_pnl=decimal_or_zero(_first(item, "unrealized_pnl", "sUnrealizedPnl", "sHyokaSoneki")),
            raw_clmid=envelope.clmid,
            raw_result_code=envelope.result_code,
            warnings=warnings,
        )
        for item in _items(envelope.raw, list_keys)
    ]


def _normalize_orders(envelope: BrokerResponseEnvelope, *, list_keys: tuple[str, ...]) -> list[BrokerOrderSnapshot]:
    as_of = _as_of(envelope.raw)
    warnings = _warnings(envelope)
    return [
        BrokerOrderSnapshot(
            source="mock",
            as_of=as_of,
            order_id=str(_first(item, "order_id", "sOrderId", "sOrderNo", default="") or ""),
            issue_code=str(_first(item, "issue_code", "sIssueCode", "sMeigaraCode", default="") or ""),
            issue_name=str(_first(item, "issue_name", "sIssueName", "sMeigaraName", default="") or ""),
            side=_normalize_side(_first(item, "side", "sSide", "sBaibaiKubun", default="")),
            order_type=str(_first(item, "order_type", "sOrderType", "sOrderPriceKubun", default="") or ""),
            quantity=decimal_or_zero(_first(item, "quantity", "sQuantity", "sOrderSuryou")),
            executed_quantity=decimal_or_zero(_first(item, "executed_quantity", "sExecutedQuantity", "sYakujouSuryou")),
            remaining_quantity=decimal_or_zero(_first(item, "remaining_quantity", "sRemainingQuantity", "sOrderZanSuryou")),
            price=decimal_or_zero(_first(item, "price", "sPrice", "sOrderPrice")),
            status=str(_first(item, "status", "sStatus", "sOrderStatus", "sOrderSyoukaiStatus", default="") or ""),
            order_datetime=str(_first(item, "order_datetime", "sOrderDatetime", "sOrderDateTime", default="") or ""),
            expire_date=str(_first(item, "expire_date", "sExpireDate", "sSikkouDay", default="") or ""),
            raw_clmid=envelope.clmid,
            raw_result_code=envelope.result_code,
            warnings=warnings,
        )
        for item in _items(envelope.raw, list_keys)
    ]


def _first(data: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return default


def _items(raw: Mapping[str, Any], list_keys: tuple[str, ...]) -> list[Mapping[str, Any]]:
    for key in list_keys:
        value = raw.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    return []


def _as_of(raw: Mapping[str, Any]) -> str:
    value = _first(raw, "as_of", "sAsOf", "sUpdateTime")
    return str(value) if value else utc_now_iso()


def _warnings(envelope: BrokerResponseEnvelope) -> tuple[str, ...]:
    warnings: list[str] = []
    if envelope.warning_code:
        warnings.append(envelope.warning_code)
    if envelope.warning_text:
        warnings.append(envelope.warning_text)
    if not envelope.is_success():
        warnings.append(f"result_code={envelope.result_code}")
    return tuple(warnings)


def _normalize_side(value: Any) -> str:
    text = str(value or "")
    return {"1": "buy", "2": "sell", "買": "buy", "売": "sell"}.get(text, text)
