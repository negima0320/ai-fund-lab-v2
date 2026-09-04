# Phase32-EQ — Long-Run State/History Accumulation Dependency & Capital Suppression Root-Cause Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Run state inspected read-only: `RUNNING`
- Evidence coverage at extraction time: `2022-10-03` through `2024-12-20`, `547` completed business days
- Source baseline in `run_state.json`: `1f64f49ee9a8dd48280007e4df656e5f03e231ca`

This is a read-only correctness / architecture audit. It separates calendar / market effects from run-age and accumulated state/history dependency. No Production, SHADOW, config, schema, runtime state, Pending, Ledger, resume, replay, recover, or fresh-run mutation was executed.

No future return, later price, MFE/MAE, final campaign PnL, later SELL result, or hindsight was used for Production judgment.

## Evidence Sources

Existing artifacts:

- `run_state.json`
- `daily/*/strategy/portfolio_construction.json`
- `daily/*/strategy/buy_quality_decisions.json`
- `daily/*/strategy/position_management.json`
- `daily/*/strategy/market_context.json`
- `daily/*/positions/position_campaigns.json`
- `daily/*/*/subprocess_trace.json`
- `.runtime/persistent_ledger/*.jsonl` line counts, read-only

Source files inspected:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `scripts/runtime_test.py`

## 1. REENTRY Suppression History Sources

REENTRY prior context is supplied from persistent execution and PM-decision history:

- `shadow_runtime._supply_prior_exit_state`
  - reads `.runtime/persistent_ledger/executions.jsonl`
  - builds `prior_by_symbol`
  - attaches `prior_exit_context` to candidate and opportunity summaries
  - skips current open symbols
- `shadow_runtime._resolve_prior_closed_campaigns_from_executions`
  - sorts all executions
  - filters only `execution_business_date < decision_business_date`
  - reconstructs symbol-level quantity state
  - records the latest fully closed campaign per symbol
- `shadow_runtime._strict_prior_pm_exit_decision_evidence_by_campaign`
  - scans all prior daily PM artifacts before the decision date
  - supplies reason/reason_codes/source PM provenance
- PC / runtime artifacts then materialize REENTRY evidence fields such as:
  - `business_days_since_exit`
  - `prior_exit_business_date`
  - `reentry_reason_codes`
  - `reentry_recovery_status`
  - `reentry_semantic_state`
  - `reentry_not_currently_eligible`

Temporal safety is mostly correct: same-day/future exits are excluded. The issue is not future leakage. The issue is that prior closed symbol membership is effectively unbounded across the whole run.

## 2. REENTRY Retention / Expiry Contract

Observed reset / expiry behavior:

- Short cooldown exists in `position_management._cooldown_state`: `post_exit_reentry_cooldown_business_days`, default observed code path `10`.
- REENTRY state checks cooldown, event restriction, opportunity state, and technical state.
- No inspected source path showed a hard maximum age after which prior ownership ceases to classify a candidate as REENTRY-like / prior-exit influenced.
- The latest prior closed campaign by symbol remains relevant even hundreds of days later.

Therefore:

- Cooldown is bounded.
- Prior-exit identity relevance is not bounded by a comparable explicit expiry.
- Old prior-exit context can continue to require recovery / new-thesis / unknown-context handling long after short-term churn protection has expired.

## 3. Relationship / ADD Suppression History Sources

Relationship and ADD state consume current campaign and lifecycle evidence:

- `positions/position_campaigns.json` is materialized from latest prior campaign snapshot plus strict-prior ledger executions plus strict-prior PM evidence.
- `shadow_runtime._materialize_pre_action_position_campaigns` carries forward prior `position_campaigns`, merges current open rows, and closes campaigns from strict-prior ledger state.
- `runtime_v2.position_management.producer._run_scoped_position_campaign_authority_by_symbol` resolves only current OPEN campaign authority for PM.
- `position_management._structured_add_worthiness_evidence` uses:
  - campaign identity status
  - continuation quality status
  - downside risk status
  - `add_history_summary`
  - `reduce_history_summary`
  - PM decision history summary

Important ADD semantics:

- `prior_add_history_limits_incremental_add` is emitted when add history count is at least `5`.
- `prior_reduce_history_requires_add_review` is emitted when reduce history count is greater than `0`.
- These are campaign-local history effects, not necessarily whole-run stale-state effects.

## 4. Run-Age Accumulation Metrics

Run-age snapshots from current evidence:

| Run age | Date | Unique ever-held symbols | Campaigns | Closed campaigns | Prior-exit symbols | REENTRY suppressed rows | Relationship suppressed rows | ADD/current rows | ADD/current suppressed | Capitalized PC members | Daily elapsed sec |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `2022-10-03` | 0 | 0 | 0 | 0 | 0 | 13 | 22 | 13 | 9 | 102.20 |
| 100 | `2023-02-28` | 115 | 125 | 113 | 105 | 7 | 10 | 34 | 27 | 17 | 132.89 |
| 200 | `2023-07-25` | 220 | 256 | 239 | 207 | 8 | 6 | 35 | 29 | 21 | 164.15 |
| 300 | `2023-12-19` | 317 | 386 | 377 | 313 | 22 | 3 | 33 | 31 | 8 | 205.66 |
| 400 | `2024-05-21` | 416 | 526 | 517 | 410 | 21 | 0 | 30 | 26 | 9 | 186.27 |
| 500 | `2024-10-15` | 477 | 620 | 616 | 476 | 27 | 1 | 35 | 31 | 7 | 293.08 |
| 547 | `2024-12-20` | 507 | 659 | 650 | 501 | 18 | 5 | 33 | 28 | 10 | 381.62 |

Period averages:

| Metric | 2023 Mar-Jun | 2024 Jul-Dec | Early run age 1-180 | Mid 181-360 | Late 361-end |
| --- | ---: | ---: | ---: | ---: | ---: |
| Unique ever-held symbols | 155.345 | 471.471 | 101.850 | 291.144 | 449.283 |
| Campaigns | 177.631 | 609.378 | 113.972 | 352.289 | 575.610 |
| Closed campaigns | 166.524 | 601.134 | 103.000 | 340.200 | 567.337 |
| Prior-exit symbols | 147.714 | 466.353 | 92.811 | 283.661 | 444.064 |
| PC members | 52.821 | 52.765 | 53.911 | 53.772 | 52.412 |
| BQ-positive rows | 42.012 | 42.891 | 41.400 | 41.817 | 42.813 |
| REENTRY suppressed rows | 11.488 | 19.546 | 9.550 | 14.378 | 19.556 |
| Relationship suppressed rows | 6.595 | 3.361 | 10.006 | 4.772 | 2.861 |
| ADD/current rows | 31.226 | 32.050 | 32.994 | 32.844 | 31.385 |
| ADD/current suppressed | 26.107 | 28.899 | 27.572 | 27.806 | 28.198 |
| Capitalized PC members | 13.143 | 9.143 | 13.439 | 13.694 | 8.968 |
| Daily elapsed seconds | 143.279 | 275.037 | 122.341 | 203.417 | 262.542 |

Key result:

- Candidate count and BQ-positive count remain roughly stable across run age.
- Prior-exit symbols and campaign history grow strongly with run age.
- REENTRY suppression increases with run age.
- Relationship suppression as a generic bucket decreases, so the run-age dependency is not uniform across all relationship logic; it concentrates in REENTRY/prior-exit logic.

## 5. Suppression Probability By Comparable Evidence

Suppression rates among BQ-positive rows:

| Period | Relationship suppression / BQ-positive | REENTRY suppression / BQ-positive | Capitalized / BQ-positive |
| --- | ---: | ---: | ---: |
| 2023 Mar-Jun | 0.157 | 0.273 | 0.313 |
| 2024 Jul-Dec | 0.078 | 0.456 | 0.213 |
| Early age 1-180 | 0.242 | 0.231 | 0.325 |
| Mid age 181-360 | 0.114 | 0.344 | 0.327 |
| Late age 361-end | 0.067 | 0.457 | 0.209 |

Quality-stratified REENTRY suppression:

| Quality bin | 2023 Mar-Jun REENTRY suppression | 2024 Jul-Dec REENTRY suppression | Late age 361-end REENTRY suppression |
| --- | ---: | ---: | ---: |
| `q>=0.75` | 0.388 | 0.653 | 0.630 |
| `q>=0.65` | 0.358 | 0.529 | 0.539 |
| `q>=0.55` | 0.348 | 0.511 | 0.515 |
| `q<0.55` | 0.126 | 0.299 | 0.299 |

Correlation evidence:

| Pair | Correlation |
| --- | ---: |
| run age vs REENTRY suppression | 0.710 |
| prior-exit symbols vs REENTRY suppression | 0.719 |
| campaigns vs REENTRY suppression | 0.712 |
| closed campaigns vs REENTRY suppression | 0.716 |
| run age vs relationship suppression | -0.693 |

Judgment:

- `REENTRY_SUPPRESSION_RUN_AGE_DEPENDENT = YES`
- `RELATIONSHIP_SUPPRESSION_RUN_AGE_DEPENDENT = NO` for the broad generic bucket; relationship-related suppression is run-age dependent mainly through REENTRY/prior-exit.
- This is not explained by candidate population size; PC member count and BQ-positive count are stable.

## 6. Long-Age Prior EXIT Evidence

Rows with REENTRY suppression often reference old prior exits:

| Period | Known-age REENTRY suppressed rows | Avg age days | Median | p90 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023 Mar-Jun | 965 | 48.1 | 16.0 | 140.0 | 192.0 |
| 2024 Jul-Dec | 2,340 | 182.0 | 133.0 | 469.0 | 577.0 |

Age buckets:

| Bucket | 2023 Mar-Jun | 2024 Jul-Dec |
| --- | ---: | ---: |
| `<=10` | 397 | 458 |
| `<=30` | 162 | 237 |
| `<=60` | 83 | 189 |
| `<=120` | 179 | 254 |
| `>120` | 144 | 1,202 |

2024 Jul-Dec REENTRY reason-code counts:

- cooldown: `167`
- recovery / not-satisfied / new-thesis: `951`
- churn: `812`
- unknown prior context: `563`

Representative long-age examples:

- `2024-07-01 89180`: `453` days since exit, rank `3`, quality `0.808041`, `reentry_trend_recovery_not_satisfied`.
- `2024-07-01 38230`: `154` days since exit, rank `13`, quality `0.721309`, `reentry_trend_recovery_not_satisfied`.
- `2024-07-01 70140`: `159` days since exit, rank `15`, quality `0.713147`, `reentry_repeated_unresolved_churn`.
- `2024-12-20`: examples in PC artifact include `business_days_since_exit` / prior-exit ages of `199`, `434`, `534`, `577` days.

Interpretation:

- This is concrete evidence that old prior ownership/exit facts remain active long after short cooldown windows.
- Some old rows are properly current-evidence failures, such as trend/momentum recovery not satisfied.
- Others are still blocked by unknown/recoverable prior context despite the age being very large.
- That pattern supports an architecture gap: prior-exit relevance is not explicitly bounded or refreshed into a NEW-equivalent lifecycle when old history is no longer semantically useful.

## 7. Stale State / Identity Defect Check

No concrete stale-state or identity defect was proven:

- Run-scoped campaign authority uses current run evidence.
- `positions/position_campaigns.json` temporal safety declares strict-prior source selection and no future information use.
- PM current-position campaign authority rejects run-id mismatch and future-information flags.
- The issue is not cross-run lineage, duplicate identity, or future leakage.

However, a history relevance gap is proven:

- Old strict-prior history is valid as history.
- Valid history is not automatically semantically relevant forever.
- Current code paths show no explicit max-age / expiry / renewed-thesis materialization boundary that releases very old prior exits from REENTRY-specific handling.

Therefore:

- `STALE_HISTORY_DEFECT_PROVEN = NO`
- `UNBOUNDED_HISTORY_ACCUMULATION_EFFECT = YES`

## 8. Runtime Slowdown Reconstruction

Daily elapsed time from existing `subprocess_trace.json`:

| Run-age bucket | n | Avg sec/day | Median | p90 |
| --- | ---: | ---: | ---: | ---: |
| 1-100 | 100 | 106.63 | 103.09 | 126.64 |
| 101-200 | 100 | 147.03 | 143.81 | 173.24 |
| 201-300 | 100 | 195.43 | 191.16 | 227.20 |
| 301-400 | 100 | 233.75 | 231.81 | 262.85 |
| 401-500 | 100 | 260.81 | 259.47 | 293.57 |
| 501-end | 47 | 284.42 | 280.81 | 310.24 |

This matches the user observation directionally: early days are around 2 minutes, late days approach 5 to 6 minutes.

Per-job averages:

| Job | Age 1-100 avg sec | Age 501-end avg sec | Increase |
| --- | ---: | ---: | ---: |
| `market_refresh` | 59.71 | 167.74 | +108.03 |
| `morning` | 19.90 | 46.89 | +26.99 |
| `sell_planning` | 2.72 | 4.97 | +2.25 |
| `data_readiness` | 2.94 | 3.37 | +0.43 |
| `submit` | 15.08 | 50.56 | +35.48 |
| `execution` | 1.83 | 3.62 | +1.79 |
| `current_valuation_refresh` | 2.81 | 5.05 | +2.24 |
| `runtime_state_refresh` | 1.63 | 2.23 | +0.60 |

Scaling correlations:

| Pair | Correlation |
| --- | ---: |
| run age vs daily elapsed | 0.948 |
| campaign count vs daily elapsed | 0.950 |
| closed campaigns vs daily elapsed | 0.949 |

Additional size evidence:

- Daily artifact directory size grew from about `112.8MB` on `2022-10-03` to `251.5MB` on `2024-12-20`.
- Current `.runtime/persistent_ledger` line counts: orders `3,698`, executions `1,849`, positions `6,557`, cash `525`, events `525`.

## 9. Slowdown Code Path Assessment

History-dependent scan paths found:

- `shadow_runtime._supply_prior_exit_state` reads all `persistent_ledger/executions.jsonl` each day.
- `shadow_runtime._resolve_prior_closed_campaigns_from_executions` sorts and walks all executions before the decision date.
- `shadow_runtime._latest_prior_position_campaigns_path` scans all prior daily directories to find the latest prior campaign artifact.
- `shadow_runtime._materialize_pre_action_position_campaigns` carries and rewrites all prior campaign rows into each daily `position_campaigns.json`.
- `shadow_runtime._strict_prior_pm_sell_decision_evidence_by_campaign` scans all prior daily `strategy/position_management.json` artifacts before the decision date.
- `shadow_runtime._strict_prior_pm_exit_decision_evidence_by_campaign` scans prior PM artifacts to recover EXIT context.
- `runtime_test.py` contains multiple summary / audit paths that glob `daily/*` and ledger jsonl files for run-level observability and recovery validation.

Performance judgment:

- The slowdown is history-related.
- It is not solely REENTRY-related: `market_refresh` and `submit` dominate the elapsed increase, while REENTRY/campaign history contributes strongly to `morning` and strategy materialization.
- The common mechanism is repeated unbounded run-history and artifact scanning.

## 10. Common Root-Cause Assessment

Capital suppression and runtime slowdown share a partial root:

- Capital suppression: accumulated prior-exit / campaign history increases the number of symbols subject to REENTRY handling, including old exits.
- Slowdown: accumulated ledger, campaign, daily artifact, and PM history increases scan and materialization cost.

But they are not a single identical defect:

- Capital suppression is a semantic relevance problem around how long prior-exit history should influence future opportunity classification.
- Slowdown is also an implementation/indexing problem across market refresh, submit, reports, ledger, and daily artifact scans.

Therefore:

- `COMMON_ROOT_CAUSE_SUPPORTED = MIXED`

## 11. Required Classification

Final classification: `F. MIXED`

Components:

- `C. UNBOUNDED_HISTORY_ACCUMULATION_EFFECT`: Proven for REENTRY prior-exit symbol growth and for daily runtime scaling.
- `E. PERFORMANCE-ONLY SCALING DEFECT`: Proven for repeated full-history scans and elapsed-time growth.
- `B. EXPECTED_BOUNDED_HISTORY_EFFECT`: Partially present for short cooldown and campaign-local ADD history, but not sufficient to explain old prior-exit suppression.
- `A. VALID_MARKET/STRATEGY_CHANGE`: Still relevant from EO/EP, but not sufficient as the only cause.
- `D. STALE_STATE / IDENTITY DEFECT`: Not proven as stale/cross-run/identity corruption.

## 12. Repair Necessity

`PRODUCTION_REPAIR_JUSTIFIED = YES`

Scope of justified repair:

- Not parameter tuning.
- Not BQ threshold changes.
- Not rank/weight/Exposure tuning.
- Not forced REENTRY acceptance.
- Not weakening PIT/fail-closed.

The justified repair is architectural:

- introduce an explicit prior-exit relevance horizon / renewed-thesis lifecycle contract, or equivalent bounded semantic release;
- ensure old prior ownership does not indefinitely impose REENTRY-specific suppression without current evidence that the prior campaign remains relevant;
- preserve short-term churn protection and genuine recovery checks;
- index or snapshot prior-exit/campaign/PM evidence so daily runtime does not repeatedly scan unbounded run history.

## Final Required Answers

- `HISTORY_ACCUMULATION_AFFECTS_CAPITALIZATION = YES`
- `REENTRY_SUPPRESSION_RUN_AGE_DEPENDENT = YES`
- `RELATIONSHIP_SUPPRESSION_RUN_AGE_DEPENDENT = NO`
- `STALE_HISTORY_DEFECT_PROVEN = NO`
- `RUNTIME_SLOWDOWN_HISTORY_RELATED = YES`
- `COMMON_ROOT_CAUSE_SUPPORTED = MIXED`
- `PRODUCTION_REPAIR_JUSTIFIED = YES`

## No-Mutation Confirmation

- `PRODUCTION_CHANGED: NO`
- `SHADOW_CHANGED: NO`
- `TARGET_RUN_MUTATED: NO`
- `RUNTIME_STATE_MUTATED: NO`
- `FRESH_RUN_EXECUTED: NO`
- `RESUME_EXECUTED: NO`
- `REPLAY_EXECUTED: NO`
- `FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT: NO`

## Final Judgment

`PHASE32_EQ_UNBOUNDED_PRIOR_EXIT_HISTORY_ACCUMULATION_AFFECTS_REENTRY_CAPITALIZATION_AND_RUNTIME_SCALING_PRODUCTION_ARCHITECTURE_REPAIR_JUSTIFIED_NO_STATE_MUTATION`
