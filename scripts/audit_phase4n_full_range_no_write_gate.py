#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping  # noqa: E402
from ai_fund_lab_v2.candidate_ai.full_range import (  # noqa: E402
    NO_WRITE_GATE_READY,
    audit_chunk_plan_distribution,
    build_full_range_no_write_summary,
    evaluate_no_write_final_gate,
    validate_chunks_no_write,
)


PHASE = "Phase4-N Full-range Feature Dry-run Plan Audit / No-write Execution"
PYTEST_HINT = (
    "python3 scripts/check_candidate_features_full_range_no_write.py && "
    "python3 scripts/audit_phase4n_full_range_no_write_gate.py && "
    "python3 -m pytest tests/test_phase4n_full_range_no_write_gate.py && "
    "python3 -m pytest -q"
)

REQUIRED_INPUTS = (
    ROOT / "docs/phase_reports/phase4l_full_range_feature_dry_run_design.md",
    ROOT / "docs/phase_reports/phase4m_full_range_feature_dry_run_skeleton.md",
    ROOT / "reports/phase_reports/phase4m_full_range_feature_dry_run_skeleton_audit.json",
    ROOT / "reports/candidate_ai/full_range/phase4m_full_range_dry_run_summary.json",
    ROOT / "src/ai_fund_lab_v2/candidate_ai/full_range.py",
    ROOT / "scripts/build_candidate_features_full_range_dry_run.py",
)

REQUIRED_FILES = (
    ROOT / "scripts/check_candidate_features_full_range_no_write.py",
    ROOT / "scripts/audit_phase4n_full_range_no_write_gate.py",
    ROOT / "docs/phase_reports/phase4n_full_range_no_write_gate.md",
    ROOT / "tests/test_phase4n_full_range_no_write_gate.py",
)

FORBIDDEN_TERMS = (
    "def tr" + "ain",
    "def pre" + "dict",
    "def back" + "test",
    "def generate_" + "labels",
    "submit_" + "order",
    "place_" + "order",
    "JQuants" + "Client(",
)


def run_audit(
    *,
    json_report_path: Path | str = "reports/phase_reports/phase4n_full_range_no_write_gate_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase4n_full_range_no_write_gate_audit.md",
) -> dict[str, Any]:
    cli_result = subprocess.run(
        [sys.executable, "scripts/check_candidate_features_full_range_no_write.py", "--run-id", "phase4n_audit"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    cli_payload = _parse_json_stdout(cli_result.stdout)
    source_text = _source_text()
    report_text = (ROOT / "docs/phase_reports/phase4n_full_range_no_write_gate.md").read_text(encoding="utf-8")
    checks = {
        "required_inputs_present": all(path.is_file() for path in REQUIRED_INPUTS),
        "required_files_present": all(path.is_file() for path in REQUIRED_FILES),
        "no_write_cli_exists": (ROOT / "scripts/check_candidate_features_full_range_no_write.py").is_file(),
        "chunk_plan_distribution_audit_exists": callable(audit_chunk_plan_distribution),
        "no_write_chunk_validation_exists": callable(validate_chunks_no_write),
        "resume_restart_abnormal_cases_covered": _test_text_has_abnormal_cases(),
        "final_gate_exists": callable(evaluate_no_write_final_gate),
        "summary_json_output_exists": bool(cli_payload.get("summary_path")) and (ROOT / str(cli_payload["summary_path"])).is_file(),
        "ready_or_blocked_status_produced": cli_payload.get("gate_status") in {
            "READY_FOR_FULL_RANGE_EXECUTION",
            "BLOCKED_BY_CHUNK_PLAN",
            "BLOCKED_BY_RESUME_STATE",
            "BLOCKED_BY_NO_WRITE_VALIDATION",
            "BLOCKED_BY_SCHEMA",
            "BLOCKED_BY_LEAKAGE",
            "SKIPPED_NO_DATA",
        },
        "feature_output_not_written": cli_payload.get("feature_output_written") is False
        and cli_payload.get("feature_generation_executed") is False,
        "full_range_generation_not_implemented": ("feature output chunk書き込み" in report_text)
        and ("feature_generation_executed" + " = " + "true") not in source_text.lower(),
        "labels_training_inference_backtest_trading_not_implemented": all(term not in source_text for term in FORBIDDEN_TERMS)
        and "label生成" in report_text
        and "学習" in report_text
        and "推論" in report_text
        and "backtest" in report_text
        and "発注" in report_text,
    }
    status = "complete" if all(checks.values()) else "incomplete"
    result = sanitize_mapping(
        {
            "phase": PHASE,
            "status": status,
            "checks": checks,
            "no_write_summary": cli_payload,
            "gate_status": cli_payload.get("gate_status"),
            "pytest_hint": PYTEST_HINT,
            "reports": {"json": str(json_report_path), "markdown": str(markdown_report_path)},
        }
    )
    _write_json(Path(json_report_path), result)
    _write_markdown(Path(markdown_report_path), result)
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase4-N full-range no-write gate.")
    parser.add_argument("--json-report", default="reports/phase_reports/phase4n_full_range_no_write_gate_audit.json")
    parser.add_argument("--markdown-report", default="docs/phase_reports/phase4n_full_range_no_write_gate_audit.md")
    args = parser.parse_args(argv)
    result = run_audit(json_report_path=Path(args.json_report), markdown_report_path=Path(args.markdown_report))
    return 0 if result["status"] == "complete" else 1


def _test_text_has_abnormal_cases() -> bool:
    path = ROOT / "tests/test_phase4n_full_range_no_write_gate.py"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return all(term in text for term in ("SUCCESS", "FAILED", "partial", "missing_output", "unknown_status"))


def _source_text() -> str:
    paths = (
        ROOT / "src/ai_fund_lab_v2/candidate_ai/full_range.py",
        ROOT / "scripts/check_candidate_features_full_range_no_write.py",
        ROOT / "scripts/audit_phase4n_full_range_no_write_gate.py",
    )
    return "\n".join(path.read_text(encoding="utf-8") for path in paths if path.is_file())


def _parse_json_stdout(stdout: str) -> dict[str, Any]:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = payload["no_write_summary"]
    lines = [
        "# AI Fund Lab vNext Phase4-N Full-range No-write Gate Audit",
        "",
        "## Audit Result",
        "",
        f"- phase: `{payload['phase']}`",
        f"- status: `{payload['status']}`",
        f"- gate_status: `{payload.get('gate_status')}`",
        "",
        "## Checks",
        "",
    ]
    for name, value in payload["checks"].items():
        lines.append(f"- {name}: `{value}`")
    lines.extend(
        [
            "",
            "## No-write Summary",
            "",
            f"- status: `{summary.get('status')}`",
            f"- mode: `{summary.get('mode')}`",
            f"- feature_generation_executed: `{summary.get('feature_generation_executed')}`",
            f"- feature_output_written: `{summary.get('feature_output_written')}`",
            f"- chunk_count: `{summary.get('chunk_count')}`",
            f"- summary_path: `{summary.get('summary_path')}`",
            "",
            "Phase4-N is no-write only. It does not implement full-range feature generation, feature output chunk writes, labels, training, inference, backtest, trading, broker live access, ordering, or portfolio auto-update.",
            "",
            "## pytest",
            "",
            f"`{payload['pytest_hint']}`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
