from __future__ import annotations

from ai_fund_lab_v2.runtime_v2.observability.cross_authority_evidence import (
    EvidenceSource,
    build_cross_authority_evidence,
    build_mode_parity_matrix,
    build_negative_assertion_aggregate,
)


BUSINESS_DATE = "2026-07-09"


def test_phase26_step9_full_buy_decision_trace_links_all_authorities() -> None:
    evidence = _build(action="BUY", submit_status="PASS")

    assert evidence["validation"]["status"] == "PASS"
    names = {row["authority_name"] for row in evidence["authority_evidence"]}
    assert {
        "market_context",
        "capital",
        "position_count",
        "cash_exposure",
        "position_sizing",
        "planning",
        "pending_approval",
        "submit",
        "current",
        "projection",
        "accepted_generation",
        "temporal",
        "safety",
        "corporate_action",
    }.issubset(names)
    assert all(row["fallback_used"] is False for row in evidence["authority_evidence"])
    assert evidence["decision_trace"]["buy_chain"][0]["authority_name"] == "market_context"
    assert evidence["design"]["read_only"] is True
    assert evidence["design"]["evidence_aggregate_is_authority"] is False


def test_phase26_step9_full_sell_trace_does_not_apply_buy_generation_requirement() -> None:
    evidence = _build(action="SELL", submit_status="PASS", generation_status="NOT_REQUIRED")

    assert evidence["buy_sell_independence"]["sell_submit_status"] == "PASS"
    generation = next(row for row in evidence["authority_evidence"] if row["authority_name"] == "accepted_generation")
    assert generation["authority_status"] == "NOT_REQUIRED"
    assert evidence["failure_scope"]["halt_required"] is False


def test_phase26_step9_buy_review_sell_pass_is_observable_without_global_halt() -> None:
    evidence = _build(action="BUY", submit_status="REVIEW_REQUIRED", sell_submit_status="PASS")

    assert evidence["buy_sell_independence"]["buy_submit_status"] == "REVIEW_REQUIRED"
    assert evidence["buy_sell_independence"]["sell_submit_status"] == "PASS"
    assert evidence["buy_sell_independence"]["buy_block_scope"] == "BUY_ITEM_REVIEW"
    assert evidence["buy_sell_independence"]["system_wide_halt"] is False
    assert evidence["failure_scope"]["affected_actions"] == ["BUY"]
    assert "SELL" in evidence["failure_scope"]["unaffected_actions"]


def test_phase26_step9_missing_dynamic_position_count_materializes_failure_scope() -> None:
    sources = _sources()
    sources[2] = EvidenceSource(
        "position_count",
        {
            "position_count_authority_winner": "",
            "selected_dynamic_position_count": None,
            "position_count_binding_constraint": "REVIEW_REQUIRED",
            "position_count_authority_status": "REVIEW_REQUIRED",
            "position_count_authority_reason": "dynamic_position_count_missing",
        },
        "position_count.json",
    )

    evidence = _build_from_sources(sources)

    assert evidence["validation"]["status"] == "REVIEW_REQUIRED"
    assert evidence["failure_scope"]["failure_authority"] == "position_count"
    assert evidence["failure_scope"]["fallback_used"] is False
    assert evidence["failure_scope"]["review_required"] is True


def test_phase26_step9_current_source_conflict_is_visible() -> None:
    sources = _sources()
    sources[9] = EvidenceSource(
        "current",
        {
            "selected_current_source": "persistent_ledger/state.json",
            "current_authority_winner": "persistent_ledger_state",
            "current_total_equity": None,
            "current_source_business_date": BUSINESS_DATE,
            "current_authority_status": "REVIEW_REQUIRED",
            "current_authority_reason": "current_source_conflict_detected",
            "source_conflict_detected": True,
            "source_selection_reason": "broker_ledger_conflict_requires_review",
        },
        "current_state.json",
    )

    evidence = _build_from_sources(sources)
    current = next(row for row in evidence["authority_evidence"] if row["authority_name"] == "current")

    assert current["authority_status"] == "REVIEW_REQUIRED"
    assert current["selection_reason"] == "current_source_conflict_detected"
    assert evidence["failure_scope"]["failure_authority"] == "current"


def test_phase26_step9_generation_mismatch_materializes_pending_approval_submit_ids() -> None:
    sources = _sources()
    sources[8] = EvidenceSource(
        "submit",
        {
            "submit_authority_source": "pending_approval_planning_materialized_evidence",
            "submit_authority_winner": "canonical_quantity_contract_revalidated_at_submit",
            "submit_item_status": "REVIEW_REQUIRED",
            "submit_generation_binding_status": "BLOCKED",
            "submit_generation_binding_reason": "accepted_generation_id_mismatch",
            "planning_generation_id": "gen-b",
            "pending_generation_id": "gen-a",
            "approval_generation_id": "gen-a",
            "submit_generation_id": "gen-a",
            "quantity": 100,
            "estimated_amount": 100000,
        },
        "submit_guard.json",
    )

    evidence = _build_from_sources(sources)
    submit = next(row for row in evidence["authority_evidence"] if row["authority_name"] == "submit")

    assert submit["authority_status"] == "REVIEW_REQUIRED"
    assert submit["selected_value"] == "gen-a"
    assert submit["requested_value"] == "gen-b"
    assert evidence["failure_scope"]["failure_authority"] == "submit"


def test_phase26_step9_system_halt_is_distinguished_from_item_review() -> None:
    evidence = _build(action="BUY", safety_halt=True)

    assert evidence["failure_scope"]["halt_required"] is True
    assert evidence["failure_scope"]["failure_scope"] == "RUN_SCOPED_HALT"
    assert evidence["buy_sell_independence"]["scope_classification"] == "RUN_SCOPED_HALT"


def test_phase26_step9_negative_assertion_and_mode_parity_aggregate_pass() -> None:
    negative = build_negative_assertion_aggregate(
        step_ledgers=[{"negative_assertions": _negative_pass()}],
        evidence_paths={name: f"reports/{name}.md" for name in _negative_names()},
    )
    parity = build_mode_parity_matrix()

    assert negative["status"] == "PASS"
    assert {item["assertion"] for item in negative["checks"]} == set(_negative_names())
    assert parity["status"] == "PASS"
    assert len(parity["rows"]) >= 10
    assert all(row["status"] == "PASS" for row in parity["rows"])


def _build(
    *,
    action: str,
    submit_status: str = "PASS",
    sell_submit_status: str = "",
    generation_status: str = "PASS",
    safety_halt: bool = False,
) -> dict:
    sources = _sources(
        action=action,
        submit_status=submit_status,
        sell_submit_status=sell_submit_status,
        generation_status=generation_status,
        safety_halt=safety_halt,
    )
    return _build_from_sources(sources, action=action)


def _build_from_sources(sources, *, action: str = "BUY") -> dict:
    return build_cross_authority_evidence(
        run_id="run-step9",
        business_date=BUSINESS_DATE,
        runtime_mode="demo",
        decision_scope="item",
        symbol="7203",
        action=action,
        item_id="item-1",
        pending_id="pending-1",
        approval_id="approval-1",
        submit_id="submit-1",
        sources=sources,
    )


def _sources(
    *,
    action: str = "BUY",
    submit_status: str = "PASS",
    sell_submit_status: str = "",
    generation_status: str = "PASS",
    safety_halt: bool = False,
):
    submit_payload = {
        "submit_authority_source": "pending_approval_planning_materialized_evidence",
        "submit_authority_winner": "canonical_quantity_contract_revalidated_at_submit",
        "submit_item_status": submit_status,
        "submit_aggregate_status": submit_status,
        "buy_submit_status": submit_status if action == "BUY" else "",
        "sell_submit_status": sell_submit_status or (submit_status if action == "SELL" else "PASS"),
        "submit_generation_binding_status": generation_status,
        "planning_generation_id": "gen-a",
        "pending_generation_id": "gen-a",
        "approval_generation_id": "gen-a",
        "submit_generation_id": "gen-a",
        "quantity": 100,
        "estimated_amount": 100000,
        "guard_decision": submit_status,
        "buy_sell_independence_preserved": True,
    }
    return [
        EvidenceSource("market_context", {"market_context_source": "market_context.json", "market_context_authority_winner": "market_context_regime", "market_context_regime": "normal", "market_context_risk_state": "normal", "market_context_status": "PASS"}, "market_context.json"),
        EvidenceSource("capital", {"selected_capital_source": "current_state.total_equity", "capital_authority_winner": "current_total_equity", "active_deployment_capital": 1000000, "initial_or_bootstrap_capital": 1000000, "capital_authority_status": "PASS"}, "current_state.json"),
        EvidenceSource("position_count", {"position_count_authority_source": "dynamic_position_count_policy", "position_count_authority_winner": "dynamic_position_count", "selected_dynamic_position_count": 7, "strategy_requested_position_count": 8, "position_count_binding_constraint": "CURRENT_HOLDINGS", "position_count_authority_status": "PASS"}, "position_count.json"),
        EvidenceSource("cash_exposure", {"cash_exposure_authority_source": "dynamic_cash_exposure_policy", "cash_exposure_authority_winner": "dynamic_cash_exposure", "selected_runtime_exposure_limit": 800000, "strategy_requested_exposure_ratio": 0.8, "cash_exposure_binding_constraint": "CURRENT_CASH_EXPOSURE", "cash_exposure_authority_status": "PASS"}, "cash_exposure.json"),
        EvidenceSource("portfolio_policy", {"portfolio_policy_source": "capital_deployment_policy", "portfolio_policy_authority_winner": "capital_deployment_policy", "policy_version": "v1", "portfolio_policy_status": "PASS"}, "policy.json"),
        EvidenceSource("position_sizing", {"position_sizing_source": "position_sizing_authority", "position_sizing_authority_winner": "dynamic_position_sizing", "selected_position_amount": 100000, "strategy_requested_position_amount": 120000, "position_sizing_binding_constraint": "LOT_ADJUSTED_CAPACITY", "position_sizing_authority_status": "PASS"}, "position_sizing.json"),
        EvidenceSource("planning", {"planning_source": "runtime_planning.json", "planning_authority_winner": "strategy_runtime_planning", "planning_action": action, "selected_quantity": 100, "requested_quantity": 120, "planning_binding_constraint": "LOT_ADJUSTED_CAPACITY", "planning_status": "PASS", "buy_planning_status": "PASS", "sell_planning_status": "PASS"}, "runtime_planning.json"),
        EvidenceSource("pending_approval", {"pending_path": "pending_order_plan.json", "approval_path": "approval_artifact.json", "pending_status": "APPROVED", "approval_status": "APPROVED", "approved_item_ids": ["item-1"], "approved_order_conditions": {"item-1": {"quantity": 100}}}, "pending_order_plan.json"),
        EvidenceSource("submit", submit_payload, "submit_guard.json"),
        EvidenceSource("current", {"selected_current_source": "persistent_ledger/state.json", "current_authority_winner": "persistent_ledger_state", "current_cash": 500000, "current_market_value": 100000, "current_total_equity": 600000, "current_source_business_date": BUSINESS_DATE, "current_authority_status": "PASS"}, "current_state.json"),
        EvidenceSource("projection", {"selected_projection_source": "runtime_owned_fill_projection", "projection_status": "PASS", "projection_authority_winner": "runtime_owned_fill_projection", "current_source_business_date": BUSINESS_DATE}, "projection.json"),
        EvidenceSource("accepted_generation", {"accepted_generation_source": "accepted_generation_manifest", "accepted_generation_id": "gen-a", "accepted_generation_business_date": BUSINESS_DATE, "requested_business_date": BUSINESS_DATE, "accepted_generation_status": generation_status, "generation_binding_status": generation_status}, "accepted_generation_manifest.json"),
        EvidenceSource("temporal", {"temporal_authority_source": "runtime_business_date", "temporal_authority_winner": "runtime_business_date", "requested_business_date": BUSINESS_DATE, "selected_business_date": BUSINESS_DATE, "temporal_authority_status": "PASS", "temporal_binding_status": "PASS"}, "temporal.json"),
        EvidenceSource("safety", {"safety_source": "runtime_safety_decision", "safety_decision": "PASS" if not safety_halt else "HALT", "safety_guard_status": "PASS" if not safety_halt else "HALT", "safety_halt_runtime": safety_halt}, "safety.json"),
        EvidenceSource("corporate_action", {"corporate_action_adjustment_authority_path": "corporate_action.json", "corporate_action_adjustment_authority_winner": "corporate_action_adjustment_authority", "corporate_action_adjustment_authority_status": "PASS", "corporate_action_event_status": "NOT_DETECTED", "quantity": 100}, "corporate_action.json"),
    ]


def _negative_names():
    return (
        "old_capital_path_zero",
        "old_position_count_path_zero",
        "old_cash_exposure_path_zero",
        "old_position_sizing_path_zero",
        "old_planning_path_zero",
        "old_submit_path_zero",
        "old_current_path_zero",
        "old_generation_path_zero",
        "old_temporal_path_zero",
        "old_config_authority_zero",
        "old_schema_authority_zero",
        "old_fallback_zero",
        "old_runtime_activation_zero",
        "old_fixture_test_expectation_zero",
        "production_old_consumer_zero",
        "demo_old_consumer_zero",
        "historical_old_consumer_zero",
    )


def _negative_pass():
    return {
        "old_production_consumer_zero": "PASS",
        "old_demo_consumer_zero": "PASS",
        "old_historical_consumer_zero": "PASS",
        "old_config_authority_zero": "PASS",
        "old_schema_authority_zero": "PASS",
        "old_fallback_zero": "PASS",
        "old_runtime_activation_zero": "PASS",
        "old_fixture_test_expectation_zero": "PASS",
    }
