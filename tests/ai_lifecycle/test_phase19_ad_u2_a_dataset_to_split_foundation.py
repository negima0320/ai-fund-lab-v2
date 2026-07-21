from __future__ import annotations

from ai_fund_lab_v2.ai_lifecycle.dataset_to_split import (
    INSUFFICIENT,
    NO_RETRAIN_INSUFFICIENT_NEW_DATA,
    REVIEW_REQUIRED,
    SUFFICIENT,
    DataSufficiencyPolicy,
    build_dataset_revision_metadata,
    build_versioned_rolling_split_contract,
    evaluate_data_sufficiency,
    evaluate_label_safe_availability,
    validate_dataset_revision_binding,
    validate_dataset_lineage,
    validate_versioned_split_contract,
)


def test_data_sufficiency_passes_only_when_all_foundation_conditions_pass() -> None:
    previous = _revision("2026-05-15", row_count=1_000)
    calendar = _business_days("2026-05-01", "2026-06-30")
    label_safe_cutoff = calendar[calendar.index("2026-06-30") - 20]
    current = _revision(label_safe_cutoff, row_count=1_750, previous=previous.to_dict()["dataset_revision"])
    label_safe = evaluate_label_safe_availability(
        dataset_revision=current,
        latest_trading_date="2026-06-30",
        label_safe_cutoff=label_safe_cutoff,
        trading_calendar_dates=calendar,
    )

    result = evaluate_data_sufficiency(
        current=current,
        previous=previous,
        policy=_policy(current.to_dict()["schema_hash"]),
        label_safe_availability=label_safe,
        incremental_business_days=20,
        incremental_rows=750,
    )

    assert result["status"] == SUFFICIENT
    assert result["decision_code"] == SUFFICIENT
    assert result["training_executed"] is False
    assert result["runtime_mutation_performed"] is False
    assert result["broker_write_executed"] is False


def test_insufficient_new_data_returns_no_retrain_decision_code() -> None:
    previous = _revision("2026-05-15", row_count=1_000)
    current = _revision("2026-05-16", row_count=1_020, previous=previous.to_dict()["dataset_revision"])
    label_safe = evaluate_label_safe_availability(
        dataset_revision=current,
        latest_trading_date="2026-06-30",
        label_safe_cutoff="2026-05-16",
        trading_calendar_dates=_business_days("2026-04-01", "2026-06-30"),
    )

    result = evaluate_data_sufficiency(
        current=current,
        previous=previous,
        policy=_policy(current.to_dict()["schema_hash"]),
        label_safe_availability=label_safe,
        incremental_business_days=1,
        incremental_rows=20,
    )

    assert result["status"] == INSUFFICIENT
    assert result["decision_code"] == NO_RETRAIN_INSUFFICIENT_NEW_DATA
    assert result["reason_codes"][0] == NO_RETRAIN_INSUFFICIENT_NEW_DATA


def test_label_safe_unavailable_is_insufficient_for_retraining() -> None:
    previous = _revision("2026-05-15", row_count=1_000)
    current = _revision("2026-06-04", row_count=1_750, previous=previous.to_dict()["dataset_revision"])
    label_safe = evaluate_label_safe_availability(
        dataset_revision=current,
        latest_trading_date="2026-06-30",
        label_safe_cutoff=None,
    )

    result = evaluate_data_sufficiency(
        current=current,
        previous=previous,
        policy=_policy(current.to_dict()["schema_hash"]),
        label_safe_availability=label_safe,
        incremental_business_days=20,
        incremental_rows=750,
    )

    assert label_safe["status"] == REVIEW_REQUIRED
    assert result["status"] == INSUFFICIENT
    assert result["decision_code"] == NO_RETRAIN_INSUFFICIENT_NEW_DATA


def test_dataset_hash_mismatch_is_lineage_failure() -> None:
    current = _revision("2026-06-04", row_count=1_750)

    result = validate_dataset_lineage(current=current, expected_dataset_hash="wrong")

    assert result["status"] == "FAIL"
    assert "dataset_hash_match" in result["reason_codes"]


def test_dataset_missing_revision_requires_review() -> None:
    current = _revision("2026-06-04", row_count=1_750).to_dict()
    current["dataset_revision"] = ""

    result = evaluate_data_sufficiency(
        current=current,
        previous=None,
        policy=_policy(current["schema_hash"]),
        label_safe_availability={"status": "PASS"},
        incremental_business_days=20,
        incremental_rows=750,
    )

    assert result["status"] == REVIEW_REQUIRED
    assert "dataset_revision_present" in result["reason_codes"]


def test_dataset_lineage_discontinuity_requires_review() -> None:
    previous = _revision("2026-05-15", row_count=1_000, lineage_value="jquants:a")
    current = _revision(
        "2026-06-04",
        row_count=1_750,
        previous=previous.to_dict()["dataset_revision"],
        lineage_value="jquants:b",
    )

    result = evaluate_data_sufficiency(
        current=current,
        previous=previous,
        policy=_policy(current.to_dict()["schema_hash"]),
        label_safe_availability={"status": "PASS"},
        incremental_business_days=20,
        incremental_rows=750,
    )

    assert result["status"] == REVIEW_REQUIRED
    assert "dataset_lineage_continuity" in result["reason_codes"]


def test_dataset_revision_self_cycle_is_lineage_failure() -> None:
    current = _revision("2026-06-04", row_count=1_750).to_dict()
    current["previous_dataset_revision"] = current["dataset_revision"]

    result = validate_dataset_lineage(current=current)

    assert result["status"] == "FAIL"
    assert "revision_not_self_referential" in result["reason_codes"]


def test_dataset_revision_binding_detects_tampered_dataset_hash() -> None:
    current = _revision("2026-06-04", row_count=1_750)

    result = validate_dataset_revision_binding(
        revision=current,
        dataset_file_exists=True,
        actual_dataset_hash="different-hash",
    )

    assert result["status"] == "FAIL"
    assert "actual_dataset_hash_matches_revision" in result["reason_codes"]


def test_label_safe_requires_business_day_horizon_not_calendar_day_guess() -> None:
    current = _revision("2026-01-09", row_count=1_750)

    result = evaluate_label_safe_availability(
        dataset_revision=current,
        latest_trading_date="2026-01-09",
        label_safe_cutoff="2026-01-05",
        target_horizon_business_days=3,
        trading_calendar_dates=["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-09"],
    )

    assert result["status"] == REVIEW_REQUIRED
    assert "business_day_horizon_covered" in result["reason_codes"]
    assert result["business_day_horizon"]["computed_label_safe_cutoff"] == "2026-01-05"


def test_label_safe_rejects_missing_per_symbol_future_labels() -> None:
    current = _revision("2026-01-06", row_count=1_750)

    result = evaluate_label_safe_availability(
        dataset_revision=current,
        latest_trading_date="2026-01-09",
        label_safe_cutoff="2026-01-06",
        target_horizon_business_days=3,
        trading_calendar_dates=["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-09"],
        unavailable_label_rows=1,
    )

    assert result["status"] == REVIEW_REQUIRED
    assert "per_symbol_labels_available" in result["reason_codes"]


def test_versioned_split_contract_is_generation_input_only_and_schema_checked() -> None:
    current = _revision("2026-06-04", row_count=1_750)
    split = build_versioned_rolling_split_contract(
        dataset_revision=current,
        train_start="2021-09-08",
        train_end="2025-12-30",
        validation_start="2026-02-02",
        validation_end="2026-06-04",
        policy_version="rolling_split_policy_v1",
    )

    assert validate_versioned_split_contract(split=split, dataset_revision=current)["status"] == "PASS"
    assert split["runtime_consumed"] is False
    assert split["generation_input_artifact"] is True

    bad = {**split, "schema_hash": "wrong"}
    result = validate_versioned_split_contract(split=bad, dataset_revision=current)
    assert result["status"] == "FAIL"
    assert "schema_hash_match" in result["reason_codes"]


def test_versioned_split_rejects_embargo_gap_and_future_validation_end() -> None:
    current = _revision("2026-06-04", row_count=1_750)
    split = build_versioned_rolling_split_contract(
        dataset_revision=current,
        train_start="2021-09-08",
        train_end="2026-05-20",
        validation_start="2026-05-21",
        validation_end="2026-06-05",
        policy_version="rolling_split_policy_v1",
        embargo_business_days=20,
    )

    result = validate_versioned_split_contract(
        split=split,
        dataset_revision=current,
        trading_calendar_dates=_business_days("2026-05-01", "2026-06-30"),
    )

    assert result["status"] == "FAIL"
    assert "embargo_gap_satisfied" in result["reason_codes"]
    assert "validation_end_not_after_label_safe_max" in result["reason_codes"]


def _revision(
    target_date_max: str,
    *,
    row_count: int,
    previous: str | None = None,
    lineage_value: str = "jquants:a",
):
    return build_dataset_revision_metadata(
        component="Opportunity",
        dataset_path=".runtime/ai_lifecycle/datasets/opportunity_ai/example/dataset.parquet",
        dataset_hash=f"hash-{target_date_max}-{row_count}",
        schema_hash="schema-hash-v1",
        row_count=row_count,
        target_date_min="2021-09-08",
        target_date_max=target_date_max,
        label_safe_cutoff=target_date_max,
        source_lineage={"source": lineage_value},
        previous_dataset_revision=previous,
    )


def _policy(schema_hash: str) -> DataSufficiencyPolicy:
    return DataSufficiencyPolicy(
        min_incremental_business_days=20,
        min_incremental_rows=500,
        required_schema_hash=schema_hash,
    )


def _business_days(start: str, end: str) -> list[str]:
    import pandas as pd

    return pd.bdate_range(start, end).strftime("%Y-%m-%d").tolist()
