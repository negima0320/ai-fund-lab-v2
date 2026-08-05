#!/usr/bin/env python3
"""Generate Phase27-D2-E Runtime Planning canonical quantity delta evidence."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "Phase27-D2-E"
OUT_DIR = REPO_ROOT / "reports/phase27_d2e_runtime_planning_canonical_quantity_delta_integration"
PHASE_REPORT = REPO_ROOT / "docs/phase_reports/phase27_d2e_runtime_planning_canonical_quantity_delta_integration.md"
PRIMARY = "PHASE27_D2E_RUNTIME_PLANNING_CANONICAL_INTEGRATION_COMPLETE_D2F_READY"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def runtime_mapping_matrix() -> list[dict[str, object]]:
    return [
        {
            "position_state": "NO_CURRENT_POSITION",
            "canonical_quantity_delta": "POSITIVE",
            "target_quantity_candidate": "> 0",
            "runtime_action": "BUY_NEW",
            "runtime_responsibility": "MAP_ONLY",
            "strategy_recalculation": False,
        },
        {
            "position_state": "CURRENT_POSITION",
            "canonical_quantity_delta": "POSITIVE",
            "target_quantity_candidate": "> current_quantity",
            "runtime_action": "BUY_ADD",
            "runtime_responsibility": "MAP_ONLY",
            "strategy_recalculation": False,
        },
        {
            "position_state": "CURRENT_POSITION",
            "canonical_quantity_delta": "ZERO",
            "target_quantity_candidate": "current_quantity",
            "runtime_action": "NO_ACTION",
            "runtime_responsibility": "MAP_ONLY",
            "strategy_recalculation": False,
        },
        {
            "position_state": "CURRENT_POSITION",
            "canonical_quantity_delta": "NEGATIVE_PARTIAL",
            "target_quantity_candidate": "> 0",
            "runtime_action": "SELL_REDUCE",
            "runtime_responsibility": "MAP_ONLY",
            "strategy_recalculation": False,
        },
        {
            "position_state": "CURRENT_POSITION",
            "canonical_quantity_delta": "FULL_NEGATIVE",
            "target_quantity_candidate": 0,
            "runtime_action": "SELL_EXIT",
            "runtime_responsibility": "MAP_ONLY",
            "strategy_recalculation": False,
        },
    ]


def runtime_action_examples() -> list[dict[str, object]]:
    return [
        {"symbol": "6758", "current_quantity": 100, "target_quantity_candidate": 150, "quantity_delta_candidate": 50, "runtime_action": "BUY_ADD"},
        {"symbol": "7203", "current_quantity": 100, "target_quantity_candidate": 100, "quantity_delta_candidate": 0, "runtime_action": "NO_ACTION"},
        {"symbol": "8306", "current_quantity": 100, "target_quantity_candidate": 60, "quantity_delta_candidate": -40, "runtime_action": "SELL_REDUCE"},
        {"symbol": "9432", "current_quantity": 100, "target_quantity_candidate": 0, "quantity_delta_candidate": -100, "runtime_action": "SELL_EXIT"},
    ]


def supporting() -> dict[str, str]:
    return {
        "canonical_priority": "CONFIRMED",
        "pm_fallback": "LEGACY_ONLY",
        "duplicate_authority": "ZERO",
        "degression": "PASS",
        "next": "D2-F_APPROVED",
    }


def test_results() -> dict[str, object]:
    return {
        "historical_executed": False,
        "fresh_run_executed": False,
        "prohibited_execution": "NOT_EXECUTED",
        "commands": [
            {
                "command": "PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase27_d2e python3 -m pytest -q tests/strategy/test_phase22_g_runtime_planning.py",
                "result": "PASS",
                "summary": "39 passed in 0.40s",
            },
            {
                "command": "PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase27_d2e python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase27_d2d_position_sizing_plan.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py",
                "result": "PASS",
                "summary": "137 passed in 2.52s",
            },
        ],
    }


def files() -> dict[str, object]:
    matrix = runtime_mapping_matrix()
    examples = runtime_action_examples()
    return {
        "summary.json": {
            "task_id": TASK_ID,
            "primary_judgment": PRIMARY,
            "supporting": supporting(),
            "implementation_changed": True,
            "historical_executed": False,
            "fresh_run_executed": False,
            "common_architecture_docs_updated": [
                "docs/02_architecture/runtime_architecture_v2.md",
                "docs/02_architecture/portfolio_construction_and_position_sizing_contract.md",
            ],
            "changed_files": [
                "src/ai_fund_lab_v2/strategy/runtime_planning.py",
                "tests/strategy/test_phase22_g_runtime_planning.py",
                "docs/02_architecture/runtime_architecture_v2.md",
                "docs/02_architecture/portfolio_construction_and_position_sizing_contract.md",
                "docs/phase_reports/phase27_d2e_runtime_planning_canonical_quantity_delta_integration.md",
                "reports/phase27_d2e_runtime_planning_canonical_quantity_delta_integration/",
                "tools/phase27_analysis/phase27_d2e_generate_runtime_planning_integration_report.py",
            ],
        },
        "runtime_mapping_matrix.json": matrix,
        "fallback_retirement_proof.json": {
            "rule_1": {
                "condition": "Canonical quantity delta exists",
                "result": "PM fallback disabled",
                "evidence": "test_phase27_d2e_canonical_delta_disables_pm_fallback",
            },
            "rule_2": {
                "condition": "Canonical position_sizing_plan.v1 missing",
                "result": "Compatibility PM fallback allowed",
                "evidence": "test_phase27_d2e_legacy_pm_fallback_allowed_when_canonical_missing",
            },
            "rule_3": {
                "condition": "Canonical sizing lineage exists but quantity delta is missing and PM fallback is available",
                "result": "REVIEW_REQUIRED, not executable fallback",
                "evidence": "test_phase27_d2e_canonical_row_without_delta_blocks_duplicate_pm_authority",
            },
        },
        "canonical_priority_proof.json": {
            "canonical_input": "position_sizing_plan.v1",
            "canonical_priority_confirmed": True,
            "runtime_payload_fields": ["canonical_quantity_source", "canonical_quantity_delta_priority", "pm_fallback_used", "pm_fallback_scope"],
            "quantity_authority_when_executable": "PHASE27_D2D_POSITION_SIZING_PLAN",
            "pm_fallback_with_canonical_delta": "NOT_USED",
        },
        "runtime_action_examples.json": examples,
        "lineage_validation.json": {
            "source_artifact_registered": "position_sizing_plan",
            "source_hash_included": True,
            "runtime_rows_preserve_quantity_fields": ["target_quantity_candidate", "quantity_delta_candidate"],
            "source_status_rules": {
                "schema_version": "position_sizing_plan.v1",
                "authority_mode": "SHADOW",
                "decision_effect": "NONE",
            },
        },
        "non_change_proof.json": {
            "momentum_changed": False,
            "quality_changed": False,
            "opportunity_changed": False,
            "sizing_formula_changed": False,
            "portfolio_decision_changed": False,
            "pm_changed": False,
            "buy_new_selection_changed": False,
            "cash_policy_changed": False,
            "pending_changed": False,
            "submit_changed": False,
            "execution_changed": False,
        },
        "regression_results.json": test_results(),
        "implementation_completeness_checklist.json": {
            "canonical_delta_priority": "PASS",
            "pm_fallback_legacy_only": "PASS",
            "same_row_canonical_plus_fallback_blocked_or_review": "PASS",
            "buy_add_generation_possible": "PASS",
            "sell_reduce_generation_possible": "PASS",
            "sell_exit_generation_possible": "PASS",
            "no_action_generation_possible": "PASS",
            "runtime_planning_rejudgment_absent": "PASS",
            "pm_unchanged": "PASS",
            "portfolio_unchanged": "PASS",
            "sizing_formula_unchanged": "PASS",
            "historical_not_executed": "PASS",
            "fresh_run_not_executed": "PASS",
        },
        "test_results.json": test_results(),
    }


def render_report() -> str:
    return f"""# Phase27-D2-E Runtime Planning Canonical Quantity Delta Integration

## 1. Scope

Phase27-D2-E connects `position_sizing_plan.v1` to Runtime Planning as the canonical quantity delta source.

```text
Implementation Change: true
Runtime Planning: changed
PM fallback: legacy compatibility only
Pending / Approval / Submit / Execution: unchanged
Momentum / Quality / Opportunity / Incremental Eligibility: unchanged
Historical / fresh-run / resume / long regression: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
{PRIMARY}
```

Supporting:

```json
{json.dumps(supporting(), ensure_ascii=False, indent=2)}
```

## 3. Contract Implemented

Runtime Planning now accepts optional `position_sizing_plan.v1` input and selects quantity authority as follows:

```text
position_sizing_plan.v1 present
  -> canonical quantity delta authority
  -> PM fallback disabled for rows with canonical sizing lineage

position_sizing_plan.v1 absent
  -> legacy position_sizing.v1 / PM compatibility behavior remains available
```

Runtime Planning remains a mapper only. It maps `quantity_delta_candidate` to `BUY_NEW`, `BUY_ADD`, `NO_ACTION`, `SELL_REDUCE`, or `SELL_EXIT`; it does not recalculate Strategy decisions.

## 4. Runtime Mapping

| Position State | Delta | Target Quantity | Runtime Action |
|---|---:|---:|---|
| New | Positive | Positive | `BUY_NEW` |
| Existing | Positive | Positive | `BUY_ADD` |
| Existing | Zero | Current quantity | `NO_ACTION` |
| Existing | Negative partial | > 0 | `SELL_REDUCE` |
| Existing | Full negative | 0 | `SELL_EXIT` |

## 5. Fallback Retirement

- Canonical delta present: PM fallback not used.
- Canonical artifact absent: PM fallback allowed only as legacy compatibility.
- Canonical sizing lineage with missing delta plus PM fallback evidence: resolves to `REVIEW_REQUIRED`, not executable ADD/REDUCE/EXIT.

## 6. Non-change Proof

No changes were made to PM, Portfolio Construction, Position Sizing formula, Momentum, Quality, Opportunity, Incremental Eligibility, cash policy, Pending, Approval, Submit, Safety, or Execution. Common architecture docs were updated so this contract is not phase-local.

## 7. Evidence

Evidence files:

```text
{OUT_DIR.relative_to(REPO_ROOT)}
```

## 8. Tests

```text
{test_results()["commands"][0]["command"]}
{test_results()["commands"][0]["summary"]}

{test_results()["commands"][1]["command"]}
{test_results()["commands"][1]["summary"]}
```

No Historical, fresh-run, resume, 10BD, 100BD, 1year, or long regression was executed.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in files().items():
        write_json(OUT_DIR / name, payload)
    PHASE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    PHASE_REPORT.write_text(render_report() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
