from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.config.settings import AppSettings, JQuantsSettings
from ai_fund_lab_v2.runtime.paths import RuntimePaths
from scripts.audit_phase4az_long_history_controlled_fetch_retry import run_audit
from scripts.phase4az_long_history_controlled_fetch_retry import (
    BLOCKED_MISSING_CREDENTIAL,
    BLOCKED_MISSING_REQUESTS,
    BLOCKED_MISSING_AY,
    BLOCKED_PRE_START,
    BLOCKED_AY_NOT_READY,
    PARTIAL_READY,
    READY,
    run_long_history_controlled_fetch_retry,
)


def test_phase4az_blocks_missing_phase4ay_summary(tmp_path: Path) -> None:
    summary = run_long_history_controlled_fetch_retry(
        phase4ay_summary_path=tmp_path / "missing.json",
        phase4ay_requests_path=tmp_path / "requests.json",
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        raw_output_dir=tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily",
    )

    assert summary["readiness_status"] == BLOCKED_MISSING_AY
    assert summary["api_call_performed"] is False


def test_phase4az_blocks_not_ready_phase4ay_summary(tmp_path: Path) -> None:
    ay_summary = _write_json(tmp_path / "ay.json", {"readiness_status": "BLOCKED"})
    requests = _write_requests(tmp_path, ["2021-06-01"])

    summary = run_long_history_controlled_fetch_retry(
        phase4ay_summary_path=ay_summary,
        phase4ay_requests_path=requests,
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        raw_output_dir=tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily",
    )

    assert summary["readiness_status"] == BLOCKED_AY_NOT_READY


def test_phase4az_blocks_missing_corrected_requests(tmp_path: Path) -> None:
    ay_summary = _write_ay_summary(tmp_path)

    summary = run_long_history_controlled_fetch_retry(
        phase4ay_summary_path=ay_summary,
        phase4ay_requests_path=tmp_path / "missing_requests.json",
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        raw_output_dir=tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily",
    )

    assert summary["readiness_status"] == BLOCKED_MISSING_REQUESTS


def test_phase4az_blocks_pre_start_request(tmp_path: Path) -> None:
    ay_summary = _write_ay_summary(tmp_path)
    requests = _write_requests(tmp_path, ["2021-05-31", "2021-06-01"])

    summary = run_long_history_controlled_fetch_retry(
        phase4ay_summary_path=ay_summary,
        phase4ay_requests_path=requests,
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        raw_output_dir=tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily",
    )

    assert summary["readiness_status"] == BLOCKED_PRE_START
    assert summary["pre_start_request_executed"] is False


def test_phase4az_blocks_missing_credential(tmp_path: Path) -> None:
    ay_summary = _write_ay_summary(tmp_path)
    requests = _write_requests(tmp_path, ["2021-06-01"])

    summary = run_long_history_controlled_fetch_retry(
        phase4ay_summary_path=ay_summary,
        phase4ay_requests_path=requests,
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        raw_output_dir=tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily",
        settings_loader=lambda: _settings(tmp_path, api_key=None),
    )

    assert summary["readiness_status"] == BLOCKED_MISSING_CREDENTIAL
    assert summary["credential_read_performed"] is True
    assert summary["api_call_performed"] is False


def test_phase4az_fetches_with_mock_client_and_skips_success(tmp_path: Path) -> None:
    ay_summary = _write_ay_summary(tmp_path)
    requests = _write_requests(tmp_path, ["2021-06-01", "2021-06-02"])
    raw_output = tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    manifest_dir = raw_output / "request_manifests"
    response_dir = raw_output / "responses"
    manifest_dir.mkdir(parents=True)
    response_dir.mkdir(parents=True)
    _write_json(
        manifest_dir / "2021-06-01.json",
        {"phase": "Phase4-AZ", "target_date": "2021-06-01", "status": "SUCCESS", "row_count": 1},
    )
    _write_json(
        response_dir / "2021-06-01_page_001.json",
        {"payload": {"data": [{"Date": "2021-06-01", "Code": "1301"}]}},
    )

    summary = run_long_history_controlled_fetch_retry(
        phase4ay_summary_path=ay_summary,
        phase4ay_requests_path=requests,
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        raw_output_dir=raw_output,
        settings_loader=lambda: _settings(tmp_path),
        client_factory=lambda settings: FakeClient({"2021-06-02": [{"Date": "2021-06-02", "Code": "1302"}]}),
    )

    assert summary["readiness_status"] == READY
    assert summary["executed_request_count"] == 1
    assert summary["succeeded_request_count"] == 1
    assert summary["skipped_request_count"] == 1
    assert summary["completed_request_count"] == 2
    assert summary["pre_start_request_executed"] is False
    assert summary["normalized_data_written"] is False
    assert summary["feature_generation_executed"] is False
    assert (raw_output / "request_manifests" / "2021-06-02.json").is_file()
    assert (raw_output / "responses" / "2021-06-02_page_001.json").is_file()


def test_phase4az_failed_request_is_resume_ready_and_secret_sanitized(tmp_path: Path) -> None:
    ay_summary = _write_ay_summary(tmp_path)
    requests = _write_requests(tmp_path, ["2021-06-01"])
    raw_output = tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"

    summary = run_long_history_controlled_fetch_retry(
        phase4ay_summary_path=ay_summary,
        phase4ay_requests_path=requests,
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        raw_output_dir=raw_output,
        settings_loader=lambda: _settings(tmp_path, api_key="SECRET_KEY"),
        client_factory=lambda settings: FailingClient("bad x-api-key SECRET_KEY token"),
        max_consecutive_failures=1,
    )

    manifest_text = (raw_output / "request_manifests" / "2021-06-01.json").read_text(encoding="utf-8")
    summary_text = json.dumps(summary)
    assert summary["readiness_status"] == PARTIAL_READY
    assert summary["failed_request_count"] == 1
    assert summary["resume_supported"] is True
    assert "SECRET_KEY" not in manifest_text
    assert "SECRET_KEY" not in summary_text
    assert "x-api-key" not in manifest_text


def test_phase4az_counts_pre_start_failed_manifests_as_quarantined(tmp_path: Path) -> None:
    ay_summary = _write_ay_summary(tmp_path)
    requests = _write_requests(tmp_path, ["2021-06-01"])
    raw_output = tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    manifest_dir = raw_output / "request_manifests"
    manifest_dir.mkdir(parents=True)
    _write_json(manifest_dir / "2021-05-31.json", {"status": "FAILED"})

    summary = run_long_history_controlled_fetch_retry(
        phase4ay_summary_path=ay_summary,
        phase4ay_requests_path=requests,
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        raw_output_dir=raw_output,
        settings_loader=lambda: _settings(tmp_path),
        client_factory=lambda settings: FakeClient({"2021-06-01": [{"Date": "2021-06-01", "Code": "1301"}]}),
    )

    assert summary["quarantined_failed_manifest_count"] == 1
    assert summary["pre_start_request_executed"] is False


def test_phase4az_audit_completes(tmp_path: Path) -> None:
    ay_summary = _write_ay_summary(tmp_path)
    requests = _write_requests(tmp_path, ["2021-06-01"])
    raw_output = tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    summary_path = tmp_path / "summary.json"
    run_long_history_controlled_fetch_retry(
        phase4ay_summary_path=ay_summary,
        phase4ay_requests_path=requests,
        summary_path=summary_path,
        report_path=tmp_path / "report.md",
        raw_output_dir=raw_output,
        settings_loader=lambda: _settings(tmp_path),
        client_factory=lambda settings: FakeClient({"2021-06-01": [{"Date": "2021-06-01", "Code": "1301"}]}),
    )

    result = run_audit(
        summary_path=summary_path,
        raw_manifest_path=raw_output / "manifest.json",
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "complete"
    assert result["checks"]["pre_start_request_not_executed"] is True
    assert result["checks"]["normalized_not_written"] is True
    assert result["checks"]["secret_value_not_written"] is True


class FakeClient:
    def __init__(self, rows_by_date: dict[str, list[dict]]) -> None:
        self.rows_by_date = rows_by_date

    def fetch_daily_quotes(self, *, date: str, pagination_key=None):
        return {"data": self.rows_by_date.get(date, [])}


class FailingClient:
    def __init__(self, message: str) -> None:
        self.message = message

    def fetch_daily_quotes(self, *, date: str, pagination_key=None):
        raise RuntimeError(self.message)


def _settings(tmp_path: Path, api_key: str | None = "test-key") -> AppSettings:
    return AppSettings(
        runtime_paths=RuntimePaths(runtime_dir=tmp_path / ".runtime"),
        jquants=JQuantsSettings(api_key=api_key),
    )


def _write_ay_summary(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "ay_summary.json",
        {
            "readiness_status": "READY_FOR_LONG_HISTORY_CONTROLLED_FETCH_RETRY",
            "corrected_fetch_start_date": "2021-06-01",
            "fetch_end_date": "2026-06-12",
            "request_count": 1,
        },
    )


def _write_requests(tmp_path: Path, dates: list[str]) -> Path:
    requests = [
        {
            "request_id": f"test_{target_date}",
            "sequence": index + 1,
            "endpoint": "/v2/equities/bars/daily",
            "method": "GET",
            "params": {"date": target_date, "code": None, "pagination_key": None},
        }
        for index, target_date in enumerate(dates)
    ]
    return _write_json(tmp_path / "requests.json", {"request_count": len(requests), "requests": requests})


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
