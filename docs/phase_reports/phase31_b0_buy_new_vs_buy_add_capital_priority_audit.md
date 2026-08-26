# Phase31-B0 — BUY_NEW vs BUY_ADD Capital Priority / Winner Amplification Audit

## PRIMARY_JUDGMENT

`BUY_ADD_WINNER_AMPLIFICATION_PRIORITY_GAP_CONFIRMED_FROM_CURRENT_CLEAN_PIT_EVIDENCE`

The current architecture gives BUY_NEW and BUY_ADD a common capital competition path, but it does not define an explicit lifecycle-aware priority, reserve, or marginal-opportunity premium for BUY_ADD. Portfolio Construction accepts both BUY_ADD increments and BUY_NEW targets into the same incremental budget, orders the first pass by `construction_priority`, then performs lot-aware final reallocation over `BUY_ADD` and `BUY_NEW` candidates by quality/order/priority. Runtime Planning then applies a priority-ordered reserved-notional cash-feasible buy batch using canonical strategy order derived from Portfolio Construction and Position Sizing.

In the current target run's completed-day PIT evidence, the 94320 control case shows a strong BUY_ADD opportunity that repeatedly passed PM/PC/PS as a positive executable ADD. It was included and filled on five days, but it was also cash-pruned on three days and review-required once. Two of the cash-pruned days show prior BUY_NEW reserved-notional includes consuming cash before the 94320 ADD item, after which 94320 failed with `DEFERRED_INSUFFICIENT_RESERVED_CASH`.

This is not proof that any BUY_ADD must always outrank BUY_NEW. It is sufficient evidence that the current common competition lacks an explicit winner-amplification authority and can lose strong ADD opportunities to processing order. Performance implementation remains unauthorized.

## Required Fields

| Field | Value |
| --- | --- |
| `TARGET_RUN` | `runtime-test-historical-extended-smoke-20260818T015851711672Z` |
| `RUN_STATUS_AT_AUDIT` | `RUNNING`; audit used only completed business days in `run_state.json`. |
| `COMPLETED_BUSINESS_DAY_SCOPE` | 69 completed business days, `2022-08-10` through `2022-11-21`. |
| `CURRENT_CAPITAL_COMPETITION_OWNER` | Strategy Portfolio Construction owns target/incremental capital competition; Strategy Position Sizing turns accepted targets into executable deltas; Runtime Planning owns reserved-notional cash-feasible batch membership/order consumption for pending BUYs. |
| `BUY_NEW_AND_BUY_ADD_COMMON_COMPETITION` | Yes. PC `_reconcile_incremental_budget` puts `ADD_INCREMENT` and `BUY_NEW` participant requests into one incremental budget; `apply_lot_aware_final_reallocation` then rebatches both as `BUY_ADD` / `BUY_NEW` candidates. |
| `BUY_NEW_EXPLICIT_PRIORITY` | No side-specific explicit priority found. BUY_NEW receives priority only through common `construction_priority`, quality-adjusted reallocation order, lot/broker feasibility, and Runtime Planning's canonical strategy order. |
| `BUY_ADD_EXPLICIT_PRIORITY` | No explicit ADD-over-NEW capital priority/reserve found. ADD has PM intent, ADD eligibility, opportunity-cost pass/fail, and sizing adjustment evidence, but no final cross-side capital priority authority that says strong ADD must outrank comparable BUY_NEW. |
| `PROCESSING_ORDER_CASH_STARVATION` | Yes, observed for 94320 on `2022-08-19` and `2022-08-24`: prior BUY_NEW includes consumed reserved cash before BUY_ADD 94320, then 94320 was `PRUNE` / `DEFERRED_INSUFFICIENT_RESERVED_CASH`. |
| `DAYS_WITH_BOTH_NEW_AND_ADD` | 9 Runtime Planning days: `2022-08-19`, `2022-08-22`, `2022-08-23`, `2022-08-24`, `2022-08-30`, `2022-09-01`, `2022-09-15`, `2022-09-16`, `2022-09-20`. |
| `ADD_CASH_STARVED_DAY_COUNT` | 3 literal BUY_ADD reserved-cash PRUNE days: `2022-08-19`, `2022-08-24`, `2022-09-01`. Of these, 2 were processing-order starvation after prior BUY_NEW includes. |
| `ADD_CASH_STARVED_ITEM_COUNT` | 3 BUY_ADD PRUNE items, all symbol `94320`. |
| `ADD_CASH_STARVED_NOTIONAL` | `160,520` reserved notional (`59,850` + `60,510` + `40,160`). |
| `BUY_NEW_PRIOR_ALLOCATED_NOTIONAL_ON_STARVED_DAYS` | `218,700` prior included BUY_NEW reserved notional on the two processing-order starvation days (`163,000` on `2022-08-19`; `55,700` on `2022-08-24`). `2022-09-01` had no prior BUY_NEW include because all BUYs were cash-pruned against low starting cash. |
| `ADD_FUNNEL` | PM/PC ADD intent: 58; PC positive ADD increment: 9; PS positive BUY_ADD quantity: 9; Runtime Planning BUY_ADD: 9; Pending BUY_ADD included: 5; Pending BUY_ADD cash-pruned: 3; Pending BUY_ADD review-required: 1; BUY_ADD fills inferred by same-day symbol/BUY join: 5. |
| `TOP_ADD_DROP_REASONS` | PS zero-delta/non-executable ADD days: `ADD_TARGET_WEIGHT_UNCHANGED` 50, `EXISTING_BASELINE_CAP_DRIFT_ACCEPTED_NO_INCREMENT` 39. Pending BUY_ADD drops: `DEFERRED_INSUFFICIENT_RESERVED_CASH` 3, `dynamic_cash` review 1. No BUY_ADD lot-aware PC skips were observed; PC lot skips were BUY_NEW only. |
| `94320_CONTROL_CASE` | 94320 was BUY_NEW on `2022-08-15`, then a recurring PM `ADD` / PC `RETAIN` positive-increment case. Runtime Planning BUY_ADD outcomes: PRUNE on `2022-08-19`, INCLUDE/fill on `2022-08-22`, INCLUDE/fill on `2022-08-23`, PRUNE on `2022-08-24`, INCLUDE/fill on `2022-08-30`, PRUNE on `2022-09-01`, INCLUDE_REVIEW_REQUIRED on `2022-09-15`, INCLUDE/fill on `2022-09-16`, INCLUDE/fill on `2022-09-20`. |
| `BUY_NEW_VS_ADD_OUTCOME_SUMMARY` | In completed days, inferred BUY fills were BUY_NEW: 113 fills / `6,726,470` gross notional; BUY_ADD: 5 fills / `152,130` gross notional. Fill lineage required symbol/day inference because execution fills often carry `order_plan_item_id=MISSING` / `pending_item_id=MISSING` for BUYs. |
| `WINNER_AMPLIFICATION_OPPORTUNITY_LOST` | Yes as an architecture/evidence finding, not a performance claim. 94320 was a continuing winner/ADD candidate with PIT positive ADD evidence and `opportunity_buy_rank=1` on the ADD days inspected, yet some executable ADD attempts were deferred by later reserved-cash processing. |
| `ARCHITECTURE_DEFECT` | Yes. The defect is absence of an explicit, auditable BUY_ADD-vs-BUY_NEW capital-priority contract. Runtime has a canonical priority/order consumer, but the common competition does not express whether strong ADD should receive reserve/priority over comparable new exposure. |
| `IMPLEMENTATION_RECOMMENDATION` | Do not implement in this phase. Recommended next design task: define a canonical marginal-capital priority contract that can compare BUY_ADD and BUY_NEW using PIT Strategy evidence, expose side/lifecycle priority explicitly, and preserve Runtime Planning's reserved-notional authority without creating future leakage or post-hoc performance labels. |
| `PERFORMANCE_IMPLEMENTATION_AUTHORIZED` | `NO` |

## Canonical Architecture Evidence

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:2020` defines `_reconcile_incremental_budget`.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:2068`-`2081` classifies current-position ADD increments as `ADD_INCREMENT` and new ADD candidates as `BUY_NEW`.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:2188` allocates the common participant requests by `(construction_priority, security_code)`.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:2239` defines `apply_lot_aware_final_reallocation`.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:2269`-`2293` maps positive ADD increments to `BUY_ADD` and new exposure to `BUY_NEW`.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:2353` sorts lot-aware candidates by `(quality_order, priority, symbol)`.
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:441` defines `_cash_feasible_buy_batch`.
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:452`-`463` records the canonical batch authority, reserved-notional producer, canonical buy priority authority, and `DEFERRED_INSUFFICIENT_RESERVED_CASH` pruning semantic.

## 94320 Processing-Order Evidence

| Date | ADD reserved notional | ADD decision | Remaining cash before ADD | Prior included BUY_NEW notional | Interpretation |
| --- | ---: | --- | ---: | ---: | --- |
| `2022-08-19` | `59,850` | `PRUNE` / `DEFERRED_INSUFFICIENT_RESERVED_CASH` | `24,950` | `163,000` | Processing-order cash starvation after BUY_NEW includes. |
| `2022-08-24` | `60,510` | `PRUNE` / `DEFERRED_INSUFFICIENT_RESERVED_CASH` | `13,200` | `55,700` | Processing-order cash starvation after BUY_NEW include. |
| `2022-09-01` | `40,160` | `PRUNE` / `DEFERRED_INSUFFICIENT_RESERVED_CASH` | `17,140` | `0` | Literal cash starvation, but not caused by prior BUY_NEW include. |
| `2022-09-15` | `41,020` | `INCLUDE_REVIEW_REQUIRED` / `dynamic_cash` | `103,710` | `0` | Not reserved-cash starvation; dynamic cash capacity policy review. |

## Conclusion

Based on current clean PIT evidence, is there a justified reason to believe that a sufficiently strong BUY_ADD opportunity should receive higher capital priority than a comparable BUY_NEW opportunity?

`YES`.

The evidence justifies the design hypothesis because 94320 was a PIT-valid, recurring, positive-increment ADD with high opportunity rank, and the current common competition allowed some of those ADD attempts to be deferred by reserved-cash processing after BUY_NEW includes. This does not authorize a performance implementation and does not prove an unconditional ADD preference. It does justify a follow-up architecture design for explicit marginal-capital priority between BUY_ADD and BUY_NEW.
