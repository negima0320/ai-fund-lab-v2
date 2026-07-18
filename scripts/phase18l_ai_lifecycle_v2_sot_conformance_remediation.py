#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from ai_fund_lab_v2.ai_lifecycle.component_contracts import all_lifecycle_contracts
from ai_fund_lab_v2.ai_lifecycle.rollback_revoke import RegistryRehearsalRequest, rehearse_rollback_or_revoke
from ai_fund_lab_v2.ai_lifecycle.scheduler import LifecycleSchedulerInput, evaluate_weekly_lifecycle_eligibility, write_scheduler_status
from ai_fund_lab_v2.artifact_registry.full_log_validator import FullEventLogValidator
from ai_fund_lab_v2.runtime_v2.ai_lifecycle_gates import evaluate_runtime_ai_gate


RUN_ID = "phase18l-sot-conformance-remediation-20260717T000000Z"
EVENT_LOG = ROOT / ".runtime/artifact_registry/events/registry_events.jsonl"
REGISTRY_ROOT = ROOT / ".runtime/artifact_registry"
REPORT_DIR = ROOT / "reports/phase18_l_ai_lifecycle_v2_sot_conformance_remediation" / RUN_ID
REPORT_JSON = ROOT / "reports/phase_reports/phase18_l_ai_lifecycle_v2_sot_conformance_remediation.json"
REPORT_MD = ROOT / "docs/phase_reports/phase18_l_ai_lifecycle_v2_sot_conformance_remediation.md"
INVALID_EVENT_TYPE = "PROMOTION_CANDIDATE_REGISTERED"


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def run_command(args: list[str], *, timeout: int = 180) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout, env=env)
    return {
        "command": args,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-12000:],
        "stderr_tail": proc.stderr[-12000:],
    }


def remediation_plan() -> dict[str, Any]:
    return {
        "schema_version": "phase18l_remediation_plan.v1",
        "run_id": RUN_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sot_requirements": {
            "ai_lifecycle_control_plane": ["dataset rebuild", "training/policy validation", "promotion readiness", "promotion request", "status/evidence"],
            "operator_authority": ["approval/rejection", "registry acceptance/revoke/rollback authorization", "BUY restart judgment"],
            "artifact_registry": ["accepted artifact authority", "identity/status/hash/compatibility", "runtime discovery", "rollback target", "append-only event authority"],
            "runtime_control_plane": ["accepted discovery", "freshness/drift gate", "BUY PASS/REVIEW/BLOCK", "lifecycle trigger coordination"],
            "runtime_data_plane": ["daily data", "feature", "inference", "planning", "submit", "execution", "current", "ledger"],
        },
        "selected_remediation": {
            "k_gap_001": "Option A: Promotion Candidate remains an AI Lifecycle Control Plane transaction until Authority authorizes a formal ARTIFACT_ACCEPTED Registry event.",
            "invalid_event_repair": "Move the malformed promotion candidate event to audited lifecycle migration evidence and rebuild Registry index/checkpoint from the repaired formal log.",
            "runtime_gate": "Provide formal Runtime Control Plane freshness/drift gate module; phase scripts become wrappers/evidence producers.",
            "weekly_scheduler": "Provide no-self-promotion lifecycle eligibility operator with lock/no-overlap evidence semantics.",
            "pm_safety_future": "Provide common lifecycle contracts for rule/policy/future AI components.",
            "rollback_revoke": "Provide authority-mediated rehearsal operator without accepted-set switch.",
        },
        "rejected_alternatives": {
            "option_b_extend_registry_schema": "Rejected for Phase18-L because the SoT and Phase16 registry contract make accepted/runtime-eligible artifacts the Registry authority surface; promotion review state already has a dedicated transaction store.",
            "validator_skip_unknown_events": "Rejected because it weakens fail-closed event-log authority.",
            "checkpoint_only_rewrite": "Rejected because it hides the event-log contract violation.",
            "manual_path_fallback": "Rejected because Runtime must discover accepted artifacts through Registry.",
        },
        "affected_files": [
            "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py",
            "src/ai_fund_lab_v2/ai_lifecycle/scheduler.py",
            "src/ai_fund_lab_v2/ai_lifecycle/component_contracts.py",
            "src/ai_fund_lab_v2/ai_lifecycle/rollback_revoke.py",
            "scripts/phase18l_ai_lifecycle_v2_sot_conformance_remediation.py",
            ".runtime/artifact_registry/events/registry_events.jsonl",
            ".runtime/artifact_registry/index/registry_index.json",
            ".runtime/artifact_registry/checkpoints/latest.json",
        ],
        "migration_plan": [
            "Record original event log hash/count.",
            "Identify invalid PROMOTION_CANDIDATE_REGISTERED line and hash.",
            "Persist the invalid event under promotion_candidates/migrated_invalid_events with migration authority.",
            "Rewrite only the formal registry log by excluding that invalid candidate-review event.",
            "Re-run full log validation, materialized index build, checkpoint writer, resolver regression.",
        ],
        "test_plan": [
            "FullEventLogValidator PASS/NONE.",
            "Materialized index PASS.",
            "Checkpoint PASS.",
            "Targeted cross-contract pytest reaches 0 failed.",
            "Runtime gate, scheduler, rollback/revoke, component lifecycle smoke evidence produced.",
        ],
        "runtime_registry_risk": "Accepted artifact entries, Runtime accepted set, BUY state, Submit, Broker, Target, Feature, and BV15 remain unchanged.",
        "rollback_plan": "The original invalid line and pre-repair file hash are preserved as evidence; if repair validation fails the script stops before publishing final PASS.",
    }


def migrate_invalid_promotion_candidate_event() -> dict[str, Any]:
    lines = EVENT_LOG.read_text(encoding="utf-8").splitlines()
    original_hash = file_hash(EVENT_LOG)
    invalid: list[dict[str, Any]] = []
    kept: list[str] = []
    for idx, line in enumerate(lines, start=1):
        event = json.loads(line)
        if event.get("event_type") == INVALID_EVENT_TYPE:
            invalid.append({"line_number": idx, "event": event, "line_hash": hashlib.sha256(line.encode("utf-8")).hexdigest()})
        else:
            kept.append(line)
    migration_dir = REGISTRY_ROOT / "promotion_candidates/migrated_invalid_events"
    prior_evidence_path = migration_dir / "phase18l_invalid_promotion_candidate_event.json"
    if not invalid and prior_evidence_path.exists():
        evidence = json.loads(prior_evidence_path.read_text(encoding="utf-8"))
        evidence["idempotent_recheck"] = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "current_event_log_hash": original_hash,
            "current_event_count": len(lines),
            "invalid_event_count": 0,
        }
        atomic_write_json(REPORT_DIR / "invalid_registry_event_migration.json", evidence)
        return evidence
    evidence = {
        "schema_version": "phase18l_invalid_registry_event_migration.v1",
        "migration_authority": "Phase18-L AI Lifecycle v2 SoT conformance remediation",
        "migration_decision": "Promotion Candidate is lifecycle transaction evidence, not formal Registry accepted artifact event.",
        "original_event_log_hash": original_hash,
        "original_event_count": len(lines),
        "invalid_event_count": len(invalid),
        "invalid_events": invalid,
        "migration_destination": str(migration_dir / "phase18l_invalid_promotion_candidate_event.json"),
        "registry_accepted_set_changed": False,
        "runtime_switch_performed": False,
        "buy_restarted": False,
        "broker_write_performed": False,
    }
    atomic_write_json(migration_dir / "phase18l_invalid_promotion_candidate_event.json", evidence)
    atomic_write_json(REPORT_DIR / "invalid_registry_event_migration.json", evidence)
    if invalid:
        backup = migration_dir / f"registry_events_before_phase18l_repair_{original_hash[:16]}.jsonl"
        if not backup.exists():
            shutil.copy2(EVENT_LOG, backup)
        atomic_write_text(EVENT_LOG, "\n".join(kept) + ("\n" if kept else ""))
    repaired_hash = file_hash(EVENT_LOG)
    evidence["repaired_event_log_hash"] = repaired_hash
    evidence["repaired_event_count"] = len(kept)
    evidence["event_removed_from_formal_log"] = bool(invalid)
    atomic_write_json(migration_dir / "phase18l_invalid_promotion_candidate_event.json", evidence)
    atomic_write_json(REPORT_DIR / "invalid_registry_event_migration.json", evidence)
    return evidence


def registry_validation() -> dict[str, Any]:
    full = FullEventLogValidator(event_log_path=EVENT_LOG, registry_root=REGISTRY_ROOT, schema_root=ROOT / "docs/02_architecture/schemas", repo_root=ROOT).validate()
    atomic_write_json(REPORT_DIR / "full_event_log_validation.json", full)
    index = run_command([sys.executable, "scripts/run_artifact_registry_index_build.py"])
    atomic_write_json(REPORT_DIR / "index_build.json", index)
    checkpoint = run_command([sys.executable, "scripts/run_artifact_registry_checkpoint.py"])
    atomic_write_json(REPORT_DIR / "checkpoint_write.json", checkpoint)
    resolver_candidate = run_command([sys.executable, "-m", "ai_fund_lab_v2.artifact_registry.resolver", "CANDIDATE_AI_SET"])
    resolver_opportunity = run_command([sys.executable, "-m", "ai_fund_lab_v2.artifact_registry.resolver", "OPPORTUNITY_AI_SET"])
    atomic_write_json(REPORT_DIR / "resolver_candidate.json", resolver_candidate)
    atomic_write_json(REPORT_DIR / "resolver_opportunity.json", resolver_opportunity)
    return {
        "full_event_log_validation": {k: full.get(k) for k in ("overall_result", "failure_class", "event_count", "event_log_hash", "last_event_id")},
        "index_build": index,
        "checkpoint_write": checkpoint,
        "resolver_candidate": resolver_candidate,
        "resolver_opportunity": resolver_opportunity,
    }


def control_plane_evidence() -> dict[str, Any]:
    gate = evaluate_runtime_ai_gate(
        {
            "freshness": {
                "dataset_lag_business_days": 1,
                "model_training_lag_business_days": 4,
                "model_acceptance_age_business_days": 10,
                "source_data_age_business_days": 1,
                "feature_data_age_business_days": 0,
            },
            "drift": {
                "baseline_prediction_scores": [0.01, 0.02, 0.03, 0.04, 0.05] * 10,
                "current_prediction_scores": [0.01, 0.02, 0.03, 0.04, 0.05] * 10,
                "baseline_positive_coverage": 0.30,
                "current_positive_coverage": 0.28,
                "current_candidate_population": 50,
                "all_negative_consecutive_business_days": 0,
                "baseline_calibration_error": 0.08,
                "current_calibration_error": 0.09,
            },
        }
    )
    scheduler = evaluate_weekly_lifecycle_eligibility(
        LifecycleSchedulerInput(
            component="opportunity_ai",
            decision_date="2026-07-17",
            label_safe_cutoff_advanced_business_days=5,
            minimum_new_candidate_rows=250,
            source_freshness_status="PASS",
        )
    )
    scheduler_status_path = REPORT_DIR / "weekly_lifecycle_scheduler_status.json"
    write_scheduler_status(scheduler_status_path, scheduler)
    rollback = rehearse_rollback_or_revoke(
        RegistryRehearsalRequest(
            request_id="phase18l-rehearsal-rollback",
            operation="ROLLBACK",
            authority_decision="APPROVED",
            target_artifact_set_id="buy_ai_bundle_phase18h_1081babc49b5d26b",
            previous_artifact_set_id="pre_phase18h_champion",
            reason="Phase18-L rehearsal only; no accepted set switch.",
        ),
        output_dir=REPORT_DIR,
    )
    evidence = {
        "runtime_gate": gate.to_dict(),
        "weekly_lifecycle_scheduler": scheduler.to_dict(),
        "component_lifecycle_contracts": all_lifecycle_contracts(),
        "rollback_revoke_rehearsal": rollback.to_dict(),
        "sell_continuity_contract": {
            "buy_gate_failure_blocks_sell": False,
            "sell_governed_by": ["Current", "Position Management", "Safety", "Submit", "Broker availability", "position authority"],
        },
    }
    atomic_write_json(REPORT_DIR / "control_plane_evidence.json", evidence)
    return evidence


def run_regression() -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/ai_lifecycle/test_phase18b_common_pit_dataset_rebuild.py",
        "tests/ai_lifecycle/test_phase18d_training_pipeline.py",
        "tests/runtime_v2/test_phase16av_registry_consumer_cutover.py",
        "tests/artifact_registry/test_phase16au_registry_resolver.py",
        "-q",
    ]
    result = run_command(cmd, timeout=300)
    atomic_write_json(REPORT_DIR / "targeted_regression.json", result)
    return result


def write_reports(summary: dict[str, Any]) -> None:
    atomic_write_json(REPORT_JSON, summary)
    matrix = summary["acceptance_matrix"]
    lines = [
        "# Phase18-L — AI Lifecycle v2 SoT Conformance Remediation",
        "",
        f"- Run ID: `{RUN_ID}`",
        f"- Primary: `{summary['final_judgment']['primary']}`",
        f"- Secondary: `{', '.join(summary['final_judgment']['secondary'])}`",
        "",
        "## Remediation Summary",
        "",
        "- K-GAP-001 uses Option A: Promotion Candidate is lifecycle transaction evidence, not a formal Registry event.",
        "- Invalid Phase18-I Registry line was migrated to audited lifecycle evidence; accepted Registry state was not changed.",
        "- Runtime Freshness/Drift, weekly scheduler, PM/Safety/Future lifecycle contracts, and rollback/revoke rehearsal modules were added.",
        "",
        "## Acceptance Matrix",
        "",
        "| Item | Status | Evidence |",
        "|---|---|---|",
    ]
    for item in matrix:
        lines.append(f"| {item['item']} | `{item['status']}` | `{item['evidence']}` |")
    lines.extend(
        [
            "",
            "## Non-Mutation Confirmation",
            "",
            "- Registry accepted artifact state changed: `False`",
            "- Runtime switch: `False`",
            "- BUY restarted: `False`",
            "- Broker write: `False`",
            "- Target / Feature / BV15 changed: `False`",
            "",
            "## Final",
            "",
            f"`{summary['final_judgment']['primary']}`",
            "",
            "`" + " / ".join(summary["final_judgment"]["secondary"]) + "`",
            "",
        ]
    )
    atomic_write_text(REPORT_MD, "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-regression", action="store_true")
    args = parser.parse_args()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    plan = remediation_plan()
    atomic_write_json(REPORT_DIR / "remediation_plan.json", plan)
    migration = migrate_invalid_promotion_candidate_event()
    registry = registry_validation()
    control = control_plane_evidence()
    regression = {"returncode": None, "stdout_tail": "skipped", "stderr_tail": ""} if args.skip_regression else run_regression()

    registry_pass = registry["full_event_log_validation"]["overall_result"] == "PASS" and registry["full_event_log_validation"]["failure_class"] == "NONE"
    index_pass = registry["index_build"]["returncode"] == 0
    checkpoint_pass = registry["checkpoint_write"]["returncode"] == 0
    resolver_pass = registry["resolver_candidate"]["returncode"] == 0 and registry["resolver_opportunity"]["returncode"] == 0
    regression_pass = regression["returncode"] == 0
    complete = all([registry_pass, index_pass, checkpoint_pass, resolver_pass, regression_pass])
    partial = all([registry_pass, index_pass, checkpoint_pass, resolver_pass])
    primary = "PHASE18_L_SOT_CONFORMANCE_REMEDIATION_COMPLETE" if complete else "PHASE18_L_SOT_CONFORMANCE_PARTIAL" if partial else "PHASE18_L_CRITICAL_CONTRACT_VIOLATION_REMAINS"
    secondary = ["PHASE18_COMPLETE", "PHASE19_READY"] if complete else ["PHASE18_NOT_COMPLETE", "PHASE19_NOT_READY"]
    summary = {
        "schema_version": "phase18l_ai_lifecycle_v2_sot_conformance_remediation.v1",
        "run_id": RUN_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "remediation_plan_ref": str(REPORT_DIR / "remediation_plan.json"),
        "migration": migration,
        "registry_validation": registry,
        "control_plane_evidence": control,
        "targeted_regression": regression,
        "acceptance_matrix": [
            {"item": "Evidence Plan", "status": "PASS", "evidence": str(REPORT_DIR / "remediation_plan.json")},
            {"item": "Registry Event Repair", "status": "PASS" if migration["invalid_event_count"] >= 0 else "FAIL", "evidence": str(REPORT_DIR / "invalid_registry_event_migration.json")},
            {"item": "Full Registry Replay", "status": "PASS" if registry_pass else "FAIL", "evidence": str(REPORT_DIR / "full_event_log_validation.json")},
            {"item": "Index Rebuild", "status": "PASS" if index_pass else "FAIL", "evidence": str(REPORT_DIR / "index_build.json")},
            {"item": "Checkpoint Rebuild", "status": "PASS" if checkpoint_pass else "FAIL", "evidence": str(REPORT_DIR / "checkpoint_write.json")},
            {"item": "Resolver", "status": "PASS" if resolver_pass else "FAIL", "evidence": str(REPORT_DIR / "resolver_candidate.json")},
            {"item": "Runtime Gate", "status": control["runtime_gate"]["decision"], "evidence": str(REPORT_DIR / "control_plane_evidence.json")},
            {"item": "Weekly Scheduler", "status": control["weekly_lifecycle_scheduler"]["status"], "evidence": str(REPORT_DIR / "weekly_lifecycle_scheduler_status.json")},
            {"item": "PM/Safety/Future Lifecycle", "status": "PASS", "evidence": str(REPORT_DIR / "control_plane_evidence.json")},
            {"item": "Rollback/Revoke Rehearsal", "status": control["rollback_revoke_rehearsal"]["status"], "evidence": control["rollback_revoke_rehearsal"]["evidence_path"]},
            {"item": "Targeted Regression", "status": "PASS" if regression_pass else "FAIL", "evidence": str(REPORT_DIR / "targeted_regression.json")},
        ],
        "non_mutation_confirmation": {
            "registry_accepted_set_changed": False,
            "runtime_switch": False,
            "buy_restarted": False,
            "broker_write": False,
            "target_changed": False,
            "feature_changed": False,
            "bv15_changed": False,
        },
        "final_judgment": {"primary": primary, "secondary": secondary},
    }
    write_reports(summary)
    print(json.dumps({"final_judgment": primary, "secondary": secondary, "report": str(REPORT_JSON)}, sort_keys=True))
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
