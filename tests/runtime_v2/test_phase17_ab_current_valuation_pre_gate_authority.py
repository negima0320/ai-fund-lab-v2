from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import (
    main,
    _readiness_scope_for_args,
    _write_current_valuation_manifest_evidence,
)
from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness
from ai_fund_lab_v2.runtime_v2.historical_support.safety_temporal_authority import (
    evaluate_historical_daily_neutral_safety_authority,
    pending_scope_current_valuation_adapter_ready,
)
from ai_fund_lab_v2.runtime_v2.pending.review_scope_authority import (
    GENERIC_TERMINAL_ITEM_STATES,
    NOT_EXECUTABLE_TERMINAL_EVIDENCE_INVALID,
    build_pending_review_scope_authority,
)


BUSINESS_DATE = "2026-07-06"
RUN_ID = "runtime-test-phase17ab"
PROFILE_ID = "historical-smoke"


def test_phase17ab_historical_current_valuation_pre_gate_passes_with_consumed_pending_authority(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_consumed_pending(runtime_root, tmp_path)
    _write_stale_latest_safety(runtime_root)

    result = _evaluate(runtime_root, tmp_path)

    assert result.status == "READY"
    assert result.payload["readiness_scope"] == "current_valuation"
    assert result.payload["safety_status"] == "READY"
    assert result.payload["broker_direct_scope_status"] == "NOT_REQUIRED"
    assert result.payload["components"]["safety"]["historical_safety_temporal_authority"] == "historical_initial_no_external_effect"
    assert result.payload["components"]["pending"]["historical_pending_safety_authority"]["pending_lifecycle_state"] == "CONSUMED"
    assert result.payload["components"]["pending"]["historical_pending_safety_authority"]["pending_consumed"] is True


def test_phase17ab_isolated_cli_reaches_current_valuation_producer_after_pre_gate_pass(tmp_path):
    pd = pytest.importorskip("pandas")
    runtime_root = _runtime_root(tmp_path)
    evidence_root = _evidence_root(tmp_path)
    _write_consumed_pending(runtime_root, tmp_path)
    _write_stale_latest_safety(runtime_root)
    _write_historical_asof_view(evidence_root, tmp_path, pd)
    policy_path = _write_policy(tmp_path / "capital_policy.json")

    exit_code = main(
        [
            "--mode",
            "historical",
            "--job",
            "current_valuation_refresh",
            "--business-date",
            BUSINESS_DATE,
            "--broker-environment",
            "historical_simulated",
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
            "--runtime-test-run-id",
            RUN_ID,
            "--runtime-test-profile-id",
            PROFILE_ID,
            "--runtime-test-evidence-root",
            str(evidence_root),
            "--evaluation-time",
            "2026-07-06T15:35:00+09:00",
        ]
    )

    manifest = _latest_manifest(runtime_root)
    stage_names = {stage["name"] for stage in manifest["stages"]}
    valuation = _read_json(Path(manifest["current_valuation_refresh_artifact_path"]))
    evidence = _read_json(evidence_root / "daily" / BUSINESS_DATE / "current_valuation_refresh" / "valuation_projection.json")
    assert exit_code == 0
    assert manifest["data_readiness_status"] == "READY"
    assert manifest["data_readiness_scope"] == "current_valuation"
    assert "current_valuation_refresh" in stage_names
    assert valuation["position_count"] == 5
    assert valuation["valued_position_count"] == 5
    assert valuation["market_date"] == BUSINESS_DATE
    assert valuation["market_evidence_path"].endswith("historical_asof_view.json")
    assert valuation["apply_requested"] is False
    assert valuation["apply_executed"] is False
    assert evidence["execution_reached"] is True
    assert evidence["blocked_before_producer"] is False


def test_phase30_ak9r6_post_submit_residual_buy_review_allows_current_valuation_readiness(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_post_submit_residual_buy_review_pending(runtime_root, tmp_path)
    _write_stale_latest_safety(runtime_root)

    result = _evaluate(runtime_root, tmp_path)

    pending = result.payload["components"]["pending"]
    safety = result.payload["components"]["safety"]["pending_safety_authority"]
    assert result.status == "READY"
    assert pending["reason"] == "post_submit_residual_buy_review_current_valuation_ready"
    assert pending["post_submit_residual_buy_review_current_valuation_ready"] is True
    assert safety["status"] == "READY"
    assert safety["reason"] == "historical_post_submit_residual_buy_review_current_valuation_ready"
    assert safety["post_submit_residual_buy_review_current_valuation_ready"] is True
    assert "pending_review_required" not in result.payload["review_reasons"]
    assert "historical_safety_temporal_authority_missing" not in result.payload["review_reasons"]


def test_phase31_f1z6_not_executable_terminal_pending_allows_current_valuation_readiness(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_terminal_not_executable_pending(runtime_root, tmp_path)
    _write_stale_latest_safety(runtime_root)

    result = _evaluate(runtime_root, tmp_path)
    pending_payload = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    authority = build_pending_review_scope_authority(pending_payload, slot_status="REVIEW_REQUIRED", active_pending=True)

    assert result.status == "READY"
    assert result.payload["components"]["pending"]["post_submit_residual_buy_review_current_valuation_ready"] is True
    assert result.payload["components"]["pending"]["historical_pending_safety_authority"]["status"] == "READY"
    assert result.payload["components"]["pending"]["historical_pending_safety_authority"]["pending_scope_compatible"] is True
    assert "pending_review_required" not in result.payload["review_reasons"]
    assert "historical_safety_temporal_authority_missing" not in result.payload["review_reasons"]
    assert "NOT_EXECUTABLE" in GENERIC_TERMINAL_ITEM_STATES
    assert set(authority.terminal_item_ids) == {"terminal-75590", "terminal-34940", "terminal-56100"}
    assert authority.non_terminal_item_ids == ()
    assert authority.reviewed_item_ids == ()
    assert authority.executable_item_ids == ()
    assert pending_scope_current_valuation_adapter_ready(
        pending_payload={"payload": pending_payload, "slot_status": "REVIEW_REQUIRED", "active_pending": True},
        business_date=BUSINESS_DATE,
        mode="historical",
    )


def test_phase31_f1z6_not_executable_terminal_pending_resolves_historical_neutral_safety(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_terminal_not_executable_pending(runtime_root, tmp_path)
    pending_payload = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    result = evaluate_historical_daily_neutral_safety_authority(
        business_date=BUSINESS_DATE,
        mode="historical",
        broker_environment="historical_simulated",
        current_payload={},
        pending_payload={"payload": pending_payload, "slot_status": "REVIEW_REQUIRED", "active_pending": True},
        readiness_scope="current_valuation",
        runtime_test_run_id=RUN_ID,
        runtime_test_profile_id=PROFILE_ID,
        runtime_test_evidence_root=str(_evidence_root(tmp_path)),
        broker_write=False,
        external_delivery=False,
        previous_empty_pending_present=False,
    )

    assert result["status"] == "READY"
    assert result["pending_scope_compatible"] is True
    assert result["mismatched_fields"] == []


def test_phase31_f1z6_malformed_not_executable_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_terminal_not_executable_pending(runtime_root, tmp_path, not_executable_overrides={"feasibility_status": ""})
    _write_stale_latest_safety(runtime_root)

    result = _evaluate(runtime_root, tmp_path)
    pending_payload = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    authority = build_pending_review_scope_authority(pending_payload, slot_status="REVIEW_REQUIRED", active_pending=True)

    assert result.status == "REVIEW_REQUIRED"
    assert "pending_review_required" in result.payload["review_reasons"]
    assert authority.structural_validity == "REVIEW_REQUIRED"
    assert any(reason.startswith(NOT_EXECUTABLE_TERMINAL_EVIDENCE_INVALID) for reason in authority.malformed_reasons)
    assert "terminal-34940" not in authority.terminal_item_ids


def test_phase31_f1z6_not_executable_unknown_side_effect_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_terminal_not_executable_pending(runtime_root, tmp_path, not_executable_overrides={"ledger_order_record_id": "unknown-ledger"})
    _write_stale_latest_safety(runtime_root)

    result = _evaluate(runtime_root, tmp_path)
    pending_payload = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    authority = build_pending_review_scope_authority(pending_payload, slot_status="REVIEW_REQUIRED", active_pending=True)

    assert result.status == "REVIEW_REQUIRED"
    assert "pending_review_required" in result.payload["review_reasons"]
    assert any(reason.startswith(NOT_EXECUTABLE_TERMINAL_EVIDENCE_INVALID) for reason in authority.malformed_reasons)


def test_phase31_f1z6_reviewed_sell_still_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_terminal_not_executable_pending(runtime_root, tmp_path, include_review_sell=True)
    _write_stale_latest_safety(runtime_root)

    result = _evaluate(runtime_root, tmp_path)

    assert result.status == "REVIEW_REQUIRED"
    assert "pending_review_required" in result.payload["review_reasons"]


def test_phase31_f1z6_retryable_approved_item_still_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_terminal_not_executable_pending(runtime_root, tmp_path, include_approved_retryable=True)
    _write_stale_latest_safety(runtime_root)

    result = _evaluate(runtime_root, tmp_path)
    pending_payload = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    authority = build_pending_review_scope_authority(pending_payload, slot_status="REVIEW_REQUIRED", active_pending=True)

    assert result.status == "REVIEW_REQUIRED"
    assert "pending_review_required" in result.payload["review_reasons"]
    assert authority.non_terminal_item_ids == ("retryable-72030",)


def test_phase30_ak9r6_isolated_cli_reaches_current_valuation_producer_with_residual_buy_review(tmp_path):
    pd = pytest.importorskip("pandas")
    runtime_root = _runtime_root(tmp_path)
    evidence_root = _evidence_root(tmp_path)
    _write_post_submit_residual_buy_review_pending(runtime_root, tmp_path)
    _write_stale_latest_safety(runtime_root)
    _write_historical_asof_view(evidence_root, tmp_path, pd)
    policy_path = _write_policy(tmp_path / "capital_policy.json")

    exit_code = main(
        [
            "--mode",
            "historical",
            "--job",
            "current_valuation_refresh",
            "--business-date",
            BUSINESS_DATE,
            "--broker-environment",
            "historical_simulated",
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
            "--runtime-test-run-id",
            RUN_ID,
            "--runtime-test-profile-id",
            PROFILE_ID,
            "--runtime-test-evidence-root",
            str(evidence_root),
            "--evaluation-time",
            "2026-07-06T15:35:00+09:00",
        ]
    )

    manifest = _latest_manifest(runtime_root)
    evidence = _read_json(evidence_root / "daily" / BUSINESS_DATE / "current_valuation_refresh" / "valuation_projection.json")
    pending = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    reviewed_states = {
        item["pending_item_id"]: item["state"]
        for item in pending["items"]
        if item["pending_item_id"] in pending["review_required_buy_item_ids"]
    }
    assert exit_code == 0
    assert manifest["data_readiness_status"] == "READY"
    assert evidence["execution_reached"] is True
    assert evidence["blocked_before_producer"] is False
    assert pending["state"] == "REVIEW_REQUIRED"
    assert reviewed_states == {"review-38410": "REVIEW_REQUIRED", "review-39950": "REVIEW_REQUIRED"}


def test_phase30_ak9r6_reviewed_buy_accidentally_consumed_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_post_submit_residual_buy_review_pending(runtime_root, tmp_path, reviewed_state="CONSUMED")
    _write_stale_latest_safety(runtime_root)

    result = _evaluate(runtime_root, tmp_path)

    assert result.status == "REVIEW_REQUIRED"
    assert "pending_review_required" in result.payload["review_reasons"]
    assert "historical_safety_temporal_authority_missing" in result.payload["review_reasons"]


def test_phase30_ak9r6_aggregate_cash_failure_remains_fail_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_post_submit_residual_buy_review_pending(runtime_root, tmp_path, violated_policy="aggregate_cash")
    _write_stale_latest_safety(runtime_root)

    result = _evaluate(runtime_root, tmp_path)

    assert result.status == "REVIEW_REQUIRED"
    assert "pending_review_required" in result.payload["review_reasons"]


def test_phase30_ak9r6_unresolved_sell_review_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_post_submit_residual_buy_review_pending(runtime_root, tmp_path, include_review_sell=True)
    _write_stale_latest_safety(runtime_root)

    result = _evaluate(runtime_root, tmp_path)

    assert result.status == "REVIEW_REQUIRED"
    assert "pending_review_required" in result.payload["review_reasons"]


def test_phase17ab_run_id_mismatch_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_consumed_pending(runtime_root, tmp_path, run_id="wrong-run")
    _write_stale_latest_safety(runtime_root)

    result = _evaluate(runtime_root, tmp_path)

    assert result.status == "REVIEW_REQUIRED"
    assert "historical_safety_temporal_authority_missing" in result.payload["review_reasons"]
    assert result.payload["components"]["pending"]["historical_pending_safety_authority"]["mismatched_fields"] == [
        "safety_context.runtime_test_run_id"
    ]


def test_phase17ab_profile_mismatch_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_consumed_pending(runtime_root, tmp_path, profile_id="wrong-profile")
    _write_stale_latest_safety(runtime_root)

    result = _evaluate(runtime_root, tmp_path)

    assert result.status == "REVIEW_REQUIRED"
    assert "safety_context.runtime_test_profile_id" in result.payload["components"]["pending"]["historical_pending_safety_authority"]["mismatched_fields"]


def test_phase17ab_evidence_root_mismatch_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_consumed_pending(runtime_root, tmp_path, evidence_root=str(tmp_path / "other-run"))
    _write_stale_latest_safety(runtime_root)

    result = _evaluate(runtime_root, tmp_path)

    assert result.status == "REVIEW_REQUIRED"
    assert "safety_context.runtime_test_evidence_root" in result.payload["components"]["pending"]["historical_pending_safety_authority"]["mismatched_fields"]


def test_phase17ab_business_date_mismatch_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_consumed_pending(runtime_root, tmp_path, safety_business_date="2026-07-07")
    _write_stale_latest_safety(runtime_root)

    result = _evaluate(runtime_root, tmp_path)

    assert result.status == "REVIEW_REQUIRED"
    assert "safety_context.safety_business_date" in result.payload["components"]["pending"]["historical_pending_safety_authority"]["mismatched_fields"]


def test_phase17ab_pending_safety_authority_missing_remains_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_consumed_pending(runtime_root, tmp_path, safety_context={})
    _write_stale_latest_safety(runtime_root)

    result = _evaluate(runtime_root, tmp_path)

    assert result.status == "REVIEW_REQUIRED"
    assert "historical_safety_temporal_authority_missing" in result.payload["review_reasons"]


def test_phase17ab_production_safety_missing_does_not_use_historical_fallback(tmp_path):
    runtime_root = _runtime_root(tmp_path, mode="production")
    _write_consumed_pending(runtime_root, tmp_path)

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="production",
        readiness_scope="current_valuation",
        broker_write=False,
        external_delivery=False,
    )

    assert result.status in {"REVIEW_REQUIRED", "HALT"}
    assert result.payload["safety_status"] == "REVIEW_REQUIRED"
    assert "safety decision evidence missing" in result.payload["review_reasons"]


def test_phase17ab_current_valuation_scope_mapping_is_not_execution():
    class Args:
        readiness_scope = ""
        job = "current_valuation_refresh"

    assert _readiness_scope_for_args(Args()) == "current_valuation"


def test_phase17ab_evidence_writer_marks_pre_gate_failure(tmp_path):
    evidence_root = _evidence_root(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    manifest = {
        "mode": "historical",
        "job": "current_valuation_refresh",
        "data_readiness_status": "REVIEW_REQUIRED",
        "warnings": ["historical_safety_temporal_authority_missing"],
        "errors": [],
        "prohibited_actions": {},
        "stages": [
            {"name": "environment_composition", "status": "PASS", "details": {"historical_replay": True}},
            {"name": "runtime_data_readiness_gate", "status": "REVIEW_REQUIRED", "details": {"reason": "historical_safety_temporal_authority_missing"}},
        ],
    }

    _write_current_valuation_manifest_evidence(
        evidence_root=evidence_root,
        business_date=BUSINESS_DATE,
        manifest_path=manifest_path,
        manifest=manifest,
    )

    projection = _read_json(evidence_root / "daily" / BUSINESS_DATE / "current_valuation_refresh" / "valuation_projection.json")
    apply = _read_json(evidence_root / "daily" / BUSINESS_DATE / "current_valuation_refresh" / "valuation_apply_evidence.json")
    assert projection["execution_reached"] is False
    assert projection["blocked_before_producer"] is True
    assert projection["blocking_stage"] == "runtime_data_readiness_gate"
    assert projection["blocking_reason"] == "historical_safety_temporal_authority_missing"
    assert apply["status"] == "NOT_EXECUTED"


def _evaluate(runtime_root: Path, tmp_path: Path):
    return evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        readiness_scope="current_valuation",
        broker_environment="historical_simulated",
        runtime_test_evidence_root=_evidence_root(tmp_path),
        runtime_test_run_id=RUN_ID,
        runtime_test_profile_id=PROFILE_ID,
        broker_write=False,
        external_delivery=False,
    )


def _runtime_root(tmp_path: Path, *, mode: str = "historical") -> Path:
    root = tmp_path / ".runtime"
    _write_contract_calendar(root)
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "runtime_v2_current_temporal_v1",
            "temporal_schema_version": "runtime_v2_current_temporal_v1",
            "position_state_as_of": BUSINESS_DATE,
            "valuation_as_of": BUSINESS_DATE,
            "source_market_date": BUSINESS_DATE,
            "last_execution_date": BUSINESS_DATE,
            "last_reconciled_at": "2026-07-06T06:30:00+00:00",
            "updated_at": "2026-07-06T06:30:00+00:00",
            "environment": mode,
            "positions": [_position(symbol) for symbol in ("81050", "67400", "66590", "36670", "45640")],
            "cash": 191600,
            "buying_power": 191600,
            "market_value": 808400,
            "total_equity": 1000000,
            "review_required": False,
        },
    )
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "runtime_v2_operation_state_v1",
            "role": "authoritative_runtime_operation_state",
            "business_date": BUSINESS_DATE,
            "generated_at": "2026-07-06T06:40:00+00:00",
            "updated_at": "2026-07-06T06:40:00+00:00",
            "environment": mode,
            "runtime_mode": mode,
            "state": "CURRENT_STATE_LOADED",
            "safety_state": "NORMAL",
            "current_safety_state": "NORMAL",
            "source": "runtime_v2_runtime_state_producer",
            "asset_state_is_authoritative_here": False,
            "pending_state_is_authoritative_here": False,
        },
    )
    _write_json(
        root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "runtime_business_date": BUSINESS_DATE,
            "business_date": BUSINESS_DATE,
            "market_date": BUSINESS_DATE,
            "status": "READY",
            "market_status": "READY",
            "quote_status": "READY",
            "quote_count": 5,
            "market_summary": {"quote_count": 5},
        },
    )
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    return root


def _write_contract_calendar(root: Path) -> None:
    _write_jsonl(
        root / "operations" / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.jsonl",
        [
            {"Date": "2026-07-03", "target_date": "2026-07-03", "HolDiv": "1"},
            {"Date": BUSINESS_DATE, "target_date": BUSINESS_DATE, "HolDiv": "1"},
        ],
    )


def _position(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "quantity": 100,
        "average_price": 1000,
        "current_price": 1000,
        "market_value": 100000,
        "unrealized_pnl": 0,
        "ownership": "runtime_owned",
    }


def _write_consumed_pending(
    runtime_root: Path,
    tmp_path: Path,
    *,
    run_id: str = RUN_ID,
    profile_id: str = PROFILE_ID,
    evidence_root: str | None = None,
    safety_business_date: str = BUSINESS_DATE,
    safety_context: dict | None = None,
) -> None:
    if safety_context is None:
        safety_context = {
            "safety_authority": "historical_initial_no_external_effect",
            "safety_decision_id": "",
            "safety_policy_version": "historical_replay_neutral_safety_v1",
            "safety_source": "data_readiness_historical_temporal_authority",
            "safety_decision": "ALLOW",
            "safety_reason": "historical_neutral_no_event_safety_ready",
            "safety_business_date": safety_business_date,
            "runtime_test_run_id": run_id,
            "runtime_test_profile_id": profile_id,
            "runtime_test_evidence_root": evidence_root or str(_evidence_root(tmp_path)),
        }
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-phase17ab",
            "state": "CONSUMED",
            "environment": "historical",
            "target_session_date": BUSINESS_DATE,
            "pending_policy_hash": "policy-hash",
            "approval": {"approval_status": "APPROVED", "pending_policy_hash": "policy-hash"},
            "consume": {"consumed": True, "consumed_at": "2026-07-06T06:35:00+00:00"},
            "safety_decision_id": "",
            "safety_policy_version": "historical_replay_neutral_safety_v1",
            "safety_context": safety_context,
            "items": [],
        },
    )


def _write_post_submit_residual_buy_review_pending(
    runtime_root: Path,
    tmp_path: Path,
    *,
    reviewed_state: str = "REVIEW_REQUIRED",
    violated_policy: str = "pc_discrete_quantity_authority_lot_overshoot_unresolved",
    include_review_sell: bool = False,
) -> None:
    safety_context = _historical_safety_context(tmp_path)
    approved_ids = ["approved-23700", "approved-94320"]
    review_ids = ["review-38410", "review-39950"]
    items = [
        _pending_item("approved-23700", "23700", "BUY", "CONSUMED", True, "PASS_ITEM_SUBMITTABLE", safety_context),
        _pending_item("approved-94320", "94320", "BUY", "CONSUMED", True, "PASS_ITEM_SUBMITTABLE", safety_context),
        _pending_item("review-38410", "38410", "BUY", reviewed_state, False, "ITEM_REVIEW_REQUIRED", safety_context),
        _pending_item("review-39950", "39950", "BUY", reviewed_state, False, "ITEM_REVIEW_REQUIRED", safety_context),
    ]
    review_sell_ids: list[str] = []
    if include_review_sell:
        review_sell_ids.append("review-sell-81050")
        items.append(_pending_item("review-sell-81050", "81050", "SELL", "REVIEW_REQUIRED", False, "ITEM_REVIEW_REQUIRED", safety_context))
    feasibility_items = [
        {"pending_item_id": item_id, "symbol": symbol, "side": "BUY", "status": "PASS"}
        for item_id, symbol in (("approved-23700", "23700"), ("approved-94320", "94320"))
    ]
    feasibility_items.extend(
        {
            "pending_item_id": item_id,
            "symbol": symbol,
            "side": "BUY",
            "status": "REVIEW_REQUIRED",
            "violated_policy": violated_policy,
            "violated_policy_source": "position_sizing_authority",
        }
        for item_id, symbol in (("review-38410", "38410"), ("review-39950", "39950"))
    )
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "phase30_ak9r6_fixture_v1",
            "pending_plan_id": "pending-phase30-ak9r6",
            "state": "REVIEW_REQUIRED",
            "environment": "historical",
            "target_session_date": BUSINESS_DATE,
            "review_reason": "pending_review_required",
            "review_scope": "BUY_ITEM_SCOPED_REVIEW",
            "sell_continuation_allowed": True,
            "plan_overall_status": "APPROVED_WITH_BUY_ITEM_SCOPED_REVIEW",
            "buy_items_status": "REVIEW_REQUIRED",
            "sell_items_status": "NOT_PRESENT",
            "approved_buy_item_ids": approved_ids,
            "review_required_buy_item_ids": review_ids,
            "review_required_sell_item_ids": review_sell_ids,
            "approval": {"approval_status": "APPROVED_WITH_BUY_ITEM_SCOPED_REVIEW", "pending_policy_hash": "policy-hash"},
            "consume": {"consumed": False},
            "safety_policy_version": "historical_replay_neutral_safety_v1",
            "safety_context": safety_context,
            "planning_submit_feasibility": {
                "status": "REVIEW_REQUIRED",
                "items": feasibility_items,
            },
            "items": items,
        },
    )


def _write_terminal_not_executable_pending(
    runtime_root: Path,
    tmp_path: Path,
    *,
    not_executable_overrides: dict | None = None,
    include_review_sell: bool = False,
    include_approved_retryable: bool = False,
) -> None:
    safety_context = _historical_safety_context(tmp_path)
    approved_buy_ids = ["terminal-75590"]
    approved_sell_ids = ["terminal-56100"]
    review_sell_ids: list[str] = []
    items = [
        _pending_item("terminal-75590", "75590", "BUY", "CONSUMED", True, "PASS_ITEM_SUBMITTABLE", safety_context),
        {
            **_pending_item("terminal-34940", "34940", "SELL", "NOT_EXECUTABLE", False, "NOT_EXECUTABLE", safety_context),
            "feasibility_status": "NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE",
            "item_review_reason": "EXECUTION_AUTHORITY_UNAVAILABLE",
            "retry_eligible_same_day": False,
            "next_day_re_evaluation_required": True,
            **(not_executable_overrides or {}),
        },
        _pending_item("terminal-56100", "56100", "SELL", "CONSUMED", True, "PASS_ITEM_SUBMITTABLE", safety_context),
    ]
    if include_review_sell:
        review_sell_ids.append("review-sell-81050")
        items.append(_pending_item("review-sell-81050", "81050", "SELL", "REVIEW_REQUIRED", False, "ITEM_REVIEW_REQUIRED", safety_context))
    if include_approved_retryable:
        approved_buy_ids.append("retryable-72030")
        items.append(_pending_item("retryable-72030", "72030", "BUY", "APPROVED", True, "PASS_ITEM_SUBMITTABLE", safety_context))
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "phase31_f1z6_fixture_v1",
            "pending_plan_id": "pending-phase31-f1z6",
            "state": "REVIEW_REQUIRED",
            "environment": "historical",
            "target_session_date": BUSINESS_DATE,
            "review_reason": "pending_review_required",
            "review_scope": "",
            "sell_continuation_allowed": False,
            "plan_overall_status": "REVIEW_REQUIRED_WITH_TERMINAL_RESIDUALS",
            "approved_item_ids": approved_buy_ids + approved_sell_ids,
            "approved_buy_item_ids": approved_buy_ids,
            "approved_sell_item_ids": approved_sell_ids,
            "review_required_buy_item_ids": [],
            "review_required_sell_item_ids": review_sell_ids,
            "approval": {"approval_status": "REVIEW_REQUIRED_WITH_TERMINAL_RESIDUALS", "pending_policy_hash": "policy-hash"},
            "consume": {"consumed": False, "submitted_order_ids": ["order-75590", "order-56100"], "ledger_order_record_ids": ["ledger-75590", "ledger-56100"]},
            "safety_policy_version": "historical_replay_neutral_safety_v1",
            "safety_context": safety_context,
            "planning_submit_feasibility": {
                "status": "REVIEW_REQUIRED",
                "items": [
                    {"pending_item_id": "terminal-75590", "symbol": "75590", "side": "BUY", "status": "PASS"},
                    {"pending_item_id": "terminal-56100", "symbol": "56100", "side": "SELL", "status": "PASS"},
                ],
            },
            "items": items,
        },
    )


def _historical_safety_context(tmp_path: Path) -> dict:
    return {
        "safety_authority": "historical_initial_no_external_effect",
        "safety_decision_id": f"historical-neutral-safety:{BUSINESS_DATE}",
        "safety_policy_version": "historical_replay_neutral_safety_v1",
        "safety_source": "data_readiness_historical_temporal_authority",
        "safety_decision": "ALLOW",
        "safety_reason": "historical_neutral_no_event_safety_ready",
        "safety_business_date": BUSINESS_DATE,
        "runtime_test_run_id": RUN_ID,
        "runtime_test_profile_id": PROFILE_ID,
        "runtime_test_evidence_root": str(_evidence_root(tmp_path)),
    }


def _pending_item(
    item_id: str,
    symbol: str,
    side: str,
    state: str,
    approved: bool,
    batch_submit_status: str,
    safety_context: dict,
) -> dict:
    return {
        "pending_item_id": item_id,
        "symbol": symbol,
        "side": side,
        "state": state,
        "approved": approved,
        "batch_submit_status": batch_submit_status,
        "quantity": 100,
        "temporal_authority_business_date": BUSINESS_DATE,
        **safety_context,
    }


def _write_stale_latest_safety(runtime_root: Path) -> None:
    _write_json(
        runtime_root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "business_date": "2026-07-10",
            "runtime_mode": "historical",
            "decision": "REVIEW_REQUIRED",
            "reason": "HIGH_RISK_REVIEW",
            "review_required": True,
        },
    )


def _write_historical_asof_view(evidence_root: Path, tmp_path: Path, pd) -> None:
    parquet = tmp_path / "normalized_ohlcv.parquet"
    calendar = tmp_path / "trading_calendar.jsonl"
    pd.DataFrame(
        [
            {"Date": BUSINESS_DATE, "Code": symbol, "Close": 1000.0}
            for symbol in ("81050", "67400", "66590", "36670", "45640")
        ]
    ).to_parquet(parquet)
    _write_jsonl(
        calendar,
        [
            {"Date": "2026-07-03", "target_date": "2026-07-03", "HolDiv": "1"},
            {"Date": BUSINESS_DATE, "target_date": BUSINESS_DATE, "HolDiv": "1"},
        ],
    )
    _write_json(
        evidence_root / "daily" / BUSINESS_DATE / "market_refresh" / "historical_asof_view.json",
        {
            "schema_version": "phase17_l_historical_asof_view_v1",
            "status": "PASS",
            "reason": "historical_asof_view_ready",
            "business_date": BUSINESS_DATE,
            "latest_available_market_date": BUSINESS_DATE,
            "future_rows_excluded_from_consumer": True,
            "authorities": [
                {
                    "authority": "normalized_ohlcv",
                    "status": "PASS",
                    "reason": "historical_asof_authority_ready",
                    "business_date": BUSINESS_DATE,
                    "physical_source_path": str(parquet),
                    "physical_source_hash": "fixture",
                    "logical_cutoff": BUSINESS_DATE,
                    "logical_max_date": BUSINESS_DATE,
                },
                {
                    "authority": "trading_calendar",
                    "status": "PASS",
                    "reason": "historical_calendar_authority_ready",
                    "business_date": BUSINESS_DATE,
                    "physical_source_path": str(calendar),
                    "physical_source_hash": "fixture-calendar",
                    "logical_cutoff": BUSINESS_DATE,
                    "logical_max_date": BUSINESS_DATE,
                }
            ],
        },
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
            "manual_review_threshold": {"buy_amount": None, "sell_liquidation_amount": None},
        },
    )
    return path


def _latest_manifest(runtime_root: Path) -> dict:
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / BUSINESS_DATE).glob("*.json"))
    assert manifests
    return _read_json(manifests[-1])


def _evidence_root(tmp_path: Path) -> Path:
    return tmp_path / "reports" / "runtime_tests" / "runs" / RUN_ID


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
