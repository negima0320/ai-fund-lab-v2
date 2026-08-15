from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pandas as pd

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
