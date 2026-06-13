from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase4ax2_http400_root_cause import (
    CALENDAR_SOURCE_INVALID,
    FETCH_START_DATE_OUT_OF_RANGE,
    REQUEST_FORMAT_MISMATCH,
    audit_phase4ax2_http400_root_cause,
    classify_root_cause,
)


def test_phase4ax2_detects_fetch_start_date_out_of_range(tmp_path: Path) -> None:
    raw_dir = _prepare_fixture(tmp_path)

    summary = audit_phase4ax2_http400_root_cause(
        raw_dir=raw_dir,
        aw_requests_path=tmp_path / "requests.json",
        ax_summary_path=tmp_path / "ax.json",
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
    )

    assert summary["readiness_status"] == FETCH_START_DATE_OUT_OF_RANGE
    assert summary["suspected_root_cause"] == FETCH_START_DATE_OUT_OF_RANGE
    assert summary["first_failed_request"]["target_date"] == "2021-03-09"
    assert "400" in summary["failed_status_codes"]
    assert summary["successful_reference_request_from_ad_or_ah"]["phase"] == "Phase4-AH"
    assert summary["request_diff_summary"]["endpoint_same"] is True
    assert summary["request_diff_summary"]["only_date_value_differs"] is True
    assert summary["safe_to_resume"] is False
    assert summary["adjusted_fetch_start_date_if_needed"] == "2021-06-14"
    assert summary["additional_fetch_executed"] is False
    assert summary["training_executed"] is False
    assert Path(summary["summary_path"]).is_file()
    assert Path(summary["report_path"]).is_file()


def test_phase4ax2_classifies_request_format_mismatch() -> None:
    result = classify_root_cause(
        request_diff={"endpoint_same": False, "method_same": True, "param_keys_same": True},
        http400_dates=["2021-03-09"],
        first_success_date="2021-06-14",
        failed_dates=["2021-03-09"],
        aw_artifact={},
    )

    assert result == REQUEST_FORMAT_MISMATCH


def test_phase4ax2_classifies_calendar_invalid_for_weekend_failure() -> None:
    result = classify_root_cause(
        request_diff={"endpoint_same": True, "method_same": True, "param_keys_same": True},
        http400_dates=["2021-03-13"],
        first_success_date="2021-06-14",
        failed_dates=["2021-03-13"],
        aw_artifact={},
    )

    assert result == CALENDAR_SOURCE_INVALID


def test_phase4ax2_sanitizes_secret_terms(tmp_path: Path) -> None:
    raw_dir = _prepare_fixture(tmp_path, error_message="status=400 x-api-key SECRET")

    summary = audit_phase4ax2_http400_root_cause(
        raw_dir=raw_dir,
        aw_requests_path=tmp_path / "requests.json",
        ax_summary_path=tmp_path / "ax.json",
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
    )

    text = json.dumps(summary).lower()
    assert "x-api-key" not in text
    assert "authorization" not in text
    assert "password" not in text


def _prepare_fixture(tmp_path: Path, *, error_message: str = "J-Quants request failed: endpoint=/v2/equities/bars/daily status=400") -> Path:
    raw_dir = tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    manifests = raw_dir / "request_manifests"
    manifests.mkdir(parents=True)
    _write_json(
        manifests / "2021-03-09.json",
        {
            "phase": "Phase4-AX",
            "endpoint": "/v2/equities/bars/daily",
            "target_date": "2021-03-09",
            "status": "FAILED",
            "request_params": {"date": "2021-03-09", "code": None},
            "error_message": error_message,
        },
    )
    _write_json(
        manifests / "2021-06-14.json",
        {
            "phase": "Phase4-AX",
            "endpoint": "/v2/equities/bars/daily",
            "target_date": "2021-06-14",
            "status": "SUCCESS",
            "request_params": {"date": "2021-06-14", "code": None},
            "page_count": 1,
            "row_count": 4108,
        },
    )
    _write_json(
        manifests / "2026-03-02.json",
        {
            "phase": "Phase4-AH",
            "endpoint": "/v2/equities/bars/daily",
            "target_date": "2026-03-02",
            "status": "SUCCESS",
            "request_params": {"date": "2026-03-02", "code": None},
            "page_count": 1,
            "row_count": 4439,
        },
    )
    _write_json(
        tmp_path / "requests.json",
        {
            "request_count": 2,
            "requests": [
                {
                    "endpoint": "/v2/equities/bars/daily",
                    "method": "GET",
                    "params": {"date": "2021-03-09", "code": None, "pagination_key": None},
                }
            ],
        },
    )
    _write_json(tmp_path / "ax.json", {"readiness_status": "PARTIAL_FETCH_READY_FOR_RESUME"})
    return raw_dir


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
