# Phase32-DT — One-Year DQ SHADOW Isolated Historical PIT Backfill Implementation

## Scope

- Source run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Backfill window: `2022-10-03` through `2023-10-26`
- Output root: `reports/runtime_tests/analysis/phase32_dt_dq_shadow_backfill_20260903`
- Backfill type: isolated analysis only
- Production Strategy rerun: NO
- Full modern Portfolio Construction recompute: NO
- Runtime state mutation: NO
- Source run artifact mutation: NO
- Fresh-run/resume/recover/replay executed: NO
- DQ Production promotion executed: NO

Mandatory references read:

- `docs/phase_reports/phase32_ds_historical_pit_dq_shadow_backfill_feasibility_read_only_audit.md`
- `docs/phase_reports/phase32_dq_unified_marginal_capital_authority_shadow_implementation.md`
- `docs/phase_reports/phase32_dp_winner_capitalization_unified_marginal_capital_allocation_deep_dive_shadow_audit.md`
- `docs/phase_reports/phase32_dr_production_vs_unified_marginal_capital_shadow_divergence_read_only_audit.md`
- current DQ evaluator source
- Runtime Test command architecture and command guide

## Implementation

Added a dedicated Runtime Test analysis command:

```text
shadow-backfill-marginal-capital
```

Required arguments:

- `--source-run-id`
- `--start-date`
- `--end-date`
- `--output-root`

Supported:

- `--dry-run`
- `--confirm`
- `--json`
- `--evidence-root`

Changed files:

- `scripts/runtime_test.py`
- `docs/03_operations/runtime_test_command_guide.md`
- `tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py`
- `docs/phase_reports/phase32_dt_one_year_dq_shadow_isolated_historical_pit_backfill.md`

The command is dispatched before profile/runtime-root validation, so it does not read live `.runtime` state through the usual Runtime Test environment path.

## Backfill Contract

For each date, the command reads only:

```text
reports/runtime_tests/runs/<source_run_id>/daily/<date>/strategy/portfolio_construction.json
```

It consumes stored original PIT materialization:

- `portfolio_members`
- `capital_competition.competitors`
- `capital_competition.canonical_cash_competitor_evidence`
- `capital_competition.market_candidate_cash_interaction`
- `capital_competition.risk_pacing_evidence`
- `incremental_budget_reconciliation`
- `business_date`

It then calls only:

```text
ai_fund_lab_v2.strategy.marginal_capital_value.build_unified_marginal_capital_shadow(...)
```

It does not invoke full Portfolio Construction and does not recompute Candidate, Opportunity, BQ, Entry, SI, PM, REENTRY, portfolio snapshot, or risk producers.

Fail-closed checks were added for:

- missing source run
- invalid date range
- missing PC artifact
- PC `business_date` mismatch
- missing `portfolio_members`
- missing `capital_competition`
- missing `competitors`
- missing canonical cash evidence
- missing market-candidate cash interaction
- missing risk pacing evidence
- output root outside `reports/runtime_tests/analysis`
- output root inside source run or `.runtime`
- non-empty actual output root
- missing `--confirm` for artifact creation

## Output

Materialized output:

```text
reports/runtime_tests/analysis/phase32_dt_dq_shadow_backfill_20260903/
  manifest.json
  summary.json
  daily/<date>/unified_marginal_capital_shadow.json
  daily/<date>/input_hashes.json
```

File count:

- 264 daily SHADOW artifacts
- 264 daily input hash artifacts
- `manifest.json`
- `summary.json`
- total files: 530

Every daily artifact records:

- original source run id
- original source baseline identity
- original daily PC artifact path/hash
- original PC schema/producer/hash
- original PC source hashes and upstream artifact summary
- current DQ evaluator schema/contract/source file hashes/git head
- `analysis_only=true`
- `shadow_only=true`
- `full_pc_recompute_executed=false`
- `live_runtime_state_used=false`
- `upstream_historical_producers_recomputed=false`
- `future_information_used=false`
- original Production decision preserved

`DUAL_PROVENANCE_RECORDED = PASS`

## Coverage Reconciliation

DS estimate vs DT actual:

| Metric | DS estimate | DT actual | Reconciliation |
|---|---:|---:|---|
| Business days | 264 | 264 | MATCH |
| `BUY_NEW_NEXT_LOT` | 2,483 | 2,483 | MATCH |
| `REENTRY_NEXT_LOT` | 5,196 | 5,196 | MATCH |
| `BUY_ADD_NEXT_LOT` | 152 | 152 | MATCH |
| `CASH_OPTIONALITY` | 264 | 264 | MATCH |
| ADD days | approx. 113 | 113 | MATCH |

`BACKFILL_COVERAGE_RECONCILIATION = PASS; DS_ESTIMATES_MATCH_DT_ACTUAL`

## Regime Coverage

| Trend regime | Days |
|---|---:|
| `BULL` | 111 |
| `RECOVERY` | 46 |
| `RANGE` | 46 |
| `BEAR` | 45 |
| `CORRECTION` | 16 |

`REGIME_COVERAGE_COMPLETE = PASS`

## Divergence Summary

| Divergence class | Count |
|---|---:|
| `AGREEMENT` | 76 |
| `Production NEW_OR_REENTRY / SHADOW Cash` | 85 |
| `Production NEW_OR_REENTRY / SHADOW REENTRY` | 50 |
| `Production NEW_OR_REENTRY / SHADOW ADD` | 22 |
| `Production NEW_OR_REENTRY / SHADOW NEW` | 15 |
| `Production ADD / SHADOW Cash` | 8 |
| `Production ADD / SHADOW REENTRY` | 3 |
| `Production Cash / SHADOW REENTRY` | 3 |
| `Production ADD / SHADOW NEW` | 1 |
| `Production ADD / SHADOW ADD` | 1 |

Aggregate:

- agreement sets: 76
- divergent sets: 188
- total sets: 264

`ONE_YEAR_DIVERGENCE_SUMMARY = MATERIALIZED`

DT intentionally does not decide Production promotion or final neutrality. That belongs to the next READ-ONLY audit over this materialized evidence.

## ADD Value / Feasibility

| ADD bucket | Count |
|---|---:|
| `LOW_VALUE + COMPLETE + INFEASIBLE_DUE_TO_LOT + BLOCKED_BY_CONCENTRATION` | 77 |
| `HIGH_VALUE_EVIDENCE_INCOMPLETE + INCOMPLETE + INFEASIBLE_DUE_TO_LOT + BLOCKED_BY_CONCENTRATION` | 40 |
| `MEDIUM_VALUE + COMPLETE + FEASIBLE + BLOCKED_BY_CONCENTRATION` | 19 |
| `MEDIUM_VALUE + COMPLETE + INFEASIBLE_DUE_TO_LOT + BLOCKED_BY_CONCENTRATION` | 11 |
| `LOW_VALUE + COMPLETE + FEASIBLE + BLOCKED_BY_CONCENTRATION` | 5 |

Identity and evidence integrity:

- `add_identity_missing_count = 0`
- `value_feasibility_missing_count = 0`

`ONE_YEAR_ADD_VALUE_FEASIBILITY_SUMMARY = MATERIALIZED`

`ADD_BACKFILL_IDENTITY_COMPLETE = PASS`

`VALUE_FEASIBILITY_SEPARATION_PRESERVED = PASS`

## Strong ADD Displacement Inventory

The isolated backfill summary materialized 22 cases where SHADOW winner is `BUY_ADD_NEXT_LOT` and original Production did not fund ADD as the winning family.

First observed examples:

| Date | SHADOW ADD symbol | Campaign | Desirability | Feasibility | Divergence |
|---|---|---|---|---|---|
| `2022-11-02` | `99840` | `pc-5a5765b1c257b5b8-99840-0001` | `HIGH_VALUE_EVIDENCE_INCOMPLETE` | `INFEASIBLE_DUE_TO_LOT` | `Production NEW_OR_REENTRY / SHADOW ADD` |
| `2022-11-07` | `99840` | `pc-5a5765b1c257b5b8-99840-0001` | `HIGH_VALUE_EVIDENCE_INCOMPLETE` | `INFEASIBLE_DUE_TO_LOT` | `Production NEW_OR_REENTRY / SHADOW ADD` |
| `2022-11-28` | `45940` | `pc-d849118022b497c9-45940-0001` | `HIGH_VALUE_EVIDENCE_INCOMPLETE` | `INFEASIBLE_DUE_TO_LOT` | `Production NEW_OR_REENTRY / SHADOW ADD` |
| `2022-11-30` | `45940` | `pc-d849118022b497c9-45940-0001` | `HIGH_VALUE_EVIDENCE_INCOMPLETE` | `INFEASIBLE_DUE_TO_LOT` | `Production NEW_OR_REENTRY / SHADOW ADD` |
| `2022-12-22` | `45410` | `pc-97e69ccc8e91da3a-45410-0001` | `HIGH_VALUE_EVIDENCE_INCOMPLETE` | `INFEASIBLE_DUE_TO_LOT` | `Production NEW_OR_REENTRY / SHADOW ADD` |

`STRONG_ADD_DISPLACEMENT_INVENTORY = MATERIALIZED; 22_CASES`

Important: these are decision-time SHADOW inventory rows only. DT does not use subsequent returns to decide whether any case was economically better.

## NEW vs ADD Neutrality

The summary materialized 22 dates where NEW and feasible ADD evidence coexisted enough for neutrality inspection. The detailed date-level records are in:

```text
reports/runtime_tests/analysis/phase32_dt_dq_shadow_backfill_20260903/summary.json::new_vs_add_neutrality_cases
```

`NEW_VS_ADD_NEUTRALITY_SUMMARY = MATERIALIZED; 22_CASES`

DT does not perform the final neutrality judgment.

## BEAR / BULL / RECOVERY

The backfill includes all target regimes:

- BEAR: 45 days
- BULL: 111 days
- RECOVERY: 46 days

Regime-specific ADD-vs-NEW/Cash summaries are materialized through:

```text
summary.json::regime_counts
summary.json::regime_divergence_counts
daily/<date>/unified_marginal_capital_shadow.json::regime_context
```

`BEAR_ADD_VS_NEW_CASH_SUMMARY = MATERIALIZED_FOR_NEXT_READ_ONLY_AUDIT`

`BULL_RECOVERY_ADD_VS_NEW_SUMMARY = MATERIALIZED_FOR_NEXT_READ_ONLY_AUDIT`

## Campaign Graduation

Backfill found:

- campaigns with ADD SHADOW rows: 17
- repeated ADD SHADOW campaigns: 14

Top repeated campaigns:

| Campaign | ADD SHADOW rows | Production ADD selected rows |
|---|---:|---:|
| `94320 / pc-7c5bd9294d48b016-94320-0001` | 35 | 6 |
| `99840 / pc-5a5765b1c257b5b8-99840-0001` | 18 | 0 |
| `94320 / pc-401763653bc4df1d-94320-0001` | 15 | 1 |
| `94340 / pc-8d0b3d71adb1e835-94340-0001` | 14 | 0 |
| `83060 / pc-090162015342d58a-83060-0001` | 12 | 0 |

`ONE_YEAR_CAMPAIGN_GRADUATION_SHADOW_SUMMARY = MATERIALIZED`

## Controls

### 94320 Positive Control

Backfill controls:

| Date | Result |
|---|---|
| `2023-02-13` | 25 competitors; `BUY_ADD_NEXT_LOT=1`; ADD `94320` preserves campaign/PM evidence |
| `2023-03-15` | 38 competitors; `BUY_ADD_NEXT_LOT=1`; ADD `94320` preserves campaign/PM evidence |

`94320_BACKFILL_CONTROL = PASS`

### Determinism

Executed the same one-day backfill twice for `2023-02-13` into separate isolated output roots:

- `reports/runtime_tests/analysis/phase32_dt_determinism_a`
- `reports/runtime_tests/analysis/phase32_dt_determinism_b`

Both produced identical hashes:

- `backfill_daily_hash = 27e7149ebf01e9908d95fe522f08ebcaa5736a33759ee4b4f647014b822511c3`
- `shadow_authority_hash = d22185ecf110a1292c723c958d3e96290b2fe340a7b9e4e0b0a294bfcf704773`

`BACKFILL_DETERMINISM = PASS`

### Native DQ Controls

Dry-run command over native DQ dates `2023-11-13` through `2023-11-14` passed.

Control hashes:

- `2023-11-13`: `bc5c0f178d7f501aaaa1da0971bdcfb4b80897046dc0c272e1a1df39bbf5d6f3`
- `2023-11-14`: `f8c1dc2378bc3b67916e9fdfe468b5108adf75ddd2d34622e8209c94e54e8a24`

These match the native DQ artifact hashes previously inspected in DS/DR. `2023-11-10` remains a source-version-note partial control because early native DQ classification included `REENTRY_NOT_APPLICABLE` continuation-like rows that current corrected DQ excludes.

`NATIVE_DQ_CONTROL_STATUS = PASS_FOR_2023-11-13_AND_2023-11-14; 2023-11-10_PARTIAL_BY_KNOWN_CLASSIFICATION_GENERATION_DRIFT`

## Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-dt-tests PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py
```

Result:

```text
5 passed in 12.54s
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-dt PYTHONPATH=src python3 -m py_compile scripts/runtime_test.py
```

Result: PASS

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-dt-tests PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py
```

Result:

```text
8 passed in 10.82s
```

Backfill commands:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-dt PYTHONPATH=src python3 scripts/runtime_test.py shadow-backfill-marginal-capital --source-run-id runtime-test-historical-extended-smoke-20260902T060955933565Z --start-date 2022-10-03 --end-date 2023-10-26 --output-root reports/runtime_tests/analysis/phase32_dt_dq_shadow_backfill_20260903 --dry-run --json
```

Result: PASS, 264 business days, no output files.

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-dt PYTHONPATH=src python3 scripts/runtime_test.py shadow-backfill-marginal-capital --source-run-id runtime-test-historical-extended-smoke-20260902T060955933565Z --start-date 2022-10-03 --end-date 2023-10-26 --output-root reports/runtime_tests/analysis/phase32_dt_dq_shadow_backfill_20260903 --confirm --json
```

Result: PASS, 264 business days, isolated analysis output materialized.

No fresh-run, resume, recover, replay, or long Historical trading simulation was executed.

## Required Final Answers

1. `BACKFILL_COMMAND_IMPLEMENTED = YES`
2. `FULL_PC_RECOMPUTE_EXECUTED = NO`
3. `LIVE_RUNTIME_STATE_USED = NO`
4. `UPSTREAM_HISTORICAL_PRODUCERS_RECOMPUTED = NO`
5. `DUAL_PROVENANCE_RECORDED = PASS`
6. `SOURCE_RUN_ARTIFACT_MUTATED = NO`
7. `ACTION_CLASSIFICATION_INTEGRITY = PASS`
8. `ADD_BACKFILL_IDENTITY_COMPLETE = PASS`
9. `VALUE_FEASIBILITY_SEPARATION_PRESERVED = PASS`
10. `PRODUCTION_SHADOW_COMPARISON_MATERIALIZED = PASS`
11. `ONE_YEAR_BACKFILL_EXECUTED = YES`
12. `BACKFILL_COVERAGE_RECONCILIATION = PASS; DS_ESTIMATES_MATCH_DT_ACTUAL`
13. `REGIME_COVERAGE_COMPLETE = PASS`
14. `ONE_YEAR_DIVERGENCE_SUMMARY = MATERIALIZED`
15. `ONE_YEAR_ADD_VALUE_FEASIBILITY_SUMMARY = MATERIALIZED`
16. `STRONG_ADD_DISPLACEMENT_INVENTORY = MATERIALIZED; 22_CASES`
17. `NEW_VS_ADD_NEUTRALITY_SUMMARY = MATERIALIZED; 22_CASES`
18. `BEAR_ADD_VS_NEW_CASH_SUMMARY = MATERIALIZED_FOR_NEXT_READ_ONLY_AUDIT`
19. `BULL_RECOVERY_ADD_VS_NEW_SUMMARY = MATERIALIZED_FOR_NEXT_READ_ONLY_AUDIT`
20. `ONE_YEAR_CAMPAIGN_GRADUATION_SHADOW_SUMMARY = MATERIALIZED`
21. `94320_BACKFILL_CONTROL = PASS`
22. `BACKFILL_DETERMINISM = PASS`
23. `NATIVE_DQ_CONTROL_STATUS = PASS_FOR_2023-11-13_AND_2023-11-14; 2023-11-10_PARTIAL_BY_KNOWN_CLASSIFICATION_GENERATION_DRIFT`
24. `FUTURE_INFORMATION_USED = NO`
25. `PRODUCTION_CHANGE_EXECUTED = NO`
26. `TARGET_RUN_MUTATED = NO`
27. `RUNTIME_STATE_MUTATED = NO`
28. `DQ_PRODUCTION_PROMOTION_EXECUTED = NO`
29. `NEXT_RECOMMENDED_STEP = PHASE32-DU_READ_ONLY_ONE_YEAR_DQ_SHADOW_NEUTRALITY_AND_CAPITAL_ALLOCATION_AUDIT_USING_reports/runtime_tests/analysis/phase32_dt_dq_shadow_backfill_20260903`
30. `FINAL_JUDGMENT = PHASE32_DT_ONE_YEAR_DQ_SHADOW_ISOLATED_BACKFILL_MATERIALIZED_READY_FOR_READ_ONLY_NEUTRALITY_AUDIT`

## Final Judgment

`PHASE32_DT_ONE_YEAR_DQ_SHADOW_ISOLATED_BACKFILL_MATERIALIZED_READY_FOR_READ_ONLY_NEUTRALITY_AUDIT`

DT implemented the DS-approved isolated analysis path and materialized a one-year DQ SHADOW backfill over immutable historical PC PIT artifacts. The output is sufficient for the next READ-ONLY neutrality/capital-allocation audit. No Production behavior was changed or promoted.
