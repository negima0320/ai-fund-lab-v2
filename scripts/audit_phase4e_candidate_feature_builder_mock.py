from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping  # noqa: E402
from ai_fund_lab_v2.candidate_ai import (  # noqa: E402
    build_candidate_features_mock,
    build_candidate_features_mock_with_audit,
    build_mock_daily_quotes_normalized,
    validate_feature_table,
    write_candidate_feature_outputs,
)
from ai_fund_lab_v2.candidate_ai.leakage_audit import audit_feature_table  # noqa: E402


PHASE = "Phase4-E Candidate Feature Builder Mock Implementation"
PYTEST_HINT = (
    "python3 scripts/build_candidate_features_mock.py && "
    "python3 scripts/audit_phase4e_candidate_feature_builder_mock.py && "
    "python3 -m pytest tests/test_phase4e_candidate_feature_builder_mock.py && "
    "python3 -m pytest -q"
)

REQUIRED_INPUT_DOCS = (
    ROOT / "docs/00_vision/investment_philosophy.md",
    ROOT / "docs/01_requirements/system_requirements.md",
    ROOT / "docs/01_requirements/success_metrics.md",
    ROOT / "docs/01_requirements/phase_roadmap.md",
    ROOT / "docs/02_architecture/system_architecture.md",
    ROOT / "docs/03_ai_design/candidate_ai_design.md",
    ROOT / "docs/03_ai_design/candidate_feature_catalog.md",
    ROOT / "docs/03_ai_design/candidate_training_data_design.md",
    ROOT / "docs/03_ai_design/candidate_feature_builder_design.md",
    ROOT / "docs/phase_reports/phase4a_candidate_ai_design.md",
    ROOT / "docs/phase_reports/phase4b_candidate_training_data_design.md",
    ROOT / "docs/phase_reports/phase4c_candidate_feature_builder_design.md",
    ROOT / "docs/phase_reports/phase4d_candidate_feature_builder_skeleton.md",
    ROOT / "reports/phase_reports/phase4a_candidate_ai_design_audit.json",
    ROOT / "reports/phase_reports/phase4b_candidate_training_data_design_audit.json",
    ROOT / "reports/phase_reports/phase4c_candidate_feature_builder_design_audit.json",
    ROOT / "reports/phase_reports/phase4d_candidate_feature_builder_skeleton_audit.json",
)

REQUIRED_FILES = (
    ROOT / "src/ai_fund_lab_v2/candidate_ai/feature_builder.py",
    ROOT / "src/ai_fund_lab_v2/candidate_ai/manifest.py",
    ROOT / "src/ai_fund_lab_v2/candidate_ai/mock_data.py",
    ROOT / "scripts/build_candidate_features_mock.py",
    ROOT / "docs/phase_reports/phase4e_candidate_feature_builder_mock.md",
    ROOT / "tests/test_phase4e_candidate_feature_builder_mock.py",
)

EXPECTED_FEATURE_COLUMNS = (
    "price_momentum_return_5d",
    "price_momentum_return_20d",
    "volume_momentum_ratio_5d",
    "volatility_return_std_20d",
    "trend_close_over_ma_20d",
    "liquidity_avg_volume_20d",
    "missing_flags_insufficient_lookback",
)


def run_audit(
    json_report_path: Path | str = "reports/phase_reports/phase4e_candidate_feature_builder_mock_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase4e_candidate_feature_builder_mock_audit.md",
) -> dict[str, Any]:
    source_rows = build_mock_daily_quotes_normalized()
    build_result = build_candidate_features_mock_with_audit(source_rows, as_of_date="2026-06-01")
    validation = validate_feature_table(build_result.rows)
    forbidden_rows = [dict(build_result.rows[0], future_return_20d=0.1)]
    forbidden_audit = audit_feature_table(forbidden_rows)

    with tempfile.TemporaryDirectory() as tmpdir:
        paths = write_candidate_feature_outputs(build_result.rows, audit=build_result.audit, runtime_dir=tmpdir)
        output_files_exist = all(path.is_file() for path in paths.values())
        output_paths_under_runtime = all(str(path).startswith(str(Path(tmpdir) / "candidate_ai")) for path in paths.values())

    checks = {
        "required_input_docs_present": all(path.is_file() for path in REQUIRED_INPUT_DOCS),
        "phase4e_files_present": all(path.is_file() for path in REQUIRED_FILES),
        "mock_data_fixture_present": callable(build_mock_daily_quotes_normalized),
        "mock_feature_builder_present": callable(build_candidate_features_mock),
        "manifest_writer_present": callable(write_candidate_feature_outputs),
        "required_columns_present": _required_columns_present(build_result.rows),
        "expected_mock_feature_columns_present": all(column in build_result.rows[0] for column in EXPECTED_FEATURE_COLUMNS),
        "schema_validation_passes": validation.is_valid,
        "leakage_audit_passes": build_result.audit.status == "OK" and not build_result.audit.forbidden_feature_detected,
        "forbidden_feature_detection_works": forbidden_audit.status == "ERROR"
        and "future_return_20d" in forbidden_audit.forbidden_columns,
        "future_rows_ignored": _future_rows_ignored(source_rows),
        "insufficient_lookback_excluded": _insufficient_lookback_excluded(build_result.rows),
        "audit_counts_present": build_result.audit.row_count == 2
        and build_result.audit.eligible_count == 1
        and build_result.audit.excluded_count == 1
        and build_result.audit.excluded_reason_counts.get("insufficient_lookback") == 1,
        "runtime_outputs_written": output_files_exist and output_paths_under_runtime,
        "script_has_no_real_data_access": _script_has_no_real_data_access(),
        "non_implementation_boundary_present": _non_implementation_boundary_present(),
    }
    status = "complete" if all(checks.values()) else "incomplete"
    result = sanitize_mapping(
        {
            "phase": PHASE,
            "status": status,
            "checks": checks,
            "pytest_hint": PYTEST_HINT,
            "reports": {
                "json": str(json_report_path),
                "markdown": str(markdown_report_path),
            },
        }
    )
    _write_json(Path(json_report_path), result)
    _write_markdown(Path(markdown_report_path), result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase4-E Candidate Feature Builder mock implementation.")
    parser.add_argument(
        "--json-report",
        default="reports/phase_reports/phase4e_candidate_feature_builder_mock_audit.json",
        help="JSON report output path.",
    )
    parser.add_argument(
        "--markdown-report",
        default="docs/phase_reports/phase4e_candidate_feature_builder_mock_audit.md",
        help="Markdown report output path.",
    )
    args = parser.parse_args(argv)
    result = run_audit(Path(args.json_report), Path(args.markdown_report))
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def _required_columns_present(rows: list[dict[str, Any]]) -> bool:
    required = {
        "as_of_date",
        "target_date",
        "code",
        "feature_version",
        "source_snapshot_id",
        "universe_eligible",
        "excluded_reason",
    }
    return all(required.issubset(row) for row in rows)


def _future_rows_ignored(source_rows: list[dict[str, Any]]) -> bool:
    with_future = build_candidate_features_mock(source_rows, as_of_date="2026-06-01")
    without_future = build_candidate_features_mock(
        [row for row in source_rows if str(row["date"]) <= "2026-06-01"],
        as_of_date="2026-06-01",
    )
    return [_without_created_at(row) for row in with_future] == [_without_created_at(row) for row in without_future]


def _without_created_at(row: dict[str, Any]) -> dict[str, Any]:
    comparable = dict(row)
    comparable.pop("created_at", None)
    return comparable


def _insufficient_lookback_excluded(rows: list[dict[str, Any]]) -> bool:
    row = next(item for item in rows if item["code"] == "9999")
    return (
        row["universe_eligible"] is False
        and row["excluded_reason"] == "insufficient_lookback"
        and row["missing_flags_insufficient_lookback"] is True
    )


def _script_has_no_real_data_access() -> bool:
    script_text = (ROOT / "scripts/build_candidate_features_mock.py").read_text(encoding="utf-8")
    blocked_terms = ("read_csv", "read_parquet", "MarketDataStore", "JQuants", "requests", "urllib", "--input")
    return all(term not in script_text for term in blocked_terms)


def _non_implementation_boundary_present() -> bool:
    report = ROOT / "docs/phase_reports/phase4e_candidate_feature_builder_mock.md"
    report_text = report.read_text(encoding="utf-8") if report.is_file() else ""
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "src/ai_fund_lab_v2/candidate_ai/feature_builder.py",
            ROOT / "src/ai_fund_lab_v2/candidate_ai/manifest.py",
            ROOT / "src/ai_fund_lab_v2/candidate_ai/mock_data.py",
        )
        if path.is_file()
    )
    blocked_source_terms = (
        "def train",
        "def predict",
        "def backtest",
        "place_order",
        "submit_order",
        "PaperTrading",
        "OpportunityAI",
        "CapitalAllocation",
        "JQuantsClient",
        "MarketDataStore",
    )
    required_report_terms = (
        "実daily_quotes_normalized読み込みは実装しない",
        "label生成は実装しない",
        "学習は実装しない",
        "推論は実装しない",
        "backtestは実装しない",
        "発注は実装しない",
    )
    return all(term not in source_text for term in blocked_source_terms) and all(
        term in report_text for term in required_report_terms
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AI Fund Lab vNext Phase4-E Candidate Feature Builder Mock Audit",
        "",
        "## Audit Result",
        "",
        f"- phase: `{payload['phase']}`",
        f"- status: `{payload['status']}`",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- `{name}`: {'OK' if passed else 'NG'}" for name, passed in sorted(payload["checks"].items()))
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "Phase4-E adds mock-only Candidate feature generation, schema validation, leakage audit, manifest output, and runtime dry-run artifacts.",
            "It does not add real data loading, label generation, training, inference, backtest, Paper Trading, ordering, broker live access, or portfolio auto-update.",
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
