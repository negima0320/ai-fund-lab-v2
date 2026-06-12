from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_fund_lab_v2.broker.allowlist import ensure_read_only_clmid
from ai_fund_lab_v2.broker.settings import BrokerSettings


@dataclass(frozen=True)
class BrokerSessionContext:
    request_url: str | None = None

    def __repr__(self) -> str:
        return "BrokerSessionContext(request_url=[SET])" if self.request_url else "BrokerSessionContext(request_url=[MISSING])"


@dataclass(frozen=True)
class TachibanaRequestBuilder:
    settings: BrokerSettings

    def __repr__(self) -> str:
        return f"TachibanaRequestBuilder(settings={self.settings!r})"

    def build(self, clmid: str, **params: Any) -> dict[str, Any]:
        ensure_read_only_clmid(clmid)
        payload = {"sCLMID": clmid}
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

    def order_list_detail(self, issue_code: str = "", execution_day: str = "", order_status: str = "") -> dict[str, Any]:
        return self.build(
            "CLMOrderListDetail",
            sIssueCode=issue_code,
            sSikkouDay=execution_day,
            sOrderSyoukaiStatus=order_status,
        )
