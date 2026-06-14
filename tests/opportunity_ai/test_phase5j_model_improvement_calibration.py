from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.model_calibration import (
    READY_FOR_PHASE5K_POLICY_FINALIZATION,
    run_model_improvement_calibration,
    select_top10_excluding_weak_tail,
    select_top_n_with_score_floor,
)
from ai_fund_lab_v2.opportunity_ai.training import fit_preprocessing


class LinearFixtureModel:
    def predict(self, matrix: np.ndarray) -> np.ndarray:
        return matrix[:, 0] * 0.07 + matrix[:, 1] * 0.03 - matrix[:, 2] * 0.02


def test_phase5j_runs_strategy_comparison(tmp_path: Path) -> None:
    dataset_path = tmp_path / "full_history_opportunity_dataset.parquet"
    model_path = tmp_path / "opportunity_model.pkl"
    phase5i_metrics_path = tmp_path / "full_history_combined_validation_metrics.json"
    phase5i_audit_path = tmp_path / "full_history_audit.json"
    output_dir = tmp_path / "phase5j"
    dataset = _dataset()
    dataset.to_parquet(dataset_path, index=False)
    feature_columns = [column for column in dataset.columns if column.startswith("feature__")]
    preprocessing = fit_preprocessing(dataset[dataset["split"] == "train"], feature_columns)
    with model_path.open("wb") as handle:
        pickle.dump(
            {
                "model": LinearFixtureModel(),
                "feature_columns": feature_columns,
                "preprocessing": preprocessing,
            },
            handle,
        )
    phase5i_metrics_path.write_text(json.dumps({"readiness_status": "READY_FOR_PHASE5J_MODEL_IMPROVEMENT_OR_CALIBRATION"}), encoding="utf-8")
    phase5i_audit_path.write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_PHASE5J_MODEL_IMPROVEMENT_OR_CALIBRATION",
                "top5_lift_status": "MIXED",
                "top10_lift_status": "MIXED",
                "top20_lift_status": "CONFIRMED",
                "top10_underperformance_status": "PERSISTENT_BUT_INVESTIGATED",
            }
        ),
        encoding="utf-8",
    )

    result = run_model_improvement_calibration(
        dataset_path=dataset_path,
        model_path=model_path,
        phase5i_metrics_path=phase5i_metrics_path,
        phase5i_audit_path=phase5i_audit_path,
        output_dir=output_dir,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.metrics["readiness_status"] == READY_FOR_PHASE5K_POLICY_FINALIZATION
    assert result.metrics["promotion_ready"] is False
    assert result.audit["leakage_status"] == "OK"
    assert result.audit["future_feature_column_count"] == 0
    assert result.audit["trade_result_feature_column_count"] == 0
    assert result.audit["multiple_strategies_compared"] is True
    assert result.audit["top6_10_tail_investigated"] is True
    assert result.recommended_policy["promotion_ready"] is False
    assert result.recommended_policy["policy_name"]
    assert (output_dir / "calibration_metrics.json").is_file()
    assert (output_dir / "calibration_audit.json").is_file()
    assert (output_dir / "calibration_by_strategy.csv").is_file()
    assert (output_dir / "calibration_by_date.csv").is_file()
    assert (output_dir / "recommended_policy.json").is_file()
    assert {"current_model_top10", "top10_score_threshold_policy", "blend_candidate_score_model_top10"}.issubset(
        set(result.by_strategy["strategy"])
    )


def test_phase5j_threshold_policies_reduce_or_preserve_top10_count() -> None:
    frame = pd.DataFrame(
        [
            {"target_date": "2026-01-31", "code": f"{index:04d}", "score__model": 1.0 - index * 0.05, "risk__downside_proxy": index / 20}
            for index in range(12)
        ]
    )

    score_selected = select_top_n_with_score_floor(frame, score_column="score__model", top_n=10, score_floor=0.70)
    weak_tail_selected = select_top10_excluding_weak_tail(
        frame,
        score_column="score__model",
        tail_score_floor=0.72,
        tail_risk_ceiling=0.35,
    )

    assert len(score_selected) <= 10
    assert len(weak_tail_selected) <= 10
    assert len(weak_tail_selected) >= 5


def _dataset() -> pd.DataFrame:
    rows = []
    split_by_date = {
        **{f"2024-01-{day:02d}": "train" for day in range(1, 7)},
        **{f"2025-01-{day:02d}": "validation" for day in range(1, 4)},
        **{f"2026-01-{day:02d}": "test" for day in range(1, 4)},
    }
    for target_date, split_name in split_by_date.items():
        for rank in range(1, 13):
            strength = (13 - rank) / 12
            future_return = 0.015 + strength * 0.08
            if rank in {6, 7, 8, 9, 10} and split_name == "test":
                future_return -= 0.07
            rows.append(
                {
                    "target_date": target_date,
                    "code": f"{rank:04d}",
                    "split": split_name,
                    "feature__candidate_score": strength,
                    "feature__candidate_rank": rank,
                    "feature__price_momentum_return_20d": strength * 0.20,
                    "feature__price_momentum_return_60d": strength * 0.25,
                    "feature__trend_close_over_ma_20d": strength * 0.10,
                    "feature__trend_ma_20_60_ratio": 1.0 + strength * 0.05,
                    "feature__liquidity_avg_volume_20d": 100000 + rank * 1000,
                    "feature__volatility_return_std_20d": 0.02 + rank * 0.002,
                    "feature__volume_momentum_ratio_1d_20d": 1.0 + rank * 0.05,
                    "label__expected_edge_label_20d": future_return + strength * 0.04,
                    "label__future_return_20d": future_return,
                    "label__future_max_return_20d": future_return + 0.05,
                    "label__future_max_drawdown_20d": -0.03 - rank * 0.002,
                    "label__downside_bad_20d": rank >= 9,
                    "label__top_decile_20d": rank <= 2,
                }
            )
    return pd.DataFrame(rows)
