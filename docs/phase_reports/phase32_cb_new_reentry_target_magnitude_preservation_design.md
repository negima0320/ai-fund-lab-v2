# Phase32-CB - NEW/REENTRY Target-Magnitude Preservation Design

## Executive Summary

Phase32-CB defines a design-only production migration for preserving
NEW/REENTRY target magnitude inside the BG/BF common marginal capital frontier.

Phase32-CA showed that BV/BZ restored first-lot admission and ADD discipline,
but NEW/REENTRY initial sizing can still be compressed. The active authority
currently emits one `NEW_FIRST_LOT` or `REENTRY_FIRST_LOT` row per symbol. For
high-priced names, one lot often preserves PC target notional. For lower-priced
names, PC may already have a positive target and executable quantity for
multiple lots, while BF only passes one 100-share lot to PS.

The design below migrates existing PC target magnitude into the common frontier:

```text
PC production admission
-> PC target weight / executable quantity authority
-> NEW/REENTRY lot #1/#2/#N candidate expansion up to PC target quantity
-> NEW/REENTRY/ADD/Cash common capital competition
-> BF aggregated PS target
-> Position Sizing target-to-quantity conversion
```

This is not a rollback to the old NEW path. It is a formal transplantation of
PC-owned target magnitude into the new common frontier. No production code,
config, threshold, model, runtime state, fresh-run, resume, replay, or backtest
was changed or executed in this task.

## Required Inputs

Read:

- `docs/phase_reports/phase32_ca_new_conviction_target_weight_semantic_preservation_audit.md`
- `docs/phase_reports/phase32_bv_new_reentry_production_admission_semantic_restoration.md`
- `docs/phase_reports/phase32_bz_add_admission_bf_only_authority_narrow_repair.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`

Relevant SoT constraints:

- Portfolio Construction owns target weight / target allocation.
- Position Sizing consumes accepted target allocation and converts to notional /
  discrete quantity.
- Position Sizing and Runtime must not reinterpret rank, quality, opportunity,
  target weight, or capital priority.
- BG/BF switched rows are the only production PC-to-PS target authority.
- Legacy target-gap fallback and legacy zero fallback remain forbidden.

## Problem Statement

Current BG/BF authority behavior after BV/BZ:

- BV: blocks legacy PC `target_weight = 0` NEW/REENTRY promotion.
- BZ: blocks ADD unless authoritative ADD evidence is PASS and enforces BF-only
  ADD consumption.
- Remaining issue: admitted NEW/REENTRY can be reduced to exactly one first-lot
  candidate even when existing PC evidence says the initial target supports
  multiple executable lots.

Phase32-CA evidence:

- 56/56 nonzero first-lot PS outputs were 100 shares.
- 39/56 accepted rows preserved at least 95% of PC target notional because one
  lot was economically close to PC target.
- 17/56 accepted rows preserved less than 50% of PC target notional.
- The compression point was `NEW_FIRST_LOT` authority/BF target generation, not
  PS arithmetic or Runtime mapping.

## Design Goal

Preserve PC decision-time target magnitude for NEW/REENTRY without changing the
authority ownership model:

- PC target magnitude remains the hard upper authority.
- The common frontier decides how much of that authorized target is actually
  accepted under budget, Cash, cap, Safety, Risk Pacing, and marginal value.
- PS remains a converter from accepted target to quantity.
- Runtime remains a mapper from PS quantity to execution intent.

## Semantic Separation

NEW multi-lot and ADD multi-lot are separate concepts.

| Type | Meaning | Admission Source | Upper Bound |
| --- | --- | --- | --- |
| NEW multi-lot | Capitalizing entry-time PC conviction that already exists at first entry | BV first-lot production admission plus PC target magnitude | PC target executable quantity |
| REENTRY multi-lot | Capitalizing entry-time PC conviction after prior full exit and valid re-entry context | BV first-lot production admission plus re-entry admission plus PC target magnitude | PC target executable quantity |
| ADD multi-lot | Additional investment after entry based on fresh ADD evidence | BZ ADD PASS-only evidence plus campaign identity | ADD evidence/cap/budget sequence |

NEW/REENTRY lot #2 is not an ADD. It has no prior entry fill yet in the same
decision surface; it is simply the second lot of the initial target that PC has
already authorized.

## Authority Source for Target Quantity

The authoritative upper quantity for NEW/REENTRY lot expansion should be resolved
from existing PC and lot evidence in priority order:

1. `phase29_l19_lot_resolution.pc_positive_executable_quantity_authority`
   when status is PASS, semantic type is `BUY_NEW` or `REENTRY`, and PIT flags
   are explicit.
2. `phase29_l19_lot_resolution.executable_quantity_delta` when the lot
   resolution status is PASS and it is derived from PC `target_weight`.
3. `target_weight * portfolio_total_equity / reference_price`, rounded down to
   trading unit, only when target weight authority, reference price authority,
   and trading unit authority are all PASS.

The resolved quantity is a hard upper bound:

```text
0 <= sum(accepted NEW/REENTRY lots for symbol) <= pc_target_executable_quantity
```

If the sources disagree materially, are missing, stale, future-dated, lack source
hashes, or lack explicit PIT flags, the candidate fails closed as
`REVIEW_REQUIRED`.

## Candidate Expansion Contract

For each BV-admitted `NEW_FIRST_LOT` or `REENTRY_FIRST_LOT`, the authority
generates a deterministic lot ladder:

```text
NEW_TARGET_LOT or REENTRY_TARGET_LOT
symbol
semantic_type = NEW_TARGET_LOT / REENTRY_TARGET_LOT
entry_lot_index = 1..N
pre_quantity = trading_unit * (entry_lot_index - 1)
increment_quantity = trading_unit
post_quantity = trading_unit * entry_lot_index
increment_notional = reference_price * trading_unit
increment_weight = increment_notional / portfolio_total_equity
pc_target_executable_quantity = hard upper quantity
pc_target_weight = hard upper weight
```

Generation stops before exceeding any of:

- PC target executable quantity;
- PC target weight;
- effective Strategy cap;
- Safety hard cap;
- valid reference price/trading unit evidence;
- available Cash/budget feasibility for the candidate lot;
- deterministic max lot count derived from PC target quantity, not a fixed
  position-count rule.

Example:

```text
PC target executable quantity = 400
trading_unit = 100

Generate lot #1: 0 -> 100
Generate lot #2: 100 -> 200
Generate lot #3: 200 -> 300
Generate lot #4: 300 -> 400
Do not generate lot #5.
```

High-priced one-lot names naturally generate one lot because PC target
executable quantity is one trading unit.

## Competition Contract

Each expanded lot independently enters the same budget-bounded frontier as ADD
and Cash:

```text
NEW_TARGET_LOT #1
NEW_TARGET_LOT #2
REENTRY_TARGET_LOT #1
ADD_NEXT_LOT #1
CASH_OPTIONALITY
...
```

Acceptance is sequential:

1. Sort by bounded marginal capital value and deterministic tie rules.
2. Check sequence readiness:
   - NEW/REENTRY lot #1 must be accepted before lot #2 can compete.
   - lot #N must be accepted before lot #N+1 can compete.
   - ADD retains its existing campaign-specific sequence readiness.
3. Accept one lot only if it beats Cash/alternative under the existing
   competition contract.
4. Recompute remaining budget, Cash, position weight, headroom, concentration,
   and capital conservation after each accepted lot.
5. Stop when Cash wins, budget is exhausted, cap/Safety/Risk Pacing blocks,
   target quantity is reached, or evidence becomes ambiguous.

Budget consumption alone must never force an extra lot. A lot is accepted only
because it wins the marginal competition and passes all constraints.

## Capital Value Semantics

The design does not introduce performance-tuned thresholds or future-outcome
weights.

For v1 implementation, later lots for the same NEW/REENTRY target should inherit
the same decision-time selection evidence but receive explicit diminishing /
headroom context from the hypothetical post-lot state:

- PC target remaining fraction;
- post-lot weight vs PC target weight;
- post-lot headroom to Strategy cap and Safety cap;
- remaining Cash/budget after prior accepted lots;
- strongest available alternative;
- Cash comparison.

No lot may exceed the PC target magnitude. Repeated initial lots are not
evidence of fresh strengthening; they are partial capitalization of one existing
PC target decision.

## REENTRY

REENTRY uses the same target-magnitude preservation mechanism after it passes
the existing re-entry semantic/admission gates:

- strict prior context where required;
- cooldown/recovery/continuation/downside gates where applicable;
- BV first-lot production admission;
- PC positive target weight;
- PC executable quantity evidence.

The generated lots are `REENTRY_TARGET_LOT` rows, not ADD rows. They do not use
ADD evidence and do not create an ADD campaign. Once filled, later future
incremental investment would be governed by ADD PASS-only evidence under BZ.

## ADD Same-Day Competition

If a day has NEW/REENTRY target lots and ADD next lots, all lots compete in one
common frontier.

Rules:

- NEW/REENTRY lots are bounded by PC initial target magnitude.
- ADD lots are bounded by ADD evidence, current campaign state, cap, Cash, and
  budget.
- NEW lot #2 cannot skip NEW lot #1.
- ADD lot #2 cannot skip ADD lot #1.
- A NEW/REENTRY lot and an ADD lot may alternate in the acceptance sequence if
  marginal value supports it.
- Cash can stop all remaining lots.

This preserves the common capital competition while preventing type-specific
priority hacks.

## BF Aggregation

BF aggregates accepted lots by symbol and semantic entry campaign:

```text
symbol
semantic_type = NEW_FIRST_LOT or REENTRY_FIRST_LOT for PS compatibility
accepted_lot_count
accepted_increment_indexes
current_quantity = 0
final_quantity_delta = sum(accepted lot quantities)
final_target_quantity = final_quantity_delta
accepted_incremental_weight = sum(accepted lot weights)
final_target_weight = accepted_incremental_weight
pc_target_executable_quantity
pc_target_weight
pc_target_magnitude_preserved_status
source_frontier_candidate_ids
source_pc_evidence_ids
legacy_target_gap_fallback_allowed = false
legacy_zero_fallback_allowed = false
```

For example, if lots #1, #2, and #3 win but lot #4 loses to Cash:

```text
pc_target_executable_quantity = 400
accepted_lot_count = 3
final_quantity_delta = 300
final_target_quantity = 300
```

This is valid because the hard upper bound is 400, not a requirement to accept
all four lots.

## PS Consumer Contract

Position Sizing remains the quantity conversion owner, but under BG/BF it must
consume the BF aggregated target as the only switched target authority.

Required PS behavior:

- If BF target exists and is PASS, consume `final_quantity_delta` and
  `final_target_weight`.
- Preserve `pc_positive_executable_quantity_authority` PIT fields.
- Emit `quantity_delta_candidate = final_quantity_delta`.
- Do not recompute capital priority or add extra lots.
- If BF target is missing/invalid for a switched row, fail closed or zero per
  the existing BF-only contract; never use legacy target-gap fallback.

This does not change PS arithmetic. It changes what PC/BF passes to PS.

## Duplicate / Double Allocation Prevention

The authority must enforce:

- one generated lot identity per `(business_date, symbol, semantic_type,
  entry_lot_index, source_pc_target_id)`;
- no duplicate accepted lot index per symbol;
- accepted lot indexes are contiguous from 1;
- `sum(accepted_quantity) <= pc_target_executable_quantity`;
- `sum(accepted_weight) <= pc_target_weight + tolerance`;
- NEW/REENTRY accepted quantity and ADD accepted quantity cannot share the same
  campaign identity;
- existing-position ADD cannot be generated for a no-position NEW row;
- NEW/REENTRY target lots cannot be generated for an existing-position ADD row.

Any duplicate, campaign collision, non-contiguous sequence, source conflict, or
quantity/weight mismatch is `REVIEW_REQUIRED`.

## Fail-Closed Conditions

Fail closed as `REVIEW_REQUIRED` when:

- BV production admission is not PASS;
- PC target weight is missing, zero, negative, stale, future-dated, or not PASS;
- reference price or trading unit evidence is missing/stale/future-dated;
- target quantity sources conflict;
- PC target executable quantity is not divisible by trading unit;
- lot expansion would exceed PC target quantity or PC target weight;
- cap evidence is missing/ambiguous;
- Cash/budget evidence is missing/ambiguous;
- source hashes/lineage are missing where required;
- historical outcome/PnL fields are present as inputs;
- BF aggregation cannot prove capital conservation;
- PS consumer would need legacy fallback to produce quantity.

Block as infeasible rather than review when evidence is valid but a lot violates:

- effective Strategy cap;
- Safety hard cap;
- Cash feasibility;
- allocation budget;
- Risk Pacing;
- Cash/alternative marginal value comparison.

## Migration Plan

Design-only migration stages:

1. Extend shadow/authority candidate materialization to generate NEW/REENTRY
   target lots up to PC target quantity.
2. Preserve the existing `NEW_FIRST_LOT` / `REENTRY_FIRST_LOT` PS-facing
   semantic names in BF aggregation for compatibility, while internal candidates
   use explicit lot indexes.
3. Extend frontier sequence readiness for NEW/REENTRY lot indexes.
4. Extend BF validation to require contiguous NEW/REENTRY accepted lot indexes
   and hard upper target checks.
5. Keep PS consumer unchanged except for accepting multi-lot BF quantity deltas
   for NEW/REENTRY exactly as it already accepts aggregated ADD deltas.
6. Add focused regressions before any fresh validation.
7. User-operated short fresh validation after implementation.

## Test Design

Minimum focused regressions for implementation:

- PC target executable quantity 400 -> generate lots #1/#2/#3/#4 only.
- Lot #5 is not generated and cannot be accepted.
- Low-priced NEW with PC 400 shares can accept multiple lots if they win
  competition.
- High-priced NEW with PC one-lot target remains one lot.
- REENTRY target magnitude expands the same way after REENTRY admission PASS.
- BV legacy-zero NEW remains blocked and generates no lots.
- BZ ADD FAIL_CLOSED remains blocked.
- ADD PASS multi-lot remains preserved and separate from NEW/REENTRY lots.
- NEW/REENTRY lot #2 cannot be accepted if lot #1 loses.
- Cash beats lot #N and stops remaining lots.
- Cap crossing lot is blocked while earlier lots can pass.
- Strategy 18% cap and Safety 25% cap are both preserved.
- Budget exhaustion creates explicit Cash residual / budget stop.
- Duplicate lot index fail-closed.
- PC target quantity conflict fail-closed.
- Historical outcome field injection fail-closed.
- BF aggregation emits PS-compatible net quantity.
- PS consumes BF net quantity with legacy fallback still zero.
- Deterministic rerun produces identical payload.

## Production Boundary

No production change was made in this task.

Do not change:

- PM;
- ADD admission thresholds;
- rank/quality/marginal-value weights;
- Cash policy;
- allocation budget policy;
- Strategy/Safety cap values;
- Risk Pacing;
- PS arithmetic;
- Runtime mapping;
- Pending/Orders/Execution;
- REDUCE/EXIT;
- fixed position count or fixed target count.

## Implementation Readiness

The design is implementation-ready at the PC authority/BF boundary. The main
open implementation detail is schema naming:

- keep external BF target semantic as `NEW_FIRST_LOT` / `REENTRY_FIRST_LOT` for
  PS compatibility;
- add internal lot-indexed candidate type or fields, such as
  `first_lot_expansion_index` and `pc_target_magnitude_authority`.

No additional cardinal score design is required for v1. Existing marginal value
can rank each lot, while diminishing/headroom context is recomputed per
hypothetical post-lot state.

## Final Judgments

PHASE32_CB_PC_TARGET_MAGNITUDE_AUTHORITY_DEFINED = YES

PHASE32_CB_NEW_MULTI_LOT_DESIGN_DEFINED = YES

PHASE32_CB_REENTRY_MULTI_LOT_DESIGN_DEFINED = YES

PHASE32_CB_NEW_ADD_SEMANTICS_SEPARATED = YES

PHASE32_CB_COMMON_CAPITAL_COMPETITION_PRESERVED = YES

PHASE32_CB_BV_BZ_GUARDRAILS_PRESERVED = YES

PHASE32_CB_DOUBLE_ALLOCATION_PREVENTED = YES

PHASE32_CB_IMPLEMENTATION_READY = YES

PHASE32_CB_PRODUCTION_CHANGE_THIS_TASK = NO

PHASE32_CB_NEXT_STEP = Implement NEW/REENTRY target-magnitude lot expansion inside the PC-owned marginal frontier authority and BF aggregation, consumer-compatible and guarded by focused regressions before user-operated fresh validation.
