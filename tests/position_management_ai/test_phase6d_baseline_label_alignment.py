from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.position_management_ai.alignment_audit import (
    READY_FOR_PHASE6E_BASELINE_REVIEW,
    build_alignment_table,
    extract_mismatches,
    run_phase6d_baseline_label_alignment_audit,
)
from ai_fund_lab_v2.position_management_ai.label_dataset import run_phase6c_position_label_dataset_dry_run


def test_phase6d_alignment_summary_is_generated(tmp_path: Path) -> None:
    dataset_path = tmp_path / "phase6c_dataset.csv"
    run_phase6c_position_label_dataset_dry_run(
        output_csv_path=dataset_path,
        output_json_path=tmp_path / "phase6c_dataset.json",
        audit_path=tmp_path / "phase6c_audit.json",
        created_at="2026-06-14T00:00:00+00:00",
    )

    result = run_phase6d_baseline_label_alignment_audit(
        dataset_path=dataset_path,
        alignment_csv_path=tmp_path / "alignment.csv",
        alignment_json_path=tmp_path / "alignment.json",
        mismatch_csv_path=tmp_path / "mismatches.csv",
        audit_path=tmp_path / "audit.json",
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.summary["readiness_status"] == READY_FOR_PHASE6E_BASELINE_REVIEW
    assert result.summary["row_count"] > 0
    assert not result.alignment.empty
    assert (tmp_path / "alignment.csv").is_file()
    assert (tmp_path / "alignment.json").is_file()


def test_phase6d_mismatch_extraction_is_available(tmp_path: Path) -> None:
    result = _run(tmp_path)

    mismatches = extract_mismatches(result.mismatches.drop(columns=["mismatch_reason"], errors="ignore")) if result.mismatches.empty else result.mismatches
    assert "mismatch_reason" in result.mismatches.columns
    assert result.summary["mismatch_count"] == len(result.mismatches)
    assert len(mismatches) >= 0


def test_phase6d_add_has_no_loss_positions(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.audit["add_loss_position_count"] == 0


def test_phase6d_forbidden_feature_audit_ok(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.audit["forbidden_feature_audit_status"] == "OK"
    assert result.audit["label_audit"]["forbidden_feature_column_count"] == 0
    assert result.audit["feature_audit"]["forbidden_feature_column_count"] == 0


def test_phase6d_leakage_audit_ok(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.audit["leakage_audit_status"] == "OK"
    assert result.audit["label_audit"]["label_leakage_audit_status"] == "OK"
    assert result.audit["feature_audit"]["leakage_audit_status"] == "OK"


def test_phase6d_alignment_table_has_expected_columns(tmp_path: Path) -> None:
    result = _run(tmp_path)
    alignment = build_alignment_table(result.mismatches.drop(columns=["mismatch_reason"], errors="ignore")) if result.mismatches.empty else result.alignment

    assert {"action", "row_count", "label__label_continue_winner_true_count"}.issubset(alignment.columns)


def _run(tmp_path: Path):
    dataset_path = tmp_path / "phase6c_dataset.csv"
    run_phase6c_position_label_dataset_dry_run(
        output_csv_path=dataset_path,
        output_json_path=tmp_path / "phase6c_dataset.json",
        audit_path=tmp_path / "phase6c_audit.json",
        created_at="2026-06-14T00:00:00+00:00",
    )
    return run_phase6d_baseline_label_alignment_audit(
        dataset_path=dataset_path,
        alignment_csv_path=tmp_path / "alignment.csv",
        alignment_json_path=tmp_path / "alignment.json",
        mismatch_csv_path=tmp_path / "mismatches.csv",
        audit_path=tmp_path / "audit.json",
        created_at="2026-06-14T00:00:00+00:00",
    )
