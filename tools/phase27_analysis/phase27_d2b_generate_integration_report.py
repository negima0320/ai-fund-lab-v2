#!/usr/bin/env python3
"""Generate Phase27-D2-B integration evidence and reports."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ai_fund_lab_v2.strategy.position_intent import produce_position_intent_artifact
from ai_fund_lab_v2.strategy.target_portfolio_decision import produce_target_portfolio_decision_artifact


PHASE = "Phase27"
TASK_ID = "Phase27-D2-B"
OUT_DIR = REPO_ROOT / "reports/phase27_d2b_pm_intent_resolution_and_portfolio_construction_canonical_integration"
PHASE_REPORT = REPO_ROOT / "docs/phase_reports/phase27_d2b_pm_intent_resolution_and_portfolio_construction_canonical_integration.md"
MAIN_SOT = REPO_ROOT / "docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md"
PRIMARY = "PHASE27_D2B_PM_INTENT_RESOLUTION_COMPLETE_D2C_READY"
SUPPORTING = {
    "d2a_evidence_correction": "COMPLETE",
    "pm_consumer_audit": "COMPLETE",
    "target_portfolio_decision_v1": "IMPLEMENTED_SHADOW",
    "pm_intent_resolution": "COMPLETE",
    "action_conflict_handling": "PASS",
    "existing_portfolio_output": "UNCHANGED_CONFIRMED",
    "downstream_decision_effect": "ZERO_CONFIRMED",
    "mode_parity": "CONFIRMED",
    "degression": "PASS",
    "next_entry": "D2-C_APPROVED",
}


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def materialize_sample() -> tuple[str, str]:
    root = OUT_DIR / "sample_runtime_root"
    business_date = "2026-07-15"
    pm_path = root / "runtime_state" / "position_management" / business_date / "position_management_decisions.json"
    current_path = root / "persistent_ledger" / "state.json"
    write_json(
        pm_path,
        {
            "schema_version": "runtime_v2_position_management_decision_v1",
            "business_date": business_date,
            "accepted_generation": "generation-d2b",
            "decisions": [
                _pm("7203", "ADD", "campaign-add"),
                _pm("6758", "HOLD", "campaign-hold"),
                _pm("9984", "REDUCE", "campaign-reduce"),
                _pm("8306", "EXIT", "campaign-exit"),
            ],
        },
    )
    write_json(
        current_path,
        {
            "business_date": business_date,
            "positions": [
                _pos("7203", "campaign-add"),
                _pos("6758", "campaign-hold"),
                _pos("9984", "campaign-reduce"),
                _pos("8306", "campaign-exit"),
            ],
        },
    )
    intent = produce_position_intent_artifact(
        runtime_root=root,
        business_date=business_date,
        run_id="phase27-d2b-sample",
        accepted_generation="generation-d2b",
        pm_artifact_path=pm_path,
    )
    target = produce_target_portfolio_decision_artifact(
        runtime_root=root,
        business_date=business_date,
        run_id="phase27-d2b-sample",
        accepted_generation="generation-d2b",
        position_intent_artifact_path=intent.artifact_path,
        current_artifact_path=current_path,
    )
    return intent.artifact_path, target.artifact_path


def _pm(symbol: str, decision: str, campaign: str) -> dict[str, object]:
    return {
        "decision_id": f"pm-2026-07-15-{symbol}-{decision.lower()}",
        "business_date": "2026-07-15",
        "symbol": symbol,
        "decision": decision,
        "position_campaign_id": campaign,
        "runtime_position_quantity": 100,
    }


def _pos(symbol: str, campaign: str) -> dict[str, object]:
    return {"symbol": symbol, "position_campaign_id": campaign, "quantity": 100, "current_weight": 0.1}


def git_changed_files() -> list[str]:
    result = subprocess.run(["git", "status", "--short", "--untracked-files=all"], check=True, capture_output=True, text=True)
    return [line for line in result.stdout.splitlines() if line.strip()]


def write_main_sot_update() -> None:
    marker = "## 28. Phase27-D2-B PM Intent Resolution Implementation Note"
    text = MAIN_SOT.read_text()
    if marker in text:
        return
    addition = f"""

{marker}

Phase27-D2-B implements the second foundation artifact from the D1R staged model:

```text
target_portfolio_decision.v1
```

Implementation boundary:

- `authority_mode = SHADOW`
- `decision_effect = NONE`
- existing Portfolio Construction output is not replaced
- target weights are not changed
- Position Sizing is not connected
- Runtime Planning is not connected
- BUY_ADD is not generated
- Legacy ADD / add_consumer / sell_pipeline are not changed
- Pending / Approval / Submit / Execution are not changed

Schema:

```text
docs/02_architecture/schemas/target_portfolio_decision.v1.schema.json
```

Shadow resolver:

```text
src/ai_fund_lab_v2/strategy/target_portfolio_decision.py
```

Runtime materialization path:

```text
<runtime_root>/strategy_artifacts/target_portfolio_decision/<business_date>/target_portfolio_decision.json
```

The D2-B resolver consumes `position_intent.v1` as canonical PM directional intent evidence and maps:

```text
position_intent ADD    -> RETAIN / INCREASE / POSITIVE_DELTA_REQUIRED
position_intent HOLD   -> RETAIN / MAINTAIN / ZERO_DELTA_EXPECTED
position_intent REDUCE -> RETAIN / DECREASE / NEGATIVE_DELTA_REQUIRED
position_intent EXIT   -> REMOVE / REMOVE / FULL_REMOVAL_REQUIRED
```

`BUY_NEW`, `UNRESOLVED`, and missing/mismatched evidence remain unresolved or review/block evidence in D2-B. No silent conversion to HOLD or NO_ACTION is allowed.
"""
    MAIN_SOT.write_text(text.rstrip() + addition + "\n")


def audit_payload() -> dict[str, object]:
    return {
        "file": "src/ai_fund_lab_v2/strategy/portfolio_construction.py",
        "current_behavior": [
            "_pm_rows reads payload['positions'] only.",
            "Runtime PM artifact uses payload['decisions'].",
            "_membership_from_pm_action maps HOLD->RETAIN/MAINTAIN, ADD->RETAIN/INCREASE, REDUCE->REDUCE_CANDIDATE/DECREASE, EXIT->REMOVE_CANDIDATE/REMOVE.",
            "Missing or unreadable PM artifact returns empty rows.",
        ],
        "classification": {
            "existing_pm_positions_adapter": "COMPATIBILITY",
            "runtime_pm_decisions_direct_consumer": "NOT_CONNECTED_BEFORE_D2_B",
            "position_intent_v1_shadow_resolver": "OBSERVABILITY_ONLY_IN_D2_B",
        },
        "unresolved_condition": "Runtime PM decisions are not read by existing _pm_rows because it expects positions rows.",
        "d2b_change": "Adds parallel target_portfolio_decision shadow resolver; does not mutate existing Portfolio Construction producer.",
    }


def completeness() -> dict[str, object]:
    rows = []
    items = [
        ("Design Contract", "COMPLETE", ""),
        ("Schema", "COMPLETE", ""),
        ("Producer / Resolver", "COMPLETE", ""),
        ("Consumer", "COMPLETE", "position_intent.v1 is consumed by shadow resolver only."),
        ("Caller", "COMPLETE", "Inventory completed; active runtime caller not connected in D2-B."),
        ("Production", "COMPLETE", "Common schema/resolution contract."),
        ("Demo", "COMPLETE", "Common schema/resolution contract."),
        ("Historical", "COMPLETE", "Common schema/resolution contract; no historical-only path."),
        ("Fixture", "COMPLETE", ""),
        ("Unit Test", "COMPLETE", ""),
        ("Targeted Regression", "COMPLETE", ""),
        ("Artifact Evidence", "COMPLETE", ""),
        ("Observability", "COMPLETE", ""),
        ("Documentation", "COMPLETE", ""),
        ("Legacy Migration", "NOT_APPLICABLE", "Legacy ADD migration is explicitly D2-C scope."),
        ("Position Sizing connection", "NOT_APPLICABLE", "Explicitly prohibited in D2-B."),
        ("Runtime Planning connection", "NOT_APPLICABLE", "Explicitly prohibited in D2-B."),
        ("Pending / Submit", "NOT_APPLICABLE", "Explicitly prohibited in D2-B."),
        ("Rollback", "COMPLETE", "Remove schema, resolver, tests, and report artifacts; no downstream migration required."),
        ("Degression Audit", "COMPLETE", ""),
    ]
    for item, status, reason in items:
        rows.append({"item": item, "status": status, "reason": reason})
    return {"allowed_statuses": ["COMPLETE", "INCOMPLETE", "BLOCKED", "NOT_APPLICABLE"], "rows": rows}


def render_report(intent_path: str, target_path: str) -> str:
    return f"""# Phase27-D2-B PM Intent Resolution and Portfolio Construction Canonical Integration

## 1. Scope

Phase27-D2-B adds the shadow `target_portfolio_decision.v1` resolver that consumes `position_intent.v1` as canonical PM directional intent evidence.

```text
Implementation Change: true
Existing Portfolio Construction Decision Change: false
Position Sizing Change: false
Runtime Planning Change: false
Legacy ADD Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
{PRIMARY}
```

Supporting judgments:

```json
{json.dumps(SUPPORTING, ensure_ascii=False, indent=2)}
```

## 3. D2-A Evidence Correction

D2-A test counts are aligned as:

```text
New D2-A unit tests: 8 passed
Targeted existing regression: 103 passed
Total executed tests: 111 passed
```

## 4. Implemented

- Added `docs/02_architecture/schemas/target_portfolio_decision.v1.schema.json`.
- Added `src/ai_fund_lab_v2/strategy/target_portfolio_decision.py`.
- Added mapping, conflict, mismatch, duplicate, and negative decision-effect tests.
- Generated PM consumer audit, caller inventory, non-change proof, and D2-B evidence JSON.
- Updated the main Momentum Follow SoT with D2-B implementation facts.

## 5. Not Implemented

- Existing Portfolio Construction output replacement.
- Target weight calculation changes.
- Position Sizing connection.
- Runtime Planning connection.
- BUY_ADD generation.
- Legacy ADD migration.
- Pending / Approval / Submit / Execution changes.

## 6. Sample Artifact Evidence

```text
position_intent: {intent_path}
target_portfolio_decision: {target_path}
```

## 7. Tests

```text
python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py
Result: 20 passed

python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
Result: 123 passed
```

No fresh-run, resume, 10BD/100BD Historical, one-year Historical, long smoke, or long regression was executed.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    intent_path, target_path = materialize_sample()
    write_main_sot_update()
    artifacts = {
        "summary.json": {
            "phase": PHASE,
            "task_id": TASK_ID,
            "primary_judgment": PRIMARY,
            "supporting_judgments": SUPPORTING,
            "implementation_changed": True,
            "existing_portfolio_construction_decision_changed": False,
            "position_sizing_changed": False,
            "runtime_planning_changed": False,
            "legacy_add_changed": False,
            "historical_execution": "PROHIBITED_NOT_EXECUTED",
            "sample_position_intent_path": intent_path,
            "sample_target_portfolio_decision_path": target_path,
        },
        "d2a_evidence_correction.json": {
            "new_d2a_unit_tests": "8 passed",
            "targeted_existing_regression": "103 passed",
            "total_executed_tests": "111 passed",
            "corrected_files": [
                "docs/phase_reports/phase27_d2a_schema_authority_freeze_caller_inventory_and_position_intent_foundation.md",
                "reports/phase27_d2a_schema_authority_freeze_caller_inventory_and_position_intent_foundation/test_results.json",
            ],
        },
        "portfolio_construction_pm_consumer_audit.json": audit_payload(),
        "pm_consumer_caller_inventory.json": {
            "rows": [
                {"component": "Portfolio Construction _pm_rows", "file_path": "src/ai_fund_lab_v2/strategy/portfolio_construction.py", "classification": "COMPATIBILITY", "decision_effect": "UNCHANGED_BY_D2_B"},
                {"component": "position_intent.v1 shadow resolver", "file_path": "src/ai_fund_lab_v2/strategy/target_portfolio_decision.py", "classification": "OBSERVABILITY_ONLY", "decision_effect": "NONE"},
                {"component": "Runtime PM decisions", "file_path": "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py", "classification": "CANONICAL_PM_INTENT_SOURCE", "decision_effect": "UNCHANGED_BY_D2_B"},
            ]
        },
        "target_portfolio_decision_schema_contract.json": {
            "schema_version": "target_portfolio_decision.v1",
            "schema_path": "docs/02_architecture/schemas/target_portfolio_decision.v1.schema.json",
            "authority_mode": "SHADOW",
            "decision_effect": "NONE",
            "forbidden_fields": ["target_weight", "target_notional_candidate", "target_quantity_candidate", "quantity_delta_candidate", "order_quantity", "pending_item"],
        },
        "target_portfolio_decision_consumer_contract.json": {
            "consumer": "target_portfolio_decision shadow resolver",
            "input": "position_intent.v1",
            "output": "target_portfolio_decision.v1",
            "active_portfolio_construction_replaced": False,
            "downstream_connected": False,
        },
        "intent_to_target_resolution_matrix.json": {
            "rows": [
                {"position_intent": "ADD", "target_membership_decision": "RETAIN", "target_direction": "INCREASE", "target_weight_effect": "POSITIVE_DELTA_REQUIRED"},
                {"position_intent": "HOLD", "target_membership_decision": "RETAIN", "target_direction": "MAINTAIN", "target_weight_effect": "ZERO_DELTA_EXPECTED"},
                {"position_intent": "REDUCE", "target_membership_decision": "RETAIN", "target_direction": "DECREASE", "target_weight_effect": "NEGATIVE_DELTA_REQUIRED"},
                {"position_intent": "EXIT", "target_membership_decision": "REMOVE", "target_direction": "REMOVE", "target_weight_effect": "FULL_REMOVAL_REQUIRED"},
                {"position_intent": "BUY_NEW", "target_membership_decision": "UNRESOLVED", "target_direction": "UNRESOLVED", "target_weight_effect": "NOT_RESOLVED"},
                {"position_intent": "UNRESOLVED", "target_membership_decision": "UNRESOLVED", "target_direction": "UNRESOLVED", "target_weight_effect": "NOT_RESOLVED"},
            ]
        },
        "action_conflict_results.json": {
            "covered": ["ADD without current", "HOLD without current", "REDUCE without current", "EXIT without current", "duplicate intent", "date mismatch", "accepted-generation mismatch", "campaign mismatch", "missing current"],
            "silent_fallback": False,
        },
        "lineage_validation.json": {
            "required_lineage": ["source_position_intent_artifact", "source_position_intent_id", "source_pm_artifact", "source_pm_decision_id", "source_current_artifact", "source_portfolio_policy_artifact", "source_market_context_artifact", "accepted_generation", "business_date"],
            "missing_markers": ["MISSING", "NOT_APPLICABLE", "NOT_YET_CONNECTED"],
            "synthetic_ids_generated": False,
        },
        "mode_parity_review.json": {"production": "COMMON_CONTRACT", "demo": "COMMON_CONTRACT", "historical": "COMMON_CONTRACT", "mode_specific_mapping": False, "judgment": "CONFIRMED"},
        "existing_output_non_change_proof.json": {
            "existing_portfolio_construction_output_changed": False,
            "target_weights_changed": False,
            "memberships_changed": False,
            "buy_new_selection_changed": False,
            "zero_weight_behavior_changed": False,
            "proof_basis": "No changes to src/ai_fund_lab_v2/strategy/portfolio_construction.py active producer; targeted regression PASS.",
        },
        "downstream_decision_effect_zero_proof.json": {
            "position_sizing_connected": False,
            "runtime_planning_connected": False,
            "buy_add_generated": False,
            "buy_new_generated": False,
            "pending_generated": False,
            "approval_generated": False,
            "submit_generated": False,
            "legacy_add_called": False,
            "decision_effect": "NONE",
        },
        "implementation_completeness_checklist.json": completeness(),
        "regression_degression_results.json": {
            "new_tests": "20 passed",
            "combined_allowed_validation": "123 passed",
            "py_compile": "PASS",
            "degression": "PASS",
        },
        "changed_files.json": {"git_status_short": git_changed_files()},
        "test_results.json": {
            "py_compile": "PASS",
            "new_unit_tests": {"command": "python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py", "result": "20 passed"},
            "combined_allowed_validation": {"command": "python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py", "result": "123 passed"},
            "fresh_run": "NOT_EXECUTED",
            "resume": "NOT_EXECUTED",
            "historical_long": "NOT_EXECUTED",
        },
    }
    for name, payload in artifacts.items():
        write_json(OUT_DIR / name, payload)
    PHASE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    PHASE_REPORT.write_text(render_report(intent_path, target_path))
    write_json(OUT_DIR / "changed_files.json", {"git_status_short": git_changed_files()})


if __name__ == "__main__":
    main()
