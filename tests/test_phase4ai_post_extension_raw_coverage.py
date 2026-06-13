from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase4ai_post_extension_raw_coverage import (
    BLOCKED_COVERAGE,
    BLOCKED_INTEGRITY,
    BLOCKED_SECRET,
    READY,
    build_post_extension_raw_coverage_summary,
    run_audit,
)


def test_phase4ai_ready_when_integrated_raw_has_60_non_empty_dates(tmp_path: Path) -> None:
    phase4ah, raw_root = _prepare_raw_fixture(tmp_path, dates=[f"2026-03-{day:02d}" for day in range(1, 61)])

    summary = build_post_extension_raw_coverage_summary(
        phase4ah_summary_path=phase4ah,
        raw_root=raw_root,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["fetched_non_empty_trading_day_count"] == 60
    assert summary["required_non_empty_trading_day_count"] == 60
    assert summary["coverage_sufficient_for_features"] is True
    assert summary["row_count"] == 120
    assert summary["code_count"] == 2
    assert summary["duplicate_date_code_count"] == 0
    assert summary["raw_schema_status"] == "OK"
    assert summary["manifest_consistency_status"] == "OK"
    assert summary["normalized_data_written"] is False
    assert summary["promotion_performed"] is False
    assert summary["reader_switch_performed"] is False


def test_phase4ai_blocks_coverage_gap(tmp_path: Path) -> None:
    phase4ah, raw_root = _prepare_raw_fixture(tmp_path, dates=["2026-03-02", "2026-03-03"])

    summary = build_post_extension_raw_coverage_summary(
        phase4ah_summary_path=phase4ah,
        raw_root=raw_root,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == BLOCKED_COVERAGE
    assert summary["coverage_sufficient_for_features"] is False
    assert summary["missing_non_empty_trading_day_count"] == 58


def test_phase4ai_blocks_raw_schema_error(tmp_path: Path) -> None:
    phase4ah, raw_root = _prepare_raw_fixture(tmp_path, dates=["2026-03-02"])
    response_path = raw_root / "responses" / "2026-03-02_page_001.json"
    response = json.loads(response_path.read_text(encoding="utf-8"))
    response["payload"]["data"][0].pop("Code")
    response_path.write_text(json.dumps(response), encoding="utf-8")

    summary = build_post_extension_raw_coverage_summary(
        phase4ah_summary_path=phase4ah,
        raw_root=raw_root,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["readiness_status"] == BLOCKED_INTEGRITY
    assert summary["raw_schema_status"] == "ERROR"


def test_phase4ai_blocks_manifest_mismatch(tmp_path: Path) -> None:
    phase4ah, raw_root = _prepare_raw_fixture(tmp_path, dates=["2026-03-02", "2026-03-03"])
    (raw_root / "responses" / "2026-03-03_page_001.json").unlink()

    summary = build_post_extension_raw_coverage_summary(
        phase4ah_summary_path=phase4ah,
        raw_root=raw_root,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["readiness_status"] == BLOCKED_INTEGRITY
    assert summary["manifest_consistency_status"] == "ERROR"


def test_phase4ai_detects_duplicate_date_code(tmp_path: Path) -> None:
    phase4ah, raw_root = _prepare_raw_fixture(tmp_path, dates=["2026-03-02"])
    response_path = raw_root / "responses" / "2026-03-02_page_001.json"
    response = json.loads(response_path.read_text(encoding="utf-8"))
    response["payload"]["data"].append(dict(response["payload"]["data"][0]))
    response_path.write_text(json.dumps(response), encoding="utf-8")

    summary = build_post_extension_raw_coverage_summary(
        phase4ah_summary_path=phase4ah,
        raw_root=raw_root,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["duplicate_date_code_count"] == 1


def test_phase4ai_blocks_secret_marker(tmp_path: Path) -> None:
    phase4ah, raw_root = _prepare_raw_fixture(tmp_path, dates=["2026-03-02"])
    manifest_path = raw_root / "request_manifests" / "2026-03-02.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["bad"] = "Authorization"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    summary = build_post_extension_raw_coverage_summary(
        phase4ah_summary_path=phase4ah,
        raw_root=raw_root,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["readiness_status"] == BLOCKED_SECRET
    assert summary["secret_value_detected_in_manifests"] is True


def test_phase4ai_audit_completes(tmp_path: Path) -> None:
    phase4ah, raw_root = _prepare_raw_fixture(tmp_path, dates=[f"2026-03-{day:02d}" for day in range(1, 61)])

    result = run_audit(
        phase4ah_summary_path=phase4ah,
        raw_root=raw_root,
        summary_path=tmp_path / "summary.json",
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "complete"
    assert result["readiness_status"] == READY
    assert (tmp_path / "audit.json").is_file()
    assert (tmp_path / "audit.md").is_file()


def test_phase4ai_report_documents_required_rules() -> None:
    report = Path("docs/phase_reports/phase4ai_post_extension_raw_coverage.md").read_text(encoding="utf-8")

    assert "READY_FOR_REAL_RUNTIME_NORMALIZED_REBUILD" in report
    assert "does not call APIs" in report
    assert "required_non_empty_trading_day_count = 60" in report
    assert "Phase4-AJ" in report


def _prepare_raw_fixture(tmp_path: Path, *, dates: list[str]) -> tuple[Path, Path]:
    raw_root = tmp_path / "runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    request_dir = raw_root / "request_manifests"
    response_dir = raw_root / "responses"
    request_dir.mkdir(parents=True)
    response_dir.mkdir(parents=True)
    phase4ah = tmp_path / "phase4ah.json"
    phase4ah.write_text(
        json.dumps({"readiness_status": "READY_FOR_POST_EXTENSION_RAW_COVERAGE_AUDIT"}),
        encoding="utf-8",
    )
    (raw_root / "manifest.json").write_text(
        json.dumps({"planned_request_count": len(dates), "completed_request_count": len(dates)}),
        encoding="utf-8",
    )
    for target_date in dates:
        (request_dir / f"{target_date}.json").write_text(
            json.dumps({"target_date": target_date, "status": "SUCCESS"}),
            encoding="utf-8",
        )
        (response_dir / f"{target_date}_page_001.json").write_text(
            json.dumps(
                {
                    "date": target_date,
                    "payload": {
                        "data": [
                            {"Date": target_date, "Code": "7203"},
                            {"Date": target_date, "Code": "6758"},
                        ]
                    },
                }
            ),
            encoding="utf-8",
        )
    return phase4ah, raw_root
