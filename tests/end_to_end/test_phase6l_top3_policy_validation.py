from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.end_to_end.top3_policy_validation import (
    PHASE6L_TOP3_POLICY_NOT_VALIDATED,
    run_phase6l_top3_policy_validation,
)


@pytest.fixture(scope="module")
def phase6l_result(tmp_path_factory: pytest.TempPathFactory):
    tmp_path = tmp_path_factory.mktemp("phase6l")
    return run_phase6l_top3_policy_validation(
        output_csv_path=tmp_path / "top3_policy.csv",
        output_json_path=tmp_path / "top3_policy.json",
        comparison_path=tmp_path / "comparison.json",
        yearly_top3_path=tmp_path / "yearly_top3.json",
        risk_policy_path=tmp_path / "risk_policy.json",
        recommendation_path=tmp_path / "recommendation.json",
        seed=42,
        dates_per_year=5,
        created_at="2026-06-14T00:00:00+00:00",
    )


def test_phase6l_reuses_phase6k_target_dates(phase6l_result) -> None:
    selected = phase6l_result.summary["selected_target_dates"]

    assert selected == {
        "2021": ["2021-09-15", "2021-10-05", "2021-10-25", "2021-10-28", "2021-11-04"],
        "2022": ["2022-02-10", "2022-03-03", "2022-10-27", "2022-11-18", "2022-11-21"],
        "2023": ["2023-01-17", "2023-02-06", "2023-07-04", "2023-09-04", "2023-09-21"],
        "2024": ["2024-01-17", "2024-02-08", "2024-04-02", "2024-04-08", "2024-07-19"],
        "2025": ["2025-01-15", "2025-03-21", "2025-08-28", "2025-10-03", "2025-11-20"],
        "2026": ["2026-01-16", "2026-03-02", "2026-03-11", "2026-04-07", "2026-04-14"],
    }


def test_phase6l_top3_top5_top10_comparison_is_generated(phase6l_result) -> None:
    comparison = phase6l_result.comparison

    assert {"Top3", "Top5", "Top10"}.issubset(comparison)
    assert comparison["Top3"]["count"] == 90
    assert comparison["Top5"]["count"] == 150
    assert comparison["Top10"]["count"] == 300
    assert comparison["Top3"]["mean_future_return_20bd"] > comparison["Top5"]["mean_future_return_20bd"]
    assert comparison["Top3"]["mean_future_return_20bd"] > comparison["Top10"]["mean_future_return_20bd"]


def test_phase6l_top4_5_and_top6_10_comparison_is_generated(phase6l_result) -> None:
    comparison = phase6l_result.comparison

    assert comparison["Top4-5"]["count"] == 60
    assert comparison["Top6-10"]["count"] == 150
    assert comparison["top4_5_backup_only"] is True
    assert comparison["top6_10_avoid_confirmed"] is True


def test_phase6l_risk_guard_skip_vs_low_priority_is_generated(phase6l_result) -> None:
    risk_policy = phase6l_result.risk_guard_policy_comparison

    assert set(risk_policy) == {
        "Top3_BUY_ONLY",
        "Top3_WITH_LOW_PRIORITY",
        "Top5_BUY_ONLY",
        "Top5_WITH_LOW_PRIORITY",
    }
    assert risk_policy["Top3_BUY_ONLY"]["skip_count"] >= 0
    assert risk_policy["Top3_WITH_LOW_PRIORITY"]["low_priority_count"] == risk_policy["Top3_BUY_ONLY"]["skip_count"]
    assert risk_policy["Top5_WITH_LOW_PRIORITY"]["included_count"] == 150


def test_phase6l_policy_recommendation_is_generated(phase6l_result) -> None:
    recommendation = phase6l_result.policy_recommendation

    assert recommendation["primary_buy_target"] == "Top3"
    assert recommendation["backup_watchlist"] == "Top4-5"
    assert recommendation["avoid_or_no_buy"] == "Top6-10"
    assert recommendation["risk_guard_bad_policy"] == "LOW_PRIORITY_REVIEW"


def test_phase6l_audit_ok_and_no_execution_side_effects(phase6l_result) -> None:
    audit = phase6l_result.summary["audit"]

    assert phase6l_result.summary["completion_status"] != PHASE6L_TOP3_POLICY_NOT_VALIDATED
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


def test_phase6l_output_files_are_generated(tmp_path: Path) -> None:
    result = run_phase6l_top3_policy_validation(
        output_csv_path=tmp_path / "top3_policy.csv",
        output_json_path=tmp_path / "top3_policy.json",
        comparison_path=tmp_path / "comparison.json",
        yearly_top3_path=tmp_path / "yearly_top3.json",
        risk_policy_path=tmp_path / "risk_policy.json",
        recommendation_path=tmp_path / "recommendation.json",
        seed=42,
        dates_per_year=5,
        created_at="2026-06-14T00:00:00+00:00",
    )

    for filename in [
        "top3_policy.csv",
        "top3_policy.json",
        "comparison.json",
        "yearly_top3.json",
        "risk_policy.json",
        "recommendation.json",
    ]:
        assert (tmp_path / filename).is_file()
    persisted = pd.read_csv(tmp_path / "top3_policy.csv")
    payload = json.loads((tmp_path / "top3_policy.json").read_text(encoding="utf-8"))
    assert len(persisted) == len(result.output) == 300
    assert payload["summary"]["policy_recommendation"]["primary_buy_target"] == "Top3"
