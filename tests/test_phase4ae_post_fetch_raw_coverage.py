from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase4ae_post_fetch_raw_coverage import (
    BLOCKED_COVERAGE,
    BLOCKED_MANIFEST_MISMATCH,
    BLOCKED_MISSING_AD,
    BLOCKED_SCHEMA,
    BLOCKED_SECRET,
    READY,
    build_raw_coverage_summary,
    run_audit,
)


def test_phase4ae_blocks_missing_phase4ad_summary(tmp_path: Path) -> None:
    summary = build_raw_coverage_summary(
        phase4ad_summary_path=tmp_path / "missing.json",
        raw_root=tmp_path / "raw",
        summary_path=tmp_path / "summary.json",
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == BLOCKED_MISSING_AD
    assert summary["normalized_data_written"] is False
    assert summary["promotion_performed"] is False


def test_phase4ae_detects_coverage_gap_and_empty_responses(tmp_path: Path) -> None:
    phase4ab, phase4ad, raw_root = _prepare_raw_fixture(tmp_path, dates=["2026-03-10", "2026-03-11"], empty_dates=["2026-03-11"])

    summary = build_raw_coverage_summary(
        phase4ab_summary_path=phase4ab,
        phase4ad_summary_path=phase4ad,
        raw_root=raw_root,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == BLOCKED_COVERAGE
    assert summary["coverage_sufficient_for_features"] is False
    assert summary["fetched_business_day_count"] == 1
    assert summary["empty_response_date_count"] == 1
    assert summary["empty_response_dates"] == ["2026-03-11"]
    assert summary["missing_requested_dates"] == ["2026-03-11"]
    assert summary["row_count"] == 2
    assert summary["code_count"] == 2
    assert summary["duplicate_date_code_count"] == 0
    assert summary["raw_schema_status"] == "OK"
    assert summary["manifest_consistency_status"] == "OK"
    assert summary["normalized_data_written"] is False
    assert summary["mock_path_written"] is False
    assert summary["isolated_normalized_path_written"] is False


def test_phase4ae_ready_when_coverage_sufficient(tmp_path: Path) -> None:
    dates = [f"2026-03-{day:02d}" for day in range(1, 61)]
    phase4ab, phase4ad, raw_root = _prepare_raw_fixture(tmp_path, dates=dates, empty_dates=[])

    summary = build_raw_coverage_summary(
        phase4ab_summary_path=phase4ab,
        phase4ad_summary_path=phase4ad,
        raw_root=raw_root,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["coverage_sufficient_for_features"] is True
    assert summary["fetched_business_day_count"] == 60


def test_phase4ae_detects_manifest_mismatch(tmp_path: Path) -> None:
    phase4ab, phase4ad, raw_root = _prepare_raw_fixture(tmp_path, dates=["2026-03-10", "2026-03-11"], empty_dates=[])
    (raw_root / "responses" / "2026-03-11_page_001.json").unlink()

    summary = build_raw_coverage_summary(
        phase4ab_summary_path=phase4ab,
        phase4ad_summary_path=phase4ad,
        raw_root=raw_root,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["readiness_status"] == BLOCKED_MANIFEST_MISMATCH
    assert summary["manifest_consistency_status"] == "ERROR"


def test_phase4ae_detects_raw_schema_error(tmp_path: Path) -> None:
    phase4ab, phase4ad, raw_root = _prepare_raw_fixture(tmp_path, dates=["2026-03-10"], empty_dates=[])
    response_path = raw_root / "responses" / "2026-03-10_page_001.json"
    response = json.loads(response_path.read_text(encoding="utf-8"))
    response["payload"]["data"][0].pop("Code")
    response_path.write_text(json.dumps(response), encoding="utf-8")

    summary = build_raw_coverage_summary(
        phase4ab_summary_path=phase4ab,
        phase4ad_summary_path=phase4ad,
        raw_root=raw_root,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["readiness_status"] == BLOCKED_SCHEMA
    assert summary["raw_schema_status"] == "ERROR"


def test_phase4ae_detects_duplicate_date_code(tmp_path: Path) -> None:
    phase4ab, phase4ad, raw_root = _prepare_raw_fixture(tmp_path, dates=["2026-03-10"], empty_dates=[])
    response_path = raw_root / "responses" / "2026-03-10_page_001.json"
    response = json.loads(response_path.read_text(encoding="utf-8"))
    response["payload"]["data"].append(dict(response["payload"]["data"][0]))
    response_path.write_text(json.dumps(response), encoding="utf-8")

    summary = build_raw_coverage_summary(
        phase4ab_summary_path=phase4ab,
        phase4ad_summary_path=phase4ad,
        raw_root=raw_root,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["duplicate_date_code_count"] == 1


def test_phase4ae_detects_secret_marker(tmp_path: Path) -> None:
    phase4ab, phase4ad, raw_root = _prepare_raw_fixture(tmp_path, dates=["2026-03-10"], empty_dates=[])
    manifest = json.loads((raw_root / "request_manifests" / "2026-03-10.json").read_text(encoding="utf-8"))
    manifest["bad"] = "Authorization"
    (raw_root / "request_manifests" / "2026-03-10.json").write_text(json.dumps(manifest), encoding="utf-8")

    summary = build_raw_coverage_summary(
        phase4ab_summary_path=phase4ab,
        phase4ad_summary_path=phase4ad,
        raw_root=raw_root,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["readiness_status"] == BLOCKED_SECRET
    assert summary["secret_value_detected_in_manifests"] is True


def test_phase4ae_audit_completes(tmp_path: Path) -> None:
    phase4ab, phase4ad, raw_root = _prepare_raw_fixture(tmp_path, dates=["2026-03-10", "2026-03-11"], empty_dates=["2026-03-11"])

    result = run_audit(
        phase4ab_summary_path=phase4ab,
        phase4ad_summary_path=phase4ad,
        raw_root=raw_root,
        summary_path=tmp_path / "summary.json",
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "complete"
    assert result["readiness_status"] == BLOCKED_COVERAGE
    assert (tmp_path / "audit.json").is_file()
    assert (tmp_path / "audit.md").is_file()


def test_phase4ae_report_documents_required_rules() -> None:
    report = Path("docs/phase_reports/phase4ae_post_fetch_raw_coverage.md").read_text(encoding="utf-8")

    assert "BLOCKED_BY_COVERAGE_GAP" in report
    assert "does not call J-Quants APIs" in report
    assert "coverage_sufficient_for_features = false" in report
    assert "Phase4-AF" in report


def _prepare_raw_fixture(tmp_path: Path, *, dates: list[str], empty_dates: list[str]):
    raw_root = tmp_path / "runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    (raw_root / "request_manifests").mkdir(parents=True)
    (raw_root / "responses").mkdir(parents=True)
    phase4ab = tmp_path / "phase4ab.json"
    phase4ad = tmp_path / "phase4ad.json"
    phase4ab.write_text(
        json.dumps({"target_business_day_list": dates, "required_business_day_count": 60}),
        encoding="utf-8",
    )
    phase4ad.write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_POST_FETCH_RAW_AUDIT",
                "planned_request_count": len(dates),
                "completed_request_count": len(dates),
                "succeeded_request_count": len(dates),
                "failed_request_count": 0,
                "skipped_request_count": 0,
                "pagination_request_count": 0,
                "target_start_date": dates[0],
                "target_end_date": dates[-1],
            }
        ),
        encoding="utf-8",
    )
    (raw_root / "manifest.json").write_text(
        json.dumps(
            {
                "planned_request_count": len(dates),
                "succeeded_request_count": len(dates),
                "failed_request_count": 0,
                "skipped_request_count": 0,
                "pagination_request_count": 0,
            }
        ),
        encoding="utf-8",
    )
    for target_date in dates:
        rows = [] if target_date in empty_dates else [
            {"Date": target_date, "Code": "7203"},
            {"Date": target_date, "Code": "6758"},
        ]
        (raw_root / "request_manifests" / f"{target_date}.json").write_text(
            json.dumps({"status": "SUCCESS", "target_date": target_date, "row_count": len(rows)}),
            encoding="utf-8",
        )
        (raw_root / "responses" / f"{target_date}_page_001.json").write_text(
            json.dumps({"date": target_date, "payload": {"data": rows}}),
            encoding="utf-8",
        )
    return phase4ab, phase4ad, raw_root
