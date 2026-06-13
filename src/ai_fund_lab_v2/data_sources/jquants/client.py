from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.config.settings import JQuantsSettings
from ai_fund_lab_v2.data.jquants_fetch_policy import (
    JQuantsRateLimitPolicy,
    JQuantsRetryPolicy,
    RateLimitState,
    build_endpoint_params,
    endpoint_capability_manifest,
    jquants_common_policy_manifest,
)
from ai_fund_lab_v2.logging.runtime_logging import configure_runtime_logger
from ai_fund_lab_v2.runtime.paths import RuntimePaths

JQUANTS_DAILY_QUOTES_ENDPOINT = "/v2/equities/bars/daily"
JQUANTS_LISTED_ISSUES_ENDPOINT = "/v2/equities/master"
JQUANTS_TRADING_CALENDAR_ENDPOINT = "/v2/markets/calendar"
JQUANTS_FINS_SUMMARY_ENDPOINT = "/v2/fins/summary"
PAGINATION_KEY = "pagination_key"


class JQuantsClientError(RuntimeError):
    """Raised when a J-Quants API request fails."""


@dataclass
class JQuantsClient:
    settings: JQuantsSettings
    paths: RuntimePaths
    opener: Any = urllib.request.urlopen
    sleep: Any = time.sleep
    _rate_limit_state: RateLimitState | None = field(default=None, init=False)
    _retry_policy: JQuantsRetryPolicy = field(default_factory=JQuantsRetryPolicy, init=False)

    def __post_init__(self) -> None:
        self.paths.ensure_base_dirs()
        self._rate_limit_state = RateLimitState(
            JQuantsRateLimitPolicy(max_requests_per_minute=self.settings.rate_limit_per_minute)
        )
        self.logger = configure_runtime_logger(
            "ai_fund_lab_v2.jquants",
            self.paths.logs,
            "jquants_client.log",
        )

    @property
    def token_cache_path(self) -> Path:
        return self.paths.cache / "jquants_token_cache.json"

    def fetch_daily_quotes(
        self,
        *,
        code: str | None = None,
        date: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        pagination_key: str | None = None,
    ) -> dict[str, Any]:
        return self.get(
            JQUANTS_DAILY_QUOTES_ENDPOINT,
            params=build_endpoint_params(
                JQUANTS_DAILY_QUOTES_ENDPOINT,
                date=date,
                from_date=from_date,
                to_date=to_date,
                code=code,
                pagination_key=pagination_key,
            ),
        )

    def get_daily_quotes(self, **kwargs: Any) -> dict[str, Any]:
        return self.fetch_daily_quotes(**kwargs)

    def fetch_listed_issues(
        self,
        *,
        code: str | None = None,
        date: str | None = None,
        pagination_key: str | None = None,
    ) -> dict[str, Any]:
        return self.get(
            JQUANTS_LISTED_ISSUES_ENDPOINT,
            params=build_endpoint_params(
                JQUANTS_LISTED_ISSUES_ENDPOINT,
                code=code,
                date=date,
                pagination_key=pagination_key,
            ),
        )

    def fetch_trading_calendar(
        self,
        *,
        date: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        pagination_key: str | None = None,
    ) -> dict[str, Any]:
        return self.get(
            JQUANTS_TRADING_CALENDAR_ENDPOINT,
            params=build_endpoint_params(
                JQUANTS_TRADING_CALENDAR_ENDPOINT,
                date=date,
                from_date=from_date,
                to_date=to_date,
                pagination_key=pagination_key,
            ),
        )

    def fetch_fins_summary(
        self,
        *,
        code: str | None = None,
        date: str | None = None,
        pagination_key: str | None = None,
    ) -> dict[str, Any]:
        return self.get(
            JQUANTS_FINS_SUMMARY_ENDPOINT,
            params=build_endpoint_params(
                JQUANTS_FINS_SUMMARY_ENDPOINT,
                code=code,
                date=date,
                pagination_key=pagination_key,
            ),
        )

    def fetch_all_pages(
        self,
        endpoint: str,
        *,
        params: dict[str, str] | None = None,
        max_pages: int = 100,
        target_date: str | None = None,
    ) -> list[dict[str, Any]]:
        if max_pages < 1:
            raise ValueError("max_pages must be >= 1")

        all_records: list[dict[str, Any]] = []
        pagination_key: str | None = None
        base_params = dict(params or {})

        for page in range(1, max_pages + 1):
            request_params = dict(base_params)
            if pagination_key:
                request_params[PAGINATION_KEY] = pagination_key
            try:
                payload = self.get(endpoint, params=request_params)
            except Exception:
                self.logger.error(
                    "J-Quants pagination failed endpoint=%s target_date=%s pages_fetched=%s",
                    endpoint,
                    target_date,
                    page - 1,
                )
                raise

            page_records = payload.get("data") or []
            for record in page_records:
                enriched = dict(record)
                enriched["pagination_page"] = page
                if pagination_key:
                    enriched["pagination_key"] = pagination_key
                all_records.append(enriched)

            pagination_key = payload.get(PAGINATION_KEY)
            if not pagination_key:
                break

        return all_records

    def fetch_all_daily_quotes(self, *, max_pages: int = 100, **kwargs: Any) -> list[dict[str, Any]]:
        return self.fetch_all_pages(
            JQUANTS_DAILY_QUOTES_ENDPOINT,
            params=self._daily_quote_params(**kwargs),
            max_pages=max_pages,
            target_date=kwargs.get("date") or kwargs.get("from_date"),
        )

    def fetch_all_listed_issues(self, *, max_pages: int = 100, **kwargs: Any) -> list[dict[str, Any]]:
        return self.fetch_all_pages(
            JQUANTS_LISTED_ISSUES_ENDPOINT,
            params=self._params(**kwargs),
            max_pages=max_pages,
            target_date=kwargs.get("date"),
        )

    def fetch_all_trading_calendar(self, *, max_pages: int = 100, **kwargs: Any) -> list[dict[str, Any]]:
        return self.fetch_all_pages(
            JQUANTS_TRADING_CALENDAR_ENDPOINT,
            params=self._calendar_params(**kwargs),
            max_pages=max_pages,
            target_date=kwargs.get("date") or kwargs.get("from_date"),
        )

    def fetch_all_fins_summary(self, *, max_pages: int = 100, **kwargs: Any) -> list[dict[str, Any]]:
        return self.fetch_all_pages(
            JQUANTS_FINS_SUMMARY_ENDPOINT,
            params=self._params(**kwargs),
            max_pages=max_pages,
            target_date=kwargs.get("date"),
        )

    def get(self, endpoint: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        api_key = self.settings.require_api_key()
        url = self._build_url(endpoint, params or {})
        request = urllib.request.Request(url, headers={"x-api-key": api_key})
        attempt = 1
        while True:
            self._wait_for_rate_limit()
            try:
                with self.opener(request, timeout=self.settings.timeout_seconds) as response:
                    self._record_request()
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                self._record_request()
                self._log_request_failure(endpoint, exc.code, "http_error")
                decision = self._retry_policy.should_retry(exc.code, attempt)
                if decision.retryable:
                    self.sleep(decision.wait_seconds)
                    attempt += 1
                    continue
                raise JQuantsClientError(self._safe_error_message(endpoint, exc.code)) from exc
            except urllib.error.URLError as exc:
                self._record_request()
                self._log_request_failure(endpoint, "url_error", "url_error")
                decision = self._retry_policy.should_retry("url_error", attempt)
                if decision.retryable:
                    self.sleep(decision.wait_seconds)
                    attempt += 1
                    continue
                raise JQuantsClientError(self._safe_error_message(endpoint, "url_error")) from exc
            except (TimeoutError, socket.timeout) as exc:
                self._record_request()
                self._log_request_failure(endpoint, "timeout", "timeout")
                decision = self._retry_policy.should_retry("timeout", attempt)
                if decision.retryable:
                    self.sleep(decision.wait_seconds)
                    attempt += 1
                    continue
                raise JQuantsClientError(self._safe_error_message(endpoint, "timeout")) from exc

    def save_token_cache(self, payload: dict[str, Any]) -> Path:
        """Persist non-source-controlled auth cache for future auth extensions."""
        self.paths.cache.mkdir(parents=True, exist_ok=True)
        safe_payload = {key: value for key, value in payload.items() if key not in {"password", "api_key"}}
        with self.token_cache_path.open("w", encoding="utf-8") as handle:
            json.dump(safe_payload, handle, ensure_ascii=False, sort_keys=True)
        return self.token_cache_path

    def _build_url(self, endpoint: str, params: dict[str, str]) -> str:
        query = urllib.parse.urlencode(params)
        url = f"{self.settings.base_url}{endpoint}"
        return f"{url}?{query}" if query else url

    def _daily_quote_params(self, **kwargs: Any) -> dict[str, str]:
        return build_endpoint_params(
            JQUANTS_DAILY_QUOTES_ENDPOINT,
            date=kwargs.get("date"),
            from_date=kwargs.get("from_date"),
            to_date=kwargs.get("to_date"),
            code=kwargs.get("code"),
        )

    def _calendar_params(self, **kwargs: Any) -> dict[str, str]:
        return build_endpoint_params(
            JQUANTS_TRADING_CALENDAR_ENDPOINT,
            date=kwargs.get("date"),
            from_date=kwargs.get("from_date"),
            to_date=kwargs.get("to_date"),
        )

    def _params(self, **kwargs: Any) -> dict[str, str]:
        return {key: str(value) for key, value in kwargs.items() if value is not None and value != ""}

    def _wait_for_rate_limit(self) -> None:
        if self._rate_limit_state is None:
            return
        wait_seconds = self._rate_limit_state.seconds_until_available(time.monotonic())
        if wait_seconds > 0:
            self.sleep(wait_seconds)

    def _record_request(self) -> None:
        if self._rate_limit_state is not None:
            self._rate_limit_state.record_request(time.monotonic())

    def common_policy_manifest(self, endpoint: str) -> dict[str, Any]:
        return jquants_common_policy_manifest(
            endpoint=endpoint,
            rate_limit_per_minute=self.settings.rate_limit_per_minute,
            max_attempts=self._retry_policy.max_attempts,
        )

    def endpoint_capability_manifest(self, endpoint: str) -> dict[str, Any]:
        return endpoint_capability_manifest(endpoint)

    def _safe_error_message(self, endpoint: str, status: int | str) -> str:
        if status in (401, 403):
            return f"J-Quants authentication failed: endpoint={endpoint} status={status}"
        if status == 429:
            return f"J-Quants rate limit exceeded: endpoint={endpoint} status={status}"
        return f"J-Quants request failed: endpoint={endpoint} status={status}"

    def _log_request_failure(self, endpoint: str, status: int | str, error_type: str) -> None:
        self.logger.error(
            "J-Quants request failed endpoint=%s status=%s error_type=%s",
            endpoint,
            status,
            error_type,
        )
