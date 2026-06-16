from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ai_fund_lab_v2.broker.models import (
    BrokerAccountSnapshot,
    BrokerBalanceSnapshot,
    BrokerExecutionSnapshot,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    decimal_or_zero,
    utc_now_iso,
)
from ai_fund_lab_v2.broker.moomoo.readonly_methods import MOOMOO_READ_ONLY_METHODS
from ai_fund_lab_v2.broker.sanitizer import hash_account_id


def normalize_moomoo_mock_response(payload: Mapping[str, Any]) -> dict[str, object]:
    _ensure_mock_payload_uses_read_only_methods(payload)
    metadata = _metadata(payload)
    orders = _normalize_orders(payload, metadata)
    return {
        "accounts": _normalize_accounts(payload, metadata),
        "balance": _normalize_balance(payload, metadata),
        "positions": _normalize_positions(payload, metadata),
        "orders": orders,
        "executions": _normalize_executions_from_orders(orders, metadata),
    }


def _ensure_mock_payload_uses_read_only_methods(payload: Mapping[str, Any]) -> None:
    for key in payload:
        if key == "metadata":
            continue
        if key not in MOOMOO_READ_ONLY_METHODS:
            raise ValueError(f"Unexpected moomoo mock method: {key}")


def _metadata(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    value = payload.get("metadata")
    return value if isinstance(value, Mapping) else {}


def _normalize_accounts(payload: Mapping[str, Any], metadata: Mapping[str, Any]) -> list[BrokerAccountSnapshot]:
    method = "get_acc_list"
    raw = _method_payload(payload, method)
    return [
        BrokerAccountSnapshot(
            broker="moomoo",
            source=_source(metadata),
            as_of=_as_of(metadata),
            account_ref=_account_ref(item, metadata),
            account_label=str(_first(item, "account_label", default="") or ""),
            environment=str(_first(item, "trd_env", default=metadata.get("environment", "readonly_mock")) or ""),
            account_type=str(_first(item, "acc_type", default="") or ""),
            broker_account_status=str(_first(item, "acc_status", default="") or ""),
            trade_market_auth=tuple(str(value) for value in _first(item, "trdmarket_auth", default=[]) or []),
            raw_method=method,
            raw_result_code=str(raw.get("ret", "")),
            warnings=_warnings(raw),
        )
        for item in _data_list(raw)
    ]


def _normalize_balance(payload: Mapping[str, Any], metadata: Mapping[str, Any]) -> BrokerBalanceSnapshot:
    method = "accinfo_query"
    raw = _method_payload(payload, method)
    data = _data_mapping(raw)
    return BrokerBalanceSnapshot(
        broker="moomoo",
        source=_source(metadata),
        as_of=_as_of(metadata),
        currency=str(_first(data, "currency", default=metadata.get("currency", "JPY")) or "JPY"),
        cash_available=decimal_or_zero(_first(data, "jp_cash", "cash", default="0")),
        buying_power=decimal_or_zero(_first(data, "jpy_net_cash_power", "power", default="0")),
        withdrawable_cash=decimal_or_zero(_first(data, "jp_avl_withdrawal_cash", "avl_withdrawal_cash", default="0")),
        total_assets=decimal_or_zero(_first(data, "jpy_assets", "total_assets", default="0")),
        raw_method=method,
        raw_result_code=str(raw.get("ret", "")),
        warnings=_warnings(raw, extra=(f"risk_status={data.get('risk_status')}",) if data.get("risk_status") else ()),
    )


def _normalize_positions(payload: Mapping[str, Any], metadata: Mapping[str, Any]) -> list[BrokerPositionSnapshot]:
    method = "position_list_query"
    raw = _method_payload(payload, method)
    return [
        BrokerPositionSnapshot(
            broker="moomoo",
            source=_source(metadata),
            as_of=_as_of(metadata),
            account_type="cash",
            issue_code=_normalize_issue_code(str(_first(item, "code", default="") or "")),
            issue_name=str(_first(item, "stock_name", default="") or ""),
            quantity=decimal_or_zero(_first(item, "qty", default="0")),
            available_quantity=decimal_or_zero(_first(item, "can_sell_qty", default="0")),
            average_price=decimal_or_zero(_first(item, "cost_price", default="0")),
            market_price=decimal_or_zero(_first(item, "nominal_price", default="0")),
            market_value=decimal_or_zero(_first(item, "market_val", default="0")),
            unrealized_pnl=decimal_or_zero(_first(item, "pl_val", default="0")),
            raw_method=method,
            raw_result_code=str(raw.get("ret", "")),
            warnings=_warnings(raw),
        )
        for item in _data_list(raw)
    ]


def _normalize_orders(payload: Mapping[str, Any], metadata: Mapping[str, Any]) -> list[BrokerOrderSnapshot]:
    orders: list[BrokerOrderSnapshot] = []
    for method in ("order_list_query", "history_order_list_query"):
        raw = _method_payload(payload, method)
        for item in _data_list(raw):
            quantity = decimal_or_zero(_first(item, "qty", default="0"))
            executed_quantity = decimal_or_zero(_first(item, "dealt_qty", default="0"))
            orders.append(
                BrokerOrderSnapshot(
                    broker="moomoo",
                    source=_source(metadata),
                    as_of=_as_of(metadata),
                    order_id=str(_first(item, "order_id", default="") or ""),
                    issue_code=_normalize_issue_code(str(_first(item, "code", default="") or "")),
                    issue_name=str(_first(item, "stock_name", default="") or ""),
                    side=_normalize_side(_first(item, "trd_side", default="")),
                    order_type=str(_first(item, "order_type", default="") or ""),
                    quantity=quantity,
                    executed_quantity=executed_quantity,
                    remaining_quantity=max(quantity - executed_quantity, decimal_or_zero("0")),
                    price=decimal_or_zero(_first(item, "price", default="0")),
                    status=str(_first(item, "order_status", default="") or ""),
                    order_datetime=str(_first(item, "create_time", default="") or ""),
                    expire_date="",
                    raw_method=method,
                    raw_result_code=str(raw.get("ret", "")),
                    warnings=_warnings(raw),
                )
            )
    return orders


def _normalize_executions_from_orders(
    orders: list[BrokerOrderSnapshot], metadata: Mapping[str, Any]
) -> list[BrokerExecutionSnapshot]:
    executions: list[BrokerExecutionSnapshot] = []
    for order in orders:
        if order.executed_quantity <= 0:
            continue
        executions.append(
            BrokerExecutionSnapshot(
                broker="moomoo",
                source=_source(metadata),
                as_of=_as_of(metadata),
                execution_id=f"exec_{order.order_id}",
                order_id=order.order_id,
                issue_code=order.issue_code,
                issue_name=order.issue_name,
                side=order.side,
                quantity=order.executed_quantity,
                price=order.price,
                executed_at=order.order_datetime,
                currency="JPY",
                raw_method=order.raw_method,
                raw_result_code=order.raw_result_code,
                warnings=order.warnings,
            )
        )
    return executions


def _method_payload(payload: Mapping[str, Any], method: str) -> Mapping[str, Any]:
    value = payload.get(method, {})
    return value if isinstance(value, Mapping) else {}


def _data_mapping(raw: Mapping[str, Any]) -> Mapping[str, Any]:
    value = raw.get("data", {})
    if isinstance(value, Mapping):
        return value
    if isinstance(value, list) and value and isinstance(value[0], Mapping):
        return value[0]
    return {}


def _data_list(raw: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    value = raw.get("data", [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _first(data: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return default


def _as_of(metadata: Mapping[str, Any]) -> str:
    value = metadata.get("as_of")
    return str(value) if value else utc_now_iso()


def _source(metadata: Mapping[str, Any]) -> str:
    return str(metadata.get("source") or "mock")


def _account_ref(item: Mapping[str, Any], metadata: Mapping[str, Any]) -> str:
    alias = _first(item, "account_ref", default=metadata.get("account_ref", ""))
    if alias:
        return str(alias)
    raw_id = _first(item, "acc_id", "card_num", "uni_card_num", "account_number", default="")
    if raw_id:
        return f"acct_hash_{hash_account_id(str(raw_id))}"
    return ""


def _warnings(raw: Mapping[str, Any], extra: tuple[str, ...] = ()) -> tuple[str, ...]:
    warnings = list(extra)
    if raw.get("ret") not in (None, "", "OK"):
        warnings.append(f"ret={raw.get('ret')}")
    return tuple(warnings)


def _normalize_issue_code(value: str) -> str:
    return value.split(".", 1)[1] if "." in value else value


def _normalize_side(value: Any) -> str:
    return {"BUY": "buy", "SELL": "sell"}.get(str(value or "").upper(), str(value or "").lower())
