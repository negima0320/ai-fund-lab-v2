# Phase30-Q0 — 2023-10-27 Held-Position Missing Quote Runtime Continuity Re-Audit

## Primary Judgment

`PHASE30_Q0_20231027_HELD_POSITION_MISSING_QUOTE_LISTING_STATUS_TRANSITION_STILL_PRESENT_RUNTIME_CONTINUITY_GATE_BLOCKED`

Phase30-FのHALT root causeは、現行repositoryでもProduction-common
continuityとして未解決である。

```text
CURRENT_DEFECT_STATUS = STILL_PRESENT
10BD_RUNTIME_CONTINUITY_GATE_BLOCKED
CRITICAL_BLOCKER = YES
```

Phase30-Q0はREAD-ONLY監査であり、Runtime / Strategy / config /
threshold / model / Accepted Generation / target run artifactの変更、
fresh run、resume、replay、repairは実行していない。

## Mandatory Boundary

Phase30-PのStrategy Intelligence Production migrationは保持されている。

```text
PHASE30_P_STRATEGY_MIGRATION_PRESERVED = YES
LEGACY_STRATEGY_PATH_REINTRODUCED = NO
ACTUAL_TRADING_BEHAVIOR_CHANGED = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

この問題はStrategyではなく、Current Valuation / Market Evidence /
Runtime continuity authorityの問題である。

## Phase30-F Root Cause Reconfirmed

Target run:

```text
runtime-test-historical-extended-smoke-20260815T061857447380Z
```

HALT boundary:

```text
2023-10-27:current_valuation_refresh
```

Observed chain remains:

```text
held position 76710
-> 2023-10-27 current valuation quote unavailable
-> current_valuation_review_required
-> valuation apply NOT_EXECUTED
-> CLI exit_code 20
-> run_state HALT at 2023-10-27:current_valuation_refresh
```

Source artifacts:

| Artifact | Evidence |
| --- | --- |
| `current_valuation_manifest.json` | `artifact.status = REVIEW_REQUIRED`, `missing_symbols = ["76710"]`, `missing_evidence = ["76710", "current_valuation_quote_missing", "quote_status_not_allowed"]` |
| `valuation_projection.json` | `status = REVIEW_REQUIRED`, `reason = current_valuation_review_required`, `valuation_refresh_precondition_status = PASS`, `valuation_refresh_action = APPLY` |
| `valuation_apply_evidence.json` | `status = NOT_APPLIED`, `apply_status = NOT_EXECUTED`, `postcondition_status = NOT_EXECUTED` |
| `market_evidence_authority.json` | `status = PASS`, `market_date = 2023-10-27`, `missing_symbols = ["76710"]` |
| `cli_result.json` | `exit_code = 20` |
| `run_state.json` | `status = HALT`, `next_job = 2023-10-27:current_valuation_refresh` |

## 76710 Missing Quote Classification

`76710_MISSING_QUOTE_CLASSIFICATION = LISTING_STATUS_TRANSITION`

Best-supported PIT evidence:

| Date | Raw bar | Normalized bar | Listed issue row | Close |
| --- | --- | --- | --- | --- |
| 2023-10-25 | present | present | present | 949 |
| 2023-10-26 | present | present | present | 949 |
| 2023-10-27 | absent | absent | absent | none |

The 2023-10-27 J-Quants trading calendar marks the market as a trading day
(`is_trading_day = True`). The 2023-10-27 historical as-of view is `PASS` for
normalized OHLCV, raw OHLCV, trading calendar, and listed issues. Therefore the
best-supported cause is not a normalization drop or market holiday. The symbol
is absent from both same-day listed issues and same-day bars.

Corporate Event evidence does not provide a 76710 event on 2023-10-27. The
classification is therefore a listed-issue / quote authority transition, not a
proved corporate-action repair path.

## Raw Evidence

2023-10-27 historical as-of view:

```text
status = PASS
latest_available_market_date = 2023-10-27
normalized_ohlcv authority = PASS
raw_ohlcv authority = PASS
trading_calendar authority = PASS
listed_issues authority = PASS
listed_issues selected_snapshot_date = 2023-10-27
```

Raw / normalized boundary:

```text
2023-10-27 raw OHLCV row_count = 4312, contains_76710 = false
2023-10-27 normalized OHLCV row_count = 4150, contains_76710 = false
2023-10-27 listed issues row_count = 4312, contains_76710 = false
```

This is not proven to be a normalized-only defect.

## Current Runtime Contract

Current implementation:

```text
src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py
```

Current valuation accepts only market / quote statuses:

```text
ALLOWED_MARKET_STATUSES = {"READY", "VALID_CARRYOVER"}
```

For every runtime-owned held position, a quote must exist and must have:

- basis-compatible valuation price,
- allowed price type,
- `freshness_status` in `READY` or `VALID_CARRYOVER`,
- quote market date matching the market evidence date,
- source provenance.

If any held symbol is missing or invalid, current valuation returns
`REVIEW_REQUIRED` and does not apply.

This is safe fail-closed behavior, but it does not yet classify:

- listing transition,
- delisting / post-delisting holding,
- suspension,
- no valid close,
- provider/source defect,
- authorized stale valuation.

## Production-Common Correctness

The present behavior is partially correct but not Production-common complete.

Correct:

- no blind previous-close fallback,
- no partial update,
- no valuation apply when quote authority is missing,
- no Strategy or Safety attempt to fabricate price,
- no Phase29 raw/adjusted basis recurrence.

Incomplete:

- a held position can remain in Current while the same-day listed issue row and
  quote disappear,
- current valuation records only generic quote missing / quote status not
  allowed,
- no explicit listing-state / corporate-action ambiguity / stale valuation
  taxonomy is carried into Current,
- no authorized stale valuation semantic exists for legitimate no-quote cases.

Therefore the 10BD Runtime continuity gate is blocked until a Production-common
repair is designed and implemented.

## Historical-Only Special Case

```text
HISTORICAL_ONLY_FIX_REQUIRED = NO
```

No 2023-10-27-only or 76710-only repair is authorized.

## Blind Previous-Close Fallback

```text
BLIND_PREVIOUS_CLOSE_FALLBACK_AUTHORIZED = NO
```

If stale valuation is introduced later, it must be explicit, classified, and
visible to downstream Current / Safety / Strategy consumers.

## Missing Quote Taxonomy

Taxonomy is required.

Minimum categories for the next repair:

| Category | Expected behavior |
| --- | --- |
| `AUTHORITATIVELY_LEGITIMATE_STALE_VALUATION` | Allow only with explicit stale metadata and no unresolved CA/listing ambiguity |
| `DATA_OR_SOURCE_FAILURE` | `REVIEW_REQUIRED / FAIL_CLOSED` |
| `LISTING_OR_CORPORATE_ACTION_AMBIGUITY` | `REVIEW_REQUIRED / QUARANTINE / FAIL_CLOSED` |
| `UNKNOWN_MISSING_QUOTE` | `REVIEW_REQUIRED / FAIL_CLOSED` |

Required stale metadata if allowed:

```text
valuation_quote_status
quote_business_date
valuation_business_date
staleness_business_days
stale_reason
stale_authority
price_basis
source provenance
listing_status_evidence
corporate_action_ambiguity_status
```

Portfolio accounting stale valuation and Strategy market-signal freshness must
remain separate.

## Phase29 Basis Recurrence

```text
PHASE29_VALUATION_BASIS_DEFECT_RECURRENCE = NO
```

76710 state at the halt still carries internally consistent basis metadata:

```text
quantity = 100
average_price = 948
current_price = 949
quantity_basis = ADJUSTED
valuation_price_basis = ADJUSTED
valuation_price_role = reconciled_adjusted_basis_valuation_price
```

The valuation apply was blocked before a contaminated price could be applied.

## Generality

The observed 299BD completed segment had no other current valuation projection
missing-symbol failure before 2023-10-27. This exact observed case is 76710, but
the contract issue is general:

```text
held position + expected market business day + same-day quote/listed row absent
```

Any held symbol can encounter this through listing transition, suspension,
no valid close, data vendor defect, or normalization/source issue.

## Existing Test Coverage

Existing coverage includes:

- no-fill valuation-only refresh,
- non-trading-day valid carryover,
- stale market fails closed,
- missing quote fails closed,
- invalid price fails closed,
- stale quote fails closed,
- quote date mismatch fails closed,
- missing quote source fails closed,
- no feature / previous-price fallback,
- no-position readiness without quotes,
- dry-run idempotency,
- apply backup/current atomic write,
- historical run-scoped logical input preference,
- valuation basis contract regressions.

Missing coverage for the repair:

- held position disappears from listed issues while still present in Current,
- listing transition + missing quote taxonomy,
- corporate-action ambiguity + missing quote,
- suspension / no valid close classification,
- authorized stale valuation metadata,
- stale valuation basis preservation,
- downstream Current / Safety / Strategy visibility of stale valuation,
- resume-at-current_valuation_refresh after execution already applied,
- duplicate execution / ledger / cash / pending prevention on resume.

## Resume Boundary

2023-10-27 execution evidence:

```text
execution cli exit_code = 0
fills = SELL 61920 quantity 200 price 84 cash_effect +16800
current_apply_evidence.status = APPLIED
ledger_append_evidence.status = PASS
pending_terminalization_evidence.status = NOT_REQUIRED
```

Current valuation evidence:

```text
valuation_projection.status = REVIEW_REQUIRED
valuation_apply_evidence.status = NOT_APPLIED
apply_status = NOT_EXECUTED
postcondition_status = NOT_EXECUTED
```

Exact future resume boundary, if repaired and explicitly authorized:

```text
2023-10-27:current_valuation_refresh
```

Replay risk exists if earlier jobs are rerun. A future repair must prove:

- no duplicate execution,
- no duplicate Ledger append,
- no duplicate Cash mutation,
- no duplicate Pending terminalization,
- valuation applied exactly once,
- Current pointer/hash consistency.

## Gate Decision

```text
10BD_RUNTIME_CONTINUITY_GATE_BLOCKED
CRITICAL_BLOCKER = YES
```

Reason:

```text
Production-common held-position missing quote / listing transition valuation
continuity taxonomy and authorized stale valuation semantics are not yet
implemented.
```

Recommended next task:

```text
Phase30-Q1 — Production-Common Held-Position Missing Quote Valuation Continuity Repair
```
