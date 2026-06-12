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
from ai_fund_lab_v2.candidate_ai import (  # noqa: E402
    build_candidate_features_mock_with_audit,
    build_mock_daily_quotes_normalized,
    read_daily_quotes_normalized_small_range,
)
from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes, write_daily_quotes_normalized  # noqa: E402
from ai_fund_lab_v2.data_store import MarketDataStore  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402
from scripts.build_candidate_features_real_dry_run import run_real_feature_dry_run  # noqa: E402


PHASE = "Phase4-H Real Feature Dry-run"
PYTEST_HINT = (
    "python3 scripts/build_candidate_features_real_dry_run.py && "
    "python3 scripts/audit_phase4h_real_feature_dry_run.py && "
    "python3 scripts/build_candidate_features_mock.py && "
    "python3 scripts/audit_phase4e_candidate_feature_builder_mock.py && "
    "python3 scripts/check_candidate_real_normalized_dry_run.py && "
    "python3 scripts/audit_phase4g_real_normalized_dry_run.py && "
    "python3 -m pytest tests/test_phase4h_real_feature_dry_run.py && "
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
    ROOT / "docs/phase_reports/phase4g_real_normalized_dry_run.md",
    ROOT / "reports/phase_reports/phase4a_candidate_ai_design_audit.json",
    ROOT / "reports/phase_reports/phase4b_candidate_training_data_design_audit.json",
    ROOT / "reports/phase_reports/phase4c_candidate_feature_builder_design_audit.json",
    ROOT / "reports/phase_reports/phase4d_candidate_feature_builder_skeleton_audit.json",
    ROOT / "reports/phase_reports/phase4e_candidate_feature_builder_mock_audit.json",
    ROOT / "reports/phase_reports/phase4f_candidate_real_data_loader_contract_audit.json",
    ROOT / "reports/phase_reports/phase4g_real_normalized_dry_run_audit.json",
)

REQUIRED_FILES = (
    ROOT / "scripts/build_candidate_features_real_dry_run.py",
    ROOT / "scripts/audit_phase4h_real_feature_dry_run.py",
    ROOT / "docs/phase_reports/phase4h_real_feature_dry_run.md",
    ROOT / "tests/test_phase4h_real_feature_dry_run.py",
)

EXPECTED_FEATURES = (
    "price_momentum_return_5d",
    "price_momentum_return_20d",
    "volume_momentum_ratio_5d",
    "volatility_return_std_20d",
    "trend_close_over_ma_20d",
    "liquidity_avg_volume_20d",
    "missing_flags_insufficient_lookback",
)


def run_audit(
    json_report_path: Path | str = "reports/phase_reports/phase4h_real_feature_dry_run_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase4h_real_feature_dry_run_audit.md",
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as fixture_tmp, tempfile.TemporaryDirectory() as missing_tmp:
        fixture_runtime = Path(fixture_tmp) / "runtime"
        _prepare_fixture_runtime(fixture_runtime)
        summary = run_real_feature_dry_run(
            runtime_dir=fixture_runtime,
            as_of_date="2026-06-07",
            lookback_business_days=21,
            max_codes=2,
            max_rows=80,
            report_dir=Path(fixture_tmp) / "reports",
        )
        skipped = run_real_feature_dry_run(runtime_dir=Path(missing_tmp) / "runtime", as_of_date="2026-06-01")
        script = subprocess.run(
            [
                sys.executable,
                "scripts/build_candidate_features_real_dry_run.py",
                "--runtime-dir",
                str(fixture_runtime),
                "--as-of-date",
                "2026-06-07",
                "--lookback-business-days",
                "21",
                "--max-codes",
                "2",
                "--max-rows",
                "80",
                "--report-dir",
                str(Path(fixture_tmp) / "script-reports"),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        feature_payload = _read_json(summary.get("features_path"))
        audit_payload = _read_json(summary.get("audit_path"))
        manifest_payload = _read_json(summary.get("manifest_path"))
        summary_payload = _read_json(summary.get("summary_path"))
    phase4e = build_candidate_features_mock_with_audit(build_mock_daily_quotes_normalized(), as_of_date="2026-06-01")
    phase4g = read_daily_quotes_normalized_small_range(runtime_dir=Path(tempfile.mkdtemp()) / "missing", as_of_date="2026-06-01")
    report_text = (ROOT / "docs/phase_reports/phase4h_real_feature_dry_run.md").read_text(encoding="utf-8") if (ROOT / "docs/phase_reports/phase4h_real_feature_dry_run.md").is_file() else ""
    checks = {
        "required_input_docs_present": all(path.is_file() for path in REQUIRED_INPUT_DOCS),
        "phase4h_files_present": all(path.is_file() for path in REQUIRED_FILES),
        "real_feature_dry_run_script_exists": (ROOT / "scripts/build_candidate_features_real_dry_run.py").is_file(),
        "reader_loader_feature_builder_connected": summary["status"] == "OK" and summary["feature_row_count"] > 0,
        "small_range_limits_exist": summary["input_row_count"] <= 80 and "max_codes" in manifest_payload and "max_rows" in manifest_payload,
        "max_codes_max_rows_exist": manifest_payload.get("max_codes") == 2 and manifest_payload.get("max_rows") == 80,
        "feature_table_output_or_skipped": bool(summary.get("features_path")) or skipped["status"] == "SKIPPED",
        "required_features_generated": _required_features_generated(feature_payload),
        "schema_validation_passes": summary["schema_validation_status"] == "OK",
        "leakage_audit_passes": summary["leakage_audit_status"] == "OK",
        "future_rows_not_used": _feature_rows_do_not_exceed_as_of(feature_payload, summary["normalized_as_of_date"]),
        "dropped_future_row_count_recorded": audit_payload.get("dropped_future_row_count", -1) >= 1
        and manifest_payload.get("dropped_future_row_count", -1) >= 1,
        "manifest_json_output": bool(manifest_payload) and manifest_payload.get("dropped_future_row_count", -1) >= 0,
        "audit_json_output": bool(audit_payload) and audit_payload.get("leakage_audit_status", audit_payload.get("status")) == "OK",
        "summary_json_output": bool(summary_payload) and summary_payload.get("status") == "OK",
        "skipped_safe_without_normalized_data": skipped["status"] == "SKIPPED",
        "dry_run_script_runs": script.returncode == 0 and "feature_row_count" in script.stdout,
        "phase4e_mock_builder_compatible": phase4e.validation.is_valid and phase4e.audit.status == "OK",
        "phase4g_normalized_dry_run_compatible": phase4g.status == "SKIPPED",
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
    parser = argparse.ArgumentParser(description="Audit Phase4-H real feature dry-run.")
    parser.add_argument("--json-report", default="reports/phase_reports/phase4h_real_feature_dry_run_audit.json")
    parser.add_argument("--markdown-report", default="docs/phase_reports/phase4h_real_feature_dry_run_audit.md")
    args = parser.parse_args(argv)
    result = run_audit(Path(args.json_report), Path(args.markdown_report))
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def _prepare_fixture_runtime(runtime_dir: Path) -> None:
    paths = RuntimePaths(runtime_dir=runtime_dir)
    raw_records: list[dict[str, object]] = []
    for day in range(1, 23):
        date = f"2026-06-{day:02d}"
        if day in {6, 7, 13, 14, 20, 21}:
            continue
        raw_records.append({"Date": date, "Code": "11110", "O": 100 + day, "H": 104 + day, "L": 99 + day, "C": 102 + day, "Vo": 1000 + day})
    raw_records.extend(
        [
            {"Date": "2026-06-08", "Code": "22220", "O": 20, "H": 22, "L": 19, "C": 21, "Vo": 200},
            {"Date": "2026-06-23", "Code": "11110", "O": 999, "H": 999, "L": 999, "C": 999, "Vo": 9999},
        ]
    )
    normalized, _ = normalize_daily_quotes(raw_records)
    write_daily_quotes_normalized(paths, "jsonl", normalized)
    store = MarketDataStore(paths)
    store.save_raw(_calendar_records(), endpoint="/v2/markets/calendar", collection="jquants/trading_calendar")


def _calendar_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for day in range(1, 24):
        date = f"2026-06-{day:02d}"
        hol_div = "0" if day in {6, 7, 13, 14, 20, 21} else "1"
        records.append({"Date": date, "HolDiv": hol_div})
    return records


def _required_features_generated(payload: dict[str, Any]) -> bool:
    rows = payload.get("rows") or []
    return bool(rows) and all(feature in rows[0] for feature in EXPECTED_FEATURES)


def _feature_rows_do_not_exceed_as_of(payload: dict[str, Any], as_of_date: str | None) -> bool:
    if not as_of_date:
        return False
    rows = payload.get("rows") or []
    return all(str(row.get("data_end_date")) <= as_of_date for row in rows if row.get("data_end_date"))


def _read_json(path_value: Any) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(str(path_value))
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _non_implementation_boundary_present(report_text: str) -> bool:
    source_text = (ROOT / "scripts/build_candidate_features_real_dry_run.py").read_text(encoding="utf-8")
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
        "label生成は実装しない",
        "学習は実装しない",
        "推論は実装しない",
        "backtestは実装しない",
        "発注は実装しない",
        "実データ全量feature生成は実装しない",
    )
    return all(term not in source_text for term in blocked_source_terms) and all(term in report_text for term in required_report_terms)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AI Fund Lab vNext Phase4-H Real Feature Dry-run Audit",
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
            "Phase4-H connects small-range real normalized reader output to the Candidate feature builder and writes feature, manifest, audit, and summary JSON.",
            "It does not implement labels, datasets, training, inference, backtest, trading, broker live access, ordering, or portfolio auto-update.",
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
