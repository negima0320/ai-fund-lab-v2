from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.historical_support.corporate_action_quarantine import (
    read_registry,
    upsert_quarantine,
)
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline
from scripts.runtime_test import (
    classify_historical_corporate_action_quarantine_result,
    repair_ca_quarantine_continuation_command,
)
from tests.runtime_v2.test_phase17_g_historical_submit_guard_and_fill import (
    BUSINESS_DATE,
    _historical_context,
    _runtime_fixture,
)


def test_phase29_l9_historical_ca_quarantine_classifier_persists_symbol_scope(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_submit_manifest(run_dir, run_type="HISTORICAL")

    result = classify_historical_corporate_action_quarantine_result(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-28",
        job="submit",
        exit_code=20,
    )

    assert result is not None
    assert result["status"] == "COMPLETED_WITH_SYMBOL_QUARANTINE"
    assert result["quarantined_symbols"] == ["76920"]
    assert result["corporate_action_quarantine_status"] == "QUARANTINED"
    assert result["corporate_action_run_continuation_eligibility"] == "ALLOWED_FOR_HISTORICAL_REPLAY_ONLY"
    assert result["production_applicability"] == "NEVER"
    assert result["corporate_action_split_inference_used"] is False
    assert result["corporate_action_quantity_adjustment_performed"] is False
    assert result["portfolio_performance_limitation_status"] == "REVIEW_REQUIRED"
    registry = read_registry(runtime_root)
    entry = registry["symbols"]["76920"]
    assert entry["first_detected_date"] == "2022-10-28"
    assert entry["latest_checked_date"] == "2022-10-28"
    assert entry["resolution_status"] == "UNRESOLVED"


def test_phase29_l9_historical_ca_quarantine_classifier_rejects_generic_review(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_submit_manifest(run_dir, run_type="HISTORICAL", guard_reason="aggregate_submit_feasibility_failed")

    result = classify_historical_corporate_action_quarantine_result(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-28",
        job="submit",
        exit_code=20,
    )

    assert result is None
    assert read_registry(runtime_root)["symbols"] == {}


def test_phase29_l9_historical_ca_quarantine_classifier_rejects_production_context(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_submit_manifest(run_dir, run_type="PRODUCTION", broker_environment="production")

    result = classify_historical_corporate_action_quarantine_result(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-28",
        job="submit",
        exit_code=20,
    )

    assert result is None
    assert read_registry(runtime_root)["symbols"] == {}


def test_phase29_l11_real_submit_payload_without_item_results_is_eligible(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_submit_manifest(run_dir, run_type="HISTORICAL", include_item_results=False)

    result = classify_historical_corporate_action_quarantine_result(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-28",
        job="submit",
        exit_code=20,
    )

    assert result is not None
    assert result["status"] == "COMPLETED_WITH_SYMBOL_QUARANTINE"
    assert result["checks"]["blocked_count_matches_ca_items"] is True
    assert result["checks"]["submitted_count_matches_pass_items"] is True
    assert result["checks"]["pending_count_matches_guard_evidence"] is True
    assert result["quarantined_symbols"] == ["76920"]
    assert (run_dir / "daily" / "2022-10-28" / "submit" / "corporate_action_symbol_quarantine_continuation.json").exists()
    assert read_registry(runtime_root)["symbols"]["76920"]["corporate_action_quarantine_status"] == "QUARANTINED"


def test_phase29_l11_real_submit_payload_rejects_mixed_review_reason(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_submit_manifest(
        run_dir,
        run_type="HISTORICAL",
        include_item_results=False,
        extra_blocked_guard={
            "pending_item_id": "sell-7203",
            "symbol": "7203",
            "side": "SELL",
            "quantity": 100.0,
            "submit_item_status": "REVIEW_REQUIRED",
            "guard_decision": "BLOCKED",
            "guard_reason": "broker_available_quantity_missing",
            "blocked_at_submit_reason": "broker_available_quantity_missing",
        },
        submitted_count=2,
        blocked_count=2,
        pending_item_count=4,
    )

    result = classify_historical_corporate_action_quarantine_result(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-28",
        job="submit",
        exit_code=20,
    )

    assert result is None
    assert read_registry(runtime_root)["symbols"] == {}


def test_phase29_l11_real_submit_payload_rejects_actual_broker_write(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_submit_manifest(
        run_dir,
        run_type="HISTORICAL",
        include_item_results=False,
        broker_write=True,
    )

    result = classify_historical_corporate_action_quarantine_result(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-28",
        job="submit",
        exit_code=20,
    )

    assert result is None
    assert read_registry(runtime_root)["symbols"] == {}


def test_phase29_l11_retrospective_repair_dry_run_is_idempotent_and_does_not_mutate(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    evidence_root = tmp_path / "reports" / "runtime_tests"
    run_id = "runtime-test-l11-fixture"
    run_dir = evidence_root / "runs" / run_id
    runtime_root.mkdir(parents=True)
    _write_submit_manifest(run_dir, run_type="HISTORICAL", include_item_results=False)
    run_state = {
        "schema_version": "runtime_test_run_state_v1",
        "run_id": run_id,
        "profile_id": "historical-smoke",
        "status": "HALT",
        "next_job": "2022-10-28:submit",
        "source_baseline": {},
        "completed_business_days": ["2022-10-27"],
        "completed_jobs": [
            {"business_date": "2022-10-28", "job": "submit", "exit_code": 20},
        ],
        "halted_at": {"business_date": "2022-10-28", "job": "submit", "exit_code": 20},
    }
    (run_dir / "run_state.json").write_text(json.dumps(run_state), encoding="utf-8")
    args = argparse.Namespace(
        run_id=run_id,
        business_date="2022-10-28",
        job="submit",
        dry_run=True,
        confirm=False,
        explicit_mutation_confirm=False,
    )
    profile = {"profile_id": "historical-smoke", "mode": "historical"}

    first = repair_ca_quarantine_continuation_command(
        args,
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=evidence_root,
    )
    second = repair_ca_quarantine_continuation_command(
        args,
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=evidence_root,
    )

    assert first.status == "DRY_RUN"
    assert second.status == "DRY_RUN"
    assert read_registry(runtime_root)["symbols"] == {}
    persisted_state = json.loads((run_dir / "run_state.json").read_text(encoding="utf-8"))
    assert persisted_state["status"] == "HALT"
    assert "runtime_test_job_status" not in persisted_state["completed_jobs"][0]


def test_phase29_l9_persistent_quarantine_blocks_same_symbol_but_not_other_symbols(tmp_path: Path) -> None:
    (tmp_path / "quarantined").mkdir()
    quarantined_root, quarantined_policy_path, quarantined_adapter = _runtime_fixture(
        tmp_path / "quarantined",
        side="SELL",
        symbol="76920",
    )
    upsert_quarantine(
        runtime_root=quarantined_root,
        business_date=BUSINESS_DATE,
        symbol="76920",
        reason="corporate_action_event_not_resolved",
        event_status="IMPACT_DETECTED",
    )

    quarantined_result = run_submit_pipeline(
        runtime_root=quarantined_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=quarantined_adapter,
        capital_deployment_policy_path=quarantined_policy_path,
        environment_context=_historical_context(),
    )

    guard = quarantined_result.submit_guard_item_evidence[0]
    assert quarantined_result.status == "REVIEW_REQUIRED"
    assert quarantined_result.submitted_count == 0
    assert quarantined_result.item_results[0].submit_status == "NOT_SUBMITTED"
    assert guard["violated_policy"] == "historical_corporate_action_symbol_quarantine"
    assert guard["corporate_action_quarantine_status"] == "QUARANTINED"
    assert guard["corporate_action_quarantined_symbol"] == "76920"
    assert guard["corporate_action_quantity_adjustment_performed"] is False

    (tmp_path / "other").mkdir()
    other_root, other_policy_path, other_adapter = _runtime_fixture(
        tmp_path / "other",
        side="BUY",
        symbol="7203",
    )
    upsert_quarantine(
        runtime_root=other_root,
        business_date=BUSINESS_DATE,
        symbol="76920",
        reason="corporate_action_event_not_resolved",
        event_status="IMPACT_DETECTED",
    )

    other_result = run_submit_pipeline(
        runtime_root=other_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=other_adapter,
        capital_deployment_policy_path=other_policy_path,
        environment_context=_historical_context(),
    )

    assert other_result.status == "PASS"
    assert other_result.submitted_count == 1
    assert other_result.item_results[0].submit_status == "ACCEPTED"


def _write_submit_manifest(
    run_dir: Path,
    *,
    run_type: str,
    broker_environment: str = "historical_simulated",
    guard_reason: str = "corporate_action_event_not_resolved",
    include_item_results: bool = True,
    extra_blocked_guard: dict | None = None,
    submitted_count: int = 3,
    blocked_count: int = 1,
    pending_item_count: int = 4,
    broker_write: bool = False,
) -> None:
    job_dir = run_dir / "daily" / "2022-10-28" / "submit"
    job_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_type": run_type,
        "runtime_mode": "historical" if run_type == "HISTORICAL" else "production",
        "broker_environment": broker_environment,
        "final_state": "REVIEW_REQUIRED",
        "reason": "submit completed with rejected/unknown/blocked items",
        "submit_action": "SUBMIT",
        "submitted_count": submitted_count,
        "blocked_count": blocked_count,
        "pending_item_count": pending_item_count,
        "prohibited_actions": {
            "demo_submit_executed": False,
            "production_order_executed": False,
            "broker_write": broker_write,
            "external_delivery": broker_write,
        },
        "stages": [
            {
                "name": "environment_composition",
                "status": "PASS",
                "details": {
                    "run_type": run_type,
                    "broker_environment": broker_environment,
                    "historical_replay": run_type == "HISTORICAL",
                    "broker_write": broker_write,
                    "external_delivery": broker_write,
                    "tachibana_demo_write": False,
                    "tachibana_production_write": False,
                },
            }
        ],
        "submit_guard_item_evidence": [
            {
                "pending_item_id": "buy-93180",
                "symbol": "93180",
                "submit_item_status": "PASS",
                "guard_decision": "PASS",
                "guard_reason": "approved_by_submit_guard_policy",
            },
            {
                "pending_item_id": "buy-99840",
                "symbol": "99840",
                "submit_item_status": "PASS",
                "guard_decision": "PASS",
                "guard_reason": "approved_by_submit_guard_policy",
            },
            {
                "pending_item_id": "sell-7203",
                "symbol": "7203",
                "side": "SELL",
                "submit_item_status": "PASS",
                "guard_decision": "PASS",
                "guard_reason": "approved_by_submit_guard_policy",
            },
            {
                "pending_item_id": "sell-76920",
                "symbol": "76920",
                "side": "SELL",
                "quantity": 700.0,
                "submit_item_status": "REVIEW_REQUIRED",
                "guard_decision": "BLOCKED",
                "guard_reason": guard_reason,
                "corporate_action_event_status": "IMPACT_DETECTED",
                "corporate_action_event_type": "UNKNOWN_ADJFACTOR_IMPACT",
                "corporate_action_adjustment_factor": 0.3333333333333333,
                "corporate_action_adjustment_authority_status": "REVIEW_REQUIRED",
                "corporate_action_adjustment_authority_reason": "corporate_action_event_not_resolved",
                "corporate_action_split_inference_used": False,
                "corporate_action_quantity_adjustment_performed": False,
            },
        ],
    }
    if extra_blocked_guard:
        manifest["submit_guard_item_evidence"].insert(2, extra_blocked_guard)
    if include_item_results:
        manifest["item_results"] = [
            {"pending_item_id": "buy-93180", "symbol": "93180", "submit_status": "ACCEPTED"},
            {"pending_item_id": "buy-99840", "symbol": "99840", "submit_status": "ACCEPTED"},
            {"pending_item_id": "sell-7203", "symbol": "7203", "submit_status": "ACCEPTED"},
            {"pending_item_id": "sell-76920", "symbol": "76920", "submit_status": "NOT_SUBMITTED"},
        ]
    (job_dir / "runtime_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
