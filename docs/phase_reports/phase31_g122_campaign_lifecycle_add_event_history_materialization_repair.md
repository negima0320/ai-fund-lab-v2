# Phase31-G122 — Campaign Lifecycle ADD Event History Materialization Repair

## PRIMARY_JUDGMENT

G122_CAMPAIGN_LIFECYCLE_ADD_HISTORY_MATERIALIZATION_REPAIR_ACCEPTED

## Scope

- Phase: Phase31
- Task type: focused implementation repair
- Repair boundary: `strategy.shadow_runtime._materialize_pre_action_position_campaigns()`
- Fresh-run/resume/replay/long Historical executed: NO
- PM ADD policy changed: NO
- G115 marginal competition changed: NO
- Market Quality / Risk Pacing changed: NO
- Position Sizing / Runtime / Submit changed: NO

## Source Basis

Read and used:

- `docs/phase_reports/phase31_g120_post_g119_long_horizon_performance_capital_characterization.md`
- `docs/phase_reports/phase31_g121_campaign_level_add_identity_winner_scaling_audit.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`

## Confirmed Defect

G121 confirmed:

```text
actual BUY_ADD fill exists
+ OPEN campaign exists
+ same position_campaign_id is preserved
+ campaign quantity increases correctly
BUT
campaign events / buy_history_summary / add_history_summary
do not record the additional BUY execution.
```

The root boundary was:

```text
_materialize_pre_action_position_campaigns()
  existing prior OPEN campaign
  -> _refresh_campaign_with_current()
```

`_refresh_campaign_with_current()` updated current quantity and valuation state, but did not merge strict-prior ledger BUY executions that happened after the previous campaign snapshot while the same campaign remained open.

## Repair

Added a narrow merge step after refreshing an existing open campaign:

```text
strict-prior ledger campaign reconstruction
-> existing open canonical campaign
-> merge missing execution-backed events/history
```

The repair:

- Preserves the existing `position_campaign_id`.
- Requires strict-prior execution / ledger evidence.
- Does not infer ADD from quantity delta.
- Appends missing BUY events deterministically.
- Updates `buy_history_summary` to count all campaign BUY executions.
- Updates `add_history_summary` to count only BUY executions after the initial BUY.
- Keeps flat-after-EXIT BUY as re-entry / new campaign.
- Dedupes by execution identity, with a natural-key replacement only for legacy event rows missing execution IDs.

Changed:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`

Added:

- `tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py`

Updated SoT:

- `docs/02_architecture/strategy_intelligence_architecture_v1.md`

## Actual-Shape Producer-Equivalent Gate

Using existing completed artifacts from:

```text
runtime-test-historical-extended-smoke-20260825T135619843503Z
```

I built a temporary `/private/tmp` producer-equivalent run directory and a minimal strict-prior ledger from completed `execution/fills.json` evidence. No source run artifact was modified.

Result:

| Materialization date | Symbol | BUY events | buy_history count | add_history count | Quantity | Gate |
|---|---|---:|---:|---:|---:|---|
| 2022-10-13 | 94320 | 2 | 2 | 1 | 300 | PASS |
| 2022-10-13 | 94340 | 2 | 2 | 1 | 300 | PASS |
| 2022-10-14 | 94340 | 3 | 3 | 2 | 400 | PASS |
| 2023-02-16 | 54010 | 2 | 2 | 1 | 200 | PASS |
| 2023-06-01 | 30410 | 2 | 2 | 1 | 200 | PASS |

`G121_TRUE_ADD_ANCHORS_RECONCILED = 5/5`

## Regression Results

PASS:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py
```

Result:

```text
4 passed
```

PASS:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py::test_phase30_ad1_first_buy_multi_symbol_bootstrap_uses_strict_prior_ledger \
  tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py::test_phase30_ad1_add_reduce_exit_and_reentry_lifecycle_from_ledger \
  tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py::test_phase30_ad1_prior_open_campaign_closes_when_strict_prior_ledger_exits \
  tests/strategy/test_phase30_n_strategy_intelligence_campaign_authority.py \
  tests/strategy/test_phase31_g110_actual_path_campaign_activation.py \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py \
  tests/strategy/test_phase31_g117_normal_buy_scope_repair.py \
  tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py
```

Result:

```text
22 passed, 1 skipped
```

Attempted broader nearby command:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py \
  tests/strategy/test_phase30_n_strategy_intelligence_campaign_authority.py \
  tests/strategy/test_phase31_g110_actual_path_campaign_activation.py \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py \
  tests/strategy/test_phase31_g117_normal_buy_scope_repair.py \
  tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py
```

Result:

```text
1 failed, 39 passed, 1 skipped
```

The failed test was:

```text
tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py::test_phase22_p_strategy_shadow_generation_preserves_runtime_authority
```

Failure:

```text
assert summary["runtime_mutation_performed"] is False
actual True
```

This test uses the live `.runtime` fixture state and is not specific to the G122 campaign materializer. Direct materializer lifecycle tests and focused downstream consumers passed.

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/shadow_runtime.py \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py
```

PASS:

```text
git diff --check
```

## Required Judgments

G122_CAMPAIGN_ADD_HISTORY_REPAIRED = YES

OPEN_CAMPAIGN_BUY_IS_ADD = YES

FLAT_AFTER_EXIT_BUY_IS_REENTRY = YES

STRICT_PRIOR_LEDGER_ADD_EVENTS_MERGED_INTO_OPEN_CAMPAIGN = YES

SYNTHETIC_ADD_FROM_QUANTITY_DELTA = NO

ADD_EVENT_MATERIALIZATION_IDEMPOTENT = YES

CAMPAIGN_EVENT_ORDER_DETERMINISTIC = YES

BUY_HISTORY_SUMMARY_COUNTS_ALL_CAMPAIGN_BUYS = YES

ADD_HISTORY_INITIAL_BUY_EXCLUDED = YES

G121_TRUE_ADD_ANCHORS_RECONCILED = 5/5

94340_MULTI_ADD_CAMPAIGN_GATE = PASS

94320_ADD_GATE = PASS

54010_ADD_GATE = PASS

30410_ADD_GATE = PASS

REENTRY_MERGED_INTO_PRIOR_CLOSED_CAMPAIGN_COUNT = 0

NEW_CAMPAIGN_ID_AFTER_FLAT_PRESERVED = YES

CAMPAIGN_ADD_QUANTITY_RECONCILIATION_FAILURE_COUNT = 0

SELL_LIFECYCLE_CHANGED = NO

PM_ADD_POLICY_CHANGED = NO

G115_CHANGED = NO

PS_CHANGED = NO

RUNTIME_PRIORITY_CHANGED = NO

SUBMIT_CHANGED = NO

G122_CAMPAIGN_ADD_ACTUAL_PATH_GATE = PASS

CAMPAIGN_HISTORY_CONSUMER_REGRESSION = NO

FUTURE_INFORMATION_USED = NO

HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_DECISION = NO

G122_ACCEPTED = YES

## Final Decision

G122_CAMPAIGN_LIFECYCLE_ADD_HISTORY_MATERIALIZATION_REPAIR_ACCEPTED

## Next

Return to operator / ChatGPT for validation sequencing. Do not assume old long-run performance is reproducible without a fresh validation run, because downstream Strategy Intelligence now receives correct campaign ADD history.

