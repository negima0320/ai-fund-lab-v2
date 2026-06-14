from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.end_to_end.random_yearly_smoke_test import (
    PHASE6J_E2E_SMOKE_TEST_PASSED,
    run_phase6j_random_yearly_e2e_smoke_test,
)


@pytest.fixture(scope="module")
def phase6j_result(tmp_path_factory: pytest.TempPathFactory):
    tmp_path = tmp_path_factory.mktemp("phase6j")
    return run_phase6j_random_yearly_e2e_smoke_test(
        output_csv_path=tmp_path / "e2e.csv",
        output_json_path=tmp_path / "e2e.json",
        summary_path=tmp_path / "summary.json",
        seed=42,
        created_at="2026-06-14T00:00:00+00:00",
    )


def test_phase6j_selects_at_most_one_date_per_year(phase6j_result) -> None:
    selected = phase6j_result.summary["selected_target_dates"]

    assert set(selected) == {"2021", "2022", "2023", "2024", "2025", "2026"}
    assert phase6j_result.output.groupby("year")["target_date"].nunique().max() == 1


def test_phase6j_seed_is_reproducible(tmp_path: Path, phase6j_result) -> None:
    rerun = run_phase6j_random_yearly_e2e_smoke_test(
        output_csv_path=tmp_path / "e2e.csv",
        output_json_path=tmp_path / "e2e.json",
        summary_path=tmp_path / "summary.json",
        seed=42,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert rerun.summary["selected_target_dates"] == phase6j_result.summary["selected_target_dates"]


def test_phase6j_top5_is_generated(phase6j_result) -> None:
    output = phase6j_result.output

    assert len(output) == 30
    assert output.groupby("year")["buy_rank"].max().eq(5).all()
    assert output["expected_edge_score"].notna().all()
    assert output["downside_risk_score"].notna().all()


def test_phase6j_future_columns_are_evaluation_only(phase6j_result) -> None:
    output = phase6j_result.output
    audit = phase6j_result.summary["audit"]

    for column in [
        "future_return_5bd",
        "future_return_10bd",
        "future_return_20bd",
        "future_max_return_20bd",
        "future_min_return_20bd",
    ]:
        assert column in output.columns
    assert audit["future_columns_not_used_for_inference"] is True
    assert audit["future_feature_columns"] == []


def test_phase6j_audit_ok_and_no_execution_side_effects(phase6j_result) -> None:
    audit = phase6j_result.summary["audit"]

    assert phase6j_result.summary["completion_status"] == PHASE6J_E2E_SMOKE_TEST_PASSED
    assert audit["forbidden_feature_audit_status"] == "OK"
    assert audit["leakage_audit_status"] == "OK"
    assert audit["broker_api_executed"] is False
    assert audit["order_executed"] is False
    assert audit["paper_trading_executed"] is False
    assert audit["capital_allocation_executed"] is False


def test_phase6j_output_files_are_generated(tmp_path: Path) -> None:
    run_phase6j_random_yearly_e2e_smoke_test(
        output_csv_path=tmp_path / "e2e.csv",
        output_json_path=tmp_path / "e2e.json",
        summary_path=tmp_path / "summary.json",
        seed=42,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert (tmp_path / "e2e.csv").is_file()
    assert (tmp_path / "e2e.json").is_file()
    assert (tmp_path / "summary.json").is_file()
    persisted = pd.read_csv(tmp_path / "e2e.csv")
    assert len(persisted) == 30
