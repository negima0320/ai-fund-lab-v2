import json

from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import SellExitDecision, run_sell_planning_pending_pipeline
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline

from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings
from tests.runtime_v2.test_phase15i_submit_guard_buy_sell_policy_manifest import (
    _attach_pending_safety_evidence,
    _approved_pending,
    _item,
    _position,
    _runtime_root,
    _write_broker_positions_snapshot,
    _write_current_state,
    _write_policy,
    _write_runtime_readiness_authorities,
    _write_safety_decision,
)
from tests.runtime_v2.test_phase15k_morning_policy_propagation_hidden_policy_removal import (
    _latest_manifest,
    _run_morning,
    _write_current,
    _write_features,
    _write_policy as _write_morning_policy,
)
from tests.runtime_v2.feature_date_contract_helpers import materialize_feature_date_contract
def test_phase15n_safety_missing_blocks_submit_before_broker(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _safety_path(runtime_root).unlink()
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_current_state(runtime_root, positions=[], cash=1_000_000, market_value=0)
    pending = _approved_pending(
        (
            _item(
                pending_item_id="buy-1",
                symbol="7203",
                side="BUY",
                quantity=100,
                estimated_price=1000,
                estimated_amount=100_000,
            ),
        ),
        policy_path=policy_path,
    )
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
    assert result.submitted_count == 0
    assert result.demo_submit_executed is False
    assert evidence["safety_guard_status"] == "REVIEW_REQUIRED"
    assert evidence["violated_policy"] == "safety_operation_guard"
def test_phase15n_safety_block_buy_stops_buy_but_not_sell(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_safety_decision(runtime_root, block_buy=True, reason="buy paused")
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_current_state(
        runtime_root,
        positions=[_position("6522", quantity=1000, price=300)],
        cash=700_000,
        market_value=300_000,
    )
    _write_broker_positions_snapshot(runtime_root, symbol="6522", quantity=1000, available_quantity=1000)
    buy_pending = _approved_pending(
        (
            _item(
                pending_item_id="buy-1",
                symbol="7203",
                side="BUY",
                quantity=100,
                estimated_price=1000,
                estimated_amount=100_000,
            ),
        ),
        policy_path=policy_path,
    )
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", buy_pending)
    buy_submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=_BrokerShouldNotBeCalled(),
        capital_deployment_policy_path=policy_path,
    )
    assert buy_submit.status == "REVIEW_REQUIRED"
    assert buy_submit.submit_guard_item_evidence[0]["safety_guard_status"] == "REVIEW_REQUIRED"

    sell_pending = _approved_pending(
        (_sell_item(quantity=500, estimated_amount=150_000),),
        policy_path=policy_path,
    )
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", sell_pending)
    sell_submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )
    assert sell_submit.status == "PASS"
    assert sell_submit.submit_guard_item_evidence[0]["side"] == "SELL"
    assert sell_submit.submit_guard_item_evidence[0]["safety_guard_status"] == "PASS"


def test_phase15n_safety_block_sell_stops_sell_planning_and_submit(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_safety_decision(runtime_root, block_sell=True, reason="sell paused")
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_current_state(
        runtime_root,
        positions=[_position("6522", quantity=1000, price=300)],
        cash=700_000,
        market_value=300_000,
    )
    sell_plan = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        exit_decisions=(SellExitDecision(symbol="6522", quantity=1000, reason="exit"),),
    )
    assert sell_plan.status == "REVIEW_REQUIRED"
    assert sell_plan.safety_block_sell is True

    _write_broker_positions_snapshot(runtime_root, symbol="6522", quantity=1000, available_quantity=1000)
    sell_pending = _approved_pending((_sell_item(quantity=500, estimated_amount=150_000),), policy_path=policy_path)
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", sell_pending)
    sell_submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=_BrokerShouldNotBeCalled(),
        capital_deployment_policy_path=policy_path,
    )
    assert sell_submit.status == "REVIEW_REQUIRED"
    assert sell_submit.submit_guard_item_evidence[0]["safety_block_sell"] is True


def test_phase15n_safety_halt_stops_submit(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_safety_decision(runtime_root, decision="HALT", halt_runtime=True, reason="emergency halt")
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_current_state(runtime_root, positions=[], cash=1_000_000, market_value=0)
    pending = _approved_pending(
        (
            _item(
                pending_item_id="buy-1",
                symbol="7203",
                side="BUY",
                quantity=100,
                estimated_price=1000,
                estimated_amount=100_000,
            ),
        ),
        policy_path=policy_path,
    )
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

    assert result.status == "HALT"
    assert result.submitted_count == 0
    assert result.submit_guard_item_evidence[0]["safety_guard_status"] == "HALT"


def test_phase15n_cli_manifest_contains_safety_evidence(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_current_state(runtime_root, positions=[], cash=1_000_000, market_value=0)
    pending = _approved_pending(
        (
            _item(
                pending_item_id="buy-1",
                symbol="7203",
                side="BUY",
                quantity=100,
                estimated_price=1000,
                estimated_amount=100_000,
            ),
        ),
        policy_path=policy_path,
    )
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)
    _attach_pending_safety_evidence(runtime_root, safety_decision_id="safety-phase15i-fixture")
    _write_runtime_readiness_authorities(runtime_root, business_date="2026-07-09")
    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "submit",
            "--business-date",
            "2026-07-09",
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
        ]
    )
    manifest = _latest_manifest(runtime_root, "2026-07-09")
    safety_stage = next(stage for stage in manifest["stages"] if stage["name"] == "safety_operation_guard")
    assert exit_code == 0
    assert manifest["safety_decision"] == "ALLOW"
    assert safety_stage["status"] == "PASS"


def _sell_item(*, quantity: float, estimated_amount: float):
    return _item(
        pending_item_id="sell-1",
        symbol="6522",
        side="SELL",
        quantity=quantity,
        estimated_price=300,
        estimated_amount=estimated_amount,
    )


def _safety_path(runtime_root):
    return runtime_root / "runtime_state" / "safety" / "latest_safety_decision.json"


class _BrokerShouldNotBeCalled:
    def preflight(self, command):
        raise AssertionError("broker preflight must not be called when safety blocks")

    def submit(self, command):
        raise AssertionError("broker submit must not be called when safety blocks")


def _write_market_evidence(runtime_root):
    path = runtime_root / "runtime_state" / "market" / "2026-07-09" / "market_evidence.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "runtime_v2_market_evidence_v1",
                "business_date": "2026-07-09",
                "generated_at": "2026-07-09T00:00:00Z",
                "market_summary": {"quote_count": 1},
                "quote_count": 1,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
