from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase4ay_border_date_availability import (
    BLOCKED_API_FORMAT,
    READY,
    BoundaryResponse,
    audit_phase4ay_border_date_availability,
)


def test_phase4ay_confirms_20210601_available(tmp_path: Path) -> None:
    raw_dir = _prepare_reference(tmp_path)

    def requester(target_date: str, secret: str, timeout: float) -> BoundaryResponse:
        if target_date == "2021-06-01":
            return BoundaryResponse(target_date, 200, "OK", row_count=4100, payload_keys=("data",))
        return BoundaryResponse(target_date, 400, "a target date is not available", row_count=0)

    summary = audit_phase4ay_border_date_availability(
        raw_dir=raw_dir,
        calendar_jsonl=tmp_path / "missing_calendar.jsonl",
        ax2_summary_path=tmp_path / "ax2.json",
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        requester=requester,
        sleep=lambda _: None,
    )

    assert summary["readiness_status"] == READY
    assert summary["api_call_performed"] is True
    assert summary["credential_read_performed"] is False
    assert summary["first_successful_date"] == "2021-06-01"
    assert summary["first_available_trading_date"] == "2021-06-01"
    assert summary["corrected_fetch_start_date"] == "2021-06-01"
    assert summary["request_artifact_regeneration_required"] is True
    assert summary["long_history_resume_fetch_executed"] is False
    assert Path(summary["summary_path"]).is_file()
    assert Path(summary["report_path"]).is_file()


def test_phase4ay_uses_first_available_trading_date_when_0601_fails(tmp_path: Path) -> None:
    raw_dir = _prepare_reference(tmp_path)

    def requester(target_date: str, secret: str, timeout: float) -> BoundaryResponse:
        if target_date == "2021-06-14":
            return BoundaryResponse(target_date, 200, "OK", row_count=4108, payload_keys=("data",))
        return BoundaryResponse(target_date, 400, "not found for this date", row_count=0)

    summary = audit_phase4ay_border_date_availability(
        raw_dir=raw_dir,
        calendar_jsonl=tmp_path / "missing_calendar.jsonl",
        ax2_summary_path=tmp_path / "ax2.json",
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        requester=requester,
        sleep=lambda _: None,
    )

    assert summary["readiness_status"] == READY
    assert summary["first_successful_date"] == "2021-06-14"
    assert summary["corrected_fetch_start_date"] == "2021-06-14"
    assert "2021-06-14" in summary["recommended_next_action"]


def test_phase4ay_detects_api_format_diff(tmp_path: Path) -> None:
    raw_dir = tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    manifests = raw_dir / "request_manifests"
    manifests.mkdir(parents=True)
    _write_json(
        manifests / "2026-03-02.json",
        {
            "phase": "Phase4-AH",
            "endpoint": "/v2/equities/master",
            "target_date": "2026-03-02",
            "status": "SUCCESS",
            "request_params": {"date": "2026-03-02", "code": None},
            "row_count": 4444,
        },
    )

    def requester(target_date: str, secret: str, timeout: float) -> BoundaryResponse:
        return BoundaryResponse(target_date, 200, "OK", row_count=1, payload_keys=("data",))

    summary = audit_phase4ay_border_date_availability(
        raw_dir=raw_dir,
        calendar_jsonl=tmp_path / "missing_calendar.jsonl",
        ax2_summary_path=tmp_path / "ax2.json",
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        requester=requester,
        sleep=lambda _: None,
    )

    assert summary["readiness_status"] == BLOCKED_API_FORMAT
    assert summary["request_diff_summary"]["endpoint_same"] is False


def test_phase4ay_sanitizes_secret_in_response_message(tmp_path: Path) -> None:
    raw_dir = _prepare_reference(tmp_path)
    secret = "SECRET_API_KEY"

    def requester(target_date: str, passed_secret: str, timeout: float) -> BoundaryResponse:
        return BoundaryResponse(target_date, 400, f"x-api-key {secret} token password", row_count=0)

    class Settings:
        class JQuants:
            def require_api_key(self) -> str:
                return secret

            base_url = "https://example.test"

        jquants = JQuants()

    summary = audit_phase4ay_border_date_availability(
        raw_dir=raw_dir,
        calendar_jsonl=tmp_path / "missing_calendar.jsonl",
        ax2_summary_path=tmp_path / "ax2.json",
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        settings_loader=lambda: Settings(),
        requester=requester,
        sleep=lambda _: None,
    )

    text = json.dumps(summary).lower()
    assert "secret_api_key" not in text
    assert "x-api-key" not in text
    assert "token" not in text
    assert "password" not in text
    assert summary["secret_value_written"] is False


def _prepare_reference(tmp_path: Path) -> Path:
    raw_dir = tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    manifests = raw_dir / "request_manifests"
    manifests.mkdir(parents=True)
    _write_json(
        manifests / "2026-03-02.json",
        {
            "phase": "Phase4-AH",
            "endpoint": "/v2/equities/bars/daily",
            "target_date": "2026-03-02",
            "status": "SUCCESS",
            "request_params": {"date": "2026-03-02", "code": None},
            "row_count": 4439,
        },
    )
    _write_json(tmp_path / "ax2.json", {"first_successful_date_detected": "2021-06-14"})
    return raw_dir


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
