from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.inference import OUTPUT_COLUMNS
from ai_fund_lab_v2.opportunity_ai.quality_audit import (
    READY_FOR_PHASE5H_COMBINED_VALIDATION,
    audit_latest_inference_schema,
    audit_opportunity_quality,
)


class DummyQualityModel:
    def predict(self, x_input: np.ndarray) -> np.ndarray:
        return x_input[:, 0] * 0.8 + x_input[:, 1] * 0.2


def test_phase5g_audits_quality_and_writes_outputs(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)

    result = audit_opportunity_quality(
        dataset_path=paths["dataset"],
        model_path=paths["model"],
        latest_inference_path=paths["latest"],
        latest_inference_summary_path=paths["latest_summary"],
        latest_inference_audit_path=paths["latest_audit"],
        output_dir=tmp_path / "out",
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.metrics["readiness_status"] == READY_FOR_PHASE5H_COMBINED_VALIDATION
    assert result.metrics["promotion_ready"] is False
    assert result.audit["promotion_ready"] is False
    assert result.audit["leakage_status"] == "OK"
    assert result.audit["latest_inference_schema_status"] == "OK"
    assert result.audit["latest_inference_top5_count"] == 5
    assert result.audit["latest_inference_top10_count"] == 10
    assert result.audit["latest_inference_top20_count"] == 20
    assert Path(result.metrics["metrics_path"]).is_file()
    assert Path(result.metrics["audit_path"]).is_file()
    assert Path(result.metrics["by_split_path"]).is_file()


def test_phase5g_generates_topn_metrics_and_candidate_baseline_comparison(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)

    result = audit_opportunity_quality(
        dataset_path=paths["dataset"],
        model_path=paths["model"],
        latest_inference_path=paths["latest"],
        latest_inference_summary_path=paths["latest_summary"],
        latest_inference_audit_path=paths["latest_audit"],
        output_dir=tmp_path / "out",
        created_at="2026-06-14T00:00:00+00:00",
    )

    validation = result.metrics["quality_metrics"]["validation"]
    assert "candidate_top50_average" in validation
    assert "candidate_score_baseline" in validation["rankers"]
    assert "model" in validation["rankers"]
    assert "top5" in validation["rankers"]["model"]
    assert "selected_mean_future_return" in validation["rankers"]["model"]["top5"]
    assert "model_minus_candidate_score_mean_future_return" in result.metrics["model_vs_baseline_lift"]["test"]["top10"]
    assert set(result.by_split["selection"]).issuperset({"average", "top5", "top10", "top20"})


def test_phase5g_latest_inference_schema_fails_when_topn_counts_wrong() -> None:
    latest = _latest_inference_frame()
    latest["is_top5"] = False
    latest_summary = {"label_table_read_flag": False}
    latest_audit = {
        "leakage_audit_status": "OK",
        "future_feature_column_count": 0,
        "forbidden_feature_column_count": 0,
        "trade_result_feature_column_count": 0,
        "portfolio_feature_column_count": 0,
        "backtest_feature_column_count": 0,
        "ai_output_leakage_column_count": 0,
    }

    audit = audit_latest_inference_schema(latest, latest_summary=latest_summary, latest_audit=latest_audit)

    assert audit["schema_status"] == "ERROR"
    assert audit["top5_count"] == 0


def test_phase5g_metrics_do_not_include_portfolio_performance_terms(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)

    result = audit_opportunity_quality(
        dataset_path=paths["dataset"],
        model_path=paths["model"],
        latest_inference_path=paths["latest"],
        latest_inference_summary_path=paths["latest_summary"],
        latest_inference_audit_path=paths["latest_audit"],
        output_dir=tmp_path / "out",
        created_at="2026-06-14T00:00:00+00:00",
    )

    payload = json.dumps(result.metrics, sort_keys=True)
    assert "annual_return" not in payload
    assert "final_assets" not in payload
    assert "profit_factor" not in payload
    assert "portfolio_drawdown" not in payload


def _write_inputs(tmp_path: Path) -> dict[str, Path]:
    dataset = tmp_path / "dataset.parquet"
    model = tmp_path / "model.pkl"
    latest = tmp_path / "latest.parquet"
    latest_summary = tmp_path / "latest_summary.json"
    latest_audit = tmp_path / "latest_audit.json"
    _dataset_frame().to_parquet(dataset, index=False)
    _write_model(model)
    _latest_inference_frame().to_parquet(latest, index=False)
    latest_summary.write_text(json.dumps({"label_table_read_flag": False, "promotion_ready": False}), encoding="utf-8")
    latest_audit.write_text(
        json.dumps(
            {
                "leakage_audit_status": "OK",
                "future_feature_column_count": 0,
                "forbidden_feature_column_count": 0,
                "trade_result_feature_column_count": 0,
                "portfolio_feature_column_count": 0,
                "backtest_feature_column_count": 0,
                "ai_output_leakage_column_count": 0,
            }
        ),
        encoding="utf-8",
    )
    return {
        "dataset": dataset,
        "model": model,
        "latest": latest,
        "latest_summary": latest_summary,
        "latest_audit": latest_audit,
    }


def _write_model(path: Path) -> None:
    payload = {
        "model_version": "fixture_quality_model",
        "model": DummyQualityModel(),
        "feature_columns": ["feature__candidate_score", "feature__price_momentum_return_20d"],
        "preprocessing": {
            "categorical_maps": {},
            "medians": {
                "feature__candidate_score": 0.0,
                "feature__price_momentum_return_20d": 0.0,
            },
            "boolean_columns": [],
        },
        "simple_rule_baseline": {
            "columns": ["feature__price_momentum_return_20d"],
            "weights": {"feature__price_momentum_return_20d": 1.0},
            "stats": {"feature__price_momentum_return_20d": {"mean": 0.0, "std": 1.0}},
        },
    }
    with path.open("wb") as handle:
        pickle.dump(payload, handle)


def _dataset_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for split, dates in {"validation": ["2025-01-31", "2025-02-28"], "test": ["2026-01-30", "2026-02-27"]}.items():
        for target_date in dates:
            for rank in range(1, 26):
                future_return = 0.14 - rank * 0.01
                future_max_return = 0.20 - rank * 0.006
                future_max_drawdown = -0.005 * rank
                downside_bad = rank >= 20
                rows.append(
                    {
                        "target_date": target_date,
                        "as_of_date": target_date,
                        "code": f"{rank:04d}",
                        "split": split,
                        "feature__candidate_score": 1.0 - rank / 100.0,
                        "feature__candidate_rank": rank,
                        "feature__candidate_reason": "fixture",
                        "feature__price_momentum_return_20d": (26 - rank) / 100.0,
                        "feature__volatility_return_std_20d": rank / 1000.0,
                        "label__expected_edge_label_20d": 0.5 * future_return + 0.3 * future_max_return - 0.2 * abs(future_max_drawdown),
                        "label__future_return_20d": future_return,
                        "label__future_max_return_20d": future_max_return,
                        "label__future_max_drawdown_20d": future_max_drawdown,
                        "label__downside_bad_20d": downside_bad,
                        "label__top_decile_20d": rank <= 3,
                    }
                )
    return pd.DataFrame(rows)


def _latest_inference_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for rank in range(1, 26):
        row = {
            "target_date": "2026-06-12",
            "code": f"{rank:04d}",
            "expected_edge_score": 1.0 - rank / 100.0,
            "buy_rank": rank,
            "expected_return_horizon": "20d",
            "downside_risk_score": rank / 100.0,
            "buy_reason": "fixture",
            "no_buy_reason": "",
            "candidate_score": 1.0 - rank / 100.0,
            "candidate_rank": rank,
            "model_version": "fixture_quality_model",
            "feature_version": "fixture_feature",
            "inference_run_id": "fixture_run",
            "created_at": "2026-06-14T00:00:00+00:00",
            "is_top5": rank <= 5,
            "is_top10": rank <= 10,
            "is_top20": rank <= 20,
        }
        assert set(OUTPUT_COLUMNS).issubset(row)
        rows.append(row)
    return pd.DataFrame(rows)
