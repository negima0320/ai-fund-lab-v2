from __future__ import annotations

from ai_fund_lab_v2.strategy import portfolio_construction


def _semantic(row: dict) -> dict:
    return portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-09-01", is_buy_new=True)


def _recovery(row: dict) -> dict:
    return portfolio_construction._reentry_recovery_evidence(
        row=row,
        semantic=_semantic(row),
        capacity_ratio=0.01,
        liquidity_status="WATCH",
    )


def _base(**overrides: object) -> dict:
    return {
        "code": "11110",
        "prior_exit_business_date": "2022-08-26",
        "prior_exit_reason": "EXIT_BY_TREND_AND_EDGE_BREAK",
        "runtime_opportunity_score": -0.05,
        "opportunity_buy_rank": 2,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "trend_close_over_ma_20d": 1.02,
        "price_momentum_return_20d": 0.03,
        "corporate_action_status": "NO_EVENT",
        "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
        "entry_admission_action": "BUY_NEW_ALLOWED",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "strategy_intelligence_continuation_quality_status": "PASS",
        "strategy_intelligence_downside_risk_status": "PASS",
        **overrides,
    }


def test_phase30_z_genuine_recovery_allows_reentry_even_with_uncalibrated_negative_edge() -> None:
    recovery = _recovery(_base(runtime_opportunity_score=-0.18))

    assert recovery["reentry_recovery_status"] == "PASS"
    assert recovery["reentry_score_gate_status"] == "DIAGNOSTIC_ONLY"
    assert recovery["reentry_recovery_reason"] == "reentry_recovery_qualified"


def test_phase30_z_partial_technical_recovery_no_longer_proves_reentry() -> None:
    trend_only = _recovery(_base(price_momentum_return_20d=-0.01))
    momentum_only = _recovery(_base(trend_close_over_ma_20d=0.99))

    assert trend_only["reentry_recovery_status"] == "FAIL_CLOSED"
    assert trend_only["reentry_recovery_reason"] == "reentry_momentum_recovery_not_satisfied"
    assert momentum_only["reentry_recovery_status"] == "FAIL_CLOSED"
    assert momentum_only["reentry_recovery_reason"] == "reentry_trend_recovery_not_satisfied"


def test_phase30_z_unknown_prior_exit_context_fails_safe_to_review() -> None:
    recovery = _recovery(_base(prior_exit_reason="EXIT"))

    assert recovery["previous_exit_reason_class"] == "GENERIC"
    assert recovery["reentry_recovery_status"] == "REVIEW_REQUIRED"
    assert recovery["reentry_recovery_reason"] == "insufficient_prior_exit_context"


def test_phase30_z_entry_admission_blocks_unresolved_reversal_or_overheated_reentry() -> None:
    reversal = _recovery(
        _base(
            prior_exit_reason="REVERSAL_RISK_EXIT",
            entry_admission_state="REVERSAL_RISK_ENTRY",
            entry_admission_action="BUY_WAIT",
        )
    )
    overheated = _recovery(
        _base(
            entry_admission_state="OVERHEATED_DECELERATING_ENTRY",
            entry_admission_action="BUY_WAIT",
        )
    )

    assert reversal["reentry_recovery_status"] == "FAIL_CLOSED"
    assert reversal["reentry_recovery_reason"] == "reentry_entry_admission_not_allowed"
    assert overheated["reentry_recovery_status"] == "FAIL_CLOSED"
    assert overheated["reentry_recovery_reason"] == "reentry_entry_admission_not_allowed"


def test_phase30_z_repeated_unresolved_churn_blocks_reentry_without_using_pnl_outcomes() -> None:
    recovery = _recovery(_base(prior_same_symbol_exit_count=2, price_momentum_return_20d=-0.01))

    assert recovery["reentry_recovery_status"] == "FAIL_CLOSED"
    assert recovery["reentry_recovery_reason"] == "reentry_repeated_unresolved_churn"
    assert "pnl" not in str(recovery).lower()


def test_phase30_z_buy_new_without_prior_exit_remains_unaffected() -> None:
    row = _base()
    row.pop("prior_exit_business_date")
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-09-01", is_buy_new=True)
    recovery = portfolio_construction._reentry_recovery_evidence(
        row=row,
        semantic=semantic,
        capacity_ratio=0.01,
        liquidity_status="WATCH",
    )

    assert semantic["semantic_buy_type"] == "BUY_NEW"
    assert recovery["reentry_recovery_status"] == "NOT_APPLICABLE"


def test_phase30_z_genuine_recovery_after_prior_failure_can_still_reenter() -> None:
    recovery = _recovery(_base(prior_same_symbol_exit_count=2))

    assert recovery["reentry_recovery_status"] == "PASS"
    assert recovery["reentry_recovery_reason"] == "reentry_recovery_qualified"


def _eligibility(
    row: dict,
    *,
    business_date: str = "2022-09-01",
    liquidity_status: str = "WATCH",
    **overrides: object,
) -> dict:
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date=business_date, is_buy_new=True)
    recovery = portfolio_construction._reentry_recovery_evidence(
        row=row,
        semantic=semantic,
        capacity_ratio=0.01,
        liquidity_status=liquidity_status,
    )
    params = {
        "row": row,
        "business_date": business_date,
        "is_buy_new": True,
        "semantic": semantic,
        "recovery": recovery,
        "liquidity_status": liquidity_status,
        "target_membership": True,
        "normal_target_weight": 0.05,
        "target_weight_reason": "target_member_competition_eligible",
        "zero_weight_reason": "",
        "review_reason": "",
    }
    params.update(overrides)
    return portfolio_construction._canonical_reentry_semantic_eligibility(**params)


def test_phase32_ag_positive_broker_support_reason_code_does_not_safety_block_reentry() -> None:
    row = _base(
        code="83060",
        prior_exit_business_date="2022-10-04",
        prior_exit_reason="trend_and_opportunity_broken",
        prior_exit_reason_codes=["trend_and_opportunity_broken"],
        reason_codes=[
            "BROKER_PRODUCT_CATEGORY_SUPPORTED",
            "buy_quality_full_allocation_eligible",
            "candidate_eligible",
            "opportunity_rank_preserved",
            "reentry_recovery_qualified",
        ],
        runtime_opportunity_score=-0.16383348,
        opportunity_buy_rank=10,
        trend_close_over_ma_20d=1.055926,
        price_momentum_return_20d=0.033324,
        corporate_action_status="NO_EVENT",
        entry_admission_state="CONTINUATION_WITH_CAUTION",
        entry_admission_action="BUY_NEW_REDUCED_ONLY",
        strategy_intelligence_continuation_quality_status="PASS",
        strategy_intelligence_downside_risk_status="PASS",
    )

    assert portfolio_construction._reentry_safety_status(row=row, liquidity_status="NORMAL", reason_text="") == "PASS"

    eligibility = _eligibility(
        row,
        business_date="2022-10-25",
        liquidity_status="NORMAL",
        normal_target_weight=0.032258,
    )

    assert eligibility["safety_restriction_status"] == "PASS"
    assert eligibility["reentry_semantic_state"] == "REENTRY_ELIGIBLE"
    assert eligibility["eligibility_status"] == "PASS"


def test_phase32_ag_positive_cash_and_safety_support_text_does_not_safety_block() -> None:
    row = _base(
        reason_codes=[
            "BROKER_PRODUCT_CATEGORY_SUPPORTED",
            "cash_optionality_preserved",
            "safety_hard_cap_preserved",
        ],
        corporate_action_status="NO_EVENT",
    )

    assert (
        portfolio_construction._reentry_safety_status(
            row=row,
            liquidity_status="NORMAL",
            reason_text="sufficient_buying_power cash_availability safety_pass",
        )
        == "PASS"
    )


def test_phase32_ag_explicit_negative_safety_evidence_still_fails_closed() -> None:
    negative_cases = [
        ({"broker_eligibility_status": "FAIL_CLOSED"}, "broker status"),
        ({"reason_codes": ["broker_product_category_unsupported"]}, "broker code"),
        ({"reason_codes": ["buying_power_blocked"]}, "buying power"),
        ({"safety_hard_cap_status": "VIOLATION"}, "safety hard cap"),
        ({"reason_codes": ["corporate_action_blocking"]}, "corporate action"),
        ({"reason_codes": ["explicit_safety_prohibition"]}, "explicit safety"),
    ]

    for extra, label in negative_cases:
        row = _base(corporate_action_status="NO_EVENT", **extra)
        assert portfolio_construction._reentry_safety_status(row=row, liquidity_status="NORMAL", reason_text="") == "FAIL_CLOSED", label


def test_phase32_ag_liquidity_unknown_remains_review_required() -> None:
    row = _base(corporate_action_status="NO_EVENT", reason_codes=["BROKER_PRODUCT_CATEGORY_SUPPORTED"])

    assert (
        portfolio_construction._reentry_safety_status(row=row, liquidity_status="UNKNOWN", reason_text="")
        == "REVIEW_REQUIRED"
    )


def test_phase32_ai_positive_support_taxonomy_does_not_safety_block() -> None:
    positive_cases = [
        ({"broker_eligibility_status": "PASS", "reason_codes": ["BROKER_PRODUCT_CATEGORY_SUPPORTED"]}, "broker supported"),
        ({"broker_product_category_status": "SUPPORTED"}, "broker category supported"),
        ({"buying_power_status": "SUFFICIENT"}, "buying power sufficient"),
        ({"cash_buying_power_status": "AVAILABLE"}, "cash available"),
        ({"safety_status": "PASS"}, "safety pass"),
        ({"safety_hard_cap_preservation_status": "PRESERVED"}, "hard cap preserved"),
        ({"corporate_action_blocking_status": "NO_EVENT"}, "corporate no event"),
        ({"execution_safety_status": "OK"}, "execution safety ok"),
    ]

    for extra, label in positive_cases:
        row = _base(corporate_action_status="NO_EVENT", **extra)
        assert portfolio_construction._reentry_safety_status(row=row, liquidity_status="NORMAL", reason_text="") == "PASS", label


def test_phase32_ai_unknown_and_review_safety_taxonomy_requires_review() -> None:
    review_cases = [
        ({"reason_codes": ["BROKER_PRODUCT_CATEGORY_UNKNOWN"]}, "broker unknown code"),
        ({"broker_eligibility_status": "UNKNOWN"}, "broker unknown status"),
        ({"broker_product_category_status": "MISSING"}, "broker category missing"),
        ({"safety_status": "REVIEW_REQUIRED"}, "safety review"),
        ({"execution_safety_status": "UNCLASSIFIED_STATUS"}, "unexpected structured status"),
    ]

    for extra, label in review_cases:
        row = _base(corporate_action_status="NO_EVENT", **extra)
        assert (
            portfolio_construction._reentry_safety_status(row=row, liquidity_status="NORMAL", reason_text="")
            == "REVIEW_REQUIRED"
        ), label


def test_phase32_ai_explicit_blocking_alias_taxonomy_fails_closed() -> None:
    negative_cases = [
        ({"reason_codes": ["BROKER_PRODUCT_CATEGORY_UNSUPPORTED"]}, "broker unsupported"),
        ({"broker_eligible": False}, "broker ineligible"),
        ({"tradable": False}, "not tradable"),
        ({"reason_codes": ["INSUFFICIENT_BUYING_POWER"]}, "insufficient buying power"),
        ({"reason_codes": ["BUYING_POWER_AFTER_CASH_BUFFER"]}, "cash buffer buying power"),
        ({"reason_codes": ["INSUFFICIENT_CASH"]}, "insufficient cash"),
        ({"reason_codes": ["SAFETY_HARD_CAP_VIOLATION"]}, "safety hard cap violation"),
        ({"reason_codes": ["SAFETY_CAP_BOUND"]}, "safety cap bound"),
        ({"reason_codes": ["MINIMUM_LOT_EXCEEDS_SAFETY_HARD_CAP"]}, "minimum lot safety hard cap"),
        ({"reason_codes": ["explicit_safety_prohibition"]}, "explicit safety prohibition"),
        ({"reason_codes": ["CORPORATE_ACTION_BLOCKING"]}, "corporate action blocking"),
        ({"reason_codes": ["CORPORATE_ACTION_BLOCK"]}, "corporate action block alias"),
        ({"reason_codes": ["CORPORATE_EVENT_BLOCK"]}, "corporate event block alias"),
        ({"reason_codes": ["liquidity_block"]}, "liquidity block"),
        ({"safety_status": "FAILED"}, "failed status alias"),
        ({"execution_safety_status": "PROHIBITED"}, "prohibited status alias"),
    ]

    for extra, label in negative_cases:
        row = _base(corporate_action_status="NO_EVENT", **extra)
        assert portfolio_construction._reentry_safety_status(row=row, liquidity_status="NORMAL", reason_text="") == "FAIL_CLOSED", label


def test_phase32_ag_reentry_precedence_keeps_earlier_gates_authoritative() -> None:
    cooldown_row = _base(
        prior_exit_business_date="2022-08-31",
        reason_codes=["BROKER_PRODUCT_CATEGORY_SUPPORTED"],
        corporate_action_status="NO_EVENT",
    )
    recovery_row = _base(
        opportunity_buy_rank=11,
        reason_codes=["BROKER_PRODUCT_CATEGORY_SUPPORTED"],
        corporate_action_status="NO_EVENT",
    )
    current_candidate_row = _base(reason_codes=["BROKER_PRODUCT_CATEGORY_SUPPORTED"], corporate_action_status="NO_EVENT")

    assert (
        _eligibility(cooldown_row, liquidity_status="NORMAL")["reentry_semantic_state"]
        == "REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION"
    )
    assert (
        _eligibility(recovery_row, liquidity_status="NORMAL")["reentry_semantic_state"]
        == "REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE"
    )
    assert (
        _eligibility(current_candidate_row, liquidity_status="NORMAL", target_membership=False, normal_target_weight=0.0)[
            "reentry_semantic_state"
        ]
        == "REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE"
    )
