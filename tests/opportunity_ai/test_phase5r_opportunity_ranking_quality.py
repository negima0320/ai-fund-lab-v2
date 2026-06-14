from __future__ import annotations

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.ranking_quality_audit import (
    aggregate_quality,
    build_bucket_analysis,
    date_metric_row,
    ndcg_at_k,
    precision_at_k,
)


def test_phase5r_ndcg_and_precision_reward_correct_ordering() -> None:
    frame = pd.DataFrame(
        {
            "ranking_score": [0.9, 0.8, 0.1, 0.0],
            "label__future_return_20d": [0.4, 0.3, -0.1, -0.2],
            "code": ["A", "B", "C", "D"],
        }
    )

    assert ndcg_at_k(frame["ranking_score"], frame["label__future_return_20d"], 2) == 1.0
    assert precision_at_k(frame, "label__future_return_20d", 2) == 1.0


def test_phase5r_date_metrics_and_bucket_analysis() -> None:
    frame = _ranking_fixture()

    row = date_metric_row("fixture", "test", "2025-01-01", frame)
    by_date = pd.DataFrame([row])
    aggregate = aggregate_quality(by_date, ["strategy", "split"])
    bucket = build_bucket_analysis(frame.assign(strategy="fixture", split="test", target_date="2025-01-01"))

    assert row["precision@5_future_return_20d"] == 1.0
    assert row["ndcg@5_future_return_20d"] == 1.0
    assert aggregate["target_date_count"].iloc[0] == 1
    assert {"rank_1_5", "rank_6_10", "rank_11_20", "rank_21_50"}.issubset(set(bucket["bucket"]))
    assert bucket.loc[bucket["bucket"] == "rank_1_5", "mean_future_return_20d"].iloc[0] > bucket.loc[bucket["bucket"] == "rank_21_50", "mean_future_return_20d"].iloc[0]


def _ranking_fixture() -> pd.DataFrame:
    rows = []
    for rank in range(1, 51):
        rows.append(
            {
                "target_date": "2025-01-01",
                "split": "test",
                "code": f"{rank:04d}",
                "ranking_score": float(100 - rank),
                "label__future_return_5d": float(51 - rank) / 1000,
                "label__future_return_10d": float(51 - rank) / 800,
                "label__future_return_20d": float(51 - rank) / 500,
                "label__future_max_return_20d": float(51 - rank) / 400,
                "label__future_max_drawdown_20d": -float(rank) / 1000,
                "label__risk_adjusted_future_return_20d": float(51 - rank) / 600,
                "label__downside_bad_20d": rank > 40,
                "label__top_decile_20d": rank <= 5,
            }
        )
    return pd.DataFrame(rows)
