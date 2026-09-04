# Phase32-EC — Incumbent Strength-to-Increment Target Authority SHADOW Design / Implementation / One-Year Impact Audit

## Scope

Implemented a SHADOW-only PC-owned authority:

`ADD_STRENGTH_TO_INCREMENT_TARGET_AUTHORITY`

Primary source run:

`runtime-test-historical-extended-smoke-20260902T060955933565Z`

Primary comparison baseline:

`reports/runtime_tests/analysis/phase32_dw_dq_shadow_backfill_20260903T000001`

EC one-year output:

`reports/runtime_tests/analysis/phase32_ec_add_strength_increment_shadow_20260903T000002`

Window:

`2022-10-03` through `2023-10-26`

No Production consumer was connected. No fresh-run, resume, recover, replay, or long Historical run was executed.

## Design

The new authority is materialized on each DW `BUY_ADD_NEXT_LOT` competitor row as:

`add_strength_to_increment_target_authority`

It is owned by:

`PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY`

It separates:

- ADD eligibility: PM/BQ/Entry says the incumbent may be considered.
- ADD increment demand: current PIT evidence justifies positive capital above current weight.

PM ADD alone cannot create positive demand. A fixed ADD bonus, NEW penalty, REENTRY penalty, incumbent preference, or carry-forward conviction score is not used.

Positive demand requires current-day evidence:

- PM ADD intent.
- campaign identity and PM decision provenance.
- current position and current weight.
- structured headroom.
- BQ not hard-blocking.
- Entry not hard-blocking.
- PM strength reason codes.
- no-loss averaging.
- campaign continuation.
- expected edge positive/pass.
- incremental value `POSITIVE`.
- opportunity cost `PASS`.
- PIT validation `PASS`.

`UNKNOWN` incremental value remains non-positive.

Magnitude is conservative and diagnostic: it uses existing observed next-lot/headroom/accepted-increment evidence. It does not choose a tuned percentage from Historical PnL.

## Implementation

Changed:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `scripts/runtime_test.py`
- `tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py`
- `tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py`

Key implementation points:

- Added `add_strength_to_increment_target_authority.v1`.
- Added per-row `ec_proposed_refreshed_target_weight`, `ec_proposed_incremental_target_weight`, and `ec_positive_increment_demand`.
- Added `ec_strength_increment_executable_capital_ranking` as SHADOW diagnostic only.
- Added backfill summary counters for EC evidence tier, demand status, zero-desired reclassification, EC Stage-B winners, campaign-level positive demand, and regime-level EC demand.
- Preserved DW Stage A / Stage B Production comparison unchanged.

Production isolation flags remain:

- `authoritative_consumer_count = 0`
- `production_allocation_consumer = False`
- `production_ordering_consumer = False`
- `production_sizing_consumer = False`
- `runtime_planning_consumer = False`

## Focused Validation

Passed:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ec python3 -m pytest -q tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py
```

Result:

`14 passed`

Passed broader focused regression:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ec python3 -m pytest -q tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase31_g63_runtime_executable_binding.py tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py
```

Result:

`67 passed`

Passed:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ec python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/strategy/marginal_capital_value.py
```

Result:

`PASS`

## EC One-Year Backfill

Executed isolated analysis command:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ec python3 scripts/runtime_test.py shadow-backfill-marginal-capital --source-run-id runtime-test-historical-extended-smoke-20260902T060955933565Z --start-date 2022-10-03 --end-date 2023-10-26 --output-root reports/runtime_tests/analysis/phase32_ec_add_strength_increment_shadow_20260903T000002 --confirm --json
```

Result:

- status: `PASS`
- business days: `264`
- production change executed: `false`
- target run mutated: `false`
- runtime state mutated: `false`

## DW vs EC Summary

DW baseline counts:

| Metric | DW |
| --- | ---: |
| BUY_ADD rows | 152 |
| `NO_POSITIVE_DESIRED_INCREMENT` | 99 |
| `NO_ACCEPTED_CONTINUOUS_INCREMENT` | 22 |
| `BQ_BLOCKS_INCREMENT` | 9 |
| `EXECUTABLE_INCREMENT_AVAILABLE` | 19 |
| `SAFETY_HARD_CAP_BLOCK` | 3 |
| Stage-B ADD winners | 11 |

EC overlay counts:

| EC metric | Count |
| --- | ---: |
| `POSITIVE_INCREMENT_DEMAND` | 17 |
| `NO_POSITIVE_DEMAND` | 62 |
| `BLOCKED` | 73 |
| `MODERATE_COMPLETE` evidence tier | 17 |
| `INSUFFICIENT` evidence tier | 62 |
| `BLOCKED` evidence tier | 73 |
| EC ADD eligible rows | 21 |
| EC Stage-B ADD winners | 11 |

Stage-B winner distribution is unchanged:

| Winner type | DW Stage-B | EC overlay |
| --- | ---: | ---: |
| BUY_ADD_NEXT_LOT | 11 | 11 |
| BUY_NEW_NEXT_LOT | 212 | 212 |
| REENTRY_NEXT_LOT | 37 | 37 |
| CASH_OPTIONALITY | 3 | 3 |
| NONE | 1 | 1 |

Interpretation:

EC did not create new executable ADD winner days in the current one-year evidence. It confirmed that, under strict PIT evidence sufficiency, Production's existing executable ADD controls are the rows where positive ADD demand is currently defensible.

## 99 Zero-Desired Reclassification

All 99 EB `NO_POSITIVE_DESIRED_INCREMENT` rows remain zero under EC:

| Reclassification | Count |
| --- | ---: |
| remain zero | 99 |
| become positive but evidence incomplete | 0 |
| become positive but infeasible | 0 |
| become complete + executable positive ADD demand | 0 |
| become Stage-B ADD winner | 0 |

Breakdown:

- 50 are `BLOCKED`.
- 49 are `NO_POSITIVE_DEMAND`.

This is intentional. EC does not infer a positive increment from PM ADD alone or from incomplete incumbent evidence.

## EB Strong-ish 49 Reassessment

EB strong-ish set:

`NO_POSITIVE_DESIRED_INCREMENT + HEADROOM_AVAILABLE + BQ/Entry not fully hard-blocked`

EC result:

| EC status | Count |
| --- | ---: |
| `NO_POSITIVE_DEMAND` | 49 |

Quality classes:

| Class | Count |
| --- | ---: |
| `BLOCKED` | 35 |
| `INSUFFICIENT` | 14 |

The strong-ish 49 remain non-positive because the missing bridge is not just target arithmetic. Their current ADD investment evidence still lacks a complete PIT-positive incremental value / opportunity-cost / expected-edge package.

## Positive Controls

Existing executable ADD controls are preserved:

- Existing executable ADD rows: 19
- Complete positive EC demand rows: 17
- EC ADD eligible rows: 21
- Stage-B ADD winners: 11

The Stage-B ADD winner count remains `11`, matching DW.

## 94320 Graduation Control

94320:

- ADD rows: 50
- EC positive demand: 9
- blocked: 27
- no positive demand: 14

Positive EC demand dates:

| Date | Campaign | Proposed increment |
| --- | --- | ---: |
| 2022-10-28 | `pc-401763653bc4df1d-94320-0001` | 0.037037 |
| 2022-11-01 | `pc-401763653bc4df1d-94320-0001` | 0.032258 |
| 2023-01-26 | `pc-7c5bd9294d48b016-94320-0001` | 0.027778 |
| 2023-01-31 | `pc-7c5bd9294d48b016-94320-0001` | 0.034483 |
| 2023-02-01 | `pc-7c5bd9294d48b016-94320-0001` | 0.027778 |
| 2023-02-13 | `pc-7c5bd9294d48b016-94320-0001` | 0.033333 |
| 2023-02-22 | `pc-7c5bd9294d48b016-94320-0001` | 0.040000 |
| 2023-02-24 | `pc-7c5bd9294d48b016-94320-0001` | 0.033333 |
| 2023-03-15 | `pc-7c5bd9294d48b016-94320-0001` | 0.029412 |

94320 remains the positive control: EC recognizes already-defensible positive ADD demand and preserves repeated qualifying days without carrying stale conviction forward.

## Failed-Graduation Controls

| Symbol | EC result |
| --- | --- |
| 99840 | 26 rows; 0 positive demand; 20 blocked; 6 no-positive-demand |
| 94340 | 20 rows; 4 positive demand; 10 no-positive-demand; 6 blocked |
| 83060 | 15 rows; 2 positive demand; 7 no-positive-demand; 6 blocked |
| 40520 | 7 rows; 0 positive demand; 5 blocked; 2 no-positive-demand |
| 43880 | 12 rows; 0 positive demand; 9 no-positive-demand; 3 blocked |
| 54010 | 6 rows; 1 positive demand; 4 no-positive-demand; 1 blocked |

EC does not rescue 99840/40520/43880 because the required PIT-positive incremental evidence is absent or blocked. It recognizes only the subset of 94340/83060/54010 where current evidence is complete enough.

## Campaign-Level Impact

Campaigns with EC positive increment demand:

| Campaign | Positive demand days |
| --- | ---: |
| `94320|pc-7c5bd9294d48b016-94320-0001` | 7 |
| `94340|pc-c09afbf08095a527-94340-0001` | 4 |
| `94320|pc-401763653bc4df1d-94320-0001` | 2 |
| `83060|pc-090162015342d58a-83060-0001` | 2 |
| `54010|pc-0972f0d0a80bbd70-54010-0001` | 1 |
| `59550|pc-15bcec8077b3dc77-59550-0001` | 1 |

Unique campaigns receiving positive demand:

`6`

Repeated positive-demand campaigns:

`4`

Longest positive-demand campaign count:

`7`

One-day-only campaigns:

`2`

No capital reservation or future order promise is created.

## Portfolio-Level Impact Estimate

Compared with DW:

- additional EC Stage-B ADD winner days: `0`
- NEW winner days displaced: `0`
- REENTRY winner days displaced: `0`
- Cash winner days displaced: `0`
- same-symbol ADD graduation frequency: unchanged at current Stage-B winner level
- expected position-count/concentration direction under current strict EC evidence: neutral

This is not a negative performance judgment. It means the current evidence set still does not support Production promotion of a broader ADD target-refresh rule.

## Regime Breakdown

EC ADD demand by trend regime:

| Regime | Blocked | No positive demand | Positive demand |
| --- | ---: | ---: | ---: |
| BULL | 47 | 34 | 9 |
| RECOVERY | 9 | 5 | 2 |
| RANGE | 7 | 12 | 3 |
| CORRECTION | 5 | 1 | 0 |
| BEAR | 5 | 10 | 3 |

No fixed regime -> ADD preference was introduced.

## June–September 2023 Focus

June-September 2023 ADD rows:

`20`

EC statuses:

| Status | Count |
| --- | ---: |
| `BLOCKED` | 16 |
| `NO_POSITIVE_DEMAND` | 4 |
| `POSITIVE_INCREMENT_DEMAND` | 0 |

The period previously associated with weak ADD graduation does not become positive under EC. Current PIT ADD evidence in that window is blocked or insufficient rather than cleanly underfunded.

## Production Readiness

`ADD_STRENGTH_INCREMENT_AUTHORITY_PRODUCTION_READINESS = NOT_READY`

Reasons:

- EC successfully materializes the missing contract shape.
- Actual one-year evidence does not show new clean positive-demand ADD rows among the 99 zero-desired cases.
- EB's strong-ish 49 remain blocked/insufficient.
- Current ADD investment evidence remains the limiting input, especially incremental value and opportunity-cost quality.
- No Production allocation change should be promoted from this EC result.

## Required Final Answers

1. `AUTHORITY_OWNERSHIP_PRESERVED = PASS`
2. `ADD_ELIGIBILITY_AND_INCREMENT_DEMAND_SEPARATED = YES`
3. `INCUMBENT_INCREMENT_EVIDENCE_CONTRACT = PM_ADD + CAMPAIGN_ID + SOURCE_PM_DECISION + CURRENT_POSITION + CURRENT_WEIGHT + PM_STRENGTH_REASONS + NO_LOSS + CAMPAIGN_CONTINUATION + EXPECTED_EDGE + INCREMENTAL_VALUE + OPPORTUNITY_COST + BQ + ENTRY + STRUCTURED_HEADROOM + PIT`
4. `ADD_INCREMENT_EVIDENCE_SUFFICIENCY_CONTRACT = PASS; STRONG_COMPLETE/MODERATE_COMPLETE/INSUFFICIENT/BLOCKED; UNKNOWN_INCREMENTAL_VALUE_STAYS_NON_POSITIVE`
5. `FIXED_ADD_BONUS = NO`
6. `SHADOW_INCREMENT_TARGET_MATERIALIZED = YES`
7. `HISTORICAL_PNL_USED_FOR_INCREMENT_MAGNITUDE = NO`
8. `CURRENT_TARGET_NOT_TREATED_AS_PERMANENT_CEILING = YES_IN_SHADOW_ONLY`
9. `FRESH_PIT_TARGET_REFRESH = PASS`
10. `REPEATED_INCREMENT_DEMAND_OBSERVABILITY = PASS`
11. `BQ_ENTRY_AUTHORITY_PRESERVED = PASS`
12. `ADD_INVESTMENT_EVIDENCE_QUALITY_AUDIT = CURRENT_LIMITING_INPUT; MANY_ADD_ROWS_HAVE_INCREMENTAL_VALUE_UNKNOWN_OR_OPPORTUNITY_COST_NOT_PASS; NOT_A_PROPAGATION_PROVEN_DEFECT_IN_EC`
13. `DW_TWO_STAGE_SHADOW_INTEGRATION = PASS`
14. `FINAL_MARGINAL_COMPETITION_ACTION_NEUTRAL = PASS`
15. `ZERO_DESIRED_99_RECLASSIFICATION = REMAIN_ZERO_99; POSITIVE_INCOMPLETE_0; POSITIVE_INFEASIBLE_0; COMPLETE_EXECUTABLE_POSITIVE_0; STAGE_B_ADD_WINNER_0`
16. `EB_STRONGISH_49_REASSESSMENT = NO_POSITIVE_DEMAND_49; QUALITY_BLOCKED_35; INSUFFICIENT_14`
17. `EXISTING_EXECUTABLE_ADD_CONTROLS_PRESERVED = PASS`
18. `94320_SHADOW_GRADUATION_CONTROL = PASS; 9_POSITIVE_DEMAND_DAYS; 5_STAGE_B_WINNER_CONTROL_DAYS_PRESERVED`
19. `FAILED_GRADUATION_SHADOW_REASSESSMENT = 99840/40520/43880_REMAIN_ZERO; 94340/83060/54010_HAVE_LIMITED_EVIDENCE_POSITIVE_SUBSETS`
20. `CAMPAIGN_LEVEL_INCREMENT_DEMAND_IMPACT = 6_CAMPAIGNS_POSITIVE; 4_REPEATED; LONGEST_COUNT_7; 2_ONE_DAY_ONLY`
21. `SHADOW_PORTFOLIO_STRUCTURE_IMPACT_ESTIMATE = NEUTRAL_UNDER_CURRENT_STRICT_EVIDENCE; ADD_STAGE_B_11_UNCHANGED; NEW/REENTRY/CASH_DISPLACEMENT_0`
22. `REGIME_INCREMENT_DEMAND_PROFILE = BULL_9_POSITIVE; RECOVERY_2; RANGE_3; CORRECTION_0; BEAR_3`
23. `2023_JUN_SEP_WINNER_GRADUATION_SHADOW_IMPACT = 20_ADD_ROWS; 0_POSITIVE_DEMAND; 16_BLOCKED; 4_NO_POSITIVE_DEMAND`
24. `STRUCTURED_HEADROOM_PRESERVED = PASS`
25. `DEMAND_VS_EXECUTABILITY_SEPARATION = PASS`
26. `PRODUCTION_ISOLATION = PASS`
27. `SHADOW_FAILURE_ISOLATION_PRESERVED = PASS`
28. `EC_ONE_YEAR_SHADOW_BACKFILL_EXECUTED = YES`
29. `DW_VS_EC_INCREMENT_DEMAND_COMPARISON = DW_STAGE_B_ADD_11; EC_STAGE_B_ADD_11; ZERO_DESIRED_99_REMAIN_ZERO; EC_POSITIVE_DEMAND_17; UNIQUE_CAMPAIGNS_AFFECTED_6`
30. `ADD_STRENGTH_INCREMENT_AUTHORITY_PRODUCTION_READINESS = NOT_READY`
31. `INVESTMENT_PHILOSOPHY_ALIGNMENT = PASS_FOR_SHADOW_CONTRACT; NOT_READY_FOR_PRODUCTION`
32. `MODEL2_ENABLED = NO`
33. `FUTURE_OUTCOME_USED = NO`
34. `PRODUCTION_CHANGE_EXECUTED = NO`
35. `TARGET_RUN_MUTATED = NO`
36. `RUNTIME_STATE_MUTATED = NO`
37. `LONG_RUNTIME_EXECUTED = NO`
38. `NEXT_RECOMMENDED_STEP = REPAIR_OR_ENRICH_ADD_INVESTMENT_EVIDENCE_QUALITY_FOR_INCUMBENTS_BEFORE_PRODUCTION_PROMOTION; ESPECIALLY_INCREMENTAL_VALUE_AND_OPPORTUNITY_COST`
39. `FINAL_JUDGMENT = PHASE32_EC_ADD_STRENGTH_INCREMENT_TARGET_AUTHORITY_SHADOW_IMPLEMENTED_ONE_YEAR_BACKFILL_ACCEPTED_PRODUCTION_NOT_READY`

## Final Judgment

`PHASE32_EC_ADD_STRENGTH_INCREMENT_TARGET_AUTHORITY_SHADOW_IMPLEMENTED_ONE_YEAR_BACKFILL_ACCEPTED_PRODUCTION_NOT_READY`
