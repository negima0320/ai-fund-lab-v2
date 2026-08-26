from __future__ import annotations

from dataclasses import replace

from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalDecision, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.approval.policy import (
    build_approval_artifact,
    build_approval_request,
    build_approved_order_conditions,
)
from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import normalize_broker_readonly_payload
from ai_fund_lab_v2.runtime_v2.execution.ledger_projection import project_order_to_ledger_record
from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan_path
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.submit.guards import build_runtime_v2_submit_command
from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework
from ai_fund_lab_v2.strategy.runtime_planning import _attach_strategy_authority_lineage, _strategy_authority_lineage_envelope
from tests.runtime_v2.pending_fixtures import make_pending_plan


BUSINESS_DATE = "2026-07-15"


def test_phase31_g45_buy_new_refined_lineage_runtime_pending_reload() -> None:
    lineage = _runtime_authority_lineage([_new("11110", quality="STRONG")], "NORMAL_DEPLOYMENT")
    attached = _attach_strategy_authority_lineage([_plan("11110", "BUY_NEW")], lineage)
    item_lineage = attached[0]["strategy_authority_lineage"]["refined_capital_decision_lineage"]

    assert lineage["refined_capital_decision_lineage"]["schema_version"] == "refined_capital_decision_lineage.v1"
    assert lineage["refined_capital_decision_lineage"]["lineage_status"] == "AVAILABLE"
    assert lineage["full_upstream_artifact_duplicated"] is False
    assert lineage["downstream_capital_winner_recomputation_count"] == 0
    assert item_lineage["capital_competition_winner_type"] == "NEW_BUY"
    assert item_lineage["capital_competition_winner_symbol"] == "11110"
    assert item_lineage["security_winner_quantity_source"] == "POSITION_SIZING"


def test_phase31_g45_cash_winner_keeps_no_downstream_security_substitution() -> None:
    lineage = _runtime_authority_lineage([_new("22220", quality="COMPARABLE_MARGINAL")], "PRESERVE_OPTIONALITY")
    refined = lineage["refined_capital_decision_lineage"]

    assert refined["capital_competition_winner_type"] == "CASH_OPTIONALITY"
    assert refined["capital_competition_winner_symbol"] == ""
    assert refined["cash_winner_downstream_security_substitution_count"] == 0
    assert lineage["downstream_capital_reclassification_count"] == 0


def test_phase31_g45_add_reentry_lot_and_legacy_unavailable_are_explicit() -> None:
    add_lineage = _runtime_authority_lineage([_add("33330", quality="STRONG")], "CAUTIOUS_DEPLOYMENT")
    add_item = add_lineage["refined_capital_decision_lineage"]["items"][0]
    assert add_item["planning_intent"] == "BUY_ADD"
    assert add_item["add_binding"]["schema_version"] == "portfolio_construction.add_capital_competitor.v1"

    reentry_member = _new("44440", quality="STRONG")
    reentry_member["reentry_semantic_eligibility"] = "PASS"
    reentry_lineage = _runtime_authority_lineage([reentry_member], "NORMAL_DEPLOYMENT")
    reentry_item = reentry_lineage["refined_capital_decision_lineage"]["items"][0]
    assert reentry_item["reentry_binding"]["reentry_semantic_eligibility"] == "PASS"

    legacy_lineage = _strategy_authority_lineage_envelope(
        business_date=BUSINESS_DATE,
        as_of=f"{BUSINESS_DATE}T00:00:00+00:00",
        pc_payload={"portfolio_members": [_new("55550", quality="STRONG")]},
        policy_payload={},
        pm_payload={},
        ps_payload={"positions": [_sizing("55550")]},
        source_artifacts=(),
        source_hashes=(),
        plans=[_plan("55550", "BUY_NEW")],
    )
    assert legacy_lineage["refined_capital_decision_lineage"]["lineage_status"] == "UNAVAILABLE_LEGACY_RECORD"
    assert legacy_lineage["refined_capital_decision_lineage"]["missing_refined_lineage_not_reconstructed_from_later_state"] is True


def test_phase31_g45_pending_submit_snapshot_and_projected_ledger_preserve_refined_lineage(tmp_path) -> None:
    lineage = _runtime_authority_lineage([_new("7203", quality="STRONG")], "NORMAL_DEPLOYMENT")
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
        strategy_authority_lineage=item_lineage,
        strategy_authority_lineage_hash=lineage["lineage_hash"],
    )
    pending = replace(
        pending,
        items=(item,),
        strategy_authority_lineage=lineage,
        strategy_authority_lineage_hash=lineage["lineage_hash"],
    )
    path = tmp_path / ".runtime/pending_order_plan/pending_order_plan.json"
    write_pending_order_plan(path, pending)
    reloaded = read_pending_order_plan_path(path=path, environment="demo").plan

    assert reloaded is not None
    assert reloaded.strategy_authority_lineage == lineage
    assert reloaded.items[0].strategy_authority_lineage == item_lineage

    approval_request = build_approval_request(
        pending_plan=reloaded,
        business_date=BUSINESS_DATE,
        expires_at=f"{BUSINESS_DATE}T15:00:00+09:00",
    )
    approval = build_approval_artifact(
        request=approval_request,
        decision=ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            approved_item_ids=("item-1",),
            rejected_item_ids=(),
            reason="phase31_g45_fixture",
            operator="phase31_g45",
            decided_at=f"{BUSINESS_DATE}T08:45:00+09:00",
            approved_order_conditions=build_approved_order_conditions(
                pending_items=reloaded.items,
                target_session_date=reloaded.target_session_date,
            ),
        ),
    )
    command = build_runtime_v2_submit_command(
        pending_plan=reloaded,
        approval_artifact=approval,
        approved_item_id="item-1",
        live_order_allowed=False,
    )

    assert command.strategy_authority_lineage == item_lineage
    assert command.strategy_authority_lineage_hash == lineage["lineage_hash"]

    bundle = normalize_broker_readonly_payload(
        environment="demo",
        source="historical_submit_fixture",
        as_of=f"{BUSINESS_DATE}T09:00:00+09:00",
        orders=(
            {
                "order_ref": "ORDER-G45",
                "pending_plan_id": command.pending_plan_id,
                "pending_item_id": command.pending_item_id,
                "symbol": command.symbol,
                "side": command.side,
                "quantity": command.quantity,
                "order_status": "accepted",
                "strategy_authority_lineage": command.strategy_authority_lineage,
                "strategy_authority_lineage_hash": command.strategy_authority_lineage_hash,
            },
        ),
        executions=(),
        positions=(),
        cash={"cash_ref": "CASH-G45", "cash": 100000, "buying_power": 50000},
    )
    projected = project_order_to_ledger_record(bundle.orders[0])

    assert bundle.orders[0].strategy_authority_lineage == item_lineage
    assert projected.strategy_authority_lineage == item_lineage
    assert projected.strategy_authority_lineage["refined_capital_decision_lineage"]["runtime_recomputed_capital_decision"] is False


def _runtime_authority_lineage(members: list[dict], risk_pacing_intent: str) -> dict:
    competition = build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.3,
        total_target_weight=sum(float(item.get("target_weight") or 0.0) for item in members),
        business_date=BUSINESS_DATE,
        risk_pacing_evidence=_risk_pacing(risk_pacing_intent),
    )
    pc_payload = {
        "business_date": BUSINESS_DATE,
        "as_of": f"{BUSINESS_DATE}T00:00:00+00:00",
        "artifact_hash": "pc-g45",
        "portfolio_members": members,
        "capital_competition": competition,
    }
    plans = [_plan(str(item["security_code"]), "BUY_ADD" if item.get("current_position") else "BUY_NEW") for item in members]
    return _strategy_authority_lineage_envelope(
        business_date=BUSINESS_DATE,
        as_of=f"{BUSINESS_DATE}T00:00:00+00:00",
        pc_payload=pc_payload,
        policy_payload={
            "business_date": BUSINESS_DATE,
            "as_of": f"{BUSINESS_DATE}T00:00:00+00:00",
            "risk_pacing_intent": risk_pacing_intent,
            "risk_pacing_as_of": BUSINESS_DATE,
        },
        pm_payload={"positions": []},
        ps_payload={"positions": [_sizing(str(item["security_code"])) for item in members]},
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
        },
    }


def _new(symbol: str, *, quality: str) -> dict:
    return {
        "security_code": symbol,
        "symbol": symbol,
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "target_weight": 0.1,
        "accepted_buy_new_weight": 0.1,
        "construction_priority": 1,
        "marginal_capital_value_class": "ELIGIBLE_STRONG" if quality == "STRONG" else "ELIGIBLE_COMPARABLE",
        "marginal_capital_value_authority": _quality(quality),
        "opportunity_quality_evidence": _quality(quality),
        "canonical_opportunity_quality_class": quality,
    }


def _add(symbol: str, *, quality: str) -> dict:
    member = _new(symbol, quality=quality)
    member.update(
        {
            "current_position": True,
            "membership_intent": "RETAIN",
            "pm_action": "ADD",
            "current_weight": 0.05,
            "target_weight": 0.13,
            "accepted_incremental_weight": 0.08,
            "requested_incremental_weight": 0.08,
            "add_allocation_eligibility_status": "PASS",
            "add_investment_evidence": {
                "incremental_value": {"status": "PASS"},
                "opportunity_cost": {"status": "PASS"},
            },
        }
    )
    return member


def _quality(quality: str) -> dict:
    return {
        "schema_version": "opportunity_quality.v1",
        "authority_type": "PHASE31_G40_OPPORTUNITY_QUALITY",
        "business_date": BUSINESS_DATE,
        "canonical_opportunity_quality_class": quality,
        "opportunity_quality_class": quality,
        "opportunity_quality_reason_codes": [f"{quality.lower()}_fixture"],
        "opportunity_quality_hash": f"oq-{quality}",
    }


def _sizing(symbol: str) -> dict:
    return {
        "security_code": symbol,
        "position_reference": f"ps-{symbol}",
        "target_quantity_candidate": 100,
        "quantity_delta_candidate": 100,
        "quantity_status": "RESOLVED_EXECUTABLE",
        "canonical_sizing_evidence": {
            "evidence_class": "EXECUTABLE",
            "final_allocated_quantity": 100,
            "executable_quantity_delta": 100,
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
