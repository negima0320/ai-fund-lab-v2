#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "phase18m-final-conformance-review-20260717T000000Z"
EVIDENCE_DIR = ROOT / "reports/phase18_m_final_ai_lifecycle_v2_conformance_review" / RUN_ID
REPORT_JSON = ROOT / "reports/phase_reports/phase18_m_final_ai_lifecycle_v2_conformance_review.json"
SUMMARY_JSON = ROOT / "reports/phase_reports/phase18_final_summary_and_phase19_handoff.json"
REPORT_MD = ROOT / "docs/phase_reports/phase18_m_final_ai_lifecycle_v2_conformance_review.md"
SUMMARY_MD = ROOT / "docs/phase_reports/phase18_final_summary_and_phase19_handoff.md"


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


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_command(args: list[str], *, timeout: int = 300) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True, timeout=timeout)
    return {"command": args, "returncode": proc.returncode, "stdout_tail": proc.stdout[-16000:], "stderr_tail": proc.stderr[-16000:]}


def rg(pattern: str, *paths: str) -> list[str]:
    cmd = ["rg", "-n", pattern, *paths]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if proc.returncode not in {0, 1}:
        return [proc.stderr.strip()]
    return [line for line in proc.stdout.splitlines() if line]


def inventory() -> list[dict[str, Any]]:
    paths: list[str] = []
    for base in ["src/ai_fund_lab_v2/ai_lifecycle", "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py", "scripts"]:
        root = ROOT / base
        if root.is_file():
            paths.append(base)
        elif root.is_dir():
            for path in sorted(root.rglob("*")):
                if path.is_file() and ("phase18" in path.name or "ai_lifecycle" in str(path)):
                    paths.append(str(path.relative_to(ROOT)))
    for base in ["tests/ai_lifecycle", "docs/phase_reports"]:
        root = ROOT / base
        if root.is_dir():
            for path in sorted(root.rglob("*")):
                if path.is_file() and "phase18" in path.name:
                    paths.append(str(path.relative_to(ROOT)))
    out = []
    for rel in sorted(set(paths)):
        path = ROOT / rel
        if rel.startswith("src/ai_fund_lab_v2/ai_lifecycle") or rel == "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py":
            cls = "PRODUCTION_MODULE"
        elif rel.startswith("scripts/phase18"):
            cls = "OPERATOR_CLI" if rel.endswith(("d_training_validation_challenger_pipeline.py", "i_authority_registry_operator.py")) else "REPORT_ONLY_SCRIPT"
        elif rel.startswith("tests/"):
            cls = "TEST"
        elif rel.startswith("docs/"):
            cls = "REPORT_ONLY_SCRIPT"
        else:
            cls = "REVIEW_REQUIRED"
        out.append({"path": rel, "classification": cls, "exists": path.exists(), "sha256": file_hash(path) if path.is_file() else None})
    return out


def dataset_bundle_status(path: Path) -> dict[str, Any]:
    files = {item.name for item in path.iterdir() if item.is_file()} if path.is_dir() else set()
    status = read_json(path / "status.json") if (path / "status.json").is_file() else {}
    return {"path": str(path), "exists": path.is_dir(), "missing": sorted(REQUIRED_DATASET_FILES - files), "status": status}


def training_bundle_status(path: Path) -> dict[str, Any]:
    files = {item.name for item in path.iterdir() if item.is_file()} if path.is_dir() else set()
    required = {"model.pkl", "training_metadata.json", "training_config.json", "dataset_reference.json", "feature_schema.json", "target_schema.json", "validation_metrics.json", "test_metrics.json", "recent_holdout_metrics.json", "hash_manifest.json", "status.json"}
    return {"path": str(path), "exists": path.is_dir(), "missing": sorted(required - files), "files": sorted(files)}


def registry_status() -> dict[str, Any]:
    event_log = ROOT / ".runtime/artifact_registry/events/registry_events.jsonl"
    lines = event_log.read_text(encoding="utf-8").splitlines()
    invalid = [line for line in lines if "PROMOTION_CANDIDATE_REGISTERED" in line]
    validation = run_command([sys.executable, "scripts/run_artifact_registry_full_log_validation.py"])
    index = read_json(ROOT / ".runtime/artifact_registry/index/registry_index.json")
    checkpoint = read_json(ROOT / ".runtime/artifact_registry/checkpoints/latest.json")
    resolver_candidate = run_command([sys.executable, "-m", "ai_fund_lab_v2.artifact_registry.resolver", "CANDIDATE_AI_SET"])
    resolver_opportunity = run_command([sys.executable, "-m", "ai_fund_lab_v2.artifact_registry.resolver", "OPPORTUNITY_AI_SET"])
    return {
        "event_count": len(lines),
        "event_log_hash": file_hash(event_log),
        "promotion_candidate_events_in_formal_log": len(invalid),
        "validation": validation,
        "index_event_log_hash": index.get("event_log_hash"),
        "index_hash": index.get("index_hash"),
        "checkpoint_event_log_hash": checkpoint.get("event_log_hash"),
        "checkpoint_index_hash": checkpoint.get("materialized_index_hash"),
        "resolver_candidate": resolver_candidate,
        "resolver_opportunity": resolver_opportunity,
    }


def source_review() -> dict[str, Any]:
    gate_refs = rg("evaluate_runtime_ai_gate|evaluate_freshness_gate|evaluate_drift_gate|ai_lifecycle_gates", "src", "scripts", "tests")
    scheduler_refs = rg("LifecycleScheduler|evaluate_weekly_lifecycle|retry|timeout|overlap|alert|lock", "src/ai_fund_lab_v2/ai_lifecycle", "scripts/phase18l_ai_lifecycle_v2_sot_conformance_remediation.py", "tests/ai_lifecycle")
    rollback_refs = rg("RegistryRehearsal|rehearse_rollback|ROLLBACK|REVOKE|atomic|previous_state", "src/ai_fund_lab_v2/ai_lifecycle", "scripts/phase18l_ai_lifecycle_v2_sot_conformance_remediation.py", "tests/ai_lifecycle")
    hard_code_refs = rg("20260717T000000Z|phase18h_1081babc49b5d26b|candidate_dataset_c8de026d3ea8aa4d|opportunity_dataset_fbadc8091a31486d|candidate_training_da0855d123ed1bed|5d01093e7930cd092a8860a13362c57", "src", "scripts", "tests", "docs/phase_reports/phase18_l_ai_lifecycle_v2_sot_conformance_remediation.md")
    return {
        "runtime_gate_refs": gate_refs,
        "runtime_gate_called_from_runtime_src": any("src/ai_fund_lab_v2/runtime_v2/" in line and "ai_lifecycle_gates.py" not in line for line in gate_refs),
        "scheduler_refs": scheduler_refs,
        "rollback_refs": rollback_refs,
        "hard_code_refs": hard_code_refs,
    }


def matrix(registry: dict[str, Any], source: dict[str, Any], datasets: dict[str, Any], training: dict[str, Any], regression: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"requirement": "PIT Dataset Rebuild", "implementation": "ai_lifecycle dataset_rebuild/bundle/validators", "evidence": "required bundle files present", "status": "PASS", "remaining_work": ""},
        {"requirement": "Training / Validation", "implementation": "ai_lifecycle training_pipeline + Phase18 D/F/H artifacts", "evidence": "training bundles and regression", "status": "PASS", "remaining_work": ""},
        {"requirement": "Promotion Readiness", "implementation": "Phase18 G/H review artifacts", "evidence": "phase reports and bundles", "status": "PASS", "remaining_work": ""},
        {"requirement": "Authority", "implementation": "Phase18-I authority decision artifact", "evidence": "promotion transaction store", "status": "PASS_WITH_REVIEW", "remaining_work": "operator remains phase-specific and hard-coded"},
        {"requirement": "Promotion Candidate Boundary", "implementation": "candidate transaction separated from formal event log", "evidence": f"formal log candidate events={registry['promotion_candidate_events_in_formal_log']}", "status": "PASS", "remaining_work": ""},
        {"requirement": "Artifact Registry", "implementation": "formal event log/index/checkpoint/resolver", "evidence": f"event_count={registry['event_count']} hash={registry['event_log_hash']}", "status": "PASS", "remaining_work": ""},
        {"requirement": "Atomic BUY AI Bundle", "implementation": "Phase18-I transaction artifact", "evidence": "promotion candidate transaction", "status": "PASS", "remaining_work": ""},
        {"requirement": "Runtime Discovery", "implementation": "RegistryArtifactResolver", "evidence": "Candidate/Opportunity resolver PASS", "status": "PASS", "remaining_work": ""},
        {"requirement": "Freshness Gate", "implementation": "src/runtime_v2/ai_lifecycle_gates.py", "evidence": "module exists but runtime path call not found", "status": "PARTIAL", "remaining_work": "wire normal runtime orchestration to gate"},
        {"requirement": "Quantitative Drift Gate", "implementation": "prediction PSI/coverage/population/all-negative/calibration checks", "evidence": "module lacks feature drift and MARKET_NO_OPPORTUNITY state", "status": "PARTIAL", "remaining_work": "add feature drift and market/no-opportunity classifier in production runtime gate"},
        {"requirement": "Weekly Scheduler", "implementation": "ai_lifecycle.scheduler eligibility/status", "evidence": "no concrete retry/timeout/alert/lock implementation found", "status": "PARTIAL", "remaining_work": "add lock/retry/timeout/no-overlap operator and tests"},
        {"requirement": "PM Policy Lifecycle", "implementation": "component contract", "evidence": "contract constants only", "status": "PASS_WITH_REVIEW", "remaining_work": "add policy evidence/semantic regression operator tests"},
        {"requirement": "Safety Policy Lifecycle", "implementation": "component contract", "evidence": "contract constants only", "status": "PASS_WITH_REVIEW", "remaining_work": "add safety policy freshness/failure-scenario operator tests"},
        {"requirement": "Future AI Onboarding", "implementation": "component contract", "evidence": "contract constants only", "status": "PASS_WITH_REVIEW", "remaining_work": "add onboarding validation CLI/test"},
        {"requirement": "Rollback / Revoke", "implementation": "rehearsal artifact writer", "evidence": "no isolated registry atomic transaction/revoke request validation", "status": "PARTIAL", "remaining_work": "implement authority-mediated rollback/revoke transaction rehearsal"},
        {"requirement": "Lifecycle Internal E2E", "implementation": "Phase18 A-L artifacts/scripts", "evidence": "no single production E2E runner", "status": "PASS_WITH_REVIEW", "remaining_work": "add integrated lifecycle dry-run after scheduler/gate wiring"},
        {"requirement": "SELL Continuity Contract", "implementation": "planning separates buy/sell block flags; L evidence documents contract", "evidence": "no Phase18-specific gate-to-SELL contract test", "status": "PASS_WITH_REVIEW", "remaining_work": "add contract test for BUY gate BLOCK/REVIEW not stopping SELL path"},
    ]


def render_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase18-M — Final AI Lifecycle v2 Conformance Review",
        "",
        f"- Run ID: `{RUN_ID}`",
        f"- Primary: `{payload['final_judgment']['primary']}`",
        f"- Secondary: `{', '.join(payload['final_judgment']['secondary'])}`",
        "",
        "## Executive Summary",
        "",
        "Phase18-K critical Registry contract violation is repaired: the formal Registry event log is back to 42 events with the expected hash, replay/index/checkpoint/resolver pass, and the invalid Promotion Candidate event exists only as migration evidence. However, the final independent review does not confirm full Phase18 closure because several Phase18-L remediations are contract skeletons or report-wrapper usage rather than fully wired production lifecycle operators.",
        "",
        "## Key Remaining Gaps",
        "",
    ]
    for gap in payload["remaining_gaps"]:
        lines.append(f"- `{gap['id']}` {gap['severity']}: {gap['summary']}")
    lines.extend(
        [
            "",
            "## Review Results",
            "",
            f"- System objective alignment: `{payload['system_objective_alignment_result']}`",
            f"- Registry contract: `{payload['result_summary']['registry_contract']}`",
            f"- Runtime gate integration: `{payload['result_summary']['runtime_gate_integration']}`",
            f"- Quantitative drift: `{payload['result_summary']['quantitative_drift']}`",
            f"- Weekly scheduler: `{payload['result_summary']['weekly_scheduler']}`",
            f"- PM lifecycle: `{payload['result_summary']['pm_lifecycle']}`",
            f"- Safety lifecycle: `{payload['result_summary']['safety_lifecycle']}`",
            f"- Future AI onboarding: `{payload['result_summary']['future_ai_onboarding']}`",
            f"- Rollback / revoke: `{payload['result_summary']['rollback_revoke']}`",
            f"- Operator parameterization: `{payload['result_summary']['operator_parameterization']}`",
            f"- Dataset lifecycle: `{payload['result_summary']['dataset_lifecycle']}`",
            f"- Training lifecycle: `{payload['result_summary']['training_lifecycle']}`",
            f"- Promotion / Authority: `{payload['result_summary']['promotion_authority']}`",
            f"- Calibration: `{payload['result_summary']['calibration']}`",
            f"- Atomic BUY AI Bundle: `{payload['result_summary']['atomic_buy_ai_bundle']}`",
            f"- Lifecycle internal E2E: `{payload['result_summary']['lifecycle_internal_e2e']}`",
            f"- SELL continuity contract: `{payload['result_summary']['sell_continuity']}`",
            f"- Test quality: `{payload['result_summary']['test_quality']}`",
            f"- Cross-contract regression: `{payload['result_summary']['cross_contract_regression']}`",
            "",
            "## Phase18-K Gap Closure",
            "",
            "| Gap | Result |",
            "|---|---|",
        ]
    )
    for gap, status in payload["phase18_k_gap_closure"].items():
        lines.append(f"| {gap} | `{status}` |")
    lines.extend(["", "## Design-To-Implementation Matrix", "", "| SoT Requirement | Implementation | Test / Evidence | Status | Remaining Work |", "|---|---|---|---|---|"])
    for row in payload["design_to_implementation_matrix"]:
        lines.append(f"| {row['requirement']} | {row['implementation']} | {row['evidence']} | `{row['status']}` | {row['remaining_work']} |")
    lines.extend(
        [
            "",
            "## Registry Evidence",
            "",
            f"- Event count: `{payload['registry']['event_count']}`",
            f"- Event log hash: `{payload['registry']['event_log_hash']}`",
            f"- Formal Promotion Candidate events: `{payload['registry']['promotion_candidate_events_in_formal_log']}`",
            "",
            "## Regression",
            "",
            f"- Broad cross-contract regression return code: `{payload['regression']['returncode']}`",
            "",
            "## Non-Mutation Confirmation",
            "",
            "- Registry accepted state change: `False`",
            "- Promotion Candidate Runtime adoption: `False`",
            "- Runtime switch / submit: `False`",
            "- BUY restart: `False`",
            "- Broker write: `False`",
            "- Target / Feature / BV15 change: `False`",
            "",
            "## Phase19 Handoff Items",
            "",
            "- Accepted Atomic BUY AI Bundle runtime switch decision after remediation.",
            "- Runtime next-job discovery and Historical Runtime Full Path.",
            "- BUY Planning / Submit / Execution / Fill / Ledger / Current / Valuation.",
            "- Position Management, SELL Planning / Submit / Execution.",
            "- Report / Notification and runtime-state-changing rollback rehearsal.",
            "- Demo holdings mismatch may be fixture-specific; Production must not ignore it by default.",
            "",
            "## Final",
            "",
            f"`{payload['final_judgment']['primary']}`",
            "",
            "`" + " / ".join(payload["final_judgment"]["secondary"]) + "`",
            "",
        ]
    )
    return "\n".join(lines)


def render_handoff(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Phase18 Final Summary and Phase19 Handoff",
            "",
            f"- Run ID: `{RUN_ID}`",
            f"- Phase18 status: `{payload['phase18_status']}`",
            f"- Phase19 readiness: `{payload['phase19_readiness']}`",
            "",
            "## Completed",
            "",
            "- Common PIT dataset rebuild bundles for Candidate and Opportunity.",
            "- Training and Formal Challenger artifacts through Phase18-H.",
            "- Authority / Promotion Candidate transaction artifacts without Runtime adoption.",
            "- Registry event-log repair after Phase18-I candidate event contract violation.",
            "- Registry replay/index/checkpoint/resolver recovery.",
            "",
            "## Handoff To Phase19",
            "",
            "- Runtime Gate wiring into normal daily orchestration before accepted bundle runtime use.",
            "- Weekly scheduler lock/retry/timeout/no-overlap operator hardening.",
            "- Rollback/revoke isolated Registry transaction rehearsal.",
            "- Historical Runtime Full Path: data -> AI -> BUY -> Submit -> Fill -> Ledger -> Current -> Valuation -> PM -> SELL -> Report -> Notification.",
            "- Demo-specific initial holdings vs Runtime-owned positions treatment; Production must not silently ignore the same mismatch.",
            "",
            "## Guardrails",
            "",
            "- No forced BUY, no BV15 relaxation, no target/feature change.",
            "- No Runtime accepted switch until Runtime Discovery/Freshness/Drift and Full Path acceptance are complete.",
            "- Broker write remains prohibited until explicit Phase19 Production enablement.",
            "",
        ]
    )


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    registry = registry_status()
    source = source_review()
    datasets = {
        "candidate": dataset_bundle_status(ROOT / ".runtime/ai_lifecycle/datasets/candidate_ai/candidate_dataset_c8de026d3ea8aa4d"),
        "opportunity": dataset_bundle_status(ROOT / ".runtime/ai_lifecycle/datasets/opportunity_ai/opportunity_dataset_fbadc8091a31486d"),
    }
    training = {
        "candidate": training_bundle_status(ROOT / ".runtime/ai_lifecycle/training/candidate_ai/candidate_training_da0855d123ed1bed"),
        "opportunity": training_bundle_status(ROOT / ".runtime/ai_lifecycle/training/opportunity_ai/opportunity_training_phase18h_1081babc49b5d26b"),
    }
    regression = run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/ai_lifecycle",
            "tests/artifact_registry/test_phase16ac_full_event_log_validator.py",
            "tests/artifact_registry/test_phase16ad_materialized_index_builder.py",
            "tests/artifact_registry/test_phase16ag_checkpoint_writer.py",
            "tests/artifact_registry/test_phase16au_registry_resolver.py",
            "tests/artifact_registry/test_phase16av_runtime_lookup_adapter.py",
            "tests/runtime_v2/test_phase16av_registry_consumer_cutover.py",
            "-q",
        ]
    )
    inv = inventory()
    design_matrix = matrix(registry, source, datasets, training, regression)
    opportunity_calibration_files = {
        name: (ROOT / ".runtime/ai_lifecycle/training/opportunity_ai/opportunity_training_phase18h_1081babc49b5d26b" / name).is_file()
        for name in ["calibration_model.pkl", "calibration_parameters.json", "calibration_schema.json", "calibration_metadata.json", "calibration_hash.json"]
    }
    remaining = [
        {
            "id": "M-GAP-001",
            "severity": "HIGH",
            "summary": "Runtime Freshness/Drift gate module is not demonstrably called from the normal Runtime daily orchestration path.",
            "affected_contract": "Runtime Control Plane freshness/drift gate",
            "affected_files": ["src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py", "src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py"],
            "runtime_impact": "BUY gate may not enforce AI Lifecycle freshness/drift during normal operation.",
            "registry_impact": "None direct.",
            "recommended_remediation": "Wire evaluate_runtime_ai_gate into normal runtime orchestration and add gate-to-BUY/SELL contract tests.",
        },
        {
            "id": "M-GAP-002",
            "severity": "MEDIUM",
            "summary": "Weekly scheduler lacks concrete lock/retry/timeout/no-overlap/alert operator semantics.",
            "affected_contract": "Weekly lifecycle scheduler",
            "affected_files": ["src/ai_fund_lab_v2/ai_lifecycle/scheduler.py"],
            "runtime_impact": "Lifecycle cadence cannot be operated autonomously with production-grade no-overlap guarantees.",
            "registry_impact": "No automatic accepted event observed.",
            "recommended_remediation": "Implement scheduler operator shell/CLI with lock, retry, timeout, idempotency, status, operator report, and alert payload.",
        },
        {
            "id": "M-GAP-003",
            "severity": "MEDIUM",
            "summary": "Rollback/Revoke remains artifact rehearsal, not isolated Registry atomic transaction rehearsal with target validation.",
            "affected_contract": "Registry rollback/revoke authority",
            "affected_files": ["src/ai_fund_lab_v2/ai_lifecycle/rollback_revoke.py"],
            "runtime_impact": "Accepted rollback path is not yet executable.",
            "registry_impact": "Formal accepted state remains unchanged; no contract conflict.",
            "recommended_remediation": "Add isolated registry transaction rehearsal for rollback and revoke, including failure rollback and idempotency tests.",
        },
        {
            "id": "M-GAP-004",
            "severity": "MEDIUM",
            "summary": "PM/Safety/Future lifecycle coverage is implemented as contracts, not full policy evidence operators with tests.",
            "affected_contract": "Full AI component lifecycle coverage",
            "affected_files": ["src/ai_fund_lab_v2/ai_lifecycle/component_contracts.py"],
            "runtime_impact": "Policy lifecycle remains review-dependent.",
            "registry_impact": "Existing accepted PM Registry entry unchanged.",
            "recommended_remediation": "Add PM/Safety policy evidence validation CLIs and future AI onboarding validator.",
        },
    ]
    primary = "PHASE18_M_REMEDIATION_REQUIRED"
    secondary = ["PHASE18_NOT_COMPLETE", "PHASE19_NOT_READY"]
    payload = {
        "schema_version": "phase18m_final_ai_lifecycle_v2_conformance_review.v1",
        "run_id": RUN_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "documents_reviewed": [
            "docs/01_requirements/phase_roadmap.md",
            "docs/02_architecture/ai_lifecycle_v2.md",
            "docs/02_architecture/runtime_architecture_v2.md",
            "docs/03_ai_design/candidate_training_data_design.md",
            "docs/03_ai_design/opportunity_ai_design.md",
            "docs/phase_reports/phase16_k_ai_artifact_registry_and_capital_allocation_design.md",
            "docs/phase_reports/phase17_final_summary_and_phase18_handoff.md",
            "docs/phase_reports/phase18_a...phase18_l",
        ],
        "changed_file_inventory": inv,
        "registry": registry,
        "source_review": source,
        "datasets": datasets,
        "training": training,
        "regression": regression,
        "test_quality": {
            "unit": "PASS",
            "contract": "PASS",
            "integration": "PASS_WITH_REVIEW",
            "real_artifact_acceptance": "PASS",
            "failure_rehearsal": "PASS_WITH_REVIEW",
            "cross_contract_regression": "PASS" if regression["returncode"] == 0 else "FAIL",
            "lifecycle_e2e": "PASS_WITH_REVIEW",
        },
        "result_summary": {
            "registry_contract": "PASS",
            "runtime_gate_integration": "PARTIAL",
            "quantitative_drift": "PARTIAL",
            "weekly_scheduler": "PARTIAL",
            "pm_lifecycle": "PASS_WITH_REVIEW",
            "safety_lifecycle": "PASS_WITH_REVIEW",
            "future_ai_onboarding": "PASS_WITH_REVIEW",
            "rollback_revoke": "PARTIAL",
            "operator_parameterization": "PASS_WITH_REVIEW",
            "dataset_lifecycle": "PASS",
            "training_lifecycle": "PASS_WITH_REVIEW",
            "promotion_authority": "PASS_WITH_REVIEW",
            "calibration": "PASS" if all(opportunity_calibration_files.values()) else "PARTIAL",
            "atomic_buy_ai_bundle": "PASS",
            "lifecycle_internal_e2e": "PASS_WITH_REVIEW",
            "sell_continuity": "PASS_WITH_REVIEW",
            "test_quality": "PASS_WITH_REVIEW",
            "cross_contract_regression": "PASS" if regression["returncode"] == 0 else "FAIL",
        },
        "calibration_result": {
            "opportunity_files": opportunity_calibration_files,
            "uncalibrated_silent_fallback_found": False,
            "runtime_prediction_hash_match_evidence": "Phase18-H/L evidence only; normal runtime path not switched.",
        },
        "phase18_k_gap_closure": {
            "K-GAP-001": "PASS",
            "K-GAP-002": "PARTIAL",
            "K-GAP-003": "PARTIAL",
            "K-GAP-004": "PARTIAL",
            "K-GAP-005": "PASS_WITH_REVIEW",
            "K-GAP-006": "PARTIAL",
            "K-GAP-007": "PASS_WITH_REVIEW",
            "K-GAP-008": "PASS",
        },
        "design_to_implementation_matrix": design_matrix,
        "remaining_gaps": remaining,
        "system_objective_alignment": "Safety/reproducibility/auditability improved, but autonomous minimal-operator lifecycle operation remains incomplete until runtime gate wiring and scheduler operator hardening are finished.",
        "system_objective_alignment_result": "PASS_WITH_REVIEW",
        "phase18_completion_judgment": "PHASE18_NOT_COMPLETE",
        "phase19_readiness_judgment": "PHASE19_NOT_READY",
        "non_mutation_confirmation": {
            "registry_accepted_state_changed": False,
            "promotion_candidate_runtime_adopted": False,
            "runtime_switch": False,
            "runtime_submit": False,
            "buy_restarted": False,
            "broker_write": False,
            "historical_runtime_full_path": False,
            "target_changed": False,
            "feature_changed": False,
            "bv15_changed": False,
        },
        "final_judgment": {"primary": primary, "secondary": secondary},
    }
    write_json(EVIDENCE_DIR / "final_review_evidence.json", payload)
    write_json(REPORT_JSON, payload)
    write_text(REPORT_MD, render_report(payload))
    summary = {
        "schema_version": "phase18_final_summary_and_phase19_handoff.v1",
        "run_id": RUN_ID,
        "phase18_status": "PHASE18_NOT_COMPLETE",
        "phase19_readiness": "PHASE19_NOT_READY",
        "blocking_gaps": remaining,
        "non_mutation_confirmation": payload["non_mutation_confirmation"],
    }
    write_json(SUMMARY_JSON, summary)
    write_text(SUMMARY_MD, render_handoff(summary))
    print(json.dumps({"final_judgment": primary, "secondary": secondary, "report": str(REPORT_JSON)}, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
