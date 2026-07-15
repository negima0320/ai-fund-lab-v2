from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import get_broker_capability
from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import _write_execution_manifest_evidence
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from ai_fund_lab_v2.runtime_v2.historical_support.environment import (
    HistoricalExecutionSnapshotProvider,
    HistoricalSubmitAdapter,
)
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    load_capital_deployment_policy,
)
from ai_fund_lab_v2.runtime_v2.submit.guards import run_submit_preflight
from ai_fund_lab_v2.runtime_v2.submit.models import SubmitEnvironmentGuardContext
from ai_fund_lab_v2.runtime_v2.submit.pipeline import _approval_from_pending, run_submit_pipeline


BUSINESS_DATE = "2026-07-06"
EVALUATION_TIME = "2026-07-06T08:30:00+09:00"
SYMBOL = "7203"


def test_phase17_g_environment_matrix_allows_only_formal_historical_context() -> None:
    pending = _pending("historical")
    approval = _approval_from_pending(pending)
    accepted = run_submit_preflight(
        pending_plan=pending,
        approval_artifact=approval,
        approved_item_id="item-1",
        existing_order_dedup_keys=set(),
        environment="historical",
        base_url_is_demo=False,
        base_url_is_production=False,
        live_order_allowed=True,
        broker_capability=get_broker_capability("historical"),
        environment_context=_historical_context(),
    )
    wrong_adapter = run_submit_preflight(
        pending_plan=pending,
        approval_artifact=approval,
        approved_item_id="item-1",
        existing_order_dedup_keys=set(),
        environment="historical",
        base_url_is_demo=False,
        base_url_is_production=False,
        live_order_allowed=True,
        broker_capability=get_broker_capability("historical"),
        environment_context=replace(_historical_context(), adapter_type="DemoSubmitAdapter"),
    )
    broker_write = run_submit_preflight(
        pending_plan=pending,
        approval_artifact=approval,
        approved_item_id="item-1",
        existing_order_dedup_keys=set(),
        environment="historical",
        base_url_is_demo=False,
        base_url_is_production=False,
        live_order_allowed=True,
        broker_capability=get_broker_capability("historical"),
        environment_context=replace(_historical_context(), broker_write=True),
    )

    assert accepted.allowed is True
    assert accepted.command is not None
    assert wrong_adapter.reason == "environment matrix guard failure: historical adapter mismatch"
    assert broker_write.reason == "environment matrix guard failure: historical broker_write must be false"


def test_phase17_g_submit_pipeline_uses_normal_guard_before_historical_adapter(tmp_path: Path) -> None:
    runtime_root, policy_path, adapter = _runtime_fixture(tmp_path, side="BUY")

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
        environment_context=_historical_context(),
    )

    assert result.status == "PASS"
    assert result.submitted_count == 1
    assert result.accepted_count == 1
    assert result.demo_submit_executed is False
    evidence_dir = runtime_root / "runtime_state" / "historical_broker" / BUSINESS_DATE
    assert len(list(evidence_dir.glob("*.json"))) == 1


def test_phase17_g_historical_adapter_prefers_run_scoped_asof_hash_over_stale_manifest(tmp_path: Path) -> None:
    runtime_root, _, _ = _runtime_fixture(tmp_path, side="BUY")
    stale_manifest = tmp_path / "stale_pit_manifest.json"
    stale_manifest.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "business_date": BUSINESS_DATE,
                        "source_hashes": {"ohlcv_normalized": "0" * 64},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    asof_view = tmp_path / "historical_asof_view.json"
    asof_view.write_text(
        json.dumps(
            {
                "business_date": BUSINESS_DATE,
                "authorities": [
                    {
                        "authority": "normalized_ohlcv",
                        "business_date": BUSINESS_DATE,
                        "physical_source_path": str(tmp_path / "ohlcv.parquet"),
                        "physical_source_hash": _sha(tmp_path / "ohlcv.parquet"),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    adapter = HistoricalSubmitAdapter(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        evaluation_time=EVALUATION_TIME,
        pit_manifest_path=stale_manifest,
        historical_asof_view_path=asof_view,
        ohlcv_path=tmp_path / "ohlcv.parquet",
        listed_issues_path=tmp_path / "listed.parquet",
        raw_ohlcv_path=tmp_path / "raw_ohlcv.parquet",
    )

    result = adapter.preflight(_command_from_pending(_pending("historical")))

    assert result.status == "DRY_RUN_READY"


def test_phase17_g_safety_block_never_calls_historical_adapter(tmp_path: Path) -> None:
    runtime_root, policy_path, adapter = _runtime_fixture(tmp_path, side="BUY", safety_decision="BLOCKED")

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
        environment_context=_historical_context(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.submitted_count == 0
    assert not (runtime_root / "runtime_state" / "historical_broker").exists()
    assert result.item_results[0].guard_evidence["violated_policy"] == "safety_operation_guard"


def test_phase17_g_execution_snapshot_provider_emits_runtime_schema(tmp_path: Path) -> None:
    runtime_root, _, adapter = _runtime_fixture(tmp_path, side="BUY")
    command = _command_from_pending(_pending("historical"))
    submit = adapter.submit(command)
    provider = HistoricalExecutionSnapshotProvider(runtime_root=runtime_root, business_date=BUSINESS_DATE)
    snapshot_path = tmp_path / "snapshot.json"
    report_path = tmp_path / "report.json"

    result = provider(mode="historical", snapshot_path=snapshot_path, report_path=report_path)
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))

    assert submit.accepted is True
    assert result.status == "PASS"
    assert payload["orders"][0]["order_status"] == "filled"
    assert payload["executions"][0]["price"] == 3000.0
    assert payload["buying_power"]["cash_available"] == "700000.0"
    assert payload["buying_power"]["buying_power"] == "700000.0"
    assert payload["broker_write"] is False


def test_phase17_g_execution_processor_accepts_historical_provider_fixture(tmp_path: Path) -> None:
    runtime_root, policy_path, adapter = _runtime_fixture(tmp_path, side="BUY")
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
        environment_context=_historical_context(),
    )
    provider = HistoricalExecutionSnapshotProvider(runtime_root=runtime_root, business_date=BUSINESS_DATE)

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        snapshot_provider=provider,
    )

    assert submit.status == "PASS"
    assert result.snapshot_status == "PASS"
    assert result.status == "PASS"
    assert result.orderlist_readonly_connected is True
    assert result.execution_reflection_connected is True
    assert result.ledger_connected is True
    assert result.asset_current_written is True
    assert result.runtime_owned_projection_status == "PASS"
    assert result.current_apply_status == "APPLIED"
    assert result.reconcile_status == "PASS"


def test_phase17_g_execution_run_scoped_evidence_writer_records_authorities(tmp_path: Path) -> None:
    evidence_root = tmp_path / "run"
    manifest_path = tmp_path / "runtime-v2-execution.json"
    manifest = {
        "business_date": BUSINESS_DATE,
        "mode": "historical",
        "runtime_test_run_id": "runtime-test-fixture",
        "runtime_test_profile_id": "historical-smoke",
        "warnings": [],
        "errors": [],
        "prohibited_actions": {
            "demo_submit_executed": False,
            "production_order_executed": False,
            "notification_sent": False,
            "phase9_runtime_called": False,
            "phase9_writer_called": False,
            "mode_rooted_current_used": False,
        },
        "stages": [
            {
                "name": "environment_composition",
                "status": "PASS",
                "details": {
                    "broker_write": False,
                    "external_delivery": False,
                    "historical_replay": True,
                    "simulation": True,
                },
            },
            {
                "name": "runtime_v2_execution_readonly_pipeline",
                "status": "PASS",
                "details": {
                    "execution_acceptance_status": "PASS",
                    "execution_acceptance_reason": "orderlist_position_cash_evidence_accepted",
                    "snapshot_status": "PASS",
                    "snapshot_path": ".runtime/runtime_state/broker_readonly/2026-07-06/tachibana_snapshot.json",
                    "orders_count": 1,
                    "executions_count": 1,
                    "positions_count": 1,
                    "cash_present": True,
                    "ledger_connected": True,
                    "ledger_orders_appended": 1,
                    "ledger_executions_appended": 2,
                    "ledger_positions_appended": 1,
                    "ledger_cash_appended": 1,
                    "ledger_events_appended": 1,
                    "current_apply_status": "APPLIED",
                    "current_apply_reason": "current projection applied to runtime state",
                    "runtime_owned_projection_status": "PASS",
                    "asset_current_written": True,
                    "current_hash": "sha256:fixture",
                    "current_version": "current-fixture",
                    "runtime_state_path": ".runtime/runtime_state/current_state.json",
                    "runtime_state_version": "runtime-state-fixture",
                    "execution_references": ["execution-equivalent:fixture"],
                    "execution_equivalent_count": 1,
                    "orderlist_readonly_connected": True,
                },
            },
        ],
    }

    _write_execution_manifest_evidence(
        evidence_root=evidence_root,
        business_date=BUSINESS_DATE,
        manifest_path=manifest_path,
        manifest=manifest,
    )

    execution_dir = evidence_root / "daily" / BUSINESS_DATE / "execution"
    assert json.loads((execution_dir / "external_effect_audit.json").read_text(encoding="utf-8"))["status"] == "PASS"
    submitted = json.loads((execution_dir / "submitted_order_authority.json").read_text(encoding="utf-8"))
    current = json.loads((execution_dir / "current_apply_evidence.json").read_text(encoding="utf-8"))
    pending = json.loads((execution_dir / "pending_terminalization_evidence.json").read_text(encoding="utf-8"))
    assert submitted["runtime_test_run_id"] == "runtime-test-fixture"
    assert submitted["orders_count"] == 1
    assert current["status"] == "APPLIED"
    assert pending["pending_consumed"] is True


def _runtime_fixture(
    tmp_path: Path,
    *,
    side: str,
    safety_decision: str = "ALLOW",
) -> tuple[Path, Path, HistoricalSubmitAdapter]:
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_market_data(tmp_path)
    policy_path = runtime_root / "runtime_state" / "policy" / "capital_deployment.json"
    _write_policy(policy_path)
    _write_safety(runtime_root, decision=safety_decision)
    _write_current(runtime_root, side=side)
    pending = _pending("historical", side=side, policy_path=policy_path)
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)
    adapter = HistoricalSubmitAdapter(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        evaluation_time=EVALUATION_TIME,
        pit_manifest_path=tmp_path / "pit_manifest.json",
        ohlcv_path=tmp_path / "ohlcv.parquet",
        listed_issues_path=tmp_path / "listed.parquet",
        raw_ohlcv_path=tmp_path / "raw_ohlcv.parquet",
    )
    return runtime_root, policy_path, adapter


def _write_market_data(root: Path) -> None:
    ohlcv = pd.DataFrame([{"Date": BUSINESS_DATE, "Code": SYMBOL, "Open": 3000.0}])
    raw = pd.DataFrame([{"Date": BUSINESS_DATE, "Code": SYMBOL, "AdjFactor": 1.0}])
    listed = pd.DataFrame([{"Date": BUSINESS_DATE, "Code": SYMBOL}])
    ohlcv.to_parquet(root / "ohlcv.parquet", index=False)
    raw.to_parquet(root / "raw_ohlcv.parquet", index=False)
    listed.to_parquet(root / "listed.parquet", index=False)
    manifest = {
        "entries": [
            {
                "business_date": BUSINESS_DATE,
                "source_hashes": {"ohlcv_normalized": _sha(root / "ohlcv.parquet")},
            }
        ]
    }
    (root / "pit_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _pending(environment: str, *, side: str = "BUY", policy_path: Path | None = None):
    policy = load_capital_deployment_policy(policy_path) if policy_path else None
    item = PendingOrderItem(
        pending_item_id="item-1",
        symbol=SYMBOL,
        side=side,
        quantity=100.0,
        order_type="MARKET",
        estimated_price=3000.0,
        estimated_amount=300000.0,
        approved=True,
        state="APPROVED",
        listed_info={"code": SYMBOL, "trading_unit": 100},
        policy_version=policy.policy_version if policy else "",
        policy_source=policy.policy_source if policy else "",
        evaluation_capital=policy.evaluation_capital if policy else None,
        target_investment_ratio=policy.target_investment_ratio if policy else None,
        cash_buffer=policy.cash_buffer if policy else None,
        max_exposure=policy.max_exposure if policy else None,
        max_position_weight=policy.max_position_weight if policy else None,
        max_positions=policy.max_positions if policy else None,
        max_buy_order_amount=policy.max_buy_order_amount if policy else None,
        max_sell_liquidation_amount=policy.max_sell_liquidation_amount if policy else None,
        min_order_amount=policy.min_order_amount if policy else None,
        buy_notional_policy=policy.buy_notional_policy if policy else "",
        sell_liquidation_policy=policy.sell_liquidation_policy if policy else "",
        manual_review_threshold=asdict(policy.manual_review_threshold) if policy else None,
        safety_decision_id="safety-phase17-g",
        safety_policy_version="safety_policy_v1",
        safety_decision="ALLOW",
    )
    pending = promote_order_plan_to_pending(
        order_plan_id="order-plan-phase17-g",
        source_order_plan_path="fixture-order-plan.json",
        source_order_plan_hash="sha256:fixture",
        environment=environment,
        plan_created_date=BUSINESS_DATE,
        intended_submit_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        items=(item,),
    )
    approval = ApprovalArtifact(
        approval_id="approval-phase17-g",
        approval_request_id="request-phase17-g",
        pending_plan_id=pending.pending_plan_id,
        order_plan_id=pending.source_order_plan.order_plan_id,
        status=ApprovalStatus.APPROVED,
        approved_item_ids=("item-1",),
        rejected_item_ids=(),
        approval_hash="sha256:approval",
        approved_at=EVALUATION_TIME,
        expires_at="2026-07-06T15:00:00+09:00",
        review_required=False,
        reason="phase17-g fixture",
        policy_version=pending.policy_version,
        policy_source=pending.policy_source,
        pending_policy_hash=pending.pending_policy_hash,
        safety_decision_id=pending.safety_decision_id,
        safety_policy_version=pending.safety_policy_version,
        approved_order_conditions={
            "item-1": {
                "order_type": "MARKET",
                "target_session": BUSINESS_DATE,
                "quantity": 100.0,
                "side": side,
                "issue_code": SYMBOL,
                "limit_price": None,
                "time_in_force": "DAY",
                "price_condition": "MARKET",
            }
        },
    )
    return link_approval_to_pending(pending_plan=pending, approval_artifact=approval)


def _command_from_pending(pending):
    return run_submit_preflight(
        pending_plan=pending,
        approval_artifact=_approval_from_pending(pending),
        approved_item_id="item-1",
        existing_order_dedup_keys=set(),
        environment="historical",
        base_url_is_demo=False,
        base_url_is_production=False,
        live_order_allowed=True,
        broker_capability=get_broker_capability("historical"),
        environment_context=_historical_context(),
    ).command


def _historical_context() -> SubmitEnvironmentGuardContext:
    return SubmitEnvironmentGuardContext(
        runtime_environment="historical",
        pending_environment="historical",
        run_type="HISTORICAL",
        broker_environment="historical_simulated",
        adapter_type="HistoricalSubmitAdapter",
        broker_write=False,
        external_delivery=False,
        business_date=BUSINESS_DATE,
        evaluation_time=EVALUATION_TIME,
        production_acceptance=False,
    )


def _write_policy(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "policy_version": "capital_deployment_v1",
        "policy_source": str(path),
        "evaluation_capital": 1_000_000,
        "target_investment_ratio": 0.85,
        "cash_buffer": 0.05,
        "max_exposure": 850_000,
        "max_position_weight": 0.5,
        "max_positions": 5,
        "min_order_amount": 0,
        "max_buy_order_amount": None,
        "max_sell_liquidation_amount": None,
        "buy_notional_policy": "derived_from_capital_allocation_and_constraints",
        "sell_liquidation_policy": "current_owned_available_quantity_policy",
        "allowed_order_types": ["MARKET"],
        "allowed_time_in_force": ["DAY"],
        "manual_review_threshold": {"buy_amount": 999999999, "sell_liquidation_amount": 999999999},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_safety(runtime_root: Path, *, decision: str) -> None:
    path = runtime_root / "runtime_state" / "safety" / "latest_safety_decision.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    blocked = decision == "BLOCKED"
    path.write_text(
        json.dumps(
            {
                "safety_decision_id": "safety-phase17-g",
                "safety_policy_version": "safety_policy_v1",
                "safety_source": "phase17-g-fixture",
                "business_date": BUSINESS_DATE,
                "runtime_mode": "historical",
                "decision": decision,
                "reason": "phase17-g fixture",
                "review_required": blocked,
                "block_buy": blocked,
                "block_sell": blocked,
                "block_submit": blocked,
                "halt_runtime": False,
                "emergency_stop": False,
                "generated_at": EVALUATION_TIME,
                "expires_at": "2026-07-06T15:00:00+09:00",
                "safety_status": "PASS",
                "action_permissions": {
                    "buy_submit": "BLOCKED" if blocked else "ALLOWED",
                    "sell_submit": "BLOCKED" if blocked else "ALLOWED",
                    "broker_write": "BLOCKED",
                },
            }
        ),
        encoding="utf-8",
    )


def _write_current(runtime_root: Path, *, side: str) -> None:
    path = runtime_root / "persistent_ledger" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    positions = (
        [{"symbol": SYMBOL, "quantity": 100.0, "average_price": 2500.0, "market_value": 300000.0}]
        if side == "SELL"
        else []
    )
    path.write_text(
        json.dumps(
            {
                "cash": 1_000_000.0,
                "buying_power": 1_000_000.0,
                "positions": positions,
                "market_value": 300000.0 if positions else 0.0,
                "total_equity": 1_000_000.0,
            }
        ),
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
