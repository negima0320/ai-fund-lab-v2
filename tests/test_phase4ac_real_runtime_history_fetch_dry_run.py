from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.audit_phase4ac_real_runtime_history_fetch_dry_run import run_audit
from scripts.phase4ac_real_runtime_history_fetch_dry_run import READY, run_dry_run


def test_phase4ac_generates_request_sequence(tmp_path: Path) -> None:
    phase4ab = _write_phase4ab_summary(tmp_path)
    summary_path = tmp_path / "summary.json"
    requests_path = tmp_path / "requests.json"

    summary = run_dry_run(
        phase4ab_summary_path=phase4ab,
        summary_path=summary_path,
        requests_path=requests_path,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["planned_request_count"] == 3
    assert summary["generated_request_count"] == 3
    assert summary["target_start_date"] == "2026-03-10"
    assert summary["target_end_date"] == "2026-03-12"
    assert summary["api_call_performed"] is False
    assert summary["fetch_executed"] is False
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
    artifact = json.loads(requests_path.read_text(encoding="utf-8"))
    requests = artifact["requests"]
    assert [request["date"] for request in requests] == ["2026-03-10", "2026-03-11", "2026-03-12"]
    assert all(request["endpoint"] == "/v2/equities/bars/daily" for request in requests)
    assert all(request["method"] == "GET" for request in requests)
    assert all(request["params"]["code"] is None for request in requests)
    assert all(request["params"]["pagination_key"] is None for request in requests)
    assert all(request["no_live"] is True for request in requests)
    assert all(request["api_call_performed"] is False for request in requests)


def test_phase4ac_blocks_missing_phase4ab_summary(tmp_path: Path) -> None:
    summary = run_dry_run(
        phase4ab_summary_path=tmp_path / "missing.json",
        summary_path=tmp_path / "summary.json",
        requests_path=tmp_path / "requests.json",
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == "BLOCKED_BY_MISSING_PHASE4AB_SUMMARY"
    assert summary["api_call_performed"] is False
    assert summary["fetch_executed"] is False
    assert summary["credential_read_performed"] is False


def test_phase4ac_blocks_phase4ab_not_ready(tmp_path: Path) -> None:
    phase4ab = _write_phase4ab_summary(tmp_path, readiness_status="BLOCKED_BY_TEST")

    summary = run_dry_run(
        phase4ab_summary_path=phase4ab,
        summary_path=tmp_path / "summary.json",
        requests_path=tmp_path / "requests.json",
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == "BLOCKED_BY_PHASE4AB_NOT_READY"
    assert summary["fetch_executed"] is False


def test_phase4ac_audit_completes(tmp_path: Path) -> None:
    phase4ab = _write_phase4ab_summary(tmp_path)
    summary_path = tmp_path / "summary.json"
    requests_path = tmp_path / "requests.json"
    run_dry_run(phase4ab_summary_path=phase4ab, summary_path=summary_path, requests_path=requests_path)

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


def test_phase4ac_script_runs_without_live_work() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/phase4ac_real_runtime_history_fetch_dry_run.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "Phase4-AC no-live dry-run" in completed.stdout
    assert "api_call_performed=false" in completed.stdout
    assert "fetch_executed=false" in completed.stdout
    assert "password" not in completed.stdout
    assert "Authorization" not in completed.stdout


def test_phase4ac_audit_script_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/audit_phase4ac_real_runtime_history_fetch_dry_run.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["status"] == "complete"
    assert payload["checks"]["api_call_not_performed"]
    assert payload["checks"]["fetch_not_executed"]
    assert payload["checks"]["credential_not_read"]
    assert payload["checks"]["raw_not_written"]
    assert payload["checks"]["normalized_not_written"]


def test_phase4ac_report_documents_required_rules() -> None:
    report = Path("docs/phase_reports/phase4ac_real_runtime_history_fetch_dry_run.md").read_text(encoding="utf-8")

    assert "READY_FOR_CONTROLLED_REAL_RUNTIME_HISTORY_FETCH" in report
    assert "credential_read_performed = false" in report
    assert "http_client_initialized = false" in report
    assert "raw_data_written = false" in report
    assert "normalized_data_written = false" in report
    assert "Phase4-AD" in report


def _write_phase4ab_summary(tmp_path: Path, *, readiness_status: str = "READY_FOR_NO_LIVE_FETCH_DRY_RUN_CLI") -> Path:
    path = tmp_path / "phase4ab_summary.json"
    payload = {
        "status": "OK",
        "readiness_status": readiness_status,
        "endpoint": "/v2/equities/bars/daily",
        "target_start_date": "2026-03-10",
        "target_end_date": "2026-03-12",
        "planned_request_count": 3,
        "missing_business_day_list": ["2026-03-10", "2026-03-11", "2026-03-12"],
        "pagination_policy": "continue while next pagination key exists",
        "max_pages_policy": "max_pages=1 in dry-run",
        "rate_limit_policy": "60 req/min",
        "retry_policy": "bounded transient retry",
        "raw_output_path": ".runtime/data/raw/jquants/equities_bars_daily/",
        "isolated_normalized_output_path": ".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/",
        "mock_path_will_be_unchanged": True,
        "manifest_provenance_required": True,
        "post_fetch_raw_audit_defined": True,
        "post_normalize_coverage_audit_defined": True,
        "promotion_gate_defined": True,
        "reader_switch_gate_defined": True,
        "rollback_plan_defined": True,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
