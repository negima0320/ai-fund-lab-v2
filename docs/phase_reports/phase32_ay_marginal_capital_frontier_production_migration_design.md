# Phase32-AY - Marginal Capital Frontier Production Migration Design

## Executive Summary

Phase32-AY defines the production migration design for the shadow frontier
accepted through Phase32-AX:

```text
canonical_marginal_capital_frontier.v1
```

No production code, config, threshold, model, runtime state, fresh-run, resume,
replay, backtest, or current-run control was changed or executed.

Primary design judgment:

```text
Production authority should migrate to a Portfolio Construction-owned common marginal capital value / target-gap authority.
The shadow structured partial-order artifact is not sufficient by itself as production target authority.
A production cardinal-value or bounded deterministic target-allocation contract is required before Position Sizing can consume accepted increments.
```

The target production path is:

```text
PM ADD intent
-> PC-owned common marginal capital competition
-> accepted incremental target / target gap
-> existing Position Sizing target-to-quantity conversion
-> existing Runtime Planning / Pending / Orders / Execution
```

Fixed 200/300-share rules, fixed ADD multipliers, fixed position count, and
Historical outcome selected parameters remain forbidden.

## Evidence Base

Read:

- `docs/phase_reports/phase32_ax_broad_fresh_run_shadow_frontier_acceptance.md`
- `docs/phase_reports/phase32_ar_shadow_common_marginal_capital_value_add_next_lot_architecture_design.md`
- `docs/phase_reports/phase32_aq_add_scarcity_marginal_capital_value_target_gap_root_architecture_audit.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

Locked inherited facts:

| Source | Accepted fact |
| --- | --- |
| AQ | ADD scarcity is primarily `PM ADD intent -> positive accepted incremental target weight / target gap`, not PS lot rounding. |
| AR | The right object is a PC-owned common marginal frontier across NEW / REENTRY / ADD / Cash. |
| AS/AU | The shadow artifact is deterministic, PIT-safe, fail-closed, and non-authoritative. |
| AX | 44-day fresh-run shadow characterization showed Cash resolver PASS on all days, ADD lot #1/#2/#3+ broad surface, guardrails preserved, and production migration readiness `PARTIAL`. |

AX counts used as migration design evidence:

| Metric | Value |
| --- | ---: |
| Characterized days | 44 |
| NEW winners | 33 |
| REENTRY winners | 7 |
| ADD winners | 4 |
| Cash winners | 0 |
| ADD candidates | 141 |
| ADD lot #1/#2/#3+ candidates | 47 / 47 / 47 |
| Production target-gap=0 and shadow ADD winner days | 4 |
| Production consumer count | 0 |

## Authority Ownership

| Layer | Production migration stance |
| --- | --- |
| PM | KEEP as existing-position intent / continuation / ADD evidence producer. PM does not own capital quantity, target weight, or final ADD admission. |
| Candidate / Opportunity / BUY Quality | KEEP as PIT evidence. No outcome-derived score tuning. |
| Portfolio Construction | MIGRATE to own common marginal capital value and accepted target-gap authority. |
| Position Sizing | KEEP as target-to-discrete-quantity authority. It consumes accepted target / incremental target only after PC emits production authority. |
| Runtime Planning | KEEP. Runtime maps PS quantity deltas; it must not recompute capital priority. |
| Pending / Orders / Execution | KEEP. They consume Runtime / Submit decisions only. |
| Safety | KEEP as hard authority. Safety blocks must remain binding. |
| Risk Pacing | KEEP as deployment posture / hard block where already authoritative. |
| REDUCE / EXIT | KEEP. No weakening or migration in AY. |
| Cash | KEEP as first-class capital alternative, not residual. |

## Production Artifact Design

AY recommends a new production artifact rather than promoting the shadow artifact
in place:

```text
canonical_marginal_capital_frontier_authority.v1
```

Owner:

```text
PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY
```

Required status:

```text
PRODUCTION_AUTHORITATIVE
PIT_SAFE
DETERMINISTIC
FAIL_CLOSED
MODE_COMPATIBLE
```

Required artifact-level fields:

| Field | Requirement |
| --- | --- |
| `schema_name` | fixed production authority schema name |
| `schema_version` | versioned independent of shadow v1 |
| `authority_owner` | `PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY` |
| `business_date` / `session` / `run_id` | same-date identity |
| `frontier_input_refs` | PC / PM / candidate / quality / market / safety / risk / cash refs and hashes |
| `cash_source_status` / `cash_source_lineage` | AU resolver lineage preserved |
| `candidate_frontier` | all candidates considered, including losers and infeasible rows |
| `accepted_incremental_targets` | authoritative per-symbol target increments emitted to PS |
| `target_gap_authority` | accepted target-minus-current by symbol/campaign |
| `cash_disposition` | first-class Cash outcome |
| `guardrail_decisions` | cap / Cash / Safety / Risk Pacing / lot / no-loss-averaging decisions |
| `review_required_reasons` | fail-closed blockers |
| `production_consumer_eligibility` | eligible only when all contracts pass |
| `legacy_path_migration_state` | no permanent fallback after migration |

The shadow artifact may continue as an observability artifact, but it must remain
non-authoritative.

## Partial-Order vs Cardinal Contract

AY judgment:

```text
Shadow structured partial-order is production-safe as explanation and candidate ranking evidence only.
It is not production-safe as final target authority.
```

Reason:

- PS requires concrete accepted target / incremental target fields.
- Runtime requires deterministic quantity deltas, not ambiguous comparisons.
- A partial-order result can validly express near-comparable / review states;
  production target authority cannot silently choose through ambiguity.
- Production must allocate scarce capital across multiple selected candidates,
  not only explain a single shadow winner.

Therefore a production migration must add one of:

1. `canonical_marginal_capital_value.v1`, a cardinal marginal value object with
   transparent bounded components; or
2. a deterministic bounded ordinal-to-target allocation contract that maps
   dominance classes to accepted target gaps without hidden coefficients.

Preferred AY direction:

```text
canonical_marginal_capital_value.v1 required before production activation
```

The cardinal contract must be PIT-only and evidence based. It may use existing
decision-time fields such as opportunity score, quality, rank, continuation,
recovery, trend/momentum state, current/post-lot weight, headroom, Cash, Safety,
and Risk Pacing. It must not use future returns, realized fills, PnL, or
Historical winner labels to choose weights, coefficients, or thresholds.

## Candidate / Lot Contract

Production candidates:

```text
NEW_FIRST_LOT
REENTRY_FIRST_LOT
ADD_NEXT_LOT
CASH_OPTIONALITY
```

Each candidate represents one executable marginal capital unit.

ADD production sequence:

1. Generate ADD lot #1 for every eligible existing campaign with PM ADD evidence.
2. Compare lot #1 against NEW, REENTRY, other ADD lot #1 candidates, and Cash.
3. If an ADD lot is accepted, recompute hypothetical state:
   - quantity;
   - notional;
   - portfolio weight;
   - remaining Cash;
   - single-name headroom;
   - concentration pressure;
   - safety / risk context.
4. Generate / evaluate the next ADD lot for that campaign only under the
   recomputed state.
5. Stop when the next lot loses, is blocked, Cash wins, budget/headroom is
   exhausted, evidence becomes ambiguous, or a non-investment engineering bound
   is reached.

Forbidden shortcuts:

- fixed 200/300 shares;
- fixed ADD multiplier;
- fixed number of lots;
- fixed position count;
- PS-side priority recomputation;
- Runtime-side priority recomputation.

## Accepted Incremental Target Contract

PC must emit production target authority in a form PS already understands:

| Field family | Meaning |
| --- | --- |
| `target_weight` | authoritative final target weight after accepted increments |
| `current_weight` | same-date starting weight |
| `accepted_incremental_weight` | authoritative accepted increment from the frontier |
| `target_minus_current` / `target_gap` | explicit target gap for PS conversion |
| `accepted_incremental_notional` | optional explanatory notional |
| `accepted_frontier_candidate_ids` | lineage to accepted marginal candidates |
| `capital_value_authority` | PC owner / method / artifact refs |
| `target_weight_reason_codes` | why the candidate won, lost, or was blocked |

PS remains responsible for:

- lot rounding;
- tradable quantity conversion;
- current quantity baseline;
- executable quantity delta;
- no order generation when PC accepted target gap is zero.

## Guardrails

The production frontier must preserve:

- single-name cap / headroom;
- Cash / buying power feasibility;
- Safety hard blocks;
- Risk Pacing blocks where currently authoritative;
- lot feasibility;
- no-loss-averaging rejection;
- downside and concentration evidence;
- missing/stale evidence fail-closed behavior;
- campaign identity requirements for ADD;
- prior-exit / recovery requirements for REENTRY.

No guardrail may be converted into a soft score contribution when it is already
a hard production constraint.

## Legacy Path Classification

| Existing path | Classification | Notes |
| --- | --- | --- |
| PM ADD intent producer | KEEP | Evidence only. |
| Existing PC target-weight builder | MIGRATE | Becomes consumer of production capital-value authority or hosts it directly. |
| Existing ADD allocation bridge / target-gap zero path | DEPRECATE after migration | Keep during shadow/dual-read; no permanent fallback after acceptance. |
| Existing canonical multi-allocation deployment set | MIGRATE | Should receive common frontier accepted increments instead of type-local compression. |
| Existing PS target-to-quantity conversion | KEEP | Must remain quantity authority. |
| Runtime Planning | KEEP | No capital priority recomputation. |
| Pending / Submit / Execution | KEEP | No authority change. |
| REDUCE / EXIT | KEEP | Defensive behavior unchanged. |
| Shadow `canonical_marginal_capital_frontier.v1` | KEEP as diagnostic | Must not become production consumer directly. |

Fallback rule:

```text
During migration validation, old and new paths may run side-by-side for comparison.
After accepted migration, production must not silently fallback to legacy ADD compression.
If production authority fails, fail closed to REVIEW_REQUIRED / no new deployment rather than fallback.
```

## Consumer Switch Design

Recommended switch phases:

| Phase | Scope |
| --- | --- |
| AY1 | Implement production candidate/value artifact with production consumer disabled. |
| AY2 | Dual-read PC comparison: old target path remains authoritative; new production-shaped artifact emits candidate accepted targets as diagnostic. |
| AY3 | Authority gate: validate cardinal value, target-gap, guardrails, determinism, and fail-closed behavior. |
| AY4 | PC consumer switch: PC target weights consume `accepted_incremental_targets` from capital frontier authority. |
| AY5 | PS compatibility validation: PS consumes unchanged target fields and produces quantity deltas. |
| AY6 | Runtime short fresh validation. |
| AY7 | Longer Historical/Demo characterization before Production activation. |

Switch invariant:

```text
Only PC target-gap authority changes.
PS / Runtime / Pending / Orders / Execution / Safety contracts remain stable.
```

## Rollback Boundary

Rollback unit:

```text
Portfolio Construction capital-value authority consumer switch
```

Rollback must restore the prior PC target-gap source before PS. Rollback must
not alter PM, PS, Runtime, Pending, Orders, Execution, Safety, REDUCE, EXIT,
Cash policy, or thresholds.

Fail-closed production behavior:

- missing capital-value artifact: `REVIEW_REQUIRED`;
- ambiguous candidate ordering/value: `REVIEW_REQUIRED`;
- missing Cash source: `REVIEW_REQUIRED`;
- missing campaign identity for ADD: `REVIEW_REQUIRED`;
- missing prior-exit/recovery evidence for REENTRY: not eligible / review
  according to the existing REENTRY contract;
- Safety / Risk Pacing hard block: ineligible;
- insufficient Cash / cap/headroom breach: infeasible.

## Focused Regression Plan

Required implementation tests before any production switch:

- NEW first-lot accepted target emitted;
- REENTRY first-lot accepted target emitted;
- ADD lot #1 accepted target emitted;
- ADD lot #1/#2/#N sequential generation and stop condition;
- post-lot Cash / weight / headroom recomputation;
- Cash wins and creates no security target gap;
- cap blocked;
- insufficient Cash blocked;
- Safety block;
- Risk Pacing block;
- no-loss-averaging block;
- missing campaign identity fail-closed;
- missing Cash fail-closed;
- ambiguous same-priority Cash fail-closed;
- ambiguous cross-type value fail-closed;
- deterministic rerun;
- PIT future/outcome fields rejected;
- PS consumes accepted target without logic changes;
- Runtime maps PS quantity delta without priority recomputation;
- production consumer count for shadow artifact remains 0;
- old ADD bridge cannot silently fallback after production switch.

## Validation Plan

Short fresh validation:

```text
First run with PC authority switch enabled should be short and monitored.
Acceptance should be semantic and contract-based, not performance-based.
```

Acceptance gates:

- production capital frontier artifact generated;
- PC accepted target gaps sourced from frontier authority;
- PM remains evidence only;
- PS quantity conversion unchanged;
- Runtime / Pending / Execution lineage preserved;
- NEW / REENTRY / ADD / Cash competition visible;
- ADD lot #1/#2/#N sequential recomputation visible;
- guardrails preserved;
- fail-closed cases block rather than fallback;
- no future outcome fields;
- no fixed 200/300 shares, ADD multiplier, or position count.

Longer validation:

- continue the current long run;
- repeat artifact-only shadow/dual-read characterization;
- only use performance as post-hoc characterization, not parameter selection.

## Production Migration Readiness

Implementation readiness:

```text
PARTIAL
```

Ready:

- authority boundary is clear;
- production target-gap owner is identified as PC;
- PM / PS / Runtime / Safety keep boundaries are clear;
- ADD multi-lot sequential semantics are defined;
- guardrail and fail-closed contracts are defined;
- legacy path migration classification is defined.

Not ready for direct activation:

- production cardinal / bounded target-allocation value contract is not yet
  implemented;
- accepted target emission contract is not yet validated;
- consumer switch tests do not yet exist;
- short fresh validation has not yet run under a production-shaped authority.

## Final Judgments

PHASE32_AY_PRODUCTION_AUTHORITY_DEFINED = YES

PHASE32_AY_PARTIAL_ORDER_PRODUCTION_SAFE = PARTIAL

PHASE32_AY_CARDINAL_VALUE_REQUIRED = YES

PHASE32_AY_ADD_MULTI_LOT_AUTHORITY_DEFINED = YES

PHASE32_AY_GUARDRAILS_PRESERVED_BY_DESIGN = YES

PHASE32_AY_LEGACY_PATH_MIGRATION_DEFINED = YES

PHASE32_AY_IMPLEMENTATION_READY = PARTIAL

PHASE32_AY_PRODUCTION_CHANGE_THIS_TASK = NO

PHASE32_AY_LONG_RUN_CONTINUE = YES

PHASE32_AY_NEXT_STEP = Phase32-AZ production-shaped cardinal marginal capital value / accepted target-gap authority implementation behind a disabled consumer switch; keep shadow non-authoritative and do not activate production consumption until a later acceptance phase.
