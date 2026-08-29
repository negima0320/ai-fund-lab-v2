# Phase32-BY - ADD Breadth / Funnel and Admission Boundary Audit

## Executive Summary

This was a READ-ONLY ADD breadth and funnel audit for run
`runtime-test-historical-extended-smoke-20260828T230436594098Z`.

The audit uses the same 55BD coverage snapshot as Phase32-BX:

```text
2022-10-03 through 2022-12-21
completed business days = 55
```

The run had advanced beyond this while the audit was performed, but this report
intentionally freezes the BX-aligned 55BD window. No production code, config,
threshold, model, runtime state, fresh-run, resume, replay, or backtest was
changed or executed.

The ADD breadth/scarcity result is clear:

- PM emitted ADD intent for only 4 symbols: `94320`, `94340`, `99840`, and
  `72730`.
- Frontier ADD candidates were also limited to the same 4 symbols.
- Accepted ADD targets narrowed to 3 symbols: `94320`, `94340`, and `72730`.
- Actual BUY_ADD fills also occurred in those same 3 symbols.
- The unique-symbol drop from 4 to 3 is explained by `99840` being cap-blocked.
- The lot-level drop from 102 ADD candidate lots to 31 accepted lots is
  overwhelmingly cap/headroom, not NEW/REENTRY/Cash competition.

The BX semantic gap is also confirmed at funnel scale: 21 of 31 accepted ADD
lots had `final_add_eligibility = FAIL_CLOSED`. That is the false-positive ADD
path. Evidence of a broad false-negative ADD path is weaker: no ADD lot lost
common competition to NEW/REENTRY/Cash, and the non-accepted eligible ADD
surface is mostly cap-blocked `99840`.

There is one additional boundary concern: `94320` on `2022-10-28` produced a
runtime BUY_ADD and actual 100-share ADD fill even though the marginal frontier
authority/BF boundary had no accepted ADD target for `94320`; the frontier ADD
lots were cap-blocked. This looks like a residual PS/runtime ADD route outside
the BF-only target authority and should be included in the repair scope.

## Run Identity

| Field | Value |
| --- | --- |
| Run | `runtime-test-historical-extended-smoke-20260828T230436594098Z` |
| Coverage used | `2022-10-03` through `2022-12-21` |
| Completed business days used | 55 |
| Current run status during audit | RUNNING beyond the frozen 55BD window |
| Primary ADD authority | `daily/<date>/strategy/marginal_capital_frontier_authority.json` |
| PM source | `daily/<date>/position_management/pm_decisions.json` |
| PS source | `daily/<date>/strategy/position_sizing.json` |
| Runtime source | `daily/<date>/strategy/runtime_planning.json` |
| Fill source | `daily/<date>/execution/fills.json` |

## Funnel Summary

The artifacts naturally use different units:

- PM intent is a day-symbol/campaign decision.
- Frontier candidates and accepted targets are per-lot rows.
- BF, PS, Runtime, and fills are symbol-day aggregated events.

| Stage | Total | Unique Symbols | Unique Campaigns | Notes |
| --- | ---: | ---: | ---: | --- |
| PM ADD intent | 41 day-symbol decisions | 4 | 4 | `94320`, `94340`, `99840`, `72730` |
| ADD evidence eligible | 36 candidate lots / 12 day-symbols | 3 | 3 | `94320`, `94340`, `99840` |
| Frontier ADD candidate | 102 candidate lots / 34 day-symbols | 4 | 4 | Same 4 PM ADD symbols |
| Feasible ADD candidate | 31 candidate lots / 11 day-symbols | 3 | 3 | Same rows as accepted lots |
| Common competition winner | 31 accepted lots / 11 day-symbols | 3 | 3 | No ADD `REJECTED_BY_STRONGER_MARGINAL_CAPITAL_VALUE` rows observed |
| BF aggregated ADD target | 11 symbol-day events | 3 | 3 | 31 accepted lots aggregated to +3,100 shares |
| PS positive ADD quantity | 11 symbol-day events | 3 | 3 | +2,900 shares; PS rounded/limited two 94320 days to +200 |
| Runtime BUY_ADD plan | 12 symbol-day events | 3 | 3 | Includes extra `94320` on 2022-10-28 without BF ADD target |
| Actual BUY_ADD fill | 8 fill events | 3 | 3 | +2,000 shares |

## PM ADD Intent Breadth

PM decisions across the 55BD window:

| PM decision type | Count |
| --- | ---: |
| HOLD | 333 |
| REDUCE | 89 |
| EXIT | 53 |
| ADD | 41 |

PM ADD intent was concentrated:

| Symbol | PM ADD intent days |
| --- | ---: |
| 94320 | 19 |
| 99840 | 19 |
| 94340 | 2 |
| 72730 | 1 |

The first breadth limiter is therefore PM itself: among 97 symbols with PM
decisions, only 4 ever reached PM ADD intent. The other 93 symbols stayed in
HOLD/REDUCE/EXIT states. Common non-ADD PM reasons were:

| Pattern | Count |
| --- | ---: |
| HOLD: `trend_continuation`, `downside_risk_contained` | 110 |
| HOLD: `trend_continuation` | 98 |
| REDUCE: `risk_increased_but_trend_not_broken` | 80 |
| EXIT: `trend_and_opportunity_broken` | 33 |
| HOLD: `hold_score_above_exit_threshold` | 33 |

This supports ADD scarcity at the PM intent layer. Most held positions were not
even asking for additional capital.

## Frontier Candidate Breadth

Every frontier ADD day-symbol had a PM ADD day-symbol; no frontier ADD symbol
appeared without PM ADD intent.

```text
PM ADD day-symbols = 41
frontier ADD day-symbols = 34
PM ADD day-symbols with frontier ADD = 34
frontier ADD day-symbols without PM ADD = 0
```

The 7 PM ADD day-symbols that did not become frontier ADD candidates were all
`94320` on `2022-10-31`, `2022-11-01`, `2022-11-02`, `2022-11-04`,
`2022-11-07`, `2022-11-08`, and `2022-11-09`. PC materialized these as
`membership_intent = RETAIN`, `semantic_type = NONE`, and current weight around
18.4% to 19.2%, already at or above the 18% effective cap. The observed drop is
therefore consistent with cap/headroom suppression, not missing campaign
identity or missing PM lineage.

ADD candidate lot distribution:

| Symbol | Frontier ADD lots |
| --- | ---: |
| 99840 | 57 |
| 94320 | 36 |
| 94340 | 6 |
| 72730 | 3 |

## Evidence Eligibility Drop-Off

ADD evidence eligibility was materially narrower than PM intent:

| Status | Candidate Lots |
| --- | ---: |
| `final_add_eligibility = PASS` | 36 |
| `final_add_eligibility = FAIL_CLOSED` | 66 |

Top FAIL_CLOSED reason patterns:

| Reason Pattern | Lots |
| --- | ---: |
| `ADD_EXPECTED_EDGE_WEAKENING`, `ADD_INCREMENTAL_VALUE_UNKNOWN` | 30 |
| `ADD_INCREMENTAL_VALUE_UNKNOWN`, `ADD_OPPORTUNITY_COST_FAIL` | 18 |
| `ADD_EXPECTED_EDGE_WEAKENING`, `ADD_INCREMENTAL_VALUE_UNKNOWN`, `ADD_OPPORTUNITY_COST_FAIL` | 15 |
| `ADD_EXPECTED_EDGE_UNKNOWN_FAIL_CLOSED`, `ADD_INCREMENTAL_VALUE_UNKNOWN`, `ADD_OPPORTUNITY_COST_FAIL` | 3 |

This is exactly the semantic boundary identified in Phase32-BX: the system
computes ADD-specific eligibility, but the downstream accepted target boundary
does not treat non-PASS ADD evidence as a hard blocker.

## Common Competition / Feasibility

ADD candidate disposition was binary in this window:

| Frontier ADD disposition | Lots | Unique Symbols |
| --- | ---: | ---: |
| `ACCEPTED_INCREMENTAL_TARGET` | 31 | 3 |
| `INFEASIBLE_CAP_BLOCKED` | 71 | 2 |

No ADD candidate was observed with
`REJECTED_BY_STRONGER_MARGINAL_CAPITAL_VALUE`. In this 55BD window, ADD did not
primarily lose to NEW/REENTRY/Cash in common competition. It either became an
accepted target or was blocked by cap/headroom.

Cap-blocked concentration:

| Symbol | Cap-blocked ADD lots | Interpretation |
| --- | ---: | --- |
| 99840 | 57 | Legitimate cap/headroom blocker; no accepted ADD lots or fills |
| 94320 | 14 | Late campaign already near/over 18% effective cap |

`99840` is the main false-negative risk surface: it had PM ADD intent and some
eligible ADD evidence, but all frontier ADD lots were cap-blocked. The artifacts
do not show an unjustified competition loss; they show concentration/headroom
blocking. That is a legitimate guardrail, although it should be rechecked after
the ADD admission repair because removing false-positive accepted ADD elsewhere
could change future budget/headroom surfaces in a new run.

## Accepted ADD Concentration

Accepted ADD lots:

| Symbol | Accepted ADD lots | BF events | Actual ADD fills |
| --- | ---: | ---: | ---: |
| 94320 | 22 | 8 | 5 |
| 94340 | 6 | 2 | 2 |
| 72730 | 3 | 1 | 1 |
| 99840 | 0 | 0 | 0 |

Accepted ADD eligibility status:

| Eligibility at accepted-lot boundary | Accepted Lots |
| --- | ---: |
| PASS | 10 |
| FAIL_CLOSED | 21 |

This is the strongest evidence of the false-positive path: most accepted ADD
lots were not backed by PASS ADD investment evidence.

## BF / PS / Runtime / Fill Boundary

BF aggregation converted 31 accepted lots into 11 symbol-day targets:

| Date | Symbol | BF lots | BF quantity delta | Fill outcome |
| --- | --- | ---: | ---: | --- |
| 2022-10-05 | 94340 | 3 | +300 | filled +300 |
| 2022-10-06 | 94340 | 3 | +300 | filled +300 |
| 2022-10-07 | 94320 | 3 | +300 | filled +300 |
| 2022-10-11 | 94320 | 3 | +300 | no ADD fill; submit feasibility review |
| 2022-10-12 | 94320 | 3 | +300 | filled +300 |
| 2022-10-17 | 94320 | 3 | +300 | PS +200; no ADD fill; quantity mismatch review |
| 2022-10-18 | 94320 | 3 | +300 | PS +200; no ADD fill; dynamic cash review |
| 2022-10-19 | 94320 | 3 | +300 | no ADD fill; dynamic cash review |
| 2022-10-20 | 94320 | 3 | +300 | filled +300 |
| 2022-10-21 | 94320 | 1 | +100 | filled +100 |
| 2022-12-12 | 72730 | 3 | +300 | filled +300 |

Runtime produced 12 BUY_ADD plans. The extra plan was `94320` on `2022-10-28`.
On that day:

- marginal frontier authority had only a NEW target for `76920`;
- `94320` ADD candidates were `INFEASIBLE_CAP_BLOCKED`;
- BF aggregated targets had no `94320` ADD target;
- `position_sizing.json` nevertheless had `canonical_sizing_evidence` with
  `ADD_POSITIVE_QUANTITY_DELTA`, `final_quantity_delta = 100`, and
  `bg_bf_aggregated_target = {}`;
- runtime planning generated BUY_ADD for `94320`;
- execution filled +100 shares of `94320`.

That is a separate boundary defect candidate: a residual PS/runtime ADD route
can still deploy ADD without BF accepted ADD authority.

## Relation To BX Gap

BX asked whether ADD semantics distinguish:

```text
still strong
vs.
fresh evidence justifies more capital now
```

BY confirms the gap is operationally material:

- False-positive ADD path: YES. 21 accepted lots had FAIL_CLOSED ADD evidence.
- False-negative ADD risk: PARTIAL. The only additional PM ADD symbol,
  `99840`, was cap-blocked rather than losing unfairly to NEW/REENTRY/Cash.
- Common-competition false negative: not observed. ADD did not lose through
  `REJECTED_BY_STRONGER_MARGINAL_CAPITAL_VALUE`.
- Candidate materialization false negative: not broadly observed. All frontier
  ADD symbols had PM ADD, and all non-frontier PM ADD rows were late `94320`
  rows already at/above cap.
- Boundary leak: observed on `2022-10-28`, where PS/runtime created a 94320
  ADD without BF ADD target.

The best characterization is therefore:

```text
The system is not broadly dropping valid ADD candidates in favor of NEW/Cash.
It is too concentrated at PM intent and cap/headroom, and it can accept or
execute ADD through rows that should be non-authoritative under the intended
ADD evidence admission contract.
```

## Repair Scope

The production repair should remain narrow:

- Preserve PM ADD intent as evidence only.
- Preserve common NEW/REENTRY/ADD/Cash competition.
- Preserve multi-lot ADD machinery, BF aggregation, PS quantity arithmetic,
  cap, Cash, and Risk Pacing.
- Make `add_investment_evidence.final_add_eligibility = PASS` or an explicit
  equivalent ADD admission status mandatory before ADD can become an accepted
  frontier/BF/PS target.
- Block `requalification = 0.0` or non-PASS incremental evidence from producing
  accepted ADD targets unless there is an explicit reviewed PASS contract.
- Ensure BF-only target authority is actually exclusive for ADD, closing the
  2022-10-28 residual PS/runtime ADD path.
- Do not tune thresholds, weights, ADD quantity, or Cash policy from historical
  outcome.

## Final Judgments

```text
PHASE32_BY_PM_ADD_INTENT_TOTAL = 41
PHASE32_BY_PM_ADD_INTENT_UNIQUE_SYMBOLS = 4
PHASE32_BY_ADD_ELIGIBLE_UNIQUE_SYMBOLS = 3
PHASE32_BY_FRONTIER_ADD_UNIQUE_SYMBOLS = 4
PHASE32_BY_ACCEPTED_ADD_UNIQUE_SYMBOLS = 3
PHASE32_BY_FILLED_ADD_UNIQUE_SYMBOLS = 3
PHASE32_BY_ADD_BREADTH_SCARCE = YES
PHASE32_BY_PRIMARY_DROPOFF = FRONTIER_ADD_CANDIDATE_TO_ACCEPTED_BY_EFFECTIVE_CAP_HEADROOM_AND_PM_INTENT_SCARCITY; SEMANTICALLY_CRITICAL_DROPOFF_IS_ADD_EVIDENCE_FAIL_CLOSED_NOT_ENFORCED
PHASE32_BY_REPEATED_ADD_CONCENTRATION_BIAS = PARTIAL
PHASE32_BY_FALSE_POSITIVE_ADD_PATH = YES
PHASE32_BY_FALSE_NEGATIVE_ADD_RISK = PARTIAL
PHASE32_BY_PRODUCTION_REPAIR_SCOPE = ADD_EVIDENCE_PASS_ADMISSION_BOUNDARY_PLUS_BF_ONLY_ADD_TARGET_AUTHORITY_ENFORCEMENT; PRESERVE_MULTI_LOT_ADD_CAP_CASH_BUDGET_PS_RUNTIME_ARITHMETIC
PHASE32_BY_NEXT_STEP = IMPLEMENT_NARROW_ADD_ADMISSION_REPAIR_REQUIRING_PASS_INCREMENTAL_ADD_EVIDENCE_AND_CLOSE_RESIDUAL_NON_BF_ADD_EXECUTION_PATH_WITHOUT_THRESHOLD_OR_OUTCOME_TUNING
```
