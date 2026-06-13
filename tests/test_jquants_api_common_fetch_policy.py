from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest

from ai_fund_lab_v2.config import JQuantsSettings
from ai_fund_lab_v2.data.jquants_fetch_policy import (
    AUTH_ERROR,
    JQUANTS_DAILY_QUOTES_ENDPOINT,
    JQUANTS_FINS_SUMMARY_ENDPOINT,
    JQUANTS_TRADING_CALENDAR_ENDPOINT,
    JQuantsRateLimitPolicy,
    JQuantsRetryPolicy,
    RateLimitState,
    build_endpoint_params,
    choose_fetch_strategy,
    classify_http_status,
    endpoint_capability,
    jquants_common_policy_manifest,
)
from ai_fund_lab_v2.data_sources.jquants import JQuantsClient, JQuantsClientError
from ai_fund_lab_v2.runtime import RuntimePaths


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_rate_limit_policy_does_not_sleep_until_minute_window_is_full() -> None:
    policy = JQuantsRateLimitPolicy(max_requests_per_minute=60)
    state = RateLimitState(policy)

    for index in range(59):
        state.record_request(float(index))

    assert state.seconds_until_available(59.1) == 0.0

    state.record_request(59.2)
    assert state.seconds_until_available(59.3) > 0.0


def test_rate_limit_state_resumes_after_window_rolls_forward() -> None:
    state = RateLimitState(JQuantsRateLimitPolicy(max_requests_per_minute=2, window_seconds=60.0))
    state.record_request(0.0)
    state.record_request(10.0)

    assert state.seconds_until_available(10.1) > 0.0
    assert state.seconds_until_available(60.1) == 0.0


def test_retry_policy_classifies_statuses() -> None:
    policy = JQuantsRetryPolicy(max_attempts=2)

    assert policy.classify_status(429).retryable is True
    assert policy.classify_status(429).wait_seconds == 60.0
    assert policy.classify_status(500).retryable is True
    assert policy.classify_status(400).retryable is False
    assert policy.classify_status(400).category == "request_error"
    assert policy.classify_status(401).category == AUTH_ERROR
    assert policy.classify_status(403).category == AUTH_ERROR
    assert classify_http_status(500) == "retryable"


def test_endpoint_capability_and_range_strategy() -> None:
    daily = endpoint_capability(JQUANTS_DAILY_QUOTES_ENDPOINT)
    calendar = endpoint_capability(JQUANTS_TRADING_CALENDAR_ENDPOINT)
    fins = endpoint_capability(JQUANTS_FINS_SUMMARY_ENDPOINT)

    assert daily.supports_date is True
    assert daily.supports_from_to is True
    assert daily.supports_pagination is True
    assert choose_fetch_strategy(JQUANTS_DAILY_QUOTES_ENDPOINT, from_date="2026-01-01", to_date="2026-01-31") == "range_fetch"
    assert calendar.prefer_range_fetch is True
    assert choose_fetch_strategy(JQUANTS_TRADING_CALENDAR_ENDPOINT, from_date="2026-01-01", to_date="2026-01-31") == "range_fetch"
    assert fins.supports_code is True
    assert choose_fetch_strategy(JQUANTS_FINS_SUMMARY_ENDPOINT, from_date="2026-01-01", to_date="2026-01-31") == "date_by_date"


def test_build_endpoint_params_respects_capabilities() -> None:
    daily_params = build_endpoint_params(
        JQUANTS_DAILY_QUOTES_ENDPOINT,
        date="2026-06-01",
        from_date="2026-06-01",
        to_date="2026-06-30",
        code="72030",
        pagination_key="next",
    )
    fins_params = build_endpoint_params(
        JQUANTS_FINS_SUMMARY_ENDPOINT,
        from_date="2026-06-01",
        to_date="2026-06-30",
        code="72030",
    )

    assert daily_params == {
        "date": "2026-06-01",
        "from": "2026-06-01",
        "to": "2026-06-30",
        "code": "72030",
        "pagination_key": "next",
    }
    assert fins_params == {"code": "72030"}


def test_manifest_contains_rate_limit_retry_and_endpoint_capability_without_secret() -> None:
    manifest = jquants_common_policy_manifest(endpoint=JQUANTS_DAILY_QUOTES_ENDPOINT, rate_limit_per_minute=60)
    text = json.dumps(manifest).lower()

    assert manifest["rate_limit_policy"]["fixed_sleep_per_request"] is False
    assert manifest["retry_policy"]["rate_limit_retry_wait_seconds"] == 60.0
    assert manifest["endpoint_capability"]["endpoint"] == JQUANTS_DAILY_QUOTES_ENDPOINT
    assert "x-api-key" not in text
    assert "authorization" not in text
    assert "password" not in text


def test_client_uses_rolling_window_rate_limit_without_fixed_one_second_wait(tmp_path: Path) -> None:
    sleeps: list[float] = []
    calls: list[str] = []

    def fake_opener(request: Any, timeout: float) -> FakeResponse:
        calls.append(request.full_url)
        return FakeResponse({"data": []})

    client = JQuantsClient(
        settings=JQuantsSettings(api_key="secret-key", rate_limit_per_minute=60),
        paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        opener=fake_opener,
        sleep=sleeps.append,
    )

    client.fetch_daily_quotes(date="2026-06-01")
    client.fetch_daily_quotes(date="2026-06-02")

    assert len(calls) == 2
    assert sleeps == []


def test_client_waits_sixty_seconds_and_retries_on_429(tmp_path: Path) -> None:
    sleeps: list[float] = []
    calls = 0

    def fake_opener(request: Any, timeout: float) -> FakeResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise make_http_error(429)
        return FakeResponse({"data": [{"Date": "2026-06-01", "Code": "7203"}]})

    client = JQuantsClient(
        settings=JQuantsSettings(api_key="secret-key", rate_limit_per_minute=60),
        paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        opener=fake_opener,
        sleep=sleeps.append,
    )

    payload = client.fetch_daily_quotes(date="2026-06-01")

    assert payload["data"][0]["Code"] == "7203"
    assert calls == 2
    assert sleeps == [60.0]


def test_client_does_not_retry_400(tmp_path: Path) -> None:
    calls = 0

    def fake_opener(request: Any, timeout: float) -> FakeResponse:
        nonlocal calls
        calls += 1
        raise make_http_error(400)

    client = JQuantsClient(
        settings=JQuantsSettings(api_key="secret-key"),
        paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        opener=fake_opener,
        sleep=lambda _: pytest.fail("400 should not sleep for retry"),
    )

    with pytest.raises(JQuantsClientError, match="status=400"):
        client.fetch_daily_quotes(date="2021-06-01")

    assert calls == 1


def test_client_retries_5xx_once(tmp_path: Path) -> None:
    calls = 0

    def fake_opener(request: Any, timeout: float) -> FakeResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise make_http_error(503)
        return FakeResponse({"data": [{"Code": "1301"}]})

    client = JQuantsClient(
        settings=JQuantsSettings(api_key="secret-key"),
        paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        opener=fake_opener,
        sleep=lambda _: None,
    )

    payload = client.fetch_daily_quotes(date="2026-06-01")

    assert calls == 2
    assert payload["data"][0]["Code"] == "1301"


def make_http_error(status: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://api.jquants.com/v2/equities/bars/daily",
        code=status,
        msg="mocked error",
        hdrs={},
        fp=None,
    )
