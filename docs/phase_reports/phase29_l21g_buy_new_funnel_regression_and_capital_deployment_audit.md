# Phase29-L21G - BUY_NEW Funnel Regression and Capital Deployment Audit

## Primary Judgment

`PHASE29_L21G_BUY_NEW_FUNNEL_THIN_PRE_EXISTING_CAPITAL_DEPLOYMENT_GAP_CONFIRMED`

BUY_NEW regression is not confirmed. The target run did open only one new position campaign, but the same initial 2022-08-10 to 2022-08-19 funnel shape is present in the L21A comparison run. The primary bottleneck is upstream BUY_NEW supply quality: every audited business date had 50 candidate rows, but only one Buy Quality PASS, and that PASS was the same symbol, `94320`, on all seven strategy dates. After `94320` was opened on 2022-08-10, subsequent PASS rows were existing-position ADD/HOLD candidates, not new positions.

## Target Run

- Target run: `reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T130548490709Z`
- Completed business days: `2022-08-10`, `2022-08-12`, `2022-08-15`, `2022-08-16`, `2022-08-17`, `2022-08-18`
- Halt strategy date included in funnel: `2022-08-19`
- Halt-date limitation: 2022-08-19 has strategy artifacts, but no submit/execution/day-completion artifacts.

## Observed New Positions

Only one new campaign opened:

| Date | Symbol | Quantity | Buy notional | Campaign |
|---|---:|---:|---:|---|
| 2022-08-10 | `94320` | 900 | 134,280 | `pc-c452f23b1594cb9c-94320-0001` |

## Completed Business Days

Six days completed. The seventh inspected date, 2022-08-19, halted after strategy generation and is included only through Runtime Planning.

## Aggregate BUY_NEW Funnel

| Stage | Count | Conversion from prior stage | Top drop reason |
|---|---:|---:|---|
| Candidate universe | 350 | - | 50 candidates on each of 7 dates |
| Candidate Top-N / Buy Quality evaluated | 350 | 100.0% | Full daily Top-N evaluated |
| Buy Quality PASS | 7 | 2.0% | 343 rejects, mostly `non_positive_or_missing_raw_opportunity_score` with `UNUSABLE` band |
| PC positive BUY_NEW | 1 | 14.3% | The six later PASS rows were the already-held `94320`; rejected candidates were `buy_quality_rejected` |
| PS positive BUY_NEW quantity | 1 | 100.0% | No BUY_NEW sizing defect after PC positive target |
| Runtime BUY_NEW | 1 | 100.0% | Positive PS quantity mapped correctly to `BUY_NEW` |
| Submit BUY | 1 | 100.0% | No submit block for the one BUY_NEW |
| Fill BUY | 1 | 100.0% | Historical fill succeeded |
| New Position Campaign | 1 | 100.0% | Campaign opened correctly |

Aggregate Buy Quality actions:

| Action | Count |
|---|---:|
| `REDUCED_ALLOCATION_ONLY` | 7 |
| `REJECT` | 343 |

Aggregate Buy Quality bands:

| Band | Count |
|---|---:|
| `HIGH` | 6 |
| `MEDIUM` | 1 |
| `UNUSABLE` | 343 |

## Daily BUY_NEW Funnel

| Date | Market | Breadth | Vol | Target Cash / Exposure | Capacity | Candidate | BQ PASS | PC BUY_NEW positive | PS positive | Runtime BUY_NEW | Submit BUY | Fill BUY | New Campaign | Primary Drop Reason |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2022-08-10 | BULL | STRONG | NORMAL | 0.0 / 1.0 | 50 | 50 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | Passed to campaign |
| 2022-08-12 | BULL | STRONG | NORMAL | 0.0 / 1.0 | 50 | 50 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | BQ PASS was existing `94320`; no new PC positive target |
| 2022-08-15 | BULL | STRONG | NORMAL | 0.0 / 1.0 | 50 | 50 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | BQ PASS was existing `94320`; no new PC positive target |
| 2022-08-16 | BULL | STRONG | NORMAL | 0.0 / 1.0 | 50 | 50 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | BQ PASS was existing `94320`; no new PC positive target |
| 2022-08-17 | BULL | STRONG | NORMAL | 0.0 / 1.0 | 50 | 50 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | BQ PASS was existing `94320`; no new PC positive target |
| 2022-08-18 | BULL | STRONG | NORMAL | 0.0 / 1.0 | 50 | 50 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | BQ PASS was existing `94320`; no new PC positive target |
| 2022-08-19 | BULL | NEUTRAL | NORMAL | 0.0 / 1.0 | 50 | 50 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | Halt-date strategy only; BQ PASS was existing `94320` BUY_ADD |

Daily PM / Runtime notes:

| Date | PM actions | Runtime intents | Notes |
|---|---|---|---|
| 2022-08-10 | New candidate path from PC/PS | `BUY_NEW: 1` | `position_sizing_positive_quantity_delta_maps_to_buy_new` |
| 2022-08-12 | `ADD: 1` | `NO_ACTION: 1` | `current_position_zero_delta_maps_to_no_action` |
| 2022-08-15 | `ADD: 1` | `NO_ACTION: 1` | `current_position_zero_delta_maps_to_no_action` |
| 2022-08-16 | `ADD: 1` | `NO_ACTION: 1` | `current_position_zero_delta_maps_to_no_action` |
| 2022-08-17 | `ADD: 1` | `NO_ACTION: 1` | `current_position_zero_delta_maps_to_no_action` |
| 2022-08-18 | `ADD: 1` | `NO_ACTION: 1` | `current_position_zero_delta_maps_to_no_action` |
| 2022-08-19 | `ADD: 1` | `BUY_ADD: 1` | Halt root from L21E/L21F path: `target_weight_above_position_cap:0`, not BUY_NEW |

## Primary Bottleneck

`BUY_QUALITY_PRIMARY_BOTTLENECK`

The decisive drop is Candidate Top-N to Buy Quality PASS: 350 evaluated rows became 7 PASS rows, a 2.0% pass rate. More importantly, the seven PASS rows were not seven distinct deployable new entries; they were the same rank-1 symbol, `94320`, repeated across the inspected dates. The other 343 rows were rejected, usually with `UNUSABLE` quality band and reason patterns including `non_positive_or_missing_raw_opportunity_score`.

## Secondary Bottleneck

`CAPITAL_AVAILABLE_BUT_ENTRY_FUNNEL_THIN`

After the first fill, the run still had roughly 865,720 cash and about 13% gross exposure on the inspected days, while policy target exposure remained 1.0. Cash was therefore available, but the entry funnel did not produce additional distinct BUY_NEW candidates that survived Buy Quality and PC as positive new targets.

## Market Context Suppression

`MARKET_CONTEXT_RATIONALLY_SUPPRESSED_NEW_BUY = NO`

The inspected dates were BULL/NORMAL throughout, with STRONG breadth except 2022-08-19 NEUTRAL breadth. Market context contributed quality modifiers, but it did not rationally explain zero new deployment after day one.

## Portfolio Policy Suppression

`PORTFOLIO_POLICY_ZERO_CAPACITY = NO`

Every inspected date had target cash `0.0`, target exposure `1.0`, and resolved opportunity capacity `50`. Policy did not set target position count or capacity to zero. This matches L21A's prior finding that policy generally allowed deployment and left downstream quality/lot/concentration/quantity stages to decide executable capital use.

## Capital Available But Entry Funnel Thin

Confirmed. Cash remained high after day one:

| Date | Cash | Gross exposure | Current positions |
|---|---:|---:|---:|
| 2022-08-10 | 1,000,000 | 0 | 0 |
| 2022-08-12 | 865,720 | 134,820 | 1 |
| 2022-08-15 | 865,720 | 133,110 | 1 |
| 2022-08-16 | 865,720 | 133,830 | 1 |
| 2022-08-17 | 865,720 | 132,660 | 1 |
| 2022-08-18 | 865,720 | 134,280 | 1 |
| 2022-08-19 | 865,720 | 134,550 | 1 |

The unused cash is primarily explained by thin quality-approved entry supply, not by a downstream refusal to submit/fill valid BUY_NEW orders.

## Buy Quality Bottleneck

Confirmed. Buy Quality is the primary bottleneck:

- 350 decisions evaluated.
- 7 PASS / reduced allocation rows.
- 343 rejects.
- The rejected set is dominated by `UNUSABLE` quality band.
- The recurring reject reason set includes `non_positive_or_missing_raw_opportunity_score`, `calibration_not_applied_raw_score_not_expected_return`, `execution_feasibility_available`, `market_context_symbol_quality_modifier_no_exposure_duplication`, and `portfolio_fit_not_position_count_gate`.
- No evidence shows corporate-action quarantine, liquidity block, or minimum notional as the primary BUY_NEW suppressor in this target window.

This is a quality/pass-through scarcity finding, not a recommendation to relax thresholds in this task.

## Portfolio Construction Bottleneck

PC is not the primary defect. On 2022-08-10, the one quality-approved new symbol received positive BUY_NEW target weight and became executable. On later days, the only PASS row was already-held `94320`; the rejected candidate rows appeared in PC as excluded with `buy_quality_rejected`. Therefore PC is mostly propagating upstream quality and current-position state rather than independently over-filtering distinct new candidates.

BUY_NEW lot/cap evidence for the one positive PC row passed:

- `lot_first_feasibility_classification = EXECUTABLE_NOW`
- `strategy_cap_preserved = true`
- `safety_hard_cap_preserved = true`
- `target_weight = 0.18`
- `lot_aware_accepted_buy_new_weight = 0.18`

## Position Sizing Bottleneck

No BUY_NEW Position Sizing defect is found. The single PC-positive BUY_NEW row produced `quantity_delta_candidate = 900` and reached Runtime Planning as `BUY_NEW`. Later dates had no positive BUY_NEW PC target for PS to size. The 2022-08-19 PS block is the known BUY_ADD cap integration case from L21E/L21F, not a BUY_NEW failure.

## Runtime Planning Defect

No BUY_NEW Runtime Planning mapping defect is found. The only positive BUY_NEW sizing row mapped to:

```text
planning_intent = BUY_NEW
planned_quantity = 900
reason = position_sizing_positive_quantity_delta_maps_to_buy_new
```

The later `NO_ACTION` rows are existing-position zero-delta mappings, not lost BUY_NEW rows.

## Submit/Fill Bottleneck

No Submit/Fill bottleneck is found for BUY_NEW. The only Runtime `BUY_NEW` submitted once, filled once, and opened one position campaign. The 2022-08-19 halt date has no submit/execution artifacts, so it cannot be used as evidence of a BUY_NEW submit/fill failure.

## BUY_NEW Regression Confirmed

NO.

Few BUY_NEW events are observed, but regression is not proven. The L21A comparison run, `runtime-test-historical-smoke-20260811T113809030985Z`, has the same first-seven-date pass symbols and early funnel behavior:

| Run | Days inspected | BQ PASS/day | PC positive BUY_NEW/day | PS positive BUY_NEW/day | Runtime BUY_NEW/day | Fill BUY/day | Average position count |
|---|---:|---:|---:|---:|---:|---:|---:|
| `runtime-test-historical-smoke-20260811T113809030985Z` | 51 | 2.784 | 0.922 | 0.471 | 0.471 | 0.216 | 2.647 |
| `runtime-test-historical-smoke-20260811T130548490709Z` | 7 | 1.000 | 0.143 | 0.143 | 0.143 | 0.143 | 0.857 |

For the overlapping dates 2022-08-10 through 2022-08-19, both runs show exactly one daily BQ PASS, always `94320`, and only the first day creates a BUY_NEW. The longer comparison run later finds more entries, which supports thin early opportunity supply rather than a current-run-only regression.

The preferred historical candidates `runtime-test-historical-smoke-20260809T141932598150Z` and `runtime-test-historical-smoke-20260809T065457596902Z` were not present in the workspace. The L21A run is comparable as an existing historical-smoke performance run, but it is not a perfect same-implementation before/after proof.

## Regression Introduced in Phase29

NO evidence found.

L21A already classified high retained cash as primarily BUY Quality / opportunity supply scarcity, with policy allowing deployment. L21B found BUY_NEW rows were genuine new candidates and that Runtime mapping for positive quantities was functioning. The target run reproduces the same early sparse BUY_NEW behavior.

## Regression Introduced by L21D/L21F

NO evidence found.

L21D and L21F were scoped to existing `BUY_ADD` lot-aware Strategy soft-cap overshoot. Their own reports state:

- `BUY_NEW Semantics Changed = NO`
- `Runtime Planning Special Case Added = NO`

The local diff evidence also shows the new authorization predicates gated on `semantic_buy_type == "BUY_ADD"` / `participant_type == "BUY_ADD"`. The target run's BUY_NEW path that exists on 2022-08-10 still maps, submits, fills, and opens a campaign.

## Pre-existing Issue

YES.

This is consistent with the pre-existing capital deployment / entry selectivity issue identified in L21A: high cash is not mainly caused by Portfolio Policy zeroing or Runtime submit/fill loss, but by thin economically acceptable BUY supply and later concentration/ADD conversion constraints.

## Comparison Run(s)

Used:

- `runtime-test-historical-smoke-20260811T113809030985Z`

Not available in workspace:

- `runtime-test-historical-smoke-20260809T141932598150Z`
- `runtime-test-historical-smoke-20260809T065457596902Z`

Comparison status:

- The L21A run is a useful historical-smoke baseline and completed a much longer window.
- It is not a clean regression proof baseline because implementation generation differs.
- Its overlapping 2022-08-10 to 2022-08-19 behavior matches the current target run, which argues against a Phase29/L21F-introduced BUY_NEW regression.

## Git/History Findings

Read-only git/history inspection found no direct evidence that L21D/L21F narrowed BUY_NEW:

- Strategy/PS local diff for the recent repair is gated around BUY_ADD Strategy-cap overshoot authorization.
- L21D report states BUY_NEW remains unchanged.
- L21F report states BUY_NEW semantics did not change and Runtime Planning special cases were not added.
- L21A already documented sparse BUY_NEW and high cash before the L21F target run.

Recent history touching strategy/capital areas includes Phase22, Phase23, Phase24, Phase26, Phase27, Phase28, and Phase29 commits, but the available evidence does not identify a specific Phase28/29 commit that regressed BUY_NEW eligibility.

## Required Classification

| Classification | Judgment |
|---|---|
| A. BUY Quality primary bottleneck | YES, primary |
| B. Candidate scarcity | PARTIAL; raw candidates exist, quality-approved distinct new candidates are scarce |
| C. Market Context suppression | NO |
| D. Portfolio Policy suppression | NO |
| E. Portfolio Construction over-filtering | NO as primary; mostly propagates BQ/current-position state |
| F. Lot/minimum-notional bottleneck | NO for BUY_NEW in target window |
| G. Position Sizing quantity zeroing | NO for BUY_NEW |
| H. Runtime Planning mapping defect | NO |
| I. Submit/Fill bottleneck | NO |
| J. Regression from Phase28/29 changes | NOT CONFIRMED |
| K. Pre-existing performance architecture issue | YES |
| L. Multi-causal | PARTIAL; primary BQ scarcity, secondary current-position/concentration/ADD lifecycle after first buy |

## Recommended Repair Scope

No code/config repair is authorized by L21G. Recommended next scope is diagnostic only unless a later task authorizes changes:

- Add a BUY_NEW funnel observability report that distinguishes raw candidates, buy-eligible opportunities, distinct BQ PASS symbols, existing-position PASS rows, PC-positive distinct new candidates, and deployable PS quantities.
- Audit why 49 / 50 daily opportunity rows have non-positive or missing raw opportunity score during this early window.
- Audit whether repeated pass-through of already-held rank-1 `94320` should be separated from new-entry discovery metrics.
- Keep L21D/L21F BUY_ADD repair isolated from BUY_NEW unless direct evidence later shows BUY_NEW-specific lot/cap failure.

## New Component Required

YES, if the product goal is to improve capital deployment without weakening safety gates blindly. The missing component is not a fallback order generator; it is a durable BUY_NEW opportunity/funnel diagnostic layer that can attribute undeployed cash to distinct-entry scarcity, quality calibration, PC exclusion, lot/cap sizing, runtime mapping, or submit/fill.

## Current Run Mutated NO

YES. The halted run was not resumed, repaired, or mutated.

## Long Historical Executed NO

YES. No fresh historical, resume, 100BD, 4-year, pending lifecycle, or repair run was executed.

