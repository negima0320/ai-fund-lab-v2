from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy import capital_deployment, portfolio_construction, portfolio_policy, position_management, runtime_planning
from ai_fund_lab_v2.strategy.runtime_planning import (
    RuntimePlanningConsumerError,
    RuntimePlanningSchemaError,
    RuntimePlanningSourceSummary,
    build_runtime_planning_payload,
    default_runtime_artifact_path,
    load_runtime_planning_fixture,
    validate_runtime_planning_artifact,
    verify_source_hashes,
)


def test_phase22_g_produces_draft_pass_eligible_runtime_planning_artifact(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert result.status == "PASS"
    assert result.payload["artifact_lifecycle_status"] == "DRAFT"
    assert result.payload["runtime_consumer_eligibility"] == "ELIGIBLE"
    assert result.payload["downstream_calculation_eligibility"] == "CALCULATION_ALLOWED_WITH_REVIEW"
    assert result.payload["concrete_allocation_decided"] is False
    assert result.payload["concrete_quantity_decided"] is False
    assert result.payload["lot_rounding_decided"] is False
    assert result.payload["pending_written"] is False
    assert result.payload["submit_generated"] is False
    assert validate_runtime_planning_artifact(result.payload)["status"] == "PASS"


def test_phase22_g_schema_rejects_invalid_intent_status_and_concrete_fields(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload
    mutations = (
        lambda item: item["plans"][0].update({"planning_intent": "BUY"}),
        lambda item: item["plans"][0].update({"order_side_intent": "BID"}),
        lambda item: item["plans"][0].pop("planning_id"),
        lambda item: item["plans"][0].pop("security_code"),
        lambda item: item.update({"schema_version": "runtime_planning.v999"}),
        lambda item: item.update({"runtime_consumer_eligibility": "NOT_ELIGIBLE"}),
        lambda item: item.update({"allocation_jpy": 100000}),
        lambda item: item["plans"][0].update({"quantity": 100}),
        lambda item: item["plans"][0].update({"lot_rounding_result": 100}),
        lambda item: item.update({"pending_written": True}),
        lambda item: item.update({"submit_generated": True}),
        lambda item: item["plans"][0]["pending_candidate_contract"].update({"pending_writer_connected": True}),
    )
    for mutation in mutations:
        mutated = json.loads(json.dumps(payload))
        mutation(mutated)
        with pytest.raises(RuntimePlanningSchemaError):
            validate_runtime_planning_artifact(mutated)


def test_phase22_g_pm_and_portfolio_mapping_taxonomy(tmp_path: Path) -> None:
    result = _produce(
        tmp_path,
        pm_actions={"7203": "HOLD", "6758": "ADD", "8306": "REDUCE", "9432": "EXIT"},
        pc_members={
            "7203": ("RETAIN", True),
            "6758": ("RETAIN", True),
            "8306": ("RETAIN", True),
            "9432": ("RETAIN", True),
            "6098": ("ADD_CANDIDATE", False),
            "9984": ("EXCLUDE", False),
        },
        current_codes=("7203", "6758", "8306", "9432"),
    )

    intents = {plan["security_code"]: plan["planning_intent"] for plan in result.payload["plans"]}
    assert intents["7203"] == "NO_ACTION"
    assert intents["6758"] == "BUY_ADD"
    assert intents["8306"] == "SELL_REDUCE"
    assert intents["9432"] == "SELL_EXIT"
    assert intents["6098"] == "BUY_NEW"
    assert "9984" not in intents
    assert result.payload["producer_result_status"] == "REVIEW_REQUIRED"


def test_phase22_g_portfolio_sell_membership_alone_does_not_generate_sell(tmp_path: Path) -> None:
    result = _produce(
        tmp_path,
        pm_actions={"8306": "HOLD"},
        pc_members={"8306": ("REMOVE_CANDIDATE", True)},
        current_codes=("8306",),
    )

    plan = result.payload["plans"][0]
    assert plan["planning_intent"] == "UNRESOLVED"
    assert "planning_conflict_review:portfolio_membership_requires_pm_sell_intent:8306" in plan["reason_codes"]
    assert all(plan["planning_intent"] not in {"SELL_REDUCE", "SELL_EXIT"} for plan in result.payload["plans"])


def test_phase22_g_conflicts_and_current_position_guards_fail_closed(tmp_path: Path) -> None:
    add_missing = _produce(
        tmp_path / "add_missing",
        pm_actions={"6758": "ADD"},
        pc_members={"6758": ("RETAIN", False)},
        current_codes=(),
    )
    sell_missing = _produce(
        tmp_path / "sell_missing",
        pm_actions={"8306": "REDUCE"},
        pc_members={"8306": ("RETAIN", True)},
        current_codes=(),
    )
    pending_conflict = _produce(
        tmp_path / "pending_conflict",
        pm_actions={"6758": "ADD"},
        pc_members={"6758": ("RETAIN", True)},
        current_codes=("6758",),
        pending_codes=("6758",),
    )

    assert add_missing.payload["producer_result_status"] == "BLOCK"
    assert "add_without_current_position:6758" in add_missing.payload["reason_codes"]
    assert sell_missing.payload["producer_result_status"] == "BLOCK"
    assert "missing_current_position_for_sell:8306" in sell_missing.payload["reason_codes"]
    assert pending_conflict.payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert "existing_pending_conflict:6758" in pending_conflict.payload["reason_codes"]


def test_phase22_g_quantity_authority_boundary_never_decides_quantity(tmp_path: Path) -> None:
    payload = _produce(tmp_path, pm_actions={"6758": "ADD"}, pc_members={"6758": ("RETAIN", True)}, current_codes=("6758",)).payload
    plan = payload["plans"][0]

    assert plan["quantity_required"] is True
    assert plan["quantity_authority"] == "PHASE22_J_POSITION_SIZING"
    assert plan["quantity_status"] == "REVIEW_REQUIRED_AUTHORITY_UNRESOLVED"
    assert "quantity" not in plan
    assert "allocation_jpy" not in plan
    assert payload["concrete_quantity_decided"] is False


def test_phase23_aa_runtime_planning_maps_position_sizing_zero_to_no_order(tmp_path: Path) -> None:
    position_sizing_path = _write_position_sizing(
        tmp_path,
        {
            "6098": {
                "sizing_status": "RESOLVED_ZERO_ALLOCATION",
                "target_notional": 0.0,
                "incremental_buy_notional": 0.0,
            }
        },
        current_position_rows=(
            _runtime_owned_current_position_row(
                "76470",
                quantity=6900,
                as_of="2026-07-15",
                source="runtime_v2_runtime_owned_fill_projection",
            ),
        ),
    )
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, {"6098": ("ADD_CANDIDATE", False)}),
        capital_deployment_artifact_path=_write_capital_deployment(tmp_path, pm_actions={}, current_codes=(), pc_members={"6098": ("ADD_CANDIDATE", False)}),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, {}),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(tmp_path, "position"),
        pending_summary=_summary(tmp_path, "pending"),
        planning_config_summary=_summary(tmp_path, "planning_config"),
        position_sizing_artifact_path=position_sizing_path,
    )

    assert payload["producer_result_status"] == "PASS"
    plan = payload["plans"][0]
    assert plan["planning_intent"] == "NO_ORDER"
    assert plan["order_side_intent"] == "NONE"
    assert plan["quantity_required"] is False
    assert plan["quantity_status"] == "RESOLVED_ZERO_DELTA"
    assert "quantity_unresolved:6098" not in payload["reason_codes"]


def test_phase23_ai_runtime_planning_keeps_sized_buy_candidate_as_buy_new(tmp_path: Path) -> None:
    position_sizing_path = _write_position_sizing(
        tmp_path,
        {
            "6098": {
                "sizing_status": "SIZED",
                "target_notional": 120000.0,
                "incremental_buy_notional": 120000.0,
            }
        },
    )
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, {"6098": ("ADD_CANDIDATE", False)}),
        capital_deployment_artifact_path=_write_capital_deployment(tmp_path, pm_actions={}, current_codes=(), pc_members={"6098": ("ADD_CANDIDATE", False)}),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, {}),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(tmp_path, "position"),
        pending_summary=_summary(tmp_path, "pending"),
        planning_config_summary=_summary(tmp_path, "planning_config"),
        position_sizing_artifact_path=position_sizing_path,
    )

    assert payload["producer_result_status"] == "PASS"
    plan = payload["plans"][0]
    assert plan["planning_intent"] == "BUY_NEW"
    assert plan["order_side_intent"] == "BUY"
    assert plan["quantity_required"] is True
    assert plan["quantity_status"] == "RESOLVED_EXECUTABLE"
    assert plan["reference_price"] == 1000.0
    assert plan["reference_price_resolution"]["status"] == "PASS"
    assert plan["reference_price_authority"]["PIT_status"] == "PASS"
    assert all(item["planning_intent"] != "NO_ORDER" for item in payload["plans"])


def test_phase28_d25_runtime_planning_blocks_target_zero_sell_exit_without_pm_exit_authority(tmp_path: Path) -> None:
    position_sizing_path = _write_position_sizing(
        tmp_path,
        {
            "7203": {
                "sizing_status": "SIZED",
                "target_notional": 0.0,
                "target_quantity_candidate": 0,
                "quantity_delta_candidate": -100,
                "quantity_status": "RESOLVED_CANDIDATE",
            }
        },
    )
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, {"7203": ("RETAIN", True)}),
        capital_deployment_artifact_path=None,
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, {"7203": "HOLD"}),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(tmp_path, "position", rows=({"security_code": "7203"},)),
        pending_summary=_summary(tmp_path, "pending"),
        planning_config_summary=_summary(tmp_path, "planning_config"),
        position_sizing_artifact_path=position_sizing_path,
    )

    plan = payload["plans"][0]
    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert plan["planning_intent"] == "UNRESOLVED"
    assert plan["order_side_intent"] == "UNRESOLVED"
    assert plan["pending_eligibility"] == "REVIEW_REQUIRED"
    assert plan["quantity_required"] is False
    assert plan["planned_quantity"] == 0
    assert plan["source_pm_action"] == "HOLD"
    assert plan["full_liquidation_authority_present"] is False
    assert plan["full_liquidation_authority_source"] == "NONE"
    assert "planning_conflict_review:full_liquidation_authority_missing:7203" in plan["reason_codes"]


def test_phase28_d25_runtime_planning_preserves_pm_exit_to_sell_exit(tmp_path: Path) -> None:
    position_sizing_path = _write_position_sizing(
        tmp_path,
        {
            "9432": {
                "sizing_status": "SIZED",
                "target_notional": 0.0,
                "target_quantity_candidate": 0,
                "quantity_delta_candidate": -100,
                "quantity_status": "RESOLVED_CANDIDATE",
            }
        },
    )
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, {"9432": ("REMOVE_CANDIDATE", True)}),
        capital_deployment_artifact_path=None,
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, {"9432": "EXIT"}),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(tmp_path, "position", rows=({"security_code": "9432"},)),
        pending_summary=_summary(tmp_path, "pending"),
        planning_config_summary=_summary(tmp_path, "planning_config"),
        position_sizing_artifact_path=position_sizing_path,
    )

    plan = payload["plans"][0]
    assert payload["producer_result_status"] == "PASS"
    assert plan["planning_intent"] == "SELL_EXIT"
    assert plan["order_side_intent"] == "SELL"
    assert plan["planned_quantity"] == 100
    assert plan["source_pm_action"] == "EXIT"
    assert plan["full_liquidation_authority_present"] is True
    assert plan["full_liquidation_authority_source"] == "PM_EXIT"
    assert "full_liquidation_authority:PM_EXIT" in plan["reason_codes"]
    assert plan["reference_price"] == 1000.0
    assert plan["reference_price_resolution"]["status"] == "PASS"


def test_phase28_d25_runtime_planning_maps_pm_reduce_to_sell_reduce_not_exit(tmp_path: Path) -> None:
    result = _produce(
        tmp_path,
        pm_actions={"8306": "REDUCE"},
        pc_members={"8306": ("REDUCE_CANDIDATE", True)},
        current_codes=("8306",),
        current_position_rows=(
            _runtime_owned_current_position_row(
                "8306",
                quantity=100,
                as_of="2026-07-15",
                source="runtime_v2_runtime_owned_fill_projection",
            ),
        ),
        position_sizing_positions={
            "8306": {
                "sizing_status": "SIZED",
                "target_quantity_candidate": 60,
                "quantity_delta_candidate": -40,
                "quantity_status": "RESOLVED_CANDIDATE",
            }
        },
    )

    plan = result.payload["plans"][0]
    assert result.payload["producer_result_status"] == "PASS"
    assert plan["planning_intent"] == "SELL_REDUCE"
    assert plan["order_side_intent"] == "SELL"
    assert plan["planned_quantity"] == 40
    assert plan["source_pm_action"] == "REDUCE"
    assert plan["full_liquidation_authority_present"] is False
    assert plan["full_liquidation_authority_source"] == "NONE"


def test_phase29_l21t_ad_runtime_planning_preserves_reduce_intentional_no_order_semantic(tmp_path: Path) -> None:
    result = _produce(
        tmp_path,
        pm_actions={"8306": "REDUCE"},
        pc_members={"8306": ("REDUCE_CANDIDATE", True)},
        current_codes=("8306",),
        current_position_rows=(
            _runtime_owned_current_position_row(
                "8306",
                quantity=100,
                as_of="2026-07-15",
                source="runtime_v2_runtime_owned_fill_projection",
            ),
        ),
        position_sizing_positions={
            "8306": {
                "sizing_status": "SIZED",
                "target_quantity_candidate": 100,
                "quantity_delta_candidate": 0,
                "quantity_status": "RESOLVED_ZERO_DELTA",
                "reduce_execution_semantic": "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT",
                "reduce_executability_status": "INTENTIONAL_NO_ORDER",
                "reduce_intentional_no_order": True,
                "reduce_intentional_no_order_reason": "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT",
                "reduce_executability_evidence": {
                    "source_decision": "REDUCE",
                    "symbol": "8306",
                    "raw_reduce_quantity": 25.0,
                    "tradable_unit": 100,
                    "rounded_executable_quantity": 0,
                    "final_sell_quantity": 0,
                    "execution_semantic": "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT",
                    "intentional_no_order": True,
                },
            }
        },
    )

    plan = result.payload["plans"][0]
    assert result.payload["producer_result_status"] == "PASS"
    assert plan["planning_intent"] == "NO_ORDER"
    assert plan["order_side_intent"] == "NONE"
    assert plan["quantity_required"] is False
    assert plan["no_order_reason"] == "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT"
    assert plan["reduce_execution_semantic"] == "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT"
    assert plan["reduce_intentional_no_order"] is True
    assert "no_order_reduce_intentional_no_order" in plan["reason_codes"]
    assert validate_runtime_planning_artifact(result.payload)["status"] == "PASS"


def test_phase28_d36_runtime_planning_maps_existing_add_zero_delta_to_no_action(tmp_path: Path) -> None:
    result = _produce(
        tmp_path,
        pm_actions={"76470": "ADD"},
        pc_members={"76470": ("RETAIN", True)},
        current_codes=("76470",),
        position_sizing_positions={
            "76470": {
                "sizing_status": "SIZED",
                "target_quantity_candidate": 6900,
                "quantity_delta_candidate": 0,
                "quantity_status": "RESOLVED_ZERO_DELTA",
            }
        },
        current_position_rows=(
            _runtime_owned_current_position_row(
                "76470",
                quantity=6900,
                as_of="2026-07-15",
                source="runtime_v2_runtime_owned_fill_projection",
            ),
        ),
    )

    plan = result.payload["plans"][0]
    assert result.payload["producer_result_status"] == "PASS"
    assert plan["planning_intent"] == "NO_ACTION"
    assert plan["planned_quantity"] == 0
    assert plan["source_pm_action"] == "ADD"
    assert "current_position_zero_delta_maps_to_no_action" in plan["reason_codes"]


def test_phase28_d25_pm_reduce_rounding_zero_does_not_silently_escalate_to_sell_exit(tmp_path: Path) -> None:
    result = _produce(
        tmp_path,
        pm_actions={"8306": "REDUCE"},
        pc_members={"8306": ("REDUCE_CANDIDATE", True)},
        current_codes=("8306",),
        position_sizing_positions={
            "8306": {
                "sizing_status": "SIZED",
                "target_quantity_candidate": 0,
                "quantity_delta_candidate": -100,
                "quantity_status": "RESOLVED_CANDIDATE",
            }
        },
    )

    plan = result.payload["plans"][0]
    assert result.payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert plan["planning_intent"] == "UNRESOLVED"
    assert plan["pending_eligibility"] == "REVIEW_REQUIRED"
    assert plan["source_pm_action"] == "REDUCE"
    assert plan["full_liquidation_authority_present"] is False
    assert "planning_conflict_review:full_liquidation_authority_missing:8306" in plan["reason_codes"]


def test_phase28_d25_pm_unresolved_target_zero_does_not_generate_sell_exit(tmp_path: Path) -> None:
    result = _produce(
        tmp_path,
        pm_actions={"31330": "UNRESOLVED"},
        pc_members={"31330": ("UNRESOLVED", True)},
        current_codes=("31330",),
        position_sizing_positions={
            "31330": {
                "sizing_status": "SIZED",
                "target_quantity_candidate": 0,
                "quantity_delta_candidate": -100,
                "quantity_status": "RESOLVED_CANDIDATE",
            }
        },
    )

    plan = result.payload["plans"][0]
    assert result.payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert plan["planning_intent"] == "UNRESOLVED"
    assert plan["source_pm_action"] == "UNRESOLVED"
    assert plan["full_liquidation_authority_present"] is False
    assert plan["full_liquidation_authority_source"] == "NONE"
    assert "planning_conflict_review:full_liquidation_authority_missing:31330" in plan["reason_codes"]


def test_phase23_bo_runtime_planning_requires_price_authority_for_executable_plan(tmp_path: Path) -> None:
    position_sizing_path = _write_position_sizing(
        tmp_path,
        {
            "6098": {
                "sizing_status": "SIZED",
                "target_notional": 120000.0,
                "incremental_buy_notional": 120000.0,
                "reference_price": None,
                "reference_price_authority": {},
                "reference_price_resolution": {},
            }
        },
    )
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, {"6098": ("ADD_CANDIDATE", False)}),
        capital_deployment_artifact_path=None,
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, {}),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(tmp_path, "position"),
        pending_summary=_summary(tmp_path, "pending"),
        planning_config_summary=_summary(tmp_path, "planning_config"),
        position_sizing_artifact_path=position_sizing_path,
    )

    assert payload["plans"][0]["planning_intent"] == "BUY_NEW"
    with pytest.raises(RuntimePlanningSchemaError) as excinfo:
        validate_runtime_planning_artifact(payload)
    assert "reference_price_missing_for_executable_plan:0" in str(excinfo.value)


def test_phase23_bh_runtime_planning_blocks_no_buy_reason_from_executable_buy(tmp_path: Path) -> None:
    opportunity_path = _write_opportunity_rankings(
        tmp_path,
        [
            {
                "symbol": "6098",
                "rank": 1,
                "buy_rank": 1,
                "expected_edge_score": 0.42,
                "no_buy_reason": "high_downside_risk_score",
            }
        ],
    )
    result = _produce(
        tmp_path,
        pc_members={"6098": ("ADD_CANDIDATE", False)},
        current_codes=(),
        position_sizing_positions={
            "6098": {
                "sizing_status": "SIZED",
                "target_notional": 120000.0,
                "target_quantity_candidate": 100,
                "quantity_delta_candidate": 100,
                "quantity_status": "RESOLVED_CANDIDATE",
            }
        },
        opportunity_artifact_path=opportunity_path,
    )

    plan = result.payload["plans"][0]
    assert plan["planning_intent"] == "NO_ORDER"
    assert plan["order_side_intent"] == "NONE"
    assert plan["quantity_required"] is False
    assert plan["planned_quantity"] == 0
    assert plan["no_order_reason"] == "opportunity_no_buy_reason_present"
    assert "opportunity_no_buy_reason_present:high_downside_risk_score" in plan["reason_codes"]


def test_phase29_l21t_ak_runtime_planning_allows_uncalibrated_non_positive_reason(tmp_path: Path) -> None:
    opportunity_path = _write_opportunity_rankings(
        tmp_path,
        [
            {
                "symbol": "6098",
                "rank": 1,
                "buy_rank": 1,
                "runtime_opportunity_score": -0.25,
                "expected_edge_score": -0.25,
                "no_buy_reason": "non_positive_expected_edge_score",
                "canonical_score_field": "runtime_opportunity_score",
                "score_semantic_role": "uncalibrated_relative_model_score",
                "calibration_applied": False,
                "economic_units_available": False,
            }
        ],
        metadata={
            "canonical_score_field": "runtime_opportunity_score",
            "score_semantic_role": "uncalibrated_relative_model_score",
            "calibration_applied": False,
            "economic_units_available": False,
        },
    )
    result = _produce(
        tmp_path,
        pc_members={"6098": ("ADD_CANDIDATE", False)},
        current_codes=(),
        position_sizing_positions={
            "6098": {
                "sizing_status": "SIZED",
                "target_notional": 120000.0,
                "target_quantity_candidate": 100,
                "quantity_delta_candidate": 100,
                "quantity_status": "RESOLVED_CANDIDATE",
                "reference_price": 1200.0,
            }
        },
        opportunity_artifact_path=opportunity_path,
    )

    plan = result.payload["plans"][0]
    assert plan["planning_intent"] == "BUY_NEW"
    assert plan["order_side_intent"] == "BUY"
    assert plan["quantity_required"] is True
    assert plan["planned_quantity"] == 100
    assert plan["no_order_reason"] == ""
    assert "opportunity_no_buy_reason_present:non_positive_expected_edge_score" not in plan["reason_codes"]


def test_phase23_bk_runtime_owned_current_position_zero_delta_maps_to_no_action(tmp_path: Path) -> None:
    result = _produce(
        tmp_path,
        pm_actions={"31330": "UNRESOLVED"},
        pc_members={"31330": ("UNRESOLVED", True)},
        current_codes=("31330",),
        current_position_rows=(
            _runtime_owned_current_position_row("31330", quantity=700, as_of="2026-07-15", source="runtime_v2_runtime_owned_fill_projection"),
        ),
        position_sizing_positions={
            "31330": {
                "sizing_status": "SIZED",
                "target_quantity_candidate": 0,
                "quantity_delta_candidate": 0,
                "quantity_status": "RESOLVED_ZERO_DELTA",
            }
        },
    )

    plan = result.payload["plans"][0]
    authority = plan["current_position_membership_authority"]
    assert result.payload["producer_result_status"] == "PASS"
    assert plan["planning_intent"] == "NO_ACTION"
    assert plan["order_side_intent"] == "NONE"
    assert plan["pending_eligibility"] == "NOT_REQUIRED"
    assert plan["quantity_required"] is False
    assert plan["planned_quantity"] == 0
    assert authority["status"] == "PASS"
    assert authority["membership"] == "NEWLY_FILLED_PORTFOLIO_MEMBER"
    assert "current_position_zero_delta_maps_to_no_action" in plan["reason_codes"]
    assert "unresolved_mapping:portfolio_membership_unresolved" not in result.payload["reason_codes"]


def test_phase27_d2e_runtime_planning_maps_canonical_quantity_delta_to_runtime_action(tmp_path: Path) -> None:
    position_sizing_plan_path = _write_position_sizing_plan(
        tmp_path,
        {
            "6758": {"source_pm_intent": "ADD", "current_quantity": 100, "target_quantity_candidate": 150, "quantity_delta_candidate": 50},
            "7203": {"source_pm_intent": "HOLD", "current_quantity": 100, "target_quantity_candidate": 100, "quantity_delta_candidate": 0},
            "8306": {"source_pm_intent": "REDUCE", "current_quantity": 100, "target_quantity_candidate": 60, "quantity_delta_candidate": -40},
            "9432": {"source_pm_intent": "EXIT", "current_quantity": 100, "target_quantity_candidate": 0, "quantity_delta_candidate": -100},
        },
    )
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(
            tmp_path,
            {
                "6758": ("RETAIN", True),
                "7203": ("RETAIN", True),
                "8306": ("RETAIN", True),
                "9432": ("RETAIN", True),
            },
        ),
        capital_deployment_artifact_path=None,
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(
            tmp_path,
            {"6758": "ADD", "7203": "HOLD", "8306": "REDUCE", "9432": "EXIT"},
        ),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(
            tmp_path,
            "position",
            rows=(
                _runtime_owned_current_position_row("6758", quantity=100, as_of="2026-07-15", source="runtime_owned_execution_ledger"),
                _runtime_owned_current_position_row("7203", quantity=100, as_of="2026-07-15", source="runtime_owned_execution_ledger"),
                _runtime_owned_current_position_row("8306", quantity=100, as_of="2026-07-15", source="runtime_owned_execution_ledger"),
                _runtime_owned_current_position_row("9432", quantity=100, as_of="2026-07-15", source="runtime_owned_execution_ledger"),
            ),
        ),
        pending_summary=_summary(tmp_path, "pending"),
        planning_config_summary=_summary(tmp_path, "planning_config"),
        position_sizing_plan_artifact_path=position_sizing_plan_path,
    )

    plans = {plan["security_code"]: plan for plan in payload["plans"]}
    assert payload["producer_result_status"] == "PASS"
    assert payload["canonical_quantity_source"] == "CANONICAL_POSITION_SIZING_PLAN"
    assert payload["canonical_quantity_delta_priority"] is True
    assert plans["6758"]["planning_intent"] == "BUY_ADD"
    assert plans["6758"]["quantity_authority"] == runtime_planning.CANONICAL_QUANTITY_AUTHORITY
    assert plans["6758"]["planned_quantity"] == 50
    assert plans["7203"]["planning_intent"] == "NO_ACTION"
    assert plans["7203"]["quantity_delta_candidate"] == 0
    assert plans["8306"]["planning_intent"] == "SELL_REDUCE"
    assert plans["8306"]["planned_quantity"] == 40
    assert plans["9432"]["planning_intent"] == "SELL_EXIT"
    assert plans["9432"]["planned_quantity"] == 100
    assert all(plan["pm_fallback_used"] is False for plan in payload["plans"])
    assert validate_runtime_planning_artifact(payload)["status"] == "PASS"


def test_phase29_l21f_runtime_planning_consumes_soft_cap_buy_add_positive_quantity(tmp_path: Path) -> None:
    result = _produce(
        tmp_path,
        pm_actions={"94320": "ADD"},
        pc_members={"94320": ("RETAIN", True)},
        current_codes=("94320",),
        position_sizing_positions={
            "94320": {
                "sizing_status": "SIZED",
                "pm_action": "ADD",
                "target_weight": 0.194658,
                "maximum_position_weight": 0.18,
                "current_quantity": 900,
                "target_quantity_candidate": 1300,
                "quantity_delta_candidate": 400,
                "quantity_status": "RESOLVED_CANDIDATE",
                "reference_price": 150.4,
            }
        },
    )
    plan = result.payload["plans"][0]

    assert result.payload["producer_result_status"] == "PASS"
    assert plan["security_code"] == "94320"
    assert plan["planning_intent"] == "BUY_ADD"
    assert plan["planned_quantity"] == 400
    assert plan["quantity_delta_candidate"] == 400
    assert "strategy_plan_quantity_unresolved:94320" not in result.payload["reason_codes"]
    assert validate_runtime_planning_artifact(result.payload)["status"] == "PASS"


def test_phase29_l21t_b_runtime_planning_consumes_one_lot_buy_new_soft_cap_quantity(tmp_path: Path) -> None:
    result = _produce(
        tmp_path,
        pm_actions={},
        pc_members={"78780": ("ADD_CANDIDATE", False)},
        current_codes=(),
        position_sizing_positions={
            "78780": {
                "sizing_status": "SIZED",
                "pm_action": "NEW",
                "semantic_buy_type": "BUY_NEW",
                "target_weight": 0.243189,
                "maximum_position_weight": 0.18,
                "current_quantity": 0,
                "target_quantity_candidate": 100,
                "quantity_delta_candidate": 100,
                "quantity_status": "RESOLVED_CANDIDATE",
                "reference_price": 2420.0,
                "phase29_l19_lot_resolution": {
                    "boundary_classification": "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX",
                    "semantic_type": "BUY_NEW",
                    "strategy_cap_overshoot_applied": True,
                    "one_lot_fallback_applied": True,
                    "one_lot_feasibility_status": "PASS",
                    "one_lot_quantity": 100,
                    "final_allocated_quantity": 100,
                    "post_trade_weight": 0.243189,
                    "safety_hard_cap": 0.25,
                    "safety_hard_cap_preserved": True,
                    "safety_margin_after_trade": 0.006811,
                    "lot_overshoot_reason": "ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP",
                },
            }
        },
    )
    plan = next(plan for plan in result.payload["plans"] if plan["security_code"] == "78780")

    assert result.payload["producer_result_status"] == "PASS"
    assert plan["security_code"] == "78780"
    assert plan["planning_intent"] == "BUY_NEW"
    assert plan["order_side_intent"] == "BUY"
    assert plan["planned_quantity"] == 100
    assert plan["quantity_delta_candidate"] == 100
    assert plan["quantity_status"] == "RESOLVED_EXECUTABLE"
    assert "quantity_not_produced_due_to_upstream_block" not in plan["reason_codes"]
    assert validate_runtime_planning_artifact(result.payload)["status"] == "PASS"


def test_phase27_d2e_canonical_delta_disables_pm_fallback(tmp_path: Path) -> None:
    position_sizing_plan_path = _write_position_sizing_plan(
        tmp_path,
        {"6758": {"source_pm_intent": "ADD", "current_quantity": 100, "target_quantity_candidate": 100, "quantity_delta_candidate": 0}},
    )
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, {"6758": ("RETAIN", True)}),
        capital_deployment_artifact_path=None,
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, {"6758": "ADD"}),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(
            tmp_path,
            "position",
            rows=(_runtime_owned_current_position_row("6758", quantity=100, as_of="2026-07-15", source="runtime_owned_execution_ledger"),),
        ),
        pending_summary=_summary(tmp_path, "pending"),
        planning_config_summary=_summary(tmp_path, "planning_config"),
        position_sizing_plan_artifact_path=position_sizing_plan_path,
    )

    plan = payload["plans"][0]
    assert payload["producer_result_status"] == "PASS"
    assert plan["planning_intent"] == "NO_ACTION"
    assert plan["pm_fallback_used"] is False
    assert plan["pm_fallback_scope"] == "NOT_USED"
    assert "pm_add_maps_to_buy_add" not in plan["reason_codes"]
    assert "canonical_zero_quantity_delta_maps_to_no_action" in plan["reason_codes"]


def test_phase27_d2e_legacy_pm_fallback_allowed_when_canonical_missing(tmp_path: Path) -> None:
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, {"6758": ("RETAIN", True)}),
        capital_deployment_artifact_path=None,
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, {"6758": "ADD"}),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(
            tmp_path,
            "position",
            rows=(_runtime_owned_current_position_row("6758", quantity=100, as_of="2026-07-15", source="runtime_owned_execution_ledger"),),
        ),
        pending_summary=_summary(tmp_path, "pending"),
        planning_config_summary=_summary(tmp_path, "planning_config"),
    )

    plan = payload["plans"][0]
    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert payload["canonical_quantity_source"] == "LEGACY_POSITION_SIZING"
    assert plan["planning_intent"] == "BUY_ADD"
    assert plan["pm_fallback_used"] is True
    assert plan["pm_fallback_scope"] == "LEGACY_COMPATIBILITY"
    assert "pm_add_maps_to_buy_add" in plan["reason_codes"]


def test_phase27_d2e_canonical_row_without_delta_blocks_duplicate_pm_authority(tmp_path: Path) -> None:
    position_sizing_plan_path = _write_position_sizing_plan(
        tmp_path,
        {"6758": {"source_pm_intent": "ADD", "current_quantity": 100, "target_quantity_candidate": 150, "quantity_delta_candidate": None}},
    )
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, {"6758": ("RETAIN", True)}),
        capital_deployment_artifact_path=None,
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, {"6758": "ADD"}),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(
            tmp_path,
            "position",
            rows=(_runtime_owned_current_position_row("6758", quantity=100, as_of="2026-07-15", source="runtime_owned_execution_ledger"),),
        ),
        pending_summary=_summary(tmp_path, "pending"),
        planning_config_summary=_summary(tmp_path, "planning_config"),
        position_sizing_plan_artifact_path=position_sizing_plan_path,
    )

    plan = payload["plans"][0]
    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert plan["planning_intent"] == "UNRESOLVED"
    assert plan["pm_fallback_used"] is False
    assert "planning_conflict_review:canonical_delta_missing_pm_fallback_disabled:6758" in plan["reason_codes"]
    assert "pm_add_maps_to_buy_add" not in plan["reason_codes"]


@pytest.mark.parametrize(
    ("as_of", "valuation_as_of", "expected_membership"),
    [
        ("2026-07-14", "2026-07-14", "CURRENT_PORTFOLIO_MEMBER"),
        ("2026-07-10", "2026-07-14", "CURRENT_PORTFOLIO_MEMBER"),
        ("2026-01-05", "2026-07-14", "CURRENT_PORTFOLIO_MEMBER"),
        ("2026-07-15", "2026-07-15", "NEWLY_FILLED_PORTFOLIO_MEMBER"),
    ],
)
def test_phase23_bq_runtime_owned_current_position_carry_forward_temporal_authority_passes(
    tmp_path: Path,
    as_of: str,
    valuation_as_of: str,
    expected_membership: str,
) -> None:
    row = _runtime_owned_current_position_row(
        "31330",
        quantity=700,
        as_of=as_of,
        source="runtime_v2_runtime_owned_fill_projection",
    )
    row["valuation_as_of"] = valuation_as_of
    row["source_market_date"] = valuation_as_of
    result = _produce(
        tmp_path,
        pm_actions={"31330": "UNRESOLVED"},
        pc_members={"31330": ("UNRESOLVED", True)},
        current_codes=("31330",),
        current_position_rows=(row,),
        position_sizing_positions={
            "31330": {
                "sizing_status": "SIZED",
                "target_quantity_candidate": 0,
                "quantity_delta_candidate": 0,
                "quantity_status": "RESOLVED_ZERO_DELTA",
            }
        },
    )

    plan = result.payload["plans"][0]
    authority = plan["current_position_membership_authority"]
    assert result.payload["producer_result_status"] == "PASS"
    assert plan["planning_intent"] == "NO_ACTION"
    assert plan["order_side_intent"] == "NONE"
    assert authority["status"] == "PASS"
    assert authority["membership"] == expected_membership
    assert authority["position_state_as_of"] == as_of
    assert authority["valuation_as_of"] == valuation_as_of
    assert authority["temporal_contract"]["position_state_not_after_business_date"] is True
    assert "unresolved_mapping:current_position_business_date_mismatch" not in result.payload["reason_codes"]


@pytest.mark.parametrize(
    ("row", "reason"),
    [
        ({"security_code": "31330", "symbol": "31330", "quantity": 700, "as_of": "2026-07-15", "valuation_as_of": "2026-07-15", "source_market_date": "2026-07-15", "source": ""}, "unresolved_mapping:current_position_ownership_authority_missing"),
        ({"security_code": "31330", "symbol": "31330", "quantity": 700, "as_of": "2026-07-15", "valuation_as_of": "2026-07-15", "source_market_date": "2026-07-15", "source": "broker_snapshot"}, "unresolved_mapping:current_position_not_runtime_owned"),
        ({"security_code": "31330", "symbol": "31330", "quantity": 700, "as_of": "2026-07-16", "valuation_as_of": "2026-07-15", "source_market_date": "2026-07-15", "source": "runtime_v2_runtime_owned_fill_projection"}, "unresolved_mapping:current_position_state_future_date"),
        ({"security_code": "31330", "symbol": "31330", "quantity": 700, "as_of": "2026-07-15", "acquisition_date": "2026-07-16", "valuation_as_of": "2026-07-15", "source_market_date": "2026-07-15", "source": "runtime_v2_runtime_owned_fill_projection"}, "unresolved_mapping:current_position_acquisition_future_date"),
        ({"security_code": "31330", "symbol": "31330", "quantity": 700, "as_of": "2026-07-15", "fill_date": "2026-07-16", "valuation_as_of": "2026-07-15", "source_market_date": "2026-07-15", "source": "runtime_v2_runtime_owned_fill_projection"}, "unresolved_mapping:current_position_fill_future_date"),
        ({"security_code": "31330", "symbol": "31330", "quantity": 700, "as_of": "2026-07-15", "valuation_as_of": "2026-07-16", "source_market_date": "2026-07-15", "source": "runtime_v2_runtime_owned_fill_projection"}, "unresolved_mapping:current_position_valuation_future_date"),
        ({"security_code": "31330", "symbol": "31330", "quantity": 700, "as_of": "2026-07-15", "valuation_as_of": "2026-07-15", "source_market_date": "2026-07-16", "source": "runtime_v2_runtime_owned_fill_projection"}, "unresolved_mapping:current_position_source_market_future_date"),
        ({"security_code": "31330", "symbol": "31330", "quantity": 700, "as_of": "2026-07-15", "previous_trading_date": "2026-07-16", "valuation_as_of": "2026-07-15", "source_market_date": "2026-07-15", "source": "runtime_v2_runtime_owned_fill_projection"}, "unresolved_mapping:current_position_previous_trading_future_date"),
        ({"security_code": "31330", "symbol": "72030", "quantity": 700, "as_of": "2026-07-15", "valuation_as_of": "2026-07-15", "source_market_date": "2026-07-15", "source": "runtime_v2_runtime_owned_fill_projection"}, "unresolved_mapping:current_position_symbol_mismatch"),
        ({"security_code": "31330", "symbol": "31330", "quantity": 700, "as_of": "2026-07-15", "valuation_as_of": "2026-07-15", "source_market_date": "2026-07-15", "source": "runtime_v2_runtime_owned_fill_projection", "filled_quantity": 600}, "unresolved_mapping:current_position_fill_quantity_mismatch"),
    ],
)
def test_phase23_bk_current_position_membership_authority_fail_closed(tmp_path: Path, row: dict[str, object], reason: str) -> None:
    result = _produce(
        tmp_path,
        pm_actions={"31330": "UNRESOLVED"},
        pc_members={"31330": ("UNRESOLVED", True)},
        current_codes=("31330",),
        current_position_rows=(row,),
        position_sizing_positions={
            "31330": {
                "sizing_status": "SIZED",
                "target_quantity_candidate": 0,
                "quantity_delta_candidate": 0,
                "quantity_status": "RESOLVED_ZERO_DELTA",
            }
        },
    )

    plan = result.payload["plans"][0]
    assert result.payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert plan["planning_intent"] == "UNRESOLVED"
    assert plan["pending_eligibility"] == "REVIEW_REQUIRED"
    assert plan["quantity_required"] is False
    assert plan["planned_quantity"] == 0
    assert reason in result.payload["reason_codes"]


def test_phase23_ar_minimum_notional_unmet_is_no_order_not_review(tmp_path: Path) -> None:
    position_sizing_path = _write_position_sizing(
        tmp_path,
        {
            "6098": {
                "sizing_status": "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY",
                "target_notional": 5000.0,
                "target_quantity_candidate": 0,
                "quantity_delta_candidate": 0,
                "quantity_status": "NO_ORDER_MINIMUM_NOTIONAL_UNMET",
            }
        },
    )
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, {"6098": ("ADD_CANDIDATE", False)}),
        capital_deployment_artifact_path=None,
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, {}),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(tmp_path, "position"),
        pending_summary=_summary(tmp_path, "pending"),
        planning_config_summary=_summary(tmp_path, "planning_config"),
        position_sizing_artifact_path=position_sizing_path,
    )

    plan = payload["plans"][0]
    assert payload["producer_result_status"] == "PASS"
    assert plan["planning_intent"] == "NO_ORDER"
    assert plan["no_order_reason"] == "NO_ORDER_MINIMUM_NOTIONAL_UNMET"


def test_phase23_ar_runtime_planning_is_pure_mapper_for_same_sizing_output(tmp_path: Path) -> None:
    sizing = {
        "6098": {
            "sizing_status": "SIZED",
            "target_notional": 120000.0,
            "target_quantity_candidate": 100,
            "quantity_delta_candidate": 100,
            "quantity_status": "RESOLVED_CANDIDATE",
        }
    }
    position_sizing_path = _write_position_sizing(tmp_path, sizing)
    first, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path / "a", {"6098": ("ADD_CANDIDATE", False)}),
        capital_deployment_artifact_path=None,
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path / "a"),
        position_management_artifact_path=_write_position_management(tmp_path / "a", {}),
        current_portfolio_summary=_summary(tmp_path / "a", "portfolio"),
        current_cash_summary=_summary(tmp_path / "a", "cash"),
        current_position_summary=_summary(tmp_path / "a", "position"),
        pending_summary=_summary(tmp_path / "a", "pending"),
        planning_config_summary=_summary(tmp_path / "a", "planning_config"),
        position_sizing_artifact_path=position_sizing_path,
    )
    second, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path / "b", {"6098": ("RETAIN", False)}),
        capital_deployment_artifact_path=None,
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path / "b"),
        position_management_artifact_path=_write_position_management(tmp_path / "b", {}),
        current_portfolio_summary=_summary(tmp_path / "b", "portfolio"),
        current_cash_summary=_summary(tmp_path / "b", "cash"),
        current_position_summary=_summary(tmp_path / "b", "position"),
        pending_summary=_summary(tmp_path / "b", "pending"),
        planning_config_summary=_summary(tmp_path / "b", "planning_config"),
        position_sizing_artifact_path=position_sizing_path,
    )

    assert [(p["planning_intent"], p["planned_quantity"]) for p in first["plans"]] == [(p["planning_intent"], p["planned_quantity"]) for p in second["plans"]]


def test_phase24_if_upstream_block_does_not_report_independent_quantity_authority_failures(tmp_path: Path) -> None:
    pc_members = {
        "21340": ("ADD_CANDIDATE", False),
        "37820": ("ADD_CANDIDATE", False),
    }
    pc_path = _write_portfolio_construction(tmp_path, pc_members)
    pc_payload = json.loads(pc_path.read_text(encoding="utf-8"))
    pc_payload.update(
        {
            "source_authority_status": "AUTHORITY_CONFLICT",
            "producer_result_status": "BLOCK",
            "validation_status": "BLOCK",
            "producer_calculation_completed": False,
            "downstream_calculation_eligibility": "CALCULATION_NOT_ALLOWED",
            "decision_resolution": "UNRESOLVED",
            "reason_codes": ["total_target_weight_above_target_gross_exposure"],
        }
    )
    pc_payload["artifact_hash"] = portfolio_construction.portfolio_construction_hash(pc_payload)
    _write_json(pc_path, pc_payload)
    ps_path = _write_position_sizing(
        tmp_path,
        {
            "21340": {"sizing_status": "UPSTREAM_REVIEW_REQUIRED"},
            "37820": {"sizing_status": "UPSTREAM_REVIEW_REQUIRED"},
        },
    )

    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=pc_path,
        capital_deployment_artifact_path=_write_capital_deployment(tmp_path / "cd", pm_actions={}, current_codes=(), pc_members=pc_members),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, {}),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(tmp_path, "position"),
        pending_summary=_summary(tmp_path, "pending"),
        planning_config_summary=_summary(tmp_path, "planning_config"),
        position_sizing_artifact_path=ps_path,
        opportunity_artifact_path=None,
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert "upstream_block:SOURCE_BLOCKED" in payload["reason_codes"]
    assert not any(reason.startswith("review_required_quantity_authority:") for reason in payload["reason_codes"])
    assert all(
        "quantity_not_produced_due_to_upstream_block" in plan["reason_codes"]
        for plan in payload["plans"]
        if plan["security_code"] in {"21340", "37820"}
    )


def test_phase24_ii_position_sizing_block_does_not_report_independent_quantity_authority_failures(tmp_path: Path) -> None:
    pc_members = {
        "21340": ("ADD_CANDIDATE", False),
        "37820": ("ADD_CANDIDATE", False),
    }
    ps_path = _write_position_sizing(tmp_path, {})
    ps_payload = json.loads(ps_path.read_text(encoding="utf-8"))
    ps_payload.update(
        {
            "producer_result_status": "BLOCK",
            "positions": [],
            "reason_codes": ["aggregate_target_weight_above_exposure_cap"],
        }
    )
    _write_json(ps_path, ps_payload)

    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, pc_members),
        capital_deployment_artifact_path=_write_capital_deployment(tmp_path / "cd", pm_actions={}, current_codes=(), pc_members=pc_members),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, {}),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(tmp_path, "position"),
        pending_summary=_summary(tmp_path, "pending"),
        planning_config_summary=_summary(tmp_path, "planning_config"),
        position_sizing_artifact_path=ps_path,
        opportunity_artifact_path=None,
    )

    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert not any(reason.startswith("review_required_quantity_authority:") for reason in payload["reason_codes"])
    assert all(
        "quantity_not_produced_due_to_upstream_block" in plan["reason_codes"]
        for plan in payload["plans"]
        if plan["security_code"] in {"21340", "37820"}
    )


def test_phase22_g_upstream_review_not_eligible_and_block_propagate(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    assert result.payload["producer_result_status"] == "PASS"
    assert "upstream_review_required:SOURCE_NOT_ELIGIBLE" not in result.payload["reason_codes"]
    assert result.payload["consumer_eligibility_reason_codes"] == []
    with pytest.raises(RuntimePlanningConsumerError):
        load_runtime_planning_fixture(result.artifact_path, for_production=True)

    bad_cd = Path(_write_capital_deployment(tmp_path / "bad_cd", pm_actions={"7203": "HOLD"}, current_codes=("7203",)))
    mutated = json.loads(bad_cd.read_text(encoding="utf-8"))
    mutated["members"][0]["allocation_posture"] = "WITHHOLD"
    _write_json(bad_cd, mutated)
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path / "bad_cd", {"7203": ("RETAIN", True)}),
        capital_deployment_artifact_path=bad_cd,
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path / "bad_cd"),
        position_management_artifact_path=_write_position_management(tmp_path / "bad_cd", {"7203": "HOLD"}),
        current_portfolio_summary=_summary(tmp_path / "bad_cd", "portfolio"),
        current_cash_summary=_summary(tmp_path / "bad_cd", "cash"),
        current_position_summary=_summary(tmp_path / "bad_cd", "position", rows=({"security_code": "7203"},)),
        pending_summary=_summary(tmp_path / "bad_cd", "pending"),
        planning_config_summary=_summary(tmp_path / "bad_cd", "planning_config"),
    )
    assert payload["producer_result_status"] == "PASS"
    assert "upstream_block:INCOMPATIBLE_HASH" not in payload["reason_codes"]
    assert payload["upstream_artifacts"]["capital_deployment"]["status"] in {"NON_CANONICAL_OBSERVABILITY", "MERGED_INTO_RUNTIME_PLANNING"}


def test_phase22_g_date_pit_blocks_future_current_and_pending(tmp_path: Path) -> None:
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, {"7203": ("RETAIN", True)}),
        capital_deployment_artifact_path=_write_capital_deployment(tmp_path, pm_actions={"7203": "HOLD"}, current_codes=("7203",)),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, {"7203": "HOLD"}),
        current_portfolio_summary=_summary(tmp_path, "portfolio", feature_date="2026-07-16"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(tmp_path, "position", rows=({"security_code": "7203"},)),
        pending_summary=_summary(tmp_path, "pending"),
        planning_config_summary=_summary(tmp_path, "planning_config"),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert "current_portfolio_date_mismatch" in payload["reason_codes"]
    assert "future_current_or_pending_date_detected" in payload["reason_codes"]
    assert payload["temporal_safety"]["implicit_latest_fallback_used"] is False
    assert payload["temporal_safety"]["previous_day_runtime_planning_copied"] is False


def test_phase22_g_hash_lineage_and_artifact_hash_validation(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert verify_source_hashes(result.payload)["status"] == "PASS"
    assert result.payload["artifact_hash"] == runtime_planning.runtime_planning_hash(result.payload)
    changed = json.loads(json.dumps(result.payload))
    changed["source_hashes"][0]["sha256"] = "deadbeef"
    assert verify_source_hashes(changed)["status"] == "BLOCK"


def test_phase22_g_bootstrap_missing_inputs_does_not_use_fixed_fallbacks(tmp_path: Path) -> None:
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=None,
        capital_deployment_artifact_path=None,
        portfolio_policy_artifact_path=None,
        position_management_artifact_path=None,
        current_portfolio_summary=_summary(tmp_path, "portfolio", status="REVIEW_REQUIRED"),
        current_cash_summary=_summary(tmp_path, "cash", status="REVIEW_REQUIRED"),
        current_position_summary=_summary(tmp_path, "position", status="REVIEW_REQUIRED"),
        pending_summary=_summary(tmp_path, "pending", status="REVIEW_REQUIRED"),
        planning_config_summary=_summary(tmp_path, "planning_config", status="REVIEW_REQUIRED"),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert payload["plans"] == []
    assert payload["temporal_safety"]["implicit_latest_fallback_used"] is False
    assert payload["temporal_safety"]["previous_day_runtime_planning_copied"] is False


def test_phase26_step5_runtime_planning_authority_switch_contract(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    payload = load_runtime_planning_fixture(result.artifact_path)

    assert payload["production_consumer_connected"] is False
    assert payload["pending_writer_connected"] is True
    assert payload["runtime_switch_performed"] is True
    assert payload["legacy_authority_active"] is False
    assert payload["legacy_planning_authority_used"] is False
    assert payload["planning_fallback_used"] is False
    assert payload["planning_config_authority_used"] is False
    assert payload["planning_authority_winner"] == "strategy_runtime_planning"
    assert payload["existing_morning_planning_changed"] is True
    assert payload["existing_add_planning_changed"] is True
    assert payload["existing_sell_planning_changed"] is False
    assert payload["pending_changed"] is True
    assert payload["approval_changed"] is False
    assert payload["submit_changed"] is False
    assert payload["execution_changed"] is False
    evidence = runtime_planning.produced_but_not_consumed_evidence(payload)
    assert evidence["runtime_planning_production_consumer_connected"] is True
    assert evidence["pending_written"] is True
    assert evidence["pending_changed"] is True
    assert evidence["submit_generated"] is False


def _produce(
    tmp_path: Path,
    *,
    pm_actions: dict[str, str] | None = None,
    pc_members: dict[str, tuple[str, bool]] | None = None,
    position_sizing_positions: dict[str, dict[str, object]] | None = None,
    opportunity_artifact_path: Path | str | None = None,
    current_codes: tuple[str, ...] = ("7203",),
    current_position_rows: tuple[dict[str, object], ...] | None = None,
    pending_codes: tuple[str, ...] = (),
):
    pm_actions = pm_actions or {"7203": "HOLD", "6098": "HOLD"}
    pc_members = pc_members or {"7203": ("RETAIN", True), "6098": ("ADD_CANDIDATE", False)}
    position_sizing_path = _write_position_sizing(tmp_path, position_sizing_positions) if position_sizing_positions is not None else None
    return runtime_planning.produce_runtime_planning_artifact(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, pc_members),
        capital_deployment_artifact_path=_write_capital_deployment(tmp_path, pm_actions=pm_actions, current_codes=current_codes, pc_members=pc_members),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, pm_actions),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(
            tmp_path,
            "position",
            rows=current_position_rows if current_position_rows is not None else tuple({"security_code": code} for code in current_codes),
        ),
        pending_summary=_summary(tmp_path, "pending", rows=tuple({"security_code": code} for code in pending_codes)),
        planning_config_summary=_summary(tmp_path, "planning_config"),
        position_sizing_artifact_path=position_sizing_path,
        opportunity_artifact_path=opportunity_artifact_path,
        output_path=default_runtime_artifact_path(tmp_path / ".runtime", "2026-07-15"),
    )


def _runtime_owned_current_position_row(
    symbol: str,
    *,
    quantity: int,
    as_of: str,
    source: str,
    filled_quantity: int | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "symbol": symbol,
        "security_code": symbol,
        "quantity": quantity,
        "average_price": 130.0,
        "market_value": float(quantity) * 130.0,
        "as_of": as_of,
        "valuation_as_of": as_of,
        "source_market_date": as_of,
        "source": source,
        "position_id": f"runtime-current-{symbol}",
        "position_campaign_id": f"pc-test-{symbol}",
    }
    if filled_quantity is not None:
        row["filled_quantity"] = filled_quantity
    return row


def _summary(
    tmp_path: Path,
    kind: str,
    *,
    status: str = "PASS",
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
    rows: tuple[dict[str, object], ...] = (),
) -> RuntimePlanningSourceSummary:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / f"{kind}_summary.json"
    payload = {"kind": kind, "business_date": business_date, "feature_date": feature_date, "status": status, "rows": list(rows)}
    _write_json(path, payload)
    return RuntimePlanningSourceSummary(status, business_date, feature_date, str(path), _sha256_file(path), rows)


def _write_capital_deployment(
    tmp_path: Path,
    *,
    pm_actions: dict[str, str],
    current_codes: tuple[str, ...],
    pc_members: dict[str, tuple[str, bool]] | None = None,
) -> Path:
    return capital_deployment.produce_capital_deployment_artifact(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, pc_members or {code: ("RETAIN", True) for code in set(pm_actions) | set(current_codes)}),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, pm_actions),
        current_cash_summary=capital_deployment.CapitalDeploymentSourceSummary("PASS", "2026-07-15", "2026-07-15", str(_write_source(tmp_path, "cash_cd")), _sha256_file(_write_source(tmp_path, "cash_cd")), {}),
        current_exposure_summary=capital_deployment.CapitalDeploymentSourceSummary("PASS", "2026-07-15", "2026-07-15", str(_write_source(tmp_path, "exposure_cd")), _sha256_file(_write_source(tmp_path, "exposure_cd")), {}),
        current_portfolio_summary=capital_deployment.CapitalDeploymentSourceSummary("PASS", "2026-07-15", "2026-07-15", str(_write_source(tmp_path, "portfolio_cd")), _sha256_file(_write_source(tmp_path, "portfolio_cd")), {}),
        pending_reservation_summary=capital_deployment.CapitalDeploymentSourceSummary("PASS", "2026-07-15", "2026-07-15", str(_write_source(tmp_path, "pending_cd")), _sha256_file(_write_source(tmp_path, "pending_cd")), {}),
        policy_config_summary=capital_deployment.CapitalDeploymentSourceSummary("PASS", "2026-07-15", "2026-07-15", str(_write_source(tmp_path, "policy_config_cd")), _sha256_file(_write_source(tmp_path, "policy_config_cd")), {}),
        output_path=tmp_path / "capital_deployment.json",
    ).artifact_path


def _write_portfolio_construction(tmp_path: Path, members: dict[str, tuple[str, bool]]) -> Path:
    source = _write_source(tmp_path, "pc_source")
    selected_codes = {
        code
        for code, (intent, _) in members.items()
        if intent in {"ADD_CANDIDATE", "RETAIN"}
    }
    base_weight = round(0.8 / len(selected_codes), 6) if selected_codes else 0.0
    payload = {
        "schema_version": portfolio_construction.SCHEMA_VERSION,
        "producer_version": "phase22_e_portfolio_construction_producer.v1",
        "business_date": "2026-07-15",
        "as_of": "2026-07-15T00:00:00+00:00",
        "feature_date": "2026-07-15",
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "REVIEW_REQUIRED",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "portfolio_members": [
            {
                "member_id": f"pc-{code}",
                "security_code": code,
                "symbol": code,
                "current_position": current,
                "membership_intent": intent,
                "target_membership": code in selected_codes,
                "target_weight": base_weight if code in selected_codes else 0.0,
                "target_weight_authority": {
                    "authority_type": "TARGET_WEIGHT_AUTHORITY",
                    "method_id": "test_production_v1_equal_weight_target_allocation",
                    "method_version": "phase23_ao_test_v1",
                    "business_date": "2026-07-15",
                    "target_gross_exposure": 0.8,
                    "resolved_target_member_count": len(selected_codes),
                    "single_name_weight_cap": 0.25,
                    "portfolio_policy_reference": "policy",
                    "dynamic_position_count_reference": "dynamic-position-count-test",
                    "opportunity_reference": f"opportunity-{code}" if intent == "ADD_CANDIDATE" else "",
                    "existing_position_reference": f"pm-{code}" if current else "",
                    "position_management_reference": f"pm-{code}" if current else "",
                    "source_artifact_paths": [str(source)],
                    "source_artifact_hashes": [{"role": "pc", "path": str(source), "sha256": _sha256_file(source)}],
                    "PIT_status": "PASS",
                },
                "target_weight_resolution": {
                    "status": "PASS",
                    "reason": "target_weight_resolved" if code in selected_codes else "opportunity_not_selected",
                    "resolved_weight": base_weight if code in selected_codes else 0.0,
                    "base_weight": base_weight,
                    "adjustments": [],
                    "cap_applied": False,
                    "normalization_applied": False,
                    "zero_weight_reason": "" if code in selected_codes else "opportunity_not_selected",
                    "review_reason": "",
                },
                "construction_priority": index,
                "weight_intent": "MAINTAIN" if intent == "RETAIN" else ("AVOID" if intent == "EXCLUDE" else "INCREASE"),
                "candidate_reference": f"candidate-{code}" if intent == "ADD_CANDIDATE" else "",
                "opportunity_reference": f"opportunity-{code}" if intent == "ADD_CANDIDATE" else "",
                "position_management_reference": f"pm-{code}" if current else "",
                "portfolio_policy_reference": "",
                "membership_reason": "fixture",
                "weight_reason": "target_weight_resolved" if code in selected_codes else "opportunity_not_selected",
                "confidence": 0.8,
                "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
                "reason_codes": ["fixture"],
            }
            for index, (code, (intent, current)) in enumerate(sorted(members.items()), start=1)
        ],
        "member_count": len(members),
        "membership_intent_taxonomy": sorted(portfolio_construction.MEMBERSHIP_INTENTS),
        "weight_intent_taxonomy": sorted(portfolio_construction.WEIGHT_INTENTS),
        "position_count_policy_reference": "policy",
        "cash_policy_reference": "policy",
        "exposure_policy_reference": "policy",
        "target_weight_method": {
            "method_id": "test_production_v1_equal_weight_target_allocation",
            "method_version": "phase23_ao_test_v1",
            "basis": "target_gross_exposure / resolved_target_member_count with single-name cap",
            "opportunity_score_weight_transform_used": False,
        },
        "target_gross_exposure": 0.8,
        "resolved_target_member_count": len(selected_codes),
        "single_name_weight_cap": 0.25,
        "total_target_weight": round(sum(base_weight for _ in selected_codes), 6),
        "concrete_values_decided": False,
        "position_count_decided": False,
        "cash_ratio_decided": False,
        "exposure_decided": False,
        "position_sizing_decided": False,
        "allocation_decided": False,
        "quantity_decided": False,
        "reason_codes": ["upstream_review_required:SOURCE_NOT_ELIGIBLE"],
        "upstream_artifacts": {},
        "source_artifacts": [{"role": "pc", "path": str(source), "required": True, "status": "PASS"}],
        "source_hashes": [{"role": "pc", "path": str(source), "sha256": _sha256_file(source)}],
        "temporal_safety": {"point_in_time": True, "future_leakage_used": False, "feature_date_lte_business_date": True, "implicit_latest_fallback_used": False, "previous_day_portfolio_construction_copied": False},
        "production_consumer_connected": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
    }
    payload["artifact_hash"] = portfolio_construction.portfolio_construction_hash(payload)
    path = tmp_path / "portfolio_construction.json"
    _write_json(path, payload)
    return path


def _write_portfolio_policy(tmp_path: Path) -> Path:
    source = _write_source(tmp_path, "policy_source")
    payload = {
        "schema_version": portfolio_policy.SCHEMA_VERSION,
        "producer_version": "phase22_c_portfolio_policy_producer.v1",
        "business_date": "2026-07-15",
        "as_of": "2026-07-15T00:00:00+00:00",
        "feature_date": "2026-07-15",
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "REVIEW_REQUIRED",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "risk_posture": "BALANCED",
        "entry_posture": "MAINTAIN",
        "position_count_posture": "MAINTAIN",
        "cash_posture": "MAINTAIN",
        "exposure_posture": "MAINTAIN",
        "position_management_bias": "NEUTRAL",
        "target_position_count_resolution": "RESOLVED",
        "target_position_count": 2,
        "target_gross_exposure_ratio_resolution": "RESOLVED",
        "target_gross_exposure_ratio": 0.8,
        "target_gross_exposure": 0.8,
        "cash_reserve_ratio_resolution": "RESOLVED",
        "cash_reserve_ratio": 0.2,
        "cash_reserve": 0.2,
        "single_name_weight_cap": 0.25,
        "single_name_weight_cap_source": "fixture#single_name_weight_cap",
        "single_name_weight_cap_authority": {"status": "PASS", "source": "fixture#single_name_weight_cap", "single_name_weight_cap": 0.25},
        "deployment_posture": "BALANCED_DEPLOYMENT",
        "confidence": 0.0,
        "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
        "reason_codes": ["upstream_review_required:SOURCE_NOT_ELIGIBLE"],
        "deferred_concrete_values": [],
        "concrete_values_decided": False,
        "upstream_artifacts": {},
        "source_artifacts": [{"role": "policy", "path": str(source), "required": True, "status": "PASS"}],
        "source_hashes": [{"role": "policy", "path": str(source), "sha256": _sha256_file(source)}],
        "temporal_safety": {"point_in_time": True, "future_leakage_used": False, "feature_date_lte_business_date": True, "implicit_latest_fallback_used": False, "previous_day_policy_copied": False},
    }
    payload["artifact_hash"] = portfolio_policy.portfolio_policy_hash(payload)
    path = tmp_path / "portfolio_policy.json"
    _write_json(path, payload)
    return path


def _write_position_management(tmp_path: Path, actions: dict[str, str]) -> Path:
    source = _write_source(tmp_path, "pm_source")
    payload = {
        "schema_version": position_management.SCHEMA_VERSION,
        "producer_version": "phase22_d_position_management_producer.v1",
        "business_date": "2026-07-15",
        "as_of": "2026-07-15T00:00:00+00:00",
        "feature_date": "2026-07-15",
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "REVIEW_REQUIRED",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "positions": [
            {
                "position_id": f"pm-{code}",
                "security_code": code,
                "action": action,
                "intensity": "NONE" if action in {"HOLD", "ADD", "EXIT"} else "MEDIUM",
                "confidence": 0.8,
                "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
                "reason_codes": ["fixture"],
                "lifecycle_reference": "",
                "opportunity_reference": "",
                "market_context_reference": "",
                "corporate_event_reference": "",
                "portfolio_policy_reference": "",
            }
            for code, action in sorted(actions.items())
        ],
        "position_count": len(actions),
        "action_taxonomy": sorted(position_management.PM_ACTIONS),
        "intensity_taxonomy": sorted(position_management.PM_INTENSITIES),
        "quantity_decided": False,
        "minimum_holding_decided": False,
        "cooldown_decided": False,
        "reason_codes": ["upstream_review_required:SOURCE_NOT_ELIGIBLE"],
        "upstream_artifacts": {},
        "accepted_generation_reference": {},
        "model_reference": {},
        "scaler_reference": {},
        "source_artifacts": [{"role": "pm", "path": str(source), "required": True, "status": "PASS"}],
        "source_hashes": [{"role": "pm", "path": str(source), "sha256": _sha256_file(source)}],
        "temporal_safety": {"point_in_time": True, "future_leakage_used": False, "feature_date_lte_business_date": True, "implicit_latest_fallback_used": False, "previous_day_pm_artifact_copied": False},
        "production_consumer_connected": False,
        "existing_pm_authority_active": True,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
    }
    payload["artifact_hash"] = position_management.position_management_hash(payload)
    path = tmp_path / "position_management.json"
    _write_json(path, payload)
    return path


def _write_source(tmp_path: Path, name: str) -> Path:
    path = tmp_path / f"{name}.json"
    _write_json(path, {"source": name})
    return path


def _write_position_sizing(
    tmp_path: Path,
    positions: dict[str, dict[str, object]],
    *,
    current_position_rows: tuple[dict[str, object], ...] | None = None,
) -> Path:
    source = _write_source(tmp_path, "position_sizing_source")
    def canonical(item: dict[str, object]) -> dict[str, object]:
        if "target_quantity_candidate" in item and "quantity_delta_candidate" in item and "quantity_status" in item:
            return item
        status = str(item.get("sizing_status") or "")
        if status == "RESOLVED_ZERO_ALLOCATION":
            return {**item, "target_quantity_candidate": 0, "quantity_delta_candidate": 0, "quantity_status": "RESOLVED_ZERO_DELTA"}
        if status in {"NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY", "MINIMUM_NOTIONAL_UNMET"}:
            return {**item, "target_quantity_candidate": 0, "quantity_delta_candidate": 0, "quantity_status": "NO_ORDER_MINIMUM_NOTIONAL_UNMET"}
        if status in {"SIZED", "CAPPED"}:
            return {**item, "target_quantity_candidate": 100, "quantity_delta_candidate": 100, "quantity_status": "RESOLVED_CANDIDATE"}
        return item
    payload = {
        "schema_version": "position_sizing.v1",
        "producer_result_status": "PASS",
        "business_date": "2026-07-15",
        "feature_date": "2026-07-15",
        "positions": [
            {
                "security_code": code,
                "position_reference": f"ps-{code}",
                "current_notional": 0.0,
                "incremental_target_notional": item.get("incremental_target_notional", item.get("target_notional", 0.0)),
                "reference_price": item.get("reference_price", 1000.0),
                "reference_price_authority": item.get(
                    "reference_price_authority",
                    {
                        "authority_type": "REFERENCE_PRICE_AUTHORITY",
                        "business_date": "2026-07-15",
                        "canonical_field": "reference_price",
                        "latest_fallback_used": False,
                        "price_date": "2026-07-15",
                        "price_type": "planning_reference_close",
                        "PIT_status": "PASS",
                        "source_authority": "MARKET_EVIDENCE_AUTHORITY",
                        "source_field": "close",
                        "symbol": code,
                    },
                ),
                "reference_price_resolution": item.get(
                    "reference_price_resolution",
                    {
                        "status": "PASS",
                        "reason": "reference_price_resolved",
                        "resolved_price": item.get("reference_price", 1000.0),
                        "review_reason": "",
                    },
                ),
                "reference_price_type": item.get("reference_price_type", "planning_reference_close"),
                "reference_price_date": item.get("reference_price_date", "2026-07-15"),
                **canonical(item),
            }
            for code, item in sorted(positions.items())
        ],
        "current_position_rows": list(current_position_rows or ()),
        "source_hashes": [{"role": "position_sizing", "path": str(source), "sha256": _sha256_file(source)}],
    }
    path = tmp_path / "position_sizing.json"
    _write_json(path, payload)
    return path


def _write_position_sizing_plan(tmp_path: Path, positions: dict[str, dict[str, object]]) -> Path:
    source = _write_source(tmp_path, "position_sizing_plan_source")

    def status_for(item: dict[str, object]) -> str:
        delta = item.get("quantity_delta_candidate")
        if delta is None:
            return str(item.get("sizing_status") or "ADD_NOT_SIZED")
        return str(item.get("sizing_status") or "SIZED")

    payload = {
        "schema_version": "position_sizing_plan.v1",
        "artifact_status": "PASS",
        "business_date": "2026-07-15",
        "authority_mode": "SHADOW",
        "decision_effect": "NONE",
        "positions": [
            {
                "position_sizing_plan_id": f"psp-{code}",
                "symbol": code,
                "source_position_intent": item.get("source_pm_intent", "HOLD"),
                "source_pm_intent": item.get("source_pm_intent", "HOLD"),
                "current_quantity": item.get("current_quantity", 100),
                "target_quantity_candidate": item.get("target_quantity_candidate"),
                "quantity_delta_candidate": item.get("quantity_delta_candidate"),
                "orderable_quantity_delta": item.get("quantity_delta_candidate"),
                "lot_rounding_result": "UNCHANGED",
                "sizing_status": status_for(item),
                "reason_codes": ["fixture"],
                "lineage": {
                    "authority": "PHASE27_D2D_POSITION_SIZING_PLAN",
                    "source_target_portfolio_decision_id": f"tpd-{code}",
                    "source_position_intent_id": f"pi-{code}",
                    "decision_effect": "NONE",
                },
                "reference_price": item.get("reference_price", 1000.0),
                "reference_price_authority": item.get(
                    "reference_price_authority",
                    {
                        "authority_type": "REFERENCE_PRICE_AUTHORITY",
                        "business_date": "2026-07-15",
                        "canonical_field": "reference_price",
                        "latest_fallback_used": False,
                        "price_date": "2026-07-15",
                        "price_type": "planning_reference_close",
                        "PIT_status": "PASS",
                        "source_authority": "MARKET_EVIDENCE_AUTHORITY",
                        "source_field": "close",
                        "symbol": code,
                    },
                ),
                "reference_price_resolution": item.get(
                    "reference_price_resolution",
                    {
                        "status": "PASS",
                        "reason": "reference_price_resolved",
                        "resolved_price": item.get("reference_price", 1000.0),
                        "review_reason": "",
                    },
                ),
                "reference_price_type": item.get("reference_price_type", "planning_reference_close"),
                "reference_price_date": item.get("reference_price_date", "2026-07-15"),
            }
            for code, item in sorted(positions.items())
        ],
        "source_hashes": [{"role": "position_sizing_plan", "path": str(source), "sha256": _sha256_file(source)}],
    }
    path = tmp_path / "position_sizing_plan.json"
    _write_json(path, payload)
    return path


def _write_opportunity_rankings(tmp_path: Path, rows: list[dict[str, object]], metadata: dict[str, object] | None = None) -> Path:
    payload = {
        "schema_version": "runtime_v2_opportunity_ranking_v1",
        "schema_name": "runtime_v2_buy_opportunity_ranking",
        "artifact_role": "BUY_OPPORTUNITY_RANKING",
        "business_date": "2026-07-15",
        "feature_date": "2026-07-15",
        **(metadata or {}),
        "rankings": [
            {
                "business_date": "2026-07-15",
                "feature_date": "2026-07-15",
                "target_date": "2026-07-15",
                "symbol": str(row.get("symbol") or row.get("code") or ""),
                "code": str(row.get("symbol") or row.get("code") or ""),
                "rank": row.get("rank", index),
                "buy_rank": row.get("buy_rank", row.get("rank", index)),
                "runtime_opportunity_score": row.get("runtime_opportunity_score", row.get("expected_edge_score", 0.1)),
                "expected_edge_score": row.get("expected_edge_score", 0.1),
                "expected_return": row.get("expected_return", row.get("expected_edge_score", 0.1)),
                "no_buy_reason": str(row.get("no_buy_reason") or ""),
                **{
                    key: row[key]
                    for key in (
                        "canonical_score_field",
                        "score_semantic_role",
                        "calibration_applied",
                        "economic_units_available",
                    )
                    if key in row
                },
                "model_version": "test-opportunity-model",
            }
            for index, row in enumerate(rows, start=1)
        ],
    }
    path = tmp_path / "opportunity_rankings.json"
    _write_json(path, payload)
    return path


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
