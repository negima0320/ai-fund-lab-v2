from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.ai_lifecycle_gates import evaluate_runtime_ai_gate
from ai_fund_lab_v2.runtime_v2.lifecycle_evidence import (
    _resolve_accepted_bundle_path,
    build_runtime_lifecycle_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "phase18q-final-independent-closure-review-20260717T000000Z"
EVIDENCE_DIR = ROOT / "reports" / "phase18_q_final_independent_closure_review" / RUN_ID
REPORT_JSON = ROOT / "reports" / "phase_reports" / "phase18_q_final_independent_closure_review.json"
REPORT_MD = ROOT / "docs" / "phase_reports" / "phase18_q_final_independent_closure_review.md"
REGISTRY_LOG = ROOT / ".runtime" / "artifact_registry" / "events" / "registry_events.jsonl"
PROMOTION_BUNDLE = ROOT / ".runtime" / "artifact_registry" / "promotion_candidates" / "transactions" / "promotion-tx-phase18i-1081babc49b5d26b" / "atomic_buy_ai_bundle.json"


def _sha256(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def _rg(pattern: str, *paths: str) -> list[dict[str, Any]]:
    cmd = ["rg", "-n", pattern, *paths]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    rows: list[dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3:
            rows.append({"path": parts[0], "line": int(parts[1]), "text": parts[2]})
    return rows


def _count_registry_events() -> int:
    if not REGISTRY_LOG.exists():
        return 0
    return sum(1 for _ in REGISTRY_LOG.open("r", encoding="utf-8"))


def _line_map(path: str, patterns: dict[str, str]) -> dict[str, int]:
    text = (ROOT / path).read_text(encoding="utf-8")
    out: dict[str, int] = {}
    for name, pattern in patterns.items():
        for idx, line in enumerate(text.splitlines(), start=1):
            if re.search(pattern, line):
                out[name] = idx
                break
    return out


def _sample_payload(scores: list[float], *, candidate_count: int = 50) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate_rows = [{"symbol": f"T{i:04d}", "candidate_score": float(i % 10) / 10.0} for i in range(candidate_count)]
    rankings = [
        {
            "symbol": f"T{i:04d}",
            "rank": i + 1,
            "opportunity_score": float(score),
            "expected_edge_score": float(score),
            "artifact_path": "phase18q://current_window",
        }
        for i, score in enumerate(scores)
    ]
    return (
        {"status": "PASS", "rows": candidate_rows, "artifact_path": "phase18q://candidate"},
        {"status": "PASS", "rankings": rankings, "artifact_path": "phase18q://opportunity"},
    )


def _gate_cases() -> dict[str, Any]:
    fresh = {
        "dataset_lag_business_days": 1,
        "model_training_lag_business_days": 1,
        "model_acceptance_age_business_days": 1,
    }
    baseline_scores = [0.01, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.14, 0.16, 0.18]
    baseline_features = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    base = {
        "baseline_identity": "accepted-baseline",
        "current_window_identity": "runtime-current",
        "evidence_ref": "phase18q://gate",
        "baseline_prediction_scores": baseline_scores,
        "baseline_feature_values": baseline_features,
        "baseline_positive_coverage": 1.0,
        "baseline_candidate_population": 50,
        "baseline_calibration_error": 0.02,
    }

    cases = {
        "healthy_current": {
            "freshness": fresh,
            "drift": base
            | {
                "current_prediction_scores": baseline_scores,
                "current_feature_values": baseline_features,
                "current_positive_coverage": 1.0,
                "current_candidate_population": 50,
                "all_negative_consecutive_business_days": 0,
                "current_calibration_error": 0.02,
            },
        },
        "market_no_opportunity": {
            "freshness": fresh,
            "drift": {
                **base,
                "baseline_prediction_scores": [-0.01, -0.02, -0.03, -0.04, -0.05, -0.06, -0.07, -0.08, -0.09, -0.10],
                "baseline_positive_coverage": 0.0,
            }
            | {
                "current_prediction_scores": [-0.01, -0.02, -0.03, -0.04, -0.05, -0.06, -0.07, -0.08, -0.09, -0.10],
                "current_feature_values": baseline_features,
                "current_positive_coverage": 0.0,
                "current_candidate_population": 50,
                "all_negative_consecutive_business_days": 1,
                "current_calibration_error": 0.02,
            },
        },
        "hard_drift": {
            "freshness": fresh,
            "drift": base
            | {
                "current_prediction_scores": [0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99, 1.0],
                "current_feature_values": [9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 10.0],
                "current_positive_coverage": 1.0,
                "current_candidate_population": 5,
                "all_negative_consecutive_business_days": 0,
                "current_calibration_error": 0.40,
            },
        },
        "missing_baseline": {
            "freshness": fresh,
            "drift": {
                "baseline_identity": "",
                "current_window_identity": "runtime-current",
                "baseline_prediction_scores": [],
                "current_prediction_scores": baseline_scores,
                "baseline_feature_values": [],
                "current_feature_values": baseline_features,
                "baseline_positive_coverage": None,
                "current_positive_coverage": 1.0,
                "baseline_candidate_population": None,
                "current_candidate_population": 50,
                "all_negative_consecutive_business_days": 0,
                "baseline_calibration_error": None,
                "current_calibration_error": 0.02,
            },
        },
        "freshness_stale": {
            "freshness": {
                "dataset_lag_business_days": 21,
                "model_training_lag_business_days": 21,
                "model_acceptance_age_business_days": 121,
            },
            "drift": base
            | {
                "current_prediction_scores": baseline_scores,
                "current_feature_values": baseline_features,
                "current_positive_coverage": 1.0,
                "current_candidate_population": 50,
                "all_negative_consecutive_business_days": 0,
                "current_calibration_error": 0.02,
            },
        },
    }
    out: dict[str, Any] = {}
    for name, evidence in cases.items():
        result = evaluate_runtime_ai_gate(evidence).to_dict()
        out[name] = {
            "decision": result["decision"],
            "classification": result["classification"],
            "block_buy": result["block_buy"],
            "block_sell": result["block_sell"],
            "block_submit": result["block_submit"],
            "evidence": result["evidence"],
        }
    return out


def _runtime_evidence_checks() -> dict[str, Any]:
    resolved = _resolve_accepted_bundle_path(ROOT / ".runtime", None)
    explicit = PROMOTION_BUNDLE if PROMOTION_BUNDLE.exists() else None
    candidate_payload, opportunity_payload = _sample_payload([0.01, 0.02, 0.03, 0.04, 0.05])
    evidence = build_runtime_lifecycle_evidence(
        runtime_root=ROOT / ".runtime",
        business_date="2026-07-17",
        feature_date="2026-07-17",
        runtime_id="phase18q-independent",
        candidate_payload=candidate_payload,
        opportunity_payload=opportunity_payload,
        accepted_bundle_path=explicit,
    )
    default_evidence = build_runtime_lifecycle_evidence(
        runtime_root=ROOT / ".runtime",
        business_date="2026-07-17",
        feature_date="2026-07-17",
        runtime_id="phase18q-default-resolution",
        candidate_payload=candidate_payload,
        opportunity_payload=opportunity_payload,
    )
    freshness = evidence.freshness_evidence
    return {
        "runtime_state_accepted_bundle_exists": (ROOT / ".runtime" / "runtime_state" / "accepted_buy_ai_bundle.json").exists(),
        "default_resolved_bundle_path": str(resolved) if resolved else "",
        "default_resolution_is_promotion_candidate": bool(resolved and "promotion_candidates" in str(resolved)),
        "explicit_promotion_candidate_evidence": evidence.to_dict(),
        "default_resolution_evidence": default_evidence.to_dict(),
        "freshness_hand_check": {
            "label_safe_cutoff": freshness.get("label_safe_cutoff"),
            "training_dataset_max_date": freshness.get("training_dataset_max_date"),
            "model_training_cutoff": freshness.get("model_training_cutoff"),
            "model_training_lag_business_days": freshness.get("model_training_lag_business_days"),
            "negative_model_training_lag_treated_as_pass": bool(
                isinstance(freshness.get("model_training_lag_business_days"), int)
                and int(freshness.get("model_training_lag_business_days")) < 0
                and freshness.get("status") == "PASS"
            ),
            "trading_calendar_ref": freshness.get("trading_calendar_ref"),
            "trading_calendar_identity": freshness.get("trading_calendar_identity"),
        },
        "integrity_check": evidence.integrity_evidence,
    }


def _hard_code_audit() -> dict[str, Any]:
    rows = _rg(
        "freshness = 0|dataset_lag_business_days.*0|model_training_lag_business_days.*0|model_acceptance_age_business_days.*0|baseline = current|accepted_runtime_artifact_current_window_baseline|placeholder calibration|forced HEALTHY|forced PASS|20260717T000000Z|phase18p-runtime-lifecycle-evidence-authority|candidate_dataset_c8de026d3ea8aa4d|opportunity_dataset_fbadc8091a31486d|candidate_training_da0855d123ed1bed|opportunity_training_phase18h_1081babc49b5d26b|/Users/negishi|2026-07-17",
        "src",
        "scripts",
        "tests",
        "docs/phase_reports",
        "docs/01_requirements/phase_roadmap.md",
    )
    classified: list[dict[str, Any]] = []
    for row in rows:
        path = row["path"]
        if path.startswith("tests/"):
            category = "TEST_FIXTURE_ONLY"
        elif path.startswith("docs/"):
            category = "REPORT_EVIDENCE_ONLY"
        elif path.startswith("scripts/phase18"):
            category = "REPORT_EVIDENCE_ONLY"
        elif path.startswith("src/ai_fund_lab_v2/ai_lifecycle/") and "CREATED_AT" in row["text"]:
            category = "PRODUCTION_HARDCODE_REVIEW_REQUIRED"
        else:
            category = "REVIEW_REQUIRED"
        classified.append(row | {"classification": category})
    violations = [row for row in classified if row["classification"] in {"PRODUCTION_HARDCODE_VIOLATION", "PRODUCTION_HARDCODE_REVIEW_REQUIRED"}]
    return {
        "total_matches": len(classified),
        "production_review_required_matches": violations,
        "sample": classified[:80],
    }


def _gap_inventory() -> list[dict[str, Any]]:
    return [
        {
            "id": "Q-GAP-001",
            "category": "REGISTRY_AUTHORITY_GAP",
            "severity": "CRITICAL",
            "title": "Runtime accepted bundle resolver falls back to latest Promotion Candidate",
            "affected_files": ["src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py"],
            "evidence": "lines 158-183 resolve missing accepted bundle to .runtime/artifact_registry/promotion_candidates/transactions/*/atomic_buy_ai_bundle.json",
            "runtime_impact": "Normal BUY AI lifecycle evidence can consume a Promotion Candidate when no accepted bundle state exists.",
            "registry_impact": "Promotion Candidate boundary is bypassed without Registry accepted event.",
            "recommended_remediation": "Remove Promotion Candidate fallback from production resolution; require Registry accepted authority or explicit isolated review input that cannot be used by normal Runtime.",
        },
        {
            "id": "Q-GAP-002",
            "category": "FRESHNESS_AUTHORITY_GAP",
            "severity": "HIGH",
            "title": "Negative model training lag is treated as PASS",
            "affected_files": ["src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py", "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py"],
            "evidence": "_model_training_cutoff falls back to training_metadata.created_at; gate checks only lag greater than threshold.",
            "runtime_impact": "Future-dated training cutoff relative to label-safe cutoff is not fail-closed.",
            "registry_impact": "Accepted freshness evidence can look healthy despite inconsistent authority dates.",
            "recommended_remediation": "Resolve true model_training_cutoff from training/data authority and classify negative lag/future dates as BLOCK or REVIEW_REQUIRED.",
        },
        {
            "id": "Q-GAP-003",
            "category": "FRESHNESS_AUTHORITY_GAP",
            "severity": "HIGH",
            "title": "Formal trading calendar absence silently falls back to weekdays",
            "affected_files": ["src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py"],
            "evidence": "_load_trading_calendar returns [] for missing/unreadable refs; _bdiff then calls business_days_between without adding REVIEW_REQUIRED reason.",
            "runtime_impact": "Business-day clocks can PASS without formal calendar authority.",
            "registry_impact": "Accepted artifact metadata source authority is not enforced.",
            "recommended_remediation": "Require readable formal calendar from accepted metadata and emit fail-closed evidence when unavailable.",
        },
        {
            "id": "Q-GAP-004",
            "category": "ARTIFACT_EVIDENCE_GAP",
            "severity": "HIGH",
            "title": "Integrity evidence records hashes but does not verify bundle references, schema, lineage, or expected hash",
            "affected_files": ["src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py"],
            "evidence": "_integrity_evidence returns PASS when JSON loads; no comparison of content_hash to joint_bundle_hash/hash_manifest or dataset/training hashes.",
            "runtime_impact": "Accepted artifact hash mismatch case is not independently blocked by Runtime evidence authority.",
            "registry_impact": "Registry authority can be bypassed by a readable but inconsistent bundle file.",
            "recommended_remediation": "Verify joint bundle hash, dataset/training bundle hashes, schema hashes, lineage refs, and Candidate/Opportunity compatibility before PASS.",
        },
        {
            "id": "Q-GAP-005",
            "category": "DRIFT_BASELINE_GAP",
            "severity": "HIGH",
            "title": "Accepted drift baseline uses synthetic samples reconstructed from summary stats",
            "affected_files": ["src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py"],
            "evidence": "_sample_from_stats fabricates prediction/feature values for PSI instead of using materialized accepted baseline distributions.",
            "runtime_impact": "Quantitative drift gate may compare current evidence against generated proxy distributions.",
            "registry_impact": "Accepted Atomic BUY AI Bundle baseline identity does not fully prove source distribution authority.",
            "recommended_remediation": "Materialize accepted baseline arrays/histograms in the bundle and verify their hashes before gate use.",
        },
        {
            "id": "Q-GAP-006",
            "category": "RUNTIME_INTEGRATION_GAP",
            "severity": "HIGH",
            "title": "Daily hard gate uses calibration_error_delta without delayed labels",
            "affected_files": ["src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py", "src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py"],
            "evidence": "evaluate_drift_gate can BLOCK on calibration_error_delta; current calibration is a score-only proxy.",
            "runtime_impact": "A delayed-outcome monitoring metric can affect immediate BUY gate with proxy evidence.",
            "registry_impact": "Runtime acceptance semantics differ from the delayed monitoring boundary.",
            "recommended_remediation": "Separate immediate calibration-compatible score evidence from delayed realized calibration monitoring; do not hard-block daily BUY on realized calibration error without labels.",
        },
        {
            "id": "Q-GAP-007",
            "category": "SELL_CONTINUITY_GAP",
            "severity": "HIGH",
            "title": "BUY BLOCK / SELL continuity is recorded but not proven through downstream Runtime stages",
            "affected_files": ["src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py", "src/ai_fund_lab_v2/runtime_v2/lifecycle_sell_continuity.py"],
            "evidence": "morning job appends buy_lifecycle_sell_continuity then exits BLOCKED/REVIEW_REQUIRED before morning planning; separate sell_planning path is not exercised by this continuity check.",
            "runtime_impact": "SELL continuity remains a control-plane assertion, not an entrypoint-level proof.",
            "registry_impact": "None direct.",
            "recommended_remediation": "Introduce explicit BUY-only block semantics and an integration test proving SELL planning/submit authorization remains reachable under BUY lifecycle block.",
        },
        {
            "id": "Q-GAP-008",
            "category": "ROLLBACK_GAP",
            "severity": "MEDIUM",
            "title": "Rollback restore failure behavior is not proven as CRITICAL fail-closed",
            "affected_files": ["src/ai_fund_lab_v2/ai_lifecycle/rollback_revoke.py"],
            "evidence": "Phase18-P adds restore snapshots, but the review found no explicit restore-failure CRITICAL path in the audited flow.",
            "runtime_impact": "Atomic failure rehearsal is incomplete for restore-failure scenarios.",
            "registry_impact": "Potential partial recovery risk under secondary write failure.",
            "recommended_remediation": "Add restore failure injection and explicit CRITICAL transaction artifact/no accepted mutation guarantee.",
        },
    ]


def _matrix(gaps: list[dict[str, Any]]) -> list[dict[str, str]]:
    high = {gap["id"] for gap in gaps if gap["severity"] in {"CRITICAL", "HIGH"}}
    return [
        {"SoT Requirement": "PIT Dataset Rebuild", "Production Implementation": "Phase18-B/C bundles exist", "Test / Evidence": "Phase reports and bundle files", "Status": "PASS_WITH_REVIEW", "Remaining Work": "No Q blocker found"},
        {"SoT Requirement": "Training / Validation", "Production Implementation": "Phase18-D/H training bundles", "Test / Evidence": "Phase18-H report", "Status": "PASS_WITH_REVIEW", "Remaining Work": "No Registry accepted adoption in Q"},
        {"SoT Requirement": "Promotion Readiness", "Production Implementation": "Phase18-G/H/I reports", "Test / Evidence": "Promotion ready with review", "Status": "PASS_WITH_REVIEW", "Remaining Work": "Operational Utility review remains documented"},
        {"SoT Requirement": "Authority", "Production Implementation": "Authority and Registry operator scripts", "Test / Evidence": "Phase18-I transaction artifact", "Status": "PASS_WITH_REVIEW", "Remaining Work": "Do not use as Runtime accepted authority until fixed"},
        {"SoT Requirement": "Promotion Candidate Boundary", "Production Implementation": "Runtime evidence resolver", "Test / Evidence": "Q-GAP-001", "Status": "CONTRACT_CONFLICT", "Remaining Work": "Remove latest Promotion Candidate fallback"},
        {"SoT Requirement": "Artifact Registry", "Production Implementation": "Phase16 Registry plus Phase18 rollback/revoke", "Test / Evidence": "Regression and Q review", "Status": "PASS_WITH_REVIEW", "Remaining Work": "Restore-failure CRITICAL path"},
        {"SoT Requirement": "Atomic BUY AI Bundle", "Production Implementation": "Phase18-I bundle", "Test / Evidence": "Promotion candidate bundle", "Status": "PASS_WITH_REVIEW", "Remaining Work": "Accepted hash/lineage verification before Runtime use"},
        {"SoT Requirement": "Runtime Discovery", "Production Implementation": "Resolver and runtime artifacts", "Test / Evidence": "Q-GAP-001", "Status": "CONTRACT_CONFLICT", "Remaining Work": "Accepted-only discovery"},
        {"SoT Requirement": "Freshness Authority", "Production Implementation": "lifecycle_evidence freshness resolver", "Test / Evidence": "Q-GAP-002/Q-GAP-003", "Status": "CONTRACT_CONFLICT", "Remaining Work": "Future-date and calendar fail-closed"},
        {"SoT Requirement": "Freshness Gate", "Production Implementation": "evaluate_freshness_gate", "Test / Evidence": "Q gate cases", "Status": "PARTIAL", "Remaining Work": "Negative lag handling"},
        {"SoT Requirement": "Accepted Drift Baseline", "Production Implementation": "summary-stat sampling", "Test / Evidence": "Q-GAP-005", "Status": "PARTIAL", "Remaining Work": "Materialized accepted distributions"},
        {"SoT Requirement": "Runtime Current Evidence", "Production Implementation": "candidate/opportunity runtime payloads", "Test / Evidence": "Q current evidence", "Status": "PASS_WITH_REVIEW", "Remaining Work": "Hash current evidence artifact"},
        {"SoT Requirement": "Quantitative Drift Gate", "Production Implementation": "PSI/coverage/population/all-negative/calibration checks", "Test / Evidence": "Q-GAP-005/Q-GAP-006", "Status": "PARTIAL", "Remaining Work": "Baseline authority and delayed calibration separation"},
        {"SoT Requirement": "Runtime Daily Wiring", "Production Implementation": "morning buy producer invokes lifecycle gate", "Test / Evidence": "producer/CLI audit", "Status": "PASS_WITH_REVIEW", "Remaining Work": "Accepted boundary fix"},
        {"SoT Requirement": "Runtime Decision Contract", "Production Implementation": "block_buy/block_sell/block_submit", "Test / Evidence": "Q gate cases", "Status": "PARTIAL", "Remaining Work": "Separate BUY submit from global submit"},
        {"SoT Requirement": "SELL Continuity", "Production Implementation": "sell continuity stage", "Test / Evidence": "Q-GAP-007", "Status": "PARTIAL", "Remaining Work": "Entrypoint-level SELL path proof"},
        {"SoT Requirement": "Weekly Scheduler", "Production Implementation": "Phase18-N/P scripts", "Test / Evidence": "report review", "Status": "PASS_WITH_REVIEW", "Remaining Work": "No Q blocker found"},
        {"SoT Requirement": "PM Policy Lifecycle", "Production Implementation": "Phase18-N/P lifecycle classification", "Test / Evidence": "report review", "Status": "PASS_WITH_REVIEW", "Remaining Work": "Future acceptance"},
        {"SoT Requirement": "Safety Policy Lifecycle", "Production Implementation": "Phase18-N/P lifecycle classification", "Test / Evidence": "report review", "Status": "PASS_WITH_REVIEW", "Remaining Work": "Future acceptance"},
        {"SoT Requirement": "Future AI Onboarding", "Production Implementation": "classification artifacts", "Test / Evidence": "report review", "Status": "PASS_WITH_REVIEW", "Remaining Work": "Apply to future AIs"},
        {"SoT Requirement": "Rollback / Revoke", "Production Implementation": "rollback_revoke snapshots", "Test / Evidence": "Phase18-P tests", "Status": "PASS_WITH_REVIEW", "Remaining Work": "Restore-failure CRITICAL proof"},
        {"SoT Requirement": "Atomic Failure Restore", "Production Implementation": "failure injection", "Test / Evidence": "Q-GAP-008", "Status": "PARTIAL", "Remaining Work": "Restore failure injection"},
        {"SoT Requirement": "Lifecycle Internal E2E", "Production Implementation": "Not fully proven", "Test / Evidence": "Q review", "Status": "PARTIAL", "Remaining Work": "After gaps fixed"},
        {"SoT Requirement": "Operator Parameterization", "Production Implementation": "Phase scripts still contain fixed IDs; production modules partially parameterized", "Test / Evidence": "hard-code audit", "Status": "PASS_WITH_REVIEW" if not high else "REVIEW_REQUIRED", "Remaining Work": "Move phase constants out of production defaults where needed"},
    ]


def _render_markdown(report: dict[str, Any]) -> str:
    gaps = report["remaining_gaps"]
    lines = [
        "# Phase18-Q Final Independent Closure Review",
        "",
        f"- Run ID: `{RUN_ID}`",
        f"- Primary Judgment: `{report['final_judgment']['primary']}`",
        f"- Secondary Judgment: `{', '.join(report['final_judgment']['secondary'])}`",
        f"- Evidence: `{report['evidence_dir']}`",
        "",
        "## Executive Summary",
        "",
        "Phase18-Q cannot close Phase18. The independent review found one critical Registry Authority gap and multiple high-severity Runtime/Freshness/Drift/SELL continuity gaps. Phase18-P evidence is useful, but it does not prove accepted-only Runtime authority or full SELL continuity.",
        "",
        "## Critical Finding",
        "",
        "- `Q-GAP-001`: Runtime accepted bundle discovery falls back to the latest Promotion Candidate bundle when no accepted runtime state exists. This directly conflicts with the Phase18-Q prohibition on Promotion Candidate Runtime adoption.",
        "",
        "## O-GAP Closure Result",
        "",
        "| Gap | Result | Evidence |",
        "|---|---|---|",
        "| O-GAP-001 Freshness Authority | FAIL | Negative model-training lag and silent calendar fallback remain. |",
        "| O-GAP-002 Accepted Drift Baseline | PARTIAL | Baseline is reconstructed from summary stats and integrity is not fully verified. |",
        "| O-GAP-003 Runtime Decision Contract | PARTIAL | Gate separates MARKET_NO_OPPORTUNITY and MODEL_UNHEALTHY, but `block_submit` remains ambiguous. |",
        "| O-GAP-004 BUY BLOCK / SELL Continuity | PARTIAL | Control-plane sell continuity is recorded; downstream SELL path is not proven. |",
        "",
        "## Promotion Boundary Evidence",
        "",
        f"- `.runtime/runtime_state/accepted_buy_ai_bundle.json` exists: `{report['runtime_evidence']['runtime_state_accepted_bundle_exists']}`",
        f"- Default resolved bundle: `{report['runtime_evidence']['default_resolved_bundle_path']}`",
        f"- Default resolution is Promotion Candidate: `{report['runtime_evidence']['default_resolution_is_promotion_candidate']}`",
        "",
        "## Freshness Evidence",
        "",
        "```json",
        json.dumps(report["runtime_evidence"]["freshness_hand_check"], indent=2, sort_keys=True),
        "```",
        "",
        "## Runtime Dry-run Summary",
        "",
        "| Case | Decision | Classification | block_buy | block_sell | block_submit |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for name, result in report["runtime_gate_cases"].items():
        lines.append(
            f"| {name} | `{result['decision']}` | `{result['classification']}` | `{result['block_buy']}` | `{result['block_sell']}` | `{result['block_submit']}` |"
        )
    lines.extend(
        [
            "",
            "## Test Execution",
            "",
            "- Targeted lifecycle tests: `10 passed in 3.24s`",
            "- Cross-contract regression: `85 passed, 2 warnings in 3.93s`",
            "- Test quality result: PASS does not cover accepted-only Runtime discovery, negative freshness lag fail-closed, formal calendar missing fail-closed, accepted bundle hash mismatch, materialized baseline distribution authority, or end-to-end SELL continuity under BUY block.",
            "",
            "## Design-to-Implementation Matrix",
            "",
            "| SoT Requirement | Production Implementation | Test / Evidence | Status | Remaining Work |",
            "|---|---|---|---|---|",
        ]
    )
    for row in report["design_to_implementation_matrix"]:
        lines.append(
            f"| {row['SoT Requirement']} | {row['Production Implementation']} | {row['Test / Evidence']} | `{row['Status']}` | {row['Remaining Work']} |"
        )
    lines.extend(["", "## Remaining Gaps", ""])
    for gap in gaps:
        lines.extend(
            [
                f"### {gap['id']} - {gap['severity']}",
                "",
                f"- Category: `{gap['category']}`",
                f"- Title: {gap['title']}",
                f"- Evidence: {gap['evidence']}",
                f"- Runtime impact: {gap['runtime_impact']}",
                f"- Registry impact: {gap['registry_impact']}",
                f"- Recommended remediation: {gap['recommended_remediation']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Non-mutation Confirmation",
            "",
            f"- Registry event count before/after: `{report['registry_non_mutation']['event_count_before']}` / `{report['registry_non_mutation']['event_count_after']}`",
            f"- Registry event log hash before/after: `{report['registry_non_mutation']['event_log_hash_before']}` / `{report['registry_non_mutation']['event_log_hash_after']}`",
            "- Runtime switch: not performed",
            "- Runtime submit: not performed",
            "- BUY restart: not performed",
            "- Broker write: not performed",
            "",
            "## Phase18 / Phase19 Judgment",
            "",
            "- Phase18 completion judgment: `PHASE18_NOT_COMPLETE`",
            "- Phase19 readiness judgment: `PHASE19_NOT_READY`",
            "- Final judgment: `PHASE18_Q_CRITICAL_CONTRACT_VIOLATION_DETECTED`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    before_hash = _sha256(REGISTRY_LOG)
    before_count = _count_registry_events()
    line_refs = {
        "lifecycle_evidence": _line_map(
            "src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py",
            {
                "resolve_accepted": r"def _resolve_accepted_bundle_path",
                "latest_promotion_candidate": r"def _latest_promotion_candidate_bundle",
                "model_training_cutoff": r"def _model_training_cutoff",
                "load_trading_calendar": r"def _load_trading_calendar",
                "integrity_evidence": r"def _integrity_evidence",
                "sample_from_stats": r"def _sample_from_stats",
                "current_calibration_proxy": r"def _current_calibration_proxy",
            },
        ),
        "ai_lifecycle_gates": _line_map(
            "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py",
            {
                "freshness_gate": r"def evaluate_freshness_gate",
                "drift_gate": r"def evaluate_drift_gate",
                "block_submit": r"block_submit",
                "calibration_drift": r"calibration_drift",
            },
        ),
        "run_daily_operation": _line_map(
            "src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py",
            {
                "buy_lifecycle_sell_continuity": r"buy_lifecycle_sell_continuity",
                "morning_planning": r"run_morning_ai_planning_pending_pipeline",
            },
        ),
    }
    runtime_evidence = _runtime_evidence_checks()
    gate_cases = _gate_cases()
    hard_code = _hard_code_audit()
    gaps = _gap_inventory()
    after_hash = _sha256(REGISTRY_LOG)
    after_count = _count_registry_events()
    report = {
        "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_dir": str(EVIDENCE_DIR.relative_to(ROOT)),
        "documents_reviewed": [
            "docs/02_architecture/ai_lifecycle_v2.md",
            "docs/02_architecture/runtime_architecture_v2.md",
            "docs/phase_reports/phase18_o_final_independent_ai_lifecycle_v2_conformance_review.md",
            "docs/phase_reports/phase18_p_runtime_lifecycle_evidence_authority_and_atomic_failure_remediation.md",
        ],
        "changed_file_inventory": {
            "src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py": "PRODUCTION_MODULE",
            "src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py": "PRODUCTION_MODULE",
            "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py": "PRODUCTION_MODULE",
            "src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py": "PRODUCTION_OPERATOR",
            "src/ai_fund_lab_v2/ai_lifecycle/rollback_revoke.py": "PRODUCTION_MODULE",
            "tests/ai_lifecycle/test_phase18p_runtime_lifecycle_evidence_authority.py": "TEST",
            "scripts/phase18p_runtime_lifecycle_evidence_authority_and_atomic_failure_remediation.py": "EVIDENCE_WRAPPER",
        },
        "line_references": line_refs,
        "runtime_evidence": runtime_evidence,
        "runtime_gate_cases": gate_cases,
        "hard_code_audit": hard_code,
        "test_execution": {
            "targeted": {
                "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18q_pycache python3 -m pytest tests/ai_lifecycle/test_phase18p_runtime_lifecycle_evidence_authority.py tests/ai_lifecycle/test_phase18n_production_lifecycle_wiring.py -q",
                "result": "10 passed in 3.24s",
                "status": "PASS",
            },
            "cross_contract_regression": {
                "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18q_pycache python3 -m pytest tests/ai_lifecycle tests/artifact_registry/test_phase16ac_full_event_log_validator.py tests/artifact_registry/test_phase16ad_materialized_index_builder.py tests/artifact_registry/test_phase16ag_checkpoint_writer.py tests/artifact_registry/test_phase16au_registry_resolver.py tests/artifact_registry/test_phase16av_runtime_lookup_adapter.py tests/runtime_v2/test_phase16av_registry_consumer_cutover.py -q",
                "result": "85 passed, 2 warnings in 3.93s",
                "status": "PASS_WITH_WARNINGS",
            },
            "test_quality_result": "Regression passes, but the passing suite does not cover accepted-only Runtime discovery, negative freshness lag fail-closed, formal calendar missing fail-closed, accepted bundle hash mismatch, materialized baseline distribution authority, or end-to-end SELL continuity under BUY block.",
        },
        "remaining_gaps": gaps,
        "design_to_implementation_matrix": _matrix(gaps),
        "phase18_completion_judgment": "PHASE18_NOT_COMPLETE",
        "phase19_readiness_judgment": "PHASE19_NOT_READY",
        "final_judgment": {
            "primary": "PHASE18_Q_CRITICAL_CONTRACT_VIOLATION_DETECTED",
            "secondary": ["PHASE18_NOT_COMPLETE", "PHASE19_NOT_READY"],
        },
        "registry_non_mutation": {
            "event_count_before": before_count,
            "event_count_after": after_count,
            "event_log_hash_before": before_hash,
            "event_log_hash_after": after_hash,
            "unchanged": before_count == after_count and before_hash == after_hash,
        },
        "non_execution_confirmation": {
            "production_registry_accepted_state_change": False,
            "promotion_candidate_runtime_adoption_performed_by_phase18q": False,
            "runtime_model_switch": False,
            "runtime_submit": False,
            "buy_restart": False,
            "broker_write": False,
            "historical_runtime_full_path": False,
            "target_feature_bv15_pm_safety_threshold_changes": False,
        },
    }
    _write_json(EVIDENCE_DIR / "independent_review_result.json", report)
    _write_json(REPORT_JSON, report)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(_render_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
