# Phase29-L4-B Listed Issues Canonical Materialization and Trading Calendar Authority Repair

## Status

COMPLETE

PRODUCTION-COMMON IMPLEMENTATION

CANONICAL LISTED ISSUES MATERIALIZED

TRADING CALENDAR AUTHORITY RECONCILED

SHORT REGRESSION PASS

NO CONFIG CHANGE

NO STRATEGY / PM / ADD / BUY / SELL SEMANTIC CHANGE

NO ACQUISITION

NO OHLCV REFETCH

NO LONG BOOTSTRAP

NO HISTORICAL EXECUTION

## Judgment

PHASE29_L4_B_LISTED_CALENDAR_AUTHORITY_REPAIRED_PHASE29_L4_C_READY

## Summary

Phase29-L4-B implemented the data-authority repair designed in Phase29-L3 after preserving the Phase29-L4-A bootstrap post-commit repair.

The validated acquisition staging Listed Issues source at `.runtime/market_data_acquisition/runs/jquants-acquisition-20220517-20260807/raw/jquants/listed_issues/data.parquet` was materialized into canonical operations authority at `.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet`. PIT snapshots were written from provider `Date`, the existing `latest_snapshot_not_after_business_date` resolver and future-snapshot rejection semantics were preserved, and the snapshot index was rebuilt.

The validated acquisition staging Trading Calendar source was merged into canonical Historical and operations calendar authority. Staging has precedence over older base rows where it is validated and quote-consistent. The legacy `.runtime/data/raw/jquants/trading_calendar` cache remains non-authoritative. The five disputed 2026 dates are excluded as non-trading days and have zero quote rows:

- `2026-03-20`
- `2026-04-29`
- `2026-05-04`
- `2026-05-05`
- `2026-05-06`

Runtime Test calendar planning now propagates calendar authority review status when quote/calendar reconciliation detects ambiguous open-with-zero-quotes or closed-with-quotes states. Existing calendar-only fixtures remain compatible when no quote parquet is present.

The long requested window `2022-08-10..2026-08-07` resolves to 977 canonical business days. This matches the Phase29-L3 repaired expectation and excludes the disputed holidays.

## Implementation

Added `src/ai_fund_lab_v2/runtime_v2/source_authority_materialization.py`.

The module provides:

- `materialize_listed_issues_authority`
- `materialize_trading_calendar_authority`
- `reconcile_calendar_with_quotes`

Updated `scripts/runtime_test.py` calendar authority resolution:

- Reads base calendar state and validated acquisition overlay state.
- Applies validated staging overlay precedence for base/staging disagreements.
- Marks validated overlay-vs-overlay conflicts as review required.
- Reconciles final calendar state against normalized OHLCV quote rows when a quote source exists.
- Propagates calendar authority `REVIEW_REQUIRED` into window resolution.

No Strategy, Candidate, Opportunity, Portfolio Manager, ADD, BUY_NEW, SELL, REDUCE, EXIT, J1/J2, D61/D69, cash, concentration, Safety, model, threshold, or Accepted Generation semantics were changed.

## Runtime Materialization

Performed only canonical authority materialization from already completed staging data.

Not performed:

- market-data-acquisition
- listed API refetch
- price API refetch
- OHLCV re-bootstrap
- long bootstrap
- 977BD/979BD Historical run
- full multi-year feature generation

## Evidence

Evidence root:

`reports/phase29_l4_b_listed_issues_calendar_authority_repair_implementation/`

Key files:

- `implementation_summary.json`
- `listed_materialization_result.json`
- `listed_pit_validation.json`
- `calendar_authority_after.json`
- `calendar_disputed_dates.json`
- `quote_calendar_reconciliation.json`
- `full_window_resolution.json`
- `future_leakage_non_regression.json`
- `regression_results.json`
- `non_regression_matrix.json`
- `phase29_l4_c_entry_gate.json`

## Regression

Passed:

- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase29_l4_b_authority_materialization.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py tests/runtime_v2/test_phase17_bv6_historical_replay_operator_range.py`
  - 34 passed
- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase20_bb_runtime_market_data_bootstrap.py`
  - 12 passed
- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/source_authority_materialization.py scripts/runtime_test.py`
  - passed

## Non-Regression

Config impact: NONE.

ADD was not weakened. This repair does not touch capital deployment scoring, order-side selection, position sizing, Strategy, PM, BUY_NEW, ADD, SELL, REDUCE, EXIT, cash exposure, concentration, Safety policy, model thresholds, or Accepted Generation.

SELL / REDUCE / EXIT are unchanged.

L4-A bootstrap post-commit evidence/readiness repair is preserved; the focused bootstrap regression remains green.

## Phase29-L4-C Gate

Phase29-L4-C entry gate is READY.

Resolved business-day count is 977 for `2022-08-10..2026-08-07`.

Remaining blockers: none in L4-B scope.
