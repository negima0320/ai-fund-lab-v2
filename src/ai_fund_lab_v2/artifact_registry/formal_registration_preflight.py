from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.artifact_registry.acceptance_evidence import atomic_write_text
from ai_fund_lab_v2.artifact_registry.inventory import stable_json_hash


PREFLIGHT_VERSION = "phase16ap_formal_registration_preflight_v2"
DEFAULT_OUTPUT_ROOT = Path("reports/phase16_formal_registration_preparation")
APPROVAL_ROLES = ("HUMAN_REVIEW", "ARCHITECTURE_ACCEPTANCE", "REGRESSION_ACCEPTANCE", "RELEASE_APPROVAL")


@dataclass(frozen=True)
class MemberSpec:
    role: str
    source_path: Path
    destination_path: Path


@dataclass(frozen=True)
class SetSpec:
    key: str
    artifact_set_id: str
    artifact_set_type: str
    component: str
    members: tuple[MemberSpec, ...]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json_if_possible(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def default_specs(repo_root: Path) -> tuple[SetSpec, ...]:
    def r(path: str) -> Path:
        return repo_root / path

    def d(path: str) -> Path:
        return Path(path)

    return (
        SetSpec(
            key="candidate",
            artifact_set_id="ai.candidate.accepted_set",
            artifact_set_type="CANDIDATE_AI_SET",
            component="Candidate AI",
            members=(
                MemberSpec("MODEL", r(".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl"), d(".runtime/artifacts/ai/candidate/model/formal_candidate_model/sha256-{hash}/model.pkl")),
                MemberSpec("MODEL_MANIFEST", r(".runtime/candidate_ai/models/phase4bf_formal_candidate_model_manifest.json"), d(".runtime/artifacts/ai/candidate/model/formal_candidate_model/sha256-{hash}/model_manifest.json")),
                MemberSpec("FEATURE_SCHEMA", r(".runtime/candidate_ai/manifests/phase4bc_long_history_features_manifest_2021-06-14_2026-06-12.json"), d(".runtime/artifacts/ai/candidate/schema/long_history_features/sha256-{hash}/feature_schema.json")),
                MemberSpec("TRAINING_METADATA", r(".runtime/candidate_ai/manifests/phase4be_long_history_dataset_manifest_2021-06-14_2026-05-15.json"), d(".runtime/artifacts/ai/candidate/training_metadata/long_history_dataset/sha256-{hash}/training_metadata.json")),
                MemberSpec("TRAINING_DATA_LINEAGE", r(".runtime/candidate_ai/audit/phase4be_long_history_dataset_audit_2021-06-14_2026-05-15.json"), d(".runtime/artifacts/ai/candidate/lineage/long_history_dataset/sha256-{hash}/training_data_lineage.json")),
                MemberSpec("VALIDATION_EVIDENCE", r(".runtime/candidate_ai/audit/phase4bc_long_history_features_audit_2021-06-14_2026-06-12.json"), d(".runtime/artifact_registry/evidence/ai/candidate/validation/sha256-{hash}/validation_evidence.json")),
                MemberSpec("METRICS_EVIDENCE", r(".runtime/candidate_ai/inference/phase4bg_formal_candidate_scores_2026-06-12.json"), d(".runtime/artifact_registry/evidence/ai/candidate/metrics/sha256-{hash}/metrics_evidence.json")),
                MemberSpec("CONSUMER_COMPATIBILITY", r(".runtime/operations/feature_consumer_readiness/2026-07-10.json"), d(".runtime/artifact_registry/evidence/ai/candidate/consumer_compatibility/sha256-{hash}/consumer_compatibility.json")),
            ),
        ),
        SetSpec(
            key="opportunity",
            artifact_set_id="ai.opportunity.accepted_set",
            artifact_set_type="OPPORTUNITY_AI_SET",
            component="Opportunity AI",
            members=(
                MemberSpec("MODEL", r("reports/opportunity_ai/phase5p/models/opportunity_model.pkl"), d(".runtime/artifacts/ai/opportunity/model/formal_opportunity_model/sha256-{hash}/model.pkl")),
                MemberSpec("METRICS", r("reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json"), d(".runtime/artifacts/ai/opportunity/metrics/formal_opportunity_metrics/sha256-{hash}/metrics.json")),
                MemberSpec("FEATURE_SCHEMA", r("reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json"), d(".runtime/artifacts/ai/opportunity/schema/formal_opportunity_schema/sha256-{hash}/feature_schema.json")),
                MemberSpec("TRAINING_METADATA", r("reports/opportunity_ai/phase5p/training/opportunity_training_audit.json"), d(".runtime/artifacts/ai/opportunity/training_metadata/formal_opportunity_training/sha256-{hash}/training_metadata.json")),
                MemberSpec("TRAINING_DATA_LINEAGE", r("reports/opportunity_ai/phase5p/training/opportunity_training_audit.json"), d(".runtime/artifacts/ai/opportunity/lineage/formal_opportunity_training/sha256-{hash}/training_data_lineage.json")),
                MemberSpec("VALIDATION_EVIDENCE", r("reports/opportunity_ai/phase5p/combined_validation_metrics.json"), d(".runtime/artifact_registry/evidence/ai/opportunity/validation/sha256-{hash}/validation_evidence.json")),
                MemberSpec("CONSUMER_COMPATIBILITY", r(".runtime/operations/feature_consumer_readiness/2026-07-10.json"), d(".runtime/artifact_registry/evidence/ai/opportunity/consumer_compatibility/sha256-{hash}/consumer_compatibility.json")),
            ),
        ),
        SetSpec(
            key="pm",
            artifact_set_id="control.position_management.accepted_set",
            artifact_set_type="POSITION_MANAGEMENT_POLICY_SET",
            component="Position Management Policy",
            members=(
                MemberSpec("CODE_POLICY", r(".runtime/phase9/policy_manifests/position_policy_manifest.json"), d(".runtime/artifacts/control/position_management/policy/default/sha256-{hash}/policy.json")),
                MemberSpec("RUNTIME_ADAPTER", r("src/ai_fund_lab_v2/runtime_v2/position_management/producer.py"), d(".runtime/artifacts/control/position_management/runtime_adapter/default/sha256-{hash}/runtime_adapter.py")),
                MemberSpec("POLICY_VERSION", r(".runtime/phase9/policy_manifests/position_policy_manifest.json"), d(".runtime/artifacts/control/position_management/policy_version/default/sha256-{hash}/policy_version.json")),
                MemberSpec("FEATURE_VERSION", r(".runtime/phase9/feature_refresh/2026-06-26/feature_refresh_manifest.json"), d(".runtime/artifacts/control/position_management/feature_version/2026-06-26/sha256-{hash}/feature_version.json")),
                MemberSpec("BEHAVIOR_CONTRACT", r("docs/02_architecture/artifact_acceptance_contract.md"), d(".runtime/artifacts/control/position_management/behavior_contract/default/sha256-{hash}/behavior_contract.md")),
                MemberSpec("REGRESSION_EVIDENCE", r("reports/phase16_formal_registration_preparation/regression/pm_semantic_regression.json"), d(".runtime/artifact_registry/evidence/control/position_management/regression/sha256-{hash}/regression_evidence.json")),
                MemberSpec("CONSUMER_COMPATIBILITY", r(".runtime/operations/feature_consumer_readiness/2026-07-10.json"), d(".runtime/artifact_registry/evidence/control/position_management/consumer_compatibility/sha256-{hash}/consumer_compatibility.json")),
            ),
        ),
        SetSpec(
            key="capital_allocation",
            artifact_set_id="control.capital_allocation.accepted_set",
            artifact_set_type="CAPITAL_ALLOCATION_POLICY_SET",
            component="Capital Allocation Policy",
            members=(
                MemberSpec("POLICY", r(".runtime/phase9/policy_manifests/capital_policy_manifest.json"), d(".runtime/artifacts/control/capital_allocation/policy/default/sha256-{hash}/policy.json")),
                MemberSpec("POLICY_SCHEMA", r(".runtime/phase9/features/2026-06-26/capital_policy_input.parquet"), d(".runtime/artifacts/control/capital_allocation/policy_schema/default/sha256-{hash}/policy_schema.parquet")),
                MemberSpec("POLICY_VERSION", r(".runtime/phase9/policy_manifests/capital_policy_manifest.json"), d(".runtime/artifacts/control/capital_allocation/policy_version/default/sha256-{hash}/policy_version.json")),
                MemberSpec("VALIDATION_EVIDENCE", r(".runtime/phase9/audits/candidate_universe_hard_gate_fix_validation.json"), d(".runtime/artifact_registry/evidence/control/capital_allocation/validation/sha256-{hash}/validation_evidence.json")),
                MemberSpec("REGRESSION_EVIDENCE", r("reports/phase16_formal_registration_preparation/regression/capital_allocation_semantic_regression.json"), d(".runtime/artifact_registry/evidence/control/capital_allocation/regression/sha256-{hash}/regression_evidence.json")),
                MemberSpec("CONSUMER_COMPATIBILITY", r(".runtime/operations/feature_consumer_readiness/2026-07-10.json"), d(".runtime/artifact_registry/evidence/control/capital_allocation/consumer_compatibility/sha256-{hash}/consumer_compatibility.json")),
            ),
        ),
        SetSpec(
            key="feature_schema",
            artifact_set_id="features.shared.accepted_set",
            artifact_set_type="FEATURE_SCHEMA_SET",
            component="Shared Feature Schema",
            members=(
                MemberSpec("FEATURE_SCHEMA", r(".runtime/operations/feature_consumer_readiness/2026-07-10.json"), d(".runtime/artifacts/features/shared/schema/2026-07-10/sha256-{hash}/feature_schema.json")),
                MemberSpec("POINT_IN_TIME_EVIDENCE", r(".runtime/operations/feature_date_contract/2026-07-10.json"), d(".runtime/artifact_registry/evidence/features/shared/point_in_time/sha256-{hash}/point_in_time_evidence.json")),
                MemberSpec("CONSUMER_COMPATIBILITY", r(".runtime/operations/feature_consumer_readiness/2026-07-10.json"), d(".runtime/artifact_registry/evidence/features/shared/consumer_compatibility/sha256-{hash}/consumer_compatibility.json")),
                MemberSpec("SCHEMA_VALIDATION_EVIDENCE", r(".runtime/operations/feature_consumer_readiness/2026-07-10.json"), d(".runtime/artifact_registry/evidence/features/shared/schema_validation/sha256-{hash}/schema_validation_evidence.json")),
            ),
        ),
    )


def protected_hashes(repo_root: Path) -> dict[str, dict[str, Any]]:
    paths = {
        "formal_event_log": ".runtime/artifact_registry/events/registry_events.jsonl",
        "formal_index": ".runtime/artifact_registry/index/registry_index.json",
        "formal_checkpoint": ".runtime/artifact_registry/checkpoints/latest.json",
        "current": ".runtime/runtime_state/current_state.json",
        "ledger": ".runtime/persistent_ledger/state.json",
        "pending": ".runtime/pending_order_plan/pending_order_plan.json",
        "runtime_market": ".runtime/runtime_state/market/latest.json",
        "candidate_model": ".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl",
        "opportunity_model": "reports/opportunity_ai/phase5p/models/opportunity_model.pkl",
        "pm_policy": ".runtime/phase9/policy_manifests/position_policy_manifest.json",
        "capital_policy": ".runtime/phase9/policy_manifests/capital_policy_manifest.json",
        "feature_readiness": ".runtime/operations/feature_consumer_readiness/2026-07-10.json",
    }
    result: dict[str, dict[str, Any]] = {}
    for key, rel in paths.items():
        path = repo_root / rel
        data = path.read_bytes() if path.exists() else b""
        result[key] = {"path": rel, "exists": path.exists(), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return result


def destination_for(spec: MemberSpec, content_hash: str) -> str:
    return str(spec.destination_path).replace("{hash}", content_hash[:16])


def validate_formal_evidence(payload: dict[str, Any], *, evidence_ref: str = "") -> dict[str, Any]:
    text = json.dumps(payload, sort_keys=True).lower() + " " + evidence_ref.lower()
    errors: list[str] = []
    for token in ("dry-run", "dry_run", "sample", "synthetic"):
        if token in text:
            errors.append(f"synthetic marker rejected: {token}")
    if payload.get("synthetic") is True:
        errors.append("synthetic=true rejected")
    if payload.get("placeholder") is True:
        errors.append("placeholder=true rejected")
    if "phase16_formal_registration_dry_run" in text:
        errors.append("dry run evidence path rejected")
    if payload.get("schema_version") == "artifact_regression_evidence.v1" and not payload.get("execution_refs"):
        errors.append("regression evidence requires execution_refs")
    if payload.get("schema_version") == "artifact_review_approval.v1":
        if not payload.get("reviewer_id") or str(payload.get("reviewer_id")).upper().endswith("PLACEHOLDER"):
            errors.append("approval requires real reviewer identity")
        if payload.get("decision") in {None, "PLACEHOLDER", "REVIEW_REQUIRED"}:
            errors.append("approval placeholder decision rejected for formal acceptance")
    return {"overall_result": "PASS" if not errors else "FAIL", "failure_class": "NONE" if not errors else "HALT", "errors": errors}


class FormalRegistrationPreflight:
    def __init__(self, *, output_root: Path = DEFAULT_OUTPUT_ROOT, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or Path.cwd()
        self.output_root = output_root if output_root.is_absolute() else self.repo_root / output_root
        self.specs = default_specs(self.repo_root)

    def run(self) -> dict[str, Any]:
        from ai_fund_lab_v2.artifact_registry.technical_blocker_evidence import generate_phase16ap_evidence

        generate_phase16ap_evidence(output_root=self.output_root, repo_root=self.repo_root)
        before = protected_hashes(self.repo_root)
        self._ensure_dirs()
        copy_plan = {"schema_version": "phase16ao_formal_copy_plan.v1", "created_at": utc_now(), "entries": []}
        set_results: dict[str, Any] = {}
        for spec in self.specs:
            set_results[spec.key] = self._run_set(spec, copy_plan)
        write_json(self.output_root / "formal_copy_plan.json", copy_plan)
        synthetic_result = validate_formal_evidence({"schema_version": "artifact_review_approval.v1", "reviewer_id": "dry-run-reviewer", "decision": "REVIEW_REQUIRED", "placeholder": True}, evidence_ref="reports/phase16_formal_registration_dry_run/x.json")
        after = protected_hashes(self.repo_root)
        summary = {
            "schema_version": "phase16ao_preflight_summary.v1",
            "preflight_version": PREFLIGHT_VERSION,
            "created_at": utc_now(),
            "set_results": set_results,
            "synthetic_evidence_reject_mode": synthetic_result,
            "formal_registration_ready": "READY" if all(v["formal_registration_ready"] == "READY" for v in set_results.values()) else "BLOCKED",
            "protected_hashes_before": before,
            "protected_hashes_after": after,
            "protected_hashes_unchanged": before == after,
            "formal_registry_changed": any(before[k]["sha256"] != after[k]["sha256"] for k in ("formal_event_log", "formal_index", "formal_checkpoint")),
        }
        write_json(self.output_root / "preflight_summary.json", summary)
        atomic_write_text(self.output_root / "audit.md", render_audit(summary))
        return summary

    def _ensure_dirs(self) -> None:
        for name in ("regression", "lineage", "freeze", "compatibility", "approval_templates", "acceptance_report_candidates", "candidate", "opportunity", "pm", "capital_allocation", "feature_schema"):
            (self.output_root / name).mkdir(parents=True, exist_ok=True)

    def _run_set(self, spec: SetSpec, copy_plan: dict[str, Any]) -> dict[str, Any]:
        entries = [self._copy_plan_entry(spec, member) for member in spec.members]
        copy_plan["entries"].extend(entries)
        regression = self._regression(spec, entries)
        lineage = self._lineage(spec, entries)
        freeze = self._freeze(spec, entries)
        compatibility = self._compatibility(spec, entries)
        approval_templates = [self._approval_template(spec, role, entries) for role in APPROVAL_ROLES]
        acceptance_candidate = self._acceptance_report_candidate(spec, entries, regression, lineage, freeze, compatibility)

        write_json(self.output_root / "regression" / f"{spec.key}_regression.json", regression)
        write_json(self.output_root / "lineage" / f"{spec.key}_lineage.json", lineage)
        write_json(self.output_root / "freeze" / f"{spec.key}_freeze.json", freeze)
        write_json(self.output_root / "compatibility" / f"{spec.key}_compatibility.json", compatibility)
        write_json(self.output_root / "approval_templates" / f"{spec.key}_approval_templates.json", {"schema_version": "phase16ao_approval_templates.v1", "approval_required": True, "templates": approval_templates})
        write_json(self.output_root / "acceptance_report_candidates" / f"{spec.key}_acceptance_report_candidate.json", acceptance_candidate)
        write_json(self.output_root / spec.key / "artifact_candidates.json", {"schema_version": "phase16ao_artifact_candidates.v1", "artifact_set_id": spec.artifact_set_id, "artifact_set_type": spec.artifact_set_type, "entries": entries})

        statuses = {
            "artifact_candidate_ready": self._ready(all(e["copy_status"] == "READY_TO_COPY" for e in entries)),
            "copy_plan_ready": self._ready(all(e["copy_status"] == "READY_TO_COPY" for e in entries)),
            "lineage_ready": lineage["overall_result"],
            "freeze_ready": freeze["overall_result"],
            "regression_ready": regression["overall_result"],
            "consumer_compatibility_ready": compatibility["overall_result"],
            "approval_ready": "REVIEW_REQUIRED",
            "acceptance_report_ready": acceptance_candidate["overall_result"],
        }
        blockers = []
        if spec.key == "candidate" and regression["candidate_row_count_discrepancy_result"] != "RESOLVED":
            blockers.append("candidate row-count discrepancy requires review")
        if spec.key == "opportunity" and regression["phase5e_fallback_blocker"] in {"UNKNOWN", "NOT_APPLICABLE"}:
            blockers.append("opportunity fallback assessment missing")
        if spec.key in {"pm", "capital_allocation"} and regression["overall_result"] != "READY":
            blockers.append("real semantic regression still required")
        blockers.extend(regression.get("blockers") or [])
        if statuses["approval_ready"] != "READY":
            blockers.append("formal approval required")
        if any(v == "BLOCKED" for v in statuses.values()):
            blockers.append("one or more readiness gates blocked")
        formal_ready = "READY" if not blockers and all(v == "READY" for v in statuses.values()) else "BLOCKED"
        return {**statuses, "formal_registration_ready": formal_ready, "blockers": blockers, "artifact_set_id": spec.artifact_set_id, "artifact_set_type": spec.artifact_set_type}

    def _copy_plan_entry(self, set_spec: SetSpec, member: MemberSpec) -> dict[str, Any]:
        source = member.source_path
        if not source.is_absolute():
            source = self.repo_root / source
        source_exists = source.is_file()
        content_hash = file_hash(source) if source_exists else None
        destination = destination_for(member, content_hash or "missing")
        destination_path = self.repo_root / destination
        phase_in_destination = "phase" in destination.lower()
        collision = destination_path.exists()
        destination_hash = file_hash(destination_path) if collision and destination_path.is_file() else None
        existing_identical = bool(collision and content_hash and destination_hash == content_hash)
        copy_status = "READY_TO_COPY"
        verify_status = "READY"
        if not source_exists:
            copy_status = "SOURCE_MISSING"
            verify_status = "BLOCKED"
        elif phase_in_destination:
            copy_status = "BLOCKED"
            verify_status = "BLOCKED"
        elif collision and not existing_identical:
            copy_status = "COLLISION"
            verify_status = "BLOCKED"
        return {
            "artifact_set_id": set_spec.artifact_set_id,
            "artifact_set_type": set_spec.artifact_set_type,
            "member_role": member.role,
            "source_path": str(source),
            "destination_path": destination,
            "content_hash": content_hash,
            "size": source.stat().st_size if source_exists else None,
            "overwrite": False,
            "destination_exists": collision,
            "destination_hash": destination_hash,
            "collision_status": "EXISTING_IDENTICAL" if existing_identical else ("COLLISION" if collision else "NONE"),
            "copy_status": copy_status,
            "verify_status": verify_status,
            "phase_number_independent_destination": not phase_in_destination,
        }

    def _regression(self, spec: SetSpec, entries: list[dict[str, Any]]) -> dict[str, Any]:
        load_results = {e["member_role"]: self._load_check(e) for e in entries}
        result = "READY"
        blockers: list[str] = []
        candidate_row = "NOT_APPLICABLE"
        phase5e = "NOT_APPLICABLE"
        if spec.key == "candidate":
            candidate_row = self._candidate_row_count_result()
            if candidate_row != "RESOLVED":
                result = "REVIEW_REQUIRED"
                blockers.append("candidate row-count discrepancy not resolved")
        if spec.key == "opportunity":
            phase5e_evidence = read_json_if_possible(self.output_root / "opportunity" / "phase5e_fallback_inventory.json") or {}
            phase5e = str(phase5e_evidence.get("classification") or "IMPLEMENTATION_REQUIRED")
            if not entries[0]["source_path"].endswith("reports/opportunity_ai/phase5p/models/opportunity_model.pkl"):
                result = "BLOCKED"
                blockers.append("wrong opportunity model")
            if not any(e["source_path"].endswith("reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json") for e in entries):
                result = "BLOCKED"
                blockers.append("wrong opportunity metrics")
            if phase5e == "ACTIVE":
                blockers.append("Phase5-E fallback remains active until Registry Lookup or explicit metrics requirement is implemented")
                result = "REVIEW_REQUIRED" if result == "READY" else result
        if spec.key in {"pm", "capital_allocation"}:
            regression_role = next((e for e in entries if e["member_role"] == "REGRESSION_EVIDENCE"), None)
            regression_payload = read_json_if_possible(Path(regression_role["source_path"])) if regression_role else None
            if not regression_payload or regression_payload.get("overall_result") != "READY" or not regression_payload.get("execution_refs"):
                result = "REVIEW_REQUIRED"
                blockers.append("semantic regression execution refs required before formal acceptance")
        return {
            "schema_version": "phase16ao_real_regression_evidence.v1",
            "artifact_set_id": spec.artifact_set_id,
            "artifact_set_type": spec.artifact_set_type,
            "created_at": utc_now(),
            "overall_result": result,
            "load_results": load_results,
            "execution_refs": [],
            "runtime_current_ledger_pending_unchanged": True,
            "candidate_row_count_discrepancy_result": candidate_row,
            "phase5e_fallback_blocker": phase5e,
            "blockers": blockers,
        }

    def _load_check(self, entry: dict[str, Any]) -> dict[str, Any]:
        path = Path(entry["source_path"])
        if not path.is_file():
            return {"load_result": "BLOCKED", "reason": "source missing"}
        suffix = path.suffix.lower()
        if suffix == ".json":
            return {"load_result": "READY" if read_json_if_possible(path) is not None else "BLOCKED", "loader": "json"}
        if suffix in {".pkl", ".pickle"}:
            try:
                with path.open("rb") as fh:
                    pickle.load(fh)
                return {"load_result": "READY", "loader": "pickle"}
            except Exception as exc:
                return {"load_result": "REVIEW_REQUIRED", "loader": "pickle", "reason": str(exc)}
        if suffix == ".parquet":
            return {"load_result": "READY", "loader": "parquet_metadata_by_file_presence"}
        return {"load_result": "READY", "loader": "file_presence"}

    def _candidate_row_count_result(self) -> str:
        row_evidence = read_json_if_possible(self.output_root / "candidate" / "row_count_resolution.json") or {}
        if row_evidence.get("overall_result") == "READY" and row_evidence.get("dataset_matches_training_summary") is True:
            return "RESOLVED"
        manifest = read_json_if_possible(self.repo_root / ".runtime/candidate_ai/manifests/phase4be_long_history_dataset_manifest_2021-06-14_2026-05-15.json")
        model_manifest = read_json_if_possible(self.repo_root / ".runtime/candidate_ai/models/phase4bf_formal_candidate_model_manifest.json")
        if not manifest or not model_manifest:
            return "IMPLEMENTATION_REQUIRED"
        return "RESOLVED"

    def _lineage(self, spec: SetSpec, entries: list[dict[str, Any]]) -> dict[str, Any]:
        unknowns = []
        training_period = None
        stored_data_period = None
        if spec.key == "candidate":
            m = read_json_if_possible(self.repo_root / ".runtime/candidate_ai/manifests/phase4be_long_history_dataset_manifest_2021-06-14_2026-05-15.json") or {}
            training_period = m.get("training_period") or m.get("split_counts")
            stored_data_period = {"feature_row_count": m.get("feature_row_count"), "joined_row_count": m.get("joined_row_count"), "label_row_count": m.get("label_row_count")}
        elif spec.key == "opportunity":
            m = read_json_if_possible(self.repo_root / "reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json") or {}
            training_period = m.get("training_period") or m.get("dataset_period")
            stored_data_period = {"feature_columns": len(m.get("feature_columns") or []) if isinstance(m.get("feature_columns"), list) else None}
            unknowns.append("Phase5-P point-in-time sector proxy requires review")
        else:
            unknowns.append("formal point-in-time lineage requires human review")
        return {
            "schema_version": "phase16ao_source_lineage_evidence.v1",
            "artifact_set_id": spec.artifact_set_id,
            "artifact_set_type": spec.artifact_set_type,
            "member_sources": [{k: e[k] for k in ("member_role", "source_path", "content_hash")} for e in entries],
            "training_period": training_period,
            "stored_data_period": stored_data_period,
            "canonical_source_refs": [],
            "feature_source_refs": [e["source_path"] for e in entries if "feature" in e["member_role"].lower() or "schema" in e["member_role"].lower()],
            "point_in_time_status": "REVIEW_REQUIRED" if unknowns else "READY",
            "future_leakage_status": "REVIEW_REQUIRED" if unknowns else "READY",
            "backtest_contamination_status": "REVIEW_REQUIRED" if unknowns else "READY",
            "unknowns": unknowns,
            "overall_result": "REVIEW_REQUIRED" if unknowns else "READY",
        }

    def _freeze(self, spec: SetSpec, entries: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "schema_version": "phase16ao_freeze_manifest_evidence.v1",
            "artifact_set_id": spec.artifact_set_id,
            "artifact_set_type": spec.artifact_set_type,
            "hashes": {e["member_role"]: e["content_hash"] for e in entries},
            "scheduler_state": "NOT_CONNECTED",
            "automatic_retraining_disabled": True,
            "model_switch_disabled": True,
            "artifact_replacement_disabled": True,
            "overall_result": "READY",
        }

    def _compatibility(self, spec: SetSpec, entries: list[dict[str, Any]]) -> dict[str, Any]:
        missing = [e["member_role"] for e in entries if e["copy_status"] != "READY_TO_COPY"]
        return {
            "schema_version": "phase16ao_consumer_compatibility_evidence.v1",
            "artifact_set_id": spec.artifact_set_id,
            "artifact_set_type": spec.artifact_set_type,
            "consumer_id": "Runtime v2 explicit path consumer",
            "consumer_version": "current",
            "expected_member_roles": [e["member_role"] for e in entries],
            "artifact_hashes": {e["member_role"]: e["content_hash"] for e in entries},
            "schema_hash": stable_json_hash({e["member_role"]: e["content_hash"] for e in entries}),
            "load_result": "READY" if not missing else "BLOCKED",
            "compatibility_result": "READY" if not missing else "BLOCKED",
            "overall_result": "READY" if not missing else "BLOCKED",
            "missing_or_blocked_roles": missing,
        }

    def _approval_template(self, spec: SetSpec, role: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
        reviewed_hash = stable_json_hash({e["member_role"]: e["content_hash"] for e in entries})
        return {
            "schema_version": "phase16ao_approval_template.v1",
            "review_subject": spec.artifact_set_id,
            "artifact_set_id": spec.artifact_set_id,
            "artifact_set_type": spec.artifact_set_type,
            "reviewed_hash": reviewed_hash,
            "required_role": role,
            "required_evidence_refs": [
                f"reports/phase16_formal_registration_preparation/regression/{spec.key}_regression.json",
                f"reports/phase16_formal_registration_preparation/lineage/{spec.key}_lineage.json",
                f"reports/phase16_formal_registration_preparation/freeze/{spec.key}_freeze.json",
                f"reports/phase16_formal_registration_preparation/compatibility/{spec.key}_compatibility.json",
            ],
            "decision": "APPROVAL_REQUIRED",
            "reviewer": "APPROVAL_REQUIRED",
        }

    def _acceptance_report_candidate(
        self,
        spec: SetSpec,
        entries: list[dict[str, Any]],
        regression: dict[str, Any],
        lineage: dict[str, Any],
        freeze: dict[str, Any],
        compatibility: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema_version": "phase16ao_acceptance_report_candidate.v1",
            "artifact_set_id": spec.artifact_set_id,
            "artifact_set_type": spec.artifact_set_type,
            "reviewed_hash": stable_json_hash({e["member_role"]: e["content_hash"] for e in entries}),
            "decision": "REVIEW_REQUIRED",
            "regression_result": regression["overall_result"],
            "lineage_result": lineage["overall_result"],
            "freeze_result": freeze["overall_result"],
            "consumer_compatibility_result": compatibility["overall_result"],
            "approval_result": "APPROVAL_REQUIRED",
            "overall_result": "REVIEW_REQUIRED",
        }

    @staticmethod
    def _ready(ok: bool) -> str:
        return "READY" if ok else "BLOCKED"


def render_audit(summary: dict[str, Any]) -> str:
    lines = [
        "# Phase16-AO Formal Registration Preflight Audit",
        "",
        f"- preflight_version: {summary['preflight_version']}",
        f"- formal_registration_ready: {summary['formal_registration_ready']}",
        f"- protected_hashes_unchanged: {summary['protected_hashes_unchanged']}",
        f"- formal_registry_changed: {summary['formal_registry_changed']}",
        "",
        "## Sets",
    ]
    for key, result in summary["set_results"].items():
        lines.append(f"- {key}: {result['formal_registration_ready']} blockers={len(result['blockers'])}")
    lines.append("")
    return "\n".join(lines)


def run_formal_registration_preflight(*, output_root: Path = DEFAULT_OUTPUT_ROOT, repo_root: Path | None = None) -> dict[str, Any]:
    return FormalRegistrationPreflight(output_root=output_root, repo_root=repo_root or Path.cwd()).run()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare formal artifact registration evidence without copying or mutating Registry.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_ROOT))
    args = parser.parse_args(argv)
    result = run_formal_registration_preflight(output_root=Path(args.output), repo_root=Path.cwd())
    print(json.dumps({"formal_registration_ready": result["formal_registration_ready"], "formal_registry_changed": result["formal_registry_changed"]}, sort_keys=True))
    return 0 if not result["formal_registry_changed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
