from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from ai_fund_lab_v2.data_sources.jquants.client import JQuantsClientError
from ai_fund_lab_v2.runtime import RuntimePaths
from ai_fund_lab_v2.runtime_v2.historical_support.trading_calendar_snapshots import (
    acquire_calendar,
    data_path,
    list_trading_days,
    manifest_path,
    validate_calendar_store,
    write_calendar_authority,
)


def cal(day: str, holdiv: str) -> dict[str, str]:
    return {"Date": day, "HolDiv": holdiv}


def sample_records() -> list[dict[str, str]]:
    return [
        cal("2021-07-16", "1"),
        cal("2021-07-17", "0"),
        cal("2021-07-18", "0"),
        cal("2021-07-19", "1"),
        cal("2022-01-01", "0"),
        cal("2022-01-03", "0"),
        cal("2022-01-04", "1"),
        cal("2026-06-29", "1"),
        cal("2026-07-06", "1"),
    ]


class FakeClient:
    def __init__(self, records=None, errors=None):
        self.records = records if records is not None else sample_records()
        self.errors = errors or []
        self.calls = []

    def fetch_all_trading_calendar(self, *, from_date=None, to_date=None, max_pages=100):
        self.calls.append((from_date, to_date, max_pages))
        if self.errors:
            raise self.errors.pop(0)
        return list(self.records)


def load_calendar_cli():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "acquire_historical_trading_calendar.py"
    spec = importlib.util.spec_from_file_location("acquire_historical_trading_calendar", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_listed_cli():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "acquire_historical_listed_issues_snapshots.py"
    spec = importlib.util.spec_from_file_location("acquire_historical_listed_issues_snapshots", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bv4_write_and_validate_calendar_authority(tmp_path):
    root = tmp_path / "calendar"
    result = write_calendar_authority(
        calendar_root=root,
        requested_from_date="2021-07-16",
        requested_to_date="2026-07-06",
        records=sample_records(),
        fetched_at="2026-07-16T00:00:00+00:00",
    )

    validation = validate_calendar_store(calendar_root=root, required_start_date="2021-07-16", required_end_date="2026-07-06")

    assert result["status"] == "PASS"
    assert validation.status == "PASS"
    assert validation.min_date == "2021-07-16"
    assert validation.max_date == "2026-07-06"
    assert validation.duplicate_date_count == 0
    assert validation.trading_day_count == 5


def test_bv4_business_day_resolution_excludes_weekends_holidays_and_year_end(tmp_path):
    root = tmp_path / "calendar"
    write_calendar_authority(
        calendar_root=root,
        requested_from_date="2021-07-16",
        requested_to_date="2026-07-06",
        records=sample_records(),
        fetched_at="2026-07-16T00:00:00+00:00",
    )

    days = list_trading_days(data_path(root), start_date="2021-07-16", end_date="2026-07-06")

    assert "2021-07-16" in days
    assert "2022-01-04" in days
    assert "2026-06-29" in days
    assert "2026-07-06" in days
    assert "2021-07-17" not in days
    assert "2022-01-01" not in days
    assert "2022-01-03" not in days


def test_bv4_duplicate_date_halts(tmp_path):
    root = tmp_path / "calendar"
    records = [cal("2021-07-16", "1"), cal("2021-07-16", "0")]
    result = write_calendar_authority(
        calendar_root=root,
        requested_from_date="2021-07-16",
        requested_to_date="2021-07-16",
        records=records,
        fetched_at="2026-07-16T00:00:00+00:00",
    )

    assert result["status"] == "HALT"
    assert result["validation"]["reason"] == "duplicate_calendar_date"


def test_bv4_broken_parquet_and_hash_mismatch_halt(tmp_path):
    root = tmp_path / "calendar"
    write_calendar_authority(
        calendar_root=root,
        requested_from_date="2021-07-16",
        requested_to_date="2026-07-06",
        records=sample_records(),
        fetched_at="2026-07-16T00:00:00+00:00",
    )
    manifest = json.loads(manifest_path(root).read_text(encoding="utf-8"))
    manifest["content_hash"] = "bad"
    manifest_path(root).write_text(json.dumps(manifest), encoding="utf-8")
    assert validate_calendar_store(calendar_root=root).reason == "calendar_content_hash_mismatch"

    data_path(root).write_text("not parquet", encoding="utf-8")
    assert validate_calendar_store(calendar_root=root).reason == "calendar_parquet_unreadable"


def test_bv4_resume_skips_verified_existing(tmp_path):
    root = tmp_path / "calendar"
    write_calendar_authority(
        calendar_root=root,
        requested_from_date="2021-07-16",
        requested_to_date="2026-07-06",
        records=sample_records(),
        fetched_at="2026-07-16T00:00:00+00:00",
    )
    client = FakeClient(records=[cal("2099-01-01", "1")])

    result = acquire_calendar(
        client=client,
        calendar_root=root,
        start_date="2021-07-16",
        end_date="2026-07-06",
        sleep_seconds=0,
        skip_verified_existing=True,
    )

    assert result["status"] == "SKIPPED"
    assert client.calls == []


def test_bv4_partial_acquisition_can_be_retried(tmp_path):
    root = tmp_path / "calendar"
    error = JQuantsClientError("rate", diagnostic={"http_status": 429, "error_class": "API_RATE_LIMIT"})
    client = FakeClient(records=sample_records(), errors=[error])

    result = acquire_calendar(
        client=client,
        calendar_root=root,
        start_date="2021-07-16",
        end_date="2026-07-06",
        retry_count=2,
        sleep_seconds=0,
    )

    assert result["status"] == "PASS"
    assert len(client.calls) == 2


def test_bv4_api_400_retention_error_is_secret_safe(tmp_path):
    error = JQuantsClientError(
        "bad request",
        diagnostic={"http_status": 400, "error_class": "API_PARAM_ERROR", "api_key": "SECRET_CANARY"},
    )
    client = FakeClient(errors=[error])

    result = acquire_calendar(
        client=client,
        calendar_root=tmp_path / "calendar",
        start_date="2021-07-15",
        end_date="2021-07-15",
        sleep_seconds=0,
    )

    serialized = json.dumps(result, sort_keys=True)
    assert result["classification"] == "DATE_OUT_OF_RETENTION"
    assert "SECRET_CANARY" not in serialized


def test_bv4_cli_dry_run_has_no_fetch_and_reports_endpoint(tmp_path):
    cli = load_calendar_cli()
    operational = tmp_path / "operational.parquet"
    pd.DataFrame(sample_records()).to_parquet(operational, index=False)
    args = cli.build_parser().parse_args(
        [
            "--calendar-root",
            str(tmp_path / "calendar"),
            "--current-operational-calendar",
            str(operational),
            "--dry-run",
        ]
    )

    plan = cli.build_plan(args)

    assert plan["dry_run_only"] is True
    assert plan["endpoint"] == "/v2/markets/calendar"
    assert plan["endpoint_capability"]["supports_from_to"] is True
    assert plan["current_operational_calendar"]["min_date"] == "2021-07-16"


def test_bv4_cli_progress_payload_is_json_serializable(tmp_path):
    cli = load_calendar_cli()
    payload = {"status": "PASS"}
    progress_records = []
    progress_records.append(cli.json_safe_payload(payload))
    payload["progress_records"] = progress_records

    encoded = json.dumps(cli.json_safe_payload(payload), sort_keys=True)

    assert "progress_records" in encoded


def test_bv4_cli_main_writes_result_without_circular_reference(monkeypatch, tmp_path):
    cli = load_calendar_cli()
    root = tmp_path / "calendar"

    class Settings:
        runtime_paths = RuntimePaths(runtime_dir=tmp_path / "runtime")
        jquants = SimpleNamespace(require_api_key=lambda: "dummy")

    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "JQuantsClient", lambda settings, paths: FakeClient(records=sample_records()))

    exit_code = cli.main(
        [
            "--calendar-root",
            str(root),
            "--start-date",
            "2021-07-16",
            "--end-date",
            "2026-07-06",
            "--sleep-seconds",
            "0",
            "--write-evidence",
        ]
    )

    result = json.loads((root / "acquisition_result.json").read_text(encoding="utf-8"))
    assert exit_code == 0
    assert result["status"] == "PASS"
    assert result["progress_records"][0]["status"] == "PASS"


def test_bv4_listed_issues_bv3_can_use_canonical_calendar_source(tmp_path):
    root = tmp_path / "calendar"
    write_calendar_authority(
        calendar_root=root,
        requested_from_date="2021-07-16",
        requested_to_date="2026-07-06",
        records=sample_records(),
        fetched_at="2026-07-16T00:00:00+00:00",
    )
    listed_cli = load_listed_cli()
    args = listed_cli.build_parser().parse_args(
        [
            "--calendar-source",
            str(data_path(root)),
            "--snapshot-root",
            str(tmp_path / "listed"),
            "--start-date",
            "2021-07-16",
            "--end-date",
            "2026-07-06",
            "--dry-run",
        ]
    )

    dates = listed_cli.resolve_target_dates(args)
    plan = listed_cli.build_plan(args, dates)

    assert "2021-07-16" in dates
    assert "2026-06-29" in dates
    assert "2026-07-06" in dates
    assert "2021-07-17" not in dates
    assert plan["calendar_coverage_status"] == "PASS"
