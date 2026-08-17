from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy.portfolio_construction import apply_lot_aware_final_reallocation
from ai_fund_lab_v2.strategy.strategy_intelligence import produce_strategy_intelligence_artifact

from tests.strategy.test_phase22_e_portfolio_construction import _sha256_file, _write_json


BUSINESS_DATE = "2026-07-15"


def test_phase30_w_entry_admission_separates_healthy_from_overheated_without_future_outcomes(tmp_path: Path) -> None:
    path = _write_strategy_intelligence(
        tmp_path,
        [
            _technical_row(
                "11110",
                price_momentum_return_1d=0.01,
                price_momentum_return_3d=0.02,
                price_momentum_return_5d=0.04,
                price_momentum_return_10d=0.06,
                price_momentum_return_20d=0.08,
                momentum_5d_vs_20d_delta=0.01,
                momentum_1d_vs_5d_delta=0.01,
                recent_move_volatility_z_1d=0.2,
            ),
            _technical_row(
                "22220",
                price_momentum_return_1d=-0.15,
                price_momentum_return_3d=0.04,
                price_momentum_return_5d=0.42,
                price_momentum_return_10d=0.90,
                price_momentum_return_20d=2.20,
                momentum_5d_vs_20d_delta=-1.78,
                momentum_1d_vs_5d_delta=-0.57,
                recent_move_volatility_z_1d=1.5,
            ),
        ],
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    healthy = payload["symbol_intelligence"]["11110"]["entry_admission"]
    overheated = payload["symbol_intelligence"]["22220"]["entry_admission"]

    assert healthy["entry_state"] == "HEALTHY_CONTINUATION_ENTRY"
    assert healthy["admission_action"] == "BUY_NEW_ALLOWED"
    assert overheated["entry_state"] == "OVERHEATED_DECELERATING_ENTRY"
    assert overheated["admission_action"] == "BUY_WAIT"
    assert overheated["non_pending_buy_wait"] is True
    assert overheated["next_pit_date_reevaluation_required"] is True
    assert overheated["sell_independent"] is True
    assert overheated["future_information_used"] is False
    assert payload["historical_outcome_used_for_production_parameter_selection"] is False


def test_phase30_w_one_lot_overheated_overshoot_defers_and_recycles_to_quality_candidate(tmp_path: Path) -> None:
    del tmp_path
    members = [
        _buy_new_member(
            "11110",
            priority=1,
            target=0.035714,
            entry_state="OVERHEATED_DECELERATING_ENTRY",
            entry_action="BUY_WAIT",
        ),
        _buy_new_member(
            "22220",
            priority=2,
            target=0.08,
            entry_state="HEALTHY_CONTINUATION_ENTRY",
            entry_action="BUY_NEW_ALLOWED",
        ),
    ]
    result = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=[
            _one_lot_row("11110", minimum_weight=0.245, post_trade_weight=0.245),
            {
                "symbol": "22220",
                "intent_type": "BUY_NEW",
                "lot_feasible": True,
                "broker_eligible": True,
                "minimum_executable_weight": 0.08,
                "phase29_l19_lot_resolution": {
                    "boundary_classification": "CAP_CONSTRAINED_LOT_EXECUTABLE",
                    "one_lot_weight": 0.08,
                    "post_trade_weight": 0.08,
                    "safety_hard_cap_preserved": True,
                },
            },
        ],
        target_gross_exposure=0.25,
        single_name_cap=0.18,
    )
    by_code = {row["security_code"]: row for row in result["members"]}

    assert by_code["11110"]["target_weight"] == 0.0
    assert by_code["11110"]["one_lot_admission"]["status"] == "DEFER"
    assert by_code["11110"]["one_lot_admission"]["safety_hard_cap_preserved"] is True
    assert by_code["22220"]["lot_aware_accepted_buy_new_weight"] == 0.08
    assert result["evidence"]["remaining_cash_weight"] == 0.17
    assert "quality_adjusted_one_lot_admission_deferred_or_blocked" in result["reason_codes"]


def test_phase30_w_high_quality_add_can_still_receive_one_lot_increment(tmp_path: Path) -> None:
    del tmp_path
    result = apply_lot_aware_final_reallocation(
        members=[
            {
                "security_code": "33330",
                "symbol": "33330",
                "current_position": True,
                "membership_intent": "RETAIN",
                "pm_action": "ADD",
                "construction_priority": 1,
                "current_weight": 0.16,
                "requested_incremental_weight": 0.03,
                "accepted_incremental_weight": 0.03,
                "target_weight": 0.19,
                "target_membership": True,
                "add_allocation_eligibility_status": "PASS",
                "incremental_investment_value_state": "POSITIVE",
                "opportunity_cost_status": "PASS",
                "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
                "entry_admission_action": "ADD_ALLOWED",
                "target_weight_authority": {},
                "target_weight_resolution": {"status": "PASS", "resolved_weight": 0.19, "adjustments": []},
            }
        ],
        lot_feasibility_rows=[_one_lot_row("33330", intent_type="BUY_ADD", minimum_weight=0.04, post_trade_weight=0.20)],
        target_gross_exposure=0.40,
        single_name_cap=0.18,
    )
    member = result["members"][0]

    assert member["lot_aware_accepted_incremental_weight"] == 0.04
    assert member["one_lot_admission"]["status"] == "PASS"
    assert member["one_lot_admission"]["add_worthiness_state"] == "ADD_ALLOWED"


def test_phase30_w_weak_survivor_can_hold_without_add(tmp_path: Path) -> None:
    del tmp_path
    result = apply_lot_aware_final_reallocation(
        members=[
            {
                "security_code": "44440",
                "symbol": "44440",
                "current_position": True,
                "membership_intent": "RETAIN",
                "pm_action": "ADD",
                "construction_priority": 1,
                "current_weight": 0.10,
                "requested_incremental_weight": 0.03,
                "accepted_incremental_weight": 0.03,
                "target_weight": 0.13,
                "target_membership": True,
                "entry_admission_state": "REVERSAL_RISK_ENTRY",
                "entry_admission_action": "NO_ADD",
                "target_weight_authority": {},
                "target_weight_resolution": {"status": "PASS", "resolved_weight": 0.13, "adjustments": []},
            }
        ],
        lot_feasibility_rows=[_one_lot_row("44440", intent_type="BUY_ADD", minimum_weight=0.04, post_trade_weight=0.14)],
        target_gross_exposure=0.40,
        single_name_cap=0.18,
    )
    member = result["members"][0]

    assert member["target_weight"] == 0.10
    assert member["lot_aware_accepted_incremental_weight"] == 0.0
    assert member["one_lot_admission"]["status"] == "FAIL_CLOSED"
    assert member["one_lot_admission"]["add_worthiness_state"] == "NO_ADD"


def test_phase30_ak2_buy_new_sub_lot_target_admits_minimum_executable_one_lot(tmp_path: Path) -> None:
    del tmp_path
    result = apply_lot_aware_final_reallocation(
        members=[
            _buy_new_member(
                "55550",
                priority=1,
                target=0.08,
                entry_state="HEALTHY_CONTINUATION_ENTRY",
                entry_action="BUY_NEW_ALLOWED",
            )
        ],
        lot_feasibility_rows=[_minimum_one_lot_row("55550", request_weight=0.08, one_lot_weight=0.10)],
        target_gross_exposure=0.20,
        single_name_cap=0.18,
    )
    member = result["members"][0]

    assert member["target_weight"] == 0.10
    assert member["lot_aware_accepted_buy_new_weight"] == 0.10
    assert member["phase29_l19_lot_resolution"]["minimum_executable_one_lot_admitted"] is True
    assert member["phase29_l19_lot_resolution"]["minimum_executable_one_lot_reason"] == "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED"
    assert member["phase29_l19_lot_resolution"]["final_allocated_quantity"] == 100
    assert member["one_lot_admission"]["status"] == "PASS"
    assert result["evidence"]["promoted"][0]["reason"] == "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED"
    assert "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED" in result["reason_codes"]


def test_phase30_ak2_reentry_sub_lot_target_admits_minimum_executable_one_lot(tmp_path: Path) -> None:
    del tmp_path
    member = _buy_new_member(
        "55551",
        priority=1,
        target=0.08,
        entry_state="HEALTHY_CONTINUATION_ENTRY",
        entry_action="BUY_NEW_ALLOWED",
    )
    member["semantic_buy_type"] = "REENTRY"

    result = apply_lot_aware_final_reallocation(
        members=[member],
        lot_feasibility_rows=[_minimum_one_lot_row("55551", request_weight=0.08, one_lot_weight=0.10, intent_type="REENTRY")],
        target_gross_exposure=0.20,
        single_name_cap=0.18,
    )
    result_member = result["members"][0]

    assert result_member["target_weight"] == 0.10
    assert result_member["phase29_l19_lot_resolution"]["semantic_type"] == "REENTRY"
    assert result_member["phase29_l19_lot_resolution"]["minimum_executable_one_lot_admitted"] is True


def test_phase30_ak2_safety_block_never_admits_minimum_one_lot(tmp_path: Path) -> None:
    del tmp_path
    result = apply_lot_aware_final_reallocation(
        members=[
            _buy_new_member(
                "55552",
                priority=1,
                target=0.08,
                entry_state="HEALTHY_CONTINUATION_ENTRY",
                entry_action="BUY_NEW_ALLOWED",
            )
        ],
        lot_feasibility_rows=[
            _minimum_one_lot_row(
                "55552",
                request_weight=0.08,
                one_lot_weight=0.30,
                safety_preserved=False,
                boundary="MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX",
            )
        ],
        target_gross_exposure=0.40,
        single_name_cap=0.18,
    )

    assert result["members"][0]["target_weight"] == 0.0
    assert result["members"][0]["phase29_l19_lot_resolution"]["minimum_executable_one_lot_admitted"] is False
    assert result["evidence"]["skipped"][0]["reason"] == "minimum_lot_exceeds_safety_hard_cap"


def test_phase30_ak2_strategy_cap_block_preserved_for_buy_new_minimum_one_lot(tmp_path: Path) -> None:
    del tmp_path
    result = apply_lot_aware_final_reallocation(
        members=[
            _buy_new_member(
                "55553",
                priority=1,
                target=0.08,
                entry_state="HEALTHY_CONTINUATION_ENTRY",
                entry_action="BUY_NEW_ALLOWED",
            )
        ],
        lot_feasibility_rows=[_minimum_one_lot_row("55553", request_weight=0.08, one_lot_weight=0.20)],
        target_gross_exposure=0.40,
        single_name_cap=0.18,
    )

    assert result["members"][0]["target_weight"] == 0.0
    assert result["members"][0]["lot_first_rebatch_skip_reason"] == "minimum_lot_exceeds_concentration_cap"
    assert result["members"][0]["phase29_l19_lot_resolution"]["minimum_executable_one_lot_admitted"] is False


def test_phase30_ak2_entry_buy_wait_blocks_minimum_one_lot(tmp_path: Path) -> None:
    del tmp_path
    result = apply_lot_aware_final_reallocation(
        members=[
            _buy_new_member(
                "55554",
                priority=1,
                target=0.08,
                entry_state="OVERHEATED_DECELERATING_ENTRY",
                entry_action="BUY_WAIT",
            )
        ],
        lot_feasibility_rows=[_minimum_one_lot_row("55554", request_weight=0.08, one_lot_weight=0.10)],
        target_gross_exposure=0.20,
        single_name_cap=0.18,
    )

    assert result["members"][0]["target_weight"] == 0.0
    assert result["members"][0]["one_lot_admission"]["status"] == "DEFER"
    assert result["members"][0]["phase29_l19_lot_resolution"]["minimum_executable_one_lot_admitted"] is False


def test_phase30_ak2_cash_insufficient_blocks_minimum_one_lot(tmp_path: Path) -> None:
    del tmp_path
    result = apply_lot_aware_final_reallocation(
        members=[
            _buy_new_member(
                "55555",
                priority=1,
                target=0.08,
                entry_state="HEALTHY_CONTINUATION_ENTRY",
                entry_action="BUY_NEW_ALLOWED",
            )
        ],
        lot_feasibility_rows=[_minimum_one_lot_row("55555", request_weight=0.08, one_lot_weight=0.10)],
        target_gross_exposure=0.09,
        single_name_cap=0.18,
    )

    assert result["members"][0]["target_weight"] == 0.0
    assert result["members"][0]["lot_first_rebatch_skip_reason"] == "minimum_lot_exceeds_remaining_budget"
    assert result["members"][0]["phase29_l19_lot_resolution"]["minimum_executable_one_lot_admitted"] is False


def test_phase30_ak2_existing_add_and_second_lot_do_not_use_minimum_one_lot_exception(tmp_path: Path) -> None:
    del tmp_path
    add_result = apply_lot_aware_final_reallocation(
        members=[
            {
                "security_code": "55556",
                "symbol": "55556",
                "current_position": True,
                "membership_intent": "RETAIN",
                "pm_action": "ADD",
                "construction_priority": 1,
                "current_weight": 0.10,
                "current_quantity": 100,
                "requested_incremental_weight": 0.08,
                "accepted_incremental_weight": 0.08,
                "target_weight": 0.18,
                "target_membership": True,
                "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
                "entry_admission_action": "ADD_ALLOWED",
                "add_allocation_eligibility_status": "PASS",
                "incremental_investment_value_state": "POSITIVE",
                "opportunity_cost_status": "PASS",
                "target_weight_authority": {},
                "target_weight_resolution": {"status": "PASS", "resolved_weight": 0.18, "adjustments": []},
            }
        ],
        lot_feasibility_rows=[_minimum_one_lot_row("55556", request_weight=0.08, one_lot_weight=0.10, intent_type="BUY_ADD")],
        target_gross_exposure=0.40,
        single_name_cap=0.18,
    )
    second_lot_result = apply_lot_aware_final_reallocation(
        members=[
            {
                **_buy_new_member(
                    "55557",
                    priority=1,
                    target=0.08,
                    entry_state="HEALTHY_CONTINUATION_ENTRY",
                    entry_action="BUY_NEW_ALLOWED",
                ),
                "current_position": True,
                "current_quantity": 100,
                "current_weight": 0.10,
                "membership_intent": "RETAIN",
                "pm_action": "ADD",
            }
        ],
        lot_feasibility_rows=[_minimum_one_lot_row("55557", request_weight=0.08, one_lot_weight=0.10, intent_type="BUY_ADD")],
        target_gross_exposure=0.40,
        single_name_cap=0.18,
    )

    assert add_result["members"][0]["phase29_l19_lot_resolution"]["minimum_executable_one_lot_admitted"] is False
    assert second_lot_result["members"][0]["phase29_l19_lot_resolution"]["minimum_executable_one_lot_admitted"] is False


def test_phase30_ak7r_existing_add_close_to_current_lot_does_not_auto_promote(tmp_path: Path) -> None:
    del tmp_path
    result = apply_lot_aware_final_reallocation(
        members=[
            _add_member("77770", current_weight=0.10, request_weight=0.02, target_weight=0.12),
        ],
        lot_feasibility_rows=[_add_lot_row("77770", request_weight=0.02, one_lot_weight=0.10, post_trade_weight=0.20)],
        target_gross_exposure=0.40,
        single_name_cap=0.25,
    )
    member = result["members"][0]

    assert member["target_weight"] == 0.10
    assert member["lot_aware_accepted_incremental_weight"] == 0.0
    assert member["phase29_l19_lot_resolution"]["second_lot_plus_promotion"]["promotion_candidate"] is False
    assert member["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"]["status"] == "NOT_APPLICABLE"


def test_phase30_ak7r_existing_add_closer_to_next_lot_competes_and_promotes(tmp_path: Path) -> None:
    del tmp_path
    result = apply_lot_aware_final_reallocation(
        members=[
            _add_member("77771", current_weight=0.10, request_weight=0.08, target_weight=0.18),
        ],
        lot_feasibility_rows=[_add_lot_row("77771", request_weight=0.08, one_lot_weight=0.10, post_trade_weight=0.20)],
        target_gross_exposure=0.40,
        single_name_cap=0.25,
    )
    member = result["members"][0]
    promotion = member["phase29_l19_lot_resolution"]["second_lot_plus_promotion"]

    assert member["target_weight"] == 0.20
    assert member["lot_aware_accepted_incremental_weight"] == 0.10
    assert promotion["promotion_candidate"] is True
    assert promotion["nearest_lot_distance_evidence"]["threshold_source"] == "DETERMINISTIC_LOT_MIDPOINT_NOT_HISTORICAL_OUTCOME"
    assert member["phase29_l19_lot_resolution"]["final_allocated_quantity"] == 100
    assert member["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"]["status"] == "PASS"
    assert result["evidence"]["promoted"][0]["reason"] == "SECOND_LOT_PLUS_RESIDUAL_CAPITAL_AWARE_PROMOTION"


def test_phase30_ak7r_second_lot_promotion_requires_residual_capital(tmp_path: Path) -> None:
    del tmp_path
    result = apply_lot_aware_final_reallocation(
        members=[
            _add_member("77772", current_weight=0.10, request_weight=0.08, target_weight=0.18),
        ],
        lot_feasibility_rows=[_add_lot_row("77772", request_weight=0.08, one_lot_weight=0.10, post_trade_weight=0.20)],
        target_gross_exposure=0.18,
        single_name_cap=0.25,
    )
    member = result["members"][0]

    assert member["target_weight"] == 0.10
    assert member["lot_first_rebatch_skip_reason"] == "minimum_lot_exceeds_remaining_budget"
    assert member["phase29_l19_lot_resolution"]["second_lot_plus_promotion"]["promotion_candidate"] is True


def test_phase30_ak7r_second_lot_promotion_preserves_safety_and_no_add_blocks(tmp_path: Path) -> None:
    del tmp_path
    safety_result = apply_lot_aware_final_reallocation(
        members=[_add_member("77773", current_weight=0.10, request_weight=0.08, target_weight=0.18)],
        lot_feasibility_rows=[
            _add_lot_row(
                "77773",
                request_weight=0.08,
                one_lot_weight=0.10,
                post_trade_weight=0.20,
                safety_preserved=False,
                boundary="MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX",
            )
        ],
        target_gross_exposure=0.40,
        single_name_cap=0.25,
    )
    no_add_result = apply_lot_aware_final_reallocation(
        members=[
            _add_member(
                "77774",
                current_weight=0.10,
                request_weight=0.08,
                target_weight=0.18,
                entry_state="REVERSAL_RISK_ENTRY",
                entry_action="NO_ADD",
                add_worthiness="NO_ADD",
            )
        ],
        lot_feasibility_rows=[_add_lot_row("77774", request_weight=0.08, one_lot_weight=0.10, post_trade_weight=0.20)],
        target_gross_exposure=0.40,
        single_name_cap=0.25,
    )

    assert safety_result["members"][0]["target_weight"] == 0.10
    assert safety_result["members"][0]["lot_first_rebatch_skip_reason"] == "minimum_lot_exceeds_safety_hard_cap"
    assert no_add_result["members"][0]["target_weight"] == 0.10
    assert no_add_result["members"][0]["one_lot_admission"]["status"] == "FAIL_CLOSED"


def _write_strategy_intelligence(tmp_path: Path, technical_rows: list[dict[str, object]]) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    symbols = [str(row["security_code"]) for row in technical_rows]
    market = tmp_path / "market_context.json"
    _write_json(
        market,
        {
            "schema_version": "market_context.v1",
            "business_date": BUSINESS_DATE,
            "feature_date": BUSINESS_DATE,
            "market_regime": "BULL",
            "metrics": {"return_5d_equal_weight": 0.0, "return_20d_equal_weight": 0.0},
            "artifact_hash": "market-hash",
        },
    )
    corporate = tmp_path / "corporate_event.json"
    _write_json(
        corporate,
        {
            "schema_version": "corporate_event.v1",
            "business_date": BUSINESS_DATE,
            "feature_date": BUSINESS_DATE,
            "coverage_status": "AVAILABLE",
            "symbol_event_facts": {symbol: {"coverage_status": "AVAILABLE", "event_facts": []} for symbol in symbols},
            "artifact_hash": "event-hash",
        },
    )
    result = produce_strategy_intelligence_artifact(
        business_date=BUSINESS_DATE,
        candidate_summary=_summary(tmp_path, "candidate", [{"security_code": symbol} for symbol in symbols]),
        opportunity_summary=_summary(tmp_path, "opportunity", [{"security_code": symbol, "runtime_opportunity_score": 0.7} for symbol in symbols]),
        current_summary=_summary(tmp_path, "current", [{"security_code": symbol, "quantity": 0, "average_price": 1000, "market_value": 0} for symbol in symbols]),
        technical_feature_summary=_summary(tmp_path, "technical", technical_rows),
        price_volatility_summary=_summary(tmp_path, "volatility", [{"security_code": symbol, "reference_price": 1000} for symbol in symbols]),
        market_context_artifact_path=market,
        corporate_event_artifact_path=corporate,
        buy_quality_artifact_path=None,
        portfolio_construction_artifact_path=None,
        position_sizing_artifact_path=None,
        position_management_artifact_path=None,
        runtime_planning_artifact_path=None,
        output_path=tmp_path / "strategy_intelligence.json",
        production_consumer_connected=True,
        consumer_stage="PRE_ACTION_PRODUCTION_EVIDENCE",
    )
    return Path(result.artifact_path)


def _technical_row(symbol: str, **values: object) -> dict[str, object]:
    return {
        "security_code": symbol,
        "business_date": BUSINESS_DATE,
        "feature_date": BUSINESS_DATE,
        "trend_close_over_ma_20d": 1.05,
        "trend_ma_5_20_ratio": 1.02,
        "volume_momentum_ratio_5d": 1.1,
        "reference_price": 1000,
        "volatility_return_std_20d": 0.03,
        **values,
    }


def _buy_new_member(symbol: str, *, priority: int, target: float, entry_state: str, entry_action: str) -> dict[str, object]:
    return {
        "security_code": symbol,
        "symbol": symbol,
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "construction_priority": priority,
        "requested_buy_new_weight": target,
        "accepted_buy_new_weight": target,
        "target_weight": target,
        "target_membership": True,
        "entry_admission_state": entry_state,
        "entry_admission_action": entry_action,
        "target_weight_authority": {},
        "target_weight_resolution": {"status": "PASS", "resolved_weight": target, "adjustments": []},
        "runtime_opportunity_score": max(0.0, 1.0 - priority / 100.0),
    }


def _add_member(
    symbol: str,
    *,
    current_weight: float,
    request_weight: float,
    target_weight: float,
    entry_state: str = "HEALTHY_CONTINUATION_ENTRY",
    entry_action: str = "ADD_ALLOWED",
    add_worthiness: str = "ADD_ALLOWED",
) -> dict[str, object]:
    return {
        "security_code": symbol,
        "symbol": symbol,
        "current_position": True,
        "current_quantity": 100,
        "membership_intent": "RETAIN",
        "pm_action": "ADD",
        "construction_priority": 1,
        "current_weight": current_weight,
        "requested_incremental_weight": request_weight,
        "accepted_incremental_weight": request_weight,
        "target_weight": target_weight,
        "target_membership": True,
        "entry_admission_state": entry_state,
        "entry_admission_action": entry_action,
        "strategy_intelligence_add_worthiness_state": add_worthiness,
        "add_allocation_eligibility_status": "PASS" if add_worthiness != "NO_ADD" else "FAIL_CLOSED",
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "target_weight_authority": {},
        "target_weight_resolution": {"status": "PASS", "resolved_weight": target_weight, "adjustments": []},
        "runtime_opportunity_score": 0.9,
    }


def _one_lot_row(symbol: str, *, intent_type: str = "BUY_NEW", minimum_weight: float, post_trade_weight: float) -> dict[str, object]:
    return {
        "symbol": symbol,
        "intent_type": intent_type,
        "lot_feasible": True,
        "broker_eligible": True,
        "minimum_executable_weight": minimum_weight,
        "phase29_l19_lot_resolution": {
            "boundary_classification": "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX",
            "strategy_cap_weight": 0.18,
            "safety_hard_cap_weight": 0.25,
            "one_lot_weight": minimum_weight,
            "minimum_policy_lot_weight": minimum_weight,
            "post_trade_weight": post_trade_weight,
            "one_lot_fallback_applied": True,
            "one_lot_feasibility_status": "PASS",
            "one_lot_quantity": 100,
            "safety_hard_cap_preserved": True,
        },
    }


def _add_lot_row(
    symbol: str,
    *,
    request_weight: float,
    one_lot_weight: float,
    post_trade_weight: float,
    safety_preserved: bool = True,
    boundary: str = "CAP_CONSTRAINED_LOT_EXECUTABLE",
) -> dict[str, object]:
    requested_lots = int(request_weight // one_lot_weight) if one_lot_weight > 0 else 0
    return {
        "symbol": symbol,
        "intent_type": "BUY_ADD",
        "lot_feasible": safety_preserved,
        "broker_eligible": True,
        "minimum_executable_weight": one_lot_weight,
        "phase29_l19_lot_resolution": {
            "authority_type": "PHASE29_L19_CAP_CONSTRAINED_LOT_RESOLUTION",
            "boundary_classification": boundary,
            "continuous_target_weight": round(0.10 + request_weight, 6),
            "continuous_target_notional": round(request_weight * 1_000_000, 2),
            "requested_incremental_weight": request_weight,
            "requested_target_weight": round(0.10 + request_weight, 6),
            "strategy_cap_weight": 0.25,
            "strategy_target_cap": 0.25,
            "safety_hard_cap_weight": 0.25,
            "safety_hard_cap": 0.25,
            "one_lot_weight": one_lot_weight,
            "one_lot_notional": round(one_lot_weight * 1_000_000, 2),
            "one_lot_quantity": 100,
            "one_lot_fallback_applied": request_weight < one_lot_weight,
            "one_lot_feasibility_status": "PASS" if safety_preserved else "FAIL_CLOSED",
            "normal_lot_quantity": requested_lots * 100,
            "requested_lots": requested_lots,
            "executable_quantity_delta": requested_lots * 100,
            "post_trade_weight": post_trade_weight,
            "safety_hard_cap_preserved": safety_preserved,
            "safety_margin_after_trade": round(0.25 - post_trade_weight, 6),
            "strategy_cap_overshoot_applied": False,
            "lot_overshoot_reason": "",
        },
    }


def _minimum_one_lot_row(
    symbol: str,
    *,
    intent_type: str = "BUY_NEW",
    request_weight: float,
    one_lot_weight: float,
    safety_preserved: bool = True,
    boundary: str = "CAP_CONSTRAINED_LOT_EXECUTABLE",
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "intent_type": intent_type,
        "lot_feasible": safety_preserved,
        "broker_eligible": True,
        "minimum_executable_weight": one_lot_weight,
        "phase29_l19_lot_resolution": {
            "authority_type": "PHASE29_L19_CAP_CONSTRAINED_LOT_RESOLUTION",
            "boundary_classification": boundary,
            "continuous_target_weight": request_weight,
            "continuous_target_notional": round(request_weight * 1_000_000, 2),
            "requested_incremental_weight": request_weight,
            "requested_target_weight": request_weight,
            "strategy_cap_weight": 0.18,
            "strategy_target_cap": 0.18,
            "safety_hard_cap_weight": 0.25,
            "safety_hard_cap": 0.25,
            "one_lot_weight": one_lot_weight,
            "one_lot_notional": round(one_lot_weight * 1_000_000, 2),
            "one_lot_quantity": 100,
            "one_lot_fallback_applied": True,
            "one_lot_feasibility_status": "PASS" if safety_preserved else "FAIL_CLOSED",
            "normal_lot_quantity": 0,
            "requested_lots": 0,
            "executable_quantity_delta": 100 if safety_preserved else 0,
            "post_trade_weight": one_lot_weight,
            "safety_hard_cap_preserved": safety_preserved,
            "safety_margin_after_trade": round(0.25 - one_lot_weight, 6),
            "strategy_cap_overshoot_applied": False,
            "lot_overshoot_reason": "",
        },
    }


def _summary(tmp_path: Path, kind: str, rows: list[dict[str, object]]) -> dict[str, object]:
    path = tmp_path / f"{kind}.json"
    _write_json(path, {"kind": kind, "business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE, "rows": rows})
    return {
        "status": "PASS",
        "business_date": BUSINESS_DATE,
        "feature_date": BUSINESS_DATE,
        "source_ref": str(path),
        "source_hash": _sha256_file(path),
        "rows": rows,
    }
