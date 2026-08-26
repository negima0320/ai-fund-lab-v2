# Phase31-F1A — Current-Run Non-Mutating Alternative G Shadow Validation

Status: COMPLETE
Task type: NON-MUTATING SHADOW MATERIALIZATION + PIT VALIDATION

## PRIMARY_JUDGMENT

```text
PHASE31_F1A_ALTERNATIVE_G_REFINEMENT_STILL_REQUIRED
```

F1A applied the refined Alternative G shadow to the current run without mutating production behavior. The current run reproduces the F0/F1 structure: every PM REDUCE remains zero-quantity, discrete-lot and minimum-notional families are separable, persistence is visible, and recovery protection does not falsely EXIT recovery controls.

However, the current PIT evidence does not resolve any current-run REDUCE row into an EXIT shadow action. This is the correct fail-closed result under F1: persistence is structurally present, but escalation sufficiency remains parameter-unresolved and must not be inferred from later outcomes.

## Target

```text
TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260820T120909096218Z
TARGET_RUN_OR_ARTIFACT = reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260820T120909096218Z
TARGET_WINDOW = 2022-08-10 through 2022-10-12
BUSINESS_DAYS_MATERIALIZED = 42
SHADOW_ARTIFACT_PATH = daily/<DATE>/diagnostic_shadow/unrepresentable_reduce_exit_shadow.json
```

F1A reused and refined the existing shadow producer:

```text
src/ai_fund_lab_v2/strategy/unrepresentable_reduce_exit_shadow.py
```

No second competing shadow authority was created.

## Shadow Refinement

The C0D shadow was refined to expose F1A-required current-run evidence while preserving the non-mutating architecture:

- `representability_family`
- `representability_reason`
- `reduce_unrepresentable`
- `reduce_unrepresentable_due_to_minimum_notional`
- `one_lot_position`
- `minimum_notional_flag`
- `zero_reduce_count`
- `discrete_lot_count`
- `minimum_notional_count`
- `shadow_exit_count`
- `shadow_hold_or_preserve_count`

Immediate branch was also tightened so `STRONG` REDUCE alone does not create EXIT. Immediate EXIT now requires EXIT-grade PIT deterioration evidence such as canonical EXIT-grade reason families or deteriorating/insufficient expected-edge evidence.

## Current Structural Counts

| Metric | Count |
|---|---:|
| PM_REDUCE_COUNT | 154 |
| ZERO_REDUCE_COUNT | 154 |
| DISCRETE_LOT_COUNT | 139 |
| MINIMUM_NOTIONAL_COUNT | 15 |
| ONE_LOT_COUNT | 131 |
| IMMEDIATE_BRANCH_COUNT | 0 |
| PERSISTENT_BRANCH_COUNT | 94 |
| RECOVERY_BLOCKED_COUNT | 2 |
| PARAMETER_UNRESOLVED_COUNT | 108 |
| SHADOW_EXIT_COUNT | 0 |
| SHADOW_HOLD_OR_PRESERVE_COUNT | 154 |

Family split:

| Family | Rows | Interpretation |
|---|---:|---|
| DISCRETE_LOT | 139 | Core Alternative G scope |
| MINIMUM_NOTIONAL | 15 | Adjacent unresolved family; separated from discrete-lot |

Current-run shadow therefore reproduces the unrepresentable REDUCE population, but does not authorize any actual EXIT candidate.

## Recovery Protection

```text
RECOVERY_CONTROL_COUNT = 17
RECOVERY_CONTROL_FALSE_ESCALATION_COUNT = 0
WINNER_PROTECTION_SHADOW_GATE = PASS
```

The 17 recovery-control campaigns identified in F1 were checked against current shadow output. No shadow EXIT was generated for those controls. The gate blocks blind escalation because unrepresentability alone is insufficient; PIT recovery-compatible evidence, HOLD/ADD-compatible evidence, or unresolved deterioration sufficiency preserves the position.

This uses later HOLD/ADD only to identify control campaigns. The shadow classifications themselves use same-day and prior PIT evidence only.

## Persistent Campaigns

```text
PERSISTENT_CAMPAIGN_COUNT = 29
EXIT_ELIGIBLE_PIT_CAMPAIGN_COUNT = 0
PERSISTENT_UNRESOLVED_CAMPAIGN_COUNT = 28
RECOVERY_PROTECTED_CAMPAIGN_COUNT = 1
```

Campaign classes:

| Class | Campaigns |
|---|---:|
| PERSISTENT_UNRESOLVED | 28 |
| RECOVERY_PROTECTED | 1 |
| EXIT_ELIGIBLE_PIT | 0 |
| IMMEDIATE_EXIT_ELIGIBLE_PIT | 0 |
| INSUFFICIENT_EVIDENCE | 0 |

Representative persistent campaigns:

| Symbol | REDUCE rows | First unrepresentable REDUCE | Family | Final class |
|---|---:|---|---|---|
| 61750 | 19 | 2022-09-13 | DISCRETE_LOT | PERSISTENT_UNRESOLVED |
| 83060 | 9 | 2022-08-16 | DISCRETE_LOT | PERSISTENT_UNRESOLVED |
| 32710 | 8 | 2022-09-07 | DISCRETE_LOT | PERSISTENT_UNRESOLVED |
| 43760 | 8 | 2022-08-26 | DISCRETE_LOT | PERSISTENT_UNRESOLVED |
| 68360 | 8 | 2022-09-07 | DISCRETE_LOT | PERSISTENT_UNRESOLVED |
| 39890 | 7 | 2022-08-31 | DISCRETE_LOT | PERSISTENT_UNRESOLVED |
| 54010 | 7 | 2022-08-16 | DISCRETE_LOT | PERSISTENT_UNRESOLVED |
| 33500 | 6 | 2022-09-30 | DISCRETE_LOT + MINIMUM_NOTIONAL | PERSISTENT_UNRESOLVED |
| 89180 | 6 | 2022-08-12 | MINIMUM_NOTIONAL | PERSISTENT_UNRESOLVED |
| 27880 | 5 | 2022-08-31 | DISCRETE_LOT | RECOVERY_PROTECTED |

Persistent pressure is real, but current canonical PIT evidence does not semantically resolve persistent escalation into EXIT without still-unset parameters.

## 61750 Control

```text
61750_REDUCE_ROWS = 19
61750_SHADOW_EXIT_DATE = NONE
```

61750 trace:

| Date | Family | Shadow state | Branch | Shadow action |
|---|---|---|---|---|
| 2022-09-13 | DISCRETE_LOT | UNREPRESENTABLE_PRESERVE | NONE | PRESERVE |
| 2022-09-14 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-09-15 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-09-16 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-09-20 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-09-21 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-09-22 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-09-26 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-09-27 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-09-28 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-09-29 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-09-30 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-10-03 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-10-04 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-10-05 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-10-06 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-10-07 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-10-11 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |
| 2022-10-12 | DISCRETE_LOT | PARAMETER_UNRESOLVED | PERSISTENT | PRESERVE |

61750 never reaches an EXIT-eligible shadow state in the current window. The first persistent structural date is 2022-09-14, but final escalation remains unresolved. No later delisting, later price, or later PnL was used.

## Immediate Branch

```text
IMMEDIATE_EXIT_ELIGIBLE_COUNT = 0
```

The current run contains `STRONG` REDUCE rows, but the same-day REDUCE reasons are `peak_drawdown_warning` or `risk_increased_but_trend_not_broken`, not canonical EXIT-grade PM reasons. EXIT-grade families exist on baseline PM EXIT rows, but F1A does not reinterpret REDUCE as EXIT from intensity alone.

## Persistence Sufficiency

```text
PERSISTENCE_SEMANTICALLY_RESOLVABLE = PARTIAL
```

Resolvable:

- same-campaign prior unrepresentable REDUCE;
- discrete-lot versus minimum-notional family;
- one-lot state;
- persistent structural branch;
- recovery-protected structural branch;
- PIT proof and no future evidence usage.

Still unresolved:

- persistence minimum;
- recent-window length;
- deterioration sufficiency beyond PM REDUCE reason;
- recovery reset versus decay strength;
- representation-error materiality;
- minimum-notional materiality;
- whether `continuation_quality_status = PASS` and `downside_risk_status = PASS` should block, decay, or merely annotate persistence when PM still emits REDUCE.

## Minimum-Notional

```text
MINIMUM_NOTIONAL_POLICY_READY = NO
```

Minimum-notional cases are now visible as a distinct family, but the policy is not ready for mutation. Unlike one-lot discrete-lot cases, these rows can have positive rounded sell quantity while final sell quantity remains zero because the notional gate blocks execution. They require a separate notional-feasibility/materiality design before sharing the discrete-lot escalation policy.

## Non-Mutation And Consumer Isolation

```text
PRODUCTION_CONSUMER_COUNT = 0
CANONICAL_ARTIFACT_MUTATION_COUNT = 0
FUTURE_INFORMATION_USED_FOR_SHADOW = NO
OUTCOME_USED_FOR_PARAMETER_SELECTION = NO
LONG_HISTORICAL_EXECUTED = NO
```

Canonical artifacts hash-compared before and after materialization:

- `strategy/position_management.json`
- `strategy/position_sizing.json`
- `strategy/runtime_planning.json`
- `strategy/strategy_intelligence.json`
- `strategy/market_context.json`
- `strategy/portfolio_construction.json`
- `morning/pending_generation_evidence.json`
- `execution/fills.json`

No hash changed. Materialization wrote only `diagnostic_shadow/unrepresentable_reduce_exit_shadow.json`.

Repository consumer search found only:

- `src/ai_fund_lab_v2/strategy/unrepresentable_reduce_exit_shadow.py`
- `tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py`
- phase reports

No production PM / PC / PS / Runtime / Pending / Submit / Execution consumer reads the shadow.

## Verification

Focused tests:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase31_f1a_pycache python3 -m pytest -q tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py
9 passed in 0.12s
```

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase31_f1a_pycache python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/unrepresentable_reduce_exit_shadow.py \
  tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py
PASS
```

## Required Output

```text
PRIMARY_JUDGMENT = PHASE31_F1A_ALTERNATIVE_G_REFINEMENT_STILL_REQUIRED
TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260820T120909096218Z
BUSINESS_DAYS_MATERIALIZED = 42
PM_REDUCE_COUNT = 154
ZERO_REDUCE_COUNT = 154
DISCRETE_LOT_COUNT = 139
MINIMUM_NOTIONAL_COUNT = 15
ONE_LOT_COUNT = 131
IMMEDIATE_BRANCH_COUNT = 0
PERSISTENT_BRANCH_COUNT = 94
RECOVERY_BLOCKED_COUNT = 2
PARAMETER_UNRESOLVED_COUNT = 108
SHADOW_EXIT_COUNT = 0
RECOVERY_CONTROL_COUNT = 17
RECOVERY_CONTROL_FALSE_ESCALATION_COUNT = 0
PERSISTENT_CAMPAIGN_COUNT = 29
EXIT_ELIGIBLE_PIT_CAMPAIGN_COUNT = 0
PERSISTENT_UNRESOLVED_CAMPAIGN_COUNT = 28
61750_SHADOW_EXIT_DATE = NONE
PERSISTENCE_SEMANTICALLY_RESOLVABLE = PARTIAL
WINNER_PROTECTION_SHADOW_GATE = PASS
MINIMUM_NOTIONAL_POLICY_READY = NO
PRODUCTION_CONSUMER_COUNT = 0
CANONICAL_ARTIFACT_MUTATION_COUNT = 0
FUTURE_INFORMATION_USED_FOR_SHADOW = NO
OUTCOME_USED_FOR_PARAMETER_SELECTION = NO
LONG_HISTORICAL_EXECUTED = NO
MUTATING_IMPLEMENTATION_READY = NO
```

## NEXT_TASK_RECOMMENDATION

```text
Phase31-F1A-R focused refinement
```

Do not proceed directly to mutating implementation. The next work should refine semantic deterioration sufficiency and minimum-notional policy while preserving the current non-mutating shadow gate.

## FINAL QUESTIONS

1. Current runでもAlternative Gの構造は再現したか？

   Yes. 154 REDUCE / 154 zero REDUCE, 139 discrete-lot, 15 minimum-notional, 29 persistent campaigns were materialized.

2. Winner/recoveryを誤EXITせずに守れたか？

   Yes. Recovery-control false escalation count is 0.

3. persistent deteriorationをPITだけでEXIT候補まで分離できたか？

   No. Persistent branch is visible, but EXIT eligibility remains unresolved.

4. 61750は本当にEXIT可能なPIT stateまで進んだか？

   No. 61750 remains `PARAMETER_UNRESOLVED` after the first preserve row; `61750_SHADOW_EXIT_DATE = NONE`.

5. persistence thresholdなしでも十分なsemantic separationがあるか？

   Partial. Structural persistence is separable, but production EXIT sufficiency still needs unresolved parameters.

6. minimum-notionalを同じpolicyへ入れてよいか？

   No. It is now separated and should receive focused policy review.

7. 次にmutating implementationへ進める証拠は揃ったか？

   No. Proceed to F1A-R focused refinement first.
