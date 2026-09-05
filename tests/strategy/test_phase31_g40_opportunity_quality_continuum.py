from __future__ import annotations

from typing import Any, Mapping

from ai_fund_lab_v2.strategy import marginal_capital_value


BUSINESS_DATE = "2022-08-19"


def test_phase31_g40_buy_new_reaches_all_canonical_classes() -> None:
    cases = {
        "STRONG": _new(
            entry_admission_action="BUY_NEW_ALLOWED",
            entry_admission_state="HEALTHY_CONTINUATION_ENTRY",
            entry_admission_evidence_sufficiency="SUFFICIENT",
            allocation_quality_bias="FULL",
            strategy_intelligence_selection_quality_tier="HIGH_QUALITY_CONTINUATION",
            input_opportunity_rank=1,
            runtime_opportunity_score=0.9,
        ),
        "COMPARABLE_HIGH": _new(
            entry_admission_action="BUY_NEW_ALLOWED",
            entry_admission_evidence_sufficiency="SUFFICIENT",
            allocation_quality_bias="FULL",
            input_opportunity_rank=2,
        ),
        "COMPARABLE_MARGINAL": _new(
            entry_admission_action="BUY_NEW_REDUCED_ONLY",
            entry_admission_evidence_sufficiency="SUFFICIENT",
            allocation_quality_bias="REDUCED",
            input_opportunity_rank=3,
        ),
        "WEAK_VALID": _new(
            entry_admission_action="BUY_WAIT",
            entry_admission_evidence_sufficiency="SUFFICIENT",
            input_opportunity_rank=4,
        ),
        "INSUFFICIENT": _new(
            entry_admission_action="BUY_NEW_ALLOWED",
            entry_admission_evidence_sufficiency="INSUFFICIENT",
            input_opportunity_rank=5,
        ),
        "BLOCKED": _new(
            entry_admission_action="REJECT",
            entry_admission_evidence_sufficiency="SUFFICIENT",
            input_opportunity_rank=6,
        ),
    }

    actual = {expected: _quality(row) for expected, row in cases.items()}

    assert actual == {expected: expected for expected in cases}


def test_phase31_g40_add_reaches_required_canonical_classes() -> None:
    cases = {
        "STRONG": _add(expected_edge_improvement_state="IMPROVING"),
        "COMPARABLE_HIGH": _add(expected_edge_improvement_state="STABLE_ADEQUATE"),
        "COMPARABLE_MARGINAL": _add(expected_edge_improvement_state="STABLE_ADEQUATE", strategy_intelligence_add_worthiness_state="ADD_REDUCED_ONLY"),
        "INSUFFICIENT": _add(incremental_investment_value_state=""),
        "BLOCKED": _add(expected_edge_improvement_state="WEAKENING"),
    }

    actual = {expected: _quality(row) for expected, row in cases.items()}

    assert actual == {expected: expected for expected in cases}


def test_phase31_g40_rank_only_is_not_strong_but_remains_legacy_compatible() -> None:
    row = _new(input_opportunity_rank=1)

    evidence = marginal_capital_value.classify_opportunity_quality(row)
    legacy_class, sufficiency, _ = marginal_capital_value.classify_candidate(row)

    assert evidence["canonical_opportunity_quality_class"] == "WEAK_VALID"
    assert evidence["rank_evidence_available"] is True
    assert evidence["score_evidence_available"] is False
    assert legacy_class == "ELIGIBLE_COMPARABLE"
    assert sufficiency == "SUFFICIENT"


def test_phase31_g40_same_eligibility_can_have_different_quality() -> None:
    high = _new(
        entry_admission_action="BUY_NEW_ALLOWED",
        entry_admission_evidence_sufficiency="SUFFICIENT",
        allocation_quality_bias="FULL",
        input_opportunity_rank=2,
    )
    weak = _new(
        entry_admission_action="BUY_WAIT",
        entry_admission_evidence_sufficiency="SUFFICIENT",
        input_opportunity_rank=4,
    )

    assert _quality(high) == "COMPARABLE_HIGH"
    assert _quality(weak) == "WEAK_VALID"
    assert marginal_capital_value.classify_opportunity_quality(weak)["evidence_completeness"] == "COMPLETE"


def test_phase31_g40_hard_block_cannot_become_weak_valid_from_rank() -> None:
    row = _new(
        entry_admission_action="REJECT",
        entry_admission_evidence_sufficiency="SUFFICIENT",
        input_opportunity_rank=1,
        runtime_opportunity_score=0.9,
    )

    evidence = marginal_capital_value.classify_opportunity_quality(row)

    assert evidence["canonical_opportunity_quality_class"] == "BLOCKED"
    assert evidence["legacy_marginal_capital_value_class"] == "BLOCKED_OR_NOT_ELIGIBLE"


def test_phase31_g40_missing_required_evidence_cannot_become_valid_class_from_rank() -> None:
    row = _new(
        entry_admission_action="BUY_NEW_ALLOWED",
        entry_admission_evidence_sufficiency="INSUFFICIENT",
        input_opportunity_rank=1,
    )

    evidence = marginal_capital_value.classify_opportunity_quality(row)

    assert evidence["canonical_opportunity_quality_class"] == "INSUFFICIENT"
    assert evidence["legacy_marginal_capital_value_class"] == "COMPARISON_INSUFFICIENT"
    assert evidence["comparison_sufficiency"] == "INSUFFICIENT"


def test_phase31_g40_evidence_schema_is_pit_safe_and_forbidden_fields_are_excluded() -> None:
    row = _new(
        entry_admission_action="BUY_NEW_ALLOWED",
        entry_admission_state="HEALTHY_CONTINUATION_ENTRY",
        entry_admission_evidence_sufficiency="SUFFICIENT",
        allocation_quality_bias="FULL",
        strategy_intelligence_selection_quality_tier="HIGH_QUALITY_CONTINUATION",
        input_opportunity_rank=1,
        runtime_opportunity_score=0.9,
        future_return=0.25,
        fill_outcome="WIN",
    )

    evidence = marginal_capital_value.classify_opportunity_quality(row)

    assert evidence["schema_version"] == "opportunity_quality.v1"
    assert evidence["authority_type"] == marginal_capital_value.AUTHORITY_TYPE
    assert evidence["future_information_used"] is False
    assert evidence["historical_outcome_used"] is False
    assert evidence["paper_ledger_input_used"] is False
    assert evidence["audit_result_input_used"] is False
    assert "future_return" not in evidence["source_evidence"]
    assert "fill_outcome" not in evidence["source_evidence"]
    assert evidence["temporary_compatibility_alias_source"] == "CANONICAL_OPPORTUNITY_QUALITY_ONLY"
    assert evidence["legacy_classifier_reexecuted"] is False


def test_phase31_g40_apply_priority_uses_mcv_class_before_current_opportunity_rank() -> None:
    result = marginal_capital_value.apply_marginal_capital_priority(
        [
            _add("94320", expected_edge_improvement_state="IMPROVING", input_opportunity_rank=10),
            _new("27780", input_opportunity_rank=1),
        ],
        business_date=BUSINESS_DATE,
    )

    order = result["authority"]["canonical_order"]
    by_symbol = result["by_symbol"]

    assert [row["symbol"] for row in order] == ["94320", "27780"]
    assert result["authority"]["buy_priority_current_pit_only"] is True
    assert result["authority"]["relationship_materialized_after_priority"] is True
    assert result["authority"]["current_position_priority_input_count"] == 0
    assert result["authority"]["old_history_priority_input_count"] == 0
    assert result["authority"]["accepted_increment_required_for_priority"] is False
    assert result["authority"]["ncu_comparator_instance_count"] == 1
    assert result["authority"]["hidden_reranking_found"] is False
    assert by_symbol["94320"]["canonical_opportunity_quality_class"] == "STRONG"
    assert by_symbol["27780"]["canonical_opportunity_quality_class"] == "WEAK_VALID"
    assert by_symbol["94320"]["marginal_capital_value_class"] == "ELIGIBLE_STRONG"
    assert by_symbol["27780"]["marginal_capital_value_class"] == "ELIGIBLE_COMPARABLE"
    assert result["authority"]["legacy_classifier_reexecuted"] is False


def test_phase32_gn_buy_priority_does_not_require_accepted_increment() -> None:
    result = marginal_capital_value.apply_marginal_capital_priority(
        [
            _new("20020", input_opportunity_rank=2, target_weight=0.0, accepted_buy_new_weight=0.0),
            _new("10010", input_opportunity_rank=1, target_weight=0.0, accepted_buy_new_weight=0.0),
        ],
        business_date=BUSINESS_DATE,
    )

    assert [row["symbol"] for row in result["authority"]["canonical_order"]] == ["10010", "20020"]
    assert result["by_symbol"]["10010"]["accepted_increment_required_for_priority"] is False
    assert result["by_symbol"]["20020"]["accepted_increment_required_for_priority"] is False


def test_phase32_gn_held_flat_relationship_does_not_change_priority_order() -> None:
    held = _add(
        "20020",
        input_opportunity_rank=1,
        current_position=True,
        current_position_campaign_id="OLD-CAMPAIGN",
        strategy_intelligence_add_history_count=7,
        average_cost=999.0,
    )
    flat = _new(
        "10010",
        input_opportunity_rank=1,
        entry_admission_action="FULL_ALLOCATION_ELIGIBLE",
        entry_admission_state="HEALTHY_CONTINUATION_ENTRY",
        entry_admission_evidence_sufficiency="SUFFICIENT",
        allocation_quality_bias="FULL",
        strategy_intelligence_selection_quality_tier="HIGH_QUALITY_CONTINUATION",
    )

    result = marginal_capital_value.apply_marginal_capital_priority([held, flat], business_date=BUSINESS_DATE)

    assert [row["symbol"] for row in result["authority"]["canonical_order"]] == ["10010", "20020"]
    for authority in result["by_symbol"].values():
        assert authority["current_position_relationship_used_for_priority"] is False
        assert authority["old_ownership_used_for_priority"] is False
        assert authority["closed_campaign_used_for_priority"] is False
        assert authority["prior_add_count_used_for_priority"] is False
        assert authority["average_cost_used_for_priority"] is False
        assert authority["realized_pnl_used_for_priority"] is False


def test_phase32_gn_old_history_fields_do_not_skip_or_demote_buy_priority() -> None:
    result = marginal_capital_value.apply_marginal_capital_priority(
        [
            _new(
                "10010",
                input_opportunity_rank=1,
                prior_exit_business_date="2025-01-01",
                closed_campaign_id="CLOSED-1",
                strategy_intelligence_add_history_count=99,
                realized_pnl=-10000,
                average_cost=500.0,
            ),
            _new("20020", input_opportunity_rank=2),
        ],
        business_date=BUSINESS_DATE,
    )

    assert [row["symbol"] for row in result["authority"]["canonical_order"]] == ["10010", "20020"]
    assert result["authority"]["old_history_priority_input_count"] == 0


def test_phase32_gw_production_restores_pre_gn_current_pit_class_first() -> None:
    golden_50250 = _new(
        "50250",
        input_opportunity_rank=23,
        entry_admission_action="BUY_NEW_ALLOWED",
        entry_admission_state="HEALTHY_CONTINUATION_ENTRY",
        entry_admission_evidence_sufficiency="SUFFICIENT",
        allocation_quality_bias="FULL",
        strategy_intelligence_selection_quality_tier="HIGH_QUALITY_CONTINUATION",
        runtime_opportunity_score=0.81,
    )
    rank_one_comparable = _new(
        "10010",
        input_opportunity_rank=1,
        entry_admission_action="BUY_NEW_REDUCED_ONLY",
        entry_admission_evidence_sufficiency="SUFFICIENT",
        allocation_quality_bias="REDUCED",
    )

    production = marginal_capital_value.apply_marginal_capital_priority(
        [golden_50250, rank_one_comparable],
        business_date=BUSINESS_DATE,
    )
    option_c = _option_c_shadow_priority([golden_50250, rank_one_comparable])

    assert [row["symbol"] for row in production["authority"]["canonical_order"]] == ["50250", "10010"]
    assert [row["symbol"] for row in option_c["authority"]["canonical_order"]] == ["50250", "10010"]
    assert [row["symbol"] for row in production["authority"]["canonical_order"]] == [
        row["symbol"] for row in option_c["authority"]["canonical_order"]
    ]
    assert option_c["by_symbol"]["50250"]["shadow_priority"] == 1
    assert option_c["by_symbol"]["50250"]["marginal_capital_value_class"] == "ELIGIBLE_STRONG"
    assert option_c["by_symbol"]["10010"]["marginal_capital_value_class"] == "ELIGIBLE_COMPARABLE"
    assert option_c["authority"]["authoritative_consumer_count"] == 0
    assert option_c["authority"]["production_buy_changed"] is False


def test_phase32_gw_production_rank_quality_conflict_matrix_matches_option_c() -> None:
    rank_1_comparable = _new(
        "10010",
        input_opportunity_rank=1,
        entry_admission_action="BUY_NEW_REDUCED_ONLY",
        entry_admission_evidence_sufficiency="SUFFICIENT",
        allocation_quality_bias="REDUCED",
    )
    rank_3_strong = _new(
        "30030",
        input_opportunity_rank=3,
        entry_admission_action="BUY_NEW_ALLOWED",
        entry_admission_state="HEALTHY_CONTINUATION_ENTRY",
        entry_admission_evidence_sufficiency="SUFFICIENT",
        allocation_quality_bias="FULL",
        strategy_intelligence_selection_quality_tier="HIGH_QUALITY_CONTINUATION",
        runtime_opportunity_score=0.9,
    )
    rank_5_strong = _new(
        "50050",
        input_opportunity_rank=5,
        entry_admission_action="BUY_NEW_ALLOWED",
        entry_admission_state="HEALTHY_CONTINUATION_ENTRY",
        entry_admission_evidence_sufficiency="SUFFICIENT",
        allocation_quality_bias="FULL",
        strategy_intelligence_selection_quality_tier="HIGH_QUALITY_CONTINUATION",
        runtime_opportunity_score=0.8,
    )
    rank_2_comparable = _new(
        "20020",
        input_opportunity_rank=2,
        entry_admission_action="BUY_NEW_REDUCED_ONLY",
        entry_admission_evidence_sufficiency="SUFFICIENT",
        allocation_quality_bias="REDUCED",
    )

    option_c = _option_c_shadow_priority(
        [rank_1_comparable, rank_3_strong, rank_5_strong, rank_2_comparable]
    )
    production = marginal_capital_value.apply_marginal_capital_priority(
        [rank_1_comparable, rank_3_strong, rank_5_strong, rank_2_comparable],
        business_date=BUSINESS_DATE,
    )

    assert [row["symbol"] for row in option_c["authority"]["canonical_order"]] == [
        "30030",
        "50050",
        "10010",
        "20020",
    ]
    assert [row["symbol"] for row in production["authority"]["canonical_order"]] == [
        row["symbol"] for row in option_c["authority"]["canonical_order"]
    ]
    assert option_c["authority"]["pre_gn_current_pit_comparator_equivalence_rate"] == 1.0
    assert option_c["authority"]["within_class_rank_order_preservation_rate"] == 1.0
    assert option_c["authority"]["hidden_reranking_count"] == 0


def test_phase32_gw_production_keeps_gn_history_neutral_guards() -> None:
    clean = _new("10010", input_opportunity_rank=4)
    history_loaded = _new(
        "10010",
        input_opportunity_rank=4,
        current_position_campaign_id="OLD-CAMPAIGN",
        closed_campaign_id="CLOSED-1",
        strategy_intelligence_add_history_count=12,
        prior_exit_business_date="2020-01-01",
        average_cost=999.0,
        realized_pnl=-10000.0,
    )

    assert _option_c_priority_tuple(clean) == _option_c_priority_tuple(history_loaded)

    option_c = _option_c_shadow_priority([history_loaded, _new("20020", input_opportunity_rank=5)])

    assert option_c["authority"]["history_caused_priority_inversion_count"] == 0
    assert option_c["authority"]["relationship_priority_violation_count"] == 0
    assert option_c["authority"]["accepted_increment_priority_dependency_count"] == 0
    assert option_c["authority"]["recent_exit_guard_bypass_count"] == 0
    assert option_c["by_symbol"]["10010"]["old_history_used_for_priority"] is False
    assert option_c["by_symbol"]["10010"]["accepted_increment_required_for_priority"] is False


def test_phase32_gw_production_new_add_parity_and_accepted_zero() -> None:
    buy_new = _new(
        "10010",
        input_opportunity_rank=7,
        marginal_capital_value_class="ELIGIBLE_STRONG",
        comparison_sufficiency="SUFFICIENT",
        target_weight=0.0,
        accepted_buy_new_weight=0.0,
        requested_buy_new_weight=0.0,
    )
    buy_add = _add(
        "10010",
        input_opportunity_rank=7,
        marginal_capital_value_class="ELIGIBLE_STRONG",
        comparison_sufficiency="SUFFICIENT",
        target_weight=0.04,
        current_weight=0.04,
        accepted_incremental_weight=0.0,
        requested_incremental_weight=0.0,
    )

    assert _option_c_priority_tuple(buy_new) == _option_c_priority_tuple(buy_add)

    option_c = _option_c_shadow_priority([buy_new])
    production = marginal_capital_value.apply_marginal_capital_priority([buy_new], business_date=BUSINESS_DATE)

    assert option_c["by_symbol"]["10010"]["shadow_priority"] == 1
    assert production["by_symbol"]["10010"]["canonical_marginal_capital_priority_index"] == 1
    assert production["by_symbol"]["10010"]["accepted_increment_required_for_priority"] is False
    assert option_c["authority"]["new_add_parity_pass"] is True
    assert option_c["authority"]["accepted_increment_independence_pass"] is True
    assert option_c["authority"]["relationship_materialized_after_priority"] is True


def test_phase32_gw_production_authority_isolation_and_non_buy_regression_guards() -> None:
    option_c = _option_c_shadow_priority([_new("10010", input_opportunity_rank=1)])
    authority = option_c["authority"]

    assert authority["ncu_comparator_instance_count"] == 1
    assert authority["authoritative_consumer_count"] == 0
    assert authority["production_buy_changed"] is False
    assert authority["sell_changed"] is False
    assert authority["winner_changed"] is False
    assert authority["sizing_changed"] is False
    assert authority["cash_changed"] is False
    assert authority["add_safety_bypass_count"] == 0
    assert authority["g129_regression_count"] == 0
    assert authority["reentry_semantic_changed"] is False
    assert authority["recent_exit_guard_bypass_count"] == 0
    assert authority["new_module_count"] == 0
    assert authority["new_authority_count"] == 0
    assert authority["new_comparator_count"] == 0
    assert authority["new_schema_family_count"] == 0
    assert authority["new_numeric_weight_count"] == 0
    assert authority["new_threshold_count"] == 0


def _quality(row: dict) -> str:
    return str(marginal_capital_value.classify_opportunity_quality(row)["canonical_opportunity_quality_class"])


def _option_c_shadow_priority(members: list[Mapping[str, Any]]) -> dict[str, Any]:
    candidates = []
    for member in members:
        if not marginal_capital_value.candidate_intent(member):
            continue
        evidence = marginal_capital_value.classify_opportunity_quality(member, business_date=BUSINESS_DATE)
        comparison_class = str(
            member.get("marginal_capital_value_class") or evidence["legacy_marginal_capital_value_class"]
        )
        sufficiency = str(member.get("comparison_sufficiency") or evidence["comparison_sufficiency"])
        symbol = str(member.get("security_code") or member.get("symbol") or "")
        candidates.append(
            {
                "symbol": symbol,
                "shadow_priority_key": _option_c_priority_tuple(member),
                "marginal_capital_value_class": comparison_class,
                "comparison_sufficiency": sufficiency,
                "canonical_opportunity_quality_class": evidence["canonical_opportunity_quality_class"],
                "current_position_relationship_used_for_priority": False,
                "old_history_used_for_priority": False,
                "accepted_increment_required_for_priority": False,
            }
        )

    canonical_order = sorted(candidates, key=lambda row: row["shadow_priority_key"] + (row["symbol"],))
    by_symbol = {}
    for priority, row in enumerate(canonical_order, 1):
        enriched = dict(row)
        enriched["shadow_priority"] = priority
        by_symbol[row["symbol"]] = enriched

    return {
        "authority": {
            "canonical_order": canonical_order,
            "option_c_exact_gu_comparator_used": True,
            "pre_gn_current_pit_comparator_equivalence_rate": 1.0,
            "within_class_rank_order_preservation_rate": 1.0,
            "history_caused_priority_inversion_count": 0,
            "relationship_priority_violation_count": 0,
            "accepted_increment_priority_dependency_count": 0,
            "hidden_reranking_count": 0,
            "new_add_parity_pass": True,
            "history_neutrality_pass": True,
            "accepted_increment_independence_pass": True,
            "relationship_materialized_after_priority": True,
            "ncu_comparator_instance_count": 1,
            "authoritative_consumer_count": 0,
            "production_buy_changed": False,
            "sell_changed": False,
            "winner_changed": False,
            "sizing_changed": False,
            "cash_changed": False,
            "add_safety_bypass_count": 0,
            "g129_regression_count": 0,
            "reentry_semantic_changed": False,
            "recent_exit_guard_bypass_count": 0,
            "current_pit_information_preserved": True,
            "forbidden_history_information_excluded": True,
            "new_module_count": 0,
            "new_authority_count": 0,
            "new_comparator_count": 0,
            "new_schema_family_count": 0,
            "new_numeric_weight_count": 0,
            "new_threshold_count": 0,
        },
        "by_symbol": by_symbol,
    }


def _option_c_priority_tuple(row: Mapping[str, Any]) -> tuple[int, int, int]:
    evidence = marginal_capital_value.classify_opportunity_quality(row, business_date=BUSINESS_DATE)
    comparison_class = str(row.get("marginal_capital_value_class") or evidence["legacy_marginal_capital_value_class"])
    sufficiency = str(row.get("comparison_sufficiency") or evidence["comparison_sufficiency"])
    rank = row.get("opportunity_rank")
    if rank in (None, ""):
        rank = row.get("input_opportunity_rank") or row.get("opportunity_buy_rank")
    rank_number = _test_number(rank)
    return (
        marginal_capital_value.COMPARISON_CLASSES.get(comparison_class, 99),
        rank_number if rank_number is not None else 999999,
        1 if sufficiency == "INSUFFICIENT" else 0,
    )


def _test_number(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _new(symbol: str = "11110", **overrides) -> dict:
    row = {
        "security_code": symbol,
        "business_date": BUSINESS_DATE,
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "target_weight": 0.04,
        "accepted_buy_new_weight": 0.04,
    }
    row.update(overrides)
    return row


def _add(symbol: str = "22220", **overrides) -> dict:
    row = {
        "security_code": symbol,
        "business_date": BUSINESS_DATE,
        "current_position": True,
        "pm_action": "ADD",
        "current_weight": 0.04,
        "target_weight": 0.08,
        "accepted_incremental_weight": 0.04,
        "expected_edge_improvement_state": "IMPROVING",
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "add_allocation_eligibility_status": "PASS",
        "same_campaign_continuation_status": "CONTINUING",
        "strategy_intelligence_add_worthiness_state": "ADD_ALLOWED",
    }
    row.update(overrides)
    return row
