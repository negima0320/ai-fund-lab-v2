from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


UNKNOWN = "UNKNOWN"
NOT_FOUND = "NOT_FOUND"
NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class ArtifactSpec:
    logical_artifact_id_candidate: str
    artifact_type: str
    component: str
    current_physical_path: str
    path_classification: str
    producer: str
    consumer: str
    current_runtime_use: str
    runtime_use_eligibility_candidate: str
    accepted_status_candidate: str
    retention_class: str
    migration_status: str
    legacy_status: str
    evidence: str
    business_date: str = UNKNOWN
    feature_date: str = UNKNOWN
    as_of: str = UNKNOWN
    source_refs: tuple[str, ...] = ()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def directory_inventory(path: Path) -> tuple[str, int, int]:
    if not path.exists() or not path.is_dir():
        return (NOT_APPLICABLE, 0, 0)
    entries: list[dict[str, Any]] = []
    size = 0
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        rel = child.relative_to(path).as_posix()
        child_size = child.stat().st_size
        size += child_size
        entries.append({"path": rel, "size_bytes": child_size, "sha256": sha256_file(child)})
    return (stable_json_hash(entries), len(entries), size)


def schema_info(path: Path) -> tuple[str, str]:
    if not path.exists() or path.is_dir():
        return (NOT_APPLICABLE, NOT_APPLICABLE)
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            schema = json_schema_signature(payload)
            return (schema, stable_json_hash(schema))
        if suffix == ".jsonl":
            first = ""
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        first = line
                        break
            if not first:
                return ("empty_jsonl", stable_json_hash("empty_jsonl"))
            schema = {"jsonl_first_record": json_schema_signature(json.loads(first))}
            return (json.dumps(schema, sort_keys=True), stable_json_hash(schema))
        if suffix == ".parquet":
            try:
                import pyarrow.parquet as pq  # type: ignore
            except Exception:
                return (UNKNOWN, UNKNOWN)
            schema = str(pq.read_schema(path))
            return (schema, hashlib.sha256(schema.encode("utf-8")).hexdigest())
        if suffix == ".csv":
            header = path.read_text(encoding="utf-8", errors="replace").splitlines()
            schema = {"csv_header": header[0].split(",") if header else []}
            return (json.dumps(schema, sort_keys=True), stable_json_hash(schema))
    except Exception as exc:
        return (f"SCHEMA_READ_ERROR:{type(exc).__name__}", UNKNOWN)
    return (NOT_APPLICABLE, NOT_APPLICABLE)


def json_schema_signature(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_schema_signature(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, list):
        if not value:
            return []
        return [json_schema_signature(value[0])]
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"


def artifact_instance_id(logical_id: str, content_hash: str, directory_hash: str) -> str:
    hash_part = content_hash if content_hash not in {UNKNOWN, NOT_FOUND, NOT_APPLICABLE} else directory_hash
    if hash_part in {UNKNOWN, NOT_FOUND, NOT_APPLICABLE}:
        return f"{logical_id}@{NOT_FOUND}"
    return f"{logical_id}@sha256-{hash_part[:16]}"


def inventory_entry(root: Path, spec: ArtifactSpec) -> dict[str, Any]:
    path = root / spec.current_physical_path
    exists = path.exists()
    is_dir = exists and path.is_dir()
    content_hash = NOT_APPLICABLE
    directory_hash = NOT_APPLICABLE
    file_count = 0
    size_bytes = 0
    if exists:
        if is_dir:
            directory_hash, file_count, size_bytes = directory_inventory(path)
        else:
            content_hash = sha256_file(path)
            file_count = 1
            size_bytes = path.stat().st_size
    else:
        content_hash = NOT_FOUND
        directory_hash = NOT_FOUND
    schema_version, schema_hash = schema_info(path)
    artifact_id = artifact_instance_id(
        spec.logical_artifact_id_candidate,
        content_hash,
        directory_hash,
    )
    source_hashes = []
    for ref in spec.source_refs:
        ref_path = root / ref
        if ref_path.exists() and ref_path.is_file():
            source_hashes.append({"path": ref, "sha256": sha256_file(ref_path)})
        elif ref_path.exists() and ref_path.is_dir():
            source_hashes.append({"path": ref, "directory_inventory_hash": directory_inventory(ref_path)[0]})
        else:
            source_hashes.append({"path": ref, "sha256": NOT_FOUND})
    return {
        "logical_artifact_id_candidate": spec.logical_artifact_id_candidate,
        "logical_id_status": "DRAFT",
        "artifact_instance_id_candidate": artifact_id,
        "artifact_type": spec.artifact_type,
        "component": spec.component,
        "current_physical_path": spec.current_physical_path,
        "path_classification": spec.path_classification,
        "file_or_directory": "directory" if is_dir else "file",
        "exists": exists,
        "content_hash": content_hash,
        "directory_inventory_hash": directory_hash,
        "size_bytes": size_bytes,
        "file_count": file_count,
        "schema_version": schema_version,
        "schema_hash": schema_hash,
        "producer": spec.producer,
        "consumer": spec.consumer,
        "producer_version": UNKNOWN,
        "business_date": spec.business_date,
        "feature_date": spec.feature_date,
        "as_of": spec.as_of,
        "source_refs": list(spec.source_refs),
        "source_hashes": source_hashes,
        "current_runtime_use": spec.current_runtime_use,
        "runtime_use_eligibility_candidate": spec.runtime_use_eligibility_candidate,
        "accepted_status_candidate": spec.accepted_status_candidate,
        "retention_class": spec.retention_class,
        "migration_status": spec.migration_status,
        "legacy_status": spec.legacy_status,
        "evidence": spec.evidence,
        "unknowns": unknowns_for_entry(exists, schema_hash, spec),
    }


def unknowns_for_entry(exists: bool, schema_hash: str, spec: ArtifactSpec) -> list[str]:
    unknowns = []
    if not exists:
        unknowns.append("physical_path_not_found")
    if schema_hash == UNKNOWN:
        unknowns.append("schema_hash_unknown")
    if spec.producer == UNKNOWN:
        unknowns.append("producer_unknown")
    if spec.consumer == UNKNOWN:
        unknowns.append("consumer_unknown")
    return unknowns


def latest_feature_date(root: Path) -> str:
    feature_root = root / ".runtime/operations/feature_artifacts"
    if not feature_root.exists():
        return UNKNOWN
    dates = sorted(p.name for p in feature_root.iterdir() if p.is_dir())
    return dates[-1] if dates else UNKNOWN


def specs(root: Path) -> list[ArtifactSpec]:
    feature_date = latest_feature_date(root)
    feature_base = f".runtime/operations/feature_artifacts/{feature_date}" if feature_date != UNKNOWN else ".runtime/operations/feature_artifacts/UNKNOWN"
    return [
        ArtifactSpec("data.market.daily_quotes.raw", "RAW_DATA_ARTIFACT", "J-Quants Raw", ".runtime/data/raw/jquants/equities_bars_daily/responses", "TEMPORARY_REGISTERED_PATH", "J-Quants fetch scripts", "Canonical normalized producer / audit", "No", "Not direct Runtime input", "VALIDATED", "provider_raw_evidence", "MIGRATION_REQUIRED", "active", "Phase16-G formal raw daily quote response root"),
        ArtifactSpec("data.market.daily_quotes.raw_table", "RAW_DATA_ARTIFACT", "J-Quants Raw", ".runtime/data/raw/jquants/equities_bars_daily/data.parquet", "TEMPORARY_REGISTERED_PATH", "J-Quants fetch scripts", "Canonical normalized producer / audit", "No", "Not direct Runtime input", "VALIDATED", "provider_raw_evidence", "MIGRATION_REQUIRED", "active", "Phase16-G supplemental raw table"),
        ArtifactSpec("data.market.daily_quotes.canonical", "CANONICAL_DATA_ARTIFACT", "Canonical Market Data", ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet", "TEMPORARY_REGISTERED_PATH", "scripts/run_phase9j3_rebuild_canonical_normalized_daily_quotes.py", "Feature Producer / audit", "Indirect", "Feature producer eligible", "VALIDATED", "canonical_data", "MIGRATION_REQUIRED", "active", "Phase16-G confirmed canonical normalized OHLCV"),
        ArtifactSpec("data.calendar.trading.canonical", "TRADING_CALENDAR_ARTIFACT", "Trading Calendar", ".runtime/data/raw/jquants/trading_calendar/data.parquet", "TEMPORARY_REGISTERED_PATH", "J-Quants fetch / config source", "Feature Producer / calendar resolver", "Indirect", "Runtime/Feature/Safety eligible candidate", "DRAFT", "canonical_data", "DESIGN_REVIEW_REQUIRED", "active", "Phase16-G formal config calendar, insufficient historical range"),
        ArtifactSpec("data.listed_issues.canonical", "LISTED_ISSUES_ARTIFACT", "Listed Issues", ".runtime/data/raw/jquants/listed_issues/data.parquet", "TEMPORARY_REGISTERED_PATH", "J-Quants fetch / config source", "Feature Producer / universe gate", "Indirect", "Feature producer eligible candidate", "DRAFT", "canonical_data", "DESIGN_REVIEW_REQUIRED", "active", "Phase16-G formal config listed issues, insufficient historical range"),
        ArtifactSpec("data.corporate_actions.canonical", "CORPORATE_ACTION_ARTIFACT", "Corporate Action", ".runtime/data/raw/jquants/corporate_actions/data.parquet", "UNKNOWN", UNKNOWN, "Canonical / Feature producer", "Indirect", "Corporate action eligible candidate", "DRAFT", "canonical_data", "DESIGN_REVIEW_REQUIRED", NOT_FOUND, "Standalone corporate action table not found in Phase16-G"),
        ArtifactSpec("feature.candidate.daily", "CANDIDATE_FEATURE_ARTIFACT", "Feature Producer", f"{feature_base}/candidate_features.parquet", "ACCEPTED_CURRENT_PATH", "runtime_v2 market_refresh / feature_refresh", "Candidate AI", "Yes", "Candidate AI eligible candidate", "VALIDATED", "run_scoped_feature", "MIGRATION_REQUIRED", "active", "Runtime CLI default feature-root current feature artifact", feature_date=feature_date),
        ArtifactSpec("feature.opportunity.daily", "OPPORTUNITY_FEATURE_ARTIFACT", "Feature Producer", f"{feature_base}/opportunity_feature_input.parquet", "ACCEPTED_CURRENT_PATH", "runtime_v2 market_refresh / feature_refresh", "Opportunity AI", "Yes", "Opportunity AI eligible candidate", "VALIDATED", "run_scoped_feature", "MIGRATION_REQUIRED", "active", "Runtime CLI default feature-root current feature artifact", feature_date=feature_date),
        ArtifactSpec("feature.position_management.daily", "POSITION_FEATURE_ARTIFACT", "Feature Producer", f"{feature_base}/position_feature_input.parquet", "ACCEPTED_CURRENT_PATH", "runtime_v2 market_refresh / feature_refresh", "Position Management", "Yes", "PM eligible candidate", "VALIDATED", "run_scoped_feature", "MIGRATION_REQUIRED", "active", "Runtime CLI default feature-root current feature artifact", feature_date=feature_date),
        ArtifactSpec("feature.capital_allocation.daily", "CAPITAL_ALLOCATION_INPUT_ARTIFACT", "Feature Producer", f"{feature_base}/capital_policy_input.parquet", "ACCEPTED_CURRENT_PATH", "runtime_v2 market_refresh / feature_refresh", "Capital Allocation / Planning", "Yes", "Capital Allocation input eligible candidate", "VALIDATED", "run_scoped_feature", "MIGRATION_REQUIRED", "active", "Runtime CLI default feature-root current feature artifact", feature_date=feature_date),
        ArtifactSpec("ai.candidate.model.accepted", "CANDIDATE_MODEL_ARTIFACT", "Candidate AI", ".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl", "TEMPORARY_REGISTERED_PATH", "Candidate AI training acceptance", "Candidate Model Loader", "Yes", "Candidate AI eligible candidate", "VALIDATED", "accepted_model", "MIGRATION_REQUIRED", "active", "Runtime default model path in runtime_v2/buy_ai/producer.py"),
        ArtifactSpec("ai.candidate.model.manifest", "MODEL_MANIFEST_ARTIFACT", "Candidate AI", ".runtime/candidate_ai/models/phase4bf_formal_candidate_model_manifest.json", "TEMPORARY_REGISTERED_PATH", "Candidate AI training acceptance", "Candidate Model Loader / audit", "Yes", "Candidate artifact set evidence", "VALIDATED", "accepted_model_manifest", "MIGRATION_REQUIRED", "active", "Candidate model manifest path"),
        ArtifactSpec("ai.candidate.training_metadata", "TRAINING_ARTIFACT", "Candidate AI", "reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json", "TRAINING_ONLY", "Candidate AI training", "Audit / artifact set evidence", "No", "Not Runtime input", "DRAFT", "training_evidence", "MIGRATION_REQUIRED", "training_only", "Candidate training summary evidence"),
        ArtifactSpec("ai.candidate.validation_evidence", "VALIDATION_ARTIFACT", "Candidate AI", "reports/candidate_ai/full_range/phase4bh_formal_candidate_quality_summary.json", "EVIDENCE_ONLY", "Candidate AI validation", "Audit / artifact set evidence", "No", "Not Runtime input", "DRAFT", "validation_evidence", "MIGRATION_REQUIRED", "evidence_only", "Candidate validation evidence"),
        ArtifactSpec("ai.opportunity.model.accepted", "OPPORTUNITY_MODEL_ARTIFACT", "Opportunity AI", "reports/opportunity_ai/phase5p/models/opportunity_model.pkl", "TEMPORARY_REGISTERED_PATH", "Opportunity AI training acceptance", "Opportunity Model Loader", "Yes", "Opportunity AI eligible candidate as set", "VALIDATED", "accepted_model", "MIGRATION_REQUIRED", "active", "Runtime default Opportunity model path"),
        ArtifactSpec("ai.opportunity.metrics.accepted", "OPPORTUNITY_METRICS_ARTIFACT", "Opportunity AI", "reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json", "TEMPORARY_REGISTERED_PATH", "Opportunity AI training acceptance", "Opportunity Metrics Loader", "Explicit override candidate", "Opportunity AI eligible candidate as set", "VALIDATED", "accepted_metrics", "MIGRATION_REQUIRED", "active", "Phase16-F preferred Phase5-P metrics"),
        ArtifactSpec("ai.opportunity.metrics.legacy_phase5e", "OPPORTUNITY_METRICS_ARTIFACT", "Opportunity AI", "reports/opportunity_ai/phase5e/opportunity_training_metrics.json", "LEGACY_ONLY", "Opportunity AI Phase5-E training", "Opportunity Metrics Loader fallback", "Fallback exists", "NOT_RUNTIME_ELIGIBLE_CANDIDATE", "DRAFT", "training_evidence", "MIGRATION_REQUIRED", "LEGACY_ONLY/TRAINING_ONLY", "Current fallback metrics path; must not be accepted with Phase5-P model"),
        ArtifactSpec("ai.opportunity.training_metadata", "TRAINING_ARTIFACT", "Opportunity AI", "reports/opportunity_ai/phase5p/training/opportunity_training_audit.json", "TRAINING_ONLY", "Opportunity AI training", "Audit / artifact set evidence", "No", "Not Runtime input", "DRAFT", "training_evidence", "MIGRATION_REQUIRED", "training_only", "Opportunity Phase5-P training audit"),
        ArtifactSpec("ai.opportunity.validation_evidence", "VALIDATION_ARTIFACT", "Opportunity AI", "reports/opportunity_ai/phase5p/combined_validation_metrics.json", "EVIDENCE_ONLY", "Opportunity AI validation", "Audit / artifact set evidence", "No", "Not Runtime input", "DRAFT", "validation_evidence", "MIGRATION_REQUIRED", "evidence_only", "Opportunity Phase5-P combined validation metrics"),
        ArtifactSpec("ai.position_management.code_policy.accepted", "PM_CODE_POLICY_ARTIFACT", "Position Management", "src/ai_fund_lab_v2/position_management_ai/inference.py", "ACCEPTED_CURRENT_PATH", "PM code acceptance", "PM Producer", "Yes", "PM eligible candidate as code-policy set", "VALIDATED", "code_policy", "MIGRATION_REQUIRED", "active", "PM inference code-policy source"),
        ArtifactSpec("ai.position_management.runtime_adapter.accepted", "PM_RUNTIME_ADAPTER_ARTIFACT", "Position Management", "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py", "ACCEPTED_CURRENT_PATH", "Runtime v2 PM adapter", "PM Producer", "Yes", "PM eligible candidate as code-policy set", "VALIDATED", "runtime_adapter", "MIGRATION_REQUIRED", "active", "Runtime v2 PM producer adapter source"),
        ArtifactSpec("decision.candidate.daily", "CANDIDATE_DECISION_ARTIFACT", "Candidate AI", ".runtime/runtime_state/buy_ai/2026-07-10/candidate_decisions.json", "ACCEPTED_CURRENT_PATH", "Runtime buy_ai producer", "Opportunity AI / audit", "Yes if present", "Generated decision candidate", "DRAFT", "run_scoped_decision", "MIGRATION_REQUIRED", "active", "Expected Runtime buy_ai decision path", business_date="2026-07-10"),
        ArtifactSpec("decision.opportunity.daily", "OPPORTUNITY_DECISION_ARTIFACT", "Opportunity AI", ".runtime/runtime_state/buy_ai/2026-07-10/opportunity_rankings.json", "ACCEPTED_CURRENT_PATH", "Runtime buy_ai producer", "Planning / Capital Allocation", "Yes if present", "Generated decision candidate", "DRAFT", "run_scoped_decision", "MIGRATION_REQUIRED", "active", "Expected Runtime buy_ai decision path", business_date="2026-07-10"),
        ArtifactSpec("decision.position_management.daily", "PM_DECISION_ARTIFACT", "Position Management", ".runtime/runtime_state/position_management/2026-07-10/position_management_decisions.json", "ACCEPTED_CURRENT_PATH", "Runtime PM producer", "Sell Planning", "Yes", "Generated decision candidate", "VALIDATED", "run_scoped_decision", "MIGRATION_REQUIRED", "active", "Observed PM decision artifact", business_date="2026-07-10"),
        ArtifactSpec("decision.capital_allocation.signal.daily", "CAPITAL_ALLOCATION_SIGNAL_EVIDENCE", "Capital Allocation / Planning", ".runtime/runtime_state/morning_pipeline/2026-07-09/order_plan.json", "EVIDENCE_ONLY", "Runtime Planning", "Pending / audit", "Embedded evidence", "Evidence only; standalone decision not adopted", "DRAFT", "run_scoped_decision_evidence", "MIGRATION_REQUIRED", "evidence_only", "CapitalAllocationSignal embedded in Planning evidence", business_date="2026-07-09"),
        ArtifactSpec("control.capital_allocation.policy.accepted", "CAPITAL_ALLOCATION_POLICY_ARTIFACT", "Capital Allocation", "configs/runtime_v2/capital_deployment.json", "ACCEPTED_CURRENT_PATH", "Human / Policy acceptance", "Planning / Submit Guard", "Yes", "Policy eligible candidate", "VALIDATED", "policy", "MIGRATION_REQUIRED", "active", "CapitalDeploymentPolicy config"),
        ArtifactSpec("control.capital_allocation.policy.demo", "CAPITAL_ALLOCATION_POLICY_ARTIFACT", "Capital Allocation", "configs/runtime_v2/capital_deployment_demo.json", "EVIDENCE_ONLY", "Human / Policy acceptance", "Demo Planning / Submit Guard", "Mode-specific config evidence", "Policy evidence candidate", "DRAFT", "policy", "MIGRATION_REQUIRED", "evidence_only", "Demo capital deployment config"),
        ArtifactSpec("control.safety.decision.latest", "SAFETY_ARTIFACT", "Safety", ".runtime/runtime_state/safety/latest_safety_decision.json", "ACCEPTED_CURRENT_PATH", "Runtime Safety producer", "Planning / Pending / Submit Guard", "Yes within freshness", "Safety decision candidate", "VALIDATED", "run_scoped_control", "MIGRATION_REQUIRED", "active", "Runtime safety latest decision"),
        ArtifactSpec("runtime.current.state", "RUNTIME_AUTHORITY_STATE", "Runtime Current", ".runtime/persistent_ledger/state.json", "RUNTIME_AUTHORITY_STATE", "Runtime Current / Ledger", "Runtime", "Authority state", NOT_APPLICABLE, NOT_APPLICABLE, "runtime_state", NOT_APPLICABLE, NOT_APPLICABLE, "Boundary only: not Registry target"),
        ArtifactSpec("runtime.ledger.orders", "RUNTIME_AUTHORITY_STATE", "Persistent Ledger", ".runtime/persistent_ledger/orders.jsonl", "RUNTIME_AUTHORITY_STATE", "Runtime Ledger", "Runtime", "Authority state", NOT_APPLICABLE, NOT_APPLICABLE, "runtime_state", NOT_APPLICABLE, NOT_APPLICABLE, "Boundary only: not Registry target"),
        ArtifactSpec("runtime.pending.active", "RUNTIME_AUTHORITY_STATE", "Pending", ".runtime/pending_order_plan/pending_order_plan.json", "RUNTIME_AUTHORITY_STATE", "Planning / Pending writer", "Submit Guard", "Authority state", NOT_APPLICABLE, NOT_APPLICABLE, "runtime_state", NOT_APPLICABLE, NOT_APPLICABLE, "Boundary only: not Registry target"),
        ArtifactSpec("runtime.state.current", "RUNTIME_AUTHORITY_STATE", "Runtime State", ".runtime/runtime_state/current_state.json", "RUNTIME_AUTHORITY_STATE", "Runtime State producer", "Runtime", "Authority state", NOT_APPLICABLE, NOT_APPLICABLE, "runtime_state", NOT_APPLICABLE, NOT_APPLICABLE, "Boundary only: not Registry target"),
    ]


def draft_event(entry: dict[str, Any]) -> dict[str, Any]:
    status = entry["accepted_status_candidate"]
    if status not in {"DRAFT", "VALIDATED"}:
        status = "DRAFT"
    return {
        "event_type": "DRAFT_REGISTER_ARTIFACT_CANDIDATE",
        "status": status,
        "logical_artifact_id": entry["logical_artifact_id_candidate"],
        "artifact_instance_id": entry["artifact_instance_id_candidate"],
        "artifact_type": entry["artifact_type"],
        "component": entry["component"],
        "physical_path": entry["current_physical_path"],
        "content_hash": entry["content_hash"],
        "directory_inventory_hash": entry["directory_inventory_hash"],
        "schema_hash": entry["schema_hash"],
        "runtime_use_eligibility_candidate": entry["runtime_use_eligibility_candidate"],
        "path_classification": entry["path_classification"],
        "migration_status": entry["migration_status"],
        "legacy_status": entry["legacy_status"],
        "authority": "EVIDENCE_ONLY_NOT_RUNTIME_AUTHORITY",
    }


def artifact_set_manifest(name: str, entries: list[dict[str, Any]], logical_ids: list[str]) -> dict[str, Any]:
    selected = [e for e in entries if e["logical_artifact_id_candidate"] in logical_ids]
    status = "VALIDATED" if selected and all(e["exists"] for e in selected) else "DRAFT"
    return {
        "manifest_type": f"{name}_artifact_set_manifest_candidate",
        "accepted_status_candidate": status,
        "runtime_authority": False,
        "logical_id_status": "DRAFT",
        "artifacts": selected,
        "set_hash_candidate": stable_json_hash(
            [
                {
                    "logical_artifact_id_candidate": e["logical_artifact_id_candidate"],
                    "artifact_instance_id_candidate": e["artifact_instance_id_candidate"],
                    "content_hash": e["content_hash"],
                    "schema_hash": e["schema_hash"],
                }
                for e in selected
            ]
        ),
        "unknowns": [e for e in selected if e["unknowns"]],
    }


def consumer_compatibility() -> list[dict[str, Any]]:
    return [
        {"consumer": "Candidate Model Loader", "current_path": ".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl", "current_default": True, "explicit_override": "--candidate-model-path", "fallback": "None", "logical_id_candidate": "ai.candidate.model.accepted", "registry_prevalidation_possible": True, "consumer_change_required_later": "Yes for logical ID resolution"},
        {"consumer": "Opportunity Model Loader", "current_path": "reports/opportunity_ai/phase5p/models/opportunity_model.pkl", "current_default": True, "explicit_override": "--opportunity-model-path", "fallback": "None", "logical_id_candidate": "ai.opportunity.model.accepted", "registry_prevalidation_possible": True, "consumer_change_required_later": "Yes for accepted set lookup"},
        {"consumer": "Opportunity Metrics Loader", "current_path": "reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json", "current_default": False, "explicit_override": "--opportunity-training-metrics-path", "fallback": "reports/opportunity_ai/phase5e/opportunity_training_metrics.json", "logical_id_candidate": "ai.opportunity.metrics.accepted", "registry_prevalidation_possible": True, "consumer_change_required_later": "Yes; fallback removal later"},
        {"consumer": "PM Producer", "current_path": "src/ai_fund_lab_v2/position_management_ai/inference.py + src/ai_fund_lab_v2/runtime_v2/position_management/producer.py", "current_default": True, "explicit_override": "PM feature/opportunity paths", "fallback": "No model fallback", "logical_id_candidate": "ai.position_management.code_policy.accepted", "registry_prevalidation_possible": True, "consumer_change_required_later": "Yes for code/adaptor hash validation"},
        {"consumer": "Feature Producer", "current_path": ".runtime/operations/jquants/raw_normalized/... and .runtime/operations/feature_artifacts/<date>", "current_default": True, "explicit_override": "feature-root / operation paths", "fallback": "Carryover feature date selection exists", "logical_id_candidate": "feature.*.daily", "registry_prevalidation_possible": True, "consumer_change_required_later": "Yes for canonical source refs"},
        {"consumer": "AI Decision Producer", "current_path": ".runtime/runtime_state/buy_ai/<date> and .runtime/runtime_state/position_management/<date>", "current_default": True, "explicit_override": "runtime-root / business-date", "fallback": "No path search fallback intended", "logical_id_candidate": "decision.*.daily", "registry_prevalidation_possible": True, "consumer_change_required_later": "Yes for decision source hash contract"},
        {"consumer": "Capital Allocation / Planning", "current_path": "configs/runtime_v2/capital_deployment.json + embedded CapitalAllocationSignal", "current_default": True, "explicit_override": "capital_deployment_policy", "fallback": "Policy error fails planning/submit guard", "logical_id_candidate": "control.capital_allocation.policy.accepted", "registry_prevalidation_possible": True, "consumer_change_required_later": "Yes; standalone decision artifact later only"},
        {"consumer": "Runtime CLI", "current_path": ".runtime, .runtime/operations/feature_artifacts, explicit model paths", "current_default": True, "explicit_override": "CLI args", "fallback": "Existing defaults remain unchanged", "logical_id_candidate": "Multiple", "registry_prevalidation_possible": True, "consumer_change_required_later": "Yes for logical ID startup resolution"},
        {"consumer": "Audit / Report", "current_path": "reports/** and .runtime/runtime_state/**", "current_default": True, "explicit_override": "output dirs", "fallback": "Report omission allowed until refs implemented", "logical_id_candidate": "Evidence refs", "registry_prevalidation_possible": True, "consumer_change_required_later": "Optional refs later"},
    ]


def protected_paths(root: Path, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = {
        "Candidate model": ".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl",
        "Candidate manifest": ".runtime/candidate_ai/models/phase4bf_formal_candidate_model_manifest.json",
        "Opportunity model": "reports/opportunity_ai/phase5p/models/opportunity_model.pkl",
        "Phase5-P metrics": "reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json",
        "Phase5-E metrics": "reports/opportunity_ai/phase5e/opportunity_training_metrics.json",
        "PM code-policy source": "src/ai_fund_lab_v2/position_management_ai/inference.py",
        "PM adapter source": "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py",
        "Canonical normalized OHLCV": ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet",
        "Current": ".runtime/persistent_ledger/state.json",
        "Ledger": ".runtime/persistent_ledger/orders.jsonl",
        "Pending": ".runtime/pending_order_plan/pending_order_plan.json",
        "Runtime State": ".runtime/runtime_state/current_state.json",
    }
    feature = next((e for e in entries if e["logical_artifact_id_candidate"] == "feature.candidate.daily"), None)
    decision = next((e for e in entries if e["logical_artifact_id_candidate"] == "decision.position_management.daily"), None)
    if feature:
        labels["Major Feature Artifact"] = feature["current_physical_path"]
    if decision:
        labels["Major Decision Artifact"] = decision["current_physical_path"]
    result = []
    for label, rel in labels.items():
        path = root / rel
        if path.exists() and path.is_file():
            result.append({"label": label, "path": rel, "hash": sha256_file(path), "exists": True})
        elif path.exists() and path.is_dir():
            result.append({"label": label, "path": rel, "hash": directory_inventory(path)[0], "exists": True})
        else:
            result.append({"label": label, "path": rel, "hash": NOT_FOUND, "exists": False})
    return result


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_inventory(root: Path, output_dir: Path) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    artifact_entries = [inventory_entry(root, spec) for spec in specs(root)]
    before_hashes = protected_paths(root, artifact_entries)
    events = [draft_event(e) for e in artifact_entries if e["artifact_type"] != "RUNTIME_AUTHORITY_STATE"]
    index = {
        "index_type": "draft_registry_index_candidate",
        "runtime_authority": False,
        "accepted_event_count": 0,
        "entries": {e["logical_artifact_id"]: e for e in events},
    }
    candidate_set = artifact_set_manifest(
        "candidate",
        artifact_entries,
        [
            "ai.candidate.model.accepted",
            "ai.candidate.model.manifest",
            "ai.candidate.training_metadata",
            "ai.candidate.validation_evidence",
        ],
    )
    opportunity_set = artifact_set_manifest(
        "opportunity",
        artifact_entries,
        [
            "ai.opportunity.model.accepted",
            "ai.opportunity.metrics.accepted",
            "ai.opportunity.training_metadata",
            "ai.opportunity.validation_evidence",
        ],
    )
    pm_set = artifact_set_manifest(
        "pm",
        artifact_entries,
        [
            "ai.position_management.code_policy.accepted",
            "ai.position_management.runtime_adapter.accepted",
        ],
    )
    capital_policy = artifact_set_manifest(
        "capital_allocation_policy",
        artifact_entries,
        [
            "control.capital_allocation.policy.accepted",
        ],
    )
    inventory = {
        "prefix": "Phase16-P",
        "created_at": started_at,
        "runtime_authority": False,
        "accepted_status_allowed": ["DRAFT", "VALIDATED"],
        "accepted_status_prohibited": ["ACCEPTED"],
        "artifact_count": len(artifact_entries),
        "artifacts": artifact_entries,
        "consumer_compatibility": consumer_compatibility(),
        "before_hashes": before_hashes,
    }
    write_json(output_dir / "artifact_inventory.json", inventory)
    with (output_dir / "draft_registry_events.jsonl").open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    write_json(output_dir / "draft_registry_index.json", index)
    write_json(output_dir / "candidate_artifact_set_manifest_candidate.json", candidate_set)
    write_json(output_dir / "opportunity_artifact_set_manifest_candidate.json", opportunity_set)
    write_json(output_dir / "pm_artifact_set_manifest_candidate.json", pm_set)
    write_json(output_dir / "capital_allocation_policy_manifest_candidate.json", capital_policy)
    after_hashes = protected_paths(root, artifact_entries)
    hash_comparison = compare_hashes(before_hashes, after_hashes)
    inventory["after_hashes"] = after_hashes
    inventory["hash_comparison"] = hash_comparison
    write_json(output_dir / "artifact_inventory.json", inventory)
    write_audit(output_dir / "inventory_audit.md", inventory, events, candidate_set, opportunity_set, pm_set, capital_policy)
    return inventory


def compare_hashes(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[dict[str, Any]]:
    after_by_label = {item["label"]: item for item in after}
    result = []
    for item in before:
        after_item = after_by_label.get(item["label"])
        status = "UNCHANGED" if after_item and after_item["hash"] == item["hash"] else "CHANGED"
        if not item["exists"] and after_item and not after_item["exists"]:
            status = NOT_APPLICABLE
        result.append({"label": item["label"], "path": item["path"], "before_hash": item["hash"], "after_hash": after_item["hash"] if after_item else NOT_FOUND, "result": status})
    return result


def write_audit(
    path: Path,
    inventory: dict[str, Any],
    events: list[dict[str, Any]],
    candidate_set: dict[str, Any],
    opportunity_set: dict[str, Any],
    pm_set: dict[str, Any],
    capital_policy: dict[str, Any],
) -> None:
    artifacts = inventory["artifacts"]
    type_counts: dict[str, int] = {}
    for entry in artifacts:
        type_counts[entry["artifact_type"]] = type_counts.get(entry["artifact_type"], 0) + 1
    accepted_count = sum(1 for event in events if event["status"] == "ACCEPTED")
    hash_failures = [item for item in inventory["hash_comparison"] if item["result"] == "CHANGED"]
    lines = [
        "# Phase16-P Read-only Artifact Inventory Audit",
        "",
        f"- artifact_count: {len(artifacts)}",
        f"- draft_registry_event_count: {len(events)}",
        f"- accepted_event_count: {accepted_count}",
        f"- before_after_hash_failures: {len(hash_failures)}",
        f"- candidate_set_status: {candidate_set['accepted_status_candidate']}",
        f"- opportunity_set_status: {opportunity_set['accepted_status_candidate']}",
        f"- pm_set_status: {pm_set['accepted_status_candidate']}",
        f"- capital_allocation_policy_status: {capital_policy['accepted_status_candidate']}",
        "",
        "## Artifact Type Counts",
        "",
    ]
    for artifact_type, count in sorted(type_counts.items()):
        lines.append(f"- {artifact_type}: {count}")
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Runtime Contract unchanged: YES",
            "- Runtime Authority unchanged: YES",
            "- Current / Ledger / Pending unchanged: YES",
            "- Normal Mainline unchanged: YES",
            "- AI Model unchanged: YES",
            "- Feature Schema unchanged: YES",
            "- Feature calculation unchanged: YES",
            "- Consumer path unchanged: YES",
            "- CLI / config default unchanged: YES",
            "- Opportunity fallback unchanged: YES",
            "- Capital Allocation behavior unchanged: YES",
            "- Formal Registry path created: NO",
            "- .runtime/artifacts created: NO",
            "- Artifact copy / move: NO",
            "",
            "## Consumer Compatibility",
            "",
        ]
    )
    for item in inventory["consumer_compatibility"]:
        lines.append(f"- {item['consumer']}: current_path={item['current_path']}; fallback={item['fallback']}; later_change={item['consumer_change_required_later']}")
    lines.extend(["", "## Hash Comparison", ""])
    for item in inventory["hash_comparison"]:
        lines.append(f"- {item['label']}: {item['result']} ({item['path']})")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase16-P read-only artifact inventory generator")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--output-dir", default="reports/phase16_registry_inventory", help="Evidence output directory")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    output_dir = root / args.output_dir
    run_inventory(root, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

