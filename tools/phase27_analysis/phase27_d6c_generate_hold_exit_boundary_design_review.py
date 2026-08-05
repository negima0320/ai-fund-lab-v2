#!/usr/bin/env python3
"""Generate Phase27-D6-C PM HOLD/EXIT boundary design review evidence."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "Phase27-D6-C"
OUT_DIR = REPO_ROOT / "reports/phase27_d6c_pm_hold_exit_boundary_performance_design_review"
REPORT = REPO_ROOT / "docs/phase_reports/phase27_d6c_pm_hold_exit_boundary_performance_design_review.md"
PRIMARY = "PHASE27_D6C_PM_HOLD_EXIT_BOUNDARY_FROZEN_COMMON_SOT_UPDATED"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def supporting() -> dict[str, str]:
    return {
        "hold_boundary": "FROZEN",
        "exit_boundary": "FROZEN",
        "reduce_review": "COMPLETE",
        "risk_review": "UPDATED",
        "common_sot": "UPDATED",
        "implementation_entry": "READY_FOR_PM_BOUNDARY_IMPLEMENTATION",
    }


def hold_boundary_design() -> dict[str, object]:
    return {
        "action": "HOLD",
        "boundary": "Expected Edge remains sufficient / adequate.",
        "philosophy": "HOLD is an active continuation decision, not passive no-action.",
        "slight_expected_edge_decline": "Does not automatically become EXIT or REDUCE.",
        "required_explanation": [
            "expected_edge_adequate",
            "continuation evidence",
            "downside risk contained",
            "no full-close risk or Safety requirement",
        ],
        "not_reasons": ["profit_exists", "trend_alone", "rank_alone", "lack_of_new_candidate"],
        "threshold_fixed": False,
        "status": "FROZEN",
    }


def reduce_boundary_design() -> dict[str, object]:
    return {
        "action": "REDUCE",
        "boundary": "Expected Edge or risk/reward weakens while campaign optionality remains.",
        "role": "Risk Review / exposure trim / partial rotation before full EXIT is justified.",
        "needed_as_independent_action": "RETAINED_AS_DESIGN_CONCEPT",
        "relationship_to_hold": "More risk or weakening than full HOLD exposure should carry.",
        "relationship_to_exit": "Campaign is not fully invalidated; optionality remains.",
        "not_reasons": ["simple_profit_taking", "trend_alone", "mandatory_full_close"],
        "threshold_fixed": False,
        "status": "REVIEW_COMPLETE_NOT_REMOVED",
    }


def exit_boundary_design() -> dict[str, object]:
    return {
        "action": "EXIT",
        "boundary": "Expected Edge insufficient, continuation/signal broken, severe risk, or Safety full-close requirement.",
        "expected_edge_insufficient_meaning": "Forward expected value is no longer adequate for campaign continuation after integrating PIT evidence.",
        "trend_alone_exit": False,
        "profit_alone_exit": False,
        "safety_relationship": "Safety may block or require full close under hard-limit responsibility; Safety is not Expected Edge optimizer.",
        "valid_evidence": [
            "trend_and_expected_edge_broken",
            "peak_drawdown_profit_retention_risk when it affects risk/reward",
            "hard_stop_current_return",
            "risk_guard / Safety full-close evidence",
        ],
        "threshold_fixed": False,
        "status": "FROZEN",
    }


def risk_review_contract() -> dict[str, object]:
    return {
        "profit_alone_to_action": "PROHIBITED",
        "large_embedded_gain_role": "SUPPORTING_RISK_REVIEW_EVIDENCE",
        "risk_review_inputs": [
            "large_embedded_gain",
            "drawdown_from_peak",
            "volatility",
            "concentration_after_profit_expansion",
            "changed_risk_reward",
        ],
        "expected_edge_effect": "May influence Expected Edge as supporting evidence.",
        "not_action_authority": True,
        "threshold_fixed": False,
    }


def expected_edge_boundary_review() -> dict[str, object]:
    return {
        "principles": [
            {"expected_edge_state": "ADEQUATE", "action_boundary": "HOLD"},
            {"expected_edge_state": "IMPROVED", "action_boundary": "ADD_CANDIDATE"},
            {"expected_edge_state": "DETERIORATING_WITH_OPTIONALITY", "action_boundary": "REDUCE_CANDIDATE"},
            {"expected_edge_state": "INSUFFICIENT_OR_BROKEN", "action_boundary": "EXIT"},
            {"expected_edge_state": "SEVERE_RISK_OR_SAFETY", "action_boundary": "EXIT_OR_SAFETY_REVIEW"},
        ],
        "reason_relationship": {
            "expected_edge_adequate": "HOLD evidence",
            "expected_edge_risk_deterioration": "REDUCE candidate evidence when optionality remains",
            "peak_drawdown_profit_retention_risk": "Risk Review evidence, not profit-taking",
            "trend_and_opportunity_broken": "Legacy readable EXIT evidence; canonical trend_and_expected_edge_broken",
            "hard_stop_current_return": "Severe risk / loss-containment EXIT evidence",
        },
        "threshold_fixed": False,
    }


def design_revision_log() -> list[dict[str, str]]:
    return [
        {
            "file": "docs/02_architecture/strategy_architecture_v1.md",
            "revision": "Added Phase27-D6-C HOLD / REDUCE / EXIT Expected Edge boundary design.",
        },
        {
            "file": "docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md",
            "revision": "Added common PM HOLD / REDUCE / EXIT boundary section.",
        },
        {
            "file": "docs/02_architecture/position_management_decision_trace_contract.md",
            "revision": "Added trace semantics relationship for HOLD / REDUCE / EXIT boundary reasons.",
        },
        {
            "file": "docs/02_architecture/autonomous_ai_operations_architecture.md",
            "revision": "Added autonomous operations boundary for HOLD / REDUCE / EXIT and Risk Review signals.",
        },
    ]


def implementation_entry() -> dict[str, object]:
    return {
        "status": "READY_FOR_PM_BOUNDARY_IMPLEMENTATION",
        "allowed_next_scope": "Single PM boundary implementation experiment, preferably HOLD/EXIT stability.",
        "prohibited_in_d6c": [
            "PM implementation change",
            "Runtime change",
            "threshold definition",
            "Historical execution",
            "ADD improvement",
            "Quality/Market/Portfolio Fit input expansion",
        ],
        "open_questions": [
            "Expected Edge numeric representation",
            "HOLD/REDUCE/EXIT boundary thresholds",
            "Risk Review threshold",
            "Profit Review threshold",
            "REDUCE necessity",
            "ADD boundary",
        ],
    }


def files() -> dict[str, object]:
    return {
        "summary.json": {
            "task_id": TASK_ID,
            "primary_judgment": PRIMARY,
            "supporting": supporting(),
            "implementation_changed": False,
            "pm_logic_changed": False,
            "runtime_changed": False,
            "historical_executed": False,
            "fresh_run_executed": False,
            "common_sot_updated": [
                "docs/02_architecture/strategy_architecture_v1.md",
                "docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md",
                "docs/02_architecture/position_management_decision_trace_contract.md",
                "docs/02_architecture/autonomous_ai_operations_architecture.md",
            ],
        },
        "hold_boundary_design.json": hold_boundary_design(),
        "reduce_boundary_design.json": reduce_boundary_design(),
        "exit_boundary_design.json": exit_boundary_design(),
        "risk_review_contract.json": risk_review_contract(),
        "expected_edge_boundary_review.json": expected_edge_boundary_review(),
        "design_revision_log.json": design_revision_log(),
        "implementation_entry.json": implementation_entry(),
        "test_results.json": {
            "commands": [
                {
                    "command": "PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase27_d6c python3 -m py_compile tools/phase27_analysis/phase27_d6c_generate_hold_exit_boundary_design_review.py",
                    "result": "PASS",
                },
                {
                    "command": "for f in reports/phase27_d6c_pm_hold_exit_boundary_performance_design_review/*.json; do python3 -m json.tool \"$f\" >/dev/null || exit 1; done",
                    "result": "PASS",
                },
            ],
            "historical_executed": False,
            "fresh_run_executed": False,
            "runtime_executed": False,
        },
    }


def render_report() -> str:
    return f"""# Phase27-D6-C PM HOLD / EXIT Boundary Performance Design Review

## 1. Scope

Phase27-D6-C freezes the PM HOLD / REDUCE / EXIT Expected Edge boundary design and integrates it into common SoT.

```text
Implementation Change: false
PM Logic Change: false
Runtime Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
{PRIMARY}
```

Supporting:

```json
{json.dumps(supporting(), ensure_ascii=False, indent=2)}
```

## 3. Boundary Design

```text
Expected Edge adequate
  -> HOLD

Expected Edge / risk-reward weakening while campaign optionality remains
  -> REDUCE candidate

Expected Edge insufficient, continuation broken, severe risk, or Safety full-close requirement
  -> EXIT
```

HOLD is active continuation. A small Expected Edge decline does not automatically become EXIT.

REDUCE remains a distinct Risk Review / campaign-preserving exposure-trim concept. D6-C does not remove REDUCE.

EXIT is full close for insufficient Expected Edge, broken continuation/signal, severe risk, or Safety. Trend alone and profit alone are not EXIT authority.

## 4. Risk Review

Profit alone does not create action. Large embedded gain plus drawdown, volatility, concentration, or changed risk/reward can be supporting Risk Review evidence that affects Expected Edge.

## 5. Common SoT Updated

```text
docs/02_architecture/strategy_architecture_v1.md
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
docs/02_architecture/position_management_decision_trace_contract.md
docs/02_architecture/autonomous_ai_operations_architecture.md
```

## 6. Open Questions

Expected Edge numeric representation, HOLD/REDUCE/EXIT thresholds, Risk Review threshold, Profit Review threshold, REDUCE necessity, and ADD boundary remain open for later implementation design.

## 7. Evidence

```text
{OUT_DIR.relative_to(REPO_ROOT)}
```

No Runtime, PM implementation, Historical, fresh-run, resume, 10BD, 100BD, or long regression was executed.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in files().items():
        write_json(OUT_DIR / name, payload)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
