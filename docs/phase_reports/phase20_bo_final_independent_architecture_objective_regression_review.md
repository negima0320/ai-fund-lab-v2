# Phase20-BO Final Independent Architecture / Objective / Regression Review

## Executive Summary

Final status:

```text
PHASE20_BO_FINAL_INDEPENDENT_REVIEW_COMPLETE
```

Closure judgment:

```text
PHASE20_CLOSURE_APPROVED_WITH_PHASE21_ENTRY_CONDITIONS
```

This is an independent review of Phase20. It is not a formal approval of performance quality and it does not implement changes.

Primary finding:

```text
Phase20 succeeded at making Performance observable, attributable, and replayable enough for Phase21.
Phase20 did not prove actual strategy performance improvement.
```

Phase20 should close with explicit Phase21 entry conditions. The Runtime / Historical / Observability foundation is substantially stronger than at Phase20 start, but the system is not yet close to the formal return and operation-rate objectives. PM redesign is not yet supported as a direct implementation decision; PM rule review is supported as a Phase21 investigation item.

## Phase20 Original Objective

The applicable requirement and handoff materials define the AI Fund Lab v2 objective as safe, reproducible, cash-equity-only automated operation on Japanese equities using J-Quants-derived data and Tachibana Securities e-branch API authority.

Confirmed from Phase19 handoff materials:

| Requirement | Confirmed value |
|---|---|
| Market | Japanese equities |
| Initial capital | JPY 1,000,000 |
| Instrument | Cash equities only |
| Broker | Tachibana Securities e-branch API |
| Target return | Annual +50% |
| Target operation rate | 80% |
| Runtime mode contract | Production / Demo / Historical common Runtime contract |
| Safety posture | fail-closed |

Runtime Architecture v2 further states that Runtime is not the AI investment logic and does not directly achieve annual +50%. Runtime must avoid hidden fixed constraints that block explicitly designed Capital Allocation / Risk Policy deployment.

## Phase20 Actual Scope

Phase20 expanded from Performance baseline extraction into a long stabilization and attribution campaign.

| Area | Actual Phase20 work |
|---|---|
| Performance contract | Metric / benchmark / experiment comparison contract created |
| Baseline authority | 20BD baseline extracted and fixed as performance baseline |
| Attribution | Trade lifecycle, PM decision trace, diagnosis, improvement candidate reports |
| Runtime Test CLI | `run-status`, `summarize --scope`, run-scoped past-run authority |
| Observability | fills, realized slices, position campaigns, PM snapshots, benchmark missing snapshots |
| PM authority | decision trace contract, PM Runtime Adapter acceptance refresh, false-PASS closure |
| Historical data | 5y J-Quants acquisition, feature lookback, corporate action guard, trading calendar, market evidence source |
| Cross-regime analysis | Bull / Bear / Range selection, PM analysis, final attribution audit |

This was broader than pure performance improvement. It was necessary because the system could not safely identify what to improve until evidence authority and replay correctness were repaired.

## Objective Alignment Review

| Objective | Review | Judgment |
|---|---|---|
| Japanese equity autonomous operation | Historical replay now uses J-Quants-derived logical as-of input; Production/Demo source authority remains operations canonical. | PASS |
| Initial capital JPY 1,000,000 | Baseline and cross-regime runs use JPY 1,000,000. | PASS |
| Cash equity only | No evidence of derivative/margin/broker path expansion. | PASS |
| Common Runtime contract | Historical-specific source selection was added behind `mode == "historical"` and documented. | PASS_WITH_SCOPE_LIMIT |
| fail-closed | PM hash mismatch, corporate action guard, feature lookback, and market evidence source failures fail closed. | PASS |
| Performance improvement | Evaluation and attribution improved; actual returns did not prove improvement. | NOT_PROVEN |
| Annual +50% target | Baseline -4.49%, Bull -4.512%, Bear +8.828%, Range 0%. No annualized target evidence supports +50%. | NOT_MET |
| Operation rate 80% | Range had BUY 0 / PM 0 across 20BD. Bull/Bear executed only 5 BUY each. | NOT_PROVEN |
| Avoid lost opportunities | Range no-trade and Bull/Bear low-BUY indicate opportunity loss candidates. | REVIEW_REQUIRED |

## Architecture SoT Compliance

Phase20 generally respected Architecture SoT principles:

- Accepted Generation / Artifact Registry authority was preserved and refreshed formally in Phase20-W.
- PM hash mismatch was not bypassed; false PASS was fixed in Phase20-U.
- Runtime Test past-run summary no longer treats current `.runtime` as authoritative when hashes mismatch and run-scoped evidence exists.
- Historical consumers were aligned to logical as-of inputs instead of unbounded physical sources.
- Post-hoc attribution was kept out of decision-time PM input.
- Benchmark data remained `MISSING` where no local authority was confirmed.

Architecture risks remain:

- Historical mode currently has `supports_9000_series_orders=False`, matching Demo capability rather than Production capability. This is visible in `runtime_v2/broker_adapter/capability.py` and Range no-trade reasons. It may be intentional simulation conservatism, but it is not yet clearly separated as Broker capability vs Historical evaluation universe policy.
- Runtime Architecture v2 says Runtime must not reintroduce hidden fixed `max_positions=5` behavior. Cross-regime evidence shows Bull/Bear executed only 5 initial BUY despite later opportunities. The fixed basket / redeployment boundary must be reviewed against Capital Deployment Contract.

## Implementation vs Design Review

| Component | Evidence | Judgment |
|---|---|---|
| `scripts/runtime_test.py` summarize | Scope contract, run-scoped evidence, final-state snapshot priority, no shared runtime event authority. | PASS |
| Performance observability | Position campaigns, fills, realized slices, PM snapshots, benchmark missing snapshots are additive. | PASS_WITH_GAPS |
| PM Runtime Adapter | Phase20-W accepted current `producer.py` hash formally after equivalence review. | PASS |
| PM false-PASS closure | PM HALT metadata is preserved and blocks run/validate/close PASS. | PASS |
| Historical feature lookback | Resolver requires 61 business-day lookback and selects acquisition staging only for historical. | PASS |
| Historical market evidence | Market Evidence consumes the same historical logical as-of authority. | PASS |
| Corporate action guard | Fails closed for affected historical review instead of silently continuing. | PASS |
| BUY planning capability filter | Capability filter is implemented before price/eligibility checks. Historical 9000-series policy needs contract clarification. | REVIEW_REQUIRED |

## Production / Demo / Historical Regression Review

No confirmed Production or Demo regression was found in reviewed Phase20 evidence.

Production/Demo remained on operations canonical normalized OHLCV for Market Evidence. Historical mode alone can select acquisition staging through the as-of resolver when operations canonical lacks feature lookback. This preserves Production/Demo authority separation.

Historical Replay improved materially:

- Feature lookback insufficiency now fails closed before Candidate / Opportunity / PM consume incomplete features.
- Logical as-of materialization excludes future rows after the replay business date.
- Market Evidence source lineage records source role, logical cutoff, manifest path/hash, and future-row exclusion.
- Corporate action review can halt instead of producing a misleading pass.

Residual Historical risk:

```text
HISTORICAL_9000_SERIES_CAPABILITY_POLICY_NEEDS_FORMAL_CLARIFICATION
```

## CLI Regression Review

Phase20-H and BM substantially improved CLI responsibilities:

| CLI behavior | Review | Judgment |
|---|---|---|
| `run-status` | Canonical runner-state command added. | PASS |
| `status` | Compatibility alias retained. | PASS |
| `summarize --scope` | overview / performance / positions / lifecycle / full implemented. | PASS |
| Past-run authority | Current root hash mismatch is non-blocking when run-scoped evidence exists. | PASS |
| Baseline old-run gap | Old 20BD baseline lacks later run-scoped observability and still reports REVIEW_REQUIRED in direct summarize, while Phase20-C baseline artifact remains the formal performance source. | KNOWN_GAP |

## Evidence and Observability Review

Phase20 turned performance from a largely final-equity-only result into an evidence-backed attribution set.

Available or improved:

- Daily run-scoped fills.
- Daily realized slices for Phase20-J+ runs.
- Position campaign identity and lifecycle snapshots.
- PM decision snapshots and trace fields.
- Dominant PM causes and reason codes for later analysis.
- Historical market evidence lineage.
- Missing benchmark snapshots instead of implicit benchmark inference.

Remaining gaps:

- Candidate score bodies and full BUY reason bodies are not consistently retained run-scoped.
- Stable lot IDs are not available.
- Fees, tax, and slippage are not available.
- TOPIX / benchmark source is not confirmed.
- Sector attribution is missing.
- Baseline run predates later observability and therefore has derivable gaps.

## Performance Goal Progress Review

Run-scoped authority confirmed:

| Run | Regime | Final equity | Return | BUY | SELL | Runtime judgment | Performance authority |
|---|---|---:|---:|---:|---:|---|---|
| `runtime-test-historical-smoke-20260721T213848054826Z` | 20BD Baseline | 955,100 | -4.49% | 5 | 7 | PASS in original baseline / REVIEW_REQUIRED in direct modern summarize due old evidence gaps | Phase20-C baseline artifact |
| `runtime-test-historical-extended-smoke-20260723T215847198556Z` | Bull | 954,880 | -4.512% | 5 | 10 | PASS | Run-scoped position campaigns |
| `runtime-test-historical-extended-smoke-20260723T225746889854Z` | Bear | 1,088,280 | +8.828% | 5 | 11 | PASS | Run-scoped position campaigns |
| `runtime-test-historical-extended-smoke-20260724T030527368584Z` | Range | 1,000,000 | 0.000% | 0 | 0 | PASS | Current final hash match / no-trade evidence |

Performance conclusion:

```text
PERFORMANCE_EVALUABILITY_IMPROVED
ACTUAL_PERFORMANCE_IMPROVEMENT_NOT_PROVEN
ANNUAL_50_PERCENT_TARGET_NOT_PROVEN
80_PERCENT_OPERATION_RATE_NOT_PROVEN
```

## PM Redesign Decision Review

Phase20-R found:

```text
PM_EXIT_RULE_REVIEW_REQUIRED
PM_REDUCE_RULE_REVIEW_REQUIRED
PM_HOLD_RULE_ACCEPTABLE
PM_OBSERVABILITY_IMPROVEMENT_REQUIRED
THRESHOLD_CHANGE_NOT_READY
```

Phase20-S/W closed authority and trace gaps without changing PM behavior. Phase20-BN showed Bull/Bear outcomes are shaped by PM EXIT / REDUCE / HOLD after initial entry, but also showed entry selection, regime timing, and capital redeployment effects.

BO judgment:

```text
PM_REDESIGN_DECISION_NOT_YET_SUPPORTED
PM_RULE_REVIEW_PHASE21_ENTRY_CONDITION
```

Reason:

- PM review is justified by EXIT/REDUCE post-decision outcomes.
- Full PM redesign is not justified from three 20BD campaigns and one detailed PM trace campaign.
- Threshold changes remain prohibited until more cross-regime evidence and missing observability are closed.

## Range No-Trade Responsibility Review

Range result:

```text
BUY = 0
SELL = 0
PM Decision = 0
Return = 0%
```

Phase20-BN funnel:

| Stage | 20BD total |
|---|---:|
| Candidate AI rows | 1000 |
| Opportunity rows | 1000 |
| Selected rank count | 47 |
| Planning candidates | 47 |
| Listed BUY eligible | 0 |
| Opportunity BUY eligible | 0 |
| BUY selected | 0 |
| BUY executed | 0 |

Responsibility judgment:

```text
RANGE_NO_TRADE_NOT_PM_RESPONSIBILITY
RANGE_NO_TRADE_BUY_PLANNING_ELIGIBILITY_PRICE_CAPABILITY_RESPONSIBILITY
```

The no-trade point is after Candidate / Opportunity row production and before BUY selection / execution. Evidence reasons include:

- `NO_SIGNAL:no_affordable_candidates_with_reliable_price`
- `NO_SIGNAL:demo_capability_filtered_all_9000_series`

The 9000-series piece is a contract risk because Historical mode currently uses `supports_9000_series_orders=False`. Phase21 should decide whether Historical replay should mimic Demo broker capability, Production capability, or a separate simulation universe policy.

## Bull/Bear Low-BUY Review

Bull and Bear both produced 1000 Candidate rows and 1000 Opportunity rows. They still executed only 5 BUY each.

| Regime | Candidate AI rows | Opportunity rows | Planning candidates | Opportunity BUY eligible | BUY selected | BUY executed |
|---|---:|---:|---:|---:|---:|---:|
| Bull | 1000 | 1000 | 258 | 108 | 77 | 5 |
| Bear | 1000 | 1000 | 305 | 78 | 70 | 5 |
| Range | 1000 | 1000 | 47 | 0 | 0 | 0 |

Judgment:

```text
BULL_BEAR_LOW_BUY_NOT_CANDIDATE_ROW_SHORTAGE
BULL_BEAR_LOW_BUY_CAPITAL_REDEPLOYMENT_OR_MAX_POSITION_POLICY_REVIEW_REQUIRED
```

This is not a Runtime failure by itself, but it conflicts with the higher-level objective of not losing trading opportunities unless the active Capital Deployment / Risk Policy explicitly intends that behavior.

## Safety and Data Leakage Review

No future leakage was confirmed in reviewed Phase20 evidence:

- Historical logical inputs materialize rows with `Date <= business_date`.
- Market Evidence records logical cutoff and future-row exclusion.
- PM post-decision outcomes are marked as post-hoc analysis and not written to PM decision-time snapshots.
- Benchmark values remain missing instead of fetched externally or inferred.

Safety remains fail-closed:

- PM authority mismatch halted.
- Feature lookback insufficiency halted.
- Market Evidence source mismatch produced REVIEW_REQUIRED until fixed.
- Corporate action affected range halted / required continuation contract.

## Test Coverage Review

Executed Phase20 validations were targeted and short, consistent with constraints:

- Unit / regression pytest around Runtime Test summarize, observability, PM false-PASS, PM adapter equivalence, Historical as-of, Market Evidence, bootstrap, trading calendar, and corporate action guard.
- `py_compile` for touched Python files in implementation phases.
- JSON validation for reports and schemas.
- `git diff --check`.

Not executed in BO:

```text
Bull rerun
Bear rerun
Range rerun
20BD fresh run
1y / 3y historical
Broker connection
Training
Calibration
Accepted Generation change
```

Coverage gaps:

- No long-run replay proof after all late Phase20 fixes.
- No production broker live validation in Phase20-BO.
- No benchmark source validation.
- No operation-rate target test.

## Residual Gaps

| Gap | Impact | Phase21 entry condition |
|---|---|---|
| Historical 9000-series capability policy unclear | Range no-trade may be partly simulation-policy-induced | Clarify Historical capability / universe contract |
| Capital redeployment / max-position behavior | Bull/Bear low BUY count may suppress opportunity capture | Review Capital Deployment Contract and evidence |
| Candidate score / BUY reason body retention incomplete | Candidate responsibility attribution remains partial | Add run-scoped decision body evidence |
| Benchmark / sector missing | Excess return and regime-relative analysis incomplete | Approve and implement benchmark/sector authority |
| Fees/tax/slippage missing | Net PnL differs from gross attribution | Add explicit cost model or source |
| PM threshold readiness not met | EXIT/REDUCE review cannot safely become parameter change | Extend cross-regime PM evidence before threshold proposals |
| Baseline old-run observability gap | Old baseline direct summarize remains REVIEW_REQUIRED | Keep Phase20-C artifact as baseline authority or rerun baseline under new observability |

## Phase21 Entry Conditions

Phase21 may start if it treats Phase20 as an evidence-foundation phase, not as proof of profitable strategy.

Required entry conditions:

1. Do not claim annual +50% or 80% operation-rate readiness from Phase20 evidence.
2. Decide Historical 9000-series capability / universe policy before interpreting Range no-trade as pure model behavior.
3. Review Capital Deployment / max-position / redeployment against Runtime Architecture v2.
4. Keep PM threshold changes prohibited until more evidence supports them.
5. Add missing Candidate / Opportunity / BUY reason body retention before assigning final AI responsibility.
6. Keep Benchmark / Sector missing status explicit until authority is approved.
7. Run future longer campaigns only after the above contracts are clear.

## Summary Tables

### A. 設計準拠

| Area | Judgment |
|---|---|
| Architecture SoT authority | PASS_WITH_RESIDUAL_GAPS |
| Accepted Generation / Registry | PASS |
| Runtime / AI responsibility separation | PASS |
| Historical logical as-of | PASS |
| Post-hoc separation | PASS |
| Historical 9000 capability policy | REVIEW_REQUIRED |

### B. デグレ

| Area | Judgment |
|---|---|
| Production | NO_CONFIRMED_REGRESSION |
| Demo | NO_CONFIRMED_REGRESSION |
| Historical | IMPROVED_WITH_POLICY_GAP |
| Runtime Test CLI | IMPROVED |
| PM authority | IMPROVED |

### C. 目標接近

| Goal | Judgment |
|---|---|
| Performance evaluability | IMPROVED |
| Actual performance | NOT_PROVEN |
| Annual +50% | NOT_PROVEN |
| Operation rate 80% | NOT_PROVEN |
| Opportunity capture | REVIEW_REQUIRED |

### D. Performance

| Regime | Return | Interpretation |
|---|---:|---|
| Baseline | -4.49% | Negative baseline fixed |
| Bull | -4.512% | Loss; concentrated initial-basket losses |
| Bear | +8.828% | Profit; concentrated in 60850 / 67400 |
| Range | 0.000% | No-trade; BUY Planning bottleneck |

### E. PM

| PM item | Judgment |
|---|---|
| EXIT rule | REVIEW_REQUIRED |
| REDUCE rule | REVIEW_REQUIRED |
| HOLD rule | ACCEPTABLE_FOR_NOW |
| PM observability | IMPROVED |
| PM redesign | NOT_YET_SUPPORTED |
| Threshold change | NOT_READY |

### F. Closure

| Closure item | Judgment |
|---|---|
| Phase20 independent review | COMPLETE |
| Phase20 closure | APPROVED_WITH_PHASE21_ENTRY_CONDITIONS |
| Blocking implementation regression | NOT_FOUND |
| Performance target met | NO |
| Long-running tests in BO | NOT_EXECUTED |

## BO Acceptance Review

| Requirement | Judgment |
|---|---|
| BO-R1 Phase20 purpose alignment | PASS_WITH_NOT_PROVEN_PERFORMANCE |
| BO-R2 Architecture SoT compliance | PASS_WITH_RESIDUAL_GAPS |
| BO-R3 Implementation vs design | PASS_WITH_REVIEW_ITEMS |
| BO-R4 Production regression review | NO_CONFIRMED_REGRESSION |
| BO-R5 Demo regression review | NO_CONFIRMED_REGRESSION |
| BO-R6 Historical replay review | PASS_WITH_POLICY_GAP |
| BO-R7 CLI regression review | PASS |
| BO-R8 Evidence / observability review | PASS_WITH_GAPS |
| BO-R9 Performance goal progress | EVALUABILITY_ONLY |
| BO-R10 PM redesign decision | NOT_YET_SUPPORTED |
| BO-R11 Range no-trade responsibility | BUY_PLANNING_ELIGIBILITY_PRICE_CAPABILITY |
| BO-R12 Bull/Bear low-BUY | CAPITAL_REDEPLOYMENT_OR_MAX_POSITION_REVIEW_REQUIRED |
| BO-R13 Safety / leakage | PASS |
| BO-R14 Closure | APPROVED_WITH_PHASE21_ENTRY_CONDITIONS |

## Final Judgment

```text
PHASE20_BO_FINAL_INDEPENDENT_REVIEW_COMPLETE
PHASE20_CLOSURE_APPROVED_WITH_PHASE21_ENTRY_CONDITIONS
PM_REDESIGN_DECISION_NOT_YET_SUPPORTED
PERFORMANCE_EVALUABILITY_IMPROVED
ACTUAL_PERFORMANCE_IMPROVEMENT_NOT_PROVEN
PHASE21_ENTRY_CONDITIONS_REQUIRED
```
