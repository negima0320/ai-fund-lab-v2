from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ai_fund_lab_v2.config.settings import AppSettings, JQuantsSettings
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.audit_phase4ax_long_history_controlled_fetch import run_audit
from scripts.phase4ax_long_history_controlled_fetch import (
    BLOCKED_AW_NOT_READY,
    BLOCKED_MISSING_AW,
    BLOCKED_MISSING_CREDENTIAL,
    PARTIAL_READY,
    READY,
    run_long_history_controlled_fetch,
)


def test_phase4ax_blocks_when_phase4aw_summary_missing(tmp_path: Path) -> None:
    summary = run_long_history_controlled_fetch(
        phase4aw_summary_path=tmp_path / "missing.json",
        phase4aw_requests_path=tmp_path / "requests.json",
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        raw_output_dir=tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily",
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == BLOCKED_MISSING_AW


def test_phase4ax_blocks_when_phase4aw_not_ready(tmp_path: Path) -> None:
    aw_summary, requests_path = _write_aw_inputs(tmp_path, readiness_status="BLOCKED")

    summary = run_long_history_controlled_fetch(
        phase4aw_summary_path=aw_summary,
        phase4aw_requests_path=requests_path,
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        raw_output_dir=tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily",
    )

    assert summary["readiness_status"] == BLOCKED_AW_NOT_READY


def test_phase4ax_blocks_when_credential_missing(tmp_path: Path) -> None:
    aw_summary, requests_path = _write_aw_inputs(tmp_path)

    summary = run_long_history_controlled_fetch(
        phase4aw_summary_path=aw_summary,
        phase4aw_requests_path=requests_path,
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        raw_output_dir=tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily",
        settings_loader=lambda: _settings(tmp_path, api_key=None),
    )

    assert summary["readiness_status"] == BLOCKED_MISSING_CREDENTIAL
    assert summary["credential_read_performed"] is True
    assert summary["secret_present"] is False


def test_phase4ax_fetches_with_mock_client_and_writes_manifests(tmp_path: Path) -> None:
    aw_summary, requests_path = _write_aw_inputs(tmp_path)
    raw_dir = tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"

    summary = run_long_history_controlled_fetch(
        phase4aw_summary_path=aw_summary,
        phase4aw_requests_path=requests_path,
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        raw_output_dir=raw_dir,
        settings_loader=lambda: _settings(tmp_path, api_key="SECRET_API_KEY"),
        client_factory=lambda settings: MockClient(),
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["planned_request_count"] == 2
    assert summary["executed_request_count"] == 2
    assert summary["succeeded_request_count"] == 2
    assert summary["completed_request_count"] == 2
    assert summary["fetched_row_count"] == 2
    assert (raw_dir / "responses" / "2021-03-09_page_001.json").is_file()
    assert (raw_dir / "request_manifests" / "2021-03-09.json").is_file()
    assert summary["normalized_data_written"] is False
    assert summary["feature_generation_executed"] is False
    assert summary["label_generation_executed"] is False
    assert summary["training_executed"] is False
    assert "SECRET_API_KEY" not in json.dumps(summary)


def test_phase4ax_resume_skips_existing_success_manifest(tmp_path: Path) -> None:
    aw_summary, requests_path = _write_aw_inputs(tmp_path)
    raw_dir = tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    manifest_dir = raw_dir / "request_manifests"
    response_dir = raw_dir / "responses"
    manifest_dir.mkdir(parents=True)
    response_dir.mkdir(parents=True)
    (manifest_dir / "2021-03-09.json").write_text(
        json.dumps({"status": "SUCCESS", "target_date": "2021-03-09"}),
        encoding="utf-8",
    )
    (response_dir / "2021-03-09_page_001.json").write_text(
        json.dumps({"payload": {"data": [{"Date": "2021-03-09", "Code": "1001"}]}}),
        encoding="utf-8",
    )

    summary = run_long_history_controlled_fetch(
        phase4aw_summary_path=aw_summary,
        phase4aw_requests_path=requests_path,
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        raw_output_dir=raw_dir,
        settings_loader=lambda: _settings(tmp_path, api_key="SECRET_API_KEY"),
        client_factory=lambda settings: MockClient(),
    )

    assert summary["skipped_request_count"] == 1
    assert summary["executed_request_count"] == 1
    assert summary["completed_request_count"] == 2
    assert summary["readiness_status"] == READY


def test_phase4ax_failed_request_is_resume_ready(tmp_path: Path) -> None:
    aw_summary, requests_path = _write_aw_inputs(tmp_path)
    raw_dir = tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"

    summary = run_long_history_controlled_fetch(
        phase4aw_summary_path=aw_summary,
        phase4aw_requests_path=requests_path,
        summary_path=tmp_path / "summary.json",
        report_path=tmp_path / "report.md",
        raw_output_dir=raw_dir,
        settings_loader=lambda: _settings(tmp_path, api_key="SECRET_API_KEY"),
        client_factory=lambda settings: FailingClient(),
    )

    assert summary["status"] == "PARTIAL"
    assert summary["readiness_status"] == PARTIAL_READY
    assert summary["failed_request_count"] >= 1
    assert summary["resume_supported"] is True
    assert "SECRET_API_KEY" not in json.dumps(summary)


def test_phase4ax_audit_completes_for_success_summary(tmp_path: Path) -> None:
    aw_summary, requests_path = _write_aw_inputs(tmp_path)
    raw_dir = tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    summary_path = tmp_path / "summary.json"
    run_long_history_controlled_fetch(
        phase4aw_summary_path=aw_summary,
        phase4aw_requests_path=requests_path,
        summary_path=summary_path,
        report_path=tmp_path / "report.md",
        raw_output_dir=raw_dir,
        settings_loader=lambda: _settings(tmp_path, api_key="SECRET_API_KEY"),
        client_factory=lambda settings: MockClient(),
    )

    result = run_audit(
        summary_path=summary_path,
        raw_output_dir=raw_dir,
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "complete"
    assert result["checks"]["normalized_not_written"] is True
    assert result["checks"]["secret_not_logged_or_written"] is True


@dataclass
class MockClient:
    def fetch_daily_quotes(self, *, date: str, pagination_key: str | None = None):
        return {"data": [{"Date": date, "Code": "1001", "Close": 100.0}], "pagination_key": None}


@dataclass
class FailingClient:
    def fetch_daily_quotes(self, *, date: str, pagination_key: str | None = None):
        raise RuntimeError("network failed for SECRET_API_KEY")


def _settings(tmp_path: Path, api_key: str | None) -> AppSettings:
    return AppSettings(
        runtime_paths=RuntimePaths(runtime_dir=tmp_path / ".runtime"),
        jquants=JQuantsSettings(api_key=api_key),
    )


def _write_aw_inputs(tmp_path: Path, *, readiness_status: str = "READY_FOR_LONG_HISTORY_CONTROLLED_FETCH") -> tuple[Path, Path]:
    summary_path = tmp_path / "phase4aw_summary.json"
    requests_path = tmp_path / "phase4aw_requests.json"
    summary_path.write_text(
        json.dumps(
            {
                "readiness_status": readiness_status,
                "target_start_date": "2021-03-09",
                "target_end_date": "2021-03-10",
                "request_count": 2,
                "rate_limit_policy": "1 request/sec and 60 req/min max",
            }
        ),
        encoding="utf-8",
    )
    requests_path.write_text(
        json.dumps(
            {
                "requests": [
                    {"params": {"date": "2021-03-09", "code": None, "pagination_key": None}},
                    {"params": {"date": "2021-03-10", "code": None, "pagination_key": None}},
                ]
            }
        ),
        encoding="utf-8",
    )
    return summary_path, requests_path
