# Phase31-F1D — Canonical SELL Semantic Shadow Implementation / Validation

Status: COMPLETE
Task type: NON-MUTATING SHADOW IMPLEMENTATION + PIT VALIDATION

## PRIMARY_JUDGMENT

```text
PHASE31_F1D_CANONICAL_SELL_SEMANTIC_SHADOW_MATERIALIZED_VALIDATION_PASS_MUTATION_CONDITIONAL
```

F1D implemented one non-mutating canonical SELL semantic shadow producer and materialized it on the current run. The shadow cleanly reproduces existing PM action semantics: HOLD/ADD map to `HEALTHY_OR_RECOVERING`, EXIT maps to `EXIT_GRADE`, and REDUCE splits into `WEAKENING_BUT_INTACT`, `PERSISTENT_DETERIORATION`, and `UNRESOLVED`.

No PM action, Production SELL behavior, threshold, score, weight, PS quantity, Runtime plan, Pending, Submit, or Execution behavior was changed.

## Implementation

```text
PRODUCER = strategy.canonical_sell_semantic_shadow
SCHEMA_VERSION = phase31_f1d_canonical_sell_semantic_shadow.v1
MODE = NON_MUTATING_SHADOW
ARTIFACT_PATH = daily/<DATE>/diagnostic_shadow/canonical_sell_semantic_shadow.json
```

Files added:

- `src/ai_fund_lab_v2/strategy/canonical_sell_semantic_shadow.py`
- `tests/strategy/test_phase31_f1d_canonical_sell_semantic_shadow.py`

The existing `unrepresentable_reduce_exit_shadow.py` remains the Alternative G representability/escalation shadow. F1D does not create a competing PM authority. It creates a canonical SELL semantic shadow that Alternative G can join read-only.

## Target

```text
TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260820T120909096218Z
TARGET_RUN_OR_ARTIFACT = reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260820T120909096218Z
TARGET_WINDOW = 2022-08-10 through 2022-10-12
BUSINESS_DAYS_MATERIALIZED = 42
```

Materialization wrote only:

```text
daily/<DATE>/diagnostic_shadow/canonical_sell_semantic_shadow.json
```

Source hash validation found:

```text
CANONICAL_ARTIFACT_SOURCE_HASH_MISMATCH_COUNT = 0
```

## State Distribution

```text
TOTAL_POSITION_DAY_ROWS = 458
HEALTHY_OR_RECOVERING_COUNT = 244
WEAKENING_BUT_INTACT_COUNT = 44
PERSISTENT_DETERIORATION_COUNT = 95
EXIT_GRADE_COUNT = 60
UNRESOLVED_COUNT = 15
UNRESOLVED_RATE = 3.28%
```

State distribution:

| Canonical SELL state | Count |
|---|---:|
| `HEALTHY_OR_RECOVERING` | 244 |
| `WEAKENING_BUT_INTACT` | 44 |
| `PERSISTENT_DETERIORATION` | 95 |
| `EXIT_GRADE` | 60 |
| `UNRESOLVED` | 15 |

All 15 unresolved rows are minimum-notional zero-REDUCE rows, which F1C intentionally kept as a separate unresolved policy family.

## PM Action Alignment

```text
PM_ACTION_SEMANTIC_ALIGNMENT = PASS
```

Cross-tab:

| PM action | HEALTHY_OR_RECOVERING | WEAKENING_BUT_INTACT | PERSISTENT_DETERIORATION | EXIT_GRADE | UNRESOLVED |
|---|---:|---:|---:|---:|---:|
| HOLD | 211 | 0 | 0 | 0 | 0 |
| ADD | 33 | 0 | 0 | 0 | 0 |
| REDUCE | 0 | 44 | 95 | 0 | 15 |
| EXIT | 0 | 0 | 0 | 60 | 0 |

This preserves the F1C rule:

```text
AGGREGATE_PASS_SEMANTICS = EVIDENCE_AVAILABLE_NOT_HEALTH_SIGNAL
```

`continuation_quality_status = PASS` and `downside_risk_status = PASS` are never used alone as `HEALTHY_OR_RECOVERING` or as an EXIT blocker.

## EXIT Controls

```text
PM_EXIT_COUNT = 60
EXIT_GRADE_ALIGNMENT_COUNT = 60
EXIT_GRADE_MISALIGNMENT_COUNT = 0
EXIT_CONTROL_ALIGNMENT = PASS
```

All current PM EXIT rows were mapped to `EXIT_GRADE` from same-day PM EXIT-grade reason families:

- `trend_and_opportunity_broken`
- `weak_hold_score`
- `profit_retention_break`
- `hard_stop_current_return`

No later outcome was used.

## REDUCE Controls

```text
PM_REDUCE_COUNT = 154
```

REDUCE state distribution:

| REDUCE canonical SELL state | Count |
|---|---:|
| `WEAKENING_BUT_INTACT` | 44 |
| `PERSISTENT_DETERIORATION` | 95 |
| `EXIT_GRADE` | 0 |
| `UNRESOLVED` | 15 |

REDUCE is not automatically persistent. A REDUCE row reaches `PERSISTENT_DETERIORATION` only when campaign-scoped prior unrepresentable REDUCE exists, current REDUCE remains unrepresentable, current deterioration evidence is present, recovery guard is absent, and PIT proof passes.

## Persistent Campaigns

```text
PERSISTENT_CAMPAIGN_COUNT = 29
PERSISTENT_STATE_REACHED_CAMPAIGN_COUNT = 26
EXIT_GRADE_REACHED_CAMPAIGN_COUNT = 25
RECOVERY_RESET_CAMPAIGN_COUNT = 19
UNRESOLVED_PERSISTENT_CAMPAIGN_COUNT = 4
```

The `EXIT_GRADE_REACHED_CAMPAIGN_COUNT` is a mapped campaign-level observation across the materialized window. Each daily state itself remains same-day PIT-only. The count does not select thresholds or use later outcome to label an earlier day.

## Recovery Controls

```text
RECOVERY_CONTROL_COUNT = 17
RECOVERY_CONTROL_FALSE_PERSISTENT_COUNT = 0
RECOVERY_CONTROL_FALSE_EXIT_GRADE_COUNT = 0
WINNER_PROTECTION_SEMANTIC_GATE = PASS
```

The 17 recovery-control campaigns were identified from later HOLD/ADD only as controls. The shadow state for each day was computed from PIT evidence available on that business date. Across 112 recovery rows after prior REDUCE, all mapped to `HEALTHY_OR_RECOVERING`; none mapped to `PERSISTENT_DETERIORATION` or `EXIT_GRADE`.

## 61750

```text
61750_PERSISTENT_STATE_FIRST_DATE = 2022-09-14
61750_EXIT_GRADE_FIRST_DATE = NONE
```

61750 state sequence:

| Date | Canonical SELL state | Parameter status |
|---|---|---|
| 2022-09-13 | `WEAKENING_BUT_INTACT` | `CANONICAL_EXISTING` |
| 2022-09-14 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-09-15 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-09-16 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-09-20 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-09-21 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-09-22 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-09-26 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-09-27 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-09-28 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-09-29 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-09-30 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-10-03 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-10-04 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-10-05 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-10-06 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-10-07 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-10-11 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |
| 2022-10-12 | `PERSISTENT_DETERIORATION` | `UNRESOLVED_FOR_EXIT` |

61750 does not reach same-day `EXIT_GRADE`. The shadow makes persistent deterioration visible, but still does not authorize mutation because F1C parameters remain unresolved.

## Alternative G Integration Preview

```text
ALTERNATIVE_G_PERSISTENT_EXIT_CANDIDATE_COUNT = 95
ALTERNATIVE_G_EXIT_GRADE_CANDIDATE_COUNT = 0
```

These are read-only candidate counts where:

```text
PM REDUCE
+ REDUCE unrepresentable
+ canonical state = PERSISTENT_DETERIORATION or EXIT_GRADE
+ recovery guard absent
+ PIT proof complete
```

No PM action was changed. These rows remain candidate evidence for a later PM-owned design.

## Minimum-Notional

```text
MINIMUM_NOTIONAL_STATE_DISTRIBUTION = UNRESOLVED: 15
MINIMUM_NOTIONAL_POLICY_CHANGED = NO
```

F1D maps minimum-notional rows but does not merge them into discrete-lot Alternative G escalation policy.

## Production Isolation

```text
PRODUCTION_CONSUMER_COUNT = 0
CANONICAL_ARTIFACT_MUTATION_COUNT = 0
FUTURE_INFORMATION_USED_FOR_SHADOW = NO
OUTCOME_USED_FOR_PARAMETER_SELECTION = NO
MARKET_CONTEXT_LOGIC_CHANGED = NO
LONG_HISTORICAL_EXECUTED = NO
```

Repository consumer search found `canonical_sell_semantic_shadow` references only in:

- the new shadow producer;
- the focused F1D tests.

No production PM, PC, PS, Runtime, Pending, Submit, Execution, Ledger, or Safety consumer reads the shadow.

## Verification

Focused tests:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase31_f1d_pycache python3 -m pytest -q \
  tests/strategy/test_phase31_f1d_canonical_sell_semantic_shadow.py \
  tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py

19 passed in 0.22s
```

Compile:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase31_f1d_pycache python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/canonical_sell_semantic_shadow.py \
  tests/strategy/test_phase31_f1d_canonical_sell_semantic_shadow.py

PASS
```

Materialization:

```text
BUSINESS_DAYS_MATERIALIZED = 42
CANONICAL_ARTIFACT_SOURCE_HASH_MISMATCH_COUNT = 0
```

## Required Output

```text
PRIMARY_JUDGMENT = PHASE31_F1D_CANONICAL_SELL_SEMANTIC_SHADOW_MATERIALIZED_VALIDATION_PASS_MUTATION_CONDITIONAL
TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260820T120909096218Z
BUSINESS_DAYS_MATERIALIZED = 42
TOTAL_POSITION_DAY_ROWS = 458
HEALTHY_OR_RECOVERING_COUNT = 244
WEAKENING_BUT_INTACT_COUNT = 44
PERSISTENT_DETERIORATION_COUNT = 95
EXIT_GRADE_COUNT = 60
UNRESOLVED_COUNT = 15
UNRESOLVED_RATE = 3.28%
PM_ACTION_SEMANTIC_ALIGNMENT = PASS
PM_EXIT_COUNT = 60
EXIT_GRADE_ALIGNMENT_COUNT = 60
EXIT_GRADE_MISALIGNMENT_COUNT = 0
EXIT_CONTROL_ALIGNMENT = PASS
PM_REDUCE_COUNT = 154
REDUCE_STATE_DISTRIBUTION = WEAKENING_BUT_INTACT: 44; PERSISTENT_DETERIORATION: 95; EXIT_GRADE: 0; UNRESOLVED: 15
PERSISTENT_CAMPAIGN_COUNT = 29
PERSISTENT_STATE_REACHED_CAMPAIGN_COUNT = 26
EXIT_GRADE_REACHED_CAMPAIGN_COUNT = 25
RECOVERY_RESET_CAMPAIGN_COUNT = 19
UNRESOLVED_PERSISTENT_CAMPAIGN_COUNT = 4
RECOVERY_CONTROL_COUNT = 17
RECOVERY_CONTROL_FALSE_PERSISTENT_COUNT = 0
RECOVERY_CONTROL_FALSE_EXIT_GRADE_COUNT = 0
WINNER_PROTECTION_SEMANTIC_GATE = PASS
61750_STATE_SEQUENCE = 2022-09-13 WEAKENING_BUT_INTACT; 2022-09-14 through 2022-10-12 PERSISTENT_DETERIORATION / UNRESOLVED_FOR_EXIT
61750_PERSISTENT_STATE_FIRST_DATE = 2022-09-14
61750_EXIT_GRADE_FIRST_DATE = NONE
ALTERNATIVE_G_PERSISTENT_EXIT_CANDIDATE_COUNT = 95
ALTERNATIVE_G_EXIT_GRADE_CANDIDATE_COUNT = 0
MINIMUM_NOTIONAL_STATE_DISTRIBUTION = UNRESOLVED: 15
PRODUCTION_CONSUMER_COUNT = 0
CANONICAL_ARTIFACT_MUTATION_COUNT = 0
FUTURE_INFORMATION_USED_FOR_SHADOW = NO
OUTCOME_USED_FOR_PARAMETER_SELECTION = NO
MARKET_CONTEXT_LOGIC_CHANGED = NO
LONG_HISTORICAL_EXECUTED = NO
MUTATING_PM_IMPLEMENTATION_READY = CONDITIONAL
NEXT_TASK_RECOMMENDATION = Phase31-F1E PM canonical SELL semantic integration / Alternative G mutating implementation design
```

## Final Questions

1. F1CのSELL semanticをcurrent runへ安定してmaterializeできたか？

   Yes. 42 business days and 458 PM position-day rows were materialized.

2. 既存EXIT 60件をEXIT_GRADEとして再現できたか？

   Yes. `EXIT_GRADE_ALIGNMENT_COUNT = 60`, `EXIT_GRADE_MISALIGNMENT_COUNT = 0`.

3. REDUCE 154件をWEAKENING/PERSISTENTへ意味的に分離できたか？

   Yes. 44 are `WEAKENING_BUT_INTACT`, 95 are `PERSISTENT_DETERIORATION`, and 15 minimum-notional rows remain `UNRESOLVED`.

4. recovery Winnerを誤ってPERSISTENT/EXIT_GRADEにしていないか？

   No. Recovery rows after prior REDUCE had zero false persistent and zero false EXIT-grade mappings.

5. persistent 29 campaignをPIT-onlyで追跡できたか？

   Yes. 29 persistent campaigns were identified; 26 reached persistent state and 4 retained unresolved family evidence.

6. 61750はどこまで悪化stateが進んだか？

   61750 reached `PERSISTENT_DETERIORATION` from 2022-09-14, but never reached `EXIT_GRADE`.

7. Alternative Gが実際に使えるEXIT candidateをPIT-onlyで作れそうか？

   Conditionally yes. 95 persistent candidates are visible, but PM mutation still requires parameter/acceptance design.

8. 次にPMの実売買判断へ接続してよい状態か？

   Not directly. The next step should be PM integration / mutating implementation design, not immediate behavior mutation.
