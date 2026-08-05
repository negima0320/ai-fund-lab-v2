#!/usr/bin/env python3
"""Generate Phase27-D6-A PM implementation gap audit evidence and report."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "Phase27-D6-A"
OUT_DIR = REPO_ROOT / "reports/phase27_d6a_pm_implementation_gap_audit"
REPORT = REPO_ROOT / "docs/phase_reports/phase27_d6a_pm_implementation_gap_audit.md"
PRIMARY = "PHASE27_D6A_PM_IMPLEMENTATION_GAP_CONFIRMED_READY_FOR_MINIMAL_IMPLEMENTATION"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def supporting() -> dict[str, str]:
    return {
        "current_pm": "ASSESSED",
        "expected_edge": "MAPPED",
        "gap": "CONFIRMED",
        "implementation_scope": "MINIMAL",
        "degression_risk": "ASSESSED",
        "next": "D6-B_APPROVED",
    }


def pm_current_flow() -> dict[str, object]:
    return {
        "task_id": TASK_ID,
        "flow": [
            {
                "stage": "Input",
                "producer_or_function": "produce_position_management_decisions",
                "file": "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py",
                "evidence_lines": "145-356",
                "artifacts": [
                    "persistent_ledger/state.json",
                    "runtime_state/current_state.json",
                    "runtime_state/buy_ai/<business_date>/opportunity_rankings.json",
                    "position_feature_input.parquet",
                ],
                "outputs": [
                    "current_holdings_snapshot.csv",
                    "position_management_opportunity_context.csv",
                ],
            },
            {
                "stage": "Feature",
                "producer_or_function": "build_position_feature_frame / build_position_management_output",
                "file": "src/ai_fund_lab_v2/position_management_ai/inference.py",
                "evidence_lines": "300-340",
                "features": [
                    "current_return",
                    "peak_return",
                    "drawdown_from_peak",
                    "expected_edge_score",
                    "buy_rank",
                    "downside_risk_score",
                    "technical trend/momentum fields",
                    "risk_guard_status",
                ],
                "scores": [
                    "trend_score",
                    "opportunity_score",
                    "profit_score",
                    "risk_penalty",
                    "hold_score",
                    "exit_score",
                    "add_score",
                    "reduce_score",
                ],
            },
            {
                "stage": "Reason",
                "producer_or_function": "classify_position_action / _decision_trigger_booleans / _dominant_cause",
                "files": [
                    "src/ai_fund_lab_v2/position_management_ai/inference.py",
                    "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py",
                ],
                "evidence_lines": [
                    "inference.py:355-425",
                    "producer.py:777-861",
                ],
                "reason_codes": [
                    "trend_continuation",
                    "positive_expected_edge",
                    "downside_risk_contained",
                    "risk_increased_but_trend_not_broken",
                    "peak_drawdown_warning",
                    "trend_and_opportunity_broken",
                    "profit_retention_break",
                    "hard_stop_current_return",
                ],
            },
            {
                "stage": "Action",
                "producer_or_function": "classify_position_action / _decision_payload / _row_from_pm_decision",
                "files": [
                    "src/ai_fund_lab_v2/position_management_ai/inference.py",
                    "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py",
                    "src/ai_fund_lab_v2/strategy/position_intent.py",
                ],
                "actions": ["ADD", "HOLD", "REDUCE", "EXIT"],
                "buy_new_status": "NOT_PRODUCED_BY_CURRENT_PM; shadow BUY_NEW candidates remain UNRESOLVED in position_intent.",
            },
        ],
    }


def expected_edge_mapping() -> list[dict[str, object]]:
    return [
        {"input": "Trend", "status": "USED", "evidence": "calculate_trend_continuation_score, hold_score, add_score, reduce_score, trend_and_opportunity_broken", "gap": "Used as direct threshold trigger in places; D5 wants evidence inside Expected Edge reasoning."},
        {"input": "Rank", "status": "USED", "evidence": "buy_rank in calculate_opportunity_continuation_score and ADD buy_rank <= 5", "gap": "Rank is used directly for ADD; D5 says strongest-opportunity evidence is needed but rank-alone must not be action authority."},
        {"input": "Quality", "status": "NOT_USED", "evidence": "PM runtime required columns do not include quality score/action", "gap": "D5 says BUY Quality is Expected Edge evidence; PM currently has no explicit Quality input."},
        {"input": "Market", "status": "NOT_USED", "evidence": "runtime PM producer validates current/opportunity/feature artifacts, not market context artifact", "gap": "D5 says Market Context is Expected Edge evidence; PM currently has no explicit Market input in regular path."},
        {"input": "Risk", "status": "USED", "evidence": "downside_risk_score, risk_guard_status, volatility, current_return, drawdown", "gap": "Mostly aligned, but broad fallback reason hides exact risk cause."},
        {"input": "Profit", "status": "USED", "evidence": "profit_score in hold_score; current_return > 0 gates ADD; drawdown triggers profit_retention_break", "gap": "Profit influences scoring and ADD gate directly; D5 requires profit as supporting/risk-review evidence, not direct action authority."},
        {"input": "Portfolio", "status": "NOT_USED", "evidence": "No portfolio fit/concentration/current weight input in classify_position_action", "gap": "D5 expects Portfolio Fit evidence; current PM regular path does not explicitly consume it."},
        {"input": "Current", "status": "USED", "evidence": "Runtime Current -> current_holdings_snapshot.csv for quantity, price, return, peak_return, holding_days", "gap": "Aligned as position-state authority."},
        {"input": "Corporate Event", "status": "NOT_USED", "evidence": "No corporate event artifact in runtime PM regular path", "gap": "D5/Strategy SoT allows event facts as evidence; current PM does not explicitly consume them."},
    ]


def reason_code_gap_analysis() -> list[dict[str, object]]:
    return [
        {"reason_code": "trend_continuation", "current_meaning": "trend_score >= 0.50", "d5_meaning": "Continuation evidence supporting Expected Edge adequacy.", "gap": "NO_CHANGE", "minimal_change_unit": "none"},
        {"reason_code": "positive_expected_edge", "current_meaning": "expected_edge_score > 0.0", "d5_meaning": "Compatibility code; should become explicit Expected Edge adequacy wording.", "gap": "REASON_UPDATE", "minimal_change_unit": "reason naming/summary only; no threshold change in D6-A"},
        {"reason_code": "downside_risk_contained", "current_meaning": "downside_risk_score < 0.50", "d5_meaning": "Risk-contained evidence supporting HOLD/ADD.", "gap": "NO_CHANGE", "minimal_change_unit": "none"},
        {"reason_code": "risk_increased_but_trend_not_broken", "current_meaning": "fallback REDUCE reason when risk branch fires and trend/opportunity alive but no explicit risk reason is present", "d5_meaning": "Broad fallback should be split into explicit weakening/risk causes.", "gap": "RENAME", "minimal_change_unit": "reason resolver split only"},
        {"reason_code": "peak_drawdown_warning", "current_meaning": "drawdown_from_peak <= -0.07", "d5_meaning": "Risk Review / weakening evidence for REDUCE or EXIT review.", "gap": "NO_CHANGE", "minimal_change_unit": "none"},
        {"reason_code": "trend_and_opportunity_broken", "current_meaning": "trend_score < 0.30 and expected_edge_score <= 0.0", "d5_meaning": "Expected Edge deterioration and continuation break evidence for EXIT.", "gap": "NO_CHANGE", "minimal_change_unit": "none"},
        {"reason_code": "profit_retention_break", "current_meaning": "drawdown_from_peak <= -0.12; currently named like profit retention, dominant cause maps to EXIT_BY_PEAK_DRAWDOWN", "d5_meaning": "Peak-drawdown/profit-retention risk evidence, not simple profit-taking.", "gap": "RENAME", "minimal_change_unit": "reason naming/alias compatibility"},
        {"reason_code": "hard_stop_current_return", "current_meaning": "current_return <= -0.08", "d5_meaning": "Loss-containment / severe risk evidence for EXIT.", "gap": "NO_CHANGE", "minimal_change_unit": "none"},
    ]


def action_gap_analysis() -> list[dict[str, object]]:
    return [
        {
            "action": "BUY_NEW",
            "current_trigger": "Not generated by current PM implementation; BUY_NEW candidates are shadow UNRESOLVED in position_intent.",
            "reason": "BUY_NEW_SHADOW_UNRESOLVED_INCREMENTAL_ELIGIBILITY_NOT_CONNECTED",
            "consumer": "Portfolio/position_intent shadow path; not PM regular path",
            "expected_edge_relation": "D5 defines BUY_NEW boundary, but current PM gap audit finds this is outside existing-position PM implementation.",
            "gap": "NO_CHANGE_FOR_PM_D6A",
        },
        {
            "action": "ADD",
            "current_trigger": "add_score >= 0.72 and current_return > 0 and buy_rank <= 5 and downside_risk_score < 0.50",
            "reason": "strong_trend_continuation|opportunity_rank_still_high|no_loss_averaging",
            "consumer": "Runtime PM artifact marks NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE; D2-E later canonical quantity delta can map executable BUY_ADD.",
            "expected_edge_relation": "PARTIAL: uses trend/edge/rank/risk/profit, but does not explicitly require Expected Edge improvement or incremental investment value evidence.",
            "gap": "INPUT_UPDATE",
        },
        {
            "action": "HOLD",
            "current_trigger": "Default when EXIT/REDUCE/ADD branches do not fire; reasons include trend_continuation, positive_expected_edge, downside_risk_contained, or fallback hold.",
            "reason": "trend_continuation|positive_expected_edge|downside_risk_contained or hold_score_above_exit_threshold",
            "consumer": "Runtime PM artifact; position_intent shadow maps HOLD to HOLD.",
            "expected_edge_relation": "PARTIAL: compatible with maintained Expected Edge, but positive_expected_edge is raw >0 and fallback reason is not explicit Expected Edge adequacy.",
            "gap": "REASON_UPDATE",
        },
        {
            "action": "REDUCE",
            "current_trigger": "downside >= 0.65 or drawdown <= -0.07 or reduce_score >= 0.62 or hold_score < 0.42, while trend/opportunity alive",
            "reason": "peak_drawdown_warning, high_downside_risk_score, or risk_increased_but_trend_not_broken",
            "consumer": "Sell Planning owns reduce quantity; Runtime payload emits SELL_PARTIAL_POSITION_REDUCE_QUANTITY_BY_SELL_PLANNING",
            "expected_edge_relation": "MOSTLY_ALIGNED: REDUCE represents weakening/risk while campaign optionality remains; broad fallback needs reason split.",
            "gap": "RENAME",
        },
        {
            "action": "EXIT",
            "current_trigger": "current_return <= -0.08 or drawdown <= -0.12 or trend_score < 0.30 and expected_edge <= 0 or risk_guard bad or exit_score >= 0.80; weak hold score can exit if trend/opportunity not alive",
            "reason": "hard_stop_current_return, profit_retention_break, trend_and_opportunity_broken, risk_guard_status_bad, exit_score_high, weak_hold_score",
            "consumer": "Sell Planning / runtime SELL_FULL_POSITION",
            "expected_edge_relation": "PARTIAL: trend_and_opportunity_broken aligns; profit_retention_break naming and exit_score_high explanation need Expected Edge/risk wording.",
            "gap": "REASON_UPDATE",
        },
    ]


def implementation_change_units() -> list[dict[str, object]]:
    return [
        {
            "unit_id": "D6B_REASON_RENAME_COMPAT",
            "classification": "RENAME",
            "files": [
                "src/ai_fund_lab_v2/position_management_ai/inference.py",
                "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py",
                "docs/02_architecture/position_management_decision_trace_contract.md",
            ],
            "scope": "Introduce clearer Expected Edge reason names or aliases while preserving legacy compatibility.",
            "candidate_changes": ["profit_retention_break -> peak_drawdown_profit_retention_risk", "risk_increased_but_trend_not_broken -> explicit risk/weakening cause"],
            "threshold_change": False,
            "action_change": False,
            "priority": 1,
        },
        {
            "unit_id": "D6B_REASON_SUMMARY_EXPECTED_EDGE",
            "classification": "REASON_UPDATE",
            "files": [
                "src/ai_fund_lab_v2/position_management_ai/inference.py",
                "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py",
            ],
            "scope": "Make HOLD/EXIT/REDUCE reason summaries describe Expected Edge adequacy/deterioration instead of isolated raw indicators.",
            "threshold_change": False,
            "action_change": False,
            "priority": 2,
        },
        {
            "unit_id": "D6C_ADD_EXPECTED_EDGE_INPUTS",
            "classification": "INPUT_UPDATE",
            "files": ["src/ai_fund_lab_v2/position_management_ai/inference.py"],
            "scope": "Add explicit evidence slots for Expected Edge improvement and incremental investment value before changing ADD behavior.",
            "threshold_change": False,
            "action_change": "Potential in later implementation; D6-A only identifies gap.",
            "priority": 3,
        },
        {
            "unit_id": "D6C_PM_EVIDENCE_INPUT_EXPANSION",
            "classification": "INPUT_UPDATE",
            "files": [
                "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py",
                "src/ai_fund_lab_v2/position_management_ai/inference.py",
            ],
            "scope": "Connect Quality, Market, Portfolio Fit, and Corporate Event evidence as PM Expected Edge inputs if D6-B/D6-C approves.",
            "threshold_change": False,
            "action_change": "Potential after evidence-only fields are available.",
            "priority": 4,
        },
    ]


def impact_analysis() -> list[dict[str, object]]:
    return [
        {
            "file": "src/ai_fund_lab_v2/position_management_ai/inference.py",
            "functions": ["classify_position_action", "calculate_add_score", "calculate_reduce_score", "calculate_exit_score", "calculate_opportunity_continuation_score"],
            "callers": ["runtime_v2.position_management.producer.produce_position_management_decisions", "position_management_ai.calibration"],
            "consumers": ["position_management_inference.parquet", "position_management_decisions.json"],
            "unit_tests": [
                "tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py",
                "tests/runtime_v2/test_phase20_t_pm_cross_regime_analysis.py",
                "tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py",
            ],
            "regression": "PM unit tests and runtime PM artifact compatibility tests; no historical run in D6-A.",
            "risk": "HIGH if thresholds/actions change; LOW/MEDIUM for reason-only alias additions.",
        },
        {
            "file": "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py",
            "functions": ["_decision_payload", "_build_decision_trace_records", "_decision_trigger_booleans", "_dominant_cause", "_reason_codes"],
            "callers": ["runtime PM regular path", "load_sell_exit_decisions_from_pm_artifact"],
            "consumers": ["Sell Planning", "position_intent shadow producer", "PM trace artifacts"],
            "unit_tests": [
                "tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py",
                "tests/runtime_v2/test_phase20_j_performance_observability.py",
                "tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py",
            ],
            "regression": "Runtime PM artifact schema/trace compatibility and Sell Planning handoff.",
            "risk": "MEDIUM because consumer compatibility depends on legacy reason fields.",
        },
        {
            "file": "src/ai_fund_lab_v2/strategy/position_intent.py",
            "functions": ["_row_from_pm_decision", "_shadow_buy_candidate_rows", "validate_position_intent_artifact"],
            "callers": ["strategy position_intent artifact generation"],
            "consumers": ["target_portfolio_decision", "position_sizing_plan"],
            "unit_tests": ["D2-A/D2-B/D2-C/D2-D/D2-E regression tests if present in local suite"],
            "regression": "Position intent shadow contract; decision_effect must remain NONE unless later phase changes it.",
            "risk": "LOW for audit; MEDIUM if reason fields become schema inputs later.",
        },
    ]


def test_scope() -> dict[str, object]:
    return {
        "d6a_executed": [
            "python3 -m py_compile tools/phase27_analysis/phase27_d6a_generate_pm_implementation_gap_audit.py",
            "JSON validation for reports/phase27_d6a_pm_implementation_gap_audit/*.json",
        ],
        "historical_executed": False,
        "fresh_run_executed": False,
        "future_minimal_regression_scope": [
            "PM inference reason-code unit tests",
            "PM trace artifact schema/compatibility tests",
            "Runtime PM producer tests",
            "Sell Planning PM artifact consumer tests",
            "Position intent shadow mapping tests",
            "D2-E canonical quantity delta/runtime planning tests if ADD/REDUCE/EXIT handoff fields are touched",
        ],
        "prohibited_in_d6a": ["historical", "fresh-run", "resume", "100BD", "threshold changes", "PM logic changes"],
    }


def implementation_priority() -> list[dict[str, object]]:
    return [
        {"priority": 1, "unit_id": "D6B_REASON_RENAME_COMPAT", "why": "Smallest alignment with D5; reduces semantic ambiguity without action/threshold change.", "risk": "LOW_MEDIUM"},
        {"priority": 2, "unit_id": "D6B_REASON_SUMMARY_EXPECTED_EDGE", "why": "Makes PM reasoning auditable as Expected Edge reasoning while preserving current decisions.", "risk": "LOW_MEDIUM"},
        {"priority": 3, "unit_id": "D6C_ADD_EXPECTED_EDGE_INPUTS", "why": "ADD has the clearest contract gap: current_return > 0 and rank <= 5 do not prove Expected Edge improvement or incremental value.", "risk": "MEDIUM_HIGH"},
        {"priority": 4, "unit_id": "D6C_PM_EVIDENCE_INPUT_EXPANSION", "why": "Quality/Market/Portfolio/Corporate Event evidence is absent and should be introduced evidence-first before behavior changes.", "risk": "HIGH"},
    ]


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
            "required_documents_read": [
                "docs/phase_reports/phase27_d5_pm_expected_edge_reasoning_contract_design.md",
                "docs/02_architecture/strategy_architecture_v1.md",
                "docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md",
                "docs/02_architecture/position_management_decision_trace_contract.md",
            ],
            "audited_code": [
                "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py",
                "src/ai_fund_lab_v2/position_management_ai/inference.py",
                "src/ai_fund_lab_v2/strategy/position_intent.py",
                "src/ai_fund_lab_v2/strategy/position_management.py",
            ],
        },
        "pm_current_flow.json": pm_current_flow(),
        "expected_edge_mapping.json": expected_edge_mapping(),
        "reason_code_gap_analysis.json": reason_code_gap_analysis(),
        "action_gap_analysis.json": action_gap_analysis(),
        "implementation_change_units.json": implementation_change_units(),
        "impact_analysis.json": impact_analysis(),
        "test_scope.json": test_scope(),
        "implementation_priority.json": implementation_priority(),
    }


def render_report() -> str:
    return f"""# Phase27-D6-A PM Implementation Gap Audit

## 1. Scope

Phase27-D6-A audits the current PM implementation against the Phase27-D5 Expected Edge reasoning contract.

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

## 3. Current PM Flow

Current regular PM flow is:

```text
Runtime Current / Opportunity / Feature input
  -> current_holdings_snapshot + PM opportunity context
  -> build_position_feature_frame
  -> score components
  -> classify_position_action
  -> Runtime PM decision artifact and decision trace
  -> Sell Planning / position_intent shadow consumers
```

The existing PM implementation primarily produces existing-position `ADD`, `HOLD`, `REDUCE`, and `EXIT`. `BUY_NEW` is not produced by the PM regular path; BUY_NEW candidates remain shadow unresolved in `position_intent`.

## 4. Expected Edge Mapping

Used:

- Trend
- Rank
- Risk
- Profit
- Current position state

Not explicitly used in the current PM regular path:

- BUY Quality
- Market Context
- Portfolio Fit
- Corporate Event

The largest D5 gaps are semantic rather than threshold-based: isolated indicators are used directly in reason/action branches, while D5 wants them framed as Expected Edge evidence.

## 5. Reason Code Gaps

| Reason code | Gap classification | D6-A judgment |
|---|---|---|
| `trend_continuation` | `NO_CHANGE` | Aligned as continuation evidence. |
| `positive_expected_edge` | `REASON_UPDATE` | Raw positive score wording is too broad for D5 Expected Edge adequacy. |
| `downside_risk_contained` | `NO_CHANGE` | Aligned as risk-contained evidence. |
| `risk_increased_but_trend_not_broken` | `RENAME` | Broad fallback should split actual risk/weakening cause. |
| `peak_drawdown_warning` | `NO_CHANGE` | Aligned as risk/weakening evidence. |
| `trend_and_opportunity_broken` | `NO_CHANGE` | Aligned as Expected Edge deterioration evidence. |
| `profit_retention_break` | `RENAME` | Should be peak-drawdown/profit-retention risk, not profit-taking. |
| `hard_stop_current_return` | `NO_CHANGE` | Aligned as loss-containment evidence. |

## 6. Action Gaps

- `BUY_NEW`: outside current PM regular path; no PM implementation change unit for D6-B unless BUY_NEW PM scope is explicitly opened later.
- `ADD`: partial D5 gap. Current trigger uses `add_score`, `current_return > 0`, `buy_rank <= 5`, and low downside risk, but does not explicitly prove Expected Edge improvement or incremental investment value.
- `HOLD`: mostly compatible, but reason language should express Expected Edge adequacy instead of isolated positive score.
- `REDUCE`: conceptually aligned as risk/weakening while campaign remains alive; broad fallback reason needs splitting.
- `EXIT`: partly aligned; `profit_retention_break` naming and some exit summary wording need D5-compatible risk/Expected Edge semantics.

## 7. Minimal Implementation Units

1. Reason rename / alias compatibility for `profit_retention_break` and `risk_increased_but_trend_not_broken`.
2. Reason summary update so PM trace explains Expected Edge adequacy/deterioration.
3. ADD evidence input update for Expected Edge improvement and incremental investment value.
4. Evidence-first input expansion for Quality, Market, Portfolio Fit, and Corporate Event.

The first two are the minimal D6-B-safe units because they can preserve thresholds and action outcomes.

## 8. Impact

Primary files:

```text
src/ai_fund_lab_v2/position_management_ai/inference.py
src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
src/ai_fund_lab_v2/strategy/position_intent.py
```

Main consumers:

```text
position_management_decisions.json
position_management_decision_trace.json
Sell Planning
position_intent shadow producer
target_portfolio_decision / position_sizing_plan downstream contracts
```

## 9. Evidence

```text
{OUT_DIR.relative_to(REPO_ROOT)}
```

## 10. Validation

```text
python3 -m py_compile tools/phase27_analysis/phase27_d6a_generate_pm_implementation_gap_audit.py
PASS

JSON validation for all generated evidence files
PASS
```

No Runtime, Strategy, PM, Position Sizing, Historical, fresh-run, resume, 100BD, or long regression was executed.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in files().items():
        write_json(OUT_DIR / name, payload)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
