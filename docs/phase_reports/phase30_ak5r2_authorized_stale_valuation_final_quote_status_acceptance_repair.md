# Phase30-AK5R2 — Authorized Stale Valuation Final Quote-Status Acceptance Repair

## Primary Judgment

`AUTHORIZED_STALE_VALUATION_FINAL_ACCEPTANCE_REPAIRED = YES`

Phase30-AK5R2 implemented the focused Production-common Current Valuation repair
for the post-AK5R final quote-status acceptance gap. The root cause was not stale
valuation construction; AK5R stale valuation metadata continuity was already
available. The remaining defect was the final `quote_status_not_allowed` gate:
it cleared only when every valued position was `AUTHORIZED_STALE_VALUATION`,
therefore a realistic portfolio containing both fresh quotes and one authorized
stale held position still halted with `quote_status_not_allowed`.

## Scope

Authorized implementation scope was limited to:

```text
canonical authorized stale valuation -> final quote-status / projection acceptance handoff
```

No Strategy, Candidate, Portfolio Construction, Position Sizing, cap, Safety,
Submit, Execution, or AK7R logic was changed.

Fresh / long Historical was not executed by Codex.

## Repair

In `src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py`, the final
quote-status override now accepts a complete current valuation projection when:

- every runtime-owned position was valued;
- there are no missing or invalid symbols;
- each position is either `FRESH_CURRENT_QUOTE` or `AUTHORIZED_STALE_VALUATION`;
- at least one position is canonically `AUTHORIZED_STALE_VALUATION`.

This repairs mixed fresh + authorized stale portfolios without accepting generic
missing quote, unresolved corporate-action, basis-mismatched, or provenance-free
stale valuation candidates.

## 44150 Equivalent Path

`44150_EQUIVALENT_RUNTIME_PATH_PASS = YES`

The existing explicit stale valuation taxonomy sentinel remains passing:

```text
test_phase30_q1_authorized_stale_valuation_applies_with_explicit_taxonomy
```

The stale position preserves:

- prior authoritative current price;
- `quote_business_date`;
- current `valuation_business_date`;
- `AUTHORIZED_STALE_VALUATION`;
- `VALID_CARRYOVER`;
- basis compatibility;
- stale accounting marker.

## Mixed Portfolio Sentinel

`MIXED_FRESH_AND_AUTHORIZED_STALE_PORTFOLIO_PASS = YES`

Added:

```text
test_phase30_ak5r2_mixed_fresh_and_authorized_stale_portfolio_passes
```

Fixture:

- `7203`: missing current quote with authorized stale classification;
- `6758`: fresh same-day quote;
- market-level `quote_status = REVIEW_REQUIRED`.

Expected and observed:

```text
result.status = READY
apply_executed = True
postcondition_status = PASS
current_valuation_status = VALID_CARRYOVER
authorized_stale_valuation_symbols = ["7203"]
7203 valuation_quote_status = AUTHORIZED_STALE_VALUATION
6758 valuation_quote_status = FRESH_CURRENT_QUOTE
```

## Fail-Closed Preservation

`GENERIC_MISSING_QUOTE_FAIL_CLOSED_PRESERVED = YES`

Existing q1 sentinels remain passing for:

- `DATA_OR_SOURCE_FAILURE`;
- unknown missing quote;
- listing / corporate-action ambiguity.

`CORPORATE_ACTION_FAIL_CLOSED_PRESERVED = YES`

Existing q1/q2 sentinels remain passing for unresolved corporate-action
ambiguity.

`BASIS_AUTHORITY_PRESERVED = YES`

Added:

```text
test_phase30_ak5r2_authorized_stale_basis_mismatch_remains_fail_closed
```

Result:

```text
REVIEW_REQUIRED
current_valuation_quote_invalid:7203:stale_valuation_basis_mismatch
```

`AK5R_METADATA_CONTINUITY_PRESERVED = YES`

Added:

```text
test_phase30_ak5r2_authorized_stale_missing_provenance_remains_fail_closed
```

Result:

```text
REVIEW_REQUIRED
current_valuation_quote_invalid:7203:stale_valuation_provenance_missing
```

## Production Integrity

```text
TEMPORAL_AUTHORITY_PRESERVED = YES
BASIS_AUTHORITY_PRESERVED = YES
NORMAL_FRESH_VALUATION_PRESERVED = YES
BLIND_PREVIOUS_CLOSE_FALLBACK_CREATED = NO
HISTORICAL_ONLY_PATH_CREATED = NO
FUTURE_INFORMATION_USED = FALSE
```

The repair does not synthesize valuation price, quantity, basis, or provenance.
It only accepts a candidate after canonical per-position valuation evidence has
already passed.

## Tests

Executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak5r2_pycache python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2/current_state
PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak5r2_pycache python3 -m pytest tests/runtime_v2/test_phase30_q1_held_position_missing_quote_valuation_continuity.py -q
PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak5r2_pycache python3 -m pytest tests/runtime_v2/test_phase30_q2_listing_transition_corporate_action_authority.py -q
PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak5r2_pycache python3 -m pytest tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py -q
PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak5r2_pycache python3 -m pytest tests/runtime_v2/test_phase15ay_current_temporal_schema_migration.py tests/runtime_v2/test_phase17_ba_submit_temporal_authority_contract.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py -q
```

Results:

```text
compileall = PASS
q1 current valuation continuity = 11 passed
q2 listing / corporate-action authority = 10 passed
phase15az current valuation producer = 17 passed
temporal / submit authority / fill projection preservation = 39 passed
```

## Historical

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Recommended Next Task

```text
Phase30-AK8 — Runtime BUY Intent / Sell-Only Execution Boundary Root-Cause Audit
```
