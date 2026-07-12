from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import get_broker_capability
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import pending_order_plan_to_payload, write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    capital_deployment_policy_hash,
    load_capital_deployment_policy,
)


BUSINESS_DATE = "2026-07-09"
ISSUE_CODE = "6522"
PENDING_ITEM_ID = "phase15bn-sell-6522"
ORDER_CONDITIONS = {
    PENDING_ITEM_ID: {
        "order_type": "MARKET",
        "price_condition": "MARKET",
        "limit_price": None,
        "target_session": BUSINESS_DATE,
        "time_in_force": "DAY",
        "quantity": 100.0,
        "side": "SELL",
        "issue_code": ISSUE_CODE,
        "broker_issue_code": ISSUE_CODE,
    }
}


def build_isolated_submit_fixture(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    _init_dirs(root)
    policy_path = root / "runtime_state" / "policy" / "capital_deployment.json"
    _write_policy(policy_path)
    policy = load_capital_deployment_policy(policy_path)
    policy_hash = capital_deployment_policy_hash(policy)
    order_condition_path = root / "runtime_state" / "order_condition_approval" / BUSINESS_DATE / "order-condition-approval-phase15bn.json"
    broker_capability_path = root / "runtime_state" / "broker_capability" / BUSINESS_DATE / "broker-capability-demo.json"
    _write_broker_capability(broker_capability_path)
    broker_capability_hash = _hash_json(_read_json(broker_capability_path))
    _write_order_condition_approval(order_condition_path, policy_hash, broker_capability_hash)
    order_condition_hash = _hash_json(_read_json(order_condition_path))
    _write_safety(root)
    _write_current(root)
    _write_market_and_quote(root)
    _write_broker_snapshot(root)
    pending = _approved_pending(policy_path, policy_hash, order_condition_hash)
    pending_path = root / "pending_order_plan" / "pending_order_plan.json"
    write_pending_order_plan(pending_path, pending)
    _write_review_promotion_apply_evidence(
        root=root,
        policy_hash=policy_hash,
        order_condition_hash=order_condition_hash,
        broker_capability_hash=broker_capability_hash,
        pending_hash=_hash_json(pending_order_plan_to_payload(pending)),
    )
    manifest = {
        "schema_version": "phase15bn_isolated_submit_scenario_v1",
        "phase": "Phase15-BN",
        "business_date": BUSINESS_DATE,
        "runtime_root": str(root),
        "scenario_side": "SELL",
        "scenario_issue_code": ISSUE_CODE,
        "existing_runtime_referenced": False,
        "safety_action_scope": {
            "sell_submit": "ALLOWED",
            "broker_write": "ALLOWED_FOR_ACCEPTANCE",
        },
        "order_condition_authority": {
            "policy": "defines allowed order methods and constraints",
            "human_approval": "approves concrete item order conditions",
            "submit_pending_producer": "freezes approved conditions into Pending",
            "broker_capability_evidence": "validates supported side/order/session/cash/demo constraints",
            "submit_runtime": "sends approved conditions without changing them",
        },
        "artifacts": {
            "pending": str(pending_path),
            "policy": str(policy_path),
            "order_condition_approval": str(order_condition_path),
            "broker_capability": str(broker_capability_path),
            "safety": str(root / "runtime_state" / "safety" / "latest_safety_decision.json"),
            "current": str(root / "persistent_ledger" / "state.json"),
            "broker_snapshot": str(root / "broker" / "snapshots" / "positions" / "positions-phase15bn.json"),
            "market_evidence": str(root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json"),
            "quote_evidence": str(root / "runtime_state" / "quote" / BUSINESS_DATE / "quote_evidence.json"),
            "human_approval": str(root / "runtime_state" / "human_approval" / BUSINESS_DATE / "human-approval-phase15bn.json"),
            "promotion_candidate": str(root / "runtime_state" / "pending_promotion_candidate" / BUSINESS_DATE / "promotion-candidate-phase15bn.json"),
            "apply_candidate": str(root / "runtime_state" / "authoritative_pending_apply_candidate" / BUSINESS_DATE / "apply-candidate-phase15bn.json"),
        },
        "broker_write_performed": False,
        "submit_attempted": False,
        "execution_created": False,
        "current_mutated_after_fixture": False,
    }
    manifest_path = root / "scenario_manifest.json"
    _write_json(manifest_path, manifest)
    return manifest


def _init_dirs(root: Path) -> None:
    for path in (
        root / "pending_order_plan",
        root / "runtime_state",
        root / "runtime_state" / "run_manifest",
        root / "runtime_state" / "logs",
        root / "reports" / "runtime_v2",
        root / "reports" / "public" / "runtime_v2",
        root / "persistent_ledger",
    ):
        path.mkdir(parents=True, exist_ok=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (root / "persistent_ledger" / f"{name}.jsonl").write_text("", encoding="utf-8")


def _approved_pending(policy_path: Path, policy_hash: str, order_condition_hash: str):
    policy = load_capital_deployment_policy(policy_path)
    item = PendingOrderItem(
        pending_item_id=PENDING_ITEM_ID,
        symbol=ISSUE_CODE,
        side="SELL",
        quantity=100.0,
        order_type="MARKET",
        estimated_price=300.0,
        estimated_amount=30_000.0,
        approved=True,
        state="APPROVED",
        listed_info={
            "code": ISSUE_CODE,
            "market": "プライム",
            "product_category": "011",
            "security_type": "011",
            "current_listed": True,
        },
        capital_allocation_amount=30_000.0,
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
        sizing_policy_reason="phase15bn isolated submit acceptance fixture",
        safety_decision_id="safety-phase15bn-allow",
        safety_policy_version="safety_policy_v1",
        safety_source="phase15bn_fixture",
        safety_decision="ALLOW",
        safety_reason="isolated acceptance fixture",
    )
    pending = promote_order_plan_to_pending(
        order_plan_id="order-plan-phase15bn",
        source_order_plan_path="runtime_state/order_plan/2026-07-09/order-plan-phase15bn.json",
        source_order_plan_hash="sha256:phase15bn-order-plan",
        environment="demo",
        plan_created_date=BUSINESS_DATE,
        intended_submit_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        items=(item,),
    )
    approval = ApprovalArtifact(
        approval_id="human-approval-phase15bn",
        approval_request_id="approval-request-phase15bn",
        pending_plan_id=pending.pending_plan_id,
        order_plan_id=pending.source_order_plan.order_plan_id,
        status=ApprovalStatus.APPROVED,
        approved_item_ids=(PENDING_ITEM_ID,),
        rejected_item_ids=(),
        approval_hash=_hash_json({"approval": "phase15bn", "order_condition_hash": order_condition_hash}),
        approved_at="2026-07-09T08:45:00+09:00",
        expires_at="2026-07-09T15:00:00+09:00",
        review_required=False,
        reason="phase15bn isolated normal submit scenario approval",
        policy_version=pending.policy_version,
        policy_source=pending.policy_source,
        pending_policy_hash=policy_hash,
        safety_decision_id="safety-phase15bn-allow",
        safety_policy_version="safety_policy_v1",
        approved_order_conditions=ORDER_CONDITIONS,
    )
    return link_approval_to_pending(pending_plan=pending, approval_artifact=approval)


def _write_policy(path: Path) -> None:
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
            "allowed_order_types": ["MARKET"],
            "allowed_time_in_force": ["DAY"],
            "manual_review_threshold": {
                "buy_amount": None,
                "sell_liquidation_amount": None,
            },
        },
    )


def _write_safety(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": "safety-phase15bn-allow",
            "safety_policy_version": "safety_policy_v1",
            "safety_source": "phase15bn_fixture",
            "business_date": BUSINESS_DATE,
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "isolated normal submit acceptance fixture",
            "review_required": False,
            "block_buy": True,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": "2026-07-09T08:00:00+09:00",
            "expires_at": "2026-07-09T15:00:00+09:00",
            "freshness_status": "READY",
            "action_permissions": {
                "sell_submit": "ALLOWED",
                "broker_write": "ALLOWED_FOR_ACCEPTANCE",
            },
        },
    )


def _write_current(root: Path) -> None:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase15bn",
            "environment": "demo",
            "source": "phase15bn_isolated_runtime_owned_fixture",
            "as_of": BUSINESS_DATE,
            "position_state_as_of": BUSINESS_DATE,
            "valuation_as_of": BUSINESS_DATE,
            "current_position_status": "READY",
            "current_valuation_status": "READY",
            "positions": [
                {
                    "symbol": ISSUE_CODE,
                    "quantity": 100.0,
                    "average_price": 300.0,
                    "market_value": 30_000.0,
                    "source": "phase15bn_isolated_runtime_owned_fixture",
                    "as_of": BUSINESS_DATE,
                }
            ],
            "cash": 970_000.0,
            "buying_power": 970_000.0,
            "market_value": 30_000.0,
            "total_equity": 1_000_000.0,
            "review_required": False,
            "current_state_confirmed_empty": False,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
        },
    )


def _write_market_and_quote(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "runtime_business_date": BUSINESS_DATE,
            "market_date": BUSINESS_DATE,
            "latest_available_market_date": BUSINESS_DATE,
            "market_freshness_status": "READY",
            "quote_status": "READY",
            "quote_count": 1,
            "provider_status": "READY",
        },
    )
    _write_json(
        root / "runtime_state" / "quote" / BUSINESS_DATE / "quote_evidence.json",
        {
            "schema_version": "runtime_v2_quote_evidence_v1",
            "business_date": BUSINESS_DATE,
            "quote_status": "READY",
            "quotes": [{"issue_code": ISSUE_CODE, "close": 300.0}],
        },
    )


def _write_broker_snapshot(root: Path) -> None:
    _write_json(
        root / "broker" / "snapshots" / "positions" / "positions-phase15bn.json",
        {
            "kind": "positions",
            "source": "broker_readonly",
            "as_of": "2026-07-09T08:30:00+09:00",
            "review_required": False,
            "production_equivalent": True,
            "records": [
                {
                    "environment": "demo",
                    "source": "broker_readonly",
                    "as_of": "2026-07-09T08:30:00+09:00",
                    "account_type": "cash",
                    "issue_code": ISSUE_CODE,
                    "symbol": ISSUE_CODE,
                    "quantity": 100.0,
                    "available_quantity": 100.0,
                    "review_required": False,
                    "production_equivalent": True,
                }
            ],
        },
    )


def _write_broker_capability(path: Path) -> None:
    capability = get_broker_capability("demo")
    _write_json(
        path,
        {
            "schema_version": "runtime_v2_broker_capability_evidence_v1",
            "mode": capability.mode,
            "source": "static_runtime_v2_broker_capability",
            "side": "SELL",
            "order_type": "MARKET",
            "target_session": BUSINESS_DATE,
            "time_in_force": "DAY",
            "cash_equity_only": True,
            "demo_environment": True,
            "supports_order_type": True,
            "supports_session": True,
            "quantity_unit": 100,
            "trading_unit": 100,
            "price_tick": None,
            "limit_price_validation": "NOT_APPLICABLE_FOR_MARKET",
            "capability_status": "READY",
        },
    )


def _write_order_condition_approval(path: Path, policy_hash: str, broker_capability_hash: str) -> None:
    payload = {
        "schema_version": "runtime_v2_order_condition_approval_v1",
        "approval_id": "order-condition-approval-phase15bn",
        "approved_at": "2026-07-09T08:45:00+09:00",
        "expires_at": "2026-07-09T15:00:00+09:00",
        "policy_hash": policy_hash,
        "broker_capability_hash": broker_capability_hash,
        "approved_order_conditions": ORDER_CONDITIONS,
    }
    _write_json(path, payload)


def _write_review_promotion_apply_evidence(
    *,
    root: Path,
    policy_hash: str,
    order_condition_hash: str,
    broker_capability_hash: str,
    pending_hash: str,
) -> None:
    _write_json(
        root / "runtime_state" / "human_approval" / BUSINESS_DATE / "human-approval-phase15bn.json",
        {
            "schema_version": "runtime_v2_human_submit_approval_v1",
            "approval_id": "human-approval-phase15bn",
            "approval_status": "APPROVED_FOR_PENDING_PROMOTION",
            "business_date": BUSINESS_DATE,
            "approved_item_ids": [PENDING_ITEM_ID],
            "policy_hash": policy_hash,
            "order_condition_approval_hash": order_condition_hash,
            "broker_capability_hash": broker_capability_hash,
            "automatic_trade_authorized": False,
            "broker_write_authorized": False,
            "authoritative_pending_promotion_authorized": True,
        },
    )
    _write_json(
        root / "runtime_state" / "pending_promotion_candidate" / BUSINESS_DATE / "promotion-candidate-phase15bn.json",
        {
            "schema_version": "runtime_v2_submit_pending_promotion_candidate_v1",
            "candidate_id": "promotion-candidate-phase15bn",
            "business_date": BUSINESS_DATE,
            "promotion_status": "READY_FOR_APPLY",
            "promotion_allowed": True,
            "policy_hash": policy_hash,
            "order_condition_approval_hash": order_condition_hash,
            "broker_capability_hash": broker_capability_hash,
            "target_pending_plan_id": "pending-order-plan-phase15bn",
            "target_session": BUSINESS_DATE,
            "apply_requested": False,
            "apply_executed": False,
        },
    )
    _write_json(
        root / "runtime_state" / "authoritative_pending_apply_candidate" / BUSINESS_DATE / "apply-candidate-phase15bn.json",
        {
            "schema_version": "runtime_v2_authoritative_pending_apply_candidate_v1",
            "apply_candidate_id": "apply-candidate-phase15bn",
            "business_date": BUSINESS_DATE,
            "target_pending_plan_id": "pending-order-plan-phase15bn",
            "source_pending_hash": pending_hash,
            "policy_hash": policy_hash,
            "order_condition_approval_hash": order_condition_hash,
            "broker_capability_hash": broker_capability_hash,
            "apply_status": "READY_FOR_AUTHORITATIVE_APPLY",
            "apply_allowed": True,
            "apply_requested": False,
            "apply_executed": False,
            "authoritative_pending_mutated": True,
            "isolated_root_only": True,
            "broker_write_performed": False,
            "submit_executed": False,
        },
    )


def _hash_json(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".runtime_acceptance_phase15_submit")
    result = build_isolated_submit_fixture(target)
    print(json.dumps({"scenario_manifest": str(target / "scenario_manifest.json"), "scenario_issue_code": result["scenario_issue_code"]}))
