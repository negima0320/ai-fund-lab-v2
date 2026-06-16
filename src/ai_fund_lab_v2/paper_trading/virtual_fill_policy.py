from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping


FILL_POLICY_ID = "next_business_day_open_v1"

NO_FILL_REASONS = {
    "OPEN_PRICE_MISSING",
    "TRADING_HALTED",
    "LIMIT_UP_BUY",
    "LIMIT_DOWN_SELL",
    "PRICE_ABNORMAL",
    "DAILY_QUOTE_MISSING",
    "LISTED_INFO_NOT_TRADABLE",
    "LOT_SIZE_INVALID",
    "CASH_INSUFFICIENT",
    "SELL_QUANTITY_INSUFFICIENT",
    "SELL_DEPENDENCY_NOT_FILLED",
    "SAFETY_LOCKED",
}


@dataclass(frozen=True)
class VirtualFillPolicy:
    fill_policy: str = FILL_POLICY_ID
    buy_price_source: str = "virtual_execution_date_open"
    sell_price_source: str = "virtual_execution_date_open"
    slippage: Decimal = Decimal("0")
    commission: Decimal = Decimal("0")
    partial_fill_supported: bool = False
    lot_size: int = 100

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["slippage"] = str(self.slippage)
        payload["commission"] = str(self.commission)
        return payload


def resolve_open_price(
    *,
    code: str,
    execution_date: str,
    quote_rows: list[Mapping[str, Any]],
    side: str,
) -> tuple[Decimal | None, str]:
    matches = [row for row in quote_rows if _record_date(row) == execution_date and str(_value(row, "code") or "") == code]
    if not matches:
        return None, "DAILY_QUOTE_MISSING"
    row = matches[0]
    if _truthy(row.get("trading_halted") or row.get("TradingHalted") or row.get("halted")):
        return None, "TRADING_HALTED"
    if side.upper() == "BUY" and _truthy(row.get("limit_up") or row.get("LimitUp")):
        return None, "LIMIT_UP_BUY"
    if side.upper() == "SELL" and _truthy(row.get("limit_down") or row.get("LimitDown")):
        return None, "LIMIT_DOWN_SELL"
    value = _value(row, "open")
    if value in (None, ""):
        return None, "OPEN_PRICE_MISSING"
    try:
        price = Decimal(str(value).replace(",", ""))
    except Exception:
        return None, "PRICE_ABNORMAL"
    if price <= 0:
        return None, "PRICE_ABNORMAL"
    return price, ""


def _record_date(record: Mapping[str, Any]) -> str:
    return str(_value(record, "date") or "")


def _value(record: Mapping[str, Any], normalized_name: str) -> Any:
    aliases = {
        "date": ("date", "Date", "target_date"),
        "code": ("code", "Code", "business_key"),
        "open": ("open", "Open", "O", "AdjO"),
    }
    for key in aliases[normalized_name]:
        if key in record:
            return record.get(key)
    return None


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "halted"}

