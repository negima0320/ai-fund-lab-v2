# Phase27 Final Summary and Phase28 Handoff

## Final Judgment

```text
PHASE27_CLOSED_WITH_FIRST_PERFORMANCE_EXPERIMENT_ADOPTED_PHASE28_READY
```

Phase27 final status:

```text
CLOSED_WITH_ADOPTED_PERFORMANCE_IMPROVEMENT_AND_KNOWN_COMPARABILITY_LIMITATIONS
```

Supporting:

```json
{
  "architecture_repair": "COMPLETE",
  "decision_authority": "CANONICALIZED",
  "legacy_add_authority": "RETIRED_FROM_EXECUTION",
  "pm_philosophy": "FROZEN",
  "expected_edge_contract": "FROZEN",
  "pm_action_boundary": "FROZEN",
  "first_hold_exit_experiment": "ADOPTED_WITH_LIMITATIONS",
  "100bd": "COMPLETED",
  "risk_regression": "NOT_OBSERVED",
  "phase28_entry": "APPROVED"
}
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
