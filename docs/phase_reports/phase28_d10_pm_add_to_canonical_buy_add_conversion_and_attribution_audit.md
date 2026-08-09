# Phase28-D10: PM ADD to Canonical BUY_ADD Runtime Conversion and Attribution Audit

## 1. Executive Summary

Primary Judgment:

```text
PHASE28_D10_PHASE28_C_RUNTIME_CONVERSION_GAP_CONFIRMED
```

Supporting Judgments:

```text
PM_ADD_EXISTS_NO_ACTUAL_BUY_ADD_CONFIRMED
SUMMARY_OBSERVABILITY_GAP_CONFIRMED
```

At the fixed audit cutoff, 21 run-scoped PM `ADD` decisions exist, but zero actual Runtime Planning `BUY_ADD` plans exist. The `BUY_ADD` string appears 98 times, but every cutoff occurrence is `planning_intent_taxonomy` metadata in `strategy/runtime_planning.json` or `strategy_eod_shadow/runtime_planning.json`, not an actual `plans[].planning_intent`.

The first stop for all 21 PM ADD items is:

```text
PM_ADD_NOT_PROPAGATED_TO_STRATEGY_POSITION_MANAGEMENT
```

The run-scoped `position_management/pm_decisions.json` emits ADD, but the corresponding `strategy/position_management.json` rows consumed by Portfolio Construction show `action=UNRESOLVED`. Portfolio Construction then receives `pm_action=UNRESOLVED`, not ADD, so Phase28-C's ADD bridge is not reached.

## 2. Scope

Read-only diagnosis only. No implementation, config, schema, threshold, resume, fresh run, long historical run, or Runtime mutation was performed.

## 3. Audit Cutoff

```text
audit_started_at: 2026-08-06T03:16:35Z
run_id: runtime-test-historical-smoke-20260806T005408544432Z
run_status_at_audit_start: HALT
next_job_at_audit_start: 2023-06-14:submit
latest_complete_business_date_at_audit_start: 2023-06-13
completed_business_day_count_at_audit_start: 49
partial_or_uncompleted_daily_dirs_excluded: 2023-06-14
```

Cutoff authority:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260806T005408544432Z/run_state.json
```

## 4. Current Run Status

The run is not complete at cutoff. `run_state.json` reports `HALT` with `next_job=2023-06-14:submit`. The partial `daily/2023-06-14` directory was excluded from all counts.

## 5. Evidence Reviewed

Required Phase28-A/B/C/D8 reports and architecture contracts were reviewed. Primary runtime evidence was under:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260806T005408544432Z/daily/<business_date>/
```

Machine-readable evidence is in:

```text
reports/phase28_d10_pm_add_to_canonical_buy_add_conversion_and_attribution_audit/
```

## 6. Runtime Planning Schema Discovery

Actual Runtime Planning plans are stored at:

```text
strategy/runtime_planning.json -> plans[]
```

Actual intent field:

```text
plans[].planning_intent
```

Metadata field:

```text
planning_intent_taxonomy
```

Contract/code confirmation:

```text
src/ai_fund_lab_v2/strategy/runtime_planning.py
PLANNING_INTENTS contains BUY_ADD as taxonomy metadata.
_resolve_intent maps positive quantity_delta_candidate to BUY_ADD only when the symbol is in current_codes.
```

## 7. BUY_ADD Token Classification

Cutoff `BUY_ADD` token occurrences:

| Class | Count |
|---|---:|
| ALLOWED_INTENT_METADATA | 98 |
| ACTUAL_RUNTIME_PLAN | 0 |
| PENDING_ITEM | 0 |
| APPROVAL_ITEM | 0 |
| SUBMIT_ITEM | 0 |
| FILL_ITEM | 0 |
| CAMPAIGN_EVENT | 0 |

Therefore, the daily artifact `BUY_ADD` strings are allowed-intent metadata, not actual plans.

## 8. PM ADD Inventory

Run-scoped PM ADD count at cutoff:

```text
21
```

Unique symbols:

```text
21340
83060
94320
```

The user-observed `20` is treated as a cutoff difference. This audit includes 2023-06-13 as a completed business date and excludes only 2023-06-14.

## 9. Canonical Conversion Trace

All 21 PM ADD items follow the same failure shape:

```text
position_management/pm_decisions.json: decision_type=ADD
strategy/position_management.json: action=UNRESOLVED
strategy/portfolio_construction.json: pm_action=UNRESOLVED
strategy/position_sizing.json: no ADD positive delta
strategy/runtime_planning.json: no BUY_ADD
```

Example, 2023-04-04 / 94320:

```text
PM decision: pm-2023-04-04-94320-add
strategy_pm_action: UNRESOLVED
portfolio_pm_action: UNRESOLVED
portfolio_membership_intent: UNRESOLVED
target_weight: 0.0
quantity_delta_candidate: -800
runtime_planning_intent: SELL_EXIT
```

## 10. First-stop Classification

| First Stop | Count |
|---|---:|
| PM_ADD_NOT_PROPAGATED_TO_STRATEGY_POSITION_MANAGEMENT | 21 |

Requested funnel metrics:

| Metric | Count |
|---|---:|
| target_weight increase | 0 |
| positive quantity delta | 0 |
| lot rounding zero delta | 0 |
| actual BUY_ADD plan | 0 |

Lot rounding is not the cause. The ADD rows never reach the ADD bridge / positive sizing stage.

## 11. Actual BUY_ADD Plan Inventory

Actual BUY_ADD recognition contract:

```text
strategy/runtime_planning.json plans[] row exists
AND plans[].planning_intent == BUY_ADD
AND not merely planning_intent_taxonomy metadata
```

Result:

```text
actual BUY_ADD plan count: 0
unique BUY_ADD dates: none
unique BUY_ADD symbols: none
```

## 12. Pending / Approval / Submit / Fill Attribution

Because actual BUY_ADD plan count is zero:

| Stage | Count |
|---|---:|
| BUY_ADD Pending | 0 |
| BUY_ADD Approval | 0 |
| BUY_ADD Submit | 0 |
| BUY_ADD Fill | 0 |
| BUY_ADD filled notional | 0 |

No BUY_ADD pending, submit, or fill can be attributed without an actual BUY_ADD plan.

## 13. Campaign Attribution

```text
campaign count with BUY_ADD fill: 0
ADD count per campaign: 0
incremental ADD notional: 0
PnL after ADD: NOT_DERIVABLE_NO_BUY_ADD_FILL
```

No existing campaign ADD event was observed.

## 14. Capital Utilization Diagnostics

Capital utilization diagnostics are partial/non-authoritative for D10. Since no BUY_ADD fill exists, ADD-specific before/after notional, ADD PnL, holding days after ADD, and days from ADD to REDUCE/EXIT are not derivable.

## 15. Strategy Summary Observability

`summarize --scope strategy` emits both:

```text
top_level pm_decisions.add_count = 21
strategy_scope latest-day trace add_count = 0
```

The strategy scope builds the latest completed day Strategy trace from `daily/<latest>/strategy/*`, not a run-wide BUY_ADD funnel. It does not expose run-wide actual BUY_ADD plan / pending / submit / fill attribution.

Judgment:

```text
SUMMARY_OBSERVABILITY_GAP
```

## 16. Phase28-C Functional Judgment

```text
PHASE28_C_RUNTIME_CONVERSION_GAP_CONFIRMED
```

Phase28-C's Portfolio Construction bridge is not proven defective by this evidence because the bridge was not reached with `pm_action=ADD`. The immediate confirmed gap is upstream conversion/propagation:

```text
run-scoped PM ADD
-> not propagated as ADD into strategy/position_management
-> Portfolio Construction sees UNRESOLVED
-> no target_weight increase
-> no positive quantity_delta
-> no BUY_ADD
```

## 17. Risks

- The run halted at 49 completed business days, so this is not a completed 100BD audit.
- The partial 2023-06-14 artifacts may contain later evidence but were excluded by cutoff contract.
- Summary CLI can confuse PM ADD with actual BUY_ADD unless the caller distinguishes top-level run-scoped PM counts from strategy-scope runtime planning rows.

## 18. Open Gaps

1. PM ADD propagation into Strategy artifacts consumed by Portfolio Construction.
2. Summary CLI run-wide actual BUY_ADD observability.
3. BUY_ADD campaign/PnL attribution remains untested because no BUY_ADD fill exists.
4. 100BD validation remains incomplete because the run halted before completion.

## 19. Final Judgment

```text
Primary Judgment:
PHASE28_D10_PHASE28_C_RUNTIME_CONVERSION_GAP_CONFIRMED

Evidence cutoff:
2026-08-06T03:16:35Z / latest complete business date 2023-06-13 / 49 completed business days

PM ADD count:
21

Actual BUY_ADD plan count:
0

BUY_ADD Pending / Approval / Submit / Fill:
0 / 0 / 0 / 0

PM ADD conversion rate:
0.0

Summary observability gap:
YES

Runtime conversion defect:
YES

Implementation changed:
false

Config changed:
false

Schema changed:
false

Threshold changed:
false

Resume / fresh / long historical:
false / false / false

Current 100BD run mutated:
false
```

## 20. Next Phase Recommendation

```text
Phase28-D11 PM ADD strategy artifact propagation and Summary BUY_ADD observability repair design
```
