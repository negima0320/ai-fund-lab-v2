# Phase27-D2-F Existing PM HOLD / REDUCE / EXIT Decision Causality and Momentum-follow Conformance Audit

## 1. Scope

This is a read-only audit of existing PM HOLD / REDUCE / EXIT decisions in the run-scoped baseline evidence.

```text
Run: runtime-test-historical-smoke-20260804T074611098414Z
Implementation Change: false
PM / Strategy / Runtime Change: false
Historical rerun / fresh-run / resume: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
PHASE27_D2F_PM_MOMENTUM_FOLLOW_PARTIAL_CONFORMANCE_IMPROVEMENT_TARGET_IDENTIFIED
```

Supporting:

```json
{
  "hold_causality": "PARTIAL",
  "reduce_causality": "PARTIAL",
  "exit_causality": "PARTIAL",
  "profit_taking_only_exit": "OBSERVED",
  "short_reentry": "PARTIAL",
  "decision_boundary_stability": "PARTIAL",
  "momentum_follow_conformance": "PARTIAL",
  "new_momentum_component": "PM_INPUT_IMPROVEMENT_CANDIDATE",
  "next_entry": "PERFORMANCE_DESIGN_REVIEW"
}
```

## 3. Key Counts

```json
{
  "hold_count_by_causality_class": {
    "MOMENTUM_CONTINUATION_SUPPORTED": 74,
    "POSITION_VALID_BUT_MOMENTUM_EVIDENCE_PARTIAL": 61,
    "RISK_ACCEPTABLE_MAINTAIN": 25,
    "NO_EXIT_CONDITION": 2
  },
  "reduce_count_by_causality_class": {
    "RISK_REDUCTION": 19,
    "MOMENTUM_WEAKENING": 15
  },
  "exit_count_by_causality_class": {
    "MOMENTUM_BROKEN": 7,
    "RISK_OR_SAFETY_EXIT": 16
  },
  "hold_to_exit_count": 8,
  "exit_to_1bd_buy_new_count": 5,
  "exit_to_2bd_buy_new_count": 1,
  "exit_to_3_5bd_buy_new_count": 3,
  "possible_whipsaw_count": 3,
  "unstable_boundary_count": 3,
  "profit_taking_only_count": 3,
  "unexplained_exit_count": 0,
  "insufficient_evidence_count": 0
}
```

## 4. Findings

1. PM HOLD is partly active, not purely implicit: HOLD rows carry PM reason codes, mainly `positive_expected_edge`, `downside_risk_contained`, and sometimes `trend_continuation`.
2. HOLD causality is only partial because many HOLD rows lack a dedicated materialized Momentum Continuation state; reason codes support continuation/validity but not a full persistence model.
3. REDUCE is mostly explained by drawdown/risk weakening evidence, especially `peak_drawdown_warning` and `risk_increased_but_trend_not_broken`.
4. EXIT is partly explained by `hard_stop_current_return`, `trend_and_opportunity_broken`, and `profit_retention_break`; however `profit_retention_break` alone leaves ambiguity around profit retention versus momentum failure.
5. Profit existing at EXIT is separated from profit causing EXIT. Profit-only evidence is counted only when PM reason evidence is exclusively profit-linked.
6. Short EXIT -> BUY_NEW re-entry exists and is only partially explained by materialized input changes. Some cases remain possible whipsaw / unstable boundary candidates.
7. Current PM behaves as partially conformant Momentum Follow: it can hold, reduce, and exit with directional evidence, but continuation evidence is not explicit enough to fully confirm stable HOLD / EXIT boundaries.
8. The first Performance Design review candidate should be PM input/reasoning contract improvement for explicit Momentum Continuation / boundary stability evidence. This is not a recommendation to add a separate Action Authority.

## 5. Evidence Limitations

- Run-scoped PM snapshot is the direct PM decision evidence; Strategy `position_management.v1` rows remain adapter `UNRESOLVED` in this baseline.
- Dedicated `momentum_continuation_state` is not materialized in the inspected artifacts.
- Counterfactual HOLD instead of EXIT is not observable.
- PnL was not treated as PM input causality; it is used only to distinguish profit-present from profit-referenced evidence.

## 6. Evidence Files

```text
reports/phase27_d2f_existing_pm_hold_reduce_exit_decision_causality_and_momentum_follow_conformance_audit
```

## 7. Validation

```text
python3 -m py_compile tools/phase27_analysis/phase27_d2f_generate_pm_causality_audit.py
PASS

python3 -m json.tool reports/phase27_d2f_existing_pm_hold_reduce_exit_decision_causality_and_momentum_follow_conformance_audit/summary.json
PASS
```

