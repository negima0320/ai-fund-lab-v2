from __future__ import annotations

from dataclasses import dataclass

from ai_fund_lab_v2.broker.request_builder import BrokerSessionContext, TachibanaRequestBuilder
from ai_fund_lab_v2.broker.response import BrokerResponseEnvelope
from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.broker.transport import BrokerTransport


@dataclass(frozen=True)
class TachibanaReadOnlyClient:
    settings: BrokerSettings
    transport: BrokerTransport
    builder: TachibanaRequestBuilder | None = None

    @property
    def request_builder(self) -> TachibanaRequestBuilder:
        return self.builder or TachibanaRequestBuilder(self.settings)

    def build_login_request(self) -> dict:
        return self.request_builder.login()

    def build_logout_request(self, session: BrokerSessionContext | None = None) -> dict:
        return self.request_builder.logout(session)

    def get_balance_summary(self) -> BrokerResponseEnvelope:
        return self._request(self.request_builder.balance_summary())

    def get_buying_power(self) -> BrokerResponseEnvelope:
        return self._request(self.request_builder.buying_power())

    def get_cash_positions(self, issue_code: str = "") -> BrokerResponseEnvelope:
        return self._request(self.request_builder.cash_positions(issue_code=issue_code))

    def get_margin_positions(self, issue_code: str = "") -> BrokerResponseEnvelope:
        return self._request(self.request_builder.margin_positions(issue_code=issue_code))

    def get_order_list(self, issue_code: str = "", execution_day: str = "", order_status: str = "") -> BrokerResponseEnvelope:
        return self._request(
            self.request_builder.order_list(issue_code=issue_code, execution_day=execution_day, order_status=order_status)
        )

    def get_order_list_detail(self, issue_code: str = "", execution_day: str = "", order_status: str = "") -> BrokerResponseEnvelope:
        return self._request(
            self.request_builder.order_list_detail(issue_code=issue_code, execution_day=execution_day, order_status=order_status)
        )

    def _request(self, payload: dict) -> BrokerResponseEnvelope:
        return BrokerResponseEnvelope(self.transport.request(payload))
