from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase4ay_long_history_request_regeneration import run_audit
from scripts.phase4ay_long_history_request_regeneration import (
    CORRECTED_FETCH_START_DATE,
    FETCH_END_DATE,
    READY,
    iter_weekdays,
    regenerate_long_history_requests,
)


def test_phase4ay_regenerates_corrected_request_artifact(tmp_path: Path) -> None:
    av_summary = _write_av_summary(tmp_path)
    summary_path = tmp_path / "summary.json"
    requests_path = tmp_path / "requests.json"

    summary = regenerate_long_history_requests(
        phase4av_summary_path=av_summary,
        summary_path=summary_path,
        requests_path=requests_path,
        report_path=tmp_path / "report.md",
    )
    artifact = json.loads(requests_path.read_text(encoding="utf-8"))

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["corrected_fetch_start_date"] == CORRECTED_FETCH_START_DATE
    assert summary["fetch_end_date"] == FETCH_END_DATE
    assert summary["first_request_date"] == "2021-06-01"
    assert summary["request_artifact_has_pre_20210601_dates"] is False
    assert artifact["request_count"] == summary["request_count"]
    assert artifact["requests"][0]["params"]["date"] == "2021-06-01"
    assert all(request["params"]["date"] >= "2021-06-01" for request in artifact["requests"])


def test_phase4ay_request_artifact_does_not_execute_api_or_downstream(tmp_path: Path) -> None:
    summary = regenerate_long_history_requests(
        phase4av_summary_path=_write_av_summary(tmp_path),
        summary_path=tmp_path / "summary.json",
        requests_path=tmp_path / "requests.json",
        report_path=tmp_path / "report.md",
    )

    assert summary["api_call_performed"] is False
    assert summary["credential_read_performed"] is False
    assert summary["http_client_initialized"] is False
    assert summary["fetch_executed"] is False
    assert summary["normalized_rebuild_executed"] is False
    assert summary["feature_generation_executed"] is False
    assert summary["label_generation_executed"] is False
    assert summary["dataset_rebuild_executed"] is False
    assert summary["training_executed"] is False
    assert summary["inference_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    assert summary["promotion_performed"] is False
    assert summary["reader_switch_performed"] is False


def test_phase4ay_quarantine_policy_and_storage_estimate(tmp_path: Path) -> None:
    summary = regenerate_long_history_requests(
        phase4av_summary_path=_write_av_summary(tmp_path),
        summary_path=tmp_path / "summary.json",
        requests_path=tmp_path / "requests.json",
        report_path=tmp_path / "report.md",
    )

    assert summary["failed_manifest_quarantine_required"] is True
    assert "2021-03-09" in summary["failed_manifest_quarantine_policy"]
    assert "2021-05-31" in summary["failed_manifest_quarantine_policy"]
    assert summary["excluded_pre_start_request_count"] == len(iter_weekdays("2021-03-09", "2021-05-31"))
    assert summary["storage_estimate_mb"] > 0
    assert summary["safe_to_resume_after_correction"] is True


def test_phase4ay_audit_completes(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    requests_path = tmp_path / "requests.json"
    regenerate_long_history_requests(
        phase4av_summary_path=_write_av_summary(tmp_path),
        summary_path=summary_path,
        requests_path=requests_path,
        report_path=tmp_path / "report.md",
    )

    result = run_audit(
        summary_path=summary_path,
        requests_path=requests_path,
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "complete"
    assert result["checks"]["corrected_fetch_start_date_ok"] is True
    assert result["checks"]["no_pre_20210601_dates"] is True
    assert result["checks"]["api_not_called"] is True
    assert result["checks"]["safe_to_resume_after_correction"] is True


def _write_av_summary(tmp_path: Path) -> Path:
    path = tmp_path / "phase4av.json"
    payload = {
        "readiness_status": "READY_FOR_LONG_HISTORY_FETCH_DRY_RUN",
        "preferred_fetch_start_date": "2021-03-09",
        "preferred_fetch_end_date": "2026-06-12",
        "estimated_request_count": 1374,
        "storage_estimate_mb": 3254.77,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
