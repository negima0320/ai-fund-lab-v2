# Phase24-E5 Historical Pending Top-Level Safety Authority Resolution Audit and Repair

## 1. Primary Judgment

`PHASE24_E5_HISTORICAL_PENDING_SAFETY_AUTHORITY_RESOLVED_SHORT_VALIDATION_PASS`

Phase24-E5 identified and repaired the remaining Historical Pending Safety Authority resolution gap after Phase24-E3.

The repair is limited to canonical Pending Safety Authority envelope materialization and Data Readiness validation. SELL item binding, Strategy, PM decisions, quantities, price authority, cash, position count, Safety Decision content, Submit criteria, broker write, J-Quants fetch, fresh-run, and 20BD Runtime revalidation were not changed or executed.

## 2. Direct Root Cause

Phase24-E3 successfully bound BUY and SELL items, but composite Pending top-level `safety_context` still lacked runtime test lineage:

```text
safety_context.runtime_test_run_id
safety_context.runtime_test_profile_id
safety_context.runtime_test_evidence_root
```

Data Readiness reads Pending top-level `safety_context` as the primary Historical Pending Safety Authority envelope. Item-level lineage alone is insufficient.

In run `runtime-test-historical-extended-smoke-20260731T030635706513Z`, Data Readiness reported:

```text
components.pending.historical_pending_safety_authority.status = REVIEW_REQUIRED
components.pending.historical_pending_safety_authority.reason = historical_pending_safety_authority_mismatch
mismatched_fields:
  safety_context.runtime_test_evidence_root
  safety_context.runtime_test_profile_id
  safety_context.runtime_test_run_id
```

Submit then consumed Data Readiness and halted with:

```text
historical_safety_temporal_authority_missing
pending_safety_evidence_missing
```

## 3. Data Readiness Authority Source

Data Readiness reads:

```text
.runtime/pending_order_plan/pending_order_plan.json
  safety_context
  items[]
  target_session_date
  environment
  approval.safety_decision_id
  safety_decision_id
```

The primary authority resolver is:

```text
src/ai_fund_lab_v2/runtime_v2/data_readiness.py
  _historical_pending_safety_authority(...)
```

Submit consumes Data Readiness output. It does not independently repair or infer missing safety authority.

## 4. Reviewed Evidence

Reviewed required evidence:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T030635706513Z/daily/2022-07-15/data_readiness/data_readiness.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T030635706513Z/daily/2022-07-15/data_readiness/runtime_manifest.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T030635706513Z/daily/2022-07-15/submit/runtime_manifest.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T030635706513Z/daily/2022-07-15/sell_planning/data_readiness_authority.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T030635706513Z/daily/2022-07-15/sell_planning/pending_continuity_evidence.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T030635706513Z/daily/2022-07-15/sell_planning/sell_planning_manifest.json
.runtime/pending_order_plan/pending_order_plan.json
```

Confirmed:

```text
Pending state = APPROVED
target_session_date = 2022-07-15
top-level safety_context has safety_authority/date/decision/policy/source
top-level safety_context lacks runtime_test_* lineage
BUY item 23880 has complete authority and runtime lineage
SELL item 66590 has complete authority and runtime lineage
Data Readiness pending authority = REVIEW_REQUIRED
Submit final_state = REVIEW_REQUIRED
```

## 5. Pending Top-Level And Item Contract

Canonical Historical Pending Safety Authority envelope:

```text
Pending top-level safety_context:
  safety_authority
  safety_business_date
  safety_decision
  safety_decision_id
  safety_policy_version
  safety_reason
  safety_source
  temporal_authority_business_date
  runtime_test_run_id
  runtime_test_profile_id
  runtime_test_evidence_root
```

Each active BUY / SELL item must bind the same Submit-session authority:

```text
safety_authority
safety_business_date
safety_decision
safety_decision_id
safety_policy_version
safety_source
temporal_authority_business_date
runtime_test_run_id
runtime_test_profile_id
runtime_test_evidence_root
```

Top-level and item mismatch remains `REVIEW_REQUIRED`.

## 6. Authority Unresolved Point

The unresolved point was:

```text
src/ai_fund_lab_v2/runtime_v2/pending/promotion.py
  _safety_context_from_items(...)
```

When composite Pending was promoted from BUY + SELL items, `_safety_context_from_items` reconstructed top-level `safety_context` from item safety fields but did not copy item `runtime_test_*` lineage into the top-level envelope.

This replaced the complete SELL Planning context with a top-level context that was safety-valid but lineage-incomplete.

## 7. Implementation

Updated:

```text
src/ai_fund_lab_v2/runtime_v2/pending/promotion.py
src/ai_fund_lab_v2/runtime_v2/data_readiness.py
tests/runtime_v2/test_phase13_p_pending_promotion.py
tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py
tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py
```

Created:

```text
docs/phase_reports/phase24_e5_historical_pending_top_level_safety_authority_resolution_audit_and_repair.md
reports/phase_reports/phase24_e5_historical_pending_top_level_safety_authority_resolution_audit_and_repair.json
```

Behavior:

```text
Pending promotion now carries runtime_test_run_id/profile_id/evidence_root from authoritative items into top-level safety_context.
Data Readiness now validates top-level safety_context and every active item for safety authority/date/decision/policy/source/runtime lineage consistency.
Pending-safety READY now marks historical_neutral_authority_generated_or_resolved=true for active APPROVED Pending.
EMPTY no-action Pending keeps the existing Phase24-E1 semantics.
```

## 8. Responsibility Boundary

Producer / materializer:

```text
Pending item producers bind item-level Safety Authority.
Pending promotion/composition materializes the canonical top-level Safety Authority envelope.
```

Consumer:

```text
Data Readiness validates top-level and item authority consistency.
Submit consumes Data Readiness result.
```

Submit does not generate missing authority, and Data Readiness does not pass on a bare `NEUTRAL` string.

## 9. Fail-Closed Maintained

Still `REVIEW_REQUIRED`:

```text
top-level Authority missing
item Authority missing
top-level runtime_test lineage missing
item runtime_test lineage missing
top-level / item run_id mismatch
business date mismatch
decision_id mismatch
policy version mismatch
evidence_root mismatch
future Authority
latest fallback
wrong environment
```

## 10. Tests

Added / updated tests cover:

```text
Promotion materializes top-level runtime_test lineage from item safety authority.
Composite BUY+SELL Pending top-level and items share complete Historical Safety Authority.
Composite Historical Pending resolves Data Readiness safety authority.
Item lineage missing remains REVIEW_REQUIRED.
Top-level run_id mismatch remains REVIEW_REQUIRED.
Existing historical mismatch tests now assert item mismatch is also surfaced.
EMPTY no-action Pending contract remains unchanged.
Demo / production safety contracts remain covered by existing regression set.
```

## 11. Validation

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase13_p_pending_promotion.py tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py tests/runtime_v2/test_phase23_i_strategy_planning_authority.py tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py tests/runtime_v2/test_phase17_bf_empty_pending_submit_contract.py tests/runtime_v2/test_phase19_bi_empty_pending_no_action_contract.py tests/runtime_v2/test_phase23_ab_no_order_submit_guard.py -q
78 passed, 60 warnings in 4.14s
```

Also executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2/pending/promotion.py src/ai_fund_lab_v2/runtime_v2/data_readiness.py src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
PASS

git diff --check
PASS
```

## 12. Runtime Execution Boundary

Not executed:

```text
20BD Runtime revalidation
fresh-run
broker write
J-Quants fetch
Strategy change
PM change
quantity change
price change
Safety judgement relaxation
Submit fail-open
2022-07-15 special branch
23880 / 66590 special branch
```

## 13. Residual Gap

Operator revalidation is still required to confirm the repaired code clears the original 2022-07-15 Submit boundary in a full Runtime run.

Existing non-E5 observations such as Strategy Shadow review status and capital policy display fields are unchanged.

## 14. Operator Revalidation Method

Recommended:

```text
1. Rerun the failed validation boundary or the same 20BD revalidation after Evidence Review.
2. Inspect .runtime/pending_order_plan/pending_order_plan.json for 2022-07-15.
3. Confirm top-level safety_context includes:
   runtime_test_run_id
   runtime_test_profile_id
   runtime_test_evidence_root
4. Confirm BUY item 23880 and SELL item 66590 match top-level Safety Authority.
5. Confirm Data Readiness:
   pending_status = READY
   safety_status = READY
   historical_neutral_authority_generated_or_resolved = true
   pending_safety_evidence_missing absent
   historical_safety_temporal_authority_missing absent
6. Confirm Submit no longer halts on Historical Safety Temporal Authority missing.
```

## 15. Recommended Next Task

`Phase24-E6 Operator Runtime Revalidation for Historical Pending Safety Authority Resolution`

