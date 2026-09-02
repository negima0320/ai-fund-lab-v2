from __future__ import annotations

from ai_fund_lab_v2.strategy import portfolio_construction


def _base(**overrides: object) -> dict[str, object]:
    return {
        "code": "83060",
        "prior_campaign_id": "pc-prior-83060-0001",
        "prior_exit_business_date": "2022-10-04",
        "prior_exit_reason": "trend_and_opportunity_broken",
        "prior_exit_reason_codes": ["trend_and_opportunity_broken"],
        "source_pm_decision_id": "pm-2022-10-04-83060-exit",
        "source_decision_id": "decision-2022-10-04-83060-exit",
        "prior_exit_provenance_status": "PASS",
        "runtime_opportunity_score": 0.42,
        "opportunity_buy_rank": 10,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "trend_close_over_ma_20d": 1.05,
        "price_momentum_return_20d": 0.03,
        "corporate_action_status": "NO_EVENT",
        "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
        "entry_admission_action": "BUY_NEW_ALLOWED",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "strategy_intelligence_continuation_quality_status": "PASS",
        "strategy_intelligence_downside_risk_status": "PASS",
        **overrides,
    }


def _semantic(row: dict[str, object], *, business_date: str = "2022-10-25") -> dict[str, object]:
    return portfolio_construction._semantic_reentry_evidence(row=row, business_date=business_date, is_buy_new=True)


def _recovery(row: dict[str, object], *, business_date: str = "2022-10-25") -> dict[str, object]:
    return portfolio_construction._reentry_recovery_evidence(
        row=row,
        semantic=_semantic(row, business_date=business_date),
        capacity_ratio=0.01,
        liquidity_status="WATCH",
    )


def _eligibility(
    row: dict[str, object],
    *,
    business_date: str = "2022-10-25",
    target_membership: bool = True,
    normal_target_weight: float = 0.05,
    target_weight_reason: str = "selected",
    zero_weight_reason: str = "",
    review_reason: str = "",
) -> dict[str, object]:
    semantic = _semantic(row, business_date=business_date)
    recovery = portfolio_construction._reentry_recovery_evidence(
        row=row,
        semantic=semantic,
        capacity_ratio=0.01,
        liquidity_status="WATCH",
    )
    return portfolio_construction._canonical_reentry_semantic_eligibility(
        row=row,
        business_date=business_date,
        is_buy_new=True,
        semantic=semantic,
        recovery=recovery,
        liquidity_status="WATCH",
        target_membership=target_membership,
        normal_target_weight=normal_target_weight,
        target_weight_reason=target_weight_reason,
        zero_weight_reason=zero_weight_reason,
        review_reason=review_reason,
    )


def test_phase32_cw_83060_trend_momentum_reentry_passes_without_legacy_rank_penalty() -> None:
    row = _base(opportunity_buy_rank=19)
    recovery = _recovery(row)
    eligibility = _eligibility(row)

    assert recovery["previous_exit_reason_class"] == "TREND_MOMENTUM"
    assert recovery["reentry_recovery_status"] == "PASS"
    assert recovery["reentry_opportunity_qualification_status"] == "CURRENT_BUY_AUTHORITY"
    assert eligibility["eligibility_status"] == "PASS"
    assert eligibility["reentry_semantic_state"] == "REENTRY_ELIGIBLE"
    assert eligibility["prior_exit_context_classification"] == "COMPLETE_AUTHORITATIVE_CONTEXT"


def test_phase32_cw_broad_bq_penalty_removed_for_complete_context_but_ordinary_buy_can_block() -> None:
    row = _base(quality_action="REJECT")
    recovery = _recovery(row)
    eligibility = _eligibility(
        row,
        target_membership=False,
        normal_target_weight=0.0,
        target_weight_reason="quality_rejected",
        zero_weight_reason="quality_rejected",
    )

    assert recovery["reentry_recovery_status"] == "PASS"
    assert recovery["reentry_buy_quality_action"] == "REJECT"
    assert eligibility["eligibility_status"] == "FAIL_CLOSED"
    assert eligibility["reentry_semantic_state"] == "REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE"


def test_phase32_cw_portfolio_competition_rank5_special_penalty_removed() -> None:
    row = _base(
        prior_exit_reason="portfolio_competition_rebalance",
        prior_exit_reason_codes=["portfolio_competition_rebalance"],
        opportunity_buy_rank=8,
    )
    recovery = _recovery(row)

    assert recovery["previous_exit_reason_class"] == "PORTFOLIO_COMPETITION"
    assert recovery["reentry_recovery_status"] == "PASS"
    assert recovery["reentry_recovery_reason"] == "reentry_recovery_qualified"


def test_phase32_cw_hard_stop_enhanced_recovery_preserved() -> None:
    reduced = _base(
        prior_exit_reason="hard_stop_current_return",
        prior_exit_reason_codes=["hard_stop_current_return"],
        quality_action="REDUCED_ALLOCATION_ONLY",
    )
    full = {**reduced, "quality_action": "FULL_ALLOCATION_ELIGIBLE"}

    assert _recovery(reduced)["reentry_recovery_reason"] == "reentry_hard_stop_new_thesis_not_sufficient"
    assert _recovery(full)["reentry_recovery_status"] == "PASS"


def test_phase32_cw_genuine_unknown_strong_current_evidence_can_pass_without_buy_new_fallback() -> None:
    row = _base(
        prior_exit_reason="profit_retention_break",
        prior_exit_reason_codes=["profit_retention_break"],
        reentry_prior_exit_context_classification="REENTRY_UNKNOWN_PRIOR_CONTEXT",
    )
    recovery = _recovery(row)
    eligibility = _eligibility(row)

    assert recovery["previous_exit_reason_class"] == "GENERIC"
    assert recovery["reentry_prior_exit_context_classification"] == "REENTRY_UNKNOWN_PRIOR_CONTEXT"
    assert recovery["reentry_unknown_prior_context_status"] == "PASS"
    assert eligibility["eligibility_status"] == "PASS"
    assert eligibility["semantic_buy_type"] == "REENTRY"
    assert eligibility["prior_exit_context_classification"] == "REENTRY_UNKNOWN_PRIOR_CONTEXT"


def test_phase32_cw_genuine_unknown_weak_current_evidence_reviews() -> None:
    row = _base(
        prior_exit_reason="profit_retention_break",
        prior_exit_reason_codes=["profit_retention_break"],
        reentry_prior_exit_context_classification="REENTRY_UNKNOWN_PRIOR_CONTEXT",
        trend_close_over_ma_20d=0.97,
    )
    recovery = _recovery(row)
    eligibility = _eligibility(row)

    assert recovery["reentry_recovery_status"] == "REVIEW_REQUIRED"
    assert recovery["reentry_recovery_reason"] == "reentry_unknown_prior_context_independence_not_established"
    assert eligibility["eligibility_status"] == "REVIEW_REQUIRED"
    assert eligibility["reentry_semantic_state"] == "REENTRY_INSUFFICIENT_EVIDENCE"


def test_phase32_cw_recoverable_provenance_defect_does_not_become_unknown_release() -> None:
    row = _base(
        prior_exit_reason="EXIT",
        prior_exit_reason_codes=[],
        recoverable_prior_exit_context_defect=True,
    )
    recovery = _recovery(row)
    eligibility = _eligibility(row)

    assert recovery["reentry_prior_exit_context_classification"] == "RECOVERABLE_PROVENANCE_DEFECT"
    assert recovery["reentry_unknown_prior_context_status"] == "NOT_APPLICABLE"
    assert recovery["reentry_recovery_status"] == "REVIEW_REQUIRED"
    assert eligibility["eligibility_status"] == "REVIEW_REQUIRED"
    assert eligibility["semantic_buy_type"] == "REENTRY"


def test_phase32_cw_existing_three_bd_cooldown_preserved() -> None:
    row = _base(prior_exit_business_date="2022-10-24")
    semantic = _semantic(row, business_date="2022-10-25")
    eligibility = _eligibility(row, business_date="2022-10-25")

    assert semantic["reentry_cooldown_threshold_bd"] == 3
    assert semantic["reentry_cooldown_status"] == "FAIL_CLOSED"
    assert eligibility["reentry_semantic_state"] == "REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION"


def test_phase32_cw_repeated_unresolved_churn_preserved() -> None:
    row = _base(prior_same_symbol_exit_count=2, price_momentum_return_20d=-0.01)
    recovery = _recovery(row)

    assert recovery["reentry_recovery_status"] == "FAIL_CLOSED"
    assert recovery["reentry_recovery_reason"] == "reentry_repeated_unresolved_churn"
