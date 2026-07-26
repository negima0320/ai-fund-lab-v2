# Phase20-BV Historical Runtime End-to-End Authority Wiring Review

## Status

```text
PHASE20_BV_HISTORICAL_RUNTIME_AUTHORITY_WIRING_REVIEW_COMPLETE_WITH_FIXED_DEFECTS_AND_1BD_SMOKE_BLOCKED_BY_ACTIVE_RUN
```

Primary Judgment:

```text
PHASE20_BV_REVIEW_COMPLETE_WITH_CONFIRMED_DEFECTS
```

## Executive Summary

BV reviewed Historical Runtime authority wiring end-to-end instead of stopping at the BU Corporate Action symptom. The review found four High defects across the historical authority chain. Three were already fixed in BS/BT/BU, and one additional BV defect was fixed in this phase.

Counts:

| Metric | Count |
|---|---:|
| Reviewed stages | 22 |
| Authority types | 22 |
| Producer/consumer mismatches | 3 |
| Invalid fallback defects | 3 |
| Temporal defects remaining | 0 |
| BUY/SELL branch contamination | 1 |
| Critical defects remaining | 0 |
| Unfixed High defects | 0 |

## Confirmed Defects

| Defect | Severity | Status | Summary |
|---|---|---|---|
| BV-D01 | High | FIXED_IN_BT | Historical Morning Planning price authority resolved operations canonical when run-scoped logical manifest lived under reports/runtime_tests/runs |
| BV-D02 | High | FIXED_IN_BU | Historical Submit Corporate Action guard used operations canonical raw OHLCV instead of run-scoped logical raw OHLCV |
| BV-D03 | High | FIXED_IN_BV | Historical Current Valuation converted historical_asof_view to market evidence from physical normalized OHLCV even when run-scoped logical input existed |
| BV-D04 | High | FIXED_IN_BU | BUY submit evidence reported SELL-only broker_available_quantity_review_required=true |


BV-D03 was newly fixed in this phase:

```text
Historical Current Valuation now prefers run-scoped logical normalized OHLCV from
market_refresh/inputs/historical_asof/<DATE>/logical_input_manifest.json
when that manifest exists.
```

If the logical manifest exists but is invalid, non-PASS, mismatched, or missing `normalized_ohlcv`, Current Valuation resolves to a missing sentinel path and fails closed as review-required. Legacy tests without a logical manifest retain the historical_asof physical authority fixture path for compatibility.

## Authority Map

Generated artifacts:

```text
reports/phase20_bv_historical_runtime_end_to_end_authority_wiring_review/authority_inventory.json
reports/phase20_bv_historical_runtime_end_to_end_authority_wiring_review/authority_inventory.md
reports/phase20_bv_historical_runtime_end_to_end_authority_wiring_review/producer_consumer_matrix.json
```

The inventory covers:

```text
fresh-run initialization
backup / restore
business calendar resolution
data readiness
market refresh
historical as-of view
logical input materialization
feature refresh
Candidate AI
Opportunity AI
AI lifecycle gate / feature-date contract
Morning Planning
Approval
Pending Generation
Sell Planning
Position Management
Submit
Historical Submit Adapter
Fill simulation
Ledger mutation
Position Campaign
Valuation
Benchmark Snapshot
Daily Audit
Report
Summarize
Final State Hash
```

## Fallback Audit

Invalid fallback defects found and fixed:

```text
BV-D01 Morning price source: operations canonical fallback instead of run-scoped logical normalized OHLCV
BV-D02 Submit Corporate Action raw source: operations canonical fallback instead of run-scoped logical raw OHLCV
BV-D03 Current Valuation: historical_asof physical source used despite available run-scoped logical normalized OHLCV
```

Valid explicit fallbacks remain documented for Historical Safety, Summarize current-root mismatch handling, and Listed Issues PIT latest-not-after snapshot selection.

## Temporal Review

No remaining temporal defect was confirmed. The fixed chain preserves:

```text
business_date == logical_cutoff for Historical logical inputs
feature_date resolved from materialized feature-date contract
Submit target_session_date == business_date
Current Valuation market_date == business_date
Listed Issues future snapshot rejected
Corporate Action raw row evaluated at business_date
```

## BUY / SELL Branch Review

The observed BUY evidence issue was real but non-blocking:

```text
broker_available_quantity_review_required = true
side = BUY
```

It was classified as BV-D04 and fixed in BU. BUY now records `not_applicable_buy` for broker available quantity. SELL broker available quantity guard remains enforced.

## Stage Reachability

Generated artifact:

```text
reports/phase20_bv_historical_runtime_end_to_end_authority_wiring_review/stage_reachability_comparison.json
```

Direct local Run-scoped evidence was available for three runs only. Older Bull / 20BD references were therefore sourced from existing Phase reports and marked as not locally retained. The two key 2022 failures are separated:

```text
BT run: first zero stage = Morning price resolution
BU run: first HALT stage = Submit Corporate Action authority
```

## Test Coverage Audit

Existing tests missed these defects because they tended to cover producer-only or consumer-only fixtures, passed explicit paths directly to adapters, used 2026 dates where operations canonical had rows, or asserted non-blocking behavior without asserting Evidence semantics.

Closed coverage gaps:

```text
Historical Run-scoped logical input -> Morning Consumer
Historical Run-scoped raw Corporate Action authority -> Submit Consumer
Historical Current Valuation logical input priority
Run-scoped Artifact invalid -> no operations canonical fallback
BUY/SELL branch isolation
SELL broker available quantity preservation
```

## Resolver Consolidation

Generated artifact:

```text
reports/phase20_bv_historical_runtime_end_to_end_authority_wiring_review/resolver_consolidation_assessment.json
```

Current duplicate resolver/path construction count: `5`.

Recommendation:

```text
Introduce HistoricalAuthorityResolver / RunScopedEvidenceContext in a later phase.
Do not perform a large refactor inside BV now that confirmed High defects are fixed.
```

## Changed Files

```text
src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py
tests/runtime_v2/test_phase17_bh_current_valuation_refresh_temporal_contract.py
```

BV also relies on BS/BT/BU changes already present in:

```text
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py
src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py
```

## Non-Changed Scope

No changes were made to:

```text
Candidate threshold
Opportunity threshold
PM logic
Capital Deployment Policy
Accepted Generation
AI Model
BUY/SELL strategy
Performance tuning
Broker Production processing
Production/Demo authority
```

## Validation

Executed:

```text
Targeted pytest: 69 passed
py_compile: PASS
JSON validation: PASS (11 files)
git diff --check: PASS
```

1BD focused smoke:

```text
BLOCKED_BY_ACTIVE_RUN
exit_code = 70
active_run = runtime-test-historical-extended-smoke-20260725T233056749335Z
```

Evidence:

```text
reports/runtime_tests/fresh_runs/fresh-run-historical-extended-smoke-20260726T000706274036Z/fresh_run_summary.json
```

No 5BD, 20BD, 245BD, 1-year, or 3-year run was executed.

## User Revalidation Commands

First resolve the active run state. Then run the 1BD smoke:

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py status
```

After the active run is explicitly closed or abandoned by the operator:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run   --profile historical-extended-smoke   --business-days 1   --start-date 2022-09-01   --initial-cash 1000000   --confirm   --yes-i-understand-this-mutates-trading-state   --json
```

Expected confirmations:

```text
Morning price_source_path = reports/runtime_tests/runs/<RUN_ID>/daily/2022-09-01/market_refresh/inputs/historical_asof/2022-09-01/raw_normalized/jquants/equities_bars_daily/data.parquet
Submit adapter raw_ohlcv_path = reports/runtime_tests/runs/<RUN_ID>/daily/2022-09-01/market_refresh/inputs/historical_asof/2022-09-01/raw/jquants/equities_bars_daily/data.parquet
Corporate Action status is not MISSING for the BUY items
BUY broker_available_quantity_review_required = false
Current Valuation, when reached, uses run-scoped logical normalized OHLCV
submitted_count > 0 if remaining preflight checks pass
```

5BD rerun:

```text
Allowed only after the 1BD smoke passes.
```

20BD / 245BD:

```text
Not allowed yet. Run only after 1BD and 5BD pass.
```

## Closure

```text
PHASE20_CLOSURE_NOT_READY
```

Reason:

```text
Critical defects = 0
Unfixed High defects = 0
Invalid Historical canonical fallback = 0 after fixes
Future leakage = 0 confirmed
BUY/SELL branch contamination = 0 after fixes
But Historical BUY 1BD focused smoke could not run because an active run exists.
```
