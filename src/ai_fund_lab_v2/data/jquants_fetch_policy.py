from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PAGINATION_KEY = "pagination_key"

JQUANTS_DAILY_QUOTES_ENDPOINT = "/v2/equities/bars/daily"
JQUANTS_LISTED_ISSUES_ENDPOINT = "/v2/equities/master"
JQUANTS_EARNINGS_CALENDAR_ENDPOINT = "/v2/equities/earnings-calendar"
JQUANTS_TRADING_CALENDAR_ENDPOINT = "/v2/markets/calendar"
JQUANTS_FINS_SUMMARY_ENDPOINT = "/v2/fins/summary"

RETRYABLE = "retryable"
AUTH_ERROR = "auth_error"
REQUEST_ERROR = "request_error"
FATAL = "fatal"


@dataclass(frozen=True)
class EndpointCapability:
    endpoint: str
    supports_date: bool
    supports_from_to: bool
    supports_code: bool
    supports_pagination: bool
    prefer_range_fetch: bool

    def to_manifest(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "supports_date": self.supports_date,
            "supports_from_to": self.supports_from_to,
            "supports_code": self.supports_code,
            "supports_pagination": self.supports_pagination,
            "prefer_range_fetch": self.prefer_range_fetch,
        }


@dataclass(frozen=True)
class JQuantsRateLimitPolicy:
    max_requests_per_minute: int = 60
    window_seconds: float = 60.0
    retry_after_rate_limit_seconds: float = 60.0

    def wait_seconds(self, request_timestamps: list[float], now: float) -> float:
        active = self.active_timestamps(request_timestamps, now)
        if len(active) < max(self.max_requests_per_minute, 1):
            return 0.0
        oldest = min(active)
        return max((oldest + self.window_seconds) - now, 0.0)

    def active_timestamps(self, request_timestamps: list[float], now: float) -> list[float]:
        start = now - self.window_seconds
        return [timestamp for timestamp in request_timestamps if timestamp > start]

    def to_manifest(self) -> dict[str, Any]:
        return {
            "max_requests_per_minute": self.max_requests_per_minute,
            "window_seconds": self.window_seconds,
            "fixed_sleep_per_request": False,
            "wait_policy": "rolling_window_wait_only_when_limit_would_be_exceeded",
            "retry_after_rate_limit_seconds": self.retry_after_rate_limit_seconds,
        }


@dataclass
class RateLimitState:
    policy: JQuantsRateLimitPolicy
    timestamps: list[float] = field(default_factory=list)

    def seconds_until_available(self, now: float) -> float:
        self.timestamps = self.policy.active_timestamps(self.timestamps, now)
        return self.policy.wait_seconds(self.timestamps, now)

    def record_request(self, timestamp: float) -> None:
        self.timestamps = self.policy.active_timestamps(self.timestamps, timestamp)
        self.timestamps.append(timestamp)


@dataclass(frozen=True)
class RetryDecision:
    retryable: bool
    category: str
    wait_seconds: float
    reason: str


@dataclass(frozen=True)
class JQuantsRetryPolicy:
    max_attempts: int = 2
    retry_wait_seconds: float = 0.0
    retry_after_rate_limit_seconds: float = 60.0

    def classify_status(self, status: int | str) -> RetryDecision:
        if status == 429:
            return RetryDecision(True, RETRYABLE, self.retry_after_rate_limit_seconds, "rate_limit")
        if status in (401, 403):
            return RetryDecision(False, AUTH_ERROR, 0.0, "credential_or_auth_error")
        if status == 400:
            return RetryDecision(False, REQUEST_ERROR, 0.0, "bad_request_or_out_of_range")
        if isinstance(status, int) and 500 <= status <= 599:
            return RetryDecision(True, RETRYABLE, self.retry_wait_seconds, "server_error")
        if status in {"timeout", "url_error"}:
            return RetryDecision(True, RETRYABLE, self.retry_wait_seconds, str(status))
        return RetryDecision(False, FATAL, 0.0, "non_retryable")

    def should_retry(self, status: int | str, attempt: int) -> RetryDecision:
        decision = self.classify_status(status)
        if attempt >= self.max_attempts:
            return RetryDecision(False, decision.category, 0.0, f"{decision.reason}_max_attempts_reached")
        return decision

    def to_manifest(self) -> dict[str, Any]:
        return {
            "max_attempts": self.max_attempts,
            "retryable_statuses": [429, "5xx", "timeout", "url_error"],
            "auth_error_statuses": [401, 403],
            "non_retryable_statuses": [400],
            "rate_limit_retry_wait_seconds": self.retry_after_rate_limit_seconds,
            "server_error_retry_wait_seconds": self.retry_wait_seconds,
            "secret_safe_errors": True,
        }


ENDPOINT_CAPABILITIES: dict[str, EndpointCapability] = {
    JQUANTS_DAILY_QUOTES_ENDPOINT: EndpointCapability(
        endpoint=JQUANTS_DAILY_QUOTES_ENDPOINT,
        supports_date=True,
        supports_from_to=True,
        supports_code=True,
        supports_pagination=True,
        prefer_range_fetch=True,
    ),
    JQUANTS_LISTED_ISSUES_ENDPOINT: EndpointCapability(
        endpoint=JQUANTS_LISTED_ISSUES_ENDPOINT,
        supports_date=True,
        supports_from_to=False,
        supports_code=True,
        supports_pagination=True,
        prefer_range_fetch=False,
    ),
    JQUANTS_EARNINGS_CALENDAR_ENDPOINT: EndpointCapability(
        endpoint=JQUANTS_EARNINGS_CALENDAR_ENDPOINT,
        supports_date=False,
        supports_from_to=False,
        supports_code=False,
        supports_pagination=True,
        prefer_range_fetch=False,
    ),
    JQUANTS_TRADING_CALENDAR_ENDPOINT: EndpointCapability(
        endpoint=JQUANTS_TRADING_CALENDAR_ENDPOINT,
        supports_date=True,
        supports_from_to=True,
        supports_code=False,
        supports_pagination=True,
        prefer_range_fetch=True,
    ),
    JQUANTS_FINS_SUMMARY_ENDPOINT: EndpointCapability(
        endpoint=JQUANTS_FINS_SUMMARY_ENDPOINT,
        supports_date=True,
        supports_from_to=False,
        supports_code=True,
        supports_pagination=True,
        prefer_range_fetch=False,
    ),
}


def endpoint_capability(endpoint: str) -> EndpointCapability:
    if endpoint not in ENDPOINT_CAPABILITIES:
        return EndpointCapability(
            endpoint=endpoint,
            supports_date=True,
            supports_from_to=False,
            supports_code=False,
            supports_pagination=True,
            prefer_range_fetch=False,
        )
    return ENDPOINT_CAPABILITIES[endpoint]


def choose_fetch_strategy(endpoint: str, *, from_date: str | None = None, to_date: str | None = None) -> str:
    capability = endpoint_capability(endpoint)
    if capability.supports_from_to and capability.prefer_range_fetch and from_date and to_date:
        return "range_fetch"
    return "date_by_date"


def build_endpoint_params(
    endpoint: str,
    *,
    date: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    code: str | None = None,
    pagination_key: str | None = None,
) -> dict[str, str]:
    capability = endpoint_capability(endpoint)
    params: dict[str, str] = {}
    if date and capability.supports_date:
        params["date"] = date
    if from_date and capability.supports_from_to:
        params["from"] = from_date
    if to_date and capability.supports_from_to:
        params["to"] = to_date
    if code and capability.supports_code:
        params["code"] = code
    if pagination_key and capability.supports_pagination:
        params[PAGINATION_KEY] = pagination_key
    return params


def classify_http_status(status: int | str) -> str:
    return JQuantsRetryPolicy().classify_status(status).category


def endpoint_capability_manifest(endpoint: str) -> dict[str, Any]:
    return endpoint_capability(endpoint).to_manifest()


def jquants_common_policy_manifest(
    *,
    endpoint: str,
    rate_limit_per_minute: int = 60,
    max_attempts: int = 2,
) -> dict[str, Any]:
    return {
        "rate_limit_policy": JQuantsRateLimitPolicy(max_requests_per_minute=rate_limit_per_minute).to_manifest(),
        "retry_policy": JQuantsRetryPolicy(max_attempts=max_attempts).to_manifest(),
        "endpoint_capability": endpoint_capability_manifest(endpoint),
    }
