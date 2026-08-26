from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework
from ai_fund_lab_v2.strategy.position_sizing import (
    PositionSizingConfig,
    PositionSizingSourceSummary,
    build_position_sizing_payload,
)


BUSINESS_DATE = "2026-08-25"
ACTUAL_RUN = "runtime-test-historical-extended-smoke-20260824T203644021876Z"
REFERENCE_RUN = "runtime-test-historical-extended-smoke-20260824T055234719725Z"


def test_phase31_g102_actual_20230322_94320_reconsideration_gets_item_scoped_pc_authority() -> None:
    multi = _producer_equivalent_multi(ACTUAL_RUN, "2023-03-22")
    row = next(
        item
        for item in multi["security_allocations"]
        if item.get("symbol") == "94320" and item.get("residual_reconsideration_authoritative_binding")
    )
    compatibility = row["lot_aware_allocation_to_sizing_compatibility"]
    lot_resolution = row["phase29_l19_lot_resolution"]
    authority = lot_resolution["pc_positive_executable_quantity_authority"]

    assert compatibility["compatibility_state"] == "LOT_EXECUTABLE_COMPATIBLE"
    assert compatibility["projected_quantity_delta_evidence_only"] == 200
    assert row["g102_item_scoped_pc_discrete_quantity_authority_propagated"] is True
    assert lot_resolution["semantic_type"] in {"BUY_NEW", "REENTRY"}
    assert lot_resolution["final_allocated_quantity"] == 200
    assert lot_resolution["executable_quantity_delta"] == 200
    assert lot_resolution["preflight_executable_quantity_delta"] == 200
    assert authority == {
        "authority_type": "PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY",
        "status": "PASS",
        "final_allocated_quantity": 200,
        "accepted_lot_increment_weight": row["authorized_allocation_weight"],
        "ps_must_consume_canonical_quantity": True,
        "future_information_used": False,
    }


def test_phase31_g102_lot_infeasible_reconsideration_does_not_false_pass() -> None:
    multi = _producer_equivalent_multi(REFERENCE_RUN, "2023-04-07")
    for symbol in {"83060", "77760", "44440"}:
        row = next(
            item
            for item in multi["security_allocations"]
            if item.get("symbol") == symbol and item.get("residual_reconsideration_authoritative_binding")
        )
        compatibility = row["lot_aware_allocation_to_sizing_compatibility"]
        authority = (row.get("phase29_l19_lot_resolution") or {}).get("pc_positive_executable_quantity_authority") or {}

        assert compatibility["compatibility_state"] == "LOT_INFEASIBLE_RESIDUAL_REQUIRED"
        assert authority.get("status") != "PASS"
        assert row.get("g102_item_scoped_pc_discrete_quantity_authority_propagated") is not True


def test_phase31_g102_ps_consumes_item_scoped_pc_authority_without_priority_redecision() -> None:
    pc_summary = _pc_summary_with_g102_selection()
    payload, _ = build_position_sizing_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_summary=_summary(rows=tuple(pc_summary["portfolio_members"]), summary=pc_summary),
        capital_deployment_summary=_summary(),
        dynamic_position_count_summary=_summary(summary={"target_position_count": 2}),
        dynamic_cash_exposure_summary=_summary(summary={"target_gross_exposure_ratio": 0.90, "market_context_risk_state": "NORMAL"}),
        position_management_summary=_summary(),
        opportunity_summary=_summary(),
        current_position_summary=_summary(summary={"portfolio_total_equity": 1_000_000.0, "portfolio_value": 1_000_000.0}),
        price_volatility_summary=_summary(rows=({"security_code": "94320", "volatility_value": 0.02},)),
        safety_limit_summary=_summary(summary={"concentration": {"maximum_position_weight": 0.25}}),
        config=_config(),
    )
    row = next(item for item in payload["positions"] if item["security_code"] == "94320")
    authority = row["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"]

    assert payload["producer_result_status"] == "PASS"
    assert row["canonical_deployment_set_sizing_eligibility"] == "SELECTED_BY_CANONICAL_MULTI_ALLOCATION"
    assert row["pc_discrete_quantity_authority_consumed"] is True
    assert row["pc_discrete_authorized_quantity"] == 200
    assert row["quantity_delta_candidate"] == 200
    assert row["canonical_sizing_evidence"]["quantity_delta"] == 200
    assert authority["status"] == "PASS"
    assert authority["final_allocated_quantity"] == 200
    assert authority["ps_must_consume_canonical_quantity"] is True
    assert row["position_sizing_recomputes_capital_priority"] is False
    assert row["lower_priority_implicit_promotion_allowed"] is False


def _producer_equivalent_multi(run_id: str, business_date: str) -> dict[str, object]:
    strategy_dir = Path("reports/runtime_tests/runs") / run_id / "daily" / business_date / "strategy"
    pc = json.loads((strategy_dir / "portfolio_construction.json").read_text())
    risk_pacing_evidence = (pc.get("portfolio_policy_allocation_authority") or {}).get("risk_pacing_evidence") or {}
    multi = pc["capital_competition"]["canonical_multi_allocation_deployment_set"]
    competition = build_capital_competition_framework(
        members=pc["portfolio_members"],
        target_gross_exposure=pc.get("target_gross_exposure"),
        total_target_weight=pc.get("total_target_weight")
        or sum(float(row.get("target_weight") or 0.0) for row in pc["portfolio_members"]),
        business_date=business_date,
        incremental_budget_evidence={"available_incremental_budget": multi.get("available_incremental_budget")},
        lot_reallocation_evidence=pc.get("lot_aware_final_reallocation") or {},
        risk_pacing_evidence=risk_pacing_evidence,
    )
    return competition["canonical_multi_allocation_deployment_set"]


def _pc_summary_with_g102_selection() -> dict[str, object]:
    lot_resolution = _g102_lot_resolution()
    compatibility = {
        "schema_version": "portfolio_construction.lot_aware_allocation_to_sizing_compatibility.v1",
        "owner": "PORTFOLIO_CONSTRUCTION",
        "authority_status": "SHADOW_NON_AUTHORITATIVE",
        "business_date": BUSINESS_DATE,
        "position_sizing_quantity_owner": "POSITION_SIZING",
        "pc_discrete_quantity_authority": False,
        "authorized_for_position_sizing": False,
        "authorized_for_runtime_order": False,
        "allocation_count": 1,
        "lot_executable_count": 1,
        "compatibility_executable_count": 1,
        "executable_multi_security": False,
        "priority_inversion_after_compatibility": False,
        "lower_priority_implicit_promotion_allowed": False,
        "residual_capital_explicit": True,
        "add_compatibility": "PASS",
        "capital_conservation": {"status": "PASS"},
        "compatibility_hash": "g102-compatibility",
        "compatibility_rows": [
            {
                "schema_version": "portfolio_construction.lot_aware_allocation_to_sizing_compatibility.v1",
                "owner": "PORTFOLIO_CONSTRUCTION",
                "authority_status": "SHADOW_NON_AUTHORITATIVE",
                "business_date": BUSINESS_DATE,
                "symbol": "94320",
                "allocation_rank": 1,
                "competitor_type": "NEW_BUY",
                "opportunity_type": "NEW_BUY",
                "authorized_allocation_weight": 0.04,
                "minimum_executable_weight": 0.02,
                "projected_quantity_delta_evidence_only": 200,
                "executable_before_residual_reallocation": True,
                "compatibility_state": "LOT_EXECUTABLE_COMPATIBLE",
                "lower_priority_execution_requires_explicit_residual_resolution": False,
                "implicit_priority_promotion_allowed": False,
                "position_sizing_quantity_authority_preserved": True,
                "pc_quantity_authority": False,
                "residual_capital_weight": 0.0,
                "reason_codes": ["LOT_EXECUTABLE_COMPATIBLE"],
            }
        ],
    }
    allocation = {
        "symbol": "94320",
        "competitor_type": "NEW_BUY",
        "opportunity_type": "NEW_BUY",
        "authorized_allocation_weight": 0.04,
        "residual_reconsideration_authoritative_binding": True,
        "phase29_l19_lot_resolution": lot_resolution,
        "lot_aware_allocation_to_sizing_compatibility": compatibility["compatibility_rows"][0],
        "multi_allocation_set_hash": "g102-multi",
    }
    multi = {
        "schema_version": "canonical_multi_allocation_deployment_set.v1",
        "owner": "PORTFOLIO_CONSTRUCTION",
        "authority_status": "SHADOW_NON_AUTHORITATIVE",
        "business_date": BUSINESS_DATE,
        "security_allocations": [allocation],
        "lot_aware_allocation_to_sizing_compatibility": compatibility,
        "multi_allocation_set_hash": "g102-multi",
    }
    return {
        "portfolio_members": [_member()],
        "canonical_multi_allocation_deployment_set": multi,
        "capital_competition": {"canonical_multi_allocation_deployment_set": multi},
    }


def _member() -> dict[str, object]:
    return {
        "security_code": "94320",
        "symbol": "94320",
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "current_position": False,
        "current_weight": 0.0,
        "current_quantity": 0,
        "target_weight": 0.0,
        "requested_buy_new_weight": 0.0,
        "accepted_buy_new_weight": 0.0,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "quality_status": "PASS",
        "quality_decision_id": "quality-94320",
        "quality_score": 0.8,
        "quality_allocation_adjustment": 1.0,
        "quality_reason_codes": ["buy_quality_full_allocation_eligible"],
        "quality_policy_version": "phase31-g102-quality",
        "component_scores": {},
        "component_statuses": {},
        "buy_quality_authority": {
            "quality_decision_id": "quality-94320",
            "quality_action": "FULL_ALLOCATION_ELIGIBLE",
            "quality_score": 0.8,
        },
        "confidence": 1.0,
        "reference_price": 100.0,
        "reference_price_authority": {
            "authority_type": "REFERENCE_PRICE_AUTHORITY",
            "PIT_status": "PASS",
            "source_field": "reference_price",
            "latest_fallback_used": False,
        },
        "target_weight_authority": {"authority_type": "TARGET_WEIGHT_AUTHORITY"},
        "target_weight_resolution": {"status": "PASS", "resolved_weight": 0.0, "reason": "test"},
    }


def _g102_lot_resolution() -> dict[str, object]:
    return {
        "authority_type": "PHASE29_L19_CAP_CONSTRAINED_LOT_RESOLUTION",
        "symbol": "94320",
        "semantic_type": "BUY_NEW",
        "requested_target_weight": 0.04,
        "requested_incremental_weight": 0.04,
        "final_target_weight": 0.02,
        "current_weight": 0.0,
        "continuous_target_weight": 0.04,
        "post_trade_weight": 0.02,
        "one_lot_quantity": 100,
        "one_lot_weight": 0.01,
        "one_lot_feasibility_status": "PASS",
        "normal_lot_quantity": 200,
        "executable_quantity_delta": 200,
        "preflight_executable_quantity_delta": 200,
        "final_allocated_quantity": 200,
        "pc_positive_executable_quantity_authority": {
            "authority_type": "PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY",
            "status": "PASS",
            "final_allocated_quantity": 200,
            "accepted_lot_increment_weight": 0.04,
            "ps_must_consume_canonical_quantity": True,
            "future_information_used": False,
        },
        "safety_hard_cap": 0.25,
        "safety_hard_cap_weight": 0.25,
        "safety_hard_cap_preserved": True,
        "strategy_cap_weight": 0.18,
        "strategy_target_cap": 0.18,
        "strategy_cap_preserved": True,
    }


def _summary(
    *,
    rows: tuple[dict[str, object], ...] = (),
    summary: dict[str, object] | None = None,
    status: str = "PASS",
) -> PositionSizingSourceSummary:
    return PositionSizingSourceSummary(
        status=status,
        business_date=BUSINESS_DATE,
        feature_date=BUSINESS_DATE,
        source_ref="test://phase31-g102",
        source_hash="phase31-g102",
        rows=rows,
        summary=summary or {},
    )


def _config() -> PositionSizingConfig:
    return PositionSizingConfig(
        config_version="phase31-g102-test",
        config_source="test://position_sizing",
        sizing_method="asset_proportional",
        opportunity_adjustment={"HIGH": 1.0, "MEDIUM": 1.0, "LOW": 1.0},
        volatility_adjustment={
            "minimum_volatility": 0.01,
            "maximum_volatility": 0.10,
            "reference_volatility": 0.02,
            "minimum_multiplier": 0.5,
            "maximum_multiplier": 1.5,
        },
        pm_intent_adjustment={"NEW": 1.0, "HOLD": 1.0, "ADD": 1.0, "REDUCE": 1.0, "EXIT": 1.0, "UNRESOLVED": 1.0},
        minimum_meaningful_notional={"base_jpy": 0, "tradable_unit": 100, "price_buffer_ratio": 0.0},
        strategy_maximum_position_weight=0.18,
        safety_concentration_reference="test://safety#concentration.maximum_position_weight",
    )
