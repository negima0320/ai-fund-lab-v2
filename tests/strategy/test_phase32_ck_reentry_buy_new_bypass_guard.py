from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy.portfolio_construction import (
    apply_lot_aware_final_reallocation,
    build_capital_competition_framework,
)


TARGET_RUN = Path("reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z")


@pytest.mark.parametrize(
    ("business_date", "symbol"),
    [
        ("2022-11-04", "76470"),
        ("2022-12-26", "94320"),
        ("2023-04-19", "94340"),
        ("2023-05-15", "76010"),
        ("2023-05-31", "21340"),
    ],
)
def test_phase32_ck_filled_bypass_cases_no_longer_publish_buy_new_competition(
    business_date: str,
    symbol: str,
) -> None:
    competition = _rebuilt_competition_from_actual_run(business_date)

    assert _symbol_allocations(competition, symbol) == []
    assert _symbol_competitors(competition, symbol) == []


@pytest.mark.parametrize(
    ("business_date", "symbol"),
    [
        ("2023-03-02", "93180"),
        ("2023-03-10", "93180"),
        ("2023-04-14", "94340"),
        ("2023-04-14", "45860"),
    ],
)
def test_phase32_ck_planned_only_bypass_cases_no_longer_publish_buy_new_competition(
    business_date: str,
    symbol: str,
) -> None:
    competition = _rebuilt_competition_from_actual_run(business_date)

    assert _symbol_allocations(competition, symbol) == []
    assert _symbol_competitors(competition, symbol) == []


def test_phase32_ck_reentry_review_cannot_rebatch_as_buy_new() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            _new_member(
                "21340",
                semantic="REENTRY",
                reentry_status="REVIEW_REQUIRED",
                reentry_state="REENTRY_INSUFFICIENT_EVIDENCE",
                target_weight=0.05,
            )
        ],
        lot_feasibility_rows=[_lot_row("21340", semantic="BUY_NEW")],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
        business_date="2023-05-31",
    )
    member = result["members"][0]

    assert member["semantic_buy_type"] == "REENTRY"
    assert member["target_membership"] is False
    assert member["target_weight"] == 0.0
    assert member["lot_aware_accepted_buy_new_weight"] == 0.0
    assert member["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"]["status"] == "NOT_APPLICABLE"
    assert "reentry_fail_closed_buy_new_bypass_blocked" in result["reason_codes"]


def test_phase32_ck_active_churn_reentry_remains_blocked() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            _new_member(
                "83060",
                semantic="REENTRY",
                reentry_status="FAIL_CLOSED",
                reentry_state="REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION",
                target_weight=0.05,
            )
        ],
        lot_feasibility_rows=[_lot_row("83060", semantic="BUY_NEW")],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
        business_date="2023-03-01",
    )
    member = result["members"][0]

    assert member["semantic_buy_type"] == "REENTRY"
    assert member["target_membership"] is False
    assert member["target_weight"] == 0.0
    assert member["lot_aware_accepted_buy_new_weight"] == 0.0


def test_phase32_ck_genuine_never_owned_new_remains_executable() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[_new_member("11110", semantic="BUY_NEW", target_weight=0.05)],
        lot_feasibility_rows=[_lot_row("11110", semantic="BUY_NEW")],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
        business_date="2023-05-31",
    )
    member = result["members"][0]

    assert member["semantic_buy_type"] == "BUY_NEW"
    assert member["target_membership"] is True
    assert member["lot_aware_accepted_buy_new_weight"] > 0.0
    assert member["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"]["status"] == "PASS"


def test_phase32_ck_valid_reentry_remains_possible_and_not_relabelled_buy_new() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            _new_member(
                "22220",
                semantic="REENTRY",
                reentry_status="PASS",
                reentry_state="REENTRY_ELIGIBLE",
                target_weight=0.05,
            )
        ],
        lot_feasibility_rows=[_lot_row("22220", semantic="REENTRY")],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
        business_date="2023-05-31",
    )
    member = result["members"][0]

    assert member["semantic_buy_type"] == "REENTRY"
    assert member["target_membership"] is True
    assert member["lot_aware_accepted_buy_new_weight"] > 0.0
    assert member["phase29_l19_lot_resolution"]["semantic_type"] == "REENTRY"
    assert member["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"]["status"] == "PASS"
    assert member["prior_campaign_id"] == "pc-prior-22220-0001"


def test_phase32_ck_buy_add_remains_unchanged() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[_add_member("33330")],
        lot_feasibility_rows=[_lot_row("33330", semantic="BUY_ADD")],
        target_gross_exposure=0.30,
        single_name_cap=0.30,
        business_date="2023-05-31",
    )
    member = result["members"][0]

    assert member["semantic_buy_type"] == "BUY_ADD"
    assert member["target_membership"] is True
    assert member["lot_aware_accepted_incremental_weight"] > 0.0
    assert member["phase29_l19_lot_resolution"]["semantic_type"] == "BUY_ADD"


def _rebuilt_competition_from_actual_run(business_date: str) -> dict[str, object]:
    pc_path = TARGET_RUN / "daily" / business_date / "strategy" / "portfolio_construction.json"
    pc = json.loads(pc_path.read_text())
    risk = (pc.get("portfolio_policy_allocation_authority") or {}).get("risk_pacing_evidence") or {}
    return build_capital_competition_framework(
        members=pc["portfolio_members"],
        target_gross_exposure=pc.get("target_gross_exposure"),
        total_target_weight=pc.get("total_target_weight")
        or sum(float(row.get("target_weight") or 0.0) for row in pc["portfolio_members"]),
        business_date=business_date,
        incremental_budget_evidence=pc.get("incremental_budget_reconciliation") or {},
        lot_reallocation_evidence=pc.get("lot_aware_final_reallocation") or {},
        risk_pacing_evidence=risk,
    )


def _symbol_allocations(competition: dict[str, object], symbol: str) -> list[dict[str, object]]:
    multi = competition["canonical_multi_allocation_deployment_set"]  # type: ignore[index]
    return [
        row
        for row in multi.get("security_allocations", [])  # type: ignore[union-attr]
        if row.get("symbol") == symbol
    ]


def _symbol_competitors(competition: dict[str, object], symbol: str) -> list[dict[str, object]]:
    return [
        row
        for row in competition.get("competitors", [])  # type: ignore[union-attr]
        if row.get("symbol") == symbol
    ]


def _new_member(
    symbol: str,
    *,
    semantic: str,
    target_weight: float,
    reentry_status: str = "PASS",
    reentry_state: str = "REENTRY_ELIGIBLE",
) -> dict[str, object]:
    member: dict[str, object] = {
        "security_code": symbol,
        "symbol": symbol,
        "current_position": False,
        "current_quantity": 0,
        "current_weight": 0.0,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "semantic_buy_type": semantic,
        "construction_priority": 1,
        "requested_buy_new_weight": target_weight,
        "accepted_buy_new_weight": target_weight,
        "target_weight": target_weight,
        "target_membership": target_weight > 0,
        "target_weight_authority": {},
        "target_weight_resolution": {"status": "PASS", "resolved_weight": target_weight, "adjustments": []},
        "entry_admission_action": "BUY_NEW_ALLOWED",
        "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "quality_status": "PASS",
        "runtime_opportunity_score": 0.5,
        "reference_price": 100.0,
    }
    if semantic == "REENTRY":
        member.update(
            {
                "prior_campaign_id": f"pc-prior-{symbol}-0001",
                "prior_exit_business_date": "2023-05-17",
                "prior_exit_reason": "EXIT_BY_TREND_AND_EDGE_BREAK",
                "reentry_semantic_status": reentry_status,
                "reentry_semantic_state": reentry_state,
                "reentry_semantic_eligibility": {
                    "eligibility_status": reentry_status,
                    "reentry_semantic_state": reentry_state,
                    "semantic_buy_type": "REENTRY",
                    "prior_campaign_id": f"pc-prior-{symbol}-0001",
                    "prior_exit_business_date": "2023-05-17",
                },
            }
        )
    return member


def _add_member(symbol: str) -> dict[str, object]:
    return {
        "security_code": symbol,
        "symbol": symbol,
        "current_position": True,
        "current_quantity": 100,
        "current_weight": 0.10,
        "membership_intent": "RETAIN",
        "pm_action": "ADD",
        "semantic_buy_type": "BUY_ADD",
        "construction_priority": 1,
        "requested_incremental_weight": 0.05,
        "accepted_incremental_weight": 0.05,
        "target_weight": 0.15,
        "target_membership": True,
        "target_weight_authority": {},
        "target_weight_resolution": {"status": "PASS", "resolved_weight": 0.15, "adjustments": []},
        "add_allocation_eligibility_status": "PASS",
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "strategy_intelligence_add_worthiness_state": "ADD_ALLOWED",
        "runtime_opportunity_score": 0.5,
        "reference_price": 100.0,
    }


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
            "current_weight": 0.0 if semantic != "BUY_ADD" else 0.10,
            "one_lot_quantity": 100,
            "one_lot_weight": 0.02,
            "one_lot_notional": 20_000.0,
            "one_lot_feasibility_status": "PASS",
            "one_lot_fallback_applied": False,
            "normal_lot_quantity": 200,
            "executable_quantity_delta": 200,
            "final_allocated_quantity": 200,
            "post_trade_weight": 0.04 if semantic != "BUY_ADD" else 0.14,
            "safety_hard_cap": 0.30,
            "safety_hard_cap_weight": 0.30,
            "safety_hard_cap_preserved": True,
            "strategy_target_cap": 0.30,
            "strategy_cap_weight": 0.30,
        },
    }
