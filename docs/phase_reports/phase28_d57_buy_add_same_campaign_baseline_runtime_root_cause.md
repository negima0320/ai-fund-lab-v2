# Phase28-D57: BUY_ADD Same-Campaign Baseline Supply Runtime Root Cause Audit

## Primary Judgment

```text
PHASE28_D57_ACTIVE_ADD_BASELINE_CAMPAIGN_AUTHORITY_PROPAGATION_GAP_CONFIRMED
```

D57 was read-only. No implementation, config, schema, threshold, runtime mutation, resume, fresh run, or long historical run was executed.

## Run Validity

```text
Run ID = runtime-test-historical-smoke-20260808T232727106824Z
Profile = historical-smoke
Start date = 2023-04-03
Use = diagnostic evidence only
Acceptance by 100BD completion = NOT USED
```

## Funnel Findings

```text
PM ADD count = 25
PC positive ADD increment = 0
PS positive BUY_ADD delta = 0
Runtime BUY_ADD = 0
BUY_ADD Fill = 0
```

D55-A resolver was invoked for all 25 PC ADD rows:

```text
D55-A resolver invocation status = PASS_INVOKED_25_ADD_ROWS_ALL_FAIL_CLOSED
D55-A producer_version = phase28_d55_a_add_investment_evidence_resolver.v1
Campaign continuation = FAIL_CLOSED for all ADD rows
Expected edge = FAIL_CLOSED for all ADD rows
Incremental value = FAIL_CLOSED for all ADD rows
```

D55-C supplier was invoked, but every active daily evidence row showed:

```text
supplied_count = 0
missing_count = 0
future_baseline_used = false
symbol_only_baseline_used = false
```

## Direct Cause

The direct cause of `supplied_count=0` is:

```text
D55-C supplier builds current_campaign_by_symbol from current_summary only.
The Runtime current/current-summary authority reaching PC has no canonical position_campaign_id.
Therefore no opportunity row receives expected_edge_baseline_* fields.
```

The direct cause of `missing_count=0` is:

```text
missing_count increments only when an opportunity symbol has a current campaign id and no baseline.
Because current_campaign_by_symbol is empty for the supplier authority, no row can increment missing_count.
```

This is why `supplied_count=0` and `missing_count=0` persist together.

## Campaign Authority Matrix

```text
Architecture SoT:
position_campaign_id is required lineage for canonical BUY_ADD.

persistent ledger / final state sample:
symbol and quantity present, position_campaign_id absent.

positions/position_campaigns.json:
position_campaign_id exists as run-scoped observability evidence.
Example 76010 = pc-819217ff9f096cfd-76010-0001.

Strategy current -> PC current fields:
current_position_campaign_id = ""
position_campaign_id = ""

PM artifact:
position_id/current_position_reference/lifecycle_reference = runtime-current-<symbol>
explicit position_campaign_id absent.

Opportunity artifact:
campaign fields absent.

PC member:
pm_position_campaign_id = runtime-current-<symbol>
position_management_reference = runtime-current-<symbol>
current_position_campaign_id = ""
opportunity_position_campaign_id = ""
position_campaign_id = ""

D55-A resolver:
uses pm_position_campaign_id/current_position_campaign_id/current campaign side plus opportunity campaign side.

D55-C supplier:
does not consume PM pm_position_campaign_id; it uses current_summary for active campaign identity.
```

## Representative Case: 76010 / 2023-05-02

```text
2023-05-01 PC:
76010 was ADD_CANDIDATE / current_position=false / runtime_opportunity_score=0.07606276.

2023-05-02 PC:
76010 current_position=true
pm_action=ADD
current_weight=0.156835
target_weight=0.156835

D55-A:
current_campaign_id = runtime-current-76010
position_campaign_id = runtime-current-76010
opportunity_campaign_id = ""
baseline_business_date = ""
baseline_score = null
final_add_eligibility = FAIL_CLOSED
```

76010 is a valid first-ADD bootstrap example: the prior day was BUY_NEW/current_position=false, so a same-campaign current-position baseline may not yet exist under D55-C's prior-current-only rule.

## Subsequent ADD

First-ADD bootstrap does not explain the all-zero outcome.

Example:

```text
94320 has repeated ADD rows after current_position=true Strategy artifacts already exist.
All remain target_weight=current_weight.
All remain final_add_eligibility=FAIL_CLOSED.
D55-C supplied_count/missing_count remain 0/0.
```

Therefore the persistent failure is a campaign authority propagation gap, not merely first-ADD bootstrap.

## Active vs EOD Shadow

Active `strategy/` and `strategy_eod_shadow/` both show:

```text
supplied_count = 0
missing_count = 0
current_position_campaign_id = ""
opportunity_position_campaign_id = ""
target_weight_increment = 0
```

Classification:

```text
COMMON_STRATEGY_PRODUCER_PROBLEM
```

## Historical vs Production

```text
Historical-only defect = NO
Production path affected = YES
```

Evidence:

```text
run_daily_operation.py calls generate_strategy_shadow_for_day for formal morning Strategy.
generate_strategy_shadow_for_day owns D55-C baseline supply.
The supplier is in shared Strategy generation, not a historical-only replay adapter.
```

If Production/Demo current-position inputs also lack canonical campaign identity, they can hit the same baseline supply failure.

## Fault Classification

```text
D55-A defect = NO
D55-C defect = YES
D55-D relevance = unrelated
Repair required = YES
Fresh 100BD rerun required after repair = YES
```

D55-A is behaving fail-closed as designed when campaign/baseline evidence is absent. D55-C's supplier is the first point where the same-campaign baseline becomes unavailable, because it uses a campaign authority source that is not aligned with the campaign authority D55-A later sees via PM/PC.

## Minimal D58 Scope

```text
Production-common campaign identity propagation into Strategy current-position baseline supply,
aligned with D55-A campaign authority.
```

Constraints for D58:

```text
Do not use symbol-only baseline fallback.
Do not use future evidence.
Do not use unconditional latest fallback.
Do not add a Historical-only hack.
Do not force BUY_ADD.
Do not relax thresholds.
Do not fail-open missing baseline.
```

## Deliverables

```text
docs/phase_reports/phase28_d57_buy_add_same_campaign_baseline_runtime_root_cause.md
reports/phase_reports/phase28_d57_buy_add_same_campaign_baseline_runtime_root_cause.json
reports/phase28_d57_buy_add_same_campaign_baseline_runtime_root_cause/
```
