from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy.marginal_capital_frontier_authority import (
    ARTIFACT_MODE,
    PRODUCTION_CONSUMER_COUNT,
    SCHEMA_VERSION,
    assert_production_consumer_disabled,
    build_pc_to_ps_switch_boundary_validation,
    build_marginal_capital_frontier_authority_payload,
    build_marginal_capital_frontier_authority_payload_from_shadow,
    stable_authority_payload_hash,
)


BUSINESS_DATE = "2026-08-28"


def test_phase32_az_new_accepted_target_is_ps_compatible_and_consumer_disabled() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010", rank=1)]),
        cash_payload={"available_cash": 1_000_000.0},
    )

    target = payload["accepted_incremental_targets"][0]
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["artifact_mode"] == ARTIFACT_MODE
    assert target["semantic_type"] == "NEW_FIRST_LOT"
    assert target["accepted_incremental_weight"] > 0
    assert target["target_gap"] == target["accepted_incremental_weight"]
    assert target["target_minus_current"] == target["target_gap"]
    assert target["accepted_frontier_candidate_ids"]
    assert target["capital_value_authority"]["production_consumer_enabled"] is False
    assert payload["target_gap_authority"]["ps_compatible"] is True
    assert assert_production_consumer_disabled(payload) is True


def test_phase32_az_reentry_accepted_target() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_reentry("20020", rank=1)]),
        cash_payload={"available_cash": 1_000_000.0},
    )

    target = payload["accepted_incremental_targets"][0]
    assert target["semantic_type"] == "REENTRY_FIRST_LOT"
    assert target["accepted_incremental_weight"] > 0
    assert target["source_candidate_id"] == "candidate-20020"


def test_phase32_az_add_multi_lot_sequential_accepts_and_stops_at_cap() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_add("30030", current_quantity=100, current_weight=0.05, single_name_cap=0.25)]),
        cash_payload={"available_cash": 1_000_000.0},
        max_add_lots_per_position=3,
    )

    targets = payload["accepted_incremental_targets"]
    assert [target["semantic_type"] for target in targets] == ["ADD_NEXT_LOT", "ADD_NEXT_LOT"]
    assert [target["increment_index"] for target in targets] == [1, 2]
    assert targets[0]["remaining_cash_after"] > targets[1]["remaining_cash_after"]
    blocked = [row for row in payload["frontier_candidates"] if row["semantic_type"] == "ADD_NEXT_LOT" and row["increment_index"] == 3][0]
    assert blocked["authority_disposition"] == "INFEASIBLE_CAP_BLOCKED"


def test_phase32_bz_fail_closed_add_evidence_cannot_be_accepted() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc(
            [
                _add(
                    "30030",
                    current_quantity=100,
                    current_weight=0.05,
                    single_name_cap=0.30,
                    add_allocation_eligibility_status="FAIL_CLOSED",
                    expected_edge_improvement_state="WEAKENING",
                    incremental_investment_value_state="UNKNOWN",
                    opportunity_cost_status="NEW_BUY_SUPERIOR",
                )
            ]
        ),
        cash_payload={"available_cash": 1_000_000.0},
        max_add_lots_per_position=3,
    )

    add_rows = [row for row in payload["frontier_candidates"] if row["semantic_type"] == "ADD_NEXT_LOT"]
    assert add_rows
    assert payload["accepted_incremental_targets"] == []
    assert {row["authority_disposition"] for row in add_rows} == {"INELIGIBLE_ADD_ADMISSION_BLOCKED"}
    assert all(row["add_admission_authority"]["final_add_eligibility"] == "FAIL_CLOSED" for row in add_rows)
    assert all(row["capital_value_status"] == "NOT_COMPARABLE" for row in add_rows)


def test_phase32_bz_same_day_multi_lot_pass_add_evidence_is_preserved() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_add("30030", current_quantity=100, current_weight=0.05, single_name_cap=0.35)]),
        cash_payload={"available_cash": 1_000_000.0},
        max_add_lots_per_position=3,
    )

    add_targets = [target for target in payload["accepted_incremental_targets"] if target["semantic_type"] == "ADD_NEXT_LOT"]
    assert [target["increment_index"] for target in add_targets] == [1, 2, 3]
    assert all(
        row["add_admission_authority"]["status"] == "PASS"
        for row in payload["frontier_candidates"]
        if row["semantic_type"] == "ADD_NEXT_LOT"
    )


def test_phase32_db_blocked_add_admission_pass_cannot_be_accepted() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date="2022-10-21",
        portfolio_construction_payload=_pc(
            [
                _add(
                    "94320",
                    current_quantity=400,
                    current_weight=0.065464,
                    single_name_cap=0.18,
                    rank=1,
                    reference_price=161.40,
                    strategy_intelligence_add_worthiness_state="NO_ADD",
                )
            ],
            available_incremental_budget=0.474368,
        ),
        cash_payload={"available_cash": 554_500.0},
        max_add_lots_per_position=3,
    )

    add_rows = [row for row in payload["frontier_candidates"] if row["semantic_type"] == "ADD_NEXT_LOT"]
    assert [row["increment_index"] for row in add_rows] == [1, 2, 3]
    assert all(row["add_admission_authority"]["status"] == "PASS" for row in add_rows)
    assert all(row["comparison_class"] == "BLOCKED" for row in add_rows)
    assert all(row["capital_value_status"] == "NOT_COMPARABLE" for row in add_rows)
    assert {row["authority_disposition"] for row in add_rows} == {"INELIGIBLE_MARGINAL_CAPITAL_VALUE_BLOCKED"}
    assert payload["accepted_incremental_targets"] == []
    assert payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"] == []


def test_phase32_db_blocked_new_reentry_and_desirability_review_are_not_accepted() -> None:
    payload = build_marginal_capital_frontier_authority_payload_from_shadow(
        shadow_payload=_shadow_payload(
            [
                _shadow_security("11110", "NEW_FIRST_LOT", comparison_class="BLOCKED"),
                _shadow_security("22220", "REENTRY_FIRST_LOT", comparison_class="BLOCKED"),
                _shadow_security("33330", "NEW_FIRST_LOT", desirability_status="REVIEW_REQUIRED", comparison_class="COMPARABLE_HIGH"),
                _shadow_cash(),
            ]
        ),
        portfolio_construction_payload=_pc([], available_incremental_budget=1.0),
    )

    rows = {row["symbol"]: row for row in payload["frontier_candidates"] if row["semantic_type"] != "CASH_OPTIONALITY"}
    assert rows["11110"]["authority_disposition"] == "INELIGIBLE_MARGINAL_CAPITAL_VALUE_BLOCKED"
    assert rows["22220"]["authority_disposition"] == "INELIGIBLE_MARGINAL_CAPITAL_VALUE_BLOCKED"
    assert rows["33330"]["authority_disposition"] == "REVIEW_REQUIRED"
    assert payload["accepted_incremental_targets"] == []


def test_phase32_db_valid_comparable_candidate_still_competes_with_cash() -> None:
    payload = build_marginal_capital_frontier_authority_payload_from_shadow(
        shadow_payload=_shadow_payload([_shadow_security("11110", "NEW_FIRST_LOT", comparison_class="COMPARABLE_MARGINAL"), _shadow_cash()]),
        portfolio_construction_payload=_pc([], available_incremental_budget=1.0),
    )

    assert payload["accepted_incremental_targets"][0]["symbol"] == "11110"
    assert payload["frontier_candidates"][0]["capital_value_status"] == "PASS"


def test_phase32_db_bf_rejects_poisoned_accepted_source_candidate() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010", rank=1)]),
        cash_payload={"available_cash": 1_000_000.0},
    )
    poisoned = json.loads(json.dumps(payload))
    candidate_id = poisoned["accepted_incremental_targets"][0]["accepted_frontier_candidate_ids"][0]
    source = next(row for row in poisoned["frontier_candidates"] if row["candidate_id"] == candidate_id)
    source["comparison_class"] = "BLOCKED"
    source["marginal_capital_value_class"] = "BLOCKED_OR_NOT_ELIGIBLE"
    source["desirability"]["status"] = "REVIEW_REQUIRED"

    boundary = build_pc_to_ps_switch_boundary_validation(poisoned)

    assert boundary["status"] == "REVIEW_REQUIRED"
    assert boundary["aggregated_ps_targets"] == []
    assert "accepted_source_candidate_comparison_class_blocked" in boundary["review_reasons"]
    assert "accepted_source_candidate_marginal_capital_value_blocked" in boundary["review_reasons"]
    assert "accepted_source_candidate_desirability_not_pass:REVIEW_REQUIRED" in boundary["review_reasons"]


def test_phase32_az_cash_win_emits_no_security_target() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010", rank=1)]),
        cash_payload={"available_cash": 1_000_000.0, "cash_preferred": True},
    )

    assert payload["accepted_incremental_targets"] == []
    assert payload["cash_disposition"]["status"] == "ACCEPTED_OPTIONALITY"
    assert payload["target_gap_authority"]["accepted_target_count"] == 0


def test_phase32_az_cap_cash_safety_and_risk_pacing_blocks_are_preserved() -> None:
    cap = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_add("30030", current_quantity=100, current_weight=0.19, single_name_cap=0.20, reference_price=2_000.0)]),
        cash_payload={"available_cash": 1_000_000.0},
    )
    cash = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("40040", reference_price=5_000.0, single_name_cap=1.0)]),
        cash_payload={"available_cash": 100_000.0},
    )
    safety = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("50050")]),
        safety_payload={"status": "BLOCK"},
        cash_payload={"available_cash": 1_000_000.0},
    )
    risk = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("60060")]),
        risk_pacing_payload={"status": "BLOCK"},
        cash_payload={"available_cash": 1_000_000.0},
    )

    assert _candidate(cap, "30030")["authority_disposition"] == "INFEASIBLE_CAP_BLOCKED"
    assert _candidate(cash, "40040")["authority_disposition"] == "INFEASIBLE_INSUFFICIENT_CASH"
    assert _candidate(safety, "50050")["authority_disposition"] == "INELIGIBLE_SAFETY_BLOCKED"
    assert _candidate(risk, "60060")["authority_disposition"] == "INELIGIBLE_RISK_PACING_BLOCKED"
    assert cap["guardrails"]["preserved"] is True


def test_phase32_az_missing_campaign_or_cash_fails_closed_review_required() -> None:
    row = _add("30030", current_quantity=100)
    row.pop("position_campaign_id")
    missing_campaign = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row]),
        cash_payload={"available_cash": 1_000_000.0},
    )
    missing_cash = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010")]),
        cash_payload={"cash_source_status": "REVIEW_REQUIRED", "cash_source_reason": "missing_decision_time_cash_evidence"},
    )

    assert missing_campaign["target_gap_authority"]["status"] == "REVIEW_REQUIRED"
    assert missing_campaign["accepted_incremental_targets"] == []
    assert "observability_review_required" in missing_campaign["review_reasons"]
    assert missing_cash["target_gap_authority"]["status"] == "REVIEW_REQUIRED"
    assert missing_cash["accepted_incremental_targets"] == []
    assert "REVIEW_REQUIRED" in missing_cash["review_reasons"]


def test_phase32_az_ambiguous_cross_type_value_fails_closed() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010", rank=1), _reentry("20020", rank=1)]),
        cash_payload={"available_cash": 1_000_000.0},
    )

    assert payload["target_gap_authority"]["status"] == "REVIEW_REQUIRED"
    assert payload["accepted_incremental_targets"] == []
    assert "ambiguous_cross_type_cardinal_value" in payload["review_reasons"]


def test_phase32_az_deterministic_rerun_and_future_outcome_fields_rejected() -> None:
    members = [
        _new("10010", rank=2, future_return=0.8, fill_outcome="WINNER"),
        _reentry("20020", rank=1),
        _add("30030", current_quantity=100, rank=3),
    ]
    first = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc(members),
        cash_payload={"available_cash": 1_000_000.0},
    )
    second = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc(list(reversed(members))),
        cash_payload={"available_cash": 1_000_000.0},
    )

    rendered = json.dumps(first, sort_keys=True)
    assert first["artifact_hash"] == second["artifact_hash"]
    assert first["determinism_key"] == second["determinism_key"]
    assert stable_authority_payload_hash(first) == first["artifact_hash"]
    assert "future_return" not in rendered
    assert "fill_outcome" not in rendered
    assert first["future_information_used"] is False
    assert first["historical_outcome_used"] is False


def test_phase32_az_shadow_production_consumer_count_remains_zero() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010", rank=1)]),
        cash_payload={"available_cash": 1_000_000.0},
    )

    assert payload["production_consumer_count"] == PRODUCTION_CONSUMER_COUNT == 0
    assert payload["shadow_frontier_remains_non_authoritative"] is True
    assert payload["production_consumer_enabled"] is False
    assert payload["production_behavior_changed"] is False


def test_phase32_bc_finite_budget_filters_feasible_tail_and_allocates_cash_residual() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc(
            [_new("10010", rank=1), _new("20020", rank=2), _new("30030", rank=3)],
            available_incremental_budget=0.11,
        ),
        cash_payload={"available_cash": 110_000.0},
    )

    targets = payload["accepted_incremental_targets"]
    assert len(targets) == 1
    assert targets[0]["symbol"] == "10010"
    assert payload["frontier_acceptance_sequence"][-1]["decision"] == "STOP_BUDGET_EXHAUSTED_TO_CASH"
    assert payload["authorized_cash_allocation"]["authorized_allocation_weight"] > 0
    assert payload["capital_conservation"]["status"] == "PASS"


def test_phase32_bc_add_lot_two_recompetes_and_records_sequence() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc(
            [_add("30030", current_quantity=100, current_weight=0.05, single_name_cap=0.25, rank=1)],
            available_incremental_budget=0.21,
        ),
        cash_payload={"available_cash": 210_000.0},
        max_add_lots_per_position=3,
    )

    add_targets = [target for target in payload["accepted_incremental_targets"] if target["semantic_type"] == "ADD_NEXT_LOT"]
    assert [target["increment_index"] for target in add_targets] == [1, 2]
    sequence = [step for step in payload["frontier_acceptance_sequence"] if step["decision"] == "ACCEPT_INCREMENTAL_TARGET"]
    assert [step["top_candidate_increment_index"] for step in sequence] == [1, 2]
    assert sequence[1]["candidate_pool_hash"] != sequence[0]["candidate_pool_hash"]
    assert payload["capital_conservation"]["status"] == "PASS"


def test_phase32_bc_budget_exhaustion_and_cash_allocation_are_explicit() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010", rank=1), _new("20020", rank=2)], available_incremental_budget=0.1),
        cash_payload={"available_cash": 100_000.0},
    )

    assert payload["allocation_budget_authority"]["available_incremental_budget_weight"] == 0.1
    assert payload["frontier_acceptance_sequence"][-1]["decision"] == "STOP_BUDGET_EXHAUSTED"
    assert payload["authorized_cash_allocation"]["status"] == "PASS"
    assert payload["capital_conservation"]["status"] == "PASS"


def test_phase32_bc_conflicting_same_priority_budget_sources_fail_closed() -> None:
    pc = _pc([_new("10010", rank=1)], available_incremental_budget=0.05)
    pc["available_incremental_budget_weight"] = 0.10
    pc["capital_competition"] = {
        "canonical_multi_allocation_deployment_set": {
            "available_incremental_budget": 0.05,
            "budget_envelope": {"schema_version": "incremental_capital_budget_envelope.v1", "authority_status": "AUTHORITATIVE"},
        }
    }
    # Same-priority conflict is represented by two top-level aliases for the
    # BC resolver; lower-priority agreement must not hide it.
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=pc,
        cash_payload={"available_cash": 100_000.0},
    )

    assert payload["allocation_budget_authority"]["status"] == "REVIEW_REQUIRED"
    assert "conflicting_allocation_budget_authority" in payload["review_reasons"]
    assert payload["accepted_incremental_targets"] == []
    assert payload["production_consumer_count"] == 0


def test_phase32_bc_missing_budget_authority_fails_closed() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010", rank=1)], available_incremental_budget=None),
        cash_payload={"available_cash": 1_000_000.0},
    )

    assert payload["allocation_budget_authority"]["status"] == "REVIEW_REQUIRED"
    assert "missing_allocation_budget_authority" in payload["review_reasons"]
    assert payload["accepted_incremental_targets"] == []
    assert payload["capital_conservation"]["status"] == "REVIEW_REQUIRED"


def test_phase32_bf_add_three_lots_aggregate_to_net_quantity() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc(
            [_add("30030", current_quantity=100, current_weight=0.05, single_name_cap=0.40, rank=1)],
            available_incremental_budget=0.31,
        ),
        cash_payload={"available_cash": 310_000.0},
        max_add_lots_per_position=3,
    )

    boundary = payload["pc_to_ps_consumer_switch_boundary"]
    add_target = boundary["aggregated_ps_targets"][0]
    assert boundary["status"] == "PASS"
    assert add_target["semantic_type"] == "ADD_NEXT_LOT"
    assert add_target["accepted_lot_count"] == 3
    assert add_target["accepted_increment_indexes"] == [1, 2, 3]
    assert add_target["final_quantity_delta"] == 300
    assert add_target["final_target_quantity"] == 400
    assert add_target["position_campaign_id"] == "pc-30030-0001"
    assert add_target["legacy_zero_fallback_allowed"] is False


def test_phase32_bf_new_and_reentry_aggregation_are_ps_compatible() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010", rank=1), _reentry("20020", rank=2)], available_incremental_budget=0.2),
        cash_payload={"available_cash": 200_000.0},
    )

    boundary = payload["pc_to_ps_consumer_switch_boundary"]
    targets = sorted(boundary["aggregated_ps_targets"], key=lambda row: row["semantic_type"])
    assert boundary["status"] == "PASS"
    assert {target["semantic_type"] for target in targets} == {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT"}
    assert all(target["ps_compatible"] is True for target in targets)
    assert all(target["final_target_quantity"] == target["current_quantity"] + target["final_quantity_delta"] for target in targets)
    assert all(target["runtime_pending_lineage_status"] == "PASS" for target in targets)


def test_phase32_bf_duplicate_campaign_identity_fails_closed() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_add("30030", current_quantity=100, current_weight=0.05, single_name_cap=0.40, rank=1)], available_incremental_budget=0.21),
        cash_payload={"available_cash": 210_000.0},
        max_add_lots_per_position=3,
    )
    copied = json.loads(json.dumps(payload))
    copied["accepted_incremental_targets"].append(dict(copied["accepted_incremental_targets"][0]))

    boundary = build_pc_to_ps_switch_boundary_validation(copied)

    assert boundary["status"] == "REVIEW_REQUIRED"
    assert boundary["aggregated_ps_targets"] == []
    assert "duplicate_accepted_target_identity" in boundary["review_reasons"]


def test_phase32_bf_missing_authority_fails_closed() -> None:
    boundary = build_pc_to_ps_switch_boundary_validation({})

    assert boundary["status"] == "REVIEW_REQUIRED"
    assert boundary["aggregated_ps_targets"] == []
    assert "missing_or_invalid_authority_payload" in boundary["review_reasons"]


def test_phase32_bf_legacy_zero_fallback_is_impossible_and_consumer_off() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010", rank=1)]),
        cash_payload={"available_cash": 1_000_000.0},
    )

    boundary = payload["pc_to_ps_consumer_switch_boundary"]
    target = boundary["aggregated_ps_targets"][0]
    assert boundary["legacy_target_gap_input_used"] is False
    assert boundary["legacy_target_gap_fallback_allowed"] is False
    assert boundary["legacy_zero_fallback_allowed"] is False
    assert target["legacy_target_gap_fallback_allowed"] is False
    assert target["legacy_zero_fallback_allowed"] is False
    assert payload["production_consumer_enabled"] is False
    assert boundary["production_consumer_enabled"] is False
    assert assert_production_consumer_disabled(payload) is True


def test_phase32_bf_final_quantity_delta_consistency_and_determinism() -> None:
    first = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_add("30030", current_quantity=100, current_weight=0.05, single_name_cap=0.40, rank=1)], available_incremental_budget=0.31),
        cash_payload={"available_cash": 310_000.0},
        max_add_lots_per_position=3,
    )
    second = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_add("30030", current_quantity=100, current_weight=0.05, single_name_cap=0.40, rank=1)], available_incremental_budget=0.31),
        cash_payload={"available_cash": 310_000.0},
        max_add_lots_per_position=3,
    )

    first_target = first["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"][0]
    assert first_target["final_target_quantity"] == first_target["current_quantity"] + first_target["final_quantity_delta"]
    assert first["pc_to_ps_consumer_switch_boundary"]["boundary_hash"] == second["pc_to_ps_consumer_switch_boundary"]["boundary_hash"]
    assert first["artifact_hash"] == second["artifact_hash"]


def test_phase32_br_add_three_200_share_lots_aggregate_to_1300_final_target() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc(
            [_add("94340", current_quantity=700, current_weight=0.10, single_name_cap=0.50, rank=1, reference_price=145.8)],
            available_incremental_budget=0.20,
        ),
        position_sizing_payload={"positions": [{"security_code": "94340", "trading_unit": 100, "transaction_quantity_candidate": 200}]},
        cash_payload={"available_cash": 250_000.0},
        max_add_lots_per_position=3,
    )

    accepted = [target for target in payload["accepted_incremental_targets"] if target["symbol"] == "94340"]
    boundary = payload["pc_to_ps_consumer_switch_boundary"]
    aggregate = next(target for target in boundary["aggregated_ps_targets"] if target["symbol"] == "94340")

    assert [(target["pre_quantity"], target["target_quantity"], target["accepted_incremental_quantity"]) for target in accepted] == [
        (700, 900, 200),
        (900, 1100, 200),
        (1100, 1300, 200),
    ]
    assert boundary["status"] == "PASS"
    assert "ps_final_quantity_delta_inconsistent" not in boundary["review_reasons"]
    assert aggregate["current_quantity"] == 700
    assert aggregate["final_quantity_delta"] == 600
    assert aggregate["final_target_quantity"] == 1300


def test_phase32_br_hundred_share_add_lots_remain_non_regressed() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc(
            [_add("30030", current_quantity=200, current_weight=0.05, single_name_cap=0.50, rank=1)],
            available_incremental_budget=0.31,
        ),
        cash_payload={"available_cash": 310_000.0},
        max_add_lots_per_position=3,
    )

    aggregate = payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"][0]
    assert payload["pc_to_ps_consumer_switch_boundary"]["status"] == "PASS"
    assert aggregate["current_quantity"] == 200
    assert aggregate["final_quantity_delta"] == 300
    assert aggregate["final_target_quantity"] == 500


def test_phase32_br_mixed_invalid_add_sequence_still_fails_closed() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc(
            [_add("94340", current_quantity=700, current_weight=0.10, single_name_cap=0.50, rank=1, reference_price=145.8)],
            available_incremental_budget=0.20,
        ),
        position_sizing_payload={"positions": [{"security_code": "94340", "trading_unit": 100, "transaction_quantity_candidate": 200}]},
        cash_payload={"available_cash": 250_000.0},
        max_add_lots_per_position=3,
    )
    copied = json.loads(json.dumps(payload))
    copied["accepted_incremental_targets"][1]["pre_quantity"] = 800
    copied["accepted_incremental_targets"][1]["target_quantity"] = 1000

    boundary = build_pc_to_ps_switch_boundary_validation(copied)

    assert boundary["status"] == "REVIEW_REQUIRED"
    assert boundary["aggregated_ps_targets"] == []
    assert "add_repeated_lot_quantity_progression_inconsistent" in boundary["review_reasons"]


def test_phase32_bt_bq_2022_10_11_artifact_blocks_94340_lot_three_at_strategy_cap() -> None:
    root = Path("reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T161503510098Z/daily/2022-10-11/strategy")
    if not root.exists():
        return
    pc = json.loads((root / "portfolio_construction.json").read_text(encoding="utf-8"))
    ps = json.loads((root / "position_sizing_preflight.json").read_text(encoding="utf-8"))
    prior_authority = json.loads((root / "marginal_capital_frontier_authority.json").read_text(encoding="utf-8"))
    cash_payload = {
        "available_cash": prior_authority["allocation_budget_authority"]["starting_cash_notional"],
        "cash_source_status": "PASS",
    }

    payload = build_marginal_capital_frontier_authority_payload(
        business_date="2022-10-11",
        portfolio_construction_payload=pc,
        position_sizing_payload=ps,
        cash_payload=cash_payload,
        run_id="runtime-test-historical-extended-smoke-20260828T161503510098Z",
    )
    boundary = payload["pc_to_ps_consumer_switch_boundary"]
    add_94340 = next(target for target in boundary["aggregated_ps_targets"] if target["symbol"] == "94340")
    candidates_94340 = [row for row in payload["frontier_candidates"] if row["symbol"] == "94340"]

    assert payload["authority_result"]["accepted_target_count"] == 2
    assert boundary["status"] == "PASS"
    assert boundary["aggregated_ps_target_count"] == 1
    assert "ps_final_quantity_delta_inconsistent" not in boundary["review_reasons"]
    assert [(row["increment_index"], row["pre_quantity"], row["post_quantity"]) for row in candidates_94340] == [
        (1, 700, 900),
        (2, 900, 1100),
        (3, 1100, 1300),
    ]
    assert [row["authority_disposition"] for row in candidates_94340] == [
        "ACCEPTED_INCREMENTAL_TARGET",
        "ACCEPTED_INCREMENTAL_TARGET",
        "INFEASIBLE_CAP_BLOCKED",
    ]
    assert [row["feasibility"]["effective_single_name_cap"] for row in candidates_94340] == [0.18, 0.18, 0.18]
    assert add_94340["current_quantity"] == 700
    assert add_94340["final_quantity_delta"] == 400
    assert add_94340["final_target_quantity"] == 1100


def test_phase32_bt_missing_strategy_cap_fails_closed() -> None:
    row = _new("10010", rank=1)
    row.pop("single_name_cap")
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.1),
        position_sizing_payload={"effective_maximum_position_weight": 0.18, "safety_maximum_position_weight": 0.25},
        cash_payload={"available_cash": 100_000.0},
    )

    assert payload["target_gap_authority"]["status"] == "REVIEW_REQUIRED"
    assert payload["accepted_incremental_targets"] == []
    assert "feasibility_review_required" in payload["review_reasons"]
    assert "missing_strategy_single_name_cap_authority" in _candidate(payload, "10010")["feasibility"]["reason_codes"]


def test_phase32_bt_ambiguous_effective_cap_fails_closed() -> None:
    row = _new("10010", rank=1)
    row.pop("single_name_cap")
    pc = _pc([row], available_incremental_budget=0.1)
    pc["single_name_weight_cap"] = 0.18
    pc["strategy_maximum_position_weight"] = 0.20
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=pc,
        position_sizing_payload={"effective_maximum_position_weight": 0.18, "safety_maximum_position_weight": 0.25},
        cash_payload={"available_cash": 100_000.0},
    )

    assert payload["target_gap_authority"]["status"] == "REVIEW_REQUIRED"
    assert payload["accepted_incremental_targets"] == []
    assert "ambiguous_strategy_single_name_cap_authority" in _candidate(payload, "10010")["feasibility"]["reason_codes"]


def test_phase32_bt_safety_hard_cap_crossing_blocks_under_effective_cap() -> None:
    pc = _pc(
        [_add("94340", current_quantity=1100, current_weight=0.22, single_name_cap=0.90, rank=1, reference_price=100.0)],
        available_incremental_budget=0.10,
    )
    pc["single_name_weight_cap"] = 0.30
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=pc,
        position_sizing_payload={
            "strategy_maximum_position_weight": 0.30,
            "safety_maximum_position_weight": 0.25,
            "effective_maximum_position_weight": 0.25,
            "positions": [{"security_code": "94340", "trading_unit": 100, "transaction_quantity_candidate": 200}],
        },
        cash_payload={"available_cash": 100_000.0},
        max_add_lots_per_position=3,
    )

    add_rows = [row for row in payload["frontier_candidates"] if row["symbol"] == "94340"]
    assert [row["feasibility"]["effective_single_name_cap"] for row in add_rows] == [0.25, 0.25, 0.25]
    assert add_rows[0]["feasibility"]["status"] == "PASS"
    assert add_rows[1]["authority_disposition"] == "INFEASIBLE_CAP_BLOCKED"
    assert add_rows[2]["authority_disposition"] == "INFEASIBLE_CAP_BLOCKED"


def test_phase32_bt_new_and_reentry_use_effective_cap_contract() -> None:
    pc = _pc([_new("10010", rank=1, reference_price=2_000.0), _reentry("20020", rank=2, reference_price=2_000.0)])
    pc["single_name_weight_cap"] = 0.18
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=pc,
        position_sizing_payload={
            "strategy_maximum_position_weight": 0.18,
            "safety_maximum_position_weight": 0.25,
            "effective_maximum_position_weight": 0.18,
        },
        cash_payload={"available_cash": 1_000_000.0},
    )

    assert _candidate(payload, "10010")["feasibility"]["status"] == "FAIL"
    assert _candidate(payload, "10010")["authority_disposition"] == "INFEASIBLE_CAP_BLOCKED"
    assert _candidate(payload, "20020")["feasibility"]["status"] == "FAIL"
    assert _candidate(payload, "20020")["authority_disposition"] == "INFEASIBLE_CAP_BLOCKED"
    assert _candidate(payload, "10010")["feasibility"]["effective_single_name_cap"] == 0.18
    assert _candidate(payload, "20020")["feasibility"]["effective_single_name_cap"] == 0.18


def test_phase32_bv_legacy_pc_zero_new_is_not_ps_consumable() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010", rank=1, target_weight=0.0, accepted_buy_new_weight=0.033636)]),
        cash_payload={"available_cash": 1_000_000.0},
    )

    candidate = _candidate(payload, "10010")
    assert candidate["production_admission"]["status"] == "BLOCK"
    assert "pc_first_lot_target_weight_zero" in candidate["production_admission"]["reason_codes"]
    assert candidate["authority_disposition"] == "INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED"
    assert payload["accepted_incremental_targets"] == []
    assert payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"] == []


def test_phase32_bv_positive_pc_admitted_new_can_compete() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010", rank=1, target_weight=0.05)]),
        cash_payload={"available_cash": 1_000_000.0},
    )

    target = payload["accepted_incremental_targets"][0]
    assert _candidate(payload, "10010")["production_admission"]["status"] == "PASS"
    assert target["semantic_type"] == "NEW_FIRST_LOT"
    assert target["symbol"] == "10010"
    assert payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_target_count"] == 1


def test_phase32_bv_reentry_requires_pc_production_admission() -> None:
    blocked = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_reentry("20020", rank=1, target_weight=0.0)]),
        cash_payload={"available_cash": 1_000_000.0},
    )
    admitted = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_reentry("20020", rank=1, target_weight=0.05)]),
        cash_payload={"available_cash": 1_000_000.0},
    )

    assert _candidate(blocked, "20020")["authority_disposition"] == "INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED"
    assert blocked["accepted_incremental_targets"] == []
    assert _candidate(admitted, "20020")["production_admission"]["status"] == "PASS"
    assert admitted["accepted_incremental_targets"][0]["semantic_type"] == "REENTRY_FIRST_LOT"


def test_phase32_bv_add_does_not_depend_on_new_first_lot_admission() -> None:
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc(
            [
                _new("10010", rank=1, target_weight=0.0),
                _add("30030", current_quantity=100, current_weight=0.05, single_name_cap=0.40, rank=2),
            ],
            available_incremental_budget=0.31,
        ),
        cash_payload={"available_cash": 310_000.0},
        max_add_lots_per_position=3,
    )

    add_targets = [target for target in payload["accepted_incremental_targets"] if target["semantic_type"] == "ADD_NEXT_LOT"]
    assert _candidate(payload, "10010")["authority_disposition"] == "INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED"
    assert [target["increment_index"] for target in add_targets] == [1, 2, 3]
    assert payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"][0]["final_quantity_delta"] == 300


def test_phase32_bv_post_bt_day0_zero_weight_new_promotion_is_blocked() -> None:
    root = Path("reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T223340854231Z/daily/2022-10-03/strategy")
    if not root.exists():
        return
    pc = json.loads((root / "portfolio_construction.json").read_text(encoding="utf-8"))
    ps = json.loads((root / "position_sizing_preflight.json").read_text(encoding="utf-8"))
    prior_authority = json.loads((root / "marginal_capital_frontier_authority.json").read_text(encoding="utf-8"))
    cash_payload = {
        "available_cash": prior_authority["allocation_budget_authority"]["starting_cash_notional"],
        "cash_source_status": "PASS",
    }

    payload = build_marginal_capital_frontier_authority_payload(
        business_date="2022-10-03",
        portfolio_construction_payload=pc,
        position_sizing_payload=ps,
        cash_payload=cash_payload,
        run_id="runtime-test-historical-extended-smoke-20260828T223340854231Z",
    )
    accepted_symbols = {target["symbol"] for target in payload["accepted_incremental_targets"]}
    zero_pc_symbols = {
        str(row.get("security_code"))
        for row in pc["portfolio_members"]
        if str(row.get("semantic_buy_type") or "").upper() == "BUY_NEW" and float(row.get("target_weight") or 0.0) <= 0.0
    }

    assert accepted_symbols.isdisjoint(zero_pc_symbols)
    assert _candidate(payload, "41920")["authority_disposition"] == "INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED"
    assert payload["pc_to_ps_consumer_switch_boundary"]["status"] == "PASS"
    assert payload["authority_result"]["accepted_target_count"] == len(payload["accepted_incremental_targets"])


def test_phase32_cc_pc_400_share_new_expands_to_lots_one_through_four_only() -> None:
    row = _new(
        "77770",
        rank=1,
        reference_price=100.0,
        target_weight=0.04,
        phase29_l19_lot_resolution=_entry_lot_resolution(400),
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.15),
        cash_payload={"available_cash": 150_000.0},
    )

    new_candidates = [candidate for candidate in payload["frontier_candidates"] if candidate["symbol"] == "77770"]
    targets = payload["accepted_incremental_targets"]
    aggregate = payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"][0]

    assert [candidate["increment_index"] for candidate in new_candidates] == [1, 2, 3, 4]
    assert all(candidate["pc_target_magnitude_authority"]["pc_target_executable_quantity"] == 400 for candidate in new_candidates)
    assert [target["increment_index"] for target in targets] == [1, 2, 3, 4]
    assert aggregate["semantic_type"] == "NEW_FIRST_LOT"
    assert aggregate["accepted_lot_count"] == 4
    assert aggregate["final_quantity_delta"] == 400
    assert aggregate["final_target_quantity"] == 400
    assert 5 not in [candidate["increment_index"] for candidate in new_candidates]


def test_phase32_ch_reduced_new_quality_bounds_entry_lot_expansion() -> None:
    row = _new(
        "89180",
        rank=25,
        reference_price=100.0,
        target_weight=0.04,
        pre_quality_base_target_weight=0.04,
        quality_allocation_adjustment=0.6,
        quality_authorized_target_weight=0.024,
        quality_target_upper_bound_enforced=True,
        production_deployability_class="REDUCED_ALLOCATION_ONLY",
        phase29_l19_lot_resolution=_entry_lot_resolution(400),
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.15),
        cash_payload={"available_cash": 150_000.0},
    )

    candidates = [candidate for candidate in payload["frontier_candidates"] if candidate["symbol"] == "89180"]
    targets = payload["accepted_incremental_targets"]
    aggregate = payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"][0]

    assert [candidate["increment_index"] for candidate in candidates] == [1, 2]
    assert all(candidate["pc_target_magnitude_authority"]["quality_authorized_target_weight"] == 0.024 for candidate in candidates)
    assert all(candidate["pc_target_magnitude_authority"]["pc_target_executable_quantity"] == 200 for candidate in candidates)
    assert [target["increment_index"] for target in targets] == [1, 2]
    assert aggregate["final_quantity_delta"] == 200
    assert aggregate["final_target_quantity"] == 200


def test_phase32_ch_reentry_quality_bound_is_preserved() -> None:
    row = _reentry(
        "83060",
        rank=4,
        reference_price=100.0,
        target_weight=0.03,
        pre_quality_base_target_weight=0.03,
        quality_allocation_adjustment=0.5,
        quality_authorized_target_weight=0.015,
        quality_target_upper_bound_enforced=True,
        production_deployability_class="REDUCED_ALLOCATION_ONLY",
        phase29_l19_lot_resolution=_entry_lot_resolution(300),
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.04),
        cash_payload={"available_cash": 40_000.0},
    )

    candidates = [candidate for candidate in payload["frontier_candidates"] if candidate["symbol"] == "83060"]
    aggregate = payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"][0]

    assert [candidate["increment_index"] for candidate in candidates] == [1]
    assert candidates[0]["pc_target_magnitude_authority"]["pc_target_executable_quantity"] == 100
    assert aggregate["semantic_type"] == "REENTRY_FIRST_LOT"
    assert aggregate["final_quantity_delta"] == 100


def test_phase32_co_sub_lot_supportive_authority_admits_one_lot_candidate() -> None:
    row = _new(
        "33700",
        rank=4,
        reference_price=1_000.0,
        target_weight=0.004,
        pre_quality_base_target_weight=0.04,
        quality_allocation_adjustment=0.1,
        quality_authorized_target_weight=0.004,
        quality_target_upper_bound_enforced=True,
        production_deployability_class="REDUCED_ALLOCATION_ONLY",
        entry_admission_action="FULL_ALLOCATION_ELIGIBLE",
        allocation_quality_bias="FULL",
        phase29_l19_lot_resolution=_entry_lot_resolution(100),
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.15),
        cash_payload={"available_cash": 150_000.0},
    )

    candidate = _candidate(payload, "33700")
    authority = candidate["pc_target_magnitude_authority"]["minimum_executable_one_lot_authority"]
    assert candidate["pc_target_magnitude_authority"]["status"] == "PASS"
    assert candidate["pc_target_magnitude_authority"]["pc_target_executable_quantity"] == 100
    assert authority["decision"] == "ADMIT_ONE_LOT"
    assert authority["decision_alias"] == "ADMIT"
    assert authority["future_information_used"] is False
    assert authority["historical_outcome_used"] is False
    assert "minimum_executable_one_lot_admitted_by_bounded_pc_authority" in authority["reason_codes"]
    assert len([row for row in payload["frontier_candidates"] if row["symbol"] == "33700"]) == 1
    assert payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"][0]["final_quantity_delta"] == 100


def test_phase32_cs_comparable_marginal_is_representable_and_deferred_to_frontier() -> None:
    row = _new(
        "92420",
        rank=31,
        reference_price=1_000.0,
        target_weight=0.004,
        pre_quality_base_target_weight=0.12,
        quality_allocation_adjustment=0.1,
        quality_authorized_target_weight=0.004,
        quality_target_upper_bound_enforced=True,
        production_deployability_class="REDUCED_ALLOCATION_ONLY",
        entry_admission_action="BUY_NEW_REDUCED_ONLY",
        allocation_quality_bias="REDUCED",
        phase29_l19_lot_resolution=_entry_lot_resolution(100),
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.15),
        cash_payload={"available_cash": 150_000.0},
    )

    candidate = _candidate(payload, "92420")
    authority = candidate["pc_target_magnitude_authority"]["minimum_executable_one_lot_authority"]
    aggregate = payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"][0]

    assert candidate["pc_target_magnitude_authority"]["status"] == "PASS"
    assert authority["decision"] == "ADMIT_ONE_LOT"
    assert "comparable_marginal_one_lot_representable_deferred_to_common_frontier" in authority["reason_codes"]
    assert "minimum_one_lot_opportunity_quality_not_supportive:COMPARABLE_MARGINAL" not in authority["reason_codes"]
    assert candidate["authority_disposition"] == "ACCEPTED_INCREMENTAL_TARGET"
    assert aggregate["symbol"] == "92420"
    assert aggregate["final_quantity_delta"] == 100


def test_phase32_co_sub_lot_missing_cash_budget_reviews_required() -> None:
    row = _new(
        "33700",
        rank=4,
        reference_price=1_000.0,
        target_weight=0.004,
        pre_quality_base_target_weight=0.04,
        quality_authorized_target_weight=0.004,
        quality_target_upper_bound_enforced=True,
        production_deployability_class="REDUCED_ALLOCATION_ONLY",
        entry_admission_action="FULL_ALLOCATION_ELIGIBLE",
        allocation_quality_bias="FULL",
        phase29_l19_lot_resolution=_entry_lot_resolution(100),
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.15),
        cash_payload={"cash_source_status": "REVIEW_REQUIRED", "cash_source_reason": "missing_decision_time_cash_evidence"},
    )

    candidate = _candidate(payload, "33700")
    authority = candidate["pc_target_magnitude_authority"]["minimum_executable_one_lot_authority"]
    assert candidate["pc_target_magnitude_authority"]["status"] == "REVIEW_REQUIRED"
    assert authority["decision"] == "REVIEW_REQUIRED"
    assert "missing_decision_time_cash_evidence" in authority["reason_codes"]
    assert payload["accepted_incremental_targets"] == []


def test_phase32_co_sub_lot_admit_candidate_can_lose_to_cash() -> None:
    row = _new(
        "33700",
        rank=4,
        reference_price=1_000.0,
        target_weight=0.004,
        pre_quality_base_target_weight=0.04,
        quality_authorized_target_weight=0.004,
        quality_target_upper_bound_enforced=True,
        production_deployability_class="REDUCED_ALLOCATION_ONLY",
        entry_admission_action="FULL_ALLOCATION_ELIGIBLE",
        allocation_quality_bias="FULL",
        phase29_l19_lot_resolution=_entry_lot_resolution(100),
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.15),
        cash_payload={"available_cash": 150_000.0, "cash_preferred": True},
    )

    candidate = _candidate(payload, "33700")
    authority = candidate["pc_target_magnitude_authority"]["minimum_executable_one_lot_authority"]
    assert authority["decision"] == "ADMIT_ONE_LOT"
    assert candidate["authority_disposition"] == "REJECTED_BY_STRONGER_MARGINAL_CAPITAL_VALUE"
    assert payload["accepted_incremental_targets"] == []


def test_phase32_cq_pre_zero_sub_lot_materializes_representability_authority() -> None:
    row = _prezero_sublot_new(
        "83060",
        rank=20,
        reference_price=648.0,
        quality_authorized_target_weight=0.020607,
        pre_quality_base_target_weight=0.033636,
        quality_score=0.612652,
        runtime_opportunity_score=-0.29319864,
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.74),
        cash_payload={"available_cash": 1_000_000.0},
    )

    candidate = _candidate(payload, "83060")
    authority = candidate["pc_target_magnitude_authority"]["minimum_executable_one_lot_authority"]

    assert candidate["pc_target_magnitude_authority"]["quality_authorized_target_weight"] == 0.020607
    assert candidate["pc_target_magnitude_authority"]["status"] == "BLOCK"
    assert authority["decision"] == "BLOCK"
    assert authority["one_lot_weight"] == 0.0648
    assert "minimum_one_lot_exceeds_pre_quality_base_target" in authority["reason_codes"]
    assert "minimum_one_lot_opportunity_quality_not_supportive:COMPARABLE_MARGINAL" not in authority["reason_codes"]
    assert payload["accepted_incremental_targets"] == []
    assert payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"] == []


def test_phase32_cq_pre_zero_supportive_sub_lot_can_admit_and_connect_to_bf() -> None:
    row = _prezero_sublot_new(
        "33700",
        rank=4,
        reference_price=341.0,
        quality_authorized_target_weight=0.02167,
        pre_quality_base_target_weight=0.033636,
        entry_admission_action="FULL_ALLOCATION_ELIGIBLE",
        entry_admission_state="HEALTHY_CONTINUATION_ENTRY",
        allocation_quality_bias="FULL",
        quality_score=0.8,
        runtime_opportunity_score=0.9,
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.74),
        cash_payload={"available_cash": 1_000_000.0},
    )

    candidate = _candidate(payload, "33700")
    authority = candidate["pc_target_magnitude_authority"]["minimum_executable_one_lot_authority"]
    aggregate = payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"][0]

    assert candidate["pc_target_magnitude_authority"]["status"] == "PASS"
    assert candidate["production_admission"]["status"] == "PASS"
    assert authority["decision"] == "ADMIT_ONE_LOT"
    assert candidate["increment_quantity"] == 100
    assert len([row for row in payload["frontier_candidates"] if row["symbol"] == "33700"]) == 1
    assert aggregate["symbol"] == "33700"
    assert aggregate["final_quantity_delta"] == 100
    assert aggregate["pc_target_magnitude_authority"]["minimum_executable_one_lot_authority"]["decision"] == "ADMIT_ONE_LOT"


def test_phase32_cq_pre_zero_extreme_cap_block_materializes_authority() -> None:
    row = _prezero_sublot_new(
        "93600",
        rank=10,
        reference_price=1_911.0,
        quality_authorized_target_weight=0.023228,
        pre_quality_base_target_weight=0.033636,
        entry_admission_action="FULL_ALLOCATION_ELIGIBLE",
        allocation_quality_bias="FULL",
        quality_score=0.69058,
        runtime_opportunity_score=0.9,
        single_name_cap=0.18,
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.74),
        cash_payload={"available_cash": 1_000_000.0},
    )

    candidate = _candidate(payload, "93600")
    authority = candidate["pc_target_magnitude_authority"]["minimum_executable_one_lot_authority"]

    assert candidate["pc_target_magnitude_authority"]["status"] == "BLOCK"
    assert authority["decision"] == "BLOCK"
    assert "minimum_one_lot_exceeds_effective_single_name_cap" in authority["reason_codes"]
    assert candidate["authority_disposition"] == "INFEASIBLE_CAP_BLOCKED"


def test_phase32_cs_safety_cap_breach_still_blocks_one_lot() -> None:
    row = _prezero_sublot_new(
        "92420",
        rank=4,
        reference_price=1_375.0,
        quality_authorized_target_weight=0.020691,
        pre_quality_base_target_weight=0.033636,
        entry_admission_action="FULL_ALLOCATION_ELIGIBLE",
        allocation_quality_bias="FULL",
        quality_score=0.8,
        runtime_opportunity_score=0.9,
        single_name_cap=0.30,
    )
    pc_payload = _pc([row], available_incremental_budget=0.74)
    pc_payload["strategy_single_name_cap"] = 0.30
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=pc_payload,
        safety_payload={"maximum_position_weight": 0.05},
        cash_payload={"available_cash": 1_000_000.0},
    )

    candidate = _candidate(payload, "92420")
    authority = candidate["pc_target_magnitude_authority"]["minimum_executable_one_lot_authority"]

    assert candidate["pc_target_magnitude_authority"]["status"] == "BLOCK"
    assert authority["decision"] == "BLOCK"
    assert "minimum_one_lot_exceeds_effective_single_name_cap" in authority["reason_codes"]
    assert "minimum_one_lot_exceeds_safety_hard_cap" in authority["reason_codes"]
    assert payload["accepted_incremental_targets"] == []


def test_phase32_cq_pre_zero_missing_cash_materializes_review_required() -> None:
    row = _prezero_sublot_new(
        "92420",
        rank=4,
        reference_price=1_375.0,
        quality_authorized_target_weight=0.020691,
        pre_quality_base_target_weight=0.033636,
        entry_admission_action="FULL_ALLOCATION_ELIGIBLE",
        allocation_quality_bias="FULL",
        quality_score=0.8,
        runtime_opportunity_score=0.9,
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.74),
        cash_payload={"cash_source_status": "REVIEW_REQUIRED", "cash_source_reason": "missing_decision_time_cash_evidence"},
    )

    candidate = _candidate(payload, "92420")
    authority = candidate["pc_target_magnitude_authority"]["minimum_executable_one_lot_authority"]

    assert candidate["pc_target_magnitude_authority"]["status"] == "REVIEW_REQUIRED"
    assert authority["decision"] == "REVIEW_REQUIRED"
    assert "missing_decision_time_cash_evidence" in authority["reason_codes"]
    assert payload["accepted_incremental_targets"] == []


def test_phase32_ch_named_reduced_targets_cannot_reexpand_to_base_weight() -> None:
    examples = [
        ("89180", 0.033636, 0.019686, 3300),
        ("76470", 0.040000, 0.024384, 4000),
        ("17570", 0.038462, 0.021632, 3800),
        ("37770", 0.032258, 0.016113, 3200),
    ]
    for symbol, base_weight, quality_weight, base_quantity in examples:
        row = _new(
            symbol,
            rank=25,
            reference_price=10.0,
            target_weight=base_weight,
            pre_quality_base_target_weight=base_weight,
            quality_authorized_target_weight=quality_weight,
            quality_target_upper_bound_enforced=True,
            production_deployability_class="REDUCED_ALLOCATION_ONLY",
            phase29_l19_lot_resolution=_entry_lot_resolution(base_quantity),
        )
        payload = build_marginal_capital_frontier_authority_payload(
            business_date=BUSINESS_DATE,
            portfolio_construction_payload=_pc([row], available_incremental_budget=base_weight),
            cash_payload={"available_cash": 100_000.0},
        )
        aggregate = payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"][0]

        assert aggregate["accepted_incremental_weight"] <= quality_weight
        assert aggregate["accepted_incremental_weight"] < base_weight
        assert aggregate["pc_target_magnitude_authority"]["quality_authorized_target_weight"] == quality_weight
        assert aggregate["pc_target_magnitude_authority"]["pc_target_executable_quantity"] < base_quantity

    full = _new(
        "94340",
        rank=1,
        reference_price=100.0,
        target_weight=0.05,
        pre_quality_base_target_weight=0.05,
        quality_authorized_target_weight=0.05,
        quality_target_upper_bound_enforced=True,
        production_deployability_class="FULL_ALLOCATION_ELIGIBLE",
        phase29_l19_lot_resolution=_entry_lot_resolution(500),
    )
    full_payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([full], available_incremental_budget=0.05),
        cash_payload={"available_cash": 50_000.0},
    )
    full_aggregate = full_payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"][0]
    assert full_aggregate["final_quantity_delta"] == 500
    assert full_aggregate["accepted_incremental_weight"] == 0.05


def test_phase32_cc_reentry_target_magnitude_expands_to_multiple_lots() -> None:
    row = _reentry(
        "88880",
        rank=1,
        reference_price=100.0,
        target_weight=0.03,
        phase29_l19_lot_resolution=_entry_lot_resolution(300),
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.04),
        cash_payload={"available_cash": 40_000.0},
    )

    aggregate = payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"][0]
    assert [target["increment_index"] for target in payload["accepted_incremental_targets"]] == [1, 2, 3]
    assert aggregate["semantic_type"] == "REENTRY_FIRST_LOT"
    assert aggregate["final_quantity_delta"] == 300
    assert aggregate["runtime_pending_lineage_status"] == "PASS"


def test_phase32_cc_entry_lot_one_reject_prevents_later_lot_acceptance() -> None:
    row = _new(
        "77770",
        rank=1,
        reference_price=100.0,
        target_weight=0.04,
        single_name_cap=0.005,
        phase29_l19_lot_resolution=_entry_lot_resolution(400),
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.05),
        cash_payload={"available_cash": 50_000.0},
    )

    assert payload["accepted_incremental_targets"] == []
    assert {row["authority_disposition"] for row in payload["frontier_candidates"] if row["symbol"] == "77770"} == {"INFEASIBLE_CAP_BLOCKED"}


def test_phase32_cc_cash_stops_remaining_entry_lots() -> None:
    row = _new(
        "77770",
        rank=1,
        reference_price=100.0,
        target_weight=0.04,
        phase29_l19_lot_resolution=_entry_lot_resolution(400),
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.05),
        cash_payload={"available_cash": 50_000.0, "cash_preferred": True},
    )

    assert payload["accepted_incremental_targets"] == []
    assert payload["cash_disposition"]["status"] == "ACCEPTED_OPTIONALITY"
    assert payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"] == []


def test_phase32_cc_entry_cap_crossing_lot_is_blocked_without_exceeding_pc_target() -> None:
    row = _new(
        "77770",
        rank=1,
        reference_price=600.0,
        target_weight=0.24,
        single_name_cap=0.18,
        phase29_l19_lot_resolution=_entry_lot_resolution(400),
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.30),
        cash_payload={"available_cash": 300_000.0},
    )

    accepted = payload["accepted_incremental_targets"]
    candidates = [candidate for candidate in payload["frontier_candidates"] if candidate["symbol"] == "77770"]
    aggregate = payload["pc_to_ps_consumer_switch_boundary"]["aggregated_ps_targets"][0]

    assert [target["increment_index"] for target in accepted] == [1, 2, 3]
    assert candidates[3]["authority_disposition"] == "INFEASIBLE_CAP_BLOCKED"
    assert aggregate["final_quantity_delta"] == 300
    assert aggregate["final_target_quantity"] == 300
    assert aggregate["final_target_quantity"] <= aggregate["pc_target_magnitude_authority"]["pc_target_executable_quantity"]


def test_phase32_cc_duplicate_entry_increment_fails_closed() -> None:
    row = _new(
        "77770",
        rank=1,
        reference_price=100.0,
        target_weight=0.02,
        phase29_l19_lot_resolution=_entry_lot_resolution(200),
    )
    payload = build_marginal_capital_frontier_authority_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row], available_incremental_budget=0.03),
        cash_payload={"available_cash": 30_000.0},
    )
    copied = json.loads(json.dumps(payload))
    copied["accepted_incremental_targets"].append(dict(copied["accepted_incremental_targets"][0]))

    boundary = build_pc_to_ps_switch_boundary_validation(copied)

    assert boundary["status"] == "REVIEW_REQUIRED"
    assert boundary["aggregated_ps_targets"] == []
    assert "duplicate_accepted_target_identity" in boundary["review_reasons"]


def _candidate(payload: dict, symbol: str) -> dict:
    return next(row for row in payload["frontier_candidates"] if row["symbol"] == symbol)


def _shadow_payload(candidates: list[dict]) -> dict:
    return {
        "schema_name": "canonical_marginal_capital_frontier",
        "schema_version": "canonical_marginal_capital_frontier.v1",
        "business_date": BUSINESS_DATE,
        "session": "morning",
        "run_id": "test",
        "cash_source_status": "PASS",
        "frontier_candidates": candidates,
    }


def _shadow_security(
    symbol: str,
    semantic_type: str,
    *,
    comparison_class: str,
    desirability_status: str = "PASS",
    marginal_capital_value_class: str = "ELIGIBLE_COMPARABLE",
) -> dict:
    return {
        "candidate_id": f"cmcf-{symbol}-{semantic_type}",
        "symbol": symbol,
        "semantic_type": semantic_type,
        "increment_index": 1,
        "comparison_class": comparison_class,
        "marginal_capital_value_class": marginal_capital_value_class,
        "shadow_disposition": "PENDING_AUTHORITY_COMPARISON",
        "current_weight": 0.0,
        "pre_weight": 0.0,
        "post_weight": 0.05,
        "increment_weight": 0.05,
        "increment_quantity": 100,
        "pre_quantity": 0,
        "post_quantity": 100,
        "increment_notional": 50_000.0,
        "source_candidate_id": f"candidate-{symbol}",
        "source_pc_evidence_ids": [f"pc-{symbol}"],
        "desirability": {
            "status": desirability_status,
            "comparison_class": comparison_class,
            "components": {
                "opportunity": 0.80,
                "quality": 0.75,
                "rank": 1,
                "recovery": "PASS",
                "continuation": "PASS",
                "incremental_value": "POSITIVE",
                "cash_opportunity_cost": "PASS",
            },
            "reason_codes": [],
        },
        "feasibility": {"status": "PASS", "available_cash": 1_000_000.0, "reason_codes": ["feasible"]},
        "constraints": {"status": "PASS", "reason_codes": []},
        "observability": {"status": "PASS", "reason_codes": []},
        "risk_modifiers": {"single_name_cap": 0.30, "headroom_after": 0.25},
    }


def _shadow_cash() -> dict:
    return {
        "candidate_id": "cmcf-cash",
        "symbol": "CASH",
        "semantic_type": "CASH_OPTIONALITY",
        "comparison_class": "CASH_OPTIONALITY",
        "shadow_disposition": "PENDING_AUTHORITY_COMPARISON",
        "capital_value": 0.05,
        "desirability": {"status": "PASS", "components": {}},
        "feasibility": {"status": "PASS", "available_cash": 1_000_000.0},
        "constraints": {"status": "PASS", "reason_codes": []},
        "observability": {"status": "PASS", "reason_codes": []},
        "risk_modifiers": {},
    }


def _pc(members: list[dict], *, available_incremental_budget: float | None = 1.0) -> dict:
    payload = {
        "portfolio_value": 1_000_000.0,
        "portfolio_members": members,
        "portfolio_policy_allocation_authority": {
            "risk_pacing_evidence": {
                "risk_pacing_intent": "NORMAL_DEPLOYMENT",
                "market_quality_state": "HEALTHY",
            }
        },
    }
    if available_incremental_budget is not None:
        payload["available_incremental_budget"] = available_incremental_budget
        payload["incremental_budget_reconciliation"] = {"available_incremental_budget": available_incremental_budget}
        payload["capital_competition"] = {
            "canonical_multi_allocation_deployment_set": {
                "available_incremental_budget": available_incremental_budget,
                "budget_envelope": {"schema_version": "incremental_capital_budget_envelope.v1", "authority_status": "AUTHORITATIVE"},
            }
        }
    return payload


def _legacy_pc(members: list[dict]) -> dict:
    return {
        "portfolio_value": 1_000_000.0,
        "portfolio_members": members,
        "portfolio_policy_allocation_authority": {
            "risk_pacing_evidence": {
                "risk_pacing_intent": "NORMAL_DEPLOYMENT",
                "market_quality_state": "HEALTHY",
            }
        },
    }


def _new(symbol: str, *, rank: int = 2, reference_price: float = 1_000.0, **overrides) -> dict:
    row = {
        "security_code": symbol,
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "semantic_buy_type": "BUY_NEW",
        "candidate_id": f"candidate-{symbol}",
        "runtime_opportunity_score": 0.9,
        "input_opportunity_rank": rank,
        "quality_score": 0.8,
        "entry_admission_action": "FULL_ALLOCATION_ELIGIBLE",
        "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "target_weight": 0.05,
        "single_name_cap": overrides.pop("single_name_cap", 0.30),
        "reference_price": reference_price,
        "trading_unit": 100,
    }
    row.update(overrides)
    return row


def _reentry(symbol: str, *, rank: int = 1, reference_price: float = 1_000.0, **overrides) -> dict:
    row = _new(symbol, rank=rank, reference_price=reference_price)
    row.update(
        {
            "semantic_buy_type": "REENTRY",
            "reentry_recovery_status": "PASS",
            "previous_exit_reason_class": "TREND_AND_OPPORTUNITY_BROKEN",
        }
    )
    row.update(overrides)
    return row


def _entry_lot_resolution(quantity: int) -> dict:
    return {
        "status": "PASS",
        "executable_quantity_delta": quantity,
        "pc_positive_executable_quantity_authority": {
            "status": "PASS",
            "final_allocated_quantity": quantity,
            "discrete_authorized_quantity": quantity,
            "future_information_used": False,
            "historical_outcome_used": False,
        },
    }


def _prezero_sublot_new(
    symbol: str,
    *,
    reference_price: float,
    quality_authorized_target_weight: float,
    pre_quality_base_target_weight: float,
    **overrides,
) -> dict:
    row = _new(
        symbol,
        reference_price=reference_price,
        target_weight=0.0,
        requested_buy_new_weight=quality_authorized_target_weight,
        accepted_buy_new_weight=quality_authorized_target_weight,
        lot_aware_accepted_buy_new_weight=0.0,
        pre_quality_base_target_weight=pre_quality_base_target_weight,
        quality_authorized_target_weight=quality_authorized_target_weight,
        quality_allocation_adjustment=round(quality_authorized_target_weight / pre_quality_base_target_weight, 6),
        quality_target_upper_bound_enforced=True,
        production_deployability_class="REDUCED_ALLOCATION_ONLY",
        entry_admission_action="BUY_NEW_REDUCED_ONLY",
        entry_admission_state="CONTINUATION_WITH_CAUTION",
        entry_admission_evidence_sufficiency="SUFFICIENT",
        quality_action="REDUCED_ALLOCATION_ONLY",
        quality_band="MEDIUM",
        selection_quality_tier="CAUTION_CONTINUATION",
        selection_quality_reason_codes=["selection_quality_caution_continuation"],
        strategy_intelligence_continuation_quality_status="PASS",
        strategy_intelligence_downside_risk_status="PASS",
        lot_first_rebatch_skip_reason="lot_minimum_exceeds_quality_authorized_target",
        target_weight_resolution={
            "status": "PASS",
            "resolved_weight": 0.0,
            "zero_weight_reason": "lot_minimum_exceeds_quality_authorized_target",
            "quality_target_upper_bound_enforced": True,
            "adjustments": [
                {
                    "authority": "ADAPTIVE_BUY_QUALITY_AUTHORITY",
                    "pre_quality_base_weight": pre_quality_base_target_weight,
                    "post_quality_target_weight": quality_authorized_target_weight,
                    "quality_action": "REDUCED_ALLOCATION_ONLY",
                    "quality_target_upper_bound_enforced": True,
                }
            ],
            "lot_aware_final_reallocation": {
                "blocker_reason": "lot_minimum_exceeds_quality_authorized_target",
                "minimum_executable_one_lot_authority": {},
            },
        },
        phase29_l19_lot_resolution={
            **_entry_lot_resolution(100),
            "blocked_reason": "lot_minimum_exceeds_quality_authorized_target",
            "blocker_reason": "lot_minimum_exceeds_quality_authorized_target",
            "one_lot_quantity": 100,
            "one_lot_weight": round(reference_price * 100 / 1_000_000.0, 10),
            "one_lot_notional": reference_price * 100,
            "one_lot_feasibility_status": "PASS",
            "minimum_executable_one_lot_authority": {},
            "minimum_executable_one_lot_admitted": False,
            "pc_positive_executable_quantity_authority": {"status": "NOT_APPLICABLE", "final_allocated_quantity": 0},
        },
    )
    row.update(overrides)
    return row


def _add(
    symbol: str,
    *,
    current_quantity: int,
    current_weight: float = 0.05,
    single_name_cap: float = 0.30,
    rank: int = 3,
    reference_price: float = 1_000.0,
    **overrides,
) -> dict:
    row = {
        "security_code": symbol,
        "current_position": True,
        "membership_intent": "RETAIN",
        "pm_action": "ADD",
        "position_campaign_id": f"pc-{symbol}-0001",
        "pm_decision_id": f"pm-{symbol}",
        "current_quantity": current_quantity,
        "current_weight": current_weight,
        "target_weight": current_weight,
        "single_name_cap": single_name_cap,
        "runtime_opportunity_score": 0.85,
        "input_opportunity_rank": rank,
        "quality_score": 0.78,
        "expected_edge_improvement_state": "IMPROVING",
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "add_allocation_eligibility_status": "PASS",
        "same_campaign_continuation_status": "CONTINUING",
        "no_loss_averaging_status": "PASS",
        "reference_price": reference_price,
        "trading_unit": 100,
    }
    row.update(overrides)
    return row
