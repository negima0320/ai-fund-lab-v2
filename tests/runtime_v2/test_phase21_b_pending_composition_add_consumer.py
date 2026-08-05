import json
import hashlib
from pathlib import Path

from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.planning.add_consumer import (
    LEGACY_ADD_MIGRATION_STATE,
    build_legacy_add_compatibility_artifact,
    evaluate_legacy_add_double_authority_guard,
    validate_legacy_add_compatibility_lineage,
)
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import SellExitDecision, run_sell_planning_pending_pipeline
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import capital_deployment_policy_hash, load_capital_deployment_policy
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
    assert pending["no_order_authority_status"] == "PASS"
    assert pending["no_order_authority"]["status"] == "NO_ORDER_AUTHORIZED"
    assert "sell_no_signal" in pending["no_order_authority"]["authority_reason_codes"]


def test_phase24_e1_mixed_empty_materializes_no_order_authority_and_submit_accepts(tmp_path):
    business_date = "2022-07-06"
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path, max_buy_order_amount=12_920)
    policy = load_capital_deployment_policy(policy_path)
    _write_current_state(
        runtime_root,
        positions=[_current_position("94320", quantity=1100, price=153.3, as_of=business_date)],
        as_of=business_date,
    )
    _write_strategy_no_order_authority(runtime_root, business_date=business_date)

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=business_date,
        mode="demo",
        exit_decisions=(
            SellExitDecision(
                symbol="94320",
                quantity=0,
                reason="add",
                source_decision="ADD",
                source_decision_id="pm-2022-07-06-94320-add",
            ),
        ),
        capital_deployment_policy=policy,
        submit_policy_context=_submit_policy_context(policy),
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=business_date,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "NO_SIGNAL"
    assert result.add_consumer_status == LEGACY_ADD_MIGRATION_STATE
    assert result.add_accepted_count == 0
    assert result.add_rejected_count == 0
    assert pending["state"] == "EMPTY"
    assert pending["items"] == []
    assert pending["no_order_authority_status"] == "PASS"
    reason_codes = pending["no_order_authority"]["authority_reason_codes"]
    assert "existing_position_capacity_satisfied" in reason_codes
    assert "sell_no_signal" in reason_codes
    assert "no_executable_order_items" in reason_codes
    assert pending["pm_add_consumer"]["decision_effect"] == "NONE"
    assert pending["pm_add_consumer"]["quantity_authority"] == "NONE"
    assert pending["pm_add_consumer"]["pending_authority"] == "NONE"
    assert pending["pm_add_consumer"]["approval_authority"] == "NONE"
    assert pending["pm_add_consumer"]["submit_authority"] == "NONE"
    assert pending["pm_add_consumer"]["telemetry_only"] is True
    assert submit.status == "PASS"
    assert submit.submitted_count == 0
    assert submit.no_order_authority_status == "PASS"
    assert submit.submit_action == "NO_ACTION"


def test_phase24_e1_empty_no_order_authority_business_date_mismatch_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])
    run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(),
    )
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    pending = _load_json(pending_path)
    pending["no_order_authority"]["business_date"] = "2026-07-07"
    _write_json(pending_path, pending)

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

    assert submit.status == "REVIEW_REQUIRED"
    assert submit.reason == "pending EMPTY no_order_authority business_date mismatch"


def test_phase24_e1_empty_no_order_authority_source_hash_mismatch_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])
    run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(),
    )
    order_plan_path = runtime_root / "runtime_state" / "sell_pipeline" / "2026-07-08" / "order_plan.json"
    order_plan = _load_json(order_plan_path)
    order_plan["reason"] = "tampered"
    _write_json(order_plan_path, order_plan)

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

    assert submit.status == "REVIEW_REQUIRED"
    assert submit.reason == "pending EMPTY no_order_authority source_artifact hash mismatch"


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


def test_phase21_b_pm_add_generates_compatibility_telemetry_only(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy = _policy(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("94320", quantity=1000, price=100)])

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(SellExitDecision(symbol="9432", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-1"),),
        capital_deployment_policy=policy,
        submit_policy_context=_submit_policy_context(policy),
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    order_plan_path = runtime_root / "runtime_state" / "sell_pipeline" / "2026-07-08" / "order_plan.json"
    order_plan = _load_json(order_plan_path)
    legacy_add_order_plan_path = runtime_root / "runtime_state" / "sell_pipeline" / "2026-07-08" / "pm_add_order_plan.json"

    assert result.status == "NO_SIGNAL"
    assert result.add_consumer_status == LEGACY_ADD_MIGRATION_STATE
    assert result.add_accepted_count == 0
    assert result.add_rejected_count == 0
    assert legacy_add_order_plan_path.exists() is False
    assert pending["state"] == "EMPTY"
    assert pending["items"] == []
    assert pending.get("approval_status", "") in {"", "NO_SIGNAL"}
    evidence = pending["pm_add_consumer"]
    assert evidence["requested_count"] == 1
    assert evidence["accepted_count"] == 0
    assert evidence["accepted_pending_item_ids"] == []
    assert evidence["migration_state"] == LEGACY_ADD_MIGRATION_STATE
    assert evidence["decision_effect"] == "NONE"
    assert evidence["quantity_authority"] == "NONE"
    assert evidence["pending_authority"] == "NONE"
    assert evidence["approval_authority"] == "NONE"
    assert evidence["submit_authority"] == "NONE"
    assert evidence["telemetry_only"] is True
    assert evidence["compatibility"][0]["source_pm_decision_id"] == "pm-add-1"
    assert evidence["compatibility"][0]["legacy_path_would_have_been_invoked"] is True
    assert order_plan["pm_add_consumer"]["compatibility_count"] == 1
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
    assert result.add_consumer_status == LEGACY_ADD_MIGRATION_STATE
    assert result.add_accepted_count == 0
    assert result.add_rejected_count == 0


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


def test_phase27_d2c_legacy_add_duplicate_dedup_key_blocks():
    decision = SellExitDecision(symbol="94320", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-1")
    artifact = build_legacy_add_compatibility_artifact(
        add_decisions=(decision, decision),
        business_date="2026-07-08",
        target_session_date="2026-07-08",
        environment="demo",
        run_id="run-1",
    )

    assert artifact["review_status"] == "REVIEW_REQUIRED"
    assert artifact["double_authority_guard"]["status"] == "BLOCKED"
    assert artifact["double_authority_guard"]["fail_open_allowed"] is False


def test_phase27_d2c_legacy_add_non_decision_does_not_conflict_with_canonical_authority():
    decision = SellExitDecision(symbol="94320", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-1")
    artifact = build_legacy_add_compatibility_artifact(
        add_decisions=(decision,),
        business_date="2026-07-08",
        target_session_date="2026-07-08",
        environment="demo",
        run_id="run-1",
    )
    canonical = {
        "run_id": "run-1",
        "business_date": "2026-07-08",
        "symbol": "94320",
        "position_campaign_id": "UNKNOWN",
        "decision_id": "pm-add-1",
        "decision_effect": "BUY_ADD",
        "quantity_authority": "POSITION_SIZING",
        "pending_authority": "RUNTIME_PLANNING",
    }

    guard = evaluate_legacy_add_double_authority_guard(artifact, canonical_authority_records=(canonical,))

    assert guard["status"] == "PASS"
    assert guard["canonical_legacy_authority_overlaps"] == []


def test_phase27_d2c_legacy_add_executable_overlap_blocks():
    decision = SellExitDecision(symbol="94320", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-1")
    artifact = build_legacy_add_compatibility_artifact(
        add_decisions=(decision,),
        business_date="2026-07-08",
        target_session_date="2026-07-08",
        environment="demo",
        run_id="run-1",
    )
    artifact["compatibility"][0]["decision_effect"] = "BUY_ADD"
    artifact["compatibility"][0]["quantity_authority"] = "LEGACY_ADD_CONSUMER"
    canonical = {
        "run_id": "run-1",
        "business_date": "2026-07-08",
        "symbol": "94320",
        "position_campaign_id": "UNKNOWN",
        "decision_id": "pm-add-1",
        "decision_effect": "BUY_ADD",
        "quantity_authority": "POSITION_SIZING",
        "pending_authority": "RUNTIME_PLANNING",
    }

    guard = evaluate_legacy_add_double_authority_guard(artifact, canonical_authority_records=(canonical,))

    assert guard["status"] == "BLOCKED"
    assert guard["conflict_behavior"] == "BLOCKED"
    assert guard["fail_open_allowed"] is False


def test_phase27_d2c_legacy_add_lineage_mismatches_require_review():
    decision = SellExitDecision(symbol="94320", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-1")
    artifact = build_legacy_add_compatibility_artifact(
        add_decisions=(decision,),
        business_date="2026-07-08",
        target_session_date="2026-07-08",
        environment="demo",
        run_id="run-1",
        accepted_generation="generation-a",
    )

    validation = validate_legacy_add_compatibility_lineage(
        artifact,
        expected_business_date="2026-07-09",
        expected_accepted_generation="generation-b",
        expected_campaign_by_symbol={"94320": "campaign-1"},
    )

    assert validation["status"] == "REVIEW_REQUIRED"
    assert validation["fail_open_allowed"] is False
    assert validation["reason_codes"] == [
        "ACCEPTED_GENERATION_MISMATCH",
        "BUSINESS_DATE_MISMATCH",
        "POSITION_CAMPAIGN_MISMATCH",
    ]
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


def _write_current_state(root: Path, *, positions, as_of: str = "2026-07-08"):
    market_value = sum(float(item["market_value"]) for item in positions)
    payload = {
        "schema_version": "1",
        "asset_state_id": "asset-phase21b",
        "environment": "demo",
        "source": "fixture",
        "as_of": as_of,
        "positions": positions,
        "cash": 1_000_000,
        "buying_power": 1_000_000,
        "market_value": market_value,
        "total_equity": 1_000_000 + market_value,
        "review_required": False,
        "production_equivalent": False,
        "current_state_confirmed_empty": False,
        "current_positions_unknown": False,
        "cash_unknown": False,
        "buying_power_unknown": False,
        "generated_from": ["fixture"],
        "created_at": as_of,
        "updated_at": as_of,
    }
    _write_json(root / "persistent_ledger" / "state.json", payload)
    _write_dynamic_cash_exposure(root, business_date=as_of, cash=1_000_000, market_value=market_value)
    _write_position_sizing(root, business_date=as_of, positions=positions, cash=1_000_000, market_value=market_value)


def _current_position(symbol: str, *, quantity: float, price: float, as_of: str = "2026-07-08") -> dict:
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": price,
        "market_value": quantity * price,
        "source": "fixture",
        "as_of": as_of,
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
        target_investment_ratio=None,
        cash_buffer=None,
        max_exposure=None,
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


def _policy_path(tmp_path: Path, *, max_buy_order_amount=None) -> Path:
    path = tmp_path / "capital_deployment_policy.json"
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "max_positions": 5,
            "min_order_amount": 0,
            "max_buy_order_amount": max_buy_order_amount,
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


def _write_position_sizing(root: Path, *, business_date: str, positions, cash: float, market_value: float) -> None:
    total_equity = cash + market_value
    rows = []
    for item in positions:
        current_notional = float(item["market_value"])
        target_weight = 0.18
        target_notional = round(total_equity * target_weight, 2)
        incremental = max(round(target_notional - current_notional, 2), 0.0)
        rows.append(
            {
                "security_code": str(item["symbol"]),
                "membership_intent": "KEEP",
                "pm_action": "ADD",
                "current_weight": round(current_notional / total_equity, 6) if total_equity else 0.0,
                "base_weight": target_weight,
                "quality_adjustment": 1.0,
                "volatility_adjustment": 1.0,
                "pm_intent_adjustment": 1.0,
                "adjusted_weight": target_weight,
                "capped_weight": target_weight,
                "target_weight": target_weight,
                "weight_delta": round(target_weight - (current_notional / total_equity if total_equity else 0.0), 6),
                "target_notional": target_notional,
                "current_notional": current_notional,
                "incremental_target_notional": incremental,
                "incremental_buy_notional": incremental,
                "minimum_meaningful_notional": 0.0,
                "maximum_position_weight": target_weight,
                "sizing_status": "SIZED",
                "confidence": 0.9,
                "uncertainty": "LOW",
                "reason_codes": ["fixture_position_sizing"],
                "target_weight_authority": {
                    "portfolio_policy_reference": {
                        "path": "fixture_portfolio_policy",
                    }
                },
            }
        )
    total_target_weight = round(sum(float(row["target_weight"]) for row in rows), 6)
    payload = {
        "schema_version": "position_sizing.v1",
        "business_date": business_date,
        "as_of": f"{business_date}T00:00:00+00:00",
        "feature_date": business_date,
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "PASS",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "target_gross_exposure_ratio": 0.80,
        "target_position_count": len(rows),
        "positions": rows,
        "positions_sized": len(rows),
        "positions_withheld": 0,
        "total_target_weight": total_target_weight,
        "residual_cash_ratio": round(max(1.0 - total_target_weight, 0.0), 6),
        "concrete_target_weight_decided": True,
        "target_notional_decided": True,
        "share_quantity_decided": False,
        "lot_rounding_decided": False,
        "order_price_decided": False,
        "pending_decided": False,
        "submit_decided": False,
        "strategy_maximum_position_weight": 0.18,
        "strategy_maximum_position_weight_source": "fixture#strategy_maximum_position_weight",
        "safety_maximum_position_weight": 0.25,
        "safety_maximum_position_weight_source": "fixture#safety_maximum_position_weight",
        "safety_authority_status": "PASS",
        "effective_maximum_position_weight": 0.18,
        "effective_maximum_position_weight_derivation": "min(strategy_maximum_position_weight, safety_maximum_position_weight)",
        "explicit_zero_cap": False,
        "emergency_brake_active": False,
        "market_context_risk_state": "NORMAL",
        "dynamic_position_count": len(rows),
        "dynamic_cash_exposure": 0.80,
        "aggregate_exposure_cap": 0.80,
        "source_artifacts": [{"role": "portfolio_policy", "path": "fixture_portfolio_policy", "required": True, "status": "PASS"}],
        "source_hashes": [{"role": "fixture", "path": "fixture", "sha256": "0" * 64}],
        "temporal_safety": {
            "point_in_time": True,
            "future_leakage_used": False,
            "feature_date_lte_business_date": True,
            "implicit_latest_fallback_used": False,
            "previous_day_position_sizing_copied": False,
        },
        "production_consumer_connected": False,
        "runtime_switch_performed": False,
    }
    _write_json(
        root / "strategy_artifacts" / "position_sizing" / business_date / "position_sizing.json",
        payload,
    )


def _write_dynamic_cash_exposure(root: Path, *, business_date: str, cash: float, market_value: float) -> None:
    total_equity = cash + market_value
    target_cash_ratio = 0.20
    target_exposure_ratio = 0.80
    payload = {
        "schema_version": "dynamic_cash_exposure.v1",
        "business_date": business_date,
        "as_of": f"{business_date}T00:00:00+00:00",
        "feature_date": business_date,
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "PASS",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "minimum_cash_ratio": 0.12,
        "target_cash_ratio": target_cash_ratio,
        "maximum_cash_ratio": 0.50,
        "minimum_gross_exposure_ratio": 0.40,
        "target_gross_exposure_ratio": target_exposure_ratio,
        "maximum_gross_exposure_ratio": 0.88,
        "portfolio_total_equity": total_equity,
        "current_cash": cash,
        "current_market_value": market_value,
        "pending_reserved_cash": 0.0,
        "net_available_cash": cash,
        "target_cash_amount": round(total_equity * target_cash_ratio, 2),
        "target_invested_ratio": target_exposure_ratio,
        "target_invested_notional": round(total_equity * target_exposure_ratio, 2),
        "current_invested_ratio": 0.0 if total_equity <= 0 else round(market_value / total_equity, 6),
        "incremental_deployment_capacity": max(round(total_equity * target_exposure_ratio - market_value, 2), 0.0),
        "strategy_fixed_jpy_exposure_cap_used": False,
        "legacy_max_exposure_authority_used": False,
        "current_cash_ratio": 0.0 if total_equity <= 0 else round(cash / total_equity, 6),
        "current_gross_exposure_ratio": 0.0 if total_equity <= 0 else round(market_value / total_equity, 6),
        "cash_posture": "DEPLOY",
        "exposure_posture": "INCREASE",
        "capital_constraint_status": "SUFFICIENT",
        "confidence": 0.9,
        "uncertainty": "LOW",
        "reason_codes": ["fixture_dynamic_cash_exposure"],
        "source_artifacts": [{"role": "fixture", "path": "fixture", "required": True, "status": "PASS"}],
        "source_hashes": [{"role": "fixture", "path": "fixture", "sha256": "0" * 64}],
        "temporal_safety": {
            "point_in_time": True,
            "future_leakage_used": False,
            "feature_date_lte_business_date": True,
            "implicit_latest_fallback_used": False,
            "previous_day_dynamic_cash_exposure_copied": False
        },
        "production_consumer_connected": False,
        "runtime_switch_performed": False,
        "position_sizing_decided": False,
        "allocation_decided": False,
        "quantity_decided": False,
        "lot_rounding_decided": False
    }
    _write_json(
        root / "strategy_artifacts" / "dynamic_cash_exposure" / business_date / "dynamic_cash_exposure.json",
        payload,
    )


def _submit_policy_context(policy) -> dict:
    return {
        "submit_policy_authority": "capital_deployment_policy",
        "submit_policy_schema_version": "phase23_bb_submit_policy_authority.v1",
        "submit_policy_version": policy.policy_version,
        "submit_policy_source": policy.policy_source,
        "submit_policy_hash": capital_deployment_policy_hash(policy),
    }


def _write_strategy_no_order_authority(root: Path, *, business_date: str) -> None:
    strategy_dir = root / "runtime_state" / "strategy_planning" / business_date
    order_plan = {
        "schema_version": "phase23_i_strategy_authority_order_plan.v1",
        "order_plan_id": f"strategy-plan-demo-{business_date}-no-order",
        "environment": "demo",
        "business_date": business_date,
        "target_session_date": business_date,
        "status": "NO_ORDER_AUTHORIZED",
        "planning_consumer_eligibility": "NO_ORDER_AUTHORIZED",
        "planning_authority": "phase22_strategy_runtime_planning",
        "strategy_artifact_path": str(root / "strategy" / business_date / "runtime_planning.json"),
        "position_sizing_artifact_path": str(root / "strategy" / business_date / "position_sizing.json"),
        "items": [],
        "strategy_item_lineage": [
            {
                "planning_id": f"rp-{business_date}-94320-no-action",
                "security_code": "94320",
                "planning_intent": "NO_ACTION",
                "order_side_intent": "NONE",
                "pending_item_generated": False,
                "reason": "no_action_strategy_intent",
            }
        ],
        "broker_write_allowed": False,
        "broker_write_performed": False,
        "production_decision_allowed": False,
        "silent_fallback_used": False,
        "latest_fallback_used": False,
        "future_information_used": False,
    }
    _write_json(strategy_dir / "order_plan.json", order_plan)
    _write_json(
        strategy_dir / "approval_artifact.json",
        {
            "schema_version": "phase23_ab_no_order_authorized_approval.v1",
            "status": "NO_ORDER_AUTHORIZED",
            "reason": "strategy_planning_no_order_authorized",
            "business_date": business_date,
            "target_session_date": business_date,
            "pending_item_count": 0,
            "order_plan_id": order_plan["order_plan_id"],
            "order_plan_hash": hashlib.sha256((strategy_dir / "order_plan.json").read_bytes()).hexdigest(),
        },
    )


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
