# Phase30-AK1 - ADD Conversion / PS Executable Capital Bridge Lineage and Root-Cause Audit

## Scope

Task ID: `Phase30-AK1`

Target run:

```text
runtime-test-historical-extended-smoke-20260816T121454359538Z
```

This audit is READ-ONLY. The target run was not stopped, resumed, replayed,
repaired, tuned, or mutated. No Strategy, Runtime, config, threshold, cap, lot,
or model implementation was changed.

Audit freeze:

```text
AUDIT_CUTOFF_DATE = 2023-09-21
completed_business_days_at_freeze = 275
```

All findings below are based on run artifacts through 2023-09-21 only.

## Primary Judgment

```text
PRIMARY_CAPITAL_BRIDGE_ROOT_CAUSE =
BUY_NEW: QUALITY_DEFERRED_TO_CASH / lot-cap feasibility attrition before PS
final quantity, plus submit guard quarantine after Runtime intent.

BUY_ADD: existing-position baseline/cap-drift authority leaves most ADD intent
with zero incremental target, especially when current weight already exceeds
the Strategy 18% cap.
```

Canonical classification:

```text
CAPITAL_BRIDGE_LINEAGE_CLASSIFICATION =
POLICY_CAP_AND_EXECUTION_GUARD_DOMINATED_ATTRITION_WITH_OBSERVABILITY_GAPS;
NOT_CAMPAIGN_ID_MISMATCH
```

This is not a recurrence of the Phase30-AE1 canonical campaign id mismatch.
PM, SI, and PC campaign identity matched for all ADD rows observed at cutoff.

## Canonical Funnel Summary

### BUY_NEW

| Stage | Count |
| --- | ---: |
| Hybrid Candidate rows | 13,750 |
| Opportunity reached | 13,750 |
| Buy Quality reached | 13,750 |
| PC competition reached | 13,750 |
| PC positive increment | 4,069 |
| PS quantity candidate positive | 937 |
| PS final quantity positive | 170 |
| Runtime BUY intent | 170 |
| BUY fills | 131 |

BUY_NEW attrition is dominated by PC/PS executable-capital gating, not by
Candidate, Opportunity, or Buy Quality surface loss. Candidate to PC coverage is
complete for the cutoff set.

The dominant zero-delta class is:

```text
QUALITY_DEFERRED_TO_CASH = 13,472
```

Additional zero-delta classes:

```text
ZERO_INCREMENTAL_TARGET = 130
GENUINE_LOT_INFEASIBILITY = 23
MINIMUM_MEANINGFUL_NOTIONAL = 21
CONCENTRATION_HEADROOM_LIMIT = 14
RESIDUAL_CAPITAL_TOO_SMALL = 1
```

### BUY_ADD

| Stage | Count |
| --- | ---: |
| PM ADD rows | 262 |
| Campaign identity match | 262 |
| Campaign identity mismatch | 0 |
| Opportunity Cost PASS | 197 |
| Entry ADD_ALLOWED / ADD_REDUCED_ONLY | 227 |
| Entry NO_ADD | 35 |
| PC positive incremental target | 8 |
| PS positive quantity delta | 6 |
| Runtime BUY_ADD intent | 6 |
| Economic same-day BUY fill after Runtime BUY_ADD intent | 6 |
| Fill semantic preserved as BUY_ADD | 0 |

The economic ADD path existed and worked in early 94320 cases. The fill
observability layer records these executions as generic `BUY`, not semantic
`BUY_ADD`, so `BUY_ADD` is not preserved as a fill-side semantic label.

## PM to PC

PM ADD intent reaches PC with canonical campaign identity intact.

Observed ADD campaign identity:

```text
campaign_identity_match = 262
campaign_identity_mismatch = 0
PHASE30_AE1_ADD_CONVERSION_PRESERVED = YES
```

The main ADD loss is after PM/PC identity resolution. PC frequently retains the
existing position as the authoritative baseline and sets no incremental target:

```text
baseline_authority_zero_increment = 254 / 262
```

This is concentrated in cap-drift situations:

```text
ADD rows with current_weight >= 18% Strategy cap = 217 / 262
ADD_ALLOWED or ADD_REDUCED_ONLY rows with current_weight >= 18% = 191
zero-increment ADD_ALLOWED or ADD_REDUCED_ONLY rows with current_weight >= 18% = 191
```

The bridge is therefore not failing because ADD campaign continuity is unknown.
It is failing, or intentionally stopping, because PC treats current overweight
baseline as already above the Strategy cap and does not create an incremental
target.

## PC ADD Continuation

PC positive ADD semantics are valid only when incremental weight is positive.
For ADD, `target_weight == baseline_existing_weight` is not a positive ADD,
even if PM action remains `ADD`.

Relevant canonical flag:

```text
PC_POSITIVE_SEMANTICS_VALID =
YES_IF_INCREMENTAL_WEIGHT_POSITIVE; TARGET_EQUALS_BASELINE_IS_NOT_PC_POSITIVE_ADD
```

Observed ADD action distribution:

```text
ADD_ALLOWED = 10
ADD_REDUCED_ONLY = 217
NO_ADD = 35
```

Opportunity Cost is not the dominant ADD blocker:

```text
Opportunity Cost PASS = 197
Opportunity Cost FAIL_CLOSED = 65
OPPORTUNITY_COST_IS_DOMINANT_ADD_BLOCKER = NO
```

## PC to PS

PC-to-PS handoff did not show the Phase30-S zero-buy recurrence. When PS has a
positive final quantity, Runtime Planning receives a positive intent.

```text
PS final quantity positive = 170
Runtime BUY / BUY_ADD intent = 170
PHASE30_S_HANDOFF_PRESERVED = YES
```

The dominant PC/PS blocker is not missing handoff metadata. It is allocation
quality/cap/lot filtering before final executable quantity.

```text
PC_TO_PS_DOMINANT_BLOCKER = QUALITY_DEFERRED_TO_CASH
```

Lot and capital conversion evidence:

```text
one_lot_executable_but_zero_delta_count = 3,256
genuine_lot_infeasibility_rate = 0.058
repairable_zero_delta_rate = 0.234
```

The presence of one-lot executable but zero-delta rows means that many misses
are not physical lot infeasibility. They are policy/capital-allocation outcomes
where PC/PS deferred available capital to cash rather than forcing execution.

## PS to Runtime to Fill

PS positive quantity maps to Runtime intent:

```text
PS final quantity positive = 170
positive PS to Runtime positive planned quantity = 170
positive PS to fill = 131
positive Runtime intent without same-symbol fill = 39
```

The no-fill subset is downstream of Runtime intent and is dominated by submit
guard behavior. Sample evidence shows historical corporate-action quarantine
for positive BUY plans, with pending items classified as terminal
`QUARANTINED_NOT_SUBMITTED`.

Distribution from submitted-order authority on positive Runtime/no-fill rows:

```text
historical_corporate_action_quarantine_no_submitted_orders = 15
orderlist_position_cash_evidence_accepted = 24
```

This is not a Phase30-S PC-to-PS handoff recurrence.

## 94320 Sentinel

For 94320, the required sentinel dates show canonical PM/PC campaign continuity,
then a PC zero-increment drop before PS:

| Date | PM | Entry Action | Opportunity Cost | Current Weight | Target Weight | Lot-Aware Increment | PS Delta | Runtime |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| 2023-08-24 | ADD | ADD_REDUCED_ONLY | PASS | 0.229662 | 0.229662 | 0.000000 | 0 | NO_ACTION |
| 2023-08-31 | ADD | ADD_REDUCED_ONLY | PASS | 0.233361 | 0.233361 | 0.000000 | 0 | NO_ACTION |
| 2023-09-01 | ADD | ADD_REDUCED_ONLY | PASS | 0.234026 | 0.234026 | 0.000000 | 0 | NO_ACTION |
| 2023-09-05 | ADD | NO_ADD | PASS | 0.236101 | 0.236101 | 0.000000 | 0 | NO_ACTION |
| 2023-09-06 | ADD | ADD_REDUCED_ONLY | FAIL_CLOSED | 0.234577 | 0.234577 | 0.000000 | 0 | NO_ACTION |
| 2023-09-21 | ADD | NO_ADD | PASS | 0.247584 | 0.247584 | 0.000000 | 0 | NO_ACTION |

Canonical drop layer:

```text
94320_ADD_DROP_LAYER = PC_INCREMENTAL_TARGET_MATERIALIZATION_ZERO_BEFORE_PS
```

The PS evidence carries:

```text
ADD_TARGET_WEIGHT_UNCHANGED
EXISTING_BASELINE_CAP_DRIFT_ACCEPTED_NO_INCREMENT
existing_position_baseline_quantity_authoritative
```

The 94320 path is therefore not being dropped because PC cannot compare
campaign ids. It is being dropped because PC accepts the current overweight
baseline and does not create incremental ADD weight.

### 94320 Fill / Campaign Reconciliation

Run-scoped execution evidence includes 94320 economic BUY fills on:

```text
2022-08-10: 200
2022-08-19: 200
2022-08-22: 200
2022-08-23: 200
2022-08-24: 200
2022-09-01: 100
2022-09-15: 100
```

Total run-scoped economic BUY quantity:

```text
1,200
```

However, cutoff campaign summary compacts to one BUY event and the fill-side
campaign id differs from the current canonical campaign id:

```text
current canonical campaign id = pc-9df523ec4cc67774-94320-0001
run-scoped fill campaign id = pc-7744796ba6779c27-94320-0001
fill source_decision_type = BUY
```

This is a campaign/execution observability lineage gap. It is not the recent
2023-08/09 ADD drop layer, which occurs earlier at PC zero incremental target.

## Prior Repair Contract Status

```text
PHASE28_ADD_BRIDGE_PRESERVED =
YES_FOR_EARLY_94320_ADD_TO_RUNTIME_BUY_ADD; LATER_BLOCKED_BY_CAP_DRIFT_ZERO_INCREMENT

PHASE29_LOT_CAPITAL_CONVERSION_PRESERVED =
YES_LOT_FIRST_REALLOCATION_AND_ONE_LOT_EVIDENCE_PRESENT; MANY_ZERO_DELTAS_ARE_QUALITY/CAP_DEFERRED

PHASE30_S_HANDOFF_PRESERVED =
YES_PC/PS_POSITIVE_QUANTITY_MAPS_TO_RUNTIME_INTENT; NO_ZERO_BUY_HANDOFF_RECURRENCE_PROVEN

PHASE30_AE1_ADD_CONVERSION_PRESERVED =
YES_CANONICAL_PM_PC_CAMPAIGN_IDS_MATCH_262_OF_262
```

## Required Flags

```text
ADD_CONVERSION_REGRESSION =
NO_AE1_CAMPAIGN_REGRESSION; PARTIAL_ACTION_EFFECT_GAP_REMAINS_FOR_CAP_DRIFT_ADD

CAPITAL_CONVERSION_REGRESSION =
PARTIAL_BUY_NEW_PC_TO_PS_ATTRITION_AND_SUBMIT_QUARANTINE; PHASE30_S_HANDOFF_NOT_RECURRED

BUY_NEW_AND_ADD_COMMON_ROOT =
NO_DOMINANT_ROOTS_DIFFER; COMMON_THEME_IS_PC_TO_EXECUTABLE_CAPITAL_ATTRITION

KNOWN_RUNTIME_OR_AUTHORITY_DEFECT =
YES_OBSERVABILITY: RUNTIME_PLANNING_DRAFT_PENDING_NOT_WRITTEN_AND_FILL_BUY_ADD_SEMANTIC/CAMPAIGN_LINEAGE_LOSS; PRIMARY_CAPITAL_DROP_IS_POLICY/CAP_LAYER

SAFETY_WEAKENING_REQUIRED = NO
FORCED_INVESTMENT_REQUIRED = NO
```

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

This audit did not use future outcomes to select parameters or tune Strategy.

## Evidence Artifacts

Summary report:

```text
reports/phase_reports/phase30_ak1_add_conversion_ps_executable_capital_bridge_lineage_root_cause_audit.json
```

Detailed evidence directory:

```text
reports/phase_reports/phase30_ak1/
```

Generated evidence files:

```text
canonical_capital_conversion_funnel.json
buy_new_conversion_analysis.json
buy_add_conversion_analysis.json
pc_to_ps_zero_delta_analysis.json
ps_to_runtime_fill_analysis.json
94320_add_lineage.json
94320_fill_campaign_reconciliation.json
add_sentinel_comparison.json
buy_new_success_near_miss_comparison.json
lot_feasibility_analysis.json
residual_capital_recycling_analysis.json
baseline_authority_analysis.json
opportunity_cost_cross_tab.json
add_worthiness_analysis.json
regression_lineage_analysis.json
executable_capital_bridge_map.json
```

## Implementation

```text
NO IMPLEMENTATION AUTHORIZED BY PHASE30-AK1
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
FRESH_RUN_EXECUTED_BY_CODEX = NO
```

## Recommended Next Task

```text
Phase30-AK2 - Executable Capital Policy / Submit Guard / Campaign Fill Lineage Repair Design
```

Scope should be design-only unless separately authorized. The single next task
should separate:

1. cap-drift ADD action-effect semantics,
2. BUY_NEW quality-deferred-to-cash capital recycling,
3. historical corporate-action submit quarantine for positive Runtime BUY
   intents,
4. fill-side BUY_ADD semantic and campaign-id observability preservation.
