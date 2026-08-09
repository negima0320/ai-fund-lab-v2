# Phase28-D43: SELL Pending Listed-Info Authority Conflict Root Cause

## Judgment

Primary Judgment:

```text
PHASE28_D43_SELL_PENDING_LISTED_INFO_CORE_IDENTITY_CONFLICT_ROOT_CAUSE_CONFIRMED
```

Root classification:

```text
PENDING_SECURITY_IDENTITY_AUTHORITY_CONFLICT
```

Repair Required:

```text
YES
```

D43 was read-only diagnosis. No implementation, config change, schema change, threshold change, resume, fresh run, long historical run, or runtime mutation was performed.

## Target

```text
run_id = runtime-test-historical-smoke-20260807T110037147037Z
business_date = 2023-06-02
halt_stage = sell_planning
exit_code = 20
```

Direct artifact:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260807T110037147037Z/daily/2023-06-02/sell_planning/pending_continuity_evidence.json
```

Observed direct reason:

```text
PENDING_SELL_LISTED_INFO_AUTHORITY_CONFLICT;
PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED
```

The coarse sell-planning artifact did not expose field-level conflict details. The detailed reconciliation evidence was recovered from:

```text
.runtime/runtime_state/sell_pipeline/2023-06-02/pending_sell_reconciliation_evidence.json
```

## Direct HALT Producer

Direct HALT Producer:

```text
runtime_v2.pending.composition.reconcile_with_existing_sell_pending
```

Code trace:

```text
src/ai_fund_lab_v2/runtime_v2/pending/composition.py:300-324
compatible SELL update enters required authority merge

src/ai_fund_lab_v2/runtime_v2/pending/composition.py:340-350
review_reasons produce ORIGINAL_PENDING_PRESERVED and PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED

src/ai_fund_lab_v2/runtime_v2/pending/composition.py:652-693
listed_info merge evaluates equivalence / precedence / REVIEW_REQUIRED conflict

src/ai_fund_lab_v2/runtime_v2/pending/composition.py:777-780
core identity mismatch returns core_identity_mismatch

src/ai_fund_lab_v2/runtime_v2/pending/composition.py:786-799
canonical-over-PM precedence is only allowed after core fields match
```

New SELL candidate listed-info producer:

```text
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:1069-1086
_pending_item(...)
```

That function materializes PM basic execution metadata as:

```text
code = item.symbol
market = 東証
product_category = 011
security_type = 011
current_listed = true
```

## Conflicting Symbol

Only one symbol conflicted:

```text
93990
```

Non-conflicting same-day SELL pending reconciliations:

```text
59550 SELL_EXIT = PASS via canonical-over-PM market precedence
76470 SELL_REDUCE = PASS via canonical-over-PM market precedence
```

Failing reconciliation:

```text
symbol = 93990
existing_pending_item_id = strategy-fd750c0ea2bcc16bd06a
new_pending_item_id = opi-sell-exit-pm-93990-002
existing_intent = EXIT
new_intent = EXIT
existing_quantity = 600
new_quantity = 600
conflict_status = CONFLICTING_LISTED_INFO
core_identity_match_status = MISMATCH
```

## Existing Pending

Existing active pending:

```text
pending_plan_id = pending-strategy-plan-historical-2023-06-02-3622adc89c2e5341
plan_created_date = 2023-06-02
target_session_date = 2023-06-02
state = APPROVED
consume.consumed = false
```

For 93990:

```text
side = SELL
intent = EXIT
quantity = 600
source date = 2023-06-02
listed_info authority = canonical_pit_listed_issues
```

Existing canonical listed-info:

```text
code = 93990
market = スタンダード
product_category = 021
security_type = 021
current_listed = true
listed_info_business_date = 2023-06-02
listed_info_row_id = canonical_listed_issues:2023-06-02:93990
listed_info_source = run-scoped historical as-of listed_issues
```

The item is legitimately active: same-day, approved, unconsumed, same target session.

## New Candidate

New PM candidate:

```text
PM action = EXIT
PM decision id = pm-2023-06-02-93990-exit
PM reason = trend_and_opportunity_broken
strategy planning intent = SELL_EXIT
planning id = rp-2023-06-02-93990-sell_exit-aae8c0798d961a9c
planned quantity = 600
```

New candidate listed-info reconstructed from `sell_pipeline._pending_item`:

```text
code = 93990
market = 東証
product_category = 011
security_type = 011
current_listed = true
authority type = PM_BASIC_EXECUTION_METADATA
```

## Exact Authority Mismatch

Field-level mismatch:

| Field | Existing Canonical | New PM Basic | Meaning |
|---|---:|---:|---|
| code | 93990 | 93990 | match |
| market | スタンダード | 東証 | market-semantics mismatch |
| product_category | 021 | 011 | core identity mismatch |
| security_type | 021 | 011 | core identity mismatch |
| current_listed | true | true | match |

D16 permits canonical-over-PM precedence for market-semantics mismatch only after core fields match:

```text
code
product_category
security_type
current_listed
```

For 93990, core fields do not match. Therefore this is not the D16 market-only case. The current fail-closed result is expected for the current predicate.

## First Divergence Point

First divergence:

```text
sell_pipeline._pending_item hardcodes product_category/security_type = 011
```

This is harmless for symbols whose canonical PIT listed-info is also `011`, as seen for 59550 and 76470. It fails for 93990 because canonical PIT authority says:

```text
product_category = 021
security_type = 021
```

## D3 Relationship

D3 relationship:

```text
PARTIAL
```

D3 did its base job:

```text
same symbol = true
side = SELL
existing intent = EXIT
new intent = EXIT
quantity = 600 vs 600
classification = SAME_SYMBOL_COMPATIBLE_UPDATE
```

The halt occurred after D3 classification, in the later required authority merge layer added by D8/D16. This is a D3 uncovered subtype, not a regression of the original D3 same-symbol reconciliation repair.

## PM Intent Audit

SELL-relevant PM decisions on 2023-06-02:

| Symbol | PM Action | PM Reason | Strategy Intent | Existing Intent | New Intent | Result |
|---|---|---|---|---|---|---|
| 59550 | EXIT | hard_stop_current_return; profit_retention_break | SELL_EXIT | EXIT | EXIT | PASS |
| 76470 | REDUCE | peak_drawdown_warning | SELL_REDUCE | REDUCE | REDUCE | PASS |
| 93990 | EXIT | trend_and_opportunity_broken | SELL_EXIT | EXIT | EXIT | REVIEW_REQUIRED |

This is not REDUCE vs EXIT escalation. REDUCE != EXIT semantics are preserved.

## Original Preservation

Original pending preserved:

```text
YES
```

Evidence:

```text
resolution_action = ORIGINAL_PENDING_PRESERVED
replaced_item_ids = []
superseded_item_ids = []
new_item_ids = []
existing pending item ids remain:
  strategy-ef0fe783100c6660e111
  strategy-d6fc55d2695266a9d00c
  strategy-fd750c0ea2bcc16bd06a
```

Partial runtime mutation:

```text
NO pending-plan mutation by reconciliation
```

Sell Planning wrote review/evidence artifacts. It did not replace or supersede the active pending plan.

## Historical Scope

Historical-only defect:

```text
NO
```

The defect is in common Runtime code:

```text
sell_pipeline._pending_item
pending.composition listed_info reconciliation
```

Historical safety authority only allowed the replay to reach sell planning. Safety is not the direct HALT producer.

## Causality

```text
D39 = INDIRECT
D42 = INDIRECT
D3 = PARTIAL
```

D39/D42 allowed the run to pass the 2023-06-01 passive-convergence boundary and expose the 2023-06-02 pending reconciliation path. That is exposure, not defect causality.

D3 is partial because its reconciliation path is the layer where the conflict is handled, but the specific failure is the D8/D16 required listed-info authority subtype.

## Root Cause

Root cause:

```text
For 93990 same-day SELL_EXIT reconciliation, existing pending listed_info came from canonical PIT listed issues with product_category/security_type 021, while the new sell-planning PM candidate listed_info was PM basic execution metadata hardcoded to product_category/security_type 011. D16 precedence only permits market-semantics mismatch when core identity fields match, so the core identity mismatch correctly failed closed as PENDING_SELL_LISTED_INFO_AUTHORITY_CONFLICT.
```

This is not:

```text
Safety HALT
D39 regression
D42 regression
REDUCE/EXIT escalation conflict
stale active pending lifecycle defect
```

## Minimal Repair Scope

Next Phase:

```text
Phase28-D44
```

Minimal repair:

```text
SELL pending candidate listed_info authority repair for PM basic execution metadata product_category/security_type.
```

D44 should consume canonical listed-info or otherwise avoid hardcoded `011` core identity for SELL candidates. It must preserve D16 fail-closed behavior for true core identity conflicts.

Do not change:

```text
D39
D42
D3 base reconciliation
Portfolio Construction
Position Sizing
Runtime Planning
Submit
Broker
Config
Schema
Threshold
```

## Evidence

Evidence directory:

```text
reports/phase28_d43_sell_pending_listed_info_authority_conflict_root_cause/
```

Files:

```text
conflicting_symbol_inventory.json
existing_pending_inventory.json
new_sell_candidate_inventory.json
listed_info_authority_diff.json
reconciliation_code_trace.json
d3_contract_comparison.json
pm_intent_comparison.json
pending_lifecycle_audit.json
original_preservation_audit.json
historical_vs_production_scope.json
causality_matrix.json
root_cause.json
minimal_repair_scope.json
next_phase_contract.json
open_gap_inventory.json
```
