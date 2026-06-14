from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.position_management_ai.realdata_dry_run import (
    DEFAULT_QUOTE_PATH,
    READY_FOR_PHASE6G_POLICY_EXPANSION,
    run_phase6f_realdata_position_dry_run,
)


def test_phase6f_realdata_dry_run_succeeds_small(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.audit["readiness_status"] == READY_FOR_PHASE6G_POLICY_EXPANSION
    assert result.audit["label_row_count"] > 0
    assert result.audit["feature_row_count"] > 0


def test_phase6f_output_files_are_generated(tmp_path: Path) -> None:
    _run(tmp_path)

    assert (tmp_path / "features.csv").is_file()
    assert (tmp_path / "labels.csv").is_file()
    assert (tmp_path / "alignment.csv").is_file()
    assert (tmp_path / "audit.json").is_file()


def test_phase6f_audit_ok(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.audit["forbidden_feature_audit_status"] == "OK"
    assert result.audit["leakage_audit_status"] == "OK"
    assert result.audit["feature_audit"]["forbidden_feature_column_count"] == 0
    assert result.audit["label_audit"]["label_leakage_audit_status"] == "OK"


def test_phase6f_no_add_on_loss(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.audit["add_loss_position_count"] == 0


def test_phase6f_no_continue_winner_wrong_exit(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.audit["exit_continue_winner_count"] == 0


def _run(tmp_path: Path):
    return run_phase6f_realdata_position_dry_run(
        quote_path=DEFAULT_QUOTE_PATH,
        feature_output_path=tmp_path / "features.csv",
        label_output_path=tmp_path / "labels.csv",
        alignment_output_path=tmp_path / "alignment.csv",
        audit_output_path=tmp_path / "audit.json",
        max_codes=8,
        max_target_dates=2,
        created_at="2026-06-14T00:00:00+00:00",
    )
