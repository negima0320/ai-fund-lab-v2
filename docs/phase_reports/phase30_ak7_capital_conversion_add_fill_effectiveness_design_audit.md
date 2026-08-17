# Phase30-AK7 - Capital Conversion / ADD Fill Effectiveness Design Audit

## Scope

Task ID: `Phase30-AK7`

Type: `READ_ONLY_DESIGN_AND_AUTHORITY_AUDIT`

Target run:

```text
runtime-test-historical-extended-smoke-20260817T014925194738Z
```

Audit window:

```text
context anchor = 2022-09-12
primary window = 2022-09-13 through 2022-09-27
```

No implementation, threshold change, cap change, fixed exposure target,
Candidate/model change, Safety weakening, fresh run, replay, resume, target-run
mutation, or historical-outcome fitting was performed.

## Primary Judgment

```text
CAPITAL_CONVERSION_REPAIR_JUSTIFIED = YES
IMPLEMENTATION_RECOMMENDED = YES
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = YES
```

AK7 confirms systematic under-conversion between PC/PM intent and executable
capital. The main issue is not poor return in the audit window. It is authority
and design behavior visible before outcome:

1. PC-positive BUY_NEW rows dropped from 87 to 26 PS-positive quantities.
2. Of the 61 zero rows, 31 were residual-priority / capital-below-next-lot, 22
   were Safety hard cap, and 8 were PC/PS discrete authority handoff gaps.
3. Runtime BUY_NEW to Fill dropped from 26 to 10; the 16 non-filled rows were
   mostly not submitted as BUY orders after Planning.
4. ADD worked for `94320`, but only when PC incremental target was large enough
   and the BUY survived Submit/Execution.

## PC Positive BUY_NEW -> PS Zero

Canonical population:

```text
PC_POSITIVE_BUY_NEW_COUNT = 87
PS_POSITIVE_BUY_NEW_COUNT = 26
PC_POSITIVE_TO_PS_ZERO_COUNT = 61
```

Exclusive zero taxonomy:

```text
PC_POSITIVE_TO_PS_ZERO_ROOT_CAUSE_DISTRIBUTION = {
  RESIDUAL_PRIORITY: 31,
  SAFETY_HARD_CAP: 22,
  OTHER_PC_PS_DISCRETE_AUTHORITY_HANDOFF_GAP: 8
}
```

The 31 `RESIDUAL_PRIORITY` rows are explainable by the lot-aware reallocation
contract: the next executable lot exceeded remaining deployable budget after
higher-priority allocations. Cash remains a valid endpoint here.

The 22 `SAFETY_HARD_CAP` rows are also explainable and should remain
fail-closed.

The 8 `OTHER_PC_PS_DISCRETE_AUTHORITY_HANDOFF_GAP` rows are not explained by
cash, Safety, or quality rejection. In those rows, PC/lot-aware evidence carried
positive `final_allocated_quantity`, but PS top-level quantity stayed zero.

Affected symbol-days:

```text
2022-09-13 43550
2022-09-13 68360
2022-09-14 68360
2022-09-15 21560
2022-09-20 21560
2022-09-22 70640
2022-09-26 70640
2022-09-27 70640
```

Detailed rows:

```text
reports/phase_reports/phase30_ak7/pc_positive_buy_new_rows.json
```

## AK2 Coverage

```text
AK2_ELIGIBLE_PC_POSITIVE_COUNT = 46
AK2_ADMITTED_COUNT = 18
AK2_ELIGIBLE_BUT_NOT_ADMITTED_COUNT = 28
```

The 28 eligible-but-not-admitted rows were blocked by remaining deployable
budget / residual priority, not by a missing AK2 authority record. AK2 is
therefore action-effective but bounded: it saves some sub-lot BUY_NEW rows, but
it does not override residual budget, Safety, Strategy cap, or priority order.

## Runtime BUY_NEW -> Fill

```text
BUY_NEW_RUNTIME_TO_FILL_DROP_DISTRIBUTION = {
  cash-pruned: 2,
  submit review/no submitted orders: 1,
  superseded/sell-only execution boundary: 13
}
```

Runtime preserved the 26 PS-positive BUY_NEW intents as Runtime BUY_NEW, but
only 10 filled. The non-fill cases were not a recurrence of reserved-cash
review: two were AK3R2B cash pruning, one had no submitted order, and most fell
into a sell-only execution boundary where submitted execution evidence contained
no BUY fill for the Runtime BUY_NEW intent.

Detailed rows:

```text
reports/phase_reports/phase30_ak7/runtime_buy_new_to_fill_rows.json
```

## Current Second-Lot+ Contract

```text
CURRENT_SECOND_LOT_PLUS_CONTRACT =
PM ADD is intent only. PC must authorize a positive incremental target using
campaign continuity, incremental value, opportunity cost, no-loss averaging,
capital, cap, and lot-aware residual priority. PS then converts the accepted
incremental notional to executable quantity by floor division into the 100-share
trading unit. AK2 minimum executable one-lot admission applies only to BUY_NEW /
REENTRY with current quantity zero; it is not a general 1lot -> 2lot+ promotion
rule.
```

Code authority observed:

```text
Portfolio Construction:
src/ai_fund_lab_v2/strategy/portfolio_construction.py::apply_lot_aware_final_reallocation

Position Sizing:
src/ai_fund_lab_v2/strategy/position_sizing.py::_lot_quantity
src/ai_fund_lab_v2/strategy/position_sizing.py::_resolve_one_lot_discrete_quantity_authority
```

## Second-Lot Threshold

```text
SECOND_LOT_THRESHOLD_SEMANTIC =
floor-to-executable-increment. For ADD, the next lot normally requires accepted
incremental notional >= one_lot_notional. A desired total of 1.2, 1.5, or
1.8 lots remains at 1 lot unless a separate one-lot strategy soft-cap authority
has explicitly authorized an overshoot within Safety. A desired total of 2.1
lots can produce a 1-lot increment, with any fractional residual left unexecuted.
```

Design judgment:

```text
SECOND_LOT_PLUS_DISCRETE_CONVERSION_DESIGN = TOO_CONSERVATIVE
```

The current design is safe, deterministic, and cap-preserving, but it can lose
too much PC intent for high-quality ADD candidates when accepted incremental
target is materially closer to the next executable lot than to zero.

## Design Options

| Option | Judgment | Notes |
| --- | --- | --- |
| A - Current floor semantics | Safe but too conservative | Preserves caps and avoids over-allocation, but loses ADD intent until full next-lot notional is reached. |
| B - Nearest executable lot | Promising but needs guardrails | Mathematically neutral at 0.5 lot, but can increase concentration and turnover if used alone. |
| C - Minimum incremental threshold | Not selected alone | Any threshold must be derived from market discreteness, not fitted from this run. |
| D - Residual-capital-aware promotion | Recommended | Uses existing PC priority, residual budget, cap, Safety, quality, and opportunity-cost evidence to compete next-lot promotions. |
| E - Keep current ADD semantics | Not sufficient | AK7 found authority gaps and systematic under-conversion beyond normal caution. |

```text
RECOMMENDED_SECOND_LOT_PLUS_DESIGN =
Option D - Residual-capital-aware promotion, with nearest-lot distance used as
deterministic lot-discreteness evidence, not as fitted performance tuning.
```

The first repair should be narrow: preserve AK2's 0 -> 1lot scope, fix the
PC/PS discrete authority handoff gap, and then design the 1lot -> 2lot+
promotion contract under PC authority. Do not add an unconditional ADD round-up.

## 94320 Comparator

`94320` succeeded because all required layers aligned on the two fill dates.

```text
94320_ADD_SUCCESS_DISCRIMINATORS = {
  2022-09-21: {
    PM_ADD: YES,
    rank: 1,
    current_quantity: 800,
    current_weight: 11.651%,
    target_weight: 15.751%,
    incremental_notional: 44,086.07,
    one_lot_notional: 15,480,
    target_next_lot_ratio: 2.847937,
    strategy_cap_headroom: 6.349%,
    safety_cap_headroom: 13.349%,
    PS_quantity_delta: 200,
    Runtime_BUY_ADD: YES,
    fill_quantity: 200
  },
  2022-09-26: {
    PM_ADD: YES,
    rank: 1,
    current_quantity: 1000,
    current_weight: 14.575%,
    target_weight: 17.4212%,
    incremental_notional: 30,209.85,
    one_lot_notional: 15,550,
    target_next_lot_ratio: 1.942756,
    strategy_cap_headroom: 3.425%,
    safety_cap_headroom: 10.425%,
    PS_quantity_delta: 100,
    Runtime_BUY_ADD: YES,
    fill_quantity: 100
  }
}
```

Non-fill ADD rows for `94320`:

```text
PERSISTENT_STRONG_ADD_INTENT_NO_FILL_COUNT = 7
PERSISTENT_STRONG_ADD_INTENT_NO_FILL_REASONS = {
  PC incremental target zero / baseline retained: 4,
  Runtime BUY_ADD intent did not submit/fill: 3
}
```

This supports the AK6 finding: `94320` proves ADD can work, but it worked
narrowly and inconsistently.

## Compound Capital

```text
SECOND_LOT_PLUS_CONTRACT_SUPPORTS_COMPOUND_SCALING = PARTIAL
```

Equity enters PC target notional, and `94320` did scale from 800 to 1100 shares.
However, current ADD floor semantics plus residual priority plus Runtime
BUY-to-Fill attrition means compound capital does not reliably become
incremental lots.

## Position Count Authority

```text
CANONICAL_POSITION_COUNT_AUTHORITY =
Portfolio Policy internal dynamic_position_count / position_count_authority.
Fixed maximum_position_count is deprecated and not authoritative; Safety hard
maximum is absent for this window.

OBSERVED_MAX_POSITION_COUNT = 14
OBSERVED_POSITION_COUNT_CONFORMS = YES
```

The observed 10-14 position range is not a fixed-position-count violation.

## Final Judgments

```text
PC_POSITIVE_TO_PS_ZERO_ROOT_CAUSE_DISTRIBUTION = {
  RESIDUAL_PRIORITY: 31,
  SAFETY_HARD_CAP: 22,
  OTHER_PC_PS_DISCRETE_AUTHORITY_HANDOFF_GAP: 8
}

AK2_ELIGIBLE_PC_POSITIVE_COUNT = 46
AK2_ADMITTED_COUNT = 18
AK2_ELIGIBLE_BUT_NOT_ADMITTED_COUNT = 28

BUY_NEW_RUNTIME_TO_FILL_DROP_DISTRIBUTION = {
  cash-pruned: 2,
  submit review/no submitted orders: 1,
  superseded/sell-only execution boundary: 13
}

CURRENT_SECOND_LOT_PLUS_CONTRACT = PM_ADD intent -> PC incremental authorization -> PS floor-to-100-share executable quantity -> Runtime BUY_ADD -> Submit/Execution
SECOND_LOT_THRESHOLD_SEMANTIC = floor-to-executable-increment
SECOND_LOT_PLUS_DISCRETE_CONVERSION_DESIGN = TOO_CONSERVATIVE
RECOMMENDED_SECOND_LOT_PLUS_DESIGN = RESIDUAL_CAPITAL_AWARE_PROMOTION_WITH_NEAREST_LOT_DISTANCE_EVIDENCE

PERSISTENT_STRONG_ADD_INTENT_NO_FILL_COUNT = 7
SECOND_LOT_PLUS_CONTRACT_SUPPORTS_COMPOUND_SCALING = PARTIAL
CANONICAL_POSITION_COUNT_AUTHORITY = Portfolio Policy internal dynamic_position_count / no fixed maximum_position_count
OBSERVED_MAX_POSITION_COUNT = 14
OBSERVED_POSITION_COUNT_CONFORMS = YES

KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = YES
CAPITAL_CONVERSION_REPAIR_JUSTIFIED = YES
IMPLEMENTATION_RECOMMENDED = YES
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
```

## Deliverables

```text
docs/phase_reports/phase30_ak7_capital_conversion_add_fill_effectiveness_design_audit.md
reports/phase_reports/phase30_ak7_capital_conversion_add_fill_effectiveness_design_audit.json
reports/phase_reports/phase30_ak7/evidence_summary.json
reports/phase_reports/phase30_ak7/pc_positive_buy_new_rows.json
reports/phase_reports/phase30_ak7/runtime_buy_new_to_fill_rows.json
```

## Implementation Authorization

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK7
```

## Recommended Next Task

```text
Phase30-AK7R - Approved Capital Conversion / ADD Discrete-Lot Repair
```

