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
from ai_fund_lab_v2.candidate_ai import (  # noqa: E402
    ALLOWED_FEATURE_PREFIXES,
    FORBIDDEN_FEATURE_TERMS,
    REQUIRED_FEATURE_COLUMNS,
    CandidateAIRuntimePaths,
    CandidateFeatureAudit,
    CandidateFeatureManifest,
    audit_feature_table,
    validate_feature_table,
)
from ai_fund_lab_v2.candidate_ai.schemas import AUDIT_FIELDS, MANIFEST_FIELDS  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402


PHASE = "Phase4-D Candidate Feature Builder Skeleton / Schema Contracts"
PYTEST_HINT = (
    "python3 scripts/audit_phase4d_candidate_feature_builder_skeleton.py && "
    "python3 -m pytest tests/test_phase4d_candidate_feature_builder_skeleton.py && "
    "python3 -m pytest -q"
)

PHASE_REPORT = ROOT / "docs/phase_reports/phase4d_candidate_feature_builder_skeleton.md"

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
    ROOT / "reports/phase_reports/phase4a_candidate_ai_design_audit.json",
    ROOT / "reports/phase_reports/phase4b_candidate_training_data_design_audit.json",
    ROOT / "reports/phase_reports/phase4c_candidate_feature_builder_design_audit.json",
)

PACKAGE_FILES = (
    ROOT / "src/ai_fund_lab_v2/candidate_ai/__init__.py",
    ROOT / "src/ai_fund_lab_v2/candidate_ai/schemas.py",
    ROOT / "src/ai_fund_lab_v2/candidate_ai/paths.py",
    ROOT / "src/ai_fund_lab_v2/candidate_ai/validation.py",
    ROOT / "src/ai_fund_lab_v2/candidate_ai/leakage_audit.py",
)

EXPECTED_REQUIRED_COLUMNS = frozenset(
    {
        "as_of_date",
        "target_date",
        "code",
        "feature_version",
        "source_snapshot_id",
        "universe_eligible",
        "excluded_reason",
    }
)

EXPECTED_ALLOWED_PREFIXES = (
    "price_momentum_",
    "volume_momentum_",
    "volatility_",
    "trend_",
    "relative_strength_",
    "market_regime_",
    "sector_relative_",
    "fundamental_",
    "liquidity_",
    "missing_flags_",
)

EXPECTED_FORBIDDEN_TERMS = (
    "future_return_",
    "future_max_return_",
    "future_max_drawdown_",
    "top_decile_",
    "downside_bad_",
    "momentum_candidate_label",
    "backtest",
    "trade",
    "selected",
    "bought",
    "sold",
    "cash",
    "portfolio",
    "annual_return",
    "final_assets",
    "paper_trade",
    "position",
    "allocation",
    "order",
    "execution",
    "profit",
    "loss",
    "pnl",
)


def run_audit(
    json_report_path: Path | str = "reports/phase_reports/phase4d_candidate_feature_builder_skeleton_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase4d_candidate_feature_builder_skeleton_audit.md",
) -> dict[str, Any]:
    valid_result = validate_feature_table(_valid_rows())
    forbidden_result = validate_feature_table(_rows_with_forbidden_column())
    invalid_date_result = validate_feature_table(_rows_with_invalid_date())
    invalid_prefix_result = validate_feature_table(_rows_with_invalid_prefix())
    audit_result = audit_feature_table(_rows_with_forbidden_column())
    paths = CandidateAIRuntimePaths(RuntimePaths(runtime_dir=Path(".runtime")))

    checks = {
        "required_input_docs_present": all(path.is_file() for path in REQUIRED_INPUT_DOCS),
        "phase4d_report_present": PHASE_REPORT.is_file(),
        "candidate_ai_package_skeleton_present": all(path.is_file() for path in PACKAGE_FILES),
        "feature_schema_contract_present": REQUIRED_FEATURE_COLUMNS == EXPECTED_REQUIRED_COLUMNS,
        "manifest_schema_contract_present": EXPECTED_MANIFEST_FIELDS.issubset(MANIFEST_FIELDS),
        "audit_schema_contract_present": EXPECTED_AUDIT_FIELDS.issubset(AUDIT_FIELDS),
        "runtime_path_helper_present": str(paths.features).endswith(".runtime/candidate_ai/features")
        and str(paths.manifests).endswith(".runtime/candidate_ai/manifests")
        and str(paths.audit).endswith(".runtime/candidate_ai/audit"),
        "schema_validation_present": callable(validate_feature_table),
        "leakage_audit_minimal_code_present": callable(audit_feature_table),
        "required_columns_defined": EXPECTED_REQUIRED_COLUMNS.issubset(REQUIRED_FEATURE_COLUMNS),
        "allowed_feature_prefixes_defined": all(prefix in ALLOWED_FEATURE_PREFIXES for prefix in EXPECTED_ALLOWED_PREFIXES),
        "forbidden_feature_terms_defined": all(term in FORBIDDEN_FEATURE_TERMS for term in EXPECTED_FORBIDDEN_TERMS),
        "valid_feature_table_fixture_passes": valid_result.is_valid,
        "forbidden_column_fixture_detected": "future_return_20d" in forbidden_result.forbidden_columns
        and audit_result.forbidden_feature_detected,
        "invalid_date_fixture_detected": invalid_date_result.invalid_date_rows == (0,)
        and audit_feature_table(_rows_with_invalid_date()).post_as_of_data_detected,
        "invalid_prefix_fixture_detected": "mystery_signal" in invalid_prefix_result.invalid_prefix_columns,
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


EXPECTED_MANIFEST_FIELDS = frozenset(
    {
        "feature_version",
        "created_at",
        "as_of_date",
        "target_date",
        "row_count",
        "eligible_count",
        "excluded_count",
        "source_snapshot_id",
        "input_sources",
        "output_path",
        "audit_path",
        "schema_version",
        "code_hash_optional",
    }
)

EXPECTED_AUDIT_FIELDS = frozenset(
    {
        "status",
        "feature_version",
        "as_of_date",
        "target_date",
        "row_count",
        "forbidden_feature_detected",
        "forbidden_columns",
        "future_column_detected",
        "label_column_detected",
        "post_as_of_data_detected",
        "fins_publication_violation_detected",
        "target_date_leakage_detected",
        "missing_required_columns",
        "invalid_prefix_columns",
        "eligible_count",
        "excluded_count",
        "excluded_reason_counts",
    }
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase4-D Candidate Feature Builder skeleton criteria.")
    parser.add_argument(
        "--json-report",
        default="reports/phase_reports/phase4d_candidate_feature_builder_skeleton_audit.json",
        help="JSON report output path.",
    )
    parser.add_argument(
        "--markdown-report",
        default="docs/phase_reports/phase4d_candidate_feature_builder_skeleton_audit.md",
        help="Markdown report output path.",
    )
    args = parser.parse_args(argv)
    result = run_audit(Path(args.json_report), Path(args.markdown_report))
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def _valid_rows() -> list[dict[str, object]]:
    return [
        {
            "as_of_date": "2026-06-01",
            "target_date": "2026-06-01",
            "code": "7203",
            "feature_version": "candidate_features_v1",
            "source_snapshot_id": "snapshot-001",
            "universe_eligible": True,
            "excluded_reason": "",
            "price_momentum_return_20d": 0.12,
            "volume_momentum_ratio_5d_20d": 1.8,
            "missing_flags_price": False,
        }
    ]


def _rows_with_forbidden_column() -> list[dict[str, object]]:
    row = dict(_valid_rows()[0])
    row["future_return_20d"] = 0.2
    return [row]


def _rows_with_invalid_date() -> list[dict[str, object]]:
    row = dict(_valid_rows()[0])
    row["as_of_date"] = "2026-06-02"
    row["target_date"] = "2026-06-01"
    return [row]


def _rows_with_invalid_prefix() -> list[dict[str, object]]:
    row = dict(_valid_rows()[0])
    row["mystery_signal"] = 1
    return [row]


def _non_implementation_boundary_present() -> bool:
    report_text = PHASE_REPORT.read_text(encoding="utf-8") if PHASE_REPORT.is_file() else ""
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in PACKAGE_FILES if path.is_file())
    blocked_code_terms = (
        "def train",
        "def predict",
        "def backtest",
        "place_order",
        "submit_order",
        "fins_summary",
        "JQuantsClient",
        "MarketDataStore",
        "read_parquet",
        "read_csv",
    )
    required_report_terms = (
        "daily_quotes_normalizedからの実feature生成",
        "label生成",
        "学習",
        "推論",
        "backtest",
        "発注",
    )
    return all(term in report_text for term in required_report_terms) and all(term not in source_text for term in blocked_code_terms)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AI Fund Lab vNext Phase4-D Candidate Feature Builder Skeleton Audit",
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
            "Phase4-D adds schema contracts, runtime path helper, schema validation, and minimal leakage audit only.",
            "Actual feature generation, label generation, training, inference, backtest, Paper Trading, ordering, broker live access, and portfolio auto-update are not implemented.",
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
