from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.historical_support.asof import (
    materialize_historical_logical_inputs,
    resolve_historical_market_data_asof,
)
from ai_fund_lab_v2.runtime_v2.market_refresh import pipeline


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "runtime_test.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("runtime_test_script_phase17_l", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_market_authorities(root: Path) -> None:
    operations = root / "operations"
    normalized = operations / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily"
    raw = operations / "jquants" / "raw" / "jquants" / "equities_bars_daily"
    calendar = operations / "jquants" / "raw" / "jquants" / "trading_calendar"
    listed = operations / "jquants" / "raw" / "jquants" / "listed_issues"
    for path in (normalized, raw, calendar, listed):
        path.mkdir(parents=True, exist_ok=True)
    quotes = pd.DataFrame(
        [
            {"target_date": "2026-07-06", "code": "7203", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 100},
            {"target_date": "2026-07-10", "code": "7203", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 100},
        ]
    )
    quotes.to_parquet(normalized / "data.parquet", index=False)
    quotes.to_parquet(raw / "data.parquet", index=False)
    pd.DataFrame([{"Date": "2026-07-06"}, {"Date": "2026-07-10"}]).to_parquet(calendar / "data.parquet", index=False)
    pd.DataFrame([{"Date": "2026-07-06", "Code": "7203"}, {"Date": "2026-07-10", "Code": "7203"}]).to_parquet(listed / "data.parquet", index=False)


def _normalized_quotes(days: list[str], codes: tuple[str, ...] = ("13010",)) -> pd.DataFrame:
    rows = []
    for day in days:
        for code in codes:
            rows.append(
                {
                    "Date": day,
                    "Code": code,
                    "Open": 100.0,
                    "High": 101.0,
                    "Low": 99.0,
                    "Close": 100.0,
                    "Volume": 1000.0,
                    "PriceSource": "adjusted",
                    "SchemaVersion": 2,
                    "source_endpoint": "/v2/equities/bars/daily",
                    "target_date": day,
                    "code": code,
                    "business_key": code,
                    "endpoint": "daily_quotes_normalized",
                    "source": "jquants",
                }
            )
    return pd.DataFrame(rows)


def write_phase20_bi_market_authorities(root: Path, *, current_days: list[str], acquisition_days: list[str] | None = None) -> None:
    operations = root / "operations"
    normalized = operations / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily"
    raw = operations / "jquants" / "raw" / "jquants" / "equities_bars_daily"
    calendar = operations / "jquants" / "raw" / "jquants" / "trading_calendar"
    listed = operations / "jquants" / "raw" / "jquants" / "listed_issues"
    for path in (normalized, raw, calendar, listed):
        path.mkdir(parents=True, exist_ok=True)
    current = _normalized_quotes(current_days)
    current.to_parquet(normalized / "data.parquet", index=False)
    current.to_parquet(raw / "data.parquet", index=False)
    pd.DataFrame([{"Date": day, "HolidayDivision": "1"} for day in sorted(set(current_days + (acquisition_days or [])))]).to_parquet(calendar / "data.parquet", index=False)
    pd.DataFrame([{"Date": "2026-03-24", "Code": "13010"}]).to_parquet(listed / "data.parquet", index=False)
    if acquisition_days is None:
        return
    run_root = root / "market_data_acquisition" / "runs" / "jquants-acquisition-test"
    acquisition = _normalized_quotes(acquisition_days)
    for prefix in ("raw", "raw_normalized"):
        target = run_root / prefix / "jquants" / "equities_bars_daily"
        target.mkdir(parents=True, exist_ok=True)
        acquisition.to_parquet(target / "data.parquet", index=False)
    calendar_target = run_root / "raw" / "jquants" / "trading_calendar"
    calendar_target.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Date": day, "HolDiv": "1"} for day in acquisition_days]).to_parquet(calendar_target / "data.parquet", index=False)


def test_phase17_l_asof_resolver_excludes_physical_future_rows(tmp_path: Path) -> None:
    write_market_authorities(tmp_path / ".runtime")
    result = resolve_historical_market_data_asof(
        operations_root=tmp_path / ".runtime" / "operations",
        business_date="2026-07-06",
    )
    assert result.status == "PASS"
    normalized = next(item for item in result.authorities if item.authority == "normalized_ohlcv")
    assert normalized.physical_max_date == "2026-07-10"
    assert normalized.logical_max_date == "2026-07-06"
    assert normalized.future_rows_excluded_count == 1
    assert result.to_payload()["future_rows_excluded_from_consumer"] is True


def test_phase20_bi_historical_logical_input_uses_acquisition_source_when_operations_lookback_is_short(tmp_path: Path) -> None:
    current_days = pd.bdate_range("2026-02-16", "2026-03-24").strftime("%Y-%m-%d").tolist()
    acquisition_days = pd.bdate_range("2025-12-01", "2026-04-30").strftime("%Y-%m-%d").tolist()
    write_phase20_bi_market_authorities(tmp_path / ".runtime", current_days=current_days, acquisition_days=acquisition_days)

    logical = materialize_historical_logical_inputs(
        operations_root=tmp_path / ".runtime" / "operations",
        business_date="2026-03-24",
        evidence_root=tmp_path / "evidence",
        require_feature_lookback=True,
    )

    assert logical.status == "PASS"
    coverage = logical.resolution.feature_lookback_coverage or {}
    assert coverage["selected_source_role"] == "acquisition_staging"
    assert coverage["status"] == "PASS"
    frame = pd.read_parquet(Path(logical.logical_paths["normalized_ohlcv"]))
    assert frame["Date"].astype(str).min() == "2025-12-01"
    assert frame["Date"].astype(str).max() == "2026-03-24"
    assert "2026-03-25" not in set(frame["Date"].astype(str))


def test_phase20_bi_historical_asof_fails_closed_when_no_source_has_feature_lookback(tmp_path: Path) -> None:
    current_days = pd.bdate_range("2026-02-16", "2026-03-24").strftime("%Y-%m-%d").tolist()
    write_phase20_bi_market_authorities(tmp_path / ".runtime", current_days=current_days)

    result = resolve_historical_market_data_asof(
        operations_root=tmp_path / ".runtime" / "operations",
        business_date="2026-03-24",
        require_feature_lookback=True,
    )

    assert result.status == "HALT"
    assert result.reason == "historical_feature_lookback_insufficient"
    coverage = result.feature_lookback_coverage or {}
    assert coverage["status"] == "BLOCK"
    assert coverage["selected_source_role"] == "operations_canonical"
    assert "feature_lookback_insufficient" in coverage["candidate_sources"][0]["blocked_reasons"]


def test_phase17_l_asof_resolver_fails_closed_on_hash_mismatch(tmp_path: Path) -> None:
    write_market_authorities(tmp_path / ".runtime")
    result = resolve_historical_market_data_asof(
        operations_root=tmp_path / ".runtime" / "operations",
        business_date="2026-07-06",
        expected_hashes={"normalized_ohlcv": "not-the-real-hash"},
    )
    assert result.status == "HALT"
    normalized = next(item for item in result.authorities if item.authority == "normalized_ohlcv")
    assert normalized.reason == "source_hash_mismatch"


def test_phase17_l_asof_resolver_fails_closed_on_manifest_hash_mismatch(tmp_path: Path) -> None:
    write_market_authorities(tmp_path / ".runtime")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"ok": True}), encoding="utf-8")
    result = resolve_historical_market_data_asof(
        operations_root=tmp_path / ".runtime" / "operations",
        business_date="2026-07-06",
        manifest_refs={"normalized_ohlcv": str(manifest)},
        expected_manifest_hashes={"normalized_ohlcv": "not-the-real-hash"},
    )
    normalized = next(item for item in result.authorities if item.authority == "normalized_ohlcv")
    assert result.status == "HALT"
    assert normalized.reason == "manifest_hash_mismatch"


@dataclass(frozen=True)
class DummyContract:
    status: str = "PASS"
    reason: str = "requested_feature_artifacts_available"
    requested_feature_date: str = "2026-07-06"
    selected_feature_date: str = "2026-07-06"
    latest_available_market_date: str = "2026-07-06"
    carryover_used: bool = False
    carryover_reason: str = ""
    freshness_lag_business_days: int = 0
    freshness_limit_business_days: int = 1
    feature_artifact_dir: str = ""
    generated_feature_artifacts: dict[str, str] = None  # type: ignore[assignment]
    missing_feature_artifacts: tuple[str, ...] = ()
    requested_feature_artifact_dir: str = ""
    requested_missing_feature_artifacts: tuple[str, ...] = ()
    price_source_alignment: str = "selected_feature_date"
    consumer_ready: bool = True
    schema_version: str = "runtime_v2_feature_contract_v1"
    candidate_schema_status: str = "READY"
    candidate_missing_columns: tuple[str, ...] = ()
    opportunity_schema_status: str = "READY"
    pm_schema_status: str = "READY"
    consumer_readiness_artifact_path: str = ""


@dataclass(frozen=True)
class DummyMarketEvidence:
    status: str = "READY"
    reason: str = "market_evidence_ready"
    latest_expected_trading_date: str = "2026-07-06"
    latest_available_market_date: str = "2026-07-06"
    artifact_path: str = ""
    latest_pointer_path: str = ""
    history_artifact_path: str = ""
    market_date: str = "2026-07-06"
    market_freshness_status: str = "READY"
    quote_status: str = "READY"
    quote_count: int = 1
    missing_quote_count: int = 0
    market_summary_status: str = "READY"
    publication_status: str = "READY"
    provider_status: str = "READY"


def test_phase17_l_historical_market_refresh_uses_asof_view_and_run_scoped_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    write_market_authorities(tmp_path / ".runtime")
    acquisition_days = pd.bdate_range("2026-04-01", "2026-07-10").strftime("%Y-%m-%d").tolist()
    run_root = tmp_path / ".runtime" / "market_data_acquisition" / "runs" / "jquants-acquisition-test"
    acquisition = _normalized_quotes(acquisition_days, codes=("7203",))
    for prefix in ("raw", "raw_normalized"):
        target = run_root / prefix / "jquants" / "equities_bars_daily"
        target.mkdir(parents=True, exist_ok=True)
        acquisition.to_parquet(target / "data.parquet", index=False)
    calendar_target = run_root / "raw" / "jquants" / "trading_calendar"
    calendar_target.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Date": day, "HolDiv": "1"} for day in acquisition_days]).to_parquet(calendar_target / "data.parquet", index=False)
    evidence_roots: list[Path | None] = []

    def fake_operations_refresh(**kwargs):
        evidence_roots.append(kwargs.get("evidence_output_root"))
        return {
            "status": "BLOCK",
            "blocked_reasons": ["future_row_detected"],
            "latest_available_market_date": "2026-07-10",
            "data_quality_status": "BLOCK",
            "feature_freshness_status": "FEATURE_STALE",
            "jquants_api_fetch_executed": False,
            "canonical_normalized_updated": False,
            "feature_refresh_executed": False,
            "feature_refresh_status": "FEATURE_REFRESH_REQUIRED",
        }

    monkeypatch.setattr(pipeline, "_run_operations_market_refresh", fake_operations_refresh)
    monkeypatch.setattr(pipeline, "resolve_feature_date_contract", lambda **kwargs: DummyContract(generated_feature_artifacts={}))
    monkeypatch.setattr(pipeline, "write_feature_date_contract", lambda **kwargs: tmp_path / "contract.json")
    market_evidence_kwargs: list[dict] = []

    def fake_market_evidence(**kwargs):
        market_evidence_kwargs.append(kwargs)
        return DummyMarketEvidence()

    monkeypatch.setattr(pipeline, "produce_market_quote_evidence", fake_market_evidence)
    result = pipeline.run_runtime_v2_market_refresh_pipeline(
        business_date="2026-07-06",
        operations_root=tmp_path / ".runtime" / "operations",
        allow_api_fetch=False,
        mode="historical",
        runtime_test_context={
            "run_id": "runtime-test-fixture",
            "profile_id": "historical-smoke",
            "evidence_root": str(tmp_path / "reports" / "runtime_tests" / "runs" / "runtime-test-fixture"),
            "job": "market_refresh",
        },
    )
    assert result.status == "PASS"
    assert result.reason == "HISTORICAL_DATA_AS_OF_READY"
    assert result.latest_available_market_date == "2026-07-06"
    assert result.historical_asof_status == "PASS"
    assert "future_row_detected" not in result.blocked_reasons
    assert evidence_roots == [tmp_path / "reports" / "runtime_tests" / "runs" / "runtime-test-fixture" / "daily" / "2026-07-06" / "market_refresh"]
    assert Path(result.historical_asof_evidence_path).is_file()
    assert market_evidence_kwargs[0]["quote_source_path"] == (
        tmp_path
        / "reports"
        / "runtime_tests"
        / "runs"
        / "runtime-test-fixture"
        / "daily"
        / "2026-07-06"
        / "market_refresh"
        / "inputs"
        / "historical_asof"
        / "2026-07-06"
        / "raw_normalized"
        / "jquants"
        / "equities_bars_daily"
        / "data.parquet"
    )
    assert market_evidence_kwargs[0]["source_authority"]["source_role"] == "acquisition_staging"
    assert market_evidence_kwargs[0]["source_authority"]["future_rows_excluded"] is True


def test_phase17_l_demo_market_refresh_keeps_future_row_block(monkeypatch, tmp_path: Path) -> None:
    def fake_operations_refresh(**kwargs):
        return {
            "status": "BLOCK",
            "blocked_reasons": ["future_row_detected"],
            "latest_available_market_date": "2026-07-10",
            "data_quality_status": "BLOCK",
            "feature_refresh_status": "FEATURES_READY",
        }

    monkeypatch.setattr(pipeline, "_run_operations_market_refresh", fake_operations_refresh)
    monkeypatch.setattr(pipeline, "resolve_feature_date_contract", lambda **kwargs: DummyContract(generated_feature_artifacts={}))
    monkeypatch.setattr(pipeline, "write_feature_date_contract", lambda **kwargs: tmp_path / "contract.json")
    monkeypatch.setattr(pipeline, "produce_market_quote_evidence", lambda **kwargs: DummyMarketEvidence(provider_status="API_ERROR"))
    result = pipeline.run_runtime_v2_market_refresh_pipeline(
        business_date="2026-07-06",
        operations_root=tmp_path / ".runtime" / "operations",
        allow_api_fetch=False,
        mode="demo",
    )
    assert result.status == "BLOCKED"
    assert result.historical_asof_status == ""
    assert result.blocked_reasons == ("future_row_detected",)


def test_phase17_l_runner_passes_identity_and_uses_profile_only_as_expected_value(tmp_path: Path) -> None:
    runner = load_runner()
    root = tmp_path / ".runtime"
    (root / "operations" / "feature_date_contract").mkdir(parents=True)
    profile = runner.load_profile("historical-smoke")
    plan = runner.build_plan(
        profile=profile,
        runtime_root=root,
        evidence_root=tmp_path / "reports" / "runtime_tests",
        business_days=1,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id="runtime-test-fixture",
    )
    feature_evidence = plan["business_dates"][0]["feature_date_evidence"]
    command = plan["business_dates"][0]["jobs"][0]["command"]
    assert feature_evidence["source"] == "runtime_test_plan_schedule_expectation"
    assert feature_evidence["feature_date_authority_source"] == "not_yet_materialized_plan_expectation"
    assert feature_evidence["profile_value_used_as_authority"] is False
    assert "--runtime-test-run-id" in command
    assert command[command.index("--runtime-test-run-id") + 1] == "runtime-test-fixture"
    assert "--runtime-test-evidence-root" in command
