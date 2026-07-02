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
DEMO_ORDER_CLMIDS: frozenset[str] = frozenset({"CLMKabuNewOrder"})


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


def ensure_demo_order_clmid(
    clmid: str | None,
    *,
    environment: str,
    base_url: str,
    demo_base_url: str,
    demo_order_wire_execution: bool,
    production_order_allowed: bool,
) -> str:
    if not clmid:
        raise BrokerAllowlistError("Broker order request is missing sCLMID.")
    if clmid not in DEMO_ORDER_CLMIDS:
        raise BrokerAllowlistError(f"Broker CLMID {clmid} is not in the demo order allowlist.")
    if environment != "demo":
        raise BrokerAllowlistError("Demo order CLMID requires demo environment.")
    if base_url.rstrip("/") != demo_base_url.rstrip("/"):
        raise BrokerAllowlistError("Demo order CLMID requires demo base URL.")
    if not demo_order_wire_execution:
        raise BrokerAllowlistError("Demo order wire execution flag is false.")
    if production_order_allowed:
        raise BrokerAllowlistError("Production order flag must be false for demo order CLMID.")
    return clmid
