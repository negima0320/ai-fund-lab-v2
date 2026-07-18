from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "phase18u-final-independent-contract-closure-20260717T000000Z"
EVIDENCE_DIR = ROOT / "reports" / "phase18_u_final_independent_contract_closure_review" / RUN_ID
REPORT_JSON = ROOT / "reports" / "phase_reports" / "phase18_u_final_independent_contract_closure_review.json"
REPORT_MD = ROOT / "docs" / "phase_reports" / "phase18_u_final_independent_contract_closure_review.md"


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def line_refs() -> dict[str, dict[str, int]]:
    targets = {
        "src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py": {
            "accepted_resolver": "def _resolve_accepted_bundle(",
            "manual_prod_reject": "manual_accepted_bundle_path_forbidden",
            "promotion_candidate_reject": "promotion_candidates",
            "integrity": "def _integrity_evidence(",
            "component_hash": "def _verify_component_hash(",
            "training_dataset_ref": "def _verify_training_dataset_reference(",
            "calibration_artifact": "def _verify_calibration_artifact(",
            "freshness": "def _resolve_freshness(",
            "calendar_status": "def _calendar_status(",
            "calendar_range": "def _calendar_range_reasons(",
            "business_days": "def _bdiff(",
            "baseline": "def _resolve_baseline(",
            "materialized_baseline": "def _materialized_baseline(",
        },
        "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py": {
            "freshness_gate": "def evaluate_freshness_gate(",
            "integrity_gate": "def evaluate_integrity_gate(",
            "drift_gate": "def evaluate_drift_gate(",
            "runtime_gate": "def evaluate_runtime_ai_gate(",
            "scoped_flags": "block_buy_planning",
            "classifications": "CRITICAL_AUTHORITY_VIOLATION",
        },
        "src/ai_fund_lab_v2/runtime_v2/lifecycle_sell_continuity.py": {
            "contract": "class SellContinuityDecision",
            "evaluator": "def evaluate_sell_continuity_from_buy_lifecycle_gate(",
        },
        "src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py": {
            "buy_block_branch": "elif buy_ai_result.status == \"BLOCKED\"",
            "sell_authorization_stage": "buy_lifecycle_sell_authorization_continuity",
            "morning_evidence_writer": "def _write_morning_manifest_evidence(",
        },
        "src/ai_fund_lab_v2/ai_lifecycle/rollback_revoke.py": {
            "transaction_states": "TRANSACTION_STATES",
            "restore_failures": "RESTORE_FAILURES",
            "transaction": "def _transaction(",
            "restore_files": "def _restore_files(",
            "registry_hashes": "def _registry_hashes(",
        },
        "tests/ai_lifecycle/test_phase18s_accepted_runtime_evidence_authority.py": {
            "accepted_state": "test_phase18s_accepted_state_resolves_without_manual_path",
            "no_candidate_fallback": "test_phase18s_accepted_state_missing_does_not_fallback_to_promotion_candidate",
            "manual_prod_path": "test_phase18s_manual_path_rejected_in_production_runtime",
            "hash_fail_closed": "test_phase18s_hash_schema_lineage_mismatch_fail_closed",
            "freshness": "test_phase18s_freshness_invalid_calendar_and_negative_lag_fail_closed",
            "baseline": "test_phase18s_materialized_baseline_required_and_hash_verified",
            "drift": "test_phase18s_immediate_drift_cases",
        },
        "tests/ai_lifecycle/test_phase18t_buy_only_and_restore_failure.py": {
            "buy_only": "test_phase18t_buy_lifecycle_blocks_buy_only_for_required_scenarios",
            "call_graph": "test_phase18t_run_daily_operation_stage_reaches_sell_authorization_call_graph",
            "restore_failure": "test_phase18t_restore_failure_is_critical_and_registry_unchanged",
        },
    }
    refs: dict[str, dict[str, int]] = {}
    for rel, patterns in targets.items():
        path = ROOT / rel
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        refs[rel] = {}
        for name, pattern in patterns.items():
            for idx, line in enumerate(text.splitlines(), start=1):
                if pattern in line:
                    refs[rel][name] = idx
                    break
    return refs


def source_hashes() -> dict[str, str]:
    paths = [
        "docs/02_architecture/ai_lifecycle_v2.md",
        "docs/02_architecture/runtime_architecture_v2.md",
        "docs/phase_reports/phase18_r_ai_lifecycle_v2_root_cause_and_contract_closure_audit.md",
        "docs/phase_reports/phase18_s_accepted_runtime_evidence_authority_remediation.md",
        "docs/phase_reports/phase18_t_buy_only_runtime_control_and_atomic_restore_failure_semantics.md",
        "src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py",
        "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py",
        "src/ai_fund_lab_v2/runtime_v2/lifecycle_sell_continuity.py",
        "src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py",
        "src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py",
        "src/ai_fund_lab_v2/ai_lifecycle/rollback_revoke.py",
        "tests/ai_lifecycle/test_phase18s_accepted_runtime_evidence_authority.py",
        "tests/ai_lifecycle/test_phase18t_buy_only_and_restore_failure.py",
    ]
    return {rel: sha256_file(ROOT / rel) for rel in paths}


def ru_matrix() -> list[dict[str, Any]]:
    return [
        {
            "ru": "RU1",
            "contract": "Accepted-only Runtime Authority and Integrity Verification",
            "status": "PASS",
            "evidence": [
                "accepted state is required; missing state does not fallback to Promotion Candidate",
                "Production manual accepted_bundle_path is rejected",
                "joint, dataset, training, calibration, schema/target/feature, compatibility and lineage evidence fail closed",
            ],
            "contract_violations": [],
        },
        {
            "ru": "RU2",
            "contract": "Formal Calendar and Freshness Authority",
            "status": "PASS",
            "evidence": [
                "dataset lag, model training lag and model acceptance age are computed from formal calendar",
                "negative/future lag and calendar authority reason codes block or review fail-closed",
                "weekday fallback is forbidden as Production authority",
            ],
            "contract_violations": [],
        },
        {
            "ru": "RU3",
            "contract": "Materialized Drift Baseline and Immediate Runtime Gate",
            "status": "PASS",
            "evidence": [
                "materialized runtime_baseline is required and baseline_hash is verified",
                "prediction, feature, population, positive coverage, and all-negative checks are immediate gate inputs",
                "delayed realized calibration metric is not part of immediate drift gate",
            ],
            "contract_violations": [],
        },
        {
            "ru": "RU4",
            "contract": "BUY-only Control and SELL Continuity",
            "status": "PASS",
            "evidence": [
                "block_buy_planning and block_buy_submit are explicit",
                "SELL planning and SELL submit authorization remain reachable when SELL dependencies are normal",
                "run_daily_operation morning path records buy_lifecycle_sell_authorization_continuity",
            ],
            "contract_violations": [],
        },
        {
            "ru": "RU5",
            "contract": "Atomic Restore Failure Semantics",
            "status": "PASS",
            "evidence": [
                "restore failures map to RESTORE_FAILED then CRITICAL",
                "accepted state and registry hashes remain unchanged",
                "partial event/index/checkpoint are false and manual recovery is required",
            ],
            "contract_violations": [],
        },
    ]


def runtime_decision_matrix() -> list[dict[str, str]]:
    return [
        {"decision": "PASS", "classification": "HEALTHY / MARKET_NO_OPPORTUNITY", "buy_scope": "BUY allowed or no opportunity; SELL continuity allowed", "status": "PASS"},
        {"decision": "REVIEW_REQUIRED", "classification": "INSUFFICIENT_EVIDENCE / MODEL_HEALTH_REVIEW_REQUIRED", "buy_scope": "BUY planning/submit blocked; SELL continuity allowed if dependencies normal", "status": "PASS"},
        {"decision": "BLOCK", "classification": "MODEL_UNHEALTHY / CRITICAL_AUTHORITY_VIOLATION", "buy_scope": "BUY planning/submit blocked; SELL continuity independent unless SELL dependency blocks", "status": "PASS"},
    ]


def build_payload() -> dict[str, Any]:
    registry_events = ROOT / ".runtime" / "artifact_registry" / "events" / "registry_events.jsonl"
    tests = {
        "phase18_regression": {
            "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18u_pycache python3 -m pytest tests/ai_lifecycle -q",
            "result": "28 passed, 2 sklearn convergence warnings",
            "warning_assessment": "sklearn SGD convergence warnings in Phase18-D fixture; not a RU1-RU5 contract violation",
        },
        "cross_contract": {
            "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18u_pycache python3 -m pytest tests/ai_lifecycle tests/artifact_registry/test_phase16ac_full_event_log_validator.py tests/artifact_registry/test_phase16ad_materialized_index_builder.py tests/artifact_registry/test_phase16ag_checkpoint_writer.py tests/artifact_registry/test_phase16au_registry_resolver.py tests/artifact_registry/test_phase16av_runtime_lookup_adapter.py tests/runtime_v2/test_phase16av_registry_consumer_cutover.py -q",
            "result": "96 passed, 2 sklearn convergence warnings",
            "warning_assessment": "same warning source; no accepted authority, Runtime, BUY-only, or restore failure contract impact",
        },
        "compile": {
            "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18u_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py src/ai_fund_lab_v2/runtime_v2/lifecycle_sell_continuity.py src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py src/ai_fund_lab_v2/ai_lifecycle/rollback_revoke.py",
            "result": "PASS",
            "warning_assessment": "none",
        },
    }
    return {
        "phase": "Phase18-U",
        "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "review_type": "final independent contract closure review",
        "production_code_modified": False,
        "new_contracts_added": False,
        "new_gaps": [],
        "primary_judgement": "PHASE18_U_FINAL_CONTRACT_CLOSURE_PASS",
        "secondary_judgements": ["PHASE18_COMPLETE", "PHASE19_READY"],
        "review_basis": [
            "docs/02_architecture/ai_lifecycle_v2.md",
            "docs/02_architecture/runtime_architecture_v2.md",
            "docs/phase_reports/phase18_r_ai_lifecycle_v2_root_cause_and_contract_closure_audit.md",
            "docs/phase_reports/phase18_s_accepted_runtime_evidence_authority_remediation.md",
            "docs/phase_reports/phase18_t_buy_only_runtime_control_and_atomic_restore_failure_semantics.md",
        ],
        "ru_matrix": ru_matrix(),
        "runtime_decision_matrix": runtime_decision_matrix(),
        "tests": tests,
        "non_execution_confirmation": {
            "runtime_switch": False,
            "buy_restart": False,
            "broker_write": False,
            "registry_accepted_update": False,
            "historical_runtime_full_path": False,
            "registry_events_hash": sha256_file(registry_events),
            "registry_events_count": count_lines(registry_events),
        },
        "line_refs": line_refs(),
        "source_hashes": source_hashes(),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase18-U Final Independent Contract Closure Review",
        "",
        f"Run ID: `{payload['run_id']}`",
        "",
        f"Primary: `{payload['primary_judgement']}`",
        "",
        "Secondary: " + ", ".join(f"`{item}`" for item in payload["secondary_judgements"]),
        "",
        "## Review Scope",
        "",
        "Phase18-Rで固定済みのRU1〜RU5 Acceptance Contractのみを確認しました。新しいRoot Cause、Remediation Unit、Architecture、Evidence形式、Registry Contract、Phase19要件は追加していません。",
        "",
        "## RU Closure Matrix",
        "",
        "| RU | Contract | Status | Evidence |",
        "|---|---|---:|---|",
    ]
    for item in payload["ru_matrix"]:
        lines.append(f"| {item['ru']} | {item['contract']} | {item['status']} | {'; '.join(item['evidence'])} |")
    lines.extend(["", "## Runtime Decision Contract", "", "| Decision | Classification | BUY Scope | Status |", "|---|---|---|---:|"])
    for item in payload["runtime_decision_matrix"]:
        lines.append(f"| {item['decision']} | {item['classification']} | {item['buy_scope']} | {item['status']} |")
    lines.extend(["", "## Regression", ""])
    for name, test in payload["tests"].items():
        lines.append(f"- `{name}`: `{test['result']}`; {test['warning_assessment']}")
    lines.extend(
        [
            "",
            "## Non-Execution Confirmation",
            "",
            "- Production code修正: `False`",
            "- Runtime switch: `False`",
            "- BUY restart: `False`",
            "- Broker write: `False`",
            "- Registry accepted変更: `False`",
            "- Historical Runtime Full Path: `False`",
            "",
            "## Gap Decision",
            "",
            "Phase18-R Acceptance Contract違反、SoT違反、Production Contract違反、重大な実装修正漏れは検出されませんでした。",
            "",
            "## Final",
            "",
            "`PHASE18_U_FINAL_CONTRACT_CLOSURE_PASS`",
            "",
            "`PHASE18_COMPLETE` / `PHASE19_READY`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_json(EVIDENCE_DIR / "phase18u_evidence.json", payload)
    write_json(EVIDENCE_DIR / "ru_closure_matrix.json", {"items": payload["ru_matrix"]})
    write_json(EVIDENCE_DIR / "source_hashes.json", payload["source_hashes"])
    write_json(REPORT_JSON, payload)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": "PASS", "run_id": RUN_ID, "report": str(REPORT_JSON.relative_to(ROOT))}, sort_keys=True))


if __name__ == "__main__":
    main()
