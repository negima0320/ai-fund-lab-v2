from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.data_sources.jquants import JQuantsClientError
from ai_fund_lab_v2.runtime_v2.market_data_acquisition import (
    AcquisitionRequestError,
    REQUEST_CONTRACT_VERSION,
    build_acquisition_plan,
    fetch_chunk_pages,
    resume_acquisition,
    run_acquisition,
    validate_staging_source,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TEST = REPO_ROOT / "scripts/runtime_test.py"


def _raw(day: str, code: str = "13010") -> dict[str, Any]:
    return {
        "Date": day,
        "Code": code,
        "O": 100.0,
        "H": 105.0,
        "L": 95.0,
        "C": 102.0,
        "Vo": 1000.0,
        "AdjO": 100.0,
        "AdjH": 105.0,
        "AdjL": 95.0,
        "AdjC": 102.0,
        "AdjVo": 1000.0,
        "AdjFactor": 1.0,
    }


class PagingFetcher:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = list(payloads)
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
        if not self.payloads:
            return {"data": []}
        payload = self.payloads.pop(0)
        if isinstance(payload, Exception):
            raise payload
        return payload


def test_phase20_bc_plan_is_read_only_and_staging_only(tmp_path: Path) -> None:
    plan = build_acquisition_plan(
        runtime_root=tmp_path / ".runtime",
        start_date="2021-04-20",
        end_date="2021-05-31",
        evidence_root=tmp_path / "evidence",
        staging_root=tmp_path / "runs",
        write_evidence=True,
    )

    assert plan["final_judgment"] == "ACQUISITION_PLAN_READY"
    assert plan["request_contract_version"] == REQUEST_CONTRACT_VERSION
    assert plan["request_strategy"] == "date_by_date"
    assert plan["read_only"] is True
    assert plan["mutation_scope"] == "staging_only"
    assert plan["jquants_api_fetch_executed"] is False
    assert (tmp_path / "evidence" / "api_pagination_contract.json").is_file()


def test_phase20_bc_pagination_fetches_until_token_absent() -> None:
    fetcher = PagingFetcher(
        [
            {"data": [_raw("2026-06-01", "11110")], "pagination_key": "NEXT"},
            {"data": [_raw("2026-06-01", "22220")]},
        ]
    )

    records, stats = fetch_chunk_pages(fetcher=fetcher, start_date="2026-06-01", end_date="2026-06-01")

    assert [row["Code"] for row in records] == ["11110", "22220"]
    assert stats["page_count"] == 2
    assert fetcher.calls[1]["pagination_key"] == "NEXT"
    assert fetcher.calls[0]["date"] == "2026-06-01"
    assert fetcher.calls[0]["from_date"] is None
    assert fetcher.calls[0]["to_date"] is None


def test_phase20_bc_pagination_token_cycle_blocks() -> None:
    fetcher = PagingFetcher(
        [
            {"data": [_raw("2026-06-01", "11110")], "pagination_key": "LOOP"},
            {"data": [_raw("2026-06-01", "22220")], "pagination_key": "LOOP"},
        ]
    )

    try:
        fetch_chunk_pages(fetcher=fetcher, start_date="2026-06-01", end_date="2026-06-01")
    except Exception as exc:  # noqa: BLE001
        assert "pagination_token_cycle_detected" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("cycle should block")


def test_phase20_bc_retry_then_success_for_rate_limit() -> None:
    error = JQuantsClientError("rate limit", diagnostic={"error_class": "API_RATE_LIMIT"})
    fetcher = PagingFetcher([error, {"data": [_raw("2026-06-01")]}])

    records, stats = fetch_chunk_pages(
        fetcher=fetcher,
        start_date="2026-06-01",
        end_date="2026-06-01",
        sleep=lambda _seconds: None,
    )

    assert len(records) == 1
    assert stats["retry_count"] == 1
    assert stats["request_count"] == 2


def test_phase20_bc_auth_error_blocks_without_retry() -> None:
    error = JQuantsClientError("auth", diagnostic={"error_class": "API_AUTH_ERROR"})
    fetcher = PagingFetcher([error])

    try:
        fetch_chunk_pages(fetcher=fetcher, start_date="2026-06-01", end_date="2026-06-01")
    except AcquisitionRequestError:
        pass
    else:  # pragma: no cover
        raise AssertionError("auth should block")
    assert len(fetcher.calls) == 1


def test_phase20_bc_run_and_resume_skip_completed_chunk(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    staging_root = tmp_path / "runs"
    class EchoFetcher(PagingFetcher):
        def __init__(self) -> None:
            super().__init__([])

        def fetch_daily_quotes(
            self,
            *,
            date: str | None = None,
            from_date: str | None = None,
            to_date: str | None = None,
            pagination_key: str | None = None,
        ) -> dict[str, Any]:
            self.calls.append({"date": date, "from_date": from_date, "to_date": to_date, "pagination_key": pagination_key})
            return {"data": [_raw(str(date), "11110" if str(date).startswith("2026-06") else "22220")]}

    fetcher = EchoFetcher()
    partial = run_acquisition(
        runtime_root=runtime_root,
        start_date="2026-06-01",
        end_date="2026-07-02",
        run_id="fixture-run",
        staging_root=staging_root,
        evidence_root=tmp_path / "evidence",
        confirm=True,
        explicit_fetch_confirm=True,
        fetcher=fetcher,
        stop_after_chunks=1,
        sleep=lambda _seconds: None,
    )
    assert partial["status"] == "IN_PROGRESS"
    assert partial["completed_chunks"] == 1

    resumed = resume_acquisition(
        runtime_root=runtime_root,
        run_id="fixture-run",
        staging_root=staging_root,
        evidence_root=tmp_path / "evidence",
        confirm=True,
        explicit_fetch_confirm=True,
        fetcher=fetcher,
        sleep=lambda _seconds: None,
    )

    assert resumed["final_judgment"] == "ACQUISITION_SOURCE_READY"
    assert resumed["completed_chunks"] == 2
    assert {"2026-06-01", "2026-07-01", "2026-07-02"}.issubset({str(call["date"]) for call in fetcher.calls})
    assert Path(resumed["normalized_output_path"]).is_file()


def test_phase20_bc_validation_blocks_future_rows(tmp_path: Path) -> None:
    path = tmp_path / "normalized.parquet"
    pd.DataFrame(
        [
            {
                "Date": "2999-01-01",
                "Code": "13010",
                "Open": 100.0,
                "High": 101.0,
                "Low": 99.0,
                "Close": 100.0,
                "Volume": 1000.0,
                "PriceSource": "adjusted",
                "SchemaVersion": 2,
                "source_endpoint": "/v2/equities/bars/daily",
                "target_date": "2999-01-01",
                "code": "13010",
                "business_key": "13010",
                "endpoint": "daily_quotes_normalized",
                "source": "jquants",
            }
        ]
    ).to_parquet(path, index=False)

    result = validate_staging_source(normalized_path=path, requested_start_date="2026-01-01", requested_end_date="2026-01-31")

    assert result["status"] == "BLOCK"
    assert "future_date_contamination" in result["blocked_reasons"]


def test_phase20_bc_cli_plan_help_and_json_plan() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src:."
    help_result = subprocess.run(
        [sys.executable, str(RUNTIME_TEST), "market-data-acquisition", "plan", "--help"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert help_result.returncode == 0
    assert "--start-date" in help_result.stdout
    plan_result = subprocess.run(
        [
            sys.executable,
            str(RUNTIME_TEST),
            "market-data-acquisition",
            "plan",
            "--start-date",
            "2021-04-20",
            "--end-date",
            "2021-04-30",
            "--json",
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(plan_result.stdout)
    assert payload["status"] == "PASS"
    assert payload["acquisition_result"]["final_judgment"] == "ACQUISITION_PLAN_READY"
