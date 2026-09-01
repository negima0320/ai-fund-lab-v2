# Phase32-CC — Existing PM HOLD / REDUCE / EXIT Boundary SHADOW Reclassification Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T234344371102Z`
- Audit mode: SHADOW / READ-ONLY
- Latest completed actual Runtime day used: `2023-05-17`
- Continuation point observed: `2023-05-18:market_refresh`
- Primary population: actual PM `HOLD` rows for profitable / mature winner positions.

No source, config, PM threshold, PM weight, model, feature, SELL/EXIT logic, BO/BQ behavior, Runtime state, Pending, Ledger, resume, recover, replay, or fresh-run action was changed or executed. This audit emits no Production decision.

Phase32-CA, Phase32-CB, and Phase32-BZ conclusions are preserved:

- Upside capture is strong.
- `profit cushion alone -> HOLD` regression was not found.
- The main late-run mechanism remains `HOLD_CONFIRMATION_LAG_AMPLIFIED_BY_CAPITAL_SCALE`.
- CB found only partial PIT separability for Winner HOLD continuation vs protection.
- BZ is a separate deferred BQ refinement track; CC does not redesign BQ.

Later outcomes were used only after same-day PIT classification to evaluate labels. They were not used to choose a Production rule.

## Evidence Sources

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/daily/<date>/position_management/pm_decisions.json`
- `.runtime/runtime_state/position_management/<date>/position_management_decisions.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/daily/<date>/current_valuation_refresh/current_valuation_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/daily/<date>/current_valuation_refresh/valuation_projection.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/daily/<date>/execution/fills.json`
- `src/ai_fund_lab_v2/position_management_ai/inference.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `src/ai_fund_lab_v2/strategy/reduce_intensity_authority.py`
- `docs/phase_reports/phase32_ca_early_vs_late_large_loss_scaling_hold_confirmation_lag_read_only_audit.md`
- `docs/phase_reports/phase32_cb_winner_hold_continuation_vs_profit_protection_pit_semantic_separability_read_only_audit.md`
- `docs/phase_reports/phase32_bz_recurrent_bq_insufficient_hold_later_loss_pit_separability_read_only_audit.md`

## CURRENT_PM_HOLD_REDUCE_EXIT_DECISION_CONTRACT

Current PM scoring is implemented by `position_management_ai.inference.build_position_management_output` and normalized by `runtime_v2.position_management.producer`.

### HOLD Authority

HOLD is selected when terminal EXIT and REDUCE branches do not take authority, or when the explicit profit-retention-only override applies:

```text
profit_retention_break + positive_expected_edge + no high downside risk + exit_score < 0.80
-> HOLD
```

HOLD reason families include:

- `trend_continuation`
- `positive_expected_edge`
- `downside_risk_contained`
- `hold_score_above_exit_threshold`

The Runtime reason semantics contract records HOLD expected edge as adequate and marks profit-retention evidence as risk review, not direct profit-taking authority.

### REDUCE Authority

REDUCE is selected when risk or weakening evidence is present, but trend or opportunity is still alive:

```text
downside_risk_score >= 0.65
or drawdown_from_peak <= -0.07
or reduce_score >= 0.62
or hold_score < 0.42

and

trend_score >= 0.35 or expected_edge_score > 0
```

REDUCE reason families include:

- `high_downside_risk_score`
- `peak_drawdown_warning`
- `risk_increased_but_trend_not_broken`
- weak hold score / expected-edge weakening

Runtime maps PM REDUCE to `SELL_PARTIAL_POSITION_REDUCE_QUANTITY_BY_SELL_PLANNING`. Quantity is not decided by PM. Reduce intensity is:

| Intensity | Contract ratio |
|---|---:|
| `LIGHT` | 0.25 |
| `MEDIUM` | 0.33 |
| `STRONG` | 0.50 |

`producer._reduce_intensity` selects `STRONG` when `reduce_score >= 0.60` or high-downside text exists, `MEDIUM` when `reduce_score >= 0.50` or `peak_drawdown_warning` exists, otherwise `LIGHT`.

### EXIT Authority

EXIT is selected for terminal risk or continuation break:

- `hard_stop_current_return`
- `profit_retention_break`, unless the positive expected-edge override applies
- `trend_and_opportunity_broken`
- bad risk guard status
- `exit_score >= 0.80`
- weak-hold branch with no live trend/opportunity

Runtime maps EXIT to full sell quantity authority.

### Boundary Finding

The existing architecture already has a conceptual `HOLD -> REDUCE -> EXIT` ladder. The under-tested boundary is not a missing action. It is the conflict state where:

```text
profit_retention_break / peak_drawdown_warning / reduce_score_threshold
coexist with
positive_expected_edge / strong_trend_continuation / downside_risk_contained
```

Current PM often resolves that conflict to HOLD.

## Population

Winner HOLD event rule:

- PM decision is `HOLD`
- and current return `>= +5%` or PIT peak return `>= +10%`

Using completed evidence through `2023-05-17`:

| Scope | Count |
|---|---:|
| Winner HOLD events evaluated | 579 |
| Winner campaigns evaluated | 74 |

Outcome labels use subsequent actual evidence only after PIT grouping:

| Label | Event count |
|---|---:|
| `MATERIAL_GIVEBACK_AFTER_HOLD` | 74 |
| `GAIN_RETAINED_OR_EXTENDED` | 29 |
| `NEUTRAL` | 471 |
| `INSUFFICIENT_OUTCOME` | 5 |

Campaign-level worst-precedence labels:

| Label | Campaign count |
|---|---:|
| `MATERIAL_GIVEBACK_AFTER_HOLD` | 32 |
| `GAIN_RETAINED_OR_EXTENDED` | 5 |
| `NEUTRAL` | 37 |

These counts differ from Phase32-CB because the target run advanced from CB's fixed `2023-05-08` snapshot to `2023-05-17`.

## SHADOW Reclassification

The audit tested an existing-semantics-only diagnostic boundary:

- `SHADOW_EXIT_WARRANTED`: terminal EXIT trigger exists, excluding profit-retention-only override.
- `SHADOW_REDUCE_WARRANTED`: existing REDUCE branch is active and the row resembles current PM REDUCE authority, especially high downside / weak hold / non-positive expected edge while continuation is not terminally broken.
- `SHADOW_AMBIGUOUS`: REDUCE/profit-retention evidence conflicts with positive expected edge or strong continuation. This is the important Winner profit-protection conflict state.
- `SHADOW_HOLD_CONTINUE`: no terminal/REDUCE conflict, or continuation evidence remains dominant under current PM semantics.

Result:

| Diagnostic label | Count |
|---|---:|
| `SHADOW_HOLD_CONTINUE` | 564 |
| `SHADOW_REDUCE_WARRANTED` | 1 |
| `SHADOW_EXIT_WARRANTED` | 0 |
| `SHADOW_AMBIGUOUS` | 14 |

This is deliberately conservative. Treating all profit-retention / reduce-score conflicts as `REDUCE_WARRANTED` would catch more later giveback, but it would also damage mandatory Winner continuation controls.

## 59350 Timeline

| Date | PM action | Shadow label | Outcome label | Current return | Drawdown from peak | Hold score | Reduce score | Exit score | Expected edge | PIT notes |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 2023-03-30 | HOLD | `SHADOW_AMBIGUOUS` | `GAIN_RETAINED_OR_EXTENDED` | +23.7% | -22.2% | 0.876 | 0.776 | 0.318 | +0.275 | `positive_expected_edge`, `profit_retention_break`, strong continuation. |
| 2023-03-31 | HOLD | `SHADOW_AMBIGUOUS` | `GAIN_RETAINED_OR_EXTENDED` | +45.9% | -33.0% | 0.800 | 0.776 | 0.318 | +0.093 | Same conflict; continuation still paid. |
| 2023-04-03 | HOLD | `SHADOW_AMBIGUOUS` | `GAIN_RETAINED_OR_EXTENDED` | +78.8% | -33.0% | 0.815 | 0.768 | 0.318 | +0.122 | Still not cleanly separable from continuation control. |
| 2023-04-04 | HOLD | `SHADOW_HOLD_CONTINUE` | `MATERIAL_GIVEBACK_AFTER_HOLD` | +111.8% | +19.1% | 0.776 | 0.510 | 0.083 | +0.010 | No peak-drawdown/profit-retention trigger in the trace. |
| 2023-04-05 | HOLD | `SHADOW_AMBIGUOUS` | `MATERIAL_GIVEBACK_AFTER_HOLD` | +92.7% | -33.0% | 0.834 | 0.773 | 0.318 | +0.161 | Strongest conflict begins, but positive expected edge and continuation remain live. |
| 2023-04-06 | HOLD | `SHADOW_AMBIGUOUS` | `MATERIAL_GIVEBACK_AFTER_HOLD` | +125.7% | -33.0% | 0.867 | 0.771 | 0.318 | +0.258 | Clearest protection candidate from CB, still not terminal EXIT under existing PM. |
| 2023-04-07 | HOLD | `SHADOW_HOLD_CONTINUE` | `MATERIAL_GIVEBACK_AFTER_HOLD` | +158.7% | +42.6% | 0.827 | 0.517 | 0.083 | +0.080 | Strong continuation trace, no profit-retention trigger. |
| 2023-04-10 | HOLD | `SHADOW_HOLD_CONTINUE` | `MATERIAL_GIVEBACK_AFTER_HOLD` | +116.1% | +6.4% | 0.754 | 0.430 | 0.068 | +0.054 | HOLD continuation remains trace-consistent. |
| 2023-04-17 | HOLD | `SHADOW_AMBIGUOUS` | `GAIN_RETAINED_OR_EXTENDED` | +73.0% | -33.0% | 0.682 | 0.692 | 0.318 | +0.040 | Profit-retention conflict returns, but not terminal. |
| 2023-04-20 | EXIT | Production EXIT | actual EXIT | +78.1% | -14.8% | 0.668 | 0.706 | 0.353 | -0.017 | PM EXIT by `profit_retention_break`; expected edge no longer positive. |

Answers for 59350:

- `59350_0330_0404_HOLD_PRESERVED`: `PARTIAL`. The tested conservative classifier preserves the period from Production action change, but 3/30, 3/31, and 4/3 remain `SHADOW_AMBIGUOUS`, not clean `HOLD_CONTINUE`.
- `59350_0405_0406_REDUCE_ZONE_SUPPORTED`: `AMBIGUOUS_PARTIAL_SUPPORT`. Existing REDUCE evidence is present, but current PM continuation evidence is also strong. The rows support a shadow conflict state more than direct REDUCE.
- `59350_EXIT_ZONE_DATE`: `2023-04-20`, when Production PM actually reaches EXIT after expected edge is no longer positive.

## Comparison With Actual PM REDUCE

Actual PM REDUCE rows through `2023-05-17`:

| Scope | Count |
|---|---:|
| Actual REDUCE events | 322 |
| Actual REDUCE campaigns | 155 |

Dominant actual REDUCE causes:

| Cause | Count |
|---|---:|
| `REDUCE_BY_WEAK_HOLD_SCORE` | 257 |
| `REDUCE_BY_PEAK_DRAWDOWN_WARNING` | 51 |
| `REDUCE_BY_RISK_INCREASED_BUT_TREND_NOT_BROKEN` | 10 |
| `REDUCE_BY_REDUCE_SCORE_THRESHOLD` | 4 |

Median profile comparison:

| Metric | Shadow REDUCE warranted | Actual PM REDUCE |
|---|---:|---:|
| Current return | +0.0% | +0.3% |
| Drawdown from peak | -50.0% | -1.5% |
| Hold score | 0.445 | 0.391 |
| Reduce score | 0.623 | 0.340 |
| Exit score | 0.620 | 0.239 |
| Expected edge | +0.211 | -0.286 |
| Downside risk | 0.700 | 0.450 |
| Market value | 8,200 | 46,750 |

The strict `SHADOW_REDUCE_WARRANTED` row is `93180` on `2023-01-12`: high downside risk, peak drawdown warning, reduce score threshold, and positive expected edge keeping trend/opportunity alive. This is semantically close to REDUCE, but it is not the 59350 profit-protection case.

The 59350 `2023-04-05` / `2023-04-06` rows are not close to ordinary actual PM REDUCE rows by expected-edge or hold-score neighborhood. They are a different conflict: strong continuation plus profit-retention risk. Existing PM concepts expose it, but current REDUCE authority does not cleanly own it.

Therefore:

```text
PROPOSED_REDUCE_CASES_MATCH_EXISTING_PM_REDUCE_NEIGHBORHOOD = WEAK_PARTIAL
```

## Winner False-Reduction Controls

Mandatory controls:

| Symbol | Events | Shadow summary | Outcome summary |
|---:|---:|---|---|
| 44440 | 2 | 1 `HOLD_CONTINUE`, 1 `AMBIGUOUS` | 2 gain-retained |
| 78860 | 11 | 11 `HOLD_CONTINUE` | 7 gain-retained, 3 neutral, 1 material giveback |
| 99840 | 24 | 24 `HOLD_CONTINUE` | 8 gain-retained, 16 neutral |
| 69730 | 18 | 18 `HOLD_CONTINUE` | 18 neutral |
| 92270 | 5 | 5 `HOLD_CONTINUE` | 4 neutral, 1 material giveback |
| 64240 | 2 | 2 `HOLD_CONTINUE` | 2 gain-retained |
| 51360 | 7 | 7 `HOLD_CONTINUE` | 6 neutral, 1 material giveback |

Strict false-reduce risk:

```text
LOW
```

Broad conflict-as-REDUCE false-reduce risk:

```text
HIGH
```

The difference matters. A narrow existing-REDUCE-neighborhood classifier preserves valid Winner continuation but barely captures harmful HOLD lag. A broad classifier would catch more 59350-like conflict, but it would incorrectly pressure valid continuation controls such as 59350 3/30-4/3 and 44440 3/20.

## Harmful HOLD-Lag Capture

Under the conservative existing-semantics classifier:

| Metric | Count |
|---|---:|
| Harmful HOLD-lag events | 74 |
| Harmful HOLD-lag campaigns | 32 |
| Harmful events classified `SHADOW_REDUCE_WARRANTED` before material giveback | 0 |
| Harmful events missed by `SHADOW_REDUCE_WARRANTED` | 74 |
| Median pre-loss REDUCE lead time | `N/A` |

`SHADOW_AMBIGUOUS` captures the important 59350 conflict rows, including 2023-04-05 and 2023-04-06, but the evidence is not strong enough to label them as REDUCE without introducing additional semantics or a new threshold.

This supports a missing shadow diagnostic state more than a directly promotable REDUCE decision.

## Expected REDUCE Quantity Intent

For the single strict `SHADOW_REDUCE_WARRANTED` row:

| Symbol | Date | Quantity | Reduce intensity | Raw reduce quantity | Executable reduce quantity | Trading unit assumption |
|---:|---|---:|---|---:|---:|---:|
| 93180 | 2023-01-12 | 4,100 | `STRONG` | 2,050 | 2,000 | 100 |

For 59350 4/5 and 4/6, if they were hypothetically treated as REDUCE, current PM intensity semantics would be `STRONG`, raw reduce quantity would be 50 shares, and executable reduce quantity would be 0 shares under 100-share lot resolution. That diagnostic case would require the existing BQ reconsideration architecture. CC does not solve it.

Summary:

| Scope | Count |
|---|---:|
| Expected REDUCE executable candidates | 1 |
| Expected REDUCE unexecutable candidates | 0 |
| Would require existing BQ reconsideration | 0 under strict REDUCE; 2 for hypothetical 59350 4/5 and 4/6 conflict-as-REDUCE |

## BQ Separation

No BQ logic is changed or redesigned here.

If a future PM SHADOW evaluation decides that 59350-like conflict belongs to REDUCE, one-lot positions would often produce raw partial REDUCE quantities below the 100-share unit. Those cases should flow into the existing BQ reconsideration architecture:

```text
PM HOLD/REDUCE/EXIT
-> if REDUCE executable: execute REDUCE
-> if REDUCE unexecutable: existing BQ reconsideration path
```

No second binary reconsideration mechanism is justified.

## Decision

Missing or underused REDUCE zone support:

```text
WEAK_SUPPORT
```

HOLD to REDUCE PIT separability:

```text
WEAKLY_SEPARABLE
```

Rationale:

- Existing PM traces expose the conflict state.
- Existing REDUCE triggers are active in 59350 4/5 and 4/6.
- But the same rows also carry strong HOLD/ADD-like continuation evidence.
- Actual PM REDUCE rows are usually weak-hold / negative-edge / peak-warning management rows, not high-conviction winners with positive expected edge.
- Current evidence does not justify direct Production REDUCE without new semantic materialization.

Recommended next step:

```text
Narrow SHADOW implementation inside existing PM architecture that materializes HOLD_CONTINUE / REDUCE_WARRANTED / EXIT_WARRANTED / AMBIGUOUS diagnostics from existing PM trace fields only.
```

This should not create a new module, subsystem, decision engine, parallel sell path, or Production action. It should first make the ambiguous Winner profit-protection conflict observable and test false-reduction controls.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED = 2023-05-17`
2. `CURRENT_PM_HOLD_REDUCE_EXIT_DECISION_CONTRACT = Existing PM has HOLD, REDUCE, EXIT. HOLD is continuation/expected-edge/risk-contained or profit-retention-only override; REDUCE is risk/weakening with trend/opportunity alive; EXIT is terminal risk or continuation break. PM emits REDUCE intensity only, while Sell Planning owns executable quantity.`
3. `WINNER_HOLD_EVENTS_EVALUATED = 579`
4. `SHADOW_HOLD_CONTINUE_COUNT = 564`
5. `SHADOW_REDUCE_WARRANTED_COUNT = 1`
6. `SHADOW_EXIT_WARRANTED_COUNT = 0`
7. `SHADOW_AMBIGUOUS_COUNT = 14`
8. `59350_0330_0404_HOLD_PRESERVED = PARTIAL; no Production change supported, but 3/30, 3/31, 4/3 remain shadow ambiguous`
9. `59350_0405_0406_REDUCE_ZONE_SUPPORTED = AMBIGUOUS_PARTIAL_SUPPORT; existing REDUCE triggers fire, but strong continuation remains`
10. `59350_EXIT_ZONE_DATE = 2023-04-20`
11. `PROPOSED_REDUCE_CASES_MATCH_EXISTING_PM_REDUCE_NEIGHBORHOOD = WEAK_PARTIAL`
12. `FALSE_REDUCE_RISK = LOW for strict REDUCE-neighborhood; HIGH if ambiguous winner conflict is promoted directly`
13. `VALID_WINNER_CONTROLS_PRESERVED = YES under strict classifier; NOT GUARANTEED under broad conflict-as-REDUCE`
14. `HARMFUL_HOLD_LAG_CAPTURE_COUNT = 0 strict REDUCE_WARRANTED events; 59350 conflict captured as AMBIGUOUS`
15. `HARMFUL_HOLD_LAG_MISS_COUNT = 74 strict REDUCE_WARRANTED event misses`
16. `MEDIAN_PRELOSS_REDUCE_LEAD_TIME = N/A under strict REDUCE_WARRANTED`
17. `EXPECTED_REDUCE_EXECUTABLE_COUNT = 1`
18. `EXPECTED_REDUCE_UNEXECUTABLE_COUNT = 0 strict; 2 if 59350 4/5 and 4/6 were hypothetically mapped to REDUCE`
19. `WOULD_REQUIRE_EXISTING_BQ_RECONSIDERATION_COUNT = 0 strict; 2 hypothetical 59350 conflict-as-REDUCE cases`
20. `NEW_COMPONENT_CREATED = NO`
21. `NEW_MODULE_CREATED = NO`
22. `NEW_PRODUCTION_ACTION_CREATED = NO`
23. `NEW_MODEL_REQUIRED = NO_CONCRETE_EVIDENCE`
24. `NEW_THRESHOLD_JUSTIFIED = NO_FOR_PRODUCTION`
25. `MISSING_OR_UNDERUSED_REDUCE_ZONE_SUPPORT = WEAK_SUPPORT`
26. `HOLD_TO_REDUCE_PIT_SEPARABILITY = WEAKLY_SEPARABLE`
27. `PRODUCTION_CHANGE_JUSTIFIED = NO`
28. `NEXT_RECOMMENDED_STEP = Implement a narrow SHADOW-only diagnostic materialization inside existing PM trace/producer boundaries, preserving HOLD/REDUCE/EXIT Production actions and explicitly tracking AMBIGUOUS winner profit-protection conflict before any REDUCE mapping.`
29. `FINAL_JUDGMENT = PHASE32_CC_EXISTING_PM_BOUNDARY_WEAKLY_SEPARABLE_SHADOW_DIAGNOSTIC_JUSTIFIED_PRODUCTION_REDUCE_NOT_JUSTIFIED`

## Final Judgment

```text
PHASE32_CC_EXISTING_PM_BOUNDARY_WEAKLY_SEPARABLE_SHADOW_DIAGNOSTIC_JUSTIFIED_PRODUCTION_REDUCE_NOT_JUSTIFIED
```
