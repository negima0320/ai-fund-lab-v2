# Phase30-AC - Campaign Lifecycle / HOLD-ADD Winner Amplification Repair Implementation and Legacy Retirement

Task ID: `Phase30-AC`

## Primary Judgment

```text
PHASE30_AC_CAMPAIGN_LIFECYCLE_HOLD_ADD_WINNER_AMPLIFICATION_REPAIR_IMPLEMENTED
IMPLEMENTATION_STATUS = IMPLEMENTED
USER_OPERATED_FRESH_VALIDATION_READY
```

Phase30-AC implemented the Phase30-AB design in the Production-common Strategy
path. It did not create a new AI, retrain a model, tune thresholds, calibrate
Expected Edge, add sector data, use Historical outcomes as Runtime input,
change Phase30-W Entry Admission, change Phase30-Z REENTRY, redesign SELL /
REDUCE / EXIT, or weaken Safety.

## Canonical Campaign Connection

Pre-action Strategy generation now materializes canonical campaign lifecycle
authority before Strategy Intelligence:

```text
latest prior daily/<prior>/positions/position_campaigns.json
+ Current state available at decision time
-> daily/<business_date>/positions/position_campaigns.json
-> strategy/strategy_intelligence.json
```

The materialized artifact records:

- `position_campaign_id`
- opened business date
- current quantity / market value / average price
- campaign-relative return
- observed campaign MFE
- observed giveback
- ADD / REDUCE / BUY / SELL history
- temporal safety flags

The temporal selection rule is strict prior campaign state plus current
decision-time state. Same-day EOD campaign reconstruction, same-day future
execution, future MFE, future giveback, Historical outcome, and audit judgment
are not inputs.

## Strategy Intelligence

Strategy Intelligence now consumes the canonical campaign authority and no
longer treats held-position missing campaign identity as a silent partial
fallback. For held positions, missing canonical campaign identity is explicit:

```text
campaign_identity_authority_status = MISSING
```

Lifecycle context now exposes:

- `campaign_age_business_days`
- `current_campaign_relative_return`
- `observed_campaign_mfe`
- `observed_giveback`
- campaign history summaries

Observed MFE/giveback are campaign-owned observed state, not Current-only
fallback truth.

## HOLD / Profit Protection

PM remains Action Authority. PM now attaches structured evidence:

- `strategy_intelligence_hold_worthiness_evidence`
- `strategy_intelligence_profit_protection_evidence`
- campaign age
- current campaign-relative return
- observed MFE / giveback
- ADD / REDUCE history
- CQ / Downside Risk status

The retired status-only HOLD reason was replaced with structured reason codes:

```text
structured_hold_worthiness_pass
structured_hold_worthiness_review_required
```

HOLD is no longer represented as only "SELL condition not reached"; it carries
campaign lifecycle and profit-protection evidence.

## ADD / Winner Amplification

PM and PC preserve:

```text
HOLD-worthy != ADD-worthy
```

PM now attaches `strategy_intelligence_add_worthiness_evidence`. ADD is blocked
to HOLD when campaign-aware evidence is not sufficient, using:

```text
structured_add_worthiness_no_add
```

PC member rows now receive campaign-aware ADD fields:

- campaign id and campaign identity status
- campaign age
- campaign-relative return
- observed MFE / giveback
- ADD history count
- REDUCE history count
- Profit Protection status
- `strategy_intelligence_add_worthiness_state`

Repeated ADD history and prior REDUCE history are recognized. Weak survivors
are not ADD-worthy merely because they remain open.

## Capital Reallocation

Residual reallocation still preserves Phase30-W residual recycling and one-lot
admission, but current-position ADD candidates now participate with lifecycle
quality:

- `ADD_ALLOWED` / `ADD_REDUCED_ONLY` can receive stronger residual priority.
- `NO_ADD` is deprioritized.
- one-lot overshoot admission uses the campaign-aware ADD-worthiness state.

Cash remains valid when lifecycle / ADD-worthiness evidence does not support
incremental capital.

## Legacy Retirement

```text
KEEP = 8
MIGRATED = 6
REMOVED_OR_RETIRED = 12
```

Retired code/test references:

```text
LEGACY_CAMPAIGN_FALLBACK_REFERENCE_COUNT = 0
OBSOLETE_HOLD_ADD_HEURISTIC_REFERENCE_COUNT = 0
```

Removed / retired targets include:

- PM/current lifecycle reference as ADD baseline campaign authority
- Current `position_lifecycle_id` / `source_execution_id` / `position_id` as
  campaign-id fallback in Strategy shadow current summary
- status-only HOLD reason codes
- CQ-only ADD-to-HOLD reason code
- Current-only observed MFE/giveback assumption in SI tests

## Reference Counts

Search scope:

```text
src/ai_fund_lab_v2 tests
```

Reference count result:

```text
strategy_position_management_current_position_lifecycle_reference = 0
strategy_intelligence_add_not_worthy_hold = 0
strategy_intelligence_hold_worthiness_pass = 0
strategy_intelligence_hold_worthiness_review_required = 0
```

## Duplicate Authority

```text
DUPLICATE_CAMPAIGN_AUTHORITY = NO
```

The implementation writes the same canonical `positions/position_campaigns.json`
authority for the pre-action path. Strategy Intelligence, PM, and PC consume it;
they do not create a second campaign ledger.

## Production Path

```text
ONE_PRODUCTION_CAMPAIGN_LIFECYCLE_PATH = YES
```

## Preserved Improvements

```text
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
PHASE30_W_ONE_LOT_ADMISSION_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
SELL_REDUCE_EXIT_SEMANTICS_PRESERVED = YES
BUY_SELL_INDEPENDENCE = PASS
PHASE30_P_SINGLE_STRATEGY_AUTHORITY_PATH_PRESERVED = YES
PHASE30_S_QUANTITY_HANDOFF_PRESERVED = YES
EXPECTED_EDGE = UNCALIBRATED
```

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

## Tests

Compile:

```text
PYTHONPYCACHEPREFIX=.pytest_pycache python3 -m compileall -q src/ai_fund_lab_v2/strategy/strategy_intelligence.py src/ai_fund_lab_v2/strategy/shadow_runtime.py src/ai_fund_lab_v2/strategy/position_management.py src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py tests/strategy/test_phase30_l_strategy_intelligence_gap_repair.py tests/strategy/test_phase30_n_strategy_intelligence_campaign_authority.py tests/strategy/test_phase30_p_strategy_intelligence_production_migration.py
```

Result:

```text
PASS
```

Focused regression:

```text
4 passed - Phase30-AC pre-action campaign materialization and canonical ADD baseline
14 passed - Strategy Intelligence lifecycle / PM production migration
20 passed - Phase30-W / Phase30-Z / Phase30-S preservation
18 passed - Strategy shadow wiring
106 passed - Portfolio Construction / SI / one-lot focused regression
```

Post-removal regression was run after old reason / authority references were
removed from code and tests.

## Long Historical

```text
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Validation Gate

```text
USER_OPERATED_FRESH_VALIDATION_READY
```

## Recommended Next Task

```text
Phase30-AD - Post-Repair Behavior Validation
```
