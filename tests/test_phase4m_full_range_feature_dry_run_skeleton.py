from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.candidate_ai.full_range import (
    FullRangeChunkManifest,
    build_full_range_chunk_plan,
    build_full_range_dry_run_summary,
    build_run_manifest,
    check_resume_restart,
    resolve_full_range_paths,
)
from scripts.audit_phase4m_full_range_feature_dry_run_skeleton import run_audit
from scripts.prepare_phase4k_normalized_history import prepare_mock_normalized_history


def test_chunk_plan_builder_creates_month_and_code_chunks() -> None:
    records = [
        {"Date": "2026-03-30", "Code": "11110"},
        {"Date": "2026-03-31", "Code": "22220"},
        {"Date": "2026-04-01", "Code": "11110"},
        {"Date": "2026-04-02", "Code": "22220"},
    ]

    plans = build_full_range_chunk_plan(records, run_id="run", data_source_type="mock", max_codes_per_chunk=1)

    assert len(plans) == 4
    assert {plan.date_start[:7] for plan in plans} == {"2026-03", "2026-04"}
    assert all(plan.status == "PLANNED" for plan in plans)
    assert all(plan.feature_version for plan in plans)
    assert all(plan.schema_version for plan in plans)


def test_full_range_path_resolver() -> None:
    paths = resolve_full_range_paths(runtime_dir=".runtime-test", report_dir="reports-test/candidate_ai/full_range")

    assert str(paths.feature_dir).endswith(".runtime-test/candidate_ai/features/full_range")
    assert str(paths.manifest_dir).endswith(".runtime-test/candidate_ai/manifests/full_range")
    assert str(paths.audit_dir).endswith(".runtime-test/candidate_ai/audit/full_range")
    assert str(paths.tmp_dir).endswith(".runtime-test/candidate_ai/tmp/full_range")
    assert str(paths.report_dir).endswith("reports-test/candidate_ai/full_range")


def test_run_and_chunk_manifest_models() -> None:
    records = [{"Date": "2026-03-30", "Code": "11110"}]
    plans = build_full_range_chunk_plan(records, run_id="run", data_source_type="mock")
    manifest = build_run_manifest(run_id="run", records=records, chunk_plans=plans, data_source_type="mock")
    chunk_manifest = FullRangeChunkManifest(
        run_id="run",
        chunk_id=plans[0].chunk_id,
        status="SUCCESS",
        date_start=plans[0].date_start,
        date_end=plans[0].date_end,
        code_count=1,
        row_count=1,
        eligible_count=0,
        excluded_count=1,
        schema_validation_status="OK",
        leakage_audit_status="OK",
        output_path=None,
        manifest_path=None,
        audit_path=None,
        error_message=None,
    )

    assert manifest.run_id == "run"
    assert manifest.chunk_count == 1
    assert chunk_manifest.to_dict()["status"] == "SUCCESS"


def test_resume_restart_checker_detects_completed_failed_missing_and_partial(tmp_path: Path) -> None:
    records = [
        {"Date": "2026-03-30", "Code": "11110"},
        {"Date": "2026-04-01", "Code": "11110"},
    ]
    plans = build_full_range_chunk_plan(records, run_id="run", data_source_type="mock")
    manifest_dir = tmp_path / "manifests"
    tmp_dir = tmp_path / "tmp"
    manifest_dir.mkdir()
    tmp_dir.mkdir()
    completed = plans[0]
    (manifest_dir / f"{completed.chunk_id}_chunk_manifest.json").write_text(
        json.dumps({"chunk_id": completed.chunk_id, "status": "SUCCESS"}) + "\n",
        encoding="utf-8",
    )
    (tmp_dir / "partial.tmp").write_text("partial", encoding="utf-8")

    summary = check_resume_restart(plans, manifest_dir=manifest_dir, tmp_dir=tmp_dir)

    assert completed.chunk_id in summary.completed_chunk_ids
    assert len(summary.missing_chunk_ids) == len(plans) - 1
    assert summary.partial_tmp_paths


def test_dry_run_cli_generates_plan_manifest_and_summary(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    report_dir = tmp_path / "reports"
    prepare_mock_normalized_history(runtime_dir=runtime_dir, business_days=65, code_count=3, output_format="jsonl", report_dir=tmp_path / "prep")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_candidate_features_full_range_dry_run.py",
            "--runtime-dir",
            str(runtime_dir),
            "--report-dir",
            str(report_dir),
            "--input-format",
            "jsonl",
            "--max-codes-per-chunk",
            "2",
            "--run-id",
            "test_run",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "OK"
    assert payload["feature_generation_executed"] is False
    assert payload["chunk_count"] > 0
    assert Path(payload["summary_path"]).is_file()
    assert Path(payload["run_manifest_path"]).is_file()
    assert Path(payload["chunk_plan_path"]).is_file()


def test_dry_run_safe_skipped_when_no_normalized_data(tmp_path: Path) -> None:
    summary = build_full_range_dry_run_summary(runtime_dir=tmp_path / "missing-runtime", report_dir=tmp_path / "reports", run_id="skip")

    assert summary["status"] == "SKIPPED"
    assert summary["feature_generation_executed"] is False
    assert summary["chunk_count"] == 0
    assert Path(summary["summary_path"]).is_file()


def test_phase4m_audit_completes_and_writes_reports(tmp_path: Path) -> None:
    result = run_audit(
        json_report_path=tmp_path / "phase4m.json",
        markdown_report_path=tmp_path / "phase4m.md",
    )

    assert result["status"] == "complete"
    assert result["checks"]["chunk_plan_builder_exists"]
    assert result["checks"]["dry_run_cli_does_not_generate_features"]
    assert (tmp_path / "phase4m.json").is_file()
    assert (tmp_path / "phase4m.md").is_file()


def test_phase4m_does_not_add_generation_training_or_trading_code() -> None:
    source = "\n".join(
        [
            Path("src/ai_fund_lab_v2/candidate_ai/full_range.py").read_text(encoding="utf-8"),
            Path("scripts/build_candidate_features_full_range_dry_run.py").read_text(encoding="utf-8"),
            Path("scripts/audit_phase4m_full_range_feature_dry_run_skeleton.py").read_text(encoding="utf-8"),
        ]
    )

    for forbidden in ("def train", "def predict", "def backtest", "def generate_labels", "submit_order", "place_order"):
        assert forbidden not in source
