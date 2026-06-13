from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from scripts.audit_phase4bb_long_history_normalized import run_audit
from scripts.rebuild_phase4bb_long_history_normalized import (
    BLOCKED_COVERAGE,
    BLOCKED_RAW_SCHEMA,
    READY,
    rebuild_phase4bb_long_history_normalized,
)


def test_phase4bb_rebuilds_long_history_isolated_normalized(tmp_path: Path) -> None:
    runtime_dir, ba_summary = _prepare_runtime_fixture(tmp_path, business_day_count=80)
    mock_path = runtime_dir / "data" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.jsonl"
    before = mock_path.read_text(encoding="utf-8")

    summary = rebuild_phase4bb_long_history_normalized(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        output_format="jsonl",
        phase4ba_summary_path=ba_summary,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["normalized_rebuild_executed"] is True
    assert summary["raw_row_count"] == 160
    assert summary["normalized_row_count"] == 160
    assert summary["price_missing_excluded_count"] == 0
    assert summary["normalization_error_count"] == 0
    assert summary["business_day_count"] == 80
    assert summary["code_count"] == 2
    assert summary["duplicate_date_code_count"] == 0
    assert summary["schema_mapping_status"] == "OK"
    assert summary["mock_path_unchanged"] is True
    assert summary["promotion_performed"] is False
    assert summary["reader_switch_performed"] is False
    assert summary["feature_generation_executed"] is False
    assert summary["label_generation_executed"] is False
    assert summary["dataset_rebuild_executed"] is False
    assert summary["training_executed"] is False
    assert Path(summary["isolated_output_path"]).is_file()
    assert Path(summary["manifest_path"]).is_file()
    assert mock_path.read_text(encoding="utf-8") == before


def test_phase4bb_blocks_raw_schema_key_errors(tmp_path: Path) -> None:
    runtime_dir, ba_summary = _prepare_runtime_fixture(tmp_path, business_day_count=80, malformed=True)

    summary = rebuild_phase4bb_long_history_normalized(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        output_format="jsonl",
        phase4ba_summary_path=ba_summary,
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == BLOCKED_RAW_SCHEMA
    assert summary["invalid_key_record_count"] > 0
    assert not Path(summary["isolated_output_path"]).exists()


def test_phase4bb_blocks_when_ba_coverage_not_sufficient(tmp_path: Path) -> None:
    runtime_dir, ba_summary = _prepare_runtime_fixture(tmp_path, business_day_count=80, coverage_sufficient=False)

    summary = rebuild_phase4bb_long_history_normalized(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        output_format="jsonl",
        phase4ba_summary_path=ba_summary,
    )

    assert summary["readiness_status"] == BLOCKED_COVERAGE
    assert summary["formal_training_coverage_sufficient_after_normalization"] is False


def test_phase4bb_audit_completes(tmp_path: Path) -> None:
    runtime_dir, ba_summary = _prepare_runtime_fixture(tmp_path, business_day_count=80)
    summary_path = tmp_path / "reports" / "phase4bb_long_history_normalized_summary.json"
    rebuild_phase4bb_long_history_normalized(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        output_format="jsonl",
        phase4ba_summary_path=ba_summary,
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
    assert result["checks"]["mock_path_unchanged"] is True
    assert result["checks"]["no_downstream_execution"] is True


def _prepare_runtime_fixture(
    tmp_path: Path,
    *,
    business_day_count: int,
    malformed: bool = False,
    coverage_sufficient: bool = True,
) -> tuple[Path, Path]:
    runtime_dir = tmp_path / "runtime"
    raw_root = runtime_dir / "data" / "raw" / "jquants" / "equities_bars_daily"
    response_dir = raw_root / "responses"
    response_dir.mkdir(parents=True)
    raw_root.mkdir(parents=True, exist_ok=True)
    (raw_root / "manifest.json").write_text(
        json.dumps({"completed_request_count": business_day_count, "phase": "Phase4-AZ"}),
        encoding="utf-8",
    )
    dates = _business_dates(date(2021, 6, 14), business_day_count)
    for target_date in dates:
        rows = [_raw_quote(target_date, "7203"), _raw_quote(target_date, "6758")]
        if malformed:
            rows[0].pop("Code")
        (response_dir / f"{target_date}_page_001.json").write_text(
            json.dumps({"date": target_date, "payload": {"data": rows}}, ensure_ascii=True),
            encoding="utf-8",
        )

    mock_path = runtime_dir / "data" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.jsonl"
    mock_path.parent.mkdir(parents=True)
    mock_path.write_text('{"Date":"2020-01-01","Code":"MOCK"}\n', encoding="utf-8")

    ba_summary = tmp_path / "phase4ba.json"
    ba_summary.write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_LONG_HISTORY_NORMALIZED_REBUILD",
                "formal_training_coverage_sufficient": coverage_sufficient,
                "fetched_business_day_count": business_day_count,
                "fetched_date_min": dates[0],
                "fetched_date_max": dates[-1],
                "first_trainable_target_date": dates[60] if len(dates) > 60 else None,
                "last_label_target_date": dates[-21] if len(dates) > 21 else None,
            }
        ),
        encoding="utf-8",
    )
    return runtime_dir, ba_summary


def _business_dates(start: date, count: int) -> list[str]:
    values: list[str] = []
    current = start
    while len(values) < count:
        if current.weekday() < 5:
            values.append(current.isoformat())
        current += timedelta(days=1)
    return values


def _raw_quote(target_date: str, code: str) -> dict[str, object]:
    return {
        "Date": target_date,
        "Code": code,
        "AdjO": 100.0,
        "AdjH": 110.0,
        "AdjL": 95.0,
        "AdjC": 105.0,
        "AdjVo": 1000.0,
        "O": 100.0,
        "H": 110.0,
        "L": 95.0,
        "C": 105.0,
        "Vo": 1000.0,
    }
