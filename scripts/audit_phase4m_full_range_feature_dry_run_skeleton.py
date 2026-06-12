#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
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

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping  # noqa: E402
from ai_fund_lab_v2.candidate_ai.full_range import (  # noqa: E402
    FullRangeChunkManifest,
    FullRangeChunkPlan,
    FullRangeRunManifest,
    build_full_range_chunk_plan,
    build_full_range_dry_run_summary,
    check_resume_restart,
    resolve_full_range_paths,
)


PHASE = "Phase4-M Full-range Feature Dry-run Skeleton"
PYTEST_HINT = (
    "python3 scripts/build_candidate_features_full_range_dry_run.py && "
    "python3 scripts/audit_phase4m_full_range_feature_dry_run_skeleton.py && "
    "python3 -m pytest tests/test_phase4m_full_range_feature_dry_run_skeleton.py && "
    "python3 -m pytest -q"
)

REQUIRED_INPUTS = (
    ROOT / "docs/phase_reports/phase4l_full_range_feature_dry_run_design.md",
    ROOT / "docs/phase_reports/phase4l_full_range_feature_dry_run_design_audit.md",
    ROOT / "reports/phase_reports/phase4l_full_range_feature_dry_run_design_audit.json",
    ROOT / "docs/phase_reports/phase4k_normalized_history_readiness.md",
    ROOT / "reports/phase_reports/phase4k_normalized_history_readiness_audit.json",
)

REQUIRED_FILES = (
    ROOT / "src/ai_fund_lab_v2/candidate_ai/full_range.py",
    ROOT / "scripts/build_candidate_features_full_range_dry_run.py",
    ROOT / "scripts/audit_phase4m_full_range_feature_dry_run_skeleton.py",
    ROOT / "docs/phase_reports/phase4m_full_range_feature_dry_run_skeleton.md",
    ROOT / "tests/test_phase4m_full_range_feature_dry_run_skeleton.py",
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
    json_report_path: Path | str = "reports/phase_reports/phase4m_full_range_feature_dry_run_skeleton_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase4m_full_range_feature_dry_run_skeleton_audit.md",
) -> dict[str, Any]:
    skipped_summary = _run_skipped_fixture()
    cli_result = subprocess.run(
        [sys.executable, "scripts/build_candidate_features_full_range_dry_run.py", "--run-id", "phase4m_audit"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    cli_payload = _parse_json_stdout(cli_result.stdout)
    source_text = _source_text()
    report_text = (ROOT / "docs/phase_reports/phase4m_full_range_feature_dry_run_skeleton.md").read_text(encoding="utf-8")
    paths = resolve_full_range_paths()
    checks = {
        "required_inputs_present": all(path.is_file() for path in REQUIRED_INPUTS),
        "required_files_present": all(path.is_file() for path in REQUIRED_FILES),
        "chunk_plan_builder_exists": callable(build_full_range_chunk_plan),
        "month_date_chunk_exists": _month_chunk_check(),
        "code_chunk_exists": _code_chunk_check(),
        "run_manifest_model_exists": FullRangeRunManifest is not None,
        "chunk_manifest_model_exists": FullRangeChunkManifest is not None,
        "resume_restart_checker_exists": callable(check_resume_restart),
        "full_range_path_resolver_exists": all(
            str(path).endswith(expected)
            for path, expected in (
                (paths.feature_dir, "candidate_ai/features/full_range"),
                (paths.manifest_dir, "candidate_ai/manifests/full_range"),
                (paths.audit_dir, "candidate_ai/audit/full_range"),
                (paths.tmp_dir, "candidate_ai/tmp/full_range"),
                (paths.report_dir, "reports/candidate_ai/full_range"),
            )
        ),
        "dry_run_cli_exists": (ROOT / "scripts/build_candidate_features_full_range_dry_run.py").is_file(),
        "dry_run_cli_does_not_generate_features": cli_result.returncode == 0 and cli_payload.get("feature_generation_executed") is False,
        "summary_json_output_exists": bool(cli_payload.get("summary_path")) and (ROOT / str(cli_payload["summary_path"])).is_file(),
        "skipped_safe_exit_supported": skipped_summary["status"] == "SKIPPED" and skipped_summary["feature_generation_executed"] is False,
        "full_range_generation_not_implemented": ("feature_generation_executed" + " = " + "true") not in source_text.lower()
        and "full-range feature generation本体" in report_text,
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
            "dry_run_cli_summary": cli_payload,
            "skipped_fixture_summary": skipped_summary,
            "pytest_hint": PYTEST_HINT,
            "reports": {"json": str(json_report_path), "markdown": str(markdown_report_path)},
        }
    )
    _write_json(Path(json_report_path), result)
    _write_markdown(Path(markdown_report_path), result)
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase4-M full-range feature dry-run skeleton.")
    parser.add_argument("--json-report", default="reports/phase_reports/phase4m_full_range_feature_dry_run_skeleton_audit.json")
    parser.add_argument("--markdown-report", default="docs/phase_reports/phase4m_full_range_feature_dry_run_skeleton_audit.md")
    args = parser.parse_args(argv)
    result = run_audit(json_report_path=Path(args.json_report), markdown_report_path=Path(args.markdown_report))
    return 0 if result["status"] == "complete" else 1


def _month_chunk_check() -> bool:
    plans = build_full_range_chunk_plan(_fixture_records(), run_id="audit", data_source_type="mock", max_codes_per_chunk=10)
    return len({(plan.date_start, plan.date_end) for plan in plans}) >= 2


def _code_chunk_check() -> bool:
    plans = build_full_range_chunk_plan(_fixture_records(), run_id="audit", data_source_type="mock", max_codes_per_chunk=1)
    return len(plans) >= 4 and all(isinstance(plan, FullRangeChunkPlan) for plan in plans)


def _fixture_records() -> list[dict[str, Any]]:
    return [
        {"Date": "2026-03-30", "Code": "11110", "Open": 1, "High": 2, "Low": 1, "Close": 2, "Volume": 100},
        {"Date": "2026-03-31", "Code": "22220", "Open": 1, "High": 2, "Low": 1, "Close": 2, "Volume": 100},
        {"Date": "2026-04-01", "Code": "11110", "Open": 1, "High": 2, "Low": 1, "Close": 2, "Volume": 100},
        {"Date": "2026-04-02", "Code": "22220", "Open": 1, "High": 2, "Low": 1, "Close": 2, "Volume": 100},
    ]


def _run_skipped_fixture() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        return build_full_range_dry_run_summary(runtime_dir=Path(tmp) / "runtime", report_dir=Path(tmp) / "reports", run_id="skipped_fixture")


def _parse_json_stdout(stdout: str) -> dict[str, Any]:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {}


def _source_text() -> str:
    paths = (
        ROOT / "src/ai_fund_lab_v2/candidate_ai/full_range.py",
        ROOT / "scripts/build_candidate_features_full_range_dry_run.py",
        ROOT / "scripts/audit_phase4m_full_range_feature_dry_run_skeleton.py",
    )
    return "\n".join(path.read_text(encoding="utf-8") for path in paths if path.is_file())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AI Fund Lab vNext Phase4-M Full-range Feature Dry-run Skeleton Audit",
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
    summary = payload["dry_run_cli_summary"]
    lines.extend(
        [
            "",
            "## Dry-run CLI",
            "",
            f"- status: `{summary.get('status')}`",
            f"- mode: `{summary.get('mode')}`",
            f"- feature_generation_executed: `{summary.get('feature_generation_executed')}`",
            f"- chunk_count: `{summary.get('chunk_count')}`",
            f"- summary_path: `{summary.get('summary_path')}`",
            "",
            "Phase4-M is skeleton only. It does not implement full-range feature generation, labels, training, inference, backtest, trading, broker live access, ordering, or portfolio auto-update.",
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
