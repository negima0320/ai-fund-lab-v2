from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.ai_lifecycle.dataset_to_split import (
    DataSufficiencyPolicy,
    evaluate_data_sufficiency,
    evaluate_label_safe_availability,
    stable_json_hash,
    validate_dataset_revision_binding,
    validate_versioned_split_contract,
)


DATASET_REVISION_POLICY_VERSION = "phase19_ad_u2_b_dataset_revision_policy.v1"
CORPORATE_ACTION_POLICY_VERSION = "phase19_ad_u2_b_corporate_action_sufficiency.v1"
ROLLING_BOUNDARY_POLICY_VERSION = "phase19_ad_u2_b_rolling_boundary_policy.v1"
DATASET_INPUT_MANIFEST_SCHEMA_VERSION = "phase19_ad_u2_b_dataset_generation_input_manifest.v1"
PHASE19_AD_U2_C_POLICY_VERSION = "phase19_ad_u2_c_dataset_policy_blocker_closure.v1"
PHASE19_AD_U2_D_POLICY_VERSION = "phase19_ad_u2_d_corporate_action_policy.v1"
PHASE19_AD_U2_F_POLICY_VERSION = "phase19_ad_u2_f_rolling_split_policy.v1"

REVIEW_REQUIRED_BRANCH_DETECTED = "REVIEW_REQUIRED_BRANCH_DETECTED"
REVIEW_REQUIRED_SPLIT_POLICY_MISSING = "REVIEW_REQUIRED_SPLIT_POLICY_MISSING"
NO_RETRAIN_INSUFFICIENT_NEW_DATA = "NO_RETRAIN_INSUFFICIENT_NEW_DATA"
HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
APPROVE_WITH_FORMAL_LIMITATION = "APPROVE_WITH_FORMAL_LIMITATION"
PASS_WITH_FORMAL_LIMITATION = "PASS_WITH_FORMAL_LIMITATION"
ROLLING_SPLIT_POLICY_APPROVED = "ROLLING_SPLIT_POLICY_APPROVED"


@dataclass(frozen=True)
class RevisionPolicy:
    policy_version: str = DATASET_REVISION_POLICY_VERSION
    target_horizon_business_days: int = 20
    authority: str = "Phase19-AD-U2-B Dataset Revision Materialization"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["policy_hash"] = stable_json_hash(payload)
        return payload


@dataclass(frozen=True)
class RollingSplitPolicy:
    policy_version: str
    training_window_business_days: int | None
    validation_window_business_days: int | None
    embargo_business_days: int
    target_horizon_business_days: int
    minimum_training_rows: int | None
    minimum_validation_rows: int | None
    trading_calendar_identity: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["policy_hash"] = stable_json_hash(payload)
        payload["status"] = "PASS" if self.is_complete else REVIEW_REQUIRED_SPLIT_POLICY_MISSING
        return payload

    @property
    def is_complete(self) -> bool:
        return all(
            value is not None
            for value in (
                self.training_window_business_days,
                self.validation_window_business_days,
                self.minimum_training_rows,
                self.minimum_validation_rows,
            )
        )


def materialize_dataset_revision(
    *,
    component: str,
    dataset_dir: Path | str,
    output_root: Path | str,
    source_artifacts: dict[str, Any],
    trading_calendar_identity: str,
    listed_issues_identity: str,
    corporate_action_evidence_ref: str,
    corporate_action_evidence_hash: str,
    previous_dataset_revision: str | None,
    created_at: str,
    policy: RevisionPolicy | None = None,
) -> dict[str, Any]:
    policy_payload = (policy or RevisionPolicy()).to_dict()
    root = Path(dataset_dir)
    metadata = _read_json(root / "dataset_metadata.json")
    manifest = _read_json(root / "hash_manifest.json")
    coverage = _read_json(root / "date_coverage.json")
    lineage = _read_json(root / "lineage.json")
    dataset_path = root / "dataset.parquet"
    actual_dataset_hash = _file_hash(dataset_path)
    dataset_hash = str(manifest.get("dataset_hash") or "")
    source_lineage_hash = stable_json_hash(lineage)
    identity_payload = {
        "component": component,
        "dataset_path": str(dataset_path),
        "dataset_hash": dataset_hash,
        "schema_hash": str(manifest.get("schema_hash") or metadata.get("schema_hash") or ""),
        "source_lineage_hash": source_lineage_hash,
        "target_date_min": coverage.get("target_date_min"),
        "target_date_max": coverage.get("target_date_max"),
        "label_safe_cutoff": (metadata.get("label_safe_cutoff") or {}).get("label_safe_cutoff"),
        "target_horizon_business_days": (metadata.get("label_safe_cutoff") or {}).get("target_horizon_business_days"),
        "policy_hash": policy_payload["policy_hash"],
        "trading_calendar_identity": trading_calendar_identity,
        "listed_issues_identity": listed_issues_identity,
        "corporate_action_evidence_hash": corporate_action_evidence_hash,
        "previous_dataset_revision": previous_dataset_revision,
    }
    revision_hash = stable_json_hash(identity_payload)
    payload = {
        "schema_version": "phase19_ad_u2_b_dataset_revision.v1",
        "dataset_identity": f"{component.lower()}:{stable_json_hash({'component': component, 'dataset_hash': dataset_hash, 'schema_hash': identity_payload['schema_hash']})[:16]}",
        "dataset_revision": f"{component.lower()}_dataset_revision_{revision_hash[:16]}",
        "component": component,
        "dataset_path": str(dataset_path),
        "dataset_hash": dataset_hash,
        "actual_dataset_hash": actual_dataset_hash,
        "schema_hash": identity_payload["schema_hash"],
        "row_count": int(metadata.get("row_count") or 0),
        "target_date_min": coverage.get("target_date_min"),
        "target_date_max": coverage.get("target_date_max"),
        "label_safe_cutoff": identity_payload["label_safe_cutoff"],
        "target_horizon_business_days": identity_payload["target_horizon_business_days"],
        "source_lineage_hash": source_lineage_hash,
        "source_artifacts": source_artifacts,
        "previous_dataset_revision": previous_dataset_revision,
        "created_at": created_at,
        "policy_version": policy_payload["policy_version"],
        "policy_hash": policy_payload["policy_hash"],
        "trading_calendar_identity": trading_calendar_identity,
        "listed_issues_identity": listed_issues_identity,
        "corporate_action_evidence_ref": corporate_action_evidence_ref,
        "corporate_action_evidence_hash": corporate_action_evidence_hash,
        "bootstrap_revision": previous_dataset_revision is None,
        "bootstrap_reason": "no prior materialized Phase19 dataset revision artifact exists" if previous_dataset_revision is None else "",
    }
    validation = validate_dataset_revision_binding(
        revision=payload,
        dataset_file_exists=dataset_path.is_file(),
        actual_dataset_hash=actual_dataset_hash,
    )
    payload["revision_hash"] = revision_hash
    payload["validation"] = validation
    path = Path(output_root) / component.lower() / f"{payload['dataset_revision']}.json"
    atomic_write_json(path, payload)
    append_jsonl(Path(output_root) / component.lower() / "revision_history.jsonl", {"dataset_revision": payload["dataset_revision"], "artifact_path": str(path), "created_at": created_at})
    return {**payload, "artifact_path": str(path)}


def validate_revision_chain(
    *,
    revisions: list[dict[str, Any]],
    allowed_schema_change: bool = False,
) -> dict[str, Any]:
    by_id = {str(rev.get("dataset_revision")): rev for rev in revisions}
    children: dict[str, list[str]] = {}
    blockers: list[str] = []
    review: list[str] = []
    for rev in revisions:
        rid = str(rev.get("dataset_revision") or "")
        parent = rev.get("previous_dataset_revision")
        if parent is None:
            continue
        parent_id = str(parent)
        children.setdefault(parent_id, []).append(rid)
        if parent_id == rid:
            blockers.append("revision_self_cycle")
        if parent_id not in by_id:
            review.append("parent_revision_missing")
            continue
        parent_rev = by_id[parent_id]
        if parent_rev.get("schema_hash") != rev.get("schema_hash") and not allowed_schema_change:
            review.append("schema_changed_without_policy")
        if str(rev.get("target_date_max") or "") < str(parent_rev.get("target_date_max") or ""):
            blockers.append("target_range_regressed")
    if _has_cycle(by_id):
        blockers.append("revision_cycle")
    if any(len(items) > 1 for items in children.values()):
        review.append(REVIEW_REQUIRED_BRANCH_DETECTED)
    status = "BLOCK" if blockers else ("REVIEW_REQUIRED" if review else "PASS")
    return {
        "status": status,
        "blockers": sorted(set(blockers)),
        "review_reasons": sorted(set(review)),
        "revision_count": len(revisions),
        "children_by_parent": children,
    }


def evaluate_corporate_action_sufficiency(
    *,
    source_identity: str,
    source_cutoff: str,
    adjusted_price_fields: list[str],
    listed_issue_history_available: bool,
    known_limitations: list[str] | None = None,
    future_corporate_action_leakage: bool = False,
    missing_delisting_handling: bool = False,
) -> dict[str, Any]:
    policy_payload = {
        "corporate_action_policy_version": CORPORATE_ACTION_POLICY_VERSION,
        "source_identity": source_identity,
        "source_cutoff": source_cutoff,
        "minimum_acceptance": {
            "price_adjustment_lineage_valid": bool(adjusted_price_fields),
            "future_corporate_action_not_applied_before_availability": not future_corporate_action_leakage,
            "delisted_issues_do_not_silently_disappear": not missing_delisting_handling and listed_issue_history_available,
            "code_changes_do_not_merge_unrelated_securities": "UNKNOWN",
            "restatements_are_versioned": "UNKNOWN",
            "listed_issues_source_is_pit_consistent": listed_issue_history_available,
        },
    }
    policy_payload["corporate_action_policy_hash"] = stable_json_hash(policy_payload)
    fields = {
        "adjusted_price_fields": adjusted_price_fields,
        "adjustment_factor_available": "UNKNOWN",
        "listed_issue_history_available": listed_issue_history_available,
        "delisting_handling": "PIT_LISTED_ISSUES_AVAILABLE" if listed_issue_history_available and not missing_delisting_handling else "UNKNOWN",
        "code_change_handling": "UNKNOWN",
        "merger_handling": "UNKNOWN",
        "stock_transfer_handling": "UNKNOWN",
        "restatement_handling": "UNKNOWN",
        "pit_availability": "PARTIAL" if listed_issue_history_available else "UNKNOWN",
    }
    if future_corporate_action_leakage:
        decision = "BLOCK"
    elif missing_delisting_handling:
        decision = "REVIEW_REQUIRED"
    elif any(value == "UNKNOWN" for value in fields.values()):
        decision = "PASS_WITH_LIMITATION"
    else:
        decision = "PASS"
    return {
        **policy_payload,
        **fields,
        "known_limitations": known_limitations or [],
        "decision": decision,
        "implicit_pass_used": False,
    }


def build_corporate_action_acceptance_policy(
    *,
    source_inventory: dict[str, Any],
    feature_impact_matrix: list[dict[str, Any]],
    reviewer_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decisions: list[dict[str, Any]] = []
    blockers: list[str] = []
    review_reasons: list[str] = []
    for item in feature_impact_matrix:
        event_type = str(item.get("event_type") or "")
        evidence_status = str(item.get("evidence_status") or "UNKNOWN")
        future_leakage_guard = bool(item.get("future_leakage_guard"))
        decision = "PASS"
        if not future_leakage_guard:
            decision = "BLOCK"
            blockers.append(f"{event_type}:future_leakage_guard_missing")
        elif evidence_status in {"UNKNOWN", "PARTIAL"}:
            decision = HUMAN_REVIEW_REQUIRED
            review_reasons.append(f"{event_type}:{evidence_status.lower()}")
        decisions.append({**item, "policy_decision": decision})

    policy = {
        "schema_version": PHASE19_AD_U2_C_POLICY_VERSION,
        "policy_type": "corporate_action_acceptance_policy",
        "source_inventory_hash": stable_json_hash(source_inventory),
        "feature_impact_matrix_hash": stable_json_hash(feature_impact_matrix),
        "decisions": decisions,
        "implicit_pass_used": False,
        "reviewer_decision": reviewer_decision,
    }
    policy["policy_hash"] = stable_json_hash({key: value for key, value in policy.items() if key != "reviewer_decision"})
    if blockers:
        status = "BLOCK"
    elif review_reasons and not _review_approves_hash(reviewer_decision, policy["policy_hash"]):
        status = HUMAN_REVIEW_REQUIRED
    else:
        status = "PASS"
    return {
        **policy,
        "status": status,
        "blockers": sorted(set(blockers)),
        "review_reasons": sorted(set(review_reasons)),
    }


def build_corporate_action_policy_contract(
    *,
    policy_id: str,
    effective_from: str,
    authority: str,
    decision_reason: str,
    review_reference: str,
    source_authorities: dict[str, Any],
) -> dict[str, Any]:
    contract = {
        "schema_version": PHASE19_AD_U2_D_POLICY_VERSION,
        "policy_id": policy_id,
        "policy_version": PHASE19_AD_U2_D_POLICY_VERSION,
        "effective_from": effective_from,
        "authority": authority,
        "decision": APPROVE_WITH_FORMAL_LIMITATION,
        "decision_reason": decision_reason,
        "scope": [
            "COMMON_PIT_DATASET",
            "CANDIDATE_AI_INPUT",
            "OPPORTUNITY_AI_INPUT",
            "LABEL_GENERATION",
        ],
        "allowed_inputs": [
            "J-Quants derived PIT market data",
            "PIT-consistent listed issues",
            "Formal trading calendar",
            "Price/volume data available at the historical point in time",
            "Adjusted fields only when their historical availability is proven",
        ],
        "prohibited_inputs": [
            "Future Corporate Action announcement",
            "Future effective event",
            "Future adjustment information",
            "Retrospectively corrected price not available at target time",
            "Backtest result",
            "Runtime result",
            "Paper result",
            "Broker state",
            "Test result",
            "Audit result",
        ],
        "dataset_responsibility": [
            "preserve point-in-time availability",
            "prevent future leakage",
            "guarantee label-safe availability",
            "produce trainable price and volume series",
            "exclude or block rows corrupted by corporate action inconsistency",
            "record source cutoff, revision, and policy hash",
        ],
        "ai_responsibility": [
            "use only formal features passed by the dataset layer",
            "do not directly interpret corporate action events",
            "do not ingest future events",
            "do not train on test, audit, runtime, paper, broker, or PnL results",
        ],
        "formal_limitations": {
            "standalone_accepted_corporate_action_event_sot": "NOT_AVAILABLE",
            "adjustment_factor_dedicated_sot": "NOT_FORMALLY_ACCEPTED",
            "code_change_mapping": "NOT_FORMALLY_ACCEPTED",
            "merger_stock_transfer_mapping": "NOT_FORMALLY_ACCEPTED",
            "restatement_lifecycle": "NOT_FORMALLY_ACCEPTED",
        },
        "hard_block_conditions": [
            "FUTURE_CORPORATE_ACTION_LEAKAGE",
            "FUTURE_ADJUSTMENT_LEAKAGE",
            "PIT_AVAILABILITY_UNPROVEN",
            "SECURITY_IDENTITY_COLLISION",
            "HISTORICAL_UNIVERSE_SILENT_REMOVAL",
            "CORPORATE_ACTION_FEATURE_CORRUPTION",
            "CORPORATE_ACTION_LABEL_CORRUPTION",
            "SOURCE_REVISION_UNBOUND",
            "POLICY_HASH_MISMATCH",
        ],
        "source_authorities": source_authorities,
        "known_unsupported_events": [
            "standalone corporate action event feed",
            "dedicated adjustment factor feed",
            "code change mapping",
            "merger mapping",
            "stock transfer mapping",
            "restatement lifecycle",
        ],
        "review_reference": review_reference,
    }
    contract["policy_hash"] = stable_json_hash(_corporate_action_policy_hash_payload(contract))
    contract["reviewed_hash"] = contract["policy_hash"]
    return contract


def build_corporate_action_policy_human_review(
    *,
    review_id: str,
    reviewer: str,
    reviewed_at: str,
    policy_contract: dict[str, Any],
    evidence_paths: list[str],
    decision_reason: str,
) -> dict[str, Any]:
    if not reviewer or reviewer.lower().startswith("codex"):
        status = "INVALID"
        reason_codes = ["missing_or_invalid_reviewer"]
    else:
        status = "PASS"
        reason_codes = []
    return {
        "schema_version": PHASE19_AD_U2_D_POLICY_VERSION,
        "review_id": review_id,
        "policy_id": policy_contract.get("policy_id"),
        "policy_version": policy_contract.get("policy_version"),
        "reviewed_at": reviewed_at,
        "reviewer": reviewer,
        "decision": APPROVE_WITH_FORMAL_LIMITATION,
        "decision_reason": decision_reason,
        "reviewed_hash": policy_contract.get("policy_hash"),
        "approved_limitations": policy_contract.get("formal_limitations", {}),
        "hard_block_conditions": policy_contract.get("hard_block_conditions", []),
        "required_followups": [
            "materialize standalone corporate action event SoT before using events as AI inputs",
            "materialize code change and restatement lifecycle before treating those events as fully supported",
            "keep rolling split policy human-review gated until threshold policy is approved",
        ],
        "evidence_paths": evidence_paths,
        "status": status,
        "reason_codes": reason_codes,
    }


def validate_corporate_action_review_binding(
    *,
    policy_contract: dict[str, Any],
    human_review: dict[str, Any],
) -> dict[str, Any]:
    reason_codes: list[str] = []
    if human_review.get("status") != "PASS":
        reason_codes.append("human_review_invalid")
    if human_review.get("decision") != APPROVE_WITH_FORMAL_LIMITATION:
        reason_codes.append("decision_not_approve_with_formal_limitation")
    if human_review.get("reviewed_hash") != policy_contract.get("policy_hash"):
        reason_codes.append("reviewed_hash_mismatch")
    if not human_review.get("reviewer") or str(human_review.get("reviewer")).lower().startswith("codex"):
        reason_codes.append("missing_or_invalid_reviewer")
    return {
        "schema_version": PHASE19_AD_U2_D_POLICY_VERSION,
        "status": "PASS" if not reason_codes else "BLOCK",
        "reason_codes": reason_codes,
        "policy_hash": policy_contract.get("policy_hash"),
        "reviewed_hash": human_review.get("reviewed_hash"),
    }


def evaluate_corporate_action_policy_sufficiency(
    *,
    policy_contract: dict[str, Any],
    human_review: dict[str, Any],
    label_safe_authority: dict[str, Any],
    current_feature_label_requires_standalone_event: bool,
    future_corporate_action_leakage: bool = False,
    future_adjustment_leakage: bool = False,
    pit_availability_unproven: bool = False,
    security_identity_collision: bool = False,
    historical_universe_silent_removal: bool = False,
    feature_corruption: bool = False,
    label_corruption: bool = False,
    source_revision_unbound: bool = False,
    policy_hash_mismatch: bool = False,
    unknown_unsupported_event_feature_impact: bool = False,
) -> dict[str, Any]:
    binding = validate_corporate_action_review_binding(policy_contract=policy_contract, human_review=human_review)
    hard_block_flags = {
        "FUTURE_CORPORATE_ACTION_LEAKAGE": future_corporate_action_leakage,
        "FUTURE_ADJUSTMENT_LEAKAGE": future_adjustment_leakage,
        "PIT_AVAILABILITY_UNPROVEN": pit_availability_unproven,
        "SECURITY_IDENTITY_COLLISION": security_identity_collision,
        "HISTORICAL_UNIVERSE_SILENT_REMOVAL": historical_universe_silent_removal,
        "CORPORATE_ACTION_FEATURE_CORRUPTION": feature_corruption,
        "CORPORATE_ACTION_LABEL_CORRUPTION": label_corruption,
        "SOURCE_REVISION_UNBOUND": source_revision_unbound,
        "POLICY_HASH_MISMATCH": policy_hash_mismatch or binding["status"] != "PASS",
    }
    blockers = [name for name, active in hard_block_flags.items() if active]
    review_reasons: list[str] = []
    if label_safe_authority.get("overall_status", label_safe_authority.get("status")) != "PASS":
        review_reasons.append("label_safe_authority_not_pass")
    if current_feature_label_requires_standalone_event:
        review_reasons.append("standalone_event_required_by_current_feature_or_label")
    if unknown_unsupported_event_feature_impact:
        review_reasons.append("unknown_unsupported_event_possible_feature_impact")
    if blockers:
        decision = "BLOCK"
    elif review_reasons:
        decision = "REVIEW_REQUIRED"
    else:
        decision = PASS_WITH_FORMAL_LIMITATION
    return {
        "schema_version": PHASE19_AD_U2_D_POLICY_VERSION,
        "decision": decision,
        "hard_block_flags": hard_block_flags,
        "blockers": blockers,
        "review_reasons": review_reasons,
        "policy_hash": policy_contract.get("policy_hash"),
        "reviewed_hash": human_review.get("reviewed_hash"),
        "binding": binding,
        "formal_limitations": policy_contract.get("formal_limitations", {}),
        "implicit_pass_used": False,
    }


def audit_prohibited_training_input_references(
    references: list[dict[str, Any]],
) -> dict[str, Any]:
    prohibited_classes = {
        "Backtest result",
        "Runtime PnL",
        "Paper Ledger",
        "Broker Snapshot",
        "selected",
        "bought",
        "cash",
        "portfolio value",
        "test result",
        "audit result",
        "future corporate action data",
        "future adjustment data",
    }
    violations = []
    for ref in references:
        classification = ref.get("classification")
        term = ref.get("term")
        if classification in {"TRAINING_INPUT", "TRAINING_TARGET", "AUTOMATIC_PROMOTION_METRIC"} and term in prohibited_classes:
            violations.append(ref)
    return {
        "schema_version": PHASE19_AD_U2_D_POLICY_VERSION,
        "status": "BLOCK" if violations else "PASS",
        "violations": violations,
        "reference_count": len(references),
    }


def build_policy_amended_dataset_revision(
    *,
    previous_revision: dict[str, Any],
    policy_contract: dict[str, Any],
    sufficiency: dict[str, Any],
    created_at: str,
    output_root: Path | str | None = None,
) -> dict[str, Any]:
    amendment = {
        "amendment_type": "corporate_action_policy_binding",
        "previous_dataset_revision": previous_revision.get("dataset_revision"),
        "dataset_hash": previous_revision.get("dataset_hash"),
        "schema_hash": previous_revision.get("schema_hash"),
        "corporate_action_policy_id": policy_contract.get("policy_id"),
        "corporate_action_policy_version": policy_contract.get("policy_version"),
        "corporate_action_policy_hash": policy_contract.get("policy_hash"),
        "corporate_action_decision": sufficiency.get("decision"),
    }
    revision_hash = stable_json_hash(amendment)
    payload = {
        **previous_revision,
        "schema_version": "phase19_ad_u2_d_policy_amended_dataset_revision.v1",
        "dataset_revision": f"{str(previous_revision.get('component') or 'dataset').lower()}_dataset_revision_policy_amended_{revision_hash[:16]}",
        "previous_dataset_revision": previous_revision.get("dataset_revision"),
        "previous_revision_artifact_path": previous_revision.get("artifact_path"),
        "policy_amended_revision": True,
        "dataset_bytes_reused": True,
        "created_at": created_at,
        "corporate_action_policy_id": policy_contract.get("policy_id"),
        "corporate_action_policy_version": policy_contract.get("policy_version"),
        "corporate_action_policy_hash": policy_contract.get("policy_hash"),
        "corporate_action_decision": sufficiency.get("decision"),
        "corporate_action_limitations": policy_contract.get("formal_limitations", {}),
        "revision_hash": revision_hash,
    }
    if output_root is not None:
        path = Path(output_root) / str(previous_revision.get("component", "dataset")).lower() / f"{payload['dataset_revision']}.json"
        atomic_write_json(path, payload)
        append_jsonl(
            Path(output_root) / str(previous_revision.get("component", "dataset")).lower() / "revision_history.jsonl",
            {"dataset_revision": payload["dataset_revision"], "previous_dataset_revision": payload["previous_dataset_revision"], "artifact_path": str(path), "created_at": created_at},
        )
        payload["artifact_path"] = str(path)
    return payload


def build_approved_rolling_split_policy_contract(
    *,
    policy_id: str,
    effective_from: str,
    reviewer: str,
    source_draft: dict[str, Any],
    trading_calendar_identity: str,
) -> dict[str, Any]:
    contract = {
        "schema_version": PHASE19_AD_U2_F_POLICY_VERSION,
        "policy_id": policy_id,
        "policy_version": PHASE19_AD_U2_F_POLICY_VERSION,
        "policy_status": ROLLING_SPLIT_POLICY_APPROVED,
        "decision": "APPROVE",
        "approved_option": "OPTION_C_CAPPED_EXPANDING_HYBRID",
        "window_type": "CAPPED_EXPANDING_HYBRID",
        "training_window_rule": "use available history, capped around the project-wide approximately five-year learning policy; concrete business-day boundaries are computed from the formal trading calendar",
        "training_window_cap": "approximately five years by formal trading calendar",
        "validation_window_rule": "maintain an independent validation period; concrete business-day count is not fixed in AD-U2-F",
        "test_window_rule": "maintain an independent test period",
        "recent_holdout_rule": "maintain recent holdout for recent regime confirmation",
        "target_horizon_business_days": 20,
        "embargo_business_days": 20,
        "embargo_rule": "embargo_business_days equals target_horizon_business_days",
        "component_scope": "COMMON_TEMPORAL_POLICY_PLUS_COMPONENT_SPECIFIC_MINIMUMS",
        "bootstrap_behavior": "previous revision delta is not required for bootstrap when full history, label-safe, Corporate Action policy, and Split policy pass",
        "retraining_behavior": "requires incremental label-safe business days, incremental rows, schema continuity, and lineage continuity",
        "deferred_model_quality_decisions": [
            "minimum_training_rows",
            "minimum_validation_rows",
            "minimum_positive_labels",
            "minimum_negative_labels",
            "maximum_missing_ratio",
        ],
        "trading_calendar_identity": trading_calendar_identity,
        "source_draft_policy_hash": source_draft.get("policy_hash"),
        "effective_from": effective_from,
        "authority": "User Human Review decision for Phase19-AD-U2-F",
        "reviewer": reviewer,
        "split_generation_allowed": True,
        "runtime_consumed": False,
    }
    contract["policy_hash"] = stable_json_hash(_rolling_split_policy_hash_payload(contract))
    contract["reviewed_hash"] = contract["policy_hash"]
    return contract


def build_rolling_split_policy_human_review_approval(
    *,
    review_id: str,
    reviewer: str,
    reviewed_at: str,
    policy_contract: dict[str, Any],
    decision_reason: str,
    evidence_paths: list[str],
) -> dict[str, Any]:
    valid_reviewer = bool(reviewer) and not str(reviewer).lower().startswith("codex")
    return {
        "schema_version": PHASE19_AD_U2_F_POLICY_VERSION,
        "review_id": review_id,
        "policy_area": "ROLLING_SPLIT_POLICY",
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "decision": "APPROVE" if valid_reviewer else "INVALID",
        "policy_decision": "OPTION_C_CAPPED_EXPANDING_HYBRID",
        "decision_reason": decision_reason,
        "reviewed_hash": policy_contract.get("policy_hash"),
        "evidence_paths": evidence_paths,
        "deferred_model_quality_decisions": policy_contract.get("deferred_model_quality_decisions", []),
        "status": "PASS" if valid_reviewer else "INVALID",
        "reason_codes": [] if valid_reviewer else ["missing_or_invalid_reviewer"],
    }


def validate_rolling_split_review_binding(
    *,
    policy_contract: dict[str, Any],
    human_review: dict[str, Any],
) -> dict[str, Any]:
    reason_codes: list[str] = []
    if human_review.get("status") != "PASS":
        reason_codes.append("human_review_invalid")
    if human_review.get("decision") != "APPROVE":
        reason_codes.append("decision_not_approve")
    if human_review.get("policy_decision") != "OPTION_C_CAPPED_EXPANDING_HYBRID":
        reason_codes.append("policy_decision_mismatch")
    if human_review.get("reviewed_hash") != policy_contract.get("policy_hash"):
        reason_codes.append("reviewed_hash_mismatch")
    if policy_contract.get("policy_status") != ROLLING_SPLIT_POLICY_APPROVED:
        reason_codes.append("policy_not_approved")
    return {
        "schema_version": PHASE19_AD_U2_F_POLICY_VERSION,
        "status": "PASS" if not reason_codes else "BLOCK",
        "reason_codes": reason_codes,
        "policy_hash": policy_contract.get("policy_hash"),
        "reviewed_hash": human_review.get("reviewed_hash"),
    }


def build_versioned_split_from_evidence(
    *,
    component: str,
    dataset_revision: dict[str, Any],
    split_evidence: dict[str, Any],
    policy_contract: dict[str, Any],
    created_at: str,
) -> dict[str, Any]:
    if policy_contract.get("policy_status") != ROLLING_SPLIT_POLICY_APPROVED:
        return {
            "status": "BLOCK",
            "reason_codes": ["rolling_split_policy_not_approved"],
            "split_id": None,
            "runtime_consumed": False,
        }
    payload = {
        "schema_version": "phase19_ad_u2_f_versioned_rolling_split.v1",
        "component": component,
        "dataset_revision": dataset_revision.get("dataset_revision"),
        "dataset_hash": dataset_revision.get("dataset_hash"),
        "schema_hash": dataset_revision.get("schema_hash"),
        "split_method": "CAPPED_EXPANDING_HYBRID",
        "train_start": split_evidence.get("train_start"),
        "train_end": split_evidence.get("train_end"),
        "validation_start": split_evidence.get("validation_start"),
        "validation_end": split_evidence.get("validation_end"),
        "test_start": split_evidence.get("test_start"),
        "test_end": split_evidence.get("test_end"),
        "recent_holdout_start": split_evidence.get("recent_holdout_start") or split_evidence.get("holdout_start"),
        "recent_holdout_end": split_evidence.get("recent_holdout_end") or split_evidence.get("holdout_end"),
        "train_business_days": split_evidence.get("train_business_days"),
        "validation_business_days": split_evidence.get("validation_business_days"),
        "test_business_days": split_evidence.get("test_business_days"),
        "recent_holdout_business_days": split_evidence.get("recent_holdout_business_days") or split_evidence.get("holdout_business_days"),
        "target_horizon_business_days": policy_contract.get("target_horizon_business_days"),
        "embargo_business_days": policy_contract.get("embargo_business_days"),
        "embargo_rule": policy_contract.get("embargo_rule"),
        "policy_id": policy_contract.get("policy_id"),
        "policy_version": policy_contract.get("policy_version"),
        "policy_hash": policy_contract.get("policy_hash"),
        "trading_calendar_identity": policy_contract.get("trading_calendar_identity"),
        "deferred_model_quality_decisions": policy_contract.get("deferred_model_quality_decisions", []),
        "generation_input_artifact": True,
        "runtime_consumed": False,
        "created_at": created_at,
    }
    payload["split_id"] = f"split_{stable_json_hash(payload)[:16]}"
    return payload


def validate_approved_versioned_split(
    *,
    split: dict[str, Any],
    dataset_revision: dict[str, Any],
    label_safe_authority: dict[str, Any],
    policy_contract: dict[str, Any],
) -> dict[str, Any]:
    reason_codes: list[str] = []
    if split.get("policy_hash") != policy_contract.get("policy_hash"):
        reason_codes.append("policy_hash_mismatch")
    if split.get("embargo_business_days") != split.get("target_horizon_business_days"):
        reason_codes.append("embargo_not_equal_target_horizon")
    if not split.get("trading_calendar_identity"):
        reason_codes.append("trading_calendar_identity_missing")
    if str(split.get("recent_holdout_end") or "") > str(label_safe_authority.get("dataset_max") or label_safe_authority.get("dataset_target_date_max") or ""):
        reason_codes.append("holdout_after_label_safe_dataset_max")
    if split.get("dataset_revision") != dataset_revision.get("dataset_revision"):
        reason_codes.append("dataset_revision_mismatch")
    ordered = [
        split.get("train_start"),
        split.get("train_end"),
        split.get("validation_start"),
        split.get("validation_end"),
        split.get("test_start"),
        split.get("test_end"),
        split.get("recent_holdout_start"),
        split.get("recent_holdout_end"),
    ]
    if any(not item for item in ordered):
        reason_codes.append("split_boundary_missing")
    elif ordered != sorted(ordered):
        reason_codes.append("split_temporal_order_invalid")
    return {
        "schema_version": PHASE19_AD_U2_F_POLICY_VERSION,
        "status": "PASS" if not reason_codes else "BLOCK",
        "reason_codes": reason_codes,
        "split_id": split.get("split_id"),
        "runtime_consumed": False,
    }


def evaluate_formal_label_safe_cutoff_authority(
    *,
    dataset_revision: dict[str, Any],
    latest_source_market_date: str,
    legacy_metadata_label_safe_cutoff: str | None,
    trading_calendar_dates: list[str],
    target_horizon_business_days: int = 20,
    unavailable_label_rows: int = 0,
) -> dict[str, Any]:
    dataset_max = str(dataset_revision.get("target_date_max") or "")
    computed_cutoff = _business_day_cutoff(
        latest_source_market_date=latest_source_market_date,
        trading_calendar_dates=trading_calendar_dates,
        target_horizon_business_days=target_horizon_business_days,
    )
    mismatch = bool(legacy_metadata_label_safe_cutoff and legacy_metadata_label_safe_cutoff != computed_cutoff)
    checks = {
        "dataset_max_not_after_computed_cutoff": bool(dataset_max) and dataset_max <= computed_cutoff,
        "dataset_not_after_latest_source_market_date": bool(dataset_max) and dataset_max <= latest_source_market_date,
        "per_symbol_labels_available": int(unavailable_label_rows) == 0,
        "computed_cutoff_from_trading_calendar": bool(computed_cutoff),
    }
    reason_codes = [name for name, passed in checks.items() if not passed]
    if mismatch:
        reason_codes.append("legacy_metadata_cutoff_mismatch_recorded")
    status = "PASS" if all(checks.values()) else "REVIEW_REQUIRED"
    return {
        "schema_version": PHASE19_AD_U2_C_POLICY_VERSION,
        "status": status,
        "reason_codes": reason_codes,
        "checks": checks,
        "cutoff_authority": "AI Lifecycle cutoff resolver using formal trading calendar",
        "latest_source_market_date": latest_source_market_date,
        "computed_label_safe_cutoff": computed_cutoff,
        "legacy_metadata_label_safe_cutoff": legacy_metadata_label_safe_cutoff,
        "metadata_cutoff_mismatch": mismatch,
        "dataset_target_date_max": dataset_max,
        "target_horizon_business_days": target_horizon_business_days,
        "unavailable_label_rows": int(unavailable_label_rows),
    }


def build_dataset_split_policy_human_review(
    *,
    policy_options: list[dict[str, Any]],
    selected_policy_hash: str | None = None,
    reviewer_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    options_hash = stable_json_hash(policy_options)
    approved = _review_approves_hash(reviewer_decision, selected_policy_hash or "")
    missing_selection = not selected_policy_hash
    status = "PASS" if selected_policy_hash and approved else HUMAN_REVIEW_REQUIRED
    return {
        "schema_version": PHASE19_AD_U2_C_POLICY_VERSION,
        "policy_type": "dataset_split_policy_human_review",
        "status": status,
        "options_hash": options_hash,
        "selected_policy_hash": selected_policy_hash,
        "reviewer_decision": reviewer_decision,
        "review_required": status == HUMAN_REVIEW_REQUIRED,
        "reason_codes": ["split_policy_not_selected"] if missing_selection else (["split_policy_hash_not_approved"] if not approved else []),
    }


def validate_rolling_split_policy_contract(
    *,
    policy: RollingSplitPolicy,
    expected_policy_hash: str | None = None,
    runtime_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = policy.to_dict()
    reason_codes: list[str] = []
    if runtime_override:
        reason_codes.append("runtime_override_prohibited")
    if not policy.is_complete:
        reason_codes.append(REVIEW_REQUIRED_SPLIT_POLICY_MISSING)
    if expected_policy_hash and payload["policy_hash"] != expected_policy_hash:
        reason_codes.append("policy_hash_mismatch")
    return {
        "status": "PASS" if not reason_codes else "REVIEW_REQUIRED",
        "reason_codes": reason_codes,
        "policy": payload,
        "runtime_consumed": False,
    }


def evaluate_bootstrap_vs_retraining_sufficiency(
    *,
    dataset_revision: dict[str, Any],
    label_safe_availability: dict[str, Any],
    split_policy_review: dict[str, Any],
    corporate_action_policy: dict[str, Any],
    previous_generation_ref: str | None,
    incremental_business_days: int,
    incremental_rows: int,
    min_incremental_business_days: int,
    min_incremental_rows: int,
) -> dict[str, Any]:
    retrain_ok = (
        previous_generation_ref is not None
        and incremental_business_days >= min_incremental_business_days
        and incremental_rows >= min_incremental_rows
    )
    bootstrap_blockers = []
    if label_safe_availability.get("status") != "PASS":
        bootstrap_blockers.append("label_safe_not_pass")
    if split_policy_review.get("status") != "PASS":
        bootstrap_blockers.append("split_policy_review_required")
    if corporate_action_policy.get("status") != "PASS":
        bootstrap_blockers.append("corporate_action_policy_not_pass")
    if int(dataset_revision.get("row_count") or 0) <= 0:
        bootstrap_blockers.append("dataset_rows_missing")
    return {
        "schema_version": PHASE19_AD_U2_C_POLICY_VERSION,
        "bootstrap_generation_input_sufficiency": "SUFFICIENT" if not bootstrap_blockers else HUMAN_REVIEW_REQUIRED,
        "bootstrap_blockers": bootstrap_blockers,
        "retrain_trigger_sufficiency": "SUFFICIENT" if retrain_ok else "INSUFFICIENT",
        "retrain_decision_code": "RETRAIN_ALLOWED" if retrain_ok else NO_RETRAIN_INSUFFICIENT_NEW_DATA,
        "previous_generation_ref": previous_generation_ref,
        "incremental_business_days": int(incremental_business_days),
        "incremental_rows": int(incremental_rows),
        "min_incremental_business_days": int(min_incremental_business_days),
        "min_incremental_rows": int(min_incremental_rows),
    }


def generate_rolling_split_from_revision(
    *,
    revision: dict[str, Any],
    policy: RollingSplitPolicy,
    trading_calendar_dates: list[str],
    created_at: str,
) -> dict[str, Any]:
    policy_payload = policy.to_dict()
    if not policy.is_complete:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": REVIEW_REQUIRED_SPLIT_POLICY_MISSING,
            "policy": policy_payload,
            "generation_input_artifact": True,
            "runtime_consumed": False,
        }
    dates = [date for date in sorted(trading_calendar_dates) if str(revision["target_date_min"]) <= date <= str(revision["label_safe_cutoff"])]
    if len(dates) < policy.validation_window_business_days + policy.embargo_business_days + policy.training_window_business_days:
        return {"status": "REVIEW_REQUIRED", "reason": "insufficient_calendar_for_split_policy", "policy": policy_payload}
    validation = dates[-policy.validation_window_business_days :]
    embargo = dates[-(policy.validation_window_business_days + policy.embargo_business_days) : -policy.validation_window_business_days]
    train_candidates = dates[: -(policy.validation_window_business_days + policy.embargo_business_days)]
    train = train_candidates[-policy.training_window_business_days :]
    split_payload = {
        "schema_version": "phase19_ad_u2_b_versioned_rolling_split.v1",
        "dataset_revision": revision["dataset_revision"],
        "component": revision["component"],
        "train_start": train[0],
        "train_end": train[-1],
        "validation_start": validation[0],
        "validation_end": validation[-1],
        "embargo_start": embargo[0],
        "embargo_end": embargo[-1],
        "policy_version": policy.policy_version,
        "policy_hash": policy_payload["policy_hash"],
        "schema_hash": revision["schema_hash"],
        "target_horizon_business_days": policy.target_horizon_business_days,
        "trading_calendar_identity": policy.trading_calendar_identity,
        "generation_input_artifact": True,
        "runtime_consumed": False,
        "created_at": created_at,
    }
    split_payload["split_id"] = f"split_{stable_json_hash(split_payload)[:16]}"
    validation_result = validate_versioned_split_contract(
        split={
            **split_payload,
            "embargo_business_days": policy.embargo_business_days,
            "schema_version": "phase19_ad_u2_a_versioned_rolling_split.v1",
        },
        dataset_revision=revision,
        trading_calendar_dates=trading_calendar_dates,
    )
    return {**split_payload, "status": "PASS" if validation_result["status"] == "PASS" else "BLOCK", "validation": validation_result}


def build_dataset_generation_input_manifest(
    *,
    candidate_revision: dict[str, Any],
    opportunity_revision: dict[str, Any],
    candidate_split: dict[str, Any],
    opportunity_split: dict[str, Any],
    lineage_compatibility: dict[str, Any],
    policy_hashes: dict[str, str],
    created_at: str,
) -> dict[str, Any]:
    payload = {
        "schema_version": DATASET_INPUT_MANIFEST_SCHEMA_VERSION,
        "candidate_dataset_revision": candidate_revision["dataset_revision"],
        "opportunity_dataset_revision": opportunity_revision["dataset_revision"],
        "candidate_split_id": candidate_split.get("split_id"),
        "opportunity_split_id": opportunity_split.get("split_id"),
        "lineage_compatibility": lineage_compatibility,
        "policy_hashes": policy_hashes,
        "generation_input_artifact": True,
        "runtime_consumed": False,
        "created_at": created_at,
    }
    payload["manifest_hash"] = stable_json_hash(payload)
    return payload


def evaluate_materialized_sufficiency(
    *,
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    policy: DataSufficiencyPolicy,
    label_safe_availability: dict[str, Any],
    corporate_action_decision: str,
    incremental_business_days: int,
    incremental_rows: int,
) -> dict[str, Any]:
    result = evaluate_data_sufficiency(
        current=current,
        previous=previous,
        policy=policy,
        label_safe_availability=label_safe_availability,
        incremental_business_days=incremental_business_days,
        incremental_rows=incremental_rows,
    )
    if corporate_action_decision == "BLOCK":
        return {**result, "status": "REVIEW_REQUIRED", "decision_code": "CORPORATE_ACTION_BLOCK", "corporate_action_decision": corporate_action_decision}
    if corporate_action_decision in {"REVIEW_REQUIRED", "PASS_WITH_LIMITATION"}:
        return {**result, "status": "REVIEW_REQUIRED", "decision_code": "CORPORATE_ACTION_REVIEW_REQUIRED", "corporate_action_decision": corporate_action_decision}
    return {**result, "corporate_action_decision": corporate_action_decision}


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=True, indent=2, sort_keys=True, default=str)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_path, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str) + "\n")


def _has_cycle(by_id: dict[str, dict[str, Any]]) -> bool:
    for start in by_id:
        seen: set[str] = set()
        current = start
        while current:
            if current in seen:
                return True
            seen.add(current)
            parent = by_id.get(current, {}).get("previous_dataset_revision")
            current = str(parent) if parent else ""
    return False


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _business_day_cutoff(
    *,
    latest_source_market_date: str,
    trading_calendar_dates: list[str],
    target_horizon_business_days: int,
) -> str:
    dates = [date for date in sorted(set(trading_calendar_dates)) if date <= latest_source_market_date]
    if len(dates) <= target_horizon_business_days:
        return ""
    return dates[-(target_horizon_business_days + 1)]


def _review_approves_hash(reviewer_decision: dict[str, Any] | None, policy_hash: str) -> bool:
    if not reviewer_decision or not policy_hash:
        return False
    return (
        reviewer_decision.get("decision") == "APPROVE"
        and reviewer_decision.get("approved_policy_hash") == policy_hash
        and bool(reviewer_decision.get("reviewer"))
        and bool(reviewer_decision.get("reviewed_at"))
    )


def _corporate_action_policy_hash_payload(contract: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "decision",
        "scope",
        "allowed_inputs",
        "prohibited_inputs",
        "dataset_responsibility",
        "ai_responsibility",
        "formal_limitations",
        "hard_block_conditions",
        "source_authorities",
        "known_unsupported_events",
        "effective_from",
    )
    return {key: contract.get(key) for key in keys}


def _rolling_split_policy_hash_payload(contract: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "policy_id",
        "policy_version",
        "policy_status",
        "decision",
        "approved_option",
        "window_type",
        "training_window_rule",
        "training_window_cap",
        "validation_window_rule",
        "test_window_rule",
        "recent_holdout_rule",
        "target_horizon_business_days",
        "embargo_business_days",
        "embargo_rule",
        "component_scope",
        "bootstrap_behavior",
        "retraining_behavior",
        "deferred_model_quality_decisions",
        "trading_calendar_identity",
        "source_draft_policy_hash",
        "effective_from",
        "authority",
        "reviewer",
        "split_generation_allowed",
    )
    return {key: contract.get(key) for key in keys}
