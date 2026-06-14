from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.position_management_ai.danger_only_exit_validation import (
    run_phase6n_danger_only_exit_validation,
)


@pytest.fixture(scope="module")
def phase6n_result(tmp_path_factory: pytest.TempPathFactory):
    tmp_path = tmp_path_factory.mktemp("phase6n")
    return run_phase6n_danger_only_exit_validation(
        output_csv_path=tmp_path / "validation.csv",
        output_json_path=tmp_path / "validation.json",
        summary_path=tmp_path / "summary.json",
        yearly_summary_path=tmp_path / "yearly.json",
        action_stats_path=tmp_path / "actions.json",
        seed=42,
        dates_per_year=5,
        created_at="2026-06-14T00:00:00+00:00",
    )


def test_phase6n_reuses_phase6m_target_dates(phase6n_result) -> None:
    selected = phase6n_result.summary["selected_target_dates"]

    assert selected == {
        "2021": ["2021-09-15", "2021-10-05", "2021-10-25", "2021-10-28", "2021-11-04"],
        "2022": ["2022-02-10", "2022-03-03", "2022-10-27", "2022-11-18", "2022-11-21"],
        "2023": ["2023-01-17", "2023-02-06", "2023-07-04", "2023-09-04", "2023-09-21"],
        "2024": ["2024-01-17", "2024-02-08", "2024-04-02", "2024-04-08", "2024-07-19"],
        "2025": ["2025-01-15", "2025-03-21", "2025-08-28", "2025-10-03", "2025-11-20"],
        "2026": ["2026-01-16", "2026-03-02", "2026-03-11", "2026-04-07", "2026-04-14"],
    }


def test_phase6n_validates_top3_only(phase6n_result) -> None:
    trades = phase6n_result.trades

    assert len(trades) == 90
    assert trades["buy_rank"].max() == 3
    assert trades.groupby("year")["target_date"].nunique().eq(5).all()


def test_phase6n_fixed_current_danger_comparison_is_generated(phase6n_result) -> None:
    comparison = phase6n_result.comparison

    assert set(comparison).issuperset({"Fixed_20bd", "Current_Position_Managed", "Danger_Only_Exit"})
    assert comparison["Fixed_20bd"]["count"] == 90
    assert comparison["Current_Position_Managed"]["count"] == 90
    assert comparison["Danger_Only_Exit"]["count"] == 90
    assert "danger_vs_fixed_20bd" in comparison
    assert "danger_vs_current_position" in comparison


def test_phase6n_reduce_and_add_are_not_actual_actions(phase6n_result) -> None:
    stats = phase6n_result.action_statistics["danger_only_exit"]

    assert stats["actual_exit_count"] + stats["actual_hold_count"] == 90
    assert phase6n_result.summary["audit"]["danger_actual_reduce_count"] == 0
    assert phase6n_result.summary["audit"]["danger_actual_add_count"] == 0


def test_phase6n_danger_exit_condition_is_applied(phase6n_result) -> None:
    stats = phase6n_result.action_statistics["danger_only_exit"]

    assert phase6n_result.summary["audit"]["danger_condition_applied"] is True
    assert stats["actual_exit_count"] > 0
    assert phase6n_result.trades["max_danger_score"].max() >= 2


def test_phase6n_audit_ok_and_future_not_used_for_inference(phase6n_result) -> None:
    audit = phase6n_result.summary["audit"]

    assert audit["forbidden_feature_audit_status"] == "OK"
    assert audit["leakage_audit_status"] == "OK"
    assert audit["future_columns_not_used_for_inference"] is True
    assert audit["future_feature_columns"] == []
    assert audit["broker_api_executed"] is False
    assert audit["order_executed"] is False
    assert audit["paper_trading_executed"] is False
    assert audit["capital_allocation_executed"] is False
    assert audit["live_order_executed"] is False
    assert audit["real_account_updated"] is False


def test_phase6n_output_files_are_generated(tmp_path: Path) -> None:
    result = run_phase6n_danger_only_exit_validation(
        output_csv_path=tmp_path / "validation.csv",
        output_json_path=tmp_path / "validation.json",
        summary_path=tmp_path / "summary.json",
        yearly_summary_path=tmp_path / "yearly.json",
        action_stats_path=tmp_path / "actions.json",
        seed=42,
        dates_per_year=5,
        created_at="2026-06-14T00:00:00+00:00",
    )

    for filename in ["validation.csv", "validation.json", "summary.json", "yearly.json", "actions.json"]:
        assert (tmp_path / filename).is_file()
    persisted = pd.read_csv(tmp_path / "validation.csv")
    payload = json.loads((tmp_path / "validation.json").read_text(encoding="utf-8"))
    assert len(persisted) == len(result.trades) == 90
    assert payload["summary"]["danger_only_model_version"].endswith("danger_only_exit_v1")
