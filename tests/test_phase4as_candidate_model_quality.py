from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from scripts.analyze_phase4as_candidate_model_quality import (
    BLOCKED_DATASET,
    BLOCKED_MODEL,
    READY,
    analyze_feature_stats,
    analyze_phase4as_candidate_model_quality,
    extract_feature_importance,
    extract_tree_stats,
    prediction_stats,
)


def test_phase4as_analyzes_model_quality(tmp_path: Path) -> None:
    ao_summary, ap_summary, aq_summary, ar_summary = _prepare_fixture(tmp_path)

    summary = analyze_phase4as_candidate_model_quality(
        phase4ao_summary_path=ao_summary,
        phase4ap_summary_path=ap_summary,
        phase4aq_summary_path=aq_summary,
        phase4ar_summary_path=ar_summary,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["root_cause_analysis_executed"] is True
    assert summary["dataset_row_count"] == 40
    assert summary["smoke_train_row_count"] > 0
    assert summary["smoke_validation_row_count"] > 0
    assert summary["feature_column_count"] == 3
    assert summary["feature_importance_nonzero_count"] > 0
    assert summary["train_prediction_unique_count"] > 1
    assert summary["validation_prediction_unique_count"] > 1
    assert summary["latest_prediction_unique_count"] == 1
    assert summary["all_same_score_direct_cause"]
    assert summary["likely_root_causes"]
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False


def test_phase4as_blocks_missing_model(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps({"rows": []}), encoding="utf-8")
    ao_summary = tmp_path / "ao.json"
    ap_summary = tmp_path / "ap.json"
    aq_summary = tmp_path / "aq.json"
    ar_summary = tmp_path / "ar.json"
    ao_summary.write_text(json.dumps({"dataset_output_path": str(dataset_path)}), encoding="utf-8")
    ap_summary.write_text(json.dumps({"model_artifact_path": str(tmp_path / "missing.pkl")}), encoding="utf-8")
    aq_summary.write_text(json.dumps({}), encoding="utf-8")
    ar_summary.write_text(json.dumps({}), encoding="utf-8")

    summary = analyze_phase4as_candidate_model_quality(
        phase4ao_summary_path=ao_summary,
        phase4ap_summary_path=ap_summary,
        phase4aq_summary_path=aq_summary,
        phase4ar_summary_path=ar_summary,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["readiness_status"] == BLOCKED_MODEL


def test_phase4as_blocks_missing_dataset(tmp_path: Path) -> None:
    model_path, manifest_path = _write_model(tmp_path)
    ao_summary = tmp_path / "ao.json"
    ap_summary = tmp_path / "ap.json"
    aq_summary = tmp_path / "aq.json"
    ar_summary = tmp_path / "ar.json"
    ao_summary.write_text(json.dumps({"dataset_output_path": str(tmp_path / "missing.json")}), encoding="utf-8")
    ap_summary.write_text(
        json.dumps({"model_artifact_path": str(model_path), "model_manifest_path": str(manifest_path)}),
        encoding="utf-8",
    )
    aq_summary.write_text(json.dumps({}), encoding="utf-8")
    ar_summary.write_text(json.dumps({}), encoding="utf-8")

    summary = analyze_phase4as_candidate_model_quality(
        phase4ao_summary_path=ao_summary,
        phase4ap_summary_path=ap_summary,
        phase4aq_summary_path=aq_summary,
        phase4ar_summary_path=ar_summary,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["readiness_status"] == BLOCKED_DATASET


def test_phase4as_feature_stats_detect_constant_and_null() -> None:
    rows = [
        {"feature__a": 1.0, "feature__b": None, "feature__c": 1.0},
        {"feature__a": 1.0, "feature__b": None, "feature__c": 2.0},
        {"feature__a": 1.0, "feature__b": 3.0, "feature__c": 3.0},
    ]

    stats = analyze_feature_stats(rows, ["feature__a", "feature__b", "feature__c"])

    assert stats["constant_feature_count"] == 2
    assert stats["high_null_feature_count"] == 1


def test_phase4as_importance_and_prediction_stats() -> None:
    model = LogisticRegression(random_state=42).fit(
        np.asarray([[0, 0], [1, 1], [2, 2], [3, 3]], dtype=float),
        np.asarray([0, 0, 1, 1], dtype=int),
    )

    importance = extract_feature_importance(model, ["feature__a", "feature__b"])
    tree_stats = extract_tree_stats(model)
    pred_stats = prediction_stats(np.asarray([0.1, 0.1, 0.2]))

    assert importance["feature_importance_nonzero_count"] == 2
    assert tree_stats["effective_split_count"] == 2
    assert pred_stats["unique_count"] == 2


def test_phase4as_report_exists_after_analysis(tmp_path: Path) -> None:
    ao_summary, ap_summary, aq_summary, ar_summary = _prepare_fixture(tmp_path)
    analyze_phase4as_candidate_model_quality(
        phase4ao_summary_path=ao_summary,
        phase4ap_summary_path=ap_summary,
        phase4aq_summary_path=aq_summary,
        phase4ar_summary_path=ar_summary,
        summary_path=tmp_path / "summary.json",
    )

    report = Path("docs/phase_reports/phase4as_candidate_model_quality_root_cause.md").read_text(encoding="utf-8")
    assert "Phase4-AS" in report
    assert "Root Cause" in report
    assert "does not" in report


def _prepare_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    model_path, manifest_path = _write_model(tmp_path)
    dataset_path = tmp_path / "dataset.json"
    inference_path = tmp_path / "inference.json"
    dataset_path.write_text(json.dumps({"rows": [_dataset_row(index) for index in range(40)]}), encoding="utf-8")
    inference_path.write_text(
        json.dumps({"rows": [{"candidate_score": 0.1, "code": str(index)} for index in range(10)]}),
        encoding="utf-8",
    )
    ao_summary = tmp_path / "ao.json"
    ap_summary = tmp_path / "ap.json"
    aq_summary = tmp_path / "aq.json"
    ar_summary = tmp_path / "ar.json"
    ao_summary.write_text(json.dumps({"dataset_output_path": str(dataset_path)}), encoding="utf-8")
    ap_summary.write_text(
        json.dumps(
            {
                "model_artifact_path": str(model_path),
                "model_manifest_path": str(manifest_path),
                "model_type": "sklearn.LogisticRegression",
            }
        ),
        encoding="utf-8",
    )
    aq_summary.write_text(json.dumps({"inference_output_path": str(inference_path)}), encoding="utf-8")
    ar_summary.write_text(json.dumps({"all_same_score": True}), encoding="utf-8")
    return ao_summary, ap_summary, aq_summary, ar_summary


def _write_model(tmp_path: Path) -> tuple[Path, Path]:
    feature_columns = ["feature__a", "feature__b", "feature__c"]
    model = LogisticRegression(random_state=42).fit(
        np.asarray([[0, 0, 0], [1, 1, 1], [2, 2, 2], [3, 3, 3]], dtype=float),
        np.asarray([0, 0, 1, 1], dtype=int),
    )
    model_path = tmp_path / "model.pkl"
    manifest_path = tmp_path / "manifest.json"
    with model_path.open("wb") as handle:
        pickle.dump({"model": model, "model_type": "sklearn.LogisticRegression", "feature_columns": feature_columns}, handle)
    manifest_path.write_text(json.dumps({"model_type": "sklearn.LogisticRegression"}), encoding="utf-8")
    return model_path, manifest_path


def _dataset_row(index: int) -> dict[str, object]:
    positive = index % 4 == 0
    return {
        "target_date": f"2026-03-{(index // 4) + 1:02d}",
        "feature__a": float(index),
        "feature__b": float(index % 7),
        "feature__c": 1.0 if positive else 0.0,
        "label__momentum_candidate_label": positive,
    }
