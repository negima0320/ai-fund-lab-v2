# Phase30-AD0 - Post-AC Fresh-Run Position / Campaign Lifecycle HALT Root Cause Audit

Task ID: `Phase30-AD0`

Target run:

```text
runtime-test-historical-extended-smoke-20260816T043332338677Z
```

Boundary:

```text
READ_ONLY_AUDIT
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30-AD0
NO_TARGET_RUN_MUTATION
NO_RESUME
NO_REPLAY
NO_FRESH_RUN
NO_STRATEGY_TUNING
```

## Primary Judgment

```text
ROOT_CAUSE_CLASSIFICATION = PHASE30_AC_CANONICAL_CAMPAIGN_FIRST_DAY_BOOTSTRAP_GAP
PHASE30_AC_REGRESSION = YES
PERFORMANCE_EVIDENCE_VALID = NO
```

Accounting and Current are consistent after the 2022-08-10 BUY fills. The HALT
is caused by canonical campaign lifecycle continuity: Phase30-AC pre-action
campaign materialization wrote an empty first-day campaign snapshot before BUY
fills, and the next morning used that empty strict-prior snapshot even though
Current had 9 open positions.

This is not a valuation defect and not a monitor-only issue. It is a canonical
campaign bootstrap gap in the Phase30-AC path.

## Exact HALT Cause

Fresh wrapper:

```text
final_judgment = HALT
fresh_run_exit_code = 30
completed_days = ["2022-08-10"]
```

Runtime CLI:

```text
2022-08-12:morning
exit_code = 20
```

Halt summary:

```text
halt_classification = REVIEW_REQUIRED
root_reason = morning pipeline review required: strategy_planning_authority_unresolved
```

Failing artifact:

```text
daily/2022-08-12/morning/planning_evidence.json
daily/2022-08-12/morning/strategy_planning_authority_evidence.json
```

Exact reason:

```text
status = REVIEW_REQUIRED
reason = strategy_planning_authority_unresolved
reason_codes include strategy_plan_order_side_unresolved
reason_codes include strategy_plan_quantity_unresolved:<26 symbols>
```

Upstream chain:

```text
Strategy Intelligence campaign identity MISSING for 9 held positions
-> PM REVIEW_REQUIRED / UNRESOLVED for 23700, 93180, 94340
-> PC REVIEW_REQUIRED
-> Position Sizing REVIEW_REQUIRED with 0 rows
-> Runtime Planning quantity unresolved
-> morning planning REVIEW_REQUIRED
-> CLI exit code 20
```

## 2022-08-10 BUY / Fill State

Morning planning:

```text
plan_count = 21
pending_item_count = 9
status = PASS
```

Submit / execution:

```text
submitted_order_count = 9
fill_count = 9
ledger_executions_appended = 9
ledger_positions_appended = 9
ledger_cash_appended = 1
```

Fills:

| Symbol | Qty | Notional |
| --- | ---: | ---: |
| 23880 | 200 | 33,800 |
| 94340 | 200 | 30,280 |
| 66590 | 400 | 40,800 |
| 93180 | 7,900 | 47,400 |
| 89180 | 3,200 | 32,000 |
| 94320 | 200 | 29,840 |
| 45710 | 100 | 20,300 |
| 76470 | 1,300 | 33,800 |
| 23700 | 600 | 43,200 |

Total BUY notional:

```text
311,420 JPY
```

## Accounting / Current Reconciliation

End of 2022-08-10:

```text
Equity = 994,000
Cash = 688,580
Equity - Cash = 305,420
Position market value sum = 305,420
Reconciliation difference = 0
Current position count = 9
```

Position market values:

| Symbol | Qty | Avg | Valuation price | MV |
| --- | ---: | ---: | ---: | ---: |
| 23700 | 600 | 72.0 | 71.0 | 42,600 |
| 23880 | 200 | 169.0 | 151.0 | 30,200 |
| 45710 | 100 | 203.0 | 199.0 | 19,900 |
| 66590 | 400 | 102.0 | 98.0 | 39,200 |
| 76470 | 1,300 | 26.0 | 26.0 | 33,800 |
| 89180 | 3,200 | 10.0 | 10.0 | 32,000 |
| 93180 | 7,900 | 6.0 | 6.0 | 47,400 |
| 94320 | 200 | 149.2 | 149.8 | 29,960 |
| 94340 | 200 | 151.4 | 151.8 | 30,360 |

Judgment:

```text
ACCOUNTING_POSITION_STATE = CONSISTENT
CURRENT_POSITION_STATE = CONSISTENT
```

## Canonical Campaign State

2022-08-10 canonical campaign artifact:

```text
path = daily/2022-08-10/positions/position_campaigns.json
authority = CANONICAL_PRE_ACTION_POSITION_CAMPAIGN_LIFECYCLE
contract_version = phase30_ac_pre_action_campaign_lifecycle.v1
open_campaign_count = 0
```

But after execution, Current had 9 open positions. The 2022-08-10 artifact's
`pre_action_connection` records:

```text
current_open_position_count = 9
updated_open_campaign_count = 0
missing_current_campaign_symbols =
  23700, 23880, 45710, 66590, 76470, 89180, 93180, 94320, 94340
```

2022-08-12 SI consumed pre-action campaign hash:

```text
99b987d9dda488db35a10c60fada2e2865f01f0d9e3a2545ede9e48e1be9942b
```

The currently visible 2022-08-12 `positions/position_campaigns.json` hash is:

```text
5d18b2ecf12216bbc48dc16463ffdb4804400ef0e24f3addd89721dc97bf2f32
```

That visible artifact is post/pre-action-overwritten observability evidence
with 9 campaigns. It is not the hash consumed by Strategy Intelligence.

Judgment:

```text
CANONICAL_CAMPAIGN_STATE = INCONSISTENT
```

## Valuation

2022-08-10 valuation:

```text
projection_status = PASS
status = READY
position_count = 9
valued_position_count = 9
new_total_market_value = 305,420
cash = 688,580
apply_status = APPLIED
```

Valuation and accounting agree with Current. The market value of 305,420 JPY is
real in runtime accounting.

## Monitoring Display Cause

Observed monitor:

```text
Positions = 0
Holdings = -
```

Classification:

```text
CANONICAL_CAMPAIGN_EMPTY
MONITOR_DISPLAY_STATE = INCONSISTENT
```

This is not clean monitor-only display drift. Accounting / Current / valuation
show 9 positions, while the canonical campaign artifact available in the
pre-action lifecycle path was empty. A display that relies on campaign or
pre-action lifecycle state will show 0 even though accounting has positions.

## 2022-08-12 Morning Failure

Strategy Intelligence:

```text
producer_result_status = PASS
held_position_count = 9
campaign_identity_missing_count = 9
```

Missing symbols:

```text
23700
23880
45710
66590
76470
89180
93180
94320
94340
```

PM:

```text
producer_result_status = REVIEW_REQUIRED
decision_resolution = UNRESOLVED
position_count = 9
```

PM unresolved because `structured_hold_worthiness_review_required` applied to:

```text
23700
93180
94340
```

PC:

```text
producer_result_status = REVIEW_REQUIRED
decision_resolution = UNRESOLVED
reason_codes include upstream_review_required:SOURCE_REVIEW_REQUIRED
```

Position Sizing:

```text
producer_result_status = REVIEW_REQUIRED
decision_resolution = UNRESOLVED
position_sizing rows = 0
reason_codes =
  portfolio_construction_review_required:REVIEW_REQUIRED
  position_management_review_required:REVIEW_REQUIRED
```

Runtime Planning:

```text
producer_result_status = REVIEW_REQUIRED
decision_resolution = UNRESOLVED
plan_count = 30
quantity_unresolved_count = 26
```

Morning planning:

```text
status = REVIEW_REQUIRED
reason = strategy_planning_authority_unresolved
exit_code = 20
```

Judgment:

```text
MORNING_RESTORE_STATE = INCONSISTENT
```

## Phase30-AC Causality

```text
PHASE30_AC_REGRESSION_CONFIRMED
PHASE30_AC_REGRESSION = YES
```

Phase30-AC correctly removed campaign fallback and required canonical campaign
identity for held positions. The regression is that the new canonical path does
not bootstrap campaigns created by first-day BUY fills into the next pre-action
campaign snapshot.

The defect is not that the fallback was removed. The defect is that canonical
campaign materialization lacks first BUY / post-execution carry-forward into
the strict-prior pre-action snapshot.

## Legacy Retirement Impact

Legacy retirement made the gap visible and fail-closed. Reinstating symbol-only
fallback, PM/current lifecycle fallback, or old HOLD/ADD heuristics would hide
the defect and violate Phase30-AB/AC.

Required repair direction:

```text
repair canonical campaign bootstrap / carry-forward
do not restore legacy fallback
```

## Temporal / Bootstrap Finding

Temporal safety itself held:

```text
same_day_eod_campaign_reconstruction_used = false
future_information_used = false
```

However, the bootstrap contract is incomplete:

```text
first-day BUY fills
-> Ledger / Current positions exist
-> canonical campaign state not carried into next pre-action snapshot
-> next morning held positions have campaign_identity_authority_status = MISSING
```

This is the exact continuity gap.

## Required Final Judgments

```text
ACCOUNTING_POSITION_STATE = CONSISTENT
CURRENT_POSITION_STATE = CONSISTENT
CANONICAL_CAMPAIGN_STATE = INCONSISTENT
MONITOR_DISPLAY_STATE = INCONSISTENT
MORNING_RESTORE_STATE = INCONSISTENT
PHASE30_AC_REGRESSION = YES
ROOT_CAUSE_CLASSIFICATION = PHASE30_AC_CANONICAL_CAMPAIGN_FIRST_DAY_BOOTSTRAP_GAP
```

## Performance Evidence

```text
PERFORMANCE_EVIDENCE_VALID = NO
```

The run stopped after one completed business day and must not be used for
Strategy performance evaluation.

## Implementation Authorization

```text
NO IMPLEMENTATION AUTHORIZED BY PHASE30-AD0
```

## Recommended Next Task

```text
Phase30-AD1 - Canonical Campaign Fresh-Run Bootstrap / Morning Continuity Repair
```
