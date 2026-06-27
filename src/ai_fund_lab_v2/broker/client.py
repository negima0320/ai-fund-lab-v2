from __future__ import annotations

from dataclasses import dataclass

from ai_fund_lab_v2.broker.request_builder import BrokerSessionContext, TachibanaRequestBuilder
from ai_fund_lab_v2.broker.response import BrokerResponseEnvelope
from ai_fund_lab_v2.broker.session import TachibanaSession, UrlDecryptor, normalize_login_ack
from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.broker.transport import BrokerTransport


@dataclass(frozen=True)
class TachibanaReadOnlyClient:
    settings: BrokerSettings
    transport: BrokerTransport
    builder: TachibanaRequestBuilder | None = None

    def __post_init__(self) -> None:
        if self.builder is None:
            object.__setattr__(self, "builder", TachibanaRequestBuilder(self.settings))

    @property
    def request_builder(self) -> TachibanaRequestBuilder:
        if self.builder is None:
            raise RuntimeError("Tachibana request builder was not initialized.")
        return self.builder

    def build_login_request(self) -> dict:
        return self.request_builder.login()

    def build_logout_request(self, session: BrokerSessionContext | None = None) -> dict:
        return self.request_builder.logout(session)

    def login(self, *, decrypt_url: UrlDecryptor) -> TachibanaSession:
        response = self._request(self.build_login_request())
        return normalize_login_ack(response, environment=self.settings.environment, decrypt_url=decrypt_url)

    def logout(self, session: TachibanaSession, *, transport: BrokerTransport | None = None) -> BrokerResponseEnvelope:
        _ = session
        selected_transport = transport or self.transport
        return BrokerResponseEnvelope(selected_transport.request(self.build_logout_request()))

    def get_balance_summary(self) -> BrokerResponseEnvelope:
        return self._request(self.request_builder.balance_summary())

    def get_account_summary(self) -> BrokerResponseEnvelope:
        return self.get_balance_summary()

    def get_buying_power(self) -> BrokerResponseEnvelope:
        return self._request(self.request_builder.buying_power())

    def get_available_cash(self) -> BrokerResponseEnvelope:
        return self.get_buying_power()

    def get_cash_positions(self, issue_code: str = "") -> BrokerResponseEnvelope:
        return self._request(self.request_builder.cash_positions(issue_code=issue_code))

    def get_margin_positions(self, issue_code: str = "") -> BrokerResponseEnvelope:
        return self._request(self.request_builder.margin_positions(issue_code=issue_code))

    def get_positions(self, issue_code: str = "") -> tuple[BrokerResponseEnvelope, BrokerResponseEnvelope]:
        return (self.get_cash_positions(issue_code=issue_code), self.get_margin_positions(issue_code=issue_code))

    def get_order_list(self, issue_code: str = "", execution_day: str = "", order_status: str = "") -> BrokerResponseEnvelope:
        return self._request(
            self.request_builder.order_list(issue_code=issue_code, execution_day=execution_day, order_status=order_status)
        )

    def get_orders(self, issue_code: str = "", execution_day: str = "", order_status: str = "") -> BrokerResponseEnvelope:
        return self.get_order_list(issue_code=issue_code, execution_day=execution_day, order_status=order_status)

    def get_order_list_detail(self, order_number: str = "") -> BrokerResponseEnvelope:
        return self._request(self.request_builder.order_list_detail(order_number=order_number))

    def get_order_detail(self, order_number: str) -> BrokerResponseEnvelope:
        return self.get_order_list_detail(order_number=order_number)

    def get_executions_history(self, order_number: str) -> BrokerResponseEnvelope:
        return self.get_order_detail(order_number=order_number)

    def get_market_price(self, issue_codes: list[str], columns: str | None = None) -> BrokerResponseEnvelope:
        return self._request(self.request_builder.quote(issue_codes, columns=columns))

    def get_quotes(self, issue_codes: list[str], columns: str | None = None) -> BrokerResponseEnvelope:
        return self.get_market_price(issue_codes, columns=columns)

    def _request(self, payload: dict) -> BrokerResponseEnvelope:
        return BrokerResponseEnvelope(self.transport.request(payload))
