# Phase32-CZ — Post-CW March Upside Capture / Capital Allocation Causal READ-ONLY Audit

## Scope

This is a READ-ONLY audit.

No Production source, config, Strategy threshold, score, sizing, model, runtime
state, Pending, Ledger, run artifact, resume, recover, replay, fresh-run, or
long Historical command was modified or executed.

Primary run:

```text
runtime-test-historical-extended-smoke-20260901T223409325599Z
```

Audit snapshot:

```text
run_status = RUNNING
source_commit = a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd
completed_business_days_used = 119
first_completed_date_used = 2022-10-03
LATEST_COMPLETED_DATE_USED = 2023-03-28
next_job_at_snapshot = 2023-03-29:market_refresh / later observed 2023-03-29:submit while run continued
```

The run was active during inspection. This report freezes the evidence set at
`2023-03-28` for March analysis.

## Old Evidence Boundary

The old pre-CW raw Historical artifacts have been deleted.

```text
OLD_RAW_ARTIFACT_AVAILABILITY = DELETED
OLD_RUN_CAUSAL_COMPARISON_ALLOWED = NO
OLD_RUN_DESCRIPTIVE_REFERENCE_ALLOWED = YES
OLD_RUN_REFERENCE_USAGE = DESCRIPTIVE_ONLY
```

Old Phase Reports are used only as descriptive context. No unavailable old PM,
PC, PS, Runtime, or Pending decision was reconstructed.

## References Read

- `docs/phase_reports/phase32_ch_post_april_plateau_root_cause_winner_capitalization_funnel_read_only_audit.md`
- `docs/phase_reports/phase32_ci_new_reentry_add_action_type_bias_post_april_opportunity_capture_root_cause_audit.md`
- `docs/phase_reports/phase32_cw_minimal_residual_reentry_unknown_context_production_repair.md`
- `docs/phase_reports/phase32_cx_reentry_suppression_accumulation_vs_long_horizon_growth_decay_read_only_audit.md`
- `docs/phase_reports/phase32_cy_winner_add_marginal_capital_competition_read_only_audit.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/runtime_architecture_v2.md`

## March Diagnostic Window

```text
MARCH_DIAGNOSTIC_WINDOW = 2023-03-01 through 2023-03-28
SPECIAL_ATTENTION_WINDOW = 2023-03-14 through 2023-03-24
```

The window uses completed current-run artifacts only.

## Post-CW March Equity Profile

Current-run valuation projection:

| Date | Equity | Cash | Market value | Position count |
|---|---:|---:|---:|---:|
| 2023-03-01 | 1,231,640 | 453,220 | 778,420 | 12 |
| 2023-03-14 | 1,216,370 | 576,840 | 639,530 | 7 |
| 2023-03-15 | 1,221,910 | 407,600 | 814,310 | 8 |
| 2023-03-17 | 1,217,650 | 285,530 | 932,120 | 11 |
| 2023-03-24 | 1,233,050 | 360,860 | 872,190 | 10 |
| 2023-03-28 | 1,339,600 | 256,760 | 1,082,840 | 9 |

Summary:

```text
March starting equity = 1,231,640
March high-water mark = 1,339,600 on 2023-03-28
latest March equity = 1,339,600
March return delta = +8.77%
daily PnL observations = 18
positive daily PnL count = 11
negative daily PnL count = 7
largest positive daily change = +79,890 on 2023-03-27
largest negative daily change = -21,470 on 2023-03-10
average daily change = +5,998
average exposure = 80.5%
average cash = 240,787
average position count = 11.5
```

`POST_CW_MARCH_EQUITY_PROFILE = POSITIVE_MONTH_WITH_WEAK_MID_MARCH_SLOPE_AND_LATE_MONTH_RECOVERY`

PnL is used here only as diagnostic output, not as a rule-selection input.

## March Current Opportunity Set

Current-run PC / BQ / capital-competition evidence:

| Measure | Count |
|---|---:|
| PC rows | 1,004 |
| BQ pass or reduced candidates | 794 |
| strong top-5 positive-score rows | 95 |
| capital competitors | 211 |
| NEW competitors | 191 |
| ADD competitors | 20 |
| REENTRY semantic rows | 337 |
| REENTRY_ELIGIBLE rows | 16 |
| average cash retained | 240,787 |

`MARCH_CURRENT_OPPORTUNITY_SET = BROAD_NEW_SET_WITH_SOME_REENTRY_ELIGIBLE_ROWS_AND_NARROW_ADD_SET`

`MARCH_STRONG_OPPORTUNITY_AVAILABLE = PARTIAL`

Reason:

- NEW opportunity supply was broad and repeatedly funded.
- REENTRY returned to semantic visibility after CW, including 16 eligible rows,
  but did not become executable/funded in March.
- ADD had strong-looking PIT rows by rank/score, but most were stopped by ADD
  eligibility or BQ before capital execution.
- The current evidence is not enough to say the March opportunity set was
  uniformly strong in an action-neutral marginal-capital sense.

## March Action Funnels

### NEW

```text
MARCH_NEW_FUNNEL =
NEW candidate rows 376
-> selected target rows 69
-> PS executable rows 70
-> Runtime BUY_NEW plans 70
-> BUY_NEW fills 25
-> BUY_NEW notional 1,877,920
```

### REENTRY

```text
MARCH_REENTRY_FUNNEL =
REENTRY semantic rows 337
-> REENTRY_ELIGIBLE rows 16
-> selected target rows 0 accepted as canonical funded REENTRY
-> PS executable REENTRY rows 0
-> Runtime REENTRY plans 0
-> REENTRY fills 0
```

REENTRY state distribution:

| State | Count |
|---|---:|
| REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE | 108 |
| REENTRY_INSUFFICIENT_EVIDENCE | 84 |
| REENTRY_NOT_ELIGIBLE_PRIOR_EXIT_CONTEXT | 71 |
| REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION | 58 |
| REENTRY_ELIGIBLE | 16 |

### ADD

```text
MARCH_ADD_FUNNEL =
PM/PC ADD rows 20
-> selected positive ADD target rows 1
-> PS positive ADD delta rows 1
-> Runtime BUY_ADD plans 1
-> BUY_ADD fills 1
-> BUY_ADD notional 15,840
```

The sole March BUY_ADD fill was `94320` on `2023-03-15`, 100 shares.

## March Position Capital Map

Representative held-position map:

| Date | Symbol | Campaign | Shares | Weight | PM | Score | Rank | BQ | ADD status |
|---|---|---|---:|---:|---|---:|---:|---|---|
| 2023-03-15 | 94320 | pc-56fe03f336dc0c03-94320-0001 | 600 | 7.75% | ADD | 0.3409 | 1 | REDUCED | PASS / BUY_ADD filled |
| 2023-03-15 | 54010 | pc-2af0ce1c2a7bbed4-54010-0001 | 200 | 10.10% | HOLD | 0.2076 | 8 | REDUCED | n/a |
| 2023-03-16 | 93180 | pc-762ddee5bae0f9e4-93180-0001 | 11900 | 2.92% | ADD | 0.2912 | 5 | FULL | FAIL_CLOSED |
| 2023-03-17 | 94320 | pc-56fe03f336dc0c03-94320-0001 | 700 | 9.18% | HOLD | 0.3828 | 1 | REDUCED | n/a |
| 2023-03-17 | 43880 | pc-dbcd41771c538cab-43880-0001 | 100 | 10.64% | ADD | 0.2571 | 5 | REDUCED | FAIL_CLOSED |
| 2023-03-24 | 43880 | pc-dbcd41771c538cab-43880-0001 | 100 | 10.38% | ADD | 0.1809 | 3 | FULL | FAIL_CLOSED |
| 2023-03-24 | 59350 | pc-ddcabe5da671fb71-59350-0001 | 100 | 16.35% | ADD | 0.1638 | 4 | REDUCED | FAIL_CLOSED |
| 2023-03-27 | 59350 | pc-ddcabe5da671fb71-59350-0001 | 100 | 16.53% | HOLD | 0.2413 | 3 | REDUCED | n/a |
| 2023-03-28 | 43880 | pc-dbcd41771c538cab-43880-0001 | 100 | 11.22% | ADD | 0.1943 | 4 | REDUCED | FAIL_CLOSED |

`MARCH_POSITION_CAPITAL_MAP = AVAILABLE_FROM_CURRENT_PC_PS_RUNTIME_ARTIFACTS`

This map is PIT evidence only. No position is called a Winner because of later
returns.

## March Position PnL Contribution

Approximate same-day diagnostic contribution was reconstructed from current-run
weights, daily equity, and same-day fills:

```text
current market value + same-day SELL proceeds - prior market value - same-day BUY notional
```

Largest positive March contributors:

| Symbol | Approx contribution |
|---|---:|
| 61440 | +161,000 |
| 43810 | +140,800 |
| 54010 | +122,355 |
| 30830 | +114,200 |
| 94320 | +98,291 |
| 94670 | +94,276 |
| 59350 | +84,756 |
| 83060 | +83,220 |
| 13840 | +82,300 |
| 93180 | +48,325 |

Largest negative contributors were small relative to positives:

| Symbol | Approx contribution |
|---|---:|
| 73590 | -11,450 |
| 77930 | -8,800 |
| 92520 | -7,080 |
| 65500 | -6,600 |
| 72710 | -3,300 |

`MARCH_POSITION_PNL_CONTRIBUTION = ABSENCE_OF_SUSTAINED_MID_MONTH_LARGE_POSITIVE_CONCENTRATION_MORE_THAN_SINGLE_OVERSIZED_LOSS`

This decomposition is diagnostic; it was not used to define Strategy repair.

## 9318 / 93180 Actual Path Trace

Actual current-run path:

| Boundary | Evidence |
|---|---|
| Candidate / PC before buy | 2023-03-01 through 2023-03-15 PC `ADD_CANDIDATE`, rank 1-3 most days, positive score |
| BQ on 2023-03-15 | `FULL_ALLOCATION_ELIGIBLE`, quality band `HIGH`, all major BQ components PASS, momentum trajectory `PASS_WITH_REDUCTION` |
| Listing / product | current listed, Standard market, product category `011`, security type `011` |
| Entry / PC | `CONTINUATION_WITH_CAUTION`, `BUY_NEW_REDUCED_ONLY`, target weight 2.9412% |
| Sizing / plan | reference price 3.0, BUY_NEW quantity 11,900 |
| Fill | 2023-03-15 BUY_NEW 11,900 shares, notional 23,800, campaign `pc-762ddee5bae0f9e4-93180-0001` |
| Next day ADD | 2023-03-16 PM ADD, rank 5, score 0.2912, BQ FULL, but `add_allocation_eligibility_status=FAIL_CLOSED`; Runtime NO_ACTION |
| Later hold | 2023-03-17 through 2023-03-27 HOLD, weight around 2.9% |
| Exit | 2023-03-28 PM EXIT / SELL_EXIT 11,900 shares |

`9318_ACTUAL_PATH_TRACE = BUY_NEW_REDUCED_ENTRY_THEN_NO_ADD_THEN_EXIT`

Search of current source/config/docs found no active symbol-specific blacklist
or special 93180 exclusion authority. Current actual artifacts show ordinary
listing, broker, BQ, corporate-event, PC, PS, and Runtime handling.

`9318_EXISTING_EXCLUSION_OR_SAFETY_AUTHORITY = NO_SUCH_CURRENT_AUTHORITY_FOUND`

`9318_CORRECTNESS_DEFECT = NO_CONFIRMED_CURRENT_SYMBOL_SPECIFIC_DEFECT`

Large share count came from very low reference price. The position weight was
only about 2.9%, so it did not dominate capital or concentration risk.

## March Capital Concentration Profile

Average March concentration:

| Measure | Value |
|---|---:|
| average top-1 weight | 15.04% |
| average top-3 weight | 36.86% |
| average top-5 weight | 53.92% |
| average position count | 11.84 |
| average position weight | 6.97% |
| median position weight | 6.93% |
| average 100-share starter count | 7.42 |
| average >100-share position count | 4.42 |
| 2023-03-28 starter / >100-share | 6 / 4 |

`MARCH_CAPITAL_CONCENTRATION_PROFILE = MODERATE_CONCENTRATION_WITH_MANY_100_SHARE_STARTERS`

The March book was not under-deployed on average. The question is allocation
quality and maturation of strong positions, not just cash deployment.

## Strong Continuation / ADD Set

PIT-only strong-continuation screen:

```text
current position
PM ADD
positive runtime_opportunity_score
input_opportunity_rank <= 5
BQ FULL or REDUCED
```

Rows found: `12`.

Representative rows:

| Date | Symbol | Weight | Score | Rank | BQ | ADD blocker |
|---|---|---:|---:|---:|---|---|
| 2023-03-06 | 94320 | 7.59% | 0.1524 | 4 | FULL | ADD_ELIGIBILITY |
| 2023-03-07 | 94320 | 7.53% | 0.1570 | 2 | FULL | ADD_ELIGIBILITY |
| 2023-03-15 | 94320 | 7.75% | 0.3409 | 1 | REDUCED | authorized / filled |
| 2023-03-16 | 93180 | 2.92% | 0.2912 | 5 | FULL | ADD_ELIGIBILITY |
| 2023-03-17 | 43880 | 10.64% | 0.2571 | 5 | REDUCED | ADD_ELIGIBILITY |
| 2023-03-24 | 59350 | 16.35% | 0.1638 | 4 | REDUCED | ADD_ELIGIBILITY |
| 2023-03-28 | 43880 | 11.22% | 0.1943 | 4 | REDUCED | ADD_ELIGIBILITY |

`MARCH_STRONG_CONTINUATION_POSITION_SET = 12_PIT_SCREEN_ROWS`

`MARCH_VALID_ADD_OPPORTUNITY_COUNT = 1_AUTHORIZED_AND_FILLED; 12_STRONG_SCREEN_ROWS_NOT_ALL_CANONICALLY_VALID_ADD`

The distinction matters: strong rank/score/BQ continuation is not the same as
canonical ADD authority.

## March ADD First Blocker Distribution

For March PM/PC ADD rows that did not become BUY_ADD:

| First blocker | Count |
|---|---:|
| ADD eligibility | 12 |
| BUY Quality | 7 |
| Trend / momentum deterioration | 0 first-boundary rows |
| Marginal competition loss | 0 |
| Cash preference | 0 first-boundary rows |
| Lot infeasibility | 0 |
| Cap | 0 |
| PS zero / target unchanged | 0 first-boundary rows |
| Runtime / execution | 0 |

`MARCH_ADD_FIRST_BLOCKER_DISTRIBUTION = ADD_ELIGIBILITY_12, BUY_QUALITY_7, AUTHORIZED_BUY_ADD_1`

Compared with CY full-window distribution, March is even more clearly upstream:
ADD did not mainly lose to NEW at the final capital frontier; it usually failed
before positive ADD authority was materialized.

## Strong ADD vs Starter Substitution

`MARCH_STRONG_ADD_TO_STARTER_SUBSTITUTION_COUNT = 0_CONFIRMED`

No March row met all of:

- strong PIT continuation;
- canonical valid ADD authority;
- BUY_NEW / REENTRY funded;
- ADD zero;
- no obvious constraint.

There were many cases where strong-looking PM ADD rows coexisted with NEW
funding, but they carried `ADD_ELIGIBILITY=FAIL_CLOSED` or BUY_WAIT, so they are
not accepted as unfair ADD-to-starter substitution.

## Marginal Capital Gap Materiality

`MARCH_MARGINAL_CAPITAL_GAP_MATERIALITY = SUPPORTED_BUT_NOT_PROVEN`

Supported:

- March shows broad NEW funding and narrow ADD execution.
- Strong-looking current positions often did not receive incremental capital.
- REENTRY semantic rows returned after CW but still did not reach funded capital.

Not proven:

- March ADD non-execution is explained by explicit upstream ADD eligibility/BQ
  blockers rather than final ADD-vs-NEW marginal competition.
- No valid ADD authority was shown losing to weaker funded starter in March.
- The diagnostic window ends before the post-April plateau window where CH/CI
  found stronger zero-ADD symptoms.

## March Action-Type Capitalization

Actual March fills:

| Action | Fills | Notional |
|---|---:|---:|
| BUY_NEW | 25 | 1,877,920 |
| BUY_ADD | 1 | 15,840 |
| REENTRY | 0 | 0 |
| SELL_EXIT | 30 | 1,726,650 |
| EXIT | 2 | 276,350 |
| REDUCE | 7 | 76,500 |

PC capital competition weight evidence:

| Type | Selected weight sum | Rejected/requested weight sum |
|---|---:|---:|
| NEW_BUY | 5.016162 | 3.987696 |
| ADD | 0.012981 | 0.000000 |

`MARCH_ACTION_TYPE_CAPITALIZATION = BUY_NEW_DOMINANT, BUY_ADD_PRESENT_BUT_SMALL, REENTRY_ZERO`

`MARCH_ACTION_TYPE_BIAS = ACTION_GATE_ASYMMETRY_PRESENT; SYSTEMATIC_UNFAIR_DIVERSION_NOT_CONFIRMED`

## Post-CW REENTRY Capital Effect

`MARCH_POST_CW_REENTRY_CAPITAL_EFFECT = SEMANTIC_VISIBILITY_IMPROVED_BUT_NOT_MATERIAL_CAPITAL_EFFECT_YET`

REENTRY rows are present and include 16 `REENTRY_ELIGIBLE` cases, but there were
no REENTRY plans or fills in the March frozen window. This means liberated
REENTRY is not yet visibly competing away ADD capital in actual March fills.

## Exposure vs Allocation Quality

`MARCH_EXPOSURE_SUFFICIENCY = YES_PARTIAL`

Average exposure was about 80.5%, and cash declined into the late-month rally.
The system did deploy capital; the March weakness around 2023-03-14 through
2023-03-24 is not a pure cash-underdeployment story.

`MARCH_ALLOCATION_QUALITY_ASSESSMENT = MIXED`

The portfolio had meaningful positive contributors, but the mid-March book was
fragmented and rotated heavily through NEW while ADD and REENTRY remained thin.
The evidence points to allocation-quality / maturation friction more than a
single obvious wrong position or safety bug.

## Starter Proliferation and Sizing Dilution

`MARCH_STARTER_PROLIFERATION_PROFILE = MANY_100_SHARE_STARTERS_WITH_FEW_ADD_GROWN_POSITIONS`

Observed:

- average 100-share starter count: 7.42;
- average >100-share position count: 4.42;
- only one March BUY_ADD fill;
- strong-continuation screen rows: 12;
- valid canonical ADD fill: 1.

`PORTFOLIO_GROWTH_POSITION_SIZING_DILUTION = PARTIAL`

As total equity grows, one 100-share lot can become a smaller portfolio weight
for normal-priced symbols, while low-priced symbols can still create very large
share counts without large weight. Current PS correctly owns discrete quantity,
but the architecture still lacks a high-resolution next-lot value authority
that preserves economic meaning separately from lot feasibility.

## Low-Price / Large-Share Interaction

`LOW_PRICE_LARGE_SHARE_CAPITAL_INTERACTION = NOT_MATERIAL_FOR_93180_CAPITAL_SUPPRESSION`

93180 used 11,900 shares because the reference price was 2-3 JPY. Its weight was
about 2.9%, and it did not consume a dominant share of portfolio capital. It did
occupy a position slot and was a very low-price/microstructure-risk example, but
current evidence shows ordinary BQ/PC/Safety handling rather than a bypassed
symbol-specific exclusion.

## March Upside Capture Root Cause

`MARCH_UPSIDE_CAPTURE_ROOT_CAUSE = COMBINATION_OF_MID_MONTH_PORTFOLIO_ROTATION_FRAGMENTATION, THIN_ADD_MATERIALIZATION, ZERO_REENTRY_CAPITAL_EFFECT, AND LOW_RESOLUTION_MARGINAL_CAPITAL_ARCHITECTURE`

Classification:

- market opportunity genuinely weaker for current portfolio: `PARTIAL`
- portfolio path divergence only: `DESCRIPTIVE_ONLY_NOT_CAUSAL_FROM_OLD_RAW`
- capital fragmentation: `YES`
- Winner undercapitalization: `SUPPORTED_BUT_NOT_PROVEN`
- marginal capital semantic gap: `SUPPORTED_BUT_NOT_PROVEN`
- REENTRY/ADD competition: `NOT_MATERIAL_IN_FILLS_YET`
- sizing dilution: `PARTIAL`
- security-quality/correctness issue: `NO_CONFIRMED_93180_SPECIFIC_DEFECT`

The central answer is: the current Post-CW system did not simply fail to deploy
cash, and it did not show a downstream BUY_ADD runtime break. March evidence
shows many current opportunities, but canonical ADD and REENTRY were not yet
material capital channels. That supports the known architecture concern, but
does not yet prove a current correctness repair.

## Production Repair Decision

`PRODUCTION_REPAIR_REQUIRED = CONDITIONAL`

No CZ repair is authorized. A future Production architecture task may be
justified if continued Post-CW evidence reaches the post-April window and shows
valid strong incumbent ADD or REENTRY opportunities being systematically
undercapitalized because the current low-resolution capital value authority
cannot compare them fairly against BUY_NEW/Cash.

Do not tune ADD count, concentration, caps, thresholds, score weights, or
blacklists from this March PnL evidence.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED`: `2023-03-28`
2. `OLD_RAW_ARTIFACT_AVAILABILITY`: `DELETED`
3. `OLD_RUN_CAUSAL_COMPARISON_ALLOWED`: `NO`
4. `OLD_RUN_DESCRIPTIVE_REFERENCE_ALLOWED`: `YES`
5. `MARCH_DIAGNOSTIC_WINDOW`: `2023-03-01 through 2023-03-28; special attention 2023-03-14 through 2023-03-24`
6. `POST_CW_MARCH_EQUITY_PROFILE`: `+8.77% month-to-date, weak mid-March slope, late-month recovery; average exposure 80.5%, average cash 240,787`
7. `MARCH_CURRENT_OPPORTUNITY_SET`: `broad NEW, 337 REENTRY semantic rows / 16 eligible, 20 ADD rows`
8. `MARCH_STRONG_OPPORTUNITY_AVAILABLE`: `PARTIAL`
9. `MARCH_NEW_FUNNEL`: `376 candidates -> 69 targets -> 70 PS/plans -> 25 fills`
10. `MARCH_REENTRY_FUNNEL`: `337 semantic rows -> 16 eligible -> 0 PS/plans/fills`
11. `MARCH_ADD_FUNNEL`: `20 ADD rows -> 1 authorized/PS/plan/fill`
12. `MARCH_POSITION_CAPITAL_MAP`: `available; representative map included`
13. `MARCH_POSITION_PNL_CONTRIBUTION`: `positive contribution broad but mid-month lacked sustained concentrated upside; no single oversized loss`
14. `9318_ACTUAL_PATH_TRACE`: `2023-03-15 BUY_NEW 11900 shares -> 2023-03-16 ADD intent fail-closed -> HOLD -> 2023-03-28 SELL_EXIT`
15. `9318_EXISTING_EXCLUSION_OR_SAFETY_AUTHORITY`: `NO_SUCH_CURRENT_AUTHORITY_FOUND`
16. `9318_CORRECTNESS_DEFECT`: `NO_CONFIRMED_CURRENT_SYMBOL_SPECIFIC_DEFECT`
17. `MARCH_CAPITAL_CONCENTRATION_PROFILE`: `top1 15.04%, top3 36.86%, top5 53.92%, many 100-share starters`
18. `MARCH_STRONG_CONTINUATION_POSITION_SET`: `12 PIT-screen rows`
19. `MARCH_VALID_ADD_OPPORTUNITY_COUNT`: `1 canonical authorized/fill; 12 strong screen rows`
20. `MARCH_ADD_FIRST_BLOCKER_DISTRIBUTION`: `ADD_ELIGIBILITY_12, BUY_QUALITY_7, AUTHORIZED_1`
21. `MARCH_STRONG_ADD_TO_STARTER_SUBSTITUTION_COUNT`: `0_CONFIRMED`
22. `MARCH_MARGINAL_CAPITAL_GAP_MATERIALITY`: `SUPPORTED_BUT_NOT_PROVEN`
23. `MARCH_ACTION_TYPE_CAPITALIZATION`: `BUY_NEW_25_1877920, BUY_ADD_1_15840, REENTRY_0`
24. `MARCH_ACTION_TYPE_BIAS`: `ACTION_GATE_ASYMMETRY_PRESENT; UNFAIR_DIVERSION_NOT_CONFIRMED`
25. `MARCH_POST_CW_REENTRY_CAPITAL_EFFECT`: `semantic visibility improved; material capital effect not yet observed`
26. `MARCH_EXPOSURE_SUFFICIENCY`: `YES_PARTIAL`
27. `MARCH_ALLOCATION_QUALITY_ASSESSMENT`: `MIXED`
28. `MARCH_STARTER_PROLIFERATION_PROFILE`: `average 7.42 100-share starters, 4.42 >100-share positions`
29. `PORTFOLIO_GROWTH_POSITION_SIZING_DILUTION`: `PARTIAL`
30. `LOW_PRICE_LARGE_SHARE_CAPITAL_INTERACTION`: `NOT_MATERIAL_FOR_93180_CAPITAL_SUPPRESSION`
31. `MARCH_UPSIDE_CAPTURE_ROOT_CAUSE`: `COMBINATION_OF_ROTATION_FRAGMENTATION_THIN_ADD_ZERO_REENTRY_CAPITAL_AND_LOW_RESOLUTION_MARGINAL_CAPITAL_ARCHITECTURE`
32. `PRODUCTION_REPAIR_REQUIRED`: `CONDITIONAL`
33. `OLD_RUN_REFERENCE_USAGE`: `DESCRIPTIVE_ONLY`
34. `FUTURE_OUTCOME_USED_TO_DEFINE_REPAIR`: `NO`
35. `PRODUCTION_CHANGE_EXECUTED`: `NO`
36. `TARGET_RUN_MUTATED`: `NO`
37. `NEXT_RECOMMENDED_STEP`: `continue user-operated Post-CW run into post-April window; re-audit ADD/REENTRY capital materialization before designing high-resolution marginal-capital Production work`
38. `FINAL_JUDGMENT`: `PHASE32_CZ_MARCH_UPSIDE_CAPTURE_WEAKNESS_CHARACTERIZED_CONDITIONAL_ARCHITECTURE_REPAIR_ONLY_MORE_POST_APRIL_EVIDENCE_REQUIRED`

## Final Judgment

```text
PHASE32_CZ_MARCH_UPSIDE_CAPTURE_WEAKNESS_CHARACTERIZED_CONDITIONAL_ARCHITECTURE_REPAIR_ONLY_MORE_POST_APRIL_EVIDENCE_REQUIRED
```

Given only the Post-CW system's own decision-time evidence, March weak upside
capture is best explained by a combination of capital rotation/fragmentation,
thin ADD materialization, zero realized REENTRY capital effect, and the known
low-resolution marginal-capital architecture. It is not explained by a confirmed
93180 symbol-specific safety bypass, a downstream BUY_ADD Runtime defect, or
cash underdeployment alone.

No Production change is executed or justified by CZ alone. The evidence supports
watching the same user-operated run into the post-April window, where the prior
CH/CI symptoms were materially stronger, before promoting a new high-resolution
marginal capital authority or related architecture repair.
