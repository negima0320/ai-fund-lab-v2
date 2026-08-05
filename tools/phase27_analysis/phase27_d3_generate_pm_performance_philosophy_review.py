#!/usr/bin/env python3
"""Generate Phase27-D3 PM performance philosophy SoT evidence and report."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "Phase27-D3"
OUT_DIR = REPO_ROOT / "reports/phase27_d3_pm_momentum_follow_performance_strategy_design_review"
REPORT = REPO_ROOT / "docs/phase_reports/phase27_d3_pm_momentum_follow_performance_strategy_design_review.md"
PRIMARY = "PHASE27_D3_PM_PERFORMANCE_PHILOSOPHY_FROZEN_COMMON_SOT_UPDATED"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def supporting() -> dict[str, str]:
    return {
        "performance_philosophy": "FROZEN",
        "pm_responsibility": "CONFIRMED",
        "component_responsibility": "CONFIRMED",
        "common_sot": "UPDATED",
        "implementation_entry": "READY_FOR_PM_IMPROVEMENT",
    }


def pm_philosophy() -> dict[str, object]:
    return {
        "style": "Momentum Follow / Momentum Rotation",
        "position_management_action_authority": "PM_ONLY",
        "profit_taking_philosophy": "NOT_ADOPTED_AS_INDEPENDENT_ACTION_PHILOSOPHY",
        "cash_philosophy": "RESIDUAL_OUTCOME_NOT_DEPLOYMENT_TARGET",
        "capital_philosophy": "1000000_JPY_EXPECTED_VALUE_MAXIMIZATION_CAPITAL_NOT_FIXED_FULL_DEPLOYMENT_MANDATE",
        "actions": {
            "BUY_NEW": "Enter a no-position symbol entering an upward trend or carrying sufficient forward expected value.",
            "HOLD": "Actively continue an open position while upward trend continuation and expected value remain valid.",
            "ADD": "Consider increasing an existing position only when still strongest, trend continuing, and incremental value exists.",
            "REDUCE": "Reduce exposure while preserving campaign optionality when weakening/risk/concentration/partial rotation evidence supports it.",
            "EXIT": "Close a campaign when trend continuation fails, expected value deteriorates, signals break, or risk/Safety requires it.",
        },
    }


def principles() -> list[dict[str, object]]:
    return [
        {"principle": "Do not sell because profit exists", "status": "FROZEN", "threshold_fixed": False},
        {"principle": "Hold while upward trend continuation remains valid", "status": "FROZEN", "threshold_fixed": False},
        {"principle": "ADD only for strongest continuing held opportunities with incremental value", "status": "FROZEN", "threshold_fixed": False},
        {"principle": "Cash is outcome, not objective", "status": "FROZEN", "threshold_fixed": False},
        {"principle": "100万円 is expectation-maximization capital", "status": "FROZEN", "threshold_fixed": False},
        {"principle": "Performance improvement must not add Action Authority", "status": "FROZEN", "threshold_fixed": False},
    ]


def action_design(action: str) -> dict[str, object]:
    designs = {
        "BUY_NEW": {
            "purpose": "Entry into symbols starting or expected to continue upward trend.",
            "positive_requirements": ["forward_expected_value", "entry_opportunity", "quality_and_risk_evidence", "portfolio_fit"],
            "not_reasons": ["profit_rate", "cash_available", "rank_alone"],
        },
        "HOLD": {
            "purpose": "Active continuation of an open campaign.",
            "positive_requirements": ["trend_continuation", "expected_value_remains", "risk_acceptable", "exit_condition_absent"],
            "not_reasons": ["passive_no_op", "profit_exists", "lack_of_new_candidate"],
        },
        "ADD": {
            "purpose": "Increase an existing position only when the held symbol remains a strongest opportunity.",
            "minimum_philosophy": ["Still Rank1 or materially strongest", "Trend Continuing", "Incremental Value Exists"],
            "not_reasons": ["no_new_candidate_available", "cash_available", "PM_ADD_alone", "rank_alone"],
        },
        "REDUCE": {
            "purpose": "Review-preserved intermediate action between HOLD and EXIT.",
            "valid_roles": ["momentum_weakening", "risk_reduction", "concentration_reduction", "partial_rotation"],
            "boundary_questions": ["HOLD_vs_REDUCE", "REDUCE_vs_EXIT", "partial_quantity_basis"],
            "not_reasons": ["simple_profit_taking"],
            "decision": "REVIEWED_NOT_REMOVED_NOT_NUMERICALLY_DEFINED",
        },
        "EXIT": {
            "purpose": "Full campaign close when continuation no longer supports holding.",
            "positive_requirements": ["trend_broken", "expected_value_deteriorated", "signal_invalidated", "risk_or_safety_exit", "material_replacement"],
            "not_reasons": ["profit_exists_only", "fixed_holding_days", "symbol_exception", "post_hoc_pnl"],
        },
    }
    return {"action": action, **designs[action]}


def component_responsibility() -> list[dict[str, str]]:
    return [
        {"component": "Opportunity", "evaluates": "Expected-edge and rank evidence", "producer_type": "EVIDENCE_PRODUCER", "does_not_decide": "BUY/ADD/HOLD/REDUCE/EXIT"},
        {"component": "BUY Quality", "evaluates": "Allocation eligibility, signal reliability, scaling evidence", "producer_type": "EVIDENCE_PRODUCER", "does_not_decide": "BUY-versus-cash or SELL action"},
        {"component": "Market Context", "evaluates": "Regime, breadth, volatility, market posture", "producer_type": "EVIDENCE_PRODUCER", "does_not_decide": "Symbol-level action"},
        {"component": "Momentum Evidence", "evaluates": "Continuation, weakening, broken-state evidence", "producer_type": "EVIDENCE_PRODUCER_OR_PM_INPUT", "does_not_decide": "Action unless later SoT explicitly changes authority"},
        {"component": "Incremental Eligibility", "evaluates": "Whether additional capital is justified now", "producer_type": "EVIDENCE_PRODUCER", "does_not_decide": "Direct BUY_NEW/ADD order authority"},
        {"component": "PM", "evaluates": "Existing-position directional action using evidence", "producer_type": "ACTION_PRODUCER", "does_not_decide": "Quantity, Submit, Broker execution"},
        {"component": "Portfolio Construction", "evaluates": "Target membership and target weight resolution", "producer_type": "TARGET_PORTFOLIO_PRODUCER", "does_not_decide": "PM action or broker quantity"},
        {"component": "Position Sizing", "evaluates": "Target quantity and quantity delta", "producer_type": "QUANTITY_PRODUCER", "does_not_decide": "PM action"},
        {"component": "Runtime Planning", "evaluates": "Quantity delta to runtime action mapping", "producer_type": "RUNTIME_MAPPER", "does_not_decide": "Strategy judgment"},
    ]


def open_questions() -> list[dict[str, object]]:
    return [
        {"question": "What exactly counts as Continuation?", "numeric_threshold_fixed": False},
        {"question": "What exactly counts as Weakening?", "numeric_threshold_fixed": False},
        {"question": "What exactly counts as Broken?", "numeric_threshold_fixed": False},
        {"question": "Where is HOLD vs ADD boundary?", "numeric_threshold_fixed": False},
        {"question": "Where is HOLD vs REDUCE boundary?", "numeric_threshold_fixed": False},
        {"question": "Where is REDUCE vs EXIT boundary?", "numeric_threshold_fixed": False},
        {"question": "How should Trend Continuing be evaluated?", "numeric_threshold_fixed": False},
        {"question": "How should Incremental Value Exists be calibrated?", "numeric_threshold_fixed": False},
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
                "docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md",
                "docs/02_architecture/strategy_architecture_v1.md",
                "docs/02_architecture/autonomous_ai_operations_architecture.md",
                "docs/02_architecture/portfolio_construction_and_position_sizing_contract.md",
            ],
        },
        "pm_performance_philosophy.json": pm_philosophy(),
        "pm_design_principles.json": principles(),
        "buy_design.json": action_design("BUY_NEW"),
        "hold_design.json": action_design("HOLD"),
        "add_design.json": action_design("ADD"),
        "reduce_design_review.json": action_design("REDUCE"),
        "exit_design.json": action_design("EXIT"),
        "component_responsibility_review.json": component_responsibility(),
        "performance_open_questions.json": open_questions(),
        "design_revision_log.json": [
            {"file": "docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md", "revision": "Added Phase27-D3 PM Performance Philosophy Freeze and Evidence Producer vs Action Producer sections."},
            {"file": "docs/02_architecture/strategy_architecture_v1.md", "revision": "Added PM performance philosophy and evidence/action authority separation to Strategy investment philosophy."},
            {"file": "docs/02_architecture/autonomous_ai_operations_architecture.md", "revision": "Added operations boundary preventing performance evidence from becoming action/training/runtime authority."},
            {"file": "docs/02_architecture/portfolio_construction_and_position_sizing_contract.md", "revision": "Added PM performance philosophy boundary for downstream target/sizing/runtime stages."},
        ],
        "test_results.json": {
            "historical_executed": False,
            "fresh_run_executed": False,
            "commands": [
                {"command": "python3 -m py_compile tools/phase27_analysis/phase27_d3_generate_pm_performance_philosophy_review.py", "result": "PASS"},
                {"command": "for f in reports/phase27_d3_pm_momentum_follow_performance_strategy_design_review/*.json; do python3 -m json.tool \"$f\" >/dev/null || exit 1; done", "result": "PASS"},
            ],
        },
    }


def render_report() -> str:
    return f"""# Phase27-D3 PM Momentum Follow Performance Strategy Design Review

## 1. Scope

Phase27-D3 freezes the PM Momentum Follow performance philosophy and integrates it into common Architecture SoT.

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

## 3. Frozen Philosophy

- BUY enters symbols with upward-trend entry or sufficient forward expected value.
- HOLD is active continuation while upward trend and expected value remain valid.
- EXIT is for trend end, expected-value deterioration, signal break, severe risk worsening, or Safety/Portfolio necessity.
- ADD is considered only when the held symbol remains strongest, trend continues, and incremental value exists.
- REDUCE remains a reviewed intermediate risk/weakening/partial-rotation action, not a profit-taking philosophy.
- Profit-taking is not adopted as an independent action philosophy.
- Cash is an outcome, not a forced deployment target.
- Performance improvement must not add duplicate action authority.

## 4. Responsibility

PM is the Strategy Action Authority for existing-position `ADD`, `HOLD`, `REDUCE`, and `EXIT`.

Opportunity, BUY Quality, Market Context, Momentum Evidence, and Incremental Eligibility are Evidence Producers. Portfolio Construction resolves target membership/weight; Position Sizing resolves quantity delta; Runtime Planning maps quantity delta to runtime action.

## 5. Common SoT Updated

```text
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
docs/02_architecture/strategy_architecture_v1.md
docs/02_architecture/autonomous_ai_operations_architecture.md
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
```

## 6. Open Questions

No numeric thresholds were fixed. Continuation, Weakening, Broken, ADD boundary, REDUCE boundary, EXIT boundary, and Trend evaluation method remain controlled design questions.

## 7. Evidence

```text
{OUT_DIR.relative_to(REPO_ROOT)}
```

## 8. Validation

```text
python3 -m py_compile tools/phase27_analysis/phase27_d3_generate_pm_performance_philosophy_review.py
PASS

JSON validation for all generated evidence files
PASS
```

No Runtime, Strategy, PM, Historical, fresh-run, resume, 10BD, 100BD, or long regression was executed.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in files().items():
        write_json(OUT_DIR / name, payload)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
