from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    capital_deployment_policy_hash,
    load_capital_deployment_policy,
)
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand, RuntimeV2SubmitResult

from tests.runtime_v2.phase15bo_submit_simulation import RuntimeV2SubmitSimulationAdapter
from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings


BUSINESS_DATE = "2022-12-08"
PENDING_PLAN_ID = "pending-order-plan-buy-review-sell-continuation-2022-12-08-9002066a3dd7"
REVIEW_BUY_ITEM_ID = "strategy-dae988dcba6a12b37f97"
MISSING_SELL_ITEM_ID = "strategy-5c7d2975b463ced32e60"
EXISTING_ITEM_IDS = (
    "strategy-9242cb1dda97a6433677",
    "strategy-8f700934de4464ffa4d5",
    "strategy-d869e35933dcd6215538",
    "strategy-72c08989f99bb27f815a",
)


def test_phase31_f1w_partial_submit_reconciles_existing_items_and_submits_missing_once(tmp_path):
    runtime_root = _build_f1w_fixture(tmp_path)
    adapter = RuntimeV2SubmitSimulationAdapter(scenario="SIMULATED_ACCEPTED")

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=adapter,
        capital_deployment_policy_path=runtime_root / "runtime_state" / "policy" / "capital_deployment.json",
    )
    pending = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    orders = _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl")

    assert result.status == "PASS"
    assert result.reason == "submitted_with_reviewed_buy_items_not_submitted"
    assert adapter.submit_calls == 1
    assert adapter.request_payloads[0]["pending_item_id"] == MISSING_SELL_ITEM_ID
    assert result.submitted_count == 5
    assert result.accepted_count == 5
    assert result.pending_consumed is False
    assert pending["state"] == "REVIEW_REQUIRED"
    assert pending["consume"]["consumed"] is False
    assert len(pending["consume"]["submitted_order_ids"]) == 5
    assert len(pending["consume"]["ledger_order_record_ids"]) == 5
    assert len(orders) == 5
    assert _item_state(pending, REVIEW_BUY_ITEM_ID) == "REVIEW_REQUIRED"
    assert _item_state(pending, MISSING_SELL_ITEM_ID) == "CONSUMED"
    assert all(_item_state(pending, item_id) == "CONSUMED" for item_id in EXISTING_ITEM_IDS)
    assert not any(order["pending_item_id"] == REVIEW_BUY_ITEM_ID for order in orders)

    retry_adapter = RuntimeV2SubmitSimulationAdapter(scenario="SIMULATED_ACCEPTED")
    retry = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=retry_adapter,
        capital_deployment_policy_path=runtime_root / "runtime_state" / "policy" / "capital_deployment.json",
    )
    retry_orders = _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl")

    assert retry.status == "PASS"
    assert retry.reason == "submitted_with_reviewed_buy_items_not_submitted"
    assert retry_adapter.submit_calls == 0
    assert retry.submitted_count == 5
    assert len(retry_orders) == 5


def test_phase31_f1y_existing_sell_reconciliation_precedes_available_quantity_guard(tmp_path):
    runtime_root = _build_f1w_fixture(tmp_path)
    adapter = F1Y34940PreflightHaltAdapter()
    state_before = (runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8")
    cash_before = (runtime_root / "persistent_ledger" / "cash.jsonl").read_text(encoding="utf-8")
    executions_before = (runtime_root / "persistent_ledger" / "executions.jsonl").read_text(encoding="utf-8")

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=adapter,
        capital_deployment_policy_path=runtime_root / "runtime_state" / "policy" / "capital_deployment.json",
    )
    pending = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    orders = _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl")
    by_symbol = {item.symbol: item for item in result.item_results}

    assert result.status == "PASS"
    assert result.reason == "submitted_with_reviewed_and_terminal_non_executable_items_not_submitted"
    assert result.blocked_count == 0
    assert result.submitted_count == 4
    assert adapter.submit_calls == 0
    assert adapter.preflight_item_ids == [MISSING_SELL_ITEM_ID]
    assert {symbol for symbol, item in by_symbol.items() if item.preflight_status == "RECONCILED"} == {
        "61440",
        "82560",
        "37790",
        "45910",
    }
    assert by_symbol["34940"].preflight_status == "NOT_EXECUTABLE"
    assert by_symbol["34940"].reason == "EXECUTION_AUTHORITY_UNAVAILABLE"
    assert by_symbol["34940"].guard_evidence["execution_feasibility_status"] == "NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE"
    assert by_symbol["34940"].guard_evidence["adapter_submit_called"] is False
    assert by_symbol["34940"].guard_evidence["order_created"] is False
    assert by_symbol["34940"].guard_evidence["broker_side_effect_created"] is False
    assert by_symbol["34940"].guard_evidence["ledger_order_created"] is False
    assert by_symbol["34940"].guard_evidence["position_mutated"] is False
    assert by_symbol["34940"].guard_evidence["cash_mutated"] is False
    assert by_symbol["34940"].guard_evidence["realized_pnl_mutated"] is False
    assert by_symbol["34940"].guard_evidence["retry_eligible_same_day"] is False
    assert by_symbol["34940"].guard_evidence["next_day_re_evaluation_required"] is True
    assert by_symbol["34940"].guard_evidence["future_information_used"] is False
    assert by_symbol["76920"].review_required is True
    assert by_symbol["76920"].submitted is False
    assert pending["consume"]["consumed"] is False
    assert set(pending["consume"]["submitted_order_ids"]) == {
        order["order_id"] for order in orders if order["symbol"] in {"61440", "82560", "37790", "45910"}
    }
    assert set(pending["consume"]["ledger_order_record_ids"]) == {
        order["ledger_record_id"] for order in orders if order["symbol"] in {"61440", "82560", "37790", "45910"}
    }
    assert _item_state(pending, REVIEW_BUY_ITEM_ID) == "REVIEW_REQUIRED"
    assert _item_state(pending, MISSING_SELL_ITEM_ID) == "NOT_EXECUTABLE"
    terminal_item = next(item for item in pending["items"] if item["pending_item_id"] == MISSING_SELL_ITEM_ID)
    assert terminal_item["approved"] is False
    assert terminal_item["feasibility_status"] == "NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE"
    assert terminal_item["item_review_reason"] == "EXECUTION_AUTHORITY_UNAVAILABLE"
    assert MISSING_SELL_ITEM_ID not in pending["approved_item_ids"]
    assert MISSING_SELL_ITEM_ID not in pending["approved_sell_item_ids"]
    assert all(_item_state(pending, item_id) == "CONSUMED" for item_id in EXISTING_ITEM_IDS)
    assert not any(order["pending_item_id"] == MISSING_SELL_ITEM_ID for order in orders)
    assert (runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8") == state_before
    assert (runtime_root / "persistent_ledger" / "cash.jsonl").read_text(encoding="utf-8") == cash_before
    assert (runtime_root / "persistent_ledger" / "executions.jsonl").read_text(encoding="utf-8") == executions_before

    retry_adapter = F1Y34940PreflightHaltAdapter()
    retry = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=retry_adapter,
        capital_deployment_policy_path=runtime_root / "runtime_state" / "policy" / "capital_deployment.json",
    )

    assert retry.submitted_count == 4
    assert MISSING_SELL_ITEM_ID not in retry_adapter.preflight_item_ids
    assert retry_adapter.submit_calls == 0
    assert len(_read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl")) == 4


def test_phase31_f2b_zero_submission_terminal_noop_continuation_passes_without_fake_side_effects(tmp_path):
    runtime_root = _build_f1w_fixture(tmp_path)
    _reduce_fixture_to_reviewed_buy_and_missing_sell(runtime_root)
    adapter = F1Y34940PreflightHaltAdapter()
    state_before = (runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8")
    cash_before = (runtime_root / "persistent_ledger" / "cash.jsonl").read_text(encoding="utf-8")
    executions_before = (runtime_root / "persistent_ledger" / "executions.jsonl").read_text(encoding="utf-8")

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=adapter,
        capital_deployment_policy_path=runtime_root / "runtime_state" / "policy" / "capital_deployment.json",
    )
    pending = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    orders = _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl")
    by_symbol = {item.symbol: item for item in result.item_results}
    aggregate = result.no_order_authority_evidence["submit_aggregate_terminal_noop_authority"]

    assert result.status == "PASS"
    assert result.reason == "zero_submission_terminal_noop_continuation"
    assert result.submitted_count == 0
    assert result.accepted_count == 0
    assert result.blocked_count == 0
    assert result.rejected_count == 0
    assert result.unknown_count == 0
    assert result.submit_action == "NO_SUBMIT_ATTEMPTED"
    assert adapter.submit_calls == 0
    assert adapter.preflight_item_ids == [MISSING_SELL_ITEM_ID]
    assert by_symbol["76920"].review_required is True
    assert by_symbol["76920"].submitted is False
    assert by_symbol["34940"].preflight_status == "NOT_EXECUTABLE"
    assert by_symbol["34940"].submitted is False
    assert by_symbol["34940"].accepted is False
    assert by_symbol["34940"].guard_evidence["adapter_submit_called"] is False
    assert by_symbol["34940"].guard_evidence["order_created"] is False
    assert by_symbol["34940"].guard_evidence["broker_side_effect_created"] is False
    assert by_symbol["34940"].guard_evidence["ledger_order_created"] is False
    assert by_symbol["34940"].guard_evidence["position_mutated"] is False
    assert by_symbol["34940"].guard_evidence["cash_mutated"] is False
    assert by_symbol["34940"].guard_evidence["retry_eligible_same_day"] is False
    assert pending["state"] == "REVIEW_REQUIRED"
    assert pending["consume"]["consumed"] is False
    assert pending["consume"]["submitted_order_ids"] == []
    assert pending["consume"]["ledger_order_record_ids"] == []
    assert _item_state(pending, REVIEW_BUY_ITEM_ID) == "REVIEW_REQUIRED"
    assert _item_state(pending, MISSING_SELL_ITEM_ID) == "NOT_EXECUTABLE"
    terminal_item = next(item for item in pending["items"] if item["pending_item_id"] == MISSING_SELL_ITEM_ID)
    assert terminal_item["approved"] is False
    assert terminal_item["feasibility_status"] == "NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE"
    assert terminal_item["item_review_reason"] == "EXECUTION_AUTHORITY_UNAVAILABLE"
    assert MISSING_SELL_ITEM_ID not in pending["approved_item_ids"]
    assert MISSING_SELL_ITEM_ID not in pending["approved_sell_item_ids"]
    assert orders == []
    assert (runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8") == state_before
    assert (runtime_root / "persistent_ledger" / "cash.jsonl").read_text(encoding="utf-8") == cash_before
    assert (runtime_root / "persistent_ledger" / "executions.jsonl").read_text(encoding="utf-8") == executions_before
    assert aggregate["status"] == "PASS"
    assert aggregate["authority_type"] == "SUBMIT_AGGREGATE_TERMINAL_NOOP_CONTINUATION"
    assert aggregate["classification_authority"] == "SubmitItemResult + PendingReviewScopeAuthority"
    assert aggregate["counts"]["submitted_or_reconciled"] == 0
    assert aggregate["counts"]["terminal_not_executable"] == 1
    assert aggregate["counts"]["deferred_item_scoped_review"] == 1
    assert aggregate["zero_submission_safe_terminal_pass_supported"] is True
    assert aggregate["fake_submission_created"] is False
    assert aggregate["fake_execution_created"] is False
    assert aggregate["fake_cash_mutation"] is False
    assert aggregate["fake_position_mutation"] is False
    assert aggregate["same_day_retry_prevented_for_terminal_items"] is True

    retry_adapter = F1Y34940PreflightHaltAdapter()
    retry = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=retry_adapter,
        capital_deployment_policy_path=runtime_root / "runtime_state" / "policy" / "capital_deployment.json",
    )

    assert retry.status == "PASS"
    assert retry.reason == "BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION_REQUIRED"
    assert retry.submitted_count == 0
    assert retry_adapter.preflight_item_ids == []
    assert retry_adapter.submit_calls == 0
    assert _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl") == []


def test_phase31_f1y_side_effect_identity_mismatch_does_not_reconcile(tmp_path):
    runtime_root = _build_f1w_fixture(tmp_path)
    orders_path = runtime_root / "persistent_ledger" / "orders.jsonl"
    orders = _read_jsonl(orders_path)
    for order in orders:
        if order["pending_item_id"] == "strategy-8f700934de4464ffa4d5":
            order["quantity"] = 200.0
    orders_path.write_text("".join(json.dumps(order, sort_keys=True) + "\n" for order in orders), encoding="utf-8")

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=F1Y34940PreflightHaltAdapter(),
        capital_deployment_policy_path=runtime_root / "runtime_state" / "policy" / "capital_deployment.json",
    )
    item = next(item for item in result.item_results if item.symbol == "82560")

    assert item.preflight_status == "BLOCKED"
    assert item.reason == "sell quantity exceeds broker available quantity"
    assert item.guard_evidence.get("idempotency_status", "") == ""


def test_phase31_f1z2_ambiguous_execution_authority_still_fail_closed(tmp_path):
    runtime_root = _build_f1w_fixture(tmp_path)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=F1Z2Ambiguous34940PreflightHaltAdapter(),
        capital_deployment_policy_path=runtime_root / "runtime_state" / "policy" / "capital_deployment.json",
    )
    pending = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    by_symbol = {item.symbol: item for item in result.item_results}

    assert result.status == "REVIEW_REQUIRED"
    assert result.blocked_count == 1
    assert by_symbol["34940"].preflight_status == "HALT"
    assert by_symbol["34940"].blocked is True
    assert by_symbol["34940"].reason == "conflicting execution authorities for target session"
    assert _item_state(pending, MISSING_SELL_ITEM_ID) == "APPROVED"


class F1Y34940PreflightHaltAdapter(RuntimeV2SubmitSimulationAdapter):
    preflight_item_ids: list[str]

    def __init__(self) -> None:
        super().__init__(scenario="SIMULATED_ACCEPTED")
        self.preflight_item_ids = []

    def preflight(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        self.preflight_item_ids.append(command.pending_item_id)
        if command.pending_item_id == MISSING_SELL_ITEM_ID:
            return RuntimeV2SubmitResult(
                status="HALT",
                submitted=False,
                accepted=False,
                blocked=True,
                review_required=False,
                broker_api_called=False,
                reason="missing or non-unique target session OHLCV row",
                response_classification={
                    "status": "HALT",
                    "reason": "missing or non-unique target session OHLCV row",
                    "simulation": True,
                    "broker_write": False,
                },
                configuration_diagnostic={"adapter": "F1Y34940PreflightHaltAdapter"},
                next_action="fix_historical_submit_preflight_input",
            )
        return super().preflight(command)


class F1Z2Ambiguous34940PreflightHaltAdapter(RuntimeV2SubmitSimulationAdapter):
    def __init__(self) -> None:
        super().__init__(scenario="SIMULATED_ACCEPTED")

    def preflight(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        if command.pending_item_id == MISSING_SELL_ITEM_ID:
            return RuntimeV2SubmitResult(
                status="HALT",
                submitted=False,
                accepted=False,
                blocked=True,
                review_required=False,
                broker_api_called=False,
                reason="conflicting execution authorities for target session",
                response_classification={
                    "status": "HALT",
                    "reason": "conflicting execution authorities for target session",
                    "simulation": True,
                    "broker_write": False,
                },
                configuration_diagnostic={"adapter": "F1Z2Ambiguous34940PreflightHaltAdapter"},
                next_action="manual_review_required",
            )
        return super().preflight(command)


def _build_f1w_fixture(tmp_path: Path) -> Path:
    runtime_root = tmp_path / ".runtime"
    _init_dirs(runtime_root)
    policy_path = runtime_root / "runtime_state" / "policy" / "capital_deployment.json"
    _write_policy(policy_path)
    policy = load_capital_deployment_policy(policy_path)
    policy_hash = capital_deployment_policy_hash(policy)
    _write_safety(runtime_root)
    _write_current(runtime_root)
    _write_broker_snapshot(runtime_root)

    binding = _accepted_generation_binding()
    items = tuple(_item_with_policy(item, policy, policy_hash, binding) for item in _items())
    pending = promote_order_plan_to_pending(
        order_plan_id="order-plan-phase31-f1w",
        source_order_plan_path="runtime_state/order_plan/2022-12-08/order-plan-phase31-f1w.json",
        source_order_plan_hash="sha256:phase31-f1w-order-plan",
        environment="demo",
        plan_created_date=BUSINESS_DATE,
        intended_submit_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        items=items,
    )
    pending = replace(
        pending,
        pending_plan_id=PENDING_PLAN_ID,
        accepted_generation_id=binding["accepted_generation_id"],
        accepted_generation_business_date=BUSINESS_DATE,
        accepted_generation_binding_status="PASS",
        accepted_generation_binding=binding,
    )
    approval = ApprovalArtifact(
        approval_id="approval-4fcbbbe595a97ca9",
        approval_request_id="approval-request-phase31-f1w",
        pending_plan_id=pending.pending_plan_id,
        order_plan_id=pending.source_order_plan.order_plan_id,
        status=ApprovalStatus.APPROVED,
        approved_item_ids=tuple(item.pending_item_id for item in pending.items if item.approved),
        rejected_item_ids=(),
        approval_hash="sha256:phase31-f1w-approval",
        approved_at=BUSINESS_DATE + "T08:45:00+09:00",
        expires_at=BUSINESS_DATE + "T15:00:00+09:00",
        review_required=False,
        reason="phase31 f1w fixture approval",
        policy_version=pending.policy_version,
        policy_source=pending.policy_source,
        pending_policy_hash=pending.pending_policy_hash,
        submit_policy_version=pending.submit_policy_version,
        submit_policy_source=pending.submit_policy_source,
        submit_policy_hash=pending.submit_policy_hash,
        approved_order_conditions=_order_conditions(pending.items),
    )
    pending = link_approval_to_pending(pending_plan=pending, approval_artifact=approval)
    pending = replace(
        pending,
        state=PendingPlanState.REVIEW_REQUIRED,
        approved_item_ids=tuple(item.pending_item_id for item in pending.items if item.approved),
        approved_buy_item_ids=tuple(item.pending_item_id for item in pending.items if item.approved and item.side == "BUY"),
        approved_sell_item_ids=tuple(item.pending_item_id for item in pending.items if item.approved and item.side == "SELL"),
        review_required_buy_item_ids=(REVIEW_BUY_ITEM_ID,),
        review_required_sell_item_ids=(),
        review_scope="BUY_ITEM_SCOPED_REVIEW",
        review_scope_source="phase31_f1w_fixture",
        review_scope_reason="corporate_action_event_not_resolved",
        sell_continuation_allowed=True,
        items=tuple(
            replace(item, state="REVIEW_REQUIRED", approved=False)
            if item.pending_item_id == REVIEW_BUY_ITEM_ID
            else item
            for item in pending.items
        ),
    )
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)
    _write_existing_orders(runtime_root)
    return runtime_root


def _reduce_fixture_to_reviewed_buy_and_missing_sell(runtime_root: Path) -> None:
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    pending = _read_json(pending_path)
    kept_ids = {REVIEW_BUY_ITEM_ID, MISSING_SELL_ITEM_ID}
    pending["items"] = [item for item in pending["items"] if item["pending_item_id"] in kept_ids]
    pending["approved_item_ids"] = [MISSING_SELL_ITEM_ID]
    pending["approved_buy_item_ids"] = []
    pending["approved_sell_item_ids"] = [MISSING_SELL_ITEM_ID]
    pending["review_required_buy_item_ids"] = [REVIEW_BUY_ITEM_ID]
    pending["review_required_sell_item_ids"] = []
    pending["approval"]["approved_item_ids"] = [MISSING_SELL_ITEM_ID]
    pending["approval"]["approved_order_conditions"] = {
        item_id: condition
        for item_id, condition in pending["approval"]["approved_order_conditions"].items()
        if item_id == MISSING_SELL_ITEM_ID
    }
    _write_json(pending_path, pending)
    (runtime_root / "persistent_ledger" / "orders.jsonl").write_text("", encoding="utf-8")


def _items() -> tuple[PendingOrderItem, ...]:
    return (
        _item("strategy-9242cb1dda97a6433677", "61440", "BUY", 100, 1000),
        _item(REVIEW_BUY_ITEM_ID, "76920", "BUY", 200, 1000, approved=False, state="REVIEW_REQUIRED"),
        _item(MISSING_SELL_ITEM_ID, "34940", "SELL", 100, 1000),
        _item("strategy-8f700934de4464ffa4d5", "82560", "SELL", 300, 1000),
        _item("strategy-d869e35933dcd6215538", "37790", "SELL", 100, 1000),
        _item("strategy-72c08989f99bb27f815a", "45910", "SELL", 100, 1000),
    )


def _item(
    pending_item_id: str,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    *,
    approved: bool = True,
    state: str = "APPROVED",
) -> PendingOrderItem:
    return PendingOrderItem(
        pending_item_id=pending_item_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        order_type="MARKET",
        estimated_price=price,
        estimated_amount=quantity * price,
        approved=approved,
        state=state,
        feasibility_status="PASS" if approved else "REVIEW_REQUIRED",
        batch_submit_status="PASS_ITEM_SUBMITTABLE" if approved else "ITEM_REVIEW_REQUIRED",
        item_review_reason="" if approved else "corporate_action_event_not_resolved",
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
            "opportunity_business_date": BUSINESS_DATE,
            "opportunity_feature_date": BUSINESS_DATE,
            "opportunity_eligibility_policy_version": "runtime_v2_opportunity_buy_eligibility_v1",
            "opportunity_eligibility_reason": "opportunity_positive_expected_edge",
        },
    )


def _item_with_policy(item: PendingOrderItem, policy, policy_hash: str, binding: dict) -> PendingOrderItem:
    is_buy = item.side == "BUY"
    return replace(
        item,
        capital_allocation_amount=item.estimated_amount,
        policy_version=policy.policy_version,
        policy_source=policy.policy_source,
        planning_authority_version="phase31_f1w_fixture_planning",
        planning_authority_source=item.pending_item_id,
        planning_authority_hash="sha256:phase31-f1w-planning",
        submit_policy_version=policy.policy_version,
        submit_policy_source=policy.policy_source,
        submit_policy_hash=policy_hash,
        evaluation_capital=policy.evaluation_capital,
        max_positions=policy.max_positions,
        max_buy_order_amount=policy.max_buy_order_amount,
        max_sell_liquidation_amount=policy.max_sell_liquidation_amount,
        min_order_amount=policy.min_order_amount,
        buy_notional_policy=policy.buy_notional_policy,
        sell_liquidation_policy=policy.sell_liquidation_policy,
        manual_review_threshold={"buy_amount": None, "sell_liquidation_amount": None},
        accepted_generation_id=binding["accepted_generation_id"] if is_buy else "",
        accepted_generation_business_date=BUSINESS_DATE if is_buy else "",
        accepted_generation_binding_status="PASS" if is_buy else "NOT_REQUIRED",
        accepted_generation_binding=binding if is_buy else None,
        quantity_contract={
            "position_count_authority": {"selected_dynamic_position_count": 20, "target_position_count": 20, "safety_hard_maximum": 20},
            "cash_exposure_authority": {"selected_dynamic_cash_ratio": 0.05, "selected_dynamic_exposure_ratio": 0.85},
            "position_sizing_authority": {
                "positions": [
                    {
                        "symbol": item.symbol,
                        "target_weight": 0.10,
                        "target_notional": item.estimated_amount,
                        "incremental_buy_notional": item.estimated_amount if is_buy else 0.0,
                        "maximum_position_weight": 1.0,
                    }
                ],
                "effective_maximum_position_weight": 1.0,
            },
        },
        sizing_policy_reason="phase31 f1w fixture policy evidence",
        safety_decision_id="safety-phase31-f1w",
        safety_policy_version="safety_policy_v1",
        safety_source="phase31_f1w_fixture",
        safety_decision="ALLOW",
        safety_reason="phase31 f1w fixture",
        source_decision_type="BUY" if is_buy else "SELL_EXIT",
    )


def _order_conditions(items: tuple[PendingOrderItem, ...]) -> dict:
    return {
        item.pending_item_id: {
            "order_type": item.order_type,
            "price_condition": "MARKET",
            "limit_price": None,
            "target_session": BUSINESS_DATE,
            "time_in_force": "DAY",
            "quantity": item.quantity,
            "side": item.side,
            "issue_code": item.symbol,
            "broker_issue_code": item.symbol,
        }
        for item in items
        if item.approved
    }


def _write_existing_orders(runtime_root: Path) -> None:
    rows = [
        _ledger_row("existing-61440", "strategy-9242cb1dda97a6433677", "61440", "BUY", 100),
        _ledger_row("existing-82560", "strategy-8f700934de4464ffa4d5", "82560", "SELL", 300),
        _ledger_row("existing-37790", "strategy-d869e35933dcd6215538", "37790", "SELL", 100),
        _ledger_row("existing-45910", "strategy-72c08989f99bb27f815a", "45910", "SELL", 100),
    ]
    (runtime_root / "persistent_ledger" / "orders.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _ledger_row(seed: str, pending_item_id: str, symbol: str, side: str, quantity: float) -> dict:
    record_id = "ledger-order-submit-" + _short_hash(seed)
    return {
        "record_id": record_id,
        "ledger_record_id": record_id,
        "record_type": "order",
        "schema_version": "1",
        "environment": "demo",
        "source": "runtime_v2_submit_pipeline",
        "created_at": BUSINESS_DATE + "T09:00:00+09:00",
        "dedup_key": "runtime_v2_submit:" + seed,
        "review_required": False,
        "production_equivalent": False,
        "order_id": "sha256:" + _hash(seed),
        "business_date": BUSINESS_DATE,
        "pending_plan_id": PENDING_PLAN_ID,
        "pending_item_id": pending_item_id,
        "side": side,
        "symbol": symbol,
        "quantity": quantity,
        "status": "ACCEPTED",
    }


def _write_policy(path: Path) -> None:
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "max_positions": 20,
            "min_order_amount": 0,
            "max_buy_order_amount": None,
            "max_sell_liquidation_amount": None,
            "buy_notional_policy": "derived_from_capital_allocation_and_constraints",
            "sell_liquidation_policy": "current_owned_available_quantity_policy",
            "allowed_order_types": ["MARKET"],
            "allowed_time_in_force": ["DAY"],
            "manual_review_threshold": {"buy_amount": None, "sell_liquidation_amount": None},
        },
    )


def _write_safety(runtime_root: Path) -> None:
    _write_json(
        runtime_root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": "safety-phase31-f1w",
            "safety_policy_version": "safety_policy_v1",
            "safety_source": "phase31_f1w_fixture",
            "business_date": BUSINESS_DATE,
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase31 f1w fixture",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": BUSINESS_DATE + "T08:00:00+09:00",
            "expires_at": BUSINESS_DATE + "T15:00:00+09:00",
            "freshness_status": "READY",
            "action_permissions": {"buy_submit": "ALLOWED", "sell_submit": "ALLOWED", "broker_write": "ALLOWED_FOR_ACCEPTANCE"},
        },
    )


def _write_current(runtime_root: Path) -> None:
    positions = [
        {"symbol": symbol, "quantity": quantity, "average_price": 1000.0, "market_value": quantity * 1000.0, "source": "fixture", "as_of": BUSINESS_DATE}
        for symbol, quantity in (("34940", 100), ("82560", 300), ("37790", 100), ("45910", 100))
    ]
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase31-f1w",
            "environment": "demo",
            "source": "phase31_f1w_fixture",
            "as_of": BUSINESS_DATE,
            "position_state_as_of": BUSINESS_DATE,
            "valuation_as_of": BUSINESS_DATE,
            "current_position_status": "READY",
            "current_valuation_status": "READY",
            "positions": positions,
            "cash": 1_000_000.0,
            "buying_power": 1_000_000.0,
            "market_value": sum(position["market_value"] for position in positions),
            "total_equity": 1_600_000.0,
            "review_required": False,
            "current_state_confirmed_empty": False,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
        },
    )


def _write_broker_snapshot(runtime_root: Path) -> None:
    records = [
        {
            "environment": "demo",
            "source": "broker_readonly",
            "as_of": BUSINESS_DATE + "T08:30:00+09:00",
            "account_type": "cash",
            "issue_code": symbol[:4],
            "symbol": symbol,
            "quantity": quantity,
            "available_quantity": quantity if symbol == "34940" else 0,
            "review_required": False,
            "production_equivalent": True,
        }
        for symbol, quantity in (("34940", 100), ("82560", 300), ("37790", 100), ("45910", 100))
    ]
    _write_json(
        runtime_root / "broker" / "snapshots" / "positions" / "positions-phase31-f1w.json",
        {"kind": "positions", "source": "broker_readonly", "as_of": BUSINESS_DATE + "T08:30:00+09:00", "review_required": False, "production_equivalent": True, "records": records},
    )


def _accepted_generation_binding() -> dict:
    return {
        "schema_version": "phase31_f1w_accepted_generation_binding.v1",
        "consumer": "phase31_f1w_fixture",
        "mode": "demo",
        "requested_business_date": BUSINESS_DATE,
        "selected_business_date": BUSINESS_DATE,
        "accepted_generation_id": "phase31-f1w-generation",
        "accepted_generation_business_date": BUSINESS_DATE,
        "generation_binding_status": "PASS",
        "temporal_binding_status": "PASS",
        "latest_fallback_used": False,
        "shared_state_fallback_used": False,
        "default_generation_used": False,
        "legacy_component_fallback_used": False,
        "promotion_candidate_fallback_used": False,
        "manual_model_path_used": False,
    }


def _init_dirs(runtime_root: Path) -> None:
    for path in (
        runtime_root / "pending_order_plan",
        runtime_root / "runtime_state" / "policy",
        runtime_root / "runtime_state" / "safety",
        runtime_root / "broker" / "snapshots" / "positions",
        runtime_root / "persistent_ledger",
    ):
        path.mkdir(parents=True, exist_ok=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (runtime_root / "persistent_ledger" / f"{name}.jsonl").write_text("", encoding="utf-8")


def _item_state(pending: dict, pending_item_id: str) -> str:
    return next(item["state"] for item in pending["items"] if item["pending_item_id"] == pending_item_id)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _short_hash(value: str) -> str:
    return _hash(value)[:16]
