from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.ai_lifecycle.dataset_revision_materialization import (
    REVIEW_REQUIRED_BRANCH_DETECTED,
    REVIEW_REQUIRED_SPLIT_POLICY_MISSING,
    RollingSplitPolicy,
    build_dataset_generation_input_manifest,
    evaluate_corporate_action_sufficiency,
    generate_rolling_split_from_revision,
    validate_revision_chain,
)


def test_revision_chain_rejects_missing_parent_self_cycle_two_node_cycle_and_branch() -> None:
    base = _revision("base", previous=None)
    missing_parent = _revision("missing-child", previous="missing")
    self_cycle = _revision("self", previous="self")
    two_a = _revision("two-a", previous="two-b")
    two_b = _revision("two-b", previous="two-a")
    branch_a = _revision("branch-a", previous="base")
    branch_b = _revision("branch-b", previous="base")

    missing = validate_revision_chain(revisions=[base, missing_parent])
    assert missing["status"] == "REVIEW_REQUIRED"
    assert "parent_revision_missing" in missing["review_reasons"]

    self_result = validate_revision_chain(revisions=[self_cycle])
    assert self_result["status"] == "BLOCK"
    assert "revision_self_cycle" in self_result["blockers"]

    two_node = validate_revision_chain(revisions=[two_a, two_b])
    assert two_node["status"] == "BLOCK"
    assert "revision_cycle" in two_node["blockers"]

    branch = validate_revision_chain(revisions=[base, branch_a, branch_b])
    assert branch["status"] == "REVIEW_REQUIRED"
    assert REVIEW_REQUIRED_BRANCH_DETECTED in branch["review_reasons"]


def test_schema_change_without_policy_requires_review() -> None:
    parent = _revision("parent", schema_hash="schema-a")
    child = _revision("child", previous="parent", schema_hash="schema-b")

    result = validate_revision_chain(revisions=[parent, child])

    assert result["status"] == "REVIEW_REQUIRED"
    assert "schema_changed_without_policy" in result["review_reasons"]


def test_corporate_action_unknowns_are_not_implicit_pass_and_leakage_blocks() -> None:
    limited = evaluate_corporate_action_sufficiency(
        source_identity="jquants",
        source_cutoff="2026-06-26",
        adjusted_price_fields=["Open", "High", "Low", "Close"],
        listed_issue_history_available=True,
    )
    leaked = evaluate_corporate_action_sufficiency(
        source_identity="jquants",
        source_cutoff="2026-06-26",
        adjusted_price_fields=["Open", "High", "Low", "Close"],
        listed_issue_history_available=True,
        future_corporate_action_leakage=True,
    )
    missing_delisting = evaluate_corporate_action_sufficiency(
        source_identity="jquants",
        source_cutoff="2026-06-26",
        adjusted_price_fields=["Open", "High", "Low", "Close"],
        listed_issue_history_available=False,
        missing_delisting_handling=True,
    )

    assert limited["decision"] == "PASS_WITH_LIMITATION"
    assert limited["implicit_pass_used"] is False
    assert leaked["decision"] == "BLOCK"
    assert missing_delisting["decision"] == "REVIEW_REQUIRED"


def test_missing_split_policy_stops_boundary_generation_without_random_id() -> None:
    policy = RollingSplitPolicy(
        policy_version="rolling_split_policy_v1",
        training_window_business_days=None,
        validation_window_business_days=None,
        embargo_business_days=20,
        target_horizon_business_days=20,
        minimum_training_rows=None,
        minimum_validation_rows=None,
        trading_calendar_identity="calendar",
    )

    result = generate_rolling_split_from_revision(
        revision=_revision("current", label_safe_cutoff="2026-06-04"),
        policy=policy,
        trading_calendar_dates=["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"],
        created_at="2026-07-19T00:00:00+00:00",
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["reason"] == REVIEW_REQUIRED_SPLIT_POLICY_MISSING
    assert "split_id" not in result


def test_split_generation_is_deterministic_when_policy_is_complete() -> None:
    policy = RollingSplitPolicy(
        policy_version="test_policy",
        training_window_business_days=5,
        validation_window_business_days=3,
        embargo_business_days=2,
        target_horizon_business_days=2,
        minimum_training_rows=1,
        minimum_validation_rows=1,
        trading_calendar_identity="calendar",
    )
    revision = _revision("current", label_safe_cutoff="2026-01-20")
    dates = [
        "2026-01-05",
        "2026-01-06",
        "2026-01-07",
        "2026-01-08",
        "2026-01-09",
        "2026-01-12",
        "2026-01-13",
        "2026-01-14",
        "2026-01-15",
        "2026-01-16",
        "2026-01-19",
        "2026-01-20",
    ]

    first = generate_rolling_split_from_revision(
        revision=revision,
        policy=policy,
        trading_calendar_dates=dates,
        created_at="2026-07-19T00:00:00+00:00",
    )
    second = generate_rolling_split_from_revision(
        revision=revision,
        policy=policy,
        trading_calendar_dates=dates,
        created_at="2026-07-19T00:00:00+00:00",
    )

    assert first["split_id"] == second["split_id"]


def test_dataset_generation_input_manifest_binds_component_revisions_and_splits() -> None:
    candidate = _revision("candidate")
    opportunity = _revision("opportunity")
    candidate_split = {"split_id": "candidate-split"}
    opportunity_split = {"split_id": "opportunity-split"}

    manifest = build_dataset_generation_input_manifest(
        candidate_revision=candidate,
        opportunity_revision=opportunity,
        candidate_split=candidate_split,
        opportunity_split=opportunity_split,
        lineage_compatibility={"status": "PASS"},
        policy_hashes={"revision_policy": "hash"},
        created_at="2026-07-19T00:00:00+00:00",
    )

    assert manifest["candidate_dataset_revision"] == "candidate"
    assert manifest["opportunity_dataset_revision"] == "opportunity"
    assert manifest["generation_input_artifact"] is True
    assert manifest["runtime_consumed"] is False
    assert manifest["manifest_hash"]


def test_partial_artifact_json_is_not_valid(tmp_path: Path) -> None:
    path = tmp_path / "partial.json"
    path.write_text('{"dataset_revision": ', encoding="utf-8")

    import json

    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        decoded = False
    else:
        decoded = True

    assert decoded is False


def _revision(
    revision: str,
    *,
    previous: str | None = None,
    schema_hash: str = "schema",
    label_safe_cutoff: str = "2026-06-04",
) -> dict:
    return {
        "dataset_revision": revision,
        "previous_dataset_revision": previous,
        "schema_hash": schema_hash,
        "source_lineage_hash": "lineage",
        "target_date_min": "2021-09-08",
        "target_date_max": "2026-05-15",
        "label_safe_cutoff": label_safe_cutoff,
        "component": "Opportunity",
        "row_count": 100,
    }
