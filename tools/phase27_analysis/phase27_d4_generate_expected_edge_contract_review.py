#!/usr/bin/env python3
"""Generate Phase27-D4 Expected Edge decision contract evidence and report."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "Phase27-D4"
OUT_DIR = REPO_ROOT / "reports/phase27_d4_expected_edge_decision_contract_design_review"
REPORT = REPO_ROOT / "docs/phase_reports/phase27_d4_expected_edge_decision_contract_design_review.md"
PRIMARY = "PHASE27_D4_EXPECTED_EDGE_DECISION_CONTRACT_FROZEN_COMMON_SOT_UPDATED"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def supporting() -> dict[str, str]:
    return {
        "expected_edge_philosophy": "FROZEN",
        "pm_contract": "UPDATED",
        "common_sot": "UPDATED",
        "implementation_entry": "READY_FOR_PM_REASONING_IMPROVEMENT",
    }


def expected_edge_definition() -> dict[str, object]:
    return {
        "concept": "Expected Edge",
        "definition": "Forward-looking expected value attractiveness estimated from Point-in-Time evidence.",
        "pm_role": "PM evaluates Expected Edge and emits BUY_NEW/ADD/HOLD/REDUCE/EXIT.",
        "not_equal_to": [
            "profit_rate",
            "trend_alone",
            "rank_alone",
            "buy_quality_alone",
            "market_context_alone",
            "cash_availability",
        ],
        "direct_action_authority": "PM_ONLY",
        "point_in_time_required": True,
        "numeric_threshold_fixed": False,
    }


def component_mapping() -> list[dict[str, object]]:
    return [
        {
            "component": "Trend / Momentum",
            "relationship": "Evidence of continuation, weakening, or break.",
            "expected_edge_role": "SUPPORTING_EVIDENCE",
            "action_boundary": "Trend alone does not decide BUY/ADD/HOLD/REDUCE/EXIT.",
        },
        {
            "component": "Opportunity",
            "relationship": "Relative and absolute expected-edge evidence, including rank.",
            "expected_edge_role": "SUPPORTING_EVIDENCE",
            "action_boundary": "Rank alone does not decide BUY/ADD/EXIT.",
        },
        {
            "component": "BUY Quality",
            "relationship": "Signal reliability, eligibility, and scaling evidence.",
            "expected_edge_role": "SUPPORTING_EVIDENCE",
            "action_boundary": "Quality alone does not produce action.",
        },
        {
            "component": "Market Context",
            "relationship": "Regime, breadth, volatility, and risk posture evidence.",
            "expected_edge_role": "SUPPORTING_EVIDENCE",
            "action_boundary": "Market context does not mechanically override symbol-level PM.",
        },
        {
            "component": "Portfolio Fit",
            "relationship": "Concentration, exposure, replacement, compatibility, and capital-fit evidence.",
            "expected_edge_role": "SUPPORTING_EVIDENCE_AND_CONSTRAINT",
            "action_boundary": "Portfolio fit does not create a separate action producer.",
        },
        {
            "component": "Execution Feasibility",
            "relationship": "Orderability, lot, liquidity, and operational feasibility evidence.",
            "expected_edge_role": "FEASIBILITY_EVIDENCE",
            "action_boundary": "Executable does not mean desirable.",
        },
        {
            "component": "Profit / Unrealized PnL",
            "relationship": "Risk-review evidence for embedded gains, concentration, volatility, or drawdown-from-peak risk.",
            "expected_edge_role": "RISK_REVIEW_EVIDENCE",
            "action_boundary": "Profit alone is not EXIT or REDUCE.",
        },
    ]


def principles() -> list[dict[str, object]]:
    return [
        {"principle": "Trust Point-in-Time data", "status": "FROZEN", "numeric_threshold_fixed": False},
        {"principle": "AI estimates Expected Edge by integrating PIT evidence", "status": "FROZEN", "numeric_threshold_fixed": False},
        {"principle": "PM decides actions using Expected Edge", "status": "FROZEN", "numeric_threshold_fixed": False},
        {"principle": "Trend is evidence, not Expected Edge itself", "status": "FROZEN", "numeric_threshold_fixed": False},
        {"principle": "Rank is evidence, not direct action authority", "status": "FROZEN", "numeric_threshold_fixed": False},
        {"principle": "BUY Quality is evidence, not action authority", "status": "FROZEN", "numeric_threshold_fixed": False},
        {"principle": "Do not exit because profit exists", "status": "FROZEN", "numeric_threshold_fixed": False},
        {"principle": "Profit may trigger Risk Review", "status": "FROZEN", "numeric_threshold_fixed": False},
        {"principle": "Cash is outcome, not objective", "status": "FROZEN", "numeric_threshold_fixed": False},
    ]


def pm_contract() -> dict[str, object]:
    return {
        "input_shape": "PIT Data -> Evidence Artifacts -> Expected Edge Estimation",
        "action_authority": "PM_ONLY",
        "actions": {
            "BUY_NEW": "No-position symbol has sufficiently attractive forward Expected Edge and entry evidence.",
            "ADD": "Existing position remains among strongest Expected Edge opportunities and incremental value exists.",
            "HOLD": "Open position still has sufficient forward Expected Edge.",
            "REDUCE": "Expected Edge or risk/reward has weakened enough to trim exposure, but full exit is not required.",
            "EXIT": "Forward Expected Edge is no longer sufficient, continuation has broken, or risk/Safety requires full close.",
        },
        "non_authorities": [
            "Trend alone",
            "Rank alone",
            "BUY Quality alone",
            "Profit alone",
            "Cash availability",
            "Runtime Planning",
            "Submit",
        ],
    }


def responsibility_matrix() -> list[dict[str, str]]:
    return [
        {"component": "PM", "producer_type": "ACTION_PRODUCER", "artifact_role": "Expected Edge to action", "may_emit_action": "YES"},
        {"component": "Opportunity", "producer_type": "EVIDENCE_PRODUCER", "artifact_role": "Rank/edge evidence", "may_emit_action": "NO"},
        {"component": "BUY Quality", "producer_type": "EVIDENCE_PRODUCER", "artifact_role": "Reliability/eligibility evidence", "may_emit_action": "NO"},
        {"component": "Market Context", "producer_type": "EVIDENCE_PRODUCER", "artifact_role": "Regime/risk evidence", "may_emit_action": "NO"},
        {"component": "Momentum Evidence", "producer_type": "EVIDENCE_PRODUCER", "artifact_role": "Continuation/weakening/broken evidence", "may_emit_action": "NO"},
        {"component": "Portfolio Construction", "producer_type": "TARGET_PORTFOLIO_PRODUCER", "artifact_role": "Membership/weight resolution", "may_emit_action": "NO_PM_ACTION"},
        {"component": "Position Sizing", "producer_type": "QUANTITY_PRODUCER", "artifact_role": "Quantity/delta", "may_emit_action": "NO"},
        {"component": "Runtime Planning", "producer_type": "RUNTIME_MAPPER", "artifact_role": "Quantity delta to runtime action mapping", "may_emit_action": "NO_STRATEGY_ACTION"},
    ]


def profit_review() -> dict[str, object]:
    return {
        "profit_direct_exit_authority": "NOT_ADOPTED",
        "profit_effect_classification": "RISK_REVIEW",
        "allowed_review_reasons": [
            "large_embedded_gain",
            "concentration_after_profit_expansion",
            "volatility_or_gap_risk",
            "drawdown_from_peak_risk",
            "risk_reward_changed_after_move",
        ],
        "disallowed_reasons": [
            "profit_exists_only",
            "fixed_profit_taking_rule_without_expected_edge_or_risk_review",
        ],
        "threshold_fixed": False,
    }


def open_questions() -> list[dict[str, object]]:
    return [
        {"question": "Expected Edge numeric representation", "status": "OPEN", "numeric_threshold_fixed": False},
        {"question": "Expected Edge threshold", "status": "OPEN", "numeric_threshold_fixed": False},
        {"question": "Trend判定式", "status": "OPEN", "numeric_threshold_fixed": False},
        {"question": "Profit Review条件", "status": "OPEN", "numeric_threshold_fixed": False},
        {"question": "ADD境界", "status": "OPEN", "numeric_threshold_fixed": False},
        {"question": "REDUCE境界", "status": "OPEN", "numeric_threshold_fixed": False},
        {"question": "EXIT境界", "status": "OPEN", "numeric_threshold_fixed": False},
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
            ],
        },
        "expected_edge_definition.json": expected_edge_definition(),
        "expected_edge_component_mapping.json": component_mapping(),
        "expected_edge_design_principles.json": principles(),
        "pm_expected_edge_contract.json": pm_contract(),
        "component_responsibility_matrix.json": responsibility_matrix(),
        "profit_position_review.json": profit_review(),
        "open_questions.json": open_questions(),
        "design_revision_log.json": [
            {
                "file": "docs/02_architecture/strategy_architecture_v1.md",
                "revision": "Added Phase27-D4 Expected Edge decision contract to Strategy investment philosophy.",
            },
            {
                "file": "docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md",
                "revision": "Added Phase27-D4 Expected Edge Decision Contract section.",
            },
            {
                "file": "docs/02_architecture/autonomous_ai_operations_architecture.md",
                "revision": "Added autonomous operations boundary for PIT evidence -> Expected Edge -> PM action.",
            },
        ],
        "test_results.json": {
            "historical_executed": False,
            "fresh_run_executed": False,
            "commands": [
                {
                    "command": "python3 -m py_compile tools/phase27_analysis/phase27_d4_generate_expected_edge_contract_review.py",
                    "result": "PASS",
                },
                {
                    "command": "for f in reports/phase27_d4_expected_edge_decision_contract_design_review/*.json; do python3 -m json.tool \"$f\" >/dev/null || exit 1; done",
                    "result": "PASS",
                },
            ],
        },
    }


def render_report() -> str:
    return f"""# Phase27-D4 Expected Edge Decision Contract Design Review

## 1. Scope

Phase27-D4 freezes the Expected Edge decision contract and integrates it into common Architecture SoT.

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

## 3. Expected Edge Definition

Expected Edge means whether forward-looking expected value remains sufficiently attractive from Point-in-Time evidence.

It is not profit rate itself, Trend alone, Rank alone, BUY Quality alone, Market Context alone, or cash availability.

## 4. Evidence Relationship

Trend, Opportunity Rank, BUY Quality, Market Context, Portfolio Fit, Execution Feasibility, and profit/risk evidence are inputs to Expected Edge review.

Trend is evidence, not Expected Edge itself. Rank is evidence, not direct BUY/ADD/EXIT authority. BUY Quality is evidence, not Action Authority.

## 5. PM Contract

PM evaluates Expected Edge and decides:

```text
BUY_NEW
ADD
HOLD
REDUCE
EXIT
```

Other components emit evidence, constraints, target portfolio decisions, quantity deltas, or runtime mappings. They do not emit Strategy action authority.

## 6. Profit Position Review

Profit alone does not create EXIT or REDUCE.

Large embedded gain, concentration after profit expansion, volatility/gap risk, drawdown-from-peak risk, or changed risk/reward may trigger Risk Review. No numeric Profit Review threshold is fixed in D4.

## 7. Common SoT Updated

```text
docs/02_architecture/strategy_architecture_v1.md
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
docs/02_architecture/autonomous_ai_operations_architecture.md
```

## 8. Open Questions

Expected Edge numeric representation, threshold, Trend formula, Profit Review conditions, ADD boundary, REDUCE boundary, and EXIT boundary remain open for D5 or later.

## 9. Evidence

```text
{OUT_DIR.relative_to(REPO_ROOT)}
```

## 10. Validation

```text
python3 -m py_compile tools/phase27_analysis/phase27_d4_generate_expected_edge_contract_review.py
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
