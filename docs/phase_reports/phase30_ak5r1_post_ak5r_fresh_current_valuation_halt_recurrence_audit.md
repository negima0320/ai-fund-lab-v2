# Phase30-AK5R1 - Post-AK5R Fresh Current-Valuation HALT Recurrence Audit

## Scope

Task ID: `Phase30-AK5R1`

Type: `READ_ONLY_POST_REPAIR_RUNTIME_CONFORMANCE_AND_ROOT_CAUSE_AUDIT`

Target run:

```text
runtime-test-historical-extended-smoke-20260817T014925194738Z
```

Observed:

```text
last completed business day = 2022-10-20
failed job = 2022-10-21:current_valuation_refresh
Runtime CLI exit code = 20
```

No implementation, replay, resume, fresh run, target-run mutation, Strategy
change, valuation fallback, Historical-only path, Safety relaxation, or AK7R
implementation was performed by this audit.

## Primary Judgment

```text
POST_AK5R_HALT_CLASSIFICATION = AK5R_STALE_CLASSIFICATION_NOT_ACTION_EFFECTIVE
AK5R_REGRESSION_CONFIRMED = YES
KNOWN_RUNTIME_DEFECT = YES
KNOWN_AUTHORITY_DEFECT = YES
IMPLEMENTATION_REPAIR_REQUIRED = YES
AK7R_SAFE_TO_IMPLEMENT_BEFORE_VALUATION_FIX = NO
```

AK5R partially materialized in the fresh runtime. Execution-projected Current
now preserves the per-position valuation metadata that was missing in AK5.
However, the stale no-valid-close authority did not become action-effective at
runtime. The run still halted at `2022-10-21:current_valuation_refresh`.

The recurrence is not the old metadata continuity failure. It is the remaining
classification / final quote-status boundary: `44150` is a held, listed symbol
with a raw same-day row but no valid close, Corporate Event authority is clear,
and previous valuation provenance is complete, but the persisted runtime
projection did not materialize `AUTHORIZED_STALE_VALUATION` / `VALID_CARRYOVER`.

## Exact HALT Producer

```text
HALT_DIRECT_PRODUCER =
  ai_fund_lab_v2.runtime_v2.current_state.valuation.run_current_valuation_refresh
HALT_DIRECT_REASON = current_valuation_review_required
HALT_TRIGGER_SYMBOLS = ["44150"]
FIRST_NON_PASS_LAYER = current_valuation_refresh valuation_projection
```

Direct artifacts:

```text
run_state.status = HALT
run_state.next_job = 2022-10-21:current_valuation_refresh
fresh_run_summary.error =
  Runtime CLI stopped at 2022-10-21:current_valuation_refresh with exit code 20
runtime_manifest.projection_status = REVIEW_REQUIRED
runtime_manifest.apply_status = NOT_EXECUTED
runtime_manifest.reason = current_valuation_review_required
valuation_projection.status = REVIEW_REQUIRED
valuation_apply_evidence.apply_executed = false
```

Persisted `current_valuation_manifest` changed from the pre-AK5R run:

```text
pre-AK5R missing_symbols = ["44150"]
post-AK5R missing_symbols = []
post-AK5R missing_evidence = ["quote_status_not_allowed"]
```

The explicit post-AK5R artifact no longer names `44150` in `missing_symbols`,
but `44150` remains the reconstructed trigger symbol: it is the only held
runtime symbol absent from normalized 2022-10-21 quotes while listed with a raw
no-valid-close row and CA clear evidence.

## AK5R Metadata Continuity Conformance

```text
AK5R_METADATA_CONTINUITY_RUNTIME_MATERIALIZED = YES
POSITIONS_WITH_MISSING_VALUATION_PROVENANCE = []
```

All 9 execution-projected open positions on 2022-10-21 carry:

```text
valuation_as_of
source_market_date
valuation_source
valuation_price_type
valuation_quote_status
valuation_price_basis
valuation_price_provenance
quantity_basis
quantity_basis_provenance
```

`44150` post-AK5R position metadata:

```text
quantity = 100
average_price = 619.0
current_price = 613.0
market_value = 61,300
valuation_as_of = 2022-10-20
source_market_date = 2022-10-20
valuation_source =
  reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260817T014925194738Z/daily/2022-10-20/market_refresh/inputs/historical_asof/2022-10-20/raw_normalized/jquants/equities_bars_daily/data.parquet
valuation_price_type = jquants_daily_quote
valuation_quote_status = FRESH_CURRENT_QUOTE
valuation_price_basis = ADJUSTED
quantity_basis = ADJUSTED
valuation_price_provenance = present
quantity_basis_provenance = present
```

## 44150 Revalidation

```text
44150_PREVIOUS_VALUATION_PROVENANCE_COMPLETE = YES
44150_CA_CLEAR = YES
44150_LISTED_NO_VALID_CLOSE_CLASSIFIED = NO
44150_AUTHORIZED_STALE_VALUATION = NO
```

Evidence:

| Check | Result |
| --- | --- |
| Held quantity | `100` |
| Previous authoritative price | `613.0` on `2022-10-20` |
| Previous valuation provenance | Complete |
| Quantity basis / valuation basis | `ADJUSTED / ADJUSTED` |
| Listed issue on 2022-10-21 | Present |
| Corporate Event authority | `KNOWN_NO_EVENT`, `AVAILABLE` |
| Raw 2022-10-21 OHLCV | Row present for `44150`, O/H/L/C/AdjC all null |
| Normalized 2022-10-21 OHLCV | No row |
| Runtime stale quote status | Not materialized |
| Final valuation status | `REVIEW_REQUIRED` |

Read-only re-evaluation of the current code against the saved inputs classifies
`44150` as:

```text
missing_quote_class = AUTHORITATIVELY_LEGITIMATE_STALE_VALUATION
classification_reason = listed_symbol_raw_no_valid_close_ca_clear
corporate_action_ambiguity_status = CLEAR
```

But the target run artifact did not persist that classification and did not
apply `AUTHORIZED_STALE_VALUATION`.

## AK5R Stale Authority Action Effect

Expected chain:

```text
held position
-> listed
-> same-day no valid close
-> CA CLEAR
-> previous authoritative valuation provenance complete
-> basis compatible
-> AUTHORIZED_STALE_VALUATION
-> VALID_CARRYOVER
```

Runtime result:

```text
AK5R_STALE_VALUATION_RUNTIME_ACTION_EFFECTIVE = NO
AK5R_STALE_AUTHORITY_FAILURE_REASON =
  listed-no-valid-close stale classification / AUTHORIZED_STALE_VALUATION did
  not materialize into the persisted current_valuation_refresh artifact; final
  quote status remained disallowed and projection halted with
  quote_status_not_allowed.
```

The metadata part of AK5R is action-effective. The stale valuation
classification / final projection acceptance part is not.

## Pre-AK5R vs Post-AK5R

```text
AK5R_CHANGED_RUNTIME_EVIDENCE = YES
```

Changed evidence on 2022-10-21:

| Evidence | Pre-AK5R run | Post-AK5R run |
| --- | --- | --- |
| Missing symbols | `["44150"]` | `[]` |
| Missing evidence | `44150`, `current_valuation_quote_missing`, `quote_status_not_allowed` | `quote_status_not_allowed` |
| Valued position count | `0` | `9` |
| Missing position valuation metadata | all 9 open positions | none |
| 44150 previous valuation metadata | missing valuation date/source/type/status | complete previous-day metadata |
| Apply | `NOT_EXECUTED` | `NOT_EXECUTED` |
| Final status | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` |

This confirms a partial repair: metadata continuity improved, but the stale
valuation authority did not close the runtime boundary.

## Accounting / Temporal / CA

```text
VALUATION_ACCOUNTING_CONSISTENCY = PASS
TEMPORAL_AUTHORITY_TRIGGERED_HALT = NO
CORPORATE_ACTION_TRIGGERED_HALT = NO
FUTURE_INFORMATION_USED = FALSE
```

Accounting:

```text
cash = 445,370
position_market_value = 629,610
total_equity = 1,074,980
cash + position_market_value = 1,074,980
reconciliation_difference = 0
```

Temporal evidence remains bounded to 2022-10-21 historical as-of data:

```text
historical_asof_view.status = PASS
business_date = 2022-10-21
latest_available_market_date = 2022-10-21
future_rows_excluded_from_consumer = true
```

Corporate Action does not trigger the halt. `44150` has `KNOWN_NO_EVENT` and
`coverage_status = AVAILABLE`.

## Repair Decision

```text
AK5R_REGRESSION_CONFIRMED = YES
KNOWN_RUNTIME_DEFECT = YES
KNOWN_AUTHORITY_DEFECT = YES
IMPLEMENTATION_REPAIR_REQUIRED = YES
AK7R_SAFE_TO_IMPLEMENT_BEFORE_VALUATION_FIX = NO
```

The required next repair should focus on the remaining stale valuation
classification / quote-status acceptance path for a mixed fresh-plus-authorized
stale portfolio. It should not create a blind previous-close fallback and
should not weaken CA, basis, or temporal authority.

## Implementation Authorization

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK5R1
```

## Recommended Next Task

```text
Phase30-AK5R2 - Confirmed Post-AK5R Valuation Focused Repair
```
