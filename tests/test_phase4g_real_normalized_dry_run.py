from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.candidate_ai import (
    build_candidate_features_mock_with_audit,
    build_mock_daily_quotes_normalized,
    build_trading_calendar_window,
    discover_daily_quotes_normalized,
    read_daily_quotes_normalized_small_range,
)
from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes, write_daily_quotes_normalized
from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.audit_phase4g_real_normalized_dry_run import run_audit


def test_discover_daily_quotes_normalized_jsonl(tmp_path: Path) -> None:
    runtime_dir = prepare_runtime(tmp_path)

    discovery = discover_daily_quotes_normalized(runtime_dir)

    assert discovery.status == "FOUND"
    assert discovery.storage_format == "jsonl"
    assert discovery.path is not None
    assert discovery.path.name == "data.jsonl"


def test_trading_calendar_window_normalizes_non_business_day() -> None:
    window = build_trading_calendar_window(
        as_of_date="2026-06-07",
        lookback_business_days=5,
        calendar_records=calendar_records(),
    )

    assert window.requested_as_of_date == "2026-06-07"
    assert window.normalized_as_of_date == "2026-06-05"
    assert window.window_start_date == "2026-06-01"
    assert window.as_of_date_was_normalized
    assert window.source == "trading_calendar_raw"


def test_trading_calendar_window_uses_weekday_fallback() -> None:
    window = build_trading_calendar_window(as_of_date="2026-06-07", lookback_business_days=3)

    assert window.normalized_as_of_date == "2026-06-05"
    assert window.business_days == ("2026-06-03", "2026-06-04", "2026-06-05")
    assert window.source == "weekday_fallback"


def test_real_normalized_small_range_dry_run_connects_loader_contract(tmp_path: Path) -> None:
    runtime_dir = prepare_runtime(tmp_path)

    result = read_daily_quotes_normalized_small_range(
        runtime_dir=runtime_dir,
        as_of_date="2026-06-07",
        lookback_business_days=5,
        max_codes=2,
        max_rows=20,
    )

    assert result.status == "OK"
    assert result.normalized_as_of_date == "2026-06-05"
    assert result.window_start_date == "2026-06-01"
    assert result.code_count <= 2
    assert result.input_row_count <= 20
    assert result.filtered_row_count <= 20
    assert result.dropped_future_row_count >= 1
    assert result.manifest_path and Path(result.manifest_path).is_file()
    assert result.audit_path and Path(result.audit_path).is_file()


def test_real_normalized_dry_run_skips_safely_without_data(tmp_path: Path) -> None:
    result = read_daily_quotes_normalized_small_range(runtime_dir=tmp_path / "missing-runtime", as_of_date="2026-06-01")

    assert result.status == "SKIPPED"
    assert "not found" in result.message
    assert result.audit_path and Path(result.audit_path).is_file()


def test_check_candidate_real_normalized_dry_run_script_runs(tmp_path: Path) -> None:
    runtime_dir = prepare_runtime(tmp_path)
    report_dir = tmp_path / "reports"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_candidate_real_normalized_dry_run.py",
            "--runtime-dir",
            str(runtime_dir),
            "--as-of-date",
            "2026-06-07",
            "--lookback-business-days",
            "5",
            "--max-codes",
            "2",
            "--max-rows",
            "20",
            "--report-dir",
            str(report_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(completed.stdout)

    assert summary["status"] == "OK"
    assert summary["normalized_as_of_date"] == "2026-06-05"
    assert summary["dropped_future_row_count"] >= 1
    assert Path(summary["report_path"]).is_file()


def test_phase4e_mock_builder_still_passes() -> None:
    result = build_candidate_features_mock_with_audit(build_mock_daily_quotes_normalized(), as_of_date="2026-06-01")

    assert result.validation.is_valid
    assert result.audit.status == "OK"


def test_phase4g_audit_completes_and_writes_reports(tmp_path: Path) -> None:
    json_report = tmp_path / "phase4g_audit.json"
    markdown_report = tmp_path / "phase4g_audit.md"

    result = run_audit(json_report_path=json_report, markdown_report_path=markdown_report)

    assert result["status"] == "complete"
    assert json_report.is_file()
    assert markdown_report.is_file()
    assert result["checks"]["small_range_read_implemented"]
    assert result["checks"]["missing_data_skips_safely"]


def test_phase4g_outputs_have_no_sensitive_values(tmp_path: Path) -> None:
    runtime_dir = prepare_runtime(tmp_path)
    result = read_daily_quotes_normalized_small_range(runtime_dir=runtime_dir, as_of_date="2026-06-07")
    combined = ""
    for path_value in (result.manifest_path, result.audit_path, result.rows_path):
        if path_value:
            combined += Path(path_value).read_text(encoding="utf-8")

    for forbidden in ["secret-auth-id", "secret-password", "secret-token", "secret-cookie", "https://example.invalid"]:
        assert forbidden not in combined


def prepare_runtime(tmp_path: Path) -> Path:
    runtime_dir = tmp_path / "runtime"
    paths = RuntimePaths(runtime_dir=runtime_dir)
    normalized, _ = normalize_daily_quotes(
        [
            {"Date": "2026-06-01", "Code": "11110", "O": 10, "H": 12, "L": 9, "C": 11, "Vo": 100},
            {"Date": "2026-06-02", "Code": "11110", "O": 11, "H": 13, "L": 10, "C": 12, "Vo": 110},
            {"Date": "2026-06-03", "Code": "11110", "O": 12, "H": 14, "L": 11, "C": 13, "Vo": 120},
            {"Date": "2026-06-04", "Code": "11110", "O": 13, "H": 15, "L": 12, "C": 14, "Vo": 130},
            {"Date": "2026-06-05", "Code": "11110", "O": 14, "H": 16, "L": 13, "C": 15, "Vo": 140},
            {"Date": "2026-06-08", "Code": "11110", "O": 99, "H": 99, "L": 99, "C": 99, "Vo": 990},
            {"Date": "2026-06-05", "Code": "22220", "O": 20, "H": 22, "L": 19, "C": 21, "Vo": 200},
        ]
    )
    write_daily_quotes_normalized(paths, "jsonl", normalized)
    store = MarketDataStore(paths)
    store.save_raw(calendar_records(), endpoint="/v2/markets/calendar", collection="jquants/trading_calendar")
    return runtime_dir


def calendar_records() -> list[dict[str, object]]:
    return [
        {"Date": "2026-06-01", "HolDiv": "1"},
        {"Date": "2026-06-02", "HolDiv": "1"},
        {"Date": "2026-06-03", "HolDiv": "1"},
        {"Date": "2026-06-04", "HolDiv": "1"},
        {"Date": "2026-06-05", "HolDiv": "1"},
        {"Date": "2026-06-06", "HolDiv": "0"},
        {"Date": "2026-06-07", "HolDiv": "0"},
        {"Date": "2026-06-08", "HolDiv": "1"},
    ]
