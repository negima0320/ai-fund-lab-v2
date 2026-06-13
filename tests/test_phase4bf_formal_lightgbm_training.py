from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from scripts.audit_phase4bf_formal_candidate_model import run_audit
from scripts.train_phase4bf_formal_candidate_model import (
    READY,
    TARGET_LABEL,
    audit_training_features,
    calculate_formal_metrics,
    train_phase4bf_formal_candidate_model,
)


def test_phase4bf_trains_formal_model(tmp_path: Path) -> None:
    runtime_dir, be_summary = _prepare_runtime_fixture(tmp_path)

    summary = train_phase4bf_formal_candidate_model(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        phase4be_summary_path=be_summary,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["training_executed"] is True
    assert summary["formal_training"] is True
    assert summary["random_split_used"] is False
    assert summary["future_column_used_as_feature"] is False
    assert summary["label_column_used_as_feature"] is False
    assert summary["leakage_audit_status"] == "OK"
    assert summary["all_same_score"] is False
    assert summary["unique_score_count"] > 1
    assert Path(summary["model_artifact_path"]).is_file()
    assert Path(summary["model_manifest_path"]).is_file()
    assert summary["inference_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False


def test_phase4bf_feature_audit_rejects_label_feature() -> None:
    result = audit_training_features(["feature__price_momentum_return_5d", "feature__momentum_candidate_label"])

    assert result["status"] == "ERROR"
    assert result["label_column_used_as_feature"] is True


def test_phase4bf_metrics_include_top50_fields() -> None:
    frame = pd.DataFrame(
        {
            "label__top_decile_20d": [True, False, True],
            "label__downside_bad_20d": [False, False, True],
            "label__future_return_20d": [0.1, -0.1, 0.2],
            "label__future_max_return_20d": [0.15, 0.01, 0.25],
        }
    )
    y = pd.Series([1, 0, 1]).to_numpy()
    scores = pd.Series([0.9, 0.1, 0.8]).to_numpy()

    metrics = calculate_formal_metrics(frame, y, scores)

    assert metrics["precision_at_top_50"] > 0
    assert "candidate_top_decile_rate_at_top_50" in metrics
    assert "candidate_mean_future_return_20d_at_top_50" in metrics


def test_phase4bf_audit_completes(tmp_path: Path) -> None:
    runtime_dir, be_summary = _prepare_runtime_fixture(tmp_path)
    summary_path = tmp_path / "reports" / "phase4bf_formal_lightgbm_training_summary.json"
    train_phase4bf_formal_candidate_model(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        phase4be_summary_path=be_summary,
    )

    result = run_audit(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        summary_path=summary_path,
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "complete"
    assert result["readiness_status"] == READY


def test_phase4bf_report_documents_scope() -> None:
    report = Path("docs/phase_reports/phase4bf_formal_lightgbm_training.md").read_text(encoding="utf-8")

    assert "READY_FOR_FORMAL_CANDIDATE_INFERENCE" in report
    assert "Phase4-BG" in report
    assert "inference_executed: `False`" in report
    assert "backtest_executed: `False`" in report


def _prepare_runtime_fixture(tmp_path: Path) -> tuple[Path, Path]:
    runtime_dir = tmp_path / "runtime"
    rows = _dataset_rows()
    dataset_path = runtime_dir / "candidate_ai" / "datasets" / "phase4be_dataset.parquet"
    dataset_path.parent.mkdir(parents=True)
    pd.DataFrame(rows).to_parquet(dataset_path, index=False)
    be_summary = tmp_path / "phase4be.json"
    be_summary.write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_FORMAL_LIGHTGBM_TRAINING",
                "dataset_output_path": str(dataset_path),
                "joined_row_count": len(rows),
            }
        ),
        encoding="utf-8",
    )
    return runtime_dir, be_summary


def _dataset_rows() -> list[dict[str, object]]:
    dates = _business_dates(date(2021, 9, 9), 1260)
    rows: list[dict[str, object]] = []
    for code_index, code in enumerate(("7203", "6758", "9984"), start=1):
        for index, target_date in enumerate(dates, start=1):
            split = "train" if target_date <= "2024-12-31" else "validation" if target_date <= "2025-12-31" else "test"
            signal = (index + code_index) % 11 == 0 or code == "9984"
            rows.append(
                {
                    "target_date": target_date,
                    "as_of_date": target_date,
                    "code": code,
                    "dataset_version": "fixture",
                    "feature_version": "fixture",
                    "label_version": "fixture",
                    "split": split,
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "feature__price_momentum_return_5d": 1.0 if signal else 0.0,
                    "feature__price_momentum_return_20d": index / 1000.0,
                    "feature__price_momentum_return_60d": code_index / 10.0,
                    "feature__missing_flags_insufficient_history": False,
                    "label__future_return_5d": 0.03 if signal else -0.01,
                    "label__future_return_10d": 0.04 if signal else -0.01,
                    "label__future_return_20d": 0.05 if signal else -0.02,
                    "label__future_max_return_20d": 0.08 if signal else 0.01,
                    "label__future_max_drawdown_20d": -0.02 if signal else -0.08,
                    "label__top_decile_20d": bool(signal),
                    "label__downside_bad_20d": False,
                    TARGET_LABEL: bool(signal),
                }
            )
    return rows


def _business_dates(start: date, count: int) -> list[str]:
    values: list[str] = []
    current = start
    while len(values) < count:
        if current.weekday() < 5:
            values.append(current.isoformat())
        current += timedelta(days=1)
    return values
