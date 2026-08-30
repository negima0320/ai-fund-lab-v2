# Phase32-G - PM ADD to PC Increment Authority Root-Cause Audit

Audit type: READ-ONLY correctness audit.  
Target run: `runtime-test-historical-extended-smoke-20260829T205402869666Z`  
Primary question: why Phase32-E observed 53 PM ADD intents resolving to `ADD_TARGET_WEIGHT_UNCHANGED`.

## Scope Controls

This audit did not modify source code, Strategy config, thresholds, weights, ranks, Cash policy, Risk Pacing, Buy Quality, PM semantics, or G129 semantics. It did not run fresh-run, resume, replay, or long Historical.

The only change produced by Phase32-G is this report.

No future price, future return, future regime, future MFE/MAE, later SELL, final campaign outcome, Historical profitability, or "later went up" evidence was used. J-Quants evidence was used only through existing decision-time run artifacts and PIT authority fields already present in the target run.

## Current Source / Baseline Identity

- Current source commit: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Current worktree: dirty from prior Phase32-C/D/F work.
- Target run source baseline per Phase32-E: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`, dirty source, accepted artifact hash `d2352977bf6feaea22e7c4e5d00980d775eefe1622126fbbde4bd22d3ee6e0e0`.
- Phase32-F has since repaired KI-006 Buy Quality ADD authority preservation in current source. The 53-count analysis below intentionally uses the same Phase32-E completed-window cutoff so that the observed `ADD_TARGET_WEIGHT_UNCHANGED` population is comparable to Phase32-E.

## Evidence Coverage

Two coverage views exist for this run:

| View | Completed days | Window | PM ADD rows | Zero ADD rows | Positive PS ADD rows |
|---|---:|---|---:|---:|---:|
| Phase32-E comparable cutoff | 85 | `2022-10-03` to `2023-02-06` | 78 | 53 | 25 |
| Current accumulated run_state at audit time | 95 | `2022-10-03` to `2023-02-20` | 90 | 64 | 26 |

The root-cause classification below answers the requested 53-row Phase32-E population. The additional 10 completed days do not change the contract finding.

Artifacts inspected:

- `strategy/portfolio_construction.json`
- `strategy/position_sizing.json`
- `strategy/runtime_planning.json`
- `morning/planning_evidence.json`
- `execution/fills.json`
- `position_management/pm_decisions.json`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- current `portfolio_construction.py`, `position_sizing.py`, and `runtime_planning.py`

## PM ADD Semantic Contract

The Phase31 accepted Architecture defines PM ADD as directional lifecycle intent, not an order and not a quantity authority.

Canonical ownership:

| Concern | Owner |
|---|---|
| Existing-position directional lifecycle intent / ADD eligibility | Position Management |
| Target membership and target weight after integrating PM, Opportunity, Buy Quality, Policy, Market Context, Corporate Events, Current, Cash, and Pending | Portfolio Construction |
| Positive incremental ADD capital magnitude and marginal capital comparison | Portfolio Construction |
| Discrete executable quantity | Position Sizing |
| Mapping positive current-position quantity delta to `BUY_ADD` | Runtime Planning |

The key Architecture constraints are:

- PM ADD is directional intent, not an order.
- PC must not convert PM ADD directly into Pending.
- Rank 1 alone and PM ADD alone do not justify ADD.
- ADD becomes executable only when PS emits positive `quantity_delta_candidate` for a current holding and Runtime maps it to `BUY_ADD`.
- Runtime must not decide target weight, position sizing, ADD capital priority, or BUY_NEW vs BUY_ADD ranking.

Judgment: a PM ADD intent with zero target increase is allowed by contract when PC/PS do not find or cannot execute a positive incremental allocation.

## ADD Magnitude Authority

Positive ADD capital magnitude comes from Portfolio Construction, not PM and not Runtime.

Current source confirms the staged path:

1. `_resolve_canonical_add_allocation_bridge(...)` evaluates PM ADD plus decision-time ADD investment evidence:
   - expected edge improvement
   - incremental investment value
   - opportunity cost versus new buys
   - campaign continuation
   - no-loss averaging
   - concentration, capital, and execution feasibility
   - Buy Quality incremental ADD gate added by Phase32-F
2. `apply_lot_aware_final_reallocation(...)` treats a current-position PM ADD as a `BUY_ADD` capital participant only when a positive requested increment exists, then applies marginal priority, G43 binding, lot feasibility, single-name cap, safety hard cap, remaining budget, and staged G115 one-increment authority.
3. `position_sizing.py` consumes `lot_aware_accepted_incremental_weight`, then `accepted_incremental_weight`, then `target-current` as the ADD transaction basis. If the resulting transaction delta is zero, it records `ADD_TARGET_WEIGHT_UNCHANGED`.
4. `runtime_planning.py` maps positive current-position delta to `BUY_ADD`; zero current-position delta maps to `NO_ACTION`.

Therefore PM ADD does not own positive quantity, target weight uplift, or capital amount. PC owns positive ADD capital magnitude; PS owns discrete conversion; Runtime only consumes the PS-bound quantity.

## 53 Zero-Increment Case Breakdown

For the Phase32-E comparable 85-day window, the 53 `ADD_TARGET_WEIGHT_UNCHANGED` cases break down as:

| Boundary / cause | Count | Classification |
|---|---:|---|
| PC ADD bridge fail-closed before positive increment | 45 | `INTENDED_DIRECTIONAL_ADD_SEMANTIC_NO_DEFECT` |
| PC bridge passed but G43 binding blocked the security winner | 2 | `CAPITAL_COMPETITION_VALIDLY_PREFERS_OTHER_DESTINATIONS` / binding limit |
| PC bridge passed but minimum executable lot would exceed safety hard max | 6 | `CAP_OR_RISK_BUDGET_INTENDED_LIMIT` and `E_CASH_OR_LOT_FEASIBILITY_LIMIT` |

Detailed bridge-state counts for the 53 zero rows:

| Evidence state | Count |
|---|---:|
| `add_allocation_eligibility_status=FAIL_CLOSED` | 45 |
| `add_allocation_eligibility_status=PASS` but lot/binding final increment zero | 8 |
| `expected_edge_improvement_state=WEAKENING` | 34 |
| `expected_edge_improvement_state=IMPROVING` | 17 |
| `expected_edge_improvement_state=UNKNOWN` | 2 |
| `incremental_investment_value_state=UNKNOWN` | 45 |
| `incremental_investment_value_state=POSITIVE` | 8 |
| `opportunity_cost_status=FAIL_CLOSED` | 14 |
| `opportunity_cost_status=PASS` | 39 |
| `no_loss_averaging_status=PASS` | 53 |

Primary reason-code sets:

| Reason-code set | Count |
|---|---:|
| `ADD_EXPECTED_EDGE_WEAKENING`, `ADD_INCREMENTAL_VALUE_UNKNOWN` | 29 |
| `ADD_INCREMENTAL_VALUE_UNKNOWN`, `ADD_OPPORTUNITY_COST_FAIL` | 9 |
| `ADD_TARGET_WEIGHT_INCREASED` then later final increment zero | 8 |
| `ADD_EXPECTED_EDGE_WEAKENING`, `ADD_INCREMENTAL_VALUE_UNKNOWN`, `ADD_OPPORTUNITY_COST_FAIL` | 5 |
| `ADD_EXPECTED_EDGE_UNKNOWN_FAIL_CLOSED`, `ADD_INCREMENTAL_VALUE_UNKNOWN` | 2 |

Quality state distribution among zero rows:

| Buy Quality state | Count |
|---|---:|
| `REDUCED_ALLOCATION_ONLY` | 26 |
| `FULL_ALLOCATION_ELIGIBLE` | 14 |
| `BUY_WAIT` | 13 |

The `BUY_WAIT` observations in this 53-row zero population are not winner-capitalization under-allocation defects. They either failed the PC bridge or were blocked by safety/lot constraints. The separate Phase32-E KI-006 defect was the opposite direction: `BUY_WAIT` / zero quality adjustment incorrectly becoming positive executable BUY_ADD in three filled-path cases. Phase32-F repaired that current-source defect.

## First Zero-Increment Boundary

First decisive boundary for the majority:

```text
PM ADD
  -> Portfolio Construction ADD allocation bridge
  -> add_allocation_eligibility_status = FAIL_CLOSED
  -> target/current preserved
  -> Position Sizing quantity_delta_candidate = 0
  -> Runtime Planning NO_ACTION
```

Count: 45 of 53.

First decisive boundary for the remaining 8:

```text
PM ADD
  -> PC ADD bridge PASS
  -> requested/accepted continuous increment exists
  -> lot-aware / G43 / safety binding sets final lot-aware increment to 0
  -> Position Sizing quantity_delta_candidate = 0
  -> Runtime Planning NO_ACTION
```

Count: 8 of 53.

## Representative Time Series

Representative zero-increment cases:

| Date | Symbol | Current weight | Final target | Requested increment | PC bridge | Evidence | Final boundary |
|---|---:|---:|---:|---:|---|---|---|
| `2022-10-05` | `94340` | 0.028291 | 0.028291 | 0.000000 | `FAIL_CLOSED` | expected edge `WEAKENING`, incremental value `UNKNOWN`, opportunity cost `FAIL_CLOSED` | PC bridge |
| `2022-10-07` | `94320` | 0.029755 | 0.029755 | 0.000000 | `FAIL_CLOSED` | expected edge `WEAKENING`, incremental value `UNKNOWN`, opportunity cost `PASS` | PC bridge |
| `2022-10-21` | `94320` | 0.046888 | 0.046888 | 0.029677 | `PASS` | expected edge `IMPROVING`, incremental value `POSITIVE`, opportunity cost `PASS` | G43 binding `g43_binding_blocked` |
| `2022-11-15` | `99840` | 0.147567 | 0.147567 | 0.032433 | `PASS` | expected edge `IMPROVING`, incremental value `POSITIVE`, opportunity cost `PASS` | one lot would exceed safety hard max |

Representative positive ADD cases:

| Date | Symbol | Current weight | Final target | Requested increment | Lot-aware accepted increment | PS delta | Evidence |
|---|---:|---:|---:|---:|---:|---:|---|
| `2022-10-06` | `94340` | 0.027703 | 0.041489 | 0.035714 | 0.013786 | 100 | improving / positive / opportunity cost pass |
| `2022-10-12` | `94340` | 0.041928 | 0.056000 | 0.021765 | 0.014072 | 100 | improving / positive / opportunity cost pass |
| `2022-10-28` | `94320` | 0.046191 | 0.061730 | 0.035714 | 0.015539 | 100 | improving / positive / opportunity cost pass |
| `2022-11-29` | `76470` | 0.029929 | 0.032423 | 0.029412 | 0.002494 | 100 | improving / positive / opportunity cost pass |

This proves the ADD magnitude path exists. It is selective, not globally disconnected.

## Filled vs Unchanged Comparison

By symbol in the Phase32-E comparable window:

| Symbol | PM ADD rows | Positive PS ADD | Zero ADD | Main zero pattern |
|---:|---:|---:|---:|---|
| `76470` | 25 | 13 | 12 | 11/12 had expected edge `WEAKENING` or `UNKNOWN` and incremental value `UNKNOWN`; opportunity cost usually passed |
| `94320` | 29 | 8 | 21 | mix of expected edge weakening, opportunity-cost fail, and 2 G43 binding blocks |
| `94340` | 6 | 4 | 2 | expected edge weakening / incremental value unknown |
| `99840` | 18 | 0 | 18 | high current weights near cap plus either incremental value unknown / opportunity-cost fail or one-lot safety hard-cap block |

Positive ADD rows consistently had:

- `add_allocation_eligibility_status=PASS`: 25/25
- `expected_edge_improvement_state=IMPROVING`: 25/25
- `incremental_investment_value_state=POSITIVE`: 25/25
- `opportunity_cost_status=PASS`: 25/25
- no lot-aware skip reason: 25/25

Zero ADD rows did not show this complete path. They either failed PC evidence checks before a positive capital participant existed, or they passed continuous evidence but failed binding/lot/safety conversion.

## NEW vs ADD Competition Evidence

In the Phase32-E comparable window, 48 days had at least one zero PM ADD row and a same-day BUY_NEW plan or BUY_NEW fill. This shows NEW deployment coexisted with zero ADD, but it does not prove invalid diversion.

Concrete examples:

- `2022-10-05`: `94340` PM ADD zero because PC bridge failed on expected edge weakening, incremental value unknown, and opportunity cost fail. Same day BUY_NEW plans/fills existed for other symbols. Since the ADD side never became a positive capital competitor, this is not a valid ADD being overridden by NEW.
- `2022-10-21`: `94320` bridge passed but G43 binding blocked the security winner. Same day BUY_NEW plans existed. This is capital/binding selection at PC, not Runtime re-ranking.
- `2022-11-15`: `99840` bridge passed but a one-lot ADD would breach safety hard max. Same day NEW opportunities existed, but the ADD was not executable under safety/lot constraints.

Runtime evidence remains consistent with Architecture: Runtime consumed Strategy order and PS quantity delta. It did not re-rank BUY_NEW over BUY_ADD.

## J-Quants PIT Evidence Used

No new J-Quants fetch was performed. The audit relied on existing run artifacts, which carry decision-time/PIT market evidence and reference-price authority.

Representative examples:

- `2022-10-05 94340`: Phase32-E established reference price `148.0`, source dataset `J-Quants equities_bars_daily`, PIT `PASS`.
- `2022-10-12 94320`: Phase32-E established reference price `158.0`, source dataset `J-Quants equities_bars_daily`, PIT `PASS`.

No future market observation or outcome was used to judge whether ADD should have been larger.

## Architecture Consistency Judgment

Architecture is internally consistent for this question:

- PM says whether an existing position has ADD lifecycle intent / eligibility.
- PC decides whether that intent receives positive marginal capital and how much continuous/staged increment is authorized.
- PS converts authorized increment to executable quantity.
- Runtime only maps positive/zero/negative quantity deltas.

`PM ADD says yes but PC target unchanged` is therefore not inherently defective. It is an intended outcome when marginal ADD evidence is weak/unknown, NEW opportunity cost is superior, safety/cap/lot constraints block execution, or binding competition selects another destination.

The current contract is not capital-effectless: the same population produced 25 positive PS ADD rows, 23 BUY_ADD fills in Phase32-E's accumulated execution view, and repeated ADD fills for `76470`, `94320`, and `94340`.

## Root Cause

The 53 Phase32-E zero-increment PM ADD intents resolved to `ADD_TARGET_WEIGHT_UNCHANGED` because PM ADD is directional intent only. Most rows did not satisfy PC's positive incremental capital evidence contract, and the remainder were blocked by downstream PC-owned binding/lot/safety constraints before PS could emit a positive quantity delta.

Dominant direct root cause:

```text
PC ADD bridge did not authorize positive incremental ADD capital
because incremental investment value was UNKNOWN and/or expected edge was WEAKENING / UNKNOWN
and, in some rows, opportunity cost failed against available NEW opportunities.
```

Secondary direct root cause:

```text
PC continuous ADD eligibility existed,
but G43 binding or one-lot safety hard-cap feasibility reduced final lot-aware increment to zero.
```

Not root cause:

- Runtime re-ranking.
- PM quantity ambiguity / G129 fallback.
- Missing direct PM ADD-to-Pending behavior.
- Strategy performance / Historical profitability.
- Future winner outcome.

## Defect Classification

Overall classification: `G_MULTIPLE_CAUSES`.

Component classifications:

- 45/53: `INTENDED_DIRECTIONAL_ADD_SEMANTIC_NO_DEFECT`
- 2/53: `CAPITAL_COMPETITION_VALIDLY_PREFERS_OTHER_DESTINATIONS`
- 6/53: `CAP_OR_RISK_BUDGET_INTENDED_LIMIT` plus lot/safety feasibility

`PM_ADD_TO_CAPITAL_MAGNITUDE_AUTHORITY_GAP`: `NOT_REPRODUCED`.

`PC_TARGET_CONSTRUCTION_DEFECT`: `NOT_REPRODUCED` for the 53 zero-increment population.

`WINNER_CAPITALIZATION_BLOCKED_BY_CORRECTNESS_DEFECT`: `NO` for the requested 53 zero-increment question. Progressive ADD is materially weak, but the observed weakness follows the accepted authority contract. Improving breadth or aggressiveness of ADD capitalization would be a performance/Strategy initiative, not a correctness repair, unless a future audit finds a specific decision-time authority violation.

## Repair Required

Repair required: `NO_REPAIR` for Phase32-G.

No correctness repair is required for the PM ADD to PC increment contract. A change that makes PM ADD more frequently or more aggressively deploy capital would alter Strategy behavior and requires a user-approved performance initiative with explicit new semantics.

Phase32-F already addressed the separate KI-006 defect where Buy Quality zero authority could be re-expanded into positive ADD. Phase32-G does not reopen G129 or Phase32-F.

## Retest Required

Retest required: `NO` for this read-only correctness audit.

No user command is required to validate a Phase32-G code repair, because no repair was performed. The next long Historical validation remains a user-operated activity only if the user wants to evaluate the already-completed Phase32-C/D/F repairs.

## Confirmations

- NO CODE CHANGE: confirmed.
- NO Strategy/parameter/threshold/weight/rank/Cash/Risk Pacing change: confirmed.
- NO PM semantic change: confirmed.
- NO G129 semantic change: confirmed.
- NO future-information use: confirmed.
- Historical PnL / profitability not used: confirmed.

## Final Judgment

1. `WHY_DO_53_PM_ADD_INTENTS_RESOLVE_TO_ADD_TARGET_WEIGHT_UNCHANGED`

   Because 45 did not receive positive incremental capital authority at the PC ADD bridge, mainly due to unknown/weak marginal ADD evidence and/or opportunity-cost failure, and 8 passed the continuous bridge but were reduced to zero by G43 binding or one-lot safety hard-cap constraints.

2. `WHO_OWNS_POSITIVE_ADD_CAPITAL_MAGNITUDE`

   Portfolio Construction owns positive ADD capital magnitude and staged marginal ADD increment authorization. Position Sizing owns discrete executable quantity. Runtime Planning only maps PS quantity delta to runtime intent.

3. `IS_THE_CURRENT_PM_ADD_TO_PC_INCREMENT_CONTRACT_DEFECTIVE`

   NO. The accepted contract says PM ADD is directional intent, not quantity or target-weight authority. PC may validly preserve current target when positive incremental ADD evidence is absent or feasibility/binding constraints block execution.

4. `IS_WINNER_CAPITALIZATION_BEING_BLOCKED_BY_A_CORRECTNESS_DEFECT`

   NO for the 53 zero-increment population. Winner capitalization is selective and materially weak, but the evidence does not show a correctness defect blocking valid positive ADD capital. The separate Buy Quality authority defect found in Phase32-E was repaired in Phase32-F and was not an under-capitalization defect.

5. `IS_A_REPAIR_REQUIRED_OR_WOULD_CHANGE_REQUIRE_A_NEW_PERFORMANCE_INITIATIVE`

   No correctness repair is required. Any change to make PM ADD create more capital, loosen marginal evidence gates, prefer ADD over NEW more often, or raise staged ADD magnitude would be a new user-approved Strategy/performance initiative.
