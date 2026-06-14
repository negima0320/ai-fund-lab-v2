from __future__ import annotations

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.market_sector_completion import (
    MARKET_FEATURE_COLUMNS,
    SECTOR_FEATURE_COLUMNS,
    attach_market_sector_features,
    audit_sector_master_snapshot,
    build_baseline_comparison,
    build_market_sector_features,
)


def test_phase5p_builds_market_and_sector_features_without_future_columns() -> None:
    source = _source_features()
    listed = pd.DataFrame(
        [
            {"code": "1001", "S33Nm": "Tech", "Date": "2026-06-01"},
            {"code": "1002", "S33Nm": "Tech", "Date": "2026-06-01"},
            {"code": "2001", "S33Nm": "Retail", "Date": "2026-06-01"},
        ]
    )

    features = build_market_sector_features(source, listed, target_dates=["2021-01-04", "2021-01-05"], created_at="2026-06-14T00:00:00+00:00")

    assert {"target_date", "code", "market_return_20d", "sector_return_20d", "stock_vs_sector_return_20d"}.issubset(features.columns)
    assert len(features) == 6
    assert not [column for column in features.columns if "future_" in column]
    assert features["market_breadth_20d"].between(0, 1).all()


def test_phase5p_attaches_prefixed_features_and_audits_sector_snapshot() -> None:
    source = _source_features()
    listed = pd.DataFrame(
        [
            {"code": "1001", "S33Nm": "Tech", "Date": "2026-06-01"},
            {"code": "1002", "S33Nm": "Tech", "Date": "2026-06-01"},
            {"code": "2001", "S33Nm": "Retail", "Date": "2026-06-01"},
        ]
    )
    features = build_market_sector_features(source, listed, target_dates=["2021-01-04", "2021-01-05"], created_at="2026-06-14T00:00:00+00:00")
    dataset = pd.DataFrame(
        [
            {"target_date": "2021-01-04", "as_of_date": "2021-01-04", "code": "1001", "split": "train", "feature__candidate_score": 0.5, "label__future_return_20d": 0.1},
            {"target_date": "2021-01-05", "as_of_date": "2021-01-05", "code": "2001", "split": "train", "feature__candidate_score": 0.4, "label__future_return_20d": -0.1},
        ]
    )

    enriched = attach_market_sector_features(dataset, features, created_at="2026-06-14T00:00:00+00:00")
    snapshot_audit = audit_sector_master_snapshot(listed, enriched)

    assert set(MARKET_FEATURE_COLUMNS).issubset(enriched.columns)
    assert set(SECTOR_FEATURE_COLUMNS).issubset(enriched.columns)
    assert not [column for column in enriched.columns if column.startswith("feature__future_")]
    assert snapshot_audit["snapshot_proxy_warning"] is True
    assert snapshot_audit["rows_with_date_after_dataset_min_target_date"] == 3


def test_phase5p_baseline_comparison_detects_failure_date_improvement() -> None:
    comparison = build_baseline_comparison(
        baseline_combined=_combined_metric(0.01),
        new_combined=_combined_metric(0.02),
        baseline_random=_random_metric(-0.10),
        new_random=_random_metric(-0.02),
    )

    assert comparison["any_topn_improved"] is True
    assert comparison["failure_date_2022_01_13_improved"] is True
    assert comparison["random_date_outcome"]["phase5p_minus_baseline_2022_01_13"] == 0.08


def _source_features() -> pd.DataFrame:
    rows = []
    for target_date, offset in (("2021-01-04", 0.0), ("2021-01-05", 0.02)):
        rows.extend(
            [
                {
                    "target_date": target_date,
                    "code": "1001",
                    "price_momentum_return_5d": 0.01 + offset,
                    "price_momentum_return_20d": 0.05 + offset,
                    "trend_ma_5_20_ratio": 0.02,
                    "volatility_return_std_20d": 0.03,
                },
                {
                    "target_date": target_date,
                    "code": "1002",
                    "price_momentum_return_5d": -0.01 + offset,
                    "price_momentum_return_20d": -0.02 + offset,
                    "trend_ma_5_20_ratio": -0.01,
                    "volatility_return_std_20d": 0.04,
                },
                {
                    "target_date": target_date,
                    "code": "2001",
                    "price_momentum_return_5d": 0.03 + offset,
                    "price_momentum_return_20d": 0.08 + offset,
                    "trend_ma_5_20_ratio": 0.03,
                    "volatility_return_std_20d": 0.02,
                },
            ]
        )
    return pd.DataFrame(rows)


def _combined_metric(value: float) -> dict:
    return {
        "quality_metrics": {
            split: {
                "rankers": {
                    "model": {
                        topn: {"selected_mean_future_return": value}
                        for topn in ("top5", "top10", "top20")
                    }
                }
            }
            for split in ("validation", "test")
        }
    }


def _random_metric(value: float) -> dict:
    return {
        "by_date_records": [
            {
                "target_date": "2022-01-13",
                "selection_group": "OpportunityTop5",
                "mean_return_20bd": value,
            }
        ],
        "opportunity_effective_dates_20bd_vs_candidate_top50": [],
    }
