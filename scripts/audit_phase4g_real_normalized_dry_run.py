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
    build_candidate_features_mock_with_audit,
    build_mock_daily_quotes_normalized,
    build_trading_calendar_window,
    discover_daily_quotes_normalized,
    read_daily_quotes_normalized_small_range,
)
from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes, write_daily_quotes_normalized  # noqa: E402
from ai_fund_lab_v2.data_store import MarketDataStore  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402


PHASE = "Phase4-G Real Normalized Data Dry-run / Trading Calendar Window"
PYTEST_HINT = (
    "python3 scripts/check_candidate_real_normalized_dry_run.py && "
    "python3 scripts/audit_phase4g_real_normalized_dry_run.py && "
    "python3 scripts/build_candidate_features_mock.py && "
    "python3 scripts/audit_phase4e_candidate_feature_builder_mock.py && "
    "python3 -m pytest tests/test_phase4g_real_normalized_dry_run.py && "
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
    ROOT / "docs/phase_reports/phase4f_candidate_real_data_loader_contract.md",
    ROOT / "reports/phase_reports/phase4a_candidate_ai_design_audit.json",
    ROOT / "reports/phase_reports/phase4b_candidate_training_data_design_audit.json",
    ROOT / "reports/phase_reports/phase4c_candidate_feature_builder_design_audit.json",
    ROOT / "reports/phase_reports/phase4d_candidate_feature_builder_skeleton_audit.json",
    ROOT / "reports/phase_reports/phase4e_candidate_feature_builder_mock_audit.json",
    ROOT / "reports/phase_reports/phase4f_candidate_real_data_loader_contract_audit.json",
)

REQUIRED_FILES = (
    ROOT / "src/ai_fund_lab_v2/candidate_ai/normalized_data_reader.py",
    ROOT / "src/ai_fund_lab_v2/candidate_ai/trading_calendar_window.py",
    ROOT / "scripts/check_candidate_real_normalized_dry_run.py",
    ROOT / "docs/phase_reports/phase4g_real_normalized_dry_run.md",
    ROOT / "tests/test_phase4g_real_normalized_dry_run.py",
)


def run_audit(
    json_report_path: Path | str = "reports/phase_reports/phase4g_real_normalized_dry_run_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase4g_real_normalized_dry_run_audit.md",
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as fixture_tmp, tempfile.TemporaryDirectory() as missing_tmp:
        fixture_runtime = Path(fixture_tmp) / "runtime"
        _prepare_fixture_runtime(fixture_runtime)
        discovery = discover_daily_quotes_normalized(fixture_runtime)
        dry_run = read_daily_quotes_normalized_small_range(
            runtime_dir=fixture_runtime,
            as_of_date="2026-06-07",
            lookback_business_days=5,
            max_codes=2,
            max_rows=20,
        )
        skipped = read_daily_quotes_normalized_small_range(runtime_dir=Path(missing_tmp) / "runtime", as_of_date="2026-06-01")
        script = subprocess.run(
            [
                sys.executable,
                "scripts/check_candidate_real_normalized_dry_run.py",
                "--runtime-dir",
                str(fixture_runtime),
                "--as-of-date",
                "2026-06-07",
                "--report-dir",
                str(fixture_runtime / "reports"),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    phase4e = build_candidate_features_mock_with_audit(build_mock_daily_quotes_normalized(), as_of_date="2026-06-01")
    report_text = (ROOT / "docs/phase_reports/phase4g_real_normalized_dry_run.md").read_text(encoding="utf-8") if (ROOT / "docs/phase_reports/phase4g_real_normalized_dry_run.md").is_file() else ""
    checks = {
        "required_input_docs_present": all(path.is_file() for path in REQUIRED_INPUT_DOCS),
        "phase4g_files_present": all(path.is_file() for path in REQUIRED_FILES),
        "normalized_data_reader_exists": callable(read_daily_quotes_normalized_small_range),
        "daily_quotes_normalized_discovery_implemented": discovery.status == "FOUND" and discovery.storage_format == "jsonl",
        "jsonl_or_parquet_supported": "jsonl" in (discovery.storage_format or "") or "parquet" in (discovery.storage_format or ""),
        "small_range_read_implemented": dry_run.status == "OK" and dry_run.filtered_row_count <= 20,
        "max_codes_and_max_rows_limit_scope": dry_run.code_count <= 2 and dry_run.input_row_count <= 20,
        "trading_calendar_window_helper_exists": callable(build_trading_calendar_window),
        "non_business_as_of_date_defined": dry_run.requested_as_of_date == "2026-06-07"
        and dry_run.normalized_as_of_date == "2026-06-05",
        "lookback_business_day_window_defined": dry_run.window_start_date == "2026-06-01",
        "phase4f_loader_contract_connected": bool(dry_run.manifest_path) and bool(dry_run.audit_path),
        "future_row_exclusion_recorded": dry_run.dropped_future_row_count >= 1,
        "dry_run_script_exists": script.returncode == 0 and "normalized_as_of_date" in script.stdout,
        "missing_data_skips_safely": skipped.status == "SKIPPED",
        "phase4e_mock_builder_compatible": phase4e.validation.is_valid and phase4e.audit.status == "OK",
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
    parser = argparse.ArgumentParser(description="Audit Phase4-G real normalized data dry-run.")
    parser.add_argument("--json-report", default="reports/phase_reports/phase4g_real_normalized_dry_run_audit.json")
    parser.add_argument("--markdown-report", default="docs/phase_reports/phase4g_real_normalized_dry_run_audit.md")
    args = parser.parse_args(argv)
    result = run_audit(Path(args.json_report), Path(args.markdown_report))
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def _prepare_fixture_runtime(runtime_dir: Path) -> None:
    paths = RuntimePaths(runtime_dir=runtime_dir)
    raw_records = [
        {"Date": "2026-06-01", "Code": "11110", "O": 10, "H": 12, "L": 9, "C": 11, "Vo": 100},
        {"Date": "2026-06-02", "Code": "11110", "O": 11, "H": 13, "L": 10, "C": 12, "Vo": 110},
        {"Date": "2026-06-03", "Code": "11110", "O": 12, "H": 14, "L": 11, "C": 13, "Vo": 120},
        {"Date": "2026-06-04", "Code": "11110", "O": 13, "H": 15, "L": 12, "C": 14, "Vo": 130},
        {"Date": "2026-06-05", "Code": "11110", "O": 14, "H": 16, "L": 13, "C": 15, "Vo": 140},
        {"Date": "2026-06-08", "Code": "11110", "O": 99, "H": 99, "L": 99, "C": 99, "Vo": 990},
        {"Date": "2026-06-05", "Code": "22220", "O": 20, "H": 22, "L": 19, "C": 21, "Vo": 200},
    ]
    normalized, _ = normalize_daily_quotes(raw_records)
    write_daily_quotes_normalized(paths, "jsonl", normalized)
    store = MarketDataStore(paths)
    store.save_raw(
        [
            {"Date": "2026-06-01", "HolDiv": "1"},
            {"Date": "2026-06-02", "HolDiv": "1"},
            {"Date": "2026-06-03", "HolDiv": "1"},
            {"Date": "2026-06-04", "HolDiv": "1"},
            {"Date": "2026-06-05", "HolDiv": "1"},
            {"Date": "2026-06-06", "HolDiv": "0"},
            {"Date": "2026-06-07", "HolDiv": "0"},
            {"Date": "2026-06-08", "HolDiv": "1"},
        ],
        endpoint="/v2/markets/calendar",
        collection="jquants/trading_calendar",
    )


def _non_implementation_boundary_present(report_text: str) -> bool:
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "src/ai_fund_lab_v2/candidate_ai/normalized_data_reader.py",
            ROOT / "src/ai_fund_lab_v2/candidate_ai/trading_calendar_window.py",
        )
    )
    blocked_source_terms = (
        "def train",
        "def predict",
        "def backtest",
        "def generate_labels",
        "submit_order",
        "place_order",
        "JQuantsClient",
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
        "# AI Fund Lab vNext Phase4-G Real Normalized Data Dry-run Audit",
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
            "Phase4-G connects small-range normalized raw discovery/read to the Candidate AI loader contract with a trading-calendar window.",
            "It keeps missing-data environments safe with SKIPPED status and does not implement full feature generation, labels, training, inference, backtest, trading, or ordering.",
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
