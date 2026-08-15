from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import attach_approval_link, promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import (
    REDUCE_QUANTITY_CONTRACT_VERSION,
    SellExitDecision,
    calculate_reduce_quantity_contract,
    run_sell_planning_pending_pipeline,
)
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline
from ai_fund_lab_v2.strategy.reduce_intensity_authority import canonical_reduce_fraction


BUSINESS_DATE = "2026-07-08"


def test_phase19_bt_reduce_quantity_normal_tiers_and_rounding():
    light = calculate_reduce_quantity_contract(position_quantity=1000, reduce_intensity="LIGHT")
    medium = calculate_reduce_quantity_contract(position_quantity=1000, reduce_intensity="MEDIUM")
    strong = calculate_reduce_quantity_contract(position_quantity=1000, reduce_intensity="STRONG")

    assert light["quantity_contract_version"] == REDUCE_QUANTITY_CONTRACT_VERSION
    assert light["final_sell_quantity"] == 200
    assert light["expected_remaining_quantity"] == 800
    assert medium["final_sell_quantity"] == 300
    assert medium["expected_remaining_quantity"] == 700
    assert strong["final_sell_quantity"] == 500
    assert strong["expected_remaining_quantity"] == 500


def test_phase28_d34_reduce_quantity_uses_shared_canonical_authority():
    assert canonical_reduce_fraction("LIGHT") == 0.25
    assert canonical_reduce_fraction("MEDIUM") == 0.33
    assert canonical_reduce_fraction("STRONG") == 0.50

    contract = calculate_reduce_quantity_contract(position_quantity=1000, reduce_intensity="STRONG")

    assert contract["target_reduce_ratio"] == canonical_reduce_fraction("STRONG")
    assert contract["reduce_fraction_authority"]["authority_type"] == "CANONICAL_REDUCE_INTENSITY_AUTHORITY"


def test_phase19_bt_reduce_small_position_non_executable_no_order_contract():
    contract = calculate_reduce_quantity_contract(position_quantity=100, reduce_intensity="LIGHT")

    assert contract["status"] == "NOT_EXECUTABLE"
    assert contract["reason"] == "REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY"
    assert contract["execution_semantic"] == "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT"
    assert contract["intentional_no_order"] is True
    assert contract["intentional_no_order_reason"] == "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT"
    assert contract["execution_feasibility_status"] == "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY"
    assert contract["effective_action"] == "NO_SELL_ORDER"
    assert contract["final_sell_quantity"] == 0


def test_phase20_m_zero_rounded_reduce_generates_no_order_and_runtime_can_continue(tmp_path):
    runtime_root = _runtime_root(tmp_path, mode="demo")
    _write_current_state(runtime_root, mode="demo", positions=[_position("50310", quantity=300, price=100)])

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        exit_decisions=(
            SellExitDecision(
                symbol="50310",
                quantity=0,
                reason="risk_increased_but_trend_not_broken",
                source_decision="REDUCE",
                reduce_intensity="LIGHT",
                source_decision_id="pm-2026-06-18-50310-reduce",
            ),
        ),
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    order_plan = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "order_plan.json")
    non_executable = order_plan["non_executable_sell_decisions"][0]
    contract = non_executable["quantity_contract"]

    assert result.status == "PASS"
    assert result.selected_count == 0
    assert pending["items"] == []
    assert pending["active_pending"] is False
    assert pending["non_executable_sell_decisions"][0]["original_decision"] == "REDUCE"
    assert pending["non_executable_sell_decisions"][0]["execution_semantic"] == "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT"
    assert pending["non_executable_sell_decisions"][0]["intentional_no_order"] is True
    assert pending["non_executable_sell_decisions"][0]["intentional_no_order_reason"] == "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT"
    assert contract["position_quantity_before"] == 300
    assert contract["raw_reduce_quantity"] == 75
    assert contract["execution_semantic"] == "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT"
    assert contract["intentional_no_order"] is True
    assert contract["rounded_executable_quantity"] == 0
    assert contract["pending_order_generated"] is False
    assert contract["effective_action"] == "NO_SELL_ORDER"
    assert contract["position_quantity_after"] == 300
    assert contract["runtime_continuation_status"] == "PASS"
    assert contract["position_lifecycle_event"] == "REDUCE_NOT_EXECUTED_MINIMUM_TRADABLE_QUANTITY"


def test_phase20_m_reduce_boundary_and_invalid_quantity_contracts():
    below = calculate_reduce_quantity_contract(position_quantity=396, reduce_intensity="LIGHT")
    exact = calculate_reduce_quantity_contract(position_quantity=400, reduce_intensity="LIGHT")
    above = calculate_reduce_quantity_contract(position_quantity=404, reduce_intensity="LIGHT")
    negative = calculate_reduce_quantity_contract(position_quantity=-100, reduce_intensity="LIGHT")
    missing_unit = calculate_reduce_quantity_contract(position_quantity=1000, reduce_intensity="LIGHT", tradable_unit=None)

    assert below["raw_reduce_quantity"] == 99
    assert below["status"] == "NOT_EXECUTABLE"
    assert exact["raw_reduce_quantity"] == 100
    assert exact["final_sell_quantity"] == 100
    assert above["raw_reduce_quantity"] == 101
    assert above["final_sell_quantity"] == 100
    assert negative["status"] == "REVIEW_REQUIRED"
    assert missing_unit["status"] == "REVIEW_REQUIRED"
    assert missing_unit["reason"] == "REVIEW_REQUIRED_REDUCE_TRADABLE_UNIT_UNKNOWN"


def test_phase19_bt_reduce_unknown_intensity_fail_closed():
    contract = calculate_reduce_quantity_contract(position_quantity=1000, reduce_intensity="")

    assert contract["status"] == "REVIEW_REQUIRED"
    assert contract["reason"] == "REVIEW_REQUIRED_REDUCE_INTENSITY_UNKNOWN"
    assert contract["final_sell_quantity"] == 0


def test_phase19_bt_reduce_sell_planning_creates_partial_sell_with_contract_evidence(tmp_path):
    runtime_root = _runtime_root(tmp_path, mode="demo")
    _write_current_state(runtime_root, mode="demo", positions=[_position("6522", quantity=1000, price=100)])
    accepted_generation_binding = _accepted_generation_binding(mode="demo", business_date=BUSINESS_DATE)

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        exit_decisions=(
            SellExitDecision(
                symbol="6522",
                quantity=0,
                reason="peak_drawdown_warning",
                score=0.55,
                source_decision="REDUCE",
                reduce_intensity="MEDIUM",
            ),
        ),
        accepted_generation_binding=accepted_generation_binding,
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    order_plan = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "order_plan.json")
    approval = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "approval_artifact.json")
    pending_item_id = pending["items"][0]["pending_item_id"]

    assert result.status == "PASS"
    assert pending["items"][0]["side"] == "SELL"
    assert pending["items"][0]["quantity"] == 300
    assert pending["items"][0]["quantity_contract"]["source_decision"] == "REDUCE"
    assert pending["items"][0]["quantity_contract"]["expected_remaining_quantity"] == 700
    assert pending["accepted_generation_binding_status"] == "PASS"
    assert pending["items"][0]["accepted_generation_binding_status"] == "PASS"
    assert pending["approval"]["accepted_generation_binding_status"] == "PASS"
    assert approval["approved_order_conditions"][pending_item_id]["side"] == "SELL"
    assert approval["approved_order_conditions"][pending_item_id]["quantity"] == 300
    assert pending["approval"]["approved_order_conditions"][pending_item_id]["condition_consumer"] == (
        "runtime_v2.submit.guards.run_submit_preflight"
    )
    assert order_plan["items"][0]["quantity_contract"]["target_reduce_ratio"] == 0.33


def test_phase26_pf3l_exit_sell_planning_materializes_approval_conditions_and_context(tmp_path):
    runtime_root = _runtime_root(tmp_path, mode="historical")
    _write_current_state(runtime_root, mode="historical", positions=[_position("76470", quantity=2100, price=26)])
    binding = _accepted_generation_binding(mode="historical", business_date="2023-01-18")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2023-01-18",
        mode="historical",
        exit_decisions=(SellExitDecision(symbol="76470", quantity=2100, reason="hard_stop", source_decision="EXIT"),),
        accepted_generation_binding=binding,
        environment_capability_context=_historical_context(),
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    approval = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / "2023-01-18" / "approval_artifact.json")
    item_id = pending["items"][0]["pending_item_id"]

    assert result.status == "PASS"
    assert pending["items"][0]["side"] == "SELL"
    assert pending["items"][0]["quantity_contract"]["source_decision"] == "EXIT"
    assert pending["approval"]["approved_order_conditions"][item_id]["issue_code"] == "76470"
    assert approval["approved_order_conditions"][item_id]["quantity"] == 2100
    assert pending["accepted_generation_id"] == "accepted-generation-pf3l"
    assert pending["items"][0]["accepted_generation_id"] == "accepted-generation-pf3l"
    assert pending["approval"]["accepted_generation_id"] == "accepted-generation-pf3l"


def test_phase19_bt_reduce_pending_sell_conflict_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path, mode="demo")
    _write_current_state(runtime_root, mode="demo", positions=[_position("6522", quantity=1000, price=100)])
    _write_existing_sell_pending(runtime_root, mode="demo", symbol="6522", quantity=100)

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        exit_decisions=(
            SellExitDecision(
                symbol="6522",
                quantity=0,
                reason="peak_drawdown_warning",
                source_decision="REDUCE",
                reduce_intensity="MEDIUM",
            ),
        ),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.selected_count == 0
    assert "PENDING_SELL_CONFLICTING_QUANTITY_REVIEW" in result.reason
    assert "PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED" in result.reason


def test_phase19_bt_exit_priority_over_reduce_same_symbol(tmp_path):
    runtime_root = _runtime_root(tmp_path, mode="demo")
    _write_current_state(runtime_root, mode="demo", positions=[_position("6522", quantity=1000, price=100)])

    run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        exit_decisions=(
            SellExitDecision(
                symbol="6522",
                quantity=0,
                reason="peak_drawdown_warning",
                source_decision="REDUCE",
                reduce_intensity="STRONG",
            ),
            SellExitDecision(symbol="6522", quantity=1000, reason="hard_stop", source_decision="EXIT"),
        ),
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert len(pending["items"]) == 1
    assert pending["items"][0]["quantity"] == 1000
    assert pending["items"][0]["quantity_contract"]["source_decision"] == "EXIT"


def test_phase19_bt_exit_sell_planning_caps_to_historical_sellable_quantity(tmp_path):
    runtime_root = _runtime_root(tmp_path, mode="historical")
    _write_current_state(runtime_root, mode="historical", positions=[_position("81050", quantity=600, price=170)])
    _append_jsonl(
        runtime_root / "persistent_ledger" / "orders.jsonl",
        {
            "environment": "historical",
            "symbol": "81050",
            "side": "SELL",
            "status": "ACCEPTED",
            "quantity": 600,
        },
    )
    _append_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        {
            "environment": "historical",
            "symbol": "81050",
            "side": "SELL",
            "execution_status": "filled",
            "filled_quantity": 400,
        },
    )
    _append_jsonl(
        runtime_root / "persistent_ledger" / "orders.jsonl",
        {
            "environment": "historical",
            "source": "runtime_v2_execution_readonly_simulation",
            "symbol": "81050",
            "side": "SELL",
            "status": "filled",
            "quantity": 400,
        },
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(SellExitDecision(symbol="81050", quantity=600, reason="hard_stop", source_decision="EXIT"),),
        environment_capability_context=_historical_context(),
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "PASS"
    assert pending["items"][0]["quantity"] == 400
    assert pending["items"][0]["quantity_contract"]["source_decision"] == "EXIT"
    assert pending["items"][0]["quantity_contract"]["sellable_quantity"] == 400
    assert pending["items"][0]["quantity_contract"]["restricted_quantity"] == 200


def test_phase19_bt_reduce_mode_parity(tmp_path):
    quantities = {}
    for mode in ("historical", "demo", "production"):
        runtime_root = _runtime_root(tmp_path / f"mode_{mode}", mode=mode)
        _write_current_state(runtime_root, mode=mode, positions=[_position("6522", quantity=1000, price=100)])
        result = run_sell_planning_pending_pipeline(
            runtime_root=runtime_root,
            business_date=BUSINESS_DATE,
            mode=mode,
            exit_decisions=(
                SellExitDecision(
                    symbol="6522",
                    quantity=0,
                    reason="peak_drawdown_warning",
                    source_decision="REDUCE",
                    reduce_intensity="MEDIUM",
                ),
            ),
            environment_capability_context=_historical_context() if mode == "historical" else None,
        )
        pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
        assert result.status == "PASS"
        quantities[mode] = pending["items"][0]["quantity"]

    assert quantities == {"historical": 300, "demo": 300, "production": 300}
def _runtime_root(tmp_path: Path, *, mode: str) -> Path:
    root = tmp_path / ".runtime"
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "runtime_state").mkdir(parents=True)
    ledger = root / "persistent_ledger"
    ledger.mkdir(parents=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (ledger / f"{name}.jsonl").write_text("", encoding="utf-8")
    _write_safety_decision(root, mode=mode)
    return root


def _write_current_state(root: Path, *, mode: str, positions):
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase19bt",
            "environment": mode,
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": BUSINESS_DATE,
            "positions": positions,
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": sum(float(item["market_value"]) for item in positions),
            "total_equity": 1_000_000 + sum(float(item["market_value"]) for item in positions),
            "review_required": False,
            "production_equivalent": mode == "production",
            "current_state_confirmed_empty": False,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
            "runtime_evaluation_capital": 1_000_000,
            "generated_from": ["fixture"],
            "created_at": BUSINESS_DATE,
            "updated_at": BUSINESS_DATE,
        },
    )


def _position(symbol: str, *, quantity: float, price: float) -> dict:
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": price,
        "market_value": quantity * price,
        "source": "fixture",
        "as_of": BUSINESS_DATE,
    }


def _write_existing_sell_pending(root: Path, *, mode: str, symbol: str, quantity: float):
    order_plan_path = root / "fixtures" / "existing_sell_order_plan.json"
    order_plan_path.parent.mkdir(parents=True, exist_ok=True)
    order_plan_path.write_text(json.dumps({"order_plan_id": "order-plan-existing-sell"}), encoding="utf-8")
    item = PendingOrderItem(
        pending_item_id=f"opi-existing-reduce-{symbol}",
        symbol=symbol,
        side="SELL",
        quantity=quantity,
        order_type="MARKET",
        estimated_price=100,
        estimated_amount=quantity * 100,
        approved=True,
        state="READY",
        quantity_contract={"source_decision": "REDUCE"},
        source_decision_type="REDUCE",
        source_position_symbol=symbol,
    )
    pending = promote_order_plan_to_pending(
        order_plan_id="order-plan-existing-sell",
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash="sha256:phase19bt-existing-sell-fixture",
        environment=mode,
        plan_created_date=BUSINESS_DATE,
        intended_submit_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        items=(item,),
    )
    pending = attach_approval_link(
        pending,
        approval_path=str(root / "fixtures" / "existing_sell_approval.json"),
        approval_hash="sha256:phase19bt-existing-sell-approval",
        approval_status="APPROVED",
        approved_item_ids=(item.pending_item_id,),
        approval_expires_at=f"{BUSINESS_DATE}T15:00:00+09:00",
    )
    pending = replace(pending, state=PendingPlanState.APPROVED)
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)
    return pending


def _partial_sell_filled_snapshot(**kwargs):
    snapshot_path = Path(kwargs["snapshot_path"])
    report_path = Path(kwargs["report_path"])
    _write_json(
        snapshot_path,
        {
            "generated_at": "2026-07-08T09:05:00+09:00",
            "orders": [
                {
                    "order_id_hash": "sell_order_6522_reduce",
                    "issue_code": "6522",
                    "side": "sell",
                    "quantity": "300",
                    "executed_quantity": "300",
                    "remaining_quantity": "0",
                    "status": "全部約定",
                    "as_of": "2026-07-08T09:05:00+09:00",
                }
            ],
            "executions": [],
            "positions": [
                {
                    "position_id": "position_6522_reduced",
                    "issue_code": "6522",
                    "quantity": "700",
                    "average_price": "100",
                    "market_value": "70000",
                }
            ],
            "buying_power": {
                "raw_clmid": "CLMZanKaiKanougaku",
                "cash_available": "1030000",
                "buying_power": "1030000",
                "currency": "JPY",
            },
            "health": {
                "orders": {"status": "PASS", "count": 1},
                "positions": {"status": "PASS", "count": 1},
                "executions": {"status": "PASS", "count": 0, "detail_attempted_count": 0},
            },
        },
    )
    _write_json(report_path, {"status": "PASS"})
    return type("SnapshotResult", (), {"status": "PASS"})()


def _demo_settings() -> BrokerSettings:
    return BrokerSettings(
        environment="demo",
        base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9",
        second_password_file="/tmp/phase19bt-second-password",
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
            "manual_review_threshold": {
                "buy_amount": None,
                "sell_liquidation_amount": None,
            },
        },
    )
    return path


def _write_broker_positions_snapshot(root: Path, *, symbol: str, quantity: float, available_quantity: float) -> None:
    _write_json(
        root / "broker" / "snapshots" / "positions" / "positions-phase19bt.json",
        {
            "kind": "positions",
            "source": "broker_readonly",
            "as_of": "2026-07-08T08:30:00+09:00",
            "review_required": False,
            "production_equivalent": True,
            "records": [
                {
                    "environment": "demo",
                    "source": "broker_readonly",
                    "as_of": "2026-07-08T08:30:00+09:00",
                    "account_type": "cash",
                    "issue_code": symbol,
                    "symbol": symbol,
                    "quantity": quantity,
                    "available_quantity": available_quantity,
                    "review_required": False,
                    "production_equivalent": True,
                }
            ],
        },
    )


def _load_policy(path: Path):
    from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy

    return load_capital_deployment_policy(path)


def _historical_context() -> dict:
    return {
        "runtime_mode": "historical",
        "historical_replay": True,
        "broker_environment": "historical_simulated",
        "simulation": True,
        "broker_write": False,
        "external_delivery": False,
        "tachibana_demo_write": False,
        "tachibana_production_write": False,
        "submit_enabled": False,
        "runtime_test_run_id": "phase19bt-test",
        "runtime_test_profile_id": "historical-smoke",
        "runtime_test_evidence_root": "reports/runtime_tests/runs/phase19bt-test",
    }


def _accepted_generation_binding(*, mode: str, business_date: str) -> dict:
    return {
        "schema_version": "phase26_step8_accepted_generation_binding.v1",
        "consumer": "sell_planning_pending_pipeline",
        "mode": mode,
        "requested_business_date": business_date,
        "selected_business_date": business_date,
        "temporal_authority_source": "runtime_business_date",
        "temporal_authority_winner": "business_date_bound_accepted_generation",
        "temporal_authority_status": "PASS",
        "accepted_generation_id": "accepted-generation-pf3l",
        "accepted_generation_source": "test_fixed_authority",
        "accepted_generation_business_date": business_date,
        "accepted_generation_status": "RESOLVED_COMMITTED",
        "accepted_generation_accepted_at": f"{business_date}T08:00:00+09:00",
        "accepted_generation_manifest_path": "runtime_state/accepted_buy_ai_bundle.json",
        "aggregate_hash": "sha256:pf3l",
        "generation_binding_status": "PASS",
        "temporal_binding_status": "PASS",
        "business_date_conflict": False,
        "market_as_of_business_date": business_date,
        "generation_conflict": False,
        "latest_fallback_used": False,
        "shared_state_fallback_used": False,
        "default_generation_used": False,
        "legacy_component_fallback_used": False,
        "promotion_candidate_fallback_used": False,
        "manual_model_path_used": False,
    }


def _write_safety_decision(root: Path, *, mode: str) -> None:
    _write_json(
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": "safety-phase19bt-fixture",
            "safety_policy_version": "safety_policy_v1",
            "safety_source": "test_phase19_bt",
            "business_date": BUSINESS_DATE,
            "runtime_mode": mode,
            "decision": "ALLOW",
            "reason": "phase19bt fixture safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": "2026-07-08T08:00:00+09:00",
            "expires_at": "2026-07-08T15:00:00+09:00",
        },
    )


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append_jsonl(path: Path, payload: dict) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
