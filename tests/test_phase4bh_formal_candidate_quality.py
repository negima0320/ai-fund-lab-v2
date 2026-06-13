from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from scripts.audit_phase4bh_formal_candidate_quality import (
    PHASE4_COMPLETE,
    PHASE4_COMPLETE_WITH_IMPROVEMENT,
    audit_phase4bh_formal_candidate_quality,
    evaluate_split,
    judge_candidate_quality,
    score_correlations,
    score_decile_report,
)


def test_phase4bh_runs_candidate_quality_audit(tmp_path: Path) -> None:
    bf_summary, bg_summary, top50 = _prepare_fixture(tmp_path)

    summary = audit_phase4bh_formal_candidate_quality(
        report_dir=tmp_path / "reports",
        phase4bf_summary_path=bf_summary,
        phase4bg_summary_path=bg_summary,
        phase4bg_top50_path=top50,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] in {PHASE4_COMPLETE, PHASE4_COMPLETE_WITH_IMPROVEMENT}
    assert summary["candidate_quality_audit_executed"] is True
    assert summary["validation_top50_top_decile_rate"] > summary["validation_market_baseline"]["top_decile_rate"]
    assert summary["test_top50_top_decile_rate"] > summary["test_market_baseline"]["top_decile_rate"]
    assert summary["candidate_quality_pass"] is True
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    assert summary["broker_api_called"] is False
    assert summary["order_executed"] is False


def test_phase4bh_evaluate_split_topk_and_baselines() -> None:
    frame = _quality_frame("validation", 100)
    scores = np.linspace(0.01, 0.99, len(frame))

    result = evaluate_split(frame, scores)

    assert result["top_50"]["row_count"] == 50
    assert result["top_50"]["top_decile_rate"] >= result["market_baseline"]["top_decile_rate"]
    assert "top_50" in result["random_baseline"]


def test_phase4bh_decile_and_correlations() -> None:
    frame = _quality_frame("test", 100)
    scores = np.linspace(0.01, 0.99, len(frame))

    deciles = score_decile_report(frame, scores)
    corr = score_correlations(frame, scores)

    assert len(deciles) == 10
    assert corr["future_max_return_20d"] is not None


def test_phase4bh_quality_judgement_with_weaknesses() -> None:
    validation = {
        "market_baseline": {"top_decile_rate": 0.1, "mean_future_max_return_20d": 0.05, "downside_bad_rate": 0.2},
        "top_50": {"top_decile_rate": 0.2, "mean_future_max_return_20d": 0.1, "downside_bad_rate": 0.3},
    }
    test = {
        "market_baseline": {"top_decile_rate": 0.1, "mean_future_max_return_20d": 0.05, "downside_bad_rate": 0.2},
        "top_50": {"top_decile_rate": 0.2, "mean_future_max_return_20d": 0.1, "downside_bad_rate": 0.3},
    }

    result = judge_candidate_quality(validation, test, {"status": "OK"})

    assert result["candidate_quality_pass"] is True
    assert result["readiness_status"] == PHASE4_COMPLETE_WITH_IMPROVEMENT
    assert result["weaknesses"]


def test_phase4bh_report_written_after_real_or_fixture_run(tmp_path: Path) -> None:
    bf_summary, bg_summary, top50 = _prepare_fixture(tmp_path)
    audit_phase4bh_formal_candidate_quality(
        report_dir=tmp_path / "reports",
        phase4bf_summary_path=bf_summary,
        phase4bg_summary_path=bg_summary,
        phase4bg_top50_path=top50,
    )

    report = Path("docs/phase_reports/phase4bh_formal_candidate_quality_audit.md").read_text(encoding="utf-8")

    assert "Formal Candidate Quality Audit" in report
    assert "No retraining" in report
    assert "No retraining, feature addition" in report


def _prepare_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    runtime_dir = tmp_path / "runtime"
    model_dir = runtime_dir / "candidate_ai" / "models"
    dataset_dir = runtime_dir / "candidate_ai" / "datasets"
    model_dir.mkdir(parents=True)
    dataset_dir.mkdir(parents=True)
    feature_columns = ["feature__signal", "feature__noise"]
    dataset = pd.concat([_quality_frame("validation", 240), _quality_frame("test", 240)], ignore_index=True)
    dataset_path = dataset_dir / "dataset.parquet"
    dataset.to_parquet(dataset_path, index=False)
    model = LogisticRegression(random_state=42).fit(dataset[feature_columns].to_numpy(), dataset["label__momentum_candidate_label"].astype(int).to_numpy())
    model_path = model_dir / "model.pkl"
    with model_path.open("wb") as handle:
        pickle.dump(
            {
                "model": model,
                "feature_columns": feature_columns,
                "dataset_path": str(dataset_path),
                "model_type": "sklearn.LogisticRegression",
            },
            handle,
        )
    bf_summary = tmp_path / "bf.json"
    bg_summary = tmp_path / "bg.json"
    top50 = tmp_path / "top50.json"
    bf_summary.write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_FORMAL_CANDIDATE_INFERENCE",
                "model_artifact_path": str(model_path),
            }
        ),
        encoding="utf-8",
    )
    bg_summary.write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_FORMAL_CANDIDATE_QUALITY_AUDIT",
                "target_date": "2026-06-12",
            }
        ),
        encoding="utf-8",
    )
    top50.write_text(json.dumps({"rows": [{"code": str(index), "candidate_rank": index + 1} for index in range(50)]}), encoding="utf-8")
    return bf_summary, bg_summary, top50


def _quality_frame(split: str, rows: int) -> pd.DataFrame:
    indices = np.arange(rows)
    signal = indices >= rows // 2
    top = indices >= int(rows * 0.9)
    return pd.DataFrame(
        {
            "split": split,
            "feature__signal": indices / rows,
            "feature__noise": (indices % 7) / 7,
            "label__future_return_5d": np.where(signal, 0.02, -0.01),
            "label__future_return_10d": np.where(signal, 0.03, -0.01),
            "label__future_return_20d": np.where(signal, 0.05, -0.02),
            "label__future_max_return_20d": np.where(signal, 0.12, 0.03),
            "label__future_max_drawdown_20d": np.where(signal, -0.03, -0.08),
            "label__top_decile_20d": top,
            "label__downside_bad_20d": ~signal,
            "label__momentum_candidate_label": signal,
        }
    )
