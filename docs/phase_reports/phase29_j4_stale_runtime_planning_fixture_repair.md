# Phase29-J4 Stale Runtime Planning Fixture Repair

## Primary Judgment

PHASE29_J4_STALE_RUNTIME_PLANNING_FIXTURE_REPAIRED_SHORT_REGRESSION_PASS_FRESH_100BD_READY.

## Scope

Test-only fixture repair. No Production code, config, schema, runtime artifact, or Historical/100BD execution was changed.

Changed file:

```text
tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py
```

## Repair

The stale Phase26 fixture now materializes current SELL authority for `7203`:

- canonical `listed_issues` parquet row for `7203`
- `strategy/input_manifest.json`
- `strategy_source_authority`
- canonical listed-info source records

The fixture intentionally does not add Accepted Generation PASS binding. This preserves the intended BUY-side review condition:

```text
accepted_generation_binding_status = REVIEW_REQUIRED
pending state = REVIEW_REQUIRED
buy_items_status = REVIEW_REQUIRED
```

The repaired test now proves:

```text
BUY review remains present
SELL authority is complete
SELL planning status = PASS
pending sell items status = PASS
sell_continuation_allowed = true
```

## Regression

Target:

```text
1 passed
```

Full target file:

```text
4 passed
```

Neighbor SELL regression:

```text
63 passed
```

J2/J1/PC/PS/Runtime/Pending/Submit/Safety short regression:

```text
310 passed
```

Broad relevant regression:

```text
129 passed
```

Compile and diff check:

```text
PASS
```

## Fresh 100BD Gate

Fresh 100BD Ready: YES.

Codex did not run fresh-run, resume, 100BD, or long Historical.

## Deliverables

- `reports/phase29_j4_stale_runtime_planning_fixture_repair/fixture_change_summary.json`
- `reports/phase29_j4_stale_runtime_planning_fixture_repair/current_contract_fields.json`
- `reports/phase29_j4_stale_runtime_planning_fixture_repair/target_test_result.json`
- `reports/phase29_j4_stale_runtime_planning_fixture_repair/neighbor_regression_results.json`
- `reports/phase29_j4_stale_runtime_planning_fixture_repair/j2_non_regression_results.json`
- `reports/phase29_j4_stale_runtime_planning_fixture_repair/fresh_100bd_gate.json`
