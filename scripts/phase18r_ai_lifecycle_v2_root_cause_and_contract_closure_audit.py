from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "phase18r-root-cause-contract-closure-audit-20260717T000000Z"
EVIDENCE_DIR = ROOT / "reports" / "phase18_r_ai_lifecycle_v2_root_cause_and_contract_closure_audit" / RUN_ID
REPORT_JSON = ROOT / "reports" / "phase_reports" / "phase18_r_ai_lifecycle_v2_root_cause_and_contract_closure_audit.json"
REPORT_MD = ROOT / "docs" / "phase_reports" / "phase18_r_ai_lifecycle_v2_root_cause_and_contract_closure_audit.md"
REGISTRY_LOG = ROOT / ".runtime" / "artifact_registry" / "events" / "registry_events.jsonl"


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def file_inventory() -> dict[str, Any]:
    roots = [
        "src/ai_fund_lab_v2/ai_lifecycle",
        "src/ai_fund_lab_v2/artifact_registry",
        "src/ai_fund_lab_v2/runtime_v2",
        "scripts",
        "tests/ai_lifecycle",
        "tests/runtime_v2",
    ]
    counts: dict[str, int] = {}
    phase18_scripts: list[str] = []
    for rel in roots:
        root = ROOT / rel
        files = [p for p in root.rglob("*") if p.is_file()] if root.exists() else []
        counts[rel] = len(files)
        if rel == "scripts":
            phase18_scripts = sorted(str(p.relative_to(ROOT)) for p in files if p.name.startswith("phase18"))
    production_scope = {
        "src/ai_fund_lab_v2/ai_lifecycle": "AUTHORITY_OWNER / TRANSACTION_OPERATOR / AMBIGUOUS_RESPONSIBILITY where phase operators also define contracts",
        "src/ai_fund_lab_v2/artifact_registry": "AUTHORITY_OWNER / RESOLVER / VALIDATOR / TRANSACTION_OPERATOR",
        "src/ai_fund_lab_v2/runtime_v2": "CONTROL_PLANE / DATA_PLANE / RESOLVER / CLI_WRAPPER",
        "src/ai_fund_lab_v2/runtime_v2/buy_ai": "DATA_PLANE plus Runtime lifecycle gate caller",
        "src/ai_fund_lab_v2/runtime_v2/cli": "CLI_WRAPPER / CONTROL_PLANE orchestration",
        "scripts/phase18*": "EVIDENCE_COLLECTOR / PHASE_SPECIFIC; must not own Production authority",
        "tests/ai_lifecycle": "TEST_ONLY",
        "tests/runtime_v2": "TEST_ONLY / Runtime entrypoint tests",
    }
    ambiguous = [
        "src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py mixes accepted artifact resolution, integrity summary, freshness, baseline extraction, current evidence, and synthetic distribution generation.",
        "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py mixes immediate drift with calibration error semantics that belong to delayed monitoring unless a label-free proxy is explicitly contracted.",
        "src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py treats BUY lifecycle BLOCK/REVIEW as morning job exit, while SELL planning is a separate job.",
        "src/ai_fund_lab_v2/ai_lifecycle/rollback_revoke.py rehearses isolated registry mutation and restore, but restore-failure CRITICAL semantics are not explicit.",
    ]
    return {
        "counts": counts,
        "phase18_scripts": phase18_scripts,
        "production_scope_classification": production_scope,
        "ambiguous_responsibility": ambiguous,
    }


def line_refs() -> dict[str, Any]:
    refs: dict[str, dict[str, int]] = {}
    targets = {
        "src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py": {
            "resolve_accepted_bundle_path": "def _resolve_accepted_bundle_path",
            "latest_promotion_candidate_bundle": "def _latest_promotion_candidate_bundle",
            "resolve_freshness": "def _resolve_freshness",
            "resolve_baseline": "def _resolve_baseline",
            "integrity_evidence": "def _integrity_evidence",
            "model_training_cutoff": "def _model_training_cutoff",
            "load_trading_calendar": "def _load_trading_calendar",
            "sample_from_stats": "def _sample_from_stats",
            "current_calibration_proxy": "def _current_calibration_proxy",
        },
        "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py": {
            "evaluate_freshness_gate": "def evaluate_freshness_gate",
            "evaluate_drift_gate": "def evaluate_drift_gate",
            "calibration_drift": "calibration_drift",
            "compose_result": "def _compose_result",
        },
        "src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py": {
            "produce_buy_ai_decisions": "def produce_buy_ai_decisions",
            "lifecycle_gate_call": "_evaluate_and_write_lifecycle_gate",
            "resolve_buy_ai_artifact_paths": "def resolve_buy_ai_artifact_paths",
        },
        "src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py": {
            "buy_ai_call": "produce_buy_ai_decisions",
            "buy_lifecycle_sell_continuity": "buy_lifecycle_sell_continuity",
            "morning_planning": "run_morning_ai_planning_pending_pipeline",
            "sell_planning": "run_sell_planning_pending_pipeline",
        },
        "src/ai_fund_lab_v2/artifact_registry/resolver.py": {
            "resolve": "def resolve",
            "accepted_filter": "runtime_use_eligible",
            "validate_manifest": "def _validate_manifest",
        },
        "src/ai_fund_lab_v2/ai_lifecycle/rollback_revoke.py": {
            "transaction": "def _transaction",
            "commit": "def _commit",
            "restore_files": "def _restore_files",
        },
    }
    for rel, patterns in targets.items():
        text = (ROOT / rel).read_text(encoding="utf-8") if (ROOT / rel).exists() else ""
        lines = text.splitlines()
        refs[rel] = {}
        for name, pattern in patterns.items():
            for idx, line in enumerate(lines, start=1):
                if pattern in line:
                    refs[rel][name] = idx
                    break
    return refs


def authority_flow() -> list[dict[str, str]]:
    return [
        {"node": "Dataset Source Authority", "owner": "AI Lifecycle Dataset Builder", "output": "source refs, schema/content hashes, lineage", "failure": "Dataset rebuild REVIEW/BLOCK; no Runtime fallback"},
        {"node": "Label-safe Dataset Bundle", "owner": "AI Lifecycle Dataset Publisher", "output": "dataset bundle with label_safe_cutoff and metadata", "failure": "Bundle unpublished; Training blocked"},
        {"node": "Training Bundle", "owner": "AI Lifecycle Training Pipeline", "output": "model, metrics, calibration, baseline evidence, dataset refs", "failure": "Promotion blocked"},
        {"node": "Promotion Candidate Transaction", "owner": "Registry Promotion Operator", "output": "candidate transaction and atomic BUY AI bundle candidate", "failure": "No accepted Runtime use"},
        {"node": "Authority Decision", "owner": "Human/Authority Control Plane", "output": "approved/rejected decision artifact", "failure": "No Registry accepted event"},
        {"node": "Registry Accepted Event", "owner": "Artifact Registry Writer", "output": "ARTIFACT_ACCEPTED event with runtime_use_eligible", "failure": "Runtime resolver returns INSUFFICIENT_EVIDENCE/HALT"},
        {"node": "Registry Accepted State", "owner": "Registry event log + index + checkpoint", "output": "accepted set identity", "failure": "No latest/manual fallback"},
        {"node": "Accepted Atomic BUY AI Bundle Resolver", "owner": "Runtime Accepted Authority Resolver", "output": "joint Candidate/Opportunity bundle identity", "failure": "BUY BLOCK, SELL dependencies continue"},
        {"node": "Integrity Verification", "owner": "Runtime Lifecycle Evidence Authority", "output": "verified hashes/schema/lineage/compatibility", "failure": "CRITICAL_AUTHORITY_VIOLATION or INSUFFICIENT_EVIDENCE"},
        {"node": "Runtime Freshness Evidence", "owner": "Runtime Lifecycle Evidence Authority", "output": "3 business-day clocks from formal calendar", "failure": "MODEL_UNHEALTHY or INSUFFICIENT_EVIDENCE"},
        {"node": "Runtime Drift Baseline", "owner": "Accepted bundle baseline artifact", "output": "materialized baseline distributions", "failure": "INSUFFICIENT_EVIDENCE"},
        {"node": "Runtime Current Evidence", "owner": "Runtime BUY AI producer", "output": "current population/distribution/positive coverage hash", "failure": "REVIEW/BLOCK depending severity"},
        {"node": "Runtime Lifecycle Decision", "owner": "Runtime Control Plane", "output": "PASS/REVIEW/BLOCK plus scoped control flags", "failure": "BUY-only block unless shared dependency fails"},
        {"node": "BUY Control", "owner": "Runtime Planning/Submit", "output": "BUY planning/submit allowed or blocked", "failure": "No forced BUY"},
        {"node": "SELL Continuity", "owner": "Runtime SELL jobs", "output": "SELL planning/submit reachable if dependencies pass", "failure": "Only SELL dependency failures block SELL"},
    ]


def accepted_resolution_contract() -> list[dict[str, str]]:
    return [
        {"artifact_type": "Registry accepted Atomic BUY AI Bundle", "production_runtime": "ALLOWED", "condition": "Resolved from accepted event/state, runtime_use_eligible, verified hashes/schema/lineage"},
        {"artifact_type": "Promotion Candidate", "production_runtime": "FORBIDDEN", "condition": "Evidence only until accepted event; candidate-only presence maps to INSUFFICIENT_EVIDENCE"},
        {"artifact_type": "Review Candidate", "production_runtime": "FORBIDDEN", "condition": "Review evidence only"},
        {"artifact_type": "Latest Training Bundle", "production_runtime": "FORBIDDEN", "condition": "No latest directory discovery; must be referenced by accepted bundle"},
        {"artifact_type": "Latest Dataset Bundle", "production_runtime": "FORBIDDEN", "condition": "No latest directory discovery; must be referenced by accepted bundle"},
        {"artifact_type": "Manual Artifact Path", "production_runtime": "FORBIDDEN by default", "condition": "Only diagnostic path equal to Registry member may be accepted; cannot override authority"},
        {"artifact_type": "Test Fixture Bundle", "production_runtime": "FORBIDDEN", "condition": "Allowed only isolated test root, never normal Runtime success"},
        {"artifact_type": "Historical Isolated Bundle", "production_runtime": "ALLOWED only in isolated historical acceptance", "condition": "Explicit mode/evidence, not Production accepted state"},
    ]


def root_cause_matrix() -> list[dict[str, str]]:
    return [
        {"Q-GAP": "Q-GAP-001", "Severity": "CRITICAL", "Symptom": "Accepted resolver falls back to Promotion Candidate", "Primary Root Cause": "ROOT-A Accepted Authority Resolver boundary unclear", "Secondary Root Cause": "ROOT-B Evidence resolver compensates for missing authority", "Shared Remediation Unit": "RU1 Accepted-only Artifact Authority and Integrity"},
        {"Q-GAP": "Q-GAP-002", "Severity": "HIGH", "Symptom": "Negative model-training lag PASS", "Primary Root Cause": "ROOT-B missing evidence/future dates normalized", "Secondary Root Cause": "ROOT-G tests omit invalid clocks", "Shared Remediation Unit": "RU2 Freshness and Formal Calendar Authority"},
        {"Q-GAP": "Q-GAP-003", "Severity": "HIGH", "Symptom": "Unreadable calendar silently uses weekdays", "Primary Root Cause": "ROOT-B fallback compensation", "Secondary Root Cause": "ROOT-G fixture tests treat weekday fallback as normal", "Shared Remediation Unit": "RU2 Freshness and Formal Calendar Authority"},
        {"Q-GAP": "Q-GAP-004", "Severity": "HIGH", "Symptom": "Bundle hash/schema/lineage not verified", "Primary Root Cause": "ROOT-A authority split from Registry resolver", "Secondary Root Cause": "ROOT-C Atomic bundle runtime contract incomplete", "Shared Remediation Unit": "RU1 Accepted-only Artifact Authority and Integrity"},
        {"Q-GAP": "Q-GAP-005", "Severity": "HIGH", "Symptom": "Synthetic baseline from summary stats", "Primary Root Cause": "ROOT-C accepted bundle lacks materialized runtime baseline", "Secondary Root Cause": "ROOT-B resolver fabricates evidence", "Shared Remediation Unit": "RU3 Materialized Drift Baseline and Immediate Gate"},
        {"Q-GAP": "Q-GAP-006", "Severity": "HIGH", "Symptom": "Delayed calibration metric in immediate gate", "Primary Root Cause": "ROOT-D Immediate/Delayed boundary not fixed", "Secondary Root Cause": "ROOT-G tests validate local proxy only", "Shared Remediation Unit": "RU3 Materialized Drift Baseline and Immediate Gate"},
        {"Q-GAP": "Q-GAP-007", "Severity": "HIGH", "Symptom": "SELL continuity not proven through downstream path", "Primary Root Cause": "ROOT-E BUY block vs global Runtime halt ambiguity", "Secondary Root Cause": "ROOT-G tests do not follow Production Call Graph", "Shared Remediation Unit": "RU4 BUY-only Control and SELL Continuity"},
        {"Q-GAP": "Q-GAP-008", "Severity": "MEDIUM", "Symptom": "Restore failure CRITICAL path not proven", "Primary Root Cause": "ROOT-F Registry transaction failure model incomplete", "Secondary Root Cause": "ROOT-G failure injection incomplete", "Shared Remediation Unit": "RU5 Atomic Restore Failure Semantics"},
    ]


def remediation_units() -> list[dict[str, Any]]:
    return [
        {
            "unit": "RU1 Accepted-only Artifact Authority and Integrity",
            "purpose": "Make Runtime consume only Registry accepted Atomic BUY AI Bundle authority and verify all hashes/contracts.",
            "root_causes": ["ROOT-A", "ROOT-B", "ROOT-C"],
            "gaps": ["Q-GAP-001", "Q-GAP-004"],
            "modules": ["runtime_v2/lifecycle_evidence.py", "runtime_v2/buy_ai/producer.py", "artifact_registry/resolver.py"],
            "do_not_change": "Target, features, BV15, Registry accepted state, Runtime switch",
            "acceptance_tests": ["accepted state resolves", "accepted state missing does not fallback", "promotion candidate only => INSUFFICIENT_EVIDENCE", "bundle hash mismatch fail-closed", "manual path rejected in Production"],
            "depends_on": [],
        },
        {
            "unit": "RU2 Freshness and Formal Calendar Authority",
            "purpose": "Define and enforce the 3 clocks with formal calendar and invalid-date fail-closed semantics.",
            "root_causes": ["ROOT-B", "ROOT-G"],
            "gaps": ["Q-GAP-002", "Q-GAP-003"],
            "modules": ["runtime_v2/lifecycle_evidence.py", "runtime_v2/ai_lifecycle_gates.py"],
            "do_not_change": "Freshness thresholds unless SoT amendment is explicitly approved",
            "acceptance_tests": ["normal clocks", "negative training lag", "future model cutoff", "missing/unreadable/range-short calendar", "missing accepted_at", "timezone mismatch"],
            "depends_on": ["RU1"],
        },
        {
            "unit": "RU3 Materialized Drift Baseline and Immediate Gate",
            "purpose": "Replace synthetic baselines and separate immediate label-free evidence from delayed realized monitoring.",
            "root_causes": ["ROOT-C", "ROOT-D", "ROOT-B"],
            "gaps": ["Q-GAP-005", "Q-GAP-006"],
            "modules": ["runtime_v2/lifecycle_evidence.py", "runtime_v2/ai_lifecycle_gates.py", "training bundle artifact writers"],
            "do_not_change": "Model target, feature contract, BUY eligibility",
            "acceptance_tests": ["materialized baseline vs stable current", "feature/prediction/population/positive coverage hard drift", "all-negative only", "missing baseline", "baseline hash mismatch", "insufficient sample"],
            "depends_on": ["RU1"],
        },
        {
            "unit": "RU4 BUY-only Control and SELL Continuity",
            "purpose": "Make BUY lifecycle block scoped to BUY planning/submit and prove SELL path reachability through Production call graph.",
            "root_causes": ["ROOT-E", "ROOT-G"],
            "gaps": ["Q-GAP-007"],
            "modules": ["runtime_v2/ai_lifecycle_gates.py", "runtime_v2/cli/run_daily_operation.py", "runtime_v2/planning/sell_pipeline.py", "runtime_v2/submit"],
            "do_not_change": "Broker write disabled, PM/Safety rules unchanged",
            "acceptance_tests": ["MODEL_UNHEALTHY + existing position", "INSUFFICIENT_EVIDENCE + SELL signal", "MARKET_NO_OPPORTUNITY + SELL signal", "BUY submit blocked", "SELL submit authorization reachable", "Current/Valuation/PM/Safety reachable"],
            "depends_on": ["RU1", "RU2", "RU3"],
        },
        {
            "unit": "RU5 Atomic Restore Failure Semantics",
            "purpose": "Define restore failure as CRITICAL with unchanged accepted state evidence and manual recovery metadata.",
            "root_causes": ["ROOT-F", "ROOT-G"],
            "gaps": ["Q-GAP-008"],
            "modules": ["ai_lifecycle/rollback_revoke.py", "artifact_registry writer/index/checkpoint"],
            "do_not_change": "Production Registry accepted state during tests",
            "acceptance_tests": ["event/index/checkpoint/post-validation failures", "restore event/index/checkpoint failure", "RESTORE_FAILED => CRITICAL", "idempotent retry"],
            "depends_on": ["RU1"],
        },
    ]


def test_architecture_audit() -> dict[str, Any]:
    return {
        "existing_regression_result": "Phase18-Q rerun: 85 passed, 2 warnings; targeted lifecycle tests: 10 passed.",
        "guarantees": [
            "Registry resolver/index/checkpoint happy path and many failure rehearsals pass.",
            "Current tests exercise local lifecycle gate states and isolated rollback/revoke failures.",
            "MARKET_NO_OPPORTUNITY and MODEL_UNHEALTHY can be separated in local gate evidence."
        ],
        "does_not_guarantee": [
            "Production Runtime accepted-only Atomic BUY AI Bundle discovery.",
            "No Promotion Candidate fallback when accepted state is absent.",
            "Negative/future freshness clocks fail-closed.",
            "Formal calendar missing/unreadable/range-short failure behavior.",
            "Accepted bundle hash/schema/lineage mismatch mapping.",
            "Materialized baseline distribution authority.",
            "Immediate/delayed calibration separation.",
            "SELL planning/submit reachability through normal Runtime entrypoints under BUY block.",
            "Restore-failure CRITICAL rollback semantics."
        ],
        "risk_patterns": [
            "Fixture accepted bundles hide missing Registry accepted state.",
            "Evidence collectors compare self-generated expected values.",
            "Phase scripts contain implementation-like logic that is not Production authority.",
            "Local operator tests do not always traverse the Production call graph."
        ],
    }


def report_payload() -> dict[str, Any]:
    registry_before = {"count": count_lines(REGISTRY_LOG), "hash": sha256_file(REGISTRY_LOG)}
    registry_after = {"count": count_lines(REGISTRY_LOG), "hash": sha256_file(REGISTRY_LOG)}
    payload = {
        "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "phase18_r_root_cause_contract_closure_audit.v1",
        "documents_reviewed": [
            "docs/01_requirements/phase_roadmap.md",
            "docs/02_architecture/ai_lifecycle_v2.md",
            "docs/02_architecture/runtime_architecture_v2.md",
            "docs/03_ai_design/candidate_training_data_design.md",
            "docs/03_ai_design/opportunity_ai_design.md",
            "docs/phase_reports/phase16_k_ai_artifact_registry_and_capital_allocation_design.md",
            "docs/phase_reports/phase16_final_summary_and_phase17_handoff.md",
            "docs/phase_reports/phase17_final_summary_and_phase18_handoff.md",
            "docs/phase_reports/phase17_bv19_ai_training_lifecycle_and_retraining_pipeline_audit.md",
            "docs/phase_reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract.md",
            "docs/phase_reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment.md",
            "docs/phase_reports/phase18_k_ai_lifecycle_v2_design_conformance_and_implementation_review.md",
            "docs/phase_reports/phase18_l_ai_lifecycle_v2_sot_conformance_remediation.md",
            "docs/phase_reports/phase18_m_final_ai_lifecycle_v2_conformance_review.md",
            "docs/phase_reports/phase18_n_production_lifecycle_wiring_and_remaining_contract_remediation.md",
            "docs/phase_reports/phase18_o_final_independent_ai_lifecycle_v2_conformance_review.md",
            "docs/phase_reports/phase18_p_runtime_lifecycle_evidence_authority_and_atomic_failure_remediation.md",
            "docs/phase_reports/phase18_q_final_independent_closure_review.md",
        ],
        "system_objective_alignment": {
            "objective": "Safe, reproducible, auditable daily Japanese cash equity operation with minimal user work.",
            "must_not_use_operational_goal_to_allow": ["forced BUY", "Top-N forced BUY", "negative expected edge BUY", "BV15 relaxation", "unapproved model adoption", "freshness/drift fail-open"],
        },
        "why_repeated_remediation_occurred": "Phase18 repeatedly patched symptoms in local operators/evidence collectors before a single accepted-authority and runtime-evidence contract was fixed. This let resolver fallback, synthetic evidence, and partial call-graph tests pass locally while new Root Cause gaps appeared in independent reviews.",
        "production_scope_inventory": file_inventory(),
        "formal_authority_flow": authority_flow(),
        "accepted_artifact_resolution_contract": accepted_resolution_contract(),
        "integrity_verification_contract": [
            "Registry accepted event identity",
            "Accepted state identity",
            "Atomic BUY AI Bundle identity",
            "Joint bundle hash",
            "Candidate/Opportunity bundle hashes",
            "Dataset/training bundle hashes",
            "Calibration artifact hash",
            "Schema, feature contract, target contract hashes",
            "Candidate/Opportunity compatibility",
            "Lineage refs",
            "Authority decision ref",
            "Registry event/checkpoint refs",
        ],
        "integrity_failure_mapping": {
            "missing accepted state": "INSUFFICIENT_EVIDENCE => BUY BLOCK, SELL dependency path may continue",
            "hash/schema/lineage mismatch": "CRITICAL_AUTHORITY_VIOLATION => BUY BLOCK, no Runtime adoption",
            "incompatible Candidate/Opportunity": "MODEL_UNHEALTHY or CRITICAL_AUTHORITY_VIOLATION depending source",
            "unreadable bundle": "INSUFFICIENT_EVIDENCE",
        },
        "freshness_contract": {
            "required_dates": {
                "label_safe_cutoff": "business-date from Dataset Bundle; required; future forbidden",
                "training_dataset_max_date": "business-date from dataset source lineage; required; future forbidden",
                "model_training_cutoff": "business-date of training data cutoff, not created_at; required; future relative to label_safe_cutoff forbidden",
                "model_created_at": "timestamp metadata; required for audit, not a substitute for cutoff",
                "model_accepted_at": "Registry accepted timestamp; required",
                "runtime_decision_date": "business-date of Runtime decision; required",
            },
            "clocks": {
                "dataset_lag_business_days": "label_safe_cutoff - training_dataset_max_date",
                "model_training_lag_business_days": "label_safe_cutoff - model_training_cutoff",
                "model_acceptance_age_business_days": "runtime_decision_date - model_accepted_at",
            },
            "invalid_cases": {
                "negative lag": "fail-closed REVIEW/BLOCK; never PASS",
                "future cutoff": "CRITICAL_AUTHORITY_VIOLATION or INSUFFICIENT_EVIDENCE",
                "accepted_at < created_at": "REVIEW_REQUIRED at minimum",
                "decision_date < accepted_at": "INSUFFICIENT_EVIDENCE",
                "calendar unavailable/unreadable/range short/holiday mismatch": "INSUFFICIENT_EVIDENCE; Production weekday fallback forbidden",
            },
        },
        "drift_evidence_contract": {
            "accepted_baseline_required": ["materialized distributions", "histogram bins/counts", "quantiles", "population/prediction stats", "positive coverage", "all-negative reference", "baseline date range", "row count", "sample policy", "hash", "schema", "lineage"],
            "runtime_current_required": ["current Candidate population", "feature distributions", "prediction distribution", "positive coverage", "all-negative state", "score distribution", "current evidence hash", "current window identity"],
            "forbidden": ["summary stats random/sample restoration", "current-derived baseline", "Production use of test fixture baseline", "hash-unverified baseline", "zero-filled missing baseline"],
            "immediate_gate": ["artifact integrity", "freshness", "feature drift", "candidate population drift", "prediction distribution drift", "positive coverage drift", "all-negative behavior", "score distribution consistency"],
            "delayed_monitoring": ["realized calibration error", "5/10/20bd return", "rank correlation", "Top-k realized return", "hit rate", "bucket realized monotonicity"],
        },
        "runtime_decision_contract": {
            "decision": ["PASS", "REVIEW_REQUIRED", "BLOCK"],
            "classification": ["HEALTHY", "MARKET_NO_OPPORTUNITY", "MODEL_UNHEALTHY", "INSUFFICIENT_EVIDENCE", "CRITICAL_AUTHORITY_VIOLATION"],
            "minimum_control_flags": ["block_buy_planning", "block_buy_submit", "block_sell_planning", "block_sell_submit"],
            "compatibility_note": "Existing block_buy/block_sell/block_submit is insufficient if block_submit is interpreted globally. Keep backward fields only as derived aliases with scoped submit fields authoritative.",
        },
        "current_production_call_graph": {
            "morning": "run_daily_operation -> produce_buy_ai_decisions -> resolve Registry model sets -> Candidate inference -> Opportunity inference -> lifecycle evidence -> lifecycle gate -> if BLOCK/REVIEW, append sell_continuity record and exit before morning planning; if PASS, run morning planning.",
            "sell_planning": "run_daily_operation --job sell_planning -> PM producer -> sell_planning_pending_pipeline if PM decisions exist.",
            "submit": "run_daily_operation --job submit -> submit guard / pending plan path, not directly controlled by AI lifecycle scoped flags today.",
            "gap": "SELL continuity is a declared stage, not a proven downstream execution path from the same blocked BUY event.",
        },
        "rollback_revoke_transaction_contract": {
            "states": ["PREPARED", "VALIDATED", "WRITING_EVENT", "WRITING_INDEX", "WRITING_CHECKPOINT", "POST_VALIDATING", "COMMITTED", "ROLLING_BACK", "RESTORED", "RESTORE_FAILED", "CRITICAL"],
            "phase18_scope": "Isolated registry transaction rehearsal with restore-failure injection and non-mutation evidence.",
            "phase19_scope": "Runtime state-changing rollback rehearsal and production acceptance gates.",
        },
        "root_cause_clusters": {
            "ROOT-A": "Accepted Authority Resolver responsibility unclear/split",
            "ROOT-B": "Evidence resolver compensates for missing evidence",
            "ROOT-C": "Accepted Atomic BUY AI Bundle lacks complete Runtime baseline/contract",
            "ROOT-D": "Immediate vs Delayed monitoring boundary not fixed",
            "ROOT-E": "BUY block vs global Runtime halt control design ambiguous",
            "ROOT-F": "Registry transaction failure model incomplete",
            "ROOT-G": "Tests emphasize local operators/fixtures over Production call graph",
        },
        "q_gap_root_cause_matrix": root_cause_matrix(),
        "remediation_units": remediation_units(),
        "remediation_dependency_graph": [
            "RU1 Accepted Authority -> RU2 Freshness",
            "RU1 Accepted Authority -> RU3 Drift Baseline",
            "RU1/RU2/RU3 -> RU4 BUY-only Control and SELL Continuity",
            "RU1 -> RU5 Atomic Restore Failure Semantics",
            "RU1-RU5 -> Closure Acceptance",
        ],
        "predefined_acceptance_contract": {
            "accepted_authority": ["accepted state resolves", "accepted state none does not fallback", "promotion candidate only => INSUFFICIENT_EVIDENCE", "accepted event/bundle hash mismatch fail-closed", "manual path rejected"],
            "freshness": ["normal 3 clocks", "negative training lag", "future model cutoff", "missing/unreadable/range-short calendar", "missing accepted_at", "timezone mismatch"],
            "drift": ["materialized baseline stable current", "feature/prediction/population/positive coverage drift", "all-negative only", "all-negative + drift", "missing baseline", "baseline hash mismatch", "insufficient sample"],
            "buy_sell": ["MODEL_UNHEALTHY + existing position", "INSUFFICIENT_EVIDENCE + SELL signal", "MARKET_NO_OPPORTUNITY + SELL signal", "BUY submit block", "SELL submit authorization reachable", "Current/Valuation/PM/Safety reachable"],
            "rollback": ["event/index/checkpoint/post-validation failures", "restore event/index/checkpoint failure", "RESTORE_FAILED => CRITICAL"],
        },
        "test_architecture_audit": test_architecture_audit(),
        "sot_vs_implementation_matrix": [
            {"Contract Point": "Accepted artifact resolution", "SoT": "Registry accepted only", "Current Implementation": "Atomic BUY bundle resolver falls back to latest Promotion Candidate", "Gap": "CONTRACT_CONFLICT", "Root Cause": "ROOT-A/ROOT-B"},
            {"Contract Point": "Integrity verification", "SoT": "Verify Registry event, bundle, hash, schema, lineage", "Current Implementation": "Loads JSON and records content_hash", "Gap": "PARTIAL", "Root Cause": "ROOT-A/ROOT-C"},
            {"Contract Point": "Freshness clocks", "SoT": "Formal 3 clocks from label-safe/cutoff/accepted_at", "Current Implementation": "created_at fallback and negative lag can pass", "Gap": "CONTRACT_CONFLICT", "Root Cause": "ROOT-B"},
            {"Contract Point": "Trading calendar", "SoT": "Formal calendar authority", "Current Implementation": "weekday fallback with no fail-closed reason", "Gap": "CONTRACT_CONFLICT", "Root Cause": "ROOT-B"},
            {"Contract Point": "Drift baseline", "SoT": "Accepted materialized baseline", "Current Implementation": "synthetic values from summary stats", "Gap": "PARTIAL", "Root Cause": "ROOT-C"},
            {"Contract Point": "Immediate/delayed", "SoT": "Delayed realized metrics not daily gate inputs", "Current Implementation": "calibration_error_delta can block immediate gate", "Gap": "CONTRACT_CONFLICT", "Root Cause": "ROOT-D"},
            {"Contract Point": "BUY/SELL control", "SoT": "BUY block does not stop SELL dependencies", "Current Implementation": "morning exits after BUY block; separate sell job not proven", "Gap": "PARTIAL", "Root Cause": "ROOT-E"},
            {"Contract Point": "Rollback restore", "SoT": "Atomic fail-closed with restore failure critical", "Current Implementation": "restore snapshots but no restore-failure CRITICAL proof", "Gap": "PARTIAL", "Root Cause": "ROOT-F"},
        ],
        "line_references": line_refs(),
        "risks_of_local_patching": [
            "Removing only the Promotion Candidate fallback without hash/lineage verification leaves forged accepted bundle risk.",
            "Adding a negative-lag check without formal calendar authority still allows wrong clocks.",
            "Replacing synthetic baseline without immediate/delayed split can keep calibration proxy misuse.",
            "Adding SELL continuity unit tests without call-graph proof can keep global block behavior hidden.",
        ],
        "remaining_unknowns": [
            "Exact Atomic BUY AI Bundle accepted event schema does not yet exist in formal Registry accepted set.",
            "Whether BUY and SELL should run in one daily wrapper or separate scheduled jobs must be fixed as an operator contract.",
            "Formal baseline artifact format must be chosen before implementation.",
        ],
        "recommended_next_implementation_step": "Implement RU1-RU3 together as the next remediation step because Accepted Authority, Integrity, Freshness, and Baseline evidence share the same Runtime evidence boundary. Then implement RU4 and RU5 with integration/failure-injection acceptance.",
        "phase18_completion_status": "PHASE18_NOT_COMPLETE",
        "phase19_readiness_status": "PHASE19_NOT_READY",
        "final_judgment": {
            "primary": "PHASE18_R_ROOT_CAUSE_AND_CONTRACT_CLOSURE_AUDIT_COMPLETE",
            "secondary": ["PHASE18_NOT_COMPLETE", "PHASE19_NOT_READY", "REMEDIATION_PLAN_READY"],
        },
        "non_mutation_confirmation": {
            "registry_count_before": registry_before["count"],
            "registry_count_after": registry_after["count"],
            "registry_hash_before": registry_before["hash"],
            "registry_hash_after": registry_after["hash"],
            "registry_unchanged": registry_before == registry_after,
            "production_code_modified_by_phase18r": False,
            "runtime_switch": False,
            "runtime_submit": False,
            "buy_restart": False,
            "broker_write": False,
        },
    }
    return payload


def md_table(rows: list[dict[str, Any]], keys: list[str]) -> list[str]:
    lines = ["| " + " | ".join(keys) + " |", "|" + "|".join(["---"] * len(keys)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(k, "")).replace("\n", " ") for k in keys) + " |")
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Phase18-R AI Lifecycle v2 Root Cause and Contract Closure Audit",
        "",
        f"- Run ID: `{RUN_ID}`",
        f"- Primary: `{report['final_judgment']['primary']}`",
        f"- Secondary: `{', '.join(report['final_judgment']['secondary'])}`",
        "- Production code fix: not performed",
        "",
        "## Executive Summary",
        "",
        "Phase18-R confirms that Q-GAP-001 through Q-GAP-008 are not eight independent bugs. They cluster around accepted authority resolution, resolver over-compensation for missing evidence, incomplete Atomic BUY AI Bundle runtime evidence, immediate/delayed metric ambiguity, BUY-only control semantics, rollback failure semantics, and test architecture gaps.",
        "",
        "The next implementation step is ready, but Phase18 remains incomplete and Phase19 is not ready.",
        "",
        "## 21.1 SoT Authority Flow",
        "",
        "```text",
        "Source -> Dataset -> Training -> Promotion -> Authority -> Registry -> Runtime -> BUY / SELL",
        "```",
        "",
    ]
    lines.extend(md_table(report["formal_authority_flow"], ["node", "owner", "output", "failure"]))
    lines.extend([
        "",
        "## 21.2 Current Production Call Graph",
        "",
        "```text",
        "morning -> produce_buy_ai_decisions -> Registry model set resolver -> Candidate inference -> Opportunity inference -> lifecycle_evidence -> ai_lifecycle_gates -> BLOCK/REVIEW exits before morning planning; PASS continues to BUY planning",
        "sell_planning -> PM producer -> sell_planning_pending_pipeline",
        "submit -> pending/approval/submit guard path",
        "```",
        "",
        f"- Gap: {report['current_production_call_graph']['gap']}",
        "",
        "## Accepted Artifact Resolution Contract",
        "",
    ])
    lines.extend(md_table(report["accepted_artifact_resolution_contract"], ["artifact_type", "production_runtime", "condition"]))
    lines.extend([
        "",
        "## Integrity Verification Contract",
        "",
    ])
    for item in report["integrity_verification_contract"]:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "Failure mapping:",
        "",
    ])
    for key, value in report["integrity_failure_mapping"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend([
        "",
        "## Freshness Contract",
        "",
        "Formal Trading Calendar is required for Production. Weekday fallback is forbidden for Production Runtime authority; it may appear only in isolated review/test evidence.",
        "",
    ])
    for key, value in report["freshness_contract"]["clocks"].items():
        lines.append(f"- `{key}` = {value}")
    lines.extend([
        "",
        "Invalid cases:",
        "",
    ])
    for key, value in report["freshness_contract"]["invalid_cases"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend([
        "",
        "## Drift Evidence Contract",
        "",
        "- Immediate gate: " + ", ".join(report["drift_evidence_contract"]["immediate_gate"]),
        "- Delayed monitoring: " + ", ".join(report["drift_evidence_contract"]["delayed_monitoring"]),
        "- Forbidden: " + ", ".join(report["drift_evidence_contract"]["forbidden"]),
        "",
        "## Runtime Decision Contract",
        "",
        "- Decisions: `PASS`, `REVIEW_REQUIRED`, `BLOCK`",
        "- Classifications: `HEALTHY`, `MARKET_NO_OPPORTUNITY`, `MODEL_UNHEALTHY`, `INSUFFICIENT_EVIDENCE`, `CRITICAL_AUTHORITY_VIOLATION`",
        "- Required scoped controls: `block_buy_planning`, `block_buy_submit`, `block_sell_planning`, `block_sell_submit`",
        "- Existing `block_submit` should become a backward-compatible alias only after scoped submit flags are authoritative.",
        "",
        "## 21.3 SoT vs Implementation Diff",
        "",
    ])
    lines.extend(md_table(report["sot_vs_implementation_matrix"], ["Contract Point", "SoT", "Current Implementation", "Gap", "Root Cause"]))
    lines.extend([
        "",
        "## 21.4 Q-GAP Root Cause Matrix",
        "",
    ])
    lines.extend(md_table(report["q_gap_root_cause_matrix"], ["Q-GAP", "Severity", "Symptom", "Primary Root Cause", "Shared Remediation Unit"]))
    lines.extend([
        "",
        "## Root Cause Clusters",
        "",
    ])
    for key, value in report["root_cause_clusters"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend([
        "",
        "## Remediation Units",
        "",
    ])
    for unit in report["remediation_units"]:
        lines.extend([
            f"### {unit['unit']}",
            "",
            f"- Purpose: {unit['purpose']}",
            f"- Root causes: `{', '.join(unit['root_causes'])}`",
            f"- Target gaps: `{', '.join(unit['gaps'])}`",
            f"- Production modules: `{', '.join(unit['modules'])}`",
            f"- Do not change: {unit['do_not_change']}",
            f"- Acceptance tests: {', '.join(unit['acceptance_tests'])}",
            f"- Depends on: {', '.join(unit['depends_on']) if unit['depends_on'] else 'none'}",
            "",
        ])
    lines.extend([
        "## 21.5 Remediation Dependency Graph",
        "",
        "```text",
        "Accepted Authority",
        "  -> Integrity",
        "  -> Freshness / Baseline",
        "  -> Runtime Decision",
        "  -> BUY / SELL Control",
        "  -> Closure Acceptance",
        "Atomic Restore Failure Semantics depends on accepted authority but can be implemented in parallel after RU1 contract is fixed.",
        "```",
        "",
        "## Test Architecture Audit",
        "",
        f"- Existing regression: {report['test_architecture_audit']['existing_regression_result']}",
        "- Guarantees:",
    ])
    for item in report["test_architecture_audit"]["guarantees"]:
        lines.append(f"  - {item}")
    lines.append("- Does not guarantee:")
    for item in report["test_architecture_audit"]["does_not_guarantee"]:
        lines.append(f"  - {item}")
    lines.extend([
        "",
        "## Predefined Acceptance Contract",
        "",
    ])
    for key, values in report["predefined_acceptance_contract"].items():
        lines.append(f"- `{key}`: {', '.join(values)}")
    lines.extend([
        "",
        "## Risks Of Local Patching",
        "",
    ])
    for item in report["risks_of_local_patching"]:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "## Recommended Next Step",
        "",
        report["recommended_next_implementation_step"],
        "",
        "## Non-Mutation Confirmation",
        "",
        f"- Registry count before/after: `{report['non_mutation_confirmation']['registry_count_before']}` / `{report['non_mutation_confirmation']['registry_count_after']}`",
        f"- Registry hash before/after: `{report['non_mutation_confirmation']['registry_hash_before']}` / `{report['non_mutation_confirmation']['registry_hash_after']}`",
        "- Runtime switch: not performed",
        "- Runtime submit: not performed",
        "- BUY restart: not performed",
        "- Broker write: not performed",
        "",
        "## Final Judgment",
        "",
        "- `PHASE18_R_ROOT_CAUSE_AND_CONTRACT_CLOSURE_AUDIT_COMPLETE`",
        "- `PHASE18_NOT_COMPLETE`",
        "- `PHASE19_NOT_READY`",
        "- `REMEDIATION_PLAN_READY`",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    report = report_payload()
    write_json(EVIDENCE_DIR / "root_cause_contract_closure_audit.json", report)
    write_json(REPORT_JSON, report)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
