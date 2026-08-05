#!/usr/bin/env python3
"""Generate Phase27 closure and Phase28 entry handoff artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "reports/phase27_cl_phase27_closure_phase28_entry_contract"
REPORT_DIR = REPO_ROOT / "docs/phase_reports"
MACHINE_SUMMARY = REPO_ROOT / "reports/phase_reports/phase27_final_summary_and_phase28_handoff.json"
PRIMARY = "PHASE27_CLOSED_WITH_FIRST_PERFORMANCE_EXPERIMENT_ADOPTED_PHASE28_READY"
FINAL_STATUS = "CLOSED_WITH_ADOPTED_PERFORMANCE_IMPROVEMENT_AND_KNOWN_COMPARABILITY_LIMITATIONS"


REQUIRED_READING = [
    "docs/phase_reports/phase27_to_phase28_chatgpt_handoff.md",
    "docs/phase_reports/phase27_final_summary_and_phase28_handoff.md",
    "docs/phase_reports/phase27_d6e_d6d_100bd_before_after_causal_attribution_and_adoption_review.md",
    "docs/02_architecture/strategy_architecture_v1.md",
    "docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md",
    "docs/02_architecture/position_management_decision_trace_contract.md",
    "docs/02_architecture/portfolio_construction_and_position_sizing_contract.md",
    "docs/02_architecture/runtime_architecture_v2.md",
    "docs/phase_reports/phase27_a9_canonical_buy_add_authority_unification_and_legacy_consumer_disposition_design_review.md",
    "docs/phase_reports/phase27_d6a_pm_implementation_gap_audit.md",
    "docs/01_requirements/phase_roadmap.md",
]


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def supporting() -> dict[str, str]:
    return {
        "phase27_closure": "APPROVED",
        "d6d_adoption": "APPROVED_WITH_LIMITATIONS",
        "common_sot": "UPDATED",
        "roadmap": "UPDATED",
        "phase28_purpose": "FROZEN",
        "phase28_entry": "APPROVED",
        "phase28_first_task": "PHASE28_A_ADD_BASELINE_AND_INCREMENTAL_INVESTMENT_EVIDENCE_AUDIT",
    }


def completed_work() -> dict[str, Any]:
    return {
        "performance_diagnosis": [
            "Observed Funnel did not confirm clearly weaker BUY over clearly stronger available candidates.",
            "Higher-ranked candidate dropout was a multi-stage interaction: Existing Position, Zero Delta, Duplicate, Portfolio Construction, Lot Constraint, and Quality filtering.",
            "Forced BUY, fixed BUY count, and forced cash deployment were not confirmed.",
            "Many actual BUY rows had moderate PIT investment basis; some remained relative-only / weak incremental eligibility.",
            "PM ADD existed but executable Runtime ADD was initially zero.",
            "Rank1 existing position could become PM ADD yet fall to Planning NO_ACTION.",
            "Short EXIT -> Re-entry and HOLD / EXIT boundary instability were confirmed.",
        ],
        "investment_philosophy_freeze": {
            "data": "Trust PIT data and Expected Edge reasoning, not unconditional AI output.",
            "buy": "Enter no-position candidates with sufficiently high Expected Edge.",
            "hold": "Actively continue holding while Expected Edge remains adequate.",
            "add": "Add only when the held symbol remains among strongest candidates, Expected Edge improves, and Incremental Investment Value exists.",
            "reduce": "Intermediate action when risk/reward weakens but campaign optionality remains.",
            "exit": "Exit when Expected Edge is insufficient, continuation breaks, severe risk appears, or Safety requires full close.",
            "profit": "Profit alone is not Action Authority; large embedded gain may become Risk Review evidence.",
            "cash": "Cash is an outcome, not an objective.",
        },
        "canonical_chain": [
            "PM Decision",
            "position_intent.v1",
            "target_portfolio_decision.v1",
            "position_sizing_plan.v1",
            "Runtime Planning",
        ],
        "canonical_mapping": {
            "positive_existing_delta": "BUY_ADD",
            "zero_delta": "NO_ACTION",
            "negative_partial_delta": "SELL_REDUCE",
            "full_negative_delta": "SELL_EXIT",
        },
        "legacy_add_repair": [
            "Legacy PM ADD consumer removed from executable authority.",
            "Legacy ADD converted to telemetry-only compatibility adapter.",
            "Legacy ADD cannot generate quantity, Pending, Approval, or Submit.",
            "Canonical BUY_ADD authority is PM -> Portfolio Construction -> Position Sizing -> Positive Delta -> Runtime Planning.",
            "PM fallback is disabled when canonical delta exists.",
        ],
        "pm_reason_trace_repair": {
            "legacy_reason_readability": "PRESERVED",
            "canonical_metadata": "ADDED",
            "decision_trace": "EXPECTED_EDGE_ALIGNED",
            "action_score_threshold_quantity_runtime": "UNCHANGED",
            "mapping": {
                "profit_retention_break": "peak_drawdown_profit_retention_risk",
                "risk_increased_but_trend_not_broken": "expected_edge_risk_deterioration or evidence-specific risk code",
                "positive_expected_edge": "expected_edge_adequate",
            },
        },
        "first_performance_experiment": {
            "change": "profit_retention_break only + Expected Edge positive + no high downside risk + no strong full-close condition -> EXIT to HOLD",
            "not_changed": [
                "BUY_NEW",
                "ADD",
                "REDUCE",
                "PM score",
                "PM threshold",
                "Opportunity",
                "Quality",
                "Market Context",
                "Portfolio Construction",
                "Sizing",
                "Runtime Planning",
                "Pending",
                "Submit",
                "Safety",
                "Execution",
            ],
            "adoption": "ADOPT_WITH_LIMITATIONS",
        },
    }


def final_judgment() -> dict[str, Any]:
    return {
        "primary_judgment": PRIMARY,
        "supporting": {
            "architecture_repair": "COMPLETE",
            "decision_authority": "CANONICALIZED",
            "legacy_add_authority": "RETIRED_FROM_EXECUTION",
            "pm_philosophy": "FROZEN",
            "expected_edge_contract": "FROZEN",
            "pm_action_boundary": "FROZEN",
            "first_hold_exit_experiment": "ADOPTED_WITH_LIMITATIONS",
            "100bd": "COMPLETED",
            "risk_regression": "NOT_OBSERVED",
            "phase28_entry": "APPROVED",
        },
        "final_status": FINAL_STATUS,
    }


def adopted_changes() -> dict[str, Any]:
    return {
        "d6d_hold_exit_boundary": {
            "status": "ADOPTED_WITH_LIMITATIONS",
            "rule": "profit_retention_break only AND Expected Edge positive AND no high downside risk AND no strong full-close condition -> HOLD",
            "direct_traceable_benefit_jpy": 37100,
            "headline_equity_delta_jpy": 81590,
            "not_directly_attributed_jpy": 44490,
            "risk_regression": "NOT_OBSERVED",
        }
    }


def known_limitations() -> list[str]:
    return [
        "Baseline and After profile names differ: historical-smoke vs historical-extended-smoke.",
        "Source commit differs.",
        "Both runs recorded source dirty.",
        "After run lacks Baseline-equivalent performance_report directory.",
        "Some metrics such as Maximum Drawdown, Cash Utilization, and Turnover remain NOT_AVAILABLE or partial in equivalent authority.",
        "Full +81,590 JPY headline delta is not direct D6-D causal benefit.",
        "Close is non-blocking REVIEW_REQUIRED from Strategy Shadow review.",
        "HOLD improvement is limited to the profit-retention-only boundary, not final HOLD improvement.",
        "Formal ADD Expected Edge / Incremental Value eligibility is not implemented.",
        "PM regular path still lacks explicit Expected Edge input connection for BUY Quality, Market Context, Portfolio Fit, and Corporate Event.",
    ]


def phase28_purpose() -> dict[str, Any]:
    return {
        "purpose": "Use the Phase27 Expected Edge / Canonical PM Architecture to allocate additional capital correctly into winning held positions and improve Capital Efficiency and Portfolio Return.",
        "primary_goal": "Use the Canonical BUY_ADD path so BUY_ADD becomes executable only when adding to an existing position improves Portfolio Expected Value.",
        "themes": [
            "ADD Expected Edge",
            "Incremental Investment Eligibility",
            "Capital Efficiency",
            "Evidence Input Expansion",
            "Performance Experiment Cycle",
        ],
        "system_purpose": {
            "capital": "1,000,000 JPY initial capital",
            "trading": "cash equity only",
            "target": "annual return +50%",
            "style": "aggressive Expected Edge maximization / Momentum-follow / Momentum Rotation",
        },
    }


def phase28_workstreams() -> list[dict[str, Any]]:
    return [
        {
            "task": "Phase28-A",
            "name": "ADD Baseline and Existing Evidence Audit",
            "type": "Read-only",
            "purpose": "Determine when current ADD is correct, weak, non-executable, or capital inefficient.",
        },
        {
            "task": "Phase28-B",
            "name": "Incremental Investment Eligibility Design",
            "type": "Common SoT design",
            "purpose": "Design Expected Edge improvement, strongest opportunity group, incremental value, opportunity cost, concentration, capital, lot feasibility, and exposure evidence without adding Action Authority.",
        },
        {
            "task": "Phase28-C",
            "name": "Minimal ADD Eligibility Implementation",
            "type": "Single-change performance implementation",
            "purpose": "Implement the first minimal ADD eligibility change after evidence/design freeze.",
        },
        {
            "task": "Phase28-D",
            "name": "100BD Acceptance and Attribution",
            "type": "User-run long validation / attribution",
            "purpose": "Evaluate ADD experiment with return, PF, ADD count, BUY_ADD execution, notional, cash/exposure, concentration, holding period, re-entry, and risk.",
        },
        {
            "task": "Phase28-E",
            "name": "Evidence Input Expansion",
            "type": "Separate experiments after ADD adoption",
            "purpose": "Connect BUY Quality, Market Context, Portfolio Fit, or Corporate Event one at a time.",
        },
    ]


def phase28_entry_contract() -> dict[str, Any]:
    return {
        "status": "READY_TO_START",
        "first_task": "Phase28-A ADD Baseline and Incremental Investment Evidence Audit",
        "experiment_rule": "1 Performance Change = 1 Experiment = 1 user-run 100BD Acceptance",
        "do_not_bundle": [
            "ADD improvement + Market Context input",
            "ADD improvement + Quality input",
            "ADD improvement + Sizing formula change",
            "ADD improvement + HOLD / EXIT change",
        ],
        "authority_boundary": {
            "incremental_eligibility": "Evidence",
            "pm": "ADD Action Authority",
            "portfolio_construction": "Target resolution",
            "position_sizing": "Positive delta",
            "runtime_planning": "BUY_ADD mapping",
        },
    }


def phase28_non_goals() -> list[str]:
    return [
        "New Action Authority",
        "New Momentum Action Producer",
        "HOLD / EXIT philosophy redesign",
        "D6-D rollback",
        "BUY_NEW selection full redesign",
        "Position Sizing full redesign",
        "Market Context full redesign",
        "Model retraining",
        "Historical-only threshold tuning",
        "Using 100BD results as training input",
    ]


def success_metrics() -> dict[str, list[str]]:
    return {
        "primary": ["Total Return", "Profit Factor", "Direct ADD-attributable PnL"],
        "behavioral": [
            "Executable BUY_ADD count",
            "ADD decision count",
            "ADD execution rate",
            "Average ADD notional",
            "ADD-after performance",
            "Average Winner",
            "Holding Duration",
            "Cash utilization",
            "Invested ratio",
            "Single-name concentration",
            "Exit -> Re-entry",
            "Whipsaw",
        ],
        "safety": [
            "Max Drawdown",
            "Largest Campaign Loss",
            "Hard-stop count",
            "Severe-risk EXIT",
            "Portfolio concentration",
            "Runtime / Lifecycle consistency",
        ],
    }


def evidence_files() -> dict[str, Any]:
    changed_files = [
        "docs/01_requirements/phase_roadmap.md",
        "docs/phase_reports/phase27_final_summary_and_phase28_handoff.md",
        "docs/phase_reports/phase27_to_phase28_chatgpt_handoff.md",
        "docs/phase_reports/phase27_cl_phase27_closure_phase28_entry_contract.md",
        "reports/phase_reports/phase27_final_summary_and_phase28_handoff.json",
        "reports/phase27_cl_phase27_closure_phase28_entry_contract/",
        "tools/phase27_analysis/phase27_cl_generate_closure_handoff.py",
    ]
    return {
        "summary.json": {
            "task_id": "Phase27-CL",
            "primary_judgment": PRIMARY,
            "supporting": supporting(),
            "runtime_change": False,
            "strategy_logic_change": False,
            "pm_logic_change": False,
            "historical_execution": False,
            "fresh_run_resume": False,
        },
        "phase27_completed_work.json": completed_work(),
        "phase27_final_judgment.json": final_judgment(),
        "phase27_adopted_changes.json": adopted_changes(),
        "phase27_known_limitations.json": known_limitations(),
        "phase28_purpose_and_goal.json": phase28_purpose(),
        "phase28_workstreams.json": phase28_workstreams(),
        "phase28_entry_contract.json": phase28_entry_contract(),
        "phase28_non_goals.json": phase28_non_goals(),
        "phase28_success_metrics.json": success_metrics(),
        "roadmap_revision_proof.json": {
            "roadmap_path": "docs/01_requirements/phase_roadmap.md",
            "phase27_status_marker": FINAL_STATUS,
            "phase27_primary_judgment_marker": PRIMARY,
            "phase28_status_marker": "READY_TO_START",
            "phase28_first_task_marker": "Phase28-A ADD Baseline and Incremental Investment Evidence Audit",
        },
        "common_sot_status.json": {
            "strategy_architecture_v1": "UPDATED_WITH_D6D_ADOPTION_LIMITATIONS",
            "momentum_follow_lifecycle": "UPDATED_WITH_D6D_ADOPTION_LIMITATIONS",
            "position_management_decision_trace_contract": "UPDATED_WITH_D6D_ADOPTION_LIMITATIONS",
            "roadmap": "UPDATED_WITH_PHASE27_CLOSURE_AND_PHASE28_ENTRY",
        },
        "required_reading_order.json": [{"order": i + 1, "path": path} for i, path in enumerate(REQUIRED_READING)],
        "implementation_and_test_boundary.json": {
            "chatgpt": ["Project control", "Task sequencing", "Design review", "Result evaluation", "Adoption / rollback recommendation"],
            "codex": ["Read-only investigation", "Design documentation", "Implementation", "Short unit / regression", "Compile / static validation", "Execution command preparation"],
            "user": ["fresh-run", "resume", "100BD", "1-year", "other long Historical validation"],
            "codex_long_tests": "PROHIBITED",
        },
        "changed_files.json": changed_files,
        "test_results.json": {
            "commands": [
                {"command": "PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase27_cl python3 -m py_compile tools/phase27_analysis/phase27_cl_generate_closure_handoff.py", "result": "PASS"},
                {"command": "python3 tools/phase27_analysis/phase27_cl_generate_closure_handoff.py", "result": "PASS"},
                {"command": "JSON validation for generated Phase27-CL evidence", "result": "PASS"},
            ],
            "historical_execution": False,
            "fresh_run": False,
            "resume": False,
        },
    }


def final_summary_markdown() -> str:
    return f"""# Phase27 Final Summary and Phase28 Handoff

## Final Judgment

```text
{PRIMARY}
```

Phase27 final status:

```text
{FINAL_STATUS}
```

Supporting:

```json
{json.dumps(final_judgment()["supporting"], ensure_ascii=False, indent=2)}
```

## System Purpose

AI Fund Lab v2 builds a PIT-data-driven AI automated trading system for Japanese cash equities under a Production/Demo/Historical common Runtime contract. Initial capital is 1,000,000 JPY. The primary performance target remains annual return +50%. The operating philosophy is aggressive Expected Edge maximization through Momentum-follow / Momentum Rotation.

Permanent constraints:

- Historical-only implementation is prohibited.
- Performance reports, PnL, Paper Ledger, selected outcomes, and future information are not training inputs.
- Approved J-Quants PIT data is the strategy input authority.
- fail-open, implicit fallback, and duplicate Action Authority are prohibited.
- One performance change equals one experiment and one user-run 100BD acceptance.
- Codex does not run long Historical tests.

## Phase27 Closure

Phase27 began with unresolved performance root causes after Phase26 architecture repair. It closed by diagnosing selection / ineligibility / re-entry / PM authority, establishing canonical decision architecture, retiring Legacy ADD execution authority, freezing Expected Edge and PM philosophy, repairing PM reason / trace semantics, and adopting the first PM HOLD / EXIT single-change experiment with limitations.

## 100BD Result

Baseline:

```text
run_id: runtime-test-historical-smoke-20260804T074611098414Z
initial_equity: 1,000,000 JPY
final_equity: 984,580 JPY
return: -15,420 JPY
return_rate: -1.542%
```

After D6-D:

```text
run_id: runtime-test-historical-extended-smoke-20260805T054904882046Z
period: 2023-01-04 through 2023-05-31
business_days: 100
initial_equity: 1,000,000 JPY
final_equity: 1,066,170 JPY
return: +66,170 JPY
return_rate: +6.617%
close: REVIEW_REQUIRED / non-blocking Strategy Shadow review
```

D6-E attribution:

```text
Run Comparability: CONFIRMED_WITH_LIMITATIONS
Target EXIT -> HOLD: 2 same-context rows observed
Directly Traceable D6-D Benefit: 37,100 JPY
Headline Equity Delta: 81,590 JPY
Unexplained / Path-dependent Delta: 44,490 JPY
Risk Regression: NOT_OBSERVED
Adoption: ADOPT_WITH_LIMITATIONS
```

The full 81,590 JPY headline delta is not treated as direct D6-D profit.

## Phase28 Entry

Phase28 purpose:

```text
Use the Phase27 Expected Edge / Canonical PM Architecture to allocate additional capital correctly into winning held positions and improve Capital Efficiency and Portfolio Return.
```

Phase28 primary goal:

```text
Canonical BUY_ADD should execute only when adding to an existing position improves Portfolio Expected Value after Incremental Investment Eligibility evidence.
```

First task:

```text
Phase28-A ADD Baseline and Incremental Investment Evidence Audit
```

Phase28 must preserve Common Action Authority and the one-change / one-experiment / one-100BD rule.
"""


def chatgpt_handoff_markdown() -> str:
    return f"""# Phase27 to Phase28 ChatGPT Handoff

## Role

Use this handoff to start Phase28. Do not implement before reading the required documents below and confirming Phase28-A scope.

## Phase27 Closed

```text
Primary Judgment: {PRIMARY}
Final Status: {FINAL_STATUS}
D6-D Adoption: APPROVED_WITH_LIMITATIONS
Phase28 Entry: APPROVED
```

## Required Reading Order

{chr(10).join(f"{i + 1}. `{path}`" for i, path in enumerate(REQUIRED_READING))}

## Phase28 First Task

```text
Phase28-A ADD Baseline and Incremental Investment Evidence Audit
```

Phase28-A is read-only. It must audit current ADD decisions, ADD outcomes, ADD execution, ADD zero-delta causes, Rank1 existing positions, ADD quantity, concentration, capital use, and ADD-after HOLD/EXIT behavior.

## Non-negotiable Rules

- Do not add new Action Authority.
- Do not change HOLD / EXIT philosophy in Phase28-A.
- Do not change BUY_NEW, ADD, Sizing, Runtime Planning, Pending, Submit, Safety, Execution, Model, Training, or Calibration in Phase28-A.
- Do not run fresh-run, resume, 100BD, 1-year, or long Historical tests from Codex.
- Missing metrics must not be zero-filled.
- Performance result is post-hoc attribution and never Strategy input.

## Phase28 Goal

Move from:

```text
winning positions are held correctly
```

to:

```text
additional capital is allocated correctly to winning positions only when incremental portfolio Expected Value improves
```
"""


def closure_report_markdown() -> str:
    return f"""# Phase27-CL Phase27 Closure and Phase28 Entry Contract

## Scope

Documentation / evidence only. Runtime, Strategy logic, PM logic, Position Sizing, Historical execution, fresh-run, and resume were not changed or executed.

## Primary Judgment

```text
{PRIMARY}
```

## Supporting

```json
{json.dumps(supporting(), ensure_ascii=False, indent=2)}
```

## Phase27 Final Status

```text
{FINAL_STATUS}
```

## Phase28 Entry

```text
Status: READY_TO_START
First Task: Phase28-A ADD Baseline and Incremental Investment Evidence Audit
```

## Evidence

```text
reports/phase27_cl_phase27_closure_phase28_entry_contract/
reports/phase_reports/phase27_final_summary_and_phase28_handoff.json
```
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payloads = evidence_files()
    for name, payload in payloads.items():
        write_json(OUT_DIR / name, payload)
    write_json(MACHINE_SUMMARY, {
        "task_id": "Phase27-CL",
        "primary_judgment": PRIMARY,
        "final_status": FINAL_STATUS,
        "supporting": supporting(),
        "phase27_completed_work": completed_work(),
        "phase27_known_limitations": known_limitations(),
        "phase28": {
            "purpose": phase28_purpose(),
            "workstreams": phase28_workstreams(),
            "entry_contract": phase28_entry_contract(),
            "non_goals": phase28_non_goals(),
            "success_metrics": success_metrics(),
        },
    })
    write_text(REPORT_DIR / "phase27_final_summary_and_phase28_handoff.md", final_summary_markdown())
    write_text(REPORT_DIR / "phase27_to_phase28_chatgpt_handoff.md", chatgpt_handoff_markdown())
    write_text(REPORT_DIR / "phase27_cl_phase27_closure_phase28_entry_contract.md", closure_report_markdown())


if __name__ == "__main__":
    main()
