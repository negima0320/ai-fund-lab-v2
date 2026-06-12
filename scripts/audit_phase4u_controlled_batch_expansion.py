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

from ai_fund_lab_v2.candidate_ai import build_first_controlled_batch_summary  # noqa: E402
from scripts.audit_phase4t_post_batch_integrity import build_post_batch_integrity_summary  # noqa: E402
from scripts.build_candidate_features_controlled_batch_expansion import (  # noqa: E402
    EXPANSION_COMPLETED,
    READY_FOR_EXPANSION,
    SUMMARY_PATH,
    build_controlled_batch_expansion_summary,
)
from scripts.prepare_phase4k_normalized_history import prepare_mock_normalized_history  # noqa: E402

JSON_REPORT_PATH = Path("reports/phase_reports/phase4u_controlled_batch_expansion_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4u_controlled_batch_expansion_audit.md")


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="phase4u_expansion_") as temp_dir:
        root = Path(temp_dir)
        runtime_dir = root / "runtime"
        report_dir = root / "reports"
        prepare_mock_normalized_history(
            runtime_dir=runtime_dir,
            business_days=70,
            code_count=4,
            output_format="jsonl",
            report_dir=root / "prepare_reports",
        )
        gate_source = build_first_controlled_batch_summary(
            runtime_dir=runtime_dir,
            report_dir=report_dir,
            input_format="jsonl",
            max_codes_per_chunk=4,
            max_chunks_to_execute=2,
            data_source_type="mock",
            run_id="phase4u_gate_source",
        )
        phase4t_gate = build_post_batch_integrity_summary(gate_source)
        summary = build_controlled_batch_expansion_summary(
            runtime_dir=runtime_dir,
            report_dir=report_dir,
            input_format="jsonl",
            max_codes_per_chunk=4,
            max_chunks_to_execute=4,
            data_source_type="mock",
            run_id="phase4u_audit_expansion",
            phase4t_integrity_summary=phase4t_gate,
        )
    summary["summary_path"] = str(SUMMARY_PATH)
    _write_json(SUMMARY_PATH, summary)
    checks = {
        "controlled_expansion_cli_exists": Path("scripts/build_candidate_features_controlled_batch_expansion.py").is_file(),
        "phase4t_integrity_gate_checked": summary.get("integrity_gate_status") == "READY"
        and phase4t_gate.get("integrity_status") == READY_FOR_EXPANSION,
        "max_chunks_to_execute_is_four": summary.get("max_chunks_to_execute") == 4,
        "stop_on_first_failure_true": summary.get("stop_on_first_failure") is True,
        "max_failed_chunks_allowed_zero": summary.get("max_failed_chunks_allowed") == 0,
        "success_chunks_skipped": summary.get("skipped_success_chunk_count", 0) >= 2,
        "missing_chunks_executed": summary.get("executed_chunk_count", 0) >= 1,
        "executed_chunk_count_within_limit": summary.get("executed_chunk_count", 0) <= 4,
        "schema_validation_ok": summary.get("schema_validation_status") == "OK",
        "leakage_audit_ok": summary.get("leakage_audit_status") == "OK",
        "post_expansion_integrity_checked": "post_expansion_integrity" in summary
        and summary.get("tmp_leftover_count") == 0
        and summary.get("duplicate_output_count") == 0
        and summary.get("orphan_output_count") == 0,
        "summary_json_exists": SUMMARY_PATH.is_file(),
        "not_generalized_beyond_controlled_expansion": summary.get("expansion_status") == EXPANSION_COMPLETED
        and summary.get("max_chunks_to_execute") == 4,
        "label_generation_not_implemented": summary.get("label_generation_executed") is False,
        "training_inference_backtest_trading_not_implemented": summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "no_secret_terms_in_reports": _no_secret_terms(summary),
    }
    result = {
        "phase": "Phase4-U",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "summary": _compact_summary(summary),
        "summary_path": str(SUMMARY_PATH),
        "pytest_hint": "python3 -m pytest tests/test_phase4u_controlled_batch_expansion.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "expansion_status",
        "integrity_gate_status",
        "max_chunks_to_execute",
        "planned_chunk_count",
        "existing_success_chunk_count",
        "skipped_success_chunk_count",
        "executed_chunk_count",
        "completed_chunk_count",
        "failed_chunk_count",
        "remaining_missing_chunk_count",
        "schema_validation_status",
        "leakage_audit_status",
        "tmp_leftover_count",
        "duplicate_output_count",
        "orphan_output_count",
    )
    return {key: summary.get(key) for key in keys}


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    terms = ("sAuthId", "Authorization", "x-api-key", "password", "cookie", "token", "http://", "https://")
    return not any(term in text for term in terms)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-U Controlled Batch Expansion Audit",
        "",
        "## Audit Result",
        "",
        f"- status: {result['status']}",
        f"- summary: `{result['summary_path']}`",
        "",
        "## Expansion Summary",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Checks", ""])
    for name, value in result["checks"].items():
        mark = "OK" if value else "NG"
        lines.append(f"- {mark}: `{name}`")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- Phase4-U expands only a controlled mock/runtime batch up to four chunks.",
            "- It keeps stop_on_first_failure=true and max_failed_chunks_allowed=0.",
            "- It does not implement labels, datasets, model training, inference, backtest, broker API, orders, trading, or Portfolio auto-update.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
