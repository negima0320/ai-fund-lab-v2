from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "runtime_test.py"
CONFIRM_FLAG = "--yes-i-understand-this-mutates-trading-state"


def load_runner():
    spec = importlib.util.spec_from_file_location("runtime_test_script", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "persistent_ledger").mkdir(parents=True)
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "runtime_state").mkdir(parents=True)
    (root / "artifact_registry" / "checkpoints").mkdir(parents=True)
    (root / "artifact_registry" / "index").mkdir(parents=True)
    (root / "operations" / "feature_date_contract").mkdir(parents=True)
    (root / "persistent_ledger" / "state.json").write_text(
        json.dumps({"schema_version": "runtime_v2_current_temporal_v1", "environment": "historical", "cash": 12, "buying_power": 12, "positions": []}),
        encoding="utf-8",
    )
    for name in ("orders.jsonl", "executions.jsonl", "positions.jsonl", "cash.jsonl", "events.jsonl"):
        (root / "persistent_ledger" / name).write_text("", encoding="utf-8")
    (root / "pending_order_plan" / "pending_order_plan.json").write_text(
        json.dumps({"schema_version": "runtime_v2_pending_slot_v1", "status": "EMPTY", "state": "EMPTY", "active_pending": False}),
        encoding="utf-8",
    )
    (root / "runtime_state" / "current_state.json").write_text(
        json.dumps({"schema_version": "runtime_v2_operation_state_v1", "runtime_mode": "historical", "environment": "historical", "state": "READY", "business_date": "2026-07-06"}),
        encoding="utf-8",
    )
    _write_accepted_generation_authority(root, business_date="2026-07-06")
    (root / "artifact_registry" / "checkpoints" / "latest.json").write_text(
        json.dumps({"checkpoint_hash": "checkpoint-a"}),
        encoding="utf-8",
    )
    (root / "artifact_registry" / "index" / "registry_index.json").write_text(
        json.dumps({"index_hash": "index-a"}),
        encoding="utf-8",
    )
    for business_date, selected in {
        "2026-07-06": "2026-07-06",
        "2026-07-07": "2026-07-07",
        "2026-07-08": "2026-07-08",
        "2026-07-09": "2026-07-08",
        "2026-07-10": "2026-07-10",
    }.items():
        (root / "operations" / "feature_date_contract" / f"{business_date}.json").write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "requested_feature_date": business_date,
                    "selected_feature_date": selected,
                    "latest_available_market_date": selected,
                    "carryover_used": selected != business_date,
                    "generated_feature_artifacts": {
                        name: str(root / "operations" / "feature_artifacts" / selected / name)
                        for name in (
                            "candidate_features.parquet",
                            "opportunity_feature_input.parquet",
                            "position_feature_input.parquet",
                            "capital_policy_input.parquet",
                        )
                    },
                }
            ),
            encoding="utf-8",
        )
    return root


def _make_q3b_failed_execution_fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    root = tmp_path / ".runtime"
    reports = tmp_path / "reports"
    run_id = "runtime-test-q3b-fixture"
    run_dir = reports / "runs" / run_id
    (root / "persistent_ledger").mkdir(parents=True)
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "runtime_state" / "current_state").mkdir(parents=True)
    (root / "runtime_state" / "historical_broker" / "2023-06-08").mkdir(parents=True)
    state = {
        "schema_version": "1",
        "environment": "historical",
        "as_of": "2023-06-07",
        "business_date": "2023-06-07",
        "cash": 437870.0,
        "buying_power": 437870.0,
        "positions": [
            {"symbol": f"S{i}", "quantity": 100.0, "average_price": 10.0, "market_value": 1000.0}
            for i in range(5)
        ],
        "runtime_owned_projection": {
            "projection_status": "PASS",
            "applied_execution_dedup_keys": ["runtime_v2_execution_equivalent:prior"],
        },
    }
    _write_json(root / "persistent_ledger" / "state.json", state)
    _append_jsonl(
        root / "persistent_ledger" / "orders.jsonl",
        [
            {"record_id": "prior-order", "dedup_key": "prior-order", "business_date": "2023-06-07"},
            {"record_id": "submit-1", "dedup_key": "submit-1", "business_date": "2023-06-08", "source": "runtime_v2_submit_pipeline"},
            {"record_id": "exec-order-1", "dedup_key": "exec-order-1", "created_at": "2023-06-08", "source": "runtime_v2_execution_readonly_simulation"},
        ],
    )
    _append_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {
                "record_id": f"failed-exec-{i}",
                "dedup_key": f"runtime_v2_execution_equivalent:failed-{i}",
                "business_date": "2023-06-08",
                "source": "runtime_v2_execution_readonly",
                "symbol": str(i),
            }
            for i in range(4)
        ],
    )
    _append_jsonl(
        root / "persistent_ledger" / "positions.jsonl",
        [
            {"record_id": "prior-position", "dedup_key": "prior-position", "as_of": "2023-06-07"},
            {"record_id": "failed-position", "dedup_key": "failed-position", "as_of": "2023-06-08"},
        ],
    )
    _append_jsonl(
        root / "persistent_ledger" / "cash.jsonl",
        [
            {"record_id": "prior-cash", "dedup_key": "prior-cash", "as_of": "2023-06-07", "cash": 437870.0},
            {"record_id": "failed-cash", "dedup_key": "failed-cash", "as_of": "2023-06-08", "cash": -46930.0},
        ],
    )
    _append_jsonl(
        root / "persistent_ledger" / "events.jsonl",
        [{"record_id": "failed-event", "dedup_key": "failed-event", "created_at": "2023-06-08"}],
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "pending_plan_id": "pending-2023-06-08-failed",
            "state": "CONSUMED",
            "target_session_date": "2023-06-08",
            "items": [{"pending_item_id": "item-1", "state": "CONSUMED"}],
        },
    )
    _write_json(
        root / "runtime_state" / "current_state.json",
        {"schema_version": "runtime_v2_current_apply_state_v1", "business_date": "2023-06-08", "state": "CURRENT_STATE_LOADED"},
    )
    _write_json(root / "runtime_state" / "historical_broker" / "2023-06-08" / "failed.json", {"status": "ACCEPTED"})
    _write_json(
        run_dir / "run_state.json",
        {
            "schema_version": "runtime_test_run_state_v1",
            "run_id": run_id,
            "profile_id": "historical-smoke",
            "status": "HALT",
            "completed_business_days": ["2023-06-07"],
            "completed_jobs": [
                {"business_date": "2023-06-07", "job": "execution", "exit_code": 0},
                {"business_date": "2023-06-08", "job": "market_refresh", "exit_code": 0},
                {"business_date": "2023-06-08", "job": "data_readiness", "exit_code": 0},
                {"business_date": "2023-06-08", "job": "morning", "exit_code": 0},
                {"business_date": "2023-06-08", "job": "sell_planning", "exit_code": 0},
                {"business_date": "2023-06-08", "job": "submit", "exit_code": 0},
                {"business_date": "2023-06-08", "job": "execution", "exit_code": 20},
            ],
            "next_job": "2023-06-08:execution",
            "source_baseline": {},
        },
    )
    _write_json(
        run_dir / "daily" / "2023-06-07" / "execution" / "current_apply_evidence.json",
        {
            "current_hash": "sha256:prior-current",
            "current_version": "current-prior",
            "runtime_state_version": "runtime-state-prior",
            "execution_references": ["prior"],
        },
    )
    _write_json(run_dir / "daily" / "2023-06-08" / "execution" / "runtime_manifest.json", {"final_state": "REVIEW_REQUIRED"})
    return root, reports, run_id


def _make_l21t_stale_pending_fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    root = tmp_path / ".runtime"
    reports = tmp_path / "reports"
    run_id = "runtime-test-stale-pending-fixture"
    run_dir = reports / "runs" / run_id
    (root / "persistent_ledger").mkdir(parents=True)
    (root / "pending_order_plan").mkdir(parents=True)
    state = {
        "schema_version": "1",
        "environment": "historical",
        "as_of": "2023-06-09",
        "business_date": "2023-06-09",
        "cash": 609670.0,
        "buying_power": 609670.0,
        "positions": [
            {"symbol": "94320", "quantity": 1200.0, "average_price": 158.4, "market_value": 190000.0},
            {"symbol": "21340", "quantity": 1500.0, "average_price": 13.2, "market_value": 30000.0},
            {"symbol": "76470", "quantity": 2700.0, "average_price": 25.0, "market_value": 92360.0},
        ],
    }
    _write_json(root / "persistent_ledger" / "state.json", state)
    for name in ("orders.jsonl", "executions.jsonl", "positions.jsonl", "cash.jsonl", "events.jsonl"):
        (root / "persistent_ledger" / name).write_text("", encoding="utf-8")
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "pending_plan_id": "pending-strategy-plan-historical-2023-06-12-c5095866647c8ae8",
            "state": "REVIEW_REQUIRED",
            "plan_created_date": "2023-06-12",
            "target_session_date": "2023-06-12",
            "approved_item_ids": [],
            "review_required_buy_item_ids": ["strategy-333b4929b4bedbe3e52d"],
            "review_scope": "BUY_ITEM_SCOPED_REVIEW",
            "sell_continuation_allowed": True,
            "items": [
                {
                    "pending_item_id": "strategy-333b4929b4bedbe3e52d",
                    "symbol": "59550",
                    "side": "BUY",
                    "quantity": 1000.0,
                    "state": "REVIEW_REQUIRED",
                    "approved": False,
                    "feasibility_status": "REVIEW_REQUIRED",
                    "item_review_reason": "reserved notional exceeds selected_position_amount",
                    "estimated_amount": 108000.0,
                    "reserved_notional": 152000.0,
                }
            ],
        },
    )
    _write_json(
        run_dir / "run_state.json",
        {
            "schema_version": "runtime_test_run_state_v1",
            "run_id": run_id,
            "profile_id": "historical-smoke",
            "status": "HALT",
            "completed_business_days": ["2023-06-05", "2023-06-06", "2023-06-07", "2023-06-08", "2023-06-09"],
            "completed_jobs": [
                {"business_date": "2023-06-09", "job": "execution", "exit_code": 0},
                {"business_date": "2023-06-12", "job": "market_refresh", "exit_code": 0},
                {"business_date": "2023-06-12", "job": "data_readiness", "exit_code": 0},
                {"business_date": "2023-06-12", "job": "morning", "exit_code": 0},
                {"business_date": "2023-06-12", "job": "sell_planning", "exit_code": 20},
            ],
            "halted_at": {"business_date": "2023-06-12", "job": "sell_planning", "exit_code": 20},
            "next_job": "2023-06-12:sell_planning",
            "source_baseline": {},
        },
    )
    _write_json(run_dir / "daily" / "2023-06-12" / "sell_planning" / "runtime_manifest.json", {"final_state": "REVIEW_REQUIRED"})
    return root, reports, run_id


def _make_phase32_ac_partial_submit_fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    root = tmp_path / ".runtime"
    reports = tmp_path / "reports"
    run_id = "runtime-test-phase32-ac-partial-submit"
    run_dir = reports / "runs" / run_id
    pending_plan_id = "pending-strategy-plan-historical-2023-10-11-f650d7dcd8b7c7d7"
    consumed_item_id = "strategy-24ef30251cec051aac6a"
    blocked_item_id = "strategy-b6716e1e95fc9cc0a9aa"
    order_id = "b95f550a15c75dbb6de73a3ef5886b9c79d990825cc42ddddd756a4d356c8733"
    (root / "persistent_ledger").mkdir(parents=True)
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "runtime_state" / "historical_broker" / "2023-10-11").mkdir(parents=True)
    (root / "runtime_state" / "run_manifest" / "2023-10-11").mkdir(parents=True)
    state = {
        "schema_version": "runtime_v2_current_temporal_v1",
        "environment": "historical",
        "as_of": "2023-10-10",
        "business_date": "2023-10-10",
        "cash": 816580.0,
        "buying_power": 816580.0,
        "positions": [
            {"symbol": "66780", "quantity": 100.0},
            {"symbol": "59660", "quantity": 100.0},
            {"symbol": "50280", "quantity": 100.0},
            {"symbol": "92460", "quantity": 100.0, "average_price": 1350.0, "market_value": 135000.0},
        ],
    }
    _write_json(root / "persistent_ledger" / "state.json", state)
    _append_jsonl(
        root / "persistent_ledger" / "orders.jsonl",
        [
            {"record_id": "prior-order", "dedup_key": "prior-order", "business_date": "2023-10-10"},
            {
                "record_id": "ledger-order-submit-eb4911bfbcb7f197",
                "dedup_key": "runtime_v2_submit:submit-command-8d63867bd2f64d35",
                "source": "runtime_v2_submit_pipeline",
                "business_date": "2023-10-11",
                "pending_plan_id": pending_plan_id,
                "pending_item_id": consumed_item_id,
                "symbol": "92460",
                "issue_code_normalization": {"broker_issue_code": "92460"},
                "side": "SELL",
                "quantity": 100.0,
                "status": "ACCEPTED",
                "order_id": order_id,
                "source_decision_id": "rp-2023-10-11-92460-sell_exit-3b430763f0529b62",
                "source_pm_decision_id": "pm-2023-10-11-92460-reduce",
            },
        ],
    )
    for name in ("executions.jsonl", "positions.jsonl", "cash.jsonl", "events.jsonl"):
        (root / "persistent_ledger" / name).write_text("", encoding="utf-8")
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "pending_plan_id": pending_plan_id,
            "state": "REVIEW_REQUIRED",
            "status": "REVIEW_REQUIRED",
            "plan_created_date": "2023-10-11",
            "target_session_date": "2023-10-11",
            "approved_item_ids": [blocked_item_id, consumed_item_id],
            "review_required_buy_item_ids": ["strategy-4c1cff246933bff23312", "strategy-a92ce60a05bb6b2c9cc4"],
            "review_scope": "BUY_ITEM_SCOPED_REVIEW",
            "sell_continuation_allowed": True,
            "items": [
                {"pending_item_id": blocked_item_id, "symbol": "50280", "side": "SELL", "quantity": 100.0, "state": "APPROVED", "approved": True},
                {"pending_item_id": consumed_item_id, "symbol": "92460", "side": "SELL", "quantity": 100.0, "state": "CONSUMED", "approved": True},
                {"pending_item_id": "strategy-4c1cff246933bff23312", "symbol": "38560", "side": "BUY", "quantity": 100.0, "state": "REVIEW_REQUIRED", "approved": False},
                {"pending_item_id": "strategy-a92ce60a05bb6b2c9cc4", "symbol": "76920", "side": "BUY", "quantity": 400.0, "state": "REVIEW_REQUIRED", "approved": False},
            ],
        },
    )
    broker_path = root / "runtime_state" / "historical_broker" / "2023-10-11" / "92460.json"
    _write_json(
        broker_path,
        {
            "status": "ACCEPTED",
            "target_session_date": "2023-10-11",
            "pending_plan_id": pending_plan_id,
            "pending_item_id": consumed_item_id,
            "source_decision_id": "rp-2023-10-11-92460-sell_exit-3b430763f0529b62",
            "source_decision_type": "SELL_EXIT",
            "source_pm_decision_id": "pm-2023-10-11-92460-reduce",
            "order_plan_item_id": consumed_item_id,
            "position_campaign_id": "pc-92460",
            "campaign_id": "pc-92460",
            "symbol": "92460",
            "side": "SELL",
            "quantity": 100.0,
            "order_identity": order_id,
            "execution_identity": "execution-92460-2023-10-11",
            "fill_datetime": "2023-10-11T15:00:00+09:00",
            "fill_date": "2023-10-11",
            "fill_price": 1350.0,
            "cash_effect": 135000.0,
        },
    )
    submit_manifest = {
        "final_state": "REVIEW_REQUIRED",
        "submitted_count": 1,
        "blocked_count": 1,
        "submit_guard_item_evidence": [
            {"pending_item_id": consumed_item_id, "symbol": "92460", "status": "PASS", "guard_decision": "PASS"},
            {
                "pending_item_id": blocked_item_id,
                "symbol": "50280",
                "status": "REVIEW_REQUIRED",
                "guard_decision": "BLOCKED",
                "violated_policy": "corporate_action_adjustment_authority",
            },
        ],
    }
    _write_json(root / "runtime_state" / "run_manifest" / "2023-10-11" / "runtime-v2-submit.json", submit_manifest)
    _write_json(run_dir / "daily" / "2023-10-11" / "submit" / "runtime_manifest.json", submit_manifest)
    _write_json(
        run_dir / "run_state.json",
        {
            "schema_version": "runtime_test_run_state_v1",
            "run_id": run_id,
            "profile_id": "historical-smoke",
            "status": "HALT",
            "completed_business_days": ["2023-10-10"],
            "completed_jobs": [
                {"business_date": "2023-10-10", "job": "execution", "exit_code": 0},
                {"business_date": "2023-10-11", "job": "market_refresh", "exit_code": 0},
                {"business_date": "2023-10-11", "job": "data_readiness", "exit_code": 0},
                {"business_date": "2023-10-11", "job": "morning", "exit_code": 0},
                {"business_date": "2023-10-11", "job": "sell_planning", "exit_code": 0},
                {"business_date": "2023-10-11", "job": "submit", "exit_code": 20},
            ],
            "halted_at": {"business_date": "2023-10-11", "job": "submit", "exit_code": 20},
            "next_job": "2023-10-11:submit",
            "halt_summary": {"root_reason": "corporate_action_event_not_resolved"},
            "source_baseline": {},
        },
    )
    return root, reports, run_id


def _make_phase32_ae_partial_submit_finalization_fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    root, reports, run_id = _make_phase32_ac_partial_submit_fixture(tmp_path)
    run_dir = reports / "runs" / run_id
    old_plan_id = "pending-strategy-plan-historical-2023-10-11-f650d7dcd8b7c7d7"
    new_plan_id = "pending-strategy-plan-historical-2023-10-11-1340bca9c0bec9b6"
    consumed_item_id = "strategy-24ef30251cec051aac6a"
    order_id = "b95f550a15c75dbb6de73a3ef5886b9c79d990825cc42ddddd756a4d356c8733"
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "pending_plan_id": new_plan_id,
            "state": "REVIEW_REQUIRED",
            "status": "REVIEW_REQUIRED",
            "plan_created_date": "2023-10-11",
            "target_session_date": "2023-10-11",
            "approved_item_ids": [],
            "approved_sell_item_ids": [],
            "approved_buy_item_ids": [],
            "review_required_buy_item_ids": ["strategy-4e98c1cb77def51708c5", "strategy-c5d39910c741daebcd6d"],
            "review_scope": "AUTHORITY_UNKNOWN_REVIEW",
            "sell_continuation_allowed": False,
            "items": [
                {
                    "pending_item_id": "strategy-3da5436ff9481d6af209",
                    "symbol": "50280",
                    "side": "SELL",
                    "quantity": 100.0,
                    "state": "REVIEW_REQUIRED",
                    "approved": False,
                    "item_review_reason": "corporate_action_event_not_resolved",
                    "source_pm_decision_id": "pm-2023-10-11-50280-reduce",
                },
                {
                    "pending_item_id": "strategy-d1be135b15c4cc97433a",
                    "symbol": "92460",
                    "side": "SELL",
                    "quantity": 100.0,
                    "state": "REVIEW_REQUIRED",
                    "approved": False,
                    "batch_submit_status": "BLOCKED_BY_BATCH_REVIEW",
                    "source_pm_decision_id": "pm-2023-10-11-92460-reduce",
                },
                {
                    "pending_item_id": "strategy-4e98c1cb77def51708c5",
                    "symbol": "38560",
                    "side": "BUY",
                    "quantity": 100.0,
                    "state": "REVIEW_REQUIRED",
                    "approved": False,
                },
                {
                    "pending_item_id": "strategy-c5d39910c741daebcd6d",
                    "symbol": "76920",
                    "side": "BUY",
                    "quantity": 400.0,
                    "state": "REVIEW_REQUIRED",
                    "approved": False,
                },
            ],
        },
    )
    _write_json(
        run_dir / "daily" / "2023-10-11" / "morning" / "runtime_manifest.json",
        {
            "business_date": "2023-10-11",
            "job": "morning",
            "final_state": "PASS",
            "final_safety_status": "READY",
            "final_safety_reason": "historical_neutral_no_event_safety_ready",
        },
    )
    _write_json(
        run_dir / "plan.json",
        {
            "schema_version": "runtime_test_plan_v1",
            "run_id": run_id,
            "business_dates": [
                {"business_date": "2023-10-10", "jobs": [{"job": "execution", "command": []}]},
                {
                    "business_date": "2023-10-11",
                    "jobs": [
                        {"job": "morning", "command": []},
                        {"job": "sell_planning", "command": []},
                        {"job": "submit", "command": []},
                        {"job": "execution", "command": []},
                    ],
                },
                {"business_date": "2023-10-12", "jobs": [{"job": "market_refresh", "command": []}]},
            ],
        },
    )
    _write_json(
        run_dir / "run_state.json",
        {
            "schema_version": "runtime_test_run_state_v1",
            "run_id": run_id,
            "profile_id": "historical-smoke",
            "status": "HALT",
            "completed_business_days": ["2023-10-10"],
            "completed_jobs": [
                {"business_date": "2023-10-10", "job": "execution", "exit_code": 0},
                {"business_date": "2023-10-11", "job": "morning", "exit_code": 0},
                {"business_date": "2023-10-11", "job": "sell_planning", "exit_code": 20},
            ],
            "halted_at": {"business_date": "2023-10-11", "job": "sell_planning", "exit_code": 20},
            "next_job": "2023-10-11:sell_planning",
            "halt_summary": {"root_reason": "historical_safety_temporal_authority_missing"},
            "scoped_partial_submit_recovery": {
                "schema_version": "runtime_test_scoped_partial_submit_recovery_state_v1",
                "recovery_id": "scoped-partial-submit-7fc8aca4bb8fef42",
                "business_date": "2023-10-11",
                "rewind_to_job": "morning",
                "status": "RECOVERY_APPLIED",
                "evidence_path": str(run_dir / "recovery" / "scoped-partial-submit-7fc8aca4bb8fef42" / "recovery_evidence.json"),
                "preserved_accepted_item_ids": [consumed_item_id],
                "preserved_order_ids": [order_id],
                "excluded_from_resubmit_item_ids": [consumed_item_id],
                "replay_contract": "submit_pipeline_existing_item_submission_reconciliation",
                "superseded_pending_plan_id": old_plan_id,
            },
            "source_baseline": {},
        },
    )
    return root, reports, run_id


def _write_accepted_generation_authority(root: Path, *, business_date: str) -> None:
    generation_id = "phase26-step10r4-fixture-generation"
    generation_dir = root / "ai_lifecycle" / "generations" / generation_id
    generation_dir.mkdir(parents=True, exist_ok=True)
    candidate_model = generation_dir / "candidate_model.bin"
    opportunity_model = generation_dir / "opportunity_model.bin"
    candidate_model.write_bytes(b"phase26-step10r4-candidate-model")
    opportunity_model.write_bytes(b"phase26-step10r4-opportunity-model")
    manifest = {
        "schema_version": "runtime_v2_accepted_generation_manifest_v1",
        "generation_id": generation_id,
        "accepted_generation_id": generation_id,
        "status": "COMMITTED",
        "authority_decision": "business-date-bound Accepted Generation ledger",
        "accepted_at": f"{business_date}T00:00:00+00:00",
        "effective_from": f"{business_date}T00:00:00+00:00",
        "candidate_member": {
            "role": "candidate_model",
            "artifact_path": "candidate_model.bin",
            "model_hash": _sha256(candidate_model),
        },
        "opportunity_member": {
            "role": "opportunity_model",
            "artifact_path": "opportunity_model.bin",
            "model_hash": _sha256(opportunity_model),
        },
        "freshness_metadata": {
            "field_sources": {
                "candidate_training_cutoff": {"value": "2026-06-30"},
                "opportunity_training_cutoff": {"value": "2026-06-30"},
                "candidate_calibration_cutoff": {"value": "2026-06-30"},
                "opportunity_calibration_cutoff": {"value": "2026-06-30"},
                "validation_cutoff": {"value": "2026-06-30"},
            },
        },
        "runtime_baseline": {"source": "phase26_step10r4_test_fixture"},
    }
    manifest["aggregate_hash"] = _stable_hash(manifest)
    manifest_path = generation_dir / "accepted_generation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    pointer = {
        "schema_version": "runtime_v2_accepted_generation_pointer_v1",
        "transaction_state": "COMMITTED",
        "accepted_generation_id": generation_id,
        "bundle_manifest_path": str(Path("ai_lifecycle") / "generations" / generation_id / "accepted_generation_manifest.json"),
        "aggregate_hash": manifest["aggregate_hash"],
        "accepted_at": manifest["accepted_at"],
        "effective_from": manifest["effective_from"],
    }
    (root / "runtime_state" / "accepted_buy_ai_bundle.json").write_text(json.dumps(pointer, sort_keys=True), encoding="utf-8")
    history_dir = root / "ai_lifecycle" / "authority_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    (history_dir / "accepted_generation_history.jsonl").write_text(
        json.dumps(
            {
                "event": "ACCEPTED_GENERATION_COMMITTED",
                "generation_id": generation_id,
                "bundle_manifest_path": str(Path("ai_lifecycle") / "generations" / generation_id / "accepted_generation_manifest.json"),
                "accepted_at": manifest["accepted_at"],
                "effective_from": manifest["effective_from"],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _append_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def call_main(module, args: list[str], capsys: pytest.CaptureFixture[str]) -> dict:
    exit_code = module.main(args + ["--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    payload["_exit_code"] = exit_code
    return payload


def test_phase17_k_status_is_read_only(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    before = runner.directory_hash(root)
    payload = call_main(runner, ["status", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports")], capsys)
    after = runner.directory_hash(root)
    assert payload["status"] == "PASS"
    assert before == after


def test_phase20_h_run_status_matches_status_json_and_exit_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    args = ["--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports")]

    run_status = call_main(runner, ["run-status", *args], capsys)
    status = call_main(runner, ["status", *args], capsys)

    assert run_status["_exit_code"] == status["_exit_code"] == runner.EXIT_PASS
    assert run_status == status


def test_phase20_h_run_status_human_output_matches_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    args = ["--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports")]

    assert runner.main(["run-status", *args]) == runner.EXIT_PASS
    run_status_output = capsys.readouterr().out
    assert runner.main(["status", *args]) == runner.EXIT_PASS
    status_output = capsys.readouterr().out

    assert run_status_output == status_output


def test_phase29_l21t_q3b_failed_execution_recovery_dry_run_detects_scope(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root, reports, run_id = _make_q3b_failed_execution_fixture(tmp_path)

    payload = call_main(
        runner,
        [
            "recover-failed-execution",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(reports),
            "--run-id",
            run_id,
            "--business-date",
            "2023-06-08",
            "--dry-run",
        ],
        capsys,
    )

    assert payload["_exit_code"] == runner.EXIT_PASS, (
        payload.get("reason"),
        (payload.get("execution_result") or {}).get("runtime_owned_projection_reason"),
        (payload.get("execution_result") or {}).get("transaction_validation_reason"),
    )
    assert payload["status"] == "DRY_RUN"
    assert payload["dry_run_no_mutation"] is True
    assert len(payload["failed_ledger_rows"]["executions"]) == 4
    assert payload["superseded_pending_plan_id"] == "pending-2023-06-08-failed"
    assert payload["source_recovery_point"]["cash"] == 437870.0


def test_phase29_l21t_q3b_failed_execution_recovery_rewinds_and_preserves_prior_ledger(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root, reports, run_id = _make_q3b_failed_execution_fixture(tmp_path)
    before_prior_order = (root / "persistent_ledger" / "orders.jsonl").read_text(encoding="utf-8").splitlines()[0]

    payload = call_main(
        runner,
        [
            "recover-failed-execution",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(reports),
            "--run-id",
            run_id,
            "--business-date",
            "2023-06-08",
            "--confirm",
            CONFIRM_FLAG,
        ],
        capsys,
    )
    run_state = json.loads((reports / "runs" / run_id / "run_state.json").read_text(encoding="utf-8"))
    executions_text = (root / "persistent_ledger" / "executions.jsonl").read_text(encoding="utf-8")
    orders_lines = (root / "persistent_ledger" / "orders.jsonl").read_text(encoding="utf-8").splitlines()
    pending = json.loads((root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    recovery_dir = reports / "runs" / run_id / "recovery" / payload["recovery_id"]

    assert payload["_exit_code"] == runner.EXIT_PASS, (
        payload.get("reason"),
        (payload.get("execution_result") or {}).get("runtime_owned_projection_reason"),
        (payload.get("execution_result") or {}).get("transaction_validation_reason"),
    )
    assert payload["status"] == "PASS"
    assert run_state["next_job"] == "2023-06-08:morning"
    assert run_state["status"] == "HALT"
    assert all(
        not (record.get("business_date") == "2023-06-08" and record.get("job") in {"morning", "sell_planning", "submit", "execution"})
        for record in run_state["completed_jobs"]
    )
    assert before_prior_order == orders_lines[0]
    assert "2023-06-08" not in executions_text
    assert pending["state"] == "EMPTY"
    assert pending["superseded_pending_plan_id"] == "pending-2023-06-08-failed"
    assert not (root / "runtime_state" / "historical_broker" / "2023-06-08").exists()
    assert (recovery_dir / "failed_executions.json").is_file()
    assert (recovery_dir / "failed_pending_order_plan.json").is_file()


def test_phase29_l21t_q1b_recovery_rewinds_submit_only_precommit_halt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root, reports, run_id = _make_q3b_failed_execution_fixture(tmp_path)
    _append_jsonl(root / "persistent_ledger" / "executions.jsonl", [])
    _append_jsonl(root / "persistent_ledger" / "positions.jsonl", [{"record_id": "prior-position", "dedup_key": "prior-position", "as_of": "2023-06-07"}])
    _append_jsonl(root / "persistent_ledger" / "cash.jsonl", [{"record_id": "prior-cash", "dedup_key": "prior-cash", "as_of": "2023-06-07", "cash": 437870.0}])
    _append_jsonl(root / "persistent_ledger" / "events.jsonl", [])

    payload = call_main(
        runner,
        [
            "recover-failed-execution",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(reports),
            "--run-id",
            run_id,
            "--business-date",
            "2023-06-08",
            "--confirm",
            CONFIRM_FLAG,
        ],
        capsys,
    )
    run_state = json.loads((reports / "runs" / run_id / "run_state.json").read_text(encoding="utf-8"))
    orders_text = (root / "persistent_ledger" / "orders.jsonl").read_text(encoding="utf-8")
    pending = json.loads((root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))

    assert payload["_exit_code"] == runner.EXIT_PASS
    assert payload["status"] == "PASS"
    assert payload["recovery_classification"] == "SUBMIT_ONLY_PRECOMMIT_HALT"
    assert payload["failed_execution_dedup_keys"] == []
    assert run_state["next_job"] == "2023-06-08:morning"
    assert "2023-06-08" not in orders_text
    assert pending["state"] == "EMPTY"


def test_phase29_l21t_q3b_failed_execution_recovery_refuses_coherent_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root, reports, run_id = _make_q3b_failed_execution_fixture(tmp_path)
    _append_jsonl(root / "persistent_ledger" / "executions.jsonl", [])

    payload = call_main(
        runner,
        [
            "recover-failed-execution",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(reports),
            "--run-id",
            run_id,
            "--business-date",
            "2023-06-08",
            "--dry-run",
        ],
        capsys,
    )

    assert payload["_exit_code"] == runner.EXIT_PRECONDITION_FAILURE
    assert payload["status"] == "PRECONDITION_FAILURE"
    assert "expected four failed execution rows or submit-only precommit halt rows" in payload["errors"]


def test_phase29_l21t_t_stale_pending_recovery_dry_run_detects_scope(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root, reports, run_id = _make_l21t_stale_pending_fixture(tmp_path)

    payload = call_main(
        runner,
        [
            "recover-stale-pending",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(reports),
            "--run-id",
            run_id,
            "--business-date",
            "2023-06-12",
            "--rewind-to-job",
            "morning",
            "--expected-pending-plan-id",
            "pending-strategy-plan-historical-2023-06-12-c5095866647c8ae8",
            "--dry-run",
        ],
        capsys,
    )

    assert payload["_exit_code"] == runner.EXIT_PASS
    assert payload["status"] == "DRY_RUN"
    assert payload["dry_run_no_mutation"] is True
    assert payload["recovery_classification"] == "STALE_REVIEW_REQUIRED_PENDING_REPLAY"
    assert payload["source_recovery_point"]["business_date"] == "2023-06-09"
    assert payload["stale_pending"]["pending_plan_id"] == "pending-strategy-plan-historical-2023-06-12-c5095866647c8ae8"
    assert payload["stale_pending"]["review_scope"] == "BUY_ITEM_SCOPED_REVIEW"


def test_phase29_l21t_t_stale_pending_recovery_rewinds_and_retires_pending(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root, reports, run_id = _make_l21t_stale_pending_fixture(tmp_path)
    before_state = (root / "persistent_ledger" / "state.json").read_text(encoding="utf-8")

    payload = call_main(
        runner,
        [
            "recover-stale-pending",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(reports),
            "--run-id",
            run_id,
            "--business-date",
            "2023-06-12",
            "--rewind-to-job",
            "morning",
            "--confirm",
            CONFIRM_FLAG,
        ],
        capsys,
    )
    run_state = json.loads((reports / "runs" / run_id / "run_state.json").read_text(encoding="utf-8"))
    pending = json.loads((root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    recovery_dir = reports / "runs" / run_id / "recovery" / payload["recovery_id"]

    assert payload["_exit_code"] == runner.EXIT_PASS
    assert payload["status"] == "PASS"
    assert payload["run_state_rewind_from"] == "2023-06-12:sell_planning"
    assert payload["run_state_rewind_to"] == "2023-06-12:morning"
    assert run_state["status"] == "HALT"
    assert run_state["next_job"] == "2023-06-12:morning"
    assert all(
        not (record.get("business_date") == "2023-06-12" and record.get("job") in {"morning", "sell_planning", "submit", "execution"})
        for record in run_state["completed_jobs"]
    )
    assert pending["state"] == "EMPTY"
    assert pending["superseded_pending_plan_id"] == "pending-strategy-plan-historical-2023-06-12-c5095866647c8ae8"
    assert (root / "persistent_ledger" / "state.json").read_text(encoding="utf-8") == before_state
    assert (recovery_dir / "stale_pending_order_plan.json").is_file()


def test_phase29_l21t_t_stale_pending_recovery_refuses_existing_target_ledger_rows(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root, reports, run_id = _make_l21t_stale_pending_fixture(tmp_path)
    _append_jsonl(root / "persistent_ledger" / "orders.jsonl", [{"record_id": "order-2023-06-12", "business_date": "2023-06-12"}])

    payload = call_main(
        runner,
        [
            "recover-stale-pending",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(reports),
            "--run-id",
            run_id,
            "--business-date",
            "2023-06-12",
            "--dry-run",
        ],
        capsys,
    )

    assert payload["_exit_code"] == runner.EXIT_PRECONDITION_FAILURE
    assert payload["status"] == "PRECONDITION_FAILURE"
    assert "target business date already has ledger rows; use failed-execution recovery or audit first" in payload["errors"]


def test_phase32_ac_partial_submit_recovery_dry_run_is_deterministic_and_read_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root, reports, run_id = _make_phase32_ac_partial_submit_fixture(tmp_path)
    before_runtime_hash = runner.directory_hash(root)
    before_run_state = (reports / "runs" / run_id / "run_state.json").read_text(encoding="utf-8")

    args = [
        "recover-partial-submit",
        "--runtime-root",
        str(root),
        "--evidence-root",
        str(reports),
        "--run-id",
        run_id,
        "--business-date",
        "2023-10-11",
        "--dry-run",
    ]
    first = call_main(runner, args, capsys)
    second = call_main(runner, args, capsys)

    assert first["_exit_code"] == second["_exit_code"] == runner.EXIT_PASS
    assert first["status"] == second["status"] == "DRY_RUN"
    assert first["dry_run_no_mutation"] is True
    assert first["recovery_id"] == second["recovery_id"]
    assert first["preserved_accepted_item_ids"] == ["strategy-24ef30251cec051aac6a"]
    assert first["excluded_from_resubmit_item_ids"] == ["strategy-24ef30251cec051aac6a"]
    assert "strategy-b6716e1e95fc9cc0a9aa" in first["regenerated_item_ids"]
    assert first["target_ledger_counts"] == {"orders": 1, "executions": 0, "positions": 0, "cash": 0, "events": 0}
    assert first["submit_guard_block_evidence"][0]["violated_policy"] == "corporate_action_adjustment_authority"
    assert runner.directory_hash(root) == before_runtime_hash
    assert (reports / "runs" / run_id / "run_state.json").read_text(encoding="utf-8") == before_run_state


def test_phase32_ac_partial_submit_recovery_preserves_accepted_order_and_rewinds_pending(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root, reports, run_id = _make_phase32_ac_partial_submit_fixture(tmp_path)
    orders_before = (root / "persistent_ledger" / "orders.jsonl").read_text(encoding="utf-8")
    broker_before = (root / "runtime_state" / "historical_broker" / "2023-10-11" / "92460.json").read_text(encoding="utf-8")

    payload = call_main(
        runner,
        [
            "recover-partial-submit",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(reports),
            "--run-id",
            run_id,
            "--business-date",
            "2023-10-11",
            "--confirm",
            CONFIRM_FLAG,
        ],
        capsys,
    )
    run_state = json.loads((reports / "runs" / run_id / "run_state.json").read_text(encoding="utf-8"))
    pending = json.loads((root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    recovery_dir = reports / "runs" / run_id / "recovery" / payload["recovery_id"]

    assert payload["_exit_code"] == runner.EXIT_PASS
    assert payload["status"] == "PASS"
    assert payload["run_state_rewind_from"] == "2023-10-11:submit"
    assert payload["run_state_rewind_to"] == "2023-10-11:morning"
    assert (root / "persistent_ledger" / "orders.jsonl").read_text(encoding="utf-8") == orders_before
    assert (root / "runtime_state" / "historical_broker" / "2023-10-11" / "92460.json").read_text(encoding="utf-8") == broker_before
    assert pending["state"] == "EMPTY"
    assert pending["superseded_pending_plan_id"] == "pending-strategy-plan-historical-2023-10-11-f650d7dcd8b7c7d7"
    assert pending["preserved_accepted_item_ids"] == ["strategy-24ef30251cec051aac6a"]
    assert pending["replay_contract"] == "submit_pipeline_existing_item_submission_reconciliation"
    assert run_state["status"] == "HALT"
    assert run_state["next_job"] == "2023-10-11:morning"
    assert run_state["completed_business_days"] == ["2023-10-10"]
    assert all(
        not (record.get("business_date") == "2023-10-11" and record.get("job") in {"morning", "sell_planning", "submit", "execution"})
        for record in run_state["completed_jobs"]
    )
    assert run_state["scoped_partial_submit_recovery"]["excluded_from_resubmit_item_ids"] == ["strategy-24ef30251cec051aac6a"]
    assert (recovery_dir / "partial_submit_pending_order_plan.json").is_file()
    assert (recovery_dir / "preserved_orders.json").is_file()
    assert (recovery_dir / "preserved_historical_broker" / "92460.json").is_file()


def test_phase32_ac_partial_submit_recovery_after_apply_fails_closed_as_already_recovered(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root, reports, run_id = _make_phase32_ac_partial_submit_fixture(tmp_path)
    call_main(
        runner,
        [
            "recover-partial-submit",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(reports),
            "--run-id",
            run_id,
            "--business-date",
            "2023-10-11",
            "--confirm",
            CONFIRM_FLAG,
        ],
        capsys,
    )

    second = call_main(
        runner,
        [
            "recover-partial-submit",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(reports),
            "--run-id",
            run_id,
            "--business-date",
            "2023-10-11",
            "--dry-run",
        ],
        capsys,
    )

    assert second["_exit_code"] == runner.EXIT_PRECONDITION_FAILURE
    assert second["status"] == "PRECONDITION_FAILURE"
    assert "partial submit recovery already applied" in second["errors"]


def test_phase32_ac_partial_submit_recovery_rejects_broker_order_mismatch(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root, reports, run_id = _make_phase32_ac_partial_submit_fixture(tmp_path)
    broker_path = root / "runtime_state" / "historical_broker" / "2023-10-11" / "92460.json"
    broker = json.loads(broker_path.read_text(encoding="utf-8"))
    broker["order_identity"] = "different-order"
    _write_json(broker_path, broker)

    payload = call_main(
        runner,
        [
            "recover-partial-submit",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(reports),
            "--run-id",
            run_id,
            "--business-date",
            "2023-10-11",
            "--dry-run",
        ],
        capsys,
    )

    assert payload["_exit_code"] == runner.EXIT_PRECONDITION_FAILURE
    assert payload["status"] == "PRECONDITION_FAILURE"
    assert "historical broker accepted evidence missing or mismatched for target order row" in payload["errors"]


def test_phase32_ae_partial_submit_finalization_dry_run_is_read_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root, reports, run_id = _make_phase32_ae_partial_submit_finalization_fixture(tmp_path)
    before_runtime_hash = runner.directory_hash(root)
    before_run_state = (reports / "runs" / run_id / "run_state.json").read_text(encoding="utf-8")

    payload = call_main(
        runner,
        [
            "finalize-partial-submit-day",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(reports),
            "--run-id",
            run_id,
            "--business-date",
            "2023-10-11",
            "--dry-run",
        ],
        capsys,
    )

    assert payload["_exit_code"] == runner.EXIT_PASS
    assert payload["status"] == "DRY_RUN"
    assert payload["dry_run_no_mutation"] is True
    assert payload["preserved_order_ids"] == ["b95f550a15c75dbb6de73a3ef5886b9c79d990825cc42ddddd756a4d356c8733"]
    assert payload["preserved_accepted_item_ids"] == ["strategy-24ef30251cec051aac6a"]
    assert "strategy-3da5436ff9481d6af209" in payload["review_item_ids_not_executed"]
    assert payload["safety_authority"]["status"] == "PASS"
    assert runner.directory_hash(root) == before_runtime_hash
    assert (reports / "runs" / run_id / "run_state.json").read_text(encoding="utf-8") == before_run_state


def test_phase32_ae_partial_submit_finalization_executes_preserved_order_once(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root, reports, run_id = _make_phase32_ae_partial_submit_finalization_fixture(tmp_path)
    order_id = "b95f550a15c75dbb6de73a3ef5886b9c79d990825cc42ddddd756a4d356c8733"

    payload = call_main(
        runner,
        [
            "finalize-partial-submit-day",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(reports),
            "--run-id",
            run_id,
            "--business-date",
            "2023-10-11",
            "--confirm",
            CONFIRM_FLAG,
        ],
        capsys,
    )
    run_state = json.loads((reports / "runs" / run_id / "run_state.json").read_text(encoding="utf-8"))
    pending = json.loads((root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    state = json.loads((root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    executions = [
        row
        for row in _read_jsonl(root / "persistent_ledger" / "executions.jsonl")
        if row.get("business_date") == "2023-10-11"
    ]
    raw_submit_orders = [
        row
        for row in _read_jsonl(root / "persistent_ledger" / "orders.jsonl")
        if row.get("business_date") == "2023-10-11" and row.get("order_id") == order_id
    ]

    assert payload["_exit_code"] == runner.EXIT_PASS, (
        payload.get("reason"),
        (payload.get("execution_result") or {}).get("runtime_owned_projection_reason"),
        (payload.get("execution_result") or {}).get("transaction_validation_reason"),
    )
    assert payload["status"] == "PASS"
    assert payload["execution_result"]["status"] == "REVIEW_REQUIRED"
    assert payload["execution_result"]["persistent_commit_completed"] is True
    assert payload["execution_result"]["reason"].startswith("reconciliation findings=")
    assert len(raw_submit_orders) == 1
    assert len(executions) == 1
    assert executions[0]["symbol"] == "92460"
    assert executions[0]["side"] == "SELL"
    assert pending["state"] == "CONSUMED"
    assert pending["review_item_ids_not_executed"] == [
        "strategy-3da5436ff9481d6af209",
        "strategy-d1be135b15c4cc97433a",
        "strategy-4e98c1cb77def51708c5",
        "strategy-c5d39910c741daebcd6d",
    ]
    assert "2023-10-11" in run_state["completed_business_days"]
    assert run_state["next_job"] == "2023-10-12:market_refresh"
    assert run_state["partial_submit_day_finalization"]["status"] == "PASS"
    assert all(position.get("symbol") != "92460" for position in state.get("positions", []))
    assert (reports / "runs" / run_id / "daily" / "2023-10-11" / "day_completion" / "day_completion_evidence.json").is_file()


def test_phase32_ae_partial_submit_finalization_rejects_missing_safety_authority(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root, reports, run_id = _make_phase32_ae_partial_submit_finalization_fixture(tmp_path)
    (reports / "runs" / run_id / "daily" / "2023-10-11" / "morning" / "runtime_manifest.json").unlink()

    payload = call_main(
        runner,
        [
            "finalize-partial-submit-day",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(reports),
            "--run-id",
            run_id,
            "--business-date",
            "2023-10-11",
            "--dry-run",
        ],
        capsys,
    )

    assert payload["_exit_code"] == runner.EXIT_PRECONDITION_FAILURE
    assert payload["status"] == "PRECONDITION_FAILURE"
    assert any("historical safety authority missing" in error for error in payload["errors"])


def test_phase26_pf3f_runtime_cli_records_trace_without_fixed_timeout(tmp_path: Path) -> None:
    runner = load_runner()
    trace_path = tmp_path / "subprocess_trace.json"

    completed = runner.run_runtime_cli(
        [sys.executable, "-c", "print('trace-ok')"],
        cwd=tmp_path,
        trace_path=trace_path,
        context={"run_id": "timeout-test", "business_date": "2026-07-21", "job": "market_refresh"},
    )

    assert completed.returncode == 0
    assert completed.stdout.strip() == "trace-ok"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["status"] == "COMPLETED"
    assert trace["timed_out"] is False
    assert trace["formal_stall_timeout_contract"] == "NOT_CONFIGURED"
    assert trace["stall_timeout_seconds"] is None
    assert trace["job"] == "market_refresh"
    assert trace["returncode"] == 0
    assert trace["pid"]
    assert trace["started_at"]
    assert trace["ended_at"]
    assert trace["elapsed_seconds"] >= 0


def test_phase17_k_plan_is_read_only_and_uses_runtime_cli_sequence(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    before = runner.directory_hash(root)
    payload = call_main(
        runner,
        ["plan", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--date-from", "2026-07-06", "--date-to", "2026-07-10"],
        capsys,
    )
    after = runner.directory_hash(root)
    assert payload["status"] == "PASS"
    assert before == after
    assert [job["job"] for job in payload["business_dates"][0]["jobs"]] == list(runner.JOB_SEQUENCE)
    assert payload["business_dates"][2]["feature_date"] == "2026-07-08"
    first_command = payload["business_dates"][0]["jobs"][0]["command"]
    assert "-m" in first_command
    assert runner.RUNTIME_CLI_MODULE in first_command


def test_phase26_pf3h_date_from_overrides_profile_start_for_business_day_window(tmp_path: Path) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    _write_historical_calendar(root, ["2022-07-01", "2022-07-04", "2022-07-05", "2026-07-06"])

    window = runner.resolve_business_window(
        profile=runner.load_profile("historical-smoke"),
        runtime_root=root,
        business_days=3,
        start_date=None,
        date_from="2022-07-01",
        date_to=None,
    )

    assert window["requested_start_date"] == "2022-07-01"
    assert window["profile_start_date"] == "2026-07-06"
    assert window["selected_start_date"] == "2022-07-01"
    assert window["selection_authority"] == "cli_date_from"
    assert window["override_applied"] is True
    assert window["override_reason"] == "cli_date_from_defines_business_days_window_start"
    assert window["resolved_business_dates"] == ["2022-07-01", "2022-07-04", "2022-07-05"]


def test_phase26_pf3h_profile_start_remains_fallback_when_cli_start_absent(tmp_path: Path) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    _write_historical_calendar(root, ["2026-07-06", "2026-07-07", "2026-07-08"])

    window = runner.resolve_business_window(
        profile=runner.load_profile("historical-smoke"),
        runtime_root=root,
        business_days=3,
        start_date=None,
        date_from=None,
        date_to=None,
    )

    assert window["requested_start_date"] == "2026-07-06"
    assert window["profile_start_date"] == "2026-07-06"
    assert window["selected_start_date"] == "2026-07-06"
    assert window["selection_authority"] == "profile_window_date_from"
    assert window["override_applied"] is False
    assert window["override_reason"] == "profile_default_used_when_cli_start_absent"
    assert window["resolved_business_dates"] == ["2026-07-06", "2026-07-07", "2026-07-08"]


def _write_historical_calendar(root: Path, days: list[str]) -> None:
    target = root / "operations" / "jquants" / "historical_snapshots" / "trading_calendar"
    target.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Date": day, "HolDiv": "1"} for day in days]).to_parquet(target / "data.parquet", index=False)
    (target / "validation.json").write_text(json.dumps({"status": "PASS", "reason": "calendar_authority_ready", "max_date": days[-1] if days else ""}), encoding="utf-8")


def _write_validated_calendar_overlay(root: Path, days: list[str]) -> None:
    run_root = root / "market_data_acquisition" / "runs" / "jquants-acquisition-test"
    calendar = run_root / "raw" / "jquants" / "trading_calendar"
    calendar.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Date": day, "HolDiv": "1"} for day in days]).to_parquet(calendar / "data.parquet", index=False)
    final_validation = {
        "status": "PASS",
        "future_date_count": 0,
        "normalized_inventory": {"duplicate_key_count": 0},
        "schema_comparison": {"status": "PASS", "runtime_merge_compatible": True},
        "jquants_lineage": {"status": "PASS"},
    }
    (run_root / "state.json").write_text(json.dumps({"status": "PASS", "acquisition_run_id": run_root.name, "final_validation": final_validation}), encoding="utf-8")
    (run_root / "plan.json").write_text(json.dumps({"status": "PASS", "acquisition_run_id": run_root.name}), encoding="utf-8")


def test_phase23_ag_plan_preserves_requested_window_when_calendar_is_partial(tmp_path: Path) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    _write_historical_calendar(root, ["2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", "2026-07-10", "2026-07-13", "2026-07-14", "2026-07-15"])

    plan = runner.build_plan(
        profile=runner.load_profile("historical-extended-smoke"),
        runtime_root=root,
        evidence_root=tmp_path / "reports",
        business_days=10,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id="runtime-test-window-partial",
    )

    assert plan["requested_business_days"] == 10
    assert plan["resolved_business_day_count"] == 8
    assert plan["window_resolution_status"] == "REVIEW_REQUIRED"
    assert plan["request_conformance_status"] == "NOT_PASS"
    assert plan["unresolved_requested_dates"] == ["2026-07-16", "2026-07-17"]


def test_phase26_pf3c_plan_returns_review_required_for_empty_resolved_window(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    _write_historical_calendar(root, ["2026-07-06", "2026-07-07", "2026-07-08"])

    payload = call_main(
        runner,
        [
            "plan",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(tmp_path / "reports"),
            "--start-date",
            "2026-07-20",
            "--business-days",
            "10",
        ],
        capsys,
    )

    assert payload["_exit_code"] == runner.EXIT_REVIEW_REQUIRED
    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["plan_judgment"] == "PLAN_REVIEW_REQUIRED"
    assert payload["requested_start_date"] == "2026-07-20"
    assert payload["resolved_business_dates"] == []
    assert payload["business_dates"] == []
    assert payload["eligible_dates"] == []
    assert payload["first_eligible_start_date"] is None
    assert payload["operator_ready"] is False
    assert payload["source_readiness"]["blocked_dates"] == payload["unresolved_requested_dates"]
    assert payload["calendar_readiness"]["status"] == "REVIEW_REQUIRED"


def test_phase23_ag_plan_composes_validated_calendar_overlay_for_full_resolution(tmp_path: Path) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    _write_historical_calendar(root, ["2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", "2026-07-10", "2026-07-13", "2026-07-14", "2026-07-15"])
    _write_validated_calendar_overlay(root, ["2026-07-16", "2026-07-17", "2026-07-20"])

    plan = runner.build_plan(
        profile=runner.load_profile("historical-extended-smoke"),
        runtime_root=root,
        evidence_root=tmp_path / "reports",
        business_days=10,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id="runtime-test-window-overlay",
    )

    assert plan["requested_business_days"] == 10
    assert plan["resolved_business_day_count"] == 10
    assert plan["resolved_business_dates"][-2:] == ["2026-07-16", "2026-07-17"]
    assert plan["window_resolution_status"] == "PASS"
    assert plan["calendar_authority"]["overlay_count"] == 1


def test_phase23_ag_plan_ignores_unvalidated_calendar_overlay(tmp_path: Path) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    _write_historical_calendar(root, ["2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", "2026-07-10", "2026-07-13", "2026-07-14", "2026-07-15"])
    run_root = root / "market_data_acquisition" / "runs" / "unvalidated"
    calendar = run_root / "raw" / "jquants" / "trading_calendar"
    calendar.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Date": "2026-07-16", "HolDiv": "1"}, {"Date": "2026-07-17", "HolDiv": "1"}]).to_parquet(calendar / "data.parquet", index=False)

    plan = runner.build_plan(
        profile=runner.load_profile("historical-extended-smoke"),
        runtime_root=root,
        evidence_root=tmp_path / "reports",
        business_days=10,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id="runtime-test-window-unvalidated",
    )

    assert plan["requested_business_days"] == 10
    assert plan["resolved_business_day_count"] == 8
    assert plan["window_resolution_status"] == "REVIEW_REQUIRED"
    assert plan["calendar_authority"]["overlay_count"] == 0


def test_phase17_k_backup_excludes_foundation_and_dry_run_no_mutation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    before = runner.directory_hash(root)
    payload = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--dry-run"], capsys)
    after = runner.directory_hash(root)
    assert payload["status"] == "PASS"
    assert before == after
    excluded = set(payload["excluded_prefixes"])
    assert "artifact_registry" in excluded
    assert "phase9/canonical_data" in excluded
    assert all(not item["path"].startswith("artifact_registry") for item in payload["targets"])


def test_phase17_k_reset_requires_valid_backup(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    payload = call_main(runner, ["reset", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--dry-run"], capsys)
    assert payload["status"] == "PRECONDITION_FAILURE"
    assert payload["_exit_code"] == runner.EXIT_PRECONDITION_FAILURE


def test_fresh_run_accepts_auto_abandon_on_error_option(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    payload = call_main(
        runner,
        ["fresh-run", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--business-days", "1", "--dry-run", "--auto-abandon-on-error"],
        capsys,
    )
    assert payload["status"] == "DRY_RUN"


def test_fresh_run_auto_abandon_writes_standard_abandonment_artifacts(tmp_path: Path) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports"
    run_id = "runtime-test-auto-abandon"
    run_dir = evidence_root / "runs" / run_id
    runner.write_json_atomic(
        run_dir / "run_state.json",
        {
            "schema_version": runner.RUN_STATE_SCHEMA_VERSION,
            "run_id": run_id,
            "profile_id": "historical-smoke",
            "status": "HALT",
            "halted_at": {"business_date": "2026-07-06", "job": "submit", "exit_code": 20},
            "completed_business_days": [],
            "next_job": "submit",
        },
    )

    result = runner._maybe_auto_abandon_fresh_run(
        args=runner.argparse.Namespace(auto_abandon_on_error=True, auto_abandon_reason="test_auto_abandon"),
        profile={"profile_id": "historical-smoke"},
        runtime_root=root,
        evidence_root=evidence_root,
        run_id=run_id,
        final_status="HALT",
        exit_code=runner.EXIT_HALT,
    )

    abandonment = json.loads((run_dir / "abandonment.json").read_text(encoding="utf-8"))
    final_summary = json.loads((run_dir / "final_summary.json").read_text(encoding="utf-8"))
    assert result["performed"] is True
    assert result["reason"] == "halt_run_abandoned_after_fresh_run_error"
    assert abandonment["abandon_reason"] == "test_auto_abandon"
    assert abandonment["abandoned_by"] == "fresh-run"
    assert abandonment["resume_disabled"] is True
    assert final_summary["status"] == "ABANDONED"
    assert final_summary["broker_write"] is False


def _write_phase29_ae_run_state(
    runner,
    *,
    root: Path,
    evidence_root: Path,
    run_id: str,
    status: str = "RUNNING",
    completed_business_days: list[str] | None = None,
) -> Path:
    run_dir = evidence_root / "runs" / run_id
    (run_dir / "daily" / "2026-07-06" / "execution").mkdir(parents=True, exist_ok=True)
    (run_dir / "daily" / "2026-07-06" / "execution" / "runtime_manifest.json").write_text(
        json.dumps({"schema_version": "fixture", "status": "PASS"}),
        encoding="utf-8",
    )
    runner.write_json_atomic(
        run_dir / "run_state.json",
        {
            "schema_version": runner.RUN_STATE_SCHEMA_VERSION,
            "run_id": run_id,
            "profile_id": "historical-smoke",
            "status": status,
            "completed_business_days": completed_business_days if completed_business_days is not None else ["2026-07-05"],
            "completed_jobs": [],
            "next_job": "2026-07-06:submit",
            "source_baseline": runner.source_baseline(root),
        },
    )
    return run_dir


def test_phase29_l21t_ae_stop_running_run_marks_operator_stopped_halt(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    run_id = "runtime-test-ae-stop"
    run_dir = _write_phase29_ae_run_state(runner, root=root, evidence_root=evidence, run_id=run_id)
    daily_hash_before = hashlib.sha256((run_dir / "daily" / "2026-07-06" / "execution" / "runtime_manifest.json").read_bytes()).hexdigest()

    payload = call_main(
        runner,
        ["stop", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", run_id, "--confirm", CONFIRM_FLAG],
        capsys,
    )
    run_state = json.loads((run_dir / "run_state.json").read_text(encoding="utf-8"))
    daily_hash_after = hashlib.sha256((run_dir / "daily" / "2026-07-06" / "execution" / "runtime_manifest.json").read_bytes()).hexdigest()

    assert payload["status"] == "STOPPED"
    assert payload["_exit_code"] == runner.EXIT_PASS
    assert payload["target_status"] == "HALT"
    assert payload["trading_state_mutated"] is False
    assert payload["completed_business_days_changed"] is False
    assert run_state["status"] == "HALT"
    assert run_state["halted_at"]["runtime_test_job_status"] == "OPERATOR_STOPPED"
    assert run_state["halted_at"]["operator_stop"] is True
    assert daily_hash_before == daily_hash_after


def test_phase29_l21t_ae_stop_dry_run_is_read_only(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    run_id = "runtime-test-ae-stop-dry-run"
    run_dir = _write_phase29_ae_run_state(runner, root=root, evidence_root=evidence, run_id=run_id)
    before = (run_dir / "run_state.json").read_text(encoding="utf-8")

    payload = call_main(
        runner,
        ["stop", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", run_id, "--dry-run"],
        capsys,
    )
    after = (run_dir / "run_state.json").read_text(encoding="utf-8")

    assert payload["status"] == "DRY_RUN"
    assert payload["stop_eligible"] is True
    assert payload["dry_run_no_mutation"] is True
    assert before == after


def test_phase29_l21t_ae_stopped_run_can_be_abandoned_and_running_direct_abandon_still_rejected(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    stopped_run_id = "runtime-test-ae-stop-abandon"
    running_run_id = "runtime-test-ae-running-abandon"
    _write_phase29_ae_run_state(runner, root=root, evidence_root=evidence, run_id=stopped_run_id)
    _write_phase29_ae_run_state(runner, root=root, evidence_root=evidence, run_id=running_run_id)

    direct = call_main(
        runner,
        ["abandon", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", running_run_id, "--confirm", CONFIRM_FLAG],
        capsys,
    )
    assert direct["status"] == "PRECONDITION_FAILURE"
    assert "RUNNING run must be halted or stopped" in direct["error"]

    stop = call_main(
        runner,
        ["stop", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", stopped_run_id, "--confirm", CONFIRM_FLAG],
        capsys,
    )
    abandoned = call_main(
        runner,
        ["abandon", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", stopped_run_id, "--confirm", CONFIRM_FLAG],
        capsys,
    )
    assert stop["status"] == "STOPPED"
    assert abandoned["status"] == "ABANDONED"
    assert abandoned["evidence_preserved"] is True


def test_phase29_l21t_ae_double_stop_is_idempotent(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    run_id = "runtime-test-ae-double-stop"
    run_dir = _write_phase29_ae_run_state(runner, root=root, evidence_root=evidence, run_id=run_id)

    first = call_main(
        runner,
        ["stop", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", run_id, "--confirm", CONFIRM_FLAG],
        capsys,
    )
    before_second = (run_dir / "run_state.json").read_text(encoding="utf-8")
    second = call_main(
        runner,
        ["stop", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", run_id, "--confirm", CONFIRM_FLAG],
        capsys,
    )
    after_second = (run_dir / "run_state.json").read_text(encoding="utf-8")

    assert first["status"] == "STOPPED"
    assert second["status"] == "ALREADY_STOPPED"
    assert second["already_stopped"] is True
    assert before_second == after_second


def test_phase29_l21t_ae_stop_rejects_abandoned_completed_and_unknown_runs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    abandoned_id = "runtime-test-ae-abandoned"
    completed_id = "runtime-test-ae-completed"
    abandoned_dir = _write_phase29_ae_run_state(runner, root=root, evidence_root=evidence, run_id=abandoned_id, status="HALT")
    _write_phase29_ae_run_state(runner, root=root, evidence_root=evidence, run_id=completed_id, status="COMPLETED")
    runner.write_json_atomic(
        abandoned_dir / "abandonment.json",
        {"schema_version": "runtime_test_abandonment_v1", "run_id": abandoned_id, "abandoned_at": "2026-07-07T00:00:00Z", "resume_disabled": True},
    )

    abandoned = call_main(runner, ["stop", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", abandoned_id, "--confirm", CONFIRM_FLAG], capsys)
    completed = call_main(runner, ["stop", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", completed_id, "--confirm", CONFIRM_FLAG], capsys)
    unknown = call_main(runner, ["stop", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", "missing-run", "--dry-run"], capsys)

    assert abandoned["status"] == "PRECONDITION_FAILURE"
    assert completed["status"] == "PRECONDITION_FAILURE"
    assert unknown["status"] == "PRECONDITION_FAILURE"


def test_phase29_l21t_ae_stop_resume_and_status_show_observability(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    run_id = "runtime-test-ae-status-show"
    _write_phase29_ae_run_state(runner, root=root, evidence_root=evidence, run_id=run_id)

    stop = call_main(runner, ["stop", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", run_id, "--confirm", CONFIRM_FLAG], capsys)
    status_payload = call_main(runner, ["run-status", "--runtime-root", str(root), "--evidence-root", str(evidence)], capsys)
    show_payload = call_main(runner, ["show", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", run_id], capsys)
    resume = call_main(runner, ["resume", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", run_id, "--dry-run"], capsys)

    assert stop["status"] == "STOPPED"
    assert status_payload["active_test_run"] == run_id
    assert status_payload["run_status"] == "HALT"
    assert show_payload["status"] == "HALT"
    assert show_payload["halted_at"]["runtime_test_job_status"] == "OPERATOR_STOPPED"
    assert resume["status"] == "DRY_RUN"
    assert resume["resume_allowed"] is True


def test_phase17_k_reset_initial_state_after_confirmed_backup(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    assert backup["status"] == "PASS"
    reset = call_main(runner, ["reset", "--runtime-root", str(root), "--evidence-root", str(evidence), "--backup-id", backup["backup_id"], "--confirm", CONFIRM_FLAG], capsys)
    assert reset["status"] == "PASS"
    state = json.loads((root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    pending = json.loads((root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    assert state["cash"] == 1_000_000.0
    assert state["buying_power"] == 1_000_000.0
    assert state["positions"] == []
    assert pending["status"] == "EMPTY"
    assert (root / "persistent_ledger" / "orders.jsonl").read_text(encoding="utf-8") == ""


def test_phase20_o_reset_initial_state_separates_logical_date_from_wall_clock(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)

    reset = call_main(
        runner,
        [
            "reset",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(evidence),
            "--backup-id",
            backup["backup_id"],
            "--initial-position-state-date",
            "2026-06-15",
            "--initial-cash",
            "1000000",
            "--confirm",
            CONFIRM_FLAG,
        ],
        capsys,
    )
    state = json.loads((root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))

    assert reset["status"] == "PASS"
    assert reset["initial_date_policy"] == "historical_fresh_run_first_business_date"
    assert reset["resolved_initial_position_state_date"] == "2026-06-15"
    assert state["business_date"] == "2026-06-15"
    assert state["as_of"] == "2026-06-15"
    assert state["position_state_as_of"] == "2026-06-15"
    assert state["current_position_status"] == "READY"
    assert state["current_positions_unknown"] is False
    assert state["current_state_confirmed_empty"] is True
    assert state["no_position"] is True
    assert state["no_position_reason"] == "runtime_test_initial_empty_portfolio"
    assert state["position_state_source"] == "runtime_test_reset"
    assert state["temporal_status"] == "READY"
    assert state["review_required"] is False
    assert state["cash"] == 1_000_000.0
    assert state["total_equity"] == 1_000_000.0
    assert state["created_at"] > "2026-06-15"
    assert state["reset_executed_at"] == state["created_at"]
    assert state["wall_clock_fields"]["created_at"] == state["created_at"]
    assert state["logical_time_fields"]["position_state_as_of"] == "2026-06-15"


def test_phase20_o_reset_invalid_initial_position_state_date_fails_closed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)

    reset = call_main(
        runner,
        [
            "reset",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(evidence),
            "--backup-id",
            backup["backup_id"],
            "--initial-position-state-date",
            "2026/06/15",
            "--confirm",
            CONFIRM_FLAG,
        ],
        capsys,
    )

    assert reset["status"] == "PRECONDITION_FAILURE"
    assert reset["_exit_code"] == runner.EXIT_PRECONDITION_FAILURE


def test_phase17_k_reset_clears_historical_broker_evidence(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    broker_evidence = root / "runtime_state" / "historical_broker" / "2026-07-06" / "old-fill.json"
    broker_evidence.parent.mkdir(parents=True, exist_ok=True)
    broker_evidence.write_text(json.dumps({"status": "ACCEPTED"}), encoding="utf-8")
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    assert backup["status"] == "PASS"

    broker_evidence.write_text(json.dumps({"status": "STALE_ACCEPTED"}), encoding="utf-8")
    reset = call_main(runner, ["reset", "--runtime-root", str(root), "--evidence-root", str(evidence), "--backup-id", backup["backup_id"], "--confirm", CONFIRM_FLAG], capsys)

    assert reset["status"] == "PASS"
    assert "runtime_state/historical_broker" in reset["reset_scope"]
    assert not (root / "runtime_state" / "historical_broker").exists()


def test_phase17_k_run_invokes_normal_runtime_cli_and_stops_on_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path):
        commands.append(command)
        return subprocess.CompletedProcess(command, 30, "", "halt")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
        runner,
        ["run", "--runtime-root", str(root), "--evidence-root", str(evidence), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    assert backup["status"] == "PASS"
    assert payload["status"] == "HALT"
    assert payload["_exit_code"] == runner.EXIT_HALT
    assert commands
    assert commands[0][commands[0].index("-m") + 1] == runner.RUNTIME_CLI_MODULE


def test_phase23_d_halt_summary_propagates_manifest_reason_after_state_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    manifest_path = tmp_path / "runtime_manifest.json"

    def fake_run(command: list[str], *, cwd: Path):
        job = command[command.index("--job") + 1]
        business_date = command[command.index("--business-date") + 1]
        if job == "submit":
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "run_id": "daily-runtime-fixture",
                        "business_date": business_date,
                        "job": job,
                        "exit_code": 20,
                        "final_state": "REVIEW_REQUIRED",
                        "reason": "historical_safety_temporal_authority_missing",
                        "data_readiness_review_reasons": ["historical_safety_temporal_authority_missing"],
                        "data_readiness_next_operator_action": "Refresh or inspect evidence: historical_safety_temporal_authority_missing",
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 20, json.dumps({"exit_code": 20, "manifest": str(manifest_path)}), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
        runner,
        ["run", "--runtime-root", str(root), "--evidence-root", str(evidence), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    run_id = next((evidence / "runs").iterdir()).name
    run_dir = evidence / "runs" / run_id
    run_state = json.loads((run_dir / "run_state.json").read_text(encoding="utf-8"))
    status_payload = call_main(runner, ["status", "--runtime-root", str(root), "--evidence-root", str(evidence)], capsys)
    close_payload = call_main(runner, ["close", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", run_id], capsys)
    final_summary = json.loads((run_dir / "final_summary.json").read_text(encoding="utf-8"))

    assert payload["status"] == "HALT"
    assert payload["_exit_code"] == runner.EXIT_HALT
    assert run_state["status"] == "HALT"
    assert run_state["halted_at"]["exit_code"] == 20
    assert run_state["halt_summary"]["status"] == "HALT"
    assert run_state["halt_summary"]["root_reason"] == "historical_safety_temporal_authority_missing"
    assert run_state["halt_summary"]["root_reason_code"] == "historical_safety_temporal_authority_missing"
    assert run_state["halt_summary"]["recommended_action"] == "Refresh or inspect evidence: historical_safety_temporal_authority_missing"
    assert status_payload["halt_summary"] == run_state["halt_summary"]
    assert close_payload["halt_summary"] == run_state["halt_summary"]
    assert final_summary["halt_summary"] == run_state["halt_summary"]


def test_phase17_k_run_marks_execution_success_when_runtime_cli_jobs_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
        runner,
        ["run", "--runtime-root", str(root), "--evidence-root", str(evidence), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )

    assert backup["status"] == "PASS"
    assert payload["status"] == "PASS"
    assert any("--job" in command and command[command.index("--job") + 1] == "execution" for command in commands)
    assert len(commands) == len(runner.JOB_SEQUENCE)


def test_phase29_l20f_runner_invokes_pending_lifecycle_before_next_day_readiness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    commands: list[tuple[str, str]] = []

    def fake_run(command: list[str], *, cwd: Path):
        job = command[command.index("--job") + 1]
        business_date = command[command.index("--business-date") + 1]
        run_dir = Path(command[command.index("--runtime-test-evidence-root") + 1])
        commands.append((business_date, job))
        if business_date == "2026-07-06" and job == "morning":
            _write_json(
                root / "pending_order_plan" / "pending_order_plan.json",
                {
                    "schema_version": "runtime_v2_pending_slot_v1",
                    "state": "APPROVED",
                    "pending_plan_id": "pending-ca-buy",
                    "target_session_date": "2026-07-06",
                    "items": [{"pending_item_id": "item-ca-buy", "symbol": "76920", "side": "BUY", "quantity": 2000}],
                },
            )
        if business_date == "2026-07-06" and job == "execution":
            _write_json(
                run_dir / "daily" / business_date / "execution" / "pending_terminalization_evidence.json",
                {
                    "status": "PENDING_LIFECYCLE_REQUIRED",
                    "pending_read_valid": True,
                    "pending_plan_present": True,
                    "pending_item_count": 1,
                    "pending_consumed": False,
                    "pending_mutated": False,
                },
            )
        if business_date == "2026-07-06" and job == "pending_lifecycle":
            _write_json(
                root / "pending_order_plan" / "pending_order_plan.json",
                {
                    "schema_version": "runtime_v2_pending_slot_v1",
                    "status": "EMPTY",
                    "state": "EMPTY",
                    "active_pending": False,
                    "last_pending_plan_id": "pending-ca-buy",
                    "last_terminal_state": "EXPIRED",
                },
            )
            manifest = tmp_path / "pending_lifecycle_manifest.json"
            _write_json(
                manifest,
                {
                    "schema_version": "1",
                    "business_date": business_date,
                    "job": "pending_lifecycle",
                    "exit_code": 0,
                    "final_state": "COMPLETED",
                    "pending_lifecycle_status": "EXPIRED",
                    "pending_lifecycle_reason": "historical_corporate_action_quarantine_not_submitted_non_retryable",
                    "previous_state": "APPROVED",
                    "new_state": "EXPIRED",
                    "current_pending_path": str(root / "pending_order_plan" / "pending_order_plan.json"),
                    "stages": [
                        {
                            "name": "pending_lifecycle",
                            "status": "EXPIRED",
                            "details": {"pending_lifecycle_status": "EXPIRED", "new_state": "EXPIRED"},
                        }
                    ],
                },
            )
            return subprocess.CompletedProcess(command, 0, json.dumps({"exit_code": 0, "manifest": str(manifest)}), "")
        if business_date == "2026-07-07" and job == "data_readiness":
            pending = json.loads((root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
            assert pending["state"] == "EMPTY"
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
        runner,
        ["run", "--runtime-root", str(root), "--evidence-root", str(evidence), "--business-days", "2", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    run_id = next((evidence / "runs").iterdir()).name
    run_dir = evidence / "runs" / run_id
    run_state = json.loads((run_dir / "run_state.json").read_text(encoding="utf-8"))
    day_completion = json.loads((run_dir / "daily" / "2026-07-06" / "day_completion" / "day_completion_evidence.json").read_text(encoding="utf-8"))

    assert payload["status"] == "PASS"
    assert ("2026-07-06", "pending_lifecycle") in commands
    assert commands.index(("2026-07-06", "pending_lifecycle")) < commands.index(("2026-07-06", "current_valuation_refresh"))
    assert commands.index(("2026-07-06", "pending_lifecycle")) < commands.index(("2026-07-07", "data_readiness"))
    assert run_state["completed_business_days"] == ["2026-07-06", "2026-07-07"]
    assert day_completion["status"] == "PASS"
    assert day_completion["pending_lifecycle_requirement"]["required"] is True
    assert day_completion["pending_lifecycle_result"]["status"] == "EXPIRED"


def test_phase29_l20h_day_completion_accepts_consumed_mixed_lifecycle(tmp_path: Path) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "run-l20h"
    business_date = "2026-07-06"
    _write_json(
        run_dir / "daily" / business_date / "execution" / "pending_terminalization_evidence.json",
        {
            "status": "PENDING_LIFECYCLE_REQUIRED",
            "item_lifecycle_authority": {"status": "PASS", "derived_plan_state": "CONSUMED"},
        },
    )
    _write_json(
        run_dir / "daily" / business_date / "pending_lifecycle" / "runtime_manifest.json",
        {
            "job": "pending_lifecycle",
            "business_date": business_date,
            "pending_lifecycle_status": "CONSUMED",
            "pending_lifecycle_reason": "historical_mixed_filled_and_ca_quarantined_items_terminal",
            "new_state": "CONSUMED",
            "stages": [
                {
                    "name": "pending_lifecycle",
                    "status": "CONSUMED",
                    "details": {"pending_lifecycle_status": "CONSUMED", "new_state": "CONSUMED"},
                }
            ],
        },
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "status": "EMPTY",
            "state": "EMPTY",
            "active_pending": False,
            "last_pending_plan_id": "pending-l20h",
            "last_terminal_state": "CONSUMED",
        },
    )

    result = runner._write_day_completion_evidence(run_dir=run_dir, runtime_root=root, business_date=business_date)

    assert result["status"] == "PASS"
    assert result["pending_lifecycle_result"]["status"] == "CONSUMED"
    assert result["completion_contract"]["completed_business_days_append_allowed"] is True


def test_phase29_l20f_runner_does_not_complete_day_when_required_lifecycle_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)

    def fake_run(command: list[str], *, cwd: Path):
        job = command[command.index("--job") + 1]
        business_date = command[command.index("--business-date") + 1]
        run_dir = Path(command[command.index("--runtime-test-evidence-root") + 1])
        if job == "execution":
            _write_json(
                run_dir / "daily" / business_date / "execution" / "pending_terminalization_evidence.json",
                {
                    "status": "PENDING_LIFECYCLE_REQUIRED",
                    "pending_read_valid": True,
                    "pending_plan_present": True,
                    "pending_item_count": 1,
                    "pending_consumed": False,
                    "pending_mutated": False,
                },
            )
        if job == "pending_lifecycle":
            manifest = tmp_path / "pending_lifecycle_review_required.json"
            _write_json(
                manifest,
                {
                    "schema_version": "1",
                    "business_date": business_date,
                    "job": "pending_lifecycle",
                    "exit_code": 20,
                    "final_state": "REVIEW_REQUIRED",
                    "pending_lifecycle_status": "REVIEW_REQUIRED",
                    "pending_lifecycle_reason": "possible_unknown_submit_outcome",
                    "stages": [
                        {
                            "name": "pending_lifecycle",
                            "status": "REVIEW_REQUIRED",
                            "details": {
                                "pending_lifecycle_status": "REVIEW_REQUIRED",
                                "pending_lifecycle_reason": "possible_unknown_submit_outcome",
                            },
                        }
                    ],
                },
            )
            return subprocess.CompletedProcess(command, 20, json.dumps({"exit_code": 20, "manifest": str(manifest)}), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
        runner,
        ["run", "--runtime-root", str(root), "--evidence-root", str(evidence), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    run_id = next((evidence / "runs").iterdir()).name
    run_state = json.loads((evidence / "runs" / run_id / "run_state.json").read_text(encoding="utf-8"))

    assert payload["status"] == "HALT"
    assert payload["_exit_code"] == runner.EXIT_HALT
    assert run_state["completed_business_days"] == []
    assert run_state["halted_at"]["job"] == "pending_lifecycle"
    assert run_state["halted_at"]["runtime_test_job_status"] == "HALT_PENDING_LIFECYCLE_REQUIRED_UNRESOLVED"
    assert run_state["halted_at"]["reason"] == "possible_unknown_submit_outcome"


def test_phase20_u_run_halts_when_pm_artifact_halts_despite_cli_exit_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path):
        commands.append(command)
        job = command[command.index("--job") + 1]
        business_date = command[command.index("--business-date") + 1]
        if job == "sell_planning":
            pm_dir = root / "runtime_state" / "position_management" / business_date
            pm_dir.mkdir(parents=True)
            (pm_dir / "position_management_decisions.json").write_text(
                json.dumps(
                    {
                        "status": "HALT",
                        "reason": "artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER",
                        "decisions": [],
                        "input_contract": {
                            "pm_input_schema_status": "HALT",
                            "pm_runtime_adapter_authority_status": "HALT",
                            "pm_runtime_adapter_authority_reason": "artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER",
                        },
                    }
                ),
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
        runner,
        ["run", "--runtime-root", str(root), "--evidence-root", str(evidence), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    run_id = next((evidence / "runs").iterdir()).name
    run_state = json.loads((evidence / "runs" / run_id / "run_state.json").read_text(encoding="utf-8"))
    pm_snapshot = json.loads((evidence / "runs" / run_id / "daily" / "2026-07-06" / "position_management" / "pm_decisions.json").read_text(encoding="utf-8"))

    assert payload["status"] == "HALT"
    assert payload["_exit_code"] == runner.EXIT_HALT
    assert run_state["status"] == "HALT"
    assert run_state["halted_at"]["runtime_test_job_status"] == "HALT_PM_POSITION_MANAGEMENT"
    assert pm_snapshot["source_status"] == "AVAILABLE"
    assert pm_snapshot["pm_status"] == "HALT"
    assert pm_snapshot["pm_authority_status"] == "HALT"
    assert pm_snapshot["pm_decision_count"] == 0
    assert [command[command.index("--job") + 1] for command in commands][-1] == "sell_planning"


def test_phase17_k_run_dry_run_never_executes_runtime_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)

    def forbidden_run(command: list[str], *, cwd: Path):
        raise AssertionError("runtime cli must not run in dry-run")

    monkeypatch.setattr(runner, "run_runtime_cli", forbidden_run)
    before = runner.directory_hash(root)
    payload = call_main(runner, ["run", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--business-days", "1", "--dry-run"], capsys)
    after = runner.directory_hash(root)
    assert payload["status"] == "DRY_RUN"
    assert payload["dry_run_no_mutation"] is True
    assert before == after


def test_phase17_k_resume_rejects_changed_source_baseline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    run_id = "runtime-test-fixture"
    run_dir = evidence / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "run_state.json").write_text(
        json.dumps({"schema_version": "phase17_k_run_state_v1", "run_id": run_id, "status": "HALT", "source_baseline": {"source_commit": "different", "source_dirty": False, "registry_hash": "different"}}),
        encoding="utf-8",
    )
    payload = call_main(runner, ["resume", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", run_id, "--dry-run"], capsys)
    assert payload["status"] == "PRECONDITION_FAILURE"


def test_phase17_k_resume_uses_fixed_plan_without_skipping_failed_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    plan = runner.build_plan(
        profile=runner.load_profile("historical-smoke"),
        runtime_root=root,
        evidence_root=evidence,
        business_days=1,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id="runtime-test-resume-fixture",
    )
    run_dir = evidence / "runs" / "runtime-test-resume-fixture"
    runner.write_json_atomic(run_dir / "plan.json", plan)
    historical_authority = runner.materialize_historical_evaluation_authority(
        run_dir=run_dir,
        runtime_root=root,
        profile=runner.load_profile("historical-smoke"),
        plan_payload=plan,
    )
    runner.write_json_atomic(
        run_dir / "run_state.json",
        {
            "schema_version": runner.RUN_STATE_SCHEMA_VERSION,
            "run_id": "runtime-test-resume-fixture",
            "status": "HALT",
            "source_baseline": runner.source_baseline(root),
            "historical_evaluation_authority": historical_authority,
            "completed_jobs": [
                {"business_date": "2026-07-06", "job": "market_refresh", "exit_code": 0},
                {"business_date": "2026-07-06", "job": "data_readiness", "exit_code": 30},
            ],
        },
    )
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
        runner,
        ["resume", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", "runtime-test-resume-fixture", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    assert payload["status"] == "PASS"
    assert commands[0][commands[0].index("--job") + 1] == "data_readiness"


def test_phase17_k_rollback_restores_full_resettable_state(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    (root / "persistent_ledger" / "state.json").write_text(json.dumps({"schema_version": "changed", "cash": 0}), encoding="utf-8")
    payload = call_main(runner, ["rollback", "--runtime-root", str(root), "--evidence-root", str(evidence), "--backup-id", backup["backup_id"], "--confirm", CONFIRM_FLAG], capsys)
    restored = json.loads((root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert restored["cash"] == 12


def test_phase17_k_mode_rooted_path_and_production_profile_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    mode_rooted = root / "historical"
    payload = call_main(runner, ["status", "--runtime-root", str(mode_rooted), "--evidence-root", str(tmp_path / "reports")], capsys)
    assert payload["status"] == "INVALID_ARGUMENT"
    production_profile = tmp_path / "production_profile.json"
    profile = json.loads(Path("config/runtime_tests/historical_smoke_5bd.json").read_text(encoding="utf-8"))
    profile["profile_id"] = "production-fixture"
    profile["mode"] = "production"
    profile["runtime_root"] = str(root)
    production_profile.write_text(json.dumps(profile), encoding="utf-8")
    payload = call_main(runner, ["status", "--profile", str(production_profile), "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports")], capsys)
    assert payload["status"] == "HALT"
