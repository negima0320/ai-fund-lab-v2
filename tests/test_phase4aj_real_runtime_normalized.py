from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from scripts.audit_phase4aj_real_runtime_normalized import run_audit
from scripts.rebuild_phase4aj_real_runtime_normalized import (
    BLOCKED_RAW_SCHEMA,
    READY,
    rebuild_phase4aj_real_runtime_normalized,
)


def test_phase4aj_rebuilds_isolated_real_runtime_normalized_from_raw_responses(tmp_path: Path) -> None:
    runtime_dir, phase4ai_summary = _prepare_runtime_fixture(tmp_path, business_day_count=60)
    mock_path = runtime_dir / "data" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.jsonl"
    before = mock_path.read_text(encoding="utf-8")

    summary = rebuild_phase4aj_real_runtime_normalized(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        output_format="jsonl",
        phase4ai_summary_path=phase4ai_summary,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["raw_row_count"] == 120
    assert summary["normalized_row_count"] == 120
    assert summary["business_day_count"] == 60
    assert summary["code_count"] == 2
    assert summary["normalization_error_count"] == 0
    assert summary["schema_mapping_status"] == "OK"
    assert summary["promotion_status"] == "not_promoted"
    assert summary["promotion_performed"] is False
    assert summary["reader_switch_performed"] is False
    assert summary["mock_path_unchanged"] is True
    assert summary["feature_generation_executed"] is False
    assert summary["label_generation_executed"] is False
    assert summary["training_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    assert Path(summary["isolated_output_path"]).is_file()
    assert Path(summary["isolated_manifest_path"]).is_file()
    assert mock_path.read_text(encoding="utf-8") == before


def test_phase4aj_blocks_raw_schema_key_errors(tmp_path: Path) -> None:
    runtime_dir, phase4ai_summary = _prepare_runtime_fixture(tmp_path, business_day_count=60, malformed=True)

    summary = rebuild_phase4aj_real_runtime_normalized(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        output_format="jsonl",
        phase4ai_summary_path=phase4ai_summary,
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == BLOCKED_RAW_SCHEMA
    assert summary["invalid_key_record_count"] > 0
    assert not Path(summary["isolated_output_path"]).exists()


def test_phase4aj_audit_completes(tmp_path: Path) -> None:
    runtime_dir, phase4ai_summary = _prepare_runtime_fixture(tmp_path, business_day_count=60)
    summary_path = tmp_path / "reports" / "phase4aj_real_runtime_normalized_summary.json"
    rebuild_phase4aj_real_runtime_normalized(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        output_format="jsonl",
        phase4ai_summary_path=phase4ai_summary,
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


def test_phase4aj_report_documents_scope() -> None:
    report = Path("docs/phase_reports/phase4aj_real_runtime_normalized.md").read_text(encoding="utf-8")

    assert "READY_FOR_REAL_RUNTIME_FEATURE_GENERATION" in report
    assert ".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/" in report
    assert ".runtime/data/raw_normalized/jquants/equities_bars_daily/" in report
    assert "promotion_performed = false" in report
    assert "reader_switch_performed = false" in report
    assert "Phase4-AK" in report


def _prepare_runtime_fixture(
    tmp_path: Path,
    *,
    business_day_count: int,
    malformed: bool = False,
) -> tuple[Path, Path]:
    runtime_dir = tmp_path / "runtime"
    raw_root = runtime_dir / "data" / "raw" / "jquants" / "equities_bars_daily"
    response_dir = raw_root / "responses"
    response_dir.mkdir(parents=True)
    raw_root.mkdir(parents=True, exist_ok=True)
    (raw_root / "manifest.json").write_text(
        json.dumps({"planned_request_count": business_day_count, "completed_request_count": business_day_count}),
        encoding="utf-8",
    )
    dates = _business_dates(date(2026, 3, 2), business_day_count)
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

    phase4ai_summary = tmp_path / "phase4ai.json"
    phase4ai_summary.write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_REAL_RUNTIME_NORMALIZED_REBUILD",
                "fetched_non_empty_trading_day_count": business_day_count,
                "required_non_empty_trading_day_count": 60,
                "row_count": business_day_count * 2,
            }
        ),
        encoding="utf-8",
    )
    return runtime_dir, phase4ai_summary


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
