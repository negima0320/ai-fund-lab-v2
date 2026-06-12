#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai import (  # noqa: E402
    FullRangeChunkManifest,
    build_full_range_chunk_plan,
    build_full_range_resume_controlled_summary,
    resolve_full_range_paths,
)
from ai_fund_lab_v2.candidate_ai.normalized_data_reader import discover_daily_quotes_normalized  # noqa: E402
from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402
from scripts.prepare_phase4k_normalized_history import prepare_mock_normalized_history  # noqa: E402


JSON_REPORT_PATH = Path("reports/phase_reports/phase4q_resume_aware_controlled_runner_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4q_resume_aware_controlled_runner_audit.md")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4q_resume_aware_controlled_summary.json")


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="phase4q_resume_runner_") as temp_dir:
        root = Path(temp_dir)
        resume_summary = _run_resume_fixture(root / "resume")
        blocked_summary = _run_inconsistency_fixture(root / "blocked")
    _write_json(SUMMARY_PATH, resume_summary)
    checks = {
        "resume_aware_runner_exists": _source_contains("build_full_range_resume_controlled_summary"),
        "success_chunk_skip_confirmed": resume_summary.get("skipped_success_chunk_count") == 1,
        "failed_chunk_rerun_confirmed": resume_summary.get("rerun_failed_chunk_count", 0) >= 1,
        "missing_chunk_run_confirmed": resume_summary.get("run_missing_chunk_count", 0) >= 1,
        "partial_tmp_warning_confirmed": resume_summary.get("partial_tmp_warning_count", 0) >= 1,
        "inconsistency_block_confirmed": blocked_summary.get("status") == "BLOCKED"
        and blocked_summary.get("blocked_inconsistency_count", 0) >= 1,
        "max_chunks_to_execute_limit_confirmed": resume_summary.get("max_chunks_to_execute") == 2
        and resume_summary.get("executed_chunk_count") == 2,
        "tmp_to_final_atomic_move_maintained": resume_summary.get("tmp_to_final_atomic_move") is True,
        "schema_validation_ok": resume_summary.get("schema_validation_status") == "OK",
        "leakage_audit_ok": resume_summary.get("leakage_audit_status") == "OK",
        "summary_json_exists": SUMMARY_PATH.is_file(),
        "full_range_generation_not_expanded": resume_summary.get("executed_chunk_count", 0) <= 2,
        "label_generation_not_implemented": resume_summary.get("label_generation_executed") is False,
        "training_inference_backtest_trading_not_implemented": resume_summary.get("training_executed") is False
        and resume_summary.get("inference_executed") is False
        and resume_summary.get("backtest_executed") is False
        and resume_summary.get("trading_executed") is False,
        "no_secret_terms_in_reports": _no_secret_terms(resume_summary) and _no_secret_terms(blocked_summary),
    }
    result = {
        "phase": "Phase4-Q",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "resume_summary": _compact_summary(resume_summary),
        "blocked_summary": _compact_summary(blocked_summary),
        "summary_path": str(SUMMARY_PATH),
        "pytest_hint": "python3 -m pytest tests/test_phase4q_resume_aware_controlled_runner.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _run_resume_fixture(root: Path) -> dict[str, Any]:
    runtime_dir = root / "runtime"
    report_dir = root / "reports"
    run_id = "phase4q_resume_fixture"
    plans, paths = _prepare_plans(runtime_dir, report_dir, run_id)
    output_path = paths.feature_dir / run_id / "already_done.json"
    audit_path = paths.audit_dir / f"{run_id}_already_done_audit.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text('{"rows":[]}\n', encoding="utf-8")
    audit_path.write_text('{"status":"OK"}\n', encoding="utf-8")
    _write_manifest(paths.manifest_dir / f"{run_id}_success_manifest.json", plans[0], "SUCCESS", output_path, audit_path)
    _write_manifest(paths.manifest_dir / f"{run_id}_failed_manifest.json", plans[1], "FAILED", None, None)
    partial = paths.tmp_dir / run_id / "partial.tmp.json"
    partial.parent.mkdir(parents=True, exist_ok=True)
    partial.write_text('{"partial":true}\n', encoding="utf-8")
    return build_full_range_resume_controlled_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format="jsonl",
        max_codes_per_chunk=1,
        max_chunks_to_execute=2,
        data_source_type="mock",
        run_id=run_id,
    )


def _run_inconsistency_fixture(root: Path) -> dict[str, Any]:
    runtime_dir = root / "runtime"
    report_dir = root / "reports"
    run_id = "phase4q_block_fixture"
    plans, paths = _prepare_plans(runtime_dir, report_dir, run_id)
    _write_manifest(paths.manifest_dir / f"{run_id}_missing_output_manifest.json", plans[0], "SUCCESS", paths.feature_dir / "missing.json", None)
    return build_full_range_resume_controlled_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format="jsonl",
        max_codes_per_chunk=1,
        max_chunks_to_execute=2,
        data_source_type="mock",
        run_id=run_id,
    )


def _prepare_plans(runtime_dir: Path, report_dir: Path, run_id: str):
    prepare_mock_normalized_history(
        runtime_dir=runtime_dir,
        business_days=65,
        code_count=4,
        output_format="jsonl",
        report_dir=report_dir / "prepare",
    )
    discovery = discover_daily_quotes_normalized(runtime_dir, input_format="jsonl")
    if discovery.path is None or discovery.storage_format is None:
        raise RuntimeError("normalized fixture missing")
    records = create_storage_backend(discovery.storage_format).read_records(discovery.path)
    plans = build_full_range_chunk_plan(records, run_id=run_id, data_source_type="mock", max_codes_per_chunk=1)
    paths = resolve_full_range_paths(runtime_dir=runtime_dir, report_dir=report_dir)
    paths.ensure_dirs()
    return plans, paths


def _write_manifest(path: Path, plan, status: str, output_path: Path | None, audit_path: Path | None) -> None:
    manifest = FullRangeChunkManifest(
        run_id=plan.run_id,
        chunk_id=plan.chunk_id,
        status=status,
        date_start=plan.date_start,
        date_end=plan.date_end,
        code_count=plan.code_count,
        row_count=1,
        eligible_count=1,
        excluded_count=0,
        schema_validation_status="OK",
        leakage_audit_status="OK",
        output_path=str(output_path) if output_path else None,
        manifest_path=str(path),
        audit_path=str(audit_path) if audit_path else None,
        error_message=None if status == "SUCCESS" else "fixture failed chunk",
    )
    _write_json(path, manifest.to_dict())


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "runner_status",
        "max_chunks_to_execute",
        "planned_chunk_count",
        "skipped_success_chunk_count",
        "rerun_failed_chunk_count",
        "run_missing_chunk_count",
        "executed_chunk_count",
        "blocked_inconsistency_count",
        "partial_tmp_warning_count",
        "completed_chunk_count",
        "failed_chunk_count",
        "schema_validation_status",
        "leakage_audit_status",
    )
    return {key: summary.get(key) for key in keys}


def _source_contains(text: str) -> bool:
    return text in Path("src/ai_fund_lab_v2/candidate_ai/full_range.py").read_text(encoding="utf-8")


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    terms = ("sAuthId", "Authorization", "x-api-key", "password", "cookie", "token", "http://", "https://")
    return not any(term in text for term in terms)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-Q Resume-aware Controlled Runner Audit",
        "",
        "## Audit Result",
        "",
        f"- status: {result['status']}",
        f"- summary: `{result['summary_path']}`",
        "",
        "## Checks",
        "",
    ]
    for name, value in result["checks"].items():
        mark = "OK" if value else "NG"
        lines.append(f"- {mark}: `{name}`")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- The runner executes at most two controlled chunks.",
            "- It does not implement full-range generation, labels, dataset building, training, inference, backtest, broker API, orders, trading, or Portfolio auto-update.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
