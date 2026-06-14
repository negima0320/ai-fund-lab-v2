from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.inference import (
    BLOCKED_BY_LEAKAGE_AUDIT,
    READY_FOR_PHASE5G_QUALITY_AUDIT,
    audit_opportunity_inference_frame,
    build_inference_feature_frame,
    run_opportunity_inference,
)


class DummyOpportunityModel:
    def predict(self, x_input: np.ndarray) -> np.ndarray:
        return x_input[:, 0] * 0.5 + x_input[:, 2] * 0.2 - x_input[:, 3] * 0.1


def test_phase5f_runs_inference_and_writes_outputs_without_label_table(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    feature_path = tmp_path / "feature.parquet"
    model_path = tmp_path / "model.pkl"
    metrics_path = tmp_path / "training_metrics.json"
    _write_candidate(candidate_path)
    _feature_frame().to_parquet(feature_path, index=False)
    _write_model(model_path)
    metrics_path.write_text(json.dumps({"readiness_status": "TRAINING_COMPLETE_WITH_WARNINGS"}), encoding="utf-8")

    result = run_opportunity_inference(
        candidate_path=candidate_path,
        feature_path=feature_path,
        model_path=model_path,
        training_metrics_path=metrics_path,
        output_dir=tmp_path / "out",
        created_at="2026-06-14T00:00:00+00:00",
        inference_run_id="fixture_run",
    )

    assert result.summary["readiness_status"] == READY_FOR_PHASE5G_QUALITY_AUDIT
    assert result.summary["promotion_ready"] is False
    assert result.audit["label_table_read_flag"] is False
    assert result.audit["leakage_audit_status"] == "OK"
    assert result.summary["input_candidate_count"] == 25
    assert result.summary["output_count"] == 25
    assert result.summary["top5_count"] == 5
    assert result.summary["top10_count"] == 10
    assert result.summary["top20_count"] == 20
    assert Path(result.summary["output_path"]).is_file()
    assert Path(result.summary["top20_path"]).is_file()
    assert result.output["buy_rank"].min() == 1
    assert result.output["buy_rank"].max() == 25


def test_phase5f_output_schema_contains_required_columns(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    feature_path = tmp_path / "feature.parquet"
    model_path = tmp_path / "model.pkl"
    _write_candidate(candidate_path)
    _feature_frame().to_parquet(feature_path, index=False)
    _write_model(model_path)

    result = run_opportunity_inference(
        candidate_path=candidate_path,
        feature_path=feature_path,
        model_path=model_path,
        output_dir=tmp_path / "out",
        created_at="2026-06-14T00:00:00+00:00",
        inference_run_id="fixture_run",
    )

    required = {
        "target_date",
        "code",
        "expected_edge_score",
        "buy_rank",
        "expected_return_horizon",
        "downside_risk_score",
        "buy_reason",
        "no_buy_reason",
        "candidate_score",
        "candidate_rank",
        "model_version",
        "feature_version",
        "inference_run_id",
        "created_at",
        "is_top5",
        "is_top10",
        "is_top20",
    }
    assert required.issubset(result.output.columns)


def test_phase5f_blocks_future_feature_leakage() -> None:
    candidate = pd.DataFrame(_candidate_rows())
    features = _feature_frame()
    features["future_return_20d"] = 0.50
    frame = build_inference_feature_frame(candidate_frame=candidate, feature_frame=features)
    feature_columns = ["feature__candidate_score", "feature__future_return_20d"]

    audit = audit_opportunity_inference_frame(
        frame,
        feature_columns=feature_columns,
        input_candidate_count=len(candidate),
        label_table_read_flag=False,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert audit["readiness_status"] == BLOCKED_BY_LEAKAGE_AUDIT
    assert audit["leakage_audit_status"] == "ERROR"
    assert audit["future_feature_column_count"] >= 1


def test_phase5f_blocks_ai_output_reinput_leakage() -> None:
    candidate = pd.DataFrame(_candidate_rows())
    features = _feature_frame()
    features["expected_edge_score"] = 0.10
    frame = build_inference_feature_frame(candidate_frame=candidate, feature_frame=features)

    audit = audit_opportunity_inference_frame(
        frame,
        feature_columns=["feature__candidate_score"],
        input_candidate_count=len(candidate),
        label_table_read_flag=False,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert audit["leakage_audit_status"] == "ERROR"
    assert audit["ai_output_leakage_column_count"] == 1


def _write_candidate(path: Path) -> None:
    path.write_text(json.dumps({"rows": _candidate_rows(), "target_date": "2026-06-12"}), encoding="utf-8")


def _write_model(path: Path) -> None:
    payload = {
        "model_version": "fixture_opportunity_model",
        "model": DummyOpportunityModel(),
        "feature_columns": [
            "feature__candidate_score",
            "feature__candidate_reason",
            "feature__price_momentum_return_20d",
            "feature__volatility_return_std_20d",
        ],
        "preprocessing": {
            "categorical_maps": {
                "feature__candidate_reason": {
                    "high_candidate_score": 1,
                    "liquidity_available": 0,
                }
            },
            "medians": {
                "feature__candidate_score": 0.0,
                "feature__candidate_reason": -1.0,
                "feature__price_momentum_return_20d": 0.0,
                "feature__volatility_return_std_20d": 0.0,
            },
            "boolean_columns": [],
        },
    }
    with path.open("wb") as handle:
        pickle.dump(payload, handle)


def _candidate_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for rank in range(1, 26):
        rows.append(
            {
                "target_date": "2026-06-12",
                "code": f"{1000 + rank}",
                "candidate_score": 1.0 - rank / 100.0,
                "candidate_rank": rank,
                "candidate_reason": "high_candidate_score" if rank <= 10 else "liquidity_available",
                "model_version": "phase4bf_formal_candidate_model",
                "feature_snapshot_id": "fixture",
            }
        )
    return rows


def _feature_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for rank in range(1, 26):
        rows.append(
            {
                "target_date": "2026-06-12",
                "as_of_date": "2026-06-12",
                "code": f"{1000 + rank}",
                "feature_version": "candidate_features_real_runtime_v1",
                "source_snapshot_id": "fixture",
                "feature_set_name": "fixture",
                "universe_eligible": True,
                "missing_flags_insufficient_history": False,
                "missing_flags_price": False,
                "missing_flags_volume": False,
                "price_momentum_return_20d": (26 - rank) / 100.0,
                "price_momentum_return_60d": (26 - rank) / 80.0,
                "volatility_return_std_20d": rank / 1000.0,
                "trend_close_over_ma_20d": (26 - rank) / 200.0,
                "trend_ma_5_20_ratio": 1.0,
                "trend_ma_20_60_ratio": 1.0,
                "liquidity_avg_volume_20d": 1000000.0,
                "volume_momentum_ratio_1d_20d": 1.0,
                "volume_momentum_ratio_5d": 1.0,
            }
        )
    return pd.DataFrame(rows)
