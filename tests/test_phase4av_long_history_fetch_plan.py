from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from scripts.audit_phase4av_long_history_fetch_plan import (
    BLOCKED_INCONSISTENCY,
    ENDPOINT,
    READY,
    audit_phase4av_long_history_fetch_plan,
    count_business_days,
    subtract_business_days,
)


def test_phase4av_creates_long_history_fetch_plan(tmp_path: Path) -> None:
    au_summary = _write_au_summary(tmp_path, readiness_status="READY_FOR_LONG_HISTORY_FETCH_PLAN")

    summary = audit_phase4av_long_history_fetch_plan(
        runtime_dir=tmp_path / ".runtime",
        phase4au_summary_path=au_summary,
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        current_date=date(2026, 6, 13),
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["plan_created"] is True
    assert summary["preferred_fetch_end_date"] == "2026-06-12"
    assert summary["preferred_fetch_start_date"] < summary["required_training_start_date"]
    assert summary["required_training_start_date"] == "2021-06-01"
    assert summary["required_training_end_date"] < summary["preferred_fetch_end_date"]
    assert summary["lookback_business_days"] == 60
    assert summary["label_horizon_business_days"] == 20
    assert summary["estimated_request_count"] == summary["estimated_fetch_business_day_count"]
    assert summary["endpoint"] == ENDPOINT
    assert summary["formal_training_possible_after_fetch"] is True
    assert summary["phase4_completion_criteria_restored"] is True
    assert Path(summary["summary_path"]).is_file()
    assert Path(summary["report_path"]).is_file()


def test_phase4av_does_not_execute_fetch_training_or_trading(tmp_path: Path) -> None:
    au_summary = _write_au_summary(tmp_path, readiness_status="READY_FOR_LONG_HISTORY_FETCH_PLAN")

    summary = audit_phase4av_long_history_fetch_plan(
        runtime_dir=tmp_path / ".runtime",
        phase4au_summary_path=au_summary,
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        current_date=date(2026, 6, 13),
    )

    assert summary["api_call_performed"] is False
    assert summary["fetch_executed"] is False
    assert summary["normalized_rebuild_executed"] is False
    assert summary["feature_generation_executed"] is False
    assert summary["label_generation_executed"] is False
    assert summary["dataset_rebuild_executed"] is False
    assert summary["training_executed"] is False
    assert summary["inference_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False


def test_phase4av_blocks_when_au_is_not_ready_for_long_history(tmp_path: Path) -> None:
    au_summary = _write_au_summary(tmp_path, readiness_status="READY_FOR_DATASET_LOOKBACK_FILTER_PLAN")

    summary = audit_phase4av_long_history_fetch_plan(
        runtime_dir=tmp_path / ".runtime",
        phase4au_summary_path=au_summary,
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        current_date=date(2026, 6, 13),
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == BLOCKED_INCONSISTENCY
    assert summary["plan_created"] is False


def test_phase4av_business_day_helpers_are_deterministic() -> None:
    start = date(2021, 6, 1)

    assert subtract_business_days(start, 1).isoformat() == "2021-05-31"
    assert subtract_business_days(start, 60).weekday() < 5
    assert count_business_days(date(2021, 6, 1), date(2021, 6, 7)) == 5


def test_phase4av_report_contains_policies(tmp_path: Path) -> None:
    au_summary = _write_au_summary(tmp_path, readiness_status="READY_FOR_LONG_HISTORY_FETCH_PLAN")
    report_path = tmp_path / "report.md"

    audit_phase4av_long_history_fetch_plan(
        runtime_dir=tmp_path / ".runtime",
        phase4au_summary_path=au_summary,
        summary_path=tmp_path / "summary.json",
        report_path=report_path,
        current_date=date(2026, 6, 13),
    )

    report = report_path.read_text(encoding="utf-8")
    assert "60 req/min" in report
    assert "Phase4-AW Long History Fetch Dry-run" in report
    assert "does not call APIs" in report


def _write_au_summary(tmp_path: Path, *, readiness_status: str) -> Path:
    path = tmp_path / "phase4au.json"
    payload = {
        "readiness_status": readiness_status,
        "normalized_date_min": "2026-03-02",
        "normalized_date_max": "2026-05-29",
        "normalized_business_day_count": 60,
        "root_cause_confirmed": "No Phase4-AO dataset target_date satisfies the 60-business-day lookback window.",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
