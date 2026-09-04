# Phase32-EJ — Winner Position-Size Adequacy / Positive Next-Lot Authority SHADOW Audit

## Scope

Phase32-EJ implemented and ran a SHADOW-only diagnostic contract:

`winner_position_size_adequacy_shadow.v1`

The diagnostic asks whether a held position is already adequately sized under current PIT evidence, or whether one more executable lot deserves further consideration. It does not authorize Production ADD, target weights, quantities, order planning, or runtime submission.

## Source / Evidence

- Source run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Window: 2022-10-03 through 2023-10-26
- Prior EH analysis: `reports/runtime_tests/analysis/phase32_eh_pc_security_opportunity_shadow_20260903T014000`
- EJ output: `reports/runtime_tests/analysis/phase32_ej_position_size_adequacy_20260903T020000`
- EJ source identity recorded by source run/EH context: `1f64f49ee9a8dd48280007e4df656e5f03e231ca`

The EJ backfill is isolated analysis output only. It reads source run artifacts and writes under `reports/runtime_tests/analysis/`.

## Contract

`winner_position_size_adequacy_shadow.v1` consumes existing PIT evidence:

- Security Opportunity evidence
- current position quantity / weight
- PM ADD / continuation context
- BQ / Entry
- Expected Edge
- headroom / risk
- lot feasibility / next executable lot
- NEW / REENTRY / Cash opportunity cost

Hard contract flags:

- `authoritative_consumer_count = 0`
- `production_allocation_consumer = false`
- `production_ordering_consumer = false`
- `production_sizing_consumer = false`
- `runtime_planning_consumer = false`
- `target_weight_authority = false`
- `quantity_authority = false`
- `action_authority = false`
- `fixed_add_preference = false`
- `production_target_weight_change = false`

## CURRENT_TARGET_USED_AS_CONTROL_NOT_LABEL

`PASS`

Current Production target remains visible as a control, but it is not used by itself as an adequacy label.

Backfill result:

- `target_equality_control_rows = 137`
- `target_equality_labeled_adequate_by_itself = 0`

This satisfies the central EJ requirement: `target_weight == current_weight` does not automatically mean `ADEQUATELY_SIZED`.

## POSITION_SIZE_ADEQUACY_CONTRACT

`phase32_ej_winner_position_size_adequacy_shadow.v1`

Classification states:

- `ADEQUATELY_SIZED`
- `POTENTIAL_UNDERCAPITALIZED`
- `WEAKENING_NO_ADD`
- `BQ_ENTRY_BLOCKED`
- `RISK_OR_HEADROOM_BLOCKED`
- `LOSES_TO_OTHER_CAPITAL_USE`
- `INSUFFICIENT`

Positive next-lot classification requires:

- complete Security Opportunity evidence;
- held position;
- strong current opportunity evidence;
- low/moderate exposure;
- headroom available;
- no BQ/Entry hard block;
- no-loss-averaging satisfied;
- no unresolved Expected Edge weakening;
- feasible next lot;
- opportunity cost competitive with NEW / REENTRY / Cash.

PM ADD alone is insufficient.

## One-Year Backfill

`EJ_ONE_YEAR_SHADOW_BACKFILL = PASS`

Summary:

| Metric | Value |
| --- | ---: |
| Business days | 264 |
| Diagnostic ADD rows | 152 |
| Authoritative consumers | 0 |
| Production change | false |
| Target run mutated | false |
| Runtime state mutated | false |
| Future information used | false |
| Historical outcome used | false |

Overall adequacy counts:

| Class | Count |
| --- | ---: |
| `BQ_ENTRY_BLOCKED` | 66 |
| `WEAKENING_NO_ADD` | 46 |
| `LOSES_TO_OTHER_CAPITAL_USE` | 22 |
| `POTENTIAL_UNDERCAPITALIZED` | 11 |
| `RISK_OR_HEADROOM_BLOCKED` | 5 |
| `ADEQUATELY_SIZED` | 2 |

## EI_116_POSITION_SIZE_ADEQUACY_RECLASSIFICATION

The original EI/EH ADD UNKNOWN 116 rows were reclassified as:

| Class | Count |
| --- | ---: |
| `BQ_ENTRY_BLOCKED` | 53 |
| `WEAKENING_NO_ADD` | 46 |
| `LOSES_TO_OTHER_CAPITAL_USE` | 16 |
| `RISK_OR_HEADROOM_BLOCKED` | 1 |
| `POTENTIAL_UNDERCAPITALIZED` | 0 |

Interpretation:

The EI 116 are not clean undercapitalized cases under the EJ positive next-lot contract. Once current target equality is removed as an adequacy label, they still fail positive next-lot requirements because of BQ/Entry blocks, Expected Edge weakening, other capital-use superiority, or risk/headroom block.

## LOW_MID_EXPOSURE_50_PROFILE

The 50 low/mid exposure EI rows were reclassified as:

| Class | Count |
| --- | ---: |
| `WEAKENING_NO_ADD` | 24 |
| `BQ_ENTRY_BLOCKED` | 20 |
| `LOSES_TO_OTHER_CAPITAL_USE` | 6 |
| `POTENTIAL_UNDERCAPITALIZED` | 0 |

Even below 6% current weight, the EI population does not produce a clean positive next-lot case.

## 94320_POSITION_SIZE_ADEQUACY_CONTROL

94320 total ADD diagnostic rows:

| Class | Count |
| --- | ---: |
| `BQ_ENTRY_BLOCKED` | 27 |
| `WEAKENING_NO_ADD` | 13 |
| `POTENTIAL_UNDERCAPITALIZED` | 5 |
| `LOSES_TO_OTHER_CAPITAL_USE` | 5 |

94320 EI ADD UNKNOWN rows:

- 33 rows
- no `POTENTIAL_UNDERCAPITALIZED` rows inside the EI 116 population

94320 potential rows outside the EI unknown subset:

| Date | Campaign | Current weight | Target weight | Next qty | BQ | Entry |
| --- | --- | ---: | ---: | ---: | --- | --- |
| 2022-11-01 | `pc-401763653bc4df1d-94320-0001` | 3.1% | 4.6% | 200 | `REDUCED_ALLOCATION_ONLY` | `ADD_REDUCED_ONLY` |
| 2023-02-13 | `pc-7c5bd9294d48b016-94320-0001` | 3.7% | 4.9% | 200 | `REDUCED_ALLOCATION_ONLY` | `ADD_REDUCED_ONLY` |
| 2023-02-22 | `pc-7c5bd9294d48b016-94320-0001` | 5.3% | 6.6% | 300 | `FULL_ALLOCATION_ELIGIBLE` | `ADD_REDUCED_ONLY` |
| 2023-02-24 | `pc-7c5bd9294d48b016-94320-0001` | 6.6% | 7.9% | 200 | `REDUCED_ALLOCATION_ONLY` | `ADD_REDUCED_ONLY` |
| 2023-03-15 | `pc-7c5bd9294d48b016-94320-0001` | 7.8% | 9.1% | 200 | `REDUCED_ALLOCATION_ONLY` | `ADD_REDUCED_ONLY` |

94320 therefore confirms two facts at once:

1. EI UNKNOWN suppression is explained by legitimate negative/blocking evidence.
2. Outside EI UNKNOWN, repeated current-PIT potential undercapitalization cases exist and deserve a later SHADOW design/acceptance step.

## WINNER_POSITION_SIZE_CONTROL_SET

| Symbol | Rows | EI rows | Class profile |
| --- | ---: | ---: | --- |
| 94320 | 50 | 33 | 27 BQ/Entry blocked, 13 weakening, 5 potential, 5 loses to other capital |
| 94340 | 20 | 16 | 7 weakening, 6 BQ/Entry blocked, 4 potential, 3 loses to other capital |
| 99840 | 26 | 15 | 14 BQ/Entry blocked, 4 weakening, 4 risk/headroom blocked, 2 adequate, 2 loses |
| 83060 | 15 | 13 | 6 BQ/Entry blocked, 6 weakening, 3 loses |
| 43880 | 12 | 12 | 7 weakening, 3 BQ/Entry blocked, 2 loses |
| 54010 | 6 | 5 | 3 loses, 1 potential, 1 BQ/Entry blocked, 1 weakening |

No symbol-specific rule was introduced.

## 2023_JUN_SEP_POSITION_SIZE_ADEQUACY_PROFILE

Jun-Sep EI rows:

| Class | Count |
| --- | ---: |
| `BQ_ENTRY_BLOCKED` | 12 |
| `LOSES_TO_OTHER_CAPITAL_USE` | 2 |
| `WEAKENING_NO_ADD` | 2 |
| `POTENTIAL_UNDERCAPITALIZED` | 0 |

The weak-graduation period does not show clean positive next-lot evidence inside the EI unknown set. Suppression is mostly BQ/Entry, then edge/competition.

## NEXT_LOT_ACTION_NEUTRAL_COMPETITION

`PASS`

The EJ diagnostic does not add a NEW penalty or ADD bonus. Potential ADD lots must be competitive against NEW / REENTRY / Cash and must satisfy feasible next-lot requirements.

## POTENTIAL_UNDERCAPITALIZED_COUNT

`11`

These 11 are across the full one-year ADD diagnostic population, not inside the EI 116 ADD UNKNOWN population.

Potential rows:

| Date | Symbol | Campaign | Current weight | Target weight | Next qty |
| --- | --- | --- | ---: | ---: | ---: |
| 2022-10-06 | 94340 | `pc-c09afbf08095a527-94340-0001` | 2.8% | 4.1% | 200 |
| 2022-10-11 | 94340 | `pc-c09afbf08095a527-94340-0001` | 4.1% | 5.5% | 200 |
| 2022-10-12 | 94340 | `pc-c09afbf08095a527-94340-0001` | 4.2% | 5.6% | 100 |
| 2022-10-13 | 94340 | `pc-c09afbf08095a527-94340-0001` | 5.7% | 7.1% | 100 |
| 2022-11-01 | 94320 | `pc-401763653bc4df1d-94320-0001` | 3.1% | 4.6% | 200 |
| 2023-02-13 | 94320 | `pc-7c5bd9294d48b016-94320-0001` | 3.7% | 4.9% | 200 |
| 2023-02-15 | 54010 | `pc-0972f0d0a80bbd70-54010-0001` | 4.7% | 9.4% | 100 |
| 2023-02-22 | 94320 | `pc-7c5bd9294d48b016-94320-0001` | 5.3% | 6.6% | 300 |
| 2023-02-24 | 94320 | `pc-7c5bd9294d48b016-94320-0001` | 6.6% | 7.9% | 200 |
| 2023-03-15 | 94320 | `pc-7c5bd9294d48b016-94320-0001` | 7.8% | 9.1% | 200 |
| 2023-05-31 | 59550 | `pc-15bcec8077b3dc77-59550-0001` | 3.7% | 4.5% | 300 |

## POTENTIAL_UNDERCAPITALIZED_CAMPAIGNS

| Campaign | Rows |
| --- | ---: |
| `94340|pc-c09afbf08095a527-94340-0001` | 4 |
| `94320|pc-7c5bd9294d48b016-94320-0001` | 4 |
| `94320|pc-401763653bc4df1d-94320-0001` | 1 |
| `54010|pc-0972f0d0a80bbd70-54010-0001` | 1 |
| `59550|pc-15bcec8077b3dc77-59550-0001` | 1 |

## REPEATED_UNDERCAPITALIZED_CAMPAIGNS

| Campaign | Rows |
| --- | ---: |
| `94340|pc-c09afbf08095a527-94340-0001` | 4 |
| `94320|pc-7c5bd9294d48b016-94320-0001` | 4 |

This is material enough to justify a next SHADOW acceptance/design phase, but not enough for direct Production promotion in EJ.

## Production Preservation

`CURRENT_PRODUCTION_PRESERVATION = PASS`

Preserved:

- BUY_NEW equivalence
- REENTRY equivalence
- Candidate ranking
- PM / SELL / REDUCE behavior
- BQ / Entry
- Risk Pacing
- Cash
- concentration/caps
- lot-aware sizing
- G129 BUY_ADD semantics
- Runtime mapper-only behavior

No Production path consumes the EJ artifact.

## Validation

Focused tests:

- `PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ej-tests python3 -m pytest -q tests/strategy/test_phase32_ej_winner_position_size_adequacy_shadow.py tests/runtime_v2/test_phase32_ej_position_size_adequacy_backfill.py`
- Result: `5 passed`

EG/EH/EJ adjacency:

- `PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ej-tests python3 -m pytest -q tests/strategy/test_phase32_eg_security_opportunity_evidence.py tests/runtime_v2/test_phase32_eg_security_opportunity_backfill.py tests/strategy/test_phase32_eh_pc_security_opportunity_shadow_consumer.py tests/runtime_v2/test_phase32_eh_pc_security_opportunity_backfill.py tests/strategy/test_phase32_ej_winner_position_size_adequacy_shadow.py tests/runtime_v2/test_phase32_ej_position_size_adequacy_backfill.py`
- Result: `15 passed`

ADD / G129 / DQ / AX-AA-AE adjacent focused regression:

- `PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ej-tests python3 -m pytest -q tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py tests/strategy/test_phase31_g117_normal_buy_scope_repair.py tests/runtime_v2/test_phase31_a5_executable_membership_guard.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase32_ae_partial_submit_finalization_dry_run_is_read_only tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase32_ae_partial_submit_finalization_executes_preserved_order_once`
- Result: `55 passed`

Compile:

- `PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ej-tests python3 -m py_compile src/ai_fund_lab_v2/strategy/marginal_capital_value.py scripts/runtime_test.py`
- Result: `PASS`

Backfill:

- `PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ej-backfill python3 scripts/runtime_test.py shadow-backfill-position-size-adequacy --source-run-id runtime-test-historical-extended-smoke-20260902T060955933565Z --start-date 2022-10-03 --end-date 2023-10-26 --output-root reports/runtime_tests/analysis/phase32_ej_position_size_adequacy_20260903T020000 --confirm --json`
- Result: `PASS`

## Files Changed

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `scripts/runtime_test.py`
- `tests/strategy/test_phase32_ej_winner_position_size_adequacy_shadow.py`
- `tests/runtime_v2/test_phase32_ej_position_size_adequacy_backfill.py`
- `docs/phase_reports/phase32_ej_winner_position_size_adequacy_positive_next_lot_shadow_audit.md`

Analysis artifact created:

- `reports/runtime_tests/analysis/phase32_ej_position_size_adequacy_20260903T020000`

## Required Final Answers

- `CURRENT_TARGET_USED_AS_CONTROL_NOT_LABEL`: `PASS`
- `POSITION_SIZE_ADEQUACY_CONTRACT`: `winner_position_size_adequacy_shadow.v1`
- `FIXED_ADD_PREFERENCE`: `NO`
- `EI_NEGATIVE_CONTROLS_PRESERVED`: `PASS`
- `EI_116_POSITION_SIZE_ADEQUACY_RECLASSIFICATION`: 53 `BQ_ENTRY_BLOCKED`, 46 `WEAKENING_NO_ADD`, 16 `LOSES_TO_OTHER_CAPITAL_USE`, 1 `RISK_OR_HEADROOM_BLOCKED`, 0 `POTENTIAL_UNDERCAPITALIZED`
- `LOW_MID_EXPOSURE_50_PROFILE`: 24 `WEAKENING_NO_ADD`, 20 `BQ_ENTRY_BLOCKED`, 6 `LOSES_TO_OTHER_CAPITAL_USE`, 0 `POTENTIAL_UNDERCAPITALIZED`
- `94320_POSITION_SIZE_ADEQUACY_CONTROL`: 50 diagnostic rows; 5 potential outside EI unknown; EI unknown remains no-potential.
- `WINNER_POSITION_SIZE_CONTROL_SET`: completed for 94320 / 94340 / 99840 / 83060 / 43880 / 54010.
- `2023_JUN_SEP_POSITION_SIZE_ADEQUACY_PROFILE`: 12 BQ/Entry blocked, 2 loses, 2 weakening, 0 potential.
- `NEXT_LOT_ACTION_NEUTRAL_COMPETITION`: `PASS`
- `POTENTIAL_UNDERCAPITALIZED_COUNT`: `11`
- `POTENTIAL_UNDERCAPITALIZED_CAMPAIGNS`: 5 unique campaigns.
- `REPEATED_UNDERCAPITALIZED_CAMPAIGNS`: `94340|pc-c09afbf08095a527-94340-0001`, `94320|pc-7c5bd9294d48b016-94320-0001`
- `PRODUCTION_TARGET_WEIGHT_CHANGE`: `NO`
- `EJ_ONE_YEAR_SHADOW_BACKFILL`: `PASS`
- `CURRENT_PRODUCTION_PRESERVATION`: `PASS`
- `EJ_SHADOW_FAILURE_ISOLATION`: `PASS`
- `PRODUCTION_CHANGE_EXECUTED`: `NO`
- `TARGET_RUN_MUTATED`: `NO`
- `RUNTIME_STATE_MUTATED`: `NO`
- `LONG_RUNTIME_EXECUTED`: `NO`
- `FUTURE_OUTCOME_USED`: `NO`
- `HISTORICAL_PNL_USED_FOR_TUNING`: `NO`
- `NEXT_RECOMMENDED_STEP`: Run a follow-up SHADOW acceptance/design phase focused only on the 11 potential undercapitalized rows and the 2 repeated campaigns, to decide whether explicit positive ADD increment authority is stable enough for a later Production proposal.

## Final Judgment

`PHASE32_EJ_WINNER_POSITION_SIZE_ADEQUACY_SHADOW_ACCEPTED_EI_116_NO_CLEAN_UNDERCAPITALIZED_FULL_ADD_DIAGNOSTIC_FINDS_11_POTENTIAL_CASES_NO_PRODUCTION_CHANGE`
