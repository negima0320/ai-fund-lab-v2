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
from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes, write_daily_quotes_normalized  # noqa: E402
from ai_fund_lab_v2.data_store import MarketDataStore  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402
from scripts.build_candidate_features_real_prepared_dry_run import (  # noqa: E402
    DEFAULT_LOOKBACK_BUSINESS_DAYS,
    DEFAULT_MAX_CODES,
    DEFAULT_MAX_ROWS,
    run_prepared_real_feature_dry_run,
    select_prepared_as_of_date,
)


PHASE = "Phase4-J Candidate Feature Full-range Dry-run Preparation"
PYTEST_HINT = (
    "python3 scripts/build_candidate_features_real_prepared_dry_run.py && "
    "python3 scripts/audit_phase4j_real_feature_prepared_dry_run.py && "
    "python3 -m pytest tests/test_phase4j_real_feature_prepared_dry_run.py && "
    "python3 -m pytest -q"
)

REQUIRED_INPUT_DOCS = (
    ROOT / "docs/phase_reports/phase4h_real_feature_dry_run.md",
    ROOT / "docs/phase_reports/phase4i_real_feature_readiness.md",
    ROOT / "docs/phase_reports/phase4i_real_feature_readiness_audit.md",
    ROOT / "reports/phase_reports/phase4h_real_feature_dry_run_audit.json",
    ROOT / "reports/phase_reports/phase4i_real_feature_readiness_audit.json",
    ROOT / "reports/candidate_ai/phase4h_real_feature_dry_run_summary.json",
)

REQUIRED_FILES = (
    ROOT / "scripts/build_candidate_features_real_prepared_dry_run.py",
    ROOT / "scripts/audit_phase4j_real_feature_prepared_dry_run.py",
    ROOT / "docs/phase_reports/phase4j_real_feature_prepared_dry_run.md",
    ROOT / "tests/test_phase4j_real_feature_prepared_dry_run.py",
)


def run_audit(
    json_report_path: Path | str = "reports/phase_reports/phase4j_real_feature_prepared_dry_run_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase4j_real_feature_prepared_dry_run_audit.md",
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as fixture_tmp:
        fixture_runtime = Path(fixture_tmp) / "runtime"
        _prepare_fixture_runtime(fixture_runtime)
        fixture_summary = run_prepared_real_feature_dry_run(
            runtime_dir=fixture_runtime,
            lookback_business_days=60,
            max_codes=2,
            max_rows=120,
            report_dir=Path(fixture_tmp) / "reports",
        )
        script = subprocess.run(
            [
                sys.executable,
                "scripts/build_candidate_features_real_prepared_dry_run.py",
                "--runtime-dir",
                str(fixture_runtime),
                "--lookback-business-days",
                "60",
                "--max-codes",
                "2",
                "--max-rows",
                "120",
                "--report-dir",
                str(Path(fixture_tmp) / "script-reports"),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        fixture_outputs = {
            "manifest": bool(fixture_summary.get("manifest_path")) and Path(fixture_summary["manifest_path"]).is_file(),
            "audit": bool(fixture_summary.get("audit_path")) and Path(fixture_summary["audit_path"]).is_file(),
            "summary": bool(fixture_summary.get("summary_path")) and Path(fixture_summary["summary_path"]).is_file(),
        }
    real_summary = run_prepared_real_feature_dry_run(report_dir=ROOT / "reports/candidate_ai")
    report_text = (ROOT / "docs/phase_reports/phase4j_real_feature_prepared_dry_run.md").read_text(encoding="utf-8") if (ROOT / "docs/phase_reports/phase4j_real_feature_prepared_dry_run.md").is_file() else ""
    checks = {
        "required_input_docs_present": all(path.is_file() for path in REQUIRED_INPUT_DOCS),
        "phase4j_files_present": all(path.is_file() for path in REQUIRED_FILES),
        "prepared_dry_run_script_exists": (ROOT / "scripts/build_candidate_features_real_prepared_dry_run.py").is_file(),
        "as_of_date_auto_selection_exists": callable(select_prepared_as_of_date)
        and fixture_summary["selected_as_of_date"] == "2026-03-31",
        "lookback_business_days_at_least_60": fixture_summary["lookback_business_days"] >= 60,
        "max_rows_max_codes_limited": fixture_summary["max_codes"] == 2 and fixture_summary["max_rows"] == 120,
        "per_code_lookback_check_exists": fixture_summary["per_code_row_count_min"] >= 60
        and fixture_summary["codes_with_sufficient_lookback"] >= 1,
        "eligible_count_positive_or_blocked": fixture_summary["eligible_count"] > 0
        or real_summary["readiness_status"] == "BLOCKED_BY_DATA_WINDOW",
        "schema_validation_ok": fixture_summary["schema_validation_status"] == "OK",
        "leakage_audit_ok": fixture_summary["leakage_audit_status"] == "OK",
        "manifest_json_output": fixture_outputs["manifest"],
        "audit_json_output": fixture_outputs["audit"],
        "summary_json_output": fixture_outputs["summary"],
        "readiness_status_output": fixture_summary["readiness_status"] == "READY_FOR_FULL_RANGE_FEATURE_DRY_RUN"
        and real_summary["readiness_status"] in {"READY_FOR_FULL_RANGE_FEATURE_DRY_RUN", "BLOCKED_BY_DATA_WINDOW", "BLOCKED_BY_RUNTIME_OUTPUT"},
        "phase4h_i_compatible": (ROOT / "reports/phase_reports/phase4h_real_feature_dry_run_audit.json").is_file()
        and (ROOT / "reports/phase_reports/phase4i_real_feature_readiness_audit.json").is_file(),
        "non_implementation_boundary_present": _non_implementation_boundary_present(report_text),
        "dry_run_script_runs": script.returncode == 0 and "readiness_status" in script.stdout,
    }
    status = "complete" if all(checks.values()) else "incomplete"
    result = sanitize_mapping(
        {
            "phase": PHASE,
            "status": status,
            "checks": checks,
            "fixture_summary": fixture_summary,
            "real_runtime_summary": real_summary,
            "pytest_hint": PYTEST_HINT,
            "reports": {"json": str(json_report_path), "markdown": str(markdown_report_path)},
        }
    )
    _write_json(Path(json_report_path), result)
    _write_markdown(Path(markdown_report_path), result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase4-J prepared real feature dry-run.")
    parser.add_argument("--json-report", default="reports/phase_reports/phase4j_real_feature_prepared_dry_run_audit.json")
    parser.add_argument("--markdown-report", default="docs/phase_reports/phase4j_real_feature_prepared_dry_run_audit.md")
    args = parser.parse_args(argv)
    result = run_audit(Path(args.json_report), Path(args.markdown_report))
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def _prepare_fixture_runtime(runtime_dir: Path) -> None:
    paths = RuntimePaths(runtime_dir=runtime_dir)
    raw_records: list[dict[str, object]] = []
    for day in range(1, 91):
        date = _date_from_day(day)
        if date.endswith("-06") or date.endswith("-07"):
            continue
        raw_records.append({"Date": date, "Code": "11110", "O": 100 + day, "H": 104 + day, "L": 99 + day, "C": 102 + day, "Vo": 1000 + day})
        raw_records.append({"Date": date, "Code": "22220", "O": 20 + day, "H": 24 + day, "L": 19 + day, "C": 22 + day, "Vo": 200 + day})
    normalized, _ = normalize_daily_quotes(raw_records)
    write_daily_quotes_normalized(paths, "jsonl", normalized)
    MarketDataStore(paths).save_raw(_calendar_records(), endpoint="/v2/markets/calendar", collection="jquants/trading_calendar")


def _date_from_day(day: int) -> str:
    # Keep fixture deterministic without adding dateutil dependency.
    from datetime import date, timedelta

    return (date(2026, 1, 1) + timedelta(days=day - 1)).isoformat()


def _calendar_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for day in range(1, 91):
        value = _date_from_day(day)
        records.append({"Date": value, "HolDiv": "0" if value.endswith("-06") or value.endswith("-07") else "1"})
    return records


def _non_implementation_boundary_present(report_text: str) -> bool:
    source_text = (ROOT / "scripts/build_candidate_features_real_prepared_dry_run.py").read_text(encoding="utf-8")
    blocked_terms = (
        "def train",
        "def predict",
        "def backtest",
        "def generate_labels",
        "submit_order",
        "place_order",
        "JQuantsClient",
    )
    required_report_terms = (
        "label生成は実装しない",
        "学習は実装しない",
        "推論は実装しない",
        "backtestは実装しない",
        "発注は実装しない",
        "実データ全量feature生成は実装しない",
    )
    return all(term not in source_text for term in blocked_terms) and all(term in report_text for term in required_report_terms)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fixture = payload["fixture_summary"]
    real = payload["real_runtime_summary"]
    lines = [
        "# AI Fund Lab vNext Phase4-J Real Feature Prepared Dry-run Audit",
        "",
        "## Audit Result",
        "",
        f"- phase: `{payload['phase']}`",
        f"- status: `{payload['status']}`",
        "",
        "## Fixture Prepared Dry-run",
        "",
        f"- readiness_status: `{fixture['readiness_status']}`",
        f"- selected_as_of_date: `{fixture['selected_as_of_date']}`",
        f"- eligible_count: `{fixture['eligible_count']}`",
        f"- excluded_count: `{fixture['excluded_count']}`",
        f"- per_code_row_count_min: `{fixture['per_code_row_count_min']}`",
        f"- schema_validation_status: `{fixture['schema_validation_status']}`",
        f"- leakage_audit_status: `{fixture['leakage_audit_status']}`",
        "",
        "## Real Runtime Dry-run",
        "",
        f"- readiness_status: `{real['readiness_status']}`",
        f"- selected_as_of_date: `{real.get('selected_as_of_date')}`",
        f"- eligible_count: `{real['eligible_count']}`",
        f"- reason: `{real.get('reason', '')}`",
        "",
        "## Summary",
        "",
        "Phase4-J adds prepared dry-run conditions and per-code lookback checks. It does not implement labels, datasets, training, inference, backtest, trading, broker live access, ordering, or portfolio auto-update.",
        "",
        "## pytest",
        "",
        f"`{payload['pytest_hint']}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
