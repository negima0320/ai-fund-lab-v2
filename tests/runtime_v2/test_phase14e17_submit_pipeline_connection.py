import json
from datetime import datetime
from dataclasses import replace
from pathlib import Path
from typing import Optional

from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.runtime_v2.cli import run_daily_operation
from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import get_broker_capability, is_symbol_allowed_by_capability
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    capital_deployment_policy_hash,
    load_capital_deployment_policy,
)
from ai_fund_lab_v2.runtime_v2.submit.pipeline import SubmitItemResult, SubmitPipelineResult, run_submit_pipeline


def test_phase14e17_submit_pipeline_submits_all_approved_pending_items(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    pending = _approved_pending(("65220", "78780", "68970", "63270", "45910"), policy_path=policy_path)
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    updated = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    orders = _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl")

    assert result.status == "PASS"
    assert result.demo_submit_executed is True
    assert result.submitted_count == 5
    assert result.accepted_count == 5
    assert result.rejected_count == 0
    assert result.unknown_count == 0
    assert result.blocked_count == 0
    assert result.submitted_symbols == ("65220", "78780", "68970", "63270", "45910")
    assert len(result.submitted_order_ids) == 5
    assert len(result.ledger_order_record_ids) == 5
    assert updated["state"] == "CONSUMED"
    assert updated["consume"]["consumed"] is True
    assert len(updated["consume"]["submitted_order_ids"]) == 5
    assert len(orders) == 5
    assert {order["source"] for order in orders} == {"runtime_v2_submit_pipeline"}
    assert all(order["raw_request_saved"] is False for order in (updated,))


def test_phase16d_submit_pipeline_uses_explicit_now_for_pending_and_ledger_timestamps(tmp_path):
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    evaluation_time = datetime.fromisoformat("2026-07-08T09:00:00+09:00")

    first = _run_single_submit(tmp_path / "run-1", policy_path=policy_path, evaluation_time=evaluation_time)
    second = _run_single_submit(tmp_path / "run-2", policy_path=policy_path, evaluation_time=evaluation_time)

    expected = "2026-07-08T00:00:00+00:00"
    assert first["pending"]["updated_at"] == expected
    assert second["pending"]["updated_at"] == expected
    assert first["orders"][0]["created_at"] == expected
    assert first["orders"][0]["recorded_at"] == expected
    assert second["orders"][0]["created_at"] == expected
    assert second["orders"][0]["recorded_at"] == expected
    assert first["orders"] == second["orders"]
    assert first["result"].submitted_count == 1
    assert first["result"].pending_consumed is True


def test_phase16d_submit_pipeline_default_now_preserves_normal_operation_timestamp(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    pending = _approved_pending(("65220",), policy_path=policy_path)
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    updated = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    orders = _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl")

    assert result.status == "PASS"
    assert updated["updated_at"].endswith("+00:00")
    assert orders[0]["created_at"].endswith("+00:00")
    assert orders[0]["recorded_at"] == orders[0]["created_at"]


def test_phase14e17_submit_pipeline_blocks_demo_9000_series_before_submit(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    pending = _approved_pending(("9432",), policy_path=policy_path)
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
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

    assert result.status == "BLOCKED"
    assert result.demo_submit_executed is False
    assert result.submitted_count == 0
    assert result.blocked_count == 1
    assert result.item_results[0].reason == "symbol not supported by broker capability"
    assert orders == []


def test_phase14e17_production_capability_does_not_block_9000_series():
    production = get_broker_capability("production")
    demo = get_broker_capability("demo")

    assert is_symbol_allowed_by_capability("9432", production) is True
    assert is_symbol_allowed_by_capability("9432", demo) is False


def test_phase14e17_cli_submit_job_records_submit_pipeline_stage(monkeypatch, tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    write_pending_order_plan(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        _approved_pending(("7203",), policy_path=policy_path),
    )
    _attach_pending_safety_evidence(runtime_root, safety_decision_id="safety-phase14e17-fixture")
    _write_runtime_readiness_authorities(runtime_root, business_date="2026-07-08")
    captured = {}

    def fake_submit_pipeline(**kwargs):
        captured.update(kwargs)
        return SubmitPipelineResult(
            status="PASS",
            reason="submitted",
            pending_plan_id="pending-test",
            pending_path=str(runtime_root / "pending_order_plan" / "pending_order_plan.json"),
            orders_ledger_path=str(runtime_root / "persistent_ledger" / "orders.jsonl"),
            demo_submit_executed=True,
            submitted_count=1,
            accepted_count=1,
            rejected_count=0,
            unknown_count=0,
            blocked_count=0,
            pending_consumed=True,
            submitted_order_ids=("sha256:order",),
            ledger_order_record_ids=("ledger-order-1",),
            submitted_symbols=("7203",),
            item_results=(
                SubmitItemResult(
                    pending_item_id="item-1",
                    symbol="7203",
                    side="BUY",
                    quantity=100,
                    preflight_status="PASS",
                    submit_status="ACCEPTED",
                    submitted=True,
                    accepted=True,
                    rejected=False,
                    unknown=False,
                    blocked=False,
                    review_required=False,
                    broker_order_id_hash="sha256:order",
                    ledger_order_record_id="ledger-order-1",
                    reason="fake",
                    issue_code_normalization={"original_symbol": "7203", "broker_issue_code": "7203"},
                    response_classification={"business_classification": "ACCEPTED"},
                    configuration_diagnostic={},
                    next_action="",
                ),
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
            "2026-07-08",
            "--evaluation-time",
            "2026-07-08T09:00:00+09:00",
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
            str(tmp_path / ".runtime" / "runtime_state" / "run_manifest"),
            "--log-root",
            str(tmp_path / ".runtime" / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
        ]
    )
    manifest = json.loads(
        next((tmp_path / ".runtime" / "runtime_state" / "run_manifest" / "2026-07-08").glob("*.json")).read_text(
            encoding="utf-8"
        )
    )
    submit_stage = next(stage for stage in manifest["stages"] if stage["name"] == "runtime_v2_submit_pipeline")

    assert exit_code == 0
    assert captured["now"].isoformat() == "2026-07-08T00:00:00+00:00"
    assert submit_stage["status"] == "PASS"
    assert submit_stage["details"]["submitted_count"] == 1
    assert manifest["prohibited_actions"]["demo_submit_executed"] is True


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "pending_order_plan").mkdir(parents=True)
    ledger = root / "persistent_ledger"
    ledger.mkdir(parents=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (ledger / f"{name}.jsonl").write_text("", encoding="utf-8")
    _write_safety_decision(root)
    return root


def _write_asset_state(root: Path) -> None:
    payload = {
        "schema_version": "1",
        "asset_state_id": "asset-e17",
        "environment": "demo",
        "source": "phase14e8_demo_operation_initial_state",
        "as_of": "2026-07-08",
        "positions": [],
        "cash": 1_000_000.0,
        "buying_power": 1_000_000.0,
        "market_value": 0,
        "total_equity": 1_000_000.0,
        "review_required": False,
        "production_equivalent": False,
        "current_state_confirmed_empty": True,
        "current_positions_unknown": False,
        "cash_unknown": False,
        "buying_power_unknown": False,
        "generated_from": ["fixture"],
        "created_at": "2026-07-08",
        "updated_at": "2026-07-08",
    }
    (root / "persistent_ledger" / "state.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


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
            "source": "phase14e17_cli_fixture",
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


def _approved_pending(symbols: tuple[str, ...], *, policy_path: Optional[Path] = None):
    items = tuple(
        PendingOrderItem(
            pending_item_id=f"item-{index}",
            symbol=symbol,
            side="BUY",
            quantity=100.0,
            order_type="MARKET",
            estimated_price=1000.0,
            estimated_amount=100000.0,
            approved=False,
            state="CREATED",
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
                "opportunity_buy_rank": index,
                "opportunity_business_date": "2026-07-08",
                "opportunity_feature_date": "2026-07-08",
                "opportunity_eligibility_policy_version": "runtime_v2_opportunity_buy_eligibility_v1",
                "opportunity_eligibility_reason": "opportunity_positive_expected_edge",
            },
        )
        for index, symbol in enumerate(symbols, start=1)
    )
    if policy_path is not None:
        policy = load_capital_deployment_policy(policy_path)
        items = tuple(_item_with_policy(item, policy) for item in items)
    pending = promote_order_plan_to_pending(
        order_plan_id="order-plan-e17",
        source_order_plan_path=".runtime/runtime_state/morning_pipeline/2026-07-08/order_plan.json",
        source_order_plan_hash="sha256:order-plan-e17",
        environment="demo",
        plan_created_date="2026-07-08",
        intended_submit_date="2026-07-08",
        target_session_date="2026-07-08",
        items=items,
    )
    approval = ApprovalArtifact(
        approval_id="approval-e17",
        approval_request_id="approval-request-e17",
        pending_plan_id=pending.pending_plan_id,
        order_plan_id=pending.source_order_plan.order_plan_id,
        status=ApprovalStatus.APPROVED,
        approved_item_ids=tuple(item.pending_item_id for item in pending.items),
        rejected_item_ids=(),
        approval_hash="sha256:approval-e17",
        approved_at="2026-07-08T08:45:00+09:00",
        expires_at="2026-07-08T15:00:00+09:00",
        review_required=False,
        reason="test approval",
        policy_version=pending.policy_version,
        policy_source=pending.policy_source,
        pending_policy_hash=pending.pending_policy_hash,
        approved_order_conditions={
            item.pending_item_id: {
                "order_type": item.order_type,
                "target_session": pending.target_session_date,
                "quantity": item.quantity,
                "side": item.side,
                "issue_code": item.symbol,
                "limit_price": None,
                "time_in_force": "DAY",
                "price_condition": item.order_type,
            }
            for item in pending.items
        },
    )
    return link_approval_to_pending(pending_plan=pending, approval_artifact=approval)


def _item_with_policy(item: PendingOrderItem, policy) -> PendingOrderItem:
    quantity_contract = dict(item.quantity_contract or {})
    quantity_contract.update(_authority_quantity_contract(item, policy))
    binding = _accepted_generation_binding()
    is_buy = item.side.upper() == "BUY"
    return replace(
        item,
        capital_allocation_amount=item.estimated_amount,
        policy_version=policy.policy_version,
        policy_source=policy.policy_source,
        planning_authority_version="phase14e17_fixture_planning_authority",
        planning_authority_source=item.pending_item_id,
        planning_authority_hash="sha256:phase14e17-fixture-planning",
        submit_policy_version=policy.policy_version,
        submit_policy_source=policy.policy_source,
        submit_policy_hash=capital_deployment_policy_hash(policy),
        evaluation_capital=policy.evaluation_capital,
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
        accepted_generation_id=binding["accepted_generation_id"] if is_buy else "",
        accepted_generation_business_date=binding["accepted_generation_business_date"] if is_buy else "",
        accepted_generation_binding_status="PASS" if is_buy else "NOT_REQUIRED",
        accepted_generation_binding=binding if is_buy else None,
        quantity_contract=quantity_contract,
        sizing_policy_reason="phase14e17 fixture policy evidence",
    )


def _authority_quantity_contract(item: PendingOrderItem, policy) -> dict:
    return {
        "position_count_authority": {
            "selected_dynamic_position_count": policy.max_positions,
            "target_position_count": policy.max_positions,
            "safety_hard_maximum": policy.max_positions,
        },
        "cash_exposure_authority": {
            "selected_dynamic_cash_ratio": 0.05,
            "target_cash_ratio": 0.05,
            "selected_dynamic_exposure_ratio": 0.85,
            "target_gross_exposure_ratio": 0.85,
            "exposure_safety_maximum": 0.85,
        },
        "position_sizing_authority": {
            "positions": [
                {
                    "symbol": item.symbol,
                    "target_weight": 0.20,
                    "target_notional": item.estimated_amount,
                    "incremental_buy_notional": item.estimated_amount,
                    "maximum_position_weight": 1.0,
                }
            ],
            "effective_maximum_position_weight": 1.0,
        },
    }


def _accepted_generation_binding() -> dict:
    return {
        "schema_version": "phase26_step8_accepted_generation_binding.v1",
        "consumer": "phase14e17_submit_fixture",
        "mode": "demo",
        "requested_business_date": "2026-07-08",
        "selected_business_date": "2026-07-08",
        "accepted_generation_id": "phase14e17-fixture-generation",
        "accepted_generation_business_date": "2026-07-08",
        "generation_binding_status": "PASS",
        "temporal_binding_status": "PASS",
        "latest_fallback_used": False,
        "shared_state_fallback_used": False,
        "default_generation_used": False,
        "legacy_component_fallback_used": False,
        "promotion_candidate_fallback_used": False,
        "manual_model_path_used": False,
    }


def _demo_settings() -> BrokerSettings:
    return BrokerSettings(
        environment="demo",
        base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9",
        second_password_file="/tmp/phase14e17-second-password",
    )


def _run_single_submit(root_parent: Path, *, policy_path: Path, evaluation_time: datetime) -> dict:
    runtime_root = _runtime_root(root_parent)
    _write_asset_state(runtime_root)
    pending = _approved_pending(("65220",), policy_path=policy_path)
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
        now=evaluation_time,
    )

    return {
        "result": result,
        "pending": json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")),
        "orders": _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl"),
    }


def _write_policy(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
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
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def _write_safety_decision(root: Path) -> Path:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "safety_decision_id": "safety-phase14e17-fixture",
                "safety_policy_version": "safety_policy_v1",
                "safety_source": str(path),
                "business_date": "2026-07-08",
                "runtime_mode": "demo",
                "decision": "ALLOW",
                "reason": "phase14e17 fixture safety allow",
                "review_required": False,
                "block_buy": False,
                "block_sell": False,
                "block_submit": False,
                "halt_runtime": False,
                "emergency_stop": False,
                "generated_at": "2026-07-08T08:00:00+09:00",
                "expires_at": "2026-07-08T15:00:00+09:00",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
