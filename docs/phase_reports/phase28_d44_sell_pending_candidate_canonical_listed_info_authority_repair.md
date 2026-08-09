# Phase28-D44: SELL Pending Candidate Canonical Listed-Info Authority Repair

## Judgment

Primary Judgment:

```text
PHASE28_D44_SELL_CANDIDATE_CANONICAL_LISTED_INFO_AUTHORITY_REPAIRED_SHORT_VALIDATION_PASS
```

Supporting Judgment:

```text
PHASE28_D44_SELL_PENDING_CORE_IDENTITY_REPAIR_FRESH_100BD_READY
```

Fresh Test Entry:

```text
READY
```

D44 implemented one repair only: SELL pending candidate `listed_info` now consumes Canonical PIT Listed Issues before `PendingOrderItem` materialization. PM basic metadata remains only as fallback when canonical authority is unavailable.

No config, schema, threshold, Submit Guard, Broker, Pending Composition, D14, D12, Phase28-C, Portfolio Construction, Position Sizing, or Runtime Planning change was made. No resume, fresh run, long historical run, or runtime mutation was executed.

## Root

D43 confirmed the 2023-06-02 HALT was not caused by D16 itself. D16 correctly rejected a true core identity mismatch:

```text
existing 93990 listed_info:
Canonical PIT Listed Issues
market = スタンダード
product_category = 021
security_type = 021

new PM SELL candidate listed_info:
PM Basic hardcoded in sell_pipeline._pending_item
market = 東証
product_category = 011
security_type = 011
```

The first incorrect producer was:

```text
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:_pending_item
```

It invented SELL candidate core identity fields instead of consuming canonical listed-info authority.

## Implementation

Changed file:

```text
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
```

New flow:

```text
executable PM SELL decisions
↓
_canonical_sell_candidate_listed_info_by_symbol
↓
strategy_source_authority / strategy input_manifest
↓
Canonical PIT Listed Issues resolver
↓
_pending_item_with_sell_candidate_listed_info
↓
PendingOrderItem.listed_info = canonical row
↓
D3/D8/D16 reconciliation
```

Authority priority:

```text
1. Canonical PIT Listed Issues
2. PM basic fallback only when canonical authority is unavailable
```

The repair reuses the D14 canonical resolver:

```text
runtime_v2.planning.strategy_authority._canonical_listed_info_from_strategy_source_authority
```

Resolution sources:

```text
environment_capability_context.strategy_source_authority
environment_capability_context.strategy_input_manifest_path
runtime_test_evidence_root/daily/<business_date>/strategy/input_manifest.json
```

## 93990 Result

Focused replay:

```text
symbol = 93990
side = SELL
intent = EXIT
existing_pending_item_id = strategy-fd750c0ea2bcc16bd06a
pm_decision_id = pm-2023-06-02-93990-exit
quantity = 600
```

Generated candidate listed-info after D44:

```text
code = 93990
market = スタンダード
product_category = 021
security_type = 021
current_listed = true
listed_info_authority = canonical_pit_listed_issues
```

Result:

```text
PASS
PENDING_SELL_LISTED_INFO_AUTHORITY_CONFLICT absent
existing pending item preserved
```

## Validation

Passed:

```text
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py \
  tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py -q

15 passed
```

Passed:

```text
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase28_d14_strategy_sell_30410_uses_canonical_listed_info_without_opportunity \
  tests/strategy/test_phase22_d_position_management.py::test_phase28_d12_runtime_current_adapter_reads_runtime_pm_decision_type \
  tests/strategy/test_phase22_d_position_management.py::test_phase28_d12_runtime_current_adapter_preserves_action_decision_priority_and_conflict_evidence \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_c_canonical_add_bridge_increases_existing_target_weight_when_incremental_evidence_passes \
  tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_target_weight_bridge_reaches_positive_quantity_delta -q

8 passed
```

Passed:

```text
selected REDUCE / EXIT semantics from tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py

8 passed
```

Passed:

```text
py_compile = PASS
git diff --check = PASS
JSON validation = PASS
```

Note:

```text
Full tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py has one stale pre-D3 expectation:
test_phase19_bt_reduce_pending_sell_conflict_review_required

Observed current behavior = PASS via D3 reconciliation-compatible path.
D44 did not modify that path.
```

## Final Fields

Implemented repair:

```text
SELL pending candidate canonical listed_info authority enrichment
```

Changed files:

```text
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py
```

Canonical listed-info source:

```text
Canonical PIT Listed Issues
```

Runtime Authority violation:

```text
NO
```

Performance change:

```text
NO
```

Config / Schema / Threshold changed:

```text
NO / NO / NO
```

Resume / Fresh / Long Historical:

```text
NO / NO / NO
```

fresh100BD:

```text
READY
```

## Deliverables

```text
docs/phase_reports/phase28_d44_sell_pending_candidate_canonical_listed_info_authority_repair.md
reports/phase_reports/phase28_d44_sell_pending_candidate_canonical_listed_info_authority_repair.json
reports/phase28_d44_sell_pending_candidate_canonical_listed_info_authority_repair/
```
