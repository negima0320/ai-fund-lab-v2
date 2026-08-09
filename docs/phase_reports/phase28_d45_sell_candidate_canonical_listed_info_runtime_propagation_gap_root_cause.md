# Phase28-D45: SELL Candidate Canonical Listed-Info Runtime Propagation Gap Root Cause

## Judgment

Primary Judgment:

```text
PHASE28_D45_D44_NOT_ON_TARGET_RUN_AND_REAL_CONTEXT_MANIFEST_FALLBACK_DEFECT_CONFIRMED
```

D44 causality classification:

```text
D44_IMPLEMENTATION_NOT_ON_ACTIVE_RUNTIME_PATH
```

Supporting classification for the current D44 workspace code:

```text
D44_FALLBACK_ELIGIBILITY_DEFECT
```

D45 was read-only diagnosis. No implementation, config change, schema change, threshold change, resume, fresh run, long historical run, or runtime mutation was performed.

## Target

```text
run_id = runtime-test-historical-smoke-20260807T130749981758Z
business_date = 2023-06-02
failing_stage = sell_planning
exit_code = 20
```

The target subprocess trace recorded:

```text
PYTHONPATH = src
runtime_test_evidence_root = reports/runtime_tests/runs/runtime-test-historical-smoke-20260807T130749981758Z
source_commit = cd1b47a44234bb66c3a773fe7c0324fe11123000
source_dirty = true
```

## Direct Finding

The target run's recorded `source_commit` does not contain the D44 helper:

```text
_canonical_sell_candidate_listed_info_by_symbol
_pending_item_with_sell_candidate_listed_info
_strategy_source_authority_context_for_sell_candidate
```

At that source commit, the active code path is:

```text
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:483-486
sell_pending_items = tuple(_pending_item(item) ...)

src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:979-996
_pending_item constructs listed_info with:
market = 東証
product_category = 011
security_type = 011
current_listed = true
```

Therefore for the recorded target run:

```text
D44 helper called = NO
D44 canonical resolver result for 93990 = NOT INVOKED
Actual candidate producer = sell_pipeline._pending_item
Actual PendingOrderItem constructor path = sell_pipeline._pending_item -> PendingOrderItem(...)
```

## Runtime Artifact Lineage

PM decision:

```text
artifact = reports/runtime_tests/runs/runtime-test-historical-smoke-20260807T130749981758Z/daily/2023-06-02/position_management/pm_decisions.json
symbol = 93990
pm_decision_id = pm-2023-06-02-93990-exit
decision_type = EXIT
quantity_requested = 600
listed_info = absent
```

Strategy runtime planning:

```text
artifact = .../strategy/runtime_planning.json
planning_id = rp-2023-06-02-93990-sell_exit-20e500acea55959f
planning_intent = SELL_EXIT
source_pm_decision_id = pm-2023-06-02-93990-exit
listed_info = null
```

SELL Planning generated candidate:

```text
artifact = .runtime/runtime_state/sell_pipeline/2023-06-02/order_plan.json
pending_item_id = opi-sell-exit-pm-93990-002
source_decision_id = pm-2023-06-02-93990-exit
listed_info authority = PM_BASIC_EXECUTION_METADATA
market = 東証
product_category = 011
security_type = 011
```

Existing pending:

```text
artifact = .runtime/pending_order_plan/pending_order_plan.json
existing_pending_item_id = strategy-a554f4e0fb84b6736786
listed_info authority = canonical_pit_listed_issues
market = スタンダード
product_category = 021
security_type = 021
```

Reconciliation:

```text
artifact = .runtime/runtime_state/sell_pipeline/2023-06-02/pending_sell_reconciliation_evidence.json
existing_authority_type = CANONICAL_PIT_LISTED_ISSUE_AUTHORITY
new_authority_type = PM_BASIC_EXECUTION_METADATA
core_identity_match_status = MISMATCH
conflict_status = CONFLICTING_LISTED_INFO
reason_code = PENDING_SELL_LISTED_INFO_AUTHORITY_CONFLICT
```

## Canonical Availability

Canonical source availability is confirmed:

```text
artifact = reports/runtime_tests/runs/runtime-test-historical-smoke-20260807T130749981758Z/daily/2023-06-02/strategy/input_manifest.json
strategy_source_authority.status = PASS
listed_issues.pit_status = PASS
listed_issues.exists = true
business_date = 2023-06-02
```

Direct read-only resolver invocation with the real `strategy_source_authority` returns:

```text
93990:
market = スタンダード
product_category = 021
security_type = 021
listed_info_authority = canonical_pit_listed_issues
listed_info_row_id = canonical_listed_issues:2023-06-02:93990
```

Therefore:

```text
canonical available in real Runtime = YES
canonical data unavailable = NO
```

## Focused Replay vs Real Runtime

D44 focused replay:

```text
environment_capability_context.strategy_source_authority = injected directly
_strategy_source_authority_context_for_sell_candidate returns direct authority
manifest fallback not exercised
canonical mapping for 93990 = 021 / 021
candidate listed_info = canonical
```

Real Runtime context:

```text
environment_capability_context.strategy_source_authority = absent
environment_capability_context.strategy_input_manifest_path = absent
environment_capability_context.runtime_test_evidence_root = present
```

The current D44 workspace helper tries:

```text
runtime_test_evidence_root/daily/2023-06-02/strategy/input_manifest.json
```

but `_strategy_source_authority_from_manifest_path` calls `_read_json(path)` inside `sell_pipeline.py`, and `sell_pipeline.py` has no `_read_json` function. The broad exception handler returns `{}`.

Thus, even after D44 code is present:

```text
manifest authority lookup = {}
canonical mapping = {}
fallback to _pending_item PM Basic = YES
fallback legitimate = NO
```

First focused-vs-real divergence:

```text
focused replay provided direct strategy_source_authority
real Runtime provided only runtime_test_evidence_root
```

Second divergence in current D44 code:

```text
manifest fallback uses undefined _read_json and silently returns empty authority
```

## 59550 / 76470 / 93990

All three new SELL candidates are PM Basic in the real SELL Planning candidate path:

```text
59550 new_authority_type = PM_BASIC_EXECUTION_METADATA
76470 new_authority_type = PM_BASIC_EXECUTION_METADATA
93990 new_authority_type = PM_BASIC_EXECUTION_METADATA
```

59550 and 76470 pass only because canonical existing pending and PM Basic candidate core identity both use:

```text
product_category = 011
security_type = 011
```

93990 fails because canonical existing pending is:

```text
product_category = 021
security_type = 021
```

This is systemic SELL candidate authority propagation failure, surfaced only by 93990's 021/021 core identity.

## Producer Inventory

Active production Runtime SELL candidate producer:

```text
run_daily_operation.py:773-790
passes pm_result.sell_exit_decisions to run_sell_planning_pending_pipeline

sell_pipeline.py:_pending_item
constructs SELL PendingOrderItem and PM Basic listed_info
```

Strategy SELL candidate producer:

```text
strategy_authority.py:_pending_item_from_strategy_plan
uses canonical PIT listed-info for SELL after D14
```

The D43/D45 failing candidate is not the strategy SELL producer. It is the PM SELL Planning producer.

Multiple active SELL candidate producers:

```text
YES
strategy SELL producer
PM SELL Planning producer
```

Production Runtime authoritative owner for this defect:

```text
runtime_v2.planning.sell_pipeline.run_sell_planning_pending_pipeline
```

## D43 / D3 / D8 / D16

D43 remains valid:

```text
hardcoded/basic SELL candidate core identity causes 93990 conflict
```

D16 remains valid:

```text
canonical-over-PM precedence only permits market semantics mismatch after core identity matches
93990 core identity mismatch must fail closed
```

D3/D8/D16 are not repair targets for D46.

## Root Cause

Root Cause:

```text
The target run did not execute D44's canonical SELL candidate enrichment because the recorded source commit did not contain the D44 helper. In the current D44 workspace code, the focused test passed by injecting strategy_source_authority directly, but the real Runtime invocation supplies only runtime_test_evidence_root. That manifest fallback path calls an undefined _read_json in sell_pipeline.py, catches the exception, returns empty authority, and leaves _pending_item's PM Basic listed_info in place.
```

Repair Required:

```text
YES
```

Minimal D46 Scope:

```text
Fix the active PM SELL Planning candidate authority resolver so runtime_test_evidence_root / strategy_input_manifest_path loads strategy_source_authority correctly, and prove opi-sell-exit-pm-93990-002 receives canonical 021/021 before reconciliation.
```

Do not duplicate canonical resolution in D3/D8/D16, Submit Guard, or Broker.

## Deliverables

```text
docs/phase_reports/phase28_d45_sell_candidate_canonical_listed_info_runtime_propagation_gap_root_cause.md
reports/phase_reports/phase28_d45_sell_candidate_canonical_listed_info_runtime_propagation_gap_root_cause.json
reports/phase28_d45_sell_candidate_canonical_listed_info_runtime_propagation_gap_root_cause/
```
