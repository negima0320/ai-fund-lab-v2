from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.position_management_ai.calibration import (
    READY_FOR_PHASE6F_POLICY_REVIEW,
    run_phase6e_baseline_calibration,
)
from ai_fund_lab_v2.position_management_ai.label_dataset import run_phase6c_position_label_dataset_dry_run


def test_phase6e_calibrated_baseline_runs(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.summary["readiness_status"] == READY_FOR_PHASE6F_POLICY_REVIEW
    assert result.summary["row_count"] > 0
    assert not result.alignment.empty


def test_phase6e_forbidden_and_leakage_audit_ok(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.audit["forbidden_feature_audit_status"] == "OK"
    assert result.audit["leakage_audit_status"] == "OK"
    assert result.audit["feature_audit"]["forbidden_feature_column_count"] == 0
    assert result.audit["label_audit"]["label_leakage_audit_status"] == "OK"


def test_phase6e_no_add_on_loss_position(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.audit["add_loss_position_count"] == 0
    assert result.comparison["calibrated_add_loss_position_count"] == 0


def test_phase6e_add_does_not_overlap_exit_label(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.audit["add_exit_label_overlap_count"] == 0
    assert result.comparison["calibrated_add_exit_label_overlap_count"] == 0


def test_phase6e_old_vs_calibrated_comparison_is_available(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert "old_mismatch_count" in result.comparison
    assert "calibrated_mismatch_count" in result.comparison
    assert result.comparison["calibrated_mismatch_count"] <= result.comparison["old_mismatch_count"]
    assert (tmp_path / "comparison.json").is_file()


def test_phase6e_continue_winner_wrong_exit_does_not_increase(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.comparison["calibrated_exit_continue_winner_count"] <= result.comparison["old_exit_continue_winner_count"]


def _run(tmp_path: Path):
    dataset_path = tmp_path / "phase6c_dataset.csv"
    run_phase6c_position_label_dataset_dry_run(
        output_csv_path=dataset_path,
        output_json_path=tmp_path / "phase6c_dataset.json",
        audit_path=tmp_path / "phase6c_audit.json",
        created_at="2026-06-14T00:00:00+00:00",
    )
    return run_phase6e_baseline_calibration(
        dataset_path=dataset_path,
        alignment_csv_path=tmp_path / "alignment.csv",
        alignment_json_path=tmp_path / "alignment.json",
        mismatch_csv_path=tmp_path / "mismatches.csv",
        audit_path=tmp_path / "audit.json",
        comparison_path=tmp_path / "comparison.json",
        created_at="2026-06-14T00:00:00+00:00",
    )
