from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from scripts.audit_phase4au_training_lookback_coverage import (
    BLOCKED_MISSING_DATASET,
    BLOCKED_MISSING_NORMALIZED_HISTORY,
    READY_FILTER,
    READY_LONG_HISTORY,
    audit_phase4au_training_lookback_coverage,
    build_lookback_report,
)


def test_phase4au_blocks_when_dataset_missing(tmp_path: Path) -> None:
    paths = _prepare_fixture(tmp_path, dataset_dates=[], normalized_day_count=70)
    paths["dataset_path"].unlink()

    summary = audit_phase4au_training_lookback_coverage(
        runtime_dir=tmp_path / ".runtime",
        phase4ao_summary_path=paths["ao_summary"],
        phase4an_summary_path=paths["an_summary"],
        phase4al_summary_path=paths["al_summary"],
        phase4at_summary_path=paths["at_summary"],
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == BLOCKED_MISSING_DATASET
    assert summary["training_executed"] is False


def test_phase4au_blocks_when_normalized_history_missing(tmp_path: Path) -> None:
    paths = _prepare_fixture(tmp_path, dataset_dates=_date_strings(70)[:5], normalized_day_count=0)
    paths["normalized_path"].unlink()

    summary = audit_phase4au_training_lookback_coverage(
        runtime_dir=tmp_path / ".runtime",
        phase4ao_summary_path=paths["ao_summary"],
        phase4an_summary_path=paths["an_summary"],
        phase4al_summary_path=paths["al_summary"],
        phase4at_summary_path=paths["at_summary"],
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == BLOCKED_MISSING_NORMALIZED_HISTORY
    assert summary["inference_executed"] is False


def test_phase4au_calculates_first_lookback_dates_and_rates() -> None:
    dates = _date_strings(70)
    report = build_lookback_report(dataset_dates=dates, normalized_dates=dates)

    assert report["first_target_date_with_5d_lookback"] == dates[4]
    assert report["first_target_date_with_20d_lookback"] == dates[19]
    assert report["first_target_date_with_60d_lookback"] == dates[59]
    assert report["lookback_5d_coverage_rate"] == round(66 / 70, 6)
    assert report["lookback_20d_coverage_rate"] == round(51 / 70, 6)
    assert report["lookback_60d_coverage_rate"] == round(11 / 70, 6)


def test_phase4au_detects_long_history_need_when_no_60d_target_dates(tmp_path: Path) -> None:
    dates = _date_strings(70)
    paths = _prepare_fixture(tmp_path, dataset_dates=dates[:40], normalized_day_count=60)

    summary = audit_phase4au_training_lookback_coverage(
        runtime_dir=tmp_path / ".runtime",
        phase4ao_summary_path=paths["ao_summary"],
        phase4an_summary_path=paths["an_summary"],
        phase4al_summary_path=paths["al_summary"],
        phase4at_summary_path=paths["at_summary"],
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY_LONG_HISTORY
    assert summary["target_dates_with_60d_lookback_count"] == 0
    assert summary["trainable_row_count"] == 0
    assert summary["excluded_by_lookback_row_count"] > 0
    assert summary["root_cause_confirmed"]
    assert summary["training_executed"] is False
    assert summary["inference_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False


def test_phase4au_ready_for_filter_when_60d_target_dates_exist(tmp_path: Path) -> None:
    dates = _date_strings(70)
    paths = _prepare_fixture(tmp_path, dataset_dates=dates, normalized_day_count=70)

    summary = audit_phase4au_training_lookback_coverage(
        runtime_dir=tmp_path / ".runtime",
        phase4ao_summary_path=paths["ao_summary"],
        phase4an_summary_path=paths["an_summary"],
        phase4al_summary_path=paths["al_summary"],
        phase4at_summary_path=paths["at_summary"],
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
    )

    assert summary["readiness_status"] == READY_FILTER
    assert summary["first_target_date_with_60d_lookback"] == dates[59]
    assert summary["trainable_target_date_count"] == 11
    assert summary["trainable_row_count"] == 22
    assert summary["feature_non_null_rate_by_window"]["lookback_60d"]["row_count"] == 22
    assert Path(summary["summary_path"]).is_file()
    assert Path(summary["report_path"]).is_file()


def _prepare_fixture(tmp_path: Path, *, dataset_dates: list[str], normalized_day_count: int) -> dict[str, Path]:
    dataset_path = tmp_path / "dataset.json"
    feature_path = tmp_path / "features.json"
    label_path = tmp_path / "labels.json"
    normalized_path = tmp_path / "normalized.json"
    dataset_rows = []
    feature_rows = []
    label_rows = []
    for day in dataset_dates:
        for code in ("1001", "1002"):
            dataset_rows.append(
                {
                    "target_date": day,
                    "code": code,
                    "feature__price_momentum_return_5d": 0.1 if day >= dataset_dates[-1] else None,
                    "feature__trend_close_over_ma_20d": 1.0,
                    "feature__missing_flags_insufficient_history": day < dataset_dates[-1],
                    "label__momentum_candidate_label": 1 if code == "1001" else 0,
                }
            )
            feature_rows.append(
                {
                    "target_date": day,
                    "code": code,
                    "price_momentum_return_5d": 0.1,
                    "trend_close_over_ma_20d": 1.0,
                }
            )
            label_rows.append({"target_date": day, "code": code, "momentum_candidate_label": 1})
    normalized_rows = [{"Date": day, "Code": "1001"} for day in _date_strings(normalized_day_count)]
    _write_rows(dataset_path, dataset_rows)
    _write_rows(feature_path, feature_rows)
    _write_rows(label_path, label_rows)
    _write_rows(normalized_path, normalized_rows)
    ao_summary = tmp_path / "phase4ao.json"
    an_summary = tmp_path / "phase4an.json"
    al_summary = tmp_path / "phase4al.json"
    at_summary = tmp_path / "phase4at.json"
    ao_summary.write_text(json.dumps({"dataset_output_path": str(dataset_path)}), encoding="utf-8")
    an_summary.write_text(json.dumps({"historical_feature_output_path": str(feature_path)}), encoding="utf-8")
    al_summary.write_text(
        json.dumps({"label_output_path": str(label_path), "normalized_input_path": str(normalized_path)}),
        encoding="utf-8",
    )
    at_summary.write_text(json.dumps({"readiness_status": "READY_FOR_FEATURE_EXPANSION_PLAN"}), encoding="utf-8")
    return {
        "dataset_path": dataset_path,
        "feature_path": feature_path,
        "label_path": label_path,
        "normalized_path": normalized_path,
        "ao_summary": ao_summary,
        "an_summary": an_summary,
        "al_summary": al_summary,
        "at_summary": at_summary,
    }


def _date_strings(count: int) -> list[str]:
    current = date(2026, 1, 1)
    dates: list[str] = []
    while len(dates) < count:
        if current.weekday() < 5:
            dates.append(current.isoformat())
        current += timedelta(days=1)
    return dates


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
