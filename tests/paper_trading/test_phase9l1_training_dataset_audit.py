from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.training_dataset_audit import (
    TRAINING_DATASET_BLOCKED,
    TRAINING_DATASET_READY,
    audit_training_dataset,
)


def test_jquants_source_accepted(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.parquet"
    _write_dataset(dataset)

    result = audit_training_dataset(
        ai_name="candidate",
        dataset_path=dataset,
        data_until="2026-06-15",
        safe_train_until="2026-05-18",
        train_until="2026-05-18",
        label_horizon=20,
        source_data_refs={"normalized": ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet", "source": "jquants"},
        label_source_until="2026-06-15",
    )

    assert result.status == TRAINING_DATASET_READY
    assert result.forbidden_source_check == "OK"
    assert result.future_leakage_check == "OK"
    assert result.feature_schema_hash


def test_train_until_after_safe_train_until_blocked(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.parquet"
    _write_dataset(dataset, date="2026-05-19")

    result = audit_training_dataset(
        ai_name="candidate",
        dataset_path=dataset,
        data_until="2026-06-15",
        safe_train_until="2026-05-18",
        train_until="2026-05-19",
        label_horizon=20,
        source_data_refs={"source": "jquants"},
        label_source_until="2026-06-15",
    )

    assert result.status == TRAINING_DATASET_BLOCKED
    assert "train_until_after_safe_train_until" in result.blocked_reasons


def test_forbidden_source_and_columns_blocked(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.parquet"
    _write_dataset(dataset, extra={"cash": 100})

    result = audit_training_dataset(
        ai_name="candidate",
        dataset_path=dataset,
        data_until="2026-06-15",
        safe_train_until="2026-05-18",
        train_until="2026-05-18",
        label_horizon=20,
        source_data_refs={"paper_ledger": ".runtime/phase9/ledger/latest.json"},
        label_source_until="2026-06-15",
    )

    assert "forbidden_source_detected" in result.blocked_reasons
    assert "forbidden_columns_detected" in result.blocked_reasons


def test_missing_label_horizon_blocked(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.parquet"
    _write_dataset(dataset)

    result = audit_training_dataset(
        ai_name="candidate",
        dataset_path=dataset,
        data_until="2026-06-15",
        safe_train_until="2026-05-18",
        train_until="2026-05-18",
        label_horizon=None,
        source_data_refs={"source": "jquants"},
        label_source_until="2026-06-15",
    )

    assert "missing_label_horizon" in result.blocked_reasons


def test_feature_row_after_train_until_blocked(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.parquet"
    _write_dataset(dataset, date="2026-05-19")

    result = audit_training_dataset(
        ai_name="candidate",
        dataset_path=dataset,
        data_until="2026-06-15",
        safe_train_until="2026-05-20",
        train_until="2026-05-18",
        label_horizon=20,
        source_data_refs={"source": "jquants"},
        label_source_until="2026-06-15",
    )

    assert "feature_row_after_train_until" in result.blocked_reasons


def _write_dataset(path: Path, *, date: str = "2026-05-18", extra: dict | None = None) -> None:
    row = {
        "target_date": date,
        "code": "10010",
        "feature__x": 1.0,
        "label__future_return_20d": 0.1,
    }
    row.update(extra or {})
    pd.DataFrame([row]).to_parquet(path, index=False)
