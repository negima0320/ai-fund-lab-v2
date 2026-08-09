# Phase28-D18: PM ADD Strategy PM Propagation Runtime-Run Mismatch Root Cause Diagnosis

## Primary Judgment

```text
PHASE28_D18_D12_RUNTIME_WIRING_GAP_CONFIRMED_D19_READY
```

Phase28-D18 was read-only. No implementation, config, schema, threshold, resume, fresh run, long historical run, or Runtime mutation was performed.

Target run:

```text
runtime-test-historical-smoke-20260806T053322547871Z
```

## Root Cause

The D12 normalizer is present in `src/ai_fund_lab_v2/strategy/position_management.py`, but the actual fresh historical runtime path does not pass the same-day PM ADD row into Strategy Position Management.

Exact root cause:

```text
Formal morning Strategy PM generation runs before same-day sell_planning PM producer.
Strategy PM input selection looks for same-day runtime PM artifacts.
Therefore existing_pm_decisions is empty when Strategy PM is produced.
The D12 helper receives an empty decision mapping for runtime-current rows, not the PM ADD row.
```

This is a Runtime path / input selection wiring defect, not a Phase28-C ADD bridge defect and not a Portfolio Construction defect.

## Runtime Path

Actual entrypoint:

```text
python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --job morning
```

Actual Strategy PM producer:

```text
ai_fund_lab_v2.strategy.position_management.produce_position_management_artifact
```

Actual adapter:

```text
_positions_from_runtime_current
```

Actual PM input lookup:

```text
ai_fund_lab_v2.strategy.shadow_runtime._existing_pm_decisions
```

Lookup candidates:

```text
.runtime/runtime_state/sell_pipeline/<business_date>/position_management_decisions.json
.runtime/runtime_state/position_management/<business_date>/position_management_decisions.json
```

Actual Strategy PM output:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260806T053322547871Z/daily/<business_date>/strategy/position_management.json
```

Code evidence:

```text
run_daily_operation.py:617-648
morning job generates formal Strategy artifacts.

run_daily_operation.py:715-725
sell_planning job later produces Runtime PM decisions.

shadow_runtime.py:226-234
Strategy PM receives _existing_pm_decisions(...) and runtime_current_positions.

shadow_runtime.py:1344-1354
_existing_pm_decisions searches same-date PM runtime artifacts.

position_management.py:278-288
existing_pm_decisions are copied, then _positions_from_runtime_current is used.

position_management.py:1305-1323
decisions_by_symbol is built; empty lookup yields decision = {}.

position_management.py:1339-1356
missing decision emits runtime_current_position_requires_strategy_pm_evaluation and empty source_pm_decision_ref.
```

## Representative ADD Trace

Three representative ADD rows were checked: early, middle, and late.

Observed shape for all samples:

```text
position_management/pm_decisions.json
decision_type = ADD
pm_decision_id = present

strategy/position_management.json
action = UNRESOLVED
source_pm_decision_ref = ""
reason_codes = ["runtime_current_position_requires_strategy_pm_evaluation"]
adapter_source = runtime_current_position_adapter
```

The Strategy PM artifact records Runtime Current as source:

```text
.runtime/persistent_ledger/state.json
```

It does not record `position_management_decisions.json` as a source artifact role for these cases.

## All 51 ADD Classification

```text
PM ADD count: 51
Strategy PM ADD count: 0
All 51 same root cause: YES
```

Classification:

| Classification | Count |
|---|---:|
| STRATEGY_PM_INPUT_SELECTION_EMPTY_PM_DECISIONS | 51 |

First loss point:

```text
STRATEGY_JOB_INPUT_SELECTION
```

Last artifact where ADD exists:

```text
daily/<business_date>/position_management/pm_decisions.json
```

First artifact where ADD is absent:

```text
daily/<business_date>/strategy/position_management.json
```

## D12 Fixture vs Actual Runtime

| Attribute | D12 Fixture | Actual Runtime |
|---|---|---|
| input container | `existing_pm_decisions` list supplied directly | same-day PM lookup is empty during formal morning Strategy generation |
| symbol field | present | present in later PM snapshot, not present in Strategy PM input |
| decision_type | `ADD` present | `ADD` exists later, absent from Strategy PM input |
| pm_decision_id | present | exists later, absent from Strategy PM input |
| current position source | runtime current rows plus PM rows | runtime current rows only |
| adapter invoked | `_positions_from_runtime_current` with populated PM rows | `_positions_from_runtime_current` with empty PM rows |
| decision lookup | `decisions_by_symbol` contains ADD | `decisions_by_symbol` empty |
| output action | `ADD` | `UNRESOLVED` |

D12 repaired the field-normalization gap, but the focused fixture did not reproduce the actual runtime timing/input-selection condition.

## BUY_ADD Zero Causality

Direct causality is confirmed:

```text
PM ADD exists after sell_planning
↓
Formal Strategy PM has no same-day PM decision input
↓
Strategy PM emits UNRESOLVED
↓
Portfolio Construction receives pm_action=UNRESOLVED
↓
Phase28-C ADD bridge is not reached
↓
Runtime Planning emits zero BUY_ADD
↓
Pending / Submit / Fill BUY_ADD remain zero
```

Phase28-C defect:

```text
NO
```

D12 defect:

```text
PARTIAL
```

Meaning: D12 normalizer is not the broken code path, but D12 regression did not cover the real runtime ordering/input-selection path.

Runtime wiring defect:

```text
YES
```

## Cash Utilization Relation

Judgment:

```text
LIKELY
```

D17 observed:

```text
avg cash ratio = 73.3801%
avg invested ratio = 26.6199%
BUY_ADD fill count = 0
```

BUY_ADD zero likely contributed to under-deployment by removing the route for adding capital to existing high-conviction holdings. Exact cash-utilization delta is not directly established without a repaired counterfactual run. Cash / exposure policy must not be changed before the BUY_ADD runtime defect is repaired.

## Re-entry Relation

Judgment:

```text
INDIRECT_RELATION_POSSIBLE
```

D17 observed:

```text
re-entry count = 93
campaigns with ADD event = 0
```

With BUY_ADD unavailable, additions to existing campaigns cannot occur; repeated BUY_NEW re-entry may absorb some capital after exits. Direct causality for the 93 re-entry events is not established here and should remain a D20 audit topic.

## Minimal Repair Scope

Recommended D19 repair scope:

```text
Strategy job PM input selection / runtime path wiring repair
```

Allowed:

```text
Strategy job PM input selection repair
D12 actual runtime path wiring repair
```

Forbidden in D19:

```text
Portfolio Construction ADD reconstruction
Position Sizing / Runtime Planning heuristics
Cash / exposure threshold changes
Re-entry suppression
ADD aggressiveness tuning
Exit tuning
```

## Evidence

```text
reports/phase28_d18_pm_add_strategy_pm_runtime_run_mismatch_root_cause_diagnosis/
reports/phase_reports/phase28_d18_pm_add_strategy_pm_runtime_run_mismatch_root_cause_diagnosis.json
```

## Next Phase

```text
Phase28-D19 PM ADD actual Runtime path minimal repair
```

D19 entry decision:

```text
READY
```
