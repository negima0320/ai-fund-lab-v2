from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.training import (
    BLOCKED_BY_LEAKAGE_AUDIT,
    READY_FOR_PHASE5F_INFERENCE,
    TARGET_LABEL,
    TRAINING_COMPLETE_WITH_WARNINGS,
    audit_opportunity_training_dataset,
    train_opportunity_model,
)


def test_phase5e_trains_model_and_writes_metrics_audit_and_artifact(tmp_path: Path) -> None:
    dataset_path = tmp_path / "opportunity_dataset.parquet"
    _dataset_frame().to_parquet(dataset_path, index=False)

    result = train_opportunity_model(
        dataset_path=dataset_path,
        model_dir=tmp_path / "models",
        report_dir=tmp_path / "reports",
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.metrics["status"] == "OK"
    assert result.metrics["readiness_status"] in {READY_FOR_PHASE5F_INFERENCE, TRAINING_COMPLETE_WITH_WARNINGS}
    assert result.metrics["training_executed"] is True
    assert result.metrics["target_label"] == TARGET_LABEL
    assert result.audit["leakage_audit_status"] == "OK"
    assert result.audit["model_trained"] is True
    assert Path(result.metrics["model_artifact_path"]).is_file()
    assert Path(result.metrics["metrics_path"]).is_file()
    assert Path(result.metrics["audit_path"]).is_file()
    assert result.metrics["train_rows"] > 0
    assert result.metrics["validation_rows"] > 0
    assert result.metrics["test_rows"] > 0


def test_phase5e_uses_only_feature_columns_and_blocks_future_feature_leakage() -> None:
    dataset = _dataset_frame()
    dataset["feature__future_return_20d"] = 0.99
    feature_columns = sorted(column for column in dataset.columns if column.startswith("feature__"))
    label_columns = sorted(column for column in dataset.columns if column.startswith("label__"))

    audit = audit_opportunity_training_dataset(
        dataset,
        feature_columns=feature_columns,
        label_columns=label_columns,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert audit["leakage_audit_status"] == "ERROR"
    assert audit["future_feature_column_count"] == 1
    assert audit["readiness_status"] == BLOCKED_BY_LEAKAGE_AUDIT


def test_phase5e_keeps_feature_and_label_columns_separated(tmp_path: Path) -> None:
    dataset_path = tmp_path / "opportunity_dataset.parquet"
    _dataset_frame().to_parquet(dataset_path, index=False)

    result = train_opportunity_model(
        dataset_path=dataset_path,
        model_dir=tmp_path / "models",
        report_dir=tmp_path / "reports",
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert "label__future_return_20d" in result.metrics["label_columns"]
    assert "label__future_return_20d" not in result.metrics["feature_columns"]
    assert all(column.startswith("feature__") for column in result.metrics["feature_columns"])
    assert result.audit["feature_label_columns_separated"] is True


def test_phase5e_evaluates_candidate_top50_against_opportunity_topn(tmp_path: Path) -> None:
    dataset_path = tmp_path / "opportunity_dataset.parquet"
    _dataset_frame().to_parquet(dataset_path, index=False)

    result = train_opportunity_model(
        dataset_path=dataset_path,
        model_dir=tmp_path / "models",
        report_dir=tmp_path / "reports",
        created_at="2026-06-14T00:00:00+00:00",
    )

    validation = result.metrics["ranking_metrics"]["validation"]
    model_top5 = validation["rankers"]["model"]["top5"]
    candidate_average = validation["candidate_top50_average"]
    assert "selected_mean_future_return" in model_top5
    assert "selected_mean_future_max_return" in model_top5
    assert "selected_top_decile_rate" in model_top5
    assert "selected_downside_bad_rate" in model_top5
    assert "selected_mean_future_max_drawdown" in model_top5
    assert "win_rate_20d" in model_top5
    assert candidate_average["selected_row_count"] == result.metrics["validation_rows"]
    assert "candidate_score_baseline" in validation["rankers"]
    assert "simple_rule_baseline" in validation["rankers"]


def test_phase5e_metrics_do_not_include_portfolio_performance_terms(tmp_path: Path) -> None:
    dataset_path = tmp_path / "opportunity_dataset.parquet"
    _dataset_frame().to_parquet(dataset_path, index=False)

    result = train_opportunity_model(
        dataset_path=dataset_path,
        model_dir=tmp_path / "models",
        report_dir=tmp_path / "reports",
        created_at="2026-06-14T00:00:00+00:00",
    )

    payload = json.dumps(result.metrics, sort_keys=True)
    assert "annual_return" not in payload
    assert "final_assets" not in payload
    assert "profit_factor" not in payload
    assert "portfolio_drawdown" not in payload


def _dataset_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    split_dates = {
        "train": ["2024-10-31", "2024-11-29", "2024-12-30"],
        "validation": ["2025-06-30", "2025-07-31"],
        "test": ["2026-02-27", "2026-03-31"],
    }
    for split, dates in split_dates.items():
        for date_index, target_date in enumerate(dates):
            for rank in range(1, 13):
                code = f"{date_index + 1}{rank:03d}"
                momentum = (13 - rank) / 100.0
                volatility = rank / 200.0
                future_return = 0.12 - rank * 0.012 + (date_index * 0.002)
                future_max_return = max(0.02, 0.18 - rank * 0.01)
                future_max_drawdown = -0.01 * rank
                downside_bad = future_max_drawdown <= -0.10 or future_return <= -0.05
                expected_edge = (
                    0.60 * future_return
                    + 0.30 * future_max_return
                    - 0.30 * abs(future_max_drawdown)
                    - 0.20 * float(downside_bad)
                )
                rows.append(
                    {
                        "target_date": target_date,
                        "as_of_date": target_date,
                        "code": code,
                        "dataset_version": "opportunity_dataset_v1",
                        "feature_version": "opportunity_feature_v1",
                        "label_version": "opportunity_label_v1",
                        "split": split,
                        "created_at": "2026-06-14T00:00:00+00:00",
                        "feature__candidate_score": 1.0 - rank / 20.0,
                        "feature__candidate_rank": rank,
                        "feature__candidate_reason": "price_momentum_positive" if rank <= 6 else "liquidity_available",
                        "feature__price_momentum_return_20d": momentum,
                        "feature__price_momentum_return_60d": momentum * 1.5,
                        "feature__trend_close_over_ma_20d": momentum / 2,
                        "feature__trend_ma_20_60_ratio": 1.0 + momentum,
                        "feature__liquidity_avg_volume_20d": 1000000.0 + rank * 1000.0,
                        "feature__volatility_return_std_20d": volatility,
                        "feature__volume_momentum_ratio_1d_20d": 1.0 + rank / 20.0,
                        "feature__missing_flags_price": False,
                        "label__expected_edge_label_20d": expected_edge,
                        "label__risk_adjusted_future_return_20d": expected_edge,
                        "label__future_return_20d": future_return,
                        "label__future_max_return_20d": future_max_return,
                        "label__future_max_drawdown_20d": future_max_drawdown,
                        "label__downside_bad_20d": downside_bad,
                        "label__top_decile_20d": rank <= 2,
                    }
                )
    return pd.DataFrame(rows)
