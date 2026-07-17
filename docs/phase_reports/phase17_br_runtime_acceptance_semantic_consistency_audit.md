# Phase17-BR Runtime Acceptance Semantic Consistency Audit

## Executive Summary

Phase17-BR audited the accepted clean Historical Smoke run from semantic and accounting perspectives, without executing Runtime Test, mutating the Frozen Run, editing `.runtime`, refreshing Registry, fetching market data, writing broker state, or sending external notifications.

- Target run: `runtime-test-historical-smoke-20260715T232527885578Z`
- Operator-reported baseline: Run PASS, Validate PASS, 40/40 jobs exit 0, full Runtime v2 regression 874 passed
- Final ledger state: cash `191600.0`, market value `813700.0`, total equity `1005300.0`, positions `5`
- Final judgment: `PHASE17_BR_TARGETED_FIX_REQUIRED`

The Runtime execution path is not rejected by this audit. Current accounting projection is safe for the inspected path. However, Phase17 close should include a targeted ledger/performance-event contract fix because the persistent ledger currently stores both raw and equivalent execution representations, and performance consumers need an explicit canonical view to avoid future double counting.

## Finding Inventory

| ID | Subject | Classification | Severity | Runtime Decision | Accounting | Performance Metrics | Fix Before Close |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BR-F1 | Morning no-signal reason when max position slots are exhausted | `DIAGNOSTIC_REASON_DEFECT` | LOW | false | false | false | false |
| BR-F2 | Persistent ledger contains raw and canonical-looking order/execution rows for the same five fills | `DUPLICATE_REPRESENTATION_WITH_SAFE_CONSUMERS` | MEDIUM | false | false | true | true |
| BR-F3 | Position mutation date remains 2026-07-06 while valuation advances to 2026-07-10 | `CORRECT_POSITION_MUTATION_DATE` | INFO | false | false | false | false |
| BR-F4 | Intermediate Safety REVIEW_REQUIRED/neutral transitions versus final READY/ALLOW authority | `CORRECT_FAIL_CLOSED_THEN_RESOLVED` | LOW | false | false | false | false |

## BR-F1 Morning No-Signal Reason

Classification: `DIAGNOSTIC_REASON_DEFECT`

From 2026-07-07 through 2026-07-10, morning planning emits `NO_SIGNAL:available_cash_missing_or_zero` while `available_cash` is 191,600 and `planning_budget` is positive. The binding predicate is not cash: the portfolio already holds five positions while `morning_policy_max_positions=5`, so the derived effective order limit is zero.

This does not change the Runtime decision because order count remains zero for a valid reason, but the diagnostic reason is misleading. Recommended correction is to split the compound guard in `morning_pipeline.py` and emit a slot-specific reason such as `NO_SIGNAL:max_positions_reached_or_no_available_slots`.

Evidence:

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T232527885578Z/daily/2026-07-07/morning/planning_evidence.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T232527885578Z/daily/2026-07-08/morning/planning_evidence.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T232527885578Z/daily/2026-07-09/morning/planning_evidence.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T232527885578Z/daily/2026-07-10/morning/planning_evidence.json`

## BR-F2 Order / Execution Ledger Lineage

Classification: `DUPLICATE_REPRESENTATION_WITH_SAFE_CONSUMERS`

The final persistent ledger contains 10 order rows and 10 execution rows for five BUY targets:

- Five submit order records from `runtime_v2_submit_pipeline`
- Five readonly broker order records from `runtime_v2_execution_readonly_simulation`
- Five raw broker-detail execution rows with `execution_evidence_type=broker_detail_execution`
- Five execution-equivalent rows with `execution_evidence_type=execution_equivalent`

The inspected accounting consumer is safe: `runtime_owned_fill_projection.py` filters cash and realized-PnL projection to `execution_evidence_type == "execution_equivalent"`, so final cash and positions are not double counted. The remaining risk is semantic: a future backtest/performance consumer could count both raw broker-detail and equivalent execution rows unless a canonical performance/event contract is explicit and tested.

This is the only finding that requires a targeted fix before Phase17 close.

Evidence:

- `.runtime/persistent_ledger/orders.jsonl`
- `.runtime/persistent_ledger/executions.jsonl`
- `.runtime/persistent_ledger/positions.jsonl`
- `.runtime/persistent_ledger/state.json`
- `reports/phase17_br_runtime_acceptance_semantic_consistency_audit/order_execution_lineage.json`

## BR-F3 Position State and Valuation Dates

Classification: `CORRECT_POSITION_MUTATION_DATE`

`position_state_as_of=2026-07-06` is correct because 2026-07-06 is the last Runtime-owned position mutation date. `valuation_as_of=2026-07-10` and per-position `valuation_as_of=2026-07-10` are also correct because valuation refreshes may advance independently on no-fill days.

This matches the temporal freshness contract: position quantity authority and valuation authority are intentionally separate.

Evidence:

- `.runtime/persistent_ledger/state.json`
- `.runtime/persistent_ledger/positions.jsonl`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `reports/phase17_br_runtime_acceptance_semantic_consistency_audit/temporal_authority_matrix.json`

## BR-F4 Safety Effective Decision Semantics

Classification: `CORRECT_FAIL_CLOSED_THEN_RESOLVED`

Intermediate fail-closed or neutral Safety diagnostics exist in artifacts, but daily Data Readiness and Morning manifests expose explicit final/effective Safety authority fields. The accepted path has final/effective Safety READY/PASS with historical daily neutral or pending Safety authority as appropriate, and the Phase17-BJ previous-empty-pending exclusion remains visible in Evidence.

No Safety authority defect or environment leakage was identified. The main recommendation is documentation/schema guidance: consumers should read final/effective Safety fields rather than grep raw intermediate diagnostics.

Evidence:

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T232527885578Z/daily/2026-07-08/data_readiness/data_readiness.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T232527885578Z/daily/2026-07-08/morning/runtime_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T232527885578Z/daily/2026-07-09/data_readiness/data_readiness.json`
- `reports/phase17_br_runtime_acceptance_semantic_consistency_audit/safety_effective_decision_matrix.json`

## Acceptance Impact

Phase17-BR does not invalidate the successful Historical Smoke Run. It does identify one targeted acceptance closure item:

1. Define a canonical persistent ledger performance/event contract so exactly one execution representation contributes to trade count, turnover, return, and long-term performance metrics.
2. Add regression tests that prove five BUY targets produce five canonical performance fills, not ten.
3. Optionally improve lineage fields between submit orders, readonly broker orders, broker-detail executions, and execution-equivalent rows.
4. Separately improve the Morning no-signal diagnostic reason for max-position exhaustion.

## Files Created

- `reports/phase17_br_runtime_acceptance_semantic_consistency_audit/summary.json`
- `reports/phase17_br_runtime_acceptance_semantic_consistency_audit/finding_inventory.json`
- `reports/phase17_br_runtime_acceptance_semantic_consistency_audit/order_execution_lineage.json`
- `reports/phase17_br_runtime_acceptance_semantic_consistency_audit/temporal_authority_matrix.json`
- `reports/phase17_br_runtime_acceptance_semantic_consistency_audit/safety_effective_decision_matrix.json`
- `reports/phase_reports/phase17_br_runtime_acceptance_semantic_consistency_audit.json`

## Commands Executed

Read-only inspection commands were used: `find`, `rg`, `sed`, `python3` JSON extraction, and JSON validation. No Runtime Test execution or Runtime mutation command was run.

## Prohibited Operations Confirmation

- `runtime_test.py run/resume/reset/rollback/close`: not executed
- Frozen Run editing: not performed
- `.runtime` manual edit: not performed
- Ledger manual fix: not performed
- Registry refresh: not performed
- broker write / real submit: not performed
- external notification: not performed
- J-Quants fetch: not performed
- code fix before confirmed issue: not performed

## Final Judgment

`PHASE17_BR_TARGETED_FIX_REQUIRED`
