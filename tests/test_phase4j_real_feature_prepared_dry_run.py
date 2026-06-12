from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes, write_daily_quotes_normalized
from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.audit_phase4j_real_feature_prepared_dry_run import run_audit
from scripts.build_candidate_features_real_prepared_dry_run import (
    compute_per_code_lookback_stats,
    run_prepared_real_feature_dry_run,
    select_prepared_as_of_date,
)


def test_select_prepared_as_of_date_prefers_latest_sufficient_date() -> None:
    records = [{"Date": f"2026-01-{day:02d}", "Code": "11110"} for day in range(1, 25)]

    assert select_prepared_as_of_date(records, min_lookback_rows=21) == "2026-01-24"


def test_per_code_lookback_stats() -> None:
    rows = [{"code": "11110"} for _ in range(21)] + [{"code": "22220"} for _ in range(3)]

    stats = compute_per_code_lookback_stats(rows, min_lookback_rows=21)

    assert stats["per_code_row_count_min"] == 3
    assert stats["per_code_row_count_max"] == 21
    assert stats["codes_with_sufficient_lookback"] == 1
    assert stats["codes_with_insufficient_lookback"] == 1


def test_prepared_dry_run_ready_with_sufficient_fixture(tmp_path: Path) -> None:
    runtime_dir = prepare_runtime(tmp_path)

    summary = run_prepared_real_feature_dry_run(
        runtime_dir=runtime_dir,
        lookback_business_days=60,
        max_codes=2,
        max_rows=120,
        report_dir=tmp_path / "reports",
    )

    assert summary["readiness_status"] == "READY_FOR_FULL_RANGE_FEATURE_DRY_RUN"
    assert summary["eligible_count"] > 0
    assert summary["schema_validation_status"] == "OK"
    assert summary["leakage_audit_status"] == "OK"
    assert summary["per_code_row_count_min"] >= 60
    assert Path(summary["features_path"]).is_file()
    assert Path(summary["manifest_path"]).is_file()
    assert Path(summary["audit_path"]).is_file()
    assert Path(summary["summary_path"]).is_file()


def test_prepared_dry_run_blocks_when_data_window_is_short(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    paths = RuntimePaths(runtime_dir=runtime_dir)
    normalized, _ = normalize_daily_quotes(
        [{"Date": "2026-06-01", "Code": "11110", "O": 1, "H": 2, "L": 1, "C": 2, "Vo": 100}]
    )
    write_daily_quotes_normalized(paths, "jsonl", normalized)

    summary = run_prepared_real_feature_dry_run(runtime_dir=runtime_dir, report_dir=tmp_path / "reports")

    assert summary["readiness_status"] == "BLOCKED_BY_DATA_WINDOW"
    assert summary["eligible_count"] == 0


def test_phase4j_audit_completes_and_writes_reports(tmp_path: Path) -> None:
    result = run_audit(
        json_report_path=tmp_path / "phase4j.json",
        markdown_report_path=tmp_path / "phase4j.md",
    )

    assert result["status"] == "complete"
    assert result["checks"]["as_of_date_auto_selection_exists"]
    assert result["checks"]["per_code_lookback_check_exists"]
    assert Path(tmp_path / "phase4j.json").is_file()
    assert Path(tmp_path / "phase4j.md").is_file()


def test_prepared_dry_run_outputs_have_no_sensitive_values(tmp_path: Path) -> None:
    runtime_dir = prepare_runtime(tmp_path)
    summary = run_prepared_real_feature_dry_run(runtime_dir=runtime_dir, report_dir=tmp_path / "reports")
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
    for day in range(1, 91):
        date = f"2026-03-{day:02d}" if day <= 31 else f"2026-04-{day - 31:02d}" if day <= 61 else f"2026-05-{day - 61:02d}"
        raw_records.append({"Date": date, "Code": "11110", "O": 100 + day, "H": 104 + day, "L": 99 + day, "C": 102 + day, "Vo": 1000 + day})
        raw_records.append({"Date": date, "Code": "22220", "O": 20 + day, "H": 24 + day, "L": 19 + day, "C": 22 + day, "Vo": 200 + day})
    normalized, _ = normalize_daily_quotes(raw_records)
    write_daily_quotes_normalized(paths, "jsonl", normalized)
    MarketDataStore(paths).save_raw(
        [{"Date": record["Date"], "HolDiv": "1"} for record in normalized],
        endpoint="/v2/markets/calendar",
        collection="jquants/trading_calendar",
    )
    return runtime_dir
