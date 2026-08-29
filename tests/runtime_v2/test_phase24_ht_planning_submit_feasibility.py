from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.order_reservation import (
    jpx_regular_stop_high_price,
    resolve_order_cash_reservation,
)
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    capital_deployment_policy_hash,
    load_capital_deployment_policy,
)
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import load_runtime_current_exposure
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline

from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings


def test_phase24_ht_planning_exposure_pass_allows_approved_pending(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=400_000, positions=[_position("1111", 100, 1000)])
    pending = _pending((_item("buy-1", amount=100_000),), policy=policy)
    approval = _approval(pending)

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=approval,
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.APPROVED
    assert linked.approved_item_ids == ("buy-1",)
    assert linked.planning_submit_feasibility["status"] == "PASS"


def test_phase32_db_runtime_rejects_positive_buy_with_blocked_marginal_capital_class(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=400_000, positions=[])
    blocked_item = replace(
        _item("buy-blocked", amount=100_000, symbol="94320", quantity=300),
        marginal_capital_value_class="BLOCKED_OR_NOT_ELIGIBLE",
        marginal_capital_value_authority={"authority_type": "MARGINAL_CAPITAL_VALUE_AUTHORITY"},
    )
    pending = _pending((blocked_item,), policy=policy)
    approval = _approval(pending)

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=approval,
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert linked.planning_submit_feasibility["status"] == "REVIEW_REQUIRED"
    assert item_evidence["violated_policy"] == "marginal_capital_value"
    assert item_evidence["reason"] == "blocked_marginal_capital_value_positive_buy_quantity"
    assert linked.approved_buy_item_ids == ()


def test_phase24_ht_planning_exposure_fail_blocks_approved_pending(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=265_230, positions=[_position("1111", 1, 685_510)])
    pending = _pending((_item("buy-1", amount=166_400),), policy=policy)
    approval = _approval(pending)

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=approval,
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    assert linked.approved_item_ids == ()
    assert linked.items[0].approved is False
    assert linked.planning_submit_feasibility["status"] == "REVIEW_REQUIRED"
    assert linked.planning_submit_feasibility["items"][0]["violated_policy"] == "dynamic_exposure"
    assert linked.planning_submit_feasibility["items"][0]["remaining_exposure"] == 122_619
    assert linked.planning_submit_feasibility["items"][0]["active_deployment_capital"] == 950_740
    assert linked.planning_submit_feasibility["items"][0]["selected_runtime_exposure_limit"] == 808_129
    assert linked.planning_submit_feasibility["items"][0]["legacy_exposure_config_used"] is False
    assert linked.planning_submit_feasibility["items"][0]["cash_exposure_fallback_used"] is False
    assert linked.planning_submit_feasibility["items"][0]["legacy_capital_config_used"] is False
    assert linked.review_scope == "BUY_ITEM_SCOPED_REVIEW"
    assert linked.sell_continuation_allowed is True
    assert linked.approved_buy_item_ids == ()
    assert linked.review_required_buy_item_ids == ("buy-1",)


def test_phase29_l21t_h_planning_feasibility_accepts_authorized_one_lot_selected_amount_delta(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=685_780, positions=[_position("1111", 100, 1546.65), _position("2222", 100, 1546.65)])
    pending = _pending(
        (
            _item(
                "buy-1",
                amount=242_000.0,
                symbol="78780",
                quantity_contract=_quantity_contract(symbol="78780", amount=241_999.81)
                | {
                    "selected_notional": 242_000.0,
                    "selected_quantity": 100,
                    "planned_quantity": 100,
                    "planning_intent": "BUY_NEW",
                    "position_sizing_authority": _one_lot_position_sizing_authority("BUY_NEW"),
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.APPROVED
    assert linked.approved_buy_item_ids == ("buy-1",)
    assert linked.planning_submit_feasibility["status"] == "PASS"
    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert item_evidence["selected_position_amount"] == 242_000.0
    assert item_evidence["one_lot_authority_consumed"] is True


def test_phase29_l21t_h_planning_feasibility_blocks_multi_lot_abuse(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=685_780, positions=[_position("1111", 100, 1546.65), _position("2222", 100, 1546.65)])
    pending = _pending(
        (
            _item(
                "buy-1",
                amount=484_000.0,
                symbol="78780",
                quantity=200,
                quantity_contract=_quantity_contract(symbol="78780", amount=241_999.81)
                | {
                    "selected_notional": 484_000.0,
                    "selected_quantity": 200,
                    "planned_quantity": 200,
                    "planning_intent": "BUY_NEW",
                    "quantity_delta_candidate": 200,
                    "position_sizing_authority": _one_lot_position_sizing_authority("BUY_NEW")
                    | {"quantity_delta_candidate": 200},
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    assert linked.approved_buy_item_ids == ()
    assert linked.planning_submit_feasibility["items"][0]["violated_policy"] == "position_sizing"


def test_phase30_ak3r1_submit_feasibility_accepts_authorized_minimum_executable_one_lot(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=400_000, positions=[_position("1111", 100, 1000)])
    pending = _pending(
        (
            _item(
                "buy-ak2",
                amount=100_000.0,
                symbol="78780",
                quantity=100,
                quantity_contract=_quantity_contract(symbol="78780", amount=70_000.0)
                | {
                    "selected_notional": 100_000.0,
                    "selected_quantity": 100,
                    "planned_quantity": 100,
                    "planning_intent": "BUY_NEW",
                    "position_sizing_authority": _ak2_minimum_one_lot_position_sizing_authority(
                        symbol="78780",
                        selected_position_amount=70_000.0,
                        one_lot_notional=100_000.0,
                    ),
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.APPROVED
    assert linked.approved_buy_item_ids == ("buy-ak2",)
    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert item_evidence["status"] == "PASS"
    assert item_evidence["strategy_executable_notional"] == 100_000.0
    assert item_evidence["selected_position_amount"] == 100_000.0
    assert item_evidence["strategy_requested_position_amount"] == 70_000.0
    assert item_evidence["one_lot_authority_consumed"] is True
    assert item_evidence["one_lot_authority_reason"] == "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED"
    assert item_evidence["one_lot_submit_authority"]["status"] == "PASS"


def test_phase32_co_submit_feasibility_accepts_admit_one_lot_decision(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=400_000, positions=[_position("1111", 100, 1000)])
    pending = _pending(
        (
            _item(
                "buy-co",
                amount=100_000.0,
                symbol="78780",
                quantity=100,
                quantity_contract=_quantity_contract(symbol="78780", amount=70_000.0)
                | {
                    "selected_notional": 100_000.0,
                    "selected_quantity": 100,
                    "planned_quantity": 100,
                    "planning_intent": "BUY_NEW",
                    "position_sizing_authority": _ak2_minimum_one_lot_position_sizing_authority(
                        symbol="78780",
                        selected_position_amount=70_000.0,
                        one_lot_notional=100_000.0,
                        one_lot_decision="ADMIT_ONE_LOT",
                    ),
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.APPROVED
    assert linked.approved_buy_item_ids == ("buy-co",)
    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert item_evidence["one_lot_authority_consumed"] is True
    assert item_evidence["one_lot_submit_authority"]["status"] == "PASS"


def test_phase30_ak3r1_submit_feasibility_preserves_review_without_one_lot_authority(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=400_000, positions=[_position("1111", 100, 1000)])
    pending = _pending(
        (
            _item(
                "buy-no-authority",
                amount=100_000.0,
                symbol="78780",
                quantity=100,
                quantity_contract=_quantity_contract(symbol="78780", amount=70_000.0),
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert item_evidence["violated_policy"] == "position_sizing"
    assert item_evidence["reason"] == "estimated amount exceeds selected_position_amount"
    assert item_evidence["one_lot_authority_consumed"] is False


def test_phase30_ak3r1_submit_feasibility_blocks_tampered_one_lot_authority_symbol(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=400_000, positions=[_position("1111", 100, 1000)])
    authority = _ak2_minimum_one_lot_position_sizing_authority(
        symbol="99990",
        selected_position_amount=70_000.0,
        one_lot_notional=100_000.0,
    )
    authority["symbol"] = "78780"
    pending = _pending(
        (
            _item(
                "buy-mismatch",
                amount=100_000.0,
                symbol="78780",
                quantity=100,
                quantity_contract=_quantity_contract(symbol="78780", amount=70_000.0)
                | {
                    "selected_notional": 100_000.0,
                    "selected_quantity": 100,
                    "planned_quantity": 100,
                    "planning_intent": "BUY_NEW",
                    "position_sizing_authority": authority,
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert item_evidence["violated_policy"] == "position_sizing"
    assert item_evidence["reason"] == "one_lot_authority_symbol_mismatch"


def test_phase30_ak3r1_submit_feasibility_blocks_second_lot_plus_with_ak2_authority(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=500_000, positions=[_position("1111", 100, 1000)])
    pending = _pending(
        (
            _item(
                "buy-two-lots",
                amount=200_000.0,
                symbol="78780",
                quantity=200,
                quantity_contract=_quantity_contract(symbol="78780", amount=70_000.0)
                | {
                    "selected_notional": 200_000.0,
                    "selected_quantity": 200,
                    "planned_quantity": 200,
                    "planning_intent": "BUY_NEW",
                    "position_sizing_authority": _ak2_minimum_one_lot_position_sizing_authority(
                        symbol="78780",
                        selected_position_amount=70_000.0,
                        one_lot_notional=100_000.0,
                    ),
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert item_evidence["violated_policy"] == "position_sizing"
    assert item_evidence["reason"] in {
        "estimated amount exceeds selected_position_amount",
        "one_lot_authority_quantity_mismatch",
        "one_lot_authority_notional_mismatch",
    }


def test_phase30_ak3r1_mixed_atomic_batch_allows_legacy_and_authorized_one_lot(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=500_000, positions=[_position("1111", 100, 1000)])
    pending = _pending(
        (
            _item("buy-legacy", amount=50_000.0, symbol="7203", quantity=100),
            _item(
                "buy-ak2",
                amount=100_000.0,
                symbol="78780",
                quantity=100,
                quantity_contract=_quantity_contract(symbol="78780", amount=70_000.0)
                | {
                    "selected_notional": 100_000.0,
                    "selected_quantity": 100,
                    "planned_quantity": 100,
                    "planning_intent": "BUY_NEW",
                    "position_sizing_authority": _ak2_minimum_one_lot_position_sizing_authority(
                        symbol="78780",
                        selected_position_amount=70_000.0,
                        one_lot_notional=100_000.0,
                    ),
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.APPROVED
    assert linked.approved_buy_item_ids == ("buy-legacy", "buy-ak2")
    assert linked.planning_submit_feasibility["status"] == "PASS"
    assert [item["status"] for item in linked.planning_submit_feasibility["items"]] == ["PASS", "PASS"]


def test_phase30_ak9r1b_accepts_pc_discrete_quantity_over_selected_amount(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=400_000, positions=[_position("1111", 100, 1000)])
    pending = _pending(
        (
            _item(
                "buy-pc-discrete",
                amount=45_300.0,
                symbol="23880",
                quantity=300,
                quantity_contract=_quantity_contract(symbol="23880", amount=39_054.0)
                | {
                    "selected_notional": 45_300.0,
                    "selected_quantity": 300,
                    "planned_quantity": 300,
                    "planning_intent": "BUY_NEW",
                    "position_sizing_authority": _pc_discrete_position_sizing_authority(
                        symbol="23880",
                        selected_position_amount=39_054.0,
                        executable_quantity=300,
                        executable_notional=45_300.0,
                    ),
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.APPROVED
    assert linked.approved_buy_item_ids == ("buy-pc-discrete",)
    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert item_evidence["status"] == "PASS"
    assert item_evidence["selected_position_amount"] == 39_054.0
    assert item_evidence["canonical_discrete_quantity_submit_authority"]["status"] == "PASS"
    assert item_evidence["canonical_discrete_quantity_precedence_applied"] is True


def test_phase30_ak9r1b_preserves_selected_amount_review_without_pc_authority(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=400_000, positions=[_position("1111", 100, 1000)])
    pending = _pending(
        (
            _item(
                "buy-no-pc-discrete",
                amount=45_300.0,
                symbol="23880",
                quantity=300,
                quantity_contract=_quantity_contract(symbol="23880", amount=39_054.0),
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert item_evidence["violated_policy"] == "position_sizing"
    assert item_evidence["reason"] == "estimated amount exceeds selected_position_amount"
    assert item_evidence["canonical_discrete_quantity_submit_authority"]["status"] == "NOT_APPLICABLE"


def test_phase30_ak9r1b_blocks_pc_ps_quantity_mismatch(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=400_000, positions=[_position("1111", 100, 1000)])
    pending = _pending(
        (
            _item(
                "buy-pc-mismatch",
                amount=45_300.0,
                symbol="23880",
                quantity=200,
                quantity_contract=_quantity_contract(symbol="23880", amount=39_054.0)
                | {
                    "selected_notional": 45_300.0,
                    "selected_quantity": 200,
                    "planned_quantity": 200,
                    "planning_intent": "BUY_NEW",
                    "position_sizing_authority": _pc_discrete_position_sizing_authority(
                        symbol="23880",
                        selected_position_amount=39_054.0,
                        executable_quantity=300,
                        executable_notional=45_300.0,
                    ),
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    assert item_evidence["violated_policy"] == "position_sizing"
    assert item_evidence["reason"] == "pc_discrete_quantity_authority_quantity_mismatch"


def test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=400_000, positions=[_position("94340", 200, 150.0)])
    authority = _pc_discrete_position_sizing_authority(
        symbol="94340",
        selected_position_amount=15_000.0,
        executable_quantity=100,
        executable_notional=15_000.0,
        intent="BUY_ADD",
    )
    authority["current_quantity"] = 200
    authority["discrete_authorized_quantity"] = 100
    authority["phase29_l19_lot_resolution"].update(
        {
            "current_quantity": 200,
            "current_weight": 0.03,
            "final_allocated_quantity": 100,
            "executable_quantity_delta": 200,
            "preflight_executable_quantity_delta": 200,
            "semantic_type": "BUY_ADD",
        }
    )
    authority["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"][
        "final_allocated_quantity"
    ] = 100
    pending = _pending(
        (
            _item(
                "buy-add-g129",
                amount=15_000.0,
                symbol="94340",
                quantity=100,
                quantity_contract=_quantity_contract(symbol="94340", amount=15_000.0)
                | {
                    "selected_notional": 15_000.0,
                    "selected_quantity": 100,
                    "planned_quantity": 100,
                    "planning_intent": "BUY_ADD",
                    "position_sizing_authority": authority,
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert linked.state == PendingPlanState.APPROVED
    assert item_evidence["status"] == "PASS"
    assert item_evidence["canonical_discrete_quantity_submit_authority"]["status"] == "PASS"
    assert item_evidence["canonical_discrete_quantity_submit_authority"]["quantity_scope"] == "ORDER_INCREMENT"
    assert item_evidence["canonical_discrete_quantity_submit_authority"]["authorized_quantity"] == 100


def test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=400_000, positions=[_position("94320", 200, 150.0)])
    authority = _pc_discrete_position_sizing_authority(
        symbol="94320",
        selected_position_amount=15_000.0,
        executable_quantity=100,
        executable_notional=15_000.0,
        intent="BUY_ADD",
    )
    authority["discrete_authorized_quantity"] = 100
    authority["phase29_l19_lot_resolution"]["semantic_type"] = "BUY_ADD"
    authority["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"][
        "final_allocated_quantity"
    ] = 100
    pending = _pending(
        (
            _item(
                "buy-add-g129-mismatch",
                amount=30_000.0,
                symbol="94320",
                quantity=200,
                quantity_contract=_quantity_contract(symbol="94320", amount=30_000.0)
                | {
                    "selected_notional": 30_000.0,
                    "selected_quantity": 200,
                    "planned_quantity": 200,
                    "planning_intent": "BUY_ADD",
                    "position_sizing_authority": authority,
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    assert item_evidence["violated_policy"] == "position_sizing"
    assert item_evidence["reason"] == "pc_discrete_quantity_authority_quantity_mismatch"


def test_phase30_ak9r1b_blocks_pc_discrete_strategy_or_safety_breach(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=400_000, positions=[_position("1111", 100, 1000)])
    authority = _pc_discrete_position_sizing_authority(
        symbol="23880",
        selected_position_amount=39_054.0,
        executable_quantity=300,
        executable_notional=45_300.0,
    )
    authority["phase29_l19_lot_resolution"]["safety_hard_cap_preserved"] = False
    pending = _pending(
        (
            _item(
                "buy-pc-safety-breach",
                amount=45_300.0,
                symbol="23880",
                quantity=300,
                quantity_contract=_quantity_contract(symbol="23880", amount=39_054.0)
                | {
                    "selected_notional": 45_300.0,
                    "selected_quantity": 300,
                    "planned_quantity": 300,
                    "planning_intent": "BUY_NEW",
                    "position_sizing_authority": authority,
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    assert item_evidence["violated_policy"] == "position_sizing"
    assert item_evidence["reason"] == "pc_discrete_quantity_authority_safety_hard_cap_not_preserved"


def test_phase30_ak9r21_buy_new_pc_discrete_soft_cap_overshoot_passes_submit(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=900_000, positions=[_position("1111", 100, 1000)])
    authority = _pc_discrete_position_sizing_authority(
        symbol="47770",
        selected_position_amount=60_000.0,
        executable_quantity=100,
        executable_notional=68_400.0,
        intent="BUY_NEW",
    )
    lot_resolution = authority["phase29_l19_lot_resolution"]
    lot_resolution.update(
        {
            "boundary_classification": "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX",
            "lot_overshoot_reason": "LOT_AWARE_STRATEGY_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP",
            "strategy_cap_overshoot_applied": True,
            "maximum_strategy_feasible_lots": 0,
            "maximum_safety_feasible_lots": 1,
            "strategy_cap_preserved": True,
            "safety_hard_cap_preserved": True,
        }
    )
    pending = _pending(
        (
            _item(
                "buy-new-pc-overshoot",
                amount=68_400.0,
                symbol="47770",
                quantity=100,
                quantity_contract=_quantity_contract(symbol="47770", amount=60_000.0)
                | {
                    "selected_notional": 68_400.0,
                    "selected_quantity": 100,
                    "planned_quantity": 100,
                    "planning_intent": "BUY_NEW",
                    "position_sizing_authority": authority,
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert linked.state == PendingPlanState.APPROVED
    assert item_evidence["status"] == "PASS"
    assert item_evidence["canonical_discrete_quantity_submit_authority"]["status"] == "PASS"
    assert item_evidence["canonical_discrete_quantity_precedence_applied"] is True


def test_phase30_ak9r21_buy_add_second_lot_promotion_passes_submit(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=900_000, positions=[_position("89180", 100, 1000)])
    authority = _pc_discrete_position_sizing_authority(
        symbol="89180",
        selected_position_amount=85_000.0,
        executable_quantity=100,
        executable_notional=95_000.0,
        intent="BUY_ADD",
    )
    authority["current_quantity"] = 100
    lot_resolution = authority["phase29_l19_lot_resolution"]
    lot_resolution.update(
        {
            "boundary_classification": "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX",
            "current_quantity": 100,
            "lot_overshoot_reason": "SECOND_LOT_PLUS_RESIDUAL_CAPITAL_AWARE_PROMOTION",
            "maximum_strategy_feasible_lots": 0,
            "maximum_safety_feasible_lots": 2,
            "second_lot_plus_promotion": {"promotion_candidate": True, "decision": "PROMOTE"},
            "semantic_type": "BUY_ADD",
            "strategy_cap_overshoot_applied": True,
            "strategy_cap_preserved": True,
            "safety_hard_cap_preserved": True,
        }
    )
    pending = _pending(
        (
            _item(
                "buy-add-pc-overshoot",
                amount=95_000.0,
                symbol="89180",
                quantity=100,
                quantity_contract=_quantity_contract(symbol="89180", amount=85_000.0)
                | {
                    "selected_notional": 95_000.0,
                    "selected_quantity": 100,
                    "planned_quantity": 100,
                    "planning_intent": "BUY_ADD",
                    "position_sizing_authority": authority,
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert linked.state == PendingPlanState.APPROVED
    assert item_evidence["status"] == "PASS"
    assert item_evidence["canonical_discrete_quantity_submit_authority"]["status"] == "PASS"
    assert item_evidence["canonical_discrete_quantity_precedence_applied"] is True


def test_phase30_ak9r21_rejects_unknown_pc_discrete_overshoot_reason(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=900_000, positions=[_position("1111", 100, 1000)])
    authority = _pc_discrete_position_sizing_authority(
        symbol="23880",
        selected_position_amount=60_000.0,
        executable_quantity=100,
        executable_notional=68_400.0,
    )
    lot_resolution = authority["phase29_l19_lot_resolution"]
    lot_resolution.update(
        {
            "lot_overshoot_reason": "UNAUTHORIZED_SOFT_CAP_OVERSHOOT",
            "maximum_strategy_feasible_lots": 0,
            "maximum_safety_feasible_lots": 1,
            "strategy_cap_preserved": True,
            "safety_hard_cap_preserved": True,
        }
    )
    pending = _pending(
        (
            _item(
                "buy-unknown-overshoot",
                amount=68_400.0,
                symbol="23880",
                quantity=100,
                quantity_contract=_quantity_contract(symbol="23880", amount=60_000.0)
                | {
                    "selected_notional": 68_400.0,
                    "selected_quantity": 100,
                    "planned_quantity": 100,
                    "planning_intent": "BUY_NEW",
                    "position_sizing_authority": authority,
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    assert item_evidence["violated_policy"] == "position_sizing"
    assert item_evidence["reason"] == "pc_discrete_quantity_authority_strategy_cap_not_preserved"


def test_phase30_ak9r21_rejects_malformed_second_lot_promotion(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=900_000, positions=[_position("89180", 100, 1000)])
    authority = _pc_discrete_position_sizing_authority(
        symbol="89180",
        selected_position_amount=85_000.0,
        executable_quantity=100,
        executable_notional=95_000.0,
        intent="BUY_ADD",
    )
    lot_resolution = authority["phase29_l19_lot_resolution"]
    lot_resolution.update(
        {
            "lot_overshoot_reason": "SECOND_LOT_PLUS_RESIDUAL_CAPITAL_AWARE_PROMOTION",
            "maximum_strategy_feasible_lots": 1,
            "maximum_safety_feasible_lots": 2,
            "second_lot_plus_promotion": {"promotion_candidate": False, "decision": "NO_PROMOTION"},
            "semantic_type": "BUY_ADD",
            "strategy_cap_preserved": True,
            "safety_hard_cap_preserved": True,
        }
    )
    pending = _pending(
        (
            _item(
                "buy-add-malformed-promotion",
                amount=95_000.0,
                symbol="89180",
                quantity=100,
                quantity_contract=_quantity_contract(symbol="89180", amount=85_000.0)
                | {
                    "selected_notional": 95_000.0,
                    "selected_quantity": 100,
                    "planned_quantity": 100,
                    "planning_intent": "BUY_ADD",
                    "position_sizing_authority": authority,
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    assert item_evidence["violated_policy"] == "position_sizing"
    assert item_evidence["reason"] == "pc_discrete_quantity_authority_lot_overshoot_unresolved"


def test_phase31_g104_accepts_g102_item_scoped_pc_discrete_authority(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=400_000, positions=[_position("1111", 100, 1000)])
    authority = _g104_g102_pc_discrete_position_sizing_authority()
    pending = _pending(
        (
            _item(
                "buy-g104-94320",
                amount=41_940.0,
                symbol="94320",
                quantity=200,
                quantity_contract=_quantity_contract(symbol="94320", amount=41_940.0)
                | {
                    "selected_notional": 41_940.0,
                    "selected_quantity": 200,
                    "planned_quantity": 200,
                    "planning_intent": "BUY_NEW",
                    "position_sizing_authority": authority,
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert linked.state == PendingPlanState.APPROVED
    assert linked.approved_buy_item_ids == ("buy-g104-94320",)
    assert item_evidence["status"] == "PASS"
    assert item_evidence["canonical_discrete_quantity_submit_authority"]["status"] == "PASS"
    assert item_evidence["canonical_discrete_quantity_submit_authority"]["authorized_quantity"] == 200
    assert item_evidence["canonical_discrete_quantity_precedence_applied"] is True


@pytest.mark.parametrize(
    ("case_name", "mutate", "quantity"),
    (
        (
            "authority_not_pass",
            lambda authority: authority["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"].update({"status": "REVIEW_REQUIRED"}),
            200,
        ),
        ("item_quantity_mismatch", lambda authority: None, 100),
        (
            "ps_quantity_mismatch",
            lambda authority: authority["phase29_l19_lot_resolution"].update({"ps_final_quantity": 100}),
            200,
        ),
        (
            "future_information_used",
            lambda authority: authority["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"].update({"future_information_used": True}),
            200,
        ),
        (
            "ps_must_consume_false",
            lambda authority: authority["phase29_l19_lot_resolution"]["pc_positive_executable_quantity_authority"].update({"ps_must_consume_canonical_quantity": False}),
            200,
        ),
        (
            "invalid_semantic",
            lambda authority: authority["phase29_l19_lot_resolution"].update({"semantic_type": "SELL_EXIT"}),
            200,
        ),
        (
            "strategy_cap_not_preserved",
            lambda authority: authority["phase29_l19_lot_resolution"].update({"strategy_cap_preserved": False}),
            200,
        ),
        (
            "safety_hard_cap_not_preserved",
            lambda authority: authority["phase29_l19_lot_resolution"].update({"safety_hard_cap_preserved": False}),
            200,
        ),
        (
            "one_lot_not_pass",
            lambda authority: authority["phase29_l19_lot_resolution"].update({"one_lot_feasibility_status": "FAIL"}),
            200,
        ),
        (
            "arbitrary_unknown_reason",
            lambda authority: authority["phase29_l19_lot_resolution"].update({"lot_overshoot_reason": "ARBITRARY_UNKNOWN_REASON"}),
            200,
        ),
        (
            "lot_infeasible_compatibility",
            lambda authority: authority["phase29_l19_lot_resolution"]["lot_aware_allocation_to_sizing_compatibility"].update(
                {"compatibility_state": "LOT_INFEASIBLE_RESIDUAL_REQUIRED"}
            ),
            200,
        ),
    ),
)
def test_phase31_g104_g102_item_scoped_authority_fail_closed(
    tmp_path: Path,
    case_name: str,
    mutate,
    quantity: int,
) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=400_000, positions=[_position("1111", 100, 1000)])
    authority = _g104_g102_pc_discrete_position_sizing_authority()
    mutate(authority)
    pending = _pending(
        (
            _item(
                f"buy-g104-negative-{case_name}",
                amount=41_940.0,
                symbol="94320",
                quantity=quantity,
                quantity_contract=_quantity_contract(symbol="94320", amount=41_940.0)
                | {
                    "selected_notional": 41_940.0,
                    "selected_quantity": quantity,
                    "planned_quantity": quantity,
                    "planning_intent": "BUY_NEW",
                    "position_sizing_authority": authority,
                },
            ),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    assert item_evidence["violated_policy"] == "position_sizing"
    assert item_evidence["canonical_discrete_quantity_submit_authority"]["status"] == "REVIEW_REQUIRED"


def test_phase24_id_planning_aggregate_cash_reservation_blocks_later_buy(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=250_000, positions=[_position("1111", 100, 1000)])
    pending = _pending(
        (
            _item("buy-1", amount=60_000, symbol="7203"),
            _item("buy-2", amount=60_000, symbol="6758"),
            _item("buy-3", amount=150_000, symbol="9984"),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    assert linked.planning_submit_feasibility["reservation_contract"] == "phase24_id_aggregate_pending_batch_reservation_v1"
    assert linked.planning_submit_feasibility["items"][0]["status"] == "PASS"
    assert linked.planning_submit_feasibility["items"][0]["post_buy_cash"] == 190_000
    assert linked.planning_submit_feasibility["items"][1]["status"] == "PASS"
    assert linked.planning_submit_feasibility["items"][2]["status"] == "REVIEW_REQUIRED"
    assert linked.planning_submit_feasibility["items"][2]["cash"] == 130_000
    assert linked.planning_submit_feasibility["items"][2]["violated_policy"] == "cash"
    assert linked.approved_item_ids == ()
    assert linked.approved_buy_item_ids == ()
    assert linked.review_required_buy_item_ids == ("buy-3",)
    assert linked.items[0].approved is False
    assert linked.items[0].feasibility_status == "PASS"
    assert linked.items[0].batch_submit_status == "BLOCKED_BY_BATCH_REVIEW"
    assert linked.items[0].item_review_reason == "batch_submit_blocked_by_item_scoped_review"
    assert linked.items[1].approved is False
    assert linked.items[1].feasibility_status == "PASS"
    assert linked.items[1].batch_submit_status == "BLOCKED_BY_BATCH_REVIEW"
    assert linked.items[2].approved is False
    assert linked.items[2].feasibility_status == "REVIEW_REQUIRED"
    assert linked.items[2].batch_submit_status == "ITEM_REVIEW_REQUIRED"


def test_phase29_l21t_q1_market_buy_uses_reserved_notional_for_aggregate_cash(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=250_000, positions=[])

    def reserved_item(item_id: str, symbol: str) -> PendingOrderItem:
        base = _item(item_id, amount=60_000, symbol=symbol, quantity=100)
        return replace(
            base,
            reservation_price=1000.0,
            reserved_notional=100_000.0,
            reservation_price_authority={
                "authority_type": "ORDER_CONDITION_DERIVED_RESERVATION_PRICE_AUTHORITY",
                "reservation_price_type": "market_order_cash_estimate",
                "future_execution_price_used": False,
            },
            reservation_reason="phase29_l21t_q1_fixture_market_buy_reservation",
            quantity_contract=_quantity_contract(symbol=symbol, amount=100_000),
        )

    pending = _pending(
        (
            reserved_item("buy-1", "7203"),
            reserved_item("buy-2", "6758"),
            reserved_item("buy-3", "9984"),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    assert linked.planning_submit_feasibility["items"][0]["reserved_notional"] == 100_000
    assert linked.planning_submit_feasibility["items"][1]["post_buy_cash"] == 50_000
    assert linked.planning_submit_feasibility["items"][2]["status"] == "REVIEW_REQUIRED"
    assert linked.planning_submit_feasibility["items"][2]["violated_policy"] == "cash"
    assert linked.approved_item_ids == ()


def test_phase29_l21t_q1b_market_buy_reservation_uses_previous_close_stop_high(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    quote_path = root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    quote_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"Date": "2023-06-07", "Code": "67310", "Close": 3000.0},
            {"Date": "2023-06-08", "Code": "67310", "Open": 3000.0, "High": 3000.0, "Low": 2000.0, "Close": 2000.0},
        ]
    ).to_parquet(quote_path, index=False)

    reservation = resolve_order_cash_reservation(
        runtime_root=root,
        business_date="2023-06-08",
        symbol="67310",
        side="BUY",
        order_type="MARKET",
        quantity=100,
        reference_price=2000.0,
        reference_price_authority={"source_field": "target_day_close_fixture_should_not_drive_reservation"},
    )
    authority = reservation["reservation_price_authority"]

    assert jpx_regular_stop_high_price(3000.0) == 3700.0
    assert reservation["reservation_price"] == 3700.0
    assert reservation["reservation_price_type"] == "market_buy_stop_high_cash_reservation"
    assert reservation["reserved_notional"] == 370000.0
    assert authority["reservation_price_type"] == "market_buy_stop_high_cash_reservation"
    assert authority["basis"]["basis_date"] == "2023-06-07"
    assert authority["basis"]["base_price"] == 3000.0
    assert authority["future_execution_price_used"] is False
    assert authority["target_day_ohlc_used"] is False
    assert authority["arbitrary_percentage_buffer_used"] is False
    assert authority["runtime_path"] == "Production/Demo/Historical common runtime_v2"


def test_phase29_l21t_q1b_limit_buy_reservation_uses_limit_price(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)

    reservation = resolve_order_cash_reservation(
        runtime_root=root,
        business_date="2026-07-09",
        symbol="7203",
        side="BUY",
        order_type="LIMIT",
        quantity=100,
        reference_price=1800.0,
        limit_price=1750.0,
    )

    assert reservation["reservation_price"] == 1750.0
    assert reservation["reservation_price_type"] == "limit_order_limit_price_cash_reservation"
    assert reservation["reserved_notional"] == 175000.0
    assert reservation["reservation_price_authority"]["reservation_price_type"] == "limit_order_limit_price_cash_reservation"
    assert reservation["reservation_price_authority"]["future_execution_price_used"] is False


def test_phase29_l21t_q1b_market_buy_stop_high_aggregate_blocks_batch_before_submit(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=437_870, positions=[])
    quote_path = root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    quote_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"Date": "2023-06-07", "Code": "30410", "Close": 1203.0},
            {"Date": "2023-06-07", "Code": "59550", "Close": 101.0},
            {"Date": "2023-06-07", "Code": "67310", "Close": 3000.0},
        ]
    ).to_parquet(quote_path, index=False)

    def market_item(item_id: str, symbol: str, reference_price: float, quantity: float) -> PendingOrderItem:
        reservation = resolve_order_cash_reservation(
            runtime_root=root,
            business_date="2023-06-08",
            symbol=symbol,
            side="BUY",
            order_type="MARKET",
            quantity=quantity,
            reference_price=reference_price,
        )
        base = _item(item_id, amount=reference_price * quantity, symbol=symbol, quantity=quantity)
        return replace(
            base,
            reference_price=reference_price,
            reservation_price=reservation["reservation_price"],
            reservation_price_type=reservation["reservation_price_type"],
            reservation_price_authority=reservation["reservation_price_authority"],
            reservation_reason=reservation["reservation_reason"],
            reserved_notional=reservation["reserved_notional"],
            quantity_contract=_quantity_contract(symbol=symbol, amount=reservation["reserved_notional"]),
        )

    pending = _pending(
        (
            market_item("buy-30410", "30410", 1203.0, 100),
            market_item("buy-59550", "59550", 101.0, 1100),
            market_item("buy-67310", "67310", 2000.0, 100),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    assert linked.approved_item_ids == ()
    assert linked.planning_submit_feasibility["items"][2]["reserved_notional"] == 370000.0
    assert linked.planning_submit_feasibility["items"][2]["violated_policy"] == "cash"
    assert linked.review_scope == "BUY_ITEM_SCOPED_REVIEW"
    assert linked.sell_continuation_allowed is True


def test_phase29_l21t_s_market_buy_reservation_does_not_violate_strategy_sizing(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=609_670.0, positions=[_position("1111", 100, 3123.6)])
    item = _reserved_market_item(
        "buy-59550",
        symbol="59550",
        reference_amount=108_000.0,
        selected_position_amount=115_253.75,
        reserved_notional=152_000.0,
        quantity=1000,
        reference_price=108.0,
        reservation_price=152.0,
    )
    pending = _pending((item,), policy=policy)

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.APPROVED
    assert linked.approved_buy_item_ids == ("buy-59550",)
    assert linked.planning_submit_feasibility["status"] == "PASS"
    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert item_evidence["strategy_executable_notional"] == 108_000.0
    assert item_evidence["selected_position_amount"] == 115_253.75
    assert item_evidence["reserved_notional"] == 152_000.0
    assert item_evidence["status"] == "PASS"
    assert item_evidence["reason"] != "reserved notional exceeds selected_position_amount"


def test_phase29_l21t_s_market_buy_reservation_still_blocks_cash_shortfall(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=100_000.0, positions=[])
    item = _reserved_market_item(
        "buy-59550",
        symbol="59550",
        reference_amount=108_000.0,
        selected_position_amount=115_253.75,
        reserved_notional=152_000.0,
        quantity=1000,
        reference_price=108.0,
        reservation_price=152.0,
    )
    pending = _pending((item,), policy=policy)

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert item_evidence["violated_policy"] == "cash"
    assert item_evidence["reason"] == "reserved notional exceeds Current cash"
    assert linked.review_scope == "BUY_ITEM_SCOPED_REVIEW"


def test_phase29_l21t_s_strategy_executable_notional_still_blocks_sizing_violation(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=609_670.0, positions=[_position("1111", 100, 3123.6)])
    item = _reserved_market_item(
        "buy-59550",
        symbol="59550",
        reference_amount=108_000.0,
        selected_position_amount=100_000.0,
        reserved_notional=109_000.0,
        quantity=1000,
        reference_price=108.0,
        reservation_price=109.0,
    )
    pending = _pending((item,), policy=policy)

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    item_evidence = linked.planning_submit_feasibility["items"][0]
    assert item_evidence["strategy_executable_notional"] == 108_000.0
    assert item_evidence["reserved_notional"] == 109_000.0
    assert item_evidence["violated_policy"] == "position_sizing"
    assert item_evidence["reason"] == "estimated amount exceeds selected_position_amount"


def test_phase24_id_submit_aggregate_preflight_blocks_before_adapter_boundary(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=900_000, positions=[_position("1111", 100, 1000)])
    pending = _pending(
        (
            _item("buy-1", amount=175_000, symbol="7203"),
            _item("buy-2", amount=175_000, symbol="6758"),
            _item("buy-3", amount=175_000, symbol="9984"),
        ),
        policy=policy,
    )
    pending = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )
    assert pending.state == PendingPlanState.APPROVED
    _write_current(root, cash=100_000, positions=[_position("1111", 100, 9000)])
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.submitted_count == 0
    assert result.reason == "submit blocked before broker boundary; manual review required"
    blocked = [item for item in result.submit_guard_item_evidence if item["guard_decision"] == "BLOCKED"]
    assert blocked
    assert {item["violated_policy"] for item in blocked} == {"cash"}


def test_phase24_ht_planning_pass_then_submit_guard_passes(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=500_000, positions=[_position("1111", 100, 1000)])
    pending = _pending((_item("buy-1", amount=100_000),), policy=policy)
    pending = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.submit_guard_item_evidence[0]["guard_decision"] == "BLOCKED"
    assert result.submit_guard_item_evidence[0]["violated_policy"] == "accepted_generation_binding"


def test_phase24_ht_submit_guard_revalidates_after_planning_pass(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=500_000, positions=[_position("1111", 100, 1000)])
    pending = _pending((_item("buy-1", amount=100_000),), policy=policy)
    pending = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )
    assert pending.planning_submit_feasibility["status"] == "PASS"
    _write_current(root, cash=300_000, positions=[_position("1111", 1, 1_600_000)])
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.submit_guard_item_evidence[0]["guard_decision"] == "BLOCKED"
    assert result.submit_guard_item_evidence[0]["violated_policy"] == "dynamic_exposure"


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "persistent_ledger").mkdir(parents=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (root / "persistent_ledger" / f"{name}.jsonl").write_text("", encoding="utf-8")
    _write_safety(root)
    return root


def _pending(items: tuple[PendingOrderItem, ...], *, policy) -> object:
    items = tuple(
        item.__class__(
            **{
                **item.__dict__,
                "policy_version": policy.policy_version,
                "policy_source": policy.policy_source,
                "submit_policy_version": policy.policy_version,
                "submit_policy_source": policy.policy_source,
                "submit_policy_hash": capital_deployment_policy_hash(policy),
                "evaluation_capital": policy.evaluation_capital,
                "target_investment_ratio": None,
                "cash_buffer": None,
                "max_exposure": None,
                "max_positions": policy.max_positions,
                "buy_notional_policy": policy.buy_notional_policy,
                "sell_liquidation_policy": policy.sell_liquidation_policy,
            }
        )
        for item in items
    )
    pending = promote_order_plan_to_pending(
        order_plan_id="order-plan-phase24-ht",
        source_order_plan_path=".runtime/runtime_state/morning/order_plan.json",
        source_order_plan_hash="sha256:phase24-ht-order-plan",
        environment="demo",
        plan_created_date="2026-07-09",
        intended_submit_date="2026-07-09",
        target_session_date="2026-07-09",
        items=items,
    )
    return pending.__class__(
        **{
            **pending.__dict__,
            "policy_context": {
                "policy_version": policy.policy_version,
                "policy_source": policy.policy_source,
                "target_position_count": 8,
                "selected_dynamic_position_count": 8,
                "safety_hard_maximum": None,
                "legacy_position_count_config_used": False,
                "position_count_fallback_used": False,
                "target_cash_ratio": 0.10,
                "target_gross_exposure_ratio": 0.85,
                "maximum_gross_exposure_ratio": 0.90,
                "legacy_cash_config_used": False,
                "legacy_exposure_config_used": False,
                "cash_exposure_fallback_used": False,
            },
        }
    )


def _approval(pending) -> ApprovalArtifact:
    return ApprovalArtifact(
        approval_id="approval-phase24-ht",
        approval_request_id="approval-request-phase24-ht",
        pending_plan_id=pending.pending_plan_id,
        order_plan_id=pending.source_order_plan.order_plan_id,
        status=ApprovalStatus.APPROVED,
        approved_item_ids=tuple(item.pending_item_id for item in pending.items),
        rejected_item_ids=(),
        approval_hash="sha256:approval-phase24-ht",
        approved_at="2026-07-09T08:45:00+09:00",
        expires_at="2026-07-09T15:00:00+09:00",
        review_required=False,
        reason="phase24 ht approval",
        submit_policy_version=pending.submit_policy_version,
        submit_policy_source=pending.submit_policy_source,
        submit_policy_hash=pending.submit_policy_hash,
        approved_order_conditions={
            item.pending_item_id: {
                "order_type": item.order_type,
                "target_session": pending.target_session_date,
                "quantity": item.quantity,
                "side": item.side,
                "issue_code": item.symbol,
                "price_condition": "MARKET" if item.order_type == "MARKET" else "LIMIT",
                "limit_price": None if item.order_type == "MARKET" else item.estimated_price,
                "time_in_force": "DAY",
            }
            for item in pending.items
        },
    )


def _item(
    pending_item_id: str,
    *,
    amount: float,
    symbol: str = "7203",
    quantity: float = 100,
    quantity_contract: dict | None = None,
) -> PendingOrderItem:
    return PendingOrderItem(
        pending_item_id=pending_item_id,
        symbol=symbol,
        side="BUY",
        quantity=quantity,
        order_type="MARKET",
        estimated_price=amount / quantity,
        estimated_amount=amount,
        approved=False,
        state="PENDING_APPROVAL",
        listed_info={
            "code": symbol,
            "current_listed": True,
            "market": "プライム",
            "product_category": "011",
            "security_type": "011",
            "opportunity_buy_eligibility_status": "PASS",
            "opportunity_buy_eligibility": "BUY_ELIGIBLE",
            "opportunity_expected_edge_score": 0.10,
            "opportunity_expected_return": 0.10,
            "opportunity_no_buy_reason": "",
            "opportunity_buy_rank": 1,
            "opportunity_business_date": "2026-07-09",
            "opportunity_feature_date": "2026-07-09",
            "opportunity_eligibility_policy_version": "runtime_v2_opportunity_buy_eligibility_v1",
            "opportunity_eligibility_reason": "opportunity_positive_expected_edge",
        },
        quantity_contract=quantity_contract or _quantity_contract(symbol=symbol, amount=amount),
    )


def _reserved_market_item(
    pending_item_id: str,
    *,
    symbol: str,
    reference_amount: float,
    selected_position_amount: float,
    reserved_notional: float,
    quantity: float,
    reference_price: float,
    reservation_price: float,
) -> PendingOrderItem:
    base = _item(
        pending_item_id,
        amount=reference_amount,
        symbol=symbol,
        quantity=quantity,
        quantity_contract=_quantity_contract(symbol=symbol, amount=selected_position_amount)
        | {
            "lot_adjusted_notional": reference_amount,
            "lot_adjusted_quantity": quantity,
            "selected_notional": reference_amount,
            "selected_quantity": quantity,
        },
    )
    return replace(
        base,
        reference_price=reference_price,
        reservation_price=reservation_price,
        reservation_price_type="market_buy_stop_high_cash_reservation",
        reservation_price_authority={
            "authority_type": "ORDER_CONDITION_DERIVED_RESERVATION_PRICE_AUTHORITY",
            "reservation_price_type": "market_buy_stop_high_cash_reservation",
            "source_authority": "production_market_buy_price_limit_authority",
            "future_execution_price_used": False,
            "target_day_ohlc_used": False,
            "arbitrary_percentage_buffer_used": False,
            "runtime_path": "Production/Demo/Historical common runtime_v2",
        },
        reservation_reason="phase29_l21t_s_fixture_market_buy_stop_high_reservation",
        reserved_notional=reserved_notional,
    )


def _position(symbol: str, quantity: float, price: float) -> dict:
    return {"symbol": symbol, "quantity": quantity, "market_value": quantity * price, "average_price": price}


def _write_current(root: Path, *, cash: float, positions: list[dict]) -> None:
    market_value = sum(float(position["market_value"]) for position in positions)
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase24-ht",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2026-07-09",
            "positions": positions,
            "cash": cash,
            "buying_power": cash,
            "market_value": market_value,
            "total_equity": cash + market_value,
        },
    )


def _write_policy(path: Path) -> Path:
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "max_positions": 5,
            "min_order_amount": 0,
            "max_buy_order_amount": None,
            "max_sell_liquidation_amount": None,
            "buy_notional_policy": "derived_from_capital_allocation_and_constraints",
            "sell_liquidation_policy": "current_owned_available_quantity_policy",
            "manual_review_threshold": {"buy_amount": None, "sell_liquidation_amount": None},
        },
    )
    return path


def _write_safety(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": "safety-phase24-ht",
            "safety_policy_version": "safety_policy_v1",
            "safety_source": "phase24_ht_fixture",
            "business_date": "2026-07-09",
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase24 ht safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
        },
    )


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _quantity_contract(*, symbol: str, amount: float) -> dict:
    return {
        "quantity_contract_version": "phase26_step4_test_quantity_contract",
        "target_position_count": 8,
        "selected_dynamic_position_count": 8,
        "safety_hard_maximum": None,
        "legacy_position_count_config_used": False,
        "position_count_fallback_used": False,
        "target_cash_ratio": 0.10,
        "target_gross_exposure_ratio": 0.85,
        "maximum_gross_exposure_ratio": 0.90,
        "legacy_cash_config_used": False,
        "legacy_exposure_config_used": False,
        "cash_exposure_fallback_used": False,
        "position_sizing_authority": {
            "symbol": symbol,
            "selected_position_amount": amount,
            "remaining_add_capacity": amount,
            "selected_position_weight": 0.18,
            "target_weight": 0.18,
            "target_notional": amount,
            "incremental_buy_notional": amount,
            "maximum_position_weight": 0.18,
            "portfolio_policy_source": "phase24_ht_fixture_portfolio_policy",
        },
    }


def _one_lot_position_sizing_authority(intent: str) -> dict:
    return {
        "symbol": "78780",
        "selected_position_amount": 241_999.81,
        "remaining_add_capacity": 241_999.81,
        "selected_position_weight": 0.243189,
        "target_weight": 0.243189,
        "target_notional": 241_999.81,
        "incremental_buy_notional": 241_999.81,
        "maximum_position_weight": 0.18,
        "semantic_buy_type": intent,
        "quantity_delta_candidate": 100,
        "discrete_authorized_quantity": 100,
        "discrete_authorized_notional": 242_000.0,
        "portfolio_policy_source": "phase24_ht_fixture_portfolio_policy",
        "phase29_l19_lot_resolution": {
            "boundary_classification": "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX",
            "semantic_type": intent,
            "strategy_cap_overshoot_applied": True,
            "one_lot_fallback_applied": True,
            "one_lot_feasibility_status": "PASS",
            "one_lot_quantity": 100,
            "one_lot_notional": 242_000.0,
            "final_allocated_quantity": 100,
            "post_trade_weight": 0.243189,
            "safety_hard_cap": 0.25,
            "safety_hard_cap_weight": 0.25,
            "safety_hard_cap_preserved": True,
            "safety_margin_after_trade": 0.006811,
            "lot_overshoot_reason": "ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP",
        },
    }


def _ak2_minimum_one_lot_position_sizing_authority(
    *,
    symbol: str,
    selected_position_amount: float,
    one_lot_notional: float,
    intent: str = "BUY_NEW",
    one_lot_decision: str = "ADMIT",
) -> dict:
    one_lot_weight = one_lot_notional / 1_000_000.0
    selected_weight = selected_position_amount / 1_000_000.0
    return {
        "symbol": symbol,
        "security_code": symbol,
        "selected_position_amount": selected_position_amount,
        "remaining_add_capacity": selected_position_amount,
        "selected_position_weight": selected_weight,
        "target_weight": selected_weight,
        "target_notional": selected_position_amount,
        "incremental_buy_notional": selected_position_amount,
        "maximum_position_weight": 0.18,
        "semantic_buy_type": intent,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "current_quantity": 0,
        "final_quantity_delta": 100,
        "discrete_authorized_quantity": 100,
        "discrete_authorized_notional": one_lot_notional,
        "portfolio_policy_source": "phase30_ak3r1_fixture_portfolio_policy",
        "phase29_l19_lot_resolution": {
            "authority_type": "PHASE29_L19_CAP_CONSTRAINED_LOT_RESOLUTION",
            "boundary_classification": "CAP_CONSTRAINED_LOT_EXECUTABLE",
            "current_weight": 0.0,
            "executable_lots": 1,
            "executable_quantity_delta": 100,
            "final_allocated_quantity": 100,
            "final_target_weight": one_lot_weight,
            "lot_overshoot_reason": "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED",
            "maximum_safety_feasible_lots": 2,
            "maximum_strategy_feasible_lots": 1,
            "minimum_executable_one_lot_admitted": True,
            "minimum_executable_one_lot_reason": "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED",
            "minimum_executable_one_lot_authority": {
                "schema_version": "minimum_executable_one_lot_authority.v1",
                "authority_type": "PORTFOLIO_CONSTRUCTION_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION",
                "decision": one_lot_decision,
                "reason": "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED",
                "admission_decision": "PASS",
                "admission_reason": "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED",
                "symbol": symbol,
                "intent": intent,
                "current_quantity": 0,
                "original_pc_target_weight": selected_weight,
                "original_pc_increment_weight": selected_weight,
                "original_pc_target_notional": selected_position_amount,
                "one_lot_weight": one_lot_weight,
                "one_lot_notional": one_lot_notional,
                "projected_one_lot_portfolio_weight": one_lot_weight,
                "final_promoted_target_weight": one_lot_weight,
                "ps_final_quantity": 100,
                "strategy_cap": 0.18,
                "safety_cap": 0.25,
                "future_information_used": False,
            },
            "one_lot_fallback_applied": True,
            "one_lot_feasibility_status": "PASS",
            "one_lot_notional": one_lot_notional,
            "one_lot_quantity": 100,
            "one_lot_weight": one_lot_weight,
            "post_trade_weight": one_lot_weight,
            "requested_incremental_weight": selected_weight,
            "requested_lots": 0,
            "requested_target_weight": selected_weight,
            "safety_hard_cap": 0.25,
            "safety_hard_cap_preserved": True,
            "safety_hard_cap_weight": 0.25,
            "safety_margin_after_trade": 0.25 - one_lot_weight,
            "semantic_type": intent,
            "strategy_cap_overshoot_applied": False,
            "strategy_cap_overshoot_weight": 0.0,
            "strategy_cap_preserved": True,
            "strategy_cap_weight": 0.18,
            "strategy_target_cap": 0.18,
            "symbol": symbol,
        },
    }


def _pc_discrete_position_sizing_authority(
    *,
    symbol: str,
    selected_position_amount: float,
    executable_quantity: int,
    executable_notional: float,
    intent: str = "BUY_NEW",
) -> dict:
    one_lot_quantity = 100
    executable_lots = executable_quantity // one_lot_quantity
    executable_weight = executable_notional / 1_000_000.0
    selected_weight = selected_position_amount / 1_000_000.0
    return {
        "symbol": symbol,
        "security_code": symbol,
        "selected_position_amount": selected_position_amount,
        "remaining_add_capacity": selected_position_amount,
        "selected_position_weight": selected_weight,
        "target_weight": selected_weight,
        "target_notional": selected_position_amount,
        "incremental_buy_notional": selected_position_amount,
        "maximum_position_weight": 0.18,
        "semantic_buy_type": intent,
        "current_quantity": 0,
        "final_quantity_delta": executable_quantity,
        "portfolio_policy_source": "phase30_ak9r1b_fixture_portfolio_policy",
        "phase29_l19_lot_resolution": {
            "authority_type": "PHASE29_L19_CAP_CONSTRAINED_LOT_RESOLUTION",
            "boundary_classification": "CAP_CONSTRAINED_LOT_EXECUTABLE",
            "current_weight": 0.0,
            "executable_lots": executable_lots,
            "executable_quantity_delta": executable_quantity,
            "final_allocated_quantity": executable_quantity,
            "final_target_weight": executable_weight,
            "lot_overshoot_reason": "",
            "maximum_safety_feasible_lots": max(executable_lots, 1),
            "maximum_strategy_feasible_lots": max(executable_lots, 1),
            "normal_lot_quantity": executable_quantity,
            "one_lot_fallback_applied": False,
            "one_lot_feasibility_status": "PASS",
            "one_lot_notional": executable_notional / max(executable_lots, 1),
            "one_lot_quantity": one_lot_quantity,
            "one_lot_weight": executable_weight / max(executable_lots, 1),
            "pc_positive_executable_quantity_authority": {
                "accepted_lot_increment_weight": executable_weight,
                "authority_type": "PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY",
                "final_allocated_quantity": executable_quantity,
                "future_information_used": False,
                "ps_must_consume_canonical_quantity": True,
                "status": "PASS",
            },
            "post_trade_weight": executable_weight,
            "preflight_executable_quantity_delta": executable_quantity,
            "safety_hard_cap": 0.25,
            "safety_hard_cap_preserved": True,
            "safety_hard_cap_weight": 0.25,
            "safety_margin_after_trade": 0.25 - executable_weight,
            "semantic_type": intent,
            "strategy_cap_preserved": True,
            "strategy_cap_weight": 0.18,
            "strategy_target_cap": 0.18,
            "symbol": symbol,
        },
    }


def _g104_g102_pc_discrete_position_sizing_authority() -> dict:
    authority = _pc_discrete_position_sizing_authority(
        symbol="94320",
        selected_position_amount=41_940.0,
        executable_quantity=200,
        executable_notional=41_940.0,
        intent="BUY_NEW",
    )
    authority.update(
        {
            "lot_adjusted_quantity": 200,
            "discrete_authorized_quantity": 200,
        }
    )
    lot_resolution = authority["phase29_l19_lot_resolution"]
    lot_resolution.update(
        {
            "lot_overshoot_reason": "G102_G97_G99_ITEM_SCOPED_PC_DISCRETE_QUANTITY_AUTHORITY",
            "lot_aware_allocation_to_sizing_compatibility": {
                "allocation_rank": 5,
                "authority_status": "SHADOW_NON_AUTHORITATIVE",
                "authorized_allocation_weight": 0.030303,
                "business_date": "2023-03-22",
                "cap_headroom_weight": 0.25,
                "cap_weight": 0.25,
                "compatibility_state": "LOT_EXECUTABLE_COMPATIBLE",
                "competitor_type": "NEW_BUY",
                "current_weight": 0.0,
                "executable_before_residual_reallocation": True,
                "future_information_used": False,
                "historical_outcome_used": False,
                "implicit_priority_promotion_allowed": False,
                "lot_rounding_residual_weight": 0.006671,
                "lower_priority_execution_requires_explicit_residual_resolution": False,
                "minimum_executable_weight": 0.011816,
                "opportunity_type": "NEW_BUY",
                "owner": "PORTFOLIO_CONSTRUCTION",
                "pc_quantity_authority": False,
                "portfolio_value": 1_369_320.0,
                "position_sizing_quantity_authority_preserved": True,
                "projected_quantity_delta_evidence_only": 200,
                "reason_codes": [
                    "PS_QUANTITY_AUTHORITY_PRESERVED",
                    "LOWER_PRIORITY_IMPLICIT_PROMOTION_PROHIBITED",
                    "LOT_EXECUTABLE_COMPATIBLE",
                ],
                "reference_price": 161.8,
                "residual_capital_weight": 0.0,
                "schema_version": "portfolio_construction.lot_aware_allocation_to_sizing_compatibility.v1",
                "symbol": "94320",
                "trading_unit": 100,
                "within_class_allocation_rank": None,
            },
        }
    )
    return authority
