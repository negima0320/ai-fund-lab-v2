from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from ai_fund_lab_v2.broker.models import (
    BrokerBalanceSnapshot,
    BrokerExecutionSnapshot,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    decimal_or_zero,
    utc_now_iso,
)
from ai_fund_lab_v2.broker.response import BrokerResponseEnvelope


def normalize_balance_summary(envelope: BrokerResponseEnvelope) -> BrokerBalanceSnapshot:
    raw = envelope.raw
    warnings = _warnings(envelope)
    cash_available = decimal_or_zero(_first(raw, "cash_available", "sCashAvailable", "sGenkinZandaka", "sSyukkin", "sSyukkinKanougaku"))
    buying_power = decimal_or_zero(
        _first(raw, "buying_power", "sBuyingPower", "sSummaryGenkabuKaituke", "sGenbutuKabuKaituke", "sGenbutuKaitukeKanougaku")
    )
    withdrawable_cash = decimal_or_zero(_first(raw, "withdrawable_cash", "sWithdrawableCash", "sSyukkin", "sSyukkinKanougaku"))
    total_assets = decimal_or_zero(_first(raw, "total_assets", "sTotalAssets", "sHyokaGakuGoukei", default=buying_power))
    return BrokerBalanceSnapshot(
        source="mock",
        as_of=_as_of(raw),
        currency=str(_first(raw, "currency", "sCurrency", default="JPY") or "JPY"),
        cash_available=cash_available,
        buying_power=buying_power,
        withdrawable_cash=withdrawable_cash,
        total_assets=total_assets,
        margin_buying_power=decimal_or_zero(_first(raw, "margin_buying_power", "sSinyouSinkidate", "sSinyouSinkidateKanougaku")),
        ipo_buying_power=decimal_or_zero(_first(raw, "ipo_buying_power", "sIPOKounyu")),
        nisa_growth_capacity=decimal_or_zero(
            _first(raw, "nisa_growth_capacity", "sSummaryNseityouTousiKanougaku", "sNseityouTousiKanougaku", "sSeityouTousiKanougaku")
        ),
        raw_clmid=envelope.clmid,
        raw_result_code=envelope.result_code,
        warnings=warnings,
    )


def normalize_buying_power(envelope: BrokerResponseEnvelope) -> BrokerBalanceSnapshot:
    raw = envelope.raw
    buying_power = decimal_or_zero(_first(raw, "buying_power", "sBuyingPower", "sSummaryGenkabuKaituke", "sGenbutuKabuKaituke", "sKanougaku"))
    return BrokerBalanceSnapshot(
        source="mock",
        as_of=_as_of(raw),
        currency=str(_first(raw, "currency", "sCurrency", default="JPY") or "JPY"),
        cash_available=decimal_or_zero(_first(raw, "cash_available", "sCashAvailable", "sSummaryGenkabuKaituke", "sGenkinZandaka")),
        buying_power=buying_power,
        withdrawable_cash=decimal_or_zero(_first(raw, "withdrawable_cash", "sWithdrawableCash", "sSyukkin", "sSyukkinKanougaku")),
        total_assets=decimal_or_zero(_first(raw, "total_assets", "sTotalAssets", default=buying_power)),
        margin_buying_power=decimal_or_zero(_first(raw, "margin_buying_power", "sSinyouSinkidate", "sSinyouSinkidateKanougaku")),
        ipo_buying_power=decimal_or_zero(_first(raw, "ipo_buying_power", "sIPOKounyu")),
        nisa_growth_capacity=decimal_or_zero(
            _first(raw, "nisa_growth_capacity", "sSummaryNseityouTousiKanougaku", "sNseityouTousiKanougaku", "sSeityouTousiKanougaku")
        ),
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
    return _normalize_orders(envelope, list_keys=("orders", "order_details", "aOrderList", "aOrderListDetail", "aCLMOrderListDetail"))


def normalize_order_detail_executions(envelope: BrokerResponseEnvelope, *, order_id: str = "") -> list[BrokerExecutionSnapshot]:
    raw = envelope.raw
    as_of = _as_of(raw)
    warnings = _warnings(envelope)
    return [
        BrokerExecutionSnapshot(
            broker="tachibana",
            source="mock",
            as_of=as_of,
            execution_id=str(_first(item, "execution_id", "sExecutionId", "sYakuzyouDate", default="") or ""),
            order_id=str(_first(item, "order_id", "sOrderNumber", "sOrderOrderNumber", default=order_id) or order_id),
            issue_code=str(_first(item, "issue_code", "sIssueCode", "sOrderIssueCode", default=_first(raw, "sIssueCode", "sOrderIssueCode", default="")) or ""),
            issue_name=str(_first(item, "issue_name", "sIssueName", default=_first(raw, "sIssueName", default="")) or ""),
            side=_normalize_side(_first(item, "side", "sSide", "sOrderBaibaiKubun", default=_first(raw, "sOrderBaibaiKubun", default=""))),
            quantity=decimal_or_zero(_first(item, "quantity", "sQuantity", "sYakuzyouSuryou", "sOrderYakuzyouSuryo")),
            price=decimal_or_zero(_first(item, "price", "sPrice", "sYakuzyouPrice", "sOrderYakuzyouPrice")),
            executed_at=str(_first(item, "executed_at", "sExecutedAt", "sYakuzyouDate", default="") or ""),
            currency=str(_first(item, "currency", "sCurrency", default="JPY") or "JPY"),
            raw_method=envelope.clmid,
            raw_result_code=envelope.result_code,
            warnings=warnings,
        )
        for item in _items(raw, ("executions", "aYakuzyouSikkouList"))
    ]


def normalize_market_quotes(envelope: BrokerResponseEnvelope) -> list[dict[str, Any]]:
    quotes: list[dict[str, Any]] = []
    for item in _items(envelope.raw, ("quotes", "aCLMMfdsMarketPrice")):
        quotes.append(
            {
                "issue_code": str(_first(item, "issue_code", "sIssueCode", default="") or ""),
                "last_price": _decimal_or_none(_first(item, "last_price", "pDPP")),
                "quote_time": str(_first(item, "quote_time", "tDPP:T", "tDPP", "sUpdateTime", default="") or ""),
                "open": _decimal_or_none(_first(item, "open", "pDOP")),
                "high": _decimal_or_none(_first(item, "high", "pDHP")),
                "low": _decimal_or_none(_first(item, "low", "pDLP")),
                "volume": _decimal_or_none(_first(item, "volume", "pDV")),
                "previous_day_ratio": _decimal_or_none(_first(item, "previous_day_ratio", "pPRP")),
                "raw_clmid": envelope.clmid,
                "raw_result_code": envelope.result_code,
                "warnings": _warnings(envelope),
            }
        )
    return quotes


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
            average_price=decimal_or_zero(_first(item, "average_price", "sAveragePrice", "sBokaTanka", "sHeikinTanka")),
            market_price=decimal_or_zero(_first(item, "market_price", "sMarketPrice", "sGenzaine", "sGenzaichi")),
            market_value=decimal_or_zero(_first(item, "market_value", "sMarketValue", "sHyokaGaku", "sHyoukaGaku")),
            unrealized_pnl=decimal_or_zero(_first(item, "unrealized_pnl", "sUnrealizedPnl", "sHyokaSoneki", "sHyoukaSoneki")),
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
            order_id=str(_first(item, "order_id", "sOrderId", "sOrderNo", "sOrderNumber", "sOrderOrderNumber", default="") or ""),
            issue_code=str(_first(item, "issue_code", "sIssueCode", "sOrderIssueCode", "sMeigaraCode", default="") or ""),
            issue_name=str(_first(item, "issue_name", "sIssueName", "sMeigaraName", default="") or ""),
            side=_normalize_side(_first(item, "side", "sSide", "sBaibaiKubun", "sOrderBaibaiKubun", default="")),
            order_type=str(_first(item, "order_type", "sOrderType", "sOrderPriceKubun", "sOrderOrderPriceKubun", "sOrderPriceKubun", default="") or ""),
            quantity=decimal_or_zero(_first(item, "quantity", "sQuantity", "sOrderSuryou", "sOrderOrderSuryou")),
            executed_quantity=decimal_or_zero(_first(item, "executed_quantity", "sExecutedQuantity", "sYakujouSuryou", "sOrderYakuzyouSuryo")),
            remaining_quantity=decimal_or_zero(_first(item, "remaining_quantity", "sRemainingQuantity", "sOrderZanSuryou", "sOrderCurrentSuryou")),
            price=decimal_or_zero(_first(item, "price", "sPrice", "sOrderPrice", "sOrderOrderPrice")),
            status=str(_first(item, "status", "sStatus", "sOrderStatus", "sOrderSyoukaiStatus", "sOrderYakuzyouStatus", default="") or ""),
            order_datetime=str(
                _first(item, "order_datetime", "sOrderDatetime", "sOrderDateTime", "sOrderOrderDateTime", "sOrderAcceptTime", default="") or ""
            ),
            expire_date=str(_first(item, "expire_date", "sExpireDate", "sSikkouDay", "sOrderSikkouDay", "sOrderExpireDay", "sOrderOrderExpireDay", default="") or ""),
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
    return {"1": "sell", "3": "buy", "買": "buy", "売": "sell", "BUY": "buy", "SELL": "sell"}.get(text.upper(), text)


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None
