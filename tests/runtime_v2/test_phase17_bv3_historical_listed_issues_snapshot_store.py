from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.data_sources.jquants.client import JQuantsClientError
from ai_fund_lab_v2.runtime_v2.historical_support.asof import resolve_historical_market_data_asof
from ai_fund_lab_v2.runtime_v2.historical_support.listed_issues_snapshots import (
    RETENTION_START_DATE,
    acquire_snapshots,
    rebuild_snapshot_index,
    resolve_listed_issues_snapshot,
    snapshot_manifest_path,
    write_listed_issues_snapshot,
)


def listed(date: str, code: str = "13010") -> dict[str, str]:
    return {"Date": date, "Code": code, "CoName": f"Company {code}", "Mkt": "0101"}


def write_snapshot(root: Path, day: str, codes: tuple[str, ...] = ("13010",)):
    return write_listed_issues_snapshot(
        snapshot_root=root,
        requested_date=day,
        records=[listed(day, code) for code in codes],
        storage_format="parquet",
        fetched_at="2026-07-16T00:00:00+00:00",
    )


def load_cli_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "acquire_historical_listed_issues_snapshots.py"
    spec = importlib.util.spec_from_file_location("acquire_historical_listed_issues_snapshots", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClient:
    def __init__(self, records_by_date=None, errors_by_date=None):
        self.records_by_date = records_by_date or {}
        self.errors_by_date = errors_by_date or {}
        self.calls: list[str] = []

    def fetch_all_listed_issues(self, *, date=None, max_pages=100):
        self.calls.append(str(date))
        errors = self.errors_by_date.get(date) or []
        if errors:
            error = errors.pop(0)
            raise error
        return self.records_by_date.get(date, [listed(str(date))])


def test_bv3_resolver_selects_exact_date_snapshot(tmp_path):
    root = tmp_path / "snapshots"
    write_snapshot(root, "2026-06-29")
    rebuild_snapshot_index(root)

    result = resolve_listed_issues_snapshot(snapshot_root=root, business_date="2026-06-29")

    assert result.status == "PASS"
    assert result.selected_snapshot_date == "2026-06-29"
    assert result.snapshot_age_days == 0


def test_bv3_resolver_selects_previous_snapshot_when_exact_missing(tmp_path):
    root = tmp_path / "snapshots"
    write_snapshot(root, "2026-06-26")
    write_snapshot(root, "2026-07-06")
    rebuild_snapshot_index(root)

    result = resolve_listed_issues_snapshot(snapshot_root=root, business_date="2026-06-29")

    assert result.status == "PASS"
    assert result.selected_snapshot_date == "2026-06-26"
    assert result.future_snapshot_used is False


def test_bv3_resolver_rejects_future_only_snapshot(tmp_path):
    root = tmp_path / "snapshots"
    write_snapshot(root, "2026-07-06")
    rebuild_snapshot_index(root)

    result = resolve_listed_issues_snapshot(snapshot_root=root, business_date="2026-06-29")

    assert result.status == "HALT"
    assert result.reason == "no_snapshot_not_after_business_date"


def test_bv3_resolver_rejects_empty_store(tmp_path):
    root = tmp_path / "snapshots"
    root.mkdir()
    (root / "index.json").write_text(json.dumps({"status": "PASS", "snapshots": []}), encoding="utf-8")

    result = resolve_listed_issues_snapshot(snapshot_root=root, business_date="2026-06-29")

    assert result.status == "HALT"
    assert result.reason == "snapshot_store_empty"


def test_bv3_resolver_rejects_broken_manifest_and_hash_mismatch(tmp_path):
    root = tmp_path / "snapshots"
    write_snapshot(root, "2026-06-29")
    index = rebuild_snapshot_index(root)
    manifest = snapshot_manifest_path(root, "2026-06-29")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["snapshot_date"] = "2026-06-28"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    result = resolve_listed_issues_snapshot(snapshot_root=root, business_date="2026-06-29")
    assert result.status == "HALT"
    assert result.reason == "snapshot_manifest_date_mismatch"

    index["snapshots"][0]["content_hash"] = "bad"
    (root / "index.json").write_text(json.dumps(index), encoding="utf-8")
    payload["snapshot_date"] = "2026-06-29"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    result = resolve_listed_issues_snapshot(snapshot_root=root, business_date="2026-06-29")
    assert result.reason == "snapshot_content_hash_mismatch"


def test_bv3_duplicate_identity_in_index_halts(tmp_path):
    root = tmp_path / "snapshots"
    write_snapshot(root, "2026-06-29")
    index = rebuild_snapshot_index(root)
    index["duplicate_snapshot_identities"] = ["2026-06-29"]
    (root / "index.json").write_text(json.dumps(index), encoding="utf-8")

    result = resolve_listed_issues_snapshot(snapshot_root=root, business_date="2026-06-29")

    assert result.status == "HALT"
    assert result.reason == "duplicate_snapshot_identity"


def test_bv3_acquire_skips_verified_existing_and_resumes_missing(tmp_path):
    root = tmp_path / "snapshots"
    write_snapshot(root, "2026-06-29")
    rebuild_snapshot_index(root)
    client = FakeClient(records_by_date={"2026-07-06": [listed("2026-07-06")]})

    result = acquire_snapshots(
        client=client,
        snapshot_root=root,
        target_dates=["2026-06-29", "2026-07-06"],
        sleep_seconds=0,
        skip_verified_existing=True,
    )

    assert result["status"] == "PASS"
    assert client.calls == ["2026-07-06"]
    assert result["skipped_count"] == 1
    assert result["success_count"] == 1


def test_bv3_api_400_retention_error_is_classified(tmp_path):
    error = JQuantsClientError(
        "bad request",
        diagnostic={"http_status": 400, "error_class": "API_PARAM_ERROR", "api_key": "SECRET_CANARY"},
    )
    client = FakeClient(errors_by_date={"2021-07-15": [error]})

    result = acquire_snapshots(
        client=client,
        snapshot_root=tmp_path / "snapshots",
        target_dates=["2021-07-15"],
        sleep_seconds=0,
    )

    assert result["status"] == "PARTIAL"
    failure = result["results"][0]
    assert failure["classification"] == "DATE_OUT_OF_RETENTION"
    assert "SECRET_CANARY" not in json.dumps(failure)


def test_bv3_api_rate_limit_retries(tmp_path, monkeypatch):
    error = JQuantsClientError("rate", diagnostic={"http_status": 429, "error_class": "API_RATE_LIMIT"})
    client = FakeClient(records_by_date={"2026-06-29": [listed("2026-06-29")]}, errors_by_date={"2026-06-29": [error]})
    monkeypatch.setattr("ai_fund_lab_v2.runtime_v2.historical_support.listed_issues_snapshots.time.sleep", lambda _: None)

    result = acquire_snapshots(
        client=client,
        snapshot_root=tmp_path / "snapshots",
        target_dates=["2026-06-29"],
        sleep_seconds=0,
        retry_count=2,
    )

    assert result["status"] == "PASS"
    assert client.calls == ["2026-06-29", "2026-06-29"]


def test_bv3_probe_path_is_not_used_as_authority(tmp_path):
    root = tmp_path / "operations"
    probe = root / "jquants" / "probes" / "historical_listed_issues" / "2026-06-29"
    write_snapshot(probe, "2026-06-29")
    rebuild_snapshot_index(probe)

    result = resolve_listed_issues_snapshot(
        snapshot_root=root / "jquants" / "historical_snapshots" / "listed_issues",
        business_date="2026-06-29",
    )

    assert result.status == "HALT"
    assert result.reason == "snapshot_index_missing"


def test_bv3_resolver_is_historical_mode_only(tmp_path):
    root = tmp_path / "snapshots"
    write_snapshot(root, "2026-06-29")
    rebuild_snapshot_index(root)

    result = resolve_listed_issues_snapshot(snapshot_root=root, business_date="2026-06-29", mode="production")

    assert result.status == "HALT"
    assert result.reason == "historical_snapshot_resolver_not_available_for_mode"


def test_bv3_historical_asof_uses_snapshot_store_for_2026_06_29(tmp_path):
    operations = tmp_path / "operations"
    snapshot_root = operations / "jquants" / "historical_snapshots" / "listed_issues"
    write_snapshot(snapshot_root, "2026-06-29", codes=("13010", "13050"))
    rebuild_snapshot_index(snapshot_root)
    _write_market_sources(operations)

    result = resolve_historical_market_data_asof(operations_root=operations, business_date="2026-06-29")
    listed_authority = next(item for item in result.authorities if item.authority == "listed_issues")

    assert result.status == "PASS"
    assert listed_authority.selected_snapshot_date == "2026-06-29"
    assert listed_authority.content_hash_verified is True


def test_bv3_retention_start_boundary_and_cli_dry_run(tmp_path):
    cli = load_cli_module()
    calendar = tmp_path / "calendar.parquet"
    pd.DataFrame(
        [
            {"Date": "2021-07-15", "HolDiv": "1"},
            {"Date": "2021-07-16", "HolDiv": "1"},
            {"Date": "2021-07-19", "HolDiv": "1"},
        ]
    ).to_parquet(calendar, index=False)
    args = cli.build_parser().parse_args(
        [
            "--snapshot-root",
            str(tmp_path / "snapshots"),
            "--calendar-source",
            str(calendar),
            "--start-date",
            "2021-07-15",
            "--end-date",
            "2021-07-19",
            "--dry-run",
        ]
    )

    dates = cli.resolve_target_dates(args)
    plan = cli.build_plan(args, dates)

    assert RETENTION_START_DATE == "2021-07-16"
    assert dates == ["2021-07-16", "2021-07-19"]
    assert plan["estimated_api_requests"] == 2


def _write_market_sources(operations: Path) -> None:
    for relative in [
        "jquants/raw_normalized/jquants/equities_bars_daily/data.parquet",
        "jquants/raw/jquants/equities_bars_daily/data.parquet",
        "jquants/raw/jquants/trading_calendar/data.parquet",
    ]:
        path = operations / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if "trading_calendar" in relative:
            pd.DataFrame([{"Date": "2026-06-29", "HolDiv": "1"}]).to_parquet(path, index=False)
        else:
            pd.DataFrame([{"Date": "2026-06-29", "Code": "13010", "Close": 100.0}]).to_parquet(path, index=False)
