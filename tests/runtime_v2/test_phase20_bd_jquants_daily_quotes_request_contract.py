from __future__ import annotations

import io
import json
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.config.settings import JQuantsSettings
from ai_fund_lab_v2.data_sources.jquants.client import JQuantsClient, JQuantsClientError
from ai_fund_lab_v2.runtime.paths import RuntimePaths
from ai_fund_lab_v2.runtime_v2.market_data_acquisition import (
    REQUEST_CONTRACT_VERSION,
    fetch_chunk_pages,
    resume_acquisition,
    run_acquisition,
)


def test_phase20_bd_client_daily_quotes_uses_date_param_without_range(tmp_path: Path) -> None:
    seen: dict[str, Any] = {}

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"data":[]}'

    def opener(request: Any, timeout: float) -> Response:
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["headers"] = dict(request.header_items())
        return Response()

    client = JQuantsClient(
        settings=JQuantsSettings(api_key="test-secret", base_url="https://example.test", timeout_seconds=12.5),
        paths=RuntimePaths(runtime_dir=tmp_path / ".runtime"),
        opener=opener,
        sleep=lambda _seconds: None,
    )

    client.fetch_daily_quotes(date="2026-07-01")

    parsed = urllib.parse.urlparse(str(seen["url"]))
    query = urllib.parse.parse_qs(parsed.query)
    assert parsed.path == "/v2/equities/bars/daily"
    assert query == {"date": ["2026-07-01"]}
    assert "from" not in query
    assert "to" not in query
    assert seen["timeout"] == 12.5
    assert "X-api-key" in seen["headers"]


def test_phase20_bd_http_400_detail_is_secret_safe_and_non_retryable(tmp_path: Path) -> None:
    calls = 0

    def opener(request: Any, timeout: float) -> object:
        nonlocal calls
        calls += 1
        raise urllib.error.HTTPError(
            request.full_url,
            400,
            "Bad Request",
            {"Content-Type": "application/json"},
            io.BytesIO(b'{"message":"date parameter is required"}'),
        )

    client = JQuantsClient(
        settings=JQuantsSettings(api_key="test-secret", base_url="https://example.test"),
        paths=RuntimePaths(runtime_dir=tmp_path / ".runtime"),
        opener=opener,
        sleep=lambda _seconds: None,
    )

    try:
        client.fetch_daily_quotes(date="2026-07-01")
    except JQuantsClientError as exc:
        diagnostic = exc.diagnostic
    else:  # pragma: no cover
        raise AssertionError("HTTP 400 should fail closed")

    assert calls == 1
    assert diagnostic["error_class"] == "API_PARAM_ERROR"
    assert diagnostic["http_status"] == 400
    assert diagnostic["response_content_type"] == "application/json"
    assert diagnostic["response_body"] == '{"message":"date parameter is required"}'
    assert diagnostic["request_parameter_names"] == ["date"]
    assert "test-secret" not in json.dumps(diagnostic)


class ErrorFetcher:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def fetch_daily_quotes(
        self,
        *,
        date: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        pagination_key: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append({"date": date, "from_date": from_date, "to_date": to_date, "pagination_key": pagination_key})
        raise self.error


def test_phase20_bd_http_400_counts_as_one_request_and_zero_pages() -> None:
    fetcher = ErrorFetcher(
        JQuantsClientError(
            "bad request",
            diagnostic={"error_class": "API_PARAM_ERROR", "http_status": 400, "response_body": '{"message":"bad date"}'},
        )
    )

    try:
        fetch_chunk_pages(fetcher=fetcher, start_date="2026-07-01", end_date="2026-07-01", sleep=lambda _seconds: None)
    except Exception as exc:  # noqa: BLE001
        assert getattr(exc, "request_count") == 1
        assert getattr(exc, "page_count") == 0
        assert getattr(exc, "http_status") == 400
    else:  # pragma: no cover
        raise AssertionError("HTTP 400 should block")
    assert fetcher.calls == [{"date": "2026-07-01", "from_date": None, "to_date": None, "pagination_key": None}]


def test_phase20_bd_legacy_bc_run_requires_new_run_id(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    staging_root = tmp_path / "runs"
    run_root = staging_root / "legacy-run"
    run_root.mkdir(parents=True)
    plan = {
        "schema_version": "phase20_bc_jquants_market_data_acquisition.v1",
        "acquisition_run_id": "legacy-run",
        "requested_start_date": "2021-07-01",
        "requested_end_date": "2021-07-02",
        "endpoint": "/v2/equities/bars/daily",
        "chunk_strategy": "month",
        "blocked_reasons": [],
    }
    state = {
        "schema_version": "phase20_bc_jquants_market_data_acquisition_state.v1",
        "status": "BLOCK",
        "acquisition_run_id": "legacy-run",
        "binding": {key: plan[key] for key in ("schema_version", "requested_start_date", "requested_end_date", "endpoint", "chunk_strategy")},
        "chunks": [],
    }
    (run_root / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    (run_root / "state.json").write_text(json.dumps(state), encoding="utf-8")

    result = resume_acquisition(
        runtime_root=runtime_root,
        run_id="legacy-run",
        staging_root=staging_root,
        evidence_root=tmp_path / "evidence",
        confirm=True,
        explicit_fetch_confirm=True,
        fetcher=ErrorFetcher(RuntimeError("should not fetch")),
    )

    assert result["status"] == "BLOCK"
    assert result["final_judgment"] == "ACQUISITION_LEGACY_RUN_INCOMPATIBLE_WITH_UPDATED_REQUEST_CONTRACT"
    assert "new_run_id_required" in result["blocked_reasons"]


def test_phase20_bd_run_state_persists_date_level_requests(tmp_path: Path) -> None:
    class OneDayFetcher:
        def __init__(self) -> None:
            self.calls: list[str | None] = []

        def fetch_daily_quotes(self, *, date: str | None = None, **_kwargs: Any) -> dict[str, Any]:
            self.calls.append(date)
            return {
                "data": [
                    {
                        "Date": date,
                        "Code": "13010",
                        "O": 100.0,
                        "H": 101.0,
                        "L": 99.0,
                        "C": 100.0,
                        "Vo": 1000.0,
                    }
                ]
            }

    fetcher = OneDayFetcher()
    result = run_acquisition(
        runtime_root=tmp_path / ".runtime",
        start_date="2026-07-01",
        end_date="2026-07-01",
        run_id="bd-one-day",
        staging_root=tmp_path / "runs",
        evidence_root=tmp_path / "evidence",
        confirm=True,
        explicit_fetch_confirm=True,
        fetcher=fetcher,
        sleep=lambda _seconds: None,
    )

    state = json.loads((tmp_path / "runs" / "bd-one-day" / "state.json").read_text(encoding="utf-8"))
    assert result["final_judgment"] == "ACQUISITION_SOURCE_READY"
    assert result["request_contract_version"] == REQUEST_CONTRACT_VERSION
    assert result["request_count"] >= 1
    assert fetcher.calls == ["2026-07-01"]
    assert state["chunks"][0]["requests"][0]["request_date"] == "2026-07-01"
    assert state["chunks"][0]["requests"][0]["status"] == "COMPLETED"
