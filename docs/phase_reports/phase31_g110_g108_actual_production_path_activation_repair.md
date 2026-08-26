# Phase31-G110 — G108 Actual Production Path Activation Repair

## Summary

`runtime-test-historical-extended-smoke-20260825T072702567342Z` の
`2022-11-28:morning` HALT について、G108 の Strategy Intelligence
campaign identity predicate 自体は canonical producer で有効だった。

実際の bypass は、Strategy Intelligence producer の重複や legacy import ではなく、
その上流である pre-action `position_campaigns.json` materialization が、同一 symbol の
prior CLOSED campaign を見つけた時点で strict-prior ledger OPEN campaign の bootstrap
append を抑止していたことだった。

G110 ではこの publication/orchestration gap のみを修理した。CLOSED campaign は OPEN
campaign の存在証明ではないため、bootstrap suppression の重複防止条件を
「同一 symbol の materialized OPEN campaign が既にある場合」に限定した。

## Target

- Target run: `runtime-test-historical-extended-smoke-20260825T072702567342Z`
- Target boundary: `2022-11-28:morning`
- Anchor: `93180`

## Producer Path

ACTUAL_STRATEGY_INTELLIGENCE_PRODUCER:

`scripts/runtime_test.py -> Runtime v2 run_daily_operation -> shadow_runtime.generate_strategy_shadow_for_day -> strategy_intelligence.produce_strategy_intelligence_artifact`

ACTUAL_IMPORTED_MODULE_PATH:

`src/ai_fund_lab_v2/strategy/strategy_intelligence.py`

ACTUAL_IMPORTED_FUNCTION:

`produce_strategy_intelligence_artifact`

CANONICAL_G108_FUNCTION:

`ai_fund_lab_v2.strategy.strategy_intelligence.produce_strategy_intelligence_artifact`
using `build_strategy_intelligence_payload`, `_lifecycle_context`, and
`_current_or_same_day_closed_campaign_by_symbol`.

SAME_FUNCTION_OBJECT = YES

No duplicate Strategy Intelligence implementation, stale wrapper, alternate import, or legacy producer remained active in the actual producer chain.

## Root Cause

Before G110, actual-path pre-action campaign materialization built
`daily/2022-11-28/positions/position_campaigns.json` with the prior CLOSED 93180 campaign only.
It did not append the strict-prior ledger OPEN campaign opened on `2022-11-25`.

The failing condition was:

```python
prior_symbols = {symbol for row in materialized}
for symbol in current_symbols - updated_symbols - prior_symbols:
    append_strict_prior_ledger_open_campaign(...)
```

Because `93180` already existed as a CLOSED campaign, the OPEN campaign from strict-prior ledger
evidence was skipped. Strategy Intelligence therefore received incomplete canonical campaign
evidence and correctly emitted `campaign_identity_authority_status = MISSING`.

The repaired condition is:

```python
open_materialized_symbols = {symbol for row in materialized if campaign_is_open(row)}
for symbol in current_symbols - updated_symbols - open_materialized_symbols:
    append_strict_prior_ledger_open_campaign(...)
```

This preserves duplicate-OPEN fail-closed semantics while allowing a valid re-entry/new OPEN campaign
after an older CLOSED campaign.

## Actual-Path Evidence After Repair

The focused actual-path regression copied the target run to a temp directory and exercised the
production-common producer path:

`generate_strategy_shadow_for_day -> Strategy Intelligence -> PM -> PC -> PS -> Runtime Planning -> Strategy Planning Authority`

It did not call `build_strategy_intelligence_payload()` directly.

Observed repaired anchor evidence:

- `positions/position_campaigns.json` contains CLOSED `93180-0001` and OPEN `93180-0002`
- OPEN campaign id: `pc-92d7e68a003a6a2a-93180-0002`
- OPEN campaign date: `2022-11-25`
- OPEN campaign quantity: `700`
- `bootstrap_open_campaign_count = 1`
- `bootstrap_open_campaign_symbols = ["93180"]`
- `missing_current_campaign_symbols = []`

Strategy Intelligence:

- `producer_identity.module = ai_fund_lab_v2.strategy.strategy_intelligence`
- `producer_identity.artifact_function = produce_strategy_intelligence_artifact`
- `position_campaign_id = pc-92d7e68a003a6a2a-93180-0002`
- `campaign_opened_date = 2022-11-25`
- `campaign_status = OPEN`
- `campaign_identity_authority_status = COMPLETE`
- `missing_campaign_authority_fields = []`

Downstream:

- PM action for `93180` = `HOLD`
- PM no longer emits `canonical_campaign_identity_missing`
- PC `membership_intent = RETAIN`
- PS `sizing_status = SIZED`
- Runtime Planning `planning_intent = NO_ACTION`, `order_side_intent = NONE`
- Strategy Planning Authority = `PASS`
- No `strategy_plan_order_side_unresolved` remains for `93180`

## Scope Preservation

G110 did not change:

- campaign COMPLETE predicates
- PM thresholds
- Market Quality / Risk Pacing
- Candidate ranking
- ADD semantics
- PS quantity authority
- Runtime priority
- Submit
- Pending
- Safety
- G90 / G97 / G99 / G102 / G104 semantics

The repair only changes actual pre-action campaign materialization so that CLOSED prior campaigns do
not suppress strict-prior ledger OPEN campaign publication.

## Source Identity Observability

Strategy Intelligence artifacts now include `producer_identity`:

- module
- module file
- artifact function
- payload builder function
- campaign identity function
- campaign join function
- producer version
- semantic version

This addresses the G109 source-identity ambiguity where `source_dirty = true` made commit hash alone
insufficient to prove which producer generated an artifact.

## Regression Results

PASS:

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_g110_actual_path_campaign_activation.py
1 passed in 11.35s
```

Final rerun:

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_g110_actual_path_campaign_activation.py
1 passed in 12.70s
```

PASS:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase31_g110_actual_path_campaign_activation.py \
  tests/strategy/test_phase30_n_strategy_intelligence_campaign_authority.py \
  tests/strategy/test_phase30_p_strategy_intelligence_production_migration.py \
  tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py \
  tests/runtime_v2/test_phase20_y_pm_cross_regime_campaign.py \
  tests/runtime_v2/test_phase23_i_strategy_planning_authority.py

54 passed in 54.22s
```

PASS:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase30_j_strategy_intelligence.py \
  tests/strategy/test_phase30_l_strategy_intelligence_gap_repair.py \
  tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py \
  tests/runtime_v2/test_phase30_ak9r28_historical_safety_temporal_authority.py

33 passed in 2.33s
```

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/shadow_runtime.py \
  src/ai_fund_lab_v2/strategy/strategy_intelligence.py \
  src/ai_fund_lab_v2/strategy/position_management.py \
  src/ai_fund_lab_v2/strategy/portfolio_construction.py \
  src/ai_fund_lab_v2/strategy/position_sizing.py \
  src/ai_fund_lab_v2/strategy/runtime_planning.py \
  src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py
```

PASS:

```text
git diff --check
```

Artifact-dependent G102/G99 tests were not counted as G110 PASS because their historical target
artifacts are not guaranteed to exist in this checkout.

No fresh-run, resume, replay, or long Historical was executed by Codex.

## Required Judgments

G108_ACTUAL_BYPASS_CLASS = A7

Reason: other confirmed actual-path defect. The canonical G108 Strategy Intelligence producer was connected, but its canonical campaign input artifact was incomplete because pre-action campaign materialization suppressed a strict-prior ledger OPEN campaign when a prior CLOSED same-symbol campaign existed.

CANONICAL_STRATEGY_INTELLIGENCE_PRODUCER_CONNECTED = YES

DUPLICATE_LEGACY_PRODUCER_REMAINS_ACTIVE = NO

ACTUAL_PATH_G108_BRANCH_REACHED = YES

ACTUAL_PATH_93180_CAMPAIGN_IDENTITY_COMPLETE = YES

ACTUAL_PATH_PM_CAMPAIGN_IDENTITY_REVIEW_CLEARED = YES

20221128_STRATEGY_PLANNING_AUTHORITY_NOT_REVIEW_FROM_93180 = YES

SECOND_INDEPENDENT_BLOCKER_PRESENT = NO

ACTUAL_RUNTIME_MORNING_PATH_GATE = PASS

STRATEGY_INTELLIGENCE_PRODUCER_IDENTITY_OBSERVABLE = YES

G90_CHANGED = NO

G97_CHANGED = NO

G99_CHANGED = NO

G102_CHANGED = NO

G104_CHANGED = NO

PM_THRESHOLDS_CHANGED = NO

SUBMIT_CHANGED = NO

PENDING_CHANGED = NO

SAFETY_CHANGED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

G110_ACCEPTED = YES

## Operator Verification Sequence

Do not start a new fresh-run before resume compatibility is checked.

First, operator should run a dry-run resume on:

`runtime-test-historical-extended-smoke-20260825T072702567342Z`

Only if compatible, proceed with actual resume of the same run.
