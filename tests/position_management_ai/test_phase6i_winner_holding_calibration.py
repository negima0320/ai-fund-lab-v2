from __future__ import annotations

from pathlib import Path

import pytest

from ai_fund_lab_v2.position_management_ai.winner_holding_calibration import (
    PHASE6_VALIDATED_FOR_RISK_NOT_WINNER_HOLDING,
    PHASE6_VALIDATED_WITH_WINNER_HOLDING_IMPROVEMENT,
    run_phase6i_winner_holding_calibration,
)


@pytest.fixture(scope="module")
def phase6i_result(tmp_path_factory: pytest.TempPathFactory):
    tmp_path = tmp_path_factory.mktemp("phase6i")
    return run_phase6i_winner_holding_calibration(
        output_csv_path=tmp_path / "calibration.csv",
        output_json_path=tmp_path / "calibration.json",
        comparison_path=tmp_path / "comparison.json",
        action_stats_path=tmp_path / "actions.json",
        mismatch_path=tmp_path / "mismatches.csv",
        validation_year=2025,
        max_target_dates=6,
        top_n=5,
        created_at="2026-06-14T00:00:00+00:00",
    )


def test_phase6i_winner_holding_calibration_runs(phase6i_result) -> None:
    assert phase6i_result.summary["status"] == "OK"
    assert phase6i_result.summary["completion_status"] in {
        PHASE6_VALIDATED_WITH_WINNER_HOLDING_IMPROVEMENT,
        PHASE6_VALIDATED_FOR_RISK_NOT_WINNER_HOLDING,
    }
    assert phase6i_result.summary["row_count"] > 0


def test_phase6i_old_vs_new_comparison_is_generated(phase6i_result) -> None:
    comparison = phase6i_result.comparison

    assert "old_position_metrics" in comparison
    assert "winner_holding_position_metrics" in comparison
    assert "metric_delta_new_minus_old" in comparison
    assert comparison["capture_rate_improved"] or comparison["over_reduce_decreased"]


def test_phase6i_continue_winner_capture_improves_or_reports_reason(phase6i_result) -> None:
    comparison = phase6i_result.comparison

    if phase6i_result.summary["completion_status"] == PHASE6_VALIDATED_WITH_WINNER_HOLDING_IMPROVEMENT:
        assert comparison["capture_rate_improved"] or comparison["over_reduce_decreased"]
    else:
        assert phase6i_result.summary["completion_status"] == PHASE6_VALIDATED_FOR_RISK_NOT_WINNER_HOLDING


def test_phase6i_continue_winner_wrong_exit_does_not_increase(phase6i_result) -> None:
    comparison = phase6i_result.comparison

    assert comparison["false_exit_not_increased"] is True
    assert (
        comparison["winner_holding_continue_winner_false_exit_count"]
        <= comparison["old_continue_winner_false_exit_count"]
    )


def test_phase6i_add_safety_and_audits_ok(phase6i_result) -> None:
    audit = phase6i_result.summary["audit"]

    assert audit["add_loss_position_count"] == 0
    assert audit["add_exit_label_overlap_count"] == 0
    assert audit["forbidden_feature_audit_status"] == "OK"
    assert audit["leakage_audit_status"] == "OK"
    assert audit["broker_api_executed"] is False
    assert audit["order_executed"] is False
    assert audit["paper_trading_executed"] is False
    assert audit["capital_allocation_executed"] is False


def test_phase6i_output_files_are_generated(tmp_path: Path) -> None:
    run_phase6i_winner_holding_calibration(
        output_csv_path=tmp_path / "calibration.csv",
        output_json_path=tmp_path / "calibration.json",
        comparison_path=tmp_path / "comparison.json",
        action_stats_path=tmp_path / "actions.json",
        mismatch_path=tmp_path / "mismatches.csv",
        validation_year=2025,
        max_target_dates=3,
        top_n=5,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert (tmp_path / "calibration.csv").is_file()
    assert (tmp_path / "calibration.json").is_file()
    assert (tmp_path / "comparison.json").is_file()
    assert (tmp_path / "actions.json").is_file()
    assert (tmp_path / "mismatches.csv").is_file()
