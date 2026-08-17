from __future__ import annotations

from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy import portfolio_construction, position_sizing
from ai_fund_lab_v2.strategy.position_sizing import (
    PositionSizingConsumerError,
    produce_position_sizing_artifact,
)

from tests.strategy.test_phase22_e_portfolio_construction import (
    _build_d28_payload,
    _opportunity_row,
    _pm_row,
    _produce as _produce_pc,
)
from tests.strategy.test_phase22_g_runtime_planning import _produce as _produce_runtime_plan
from tests.strategy.test_phase22_j_position_sizing import (
    _config,
    _reference_price_contract,
    _row,
    _safety,
    _summary,
    _with_target_weights,
)


def test_phase30_s_final_pc_promotes_only_pass_lot_aware_allocation(tmp_path: Path) -> None:
    payload = _produce_pc(tmp_path).payload
    final = portfolio_construction.promote_final_portfolio_construction_for_production(
        {
            **payload,
            "producer_result_status": "PASS",
            "portfolio_construction_stage": "FINAL_LOT_AWARE_REALLOCATION",
            "lot_aware_final_reallocation": {"status": "PASS"},
        }
    )

    assert final["producer_result_status"] == "PASS"
    assert final["artifact_lifecycle_status"] == "ACCEPTED"
    assert final["runtime_consumer_eligibility"] == "ELIGIBLE"
    assert final["allocation_decided"] is True
    assert final["quantity_decided"] is False
    assert final["production_consumer_connected"] is True
    assert final["legacy_authority_active"] is False
    assert final["downstream_calculation_eligibility"] == "CALCULATION_ALLOWED"
    assert portfolio_construction.validate_portfolio_construction_artifact(final)["status"] == "PASS"


def test_phase30_s_final_pc_review_required_remains_fail_closed(tmp_path: Path) -> None:
    payload = _produce_pc(tmp_path).payload
    final = portfolio_construction.promote_final_portfolio_construction_for_production(
        {
            **payload,
            "producer_result_status": "REVIEW_REQUIRED",
            "portfolio_construction_stage": "FINAL_LOT_AWARE_REALLOCATION",
            "lot_aware_final_reallocation": {"status": "REVIEW_REQUIRED"},
        }
    )

    assert final["artifact_lifecycle_status"] == "DRAFT"
    assert final["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert final["allocation_decided"] is False
    assert final["production_consumer_connected"] is False
    assert final["legacy_authority_active"] is True
    assert final["downstream_calculation_eligibility"] == "CALCULATION_ALLOWED_WITH_REVIEW"
    assert portfolio_construction.validate_portfolio_construction_artifact(final)["status"] == "PASS"


def test_phase30_s_pc_positive_weight_to_ps_positive_quantity_to_runtime_buy_new(tmp_path: Path) -> None:
    ps_result = _produce_ps(
        tmp_path,
        rows=[_row("6098", score=0.9, volatility=0.03, price=500.0, membership="ADD_CANDIDATE", pm_action="NEW")],
        production_consumer_connected=True,
    )
    payload = ps_result.payload
    position = payload["positions"][0]

    assert payload["producer_result_status"] == "PASS"
    assert payload["artifact_lifecycle_status"] == "ACCEPTED"
    assert payload["runtime_consumer_eligibility"] == "ELIGIBLE"
    assert payload["share_quantity_decided"] is True
    assert payload["lot_rounding_decided"] is True
    assert position["target_weight"] > 0
    assert position["target_quantity_candidate"] > 0
    assert position["quantity_delta_candidate"] > 0
    assert position["quantity_status"] == "RESOLVED_CANDIDATE"
    assert position_sizing.load_position_sizing_fixture(ps_result.artifact_path, for_production=True)["share_quantity_decided"] is True

    runtime = _produce_runtime_plan(
        tmp_path / "runtime",
        pm_actions={"6098": "HOLD"},
        pc_members={"6098": ("ADD_CANDIDATE", False)},
        position_sizing_positions={"6098": position},
        current_codes=(),
    ).payload
    plan = runtime["plans"][0]
    assert plan["planning_intent"] == "BUY_NEW"
    assert plan["order_side_intent"] == "BUY"
    assert plan["planned_quantity"] > 0


def test_phase30_ae1_pm_pc_ps_runtime_canonical_campaign_buy_add_e2e(tmp_path: Path) -> None:
    (tmp_path / "pc").mkdir()
    pc_payload = _build_d28_payload(
        tmp_path / "pc",
        current_rows=[
            {
                "position_id": "current-11110",
                "security_code": "11110",
                "current_weight": 0.05,
                "quantity": 100,
                "current_quantity": 100,
                "reference_price": 500.0,
            }
        ],
        pm_rows=[
            {
                **_pm_row("11110", "ADD"),
                "lifecycle_reference": "runtime-current-11110",
                "strategy_intelligence_campaign_id": "pc-canonical-11110-0001",
                "strategy_intelligence_add_worthiness_state": "ADD_ALLOWED",
                "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
                "entry_admission_action": "ADD_ALLOWED",
                "reason_codes": ["strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"],
            }
        ],
        opportunity_rows=[
            _opportunity_row(
                "11110",
                1,
                0.82,
                position_campaign_id="pc-canonical-11110-0001",
                expected_edge_baseline_score=0.70,
                expected_edge_baseline_business_date="2026-07-14",
                expected_edge_baseline_campaign_id="pc-canonical-11110-0001",
                incremental_investment_value_state="POSITIVE",
                opportunity_cost_status="PASS",
                reference_price=500.0,
                **_reference_price_contract("11110", 500.0),
            )
        ],
        exposure=0.16,
        cap=0.16,
    )
    pc_member = next(row for row in pc_payload["portfolio_members"] if row["security_code"] == "11110")
    assert pc_member["add_investment_evidence"]["campaign_continuation"]["status"] == "PASS"
    assert pc_member["target_weight_change"] > 0

    ps_result = _produce_ps(
        tmp_path / "ps",
        rows=[pc_member],
        target_count=1,
        exposure=0.16,
        production_consumer_connected=True,
    )
    ps_position = ps_result.payload["positions"][0]
    assert ps_position["pm_action"] == "ADD"
    assert ps_position["quantity_delta_candidate"] > 0

    runtime = _produce_runtime_plan(
        tmp_path / "runtime",
        pm_actions={"11110": "ADD"},
        pc_members={"11110": ("RETAIN", True)},
        position_sizing_positions={"11110": ps_position},
        current_codes=("11110",),
    ).payload
    plan = runtime["plans"][0]
    assert plan["planning_intent"] == "BUY_ADD"
    assert plan["order_side_intent"] == "BUY"
    assert plan["planned_quantity"] == ps_position["quantity_delta_candidate"]


def test_phase30_s_pc_review_required_keeps_ps_not_eligible_and_unresolved(tmp_path: Path) -> None:
    ps_result = _produce_ps(
        tmp_path,
        rows=[_row("6098", score=0.9, volatility=0.03, price=500.0)],
        pc_status="REVIEW_REQUIRED",
        production_consumer_connected=True,
    )
    payload = ps_result.payload

    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert payload["share_quantity_decided"] is False
    assert payload["positions"][0]["sizing_status"] == "UPSTREAM_REVIEW_REQUIRED"
    assert "quantity_delta_candidate" not in payload["positions"][0]
    with pytest.raises(PositionSizingConsumerError):
        position_sizing.load_position_sizing_fixture(ps_result.artifact_path, for_production=True)


def test_phase30_s_lot_too_expensive_does_not_force_buy(tmp_path: Path) -> None:
    ps_result = _produce_ps(
        tmp_path,
        rows=[_row("9001", score=0.9, volatility=0.03, price=50_000.0)],
        production_consumer_connected=True,
        portfolio_value=100_000.0,
        exposure=0.05,
    )
    position = ps_result.payload["positions"][0]

    assert ps_result.payload["producer_result_status"] == "PASS"
    assert ps_result.payload["runtime_consumer_eligibility"] == "ELIGIBLE"
    assert position["target_weight"] > 0
    assert position["target_quantity_candidate"] == 0
    assert position["quantity_delta_candidate"] == 0
    assert position["quantity_status"] == "RESOLVED_ZERO_DELTA"


def test_phase30_ak7r_ps_consumes_pc_positive_executable_quantity_authority(tmp_path: Path) -> None:
    row = _row("77775", score=0.9, volatility=0.03, price=100.0, membership="RETAIN", pm_action="ADD", current_weight=0.01)
    row.update(
        {
            "current_position": True,
            "current_quantity": 100,
            "target_weight": 0.019,
            "requested_incremental_weight": 0.009,
            "accepted_incremental_weight": 0.009,
            "lot_aware_accepted_incremental_weight": 0.009,
            "add_allocation_eligibility_status": "PASS",
            "incremental_investment_value_state": "POSITIVE",
            "opportunity_cost_status": "PASS",
            "entry_admission_action": "ADD_ALLOWED",
            "strategy_intelligence_add_worthiness_state": "ADD_ALLOWED",
        }
    )
    row["target_weight_resolution"] = {
        "status": "PASS",
        "reason": "lot_aware_final_reallocation",
        "resolved_weight": 0.019,
        "adjustments": [],
        "lot_aware_final_reallocation": {
            "authority_type": "PORTFOLIO_CONSTRUCTION_LOT_AWARE_FINAL_REALLOCATION",
            "accepted_lot_increment_weight": 0.009,
            "pc_positive_executable_quantity_authority": {
                "authority_type": "PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY",
                "status": "PASS",
                "final_allocated_quantity": 100,
                "accepted_lot_increment_weight": 0.009,
                "ps_must_consume_canonical_quantity": True,
                "future_information_used": False,
            },
            "phase29_l19_lot_resolution": {
                "semantic_type": "BUY_ADD",
                "one_lot_quantity": 100,
                "one_lot_weight": 0.01,
                "one_lot_notional": 10_000.0,
                "final_allocated_quantity": 100,
                "safety_hard_cap": 0.25,
                "safety_hard_cap_weight": 0.25,
                "post_trade_weight": 0.02,
                "safety_hard_cap_preserved": True,
                "pc_positive_executable_quantity_authority": {
                    "authority_type": "PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY",
                    "status": "PASS",
                    "final_allocated_quantity": 100,
                    "accepted_lot_increment_weight": 0.009,
                    "ps_must_consume_canonical_quantity": True,
                    "future_information_used": False,
                },
            },
        },
    }
    row["target_weight_authority"]["single_name_weight_cap"] = 0.25

    position = position_sizing._raw_position(
        row,
        config=_config(),
        base=0.0,
        max_weight=0.25,
        portfolio_value=1_000_000.0,
        safety_cap=0.25,
    )

    assert position["quantity_delta_candidate"] == 100
    assert position["final_target_quantity"] == 200
    assert position["pc_discrete_quantity_authority_consumed"] is True
    assert "PC_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY_CONSUMED" in position["reason_codes"]


def test_phase30_s_ps_consumes_pc_buy_quality_reason_code_without_rethresholding(tmp_path: Path) -> None:
    row = _row("6659", score=0.78, volatility=0.03, price=500.0)
    for field in ("quality_action", "quality_status", "quality_decision_id", "quality_allocation_adjustment"):
        row.pop(field, None)
    row["reason_codes"] = ["buy_quality_full_allocation_eligible", "strategy_intelligence_buy_evidence_pass"]

    ps_result = _produce_ps(tmp_path, rows=[row], production_consumer_connected=True)
    position = ps_result.payload["positions"][0]

    assert ps_result.payload["producer_result_status"] == "PASS"
    assert position["quality_action"] == "FULL_ALLOCATION_ELIGIBLE"
    assert "buy_quality_action_resolved_from_portfolio_construction_reason_code" in position["quality_reason_codes"]
    assert position["target_quantity_candidate"] > 0


def test_phase30_s_safety_block_remains_not_eligible(tmp_path: Path) -> None:
    ps_result = _produce_ps(
        tmp_path,
        rows=[_row("6098", score=0.9, volatility=0.03, price=500.0)],
        safety_status="BLOCK",
        production_consumer_connected=True,
    )

    assert ps_result.payload["producer_result_status"] == "BLOCK"
    assert ps_result.payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert ps_result.payload["share_quantity_decided"] is False


def test_phase30_s_sell_and_no_action_semantics_are_independent(tmp_path: Path) -> None:
    rows = [
        _row("7203", score=0.7, volatility=0.03, price=1000.0, membership="RETAIN", pm_action="HOLD", current_weight=0.16),
        _row("8306", score=0.7, volatility=0.03, price=1000.0, membership="REDUCE_CANDIDATE", pm_action="REDUCE", current_weight=0.30),
    ]
    rows[0]["current_quantity"] = 100
    rows[0]["target_weight"] = 0.16
    rows[0]["target_weight_resolution"]["resolved_weight"] = 0.16
    rows[1]["current_quantity"] = 300
    rows[1]["target_weight"] = 0.10
    rows[1]["target_weight_resolution"]["resolved_weight"] = 0.10
    ps_result = _produce_ps(tmp_path, rows=rows, target_count=2, exposure=0.26, production_consumer_connected=True)
    by_code = {item["security_code"]: item for item in ps_result.payload["positions"]}

    assert by_code["7203"]["quantity_delta_candidate"] == 0
    assert by_code["8306"]["quantity_delta_candidate"] < 0


def test_phase30_s_production_position_sizing_is_idempotent(tmp_path: Path) -> None:
    kwargs = {
        "rows": [_row("6098", score=0.9, volatility=0.03, price=500.0)],
        "production_consumer_connected": True,
    }
    first = _produce_ps(tmp_path / "first", **kwargs).payload
    second = _produce_ps(tmp_path / "second", **kwargs).payload

    assert first["positions"] == second["positions"]
    assert first["total_target_weight"] == second["total_target_weight"]
    assert first["share_quantity_decided"] is True
    assert second["share_quantity_decided"] is True


def _produce_ps(
    tmp_path: Path,
    *,
    rows: list[dict[str, object]],
    target_count: int = 1,
    exposure: float = 0.16,
    pc_status: str = "PASS",
    safety_status: str = "PASS",
    production_consumer_connected: bool,
    portfolio_value: float = 1_000_000.0,
):
    tmp_path.mkdir(parents=True, exist_ok=True)
    sizing_rows = _with_target_weights(rows, target_count=target_count, exposure=exposure)
    return produce_position_sizing_artifact(
        business_date="2026-07-15",
        portfolio_construction_summary=_summary(tmp_path, "pc", status=pc_status, rows=sizing_rows),
        capital_deployment_summary=_summary(
            tmp_path,
            "cd",
            status="REVIEW_REQUIRED",
            summary={"reason": "capital_deployment_is_downstream_of_position_sizing_in_shadow_chain"},
        ),
        dynamic_position_count_summary=_summary(tmp_path, "dpc", summary={"target_position_count": target_count}),
        dynamic_cash_exposure_summary=_summary(tmp_path, "dce", summary={"target_gross_exposure_ratio": exposure}),
        position_management_summary=_summary(tmp_path, "pm"),
        opportunity_summary=_summary(tmp_path, "opp"),
        current_position_summary=_summary(tmp_path, "cur", summary={"portfolio_value": portfolio_value}),
        price_volatility_summary=_summary(tmp_path, "pv"),
        safety_limit_summary=_safety(tmp_path) if safety_status == "PASS" else _summary(tmp_path, "safety", status=safety_status, summary={}),
        config=_config(),
        output_path=tmp_path / "position_sizing.json",
        production_consumer_connected=production_consumer_connected,
    )
