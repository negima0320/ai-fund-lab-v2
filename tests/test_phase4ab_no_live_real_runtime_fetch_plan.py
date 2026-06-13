from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from scripts.audit_phase4ab_no_live_real_runtime_fetch_plan import (
    READY,
    build_no_live_fetch_plan_summary,
    run_audit,
)


def test_build_no_live_fetch_plan_summary(tmp_path: Path) -> None:
    runtime_dir, phase4aa_summary = _prepare_runtime_and_phase4aa(tmp_path)
    output = tmp_path / "phase4ab_summary.json"

    summary = build_no_live_fetch_plan_summary(
        runtime_dir=runtime_dir,
        phase4aa_summary_path=phase4aa_summary,
        summary_path=output,
    )

    assert output.is_file()
    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["api_call_performed"] is False
    assert summary["fetch_executed"] is False
    assert summary["promotion_performed"] is False
    assert summary["reader_switch_performed"] is False
    assert summary["feature_generation_executed"] is False
    assert summary["target_start_date"] == "2026-03-10"
    assert summary["target_end_date"] == "2026-06-01"
    assert len(summary["target_business_day_list"]) == 60
    assert len(summary["missing_business_day_list"]) == 59
    assert summary["planned_request_count"] == 59
    assert summary["endpoint"] == "/v2/equities/bars/daily"
    assert summary["raw_output_path"] == ".runtime/data/raw/jquants/equities_bars_daily/"
    assert (
        summary["isolated_normalized_output_path"]
        == ".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/"
    )
    assert summary["mock_path_will_be_unchanged"] is True
    assert summary["promotion_gate_defined"] is True
    assert summary["reader_switch_gate_defined"] is True
    assert summary["rollback_plan_defined"] is True


def test_phase4ab_audit_completes(tmp_path: Path) -> None:
    runtime_dir, phase4aa_summary = _prepare_runtime_and_phase4aa(tmp_path)

    result = run_audit(
        runtime_dir=runtime_dir,
        phase4aa_summary_path=phase4aa_summary,
        summary_path=tmp_path / "summary.json",
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "complete"
    assert all(result["checks"].values())
    assert result["readiness_status"] == READY
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "audit.json").is_file()
    assert (tmp_path / "audit.md").is_file()


def test_phase4ab_blocks_missing_phase4aa_summary(tmp_path: Path) -> None:
    summary = build_no_live_fetch_plan_summary(
        runtime_dir=tmp_path / "runtime",
        phase4aa_summary_path=tmp_path / "missing.json",
        summary_path=tmp_path / "summary.json",
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == "BLOCKED_BY_MISSING_PHASE4AA_SUMMARY"
    assert summary["api_call_performed"] is False
    assert summary["fetch_executed"] is False


def test_phase4ab_script_runs_without_live_work() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/audit_phase4ab_no_live_real_runtime_fetch_plan.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["status"] == "complete"
    assert payload["checks"]["api_call_not_performed"]
    assert payload["checks"]["fetch_not_executed"]
    assert payload["checks"]["promotion_not_performed"]
    assert payload["checks"]["reader_switch_not_performed"]
    assert payload["checks"]["feature_generation_not_executed"]


def test_phase4ab_report_documents_required_rules() -> None:
    report = Path("docs/phase_reports/phase4ab_no_live_real_runtime_fetch_plan.md").read_text(encoding="utf-8")

    assert "Phase4-AB does not read, validate, print, or log API credentials" in report
    assert ".runtime/data/raw/jquants/equities_bars_daily/" in report
    assert ".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/" in report
    assert ".runtime/data/raw_normalized/jquants/equities_bars_daily/" in report
    assert "READY_FOR_NO_LIVE_FETCH_DRY_RUN_CLI" in report
    assert "Phase4-AC" in report


def _prepare_runtime_and_phase4aa(tmp_path: Path) -> tuple[Path, Path]:
    runtime_dir = tmp_path / "runtime"
    isolated = runtime_dir / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily"
    isolated.mkdir(parents=True)
    isolated_output = isolated / "data.parquet"
    isolated_output.write_bytes(b"fixture")
    _write_calendar(runtime_dir)
    phase4aa_summary = tmp_path / "phase4aa_summary.json"
    phase4aa_summary.write_text(
        json.dumps(
            {
                "status": "OK",
                "readiness_status": "READY_FOR_REAL_RUNTIME_HISTORY_FETCH_PLAN",
                "api_call_performed": False,
                "isolated_real_runtime_detected": True,
                "isolated_path": str(isolated_output),
                "row_count": 4231,
                "code_count": 4231,
                "date_min": "2026-06-01",
                "date_max": "2026-06-01",
                "business_day_count": 1,
                "required_business_day_count": 60,
                "missing_business_day_count": 59,
                "fetch_range_start": "2026-03-03",
                "fetch_range_end": "2026-06-01",
                "mock_path_will_be_unchanged": True,
            }
        ),
        encoding="utf-8",
    )
    return runtime_dir, phase4aa_summary


def _write_calendar(runtime_dir: Path) -> None:
    path = runtime_dir / "data" / "raw" / "jquants" / "trading_calendar" / "data.jsonl"
    path.parent.mkdir(parents=True)
    current = date.fromisoformat("2026-03-02")
    end = date.fromisoformat("2026-06-01")
    with path.open("w", encoding="utf-8") as handle:
        while current <= end:
            if current.weekday() < 5:
                handle.write(json.dumps({"Date": current.isoformat(), "HolDiv": "1"}) + "\n")
            current += timedelta(days=1)
