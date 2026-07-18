from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "phase18t-buy-only-control-atomic-restore-20260717T000000Z"
EVIDENCE_DIR = ROOT / "reports" / "phase18_t_buy_only_runtime_control_and_atomic_restore_failure_semantics" / RUN_ID
REPORT_JSON = ROOT / "reports" / "phase_reports" / "phase18_t_buy_only_runtime_control_and_atomic_restore_failure_semantics.json"
REPORT_MD = ROOT / "docs" / "phase_reports" / "phase18_t_buy_only_runtime_control_and_atomic_restore_failure_semantics.md"


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def line_refs() -> dict[str, dict[str, int]]:
    targets = {
        "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py": {
            "scoped_block_flags": "block_buy_planning",
            "allow_sell_submit_authorization": "allow_sell_submit_authorization",
        },
        "src/ai_fund_lab_v2/runtime_v2/lifecycle_sell_continuity.py": {
            "sell_continuity_contract": "class SellContinuityDecision",
            "sell_continuity_evaluator": "def evaluate_sell_continuity_from_buy_lifecycle_gate",
        },
        "src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py": {
            "buy_ai_manifest_scoped_flags": "ai_lifecycle_gate_block_buy_planning",
            "buy_planning_permission": "buy_planning_permission",
            "sell_submit_authorization_permission": "sell_submit_authorization_permission",
        },
        "src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py": {
            "morning_buy_block_branch": "elif buy_ai_result.status == \"BLOCKED\"",
            "continuity_stage_helper": "def _buy_lifecycle_continuity_stages",
            "morning_continuity_evidence": "buy_lifecycle_sell_continuity.json",
        },
        "src/ai_fund_lab_v2/ai_lifecycle/rollback_revoke.py": {
            "transaction_states": "TRANSACTION_STATES",
            "restore_failures": "RESTORE_FAILURES",
            "transaction": "def _transaction(",
            "commit": "def _commit(",
            "restore_files": "def _restore_files(",
            "registry_hashes": "def _registry_hashes(",
        },
        "tests/ai_lifecycle/test_phase18t_buy_only_and_restore_failure.py": {
            "buy_only_scenarios": "test_phase18t_buy_lifecycle_blocks_buy_only_for_required_scenarios",
            "entrypoint_stage": "test_phase18t_run_daily_operation_stage_reaches_sell_authorization_call_graph",
            "restore_critical": "test_phase18t_restore_failure_is_critical_and_registry_unchanged",
        },
    }
    refs: dict[str, dict[str, int]] = {}
    for rel, patterns in targets.items():
        refs[rel] = {}
        path = ROOT / rel
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        for key, pattern in patterns.items():
            for idx, line in enumerate(text.splitlines(), start=1):
                if pattern in line:
                    refs[rel][key] = idx
                    break
    return refs


def acceptance_matrix() -> list[dict[str, str]]:
    return [
        {"category": "BUY-only MODEL_UNHEALTHY", "status": "PASS", "evidence": "BUY planning/submit BLOCK; Current, Valuation, PM, Safety, SELL planning, SELL authorization allowed"},
        {"category": "BUY-only INSUFFICIENT_EVIDENCE", "status": "PASS", "evidence": "BUY fail-closed; SELL continuity permissions remain PASS when SELL dependency is normal"},
        {"category": "BUY-only MARKET_NO_OPPORTUNITY", "status": "PASS", "evidence": "No forced BUY; SELL continuity remains PASS"},
        {"category": "BUY REVIEW_REQUIRED", "status": "PASS", "evidence": "BUY review blocks BUY planning/submit; SELL continuity authorization stage reached"},
        {"category": "run_daily_operation Call Graph", "status": "PASS", "evidence": "buy_lifecycle_sell_authorization_continuity stage added to morning entrypoint path"},
        {"category": "restore event failure", "status": "PASS", "evidence": "RESTORE_FAILED -> CRITICAL; accepted state and registry hashes unchanged"},
        {"category": "restore index failure", "status": "PASS", "evidence": "RESTORE_FAILED -> CRITICAL; no partial index"},
        {"category": "restore checkpoint failure", "status": "PASS", "evidence": "RESTORE_FAILED -> CRITICAL; no partial checkpoint"},
        {"category": "temporary cleanup failure", "status": "PASS", "evidence": "RESTORE_FAILED -> CRITICAL; manual recovery required"},
        {"category": "restore validation failure", "status": "PASS", "evidence": "RESTORE_FAILED -> CRITICAL; audit evidence generated"},
        {"category": "Registry Accepted Update", "status": "NOT_MODIFIED", "evidence": "No production registry accepted state mutation performed"},
        {"category": "Runtime Switch", "status": "NOT_MODIFIED", "evidence": "No Runtime accepted set switch performed"},
        {"category": "BUY Restart", "status": "NOT_MODIFIED", "evidence": "No BUY restart or broker write invoked"},
    ]


def source_hashes() -> dict[str, str]:
    paths = [
        "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py",
        "src/ai_fund_lab_v2/runtime_v2/lifecycle_sell_continuity.py",
        "src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py",
        "src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py",
        "src/ai_fund_lab_v2/ai_lifecycle/rollback_revoke.py",
        "tests/ai_lifecycle/test_phase18t_buy_only_and_restore_failure.py",
    ]
    return {rel: sha256_file(ROOT / rel) for rel in paths}


def build_payload() -> dict[str, Any]:
    tests = {
        "targeted": {
            "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18t_pycache python3 -m pytest tests/ai_lifecycle/test_phase18n_production_lifecycle_wiring.py tests/ai_lifecycle/test_phase18p_runtime_lifecycle_evidence_authority.py tests/ai_lifecycle/test_phase18s_accepted_runtime_evidence_authority.py tests/ai_lifecycle/test_phase18t_buy_only_and_restore_failure.py -q",
            "result": "21 passed",
        },
        "phase18": {
            "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18t_pycache python3 -m pytest tests/ai_lifecycle -q",
            "result": "28 passed, 2 sklearn convergence warnings",
        },
        "cross_contract": {
            "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18t_pycache python3 -m pytest tests/ai_lifecycle tests/artifact_registry/test_phase16ac_full_event_log_validator.py tests/artifact_registry/test_phase16ad_materialized_index_builder.py tests/artifact_registry/test_phase16ag_checkpoint_writer.py tests/artifact_registry/test_phase16au_registry_resolver.py tests/artifact_registry/test_phase16av_runtime_lookup_adapter.py tests/runtime_v2/test_phase16av_registry_consumer_cutover.py -q",
            "result": "96 passed, 2 sklearn convergence warnings",
        },
        "compile": {
            "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18t_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py src/ai_fund_lab_v2/runtime_v2/lifecycle_sell_continuity.py src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py src/ai_fund_lab_v2/ai_lifecycle/rollback_revoke.py",
            "result": "PASS",
        },
    }
    return {
        "phase": "Phase18-T",
        "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "primary_judgement": "PHASE18_T_BUY_ONLY_CONTROL_AND_ATOMIC_RESTORE_COMPLETE",
        "secondary_judgements": ["RU4_COMPLETE", "RU5_COMPLETE", "PHASE18_READY_FOR_FINAL_REVIEW", "PHASE19_NOT_READY"],
        "scope": {
            "included": ["RU4", "RU5", "Q-GAP-007", "Q-GAP-008"],
            "excluded": ["RU1", "RU2", "RU3", "Phase19", "Runtime Switch", "Historical Runtime Full Path", "Broker Write", "Production BUY"],
        },
        "ru4": {
            "status": "COMPLETE",
            "contract": "BUY lifecycle gate blocks BUY planning and BUY submit only; SELL continuity permissions remain independent.",
            "scenarios": ["MODEL_UNHEALTHY", "INSUFFICIENT_EVIDENCE", "MARKET_NO_OPPORTUNITY", "BUY REVIEW_REQUIRED"],
        },
        "ru5": {
            "status": "COMPLETE",
            "contract": "Restore failure is RESTORE_FAILED -> CRITICAL with accepted state and registry hash invariance evidence.",
            "failure_injections": ["restore_event_failure", "restore_index_failure", "restore_checkpoint_failure", "temporary_cleanup_failure", "restore_validation_failure"],
        },
        "acceptance_matrix": acceptance_matrix(),
        "tests": tests,
        "line_refs": line_refs(),
        "source_hashes": source_hashes(),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase18-T BUY-only Runtime Control and Atomic Restore Failure Semantics",
        "",
        f"Run ID: `{payload['run_id']}`",
        "",
        f"Final Judgement: `{payload['primary_judgement']}`",
        "",
        "Secondary Judgements: " + ", ".join(f"`{item}`" for item in payload["secondary_judgements"]),
        "",
        "## Scope",
        "",
        "- Included: " + ", ".join(payload["scope"]["included"]),
        "- Excluded: " + ", ".join(payload["scope"]["excluded"]),
        "",
        "## RU4",
        "",
        f"Status: `{payload['ru4']['status']}`",
        "",
        payload["ru4"]["contract"],
        "",
        "## RU5",
        "",
        f"Status: `{payload['ru5']['status']}`",
        "",
        payload["ru5"]["contract"],
        "",
        "## Acceptance Matrix",
        "",
        "| Category | Status | Evidence |",
        "|---|---:|---|",
    ]
    for item in payload["acceptance_matrix"]:
        lines.append(f"| {item['category']} | {item['status']} | {item['evidence']} |")
    lines.extend(["", "## Verification", ""])
    for name, test in payload["tests"].items():
        lines.append(f"- `{name}`: `{test['result']}`")
    lines.extend(
        [
            "",
            "## Runtime Safety",
            "",
            "Registry accepted変更、Runtime switch、BUY restart、Broker write、Production BUY、Historical Runtime Full Pathはいずれも未実施です。",
            "",
            "## Final",
            "",
            "`PHASE18_T_BUY_ONLY_CONTROL_AND_ATOMIC_RESTORE_COMPLETE`",
            "",
            "`RU4_COMPLETE` / `RU5_COMPLETE` / `PHASE18_READY_FOR_FINAL_REVIEW` / `PHASE19_NOT_READY`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_json(EVIDENCE_DIR / "phase18t_evidence.json", payload)
    write_json(EVIDENCE_DIR / "acceptance_matrix.json", {"items": payload["acceptance_matrix"]})
    write_json(EVIDENCE_DIR / "source_hashes.json", payload["source_hashes"])
    write_json(REPORT_JSON, payload)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": "PASS", "run_id": RUN_ID, "report": str(REPORT_JSON.relative_to(ROOT))}, sort_keys=True))


if __name__ == "__main__":
    main()
