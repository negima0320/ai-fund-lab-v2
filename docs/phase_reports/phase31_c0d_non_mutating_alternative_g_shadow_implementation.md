# Phase31-C0D — Non-Mutating Alternative G Shadow Implementation

Status: COMPLETE
Task type: IMPLEMENTATION — NON-MUTATING SHADOW ONLY

## PRIMARY_JUDGMENT

```text
PHASE31_C0D_NON_MUTATING_ALTERNATIVE_G_SHADOW_IMPLEMENTED
```

Alternative G was implemented only as a diagnostic Strategy / PM shadow. It does not mutate PM canonical action, PC, PS, Runtime Planning, Sell Planning, Pending, Submit, Execution, fills, Current, cash, exposure, valuation, portfolio membership, Safety, review behavior, BUY_NEW, BUY_ADD, REDUCE, or EXIT.

## Architecture

The implementation adds a standalone Strategy diagnostic producer:

```text
src/ai_fund_lab_v2/strategy/unrepresentable_reduce_exit_shadow.py
```

It reads existing PM / PS / Runtime Planning / Strategy Intelligence / Market Context artifacts and produces a non-authoritative shadow payload. It is not imported by production PM, PC, PS, Runtime Planning, Sell Planning, Pending, Submit, Execution, or Current.

SHADOW_PRODUCER:

```text
strategy.unrepresentable_reduce_exit_shadow
```

Primary functions:

```text
build_unrepresentable_reduce_exit_shadow_payload
write_unrepresentable_reduce_exit_shadow_artifact
materialize_unrepresentable_reduce_exit_shadow_for_day
materialize_unrepresentable_reduce_exit_shadow_for_run
```

SHADOW_SCHEMA_VERSION:

```text
phase31_c0d_unrepresentable_reduce_exit_shadow.v1
```

SHADOW_ARTIFACT_PATH:

```text
daily/<BUSINESS_DATE>/diagnostic_shadow/unrepresentable_reduce_exit_shadow.json
```

The artifact path is diagnostic and does not collide with canonical PM / PC / PS / Runtime artifacts.

## Input Authorities

Inputs are existing Production-visible PIT evidence only:

- `strategy/position_management.json` for baseline PM action, reduce intensity, PM reason evidence, and campaign id;
- `strategy/position_sizing.json` for current quantity, trading unit, target reduce ratio, raw/rounded/final reduce quantity, and `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`;
- `strategy/runtime_planning.json` for intentional no-order / runtime planning evidence;
- `strategy/strategy_intelligence.json` for existing Expected Edge, continuation, downside, recovery, and campaign evidence;
- `strategy/market_context.json` for canonical decision-time regime / market context.

The shadow does not create a new alpha feature and does not recompute a new deterioration score from raw prices.

## Shadow Semantics

Supported variants:

| Variant | Support |
|---|---|
| G0 baseline | YES |
| G1 immediate strong case | YES / structural |
| G2 persistent confirmation | YES / structural |
| G3 hybrid | YES / structural |

Required state families are materialized:

- `NOT_APPLICABLE`
- `REPRESENTABLE_REDUCE`
- `UNREPRESENTABLE_PRESERVE`
- `IMMEDIATE_EXIT_CANDIDATE`
- `PERSISTENT_EXIT_CANDIDATE`
- `RECOVERY_BLOCKED`
- `PARAMETER_UNRESOLVED`
- `EVIDENCE_INSUFFICIENT`

Persistent branch cases with prior fresh unrepresentable REDUCE history and current deterioration are intentionally `PARAMETER_UNRESOLVED` unless existing canonical semantics already resolve them. No persistence count, recent-window length, or deterioration cutoff was invented.

## Non-Mutation Proof

Required flags:

```text
ACTUAL_TRADING_PATH_MUTATED = NO
CANONICAL_PM_ACTION_MUTATED = NO
PS_EXIT_AUTHORITY_ADDED = NO
RUNTIME_EXIT_AUTHORITY_ADDED = NO
LOT_ROUNDING_CHANGED = NO
HIDDEN_REDUCE_DEBT_ADDED = NO
B10_BUSINESS_AUTHORITY_DEPENDENCY = NO
```

Focused materialization test copies one existing run day to a temp directory and confirms that `position_management.json`, `position_sizing.json`, and `runtime_planning.json` bytes are unchanged after shadow artifact creation. The output is written only under `diagnostic_shadow/`.

CANONICAL_TRADING_OUTPUT_EQUALITY:

```text
PASS
```

## PIT Proof

Each decision row includes:

- `decision_business_date`
- `feature_dates`
- `source_artifacts`
- `pit_validation_state`
- `future_information_used`
- `future_regime_used`
- `later_pnl_used`
- `final_campaign_outcome_used`

Required values:

```text
future_information_used = false
future_regime_used = false
later_pnl_used = false
final_campaign_outcome_used = false
```

Focused future-dated evidence test confirms future feature dates are marked `FAIL_FUTURE_DATED_EVIDENCE` and do not produce an EXIT candidate.

FUTURE_INFORMATION_USED:

```text
NO
```

## Persistence / Recovery

CAMPAIGN_SCOPED_PERSISTENCE:

```text
YES
```

Persistence is reconstructed from prior same-campaign fresh PM REDUCE decisions that were unrepresentable due to lot. The producer stores event dates and count only; it never accumulates desired shares and never creates hidden reduce debt.

RESTART_DETERMINISM:

```text
PASS
```

The same input artifacts and prior event set produce the same shadow state. No mutable in-memory-only counter is required for semantics.

RECOVERY_BLOCK_SUPPORTED:

```text
YES
```

The shadow can materialize `RECOVERY_BLOCKED` when prior unrepresentable REDUCE pressure exists but current PIT Strategy Intelligence indicates recovery, such as healthy continuation / ADD-allowed evidence.

## Production Consumer Isolation

Repository search found references only in:

- the new diagnostic producer module;
- the new focused tests.

PRODUCTION_CONSUMER_COUNT:

```text
0
```

No active production consumer reads this shadow output.

## Development Materialization

DEVELOPMENT_RUN_MATERIALIZED:

```text
NO
```

C0D did not materialize shadow artifacts across the full development run. This avoided writing many diagnostic files into the existing run. The implementation supports run/day materialization, and focused tests materialize one copied run day under a temp directory only.

## Focused Tests

Added:

```text
tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py
```

Coverage:

- one-lot unrepresentable REDUCE;
- representable multi-lot REDUCE;
- immediate branch structural candidate;
- persistent branch structural candidate with `PARAMETER_UNRESOLVED`;
- recovery block;
- existing PM EXIT non-interference;
- future-dated evidence PIT failure;
- canonical output equality for temp copied run day.

FOCUSED_TEST_RESULT:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase31_c0d_pycache python3 -m pytest -q tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py
8 passed in 0.10s
```

Focused existing regression:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase31_c0d_pycache python3 -m pytest -q \
  tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py \
  tests/strategy/test_phase22_j_position_sizing.py::test_phase28_d34_reduce_intensity_quantities_are_partial_sells \
  tests/strategy/test_phase22_g_runtime_planning.py::test_phase29_l21t_ad_runtime_planning_preserves_reduce_intentional_no_order_semantic
14 passed in 4.99s
```

COMPILE_RESULT:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase31_c0d_pycache python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/unrepresentable_reduce_exit_shadow.py \
  tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py
PASS
```

GIT_DIFF_CHECK:

```text
git diff --check -- src/ai_fund_lab_v2/strategy/unrepresentable_reduce_exit_shadow.py tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py
PASS
```

## Required Output Summary

SHADOW_PRODUCER:

```text
strategy.unrepresentable_reduce_exit_shadow
```

SHADOW_SCHEMA_VERSION:

```text
phase31_c0d_unrepresentable_reduce_exit_shadow.v1
```

SHADOW_ARTIFACT_PATH:

```text
daily/<BUSINESS_DATE>/diagnostic_shadow/unrepresentable_reduce_exit_shadow.json
```

ACTUAL_TRADING_PATH_MUTATED:

```text
NO
```

CANONICAL_PM_ACTION_MUTATED:

```text
NO
```

PS_EXIT_AUTHORITY_ADDED:

```text
NO
```

RUNTIME_EXIT_AUTHORITY_ADDED:

```text
NO
```

LOT_ROUNDING_CHANGED:

```text
NO
```

HIDDEN_REDUCE_DEBT_ADDED:

```text
NO
```

PRODUCTION_CONSUMER_COUNT:

```text
0
```

G0_SUPPORTED:

```text
YES
```

G1_SUPPORTED:

```text
YES
```

G2_SUPPORTED:

```text
YES
```

G3_SUPPORTED:

```text
YES
```

PARAMETER_UNRESOLVED_SUPPORTED:

```text
YES
```

RECOVERY_BLOCK_SUPPORTED:

```text
YES
```

CAMPAIGN_SCOPED_PERSISTENCE:

```text
YES
```

RESTART_DETERMINISM:

```text
PASS
```

PIT_PROOF_IMPLEMENTED:

```text
YES
```

FUTURE_INFORMATION_USED:

```text
NO
```

DEVELOPMENT_RUN_MATERIALIZED:

```text
NO
```

CANONICAL_TRADING_OUTPUT_EQUALITY:

```text
PASS
```

LONG_HISTORICAL_EXECUTED:

```text
NO
```

MUTATING_IMPLEMENTATION_AUTHORIZED:

```text
NO
```

## Limitations

- C0D does not tune or select persistence thresholds.
- C0D does not provide performance validation.
- C0D does not authorize mutating PM behavior.
- Development-run full-window materialization was not performed in this task.
- Deterioration and recovery classifications consume existing PM / Strategy Intelligence semantics; if future validation finds insufficient evidence, the correct output is `EVIDENCE_INSUFFICIENT`, not a new shadow alpha score.

## NEXT_TASK_RECOMMENDATION

```text
Phase31-C0E — Alternative G Shadow Structural Revalidation
```

Do not execute C0E in this task.

## Final Questions

### 1. Was Alternative G implemented only as a non-mutating shadow?

```text
YES
```

### 2. Can the shadow identify one-lot / lot-unrepresentable REDUCE without changing actual PM output?

```text
YES
```

### 3. Can it distinguish immediate and persistent Alternative G branches structurally?

```text
YES
```

### 4. Does it explicitly preserve unresolved parameters instead of inventing thresholds?

```text
YES
```

### 5. Can recovery evidence block escalation?

```text
YES
```

### 6. Is persistence campaign-scoped and based on fresh PM decisions rather than accumulated quantity debt?

```text
YES
```

### 7. Does any Production consumer use the new shadow output?

```text
NO
```

### 8. Was future outcome information used in the shadow decision?

```text
NO
```

### 9. Did canonical PM / PC / PS / Runtime / SELL / execution behavior remain unchanged?

```text
YES
```

### 10. Is Alternative G ready for mutating implementation after C0D alone?

```text
NO
```

### 11. What is the next task if C0D passes?

```text
Phase31-C0E — Alternative G Shadow Structural Revalidation
```
