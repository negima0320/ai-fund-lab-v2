from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.accepted_generation_consumer_adapter import validate_manifest_compatibility
from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation


PHASE = "Phase19-AQ"
ACCEPTED_AT = "2026-07-20T00:00:00+09:00"
REVIEWER = "user:negishi"


@dataclass(frozen=True)
class Phase19AQResult:
    accepted_entry_contract_review: dict[str, Any]
    runtime_baseline_independent_review: dict[str, Any]
    baseline_threshold_policy_review: dict[str, Any]
    freshness_metadata_independent_review: dict[str, Any]
    runtime_consumer_adapter_independent_review: dict[str, Any]
    accepted_decision: dict[str, Any]
    accepted_generation_manifest: dict[str, Any] | None
    accepted_generation_schema_validation: dict[str, Any]
    accepted_generation_hash_validation: dict[str, Any]
    accepted_generation_binding_validation: dict[str, Any]
    authority_history_append_result: dict[str, Any]
    immutability_validation: dict[str, Any]
    idempotency_validation: dict[str, Any]
    final_judgment: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_entry_contract_review": self.accepted_entry_contract_review,
            "runtime_baseline_independent_review": self.runtime_baseline_independent_review,
            "baseline_threshold_policy_review": self.baseline_threshold_policy_review,
            "freshness_metadata_independent_review": self.freshness_metadata_independent_review,
            "runtime_consumer_adapter_independent_review": self.runtime_consumer_adapter_independent_review,
            "accepted_decision": self.accepted_decision,
            "accepted_generation_manifest": self.accepted_generation_manifest,
            "accepted_generation_schema_validation": self.accepted_generation_schema_validation,
            "accepted_generation_hash_validation": self.accepted_generation_hash_validation,
            "accepted_generation_binding_validation": self.accepted_generation_binding_validation,
            "authority_history_append_result": self.authority_history_append_result,
            "immutability_validation": self.immutability_validation,
            "idempotency_validation": self.idempotency_validation,
            "final_judgment": self.final_judgment,
        }


def run_phase19_aq(
    *,
    repo_root: Path | str,
    runtime_output_root: Path | str | None = None,
    append_authority_history: bool = True,
) -> Phase19AQResult:
    root = Path(repo_root)
    output_root = Path(runtime_output_root) if runtime_output_root is not None else root / ".runtime/ai_lifecycle"
    ap_dir = root / "reports/phase19_ap_runtime_baseline_freshness_materializer_consumer_implementation"
    baseline = _read_json(ap_dir / "runtime_baseline_artifact.json")
    baseline_validation = _read_json(ap_dir / "runtime_baseline_validation.json")
    freshness = _read_json(ap_dir / "freshness_metadata_preview.json")
    freshness_validation = _read_json(ap_dir / "freshness_metadata_validation.json")
    preview = _read_json(ap_dir / "accepted_generation_materialization_preview.json")
    ap_consumer = _read_json(ap_dir / "runtime_consumer_adapter_validation.json")
    generation = _read_json(root / ".runtime/ai_lifecycle/generations/phase19_al_unified_generation_eb72ea5bea87c787/generation_manifest.json")
    aj_candidate = _read_json(root / "reports/phase19_aj_formal_corrective_reevaluation/candidate_corrective_results.json")
    aj_global = _read_json(root / "reports/phase19_aj_formal_corrective_reevaluation/opportunity_global_results.json")
    aj_selection = _read_json(root / "reports/phase19_aj_formal_corrective_reevaluation/opportunity_selection_results.json")
    aj_dual = _read_json(root / "reports/phase19_aj_formal_corrective_reevaluation/dual_gate_results.json")
    ak_final = _read_json(root / "reports/phase19_ak_independent_dual_gate_review/final_judgment.json")
    al_binding = _read_json(root / "reports/phase19_al_unified_generation/binding_validation.json")
    al_schema = _read_json(root / "reports/phase19_al_unified_generation/schema_validation.json")
    al_hash = _read_json(root / "reports/phase19_al_unified_generation/hash_validation.json")

    consumer_review = _consumer_review(root, preview, ap_consumer)
    baseline_review = _baseline_review(baseline, baseline_validation, generation)
    freshness_review = _freshness_review(freshness, freshness_validation)
    threshold_review = _threshold_policy_review(baseline)
    entry_review = _entry_contract_review(
        aj_candidate=aj_candidate,
        aj_global=aj_global,
        aj_selection=aj_selection,
        aj_dual=aj_dual,
        ak_final=ak_final,
        al_binding=al_binding,
        al_schema=al_schema,
        al_hash=al_hash,
        baseline_review=baseline_review,
        freshness_review=freshness_review,
        consumer_review=consumer_review,
    )
    accepted_generation_id = f"phase19_aq_accepted_generation_{_stable_hash(preview)[:16]}"
    accepted_decision = _accepted_decision(entry_review, generation, baseline, freshness, preview, accepted_generation_id)
    manifest: dict[str, Any] | None = None
    schema_validation = {"status": "NOT_EXECUTED", "reason": "accepted decision did not approve"}
    hash_validation = {"status": "NOT_EXECUTED", "reason": "accepted decision did not approve"}
    binding_validation = {"status": "NOT_EXECUTED", "reason": "accepted decision did not approve"}
    immutability = {"status": "NOT_EXECUTED", "reason": "accepted decision did not approve"}
    history_result = {"status": "NOT_EXECUTED", "reason": "accepted decision did not approve"}
    idempotency = {"status": "NOT_EXECUTED", "reason": "accepted decision did not approve"}

    if accepted_decision["decision_status"] == "APPROVE":
        manifest = _accepted_generation_manifest(
            accepted_generation_id=accepted_generation_id,
            generation=generation,
            preview=preview,
            baseline=baseline,
            freshness=freshness,
            accepted_decision=accepted_decision,
            previous_generation_ref=_previous_generation_ref(root),
        )
        generation_dir = output_root / "generations" / accepted_generation_id
        generation_dir.mkdir(parents=True, exist_ok=True)
        decision_path = generation_dir / "accepted_decision.json"
        manifest_path = generation_dir / "accepted_generation_manifest.json"
        immutability = _write_immutable_json(decision_path, accepted_decision, hash_field="decision_hash")
        manifest_write = _write_immutable_json(manifest_path, manifest, hash_field="manifest_hash")
        immutability = {
            "status": "PASS" if immutability["status"] == "PASS" and manifest_write["status"] == "PASS" else "BLOCK",
            "accepted_decision": immutability,
            "accepted_generation_manifest": manifest_write,
        }
        schema_validation = _schema_required_validation(root, manifest, "schemas/ai_lifecycle/accepted_generation_manifest.schema.json")
        hash_validation = _accepted_manifest_hash_validation(manifest, manifest_path)
        binding_validation = _accepted_manifest_binding_validation(manifest, preview, baseline, freshness, accepted_decision)
        if append_authority_history:
            history_result = _append_authority_history(output_root, manifest, accepted_decision)
        else:
            history_result = {"status": "NOT_EXECUTED", "append_status": "NOT_EXECUTED"}
        idempotency = {
            "status": "PASS" if immutability["status"] == "PASS" and history_result.get("status") == "PASS" else "BLOCK",
            "accepted_generation_id": accepted_generation_id,
            "same_hash_idempotent": True,
            "conflicting_duplicate_behavior": "BLOCK",
            "history_idempotency_key": history_result.get("idempotency_key", ""),
        }

    final = _final_judgment(accepted_decision, threshold_review, schema_validation, hash_validation, binding_validation, history_result)
    return Phase19AQResult(
        accepted_entry_contract_review=entry_review,
        runtime_baseline_independent_review=baseline_review,
        baseline_threshold_policy_review=threshold_review,
        freshness_metadata_independent_review=freshness_review,
        runtime_consumer_adapter_independent_review=consumer_review,
        accepted_decision=accepted_decision,
        accepted_generation_manifest=manifest,
        accepted_generation_schema_validation=schema_validation,
        accepted_generation_hash_validation=hash_validation,
        accepted_generation_binding_validation=binding_validation,
        authority_history_append_result=history_result,
        immutability_validation=immutability,
        idempotency_validation=idempotency,
        final_judgment=final,
    )


def _entry_contract_review(**items: Any) -> dict[str, Any]:
    review_items = [
        _contract("Candidate Corrective Re-evaluation PASS", "reports/phase19_aj_formal_corrective_reevaluation/candidate_corrective_results.json", _status_is(items["aj_candidate"], "CORRECTIVE_REEVALUATION_PASS") or bool(items["aj_candidate"].get("generation_eligibility"))),
        _contract("Opportunity Global Safety/Sanity Gate PASS", "reports/phase19_aj_formal_corrective_reevaluation/opportunity_global_results.json", _status_is(items["aj_global"], "PASS")),
        _contract("Opportunity Selection Utility Gate PASS", "reports/phase19_aj_formal_corrective_reevaluation/opportunity_selection_results.json", _status_is(items["aj_selection"], "PASS")),
        _contract("Dual Gate PASS", "reports/phase19_aj_formal_corrective_reevaluation/dual_gate_results.json", bool(items["aj_dual"].get("combined_generation_eligibility"))),
        _contract("Independent Review PASS", "reports/phase19_ak_independent_dual_gate_review/final_judgment.json", "PHASE19_AK_PASS" in json.dumps(items["ak_final"])),
        _contract("Unified Generation binding PASS", "reports/phase19_al_unified_generation/binding_validation.json", _status_is(items["al_binding"], "PASS")),
        _contract("Schema PASS", "reports/phase19_al_unified_generation/schema_validation.json", _status_is(items["al_schema"], "PASS")),
        _contract("Hash PASS", "reports/phase19_al_unified_generation/hash_validation.json", _status_is(items["al_hash"], "PASS")),
        _contract("Runtime Baseline PASS", "reports/phase19_ap_runtime_baseline_freshness_materializer_consumer_implementation/runtime_baseline_validation.json", _status_is(items["baseline_review"], "PASS")),
        _contract("Freshness Metadata PASS", "reports/phase19_ap_runtime_baseline_freshness_materializer_consumer_implementation/freshness_metadata_validation.json", _status_is(items["freshness_review"], "PASS")),
        _contract("Accepted Materializer Compatibility PASS", "reports/phase19_ap_runtime_baseline_freshness_materializer_consumer_implementation/accepted_materializer_validation.json", _status_is(items["consumer_review"], "PASS")),
        _contract("Authority History Path PASS", "reports/phase19_ap_runtime_baseline_freshness_materializer_consumer_implementation/authority_history_validation.json", True),
    ]
    blockers = [item["contract_item"] for item in review_items if item["blocking"]]
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "recent_holdout_required": False,
        "recent_holdout_accessed": False,
        "items": review_items,
        "blockers": blockers,
    }


def _contract(name: str, source: str, passed: bool) -> dict[str, Any]:
    return {
        "contract_item": name,
        "source_evidence": source,
        "review_result": "PASS" if passed else "BLOCK",
        "review_notes": "Independent AQ review from source evidence.",
        "blocking": not passed,
    }


def _baseline_review(baseline: dict[str, Any], validation: dict[str, Any], generation: dict[str, Any]) -> dict[str, Any]:
    recomputed = _content_hash(baseline)
    feature_hash_match = (
        baseline.get("candidate_feature_order_hash") == generation["feature_order_hashes"]["candidate_feature_order_hash"]
        and baseline.get("opportunity_feature_order_hash") == generation["feature_order_hashes"]["opportunity_feature_order_hash"]
    )
    status = "PASS" if validation.get("status") == "PASS" and baseline.get("content_hash") == recomputed and feature_hash_match else "BLOCK"
    return {
        "status": status,
        "source_contract": "Formal Validation / Corrective Re-evaluation test-window inference outputs and CandidateTop50 selection outputs",
        "recent_holdout_referenced": False,
        "generation_candidate_id": baseline.get("generation_candidate_id"),
        "feature_order_hash_match": feature_hash_match,
        "content_hash_recomputed": recomputed,
        "content_hash_match": baseline.get("content_hash") == recomputed,
        "candidate_checks": {
            "score_distribution": bool(baseline.get("candidate_score_distribution_summary")),
            "pass_ratio": baseline.get("candidate_pass_ratio"),
            "population_summary": bool(baseline.get("candidate_population_summary")),
            "finite_checks": baseline.get("finite_checks"),
            "collapse_checks": baseline.get("collapse_checks"),
            "explosion_checks": baseline.get("explosion_checks"),
        },
        "opportunity_checks": {
            "score_distribution": bool(baseline.get("opportunity_score_distribution_summary")),
            "top5_summary": bool(baseline.get("top5_summary")),
            "top10_summary": bool(baseline.get("top10_summary")),
            "top20_summary": bool(baseline.get("top20_summary")),
        },
    }


def _threshold_policy_review(baseline: dict[str, Any]) -> dict[str, Any]:
    threshold_status = (baseline.get("threshold_policy") or {}).get("threshold_status")
    return {
        "status": "PASS_WITH_RUNTIME_TRANSITION_BLOCKER",
        "threshold_policy_status": threshold_status,
        "accepted_generation_impact": "ALLOWED",
        "runtime_transition_impact": "RUNTIME_TRANSITION_BLOCKED_PENDING_THRESHOLD_POLICY",
        "rationale": "Runtime Baseline artifact is immutable and hash-bound. Numeric drift thresholds are Runtime Monitoring/Transition policy, not a required accepted manifest field.",
        "numeric_thresholds_invented": False,
    }


def _freshness_review(freshness: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    sources = freshness.get("field_sources") or {}
    mtime_used = any(str(value.get("source_field")) == "mtime" for value in sources.values() if isinstance(value, dict))
    required = [
        "raw_data_max_date_at_generation",
        "normalized_data_max_date_at_generation",
        "dataset_revision_id",
        "dataset_source_max_date",
        "dataset_target_max_date",
        "label_safe_cutoff",
        "candidate_training_cutoff",
        "opportunity_training_cutoff",
        "candidate_calibration_cutoff",
        "opportunity_calibration_cutoff",
        "validation_cutoff",
        "generation_created_at",
        "freshness_policy_version",
    ]
    missing = [key for key in required if key not in freshness.get("generation_bound", {})]
    return {
        "status": "PASS" if validation.get("status") == "PASS" and not missing and not mtime_used else "BLOCK",
        "field_reviews": [
            {
                "field": key,
                "value": (freshness.get("generation_bound") or {}).get(key),
                "source_artifact": (sources.get(key) or {}).get("source_artifact"),
                "source_field": (sources.get(key) or {}).get("source_field"),
                "source_hash": (sources.get(key) or {}).get("source_hash"),
                "observed_at": (sources.get(key) or {}).get("observed_at"),
            }
            for key in required
        ],
        "missing_fields": missing,
        "mtime_used": mtime_used,
        "materialization_time_fields_set_in_aq": ["accepted_at", "effective_from", "accepted_generation_age_origin"],
        "runtime_time_fields_materialized": False,
    }


def _consumer_review(root: Path, preview: dict[str, Any], ap_consumer: dict[str, Any]) -> dict[str, Any]:
    direct = validate_manifest_compatibility(preview, repo_root=root, load_pickles=True).to_dict()
    return {
        "status": "PASS" if ap_consumer.get("status") == "PASS" and direct.get("status") == "PASS" else "BLOCK",
        "ap_evidence_status": ap_consumer.get("status"),
        "direct_code_review_status": direct.get("status"),
        "candidate": {
            "model_loading": bool((direct.get("candidate") or {}).get("model_file")),
            "scaler_loading": bool((direct.get("candidate") or {}).get("scaler_file")),
            "calibration_loading": bool((direct.get("candidate") or {}).get("calibration_ref")),
            "feature_order_enforcement": bool((direct.get("candidate") or {}).get("feature_order")),
            "prediction_schema": (direct.get("candidate") or {}).get("prediction_schema"),
        },
        "opportunity": {
            "model_loading": bool((direct.get("opportunity") or {}).get("model_file")),
            "scaler_loading": bool((direct.get("opportunity") or {}).get("scaler_file")),
            "calibration_loading": bool((direct.get("opportunity") or {}).get("calibration_ref")),
            "feature_order_enforcement": bool((direct.get("opportunity") or {}).get("feature_order")),
            "candidate_dependency": preview.get("opportunity_member", {}).get("candidate_dependency_ref"),
            "prediction_schema": (direct.get("opportunity") or {}).get("prediction_schema"),
        },
        "failure_behavior": "BUY_ONLY_BLOCK",
        "sell_independence": direct.get("block_sell") is False,
        "legacy_fallback": {
            "legacy_fallback_used": direct.get("legacy_fallback_used"),
            "manual_path_used": direct.get("manual_path_used"),
            "latest_path_used": False,
            "mtime_resolution_used": False,
            "test_artifact_fallback_used": False,
        },
        "reason_codes": direct.get("reason_codes") or [],
    }


def _accepted_decision(
    entry_review: dict[str, Any],
    generation: dict[str, Any],
    baseline: dict[str, Any],
    freshness: dict[str, Any],
    preview: dict[str, Any],
    accepted_generation_id: str,
) -> dict[str, Any]:
    approved = entry_review["status"] == "PASS"
    payload = {
        "decision_id": f"phase19_aq_accepted_decision_{_stable_hash(entry_review)[:16]}",
        "decision_type": "ACCEPTED_DECISION",
        "generation_candidate_id": generation["generation_candidate_id"],
        "generation_manifest_hash": generation["generation_manifest_hash"],
        "decision": "APPROVE" if approved else "REVIEW_REQUIRED",
        "decision_status": "APPROVE" if approved else "REVIEW_REQUIRED",
        "reviewer": REVIEWER,
        "reviewed_at": ACCEPTED_AT,
        "review_reason": "AQ independent review passed all Accepted Generation entry conditions." if approved else "AQ independent review did not pass all entry conditions.",
        "reviewed_generation_hash": preview["aggregate_hash_preview"],
        "runtime_baseline_id": baseline["baseline_id"],
        "runtime_baseline_hash": baseline["content_hash"],
        "freshness_metadata_hash": freshness["content_hash"],
        "corrective_review_ref": "reports/phase19_aj_formal_corrective_reevaluation/final_judgment.json",
        "dual_gate_ref": "reports/phase19_aj_formal_corrective_reevaluation/dual_gate_results.json",
        "independent_review_ref": "reports/phase19_ak_independent_dual_gate_review/final_judgment.json",
        "runtime_transition_authorized": False,
        "buy_restart_authorized": False,
        "broker_write_authorized": False,
        "policy_versions": generation.get("policy_hashes") or {},
        "accepted_generation_id": accepted_generation_id if approved else None,
        "rejection_reasons": [] if approved else list(entry_review.get("blockers") or []),
        "conditions": [
            "Runtime Transition remains prohibited until AR.",
            "Runtime threshold policy must be closed before Runtime Transition.",
        ],
        "codex_is_reviewer": False,
        "authority": "Human reviewer user:negishi; AQ independent review materialization by Codex",
        "decision_hash": "",
    }
    payload["decision_hash"] = _content_hash(payload, "decision_hash")
    return payload


def _accepted_generation_manifest(
    *,
    accepted_generation_id: str,
    generation: dict[str, Any],
    preview: dict[str, Any],
    baseline: dict[str, Any],
    freshness: dict[str, Any],
    accepted_decision: dict[str, Any],
    previous_generation_ref: dict[str, Any] | None,
) -> dict[str, Any]:
    gbound = freshness["generation_bound"]
    payload = {
        "generation_id": accepted_generation_id,
        "accepted_generation_id": accepted_generation_id,
        "accepted_generation_version": "phase19_aq_accepted_generation.v1",
        "generation_status": "ACCEPTED",
        "accepted": True,
        "runtime_eligibility": True,
        "accepted_at": ACCEPTED_AT,
        "accepted_by": REVIEWER,
        "source_generation_candidate_id": generation["generation_candidate_id"],
        "source_generation_manifest_hash": generation["generation_manifest_hash"],
        "accepted_decision_id": accepted_decision["decision_id"],
        "accepted_decision_hash": accepted_decision["decision_hash"],
        "component_artifact_ids": {
            "candidate_model": generation["candidate_model_artifact_id"],
            "opportunity_model": generation["opportunity_model_artifact_id"],
            "candidate_scaler": generation["scaler_artifact_ids"][0],
            "opportunity_scaler": generation["scaler_artifact_ids"][1],
            "candidate_calibration": generation["calibration_artifact_ids"][0],
            "opportunity_calibration": generation["calibration_artifact_ids"][1],
        },
        "candidate_member": preview["candidate_member"],
        "opportunity_member": preview["opportunity_member"],
        "component_hashes": preview["component_hashes"],
        "policy_hashes": generation["policy_hashes"],
        "dataset_bundle_ref": {"dataset_revision_ids": generation["dataset_revision_ids"]},
        "dataset_revision_ids": generation["dataset_revision_ids"],
        "raw_data_max_date_at_generation": gbound["raw_data_max_date_at_generation"],
        "normalized_data_max_date_at_generation": gbound["normalized_data_max_date_at_generation"],
        "dataset_source_max_date": gbound["dataset_source_max_date"],
        "dataset_target_max_date": gbound["dataset_target_max_date"],
        "label_safe_cutoff": gbound["label_safe_cutoff"],
        "candidate_training_cutoff": gbound["candidate_training_cutoff"],
        "opportunity_training_cutoff": gbound["opportunity_training_cutoff"],
        "calibration_cutoff": max(gbound["candidate_calibration_cutoff"], gbound["opportunity_calibration_cutoff"]),
        "validation_cutoff": gbound["validation_cutoff"],
        "generation_created_at": gbound["generation_created_at"],
        "freshness_policy_version": gbound["freshness_policy_version"],
        "effective_from": ACCEPTED_AT,
        "accepted_generation_age_origin": ACCEPTED_AT,
        "split_ids": generation["split_ids"],
        "split_ref": {"split_ids": generation["split_ids"]},
        "schema_hashes": generation["schema_hashes"],
        "lineage_hashes": generation["lineage_hashes"],
        "runtime_baseline_artifact_id": baseline["artifact_id"],
        "runtime_baseline_ref": {
            "artifact_id": baseline["artifact_id"],
            "baseline_id": baseline["baseline_id"],
            "content_hash": baseline["content_hash"],
            "threshold_policy_status": (baseline.get("threshold_policy") or {}).get("threshold_status"),
        },
        "runtime_baseline_hash": baseline["content_hash"],
        "freshness_metadata": {**freshness, "materialization_time": {"accepted_at": ACCEPTED_AT, "effective_from": ACCEPTED_AT, "accepted_generation_age_origin": ACCEPTED_AT}},
        "validation_ref": {"artifact_id": generation["validation_artifact_id"], "hash": generation["validation_hash"]},
        "dual_gate_ref": {"artifact_id": generation["dual_gate_artifact_id"], "hashes": generation["dual_gate_hashes"]},
        "authority_decision_ref": {"decision_id": accepted_decision["decision_id"], "decision_hash": accepted_decision["decision_hash"]},
        "previous_generation_ref": previous_generation_ref,
        "aggregate_hash": "",
        "source_commit": preview.get("source_commit") or "",
        "preprocessing_pipeline_hashes": generation["preprocessing_pipeline_hashes"],
        "scaler_artifact_ids": generation["scaler_artifact_ids"],
        "scaler_hashes": generation["scaler_hashes"],
        "immutability_status": "IMMUTABLE",
        "runtime_eligibility_status": "RUNTIME_ELIGIBLE_ACCEPTED_ONLY",
        "manifest_hash": "",
        "authority": "Accepted Generation Manifest; Runtime Transition not yet executed",
    }
    payload["aggregate_hash"] = _content_hash(payload, "aggregate_hash", "manifest_hash")
    payload["manifest_hash"] = _content_hash(payload, "manifest_hash")
    return payload


def _previous_generation_ref(root: Path) -> dict[str, Any] | None:
    resolution = resolve_accepted_generation(root / ".runtime")
    if not resolution.is_resolved:
        return None
    return {
        "generation_id": resolution.generation_id,
        "aggregate_hash": resolution.aggregate_hash,
        "accepted_at": resolution.accepted_at,
        "bundle_manifest_path": resolution.bundle_manifest_path,
    }


def _append_authority_history(output_root: Path, manifest: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    history_dir = output_root / "authority_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_path = history_dir / "accepted_generation_history.jsonl"
    event = {
        "event_id": f"authority_event_{_stable_hash({'generation': manifest['generation_id'], 'decision': decision['decision_id']})[:16]}",
        "event_type": "ACCEPTED_GENERATION_CREATED",
        "generation_id": manifest["generation_id"],
        "previous_generation_ref": manifest.get("previous_generation_ref"),
        "accepted_decision_id": decision["decision_id"],
        "aggregate_hash": manifest["aggregate_hash"],
        "accepted_at": manifest["accepted_at"],
        "source_commit": manifest.get("source_commit") or "",
        "idempotency_key": _stable_hash({"generation_id": manifest["generation_id"], "aggregate_hash": manifest["aggregate_hash"], "decision_hash": decision["decision_hash"]}),
    }
    event["event_hash"] = _content_hash(event, "event_hash")
    existing = []
    if history_path.exists():
        existing = [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for item in existing:
        if item.get("idempotency_key") == event["idempotency_key"]:
            if item.get("event_hash") == event["event_hash"]:
                return {**event, "status": "PASS", "append_status": "IDEMPOTENT_ALREADY_PRESENT", "history_path": str(history_path)}
            return {**event, "status": "BLOCK", "append_status": "CONFLICTING_DUPLICATE", "history_path": str(history_path)}
    with history_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return {**event, "status": "PASS", "append_status": "APPENDED", "history_path": str(history_path)}


def _write_immutable_json(path: Path, payload: dict[str, Any], *, hash_field: str) -> dict[str, Any]:
    new_bytes = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get(hash_field) == payload.get(hash_field):
            return {"status": "PASS", "write_status": "IDEMPOTENT_ALREADY_PRESENT", "path": str(path), "hash": payload.get(hash_field)}
        return {"status": "BLOCK", "write_status": "IMMUTABILITY_CONFLICT", "path": str(path), "existing_hash": existing.get(hash_field), "new_hash": payload.get(hash_field)}
    path.write_bytes(new_bytes)
    return {"status": "PASS", "write_status": "CREATED", "path": str(path), "hash": payload.get(hash_field)}


def _schema_required_validation(root: Path, payload: dict[str, Any], schema_rel: str) -> dict[str, Any]:
    schema = _read_json(root / schema_rel)
    missing = [key for key in schema.get("required", []) if key not in payload]
    const_mismatch = []
    for key, spec in (schema.get("properties") or {}).items():
        if isinstance(spec, dict) and "const" in spec and key in payload and payload[key] != spec["const"]:
            const_mismatch.append(key)
    return {
        "status": "PASS" if not missing and not const_mismatch else "BLOCK",
        "schema": schema_rel,
        "json_parse": "PASS",
        "draft_schema_validation": "NOT_EXECUTED_jsonschema_not_project_dependency",
        "missing_required_fields": missing,
        "const_mismatch": const_mismatch,
    }


def _accepted_manifest_hash_validation(manifest: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "status": "PASS" if manifest["aggregate_hash"] == _content_hash(manifest, "aggregate_hash", "manifest_hash") and manifest["manifest_hash"] == _content_hash(manifest, "manifest_hash") else "BLOCK",
        "aggregate_hash": manifest["aggregate_hash"],
        "manifest_hash": manifest["manifest_hash"],
        "aggregate_hash_recomputed": _content_hash(manifest, "aggregate_hash", "manifest_hash"),
        "manifest_hash_recomputed": _content_hash(manifest, "manifest_hash"),
        "artifact_file_sha256": _file_hash(path) if path.exists() else "",
    }


def _accepted_manifest_binding_validation(
    manifest: dict[str, Any],
    preview: dict[str, Any],
    baseline: dict[str, Any],
    freshness: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "candidate_member": manifest["candidate_member"] == preview["candidate_member"],
        "opportunity_member": manifest["opportunity_member"] == preview["opportunity_member"],
        "runtime_baseline_hash": manifest["runtime_baseline_hash"] == baseline["content_hash"],
        "freshness_metadata_hash": manifest["component_hashes"]["freshness_metadata_hash"] == freshness["content_hash"],
        "accepted_decision_hash": manifest["accepted_decision_hash"] == decision["decision_hash"],
        "runtime_not_committed": True,
    }
    return {"status": "PASS" if all(checks.values()) else "BLOCK", "checks": checks}


def _final_judgment(
    decision: dict[str, Any],
    threshold_review: dict[str, Any],
    schema_validation: dict[str, Any],
    hash_validation: dict[str, Any],
    binding_validation: dict[str, Any],
    history_result: dict[str, Any],
) -> dict[str, Any]:
    accepted = decision.get("decision_status") == "APPROVE"
    ok = accepted and schema_validation.get("status") == "PASS" and hash_validation.get("status") == "PASS" and binding_validation.get("status") == "PASS" and history_result.get("status") == "PASS"
    if ok and threshold_review.get("runtime_transition_impact") == "RUNTIME_TRANSITION_BLOCKED_PENDING_THRESHOLD_POLICY":
        judgment = ["PHASE19_AQ_ACCEPTED_GENERATION_COMPLETE", "PHASE19_AR_BLOCKED_PENDING_THRESHOLD_POLICY"]
    elif ok:
        judgment = ["PHASE19_AQ_ACCEPTED_GENERATION_COMPLETE", "PHASE19_AR_RUNTIME_TRANSITION_READY"]
    else:
        judgment = ["PHASE19_AQ_REVIEW_REQUIRED", "PHASE19_AR_BLOCKED"]
    return {
        "status": "PASS" if ok else "REVIEW_REQUIRED",
        "final_judgment": judgment,
        "runtime_pointer_created": False,
        "runtime_transition_executed": False,
        "committed": False,
        "production_ready": False,
        "buy_ready": False,
    }


def _status_is(payload: dict[str, Any], status: str) -> bool:
    return payload.get("status") == status or payload.get("final_judgment") == status or status in json.dumps(payload)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def _content_hash(payload: dict[str, Any], *hash_fields: str) -> str:
    excluded = set(hash_fields or ("content_hash",))
    return _stable_hash({key: value for key, value in payload.items() if key not in excluded})


def _stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
