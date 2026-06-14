from __future__ import annotations

import json
import pickle
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.full_history_expansion import (
    READY_FOR_PHASE5J_MODEL_IMPROVEMENT_OR_CALIBRATION,
    compare_monthly_and_full_history,
    lift_status,
    run_full_history_expansion,
    top10_status,
)


def test_phase5i_orchestrates_full_history_outputs(monkeypatch, tmp_path: Path) -> None:
    inputs = _write_input_files(tmp_path)
    output_dir = tmp_path / "phase5i"

    def fake_candidates(**kwargs):
        out = Path(kwargs["output_dir"])
        out.mkdir(parents=True, exist_ok=True)
        path = out / "historical_candidate_top50.parquet"
        pd.DataFrame(
            [
                {"target_date": "2026-01-30", "code": "1000", "candidate_score": 0.9, "candidate_rank": 1},
                {"target_date": "2026-01-31", "code": "1001", "candidate_score": 0.8, "candidate_rank": 1},
            ]
        ).to_parquet(path, index=False)
        return {
            "status": "OK",
            "readiness_status": "READY_FOR_PHASE5D_DATASET",
            "target_date_count": 2,
            "candidate_rows": 2,
            "label_join_coverage_rate": 1.0,
            "candidate_output_path": str(path),
        }

    def fake_dataset(**kwargs):
        out = Path(kwargs["output_dir"])
        out.mkdir(parents=True, exist_ok=True)
        path = out / "opportunity_dataset.parquet"
        pd.DataFrame([{"target_date": "2026-01-30", "code": "1000"}]).to_parquet(path, index=False)
        return {
            "status": "OK",
            "readiness_status": "READY_FOR_OPPORTUNITY_TRAINING",
            "joined_row_count": 2,
            "train_row_count": 1,
            "validation_row_count": 1,
            "test_row_count": 1,
            "leakage_audit_status": "OK",
            "dataset_output_path": str(path),
        }

    def fake_train(**kwargs):
        model_dir = Path(kwargs["model_dir"])
        report_dir = Path(kwargs["report_dir"])
        model_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "opportunity_model.pkl"
        metrics_path = report_dir / "opportunity_training_metrics.json"
        with model_path.open("wb") as handle:
            pickle.dump({"model": "fixture"}, handle)
        metrics = {
            "status": "OK",
            "readiness_status": "TRAINING_COMPLETE_WITH_WARNINGS",
            "metrics_path": str(metrics_path),
            "model_artifact_path": str(model_path),
        }
        metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
        audit = {
            "leakage_audit_status": "OK",
            "forbidden_feature_column_count": 0,
            "future_feature_column_count": 0,
            "trade_result_feature_column_count": 0,
            "portfolio_feature_column_count": 0,
            "backtest_feature_column_count": 0,
        }
        return SimpleNamespace(metrics=metrics, audit=audit)

    def fake_quality(**kwargs):
        out = Path(kwargs["output_dir"])
        out.mkdir(parents=True, exist_ok=True)
        metrics_path = out / "opportunity_quality_metrics.json"
        metrics = {"status": "OK", "readiness_status": "READY_FOR_PHASE5H_COMBINED_VALIDATION", "metrics_path": str(metrics_path)}
        metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
        return SimpleNamespace(metrics=metrics, audit={"leakage_status": "OK"})

    def fake_combined(**kwargs):
        out = Path(kwargs["output_dir"])
        out.mkdir(parents=True, exist_ok=True)
        metrics_path = out / "combined_validation_metrics.json"
        metrics = _combined_metrics(metrics_path)
        metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
        audit = {
            "model_unique_score_count": 12,
            "model_all_same_score": False,
            "validation_test_gap_status": "OK",
        }
        return SimpleNamespace(metrics=metrics, audit=audit)

    monkeypatch.setattr("ai_fund_lab_v2.opportunity_ai.full_history_expansion.build_historical_candidate_top50", fake_candidates)
    monkeypatch.setattr("ai_fund_lab_v2.opportunity_ai.full_history_expansion.build_opportunity_dataset", fake_dataset)
    monkeypatch.setattr("ai_fund_lab_v2.opportunity_ai.full_history_expansion.train_opportunity_model", fake_train)
    monkeypatch.setattr("ai_fund_lab_v2.opportunity_ai.full_history_expansion.audit_opportunity_quality", fake_quality)
    monkeypatch.setattr("ai_fund_lab_v2.opportunity_ai.full_history_expansion.validate_candidate_opportunity_combined", fake_combined)

    result = run_full_history_expansion(
        output_dir=output_dir,
        phase4bf_summary_path=inputs["bf"],
        phase4bc_summary_path=inputs["bc"],
        phase4bd_summary_path=inputs["bd"],
        latest_inference_path=inputs["latest"],
        latest_inference_summary_path=inputs["latest_summary"],
        latest_inference_audit_path=inputs["latest_audit"],
        monthly_combined_metrics_path=inputs["monthly"],
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.metrics["readiness_status"] == READY_FOR_PHASE5J_MODEL_IMPROVEMENT_OR_CALIBRATION
    assert result.metrics["promotion_ready"] is False
    assert result.audit["target_date_count"] == 2
    assert result.audit["candidate_rows"] == 2
    assert result.audit["dataset_rows"] == 2
    assert result.audit["top5_lift_status"] == "CONFIRMED"
    assert result.audit["top10_underperformance_status"] == "PERSISTENT_BUT_INVESTIGATED"
    assert Path(result.metrics["artifact_paths"]["candidate"]).is_file()
    assert Path(result.metrics["artifact_paths"]["dataset"]).is_file()
    assert Path(result.metrics["artifact_paths"]["training_metrics"]).is_file()
    assert Path(result.metrics["artifact_paths"]["quality_metrics"]).is_file()
    assert Path(result.metrics["artifact_paths"]["combined_validation_metrics"]).is_file()
    assert Path(result.metrics["artifact_paths"]["audit"]).is_file()


def test_phase5i_compare_monthly_and_full_history() -> None:
    monthly = _combined_metrics(Path("monthly.json"))
    full = _combined_metrics(Path("full.json"))
    full["quality_metrics"]["test"]["rankers"]["model"]["top5"]["selected_mean_future_return"] = 0.07

    result = compare_monthly_and_full_history(monthly, full)

    assert result["available"] is True
    assert result["test"]["top5"]["delta_full_minus_monthly"] == 0.02


def test_phase5i_lift_and_top10_status_helpers() -> None:
    metrics = _combined_metrics(Path("combined.json"))

    assert lift_status(metrics, "top5") == "CONFIRMED"
    assert top10_status(metrics) == "PERSISTENT_BUT_INVESTIGATED"


def _write_input_files(tmp_path: Path) -> dict[str, Path]:
    model = tmp_path / "candidate_model.pkl"
    feature = tmp_path / "feature.parquet"
    label = tmp_path / "label.parquet"
    latest = tmp_path / "latest.parquet"
    latest_summary = tmp_path / "latest_summary.json"
    latest_audit = tmp_path / "latest_audit.json"
    bf = tmp_path / "bf.json"
    bc = tmp_path / "bc.json"
    bd = tmp_path / "bd.json"
    monthly = tmp_path / "monthly.json"
    with model.open("wb") as handle:
        pickle.dump({"model": "fixture", "feature_columns": ["feature__x"]}, handle)
    pd.DataFrame([{"target_date": "2026-01-30", "code": "1000"}]).to_parquet(feature, index=False)
    pd.DataFrame([{"target_date": "2026-01-30", "code": "1000"}]).to_parquet(label, index=False)
    pd.DataFrame([{"target_date": "2026-01-30", "code": "1000"}]).to_parquet(latest, index=False)
    latest_summary.write_text(json.dumps({"label_table_read_flag": False}), encoding="utf-8")
    latest_audit.write_text(json.dumps({"leakage_audit_status": "OK"}), encoding="utf-8")
    bf.write_text(json.dumps({"model_artifact_path": str(model)}), encoding="utf-8")
    bc.write_text(json.dumps({"feature_output_path": str(feature)}), encoding="utf-8")
    bd.write_text(json.dumps({"label_output_path": str(label)}), encoding="utf-8")
    monthly.write_text(json.dumps(_combined_metrics(monthly)), encoding="utf-8")
    return {
        "model": model,
        "feature": feature,
        "label": label,
        "latest": latest,
        "latest_summary": latest_summary,
        "latest_audit": latest_audit,
        "bf": bf,
        "bc": bc,
        "bd": bd,
        "monthly": monthly,
    }


def _combined_metrics(path: Path) -> dict[str, object]:
    return {
        "status": "OK",
        "readiness_status": "READY_FOR_PHASE5I_FULL_HISTORY_EXPANSION",
        "metrics_path": str(path),
        "quality_metrics": {
            "validation": {
                "candidate_top50_average": {"selected_mean_future_return": 0.01},
                "rankers": {
                    "model": {
                        "top5": {"selected_mean_future_return": 0.04},
                        "top10": {"selected_mean_future_return": 0.02},
                        "top20": {"selected_mean_future_return": 0.03},
                    }
                },
            },
            "test": {
                "candidate_top50_average": {"selected_mean_future_return": 0.01},
                "rankers": {
                    "model": {
                        "top5": {"selected_mean_future_return": 0.05},
                        "top10": {"selected_mean_future_return": 0.00},
                        "top20": {"selected_mean_future_return": 0.02},
                    }
                },
            },
        },
        "top10_underperformance_investigation": {"investigated": True},
    }
