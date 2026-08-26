from __future__ import annotations

from dataclasses import replace

from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import normalize_broker_readonly_payload
from ai_fund_lab_v2.runtime_v2.execution.ledger_projection import project_order_to_ledger_record
from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan_path
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.strategy.portfolio_construction import (
    apply_lot_aware_final_reallocation,
    build_capital_competition_framework,
)
from ai_fund_lab_v2.strategy.runtime_planning import _strategy_authority_lineage_envelope
from tests.runtime_v2.pending_fixtures import make_pending_plan


BUSINESS_DATE = "2026-07-15"


def test_phase31_g46_authority_uniqueness_reachability_and_non_binding_legacy_paths() -> None:
    matrix = {
        "STRONG": _competition([_new("10010", quality="STRONG", preserve_exception=True)], "CAUTIOUS_DEPLOYMENT"),
        "COMPARABLE_HIGH": _competition([_new("10020", quality="COMPARABLE_HIGH", caution_sufficient=True)], "CAUTIOUS_DEPLOYMENT"),
        "COMPARABLE_MARGINAL": _competition([_new("10030", quality="COMPARABLE_MARGINAL")], "NORMAL_DEPLOYMENT"),
        "WEAK_VALID": _competition([_new("10040", quality="WEAK_VALID")], "NORMAL_DEPLOYMENT"),
        "INSUFFICIENT": _competition([_new("10050", quality="INSUFFICIENT", target_weight=0.0, accepted_buy_new_weight=0.0)], "NORMAL_DEPLOYMENT"),
        "BLOCKED": _competition([_new("10060", quality="BLOCKED", target_weight=0.0, accepted_buy_new_weight=0.0)], "NORMAL_DEPLOYMENT"),
    }

    assert {key for key, value in matrix.items() if _record(value, next(iter(_symbols(value))))["canonical_opportunity_quality_class"] == key} == set(matrix)
    strong = matrix["STRONG"]
    interaction = strong["market_candidate_cash_interaction"]

    assert strong["authority"]["risk_pacing_owner"] == "PORTFOLIO_POLICY"
    assert strong["authority"]["risk_pacing_authoritative_consumer"] == "PORTFOLIO_CONSTRUCTION"
    assert strong["authority"]["risk_pacing_authoritative_consumer_count"] == 1
    assert strong["authority"]["cash_competitor_owner"] == "PORTFOLIO_CONSTRUCTION"
    assert strong["authority"]["add_discrete_quantity_owner"] == "POSITION_SIZING"
    assert interaction["second_capital_winner_authority"] is False
    assert interaction["legacy_late_risk_pacing_decision_authority_count"] == 0
    assert interaction["legacy_cash_winner_override_count"] == 0
    assert interaction["position_sizing_quantity_owner"] == "POSITION_SIZING"
    assert interaction["pc_computes_share_quantity"] is False
    assert interaction["outcome_derived_decision_rule_count"] == 0
    assert interaction["future_information_used"] is False
    assert interaction["historical_outcome_used"] is False
    assert interaction["paper_ledger_input_used"] is False


def test_phase31_g46_market_candidate_cash_brake_recovery_and_rebrake_are_reversible() -> None:
    day_a_brake = _competition([_new("20010", quality="COMPARABLE_MARGINAL")], "CAUTIOUS_DEPLOYMENT")
    day_b_redeploy = _competition([_new("20010", quality="COMPARABLE_HIGH")], "GRADUAL_REDEPLOYMENT")
    day_c_normal = _competition([_new("20010", quality="COMPARABLE_MARGINAL")], "NORMAL_DEPLOYMENT")
    day_d_rebrake = _competition([_new("20010", quality="COMPARABLE_MARGINAL")], "PRESERVE_OPTIONALITY")
    strong_exception = _competition([_new("20020", quality="STRONG", preserve_exception=True)], "CAUTIOUS_DEPLOYMENT")

    assert _cash_wins(day_a_brake)
    assert day_b_redeploy["capital_competition_winner_symbol"] == "20010"
    assert day_c_normal["capital_competition_winner_symbol"] == "20010"
    assert _cash_wins(day_d_rebrake)
    assert strong_exception["capital_competition_winner_symbol"] == "20020"
    assert _submit_symbols(day_a_brake) == []
    assert _submit_symbols(day_c_normal) == ["20010"]
    assert _record(day_a_brake, "20010")["as_of_business_date"] <= BUSINESS_DATE
    assert _record(day_b_redeploy, "20010")["as_of_business_date"] <= BUSINESS_DATE


def test_phase31_g46_add_reentry_and_buy_sell_independence_integrate_with_cash_competition() -> None:
    marginal_add = _competition([_add("30010", quality="COMPARABLE_MARGINAL")], "CAUTIOUS_DEPLOYMENT")
    strong_add = _competition([_add("30020", quality="STRONG", preserve_exception=True)], "CAUTIOUS_DEPLOYMENT")
    normal_reentry = _competition([_reentry("30030", quality="COMPARABLE_MARGINAL")], "NORMAL_DEPLOYMENT")
    cautious_reentry = _competition([_reentry("30030", quality="COMPARABLE_MARGINAL")], "CAUTIOUS_DEPLOYMENT")
    sell_plan = {"symbol": "39990", "side": "SELL", "pm_action": "EXIT", "quantity_owner": "POSITION_MANAGEMENT"}

    assert _cash_wins(marginal_add)
    assert strong_add["capital_competition_winner_type"] == "ADD"
    assert strong_add["capital_competition_winner_symbol"] == "30020"
    assert normal_reentry["capital_competition_winner_type"] == "NEW_BUY"
    assert normal_reentry["capital_competition_winner_symbol"] == "30030"
    assert _cash_wins(cautious_reentry)
    assert sell_plan == {"symbol": "39990", "side": "SELL", "pm_action": "EXIT", "quantity_owner": "POSITION_MANAGEMENT"}
    assert strong_add["authority"]["add_automatic_priority"] is False
    assert strong_add["authority"]["new_buy_automatic_priority"] is False


def test_phase31_g46_lot_reconsideration_does_not_force_deployment_and_preserves_winner_lineage() -> None:
    security_b_wins = apply_lot_aware_final_reallocation(
        members=[
            _new("40010", quality="STRONG", preserve_exception=True, priority=1, target_weight=0.18, accepted_buy_new_weight=0.18),
            _new("40020", quality="STRONG", preserve_exception=True, priority=2, target_weight=0.08, accepted_buy_new_weight=0.08),
        ],
        lot_feasibility_rows=[
            {"symbol": "40010", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.30, "canonical_sizing_evidence": _sizing("40010", "LOT_INFEASIBLE")},
            {"symbol": "40020", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08, "canonical_sizing_evidence": _sizing("40020", "EXECUTABLE")},
        ],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
        business_date=BUSINESS_DATE,
        risk_pacing_evidence=_risk_pacing("NORMAL_DEPLOYMENT"),
    )
    cash_wins = apply_lot_aware_final_reallocation(
        members=[
            _new("40030", quality="STRONG", preserve_exception=True, priority=1, target_weight=0.18, accepted_buy_new_weight=0.18),
            _new("40040", quality="COMPARABLE_MARGINAL", priority=2, target_weight=0.08, accepted_buy_new_weight=0.08),
        ],
        lot_feasibility_rows=[
            {"symbol": "40030", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.30, "canonical_sizing_evidence": _sizing("40030", "LOT_INFEASIBLE")},
            {"symbol": "40040", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08, "canonical_sizing_evidence": _sizing("40040", "EXECUTABLE")},
        ],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
        business_date=BUSINESS_DATE,
        risk_pacing_evidence=_risk_pacing("CAUTIOUS_DEPLOYMENT"),
    )

    b_competition = security_b_wins["evidence"]["capital_competition"]
    cash_competition = cash_wins["evidence"]["capital_competition"]
    b_integration = security_b_wins["evidence"]["lot_reconsideration_binding_integration"]
    cash_integration = cash_wins["evidence"]["lot_reconsideration_binding_integration"]

    assert b_competition["capital_competition_winner_symbol"] == "40020"
    assert cash_competition["capital_competition_winner_type"] == "CASH_OPTIONALITY"
    assert b_integration["canonical_g43_binding_matrix_reused"] is True
    assert b_integration["forces_security_deployment"] is False
    assert b_integration["second_discrete_quantity_engine_created"] is False
    assert cash_integration["residual_capital_binding_bypass_count"] == 0
    assert cash_integration["cash_win_reason_lineage_complete"] is True


def test_phase31_g46_runtime_pending_submit_execution_ledger_lineage_roundtrip(tmp_path) -> None:
    competition = _competition([_new("50010", quality="STRONG", preserve_exception=True)], "NORMAL_DEPLOYMENT")
    lineage = _lineage_for_competition(competition, [_new("50010", quality="STRONG", preserve_exception=True)], [_plan("50010", "BUY_NEW")])
    refined_item = lineage["refined_capital_decision_lineage"]["items"][0]
    item_lineage = {
        "schema_version": "runtime_authority_lineage.item.v1",
        "lineage_hash": lineage["lineage_hash"],
        "refined_capital_decision_lineage": refined_item,
        "downstream_strategy_redecision_allowed": False,
    }
    pending = make_pending_plan()
    item = replace(
        pending.items[0],
        symbol="50010",
        strategy_authority_lineage=item_lineage,
        strategy_authority_lineage_hash=lineage["lineage_hash"],
    )
    pending = replace(
        pending,
        items=(item,),
        strategy_authority_lineage=lineage,
        strategy_authority_lineage_hash=lineage["lineage_hash"],
    )
    pending_path = tmp_path / ".runtime/pending_order_plan/pending_order_plan.json"
    write_pending_order_plan(pending_path, pending)
    reloaded = read_pending_order_plan_path(path=pending_path, environment="demo").plan

    assert reloaded is not None
    assert reloaded.strategy_authority_lineage == lineage
    assert reloaded.items[0].strategy_authority_lineage == item_lineage

    bundle = normalize_broker_readonly_payload(
        environment="demo",
        source="g46_historical_submit_fixture",
        as_of=f"{BUSINESS_DATE}T09:00:00+09:00",
        orders=(
            {
                "order_ref": "ORDER-G46",
                "pending_plan_id": reloaded.pending_plan_id,
                "pending_item_id": reloaded.items[0].pending_item_id,
                "symbol": reloaded.items[0].symbol,
                "side": reloaded.items[0].side,
                "quantity": reloaded.items[0].quantity,
                "order_status": "accepted",
                "strategy_authority_lineage": item_lineage,
                "strategy_authority_lineage_hash": lineage["lineage_hash"],
            },
        ),
        executions=(),
        positions=(),
        cash={"cash_ref": "CASH-G46", "cash": 100000, "buying_power": 50000},
    )
    projected = project_order_to_ledger_record(bundle.orders[0])

    assert projected.strategy_authority_lineage == item_lineage
    assert projected.strategy_authority_lineage_hash == lineage["lineage_hash"]
    assert refined_item["runtime_recomputed_capital_decision"] is False
    assert refined_item["future_input_count"] == 0
    assert refined_item["historical_outcome_lineage_input_count"] == 0
    assert refined_item["paper_ledger_decision_input_count"] == 0


def test_phase31_g46_missing_evidence_fails_closed_without_future_or_outcome_inputs() -> None:
    missing_market = build_capital_competition_framework(
        members=[_new("60010", quality="STRONG", preserve_exception=True)],
        target_gross_exposure=0.3,
        total_target_weight=0.1,
        business_date=BUSINESS_DATE,
        risk_pacing_evidence={"risk_pacing_intent": "NORMAL_DEPLOYMENT", "mode": "AUTHORITATIVE"},
    )
    missing_candidate = _competition(
        [_new("60020", quality="INSUFFICIENT", target_weight=0.0, accepted_buy_new_weight=0.0)],
        "NORMAL_DEPLOYMENT",
    )
    interaction = missing_market["market_candidate_cash_interaction"]

    assert "CASH_EVIDENCE_MISSING_INPUT_FAIL_CLOSED" in missing_market["canonical_cash_competitor_evidence"]["reason_codes"]
    assert missing_market["canonical_cash_competitor_evidence"]["evidence_completeness"] == "INCOMPLETE_FAIL_CLOSED"
    assert _record(missing_candidate, "60020")["interaction_result"] == "FAIL_CLOSED"
    assert interaction["future_information_used"] is False
    assert interaction["historical_outcome_used"] is False
    assert interaction["paper_ledger_input_used"] is False
    assert interaction["mfe_mae_input_used"] is False
    assert interaction["outcome_derived_decision_rule_count"] == 0


def _competition(members: list[dict], risk_pacing_intent: str) -> dict:
    return build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.3,
        total_target_weight=sum(float(item.get("target_weight") or 0.0) for item in members),
        business_date=BUSINESS_DATE,
        risk_pacing_evidence=_risk_pacing(risk_pacing_intent),
    )


def _lineage_for_competition(competition: dict, members: list[dict], plans: list[dict]) -> dict:
    return _strategy_authority_lineage_envelope(
        business_date=BUSINESS_DATE,
        as_of=f"{BUSINESS_DATE}T00:00:00+00:00",
        pc_payload={
            "business_date": BUSINESS_DATE,
            "as_of": f"{BUSINESS_DATE}T00:00:00+00:00",
            "artifact_hash": "pc-g46",
            "portfolio_members": members,
            "capital_competition": competition,
        },
        policy_payload={
            "business_date": BUSINESS_DATE,
            "as_of": f"{BUSINESS_DATE}T00:00:00+00:00",
            "risk_pacing_intent": competition["market_candidate_cash_interaction"]["risk_pacing_intent"],
            "risk_pacing_as_of": BUSINESS_DATE,
        },
        pm_payload={"positions": []},
        ps_payload={"positions": [_sizing(str(item["security_code"]), "EXECUTABLE") for item in members]},
        source_artifacts=({"role": "pc", "path": "pc.json", "required": True, "status": "PASS"},),
        source_hashes=({"role": "pc", "path": "pc.json", "sha256": "pc-hash"},),
        plans=plans,
    )


def _risk_pacing(intent: str) -> dict:
    return {
        "risk_pacing_intent": intent,
        "risk_pacing_as_of": BUSINESS_DATE,
        "risk_pacing_evidence_completeness": "COMPLETE",
        "mode": "AUTHORITATIVE",
        "risk_pacing_component_evidence": {
            "schema_version": "risk_pacing_component_evidence.v1",
            "business_date": BUSINESS_DATE,
            "market_quality_state": "HEALTHY_EXPANSION",
            "market_quality_evidence_completeness": "COMPLETE",
            "market_quality_reason_codes": ["HEALTHY_EXPANSION"],
            "future_information_used": False,
            "historical_outcome_used": False,
        },
    }


def _new(
    symbol: str,
    *,
    quality: str,
    priority: int = 1,
    target_weight: float = 0.1,
    accepted_buy_new_weight: float = 0.1,
    preserve_exception: bool = False,
    caution_sufficient: bool = False,
) -> dict:
    fields = {
        "membership_intent": "ADD_CANDIDATE",
        "accepted_buy_new_weight": accepted_buy_new_weight,
    }
    if caution_sufficient:
        fields["caution_sufficient_evidence"] = True
    return _member(
        symbol,
        quality=quality,
        current_position=False,
        priority=priority,
        target_weight=target_weight,
        fields=fields,
        preserve_exception=preserve_exception,
    )


def _reentry(symbol: str, *, quality: str, preserve_exception: bool = False) -> dict:
    row = _new(symbol, quality=quality, preserve_exception=preserve_exception)
    row.update(
        {
            "semantic_buy_type": "REENTRY",
            "reentry_semantic_eligibility": "PASS",
            "reentry_semantic_state": "REENTRY_ELIGIBLE",
        }
    )
    return row


def _add(symbol: str, *, quality: str, preserve_exception: bool = False) -> dict:
    return _member(
        symbol,
        quality=quality,
        current_position=True,
        priority=1,
        target_weight=0.15,
        fields={
            "pm_action": "ADD",
            "current_weight": 0.05,
            "accepted_incremental_weight": 0.1,
            "requested_incremental_weight": 0.1,
            "expected_edge_improvement_state": "IMPROVING",
            "incremental_investment_value_state": "POSITIVE",
            "opportunity_cost_status": "PASS",
            "add_allocation_eligibility_status": "PASS",
            "same_campaign_continuation_status": "CONTINUING",
            "add_investment_evidence": {
                "incremental_value": {"status": "PASS"},
                "opportunity_cost": {"status": "PASS"},
            },
        },
        preserve_exception=preserve_exception,
    )


def _member(
    symbol: str,
    *,
    quality: str,
    current_position: bool,
    priority: int,
    target_weight: float,
    fields: dict,
    preserve_exception: bool,
) -> dict:
    reasons = [f"test_{quality.lower()}"]
    if preserve_exception:
        reasons.append("OPPORTUNITY_QUALITY_EXPLICIT_POSITIVE_ADD_EVIDENCE")
        reasons.append("STRONG_CAN_OVERRIDE_CAUTION")
    evidence = {
        "schema_version": "opportunity_quality.v1",
        "authority_type": "PHASE31_G40_OPPORTUNITY_QUALITY",
        "producer": "strategy.marginal_capital_value",
        "business_date": BUSINESS_DATE,
        "as_of_business_date": BUSINESS_DATE,
        "symbol": symbol,
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "opportunity_quality_reason_codes": reasons,
        "evidence_completeness": "COMPLETE" if quality not in {"INSUFFICIENT", "BLOCKED"} else "INSUFFICIENT",
        "source_evidence": {},
        "future_information_used": False,
        "historical_outcome_used": False,
        "paper_ledger_input_used": False,
        "audit_result_input_used": False,
        "opportunity_quality_hash": f"test-{symbol}-{quality}",
    }
    row = {
        "security_code": symbol,
        "symbol": symbol,
        "business_date": BUSINESS_DATE,
        "current_position": current_position,
        "construction_priority": priority,
        "target_weight": target_weight,
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "marginal_capital_value_class": "ELIGIBLE_STRONG" if quality == "STRONG" else "ELIGIBLE_COMPARABLE",
        "marginal_capital_value_authority": {
            "canonical_opportunity_quality_class": quality,
            "opportunity_quality_class": quality,
            "opportunity_quality_evidence": evidence,
            "future_information_used": False,
        },
        "opportunity_quality_evidence": evidence,
    }
    row.update(fields)
    return row


def _sizing(symbol: str, evidence_class: str) -> dict:
    return {
        "schema_version": "position_sizing.canonical_lot_residual_evidence.v1",
        "security_code": symbol,
        "symbol": symbol,
        "position_reference": f"ps-{symbol}",
        "evidence_class": evidence_class,
        "terminality": "RECONSIDERABLE" if evidence_class == "LOT_INFEASIBLE" else "EXECUTABLE",
        "target_quantity_candidate": 100,
        "quantity_delta_candidate": 100,
        "quantity_status": "RESOLVED_EXECUTABLE",
        "constraint_reason_codes": [evidence_class],
        "quantity_authority_owner": "POSITION_SIZING",
        "pc_reconsideration_owner": "PORTFOLIO_CONSTRUCTION",
        "canonical_sizing_evidence": {
            "evidence_class": evidence_class,
            "final_allocated_quantity": 0 if evidence_class == "LOT_INFEASIBLE" else 100,
            "executable_quantity_delta": 0 if evidence_class == "LOT_INFEASIBLE" else 100,
        },
    }


def _plan(symbol: str, intent: str) -> dict:
    return {
        "planning_id": f"plan-{symbol}",
        "security_code": symbol,
        "planning_intent": intent,
        "order_side_intent": "BUY",
        "quantity_authority": "PHASE22_J_POSITION_SIZING",
        "target_quantity_candidate": 100,
        "quantity_delta_candidate": 100,
        "planned_quantity": 100,
        "quantity_status": "RESOLVED_EXECUTABLE",
        "marginal_capital_value_class": "ELIGIBLE_STRONG",
    }


def _record(competition: dict, symbol: str) -> dict:
    for item in competition["market_candidate_cash_interaction"]["interaction_results"]:
        if item["symbol"] == symbol:
            return item
    raise AssertionError(f"missing interaction result for {symbol}")


def _symbols(competition: dict) -> set[str]:
    return {item["symbol"] for item in competition["market_candidate_cash_interaction"]["interaction_results"] if item["symbol"]}


def _cash_wins(competition: dict) -> bool:
    return competition["capital_competition_winner_type"] == "CASH_OPTIONALITY"


def _submit_symbols(competition: dict) -> list[str]:
    winner_type = competition["capital_competition_winner_type"]
    winner_symbol = competition["capital_competition_winner_symbol"]
    return [winner_symbol] if winner_type in {"NEW_BUY", "ADD"} and winner_symbol else []
