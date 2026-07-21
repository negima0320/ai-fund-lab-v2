# Phase19-BV Runtime Test Summarize / Trade Attribution Command

Final judgment: `PHASE19_BV_RUNTIME_TEST_SUMMARIZE_COMMAND_COMPLETE`

## Scope

Phase19-BV added a read-only Runtime Test post-run summary command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID>
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --write-evidence
```

This phase did not run fresh-run, smoke, or long Runtime tests. It did not change Runtime behavior, PM policy, SELL thresholds, BUY policy, broker behavior, fill generation, Ledger mutation, Current mutation, Pending mutation, Registry authority, Accepted Generation authority, or J-Quants fetch behavior.

Reviewed SoT / contract:

- `docs/02_architecture/runtime_test_specification.md`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/position_management_reduce_quantity_contract.md`
- `docs/02_architecture/position_management_feature_input_contract.md`
- Phase19-BS / BT / BU reports

## Implementation

Changed:

- `scripts/runtime_test.py`
- `tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/03_operations/runtime_test_command_guide.md`

The command reads run evidence from:

```text
reports/runtime_tests/runs/<run_id>/
```

If run-specific final Trading State snapshots are not available, it reads the current Runtime root only when `final_summary.final_state_hashes` exactly match current Runtime root hashes. Otherwise it fails closed with `RUN_FINAL_STATE_HASH_MISMATCH` / `RUN_RUNTIME_ROOT_UNRESOLVED` / `RUN_EVIDENCE_INCOMPLETE` as applicable.

`--write-evidence` writes only to:

```text
reports/runtime_tests/summaries/<summary_id>/
```

## Output Contract

JSON schema:

```text
runtime_test_summary_v1
```

Top-level sections:

- Run Summary
- External Effect Summary
- Performance Summary
- PM Decision Summary
- BUY / SELL Summary
- REDUCE / EXIT Summary
- Trade Attribution
- Current Positions
- Lifecycle Consistency
- Review / Block Summary
- Operator Judgment

Trade-level realized PnL is not guessed. When attribution is not traceable, the command reports:

```text
REVIEW_REQUIRED_TRADE_LEVEL_REALIZED_PNL_NOT_TRACEABLE
```

Negative return does not fail Runtime judgment. It is reported separately as `performance_judgment=NEGATIVE_RETURN_OBSERVED`; `strategy_judgment` remains `NOT_EVALUATED`.

## Runtime Evidence

Existing run summarized:

```text
runtime-test-historical-smoke-20260721T213848054826Z
```

Generated summary evidence:

```text
reports/runtime_tests/summaries/runtime-test-summary-runtime-test-historical-smoke-20260721T213848054826Z-20260721T221640818568Z/
```

Result:

| Item | Value |
|---|---:|
| Runtime judgment | `PASS` |
| Performance judgment | `NEGATIVE_RETURN_OBSERVED` |
| Strategy judgment | `NOT_EVALUATED` |
| Business days | 20 |
| External effect audit count | 80 |
| External effect review count | 0 |
| Final equity | 955100.0 |
| Total return | -44900.0 |
| Total return percent | -4.49 |
| Realized PnL | -51300.0 |
| Unrealized PnL | 6400.0 |
| PM decisions | 46 |
| HOLD | 30 |
| ADD | 9 |
| REDUCE | 4 |
| EXIT | 3 |
| BUY executions | 5 |
| SELL executions | 7 |
| SELL plan items | 7 |
| Current positions | 2 |
| Findings | 0 |

Lifecycle consistency:

| Check | Result |
|---|---:|
| PM_EXIT_TO_SELL_PLAN | PASS |
| PM_REDUCE_TO_PARTIAL_SELL_PLAN | PASS |
| SELL_PLAN_TO_SUBMIT | PASS |
| SELL_SUBMIT_TO_EXECUTION | PASS |
| LEDGER_TO_CURRENT | PASS |
| PENDING_EMPTY_OR_EXPLAINED | PASS |

Trade attribution traced 7 SELL executions to PM decision, SELL plan, quantity contract, execution, and Ledger / Current evidence.

## Regression

Executed short tests only:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile \
  scripts/runtime_test.py \
  tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py

PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py
```

Result:

```text
6 passed
```

Coverage:

- known PASS run summary
- unknown run precondition failure
- human output required sections
- JSON output schema and top-level fields
- negative return does not fail Runtime judgment
- PM decision aggregation
- REDUCE / EXIT source aggregation
- submitted order double-count prevention
- SELL execution aggregation
- current position summary
- trade attribution available case
- trade attribution unavailable review-required case
- lifecycle consistency PASS case
- lifecycle mismatch review-required case
- `--write-evidence` read-only behavior
- historical external effects disabled

## Historical Smoke Reexecution

Not required and not performed. Phase19-BV added a read-only summarizer and tests against fixtures plus existing run evidence only.

