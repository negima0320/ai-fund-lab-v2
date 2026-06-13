from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes
from ai_fund_lab_v2.data_store import create_storage_backend
from scripts.audit_phase4ak_real_runtime_features import run_audit
from scripts.build_phase4ak_real_runtime_features import (
    READY,
    REQUIRED_AK_FEATURE_COLUMNS,
    build_phase4ak_real_runtime_features,
    build_real_runtime_feature_rows,
)


def test_phase4ak_builds_real_runtime_features(tmp_path: Path) -> None:
    runtime_dir, phase4aj_summary = _prepare_runtime_fixture(tmp_path, business_day_count=60)

    summary = build_phase4ak_real_runtime_features(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        input_format="jsonl",
        phase4aj_summary_path=phase4aj_summary,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["feature_generation_executed"] is True
    assert summary["schema_validation_status"] == "OK"
    assert summary["leakage_audit_status"] == "OK"
    assert summary["feature_row_count"] == 2
    assert summary["eligible_count"] == 1
    assert summary["excluded_count"] == 1
    assert summary["feature_column_count"] >= len(REQUIRED_AK_FEATURE_COLUMNS)
    assert summary["forbidden_feature_detected"] is False
    assert summary["future_column_detected"] is False
    assert summary["label_column_detected"] is False
    assert summary["label_generation_executed"] is False
    assert summary["training_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    assert Path(summary["feature_output_path"]).is_file()
    assert Path(summary["manifest_path"]).is_file()
    assert Path(summary["audit_path"]).is_file()


def test_phase4ak_feature_rows_include_required_columns() -> None:
    normalized, _ = normalize_daily_quotes(_raw_records(_business_dates(date(2026, 3, 2), 60), codes=("7203",)))

    rows = build_real_runtime_feature_rows(normalized, source_snapshot_id="fixture")

    assert rows
    assert all(column in rows[0] for column in REQUIRED_AK_FEATURE_COLUMNS)
    assert rows[0]["universe_eligible"] is True
    assert rows[0]["excluded_reason"] == ""
    assert rows[0]["price_momentum_return_5d"] is not None
    assert rows[0]["price_momentum_return_60d"] is not None


def test_phase4ak_audit_completes(tmp_path: Path) -> None:
    runtime_dir, phase4aj_summary = _prepare_runtime_fixture(tmp_path, business_day_count=60)
    summary_path = tmp_path / "reports" / "phase4ak_real_runtime_feature_generation_summary.json"
    build_phase4ak_real_runtime_features(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        input_format="jsonl",
        phase4aj_summary_path=phase4aj_summary,
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
    assert (tmp_path / "audit.json").is_file()
    assert (tmp_path / "audit.md").is_file()


def test_phase4ak_report_documents_scope() -> None:
    report = Path("docs/phase_reports/phase4ak_real_runtime_feature_generation.md").read_text(encoding="utf-8")

    assert "READY_FOR_LABEL_GENERATION" in report
    assert ".runtime/candidate_ai/features/" in report
    assert "price_momentum_return_60d" in report
    assert "label_generation_executed" in report
    assert "Phase4-AL" in report


def _prepare_runtime_fixture(tmp_path: Path, *, business_day_count: int) -> tuple[Path, Path]:
    runtime_dir = tmp_path / "runtime"
    dates = _business_dates(date(2026, 3, 2), business_day_count)
    raw = _raw_records(dates, codes=("7203",))
    raw.extend(_raw_records(dates[:20], codes=("9999",)))
    normalized, _ = normalize_daily_quotes(raw)
    output_path = (
        runtime_dir
        / "data"
        / "raw_normalized_real_runtime"
        / "jquants"
        / "equities_bars_daily"
        / "data.jsonl"
    )
    create_storage_backend("jsonl").write_records(output_path, normalized)
    manifest_path = output_path.parent / "manifest.json"
    manifest_path.write_text(json.dumps({"phase": "Phase4-AJ", "normalized_row_count": len(normalized)}), encoding="utf-8")
    phase4aj_summary = tmp_path / "phase4aj.json"
    phase4aj_summary.write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_REAL_RUNTIME_FEATURE_GENERATION",
                "raw_row_count": len(normalized),
                "normalized_row_count": len(normalized),
                "business_day_count": business_day_count,
                "date_min": dates[0],
                "date_max": dates[-1],
                "isolated_manifest_path": str(manifest_path),
            }
        ),
        encoding="utf-8",
    )
    return runtime_dir, phase4aj_summary


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
        code_offset = int(code[-1])
        for index, target_date in enumerate(dates, start=1):
            close = 100.0 + index + code_offset
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
