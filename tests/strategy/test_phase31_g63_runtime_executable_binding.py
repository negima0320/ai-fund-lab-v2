from __future__ import annotations

from ai_fund_lab_v2.strategy.runtime_planning import (
    _build_plans,
    _g63_runtime_binding_precheck,
    _g63_runtime_executable_binding_summary,
)


BUSINESS_DATE = "2026-08-23"


def test_phase31_g63_ps_quantity_binds_runtime_and_blocks_implicit_promotion() -> None:
    ps_payload = _ps_payload(
        [
            _ps_position("90010", 100, lower_requires=False),
            _ps_position("90020", 100, lower_requires=True),
            _ps_position("90030", 200, lower_requires=False),
            _ps_position("91010", 100, lower_requires=False, current=True),
            _ps_position("92010", -100, lower_requires=False, current=True, reduce=True),
        ]
    )
    plans, reasons = _build_plans(
        business_date=BUSINESS_DATE,
        pc_payload=_pc_payload(),
        cd_payload={},
        pm_payload=_pm_payload(),
        ps_payload=ps_payload,
        quantity_source_mode="LEGACY_POSITION_SIZING",
        opportunity_payload={},
        opportunity_artifact_path=None,
        current_position_rows=(
            _current_position("91010", 100),
            _current_position("92010", 300),
        ),
        pending_rows=(),
        source_hash_seed="phase31-g63",
    )
    precheck = _g63_runtime_binding_precheck(ps_payload, business_date=BUSINESS_DATE)
    summary = _g63_runtime_executable_binding_summary(
        business_date=BUSINESS_DATE,
        ps_payload=ps_payload,
        plans=plans,
        precheck=precheck,
    )

    by_symbol = {plan["security_code"]: plan for plan in plans}
    assert not [reason for reason in reasons if reason.startswith(("planning_conflict", "unresolved_mapping", "review_required"))]
    assert by_symbol["90010"]["planning_intent"] == "BUY_NEW"
    assert by_symbol["90010"]["planned_quantity"] == 100
    assert by_symbol["90020"]["planning_intent"] == "NO_ORDER"
    assert by_symbol["90020"]["planned_quantity"] == 0
    assert by_symbol["90020"]["no_order_reason"] == "G61_EXPLICIT_RESIDUAL_RESOLUTION_REQUIRED"
    assert by_symbol["90030"]["planning_intent"] == "BUY_NEW"
    assert by_symbol["91010"]["planning_intent"] == "BUY_ADD"
    assert by_symbol["91010"]["planned_quantity"] == 100
    assert by_symbol["92010"]["planning_intent"] == "SELL_REDUCE"
    assert by_symbol["92010"]["order_side_intent"] == "SELL"
    assert summary["pc_ps_runtime_executable_binding"] == "PASS"
    assert summary["ps_quantity_binds_runtime"] is True
    assert summary["runtime_capital_priority_redecision"] is False
    assert summary["lower_priority_implicit_promotion_runtime"] is False
    assert summary["cash_winner_redecision_runtime"] is False
    assert summary["multi_security_runtime_planning"] is True
    assert summary["add_runtime_binding"] == "PASS"
    assert summary["implicit_promotion_blocked_plan_count"] == 1
    assert summary["future_input_count"] == 0
    assert summary["historical_outcome_strategy_input_count"] == 0


def test_phase31_g63_malformed_ps_g61_consumption_fails_closed() -> None:
    ps_payload = _ps_payload([_ps_position("90010", 100, lower_requires=False)])
    ps_payload["g61_lot_aware_compatibility_consumption"] = {
        **ps_payload["g61_lot_aware_compatibility_consumption"],
        "business_date": "2026-08-22",
    }

    precheck = _g63_runtime_binding_precheck(ps_payload, business_date=BUSINESS_DATE)

    assert precheck["status"] == "BLOCK"
    assert "G61_PS_CONSUMPTION_DATE_MISMATCH" in precheck["reason_codes"]


def _pc_payload() -> dict[str, object]:
    return {
        "producer_result_status": "PASS",
        "portfolio_members": [
            _pc_member("90010"),
            _pc_member("90020"),
            _pc_member("90030"),
            _pc_member("91010", current=True),
            _pc_member("92010", current=True, reduce=True),
        ],
        "capital_competition": {
            "canonical_multi_allocation_deployment_set": {"multi_allocation_set_hash": "phase31-g63"},
        },
    }


def _pc_member(symbol: str, *, current: bool = False, reduce: bool = False) -> dict[str, object]:
    if reduce:
        return {
            "security_code": symbol,
            "membership_intent": "RETAIN",
            "pm_action": "REDUCE",
            "current_position": True,
            "canonical_marginal_capital_priority_index": 99,
        }
    return {
        "security_code": symbol,
        "membership_intent": "RETAIN" if current else "ADD_CANDIDATE",
        "pm_action": "ADD" if current else "NEW",
        "current_position": current,
        "canonical_marginal_capital_priority_index": {"90010": 1, "90020": 2, "90030": 3, "91010": 4}.get(symbol, 99),
    }


def _pm_payload() -> dict[str, object]:
    return {
        "positions": [
            {"security_code": "91010", "action": "ADD", "position_id": "pm-91010"},
            {"security_code": "92010", "action": "REDUCE", "position_id": "pm-92010"},
        ]
    }


def _ps_payload(positions: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema_version": "position_sizing.v1",
        "producer_result_status": "PASS",
        "g61_lot_aware_compatibility_consumption": {
            "schema_version": "position_sizing.g61_lot_aware_compatibility_consumption.v1",
            "status": "PASS",
            "business_date": BUSINESS_DATE,
            "g61_compatibility_consumed_by_ps": True,
            "position_sizing_quantity_owner": "POSITION_SIZING",
            "pc_discrete_quantity_authority": False,
            "position_sizing_recomputes_capital_priority": False,
            "ordinary_lot_feasibility_priority_redecision_allowed": False,
            "lower_priority_implicit_promotion": False,
            "residual_capital_explicit_through_ps": True,
            "capital_conservation": {"status": "PASS"},
            "allocation_count": len(positions),
            "lower_priority_rows_requiring_explicit_residual_resolution": sum(
                1 for row in positions if (row.get("g61_lot_aware_compatibility") or {}).get("lower_priority_execution_requires_explicit_residual_resolution")
            ),
        },
        "positions": positions,
    }


def _ps_position(
    symbol: str,
    quantity_delta: int,
    *,
    lower_requires: bool,
    current: bool = False,
    reduce: bool = False,
) -> dict[str, object]:
    return {
        "security_code": symbol,
        "position_reference": f"ps-{symbol}",
        "schema_version": "position_sizing.v1",
        "membership_intent": "RETAIN" if current or reduce else "ADD_CANDIDATE",
        "pm_action": "REDUCE" if reduce else ("ADD" if current else "NEW"),
        "quantity_status": "RESOLVED_CANDIDATE",
        "target_quantity_candidate": 200 if quantity_delta > 0 else 200,
        "quantity_delta_candidate": quantity_delta,
        "planned_quantity": abs(quantity_delta),
        "g61_lot_aware_compatibility_consumed_by_ps": not reduce,
        "g61_lot_aware_compatibility": {}
        if reduce
        else {
            "compatibility_state": "LOT_EXECUTABLE_COMPATIBLE",
            "lower_priority_execution_requires_explicit_residual_resolution": lower_requires,
            "implicit_priority_promotion_allowed": False,
            "residual_capital_weight": 0.0,
        },
        "lower_priority_implicit_promotion_allowed": False,
        "position_sizing_recomputes_capital_priority": False,
        "ordinary_lot_feasibility_priority_redecision_allowed": False,
    }


def _current_position(symbol: str, quantity: int) -> dict[str, object]:
    return {
        "security_code": symbol,
        "quantity": quantity,
        "source": "runtime_v2_runtime_owned_fill_projection",
        "business_date": BUSINESS_DATE,
        "as_of": BUSINESS_DATE,
    }
