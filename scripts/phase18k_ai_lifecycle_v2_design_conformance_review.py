#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.artifact_registry.full_log_validator import FullEventLogValidator


PHASE = "Phase18-K"
RUN_ID = "phase18k-design-conformance-review-20260717T000000Z"
REPORT_JSON = Path("reports/phase_reports/phase18_k_ai_lifecycle_v2_design_conformance_and_implementation_review.json")
REPORT_MD = Path("docs/phase_reports/phase18_k_ai_lifecycle_v2_design_conformance_and_implementation_review.md")
EVIDENCE_DIR = Path("reports/phase18_k_ai_lifecycle_v2_design_conformance_and_implementation_review") / RUN_ID

REQUIRED_DOCS = [
    "docs/02_architecture/ai_lifecycle_v2.md",
    "docs/02_architecture/runtime_architecture_v2.md",
    "docs/01_requirements/phase_roadmap.md",
    "docs/phase_reports/phase18_a_common_pit_dataset_rebuild_pipeline_existing_implementation_audit_and_plan.md",
    "docs/phase_reports/phase18_b_common_pit_dataset_rebuild_pipeline_implementation.md",
    "docs/phase_reports/phase18_c_real_data_pit_dataset_rebuild_and_acceptance.md",
    "docs/phase_reports/phase18_d_training_validation_challenger_pipeline.md",
    "docs/phase_reports/phase18_e_opportunity_ai_design_review_and_root_cause_investigation.md",
    "docs/phase_reports/phase18_f_opportunity_training_pipeline_redesign.md",
    "docs/phase_reports/phase18_g_formal_challenger_promotion_readiness_review.md",
    "docs/phase_reports/phase18_h_promotion_blocking_issues_resolution.md",
    "docs/phase_reports/phase18_i_authority_approval_and_registry_promotion_operator.md",
    "docs/phase_reports/phase18_j_runtime_discovery_freshness_gate_acceptance.md",
    "docs/phase_reports/phase16_k_ai_artifact_registry_and_capital_allocation_design.md",
    "docs/phase_reports/phase17_final_summary_and_phase18_handoff.md",
    "docs/phase_reports/phase17_bv19_ai_training_lifecycle_and_retraining_pipeline_audit.md",
    "docs/phase_reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract.md",
    "docs/phase_reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment.md",
]

REQUIRED_DATASET_FILES = {
    "dataset.parquet",
    "dataset_metadata.json",
    "feature_schema.json",
    "target_schema.json",
    "lineage.json",
    "data_quality.json",
    "date_coverage.json",
    "drop_reasons.csv",
    "hash_manifest.json",
    "status.json",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    return str(path).replace("\\", "/")


def command(cmd: list[str]) -> dict[str, Any]:
    completed = subprocess.run(cmd, cwd=Path.cwd(), text=True, capture_output=True, check=False, env={**os.environ, "PYTHONPATH": "src"})
    return {
        "cmd": cmd,
        "returncode": completed.returncode,
        "stdout_tail": "\n".join(completed.stdout.splitlines()[-80:]),
        "stderr_tail": "\n".join(completed.stderr.splitlines()[-80:]),
    }


def git_inventory() -> dict[str, Any]:
    result = command(["git", "status", "--short"])
    files = []
    for line in result["stdout_tail"].splitlines():
        if not line:
            continue
        files.append(line[3:])
    phase18_files = [p for p in files if "phase18" in p.lower() or p.startswith("src/ai_fund_lab_v2/ai_lifecycle") or p.startswith("tests/ai_lifecycle")]
    return {"git_status": result, "phase18_changed_files": sorted(phase18_files), "phase18_changed_file_count": len(phase18_files)}


def docs_review() -> dict[str, Any]:
    return {doc: {"exists": Path(doc).is_file(), "size": Path(doc).stat().st_size if Path(doc).is_file() else 0} for doc in REQUIRED_DOCS}


def inspect_dataset_bundle(path: Path, keys: list[str]) -> dict[str, Any]:
    files = {p.name for p in path.iterdir()} if path.exists() else set()
    missing = sorted(REQUIRED_DATASET_FILES - files)
    status = read_json(path / "status.json") if (path / "status.json").is_file() else {}
    metadata = read_json(path / "dataset_metadata.json") if (path / "dataset_metadata.json").is_file() else {}
    coverage = read_json(path / "date_coverage.json") if (path / "date_coverage.json").is_file() else {}
    parquet_path = path / "dataset.parquet"
    uniqueness = {"status": "NOT_CHECKED"}
    candidate_source_ref = {"status": "NOT_APPLICABLE"}
    if parquet_path.is_file():
        df = pd.read_parquet(parquet_path)
        missing_keys = [key for key in keys if key not in df.columns]
        duplicate_count = int(df.duplicated(keys).sum()) if not missing_keys else None
        uniqueness = {"status": "PASS" if not missing_keys and duplicate_count == 0 else "FAIL", "keys": keys, "missing_keys": missing_keys, "duplicate_count": duplicate_count}
        if "candidate_source_ref" in df.columns:
            refs = sorted(str(v) for v in df["candidate_source_ref"].dropna().unique().tolist())
            candidate_source_ref = {
                "status": "PASS" if refs and all("/" not in value and "\\" not in value for value in refs) else "FAIL",
                "sample": refs[:5],
                "absolute_path_dependency_detected": any(value.startswith("/") or "/" in value or "\\" in value for value in refs),
            }
    validations = {item.get("name"): item.get("status") for item in status.get("validations", [])}
    return {
        "path": rel(path),
        "exists": path.exists(),
        "missing_files": missing,
        "bundle_complete": not missing,
        "status": status.get("status"),
        "validation_status": status.get("validation_status"),
        "validations": validations,
        "metadata_non_mutation": {
            "training_executed": metadata.get("training_executed"),
            "promotion_performed": metadata.get("promotion_performed"),
            "runtime_switch_performed": metadata.get("runtime_switch_performed"),
            "broker_write_executed": metadata.get("broker_write_executed"),
        },
        "dataset_hash": metadata.get("content_hash"),
        "schema_hash": metadata.get("schema_hash"),
        "date_coverage": coverage,
        "uniqueness": uniqueness,
        "candidate_source_ref": candidate_source_ref,
    }


def inspect_training_bundle(path: Path, required_extra: set[str] | None = None) -> dict[str, Any]:
    required = {
        "model.pkl",
        "training_metadata.json",
        "training_config.json",
        "dataset_reference.json",
        "feature_schema.json",
        "target_schema.json",
        "split_definition.json",
        "hash_manifest.json",
        "status.json",
    } | (required_extra or set())
    files = {p.name for p in path.iterdir()} if path.exists() else set()
    missing = sorted(required - files)
    metadata = read_json(path / "training_metadata.json") if (path / "training_metadata.json").is_file() else {}
    manifest = read_json(path / "hash_manifest.json") if (path / "hash_manifest.json").is_file() else {}
    split = read_json(path / "split_definition.json") if (path / "split_definition.json").is_file() else {}
    return {
        "path": rel(path),
        "exists": path.exists(),
        "missing_files": missing,
        "bundle_complete": not missing,
        "training_version": metadata.get("training_version"),
        "model_hash": manifest.get("model_hash") or (manifest.get("file_hashes") or {}).get("model.pkl"),
        "bundle_hash": manifest.get("bundle_hash"),
        "non_mutation": {
            "promotion_performed": metadata.get("promotion_performed"),
            "registry_accepted_update_performed": metadata.get("registry_accepted_update_performed"),
            "runtime_switch_performed": metadata.get("runtime_switch_performed"),
            "buy_restarted": metadata.get("buy_restarted"),
            "broker_write_executed": metadata.get("broker_write_executed"),
        },
        "split_summary": {name: split.get(name, {}) for name in ["train", "validation", "test", "recent_holdout"]},
    }


def registry_review() -> dict[str, Any]:
    validation = FullEventLogValidator().validate(include_events=False)
    errors = validation.get("errors", [])
    registry_index = read_json(Path(".runtime/artifact_registry/index/registry_index.json"))
    promotion_index = read_json(Path(".runtime/artifact_registry/promotion_candidates/promotion_candidate_index.json"))
    promotion_candidates = promotion_index.get("promotion_candidates", {})
    last_event = {}
    event_log = Path(".runtime/artifact_registry/events/registry_events.jsonl")
    if event_log.is_file() and event_log.read_text(encoding="utf-8").splitlines():
        last_event = json.loads(event_log.read_text(encoding="utf-8").splitlines()[-1])
    return {
        "full_event_log_validation": {
            "overall_result": validation.get("overall_result"),
            "failure_class": validation.get("failure_class"),
            "event_count": validation.get("event_count"),
            "event_log_hash": validation.get("event_log_hash"),
            "errors": errors[:40],
        },
        "accepted_entries": {
            key: {
                "current_status": value.get("current_status"),
                "runtime_use_eligible": value.get("runtime_use_eligible"),
                "content_hash": value.get("content_hash"),
                "schema_hash": value.get("schema_hash"),
            }
            for key, value in registry_index.get("entries", {}).items()
            if key in {"ai.candidate.accepted_set", "ai.opportunity.accepted_set"}
        },
        "promotion_candidates": promotion_candidates,
        "last_event": {
            "event_id": last_event.get("event_id"),
            "event_type": last_event.get("event_type"),
            "artifact_type": last_event.get("artifact_type"),
            "artifact_set_type": last_event.get("artifact_set_type"),
            "new_status": last_event.get("new_status"),
            "runtime_use_eligible": last_event.get("runtime_use_eligible"),
        },
    }


def phase_report_acceptance() -> dict[str, Any]:
    reports = {}
    for letter in "bcdefghij":
        path = Path(f"reports/phase_reports/phase18_{letter}_")
        matches = sorted(Path("reports/phase_reports").glob(f"phase18_{letter}_*.json"))
        if matches:
            data = read_json(matches[0])
            reports[matches[0].name] = {
                "final_judgment": data.get("final_judgment"),
                "acceptance": data.get("acceptance"),
                "non_mutation_confirmation": data.get("non_mutation_confirmation"),
            }
        else:
            reports[str(path)] = {"missing": True}
    return reports


def shortcut_audit(files: list[str]) -> dict[str, Any]:
    patterns = {
        "hard_coded_run_id": r"RUN_ID\s*=|phase18[a-z]-",
        "hard_coded_time": r"2026-07-17T00:00:00|CREATED_AT\s*=|DECISION_TIME\s*=",
        "hard_coded_bundle": r"candidate_dataset_c8de026d3ea8aa4d|opportunity_dataset_fbadc8091a31486d|1081babc49b5d26b|buy_ai_bundle_phase18h",
        "drift_forced_pass": r"hard_drift\s*=\s*False|freshness_healthy\s*=\s*True|\"status\": \"PASS\"",
        "runtime_default_model_path": r"DEFAULT_.*MODEL_PATH",
    }
    hits: dict[str, list[str]] = {key: [] for key in patterns}
    scan_files = [Path(p) for p in files if Path(p).is_file() and Path(p).suffix in {".py", ".md"}]
    for path in scan_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in patterns.items():
            if re.search(pattern, text):
                hits[name].append(rel(path))
    return hits


def run_tests() -> dict[str, Any]:
    cmd = [
        "python3",
        "-m",
        "pytest",
        "tests/ai_lifecycle/test_phase18b_common_pit_dataset_rebuild.py",
        "tests/ai_lifecycle/test_phase18d_training_pipeline.py",
        "tests/runtime_v2/test_phase16av_registry_consumer_cutover.py",
        "tests/artifact_registry/test_phase16au_registry_resolver.py",
        "-q",
    ]
    result = command(cmd)
    combined = result["stdout_tail"] + "\n" + result["stderr_tail"]
    match = re.search(r"(\d+) failed, (\d+) passed", combined)
    result["summary"] = {
        "status": "PASS" if result["returncode"] == 0 else "FAIL",
        "failed": int(match.group(1)) if match else None,
        "passed": int(match.group(2)) if match else None,
    }
    return result


def gap_inventory(registry: dict[str, Any], tests: dict[str, Any]) -> list[dict[str, Any]]:
    gaps = [
        {
            "id": "K-GAP-001",
            "title": "Phase18-I Promotion Candidate event is not compatible with formal Artifact Registry event schema",
            "classification": "IMPLEMENTATION_CONTRACT_VIOLATION",
            "severity": "CRITICAL",
            "evidence": registry["full_event_log_validation"]["errors"][:24],
            "root_cause": "Phase18-I appended a PROMOTION_CANDIDATE_REGISTERED event directly to the formal registry event log using fields not accepted by artifact_registry_event.v1.",
            "affected_contract": "Artifact Registry append-only event log, Runtime accepted artifact resolver fail-closed contract",
            "affected_files": ["scripts/phase18i_authority_registry_operator.py", ".runtime/artifact_registry/events/registry_events.jsonl"],
            "runtime_impact": "RegistryArtifactResolver halts before resolving accepted BUY AI sets; Runtime BUY AI artifact lookup fails closed.",
            "registry_impact": "Full event log validation FAIL/HALT; checkpoint/index remain at pre-Phase18-I hash and no longer describe the event log.",
            "phase18_impact": "Phase18 cannot be considered fully conformant until promotion candidate events are formalized or stored outside the accepted registry event log contract.",
            "recommended_step": "Phase18-L remediation: define/validate Promotion Candidate schema or separate candidate transaction log; rebuild validator/index/checkpoint; rerun resolver tests.",
        },
        {
            "id": "K-GAP-002",
            "title": "Runtime Freshness/Drift gates are report-script implementations, not integrated Runtime Control Plane modules",
            "classification": "RUNTIME_INTEGRATION_GAP",
            "severity": "HIGH",
            "evidence": ["scripts/phase18j_runtime_discovery_freshness_gate_acceptance.py", "src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py"],
            "root_cause": "Phase18-J evaluates gates in an audit script; runtime_v2 buy_ai producer still runs existing inference path and does not consume this gate as a reusable Runtime Control Plane component.",
            "affected_contract": "Runtime Control Plane freshness/drift gate and BUY PASS/REVIEW_REQUIRED/BLOCK boundary",
            "affected_files": ["scripts/phase18j_runtime_discovery_freshness_gate_acceptance.py", "src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py"],
            "runtime_impact": "Daily Runtime may not enforce Phase18-J gate semantics without explicit operator wiring.",
            "registry_impact": "None directly, except resolver is already blocked by K-GAP-001.",
            "phase18_impact": "Runtime Discovery/Freshness/Drift is PARTIAL rather than production-integrated.",
            "recommended_step": "Move gate logic into src/runtime_v2 control-plane module with tests; keep scripts as wrappers.",
        },
        {
            "id": "K-GAP-003",
            "title": "Drift gate evidence is shallow and includes forced PASS placeholders",
            "classification": "TEST_COVERAGE_GAP",
            "severity": "HIGH",
            "evidence": ["hard_drift = False", "freshness_healthy = True", "feature_drift status PASS by schema smoke"],
            "root_cause": "Phase18-J records distribution summaries but does not implement thresholded PSI/population/calibration drift evaluation against accepted baselines.",
            "affected_contract": "AI Lifecycle v2 Drift Contract",
            "affected_files": ["scripts/phase18j_runtime_discovery_freshness_gate_acceptance.py"],
            "runtime_impact": "Hard drift may be missed if only schema smoke passes.",
            "registry_impact": "None.",
            "phase18_impact": "Drift Gate is PARTIAL.",
            "recommended_step": "Implement quantitative drift validators and failure rehearsals for all-negative with hard drift.",
        },
        {
            "id": "K-GAP-004",
            "title": "Weekly lifecycle scheduler is not implemented",
            "classification": "DESIGN_NOT_IMPLEMENTED",
            "severity": "HIGH",
            "evidence": ["No Phase18 lifecycle scheduler module/script with eligibility, lock, retry, timeout, overlap prevention, status artifact, alert."],
            "root_cause": "Phase18 implemented manual phase operators A-J but not the recurring scheduler/monitor required by SoT and roadmap.",
            "affected_contract": "AI Lifecycle v2 weekly lifecycle trigger and observability contract",
            "affected_files": ["src/ai_fund_lab_v2/ai_lifecycle/", "scripts/"],
            "runtime_impact": "Lifecycle work cannot be automatically triggered from cadence/freshness eligibility.",
            "registry_impact": "None directly.",
            "phase18_impact": "Phase18 lifecycle coverage incomplete.",
            "recommended_step": "Add Phase18-L/M scheduler operator with lock/retry/timeout/no-overlap and no hot-swap guarantees.",
        },
        {
            "id": "K-GAP-005",
            "title": "PM/Safety policy lifecycle and Future AI onboarding are documented but not implemented as Phase18 lifecycle components",
            "classification": "DESIGN_NOT_IMPLEMENTED",
            "severity": "MEDIUM",
            "evidence": ["No PM/Safety policy lifecycle module under src/ai_fund_lab_v2/ai_lifecycle; existing PM registry acceptance is Phase16/17-specific."],
            "root_cause": "Phase18 focused on Candidate/Opportunity BUY AI lifecycle.",
            "affected_contract": "Full AI Lifecycle Coverage Review",
            "affected_files": ["src/ai_fund_lab_v2/ai_lifecycle/"],
            "runtime_impact": "BUY lifecycle work does not regress PM/Safety, but common lifecycle coverage remains incomplete.",
            "registry_impact": "Existing PM registry artifacts remain separate.",
            "phase18_impact": "Full lifecycle coverage is PARTIAL.",
            "recommended_step": "Add policy-validation lifecycle classification/operators for PM and Safety without applying trainable retrain semantics.",
        },
        {
            "id": "K-GAP-006",
            "title": "Rollback/revoke exists as metadata/rehearsal only, not as formal Registry rollback/revoke operator for BUY AI bundle",
            "classification": "REGISTRY_AUTHORITY_GAP",
            "severity": "MEDIUM",
            "evidence": ["rollback_metadata.json exists; registry_rollback_event_written=false; no Phase18 rollback/revoke operator."],
            "root_cause": "Phase18-I prepared rollback metadata but intentionally did not implement accepted rollback/revoke event flow.",
            "affected_contract": "Registry rollback/revoke acceptance contract",
            "affected_files": ["scripts/phase18i_authority_registry_operator.py"],
            "runtime_impact": "No executable rollback path for accepted BUY AI bundle yet.",
            "registry_impact": "Rollback metadata available, but no formal event flow.",
            "phase18_impact": "Rollback/revoke matrix item is PARTIAL.",
            "recommended_step": "Define and test authority-mediated rollback/revoke transaction after registry schema remediation.",
        },
        {
            "id": "K-GAP-007",
            "title": "Phase18 operators contain hard-coded run ids, artifact paths, dates, and bundle identities",
            "classification": "DOCUMENTATION_DRIFT",
            "severity": "MEDIUM",
            "evidence": ["RUN_ID/CREATED_AT constants", "candidate_dataset_c8de026d3ea8aa4d", "opportunity_training_phase18h_1081babc49b5d26b"],
            "root_cause": "Operators were implemented as phase acceptance scripts rather than reusable lifecycle CLIs.",
            "affected_contract": "No phase/test-specific shortcut and reproducible operator contract",
            "affected_files": ["scripts/phase18i_authority_registry_operator.py", "scripts/phase18j_runtime_discovery_freshness_gate_acceptance.py", "src/ai_fund_lab_v2/ai_lifecycle/training_pipeline.py"],
            "runtime_impact": "Future lifecycle runs require code edits or new scripts instead of parameterized inputs.",
            "registry_impact": "Promotion transaction ids are phase-specific.",
            "phase18_impact": "Implementation is useful evidence but not fully reusable lifecycle infrastructure.",
            "recommended_step": "Parameterize run ids, artifact refs, decision date, and component bundles; keep fixed Evidence ids only in reports.",
        },
    ]
    if tests["summary"]["status"] == "FAIL":
        gaps.append(
            {
                "id": "K-GAP-008",
                "title": "Phase18 cross-contract regression suite fails",
                "classification": "TEST_COVERAGE_GAP",
                "severity": "HIGH",
                "evidence": [tests["summary"], tests["stdout_tail"].splitlines()[-20:]],
                "root_cause": "Registry resolver tests fail after the invalid Promotion Candidate event was appended.",
                "affected_contract": "Resolver and runtime registry consumer cutover contract",
                "affected_files": ["tests/runtime_v2/test_phase16av_registry_consumer_cutover.py", "tests/artifact_registry/test_phase16au_registry_resolver.py"],
                "runtime_impact": "Accepted artifact lookup fails closed.",
                "registry_impact": "Formal registry cannot be validated as-is.",
                "phase18_impact": "Phase19 should not proceed until cross-contract regression is green.",
                "recommended_step": "Fix K-GAP-001, then rerun targeted and full lifecycle regression.",
            }
        )
    return gaps


def design_matrix() -> list[dict[str, Any]]:
    return [
        {"SoT Requirement": "PIT Dataset Rebuild", "Planned Phase18 Step": "Phase18-A/B/C", "Implementation": "src/ai_fund_lab_v2/ai_lifecycle dataset rebuild + real bundles", "Test / Evidence": "Phase18-B/C reports, dataset artifacts, tests/ai_lifecycle/test_phase18b", "Status": "PASS", "Gap": ""},
        {"SoT Requirement": "Training / Validation", "Planned Phase18 Step": "Phase18-D/F/H", "Implementation": "training_pipeline + Phase18 F/H opportunity redesign artifacts", "Test / Evidence": "Phase18-D/F/H reports, training bundles, tests/ai_lifecycle/test_phase18d", "Status": "PARTIAL", "Gap": "Reusable pipeline has fixed date split and phase-specific scripts; no scheduler trigger."},
        {"SoT Requirement": "Promotion Readiness", "Planned Phase18 Step": "Phase18-G/H", "Implementation": "Phase18-G/H review scripts and reports", "Test / Evidence": "Promotion blocking matrix and H reassessment", "Status": "PASS", "Gap": ""},
        {"SoT Requirement": "Authority", "Planned Phase18 Step": "Phase18-I", "Implementation": "Evidence-derived decision function", "Test / Evidence": "Authority decision artifact", "Status": "PARTIAL", "Gap": "Operator is phase-specific and hard-coded."},
        {"SoT Requirement": "Registry Promotion Candidate", "Planned Phase18 Step": "Phase18-I", "Implementation": "Promotion candidate transaction appended to event log", "Test / Evidence": "Full registry validation FAIL/HALT", "Status": "CONTRACT_CONFLICT", "Gap": "Promotion Candidate event violates registry schema."},
        {"SoT Requirement": "Runtime Discovery", "Planned Phase18 Step": "Phase18-J", "Implementation": "Read-only report script", "Test / Evidence": "Phase18-J report", "Status": "PARTIAL", "Gap": "Not integrated into runtime_v2 control plane; resolver currently halted by registry log."},
        {"SoT Requirement": "Freshness Gate", "Planned Phase18 Step": "Phase18-J", "Implementation": "Separate clocks in Phase18-J script", "Test / Evidence": "dataset_lag/model_training_lag/model_acceptance_age", "Status": "PARTIAL", "Gap": "Uses promotion bundle lineage for dataset/training while accepted registry entries lack physical training refs."},
        {"SoT Requirement": "Drift Gate", "Planned Phase18 Step": "Phase18-J", "Implementation": "Distribution smoke and classification", "Test / Evidence": "Phase18-J drift evidence", "Status": "PARTIAL", "Gap": "Feature/candidate/calibration drift are mostly smoke/forced PASS."},
        {"SoT Requirement": "Atomic BUY AI Bundle", "Planned Phase18 Step": "Phase18-I/J", "Implementation": "Joint bundle hash and compatibility evidence", "Test / Evidence": "atomic_buy_ai_bundle.json", "Status": "PASS", "Gap": ""},
        {"SoT Requirement": "Rollback / Revoke", "Planned Phase18 Step": "", "Implementation": "Rollback metadata only", "Test / Evidence": "rollback_metadata.json", "Status": "PARTIAL", "Gap": "No formal accepted rollback/revoke operator."},
        {"SoT Requirement": "Weekly Scheduler", "Planned Phase18 Step": "", "Implementation": "Not found", "Test / Evidence": "Repository search", "Status": "NOT_IMPLEMENTED", "Gap": "No eligibility/lock/retry/timeout/no-overlap scheduler."},
        {"SoT Requirement": "PM Policy Lifecycle", "Planned Phase18 Step": "", "Implementation": "Existing Phase16/17 registry acceptance only", "Test / Evidence": "PM registry artifacts and tests", "Status": "PARTIAL", "Gap": "No common Phase18 policy lifecycle operator."},
        {"SoT Requirement": "Safety Policy Lifecycle", "Planned Phase18 Step": "", "Implementation": "Existing runtime safety only", "Test / Evidence": "Repository search", "Status": "NOT_IMPLEMENTED", "Gap": "No Phase18 Safety policy lifecycle."},
        {"SoT Requirement": "Future AI Onboarding", "Planned Phase18 Step": "", "Implementation": "SoT text only", "Test / Evidence": "docs/02_architecture/ai_lifecycle_v2.md", "Status": "NOT_IMPLEMENTED", "Gap": "No onboarding contract implementation/test."},
        {"SoT Requirement": "Lifecycle E2E Acceptance", "Planned Phase18 Step": "", "Implementation": "A-J scripts produce artifacts but no single E2E regression", "Test / Evidence": "Targeted pytest fails in registry resolver suite", "Status": "CONTRACT_CONFLICT", "Gap": "Cross-contract suite not green."},
    ]


def reviews(gaps: list[dict[str, Any]], registry: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtime_data_plane": {
            "status": "PARTIAL",
            "evidence": ["src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py resolves accepted sets via registry, but registry resolver currently HALTs."],
            "training_in_runtime": False,
            "self_promotion": False,
            "registry_accepted_event_write_from_runtime": False,
            "promotion_candidate_direct_adoption": False,
            "model_path_fallback_risk": "Default paths exist but production path calls registry unless isolated test paths are explicitly allowed.",
        },
        "runtime_control_plane": {
            "status": "PARTIAL",
            "freshness_clocks": "Implemented in Phase18-J script; not runtime_v2 module.",
            "model_unhealthy_vs_market_no_opportunity": "Distinguished in Phase18-J script.",
            "hard_failure_blocks": "Rehearsed in script; not integrated runtime gate.",
            "sell_continuity": "SoT/older runtime tests indicate separation, but Phase18 did not revalidate SELL continuity under BUY AI gate states.",
        },
        "ai_lifecycle_control_plane": {
            "status": "PARTIAL",
            "dataset_training_separation": "PASS",
            "training_to_registry_accepted_direct_write": False,
            "authority_bypass": "Not for promotion candidate decision; registry event schema conflict remains.",
            "versioned_artifacts": "PASS for generated dataset/training bundles.",
            "partial_publication": "Dataset/training writers use tmp then os.replace.",
        },
        "registry": {
            "status": "CONTRACT_CONFLICT" if registry["full_event_log_validation"]["overall_result"] != "PASS" else "PASS",
            "event_log_validation": registry["full_event_log_validation"],
            "promotion_candidate_separated_from_accepted": True,
            "runtime_use_eligible_for_promotion_candidate": False,
        },
        "authority": {
            "status": "PARTIAL",
            "decision_from_evidence": True,
            "fixed_value_decision": False,
            "approved_with_review_supported": True,
            "accepted_without_authority_possible": "No accepted set update implemented in Phase18-I, but promotion event schema invalid.",
        },
        "sell_continuity": {
            "status": "PARTIAL",
            "evidence": ["SoT requires SELL continuity; Phase18-K did not find Phase18-specific tests for REVIEW_REQUIRED/BLOCK/MODEL_UNHEALTHY/MARKET_NO_OPPORTUNITY against SELL path."],
            "phase19_gap": True,
        },
        "weekly_scheduler": {"status": "NOT_IMPLEMENTED"},
        "pm_safety_lifecycle": {"status": "PARTIAL"},
        "future_ai_onboarding": {"status": "NOT_IMPLEMENTED"},
        "failure_semantics": {
            "status": "PARTIAL",
            "covered": ["dataset failure artifact", "training dataset authority failure", "promotion candidate rehearsal", "runtime gate rehearsal"],
            "not_covered": ["overlapping lifecycle run", "weekly scheduler lock", "formal rollback/revoke event", "integrated runtime hard drift"],
        },
    }


def build_report() -> dict[str, Any]:
    inventory = git_inventory()
    registry = registry_review()
    tests = run_tests()
    candidate_dataset = inspect_dataset_bundle(Path(".runtime/ai_lifecycle/datasets/candidate_ai/candidate_dataset_c8de026d3ea8aa4d"), ["target_date", "code"])
    opportunity_dataset = inspect_dataset_bundle(Path(".runtime/ai_lifecycle/datasets/opportunity_ai/opportunity_dataset_fbadc8091a31486d"), ["target_date", "code", "candidate_source_ref"])
    candidate_training = inspect_training_bundle(Path(".runtime/ai_lifecycle/training/candidate_ai/candidate_training_da0855d123ed1bed"))
    opportunity_training = inspect_training_bundle(
        Path(".runtime/ai_lifecycle/training/opportunity_ai/opportunity_training_phase18h_1081babc49b5d26b"),
        {"calibration_model.pkl", "calibration_parameters.json", "calibration_schema.json", "calibration_metadata.json", "calibration_hash.json"},
    )
    calibration = {
        "status": "PASS" if opportunity_training["bundle_complete"] else "FAIL",
        "files": {
            name: Path(".runtime/ai_lifecycle/training/opportunity_ai/opportunity_training_phase18h_1081babc49b5d26b", name).is_file()
            for name in ["calibration_model.pkl", "calibration_parameters.json", "calibration_schema.json", "calibration_metadata.json", "calibration_hash.json"]
        },
        "prediction_hash_match": read_json(Path("reports/phase_reports/phase18_h_promotion_blocking_issues_resolution.json"))["formal_challenger_bundle"]["runtime_compatible_reproduction"],
    }
    gaps = gap_inventory(registry, tests)
    primary = "PHASE18_K_CRITICAL_CONTRACT_VIOLATION_DETECTED" if any(g["severity"] == "CRITICAL" for g in gaps) else "PHASE18_K_DESIGN_CONFORMANCE_PASS_WITH_REVIEW"
    report = {
        "phase": PHASE,
        "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "executive_summary": {
            "primary_judgment": primary,
            "secondary_judgment": ["PHASE18_NOT_COMPLETE", "PHASE19_NOT_READY"],
            "summary": "Phase18 produced substantial Candidate/Opportunity lifecycle artifacts, but formal design conformance fails because the Phase18-I promotion-candidate event breaks the Artifact Registry event-log contract and Runtime resolver fails closed. Several lifecycle requirements remain partial or unimplemented.",
        },
        "documents_reviewed": docs_review(),
        "phase18_changed_file_inventory": inventory,
        "design_to_implementation_matrix": design_matrix(),
        "dataset_lifecycle_review": {"candidate": candidate_dataset, "opportunity": opportunity_dataset},
        "training_lifecycle_review": {"candidate": candidate_training, "opportunity": opportunity_training},
        "calibration_artifact_review": calibration,
        "promotion_lifecycle_review": {
            "phase18i_transaction": read_json(Path(".runtime/artifact_registry/promotion_candidates/transactions/promotion-tx-phase18i-1081babc49b5d26b/transaction.json")),
            "promotion_index": read_json(Path(".runtime/artifact_registry/promotion_candidates/promotion_candidate_index.json")),
        },
        "runtime_freshness_drift_review": read_json(Path("reports/phase_reports/phase18_j_runtime_discovery_freshness_gate_acceptance.json")),
        "registry_review": registry,
        "phase_reports_review": phase_report_acceptance(),
        "test_quality_review": {
            "targeted_regression": tests,
            "classification": {
                "unit_test": ["tests/ai_lifecycle/test_phase18b_common_pit_dataset_rebuild.py", "tests/ai_lifecycle/test_phase18d_training_pipeline.py"],
                "contract_test": ["tests/runtime_v2/test_phase16av_registry_consumer_cutover.py", "tests/artifact_registry/test_phase16au_registry_resolver.py"],
                "real_artifact_acceptance": ["Phase18-C/J reports and .runtime artifacts"],
                "failure_rehearsal": ["Phase18-B/D/I/J scripts"],
                "end_to_end_lifecycle_test": [],
            },
            "quality_findings": [
                "Phase18-B/D tests are mostly fixture based.",
                "Phase18-I/J have no dedicated pytest coverage.",
                "Cross-contract registry/runtime tests fail after Phase18-I event append.",
            ],
        },
        "phase_test_specific_shortcut_audit": shortcut_audit(inventory["phase18_changed_files"]),
        "reviews": reviews(gaps, registry),
        "gap_inventory": gaps,
        "severity_classification": {
            severity: [gap["id"] for gap in gaps if gap["severity"] == severity]
            for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        },
        "recommended_remediation_steps": [gap["recommended_step"] for gap in gaps],
        "phase18_completion_judgment": "Phase18 has important design contract violations and incomplete lifecycle coverage; Phase19 should not proceed before remediation.",
        "phase19_readiness_judgment": "PHASE19_NOT_READY",
        "non_mutation_confirmation": {
            "broker_write": False,
            "runtime_submit": False,
            "buy_restarted": False,
            "registry_accepted_set_changed": False,
            "promotion_candidate_runtime_adopted": False,
            "target_changed": False,
            "feature_changed": False,
            "bv15_changed": False,
        },
        "final_judgment": {
            "primary": primary,
            "secondary": ["PHASE18_NOT_COMPLETE", "PHASE19_NOT_READY"],
        },
    }
    return report


def write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# Phase18-K — AI Lifecycle v2 Design Conformance and Implementation Review",
        "",
        f"- Run ID: `{report['run_id']}`",
        f"- Primary: `{report['final_judgment']['primary']}`",
        f"- Secondary: `{', '.join(report['final_judgment']['secondary'])}`",
        "",
        "## Executive Summary",
        "",
        report["executive_summary"]["summary"],
        "",
        "## Key Findings",
        "",
    ]
    for gap in report["gap_inventory"]:
        lines.extend(
            [
                f"### {gap['id']} — {gap['title']}",
                "",
                f"- Severity: `{gap['severity']}`",
                f"- Classification: `{gap['classification']}`",
                f"- Affected contract: {gap['affected_contract']}",
                f"- Runtime impact: {gap['runtime_impact']}",
                f"- Registry impact: {gap['registry_impact']}",
                f"- Recommended step: {gap['recommended_step']}",
                "",
            ]
        )
    lines.extend(["## Design-to-Implementation Matrix", "", "| SoT Requirement | Phase18 Step | Implementation | Evidence | Status | Gap |", "|---|---|---|---|---|---|"])
    for row in report["design_to_implementation_matrix"]:
        lines.append(
            f"| {row['SoT Requirement']} | {row['Planned Phase18 Step']} | {row['Implementation']} | {row['Test / Evidence']} | `{row['Status']}` | {row['Gap']} |"
        )
    lines.extend(
        [
            "",
            "## Registry Evidence",
            "",
            f"- Full event log validation: `{report['registry_review']['full_event_log_validation']['overall_result']}` / `{report['registry_review']['full_event_log_validation']['failure_class']}`",
            f"- Event count: `{report['registry_review']['full_event_log_validation']['event_count']}`",
            "- First errors:",
        ]
    )
    for error in report["registry_review"]["full_event_log_validation"]["errors"][:12]:
        lines.append(f"  - {error}")
    lines.extend(
        [
            "",
            "## Test Evidence",
            "",
            f"- Targeted regression status: `{report['test_quality_review']['targeted_regression']['summary']['status']}`",
            f"- Passed: `{report['test_quality_review']['targeted_regression']['summary']['passed']}`",
            f"- Failed: `{report['test_quality_review']['targeted_regression']['summary']['failed']}`",
            "",
            "## Non-Mutation Confirmation",
            "",
        ]
    )
    for key, value in report["non_mutation_confirmation"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Final", "", f"`{report['final_judgment']['primary']}`", "", "`PHASE18_NOT_COMPLETE` / `PHASE19_NOT_READY`"])
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    write_json(REPORT_JSON, report)
    write_markdown(report)
    for name in [
        "documents_reviewed",
        "phase18_changed_file_inventory",
        "design_to_implementation_matrix",
        "dataset_lifecycle_review",
        "training_lifecycle_review",
        "calibration_artifact_review",
        "registry_review",
        "test_quality_review",
        "gap_inventory",
        "phase_test_specific_shortcut_audit",
    ]:
        write_json(EVIDENCE_DIR / f"{name}.json", report[name])
    print(json.dumps(report["final_judgment"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
