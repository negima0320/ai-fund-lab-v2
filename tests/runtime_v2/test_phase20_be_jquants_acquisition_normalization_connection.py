from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.runtime_v2.market_data_acquisition import (
    ACQUISITION_CONNECTION_VERSION,
    PRODUCTION_REFRESH_ADAPTER_VERSION,
    resume_acquisition,
    run_acquisition,
    validate_staging_source,
)


def _v2_row(day: str, code: str = "13010") -> dict[str, Any]:
    return {
        "Date": day,
        "Code": code,
        "Open": 100.0,
        "High": 105.0,
        "Low": 95.0,
        "Close": 102.0,
        "Volume": 1000.0,
        "AdjustmentOpen": 110.0,
        "AdjustmentHigh": 115.0,
        "AdjustmentLow": 105.0,
        "AdjustmentClose": 112.0,
        "AdjustmentVolume": 900.0,
    }


class V2Fetcher:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows
        self.calls: list[str | None] = []

    def fetch_daily_quotes(self, *, date: str | None = None, **_kwargs: Any) -> dict[str, Any]:
        self.calls.append(date)
        rows = self.rows if self.rows is not None else [_v2_row(str(date))]
        return {"data": rows}


def test_phase20_be_fixture_single_day_run_writes_raw_and_normalized_staging(tmp_path: Path) -> None:
    result = run_acquisition(
        runtime_root=tmp_path / ".runtime",
        start_date="2026-07-01",
        end_date="2026-07-01",
        run_id="be-single-day",
        staging_root=tmp_path / "runs",
        evidence_root=tmp_path / "evidence",
        confirm=True,
        explicit_fetch_confirm=True,
        fetcher=V2Fetcher(),
        sleep=lambda _seconds: None,
    )

    raw_path = Path(result["raw_output_path"])
    normalized_path = Path(result["normalized_output_path"])
    raw = pd.read_parquet(raw_path)
    normalized = pd.read_parquet(normalized_path)
    state = json.loads((tmp_path / "runs" / "be-single-day" / "state.json").read_text(encoding="utf-8"))

    assert result["final_judgment"] == "ACQUISITION_SOURCE_READY"
    assert result["acquisition_connection_version"] == ACQUISITION_CONNECTION_VERSION
    assert result["production_refresh_adapter_version"] == PRODUCTION_REFRESH_ADAPTER_VERSION
    assert result["processing_authority"] == "PRODUCTION_MARKET_REFRESH_CORE"
    assert raw_path.is_file()
    assert normalized_path.is_file()
    assert raw.iloc[0]["O"] == 100.0
    assert raw.iloc[0]["AdjO"] == 110.0
    assert normalized.iloc[0]["Open"] == 110.0
    assert normalized.iloc[0]["PriceSource"] == "adjusted"
    assert len(raw) == len(normalized) == 1
    assert state["chunks"][0]["status"] == "COMPLETED"
    assert state["chunks"][0]["processing_authority"] == "PRODUCTION_MARKET_REFRESH_CORE"
    assert state["chunks"][0]["requests"][0]["status"] == "COMPLETED"
    assert (tmp_path / "runs" / "be-single-day" / "market_refresh_manifests").is_dir()
    assert result["runtime_market_data_mutated"] is False


def test_phase20_be_normalization_failure_keeps_raw_artifact(tmp_path: Path) -> None:
    result = run_acquisition(
        runtime_root=tmp_path / ".runtime",
        start_date="2026-07-01",
        end_date="2026-07-01",
        run_id="be-normalization-failure",
        staging_root=tmp_path / "runs",
        evidence_root=tmp_path / "evidence",
        confirm=True,
        explicit_fetch_confirm=True,
        fetcher=V2Fetcher(rows=[{"Date": "2026-07-01", "Code": "13010", "Open": 100.0, "High": 99.0, "Low": 95.0, "Close": 102.0, "Volume": 1000.0}]),
        sleep=lambda _seconds: None,
    )

    state = json.loads((tmp_path / "runs" / "be-normalization-failure" / "state.json").read_text(encoding="utf-8"))
    assert result["status"] == "BLOCK"
    assert result["final_judgment"] == "ACQUISITION_SOURCE_BLOCKED"
    assert Path(result["raw_output_path"]).is_file()
    assert state["chunks"][0]["status"] == "NORMALIZATION_FAILED"
    assert "ohlc_integrity_failed" in result["final_validation"]["blocked_reasons"]


def test_phase20_be_missing_required_raw_fields_keeps_raw_and_blocks_normalization(tmp_path: Path) -> None:
    result = run_acquisition(
        runtime_root=tmp_path / ".runtime",
        start_date="2026-07-01",
        end_date="2026-07-01",
        run_id="be-missing-fields",
        staging_root=tmp_path / "runs",
        evidence_root=tmp_path / "evidence",
        confirm=True,
        explicit_fetch_confirm=True,
        fetcher=V2Fetcher(rows=[{"Date": "2026-07-01", "Code": "13010"}]),
        sleep=lambda _seconds: None,
    )

    assert result["status"] == "BLOCK"
    assert Path(result["raw_output_path"]).is_file()
    assert "normalized_inventory_not_pass" in result["blocked_reasons"] or "requested_start_coverage_missing" in result["blocked_reasons"]


def test_phase20_be_duplicate_normalized_rows_block_validation(tmp_path: Path) -> None:
    path = tmp_path / "normalized.parquet"
    rows = [
        {
            "Date": "2026-07-01",
            "Code": "13010",
            "Open": 100.0,
            "High": 101.0,
            "Low": 99.0,
            "Close": 100.0,
            "Volume": 1000.0,
            "PriceSource": "adjusted",
            "SchemaVersion": 2,
            "source_endpoint": "/v2/equities/bars/daily",
            "target_date": "2026-07-01",
            "code": "13010",
            "business_key": "13010",
            "endpoint": "daily_quotes_normalized",
            "source": "jquants",
        }
    ]
    pd.DataFrame(rows + rows).to_parquet(path, index=False)

    result = validate_staging_source(normalized_path=path, requested_start_date="2026-07-01", requested_end_date="2026-07-01")

    assert result["status"] == "BLOCK"
    assert "duplicate_date_code_keys" in result["blocked_reasons"]


def test_phase20_be_legacy_bd_probe_run_requires_new_run_id(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    staging_root = tmp_path / "runs"
    run_root = staging_root / "jquants-acquisition-20260701-bd-probe"
    run_root.mkdir(parents=True)
    plan = {
        "schema_version": "phase20_bc_jquants_market_data_acquisition.v1",
        "request_contract_version": "phase20_bd_jquants_daily_quotes_request.v1",
        "acquisition_run_id": "jquants-acquisition-20260701-bd-probe",
        "requested_start_date": "2026-07-01",
        "requested_end_date": "2026-07-01",
        "endpoint": "/v2/equities/bars/daily",
        "chunk_strategy": "month",
        "blocked_reasons": [],
    }
    state = {
        "schema_version": "phase20_bc_jquants_market_data_acquisition_state.v1",
        "request_contract_version": "phase20_bd_jquants_daily_quotes_request.v1",
        "status": "BLOCK",
        "binding": {
            "schema_version": plan["schema_version"],
            "request_contract_version": plan["request_contract_version"],
            "requested_start_date": plan["requested_start_date"],
            "requested_end_date": plan["requested_end_date"],
            "endpoint": plan["endpoint"],
            "chunk_strategy": plan["chunk_strategy"],
        },
        "chunks": [],
    }
    (run_root / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    (run_root / "state.json").write_text(json.dumps(state), encoding="utf-8")

    result = resume_acquisition(
        runtime_root=runtime_root,
        run_id="jquants-acquisition-20260701-bd-probe",
        staging_root=staging_root,
        evidence_root=tmp_path / "evidence",
        confirm=True,
        explicit_fetch_confirm=True,
        fetcher=V2Fetcher(),
    )

    assert result["status"] == "BLOCK"
    assert result["final_judgment"] == "LEGACY_RUN_RAW_ARTIFACT_MISSING"
    assert "NEW_RUN_REQUIRED" in result["blocked_reasons"]
