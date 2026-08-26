from __future__ import annotations

from ai_fund_lab_v2.strategy.position_sizing import (
    PositionSizingConfig,
    PositionSizingSourceSummary,
    build_position_sizing_payload,
)


BUSINESS_DATE = "2026-08-23"


def test_phase31_g62_position_sizing_consumes_g61_compatibility_without_priority_redecision() -> None:
    payload, _ = _build_payload(_pc_summary(_g61_compatibility()))

    consumption = payload["g61_lot_aware_compatibility_consumption"]
    assert payload["producer_result_status"] == "PASS"
    assert consumption["status"] == "PASS"
    assert consumption["g61_compatibility_consumed_by_ps"] is True
    assert consumption["lower_priority_implicit_promotion"] is False
    assert consumption["priority_semantics_preserved_through_ps"] is True
    assert consumption["residual_capital_explicit_through_ps"] is True
    assert consumption["position_sizing_quantity_owner"] == "POSITION_SIZING"
    assert consumption["pc_discrete_quantity_authority"] is False
    assert consumption["executable_multi_security"] is True
    assert consumption["add_compatibility"] == "PASS"
    assert consumption["capital_conservation"]["status"] == "PASS"
    assert consumption["runtime_order_behavior_change_count"] == 0
    assert consumption["future_input_count"] == 0
    assert consumption["historical_outcome_strategy_input_count"] == 0
    assert consumption["lower_priority_rows_requiring_explicit_residual_resolution"] == 1

    row = next(item for item in payload["positions"] if item["security_code"] == "90020")
    assert row["g61_lot_aware_compatibility_consumed_by_ps"] is True
    assert row["g61_lot_aware_compatibility"]["lower_priority_execution_requires_explicit_residual_resolution"] is True
    assert row["lower_priority_implicit_promotion_allowed"] is False
    assert row["position_sizing_recomputes_capital_priority"] is False
    assert row["ordinary_lot_feasibility_priority_redecision_allowed"] is False


def test_phase31_g62_g61_date_mismatch_fails_closed() -> None:
    compatibility = {**_g61_compatibility(), "business_date": "2026-08-22"}
    payload, _ = _build_payload(_pc_summary(compatibility))

    consumption = payload["g61_lot_aware_compatibility_consumption"]
    assert payload["producer_result_status"] == "BLOCK"
    assert consumption["status"] == "BLOCK"
    assert "G61_COMPATIBILITY_DATE_MISMATCH" in payload["reason_codes"]


def test_phase31_g62_g61_missing_rows_fail_closed() -> None:
    compatibility = {k: v for k, v in _g61_compatibility().items() if k != "compatibility_rows"}
    payload, _ = _build_payload(_pc_summary(compatibility))

    consumption = payload["g61_lot_aware_compatibility_consumption"]
    assert payload["producer_result_status"] == "BLOCK"
    assert consumption["status"] == "BLOCK"
    assert "G61_COMPATIBILITY_ROWS_MALFORMED" in payload["reason_codes"]


def test_phase31_g65_multi_allocation_executable_rows_survive_legacy_cash_winner() -> None:
    pc_summary = _pc_summary(_g65_executable_compatibility())
    for member in pc_summary["portfolio_members"]:
        member["reference_price"] = 200.0
    pc_summary["capital_competition"]["canonical_deployment_set"] = {
        "schema_version": "canonical_deployment_set.v1",
        "owner": "PORTFOLIO_CONSTRUCTION",
        "business_date": BUSINESS_DATE,
        "cardinality_contract": "SINGLE",
        "final_winner_type": "CASH_OPTIONALITY",
        "final_winner_symbol": "",
        "cash_winner": True,
        "no_deployable_opportunity": False,
        "selected_deployments": [],
        "deployment_set_hash": "legacy-cash-winner",
    }

    payload, _ = _build_payload(pc_summary)

    by_symbol = {row["security_code"]: row for row in payload["positions"]}
    assert by_symbol["90010"]["canonical_deployment_set_sizing_eligibility"] == "SELECTED_BY_CANONICAL_MULTI_ALLOCATION"
    assert by_symbol["90010"]["quantity_delta_candidate"] > 0
    assert by_symbol["90010"]["final_capital_winner_type"] == "MULTI_ALLOCATION"
    assert by_symbol["90010"]["position_sizing_recomputes_capital_priority"] is False
    assert by_symbol["90020"]["quantity_delta_candidate"] > 0
    assert payload["g61_lot_aware_compatibility_consumption"]["position_sizing_quantity_owner"] == "POSITION_SIZING"
    assert payload["g61_lot_aware_compatibility_consumption"]["pc_discrete_quantity_authority"] is False


def _build_payload(pc_summary: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    rows = tuple(pc_summary["portfolio_members"])  # type: ignore[index]
    return build_position_sizing_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_summary=_summary(rows=rows, summary=pc_summary),
        capital_deployment_summary=_summary(),
        dynamic_position_count_summary=_summary(summary={"target_position_count": 2}),
        dynamic_cash_exposure_summary=_summary(summary={"target_gross_exposure_ratio": 0.20, "market_context_risk_state": "NORMAL"}),
        position_management_summary=_summary(),
        opportunity_summary=_summary(),
        current_position_summary=_summary(summary={"portfolio_total_equity": 1_000_000.0, "portfolio_value": 1_000_000.0}),
        price_volatility_summary=_summary(rows=tuple({"security_code": symbol, "volatility_value": 0.02} for symbol in ("90010", "90020"))),
        safety_limit_summary=_summary(summary={"concentration": {"maximum_position_weight": 0.25}}),
        config=_config(),
    )


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
        source_ref="test://phase31-g62",
        source_hash="phase31-g62",
        rows=rows,
        summary=summary or {},
    )


def _config() -> PositionSizingConfig:
    return PositionSizingConfig(
        config_version="phase31-g62-test",
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


def _pc_summary(compatibility: dict[str, object]) -> dict[str, object]:
    multi = {
        "schema_version": "canonical_multi_allocation_deployment_set.v1",
        "owner": "PORTFOLIO_CONSTRUCTION",
        "authority_status": "SHADOW_NON_AUTHORITATIVE",
        "business_date": BUSINESS_DATE,
        "security_allocations": compatibility.get("compatibility_rows", []),
        "lot_aware_allocation_to_sizing_compatibility": compatibility,
        "multi_allocation_set_hash": "g62-multi-hash",
    }
    return {
        "portfolio_members": [_member("90010", 0.04), _member("90020", 0.04)],
        "canonical_multi_allocation_deployment_set": multi,
        "capital_competition": {"canonical_multi_allocation_deployment_set": multi},
    }


def _member(symbol: str, target_weight: float) -> dict[str, object]:
    return {
        "security_code": symbol,
        "symbol": symbol,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "current_position": False,
        "current_weight": 0.0,
        "current_quantity": 0,
        "target_weight": target_weight,
        "requested_buy_new_weight": target_weight,
        "accepted_buy_new_weight": target_weight,
        "construction_priority": 1 if symbol == "90010" else 2,
        "quality_decision_id": f"quality-{symbol}",
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "quality_status": "PASS",
        "quality_score": 0.8,
        "quality_allocation_adjustment": 1.0,
        "confidence": 1.0,
        "reference_price": 1_200.0 if symbol == "90010" else 200.0,
        "reference_price_authority": {
            "authority_type": "REFERENCE_PRICE_AUTHORITY",
            "PIT_status": "PASS",
            "source_field": "reference_price",
            "latest_fallback_used": False,
        },
        "target_weight_authority": {"authority_type": "TARGET_WEIGHT_AUTHORITY"},
        "target_weight_resolution": {"status": "PASS", "resolved_weight": target_weight, "reason": "test"},
    }


def _g61_compatibility() -> dict[str, object]:
    rows = [
        _compat_row("90010", rank=1, state="LOT_INFEASIBLE_RESIDUAL_REQUIRED", lower_requires=False),
        _compat_row("90020", rank=2, state="LOT_EXECUTABLE_COMPATIBLE", lower_requires=True),
    ]
    return {
        "schema_version": "portfolio_construction.lot_aware_allocation_to_sizing_compatibility.v1",
        "owner": "PORTFOLIO_CONSTRUCTION",
        "authority_status": "SHADOW_NON_AUTHORITATIVE",
        "business_date": BUSINESS_DATE,
        "position_sizing_quantity_owner": "POSITION_SIZING",
        "pc_discrete_quantity_authority": False,
        "authorized_for_position_sizing": False,
        "authorized_for_runtime_order": False,
        "allocation_count": 2,
        "lot_executable_count": 1,
        "executable_multi_security": True,
        "priority_inversion_detected_raw": True,
        "priority_inversion_after_compatibility": False,
        "lower_priority_implicit_promotion_allowed": False,
        "residual_capital_explicit": True,
        "residual_capital_weight": 0.04,
        "add_compatibility": "PASS",
        "capital_conservation": {"status": "PASS"},
        "compatibility_hash": "g61-compat-hash",
        "compatibility_rows": rows,
    }


def _g65_executable_compatibility() -> dict[str, object]:
    rows = [
        _compat_row("90010", rank=1, state="LOT_EXECUTABLE_COMPATIBLE", lower_requires=False),
        _compat_row("90020", rank=2, state="LOT_EXECUTABLE_COMPATIBLE", lower_requires=False),
    ]
    return {
        **_g61_compatibility(),
        "lot_executable_count": 2,
        "compatibility_executable_count": 2,
        "executable_multi_security": True,
        "priority_inversion_detected_raw": False,
        "residual_capital_weight": 0.0,
        "compatibility_rows": rows,
    }


def _compat_row(symbol: str, *, rank: int, state: str, lower_requires: bool) -> dict[str, object]:
    return {
        "schema_version": "portfolio_construction.lot_aware_allocation_to_sizing_compatibility.v1",
        "owner": "PORTFOLIO_CONSTRUCTION",
        "authority_status": "SHADOW_NON_AUTHORITATIVE",
        "business_date": BUSINESS_DATE,
        "symbol": symbol,
        "allocation_rank": rank,
        "competitor_type": "NEW_BUY",
        "opportunity_type": "NEW_BUY",
        "authorized_allocation_weight": 0.04,
        "minimum_executable_weight": 0.12 if symbol == "90010" else 0.02,
        "executable_before_residual_reallocation": state == "LOT_EXECUTABLE_COMPATIBLE",
        "compatibility_state": state,
        "lower_priority_execution_requires_explicit_residual_resolution": lower_requires,
        "implicit_priority_promotion_allowed": False,
        "position_sizing_quantity_authority_preserved": True,
        "pc_quantity_authority": False,
        "residual_capital_weight": 0.04 if state != "LOT_EXECUTABLE_COMPATIBLE" else 0.0,
        "reason_codes": [state],
    }
