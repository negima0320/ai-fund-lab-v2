from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes
from ai_fund_lab_v2.data_store import create_storage_backend
from scripts.audit_phase4al_labels import run_audit
from scripts.build_phase4al_labels import (
    LABEL_COLUMNS,
    READY,
    build_label_rows,
    build_phase4al_labels,
)


def test_phase4al_builds_separate_label_table(tmp_path: Path) -> None:
    runtime_dir, phase4ak_summary = _prepare_runtime_fixture(tmp_path)
    feature_path = json.loads(phase4ak_summary.read_text(encoding="utf-8"))["feature_output_path"]
    before = Path(feature_path).read_text(encoding="utf-8")

    summary = build_phase4al_labels(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        input_format="jsonl",
        phase4ak_summary_path=phase4ak_summary,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["label_generation_executed"] is True
    assert summary["label_row_count"] > 0
    assert summary["label_column_count"] == len(LABEL_COLUMNS)
    assert summary["future_return_5d_count"] == summary["label_row_count"]
    assert summary["future_return_10d_count"] == summary["label_row_count"]
    assert summary["future_return_20d_count"] == summary["label_row_count"]
    assert summary["future_max_return_20d_count"] == summary["label_row_count"]
    assert summary["future_max_drawdown_20d_count"] == summary["label_row_count"]
    assert summary["top_decile_20d_count"] > 0
    assert summary["momentum_candidate_label_count"] > 0
    assert summary["feature_table_modified"] is False
    assert summary["feature_table_joined"] is False
    assert summary["leakage_audit_status"] == "OK"
    assert "/candidate_ai/labels/" in summary["label_output_path"].replace("\\", "/")
    assert Path(feature_path).read_text(encoding="utf-8") == before


def test_phase4al_label_rows_have_expected_values() -> None:
    dates = _business_dates(date(2026, 3, 2), 30)
    normalized, _ = normalize_daily_quotes(_raw_records(dates, codes=("7203", "6758")))

    rows = build_label_rows(normalized, source_snapshot_id="fixture")

    assert rows
    assert all(column in rows[0] for column in LABEL_COLUMNS)
    assert rows[0]["future_start_date"] > rows[0]["target_date"]
    assert rows[0]["future_end_date"] > rows[0]["target_date"]
    assert isinstance(rows[0]["top_decile_20d"], bool)
    assert isinstance(rows[0]["downside_bad_20d"], bool)
    assert isinstance(rows[0]["momentum_candidate_label"], bool)


def test_phase4al_audit_completes(tmp_path: Path) -> None:
    runtime_dir, phase4ak_summary = _prepare_runtime_fixture(tmp_path)
    summary_path = tmp_path / "reports" / "phase4al_label_generation_summary.json"
    build_phase4al_labels(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        input_format="jsonl",
        phase4ak_summary_path=phase4ak_summary,
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


def test_phase4al_report_documents_scope() -> None:
    report = Path("docs/phase_reports/phase4al_label_generation.md").read_text(encoding="utf-8")

    assert "READY_FOR_DATASET_BUILDER" in report
    assert ".runtime/candidate_ai/labels/" in report
    assert "feature table is not modified" in report
    assert "Phase4-AM" in report


def _prepare_runtime_fixture(tmp_path: Path) -> tuple[Path, Path]:
    runtime_dir = tmp_path / "runtime"
    dates = _business_dates(date(2026, 3, 2), 40)
    normalized, _ = normalize_daily_quotes(_raw_records(dates, codes=("7203", "6758", "9984")))
    normalized_path = (
        runtime_dir
        / "data"
        / "raw_normalized_real_runtime"
        / "jquants"
        / "equities_bars_daily"
        / "data.jsonl"
    )
    create_storage_backend("jsonl").write_records(normalized_path, normalized)

    feature_path = runtime_dir / "candidate_ai" / "features" / "phase4ak_features.json"
    feature_path.parent.mkdir(parents=True)
    feature_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "target_date": dates[-1],
                        "as_of_date": dates[-1],
                        "code": "7203",
                        "feature_version": "fixture",
                        "source_snapshot_id": "fixture",
                        "universe_eligible": True,
                        "excluded_reason": "",
                        "price_momentum_return_5d": 0.1,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    phase4ak_summary = tmp_path / "phase4ak.json"
    phase4ak_summary.write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_LABEL_GENERATION",
                "feature_output_path": str(feature_path),
                "manifest_path": str(runtime_dir / "candidate_ai" / "manifests" / "phase4ak_manifest.json"),
            }
        ),
        encoding="utf-8",
    )
    return runtime_dir, phase4ak_summary


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
    for code_index, code in enumerate(codes, start=1):
        for index, target_date in enumerate(dates, start=1):
            close = 100.0 + index * code_index
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
