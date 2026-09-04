# Phase32-EE - Unified Next-Capital-Unit Evidence Symmetry SHADOW Design / One-Year Neutrality Audit

## Scope

EE implemented a SHADOW-only, Portfolio-Construction-owned next-capital-unit
evidence overlay. Production allocation, target weights, Position Sizing,
Runtime Planning, Candidate, PM, BQ, Entry, Risk Pacing, Cash policy, SELL /
REDUCE, and G129 were not changed.

Primary baseline:

- Source run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Prior EC analysis: `reports/runtime_tests/analysis/phase32_ec_add_strength_increment_shadow_20260903T000002`
- EE analysis output: `reports/runtime_tests/analysis/phase32_ee_unified_next_capital_unit_20260903T000003`
- Window: `2022-10-03` through `2023-10-26`
- Business days: `264`
- Future outcome / Historical PnL used for tuning: `NO`

EE did not execute fresh-run, resume, recover, replay, or long Historical.

## Implementation

Changed files:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `scripts/runtime_test.py`
- `tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py`
- `tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py`

Added SHADOW contract:

- `unified_next_capital_unit_evidence.v1`
- authority type: `UNIFIED_NEXT_CAPITAL_UNIT_SHADOW_AUTHORITY`
- contract id: `phase32_ee_unified_next_capital_unit_evidence.v1`
- owner: `PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY`
- `authoritative_consumer_count = 0`

Every competitor row now carries:

- raw PIT evidence: current weight, target weight, quantity, next executable
  quantity, lot notional, BQ/Entry, headroom, risk, ADD campaign evidence,
  REENTRY evidence, Cash optionality evidence.
- normalized comparison: completeness class, marginal investment value state,
  comparable opportunity-cost shadow, rank/winner where sufficient.

Action-specific semantics are preserved:

- BUY_NEW: opening new exposure.
- REENTRY: opening new exposure after prior EXIT, preserving context.
- BUY_ADD: increasing existing exposure with existing exposure/headroom cost.
- Cash: preserving optionality.

No fixed action bonus or penalty was introduced.

## One-Year Backfill

Command executed:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ee python3 scripts/runtime_test.py shadow-backfill-marginal-capital --source-run-id runtime-test-historical-extended-smoke-20260902T060955933565Z --start-date 2022-10-03 --end-date 2023-10-26 --output-root reports/runtime_tests/analysis/phase32_ee_unified_next_capital_unit_20260903T000003 --confirm --json
```

Result:

- status: `PASS`
- business_day_count: `264`
- production_change_executed: `false`
- target_run_mutated: `false`
- runtime_state_mutated: `false`

Manifest confirms:

- `analysis_only = true`
- `shadow_only = true`
- `source_run_artifact_mutated = false`
- `future_information_used = false`

## Core Counts

Competitor records:

| Type | Count |
| --- | ---: |
| BUY_NEW_NEXT_LOT | 2,483 |
| REENTRY_NEXT_LOT | 5,196 |
| BUY_ADD_NEXT_LOT | 152 |
| CASH_OPTIONALITY | 264 |

EE next-capital-unit completeness:

| Class | Count |
| --- | ---: |
| COMPLETE | 1,209 |
| PARTIAL | 1,468 |
| INSUFFICIENT | 4,601 |
| BLOCKED | 817 |

EE marginal-value states:

| State | Count |
| --- | ---: |
| POSITIVE | 946 |
| NEUTRAL | 264 |
| INSUFFICIENT | 6,068 |
| BLOCKED | 817 |

EE winner distribution:

| Winner | Days |
| --- | ---: |
| BUY_NEW_NEXT_LOT | 212 |
| REENTRY_NEXT_LOT | 37 |
| BUY_ADD_NEXT_LOT | 11 |
| CASH_OPTIONALITY | 3 |
| NONE | 1 |

Production vs EE:

- `AGREEMENT = 263`
- `Production Cash / EE NONE = 1`

This exactly preserves the current DW/EC Stage-B neutrality profile; EE improves
record symmetry without changing Production.

## ADD UNKNOWN Representation

ED baseline:

- ADD rows: `152`
- ADD `incremental_value=UNKNOWN`: `116`
- `NEW_BUY_SUPERIOR`: `84`
- ADD-UNKNOWN dates: `92`

EE classification of the 116 ADD UNKNOWN rows:

| EE representation | Count |
| --- | ---: |
| BLOCKED | 96 |
| REMAINS_INSUFFICIENT | 20 |
| BECOMES_COMPARABLE_POSITIVE | 0 |
| BECOMES_COMPARABLE_NEUTRAL | 0 |
| BECOMES_COMPARABLE_NEGATIVE | 0 |

Interpretation: existing contemporaneous evidence was sufficient to separate
hard blocks from unresolved evidence, but not sufficient to turn UNKNOWN ADD
incremental value into positive comparable ADD value. This preserves the
negative/weakening control and avoids manufacturing ADD demand.

## NEW_BUY_SUPERIOR 84 Reclassification

All 84 old `NEW_BUY_SUPERIOR + COMPARISON_INSUFFICIENT` ADD rows remain:

`STILL_INSUFFICIENT = 84`

No row became `ADD_SUPERIOR`, `GENUINELY_NEW_SUPERIOR`, or
`NO_CLEAR_WINNER` because the ADD side still lacks sufficient comparable
incremental-value evidence under the current PIT artifact set.

## 92-Day Neutral Comparison

EE materialized daily best records for all 92 ADD-UNKNOWN dates:

- best ADD
- best NEW
- best REENTRY
- Cash

The comparison now explicitly says when ADD is blocked or insufficient instead
of collapsing the result into ambiguous `NEW_BUY_SUPERIOR`. In these 92 cases,
the best ADD did not become a complete comparable positive next unit. NEW,
REENTRY, or Cash retained superiority only where their own evidence was complete
and executable; incomplete ADD evidence was not treated as economic inferiority.

## ADD Capitalization Impact

EE ADD impact:

- ADD UNKNOWN before: `116`
- ADD comparable after, across all ADD rows: `19`
- ADD remains insufficient or blocked: `133`
- ADD-comparably-superior rows: `0`
- complete + executable ADD-superior rows: `0`
- unique positive ADD campaigns: `6`
- repeated positive ADD campaigns: `3`

Positive ADD comparison campaigns:

| Campaign | Positive Days |
| --- | ---: |
| `94320|pc-7c5bd9294d48b016-94320-0001` | 7 |
| `94340|pc-c09afbf08095a527-94340-0001` | 4 |
| `94320|pc-401763653bc4df1d-94320-0001` | 2 |
| `83060|pc-090162015342d58a-83060-0001` | 1 |
| `54010|pc-0972f0d0a80bbd70-54010-0001` | 1 |
| `59550|pc-15bcec8077b3dc77-59550-0001` | 1 |

These are existing positive-control ADD paths, not newly rescued UNKNOWN rows.

## Controls

### 94320

- rows: `50`
- EE value: `POSITIVE=9`, `BLOCKED=40`, `INSUFFICIENT=1`
- known positive ADD dates remain comparable positive where complete and
  executable.
- UNKNOWN/blocked dates do not become positive by representation.

### Failed-Graduation Controls

| Symbol | Rows | EE Summary |
| --- | ---: | --- |
| 99840 | 26 | `BLOCKED=22`, `INSUFFICIENT=4`, no positive rescue |
| 94340 | 20 | `POSITIVE=4`, `BLOCKED=13`, `INSUFFICIENT=3` |
| 83060 | 15 | `POSITIVE=1`, `NEUTRAL=1`, `BLOCKED=12`, `INSUFFICIENT=1` |
| 40520 | 7 | `BLOCKED=6`, `INSUFFICIENT=1` |
| 43880 | 12 | `BLOCKED=9`, `INSUFFICIENT=3` |
| 54010 | 6 | `POSITIVE=1`, `BLOCKED=2`, `INSUFFICIENT=3` |

EE does not automatically rescue failed-graduation names.

### June-September 2023

June through September ADD rows: `20`

- `BLOCKED=16`
- `INSUFFICIENT=4`
- comparable opportunity cost: `COMPARISON_INSUFFICIENT=20`

The weak winner-graduation period remains unresolved by current evidence. EE
does not promote ADD during this period.

## Validation

Passed:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ee python3 -m pytest -q tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py
```

Result: `16 passed`

Passed:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ee python3 -m pytest -q tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase31_g63_runtime_executable_binding.py tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py
```

Result: `69 passed`

Passed:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ee python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/strategy/marginal_capital_value.py
```

Result: `PASS`

## Production Promotion Readiness

`EE_PRODUCTION_PROMOTION_READINESS = NOT_READY`

Reason:

- Comparison record symmetry improved.
- Legitimate negative/blocked ADD controls remain blocked.
- Current Production Stage-B behavior is preserved.
- But all 116 ADD UNKNOWN rows remain blocked or insufficient.
- All 84 old ambiguous NEW-superior rows remain insufficient.
- No complete executable ADD-superior row appears from the repaired
  representation.

Therefore EE is a good diagnostic contract but not a Production allocation
promotion basis.

## Required Final Answers

1. `CURRENT_PRODUCTION_CONTROL_PRESERVED = YES`
2. `UNIFIED_NEXT_CAPITAL_UNIT_RECORD = IMPLEMENTED_SHADOW_ONLY`
3. `ACTION_SPECIFIC_SEMANTICS_PRESERVED = PASS`
4. `COMMON_MARGINAL_COMPARISON_DIMENSIONS = IMPLEMENTED: opportunity strength, expected edge, continuation, rank, completeness, marginal value, opportunity cost, portfolio fit, risk cost, capital required, executable quantity/notional, BQ/Entry, headroom, lifecycle state`
5. `RAW_EVIDENCE_AND_NORMALIZED_VALUE_SEPARATED = PASS`
6. `CROSS_ACTION_EVIDENCE_COMPLETENESS_CONTRACT = PASS`
7. `ADD_UNKNOWN_SHADOW_REPRESENTATION = BLOCKED 96 / REMAINS_INSUFFICIENT 20 / POSITIVE 0 / NEUTRAL 0 / NEGATIVE 0`
8. `EXPECTED_EDGE_NEGATIVE_CONTROL_PRESERVED = PASS`
9. `COMPARABLE_OPPORTUNITY_COST_SHADOW = PASS`
10. `NEW_BUY_SUPERIOR_84_RECLASSIFICATION = STILL_INSUFFICIENT 84`
11. `ADD_UNKNOWN_92_DAY_NEUTRAL_COMPARISON = MATERIALIZED_FOR_92_DATES`
12. `ADD_FIXED_BONUS = NO`
13. `NEW_FIXED_BONUS = NO`
14. `REENTRY_FIXED_BONUS = NO`
15. `CASH_FIXED_BONUS = NO`
16. `MARGINAL_UNIT_COMPARABILITY_CONTRACT = PASS`
17. `INCUMBENT_EXISTING_EXPOSURE_COST_PRESERVED = PASS`
18. `NEW_STARTER_PORTFOLIO_COST_PRESERVED = PASS`
19. `REENTRY_CONTEXT_PRESERVED = PASS`
20. `CASH_OPTIONALITY_PRESERVED = PASS`
21. `DW_STAGE_A_STAGE_B_NEUTRALITY_INTEGRATION = PASS`
22. `94320_UNIFIED_MARGINAL_VALUE_CONTROL = POSITIVE 9 / BLOCKED 40 / INSUFFICIENT 1`
23. `FAILED_GRADUATION_UNIFIED_VALUE_CONTROLS = NOT_AUTOMATICALLY_RESCUED`
24. `2023_JUN_SEP_UNIFIED_MARGINAL_VALUE_RESULT = BLOCKED 16 / INSUFFICIENT 4 / ADD_SUPERIOR 0`
25. `ADD_MARGINAL_VALUE_PERSISTENCE_PROFILE = 6 positive campaigns, 3 repeated; strongest 94320 campaign positive on 7 days`
26. `EE_ONE_YEAR_SHADOW_BACKFILL_EXECUTED = YES`
27. `PRODUCTION_VS_EE_UNIFIED_COMPARISON = AGREEMENT 263 / Production Cash EE NONE 1`
28. `EE_ADD_CAPITALIZATION_IMPACT = ADD_UNKNOWN_BEFORE 116; ADD_COMPARABLE_AFTER_ALL_ADD_ROWS 19; ADD_REMAINS_INSUFFICIENT_OR_BLOCKED 133; ADD_SUPERIOR 0`
29. `EXPECTED_PORTFOLIO_STRUCTURE_DIRECTION = NEUTRAL_UNDER_CURRENT_EVIDENCE`
30. `CURRENT_GOOD_BEHAVIOR_PRESERVATION_COMPATIBLE = PASS`
31. `PHILOSOPHY_ALIGNMENT = PASS_AS_SHADOW_DIAGNOSTIC; next capital unit is compared across NEW/REENTRY/ADD/Cash while preserving action-specific lifecycle and risk semantics`
32. `EE_PRODUCTION_PROMOTION_READINESS = NOT_READY`
33. `FUTURE_OUTCOME_USED = NO`
34. `HISTORICAL_PNL_USED_FOR_TUNING = NO`
35. `PRODUCTION_CHANGE_EXECUTED = NO`
36. `TARGET_RUN_MUTATED = NO`
37. `RUNTIME_STATE_MUTATED = NO`
38. `LONG_RUNTIME_EXECUTED = NO`
39. `NEXT_RECOMMENDED_STEP = Investigate which PIT upstream evidence is missing for ADD incremental value/opportunity-cost sufficiency before any Production promotion`
40. `FINAL_JUDGMENT = PHASE32_EE_UNIFIED_NEXT_CAPITAL_UNIT_SHADOW_IMPLEMENTED_ONE_YEAR_NEUTRALITY_CONFIRMED_PRODUCTION_PROMOTION_NOT_READY`

