from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.random_date_outcome_check import (
    run_random_date_outcome_check,
    sample_target_dates,
)


class ScoreFixtureModel:
    def predict(self, matrix: np.ndarray) -> np.ndarray:
        return matrix[:, 0] * 0.5 + matrix[:, 1] * 0.2


def test_phase5o_random_seed_selects_same_dates() -> None:
    eligible = {2021: ["2021-01-01", "2021-01-02"], 2022: ["2022-01-01", "2022-01-02"]}

    first = sample_target_dates(eligible, years=[2021, 2022], samples_per_year=1, seed=7)
    second = sample_target_dates(eligible, years=[2021, 2022], samples_per_year=1, seed=7)

    assert first == second
    assert len(first) == 2
    assert first[0].startswith("2021-")
    assert first[1].startswith("2022-")


def test_phase5o_builds_outcome_artifacts(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)

    result = run_random_date_outcome_check(
        candidate_path=paths["candidate"],
        dataset_path=paths["dataset"],
        label_path=paths["label"],
        model_path=paths["model"],
        output_dir=tmp_path / "phase5o",
        doc_path=tmp_path / "phase5o.md",
        years=[2021, 2022],
        samples_per_year=1,
        top_n=5,
        seed=11,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.summary["status"] == "OK"
    assert len(result.summary["sampled_target_dates"]) == 2
    assert {"CandidateTop50", "CandidateScoreTop5", "OpportunityTop5"}.issubset(set(result.by_date["selection_group"]))
    assert "return_5bd" in result.by_stock.columns
    assert "return_10bd" in result.by_stock.columns
    assert "return_20bd" in result.by_stock.columns
    assert result.summary["feature_audit"]["future_feature_column_count"] == 0
    assert result.summary["label_table_used_for_inference_features"] is False
    assert (tmp_path / "phase5o" / "random_date_outcome_check.json").is_file()
    assert (tmp_path / "phase5o" / "random_date_outcome_by_date.csv").is_file()
    assert (tmp_path / "phase5o" / "random_date_outcome_by_stock.csv").is_file()
    assert (tmp_path / "phase5o.md").is_file()


def _write_fixture(tmp_path: Path) -> dict[str, Path]:
    candidate_path = tmp_path / "candidate.parquet"
    dataset_path = tmp_path / "dataset.parquet"
    label_path = tmp_path / "labels.parquet"
    model_path = tmp_path / "model.pkl"
    dates = ["2021-01-04", "2021-01-05", "2022-01-04", "2022-01-05"]
    candidate_rows = []
    dataset_rows = []
    label_rows = []
    for target_date in dates:
        for rank in range(1, 8):
            code = f"{rank:04d}"
            score = 1.0 - rank * 0.1
            candidate_rows.append(
                {
                    "target_date": target_date,
                    "code": code,
                    "candidate_score": score,
                    "candidate_rank": rank,
                    "candidate_reason": "fixture",
                }
            )
            dataset_rows.append(
                {
                    "target_date": target_date,
                    "code": code,
                    "split": "test",
                    "feature__candidate_score": score,
                    "feature__price_momentum_return_20d": score / 10,
                    "feature__candidate_rank": rank,
                }
            )
            label_rows.append(
                {
                    "target_date": target_date,
                    "code": code,
                    "future_return_5d": 0.01 * rank,
                    "future_return_10d": 0.02 * rank,
                    "future_return_20d": 0.03 * rank,
                    "future_max_return_20d": 0.04 * rank,
                    "future_max_drawdown_20d": -0.01 * rank,
                }
            )
    pd.DataFrame(candidate_rows).to_parquet(candidate_path, index=False)
    pd.DataFrame(dataset_rows).to_parquet(dataset_path, index=False)
    pd.DataFrame(label_rows).to_parquet(label_path, index=False)
    with model_path.open("wb") as handle:
        pickle.dump(
            {
                "model": ScoreFixtureModel(),
                "feature_columns": ["feature__candidate_score", "feature__price_momentum_return_20d"],
                "preprocessing": {
                    "categorical_maps": {},
                    "medians": {"feature__candidate_score": 0.0, "feature__price_momentum_return_20d": 0.0},
                    "boolean_columns": [],
                },
            },
            handle,
        )
    return {
        "candidate": candidate_path,
        "dataset": dataset_path,
        "label": label_path,
        "model": model_path,
    }
