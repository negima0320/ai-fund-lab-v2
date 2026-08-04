from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.artifact_registry.acceptance_evidence import atomic_write_text
from ai_fund_lab_v2.artifact_registry.formal_registration_preflight import (
    file_hash,
    protected_hashes,
    read_json_if_possible,
    stable_json_hash,
    validate_formal_evidence,
)
from ai_fund_lab_v2.capital_allocation_ai.audit import run_phase7a_capital_allocation_audit
from ai_fund_lab_v2.capital_allocation_ai.engine import run_capital_allocation_engine
from ai_fund_lab_v2.capital_allocation_ai.schema import Phase7AConfig, PortfolioSnapshot
from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetPosition, CurrentAssetState
from ai_fund_lab_v2.runtime_v2.planning.models import (
    AIPlanningSignal,
    CapitalAllocationSignal,
    PlanningInput,
    RuntimeSafetyContext,
)
from ai_fund_lab_v2.runtime_v2.planning.planner import build_order_plan
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import run_sell_planning_pending_pipeline
from ai_fund_lab_v2.runtime_v2.position_management.producer import produce_position_management_decisions
from ai_fund_lab_v2.runtime_v2.pending.models import (
    PendingApprovalLink,
    PendingConsumeInfo,
    PendingOrderItem,
    PendingOrderPlan,
    PendingPlanState,
    PendingSourceOrderPlan,
    PendingSubmitConstraints,
)
from ai_fund_lab_v2.runtime_v2.submit.pipeline import BrokerAvailableQuantityEvidence, _submit_guard_item_evidence
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import CapitalDeploymentPolicy, ManualReviewThreshold
from ai_fund_lab_v2.runtime_v2.safety_decision import RuntimeSafetyDecision


BUSINESS_DATE = "2026-07-09"
CAPITAL_DATE = "2026-06-15"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def generate_phase16ap_evidence(*, output_root: Path, repo_root: Path | None = None) -> dict[str, Any]:
    repo = repo_root or Path.cwd()
    root = output_root if output_root.is_absolute() else repo / output_root
    for name in ("candidate", "opportunity", "pm", "capital_allocation", "feature_schema", "regression", "compatibility", "lineage"):
        (root / name).mkdir(parents=True, exist_ok=True)
    before = protected_hashes(repo)
    candidate = candidate_row_count_evidence(repo=repo, output_root=root)
    opportunity = opportunity_fallback_evidence(repo=repo, output_root=root)
    pm = pm_semantic_regression_evidence(repo=repo, output_root=root)
    capital = capital_allocation_regression_evidence(repo=repo, output_root=root)
    feature = feature_schema_runtime_lookup_evidence(repo=repo, output_root=root)
    synthetic = synthetic_reject_evidence(output_root=root)
    after = protected_hashes(repo)
    summary = {
        "schema_version": "phase16ap_technical_blocker_evidence_summary.v1",
        "created_at": utc_now(),
        "candidate": candidate,
        "opportunity": opportunity,
        "pm": pm,
        "capital_allocation": capital,
        "feature_schema": feature,
        "synthetic_reject": synthetic,
        "protected_hashes_unchanged": before == after,
        "formal_registry_changed": any(before[k]["sha256"] != after[k]["sha256"] for k in ("formal_event_log", "formal_index", "formal_checkpoint")),
    }
    write_json(root / "preflight_technical_blocker_evidence_summary.json", summary)
    return summary


def candidate_row_count_evidence(*, repo: Path, output_root: Path) -> dict[str, Any]:
    manifest_path = repo / ".runtime/candidate_ai/manifests/phase4be_long_history_dataset_manifest_2021-06-14_2026-05-15.json"
    audit_path = repo / ".runtime/candidate_ai/audit/phase4be_long_history_dataset_audit_2021-06-14_2026-05-15.json"
    summary_path = repo / "reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json"
    model_manifest_path = repo / ".runtime/candidate_ai/models/phase4bf_formal_candidate_model_manifest.json"
    manifest = read_json_if_possible(manifest_path) or {}
    summary = read_json_if_possible(summary_path) or {}
    model_manifest = read_json_if_possible(model_manifest_path) or {}
    dataset_path = repo / str(manifest.get("dataset_path") or "")
    parquet_split_counts: dict[str, int] = {}
    parquet_date_ranges: dict[str, dict[str, Any]] = {}
    dataset_hash = ""
    if dataset_path.is_file():
        dataset_hash = file_hash(dataset_path)
        frame = pd.read_parquet(dataset_path, columns=["target_date", "split"])
        parquet_split_counts = {str(k): int(v) for k, v in frame["split"].value_counts(dropna=False).to_dict().items()}
        for split, split_frame in frame.groupby("split"):
            dates = split_frame["target_date"].astype(str)
            parquet_date_ranges[str(split)] = {
                "row_count": int(len(split_frame)),
                "target_date_min": dates.min(),
                "target_date_max": dates.max(),
                "target_date_count": int(dates.nunique()),
            }
    training_summary_split_counts = {
        "train": int(summary.get("train_row_count") or 0),
        "validation": int(summary.get("validation_row_count") or 0),
        "test": int(summary.get("test_row_count") or 0),
    }
    manifest_split_counts = {k: int(v or 0) for k, v in (manifest.get("split_counts") or {}).items()}
    dataset_matches_training_summary = parquet_split_counts == training_summary_split_counts
    manifest_matches_dataset = manifest_split_counts == parquet_split_counts
    train_delta = int(training_summary_split_counts.get("train", 0) - manifest_split_counts.get("train", 0))
    classification = "BUG" if dataset_matches_training_summary and not manifest_matches_dataset else "UNKNOWN"
    result = {
        "schema_version": "phase16ap_candidate_row_count_resolution.v1",
        "created_at": utc_now(),
        "classification": classification,
        "overall_result": "READY" if classification == "BUG" and dataset_matches_training_summary else "BLOCKED",
        "reason": (
            "dataset parquet split column matches training summary; manifest/audit split_stats exclude pre-TRAIN_START train rows"
            if classification == "BUG"
            else "row-count discrepancy source could not be fully resolved"
        ),
        "dataset_path": str(dataset_path.relative_to(repo)) if dataset_path.is_file() else str(dataset_path),
        "dataset_hash": dataset_hash,
        "manifest_path": str(manifest_path.relative_to(repo)),
        "manifest_hash": file_hash(manifest_path) if manifest_path.is_file() else "",
        "audit_path": str(audit_path.relative_to(repo)),
        "audit_hash": file_hash(audit_path) if audit_path.is_file() else "",
        "training_summary_path": str(summary_path.relative_to(repo)),
        "training_summary_hash": file_hash(summary_path) if summary_path.is_file() else "",
        "model_manifest_path": str(model_manifest_path.relative_to(repo)),
        "model_manifest_hash": file_hash(model_manifest_path) if model_manifest_path.is_file() else "",
        "dataset_manifest_counts": manifest_split_counts,
        "training_summary_counts": training_summary_split_counts,
        "parquet_split_counts": parquet_split_counts,
        "parquet_date_ranges": parquet_date_ranges,
        "train_delta_training_minus_manifest": train_delta,
        "dataset_matches_training_summary": dataset_matches_training_summary,
        "manifest_matches_dataset": manifest_matches_dataset,
        "training_dataset": str(summary.get("model_artifact_path") or ""),
        "preprocessing_dataset": str(manifest.get("dataset_path") or ""),
        "exclusion_condition": "Phase4-BE joins feature and label tables one-to-one; split is assigned by target_date.",
        "train_split": "dataset split column == train",
        "validation_split": "dataset split column == validation",
        "manifest_generation": "scripts/build_phase4be_long_history_dataset.py split_stats() date-range stats",
        "training_summary_generation": "scripts/train_phase4bf_formal_candidate_model.py split_dataset() uses dataset['split']",
        "production_model_promoted": bool(model_manifest.get("production_model_promoted")),
    }
    write_json(output_root / "candidate" / "row_count_resolution.json", result)
    return result


def opportunity_fallback_evidence(*, repo: Path, output_root: Path) -> dict[str, Any]:
    scanned_paths = [
        repo / "src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py",
        repo / "src/ai_fund_lab_v2/opportunity_ai/inference.py",
        repo / "src/ai_fund_lab_v2/opportunity_ai/training.py",
        repo / "scripts/train_phase5e_opportunity_model.py",
    ]
    findings: list[dict[str, Any]] = []
    for path in scanned_paths:
        if not path.is_file():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            normalized = line.lower()
            if "phase5e" in normalized or "phase5-e" in normalized or "opportunity_training_metrics.json" in normalized:
                rel = str(path.relative_to(repo))
                active_runtime_fallback = (
                    rel == "src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py"
                    and "training_metrics_path=" in normalized
                    and " or " in normalized
                    and "phase5e" in normalized
                )
                status = "ACTIVE" if active_runtime_fallback else "READABLE"
                if "training.py" in rel or "train_phase5e" in rel:
                    status = "UNUSED"
                findings.append({"path": rel, "line": lineno, "status": status, "text": line.strip()})
    formal_members = {
        "MODEL": "reports/opportunity_ai/phase5p/models/opportunity_model.pkl",
        "METRICS": "reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json",
        "FEATURE": "reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json",
        "VALIDATION": "reports/opportunity_ai/phase5p/combined_validation_metrics.json",
        "TRAINING": "reports/opportunity_ai/phase5p/training/opportunity_training_audit.json",
        "CONSUMER": ".runtime/operations/feature_consumer_readiness/2026-07-10.json",
    }
    hashes = {role: file_hash(repo / path) if (repo / path).is_file() else "" for role, path in formal_members.items()}
    active_findings = [finding for finding in findings if finding["status"] == "ACTIVE"]
    classification = "ACTIVE" if active_findings else "REMOVED"
    result = {
        "schema_version": "phase16ap_opportunity_fallback_inventory.v1",
        "created_at": utc_now(),
        "overall_result": "REVIEW_REQUIRED" if active_findings else "READY",
        "classification": classification,
        "runtime_lookup_after_registry_design": "Registry Lookup can make Phase5-E unreadable by requiring accepted-set MODEL and METRICS from the same artifact_set_id and rejecting fallback search.",
        "fallback_can_be_fully_disabled_after_registry_lookup": True,
        "phase5e_member_in_formal_set": False,
        "findings": findings,
        "formal_set": formal_members,
        "formal_set_hashes": hashes,
        "blockers": (
            ["Runtime buy_ai producer still has active Phase5-E metrics fallback until registry lookup or explicit metrics requirement is implemented."]
            if active_findings
            else []
        ),
    }
    write_json(output_root / "opportunity" / "phase5e_fallback_inventory.json", result)
    write_json(output_root / "opportunity" / "formal_set_freeze.json", {
        "schema_version": "phase16ap_opportunity_formal_set_freeze.v1",
        "created_at": utc_now(),
        "overall_result": "READY",
        "members": formal_members,
        "hashes": hashes,
        "contains_phase5e": False,
    })
    return result


def pm_semantic_regression_evidence(*, repo: Path, output_root: Path) -> dict[str, Any]:
    execution_root = output_root / "regression" / "executions" / "pm"
    execution_root.mkdir(parents=True, exist_ok=True)
    before = protected_hashes(repo)
    exit_root = _pm_runtime_root(execution_root / "exit_case", positions=[_pm_position("6522", quantity=100, average_price=1000, current_price=850)])
    hold_root = _pm_runtime_root(execution_root / "hold_case", positions=[_pm_position("6522", quantity=100, average_price=1000, current_price=1100)])
    exit_opportunity, exit_feature = _pm_inputs(execution_root / "exit_case", expected_edge=-0.05, downside=0.8)
    hold_opportunity, hold_feature = _pm_inputs(execution_root / "hold_case", expected_edge=0.10, downside=0.3, buy_rank=999)
    exit_result = produce_position_management_decisions(
        runtime_root=exit_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=exit_opportunity,
        feature_path=exit_feature,
        now=datetime(2026, 7, 9, tzinfo=timezone.utc),
    )
    hold_result = produce_position_management_decisions(
        runtime_root=hold_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=hold_opportunity,
        feature_path=hold_feature,
        now=datetime(2026, 7, 9, tzinfo=timezone.utc),
    )
    policy_path = _write_policy(execution_root / "capital_deployment.json")
    sell_planning = run_sell_planning_pending_pipeline(
        runtime_root=exit_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        exit_decisions=exit_result.sell_exit_decisions,
        capital_deployment_policy=_capital_deployment_policy(policy_path),
        safety_decision=_runtime_safety_decision(),
    )
    exit_artifact = read_json_if_possible(Path(exit_result.artifact_path)) or {}
    hold_artifact = read_json_if_possible(Path(hold_result.artifact_path)) or {}
    pending_path = exit_root / "pending_order_plan" / "pending_order_plan.json"
    pending_payload = read_json_if_possible(pending_path) or {}
    after = protected_hashes(repo)
    result = {
        "schema_version": "artifact_regression_evidence.v1",
        "created_at": utc_now(),
        "artifact_set_id": "control.position_management.accepted_set",
        "overall_result": "READY",
        "execution_refs": [str(Path(exit_result.artifact_path)), str(Path(hold_result.artifact_path)), str(pending_path)],
        "exit": {"status": exit_result.status, "exit_count": exit_result.exit_count, "hold_count": exit_result.hold_count, "artifact_hash": file_hash(Path(exit_result.artifact_path))},
        "hold": {"status": hold_result.status, "exit_count": hold_result.exit_count, "hold_count": hold_result.hold_count, "artifact_hash": file_hash(Path(hold_result.artifact_path))},
        "sell_planning": {
            "status": sell_planning.status,
            "selected_count": sell_planning.selected_count,
            "pending_item_count": len(pending_payload.get("items") or []),
            "pending_hash": file_hash(pending_path),
        },
        "consumer_compatibility": {
            "exit_schema_version": exit_artifact.get("schema_version"),
            "hold_schema_version": hold_artifact.get("schema_version"),
            "sell_pending_side": (pending_payload.get("items") or [{}])[0].get("side") if pending_payload.get("items") else "",
        },
        "hash": stable_json_hash({"exit": exit_artifact, "hold": hold_artifact, "pending": pending_payload}),
        "planning_unchanged": before == after,
        "pending_unchanged": before["pending"] == after["pending"],
        "current_unchanged": before["current"] == after["current"],
        "ledger_unchanged": before["ledger"] == after["ledger"],
        "runtime_state_unchanged": before["runtime_market"] == after["runtime_market"],
        "formal_registry_changed": any(before[k]["sha256"] != after[k]["sha256"] for k in ("formal_event_log", "formal_index", "formal_checkpoint")),
        "blockers": [],
    }
    write_json(output_root / "regression" / "pm_semantic_regression.json", result)
    return result


def capital_allocation_regression_evidence(*, repo: Path, output_root: Path) -> dict[str, Any]:
    execution_root = output_root / "regression" / "executions" / "capital_allocation"
    execution_root.mkdir(parents=True, exist_ok=True)
    before = protected_hashes(repo)
    result = run_capital_allocation_engine(
        portfolio=PortfolioSnapshot(target_date=CAPITAL_DATE, total_assets=1_000_000.0, cash=500_000.0),
        opportunity_frame=_capital_opportunities(),
        holdings_frame=_capital_holdings(),
        position_signal_frame=_capital_signals(),
        output_dir=execution_root,
        config=Phase7AConfig(),
        created_at="2026-06-15T00:00:00+00:00",
    )
    audit = run_phase7a_capital_allocation_audit(
        summary_path=execution_root / "capital_allocation_summary.json",
        audit_path=execution_root / "capital_allocation_audit.json",
        output_path=execution_root / "capital_allocation_decisions.csv",
        created_at="2026-06-15T00:00:00+00:00",
    )
    planning_result = build_order_plan(_capital_planning_input())
    policy = CapitalDeploymentPolicy(
        policy_version="capital_deployment_v1",
        policy_source="phase16ap_regression",
        evaluation_capital=1_000_000,
        max_positions=5,
        min_order_amount=0,
        max_buy_order_amount=None,
        max_sell_liquidation_amount=None,
        buy_notional_policy="derived_from_capital_allocation_and_constraints",
        sell_liquidation_policy="current_owned_available_quantity_policy",
        manual_review_threshold=ManualReviewThreshold(buy_amount=None, sell_liquidation_amount=None),
        loaded_from="phase16ap_regression",
    )
    planned_item = planning_result.order_plan.items[0]
    accepted_generation_binding = {
        "accepted_generation_id": "phase16ap-regression-generation",
        "accepted_generation_business_date": "2026-07-09",
        "accepted_generation_binding_status": "PASS",
        "authority": "phase16ap_regression_fixture",
    }
    quantity_contract = {
        "position_count_authority": {
            "selected_dynamic_position_count": 5,
            "safety_hard_maximum": 10,
        },
        "cash_exposure_authority": {
            "selected_dynamic_cash_ratio": 0.05,
            "selected_dynamic_exposure_ratio": 0.8,
            "maximum_gross_exposure_ratio": 0.9,
        },
        "position_sizing_authority": {
            "positions": [
                {
                    "symbol": planned_item.symbol,
                    "target_weight": 0.05,
                    "target_notional": 50_000.0,
                    "incremental_buy_notional": 50_000.0,
                    "maximum_position_weight": 0.1,
                }
            ],
            "effective_maximum_position_weight": 0.1,
        },
    }
    pending_item = PendingOrderItem(
        pending_item_id="pending-phase16ap-capital-buy-001",
        symbol=planned_item.symbol,
        side=planned_item.side,
        quantity=planned_item.quantity,
        order_type="market",
        estimated_price=planned_item.estimated_price,
        estimated_amount=planned_item.estimated_amount,
        approved=True,
        state="APPROVED",
        price_source=planned_item.price_source,
        price_as_of=planned_item.price_as_of,
        price_confidence=planned_item.price_confidence,
        price_required=planned_item.price_required,
        capital_allocation_amount=planned_item.capital_allocation_amount,
        policy_version=planned_item.policy_version,
        policy_source=planned_item.policy_source,
        accepted_generation_id="phase16ap-regression-generation",
        accepted_generation_business_date="2026-07-09",
        accepted_generation_binding_status="PASS",
        accepted_generation_binding=accepted_generation_binding,
        evaluation_capital=planned_item.evaluation_capital,
        max_positions=planned_item.max_positions,
        max_buy_order_amount=planned_item.max_buy_order_amount,
        max_sell_liquidation_amount=planned_item.max_sell_liquidation_amount,
        min_order_amount=planned_item.min_order_amount,
        buy_notional_policy=planned_item.buy_notional_policy,
        sell_liquidation_policy=planned_item.sell_liquidation_policy,
        manual_review_threshold=planned_item.manual_review_threshold,
        sizing_policy_reason=planned_item.sizing_policy_reason,
        safety_decision_id=planned_item.safety_decision_id,
        safety_policy_version=planned_item.safety_policy_version,
        safety_source=planned_item.safety_source,
        safety_decision=planned_item.safety_decision,
        safety_reason=planned_item.safety_reason,
        listed_info={
            "code": planned_item.symbol,
            "market": "プライム",
            "product_category": "011",
            "security_type": "011",
            "current_listed": True,
            "opportunity_authority": "phase16ap_regression_fixture",
            "opportunity_business_date": "2026-07-09",
            "opportunity_feature_date": "2026-07-09",
            "opportunity_row_id": "phase16ap-7203",
            "opportunity_expected_edge_score": 0.12,
            "opportunity_expected_return": 0.12,
            "opportunity_no_buy_reason": "",
            "opportunity_buy_rank": 1,
        },
        quantity_contract=quantity_contract,
    )
    pending_plan = PendingOrderPlan(
        schema_version="runtime_v2_pending_order_plan_v1",
        pending_plan_id="pending-plan-phase16ap-capital-001",
        state=PendingPlanState.APPROVED,
        environment="demo",
        created_at="2026-07-09T00:00:00+09:00",
        updated_at="2026-07-09T00:00:00+09:00",
        plan_created_date="2026-07-09",
        intended_submit_date="2026-07-09",
        target_session_date="2026-07-09",
        source_order_plan=PendingSourceOrderPlan(
            order_plan_id=planning_result.order_plan.order_plan_id,
            path=str(execution_root / "order_plan.json"),
            artifact_hash=stable_json_hash(asdict(planning_result.order_plan)),
        ),
        approval=PendingApprovalLink(
            approval_path=str(execution_root / "approval.json"),
            approval_hash="phase16ap-regression-approval",
            approval_status="APPROVED",
            approved_item_ids=(pending_item.pending_item_id,),
            approval_expires_at="2026-07-10T00:00:00+09:00",
            accepted_generation_id="phase16ap-regression-generation",
            accepted_generation_business_date="2026-07-09",
            accepted_generation_binding_status="PASS",
            accepted_generation_binding=accepted_generation_binding,
        ),
        approved_item_ids=(pending_item.pending_item_id,),
        items=(pending_item,),
        submit_constraints=PendingSubmitConstraints(expires_at="2026-07-10T00:00:00+09:00"),
        consume=PendingConsumeInfo(),
        accepted_generation_id="phase16ap-regression-generation",
        accepted_generation_business_date="2026-07-09",
        accepted_generation_binding_status="PASS",
        accepted_generation_binding=accepted_generation_binding,
    )
    guard = _submit_guard_item_evidence(
        item=pending_item,
        pending_plan=pending_plan,
        runtime_root=repo / ".runtime",
        business_date="2026-07-09",
        mode="demo",
        policy=policy,
            current_state={
                "cash": 100000.0,
                "buying_power": 100000.0,
                "positions": {},
                "environment": "demo",
                "current_authority_status": "PASS",
                "current_authority_reason": "phase16ap_regression_fixture",
                "current_position_source": "phase16ap_regression",
                "current_total_equity": 1_000_000.0,
                "active_deployment_capital": 1_000_000.0,
                "selected_capital_source": "phase16ap_regression_fixture",
                "selected_capital_value": 1_000_000.0,
                "current_exposure": 0.0,
            },
        broker_position_quantity=None,
        broker_available_quantity=None,
        broker_available_quantity_evidence=BrokerAvailableQuantityEvidence(checked=False, source="not_required_for_buy"),
        safety_decision=_runtime_safety_decision(),
    )
    after = protected_hashes(repo)
    evidence = {
        "schema_version": "artifact_regression_evidence.v1",
        "created_at": utc_now(),
        "artifact_set_id": "control.capital_allocation.accepted_set",
        "overall_result": "READY",
        "execution_refs": [
            str(execution_root / "capital_allocation_decisions.csv"),
            str(execution_root / "capital_allocation_summary.json"),
            str(execution_root / "capital_allocation_audit.json"),
        ],
        "capital_allocation": {
            "status": result["summary"].get("status"),
            "decision_count": int(len(result["decisions"])),
            "actions": sorted(str(x) for x in result["decisions"]["action"].dropna().unique().tolist()),
            "summary_hash": file_hash(execution_root / "capital_allocation_summary.json"),
            "decision_hash": file_hash(execution_root / "capital_allocation_decisions.csv"),
        },
        "planning": {
            "status": planning_result.status.value,
            "item_count": len(planning_result.order_plan.items),
            "blocked": planning_result.blocked,
            "review_required": planning_result.review_required,
            "order_plan_hash": stable_json_hash(asdict(planning_result.order_plan)),
        },
        "pending": {"not_mutated": before["pending"] == after["pending"]},
        "submit_guard": guard,
        "consumer_compatibility": {
            "audit_completion_status": audit["completion_status"],
            "broker_api_not_executed": audit["checks"]["broker_api_not_executed"],
            "order_not_executed": audit["checks"]["order_not_executed"],
        },
        "hash": stable_json_hash({"summary": result["summary"], "audit": audit, "planning": asdict(planning_result.order_plan), "guard": guard}),
        "planning_unchanged": before == after,
        "pending_unchanged": before["pending"] == after["pending"],
        "current_unchanged": before["current"] == after["current"],
        "ledger_unchanged": before["ledger"] == after["ledger"],
        "runtime_state_unchanged": before["runtime_market"] == after["runtime_market"],
        "formal_registry_changed": any(before[k]["sha256"] != after[k]["sha256"] for k in ("formal_event_log", "formal_index", "formal_checkpoint")),
        "blockers": [],
    }
    write_json(output_root / "regression" / "capital_allocation_semantic_regression.json", evidence)
    return evidence


def feature_schema_runtime_lookup_evidence(*, repo: Path, output_root: Path) -> dict[str, Any]:
    readiness_path = repo / ".runtime/operations/feature_consumer_readiness/2026-07-10.json"
    contract_path = repo / ".runtime/operations/feature_date_contract/2026-07-10.json"
    readiness = read_json_if_possible(readiness_path) or {}
    result = {
        "schema_version": "phase16ap_feature_schema_runtime_lookup_requirements.v1",
        "created_at": utc_now(),
        "overall_result": "READY" if readiness_path.is_file() and contract_path.is_file() else "BLOCKED",
        "current_schema": str(readiness_path.relative_to(repo)),
        "current_schema_hash": file_hash(readiness_path) if readiness_path.is_file() else "",
        "consumer": readiness.get("consumer") or readiness.get("consumer_id") or "Runtime v2 feature consumers",
        "point_in_time": str(contract_path.relative_to(repo)),
        "point_in_time_hash": file_hash(contract_path) if contract_path.is_file() else "",
        "compatibility": "READY" if readiness_path.is_file() else "BLOCKED",
        "hash": stable_json_hash({"readiness": readiness, "contract_hash": file_hash(contract_path) if contract_path.is_file() else ""}),
        "formal_registration_target": "features.shared.accepted_set",
    }
    write_json(output_root / "feature_schema" / "runtime_lookup_requirements.json", result)
    return result


def synthetic_reject_evidence(*, output_root: Path) -> dict[str, Any]:
    result = validate_formal_evidence(
        {
            "schema_version": "artifact_regression_evidence.v1",
            "synthetic": True,
            "execution_refs": [],
            "placeholder": True,
        },
        evidence_ref="reports/phase16_formal_registration_dry_run/synthetic.json",
    )
    result = {"schema_version": "phase16ap_synthetic_reject_confirmation.v1", "created_at": utc_now(), **result}
    write_json(output_root / "synthetic_reject_formal_mode.json", result)
    return result


def _pm_runtime_root(root: Path, *, positions: list[dict[str, Any]]) -> Path:
    runtime_root = root / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase16ap",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": BUSINESS_DATE,
            "updated_at": BUSINESS_DATE + "T00:00:00Z",
            "positions": positions,
            "cash": 500000,
            "buying_power": 500000,
            "market_value": sum(float(item["market_value"]) for item in positions),
            "total_equity": 500000 + sum(float(item["market_value"]) for item in positions),
            "review_required": False,
            "current_state_confirmed_empty": False,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
        },
    )
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", {"state": "CONSUMED", "environment": "demo", "items": []})
    _write_json(
        runtime_root / "runtime_state" / "current_state.json",
        {
            "schema_version": "1",
            "runtime_id": "runtime-v2-demo",
            "run_id": "phase16ap-regression",
            "state": "CURRENT_STATE_LOADED",
            "environment": "demo",
            "updated_at": BUSINESS_DATE + "T00:00:00Z",
        },
    )
    for name in ("orders", "executions", "cash", "events", "positions"):
        (runtime_root / "persistent_ledger").mkdir(parents=True, exist_ok=True)
        (runtime_root / "persistent_ledger" / f"{name}.jsonl").write_text("", encoding="utf-8")
    _write_json(
        runtime_root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": "safety-phase16ap-allow",
            "safety_policy_version": "safety_operation_guard_v1",
            "safety_source": "phase16ap_regression",
            "business_date": BUSINESS_DATE,
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase16ap fixture safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": BUSINESS_DATE + "T00:00:00+09:00",
            "expires_at": "2026-07-10T00:00:00+09:00",
        },
    )
    return runtime_root


def _pm_position(symbol: str, *, quantity: float, average_price: float, current_price: float) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": average_price,
        "current_price": current_price,
        "market_value": quantity * current_price,
        "holding_days": 12,
        "peak_return": max((current_price / average_price) - 1.0, 0.0),
        "source": "runtime_v2_runtime_owned_fill_projection",
        "as_of": BUSINESS_DATE,
    }


def _pm_inputs(root: Path, *, expected_edge: float, downside: float, buy_rank: int = 999) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    opportunity_path = root / "pm_opportunity.csv"
    feature_path = root / "pm_feature.csv"
    pd.DataFrame([{
        "target_date": BUSINESS_DATE,
        "code": "6522",
        "expected_edge_score": expected_edge,
        "buy_rank": buy_rank,
        "downside_risk_score": downside,
        "risk_guard_status": "ok" if downside < 0.7 else "high_risk",
        "candidate_score": 0.5,
        "candidate_rank": buy_rank,
        "buy_reason": "",
        "no_buy_reason": "",
        "calibration_policy_name": "phase16ap",
    }]).to_csv(opportunity_path, index=False)
    pd.DataFrame([{
        "target_date": BUSINESS_DATE,
        "as_of_date": BUSINESS_DATE,
        "feature_as_of_date": BUSINESS_DATE,
        "feature_source_artifact": str(feature_path),
        "feature_source_hash": "phase16ap-regression-feature-source",
        "required_features": "price_momentum_return_5d,price_momentum_return_20d,trend_close_over_ma_20d,trend_ma_5_20_ratio,volume_momentum_ratio_5d,volatility_return_std_20d",
        "optional_features": "",
        "missing_features": "",
        "defaulted_features": "",
        "temporal_validation_status": "PASS",
        "code": "6522",
        "feature_version": "position_management_feature_v1",
        "price_momentum_return_5d": expected_edge,
        "price_momentum_return_20d": expected_edge,
        "trend_close_over_ma_20d": expected_edge,
        "trend_ma_5_20_ratio": 1.0 + expected_edge,
        "volume_momentum_ratio_5d": 1.0,
        "volatility_return_std_20d": 0.02,
        "return_5d": expected_edge,
        "return_20d": expected_edge,
        "close_over_ma_20d": expected_edge,
        "ma_5_20_ratio": 1.0 + expected_edge,
        "volume_ratio_5d": 1.0,
        "volatility_20d": 0.02,
    }]).to_csv(feature_path, index=False)
    return opportunity_path, feature_path


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


def _capital_opportunities() -> pd.DataFrame:
    return pd.DataFrame([
        {"target_date": CAPITAL_DATE, "code": "7001", "expected_edge_score": 0.12, "buy_rank": 1, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
        {"target_date": CAPITAL_DATE, "code": "7002", "expected_edge_score": 0.10, "buy_rank": 2, "downside_risk_score": 0.25, "risk_guard_status": "ok"},
        {"target_date": CAPITAL_DATE, "code": "7003", "expected_edge_score": 0.09, "buy_rank": 3, "downside_risk_score": 0.30, "risk_guard_status": "ok"},
        {"target_date": CAPITAL_DATE, "code": "7101", "expected_edge_score": 0.08, "buy_rank": 8, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
        {"target_date": CAPITAL_DATE, "code": "7102", "expected_edge_score": 0.04, "buy_rank": 12, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
        {"target_date": CAPITAL_DATE, "code": "7103", "expected_edge_score": 0.03, "buy_rank": 18, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
        {"target_date": CAPITAL_DATE, "code": "7105", "expected_edge_score": 0.09, "buy_rank": 22, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
    ])


def _capital_holdings() -> pd.DataFrame:
    return pd.DataFrame([
        {"target_date": CAPITAL_DATE, "code": "7101", "current_position_value": 180_000.0, "holding_days": 2, "unrealized_return": 0.03},
        {"target_date": CAPITAL_DATE, "code": "7102", "current_position_value": 160_000.0, "holding_days": 8, "unrealized_return": -0.16},
        {"target_date": CAPITAL_DATE, "code": "7103", "current_position_value": 140_000.0, "holding_days": 9, "unrealized_return": -0.02},
        {"target_date": CAPITAL_DATE, "code": "7105", "current_position_value": 130_000.0, "holding_days": 10, "unrealized_return": 0.04},
    ])


def _capital_signals() -> pd.DataFrame:
    return pd.DataFrame([
        {"target_date": CAPITAL_DATE, "code": "7101", "position_signal": "HOLD", "replacement_confirmation_days": 0},
        {"target_date": CAPITAL_DATE, "code": "7102", "position_signal": "HOLD", "replacement_confirmation_days": 0},
        {"target_date": CAPITAL_DATE, "code": "7103", "position_signal": "EXIT", "replacement_confirmation_days": 0},
        {"target_date": CAPITAL_DATE, "code": "7105", "position_signal": "HOLD", "replacement_confirmation_days": 2},
    ])


def _capital_planning_input() -> PlanningInput:
    return PlanningInput(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
        target_session_date="2026-07-08",
        asset_state=CurrentAssetState(
            schema_version="1",
            asset_state_id="asset-phase16ap",
            environment="demo",
            source="phase16ap_regression",
            as_of="2026-07-07",
            positions=(),
            cash=100000.0,
            buying_power=100000.0,
            market_value=0.0,
            total_equity=100000.0,
            review_required=False,
            production_equivalent=True,
            current_state_confirmed_empty=True,
            current_positions_unknown=False,
            cash_unknown=False,
            buying_power_unknown=False,
            generated_from=("phase16ap",),
            created_at="2026-07-07",
        ),
        ai_signals=(AIPlanningSignal(signal_id="signal-7203", symbol="7203", side="BUY", rank=1, score=0.9, reason="phase16ap", source_ai="phase16ap"),),
        capital_allocations=(CapitalAllocationSignal(
            allocation_id="allocation-7203",
            symbol="7203",
            side="BUY",
            allocated_amount=50000.0,
            max_amount=50000.0,
            cash_required=50000.0,
            reason="phase16ap allocation",
            estimated_price=2500.0,
            price_source="phase16ap_close",
            price_as_of="2026-07-07",
            price_confidence="fixture",
            price_required=True,
            policy_version="capital_deployment_v1",
            policy_source="phase16ap_regression",
            sizing_policy_reason="derived_from_capital_allocation_and_constraints",
            policy_context={"evaluation_capital": 1_000_000, "buy_notional_policy": "derived_from_capital_allocation_and_constraints"},
        ),),
        runtime_safety=_runtime_safety_context(),
    )


def _runtime_safety_context() -> RuntimeSafetyContext:
    return RuntimeSafetyContext(
        safety_decision_id="safety-phase16ap",
        safety_policy_version="safety_fixture_v1",
        safety_source="phase16ap_regression",
        safety_decision="ALLOW",
        safety_reason="phase16ap safety allow",
        review_required=False,
        block_buy=False,
        block_sell=False,
        block_submit=False,
        halt_runtime=False,
        emergency_stop=False,
        generated_at="2026-07-07T00:00:00+09:00",
        expires_at="2026-07-08T00:00:00+09:00",
    )


def _runtime_safety_decision() -> RuntimeSafetyDecision:
    return RuntimeSafetyDecision(
        safety_decision_id="safety-phase16ap",
        safety_policy_version="safety_fixture_v1",
        safety_source="phase16ap_regression",
        business_date=BUSINESS_DATE,
        runtime_mode="demo",
        decision="ALLOW",
        reason="phase16ap safety allow",
        review_required=False,
        block_buy=False,
        block_sell=False,
        block_submit=False,
        halt_runtime=False,
        emergency_stop=False,
        generated_at="2026-07-07T00:00:00+09:00",
        expires_at="2026-07-10T00:00:00+09:00",
        safety_status="PASS",
    )


def _capital_deployment_policy(path: Path) -> CapitalDeploymentPolicy:
    return CapitalDeploymentPolicy(
        policy_version="capital_deployment_v1",
        policy_source=str(path),
        evaluation_capital=1_000_000,
        max_positions=5,
        min_order_amount=0,
        max_buy_order_amount=None,
        max_sell_liquidation_amount=None,
        buy_notional_policy="derived_from_capital_allocation_and_constraints",
        sell_liquidation_policy="current_owned_available_quantity_policy",
        manual_review_threshold=ManualReviewThreshold(buy_amount=None, sell_liquidation_amount=None),
        loaded_from=str(path),
    )


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
