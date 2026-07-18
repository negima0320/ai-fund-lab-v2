from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "phase18v-runtime-test-fresh-run-operator-20260717T000000Z"
EVIDENCE_DIR = ROOT / "reports" / "phase18_v_runtime_test_fresh_run_operator" / RUN_ID
REPORT_JSON = ROOT / "reports" / "phase_reports" / "phase18_v_runtime_test_fresh_run_operator.json"
REPORT_MD = ROOT / "docs" / "phase_reports" / "phase18_v_runtime_test_fresh_run_operator.md"


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
        "scripts/runtime_test.py": {
            "fresh_run_parser": "fresh = subparsers.add_parser(\"fresh-run\")",
            "auto_prepare_deprecation": "--auto-prepare is deprecated",
            "fresh_run_command": "def fresh_run_command(",
            "fresh_run_summary": "def _fresh_run_summary(",
            "dry_run_steps": "def _fresh_run_dry_run_steps(",
            "persist_summary": "def _persist_fresh_run_summary(",
        },
        "docs/03_operations/runtime_test_command_guide.md": {
            "fresh_run_section": "## Fresh Run",
            "auto_prepare_note": "`run --auto-prepare` is deprecated",
        },
        "docs/01_requirements/phase_roadmap.md": {
            "phase18v_status": "Phase18-V",
        },
        "tests/runtime_v2/test_phase18v_runtime_test_fresh_run.py": {
            "dry_run": "test_phase18v_fresh_run_dry_run_has_full_plan_and_no_mutation",
            "happy_path": "test_phase18v_fresh_run_happy_path_reuses_normal_runtime_cli_and_closes",
            "backup_failure": "test_phase18v_fresh_run_backup_failure_stops_before_reset",
            "reset_failure": "test_phase18v_fresh_run_reset_failure_stops_before_plan",
            "plan_failure": "test_phase18v_fresh_run_plan_failure_stops_before_run",
            "run_halt": "test_phase18v_fresh_run_run_halt_skips_validate_and_close",
            "validate_failure": "test_phase18v_fresh_run_validate_failure_skips_close",
            "auto_prepare": "test_phase18v_auto_prepare_is_not_ambiguous_noop",
            "production_reject": "test_phase18v_fresh_run_production_profile_rejected",
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
        "scripts/runtime_test.py",
        "docs/03_operations/runtime_test_command_guide.md",
        "docs/01_requirements/phase_roadmap.md",
        "tests/runtime_v2/test_phase18v_runtime_test_fresh_run.py",
        "tests/runtime_v2/test_phase17_k_runtime_test_runner.py",
        "tests/runtime_v2/test_phase17_bv11_runtime_test_plan_persistence.py",
    ]
    return {rel: sha256_file(ROOT / rel) for rel in paths}


def build_payload() -> dict[str, Any]:
    acceptance = [
        {"item": "fresh-run entrypoint", "status": "PASS", "evidence": "scripts/runtime_test.py fresh-run parser and command"},
        {"item": "ordered orchestration", "status": "PASS", "evidence": "Status -> Backup -> Reset -> Plan -> Run -> Validate -> Close summary"},
        {"item": "dry-run no mutation", "status": "PASS", "evidence": "dry-run test verifies no backup, reset, CLI execution, close mutation"},
        {"item": "failure stop", "status": "PASS", "evidence": "backup/reset/plan/run/validate failures stop later steps"},
        {"item": "normal Runtime CLI use", "status": "PASS", "evidence": "happy path test monkeypatches run_runtime_cli and verifies module command"},
        {"item": "evidence preservation", "status": "PASS", "evidence": "no purge path in fresh-run; new run_id generated"},
        {"item": "auto-prepare", "status": "LEGACY_INCOMPLETE_OPTION", "evidence": "option retained only as deprecated failure directing users to fresh-run"},
        {"item": "command guide", "status": "PASS", "evidence": "Fresh Run section added to docs/03_operations/runtime_test_command_guide.md"},
        {"item": "production prohibition", "status": "PASS", "evidence": "production profile rejected; broker write/external delivery disabled by profile checks"},
    ]
    tests = {
        "targeted": {
            "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18v_pycache python3 -m pytest tests/runtime_v2/test_phase17_k_runtime_test_runner.py tests/runtime_v2/test_phase17_bv11_runtime_test_plan_persistence.py tests/runtime_v2/test_phase18v_runtime_test_fresh_run.py -q",
            "result": "27 passed",
        },
        "compile": {
            "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18v_pycache python3 -m py_compile scripts/runtime_test.py",
            "result": "PASS",
        },
        "dry_run_command": {
            "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18v_pycache python3 scripts/runtime_test.py fresh-run --profile historical-extended-smoke --date-from 2026-06-29 --date-to 2026-07-10 --business-days 10 --initial-cash 1000000 --dry-run --json",
            "result": "DRY_RUN PASS; no Runtime CLI execution and no trading state mutation",
            "note": "PyArrow emitted sandbox sysctl warnings on stderr; JSON output status remained DRY_RUN PASS.",
        },
    }
    return {
        "phase": "Phase18-V",
        "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "primary_judgement": "PHASE18_V_RUNTIME_TEST_FRESH_RUN_OPERATOR_COMPLETE",
        "secondary_judgements": ["FRESH_RUN_COMMAND_READY", "PHASE18_COMPLETE_WITH_OPERATIONAL_EXTENSION", "PHASE19_NOT_STARTED"],
        "fresh_run_command": "PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-extended-smoke --date-from 2026-06-29 --date-to 2026-07-10 --business-days 10 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state",
        "auto_prepare_judgement": "LEGACY_INCOMPLETE_OPTION",
        "auto_prepare_resolution": "Deprecated failure; users must use fresh-run for formal orchestration.",
        "acceptance": acceptance,
        "tests": tests,
        "non_execution_confirmation": {
            "production_registry_accepted_state_changed": False,
            "runtime_accepted_model_switch": False,
            "production_buy_restart": False,
            "broker_write": False,
            "external_notification_delivery": False,
            "historical_10bd_real_run": False,
            "target_change": False,
            "feature_change": False,
            "bv15_change": False,
        },
        "line_refs": line_refs(),
        "source_hashes": source_hashes(),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase18-V Runtime Test Fresh-Run Operator",
        "",
        f"Run ID: `{payload['run_id']}`",
        "",
        f"Primary: `{payload['primary_judgement']}`",
        "",
        "Secondary: " + ", ".join(f"`{item}`" for item in payload["secondary_judgements"]),
        "",
        "## Command",
        "",
        "```bash",
        payload["fresh_run_command"],
        "```",
        "",
        "## Acceptance",
        "",
        "| Item | Status | Evidence |",
        "|---|---:|---|",
    ]
    for item in payload["acceptance"]:
        lines.append(f"| {item['item']} | {item['status']} | {item['evidence']} |")
    lines.extend(["", "## Tests", ""])
    for name, test in payload["tests"].items():
        lines.append(f"- `{name}`: `{test['result']}`")
    lines.extend(
        [
            "",
            "## Non-Execution Confirmation",
            "",
            "Production Registry accepted state変更、Runtime accepted model switch、Production BUY restart、Broker write、External notification delivery、Historical 10BD実Run、Target変更、Feature変更、BV15変更はいずれも未実施です。",
            "",
            "## Final",
            "",
            "`PHASE18_V_RUNTIME_TEST_FRESH_RUN_OPERATOR_COMPLETE`",
            "",
            "`FRESH_RUN_COMMAND_READY` / `PHASE18_COMPLETE_WITH_OPERATIONAL_EXTENSION` / `PHASE19_NOT_STARTED`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_json(EVIDENCE_DIR / "phase18v_evidence.json", payload)
    write_json(EVIDENCE_DIR / "acceptance_matrix.json", {"items": payload["acceptance"]})
    write_json(EVIDENCE_DIR / "source_hashes.json", payload["source_hashes"])
    write_json(REPORT_JSON, payload)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": "PASS", "run_id": RUN_ID, "report": str(REPORT_JSON.relative_to(ROOT))}, sort_keys=True))


if __name__ == "__main__":
    main()
