# Phase29-L21E — BUY_ADD Overshoot Authorized but Quantity Zero Root Cause Audit

## Primary Judgment

`PHASE29_L21E_BUY_ADD_SOFT_CAP_POSITION_SIZING_INTEGRATION_GAP_CONFIRMED_REPAIR_REQUIRED`.

Secondary classification:

- `DUPLICATE_CONSTRAINT_AUTHORITY`
- `BUY_ADD_SOFT_CAP_DOWNSTREAM_DUPLICATE_HARD_ENFORCEMENT`
- `CANONICAL_QUANTITY_MATERIALIZATION_BLOCKED_BEFORE_RUNTIME_PLANNING`

## Direct Halt Cause

Position Sizing final artifact generation blocked on:

```text
target_weight_above_position_cap:0
```

Runtime Planning then received no valid Position Sizing row for `94320`, emitted `planned_quantity = 0`, and Morning Planning Authority returned:

```text
strategy_plan_quantity_unresolved:94320
strategy_planning_authority_unresolved
```

## Target Symbol

`94320`, business date `2022-08-19`, run `runtime-test-historical-smoke-20260811T130548490709Z`.

## Required Trace Table

| Stage | Producer | Input target weight | Current weight | Desired target weight | Strategy cap | Safety hard cap | Lot quantity | Executable quantity delta | Final quantity delta | Overshoot applied | Status | Reason | Authority consumed |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| PM | Position Management | n/a | n/a | n/a | n/a | n/a | 900 current | n/a | n/a | n/a | PASS | `action=ADD` | PM intent only, no quantity authority |
| Portfolio Construction Draft | PC draft | n/a | 0.134514 | 0.18 | 0.18 | n/a | 900 current | n/a | n/a | NO | PASS | ADD eligibility PASS, `accepted_incremental_weight=0.045486` | Canonical ADD Allocation Bridge |
| Position Sizing Preflight | PS preflight | 0.18 | 0.134514 | 0.18 | 0.18 | 0.25 | requested lots 3, minimum policy lots 4 | 0 | n/a | YES | REVIEW_REQUIRED preflight row | `DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX`; requested notional below minimum executable notional | L19 lot resolution |
| Portfolio Construction Final | PC final | 0.18 | 0.134514 | 0.194658 | 0.18 | 0.25 | minimum policy lots 4 | 0 copied from preflight | 0 copied from preflight | YES | PASS | `LOT_AWARE_STRATEGY_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP`; accepted lot increment 0.060144 | L21D lot-aware final reallocation |
| Position Sizing Final | Position Sizing | 0.194658 | inferred row index 0 = 94320 | 0.194658 | effective max 0.18 | 0.25 | not materialized | not materialized | not materialized | not consumed | BLOCK | `target_weight_above_position_cap:0` | Position Sizing validator, per-position `maximum_position_weight` |
| Runtime Planning | Runtime Planning | PC target 0.194658 | current member exists | BUY_ADD intent | n/a | n/a | no PS row | null | null | not consumed | REVIEW_REQUIRED | `quantity_not_produced_due_to_upstream_block`; `planned_quantity=0` | Runtime Planning fallback / upstream block propagation |
| Morning Planning Authority | runtime_v2 planning authority | runtime plan BUY_ADD | current member exists | pending candidate | n/a | Safety authority BOUND NEUTRAL | none | none | none | not consumed | REVIEW_REQUIRED | `strategy_plan_quantity_unresolved:94320` | Strategy Planning Authority |

## Primary Question Answer

An item with `strategy_cap_overshoot_applied = true` and post-trade weight <= Safety hard cap still ends with unresolved quantity because L21D authorization is consumed by Portfolio Construction final target allocation, but not by Position Sizing final validation.

The artifact chain is:

1. PS preflight says the 18% target itself only requests 3 lots, while minimum executable policy requires 4 lots.
2. L21D correctly authorizes PC to promote the ADD from 0.045486 to 0.060144 weight, producing final target 0.194658.
3. PC preserves a misleading `final_quantity_delta = 0` by copying the preflight `executable_quantity_delta = 0`; this is observability, not final quantity authority.
4. PS final attempts to validate a position whose target weight is 0.194658 while `maximum_position_weight` remains 0.18.
5. `_validate_position` rejects it as `target_weight_above_position_cap:0`.
6. Runtime Planning has no valid PS quantity row, so it produces `BUY_ADD` from PM fallback but sets `planned_quantity = 0`.
7. Morning Planning Authority rejects the plan as `strategy_plan_quantity_unresolved:94320`.

## target_weight_above_position_cap Meaning

Exact producer:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py::validate_position_sizing_artifact
src/ai_fund_lab_v2/strategy/position_sizing.py::_validate_position
```

Exact source:

```text
target = position["target_weight"]
maximum = position["maximum_position_weight"]
if target > maximum + 0.000001 and no directional exception:
    errors.append(f"target_weight_above_position_cap:{index}")
```

Input values:

- target weight: `0.194658`
- position cap / `maximum_position_weight`: `0.18`
- Safety hard cap: `0.25`
- post-trade Safety margin from L21D evidence: `0.055342`

Meaning of `:0`:

`0` is the zero-based index of the offending `positions` item inside the would-be Position Sizing payload. In this run, Position Sizing had one active target row and index 0 corresponds to `94320`.

Which cap is referenced:

This is not the Safety hard cap. It is the Position Sizing per-position maximum, derived from:

```text
max_weight = min(config.strategy_maximum_position_weight, safety_cap)
```

With current config/evidence:

```text
min(0.18, 0.25) = 0.18
```

So the referenced cap is the effective Strategy/Position Sizing cap, not the independent Safety hard cap.

## Classification

Primary:

```text
C. Position Sizing contract does not consume L21D authorization
B. Duplicate hard-cap enforcement remains downstream
```

Secondary:

```text
D. Portfolio Construction evidence says allowed but canonical quantity materialization is not completed
```

Not primary:

```text
E. Runtime Planning is incorrectly rejecting valid zero/nonzero semantics
F. Observability-only mismatch
H. Different unrelated blocker
```

Runtime Planning is reacting to an upstream missing quantity authority, not rejecting a valid positive PS quantity.

## L21D Regression Assessment

L21D core semantics activated in real run: YES.

Evidence:

```text
participant_type = BUY_ADD
strategy_cap_overshoot_applied = true
lot_overshoot_reason = LOT_AWARE_STRATEGY_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP
post_trade_weight = 0.194658
safety_hard_cap = 0.25
safety_hard_cap_preserved = true
```

L21D produced a valid positive executable quantity: NO.

The PC target was promoted, but Position Sizing final blocked before a valid quantity artifact was emitted.

L21D regression confirmed: NO.

There is no evidence here that a previously working equivalent full integration was removed.

L21D incomplete integration confirmed: YES.

L21D allowed PC target overshoot but did not extend the Position Sizing final validator / cap exception contract to consume that authorization.

## Model Health Review

`MODEL_HEALTH_DIRECT_CAUSE = NO`.

Morning evidence includes `MODEL_HEALTH_REVIEW_REQUIRED` and `BASELINE_CURRENT_SEMANTICS_MISMATCH`, but:

```text
block_buy = false
block_buy_planning = false
buy_planning_permission = PASS
buy_submit_permission = PASS
```

The direct blocker in `strategy_shadow_summary.json` is Position Sizing, and the Morning Planning Authority direct reason is quantity unresolved.

## Safety Assessment

Safety hard cap breached: NO.

Safety blocked `94320`: NO.

Safety decision caused quantity zero: NO.

Evidence:

```text
post_trade_weight = 0.194658
safety_hard_cap = 0.25
safety_margin_after_trade = 0.055342
safety_authority = historical_initial_no_external_effect
safety_decision = NEUTRAL
```

## Architecture Concern

`DUPLICATE_CONSTRAINT_AUTHORITY = YES`.

Portfolio Construction is now authorized to treat Strategy cap as a lot-aware soft target for eligible existing `BUY_ADD`. Position Sizing final validation still treats the same Strategy-derived `maximum_position_weight = 0.18` as a hard invalidation boundary. This is not a new Safety block; it is a downstream duplicate hard enforcement of the Strategy target cap.

This is an authority integration gap between:

- Strategy target authority / PC lot-aware final reallocation
- Lot materialization authority / PS final quantity production
- Safety hard authority / independent 25% boundary

## Regression Search

Phase28-D55-B introduced the two-pass PC/PS lot-aware contract and explicitly kept:

```text
PS remains quantity authority
PC remains target-weight authority
```

L19 added explicit Strategy-vs-Safety lot boundary evidence but did not make Strategy cap soft.

L21D made PC consume the L19 boundary for eligible `BUY_ADD` overshoot. The remaining failing path is the Position Sizing final validator and `maximum_position_weight` contract. This is best classified as an incomplete integration / latent architecture gap, not a proven regression.

## Required Final Fields

```text
Primary Judgment:
PHASE29_L21E_BUY_ADD_SOFT_CAP_POSITION_SIZING_INTEGRATION_GAP_CONFIRMED_REPAIR_REQUIRED

Direct Halt Cause:
Position Sizing BLOCK target_weight_above_position_cap:0, propagated to Runtime Planning planned_quantity=0 and Morning strategy_plan_quantity_unresolved:94320

Target Symbol:
94320

L21D Core Semantics Activated:
YES

L21D Positive Quantity Materialized:
NO

Exact Zeroing Stage:
Runtime Planning sets planned_quantity=0 after Position Sizing final BLOCK; Position Sizing did not materialize a valid quantity row

Exact Zeroing Producer:
Runtime Planning _resolve_quantity_status for planned_quantity=0; root blocker is Position Sizing validator

Exact Zeroing Reason:
quantity_not_produced_due_to_upstream_block after target_weight_above_position_cap:0

target_weight_above_position_cap Meaning:
Position Sizing validation error; :0 is positions array index 0; cap is per-position maximum_position_weight 0.18 derived from min(strategy cap 0.18, safety cap 0.25), not Safety hard cap

Duplicate Constraint Authority YES/NO:
YES

Position Sizing Consumer Gap YES/NO:
YES

Runtime Planning Defect YES/NO:
NO

Safety Direct Cause YES/NO:
NO

Model Health Direct Cause YES/NO:
NO

L21D Regression Confirmed YES/NO:
NO

L21D Incomplete Integration YES/NO:
YES

Legacy Constraint Active YES/NO:
YES, the legacy/effective Position Sizing per-position hard cap remains active as a validator constraint for this L21D-authorized BUY_ADD overshoot

Recommended Repair Scope:
Extend Position Sizing final validation/materialization to consume the existing L21D/L19 lot-aware BUY_ADD overshoot authorization, allowing target > Strategy cap only when post-trade target <= Safety hard cap and all L21D eligibility evidence is present. Also stop copying preflight executable_quantity_delta=0 into PC final_quantity_delta as if it were final quantity authority, or relabel it as preflight-only evidence.

New Component Required YES/NO:
NO

Current Run Mutation:
NO

Long Historical Executed:
NO
```

## Read-Only Validation

Commands used were limited to read-only inspection:

- `sed` over required reports and source files
- `rg` for `target_weight_above_position_cap`, `executable_quantity_delta`, `final_quantity_delta`, `strategy_cap_overshoot_applied`, `strategy_plan_quantity_unresolved`, `upstream_block_propagation`
- `jq` over the halted run artifacts for `2022-08-19` / `94320`

No implementation, config edit, runtime mutation, resume, fresh-run, repair, pending lifecycle, abort, rollback, or long Historical execution was performed.
