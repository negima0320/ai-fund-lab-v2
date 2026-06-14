from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.position_management_ai.exit_confirmation_validation import (
    run_phase6o_exit_confirmation_validation,
)


@pytest.fixture(scope="module")
def phase6o_result(tmp_path_factory: pytest.TempPathFactory):
    tmp_path = tmp_path_factory.mktemp("phase6o")
    return run_phase6o_exit_confirmation_validation(
        output_csv_path=tmp_path / "validation.csv",
        output_json_path=tmp_path / "validation.json",
        summary_path=tmp_path / "summary.json",
        yearly_summary_path=tmp_path / "yearly.json",
        action_stats_path=tmp_path / "actions.json",
        seed=42,
        dates_per_year=5,
        created_at="2026-06-14T00:00:00+00:00",
    )


def test_phase6o_reuses_phase6lmn_target_dates(phase6o_result) -> None:
    assert phase6o_result.summary["selected_target_dates"] == {
        "2021": ["2021-09-15", "2021-10-05", "2021-10-25", "2021-10-28", "2021-11-04"],
        "2022": ["2022-02-10", "2022-03-03", "2022-10-27", "2022-11-18", "2022-11-21"],
        "2023": ["2023-01-17", "2023-02-06", "2023-07-04", "2023-09-04", "2023-09-21"],
        "2024": ["2024-01-17", "2024-02-08", "2024-04-02", "2024-04-08", "2024-07-19"],
        "2025": ["2025-01-15", "2025-03-21", "2025-08-28", "2025-10-03", "2025-11-20"],
        "2026": ["2026-01-16", "2026-03-02", "2026-03-11", "2026-04-07", "2026-04-14"],
    }


def test_phase6o_validates_top3_only(phase6o_result) -> None:
    trades = phase6o_result.trades

    assert len(trades) == 90
    assert trades["buy_rank"].max() == 3
    assert trades.groupby("year")["target_date"].nunique().eq(5).all()


def test_phase6o_all_strategy_comparison_is_generated(phase6o_result) -> None:
    comparison = phase6o_result.comparison

    assert {"Fixed_20bd", "Current_Position_Managed", "Exit_Immediate", "Exit_Confirm_2", "Exit_Confirm_3"}.issubset(comparison)
    for name in ["Fixed_20bd", "Current_Position_Managed", "Exit_Immediate", "Exit_Confirm_2", "Exit_Confirm_3"]:
        assert comparison[name]["count"] == 90


def test_phase6o_confirm2_does_not_sell_on_first_exit(phase6o_result) -> None:
    stats = phase6o_result.action_statistics

    assert stats["exit_signal_count"] > 0
    assert stats["exit_confirm_2"]["hold_after_first_exit_count"] > 0
    assert stats["exit_confirm_2"]["confirmed_exit_count"] <= stats["exit_immediate"]["confirmed_exit_count"]


def test_phase6o_confirm3_does_not_sell_on_first_or_second_exit(phase6o_result) -> None:
    stats = phase6o_result.action_statistics

    assert stats["exit_confirm_3"]["hold_after_first_exit_count"] > 0
    assert stats["exit_confirm_3"]["hold_after_second_exit_count"] >= 0
    assert stats["exit_confirm_3"]["confirmed_exit_count"] <= stats["exit_confirm_2"]["confirmed_exit_count"]


def test_phase6o_reduce_and_add_are_not_actual_actions(phase6o_result) -> None:
    audit = phase6o_result.summary["audit"]

    assert audit["actual_reduce_count"] == 0
    assert audit["actual_add_count"] == 0


def test_phase6o_audit_ok_and_future_not_used_for_inference(phase6o_result) -> None:
    audit = phase6o_result.summary["audit"]

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


def test_phase6o_output_files_are_generated(tmp_path: Path) -> None:
    result = run_phase6o_exit_confirmation_validation(
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
    assert payload["summary"]["exit_confirmation_model_version"].endswith("exit_confirmation_v1")
