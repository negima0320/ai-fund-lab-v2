from __future__ import annotations

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.historical_candidates import (
    READY_FOR_PHASE5D_DATASET,
    build_historical_candidate_top50_frame,
    select_target_dates,
)


class DummyModel:
    def predict_proba(self, x_input: np.ndarray) -> np.ndarray:
        score = x_input[:, 0] + x_input[:, 1] * 0.01
        score = (score - score.min()) / (score.max() - score.min() + 1e-9)
        return np.column_stack([1.0 - score, score])


def test_phase5d2_selects_monthly_target_dates_from_label_and_feature_overlap() -> None:
    selected = select_target_dates(
        feature_dates=["2025-01-02", "2025-01-31", "2025-02-03", "2025-02-28", "2025-03-03"],
        label_dates=["2025-01-31", "2025-02-03", "2025-02-28"],
        frequency="monthly",
        max_dates=None,
    )

    assert selected == ["2025-01-31", "2025-02-28"]


def test_phase5d2_builds_historical_candidate_top50_without_future_features() -> None:
    result = build_historical_candidate_top50_frame(
        model=DummyModel(),
        model_feature_columns=["feature__price_momentum_return_20d", "feature__liquidity_avg_volume_20d"],
        feature_frame=_feature_frame(),
        label_frame=_label_frame(),
        frequency="all",
        top_n=2,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.summary["readiness_status"] == READY_FOR_PHASE5D_DATASET
    assert result.summary["candidate_rows"] == 4
    assert result.audit["future_feature_column_count"] == 0
    assert result.audit["forbidden_feature_column_count"] == 0
    assert result.audit["label_join_coverage_rate"] == 1.0
    assert set(result.candidates.columns).issuperset(
        {
            "target_date",
            "code",
            "candidate_score",
            "candidate_rank",
            "candidate_reason",
            "model_version",
            "feature_version",
            "inference_run_id",
        }
    )
    assert result.candidates.groupby("target_date").size().min() == 2
    assert result.candidates.groupby("target_date")["candidate_rank"].max().max() == 2


def test_phase5d2_audit_blocks_future_model_feature() -> None:
    result = build_historical_candidate_top50_frame(
        model=DummyModel(),
        model_feature_columns=["feature__future_return_20d", "feature__liquidity_avg_volume_20d"],
        feature_frame=_feature_frame(),
        label_frame=_label_frame(),
        frequency="all",
        top_n=2,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.summary["status"] == "BLOCKED"
    assert result.audit["future_feature_column_count"] == 1
    assert result.audit["leakage_audit_status"] == "ERROR"


def test_phase5d2_audit_blocks_trade_result_source_feature() -> None:
    features = _feature_frame()
    features["trade_result"] = 1.0

    result = build_historical_candidate_top50_frame(
        model=DummyModel(),
        model_feature_columns=["feature__price_momentum_return_20d", "feature__liquidity_avg_volume_20d"],
        feature_frame=features,
        label_frame=_label_frame(),
        frequency="all",
        top_n=2,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.summary["status"] == "BLOCKED"
    assert result.audit["trade_result_column_count"] == 1
    assert result.audit["leakage_audit_status"] == "ERROR"


def _feature_frame() -> pd.DataFrame:
    rows = []
    for target_date in ("2025-01-31", "2025-02-28"):
        for index, code in enumerate(("1000", "2000", "3000"), start=1):
            rows.append(
                {
                    "target_date": target_date,
                    "as_of_date": target_date,
                    "code": code,
                    "feature_version": "candidate_features_real_runtime_v1",
                    "source_snapshot_id": "fixture",
                    "universe_eligible": True,
                    "excluded_reason": "",
                    "price_momentum_return_20d": float(index),
                    "liquidity_avg_volume_20d": float(index * 100),
                    "price_momentum_return_60d": float(index),
                    "volume_momentum_ratio_5d": 1.1,
                }
            )
    return pd.DataFrame(rows)


def _label_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2025-01-31", "code": "2000"},
            {"target_date": "2025-01-31", "code": "3000"},
            {"target_date": "2025-02-28", "code": "2000"},
            {"target_date": "2025-02-28", "code": "3000"},
        ]
    )
