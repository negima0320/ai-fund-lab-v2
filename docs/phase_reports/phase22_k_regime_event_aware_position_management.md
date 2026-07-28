# Phase22-K Regime / Event-aware Position Management

## Primary Judgment

```text
PHASE22_K_COMPLETE_WITH_UPSTREAM_REVIEW_REQUIRED
```

Regime / Event-aware Position Management was implemented as a production/demo/historical common, read-only Strategy artifact foundation. It extends the existing `position_management.v1` contract with deterministic HOLD / ADD / REDUCE / EXIT / UNRESOLVED action intent rules.

Phase22-L entry ready: `YES_READ_ONLY_FOUNDATION`.
Runtime switch ready: `NO`.
Legacy retirement ready: `NO`.

## Implemented Scope

- Added explicit PM rule config: `configs/strategy/regime_event_position_management.json`
- Extended PM producer module: `src/ai_fund_lab_v2/strategy/position_management.py`
- Compat-extended schema: `schemas/strategy/position_management.schema.json`
- Added tests: `tests/strategy/test_phase22_k_regime_event_position_management.py`
- Added evidence package: `reports/phase22_k_regime_event_aware_position_management/phase22_k_evidence_20260727/`

## Contract

Phase22-K decides only Strategy PM action intent:

```text
HOLD
ADD
REDUCE
EXIT
UNRESOLVED
```

It also records confidence, uncertainty, reason codes, cooldown state, event restriction state, regime adjustment, position health state, re-entry state, action priority, and action intensity.

It does not decide REDUCE quantity, EXIT quantity, ADD quantity, sell percentage, JPY sell allocation, order price, Pending, Submit, Approval, Execution, Ledger, or Current mutation.

## Decision Hierarchy

Implemented hierarchy:

```text
hard event / hard invalidation
source validity
corporate event restriction
market regime
technical health
opportunity persistence
holding period
portfolio policy
position sizing gap
cooldown / re-entry
conflict resolution
```

Source shortage does not fallback to HOLD. Upstream `REVIEW_REQUIRED` produces PM `REVIEW_REQUIRED` and member-level `UNRESOLVED`.

## Rules

Regime rules cover Bull, Range, Bear, Correction, Recovery, High Volatility, and Uncertain states. Bull/Recovery widen ADD/HOLD, Bear/Correction/High Volatility restrict ADD and raise REDUCE priority, and Uncertain becomes review/unresolved.

Corporate Event rules cover earnings proximity, split, merger, TOB, delisting, source unavailable, and future announcement leakage. Earnings-near restricts ADD but is not automatic EXIT. Missing Corporate Event coverage is not treated as no event.

Technical health rules cover healthy trend, weakening trend, breakdown, and volatility expansion. Opportunity persistence distinguishes strong, weakening, invalidated, and unavailable.

Holding period states:

```text
NEW / EARLY / MATURE / EXTENDED / STALE
```

Cooldown and re-entry rules are explicit and do not use PnL or trade outcome evidence.

## Runtime Preservation

Existing Runtime PM producer, ADD Planning, Sell Planning, Pending, Submit, Approval, Execution, Ledger, and Current are unchanged. Sell Planning remains REDUCE / EXIT quantity authority. ADD Planning remains executable ADD quantity authority.

## Validation

Executed short tests only:

```text
python3 -m pytest tests/strategy/test_phase22_k_regime_event_position_management.py
python3 -m pytest tests/strategy/test_phase22_a_market_context.py ... tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_phase22k python3 -m compileall src/ai_fund_lab_v2/strategy tests/strategy tests/runtime_v2/test_phase15h_capital_deployment_policy.py
jq empty configs/strategy/regime_event_position_management.json schemas/strategy/position_management.schema.json
```

Results:

```text
Phase22-K targeted: 5 passed
Selected Phase22/Runtime regression: 131 passed
compileall: PASS
JSON validation: PASS
Long tests executed: NO
```

Blocking gaps: none for the read-only foundation.

Non-blocking gaps: Market Context and Corporate Event upstream source/threshold decisions remain `REVIEW_REQUIRED`; Position Sizing remains read-only / `NOT_ELIGIBLE` until later gates.
