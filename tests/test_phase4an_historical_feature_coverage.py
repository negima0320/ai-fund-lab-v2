from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes
from ai_fund_lab_v2.data_store import create_storage_backend
from scripts.audit_phase4an_historical_feature_coverage import run_audit
from scripts.build_phase4an_historical_feature_coverage import (
    READY,
    build_historical_feature_rows,
    build_phase4an_historical_feature_coverage,
)


def test_phase4an_generates_historical_feature_coverage(tmp_path: Path) -> None:
    runtime_dir, al_summary = _prepare_runtime_fixture(tmp_path)

    summary = build_phase4an_historical_feature_coverage(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        input_format="jsonl",
        phase4al_summary_path=al_summary,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["feature_target_date_count"] == 30
    assert summary["label_target_date_count"] == 10
    assert summary["overlap_target_date_count"] == 10
    assert summary["expected_feature_target_date_min"] >= summary["actual_feature_target_date_min"]
    assert summary["expected_feature_target_date_max"] <= summary["actual_feature_target_date_max"]
    assert summary["generated_historical_feature_row_count"] == 60
    assert summary["schema_validation_status"] == "OK"
    assert summary["leakage_audit_status"] == "OK"
    assert summary["join_coverage_readiness"] is True
    assert summary["dataset_builder_executed"] is False
    assert summary["training_executed"] is False


def test_phase4an_feature_rows_use_only_past_rows() -> None:
    dates = _business_dates(date(2026, 3, 2), 5)
    normalized, _ = normalize_daily_quotes(_raw_records(dates, codes=("7203",)))

    rows = build_historical_feature_rows(normalized, source_snapshot_id="fixture")

    assert [row["target_date"] for row in rows] == dates
    assert all(row["data_end_date"] == row["target_date"] for row in rows)
    assert all(row["missing_flags_insufficient_history"] is True for row in rows)
    assert not any("future_return_5d" in row for row in rows)


def test_phase4an_audit_completes(tmp_path: Path) -> None:
    runtime_dir, al_summary = _prepare_runtime_fixture(tmp_path)
    summary_path = tmp_path / "reports" / "phase4an_historical_feature_coverage_summary.json"
    build_phase4an_historical_feature_coverage(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        input_format="jsonl",
        phase4al_summary_path=al_summary,
    )

    result = run_audit(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        summary_path=summary_path,
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "complete"
    assert result["readiness_status"] == READY


def test_phase4an_report_documents_scope() -> None:
    report = Path("docs/phase_reports/phase4an_historical_feature_coverage.md").read_text(encoding="utf-8")

    assert "READY_FOR_DATASET_BUILDER_RETRY" in report
    assert "Phase4-AO" in report
    assert "does not change labels" in report


def _prepare_runtime_fixture(tmp_path: Path) -> tuple[Path, Path]:
    runtime_dir = tmp_path / "runtime"
    dates = _business_dates(date(2026, 3, 2), 30)
    normalized, _ = normalize_daily_quotes(_raw_records(dates, codes=("7203", "6758")))
    normalized_path = (
        runtime_dir
        / "data"
        / "raw_normalized_real_runtime"
        / "jquants"
        / "equities_bars_daily"
        / "data.jsonl"
    )
    create_storage_backend("jsonl").write_records(normalized_path, normalized)
    label_path = runtime_dir / "candidate_ai" / "labels" / "labels.json"
    label_path.parent.mkdir(parents=True)
    label_path.write_text(
        json.dumps({"rows": [{"target_date": target_date, "code": "7203"} for target_date in dates[:10]]}),
        encoding="utf-8",
    )
    al_summary = tmp_path / "phase4al.json"
    al_summary.write_text(
        json.dumps({"readiness_status": "READY_FOR_DATASET_BUILDER", "label_output_path": str(label_path)}),
        encoding="utf-8",
    )
    return runtime_dir, al_summary


def _business_dates(start: date, count: int) -> list[str]:
    values: list[str] = []
    current = start
    while len(values) < count:
        if current.weekday() < 5:
            values.append(current.isoformat())
        current += timedelta(days=1)
    return values


def _raw_records(dates: list[str], *, codes: tuple[str, ...]) -> list[dict[str, object]]:
    records = []
    for code in codes:
        for index, target_date in enumerate(dates, start=1):
            close = 100.0 + index
            records.append(
                {
                    "Date": target_date,
                    "Code": code,
                    "AdjO": close - 1,
                    "AdjH": close + 2,
                    "AdjL": close - 3,
                    "AdjC": close,
                    "AdjVo": 1000.0 + index,
                    "O": close - 1,
                    "H": close + 2,
                    "L": close - 3,
                    "C": close,
                    "Vo": 1000.0 + index,
                }
            )
    return records
