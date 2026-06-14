from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.end_to_end.expanded_random_validation import (
    PHASE6K_EXPANDED_VALIDATION_FAILED,
    run_phase6k_expanded_random_validation,
)


@pytest.fixture(scope="module")
def phase6k_result(tmp_path_factory: pytest.TempPathFactory):
    tmp_path = tmp_path_factory.mktemp("phase6k")
    return run_phase6k_expanded_random_validation(
        output_csv_path=tmp_path / "expanded.csv",
        output_json_path=tmp_path / "expanded.json",
        yearly_summary_path=tmp_path / "yearly.json",
        topn_path=tmp_path / "topn.json",
        risk_guard_path=tmp_path / "risk_guard.json",
        tail_dilution_path=tmp_path / "tail.json",
        seed=42,
        dates_per_year=5,
        created_at="2026-06-14T00:00:00+00:00",
    )


def test_phase6k_seed_is_reproducible(tmp_path: Path, phase6k_result) -> None:
    rerun = run_phase6k_expanded_random_validation(
        output_csv_path=tmp_path / "expanded.csv",
        output_json_path=tmp_path / "expanded.json",
        yearly_summary_path=tmp_path / "yearly.json",
        topn_path=tmp_path / "topn.json",
        risk_guard_path=tmp_path / "risk_guard.json",
        tail_dilution_path=tmp_path / "tail.json",
        seed=42,
        dates_per_year=5,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert rerun.summary["selected_target_dates"] == phase6k_result.summary["selected_target_dates"]


def test_phase6k_selects_five_dates_per_year(phase6k_result) -> None:
    selected = phase6k_result.summary["selected_target_dates"]

    assert set(selected) == {"2021", "2022", "2023", "2024", "2025", "2026"}
    assert all(len(dates) == 5 for dates in selected.values())
    assert phase6k_result.output.groupby("year")["target_date"].nunique().eq(5).all()


def test_phase6k_top3_top5_top10_summary_is_generated(phase6k_result) -> None:
    topn = phase6k_result.topn_summary

    assert set(topn) == {"Top3", "Top5", "Top10"}
    assert topn["Top3"]["row_count"] == 90
    assert topn["Top5"]["row_count"] == 150
    assert topn["Top10"]["row_count"] == 300
    assert topn["Top3"]["mean_future_return_20bd"] > topn["Top10"]["mean_future_return_20bd"]


def test_phase6k_risk_guard_analysis_is_generated(phase6k_result) -> None:
    risk_guard = phase6k_result.risk_guard_analysis

    assert set(risk_guard) == {"BUY_CANDIDATE", "SKIP", "skip_decision_counts"}
    assert risk_guard["BUY_CANDIDATE"]["count"] > 0
    assert risk_guard["SKIP"]["count"] > 0
    assert "SKIP_RISK_GUARD" in risk_guard["skip_decision_counts"]


def test_phase6k_tail_dilution_analysis_is_generated(phase6k_result) -> None:
    tail = phase6k_result.tail_dilution_analysis

    assert set(tail) == {"Top1-3", "Top4-5", "Top6-10", "tail_dilution_confirmed"}
    assert tail["tail_dilution_confirmed"] is True
    assert tail["Top1-3"]["mean_future_return_20bd"] > tail["Top6-10"]["mean_future_return_20bd"]


def test_phase6k_audit_ok_and_no_execution_side_effects(phase6k_result) -> None:
    audit = phase6k_result.summary["audit"]

    assert phase6k_result.summary["completion_status"] != PHASE6K_EXPANDED_VALIDATION_FAILED
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
    assert audit["full_backtest_executed"] is False


def test_phase6k_output_files_are_generated(tmp_path: Path) -> None:
    result = run_phase6k_expanded_random_validation(
        output_csv_path=tmp_path / "expanded.csv",
        output_json_path=tmp_path / "expanded.json",
        yearly_summary_path=tmp_path / "yearly.json",
        topn_path=tmp_path / "topn.json",
        risk_guard_path=tmp_path / "risk_guard.json",
        tail_dilution_path=tmp_path / "tail.json",
        seed=42,
        dates_per_year=5,
        created_at="2026-06-14T00:00:00+00:00",
    )

    for filename in ["expanded.csv", "expanded.json", "yearly.json", "topn.json", "risk_guard.json", "tail.json"]:
        assert (tmp_path / filename).is_file()
    persisted = pd.read_csv(tmp_path / "expanded.csv")
    payload = json.loads((tmp_path / "expanded.json").read_text(encoding="utf-8"))
    assert len(persisted) == len(result.output) == 300
    assert payload["summary"]["completion_status"] == result.summary["completion_status"]
