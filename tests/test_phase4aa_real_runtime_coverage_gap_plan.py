from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.audit_phase4aa_real_runtime_coverage_gap_plan import (
    MINIMUM_REQUIRED_BUSINESS_DAYS,
    READY,
    build_coverage_gap_summary,
    run_audit,
)


def test_build_coverage_gap_summary_from_phase4z_summary(tmp_path: Path) -> None:
    isolated = tmp_path / "runtime" / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily"
    isolated.mkdir(parents=True)
    isolated_output = isolated / "data.parquet"
    isolated_output.write_bytes(b"fixture")
    phase4z_summary = tmp_path / "phase4z_summary.json"
    phase4z_summary.write_text(
        json.dumps(
            {
                "data_source_type": "real_runtime",
                "api_call_performed": False,
                "isolated_output_path": str(isolated_output),
                "row_count": 4231,
                "code_count": 4231,
                "date_min": "2026-06-01",
                "date_max": "2026-06-01",
                "business_day_count": 1,
                "per_code_row_count_min": 1,
                "per_code_row_count_max": 1,
                "per_code_row_count_mean": 1,
                "normalization_error_count": 218,
                "manifest": {
                    "data_source_type": "real_runtime",
                    "source_provider": "jquants",
                    "promotion_status": "not_promoted",
                },
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "phase4aa_summary.json"

    summary = build_coverage_gap_summary(phase4z_summary_path=phase4z_summary, summary_path=output)

    assert output.is_file()
    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["api_call_performed"] is False
    assert summary["isolated_real_runtime_detected"] is True
    assert summary["business_day_count"] == 1
    assert summary["required_business_day_count"] == MINIMUM_REQUIRED_BUSINESS_DAYS
    assert summary["missing_business_day_count"] == 59
    assert summary["coverage_sufficient_for_features"] is False
    assert summary["coverage_sufficient_for_training"] is False
    assert summary["fetch_range_start"] == "2026-03-03"
    assert summary["fetch_range_end"] == "2026-06-01"
    assert summary["mock_path_will_be_unchanged"] is True
    assert summary["promotion_gate_defined"] is True
    assert summary["rollback_plan_defined"] is True
    assert summary["label_generation_executed"] is False
    assert summary["training_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False


def test_phase4aa_audit_completes(tmp_path: Path) -> None:
    isolated = tmp_path / "runtime" / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily"
    isolated.mkdir(parents=True)
    isolated_output = isolated / "data.parquet"
    isolated_output.write_bytes(b"fixture")
    phase4z_summary = tmp_path / "phase4z_summary.json"
    phase4z_summary.write_text(
        json.dumps(
            {
                "data_source_type": "real_runtime",
                "api_call_performed": False,
                "isolated_output_path": str(isolated_output),
                "row_count": 10,
                "code_count": 10,
                "date_min": "2026-06-01",
                "date_max": "2026-06-01",
                "business_day_count": 1,
                "normalization_error_count": 0,
                "manifest": {
                    "data_source_type": "real_runtime",
                    "source_provider": "jquants",
                    "promotion_status": "not_promoted",
                },
            }
        ),
        encoding="utf-8",
    )

    result = run_audit(
        phase4z_summary_path=phase4z_summary,
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


def test_phase4aa_script_runs_without_live_work() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/audit_phase4aa_real_runtime_coverage_gap_plan.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["status"] == "complete"
    assert payload["checks"]["api_call_not_performed"]
    assert payload["checks"]["label_generation_not_implemented"]
    assert payload["checks"]["training_inference_backtest_trading_not_implemented"]


def test_phase4aa_reports_document_required_rules() -> None:
    report = Path("docs/phase_reports/phase4aa_real_runtime_coverage_gap_plan.md").read_text(encoding="utf-8")

    assert "business_day_count >= 60" in report
    assert "missing_business_day_count = 59" in report
    assert "mock normalized path must remain unchanged" in report
    assert "promotion_status = approved" in report
    assert "Phase4-AA performs no API call" in report
