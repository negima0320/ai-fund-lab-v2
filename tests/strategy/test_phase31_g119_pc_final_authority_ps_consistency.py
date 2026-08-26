from __future__ import annotations

from ai_fund_lab_v2.strategy import position_sizing


BUSINESS_DATE = "2022-10-12"


def test_phase31_g119_pc_final_authority_overrides_stale_cash_defeat_for_ps_quantity() -> None:
    rows = position_sizing._apply_canonical_deployment_set_to_sizing_rows(
        [_new_buy_65500()],
        _cash_winner_summary(),
    )

    adjusted = rows[0]
    assert adjusted["canonical_deployment_set_sizing_eligibility"] == "SELECTED_BY_PC_FINAL_DISCRETE_AUTHORITY"
    binding = adjusted["target_weight_resolution"]["canonical_deployment_set_binding"]
    assert binding["cash_winner"] is False
    assert binding["pc_final_discrete_authority_precedence"] is True

    sized = position_sizing._raw_position(
        adjusted,
        config=_config(),
        base=0.0,
        max_weight=0.25,
        portfolio_value=1_000_000.0,
        safety_cap=0.25,
    )

    assert sized["pc_discrete_authorized_quantity"] == 100
    assert sized["pc_discrete_quantity_authority_consumed"] is True
    assert sized["quantity_delta_candidate"] == 100
    assert "PC_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY_CONSUMED" in sized["reason_codes"]


def test_phase31_g119_final_cash_loser_without_pc_quantity_authority_remains_zero() -> None:
    rows = position_sizing._apply_canonical_deployment_set_to_sizing_rows(
        [_new_buy_65500(authority_status="NOT_APPLICABLE", final_quantity=0)],
        _cash_winner_summary(),
    )

    adjusted = rows[0]
    assert adjusted["canonical_deployment_set_sizing_eligibility"] == "DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION"
    assert adjusted["target_weight"] == 0.0
    assert adjusted["target_weight_resolution"]["canonical_deployment_set_binding"]["cash_winner"] is True

    sized = position_sizing._raw_position(
        adjusted,
        config=_config(),
        base=0.0,
        max_weight=0.25,
        portfolio_value=1_000_000.0,
        safety_cap=0.25,
    )

    assert sized["pc_discrete_authorized_quantity"] == 0
    assert sized["pc_discrete_quantity_authority_consumed"] is False
    assert sized["quantity_delta_candidate"] == 0


def test_phase31_g119_invalid_pc_quantity_authority_does_not_fail_open() -> None:
    rows = position_sizing._apply_canonical_deployment_set_to_sizing_rows(
        [_new_buy_65500(ps_must_consume=False)],
        _cash_winner_summary(),
    )

    adjusted = rows[0]
    assert adjusted["canonical_deployment_set_sizing_eligibility"] == "DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION"
    assert adjusted["target_weight"] == 0.0


def test_phase31_g119_add_staged_authority_not_promoted_by_new_buy_repair() -> None:
    rows = position_sizing._apply_canonical_deployment_set_to_sizing_rows(
        [_add_94320()],
        _cash_winner_summary(),
    )

    adjusted = rows[0]
    assert adjusted["canonical_deployment_set_sizing_eligibility"] == "DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION"
    assert adjusted["target_weight"] == 0.04
    assert "pc_final_discrete_authority_selected_for_sizing" not in adjusted["reason_codes"]


def _new_buy_65500(
    *,
    authority_status: str = "PASS",
    final_quantity: int = 100,
    ps_must_consume: bool = True,
) -> dict[str, object]:
    return {
        "security_code": "65500",
        "symbol": "65500",
        "business_date": BUSINESS_DATE,
        "current_position": False,
        "current_quantity": 0,
        "current_weight": 0.0,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "semantic_buy_type": "BUY_NEW",
        "construction_priority": 9,
        "opportunity_buy_rank": 9,
        "runtime_opportunity_score": 0.02445178,
        "confidence": 0.9,
        "target_weight": 0.018564,
        "accepted_buy_new_weight": 0.018564,
        "lot_aware_accepted_buy_new_weight": 0.018564 if final_quantity > 0 else 0.0,
        "quality_score": 1.0,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "quality_status": "PASS",
        "quality_decision_id": f"{BUSINESS_DATE}:65500:quality",
        "target_weight_authority": _target_weight_authority(),
        "target_weight_resolution": {
            "status": "PASS",
            "reason": "lot_aware_final_reallocation",
            "resolved_weight": 0.018564,
            "lot_aware_final_reallocation": {
                "authority_type": "PORTFOLIO_CONSTRUCTION_LOT_AWARE_FINAL_REALLOCATION",
                "accepted_lot_increment_weight": 0.018564 if final_quantity > 0 else 0.0,
                "post_lot_target_weight": 0.018564 if final_quantity > 0 else 0.0,
                "final_allocated_quantity": final_quantity,
                "pc_positive_executable_quantity_authority": _pc_quantity_authority(
                    authority_status=authority_status,
                    final_quantity=final_quantity,
                    ps_must_consume=ps_must_consume,
                ),
            },
        },
        "phase29_l19_lot_resolution": {
            "semantic_type": "BUY_NEW",
            "final_target_weight": 0.018564 if final_quantity > 0 else 0.0,
            "final_allocated_quantity": final_quantity,
            "one_lot_quantity": 100,
            "one_lot_notional": 19_600.0,
            "one_lot_feasibility_status": "PASS",
            "one_lot_fallback_applied": True,
            "strategy_target_cap": 0.25,
            "safety_hard_cap": 0.25,
            "safety_hard_cap_weight": 0.25,
            "safety_hard_cap_preserved": True,
            "post_trade_weight": 0.018564 if final_quantity > 0 else 0.0,
            "pc_positive_executable_quantity_authority": _pc_quantity_authority(
                authority_status=authority_status,
                final_quantity=final_quantity,
                ps_must_consume=ps_must_consume,
            ),
        },
        "reference_price": 196.0,
        "reference_price_authority": {
            "authority_type": "REFERENCE_PRICE_AUTHORITY",
            "status": "PASS",
            "reference_price": 196.0,
            "source": "test",
            "business_date": BUSINESS_DATE,
            "PIT_status": "PASS",
            "source_field": "reference_price",
            "future_information_used": False,
        },
        "reference_price_resolution": {"status": "PASS", "resolved_price": 196.0},
        "trading_unit": 100,
    }


def _add_94320() -> dict[str, object]:
    row = _new_buy_65500()
    return {
        **row,
        "security_code": "94320",
        "symbol": "94320",
        "current_position": True,
        "current_quantity": 200,
        "current_weight": 0.04,
        "membership_intent": "RETAIN",
        "pm_action": "ADD",
        "semantic_buy_type": "BUY_ADD",
        "target_weight": 0.055042,
        "accepted_incremental_weight": 0.015042,
        "lot_aware_accepted_incremental_weight": 0.015042,
        "phase29_l19_lot_resolution": {
            **dict(row["phase29_l19_lot_resolution"]),
            "semantic_type": "BUY_ADD",
            "post_trade_weight": 0.055042,
            "final_target_weight": 0.055042,
        },
    }


def _pc_quantity_authority(*, authority_status: str, final_quantity: int, ps_must_consume: bool) -> dict[str, object]:
    return {
        "authority_type": "PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY",
        "status": authority_status,
        "semantic_type": "BUY_NEW",
        "final_allocated_quantity": final_quantity,
        "ps_must_consume_canonical_quantity": ps_must_consume,
        "future_information_used": False,
        "historical_outcome_used": False,
    }


def _target_weight_authority() -> dict[str, object]:
    return {
        "authority_type": "TARGET_WEIGHT_AUTHORITY",
        "business_date": BUSINESS_DATE,
        "PIT_status": "PASS",
        "single_name_weight_cap": 0.25,
        "target_gross_exposure": 0.8,
        "resolved_target_member_count": 1,
        "source_artifact_paths": [],
        "source_artifact_hashes": [],
    }


def _cash_winner_summary() -> dict[str, object]:
    return {
        "canonical_deployment_set": {
            "schema_version": "canonical_deployment_set.v1",
            "owner": "PORTFOLIO_CONSTRUCTION",
            "cardinality_contract": "SINGLE_WINNER_OR_CASH",
            "final_winner_type": "CASH_OPTIONALITY",
            "final_winner_symbol": "",
            "cash_winner": True,
            "selected_symbol_set": [],
            "selected_deployments": [],
            "deployment_set_hash": "sha256:g119-cash-winner",
            "no_deployable_opportunity": False,
        }
    }


def _config() -> position_sizing.PositionSizingConfig:
    return position_sizing.PositionSizingConfig(
        config_version="test",
        config_source="test",
        sizing_method="asset_proportional",
        opportunity_adjustment={},
        volatility_adjustment={},
        pm_intent_adjustment={},
        minimum_meaningful_notional={"base_jpy": 0.0, "tradable_unit": 100.0, "price_buffer_ratio": 0.0},
        strategy_maximum_position_weight=0.25,
        safety_concentration_reference="test",
    )
