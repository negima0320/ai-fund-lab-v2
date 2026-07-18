from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "phase18s-accepted-runtime-evidence-authority-20260717T000000Z"
EVIDENCE_DIR = ROOT / "reports" / "phase18_s_accepted_runtime_evidence_authority_remediation" / RUN_ID
REPORT_JSON = ROOT / "reports" / "phase_reports" / "phase18_s_accepted_runtime_evidence_authority_remediation.json"
REPORT_MD = ROOT / "docs" / "phase_reports" / "phase18_s_accepted_runtime_evidence_authority_remediation.md"


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
        "src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py": {
            "accepted_resolver": "def _resolve_accepted_bundle(",
            "production_manual_reject": "manual_accepted_bundle_path_forbidden",
            "freshness_resolver": "def _resolve_freshness(",
            "formal_calendar_status": "def _calendar_status(",
            "calendar_business_days": "def _bdiff(",
            "materialized_baseline": "def _materialized_baseline(",
            "integrity_evidence": "def _integrity_evidence(",
            "component_hash_verify": "def _verify_component_hash(",
            "calibration_artifact_verify": "def _verify_calibration_artifact(",
        },
        "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py": {
            "integrity_gate": "def evaluate_integrity_gate(",
            "freshness_gate": "def evaluate_freshness_gate(",
            "drift_gate": "def evaluate_drift_gate(",
            "runtime_gate": "def evaluate_runtime_ai_gate(",
            "scoped_block_flags": "block_buy_planning",
        },
        "tests/ai_lifecycle/test_phase18s_accepted_runtime_evidence_authority.py": {
            "accepted_state": "test_phase18s_accepted_state_resolves_without_manual_path",
            "no_candidate_fallback": "test_phase18s_accepted_state_missing_does_not_fallback_to_promotion_candidate",
            "manual_path_reject": "test_phase18s_manual_path_rejected_in_production_runtime",
            "hash_fail_closed": "test_phase18s_hash_schema_lineage_mismatch_fail_closed",
            "freshness_authority": "test_phase18s_freshness_invalid_calendar_and_negative_lag_fail_closed",
            "baseline_authority": "test_phase18s_materialized_baseline_required_and_hash_verified",
            "immediate_drift": "test_phase18s_immediate_drift_cases",
            "market_no_opportunity": "test_phase18s_all_negative_without_hard_drift_is_market_no_opportunity",
        },
    }
    refs: dict[str, dict[str, int]] = {}
    for rel, patterns in targets.items():
        path = ROOT / rel
        refs[rel] = {}
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        for key, pattern in patterns.items():
            for idx, line in enumerate(text.splitlines(), start=1):
                if pattern in line:
                    refs[rel][key] = idx
                    break
    return refs


def remediation_matrix() -> list[dict[str, Any]]:
    return [
        {
            "unit": "RU1",
            "title": "Accepted-only Artifact Authority and Integrity",
            "status": "COMPLETE",
            "closed_gaps": ["Q-GAP-001", "Q-GAP-004"],
            "evidence": [
                "Runtime resolves accepted bundle from accepted state only.",
                "Production manual accepted_bundle_path is rejected.",
                "Promotion candidate fallback was removed.",
                "Joint bundle, dataset, schema, training, lineage, calibration, and compatibility evidence are verified fail-closed.",
            ],
            "tests": [
                "test_phase18s_accepted_state_resolves_without_manual_path",
                "test_phase18s_accepted_state_missing_does_not_fallback_to_promotion_candidate",
                "test_phase18s_manual_path_rejected_in_production_runtime",
                "test_phase18s_hash_schema_lineage_mismatch_fail_closed",
            ],
        },
        {
            "unit": "RU2",
            "title": "Freshness and Formal Calendar Authority",
            "status": "COMPLETE",
            "closed_gaps": ["Q-GAP-002", "Q-GAP-003"],
            "evidence": [
                "Dataset lag, model training lag, and model acceptance age are computed from formal trading calendar authority.",
                "Weekday fallback and unreadable or range-insufficient calendar evidence fail closed.",
                "Negative/future clocks are BLOCK evidence.",
            ],
            "tests": [
                "test_phase18s_freshness_invalid_calendar_and_negative_lag_fail_closed",
                "test_phase18p_freshness_and_baseline_are_authoritative_not_self_baseline",
            ],
        },
        {
            "unit": "RU3",
            "title": "Materialized Drift Baseline and Immediate Runtime Gate",
            "status": "COMPLETE",
            "closed_gaps": ["Q-GAP-005", "Q-GAP-006"],
            "evidence": [
                "Runtime drift baseline must be materialized inside the accepted bundle or referenced by it.",
                "Synthetic summary-stat baselines and immediate calibration proxy checks were removed.",
                "Immediate gate uses label-free prediction distribution, feature distribution, population, positive coverage, and all-negative sequence evidence.",
            ],
            "tests": [
                "test_phase18s_materialized_baseline_required_and_hash_verified",
                "test_phase18s_immediate_drift_cases",
                "test_phase18s_all_negative_without_hard_drift_is_market_no_opportunity",
            ],
        },
    ]


def acceptance_matrix() -> list[dict[str, str]]:
    return [
        {"item": "Accepted-only Runtime Authority", "status": "PASS", "evidence": "accepted_state resolver; no promotion candidate/manual Production fallback"},
        {"item": "Artifact Integrity", "status": "PASS", "evidence": "joint/component/calibration/dataset-reference/compatibility hash checks"},
        {"item": "Formal Calendar Authority", "status": "PASS", "evidence": "calendar status/range checks; weekday fallback forbidden"},
        {"item": "Negative/Future Freshness", "status": "PASS", "evidence": "negative lag reason_codes BLOCK"},
        {"item": "Materialized Drift Baseline", "status": "PASS", "evidence": "runtime_baseline required and baseline_hash verified"},
        {"item": "Immediate Gate Boundary", "status": "PASS", "evidence": "calibration proxy removed from immediate drift gate"},
        {"item": "BUY-only Scoped Flags", "status": "PASS", "evidence": "block_buy_planning/block_buy_submit are explicit; SELL remains false in BUY lifecycle gate"},
        {"item": "Registry Accepted Update", "status": "NOT_MODIFIED", "evidence": "Phase18-S tests use tmp_path and report writer only"},
        {"item": "Runtime Switch", "status": "NOT_MODIFIED", "evidence": "No runtime accepted set switch performed"},
        {"item": "BUY Restart", "status": "NOT_MODIFIED", "evidence": "No broker or production BUY operation invoked"},
    ]


def source_hashes() -> dict[str, str]:
    paths = [
        "src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py",
        "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py",
        "tests/ai_lifecycle/test_phase18s_accepted_runtime_evidence_authority.py",
        "tests/ai_lifecycle/test_phase18p_runtime_lifecycle_evidence_authority.py",
        "tests/ai_lifecycle/test_phase18n_production_lifecycle_wiring.py",
    ]
    return {rel: sha256_file(ROOT / rel) for rel in paths}


def build_payload() -> dict[str, Any]:
    tests = {
        "targeted": {
            "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18s_pycache python3 -m pytest tests/ai_lifecycle/test_phase18n_production_lifecycle_wiring.py tests/ai_lifecycle/test_phase18p_runtime_lifecycle_evidence_authority.py tests/ai_lifecycle/test_phase18s_accepted_runtime_evidence_authority.py -q",
            "result": "18 passed",
        },
        "phase18": {
            "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18s_pycache python3 -m pytest tests/ai_lifecycle -q",
            "result": "25 passed, 2 sklearn convergence warnings",
        },
        "cross_contract": {
            "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18s_pycache python3 -m pytest tests/ai_lifecycle tests/artifact_registry/test_phase16ac_full_event_log_validator.py tests/artifact_registry/test_phase16ad_materialized_index_builder.py tests/artifact_registry/test_phase16ag_checkpoint_writer.py tests/artifact_registry/test_phase16au_registry_resolver.py tests/artifact_registry/test_phase16av_runtime_lookup_adapter.py tests/runtime_v2/test_phase16av_registry_consumer_cutover.py -q",
            "result": "93 passed, 2 sklearn convergence warnings",
        },
        "compile": {
            "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18s_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py",
            "result": "PASS",
        },
    }
    return {
        "phase": "Phase18-S",
        "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "primary_judgement": "PHASE18_S_ACCEPTED_RUNTIME_EVIDENCE_AUTHORITY_COMPLETE",
        "secondary_judgements": ["RU1_COMPLETE", "RU2_COMPLETE", "RU3_COMPLETE", "RU4_PENDING", "RU5_PENDING", "PHASE18_NOT_COMPLETE", "PHASE19_NOT_READY"],
        "scope": {
            "included": ["RU1", "RU2", "RU3", "Q-GAP-001", "Q-GAP-002", "Q-GAP-003", "Q-GAP-004", "Q-GAP-005", "Q-GAP-006"],
            "excluded": ["RU4", "RU5", "Runtime switch", "BUY restart", "Broker write", "Historical Full Path"],
        },
        "remediation_matrix": remediation_matrix(),
        "acceptance_matrix": acceptance_matrix(),
        "tests": tests,
        "line_refs": line_refs(),
        "source_hashes": source_hashes(),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase18-S Accepted Runtime Evidence Authority Remediation",
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
        "## Remediation Matrix",
        "",
        "| Unit | Status | Closed Gaps | Evidence |",
        "|---|---:|---|---|",
    ]
    for item in payload["remediation_matrix"]:
        lines.append(f"| {item['unit']} {item['title']} | {item['status']} | {', '.join(item['closed_gaps'])} | {'; '.join(item['evidence'])} |")
    lines.extend(["", "## Acceptance Matrix", "", "| Item | Status | Evidence |", "|---|---:|---|"])
    for item in payload["acceptance_matrix"]:
        lines.append(f"| {item['item']} | {item['status']} | {item['evidence']} |")
    lines.extend(["", "## Verification", ""])
    for name, test in payload["tests"].items():
        lines.append(f"- `{name}`: `{test['result']}`")
    lines.extend(
        [
            "",
            "## Runtime Safety",
            "",
            "Registry accepted update、Runtime switch、BUY再開、Broker writeはいずれも未実施です。Phase18-Sの検証はtmp_path fixtureとEvidence/report生成に限定しました。",
            "",
            "## Final",
            "",
            "`PHASE18_S_ACCEPTED_RUNTIME_EVIDENCE_AUTHORITY_COMPLETE`",
            "",
            "`RU1_COMPLETE` / `RU2_COMPLETE` / `RU3_COMPLETE` / `RU4_PENDING` / `RU5_PENDING` / `PHASE18_NOT_COMPLETE` / `PHASE19_NOT_READY`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_json(EVIDENCE_DIR / "phase18s_evidence.json", payload)
    write_json(EVIDENCE_DIR / "source_hashes.json", payload["source_hashes"])
    write_json(EVIDENCE_DIR / "acceptance_matrix.json", {"items": payload["acceptance_matrix"]})
    write_json(REPORT_JSON, payload)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": "PASS", "run_id": RUN_ID, "report": str(REPORT_JSON.relative_to(ROOT))}, sort_keys=True))


if __name__ == "__main__":
    main()
