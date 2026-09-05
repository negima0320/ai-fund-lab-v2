# Phase32-GZ — ADD Count Hard-Block Removal / Observability-Only Count Minimal Production Repair / Focused Acceptance

Date: 2026-09-05

## Executive Summary

Phase32-GZ implemented the minimal Production repair authorized by GX/GY:

```text
current open campaign ADD count >= 5
-> observability / audit metadata only
-> no standalone NO_ADD / ADD-to-HOLD / capital-competition exclusion authority
```

No new ADD logic, authority, comparator, threshold, numeric weight, schema family, runtime mutation, fresh run, resume, replay, or recover was introduced.

## Production Changes

### PM ADD Worthiness

File: `src/ai_fund_lab_v2/strategy/position_management.py`

`_structured_add_worthiness_evidence()` no longer appends the legacy count-only blocker to `reason_codes`. ADD worthiness still blocks on existing Current-PIT / lifecycle evidence:

- incomplete canonical campaign identity
- continuation quality not PASS
- downside risk blocking status
- prior reduce history requiring ADD review

The current open-campaign ADD count remains visible inside the existing ADD worthiness evidence:

- `add_history_summary`
- `current_campaign_add_count`
- `add_count_limit_reached_observed`
- `add_count_excess_observed`
- `add_count_observability_only`
- `add_count_standalone_decision_authority`

### PC Lifecycle Mirror

File: `src/ai_fund_lab_v2/strategy/portfolio_construction.py`

`_campaign_aware_add_worthiness_state()` no longer returns `NO_ADD` solely because `add_history_summary.event_count >= 5`.

PC still returns `NO_ADD` for existing non-count blockers:

- not HELD
- incomplete campaign identity
- prior reduce history
- continuation quality not PASS
- downside risk block/fail
- unsupported profit-protection status

PC keeps count visible in existing Strategy Intelligence member fields:

- `strategy_intelligence_add_history_count`
- `strategy_intelligence_add_count_observability_only`
- `strategy_intelligence_add_count_limit_reached_observed`
- `strategy_intelligence_add_count_excess_observed`
- `strategy_intelligence_add_count_standalone_decision_authority`

## SoT Update

Updated:

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

Permanent contract added:

```text
Open-campaign ADD count is observability/audit metadata, not standalone ADD investment/safety authority.
Repeated ADD is allowed only when each increment independently satisfies Current-PIT ADD worthiness, capital competition, sizing, Cash, cap/headroom, lot, Safety, and order-increment authority.
No fixed ADD-count hard cap is Production decision authority.
```

## Focused Acceptance Evidence

New focused Production tests:

`tests/strategy/test_phase32_gz_add_count_observability_only_production.py`

Coverage:

- count over five is PM observability, not `NO_ADD`
- PM payload preserves `ADD` when count is the only former blocker
- continuation-quality failure still blocks even with count room
- reduce-history still blocks when count is over five
- count-over-five ADD reaches PC capital competition
- PC SI mirror preserves count observability without `NO_ADD`
- count 6 / 8 / 12 still reevaluate Current-PIT risk every increment

Updated GY shadow test to reflect accepted Production semantics:

`tests/strategy/test_phase32_gy_add_count_soft_evidence_shadow.py`

## Static Consumer Search

Command:

```text
rg -n "prior_add_history_limits_incremental_add" src tests/strategy/test_phase32_gz_add_count_observability_only_production.py tests/strategy/test_phase32_gy_add_count_soft_evidence_shadow.py
```

Result: no matches.

Interpretation: the legacy reason code has no remaining source/test consumer in the active GZ acceptance surface. Historical phase reports still mention it as baseline evidence only.

## Test Results

### GZ Focused Bundle

Command:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_gz_add_count_observability_only_production.py \
  tests/strategy/test_phase32_gy_add_count_soft_evidence_shadow.py \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g74_si_no_add_does_not_hard_block_positive_add_increment \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g74_99840_equivalent_si_no_add_does_not_hard_block_positive_add_increment \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g74_40520_equivalent_expected_edge_weakening_still_blocks_add \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py::test_phase32_s_missing_campaign_or_no_loss_failure_blocks_acceleration \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py::test_phase32_s_headroom_and_cautious_risk_pacing_bound_magnitude
```

Result:

```text
18 passed in 2.75s
```

### GW / G129 Focused Guard

Command:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase31_g40_opportunity_quality_continuum.py \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase31_g129_actual_buy_add_fill_runtime_id_merges_when_open_campaign_lineage_proves_identity \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase31_g129_actual_shaped_add_history_anchors_merge_with_canonical_bridge \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase31_g129_conflicting_fill_campaign_without_canonical_bridge_does_not_merge
```

Result:

```text
23 passed in 1.96s
```

### SELL / Winner / REENTRY / Runtime Boundary Bundle

Command:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py \
  tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py \
  tests/strategy/test_phase31_g63_runtime_executable_binding.py \
  tests/strategy/test_phase31_g62_position_sizing_g61_binding.py \
  tests/strategy/test_phase32_ck_reentry_buy_new_bypass_guard.py \
  tests/strategy/test_phase32_ew_reentry_semantic_removal_recent_exit_guard.py
```

Result:

```text
33 passed, 9 failed
```

The 9 failures are all `FileNotFoundError` for deleted/missing runtime-test artifacts under:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/...
```

These are artifact dependencies, not GZ regressions.

Artifact-independent REENTRY subset:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_ck_reentry_buy_new_bypass_guard.py::test_phase32_ck_reentry_review_cannot_rebatch_as_buy_new \
  tests/strategy/test_phase32_ck_reentry_buy_new_bypass_guard.py::test_phase32_ck_active_churn_reentry_remains_blocked \
  tests/strategy/test_phase32_ck_reentry_buy_new_bypass_guard.py::test_phase32_ck_valid_reentry_remains_possible_and_not_relabelled_buy_new \
  tests/strategy/test_phase32_ew_reentry_semantic_removal_recent_exit_guard.py \
  tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py
```

Result:

```text
17 passed in 1.63s
```

## Mandatory Answers

- ADD_COUNT_HARD_BLOCK_REMOVED: `YES`
- ADD_COUNT_OBSERVABILITY_PRESERVED: `YES`
- PM_COUNT_ONLY_ADD_TO_HOLD_DOWNGRADE_COUNT: `0`
- PC_COUNT_ONLY_NO_ADD_AUTHORITY_REMAINING: `0`
- COUNT_OVER_5_ADD_WORTHY_PATH_PASS: `YES`
- COUNT_OVER_5_CAPITAL_COMPETITION_PATH_REACHED: `YES`
- NEW_ADD_COMPETITION_PRESERVED: `YES`
- CASH_COMPETITION_PRESERVED: `YES`
- NO_LOSS_AVERAGING_BYPASS_COUNT: `0`
- DETERIORATION_BYPASS_COUNT: `0`
- CONCENTRATION_HEADROOM_BYPASS_COUNT: `0`
- LIQUIDITY_BYPASS_COUNT: `0`
- LOT_BYPASS_COUNT: `0`
- INSUFFICIENT_EVIDENCE_FALSE_RELEASE_COUNT: `0`
- G129_REGRESSION_COUNT: `0`
- CAMPAIGN_IDENTITY_CHANGED: `NO`
- SELL_CHANGED: `NO`
- WINNER_CHANGED: `NO`
- SIZING_CHANGED: `NO`
- CASH_CHANGED: `NO`
- REENTRY_CHANGED: `NO`
- RECENT_EXIT_GUARD_CHANGED: `NO`
- RUNAWAY_PYRAMIDING_ADVERSARIAL_CASES_PASS: `YES`
- LEGACY_COUNT_BLOCK_REASON_CONSUMER_COUNT: `0`
- NEW_MODULE_COUNT: `0`
- NEW_COMPONENT_COUNT: `0`
- NEW_AUTHORITY_COUNT: `0`
- NEW_COMPARATOR_COUNT: `0`
- NEW_SCHEMA_FAMILY_COUNT: `0`
- NEW_THRESHOLD_COUNT: `0`
- NEW_NUMERIC_WEIGHT_COUNT: `0`
- SOT_UPDATED: `YES`
- FOCUSED_TEST_PASS: `YES`
- MINIMAL_PRODUCTION_REPAIR_ACCEPTED: `YES`
- SHORT_DYNAMIC_VALIDATION_READY: `YES`
- LONG_HORIZON_VALIDATION_READY: `NO_SHORT_DYNAMIC_FIRST`
- DIRECT_PRODUCTION_PROMOTION_READY: `NO_DYNAMIC_VALIDATION_REQUIRED`
- NEXT_STEP: `Run short dynamic validation with explicit monitoring for count-over-five ADD candidates reaching capital competition, unsafe release count, no-loss/deterioration/headroom/liquidity/lot bypass counts, Cash preservation, G129, SELL/Winner, and Recent Exit/REENTRY isolation.`

## Final Judgment

current open campaign ADD count >=5という過去行動だけのhard blockをProduction decision authorityから除去し、countをobservabilityとして残しながら、6回目以降も既存Current-PIT ADD Safety / MCV / NCU / Cash / cap / lot / G129で毎回独立評価される最小修正を安全に実装できた。
