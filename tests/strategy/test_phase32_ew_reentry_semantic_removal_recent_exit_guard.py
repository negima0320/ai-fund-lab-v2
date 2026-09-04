from __future__ import annotations

from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy import portfolio_construction, shadow_runtime
from ai_fund_lab_v2.strategy.portfolio_construction import apply_lot_aware_final_reallocation


def test_old_prior_exit_is_ordinary_buy_new_audit_lineage_only() -> None:
    row = _buy_row(
        prior_exit_business_date="2026-07-09",
        prior_campaign_id="pc-old-11110",
        prior_exit_reason="hard_stop_current_return",
        source_pm_decision_id="pm-old-exit",
    )

    semantic, recovery, eligibility = _resolve(row, business_date="2026-07-15")

    assert semantic["semantic_buy_type"] == "BUY_NEW"
    assert semantic["ownership_lineage"] == "PRIOR_EXIT_LINEAGE_PRESENT"
    assert semantic["recent_exit_guard_state"] == "EXPIRED_NOT_CURRENT_DECISION_AUTHORITY"
    assert "prior_exit_context" not in semantic
    assert recovery["reentry_recovery_status"] == "NOT_APPLICABLE"
    assert eligibility["eligibility_status"] == "NOT_APPLICABLE"
    assert eligibility["reentry_identity"] == "AUDIT_LINEAGE_ONLY"
    assert "REENTRY_CURRENT_DECISION_SEMANTIC_REMOVED" in eligibility["reason_codes"]


def test_old_unknown_prior_exit_context_does_not_create_long_lived_review() -> None:
    row = _buy_row(
        prior_exit_business_date="2026-07-09",
        prior_campaign_id="pc-old-22220",
        prior_exit_reason="EXIT",
        source_pm_decision_id="",
        prior_exit_provenance_status="REVIEW_REQUIRED",
    )

    semantic, recovery, eligibility = _resolve(row, business_date="2026-07-15")

    assert semantic["semantic_buy_type"] == "BUY_NEW"
    assert semantic["recent_exit_guard_state"] == "EXPIRED_NOT_CURRENT_DECISION_AUTHORITY"
    assert recovery["reentry_recovery_status"] == "NOT_APPLICABLE"
    assert eligibility["eligibility_status"] == "NOT_APPLICABLE"
    assert eligibility["prior_exit_context_status"] == "NOT_APPLICABLE"


def test_recent_exit_unresolved_weakness_remains_guard_blocked() -> None:
    row = _buy_row(
        prior_exit_business_date="2026-07-14",
        prior_campaign_id="pc-recent-33330",
        prior_exit_reason="EXIT_BY_TREND_AND_EDGE_BREAK",
        source_pm_decision_id="pm-recent-exit",
        trend_close_over_ma_20d=0.98,
    )

    semantic, recovery, eligibility = _resolve(row, business_date="2026-07-15")

    assert semantic["semantic_buy_type"] == "BUY_NEW"
    assert semantic["recent_exit_guard_state"] == "ACTIVE_RECENT_EXIT_GUARD"
    assert recovery["reentry_recovery_status"] == "FAIL_CLOSED"
    assert eligibility["eligibility_status"] == "FAIL_CLOSED"
    assert eligibility["reentry_semantic_state"] != "REENTRY_ELIGIBLE"


def test_recent_exit_current_pit_requalification_releases_guard() -> None:
    row = _buy_row(
        prior_exit_business_date="2026-07-14",
        prior_campaign_id="pc-recent-44440",
        prior_exit_reason="EXIT_BY_TREND_AND_EDGE_BREAK",
        source_pm_decision_id="pm-recent-exit",
    )

    semantic, recovery, eligibility = _resolve(row, business_date="2026-07-15")

    assert semantic["recent_exit_guard_state"] == "ACTIVE_RECENT_EXIT_GUARD"
    assert recovery["reentry_recovery_status"] == "PASS"
    assert eligibility["eligibility_status"] == "PASS"
    assert eligibility["reentry_semantic_state"] == "RECENT_EXIT_GUARD_CURRENT_PIT_REQUALIFIED"


def test_matched_never_held_and_old_exit_use_equivalent_current_buy_semantics() -> None:
    never = _buy_row()
    old = _buy_row(
        prior_exit_business_date="2026-07-09",
        prior_campaign_id="pc-old-55550",
        prior_exit_reason="hard_stop_current_return",
        source_pm_decision_id="pm-old-exit",
    )

    never_semantic, _, never_eligibility = _resolve(never, business_date="2026-07-15")
    old_semantic, _, old_eligibility = _resolve(old, business_date="2026-07-15")

    assert never_semantic["semantic_buy_type"] == old_semantic["semantic_buy_type"] == "BUY_NEW"
    assert never_eligibility["eligibility_status"] == old_eligibility["eligibility_status"] == "NOT_APPLICABLE"
    assert old_semantic["recent_exit_guard_state"] == "EXPIRED_NOT_CURRENT_DECISION_AUTHORITY"


def test_active_recent_exit_guard_cannot_rebatch_as_executable_buy_new() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            {
                "security_code": "66660",
                "symbol": "66660",
                "current_position": False,
                "current_quantity": 0,
                "current_weight": 0.0,
                "membership_intent": "ADD_CANDIDATE",
                "pm_action": "NEW",
                "semantic_buy_type": "BUY_NEW",
                "recent_exit_guard_state": "ACTIVE_RECENT_EXIT_GUARD",
                "recent_exit_guard_status": "FAIL_CLOSED",
                "construction_priority": 1,
                "requested_buy_new_weight": 0.05,
                "accepted_buy_new_weight": 0.05,
                "target_weight": 0.05,
                "target_membership": True,
                "target_weight_authority": {},
                "target_weight_resolution": {"status": "PASS", "resolved_weight": 0.05, "adjustments": []},
                "entry_admission_action": "BUY_NEW_ALLOWED",
                "quality_action": "FULL_ALLOCATION_ELIGIBLE",
                "quality_status": "PASS",
                "runtime_opportunity_score": 0.5,
                "reference_price": 100.0,
            }
        ],
        lot_feasibility_rows=[_lot_row("66660", semantic="BUY_NEW")],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
        business_date="2026-07-15",
    )

    member = result["members"][0]
    assert member["target_membership"] is False
    assert member["target_weight"] == 0.0
    assert member["lot_aware_accepted_buy_new_weight"] == 0.0
    assert "recent_exit_guard_buy_new_bypass_blocked" in result["reason_codes"]


def test_buy_add_semantics_remain_campaign_local() -> None:
    semantic = portfolio_construction._semantic_reentry_evidence(
        row={"current_position": True, "pm_action": "ADD", "prior_exit_business_date": "2026-07-14"},
        business_date="2026-07-15",
        is_buy_new=False,
    )

    assert semantic["semantic_buy_type"] == "BUY_ADD"
    assert semantic["recent_exit_guard_state"] == "NOT_APPLICABLE"


def test_current_buy_prior_exit_supply_does_not_scan_whole_run_history(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fail_jsonl(*_args: object, **_kwargs: object) -> list[object]:
        raise AssertionError("executions.jsonl scan must not be in current BUY prior-exit hot path")

    def fail_pm_scan(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("strict-prior PM EXIT scan must not be in current BUY prior-exit hot path")

    monkeypatch.setattr(shadow_runtime, "_read_jsonl", fail_jsonl)
    monkeypatch.setattr(shadow_runtime, "_strict_prior_pm_exit_decision_evidence_by_campaign", fail_pm_scan)

    result = shadow_runtime._supply_prior_exit_state(
        run_dir=tmp_path / "run",
        runtime_root=tmp_path / "runtime",
        business_date="2026-07-15",
        candidate={"rows": ({"code": "77770"},), "payload": {"decisions": [{"code": "77770"}]}},
        opportunity={"rows": ({"code": "77770"},), "payload": {"rankings": [{"code": "77770"}]}},
        current={"rows": ()},
    )

    assert result["evidence"]["full_executions_jsonl_scanned_for_reentry"] is False
    assert result["evidence"]["strict_prior_pm_exit_artifacts_scanned_for_reentry"] is False
    assert result["candidate"]["rows"][0].get("prior_exit_business_date") is None


def _resolve(row: dict[str, object], *, business_date: str) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date=business_date, is_buy_new=True)
    recovery = portfolio_construction._reentry_recovery_evidence(
        row=row,
        semantic=semantic,
        capacity_ratio=0.0001,
        liquidity_status="NORMAL",
    )
    eligibility = portfolio_construction._canonical_reentry_semantic_eligibility(
        row=row,
        business_date=business_date,
        is_buy_new=True,
        semantic=semantic,
        recovery=recovery,
        liquidity_status="NORMAL",
        target_membership=True,
        normal_target_weight=0.05,
        target_weight_reason="ranked_candidate",
        zero_weight_reason="",
        review_reason="",
    )
    return semantic, recovery, eligibility


def _buy_row(**extra: object) -> dict[str, object]:
    row: dict[str, object] = {
        "symbol": "11110",
        "security_code": "11110",
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "opportunity_rank": 1,
        "runtime_opportunity_score": 0.8,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "trend_close_over_ma_20d": 1.02,
        "price_momentum_return_20d": 0.02,
        "entry_admission_action": "BUY_NEW_ALLOWED",
        "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "strategy_intelligence_continuation_quality_status": "PASS",
        "strategy_intelligence_downside_risk_status": "PASS",
        "corporate_action_status": "PASS",
        "prior_exit_provenance_status": "PASS",
        "source_decision_id": "runtime-source-decision",
    }
    row.update(extra)
    return row


def _lot_row(symbol: str, *, semantic: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "intent_type": semantic,
        "lot_feasible": True,
        "broker_eligible": True,
        "minimum_executable_weight": 0.02,
        "phase29_l19_lot_resolution": {
            "authority_type": "PHASE29_L19_CAP_CONSTRAINED_LOT_RESOLUTION",
            "semantic_type": semantic,
            "boundary_classification": "CAP_CONSTRAINED_LOT_EXECUTABLE",
            "continuous_target_weight": 0.05,
            "current_weight": 0.0,
            "one_lot_quantity": 100,
            "one_lot_weight": 0.02,
            "one_lot_notional": 20_000.0,
            "one_lot_feasibility_status": "PASS",
            "normal_lot_quantity": 200,
            "executable_quantity_delta": 200,
            "final_allocated_quantity": 200,
            "post_trade_weight": 0.04,
            "safety_hard_cap": 0.30,
            "safety_hard_cap_weight": 0.30,
            "safety_hard_cap_preserved": True,
            "strategy_target_cap": 0.30,
            "strategy_cap_weight": 0.30,
        },
    }
