# Phase29-L11 Historical Corporate Action Real-Payload Continuation Repair

Status:

```text
COMPLETE
PRODUCTION CODE CHANGED
CONFIG CHANGE: NO
SCHEMA CHANGE: ADDITIVE RUNTIME TEST EVIDENCE ONLY
RUNTIME / PENDING / LEDGER MUTATION DURING CODEX WORK: NO
HISTORICAL EXECUTION: NO
```

Primary Judgment:

```text
PHASE29_L11_HISTORICAL_CA_REAL_PAYLOAD_CONTINUATION_REPAIRED_RETROSPECTIVE_EVIDENCE_ONLY_REPAIR_READY_SHORT_REGRESSION_PASS
```

Real Manifest Shape:

```text
artifact:
reports/runtime_tests/runs/runtime-test-historical-smoke-20260810T232622909184Z/daily/2022-10-28/submit/runtime_manifest.json

top-level item_results present: NO
submit_guard_item_evidence present: YES, list[3]
submitted_count: 2
blocked_count: 1
pending_item_count: 3
final_state: REVIEW_REQUIRED
reason: submit completed with rejected/unknown/blocked items
submit_action: SUBMIT
```

Repair Summary:

```text
classify_historical_corporate_action_quarantine_result now supports both
payload shapes:

1. item_results present: previous path preserved.
2. item_results absent: real Runtime submit manifest path. Eligibility is
   derived from submit_guard_item_evidence plus submitted_count, blocked_count,
   and pending_item_count.

The fallback remains strict. It requires Historical replay, historical_simulated
broker, no actual broker write, Runtime submit REVIEW_REQUIRED, blocked_count
>= 1, every blocked item to be unresolved Corporate Action, all blocked items
to be NOT_SUBMITTED-equivalent by guard evidence, clear separation between PASS
items and blocked items, and exact count consistency.

Generic REVIEW_REQUIRED, mixed blocked reasons, Production, Demo, and actual
broker write remain ineligible.
```

Real Payload Classification:

```text
run_id: runtime-test-historical-smoke-20260810T232622909184Z
business_date: 2022-10-28
job: submit
classification: COMPLETED_WITH_SYMBOL_QUARANTINE
quarantined_symbols: [76920]
all strict checks: PASS
```

76920:

```text
status: REVIEW_REQUIRED
quarantine_status: QUARANTINED
submit_status: NOT_SUBMITTED-equivalent from blocked guard evidence
auto quantity adjustment: NO
split inference: NO
```

Unrelated Items:

```text
unrelated BUY items preserved: YES
resubmitted by repair/classifier: NO
```

Retrospective Repair:

```text
Implemented command:
scripts/runtime_test.py repair-ca-quarantine-continuation

The command is evidence-only and idempotent by design. It does not call Runtime
CLI submit, broker adapters, execution, ledger append, strategy, PM, cash, or
position mutation paths. It first classifies with persist=false, requires
operator confirmation for non-dry-run, then writes only:

- corporate_action_symbol_quarantine_continuation.json
- runtime_state/corporate_action_quarantine/historical_symbol_registry.json
- ca_quarantine_continuation_repair.json
- run_state.json metadata for the already completed submit job

Dry-run was executed against the real halted run and produced classification
eligible=true with state_hashes_before == state_hashes_after. No repair command
was executed in mutating mode during this Codex task.
```

Operator Commands:

```bash
PYTHONPATH=src:. python3 scripts/runtime_test.py repair-ca-quarantine-continuation --profile historical-smoke --run-id runtime-test-historical-smoke-20260810T232622909184Z --business-date 2022-10-28 --job submit --dry-run --json
```

```bash
PYTHONPATH=src:. python3 scripts/runtime_test.py repair-ca-quarantine-continuation --profile historical-smoke --run-id runtime-test-historical-smoke-20260810T232622909184Z --business-date 2022-10-28 --job submit --confirm --yes-i-understand-this-mutates-trading-state --json
```

```bash
PYTHONPATH=src:. python3 scripts/runtime_test.py resume --profile historical-smoke --run-id runtime-test-historical-smoke-20260810T232622909184Z --confirm --yes-i-understand-this-mutates-trading-state
```

Regression Evidence:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase29_l9_historical_ca_quarantine_continuation.py
8 passed

PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase29_l9_historical_ca_quarantine_continuation.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py tests/runtime_v2/test_phase29_l5_raw_ohlcv_materialization.py
23 passed

PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py
21 passed

PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile scripts/runtime_test.py
PASS
```

Resume / Fresh-Run Judgment:

```text
Current halted run without operator repair: Resume Allowed NO.
After successful retrospective evidence-only repair command: Resume Allowed YES.
Fresh-run Required after successful repair: NO.
Fresh-run Required if retrospective repair is not executed: YES.
```

Recommended Next Task:

```text
Phase29-L12 - 93180 Universe Eligibility / Low-Price Opportunity Root Cause Audit
```
