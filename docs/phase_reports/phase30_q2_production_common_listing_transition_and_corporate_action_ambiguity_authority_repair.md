# Phase30-Q2 — Production-Common Listing Transition / Corporate Action Authority Repair

## Primary Judgment

```text
PHASE30_Q2_LISTING_CA_AUTHORITY_BINDING_IMPLEMENTED_76710_REMAINS_BLOCKED_BY_DATA_FOUNDATION
```

Production-common Current Valuation now consumes Listing State Authority,
Corporate Action Ambiguity Authority, and Tradability Authority when classifying
held-position missing quotes.

Q1 taxonomy and authorized stale valuation semantics are preserved.

```text
REPAIR_STATUS = BLOCKED_BY_DATA_FOUNDATION
```

The production-common repair path is implemented and covered by focused tests,
but the target `76710 / 2023-10-27` case still lacks sufficient PIT authority to
authorize stale valuation.

## Listing State Authority

Current Valuation accepts a `listing_state_authority` object from market
evidence. It distinguishes:

```text
CURRENTLY_LISTED
PREVIOUSLY_LISTED_CURRENT_ABSENT
LISTING_TRANSITION_CONFIRMED
LISTING_TRANSITION_REASON_UNKNOWN
```

`CURRENTLY_LISTED + missing quote` maps to:

```text
DATA_OR_SOURCE_FAILURE
```

`PREVIOUSLY_LISTED_CURRENT_ABSENT` or `LISTING_TRANSITION_CONFIRMED` without an
authoritative transition reason, stale permission, and tradability support maps
to:

```text
LISTING_OR_CORPORATE_ACTION_AMBIGUITY
```

Yesterday-listed / today-absent alone is not treated as delisted or stale-safe.

## Corporate Action Ambiguity Authority

Current Valuation accepts a `corporate_action_ambiguity_authority` object from
market evidence. Stale valuation is prohibited unless:

```text
corporate_action_ambiguity_status = CLEAR
```

`COVERAGE_INCOMPLETE`, `UNRESOLVED`, and `UNKNOWN` map to:

```text
LISTING_OR_CORPORATE_ACTION_AMBIGUITY
```

Event row absence is not considered clear unless the authority explicitly
establishes adequate coverage and no unresolved event.

## Tradability Authority

```text
TRADABILITY_AUTHORITY = PARTIAL
```

Current Valuation consumes `tradability_authority` when market evidence supplies
it. Authorized stale valuation requires a supported status such as:

```text
AUTHORIZED_NO_CURRENT_QUOTE
SUSPENDED
NO_VALID_CLOSE
UNTRADABLE_AUTHORIZED
```

For the target `76710 / 2023-10-27` evidence, sufficient tradability authority
is not available.

## 76710 Final Classification

```text
76710 / 2023-10-27 = LISTING_OR_CORPORATE_ACTION_AMBIGUITY
```

The Q2 repair does not force stale valuation. The target remains blocked
because the available PIT evidence does not prove all of:

- authoritative listing-transition reason,
- corporate-action clear coverage,
- tradability / no-current-quote authority.

## Authorized Stale Valuation

Authorized stale valuation is implemented for sufficiently authoritative cases.
It requires:

- `missing_quote_class = AUTHORITATIVELY_LEGITIMATE_STALE_VALUATION`,
- `corporate_action_ambiguity_status = CLEAR`,
- stale reason and stale authority,
- original quote business date,
- prior authoritative valuation price,
- matching `quantity_basis` and `valuation_price_basis`,
- valuation provenance,
- positive stale age.

The resulting Current metadata keeps:

```text
valuation_quote_status = AUTHORIZED_STALE_VALUATION
quote_business_date = original quote date
valuation_business_date = current valuation date
stale_accounting_valuation_not_fresh_market_signal = true
```

## Safety Flags

```text
BLIND_PREVIOUS_CLOSE_FALLBACK = NO
HISTORICAL_ONLY_FIX = NO
FUTURE_INFORMATION_USED = FALSE
FUTURE_LISTING_OUTCOME_USED = FALSE
PHASE29_VALUATION_BASIS_DEFECT_RECURRENCE = NO
STALE_VALUATION_USED_AS_FRESH_STRATEGY_SIGNAL = NO
```

## Phase30-P Integrity

```text
PHASE30_P_STRATEGY_MIGRATION_PRESERVED = YES
LEGACY_STRATEGY_PATH_REINTRODUCED = NO
STRATEGY_CHANGED = NO
```

The repair is confined to Production-common Current Valuation authority
consumption and tests.

## Duplicate Authority

```text
DUPLICATE_LISTING_AUTHORITY_CREATED = NO
DUPLICATE_CORPORATE_ACTION_AUTHORITY_CREATED = NO
CURRENT_VALUATION_AUTHORITY_CONSUMER_ONLY = YES
```

## Tests

Validation executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase30q2 python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2/current_state

PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase30q2 python3 -m pytest -q \
  tests/runtime_v2/test_phase30_q2_listing_transition_corporate_action_authority.py \
  tests/runtime_v2/test_phase30_q1_held_position_missing_quote_valuation_continuity.py \
  tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py \
  tests/runtime_v2/test_phase17_bh_current_valuation_refresh_temporal_contract.py \
  tests/runtime_v2/test_phase17_ba_submit_temporal_authority_contract.py \
  tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py \
  tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py \
  tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py
```

Result:

```text
compileall = PASS
focused pytest = 84 passed, 60 warnings
```

Covered cases include normal listed fresh quote, listed missing quote, previous
listed/current absent with unknown reason, authorized stale valuation,
corporate-action coverage incomplete, unresolved corporate action, basis
preservation, stale-to-fresh recovery, SELL independence, and resume
idempotency.

## Long Historical

```text
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
TARGET_RUN_MUTATED = NO
TARGET_RUN_RESUMED = NO
```

## Runtime Continuity Gate

```text
10BD_RUNTIME_CONTINUITY_GATE_BLOCKED
```

The gate remains blocked for `76710 / 2023-10-27` until PIT listing-transition,
corporate-action coverage, and/or tradability authority can classify the
absence cleanly.

## Recommended Next Task

```text
Phase30-Q3 — Production-Common Delisting / Listing Transition Data Foundation and CA Coverage Repair
```
