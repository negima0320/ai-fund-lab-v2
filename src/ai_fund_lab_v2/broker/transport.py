from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Literal
from typing import Any, Protocol
from urllib import error, request

from ai_fund_lab_v2.broker.allowlist import ensure_demo_order_clmid, ensure_read_only_clmid
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping, sanitize_text
from ai_fund_lab_v2.broker.settings import DEMO_BASE_URL, BrokerSettings
from ai_fund_lab_v2.broker.tachibana_codec import TachibanaCodec


class BrokerTransport(Protocol):
    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...


class BrokerTransportError(RuntimeError):
    """Raised when broker transport cannot return a response."""


TransportBodyMode = Literal["json_body", "form_urlencoded_json_string", "text_plain_json"]


@dataclass
class RateLimiter:
    rate_limit_per_second: float
    _last_request_at: float = 0.0

    def wait(self) -> None:
        if self.rate_limit_per_second <= 0:
            return
        min_interval = 1.0 / self.rate_limit_per_second
        now = time.monotonic()
        wait_seconds = self._last_request_at + min_interval - now
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        self._last_request_at = time.monotonic()


@dataclass
class HttpPostBrokerTransport:
    endpoint_url: str
    timeout_seconds: float = 30.0
    rate_limit_per_second: float = 5.0
    user_agent: str = "ai-fund-lab-v2-tachibana-readonly/phase10c"
    rate_limiter: RateLimiter | None = None
    codec: TachibanaCodec | None = None
    body_mode: TransportBodyMode = "json_body"

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        ensure_read_only_clmid(str(payload.get("sCLMID") or ""))
        if self.rate_limiter is None:
            self.rate_limiter = RateLimiter(self.rate_limit_per_second)
        limiter = self.rate_limiter
        limiter.wait()
        encoded_payload = self.codec.encode_request(payload) if self.codec is not None else payload
        body, content_type = self._serialize_body(encoded_payload)
        req = request.Request(
            self.endpoint_url,
            data=body,
            headers={
                "Content-Type": content_type,
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw_text = _decode_response_bytes(response.read())
        except (error.URLError, TimeoutError, OSError) as exc:
            raise BrokerTransportError(f"Broker HTTP POST failed: {sanitize_text(str(exc))}") from exc
        try:
            decoded = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise BrokerTransportError(f"Broker HTTP POST returned invalid JSON: {sanitize_text(raw_text)}") from exc
        if not isinstance(decoded, dict):
            raise BrokerTransportError("Broker HTTP POST returned non-object JSON.")
        decoded_payload = dict(decoded)
        if self.codec is not None:
            decoded_payload = self.codec.decode_response(decoded_payload)
        return decoded_payload

    def diagnose_post_shape(self, payload: dict[str, Any], *, endpoint_type: str) -> dict[str, Any]:
        encoded_payload = self.codec.encode_request(payload) if self.codec is not None else payload
        body, content_type = self._serialize_body(encoded_payload)
        return sanitize_mapping(
            {
                "endpoint_type": endpoint_type,
                "method": "POST",
                "body_mode": self.body_mode,
                "content_type": content_type,
                "json_post": self.body_mode == "json_body",
                "form_post": self.body_mode == "form_urlencoded_json_string",
                "text_plain_post": self.body_mode == "text_plain_json",
                "payload_compressed": self.codec is not None,
                "encoded_payload_key_count": len(encoded_payload),
                "encoded_payload_keys": sorted(str(key) for key in encoded_payload.keys()),
                "body_byte_length_bucket": _length_bucket(len(body)),
                "header_names": ["Accept", "Content-Type", "User-Agent"],
                "body_values_saved": False,
            }
        )

    def _serialize_body(self, encoded_payload: dict[str, Any]) -> tuple[bytes, str]:
        text = json.dumps(encoded_payload, ensure_ascii=False)
        if self.body_mode == "json_body":
            return text.encode("utf-8"), "application/json; charset=utf-8"
        if self.body_mode == "form_urlencoded_json_string":
            return text.encode("utf-8"), "application/x-www-form-urlencoded; charset=UTF-8"
        if self.body_mode == "text_plain_json":
            return text.encode("utf-8"), "text/plain; charset=utf-8"
        raise BrokerTransportError("Unsupported Tachibana POST body mode.")


@dataclass
class DemoOrderBrokerTransport:
    endpoint_url: str
    settings: BrokerSettings
    demo_order_wire_execution: bool
    production_order_allowed: bool = False
    timeout_seconds: float = 30.0
    rate_limit_per_second: float = 5.0
    user_agent: str = "ai-fund-lab-v2-tachibana-demo-order/phase12o"
    rate_limiter: RateLimiter | None = None
    codec: TachibanaCodec | None = None
    body_mode: TransportBodyMode = "json_body"

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        ensure_demo_order_clmid(
            str(payload.get("sCLMID") or ""),
            environment=self.settings.environment,
            base_url=self.settings.base_url,
            demo_base_url=DEMO_BASE_URL,
            demo_order_wire_execution=self.demo_order_wire_execution,
            production_order_allowed=self.production_order_allowed,
        )
        if self.rate_limiter is None:
            self.rate_limiter = RateLimiter(self.rate_limit_per_second)
        self.rate_limiter.wait()
        encoded_payload = self._encode_order_payload(payload)
        body, content_type = self._serialize_body(encoded_payload)
        req = request.Request(
            self.endpoint_url,
            data=body,
            headers={
                "Content-Type": content_type,
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw_text = _decode_response_bytes(response.read())
        except (error.URLError, TimeoutError, OSError) as exc:
            raise BrokerTransportError(f"Demo broker order POST failed: {sanitize_text(str(exc))}") from exc
        try:
            decoded = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise BrokerTransportError(f"Demo broker order POST returned invalid JSON: {sanitize_text(raw_text)}") from exc
        if not isinstance(decoded, dict):
            raise BrokerTransportError("Demo broker order POST returned non-object JSON.")
        decoded_payload = dict(decoded)
        if self.codec is not None:
            decoded_payload = self.codec.decode_response(decoded_payload)
        return decoded_payload

    def _encode_order_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.codec.encode_request(payload) if self.codec is not None else dict(payload)

    def _serialize_body(self, encoded_payload: dict[str, Any]) -> tuple[bytes, str]:
        text = json.dumps(encoded_payload, ensure_ascii=False)
        if self.body_mode == "json_body":
            return text.encode("utf-8"), "application/json; charset=utf-8"
        if self.body_mode == "form_urlencoded_json_string":
            return text.encode("utf-8"), "application/x-www-form-urlencoded; charset=UTF-8"
        if self.body_mode == "text_plain_json":
            return text.encode("utf-8"), "text/plain; charset=utf-8"
        raise BrokerTransportError("Unsupported Tachibana POST body mode.")


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


def _decode_response_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "cp932", "shift_jis"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise BrokerTransportError("Broker HTTP POST returned text with an unsupported encoding.")


def _length_bucket(length: int) -> str:
    if length == 0:
        return "empty"
    if length <= 128:
        return "small"
    if length <= 1024:
        return "medium"
    return "large"
