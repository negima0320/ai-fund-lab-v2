from __future__ import annotations

READ_ONLY_CLMIDS: frozenset[str] = frozenset(
    {
        "CLMAuthLoginRequest",
        "CLMAuthLogoutRequest",
        "CLMZanKaiSummary",
        "CLMZanKaiKanougaku",
        "CLMGenbutuKabuList",
        "CLMShinyouTategyokuList",
        "CLMOrderList",
        "CLMOrderListDetail",
        "CLMMfdsGetMarketPrice",
        "CLMMfdsGetMarketPriceHistory",
    }
)

FORBIDDEN_CLMIDS: frozenset[str] = frozenset(
    {
        "CLMKabuNewOrder",
        "CLMKabuCorrectOrder",
        "CLMKabuCancelOrder",
        "CLMKabuCancelOrderAll",
        "CLMAuthCheckSecondPassword",
        "CLMAuthStkLoginRequest",
    }
)
FORBIDDEN_ORDER_CLMIDS = FORBIDDEN_CLMIDS


class BrokerAllowlistError(RuntimeError):
    """Raised when a broker CLMID is not allowed in the current phase."""


def is_read_only_clmid(clmid: str | None) -> bool:
    return bool(clmid and clmid in READ_ONLY_CLMIDS)


def ensure_read_only_clmid(clmid: str | None) -> str:
    if not clmid:
        raise BrokerAllowlistError("Broker request is missing sCLMID.")
    if clmid in FORBIDDEN_CLMIDS:
        raise BrokerAllowlistError(f"Broker CLMID {clmid} is forbidden in Phase10-C.")
    if clmid not in READ_ONLY_CLMIDS:
        raise BrokerAllowlistError(f"Broker CLMID {clmid} is not in the Phase10 read-only allowlist.")
    return clmid
