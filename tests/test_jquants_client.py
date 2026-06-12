import json
import socket
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Any

import pytest

from ai_fund_lab_v2.config import JQuantsSettings
from ai_fund_lab_v2.data_sources.jquants import JQuantsClient, JQuantsClientError
from ai_fund_lab_v2.data_sources.jquants.client import (
    JQUANTS_DAILY_QUOTES_ENDPOINT,
    JQUANTS_FINS_SUMMARY_ENDPOINT,
    JQUANTS_LISTED_ISSUES_ENDPOINT,
    JQUANTS_TRADING_CALENDAR_ENDPOINT,
)
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


def test_jquants_client_uses_mock_and_does_not_call_real_api(tmp_path: Path) -> None:
    calls = []

    def fake_opener(request: Any, timeout: float) -> FakeResponse:
        calls.append((request, timeout))
        return FakeResponse({"data": [{"Date": "2026-06-01", "Code": "72030"}]})

    client = JQuantsClient(
        settings=JQuantsSettings(api_key="secret-key", rate_limit_per_minute=10_000),
        paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        opener=fake_opener,
    )

    payload = client.get_daily_quotes(code="72030", date="2026-06-01")

    assert payload["data"][0]["Code"] == "72030"
    assert len(calls) == 1
    request = calls[0][0]
    assert request.headers["X-api-key"] == "secret-key"
    assert "72030" in request.full_url
    assert (tmp_path / "runtime" / "logs").is_dir()


@pytest.mark.parametrize(
    ("method_name", "kwargs", "expected_path", "expected_params"),
    [
        (
            "fetch_daily_quotes",
            {"date": "2026-06-01", "code": "72030", "pagination_key": "next"},
            JQUANTS_DAILY_QUOTES_ENDPOINT,
            {"date": ["2026-06-01"], "code": ["72030"], "pagination_key": ["next"]},
        ),
        (
            "fetch_listed_issues",
            {"date": "2026-06-01", "code": "72030"},
            JQUANTS_LISTED_ISSUES_ENDPOINT,
            {"date": ["2026-06-01"], "code": ["72030"]},
        ),
        (
            "fetch_trading_calendar",
            {"from_date": "2026-06-01", "to_date": "2026-06-30"},
            JQUANTS_TRADING_CALENDAR_ENDPOINT,
            {"from": ["2026-06-01"], "to": ["2026-06-30"]},
        ),
        (
            "fetch_fins_summary",
            {"date": "2026-06-01", "code": "72030"},
            JQUANTS_FINS_SUMMARY_ENDPOINT,
            {"date": ["2026-06-01"], "code": ["72030"]},
        ),
    ],
)
def test_jquants_endpoint_methods_build_expected_paths_and_params(
    tmp_path: Path,
    method_name: str,
    kwargs: dict[str, str],
    expected_path: str,
    expected_params: dict[str, list[str]],
) -> None:
    calls = []

    def fake_opener(request: Any, timeout: float) -> FakeResponse:
        calls.append(request)
        return FakeResponse({"data": []})

    client = JQuantsClient(
        settings=JQuantsSettings(api_key="secret-key", rate_limit_per_minute=10_000),
        paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        opener=fake_opener,
    )

    getattr(client, method_name)(**kwargs)

    parsed = urllib.parse.urlparse(calls[0].full_url)
    assert parsed.path == expected_path
    assert urllib.parse.parse_qs(parsed.query) == expected_params


def test_jquants_pagination_fetches_multiple_pages(tmp_path: Path) -> None:
    payloads = [
        {"data": [{"Date": "2026-06-01", "Code": "11110"}], "pagination_key": "page-2"},
        {"data": [{"Date": "2026-06-01", "Code": "22220"}]},
    ]

    def fake_opener(request: Any, timeout: float) -> FakeResponse:
        return FakeResponse(payloads.pop(0))

    client = JQuantsClient(
        settings=JQuantsSettings(api_key="secret-key", rate_limit_per_minute=10_000),
        paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        opener=fake_opener,
    )

    records = client.fetch_all_daily_quotes(date="2026-06-01")

    assert [record["Code"] for record in records] == ["11110", "22220"]
    assert [record["pagination_page"] for record in records] == [1, 2]


def test_jquants_pagination_stops_at_max_pages(tmp_path: Path) -> None:
    calls = []

    def fake_opener(request: Any, timeout: float) -> FakeResponse:
        calls.append(request.full_url)
        return FakeResponse({"data": [{"Date": "2026-06-01", "Code": str(len(calls))}], "pagination_key": "next"})

    client = JQuantsClient(
        settings=JQuantsSettings(api_key="secret-key", rate_limit_per_minute=10_000),
        paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        opener=fake_opener,
    )

    records = client.fetch_all_daily_quotes(date="2026-06-01", max_pages=2)

    assert len(records) == 2
    assert len(calls) == 2


def test_jquants_pagination_failure_logs_endpoint_target_and_pages_without_secret(tmp_path: Path) -> None:
    payloads: list[Any] = [
        {"data": [{"Date": "2026-06-01", "Code": "11110"}], "pagination_key": "page-2"},
        make_http_error(500),
    ]
    secret = "pagination-secret"

    def fake_opener(request: Any, timeout: float) -> FakeResponse:
        payload = payloads.pop(0)
        if isinstance(payload, BaseException):
            raise payload
        return FakeResponse(payload)

    client = JQuantsClient(
        settings=JQuantsSettings(api_key=secret, rate_limit_per_minute=10_000),
        paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        opener=fake_opener,
    )

    with pytest.raises(JQuantsClientError):
        client.fetch_all_daily_quotes(date="2026-06-01")

    log_text = (tmp_path / "runtime" / "logs" / "jquants_client.log").read_text(encoding="utf-8")
    assert "pagination failed endpoint=/v2/equities/bars/daily target_date=2026-06-01 pages_fetched=1" in log_text
    assert secret not in log_text


def test_jquants_client_writes_token_cache_under_runtime_cache(tmp_path: Path) -> None:
    client = JQuantsClient(
        settings=JQuantsSettings(api_key="secret-key"),
        paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        opener=lambda *args, **kwargs: pytest.fail("real API should not be called"),
    )

    path = client.save_token_cache({"id_token": "token", "api_key": "secret-key", "password": "hidden"})

    assert path == tmp_path / "runtime" / "cache" / "jquants_token_cache.json"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "token" in text
    assert "secret-key" not in text
    assert "hidden" not in text


def test_jquants_client_wraps_timeout_without_leaking_secrets(tmp_path: Path) -> None:
    secret = "super-secret-api-key"
    client = JQuantsClient(
        settings=JQuantsSettings(api_key=secret, rate_limit_per_minute=10_000),
        paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        opener=lambda *args, **kwargs: (_ for _ in ()).throw(socket.timeout(f"timed out {secret}")),
    )

    with pytest.raises(JQuantsClientError) as exc_info:
        client.get_daily_quotes(code="72030", date="2026-06-01")

    assert "timeout" in str(exc_info.value)
    assert_no_secret_leaked(tmp_path, secret, str(exc_info.value))


@pytest.mark.parametrize("status", [401, 403])
def test_jquants_client_wraps_auth_errors_without_leaking_secrets(tmp_path: Path, status: int) -> None:
    secret = f"secret-api-key-{status}"
    client = JQuantsClient(
        settings=JQuantsSettings(api_key=secret, rate_limit_per_minute=10_000),
        paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        opener=lambda *args, **kwargs: (_ for _ in ()).throw(make_http_error(status)),
    )

    with pytest.raises(JQuantsClientError) as exc_info:
        client.get_daily_quotes(code="72030", date="2026-06-01")

    message = str(exc_info.value)
    assert "authentication failed" in message
    assert f"status={status}" in message
    assert_no_secret_leaked(tmp_path, secret, message)


def test_jquants_client_handles_429_with_mocked_sleep_and_no_secret_leak(tmp_path: Path) -> None:
    secret = "rate-limit-secret-key"
    sleep_calls: list[float] = []
    client = JQuantsClient(
        settings=JQuantsSettings(api_key=secret, rate_limit_per_minute=60),
        paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        opener=lambda *args, **kwargs: (_ for _ in ()).throw(make_http_error(429)),
        sleep=sleep_calls.append,
    )

    with pytest.raises(JQuantsClientError) as exc_info:
        client.get_daily_quotes(code="72030", date="2026-06-01")

    assert "rate limit exceeded" in str(exc_info.value)
    assert sleep_calls == [1.0]
    assert_no_secret_leaked(tmp_path, secret, str(exc_info.value))


def test_jquants_client_wraps_http_error_without_real_api(tmp_path: Path) -> None:
    client = JQuantsClient(
        settings=JQuantsSettings(api_key="http-secret", rate_limit_per_minute=10_000),
        paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        opener=lambda *args, **kwargs: (_ for _ in ()).throw(make_http_error(500)),
    )

    with pytest.raises(JQuantsClientError, match="status=500"):
        client.get_daily_quotes(code="72030", date="2026-06-01")


def test_jquants_client_wraps_url_error_without_real_api(tmp_path: Path) -> None:
    secret = "url-error-secret"
    client = JQuantsClient(
        settings=JQuantsSettings(api_key=secret, rate_limit_per_minute=10_000),
        paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        opener=lambda *args, **kwargs: (_ for _ in ()).throw(urllib.error.URLError(f"failed {secret}")),
    )

    with pytest.raises(JQuantsClientError) as exc_info:
        client.get_daily_quotes(code="72030", date="2026-06-01")

    assert "url_error" in str(exc_info.value)
    assert_no_secret_leaked(tmp_path, secret, str(exc_info.value))


def make_http_error(status: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://api.jquants.com/v2/equities/bars/daily",
        code=status,
        msg="mocked error",
        hdrs={},
        fp=None,
    )


def assert_no_secret_leaked(tmp_path: Path, secret: str, message: str) -> None:
    assert secret not in message
    assert "x-api-key" not in message.lower()
    assert "authorization" not in message.lower()

    log_file = tmp_path / "runtime" / "logs" / "jquants_client.log"
    assert log_file.exists()
    log_text = log_file.read_text(encoding="utf-8")
    assert secret not in log_text
    assert "x-api-key" not in log_text.lower()
    assert "authorization" not in log_text.lower()
