from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.position_management_ai.feature_builder import build_position_features_from_quotes, fixture_quote_frame
from ai_fund_lab_v2.position_management_ai.label_dataset import (
    LABEL_COLUMNS,
    READY_FOR_PHASE6D_LABEL_VALIDATION,
    audit_position_label_dataset,
    build_position_label_dataset_frame,
    phase6c_opportunity_frame,
    phase6c_position_scenarios,
    run_phase6c_position_label_dataset_dry_run,
)


def test_phase6c_generates_label_columns() -> None:
    dataset = _dataset()

    for column in LABEL_COLUMNS:
        assert f"label__{column}" in dataset.columns
    assert len(dataset) > 0


def test_phase6c_future_labels_do_not_enter_feature_columns() -> None:
    dataset = _dataset()
    feature_columns = [column for column in dataset.columns if column.startswith("feature__")]

    assert feature_columns
    assert not [column for column in feature_columns if "future_" in column]
    assert not [column for column in feature_columns if "label_" in column]


def test_phase6c_forbidden_feature_audit_ok() -> None:
    dataset = _dataset()
    audit = audit_position_label_dataset(dataset, created_at="2026-06-14T00:00:00+00:00")

    assert audit["forbidden_feature_audit_status"] == "OK"
    assert audit["label_leakage_audit_status"] == "OK"
    assert audit["forbidden_feature_column_count"] == 0
    assert audit["future_feature_column_count"] == 0
    assert audit["feature_label_columns_separated"] is True


def test_phase6c_label_distribution_is_available() -> None:
    dataset = _dataset()
    audit = audit_position_label_dataset(dataset, created_at="2026-06-14T00:00:00+00:00")

    distribution = audit["label_distribution"]
    assert "label__label_continue_winner" in distribution
    assert "label__label_exit_before_drawdown" in distribution
    assert "label__label_add_candidate" in distribution
    assert "label__label_reduce_candidate" in distribution
    assert any(block["true"] > 0 for block in distribution.values())


def test_phase6c_dataset_dry_run_succeeds(tmp_path: Path) -> None:
    result = run_phase6c_position_label_dataset_dry_run(
        output_csv_path=tmp_path / "dataset.csv",
        output_json_path=tmp_path / "dataset.json",
        audit_path=tmp_path / "audit.json",
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.summary["readiness_status"] == READY_FOR_PHASE6D_LABEL_VALIDATION
    assert result.summary["row_count"] > 0
    assert result.summary["feature_label_columns_separated"] is True
    assert result.summary["label_leakage_audit_status"] == "OK"
    assert (tmp_path / "dataset.csv").is_file()
    assert (tmp_path / "dataset.json").is_file()
    assert (tmp_path / "audit.json").is_file()


def _dataset():
    quote_frame = fixture_quote_frame()
    feature_frame = build_position_features_from_quotes(
        position_frame=phase6c_position_scenarios(),
        quote_frame=quote_frame,
        opportunity_frame=phase6c_opportunity_frame(),
        created_at="2026-06-14T00:00:00+00:00",
    )
    return build_position_label_dataset_frame(
        feature_frame=feature_frame,
        quote_frame=quote_frame,
        created_at="2026-06-14T00:00:00+00:00",
    )
