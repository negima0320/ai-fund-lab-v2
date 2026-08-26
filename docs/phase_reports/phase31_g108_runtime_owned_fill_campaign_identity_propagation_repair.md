# Phase31-G108 — Runtime-Owned Fill Campaign Identity Propagation Repair

## Primary Judgment

G108_CAMPAIGN_IDENTITY_PROPAGATION_REPAIRED = YES

G108_ACCEPTED = YES

The G107 defect boundary is repaired narrowly at Strategy Intelligence campaign identity consumption. A currently held runtime-owned position now treats campaign identity as COMPLETE only when canonical `positions/position_campaigns.json` contains one matching OPEN campaign with required identity fields and non-conflicting current quantity. Missing, ambiguous, CLOSED-only, symbol-mismatched, and quantity-conflicting campaign evidence remains fail-closed.

No fresh-run, resume, replay, or long Historical was executed by Codex.

## Confirmed G107 Anchor

TARGET_RUN = runtime-test-historical-extended-smoke-20260825T045610960730Z

TARGET_DATE = 2022-11-28

ANCHOR_SYMBOL = 93180

G107 pre-repair actual evidence:

- 2022-11-25 BUY fill quantity = 700
- 2022-11-28 current quantity = 700
- `positions/position_campaigns.json` contains OPEN campaign `pc-93bafcd34c4af64c-93180-0002`
- pre-repair Strategy Intelligence artifact had `campaign_identity_authority_status = MISSING`
- pre-repair PM converted HOLD to UNRESOLVED through `canonical_campaign_identity_missing`

Using the same canonical 2022-11-28 campaign artifact and current position facts, the repaired lifecycle calculation resolves:

- current_position_state = HELD
- current_quantity = 700
- position_campaign_id = pc-93bafcd34c4af64c-93180-0002
- campaign_opened_date = 2022-11-25
- campaign_status = OPEN
- campaign_identity_authority_status = COMPLETE
- missing_campaign_authority_fields = []

## Repair Boundary

Changed:

- `src/ai_fund_lab_v2/strategy/strategy_intelligence.py`
  - Held-position campaign identity completion now requires an OPEN canonical campaign.
  - Campaign current quantity conflicts with Runtime Current fail closed as `campaign_current_quantity_mismatch`.
  - COMPLETE is not emitted when any required campaign authority field or reconciliation guard fails.

Added/updated regression coverage:

- `tests/strategy/test_phase30_n_strategy_intelligence_campaign_authority.py`
  - 2022-11-28 / 93180 runtime-owned BUY fill style OPEN campaign propagates to COMPLETE.
  - no campaign remains fail-closed.
  - ambiguous multiple OPEN campaigns remain fail-closed.
  - CLOSED-only campaign remains fail-closed.
  - symbol mismatch remains fail-closed.
  - quantity mismatch remains fail-closed.

- `tests/strategy/test_phase30_p_strategy_intelligence_production_migration.py`
  - PM HOLD no longer becomes UNRESOLVED solely because of campaign identity when Strategy Intelligence lifecycle campaign identity is COMPLETE.

SoT updated:

- `docs/02_architecture/strategy_intelligence_data_contract_v1.md`
  - Runtime-owned BUY fill -> Current -> canonical OPEN campaign -> Strategy Intelligence lifecycle identity propagation is now explicit.

## Required Results

20221128_93180_CAMPAIGN_IDENTITY_COMPLETE = YES

20221128_PM_CAMPAIGN_IDENTITY_REVIEW_CLEARED = YES

20221128_MORNING_PIPELINE_REVIEW_FROM_THIS_CAUSE = NO

CAMPAIGN_IDENTITY_SYNTHESIZED_WITHOUT_CANONICAL_EVIDENCE = NO

AMBIGUOUS_CAMPAIGN_FALSE_COMPLETE_COUNT = 0

CLOSED_CAMPAIGN_FALSE_COMPLETE_COUNT = 0

QUANTITY_MISMATCH_FALSE_COMPLETE_COUNT = 0

G90_CHANGED = NO

G97_CHANGED = NO

G99_CHANGED = NO

G102_CHANGED = NO

G104_CHANGED = NO

SUBMIT_CHANGED = NO

PENDING_CHANGED = NO

SAFETY_CHANGED = NO

PM_DECISION_THRESHOLDS_CHANGED = NO

MARKET_QUALITY_CHANGED = NO

RISK_PACING_CHANGED = NO

PS_QUANTITY_AUTHORITY_CHANGED = NO

RUNTIME_PRIORITY_CHANGED = NO

FRESH_RUN_EXECUTED_BY_CODEX = NO

RESUME_EXECUTED_BY_CODEX = NO

REPLAY_EXECUTED_BY_CODEX = NO

LONG_HISTORICAL_EXECUTED_BY_CODEX = NO

SHORT_E2E_20221125_TO_20221128_GATE = PASS

## Short E2E Gate

The focused gate covers the confirmed G107 causal boundary:

2022-11-25 BUY fill 93180:700
-> 2022-11-28 Runtime Current held quantity 700
-> canonical OPEN campaign `pc-93bafcd34c4af64c-93180-0002`
-> Strategy Intelligence lifecycle identity COMPLETE
-> Position Management structured HOLD evidence campaign identity COMPLETE
-> no PM UNRESOLVED solely from `canonical_campaign_identity_missing`

Downstream PC / PS / Runtime / Strategy Planning Authority were not changed. The previous exit-20 cause was PM REVIEW_REQUIRED from missing campaign identity; that cause is cleared by the focused gate.

## Test Results

PASS:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase30_n_strategy_intelligence_campaign_authority.py \
  tests/strategy/test_phase30_p_strategy_intelligence_production_migration.py

13 passed in 1.62s
```

PASS:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase30_n_strategy_intelligence_campaign_authority.py \
  tests/strategy/test_phase30_p_strategy_intelligence_production_migration.py \
  tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py \
  tests/runtime_v2/test_phase20_y_pm_cross_regime_campaign.py \
  tests/strategy/test_phase31_g97_residual_reconsideration_authoritative_binding.py \
  tests/strategy/test_phase31_g90_cash_preferred_aggregate_resolver.py \
  tests/strategy/test_phase31_g86_cash_preferred_participation_deferral.py \
  tests/strategy/test_phase31_g83_bootstrap_cash_preference_partition.py \
  tests/strategy/test_phase31_g81_opportunity_aware_security_cash_partition.py \
  tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py

62 passed in 2.81s
```

Artifact-dependent neighboring tests:

```text
tests/strategy/test_phase31_g102_item_scoped_pc_discrete_quantity_authority.py
tests/strategy/test_phase31_g99_reconsideration_lot_context_propagation.py
```

These were attempted as part of the broader focused command, but failed with `FileNotFoundError` because the local checkout does not contain the referenced prior run artifacts:

- `runtime-test-historical-extended-smoke-20260824T203644021876Z`
- `runtime-test-historical-extended-smoke-20260824T121719329586Z`

The available tests in that command otherwise passed: 65 passed, 4 artifact-missing failures.

PY_COMPILE = PASS

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/strategy_intelligence.py \
  src/ai_fund_lab_v2/strategy/position_management.py \
  src/ai_fund_lab_v2/strategy/portfolio_construction.py \
  src/ai_fund_lab_v2/strategy/position_sizing.py \
  src/ai_fund_lab_v2/strategy/runtime_planning.py
```

GIT_DIFF_CHECK = PASS

```text
git diff --check
```

## Final Decision

G108_CAMPAIGN_IDENTITY_PROPAGATION_REPAIRED = YES

G108_ACCEPTED = YES

NEXT_ACTION = user-operated resume/fresh validation may proceed from this repair standpoint; do not attribute any remaining HALT to the cleared 93180 campaign identity defect without fresh evidence.
