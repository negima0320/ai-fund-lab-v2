from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ai_fund_lab_v2.broker.allowlist import ensure_read_only_clmid
from ai_fund_lab_v2.broker.request_sequence import RequestSequenceManager
from ai_fund_lab_v2.broker.settings import BrokerSettings


@dataclass(frozen=True)
class BrokerSessionContext:
    request_url: str | None = None

    def __repr__(self) -> str:
        return "BrokerSessionContext(request_url=[SET])" if self.request_url else "BrokerSessionContext(request_url=[MISSING])"


@dataclass(frozen=True)
class TachibanaRequestBuilder:
    settings: BrokerSettings
    sequence_no: int = 0
    sequence_manager: RequestSequenceManager | None = None

    def __post_init__(self) -> None:
        if self.sequence_manager is None:
            object.__setattr__(self, "sequence_manager", RequestSequenceManager(self.sequence_no))

    def __repr__(self) -> str:
        return f"TachibanaRequestBuilder(settings={self.settings!r})"

    def build(self, clmid: str, **params: Any) -> dict[str, Any]:
        ensure_read_only_clmid(clmid)
        payload = {"p_no": self._next_no(), "p_sd_date": _tachibana_datetime(), "sCLMID": clmid}
        payload.update({key: value for key, value in params.items() if value is not None})
        return payload

    def login(self) -> dict[str, Any]:
        return self.build("CLMAuthLoginRequest", sAuthId=self.settings.require_auth_id())

    def logout(self, session: BrokerSessionContext | None = None) -> dict[str, Any]:
        _ = session
        return self.build("CLMAuthLogoutRequest")

    def balance_summary(self) -> dict[str, Any]:
        return self.build("CLMZanKaiSummary")

    def buying_power(self) -> dict[str, Any]:
        return self.build("CLMZanKaiKanougaku", sIssueCode="", sSizyouC="")

    def cash_positions(self, issue_code: str = "") -> dict[str, Any]:
        return self.build("CLMGenbutuKabuList", sIssueCode=issue_code)

    def margin_positions(self, issue_code: str = "") -> dict[str, Any]:
        return self.build("CLMShinyouTategyokuList", sIssueCode=issue_code)

    def order_list(self, issue_code: str = "", execution_day: str = "", order_status: str = "") -> dict[str, Any]:
        return self.build(
            "CLMOrderList",
            sIssueCode=issue_code,
            sSikkouDay=execution_day,
            sOrderSyoukaiStatus=order_status,
        )

    def order_list_detail(self, order_number: str = "") -> dict[str, Any]:
        return self.build(
            "CLMOrderListDetail",
            sOrderNumber=order_number,
        )

    def quote(self, issue_codes: list[str], columns: str | None = None) -> dict[str, Any]:
        if not issue_codes:
            raise ValueError("issue_codes is required for CLMMfdsGetMarketPrice.")
        if len(issue_codes) > self.settings.quote_symbol_limit:
            raise ValueError("issue_codes exceeds TACHIBANA_API_QUOTE_SYMBOL_LIMIT.")
        return self.build(
            "CLMMfdsGetMarketPrice",
            sTargetIssueCode=",".join(issue_codes),
            sTargetColumn=columns or self.settings.quote_columns,
        )

    def market_price_history(self, issue_code: str) -> dict[str, Any]:
        if not issue_code:
            raise ValueError("issue_code is required for CLMMfdsGetMarketPriceHistory.")
        return self.build("CLMMfdsGetMarketPriceHistory", sIssueCode=issue_code)

    def _next_no(self) -> int:
        if self.sequence_manager is None:
            object.__setattr__(self, "sequence_manager", RequestSequenceManager(self.sequence_no))
        value = self.sequence_manager.next_no()
        object.__setattr__(self, "sequence_no", value)
        return value


def _tachibana_datetime() -> str:
    now = datetime.now()
    return now.strftime("%Y.%m.%d-%H:%M:%S.") + f"{now.microsecond // 1000:03d}"
