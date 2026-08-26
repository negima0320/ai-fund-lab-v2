# Phase31-G61 — Lot-Aware Allocation-to-Sizing Compatibility Layer

## Primary Judgment

PHASE31_G61_LOT_AWARE_ALLOCATION_TO_SIZING_COMPATIBILITY_LAYER_ACCEPTED

G60 の blocker `LOT_AWARE_PRIORITY_INVERSION_AFTER_DISCRETE_100_SHARE_CONVERSION`
は、authoritative binding 前の shadow compatibility evidence として解消した。

## Scope

実装は Portfolio Construction の
`canonical_multi_allocation_deployment_set.v1` 内に
`portfolio_construction.lot_aware_allocation_to_sizing_compatibility.v1`
を追加する範囲に限定した。

Unchanged:

- G59 multi-allocation remains `SHADOW_NON_AUTHORITATIVE`
- Position Sizing remains the discrete quantity owner
- Candidate ranking / eligibility authority
- Market Quality / Risk Pacing semantics
- Position Sizing trading behavior
- Runtime order behavior
- Safety behavior
- Threshold / weight / Historical outcome-derived parameterization

No fresh run, resume, replay, or long Historical was executed.

## Implementation

Changed:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py`

Added schema:

- `portfolio_construction.lot_aware_allocation_to_sizing_compatibility.v1`

The compatibility layer consumes optional decision-time sizing context:

- `portfolio_value`
- `reference_price`
- 100-share `trading_unit` / canonical lot quantity
- `current_weight`
- `single_name_cap`
- `safety_hard_cap`
- `effective_maximum_position_weight`

For each G59 security allocation it records:

- minimum executable lot weight
- cap headroom
- executable-before-residual-reallocation status
- projected quantity delta as evidence only
- explicit residual capital when an allocation is lot-infeasible
- whether lower-priority execution requires explicit residual resolution

The projected quantity is diagnostic only:

- `position_sizing_quantity_owner = POSITION_SIZING`
- `pc_discrete_quantity_authority = False`
- `authorized_for_position_sizing = False`
- `authorized_for_runtime_order = False`

## Semantic Repair

G60 showed that direct conversion of G59 continuous allocations to 100-share
lots could make a lower-ranked cheap security executable while a higher-ranked
expensive security became zero quantity.

G61 does not make PC the final quantity owner. Instead it makes the unresolved
high-priority allocation explicit:

- lot-infeasible higher-priority rows become `LOT_INFEASIBLE_RESIDUAL_REQUIRED`
  or `CAP_HEADROOM_INSUFFICIENT`
- their capital becomes explicit residual evidence
- lower-priority executable rows are marked as requiring explicit residual
  resolution when any higher-priority row is unresolved
- `lower_priority_implicit_promotion_allowed = False`
- `priority_inversion_after_compatibility = False`

This prevents a lower-priority candidate from silently becoming the effective
winner merely because the higher-priority candidate did not fit one 100-share
lot.

## Real-PIT Sanity

Source run:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260822T174358377089Z`

Window:

- `2022-10-03` through `2022-10-19`
- 12 business dates

Method:

Existing PIT artifacts were read only. Current G61 code was applied in memory
using same-date PC draft members and same-date Position Sizing / Portfolio
Policy sizing context. No runtime artifact was mutated.

Results:

- Dates evaluated: `12`
- Shadow security allocation rows: `126`
- Rows executable before residual reallocation: `31`
- Compatibility executable rows: `31`
- Multi-executable dates: `11`
- All-zero collapse dates: `0`
- ADD rows: `5`
- ADD insufficient-context failures: `0`
- Raw priority inversion dates: `11`
- Post-compatibility priority inversion dates: `0`
- Lower-priority implicit promotion dates: `0`
- Residual-explicit dates: `12`
- Future input count: `0`
- Historical outcome input count: `0`
- Position Sizing behavior change count: `0`
- Runtime order change count: `0`

Representative examples:

| Date | Higher-priority unresolved | Lower executable before compatibility |
| --- | --- | --- |
| `2022-10-03` | rank 1 `58200`, rank 2 `41920` | rank 3 `76470` |
| `2022-10-05` | rank 1 `39060` | rank 2 `76920` |
| `2022-10-07` | rank 1 `39060`, rank 3 `36000` | rank 2 `76920` |
| `2022-10-17` | rank 1 `39060`, rank 2 `78780`, rank 3 `92270` | lower-priced later rows |
| `2022-10-19` | rank 1 `39060`, rank 3 `78780` | rank 2 `76920` |

These remain raw lot feasibility facts, but no longer become implicit capital
priority promotions after G61 compatibility evidence is applied.

## Acceptance

LOT_AWARE_PRIORITY_INVERSION = NO

TOP_PRIORITY_PRESERVATION = materially improved by explicit residual gating.

EXECUTABLE_MULTI_SECURITY = YES

ALL_ZERO_COLLAPSE = NO

RESIDUAL_CAPITAL_EXPLICIT = YES

LOWER_PRIORITY_IMPLICIT_PROMOTION = NO

ADD_COMPATIBILITY = PASS

CAPITAL_CONSERVATION = PASS

PS_QUANTITY_AUTHORITY_PRESERVED = YES

RUNTIME_ORDER_CHANGE_COUNT = 0

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_STRATEGY_INPUT_COUNT = 0

## Focused Regression

Command:

`PYTHONPATH=src python3 -m pytest tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py tests/strategy/test_phase31_g59_within_class_allocation_evidence.py tests/strategy/test_phase31_g57_multi_allocation_shadow.py`

Result:

`12 passed in 0.17s`

## Py Compile

Command:

`PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py`

Result:

PASS

Note: direct `python3 -m py_compile` attempted to write under the macOS user
cache and was blocked by sandbox permissions. The retry used a temp pycache
location and passed.

## Git Diff Check

GIT_DIFF_CHECK = PASS

The worktree already contained many prior Phase31 changes. The G61 scoped
changes are limited to:

- PC shadow compatibility evidence in `portfolio_construction.py`
- G61 focused tests
- this report

## Required Flags

PHASE31_CONTINUES = YES

G59_MULTI_ALLOCATION_AUTHORITY_STATUS = SHADOW_NON_AUTHORITATIVE

PS_BEHAVIOR_CHANGE_COUNT = 0

RUNTIME_ORDER_CHANGE_COUNT = 0

CANDIDATE_RANK_AUTHORITY_MUTATION = NO

CANDIDATE_ELIGIBILITY_AUTHORITY_MUTATION = NO

MARKET_QUALITY_SEMANTICS_CHANGED = NO

RISK_PACING_SEMANTICS_CHANGED = NO

FUTURE_INFORMATION_USED = NO

HISTORICAL_OUTCOME_USED_FOR_PARAMETERS = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

## Next

PHASE31_G62_AUTHORITATIVE_MULTI_ALLOCATION_ACTIVATION_POSITION_SIZING_BINDING_READINESS

Proceed only by binding this compatibility evidence explicitly into Position
Sizing. Do not let Position Sizing infer lower-priority promotion from ordinary
lot feasibility alone.
