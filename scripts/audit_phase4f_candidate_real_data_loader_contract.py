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
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping  # noqa: E402
from ai_fund_lab_v2.candidate_ai import (  # noqa: E402
    DAILY_QUOTES_NORMALIZED_COLUMN_MAPPING,
    STANDARD_INPUT_COLUMNS,
    adapt_daily_quotes_normalized,
    build_candidate_features_mock_with_audit,
    build_mock_daily_quotes_normalized,
    validate_daily_quotes_normalized_input,
    write_candidate_loader_contract_outputs,
)


PHASE = "Phase4-F Candidate Real Data Loader Contract / Adapter Design"
PYTEST_HINT = (
    "python3 scripts/check_candidate_real_data_loader_contract.py && "
    "python3 scripts/audit_phase4f_candidate_real_data_loader_contract.py && "
    "python3 scripts/build_candidate_features_mock.py && "
    "python3 scripts/audit_phase4e_candidate_feature_builder_mock.py && "
    "python3 -m pytest tests/test_phase4f_candidate_real_data_loader_contract.py && "
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
    ROOT / "docs/phase_reports/phase4e_candidate_feature_builder_mock.md",
    ROOT / "reports/phase_reports/phase4a_candidate_ai_design_audit.json",
    ROOT / "reports/phase_reports/phase4b_candidate_training_data_design_audit.json",
    ROOT / "reports/phase_reports/phase4c_candidate_feature_builder_design_audit.json",
    ROOT / "reports/phase_reports/phase4d_candidate_feature_builder_skeleton_audit.json",
    ROOT / "reports/phase_reports/phase4e_candidate_feature_builder_mock_audit.json",
)

REQUIRED_FILES = (
    ROOT / "src/ai_fund_lab_v2/candidate_ai/data_loader.py",
    ROOT / "src/ai_fund_lab_v2/candidate_ai/loader_manifest.py",
    ROOT / "scripts/check_candidate_real_data_loader_contract.py",
    ROOT / "docs/phase_reports/phase4f_candidate_real_data_loader_contract.md",
    ROOT / "tests/test_phase4f_candidate_real_data_loader_contract.py",
)


def run_audit(
    json_report_path: Path | str = "reports/phase_reports/phase4f_candidate_real_data_loader_contract_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase4f_candidate_real_data_loader_contract_audit.md",
) -> dict[str, Any]:
    records = _fixture_records()
    loader_result = adapt_daily_quotes_normalized(
        records,
        as_of_date="2026-06-01",
        input_source_path="fixture://phase4f/daily_quotes_normalized",
        input_manifest_path="fixture://phase4f/manifest",
    )
    validation = validate_daily_quotes_normalized_input(records, as_of_date="2026-06-01")
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = write_candidate_loader_contract_outputs(loader_result.rows, audit=loader_result.audit, runtime_dir=tmpdir)
        outputs_written = all(path.is_file() for path in paths.values())
        dry_run = subprocess.run(
            [sys.executable, "scripts/check_candidate_real_data_loader_contract.py", "--runtime-dir", tmpdir],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    phase4e_result = build_candidate_features_mock_with_audit(
        build_mock_daily_quotes_normalized(),
        as_of_date="2026-06-01",
    )
    report_text = (ROOT / "docs/phase_reports/phase4f_candidate_real_data_loader_contract.md").read_text(encoding="utf-8") if (ROOT / "docs/phase_reports/phase4f_candidate_real_data_loader_contract.md").is_file() else ""
    checks = {
        "required_input_docs_present": all(path.is_file() for path in REQUIRED_INPUT_DOCS),
        "phase4f_files_present": all(path.is_file() for path in REQUIRED_FILES),
        "real_data_loader_contract_exists": callable(adapt_daily_quotes_normalized),
        "daily_quotes_normalized_adapter_exists": DAILY_QUOTES_NORMALIZED_COLUMN_MAPPING
        == {
            "Date": "date",
            "Code": "code",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        },
        "schema_mapping_documented": all(term in report_text for term in ("Date -> date", "Code -> code", "Open -> open", "Volume -> volume")),
        "standard_input_columns_defined": STANDARD_INPUT_COLUMNS == ("date", "code", "open", "high", "low", "close", "volume"),
        "input_schema_validation_exists": validation.future_row_count == 1 and validation.is_valid,
        "future_rows_filtered": all(row["date"] <= "2026-06-01" for row in loader_result.rows)
        and loader_result.audit.dropped_future_row_count == 1,
        "dropped_future_row_count_recorded": loader_result.audit.to_dict()["dropped_future_row_count"] == 1,
        "source_snapshot_id_rule_exists": loader_result.audit.source_snapshot_id.startswith("daily_quotes_normalized:2026-06-01:"),
        "input_manifest_hash_rule_exists": bool(loader_result.audit.input_hash_optional)
        and loader_result.audit.input_source_path == "fixture://phase4f/daily_quotes_normalized"
        and loader_result.audit.input_manifest_path == "fixture://phase4f/manifest",
        "trading_calendar_window_rule_documented": all(
            term in report_text
            for term in ("lookbackは営業日ベース", "as_of_dateが非営業日の場合", "Phase4-Fでは本格calendar integrationは行わない")
        ),
        "runtime_outputs_written": outputs_written,
        "real_data_dry_run_script_exists": dry_run.returncode == 0 and "dropped_future_row_count" in dry_run.stdout,
        "phase4e_mock_builder_compatible": phase4e_result.validation.is_valid and phase4e_result.audit.status == "OK",
        "non_implementation_boundary_present": _non_implementation_boundary_present(report_text),
    }
    status = "complete" if all(checks.values()) else "incomplete"
    result = sanitize_mapping(
        {
            "phase": PHASE,
            "status": status,
            "checks": checks,
            "pytest_hint": PYTEST_HINT,
            "reports": {"json": str(json_report_path), "markdown": str(markdown_report_path)},
        }
    )
    _write_json(Path(json_report_path), result)
    _write_markdown(Path(markdown_report_path), result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase4-F Candidate real data loader contract.")
    parser.add_argument("--json-report", default="reports/phase_reports/phase4f_candidate_real_data_loader_contract_audit.json")
    parser.add_argument("--markdown-report", default="docs/phase_reports/phase4f_candidate_real_data_loader_contract_audit.md")
    args = parser.parse_args(argv)
    result = run_audit(Path(args.json_report), Path(args.markdown_report))
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def _fixture_records() -> list[dict[str, object]]:
    return [
        {"Date": "2026-05-29", "Code": "72030", "Open": 100, "High": 110, "Low": 95, "Close": 108, "Volume": 1000},
        {"Date": "2026-06-01", "Code": "72030", "Open": 108, "High": 112, "Low": 106, "Close": 111, "Volume": 1200},
        {"Date": "2026-06-02", "Code": "72030", "Open": 999, "High": 999, "Low": 999, "Close": 999, "Volume": 9999},
    ]


def _non_implementation_boundary_present(report_text: str) -> bool:
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "src/ai_fund_lab_v2/candidate_ai/data_loader.py",
            ROOT / "src/ai_fund_lab_v2/candidate_ai/loader_manifest.py",
        )
    )
    blocked_source_terms = (
        "def train",
        "def predict",
        "def backtest",
        "def generate_labels",
        "JQuantsClient",
        "MarketDataStore",
        "read_parquet",
        "read_csv",
        "submit_order",
        "place_order",
    )
    required_report_terms = (
        "実データ全量feature生成は実装しない",
        "label生成は実装しない",
        "学習は実装しない",
        "推論は実装しない",
        "backtestは実装しない",
        "発注は実装しない",
    )
    return all(term not in source_text for term in blocked_source_terms) and all(term in report_text for term in required_report_terms)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AI Fund Lab vNext Phase4-F Candidate Real Data Loader Contract Audit",
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
            "Phase4-F fixes the adapter contract between Phase1 daily_quotes_normalized and Candidate Feature Builder standard input.",
            "It validates schema, filters future rows, records loader manifest/audit metadata, and keeps Phase4-E mock builder compatible.",
            "It does not implement full real-data feature generation, labels, training, inference, backtest, Paper Trading, ordering, or portfolio auto-update.",
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
