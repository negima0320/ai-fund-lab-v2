# Phase28-D8: Compatible SELL Pending Required Authority Merge Implementation

## Scope

Phase28-D8 implemented one Runtime repair only:

```text
When compatible SELL reconciliation preserves an existing pending item,
validate and merge required submit authority fields from the new compatible SELL item.
```

The implementation starts with `listed_info`. No resume, fresh run, or long historical run was executed.

## Pre-Implementation Audit

Primary code path:

```text
src/ai_fund_lab_v2/runtime_v2/pending/composition.py
```

Existing D3 flow was:

```text
classify -> PRESERVE_EXISTING / REPLACE_WITH_NEW / REVIEW_REQUIRED
```

Before D8, `PRESERVE_EXISTING` kept the existing pending item as-is. This preserved pending identity but discarded valid authority fields present only on the new compatible SELL item. This was the D6/D7 root case for `43880` where:

```text
existing strategy SELL_EXIT pending listed_info = null
new PM SELL_EXIT pending listed_info = valid
D3 action = PRESERVE_EXISTING
Submit Guard later sees listed_info null
```

## Implementation

Changed file:

```text
src/ai_fund_lab_v2/runtime_v2/pending/composition.py
```

The D8 merge is invoked only after D3 classification returns:

```text
action == PRESERVE_EXISTING
```

The new helper validates compatible SELL identity/state and then handles `listed_info`:

```text
existing null / new valid        -> FILL_MISSING_FROM_NEW
existing valid / new null        -> PRESERVE_EXISTING
both valid equivalent            -> PRESERVE_EXISTING
both valid conflicting           -> REVIEW_REQUIRED
both null                        -> REVIEW_REQUIRED
```

The existing pending item identity is preserved. Only `listed_info` may be filled when the existing value is missing and the new value is valid and sourced.

## Guardrails

Fail-closed conditions include:

```text
submitted/submitting/post-send existing plan
partial-fill evidence
date/session mismatch
symbol/side mismatch
incompatible SELL lineage
accepted generation mismatch
invalid listed_info schema
both listed_info null
unknown listed_info source
conflicting listed_info
```

On review, the original pending file is not overwritten.

## Evidence Fields

Each preserve reconciliation now records `required_authority_merge` inside the classification payload and an `authority_merge_events` entry with:

```text
listed_info_source
listed_info_source_item_id
listed_info_source_business_date
listed_info_source_artifact
listed_info_source_hash
existing_listed_info_status
new_listed_info_status
merge_action
validation_status
conflict_status
existing_item_hash_before
existing_item_hash_after
pending_plan_hash_before
pending_plan_hash_after
```

## Validation

Commands executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/pending/composition.py tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py -q
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_c_canonical_add_bridge_increases_existing_target_weight_when_incremental_evidence_passes tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_c_canonical_add_bridge_fails_closed_when_expected_edge_evidence_missing tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_target_weight_bridge_reaches_positive_quantity_delta tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_lot_rounding_zero_delta_is_explicit -q
```

Results:

```text
compile: PASS
D8 + D3: 12 passed
Phase28-C focused ADD regression: 4 passed
```

## Final Judgment

```text
Primary Judgment:
PHASE28_D8_SELL_PENDING_AUTHORITY_MERGE_IMPLEMENTED_SHORT_VALIDATION_PASS_FRESH_100BD_READY

Merge Implemented:
YES

listed_info Merge:
YES

43880 Reproduction Fixture:
PASS

Identity Preserved:
YES

Approval Mutated:
NO

Submit Guard Semantics Changed:
NO

Broker Changed:
NO

Phase28-C Changed:
NO

Phase28-D3 Classifier Broken:
NO

BUY Impact:
NO

Repair Scope:
Runtime Pending Composition only

Fresh 100BD Ready:
YES

Restart Entry Decision:
APPROVED

Next Phase:
Phase28-D9 fresh 100BD operator validation
```
