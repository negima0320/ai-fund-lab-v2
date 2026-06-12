from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ai_fund_lab_v2.broker.allowlist import ensure_read_only_clmid
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping


class BrokerTransport(Protocol):
    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...


class BrokerTransportError(RuntimeError):
    """Raised when broker transport cannot return a response."""


@dataclass
class MockBrokerTransport:
    responses: dict[str, dict[str, Any]] = field(default_factory=dict)
    requests: list[dict[str, Any]] = field(default_factory=list)

    def register_response(self, clmid: str, response: dict[str, Any]) -> None:
        ensure_read_only_clmid(clmid)
        self.responses[clmid] = dict(response)

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        clmid = ensure_read_only_clmid(str(payload.get("sCLMID") or ""))
        self.requests.append(sanitize_mapping(payload))
        if clmid not in self.responses:
            raise BrokerTransportError(f"No mock response registered for broker CLMID {clmid}.")
        return dict(self.responses[clmid])
