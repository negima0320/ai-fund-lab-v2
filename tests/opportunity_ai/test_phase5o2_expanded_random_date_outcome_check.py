from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.expanded_random_outcome_check import run_expanded_random_date_outcome_check


class FixtureModel:
    def predict(self, matrix: np.ndarray) -> np.ndarray:
        return matrix[:, 0] + matrix[:, 1] * 0.1


def test_phase5o2_builds_expanded_outputs(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)

    result = run_expanded_random_date_outcome_check(
        output_dir=tmp_path / "phase5o2",
        candidate_path=paths["candidate"],
        label_path=paths["label"],
        baseline_dataset_path=paths["baseline_dataset"],
        baseline_model_path=paths["baseline_model"],
        market_only_dataset_path=paths["market_only_dataset"],
        market_only_model_path=paths["market_only_model"],
        market_sector_dataset_path=paths["market_sector_dataset"],
        market_sector_model_path=paths["market_sector_model"],
        doc_path=tmp_path / "phase5o2.md",
        years=[2021, 2022],
        samples_per_year=2,
        top_n=5,
        seed=42,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.summary["status"] == "OK"
    assert result.summary["sampled_target_date_count"] == 4
    assert {"CandidateTop50", "CandidateScoreTop5", "OpportunityBaselineTop5", "MarketOnlyTop5", "MarketSectorTop5"}.issubset(set(result.by_date["selection_group"]))
    assert "market_only_beats_baseline_20bd" in result.strategy_comparison.columns
    assert result.summary["leakage_status"] == "OK"
    assert result.summary["feature_audits"]["OpportunityBaselineTop5"]["future_feature_column_count"] == 0
    assert (tmp_path / "phase5o2" / "random_date_outcome_check_50days.json").is_file()
    assert (tmp_path / "phase5o2" / "random_date_outcome_by_date.csv").is_file()
    assert (tmp_path / "phase5o2" / "random_date_outcome_by_year.csv").is_file()
    assert (tmp_path / "phase5o2" / "random_date_strategy_comparison.csv").is_file()
    assert (tmp_path / "phase5o2.md").is_file()


def _write_fixture(tmp_path: Path) -> dict[str, Path]:
    dates = ["2021-01-04", "2021-01-05", "2022-01-04", "2022-01-05"]
    candidate_rows = []
    dataset_rows = []
    label_rows = []
    for target_date in dates:
        for rank in range(1, 8):
            code = f"{rank:04d}"
            score = 1.0 - rank * 0.1
            candidate_rows.append({"target_date": target_date, "code": code, "candidate_score": score, "candidate_rank": rank})
            dataset_rows.append(
                {
                    "target_date": target_date,
                    "as_of_date": target_date,
                    "code": code,
                    "split": "test",
                    "feature__candidate_score": score,
                    "feature__candidate_rank": rank,
                    "feature__price_momentum_return_20d": score / 10,
                    "label__future_return_20d": 0.03 * rank,
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
    paths = {
        "candidate": tmp_path / "candidate.parquet",
        "label": tmp_path / "label.parquet",
        "baseline_dataset": tmp_path / "baseline_dataset.parquet",
        "market_only_dataset": tmp_path / "market_only_dataset.parquet",
        "market_sector_dataset": tmp_path / "market_sector_dataset.parquet",
        "baseline_model": tmp_path / "baseline_model.pkl",
        "market_only_model": tmp_path / "market_only_model.pkl",
        "market_sector_model": tmp_path / "market_sector_model.pkl",
    }
    pd.DataFrame(candidate_rows).to_parquet(paths["candidate"], index=False)
    pd.DataFrame(label_rows).to_parquet(paths["label"], index=False)
    base = pd.DataFrame(dataset_rows)
    base.to_parquet(paths["baseline_dataset"], index=False)
    market_only = base.assign(feature__market_return_20d=0.1)
    market_sector = market_only.assign(feature__sector_return_20d=0.2)
    market_only.to_parquet(paths["market_only_dataset"], index=False)
    market_sector.to_parquet(paths["market_sector_dataset"], index=False)
    _write_model(paths["baseline_model"], ["feature__candidate_score", "feature__price_momentum_return_20d"])
    _write_model(paths["market_only_model"], ["feature__candidate_score", "feature__market_return_20d"])
    _write_model(paths["market_sector_model"], ["feature__candidate_score", "feature__sector_return_20d"])
    return paths


def _write_model(path: Path, feature_columns: list[str]) -> None:
    with path.open("wb") as handle:
        pickle.dump(
            {
                "model": FixtureModel(),
                "feature_columns": feature_columns,
                "preprocessing": {
                    "categorical_maps": {},
                    "medians": {column: 0.0 for column in feature_columns},
                    "boolean_columns": [],
                },
            },
            handle,
        )
