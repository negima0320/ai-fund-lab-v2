from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from scripts.audit_phase4be_long_history_dataset import run_audit
from scripts.build_phase4be_long_history_dataset import (
    READY,
    LABEL_COLUMNS,
    build_long_history_dataset_frame,
    build_phase4be_long_history_dataset,
)


def test_phase4be_builds_long_history_dataset(tmp_path: Path) -> None:
    runtime_dir, bc_summary, bd_summary = _prepare_runtime_fixture(tmp_path)

    summary = build_phase4be_long_history_dataset(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        output_format="jsonl",
        phase4bc_summary_path=bc_summary,
        phase4bd_summary_path=bd_summary,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["dataset_rebuild_executed"] is True
    assert summary["joined_row_count"] > 0
    assert summary["join_success_rate"] > 0
    assert summary["train_row_count"] > 0
    assert summary["validation_row_count"] > 0
    assert summary["test_row_count"] > 0
    assert summary["train_positive_count"] > 0
    assert summary["validation_positive_count"] > 0
    assert summary["test_positive_count"] > 0
    assert summary["future_column_detected_in_features"] is False
    assert summary["label_column_detected_in_features"] is False
    assert summary["feature_column_detected_in_labels"] is False
    assert summary["leakage_audit_status"] == "OK"
    assert summary["train_all_null_feature_count"] == 0
    assert summary["train_feature_variance_available"] is True
    assert summary["training_executed"] is False
    assert Path(summary["dataset_output_path"]).is_file()


def test_phase4be_dataset_columns_are_prefixed() -> None:
    features, labels = _feature_label_frames()

    dataset, feature_columns, label_columns = build_long_history_dataset_frame(feature_frame=features, label_frame=labels)

    assert not dataset.empty
    assert feature_columns
    assert set(label_columns) == set(LABEL_COLUMNS)
    assert any(column.startswith("feature__") for column in dataset.columns)
    assert any(column.startswith("label__") for column in dataset.columns)
    assert not any(column in LABEL_COLUMNS for column in dataset.columns)
    assert not any(column.startswith("feature__future_return_") for column in dataset.columns)


def test_phase4be_audit_completes(tmp_path: Path) -> None:
    runtime_dir, bc_summary, bd_summary = _prepare_runtime_fixture(tmp_path)
    summary_path = tmp_path / "reports" / "phase4be_long_history_dataset_rebuild_summary.json"
    build_phase4be_long_history_dataset(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        output_format="jsonl",
        phase4bc_summary_path=bc_summary,
        phase4bd_summary_path=bd_summary,
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
    assert result["checks"]["no_future_or_label_in_features"] is True


def test_phase4be_report_documents_scope() -> None:
    report = Path("docs/phase_reports/phase4be_long_history_dataset_rebuild.md").read_text(encoding="utf-8")

    assert "READY_FOR_FORMAL_LIGHTGBM_TRAINING" in report
    assert "Phase4-BF" in report
    assert "training_executed: `False`" in report
    assert "inference datasets must not include labels" in report


def _prepare_runtime_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    runtime_dir = tmp_path / "runtime"
    features, labels = _feature_label_frames()
    feature_path = runtime_dir / "candidate_ai" / "features" / "phase4bc_features.parquet"
    label_path = runtime_dir / "candidate_ai" / "labels" / "phase4bd_labels.parquet"
    feature_path.parent.mkdir(parents=True)
    label_path.parent.mkdir(parents=True)
    features.to_parquet(feature_path, index=False)
    labels.to_parquet(label_path, index=False)

    bc_summary = tmp_path / "phase4bc.json"
    bc_summary.write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_LONG_HISTORY_LABEL_REGENERATION",
                "feature_output_path": str(feature_path),
                "feature_row_count": len(features),
            }
        ),
        encoding="utf-8",
    )
    bd_summary = tmp_path / "phase4bd.json"
    bd_summary.write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_LONG_HISTORY_DATASET_REBUILD",
                "label_output_path": str(label_path),
                "label_row_count": len(labels),
            }
        ),
        encoding="utf-8",
    )
    return runtime_dir, bc_summary, bd_summary


def _feature_label_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = _business_dates(date(2021, 9, 9), 1250)
    codes = ("7203", "6758", "9984")
    feature_rows = []
    label_rows = []
    for code_index, code in enumerate(codes, start=1):
        for index, target_date in enumerate(dates, start=1):
            value = index * code_index
            feature_rows.append(
                {
                    "target_date": target_date,
                    "as_of_date": target_date,
                    "code": code,
                    "feature_version": "fixture_feature_v1",
                    "source_snapshot_id": "fixture",
                    "feature_set_name": "fixture",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "data_start_date": dates[0],
                    "data_end_date": target_date,
                    "universe_eligible": True,
                    "excluded_reason": "",
                    "price_momentum_return_5d": value / 1000.0,
                    "price_momentum_return_20d": value / 900.0,
                    "price_momentum_return_60d": value / 800.0,
                    "volume_momentum_ratio_5d": 1.0 + code_index / 10.0,
                    "volume_momentum_ratio_1d_20d": 1.0 + index / 10000.0,
                    "volatility_return_std_20d": index / 100000.0,
                    "trend_close_over_ma_20d": value / 700.0,
                    "trend_ma_5_20_ratio": value / 600.0,
                    "trend_ma_20_60_ratio": value / 500.0,
                    "liquidity_avg_volume_20d": 1000 + value,
                    "missing_flags_insufficient_history": False,
                    "missing_flags_price": False,
                    "missing_flags_volume": False,
                }
            )
            if index <= len(dates) - 20:
                positive = code == "9984"
                label_rows.append(
                    {
                        "target_date": target_date,
                        "code": code,
                        "label_version": "fixture_label_v1",
                        "future_return_5d": 0.01 * code_index,
                        "future_return_10d": 0.02 * code_index,
                        "future_return_20d": 0.03 * code_index,
                        "future_max_return_20d": 0.05 * code_index,
                        "future_max_drawdown_20d": -0.01 * code_index,
                        "top_decile_20d": positive,
                        "downside_bad_20d": False,
                        "momentum_candidate_label": positive,
                    }
                )
    return pd.DataFrame(feature_rows), pd.DataFrame(label_rows)


def _business_dates(start: date, count: int) -> list[str]:
    values: list[str] = []
    current = start
    while len(values) < count:
        if current.weekday() < 5:
            values.append(current.isoformat())
        current += timedelta(days=1)
    return values
