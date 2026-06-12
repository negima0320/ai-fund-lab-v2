from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase4i_real_feature_readiness import run_audit


def write_phase4h_outputs(base: Path, *, eligible_count: int = 0) -> tuple[Path, Path, Path, Path]:
    feature_path = base / "features.json"
    manifest_path = base / "manifest.json"
    audit_path = base / "audit.json"
    summary_path = base / "summary.json"
    rows = [
        {
            "as_of_date": "2026-06-01",
            "target_date": "2026-06-01",
            "code": "11110",
            "feature_version": "candidate_features_mock_v1",
            "source_snapshot_id": "real_normalized_dry_run:2026-06-01",
            "universe_eligible": eligible_count > 0,
            "excluded_reason": "" if eligible_count > 0 else "insufficient_lookback",
            "data_start_date": "2026-06-01",
            "data_end_date": "2026-06-01",
            "price_momentum_return_5d": None,
            "price_momentum_return_20d": None,
            "volume_momentum_ratio_5d": None,
            "volatility_return_std_20d": None,
            "trend_close_over_ma_20d": None,
            "liquidity_avg_volume_20d": None,
            "missing_flags_insufficient_lookback": eligible_count == 0,
        }
    ]
    payloads = {
        feature_path: {"rows": rows},
        manifest_path: {
            "row_count": 1,
            "eligible_count": eligible_count,
            "excluded_count": 1 - eligible_count,
            "storage_format": "jsonl",
            "normalized_as_of_date": "2026-06-01",
            "window_start_date": "2026-06-01",
            "lookback_business_days": 60,
            "max_codes": 1,
            "max_rows": 60,
            "dropped_future_row_count": 0,
        },
        audit_path: {
            "status": "OK",
            "row_count": 1,
            "eligible_count": eligible_count,
            "excluded_count": 1 - eligible_count,
            "excluded_reason_counts": {} if eligible_count > 0 else {"insufficient_lookback": 1},
            "dropped_future_row_count": 0,
        },
        summary_path: {
            "status": "OK",
            "schema_validation_status": "OK",
            "leakage_audit_status": "OK",
            "storage_format": "jsonl",
            "normalized_as_of_date": "2026-06-01",
            "window_start_date": "2026-06-01",
        },
    }
    for path, payload in payloads.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    return feature_path, manifest_path, audit_path, summary_path


def test_phase4i_audit_detects_blocked_by_data_window(tmp_path: Path) -> None:
    feature_path, manifest_path, audit_path, summary_path = write_phase4h_outputs(tmp_path)

    result = run_audit(
        feature_path=feature_path,
        manifest_path=manifest_path,
        audit_path=audit_path,
        summary_path=summary_path,
        json_report_path=tmp_path / "phase4i.json",
        markdown_report_path=tmp_path / "phase4i.md",
    )

    assert result["status"] == "complete"
    assert result["readiness_status"] == "BLOCKED_BY_DATA_WINDOW"
    assert result["review"]["eligible_count"] == 0
    assert result["review"]["excluded_reason_counts"] == {"insufficient_lookback": 1}


def test_phase4i_audit_skips_safely_when_outputs_missing(tmp_path: Path) -> None:
    result = run_audit(
        feature_path=tmp_path / "missing_features.json",
        manifest_path=tmp_path / "missing_manifest.json",
        audit_path=tmp_path / "missing_audit.json",
        summary_path=tmp_path / "missing_summary.json",
        json_report_path=tmp_path / "phase4i.json",
        markdown_report_path=tmp_path / "phase4i.md",
    )

    assert result["status"] == "skipped"
    assert result["readiness_status"] == "SKIPPED"


def test_phase4i_audit_reads_schema_and_leakage_ok(tmp_path: Path) -> None:
    feature_path, manifest_path, audit_path, summary_path = write_phase4h_outputs(tmp_path)

    result = run_audit(
        feature_path=feature_path,
        manifest_path=manifest_path,
        audit_path=audit_path,
        summary_path=summary_path,
        json_report_path=tmp_path / "phase4i.json",
        markdown_report_path=tmp_path / "phase4i.md",
    )

    assert result["review"]["schema_validation_status"] == "OK"
    assert result["review"]["leakage_audit_status"] == "OK"


def test_phase4i_audit_has_required_keys(tmp_path: Path) -> None:
    feature_path, manifest_path, audit_path, summary_path = write_phase4h_outputs(tmp_path)

    result = run_audit(
        feature_path=feature_path,
        manifest_path=manifest_path,
        audit_path=audit_path,
        summary_path=summary_path,
        json_report_path=tmp_path / "phase4i.json",
        markdown_report_path=tmp_path / "phase4i.md",
    )

    assert {"phase", "status", "readiness_status", "review", "cause_analysis", "next_actions", "checks"}.issubset(result)
    assert Path(tmp_path / "phase4i.json").is_file()
    assert Path(tmp_path / "phase4i.md").is_file()


def test_phase4i_audit_can_report_ready_when_eligible_exists(tmp_path: Path) -> None:
    feature_path, manifest_path, audit_path, summary_path = write_phase4h_outputs(tmp_path, eligible_count=1)

    result = run_audit(
        feature_path=feature_path,
        manifest_path=manifest_path,
        audit_path=audit_path,
        summary_path=summary_path,
        json_report_path=tmp_path / "phase4i.json",
        markdown_report_path=tmp_path / "phase4i.md",
    )

    assert result["readiness_status"] == "READY_FOR_FULL_RANGE_FEATURE_DRY_RUN"


def test_phase4i_audit_confirms_forbidden_scope_absent(tmp_path: Path) -> None:
    feature_path, manifest_path, audit_path, summary_path = write_phase4h_outputs(tmp_path)

    result = run_audit(
        feature_path=feature_path,
        manifest_path=manifest_path,
        audit_path=audit_path,
        summary_path=summary_path,
        json_report_path=tmp_path / "phase4i.json",
        markdown_report_path=tmp_path / "phase4i.md",
    )

    assert result["checks"]["forbidden_implementation_absent"]
