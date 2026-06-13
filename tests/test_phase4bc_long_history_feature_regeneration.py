from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes
from ai_fund_lab_v2.data_store import create_storage_backend
from scripts.audit_phase4bc_long_history_features import run_audit
from scripts.build_phase4bc_long_history_features import (
    READY,
    REQUIRED_AK_FEATURE_COLUMNS,
    build_long_history_feature_frame,
    build_phase4bc_long_history_features,
)


def test_phase4bc_builds_long_history_features(tmp_path: Path) -> None:
    runtime_dir, bb_summary = _prepare_runtime_fixture(tmp_path, business_day_count=220)

    summary = build_phase4bc_long_history_features(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        input_format="jsonl",
        output_format="jsonl",
        phase4bb_summary_path=bb_summary,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["feature_generation_executed"] is True
    assert summary["feature_row_count"] == 440
    assert summary["target_date_count"] == 220
    assert summary["feature_column_count"] >= len(REQUIRED_AK_FEATURE_COLUMNS)
    assert summary["schema_validation_status"] == "OK"
    assert summary["leakage_audit_status"] == "OK"
    assert summary["future_column_detected"] is False
    assert summary["label_column_detected"] is False
    assert summary["all_null_feature_count_train"] == 0
    assert summary["feature_variance_available_train"] is True
    assert summary["at_null_constant_problem_resolved"] is True
    assert summary["label_generation_executed"] is False
    assert summary["dataset_rebuild_executed"] is False
    assert summary["training_executed"] is False
    assert Path(summary["feature_output_path"]).is_file()
    assert Path(summary["manifest_path"]).is_file()
    assert Path(summary["audit_path"]).is_file()


def test_phase4bc_feature_frame_uses_past_rows_only() -> None:
    import pandas as pd

    dates = _business_dates(date(2021, 6, 14), 65)
    normalized, _ = normalize_daily_quotes(_raw_records(dates, codes=("7203",)))
    frame = build_long_history_feature_frame(pd.DataFrame(normalized), source_snapshot_id="fixture")

    row_59 = frame.iloc[58]
    row_60 = frame.iloc[59]

    assert bool(row_59["missing_flags_insufficient_history"]) is True
    assert bool(row_59["universe_eligible"]) is False
    assert bool(row_60["missing_flags_insufficient_history"]) is False
    assert bool(row_60["universe_eligible"]) is True
    assert row_60["data_end_date"] == row_60["target_date"]
    assert "future_return_5d" not in frame.columns
    assert "momentum_candidate_label" not in frame.columns


def test_phase4bc_audit_completes(tmp_path: Path) -> None:
    runtime_dir, bb_summary = _prepare_runtime_fixture(tmp_path, business_day_count=220)
    summary_path = tmp_path / "reports" / "phase4bc_long_history_feature_regeneration_summary.json"
    build_phase4bc_long_history_features(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        input_format="jsonl",
        output_format="jsonl",
        phase4bb_summary_path=bb_summary,
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
    assert result["checks"]["at_problem_resolved"] is True


def test_phase4bc_report_documents_scope() -> None:
    report = Path("docs/phase_reports/phase4bc_long_history_feature_regeneration.md").read_text(encoding="utf-8")

    assert "READY_FOR_LONG_HISTORY_LABEL_REGENERATION" in report
    assert "Phase4-BD" in report
    assert "label_generation_executed: `False`" in report
    assert "training_executed: `False`" in report


def _prepare_runtime_fixture(tmp_path: Path, *, business_day_count: int) -> tuple[Path, Path]:
    runtime_dir = tmp_path / "runtime"
    dates = _business_dates(date(2021, 6, 14), business_day_count)
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
    manifest_path = normalized_path.parent / "manifest.json"
    manifest_path.write_text(json.dumps({"phase": "Phase4-BB", "normalized_row_count": len(normalized)}), encoding="utf-8")
    bb_summary = tmp_path / "phase4bb.json"
    bb_summary.write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_LONG_HISTORY_FEATURE_REGENERATION",
                "normalized_row_count": len(normalized),
                "business_day_count": business_day_count,
                "date_min": dates[0],
                "date_max": dates[-1],
                "manifest_path": str(manifest_path),
            }
        ),
        encoding="utf-8",
    )
    return runtime_dir, bb_summary


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
                    "AdjVo": 1000.0 + index + code_offset,
                    "O": close - 1,
                    "H": close + 2,
                    "L": close - 3,
                    "C": close,
                    "Vo": 1000.0 + index + code_offset,
                }
            )
    return records
