# Phase31-A6 — 2022-12-16 Current Valuation Refresh HALT Root-Cause Audit

## PRIMARY_JUDGMENT

The 2022-12-16 HALT is a legitimate Current Valuation fail-closed caused by a held-position missing quote for `61750` that canonical PIT evidence classified as `LISTING_OR_CORPORATE_ACTION_AMBIGUITY`. This is not a B10, Strategy, BUY_ADD/BUY_NEW, or marginal-capital-priority issue. It is also not a price/quantity basis mismatch. Runtime correctly refused to apply a valuation candidate because `61750` was held in Current, had a valid 2022-12-15 valuation, but was absent from 2022-12-16 listed issues, raw OHLCV, and normalized OHLCV, with no authority proving a stale accounting valuation was allowed.

## TARGET_RUN

`runtime-test-historical-extended-smoke-20260818T015851711672Z`

## FAILURE_DATE

`2022-12-16`

## FAILURE_STAGE

`current_valuation_refresh`

## FIRST_NON_PASS_LAYER

`current_valuation_refresh` valuation projection, after data readiness and safety authority were already `READY` / `PASS`.

Direct chain:

```text
Current position state includes runtime-owned 61750
+ 2022-12-16 historical as-of market evidence
-> no same-day quote for 61750
-> missing quote classification = LISTING_OR_CORPORATE_ACTION_AMBIGUITY
-> current_valuation_manifest.artifact.status = REVIEW_REQUIRED
-> valuation_apply_evidence.status = NOT_APPLIED
-> Runtime CLI exit_code = 20
-> runtime_test fresh-run exit_code = 30 / HALT
```

## DIRECT_PRODUCER

`ai_fund_lab_v2.runtime_v2.current_state.valuation` Current valuation-only / no-fill producer.

The relevant producer contract is the Phase30 held-position missing quote taxonomy: a missing current quote may only be carried as stale accounting valuation under `AUTHORITATIVELY_LEGITIMATE_STALE_VALUATION`; `LISTING_OR_CORPORATE_ACTION_AMBIGUITY` must fail closed.

## DIRECT_CONSUMER

Runtime v2 daily operation CLI for `--job current_valuation_refresh`, with `--stop-on-review-required --stop-on-blocked`, consumed the projection result and returned exit code `20`. `scripts/runtime_test.py fresh-run` then converted that Runtime CLI non-PASS into top-level HALT / exit code `30`.

## DIRECT_ARTIFACT

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z/daily/2022-12-16/current_valuation_refresh/current_valuation_manifest.json`
- Supporting artifacts:
  - `valuation_projection.json`
  - `valuation_input.json`
  - `market_evidence_authority.json`
  - `valuation_apply_evidence.json`
  - `runtime_manifest.json`
  - `cli_result.json`
  - `fresh_run_summary.json`

## DIRECT_REASON

`current_valuation_review_required`

Materialized missing evidence:

```text
61750
current_valuation_quote_invalid:61750:missing_quote_class:LISTING_OR_CORPORATE_ACTION_AMBIGUITY
current_valuation_quote_missing
quote_status_not_allowed
```

## AFFECTED_SYMBOLS

`61750`

Evidence:

- 2022-12-15: `61750` present in listed issues, raw OHLCV, and normalized OHLCV; valuation status `READY`.
- 2022-12-16: `61750` absent from listed issues, raw OHLCV, and normalized OHLCV.
- 2022-12-15 corporate event fact for `61750`: `KNOWN_NO_EVENT`, `coverage_status = AVAILABLE`.
- 2022-12-16 corporate event facts contain no `61750` row because the symbol is absent from listed issues.

## PRICE_AUTHORITY_STATUS

`AMBIGUOUS`

For `61750`, the last authoritative valuation price was 2022-12-15:

```text
price = 897.0
valuation_price_basis = ADJUSTED
valuation_price_type = jquants_daily_quote
valuation_quote_status = FRESH_CURRENT_QUOTE
valuation_price_authority = PASS
valuation_price_authority_reason = valuation_price_basis_matches_adjusted_quantity_basis
```

For 2022-12-16, there is no same-day valuation quote. Runtime did not prove an authorized stale valuation; therefore price authority for 2022-12-16 is ambiguous for valuation application purposes.

## QUANTITY_AUTHORITY_STATUS

`PASS`

`61750` quantity evidence remains internally coherent:

```text
quantity = 100.0
quantity_basis = ADJUSTED
quantity_basis_provenance = runtime_execution_price_authority:adjusted_reference_price_basis
cost_basis = 89700.0
average_price = 897.0
```

No evidence shows a bad quantity, quantity-basis loss, or Current rebuild quantity defect.

## BASIS_AUTHORITY_STATUS

`PASS`

The available basis evidence is compatible:

```text
quantity_basis = ADJUSTED
valuation_price_basis = ADJUSTED
fill_price_basis = ADJUSTED
execution_price_basis = ADJUSTED
```

The HALT was not caused by raw price x adjusted quantity, adjusted price x raw quantity, analytical adjusted price misuse, or missing basis metadata. The blocking issue is absence of a 2022-12-16 quote plus missing authority to use stale accounting valuation.

## CORPORATE_ACTION_CAUSAL

`UNRESOLVED`

No artifact proves that a corporate action actually occurred for `61750` on 2022-12-16. However, the missing quote class is `LISTING_OR_CORPORATE_ACTION_AMBIGUITY`, and corporate action coverage is not sufficient to prove the stale valuation conditions. This makes corporate-action/listing-transition ambiguity part of the fail-closed classification, not a proven CA event.

## CURRENT_REBUILD_CAUSAL

`NO`

Current consumed `.runtime/persistent_ledger/state.json`, retained 16 positions, and preserved `61750` quantity and basis metadata. The candidate was not applied because projection was not ready. There is no evidence that Current rebuild dropped quantity, position identity, or basis metadata.

## RECONCILIATION_CAUSAL

`NO`

Candidate arithmetic is internally consistent but not authoritative because apply was blocked:

```text
2022-12-16 candidate cash = 157340.0
2022-12-16 candidate market_value = 912010.0
2022-12-16 candidate total_equity = 1069350.0
cash + market_value = total_equity
sum(position.market_value) = 912010.0
```

No reconciliation mismatch is the first non-PASS.

## MATERIALIZED_GUARD_CLASS

`NOT_MATERIALIZED`

`runtime_manifest.json` has empty `review_guard_classes` / `review_guard_codes` and `review_guard_summary.review_guard_count = 0`, despite the Runtime final state being `REVIEW_REQUIRED`.

## SEMANTIC_GUARD_CLASS

`DATA_INTEGRITY_SAFETY`

The semantic guard is a data-integrity fail-closed on missing held-position valuation quote / unresolved listing or corporate-action ambiguity. Observability gap: this did not materialize as a typed guard class in `review_guard_classes`.

## LEGITIMATE_FAIL_CLOSED

`YES`

The current architecture explicitly forbids `missing quote -> previous close` unless `AUTHORITATIVELY_LEGITIMATE_STALE_VALUATION` is proven with stale authority, CA clear status, stable basis/provenance, and quote date metadata. Those conditions were not proven for `61750`.

## RUNTIME_DEFECT

`NO`

No Runtime producer/consumer defect is evidenced. Runtime applied the repaired Phase30-Q1/Q2 missing-quote contract. The missing typed guard metadata is an observability gap, not the primary root cause.

## PRIOR_BASIS_REPAIR_REGRESSION

`NO`

This does not regress the prior basis repair families:

1. No analytical adjusted valuation price misuse observed.
2. No raw/economic authority mismatch observed.
3. No raw price x adjusted quantity mismatch observed.
4. Price/quantity basis contract passes for available evidence.
5. Basis metadata was not lost during Current rebuild.
6. Basis metadata persists across the held `61750` position.
7. Corporate Action adjustment authority did not produce a false pass.

## DEFECT_LINEAGE

`LEGITIMATE_STOP`

More specifically: a new date/symbol boundary that exercises the repaired Phase30 held-position missing quote and listing/CA ambiguity contract. It is not a Phase30 basis regression.

## PASS_TO_HALT_DELTA

Minimal causal delta from 2022-12-15 to 2022-12-16:

- `61750` was held in Current on both dates.
- 2022-12-15: `61750` had listed issues row, raw OHLCV row, normalized OHLCV row, and corporate event `KNOWN_NO_EVENT`; Current valuation applied with `READY`.
- 2022-12-16: `61750` disappeared from listed issues, raw OHLCV, and normalized OHLCV; no authoritative stale valuation / listing-transition / CA-clear evidence existed.
- Runtime valued 15 of 16 positions, marked `61750` missing, set projection to `REVIEW_REQUIRED`, and did not apply the candidate.

## RETROACTIVE_CONTAMINATION

`NO`

The issue first appears at the 2022-12-16 valuation boundary. Completed valuation through 2022-12-15 remains usable because `61750` had same-day quote and `KNOWN_NO_EVENT` evidence on 2022-12-15.

## EARLIEST_AFFECTED_DATE

`NOT_APPLICABLE`

## B0_B9_STRATEGY_PIT_EVIDENCE_CONTAMINATED

`NO`

This is a 2022-12-16 Current valuation application stop. It does not contaminate PM decisions, Expected Edge, Incremental Investment Value, Opportunity Cost, Market Context, PC marginal priority development evidence, or B0-B9 shadow evidence through the completed 2022-12-15 boundary. Strategy PIT evidence for completed days remains usable.

## B10_CAUSAL_TO_2022_12_16_HALT

`NO`

B10 was implemented after this run HALTed. The causal evidence is entirely within the pre-B10 Current valuation path and 2022-12-16 market/listing evidence.

## COMPLETED_DAY_EVIDENCE_USABLE

`YES_WITH_LIMITATIONS`

- Strategy PIT evidence through 2022-12-15: usable.
- Trading execution evidence through 2022-12-15: usable.
- Valuation evidence through 2022-12-15: usable.
- PnL/performance evidence through 2022-12-15: usable.
- 2022-12-16 valuation/performance: not usable as an applied Current valuation because `current_valuation_refresh` did not apply.

## REPAIR_REQUIRED

`NO`

No correctness repair is required for this HALT. A narrow observability improvement may be useful: materialize the semantic `DATA_INTEGRITY_SAFETY` / held-position missing quote guard class into typed guard metadata when Current valuation returns `REVIEW_REQUIRED`.

## NEXT_TASK_RECOMMENDATION

`legitimate fail-closed acceptance`

Do not start a new long fresh validation merely to bypass this stop. If product policy wants this symbol/date to continue through valuation, the next separate task should be an evidence/authority task for listing-transition and authorized stale valuation, not a valuation arithmetic or Strategy repair.
