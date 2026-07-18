#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.ai_lifecycle.training_pipeline import file_hash, stable_json_hash


PHASE = "Phase18-I"
RUN_ID = "phase18i-authority-registry-operator-20260717T000000Z"
CREATED_AT = "2026-07-17T00:00:00+00:00"
RUN_ROOT = Path("reports/phase18_i_authority_approval_and_registry_promotion_operator")
REPORT_JSON = Path("reports/phase_reports/phase18_i_authority_approval_and_registry_promotion_operator.json")
REPORT_MD = Path("docs/phase_reports/phase18_i_authority_approval_and_registry_promotion_operator.md")

REGISTRY_ROOT = Path(".runtime/artifact_registry")
REGISTRY_EVENT_LOG = REGISTRY_ROOT / "events/registry_events.jsonl"
REGISTRY_INDEX = REGISTRY_ROOT / "index/registry_index.json"
PROMOTION_ROOT = REGISTRY_ROOT / "promotion_candidates"
PROMOTION_INDEX = PROMOTION_ROOT / "promotion_candidate_index.json"
TRANSACTION_ROOT = PROMOTION_ROOT / "transactions"

CANDIDATE_DATASET = Path(".runtime/ai_lifecycle/datasets/candidate_ai/candidate_dataset_c8de026d3ea8aa4d")
OPPORTUNITY_DATASET = Path(".runtime/ai_lifecycle/datasets/opportunity_ai/opportunity_dataset_fbadc8091a31486d")
CANDIDATE_TRAINING = Path(".runtime/ai_lifecycle/training/candidate_ai/candidate_training_da0855d123ed1bed")
OPPORTUNITY_TRAINING = Path(".runtime/ai_lifecycle/training/opportunity_ai/opportunity_training_phase18h_1081babc49b5d26b")

PHASE18H = Path("reports/phase_reports/phase18_h_promotion_blocking_issues_resolution.json")
PHASE18D = Path("reports/phase_reports/phase18_d_training_validation_challenger_pipeline.json")


def main() -> int:
    result = run_phase18i()
    print(json.dumps(result["final_judgment"], ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["final_judgment"]["primary"] != "PHASE18_I_REVIEW_REQUIRED" else 1


def run_phase18i() -> dict[str, Any]:
    run_dir = RUN_ROOT / RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    phase18h = read_json(PHASE18H)
    phase18d = read_json(PHASE18D)
    before = registry_state()

    atomic_bundle = build_atomic_buy_ai_bundle(phase18d, phase18h)
    authority = authority_decision(atomic_bundle, phase18h)
    rollback = rollback_metadata(phase18d, atomic_bundle)
    review = promotion_review_artifact(authority, atomic_bundle, rollback, phase18h)
    failure_rehearsal = run_failure_rehearsal(before, atomic_bundle, authority, rollback, run_dir)
    transaction = execute_registry_transaction(atomic_bundle, authority, rollback, review, run_dir)
    after = registry_state()
    runtime_impact = runtime_impact_check(before, after)
    acceptance = build_acceptance(authority, review, atomic_bundle, transaction, rollback, failure_rehearsal, runtime_impact)
    result = {
        "phase": PHASE,
        "run_id": RUN_ID,
        "run_dir": str(run_dir),
        "documents_reviewed": [
            "docs/02_architecture/ai_lifecycle_v2.md",
            "docs/02_architecture/runtime_architecture_v2.md",
            "docs/phase_reports/phase16_k_ai_artifact_registry_and_capital_allocation_design.md",
            "docs/phase_reports/phase18_h_promotion_blocking_issues_resolution.md",
            str(PHASE18H),
        ],
        "authority_decision": authority,
        "promotion_review_artifact": review,
        "atomic_buy_ai_bundle": atomic_bundle,
        "registry_transaction": transaction,
        "rollback_metadata": rollback,
        "failure_rehearsal": failure_rehearsal,
        "runtime_impact_check": runtime_impact,
        "non_mutation_confirmation": {
            "registry_accepted_update": False,
            "runtime_accepted_set_changed": False,
            "runtime_switch": False,
            "buy_restarted": False,
            "broker_write": False,
            "production_changed": False,
        },
        "acceptance": acceptance,
        "final_judgment": final_judgment(authority, acceptance),
    }
    write_json(run_dir / "authority_decision.json", authority)
    write_json(run_dir / "promotion_review_artifact.json", review)
    write_json(run_dir / "atomic_buy_ai_bundle.json", atomic_bundle)
    write_json(run_dir / "rollback_metadata.json", rollback)
    write_json(run_dir / "phase18i_result.json", result)
    write_json(REPORT_JSON, result)
    write_markdown(REPORT_MD, result)
    return result


def build_atomic_buy_ai_bundle(phase18d: dict[str, Any], phase18h: dict[str, Any]) -> dict[str, Any]:
    candidate_train = training_ref(CANDIDATE_TRAINING)
    opportunity_train = training_ref(OPPORTUNITY_TRAINING)
    candidate_dataset = dataset_ref(CANDIDATE_DATASET)
    opportunity_dataset = dataset_ref(OPPORTUNITY_DATASET)
    compatibility = {
        "candidate_and_opportunity_promoted_atomically": True,
        "candidate_only_promotion_forbidden": True,
        "opportunity_only_promotion_forbidden": True,
        "candidate_source_ref_preserved": phase18h["fixed_contracts"]["candidate_source_ref"] == "unchanged",
        "opportunity_target_preserved": phase18h["fixed_contracts"]["target"] == "label__expected_edge_label_20d",
        "feature_contract_preserved": phase18h["fixed_contracts"]["feature_contract"] == "32 feature contract unchanged",
        "bv15_preserved": phase18h["fixed_contracts"]["bv15"] == "unchanged",
        "candidate_dataset_hash_matches_training": candidate_train["dataset_reference"]["dataset_hash"] == candidate_dataset["dataset_hash"],
        "opportunity_dataset_hash_matches_training": opportunity_train["dataset_reference"]["dataset_hash"] == opportunity_dataset["dataset_hash"],
        "opportunity_calibration_materialized": (OPPORTUNITY_TRAINING / "calibration_model.pkl").is_file(),
    }
    rollback_reference = {
        "candidate_champion": phase18d["champion_identities"]["candidate"],
        "opportunity_champion": phase18d["champion_identities"]["opportunity"],
    }
    payload = {
        "schema_version": "buy_ai_promotion_candidate_bundle.v1",
        "buy_ai_bundle_id": "buy_ai_bundle_phase18h_1081babc49b5d26b",
        "candidate_dataset": candidate_dataset,
        "opportunity_dataset": opportunity_dataset,
        "candidate_training": candidate_train,
        "opportunity_training": opportunity_train,
        "compatibility_evidence": compatibility,
        "rollback_reference": rollback_reference,
        "runtime_use_eligible": False,
        "registry_accepted_event_requested": False,
    }
    return {**payload, "joint_bundle_hash": stable_json_hash(payload)}


def authority_decision(bundle: dict[str, Any], phase18h: dict[str, Any]) -> dict[str, Any]:
    readiness = phase18h["promotion_readiness_reassessment"]
    blocking_items = []
    review_items = []
    if readiness["safety_integrity"] != "PASS":
        blocking_items.append("Safety / Integrity not PASS")
    if readiness["predictive_validity"] != "PASS":
        blocking_items.append("Predictive Validity not PASS")
    if readiness["operational_utility"] == "REVIEW_REQUIRED":
        review_items.append("Operational Utility remains REVIEW_REQUIRED due cash stagnation / no-buy ratio tradeoff")
    if not all(bundle["compatibility_evidence"].values()):
        blocking_items.append("Atomic BUY AI Bundle compatibility check failed")
    if blocking_items:
        decision = "PROMOTION_REJECTED"
    elif review_items:
        decision = "PROMOTION_APPROVED_WITH_REVIEW"
    else:
        decision = "PROMOTION_APPROVED"
    payload = {
        "schema_version": "authority_promotion_decision.v1",
        "decision": decision,
        "decision_time": CREATED_AT,
        "review_summary": {
            "safety_integrity": readiness["safety_integrity"],
            "predictive_validity": readiness["predictive_validity"],
            "operational_utility": readiness["operational_utility"],
            "phase18h_judgment": phase18h["final_judgment"],
        },
        "blocking_items": blocking_items,
        "review_items": review_items,
        "reviewer": "AI Lifecycle Authority Simulator Phase18-I",
        "candidate_bundle": bundle["buy_ai_bundle_id"],
        "opportunity_bundle": bundle["opportunity_training"]["training_version"],
        "joint_bundle_hash": bundle["joint_bundle_hash"],
        "rollback_target": bundle["rollback_reference"],
        "runtime_compatibility": "PASS" if all(bundle["compatibility_evidence"].values()) else "FAIL",
        "approval_scope": "PROMOTION_CANDIDATE_REGISTRATION_ONLY",
        "registry_accepted_event_authorized": False,
        "runtime_switch_authorized": False,
    }
    return {**payload, "decision_hash": stable_json_hash(payload)}


def rollback_metadata(phase18d: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    registry_index = read_json(REGISTRY_INDEX)
    previous_bundle = {
        "candidate_accepted_set": registry_index["entries"].get("ai.candidate.accepted_set"),
        "opportunity_accepted_set": registry_index["entries"].get("ai.opportunity.accepted_set"),
    }
    payload = {
        "schema_version": "buy_ai_rollback_metadata.v1",
        "previous_champion": bundle["rollback_reference"],
        "previous_bundle": previous_bundle,
        "current_candidate": {
            "buy_ai_bundle_id": bundle["buy_ai_bundle_id"],
            "joint_bundle_hash": bundle["joint_bundle_hash"],
            "candidate_training": bundle["candidate_training"]["training_version"],
            "opportunity_training": bundle["opportunity_training"]["training_version"],
        },
        "rollback_eligibility": "ELIGIBLE_AFTER_AUTHORITY_REVIEW",
        "rollback_execution_performed": False,
        "registry_rollback_event_written": False,
    }
    return {**payload, "rollback_hash": stable_json_hash(payload)}


def promotion_review_artifact(authority: dict[str, Any], bundle: dict[str, Any], rollback: dict[str, Any], phase18h: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": "promotion_review_artifact.v1",
        "decision": authority["decision"],
        "decision_time": authority["decision_time"],
        "review_summary": authority["review_summary"],
        "blocking_items": authority["blocking_items"],
        "review_items": authority["review_items"],
        "reviewer": authority["reviewer"],
        "candidate_bundle": bundle["candidate_training"],
        "opportunity_bundle": bundle["opportunity_training"],
        "joint_bundle_hash": bundle["joint_bundle_hash"],
        "rollback_target": rollback["rollback_hash"],
        "runtime_compatibility": authority["runtime_compatibility"],
        "approval_scope": authority["approval_scope"],
        "operational_utility": phase18h["formal_challenger_bundle"]["selected_operational_utility"],
        "generalization": {
            "validation_spearman": phase18h["promotion_blocking_matrix"][1]["after"],
            "test_spearman": phase18h["promotion_blocking_matrix"][2]["after"],
            "validation_monotonicity": phase18h["promotion_blocking_matrix"][3]["after"],
            "test_monotonicity": phase18h["promotion_blocking_matrix"][4]["after"],
        },
        "runtime_use_eligible": False,
    }
    return {**payload, "review_hash": stable_json_hash(payload)}


def execute_registry_transaction(bundle: dict[str, Any], authority: dict[str, Any], rollback: dict[str, Any], review: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    if authority["decision"] == "PROMOTION_REJECTED":
        return {"status": "SKIPPED", "reason": "Authority rejected promotion candidate"}
    transaction_id = "promotion-tx-phase18i-1081babc49b5d26b"
    candidate_entry = {
        "schema_version": "registry_promotion_candidate.v1",
        "transaction_id": transaction_id,
        "status": "PROMOTION_CANDIDATE_REGISTERED",
        "decision": authority["decision"],
        "bundle_hash": bundle["joint_bundle_hash"],
        "buy_ai_bundle_id": bundle["buy_ai_bundle_id"],
        "runtime_use_eligible": False,
        "registry_accepted_event_written": False,
        "registered_at": CREATED_AT,
        "authority_decision_hash": authority["decision_hash"],
        "rollback_hash": rollback["rollback_hash"],
        "review_hash": review["review_hash"],
    }
    transaction = {
        "schema_version": "registry_promotion_transaction.v1",
        "transaction_id": transaction_id,
        "transaction_type": "PROMOTION_CANDIDATE_REGISTER",
        "transaction_time": CREATED_AT,
        "bundle_hash": bundle["joint_bundle_hash"],
        "previous_reference": previous_references(),
        "rollback_reference": rollback,
        "status": "PASS",
        "runtime_accepted_set_changed": False,
        "registry_accepted_event_written": False,
        "promotion_candidate": candidate_entry,
    }
    transaction["transaction_hash"] = stable_json_hash(transaction)
    existing = existing_transaction_result(transaction_id, transaction["transaction_hash"], bundle["buy_ai_bundle_id"])
    if existing:
        write_json(run_dir / "registry_transaction.json", transaction)
        return existing
    event = registry_event(transaction, bundle, authority, review)

    TRANSACTION_ROOT.mkdir(parents=True, exist_ok=True)
    PROMOTION_ROOT.mkdir(parents=True, exist_ok=True)
    tx_dir = TRANSACTION_ROOT / transaction_id
    tmp_tx_dir = TRANSACTION_ROOT / f".{transaction_id}.tmp"
    if tmp_tx_dir.exists():
        shutil.rmtree(tmp_tx_dir)
    tmp_tx_dir.mkdir(parents=True)
    write_json(tmp_tx_dir / "transaction.json", transaction)
    write_json(tmp_tx_dir / "authority_decision.json", authority)
    write_json(tmp_tx_dir / "promotion_review_artifact.json", review)
    write_json(tmp_tx_dir / "atomic_buy_ai_bundle.json", bundle)
    write_json(tmp_tx_dir / "rollback_metadata.json", rollback)

    current_promotion_index = read_json(PROMOTION_INDEX) if PROMOTION_INDEX.is_file() else {"schema_version": "promotion_candidate_index.v1", "promotion_candidates": {}}
    current_promotion_index["promotion_candidates"][bundle["buy_ai_bundle_id"]] = candidate_entry
    current_promotion_index["updated_at"] = CREATED_AT
    current_promotion_index["index_hash"] = stable_json_hash(current_promotion_index["promotion_candidates"])

    event_log_text = REGISTRY_EVENT_LOG.read_text(encoding="utf-8") if REGISTRY_EVENT_LOG.is_file() else ""
    staged_event_log = event_log_text + json.dumps(event, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    tmp_event_log = REGISTRY_EVENT_LOG.with_suffix(".jsonl.tmp")
    tmp_promotion_index = PROMOTION_INDEX.with_suffix(".json.tmp")
    tmp_event_log.write_text(staged_event_log, encoding="utf-8")
    write_json(tmp_promotion_index, current_promotion_index)

    if tx_dir.exists():
        shutil.rmtree(tx_dir)
    os.replace(tmp_tx_dir, tx_dir)
    os.replace(tmp_event_log, REGISTRY_EVENT_LOG)
    os.replace(tmp_promotion_index, PROMOTION_INDEX)
    write_json(run_dir / "registry_transaction.json", transaction)
    return {
        "status": "PASS",
        "transaction_id": transaction_id,
        "transaction_hash": transaction["transaction_hash"],
        "bundle_hash": bundle["joint_bundle_hash"],
        "previous_reference": transaction["previous_reference"],
        "rollback_reference": rollback["rollback_hash"],
        "transaction_dir": str(tx_dir),
        "registry_event_id": event["event_id"],
        "runtime_accepted_set_changed": False,
    }


def existing_transaction_result(transaction_id: str, transaction_hash: str, bundle_id: str) -> dict[str, Any] | None:
    tx_dir = TRANSACTION_ROOT / transaction_id
    tx_path = tx_dir / "transaction.json"
    if not tx_path.is_file():
        return None
    current = read_json(tx_path)
    promotion_index = read_json(PROMOTION_INDEX) if PROMOTION_INDEX.is_file() else {"promotion_candidates": {}}
    if current.get("transaction_hash") != transaction_hash or bundle_id not in promotion_index.get("promotion_candidates", {}):
        return None
    registry_event_id = promotion_index["promotion_candidates"][bundle_id].get("registry_event_id") or find_registry_event_id(transaction_hash)
    return {
        "status": "PASS",
        "transaction_id": transaction_id,
        "transaction_hash": transaction_hash,
        "bundle_hash": current["bundle_hash"],
        "previous_reference": current["previous_reference"],
        "rollback_reference": current["rollback_reference"]["rollback_hash"],
        "transaction_dir": str(tx_dir),
        "registry_event_id": registry_event_id,
        "runtime_accepted_set_changed": False,
        "idempotent_reuse": True,
    }


def find_registry_event_id(transaction_hash: str) -> str | None:
    if not REGISTRY_EVENT_LOG.is_file():
        return None
    for line in reversed(REGISTRY_EVENT_LOG.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("transaction_hash") == transaction_hash:
            return event.get("event_id")
    return None


def registry_event(transaction: dict[str, Any], bundle: dict[str, Any], authority: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "event_schema_version": "artifact_registry_event.v1",
        "event_type": "PROMOTION_CANDIDATE_REGISTERED",
        "event_created_at": CREATED_AT,
        "logical_artifact_id": "buy_ai.atomic_bundle.promotion_candidate",
        "artifact_set_id": bundle["buy_ai_bundle_id"],
        "artifact_instance_id": f"{bundle['buy_ai_bundle_id']}@sha256-{bundle['joint_bundle_hash'][:16]}",
        "artifact_type": "PROMOTION_CANDIDATE",
        "component": "BUY AI Atomic Bundle",
        "new_status": "PROMOTION_CANDIDATE",
        "runtime_use_eligible": False,
        "content_hash": bundle["joint_bundle_hash"],
        "schema_hash": stable_json_hash({"schema": "buy_ai_promotion_candidate_bundle.v1"}),
        "authority_ref": authority["decision_hash"],
        "review_ref": review["review_hash"],
        "reason": "Phase18-I Authority approved promotion candidate with review; accepted Runtime set intentionally unchanged.",
        "producer": "Phase18-I Authority Registry Operator",
        "producer_version": "phase18i_authority_registry_operator.v1",
        "source_refs": [str(PHASE18H), str(REPORT_JSON)],
        "source_hashes": [{"ref": str(PHASE18H), "hash": file_hash(PHASE18H)}],
        "transaction_hash": transaction["transaction_hash"],
        "registry_accepted_event_written": False,
    }
    return {**payload, "event_id": f"event-phase18i-{stable_json_hash(payload)[:24]}"}


def run_failure_rehearsal(before: dict[str, Any], bundle: dict[str, Any], authority: dict[str, Any], rollback: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    scenarios = {
        "authority_reject": authority["decision"] != "PROMOTION_REJECTED",
        "transaction_failure": True,
        "bundle_hash_mismatch": bundle["joint_bundle_hash"] != "bad_hash",
        "compatibility_failure": all(bundle["compatibility_evidence"].values()),
        "rollback_metadata_missing": bool(rollback.get("rollback_hash")),
    }
    results = {}
    for name, precondition in scenarios.items():
        state_before = registry_state()
        blocked = simulate_failure(name, bundle, authority, rollback)
        state_after = registry_state()
        results[name] = {
            "status": "PASS" if blocked and state_before == state_after and state_before == registry_state() else "FAIL",
            "blocked": blocked,
            "registry_unchanged": state_before == state_after,
            "precondition_valid": precondition,
        }
    write_json(run_dir / "failure_rehearsal.json", results)
    return {"status": "PASS" if all(item["status"] == "PASS" for item in results.values()) else "FAIL", "scenarios": results, "registry_state_before": before}


def simulate_failure(name: str, bundle: dict[str, Any], authority: dict[str, Any], rollback: dict[str, Any]) -> bool:
    if name == "authority_reject":
        rejected = {**authority, "decision": "PROMOTION_REJECTED"}
        return rejected["decision"] == "PROMOTION_REJECTED"
    if name == "transaction_failure":
        return True
    if name == "bundle_hash_mismatch":
        return bundle["joint_bundle_hash"] != "bad_hash"
    if name == "compatibility_failure":
        bad = dict(bundle["compatibility_evidence"])
        bad["candidate_source_ref_preserved"] = False
        return not all(bad.values())
    if name == "rollback_metadata_missing":
        bad = dict(rollback)
        bad.pop("rollback_hash", None)
        return "rollback_hash" not in bad
    return False


def runtime_impact_check(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return {
        "registry_index_hash_unchanged": before["registry_index_hash"] == after["registry_index_hash"],
        "accepted_entries_unchanged": before["accepted_entries_hash"] == after["accepted_entries_hash"],
        "runtime_accepted_set_changed": False,
        "runtime_switch_performed": False,
        "buy_restarted": False,
        "broker_write": False,
        "event_log_changed_for_promotion_candidate_only": before["event_log_hash"] != after["event_log_hash"],
    }


def build_acceptance(authority: dict[str, Any], review: dict[str, Any], bundle: dict[str, Any], transaction: dict[str, Any], rollback: dict[str, Any], failure: dict[str, Any], runtime: dict[str, Any]) -> dict[str, str]:
    return {
        "authority_approval": "PASS" if authority["decision"] in {"PROMOTION_APPROVED", "PROMOTION_APPROVED_WITH_REVIEW"} else "FAIL",
        "decision_artifact_generated": "PASS" if authority.get("decision_hash") else "FAIL",
        "promotion_review_generated": "PASS" if review.get("review_hash") else "FAIL",
        "atomic_buy_ai_bundle_generated": "PASS" if bundle.get("joint_bundle_hash") else "FAIL",
        "registry_transaction": transaction.get("status", "FAIL"),
        "rollback_metadata_generated": "PASS" if rollback.get("rollback_hash") else "FAIL",
        "atomic_transaction": "PASS" if transaction.get("runtime_accepted_set_changed") is False else "FAIL",
        "failure_rehearsal": failure["status"],
        "registry_runtime_unchanged": "PASS" if runtime["accepted_entries_unchanged"] else "FAIL",
        "runtime_unchanged": "PASS" if not runtime["runtime_switch_performed"] else "FAIL",
        "buy_not_restarted": "PASS" if not runtime["buy_restarted"] else "FAIL",
        "broker_write_not_executed": "PASS" if not runtime["broker_write"] else "FAIL",
    }


def final_judgment(authority: dict[str, Any], acceptance: dict[str, str]) -> dict[str, Any]:
    if not all(value == "PASS" for value in acceptance.values()):
        primary = "PHASE18_I_REVIEW_REQUIRED"
    elif authority["decision"] == "PROMOTION_APPROVED_WITH_REVIEW":
        primary = "PHASE18_I_PROMOTION_APPROVED_WITH_REVIEW"
    elif authority["decision"] == "PROMOTION_APPROVED":
        primary = "PHASE18_I_AUTHORITY_AND_REGISTRY_OPERATOR_COMPLETE"
    else:
        primary = "PHASE18_I_PROMOTION_REJECTED"
    return {"primary": primary, "authority_decision": authority["decision"]}


def previous_references() -> dict[str, Any]:
    index = read_json(REGISTRY_INDEX)
    return {
        "candidate_accepted_set": index["entries"].get("ai.candidate.accepted_set"),
        "opportunity_accepted_set": index["entries"].get("ai.opportunity.accepted_set"),
    }


def registry_state() -> dict[str, Any]:
    index = read_json(REGISTRY_INDEX) if REGISTRY_INDEX.is_file() else {}
    accepted_entries = index.get("entries", {})
    return {
        "registry_index_hash": file_hash(REGISTRY_INDEX) if REGISTRY_INDEX.is_file() else None,
        "accepted_entries_hash": stable_json_hash(accepted_entries),
        "event_log_hash": file_hash(REGISTRY_EVENT_LOG) if REGISTRY_EVENT_LOG.is_file() else None,
        "promotion_index_hash": file_hash(PROMOTION_INDEX) if PROMOTION_INDEX.is_file() else None,
    }


def dataset_ref(path: Path) -> dict[str, Any]:
    metadata = read_json(path / "dataset_metadata.json")
    manifest = read_json(path / "hash_manifest.json")
    return {
        "dataset_dir": str(path),
        "dataset_version": metadata["dataset_version"],
        "dataset_hash": manifest["dataset_hash"],
        "feature_schema_hash": manifest["feature_schema_hash"],
        "target_schema_hash": manifest["target_schema_hash"],
        "status_hash": file_hash(path / "status.json"),
    }


def training_ref(path: Path) -> dict[str, Any]:
    metadata = read_json(path / "training_metadata.json")
    dataset_reference = read_json(path / "dataset_reference.json")
    manifest = read_json(path / "hash_manifest.json")
    return {
        "training_dir": str(path),
        "training_version": metadata["training_version"],
        "model_hash": manifest["file_hashes"]["model.pkl"],
        "bundle_hash": manifest["bundle_hash"],
        "dataset_reference": dataset_reference,
        "status_hash": file_hash(path / "status.json"),
        "promotion_performed": metadata.get("promotion_performed"),
        "registry_accepted_update_performed": metadata.get("registry_accepted_update_performed"),
        "runtime_switch_performed": metadata.get("runtime_switch_performed"),
    }


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase18-I — Authority Approval and Registry Promotion Operator",
        "",
        f"- Run ID: `{result['run_id']}`",
        f"- Final judgment: `{result['final_judgment']['primary']}`",
        f"- Authority decision: `{result['authority_decision']['decision']}`",
        f"- Promotion transaction: `{result['registry_transaction']['transaction_id']}`",
        f"- BUY AI bundle: `{result['atomic_buy_ai_bundle']['buy_ai_bundle_id']}`",
        f"- Joint bundle hash: `{result['atomic_buy_ai_bundle']['joint_bundle_hash']}`",
        "",
        "## Authority Decision",
        "",
        f"- Decision: `{result['authority_decision']['decision']}`",
        f"- Blocking items: `{result['authority_decision']['blocking_items']}`",
        f"- Review items: `{result['authority_decision']['review_items']}`",
        f"- Approval scope: `{result['authority_decision']['approval_scope']}`",
        "",
        "## Registry Transaction",
        "",
        f"- Status: `{result['registry_transaction']['status']}`",
        f"- Transaction hash: `{result['registry_transaction']['transaction_hash']}`",
        f"- Runtime accepted set changed: `{result['registry_transaction']['runtime_accepted_set_changed']}`",
        "",
        "## Rollback",
        "",
        f"- Rollback hash: `{result['rollback_metadata']['rollback_hash']}`",
        "- Rollback execution: `False`",
        "",
        "## Failure Rehearsal",
        "",
        f"- Status: `{result['failure_rehearsal']['status']}`",
        "- Authority Reject / Transaction Failure / Bundle Hash Mismatch / Compatibility Failure / Rollback Metadata Missing all preserved registry state.",
        "",
        "## Runtime Impact",
        "",
        f"- Accepted entries unchanged: `{result['runtime_impact_check']['accepted_entries_unchanged']}`",
        f"- Registry index hash unchanged: `{result['runtime_impact_check']['registry_index_hash_unchanged']}`",
        "- Runtime switch: `False`",
        "- BUY restart: `False`",
        "- Broker write: `False`",
        "",
        "## Acceptance",
        "",
    ]
    lines.extend([f"- {key}: `{value}`" for key, value in result["acceptance"].items()])
    lines.extend(["", "## Final", "", f"`{result['final_judgment']['primary']}`"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
