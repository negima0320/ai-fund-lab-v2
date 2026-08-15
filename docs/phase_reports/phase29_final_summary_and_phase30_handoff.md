# Phase29 Final Summary and Phase30 Handoff

## Primary Judgment

`PHASE29_CLOSED_PHASE30_CLEAN_PERFORMANCE_IMPROVEMENT_HANDOFF_READY`

Phase29 is closed as a performance-improvement and runtime-authority repair
phase. Phase30 migration is user-approved, but Phase30 tuning must begin from
clean measurement and clean attribution, not from contaminated historical
performance evidence.

Task ID for this retrospective:

`Phase29-L21T-BN`

Mode:

`READ-ONLY DOCUMENTATION / RETROSPECTIVE / HANDOFF`

No Strategy, Runtime, Config, Model, Threshold, runtime state, Pending, Ledger,
Current, fresh-run, resume, replay, recovery, or Historical execution was
changed or run by Codex for this task.

## Canonical Reading Order

1. `docs/phase_reports/phase29_to_phase30_chatgpt_handoff.md`
2. `docs/phase_reports/phase29_final_summary_and_phase30_handoff.md`
3. `docs/phase_reports/phase30_a_phase29_final_state_clean_baseline_reset_and_research_roadmap.md`
4. `docs/phase_reports/phase30_a_entry_gate_100bd_baseline_status.md`
5. `docs/01_requirements/phase_roadmap.md`

The latest `Phase29-L21T-BM` section in the Phase30 entry material is the
current authority. Older AO-era sections in that file are retained only as
historical record.

## Phase29 Starting Point

The canonical Phase28 closure equivalent is:

`docs/phase_reports/phase28_d71_final_closure_phase29_handoff.md`

The requested files `phase28_final_summary_and_phase29_handoff.md` and
`phase28_to_phase29_chatgpt_handoff.md` were not present under
`docs/phase_reports/`; `phase28_d71_final_closure_phase29_handoff.md` is the
repository-local canonical equivalent.

Phase29 inherited this problem:

```text
Move from "winning positions are held correctly" to
"additional capital is allocated correctly to winning positions only when
incremental portfolio Expected Value improves."
```

Phase28 had repaired much of the ADD architecture, but its post-D61 100BD run
was incomplete at closure. Phase29 was expected to continue the performance
evidence work, focusing on:

- PM ADD to Runtime BUY_ADD conversion.
- Incremental Investment semantics.
- Capital deployment and cash underuse.
- Dynamic position count and concentration.
- Re-entry churn and low-price risk.
- Winner retention, EXIT quality, and deployed-capital quality.
- Long-horizon validation readiness.

The project goal remained a production-common, cash-equity, momentum-oriented
swing strategy starting from `1,000,000` JPY and ultimately targeting high
annualized returns. Phase29 was never authorized to use Historical-only Strategy
logic, fixed BUY counts, forced exposure, future data, or Paper Ledger outcomes
as learning input.

## What Phase29 Actually Did

Phase29 began as a Strategy performance phase, but it became a combined
performance, runtime-authority, and measurement-integrity phase. That was the
right outcome: several apparent Strategy problems were real, but the later
valuation crisis proved that some performance conclusions were being measured
on an unsafe foundation.

### A. Capital Deployment / ADD / Lot Conversion

Problem:

PM ADD intent and positive allocation requests existed, but much of the
requested capital did not become executable `BUY_ADD` or `BUY_NEW` quantity.
Phase29-B showed only partial D61 improvement: BUY_ADD fills increased from 3
to 4 and notional improved, but Runtime BUY_ADD plans stayed at 4, average cash
worsened, and exposure did not materially improve. Phase29-C traced the main
remaining bottleneck to continuous target weights meeting 100-share lot
granularity, minimum executable notional, concentration headroom, and partial
residual recycling.

Repairs and closed contracts:

- Lot-First Feasibility-Aware Rebatch.
- Cap-Constrained Lot Floor.
- Iterative Residual Reallocation.
- Strategy cap and Safety hard cap separation.
- Residual capital recycling without forced deployment.
- Cash remains valid when no eligible, lot-feasible, authority-safe opportunity
  exists.
- `BUY_ADD` semantics were preserved; ADD was not weakened and BUY_NEW was not
  forced.

Important lesson:

High cash was not a single root cause. It could reflect opportunity shortage,
lot infeasibility, concentration policy, residual-recycling gaps, or deliberate
cash preservation after candidate exhaustion.

### B. Re-entry / Low-Price Risk

Problem:

Low-price and same-symbol re-entry cases exposed Strategy design risk:
percentage-return features could rank very low-priced names highly, while tick
risk, liquidity capacity, cooldown, and recovery quality were not explicit
enough. Phase29 did not treat a single symbol as proof; calibration and
cross-period evidence were required.

Repairs and closed contracts:

- Semantic `REENTRY` detection.
- Three completed-business-day cooldown.
- Recovery hurdle.
- Low-price single-tick risk tiers.
- Liquidity capacity cap.
- Allocation cap for low-price risk.
- No blanket Re-entry ban.
- ADD / BUY_ADD is not REENTRY.
- Existing holdings, SELL, REDUCE, EXIT, and canonical ADD remain independent.

Reason blanket ban was rejected:

Re-entry can be legitimate after cooldown and recovered evidence. A blanket ban
would hide Strategy weakness rather than distinguish churn from true recovery.

### C. Expected Edge / Opportunity Score Semantics

Problem:

The runtime was treating `runtime_opportunity_score` as if it were calibrated
economic expected return. In reality, the active Opportunity score was an
uncalibrated relative model score. Using `score <= 0` or below-top20 as an
absolute BUY_NEW rejection authority was a semantic error.

Repairs and closed contracts:

- `runtime_opportunity_score` canonicalized as
  `uncalibrated_relative_model_score` unless future calibration evidence says
  otherwise.
- Absolute zero gate removed for uncalibrated relative scores.
- Top20 is metadata / ranking context, not an absolute hard gate.
- Portfolio Construction and runtime adapter metadata propagation were repaired.
- Missing or malformed semantic metadata still fails closed.
- Future calibrated economic expected-return semantics remain allowed only when
  explicit `calibration_applied=true` and `economic_units_available=true`.

Phase30 handoff:

Formal Expected Edge Calibration remains a research candidate. It must not use
future returns as runtime learning input or revive an absolute gate without a
proper production-common calibration contract.

### D. Multi-Horizon Momentum Trajectory / BUY_WAIT

Problem:

Single-horizon momentum was not enough to distinguish healthy continuation from
fading prior winners or recent overheated moves. Actual examples showed
late-entry / prior-winner reversal risk.

Implemented facts and classes:

- `price_momentum_return_1d`
- `price_momentum_return_3d`
- `price_momentum_return_5d`
- `price_momentum_return_10d`
- `price_momentum_return_20d`
- `price_momentum_return_60d`
- recent volatility-adjusted moves
- momentum deltas
- `HEALTHY_CONTINUATION`
- `FADING_PRIOR_WINNER`
- `RECENT_ACCELERATION_OVERHEAT`
- `MIXED_OR_UNRESOLVED`

Closed `BUY_WAIT` contract:

- Temporary BUY_NEW ineligibility.
- No BUY Pending.
- No Human Review Pending.
- No runtime halt by itself.
- Reevaluate next business day from PIT features.
- SELL independence preserved.
- BUY_ADD unaffected.
- REENTRY unaffected.
- Existing holdings unaffected.

Why integration issues repeated:

AV implemented the classification, but actual runtime later exposed producer,
consumer, and adapter gaps. AY connected market-refresh feature production; BC
propagated the feature subset from Candidate/Opportunity artifacts into BUY
Quality. This is a canonical Phase29 lesson: feature correctness is not enough
until the full path reaches the actual runtime consumer.

### E. Execution NO_ACTION Contract

Problem:

After BUY_WAIT and no-op planning became normal, a valid zero-order day reached:

```text
Morning -> NO_ORDER_AUTHORIZED
Pending EMPTY
Submit NO_SUBMISSION_REQUIRED
AUTHORIZED_NO_ORDER PASS
```

Execution then halted with `submit NO_ACTION authority inconsistent`.

Closed contract:

`NO_SUBMISSION_REQUIRED` with `AUTHORIZED_NO_ORDER` and an empty Pending / zero
submitted-order state is a valid execution outcome. It should produce no fills,
no Ledger append, no Current mutation, no Pending mutation, and allow day
completion. Malformed no-action authority remains fail-closed.

### F. Performance Measurement / Valuation Crisis

This was the most important Phase29 engineering lesson.

Stage 1: A repeating valuation alternation was found for `67310`:

```text
2000 -> 3000 -> 2000 -> 3000
```

With 100 shares, this generated approximately `+/-100,000` JPY of false PnL.

Stage 2: BF proved the defect was not symbol-specific:

- Earliest contamination: `2022-08-10`
- Contaminated symbols: `104`
- Contaminated days: `299 / 300`
- False Equity reached capital authority.
- Sizing equity was contaminated.
- Position weights were contaminated.
- Classification: `CAPITAL_AUTHORITY_CONTAMINATED`

Stage 3: BE failed closed on blind adjusted analytical price consumption.

Stage 4: BG showed the actual Historical current-valuation path had no proper
economic price producer / reconciliation propagation.

Stage 5: BH connected raw/economic source, but exposed a second problem:
`raw price x adjusted-basis quantity`. `94320` and `94340` created a false Day1
equity of `1,851,270`, or `+85.13%`.

Stage 6: BI classified this as
`PRICE_QUANTITY_ADJUSTMENT_BASIS_MISMATCH`.

Correct examples:

- `94320`: quantity `200`, fill `149.2`, adjusted close `149.8`, raw close
  `3744.0`, correct market value `29,960`.
- `94340`: quantity `100`, fill `151.4`, adjusted close `151.8`, raw close
  `1517.5`, correct market value `15,180`.

Stage 7: BJ implemented the price/quantity adjustment-basis contract.

Stage 8: BK showed Day2 HALT because basis metadata was lost during
runtime-owned Current rebuild, not because the BJ contract was wrong.

Stage 9: BL persisted and materialized basis metadata across:

- existing position carry-forward
- new BUY position creation
- ADD
- REDUCE
- partial SELL
- EXIT deletion

Closed valuation contracts:

- Adjusted analytical prices cannot be consumed as economic valuation without
  provenance.
- Raw price is not always correct.
- Adjusted price is not always correct.
- Price and quantity must be on the same basis, or explicitly reconciled.
- Unknown, ambiguous, stale, future, or mismatched authority fails closed.
- Basis metadata must persist through runtime-owned state transitions.

## Performance Evidence Reset

The old long run:

```text
runtime-test-historical-extended-smoke-20260814T131647480030Z
```

is invalid as formal performance evidence. It may be retained only as:

```text
RUNTIME_FORENSIC / DEFECT_DISCOVERY_EVIDENCE
```

Invalidated for tuning authority:

- Equity curve
- Return
- MDD
- Cash attribution
- Exposure attribution
- Regime attribution
- Winner giveback
- BUY_NEW performance
- ADD performance
- SELL performance
- Campaign performance
- Deployed-Capital Quality

Old conclusions from that run are `HYPOTHESIS_GENERATION_ONLY`, not Phase30
tuning authority.

## Post-BL Clean 20BD Candidate

Target run:

```text
runtime-test-historical-extended-smoke-20260815T030154161245Z
```

Status handed off:

```text
POST_BL_CLEAN_20BD_BASELINE_CANDIDATE
```

Observed user-provided final evidence:

- Business days processed: `20`
- Period: `2022-08-10` through `2022-09-07`
- Initial Equity: `1,000,000`
- Final Equity: `972,510`
- Total Return: `-2.75%`
- Final Cash: `431,770`
- Final Exposure: `55.60%`
- Final Positions: `7`
- Final Runtime Test status: `REVIEW_REQUIRED`
- Close returned `REVIEW_REQUIRED`

Interpretation:

The negative return is not a Phase30 blocker. The user approved Phase30
migration after 20BD completion regardless of performance result. The unresolved
`REVIEW_REQUIRED` close reason must be carried to Phase30-A as a read-only
integrity / close review topic. Clean measurement integrity and Strategy quality
must be evaluated separately.

## Retrospective

### What Went Well

- Phase29 did not reduce every symptom to a Strategy parameter issue.
- BUY / SELL independence was repeatedly defended.
- Historical-only hacks were largely avoided.
- Fail-closed behavior was preserved even when it created short-term HALTs.
- Actual runtime adapters and persisted state were eventually tested, not only
  core functions.
- Valuation contamination was found before Phase30 tuning used it as authority.
- Price / quantity basis became a production-common contract.
- A clean 20BD candidate became possible after BE/BH/BJ/BL.

### What Did Not Go Well

- Producer / consumer / adapter / persistence gaps appeared repeatedly.
- Fixture-level PASS was often insufficient for actual runtime lifecycle PASS.
- Metadata propagation was repaired in one boundary, then lost at another.
- Performance analysis began before valuation integrity had a strong enough
  gate.
- Contaminated runs generated Strategy hypotheses that now require quarantine.
- Local repairs sometimes exposed the next missing authority layer, as with
  BE -> BH -> BI -> BJ -> BK -> BL.

### Why Problems Repeated

The common pattern was partial authority migration. A semantic fact or metadata
field would be created, but the full chain was not always proven:

```text
producer -> artifact -> adapter -> consumer -> persisted Current -> next-day consumer
```

Day1 fixtures also missed Day2 state-transition risks. Authority metadata was
often treated as local evidence rather than an end-to-end lifecycle contract.
Phase29 corrected many of those failures, but Phase30 should bake the process
change into every new performance or Strategy task.

### What Should Change In Phase30

- Add end-to-end authority-path regression for every new semantic field.
- Validate Day1 and Day2, plus BUY / ADD / REDUCE / partial SELL / EXIT
  transitions.
- Put measurement integrity before performance attribution.
- Quarantine contaminated or superseded runs immediately.
- Version clean baselines and do not mix code-era evidence.
- Separate Runtime correctness from Strategy quality.

## Phase29 Closed Contracts

Do not reopen these in Phase30 without new evidence:

- BUY / SELL independence.
- PM ADD -> Runtime BUY_ADD.
- Incremental Investment semantics.
- Lot-aware allocation.
- Strategy cap / Safety cap separation.
- Residual capital recycling without forced deployment.
- Semantic REENTRY.
- Re-entry cooldown.
- Re-entry recovery hurdle.
- Low-price / tick / liquidity protections.
- REDUCE discrete-lot semantics.
- Expected Edge relative semantics.
- Runtime semantic metadata propagation.
- Multi-Horizon Momentum Trajectory.
- `BUY_WAIT` non-Pending semantics.
- Execution `NO_SUBMISSION_REQUIRED` / `AUTHORIZED_NO_ORDER` continuity.
- Valuation fail-closed.
- Price / quantity adjustment-basis contract.
- Basis metadata persistence.

## Permanent Project Rules

- Production / Demo / Historical common Runtime contracts.
- Historical-only Strategy is prohibited.
- Production fail-closed weakening is prohibited.
- BUY / SELL independence is mandatory.
- Future data is prohibited.
- Paper Ledger, PnL, test result, selected result, or bought result must not be
  used as runtime learning input.
- Long-running Historical validation is user-operated.
- Codex may implement, audit, and run focused/short regressions, but must not
  run long Historical unless explicitly authorized by a future task and policy.
- Fixed BUY count is prohibited.
- Fixed position count is prohibited.
- Forced exposure is prohibited.
- Cash is acceptable when no valid opportunity exists.
- Lot-rounding or avoidable residual-cash defects remain repair targets.
- Blanket Re-entry ban is prohibited.
- Safety authority must not be weakened for Strategy convenience.

## Phase30 Objective

Primary objective:

```text
CLEAN EVIDENCE BASED PERFORMANCE IMPROVEMENT
```

Phase30 should improve returns for the production-common `1,000,000` JPY
cash-equity Strategy on top of clean measurement. The project may retain the
annual `+50%` ambition as a goal, but Phase30 must not tune thresholds simply
to pass a historical test or use Historical-only logic.

## Phase30 Priority Roadmap

### Priority 0: Clean Performance Measurement Foundation

Why: Phase29 proved measurement can be the hidden root cause.

Current evidence: BE/BH/BJ/BL repaired valuation authority, basis matching, and
basis persistence. The post-BL 20BD candidate exists but ended with
`REVIEW_REQUIRED`.

Unknowns: close reason, full 20BD valuation reconciliation, abnormal jumps,
symbol contribution, and whether all Daily PnL reconciles.

Measure: valuation integrity, price/quantity basis, Current/Ledger consistency,
cash, exposure, equity, Daily PnL, and position weights.

Must not assume: a negative or positive return is meaningful before measurement
integrity is checked.

### Priority 1: Clean Long-Horizon Baseline

Why: Phase30 needs a non-contaminated baseline before tuning.

Current evidence: the old long run is invalid; post-BL short clean evidence is
candidate-only.

Unknowns: long-horizon return, drawdown, regime performance, deployed-capital
quality, and runtime stability after BL.

Measure: user-operated 4-year fresh Historical after clean short validation and
close review.

Must not assume: old 100BD or contaminated 4-year numbers still represent the
current Strategy.

### Priority 2: Deployed-Capital Quality

Why: Cash underuse and capital quality drove much of Phase29.

Current evidence: Phase29 repaired lot and cap-aware deployment paths, but clean
post-BL deployed-capital return is unknown.

Unknowns: whether extra deployed capital has positive marginal return.

Measure: deployed return, marginal capital return, unused cash reason, eligible
but unallocated opportunities, lot/cap/cash constraints.

Must not assume: more exposure is always better.

### Priority 3: Entry Quality / Multi-Horizon Momentum Trajectory

Why: AV introduced the ability to distinguish healthy continuation from fading
or overheated entries.

Current evidence: focused regressions pass; actual clean outcome distribution is
not yet proven.

Unknowns: HEALTHY outcome quality, FADING/OVERHEAT avoided losses, MIXED
population quality, missed opportunity from BUY_WAIT.

Measure: class distribution, BUY_WAIT count, BUY_NEW count, forward outcomes,
MFE/MAE, symbol concentration.

Must not assume: a hand-picked 78780 or 53800 case defines thresholds.

### Priority 4: Winner Continuation / Profit Retention

Why: Winner dependency and giveback were recurring hypotheses.

Current evidence: old giveback evidence is contaminated; Phase29-K showed high
winner dependency in a pre-contamination-era 100BD reference, but Phase30 needs
clean recalculation.

Unknowns: whether strong winners are exited too early, reduced too late, or
allowed to give back too much.

Measure: MFE, MAE, peak unrealized PnL, realized PnL, retention ratio, campaign
length, peak-to-exit giveback.

Must not assume: a fixed profit-take percent is approved.

### Priority 5: Market Regime / Transition

Why: Performance may be regime-dependent, and SELL / HOLD behavior may need
context measurement.

Current evidence: old BULL/RANGE/BEAR/RECOVERY/CORRECTION attribution is
hypothesis-only.

Unknowns: where clean Strategy earns or loses money by regime and transition.

Measure: portfolio return, exposure, BUY/HOLD/ADD/REDUCE/EXIT behavior, and
profit giveback across BULL, RANGE, BEAR, RECOVERY, CORRECTION and transitions.

Must not assume: contaminated regime attribution is actionable.

### Priority 6: SELL / PM Market Context Authority

Why: Phase30 should test whether PM reacts only after individual weakness or
uses market context for protection.

Current evidence: BUY / SELL independence is closed; SELL quantity and
NO_ACTION continuity are repaired.

Unknowns: whether SELL / REDUCE / EXIT is context-aware enough.

Measure: HOLD, REDUCE, EXIT timing relative to regime, transitions, momentum,
MFE, and giveback.

Must not assume: BUY and SELL authority should be coupled.

### Remaining Priorities

7. Exit Outcome Separability.
8. ADD Quality.
9. Recovery Re-entry Quality.
10. Formal Expected Edge Calibration.

## Phase30 Research Questions To Preserve

Entry:

- Does `HEALTHY_CONTINUATION` produce better entries?
- Does `FADING_PRIOR_WINNER -> BUY_WAIT` avoid losses?
- Does `RECENT_ACCELERATION_OVERHEAT -> BUY_WAIT` reduce high-price chasing?
- How should `MIXED_OR_UNRESOLVED` be handled?
- Is BUY_WAIT missing too many opportunities?

Capital deployment:

- Is cash caused by opportunity shortage, quality gates, lot/cap constraints,
  or deliberate cash preservation?
- Is marginal deployed capital positive?
- Can more capital be allocated to good opportunities without forced exposure?

ADD:

- Is ADD incremental return positive?
- Does ADD to winners work?
- Does ADD increase later giveback?
- Is ADD timing too late?

HOLD / REDUCE / EXIT:

- Can GOOD CUT and PREMATURE EXIT be separated?
- Can Pullback and Breakdown be separated?
- Is REDUCE too early or EXIT too late?
- Is SELL only reacting after weakness appears?

Profit retention:

- What percent of peak unrealized profit is retained?
- Is a `STRONG_WINNER_PROFIT_TAKE_REDUCE` semantic useful?
- No fixed profit-take percentage is approved.

Market context:

- How does Strategy perform in BULL, RANGE, BEAR, RECOVERY, CORRECTION?
- Does HOLD / REDUCE / EXIT consume Market Context?
- Do regime transitions require different portfolio behavior?

Re-entry:

- Does cooldown + recovery hurdle REENTRY create profit?
- Does it reduce churn without missing real recoveries?

Expected Edge:

- Does relative score separate forward outcomes?
- Can economic calibration be built without violating learning prohibitions?

## Phase30 Evidence Hierarchy

Prefer:

1. Clean production-common fresh Historical evidence.
2. Runtime authoritative artifacts.
3. Current / Ledger / Execution evidence.
4. J-Quants PIT source data.
5. Read-only forward-outcome attribution.

Do not use as tuning authority:

- contaminated historical runs
- superseded runs
- debugging fixture outcomes
- future-return-based Runtime logic
- Paper Ledger performance as learning input
- hand-selected anecdotal winners/losers

Case studies may create hypotheses, but not Strategy changes by themselves.

## Recommended Phase30 First Task

`Phase30-A - Post-BL 20BD Clean Baseline Integrity / Close Review / Performance Attribution Audit`

Target:

`runtime-test-historical-extended-smoke-20260815T030154161245Z`

Minimum scope:

- final `REVIEW_REQUIRED` direct reason
- valuation integrity
- price/quantity basis integrity
- Daily PnL reconciliation
- Equity reconciliation
- basis persistence
- abnormal valuation jumps
- BUY_NEW / BUY_WAIT
- ADD / REDUCE / EXIT / SELL
- cash / exposure
- symbol contribution
- total `-27,490` JPY loss attribution
- `2022-08-24` `-43,400` loss attribution
- `2022-09-07` `+24,040` recovery attribution

Phase30-A should be read-only. Strategy or threshold changes should come only
after the clean root-cause attribution.

## Closure Notes

Phase29 achieved real Strategy/runtime improvements and also discovered that
performance measurement was not trustworthy enough. That is not a failure to
improve Strategy; it is the discovery that Strategy improvement must be built on
valid measurement. The clean `-2.75%` 20BD candidate is valuable precisely
because it is a candidate for clean evidence. Phase30 should analyze why it lost
money, not retreat into contaminated prior wins or tune blindly.
