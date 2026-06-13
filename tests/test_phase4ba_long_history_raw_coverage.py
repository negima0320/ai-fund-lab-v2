from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from scripts.audit_phase4ba_long_history_raw_coverage import (
    BLOCKED_NON_BOUNDARY,
    BLOCKED_SCHEMA,
    BLOCKED_SECRET,
    READY,
    audit_phase4ba_long_history_raw_coverage,
)


def test_phase4ba_boundary_failures_do_not_block_when_training_coverage_sufficient(tmp_path: Path) -> None:
    fixture = _prepare_fixture(tmp_path)

    summary = audit_phase4ba_long_history_raw_coverage(**fixture)

    assert summary["readiness_status"] == READY
    assert summary["failed_dates"] == ["2021-06-01"]
    assert summary["boundary_failed_dates"] == ["2021-06-01"]
    assert summary["non_boundary_failed_dates"] == []
    assert summary["boundary_failures_blocking"] is False
    assert summary["formal_training_coverage_sufficient"] is True
    assert summary["first_trainable_target_date"] is not None
    assert summary["last_label_target_date"] is not None
    assert summary["api_call_performed"] is False
    assert summary["normalized_rebuild_executed"] is False
    assert Path(summary["summary_path"]).is_file()
    assert Path(summary["report_path"]).is_file()


def test_phase4ba_non_boundary_failure_blocks(tmp_path: Path) -> None:
    fixture = _prepare_fixture(tmp_path, non_boundary_failure=True)

    summary = audit_phase4ba_long_history_raw_coverage(**fixture)

    assert summary["readiness_status"] == BLOCKED_NON_BOUNDARY
    assert summary["non_boundary_failed_dates"] == ["2021-09-01"]


def test_phase4ba_schema_error_blocks(tmp_path: Path) -> None:
    fixture = _prepare_fixture(tmp_path, schema_error=True)

    summary = audit_phase4ba_long_history_raw_coverage(**fixture)

    assert summary["readiness_status"] == BLOCKED_SCHEMA
    assert summary["raw_schema_status"] == "ERROR"


def test_phase4ba_secret_detection_blocks(tmp_path: Path) -> None:
    fixture = _prepare_fixture(tmp_path, secret_in_summary=True)

    summary = audit_phase4ba_long_history_raw_coverage(**fixture)

    assert summary["readiness_status"] == BLOCKED_SECRET
    assert summary["secret_value_detected"] is True


def test_phase4ba_detects_duplicate_date_code(tmp_path: Path) -> None:
    fixture = _prepare_fixture(tmp_path, duplicate=True)

    summary = audit_phase4ba_long_history_raw_coverage(**fixture)

    assert summary["duplicate_date_code_count"] == 1


def _prepare_fixture(
    tmp_path: Path,
    *,
    non_boundary_failure: bool = False,
    schema_error: bool = False,
    secret_in_summary: bool = False,
    duplicate: bool = False,
) -> dict:
    raw_dir = tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    manifest_dir = raw_dir / "request_manifests"
    response_dir = raw_dir / "responses"
    manifest_dir.mkdir(parents=True)
    response_dir.mkdir(parents=True)
    dates = _weekdays("2021-06-14", 95)
    request_dates = ["2021-06-01"] + dates
    if non_boundary_failure:
        request_dates.append("2021-09-01")

    for target_date in request_dates:
        status = "FAILED" if target_date == "2021-06-01" or (non_boundary_failure and target_date == "2021-09-01") else "SUCCESS"
        _write_json(
            manifest_dir / f"{target_date}.json",
            {
                "target_date": target_date,
                "status": status,
                "row_count": 0 if status == "FAILED" else 1,
                "request_params": {"date": target_date, "code": None},
                "secret_value_written": False,
            },
        )
        if status == "SUCCESS":
            row = {"Date": target_date, "Code": "1301", "C": 100.0}
            rows = [{"Date": target_date, "Code": "1301"}] if schema_error and target_date == dates[0] else [row]
            if duplicate and target_date == dates[0]:
                rows.append(dict(row))
            _write_json(response_dir / f"{target_date}_page_001.json", {"payload": {"data": rows}})

    _write_json(
        tmp_path / "az.json",
        {
            "completed_request_count": len([day for day in request_dates if day != "2021-06-01" and not (non_boundary_failure and day == "2021-09-01")]),
            "succeeded_request_count": len([day for day in request_dates if day != "2021-06-01" and not (non_boundary_failure and day == "2021-09-01")]),
            "skipped_request_count": 0,
            "failed_request_count": 1 + int(non_boundary_failure),
            "secret_value_logged": False,
            "secret_value_written": False,
            "note": "x-api-key" if secret_in_summary else "safe",
        },
    )
    _write_json(tmp_path / "ay.json", {"readiness_status": "READY_FOR_LONG_HISTORY_CONTROLLED_FETCH_RETRY"})
    _write_json(
        tmp_path / "requests.json",
        {
            "requests": [
                {"params": {"date": target_date, "code": None, "pagination_key": None}} for target_date in request_dates
            ]
        },
    )
    _write_json(
        tmp_path / "av.json",
        {
            "lookback_business_days": 5,
            "label_horizon_business_days": 5,
            "train_split_start": "2021-06-14",
            "train_split_end": "2021-08-31",
            "validation_split_start": "2021-09-01",
            "validation_split_end": "2021-09-30",
            "test_split_start": "2021-10-01",
            "test_split_end": "2021-12-31",
        },
    )
    return {
        "raw_dir": raw_dir,
        "az_summary_path": tmp_path / "az.json",
        "ay_summary_path": tmp_path / "ay.json",
        "ay_requests_path": tmp_path / "requests.json",
        "av_summary_path": tmp_path / "av.json",
        "summary_path": tmp_path / "summary.json",
        "report_path": tmp_path / "report.md",
    }


def _weekdays(start_date: str, count: int) -> list[str]:
    values: list[str] = []
    current = date.fromisoformat(start_date)
    while len(values) < count:
        if current.weekday() < 5:
            values.append(current.isoformat())
        current += timedelta(days=1)
    return values


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
