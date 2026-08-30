# Phase32-T — Evidence-Tiered ADD Acceleration Actual-Path Short Audit

## Scope

Target run:

`runtime-test-historical-extended-smoke-20260830T045550298045Z`

Comparison run:

`runtime-test-historical-extended-smoke-20260830T040609131559Z`

This was a READ-ONLY audit of existing run artifacts. No source, config,
Strategy parameter, threshold, weight, Risk Pacing, Cash, PM, PS, Runtime, or
G129 behavior was changed. No fresh-run, resume, replay, or long Historical was
executed by Codex.

Audit snapshot:

- target run status: `RUNNING`
- completed business days audited: 15
- audited dates: 2022-10-03, 2022-10-04, 2022-10-05, 2022-10-06,
  2022-10-07, 2022-10-11, 2022-10-12, 2022-10-13, 2022-10-14,
  2022-10-17, 2022-10-18, 2022-10-19, 2022-10-20, 2022-10-21,
  2022-10-24
- 2022-10-25 was visible but not complete at audit time and was excluded.

Current source baseline recorded by target run:

- source commit: `4ff63ba05a0012c60fce50741a946eed672f8990`
- source dirty: `True`
- accepted artifact hash: `d2352977bf6feaea22e7c4e5d00980d775eefe1622126fbbde4bd22d3ee6e0e0`
- registry hash: `ac108fcfadb01f613263fa2ea00ba37fc7a0ded0ad224387d18222bfb73c3ec2`

Comparison run source baseline:

- source commit: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- source dirty: `True`

## Tier Distribution

Across all PM ADD-shaped PC rows in audited completed days:

| Tier | Count |
| --- | ---: |
| `NO_ACCELERATION` | 7 |
| `NORMAL_ADD` | 5 |
| `STRONG_ADD` | 0 |
| `EXCEPTIONAL_ADD` | 0 |

Phase32-S fields first materialized on the actual production path on
2022-10-05 for `94340`:

- `add_acceleration_tier=NO_ACCELERATION`
- `add_acceleration_status=FAIL_CLOSED`

This confirms Phase32-S is active on the actual production PC path.

## ADD Funnel

| Stage | Count |
| --- | ---: |
| PM ADD rows | 12 |
| PC positive ADD increment rows | 5 |
| PS positive ADD quantity rows | 4 |
| Runtime `BUY_ADD` plans | 4 |
| Runtime positive `BUY_ADD` plans | 4 |
| `BUY_ADD` fills | 3 |

All positive PS / Runtime / fill ADD quantities were 100 shares. No actual
multi-lot `BUY_ADD` was observed in the audited completed window.

## NORMAL_ADD Rows

All `NORMAL_ADD` rows were normal because Risk Pacing down-tiered acceleration:

| Date | Symbol | BQ | Expected Edge | Incremental Value | Opp Cost | Risk Pacing | Pre Increment | Tier Increment | PS Qty |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 2022-10-06 | 94340 | `FULL_ALLOCATION_ELIGIBLE` | `IMPROVING` | `POSITIVE` | `PASS` | `DOWN_TIER` | 0.035714 | 0.035714 | 100 |
| 2022-10-11 | 94340 | `FULL_ALLOCATION_ELIGIBLE` | `IMPROVING` | `POSITIVE` | `PASS` | `DOWN_TIER` | 0.029600 | 0.029600 | 100 |
| 2022-10-12 | 94340 | `FULL_ALLOCATION_ELIGIBLE` | `IMPROVING` | `POSITIVE` | `PASS` | `DOWN_TIER` | 0.021765 | 0.021765 | 100 |
| 2022-10-13 | 94340 | `REDUCED_ALLOCATION_ONLY` | `IMPROVING` | `POSITIVE` | `PASS` | `DOWN_TIER` | 0.026429 | 0.026429 | 100 |
| 2022-10-21 | 94320 | `REDUCED_ALLOCATION_ONLY` | `IMPROVING` | `POSITIVE` | `PASS` | `DOWN_TIER` | 0.030667 | 0.030667 | 0 |

Representative reason codes:

- `ADD_ACCELERATION_NORMAL_ADD_BASELINE_PRESERVED`
- `ADD_ACCELERATION_RISK_PACING_DOWN_TIER`
- `ADD_ACCELERATION_REDUCED_BUY_QUALITY_NORMAL_ONLY` where Buy Quality was
  reduced.

No `NORMAL_ADD` row had `tier_bounded_incremental_weight` greater than
`pre_acceleration_incremental_weight`.

## NO_ACCELERATION Rows

The seven `NO_ACCELERATION` rows were explained by current PIT evidence, not by
a missing Phase32-S consumer path:

| Date | Symbol | Main Cause |
| --- | --- | --- |
| 2022-10-05 | 94340 | expected edge weakening, incremental value UNKNOWN, opportunity cost fail |
| 2022-10-07 | 94320 | expected edge weakening, incremental value UNKNOWN |
| 2022-10-07 | 94340 | expected edge weakening, incremental value UNKNOWN |
| 2022-10-12 | 94320 | Buy Quality `BUY_WAIT`, explicit zero quality allocation |
| 2022-10-19 | 94320 | expected edge weakening, incremental value UNKNOWN |
| 2022-10-20 | 94320 | expected edge weakening, incremental value UNKNOWN |
| 2022-10-24 | 94320 | expected edge weakening, incremental value UNKNOWN |

Campaign provenance, current-position authority, broker eligibility, corporate
action, liquidity, no-loss averaging, and Safety were PASS in these rows except
where the row intentionally stopped before downstream opportunity-cost
evaluation due to Buy Quality.

## STRONG / EXCEPTIONAL Evidence Rows

No `STRONG_ADD` or `EXCEPTIONAL_ADD` rows occurred.

The closest rows had PM reasons including:

- `strong_trend_continuation`
- `opportunity_rank_still_high`
- `no_loss_averaging`

However, Phase32-S requires PC guardrails to pass and Risk Pacing compatibility
for acceleration above normal. In every positive ADD case, Risk Pacing was
`DOWN_TIER`, so acceleration remained `NORMAL_ADD`.

## Capital Magnitude Materialization

No Phase32-S uplift above the pre-S baseline continuous increment was observed.

Observed relation:

```text
tier_bounded_incremental_weight == pre_acceleration_incremental_weight
```

for all positive `NORMAL_ADD` rows.

Observed PS outputs:

- 2022-10-06 `94340`: 100 shares
- 2022-10-11 `94340`: 100 shares
- 2022-10-12 `94340`: 100 shares
- 2022-10-13 `94340`: 100 shares

Observed Runtime positive `BUY_ADD` plans matched PS:

- 2022-10-06 `94340`: 100 shares
- 2022-10-11 `94340`: 100 shares
- 2022-10-12 `94340`: 100 shares
- 2022-10-13 `94340`: 100 shares

Observed `BUY_ADD` fills:

- 2022-10-06 `94340`: 100 shares
- 2022-10-12 `94340`: 100 shares
- 2022-10-13 `94340`: 100 shares

The 2022-10-11 Runtime plan existed but no same-day fill was observed in the
audited fill artifact.

## First Divergence From Pre-S Baseline

Compared through common completed decision-time artifacts:

| Surface | First Divergence |
| --- | --- |
| PC surface fields excluding Phase32-S observability | none |
| PS quantities | none |
| Runtime plans | none |
| fills | none |
| executable actions / quantities | none |

The first internal Phase32-S difference is observability-only:

- 2022-10-05 `94340`
- `add_acceleration_tier=NO_ACCELERATION`

No behavioral divergence reached target weights, PS quantity, Runtime order, or
fills in the audited completed window.

## Why Holdings Are Still Identical

Classification:

`NO_STRONG_OR_EXCEPTIONAL_EVIDENCE_YET`

More specifically:

- Phase32-S is active.
- `NORMAL_ADD` rows exist.
- `STRONG_ADD` / `EXCEPTIONAL_ADD` rows do not exist.
- No PC uplift above the pre-S baseline increment exists.
- PS therefore receives the same effective discrete ADD opportunity as before.
- Runtime consumes PS-bound quantities without redecision.
- Fills remain identical to the comparison run through the audited common
  completed days.

## Multi-Lot Capability

Actual artifact result:

- maximum observed PS `BUY_ADD` quantity delta: 100 shares
- observed `PS final_quantity_delta >= 200`: no

Capability judgment:

- architecture/source capability exists
- actual evidence did not reach it yet
- no actual-path hidden one-lot cap was reproduced in this audit

Basis:

- Phase32-S source keeps PC as continuous capital authority.
- PS remains discrete quantity authority and consumes
  `pc_positive_executable_quantity_authority.final_allocated_quantity`.
- Phase32-S focused validation already proved a larger PC discrete authority can
  materialize as 300-share BUY_ADD without Runtime redecision.
- Current actual evidence did not produce a `STRONG_ADD` or `EXCEPTIONAL_ADD`
  uplift requiring multi-lot PS materialization.

## UNKNOWN / Fail-Closed Behavior

Observed `incremental_investment_value_state=UNKNOWN` rows: 6.

All stayed non-accelerating:

- `add_acceleration_tier=NO_ACCELERATION`
- `add_acceleration_status=FAIL_CLOSED`
- `ADD_ACCELERATION_INCREMENTAL_VALUE_FAIL_CLOSED`

No UNKNOWN row was silently promoted to `STRONG_ADD` or `EXCEPTIONAL_ADD`.

Observed Buy Quality zero case:

- 2022-10-12 `94320`
- `quality_action=BUY_WAIT`
- `quality_allocation_adjustment=0.0`
- `tier_bounded_incremental_weight=0.0`
- `accepted_incremental_weight=0.0`
- `lot_aware_accepted_incremental_weight=0.0`

This confirms BUY_WAIT / explicit zero remains zero in the actual path.

## NEW / Cash Competition

No `STRONG_ADD` row occurred, so there was no actual case requiring
strong-ADD-vs-NEW or strong-ADD-vs-Cash adjudication.

Current evidence does not support classifying NEW/Cash competition as the main
acceleration brake. The brake is earlier: no strong/exceptional acceleration
tier was selected.

## Risk / Safety Preservation

Observed ADD guardrail statuses:

- Risk Pacing: `DOWN_TIER` for all 12 PM ADD rows.
- Safety: `PASS` for all 12 PM ADD rows.
- broker: `PASS` for all 12 PM ADD rows.
- corporate action: `PASS` for all 12 PM ADD rows.
- liquidity: `PASS` for all 12 PM ADD rows.
- campaign provenance: `PASS` for all 12 PM ADD rows.
- current-position authority: `PASS` for all 12 PM ADD rows.
- headroom: `PASS` for all 12 PM ADD rows.

No single-name cap or concentration-headroom violation was observed. Runtime
did not redecide quantity; Runtime positive `BUY_ADD` plans matched PS
100-share output.

## Defect Assessment

Defect found: NO.

Repair required: NO.

The current absence of surface trading behavior change is explained by actual
PIT evidence:

- no `STRONG_ADD`
- no `EXCEPTIONAL_ADD`
- all otherwise positive ADD cases down-tiered to `NORMAL_ADD` by Risk Pacing
- no PC uplift above the pre-S baseline
- no multi-lot PS opportunity reached

## Continue Current Run

Continue current run required: YES, if the goal is to observe an actual
`STRONG_ADD` / `EXCEPTIONAL_ADD` lifecycle and multi-lot materialization.

Do not start a new fresh-run solely for Phase32-T. The current user-operated
run should simply continue until a valid strong/exceptional ADD event appears,
unless it halts for an unrelated reason.

## NO CODE CHANGE

Confirmed. No source or config repair was performed in Phase32-T.

## NO Future-Information Use

Confirmed. This audit used current run artifacts, comparison run artifacts,
current source/report context, and Architecture/SoT only. It did not use future
price, future return, future regime, later sell result, campaign final outcome,
Historical profitability, or hindsight.

## Final Classification

`PHASE32_S_ACTIVE_BUT_NO_STRONG_EVIDENCE_YET`

## Final Judgment

1. `IS_PHASE32_S_ACTIVE_ON_THE_ACTUAL_PRODUCTION_PATH`: YES.
2. `HAVE_STRONG_ADD_OR_EXCEPTIONAL_ADD_TIERS_OCCURRED`: NO.
3. `HAS_PC_ACTUALLY_AUTHORIZED_MORE_CAPITAL_THAN_THE_PRE_S_BASELINE`: NO.
4. `HAS_PS_MATERIALIZED_MULTI_LOT_BUY_ADD`: NO.
5. `WHY_ARE_SURFACE_TRADING_RESULTS_STILL_IDENTICAL`: Phase32-S is active, but
   only `NO_ACCELERATION` and `NORMAL_ADD` occurred; all positive ADD rows were
   Risk-Pacing-down-tiered normal ADD with no uplift over baseline, so PS,
   Runtime, and fills remained identical.
6. `IS_ANY_REPAIR_REQUIRED`: NO.
7. `SHOULD_THE_CURRENT_RUN_CONTINUE_UNTIL_A_STRONG_ADD_EVENT_APPEARS`: YES.
