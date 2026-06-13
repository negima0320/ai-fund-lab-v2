from __future__ import annotations

import json
import pickle
from pathlib import Path

from scripts.audit_phase4ap_candidate_smoke import run_audit
from scripts.train_phase4ap_candidate_smoke import (
    READY,
    audit_training_features,
    build_smoke_time_series_split,
    train_phase4ap_candidate_smoke,
)


def test_phase4ap_trains_smoke_model(tmp_path: Path) -> None:
    runtime_dir, ao_summary = _prepare_fixture(tmp_path)

    summary = train_phase4ap_candidate_smoke(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        phase4ao_summary_path=ao_summary,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["training_executed"] is True
    assert summary["smoke_test"] is True
    assert summary["dataset_row_count"] == 80
    assert summary["smoke_train_row_count"] > 0
    assert summary["smoke_validation_row_count"] > 0
    assert summary["feature_column_count"] == 3
    assert summary["label_column_count"] == 8
    assert summary["positive_label_count"] > 0
    assert summary["random_split_used"] is False
    assert summary["future_column_used_as_feature"] is False
    assert summary["label_column_used_as_feature"] is False
    assert summary["leakage_audit_status"] == "OK"
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    assert summary["production_model_promoted"] is False
    assert Path(summary["model_artifact_path"]).is_file()
    assert Path(summary["model_manifest_path"]).is_file()


def test_phase4ap_model_artifact_contains_feature_columns(tmp_path: Path) -> None:
    runtime_dir, ao_summary = _prepare_fixture(tmp_path)
    summary = train_phase4ap_candidate_smoke(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        phase4ao_summary_path=ao_summary,
    )

    with Path(summary["model_artifact_path"]).open("rb") as handle:
        payload = pickle.load(handle)

    assert payload["smoke_test"] is True
    assert payload["target_label"] == "label__momentum_candidate_label"
    assert payload["feature_columns"] == [
        "feature__liquidity_avg_volume_20d",
        "feature__price_momentum_return_5d",
        "feature__volume_momentum_ratio_5d",
    ]


def test_phase4ap_time_series_split_is_not_random() -> None:
    rows = [{"target_date": f"2026-03-{day:02d}"} for day in range(1, 11)]

    split = build_smoke_time_series_split(rows, train_ratio=0.7)

    assert split["train_date_min"] == "2026-03-01"
    assert split["train_date_max"] == "2026-03-07"
    assert split["validation_date_min"] == "2026-03-08"
    assert split["validation_date_max"] == "2026-03-10"


def test_phase4ap_feature_audit_rejects_label_and_future_features() -> None:
    result = audit_training_features(
        [
            "feature__price_momentum_return_5d",
            "feature__future_return_20d",
            "feature__momentum_candidate_label",
        ]
    )

    assert result["status"] == "ERROR"
    assert result["future_column_used_as_feature"] is True
    assert result["label_column_used_as_feature"] is True


def test_phase4ap_audit_completes(tmp_path: Path) -> None:
    runtime_dir, ao_summary = _prepare_fixture(tmp_path)
    summary_path = tmp_path / "reports" / "phase4ap_candidate_training_smoke_summary.json"
    train_phase4ap_candidate_smoke(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        phase4ao_summary_path=ao_summary,
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
    assert result["checks"]["random_split_not_used"] is True
    assert result["checks"]["inference_backtest_trading_not_executed"] is True


def test_phase4ap_report_documents_smoke_scope() -> None:
    report = Path("docs/phase_reports/phase4ap_candidate_training_smoke.md").read_text(encoding="utf-8")

    assert "Smoke" in report
    assert "READY_FOR_CANDIDATE_INFERENCE_SMOKE" in report
    assert "production" in report
    assert "backtest" in report


def _prepare_fixture(tmp_path: Path) -> tuple[Path, Path]:
    runtime_dir = tmp_path / "runtime"
    dataset_path = runtime_dir / "candidate_ai" / "datasets" / "dataset.json"
    dataset_path.parent.mkdir(parents=True)
    rows = []
    for day in range(1, 21):
        target_date = f"2026-03-{day:02d}"
        for index, code in enumerate(("7203", "6758", "9984", "8306")):
            positive = (day + index) % 5 == 0
            rows.append(_dataset_row(target_date, code, positive=positive))
    dataset_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    ao_summary = tmp_path / "phase4ao.json"
    ao_summary.write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_FIRST_LIGHTGBM_TRAINING",
                "dataset_output_path": str(dataset_path),
            }
        ),
        encoding="utf-8",
    )
    return runtime_dir, ao_summary


def _dataset_row(target_date: str, code: str, *, positive: bool) -> dict[str, object]:
    return {
        "target_date": target_date,
        "as_of_date": target_date,
        "code": code,
        "dataset_version": "fixture",
        "feature_version": "fixture",
        "label_version": "fixture",
        "split": "test",
        "created_at": "2026-01-01T00:00:00+00:00",
        "feature__liquidity_avg_volume_20d": 100000.0,
        "feature__price_momentum_return_5d": 0.1 if positive else -0.02,
        "feature__volume_momentum_ratio_5d": 1.5 if positive else 0.8,
        "label__future_return_5d": 0.1,
        "label__future_return_10d": 0.1,
        "label__future_return_20d": 0.1,
        "label__future_max_return_20d": 0.2,
        "label__future_max_drawdown_20d": -0.02,
        "label__top_decile_20d": positive,
        "label__downside_bad_20d": False,
        "label__momentum_candidate_label": positive,
    }
