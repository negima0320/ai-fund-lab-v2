from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes, write_daily_quotes_normalized
from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.audit_phase4h_real_feature_dry_run import run_audit
from scripts.build_candidate_features_real_dry_run import run_real_feature_dry_run


EXPECTED_FEATURES = {
    "price_momentum_return_5d",
    "price_momentum_return_20d",
    "volume_momentum_ratio_5d",
    "volatility_return_std_20d",
    "trend_close_over_ma_20d",
    "liquidity_avg_volume_20d",
    "missing_flags_insufficient_lookback",
}


def test_real_feature_dry_run_builds_feature_outputs(tmp_path: Path) -> None:
    runtime_dir = prepare_runtime(tmp_path)

    summary = run_real_feature_dry_run(
        runtime_dir=runtime_dir,
        as_of_date="2026-06-30",
        lookback_business_days=21,
        max_codes=2,
        max_rows=80,
        report_dir=tmp_path / "reports",
    )

    assert summary["status"] == "OK"
    assert summary["feature_row_count"] == 2
    assert summary["schema_validation_status"] == "OK"
    assert summary["leakage_audit_status"] == "OK"
    assert Path(summary["features_path"]).is_file()
    assert Path(summary["manifest_path"]).is_file()
    assert Path(summary["audit_path"]).is_file()
    assert Path(summary["summary_path"]).is_file()


def test_real_feature_dry_run_outputs_required_features_and_exclusions(tmp_path: Path) -> None:
    runtime_dir = prepare_runtime(tmp_path)
    summary = run_real_feature_dry_run(
        runtime_dir=runtime_dir,
        as_of_date="2026-06-30",
        lookback_business_days=21,
        max_codes=2,
        max_rows=80,
        report_dir=tmp_path / "reports",
    )
    payload = json.loads(Path(summary["features_path"]).read_text(encoding="utf-8"))
    rows = payload["rows"]

    assert all(EXPECTED_FEATURES.issubset(row) for row in rows)
    assert any(row["universe_eligible"] is True for row in rows)
    assert any(row["excluded_reason"] == "insufficient_lookback" for row in rows)


def test_real_feature_dry_run_does_not_use_future_rows(tmp_path: Path) -> None:
    runtime_dir = prepare_runtime(tmp_path)
    summary = run_real_feature_dry_run(
        runtime_dir=runtime_dir,
        as_of_date="2026-06-30",
        lookback_business_days=21,
        max_codes=2,
        max_rows=80,
        report_dir=tmp_path / "reports",
    )
    payload = json.loads(Path(summary["features_path"]).read_text(encoding="utf-8"))

    assert summary["dropped_future_row_count"] >= 1
    assert all(row["data_end_date"] <= "2026-06-30" for row in payload["rows"])


def test_real_feature_manifest_and_audit_record_loader_metadata(tmp_path: Path) -> None:
    runtime_dir = prepare_runtime(tmp_path)
    summary = run_real_feature_dry_run(
        runtime_dir=runtime_dir,
        as_of_date="2026-06-30",
        lookback_business_days=21,
        max_codes=2,
        max_rows=80,
        report_dir=tmp_path / "reports",
    )
    manifest = json.loads(Path(summary["manifest_path"]).read_text(encoding="utf-8"))
    audit = json.loads(Path(summary["audit_path"]).read_text(encoding="utf-8"))

    assert manifest["dropped_future_row_count"] >= 1
    assert manifest["max_codes"] == 2
    assert manifest["max_rows"] == 80
    assert audit["dropped_future_row_count"] >= 1
    assert audit["loader_status"] == "OK"


def test_real_feature_dry_run_skips_safely_without_normalized_data(tmp_path: Path) -> None:
    summary = run_real_feature_dry_run(runtime_dir=tmp_path / "missing-runtime", report_dir=tmp_path / "reports")

    assert summary["status"] == "SKIPPED"
    assert summary["features_path"] is None
    assert Path(summary["summary_path"]).is_file()


def test_build_candidate_features_real_dry_run_script_runs(tmp_path: Path) -> None:
    runtime_dir = prepare_runtime(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/build_candidate_features_real_dry_run.py",
            "--runtime-dir",
            str(runtime_dir),
            "--as-of-date",
            "2026-06-30",
            "--lookback-business-days",
            "21",
            "--max-codes",
            "2",
            "--max-rows",
            "80",
            "--report-dir",
            str(tmp_path / "reports"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(completed.stdout)

    assert summary["status"] == "OK"
    assert summary["feature_row_count"] == 2
    assert Path(summary["features_path"]).is_file()


def test_phase4h_audit_completes_and_writes_reports(tmp_path: Path) -> None:
    json_report = tmp_path / "phase4h_audit.json"
    markdown_report = tmp_path / "phase4h_audit.md"

    result = run_audit(json_report_path=json_report, markdown_report_path=markdown_report)

    assert result["status"] == "complete"
    assert json_report.is_file()
    assert markdown_report.is_file()
    assert result["checks"]["reader_loader_feature_builder_connected"]
    assert result["checks"]["dropped_future_row_count_recorded"]


def test_phase4h_outputs_have_no_sensitive_values(tmp_path: Path) -> None:
    runtime_dir = prepare_runtime(tmp_path)
    summary = run_real_feature_dry_run(runtime_dir=runtime_dir, as_of_date="2026-06-30", report_dir=tmp_path / "reports")
    combined = ""
    for key in ("features_path", "manifest_path", "audit_path", "summary_path"):
        value = summary.get(key)
        if value:
            combined += Path(value).read_text(encoding="utf-8")

    for forbidden in ["secret-auth-id", "secret-password", "secret-token", "secret-cookie", "https://example.invalid"]:
        assert forbidden not in combined


def prepare_runtime(tmp_path: Path) -> Path:
    runtime_dir = tmp_path / "runtime"
    paths = RuntimePaths(runtime_dir=runtime_dir)
    raw_records: list[dict[str, object]] = []
    for day in range(1, 31):
        if day in {6, 7, 13, 14, 20, 21, 27, 28}:
            continue
        raw_records.append(
            {
                "Date": f"2026-06-{day:02d}",
                "Code": "11110",
                "O": 100 + day,
                "H": 104 + day,
                "L": 99 + day,
                "C": 102 + day,
                "Vo": 1000 + day,
            }
        )
    raw_records.extend(
        [
            {"Date": "2026-06-30", "Code": "22220", "O": 20, "H": 22, "L": 19, "C": 21, "Vo": 200},
            {"Date": "2026-07-01", "Code": "11110", "O": 999, "H": 999, "L": 999, "C": 999, "Vo": 9999},
        ]
    )
    normalized, _ = normalize_daily_quotes(raw_records)
    write_daily_quotes_normalized(paths, "jsonl", normalized)
    MarketDataStore(paths).save_raw(calendar_records(), endpoint="/v2/markets/calendar", collection="jquants/trading_calendar")
    return runtime_dir


def calendar_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for day in range(1, 31):
        records.append({"Date": f"2026-06-{day:02d}", "HolDiv": "0" if day in {6, 7, 13, 14, 20, 21, 27, 28} else "1"})
    records.append({"Date": "2026-07-01", "HolDiv": "1"})
    return records
