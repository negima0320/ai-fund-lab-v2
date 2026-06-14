from __future__ import annotations

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.market_sector_split_impact import (
    build_by_strategy_table,
    build_conclusion,
    build_random_comparison_table,
    select_strategy_dataset,
)


def test_phase5p2_select_strategy_dataset_keeps_only_requested_features() -> None:
    dataset = pd.DataFrame(
        [
            {
                "target_date": "2025-01-01",
                "as_of_date": "2025-01-01",
                "code": "1001",
                "split": "test",
                "dataset_version": "old",
                "feature_version": "old",
                "created_at": "old",
                "feature__candidate_score": 0.1,
                "feature__market_return_20d": 0.2,
                "feature__sector_return_20d": 0.3,
                "label__future_return_20d": 0.4,
            }
        ]
    )

    out = select_strategy_dataset(
        dataset,
        feature_columns=["feature__candidate_score", "feature__market_return_20d"],
        created_at="2026-06-14T00:00:00+00:00",
        strategy_name="market_only",
    )

    assert "feature__candidate_score" in out.columns
    assert "feature__market_return_20d" in out.columns
    assert "feature__sector_return_20d" not in out.columns
    assert "label__future_return_20d" in out.columns
    assert out["dataset_version"].iloc[0] == "opportunity_dataset_v1_1_market_only"


def test_phase5p2_builds_strategy_and_random_comparison() -> None:
    baseline = _combined(0.01)
    strategies = {
        "market_only": {"combined_metrics": _combined(0.03), "random_summary": _random(-0.02, ["2022-01-13"])},
        "sector_only": {"combined_metrics": _combined(0.00), "random_summary": _random(-0.12, [])},
        "market_sector": {"combined_metrics": _combined(0.02), "random_summary": _random(-0.05, ["2022-01-13"])},
    }

    by_strategy = build_by_strategy_table(baseline_combined=baseline, strategy_results=strategies)
    random_comparison = build_random_comparison_table(baseline_random=_random(-0.10, []), strategy_results=strategies)
    conclusion = build_conclusion(by_strategy, random_comparison)

    assert {"baseline", "market_only", "sector_only", "market_sector"}.issubset(set(by_strategy["strategy"]))
    assert "delta_mean_return_20d_vs_baseline" in by_strategy.columns
    assert random_comparison.loc[random_comparison["strategy"] == "market_only", "date_2022_01_13_improved"].iloc[0]
    assert conclusion["readiness_status"] in {"MARKET_ONLY_IMPROVES", "MARKET_AND_SECTOR_IMPROVES"}


def _combined(value: float) -> dict:
    return {
        "quality_metrics": {
            split: {
                "rankers": {
                    "model": {
                        topn: {
                            "selected_mean_future_return": value,
                            "selected_mean_future_max_return": value + 0.1,
                            "selected_downside_bad_rate": 0.2,
                            "selected_mean_future_max_drawdown": -0.1,
                            "win_rate_20d": 0.6,
                        }
                        for topn in ("top5", "top10", "top20")
                    }
                }
            }
            for split in ("validation", "test")
        }
    }


def _random(value: float, effective_dates: list[str]) -> dict:
    return {
        "sampled_target_dates": ["2022-01-13"],
        "opportunity_effective_dates_20bd_vs_candidate_top50": effective_dates,
        "by_date_records": [
            {
                "target_date": "2022-01-13",
                "selection_group": "OpportunityTop5",
                "mean_return_20bd": value,
            }
        ],
    }
