from __future__ import annotations

import json
import hashlib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from ai_fund_lab_v2.broker.issue_code_normalizer import normalize_broker_issue_code
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import (
    _mark_strategy_planning_authority_consumer_called,
)
from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness
from ai_fund_lab_v2.runtime_v2.historical_support.environment import HistoricalSubmitAdapter
from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan_path
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.planning.strategy_authority import activate_strategy_planning_authority
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    capital_deployment_policy_hash,
    load_capital_deployment_policy,
)
from ai_fund_lab_v2.runtime_v2.safety_decision import RuntimeSafetyDecision
from ai_fund_lab_v2.runtime_v2.submit.pipeline import (
    BrokerAvailableQuantityEvidence,
    run_submit_pipeline,
    _submit_guard_item_evidence,
)
from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings
from tests.strategy.test_phase22_g_runtime_planning import (
    _produce as produce_runtime_planning_fixture,
    _runtime_owned_current_position_row,
)


BUSINESS_DATE = "2026-07-15"


def test_phase23_i_phase22_strategy_artifact_writes_pending_without_broker_write(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={"7203": "HOLD"},
        pc_members={"6098": ("ADD_CANDIDATE", False)},
        current_codes=(),
        position_sizing_positions={"6098": _position_sizing_row(target_notional=120_000.0, target_quantity=100, quantity_delta=100)},
    )
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    _write_position_sizing(strategy_dir / "position_sizing.json", symbol="6098", target_notional=120_000.0)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        price_by_symbol={"6098": 1_000.0},
        environment_capability_context={"broker_write": False},
    )

    assert result.status == "PASS"
    assert result.planning_consumer_eligibility == "ELIGIBLE"
    assert result.strategy_artifact_eligibility == "ELIGIBLE_FOR_PLANNING_AUTHORITY"
    assert result.legacy_planning_authority_used is False
    assert result.broker_write_allowed is False
    assert result.broker_write_performed is False
    pending = read_pending_order_plan_path(path=runtime_root / "pending_order_plan" / "pending_order_plan.json", environment="historical")
    assert pending.exists and pending.valid
    assert pending.plan is not None
    assert pending.plan.items[0].symbol == "6098"
    assert pending.plan.items[0].quantity == 100
    assert pending.plan.items[0].quantity_contract["quantity_authority"] == "strategy_runtime_planning_authority"
    assert pending.plan.items[0].source_decision_type == "BUY_NEW"


def test_phase23_bo_strategy_authority_uses_runtime_plan_price_authority_without_price_map(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={"7203": "HOLD"},
        pc_members={"94320": ("ADD_CANDIDATE", False)},
        current_codes=(),
        position_sizing_positions={"94320": _position_sizing_row(target_notional=180_000.0, target_quantity=1100, quantity_delta=1100, reference_price=153.2)},
    )
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    _write_position_sizing(strategy_dir / "position_sizing.json", symbol="94320", target_notional=180_000.0, reference_price=153.2)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        price_by_symbol={},
        environment_capability_context={"broker_write": False},
    )

    pending = read_pending_order_plan_path(path=runtime_root / "pending_order_plan" / "pending_order_plan.json", environment="historical")
    assert result.status == "PASS"
    assert result.reason_codes == ()
    assert pending.plan is not None
    item = pending.plan.items[0]
    assert item.symbol == "94320"
    assert item.quantity == 1100
    assert item.estimated_price == 153.2
    assert item.quantity_contract["reference_price"] == 153.2
    assert item.quantity_contract["reference_price_authority"]["PIT_status"] == "PASS"


def test_phase29_l21t_b_strategy_authority_commits_one_lot_buy_new_soft_cap_plan(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp_l21t_b",
        pm_actions={},
        pc_members={"78780": ("ADD_CANDIDATE", False)},
        current_codes=(),
        position_sizing_positions={
            "78780": _position_sizing_row(
                target_notional=242_000.0,
                target_quantity=100,
                quantity_delta=100,
                reference_price=2420.0,
            )
            | {
                "target_weight": 0.243189,
                "maximum_position_weight": 0.18,
                "semantic_buy_type": "BUY_NEW",
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
            },
        },
    )
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    _write_position_sizing(strategy_dir / "position_sizing.json", symbol="78780", target_notional=242_000.0, reference_price=2420.0)
    sizing_payload = json.loads((strategy_dir / "position_sizing.json").read_text(encoding="utf-8"))
    sizing_payload["positions"][0].update(
        {
            "target_weight": 0.243189,
            "selected_position_weight": 0.243189,
            "target_notional": 241_999.81,
            "incremental_buy_notional": 241_999.81,
            "selected_position_amount": 241_999.81,
            "remaining_add_capacity": 241_999.81,
            "maximum_position_weight": 0.18,
            "semantic_buy_type": "BUY_NEW",
            "discrete_authorized_quantity": 100,
            "discrete_authorized_notional": 242_000.0,
            "phase29_l19_lot_resolution": {
                "boundary_classification": "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX",
                "semantic_type": "BUY_NEW",
                "strategy_cap_overshoot_applied": True,
                "one_lot_fallback_applied": True,
                "one_lot_feasibility_status": "PASS",
                "one_lot_quantity": 100,
                "one_lot_notional": 242_000.0,
                "final_allocated_quantity": 100,
                "post_trade_weight": 0.243189,
                "safety_hard_cap": 0.25,
                "safety_hard_cap_preserved": True,
                "safety_margin_after_trade": 0.006811,
                "lot_overshoot_reason": "ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP",
            },
        }
    )
    _write_json(strategy_dir / "position_sizing.json", sizing_payload)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        price_by_symbol={},
        environment_capability_context={"broker_write": False},
    )

    pending = read_pending_order_plan_path(path=runtime_root / "pending_order_plan" / "pending_order_plan.json", environment="historical")
    assert result.status == "PASS"
    assert result.reason_codes == ()
    assert result.pending_item_count == 1
    assert pending.plan is not None
    item = pending.plan.items[0]
    assert item.symbol == "78780"
    assert item.quantity == 100
    assert item.source_decision_type == "BUY_NEW"
    assert item.approved is True
    assert pending.plan.approved_buy_item_ids == (item.pending_item_id,)
    assert item.quantity_contract["quantity_status"] == "RESOLVED_EXECUTABLE"


def test_phase29_l21t_k_strategy_authority_preserves_one_lot_authority_to_pending_submit_feasibility(tmp_path: Path) -> None:
    runtime_root = _runtime_root_for_data_readiness(tmp_path)
    _write_current_cash(runtime_root, cash=1_000_000)
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    policy_path = _write_capital_policy(
        tmp_path / "capital_deployment_policy.json",
        evaluation_capital=1_000_000,
        max_exposure=1_000_000,
    )
    policy = load_capital_deployment_policy(policy_path)
    lot_resolution = {
        "authority_type": "PHASE29_L19_CAP_CONSTRAINED_LOT_RESOLUTION",
        "boundary_classification": "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX",
        "semantic_type": "BUY_NEW",
        "strategy_cap_overshoot_applied": True,
        "strategy_cap_weight": 0.18,
        "strategy_target_cap": 0.18,
        "one_lot_fallback_applied": True,
        "one_lot_feasibility_status": "PASS",
        "one_lot_quantity": 100,
        "one_lot_notional": 227_400.0,
        "one_lot_weight": 0.230339,
        "final_allocated_quantity": 100,
        "executable_quantity_delta": 100,
        "preflight_executable_quantity_delta": 100,
        "post_trade_weight": 0.230339,
        "safety_hard_cap": 0.25,
        "safety_hard_cap_weight": 0.25,
        "safety_hard_cap_preserved": True,
        "safety_margin_after_trade": 0.019661,
        "lot_overshoot_reason": "ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP",
        "blocked_reason": "",
        "blocker_reason": "",
    }
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp_l21t_k",
        pm_actions={},
        pc_members={"30410": ("ADD_CANDIDATE", False)},
        current_codes=(),
        position_sizing_positions={
            "30410": _position_sizing_row(
                target_notional=186_617.98,
                target_quantity=100,
                quantity_delta=100,
                quantity_status="RESOLVED_EXECUTABLE",
                reference_price=2274.0,
            )
            | {
                "target_weight": 0.18903,
                "selected_position_weight": 0.18903,
                "maximum_position_weight": 0.18,
                "semantic_buy_type": "BUY_NEW",
                "transaction_target_notional": 227_400.0,
                "discrete_authorized_quantity": 100,
                "discrete_authorized_notional": 227_400.0,
                "one_lot_authority_consumed": True,
                "one_lot_authority_reason": "ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP",
                "phase29_l19_lot_resolution": lot_resolution,
            },
        },
    )
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    runtime_plan_path = strategy_dir / "runtime_planning.json"
    runtime_plan_payload = json.loads(runtime_plan_path.read_text(encoding="utf-8"))
    runtime_plan_payload["plans"][0].update(
        {
            "planned_quantity": 100,
            "planned_notional": 227_400.0,
            "target_quantity_candidate": 100,
            "quantity_delta_candidate": 100,
            "quantity_status": "RESOLVED_EXECUTABLE",
            "quantity_resolution": {
                "status": "PASS",
                "resolved_quantity": 100,
                "resolved_notional": 227_400.0,
                "reason": "one_lot_authority_materialized",
            },
        }
    )
    _write_json(runtime_plan_path, runtime_plan_payload)
    _write_json(
        strategy_dir / "position_sizing.json",
        {
            "schema_version": "phase22_position_sizing.v1",
            "business_date": BUSINESS_DATE,
            "portfolio_total_equity": 987_240.0,
            "portfolio_value": 987_240.0,
            "aggregate_exposure_cap": 1.0,
            "target_gross_exposure_ratio": 1.0,
            "effective_maximum_position_weight": 0.18,
            "strategy_maximum_position_weight": 0.18,
            "safety_maximum_position_weight": 0.25,
            "positions": [
                _position_sizing_row(
                    target_notional=186_617.98,
                    target_quantity=100,
                    quantity_delta=100,
                    quantity_status="RESOLVED_CANDIDATE",
                    reference_price=2274.0,
                )
                | {
                    "symbol": "30410",
                    "security_code": "30410",
                    "position_reference": "phase22-e-2023-05-16-30410",
                    "position_type": "NEW_POSITION",
                    "current_quantity": 0,
                    "target_weight": 0.18903,
                    "selected_position_weight": 0.18903,
                    "current_weight": 0.0,
                    "weight_delta": 0.18903,
                    "incremental_buy_notional": 186_617.98,
                    "selected_position_amount": 186_617.98,
                    "remaining_add_capacity": 186_617.98,
                    "transaction_target_notional": 227_400.0,
                    "maximum_position_weight": 0.18,
                    "semantic_buy_type": "BUY_NEW",
                    "discrete_authorized_quantity": 100,
                    "discrete_authorized_notional": 227_400.0,
                    "one_lot_authority_consumed": True,
                    "one_lot_authority_reason": "ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP",
                    "phase29_l19_lot_resolution": lot_resolution,
                },
            ],
        },
    )

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        price_by_symbol={},
        environment_capability_context=_historical_context(tmp_path),
        safety_authority_payload=_historical_safety_payload(tmp_path),
        submit_policy_authority_payload=_submit_policy_payload(policy),
    )

    assert result.status == "PASS", (
        result.status,
        result.reason,
        result.reason_codes,
        result.pending_item_count,
    )
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    raw_pending = json.loads(pending_path.read_text(encoding="utf-8"))
    pending = read_pending_order_plan_path(path=pending_path, environment="historical")
    assert pending.plan is not None
    assert pending.plan.state.value == "APPROVED"
    item = pending.plan.items[0]
    assert pending.plan.approved_buy_item_ids == (item.pending_item_id,)
    quantity_contract = item.quantity_contract
    assert quantity_contract is not None
    assert item.symbol == "30410"
    assert item.quantity == 100
    assert item.source_decision_type == "BUY_NEW"
    assert quantity_contract["position_sizing_authority"]["phase29_l19_lot_resolution"]["one_lot_quantity"] == 100
    assert quantity_contract["position_sizing_authority"]["one_lot_authority_consumed"] is True
    assert quantity_contract["position_sizing_authority"]["discrete_authorized_notional"] == 227_400.0
    assert raw_pending["policy_context"]["position_sizing_authority"]["phase29_l19_lot_resolution"]["one_lot_quantity"] == 100
    item_evidence = raw_pending["planning_submit_feasibility"]["items"][0]
    assert item_evidence["status"] == "PASS"
    assert item_evidence["selected_position_amount"] == 227_400.0
    assert item_evidence["estimated_amount"] == 227_400.0
    assert item_evidence["one_lot_authority_consumed"] is True
    assert item_evidence["position_sizing_binding_constraint"] == "ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP"


def test_phase23_bq_strategy_authority_accepts_carry_forward_current_position_no_action(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={"31330": "UNRESOLVED"},
        pc_members={"31330": ("UNRESOLVED", True)},
        current_codes=("31330",),
        current_position_rows=(
            {
                "security_code": "31330",
                "symbol": "31330",
                "quantity": 700,
                "as_of": "2026-07-10",
                "valuation_as_of": "2026-07-14",
                "source_market_date": "2026-07-14",
                "source": "runtime_v2_runtime_owned_fill_projection",
                "position_id": "runtime-current-31330",
                "position_campaign_id": "pc-test-31330",
            },
        ),
        position_sizing_positions={
            "31330": _position_sizing_row(
                target_notional=0.0,
                target_quantity=0,
                quantity_delta=0,
                quantity_status="RESOLVED_ZERO_DELTA",
            )
        },
    )
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    _write_position_sizing(strategy_dir / "position_sizing.json", symbol="31330", target_notional=0.0)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        price_by_symbol={},
        environment_capability_context={"broker_write": False},
    )

    pending = read_pending_order_plan_path(path=runtime_root / "pending_order_plan" / "pending_order_plan.json", environment="historical")
    assert result.status == "NO_ORDER_AUTHORIZED"
    assert result.reason_codes == ()
    assert pending.plan is not None
    assert len(pending.plan.items) == 0


def test_phase28_d14_strategy_sell_30410_uses_canonical_listed_info_without_opportunity(tmp_path: Path) -> None:
    business_date = "2023-06-14"
    runtime_root = tmp_path / ".runtime"
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    listed_issues_path = _write_listed_issues_parquet(
        tmp_path / "listed_issues" / "data.parquet",
        rows=(
            {
                "Date": business_date,
                "Code": "30410",
                "MktNm": "スタンダード",
                "ProdCat": "011",
            },
        ),
    )
    _write_strategy_source_input_manifest(
        strategy_dir=strategy_dir,
        business_date=business_date,
        listed_issues_path=listed_issues_path,
    )
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp30410",
        pm_actions={"30410": "EXIT"},
        pc_members={"30410": ("REMOVE_CANDIDATE", True)},
        current_codes=("30410",),
        current_position_rows=(
            {
                "security_code": "30410",
                "symbol": "30410",
                "quantity": 100,
                "market_value": 130_000.0,
                "as_of": business_date,
                "valuation_as_of": business_date,
                "source_market_date": business_date,
                "source": "runtime_v2_runtime_owned_fill_projection",
            },
        ),
        position_sizing_positions={
            "30410": {
                **_position_sizing_row(
                    target_notional=0.0,
                    target_quantity=0,
                    quantity_delta=-100,
                    reference_price=1300.0,
                ),
                "current_notional": 130_000.0,
                "incremental_target_notional": -130_000.0,
                "incremental_buy_notional": 0.0,
            }
        },
    )
    runtime_payload = json.loads(Path(runtime_plan.artifact_path).read_text(encoding="utf-8"))
    runtime_payload["business_date"] = business_date
    runtime_payload["feature_date"] = business_date
    runtime_payload["as_of"] = business_date + "T00:00:00+00:00"
    for plan in runtime_payload["plans"]:
        plan["business_date"] = business_date
        plan["reference_price_authority"]["business_date"] = business_date
        plan["reference_price_authority"]["price_date"] = business_date
        plan["reference_price_authority"]["symbol"] = "30410"
        plan["reference_price_date"] = business_date
        plan.pop("opportunity_authority", None)
    _write_json(strategy_dir / "runtime_planning.json", runtime_payload)
    _write_json(
        strategy_dir / "position_sizing.json",
        {
            "schema_version": "position_sizing.v1",
            "business_date": business_date,
            "producer_result_status": "PASS",
            "positions": [
                {
                    **_position_sizing_artifact_row(symbol="30410", target_notional=0.0, reference_price=1300.0),
                    "current_notional": 130_000.0,
                    "incremental_target_notional": -130_000.0,
                    "incremental_buy_notional": 0.0,
                    "target_quantity_candidate": 0,
                    "quantity_delta_candidate": -100,
                    "quantity_status": "RESOLVED_CANDIDATE",
                }
            ],
        },
    )

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=business_date,
        mode="historical",
        strategy_dir=strategy_dir,
        price_by_symbol={},
        environment_capability_context={"broker_write": False},
    )

    pending = read_pending_order_plan_path(path=runtime_root / "pending_order_plan" / "pending_order_plan.json", environment="historical")
    approval = json.loads((runtime_root / "runtime_state" / "strategy_planning" / business_date / "approval_artifact.json").read_text(encoding="utf-8"))
    assert result.status == "PASS"
    assert result.reason_codes == ()
    assert pending.plan is not None
    assert len(pending.plan.items) == 1
    item = pending.plan.items[0]
    assert item.symbol == "30410"
    assert item.side == "SELL"
    assert item.source_decision_type == "SELL_EXIT"
    assert item.listed_info is not None
    assert item.listed_info["listed_info_authority"] == "canonical_pit_listed_issues"
    assert item.listed_info["code"] == "30410"
    assert item.listed_info["market"] == "スタンダード"
    assert item.listed_info["product_category"] == "011"
    assert item.listed_info["security_type"] == "011"
    assert item.listed_info["current_listed"] is True
    assert item.listed_info["listed_info_source_hash"] == _file_sha256(listed_issues_path)
    assert approval["status"] == "APPROVED"
    normalized = normalize_broker_issue_code(item.symbol, listed_info=item.listed_info)
    assert normalized.normalization_status == "PASS"
    assert normalized.broker_issue_code == "3041"


def test_phase24_ij_unscoped_empty_review_does_not_commit_current_pending(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={"6098": "HOLD"},
        pc_members={"6098": ("ADD_CANDIDATE", False)},
        current_codes=(),
        position_sizing_positions={
            "6098": _position_sizing_row(
                target_notional=0.0,
                target_quantity=0,
                quantity_delta=0,
                quantity_status="RESOLVED_ZERO_DELTA",
            )
        },
    )
    runtime_payload = json.loads(Path(runtime_plan.artifact_path).read_text(encoding="utf-8"))
    for plan in runtime_payload["plans"]:
        if str(plan.get("security_code") or "") == "6098":
            plan["planning_intent"] = "BUY_NEW"
            plan["order_side_intent"] = "BUY"
            plan["planned_quantity"] = 0
            plan["quantity_status"] = "RESOLVED_ZERO_DELTA"
    _write_json(strategy_dir / "runtime_planning.json", runtime_payload)
    _write_position_sizing(
        strategy_dir / "position_sizing.json",
        symbol="6098",
        target_notional=0.0,
    )
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    prior_pending = {
        "schema_version": "runtime_v2_pending_slot_v1",
        "pending_plan_id": "prior-authoritative-pending",
        "state": "EMPTY",
        "status": "EMPTY",
        "active_pending": False,
        "environment": "historical",
        "target_session_date": BUSINESS_DATE,
        "items": [],
    }
    _write_json(pending_path, prior_pending)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        price_by_symbol={},
        environment_capability_context={"broker_write": False},
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "strategy_planning_authority_unresolved"
    assert result.pending_item_count == 0
    assert result.pending_commit_status == "NOT_COMMITTED_REVIEW_REQUIRED_EMPTY_UNSCOPED"
    assert result.pending_authority_eligibility == "AUTHORITY_INELIGIBLE"
    assert result.pending_retry_eligibility == "RETRY_INPUT_INELIGIBLE"
    assert result.atomic_commit_decision == "SKIP_CURRENT_PENDING_COMMIT"
    assert json.loads(pending_path.read_text(encoding="utf-8")) == prior_pending
    order_plan = json.loads((runtime_root / "runtime_state" / "strategy_planning" / BUSINESS_DATE / "order_plan.json").read_text(encoding="utf-8"))
    approval = json.loads((runtime_root / "runtime_state" / "strategy_planning" / BUSINESS_DATE / "approval_artifact.json").read_text(encoding="utf-8"))
    assert order_plan["planning_consumer_eligibility"] == "REVIEW_REQUIRED"
    assert approval["reason"] == "strategy_planning_authority_unresolved"


def test_phase23_az_strategy_authority_canonical_path_materializes_pending_safety(tmp_path: Path) -> None:
    runtime_root = _runtime_root_for_data_readiness(tmp_path)
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    symbols = ("31330", "43780", "45640", "45960", "45970", "66340", "67400", "89180", "94320")
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={symbol: "HOLD" for symbol in symbols},
        pc_members={symbol: ("ADD_CANDIDATE", False) for symbol in symbols},
        current_codes=(),
        position_sizing_positions={
            symbol: _position_sizing_row(target_notional=120_000.0, target_quantity=100, quantity_delta=100)
            for symbol in symbols
        },
    )
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    _write_position_sizing_many(strategy_dir / "position_sizing.json", symbols=symbols, target_notional=120_000.0)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        price_by_symbol={symbol: 900.0 for symbol in symbols},
        environment_capability_context=_historical_context(tmp_path),
        safety_authority_payload=_historical_safety_payload(tmp_path),
    )

    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    raw_pending = json.loads(pending_path.read_text(encoding="utf-8"))
    pending = read_pending_order_plan_path(path=pending_path, environment="historical")
    readiness = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        readiness_scope="sell_planning",
        broker_environment="historical_simulated",
        runtime_test_evidence_root=str(_evidence_root(tmp_path)),
        runtime_test_run_id="runtime-test-phase23-az",
        runtime_test_profile_id="historical-smoke",
        broker_write=False,
        external_delivery=False,
    )

    assert result.status == "PASS"
    assert result.pending_item_count == 9
    assert result.lineage["safety_authority"]["status"] == "BOUND"
    assert raw_pending["safety_context"]["safety_decision"] == "NEUTRAL"
    assert raw_pending["safety_context"]["safety_decision_id"] == "historical-neutral-safety:2026-07-15"
    assert raw_pending["safety_decision_id"] == "historical-neutral-safety:2026-07-15"
    assert raw_pending["items"][0]["safety_authority"] == "historical_initial_no_external_effect"
    assert raw_pending["items"][0]["runtime_test_run_id"] == "runtime-test-phase23-az"
    assert pending.plan is not None
    assert len(pending.plan.items) == 9
    assert pending.plan.safety_context is not None
    assert pending.plan.items[0].safety_decision == "NEUTRAL"
    assert readiness.status == "READY"
    assert readiness.payload["components"]["pending"]["historical_pending_safety_authority"]["status"] == "READY"
    assert "historical_safety_temporal_authority_missing" not in readiness.payload["review_reasons"]
    assert "pending_safety_evidence_missing" not in readiness.payload["review_reasons"]


def test_phase23_bb_planning_lineage_and_submit_policy_authority_are_separated(tmp_path: Path) -> None:
    runtime_root = _runtime_root_for_data_readiness(tmp_path)
    _write_current_cash(runtime_root, cash=2_000_000)
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    policy_path = _write_capital_policy(
        tmp_path / "capital_deployment_policy.json",
        evaluation_capital=2_000_000,
        max_exposure=2_000_000,
    )
    policy = load_capital_deployment_policy(policy_path)
    symbols = ("31330", "43780", "45640", "45960", "45970", "66340", "67400", "89180", "94320")
    target_notional = 50_000.0
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={symbol: "HOLD" for symbol in symbols},
        pc_members={symbol: ("ADD_CANDIDATE", False) for symbol in symbols},
        current_codes=(),
        position_sizing_positions={
            symbol: _position_sizing_row(target_notional=target_notional, target_quantity=100, quantity_delta=100)
            for symbol in symbols
        },
    )
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    _write_position_sizing_many(strategy_dir / "position_sizing.json", symbols=symbols, target_notional=target_notional)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        price_by_symbol={symbol: 500.0 for symbol in symbols},
        environment_capability_context=_historical_context(tmp_path),
        safety_authority_payload=_historical_safety_payload(tmp_path),
        submit_policy_authority_payload=_submit_policy_payload(policy),
    )
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    pending_payload = json.loads(pending_path.read_text(encoding="utf-8"))
    pending = read_pending_order_plan_path(path=pending_path, environment="historical")
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=HistoricalSubmitAdapter(
            runtime_root=runtime_root,
            business_date=BUSINESS_DATE,
            evaluation_time=BUSINESS_DATE + "T08:45:00+09:00",
        ),
        capital_deployment_policy_path=policy_path,
        safety_decision=_historical_submit_safety_decision(),
    )

    assert result.status == "PASS"
    assert result.pending_item_count == 9
    assert result.lineage["submit_policy_authority"]["status"] == "BOUND"
    assert pending.plan is not None
    assert pending.plan.planning_authority_version != pending.plan.submit_policy_version
    assert pending.plan.planning_authority_version == "phase22_strategy_runtime_planning"
    assert pending.plan.submit_policy_version == "capital_deployment_v1"
    assert pending.plan.submit_policy_hash == capital_deployment_policy_hash(policy)
    assert pending.plan.approval is not None
    assert pending.plan.approval.submit_policy_hash == pending.plan.submit_policy_hash
    assert pending_payload["planning_lineage_context"]["planning_authority_source"]
    assert pending_payload["submit_policy_context"]["submit_policy_hash"] == capital_deployment_policy_hash(policy)
    assert submit.submit_policy_consistency["policy_consistency_status"] == "PASS"
    assert submit.submit_policy_consistency["comparison_authority"] == "submit_policy_authority"
    assert submit.submit_policy_consistency["policy_mismatch_reason"] == ""


def test_phase23_bd_opportunity_authority_survives_pending_item_roundtrip_and_submit_guard(tmp_path: Path) -> None:
    runtime_root = _runtime_root_for_data_readiness(tmp_path)
    _write_current_cash(runtime_root, cash=2_000_000)
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    policy_path = _write_capital_policy(
        tmp_path / "capital_deployment_policy.json",
        evaluation_capital=2_000_000,
        max_exposure=2_000_000,
    )
    policy = load_capital_deployment_policy(policy_path)
    symbols = ("31330", "43780", "45640", "45960", "45970", "66340", "67400", "89180", "94320")
    target_notional = 50_000.0
    opportunity_path = _write_opportunity_rankings(
        runtime_root / "runtime_state" / "buy_ai" / BUSINESS_DATE / "opportunity_rankings.json",
        symbols=symbols,
    )
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={symbol: "HOLD" for symbol in symbols},
        pc_members={symbol: ("ADD_CANDIDATE", False) for symbol in symbols},
        current_codes=(),
        position_sizing_positions={
            symbol: _position_sizing_row(target_notional=target_notional, target_quantity=100, quantity_delta=100)
            for symbol in symbols
        },
        opportunity_artifact_path=opportunity_path,
    )
    runtime_payload = json.loads(Path(runtime_plan.artifact_path).read_text(encoding="utf-8"))
    buy_plans = [plan for plan in runtime_payload["plans"] if plan["order_side_intent"] == "BUY"]
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    _write_position_sizing_many(strategy_dir / "position_sizing.json", symbols=symbols, target_notional=target_notional)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        strategy_dir=strategy_dir,
        price_by_symbol={symbol: 500.0 for symbol in symbols},
        environment_capability_context={"broker_write": False},
        safety_authority_payload=_demo_safety_payload(),
        submit_policy_authority_payload=_submit_policy_payload(policy),
    )
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    raw_pending = json.loads(pending_path.read_text(encoding="utf-8"))
    pending = read_pending_order_plan_path(path=pending_path, environment="demo")
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
        safety_decision=_demo_submit_safety_decision(),
    )

    assert len(buy_plans) == 9
    assert all(plan.get("opportunity_authority", {}).get("opportunity_row_id") for plan in buy_plans)
    assert result.status == "PASS"
    buy_lineage = [item for item in result.lineage["items"] if item["pending_item_generated"]]
    assert len(buy_lineage) == 9
    assert all(item["opportunity_buy_rank"] for item in buy_lineage)
    assert all(item["portfolio_input_opportunity_rank"] == item["opportunity_buy_rank"] for item in buy_lineage)
    assert all(item["position_sizing_opportunity_buy_rank"] == item["opportunity_buy_rank"] for item in buy_lineage)
    assert all(item["rank_authority_status"] == "PASS" for item in buy_lineage)
    assert all(item["rank_authority"] == "OPPORTUNITY_BUY_RANK_AUTHORITY" for item in buy_lineage)
    assert all(item["opportunity_artifact_path"] == str(opportunity_path) for item in buy_lineage)
    assert all(item["opportunity_artifact_hash"] for item in buy_lineage)
    assert all(item["opportunity_row_id"] for item in buy_lineage)
    assert all(item["opportunity_row_authority_hash"] for item in buy_lineage)
    assert pending.plan is not None
    assert len(pending.plan.items) == 9
    assert raw_pending["items"][0]["listed_info"]["opportunity_artifact_path"] == str(opportunity_path)
    assert raw_pending["items"][0]["listed_info"]["opportunity_row_id"]
    assert raw_pending["items"][0]["listed_info"]["opportunity_buy_rank"]
    assert raw_pending["items"][0]["submit_policy_hash"] == capital_deployment_policy_hash(policy)
    assert pending.plan.items[0].listed_info is not None
    assert pending.plan.items[0].listed_info["opportunity_buy_eligibility"] == "BUY_ELIGIBLE"
    assert submit.submit_policy_consistency["policy_consistency_status"] == "PASS"
    assert sum(1 for item in submit.submit_guard_item_evidence if item["violated_policy"] == "opportunity_buy_eligibility") == 0
    assert "opportunity_evidence_missing" not in {item["guard_reason"] for item in submit.submit_guard_item_evidence}


def test_phase23_bh_no_buy_reason_is_removed_before_pending_and_submit_passes(tmp_path: Path) -> None:
    runtime_root = _runtime_root_for_data_readiness(tmp_path)
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    policy_path = _write_capital_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    symbols = ("31330", "43780", "45640", "45960", "45970", "66340", "67400", "72030", "89180")
    opportunity_path = _write_opportunity_rankings(
        runtime_root / "runtime_state" / "buy_ai" / BUSINESS_DATE / "opportunity_rankings.json",
        symbols=symbols,
        no_buy_reasons={"43780": "high_downside_risk_score"},
    )
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={symbol: "HOLD" for symbol in symbols},
        pc_members={symbol: ("ADD_CANDIDATE", False) for symbol in symbols},
        current_codes=(),
        position_sizing_positions={
            symbol: _position_sizing_row(target_notional=120_000.0, target_quantity=100, quantity_delta=100)
            for symbol in symbols
        },
        opportunity_artifact_path=opportunity_path,
    )
    runtime_payload = json.loads(Path(runtime_plan.artifact_path).read_text(encoding="utf-8"))
    buy_plans = [plan for plan in runtime_payload["plans"] if plan["order_side_intent"] == "BUY"]
    blocked_plan = next(plan for plan in runtime_payload["plans"] if plan["security_code"] == "43780")
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    _write_position_sizing_many(strategy_dir / "position_sizing.json", symbols=symbols, target_notional=120_000.0)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        strategy_dir=strategy_dir,
        price_by_symbol={symbol: 1_000.0 for symbol in symbols},
        environment_capability_context={"broker_write": False},
        safety_authority_payload=_demo_safety_payload(),
        submit_policy_authority_payload=_submit_policy_payload(policy),
    )
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    pending = read_pending_order_plan_path(path=pending_path, environment="demo")
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
        safety_decision=_demo_submit_safety_decision(),
    )

    assert blocked_plan["planning_intent"] == "NO_ORDER"
    assert blocked_plan["no_order_reason"] == "opportunity_no_buy_reason_present"
    assert len(buy_plans) == 8
    assert "43780" not in {plan["security_code"] for plan in buy_plans}
    assert result.status == "PASS"
    assert pending.plan is not None
    assert len(pending.plan.items) == 8
    assert "43780" not in {item.symbol for item in pending.plan.items}
    assert submit.status == "REVIEW_REQUIRED"
    assert sum(1 for item in submit.submit_guard_item_evidence if item["violated_policy"] == "opportunity_buy_eligibility") == 0
    assert submit.blocked_count == len(pending.plan.items)
    assert len(submit.submit_guard_item_evidence) == 8
    assert {item["violated_policy"] for item in submit.submit_guard_item_evidence} == {"accepted_generation_binding"}


def test_phase23_bd_submit_guard_blocks_opportunity_row_identity_mismatch(tmp_path: Path) -> None:
    runtime_root = _runtime_root_for_data_readiness(tmp_path)
    policy_path = _write_capital_policy(tmp_path / "capital_deployment_policy.json")
    opportunity_path = _write_opportunity_rankings(
        runtime_root / "runtime_state" / "buy_ai" / BUSINESS_DATE / "opportunity_rankings.json",
        symbols=("31330",),
    )
    item = PendingOrderItem(
        pending_item_id="buy-31330",
        symbol="31330",
        side="BUY",
        quantity=100,
        order_type="MARKET",
        estimated_price=1000,
        estimated_amount=100_000,
        approved=True,
        state="APPROVED",
        listed_info={
            "code": "31330",
            "current_listed": True,
            "opportunity_authority": "runtime_v2_opportunity_ranking_row",
            "opportunity_artifact_path": str(opportunity_path),
            "opportunity_artifact_hash": _file_sha256(opportunity_path),
            "opportunity_business_date": BUSINESS_DATE,
            "opportunity_feature_date": BUSINESS_DATE,
            "opportunity_row_id": "wrong-row-id",
            "opportunity_expected_edge_score": 0.10,
            "opportunity_expected_return": 0.10,
            "opportunity_no_buy_reason": "",
            "opportunity_buy_rank": 1,
        },
        submit_policy_version="capital_deployment_v1",
        submit_policy_source=str(policy_path),
        submit_policy_hash=capital_deployment_policy_hash(load_capital_deployment_policy(policy_path)),
        accepted_generation_id="accepted-generation-2026-07-15",
        accepted_generation_business_date=BUSINESS_DATE,
        accepted_generation_binding_status="PASS",
        accepted_generation_binding={
            "status": "PASS",
            "generation_id": "accepted-generation-2026-07-15",
            "business_date": BUSINESS_DATE,
            "binding_source": "test_fixture",
            "fallback_used": False,
        },
    )
    pending_plan = SimpleNamespace(
        approval=SimpleNamespace(
            accepted_generation_id="accepted-generation-2026-07-15",
            accepted_generation_business_date=BUSINESS_DATE,
            accepted_generation_binding_status="PASS",
            accepted_generation_binding={
                "status": "PASS",
                "generation_id": "accepted-generation-2026-07-15",
                "business_date": BUSINESS_DATE,
                "binding_source": "test_fixture",
                "fallback_used": False,
            },
        ),
        accepted_generation_id="accepted-generation-2026-07-15",
        accepted_generation_business_date=BUSINESS_DATE,
        accepted_generation_binding_status="PASS",
        accepted_generation_binding={
            "status": "PASS",
            "generation_id": "accepted-generation-2026-07-15",
            "business_date": BUSINESS_DATE,
            "binding_source": "test_fixture",
            "fallback_used": False,
        },
    )
    evidence = _submit_guard_item_evidence(
        item=item,
        pending_plan=pending_plan,
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        policy=load_capital_deployment_policy(policy_path),
        current_state={"current_position_source": str(runtime_root / "persistent_ledger" / "state.json")},
        broker_position_quantity=None,
        broker_available_quantity=None,
        broker_available_quantity_evidence=_empty_broker_available_quantity_evidence(),
        safety_decision=_demo_submit_safety_decision(),
    )

    assert evidence["guard_decision"] == "BLOCKED"
    assert evidence["violated_policy"] == "opportunity_buy_eligibility"
    assert evidence["opportunity_buy_eligibility_reason_code"] == "opportunity_row_identity_mismatch"


def test_phase23_az_strategy_authority_missing_safety_payload_stays_fail_closed(tmp_path: Path) -> None:
    runtime_root = _runtime_root_for_data_readiness(tmp_path)
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={"7203": "HOLD"},
        pc_members={"6098": ("ADD_CANDIDATE", False)},
        current_codes=(),
        position_sizing_positions={"6098": _position_sizing_row(target_notional=120_000.0, target_quantity=100, quantity_delta=100)},
    )
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    _write_position_sizing(strategy_dir / "position_sizing.json", symbol="6098", target_notional=120_000.0)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        price_by_symbol={"6098": 1_000.0},
        environment_capability_context=_historical_context(tmp_path),
    )
    readiness = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        readiness_scope="sell_planning",
        broker_environment="historical_simulated",
        runtime_test_evidence_root=str(_evidence_root(tmp_path)),
        runtime_test_run_id="runtime-test-phase23-az",
        runtime_test_profile_id="historical-smoke",
        broker_write=False,
        external_delivery=False,
    )

    assert result.status == "PASS"
    assert result.lineage["safety_authority"]["status"] == "UNBOUND"
    assert readiness.status == "REVIEW_REQUIRED"
    assert "pending_safety_evidence_missing" in readiness.payload["review_reasons"]
    assert "historical_safety_temporal_authority_missing" in readiness.payload["review_reasons"]


def test_phase23_az_demo_safety_payload_preserves_runtime_decision_without_neutral_rewrite(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={"7203": "HOLD"},
        pc_members={"6098": ("ADD_CANDIDATE", False)},
        current_codes=(),
        position_sizing_positions={"6098": _position_sizing_row(target_notional=120_000.0, target_quantity=100, quantity_delta=100)},
    )
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    _write_position_sizing(strategy_dir / "position_sizing.json", symbol="6098", target_notional=120_000.0)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        strategy_dir=strategy_dir,
        price_by_symbol={"6098": 1_000.0},
        environment_capability_context={"broker_write": False},
        safety_authority_payload={
            "safety_authority": "runtime_safety_decision",
            "safety_decision_id": "demo-safety-2026-07-15",
            "safety_policy_version": "runtime_safety_v1",
            "safety_source": "runtime_state/safety/latest_safety_decision.json",
            "safety_decision": "ALLOW",
            "safety_reason": "demo safety ready",
            "safety_business_date": BUSINESS_DATE,
            "temporal_authority_business_date": BUSINESS_DATE,
        },
    )

    pending = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    assert result.status == "PASS"
    assert pending["safety_context"]["safety_decision"] == "ALLOW"
    assert pending["safety_context"]["safety_decision_id"] == "demo-safety-2026-07-15"
    assert pending["items"][0]["safety_decision"] == "ALLOW"
    assert pending["items"][0]["safety_authority"] == "runtime_safety_decision"


def test_phase23_i_missing_price_does_not_fallback_to_legacy_or_empty_pass(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={"7203": "HOLD"},
        pc_members={"6098": ("ADD_CANDIDATE", False)},
        current_codes=(),
        position_sizing_positions={"6098": _position_sizing_row(target_notional=120_000.0, target_quantity=100, quantity_delta=100)},
    )
    runtime_payload = json.loads(Path(runtime_plan.artifact_path).read_text(encoding="utf-8"))
    for field in ("reference_price", "reference_price_authority", "reference_price_resolution", "reference_price_type", "reference_price_date"):
        runtime_payload["plans"][0].pop(field, None)
    _write_json(strategy_dir / "runtime_planning.json", runtime_payload)
    _write_position_sizing(strategy_dir / "position_sizing.json", symbol="6098", target_notional=120_000.0)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        price_by_symbol={},
        environment_capability_context={"broker_write": False},
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.no_action is False
    assert result.legacy_planning_authority_used is False
    assert "strategy_runtime_planning_artifact_invalid" in result.reason_codes
    assert result.pending_commit_status == "NOT_COMMITTED_REVIEW_REQUIRED_EMPTY_UNSCOPED"
    assert result.pending_authority_eligibility == "AUTHORITY_INELIGIBLE"
    pending = read_pending_order_plan_path(path=runtime_root / "pending_order_plan" / "pending_order_plan.json", environment="historical")
    assert not pending.exists


def test_phase23_i_valid_no_action_remains_empty_pending_without_legacy_fallback(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={"7203": "HOLD"},
        pc_members={"7203": ("RETAIN", True)},
        current_codes=("7203",),
        current_position_rows=(
            _runtime_owned_current_position_row(
                "7203",
                quantity=100,
                as_of=BUSINESS_DATE,
                source="runtime_v2_runtime_owned_fill_projection",
            ),
        ),
        position_sizing_positions={"7203": _position_sizing_row(target_notional=0.0, target_quantity=100, quantity_delta=0, quantity_status="RESOLVED_ZERO_DELTA")},
    )
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    _write_position_sizing(strategy_dir / "position_sizing.json", symbol="7203", target_notional=0.0)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        price_by_symbol={"7203": 2_000.0},
        environment_capability_context={"broker_write": False},
    )

    assert result.status == "NO_ORDER_AUTHORIZED"
    assert result.no_action is True
    assert result.legacy_planning_authority_used is False
    pending = read_pending_order_plan_path(path=runtime_root / "pending_order_plan" / "pending_order_plan.json", environment="historical")
    assert pending.exists and pending.valid
    assert pending.plan is not None
    assert pending.plan.state.value == "EMPTY"


def test_phase28_d70b_no_action_missing_current_authority_still_fails_closed(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={"7203": "HOLD"},
        pc_members={"7203": ("RETAIN", True)},
        current_codes=("7203",),
        position_sizing_positions={"7203": _position_sizing_row(target_notional=0.0, target_quantity=100, quantity_delta=0, quantity_status="RESOLVED_ZERO_DELTA")},
    )
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    _write_position_sizing(strategy_dir / "position_sizing.json", symbol="7203", target_notional=0.0)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        price_by_symbol={"7203": 2_000.0},
        environment_capability_context={"broker_write": False},
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.no_action is False
    assert result.reason_codes == ("strategy_plan_order_side_unresolved",)
    pending = read_pending_order_plan_path(path=runtime_root / "pending_order_plan" / "pending_order_plan.json", environment="historical")
    assert not pending.exists


def test_phase23_ar_invalid_planned_quantity_fails_closed_without_pending_materialization(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={"7203": "HOLD"},
        pc_members={"6098": ("ADD_CANDIDATE", False)},
        current_codes=(),
        position_sizing_positions={"6098": _position_sizing_row(target_notional=120_000.0, target_quantity=100, quantity_delta=100)},
    )
    runtime_payload = json.loads(Path(runtime_plan.artifact_path).read_text())
    runtime_payload["plans"][0]["planned_quantity"] = 12.5
    _write_json(strategy_dir / "runtime_planning.json", runtime_payload)
    _write_position_sizing(strategy_dir / "position_sizing.json", symbol="6098", target_notional=120_000.0)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        price_by_symbol={"6098": 1_000.0},
        environment_capability_context={"broker_write": False},
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "strategy_runtime_planning_artifact_invalid" in result.reason_codes
    assert result.pending_commit_status == "NOT_COMMITTED_REVIEW_REQUIRED_EMPTY_UNSCOPED"
    assert result.pending_authority_eligibility == "AUTHORITY_INELIGIBLE"
    pending = read_pending_order_plan_path(path=runtime_root / "pending_order_plan" / "pending_order_plan.json", environment="historical")
    assert not pending.exists


def test_phase23_r_strategy_shadow_summary_marks_called_consumer(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    strategy_dir = run_dir / "daily" / BUSINESS_DATE / "strategy"
    strategy_dir.mkdir(parents=True)
    _write_json(
        run_dir / "plan.json",
        {"business_dates": [{"business_date": BUSINESS_DATE}]},
    )
    _write_json(
        strategy_dir / "strategy_shadow_summary.json",
        {
            "schema_version": "runtime_test_strategy_shadow_summary.v1",
            "business_date": BUSINESS_DATE,
            "strategy_shadow_judgment": "REVIEW_REQUIRED",
            "strategy_planning_authority_consumer_called": False,
            "active_runtime_consumer_eligibility": "NO",
            "artifact_count": 0,
        },
    )

    _mark_strategy_planning_authority_consumer_called(
        strategy_run_dir=run_dir,
        strategy_dir=strategy_dir,
        result={
            "status": "REVIEW_REQUIRED",
            "reason": "strategy_planning_authority_unresolved",
            "planning_consumer_eligibility": "ELIGIBLE",
            "strategy_artifact_eligibility": "ELIGIBLE_WITH_SCOPED_REVIEW",
            "plan_count": 50,
            "pending_item_count": 0,
            "selected_symbols": [],
            "reason_codes": ["strategy_plan_quantity_unresolved:7203"],
            "broker_write_performed": False,
            "runtime_switch_performed": False,
            "legacy_formal_planning_authority_active": False,
        },
    )

    daily_summary = json.loads((strategy_dir / "strategy_shadow_summary.json").read_text())
    run_summary = json.loads((run_dir / "strategy_shadow_summary.json").read_text())
    assert daily_summary["strategy_planning_authority_consumer_called"] is True
    assert daily_summary["active_runtime_consumer_eligibility"] == "YES"
    assert daily_summary["strategy_planning_authority_evidence"]["pending_item_count"] == 0
    assert run_summary["strategy_planning_authority_consumer_called"] is True
    assert run_summary["active_runtime_consumer_eligibility"] == "YES"


def _write_position_sizing(path: Path, *, symbol: str, target_notional: float, reference_price: float = 1000.0) -> None:
    _write_position_sizing_many(path, symbols=(symbol,), target_notional=target_notional, reference_price=reference_price)


def _write_position_sizing_many(path: Path, *, symbols: tuple[str, ...], target_notional: float, reference_price: float = 1000.0) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "position_sizing.v1",
                "business_date": BUSINESS_DATE,
                "producer_result_status": "PASS",
                "positions": [
                    _position_sizing_artifact_row(symbol=symbol, target_notional=target_notional, reference_price=reference_price)
                    for symbol in symbols
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _position_sizing_artifact_row(*, symbol: str, target_notional: float, reference_price: float = 1000.0) -> dict[str, object]:
    selected_position_amount = max(float(target_notional), 100.0 * float(reference_price))
    return {
        "security_code": symbol,
        "position_reference": f"pc-{symbol}",
        "target_notional": target_notional,
        "current_notional": 0.0,
        "incremental_target_notional": target_notional,
        "incremental_buy_notional": selected_position_amount,
        "selected_position_amount": selected_position_amount,
        "remaining_add_capacity": selected_position_amount,
        "target_weight": 0.05,
        "selected_position_weight": 0.05,
        "maximum_position_weight": 0.10,
        "portfolio_policy_source": "phase26_step5_fixture_portfolio_policy",
        "sizing_status": "SIZED",
        "target_quantity_candidate": 100 if target_notional > 0 else 0,
        "quantity_delta_candidate": 100 if target_notional > 0 else 0,
        "quantity_status": "RESOLVED_CANDIDATE" if target_notional > 0 else "RESOLVED_ZERO_DELTA",
        "reference_price": reference_price,
        "reference_price_authority": {
            "authority_type": "REFERENCE_PRICE_AUTHORITY",
            "business_date": BUSINESS_DATE,
            "canonical_field": "reference_price",
            "latest_fallback_used": False,
            "price_date": BUSINESS_DATE,
            "price_type": "planning_reference_close",
            "PIT_status": "PASS",
            "source_authority": "MARKET_EVIDENCE_AUTHORITY",
            "source_field": "close",
            "symbol": symbol,
        },
        "reference_price_resolution": {
            "status": "PASS",
            "reason": "reference_price_resolved",
            "resolved_price": reference_price,
            "review_reason": "",
        },
        "reference_price_type": "planning_reference_close",
        "reference_price_date": BUSINESS_DATE,
    }


def _runtime_root_for_data_readiness(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase23-az",
            "environment": "historical",
            "source": "phase23_az_fixture",
            "as_of": BUSINESS_DATE,
            "updated_at": BUSINESS_DATE + "T00:00:00Z",
            "business_date": BUSINESS_DATE,
            "positions": [],
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": 0,
            "total_equity": 1_000_000,
            "review_required": False,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
        },
    )
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "runtime_v2_operation_state_v1",
            "role": "authoritative_runtime_operation_state",
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T00:00:00Z",
            "updated_at": BUSINESS_DATE + "T00:00:00Z",
            "environment": "historical",
            "runtime_mode": "historical",
            "state": "CURRENT_STATE_LOADED",
            "safety_state": "NORMAL",
            "current_safety_state": "NORMAL",
            "source": "runtime_v2_runtime_state_producer",
            "asset_state_is_authoritative_here": False,
            "pending_state_is_authoritative_here": False,
        },
    )
    _write_json(
        root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "business_date": BUSINESS_DATE,
            "as_of": BUSINESS_DATE,
            "market_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T00:00:00Z",
            "status": "READY",
            "market_status": "READY",
            "quote_status": "READY",
            "quote_count": 1,
            "market_summary": {"quote_count": 1},
        },
    )
    _write_json(
        root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "snapshot.json",
        {
            "schema_version": "runtime_v2_broker_readonly_snapshot_v1",
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T00:00:00Z",
            "broker_mode": "historical_simulated",
            "production_equivalent": False,
            "review_required": False,
            "positions": [],
            "orders": [],
            "executions": [],
        },
    )
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    _write_jsonl(
        root / "operations" / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.jsonl",
        [
            {"Date": "2026-07-14", "HolidayDivision": "1"},
            {"Date": BUSINESS_DATE, "HolidayDivision": "1"},
            {"Date": "2026-07-16", "HolidayDivision": "1"},
        ],
    )
    _write_step26_runtime_authority_artifacts(root)
    return root


def _write_current_cash(runtime_root: Path, *, cash: float) -> None:
    state_path = runtime_root / "persistent_ledger" / "state.json"
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    payload["cash"] = cash
    payload["buying_power"] = cash
    payload["total_equity"] = cash + float(payload.get("market_value") or 0)
    _write_json(state_path, payload)


def _write_step26_runtime_authority_artifacts(runtime_root: Path) -> None:
    _write_dynamic_position_count_authority(runtime_root, target_position_count=20)
    _write_dynamic_cash_exposure_authority(runtime_root, target_cash_ratio=0.10, target_gross_exposure_ratio=0.95)


def _write_dynamic_position_count_authority(runtime_root: Path, *, target_position_count: int) -> None:
    _write_json(
        runtime_root / "strategy_artifacts" / "dynamic_position_count" / BUSINESS_DATE / "dynamic_position_count.json",
        {
            "schema_version": "dynamic_position_count.v1",
            "producer_version": "phase22_h_dynamic_position_count_producer.v1",
            "business_date": BUSINESS_DATE,
            "as_of": BUSINESS_DATE + "T00:00:00+00:00",
            "feature_date": BUSINESS_DATE,
            "artifact_lifecycle_status": "DRAFT",
            "source_authority_status": "VALID",
            "producer_result_status": "PASS",
            "runtime_consumer_eligibility": "NOT_ELIGIBLE",
            "production_consumer_connected": False,
            "runtime_switch_performed": False,
            "legacy_authority_active": True,
            "target_position_count_resolution": "RESOLVED",
            "minimum_position_count": 0,
            "calculated_target_position_count": target_position_count,
            "target_position_count": target_position_count,
            "maximum_position_count": target_position_count,
            "safety_hard_maximum": None,
            "legacy_active_max_positions": 10,
            "strategy_minimum_position_count": 0,
            "strategy_target_position_count": target_position_count,
            "strategy_maximum_position_count": target_position_count,
            "actual_target_position_count": target_position_count,
            "meaningful_allocation_position_count": target_position_count,
            "safety_hard_maximum_status": "REMOVED",
            "strategy_fixed_position_cap_used": False,
            "cash_ratio_decided": False,
            "exposure_decided": False,
            "position_sizing_decided": False,
            "allocation_decided": False,
            "quantity_decided": False,
            "lot_rounding_decided": False,
            "capacity_constraint_status": "SUFFICIENT",
            "ceiling_authority_status": "SEPARATED",
            "confidence": 0.9,
            "uncertainty": "LOW",
            "reason_codes": ["phase26_step5_fixture_dynamic_position_count_authority"],
            "eligible_opportunity_count": target_position_count,
            "available_candidate_count": target_position_count,
            "available_opportunity_count": target_position_count,
            "shadow_comparison": {
                "existing_active_max_positions": 10,
                "dynamic_minimum": 0,
                "dynamic_target": target_position_count,
                "dynamic_maximum": target_position_count,
                "difference_from_existing": target_position_count - 10,
                "would_change_available_slots": True,
                "runtime_behavior_changed": False,
            },
            "current_position_count": 0,
            "capital_affordable_position_count": target_position_count,
            "liquidity_feasible_position_count": target_position_count,
            "position_count_posture": "INCREASE",
            "source_artifacts": [{"role": "portfolio_policy", "path": "phase26_step5_fixture", "required": True, "status": "PASS"}],
            "source_hashes": [{"role": "portfolio_policy", "path": "phase26_step5_fixture", "sha256": "0" * 64}],
            "temporal_safety": {
                "point_in_time": True,
                "future_leakage_used": False,
                "feature_date_lte_business_date": True,
                "implicit_latest_fallback_used": False,
                "previous_day_target_copied": False,
            },
        },
    )


def _write_dynamic_cash_exposure_authority(
    runtime_root: Path,
    *,
    target_cash_ratio: float,
    target_gross_exposure_ratio: float,
) -> None:
    portfolio_total_equity = 1_000_000.0
    target_invested_ratio = target_gross_exposure_ratio
    _write_json(
        runtime_root / "strategy_artifacts" / "dynamic_cash_exposure" / BUSINESS_DATE / "dynamic_cash_exposure.json",
        {
            "schema_version": "dynamic_cash_exposure.v1",
            "business_date": BUSINESS_DATE,
            "as_of": BUSINESS_DATE + "T00:00:00+00:00",
            "feature_date": BUSINESS_DATE,
            "artifact_lifecycle_status": "DRAFT",
            "source_authority_status": "VALID",
            "producer_result_status": "PASS",
            "runtime_consumer_eligibility": "NOT_ELIGIBLE",
            "minimum_cash_ratio": 0.0,
            "target_cash_ratio": target_cash_ratio,
            "maximum_cash_ratio": 0.50,
            "minimum_gross_exposure_ratio": 0.0,
            "target_gross_exposure_ratio": target_gross_exposure_ratio,
            "maximum_gross_exposure_ratio": 0.98,
            "portfolio_total_equity": portfolio_total_equity,
            "current_cash": portfolio_total_equity,
            "current_market_value": 0.0,
            "pending_reserved_cash": 0.0,
            "net_available_cash": portfolio_total_equity,
            "target_cash_amount": round(portfolio_total_equity * target_cash_ratio, 2),
            "target_invested_ratio": target_invested_ratio,
            "target_invested_notional": round(portfolio_total_equity * target_invested_ratio, 2),
            "current_invested_ratio": 0.0,
            "incremental_deployment_capacity": round(portfolio_total_equity * target_gross_exposure_ratio, 2),
            "strategy_fixed_jpy_exposure_cap_used": False,
            "legacy_max_exposure_authority_used": False,
            "current_cash_ratio": 1.0,
            "current_gross_exposure_ratio": 0.0,
            "cash_posture": "DEPLOY",
            "exposure_posture": "INCREASE",
            "capital_constraint_status": "SUFFICIENT",
            "confidence": 0.9,
            "uncertainty": "LOW",
            "reason_codes": ["phase26_step5_fixture_dynamic_cash_exposure_authority"],
            "source_artifacts": [{"role": "portfolio_policy", "path": "phase26_step5_fixture", "required": True, "status": "PASS"}],
            "source_hashes": [{"role": "portfolio_policy", "path": "phase26_step5_fixture", "sha256": "0" * 64}],
            "temporal_safety": {
                "point_in_time": True,
                "future_leakage_used": False,
                "feature_date_lte_business_date": True,
                "implicit_latest_fallback_used": False,
                "previous_day_dynamic_cash_exposure_copied": False,
            },
            "production_consumer_connected": False,
            "runtime_switch_performed": False,
            "position_sizing_decided": False,
            "allocation_decided": False,
            "quantity_decided": False,
            "lot_rounding_decided": False,
        },
    )


def _historical_context(tmp_path: Path) -> dict:
    return {
        "runtime_mode": "historical",
        "broker_environment": "historical_simulated",
        "historical_replay": True,
        "simulation": True,
        "broker_write": False,
        "external_delivery": False,
        "submit_enabled": False,
        "runtime_test_run_id": "runtime-test-phase23-az",
        "runtime_test_profile_id": "historical-smoke",
        "runtime_test_evidence_root": str(_evidence_root(tmp_path)),
    }


def _historical_safety_payload(tmp_path: Path) -> dict:
    return {
        "safety_authority": "historical_initial_no_external_effect",
        "safety_decision_id": "",
        "safety_policy_version": "historical_replay_neutral_safety_v1",
        "safety_source": "data_readiness_historical_temporal_authority",
        "safety_decision": "NEUTRAL",
        "safety_reason": "historical_neutral_no_event_safety_ready",
        "safety_business_date": BUSINESS_DATE,
        "temporal_authority_business_date": BUSINESS_DATE,
        "runtime_test_run_id": "runtime-test-phase23-az",
        "runtime_test_profile_id": "historical-smoke",
        "runtime_test_evidence_root": str(_evidence_root(tmp_path)),
    }


def _demo_safety_payload() -> dict:
    return {
        "safety_authority": "runtime_safety_decision",
        "safety_decision_id": "demo-safety-2026-07-15",
        "safety_policy_version": "runtime_safety_v1",
        "safety_source": "runtime_state/safety/latest_safety_decision.json",
        "safety_decision": "ALLOW",
        "safety_reason": "demo safety ready",
        "safety_business_date": BUSINESS_DATE,
        "temporal_authority_business_date": BUSINESS_DATE,
    }


def _demo_submit_safety_decision() -> RuntimeSafetyDecision:
    return RuntimeSafetyDecision(
        safety_decision_id="demo-safety-2026-07-15",
        safety_policy_version="runtime_safety_v1",
        safety_source="runtime_state/safety/latest_safety_decision.json",
        business_date=BUSINESS_DATE,
        runtime_mode="demo",
        decision="ALLOW",
        reason="demo safety ready",
        review_required=False,
        block_buy=False,
        block_sell=False,
        block_submit=False,
        halt_runtime=False,
        emergency_stop=False,
        generated_at=BUSINESS_DATE + "T08:00:00+09:00",
        expires_at=BUSINESS_DATE + "T15:00:00+09:00",
        safety_status="PASS",
    )


def _empty_broker_available_quantity_evidence() -> BrokerAvailableQuantityEvidence:
    return BrokerAvailableQuantityEvidence(checked=False, source="")


def _write_opportunity_rankings(path: Path, *, symbols: tuple[str, ...], no_buy_reasons: dict[str, str] | None = None) -> Path:
    no_buy_reasons = no_buy_reasons or {}
    rows = []
    for rank, symbol in enumerate(symbols, start=1):
        rows.append(
            {
                "artifact_role": "BUY_OPPORTUNITY_RANKING",
                "business_date": BUSINESS_DATE,
                "feature_date": BUSINESS_DATE,
                "target_date": BUSINESS_DATE,
                "symbol": symbol,
                "code": symbol,
                "buy_rank": rank,
                "rank": rank,
                "expected_edge_score": round(0.20 - rank * 0.001, 6),
                "expected_return": round(0.20 - rank * 0.001, 6),
                "no_buy_reason": no_buy_reasons.get(symbol, ""),
                "is_top5": rank <= 5,
                "schema_name": "runtime_v2_buy_opportunity_ranking",
                "model_version": "phase23-bd-test-opportunity-model",
            }
        )
    _write_json(
        path,
        {
            "schema_version": "runtime_v2_opportunity_ranking_v1",
            "status": "PASS",
            "business_date": BUSINESS_DATE,
            "feature_date": BUSINESS_DATE,
            "rankings": rows,
        },
    )
    return path


def _write_listed_issues_parquet(path: Path, *, rows: tuple[dict[str, object], ...]) -> Path:
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(list(rows)).to_parquet(path, index=False)
    return path


def _write_strategy_source_input_manifest(
    *,
    strategy_dir: Path,
    business_date: str,
    listed_issues_path: Path,
) -> None:
    listed_issues_hash = _file_sha256(listed_issues_path)
    _write_json(
        strategy_dir / "input_manifest.json",
        {
            "schema_version": "strategy_shadow_input_manifest.v1",
            "business_date": business_date,
            "strategy_source_authority": {
                "schema_version": "phase23_bm_strategy_source_authority.v1",
                "status": "PASS",
                "reason": "run_scoped_historical_logical_input_manifest",
                "authority": "historical_logical_input_manifest",
                "business_date": business_date,
                "resolution_source": "phase28_d14_fixture",
                "source_manifest_path": str(strategy_dir / "source_manifest.json"),
                "source_manifest_hash": "",
                "run_scoped_historical_authority_used": True,
                "operations_latest_fallback_used": False,
                "paths": {"listed_issues": str(listed_issues_path)},
                "source_records": {
                    "listed_issues": {
                        "path": str(listed_issues_path),
                        "exists": True,
                        "sha256": listed_issues_hash,
                        "expected_sha256": listed_issues_hash,
                        "business_date": business_date,
                        "pit_status": "PASS",
                    }
                },
                "expected_hashes": {"jquants_listed_issues": listed_issues_hash},
            },
        },
    )


def _write_capital_policy(
    path: Path,
    *,
    evaluation_capital: float = 1_000_000,
    max_exposure: float = 850_000,
) -> Path:
    _ = max_exposure
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": evaluation_capital,
            "max_positions": 10,
            "min_order_amount": 0,
            "max_buy_order_amount": None,
            "max_sell_liquidation_amount": None,
            "buy_notional_policy": "derived_from_capital_allocation_and_constraints",
            "sell_liquidation_policy": "current_owned_available_quantity_policy",
            "manual_review_threshold": {
                "buy_amount": None,
                "sell_liquidation_amount": None,
            },
        },
    )
    return path


def _submit_policy_payload(policy) -> dict:
    return {
        "submit_policy_authority": "capital_deployment_policy",
        "submit_policy_schema_version": "phase23_bb_submit_policy_authority.v1",
        "submit_policy_version": policy.policy_version,
        "submit_policy_source": policy.policy_source,
        "submit_policy_hash": capital_deployment_policy_hash(policy),
    }


def _historical_submit_safety_decision() -> RuntimeSafetyDecision:
    return RuntimeSafetyDecision(
        safety_decision_id="historical-neutral-safety:2026-07-15",
        safety_policy_version="historical_replay_neutral_safety_v1",
        safety_source="data_readiness_historical_temporal_authority",
        business_date=BUSINESS_DATE,
        runtime_mode="historical",
        decision="NEUTRAL",
        reason="historical_neutral_no_event_safety_ready",
        review_required=False,
        block_buy=False,
        block_sell=False,
        block_submit=False,
        halt_runtime=False,
        emergency_stop=False,
        generated_at=BUSINESS_DATE + "T08:00:00+09:00",
        expires_at=BUSINESS_DATE + "T15:00:00+09:00",
        safety_status="PASS",
        action_permissions={
            "buy_submit": "ALLOWED_FOR_REPLAY",
            "sell_submit": "ALLOWED_FOR_REPLAY",
            "broker_write": "BLOCKED",
        },
    )


def _evidence_root(tmp_path: Path) -> Path:
    return tmp_path / "reports" / "runtime_tests" / "runs" / "runtime-test-phase23-az"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _position_sizing_row(
    *,
    target_notional: float,
    target_quantity: int,
    quantity_delta: int,
    quantity_status: str = "RESOLVED_CANDIDATE",
    reference_price: float = 1000.0,
) -> dict[str, object]:
    return {
        "sizing_status": "SIZED" if target_notional > 0 else "RESOLVED_ZERO_ALLOCATION",
        "target_notional": target_notional,
        "current_notional": 0.0,
        "incremental_target_notional": target_notional,
        "incremental_buy_notional": max(target_notional, 0.0),
        "target_quantity_candidate": target_quantity,
        "quantity_delta_candidate": quantity_delta,
        "quantity_status": quantity_status,
        "reference_price": reference_price,
        "reference_price_authority": {
            "authority_type": "REFERENCE_PRICE_AUTHORITY",
            "business_date": BUSINESS_DATE,
            "canonical_field": "reference_price",
            "latest_fallback_used": False,
            "price_date": BUSINESS_DATE,
            "price_type": "planning_reference_close",
            "PIT_status": "PASS",
            "source_authority": "MARKET_EVIDENCE_AUTHORITY",
            "source_field": "close",
            "symbol": "",
        },
        "reference_price_resolution": {
            "status": "PASS",
            "reason": "reference_price_resolved",
            "resolved_price": reference_price,
            "review_reason": "",
        },
        "reference_price_type": "planning_reference_close",
        "reference_price_date": BUSINESS_DATE,
    }
