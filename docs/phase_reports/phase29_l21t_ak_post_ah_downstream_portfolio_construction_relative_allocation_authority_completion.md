# Phase29-L21T-AK - Post-AH Downstream Portfolio Construction Relative Allocation Authority Completion

## Primary Judgment

`PHASE29_L21T_AK_POST_AH_DOWNSTREAM_PORTFOLIO_CONSTRUCTION_RELATIVE_ALLOCATION_AUTHORITY_COMPLETED_FOCUSED_REGRESSION_PASS`

Current Phase remains `Phase29`.  Phase30 was not entered.

## Scope

| Field | Value |
| --- | --- |
| Task ID | `Phase29-L21T-AK` |
| Task type | `PRODUCTION-COMMON MINIMAL IMPLEMENTATION + FOCUSED REGRESSION` |
| AJ Judgment inherited | `PHASE29_L21T_AJ_POST_AH_DOWNSTREAM_PORTFOLIO_CONSTRUCTION_ZERO_WEIGHT_AUTHORITY_GAP_CONFIRMED_IMPLEMENTATION_READY` |
| Target pre-AK run | `runtime-test-historical-extended-smoke-20260814T032532992929Z` |
| Target run mutated by Codex | `NO` |
| Long Historical / fresh-run / resume / replay / recovery by Codex | `NO` |
| Config changed | `NO` |
| Model changed | `NO` |
| Threshold changed | `NO` |
| Retraining performed | `NO` |
| Future return used by Runtime | `NO` |
| Historical-only branch added | `NO` |

## Root Cause

AH fixed the upstream Runtime Opportunity eligibility entry point:

```text
calibration_applied=false
economic_units_available=false
runtime_opportunity_score <= 0
-> relative competition eligible
```

AJ then showed that Portfolio Construction still retained two stale absolute
score authorities:

1. `non_positive_expected_edge_score` was consumed through
   `opportunity_no_buy_reason_blocks_buy(...)` without semantic metadata, so
   default economic-units mode turned it into a hard BUY_NEW block.
2. `_select_target_members` still used `runtime_opportunity_score < 0` as a
   standalone non-selectable gate for new candidates.

Result before AK:

```text
negative strong-quality candidate
-> materialized into PC
-> EXCLUDE / non-selectable
-> requested_buy_new_weight = 0
-> accepted_buy_new_weight = 0
-> no positive BUY quantity reaches Planning
```

## Implementation

Changed files:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
src/ai_fund_lab_v2/strategy/runtime_planning.py
tests/strategy/test_phase22_e_portfolio_construction.py
tests/strategy/test_phase22_g_runtime_planning.py
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
docs/02_architecture/strategy_architecture_v1.md
docs/01_requirements/phase_roadmap.md
docs/phase_reports/phase30_a_entry_gate_100bd_baseline_status.md
```

Portfolio Construction now consumes:

```text
canonical_score_field
score_semantic_role
calibration_applied
economic_units_available
```

It classifies `no_buy_reason` into:

```text
hard_blocking_reasons
soft_relative_reasons
unknown_reasons
```

Under the active AH contract:

```text
canonical_score_field = runtime_opportunity_score
score_semantic_role = uncalibrated_relative_model_score
calibration_applied = false
economic_units_available = false
```

the following are no longer standalone hard BUY_NEW rejection authorities:

```text
runtime_opportunity_score <= 0
non_positive_expected_edge_score
below_opportunity_top20
```

Runtime Planning now preserves the same semantic meaning when guarding
executable BUY plans.  Missing semantic metadata remains fail-closed by
defaulting to existing economic-units behavior.

## Authority Result

| Field | Result |
| --- | --- |
| Primary stale authority repaired | `YES` |
| Secondary raw score gate repaired | `YES` |
| AH semantic metadata consumed by PC | `YES` |
| canonical score field | `runtime_opportunity_score` |
| semantic role | `uncalibrated_relative_model_score` |
| calibration_applied behavior | `false` disables unproven economic zero boundary; `true` preserves future calibrated economic gate |
| economic_units_available behavior | `false` makes score-sign no-buy reasons soft relative metadata |
| `non_positive_expected_edge_score` hard block under uncalibrated semantics | `NO` |
| `below_opportunity_top20` standalone hard block under uncalibrated semantics | `NO` |
| hard risk no-buy reasons preserved | `YES` |
| Buy Quality REJECT preserved | `YES` |
| relative competition preserved | `YES` |
| positive score behavior preserved | `YES` |
| negative score auto-BUY introduced | `NO` |
| BUY count forced | `NO` |
| Exposure forced | `NO` |
| Strategy cap preserved | `YES` |
| Safety hard cap preserved | `YES` |
| Lot-first preserved | `YES` |
| Residual reallocation preserved | `YES` |
| ADD semantics changed | `NO` |
| SELL semantics changed | `NO` |
| REDUCE semantics changed | `NO` |
| REENTRY safeguards preserved | `YES` |

## Negative Strong-Quality Candidate Handling

For candidates like `66590`, `93180`, `23700`, and `36640`:

Before AK:

```text
Buy Quality FULL_ALLOCATION_ELIGIBLE
no_buy_reason = non_positive_expected_edge_score
runtime_opportunity_score < 0
-> PC EXCLUDE before target-member competition
```

After AK:

```text
Buy Quality FULL_ALLOCATION_ELIGIBLE
no hard no-buy reason
uncalibrated relative score metadata complete
-> eligible to participate in PC target-member / capital competition
```

This does not mean those symbols are always bought.  They may still receive
zero allocation from ordinary competition, budget limits, quality reduction,
Portfolio Policy, lot feasibility, Safety, broker feasibility, Corporate Event,
Re-entry guards, or other hard blockers.

## Hard Blocker Preservation

Combined reason handling is preserved:

```text
below_opportunity_top20|high_downside_risk_score|non_positive_expected_edge_score
```

Even though `below_opportunity_top20` and `non_positive_expected_edge_score` are
soft metadata under uncalibrated semantics, `high_downside_risk_score` remains
hard and blocks BUY.

Preserved fail-closed cases include:

- Buy Quality `REJECT`
- high downside risk
- unknown hard no-buy reasons
- missing / malformed semantic metadata
- future calibrated economic score with economic units and negative value
- Safety / lot infeasibility
- Corporate Action / broker / liquidity hard blocks
- ADD / SELL / REDUCE / EXIT / REENTRY existing safeguards

## Why Portfolio Path Can Change

The early 2022 trajectory can change after AK because candidates that previously
reached PC only as observable zero-weight rows can now become actual target
member / capital competition participants when their only blocking evidence was
stale score-sign metadata.  That can change requested weights, accepted weights,
Position Sizing quantities, Runtime Planning BUY intents, cash, exposure, and
position count.

This is authority migration completion, not performance tuning.

## Validation Results

Focused:

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py -k 'phase29_l21t_ak'
9 passed

PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_g_runtime_planning.py -k 'phase23_bh or phase29_l21t_ak'
2 passed
```

Affected area:

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py
91 passed

PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py
231 passed

PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bv15_opportunity_buy_eligibility_contract.py tests/strategy/test_phase26_h_adaptive_buy_quality.py
27 passed

PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_g_runtime_planning.py
48 passed

PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase23_i_strategy_planning_authority.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
58 passed

PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/strategy/test_phase29_l21k_prior_exit_materialization.py
57 passed

PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase26_step4_position_sizing_authority.py tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py tests/runtime_v2/test_phase22_gr_runtime_planning_regression_repair.py
16 passed

PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py
78 passed

PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase14e8_demo_broker_capability_evaluation_capital_fix.py
13 passed

PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase13_q_ledger_projection.py tests/runtime_v2/test_phase13_r_reconcile_orders_vs_executions.py tests/runtime_v2/test_phase13_r_reconcile_positions_vs_asset.py tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py tests/runtime_v2/test_phase15bv_execution_normalization_current_apply.py
28 passed
```

Residual unrelated broader execution check:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase13_q_ledger_projection.py tests/runtime_v2/test_phase13_r_reconcile_orders_vs_executions.py tests/runtime_v2/test_phase13_r_reconcile_positions_vs_asset.py tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py tests/runtime_v2/test_phase15bv_execution_normalization_current_apply.py
1 failed, 28 passed
```

Failure:

```text
test_phase14e21_execution_readonly_ingests_broker_evidence_without_overwriting_demo_asset
assert result.asset_connected is True
actual: False
```

This is recorded as an existing unrelated execution-readonly residual risk.  It
does not exercise the AK Portfolio Construction / Runtime Planning score
semantic path.

Final checks:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/runtime_planning.py
PASS
```

## Machine-Readable Summary

```text
reports/phase29_l21t_ak_post_ah_downstream_portfolio_construction_relative_allocation_authority_completion/summary.json
```

## Fresh Validation Requirement

Fresh 4-year rerun required:

```text
YES
```

Reason:

```text
runtime-test-historical-extended-smoke-20260814T032532992929Z contains pre-AK
completed days and is pre-AK evidence only.  BUY_NEW target-member eligibility
can change after AK, so a formal post-AK baseline requires a fresh run.
```

Codex did not execute the fresh run.

## Phase30 Status

| Field | Value |
| --- | --- |
| Common SoT updated | `YES` |
| Phase30 entry register updated | `YES` |
| Phase30 entered | `NO` |
| Phase30 blocker status | `BLOCKED_PENDING_POST_AK_FRESH_BASELINE_VALIDATION` |

## Recommended Next Task

`Phase29-L21T-AL - Post-AK Fresh Validation Readiness / Early Checkpoint Command Preparation`

## Final Questions

Portfolio ConstructionはAK後、uncalibrated relative
`runtime_opportunity_score`の符号をabsolute BUY_NEW gateとして使わず、Buy
Quality / relative competitionへ正しくauthorityを渡せるようになったか？

```text
YES
```

Evidence: focused PC AK regression 9 passed.  `non_positive_expected_edge_score`
and standalone `below_opportunity_top20` no longer hard-block under complete
uncalibrated relative metadata, and Runtime Planning preserves the same
semantics for executable BUY plans.

high downside / Safety / Lot / Corporate Action / Broker / Re-entry等の本来の
hard blockersを弱体化せずに修理できたか？

```text
YES
```

Evidence: high downside combined reason, Buy Quality REJECT, missing semantic
metadata, calibrated economic negative score, lot/planning authority, ADD,
SELL, REDUCE, Submit, Re-entry, and execution/reconcile focused regressions were
kept in the validation set above.

