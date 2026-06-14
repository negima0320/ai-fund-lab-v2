from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.dataset_builder import (
    BLOCKED_BY_LEAKAGE_AUDIT,
    READY_FOR_OPPORTUNITY_TRAINING,
    assign_time_series_split,
    build_opportunity_dataset,
    build_opportunity_dataset_frame,
)


def test_phase5d_builds_dataset_and_separates_feature_and_label_columns() -> None:
    result = build_opportunity_dataset_frame(
        candidate_frame=_candidate_frame(),
        feature_frame=_feature_frame(),
        label_frame=_label_frame(),
        created_at="2026-06-14T00:00:00+00:00",
    )

    dataset = result.dataset
    assert result.summary["readiness_status"] == READY_FOR_OPPORTUNITY_TRAINING
    assert result.summary["joined_row_count"] == 3
    assert result.audit["leakage_audit_status"] == "OK"
    assert "feature__return_20d" in dataset.columns
    assert "label__future_return_20d" in dataset.columns
    assert "future_return_20d" not in dataset.columns
    assert "feature__future_return_20d" not in dataset.columns
    assert result.audit["feature_label_columns_separated"] is True


def test_phase5d_blocks_for_forbidden_feature_columns() -> None:
    features = _feature_frame()
    features["trade_result"] = 1.0

    result = build_opportunity_dataset_frame(
        candidate_frame=_candidate_frame(),
        feature_frame=features,
        label_frame=_label_frame(),
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.summary["readiness_status"] == BLOCKED_BY_LEAKAGE_AUDIT
    assert result.audit["trade_result_column_in_feature_count"] == 1
    assert "feature__trade_result" in result.audit["forbidden_feature_columns"]


def test_phase5d_filters_future_columns_out_of_feature_columns() -> None:
    features = _feature_frame()
    features["future_return_20d"] = 0.99

    result = build_opportunity_dataset_frame(
        candidate_frame=_candidate_frame(),
        feature_frame=features,
        label_frame=_label_frame(),
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.audit["leakage_audit_status"] == "OK"
    assert "feature__future_return_20d" not in result.dataset.columns
    assert "label__future_return_20d" in result.dataset.columns


def test_phase5d_join_uses_target_date_and_code() -> None:
    labels = _label_frame()
    labels.loc[labels["code"] == "6758", "code"] = "9999"

    result = build_opportunity_dataset_frame(
        candidate_frame=_candidate_frame(),
        feature_frame=_feature_frame(),
        label_frame=labels,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.summary["joined_row_count"] == 2
    assert set(result.dataset["code"]) == {"7203", "9984"}


def test_phase5d_split_is_target_date_based() -> None:
    assert assign_time_series_split("2024-12-31") == "train"
    assert assign_time_series_split("2025-01-01") == "validation"
    assert assign_time_series_split("2026-01-01") == "test"

    result = build_opportunity_dataset_frame(
        candidate_frame=_candidate_frame(),
        feature_frame=_feature_frame(),
        label_frame=_label_frame(),
        created_at="2026-06-14T00:00:00+00:00",
    )

    split_by_date = result.dataset[["target_date", "split"]].drop_duplicates()
    assert split_by_date["target_date"].value_counts().max() == 1


def test_phase5d_writes_parquet_summary_and_audit(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.parquet"
    feature_path = tmp_path / "feature.parquet"
    label_path = tmp_path / "label.parquet"
    _candidate_frame().to_parquet(candidate_path, index=False)
    _feature_frame().to_parquet(feature_path, index=False)
    _label_frame().to_parquet(label_path, index=False)

    summary = build_opportunity_dataset(
        candidate_path=candidate_path,
        feature_path=feature_path,
        label_path=label_path,
        output_dir=tmp_path / "out",
    )

    assert summary["readiness_status"] == READY_FOR_OPPORTUNITY_TRAINING
    assert Path(summary["dataset_output_path"]).is_file()
    assert Path(summary["summary_path"]).is_file()
    assert Path(summary["audit_path"]).is_file()


def _candidate_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2024-12-30", "code": "7203", "candidate_score": 0.8, "candidate_rank": 1, "candidate_reason": "high_candidate_score"},
            {"target_date": "2025-06-02", "code": "6758", "candidate_score": 0.7, "candidate_rank": 2, "candidate_reason": "price_momentum_positive"},
            {"target_date": "2026-02-02", "code": "9984", "candidate_score": 0.6, "candidate_rank": 3, "candidate_reason": "liquidity_available"},
        ]
    )


def _feature_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _feature_row("2024-12-30", "7203", 0.10),
            _feature_row("2025-06-02", "6758", 0.20),
            _feature_row("2026-02-02", "9984", 0.30),
        ]
    )


def _feature_row(target_date: str, code: str, return_20d: float) -> dict[str, object]:
    return {
        "target_date": target_date,
        "as_of_date": target_date,
        "code": code,
        "feature_version": "opportunity_feature_v1",
        "return_20d": return_20d,
        "volume_ratio_5d": 1.2,
        "close_over_ma20": 0.05,
        "avg_trading_value_20d": 1000000.0,
    }


def _label_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2024-12-30", "code": "7203", "label_version": "lv", "future_return_20d": 0.10, "future_max_return_20d": 0.20, "future_max_drawdown_20d": -0.03},
            {"target_date": "2025-06-02", "code": "6758", "label_version": "lv", "future_return_20d": -0.06, "future_max_return_20d": 0.10, "future_max_drawdown_20d": -0.12},
            {"target_date": "2026-02-02", "code": "9984", "label_version": "lv", "future_return_20d": 0.04, "future_max_return_20d": 0.15, "future_max_drawdown_20d": -0.02},
        ]
    )
