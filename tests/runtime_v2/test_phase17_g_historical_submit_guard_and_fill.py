from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import get_broker_capability
from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import _write_execution_manifest_evidence
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import (
    _evaluate_pre_commit_cash_feasibility,
    run_execution_readonly_pipeline,
)
from ai_fund_lab_v2.runtime_v2.historical_support.environment import (
    HistoricalExecutionSnapshotProvider,
    HistoricalSubmitAdapter,
)
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    capital_deployment_policy_hash,
    load_capital_deployment_policy,
)
from ai_fund_lab_v2.runtime_v2.submit.guards import run_submit_preflight
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand, SubmitEnvironmentGuardContext
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


def test_phase20_bq_historical_simulated_capability_allows_9000_series_submit_preflight() -> None:
    pending = _pending("historical", symbol="94320")
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

    assert get_broker_capability("historical").supports_9000_series_orders is True
    assert accepted.allowed is True
    assert accepted.command is not None
    assert accepted.command.symbol == "94320"


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


def test_phase20_bq_historical_submit_pipeline_fills_9000_series_without_broker_write(tmp_path: Path) -> None:
    runtime_root, policy_path, adapter = _runtime_fixture(tmp_path, side="BUY", symbol="94320")

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
    assert result.blocked_count == 0
    assert result.demo_submit_executed is False
    assert result.item_results[0].symbol == "94320"
    evidence_dir = runtime_root / "runtime_state" / "historical_broker" / BUSINESS_DATE
    evidence_files = list(evidence_dir.glob("*.json"))
    assert len(evidence_files) == 1
    evidence = json.loads(evidence_files[0].read_text(encoding="utf-8"))
    assert evidence["symbol"] == "94320"
    assert evidence["broker_write"] is False
    assert evidence["external_delivery"] is False
    assert evidence["historical_replay"] is True


def test_phase24_im_historical_submit_materializes_corporate_action_authority_before_guard(tmp_path: Path) -> None:
    runtime_root, policy_path, adapter = _runtime_fixture(tmp_path, side="SELL")
    pd.DataFrame(
        [{"Date": BUSINESS_DATE, "Code": SYMBOL, "AdjFactor": 0.3333333333333333, "C": 795.0, "AdjC": 795.0}]
    ).to_parquet(tmp_path / "raw_ohlcv.parquet", index=False)

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

    authority_path = runtime_root / "runtime_state" / "corporate_action_adjustments" / BUSINESS_DATE / f"{SYMBOL}.json"
    authority_hash = _sha(authority_path)
    guard = result.submit_guard_item_evidence[0]

    assert result.status == "REVIEW_REQUIRED"
    assert result.submitted_count == 0
    assert authority_path.exists()
    assert guard["corporate_action_event_status"] == "IMPACT_DETECTED"
    assert guard["corporate_action_event_type"] == "UNKNOWN_ADJFACTOR_IMPACT"
    assert guard["corporate_action_adjustment_authority_status"] == "REVIEW_REQUIRED"
    assert guard["corporate_action_adjustment_authority_path"] == str(authority_path)
    assert guard["corporate_action_adjustment_authority_hash"] == authority_hash
    assert "corporate_action_type_unresolved" in guard["corporate_action_reason_codes"]

    adapter_result = adapter.preflight(
        RuntimeV2SubmitCommand(
            command_id="phase24-im-adapter-command",
            environment="historical",
            pending_plan_id="pending-phase24-im",
            pending_item_id="item-1",
            approval_hash="sha256:approval",
            symbol=SYMBOL,
            side="SELL",
            quantity=100.0,
            order_type="MARKET",
            price_type="MARKET",
            limit_price=0.0,
            estimated_amount=300000.0,
            target_session_date=BUSINESS_DATE,
            live_order_allowed=True,
            listed_info={"code": SYMBOL, "trading_unit": 100},
        )
    )
    adapter_classification = adapter_result.response_classification
    assert adapter_classification["corporate_action_adjustment_authority_path"] == str(authority_path)
    assert adapter_classification["corporate_action_adjustment_authority_hash"] == authority_hash
    assert adapter_classification["corporate_action_event_status"] == guard["corporate_action_event_status"]
    assert adapter_classification["corporate_action_adjustment_authority_status"] == guard["corporate_action_adjustment_authority_status"]


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
    logical_manifest = asof_view.parent / "inputs" / "historical_asof" / BUSINESS_DATE / "logical_input_manifest.json"
    logical_manifest.parent.mkdir(parents=True, exist_ok=True)
    logical_manifest.write_text(
        json.dumps(
            {
                "status": "PASS",
                "business_date": BUSINESS_DATE,
                "feature_date": BUSINESS_DATE,
                "as_of_date": BUSINESS_DATE,
                "materialization_id": f"test-historical-asof:{BUSINESS_DATE}",
                "logical_paths": {"normalized_ohlcv": str(tmp_path / "ohlcv.parquet")},
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
    assert result.pre_commit_cash_feasibility_status == "PASS"
    assert result.reconcile_status == "PASS"


def test_phase29_l21t_q1_execution_pre_commit_blocks_negative_candidate_cash(tmp_path: Path) -> None:
    runtime_root, policy_path, adapter = _runtime_fixture(tmp_path, side="BUY")
    _write_current(runtime_root, side="BUY", cash=250_000.0)
    submit = adapter.submit(_command_from_pending(_pending("historical", policy_path=policy_path)))
    provider = HistoricalExecutionSnapshotProvider(runtime_root=runtime_root, business_date=BUSINESS_DATE)

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        snapshot_provider=provider,
    )

    assert submit.accepted is True
    assert result.status == "REVIEW_REQUIRED"
    assert result.pre_commit_cash_feasibility_status == "REVIEW_REQUIRED"
    assert result.candidate_projected_cash == -50_000.0
    assert result.aggregate_candidate_buy_notional == 300_000.0
    assert result.ledger_orders_appended == 0
    assert result.ledger_executions_appended == 0
    assert result.asset_current_written is False
    assert result.current_apply_status == "NOT_EXECUTED"
    assert not (runtime_root / "persistent_ledger" / "executions.jsonl").exists()


def test_phase29_l21t_q2_projection_failure_blocks_persistent_mutation(tmp_path: Path) -> None:
    runtime_root, policy_path, adapter = _runtime_fixture(tmp_path, side="BUY")
    _write_current(runtime_root, side="BUY")
    current_path = runtime_root / "persistent_ledger" / "state.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current["positions"] = [
        {
            "symbol": SYMBOL,
            "quantity": 100.0,
            "average_price": 2500.0,
            "cost_basis": 1.0,
            "market_value": 300000.0,
        }
    ]
    current["market_value"] = 300000.0
    current["total_equity"] = current["cash"] + current["market_value"]
    current_path.write_text(json.dumps(current), encoding="utf-8")
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
    assert result.status == "REVIEW_REQUIRED"
    assert result.transaction_validation_status == "REVIEW_REQUIRED"
    assert result.runtime_owned_projection_status == "REVIEW_REQUIRED"
    assert "runtime_owned_cost_basis_average_price_mismatch" in result.transaction_validation_reason
    assert result.ledger_orders_appended == 0
    assert result.ledger_executions_appended == 0
    assert result.ledger_positions_appended == 0
    assert result.ledger_cash_appended == 0
    assert result.asset_current_written is False
    assert result.current_apply_status == "NOT_EXECUTED"
    assert result.pending_terminalization_status == "NOT_EXECUTED"
    assert not (runtime_root / "persistent_ledger" / "executions.jsonl").exists()


def test_phase29_l21t_q2_execution_retry_dedups_committed_transaction(tmp_path: Path) -> None:
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

    first = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        snapshot_provider=provider,
    )
    second = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        snapshot_provider=provider,
    )
    execution_rows = [
        json.loads(line)
        for line in (runtime_root / "persistent_ledger" / "executions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    dedup_keys = [str(row.get("dedup_key") or "") for row in execution_rows]

    assert submit.status == "PASS"
    assert first.status == "PASS"
    assert first.transaction_validation_status == "PASS"
    assert first.persistent_commit_started is True
    assert first.persistent_commit_completed is True
    assert first.transaction_consistency_status == "PASS"
    assert second.status == "PASS"
    assert second.transaction_validation_status == "PASS"
    assert second.ledger_orders_appended == 0
    assert second.ledger_executions_appended == 0
    assert second.ledger_positions_appended == 0
    assert second.ledger_cash_appended == 0
    assert second.current_apply_status == "NOOP_ALREADY_APPLIED"
    assert len(dedup_keys) == len(set(dedup_keys))


def test_phase29_l21t_z_pre_commit_excludes_already_applied_candidate_executions(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    state_path = runtime_root / "persistent_ledger" / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "cash": 129_890.0,
                "runtime_owned_projection": {
                    "applied_execution_ids": ["execution-equivalent:sha256:sell-applied", "execution-equivalent:sha256:buy-applied"],
                    "applied_execution_dedup_keys": [
                        "runtime_v2_execution_equivalent:sha256:sell-applied",
                        "runtime_v2_execution_equivalent:sha256:buy-applied",
                    ],
                },
            },
        ),
        encoding="utf-8",
    )

    result = _evaluate_pre_commit_cash_feasibility(
        runtime_root=runtime_root,
        business_date="2023-06-23",
        candidate_executions=[
            SimpleNamespace(
                side="SELL",
                filled_quantity=100.0,
                quantity=100.0,
                price=49.0,
                average_price=49.0,
                cash_effect=4_900.0,
                execution_id="execution-equivalent:sha256:sell-applied",
                dedup_key="runtime_v2_execution_equivalent:sha256:sell-applied",
                symbol="37820",
            ),
            SimpleNamespace(
                side="BUY",
                filled_quantity=800.0,
                quantity=800.0,
                price=152.8,
                average_price=152.8,
                cash_effect=122_240.0,
                execution_id="execution-equivalent:sha256:buy-applied",
                dedup_key="runtime_v2_execution_equivalent:sha256:buy-applied",
                symbol="94340",
            ),
        ],
    )

    assert result["status"] == "PASS"
    assert result["candidate_projected_cash"] == 129_890.0
    assert result["aggregate_candidate_buy_notional"] == 0.0
    assert result["aggregate_candidate_sell_notional"] == 0.0
    assert result["already_applied_candidate_execution_count"] == 2
    assert result["selected_candidate_execution_count"] == 0
    assert [item["selected_into_candidate_projection"] for item in result["items"]] == [False, False]


def test_phase29_l21t_z_pre_commit_applies_only_unapplied_mixed_candidate_executions(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    state_path = runtime_root / "persistent_ledger" / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "cash": 100_000.0,
                "runtime_owned_projection": {
                    "applied_execution_dedup_keys": ["runtime_v2_execution_equivalent:sha256:already-bought"],
                },
            },
        ),
        encoding="utf-8",
    )

    result = _evaluate_pre_commit_cash_feasibility(
        runtime_root=runtime_root,
        business_date="2023-06-23",
        candidate_executions=[
            SimpleNamespace(
                side="BUY",
                filled_quantity=100.0,
                quantity=100.0,
                price=900.0,
                average_price=900.0,
                cash_effect=90_000.0,
                execution_id="execution-equivalent:sha256:already-bought",
                dedup_key="runtime_v2_execution_equivalent:sha256:already-bought",
                symbol="83060",
            ),
            SimpleNamespace(
                side="BUY",
                filled_quantity=100.0,
                quantity=100.0,
                price=300.0,
                average_price=300.0,
                cash_effect=30_000.0,
                execution_id="execution-equivalent:sha256:new-buy",
                dedup_key="runtime_v2_execution_equivalent:sha256:new-buy",
                symbol="94320",
            ),
        ],
    )

    assert result["status"] == "PASS"
    assert result["candidate_projected_cash"] == 70_000.0
    assert result["aggregate_candidate_buy_notional"] == 30_000.0
    assert result["already_applied_candidate_execution_count"] == 1
    assert result["selected_candidate_execution_count"] == 1
    assert [item["selected_into_candidate_projection"] for item in result["items"]] == [False, True]


def test_phase29_l21t_z_execution_retry_with_low_cash_does_not_reapply_buy_cash_effect(tmp_path: Path) -> None:
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

    first = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        snapshot_provider=provider,
    )
    state_path = runtime_root / "persistent_ledger" / "state.json"
    committed_state = json.loads(state_path.read_text(encoding="utf-8"))
    committed_state["cash"] = 50_000.0
    committed_state["buying_power"] = 50_000.0
    committed_state["total_equity"] = 50_000.0 + committed_state["market_value"]
    state_path.write_text(json.dumps(committed_state), encoding="utf-8")
    second = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        snapshot_provider=provider,
    )
    state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))

    assert submit.status == "PASS"
    assert first.status == "PASS", first.reason
    assert first.candidate_projected_cash == 700_000.0
    assert state["cash"] == 50_000.0
    assert second.status == "PASS"
    assert second.pre_commit_cash_feasibility_status == "PASS"
    assert second.candidate_projected_cash == 50_000.0
    assert second.aggregate_candidate_buy_notional == 0.0
    assert second.ledger_orders_appended == 0
    assert second.ledger_executions_appended == 0
    assert second.ledger_positions_appended == 0
    assert second.ledger_cash_appended == 0
    assert second.current_apply_status in {"APPLIED", "NOOP_ALREADY_APPLIED"}
    assert state["cash"] == 50_000.0
    execution_rows = [
        json.loads(line)
        for line in (runtime_root / "persistent_ledger" / "executions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(execution_rows) == 1


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
    symbol: str = SYMBOL,
) -> tuple[Path, Path, HistoricalSubmitAdapter]:
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_market_data(tmp_path, symbol=symbol)
    policy_path = runtime_root / "runtime_state" / "policy" / "capital_deployment.json"
    _write_policy(policy_path)
    _write_safety(runtime_root, decision=safety_decision)
    _write_current(runtime_root, side=side, symbol=symbol)
    pending = _pending("historical", side=side, policy_path=policy_path, symbol=symbol)
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


def _write_market_data(root: Path, *, symbol: str = SYMBOL) -> None:
    ohlcv = pd.DataFrame([{"Date": BUSINESS_DATE, "Code": symbol, "Open": 3000.0}])
    raw = pd.DataFrame([{"Date": BUSINESS_DATE, "Code": symbol, "AdjFactor": 1.0}])
    listed = pd.DataFrame([{"Date": BUSINESS_DATE, "Code": symbol}])
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


def _pending(environment: str, *, side: str = "BUY", policy_path: Path | None = None, symbol: str = SYMBOL):
    policy = load_capital_deployment_policy(policy_path) if policy_path else None
    quantity_contract = _authority_quantity_contract(symbol=symbol, policy=policy)
    binding = _accepted_generation_binding(environment=environment)
    is_buy = side.upper() == "BUY"
    item = PendingOrderItem(
        pending_item_id="item-1",
        symbol=symbol,
        side=side,
        quantity=100.0,
        order_type="MARKET",
        estimated_price=3000.0,
        estimated_amount=300000.0,
        approved=True,
        state="APPROVED",
        listed_info={
            "code": symbol,
            "trading_unit": 100,
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
        policy_version=policy.policy_version if policy else "",
        policy_source=policy.policy_source if policy else "",
        planning_authority_version="phase17_g_fixture_planning_authority",
        planning_authority_source="order-plan-phase17-g",
        planning_authority_hash="sha256:phase17-g-planning",
        submit_policy_version=policy.policy_version if policy else "",
        submit_policy_source=policy.policy_source if policy else "",
        submit_policy_hash=capital_deployment_policy_hash(policy) if policy else "",
        evaluation_capital=policy.evaluation_capital if policy else None,
        max_positions=policy.max_positions if policy else None,
        max_buy_order_amount=policy.max_buy_order_amount if policy else None,
        max_sell_liquidation_amount=policy.max_sell_liquidation_amount if policy else None,
        min_order_amount=policy.min_order_amount if policy else None,
        buy_notional_policy=policy.buy_notional_policy if policy else "",
        sell_liquidation_policy=policy.sell_liquidation_policy if policy else "",
        manual_review_threshold=asdict(policy.manual_review_threshold) if policy else None,
        accepted_generation_id=binding["accepted_generation_id"] if is_buy else "",
        accepted_generation_business_date=binding["accepted_generation_business_date"] if is_buy else "",
        accepted_generation_binding_status="PASS" if is_buy else "NOT_REQUIRED",
        accepted_generation_binding=binding if is_buy else None,
        quantity_contract=quantity_contract,
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
                "issue_code": symbol,
                "limit_price": None,
                "time_in_force": "DAY",
                "price_condition": "MARKET",
            }
        },
    )
    return link_approval_to_pending(pending_plan=pending, approval_artifact=approval)


def _authority_quantity_contract(*, symbol: str, policy) -> dict:
    if policy is None:
        return {}
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
                    "symbol": symbol,
                    "target_weight": 0.20,
                    "target_notional": 300_000,
                    "incremental_buy_notional": 300_000,
                    "maximum_position_weight": 1.0,
                }
            ],
            "effective_maximum_position_weight": 1.0,
        },
    }


def _accepted_generation_binding(*, environment: str) -> dict:
    return {
        "schema_version": "phase26_step8_accepted_generation_binding.v1",
        "consumer": "phase17_g_submit_fixture",
        "mode": environment,
        "requested_business_date": BUSINESS_DATE,
        "selected_business_date": BUSINESS_DATE,
        "accepted_generation_id": "phase17-g-fixture-generation",
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


def _write_current(runtime_root: Path, *, side: str, symbol: str = SYMBOL, cash: float = 1_000_000.0) -> None:
    path = runtime_root / "persistent_ledger" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    positions = (
        [{"symbol": symbol, "quantity": 100.0, "average_price": 2500.0, "market_value": 300000.0}]
        if side == "SELL"
        else []
    )
    path.write_text(
        json.dumps(
            {
                "buying_power": cash,
                "positions": positions,
                "market_value": 300000.0 if positions else 0.0,
                "cash": cash,
                "total_equity": cash + (300000.0 if positions else 0.0),
            }
        ),
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
