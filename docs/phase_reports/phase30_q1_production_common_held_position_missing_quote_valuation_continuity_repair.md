# Phase30-Q1 — Production-Common Held-Position Missing Quote Valuation Continuity Repair

## Primary Judgment

`PHASE30_Q1_PRODUCTION_COMMON_MISSING_QUOTE_TAXONOMY_AND_AUTHORIZED_STALE_VALUATION_IMPLEMENTED_76710_REMAINS_BLOCKED_BY_AUTHORITY_GAP`

```text
REPAIR_STATUS = BLOCKED_BY_AUTHORITY_GAP
10BD_RUNTIME_CONTINUITY_GATE_BLOCKED
CRITICAL_BLOCKER = YES
```

Phase30-Q1 implemented the Production-common Current Valuation taxonomy and an
explicit authorized stale valuation path. It did not add any symbol/date special
case and did not authorize blind previous-close fallback.

The 2023-10-27 / 76710 case remains blocked because current PIT authorities
prove listing/quote absence, but do not authoritatively explain the listing
transition or clear corporate-action / symbol-transition ambiguity sufficiently
to allow stale valuation.

## Root Cause

The Runtime continuity defect was not that Current valuation failed closed. It
was that held-position missing quote conditions were not semantically
classified:

```text
held position + market business day + same-day listed issue / quote absent
```

The repaired contract now separates legitimate stale accounting valuation from
data/source failure, listing/CA ambiguity, and unknown missing quote.

## Implemented Taxonomy

| Class | Behavior |
| --- | --- |
| `AUTHORITATIVELY_LEGITIMATE_STALE_VALUATION` | May carry prior authoritative valuation as stale accounting valuation only with explicit authority, stale age, basis, provenance, and CA clear |
| `DATA_OR_SOURCE_FAILURE` | `REVIEW_REQUIRED`, no apply |
| `LISTING_OR_CORPORATE_ACTION_AMBIGUITY` | `REVIEW_REQUIRED`, no apply |
| `UNKNOWN_MISSING_QUOTE` | `REVIEW_REQUIRED`, no apply |

Historical as-of market evidence now classifies missing symbols using same-day
listed issues, raw OHLCV, and normalized OHLCV evidence. A symbol absent from
listed issues and both quote sources is classified as
`LISTING_OR_CORPORATE_ACTION_AMBIGUITY`, not automatically authorized.

## VALID_CARRYOVER

`VALID_CARRYOVER = EXTENDED`

The existing status is reused only for explicit authorized stale accounting
valuation. It is not treated as a fresh quote.

Fresh quote:

```text
valuation_quote_status = FRESH_CURRENT_QUOTE
quote_business_date = valuation_business_date
staleness_business_days = 0
```

Authorized stale valuation:

```text
valuation_quote_status = AUTHORIZED_STALE_VALUATION
quote_business_date != valuation_business_date
current_valuation_status = VALID_CARRYOVER
stale_accounting_valuation_not_fresh_market_signal = true
```

## 76710 Classification

Under the repaired contract:

```text
76710 / 2023-10-27 = LISTING_OR_CORPORATE_ACTION_AMBIGUITY
```

Evidence is sufficient to show:

- market business day,
- 76710 held in Current,
- 76710 present in listed issues and bars on 2023-10-25 / 2023-10-26,
- 76710 absent from 2023-10-27 listed issues,
- 76710 absent from 2023-10-27 raw and normalized bars.

Evidence is not sufficient to prove:

- authoritative legitimate no-quote state,
- corporate-action ambiguity clear,
- stable post-listing-transition symbol state.

Therefore stale valuation is not authorized for 76710 yet.

## Authorized Stale Valuation

`AUTHORIZED_STALE_VALUATION = YES`

Authorization requirements:

- held canonical runtime-owned position exists,
- current-day quote is missing,
- missing quote class is `AUTHORITATIVELY_LEGITIMATE_STALE_VALUATION`,
- prior authoritative valuation exists,
- `quote_business_date` is before `valuation_business_date`,
- `staleness_business_days >= 1`,
- `stale_reason` and `stale_authority` are present,
- `corporate_action_ambiguity_status = CLEAR`,
- `quantity_basis == valuation_price_basis`,
- valuation role and provenance are present.

If these are not satisfied, apply remains blocked.

## Safety Boundaries

```text
BLIND_PREVIOUS_CLOSE_FALLBACK = NO
HISTORICAL_ONLY_FIX = NO
PHASE29_VALUATION_BASIS_DEFECT_RECURRENCE = NO
STALE_VALUATION_USED_AS_FRESH_STRATEGY_SIGNAL = NO
```

Stale accounting valuation preserves source quote date and basis metadata. It
does not fabricate a current-market timestamp.

## Current / Downstream Visibility

Current positions and candidate Current receive:

```text
valuation_quote_status
quote_business_date
valuation_business_date
staleness_business_days
stale_reason
stale_authority
listing_status_evidence
corporate_action_ambiguity_status
stale_accounting_valuation_not_fresh_market_signal
authorized_stale_valuation_symbols
```

This makes stale valuation visible to downstream Current readers, Safety,
Strategy, Portfolio Construction, and Position Sizing without changing their
optimization semantics.

## SELL Independence

`SELL_INDEPENDENCE = PASS`

The repair is valuation-only. Focused regression verifies existing execution,
ledger, cash, and pending evidence are not duplicated or mutated by valuation
resume.

## Resume Boundary

Safe future resume boundary remains:

```text
2023-10-27:current_valuation_refresh
```

For repaired authorized stale cases:

```text
duplicate execution = 0
duplicate ledger = 0
duplicate cash = 0
duplicate pending = 0
valuation apply exactly once = PASS
```

Codex did not run the long resume.

## Legacy Valuation Fallback

```text
LEGACY_VALUATION_FALLBACK_REFERENCE_COUNT = 0
```

No replaced blind previous-close valuation fallback remains.

## Phase30-P Integrity

```text
PHASE30_P_STRATEGY_MIGRATION_PRESERVED = YES
OLD_PRODUCTION_CONSUMER_REFERENCE_COUNT = 0
LEGACY_STRATEGY_PATH_REINTRODUCED = NO
ONE_PRODUCTION_STRATEGY_AUTHORITY_PATH = YES
```

## Runtime / Strategy Behavior

```text
ACTUAL_RUNTIME_VALUATION_BEHAVIOR_CHANGED = YES
STRATEGY_BEHAVIOR_INTENTIONALLY_CHANGED = NO
```

Runtime behavior changes only for explicitly authorized stale valuation
semantics. Strategy decisions, models, Accepted Generation, thresholds, and
weights were not changed.

## Validation

```text
compileall src/ai_fund_lab_v2/runtime_v2/current_state = PASS
focused pytest = 76 passed
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

Focused pytest covered:

- fresh quote valuation,
- authorized stale valuation apply,
- data/source failure fail-closed,
- listing/CA ambiguity fail-closed,
- unknown missing quote fail-closed,
- CA ambiguity guard,
- basis preservation,
- stale-to-fresh recovery,
- historical as-of listed absence classification,
- strategy isolation metadata,
- sell/resume idempotency boundary.

## Gate Decision

```text
10BD_RUNTIME_CONTINUITY_GATE_BLOCKED
CRITICAL_BLOCKER = YES
```

Reason:

```text
76710 remains LISTING_OR_CORPORATE_ACTION_AMBIGUITY because listing-transition
and corporate-action-clear authority are insufficient to authorize stale
valuation.
```

Recommended next task:

```text
Phase30-Q2 — Production-Common Listing Transition and Corporate Action Ambiguity Authority Repair
```
