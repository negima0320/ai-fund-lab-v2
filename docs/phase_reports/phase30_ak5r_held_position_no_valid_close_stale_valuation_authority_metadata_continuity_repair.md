# Phase30-AK5R - Held-Position No-Valid-Close Valuation Authority / Metadata Continuity Repair

## Primary Judgment

`PHASE30_AK5R_HELD_POSITION_NO_VALID_CLOSE_STALE_VALUATION_AUTHORITY_AND_EXECUTION_PROJECTED_CURRENT_METADATA_CONTINUITY_REPAIRED`

Phase30-AK5R implemented the focused Production-common repair authorized by
Phase30-AK5. No Strategy, Candidate, Portfolio Construction, Position Sizing,
Safety, threshold, cap, performance parameter, fresh Historical, long
Historical, resume, replay, or target-run mutation was performed.

## Repair Status

```text
HELD_POSITION_NO_VALID_CLOSE_REPAIR_IMPLEMENTED = YES
EXECUTION_PROJECTED_CURRENT_VALUATION_METADATA_CONTINUITY_REPAIRED = YES
AUTHORITATIVE_STALE_VALUATION_NO_VALID_CLOSE_ACTION_EFFECTIVE = YES
44150_EQUIVALENT_SENTINEL_PASS = YES
```

## Repair A - Execution-Projected Current Metadata Continuity

Updated:

```text
src/ai_fund_lab_v2/runtime_v2/asset/models.py
src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py
```

Runtime-owned execution projection now preserves canonical valuation metadata
for positions that remain open across execution projection:

```text
valuation_as_of
source_market_date
valuation_source
valuation_price_type
valuation_quote_status
quote_business_date
valuation_business_date
valuation_price_basis
valuation_price_role
valuation_price_provenance
quantity_basis
quantity_basis_provenance
```

The projection reuses prior Current / ledger evidence. It does not fabricate a
new valuation date, source, or price authority and does not overwrite newer
authoritative valuation evidence.

Sentinel:

```text
test_phase30_ak5r_execution_projection_preserves_valuation_metadata_for_open_positions = PASS
```

The test sells a different symbol while `44150` remains open and verifies that
`44150` keeps its prior valuation date/source/basis/provenance metadata.

## Repair B - Authoritative Listed No-Valid-Close Classification

Updated:

```text
src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py
```

Current valuation now supports an additional Production-common authority case
using the existing Phase30-Q1 stale valuation architecture:

```text
held position
listed issue exists on valuation business date
raw OHLCV row exists but no usable valid close
normalized current quote absent
corporate event authority proves KNOWN_NO_EVENT / CLEAR
previous authoritative valuation metadata is complete
quantity basis and valuation basis are compatible
```

Only under those conditions is the prior authoritative valuation reused as:

```text
valuation_quote_status = AUTHORIZED_STALE_VALUATION
current_valuation_status = VALID_CARRYOVER
stale_accounting_valuation_not_fresh_market_signal = true
```

This is not a fresh quote and not a Strategy market signal.

## Fail-Closed Preservation

The repair preserves REVIEW_REQUIRED when:

```text
listing state is ambiguous
corporate action authority is unresolved or missing
previous valuation provenance is missing
previous valuation date/source is missing
previous valuation basis is missing
quantity/valuation basis is incompatible
no previous authoritative valuation exists
future quote would be required
normal quote evidence is contradictory
```

Focused sentinel:

```text
test_phase30_ak5r_listed_no_valid_close_without_ca_clear_remains_fail_closed = PASS
```

Existing Phase30-Q1/Q2 fail-closed tests also passed.

## Fresh Quote Preservation

Normal same-day fresh quote valuation remains authoritative. The stale path
does not override fresh quote evidence.

```text
NORMAL_FRESH_VALUATION_PRESERVED = YES
```

## Safety Boundaries

```text
BLIND_PREVIOUS_CLOSE_FALLBACK_CREATED = NO
HISTORICAL_ONLY_VALUATION_PATH_CREATED = NO
CORPORATE_ACTION_FAIL_CLOSED_PRESERVED = YES
TEMPORAL_AUTHORITY_PRESERVED = YES
BASIS_AUTHORITY_PRESERVED = YES
ACCOUNTING_AUTHORITY_PRESERVED = YES
FUTURE_INFORMATION_USED = FALSE
```

The repair does not use future rows or future quote lookup. Historical as-of
market evidence remains bounded by the valuation business date and existing
future-row exclusion authority.

## Tests

Executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-ak5r python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2/current_state src/ai_fund_lab_v2/runtime_v2/asset
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase30_q2_listing_transition_corporate_action_authority.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py -q
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase30_q1_held_position_missing_quote_valuation_continuity.py tests/runtime_v2/test_phase30_q2_listing_transition_corporate_action_authority.py tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py tests/runtime_v2/test_phase15ay_current_temporal_schema_migration.py tests/runtime_v2/test_phase17_ba_submit_temporal_authority_contract.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py
```

Results:

```text
compileall = PASS
focused AK5R/Q2/projection tests = 28 passed
broader current valuation / stale / temporal / projection regression = 74 passed
```

## Historical

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Required Final Judgments

```text
HELD_POSITION_NO_VALID_CLOSE_REPAIR_IMPLEMENTED = YES
EXECUTION_PROJECTED_CURRENT_VALUATION_METADATA_CONTINUITY_REPAIRED = YES
AUTHORITATIVE_STALE_VALUATION_NO_VALID_CLOSE_ACTION_EFFECTIVE = YES
44150_EQUIVALENT_SENTINEL_PASS = YES
BLIND_PREVIOUS_CLOSE_FALLBACK_CREATED = NO
HISTORICAL_ONLY_VALUATION_PATH_CREATED = NO
CORPORATE_ACTION_FAIL_CLOSED_PRESERVED = YES
TEMPORAL_AUTHORITY_PRESERVED = YES
BASIS_AUTHORITY_PRESERVED = YES
NORMAL_FRESH_VALUATION_PRESERVED = YES
FUTURE_INFORMATION_USED = FALSE
```

## Recommended Next Task

```text
User-operated fresh long Historical validation from a clean state.
```
