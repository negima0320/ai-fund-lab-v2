import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import load_runtime_current_exposure
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy
from ai_fund_lab_v2.runtime_v2.safety_decision import RuntimeSafetyDecision
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand
from ai_fund_lab_v2.runtime_v2.submit.pipeline import (
    BrokerAvailableQuantityEvidence,
    _submit_generation_binding_evidence,
    _submit_guard_item_evidence,
    run_submit_pipeline,
)

from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings
from tests.runtime_v2.test_phase30_ak3r2b_cash_feasible_buy_batch import _cash_feasible_buy_batch, _current, _policy
from tests.runtime_v2.test_phase24_ht_planning_submit_feasibility import (
    _ak2_minimum_one_lot_position_sizing_authority,
    _approval,
    _item,
    _pending,
    _quantity_contract,
    _position,
    _runtime_root,
    _write_current,
    _write_policy,
)


class CapturingDemoSubmitAdapter(FakeRuntimeV2DemoSubmitAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.commands: list[RuntimeV2SubmitCommand] = []

    def submit(self, command: RuntimeV2SubmitCommand):
        self.commands.append(command)
        return super().submit(command)


def test_phase26_step6_buy_pass_uses_approval_conditions_and_canonical_evidence(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=500_000, positions=[_position("1111", 100, 1000)])
    pending = _approved_pending(root, (_item("buy-1", amount=100_000),), policy)
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)
    adapter = CapturingDemoSubmitAdapter()

    result = run_submit_pipeline(
        runtime_root=root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "PASS"
    assert result.submitted_count == 1
    assert adapter.commands[0].price_type == "MARKET"
    assert adapter.commands[0].limit_price is None
    guard = result.submit_guard_item_evidence[0]
    assert guard["submit_authority_winner"] == "canonical_quantity_contract_revalidated_at_submit"
    assert guard["submit_feasibility_authority_source"] == "submit_guard_item_canonical_evidence_revalidation"
    assert guard["aggregate_submit_feasibility"]["authority_source"] == "submit_guard_canonical_evidence_revalidation"
    assert "legacy_submit_used" not in guard
    assert guard["submit_fallback_used"] is False
    assert guard["legacy_cash_config_used"] is False
    assert guard["legacy_exposure_config_used"] is False
    assert guard["legacy_position_count_config_used"] is False
    assert guard["selected_dynamic_cash_ratio"] == 0.1
    assert guard["selected_dynamic_exposure_ratio"] == 0.85
    assert guard["selected_dynamic_position_count"] == 0
    assert guard["selected_position_amount"] == 100_000.0
    assert guard["selected_position_weight"] == 0.18
    assert guard["selected_runtime_exposure_limit"] == 510_000.0
    assert guard["planning_budget"] == 410_000.0
    assert guard["available_position_slots"] == 0
    assert guard["remaining_exposure_capacity"] == 410_000.0


def test_phase30_ak3r2c1_submit_guard_authorized_one_lot_quantity_handoff_passes(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=500_000, positions=[])
    item = _ak2_one_lot_item(quantity=100)
    pending = _approved_pending(root, (item,), policy)

    guard = _submit_guard_item_evidence(
        item=pending.items[0],
        pending_plan=pending,
        runtime_root=root,
        business_date="2026-07-09",
        mode="demo",
        policy=policy,
        current_state=_current_state(root),
        broker_position_quantity=None,
        broker_available_quantity=None,
        broker_available_quantity_evidence=BrokerAvailableQuantityEvidence(checked=False, source=""),
        safety_decision=_demo_submit_safety_decision(),
        feasibility_evidence=(pending.planning_submit_feasibility or {})["items"][0],
    )

    assert guard["guard_decision"] == "PASS"
    assert guard["submit_item_status"] == "PASS"
    assert guard["position_sizing_authority"]["one_lot_authority_consumed"] is True
    assert guard["quantity"] == 100
    assert guard["position_sizing_authority"]["discrete_authorized_quantity"] == 100


def test_phase30_ak3r2c1_true_one_lot_quantity_mismatch_stays_review(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=500_000, positions=[])
    item = _ak2_one_lot_item(quantity=100)
    pending = _approved_pending(root, (item,), policy)
    tampered_item = replace(pending.items[0], quantity=200)

    guard = _submit_guard_item_evidence(
        item=tampered_item,
        pending_plan=pending,
        runtime_root=root,
        business_date="2026-07-09",
        mode="demo",
        policy=policy,
        current_state=_current_state(root),
        broker_position_quantity=None,
        broker_available_quantity=None,
        broker_available_quantity_evidence=BrokerAvailableQuantityEvidence(checked=False, source=""),
        safety_decision=_demo_submit_safety_decision(),
        feasibility_evidence=(pending.planning_submit_feasibility or {})["items"][0],
    )

    assert guard["guard_decision"] == "BLOCKED"
    assert guard["submit_item_status"] == "REVIEW_REQUIRED"
    assert guard["blocked_at_submit_reason"] == "one_lot_authority_quantity_mismatch"
    assert guard["violated_policy"] == "position_sizing"


def test_phase30_ak3r2c1_normal_buy_submit_guard_preserved(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=500_000, positions=[])
    item = _item("buy-normal", amount=100_000, symbol="7203", quantity=100)
    pending = _approved_pending(root, (item,), policy)

    guard = _submit_guard_item_evidence(
        item=pending.items[0],
        pending_plan=pending,
        runtime_root=root,
        business_date="2026-07-09",
        mode="demo",
        policy=policy,
        current_state=_current_state(root),
        broker_position_quantity=None,
        broker_available_quantity=None,
        broker_available_quantity_evidence=BrokerAvailableQuantityEvidence(checked=False, source=""),
        safety_decision=_demo_submit_safety_decision(),
        feasibility_evidence=(pending.planning_submit_feasibility or {})["items"][0],
    )

    assert guard["guard_decision"] == "PASS"
    assert guard["submit_item_status"] == "PASS"
    assert guard.get("one_lot_authority_consumed") in (None, False)


def test_phase30_ak3r2c1_cash_pruned_item_not_revalidated_by_submit_guard() -> None:
    active, evidence = _cash_feasible_buy_batch(
        items=(
            _item("buy-a", amount=100_000, symbol="11110", quantity=100),
            _item("buy-pruned", amount=400_000, symbol="22220", quantity=100),
            _item("buy-c", amount=50_000, symbol="33330", quantity=100),
        ),
        current=_current(cash=175_000),
        policy=_policy(),
        business_date="2026-07-09",
        mode="historical",
    )

    assert [item.symbol for item in active] == ["11110", "33330"]
    assert evidence["cash_pruned_count"] == 1
    assert evidence["items"][1]["symbol"] == "22220"
    assert evidence["items"][1]["decision"] == "PRUNE"


def test_phase26_step6_buy_review_does_not_block_valid_sell_submit(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=500_000, positions=[_position("1111", 100, 1000)])
    buy = _item("buy-1", amount=100_000, symbol="7203")
    sell = _sell_item("sell-1", symbol="1111", quantity=50, amount=50_000)
    pending = _approved_pending(root, (buy, sell), policy)
    _write_current(root, cash=90_000, positions=[_position("1111", 100, 1000)])
    _write_broker_snapshot(root, symbol="1111", quantity=100, available_quantity=100)
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)
    adapter = CapturingDemoSubmitAdapter()

    result = run_submit_pipeline(
        runtime_root=root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.submitted_count == 1
    assert result.submitted_symbols == ("1111",)
    by_id = {item["pending_item_id"]: item for item in result.submit_guard_item_evidence}
    assert by_id["buy-1"]["guard_decision"] == "BLOCKED"
    assert by_id["buy-1"]["violated_policy"] in {"cash", "buying_power"}
    assert by_id["buy-1"]["legacy_cash_config_used"] is False
    assert by_id["buy-1"]["cash_exposure_fallback_used"] is False
    assert by_id["sell-1"]["guard_decision"] == "PASS"
    assert by_id["sell-1"]["sell_quantity_guard_status"] == "PASS"
    assert by_id["sell-1"]["buy_sell_submit_independence_preserved"] is True


def test_phase26_step6_missing_approval_conditions_fail_closed(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=500_000, positions=[_position("1111", 100, 1000)])
    pending = _approved_pending(root, (_item("buy-1", amount=100_000),), policy)
    pending = replace(pending, approval=replace(pending.approval, approved_order_conditions=None))
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

    assert result.status == "BLOCKED"
    assert result.submitted_count == 0
    guard = result.submit_guard_item_evidence[0]
    assert guard["guard_decision"] == "BLOCKED"
    assert guard["guard_reason"] == "approved order conditions missing"
    assert guard["violated_policy"] == "submit_preflight"
    assert "legacy_submit_used" not in guard
    assert guard["submit_fallback_used"] is False


def test_phase26_pf3j_valid_historical_authority_separation_allows_generation_authority_date_mismatch() -> None:
    binding = _historical_evaluation_authority_binding()
    evidence = _submit_generation_binding_evidence(
        item=_bound_object(binding),
        pending_plan=_bound_plan(binding),
        business_date="2022-07-01",
        mode="historical",
    )

    assert evidence["submit_generation_binding_status"] == "PASS"
    assert evidence["submit_generation_binding_reason"] == ""
    assert evidence["historical_evaluation_authority_separation"]["status"] == "PASS"
    assert evidence["pending_generation_business_date"] == "2026-08-03"
    assert evidence["requested_business_date"] == "2022-07-01"
    assert evidence["accepted_generation_business_date_classification"].startswith("legacy_read_only_metadata")
    assert evidence["business_date_conflict_classification"].startswith("legacy_read_only_metadata")


def test_phase26_pf3j_historical_authority_missing_hashes_fail_closed() -> None:
    binding = _historical_evaluation_authority_binding()
    binding.pop("run_authority_hash")
    evidence = _submit_generation_binding_evidence(
        item=_bound_object(binding),
        pending_plan=_bound_plan(binding),
        business_date="2022-07-01",
        mode="historical",
    )

    assert evidence["submit_generation_binding_status"] == "BLOCKED"
    assert "accepted_generation_business_date_mismatch" in evidence["submit_generation_binding_reason"]
    assert "run_authority_hash_missing" in evidence["historical_evaluation_authority_separation"]["reason"]


def test_phase26_pf3j_demo_generation_business_date_mismatch_remains_blocked() -> None:
    binding = _accepted_generation_binding() | {
        "requested_business_date": "2026-07-09",
        "selected_business_date": "2026-08-03",
        "accepted_generation_business_date": "2026-08-03",
    }
    evidence = _submit_generation_binding_evidence(
        item=_bound_object(binding),
        pending_plan=_bound_plan(binding),
        business_date="2026-07-09",
        mode="demo",
    )

    assert evidence["submit_generation_binding_status"] == "BLOCKED"
    assert "accepted_generation_business_date_mismatch" in evidence["submit_generation_binding_reason"]
    assert evidence["historical_evaluation_authority_separation"]["status"] == "REVIEW_REQUIRED"
    assert "runtime_mode_not_historical" in evidence["historical_evaluation_authority_separation"]["reason"]


def test_phase26_pf3j_historical_authority_fallback_flag_fails_closed() -> None:
    binding = _historical_evaluation_authority_binding() | {"latest_fallback_used": True}
    evidence = _submit_generation_binding_evidence(
        item=_bound_object(binding),
        pending_plan=_bound_plan(binding),
        business_date="2022-07-01",
        mode="historical",
    )

    assert evidence["submit_generation_binding_status"] == "BLOCKED"
    assert "accepted_generation_business_date_mismatch" in evidence["submit_generation_binding_reason"]
    assert "old_path_fallback_flag" in evidence["historical_evaluation_authority_separation"]["reason"]


def _approved_pending(root: Path, items: tuple[PendingOrderItem, ...], policy):
    binding = _accepted_generation_binding()
    bound_items = tuple(
        replace(
            item,
            accepted_generation_id=binding["accepted_generation_id"] if item.side.upper() == "BUY" else "",
            accepted_generation_business_date=binding["accepted_generation_business_date"] if item.side.upper() == "BUY" else "",
            accepted_generation_binding_status="PASS" if item.side.upper() == "BUY" else "NOT_REQUIRED",
            accepted_generation_binding=binding if item.side.upper() == "BUY" else None,
        )
        for item in items
    )
    pending = _pending(bound_items, policy=policy)
    pending = replace(
        pending,
        accepted_generation_id=binding["accepted_generation_id"],
        accepted_generation_business_date=binding["accepted_generation_business_date"],
        accepted_generation_binding_status="PASS",
        accepted_generation_binding=binding,
    )
    return link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )


def _ak2_one_lot_item(*, quantity: float) -> PendingOrderItem:
    amount = 100_000.0
    selected_position_amount = 70_000.0
    symbol = "78780"
    return _item(
        "buy-ak2-one-lot",
        amount=amount * quantity / 100.0,
        symbol=symbol,
        quantity=quantity,
        quantity_contract=_quantity_contract(symbol=symbol, amount=selected_position_amount)
        | {
            "selected_notional": amount,
            "selected_quantity": quantity,
            "planned_quantity": quantity,
            "planning_intent": "BUY_NEW",
            "position_sizing_authority": _ak2_minimum_one_lot_position_sizing_authority(
                symbol=symbol,
                selected_position_amount=selected_position_amount,
                one_lot_notional=amount,
                intent="BUY_NEW",
            ),
        },
    )


def _current_state(root: Path) -> dict:
    return load_runtime_current_exposure(root / "persistent_ledger" / "state.json").to_payload()


def _demo_submit_safety_decision() -> RuntimeSafetyDecision:
    return RuntimeSafetyDecision(
        safety_decision_id="phase30-ak3r2c1-safety",
        safety_policy_version="runtime_safety_v1",
        safety_source="phase30_ak3r2c1_fixture",
        business_date="2026-07-09",
        runtime_mode="demo",
        decision="ALLOW",
        reason="phase30 ak3r2c1 safety allow",
        review_required=False,
        block_buy=False,
        block_sell=False,
        block_submit=False,
        halt_runtime=False,
        emergency_stop=False,
        generated_at="2026-07-09T08:00:00+09:00",
        expires_at="2026-07-09T15:00:00+09:00",
        safety_status="PASS",
    )


def _accepted_generation_binding() -> dict:
    return {
        "schema_version": "phase26_step8_accepted_generation_binding.v1",
        "consumer": "phase26_step6_submit_fixture",
        "mode": "demo",
        "requested_business_date": "2026-07-09",
        "selected_business_date": "2026-07-09",
        "accepted_generation_id": "phase26-step6-fixture-generation",
        "accepted_generation_business_date": "2026-07-09",
        "generation_binding_status": "PASS",
        "temporal_binding_status": "PASS",
        "latest_fallback_used": False,
        "shared_state_fallback_used": False,
        "default_generation_used": False,
        "legacy_component_fallback_used": False,
        "promotion_candidate_fallback_used": False,
        "manual_model_path_used": False,
    }


def _historical_evaluation_authority_binding() -> dict:
    return {
        "schema_version": "phase26_step8_accepted_generation_binding.v1",
        "consumer": "phase26_pf3j_submit_fixture",
        "mode": "historical",
        "requested_business_date": "2022-07-01",
        "selected_business_date": "2026-08-03",
        "accepted_generation_id": "phase19_aq_accepted_generation_641e6e313543f013",
        "accepted_generation_business_date": "2026-08-03",
        "generation_binding_status": "PASS",
        "temporal_binding_status": "PASS",
        "business_date_conflict": False,
        "market_as_of_business_date": "2022-07-01",
        "evaluation_authority_time": "2026-08-03T13:22:41.856832Z",
        "business_date_temporal_comparison_applied": False,
        "evaluation_authority_time_temporal_comparison_applied": True,
        "historical_business_date_acceptance_comparison": "NOT_APPLIED_TO_ACCEPTED_GENERATION",
        "temporal_authority_source": "evaluation_authority_time",
        "temporal_authority_winner": "run_start_fixed_accepted_generation",
        "historical_evaluation_authority_path": "reports/runtime_tests/runs/runtime-test-historical-smoke-20260803T132236636006Z/historical_evaluation_authority.json",
        "run_authority_hash": "sha256:af47f7f875148bcafc13f86234ce447322aea4a2d28d1b37807c1a385eccd0c0",
        "manifest_content_hash": "b6bb3a8d64db03e87e9247f291aa0d5f30483075de9305901a35207cd336ad30",
        "aggregate_hash": "b97d3ccb14448b6ac721afcd93acedbabf4275712bb07816f13c322b2045480b",
        "authority_context": {
            "schema_version": "runtime_authority_context.v1",
            "evaluation_authority": {
                "generation_id": "phase19_aq_accepted_generation_641e6e313543f013",
                "fixed_at": "2026-08-03T13:22:41.856832Z",
                "authority_time": "2026-08-03T13:22:41.856832Z",
            },
            "market_as_of_authority": {"business_date": "2022-07-01"},
        },
        "latest_fallback_used": False,
        "shared_state_fallback_used": False,
        "default_generation_used": False,
        "legacy_component_fallback_used": False,
        "promotion_candidate_fallback_used": False,
        "manual_model_path_used": False,
    }


def _bound_plan(binding: dict) -> SimpleNamespace:
    return SimpleNamespace(
        accepted_generation_id=binding["accepted_generation_id"],
        accepted_generation_business_date=binding["accepted_generation_business_date"],
        accepted_generation_binding_status=binding["generation_binding_status"],
        accepted_generation_binding=binding,
        approval=_bound_object(binding),
    )


def _bound_object(binding: dict) -> SimpleNamespace:
    return SimpleNamespace(
        side="BUY",
        accepted_generation_id=binding["accepted_generation_id"],
        accepted_generation_business_date=binding["accepted_generation_business_date"],
        accepted_generation_binding_status=binding["generation_binding_status"],
        accepted_generation_binding=binding,
    )


def _sell_item(pending_item_id: str, *, symbol: str, quantity: float, amount: float) -> PendingOrderItem:
    return PendingOrderItem(
        pending_item_id=pending_item_id,
        symbol=symbol,
        side="SELL",
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
        },
        quantity_contract={},
    )


def _write_broker_snapshot(root: Path, *, symbol: str, quantity: float, available_quantity: float) -> None:
    path = root / "broker" / "snapshots" / "positions" / "positions_20260709.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "source": "broker_readonly",
                "as_of": "2026-07-09T08:50:00+09:00",
                "production_equivalent": True,
                "records": [
                    {
                        "issue_code": symbol,
                        "quantity": quantity,
                        "available_quantity": available_quantity,
                        "account_type": "specific",
                        "production_equivalent": True,
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
