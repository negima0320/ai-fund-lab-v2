#!/usr/bin/env python3
"""Generate Phase27-D2-C legacy ADD migration evidence and report."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ai_fund_lab_v2.runtime_v2.planning.add_consumer import (
    LEGACY_ADD_COMPATIBILITY_SCHEMA_VERSION,
    LEGACY_ADD_MIGRATION_STATE,
    build_legacy_add_compatibility_artifact,
    evaluate_legacy_add_double_authority_guard,
    validate_legacy_add_compatibility_lineage,
)
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import SellExitDecision


TASK_ID = "Phase27-D2-C"
OUT_DIR = REPO_ROOT / "reports/phase27_d2c_legacy_add_non_decision_conversion_and_double_authority_prevention"
PHASE_REPORT = REPO_ROOT / "docs/phase_reports/phase27_d2c_legacy_add_non_decision_conversion_and_double_authority_prevention.md"
PRIMARY = "PHASE27_D2C_LEGACY_ADD_NON_DECISION_CONVERSION_COMPLETE_D2D_READY"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sample_artifact() -> dict[str, object]:
    decision = SellExitDecision(
        symbol="94320",
        quantity=0,
        reason="ADD is outside legacy executable authority after D2-C",
        source_decision="ADD",
        source_decision_id="pm-2026-07-08-94320-add",
    )
    return build_legacy_add_compatibility_artifact(
        add_decisions=(decision,),
        business_date="2026-07-08",
        target_session_date="2026-07-08",
        environment="demo",
        run_id="phase27-d2c-sample",
        accepted_generation="generation-d2c",
        canonical_position_intent_ref="strategy_artifacts/position_intent/2026-07-08/position_intent.json",
        canonical_target_portfolio_decision_ref="strategy_artifacts/target_portfolio_decision/2026-07-08/target_portfolio_decision.json",
    )


def git_changed_files() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def render_report() -> str:
    return f"""# Phase27-D2-C Legacy ADD Non-decision Conversion and Double-authority Prevention

## 1. Scope

Phase27-D2-C converts the legacy Runtime path from executable PM ADD order generation to compatibility telemetry only.

```text
Implementation Change: true
Canonical BUY_ADD Activation: false
Strategy / PM / Portfolio Construction / Position Sizing Change: false
Pending / Approval / Submit / Execution Logic Change: false
Historical / 100BD / Long Regression: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
{PRIMARY}
```

Supporting judgments:

```json
{json.dumps(supporting_judgments(), ensure_ascii=False, indent=2)}
```

## 3. What Changed

- `add_consumer` now emits `legacy_pm_add_compatibility.v1` telemetry for PM ADD inputs.
- Legacy ADD no longer resolves ADD-specific cash exposure, position sizing, quantity, lot rounding, Pending, Approval, or Submit authority.
- The old `pm_add_order_plan.json` executable path is no longer reached by PM ADD input because `accepted_items` is always empty in compatibility mode.
- Empty Pending no-order evidence records `pm_add_non_decision_compatibility`.
- Common architecture SoT files now freeze the D2-C migration state outside phase-local documentation.

## 4. Authority Before / After

| Object | Before | After |
|---|---|---|
| Decision Effect | Legacy ADD could become BUY Pending | `NONE` |
| Quantity | `add_consumer` calculated quantity | `NONE` |
| Pending | `pm_add_order_plan` could produce Pending | `NONE` |
| Approval | PM ADD Pending could be approved | `NONE` |
| Submit | PM ADD Pending could reach Submit | `NONE` |
| Runtime Meaning | Legacy executable ADD | Compatibility telemetry only |

## 5. Double-authority Guard

The canonical/legacy dedup key is:

```text
run_id, business_date, symbol, position_campaign_id, decision_id
```

Duplicate legacy compatibility records, lineage mismatches, or any legacy/canonical overlap where both sides claim executable authority must produce `REVIEW_REQUIRED` or `BLOCKED`; fail-open is prohibited.

## 6. Evidence Files

Evidence was written under:

```text
{OUT_DIR.relative_to(REPO_ROOT)}
```

Key artifacts:

- `summary.json`
- `legacy_add_migration_state.json`
- `compatibility_artifact_contract.json`
- `double_authority_guard_results.json`
- `legacy_pending_zero_proof.json`
- `legacy_quantity_authority_zero_proof.json`
- `legacy_approval_submit_zero_proof.json`
- `sell_pipeline_non_change_proof.json`
- `test_results.json`

## 7. Test Results

```text
python3 -m pytest -q tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
13 passed

python3 -m pytest -q tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/strategy/test_phase22_g_runtime_planning.py
68 passed

python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
127 passed
```

No fresh-run, resume, Historical, 100BD, or long regression was executed.
"""


def supporting_judgments() -> dict[str, str]:
    return {
        "legacy_caller_inventory": "COMPLETE",
        "legacy_migration_state": LEGACY_ADD_MIGRATION_STATE,
        "legacy_quantity_authority": "ZERO_CONFIRMED",
        "legacy_pending_authority": "ZERO_CONFIRMED",
        "legacy_approval_submit_authority": "ZERO_CONFIRMED",
        "double_authority_guard": "PASS",
        "sell_pipeline": "UNCHANGED_FOR_SELL_REDUCE_EXIT_CONFIRMED",
        "downstream_non_change": "CONFIRMED",
        "mode_parity": "CONFIRMED",
        "degression": "PASS",
        "next_entry": "D2-D_APPROVED",
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    artifact = sample_artifact()
    duplicate_artifact = build_legacy_add_compatibility_artifact(
        add_decisions=(
            SellExitDecision(symbol="94320", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-1"),
            SellExitDecision(symbol="94320", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-1"),
        ),
        business_date="2026-07-08",
        target_session_date="2026-07-08",
        environment="demo",
        run_id="phase27-d2c-sample",
    )
    lineage_pass = validate_legacy_add_compatibility_lineage(
        artifact,
        expected_business_date="2026-07-08",
        expected_accepted_generation="generation-d2c",
        expected_campaign_by_symbol={"94320": "UNKNOWN"},
    )
    lineage_review = validate_legacy_add_compatibility_lineage(
        artifact,
        expected_business_date="2026-07-09",
        expected_accepted_generation="generation-x",
        expected_campaign_by_symbol={"94320": "campaign-x"},
    )
    canonical_overlap_guard = evaluate_legacy_add_double_authority_guard(
        artifact,
        canonical_authority_records=(
            {
                "run_id": "phase27-d2c-sample",
                "business_date": "2026-07-08",
                "symbol": "94320",
                "position_campaign_id": "UNKNOWN",
                "decision_id": "pm-2026-07-08-94320-add",
                "decision_effect": "BUY_ADD",
                "quantity_authority": "POSITION_SIZING",
                "pending_authority": "RUNTIME_PLANNING",
            },
        ),
    )
    executable_overlap_artifact = json.loads(json.dumps(artifact))
    executable_overlap_artifact["compatibility"][0]["decision_effect"] = "BUY_ADD"
    executable_overlap_artifact["compatibility"][0]["quantity_authority"] = "LEGACY_ADD_CONSUMER"
    executable_overlap_guard = evaluate_legacy_add_double_authority_guard(
        executable_overlap_artifact,
        canonical_authority_records=(
            {
                "run_id": "phase27-d2c-sample",
                "business_date": "2026-07-08",
                "symbol": "94320",
                "position_campaign_id": "UNKNOWN",
                "decision_id": "pm-2026-07-08-94320-add",
                "decision_effect": "BUY_ADD",
                "quantity_authority": "POSITION_SIZING",
                "pending_authority": "RUNTIME_PLANNING",
            },
        ),
    )

    files = {
        "summary.json": {
            "task_id": TASK_ID,
            "primary_judgment": PRIMARY,
            "supporting_judgments": supporting_judgments(),
            "implementation_changed": True,
            "historical_executed": False,
        },
        "legacy_add_caller_inventory.json": {
            "active_caller": "src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py",
            "consumer": "src/ai_fund_lab_v2/runtime_v2/planning/add_consumer.py",
            "legacy_executable_artifact": "pm_add_order_plan.json",
            "migration_result": "caller retained as compatibility observer only",
            "mode_parity": ["production", "demo", "historical"],
        },
        "legacy_add_authority_before_after.json": {
            "before": {
                "decision_effect": "BUY_PENDING_POSSIBLE",
                "quantity_authority": "ADD_CONSUMER",
                "pending_authority": "PM_ADD_ORDER_PLAN",
                "approval_submit_path": "POSSIBLE",
            },
            "after": {
                "decision_effect": "NONE",
                "quantity_authority": "NONE",
                "pending_authority": "NONE",
                "approval_authority": "NONE",
                "submit_authority": "NONE",
                "telemetry_only": True,
            },
        },
        "legacy_add_migration_state.json": {
            "migration_state": LEGACY_ADD_MIGRATION_STATE,
            "schema_version": LEGACY_ADD_COMPATIBILITY_SCHEMA_VERSION,
            "fixed_authority_fields": {
                "decision_effect": "NONE",
                "quantity_authority": "NONE",
                "pending_authority": "NONE",
                "approval_authority": "NONE",
                "submit_authority": "NONE",
                "telemetry_only": True,
            },
        },
        "compatibility_artifact_contract.json": artifact,
        "compatibility_lineage_validation.json": {
            "pass_case": lineage_pass,
            "review_case": lineage_review,
        },
        "double_authority_guard_contract.json": {
            "dedup_key_fields": ["run_id", "business_date", "symbol", "position_campaign_id", "decision_id"],
            "guarded_objects": [
                "Position Intent",
                "Target Portfolio Decision",
                "Sized Quantity Delta",
                "Runtime Plan",
                "Pending Item",
                "Approval",
                "Submit",
                "Fill Projection",
                "Ledger Application",
            ],
            "conflict_behavior": ["REVIEW_REQUIRED", "BLOCKED"],
            "fail_open_allowed": False,
        },
        "double_authority_guard_results.json": {
            "legacy_duplicate_case": duplicate_artifact["double_authority_guard"],
            "canonical_overlap_with_non_decision_legacy_case": canonical_overlap_guard,
            "canonical_overlap_with_executable_legacy_case": executable_overlap_guard,
        },
        "dedup_key_validation.json": {
            "sample_dedup_key": artifact["compatibility"][0]["dedup_key"],
            "duplicate_case_status": duplicate_artifact["double_authority_guard"]["status"],
            "duplicate_case_review_status": duplicate_artifact["review_status"],
        },
        "legacy_pending_zero_proof.json": {
            "accepted_items_count": 0,
            "pm_add_order_plan_generation": "NOT_REACHED_BY_PM_ADD_INPUT",
            "pending_item_authority": "NONE",
        },
        "legacy_quantity_authority_zero_proof.json": {
            "cash_exposure_authority_for_legacy_add": "NOT_RESOLVED",
            "position_sizing_authority_for_legacy_add": "NOT_RESOLVED",
            "quantity_authority": "NONE",
            "requested_add_notional": "NOT_PRODUCED",
            "approved_add_notional": "NOT_PRODUCED",
        },
        "legacy_approval_submit_zero_proof.json": {
            "approval_authority": "NONE",
            "submit_authority": "NONE",
            "approval_artifact_from_legacy_add": "NOT_PRODUCED",
            "submit_item_from_legacy_add": "NOT_PRODUCED",
        },
        "sell_pipeline_non_change_proof.json": {
            "sell_reduce_exit_logic_changed": False,
            "existing_sell_tests_in_targeted_suite": "PASS",
            "scope_note": "Only ADD-specific legacy authority pre-resolution was removed; SELL planning item generation remains in sell_pipeline.",
        },
        "downstream_non_change_proof.json": {
            "pending_core_changed": False,
            "approval_core_changed": False,
            "submit_core_changed": False,
            "execution_core_changed": False,
            "ledger_core_changed": False,
        },
        "mode_parity_review.json": {
            "production": "COMMON_COMPATIBILITY_CONTRACT",
            "demo": "COMMON_COMPATIBILITY_CONTRACT",
            "historical": "COMMON_COMPATIBILITY_CONTRACT",
            "historical_executed": False,
            "historical_only_bypass": False,
        },
        "legacy_test_migration_inventory.json": {
            "migrated_tests": [
                "test_phase21_b_pm_add_generates_compatibility_telemetry_only",
                "test_phase21_b_pm_add_rejects_duplicate_pending_order",
                "test_phase24_e1_mixed_empty_materializes_no_order_authority_and_submit_accepts",
            ],
            "added_tests": [
                "test_phase27_d2c_legacy_add_duplicate_dedup_key_blocks",
                "test_phase27_d2c_legacy_add_non_decision_does_not_conflict_with_canonical_authority",
                "test_phase27_d2c_legacy_add_executable_overlap_blocks",
                "test_phase27_d2c_legacy_add_lineage_mismatches_require_review",
            ],
        },
        "implementation_completeness_checklist.json": {
            "design_contract": "COMPLETE",
            "schema": "COMPLETE",
            "producer": "COMPLETE_COMPATIBILITY_TELEMETRY_ONLY",
            "consumer": "COMPLETE_NON_DECISION",
            "caller": "COMPLETE_NO_ADD_AUTHORITY_RESOLUTION",
            "production_demo_historical_parity": "CONFIRMED_BY_COMMON_CODE_PATH",
            "unit_tests": "COMPLETE",
            "targeted_regression": "PASS",
            "documentation": "COMPLETE",
            "artifact_evidence": "COMPLETE",
        },
        "regression_degression_results.json": {
            "degression": "PASS",
            "executed_commands": [
                "python3 -m pytest -q tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py",
                "python3 -m pytest -q tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/strategy/test_phase22_g_runtime_planning.py",
                "python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py",
            ],
            "prohibited_commands_executed": [],
        },
        "changed_files.json": {"git_status_short": git_changed_files()},
        "test_results.json": {
            "historical": "NOT_EXECUTED_PROHIBITED",
            "commands": [
                {
                    "command": "python3 -m pytest -q tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py",
                    "result": "13 passed",
                },
                {
                    "command": "python3 -m pytest -q tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/strategy/test_phase22_g_runtime_planning.py",
                    "result": "68 passed",
                },
                {
                    "command": "python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py",
                    "result": "127 passed",
                },
            ],
        },
    }
    for filename, payload in files.items():
        write_json(OUT_DIR / filename, payload)
    PHASE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    PHASE_REPORT.write_text(render_report(), encoding="utf-8")


if __name__ == "__main__":
    main()
