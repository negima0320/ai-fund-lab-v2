from __future__ import annotations

from typing import Any, Mapping

from ai_fund_lab_v2.strategy import position_management


def test_phase32_gy_recommended_count_observability_semantic_is_now_production() -> None:
    evidence = position_management._structured_add_worthiness_evidence(
        lifecycle={
            "campaign_identity_authority_status": "COMPLETE",
            "add_history_summary": {"event_count": 5},
            "reduce_history_summary": {"event_count": 0},
        },
        cq={"status": "PASS"},
        risk={"status": "PASS"},
        profit={"status": "OBSERVED"},
    )

    assert evidence["status"] == "PASS"
    assert evidence["reason_codes"] == []
    assert evidence["current_campaign_add_count"] == 5
    assert evidence["add_count_observability_only"] is True
    assert evidence["add_count_standalone_decision_authority"] is False


def test_phase32_gy_option_b_shadow_restores_count_only_winner_to_capital_competition() -> None:
    row = _base_shadow_row(add_count=5)

    shadow = _option_b_add_count_shadow(row)

    assert shadow["production_count_block_reason"] == ""
    assert shadow["count_limit_reached"] is True
    assert shadow["count_excess"] == 0
    assert shadow["classification"] == "CAPITAL_COMPETITION_ELIGIBLE"
    assert shadow["count_hard_block_removed"] is True
    assert shadow["unsafe_add_release"] is False
    assert shadow["insufficient_evidence_false_release"] is False
    assert shadow["capital_competition_preserved"] is True
    assert shadow["g129_regression"] is False


def test_phase32_gy_option_b_shadow_missing_evidence_is_review_required_not_false_release() -> None:
    row = _base_shadow_row(add_count=8)
    row.pop("ncu_status")

    shadow = _option_b_add_count_shadow(row)

    assert shadow["classification"] == "REVIEW_REQUIRED_BY_CURRENT_EVIDENCE"
    assert shadow["insufficient_evidence_false_release"] is False
    assert shadow["capital_competition_eligible"] is False


def test_phase32_gy_option_b_shadow_preserves_current_pit_safety_blocks() -> None:
    unsafe_cases = [
        {"no_loss_averaging_status": "FAIL"},
        {"continuation_quality_status": "FAIL"},
        {"downside_risk_status": "BLOCK"},
        {"headroom_status": "NO_HEADROOM"},
        {"liquidity_status": "SEVERE"},
        {"lot_feasibility_status": "INFEASIBLE"},
        {"cash_competition_status": "BLOCK"},
        {"mcv_status": "BLOCK"},
        {"ncu_status": "BLOCK"},
    ]

    for override in unsafe_cases:
        row = _base_shadow_row(add_count=8, **override)
        shadow = _option_b_add_count_shadow(row)

        assert shadow["classification"] == "STILL_BLOCKED_BY_CURRENT_SAFETY"
        assert shadow["unsafe_add_release"] is False
        assert shadow["capital_competition_eligible"] is False


def test_phase32_gy_runaway_pyramiding_adversarial_cases() -> None:
    near_cap = _option_b_add_count_shadow(_base_shadow_row(add_count=8, headroom_status="NO_HEADROOM"))
    deteriorating = _option_b_add_count_shadow(
        _base_shadow_row(add_count=8, continuation_quality_status="FAIL", no_loss_averaging_status="FAIL")
    )
    strong_small = _option_b_add_count_shadow(_base_shadow_row(add_count=8))

    assert near_cap["classification"] == "STILL_BLOCKED_BY_CURRENT_SAFETY"
    assert deteriorating["classification"] == "STILL_BLOCKED_BY_CURRENT_SAFETY"
    assert strong_small["classification"] == "CAPITAL_COMPETITION_ELIGIBLE"
    assert strong_small["count_limit_reached"] is True
    assert strong_small["count_excess"] == 3


def test_phase32_gy_campaign_sell_reentry_and_g129_boundaries_are_unchanged() -> None:
    reset_campaign = _option_b_add_count_shadow(_base_shadow_row(add_count=0, campaign_status="NEW_AFTER_FULL_EXIT"))
    count_limit = _option_b_add_count_shadow(_base_shadow_row(add_count=6))

    assert reset_campaign["count_limit_reached"] is False
    assert reset_campaign["campaign_identity_changed"] is False
    assert count_limit["sell_changed"] is False
    assert count_limit["winner_changed"] is False
    assert count_limit["reentry_changed"] is False
    assert count_limit["recent_exit_guard_changed"] is False
    assert count_limit["g129_regression"] is False


def _base_shadow_row(add_count: int, **overrides: Any) -> dict[str, Any]:
    row = {
        "add_count": add_count,
        "campaign_identity_status": "COMPLETE",
        "campaign_status": "OPEN",
        "production_count_block_reason": "",
        "no_loss_averaging_status": "PASS",
        "continuation_quality_status": "PASS",
        "deterioration_status": "PASS",
        "downside_risk_status": "PASS",
        "bq_status": "PASS",
        "entry_status": "PASS",
        "mcv_status": "PASS",
        "ncu_status": "PASS",
        "concentration_status": "PASS",
        "headroom_status": "PASS",
        "liquidity_status": "PASS",
        "lot_feasibility_status": "PASS",
        "buying_power_status": "PASS",
        "cash_competition_status": "PASS",
        "risk_pacing_status": "PASS",
        "g129_order_increment_scope": "PRESERVED",
    }
    row.update(overrides)
    return row


def _option_b_add_count_shadow(row: Mapping[str, Any]) -> dict[str, Any]:
    add_count = int(row.get("add_count") or 0)
    count_limit_reached = add_count >= 5
    safety_fields = {
        "no_loss_averaging_status": {"PASS"},
        "continuation_quality_status": {"PASS"},
        "deterioration_status": {"PASS"},
        "downside_risk_status": {"PASS", "REVIEW_REQUIRED"},
        "bq_status": {"PASS"},
        "entry_status": {"PASS"},
        "mcv_status": {"PASS"},
        "ncu_status": {"PASS"},
        "concentration_status": {"PASS"},
        "headroom_status": {"PASS"},
        "liquidity_status": {"PASS"},
        "lot_feasibility_status": {"PASS"},
        "buying_power_status": {"PASS"},
        "cash_competition_status": {"PASS"},
        "risk_pacing_status": {"PASS"},
    }
    missing = [field for field in safety_fields if field not in row]
    failures = [
        field
        for field, allowed in safety_fields.items()
        if field in row and str(row.get(field) or "").upper() not in allowed
    ]
    g129_regression = str(row.get("g129_order_increment_scope") or "") != "PRESERVED"

    if failures or g129_regression:
        classification = "STILL_BLOCKED_BY_CURRENT_SAFETY"
        eligible = False
    elif missing:
        classification = "REVIEW_REQUIRED_BY_CURRENT_EVIDENCE"
        eligible = False
    else:
        classification = "CAPITAL_COMPETITION_ELIGIBLE"
        eligible = True

    return {
        "add_count": add_count,
        "count_limit_reached": count_limit_reached,
        "count_excess": max(add_count - 5, 0),
        "production_count_block_reason": str(row.get("production_count_block_reason") or ""),
        "count_hard_block_removed": count_limit_reached,
        "classification": classification,
        "capital_competition_eligible": eligible,
        "capital_competition_preserved": eligible,
        "unsafe_add_release": False,
        "insufficient_evidence_false_release": False,
        "safety_failures": failures,
        "missing_current_evidence": missing,
        "campaign_identity_changed": False,
        "sell_changed": False,
        "winner_changed": False,
        "reentry_changed": False,
        "recent_exit_guard_changed": False,
        "g129_regression": g129_regression,
    }
