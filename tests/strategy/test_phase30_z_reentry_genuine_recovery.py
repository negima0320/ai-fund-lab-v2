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
    assert recovery["reentry_recovery_reason"] == "recoverable_prior_exit_context_defect"
    assert recovery["reentry_prior_exit_context_classification"] == "RECOVERABLE_PROVENANCE_DEFECT"


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
