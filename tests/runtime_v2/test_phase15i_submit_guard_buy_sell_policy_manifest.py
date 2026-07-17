import json
from dataclasses import replace
from pathlib import Path
from typing import Optional

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.cli import run_daily_operation
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy
from ai_fund_lab_v2.runtime_v2.submit.pipeline import (
    SubmitItemResult,
    SubmitPipelineResult,
    run_submit_pipeline,
)

from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings


def test_phase15i_buy_over_100k_uses_policy_not_hidden_max_order_amount(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, positions=[], cash=1_000_000, market_value=0)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    pending = _approved_pending(
        (
            _item(
                pending_item_id="buy-1",
                symbol="7203",
                side="BUY",
                quantity=100,
                estimated_price=1500,
                estimated_amount=150_000,
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
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    evidence = result.submit_guard_item_evidence[0]
    assert result.status == "PASS"
    assert result.submitted_count == 1
    assert evidence["side"] == "BUY"
    assert evidence["estimated_amount"] == 150_000
    assert evidence["guard_decision"] == "PASS"
    assert evidence["policy_source"] == str(policy_path)
    assert evidence["notional_guard_source"] == "derived_from_capital_allocation_and_constraints"
    assert evidence["max_buy_order_amount"] is None
    assert evidence["violated_policy"] == ""


def test_phase15i_sell_over_100k_is_not_blocked_by_buy_notional_cap(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(
        runtime_root,
        positions=[_position("6522", quantity=1000, price=300)],
        cash=700_000,
        market_value=300_000,
    )
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json", max_buy_order_amount=100_000)
    _write_broker_positions_snapshot(runtime_root, symbol="6522", quantity=1000, available_quantity=1000)
    pending = _approved_pending(
        (
            _item(
                pending_item_id="sell-1",
                symbol="6522",
                side="SELL",
                quantity=1000,
                estimated_price=300,
                estimated_amount=300_000,
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
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    evidence = result.submit_guard_item_evidence[0]
    assert result.status == "PASS"
    assert result.submitted_count == 1
    assert evidence["side"] == "SELL"
    assert evidence["estimated_amount"] == 300_000
    assert evidence["guard_decision"] == "PASS"
    assert evidence["notional_guard_source"] == "current_owned_available_quantity_policy"
    assert evidence["max_buy_order_amount"] == 100_000
    assert evidence["max_sell_liquidation_amount"] is None
    assert evidence["broker_available_quantity_checked"] is True
    assert evidence["broker_available_quantity_source"] == "broker_readonly"
    assert evidence["broker_available_quantity"] == 1000
    assert evidence["current_quantity"] == 1000
    assert evidence["manual_review_required"] is False
    assert evidence["violated_policy"] == ""


def test_phase15i_missing_policy_does_not_fallback_for_submit(tmp_path):
    runtime_root = _runtime_root(tmp_path)
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
        )
    )
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.demo_submit_executed is False
    assert result.submit_guard_policy["policy_missing"] is True
    assert "capital deployment policy is required" in result.reason


def test_phase15i_cli_manifest_contains_submit_guard_policy_and_item_evidence(monkeypatch, tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, positions=[], cash=1_000_000, market_value=0)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
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

    def fake_submit_pipeline(**kwargs):
        return SubmitPipelineResult(
            status="PASS",
            reason="submitted",
            pending_plan_id="pending-phase15i",
            pending_path=str(runtime_root / "pending_order_plan" / "pending_order_plan.json"),
            orders_ledger_path=str(runtime_root / "persistent_ledger" / "orders.jsonl"),
            demo_submit_executed=False,
            submitted_count=0,
            accepted_count=0,
            rejected_count=0,
            unknown_count=0,
            blocked_count=0,
            pending_consumed=False,
            submitted_order_ids=(),
            ledger_order_record_ids=(),
            submitted_symbols=(),
            item_results=(
                SubmitItemResult(
                    pending_item_id="buy-1",
                    symbol="7203",
                    side="BUY",
                    quantity=100,
                    preflight_status="PASS",
                    submit_status="DRY_RUN_READY",
                    submitted=False,
                    accepted=False,
                    rejected=False,
                    unknown=False,
                    blocked=False,
                    review_required=False,
                    broker_order_id_hash="",
                    ledger_order_record_id="",
                    reason="fake",
                    issue_code_normalization={},
                    response_classification={},
                    configuration_diagnostic={},
                    next_action="",
                    guard_evidence={"side": "BUY", "guard_decision": "PASS", "policy_source": str(policy_path)},
                ),
            ),
            submit_guard_policy={"guard_policy_version": "submit_guard_policy_v1", "policy_source": str(policy_path)},
            submit_guard_item_evidence=(
                {"side": "BUY", "guard_decision": "PASS", "policy_source": str(policy_path)},
            ),
        )

    monkeypatch.setattr(run_daily_operation, "run_submit_pipeline", fake_submit_pipeline)

    exit_code = run_daily_operation.main(
        [
            "--mode",
            "demo",
            "--job",
            "submit",
            "--business-date",
            "2026-07-09",
            "--submit-enabled",
            "true",
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
    assert exit_code == 0
    assert manifest["submit_guard_policy"]["guard_policy_version"] == "submit_guard_policy_v1"
    assert manifest["submit_guard_item_evidence"][0]["side"] == "BUY"
    assert manifest["submit_guard_item_evidence"][0]["guard_decision"] == "PASS"


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


def _approved_pending(items: tuple[PendingOrderItem, ...], *, policy_path: Optional[Path] = None):
    if policy_path is not None:
        policy = load_capital_deployment_policy(policy_path)
        items = tuple(_item_with_policy(item, policy) for item in items)
    pending = promote_order_plan_to_pending(
        order_plan_id="order-plan-phase15i",
        source_order_plan_path=".runtime/runtime_state/morning_pipeline/2026-07-09/order_plan.json",
        source_order_plan_hash="sha256:phase15i-order-plan",
        environment="demo",
        plan_created_date="2026-07-09",
        intended_submit_date="2026-07-09",
        target_session_date="2026-07-09",
        items=items,
    )
    approval = ApprovalArtifact(
        approval_id="approval-phase15i",
        approval_request_id="approval-request-phase15i",
        pending_plan_id=pending.pending_plan_id,
        order_plan_id=pending.source_order_plan.order_plan_id,
        status=ApprovalStatus.APPROVED,
        approved_item_ids=tuple(item.pending_item_id for item in pending.items),
        rejected_item_ids=(),
        approval_hash="sha256:approval-phase15i",
        approved_at="2026-07-09T08:45:00+09:00",
        expires_at="2026-07-09T15:00:00+09:00",
        review_required=False,
        reason="phase15i approval",
        policy_version=pending.policy_version,
        policy_source=pending.policy_source,
        pending_policy_hash=pending.pending_policy_hash,
    )
    return link_approval_to_pending(pending_plan=pending, approval_artifact=approval)


def _item_with_policy(item: PendingOrderItem, policy) -> PendingOrderItem:
    return replace(
        item,
        capital_allocation_amount=item.estimated_amount,
        policy_version=policy.policy_version,
        policy_source=policy.policy_source,
        evaluation_capital=policy.evaluation_capital,
        target_investment_ratio=policy.target_investment_ratio,
        cash_buffer=policy.cash_buffer,
        max_exposure=policy.max_exposure,
        max_position_weight=policy.max_position_weight,
        max_positions=policy.max_positions,
        max_buy_order_amount=policy.max_buy_order_amount,
        max_sell_liquidation_amount=policy.max_sell_liquidation_amount,
        min_order_amount=policy.min_order_amount,
        buy_notional_policy=policy.buy_notional_policy,
        sell_liquidation_policy=policy.sell_liquidation_policy,
        manual_review_threshold={
            "buy_amount": policy.manual_review_threshold.buy_amount,
            "sell_liquidation_amount": policy.manual_review_threshold.sell_liquidation_amount,
        },
        sizing_policy_reason="phase15i fixture policy evidence",
    )


def _item(
    *,
    pending_item_id: str,
    symbol: str,
    side: str,
    quantity: float,
    estimated_price: float,
    estimated_amount: float,
) -> PendingOrderItem:
    return PendingOrderItem(
        pending_item_id=pending_item_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        order_type="MARKET",
        estimated_price=estimated_price,
        estimated_amount=estimated_amount,
        approved=True,
        state="APPROVED",
        listed_info={
            "code": symbol,
            "market": "プライム",
            "product_category": "011",
            "security_type": "011",
            "current_listed": True,
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
    )


def _write_current_state(root: Path, *, positions: list[dict], cash: float, market_value: float) -> None:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase15i",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2026-07-09",
            "positions": positions,
            "cash": cash,
            "buying_power": cash,
            "market_value": market_value,
            "total_equity": cash + market_value,
            "review_required": False,
            "current_state_confirmed_empty": not positions,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
        },
    )


def _write_runtime_readiness_authorities(root: Path, *, business_date: str) -> None:
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "runtime_v2_operation_state_v1",
            "role": "authoritative_runtime_operation_state",
            "business_date": business_date,
            "generated_at": business_date + "T08:30:00+09:00",
            "updated_at": business_date + "T08:30:00+09:00",
            "environment": "demo",
            "runtime_mode": "demo",
            "state": "CURRENT_STATE_LOADED",
            "safety_state": "NORMAL",
            "source": "phase15i_cli_fixture",
        },
    )
    _write_json(
        root / "runtime_state" / "market" / business_date / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "business_date": business_date,
            "runtime_business_date": business_date,
            "market_date": business_date,
            "as_of": business_date,
            "market_status": "READY",
            "quote_status": "READY",
            "quote_count": 1,
            "market_summary": {"status": "READY"},
        },
    )
    _write_json(
        root / "runtime_state" / "broker_readonly" / business_date / "snapshot.json",
        {
            "schema_version": "runtime_v2_broker_readonly_snapshot_v1",
            "business_date": business_date,
            "generated_at": business_date + "T08:30:00+09:00",
            "environment": "demo",
            "review_required": False,
            "positions": [],
            "orders": [],
            "executions": [],
        },
    )


def _attach_pending_safety_evidence(root: Path, *, safety_decision_id: str) -> None:
    path = root / "pending_order_plan" / "pending_order_plan.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["safety_decision_id"] = safety_decision_id
    payload["safety_policy_version"] = "safety_policy_v1"
    approval = dict(payload.get("approval") or {})
    approval["safety_decision_id"] = safety_decision_id
    approval["safety_policy_version"] = "safety_policy_v1"
    payload["approval"] = approval
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _position(symbol: str, *, quantity: float, price: float) -> dict:
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": price,
        "market_value": quantity * price,
        "source": "runtime_v2_runtime_owned_fill_projection",
        "as_of": "2026-07-09",
    }


def _write_broker_positions_snapshot(
    root: Path,
    *,
    symbol: str,
    quantity: float,
    available_quantity: float,
    as_of: str = "2026-07-09T08:30:00+09:00",
) -> Path:
    path = root / "broker" / "snapshots" / "positions" / "positions-phase15i.json"
    _write_json(
        path,
        {
            "kind": "positions",
            "source": "broker_readonly",
            "as_of": as_of,
            "review_required": False,
            "production_equivalent": True,
            "records": [
                {
                    "environment": "demo",
                    "source": "broker_readonly",
                    "as_of": as_of,
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
    return path


def _write_policy(path: Path, *, max_buy_order_amount=None, max_sell_liquidation_amount=None) -> Path:
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
            "max_buy_order_amount": max_buy_order_amount,
            "max_sell_liquidation_amount": max_sell_liquidation_amount,
            "buy_notional_policy": "derived_from_capital_allocation_and_constraints",
            "sell_liquidation_policy": "current_owned_available_quantity_policy",
            "manual_review_threshold": {
                "buy_amount": None,
                "sell_liquidation_amount": None,
            },
        },
    )
    return path


def _latest_manifest(runtime_root: Path, business_date: str):
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / business_date).glob("*.json"))
    return json.loads(manifests[-1].read_text(encoding="utf-8"))


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_safety_decision(
    root: Path,
    *,
    decision: str = "ALLOW",
    block_buy: bool = False,
    block_sell: bool = False,
    block_submit: bool = False,
    halt_runtime: bool = False,
    reason: str = "phase15 fixture safety allow",
) -> Path:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": "safety-phase15-fixture",
            "safety_policy_version": "safety_policy_v1",
            "safety_source": str(path),
            "business_date": "2026-07-09",
            "runtime_mode": "demo",
            "decision": decision,
            "reason": reason,
            "review_required": decision == "REVIEW_REQUIRED",
            "block_buy": block_buy,
            "block_sell": block_sell,
            "block_submit": block_submit,
            "halt_runtime": halt_runtime,
            "emergency_stop": halt_runtime,
            "generated_at": "2026-07-09T08:00:00+09:00",
            "expires_at": "2026-07-09T15:00:00+09:00",
        },
    )
    return path
