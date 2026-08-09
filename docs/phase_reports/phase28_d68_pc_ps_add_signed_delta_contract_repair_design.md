# Phase28-D68 PC/PS ADD Signed-Delta Contract Repair Design

## Judgment

Primary Judgment:

```text
PHASE28_D68_PC_PS_ADD_SIGNED_DELTA_CONTRACT_REPAIR_DESIGN_COMPLETE_D69_READY
```

D68 completed a design-only repair plan for the Phase28-D67 halt. No implementation, config, schema, threshold, model, Accepted Generation, Runtime artifact, Pending artifact, Runtime state, fresh run, resume, long historical, or 100BD rerun was performed.

## Root Contract Mismatch

Producer semantic:

```text
Portfolio Construction
_resolve_canonical_add_allocation_bridge
target_weight_change = post_add_target_weight - current_weight
```

This is a signed target delta. It can be negative when PM says `ADD` but the current position weight is already above the effective ADD ceiling due to valuation movement.

Consumer semantic:

```text
Position Sizing
_raw_position ADD branch
target_change = _ratio(row.get("target_weight_change"), ...)
```

`_ratio()` requires `0 <= value <= 1`, so Position Sizing currently treats `target_weight_change` as a non-negative ratio. That is the mismatch.

The 2023-05-09 / 76470 reproduction case is:

```text
PM action = ADD
current_weight = 0.182409
single_name_weight_cap = 0.18
post_add_target_weight = 0.18
target_weight_change = -0.002409
```

That state should mean:

```text
No executable ADD increment
valid zero transaction delta
NO_ACTION
```

It must not mean:

```text
Position Sizing BLOCK
unresolved BUY_ADD
forced SELL
```

## Selected Repair Design

Selected option:

```text
Option B: Make Position Sizing ADD consume positive-only ADD increment authority.
```

Do not redefine PC `target_weight_change` as positive-only. Keep it as signed observability. Position Sizing should not use it as executable ADD authority.

D69 should repair the ADD branch in:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py
_raw_position
```

The ADD executable increment authority should be:

```text
1. lot_aware_accepted_incremental_weight
2. target_weight_resolution.lot_aware_final_reallocation.accepted_lot_increment_weight
3. accepted_incremental_weight
4. max(target_weight - current_weight, 0)
```

This is already the D61/D55-B transaction-delta priority. D69 should align the later ADD reason/diagnostic branch with that same positive-only authority and stop validating signed `target_weight_change` through `_ratio()`.

## Why This Is Production-Common

The defect is not historical-only. A production current position can drift above cap by ordinary price movement. A PM ADD in that state means additional investment is desirable only if positive executable headroom exists.

Therefore:

```text
PM ADD + no positive headroom = valid zero/no-action
```

not:

```text
negative ADD
forced SELL
unresolved BUY_ADD
```

The design applies equally to production, demo, and historical paths.

## Preservation

D61 preservation:

```text
PRESERVED
```

Positive ADD remains enabled because Position Sizing continues to consume PC's accepted ADD increment and lot-aware accepted increment. The design does not revert to `base_target - current_weight` as the only ADD authority.

D63 preservation:

```text
PRESERVED
```

Pending Safety behavior is untouched. Empty/no-order terminal handling and fail-closed protections remain intact.

BUY / SELL independence:

```text
PRESERVED
```

An above-cap ADD with zero executable increment becomes no-action. It does not synthesize SELL_REDUCE or SELL_EXIT. REDUCE and EXIT remain governed by independent PM sell authority.

Fail-closed preservation:

```text
PRESERVED
```

Genuinely missing quantity, missing price, missing target authority, or unresolved current membership should still reach REVIEW_REQUIRED. The repair only turns malformed above-cap ADD zero-increment states into resolved zero transaction deltas.

No new conservative constraint is introduced. Caps, budget competition, lot-aware conversion, cash feasibility, broker feasibility, Submit Guard, SELL lifecycle, and thresholds remain unchanged.

## Regression Matrix for D69

Required short regressions:

1. ADD below cap with positive headroom: positive PC increment can still produce positive PS BUY_ADD quantity.
2. ADD exactly at cap: zero increment, zero quantity delta, Runtime NO_ACTION, no BLOCK.
3. ADD above cap by valuation appreciation: signed negative PC delta is allowed as observability, PS resolves zero ADD transaction.
4. ADD above cap with zero executable increment: no unresolved BUY_ADD quantity.
5. ADD with lot-aware zero: zero/no-action or below-lot no-order, no BLOCK.
6. ADD with valid positive lot-aware increment: PS prefers lot-aware positive increment.
7. HOLD above cap: retained baseline behavior unchanged.
8. REDUCE above cap: sell-reducing semantics unchanged.
9. EXIT above cap: full-liquidation semantics unchanged.
10. BUY_NEW unaffected.
11. Runtime BUY_ADD mapping unaffected for positive quantity deltas.
12. Strategy Planning Authority still blocks genuinely unresolved quantity.
13. Exact 2023-05-09 / 76470 reproduction: no `ratio out of range`; zero transaction delta; Runtime NO_ACTION unless another authority blocks.

## Resume and D66

Resume allowed after D69 PASS:

```text
YES
```

Fresh run required after D69 PASS:

```text
NO
```

D67 confirmed the halt occurred before 2023-05-09 pending commit, submit, broker simulation, execution, fills, ledger mutation, or current-state mutation.

D66 status:

```text
WAITING
```

D66 final attribution must wait until D69 implementation, short regression PASS, user resume, and 100BD completion. The partial run must not be used for final attribution.

## D69 Contract

D69 should implement exactly one repair:

```text
Position Sizing ADD reason/diagnostic branch must not consume signed
target_weight_change via _ratio as executable ADD authority.
```

Expected 76470 after D69:

```text
Position Sizing = PASS
quantity_delta_candidate = 0
quantity_status = RESOLVED_ZERO_DELTA
Runtime Planning = NO_ACTION
Strategy Planning Authority = no strategy_plan_quantity_unresolved:76470
```

## Deliverables

- `docs/phase_reports/phase28_d68_pc_ps_add_signed_delta_contract_repair_design.md`
- `reports/phase_reports/phase28_d68_pc_ps_add_signed_delta_contract_repair_design.json`
- `reports/phase28_d68_pc_ps_add_signed_delta_contract_repair_design/`
