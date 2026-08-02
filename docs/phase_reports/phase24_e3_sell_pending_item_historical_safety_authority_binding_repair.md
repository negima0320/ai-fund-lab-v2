# Phase24-E3 SELL Pending Item Historical Safety Authority Binding Repair

## 1. Primary Judgment

`PHASE24_E3_SELL_SAFETY_AUTHORITY_BINDING_REPAIRED_SHORT_VALIDATION_PASS`

Phase24-E3 repaired the SELL pending item binding gap that caused the 2022-07-15 Submit HALT in run `runtime-test-historical-extended-smoke-20260731T023102609262Z`.

The repair is limited to propagating already-materialized Historical Safety Temporal Authority and Runtime Test lineage into SELL pending items. Strategy, PM decision content, SELL quantity, price authority, cash, position count, Safety decision content, Submit criteria, broker write, J-Quants fetch, fresh-run execution, and Runtime performance parameters were not changed.

## 2. Direct Root Cause

The 2022-07-15 composite Pending had valid top-level Historical Safety Context and the BUY item carried full safety authority, but the SELL item only carried partial safety fields.

Observed failing SELL item `66590`:

```text
safety_decision = NEUTRAL
safety_policy_version = historical_replay_neutral_safety_v1
safety_reason = historical_neutral_no_event_safety_ready
safety_source = data_readiness_historical_temporal_authority

safety_authority = ""
safety_business_date = ""
safety_decision_id = ""
temporal_authority_business_date = ""

runtime_test_evidence_root = ""
runtime_test_profile_id = ""
runtime_test_run_id = ""
```

Because Data Readiness requires item-level Safety Authority evidence for Pending safety validation, Submit correctly halted with:

```text
historical_safety_temporal_authority_missing
pending_safety_evidence_missing
```

## 3. Authority Disappearance Point

Authority disappeared inside SELL pending materialization.

Flow:

```text
Data Readiness / Historical Safety Authority Resolver
  -> historical safety context existed for business_date 2022-07-15

SELL Planning
  -> built SELL item 66590
  -> copied only partial safety fields into the item

Historical safety attach
  -> updated Pending top-level safety_context
  -> did not update pending.items

Composite Pending
  -> merged existing BUY pending and new SELL pending
  -> BUY item remained fully bound
  -> SELL item remained partially bound

Data Readiness / Submit
  -> detected item-level safety authority and runtime lineage missing
  -> failed closed
```

The missing fields were not lost by Submit and were not caused by SELL price authority.

## 4. Reviewed Evidence

Reviewed required evidence:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T023102609262Z/daily/2022-07-15/data_readiness/data_readiness.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T023102609262Z/daily/2022-07-15/submit/runtime_manifest.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T023102609262Z/daily/2022-07-15/sell_planning/sell_planning_manifest.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T023102609262Z/daily/2022-07-15/sell_planning/pending_continuity_evidence.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T023102609262Z/daily/2022-07-15/sell_planning/data_readiness_authority.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T023102609262Z/daily/2022-07-15/sell_planning/position_management_evidence.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T023102609262Z/daily/2022-07-15/position_management/pm_decisions.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T023102609262Z/daily/2022-07-15/morning/pending_generation_evidence.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T023102609262Z/daily/2022-07-15/morning/planning_evidence.json
.runtime/pending_order_plan/pending_order_plan.json
```

Key findings:

```text
Pending state = APPROVED
pending_plan_id = pending-order-plan-pending-composite-2022-07-15-b1245f2b9e9e
top-level safety_authority = historical_initial_no_external_effect
top-level safety_business_date = 2022-07-15
top-level safety_decision_id = historical-neutral-safety:2022-07-15
BUY item 23880 = fully bound
SELL item 66590 = partial safety only, runtime_test lineage missing
Data Readiness overall_status = REVIEW_REQUIRED
Submit final_state = REVIEW_REQUIRED
Submit reason = historical_safety_temporal_authority_missing
```

`strategy_shadow_judgment = REVIEW_REQUIRED` was also recorded in Strategy Shadow evidence, but the Submit HALT reason in this task is Data Readiness safety authority missing. No code path was changed for Strategy Shadow.

## 5. BUY Item vs SELL Item Difference

BUY item authority was already bound through the Strategy Planning Authority / pending item path.

SELL item authority was generated through SELL Planning, where the item builder copied only a subset of `RuntimeSafetyContext` fields. The historical top-level attach step then materialized Pending-level `safety_context` but did not propagate that context to each SELL pending item.

This made composite Pending internally inconsistent:

```text
Pending top-level = bound
BUY item = bound
SELL item = partially bound
```

## 6. SELL Item Safety Binding Contract

Historical replay SELL pending items must carry the same Safety Temporal Authority contract as BUY items:

```text
safety_authority
safety_business_date
safety_decision
safety_decision_id
safety_policy_version
safety_reason
safety_source
temporal_authority_business_date
runtime_test_evidence_root
runtime_test_profile_id
runtime_test_run_id
```

The SELL item must bind these values from canonical Pending top-level / Data Readiness Historical Safety Authority. It must not invent a decision or pass with only `safety_decision = NEUTRAL`.

## 7. Temporal Binding

For 2022-07-15 Submit, SELL item Safety Authority is bound to Submit business date:

```text
safety_business_date = 2022-07-15
temporal_authority_business_date = 2022-07-15
safety_decision_id = historical-neutral-safety:2022-07-15
```

This is independent from position valuation / price authority:

```text
price_as_of = 2022-07-13
price_as_of != safety_business_date
```

SELL price authority remains unchanged.

## 8. Composite Pending Consistency

Composite Pending now preserves one Submit-session Safety Temporal Authority across top-level Pending and all BUY / SELL items:

```text
Pending top-level safety_authority = D authority
BUY item safety_authority = D authority
SELL item safety_authority = D authority

Pending top-level runtime_test_run_id = run identity where available through safety context
BUY item runtime_test_run_id = same run identity
SELL item runtime_test_run_id = same run identity
```

Missing or mismatched item-level authority remains fail-closed through existing Data Readiness / Submit consumers.

## 9. Implementation

Updated:

```text
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
```

The historical safety attach path now also rewrites `pending.items` with the materialized safety context:

```text
_attach_historical_safety_authority(...)
  -> materialize_historical_pending_safety_context(...)
  -> update Pending top-level safety_context
  -> update each PendingOrderItem safety authority and runtime_test lineage
```

Added helper:

```text
_pending_item_with_safety_context(...)
```

No Submit validation criteria were loosened.

## 10. Tests

Updated:

```text
tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py
```

Added coverage:

```text
test_phase24_e3_sell_only_pending_item_binds_historical_safety_authority
test_phase24_e3_composite_buy_sell_pending_items_share_historical_safety_authority
```

The tests assert:

```text
SELL-only Pending item receives full historical safety authority.
Composite BUY and SELL items share top-level safety authority.
runtime_test_run_id / profile_id / evidence_root propagate to SELL.
price_as_of remains the previous valuation date and is not reused as safety date.
```

## 11. Validation

Executed short validation:

```text
python3 -m pytest tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py -q
8 passed, 60 warnings in 2.09s
```

Executed focused regression set:

```text
python3 -m pytest tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/runtime_v2/test_phase23_i_strategy_planning_authority.py tests/runtime_v2/test_phase23_ab_no_order_submit_guard.py tests/runtime_v2/test_phase19_bi_empty_pending_no_action_contract.py -q
57 passed, 60 warnings in 2.99s
```

Executed static checks:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
PASS

git diff --check
PASS
```

## 12. Fail-Closed Confirmation

Fail-closed behavior is preserved:

```text
Data Readiness still owns Pending safety authority validation.
Submit still consumes Data Readiness result.
Missing item-level safety authority still causes REVIEW_REQUIRED.
Missing runtime_test lineage in historical replay still causes REVIEW_REQUIRED.
No consumer-side implicit supplementation was added.
No unconditional APPROVED / PASS path was added.
```

## 13. Runtime Execution Boundary

Not executed in this task:

```text
20BD runtime revalidation
fresh-run
broker write
J-Quants fetch
Strategy parameter change
PM change
SELL quantity change
price authority change
cash / position count change
Submit criterion change
```

## 14. Residual Gaps

Remaining items:

```text
Operator revalidation is required to confirm the 2022-07-15 Submit boundary passes in the full runtime evidence path.
Submit manifest observations around active_max_positions, max_exposure, and target_investment_ratio remain separate non-blocking observations.
Strategy Shadow REVIEW_REQUIRED evidence exists, but is not the direct E3 HALT cause and was not modified.
```

## 15. Operator Revalidation Method

Recommended operator check:

```text
1. Rerun the same failed 20BD validation or resume at the 2022-07-15 Submit boundary after Evidence Review.
2. Inspect .runtime/pending_order_plan/pending_order_plan.json for SELL item 66590.
3. Confirm SELL item fields:
   safety_authority = historical_initial_no_external_effect
   safety_business_date = 2022-07-15
   temporal_authority_business_date = 2022-07-15
   safety_decision_id = historical-neutral-safety:2022-07-15
   runtime_test_run_id = runtime-test-historical-extended-smoke-*
4. Confirm Data Readiness no longer emits:
   historical_safety_temporal_authority_missing
   pending_safety_evidence_missing
5. Confirm Submit does not halt for Historical Safety Temporal Authority missing.
```

## 16. Recommended Next Task

`Phase24-E4 Operator Runtime Revalidation for SELL Pending Historical Safety Authority Binding`

