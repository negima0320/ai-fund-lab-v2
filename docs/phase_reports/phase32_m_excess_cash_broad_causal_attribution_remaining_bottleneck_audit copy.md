# Phase32-M — Excess Cash Broad Causal Attribution / Remaining Bottleneck Audit

## Executive Summary

Phase32-M used only the existing Pre-L run:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z`

Primary window: `2023-05-31` through `2024-02-26`. No fresh validation, replay, resume, backtest, production code, config, threshold, risk pacing, cash preference, PC/MCC, ADD/NEW, or residual authority changes were made.

The late-Plateau excess-Cash issue is not explained by a capital-size anchor. It is primarily explained by a capital frontier composition shift after portfolio history accumulates: a large share of the non-current opportunity set becomes semantic REENTRY, and in the Pre-L artifacts those rows are suppressed by generic/insufficient prior-exit context. In the Plateau window, zero-weight reasons include `reentry_opportunity_not_requalified` 2,459 times, `insufficient_prior_exit_context` 397 times, `reentry_minimum_cooldown_not_satisfied` 339 times, and `reentry_repeated_unresolved_churn` 327 times.

Re-entry is the dominant causal bucket, but it is not the only material structure. Excluding REENTRY, the high-Cash BULL days still show small accepted NEW demand relative to available capital, plus a broad shadow residual-reconsideration surface that identifies deployable-looking security capital but remains non-authoritative. The evidence supports a bounded opportunity claim, not a post-L counterfactual fill claim.

The most important finding for sequencing is: Phase32-L should get a narrow fresh validation first, because it repairs the single confirmed defect and should materially change the frontier. A full Historical validation should wait until the L effect is measured and the remaining shadow/residual and non-reentry NEW suppression questions are narrowed.

## Scope And Cohorts

I treated "High-Cash BULL" as `market_context.regime_state == BULL` or `trend_state == BULL` with high PC Cash. The artifact set yields 23 Plateau days at `cash_weight > 50%`:

`2023-06-27`, `2023-09-25`, `2023-09-26`, `2023-09-27`, `2024-01-10`, `2024-01-11`, `2024-01-12`, `2024-01-15`, `2024-01-16`, `2024-01-17`, `2024-01-18`, `2024-01-19`, `2024-01-22`, `2024-01-23`, `2024-01-24`, `2024-01-25`, `2024-01-26`, `2024-01-29`, `2024-01-30`, `2024-01-31`, `2024-02-01`, `2024-02-22`, `2024-02-26`.

The smaller Healthy/NORMAL high-Cash cluster is 12 days at `risk_pacing_intent == NORMAL_DEPLOYMENT` and `cash_weight >= 45%`: `2023-11-02` plus the January sequence from `2024-01-05` through `2024-01-31`.

## Daily Capital Waterfall

JPY values are same-day equity-weighted artifact values. `ReCtxBound` is an attributable opportunity bound from Pre-L rows with REENTRY zero weight and generic/insufficient prior-exit context; it is not a predicted post-L buy amount.

| Date | Equity | Cash | Available | Req NEW | Acc NEW | Acc ADD | Residual Shadow | PS Buy | RT Buy | BUY Fill | SELL Fill | ReCtxBound | NonReReq | Selected | Winner |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2024-01-05 | 1,815,550 | 1,394,598 | 1,432,899 | 64,841 | 64,841 | 0 | 194,522 | 88,648 | 38,300 | 37,900 | 199,200 | 1,556,173 | 64,841 | 1 | NEW_BUY |
| 2024-01-09 | 1,812,690 | 1,402,674 | 1,402,674 | 0 | 0 | 0 | 120,845 | 60,422 | 0 | 0 | 0 | 1,570,982 | 0 | 0 | CASH_OPTIONALITY |
| 2024-01-10 | 1,824,590 | 1,233,771 | 1,430,601 | 158,659 | 158,659 | 0 | 237,989 | 317,227 | 182,600 | 181,600 | 37,300 | 1,427,931 | 158,659 | 2 | NEW_BUY |
| 2024-01-11 | 1,821,740 | 1,350,700 | 1,350,700 | 0 | 0 | 0 | 269,887 | 67,472 | 0 | 0 | 0 | 1,686,795 | 0 | 0 | CASH_OPTIONALITY |
| 2024-01-12 | 1,828,910 | 1,139,387 | 1,473,350 | 121,926 | 121,926 | 0 | 243,852 | 369,067 | 333,900 | 323,400 | 182,200 | 1,524,076 | 121,926 | 2 | NEW_BUY |
| 2024-01-15 | 1,843,390 | 1,276,500 | 1,276,500 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 170,000 | 1,580,036 | 0 | 0 | CASH_OPTIONALITY |
| 2024-01-23 | 1,863,070 | 1,402,800 | 1,402,800 | 0 | 0 | 0 | 243,008 | 142,040 | 0 | 0 | 0 | 1,620,051 | 0 | 0 | CASH_OPTIONALITY |
| 2024-01-24 | 1,849,330 | 1,564,901 | 1,608,701 | 77,056 | 77,056 | 0 | 77,056 | 106,555 | 115,800 | 138,350 | 276,100 | 1,618,177 | 77,056 | 1 | NEW_BUY |
| 2024-01-25 | 1,828,750 | 1,177,201 | 1,552,400 | 182,875 | 182,875 | 0 | 274,313 | 521,637 | 453,940 | 456,930 | 68,400 | 1,371,563 | 182,875 | 2 | NEW_BUY |
| 2024-01-26 | 1,817,840 | 1,030,235 | 1,137,168 | 106,933 | 106,933 | 0 | 0 | 62,735 | 71,600 | 71,400 | 43,450 | 1,176,259 | 106,933 | 1 | NEW_BUY |
| 2024-01-31 | 1,809,150 | 1,075,730 | 1,215,230 | 48,297 | 48,297 | 0 | 226,144 | 181,896 | 139,500 | 137,670 | 0 | 1,469,934 | 56,536 | 1 | NEW_BUY |

Waterfall readout: the largest drop occurs before PC accepted security weight. On multiple focus days, available incremental capital exceeds JPY 1.2M, but requested/accepted non-reentry NEW is zero or only one-lot-sized. Later PS/runtime/fill stages mostly consume what PC admitted; they do not explain the bulk of remaining Cash.

## Period Comparison

| Metric | Spring Acceleration | Plateau |
|---|---:|---:|
| Days | 63 | 182 |
| Avg Cash weight | 19.82% | 35.04% |
| Avg available incremental budget | 39.57% | 43.93% |
| Avg requested NEW weight | 16.21% | 8.79% |
| Avg accepted NEW weight | 15.77% | 8.26% |
| Avg REENTRY normal target weight | 57.62% | 63.05% |
| Avg generic/context-bound REENTRY target weight | 52.08% | 57.06% |
| Cash winner days | 46 / 63 | 145 / 182 |
| NEW winner days | 17 / 63 | 37 / 182 |
| Residual shadow rows | 205 | 474 |
| Residual shadow notional | JPY 8.27M | JPY 23.51M |

Portfolio history accumulation changes the frontier: later Plateau has more prior-exit-sensitive opportunity, lower non-reentry NEW demand, a higher Cash winner rate, and more residual reconsideration evidence. This supports a structural trigger rather than a simple market-quality or equity-scaling explanation.

## Re-entry Contribution

Plateau zero-weight REENTRY reasons are dominant. The broad Pre-L capital-at-risk signal is the sum of normal target weights on semantic REENTRY rows that are blocked before admission, especially rows whose previous exit class collapsed to `GENERIC` or whose reason is `insufficient_prior_exit_context`.

For the 23 BULL days with Cash above 50%, same-day sums were:

| Measure | Value |
|---|---:|
| Cash | JPY 27.47M |
| Available incremental capital | JPY 29.97M |
| Accepted NEW | JPY 1.82M |
| Residual shadow opportunity | JPY 3.14M |
| Generic/context-bound REENTRY opportunity | JPY 31.28M |
| Non-reentry NEW request | JPY 1.85M |

This makes `REENTRY_CONTEXT_DEFECT` the primary cause in Pre-L artifacts. The bound can exceed Cash because it is row-level normal target opportunity before mutual-exclusion, budget, lot, concentration, and ranking constraints. It should be read as a high-confidence opportunity surface, not as deployable notional.

## Non-Reentry Cash Analysis

Excluding semantic REENTRY, high-Cash NORMAL days still do not generate enough security demand to consume available capital:

| Cluster | Days | Avg Cash | Avg Available | Avg Req NEW | Avg Acc NEW | NonReReq Notional | Cash Notional |
|---|---:|---:|---:|---:|---:|---:|---:|
| NORMAL Cash >= 30% | 16 | 59.92% | 66.68% | 4.20% | 4.20% | JPY 1.22M | JPY 17.49M |
| NORMAL Cash >= 45% | 12 | 68.33% | 74.41% | 3.71% | 3.71% | JPY 0.82M | JPY 15.00M |
| Low-Cash NORMAL control | 11 | 8.49% | 33.76% | 14.06% | 14.06% | JPY 2.92M | JPY 1.68M |

The low-Cash BULL/NORMAL controls show the same machinery can admit NEW when non-reentry NEW demand exists. Therefore non-reentry suppression is material as a remaining bottleneck, but the evidence is more consistent with insufficient admitted non-reentry supply and quality filtering than with a confirmed non-reentry defect.

## Residual Authority Analysis

Plateau residual reconsideration is material:

| Scope | Rows | Dates | Weight Sum | Same-day Notional | PS Authorized | Runtime Authorized | Lot-executable Rows |
|---|---:|---:|---:|---:|---:|---:|---:|
| Spring | 205 | 62 | 5.2295 | JPY 8.27M | 0 | 0 | 16 |
| Plateau | 474 | 171 | 13.0942 | JPY 23.51M | 0 | 0 | 50 |
| Plateau Cash >= 45% | 178 | 68 | 5.6061 | JPY 10.16M | 0 | 0 | 33 |

The rows are overwhelmingly `COMPARABLE_MARGINAL`, with a small number of `COMPARABLE_HIGH` and `STRONG` cases. The January focus rows include positive `authorized_shadow_weight`, `interaction_result = DEPLOY_ELIGIBLE`, `shadow_outcome = SHADOW_SECURITY_PARTICIPATION_VALID`, and reason codes such as `G95_SHADOW_NON_AUTHORITATIVE`, `SHADOW_CAPITAL_BUDGET_MAXIMUM_ONLY`, and `SHADOW_OPTIONAL_CASH_FIRST_CLASS`.

Important correction: in this run the residual rows are not marked `authorized_for_position_sizing = true`; they are `authorized_for_position_sizing = false` and `authorized_for_runtime_order = false`. The confirmed issue is therefore a non-authoritative shadow residual allocation surface, not a proven PS-authorized/runtime-disconnected defect.

## Active And Passive Cash

`ACTIVE_CASH_PREFERENCE` is material. Cash reason codes in Plateau include `MARGINAL_OPPORTUNITY_SET` 156 times, `NO_VALID_COMPETITOR` 126 times, `CAUTIOUS_MARKET_OPTIONALITY_ELEVATED` 122 times, and `HEALTHY_MARKET_OPTIONALITY_LOW` 31 times. In the NORMAL Cash >= 45% cluster, `HEALTHY_MARKET_OPTIONALITY_LOW` and `NO_VALID_COMPETITOR` appear on all 12 days.

`PASSIVE_RESIDUAL_CASH` is also material but secondary. In the strict NORMAL high-Cash cluster, accepted NEW consumed about JPY 0.81M while residual shadow opportunity was about JPY 1.99M and final Cash was about JPY 15.00M. Passive residual contributes, but it does not dominate the Cash balance.

`NO_DEPLOYABLE_SECURITY` is partially true at the authoritative surface: several focus days show zero selected NEW and Cash winner. It is not fully true semantically because shadow residual and REENTRY opportunity rows exist.

## Healthy-BULL Comparison

Focus Healthy/NORMAL dates show the Cash issue without risk pacing blocks:

- `2024-01-11`: Cash JPY 1.35M, available JPY 1.35M, selected NEW 0, REENTRY context-bound opportunity JPY 1.69M, residual shadow JPY 0.27M.
- `2024-01-15`: Cash JPY 1.28M, available JPY 1.28M, selected NEW 0, REENTRY context-bound opportunity JPY 1.58M, no residual shadow.
- `2024-01-23`: Cash JPY 1.40M, available JPY 1.40M, selected NEW 0, REENTRY context-bound opportunity JPY 1.62M, residual shadow JPY 0.24M.
- `2024-01-24`: Cash JPY 1.56M, available JPY 1.61M, selected NEW 1, accepted NEW JPY 0.08M, REENTRY context-bound opportunity JPY 1.62M.
- `2024-01-31`: Cash JPY 1.08M, available JPY 1.22M, selected NEW 1, accepted NEW JPY 0.05M, REENTRY context-bound opportunity JPY 1.47M, residual shadow JPY 0.23M.

Low-Cash NORMAL controls differ mainly in admitted NEW demand: average accepted NEW is 14.06% versus 3.71% in the strict high-Cash NORMAL cluster. This points to frontier composition and admission, not risk-pacing state, as the discriminant.

## ADD / NEW / Cash Interaction

ADD evidence is present in Plateau but is not the primary Cash bottleneck in the Pre-L run. Plateau had 5 days with `canonical_add_marginal_capital_competition.increment_rows` and 79 increment rows. Competitor reason evidence includes `ADD_LOST_TO_NEW_BUY` 47 times, `ADD_LOST_TO_CASH` 8 times, `ADD_SELECTED` 5 times, and `ADD_COMPETITOR_ELIGIBLE` 6 times.

The exact triad `ADD loses to NEW` + `NEW fails to consume material capital` + `Cash remains` is not strongly represented through authoritative accepted ADD/NEW fields because `requested_incremental_weight` is generally zero in the top-level reconciliation. The interaction remains material as an architectural question, but Phase32-M does not justify changing ADD/NEW priority before L validation and a narrower ADD artifact audit.

## Causal Bucket Attribution

| Bucket | Evidence | Materiality | Classification |
|---|---|---:|---|
| REENTRY_CONTEXT_DEFECT | 2,459 `reentry_opportunity_not_requalified`, 397 `insufficient_prior_exit_context`, generic prior class observed pre-L | High | CONFIRMED_DEFECT, repaired in Phase32-L |
| REENTRY_OTHER_VALID_CONSTRAINT | cooldown 339, repeated churn 327; may remain valid even after L | Medium | CALIBRATION_QUESTION |
| PC_ACCEPTED_WEIGHT_ZERO_NON_REENTRY | high-Cash NORMAL accepted NEW only 3.71% avg | Medium | ARCHITECTURAL_LIMITATION |
| NEW_ENTRY_QUALITY_LIMITATION | most competitors `COMPARABLE_MARGINAL`; low-Cash controls deploy when NEW demand exists | Medium | CALIBRATION_QUESTION |
| RESIDUAL_RECONSIDERATION_GAP | 474 Plateau shadow rows, JPY 23.51M same-day shadow notional, 0 production binding | Medium | ARCHITECTURAL_LIMITATION |
| AUTHORITATIVE_SHADOW_GAP | positive shadow rows are not PS/runtime-authorized | Medium | ARCHITECTURAL_LIMITATION / OBSERVABILITY_GAP |
| MCC_CASH_PREFERENCE | Cash reason codes persist in Healthy/NORMAL days | Medium | CALIBRATION_QUESTION |
| PASSIVE_RESIDUAL_CASH | JPY 1.99M strict high-Cash NORMAL shadow residual vs JPY 15.00M Cash | Medium-Low | ARCHITECTURAL_LIMITATION |
| RISK_PACING | high-Cash exists under NORMAL_DEPLOYMENT; caution explains other days | Low for focus cluster | NORMAL_BEHAVIOR |
| MARKET_QUALITY_CAUTION | material outside Healthy/NORMAL; not focus root cause | Medium outside focus | NORMAL_BEHAVIOR |
| SAFETY_CONCENTRATION | appears in Cash reasons, stronger in low-Cash controls too | Low-Medium | NORMAL_BEHAVIOR |
| LOT_EXECUTABILITY | 50 Plateau residual rows lot-executable; lot blocks exist but not dominant | Low-Medium | ARCHITECTURAL_LIMITATION |
| ADD_NEW_COMPETITION | ADD loses to NEW/Cash observed, top-level ADD demand mostly zero | Low-Medium | OBSERVABILITY_GAP |
| SELL_GENERATED_CASH | SELL fills add Cash on some focus days, but do not explain admission failure | Low | NORMAL_BEHAVIOR |
| GENUINE_NO_COMPELLING_OPPORTUNITY | plausible for marginal non-reentry set after REENTRY exclusion | Medium | NORMAL_BEHAVIOR / CALIBRATION_QUESTION |

## Root-Cause Ranking

1. `REENTRY_CONTEXT_DEFECT`: affected thousands of Plateau rows and dominates high-Cash BULL capital-at-risk. Confidence high. Classification: `CONFIRMED_DEFECT`, already repaired in Phase32-L.
2. `PC_ACCEPTED_WEIGHT_ZERO_NON_REENTRY` / `NEW_ENTRY_QUALITY_LIMITATION`: affected high-Cash NORMAL days even after REENTRY exclusion; accepted NEW averaged only 3.71% in the strict cluster. Confidence medium. Classification: `CALIBRATION_QUESTION`.
3. `RESIDUAL_RECONSIDERATION_GAP` / `AUTHORITATIVE_SHADOW_GAP`: 474 Plateau rows and JPY 23.51M cumulative shadow notional, but no production binding. Confidence medium-high for observability, medium for repair. Classification: `ARCHITECTURAL_LIMITATION`.
4. `MCC_CASH_PREFERENCE`: Cash is actively preferred by semantics on Healthy/NORMAL days. Confidence medium. Classification: `CALIBRATION_QUESTION`.
5. `MARKET_QUALITY_CAUTION` / `RISK_PACING`: material in all-Plateau aggregates but not sufficient for the Healthy/NORMAL January cluster. Confidence high. Classification: `NORMAL_BEHAVIOR`.
6. `ADD_NEW_COMPETITION`: material enough to keep investigating, but not enough to change production. Confidence medium-low. Classification: `OBSERVABILITY_GAP`.

## Repair Portfolio

`MUST_REPAIR`

- Phase32-L `prior-exit context materialization defect`: already repaired; needs validation.

`SHOULD_INVESTIGATE_FOR_REPAIR`

- Non-reentry NEW admission and quality-to-capital conversion on high-Cash BULL days after excluding REENTRY.
- Residual reconsideration authority path: when, if ever, a shadow `DEPLOY_ELIGIBLE` row should become authoritative.
- MCC Cash preference semantics in Healthy/NORMAL conditions where `NO_VALID_COMPETITOR` coexists with positive shadow opportunity.
- ADD/NEW/Cash artifact lineage for cases where ADD loses to NEW, NEW consumes only one-lot or zero capital, and Cash remains.

`DO_NOT_CHANGE`

- Blanket SELL/early-exit behavior.
- Risk pacing state machine based only on this audit.
- Safety concentration limits and lot-executability protections.
- Cash reserve behavior in cautious/conflicted markets.
- ADD-vs-NEW priority or Cash preference thresholds without post-L evidence.

## Fresh Validation Timing

Recommendation: `NARROW_VALIDATION_ONLY`.

Run a narrow post-L validation that targets the January sequence and representative high-Cash BULL days before running a full Historical validation. The L repair should materially alter the dominant re-entry frontier; measuring that first will prevent the remaining Cash residual from being misattributed. A full Historical run is better deferred until post-L deltas are known and the residual/non-reentry hypotheses have sharper acceptance criteria.

## Remaining Phase32 Issues

- Post-L validation has not yet confirmed whether prior-exit reason materialization moves REENTRY rows into positive accepted capital.
- It remains unresolved how much Cash persists after REENTRY rows are either requalified or validly rejected with materialized context.
- Non-reentry NEW demand appears too small to consume high-Cash BULL capital; whether this is correct conservatism or calibration underdeployment remains open.
- Residual reconsideration is visible and material but non-authoritative; repair justification requires a narrower causal proof.
- ADD/NEW/Cash interaction is observed, but top-level ADD capital demand is mostly absent, so production priority changes are not justified.

## Final Judgments

```text
PHASE32_M_PRIMARY_CASH_CAUSE = REENTRY_CONTEXT_DEFECT-driven frontier collapse after portfolio prior-exit history accumulates; repaired in Phase32-L but not yet fresh-validated.
PHASE32_M_SECONDARY_CASH_CAUSES = PC_ACCEPTED_WEIGHT_ZERO_NON_REENTRY / NEW_ENTRY_QUALITY_LIMITATION, RESIDUAL_RECONSIDERATION_GAP / AUTHORITATIVE_SHADOW_GAP, MCC_CASH_PREFERENCE, PASSIVE_RESIDUAL_CASH, MARKET_QUALITY_CAUTION outside the Healthy/NORMAL focus cluster.

PHASE32_M_REENTRY_CONTRIBUTION = HIGH

PHASE32_M_CASH_PROBLEM_REMAINS_WITH_REENTRY_EXCLUDED = PARTIAL

PHASE32_M_NON_REENTRY_NEW_SUPPRESSION_MATERIAL = YES

PHASE32_M_RESIDUAL_AUTHORITY_GAP_MATERIAL = YES

PHASE32_M_ACTIVE_CASH_PREFERENCE_MATERIAL = YES

PHASE32_M_PASSIVE_RESIDUAL_CASH_MATERIAL = YES

PHASE32_M_ADD_NEW_CASH_INTERACTION_MATERIAL = PARTIAL

PHASE32_M_LATE_PLATEAU_STRUCTURAL_TRIGGER = portfolio-history accumulation converts a large share of the frontier into prior-exit-sensitive semantic REENTRY; Pre-L generic context then suppresses those rows while non-reentry NEW demand is too small to absorb available capital.

PHASE32_M_CONFIRMED_DEFECTS_REMAINING = none newly confirmed beyond the Phase32-L prior-exit context defect; residual/non-reentry/ADD-Cash items are material but not yet production-change defects.

PHASE32_M_SHOULD_INVESTIGATE_REPAIR = non-reentry NEW admission calibration, residual shadow-to-authoritative connection, Healthy/NORMAL MCC Cash preference semantics, ADD/NEW/Cash lineage.

PHASE32_M_DO_NOT_CHANGE = SELL/early-exit policy, risk pacing, concentration safety, lot feasibility, ADD/NEW priority, Cash thresholds before post-L evidence.

PHASE32_M_FRESH_VALIDATION_TIMING = NARROW_VALIDATION_ONLY

PHASE32_M_PRODUCTION_CHANGE_JUSTIFIED = PARTIAL

PHASE32_M_NEXT_STEP = run a narrow post-L validation on the January high-Cash BULL sequence plus representative low-Cash BULL controls, then compare REENTRY admission, accepted NEW/ADD, residual shadow, PS/runtime/fills, and remaining Cash before considering any additional repair.
```
