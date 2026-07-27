import json
from pathlib import Path

from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import SellExitDecision, run_sell_planning_pending_pipeline
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy
from ai_fund_lab_v2.runtime_v2.position_management.producer import _sell_exit_decisions_from_artifact
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline


def test_phase21_b_no_signal_preserves_existing_buy_pending(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])
    existing = _write_existing_buy_pending(runtime_root, symbol="7203")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(),
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "NO_SIGNAL"
    assert result.preserved_existing_buy_pending is True
    assert result.pending_plan_id == existing.pending_plan_id
    assert pending["pending_plan_id"] == existing.pending_plan_id
    assert pending["state"] == "APPROVED"
    assert pending["items"][0]["side"] == "BUY"


def test_phase21_b_no_signal_without_existing_buy_writes_empty(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(),
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "NO_SIGNAL"
    assert result.preserved_existing_buy_pending is False
    assert pending["status"] == "EMPTY"
    assert pending["active_pending"] is False


def test_phase21_b_sell_order_composes_existing_buy_and_sell_pending(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])
    _write_existing_buy_pending(runtime_root, symbol="7203")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(SellExitDecision(symbol="6522", quantity=100, reason="exit signal"),),
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "PASS"
    assert result.composite_pending is True
    assert result.pending_composition_model == "COMPOSITE_PENDING_PLAN"
    assert sorted(item["side"] for item in pending["items"]) == ["BUY", "SELL"]
    assert sorted(pending["approval"]["approved_item_ids"]) == sorted(item["pending_item_id"] for item in pending["items"])


def test_phase21_b_pm_add_generates_buy_pending_with_lineage(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy = _policy(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("94320", quantity=1000, price=100)])

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(SellExitDecision(symbol="9432", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-1"),),
        capital_deployment_policy=policy,
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    item = pending["items"][0]

    assert result.status == "PASS"
    assert result.add_consumer_status == "PASS"
    assert item["side"] == "BUY"
    assert item["source_decision_type"] == "ADD"
    assert item["source_pm_decision_id"] == "pm-add-1"
    assert item["source_position_symbol"] == "94320"
    assert item["add_candidate_signal"] is True
    assert item["capital_allocation_status"] == "APPROVED"
    assert item["quantity"] > 0


def test_phase21_b_pm_add_rejects_duplicate_pending_order(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy = _policy(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("94320", quantity=1000, price=100)])
    _write_existing_buy_pending(runtime_root, symbol="9432")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(SellExitDecision(symbol="94320", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-dup"),),
        capital_deployment_policy=policy,
    )

    assert result.status == "NO_SIGNAL"
    assert result.preserved_existing_buy_pending is True
    assert result.add_consumer_status == "REJECTED"
    assert result.add_rejected_count == 1


def test_phase21_b_pm_producer_keeps_add_as_planning_candidate():
    decisions = _sell_exit_decisions_from_artifact(
        {
            "artifact_path": "pm.json",
            "decisions": [
                {
                    "decision_id": "pm-2026-07-08-9432-add",
                    "symbol": "9432",
                    "decision": "ADD",
                    "reason": "ADD is outside SELL Planning scope",
                    "confidence": 0.9,
                    "runtime_sell_quantity": 0,
                }
            ],
        }
    )

    assert len(decisions) == 1
    assert decisions[0].source_decision == "ADD"
    assert decisions[0].source_decision_id == "pm-2026-07-08-9432-add"


def test_phase21_b_add_submit_ledger_keeps_lineage(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    policy = load_capital_deployment_policy(policy_path)
    _write_current_state(runtime_root, positions=[_current_position("72030", quantity=1000, price=100)])

    run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(SellExitDecision(symbol="7203", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-ledger"),),
        capital_deployment_policy=policy,
    )
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )
    orders = _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl")

    assert submit.status == "PASS"
    assert orders[0]["side"] == "BUY"
    assert orders[0]["source_decision_type"] == "ADD"
    assert orders[0]["source_pm_decision_id"] == "pm-add-ledger"
    assert orders[0]["add_candidate_signal"] is True


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "runtime_state").mkdir(parents=True)
    ledger = root / "persistent_ledger"
    ledger.mkdir(parents=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (ledger / f"{name}.jsonl").write_text("", encoding="utf-8")
    _write_safety_decision(root)
    return root


def _write_current_state(root: Path, *, positions):
    payload = {
        "schema_version": "1",
        "asset_state_id": "asset-phase21b",
        "environment": "demo",
        "source": "fixture",
        "as_of": "2026-07-08",
        "positions": positions,
        "cash": 1_000_000,
        "buying_power": 1_000_000,
        "market_value": sum(float(item["market_value"]) for item in positions),
        "total_equity": 1_000_000 + sum(float(item["market_value"]) for item in positions),
        "review_required": False,
        "production_equivalent": False,
        "current_state_confirmed_empty": False,
        "current_positions_unknown": False,
        "cash_unknown": False,
        "buying_power_unknown": False,
        "generated_from": ["fixture"],
        "created_at": "2026-07-08",
        "updated_at": "2026-07-08",
    }
    _write_json(root / "persistent_ledger" / "state.json", payload)


def _current_position(symbol: str, *, quantity: float, price: float) -> dict:
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": price,
        "market_value": quantity * price,
        "source": "fixture",
        "as_of": "2026-07-08",
    }


def _write_existing_buy_pending(root: Path, *, symbol: str):
    order_plan_path = root / "fixtures" / f"buy_order_plan_{symbol}.json"
    order_plan_path.parent.mkdir(parents=True, exist_ok=True)
    order_plan_path.write_text(json.dumps({"order_plan_id": f"order-plan-buy-{symbol}"}), encoding="utf-8")
    item = PendingOrderItem(
        pending_item_id=f"opi-buy-{symbol}",
        symbol=symbol,
        side="BUY",
        quantity=100,
        order_type="MARKET",
        estimated_price=500,
        estimated_amount=50_000,
        approved=True,
        state="READY",
        policy_version="capital_deployment_v1",
        policy_source="fixture",
        evaluation_capital=1_000_000,
        target_investment_ratio=0.85,
        cash_buffer=0.05,
        max_exposure=850_000,
        max_position_weight=0.2,
        max_positions=5,
        min_order_amount=0,
        buy_notional_policy="fixture",
        sell_liquidation_policy="fixture",
    )
    pending = promote_order_plan_to_pending(
        order_plan_id=f"order-plan-buy-{symbol}",
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash="sha256:fixture",
        environment="demo",
        plan_created_date="2026-07-08",
        intended_submit_date="2026-07-08",
        target_session_date="2026-07-08",
        items=(item,),
    )
    from ai_fund_lab_v2.runtime_v2.pending.promotion import attach_approval_link

    pending = attach_approval_link(
        pending,
        approval_path=str(root / "fixtures" / f"buy_approval_{symbol}.json"),
        approval_hash="sha256:approval",
        approval_status="APPROVED",
        approved_item_ids=(item.pending_item_id,),
        approval_expires_at="2026-07-08T15:00:00+09:00",
    )
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)
    return pending


def _policy(tmp_path: Path):
    return load_capital_deployment_policy(_policy_path(tmp_path))


def _policy_path(tmp_path: Path) -> Path:
    path = tmp_path / "capital_deployment_policy.json"
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "target_investment_ratio": 0.85,
            "cash_buffer": 0.05,
            "max_exposure": 850_000,
            "max_position_weight": 0.2,
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


def _demo_settings() -> BrokerSettings:
    return BrokerSettings(
        environment="demo",
        base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9",
        second_password_file="/tmp/phase21b-second-password",
    )


def _write_safety_decision(root: Path) -> Path:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": "safety-phase21b-fixture",
            "safety_policy_version": "safety_policy_v1",
            "safety_source": str(path),
            "business_date": "2026-07-08",
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase21b fixture safety allow",
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
    return path


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
