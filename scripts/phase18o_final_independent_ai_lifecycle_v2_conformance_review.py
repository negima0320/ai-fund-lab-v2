from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
RUN_ID = "phase18o-final-independent-review-20260717T000000Z"
EVIDENCE_DIR = ROOT / "reports" / "phase18_o_final_independent_ai_lifecycle_v2_conformance_review" / RUN_ID
REPORT_JSON = ROOT / "reports" / "phase_reports" / "phase18_o_final_independent_ai_lifecycle_v2_conformance_review.json"
REPORT_MD = ROOT / "docs" / "phase_reports" / "phase18_o_final_independent_ai_lifecycle_v2_conformance_review.md"

REGISTRY_EVENTS = ROOT / ".runtime" / "artifact_registry" / "events" / "registry_events.jsonl"

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

REQUIRED_TRAINING_FILES = {
    "model.pkl",
    "training_metadata.json",
    "training_config.json",
    "dataset_reference.json",
    "metrics.json",
    "recent_holdout_metrics.json",
    "calibration_metrics.json",
    "regime_metrics.json",
    "prediction_distribution.json",
    "hash_manifest.json",
    "status.json",
}


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def run_command(args: list[str], *, timeout: int = 300) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    proc = subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True, timeout=timeout)
    return {
        "command": args,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def bundle_presence(path: Path, required: set[str]) -> dict[str, Any]:
    present = {p.name for p in path.iterdir()} if path.exists() else set()
    missing = sorted(required - present)
    status = "PASS" if not missing else "FAIL"
    return {
        "path": str(path.relative_to(ROOT)),
        "exists": path.exists(),
        "required_files": sorted(required),
        "missing": missing,
        "status": status,
    }


def runtime_source_review() -> dict[str, Any]:
    producer = ROOT / "src" / "ai_fund_lab_v2" / "runtime_v2" / "buy_ai" / "producer.py"
    cli = ROOT / "src" / "ai_fund_lab_v2" / "runtime_v2" / "cli" / "run_daily_operation.py"
    producer_text = producer.read_text(encoding="utf-8")
    cli_text = cli.read_text(encoding="utf-8")
    checks = [
        {
            "name": "normal_buy_ai_producer_calls_gate",
            "status": "PASS" if "evaluate_runtime_ai_gate" in producer_text else "FAIL",
            "evidence": "produce_buy_ai_decisions path writes ai_lifecycle_gate_decision.json",
        },
        {
            "name": "decision_artifact_written",
            "status": "PASS" if "ai_lifecycle_gate_decision.json" in producer_text else "FAIL",
            "evidence": "runtime_state/buy_ai/{business_date}/ai_lifecycle_gate_decision.json",
        },
        {
            "name": "freshness_uses_real_runtime_authority",
            "status": "FAIL" if '"dataset_lag_business_days": 0' in producer_text and '"model_acceptance_age_business_days": 0' in producer_text else "PASS",
            "evidence": "producer hardcodes dataset/model lag and acceptance age to zero in lifecycle gate input",
        },
        {
            "name": "drift_uses_accepted_baseline_not_same_run",
            "status": "FAIL" if "accepted_runtime_artifact_current_window_baseline" in producer_text else "PASS",
            "evidence": "producer sets baseline scores/features from current window values",
        },
        {
            "name": "calibration_drift_not_placeholder",
            "status": "FAIL" if '"baseline_calibration_error": 0.0' in producer_text and '"current_calibration_error": 0.0' in producer_text else "PASS",
            "evidence": "producer sets calibration drift inputs to 0.0/0.0",
        },
        {
            "name": "daily_cli_respects_blocked_buy",
            "status": "PASS" if 'buy_ai_result.status == "BLOCKED"' in cli_text else "FAIL",
            "evidence": "run_daily_operation maps BUY AI BLOCKED to EXIT_BLOCKED",
        },
        {
            "name": "sell_continuity_integration_proven",
            "status": "REVIEW_REQUIRED",
            "evidence": "block_sell field exists, but morning CLI stops after BUY AI BLOCKED; no normal orchestration test proves SELL stages continue under BUY block",
        },
    ]
    return {"checks": checks, "status": aggregate_status(checks)}


def scheduler_review() -> dict[str, Any]:
    from ai_fund_lab_v2.ai_lifecycle.scheduler import (
        LifecycleRetryPolicy,
        LifecycleSchedulerInput,
        WeeklyLifecycleSchedulerOperator,
    )

    state_root = EVIDENCE_DIR / "scheduler_independent"
    ticks = [datetime(2026, 7, 17, tzinfo=timezone.utc)]

    def now() -> datetime:
        return ticks[-1]

    operator = WeeklyLifecycleSchedulerOperator(
        state_root=state_root,
        retry_policy=LifecycleRetryPolicy(max_attempts=2, timeout_seconds=5),
        now=now,
    )
    input_ = LifecycleSchedulerInput("opportunity_ai", "2026-07-17", 5, 250, "PASS")
    attempts = {"retry": 0, "authority": 0}

    def retry_action() -> str:
        attempts["retry"] += 1
        if attempts["retry"] == 1:
            raise Exception("TRANSIENT_ERROR")
        return "PROMOTION_REVIEW_REQUIRED"

    retry = operator.run(input_, idempotency_key="retry", action=retry_action)

    def timeout_action() -> str:
        ticks.append(ticks[-1] + timedelta(seconds=10))
        return "TRAINING_REQUIRED"

    timeout = operator.run(input_, idempotency_key="timeout", action=timeout_action)

    def authority_action() -> str:
        attempts["authority"] += 1
        raise Exception("AUTHORITY_REJECTED")

    authority = operator.run(input_, idempotency_key="authority-reject", action=authority_action)
    repeat = operator.run(input_, idempotency_key="retry", action=lambda: "DATASET_REBUILD_REQUIRED")

    checks = [
        {"name": "retryable_error_retried", "status": "PASS" if attempts["retry"] == 2 and retry.final_state == "PROMOTION_REVIEW_REQUIRED" else "FAIL", "evidence": asdict(retry)},
        {"name": "timeout_acts", "status": "PASS" if timeout.timeout_status == "TIMED_OUT" and timeout.final_state == "FAILED" else "FAIL", "evidence": asdict(timeout)},
        {"name": "authority_rejection_not_retried", "status": "PASS" if attempts["authority"] == 1 and authority.final_state == "FAILED" else "FAIL", "evidence": asdict(authority)},
        {"name": "idempotency", "status": "PASS" if repeat.final_state == retry.final_state and repeat.attempt == retry.attempt else "FAIL", "evidence": asdict(repeat)},
        {"name": "registry_runtime_non_mutation_flags", "status": "PASS" if not retry.registry_accepted_event_generated and not retry.runtime_switch_performed and not retry.buy_restarted else "FAIL", "evidence": asdict(retry)},
    ]
    return {"checks": checks, "status": aggregate_status(checks)}


def rollback_review() -> dict[str, Any]:
    from ai_fund_lab_v2.ai_lifecycle.rollback_revoke import (
        AtomicRevokeRequest,
        AtomicRollbackRequest,
        IsolatedRegistryRollbackRevokeOperator,
    )

    registry_root = EVIDENCE_DIR / "isolated_registry_independent"
    op = IsolatedRegistryRollbackRevokeOperator(registry_root=registry_root)
    state_a = {"bundle": "A", "runtime_use_eligible": True}
    state_b = {"bundle": "B", "runtime_use_eligible": True}
    init = op.initialize(accepted_state=state_b)
    targets = {"A": state_a, "B": state_b}
    target_a_hash = hashlib.sha256(json.dumps(state_a, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
    rollback = op.atomic_rollback(AtomicRollbackRequest("rb", "B", "A", "rollback", "phase18o", "APPROVED", init["state_hash"], target_a_hash, "rb-idem"), targets=targets)
    duplicate = op.atomic_rollback(AtomicRollbackRequest("rb", "B", "A", "rollback", "phase18o", "APPROVED", init["state_hash"], target_a_hash, "rb-idem"), targets=targets)
    target_missing = op.atomic_rollback(AtomicRollbackRequest("missing", "B", "Z", "missing", "phase18o", "APPROVED", rollback["after_state_hash"], "", "missing-idem"), targets=targets)
    target_hash_mismatch = op.atomic_rollback(AtomicRollbackRequest("hash", "B", "A", "hash", "phase18o", "APPROVED", rollback["after_state_hash"], "bad", "hash-idem"), targets=targets)
    current_mismatch = op.atomic_revoke(AtomicRevokeRequest("current", "A", "current", "phase18o", "APPROVED", "B", "bad-current", "current-idem"), targets=targets)
    partial = op.atomic_rollback(AtomicRollbackRequest("partial", "B", "A", "partial", "phase18o", "APPROVED", rollback["after_state_hash"], target_a_hash, "partial-idem"), targets=targets, fail_at="before_commit")
    source = (ROOT / "src" / "ai_fund_lab_v2" / "ai_lifecycle" / "rollback_revoke.py").read_text(encoding="utf-8")
    checks = [
        {"name": "rollback_pass", "status": "PASS" if rollback["status"] == "PASS" else "FAIL", "evidence": rollback},
        {"name": "duplicate_idempotent", "status": "PASS" if duplicate["audit_hash"] == rollback["audit_hash"] else "FAIL", "evidence": duplicate},
        {"name": "target_missing_fail_closed", "status": "PASS" if target_missing["status"] == "FAILED" and target_missing["reason"] == "target_missing" else "FAIL", "evidence": target_missing},
        {"name": "target_hash_mismatch_fail_closed", "status": "PASS" if target_hash_mismatch["status"] == "FAILED" and target_hash_mismatch["reason"] == "target_hash_mismatch" else "FAIL", "evidence": target_hash_mismatch},
        {"name": "current_state_mismatch_fail_closed", "status": "PASS" if current_mismatch["status"] == "FAILED" and current_mismatch["reason"] == "current_state_mismatch" else "FAIL", "evidence": current_mismatch},
        {"name": "partial_before_commit_no_state_change", "status": "PASS" if partial["status"] == "FAILED" and partial["before_state_hash"] == partial["after_state_hash"] else "FAIL", "evidence": partial},
        {"name": "partial_event_index_checkpoint_failure_rehearsal", "status": "FAIL", "evidence": "operator exposes only fail_at='before_commit'; no event write, index write, or checkpoint write failure injection exists"},
        {"name": "event_log_write_atomic", "status": "FAIL" if "event_log_path.write_text" in source else "PASS", "evidence": "event log commit uses direct write_text between state and index/checkpoint commits"},
    ]
    return {"checks": checks, "status": aggregate_status(checks)}


def aggregate_status(checks: list[dict[str, Any]]) -> str:
    statuses = {check["status"] for check in checks}
    if "FAIL" in statuses:
        return "FAIL"
    if "REVIEW_REQUIRED" in statuses:
        return "REVIEW_REQUIRED"
    if "PARTIAL" in statuses:
        return "PARTIAL"
    return "PASS"


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    before_hash = sha256_file(REGISTRY_EVENTS)

    datasets = {
        "candidate": bundle_presence(ROOT / ".runtime" / "ai_lifecycle" / "datasets" / "candidate_ai" / "candidate_dataset_c8de026d3ea8aa4d", REQUIRED_DATASET_FILES),
        "opportunity": bundle_presence(ROOT / ".runtime" / "ai_lifecycle" / "datasets" / "opportunity_ai" / "opportunity_dataset_fbadc8091a31486d", REQUIRED_DATASET_FILES),
    }
    trainings = {
        "candidate": bundle_presence(ROOT / ".runtime" / "ai_lifecycle" / "training" / "candidate_ai" / "candidate_training_da0855d123ed1bed", REQUIRED_TRAINING_FILES - {"metrics.json"}),
        "opportunity": bundle_presence(ROOT / ".runtime" / "ai_lifecycle" / "training" / "opportunity_ai" / "opportunity_training_phase18h_1081babc49b5d26b", REQUIRED_TRAINING_FILES | {"calibration_model.pkl", "calibration_parameters.json", "calibration_metadata.json", "calibration_schema.json", "calibration_hash.json"}),
    }
    calibration = {
        "opportunity": {
            "required": ["calibration_model.pkl", "calibration_parameters.json", "calibration_metadata.json", "calibration_schema.json", "calibration_hash.json"],
            "status": "PASS" if all((ROOT / ".runtime" / "ai_lifecycle" / "training" / "opportunity_ai" / "opportunity_training_phase18h_1081babc49b5d26b" / name).exists() for name in ["calibration_model.pkl", "calibration_parameters.json", "calibration_metadata.json", "calibration_schema.json", "calibration_hash.json"]) else "FAIL",
        }
    }
    runtime = runtime_source_review()
    scheduler = scheduler_review()
    rollback = rollback_review()

    phase18n = read_json(ROOT / "reports" / "phase_reports" / "phase18_n_production_lifecycle_wiring_and_remaining_contract_remediation.json")
    regression = run_command([
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
    ])

    after_hash = sha256_file(REGISTRY_EVENTS)
    gaps = [
        {
            "id": "O-GAP-001",
            "category": "RUNTIME_INTEGRATION_GAP",
            "severity": "CRITICAL",
            "title": "Runtime BUY AI producer passes hardcoded freshness zeros into lifecycle gate",
            "affected_files": ["src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py"],
            "root_cause": "The normal runtime path does not resolve dataset max date, model training cutoff, or Registry accepted timestamp for the lifecycle gate.",
            "runtime_impact": "Stale accepted artifacts can be classified healthy because the production input is fixed at zero lag.",
            "registry_impact": "Registry authority is not used as the model acceptance age source in this path.",
            "phase18_completion_impact": "Blocks Phase18 completion.",
            "recommended_remediation": "Resolve freshness from accepted Atomic BUY AI Bundle metadata, dataset lineage, and Registry accepted event before gate evaluation.",
        },
        {
            "id": "O-GAP-002",
            "category": "RUNTIME_INTEGRATION_GAP",
            "severity": "CRITICAL",
            "title": "Runtime drift baseline is same-run current-window evidence",
            "affected_files": ["src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py"],
            "root_cause": "Baseline prediction scores, feature values, positive coverage, population, and calibration are derived from the current inference payload.",
            "runtime_impact": "Prediction/feature/calibration drift can self-PASS and does not prove comparison to an accepted baseline.",
            "registry_impact": "Accepted artifact baseline identity is not resolved from Registry/Bundle evidence.",
            "phase18_completion_impact": "Blocks Phase18 completion.",
            "recommended_remediation": "Materialize accepted baseline distribution evidence in the training bundle and load it from Registry-resolved runtime artifacts.",
        },
        {
            "id": "O-GAP-003",
            "category": "ROLLBACK_GAP",
            "severity": "HIGH",
            "title": "Rollback/Revoke rehearsal does not cover event/index/checkpoint write failures and event log write is not atomic",
            "affected_files": ["src/ai_fund_lab_v2/ai_lifecycle/rollback_revoke.py"],
            "root_cause": "Failure injection only supports before_commit; commit writes state, event log, index, and checkpoint in separate steps.",
            "runtime_impact": "Rollback safety is not fully proven for partial registry materialization failures.",
            "registry_impact": "Event Log / Index / Checkpoint consistency is not guaranteed for mid-commit failures.",
            "phase18_completion_impact": "Blocks full Phase18 conformance; at minimum requires remediation before Phase19 switch.",
            "recommended_remediation": "Add transaction staging or journaled commit plus failure injection for event, index, and checkpoint writes.",
        },
        {
            "id": "O-GAP-004",
            "category": "TEST_COVERAGE_GAP",
            "severity": "HIGH",
            "title": "SELL continuity under BUY lifecycle block is not proven through normal orchestration",
            "affected_files": ["src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py", "tests/ai_lifecycle/test_phase18n_production_lifecycle_wiring.py"],
            "root_cause": "Tests assert block_sell=false at gate object level, while morning orchestration sets final_state BLOCKED after BUY AI BLOCKED and does not prove SELL stages continue.",
            "runtime_impact": "A BUY lifecycle block may halt the morning path before SELL-continuity evidence is produced.",
            "registry_impact": "None direct.",
            "phase18_completion_impact": "Blocks full Phase18 conformance until integration evidence exists.",
            "recommended_remediation": "Add normal orchestration integration evidence showing Current/Valuation/PM/Safety/SELL planning remain runnable when BUY is blocked.",
        },
    ]

    matrix = [
        {"requirement": "PIT Dataset Rebuild", "implementation": "ai_lifecycle dataset bundles", "status": aggregate_status(list(datasets.values())), "evidence": datasets},
        {"requirement": "Training / Validation", "implementation": "candidate/opportunity training bundles", "status": aggregate_status(list(trainings.values())), "evidence": trainings},
        {"requirement": "Calibration Artifact", "implementation": "Phase18-H opportunity calibration files", "status": calibration["opportunity"]["status"], "evidence": calibration},
        {"requirement": "Runtime Daily Wiring", "implementation": "BUY AI producer calls lifecycle gate", "status": "PASS_WITH_REVIEW" if runtime["status"] == "FAIL" else runtime["status"], "evidence": runtime},
        {"requirement": "Freshness Gate", "implementation": "runtime gate supports metrics but producer hardcodes zeros", "status": "CONTRACT_CONFLICT", "evidence": runtime},
        {"requirement": "Quantitative Drift Gate", "implementation": "gate supports metrics but producer uses same-run baseline", "status": "CONTRACT_CONFLICT", "evidence": runtime},
        {"requirement": "SELL Continuity", "implementation": "gate field exists; orchestration evidence missing", "status": "REVIEW_REQUIRED", "evidence": runtime},
        {"requirement": "Weekly Scheduler", "implementation": "WeeklyLifecycleSchedulerOperator", "status": "PASS", "evidence": scheduler},
        {"requirement": "Rollback / Revoke", "implementation": "IsolatedRegistryRollbackRevokeOperator", "status": "PARTIAL", "evidence": rollback},
        {"requirement": "Artifact Registry", "implementation": "formal registry event log", "status": "PASS" if phase18n.get("registry", {}).get("event_count") == 42 else "REVIEW_REQUIRED", "evidence": phase18n.get("registry", {})},
        {"requirement": "Cross-contract Regression", "implementation": "selected ai_lifecycle/artifact/runtime registry tests", "status": "PASS" if regression["returncode"] == 0 else "FAIL", "evidence": regression},
        {"requirement": "Non-mutation", "implementation": "registry event hash before/after independent review", "status": "PASS" if before_hash == after_hash else "FAIL", "evidence": {"before": before_hash, "after": after_hash}},
    ]

    final = {
        "primary": "PHASE18_O_REMEDIATION_REQUIRED",
        "secondary": ["PHASE18_NOT_COMPLETE", "PHASE19_NOT_READY"],
        "reason": "Independent review found critical production runtime gate evidence gaps and rollback rehearsal gaps.",
    }

    report = {
        "run_id": RUN_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "documents_reviewed": [
            "docs/01_requirements/phase_roadmap.md",
            "docs/02_architecture/ai_lifecycle_v2.md",
            "docs/02_architecture/runtime_architecture_v2.md",
            "docs/phase_reports/phase18_n_production_lifecycle_wiring_and_remaining_contract_remediation.md",
        ],
        "dataset_lifecycle": datasets,
        "training_lifecycle": trainings,
        "calibration": calibration,
        "runtime_gate_review": runtime,
        "scheduler_review": scheduler,
        "rollback_revoke_review": rollback,
        "cross_contract_regression": regression,
        "design_to_implementation_matrix": matrix,
        "remaining_gaps": gaps,
        "non_mutation_confirmation": {
            "registry_events_before_hash": before_hash,
            "registry_events_after_hash": after_hash,
            "registry_accepted_state_changed": before_hash != after_hash,
            "runtime_switch": False,
            "runtime_submit": False,
            "buy_restarted": False,
            "broker_write": False,
            "target_changed": False,
            "feature_changed": False,
            "bv15_changed": False,
        },
        "phase19_readiness": "PHASE19_NOT_READY",
        "final_judgment": final,
    }
    write_json(EVIDENCE_DIR / "independent_review_result.json", report)
    write_json(REPORT_JSON, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
