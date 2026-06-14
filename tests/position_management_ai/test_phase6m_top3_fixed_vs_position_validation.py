from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.position_management_ai.top3_fixed_vs_position_validation import (
    run_phase6m_top3_fixed_vs_position_validation,
)


@pytest.fixture(scope="module")
def phase6m_result(tmp_path_factory: pytest.TempPathFactory):
    tmp_path = tmp_path_factory.mktemp("phase6m")
    return run_phase6m_top3_fixed_vs_position_validation(
        output_csv_path=tmp_path / "validation.csv",
        output_json_path=tmp_path / "validation.json",
        summary_path=tmp_path / "summary.json",
        yearly_summary_path=tmp_path / "yearly.json",
        action_stats_path=tmp_path / "actions.json",
        seed=42,
        dates_per_year=5,
        created_at="2026-06-14T00:00:00+00:00",
    )


def test_phase6m_reuses_phase6l_target_dates(phase6m_result) -> None:
    selected = phase6m_result.summary["selected_target_dates"]

    assert selected == {
        "2021": ["2021-09-15", "2021-10-05", "2021-10-25", "2021-10-28", "2021-11-04"],
        "2022": ["2022-02-10", "2022-03-03", "2022-10-27", "2022-11-18", "2022-11-21"],
        "2023": ["2023-01-17", "2023-02-06", "2023-07-04", "2023-09-04", "2023-09-21"],
        "2024": ["2024-01-17", "2024-02-08", "2024-04-02", "2024-04-08", "2024-07-19"],
        "2025": ["2025-01-15", "2025-03-21", "2025-08-28", "2025-10-03", "2025-11-20"],
        "2026": ["2026-01-16", "2026-03-02", "2026-03-11", "2026-04-07", "2026-04-14"],
    }


def test_phase6m_validates_top3_only(phase6m_result) -> None:
    trades = phase6m_result.trades

    assert len(trades) == 90
    assert trades["buy_rank"].max() == 3
    assert trades.groupby("year")["target_date"].nunique().eq(5).all()


def test_phase6m_fixed_and_position_comparison_is_generated(phase6m_result) -> None:
    comparison = phase6m_result.comparison

    assert set(comparison).issuperset({"Fixed_10bd", "Fixed_20bd", "Position_Managed"})
    assert comparison["Fixed_10bd"]["count"] == 90
    assert comparison["Fixed_20bd"]["count"] == 90
    assert comparison["Position_Managed"]["count"] == 90
    assert "improvements_vs_fixed_20bd" in comparison


def test_phase6m_action_distribution_is_generated(phase6m_result) -> None:
    action_statistics = phase6m_result.action_statistics

    assert {"HOLD_count", "EXIT_count", "REDUCE_count", "ADD_count"}.issubset(action_statistics)
    assert sum(action_statistics["terminal_action_counts"].values()) == 90


def test_phase6m_audit_ok_and_future_not_used_for_inference(phase6m_result) -> None:
    audit = phase6m_result.summary["audit"]

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


def test_phase6m_output_files_are_generated(tmp_path: Path) -> None:
    result = run_phase6m_top3_fixed_vs_position_validation(
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
    assert payload["summary"]["top_n"] == 3
