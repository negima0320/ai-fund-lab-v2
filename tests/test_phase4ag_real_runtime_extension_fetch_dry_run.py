from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase4ag_real_runtime_extension_fetch_dry_run import run_audit
from scripts.phase4ag_real_runtime_extension_fetch_dry_run import (
    BLOCKED_EXTENSION_NOT_REQUIRED,
    BLOCKED_MISSING_AF,
    BLOCKED_AF_NOT_READY,
    READY,
    run_dry_run,
)


def test_phase4ag_generates_extension_request_sequence(tmp_path: Path) -> None:
    phase4af = _write_phase4af_summary(tmp_path)
    summary_path = tmp_path / "summary.json"
    requests_path = tmp_path / "requests.json"

    summary = run_dry_run(
        phase4af_summary_path=phase4af,
        summary_path=summary_path,
        requests_path=requests_path,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["extension_request_count"] == 3
    assert summary["generated_extension_request_count"] == 3
    assert summary["extension_fetch_start_date"] == "2026-03-02"
    assert summary["extension_fetch_end_date"] == "2026-03-04"
    assert summary["api_call_performed"] is False
    assert summary["extension_fetch_executed"] is False
    assert summary["credential_read_performed"] is False
    assert summary["http_client_initialized"] is False
    assert summary["raw_data_written"] is False
    assert summary["raw_manifest_updated"] is False
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
    assert summary["existing_raw_preserved"] is True
    assert summary["existing_success_manifest_preserved"] is True
    assert summary["merge_policy_defined"] is True

    artifact = json.loads(requests_path.read_text(encoding="utf-8"))
    requests = artifact["requests"]
    assert [request["date"] for request in requests] == ["2026-03-02", "2026-03-03", "2026-03-04"]
    assert all(request["endpoint"] == "/v2/equities/bars/daily" for request in requests)
    assert all(request["method"] == "GET" for request in requests)
    assert all(request["params"]["code"] is None for request in requests)
    assert all(request["params"]["pagination_key"] is None for request in requests)
    assert all(request["merge_mode"] == "append_new_date_or_skip_existing_success" for request in requests)
    assert all(request["existing_raw_preserved"] is True for request in requests)
    assert all(request["existing_success_manifest_preserved"] is True for request in requests)
    assert all(request["no_live"] is True for request in requests)
    assert all(request["api_call_performed"] is False for request in requests)
    assert artifact["merge_policy"]["existing_success_same_date_action"] == "skip"
    assert artifact["merge_policy"]["existing_failed_same_date_action"] == "rerun_candidate"


def test_phase4ag_blocks_missing_phase4af_summary(tmp_path: Path) -> None:
    summary = run_dry_run(
        phase4af_summary_path=tmp_path / "missing.json",
        summary_path=tmp_path / "summary.json",
        requests_path=tmp_path / "requests.json",
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == BLOCKED_MISSING_AF
    assert summary["api_call_performed"] is False
    assert summary["extension_fetch_executed"] is False
    assert summary["credential_read_performed"] is False


def test_phase4ag_blocks_phase4af_not_ready(tmp_path: Path) -> None:
    phase4af = _write_phase4af_summary(tmp_path, readiness_status="BLOCKED_BY_TEST")

    summary = run_dry_run(
        phase4af_summary_path=phase4af,
        summary_path=tmp_path / "summary.json",
        requests_path=tmp_path / "requests.json",
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == BLOCKED_AF_NOT_READY
    assert summary["extension_fetch_executed"] is False


def test_phase4ag_blocks_when_extension_not_required(tmp_path: Path) -> None:
    phase4af = _write_phase4af_summary(tmp_path, extension_fetch_required=False)

    summary = run_dry_run(
        phase4af_summary_path=phase4af,
        summary_path=tmp_path / "summary.json",
        requests_path=tmp_path / "requests.json",
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == BLOCKED_EXTENSION_NOT_REQUIRED
    assert summary["extension_fetch_required"] is False


def test_phase4ag_audit_completes(tmp_path: Path) -> None:
    phase4af = _write_phase4af_summary(tmp_path)
    summary_path = tmp_path / "summary.json"
    requests_path = tmp_path / "requests.json"
    run_dry_run(phase4af_summary_path=phase4af, summary_path=summary_path, requests_path=requests_path)

    result = run_audit(
        summary_path=summary_path,
        requests_path=requests_path,
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "complete"
    assert all(result["checks"].values())
    assert result["readiness_status"] == READY
    assert (tmp_path / "audit.json").is_file()
    assert (tmp_path / "audit.md").is_file()


def test_phase4ag_report_documents_required_rules() -> None:
    report = Path("docs/phase_reports/phase4ag_real_runtime_extension_fetch_dry_run.md").read_text(encoding="utf-8")

    assert "READY_FOR_CONTROLLED_EXTENSION_FETCH" in report
    assert "2026-03-02" in report
    assert "existing successful request manifests" in report
    assert "does not call J-Quants APIs" in report
    assert "Phase4-AH" in report


def _write_phase4af_summary(
    tmp_path: Path,
    *,
    readiness_status: str = "READY_FOR_EXTENSION_FETCH_DRY_RUN",
    extension_fetch_required: bool = True,
) -> Path:
    path = tmp_path / "phase4af_summary.json"
    payload = {
        "status": "OK",
        "readiness_status": readiness_status,
        "extension_fetch_required": extension_fetch_required,
        "extension_fetch_start_date": "2026-03-02",
        "extension_fetch_end_date": "2026-03-04",
        "extension_request_count": 3,
        "extension_requested_dates": ["2026-03-02", "2026-03-03", "2026-03-04"],
        "expected_non_empty_trading_day_count_after_extension": 60,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
