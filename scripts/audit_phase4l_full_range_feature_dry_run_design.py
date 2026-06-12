#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping  # noqa: E402


PHASE = "Phase4-L Full-range Feature Dry-run Design"
DESIGN_DOC = ROOT / "docs/phase_reports/phase4l_full_range_feature_dry_run_design.md"
PYTEST_HINT = (
    "python3 scripts/audit_phase4l_full_range_feature_dry_run_design.py && "
    "python3 -m pytest tests/test_phase4l_full_range_feature_dry_run_design.py && "
    "python3 -m pytest -q"
)

REQUIRED_INPUTS = (
    ROOT / "docs/phase_reports/phase4j_real_feature_prepared_dry_run.md",
    ROOT / "docs/phase_reports/phase4k_normalized_history_readiness.md",
    ROOT / "reports/phase_reports/phase4k_normalized_history_readiness_audit.json",
    ROOT / "reports/candidate_ai/phase4k_mock_normalized_history_manifest.json",
    ROOT / "scripts/build_candidate_features_real_prepared_dry_run.py",
)

REQUIRED_TERMS = {
    "full_range_scope": ("Full-range Feature Generation Scope", "daily_quotes_normalized"),
    "target_period": ("対象期間設計", "first_generatable_as_of_date"),
    "universe": ("Universe設計", "primary universe source"),
    "chunking": ("Chunking Strategy", "chunk_id", "date_start", "date_end", "eligible_count"),
    "resume_restart": ("Resume / Restart Strategy", "成功済みchunkはskip", "tmp -> final atomic move"),
    "manifest": ("Manifest Strategy", "run manifest", "chunk manifest"),
    "audit": ("Audit Strategy", "future系feature混入なし", "as_of_dateより未来データ使用なし"),
    "storage": (".runtime/candidate_ai/features/full_range/", "parquet preferred", "json summary"),
    "performance_guard": ("Performance Guard", "max_rows_per_chunk"),
    "memory_guard": ("Memory Guard", "全期間・全銘柄を一括でmaterializeしない"),
    "data_source_type": ("mock normalized history", "real_runtime normalized history", "J-Quants API由来 normalized history", "skipped"),
    "feature_version": ("Feature Version Strategy", "candidate_features_full_range_dry_run_v1"),
    "schema_version": ("Schema Version Strategy", "schema_version"),
    "leakage_audit": ("Leakage Audit強化", "future_return_*", "portfolio", "order"),
    "dataset_readiness": ("Candidate Dataset前のReadiness条件", "failed_chunk_count = 0", "eligible_count total > 0"),
    "candidate_boundary": ("買い判断", "売却判断", "資金配分", "発注"),
    "phase4k_mock_context": ("data_source_type = mock", "READY_FOR_FULL_RANGE_FEATURE_DRY_RUN"),
}

FORBIDDEN_IMPLEMENTATION_TERMS = (
    "def tr" + "ain",
    "def pre" + "dict",
    "def back" + "test",
    "def generate_" + "labels",
    "submit_" + "order",
    "place_" + "order",
    "JQuants" + "Client(",
)

REQUIRED_OUTPUT_PATHS = (
    ".runtime/candidate_ai/features/full_range/",
    ".runtime/candidate_ai/manifests/full_range/",
    ".runtime/candidate_ai/audit/full_range/",
    "reports/candidate_ai/full_range/",
)


def run_audit(
    *,
    json_report_path: Path | str = "reports/phase_reports/phase4l_full_range_feature_dry_run_design_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase4l_full_range_feature_dry_run_design_audit.md",
) -> dict[str, Any]:
    text = DESIGN_DOC.read_text(encoding="utf-8") if DESIGN_DOC.is_file() else ""
    checks = {
        "required_inputs_present": all(path.exists() for path in REQUIRED_INPUTS),
        "design_doc_exists": DESIGN_DOC.is_file(),
        "full_range_scope_defined": _contains_all(text, REQUIRED_TERMS["full_range_scope"]),
        "target_period_defined": _contains_all(text, REQUIRED_TERMS["target_period"]),
        "universe_defined": _contains_all(text, REQUIRED_TERMS["universe"]),
        "chunking_defined": _contains_all(text, REQUIRED_TERMS["chunking"]),
        "resume_restart_defined": _contains_all(text, REQUIRED_TERMS["resume_restart"]),
        "manifest_strategy_defined": _contains_all(text, REQUIRED_TERMS["manifest"]),
        "audit_strategy_defined": _contains_all(text, REQUIRED_TERMS["audit"]),
        "storage_strategy_defined": _contains_all(text, REQUIRED_TERMS["storage"])
        and all(path in text for path in REQUIRED_OUTPUT_PATHS),
        "performance_guard_defined": _contains_all(text, REQUIRED_TERMS["performance_guard"]),
        "memory_guard_defined": _contains_all(text, REQUIRED_TERMS["memory_guard"]),
        "data_source_type_handling_defined": _contains_all(text, REQUIRED_TERMS["data_source_type"]),
        "feature_version_strategy_defined": _contains_all(text, REQUIRED_TERMS["feature_version"]),
        "schema_version_strategy_defined": _contains_all(text, REQUIRED_TERMS["schema_version"]),
        "leakage_audit_strengthened": _contains_all(text, REQUIRED_TERMS["leakage_audit"]),
        "candidate_dataset_readiness_defined": _contains_all(text, REQUIRED_TERMS["dataset_readiness"]),
        "candidate_boundary_preserved": _contains_all(text, REQUIRED_TERMS["candidate_boundary"]),
        "phase4k_mock_context_separated": _contains_all(text, REQUIRED_TERMS["phase4k_mock_context"]),
        "non_implementation_boundary_present": _non_implementation_boundary_present(text),
        "no_forbidden_code_added": _no_forbidden_code_added(),
    }
    status = "complete" if all(checks.values()) else "incomplete"
    result = sanitize_mapping(
        {
            "phase": PHASE,
            "status": status,
            "checks": checks,
            "design_doc": str(DESIGN_DOC),
            "readiness_decision": "DESIGN_READY_FOR_PHASE4_M" if status == "complete" else "DESIGN_INCOMPLETE",
            "pytest_hint": PYTEST_HINT,
            "reports": {"json": str(json_report_path), "markdown": str(markdown_report_path)},
        }
    )
    _write_json(Path(json_report_path), result)
    _write_markdown(Path(markdown_report_path), result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase4-L full-range feature dry-run design.")
    parser.add_argument("--json-report", default="reports/phase_reports/phase4l_full_range_feature_dry_run_design_audit.json")
    parser.add_argument("--markdown-report", default="docs/phase_reports/phase4l_full_range_feature_dry_run_design_audit.md")
    args = parser.parse_args(argv)
    result = run_audit(json_report_path=Path(args.json_report), markdown_report_path=Path(args.markdown_report))
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def _contains_all(text: str, terms: tuple[str, ...]) -> bool:
    return all(term in text for term in terms)


def _non_implementation_boundary_present(text: str) -> bool:
    required = (
        "full-range feature generation本体",
        "label生成",
        "dataset builder",
        "Candidate AI本体",
        "学習",
        "推論",
        "backtest",
        "Broker実API",
        "発注",
        "Portfolio自動更新",
    )
    return all(term in text for term in required)


def _no_forbidden_code_added() -> bool:
    source_paths = (
        ROOT / "scripts/audit_phase4l_full_range_feature_dry_run_design.py",
    )
    text = "\n".join(path.read_text(encoding="utf-8") for path in source_paths if path.is_file())
    safe_terms = (
        "def tr" + "ain",
        "def pre" + "dict",
        "def back" + "test",
        "def generate_" + "labels",
        "submit_" + "order",
        "place_" + "order",
        "JQuants" + "Client(",
    )
    return all(term not in text for term in FORBIDDEN_IMPLEMENTATION_TERMS) and all(term not in text for term in safe_terms)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AI Fund Lab vNext Phase4-L Full-range Feature Dry-run Design Audit",
        "",
        "## Audit Result",
        "",
        f"- phase: `{payload['phase']}`",
        f"- status: `{payload['status']}`",
        f"- readiness_decision: `{payload['readiness_decision']}`",
        "",
        "## Checks",
        "",
    ]
    for name, value in payload["checks"].items():
        lines.append(f"- {name}: `{value}`")
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "Phase4-L fixes the design for full-range feature dry-run chunking, resume/restart, storage, manifest, audit, data_source_type handling, feature/schema versioning, leakage checks, and dataset-readiness gates.",
            "",
            "It does not implement full-range feature generation, labels, datasets, Candidate AI training, inference, backtest, trading, broker live access, ordering, or portfolio auto-update.",
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
