# Phase28-D46: Active PM SELL Planning Canonical Listed-Info Runtime Context Repair

## Judgment

Primary Judgment:

```text
PHASE28_D46_ACTIVE_PM_SELL_CANONICAL_CONTEXT_REPAIRED_SHORT_VALIDATION_PASS
```

Supporting Judgment:

```text
PHASE28_D46_REAL_RUNTIME_LISTED_INFO_PROPAGATION_REPAIRED_FRESH_100BD_READY
```

Fresh Test Entry Decision:

```text
READY
```

D46 implemented one repair only: active PM SELL Planning can now load `strategy_source_authority` from the real Runtime `runtime_test_evidence_root` manifest path instead of silently falling back to PM Basic metadata.

No config, schema, threshold, Submit Guard, Broker, Pending Composition, D14, D12, Phase28-C, Portfolio Construction, Position Sizing, or Runtime Planning change was made. No resume, fresh run, long historical run, or runtime mutation was executed.

## Implemented Repair

Changed file:

```text
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
```

Repair:

```text
_strategy_source_authority_from_manifest_path
before: undefined _read_json inside broad except Exception -> {}
after: strict local JSON object read via _read_json_object
```

The helper now preserves:

```text
<runtime_test_evidence_root>/daily/<business_date>/strategy/input_manifest.json
strategy_source_authority
```

and malformed JSON / non-object JSON is not silently converted to missing authority.

## Active Runtime Path

Active path:

```text
run_sell_planning_pending_pipeline
↓
_canonical_sell_candidate_listed_info_by_symbol
↓
_strategy_source_authority_context_for_sell_candidate
↓
runtime_test_evidence_root/daily/<business_date>/strategy/input_manifest.json
↓
_canonical_listed_info_from_strategy_source_authority
↓
_pending_item_with_sell_candidate_listed_info
↓
PendingOrderItem
↓
reconcile_with_existing_sell_pending
```

This is the PM SELL Planning producer used by `run_daily_operation.py` for PM `EXIT` / `REDUCE` decisions.

## Real Context Verification

The mandatory real-context fixture did not inject:

```text
strategy_source_authority
strategy_input_manifest_path
```

It provided only:

```text
runtime_test_evidence_root
```

Result:

```text
93990 candidate listed_info authority = canonical_pit_listed_issues
market = スタンダード
product_category = 021
security_type = 021
PENDING_SELL_LISTED_INFO_AUTHORITY_CONFLICT absent
```

Direct read-only resolver check against the D45 real artifact also passed:

```text
59550 = スタンダード / 011 / 011 / canonical_pit_listed_issues
76470 = スタンダード / 011 / 011 / canonical_pit_listed_issues
93990 = スタンダード / 021 / 021 / canonical_pit_listed_issues
```

## Validation

Passed:

```text
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py \
  tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py -q

19 passed
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
selected REDUCE / EXIT semantics
8 passed
```

Passed:

```text
py_compile = PASS
git diff --check = PASS
JSON validation = PASS
```

## Source Provenance Contract

Current source provenance:

```text
git rev-parse HEAD = cd1b47a44234bb66c3a773fe7c0324fe11123000
working tree = dirty
D44/D46 helper presence in workspace = YES
```

Fresh-run acceptance contract:

```text
1. Inspect daily/<date>/sell_planning/subprocess_trace.json.
2. Confirm source_commit/source_dirty provenance represents a source state containing D44/D46.
3. Reject a fresh-run as D46 validation if source provenance predates D46 or does not include:
   _canonical_sell_candidate_listed_info_by_symbol
   _read_json_object
4. Confirm order_plan or reconciliation evidence shows opi-sell-exit-pm-93990-002 is canonical 021/021 before reconciliation.
```

Example checks:

```text
python3 -m json.tool reports/runtime_tests/runs/<run_id>/daily/2023-06-02/sell_planning/subprocess_trace.json
rg -n "_canonical_sell_candidate_listed_info_by_symbol|_read_json_object" src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
```

## Final Fields

Real Runtime context manifest resolution:

```text
PASS
```

D44/D46 helper active on PM SELL Planning path:

```text
YES
```

Fallback taken when canonical available:

```text
NO
```

Malformed manifest behavior:

```text
JSONDecodeError propagates; not silently converted to empty authority
```

Silent programming-error swallowing fixed:

```text
YES
```

Historical-only logic:

```text
NO
```

Runtime Authority violation:

```text
NO
```

Resume / Fresh / Long Historical:

```text
NO / NO / NO
```

## Deliverables

```text
docs/phase_reports/phase28_d46_active_pm_sell_planning_canonical_listed_info_runtime_context_repair.md
reports/phase_reports/phase28_d46_active_pm_sell_planning_canonical_listed_info_runtime_context_repair.json
reports/phase28_d46_active_pm_sell_planning_canonical_listed_info_runtime_context_repair/
```
