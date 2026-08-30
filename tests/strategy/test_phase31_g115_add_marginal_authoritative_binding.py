from __future__ import annotations

from ai_fund_lab_v2.strategy import position_sizing
from ai_fund_lab_v2.strategy.portfolio_construction import (
    _add_marginal_increment_classification,
    _resolve_canonical_add_allocation_bridge,
    apply_lot_aware_final_reallocation,
    build_capital_competition_framework,
    resolve_add_acceleration_tier,
)


BUSINESS_DATE = "2026-08-27"


def test_phase31_g115_authoritative_artifact_authorizes_one_add_increment() -> None:
    competition = _competition(
        [
            _add("76470", requested_weight=0.05, current_quantity=400, current_weight=0.04, priority=1),
            _new("11110", weight=0.03, priority=5),
        ],
        available_budget=0.20,
    )
    authority = competition["canonical_add_marginal_capital_competition_authority"]
    rows = [row for row in authority["authority_rows"] if row["symbol"] == "76470"]

    assert authority["schema_version"] == "canonical_add_marginal_capital_competition_authority.v1"
    assert authority["authority_status"] == "AUTHORITATIVE_STAGED_PC_BINDING"
    assert authority["binding_semantic"] == "OPTION_B_WITH_OPTION_C_FRONTIER_GUARD_STAGED_PARTIAL_BINDING"
    assert authority["pm_add_intent_owner"] == "POSITION_MANAGEMENT"
    assert authority["position_sizing_quantity_owner"] == "POSITION_SIZING"
    assert authority["runtime_priority_redecision_allowed"] is False
    assert sum(1 for row in rows if row["authorized"] is True) == 1
    assert rows[0]["authorized_increment_quantity"] == 100
    assert rows[0]["authorized_increment_weight"] == rows[0]["one_lot_weight"]
    assert authority["authorized_increment_by_symbol"]["76470"] == rows[0]["one_lot_weight"]


def test_phase31_g115_terminal_add_increment_classes_fail_closed() -> None:
    competition = _competition(
        [
            _add("10010", requested_weight=0.0005, current_quantity=100, current_weight=0.02, priority=1),
            _add("20010", requested_weight=0.20, current_quantity=900, current_weight=0.095, priority=2, cap=0.10),
        ],
        available_budget=0.20,
    )
    authority = competition["canonical_add_marginal_capital_competition_authority"]
    by_symbol = {row["symbol"]: row for row in authority["authority_rows"]}

    assert by_symbol["10010"]["classification"] == "LOT_INFEASIBLE"
    assert by_symbol["10010"]["authorized"] is False
    assert by_symbol["20010"]["classification"] == "SAFETY_TERMINAL"
    assert by_symbol["20010"]["authorized"] is False
    assert authority["safety_terminal_resurrection_count"] == 0
    assert authority["lot_infeasible_resurrection_count"] == 0


def test_phase31_g115_lot_aware_final_reallocation_caps_add_to_one_increment() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            _add("76470", requested_weight=0.05, current_quantity=400, current_weight=0.04, priority=1),
        ],
        lot_feasibility_rows=[
            {
                "symbol": "76470",
                "lot_feasible": True,
                "broker_eligible": True,
                "minimum_executable_weight": 0.01,
                "phase29_l19_lot_resolution": {
                    "semantic_type": "BUY_ADD",
                    "one_lot_quantity": 100,
                    "one_lot_notional": 10_000.0,
                    "one_lot_feasibility_status": "PASS",
                    "final_allocated_quantity": 100,
                    "safety_hard_cap": 0.25,
                    "safety_hard_cap_weight": 0.25,
                    "safety_hard_cap_preserved": True,
                    "post_trade_weight": 0.05,
                },
            }
        ],
        target_gross_exposure=0.30,
        single_name_cap=0.25,
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": 0.30},
        final_capital_competition_risk_pacing_evidence=_risk(),
    )
    member = result["members"][0]
    lot_authority = member["target_weight_resolution"]["lot_aware_final_reallocation"]

    assert member["target_weight"] == 0.05
    assert member["lot_aware_accepted_incremental_weight"] == 0.01
    assert lot_authority["canonical_add_marginal_capital_competition_authority"]["authority_status"] == "AUTHORITATIVE_STAGED_PC_BINDING"
    assert lot_authority["pc_positive_executable_quantity_authority"]["status"] == "PASS"
    assert lot_authority["pc_positive_executable_quantity_authority"]["final_allocated_quantity"] == 100


def test_phase31_g115_position_sizing_consumes_g115_pc_discrete_authority() -> None:
    row = _ps_add_row()
    payload, _ = position_sizing.build_position_sizing_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_summary=_summary(rows=[row]),
        capital_deployment_summary=_summary(),
        dynamic_position_count_summary=_summary(summary={"target_position_count": 1}),
        dynamic_cash_exposure_summary=_summary(summary={"target_gross_exposure_ratio": 0.8}),
        position_management_summary=_summary(),
        opportunity_summary=_summary(),
        current_position_summary=_summary(summary={"portfolio_value": 1_000_000}),
        price_volatility_summary=_summary(),
        safety_limit_summary=_summary(summary={"maximum_position_weight": 0.25, "safety_maximum_position_weight": 0.25}),
        config=position_sizing.load_position_sizing_config("configs/strategy/position_sizing.json"),
    )
    position = payload["positions"][0]

    assert position["pm_action"] == "ADD"
    assert position["pc_discrete_quantity_authority_consumed"] is True
    assert position["quantity_delta_candidate"] == 100
    assert position["pc_discrete_authorized_quantity"] == 100


def test_phase31_g129_positive_add_evidence_not_erased_by_unrelated_mcc_fail_closed() -> None:
    classification, reason = _add_marginal_increment_classification(
        add_competitor=_add_competitor_with_investment_evidence("94320", priority=1),
        interaction={"interaction_result": "FAIL_CLOSED"},
        add_key=(1,),
        best_security_key=(1,),
    )

    assert classification == "ADD_MARGINAL_PREFERRED"
    assert reason == "ADD_POSITIVE_EVIDENCE_OVERRIDES_UNRELATED_MCC_FAIL_CLOSED"


def test_phase31_g129_mcc_fail_closed_remains_when_add_evidence_missing() -> None:
    classification, reason = _add_marginal_increment_classification(
        add_competitor={"symbol": "94320", "canonical_add_competitor": {}},
        interaction={"interaction_result": "FAIL_CLOSED"},
        add_key=(1,),
        best_security_key=(1,),
    )

    assert classification == "INSUFFICIENT_EVIDENCE"
    assert reason == "MARKET_CANDIDATE_CASH_INTERACTION_FAIL_CLOSED"


def test_phase32_s_normal_add_baseline_preserved_without_complete_strong_evidence() -> None:
    row = _phase32_s_add("76470", quality_action="REDUCED_ALLOCATION_ONLY")
    bridge = _phase32_s_bridge(row, risk_pacing="NORMAL_DEPLOYMENT")

    assert bridge["member_fields"]["add_acceleration_tier"] == "NORMAL_ADD"
    assert bridge["member_fields"]["pre_acceleration_incremental_weight"] == 0.04
    assert bridge["member_fields"]["tier_bounded_incremental_weight"] == 0.04
    assert bridge["post_add_target_weight"] == 0.09


def test_phase32_s_strong_add_authorizes_larger_continuous_pc_increment() -> None:
    row = _phase32_s_add("76470")
    bridge = _phase32_s_bridge(row, risk_pacing="NORMAL_DEPLOYMENT")
    fields = bridge["member_fields"]

    assert fields["add_acceleration_tier"] == "STRONG_ADD"
    assert fields["add_acceleration_status"] == "PASS"
    assert fields["pre_acceleration_incremental_weight"] == 0.04
    assert fields["tier_bounded_incremental_weight"] == 0.08
    assert bridge["post_add_target_weight"] == 0.13
    assert fields["add_acceleration_authority"]["owner"] == "PORTFOLIO_CONSTRUCTION"
    assert fields["add_acceleration_authority"]["position_sizing_quantity_owner"] == "POSITION_SIZING"
    assert fields["add_acceleration_authority"]["runtime_quantity_redecision_allowed"] is False


def test_phase32_s_exceptional_add_requires_explicit_complete_evidence() -> None:
    row = _phase32_s_add("76470")
    normal_risk = _phase32_s_risk("NORMAL_DEPLOYMENT")
    add_evidence = _phase32_s_add_evidence(row)
    not_exceptional = resolve_add_acceleration_tier(
        row=row,
        business_date=BUSINESS_DATE,
        pre_acceleration_incremental_weight=0.04,
        current_weight=0.05,
        single_name_cap=0.25,
        target_gross_exposure=0.8,
        risk_pacing_evidence=normal_risk,
        add_evidence=add_evidence,
    )
    exceptional = resolve_add_acceleration_tier(
        row={**row, "add_exceptional_acceleration_candidate": "TRUE"},
        business_date=BUSINESS_DATE,
        pre_acceleration_incremental_weight=0.04,
        current_weight=0.05,
        single_name_cap=0.25,
        target_gross_exposure=0.8,
        risk_pacing_evidence=normal_risk,
        add_evidence=add_evidence,
    )

    assert not_exceptional["tier"] == "STRONG_ADD"
    assert exceptional["tier"] == "EXCEPTIONAL_ADD"
    assert exceptional["tier_bounded_incremental_weight"] > not_exceptional["tier_bounded_incremental_weight"]


def test_phase32_s_acceleration_fail_closes_on_weak_or_unknown_or_opportunity_cost_fail() -> None:
    cases = (
        {"expected_edge_improvement_state": "WEAKENING"},
        {"incremental_investment_value_state": "UNKNOWN"},
        {"opportunity_cost_status": "FAIL"},
    )
    for mutation in cases:
        row = {**_phase32_s_add("76470"), **mutation}
        bridge = _phase32_s_bridge(row, risk_pacing="NORMAL_DEPLOYMENT")
        fields = bridge["member_fields"]
        assert fields["add_acceleration_tier"] == "NO_ACCELERATION"
        assert fields["add_acceleration_status"] == "FAIL_CLOSED"
        assert bridge["post_add_target_weight"] == 0.05


def test_phase32_s_buy_wait_and_zero_quality_adjustment_keep_add_zero() -> None:
    for row in (
        _phase32_s_add("76470", quality_action="BUY_WAIT"),
        _phase32_s_add("76470", quality_action="FULL_ALLOCATION_ELIGIBLE", quality_adjustment=0.0),
    ):
        bridge = _phase32_s_bridge(row, risk_pacing="NORMAL_DEPLOYMENT")
        fields = bridge["member_fields"]
        assert fields["add_acceleration_tier"] == "NO_ACCELERATION"
        assert fields["add_acceleration_status"] == "FAIL_CLOSED"
        assert fields["tier_bounded_incremental_weight"] == 0.0
        assert fields["accepted_incremental_weight"] == 0.0
        assert bridge["post_add_target_weight"] == 0.05


def test_phase32_s_missing_campaign_or_no_loss_failure_blocks_acceleration() -> None:
    missing_campaign = _phase32_s_add("76470")
    for field in ("position_campaign_id", "current_position_campaign_id", "pm_position_campaign_id", "opportunity_position_campaign_id"):
        missing_campaign.pop(field, None)
    no_loss_fail = {**_phase32_s_add("76470"), "no_loss_averaging_status": "FAIL"}

    for row in (missing_campaign, no_loss_fail):
        bridge = _phase32_s_bridge(row, risk_pacing="NORMAL_DEPLOYMENT")
        fields = bridge["member_fields"]
        assert fields["add_acceleration_tier"] == "NO_ACCELERATION"
        assert fields["add_acceleration_status"] == "FAIL_CLOSED"
        assert bridge["post_add_target_weight"] == 0.05


def test_phase32_s_headroom_and_cautious_risk_pacing_bound_magnitude() -> None:
    capped = _phase32_s_bridge(
        _phase32_s_add("76470", current_weight=0.22, requested_weight=0.04, cap=0.25),
        risk_pacing="NORMAL_DEPLOYMENT",
    )
    cautious = _phase32_s_bridge(_phase32_s_add("76470"), risk_pacing="CAUTIOUS_DEPLOYMENT")

    assert capped["member_fields"]["add_acceleration_tier"] == "STRONG_ADD"
    assert capped["member_fields"]["tier_bounded_incremental_weight"] == 0.03
    assert capped["post_add_target_weight"] == 0.25
    assert cautious["member_fields"]["add_acceleration_tier"] == "NORMAL_ADD"
    assert cautious["member_fields"]["tier_bounded_incremental_weight"] == 0.04
    assert cautious["post_add_target_weight"] == 0.09


def test_phase32_s_missing_risk_pacing_fails_closed_not_accelerated() -> None:
    row = _phase32_s_add("76470")
    add_evidence = _phase32_s_add_evidence(row)
    result = resolve_add_acceleration_tier(
        row=row,
        business_date=BUSINESS_DATE,
        pre_acceleration_incremental_weight=0.04,
        current_weight=0.05,
        single_name_cap=0.25,
        target_gross_exposure=0.8,
        risk_pacing_evidence={},
        add_evidence=add_evidence,
    )

    assert result["tier"] == "NO_ACCELERATION"
    assert result["status"] == "FAIL_CLOSED"
    assert "ADD_ACCELERATION_RISK_PACING_FAIL_CLOSED" in result["reason_codes"]


def test_phase32_s_cash_and_strong_new_can_still_beat_add() -> None:
    cash_preferred = build_capital_competition_framework(
        members=[_add("76470", requested_weight=0.04, current_quantity=400, current_weight=0.05, priority=1)],
        target_gross_exposure=0.50,
        total_target_weight=0.09,
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": 0.20},
        risk_pacing_evidence=_risk(),
    )
    strong_new = build_capital_competition_framework(
        members=[
            _add("76470", requested_weight=0.04, current_quantity=400, current_weight=0.05, priority=5),
            _new("11110", weight=0.08, priority=1),
        ],
        target_gross_exposure=0.50,
        total_target_weight=0.17,
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": 0.20},
        risk_pacing_evidence=_phase32_s_risk("NORMAL_DEPLOYMENT"),
    )

    assert cash_preferred["capital_competition_winner_type"] == "CASH_OPTIONALITY"
    assert strong_new["capital_competition_winner_type"] == "NEW_BUY"


def test_phase32_s_larger_pc_continuous_add_can_be_materialized_as_multiple_ps_lots() -> None:
    row = _ps_add_row()
    row.update(
        {
            "target_weight": 0.16,
            "target_weight_change": 0.12,
            "post_add_target_weight": 0.16,
            "accepted_incremental_weight": 0.12,
            "tier_bounded_incremental_weight": 0.12,
            "add_acceleration_tier": "STRONG_ADD",
        }
    )
    row["phase29_l19_lot_resolution"]["final_allocated_quantity"] = 300
    row["phase29_l19_lot_resolution"]["post_trade_weight"] = 0.16
    row["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"][
        "final_allocated_quantity"
    ] = 300
    row["target_weight_resolution"]["resolved_weight"] = 0.16
    row["target_weight_resolution"]["lot_aware_final_reallocation"]["phase29_l19_lot_resolution"][
        "final_allocated_quantity"
    ] = 300
    row["target_weight_resolution"]["lot_aware_final_reallocation"]["phase29_l19_lot_resolution"][
        "post_trade_weight"
    ] = 0.16
    row["target_weight_resolution"]["lot_aware_final_reallocation"]["pc_positive_executable_quantity_authority"][
        "final_allocated_quantity"
    ] = 300
    payload, _ = position_sizing.build_position_sizing_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_summary=_summary(rows=[row]),
        capital_deployment_summary=_summary(),
        dynamic_position_count_summary=_summary(summary={"target_position_count": 1}),
        dynamic_cash_exposure_summary=_summary(summary={"target_gross_exposure_ratio": 0.8}),
        position_management_summary=_summary(),
        opportunity_summary=_summary(),
        current_position_summary=_summary(summary={"portfolio_value": 1_000_000}),
        price_volatility_summary=_summary(),
        safety_limit_summary=_summary(summary={"maximum_position_weight": 0.25, "safety_maximum_position_weight": 0.25}),
        config=position_sizing.load_position_sizing_config("configs/strategy/position_sizing.json"),
    )

    position = payload["positions"][0]
    assert position["pc_discrete_quantity_authority_consumed"] is True
    assert position["quantity_delta_candidate"] == 300
    assert position["pc_discrete_authorized_quantity"] == 300


def _competition(members: list[dict[str, object]], *, available_budget: float) -> dict[str, object]:
    return build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.50,
        total_target_weight=sum(float(row.get("target_weight") or 0.0) for row in members),
        business_date=BUSINESS_DATE,
        incremental_budget_evidence={"available_incremental_budget": available_budget},
        risk_pacing_evidence=_risk(),
    )


def _risk() -> dict[str, object]:
    return _phase32_s_risk("CAUTIOUS_DEPLOYMENT")


def _phase32_s_risk(intent: str) -> dict[str, object]:
    return {
        "risk_pacing_intent": intent,
        "risk_pacing_as_of": BUSINESS_DATE,
        "risk_pacing_evidence_completeness": "COMPLETE",
        "mode": "AUTHORITATIVE",
        "risk_pacing_component_evidence": {
            "schema_version": "risk_pacing_component_evidence.v1",
            "business_date": BUSINESS_DATE,
            "market_quality_state": "SHORT_TERM_BREADTH_BREAKDOWN",
            "market_quality_evidence_completeness": "COMPLETE",
            "future_information_used": False,
            "historical_outcome_used": False,
        },
        "incremental_capital_budget_envelope": {
            "schema_version": "incremental_capital_budget_envelope.v1",
            "owner": "PORTFOLIO_POLICY",
            "authority_status": "AUTHORITATIVE",
            "business_date": BUSINESS_DATE,
            "market_quality_as_of": BUSINESS_DATE,
            "risk_pacing_as_of": BUSINESS_DATE,
            "deployment_capacity_semantic": "SELECTIVE_DEPLOYMENT_CAPACITY",
            "bootstrap_or_residual_cash_state": "NORMAL_INVESTED_PORTFOLIO",
            "envelope_hash": "test-g115-risk",
        },
    }


def _phase32_s_add(
    symbol: str,
    *,
    current_weight: float = 0.05,
    requested_weight: float = 0.04,
    cap: float = 0.25,
    quality_action: str = "FULL_ALLOCATION_ELIGIBLE",
    quality_adjustment: float | None = None,
) -> dict[str, object]:
    campaign_id = f"pc-phase32s-{symbol}-0001"
    row = _add(symbol, requested_weight=requested_weight, current_quantity=400, current_weight=current_weight, priority=1, cap=cap)
    row.update(
        {
            "target_weight": current_weight + requested_weight,
            "position_campaign_id": campaign_id,
            "current_position_campaign_id": campaign_id,
            "pm_position_campaign_id": campaign_id,
            "opportunity_position_campaign_id": campaign_id,
            "expected_edge_baseline_score": 0.40,
            "expected_edge_baseline_business_date": "2026-08-26",
            "expected_edge_improvement_state": "IMPROVING",
            "incremental_investment_value_state": "POSITIVE",
            "opportunity_cost_status": "PASS",
            "no_loss_averaging_status": "PASS",
            "quality_action": quality_action,
            "broker_eligibility_status": "PASS",
            "corporate_action_status": "NO_EVENT",
            "safety_restriction_status": "PASS",
            "liquidity_capacity_status": "NORMAL",
            "source_pm_reason_codes": ["strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"],
        }
    )
    if quality_adjustment is not None:
        row["quality_allocation_adjustment"] = quality_adjustment
    return row


def _phase32_s_add_evidence(row: dict[str, object]) -> dict[str, object]:
    from ai_fund_lab_v2.strategy.add_investment_evidence import resolve_add_investment_evidence

    return resolve_add_investment_evidence(row=row, members=[row], business_date=BUSINESS_DATE)


def _phase32_s_bridge(row: dict[str, object], *, risk_pacing: str) -> dict[str, object]:
    return _resolve_canonical_add_allocation_bridge(
        row=row,
        selected=True,
        candidate_target_weight=float(row["target_weight"]) - float(row["current_weight"]),
        single_name_cap=float(row.get("single_name_cap") or 0.25),
        target_gross_exposure=0.80,
        members=[row],
        business_date=BUSINESS_DATE,
        risk_pacing_evidence=_phase32_s_risk(risk_pacing),
    )


def _add(
    symbol: str,
    *,
    requested_weight: float,
    current_quantity: int,
    current_weight: float,
    priority: int,
    cap: float = 0.25,
) -> dict[str, object]:
    score = 1.0 - priority / 100.0
    return {
        "security_code": symbol,
        "symbol": symbol,
        "business_date": BUSINESS_DATE,
        "current_position": True,
        "membership_intent": "RETAIN",
        "pm_action": "ADD",
        "construction_priority": priority,
        "opportunity_buy_rank": priority,
        "runtime_opportunity_score": score,
        "confidence": score,
        "target_weight": current_weight + requested_weight,
        "requested_incremental_weight": requested_weight,
        "accepted_incremental_weight": requested_weight,
        "add_allocation_eligibility_status": "PASS",
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "entry_admission_action": "ADD_REDUCED_ONLY",
        "entry_admission_state": "CONTINUATION_WITH_CAUTION",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "canonical_opportunity_quality_class": "COMPARABLE_MARGINAL",
        "opportunity_quality_class": "COMPARABLE_MARGINAL",
        "quality_status": "PASS",
        "current_quantity": current_quantity,
        "current_weight": current_weight,
        "reference_price": 100.0,
        "portfolio_value": 1_000_000.0,
        "trading_unit": 100,
        "single_name_cap": cap,
        "safety_hard_cap": cap,
        "marginal_capital_value_authority": {
            "canonical_marginal_capital_priority_index": priority,
            "marginal_capital_value_class": "ELIGIBLE_COMPARABLE",
            "canonical_opportunity_quality_class": "COMPARABLE_MARGINAL",
            "future_information_used": False,
        },
    }


def _new(symbol: str, *, weight: float, priority: int) -> dict[str, object]:
    score = 1.0 - priority / 100.0
    return {
        "security_code": symbol,
        "symbol": symbol,
        "business_date": BUSINESS_DATE,
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "construction_priority": priority,
        "opportunity_buy_rank": priority,
        "runtime_opportunity_score": score,
        "confidence": score,
        "target_weight": weight,
        "accepted_buy_new_weight": weight,
        "canonical_opportunity_quality_class": "COMPARABLE_MARGINAL",
        "opportunity_quality_class": "COMPARABLE_MARGINAL",
        "quality_status": "PASS",
    }


def _add_competitor_with_investment_evidence(symbol: str, *, priority: int) -> dict[str, object]:
    return {
        "symbol": symbol,
        "canonical_opportunity_quality_class": "COMPARABLE_MARGINAL",
        "canonical_add_competitor": {
            "add_investment_evidence": {
                "incremental_investment_value": {"state": "POSITIVE", "status": "PASS"},
                "opportunity_cost": {"status": "PASS"},
            },
            "incremental_investment_value_state": "POSITIVE",
            "opportunity_cost_status": "PASS",
        },
        "construction_priority": priority,
    }


def _ps_add_row() -> dict[str, object]:
    return {
        **_add("76470", requested_weight=0.01, current_quantity=400, current_weight=0.04, priority=1),
        "target_weight": 0.05,
        "target_weight_authority": {
            "authority_type": "TARGET_WEIGHT_AUTHORITY",
            "business_date": BUSINESS_DATE,
            "PIT_status": "PASS",
            "single_name_weight_cap": 0.25,
            "target_gross_exposure": 0.8,
            "resolved_target_member_count": 1,
            "source_artifact_paths": [],
            "source_artifact_hashes": [],
        },
        "target_weight_resolution": {
            "status": "PASS",
            "reason": "lot_aware_final_reallocation",
            "resolved_weight": 0.05,
            "lot_aware_final_reallocation": {
                "authority_type": "PORTFOLIO_CONSTRUCTION_LOT_AWARE_FINAL_REALLOCATION",
                "canonical_add_marginal_capital_competition_authority": {
                    "schema_version": "canonical_add_marginal_capital_competition_authority.v1",
                    "authority_status": "AUTHORITATIVE_STAGED_PC_BINDING",
                    "reason": "G115_STAGED_ADD_MARGINAL_ONE_INCREMENT_AUTHORIZED",
                },
                "phase29_l19_lot_resolution": {
                    "semantic_type": "BUY_ADD",
                    "safety_hard_cap": 0.25,
                    "safety_hard_cap_weight": 0.25,
                    "safety_hard_cap_preserved": True,
                    "post_trade_weight": 0.05,
                    "final_allocated_quantity": 100,
                    "one_lot_quantity": 100,
                },
                "pc_positive_executable_quantity_authority": {
                    "status": "PASS",
                    "semantic_type": "BUY_ADD",
                    "final_allocated_quantity": 100,
                    "ps_must_consume_canonical_quantity": True,
                    "future_information_used": False,
                    "historical_outcome_used": False,
                },
            },
        },
        "phase29_l19_lot_resolution": {
            "semantic_type": "BUY_ADD",
            "safety_hard_cap": 0.25,
            "safety_hard_cap_weight": 0.25,
            "safety_hard_cap_preserved": True,
            "post_trade_weight": 0.05,
            "final_allocated_quantity": 100,
            "one_lot_quantity": 100,
            "pc_positive_executable_quantity_authority": {
                "status": "PASS",
                "semantic_type": "BUY_ADD",
                "final_allocated_quantity": 100,
                "ps_must_consume_canonical_quantity": True,
                "future_information_used": False,
                "historical_outcome_used": False,
            },
        },
        "semantic_buy_type": "BUY_ADD",
        "reference_price_authority": {
            "authority_type": "REFERENCE_PRICE_AUTHORITY",
            "status": "PASS",
            "reference_price": 100.0,
            "source": "test",
            "business_date": BUSINESS_DATE,
            "PIT_status": "PASS",
            "source_field": "reference_price",
            "future_information_used": False,
        },
    }


def _summary(*, rows: list[dict[str, object]] | None = None, summary: dict[str, object] | None = None):
    return position_sizing.PositionSizingSourceSummary(
        source_ref="test",
        source_hash="sha256:test",
        status="PASS",
        business_date=BUSINESS_DATE,
        feature_date=BUSINESS_DATE,
        rows=rows or [],
        summary=summary or {},
    )
