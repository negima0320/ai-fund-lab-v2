from __future__ import annotations

from pathlib import Path

import pytest

from ai_fund_lab_v2.position_management_ai.historical_validation import run_phase6h_historical_validation


@pytest.fixture(scope="module")
def phase6h_result(tmp_path_factory: pytest.TempPathFactory):
    tmp_path = tmp_path_factory.mktemp("phase6h")
    return run_phase6h_historical_validation(
        output_csv_path=tmp_path / "validation.csv",
        output_json_path=tmp_path / "validation.json",
        comparison_path=tmp_path / "comparison.json",
        action_stats_path=tmp_path / "actions.json",
        validation_year=2025,
        max_target_dates=6,
        top_n=5,
        created_at="2026-06-14T00:00:00+00:00",
    )


def test_phase6h_validation_runs_successfully(phase6h_result) -> None:
    assert phase6h_result.summary["status"] == "OK"
    assert phase6h_result.summary["row_count"] > 0
    assert phase6h_result.summary["completion_status"] in {
        "PHASE6_VALIDATED",
        "PHASE6_IMPLEMENTED_BUT_NOT_VALIDATED",
    }


def test_phase6h_comparison_is_generated(phase6h_result) -> None:
    comparison = phase6h_result.comparison

    assert "baseline" in comparison
    assert "position_managed" in comparison
    assert "profit_retention_rate" in comparison["baseline"]
    assert "profit_retention_rate" in comparison["position_managed"]
    assert "winner_to_loser_rate" in comparison["baseline"]
    assert "winner_to_loser_rate" in comparison["position_managed"]


def test_phase6h_action_statistics_are_generated(phase6h_result) -> None:
    action_stats = phase6h_result.action_statistics

    assert "checkpoint_action_counts" in action_stats
    assert "terminal_action_counts" in action_stats
    assert {"HOLD_count", "EXIT_count", "ADD_count", "REDUCE_count"}.issubset(action_stats)


def test_phase6h_audit_ok(phase6h_result) -> None:
    audit = phase6h_result.summary["audit"]

    assert audit["forbidden_feature_audit_status"] == "OK"
    assert audit["leakage_audit_status"] == "OK"
    assert audit["feature_label_separation_status"] == "OK"
    assert audit["add_safety_status"] == "OK"
    assert audit["broker_api_executed"] is False
    assert audit["order_executed"] is False
    assert audit["paper_trading_executed"] is False
    assert audit["capital_allocation_executed"] is False


def test_phase6h_outputs_are_generated(tmp_path: Path) -> None:
    run_phase6h_historical_validation(
        output_csv_path=tmp_path / "validation.csv",
        output_json_path=tmp_path / "validation.json",
        comparison_path=tmp_path / "comparison.json",
        action_stats_path=tmp_path / "actions.json",
        validation_year=2025,
        max_target_dates=3,
        top_n=5,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert (tmp_path / "validation.csv").is_file()
    assert (tmp_path / "validation.json").is_file()
    assert (tmp_path / "comparison.json").is_file()
    assert (tmp_path / "actions.json").is_file()
