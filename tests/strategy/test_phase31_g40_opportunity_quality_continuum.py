from __future__ import annotations

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


def test_phase31_g40_apply_priority_materializes_new_evidence_without_changing_legacy_order() -> None:
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
    assert by_symbol["94320"]["canonical_opportunity_quality_class"] == "STRONG"
    assert by_symbol["27780"]["canonical_opportunity_quality_class"] == "WEAK_VALID"
    assert by_symbol["94320"]["marginal_capital_value_class"] == "ELIGIBLE_STRONG"
    assert by_symbol["27780"]["marginal_capital_value_class"] == "ELIGIBLE_COMPARABLE"
    assert result["authority"]["legacy_classifier_reexecuted"] is False


def _quality(row: dict) -> str:
    return str(marginal_capital_value.classify_opportunity_quality(row)["canonical_opportunity_quality_class"])


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
