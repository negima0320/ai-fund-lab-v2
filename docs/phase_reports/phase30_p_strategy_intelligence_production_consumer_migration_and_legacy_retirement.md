# Phase30-P — Strategy Intelligence Production Consumer Migration and Legacy Retirement

## Primary Judgment

`PHASE30_P_STRATEGY_INTELLIGENCE_PRODUCTION_CONSUMER_MIGRATION_COMPLETE_LEGACY_ACTION_PATH_RETIRED_10BD_READY`

Strategy Intelligence is now connected as Production-readable evidence for the
formal planning path. It remains semantic / lifecycle / risk evidence only and
does not own target portfolio construction, directional position decisions,
quantity, runtime mapping, or safety authority.

`PRODUCTION_STRATEGY_INTELLIGENCE_MIGRATION_COMPLETE = YES`

`ACTUAL_TRADING_BEHAVIOR_CHANGED = YES`

The behavior change is intentional for Phase30-P: Portfolio Construction and
Position Management now consume Strategy Intelligence evidence before action
resolution. The change is bounded by existing authority owners.

## Authority Boundary

- Portfolio Construction remains target portfolio and BUY-side allocation authority.
- Position Management remains existing-position HOLD / ADD / REDUCE / EXIT authority.
- Position Sizing remains lot-aware quantity authority.
- Runtime Planning remains pure mapping authority.
- Safety remains independent guardrail authority.
- Strategy Intelligence remains evidence only.

## Migration Status

| Area | Status | Notes |
| --- | --- | --- |
| BUY_NEW | MIGRATED | PC consumes SI eligibility / continuation quality evidence before BUY inclusion. |
| BUY_WAIT | MIGRATED | SI continuation gaps can cause `BUY_WAIT`; no pending order is created. |
| ADD | MIGRATED | PM uses SI continuation quality before allowing ADD-worthy behavior. |
| REENTRY | MIGRATED | Campaign identity and current-position authority remain preserved. |
| HOLD | MIGRATED | PM can distinguish HOLD-worthy from merely not-SELL. |
| Profit Protection | MIGRATED_AS_EVIDENCE | SI supplies evidence; PM retains action authority. |
| REDUCE / EXIT | MIGRATED_AS_EVIDENCE | SI evidence is attached; PM retains sell-side authority. |

## Legacy Retirement

`OLD_PRODUCTION_CONSUMER_REFERENCE_COUNT = 0`

`LEGACY_FALLBACK_REFERENCE_COUNT = 0`

`SHADOW_ACTION_PATH_REMAINING = NO`

`ONE_PRODUCTION_STRATEGY_AUTHORITY_PATH = YES`

The legacy `proposed_decision_if_authorized` field and writer were removed
from Strategy Intelligence production payloads. The remaining source reference
is a negative regression assertion, and durable architecture references state
that the field is retired.

Observation-compatible artifact names such as `strategy_shadow_summary.json`
and `legacy_shadow_comparison.json` remain for existing validation manifests.
They are not production Action Authority paths; formal planning summaries mark
legacy authority as retired when the production Strategy Intelligence consumer
is connected.

Legacy inventory final counts:

```text
KEEP = 11
MIGRATED = 9
REMOVED = 11
REMAINING_DEPRECATED = 0 for Strategy Intelligence production action path
OBSERVABILITY_COMPATIBILITY_RETAINED = YES
```

## Expected Edge

`EXPECTED_EDGE_CALIBRATION_STATUS = UNCALIBRATED`

`economic_units_available = false`

No calibrated return estimate, payoff distribution, or production parameter
selection was introduced. Runtime opportunity scores remain uncalibrated
relative model evidence.

## Relative Strength Scope

`RELATIVE_STRENGTH_SCOPE = STOCK_VS_MARKET_FIRST_GENERATION`

Stock-vs-sector and sector-vs-market remain deferred data-foundation work.

## Model / Leakage Firewall

```text
NEW_AI_CREATED = NO
PRODUCTION_MODEL_RETRAINED = NO
ACCEPTED_GENERATION_CHANGED = NO
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

## Regression Results

```text
BUY_SELL_INDEPENDENCE = PASS
CAMPAIGN_AUTHORITY = PASS
VALUATION_BASIS = PASS
MULTI_DAY_LIFECYCLE = PASS
FAIL_CLOSED = PASS
IDEMPOTENCY = PASS
POST_REMOVAL_REGRESSION = PASS
```

Focused validation only:

```text
compileall src/ai_fund_lab_v2/strategy = PASS
pytest focused Phase30-P suite = 208 passed
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Implementation Summary

- Strategy Intelligence can now emit `runtime_consumer_eligibility = ELIGIBLE`
  production evidence while keeping `production_authority = false`.
- Formal planning produces SI before PC / PM consumers, then passes the SI
  artifact to both consumers.
- PC uses SI evidence for BUY inclusion / wait decisions while retaining target
  portfolio authority.
- PM uses SI evidence for HOLD / ADD / REDUCE / EXIT context while retaining
  directional authority.
- The legacy proposed-decision alias was removed from SI payloads.
- Formal planning summaries mark legacy authority inactive when the production
  SI consumer is connected.

## 10BD Entry Gate

`USER_OPERATED_10BD_FRESH_HISTORICAL_READY`

Codex did not execute long Historical. The next validation should be
user-operated fresh 10BD historical, followed by Phase30-Q focused audit.

## Critical Blocker

`CRITICAL_BLOCKER = NO`

Recommended next:

`Phase30-Q — Post-Migration Focused Audit and User 10BD Fresh Historical Entry`
