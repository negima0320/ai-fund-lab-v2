from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import SellExitDecision, run_sell_planning_pending_pipeline
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline

from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings
from tests.runtime_v2.test_phase15i_submit_guard_buy_sell_policy_manifest import (
    _approved_pending,
    _item,
    _position,
    _runtime_root,
    _write_broker_positions_snapshot,
    _write_current_state,
    _write_policy,
)


def test_phase15m_sell_broker_available_quantity_confirmed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_current_state(
        runtime_root,
        positions=[_position("6522", quantity=1000, price=300)],
        cash=700_000,
        market_value=300_000,
    )
    _write_broker_positions_snapshot(runtime_root, symbol="6522", quantity=1000, available_quantity=1000)
    pending = _approved_pending((_sell_item(quantity=1000, estimated_amount=300_000),), policy_path=policy_path)
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    evidence = result.submit_guard_item_evidence[0]
    assert result.status == "PASS"
    assert evidence["broker_available_quantity_checked"] is True
    assert evidence["broker_available_quantity_source"] == "broker_readonly"
    assert evidence["broker_available_quantity"] == 1000
    assert evidence["broker_available_quantity_issue_code"] == "6522"
    assert evidence["sell_quantity_guard_status"] == "PASS"


def test_phase15m_missing_broker_available_quantity_blocks_without_current_proxy(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_current_state(
        runtime_root,
        positions=[_position("6522", quantity=1000, price=300)],
        cash=700_000,
        market_value=300_000,
    )
    pending = _approved_pending((_sell_item(quantity=1000, estimated_amount=300_000),), policy_path=policy_path)
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=_BrokerShouldNotBeCalled(),
        capital_deployment_policy_path=policy_path,
    )

    evidence = result.submit_guard_item_evidence[0]
    assert result.status == "REVIEW_REQUIRED"
    assert result.demo_submit_executed is False
    assert result.submitted_count == 0
    assert result.pending_consumed is False
    assert evidence["broker_available_quantity_checked"] is False
    assert evidence["broker_available_quantity_source"] == "missing"
    assert evidence["broker_available_quantity"] is None
    assert evidence["sell_quantity_guard_status"] == "BROKER_AVAILABLE_MISSING"
    assert evidence["violated_policy"] == "broker_available_quantity"


def test_phase15m_insufficient_broker_available_quantity_blocks(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_current_state(
        runtime_root,
        positions=[_position("6522", quantity=1000, price=300)],
        cash=700_000,
        market_value=300_000,
    )
    _write_broker_positions_snapshot(runtime_root, symbol="6522", quantity=1000, available_quantity=500)
    pending = _approved_pending((_sell_item(quantity=1000, estimated_amount=300_000),), policy_path=policy_path)
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=_BrokerShouldNotBeCalled(),
        capital_deployment_policy_path=policy_path,
    )

    evidence = result.submit_guard_item_evidence[0]
    assert result.status == "REVIEW_REQUIRED"
    assert result.demo_submit_executed is False
    assert result.submitted_count == 0
    assert result.pending_consumed is False
    assert evidence["broker_available_quantity_checked"] is True
    assert evidence["broker_available_quantity"] == 500
    assert evidence["sell_quantity_guard_status"] == "BROKER_AVAILABLE_INSUFFICIENT"
    assert evidence["violated_policy"] == "broker_available_quantity"


def test_phase15m_broker_only_position_is_not_sell_source(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, positions=[], cash=1_000_000, market_value=0)
    _write_broker_positions_snapshot(runtime_root, symbol="6522", quantity=1000, available_quantity=1000)

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        exit_decisions=(SellExitDecision(symbol="6522", quantity=1000, reason="broker-only fixture"),),
    )

    assert result.status == "NO_SIGNAL"
    assert result.selected_count == 0
    assert result.reason == "NO_SIGNAL:current_position_missing"


def test_phase15m_current_quantity_and_broker_available_quantity_are_separate(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_current_state(
        runtime_root,
        positions=[_position("6522", quantity=1000, price=300)],
        cash=700_000,
        market_value=300_000,
    )
    _write_broker_positions_snapshot(runtime_root, symbol="6522", quantity=1000, available_quantity=800)
    pending = _approved_pending((_sell_item(quantity=500, estimated_amount=150_000),), policy_path=policy_path)
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    evidence = result.submit_guard_item_evidence[0]
    assert result.status == "PASS"
    assert evidence["current_quantity"] == 1000
    assert evidence["broker_available_quantity"] == 800
    assert evidence["sell_quantity"] == 500
    assert evidence["broker_restricted_quantity"] == 200


def _sell_item(*, quantity: float, estimated_amount: float):
    return _item(
        pending_item_id="sell-1",
        symbol="6522",
        side="SELL",
        quantity=quantity,
        estimated_price=300,
        estimated_amount=estimated_amount,
    )


class _BrokerShouldNotBeCalled:
    def preflight(self, command):
        raise AssertionError("broker preflight must not be called without broker available quantity evidence")

    def submit(self, command):
        raise AssertionError("broker submit must not be called without broker available quantity evidence")
