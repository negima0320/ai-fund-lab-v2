# Phase32-FB — Post-EZ Extended Actual-Path Semantic / Capital Allocation Acceptance Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Audited completed period: `2022-10-03` through `2022-12-16`
- Run status at read time: `RUNNING`
- Next job at read time: `2022-12-19:market_refresh`
- Completed business days audited: `52`
- Production changed: NO
- SHADOW changed: NO
- Source/config/schema changed: NO
- Target run mutated: NO
- Runtime/Pending/Ledger mutated: NO
- Fresh-run/resume/replay/recover executed: NO
- Future outcome used for Production judgment: NO

This is a correctness / Architecture acceptance audit, not a performance evaluation. Historical PnL or later returns were not used as a Production repair, threshold, weight, ranking, or parameter basis.

## Evidence Sources

- `docs/phase_reports/phase32_fa_ez_first_legitimate_divergence_recent_exit_guard_expiry_actual_path_acceptance_audit.md`
- `docs/phase_reports/phase32_ez_bounded_recent_exit_guard_materialization_connectivity_repair.md`
- `docs/phase_reports/phase32_ew_reentry_current_decision_semantic_removal_recent_exit_guard_implementation.md`
- `docs/phase_reports/phase32_eu_reentry_recent_exit_guard_replacement_architecture_design.md`
- `docs/phase_reports/phase32_ev_reentry_legacy_data_retention_runtime_state_minimization_audit.md`
- Current run daily artifacts under `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260903T213011268067Z/daily/`
- Relevant source:
  - `src/ai_fund_lab_v2/runtime_v2/recent_exit_guard.py`
  - `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
  - `src/ai_fund_lab_v2/strategy/portfolio_construction.py`

Architecture principle applied:

```text
HISTORY RETENTION != CURRENT DECISION AUTHORITY
AUDITABILITY != DAILY RUNTIME DUPLICATION
```

## 1. Extended Guard Lifecycle Audit

Across completed actual artifacts through `2022-12-16`:

| Metric | Count |
|---|---:|
| full EXIT executions requiring guard materialization (`SELL_EXIT` / `EXIT`) | 78 |
| missing guard materializations | 0 |
| recent-exit guard rows observed in execution materialization artifacts | 287 |
| stale/cross-run guard rows | 0 |
| active guard PC members | 141 |
| expired guard PC members | 42 |
| immediate BUY fills inside active guard window without guard | 0 |
| non-PASS CLI results in audited completed days | 0 |

The guard index remains compact and run-scoped. The largest observed `recent_exit_guard_materialization.json` was about `20KB` on `2022-11-02`; later files usually carried only a handful of rows. Recent artifacts show bounded emit/retain/expire behavior, for example:

| Date | emitted | retained | expired | rows |
|---|---:|---:|---:|---:|
| 2022-12-05 | 3 | 2 | 0 | 5 |
| 2022-12-07 | 3 | 5 | 2 | 8 |
| 2022-12-09 | 1 | 7 | 3 | 8 |
| 2022-12-13 | 1 | 5 | 3 | 6 |
| 2022-12-16 | 1 | 3 | 2 | 4 |

No evidence was found for:

- missing materialization,
- stale guard lineage,
- cross-run lineage,
- expiry failure,
- expired guard suppressing current decision via old history,
- guardless immediate churn.

`EXTENDED_GUARD_LIFECYCLE_CORRECT = YES`

## 2. REENTRY Semantic Absence

Across all audited current PC artifacts:

- `semantic_buy_type=REENTRY`: `0`
- stale/cross-run recent-exit guard rows: `0`
- active current-decision old REENTRY branch: not observed
- whole-run prior-exit scan reintroduced for REENTRY hot path: not observed

Source inspection confirms the current hot path:

```text
shadow_runtime._supply_prior_exit_state
-> _bounded_recent_exit_guard_state_by_symbol
-> attach compact guard lineage only
```

The evidence payload explicitly records:

- `full_executions_jsonl_scanned_for_reentry = False`
- `strict_prior_pm_exit_artifacts_scanned_for_reentry = False`
- `full_prior_campaign_history_scanned_for_reentry = False`
- `daily_full_prior_exit_context_materialized = False`

The PC artifact still has legacy-named compatibility fields such as `reentry_semantic_eligibility`, but they carry BUY_NEW + guard state rather than resurrecting current-decision REENTRY authority.

`LEGACY_REENTRY_CURRENT_AUTHORITY_FOUND = NO`

## 3. Post-Expiry History Neutrality

Post-expiry positive BUY_NEW examples include:

| Date | Symbol | days since exit | semantic | guard state | target / lot-aware weight | rank |
|---|---|---:|---|---|---:|---:|
| 2022-10-13 | 45750 | 3 | BUY_NEW | EXPIRED_NOT_CURRENT_DECISION_AUTHORITY | 0.069653 | 5 |
| 2022-10-20 | 76470 | 3 | BUY_NEW | EXPIRED_NOT_CURRENT_DECISION_AUTHORITY | 0.029677 | 5 |
| 2022-10-25 | 33580 | 3 | BUY_NEW | EXPIRED_NOT_CURRENT_DECISION_AUTHORITY | 0.031250 | 5 |
| 2022-10-25 | 89180 | 3 | BUY_NEW | EXPIRED_NOT_CURRENT_DECISION_AUTHORITY | 0.031250 | 6 |
| 2022-11-04 | 27210 | 4 | BUY_NEW | EXPIRED_NOT_CURRENT_DECISION_AUTHORITY | 0.023233 | 4 |
| 2022-11-07 | 76470 | 3 | BUY_NEW | EXPIRED_NOT_CURRENT_DECISION_AUTHORITY | 0.038462 | 1 |
| 2022-12-13 | 94320 | 3 | BUY_NEW | EXPIRED_NOT_CURRENT_DECISION_AUTHORITY | 0.032258 | 3 |

These rows participate as BUY_NEW candidates with BQ/Entry/PC/MCV evidence. Some expired rows receive positive capital, while others remain zero because of ordinary rank, cash, lot, or capital competition reasons. No post-expiry bonus or penalty based solely on prior ownership was found.

`POST_EXPIRY_HISTORY_NEUTRALITY_CONFIRMED = YES`
`POST_EXPIRY_REVERSE_BIAS_FOUND = NO`

## 4. 76470 Large Capitalization Case

Actual fill/campaign lifecycle:

| Date | Action | Quantity | Decision type | Campaign |
|---|---|---:|---|---|
| 2022-10-12 | BUY | 600 | BUY_NEW | `pc-c5e0986109845fbb-76470-0001` |
| 2022-10-14 | SELL | 600 | SELL_EXIT | `pc-c5e0986109845fbb-76470-0001` |
| 2022-10-20 | BUY | 1100 | BUY_NEW | `pc-d5155ddca7bde7ab-76470-0001` |
| 2022-10-21 | SELL | 200 | REDUCE | `pc-d5155ddca7bde7ab-76470-0001` |
| 2022-10-24 | SELL | 200 | REDUCE | `pc-d5155ddca7bde7ab-76470-0001` |
| 2022-10-25 | SELL | 100 | REDUCE | `pc-d5155ddca7bde7ab-76470-0001` |
| 2022-10-26 | SELL | 100 | REDUCE | `pc-d5155ddca7bde7ab-76470-0001` |
| 2022-10-27 | SELL | 100 | REDUCE | `pc-d5155ddca7bde7ab-76470-0001` |
| 2022-10-28 | SELL | 100 | REDUCE | `pc-d5155ddca7bde7ab-76470-0001` |
| 2022-11-01 | SELL | 300 | EXIT | `pc-d5155ddca7bde7ab-76470-0001` |
| 2022-11-07 | BUY | 1600 | BUY_NEW | `pc-e27c96bb52f0a7bb-76470-0001` |
| 2022-11-25 | BUY | 100 | BUY_ADD | `pc-e27c96bb52f0a7bb-76470-0001` |
| 2022-11-28 | BUY | 100 | BUY_ADD | `pc-e27c96bb52f0a7bb-76470-0001` |
| 2022-11-29 | BUY | 100 | BUY_ADD | `pc-e27c96bb52f0a7bb-76470-0001` |
| 2022-11-30 | BUY | 100 | BUY_ADD | `pc-e27c96bb52f0a7bb-76470-0001` |
| 2022-12-01 | BUY | 100 | BUY_ADD | `pc-e27c96bb52f0a7bb-76470-0001` |

Key current-decision boundaries:

- `2022-10-20`: `76470` returned after guard expiry as `BUY_NEW`, `recent_exit_guard_state=EXPIRED_NOT_CURRENT_DECISION_AUTHORITY`, rank `5`, BQ reduced, PC target `0.029677`, execution `1100`.
- `2022-11-07`: after the `2022-11-01` full exit and bounded guard period, `76470` returned as `BUY_NEW`, `recent_exit_guard_state=EXPIRED_NOT_CURRENT_DECISION_AUTHORITY`, rank `1`, BQ full-allocation eligible, PC target `0.038462`, execution `1600`.
- `2022-11-25` through `2022-12-01`: each positive increment is `BUY_ADD`, with PM `ADD`, PC `BUY_ADD`, same campaign `pc-e27c96bb52f0a7bb-76470-0001`, and MCV ranks `3, 1, 3, 1, 1`.

The expansion is explained by current PIT BQ/Entry/MCV/PC evidence and current open-campaign ADD decisions. There is no evidence that `76470` was preferred because it had previously exited or re-entered.

`76470_CAPITALIZATION_EXPLAINED_BY_CURRENT_PIT = YES`
`76470_HISTORY_RELATED_PREFERENCE_FOUND = NO`

## 5. 83060 Extended Case

Actual lifecycle:

| Date | Evidence |
|---|---|
| 2022-10-03 | BUY_NEW 100, campaign `pc-44641d6e44d5f85b-83060-0001` |
| 2022-10-04 | SELL_EXIT 100, same campaign; guard materialized |
| 2022-10-05 | BUY_NEW candidate but active guard `FAIL_CLOSED`; target/quantity zero; no BUY |
| 2022-10-06 | active guard `FAIL_CLOSED`; no BUY |
| 2022-10-07 | active guard `FAIL_CLOSED`; no BUY |
| 2022-10-11 | expired guard, `EXPIRED_NOT_CURRENT_DECISION_AUTHORITY`; ordinary BUY_NEW candidate but no executable fill |
| 2022-10-14 | ordinary BUY_NEW 100, new campaign `pc-353ffefc940505e3-83060-0001` |
| 2022-10-17 onward | current open position, PM HOLD; no legacy REENTRY authority |

After the `2022-10-14` BUY_NEW, `83060` stays in the current-position branch with `semantic_buy_type=NOT_APPLICABLE`, guard `NOT_APPLICABLE`, and campaign-local HOLD/ADD evaluation. No old EXIT history or REENTRY branch reappears.

`83060_EXTENDED_LIFECYCLE_CORRECT = YES`

## 6. BUY_ADD / Campaign Identity

Audited BUY_ADD fills through completed coverage:

- total BUY_ADD fills: `14`
- symbols: `76470` five, `94340` three, `94320` three, `45940` three
- BUY_ADD mismatches: `0`

For every BUY_ADD fill checked:

- PM decision type is `ADD`,
- PC member semantic is `BUY_ADD`,
- execution campaign id equals PM/current open campaign id,
- positive quantity is order-increment scoped,
- no fallback/residual path created unauthorized positive ADD.

`BUY_ADD_SEMANTICS_CORRECT = YES`
`CAMPAIGN_IDENTITY_CORRECT = YES`

## 7. Portfolio Breadth / Capitalization Characterization

Decision-time allocation character changed after the first divergence, but the observed changes are explainable by valid opportunity return, ordinary path dependency, and normal PC/MCV/cash/lot/campaign mechanics.

Completed-period action counts:

| Action | Count |
|---|---:|
| BUY / BUY_NEW | 92 |
| BUY / BUY_ADD | 14 |
| SELL / SELL_EXIT | 74 |
| SELL / EXIT | 4 |
| SELL / REDUCE | 30 |

Representative daily PC breadth:

| Date | PC members | positive PC rows | BUY mix |
|---|---:|---:|---|
| 2022-10-03 | 50 | 9 | 7 BUY_NEW |
| 2022-10-25 | 51 | 17 | 2 BUY_NEW |
| 2022-11-01 | 53 | 16 | 2 BUY_NEW, 1 BUY_ADD |
| 2022-11-24 | 53 | 17 | 1 BUY_NEW |
| 2022-12-01 | 55 | 15 | 2 BUY_ADD |
| 2022-12-15 | 55 | 15 | 3 BUY_NEW |
| 2022-12-16 | 57 | 15 | 1 BUY_NEW, 1 BUY_ADD |

Classification:

`PORTFOLIO_BREADTH_CHANGE_EXPLAINED = A_PREVIOUSLY_SUPPRESSED_VALID_OPPORTUNITY_RETURN_PLUS_B_NORMAL_PATH_DEPENDENCY`

No evidence supports weak opportunity over-capitalization or history-related reverse bias.

## 8. Correctness-Only Performance Difference Check

The user-observed new-vs-old performance difference was treated only as a locator. No evidence was found for:

- incorrect guard behavior,
- invalid BUY,
- invalid ADD,
- history-related reverse bias,
- PC/MCV correctness defect,
- provenance/campaign identity defect,
- stale generation/state defect.

Classification:

`PERFORMANCE_DIFFERENCE_WITHOUT_CORRECTNESS_DEFECT`

## 9. Runtime / Storage Scaling Quick Check

The early completed period does not show the previous unbounded REENTRY daily duplication pattern.

Observed:

- `recent_exit_guard` artifact size remains bounded; max observed about `20KB`.
- first five completed daily directory average size: about `119MB`.
- last five completed daily directory average size: about `142MB`.
- first five completed day elapsed average: about `93s`.
- last five completed day elapsed average: about `107s`.
- source hot path records no REENTRY whole-run scans.

This is a mild early-run increase, not the previous late-run `250MB+` / multi-minute scaling pattern. No runtime/storage repair is justified from this FB evidence.

`UNBOUNDED_REENTRY_HOT_PATH_REINTRODUCED = NO`

## Required Final Answers

- `EXTENDED_GUARD_LIFECYCLE_CORRECT = YES`
- `MISSING_GUARD_MATERIALIZATION_FOUND = NO`
- `STALE_OR_CROSS_RUN_GUARD_FOUND = NO`
- `EXPIRED_GUARD_DECISION_AUTHORITY_FOUND = NO`
- `LEGACY_REENTRY_CURRENT_AUTHORITY_FOUND = NO`
- `POST_EXPIRY_HISTORY_NEUTRALITY_CONFIRMED = YES`
- `POST_EXPIRY_REVERSE_BIAS_FOUND = NO`
- `76470_CAPITALIZATION_EXPLAINED_BY_CURRENT_PIT = YES`
- `76470_HISTORY_RELATED_PREFERENCE_FOUND = NO`
- `83060_EXTENDED_LIFECYCLE_CORRECT = YES`
- `BUY_ADD_SEMANTICS_CORRECT = YES`
- `CAMPAIGN_IDENTITY_CORRECT = YES`
- `PORTFOLIO_BREADTH_CHANGE_EXPLAINED = YES`
- `PERFORMANCE_DIFFERENCE_CORRECTNESS_DEFECT_FOUND = NO`
- `UNBOUNDED_REENTRY_HOT_PATH_REINTRODUCED = NO`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE = YES`

## Final Judgment

`PHASE32_FB_POST_EZ_EXTENDED_ACTUAL_PATH_SEMANTIC_AND_CAPITAL_ALLOCATION_ACCEPTED_LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE`
