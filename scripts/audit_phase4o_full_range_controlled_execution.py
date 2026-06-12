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
    CONTROLLED_EXECUTION_READY,
    build_full_range_controlled_summary,
    execute_full_range_chunk_controlled,
    promote_tmp_to_final,
)


PHASE = "Phase4-O Full-range Feature Dry-run Controlled Execution"
PYTEST_HINT = (
    "python3 scripts/build_candidate_features_full_range_controlled.py && "
    "python3 scripts/audit_phase4o_full_range_controlled_execution.py && "
    "python3 -m pytest tests/test_phase4o_full_range_controlled_execution.py && "
    "python3 -m pytest -q"
)

REQUIRED_INPUTS = (
    ROOT / "docs/phase_reports/phase4l_full_range_feature_dry_run_design.md",
    ROOT / "docs/phase_reports/phase4m_full_range_feature_dry_run_skeleton.md",
    ROOT / "docs/phase_reports/phase4n_full_range_no_write_gate.md",
    ROOT / "reports/phase_reports/phase4m_full_range_feature_dry_run_skeleton_audit.json",
    ROOT / "reports/phase_reports/phase4n_full_range_no_write_gate_audit.json",
    ROOT / "reports/candidate_ai/full_range/phase4m_full_range_dry_run_summary.json",
    ROOT / "reports/candidate_ai/full_range/phase4n_full_range_no_write_summary.json",
)

REQUIRED_FILES = (
    ROOT / "scripts/build_candidate_features_full_range_controlled.py",
    ROOT / "scripts/audit_phase4o_full_range_controlled_execution.py",
    ROOT / "docs/phase_reports/phase4o_full_range_controlled_execution.md",
    ROOT / "tests/test_phase4o_full_range_controlled_execution.py",
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
    json_report_path: Path | str = "reports/phase_reports/phase4o_full_range_controlled_execution_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase4o_full_range_controlled_execution_audit.md",
) -> dict[str, Any]:
    cli_result = subprocess.run(
        [sys.executable, "scripts/build_candidate_features_full_range_controlled.py", "--run-id", "phase4o_audit"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    cli_payload = _parse_json_stdout(cli_result.stdout)
    source_text = _source_text()
    report_text = (ROOT / "docs/phase_reports/phase4o_full_range_controlled_execution.md").read_text(encoding="utf-8")
    checks = {
        "required_inputs_present": all(path.is_file() for path in REQUIRED_INPUTS),
        "required_files_present": all(path.is_file() for path in REQUIRED_FILES),
        "controlled_execution_cli_exists": (ROOT / "scripts/build_candidate_features_full_range_controlled.py").is_file(),
        "max_chunks_to_execute_limit_exists": "max_chunks_to_execute" in source_text and cli_payload.get("max_chunks_to_execute") == 1,
        "only_one_minimal_chunk_executed": cli_payload.get("executed_chunk_count") == 1,
        "feature_output_written_after_ok": cli_payload.get("feature_output_written") is True
        and cli_payload.get("schema_validation_status") == "OK"
        and cli_payload.get("leakage_audit_status") == "OK",
        "tmp_to_final_atomic_move_exists": callable(promote_tmp_to_final)
        and cli_payload.get("tmp_to_final_atomic_move") is True
        and bool(cli_payload.get("feature_output_path"))
        and Path(str(cli_payload.get("feature_output_path"))).is_file()
        and not Path(str(cli_payload.get("tmp_output_path"))).exists(),
        "chunk_manifest_recorded": bool(cli_payload.get("chunk_manifest_path"))
        and _manifest_status(cli_payload.get("chunk_manifest_path")) == "SUCCESS",
        "run_manifest_updated": bool(cli_payload.get("run_manifest_path")) and _run_manifest_updated(cli_payload.get("run_manifest_path")),
        "summary_json_exists": bool(cli_payload.get("summary_path")) and Path(str(cli_payload.get("summary_path"))).is_file(),
        "schema_validation_ok": cli_payload.get("schema_validation_status") == "OK",
        "leakage_audit_ok": cli_payload.get("leakage_audit_status") == "OK",
        "resume_restart_compatibility_maintained": callable(execute_full_range_chunk_controlled)
        and "chunk_manifest" in source_text
        and "run_manifest" in source_text,
        "label_training_inference_backtest_trading_not_implemented": all(term not in source_text for term in FORBIDDEN_TERMS)
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
            "controlled_summary": cli_payload,
            "pytest_hint": PYTEST_HINT,
            "reports": {"json": str(json_report_path), "markdown": str(markdown_report_path)},
        }
    )
    _write_json(Path(json_report_path), result)
    _write_markdown(Path(markdown_report_path), result)
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase4-O full-range controlled execution.")
    parser.add_argument("--json-report", default="reports/phase_reports/phase4o_full_range_controlled_execution_audit.json")
    parser.add_argument("--markdown-report", default="docs/phase_reports/phase4o_full_range_controlled_execution_audit.md")
    args = parser.parse_args(argv)
    result = run_audit(json_report_path=Path(args.json_report), markdown_report_path=Path(args.markdown_report))
    return 0 if result["status"] == "complete" else 1


def _manifest_status(path: Any) -> str | None:
    if not path:
        return None
    return json.loads(Path(str(path)).read_text(encoding="utf-8")).get("status")


def _run_manifest_updated(path: Any) -> bool:
    if not path:
        return False
    payload = json.loads(Path(str(path)).read_text(encoding="utf-8"))
    return bool(
        payload.get("completed_chunk_count") == 1
        and payload.get("failed_chunk_count") == 0
        and payload.get("skipped_chunk_count", 0) >= 0
        and payload.get("last_updated_at")
    )


def _source_text() -> str:
    paths = (
        ROOT / "src/ai_fund_lab_v2/candidate_ai/full_range.py",
        ROOT / "scripts/build_candidate_features_full_range_controlled.py",
        ROOT / "scripts/audit_phase4o_full_range_controlled_execution.py",
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
    summary = payload["controlled_summary"]
    lines = [
        "# AI Fund Lab vNext Phase4-O Full-range Controlled Execution Audit",
        "",
        "## Audit Result",
        "",
        f"- phase: `{payload['phase']}`",
        f"- status: `{payload['status']}`",
        "",
        "## Checks",
        "",
    ]
    for name, value in payload["checks"].items():
        lines.append(f"- {name}: `{value}`")
    lines.extend(
        [
            "",
            "## Controlled Summary",
            "",
            f"- status: `{summary.get('status')}`",
            f"- controlled_status: `{summary.get('controlled_status')}`",
            f"- executed_chunk_count: `{summary.get('executed_chunk_count')}`",
            f"- feature_output_written: `{summary.get('feature_output_written')}`",
            f"- feature_output_path: `{summary.get('feature_output_path')}`",
            f"- chunk_manifest_path: `{summary.get('chunk_manifest_path')}`",
            f"- run_manifest_path: `{summary.get('run_manifest_path')}`",
            "",
            "Phase4-O executes only one controlled chunk. It does not implement labels, datasets, Candidate AI training, inference, backtest, trading, broker live access, ordering, or portfolio auto-update.",
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
