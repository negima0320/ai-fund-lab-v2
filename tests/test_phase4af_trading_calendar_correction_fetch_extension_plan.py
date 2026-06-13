from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from scripts.audit_phase4af_trading_calendar_correction_fetch_extension_plan import (
    BLOCKED_MISSING_AE,
    BLOCKED_UNEXPECTED_EMPTY,
    READY_EXTENSION,
    READY_NORMALIZE,
    build_extension_plan_summary,
    run_audit,
)


def test_phase4af_blocks_missing_phase4ae_summary(tmp_path: Path) -> None:
    summary = build_extension_plan_summary(
        phase4ae_summary_path=tmp_path / "missing.json",
        raw_root=tmp_path / "runtime" / "data" / "raw" / "jquants" / "equities_bars_daily",
        trading_calendar_base_path=tmp_path / "runtime" / "data" / "raw" / "jquants" / "trading_calendar" / "data",
        summary_path=tmp_path / "summary.json",
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == BLOCKED_MISSING_AE
    assert summary["api_call_performed"] is False
    assert summary["normalized_data_written"] is False


def test_phase4af_classifies_holiday_empty_as_expected_market_closed(tmp_path: Path) -> None:
    phase4ae, raw_root, calendar_base = _prepare_fixture(
        tmp_path,
        fetched_dates=["2026-03-10", "2026-03-11"],
        empty_dates=["2026-03-20"],
        requested_dates=["2026-03-10", "2026-03-11", "2026-03-20"],
        calendar_dates=["2026-03-09", "2026-03-10", "2026-03-11", "2026-03-20"],
    )

    summary = build_extension_plan_summary(
        phase4ae_summary_path=phase4ae,
        raw_root=raw_root,
        trading_calendar_base_path=calendar_base,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["readiness_status"] == READY_EXTENSION
    assert summary["expected_empty_market_closed_dates"] == ["2026-03-20"]
    assert summary["unexpected_empty_trading_dates"] == []
    assert summary["coverage_sufficient_after_calendar_correction"] is False
    assert summary["extension_fetch_required"] is True


def test_phase4af_blocks_unexpected_empty_trading_date(tmp_path: Path) -> None:
    phase4ae, raw_root, calendar_base = _prepare_fixture(
        tmp_path,
        fetched_dates=["2026-03-10", "2026-03-11"],
        empty_dates=["2026-03-12"],
        requested_dates=["2026-03-10", "2026-03-11", "2026-03-12"],
        calendar_dates=["2026-03-09", "2026-03-10", "2026-03-11", "2026-03-12"],
    )

    summary = build_extension_plan_summary(
        phase4ae_summary_path=phase4ae,
        raw_root=raw_root,
        trading_calendar_base_path=calendar_base,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["readiness_status"] == BLOCKED_UNEXPECTED_EMPTY
    assert summary["unexpected_empty_trading_dates"] == ["2026-03-12"]
    assert summary["extension_fetch_required"] is False


def test_phase4af_plans_past_extension_dates(tmp_path: Path) -> None:
    phase4ae, raw_root, calendar_base = _prepare_fixture(
        tmp_path,
        fetched_dates=["2026-03-10", "2026-03-11", "2026-03-12"],
        empty_dates=[],
        requested_dates=["2026-03-10", "2026-03-11", "2026-03-12"],
        calendar_dates=[
            "2026-03-02",
            "2026-03-03",
            "2026-03-04",
            "2026-03-05",
            "2026-03-06",
            "2026-03-09",
            "2026-03-10",
            "2026-03-11",
            "2026-03-12",
        ],
    )

    summary = build_extension_plan_summary(
        phase4ae_summary_path=phase4ae,
        raw_root=raw_root,
        trading_calendar_base_path=calendar_base,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["readiness_status"] == READY_EXTENSION
    assert summary["fetched_non_empty_trading_day_count"] == 3
    assert summary["true_missing_non_empty_trading_day_count"] == 57
    assert summary["extension_fetch_start_date"] < "2026-03-10"
    assert summary["extension_request_count"] == 57
    assert summary["extension_requested_dates"][-1] == "2026-03-09"
    assert summary["expected_non_empty_trading_day_count_after_extension"] == 60


def test_phase4af_ready_when_calendar_corrected_coverage_is_sufficient(tmp_path: Path) -> None:
    fetched_dates = _weekday_dates("2030-03-04", 60)
    phase4ae, raw_root, calendar_base = _prepare_fixture(
        tmp_path,
        fetched_dates=fetched_dates,
        empty_dates=[],
        requested_dates=fetched_dates,
        calendar_dates=fetched_dates,
    )

    summary = build_extension_plan_summary(
        phase4ae_summary_path=phase4ae,
        raw_root=raw_root,
        trading_calendar_base_path=calendar_base,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["readiness_status"] == READY_NORMALIZE
    assert summary["extension_fetch_required"] is False
    assert summary["coverage_sufficient_after_calendar_correction"] is True


def test_phase4af_classifies_june_1_not_requested(tmp_path: Path) -> None:
    phase4ae, raw_root, calendar_base = _prepare_fixture(
        tmp_path,
        fetched_dates=["2026-05-29"],
        empty_dates=[],
        requested_dates=["2026-05-29"],
        calendar_dates=["2026-05-29", "2026-06-01"],
        required_dates=["2026-05-29", "2026-06-01"],
    )

    summary = build_extension_plan_summary(
        phase4ae_summary_path=phase4ae,
        raw_root=raw_root,
        trading_calendar_base_path=calendar_base,
        summary_path=tmp_path / "summary.json",
    )

    june_1 = summary["june_1_classification"]
    assert june_1["requested"] is False
    assert june_1["response_file_exists"] is False
    assert june_1["market_open"] is True
    assert june_1["classification"] == "missing_requested_trading_date"
    assert "do not use it as latest raw coverage" in june_1["note"]


def test_phase4af_no_live_safety_flags(tmp_path: Path) -> None:
    phase4ae, raw_root, calendar_base = _prepare_fixture(
        tmp_path,
        fetched_dates=["2026-03-10"],
        empty_dates=["2026-03-20"],
        requested_dates=["2026-03-10", "2026-03-20"],
        calendar_dates=["2026-03-09", "2026-03-10", "2026-03-20"],
    )

    summary = build_extension_plan_summary(
        phase4ae_summary_path=phase4ae,
        raw_root=raw_root,
        trading_calendar_base_path=calendar_base,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["api_call_performed"] is False
    assert summary["additional_fetch_executed"] is False
    assert summary["credential_read_performed"] is False
    assert summary["http_client_initialized"] is False
    assert summary["raw_data_written"] is False
    assert summary["normalized_data_written"] is False
    assert summary["promotion_performed"] is False
    assert summary["reader_switch_performed"] is False
    assert summary["feature_generation_executed"] is False
    assert summary["label_generation_executed"] is False
    assert summary["training_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    assert summary["mock_path_written"] is False
    assert summary["isolated_normalized_path_written"] is False


def test_phase4af_audit_completes(tmp_path: Path) -> None:
    phase4ae, raw_root, calendar_base = _prepare_fixture(
        tmp_path,
        fetched_dates=["2026-03-10"],
        empty_dates=["2026-03-20"],
        requested_dates=["2026-03-10", "2026-03-20"],
        calendar_dates=["2026-03-09", "2026-03-10", "2026-03-20"],
    )

    result = run_audit(
        phase4ae_summary_path=phase4ae,
        raw_root=raw_root,
        trading_calendar_base_path=calendar_base,
        summary_path=tmp_path / "summary.json",
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "complete"
    assert result["readiness_status"] == READY_EXTENSION
    assert (tmp_path / "audit.json").is_file()
    assert (tmp_path / "audit.md").is_file()


def test_phase4af_report_documents_required_rules() -> None:
    report = Path("docs/phase_reports/phase4af_trading_calendar_correction_fetch_extension_plan.md").read_text(
        encoding="utf-8"
    )

    assert "READY_FOR_EXTENSION_FETCH_DRY_RUN" in report
    assert "does not call J-Quants APIs" in report
    assert "2026-06-01" in report
    assert "Phase4-AG" in report


def _prepare_fixture(
    tmp_path: Path,
    *,
    fetched_dates: list[str],
    empty_dates: list[str],
    requested_dates: list[str],
    calendar_dates: list[str],
    required_dates: list[str] | None = None,
) -> tuple[Path, Path, Path]:
    raw_root = tmp_path / "runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    request_dir = raw_root / "request_manifests"
    response_dir = raw_root / "responses"
    request_dir.mkdir(parents=True)
    response_dir.mkdir(parents=True)
    for target_date in requested_dates:
        (request_dir / f"{target_date}.json").write_text(
            json.dumps({"target_date": target_date, "status": "SUCCESS"}),
            encoding="utf-8",
        )
    for target_date in fetched_dates:
        (response_dir / f"{target_date}_page_001.json").write_text(
            json.dumps({"date": target_date, "payload": {"data": [{"Date": target_date, "Code": "7203"}]}}),
            encoding="utf-8",
        )
    for target_date in empty_dates:
        (response_dir / f"{target_date}_page_001.json").write_text(
            json.dumps({"date": target_date, "payload": {"data": []}}),
            encoding="utf-8",
        )
    phase4ae = tmp_path / "phase4ae.json"
    phase4ae.write_text(
        json.dumps(
            {
                "readiness_status": "BLOCKED_BY_COVERAGE_GAP",
                "empty_response_dates": empty_dates,
                "fetched_dates": fetched_dates,
                "required_business_dates": required_dates or fetched_dates + empty_dates,
                "fetched_business_day_count": len(fetched_dates),
                "fetched_date_min": fetched_dates[0] if fetched_dates else None,
                "fetched_date_max": fetched_dates[-1] if fetched_dates else None,
            }
        ),
        encoding="utf-8",
    )
    calendar_base = tmp_path / "runtime" / "data" / "raw" / "jquants" / "trading_calendar" / "data"
    calendar_base.parent.mkdir(parents=True)
    with calendar_base.with_suffix(".jsonl").open("w", encoding="utf-8") as handle:
        for target_date in calendar_dates:
            handle.write(json.dumps({"Date": target_date, "HolDiv": "1"}) + "\n")
    return phase4ae, raw_root, calendar_base


def _weekday_dates(start_date: str, count: int) -> list[str]:
    current = date.fromisoformat(start_date)
    values: list[str] = []
    while len(values) < count:
        if current.weekday() < 5:
            values.append(current.isoformat())
        current += timedelta(days=1)
    return values
