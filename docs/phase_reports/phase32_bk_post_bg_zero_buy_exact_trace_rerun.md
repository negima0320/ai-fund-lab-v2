# Phase32-BK Post-BG Zero-Buy Exact Trace Re-run

## Executive Summary

The Phase32-BK rerun found the `2022-10-03` zero-buy root cause in the
Post-BG production consumer path.

The run generated candidates and Portfolio Construction admitted the same
deployable symbol set as the prior Post-BG-pre-switch run, but the new
`canonical_marginal_capital_frontier_authority.v1` accepted zero security
targets. The first zero boundary is therefore:

```text
Portfolio Construction -> marginal capital authority budget/cash feasibility
```

Exact failure:

```text
available_incremental_budget = 0.74
source_observations budget_notional = 740000.0
but authority starting_cash_notional = 0.74
and authority available_incremental_budget_notional = 0.74
```

The authority then evaluated every security first-lot candidate against
`available_cash = 0.74`, so all `NEW_FIRST_LOT` candidates became infeasible:

```text
45 INFEASIBLE_INSUFFICIENT_CASH
5 INFEASIBLE_CAP_BLOCKED with insufficient_cash also present
0 accepted_incremental_targets
0 BF aggregated_ps_targets
```

Position Sizing did consume the active BG authority, but it consumed an empty
BF boundary. No legacy target-gap or ADD-zero fallback was used. Runtime,
Pending, Submit, and Fill correctly propagated the zero quantity.

This is a BG production-path regression, not a legitimate Cash/no-deployment
decision and not a Runtime/Pending defect.

## Run Identity

| Field | Value |
| --- | --- |
| Target run id | `runtime-test-historical-extended-smoke-20260828T153014206482Z` |
| Target date | `2022-10-03` |
| Evidence path | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T153014206482Z` |
| Audit mode | READ-ONLY artifact trace |
| Production changes | None |
| Fresh/resume/replay/backtest | Not executed |

## Required Inputs

Read:

| Report | Status |
| --- | --- |
| `docs/phase_reports/phase32_bj_post_bg_zero_buy_exact_trace.md` | Present |
| `docs/phase_reports/phase32_bg_explicit_production_consumer_switch_implementation.md` | Present |
| `docs/phase_reports/phase32_bf_pc_to_ps_consumer_switch_boundary_validator.md` | Present |

Inherited BG path:

```text
PM / candidate evidence
-> canonical_marginal_capital_frontier_authority.v1
-> pc_to_ps_consumer_switch_boundary.aggregated_ps_targets[]
-> Position Sizing
-> Runtime
```

## Day-0 Trace

| Stage | Artifact | Status | Quantity / Count Evidence |
| --- | --- | --- | --- |
| Candidate / Buy Quality | `strategy/buy_quality_decisions.json` | `PASS` | `decision_count=50`; action distribution: `BUY_WAIT=16`, `FULL_ALLOCATION_ELIGIBLE=1`, `REDUCED_ALLOCATION_ONLY=22`, `REJECT=11`. |
| Portfolio Construction | `strategy/portfolio_construction.json` | `PASS` | `available_incremental_budget=0.74`; PC cash competitor selected deployable symbols: 9 (`33700`, `37820`, `58200`, `76470`, `83060`, `89180`, `92420`, `93600`, `94340`). |
| Marginal capital authority | `strategy/marginal_capital_frontier_authority.json` | `PASS` | `candidate_count_total=51`; `NEW_FIRST_LOT=50`, `CASH_OPTIONALITY=1`; `accepted_target_count=0`. |
| Allocation budget | same authority artifact | `PASS` but semantically defective | `source_observations` show `budget_notional=740000.0`, but final `available_incremental_budget_notional=0.74`, `starting_cash_notional=0.74`, `remaining_budget_notional=0.74`. |
| BF aggregated targets | `pc_to_ps_consumer_switch_boundary` | `PASS` | `accepted_incremental_target_count=0`; `aggregated_ps_target_count=0`; `aggregated_ps_targets=[]`. |
| BG production switch | embedded authority / BF boundary | Active | `production_consumer_enabled=true`; `production_consumer_count=1`; `production_consumers=["strategy.position_sizing"]`; `feeds_position_sizing=true`. |
| Position Sizing | `strategy/position_sizing.json` | `PASS` | Consumed BG authority with `accepted_boundary_target_count=0`; all 50 rows `RESOLVED_ZERO_DELTA`; nonzero target rows = 0. |
| Runtime Planning | `strategy/runtime_planning.json` | `PASS` | 22 plans, all `NO_ORDER` / `RESOLVED_ZERO_DELTA`; reason includes `no_order_zero_quantity_delta`. |
| Planning / Pending | `morning/planning_evidence.json`, `morning/pending_generation_evidence.json` | `NO_ORDER_AUTHORIZED` | `plan_count=22`; `pending_item_count=0`; pending reason `strategy_planning_no_order_authorized`. |
| Submit / Fill | `execution/submitted_order_authority.json`, `execution/fills.json` | `PASS` | `orders_count=0`; `submitted_order_count=0`; fills = 0. |

## Authority Details

Authority result:

```text
status = PASS
candidate_count_total = 51
candidate_count_by_type = {
  ADD_NEXT_LOT: 0,
  CASH_OPTIONALITY: 1,
  NEW_FIRST_LOT: 50,
  REENTRY_FIRST_LOT: 0
}
accepted_target_count = 0
review_reasons = []
```

Disposition counts:

```text
CASH_OPTIONALITY / SHADOW_WINNER = 1
NEW_FIRST_LOT / INFEASIBLE_INSUFFICIENT_CASH = 45
NEW_FIRST_LOT / INFEASIBLE_CAP_BLOCKED = 5
```

Representative candidate evidence:

| Symbol | Increment notional | Authority available cash | Disposition | Reason |
| --- | ---: | ---: | --- | --- |
| `33500` | `4130.0` | `0.74` | `INFEASIBLE_INSUFFICIENT_CASH` | `insufficient_cash` |
| `33700` | `34100.0` | `0.74` | `INFEASIBLE_INSUFFICIENT_CASH` | `insufficient_cash` |
| `37820` | `6800.0` | `0.74` | `INFEASIBLE_INSUFFICIENT_CASH` | `insufficient_cash` |
| `49340` | `261000.0` | `0.74` | `INFEASIBLE_CAP_BLOCKED` | `cap_blocked`, `insufficient_cash` |

The minimum observed security lot notional was `300.0`, still greater than the
authority's defective `available_cash=0.74`, so no security candidate could be
accepted.

## Budget / Cash Evidence

The Portfolio Policy artifact had a valid 1,000,000 cash context:

```text
cash_available = 1000000.0
net_available_cash = 1000000.0
pending_reserved_cash = 0.0
target_gross_exposure_ratio = 0.74
```

The valuation projection also had valid cash:

```text
cash = 1000000.0
```

The authority source observations correctly derived the budget candidates from
PC weight:

| Priority | Role | Field | Budget weight | Budget notional |
| ---: | --- | --- | ---: | ---: |
| 1 | `portfolio_construction.available_incremental_budget` | `available_incremental_budget` | `0.74` | `740000.0` |
| 2 | `portfolio_construction.capital_competition.canonical_multi_allocation_deployment_set.available_incremental_budget` | `available_incremental_budget` | `0.74` | `740000.0` |
| 3 | `portfolio_construction.incremental_budget_reconciliation.available_incremental_budget` | `available_incremental_budget` | `0.74` | `740000.0` |

The defect occurs after that observation step, when the final authority budget
is capped by an incorrectly resolved `starting_cash`:

```text
available_incremental_budget_notional = 0.74
available_incremental_budget_weight = 0.00000074
starting_cash_notional = 0.74
remaining_budget_notional = 0.74
```

This is inconsistent with both the observed budget notional (`740000.0`) and
the run's actual cash (`1000000.0`).

## Code Boundary

The BG runtime hook builds and activates the authority in
`src/ai_fund_lab_v2/strategy/shadow_runtime.py`:

```text
_produce_lot_aware_final_portfolio_construction
-> build_marginal_capital_frontier_authority_payload(...)
-> activate_pc_to_ps_production_consumer_switch(...)
```

The hook passes:

```text
source_artifacts.cash = runtime_current_asset_snapshot
cash_payload = _cash_summary(...)
```

`_cash_summary` places cash under `summary.cash`, `summary.buying_power`, and
`summary.current_cash`.

The shadow cash resolver used by the authority checks only top-level
`available_cash`, `buying_power`, or `cash` on the supplied `cash_payload`, then
falls back to `portfolio_construction.available_incremental_budget`.

That fallback value is a weight (`0.74`), but the resolver treats it as cash
notional. The authority budget then caps the correctly observed `740000.0`
budget notional down to `starting_cash=0.74`.

Relevant functions:

| Component | Function | Boundary |
| --- | --- | --- |
| Runtime hook | `shadow_runtime._produce_lot_aware_final_portfolio_construction` | Builds active authority and embeds it into final PC. |
| Runtime cash payload | `shadow_runtime._cash_summary` | Emits cash inside `summary.*`. |
| Shadow cash state | `common_marginal_capital_frontier_shadow._cash_state` | Does not read nested `summary.*`; falls back to PC weight. |
| Budget authority | `marginal_capital_frontier_authority._allocation_budget_authority` | Caps `budget_notional` by defective `starting_cash`. |
| Security feasibility | `common_marginal_capital_frontier_shadow._security_candidate` / feasibility | Marks all security candidates insufficient cash. |
| PS consumer | `position_sizing._marginal_capital_frontier_switch_from_pc_summary` | Correctly consumes active but empty BF boundary. |

## BF / BG Consumer Evidence

BF boundary:

```text
status = PASS
accepted_incremental_target_count = 0
aggregated_ps_target_count = 0
production_consumer_enabled = true
production_consumer_count = 1
feeds_position_sizing = true
legacy_target_gap_input_used = false
legacy_target_gap_fallback_allowed = false
legacy_zero_fallback_allowed = false
```

PS switch consumption:

```text
status = PASS
production_consumer_enabled = true
bf_only_target_authority = true
accepted_boundary_target_count = 0
consumed_position_count = 0
legacy_target_gap_fallback_used = false
legacy_zero_fallback_used = false
review_required_position_count = 0
runtime_logic_changed = false
```

This proves PS consumed the BG authority path. It did not fall back to legacy
target-gap or legacy ADD-zero behavior.

## Downstream Propagation

Position Sizing:

```text
positions = 50
nonzero target_weight rows = 0
nonzero final_quantity_delta rows = 0
quantity_status = RESOLVED_ZERO_DELTA for all rows
```

For the 22 incremental deployment competitor rows, PS reason was:

```text
marginal_capital_frontier_authority_not_selected_for_symbol
```

The materialized row reasons are:

```text
membership_intent:ADD_CANDIDATE;pm_action:NEW
```

with:

```text
marginal_capital_frontier_switch_sizing_eligibility = NOT_SELECTED_BY_BG_AUTHORITY
```

Runtime Planning:

```text
plans = 22
all plans = NO_ORDER / RESOLVED_ZERO_DELTA
reason_codes include no_order_zero_quantity_delta
```

Pending / Submit / Fill:

```text
planning status = NO_ORDER_AUTHORIZED
pending_item_count = 0
submitted_order_count = 0
fill_count = 0
```

Runtime and Pending did not introduce the zero-buy. They received zero quantity
from PS, which received zero selected targets from the BG authority.

## Prior Run Comparison

Comparison run:

```text
runtime-test-historical-extended-smoke-20260828T000823285458Z
```

Same date:

```text
2022-10-03
```

Candidate and PC context were materially the same:

| Field | Prior run | Post-BG run |
| --- | ---: | ---: |
| Buy quality decisions | 50 | 50 |
| `BUY_WAIT` | 16 | 16 |
| `FULL_ALLOCATION_ELIGIBLE` | 1 | 1 |
| `REDUCED_ALLOCATION_ONLY` | 22 | 22 |
| `REJECT` | 11 | 11 |
| PC `available_incremental_budget` | `0.74` | `0.74` |
| PC deployable symbols | 9 | 9 |

Prior run deployable symbols:

```text
33700, 37820, 58200, 76470, 83060, 89180, 92420, 93600, 94340
```

Prior run Position Sizing produced nonzero quantity:

```text
nonzero target_weight rows = 9
nonzero final_quantity_delta rows = 9
quantity sum = 6000
planning pending_item_count = 9
submitted_order_count = 7
fill_count = 7
```

Post-BG run Position Sizing produced:

```text
nonzero target_weight rows = 0
nonzero final_quantity_delta rows = 0
planning pending_item_count = 0
submitted_order_count = 0
fill_count = 0
```

The candidates did not disappear upstream. They disappeared when BG connected
the new authority to PS and that authority had zero accepted targets due to the
cash/budget notional regression.

## Classification

| Classification | Judgment | Evidence |
| --- | --- | --- |
| Legitimate Cash/no-deployment | No | Cash was selected only after all securities were falsely infeasible under `available_cash=0.74`. |
| Authority materialization defect | Yes | Active authority materialized with `starting_cash_notional=0.74` despite 1,000,000 cash evidence. |
| Budget acceptance defect | Yes | Budget observations showed `740000.0`, final budget notional became `0.74`. |
| BF aggregation defect | No | BF aggregated zero because authority accepted zero; BF status and conservation passed. |
| BG switch defect | Partial / causal | Switch correctly consumed BF-only rows, but BG production hook exposed the authority cash/budget unit defect on the production path. |
| PS consumer defect | No | PS consumed active authority and forbade fallback as designed. |
| Runtime/Pending defect | No | Runtime/Pending propagated zero quantity from PS. |

## Defect / Repair Boundary

Production repair is required, but the repair boundary should remain narrow:

```text
BG authority materialization cash source / budget notional unit handling
```

Do not change:

```text
PM logic
PS quantity arithmetic
Runtime logic
Pending / Order / Execution logic
REENTRY gates
Cash policy thresholds
Risk Pacing
REDUCE / EXIT
```

The likely minimal repair is to make the BG runtime materialization path feed
the same PIT-safe cash resolver/source shape accepted by AU, or make the
authority cash resolver read the runtime `_cash_summary.summary.*` cash fields
without treating weight fields as notional cash.

## Final Judgments

```text
PHASE32_BK_ZERO_BUY_REGRESSION = YES
PHASE32_BK_AUTHORITY_TARGET_COUNT = 0
PHASE32_BK_BF_TARGET_COUNT = 0
PHASE32_BK_PS_CONSUMED_BG_AUTHORITY = YES
PHASE32_BK_FIRST_ZERO_STAGE = MARGINAL_CAPITAL_AUTHORITY_BUDGET_CASH_FEASIBILITY
PHASE32_BK_EXACT_ROOT_CAUSE = BG active authority materialization resolved decision-time cash as 0.74 instead of 1000000.0; allocation budget observations showed 740000.0 notional but final starting_cash_notional/available_incremental_budget_notional were capped to 0.74, causing all security candidates to be INFEASIBLE_INSUFFICIENT_CASH and BF aggregated targets to be empty.
PHASE32_BK_LEGACY_FALLBACK_USED = NO
PHASE32_BK_BG_REPAIR_REQUIRED = YES
PHASE32_BK_LONGER_VALIDATION_READY = NO
PHASE32_BK_NEXT_STEP = Implement a narrow BG cash/budget source repair so active authority materialization uses PIT-safe notional cash from portfolio_policy or valuation_projection, or reads runtime _cash_summary.summary cash fields correctly, then run focused tests and user-operated short fresh validation.
```
