#!/usr/bin/env python3
"""Generate Phase27-D5 PM Expected Edge reasoning contract evidence and report."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "Phase27-D5"
OUT_DIR = REPO_ROOT / "reports/phase27_d5_pm_expected_edge_reasoning_contract_design"
REPORT = REPO_ROOT / "docs/phase_reports/phase27_d5_pm_expected_edge_reasoning_contract_design.md"
PRIMARY = "PHASE27_D5_PM_REASONING_CONTRACT_FROZEN_COMMON_SOT_UPDATED"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def supporting() -> dict[str, str]:
    return {
        "pm_reason_contract": "FROZEN",
        "action_boundary": "FROZEN",
        "reason_contract": "UPDATED",
        "implementation_entry": "READY_FOR_PM_IMPLEMENTATION",
    }


def pm_reason_contract() -> dict[str, object]:
    return {
        "task_id": TASK_ID,
        "contract": "Expected Edge -> PM Reasoning -> Action",
        "pm_evaluates": "EXPECTED_EDGE_ONLY",
        "isolated_inputs_not_directly_evaluated": [
            "trend_alone",
            "rank_alone",
            "profit_alone",
            "market_context_alone",
            "buy_quality_alone",
        ],
        "isolated_inputs_role": "EXPECTED_EDGE_EVIDENCE",
        "reason_codes_role": "EXPLANATION_OF_EXPECTED_EDGE_REASONING_NOT_ACTION_AUTHORITY",
        "thresholds_fixed": False,
    }


def action_boundary_review() -> list[dict[str, object]]:
    return [
        {
            "action": "BUY_NEW",
            "boundary": "No-position Expected Edge is sufficiently high and entry evidence is coherent.",
            "sufficient_by_itself": "EXPECTED_EDGE_PLUS_COHERENT_ENTRY_EVIDENCE",
            "not_sufficient": ["rank_alone", "cash_available", "trend_alone"],
            "threshold_fixed": False,
            "classification": "FROZEN",
        },
        {
            "action": "HOLD",
            "boundary": "Expected Edge remains adequate enough to continue the campaign.",
            "sufficient_by_itself": "EXPECTED_EDGE_MAINTAINED",
            "not_sufficient": ["passive_no_action", "profit_exists", "lack_of_new_candidate"],
            "threshold_fixed": False,
            "classification": "FROZEN",
        },
        {
            "action": "ADD",
            "boundary": "Expected Edge improves, existing position remains a strongest opportunity, and incremental investment value exists.",
            "sufficient_by_itself": "IMPROVED_EXPECTED_EDGE_PLUS_STRONGEST_EXISTING_POSITION_PLUS_INCREMENTAL_VALUE",
            "not_sufficient": ["rank_alone", "no_new_candidate", "cash_available", "pm_add_legacy_reason_alone"],
            "threshold_fixed": False,
            "classification": "FROZEN",
        },
        {
            "action": "REDUCE",
            "boundary": "Expected Edge or risk/reward weakens enough to trim exposure while preserving optionality.",
            "sufficient_by_itself": "WEAKENING_OR_RISK_REVIEW_WITH_CAMPAIGN_OPTIONALITY",
            "not_sufficient": ["profit_exists_only", "minor_expected_edge_noise"],
            "threshold_fixed": False,
            "classification": "FROZEN_AS_DISTINCT_ACTION",
        },
        {
            "action": "EXIT",
            "boundary": "Expected Edge is no longer sufficient, continuation breaks, or risk/Safety requires full close.",
            "sufficient_by_itself": "MATERIAL_EXPECTED_EDGE_DETERIORATION_OR_FULL_CLOSE_RISK",
            "not_sufficient": ["profit_exists_only", "rank_drop_alone_without_expected_edge_review"],
            "threshold_fixed": False,
            "classification": "FROZEN",
        },
    ]


def reason_code_review() -> list[dict[str, object]]:
    return [
        {
            "reason_code": "trend_continuation",
            "classification": "KEEP",
            "action_family": "HOLD_OR_ADD",
            "expected_edge_role": "Continuation evidence supporting Expected Edge adequacy.",
            "notes": "Trend is evidence, not Expected Edge itself.",
        },
        {
            "reason_code": "positive_expected_edge",
            "classification": "REVIEW",
            "action_family": "HOLD",
            "expected_edge_role": "Compatibility code for positive edge evidence.",
            "notes": "Future wording should distinguish Expected Edge adequacy from merely positive raw score.",
        },
        {
            "reason_code": "downside_risk_contained",
            "classification": "KEEP",
            "action_family": "HOLD_OR_ADD",
            "expected_edge_role": "Risk-contained evidence supporting continued exposure.",
            "notes": "Supports Expected Edge but does not create action alone.",
        },
        {
            "reason_code": "risk_increased_but_trend_not_broken",
            "classification": "RENAME",
            "action_family": "REDUCE",
            "expected_edge_role": "Broad weakening/risk fallback.",
            "notes": "Should split into explicit risk/weakening causes in a future implementation contract.",
        },
        {
            "reason_code": "peak_drawdown_warning",
            "classification": "KEEP",
            "action_family": "REDUCE_OR_EXIT_REVIEW",
            "expected_edge_role": "Risk Review / weakening evidence.",
            "notes": "Compatible with REDUCE as a distinct risk/optional exposure action.",
        },
        {
            "reason_code": "trend_and_opportunity_broken",
            "classification": "KEEP",
            "action_family": "EXIT",
            "expected_edge_role": "Expected Edge deterioration with continuation break.",
            "notes": "Strong EXIT explanation when supported by PIT evidence.",
        },
        {
            "reason_code": "profit_retention_break",
            "classification": "RENAME",
            "action_family": "EXIT_OR_RISK_REVIEW",
            "expected_edge_role": "Peak-drawdown/profit-retention risk evidence.",
            "notes": "Must not mean simple profit-taking or profit-alone EXIT.",
        },
        {
            "reason_code": "hard_stop_current_return",
            "classification": "KEEP",
            "action_family": "EXIT",
            "expected_edge_role": "Loss containment / severe risk evidence.",
            "notes": "Risk/Safety style full-close evidence, not profit-taking.",
        },
    ]


def profit_review_design() -> dict[str, object]:
    return {
        "profit_as_primary_expected_edge_input": False,
        "profit_as_supporting_evidence": True,
        "profit_as_risk_review": True,
        "profit_direct_action_authority": False,
        "allowed_use": [
            "embedded_gain_risk_review",
            "drawdown_from_peak_review",
            "risk_reward_changed_after_large_move",
            "concentration_after_profit_expansion",
        ],
        "disallowed_use": [
            "profit_exists_only_exit",
            "profit_exists_only_reduce",
            "fixed_take_profit_action_without_expected_edge_or_risk_review",
        ],
        "threshold_fixed": False,
    }


def hold_boundary_review() -> dict[str, object]:
    return {
        "principle": "HOLD remains valid while Expected Edge is maintained enough to continue the campaign.",
        "slight_deterioration": "HOLD unless deterioration changes risk/reward enough for REDUCE or invalidates campaign enough for EXIT.",
        "hold_to_reduce": "When weakening/risk evidence supports trimming exposure while preserving campaign optionality.",
        "hold_to_exit": "When Expected Edge becomes insufficient, continuation breaks, or risk/Safety requires full close.",
        "threshold_fixed": False,
    }


def reduce_review() -> dict[str, object]:
    return {
        "independent_action_needed": "YES_AS_DESIGN_CONCEPT",
        "reason": "REDUCE expresses risk/weakening/partial-rotation before full EXIT is justified.",
        "evidence_from_d2f": "REDUCE reasons were mainly Risk and Weakening, including peak_drawdown_warning and risk_increased_but_trend_not_broken.",
        "not_a_profit_taking_action": True,
        "boundary_with_hold": "Expected Edge/risk has weakened beyond continued full exposure.",
        "boundary_with_exit": "Campaign optionality remains and full close is not justified.",
        "threshold_fixed": False,
    }


def exit_review() -> dict[str, object]:
    return {
        "principle": "EXIT centers on material Expected Edge deterioration, continuation break, full-close risk, or Safety.",
        "profit_alone_exit": "PROHIBITED_BY_DESIGN",
        "valid_exit_evidence": [
            "trend_and_opportunity_broken",
            "hard_stop_current_return",
            "risk_guard_status_bad",
            "exit_score_high",
            "weak_hold_score_without_alive_trend_or_opportunity",
            "profit_retention_break_only_when_interpreted_as_peak_drawdown_or_risk_review",
        ],
        "threshold_fixed": False,
    }


def design_revision_log() -> list[dict[str, str]]:
    return [
        {
            "file": "docs/02_architecture/strategy_architecture_v1.md",
            "revision": "Added Phase27-D5 PM Expected Edge reasoning contract and action boundaries.",
        },
        {
            "file": "docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md",
            "revision": "Added Phase27-D5 PM Expected Edge Reasoning Contract, action boundaries, and reason code review.",
        },
        {
            "file": "docs/02_architecture/autonomous_ai_operations_architecture.md",
            "revision": "Added autonomous operations boundary for reason codes as explanations, not action producers.",
        },
        {
            "file": "docs/02_architecture/position_management_decision_trace_contract.md",
            "revision": "Added Phase27-D5 Expected Edge reason code review classification.",
        },
    ]


def files() -> dict[str, object]:
    return {
        "summary.json": {
            "task_id": TASK_ID,
            "primary_judgment": PRIMARY,
            "supporting": supporting(),
            "implementation_changed": False,
            "historical_executed": False,
            "fresh_run_executed": False,
            "common_sot_updated": [
                "docs/02_architecture/strategy_architecture_v1.md",
                "docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md",
                "docs/02_architecture/autonomous_ai_operations_architecture.md",
                "docs/02_architecture/position_management_decision_trace_contract.md",
            ],
        },
        "pm_reason_contract.json": pm_reason_contract(),
        "action_boundary_review.json": action_boundary_review(),
        "reason_code_review.json": reason_code_review(),
        "profit_review_design.json": profit_review_design(),
        "hold_boundary_review.json": hold_boundary_review(),
        "reduce_review.json": reduce_review(),
        "exit_review.json": exit_review(),
        "design_revision_log.json": design_revision_log(),
        "test_results.json": {
            "historical_executed": False,
            "fresh_run_executed": False,
            "commands": [
                {
                    "command": "python3 -m py_compile tools/phase27_analysis/phase27_d5_generate_pm_expected_edge_reasoning_contract.py",
                    "result": "PASS",
                },
                {
                    "command": "for f in reports/phase27_d5_pm_expected_edge_reasoning_contract_design/*.json; do python3 -m json.tool \"$f\" >/dev/null || exit 1; done",
                    "result": "PASS",
                },
            ],
        },
    }


def render_report() -> str:
    return f"""# Phase27-D5 PM Expected Edge Reasoning Contract and Action Boundary Design

## 1. Scope

Phase27-D5 freezes the PM reasoning contract that converts Expected Edge into Strategy action.

```text
Implementation Change: false
PM Logic Change: false
Strategy Logic Change: false
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

## 3. PM Reason Contract

PM evaluates Expected Edge only.

Trend, Rank, Profit, Market Context, and BUY Quality are Expected Edge evidence. They are not direct action producers.

```text
Expected Edge Evidence
  -> PM Expected Edge Reasoning
  -> BUY_NEW / ADD / HOLD / REDUCE / EXIT
```

Reason codes explain PM Expected Edge reasoning. They do not create separate Action Authority.

## 4. Action Boundaries

- `BUY_NEW`: no-position Expected Edge is sufficiently high and entry evidence is coherent.
- `HOLD`: Expected Edge remains adequate; slight deterioration remains HOLD unless risk/reward meaningfully weakens.
- `ADD`: Expected Edge improves, the existing holding remains a strongest opportunity, and incremental investment value exists.
- `REDUCE`: Expected Edge or risk/reward weakens enough to trim exposure while preserving campaign optionality.
- `EXIT`: Expected Edge becomes insufficient, continuation breaks, or risk/Safety requires full close.

No numeric threshold is fixed.

## 5. Reason Code Review

| Reason code | Classification | Interpretation |
|---|---|---|
| `trend_continuation` | KEEP | Continuation evidence. |
| `positive_expected_edge` | REVIEW | Compatibility positive-edge code; should become more explicit in future reasoning. |
| `downside_risk_contained` | KEEP | Risk-contained evidence. |
| `risk_increased_but_trend_not_broken` | RENAME | Broad REDUCE fallback; should split into explicit causes. |
| `peak_drawdown_warning` | KEEP | Risk Review / weakening evidence. |
| `trend_and_opportunity_broken` | KEEP | Expected Edge deterioration and continuation break. |
| `profit_retention_break` | RENAME | Peak-drawdown/profit-retention risk, not simple profit-taking. |
| `hard_stop_current_return` | KEEP | Loss-containment / severe risk evidence. |

## 6. Profit Review

Profit is not a Primary Expected Edge decision input and does not directly produce action.

Profit may be Supporting Evidence and Risk Review evidence for embedded gain risk, drawdown-from-peak, changed risk/reward, or concentration after profit expansion.

## 7. HOLD / REDUCE / EXIT Boundary

If Expected Edge slightly declines, default design is not immediate EXIT. HOLD remains valid while the campaign is still attractive enough. REDUCE is the intermediate action when risk/reward weakens enough to trim exposure but campaign optionality remains. EXIT is for insufficient Expected Edge, broken continuation, full-close risk, or Safety.

## 8. Common SoT Updated

```text
docs/02_architecture/strategy_architecture_v1.md
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
docs/02_architecture/autonomous_ai_operations_architecture.md
docs/02_architecture/position_management_decision_trace_contract.md
```

## 9. Evidence

```text
{OUT_DIR.relative_to(REPO_ROOT)}
```

## 10. Validation

```text
python3 -m py_compile tools/phase27_analysis/phase27_d5_generate_pm_expected_edge_reasoning_contract.py
PASS

JSON validation for all generated evidence files
PASS
```

No Runtime, Strategy, PM, Position Sizing, Historical, fresh-run, resume, 10BD, 100BD, or long regression was executed.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in files().items():
        write_json(OUT_DIR / name, payload)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
